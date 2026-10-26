// Minimal driver for two ADS1298 on one SPI bus with separate chip selects.
// Register/opcode values: TI SBAS459K (docs/datasheets/ads1298.txt), Tables 15 and 16.
#pragma once
#include <Arduino.h>
#include <SPI.h>

namespace ads1298 {
enum Reg : uint8_t {
  ID = 0x00, CONFIG1 = 0x01, CONFIG2 = 0x02, CONFIG3 = 0x03, LOFF = 0x04,
  CH1SET = 0x05,  // CH1SET..CH8SET = 0x05..0x0C
  RLD_SENSP = 0x0D, RLD_SENSN = 0x0E, LOFF_SENSP = 0x0F, LOFF_SENSN = 0x10,
  LOFF_FLIP = 0x11, LOFF_STATP = 0x12, LOFF_STATN = 0x13, GPIO = 0x14,
  PACE = 0x15, RESP = 0x16, CONFIG4 = 0x17, WCT1 = 0x18, WCT2 = 0x19,
};
enum Cmd : uint8_t {
  WAKEUP = 0x02, STANDBY = 0x04, RESET = 0x06, START = 0x08, STOP = 0x0A,
  RDATAC = 0x10, SDATAC = 0x11, RDATA = 0x12, RREG = 0x20, WREG = 0x40,
};
constexpr uint8_t ID_ADS1298 = 0x92;  // 100 (ADS129x) 10 (fixed) 010 (8 ch)
constexpr int FRAME_BYTES = 3 + 8 * 3; // status word + 8 x 24 bit
}  // namespace ads1298

enum class InputMode : uint8_t { Normal = 0, Shorted = 1, Test = 2 };

struct AdsConfig {
  uint16_t rate = 4000;  // 2000 or 4000 SPS (HR mode)
  uint8_t gain = 6;      // 1, 2, 3, 4, 6, 8, 12
  InputMode mode = InputMode::Normal;
  bool leadoff = false;  // DC lead-off, 6 nA current source, comparators 95 %/5 %
};

class Ads1298Pair {
 public:
  enum Chip { A = 0, B = 1 };  // A = U2 (ch 1-8, clock master), B = U3 (ch 9-16)

  Ads1298Pair(SPIClass& spi, int csA, int csB, int startPin);

  // Opcode-only reset/power-up sequence (U2 first, then U3 once U2 clocks it), followed
  // by configure(). Returns true if both IDs read 0x92 and all register writes verified.
  // ~RESET/~PWDN are hard-wired high on the board, so this also works after a warm
  // ESP32 reboot with the chips still running.
  bool begin(const AdsConfig& cfg);
  // Write all configuration registers. Conversions must be stopped (stopStream()).
  bool configure(const AdsConfig& cfg);
  void startStream();  // RDATAC on both chips, then START high
  void stopStream();   // START low, SDATAC on both chips
  // Read one 27-byte frame from each chip (RDATAC mode, call after DRDY falls).
  void readFrames(uint8_t* a, uint8_t* b);

  uint8_t readReg(Chip c, uint8_t reg);  // only while stopped (SDATAC)
  void writeReg(Chip c, uint8_t reg, uint8_t val);
  void command(Chip c, uint8_t op);
  uint8_t id(Chip c) const { return id_[c]; }
  int verifyErrors() const { return verify_errors_; }
  static bool gainCode(uint8_t gain, uint8_t* code);

 private:
  void xfer(Chip c, const uint8_t* tx, uint8_t* rx, size_t n, bool fast);
  SPIClass& spi_;
  int cs_[2], start_;
  uint8_t id_[2] = {0, 0};
  int verify_errors_ = 0;
};
