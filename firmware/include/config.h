// neurband board configuration. Source of truth for the pins:
// boards/neurband_main/gen_main_sch.py
#pragma once

#define NEURBAND_FW_VERSION "0.2.0"

// ---- ADS1298 x2 (shared SPI bus, separate chip selects) -------------------
// ~RESET and ~PWDN are tied to +3V3 on the board: both chips are reset with the
// SPI RESET opcode only. CS_A/CS_B have 10k pull-ups, START has a 10k pull-down.
#define PIN_SPI_SCLK   12
#define PIN_SPI_MOSI   11
#define PIN_SPI_MISO   13
#define PIN_ADS_CS_A   10   // U2: channels 1-8, clock master (CLKSEL=1), RLD amp, DRDY
#define PIN_ADS_CS_B    9   // U3: channels 9-16, CLKSEL=0 (clock from U2 CLK pin)
#define PIN_ADS_START   7   // shared START
#define PIN_ADS_DRDY    8   // ~DRDY from U2 only (both chips convert in lock-step)

// ---- misc --------------------------------------------------------------------
#define PIN_BOOT_BTN    0     // BOOT strap; at runtime: marker button (active low)
// No IMU, battery divider or status LED on this board revision. Native USB
// (GPIO19/20) and UART0 are test pads for off-body flashing/bench use only.

// ---- stream defaults ------------------------------------------------------------
#define DEFAULT_RATE_SPS    4000
#define DEFAULT_GAIN        6
#define SAMPLES_PER_PACKET  20    // 200 packets/s at 4 kSPS, 990 bytes each

// ---- Wi-Fi defaults (overridden by the `wifi` command, stored in NVS) -------------
// Wi-Fi UDP is the on-body transport; set these or use `wifi` over USB once, off-body.
#define WIFI_DEFAULT_SSID   ""
#define WIFI_DEFAULT_PASS   ""
#define WIFI_DEFAULT_HOST   ""      // PC running neurband_rec.py, e.g. "192.168.1.50"
#define WIFI_DEFAULT_PORT   5005    // device listens for commands on this port too
