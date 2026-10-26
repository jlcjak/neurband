/* Shared state between the modules of the neurband rev C firmware. */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define FW_VERSION "c0.1"

enum stream_fmt { FMT_I16 = 0, FMT_I24 = 1 };

struct nb_cfg {
	uint16_t rate;    /* ADS rate for the raw 24-bit stream (FMT_I24): 2000 or 4000 */
	uint8_t gain;     /* PGA gain 1, 2, 3, 4, 6, 8, 12 */
	uint8_t fmt;      /* enum stream_fmt. FMT_I16 always acquires at 4 kSPS, streams 2 kSPS */
	uint8_t hp_idx;   /* FMT_I16 high-pass: 0 = 20 Hz, 1 = 40 Hz */
	uint8_t mux;      /* enum ads_mux */
	bool leadoff;
	uint8_t rld_mask; /* RLD sense set (P and N of each selected channel) */
};
extern struct nb_cfg cfg; /* main.c; only changed while acquisition is stopped */

static inline uint16_t cfg_ads_rate(const struct nb_cfg *c)
{
	return c->fmt == FMT_I16 ? 4000 : c->rate;
}

/* acq.c: DRDY -> frame ring -> DSP/packetizer -> packet queue */
int acq_init(void);
int acq_start(uint16_t max_payload);
void acq_stop(void);
bool acq_running(void);
void acq_marker(void);
uint8_t acq_rld_active(void);
uint32_t acq_overruns(void);
uint32_t acq_drops(void);
uint32_t acq_status_errors(void);
int acq_get_packet(uint8_t *buf, uint16_t *len); /* blocks; for the BLE TX thread */
uint32_t acq_sample_now(void); /* stream sample index of the newest ADS conversion (ISR-safe) */
void acq_queue_packet(uint8_t type, uint8_t n, uint32_t sample, uint8_t flags, uint8_t lp,
		      uint8_t ln, const void *body, uint16_t body_len);

/* imu.c: LSM6DSL, runs only while streaming */
int imu_init(void);
bool imu_present(void);
void imu_start(void);
void imu_stop(void);

/* ble.c */
int ble_init(void);
bool ble_connected(void);
uint16_t ble_max_payload(void);
void ble_set_status(const char *s);
void ble_link_info(char *buf, size_t len);

/* main.c */
void app_command(const char *cmd, size_t len); /* from the control characteristic */
void app_on_connect(void);
void app_on_disconnect(void);
bool app_charging(void);
bool app_low_battery(void);
uint16_t app_vbat_mv(void);
