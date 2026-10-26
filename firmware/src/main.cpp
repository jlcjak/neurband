// neurband firmware: 16-channel sEMG (2 x ADS1298), streamed over Wi-Fi UDP (on body)
// or USB CDC (off-body bench use only: never with a USB cable while worn).
//
// Tasks:
//   acq  (core 1, high prio): DRDY ISR -> notify -> read both ADS1298 -> fill packet
//   tx   (core 0)           : CRC + send finished packets over UDP or USB CDC
//   loop (core 1, prio 1)   : text commands, marker button, Wi-Fi
#include <Arduino.h>
#include <Preferences.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <stdarg.h>

#include "ads1298.h"
#include "config.h"
#include "packet.h"

// ----------------------------------------------------------------- state
static Ads1298Pair ads(SPI, PIN_ADS_CS_A, PIN_ADS_CS_B, PIN_ADS_START);
static AdsConfig cfg;
static bool ads_ok = false;

enum class Transport : uint8_t { None, Usb, Udp };
static volatile Transport tx_mode = Transport::None;
static IPAddress udp_dest;
static uint16_t udp_dest_port = 0;

struct WifiCfg {
  String ssid, pass, host;
  uint16_t port;
} wcfg;
static WiFiUDP cmd_udp;     // command socket (bound to wcfg.port), used by loop()
static WiFiUDP stream_udp;  // stream socket, used by the tx task only
static bool cmd_udp_up = false;

// Shared between loop() and the acq task (same core; short critical sections).
static portMUX_TYPE shared_mux = portMUX_INITIALIZER_UNLOCKED;
static bool marker_pending = false;

static volatile bool streaming = false;
static volatile bool session_reset = false;  // next start resets seq
static volatile bool flush_partial = false;  // drop a half-filled packet (stream restarted)
static volatile uint32_t fw_drops = 0, missed_drdy = 0, status_errors = 0;
static volatile int64_t drdy_time_us = 0;

static constexpr int NBUF = 24;  // 24 x 990 B ring, ~120 ms of buffering at 4 kSPS
static Packet bufs[NBUF];
static Packet scratch;  // samples land here when no buffer is free (packet dropped)
static QueueHandle_t free_q, full_q;
static TaskHandle_t acq_handle;
static SemaphoreHandle_t ads_mtx, usb_mtx;

// ----------------------------------------------------------------- CRC-32 (zlib)
static uint32_t crc_table[256];
static void crc_init() {
  for (uint32_t i = 0; i < 256; i++) {
    uint32_t c = i;
    for (int k = 0; k < 8; k++) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
    crc_table[i] = c;
  }
}
static uint32_t crc32(const uint8_t* p, size_t n) {
  uint32_t c = 0xFFFFFFFFu;
  while (n--) c = crc_table[(c ^ *p++) & 0xFF] ^ (c >> 8);
  return c ^ 0xFFFFFFFFu;
}

// ----------------------------------------------------------------- acquisition
static void IRAM_ATTR drdy_isr() {
  drdy_time_us = esp_timer_get_time();
  BaseType_t woken = pdFALSE;
  vTaskNotifyGiveFromISR(acq_handle, &woken);
  if (woken) portYIELD_FROM_ISR();
}

static void acq_task(void*) {
  Packet* cur = nullptr;
  int ns = 0;
  uint32_t seq = 0;
  uint16_t loff_p = 0, loff_n = 0;
  uint8_t pflags = 0;
  uint8_t fa[ads1298::FRAME_BYTES], fb[ads1298::FRAME_BYTES];

  for (;;) {
    uint32_t n = ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(100));
    if (n == 0 || !streaming) continue;
    int64_t t = drdy_time_us;
    xSemaphoreTake(ads_mtx, portMAX_DELAY);
    ads.readFrames(fa, fb);
    xSemaphoreGive(ads_mtx);

    if (flush_partial) {  // stream (re)started: never mix samples across a pause
      flush_partial = false;
      if (cur && cur != &scratch) xQueueSend(free_q, &cur, 0);
      cur = nullptr;
      if (session_reset) seq = 0;
      session_reset = false;
    }
    if (!cur) {
      if (xQueueReceive(free_q, &cur, 0) != pdTRUE) cur = &scratch;
      cur->h.t_us = (uint64_t)t;
      ns = 0;
      loff_p = loff_n = 0;
      pflags = 0;
    }
    if (n > 1) {
      missed_drdy += n - 1;
      pflags |= PKT_F_MISSED;
    }
    // Status word: 1100 | LOFF_STATP[7:0] | LOFF_STATN[7:0] | GPIO[7:4]
    const uint8_t* f[2] = {fa, fb};
    for (int c = 0; c < 2; c++) {
      uint32_t s = (uint32_t(f[c][0]) << 16) | (uint32_t(f[c][1]) << 8) | f[c][2];
      if ((s >> 20) != 0xC) {
        status_errors++;
        pflags |= PKT_F_STATUS_ERR;
      }
      loff_p |= uint16_t((s >> 12) & 0xFF) << (8 * c);
      loff_n |= uint16_t((s >> 4) & 0xFF) << (8 * c);
    }
    memcpy(cur->data + ns * 48, fa + 3, 24);
    memcpy(cur->data + ns * 48 + 24, fb + 3, 24);

    if (++ns < SAMPLES_PER_PACKET) continue;

    PacketHeader& h = cur->h;
    h.magic = PKT_MAGIC;
    h.version = PKT_VERSION;
    h.n_samples = SAMPLES_PER_PACKET;
    h.seq = seq++;
    h.rate_sps = cfg.rate;
    h.gain = cfg.gain;
    h.loff_p = loff_p;
    h.loff_n = loff_n;
    uint8_t flags = pflags | (uint8_t(cfg.mode) << PKT_F_MODE_SHIFT);
    if (cfg.leadoff) flags |= PKT_F_LEADOFF;
    portENTER_CRITICAL(&shared_mux);
    if (marker_pending) flags |= PKT_F_MARKER;
    marker_pending = false;
    portEXIT_CRITICAL(&shared_mux);
    h.fw_drops = fw_drops > 0xFFFF ? 0xFFFF : fw_drops;
    h.flags = flags;

    if (cur == &scratch) {
      fw_drops++;  // no free buffer: tx is not keeping up, packet lost
    } else {
      xQueueSend(full_q, &cur, 0);  // cannot fail: queues hold NBUF entries
    }
    cur = nullptr;
  }
}

static void tx_task(void*) {
  for (;;) {
    Packet* p;
    xQueueReceive(full_q, &p, portMAX_DELAY);
    p->crc32 = crc32((const uint8_t*)p, sizeof(Packet) - 4);
    const Transport m = tx_mode;
    bool ok = true;
    if (m == Transport::Usb) {
      xSemaphoreTake(usb_mtx, portMAX_DELAY);
      ok = Serial.write((const uint8_t*)p, sizeof(Packet)) == sizeof(Packet);
      xSemaphoreGive(usb_mtx);
    } else if (m == Transport::Udp) {
      ok = WiFi.status() == WL_CONNECTED && stream_udp.beginPacket(udp_dest, udp_dest_port);
      if (ok) {
        stream_udp.write((const uint8_t*)p, sizeof(Packet));
        ok = stream_udp.endPacket();
      }
    }
    if (!ok) fw_drops++;
    xQueueSend(free_q, &p, 0);
  }
}

// ----------------------------------------------------------------- stream control
static void stream_stop() {
  if (!streaming) return;
  streaming = false;
  xSemaphoreTake(ads_mtx, portMAX_DELAY);
  ads.stopStream();
  xSemaphoreGive(ads_mtx);
}

static void stream_start(Transport t, bool new_session) {
  stream_stop();
  tx_mode = t;
  if (new_session) session_reset = true;
  flush_partial = true;
  streaming = true;
  xSemaphoreTake(ads_mtx, portMAX_DELAY);
  ads.startStream();
  xSemaphoreGive(ads_mtx);
}

// Apply a new ADS configuration; resumes streaming (same session) if it was running.
static bool reconfigure(const AdsConfig& next) {
  const bool was = streaming;
  const Transport t = tx_mode;
  stream_stop();
  xSemaphoreTake(ads_mtx, portMAX_DELAY);
  bool ok = ads.configure(next);
  xSemaphoreGive(ads_mtx);
  if (ok) cfg = next;
  else {
    xSemaphoreTake(ads_mtx, portMAX_DELAY);
    ads.configure(cfg);  // roll back
    xSemaphoreGive(ads_mtx);
  }
  if (was) stream_start(t, false);
  return ok;
}

// ----------------------------------------------------------------- replies
struct Source {
  Transport via;
  IPAddress ip;
  uint16_t port;
};

static void reply(const Source& src, const char* fmt, ...) {
  char buf[256];
  buf[0] = '#';
  buf[1] = ' ';
  va_list ap;
  va_start(ap, fmt);
  int n = vsnprintf(buf + 2, sizeof(buf) - 3, fmt, ap);
  va_end(ap);
  n = min(n + 2, (int)sizeof(buf) - 2);
  buf[n++] = '\n';
  if (src.via == Transport::Udp) {
    cmd_udp.beginPacket(src.ip, src.port);
    cmd_udp.write((const uint8_t*)buf, n);
    cmd_udp.endPacket();
  } else {
    xSemaphoreTake(usb_mtx, portMAX_DELAY);
    Serial.write((const uint8_t*)buf, n);
    xSemaphoreGive(usb_mtx);
  }
}

// ----------------------------------------------------------------- Wi-Fi
static void wifi_load() {
  Preferences p;
  p.begin("neurband", true);
  wcfg.ssid = p.getString("ssid", WIFI_DEFAULT_SSID);
  wcfg.pass = p.getString("pass", WIFI_DEFAULT_PASS);
  wcfg.host = p.getString("host", WIFI_DEFAULT_HOST);
  wcfg.port = p.getUShort("port", WIFI_DEFAULT_PORT);
  p.end();
}

static void wifi_save() {
  Preferences p;
  p.begin("neurband", false);
  p.putString("ssid", wcfg.ssid);
  p.putString("pass", wcfg.pass);
  p.putString("host", wcfg.host);
  p.putUShort("port", wcfg.port);
  p.end();
}

static void wifi_connect() {
  if (cmd_udp_up) {
    cmd_udp.stop();
    cmd_udp_up = false;
  }
  if (WiFi.getMode() != WIFI_OFF) WiFi.disconnect(true);
  if (wcfg.ssid.length() == 0) return;
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // modem sleep adds 100 ms latency spikes and drops at 1.6 Mbit/s
  WiFi.begin(wcfg.ssid.c_str(), wcfg.pass.c_str());
}

static void wifi_service() {
  static uint32_t last_hello = 0;
  if (wcfg.ssid.length() == 0) return;
  const bool up = WiFi.status() == WL_CONNECTED;
  if (up && !cmd_udp_up) cmd_udp_up = cmd_udp.begin(wcfg.port);
  if (!up && cmd_udp_up) {
    cmd_udp.stop();
    cmd_udp_up = false;
  }
  // Idle beacon so the recorder can find the band without knowing its IP.
  IPAddress host;
  if (up && cmd_udp_up && !streaming && millis() - last_hello > 2000 && host.fromString(wcfg.host)) {
    last_hello = millis();
    char b[112];
    int n = snprintf(b, sizeof(b), "# NEURBAND HELLO ip=%s port=%u fw=%s ads_ok=%d\n",
                     WiFi.localIP().toString().c_str(), wcfg.port, NEURBAND_FW_VERSION, ads_ok);
    cmd_udp.beginPacket(host, wcfg.port);
    cmd_udp.write((const uint8_t*)b, n);
    cmd_udp.endPacket();
  }
}

// ----------------------------------------------------------------- commands
static const char* mode_name(InputMode m) {
  return m == InputMode::Test ? "test" : m == InputMode::Shorted ? "short" : "normal";
}

static void print_status(const Source& src) {
  reply(src, "neurband fw %s ads_ok=%d idA=0x%02X idB=0x%02X verify_err=%d", NEURBAND_FW_VERSION,
        ads_ok, ads.id(Ads1298Pair::A), ads.id(Ads1298Pair::B), ads.verifyErrors());
  reply(src, "rate=%u gain=%u mode=%s leadoff=%d streaming=%d via=%s",
        cfg.rate, cfg.gain, mode_name(cfg.mode), cfg.leadoff, (int)streaming,
        tx_mode == Transport::Usb ? "usb" : tx_mode == Transport::Udp ? "udp" : "none");
  reply(src, "fw_drops=%u missed_drdy=%u status_err=%u", (unsigned)fw_drops,
        (unsigned)missed_drdy, (unsigned)status_errors);
  reply(src, "wifi ssid='%s' host=%s port=%u status=%d ip=%s", wcfg.ssid.c_str(),
        wcfg.host.c_str(), wcfg.port, (int)WiFi.status(), WiFi.localIP().toString().c_str());
}

static void dump_regs(const Source& src) {
  const bool was = streaming;
  const Transport t = tx_mode;
  stream_stop();  // RREG is ignored in RDATAC mode
  xSemaphoreTake(ads_mtx, portMAX_DELAY);
  for (int c = 0; c < 2; c++) {
    char line[200];
    int n = snprintf(line, sizeof(line), "%s:", c ? "B" : "A");
    for (uint8_t r = 0; r <= ads1298::WCT2; r++)
      n += snprintf(line + n, sizeof(line) - n, " %02X", ads.readReg(Ads1298Pair::Chip(c), r));
    reply(src, "%s", line);
  }
  xSemaphoreGive(ads_mtx);
  if (was) stream_start(t, false);
}

static void handle_command(char* line, const Source& src) {
  char* argv[6] = {};
  int argc = 0;
  for (char* tok = strtok(line, " \t\r\n"); tok && argc < 6; tok = strtok(nullptr, " \t\r\n"))
    argv[argc++] = tok;
  if (argc == 0) return;
  const char* cmd = argv[0];
  AdsConfig next = cfg;

  if (!strcmp(cmd, "start")) {
    Transport t = src.via;
    if (src.via == Transport::Udp) {
      udp_dest = src.ip;  // stream back to whoever asked
      udp_dest_port = src.port;
    } else if (argc > 1 && !strcmp(argv[1], "udp")) {
      if (!udp_dest.fromString(wcfg.host) || WiFi.status() != WL_CONNECTED) {
        reply(src, "ERR wifi not connected or host not set");
        return;
      }
      udp_dest_port = wcfg.port;
      t = Transport::Udp;
    }
    if (!ads_ok) reply(src, "WARN ADS init failed, streaming anyway");
    stream_start(t, true);
    reply(src, "OK start rate=%u gain=%u", cfg.rate, cfg.gain);
  } else if (!strcmp(cmd, "stop")) {
    stream_stop();
    reply(src, "OK stop");
  } else if (!strcmp(cmd, "rate") && argc > 1) {
    next.rate = atoi(argv[1]);
    if (next.rate != 2000 && next.rate != 4000) return reply(src, "ERR rate 2000|4000");
    reply(src, reconfigure(next) ? "OK rate %u" : "ERR rate %u (verify failed)", next.rate);
  } else if (!strcmp(cmd, "gain") && argc > 1) {
    uint8_t code;
    next.gain = atoi(argv[1]);
    if (!Ads1298Pair::gainCode(next.gain, &code)) return reply(src, "ERR gain 1|2|3|4|6|8|12");
    reply(src, reconfigure(next) ? "OK gain %u" : "ERR gain %u (verify failed)", next.gain);
  } else if (!strcmp(cmd, "test") || !strcmp(cmd, "short") || !strcmp(cmd, "normal")) {
    next.mode = !strcmp(cmd, "test") ? InputMode::Test
              : !strcmp(cmd, "short") ? InputMode::Shorted : InputMode::Normal;
    reply(src, reconfigure(next) ? "OK mode %s" : "ERR mode %s", mode_name(next.mode));
  } else if (!strcmp(cmd, "leadoff") && argc > 1) {
    next.leadoff = !strcmp(argv[1], "on");
    reply(src, reconfigure(next) ? "OK leadoff %s" : "ERR leadoff %s", next.leadoff ? "on" : "off");
  } else if (!strcmp(cmd, "wifi")) {
    if (argc == 5) {
      wcfg.ssid = argv[1];
      wcfg.pass = argv[2];
      wcfg.host = argv[3];
      wcfg.port = atoi(argv[4]);
      wifi_save();
      wifi_connect();
      reply(src, "OK wifi saved, connecting to '%s'", wcfg.ssid.c_str());
    } else if (argc == 2 && !strcmp(argv[1], "off")) {
      wcfg.ssid = "";
      wifi_save();
      wifi_connect();
      reply(src, "OK wifi off");
    } else {
      reply(src, "usage: wifi <ssid> <pass> <host> <port> | wifi off");
    }
  } else if (!strcmp(cmd, "status") || !strcmp(cmd, "id")) {
    print_status(src);
  } else if (!strcmp(cmd, "regs")) {
    dump_regs(src);
  } else if (!strcmp(cmd, "help")) {
    reply(src, "start [udp] | stop | rate 2000|4000 | gain 1|2|3|4|6|8|12 | test | short | normal");
    reply(src, "leadoff on|off | wifi <ssid> <pass> <host> <port> | wifi off | status | regs");
  } else {
    reply(src, "ERR unknown command '%s' (try help)", cmd);
  }
}

static void poll_commands() {
  static char sline[160];
  static size_t slen = 0;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (slen) {
        sline[slen] = 0;
        handle_command(sline, Source{Transport::Usb, IPAddress(), 0});
      }
      slen = 0;
    } else if (slen < sizeof(sline) - 1) {
      sline[slen++] = c;
    }
  }
  if (cmd_udp_up) {
    int n = cmd_udp.parsePacket();
    if (n > 0) {
      char b[160];
      n = cmd_udp.read((uint8_t*)b, sizeof(b) - 1);
      if (n > 0) {
        b[n] = 0;
        handle_command(b, Source{Transport::Udp, cmd_udp.remoteIP(), cmd_udp.remotePort()});
      }
    }
  }
}

// ----------------------------------------------------------------- marker button
static void poll_button() {
  static bool last_level = true;
  static uint32_t last_change = 0;
  bool level = digitalRead(PIN_BOOT_BTN);
  if (level != last_level && millis() - last_change > 30) {
    last_change = millis();
    last_level = level;
    if (!level) {  // pressed
      portENTER_CRITICAL(&shared_mux);
      marker_pending = true;
      portEXIT_CRITICAL(&shared_mux);
    }
  }
}

// ----------------------------------------------------------------- setup / loop
void setup() {
  pinMode(PIN_BOOT_BTN, INPUT_PULLUP);

  Serial.setTxBufferSize(8192);
  Serial.setRxBufferSize(512);
  Serial.begin(115200);  // baud is ignored on USB CDC
  Serial.setTxTimeoutMs(20);
  crc_init();

  ads_mtx = xSemaphoreCreateMutex();
  usb_mtx = xSemaphoreCreateMutex();
  free_q = xQueueCreate(NBUF, sizeof(Packet*));
  full_q = xQueueCreate(NBUF, sizeof(Packet*));
  for (int i = 0; i < NBUF; i++) {
    Packet* p = &bufs[i];
    xQueueSend(free_q, &p, 0);
  }

  wifi_load();
  wifi_connect();  // associates in the background during the ~2 s ADS start-up

  SPI.begin(PIN_SPI_SCLK, PIN_SPI_MISO, PIN_SPI_MOSI, -1);
  cfg.rate = DEFAULT_RATE_SPS;
  cfg.gain = DEFAULT_GAIN;
  ads_ok = ads.begin(cfg);

  xTaskCreatePinnedToCore(acq_task, "acq", 4096, nullptr, configMAX_PRIORITIES - 2, &acq_handle, 1);
  xTaskCreatePinnedToCore(tx_task, "tx", 4096, nullptr, 5, nullptr, 0);
  pinMode(PIN_ADS_DRDY, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_ADS_DRDY), drdy_isr, FALLING);

  print_status(Source{Transport::Usb, IPAddress(), 0});
}

void loop() {
  poll_commands();
  poll_button();
  wifi_service();
  delay(1);
}
