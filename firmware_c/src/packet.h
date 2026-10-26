/* BLE data packets (one notification each). Little-endian, packed. Must match
 * host/neurband_ble.py; documented in docs/firmware_c.md "Packet format". */
#pragma once
#include <stdint.h>
#include <zephyr/toolchain.h>

#define PKT_MAX_LEN 244 /* ATT_MTU 247 - 3 */
#define PKT_HDR_LEN 12

enum pkt_type {
	PKT_I16 = 0,  /* filtered stream: int16 LE, 0.25 uV/count, sample-major */
	PKT_I24 = 1,  /* raw stream: ADS int24 big-endian as shifted out, sample-major */
	PKT_DIAG = 2, /* once per second: raw DC, rails, contact status (struct pkt_diag) */
	PKT_IMU = 3,  /* LSM6DSL samples: n x struct pkt_imu_sample */
};
#define PKT_I16_MAX_SAMPLES 14 /* 12 + 14 * 16 = 236 bytes */
#define PKT_I24_MAX_SAMPLES 9  /* 12 + 9 * 24 = 228 bytes */
#define PKT_IMU_MAX_SAMPLES 16 /* 12 + 16 * 14 = 236 bytes, ~77 ms at 208 Hz */

/* flags */
#define PF_MARKER   0x01 /* button pressed since the previous packet */
#define PF_CHARGING 0x02 /* charger connected (streaming is refused/stopped) */
#define PF_LOFF_EN  0x04 /* lead-off detection on */
#define PF_LOFF_ANY 0x08 /* any lead-off status bit set in this packet */
#define PF_MISSED   0x10 /* ADS frames were lost before this packet (index jumps) */
#define PF_CLIP     0x20 /* int16 saturation, or a raw code within 5 % of full scale */
#define PF_LOWBAT   0x40 /* battery below 3.5 V */
#define PF_TEST     0x80 /* inputs not normal: internal test signal or shorted */

/* cfg byte: bits 0-3 gain (1..12), bit 4 output rate 4000 (else 2000),
 * bits 5-6 high-pass (0 none/raw, 1 = 20 Hz, 2 = 40 Hz) */
#define PCFG_RATE4K 0x10
#define PCFG_HP_SHIFT 5

struct pkt_hdr {
	uint16_t seq;    /* +1 per packet of any type, also for packets dropped in firmware */
	uint32_t sample; /* index of the first sample at the output rate (diag: next sample) */
	uint8_t type;    /* enum pkt_type */
	uint8_t n;       /* samples in this packet (0 for diag) */
	uint8_t flags;
	uint8_t cfg;
	uint8_t loff_p;  /* OR of LOFF_STATP over the packet (diag: over the last second) */
	uint8_t loff_n;  /* same for LOFF_STATN; bit i = channel i+1 */
} __packed;
BUILD_ASSERT(sizeof(struct pkt_hdr) == PKT_HDR_LEN, "header layout");

struct pkt_diag {
	int32_t dc[8];      /* unfiltered DC level per channel, ADS codes (V = code * 4.8 / gain / 2^24) */
	uint8_t rail;       /* channels with |raw code| >= 95 % full scale in the last second */
	uint8_t clip;       /* channels with int16 saturation in the last second */
	uint8_t rld_cfg;    /* RLD sense set chosen by the host */
	uint8_t rld_active; /* RLD sense set in use (lead-off channels removed) */
	uint16_t vbat_mv;
	uint16_t overruns;  /* ADS frames lost since start (saturates) */
	uint16_t drops;     /* packets dropped in firmware since start (saturates) */
	uint16_t status_err;/* frames whose status word did not start with 1100b */
} __packed;
BUILD_ASSERT(sizeof(struct pkt_diag) == 44, "diag layout");

/* IMU sample. 'sample' in the header = stream sample index (same units as the EMG packets)
 * of the newest ADS conversion when INT1 fired for the first sample; dt adds to it per sample.
 * Gyro: 17.5 mdps/LSB (+-500 dps), accel: 0.122 mg/LSB (+-4 g), LSM6DSL register order. */
struct pkt_imu_sample {
	uint16_t dt;
	int16_t g[3];
	int16_t a[3];
} __packed;
BUILD_ASSERT(sizeof(struct pkt_imu_sample) == 14, "imu layout");
