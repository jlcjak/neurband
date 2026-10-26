/* 4 kSPS -> 2 kSPS antialiasing decimator + high-pass + 0.25 uV/count scaling.
 *
 * 1. DC tracker (int64, ~0.31 Hz first order): removes the electrode offset before any float
 *    math, so float32 only carries the AC part (rounding < 2 nV rms, tools/gen_filters.py).
 *    Its value is also the per-channel raw-DC diagnostic.
 * 2. 127-tap Kaiser FIR (beta 5.65, 925 Hz cutoff, < 0.01 dB to 850 Hz, > 62 dB from 1 kHz,
 *    15.75 ms delay), evaluated only on every second input (decimation by 2).
 * 3. 4th-order Butterworth high-pass at 20 or 40 Hz (two DF2T biquads) at 2 kSPS.
 * 4. Scale to 0.25 uV/count, saturate to int16 (+-8.19 mV) and flag clips.
 * Cost ~70 multiply-adds per channel per output sample: ~1.2 M MAC/s for 8 channels. */
#include "dsp.h"

#include <string.h>
#include <zephyr/sys/util.h>

#include "filter_coefs.h"

#define DC_SHIFT 11 /* fc = 4000 / (2 pi 2^11) = 0.31 Hz */
#define DC_FRAC 8
#define EXTRA 32    /* FIR history slack: one memmove per 32 samples keeps the window contiguous */

static struct {
	int64_t dc;                 /* codes << DC_FRAC */
	float hist[FIR_TAPS + EXTRA]; /* window = hist[pos .. pos + FIR_TAPS - 1], newest first */
	float z[2][2];
} ch[8];
static int pos;
static bool seeded;
static float scale;
static const float (*hp)[5];

void dsp_reset(uint8_t gain, uint8_t hp_idx)
{
	memset(ch, 0, sizeof(ch));
	pos = EXTRA;
	seeded = false;
	/* code -> volts: 2 VREF / gain / 2^24 = 4.8 / gain / 2^24 (9.6.1.6, 2.4 V reference) */
	scale = (4.8f / (float)gain / 16777216.0f) / (DSP_UV_PER_COUNT * 1e-6f);
	hp = hp_coefs[hp_idx < ARRAY_SIZE(hp_freqs) ? hp_idx : 0];
}

void dsp_dc(int32_t dc[8])
{
	for (int c = 0; c < 8; c++) {
		dc[c] = (int32_t)(ch[c].dc >> DC_FRAC);
	}
}

bool dsp_push(const int32_t x[8], uint32_t idx, bool filter, int16_t out[8], uint8_t *clip)
{
	if (!seeded) { /* start the tracker at the first sample: no huge start-up step */
		for (int c = 0; c < 8; c++) {
			ch[c].dc = (int64_t)x[c] << DC_FRAC;
		}
		seeded = true;
	}
	if (pos == 0) { /* slide the newest FIR_TAPS - 1 samples back to the end */
		for (int c = 0; c < 8; c++) {
			memmove(&ch[c].hist[EXTRA + 1], &ch[c].hist[0], (FIR_TAPS - 1) * sizeof(float));
		}
		pos = EXTRA + 1;
	}
	pos--; /* newest sample at hist[pos] */
	for (int c = 0; c < 8; c++) {
		int64_t xq = (int64_t)x[c] << DC_FRAC;

		ch[c].dc += (xq - ch[c].dc) >> DC_SHIFT;
		float v = (float)(x[c] - (int32_t)(ch[c].dc >> DC_FRAC));

		ch[c].hist[pos] = v;
	}
	if (!filter || !(idx & 1)) {
		return false;
	}
	*clip = 0;
	for (int c = 0; c < 8; c++) {
		const float *w = &ch[c].hist[pos];
		float acc = fir_taps[FIR_TAPS / 2] * w[FIR_TAPS / 2];

		for (int k = 0; k < FIR_TAPS / 2; k++) { /* symmetric taps */
			acc += fir_taps[k] * (w[k] + w[FIR_TAPS - 1 - k]);
		}
		for (int s = 0; s < 2; s++) {
			const float *b = hp[s];
			float o = b[0] * acc + ch[c].z[s][0];

			ch[c].z[s][0] = b[1] * acc - b[3] * o + ch[c].z[s][1];
			ch[c].z[s][1] = b[2] * acc - b[4] * o;
			acc = o;
		}
		float y = acc * scale;

		if (y > 32767.0f) {
			out[c] = 32767;
			*clip |= 1u << c;
		} else if (y < -32768.0f) {
			out[c] = -32768;
			*clip |= 1u << c;
		} else {
			out[c] = (int16_t)(y + (y >= 0 ? 0.5f : -0.5f));
		}
	}
	return true;
}
