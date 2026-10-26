/* ADS1298 driver. Register values and timing: TI SBAS459K (docs/datasheets/ads1298.txt).
 * Rev C wiring: CLKSEL high (internal 2.048 MHz oscillator, CLK pin unused), PWDN and RESET
 * tied together on ADC_PWDN, RLDREF pin open, AVDD = DVDD = 3.3 V, GPIO1-4 tied to GND. */
#include "ads1298.h"

#include <errno.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/pm/device.h>
#include <zephyr/version.h>

#ifndef NEURBAND_RLDREF_EXTERNAL
#define NEURBAND_RLDREF_EXTERNAL 1 /* rev C: 2x1M + 1uF divider on RLDREF (pin 60) */
#endif
#define CONFIG3_VAL (NEURBAND_RLDREF_EXTERNAL ? 0xC4 : 0xCC)

LOG_MODULE_REGISTER(ads1298, LOG_LEVEL_INF);

#define ADS_NODE DT_NODELABEL(ads1298)

/* Registers (9.6, Table 15/16) and opcodes (9.5.2) */
enum {
	REG_ID = 0x00, REG_CONFIG1 = 0x01, REG_CONFIG2 = 0x02, REG_CONFIG3 = 0x03, REG_LOFF = 0x04,
	REG_CH1SET = 0x05, REG_RLD_SENSP = 0x0D, REG_RLD_SENSN = 0x0E, REG_LOFF_SENSP = 0x0F,
	REG_LOFF_SENSN = 0x10, REG_LOFF_FLIP = 0x11, REG_CONFIG4 = 0x17, REG_WCT1 = 0x18, REG_WCT2 = 0x19,
};
enum {
	OP_RESET = 0x06, OP_RDATAC = 0x10, OP_SDATAC = 0x11, OP_RREG = 0x20, OP_WREG = 0x40,
};

/* Mode 1 (CPOL 0, CPHA 1), 9.5.1. */
#define ADS_SPI_OP (SPI_WORD_SET(8) | SPI_TRANSFER_MSB | SPI_MODE_CPHA | SPI_OP_MODE_MASTER)
#if defined(ZEPHYR_VERSION_CODE) && ZEPHYR_VERSION_CODE >= ZEPHYR_VERSION(4, 3, 0)
static const struct spi_dt_spec spec = SPI_DT_SPEC_GET(ADS_NODE, ADS_SPI_OP);
#else
static const struct spi_dt_spec spec = SPI_DT_SPEC_GET(ADS_NODE, ADS_SPI_OP, 3);
#endif
static const struct gpio_dt_spec drdy = GPIO_DT_SPEC_GET(ADS_NODE, drdy_gpios);
static const struct gpio_dt_spec start = GPIO_DT_SPEC_GET(ADS_NODE, start_gpios);
static const struct gpio_dt_spec pwdn = GPIO_DT_SPEC_GET(ADS_NODE, pwdn_gpios);

/* Register access at 1 MHz: 8 us per byte is longer than the 4 tCLK (~2 us) a multi-byte
 * command needs between bytes (9.5.2.9), so no inter-byte delays. Frame reads at 8 MHz:
 * 27 bytes = 27 us of the 250 us frame at 4 kSPS (fSCLK max 20 MHz, 7.6). */
static struct spi_config cfg_slow, cfg_fast;
static struct gpio_callback drdy_cb;
static void (*drdy_fn)(void);
static bool powered;
static uint8_t chip_id;

static void drdy_isr(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
	ARG_UNUSED(dev);
	ARG_UNUSED(cb);
	ARG_UNUSED(pins);
	drdy_fn();
}

static int xfer(const struct spi_config *c, const uint8_t *tx, uint8_t *rx, size_t n)
{
	/* n >= 2 always: nRF52832 PAN 58 clocks out an extra byte on 1-byte SPIM transfers. */
	const struct spi_buf tb = {.buf = (void *)tx, .len = n};
	const struct spi_buf rb = {.buf = rx, .len = n};
	const struct spi_buf_set ts = {.buffers = &tb, .count = 1};
	const struct spi_buf_set rs = {.buffers = &rb, .count = 1};

	return spi_transceive(spec.bus, c, &ts, &rs);
}

static void command(uint8_t op)
{
	/* opcode + one 0x00 pad byte: the device ignores DIN = 0 (9.4.1.3 keeps DIN low) */
	uint8_t tx[2] = {op, 0x00}, rx[2];

	xfer(&cfg_slow, tx, rx, sizeof(tx));
	k_busy_wait(4); /* tSDECODE before the next command */
}

static void wreg(uint8_t reg, uint8_t val)
{
	uint8_t tx[3] = {OP_WREG | reg, 0x00, val}, rx[3]; /* 9.5.2.11: 1 register */

	xfer(&cfg_slow, tx, rx, sizeof(tx));
}

static uint8_t rreg(uint8_t reg)
{
	uint8_t tx[3] = {OP_RREG | reg, 0x00, 0x00}, rx[3] = {0}; /* 9.5.2.10 */

	xfer(&cfg_slow, tx, rx, sizeof(tx));
	return rx[2];
}

int ads_init(void (*drdy_handler)(void))
{
	if (!spi_is_ready_dt(&spec) || !gpio_is_ready_dt(&drdy) || !gpio_is_ready_dt(&start) ||
	    !gpio_is_ready_dt(&pwdn)) {
		return -ENODEV;
	}
	/* Power-down first: 11.1 wants digital inputs low until the chip is set up. */
	gpio_pin_configure_dt(&pwdn, GPIO_OUTPUT_ACTIVE);
	gpio_pin_configure_dt(&start, GPIO_OUTPUT_INACTIVE);
	gpio_pin_configure_dt(&drdy, GPIO_INPUT);
	drdy_fn = drdy_handler;
	gpio_init_callback(&drdy_cb, drdy_isr, BIT(drdy.pin));
	gpio_add_callback(drdy.port, &drdy_cb);

	cfg_fast = spec.config;
	cfg_fast.cs.delay = 3; /* us; tSCCS = 4 tCLK (1.95 us) from last SCLK to CS high (7.6) */
	cfg_slow = cfg_fast;
	cfg_slow.frequency = 1000000;
	powered = false;
	return 0;
}

bool ads_is_powered(void)
{
	return powered;
}

uint8_t ads_id(void)
{
	return chip_id;
}

int ads_power_up(void)
{
	gpio_pin_set_dt(&start, 0);
	gpio_pin_set_dt(&pwdn, 0); /* PWDN and RESET high: oscillator and reference start (9.3.2.2) */
	powered = true;
	/* 11.1 / Table 38: wait tPOR = 2^18 tCLK = 128 ms and until VCAP1 (22 uF) > 1.1 V. */
	k_msleep(300);
	command(OP_SDATAC); /* the device powers up in RDATAC, which ignores register commands */
	command(OP_RESET);  /* 9.5.2.3 */
	k_busy_wait(20);    /* 18 tCLK = 9 us to finish the reset */
	command(OP_SDATAC);
	chip_id = rreg(REG_ID);
	/* CONFIG3 (9.6.1.4): PD_REFBUF=1 internal reference on, bit 6 must be 1,
	 * VREF_4V=0 -> 2.4 V (AVDD 3.3 V), PD_RLD=1, and RLDREF_INT:
	 *   0 (0xC4) = bias reference from the RC-filtered AVDD/2 divider on the RLDREF pin (rev C board),
	 *   1 (0xCC) = internal (AVDD+AVSS)/2 (no divider fitted). The external one keeps radio bursts
	 *   on AVDD out of the body bias (docs/science/simulations.md, Q4). */
	wreg(REG_CONFIG3, CONFIG3_VAL);
	k_msleep(300); /* VREFP (10 uF + 100 nF) settling, 9.3.1.6 */
	LOG_INF("ADS1298 ID 0x%02x", chip_id);
	return chip_id == ADS_ID_ADS1298 ? 0 : -ENODEV;
}

void ads_power_down(void)
{
	gpio_pin_interrupt_configure_dt(&drdy, GPIO_INT_DISABLE);
	gpio_pin_set_dt(&start, 0);
	gpio_pin_set_dt(&pwdn, 1); /* 9.3.2.2: all circuitry off; RESET low also clears registers */
	powered = false;
}

bool ads_gain_ok(uint8_t g)
{
	return g == 1 || g == 2 || g == 3 || g == 4 || g == 6 || g == 8 || g == 12;
}

static uint8_t gain_code(uint8_t g)
{
	/* CHnSET GAIN[2:0] (9.6.1.6): 000=6 001=1 010=2 011=3 100=4 101=8 110=12 */
	switch (g) {
	case 1: return 1;
	case 2: return 2;
	case 3: return 3;
	case 4: return 4;
	case 8: return 5;
	case 12: return 6;
	default: return 0;
	}
}

int ads_configure(const struct ads_settings *s)
{
	const uint8_t chset = (uint8_t)(gain_code(s->gain) << 4) | s->mux; /* PDn=0: channel on */
	const struct { uint8_t reg, val; } regs[] = {
		/* CONFIG1 (9.6.1.2): HR=1 high-resolution mode, DAISY_EN=0, CLK_EN=0 (CLK pin not
		 * used), DR=011 -> fMOD/128 = 4 kSPS, DR=100 -> 2 kSPS (HR, 24-bit data both). */
		{REG_CONFIG1, (uint8_t)(0x80 | (s->rate == 4000 ? 0x03 : 0x04))},
		/* CONFIG2 (9.6.1.3): INT_TEST=1 internal test source, TEST_AMP=0 (1 x VREF/2400),
		 * TEST_FREQ=00 (fCLK/2^21 ~ 0.98 Hz square). Bits 7:6 written 0. */
		{REG_CONFIG2, (uint8_t)(s->mux == ADS_MUX_TEST ? 0x10 : 0x00)},
		{REG_CONFIG3, CONFIG3_VAL}, /* see ads_power_up */
		/* LOFF (9.6.1.5): COMP_TH=000 (95 %/5 %), VLEAD_OFF_EN=0 (current source),
		 * ILEAD_OFF=00 (6 nA, least DC error on dry contacts), FLEAD_OFF=11 (DC). */
		{REG_LOFF, (uint8_t)(s->leadoff ? 0x03 : 0x00)},
		{REG_CH1SET + 0, chset}, {REG_CH1SET + 1, chset}, {REG_CH1SET + 2, chset},
		{REG_CH1SET + 3, chset}, {REG_CH1SET + 4, chset}, {REG_CH1SET + 5, chset},
		{REG_CH1SET + 6, chset}, {REG_CH1SET + 7, chset},
		/* RLD_SENSP/N (9.6.1.7/8): only the selected healthy channels drive the bias loop
		 * (docs/science/signal_chain.md section 3: all 16 senses risk instability).
		 * With mask 0 the amplifier just holds the body at RLDREF = mid-supply. */
		{REG_RLD_SENSP, s->rld_mask}, {REG_RLD_SENSN, s->rld_mask},
		/* LOFF_SENSP/N (9.6.1.9/10): lead-off current on all inputs when enabled */
		{REG_LOFF_SENSP, (uint8_t)(s->leadoff ? 0xFF : 0x00)},
		{REG_LOFF_SENSN, (uint8_t)(s->leadoff ? 0xFF : 0x00)},
		{REG_LOFF_FLIP, 0x00}, /* 9.6.1.11: default polarity */
		/* CONFIG4 (9.6.1.17): SINGLE_SHOT=0, PD_LOFF_COMP=1 only with lead-off */
		{REG_CONFIG4, (uint8_t)(s->leadoff ? 0x02 : 0x00)},
		{REG_WCT1, 0x00}, {REG_WCT2, 0x00}, /* 9.6.1.18/19: WCT amplifiers off */
	};
	int errors = 0;

	if (!powered || !ads_gain_ok(s->gain) || (s->rate != 2000 && s->rate != 4000)) {
		return -EINVAL;
	}
	for (size_t i = 0; i < ARRAY_SIZE(regs); i++) {
		wreg(regs[i].reg, regs[i].val);
	}
	for (size_t i = 0; i < ARRAY_SIZE(regs); i++) {
		/* CONFIG3 bit 0 is the read-only RLD_STAT; CONFIG2[7:6] read-back is unspecified */
		uint8_t mask = regs[i].reg == REG_CONFIG3 ? 0xFE : regs[i].reg == REG_CONFIG2 ? 0x3F : 0xFF;

		if ((rreg(regs[i].reg) ^ regs[i].val) & mask) {
			errors++;
		}
	}
	if (errors) {
		LOG_WRN("%d register read-back errors", errors);
	}
	return errors;
}

void ads_stream_start(void)
{
	command(OP_RDATAC); /* 9.5.2.6: frames shift out after each DRDY without an opcode */
	gpio_pin_interrupt_configure_dt(&drdy, GPIO_INT_EDGE_TO_ACTIVE); /* falling edge */
	gpio_pin_set_dt(&start, 1); /* 9.4.1.1: conversions start on START high */
}

void ads_stream_stop(void)
{
	gpio_pin_interrupt_configure_dt(&drdy, GPIO_INT_DISABLE);
	gpio_pin_set_dt(&start, 0);
	k_busy_wait(600); /* let a conversion in flight finish (500 us at 2 kSPS) */
	command(OP_SDATAC); /* 9.5.2.7 */
}

int ads_read_frame(uint8_t frame[ADS_FRAME_BYTES])
{
	static const uint8_t zeros[ADS_FRAME_BYTES]; /* DIN low for the whole read (9.4.1.3) */

	return xfer(&cfg_fast, zeros, frame, ADS_FRAME_BYTES);
}

int ads_set_rld_streaming(uint8_t mask)
{
	/* Registers can't be written in RDATAC mode (9.5.2.6): leave it, write, re-enter.
	 * ~90 us at 1 MHz, done right after a frame read so it ends before the next DRDY. */
	command(OP_SDATAC);
	wreg(REG_RLD_SENSP, mask);
	wreg(REG_RLD_SENSN, mask);
	command(OP_RDATAC);
	return 0;
}

void ads_prepare_off(void)
{
	ads_power_down();
	gpio_pin_configure_dt(&drdy, GPIO_DISCONNECTED); /* DRDY floats with the chip off */
#if defined(CONFIG_PM_DEVICE)
	pm_device_action_run(spec.bus, PM_DEVICE_ACTION_SUSPEND); /* SPI pins -> sleep state */
#endif
}
