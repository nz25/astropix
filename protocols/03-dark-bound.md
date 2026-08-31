# Session 03 — the dark bound, and the stack for `η_comb`

**No light source. Cap on. Overnight — about 5 hours of capture.**

Numbered protocols are ordered by execution. This is planning session D. It runs after the
photon transfer curve, and everything it needs in electrons comes from there.

## What this session is for

| pins | how |
|---|---|
| `D` at −10 °C | slope of plane mean vs exposure, against **interleaved** bias |
| `η_comb` (upper bound) | a stack of identical darks — perfectly registered by construction (L15) |
| dark spatial structure | 4 full-frame long darks: is there glow, and is it inside our ROI |

**Not a `D(T)` sweep.** MISSION fixes the setpoint at −10 °C, so temperature is not an axis.
The best outcome here is an **upper bound** that deletes `D` from σ² — an upper bound is a
result and is recorded as one (L14).

**`η_comb` from darks is an upper bound and its provenance must say so.** A dark stack has no
registration and no resampling, so it measures the rejection-and-averaging half of the loss
honestly and reports the resampling half as exactly zero.

## Settings, and why

- **Gain 252, offset 15.** High gain gives the finest quantisation in electrons — one ADC count
  is about 0.5 e⁻ there against 3 e⁻ at gain 100 — and the effect being hunted is a fraction of
  an electron per second. L14's failure was quantisation: median dark and median bias landed on
  the same code and the difference read as a clean zero. Offset 15 and gain 252 also match the
  archive, so anything learned here reads across to it.
- **ROI 1024 × 1024 at (1408, 568)**, as session 01, plus the full-frame block below.
- Cooler at −10 °C, held in band for a continuous 10 minutes before the first frame (L03, L04),
  and **logged per frame** — a TEC that loses the setpoint at 3 a.m. invalidates the block it was
  in, not the night, but only if the log says when.

## Capture

Bias frames here are the same minimum exposure as session 01. They are interleaved, not batched:
the whole point is that the pedestal is measured *near in time* to the dark it is subtracted
from. L14's negative dark current came from a master bias taken four hours away.

| block | exposure | frames | ROI | wall clock |
|---|---|---|---|---|
| B0 | minimum | 10 | 1024² | — |
| D1 | 1 s | 20 | 1024² | ~1 min |
| B1 | minimum | 10 | 1024² | — |
| D2 | 60 s | 20 | 1024² | ~20 min |
| B2 | minimum | 10 | 1024² | — |
| D3 | **300 s** | **32** | 1024² | ~2 h 40 — insert 10 bias after every 8 darks |
| D4 | 600 s | 8 | 1024² | ~1 h 20 — insert 10 bias after every 4 darks |
| B4 | minimum | 10 | 1024² | — |
| FF | 600 s | 4 | **full frame** | ~40 min |

≈ 155 frames, well under 1 GB. **D3 is the `η_comb` stack**: 32 identical darks give
N = 4, 8, 16, 32, enough to see a stall — L15's stall was visible by N ≈ 8.

Do not change gain, offset, ROI or setpoint at any point between B0 and B4. If something forces
a change, end the run there and record where; a night with two configurations in it is two
half-nights.

## Analysis rules, fixed before the data exists

Per CFA plane, on the mosaic, in ADC counts.

1. **`D`**: fit plane mean of the darks against exposure, with the bias level taken from the
   nearest interleaved block, not from a session master. Slope in counts/s → e⁻/px/s using
   `g(252)` when session 02 provides it.
2. **Report the slope against its own uncertainty before fitting anything to it.** If it does not
   exceed it, the result is `D < x e⁻/px/s`, quoted as a bound. **Never quote a signed value**
   (L14) — a negative dark current is a pedestal artefact announcing itself.
3. **`η_comb`**: σ of the stack mean against N, compared with σ₁/√N. Integration is a PixInsight
   step and belongs to a later build step — **tonight captures, it does not integrate.** Note for
   then: PixInsight's variance divides by n−1 and numpy's by n (L22).
4. **Full-frame block**: median-stack the 4 and look for structure. If glow reaches the central
   1024², `D` is not uniform and the ROI's own value is what the model uses.

### What each outcome decides

| observation | consequence |
|---|---|
| slope indistinguishable from zero | **`D` leaves σ² in the model.** Publish the bound; the temperature axis never opens |
| slope measurable and uniform | `D` stays as a constant at −10 °C; a `D(T)` sweep is still out of scope for pass 1 |
| glow inside the ROI | `D` becomes position-dependent — raise it before the model consumes it, do not average it away |
| stack σ tracks √N to N = 32 | `η_comb` ≈ 1 for rejection and averaging; the whole measured loss on sky is registration, and that is where to spend the next measurement |
| stack σ stalls | record the stall against stack size and rejection settings, which are part of the constant, not context for it |

## Record for the session

Ambient at start and end, capture tool, settle duration before B0, the sensor-temperature range
over the night, and any block that ran with a changed configuration.

## LEGACY entries consumed

L03, L04 (cooling) · L14 (dark below the detection floor) · L15 (`η_comb` on frames that need no
registration) · L22 (deferred to the PixInsight step) · L25 (gain 252 predictions).
