/* Streaming DSP for the default 2 kSPS / 16-bit stream (docs/firmware_c.md "DSP"). */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define DSP_UV_PER_COUNT 0.25f

void dsp_reset(uint8_t gain, uint8_t hp_idx);
/* Feed one 4 kSPS frame (codes). Updates the DC tracker. Returns true when a 2 kSPS output
 * sample was produced (odd input indices) and writes it to out (0.25 uV/count). */
bool dsp_push(const int32_t x[8], uint32_t idx, bool filter, int16_t out[8], uint8_t *clip);
void dsp_dc(int32_t dc[8]); /* current DC estimate per channel, codes */
