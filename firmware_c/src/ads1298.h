/* Minimal ADS1298 driver for rev C (one chip, SPI mode 1, internal clock and reference).
 * Section/table numbers refer to TI SBAS459K (docs/datasheets/ads1298.txt). */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define ADS_FRAME_BYTES 27   /* 24-bit status + 8 x 24-bit channels (9.4.1.3) */
#define ADS_ID_ADS1298  0x92 /* 9.6.1.1: 100 (ADS129x) 10 (fixed) 010 (8 channels) */

enum ads_mux { ADS_MUX_NORMAL = 0x0, ADS_MUX_SHORT = 0x1, ADS_MUX_TEST = 0x5 }; /* CHnSET[2:0] */

struct ads_settings {
	uint16_t rate;     /* 2000 or 4000 SPS (HR mode) */
	uint8_t gain;      /* 1, 2, 3, 4, 6, 8, 12 */
	uint8_t mux;       /* enum ads_mux, all channels */
	bool leadoff;      /* DC lead-off, 6 nA, comparators at 95 % */
	uint8_t rld_mask;  /* channels whose P and N inputs feed the bias (RLD) amplifier */
};

int ads_init(void (*drdy_handler)(void));  /* GPIO + SPI; leaves the chip powered down */
int ads_power_up(void);                    /* PWDN high, reset, ID check, reference on */
void ads_power_down(void);                 /* START low, PWDN/RESET low */
bool ads_is_powered(void);
uint8_t ads_id(void);
bool ads_gain_ok(uint8_t gain);
int ads_configure(const struct ads_settings *s); /* stopped only; returns # read-back errors */
void ads_stream_start(void);               /* RDATAC, START high, DRDY interrupt on */
void ads_stream_stop(void);                /* DRDY interrupt off, START low, SDATAC */
int ads_read_frame(uint8_t frame[ADS_FRAME_BYTES]); /* in RDATAC, after DRDY fell */
int ads_set_rld_streaming(uint8_t mask);   /* between two frames while streaming */
void ads_prepare_off(void);                /* pins to low-power state before System OFF */
