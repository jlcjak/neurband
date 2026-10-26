/* neurband rev C: control (commands, charger interlock, battery, LED, button, power).
 * Everything that touches the ADS outside streaming runs on one work queue (app_wq). */
#include <stdlib.h>
#include <string.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/poweroff.h>
#include <zephyr/sys/printk.h>

#include "ads1298.h"
#include "app.h"

LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);

#define IDLE_OFF_S     (5 * 60) /* System OFF after 5 min not connected and not streaming */
#define LONG_PRESS_MS  3000     /* hold the button 3 s: System OFF */
#define VBAT_LOW_MV    3500     /* warn (LED, flag): the 3.3 V LDO is near dropout */
#define VBAT_CRIT_MV   3300     /* stop and power off after 3 readings in a row */

#define USER_NODE DT_PATH(zephyr_user)
static const struct gpio_dt_spec led = GPIO_DT_SPEC_GET(USER_NODE, led_gpios);
static const struct gpio_dt_spec button = GPIO_DT_SPEC_GET(USER_NODE, button_gpios);
static const struct gpio_dt_spec chg = GPIO_DT_SPEC_GET(USER_NODE, chg_gpios);
static const struct adc_dt_spec vbat_adc = ADC_DT_SPEC_GET(USER_NODE);

struct nb_cfg cfg = {
	.rate = 4000, .gain = 6, .fmt = FMT_I16, .hp_idx = 0, .mux = ADS_MUX_NORMAL,
	.leadoff = false, .rld_mask = 0x0F, /* channels 1-4 (P and N) = 8 sensed inputs: 57 deg phase margin with 1M||4.7nF (docs/science/simulations.md) */
};

static K_THREAD_STACK_DEFINE(app_wq_stack, 2048);
static struct k_work_q app_wq;
K_MSGQ_DEFINE(cmd_q, 40, 4, 1);

static volatile bool charging, low_bat, connected_flag;
static volatile uint16_t vbat_mv;
static int verify_err = -1, idle_s, crit_count;
static char last[24] = "boot";

bool app_charging(void) { return charging; }
bool app_low_battery(void) { return low_bat; }
uint16_t app_vbat_mv(void) { return vbat_mv; }

/* ------------------------------------------------------------------ LED patterns */
/* 50 ms ticks over a 2 s cycle; bit i = LED on in tick i */
#define PAT(...) (pat_bits((const uint8_t[]){__VA_ARGS__, 0xFF}))
static uint64_t pat_bits(const uint8_t *t)
{
	uint64_t m = 0;

	for (; *t != 0xFF; t++) {
		m |= 1ULL << *t;
	}
	return m;
}
static uint64_t led_pat;
static uint8_t led_tick;

static void led_timer_fn(struct k_timer *t)
{
	ARG_UNUSED(t);
	gpio_pin_set_dt(&led, (int)((led_pat >> led_tick) & 1));
	led_tick = (led_tick + 1) % 40;
}
K_TIMER_DEFINE(led_timer, led_timer_fn, NULL);

static void led_update(void)
{
	if (charging) {
		led_pat = ~0ULL; /* solid while charging (charger powers it) */
	} else if (low_bat) {
		led_pat = PAT(0, 2, 4); /* triple flash every 2 s */
	} else if (acq_running()) {
		led_pat = PAT(0, 10, 20, 30); /* flash every 0.5 s */
	} else if (connected_flag) {
		led_pat = PAT(0, 3); /* double flash every 2 s */
	} else {
		led_pat = PAT(0, 20); /* advertising: flash every 1 s */
	}
}

/* ------------------------------------------------------------------ status */
static void status_publish(void)
{
	char link[48], s[STATUS_BUF_LEN];
	static const char *const mux_name[] = {[ADS_MUX_NORMAL] = "normal", [ADS_MUX_SHORT] = "short",
					       [ADS_MUX_TEST] = "test"};

	ble_link_info(link, sizeof(link));
	snprintk(s, sizeof(s),
		 "fw=%s st=%s chg=%d vbat=%u low=%d ads=0x%02x verr=%d fmt=%d rate=%u out=%u gain=%u "
		 "hp=%u mux=%s loff=%d rld=0x%02x/0x%02x imu=%d %s ovr=%u drop=%u serr=%u last=%s",
		 FW_VERSION, acq_running() ? "stream" : ads_is_powered() ? "ready" : "off", charging,
		 vbat_mv, low_bat, ads_id(), verify_err, cfg.fmt == FMT_I16 ? 16 : 24,
		 cfg_ads_rate(&cfg), cfg.fmt == FMT_I16 ? 2000 : cfg.rate, cfg.gain,
		 cfg.fmt == FMT_I16 ? (cfg.hp_idx ? 40 : 20) : 0, mux_name[cfg.mux], cfg.leadoff,
		 cfg.rld_mask, acq_rld_active(), imu_present(), link, acq_overruns(), acq_drops(),
		 acq_status_errors(), last);
	ble_set_status(s);
}

/* ------------------------------------------------------------------ AFE control */
static int afe_apply(void)
{
	const struct ads_settings s = {
		.rate = cfg_ads_rate(&cfg), .gain = cfg.gain, .mux = cfg.mux,
		.leadoff = cfg.leadoff, .rld_mask = cfg.rld_mask,
	};

	verify_err = ads_configure(&s);
	return verify_err;
}

static int afe_on(void)
{
	if (charging) {
		return -EACCES; /* interlock: never power the AFE while the charger is connected */
	}
	if (ads_is_powered()) {
		return 0;
	}
	int err = ads_power_up();

	afe_apply();
	return err;
}

static void afe_off(void)
{
	acq_stop();
	ads_power_down();
}

/* Change settings: stop, write registers, resume if it was streaming. */
static void reconfigure(void)
{
	bool was = acq_running();

	acq_stop();
	if (ads_is_powered()) {
		afe_apply();
	}
	if (was) {
		acq_start(ble_max_payload());
	}
}

static void power_off(void);

static void handle(char *line)
{
	char *arg = strchr(line, ' ');
	int err = 0;

	if (arg) {
		*arg++ = '\0';
	}
	if (!strcmp(line, "start")) {
		err = afe_on();
		if (err == 0) {
			err = acq_start(ble_max_payload());
		}
	} else if (!strcmp(line, "stop")) {
		acq_stop();
	} else if (!strcmp(line, "rate") && arg && (atoi(arg) == 2000 || atoi(arg) == 4000)) {
		cfg.rate = (uint16_t)atoi(arg); /* raw 24-bit stream only */
		reconfigure();
	} else if (!strcmp(line, "gain") && arg && ads_gain_ok((uint8_t)atoi(arg))) {
		cfg.gain = (uint8_t)atoi(arg);
		reconfigure();
	} else if (!strcmp(line, "fmt") && arg && (atoi(arg) == 16 || atoi(arg) == 24)) {
		cfg.fmt = atoi(arg) == 16 ? FMT_I16 : FMT_I24;
		reconfigure();
	} else if (!strcmp(line, "hp") && arg && (atoi(arg) == 20 || atoi(arg) == 40)) {
		cfg.hp_idx = atoi(arg) == 40;
		reconfigure();
	} else if ((!strcmp(line, "test") || !strcmp(line, "short")) && arg &&
		   (!strcmp(arg, "on") || !strcmp(arg, "off"))) {
		cfg.mux = !strcmp(arg, "off") ? ADS_MUX_NORMAL
			  : !strcmp(line, "test") ? ADS_MUX_TEST : ADS_MUX_SHORT;
		reconfigure();
	} else if (!strcmp(line, "leadoff") && arg && (!strcmp(arg, "on") || !strcmp(arg, "off"))) {
		cfg.leadoff = !strcmp(arg, "on");
		reconfigure();
	} else if (!strcmp(line, "rld") && arg) {
		cfg.rld_mask = (uint8_t)strtoul(arg, NULL, 0); /* e.g. "rld 0x03", "rld 0" */
		reconfigure();
	} else if (!strcmp(line, "status")) {
		/* just refresh */
	} else if (!strcmp(line, "off")) {
		power_off();
	} else {
		err = -EINVAL;
	}
	/* "err:" + at most 19 chars of the command: the label is cut on purpose */
	snprintk(last, sizeof(last), "%s:%.*s", err ? "err" : "ok", (int)sizeof(last) - 5, line);
	if (err) {
		LOG_WRN("command '%s' failed (%d)", line, err);
	}
	led_update();
	status_publish();
}

static void cmd_work_fn(struct k_work *w)
{
	char line[40];

	ARG_UNUSED(w);
	while (k_msgq_get(&cmd_q, line, K_NO_WAIT) == 0) {
		handle(line);
	}
}
static K_WORK_DEFINE(cmd_work, cmd_work_fn);

void app_command(const char *cmd, size_t len)
{
	char line[40];

	len = MIN(len, sizeof(line) - 1);
	memcpy(line, cmd, len);
	line[len] = '\0';
	for (size_t i = 0; i < len; i++) { /* tolerate "start\n" */
		if (line[i] == '\r' || line[i] == '\n') {
			line[i] = '\0';
		}
	}
	if (k_msgq_put(&cmd_q, line, K_NO_WAIT) == 0) {
		k_work_submit_to_queue(&app_wq, &cmd_work);
	}
}

static void conn_work_fn(struct k_work *w)
{
	ARG_UNUSED(w);
	if (connected_flag) {
		afe_on(); /* ~0.6 s; status shows the ADS ID right after connecting */
	} else {
		afe_off();
	}
	led_update();
	status_publish();
}
static K_WORK_DEFINE(conn_work, conn_work_fn);

void app_on_connect(void)
{
	connected_flag = true;
	idle_s = 0;
	k_work_submit_to_queue(&app_wq, &conn_work);
}

void app_on_disconnect(void)
{
	connected_flag = false;
	k_work_submit_to_queue(&app_wq, &conn_work);
}

/* ------------------------------------------------------------------ charger interlock */
static void chg_work_fn(struct k_work *w)
{
	ARG_UNUSED(w);
	bool now = gpio_pin_get_dt(&chg) == 1;

	if (now != charging) {
		charging = now;
		LOG_INF("charger %s", now ? "connected" : "removed");
	}
	if (charging) {
		afe_off(); /* safety interlock: AFE powered down, no streaming while charging */
	} else if (connected_flag && !ads_is_powered()) {
		afe_on();
	}
	led_update();
	status_publish();
}
static K_WORK_DEFINE(chg_work, chg_work_fn);
static struct gpio_callback chg_cb;

static void chg_isr(const struct device *d, struct gpio_callback *cb, uint32_t pins)
{
	ARG_UNUSED(d);
	ARG_UNUSED(cb);
	ARG_UNUSED(pins);
	charging = gpio_pin_get_dt(&chg) == 1; /* block streaming at once, then clean up */
	k_work_submit_to_queue(&app_wq, &chg_work);
}

/* ------------------------------------------------------------------ button */
static bool btn_down;
static void long_work_fn(struct k_work *w)
{
	ARG_UNUSED(w);
	if (gpio_pin_get_dt(&button) == 1) {
		power_off();
	}
}
static K_WORK_DELAYABLE_DEFINE(long_work, long_work_fn);

static void btn_work_fn(struct k_work *w)
{
	ARG_UNUSED(w);
	bool pressed = gpio_pin_get_dt(&button) == 1;

	if (pressed && !btn_down) {
		if (acq_running()) {
			acq_marker(); /* PF_MARKER in the next packet */
		}
		idle_s = 0;
		k_work_reschedule_for_queue(&app_wq, &long_work, K_MSEC(LONG_PRESS_MS));
	} else if (!pressed && btn_down) {
		k_work_cancel_delayable(&long_work);
	}
	btn_down = pressed;
}
static K_WORK_DELAYABLE_DEFINE(btn_work, btn_work_fn);
static struct gpio_callback btn_cb;

static void btn_isr(const struct device *d, struct gpio_callback *cb, uint32_t pins)
{
	ARG_UNUSED(d);
	ARG_UNUSED(cb);
	ARG_UNUSED(pins);
	k_work_reschedule_for_queue(&app_wq, &btn_work, K_MSEC(20)); /* debounce */
}

/* ------------------------------------------------------------------ battery */
static void vbat_read(void)
{
	int16_t raw = 0;
	struct adc_sequence seq = {.buffer = &raw, .buffer_size = sizeof(raw)};

	adc_sequence_init_dt(&vbat_adc, &seq);
	if (adc_read(vbat_adc.dev, &seq) != 0) {
		return;
	}
	int32_t mv = MAX(raw, 0);

	adc_raw_to_millivolts_dt(&vbat_adc, &mv);
	vbat_mv = (uint16_t)(mv * 2); /* 1M/1M divider */
	low_bat = vbat_mv < VBAT_LOW_MV;
	crit_count = vbat_mv < VBAT_CRIT_MV ? crit_count + 1 : 0;
}

/* ------------------------------------------------------------------ 1 s tick */
static void tick_fn(struct k_work *w);
static K_WORK_DELAYABLE_DEFINE(tick_work, tick_fn);

static void tick_fn(struct k_work *w)
{
	static int n;

	ARG_UNUSED(w);
	if (n++ % 5 == 0) {
		vbat_read();
		status_publish();
	}
	if (crit_count >= 3 && !charging) {
		LOG_WRN("battery critical (%u mV)", vbat_mv);
		power_off();
	}
	k_work_submit_to_queue(&app_wq, &chg_work); /* poll as well as the interrupt */
	if (!connected_flag && !acq_running() && !charging) {
		if (++idle_s >= IDLE_OFF_S) {
			power_off();
		}
	} else {
		idle_s = 0;
	}
	led_update();
	k_work_reschedule_for_queue(&app_wq, &tick_work, K_SECONDS(1));
}

/* ------------------------------------------------------------------ System OFF */
static void power_off(void)
{
	LOG_INF("System OFF");
	acq_stop();
	ads_prepare_off(); /* ADS in power-down (PWDN/RESET low, retained in System OFF) */
	k_timer_stop(&led_timer);
	gpio_pin_set_dt(&led, 1);
	k_msleep(500);
	gpio_pin_set_dt(&led, 0);
	/* Wake sources must be inactive now, or the chip wakes up at once. */
	while (gpio_pin_get_dt(&button) == 1) {
		k_msleep(20);
	}
	gpio_pin_interrupt_configure_dt(&button, GPIO_INT_LEVEL_ACTIVE); /* SENSE low */
	if (gpio_pin_get_dt(&chg) == 0) {
		gpio_pin_interrupt_configure_dt(&chg, GPIO_INT_LEVEL_ACTIVE); /* wake on charger */
	} else {
		gpio_pin_interrupt_configure_dt(&chg, GPIO_INT_DISABLE);
	}
	sys_poweroff();
}

int main(void)
{
	k_work_queue_start(&app_wq, app_wq_stack, K_THREAD_STACK_SIZEOF(app_wq_stack),
			   K_PRIO_PREEMPT(4), NULL);

	gpio_pin_configure_dt(&led, GPIO_OUTPUT_INACTIVE);
	if (acq_init() != 0) {
		LOG_ERR("ADS1298 SPI/GPIO not ready");
	}
	gpio_pin_configure_dt(&button, GPIO_INPUT);
	gpio_pin_configure_dt(&chg, GPIO_INPUT);
	gpio_init_callback(&btn_cb, btn_isr, BIT(button.pin));
	gpio_add_callback(button.port, &btn_cb);
	gpio_pin_interrupt_configure_dt(&button, GPIO_INT_EDGE_BOTH);
	gpio_init_callback(&chg_cb, chg_isr, BIT(chg.pin));
	gpio_add_callback(chg.port, &chg_cb);
	gpio_pin_interrupt_configure_dt(&chg, GPIO_INT_EDGE_BOTH);
	charging = gpio_pin_get_dt(&chg) == 1;
	btn_down = gpio_pin_get_dt(&button) == 1; /* the wake press is not a marker */

	if (adc_is_ready_dt(&vbat_adc) && adc_channel_setup_dt(&vbat_adc) == 0) {
		vbat_read();
	}
	for (int i = 0; i < 3; i++) { /* hello: three quick flashes */
		gpio_pin_set_dt(&led, 1);
		k_msleep(60);
		gpio_pin_set_dt(&led, 0);
		k_msleep(120);
	}
	ble_init();
	led_update();
	k_timer_start(&led_timer, K_MSEC(50), K_MSEC(50));
	k_work_reschedule_for_queue(&app_wq, &tick_work, K_SECONDS(1));
	LOG_INF("neurband %s up, vbat %u mV, charging %d", FW_VERSION, vbat_mv, charging);
	return 0;
}
