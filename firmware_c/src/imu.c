/* ST LSM6DSL accelerometer + gyroscope on I2C (raw registers, LSM6DSL datasheet DocID028475,
 * section 9 "Register description"). 208 Hz, data-ready pulses on INT1. The INT1 interrupt
 * latches the ADS conversion counter (acq_sample_now), so each IMU sample is timestamped on
 * the EMG sample clock; the I2C read happens afterwards in a thread. */
#include <string.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/sys/byteorder.h>

#include "app.h"
#include "packet.h"

LOG_MODULE_REGISTER(imu, LOG_LEVEL_INF);

#define IMU_NODE DT_NODELABEL(lsm6dsl)

enum {
	REG_DRDY_PULSE_CFG_G = 0x0B, REG_INT1_CTRL = 0x0D, REG_WHO_AM_I = 0x0F, REG_CTRL1_XL = 0x10,
	REG_CTRL2_G = 0x11, REG_CTRL3_C = 0x12, REG_OUTX_L_G = 0x22,
};
#define WHO_AM_I_LSM6DSL 0x6A

static const struct i2c_dt_spec bus = I2C_DT_SPEC_GET(IMU_NODE);
static const struct gpio_dt_spec irq = GPIO_DT_SPEC_GET(IMU_NODE, irq_gpios);
static struct gpio_callback irq_cb;
static K_SEM_DEFINE(imu_sem, 0, 16);
static uint32_t ts[16]; /* sample index latched per INT1 pulse */
static atomic_t ts_head, ts_tail, active;
static bool present;

static void irq_isr(const struct device *d, struct gpio_callback *cb, uint32_t pins)
{
	ARG_UNUSED(d);
	ARG_UNUSED(cb);
	ARG_UNUSED(pins);
	atomic_val_t h = atomic_get(&ts_head);

	if (!atomic_get(&active) || (uint32_t)(h - atomic_get(&ts_tail)) >= ARRAY_SIZE(ts)) {
		return;
	}
	ts[(uint32_t)h % ARRAY_SIZE(ts)] = acq_sample_now();
	atomic_set(&ts_head, h + 1);
	k_sem_give(&imu_sem);
}

static int wr(uint8_t reg, uint8_t val)
{
	return i2c_reg_write_byte_dt(&bus, reg, val);
}

bool imu_present(void)
{
	return present;
}

int imu_init(void)
{
	uint8_t id = 0;

	if (!i2c_is_ready_dt(&bus) || !gpio_is_ready_dt(&irq) ||
	    i2c_reg_read_byte_dt(&bus, REG_WHO_AM_I, &id) != 0 || id != WHO_AM_I_LSM6DSL) {
		LOG_WRN("LSM6DSL not found (WHO_AM_I 0x%02x)", id);
		return -ENODEV;
	}
	wr(REG_CTRL3_C, 0x01); /* SW_RESET */
	k_msleep(1);
	wr(REG_CTRL1_XL, 0x00); /* both sensors in power-down until streaming */
	wr(REG_CTRL2_G, 0x00);
	gpio_pin_configure_dt(&irq, GPIO_INPUT);
	gpio_init_callback(&irq_cb, irq_isr, BIT(irq.pin));
	gpio_add_callback(irq.port, &irq_cb);
	present = true;
	return 0;
}

void imu_start(void)
{
	if (!present) {
		return;
	}
	atomic_set(&ts_head, 0);
	atomic_set(&ts_tail, 0);
	k_sem_reset(&imu_sem);
	wr(REG_CTRL3_C, 0x44);          /* BDU=1 (no torn samples), IF_INC=1 (burst reads) */
	wr(REG_DRDY_PULSE_CFG_G, 0x80); /* DRDY_PULSED: 75 us pulse per sample, never stuck high */
	wr(REG_INT1_CTRL, 0x01);        /* INT1_DRDY_XL */
	wr(REG_CTRL1_XL, 0x58);         /* ODR 208 Hz, +-4 g (0.122 mg/LSB) */
	wr(REG_CTRL2_G, 0x54);          /* ODR 208 Hz, +-500 dps (17.5 mdps/LSB) */
	atomic_set(&active, 1);
	gpio_pin_interrupt_configure_dt(&irq, GPIO_INT_EDGE_TO_ACTIVE);
}

void imu_stop(void)
{
	if (!present) {
		return;
	}
	atomic_set(&active, 0);
	gpio_pin_interrupt_configure_dt(&irq, GPIO_INT_DISABLE);
	wr(REG_CTRL1_XL, 0x00); /* power-down: ~3 uA */
	wr(REG_CTRL2_G, 0x00);
	k_sem_give(&imu_sem); /* let the thread drop its partial packet */
}

static void imu_thread(void *a, void *b, void *c)
{
	ARG_UNUSED(a);
	ARG_UNUSED(b);
	ARG_UNUSED(c);
	static struct pkt_imu_sample buf[PKT_IMU_MAX_SAMPLES];
	uint32_t first = 0;
	uint8_t n = 0;

	for (;;) {
		k_sem_take(&imu_sem, K_FOREVER);
		if (!atomic_get(&active)) {
			n = 0;
			continue;
		}
		while (atomic_get(&ts_tail) != atomic_get(&ts_head)) {
			atomic_val_t t = atomic_get(&ts_tail);
			uint32_t idx = ts[(uint32_t)t % ARRAY_SIZE(ts)];
			uint8_t raw[12];

			atomic_set(&ts_tail, t + 1);
			if (i2c_burst_read_dt(&bus, REG_OUTX_L_G, raw, sizeof(raw)) != 0) {
				continue;
			}
			if (n == 0) {
				first = idx;
			}
			buf[n].dt = sys_cpu_to_le16((uint16_t)(idx - first));
			memcpy(buf[n].g, raw, sizeof(raw)); /* OUTX_L_G..OUTZ_H_XL, little-endian */
			if (++n == PKT_IMU_MAX_SAMPLES || idx - first > 60000) {
				acq_queue_packet(PKT_IMU, n, first, 0, 0, 0, buf, n * sizeof(buf[0]));
				n = 0;
			}
		}
	}
}
K_THREAD_DEFINE(imu_tid, 1024, imu_thread, NULL, NULL, NULL, K_PRIO_PREEMPT(2), 0, 0);
