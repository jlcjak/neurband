#include "ads1298.h"

using namespace ads1298;

// Register access: 1 MHz -> 8 us per byte, comfortably above tSDECODE = 4 tCLK (~2 us),
// so multi-byte commands need no inter-byte gaps (datasheet 9.5.2.9).
static const SPISettings kCmdSpi(1000000, MSBFIRST, SPI_MODE1);
// Data read: 2 x 27 bytes at 4 MHz = 108 us of the 250 us frame at 4 kSPS.
static const SPISettings kDataSpi(4000000, MSBFIRST, SPI_MODE1);

Ads1298Pair::Ads1298Pair(SPIClass& spi, int csA, int csB, int startPin)
    : spi_(spi), cs_{csA, csB}, start_(startPin) {}

void Ads1298Pair::xfer(Chip c, const uint8_t* tx, uint8_t* rx, size_t n, bool fast) {
  // Only one CS is ever low: the other chip's DOUT stays tri-stated.
  spi_.beginTransaction(fast ? kDataSpi : kCmdSpi);
  digitalWrite(cs_[c], LOW);
  spi_.transferBytes(tx, rx, n);
  delayMicroseconds(3);  // tSCCS: 4 tCLK (1.95 us) from last SCLK to CS high
  digitalWrite(cs_[c], HIGH);
  spi_.endTransaction();
  delayMicroseconds(2);  // tCSH: CS high >= 2 tCLK
}

void Ads1298Pair::command(Chip c, uint8_t op) {
  uint8_t rx;
  xfer(c, &op, &rx, 1, false);
  delayMicroseconds(4);  // tSDECODE before the next command
}

void Ads1298Pair::writeReg(Chip c, uint8_t reg, uint8_t val) {
  uint8_t tx[3] = {uint8_t(WREG | reg), 0x00, val}, rx[3];
  xfer(c, tx, rx, 3, false);
}

uint8_t Ads1298Pair::readReg(Chip c, uint8_t reg) {
  uint8_t tx[3] = {uint8_t(RREG | reg), 0x00, 0x00}, rx[3];
  xfer(c, tx, rx, 3, false);
  return rx[2];
}

bool Ads1298Pair::gainCode(uint8_t gain, uint8_t* code) {
  // CHnSET GAINn[2:0]: 000=6 001=1 010=2 011=3 100=4 101=8 110=12
  switch (gain) {
    case 6: *code = 0; return true;
    case 1: *code = 1; return true;
    case 2: *code = 2; return true;
    case 3: *code = 3; return true;
    case 4: *code = 4; return true;
    case 8: *code = 5; return true;
    case 12: *code = 6; return true;
  }
  return false;
}

static uint8_t config1For(uint16_t rate, bool master) {
  // HR=1 (bit 7), DAISY_EN=0, CLK_EN (bit 5) on the master only, DR: 011=4k, 100=2k (HR)
  uint8_t dr = (rate == 2000) ? 0x04 : 0x03;
  return 0x80 | (master ? 0x20 : 0x00) | dr;
}

bool Ads1298Pair::begin(const AdsConfig& cfg) {
  pinMode(cs_[A], OUTPUT);
  pinMode(cs_[B], OUTPUT);
  digitalWrite(cs_[A], HIGH);  // also 10k pull-ups on the board
  digitalWrite(cs_[B], HIGH);
  pinMode(start_, OUTPUT);
  digitalWrite(start_, LOW);   // also 10k pull-down on the board

  // ~PWDN/~RESET are tied high, so U2's oscillator has run since power-on. Make sure
  // >= tPOR (2^18 tCLK = 128 ms) and the VCAP1 charge (22 uF, VCAP1 > 1.1 V) have elapsed.
  while (millis() < 1000) delay(10);

  // --- U2 (clock master). SDATAC first: after a warm ESP32 reboot the chip may still
  // be in RDATAC, where it only accepts SDATAC.
  command(A, SDATAC);
  command(A, RESET);   // clears CLK_EN: U3 loses its clock until CONFIG1 below
  delay(1);            // >= 18 tCLK (9 us)
  command(A, SDATAC);  // device wakes up from reset in RDATAC
  writeReg(A, CONFIG1, config1For(cfg.rate, true));  // CLK_EN=1 -> U2 now clocks U3
  writeReg(A, CONFIG3, 0xCC);                         // internal reference on
  // U2: VREFP (10 uF) settling. U3: tPOR counts from a valid CLK (Fig. 105 note 2),
  // 2^18 tCLK = 128 ms; 500 ms covers both.
  delay(500);
  id_[A] = readReg(A, ID);

  // --- U3 (clocked by U2 from here on)
  command(B, SDATAC);
  command(B, RESET);
  delay(1);
  command(B, SDATAC);
  writeReg(B, CONFIG3, 0xC8);  // internal reference on, RLD amp off
  delay(500);                  // U3 VREFP settling
  id_[B] = readReg(B, ID);

  bool ok = configure(cfg);
  return ok && id_[A] == ID_ADS1298 && id_[B] == ID_ADS1298;
}

bool Ads1298Pair::configure(const AdsConfig& cfg) {
  uint8_t gc;
  if (!gainCode(cfg.gain, &gc)) return false;
  if (cfg.rate != 2000 && cfg.rate != 4000) return false;
  const uint8_t mux = cfg.mode == InputMode::Test ? 0x05 : cfg.mode == InputMode::Shorted ? 0x01 : 0x00;
  const uint8_t chset = uint8_t(gc << 4) | mux;  // PDn=0 (on)
  verify_errors_ = 0;

  for (int i = 0; i < 2; i++) {
    const Chip c = Chip(i);
    const bool master = (c == A);
    struct { uint8_t reg, val; } regs[] = {
        {CONFIG1, config1For(cfg.rate, master)},
        // INT_TEST=1, TEST_AMP=0 (1 x VREF/2400), TEST_FREQ=00 (fCLK/2^21 ~ 1 Hz)
        {CONFIG2, uint8_t(cfg.mode == InputMode::Test ? 0x10 : 0x00)},
        // PD_REFBUF=1, bit6=1, VREF_4V=0 (2.4 V), RLDREF_INT=1, PD_RLD=1 on master only
        {CONFIG3, uint8_t(master ? 0xCC : 0xC8)},
        // COMP_TH=000 (95/5 %), VLEAD_OFF_EN=0 (current source), ILEAD_OFF=00 (6 nA), FLEAD=11 (DC)
        {LOFF, uint8_t(cfg.leadoff ? 0x03 : 0x00)},
        {uint8_t(CH1SET + 0), chset}, {uint8_t(CH1SET + 1), chset},
        {uint8_t(CH1SET + 2), chset}, {uint8_t(CH1SET + 3), chset},
        {uint8_t(CH1SET + 4), chset}, {uint8_t(CH1SET + 5), chset},
        {uint8_t(CH1SET + 6), chset}, {uint8_t(CH1SET + 7), chset},
        // all 8 P and N inputs feed the shared RLDINV node (U3's amp is off, its
        // sense resistors still sum into RLD_INV)
        {RLD_SENSP, 0xFF}, {RLD_SENSN, 0xFF},
        {LOFF_SENSP, uint8_t(cfg.leadoff ? 0xFF : 0x00)},
        {LOFF_SENSN, uint8_t(cfg.leadoff ? 0xFF : 0x00)},
        {LOFF_FLIP, 0x00},
        // PD_LOFF_COMP (bit 1): comparators on only when lead-off is used
        {CONFIG4, uint8_t(cfg.leadoff ? 0x02 : 0x00)},
        {WCT1, 0x00},  // PD_WCTA=0: WCT amp A off, no augmented leads
        {WCT2, 0x00},  // PD_WCTB=PD_WCTC=0: WCT amps B, C off
    };
    for (auto& r : regs) writeReg(c, r.reg, r.val);
    for (auto& r : regs) {
      // ignore read-only RLD_STAT (CONFIG3 bit 0) and the reserved CONFIG2[7:6]
      // (reset value 1, datasheet says write 0; read-back value not specified)
      const uint8_t mask = r.reg == CONFIG3 ? 0xFE : r.reg == CONFIG2 ? 0x3F : 0xFF;
      if ((readReg(c, r.reg) ^ r.val) & mask) verify_errors_++;
    }
  }
  return verify_errors_ == 0;
}

void Ads1298Pair::startStream() {
  command(A, RDATAC);
  command(B, RDATAC);
  digitalWrite(start_, HIGH);  // shared START: both chips start on the same CLK edge
}

void Ads1298Pair::stopStream() {
  digitalWrite(start_, LOW);
  delayMicroseconds(600);  // let a conversion in flight finish (500 us at 2 kSPS)
  command(A, SDATAC);
  command(B, SDATAC);
}

void Ads1298Pair::readFrames(uint8_t* a, uint8_t* b) {
  static const uint8_t zeros[FRAME_BYTES] = {0};  // keep DIN low while reading
  xfer(A, zeros, a, FRAME_BYTES, true);
  xfer(B, zeros, b, FRAME_BYTES, true);
}
