# neurband firmware and host recorder (iteration 1)

> **SAFETY: never stream over a USB cable while the band is on skin.** The band has no USB
> connector, charger or isolation. Native USB D+/D- and UART0 TX/RX are test pads for flashing
> and bench tests **off-body only**. A wired PC connection would tie the electrodes to mains-powered
> equipment. When the band is worn it runs from its own protected 1S LiPo and streams over Wi-Fi UDP only.

This revision of the board has two ADS1298, the ESP32-S3 and a BOOT/marker button. There is no
IMU, no battery divider and no status LED; status is reported only as text over UDP or serial.

Code: `firmware/` (PlatformIO, Arduino on ESP32-S3) and `host/` (Python 3 recorder, plotter, tests).
The pin map is in `firmware/include/config.h`, copied from `.archive/neurband_main_revA/gen_main_sch.py`.
All ADS1298 register values below come from `docs/datasheets/ads1298.txt` (TI SBAS459K).

## Build and flash

Flash **off-body**. Wire a USB cable to the test pads USB_DP, USB_DN, GND (and +3V3 or VBAT
for power), or use a 3.3 V USB-UART on UART_TX/UART_RX.

```sh
pip install platformio            # once
cd firmware
pio run                           # build
pio run -t upload                 # flash over native USB pads (GPIO19/20)
pio device monitor                # bench text console (binary packets show as garbage once streaming)
```

- Board `esp32-s3-devkitc-1`, 8 MB QIO flash, no PSRAM, `default_8MB.csv` partitions.
- `ARDUINO_USB_MODE=1` and `ARDUINO_USB_CDC_ON_BOOT=1`: `Serial` is the USB-Serial/JTAG CDC on
  the USB pads, and esptool resets the chip over it.
- UART download instead: hold BOOT, pulse EN (pad), then
  `pio run -t upload --upload-port /dev/ttyUSB0`.
- Set up Wi-Fi once on the bench: `wifi <ssid> <pass> <pc-ip> 5005` over the USB console (saved
  in NVS). Defaults can also go in `config.h`.

Host (needs numpy and matplotlib; pyserial only for USB):

```sh
cd host
python3 -m unittest -v test_packet                       # packet/parser/filter tests
python3 neurband_rec.py --udp -o rec.npz                 # on body: waits for the band's HELLO beacon
python3 neurband_rec.py --udp 192.168.1.77 --rate 2000 --gain 12 --mode short --duration 10
python3 neurband_rec.py --serial /dev/ttyACM0 -o rec.npz # BENCH ONLY (band off-body)
python3 neurband_plot.py rec.npz [--raw] [--t0 2 --t1 5] [-o fig.png]
```

The recorder sends `stop`, the requested settings, `status` and `start`. Once per second it prints
per-channel RMS (µV, after the 20-450 Hz band-pass and notches at the mains frequency and its
harmonics; `--mains 60` for 60 Hz grids) and lead-off status. It also prints lost packets
(from sequence gaps), firmware drops and CRC errors. On Ctrl-C (or `--duration`) it
sends `stop` and writes the `.npz`.

The live filter is a zero-phase FFT mask. It is applied to the last 2 s of data and the RMS is
taken over the middle 1 s, so the window edges cause no ringing (tested: mains and a 5 Hz
artifact both > 60 dB down). The plotter applies the same filter to the whole recording.

### .npz contents

| key | shape / type | meaning |
|---|---|---|
| `emg` | [N,16] float32 | volts at the electrodes, using each packet's gain |
| `t` | [N] float64 | s from the first sample (device clock: packet timestamp + i/rate) |
| `gain` | [N] uint8 | PGA gain per sample |
| `markers`, `marker_t` | [K] | sample index and time of BOOT-button markers |
| `loff_p`, `loff_n`, `pkt_seq`, `pkt_t_us`, `pkt_flags` | per packet | raw packet fields |
| `meta` | JSON string | rate, gain, vref, lsb_volts, lost_packets, restarts, fw_drops, packet_version, transport, mode, mains, start time |

## Architecture

- **acq task** (core 1, near-top priority). The DRDY falling edge (GPIO8, from U2) triggers an ISR
  that timestamps the edge (`esp_timer_get_time`) and notifies the task. The task then reads
  27 bytes from U2 and 27 bytes from U3 in RDATAC mode at 4 MHz (about 110 µs of the 250 µs frame).
  It copies them into one of 24 packet buffers. A full packet goes on a queue. If no free buffer is
  left, the packet is dropped, `fw_drops` is incremented and the sequence number still advances,
  so the host sees the gap.
- **tx task** (core 0). Computes the CRC-32 and writes the packet to the UDP socket (or USB CDC on
  the bench).
- **loop()**. Handles text commands from UDP and USB, debounces the BOOT/marker button and
  services Wi-Fi.

With no LED, check the band with the `status` command over UDP, the `ads_ok=` field of the HELLO
beacon, or the boot status lines on the bench console. `ads_ok=0` means a wrong ID or a register
read-back mismatch.

## Transports

- **Wi-Fi UDP** (on body, the default). `start` received over UDP streams to the IP:port that
  sent it. The band listens for commands on UDP `port`. While idle it sends
  `# NEURBAND HELLO ip=... port=... fw=... ads_ok=...` to `host:port` every 2 s, so the recorder can find it. The
  stream leaves from a different source port than command replies; the recorder filters by IP
  only.
- **USB CDC** (bench only, off-body). `start` received over USB streams over USB. `start udp`
  received over USB streams to the configured `host:port`.
- Bandwidth: 4 kSPS × 16 ch × 24 bit = 1.54 Mbit/s of samples, plus 3 % header and CRC, at
  200 packets/s (990-byte datagrams). Wi-Fi modem sleep is disabled (`WiFi.setSleep(false)`).

## Commands (text, newline-terminated, over USB or UDP)

| command | effect |
|---|---|
| `start` / `start udp` | start streaming on the transport the command came from (new session: seq restarts at 0). `start udp` from USB uses the saved host |
| `stop` | stop conversions (START low, SDATAC) |
| `rate 2000\|4000` | CONFIG1.DR on both chips. Resumes streaming if it was running |
| `gain 1\|2\|3\|4\|6\|8\|12` | CHnSET.GAIN on all 16 channels |
| `test` | internal test square wave on all channels (CONFIG2=0x10, MUX=101) |
| `short` | inputs shorted (MUX=001), for offset/noise measurements |
| `normal` | normal electrode inputs (MUX=000) |
| `leadoff on\|off` | DC lead-off, 6 nA current source, comparators on (see registers) |
| `wifi <ssid> <pass> <host> <port>` | save to NVS and (re)connect. `wifi off` clears the SSID |
| `status` (alias `id`) | IDs, read-back errors, settings, counters, Wi-Fi |
| `regs` | dump registers 0x00-0x19 of both chips (briefly pauses streaming) |
| `help` | list commands |

Replies are text lines starting with `# `. They can arrive between binary packets on the same
USB stream; the host parser frames packets by magic + CRC and prints the `#` lines. Over UDP,
replies go to the sender's address.

## Packet format (version 2)

All fields are little-endian, packed; total 990 bytes for 20 samples. Defined in
`firmware/src/packet.h`, parsed by `host/neurband_rec.py`. Version 2 drops the IMU and battery
fields of version 1; the parser rejects other versions.

| offset | type | field | notes |
|---|---|---|---|
| 0 | u16 | magic | 0x424E, bytes `N` `B` |
| 2 | u8 | version | 2 |
| 3 | u8 | n_samples | 20 (samples per channel in this packet) |
| 4 | u32 | seq | packet counter; restarts at 0 on `start`; continues across rate/gain changes |
| 8 | u64 | t_us | ESP32 µs timer at the DRDY edge of the first sample |
| 16 | u16 | rate_sps | 2000 / 4000 |
| 18 | u8 | gain | PGA gain |
| 19 | u8 | flags | bit0 marker (BOOT pressed), bit1 lead-off enabled, bits2-3 input mode (0 normal, 1 shorted, 2 test), bit5 missed DRDY in this packet, bit6 bad ADS status word |
| 20 | u16 | loff_p | OR of LOFF_STATP over the packet; bit i = channel i+1 (bits 0-7 U2, 8-15 U3) |
| 22 | u16 | loff_n | same for the N inputs |
| 24 | u16 | fw_drops | total packets the firmware could not send (saturates at 65535) |
| 26 | 20×16×3 B | samples | sample-major (s0 ch1..ch16, s1 ch1..). Each is int24 two's complement, **big-endian** as shifted out of the ADS1298 |
| 986 | u32 | crc32 | zlib CRC-32 of bytes 0..985 |

Volts = code × (2 × VREF / gain) / 2^24 with VREF = 2.4 V (47.7 nV/LSB at gain 6).
Full scale is ±VREF/gain (±400 mV at gain 6).

## Power-up sequence (firmware `Ads1298Pair::begin`)

~RESET and ~PWDN of both chips are tied to +3V3, so the chips are powered and (U2) clocked from
power-on, and they can only be reset with the SPI RESET opcode (0x06). CS_A/CS_B have 10 kΩ
pull-ups and START a 10 kΩ pull-down, so the chips are deselected and idle while the ESP32 boots.
Only one CS is ever low at a time.

1. Drive CS_A/CS_B high and START low. Wait until at least 1 s after boot: tPOR =
   2^18 tCLK = 128 ms (Table 38), and VCAP1 (22 µF, ~12.5 kΩ internal) must reach 1.1 V.
2. **U2:** SDATAC (after a warm ESP32 reboot the chip may still be in RDATAC, where it only
   accepts SDATAC), RESET, wait ≥ 18 tCLK, SDATAC (it wakes up in RDATAC). Write CONFIG1 with
   CLK_EN=1, so U2's 2.048 MHz clock now drives U3, and CONFIG3 (reference on). Wait 500 ms: this
   covers U2's VREFP settling and U3's tPOR, which counts from a valid CLK (Fig. 105 note 2;
   ≥ 128 ms). Read the ID (0x92). The RESET clears CLK_EN, so U3 is briefly unclocked until
   CONFIG1 is written; that is why U3 is reset only after this step.
3. **U3:** SDATAC, RESET, wait, SDATAC, CONFIG3 (reference on, RLD amp off), wait 500 ms for
   VREFP, read the ID.
4. Write all registers to both chips, read each back and count mismatches (`status` shows them).

To stream: RDATAC on both, then START high. The shared START and the shared clock keep both chips
converting in lock-step, so U2's DRDY is valid for U3 (datasheet 9.4 / Fig. 65). To stop:
START low, wait 600 µs, SDATAC on both.

SPI is mode 1. Register access runs at 1 MHz (8 µs per byte), above the 4 tCLK (≈2 µs)
multi-byte decode time (9.5.2.9), so no inter-byte delays are needed. Data reads run at 4 MHz.
CS goes high ≥ 4 tCLK after the last SCLK edge (tSCCS). DIN stays low during data reads.

## Register settings and why

| reg | addr | U2 (ch 1-8) | U3 (ch 9-16) | reason |
|---|---|---|---|---|
| CONFIG1 | 0x01 | 0xA3 (4k) / 0xA4 (2k) | 0x83 / 0x84 | HR=1 (high resolution, lowest noise). CLK_EN=1 on U2 only, so its oscillator clocks U3. DAISY_EN=0 (unused: separate CS). DR=011 → fMOD/128 = 4 kSPS in HR, DR=100 → 2 kSPS. Both keep 24-bit output |
| CONFIG2 | 0x02 | 0x00, test: 0x10 | same | INT_TEST=1 generates the test signal internally. TEST_AMP=0 → 1 × (VREFP−VREFN)/2400 ≈ 1 mV. TEST_FREQ=00 → fCLK/2^21 ≈ 0.98 Hz square wave. Bits 7:6 written 0 as the datasheet says (their reset value is 1, so they are excluded from the read-back check) |
| CONFIG3 | 0x03 | 0xCC | 0xC8 | PD_REFBUF=1 (internal reference on), bit6=1 (reserved, must be 1), VREF_4V=0 → 2.4 V (3.0 V AVDD), RLDREF_INT=1 (mid-supply RLD reference; the RLDREF pin is NC), PD_RLD=1 on U2 only: one RLD amplifier drives the bias electrode, and U3's amp stays off (datasheet Fig. 45 multi-device RLD). RLD_LOFF_SENS=0 |
| LOFF | 0x04 | 0x00, lead-off: 0x03 | same | COMP_TH=000 (95 % / 5 %), VLEAD_OFF_EN=0 (current source, higher impedance than the 10 MΩ pull resistors), ILEAD_OFF=00 = 6 nA (smallest DC error on dry/high-impedance electrodes), FLEAD_OFF=11 = DC lead-off |
| CH1..8SET | 0x05-0x0C | 0x00 | 0x00 | PD=0, GAIN=000 → 6, MUX=000 normal electrode input. `gain` changes GAIN (001=1, 010=2, 011=3, 100=4, 101=8, 110=12). `test` → MUX=101, `short` → MUX=001. Gain 6 gives ±400 mV, which leaves headroom for DC-coupled electrode half-cell offsets of a few hundred mV |
| RLD_SENSP | 0x0D | 0xFF | 0xFF | All 8 P inputs feed the RLD common-mode estimate. On U3 they sum into the shared RLD_INV node even though U3's amp is off |
| RLD_SENSN | 0x0E | 0xFF | 0xFF | same, N inputs |
| LOFF_SENSP | 0x0F | 0x00 / 0xFF | same | lead-off sensing on all P inputs only when `leadoff on` |
| LOFF_SENSN | 0x10 | 0x00 / 0xFF | same | same, N inputs |
| LOFF_FLIP | 0x11 | 0x00 | 0x00 | default polarity (P pulled up, N pulled down) |
| GPIO | 0x14 | reset (0x0F) | reset | GPIO1-4 are tied to DGND on the PCB; left as inputs |
| PACE, RESP | 0x15, 0x16 | reset | reset | not used |
| CONFIG4 | 0x17 | 0x00 / 0x02 | same | PD_LOFF_COMP=1 (comparators on) only with lead-off. SINGLE_SHOT=0 (continuous) |
| WCT1 | 0x18 | 0x00 | 0x00 | PD_WCTA=0, no augmented leads (no ECG WCT needed) |
| WCT2 | 0x19 | 0x00 | 0x00 | PD_WCTB=PD_WCTC=0 (the datasheet heading says 18h; the register map says 19h) |

Lead-off status: every frame starts with the 24-bit status word
`1100 | LOFF_STATP[7:0] | LOFF_STATN[7:0] | GPIO[7:4]`. The firmware checks the `1100` prefix
(flag bit 6 if it is wrong) and ORs STATP/STATN over each packet into `loff_p` / `loff_n`.

## First power-on bring-up checklist

Do these in order and stop at the first failure. Steps 1-6 are bench steps: the band is
**off-body** and powered from a current-limited supply on the test pads. A USB cable is allowed
only here.

1. **Bare board, current-limited supply** (3.7-4.0 V on the VBAT pad, 400 mA limit, enough for Wi-Fi TX peaks). Check +3V3
   and +3V0 (AVDD) before flashing. Because ~PWDN is tied high, the ADS1298s are active from
   power-on: expect about 2 × 3.3 mA for them (datasheet HR mode at 3 V: IAVDD 2.75 mA + IDVDD
   0.5 mA per chip) on top of the ESP32. With Wi-Fi associated the total rises to roughly
   80-120 mA average, with short peaks above that. A board that draws tens of mA with the ESP32
   held in reset (EN low) has a short or a part fitted backwards: stop.
2. **Flash and open the console** over the USB pads (`pio device monitor`). The boot status line
   must show `idA=0x92 idB=0x92 verify_err=0` (also available later with `status`).
   - idA wrong: SPI wiring, CS_A, U2 supplies.
   - idA OK, idB `0x00`/`0xFF`: U3 has no clock. Check that U2 CLKSEL is high, CLK_EN is set (U2
     CONFIG1 reads 0xA3 in `regs`) and the CLK trace; scope ≈2.048 MHz on CLK.
   - `regs` dumps both register files.
3. **DRDY.** `start`, then scope GPIO8: 4 kHz falling edges. `status` should show
   `missed_drdy=0 status_err=0`. Run `python3 neurband_rec.py --serial ... --duration 10` and check
   `lost=0 fw_drops=0 bad_crc=0`.
4. **Internal test signal.** `--mode test` (or the `test` command), then plot with `--raw`. All 16
   channels should show the same ≈1 Hz square wave with a step of about 1-2 mV (formula:
   VREF/2400 ≈ 1 mV; verify on the bench whether that is peak or peak-to-peak). The same
   amplitude at every gain proves the gain conversion. Channels 9-16 in phase with 1-8 proves
   the two chips are synchronous.
5. **Shorted-input noise.** `--mode short`. Datasheet Table 1 (HR, 3 V, 2.4 V ref) gives
   1.5 µVrms / 11.1 µVpp at 4 kSPS and gain 6 (full 1048 Hz bandwidth), and 1.1 µVrms at 2 kSPS.
   The live RMS (20-450 Hz) should therefore read ≈1 µV on every channel. More than ~2 µV
   means excess noise. Repeat on battery power over Wi-Fi with the USB cable removed: the numbers
   should not get worse.
6. **Lead-off.** `normal`, then `leadoff on` with no electrodes connected. The live `loff` line
   should show `P`/`N`/`X` on all channels. Bridge an input pair to the bias electrode with
   ~10 kΩ and those channels should go `.`. Turn `leadoff off` again for recording: the 6 nA
   source adds a DC offset of tens of mV on high-impedance dry electrodes.
7. **Wi-Fi.** `wifi <ssid> <pass> <pc-ip> 5005` over USB. **Disconnect the USB cable**, run on
   the battery, then `python3 neurband_rec.py --udp`. Check that `lost` stays near 0 at 4 kSPS.
8. **Electrodes on skin: battery + Wi-Fi only, no cable attached to any pad.** Normal mode,
   gain 6, bias electrode on (U2 RLD amp). A relaxed forearm should give a few µV RMS per channel
   with no 50 Hz in the live RMS; a fist clench should give tens to hundreds of µV. Check with
   `--raw` that DC offsets stay well inside ±400 mV. If they approach the rail, drop to gain 4
   or 3. Press BOOT and check that the marker shows in the plot.

## Known limitations / to verify on hardware

- The firmware has only been syntax-checked with host g++ against stub Arduino headers;
  PlatformIO was not available. Run `pio run` first and expect small fixes.
- The test-signal amplitude convention (peak vs peak-to-peak) and the CONFIG2[7:6] read-back
  value are not stated in the datasheet text. Both are treated leniently.
- The ESP32 cannot power-cycle or hard-reset the ADS1298s. If one locks up, the only recovery
  is the RESET opcode (a reboot does it) or removing the battery.
- No battery monitoring: watch the LiPo voltage externally or by run time.
- The marker is per packet (5 ms resolution at 4 kSPS), not per sample.
- The recorder keeps the whole recording in RAM: about 1 GB per hour at 4 kSPS. Fine for
  sessions of minutes; long sessions need chunked saving.
- On the bench, the USB-Serial/JTAG CDC has to sustain ~200 kB/s. Watch `fw_drops`. If it is
  not enough, switch to TinyUSB CDC (`ARDUINO_USB_MODE=0`).
