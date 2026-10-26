# neurband rev C firmware: nRF52832-QFAA + one ADS1298, BLE streaming. See docs/firmware_c.md.
#   west build -b nrf52dk/nrf52832 firmware_c        (boards/nrf52dk_nrf52832.overlay is applied automatically)
cmake_minimum_required(VERSION 3.20.0)

# The DK board definition turns on the nRF52 DC/DC regulator. Rev C has no DCC inductor and
# must stay in LDO mode. Zephyr >= 4.0 does that in devicetree (overlay, &reg). Zephyr 3.7
# (NCS 2.x) uses Kconfig instead, so add zephyr37.conf there. west exports ZEPHYR_BASE.
if(EXISTS "$ENV{ZEPHYR_BASE}/VERSION")
  file(STRINGS "$ENV{ZEPHYR_BASE}/VERSION" _zmajor REGEX "^VERSION_MAJOR")
  if(_zmajor MATCHES "= *3$")
    list(APPEND EXTRA_CONF_FILE ${CMAKE_CURRENT_LIST_DIR}/zephyr37.conf)
  endif()
  # nRF Connect SDK: SoftDevice Controller throughput settings (symbols don't exist upstream)
  if(EXISTS "$ENV{ZEPHYR_BASE}/../nrf/subsys/bluetooth/controller/Kconfig")
    list(APPEND EXTRA_CONF_FILE ${CMAKE_CURRENT_LIST_DIR}/sdc.conf)
  endif()
endif()

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(neurband_c)

target_sources(app PRIVATE src/main.c src/ble.c src/acq.c src/ads1298.c src/dsp.c src/imu.c)
