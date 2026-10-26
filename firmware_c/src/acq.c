/* Acquisition pipeline:
 *   DRDY falling edge (ISR) -> acq thread: read the 27-byte frame over SPI (EasyDMA) into a
 *   frame ring -> proc thread: DSP + packetizing -> packet queue -> BLE TX thread (ble.c).
 * Every stage counts what it loses; the sample index in each packet header always jumps
 * over lost frames, so the host sees every gap. */
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/sys/byteorder.h>

#include "ads1298.h"
#include "app.h"
#include "dsp.h"
#include "packet.h"

LOG_MODULE_REGISTER(acq, LOG_LEVEL_INF);

#define RING_N 64  /* frames: 16 ms at 4 kSPS */
#define PKTQ_N 20  /* packets: ~140 ms of the default stream (RAM: 64 KB total) */

struct frame {
	uint32_t idx; /* ADS conversion index since start (counts missed DRDYs too) */
	uint8_t d[ADS_FRAME_BYTES];
};
struct pkt_item {
	uint16_t len;
	uint8_t d[PKT_MAX_LEN];
};

static struct frame ring[RING_N];
static atomic_t ring_head, ring_tail; /* single producer (acq), single consumer (proc) */
K_MSGQ_DEFINE(pkt_q, sizeof(struct pkt_item), PKTQ_N, 4);
static K_SEM_DEFINE(drdy_sem, 0, K_SEM_MAX_LIMIT);
static K_SEM_DEFINE(proc_sem, 0, K_SEM_MAX_LIMIT);
static K_MUTEX_DEFINE(ads_mtx);

static atomic_t running, marker, overruns, drops, status_errs;
static atomic_t rld_req; /* 0x100 | mask: new RLD sense set to apply between frames */
static uint8_t rld_active;
static uint32_t ads_idx;

/* packetizer state (proc thread only) */
static struct pkt_item cur;
static uint8_t cur_n, n_max, bps, pkt_flags, pkt_lp, pkt_ln;
static uint32_t next_out;
static atomic_t seq, drdy_edges; /* seq: shared by the proc and IMU threads */
static bool gap;
/* per-second diagnostics */
static uint32_t diag_count;
static uint8_t sec_lp, sec_ln, sec_rail, sec_clip, good_secs[8];

static void drdy_handler(void)
{
	atomic_inc(&drdy_edges);
	k_sem_give(&drdy_sem);
}

static void acq_thread(void *a, void *b, void *c)
{
	ARG_UNUSED(a);
	ARG_UNUSED(b);
	ARG_UNUSED(c);
	static uint8_t scratch[ADS_FRAME_BYTES];

	for (;;) {
		k_sem_take(&drdy_sem, K_FOREVER);
		if (!atomic_get(&running)) {
			continue;
		}
		/* More DRDY edges pending = we were late; the ADS kept only the newest frame. */
		unsigned int behind = k_sem_count_get(&drdy_sem);

		if (behind) {
			k_sem_reset(&drdy_sem);
			ads_idx += behind;
			atomic_add(&overruns, behind);
		}
		atomic_val_t h = atomic_get(&ring_head);
		bool full = (uint32_t)(h - atomic_get(&ring_tail)) >= RING_N;
		struct frame *f = &ring[(uint32_t)h % RING_N];

		k_mutex_lock(&ads_mtx, K_FOREVER);
		if (atomic_get(&running)) {
			ads_read_frame(full ? scratch : f->d);
			atomic_val_t r = atomic_clear(&rld_req);

			if (r & 0x100) {
				ads_set_rld_streaming((uint8_t)r);
				rld_active = (uint8_t)r;
			}
		}
		k_mutex_unlock(&ads_mtx);
		if (full) {
			atomic_inc(&overruns);
		} else {
			f->idx = ads_idx;
			atomic_set(&ring_head, h + 1);
			k_sem_give(&proc_sem);
		}
		ads_idx++;
	}
}

static uint8_t pkt_cfg(void)
{
	uint8_t c = cfg.gain & 0x0F;

	if (cfg.fmt == FMT_I24) {
		c |= cfg.rate == 4000 ? PCFG_RATE4K : 0;
	} else {
		c |= (uint8_t)((cfg.hp_idx + 1) << PCFG_HP_SHIFT);
	}
	return c;
}

static uint8_t common_flags(void)
{
	uint8_t f = 0;

	f |= cfg.leadoff ? PF_LOFF_EN : 0;
	f |= cfg.mux != ADS_MUX_NORMAL ? PF_TEST : 0;
	f |= app_charging() ? PF_CHARGING : 0;
	f |= app_low_battery() ? PF_LOWBAT : 0;
	return f;
}

static void queue_packet(struct pkt_item *p, uint8_t type, uint8_t n, uint32_t sample,
			 uint8_t flags, uint8_t lp, uint8_t ln, uint16_t body_len)
{
	struct pkt_hdr h = {
		.seq = sys_cpu_to_le16((uint16_t)atomic_inc(&seq)),
		.sample = sys_cpu_to_le32(sample),
		.type = type,
		.n = n,
		.flags = flags | common_flags() | ((lp | ln) ? PF_LOFF_ANY : 0),
		.cfg = pkt_cfg(),
		.loff_p = lp,
		.loff_n = ln,
	};

	memcpy(p->d, &h, sizeof(h));
	p->len = PKT_HDR_LEN + body_len;
	if (k_msgq_put(&pkt_q, p, K_NO_WAIT) != 0) {
		atomic_inc(&drops); /* seq already advanced: the host sees the gap */
	}
}

void acq_queue_packet(uint8_t type, uint8_t n, uint32_t sample, uint8_t flags, uint8_t lp,
		      uint8_t ln, const void *body, uint16_t body_len)
{
	static struct pkt_item it; /* only the IMU thread calls this */

	memcpy(&it.d[PKT_HDR_LEN], body, MIN(body_len, PKT_MAX_LEN - PKT_HDR_LEN));
	queue_packet(&it, type, n, sample, flags, lp, ln, body_len);
}

uint32_t acq_sample_now(void)
{
	uint32_t e = (uint32_t)atomic_get(&drdy_edges);

	e = e ? e - 1 : 0;
	return cfg.fmt == FMT_I16 ? e >> 1 : e;
}

static void flush(void)
{
	if (cur_n == 0) {
		return;
	}
	uint8_t f = pkt_flags | (gap ? PF_MISSED : 0);

	if (atomic_clear(&marker)) {
		f |= PF_MARKER;
	}
	queue_packet(&cur, cfg.fmt == FMT_I16 ? PKT_I16 : PKT_I24, cur_n, next_out - cur_n, f,
		     pkt_lp, pkt_ln, (uint16_t)(cur_n * bps));
	cur_n = 0;
	pkt_flags = pkt_lp = pkt_ln = 0;
	gap = false;
}

static void add_sample(uint32_t out_idx, const void *data, uint8_t clip)
{
	if (out_idx != next_out && (cur_n || atomic_get(&seq))) {
		flush();    /* the header index must describe contiguous samples */
		gap = true; /* ... and the next packet starts after lost frames */
	}
	memcpy(&cur.d[PKT_HDR_LEN + cur_n * bps], data, bps);
	cur_n++;
	next_out = out_idx + 1;
	pkt_flags |= clip ? PF_CLIP : 0;
	sec_clip |= clip;
	if (cur_n == n_max) {
		flush();
	}
}

static void send_diag(void)
{
	static struct pkt_item d;
	struct pkt_diag body = {0};
	int32_t dc[8];

	dsp_dc(dc);
	for (int c = 0; c < 8; c++) {
		body.dc[c] = (int32_t)sys_cpu_to_le32(dc[c]);
	}
	body.rail = sec_rail;
	body.clip = sec_clip;
	body.rld_cfg = cfg.rld_mask;
	body.rld_active = rld_active;
	body.vbat_mv = sys_cpu_to_le16(app_vbat_mv());
	body.overruns = sys_cpu_to_le16((uint16_t)MIN(atomic_get(&overruns), 0xFFFF));
	body.drops = sys_cpu_to_le16((uint16_t)MIN(atomic_get(&drops), 0xFFFF));
	body.status_err = sys_cpu_to_le16((uint16_t)MIN(atomic_get(&status_errs), 0xFFFF));
	memcpy(&d.d[PKT_HDR_LEN], &body, sizeof(body));
	queue_packet(&d, PKT_DIAG, 0, next_out, 0, sec_lp, sec_ln, sizeof(body));

	/* Bias loop: drop channels with lead-off from the RLD sense set at once, re-add a
	 * channel after 3 clean seconds (docs/science/signal_chain.md section 3). Lead-off
	 * status is only meaningful with lead-off detection on. */
	if (cfg.leadoff) {
		uint8_t bad = sec_lp | sec_ln, want = 0;

		for (int c = 0; c < 8; c++) {
			good_secs[c] = (bad & BIT(c)) ? 0 : MIN(good_secs[c] + 1, 255);
			if ((cfg.rld_mask & BIT(c)) && good_secs[c] >= 3) {
				want |= BIT(c);
			}
		}
		want = (rld_active & ~bad) | want;
		want &= cfg.rld_mask;
		if (want != rld_active) {
			LOG_INF("RLD sense 0x%02x -> 0x%02x", rld_active, want);
			atomic_set(&rld_req, 0x100 | want);
		}
	}
	sec_lp = sec_ln = sec_rail = sec_clip = 0;
}

static void process(const struct frame *f)
{
	const uint8_t *d = f->d;
	int32_t x[8];
	uint8_t rail = 0, clip = 0;

	/* status word (9.4.1.3): 1100 | LOFF_STATP[7:0] | LOFF_STATN[7:0] | GPIO[7:4] */
	if ((d[0] & 0xF0) != 0xC0) {
		atomic_inc(&status_errs);
	}
	uint8_t lp = (uint8_t)((d[0] << 4) | (d[1] >> 4));
	uint8_t ln = (uint8_t)((d[1] << 4) | (d[2] >> 4));

	for (int c = 0; c < 8; c++) {
		const uint8_t *p = &d[3 + 3 * c];
		int32_t v = (int32_t)(((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8)) >> 8;

		x[c] = v;
		if (v >= 7969178 || v <= -7969178) { /* 95 % of 2^23 */
			rail |= BIT(c);
		}
	}
	sec_lp |= lp;
	sec_ln |= ln;
	sec_rail |= rail;
	pkt_flags |= rail ? PF_CLIP : 0;
	pkt_lp |= lp;
	pkt_ln |= ln;

	if (cfg.fmt == FMT_I16) {
		int16_t out[8];

		if (dsp_push(x, f->idx, true, out, &clip)) {
			for (int c = 0; c < 8; c++) {
				out[c] = (int16_t)sys_cpu_to_le16(out[c]);
			}
			add_sample(f->idx >> 1, out, clip);
		}
	} else {
		dsp_push(x, f->idx, false, NULL, &clip); /* DC tracker only, for diagnostics */
		add_sample(f->idx, &d[3], 0);
	}
	if (++diag_count >= cfg_ads_rate(&cfg)) { /* once per second */
		diag_count = 0;
		send_diag();
	}
}

static void proc_thread(void *a, void *b, void *c)
{
	ARG_UNUSED(a);
	ARG_UNUSED(b);
	ARG_UNUSED(c);

	for (;;) {
		k_sem_take(&proc_sem, K_FOREVER);
		while (atomic_get(&ring_tail) != atomic_get(&ring_head)) {
			atomic_val_t t = atomic_get(&ring_tail);

			if (atomic_get(&running)) {
				process(&ring[(uint32_t)t % RING_N]);
			}
			atomic_set(&ring_tail, t + 1);
		}
	}
}

/* acq above BT host threads; the radio ISRs still preempt it (frame read is ~40 us) */
K_THREAD_DEFINE(acq_tid, 1024, acq_thread, NULL, NULL, NULL, K_PRIO_COOP(2), 0, 0);
K_THREAD_DEFINE(proc_tid, 1536, proc_thread, NULL, NULL, NULL, K_PRIO_PREEMPT(1), K_FP_REGS, 0);

int acq_init(void)
{
	if (imu_init() != 0) {
		LOG_WRN("no LSM6DSL found, streaming without IMU");
	}
	return ads_init(drdy_handler);
}

int acq_start(uint16_t max_payload)
{
	if (atomic_get(&running)) {
		return 0;
	}
	bps = cfg.fmt == FMT_I16 ? 16 : 24;
	n_max = MIN((max_payload - PKT_HDR_LEN) / bps,
		    cfg.fmt == FMT_I16 ? PKT_I16_MAX_SAMPLES : PKT_I24_MAX_SAMPLES);
	if (max_payload <= PKT_HDR_LEN || n_max == 0) {
		return -EMSGSIZE; /* ATT MTU too small for even one sample */
	}
	k_msgq_purge(&pkt_q);
	atomic_set(&ring_head, 0);
	atomic_set(&ring_tail, 0);
	k_sem_reset(&drdy_sem);
	k_sem_reset(&proc_sem);
	atomic_clear(&overruns);
	atomic_clear(&drops);
	atomic_clear(&status_errs);
	atomic_clear(&marker);
	atomic_clear(&rld_req);
	ads_idx = 0;
	atomic_clear(&seq);
	atomic_clear(&drdy_edges);
	next_out = 0;
	cur_n = 0;
	pkt_flags = pkt_lp = pkt_ln = 0;
	gap = false;
	diag_count = 0;
	sec_lp = sec_ln = sec_rail = sec_clip = 0;
	memset(good_secs, 0, sizeof(good_secs));
	rld_active = cfg.rld_mask;
	dsp_reset(cfg.gain, cfg.hp_idx);
	atomic_set(&running, 1);
	imu_start();
	ads_stream_start();
	LOG_INF("streaming fmt=%d ads_rate=%u n=%u", cfg.fmt, cfg_ads_rate(&cfg), n_max);
	return 0;
}

void acq_stop(void)
{
	if (!atomic_get(&running)) {
		return;
	}
	atomic_set(&running, 0);
	imu_stop();
	k_mutex_lock(&ads_mtx, K_FOREVER); /* wait for a frame read in progress */
	ads_stream_stop();
	k_mutex_unlock(&ads_mtx);
	k_msleep(2); /* let the proc thread finish the frame it holds */
	k_msgq_purge(&pkt_q);
}

bool acq_running(void)
{
	return atomic_get(&running);
}

void acq_marker(void)
{
	atomic_set(&marker, 1);
}

uint8_t acq_rld_active(void)
{
	return atomic_get(&running) ? rld_active : cfg.rld_mask;
}

uint32_t acq_overruns(void)
{
	return atomic_get(&overruns);
}

uint32_t acq_drops(void)
{
	return atomic_get(&drops);
}

uint32_t acq_status_errors(void)
{
	return atomic_get(&status_errs);
}

int acq_get_packet(uint8_t *buf, uint16_t *len)
{
	static struct pkt_item it;

	k_msgq_get(&pkt_q, &it, K_FOREVER);
	memcpy(buf, it.d, it.len);
	*len = it.len;
	return 0;
}
