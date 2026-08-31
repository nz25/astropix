# Session 02 — photon transfer curve

**Light source required.** This is the first session that cannot run with the cap on, and the
first that runs `light-source.md`.

Numbered protocols are ordered by **execution**, not by the letters used while planning. This
session runs before the dark bound (`03-dark-bound.md`), which is written but unrun: `g(gain)`
and `R(gain)` in electrons are the two most-consumed rows of MISSION's constants table, and
L14 predicts the dark session yields an upper bound rather than a value.

## What this session is for

| pins | how |
|---|---|
| `g(gain)` — e⁻ per ADC count | slope of pair-difference variance against signal, per CFA plane, per gain |
| the gain law | `log10 g` fitted against gain setting; the residual is the test of L29 |
| `R(gain)` in electrons | session 01's measured `R` in counts × `g(gain)` — **no read noise is measured here** (L10) |
| **whether σ² is shot plus read and nothing else** | single-frame spatial variance against pair-difference variance at the same level (MISSION's first assumption) |

**What it is not for.** Linearity, `ceiling(gain)` and full well: those need a *characterised*
light source, a shrunk ROI and a per-channel bend (L09, L12, L28), and are a later session.
Nothing here measures a bend, and no rung is placed to find one. Nor is it for dark current.

**Why it can run before the light source is characterised.** L31's unexplained 1.79%
frame-to-frame instability and L09's 3.8% illumination unevenness both fail to reach a PTC:
the curve plots variance against *measured signal*, never against commanded exposure, and it
differences frame pairs, so it is blind to fixed pattern. The exemption is L09's own — its
shrink-the-ROI rule is a linearity rule — and it stays queued there for the session that needs
it. A drifting panel moves a point along the curve, not off it.

## Prerequisite: a capture path

`astropix/asi.py` drives the camera and `astropix.fits.write` puts frames on disk; the loop over
the gain list and the exposure ladder lives in `notebooks/05_ptc.ipynb`, because the library does
one frame and the notebook does the loop. Every frame carries `DATE-OBS`, `GAIN`, `OFFSET`,
`EXPTIME` and sensor temperature, read back from the controls *after* the exposure rather than
from what was asked for.

## Pre-flight

Run all three items of `light-source.md`. Everything the old eight-item bench pre-flight also
listed is now either a gate below or a guard in `asi.py` that refuses rather than reminds.

Item 1's ten-minute warm-up **stands unqualified this session.** It is a precaution against an
untested hypothesis, and the trace that would retire it (L31 arms 1 and 2) is deliberately not
folded in here: it pins down no term this session needs, and a session with two purposes is two
sessions run badly.

### Gate 1 — white balance, verified from pixels (L01)

Set `WB_R = WB_B = 50` on open. Capture 5 darks at gain 100 and confirm the modal step between
adjacent distinct values is **16 on all four CFA planes**. Greens at 16 with red 17/18 and blue
24 means white balance is still being applied.

**Nothing captured before this passes is usable.** Stop the session; do not "correct it later".

### Gate 2 — the cooler holds

−10 °C, held in band (±0.5 °C) for a continuous **30 seconds** before the first frame, judged by
the temperature trend and not by duty cycle. Measured 2026-08-28: this TEC approaches
monotonically and does not ring.

**The whole session runs in one kernel.** Closing the camera drops the cooler while `Gain` and
`Offset` persist across the same close, so a session split across two processes is not possible
and a dead kernel restarts the cool-down from ambient.

### Gate 3 — the saturating exposure, measured per gain (`light-source.md` item 3)

Solve `t_sat(gain)` from the *measured* flux at each of the nine gains. **Never extrapolate it**
from a per-sheet attenuation figure: stacked diffusers give diminishing returns and grey level is
exhausted below about 25% of full scale because the backlight leaks (L07, L08).

`t_sat` is what sets this session's wall clock, and it is not knowable before the gate runs. The
protocol fixes the ladder's **shape**; `light-source.md` item 3 fixes its **scale**.

## Capture

Offset: **15** throughout — `project_offset` in `results/bias_constants.json`, fixed by session
01 and not an axis any more.
ROI: **1024 × 1024 at (1408, 568)** — even origin and extent, or the Bayer phase shifts (L05).
Not shrunk: L09's small-ROI rule is a linearity rule and does not apply here.

Discard the **first 2 frames after every gain change** and the **first frame after every exposure
change**, and do not write them.

Temperature discipline as session 01: a frame whose header says it was shot outside the band is
**not written — it is retaken**, and a reading on the warm side holds the run for a continuous
`asi.RECOVER_S` before retaking. Unlike session 01's 32 µs bias frames, a retake here costs a
real exposure, so the retake budget binds sooner: **10 retakes of one frame slot, or a hold past
300 s, stops the session.** Check ambient and the fan.

### The gain set

**0, 50, 100, 190, 200, 250, 300, 450** — eight.

Seven of them are L25's published rows, so the comparison is row-for-row with no interpolation on
either side. 190 and 200 straddle the HCG threshold measured in session 01. 450 is the vendor
chart's last point and the top of this project's gain domain (`CLAUDE.md`).

**Gain 600 is not in the set and is not an omission.** It is out of scope: the pedestal takes
a quarter of the scale there, the well is ~29 e⁻, and it is what would have forced this session's
light source to 4000× attenuation instead of ~800×. Dropping it is what makes the bench
reachable with paper.

**Eight and not every gain session 01 measured, because session 01 already measured `R` in ADC counts across its own grid.**
`R` in electrons is `R_counts × g(gain)`, so this session needs `g` only at enough gains to *fit
and validate* the log-linear law; the law then carries `g` onto session 01's existing grid. If
the law fails its own residual test below, that economy is withdrawn and the gain set is the
thing to widen.

### The exposure ladder

Twelve rungs per gain, **geometric** at ×1.679, from 0.3% to 90% of `t_sat(gain)`:

```
0.3  0.5  0.85  1.4  2.4  4.0  6.8  11.4  19.2  32  54  90   (% of t_sat)
```

Geometric and not linear because of L10: with a linearly-spaced ladder every point sits in the
bright end, the intercept is extrapolated back from variances in the thousands, and a synthetic
test recovered **7.1 e⁻ for a true 3.0 e⁻** while the gain from the same fit was good to 3%. The
five rungs below 4% are there to constrain the low end — not because the intercept is the answer
(it is not, see the analysis rules) but because a curve unconstrained near zero is a curve whose
slope absorbs the error.

**The top rung is capped where the frame's own noise stops fitting under 4095.** A rung is only
usable while the *spread* of its pixels clears the top code: censor the bright tail and the
measured variance comes in low, which reads as a `g` that is too high — and pair-differencing
cannot see through it, because the clipping happens before the subtraction. The margin is a
frame's own sigma, `sqrt(S/g)`, so it is the low-`g` gains that bind, and only two rungs move:

| gain | top rung | margin at 90% | why |
|---|---|---|---|
| 0–250 | 90% | 4.8–20 σ | unchanged |
| 300 | **89%** | 3.6 σ | 0.02% of pixels clipped |
| 450 | **75%** | 1.5 σ | **6.8%** clipped; σ is 259 counts there |

Formally the top rung is `min(90%, (headroom − 4σ)/headroom)`, with σ from L25's gain anchor and
L29's slope — a **prediction used to place a rung**, never an input to a result, and conservative
in the direction that matters since a larger true `g` only widens the margin. The cost is 0.08 dex
off the top of a 300:1 ladder, which the slope does not notice.

Measured, not anticipated: the scout of 2026-08-31 read `g(450)` as 0.0511 at its clean rungs and
**0.0593 at 90%** — a 13.5% variance deficit, reproduced in two runs at different panel
brightness. Uncapped, four frames per gain would be shot at a rung that cannot give a right
answer, at the gain that anchors the top of the gain law.

| block | gains | rungs | frames each | notes |
|---|---|---|---|---|
| 1 — ladder | the nine | 12 | 4 | two independent pairs per rung, so the variance has a repeat |
| 2 — bias | the nine | — | 10 | one block per gain, shot adjacent to that gain's ladder |

≈ 464 frames written, ≈ 0.9 GB. Capture time is `t_sat`-dominated and follows from Gate 3.

**Block 2 is a per-gain pedestal, not a re-measurement of read noise.** It exists because signal
must be measured against a pedestal from *this* session: L14's cautionary tale is a dark sitting
one count below a bias shot four hours earlier, which produced a negative dark current. Session
01 measured pedestal drift at **−0.00133 ± 0.254 counts/min** — two orders of magnitude inside
its own uncertainty — which is why one block per gain suffices and rung-by-rung interleaving does
not have to be paid for.

## Analysis rules, fixed before the data exists

Statistics on the CFA mosaic, split RGGB, never debayered. Values in ADC counts.

1. **Signal** = plane mean of (flat − that gain's block-2 pedestal). Per plane, never on the
   frame mean (L12).
2. **Variance** = σ² of the difference of a frame pair, divided by 2. Blind to fixed pattern by
   construction, which is what makes rule 4 a test rather than a tautology.
3. **`g(gain)`** = signal / variance, as the slope of a straight line through the rungs, per
   plane. **Read noise is passed in** from `results/bias_constants.json`, not taken from the
   intercept (L10). The fitted intercept is retained as a cross-check and is never the answer.
4. **The FPN test.** Single-frame spatial variance against pair-difference variance at the same
   signal level. Equal ⇒ no fixed-pattern term. Excess in the single-frame number ⇒ PRNU, and
   L32's **0.61%** is the figure to compare against.
5. **The gain law.** Fit `log10 g` against gain setting. L29 predicts a slope of
   **−0.00502/unit** against the 0.1 dB law's −0.00500, at 1.0% scatter.
6. **The free cross-check (L11).** Two-point photon transfer,
   `g = signal / (var_flat − var_bias)`, run on the indexed archive at gain 50 and 252 — frames
   that already exist and cost no bench time. The retired project recovered its own bench gain
   to 1.23% this way.

### What each outcome decides

| observation | consequence |
|---|---|
| `g₀` lands in **9.38–9.46** | header `EGAIN`, L25's PTC and ZWO's `GAIN=195` annotation are all reproduced; publish the measured value with provenance, and `EGAIN` becomes a standing check rather than a source |
| `g₀` outside that band | the header `EGAIN` law is wrong, and every electron figure in the repo — including `00`'s section 0 — is rescaled from the measured value |
| log-law residual under 1% | `g` is interpolable; `R(gain)` in electrons is published at all 61 of session 01's gains |
| residual over 1%, or a step at HCG | interpolation is forbidden and the gain set widens. L30 predicts no step here — the HCG discontinuity appears in read noise and *not* in e⁻/ADU — so a step would refute L30 as well |
| pair variance linear in signal to the top rung | MISSION's "no noise term that fails to scale with `t`" holds over the tested range, and `R²/t` remains the whole sub-exposure question |
| single-frame variance exceeds pair variance beyond the pair repeatability | **an FPN term exists.** MISSION's first assumption is refuted rather than untested, and the model gains a term that survives lengthening the sub |
| L11's archive gains agree with the bench to a few % | two datasets with nothing in common agree, which is stronger evidence than either alone |
| they disagree | one carries a systematic. **Do not average them** — find it, or publish the bench value with the disagreement recorded beside it |
| gain 450 is out of family | the least constrained point in the set: no L25 row, and the vendor chart's last. It weakens the top end of the law and is not on its own evidence the law is wrong. Session 01's telegraph noise and 4.027 offset slope were at gain 600, which is now out of scope |

## Record for the session

Ambient temperature at start and end, panel warm-up start time, grey level, sheet count, the
measured flux and `t_sat` per gain from Gate 3, ROI, offset, WB values after setting, the Gate 1
modal steps per plane, cooling settle duration, capture tool and version, and anything touched
mid-session.

## LEGACY entries consumed

L09 (as the exemption licensing the full ROI) · L10 (geometric ladder; read noise passed in) ·
L11 (the archive cross-check) · L25, L29, L30 (predictions to reproduce or refute) ·
L31 (as the reason a PTC may run before the light source is characterised) ·
L32 (PRNU, as the prediction the FPN test compares against).

Each verified entry moves to its destination and leaves `LEGACY.md` when the analysis notebook
publishes. A session that ends with its entries still queued has not finished.
