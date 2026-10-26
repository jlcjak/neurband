// Binary stream packet. Little-endian, packed. Documented in docs/firmware.md.
#pragma once
#include <stdint.h>
#include "config.h"

#define PKT_MAGIC    0x424E  // bytes 'N','B' on the wire
#define PKT_VERSION  2       // v2: IMU and battery fields removed (board rev without them)
#define NUM_CHANNELS 16

// flags
#define PKT_F_MARKER     0x01  // BOOT button pressed since previous packet
#define PKT_F_LEADOFF    0x02  // lead-off detection enabled
#define PKT_F_MODE_MASK  0x0C  // input mode: 0 normal, 1 shorted, 2 test signal
#define PKT_F_MODE_SHIFT 2
#define PKT_F_MISSED     0x20  // at least one DRDY was missed inside this packet
#define PKT_F_STATUS_ERR 0x40  // an ADS status word did not start with 0b1100

struct __attribute__((packed)) PacketHeader {
  uint16_t magic;       // PKT_MAGIC
  uint8_t  version;     // PKT_VERSION
  uint8_t  n_samples;   // samples per channel in this packet
  uint32_t seq;         // packet counter, reset by `start`
  uint64_t t_us;        // esp_timer time of the first sample's DRDY edge
  uint16_t rate_sps;    // 2000 or 4000
  uint8_t  gain;        // PGA gain (1,2,3,4,6,8,12)
  uint8_t  flags;       // PKT_F_*
  uint16_t loff_p;      // OR of LOFF_STATP over the packet: bit i = channel i+1 P side
  uint16_t loff_n;      // same for N side
  uint16_t fw_drops;    // cumulative packets the firmware failed to send (saturates)
};
static_assert(sizeof(PacketHeader) == 26, "header layout");

struct __attribute__((packed)) Packet {
  PacketHeader h;
  // sample-major: s0ch1, s0ch2 .. s0ch16, s1ch1 ...; each int24 two's complement,
  // big-endian (exactly as shifted out of the ADS1298)
  uint8_t  data[SAMPLES_PER_PACKET * NUM_CHANNELS * 3];
  uint32_t crc32;       // zlib-compatible CRC-32 of all preceding bytes
};
static_assert(sizeof(Packet) == 26 + SAMPLES_PER_PACKET * 48 + 4, "packet layout");
