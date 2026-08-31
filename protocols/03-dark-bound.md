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

- **Gain 250, offset 15.** High gain gives the finest quantisation in electrons — one ADC count
  is 0.513 e⁻ there against 3 e⁻ at gain 100 — and the effect being hunted is a fraction of an
  electron per second. L14's failure was quantisation: median dark and median bias landed on the
  same code and the difference read as a clean zero.

  **250, not the 252 this protocol first named.** Session 02 published `gain_law.residual_pct`
  at 1.344 against its own 1% rule, so `g` is **not interpolable** and 252 falls between measured
  points. 250 is a swept point in both sessions: `g = 0.51303 ± 0.00097` e⁻/count from
  `ptc_constants.json`, and pedestal 76.66 counts with `R = 1.728` counts at offset 15 from
  `bias_sweep.csv`. Every number this night leans on is therefore measured rather than fitted.
  What 252 would have bought — commensurability with the archive, which was shot there — is
  worth nothing to this session, because no published constant comes from the archive and
  nothing here is compared against it.
- **ROI 1024 × 1024 at (1408, 568)**, as session 01, plus the full-frame block below.
- Cooler at −10 °C, held in band for a continuous 10 minutes before the first frame (L03, L04),
  and **logged per frame** — a TEC that loses the setpoint at 3 a.m. invalidates the block it was
  in, not the night, but only if the log says when.

## Capture

Bias frames here are the same minimum exposure as session 01. They are interleaved, not batched:
the whole point is that the pedestal is measured *near in time* to the dark it is subtracted
from. L14's negative dark current came from a master bias taken four hours away.

**The interleave is on a 20-minute clock, and that is the design parameter.** Every dark block
is bracketed by a bias block before and after, and no bracket spans more than ~20 minutes of
wall clock. See rule 2 below for why: the statistical floor is already four decades below the
number being tested, so more bias frames buy nothing statistically — what the cadence buys is
suppression of pedestal *curvature*, which survives bracketing and scales as the square of the
bracket span. Halving 40 minutes to 20 quarters it. It costs ~30 s of wall clock.

| block | exposure | frames | ROI | wall clock |
|---|---|---|---|---|
| B0 | minimum | 10 | 1024² | — |
| D1 | 1 s | 20 | 1024² | ~1 min |
| B1 | minimum | 10 | 1024² | — |
| D2 | 60 s | 20 | 1024² | ~20 min — one bracket, B1 to B2 |
| B2 | minimum | 10 | 1024² | — |
| D3 | **300 s** | **32** | 1024² | ~2 h 40 — insert 10 bias after every **4** darks (20 min) |
| D4 | 600 s | 8 | 1024² | ~1 h 20 — insert 10 bias after every **2** darks (20 min) |
| B4 | minimum | 10 | 1024² | — the last of D4's interleaved blocks *is* B4 |
| FF | 600 s | 4 | **full frame** | ~40 min |

**234 frames, 0.55 GB**, ≈ 5 h 15 including the cool-down.

**D3 is the `η_comb` stack**: 32 identical darks give
N = 4, 8, 16, 32, enough to see a stall — L15's stall was visible by N ≈ 8. The interleaved
bias blocks do not enter that stack; they sit between its frames and cost it nothing.

The bias blocks are also a result in their own right: ~15 evenly-spaced pedestal measurements
across five hours at gain 250, each good to 1.1 × 10⁻³ counts. Session 01 bounded the drift over
15 minutes (`pedestal_drift_rate`); this is the same question over the span a real imaging night
actually occupies, and it is what licenses — or refuses — every long-exposure dark subtraction
this project will later do.

Do not change gain, offset, ROI or setpoint at any point between B0 and B4. If something forces
a change, end the run there and record where; a night with two configurations in it is two
half-nights.

## Analysis rules, fixed before the data exists

Per CFA plane, on the mosaic, in ADC counts.

1. **`D`**: fit plane mean of the darks against exposure, with the bias level **interpolated in
   time** between the bracketing bias blocks, not taken from a session master and not taken from
   the nearest block alone. Linear interpolation across a bracket cancels the linear part of any
   pedestal drift exactly; taking the nearest block does not. Slope in counts/s → e⁻/px/s using
   the measured `g(250) = 0.51303 ± 0.00097`.
2. **The error bar on `D` is systematic, and it is the pedestal.** Establish this before fitting,
   because it decides what the night can claim. The statistical floor is
   `σ_R / √(N_px · N_frames)` on each side of the subtraction — 1.1 × 10⁻³ counts for a 10-frame
   bias block on a 512² plane, giving **1.3 × 10⁻⁶ e⁻/px/s** at 600 s. L14's inherited floor is
   `< 0.01`, four decades coarser, so nothing here is limited by frame count. What *is* the limit:
   **11.7 counts** of pedestal wander over a bracket would fake `D = 0.01 e⁻/px/s`, and 0.12
   counts would fake 10⁻⁴. So the published uncertainty on `D` is the residual scatter of the
   bias series about its own fitted trend, in counts, converted the same way — and the bound is
   reported as whichever of the two floors is coarser.
3. **Report the slope against that uncertainty before fitting anything to it.** If it does not
   exceed it, the result is `D < x e⁻/px/s`, quoted as a bound. **Never quote a signed value**
   (L14) — a negative dark current is a pedestal artefact announcing itself.
4. **`η_comb`**: σ of the stack mean against N, compared with σ₁/√N. Integration is a PixInsight
   step and belongs to a later build step — **tonight captures, it does not integrate.** Note for
   then: PixInsight's variance divides by n−1 and numpy's by n (L22).

   A stall now has a **pre-registered meaning it did not have when this protocol was written.**
   Session 02 measured `prnu = 1.021%` and published `fpn_term_present = true`, refuting MISSION's
   first assumption; session 01 measured `bias_fixed_pattern_ratio = 1.011`, i.e. essentially no
   fixed pattern at bias level. Fixed pattern is identical in every frame of a dark stack and
   therefore cannot average down, so the stack σ must stall at exactly the dark-signal
   non-uniformity floor — and since the bias level carries none, **a stall in a 300 s dark stack
   is a DSNU measurement, not an `η_comb` failure.** Report the stall level as DSNU in counts
   before reporting it as a loss factor.
5. **Full-frame block**: median-stack the 4 and look for structure. If glow reaches the central
   1024², `D` is not uniform and the ROI's own value is what the model uses. This is rule 4's
   question asked spatially rather than statistically; the two must agree, and disagreement is
   the interesting outcome.

### What each outcome decides

| observation | consequence |
|---|---|
| slope indistinguishable from zero | **`D` leaves σ² in the model.** Publish the bound; the temperature axis never opens |
| slope measurable and uniform | `D` stays as a constant at −10 °C; a `D(T)` sweep is still out of scope for pass 1 |
| glow inside the ROI | `D` becomes position-dependent — raise it before the model consumes it, do not average it away |
| stack σ tracks √N to N = 32 | `η_comb` ≈ 1 for rejection and averaging; the whole measured loss on sky is registration, and that is where to spend the next measurement |
| stack σ stalls | **DSNU exists at 300 s.** Record the level in counts, and record the stall against stack size and rejection settings, which are part of the constant and not context for it |
| bias series scatter exceeds the dark slope | the night bounds `D` and publishes the pedestal stability that bounded it; both are results |

## Record for the session

Ambient at start and end, capture tool, settle duration before B0, the sensor-temperature range
over the night, and any block that ran with a changed configuration.

**Ambient is assumed 25 °C.** Session 02 cooled from exactly 25.0 °C and held −10 °C on 65%
duty — 35% headroom — through a run with zero holds and zero retakes. This night reads the
sensor 60× less often per hour, and readout is what heats it, so the load is lighter than the
run that already passed. If ambient is materially above 25 °C, log it and watch the duty at
setpoint before starting B0 rather than discovering it at 3 a.m.

## LEGACY entries consumed

**L14** (dark below the detection floor) · **L15** (`η_comb` on frames that need no
registration). Both leave `LEGACY.md` when this session's notebooks publish. L22 is noted in
rule 4 but belongs to the PixInsight step and is not consumed here. L03, L04 and L25 were
consumed by sessions 01 and 02 and are already gone; this line named them while they were live.
