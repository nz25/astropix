# Session 05 — linearity, `ceiling(gain)` and full well

**Light source required**, and this is the session `02-ptc.md` deferred to: linearity needs a
*characterised* source, a shrunk ROI and a per-channel bend (L09, L12, L28). It is the last
bench-only row of MISSION's constants table — `ceiling(gain)` / full well. Everything left after
it (`F_sky`, `eta_comb`, `t_dead`) comes from sky frames or the archive, not from the panel.

## What this session is for

| pins | how |
|---|---|
| `ceiling(gain)` — usable saturation, ADC counts | the level at which response departs 1% from a line fitted to the low rungs, per CFA plane, per gain |
| full well, e⁻ | `(ceiling − pedestal) × g(gain)`, with `g` consumed from `results/ptc_constants.json` and never re-measured here |
| **whether the bend is the converter or the pixel** | a bend at the same *level* across gains is the ADC; one at the same *charge* scales as `1/g` (L12) |
| the plane that binds the star-colour ceiling | per-plane saturating exposures under one white-ish source |
| `S = F · t` | the linearity residual over the working range is the only direct test MISSION's signal term ever gets |
| **L31** — is a level at fixed light steady in wall clock and in exposure length | Gate 6, below. It is a prerequisite here, not a second purpose: an exposure ladder at fixed illumination is exactly the measurement L31 says may not be repeatable |

**What it is not for.** Gain, read noise, dark current, PRNU. `g(gain)` is an input. No pair
differencing happens here and no variance is published; the quantity is a *mean* level, and the
things that ruin a mean — drift, illumination structure, pedestal state — are what this protocol
spends its design on.

## Pre-flight

All three items of `light-source.md`. Item 1's ten-minute warm-up **stands until Gate 6 has run**,
and Gate 6 is what retires or confirms it — a trace flat from cold deletes item 1 (its own
instruction), a trace that is not flat keeps it and finally gives it a number.

**Seven gates**, in this order, because each needs the one above it. Gates 1 and 2 are
`02-ptc.md`'s, unchanged and not restated: white balance verified from pixels (the modal step of
16 on all four planes) and the cooler held at −10 °C in band for 30 s. The whole session runs in
one kernel.

| gate | settles |
|---|---|
| 1 | white balance, from the pixels |
| 2 | the cooler holds |
| 3 | the panel's redraw period |
| 4 | the grey level per gain, then `t_sat` at that level |
| 5 | whether the panel flickers at the shortest rungs |
| 6 | L31 — the light is steady in wall clock and in exposure length |
| 7 | the illumination map, which chooses the analysis ROI |

Gates 3 to 5 exist because of one thing session 02 could ignore and this session cannot. **A PTC
plots variance against measured signal, so a misbehaving panel moves a point along the curve.
Linearity plots signal against commanded exposure**, and a screen that redraws every sixteen-odd
milliseconds is not a steady lamp on that timescale.

### Gate 3 — the panel's redraw period, measured rather than assumed

"60 Hz" is folklore about a device nobody measured. `grey-patch.html` times its own
`requestAnimationFrame` callbacks and reports the median interval to `patch-server.py`; the
notebook reads it back.

**Two readings, and the second is the point.** A display with adaptive refresh serves a *still*
page fewer frames than the panel drives, so a slow rate could mean a slow panel or a throttled
page — opposite consequences. The probe settles it: the page animates a 4×4 px black-on-black dot
in its corner, forcing a repaint every frame. A rate that rises with the dot on means the page was
throttled. The dot is off during every captured frame and sits outside any sane ROI.

The period taken forward is the **faster** of the two, because the panel cannot drive slower than
the frames it delivers. Everything below is scaled against it.

### Gate 4 — the grey level per gain, then `t_sat` at that level

`t_sat` is the exposure at which the brightest plane fills the headroom above its own pedestal,
measured at every gain and never extrapolated from one flux and the 0.1 dB law
(`light-source.md` item 3).

**The grey level is chosen per gain.** At one fixed level the ladder scales with `1/amplification`,
so a high gain's rungs are ~180× shorter than gain 0's and land inside a redraw or two. The rule:
**the level that puts `t_sat` nearest 22 s**, floored at level 64 — which puts this ladder's
faintest rung near 300 redraws, or 0.33% of quantisation against a 1% bend.

Nearest, not brightest. Brighter is faster and dimmer is quieter, and the first run settled which
side of that trade this bench sits on. **A gain whose faintest rung cannot reach 150 redraws at
any level the panel has is not shot at all** — the notebook stops rather than filling a ladder
with rungs quantised by more than the bend they are looking for.

Two things make this cheap. Grey level is the LCD blocking light, **not** the backlight dimming, so
it changes flux without touching the thing that might flicker — which is why the brightness slider
is *not* an axis here and stays where session 02 recorded it. And nothing in this session compares
levels across gains: the bend is measured per gain, in counts.

The floor is measured, not chosen: session 02's own curve gives flux 532 at level 160 and 85 at
level 0, so below about a quarter of white the backlight leaking through a black LCD is most of
what is left and level stops being a control (L07, L08).

### Gate 5 — does the panel actually flicker?

Gate 4 made the rungs as long as the light allows; this asks whether the ones still short are
usable. It is the only test here the page cannot run: the page reports what it is *told* to draw,
and only the sensor sees what the backlight *did*.

At the gain with the shortest rungs:

1. **Twenty frames at the faintest rung.** Their scatter against the shot noise of the mean,
   `sqrt(S/g + R²)` over the pixel count — a computable number, not a guess. Flicker shows as
   scatter far above it, because each frame catches a different slice of the redraw cycle.
2. **Three exposures a factor of two apart, all sub-redraw.** Counts per second must be constant.
   If it climbs with exposure, short frames are being short-changed — and *that* failure would
   masquerade as non-linearity at the bottom of the ladder and tilt the reference line.

**A failure does not stop the session.** It moves the reference line onto the longer rungs, under
analysis rule 4, and gets published either way.

### Gate 6 — the light source is steady, in wall clock and in exposure length (L31)

Two arms, at one gain — **100**, L31's unstable one — before the ladder:

1. **Drift.** One fixed exposure at the monitor frame's 25% of `t_sat`, repeated continuously for
   **5 minutes**, timestamped. Plane mean against wall clock. Session 01's dark arm already ran
   this with the light taken out and was flat to −0.00133 ± 0.254 counts/min, so anything is upstream
   of the sensor.
2. **Exposure length against elapsed time.** Interleave a short (~10% `t_sat`) and a long (~90%)
   exposure, alternating, for **5 minutes**. This is the arm the retired project could not run:
   their two gains differed in exposure length *and* in elapsed time, so the confound was built in.

**Pass is a number, not a feeling:** the drift arm's fitted slope, and each arm's frame-to-frame
scatter, both published. L31's contrast to beat is 1.79% at gain 100 against 0.011% at gain 200.

**A failing Gate 6 does not stop the session.** The ladder's monitor frames (below) divide out
drift on any timescale longer than one frame pair. What Gate 6 decides is whether that correction
is a safety net or load-bearing — and that has to be known before the numbers are read, not after.

### Gate 7 — the illumination map (L09)

One well-exposed frame at ~50% `t_sat`. Measure peak-to-peak variation of the plane means across
the central **1024, 512 and 256** boxes. L09 predicts **3.8%, 1.25%, 0.53%**. A 3.8% spread
saturates the bright corner ~4% of exposure before the dim one, which smears a 1% bend over more
range than the bend itself.

**This gate is a first look, not the decision.** One frame cannot separate illumination from shot
noise, and the noise per tile *grows* as the box shrinks - judge boxes on that number and the
flattest box reads as the worst. The analysis makes the real choice from the monitor stacks, with
the noise floor measured (odd frames against even) and subtracted, and takes the **largest** box
under 0.5%: among boxes flat enough to trust, the biggest has the quietest mean. Tiles are a fixed
32x32 mosaic pixels at every box. Capture stays at 1024 regardless.

## Capture

Offset **15**. Capture ROI **1024 × 1024 at (1408, 568)** — identical to session 02, so the two
sessions are row-for-row comparable, and even origin and extent or the Bayer phase shifts (L05).
Analysis crops to the Gate 7 box.

Discard the first 2 frames after every gain change and the first frame after every exposure
change, and do not write them. Temperature discipline and the retake budget are session 02's:
10 retakes of one frame slot, or a hold past 300 s, stops the session.

### What the first run measured, and why the design changed

The first run (2026-09-05, 1339 frames) passed every gate and **could not measure a ceiling.** Its
published ceilings — 539 counts at gain 0, one per-plane value of −68 — were noise crossings, not
measurements, and were removed from `results/`. **That run is deleted in full**: frames, gate
tables and all. Every diagnostic it took is re-measured by the gates below in the same session, so
the only thing its data still backed was the account of its own failure, and that account is the
next two paragraphs. The numbers in them are quoted from a run whose data is gone; they are the
reason for a design, never a measurement to cite.

Its rungs scattered **1.2–2.5%** about their own straight line — worst rung 2.1% at gain 0 rising
to 5.4% at gain 250 — against a bend defined as a 1% departure. Within a rung the three frames
agreed to under 0.3%, and the excursions appeared on all four planes at once, so it is the light
source and not the sensor.

The mechanism is the panel being a screen: light arrives in redraw pulses, so a rung of `N`
redraws carries roughly **one pulse in `N`** of error. That is why the scatter tracked exposure
length, worst where exposures were shortest. Three consequences, and they are the whole of this
redesign:

- **Long exposures are the fix, so the panel is dimmed rather than brightened.** The level is now
  chosen to put `t_sat` near **22 s**, which puts the faintest rung near 300 redraws — 0.33%.
- **Gains whose faintest rung cannot reach 150 redraws at any level this panel has are not shot.**
- **The monitor bracket has to be faster than the wobble.** It was not: monitor factors stayed
  inside 1% while the rungs they corrected moved 2%.

### The gain set

**0, 50, 100, 200** — four, all of them gains where `g` is *measured* rather than interpolated
(session 02's law carries a 1.344% residual against its own 1% rule, so **no gain outside session
02's set may appear here at all**).

Four and not eight, because the rest cannot be shot honestly. At the level floor, the faintest
rung of this ladder measures:

| gain | 0 | 50 | 100 | 200 | 250 | 300 | 450 |
|---|---|---|---|---|---|---|---|
| redraws | 306 | 255 | 323 | 110 | 62 | 35 | 6 |
| quantisation | 0.33% | 0.39% | 0.31% | 0.9% | 1.6% | 2.9% | 17% |

**250, 300 and 450 are out of reach with this light source**, and that is published as a limitation
rather than filled with numbers nobody can defend. 200 is shot and carries its 0.9% as a stated
weakness — it is the only HCG point, and full well in electrons should step across that threshold
by the conversion-gain branch ratio if the bend belongs to the converter.

### The exposure ladder

Twenty rungs per gain, in two parts:

```
line   (4 rungs):           25  31  38  47                       (% of t_sat)
bend   (linear, 4% steps):  55 59 63 ... 111 115                 (% of t_sat)
```

**Nothing below 25% of `t_sat`.** The first run spent eight rungs between 3% and 39% and every one
of them was quantisation-limited; those frames are better spent near the bend. The cost is a short
lever arm — a factor of 1.9 instead of 13 — and the compensation is that the line is now fitted on
four quiet rungs instead of eight noisy ones.

The sixteen top rungs are linear because a 1% departure has to be *located*, and a geometric
ladder puts its resolution where nothing happens. The ladder runs past `t_sat` deliberately: the
rungs above 100% show the hard clip, the pinned-pixel plateaus (L12 predicts exactly 25%, then
75%) and the per-plane saturating exposures.

**Monitor frames, between every ladder frame.** One frame at a fixed **25% of `t_sat`** before
every ladder frame, and one after the last. Each ladder frame is divided by the mean of the two
monitors bracketing *it*, and the three corrected frames are averaged into the rung afterwards —
so the published `repeat_spread` is the spread of already-corrected frames and reads directly on
whether the correction worked.

| block | gains | frames |
|---|---|---|
| 0 — Gate 6 | 100 | ~5 min per arm, two arms |
| 1 — ladder | the four | 20 rungs × 3 |
| 2 — monitor | the four | 61, interleaved frame by frame |
| 3 — bias | the four | 10, adjacent to that gain's ladder |

≈ 524 frames, ≈ 1.1 GB, and about **1 h 45 min** of capture on the numbers the first run measured
— plus cool-down and the gates. Wall clock is `t_sat`-dominated: the notebook prints the estimate
from Gate 4 **before** capture starts, and a session that does not fit drops gain 50, which is the
one carrying least.

## Analysis rules, fixed before the data exists

Statistics on the CFA mosaic, split RGGB, never debayered. Values in ADC counts.

1. **Per plane, never on the frame mean.** L12 measured the frame-mean bend wrong by −11.5% at
   gain 200 and +18.7% at gain 100, in opposite directions.
2. **Pedestal** is this session's own block 3, at that gain, run through `stats.offset_state` and
   taken as the **near-state level** — not the raw block mean. Session 11 had to repair session 02
   for exactly this: a mixture of two offset states inside a bias block is a pedestal wrong by an
   occupancy-weighted fraction of a count. It is small against a 4000-count ladder, and it is free
   to do right the first time.
3. **Signal** = for each *frame*, (plane mean − pedestal) divided by the mean of the two monitors
   bracketing that frame, in units of the gain's monitor grand mean; the three corrected frames
   are then averaged into the rung. Frame by frame, not rung by rung — a correction slower than
   the wobble it corrects is decoration, which is what the first run proved.
4. **The reference line** is fitted through the four low rungs only, forced through the origin in
   exposure — a fitted intercept there quietly absorbs the pedestal error that rule 2 exists to
   remove — and never through any rung above 50% `t_sat`. A rung under Gate 5's measured flicker
   floor is dropped from the line *and* from the bend search; how many were dropped is published
   per gain, because a shorter lever arm is a weaker fit and the reader is owed that.
5. **`ceiling(gain)`** = the lowest level whose departure from that line reaches **1%**, per plane,
   interpolated between the two bracketing rungs, and **searched for only among the bend rungs**
   above 50% `t_sat`. A first-crossing search from the bottom of the ladder finds noise and calls
   it saturation. L28 predicts 3984 counts, 97.3% of the top code, measured twice to 0.05%; it is
   a prediction to reproduce or refute.
   **Two precision gates, and a ceiling failing either is published as not measured with the
   reason:** the line's worst rung must sit inside **0.5%** of it, and the crossing rung must be
   long enough that redraw quantisation is under **0.3%** — one pulse in 333.
6. **A rung with more than 1% of its pixels at 4095 cannot define the bend** and is recorded as
   clipped, not fitted. Not *any* pinned pixel: on a million-pixel ROI a handful of hot pixels pin
   long before the mean nears the top code, and at gain 0 that rule threw away the rung carrying
   the bend. A 1% clipped fraction biases the plane mean far under the 1% being measured, and
   biases it *down*, so the ceiling reads low rather than high. The pinned fraction is published
   per rung per plane, because its plateaus are L12's independent read on which plane saturates
   first.
   **A plane that never approaches its own saturation yields no ceiling and is published as
   null.** The ladder is scaled to the brightest plane's `t_sat`, so under a white-ish source the
   dimmer planes top out at a fraction of full scale — at gain 0 the first run's R plane reached
   4095 while B was still at 1638. The brightest plane is the one the star-colour constraint binds
   on, so the session's purpose survives; what is lost is the per-plane comparison, and the fix is
   a future ladder scaled to the *dimmest* plane.
7. **The ROI test.** Rules 3–5 re-run at 1024, 512 and the Gate 7 box, and the bend level from
   each is published. L09's rule is then checked on this session's own data instead of trusted.
8. **The converter-or-pixel test.** Bend levels compared across gains: constant in counts to
   within the per-plane spread means the ADC bends; proportional to `1/g` means the well fills.
   L12 found all four planes bending at one level to 1.6% and read it as the converter.

### What each outcome decides

| observation | consequence |
|---|---|
| bend at 3984 ± a few counts, flat across gains | the ADC is the limit at every usable gain; `ceiling` is one number, and full well in electrons is `ceiling × g(gain)`, falling with gain exactly as `g` does |
| bend level scales as `1/g` at low gain | the pixel well binds below some gain and the ADC above it; `ceiling(gain)` is genuinely gain-dependent, as MISSION already allows, and the crossover gain is the number to publish |
| bend levels differ **between planes** at one gain | the converter reading is refuted, the ceiling is per plane, and the star-colour constraint is written per plane |
| no bend before 4095 at any gain | full well never binds on this sensor in this domain; `ceiling` is the top code less a margin, and the model loses a term |
| the probed redraw rate exceeds the still one | the panel has adaptive refresh and was throttling a still page; the period used is the probed one, and any future bench session on this panel inherits the same correction |
| Gate 5 scatter near shot noise and flux flat across sub-redraw exposures | the short rungs are honest and the redraw worry is retired with a number rather than an assumption |
| Gate 5 fails | its measured floor becomes the cut applied to every rung, and any gain left with fewer than four line rungs yields no ceiling |
| the rungs still scatter by more than 1% about their own line | the ceiling is again not measurable, and the answer is not a third ladder on this panel: it is a source that does not redraw |
| Gate 6 flat from cold | `light-source.md` item 1 is **deleted**, on its own instruction, and L31 leaves the queue as an artefact of the retired setup |
| Gate 6 drifts, and the monitor correction moves the bend | the drift figure is published beside the ceiling, and every future session using second-long exposures at fixed light carries monitor rungs |
| Gate 6's arms disagree — steady in wall clock, unsteady in exposure length | it is not the panel; something exposure-length dependent is in the camera, and that outranks the ceiling as a finding |
| pinned fraction plateaus at 25%, then 75% | L12's channel ordering reproduces, and the ratio of saturating exposures is the per-plane sensitivity under this source |

## Record for the session

Everything `light-source.md` lists, plus Gate 3's two redraw periods and whether the page was
throttled, Gate 4's grey level and `t_sat` per gain, Gate 5's scatter ratio and flux spread,
Gate 6's two slopes and scatters, Gate 7's three peak-to-peak figures and the box chosen, the monitor rung level, ambient at
start and end, and the pinned fraction at the top rung of every gain.

## Where it lands

`notebooks/13_linearity.ipynb` measures and writes; `notebooks/14_linearity_read.ipynb` reads it
back and explains. Published files: `results/linearity_rungs.csv` (every rung — gain, plane, crop
size, level, exposure in redraws, pinned fraction, monitor factor), `results/light_stability.csv`
(Gate 6), and `results/linearity_constants.json` — `ceiling` and `ceiling_per_plane`, `full_well`,
the bend verdict, `not_measured` (every fit that yielded nothing, and why), the ROI test,
`panel_redraw_period`, `sub_redraw_flicker` and `flicker_floor` from Gates 3 and 5,
`grey_level_per_gain` from Gate 4, and Gate 6's two L31 numbers.

The session's own record — not published constants — is `data/session05/`: `gate4.csv`,
`gate5_flicker.csv`, `gate7.json`, `panel.json` and `cooldown.csv`.

**The session captures into an empty `data/session05/`, and the notebook refuses to start if
anything is in it.** Not just leftover frames — `fits.write` already refuses to overwrite those,
so a stale frame stops the run loudly. A stale *gate table* would not: the analysis reads
`gate4.csv` and `panel.json` back and pairs them with frames by name, so an abandoned attempt's
tables would be applied to the new pixels and mislabel every rung's exposure. A dead run is
restarted by deleting the directory (`CLAUDE.md`), and on a tight C: that is also how the disk is
given back.

## LEGACY entries consumed

L09 (Gate 7 and rule 7) · L12 (rules 1, 6, 8) · L28 (rule 5's prediction) ·
L31 (Gate 6, both arms, and `light-source.md` item 1's fate).

Each verified entry moves to its destination and leaves `LEGACY.md` when notebook 14 publishes.
With these four gone the queue holds only the PixInsight block and L32's sky rate.
