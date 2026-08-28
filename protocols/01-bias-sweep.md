# Session 01 — bias sweep and pedestal drift trace

**No light source. Cap on.** This session can run before the bench rig exists.

Numbered protocols are ordered by **execution**, not by the letters used while planning. This is
planning session A. `bench-setup.md` is the pre-flight for all of them and is unnumbered.

## What this session is for

| pins | how |
|---|---|
| `pedestal(gain, offset)` | mean of a bias frame per CFA plane, per gain |
| `R(gain)` in ADC counts | pair-difference σ per gain — **not** a PTC intercept (L10) |
| HCG threshold | the read-noise cliff, dense sampling either side of 200 (L26) |
| pedestal drift rate | 15-minute continuous trace; the interleaving requirement for session 02 |
| **the offset setting itself** | the lowest offset whose clipped fraction stays under 0.1% at every gain (L13) |

**What it is not for.** `g(gain)` — that needs light and is session 03. Nothing here converts
ADC counts to electrons, and nothing here should try.

## Prerequisite: a capture path

`astropix/asi.py` drives the camera and `astropix.fits.write` puts frames on disk; the loop over
the gain list lives in `notebooks/03_bias_sweep.ipynb`, because the library does one frame and
the notebook does the loop. Every frame carries `DATE-OBS`, `GAIN`, `OFFSET`, `EXPTIME` and
sensor temperature, read back from the controls *after* the exposure rather than from what was
asked for. **Record which tool was used in the session record** — it is part of the provenance.

## Pre-flight

Run `bench-setup.md` items **1, 2, 4, 5**. Items 0, 3, 6 and 7 are light-source items and are
**not applicable** with the cap on — skip them deliberately, do not adapt them.

### Gate 1 — white balance, verified from pixels (L01)

Set `WB_R = WB_B = 50` on open. Capture 5 darks at gain 100 and confirm the modal step between
adjacent distinct values is **16 on all four CFA planes**. Greens at 16 with red 17/18 and blue
24 means white balance is still being applied.

**Nothing captured before this passes is usable.** Stop the session; do not "correct it later".

### Gate 2 — the cooler holds

−10 °C, held in band (±0.5 °C) for a continuous **30 seconds** before the first sweep frame,
judged by the temperature trend and not by duty cycle (L03, L04).

Thirty seconds, not the ten minutes this protocol first asked for. Measured 2026-08-28,
`data/session01/cooldown.csv`: first in-band reading at 571 s and **zero excursions in the 600 s
that followed** — this TEC approaches monotonically and does not ring, so a window sized for
ringing was measuring nothing. What the long window incidentally provided was a settled duty
cycle; 30 s releases at −9.5 °C with duty still climbing, and that is now the capture loop's
problem to solve (below) rather than this gate's. **The two changes are load-bearing together.**

**The whole session runs in one kernel.** Closing the camera drops the cooler — measured
2026-08-28: `CoolerOn` set to 1, closed, reopened, reads 0, while `Gain` and `Offset` persist
across the same close. Cooling in one process and capturing in another is not possible, and if
the kernel dies the cool-down starts from ambient. Never assume the camera is still cold: with
the cooler off the sensor reports a flat 0, so nothing contradicts the assumption.

## Capture

Exposure throughout: **the camera minimum**. Record the value; it is not assumed.
ROI: **1024 × 1024 at (1408, 568)** — even origin and extent, or the Bayer phase shifts (L05).
The ROI is also a disk decision: full frame would cost 16 MB a frame and C: is tight.

Discard the **first 2 frames after every gain or offset change** and do not write them.

**Gap of 0.2 s between sweep exposures, and a temperature check after every frame.** The bias
exposure is 32 µs, so the cadence — and the sensor's self-heating — is entirely readout, USB and
the file write. The first run shot back to back at ~9 fps and held the sensor a full degree above
setpoint from 15 s into block 1 to the end of it: 1,083 consecutive frames out of band, while
blocks 3 and 4 at the same rate were clean. That is a control-loop transient, not a capacity
limit — the TEC settled at 67% duty with headroom to spare.

A frame whose header says it was shot outside the band is **not written — it is retaken.** At
32 µs a retake costs the readout and nothing else, and what lands on disk is exactly the planned
frame count per setting, all in band, needing no exclusion rule downstream to stay honest. A
reading on the *warm* side of the band additionally **holds the run** before retaking: keep
shooting discards — never idle, or the duty winds back down and the transient repeats on resume
— until the sensor has been in band for a continuous `asi.RECOVER_S` (10 s). The cold side
passes on its own; that is the TEC undershooting.

**Both waits are bounded, and neither bound is a band to widen.** A hold past 300 s, or 10
retakes of one frame slot, stops the session: check ambient and the fan.

| block | offset | gains | frames each | notes |
|---|---|---|---|---|
| 1 — coarse | 15 | 0 to 600 step 10 (61) | 20 | the main sweep |
| 2 — fine | 15 | 180 to 220 step 2 (16 new) | 20 | the HCG cliff (L26) |
| 3 — offset arm | 0, 5, 10, 20, 25, 30, 35, 40, 45, 50 | 0, 50, 100, 190, 200, 252, 300, 600 | 10 | offset 15 is covered by block 1 |
| 4 — drift trace | 15 | 100 only | 450 | one frame every **2 s for 15 minutes** |

≈ 2,900 frames, ≈ 6 GB. ≈ 29 min of capture after the settle — 14 min of sweep at the 0.2 s gap
plus the 15 min the drift trace paces itself over. The gap costs about what the shorter Gate 2
window gives back, so the session is no longer than the first run.

**Offset 15 is ZWO's recommended value and the anchor of the whole archive** — all 15,090
readable frames were shot there. It is therefore a hypothesis with a strong prior, not a
setting to inherit. Blocks 1 and 2 run at 15; block 3 walks 0 to 50 in steps of 5 around it,
10 frames a point being ample for a plane mean and a single pair difference.

**Offset 0 at gain 600 is expected to clip, and that is the measurement.** L13's cautionary
tale is a run where 58 pixels of a million read zero and were mistaken for a clipped offset;
the fix is to report the *fraction* and compare it against the distribution's distance from
zero in read noises. The arm sweeps down to 0 precisely so the floor is crossed on purpose,
under measurement, rather than guessed at.

Block 4 is the dark control arm of the stability question, folded in here because it needs the
same cap and the same cooling cycle. It answers *how fast does the pedestal move*, which is what
licenses — or forces — the bias interleaving in session 02.

## Analysis rules, fixed before the data exists

Statistics on the CFA mosaic, split RGGB, never debayered. Values in ADC counts.

1. **`R(gain)`** from σ of the difference of frame pairs, divided by √2. Report per plane.
2. **`pedestal(gain, offset)`** as the plane mean. Fit `A + B · amplification` **per
   conversion-gain branch**, not across the transition (L27). A single fit landing between the
   branches and mispredicting both by 8–17% is the failure mode being avoided.
3. **Clipping** as a *fraction* against the 0.1% threshold, reported beside the distribution's
   distance from zero in read noises (L13). A handful of pixels at 0 at gain 600 is defective
   cold pixels, not a clipped offset.
4. **Drift** as plane mean vs `DATE-OBS`, with sensor temperature overlaid.

### What each outcome decides

| observation | consequence |
|---|---|
| `A` scales linearly with offset and `R` is offset-independent to <0.5% | **offset is retired as an axis.** Fix it once and never sweep it again |
| clipped fraction stays under 0.1% at every gain down to some offset `k` | the project offset is the smallest safe value with margin — 15 if the evidence supports it, and a measured number either way |
| clipping appears at 15 at any gain we intend to use | ZWO's recommendation does not hold on this rig at this setpoint, and that is a result worth `results/` |
| a read-noise cliff between two adjacent fine-grid gains | that is the HCG threshold; ZWO's own chart annotates **200** (`vendor/asi585specs/`), which is also what the retired project measured — the "ZWO say 252" belief has no source and 252 is the ASI2600's threshold |
| no cliff anywhere in 180–220 | widen the fine grid before concluding; a threshold that isn't where two independent sources say it is needs more evidence than one night |
| pedestal drift over 15 min below the frame-to-frame scatter | session 02's interleaving is a precaution, and its cost can be reduced |
| pedestal drift measurable | interleaving is mandatory in session 02 **and** in the session 03 bias pairs |

## Record for the session

Ambient temperature at start and end, capture tool and version, camera minimum exposure, ROI,
offsets used, WB values after setting, the Gate 1 modal steps per plane, cooling settle duration,
and anything touched mid-session.

## LEGACY entries consumed

L01, L03, L04, L05 (pre-flight, via `bench-setup.md`) · L10 (read noise from bias pairs) ·
L13 (clipping is a fraction) · L25, L26, L27, L29 (predictions to reproduce or refute) ·
L31 (the dark control arm only; arms 1 and 2 need the light source and are a later session).

Each verified entry moves to its destination and leaves `LEGACY.md` when the analysis notebook
publishes. A session that ends with its entries still queued has not finished.
