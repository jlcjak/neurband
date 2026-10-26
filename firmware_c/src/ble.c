/* BLE: advertising, the neurband GATT service, link tuning (2M PHY, DLE, MTU) and the
 * notification TX thread. UUIDs: 4e420c0X-6e65-7572-6261-6e6420726576 ("neurband rev"). */
#include <errno.h>
#include <string.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/printk.h>
#include <zephyr/version.h>

#include "app.h"
#include "packet.h"

LOG_MODULE_REGISTER(ble, LOG_LEVEL_INF);

#define NB_UUID(n) BT_UUID_128_ENCODE(0x4e420c00 + (n), 0x6e65, 0x7572, 0x6261, 0x6e6420726576ULL)

static const struct bt_uuid_128 svc_uuid = BT_UUID_INIT_128(NB_UUID(0));
static const struct bt_uuid_128 data_uuid = BT_UUID_INIT_128(NB_UUID(1));
static const struct bt_uuid_128 ctrl_uuid = BT_UUID_INIT_128(NB_UUID(2));
static const struct bt_uuid_128 status_uuid = BT_UUID_INIT_128(NB_UUID(3));

static struct bt_conn *conn;
static K_MUTEX_DEFINE(conn_mtx);
static bool data_notify, status_notify;
static uint16_t ci, dle_tx;
static uint8_t phy_tx;
static char status[200];
static K_MUTEX_DEFINE(status_mtx);

static ssize_t ctrl_write(struct bt_conn *c, const struct bt_gatt_attr *attr, const void *buf,
			  uint16_t len, uint16_t offset, uint8_t flags)
{
	ARG_UNUSED(c);
	ARG_UNUSED(attr);
	ARG_UNUSED(flags);
	if (offset != 0) {
		return BT_GATT_ERR(BT_ATT_ERR_INVALID_OFFSET);
	}
	app_command(buf, len);
	return len;
}

static ssize_t status_read(struct bt_conn *c, const struct bt_gatt_attr *attr, void *buf,
			   uint16_t len, uint16_t offset)
{
	char tmp[sizeof(status)];

	k_mutex_lock(&status_mtx, K_FOREVER);
	strcpy(tmp, status);
	k_mutex_unlock(&status_mtx);
	return bt_gatt_attr_read(c, attr, buf, len, offset, tmp, strlen(tmp));
}

static void data_ccc(const struct bt_gatt_attr *attr, uint16_t value)
{
	ARG_UNUSED(attr);
	data_notify = value == BT_GATT_CCC_NOTIFY;
}

static void status_ccc(const struct bt_gatt_attr *attr, uint16_t value)
{
	ARG_UNUSED(attr);
	status_notify = value == BT_GATT_CCC_NOTIFY;
}

/* attrs: 0 service, 1/2 data, 3 data CCC, 4/5 control, 6/7 status, 8 status CCC */
BT_GATT_SERVICE_DEFINE(nb_svc,
	BT_GATT_PRIMARY_SERVICE(&svc_uuid),
	BT_GATT_CHARACTERISTIC(&data_uuid.uuid, BT_GATT_CHRC_NOTIFY, BT_GATT_PERM_NONE,
			       NULL, NULL, NULL),
	BT_GATT_CCC(data_ccc, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),
	BT_GATT_CHARACTERISTIC(&ctrl_uuid.uuid, BT_GATT_CHRC_WRITE | BT_GATT_CHRC_WRITE_WITHOUT_RESP,
			       BT_GATT_PERM_WRITE, NULL, ctrl_write, NULL),
	BT_GATT_CHARACTERISTIC(&status_uuid.uuid, BT_GATT_CHRC_READ | BT_GATT_CHRC_NOTIFY,
			       BT_GATT_PERM_READ, status_read, NULL, NULL),
	BT_GATT_CCC(status_ccc, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),
);

static const struct bt_data ad[] = {
	BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
	BT_DATA_BYTES(BT_DATA_UUID128_ALL, NB_UUID(0)),
};
static const struct bt_data sd[] = {
	BT_DATA(BT_DATA_NAME_COMPLETE, CONFIG_BT_DEVICE_NAME, sizeof(CONFIG_BT_DEVICE_NAME) - 1),
};

#if defined(ZEPHYR_VERSION_CODE) && ZEPHYR_VERSION_CODE >= ZEPHYR_VERSION(4, 0, 0)
#define ADV_OPT BT_LE_ADV_OPT_CONN
#else
#define ADV_OPT (BT_LE_ADV_OPT_CONNECTABLE | BT_LE_ADV_OPT_ONE_TIME)
#endif
/* 200-250 ms advertising interval (units of 0.625 ms): quick to find, ~0.1 mA average */
static const struct bt_le_adv_param adv_param = BT_LE_ADV_PARAM_INIT(ADV_OPT, 320, 400, NULL);

static void adv_start(void)
{
	int err = bt_le_adv_start(&adv_param, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));

	if (err && err != -EALREADY) {
		LOG_ERR("advertising failed (%d)", err);
	}
}

#if defined(CONFIG_BT_GATT_CLIENT)
static void mtu_cb(struct bt_conn *c, uint8_t err, struct bt_gatt_exchange_params *p)
{
	ARG_UNUSED(p);
	LOG_INF("MTU %u (err %u)", bt_gatt_get_mtu(c), err);
}
static struct bt_gatt_exchange_params mtu_params = {.func = mtu_cb};
#endif

static void connected(struct bt_conn *c, uint8_t err)
{
	if (err) {
		return;
	}
	k_mutex_lock(&conn_mtx, K_FOREVER);
	conn = bt_conn_ref(c);
	k_mutex_unlock(&conn_mtx);
	/* Ask for the fast link right away; the central decides (docs: throughput budget). */
	bt_conn_le_phy_update(c, BT_CONN_LE_PHY_PARAM_2M);
	bt_conn_le_data_len_update(c, BT_LE_DATA_LEN_PARAM_MAX);
#if defined(CONFIG_BT_GATT_CLIENT)
	bt_gatt_exchange_mtu(c, &mtu_params);
#endif
	struct bt_conn_info info;

	if (bt_conn_get_info(c, &info) == 0) {
#if defined(ZEPHYR_VERSION_CODE) && ZEPHYR_VERSION_CODE >= ZEPHYR_VERSION(4, 4, 0)
		ci = (uint16_t)(info.le.interval_us / 1250);
#else
		ci = info.le.interval;
#endif
	}
	LOG_INF("connected");
	app_on_connect();
}

static void disconnected(struct bt_conn *c, uint8_t reason)
{
	ARG_UNUSED(c);
	k_mutex_lock(&conn_mtx, K_FOREVER);
	if (conn) {
		bt_conn_unref(conn);
		conn = NULL;
	}
	k_mutex_unlock(&conn_mtx);
	data_notify = status_notify = false;
	phy_tx = 0;
	dle_tx = 0;
	LOG_INF("disconnected (0x%02x)", reason);
	app_on_disconnect();
}

static void recycled(void)
{
	adv_start();
}

static void param_updated(struct bt_conn *c, uint16_t interval, uint16_t latency, uint16_t timeout)
{
	ARG_UNUSED(c);
	ci = interval;
	LOG_INF("conn interval %u x 1.25 ms, latency %u, timeout %u", interval, latency, timeout);
}

static void phy_updated(struct bt_conn *c, struct bt_conn_le_phy_info *p)
{
	ARG_UNUSED(c);
	phy_tx = p->tx_phy;
	LOG_INF("PHY tx %u rx %u", p->tx_phy, p->rx_phy);
}

static void dle_updated(struct bt_conn *c, struct bt_conn_le_data_len_info *i)
{
	ARG_UNUSED(c);
	dle_tx = i->tx_max_len;
	LOG_INF("data length tx %u rx %u", i->tx_max_len, i->rx_max_len);
}

BT_CONN_CB_DEFINE(conn_cb) = {
	.connected = connected,
	.disconnected = disconnected,
	.recycled = recycled,
	.le_param_updated = param_updated,
	.le_phy_updated = phy_updated,
	.le_data_len_updated = dle_updated,
};

static struct bt_conn *conn_get(void)
{
	struct bt_conn *c = NULL;

	k_mutex_lock(&conn_mtx, K_FOREVER);
	if (conn) {
		c = bt_conn_ref(conn);
	}
	k_mutex_unlock(&conn_mtx);
	return c;
}

bool ble_connected(void)
{
	return conn != NULL;
}

uint16_t ble_max_payload(void)
{
	struct bt_conn *c = conn_get();
	uint16_t mtu = 23;

	if (c) {
		mtu = bt_gatt_get_mtu(c);
		bt_conn_unref(c);
	}
	return MIN(mtu - 3, PKT_MAX_LEN);
}

void ble_link_info(char *buf, size_t len)
{
	snprintk(buf, len, "mtu=%u phy=%s dle=%u ci=%u.%02u", ble_max_payload() + 3,
		 phy_tx == BT_GAP_LE_PHY_2M ? "2M" : phy_tx == BT_GAP_LE_PHY_1M ? "1M" : "?", dle_tx,
		 ci * 125 / 100, ci * 125 % 100);
}

void ble_set_status(const char *s)
{
	k_mutex_lock(&status_mtx, K_FOREVER);
	strncpy(status, s, sizeof(status) - 1);
	status[sizeof(status) - 1] = '\0';
	k_mutex_unlock(&status_mtx);

	struct bt_conn *c = conn_get();

	if (c) {
		if (status_notify && strlen(s) <= (size_t)(bt_gatt_get_mtu(c) - 3)) {
			bt_gatt_notify(c, &nb_svc.attrs[7], s, strlen(s));
		}
		bt_conn_unref(c);
	}
}

/* Sends queued packets. bt_gatt_notify() waits for a free buffer in this thread (or returns
 * -ENOMEM on some versions: retry), which is the backpressure that fills the packet queue. */
static void tx_thread(void *a, void *b, void *p3)
{
	ARG_UNUSED(a);
	ARG_UNUSED(b);
	ARG_UNUSED(p3);
	static uint8_t buf[PKT_MAX_LEN];
	uint16_t len;

	for (;;) {
		acq_get_packet(buf, &len);
		struct bt_conn *c = conn_get();

		if (!c) {
			continue;
		}
		for (int tries = 0; data_notify && tries < 500; tries++) {
			int err = bt_gatt_notify(c, &nb_svc.attrs[2], buf, len);

			if (err != -ENOMEM && err != -ENOBUFS && err != -EAGAIN) {
				break;
			}
			k_sleep(K_MSEC(1));
		}
		bt_conn_unref(c);
	}
}
K_THREAD_DEFINE(tx_tid, 1280, tx_thread, NULL, NULL, NULL, K_PRIO_PREEMPT(3), 0, 0);

int ble_init(void)
{
	int err = bt_enable(NULL);

	if (err) {
		LOG_ERR("bt_enable failed (%d)", err);
		return err;
	}
	adv_start();
	return 0;
}
