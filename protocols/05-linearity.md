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
| the per-plane sensitivity of this bench | Gate 4's converged patch colour — the panel codes that make the four planes collect equal flux |
| `S = F · t` | the linearity residual over the working range is the only direct test MISSION's signal term ever gets |
| **L31** — is a level at fixed light steady in wall clock and in exposure length | Gate 5, below. It is a prerequisite here, not a second purpose: an exposure ladder at fixed illumination is exactly the measurement L31 says may not be repeatable |

**What it is not for.** Gain, read noise, dark current, PRNU. `g(gain)` is an input. No pair
differencing happens here and no variance is published; the quantity is a *mean* level, and the
things that ruin a mean — drift, illumination structure, pedestal state, an unbalanced source —
are what this protocol spends its design on.

## The problem this design is built around

**One white-ish source does not fill four planes.** The panel's spectrum, the Bayer filters and the
sensor's QE compose into a different flux for each CFA plane, and nothing about the sensor makes
them equal. A ladder scaled to the brightest plane's saturation therefore runs the dimmer planes
over a fraction of their own range: they never approach their own ceiling, and the measurement
that defines this session cannot be made on them at all.

Stretching the ladder does not fix it. To take the dimmest plane to saturation, every exposure
scales by the flux ratio between brightest and dimmest — and that ratio is a property of the
bench, not a small number to absorb. The brightest plane spends the whole upper ladder pinned,
and the session length scales with a ratio nobody chose.

**So the light is balanced instead of the ladder being stretched.** The panel is an LCD: it has
red, green and blue subpixels, and driving them to three different codes changes the *colour* of
the light while leaving the backlight alone. Choose the triple that makes all four planes collect
the same counts per second, and one ladder takes every plane to its own saturation together —
same rungs, same length, same treatment, four independent measurements out of one session.

This is Gate 4, and it is the only structural difference between this protocol and an ordinary
linearity ladder.

## Pre-flight

All three items of `light-source.md`, and item 2's **True Tone off** is load-bearing here rather
than hygiene: this protocol chooses the panel's colour deliberately, and True Tone retunes the
white point from an ambient sensor that nothing in the data records.

Item 1's ten-minute warm-up **stands until Gate 5 has run**, and Gate 5 is what retires or
confirms it — a trace flat from cold deletes item 1 (its own instruction), a trace that is not
flat keeps it and finally gives it a number.

**Six gates**, in this order, because each needs the one above it. Gates 1 and 2 are
`02-ptc.md`'s, unchanged and not restated: white balance verified from pixels (the modal step of
16 on all four planes) and the cooler held at −10 °C in band for 30 s. The whole session runs in
one kernel.

| gate | settles |
|---|---|
| 1 | white balance, from the pixels |
| 2 | the cooler holds |
| 3 | the panel's redraw period |
| 4 | the patch colour per gain, then `t_sat` at it |
| 5 | L31 — the light is steady in wall clock and in exposure length |
| 6 | the illumination map, which chooses the analysis ROI |

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

### Gate 4 — the patch colour per gain, then `t_sat` at it

**Two knobs, not one.** The *ratios* between the three panel codes decide which plane is
brightest. Their *overall scale* decides how long a rung is. They are different questions and the
gate solves both, because they interact: the panel's colour shifts with its level. A backlight is
always on, so light leaks through nominally-closed subpixels, and the leak is not the same colour
as the panel driven hard. **The triple is therefore solved per gain, never once for the session**
— each gain runs at its own scale and so sees its own colour.

The gate is a measured iteration, not a model. At each gain:

1. Start from grey at the previous gain's scale; gain 0 starts at grey 128.
2. Capture one frame. Plane means above the fitted pedestal, divided by exposure — four fluxes.
3. **Ratios.** Move each panel code toward the value that equalises the four plane fluxes,
   damped, one step.
4. **Scale.** Multiply all three codes to move `t_sat = (4095 − pedestal) / flux` toward 22 s.
5. Repeat from 2 until both criteria hold, or eight iterations have run.

**It needs no model of the panel and that is the point.** The subpixel gamma, the Bayer crosstalk
that lets panel-blue reach the red plane, and the backlight leak are all inside the numbers step 2
reads back, so none of them has to be known, named or assumed. This is `light-source.md` item 3 —
measure the attenuation, never predict it — applied to three channels instead of one.

**Pass is two numbers.** The four plane fluxes within **5%** of each other, and the faintest rung
at or above **150 redraws**.

**Why 5%.** The ladder's top rung is 115% of `t_sat`, and the dimmest plane must still clear 100%
of its own. A 13% imbalance is where the top rung stops saturating the dimmest plane; 5% is that
bar with the margin a measurement is owed.

**Why 22 s.** Light arrives in redraw pulses, not continuously, so an exposure of `N` redraws
carries roughly **one pulse in `N`** of error. The faintest rung is 25% of `t_sat`, so 22 s puts
it near 320 redraws — 0.3%, against a bend defined as a 1% departure. Brighter is a shorter
session and dimmer is a quieter one; 22 s is where that trade sits, and 150 redraws (0.67%) is
where it stops being worth shooting at all.

**The brightness slider stays at 100% and is not an axis.** Subpixel codes block light; they do
not dim the backlight. So the colour can be chosen freely without touching the thing that might
flicker — the same argument that kept grey level cheap, now applied per channel.

**Three ways this gate can fail, each recorded rather than papered over:**

- **`t_sat` cannot be brought down to 22 s** because the panel is already flat out. Not a failure:
  take the `t_sat` the panel gives and accept a longer session. If the clock will not take it,
  **remove one diffuser sheet and re-run Gate 6** — sheets attenuate, so removing one buys light
  at the cost of uniformity, and uniformity is Gate 6's to judge, not this one's.
- **The balance cannot be reached** because a code would have to go below what the backlight leaks
  into that plane anyway. That gain is dropped, with its residual imbalance published.
- **The faintest rung stays under 150 redraws** at every triple that balances. That gain is
  dropped, with its redraw count published.

**The converged triple is a result, not just a setting.** It is the per-plane sensitivity of this
bench under this source, read directly — which is what L12 inferred indirectly from pinned-pixel
plateaus, and what this design measures on purpose instead.

### Gate 5 — the light is steady, in wall clock and in exposure length (L31)

Two arms, at one gain — **100**, L31's unstable one — on that gain's converged triple, before the
ladder:

1. **Drift.** One fixed exposure at the monitor frame's 25% of `t_sat`, repeated continuously for
   **5 minutes**, timestamped. Plane mean against wall clock. Session 01's dark arm already ran
   this with the light taken out and was flat to −0.00133 ± 0.254 counts/min, so anything here is
   upstream of the sensor.
2. **Exposure length against elapsed time.** Interleave a short (**10%** `t_sat`) and a long
   (**45%**) exposure, alternating, for **5 minutes**. Counts per second must match. This is the
   arm the retired project could not run: their two gains differed in exposure length *and* in
   elapsed time, so the confound was built in.

**Both arms sit at or below `LINE_MAX_PCT`, and that placement is the whole of their validity.**
Put the long arm near `t_sat` and its level lands where the response may already be bending — and
a long/short flux ratio can then no longer separate *the light short-changes long exposures* from
*the sensor is non-linear near full scale*. The second is the quantity this session publishes, so
an arm up there answers its own question with its own answer. 10% against 45% keeps a 4.5×
lever on exposure length, which is all the arm needs: a redraw-envelope error goes as one pulse
in `N`.

**Arm 2 is also the whole of the redraw worry, and there is deliberately no separate flicker
gate.** Light arriving in pulses only distorts a ladder if the pulse count is not proportional to
the shutter time, and over rungs of hundreds of redraws the only mechanism that does that is a
slow envelope on the backlight. Comparing counts per second at 10% and 90% of `t_sat` tests
exactly that, and interleaving them is what separates exposure length from elapsed time.

**There is no flicker floor anywhere in the analysis.** Gate 4 refuses to shoot a gain whose
faintest rung is under 150 redraws, so no rung in this session is ever near a single redraw. A
floor applied afterwards would be a cut with nothing left to cut, and a cut that fires anyway is a
cut that has gone wrong.

**Pass is a number, not a feeling:** the drift arm's fitted slope with its uncertainty, and arm
2's ratio of counts per second long to short. L31's contrast to beat is 1.79% at gain 100 against
0.011% at gain 200.

**A failing Gate 5 does not stop the session.** The ladder's monitor frames divide out drift on
any timescale longer than one frame pair. What Gate 5 decides is whether that correction is a
safety net or load-bearing — and that has to be known before the numbers are read, not after.

### Gate 6 — the illumination map (L09)

One well-exposed frame at ~50% `t_sat`, **on the balanced colour**. Measure peak-to-peak variation
of the plane means across the central **1024, 512 and 256** boxes. L09 predicts **3.8%, 1.25%,
0.53%**. A 3.8% spread saturates the bright corner ~4% of exposure before the dim one, which
smears a 1% bend over more range than the bend itself.

**On the balanced colour, and judged on the worst plane.** An LCD's subpixels do not share an
angular response, so a coloured patch can be less uniform across the field than grey, and
differently uniform per channel. The map has to be measured on the light that will actually be
used, and the box has to satisfy every plane rather than the average of them.

**This gate is a first look, not the decision.** One frame cannot separate illumination from shot
noise, and the noise per tile *grows* as the box shrinks — judge boxes on that number and the
flattest box reads as the worst. The analysis makes the real choice from the monitor stacks, with
the noise floor measured (odd frames against even) and subtracted, and takes the **largest** box
under 0.5%: among boxes flat enough to trust, the biggest has the quietest mean. Tiles are a fixed
32×32 mosaic pixels at every box. Capture stays at 1024 regardless.

## Capture

Offset **15**. Capture ROI **1024 × 1024 at (1408, 568)** — identical to session 02, so the two
sessions are row-for-row comparable, and even origin and extent or the Bayer phase shifts (L05).
Analysis crops to the Gate 6 box.

Discard the first 2 frames after every gain change and the first frame after every exposure
change, and do not write them. **After every patch colour change, wait for the page's handshake
and then discard 2 frames** — the handshake says the page painted, the discards cover the panel
settling behind it. Both are needed and neither substitutes for the other.

**A frame is written only if the panel was lit across it, and that is a retake condition beside
temperature.** The panel is an iPad and an iPad's screen sleeps; the Screen Wake Lock does not
exist over plain `http://` (`light-source.md` item 2), so **Auto-Lock set to Never is the only
thing holding the panel on** — and a slept screen is a *black panel*, which makes a flat frame a
dark frame wearing a flat's header, with nothing in the pixels to say so. The page reports its
frame rate every 2 s and stops when iOS stops servicing it, so that report is the liveness signal:
a frame across which it did not arrive is discarded and retaken on the same budget as a
temperature excursion. **Recency alone is not enough** — a page that slept through a 60 s exposure
and woke at the end reports a fresh timestamp — so for any frame longer than a few reporting
periods the timestamp must also have *moved*. The monitor bracket would expose a dark frame
eventually, in the analysis; that is a night too late, and a retake costs one frame.

Temperature discipline and the retake budget are session 02's: 10 retakes of one frame slot, or a
hold past 300 s, stops the session.

### The gain set

**0, 50, 100, 200.** All four are gains where `g` is *measured* rather than interpolated —
session 02's set is 0, 50, 100, 190, 200, 250, 300, 450, and its gain law carries a 1.344%
residual against its own 1% rule, so **no gain outside that set may appear here at all.**

Four and not eight because of the redraw arithmetic above: a fixed light makes a high gain's rungs
shorter in proportion to its amplification, and the panel can only be dimmed so far before the
backlight leak stops level being a control. **Which gains survive that is Gate 4's to decide, not
this table's** — a gain whose faintest rung cannot reach 150 redraws at any triple that balances
is dropped and published as out of reach, rather than filled with numbers nobody can defend.

200 is shot and is the only HCG point in the set. If the bend belongs to the converter, full well
in electrons should step across that threshold by the conversion-gain branch ratio.

### The exposure ladder

Twenty rungs per gain, in two parts:

```
line   (4 rungs):           25  31  38  47                       (% of t_sat)
bend   (linear, 4% steps):  55 59 63 ... 111 115                 (% of t_sat)
```

**Nothing below 25% of `t_sat`.** A rung's quantisation error goes as one pulse in `N` redraws,
so the bottom of a geometric ladder is where the noise is and the bend is not. Four quiet rungs
make a better line than eight noisy ones, and the cost — a lever arm of 1.9 instead of 13 — is
paid back by forcing the fit through the origin, which rule 4 does for an unrelated reason anyway.

The sixteen top rungs are linear because a 1% departure has to be *located*, and a geometric
ladder puts its resolution where nothing happens. The ladder runs past `t_sat` deliberately: the
rungs above 100% show the hard clip and the per-plane saturating exposures, and — because the
source is balanced — they are the direct check on Gate 4, since four balanced planes must pin
together.

**Monitor frames, between every ladder frame.** One frame at a fixed **25% of `t_sat`** before
every ladder frame, and one after the last, on the same triple. Each ladder frame is divided by
the mean of the two monitors bracketing *it*, and the three corrected frames are averaged into the
rung afterwards — so the published `repeat_spread` is the spread of already-corrected frames and
reads directly on whether the correction worked. **Frame by frame, not rung by rung:** a
correction slower than the drift it corrects is decoration.

| block | gains | frames |
|---|---|---|
| 0 — Gate 4 | the four | ≤8 iterations each, one written frame per iteration |
| 1 — Gate 5 | 100 | ~5 min per arm, two arms |
| 2 — ladder | the four | 20 rungs × 3 |
| 3 — monitor | the four | 61, interleaved frame by frame |
| 4 — bias | the four | 10, adjacent to that gain's ladder |

≈ 590 frames, ≈ 1.2 GB. **Wall clock is `t_sat`-dominated and Gate 4 is what sets it**, so the
notebook prints the estimate per gain **before** capture starts. Each gain costs about
`60 × t_sat` in exposure alone — 60 ladder frames averaging 75% of `t_sat`, plus 61 monitors at
25%. If every gain reaches the 22 s target that is about **1 h 40 min** plus readout, gates and
cool-down; every extra second of a gain's `t_sat` adds about a minute to the session. A session
that does not fit drops gain 50, which is the one carrying least.

## Analysis rules, fixed before the data exists

Statistics on the CFA mosaic, split RGGB, never debayered. Values in ADC counts.

1. **Per plane, never on the frame mean.** L12 measured the frame-mean bend wrong by −11.5% at
   gain 200 and +18.7% at gain 100, in opposite directions. Under a balanced source the frame mean
   is far less wrong than that — which makes it more tempting and no more correct.
2. **Pedestal** is this session's own block 4, at that gain, run through `stats.offset_state` and
   taken as the **near-state level** — not the raw block mean. Session 11 had to repair session 02
   for exactly this: a mixture of two offset states inside a bias block is a pedestal wrong by an
   occupancy-weighted fraction of a count. It is small against a 4000-count ladder, and it is free
   to do right the first time.
3. **Signal** = for each *frame*, (plane mean − pedestal) divided by the mean of the two monitors
   bracketing that frame, in units of the gain's monitor grand mean; the three corrected frames
   are then averaged into the rung.
4. **The reference line** is fitted through the four low rungs only, forced through the origin in
   exposure — a fitted intercept there quietly absorbs the pedestal error that rule 2 exists to
   remove — and never through any rung above 50% `t_sat`.
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
   long before the mean nears the top code, and that rule throws away the rung carrying the bend.
   A 1% clipped fraction biases the plane mean far under the 1% being measured, and biases it
   *down*, so the ceiling reads low rather than high.
   **The pinned fraction is published per rung per plane, and under a balanced source it is a
   check on Gate 4 rather than on the sensor.** L12's plateaus at 25% and then 75% of the mosaic
   are the signature of a *white-ish* source saturating one channel and then three. Balanced, all
   four planes pin together and the fraction steps once. A surviving plateau means the balance did
   not hold at the top of the ladder, and it says by how much.
7. **The ROI test.** Rules 3–5 re-run at 1024, 512 and the Gate 6 box, and the bend level from
   each is published. L09's rule is then checked on this session's own data instead of trusted.
8. **The converter-or-pixel test.** Bend levels compared across gains: constant in counts to
   within the per-plane spread means the ADC bends; proportional to `1/g` means the well fills.
   L12 found all four planes bending at one level to 1.6% and read it as the converter. **This
   session is the first that can put all four planes on that comparison at equal weight**, because
   all four reach their own saturation on the same ladder.

### What each outcome decides

| observation | consequence |
|---|---|
| bend at 3984 ± a few counts, flat across gains | the ADC is the limit at every usable gain; `ceiling` is one number, and full well in electrons is `ceiling × g(gain)`, falling with gain exactly as `g` does |
| bend level scales as `1/g` at low gain | the pixel well binds below some gain and the ADC above it; `ceiling(gain)` is genuinely gain-dependent, as MISSION already allows, and the crossover gain is the number to publish |
| bend levels differ **between planes** at one gain | the converter reading is refuted, the ceiling is per plane, and the star-colour constraint is written per plane |
| no bend before 4095 at any gain | full well never binds on this sensor in this domain; `ceiling` is the top code less a margin, and the model loses a term |
| Gate 4 converges at every gain inside 5% | the balanced-source design works, and every future bench session needing all four planes at once inherits it rather than re-deriving it |
| Gate 4 cannot balance a gain | that gain is published as out of reach with its residual, and the reason is a property of *this panel* — a source with independent channels would not have it |
| the pinned fraction still plateaus at 25% then 75% | Gate 4's balance did not survive to the top of the ladder; the ceiling on the late-pinning planes is suspect and the plateau ratio says by how much |
| the probed redraw rate exceeds the still one | the panel has adaptive refresh and was throttling a still page; the period used is the probed one, and any future bench session on this panel inherits the same correction |
| Gate 5 arm 2 flat | light arriving in redraw pulses does not distort a ladder of rungs this long, and the redraw worry is retired with a number rather than an assumption |
| Gate 5 arm 2 not flat | flux depends on how long the shutter was open, which is the one failure that masquerades as non-linearity; the ceiling is not measurable on this source and the answer is a source that does not redraw |
| Gate 5 flat from cold | `light-source.md` item 1 is **deleted**, on its own instruction, and L31 leaves the queue as an artefact of the retired setup |
| Gate 5 drifts, and the monitor correction moves the bend | the drift figure is published beside the ceiling, and every future session using second-long exposures at fixed light carries monitor rungs |
| Gate 5's arms disagree — steady in wall clock, unsteady in exposure length | it is not the panel; something exposure-length dependent is in the camera, and that outranks the ceiling as a finding |
| the rungs scatter by more than 1% about their own line | the ceiling is not measurable on this source, whatever the gates said; the answer is not another ladder on this panel |

## Record for the session

Everything `light-source.md` lists, plus True Tone confirmed off, Gate 3's two redraw periods and
whether the page was throttled, **Gate 4's converged patch colour, plane balance residual and
`t_sat` per gain, and any gain it dropped with the reason**, Gate 5's two slopes and scatters and
arm 2's ratio, Gate 6's three peak-to-peak figures per plane and the box chosen, the monitor rung
level, ambient at start and end, and the pinned fraction at the top rung of every gain.

## Where it lands

`notebooks/13_linearity.ipynb` measures and writes; `notebooks/14_linearity_read.ipynb` reads it
back and explains. Published files: `results/linearity_rungs.csv` (every rung — gain, plane, crop
size, level, exposure in redraws, pinned fraction, monitor factor), `results/light_stability.csv`
(Gate 5), and `results/linearity_constants.json` — `ceiling` and `ceiling_per_plane`, `full_well`,
the bend verdict, `not_measured` (every fit that yielded nothing, and why), the ROI test,
`panel_redraw_period` from Gate 3, and from Gate 4 `patch_colour_per_gain`, `plane_balance` and
`t_sat_per_gain`.

The session's own record — not published constants — is `data/session05/`: `gate4.csv` (one row
per balance iteration per gain), `gate6.json`, `panel.json` and `cooldown.csv`.

**The session captures into an empty `data/session05/`, and the notebook refuses to start if
anything is in it.** Not just leftover frames — `fits.write` already refuses to overwrite those,
so a stale frame stops the run loudly. A stale *gate table* would not: the analysis reads
`gate4.csv` and `panel.json` back and pairs them with frames by name, so an abandoned attempt's
tables would be applied to the new pixels and mislabel every rung's exposure *and its patch
colour*. A dead run is restarted by deleting the directory (`CLAUDE.md`), and on a tight C: that is
also how the disk is given back.

## What the panel has to provide

`grey-patch.html` and `patch-server.py` take a **triple**: `GET /set?rgb=170,221,255`, with the
`level=` form kept and meaning grey, so every session before this one still runs. The page renders
`rgb(r,g,b)` and reports the triple in its own record line. The manual controls stay grey-only —
solving for a colour needs measured flux, which the page does not have.

**And a handshake, because the gap between asking and showing is where a rung gets poisoned.** The
page polls every 300 ms and paints on its next redraw, so a capture fired straight after `/set`
can land on the *previous* colour with nothing in the frame to say so. The page therefore reports
what it painted — `GET /applied?rgb=..&seq=..` — on the frame after it painted it, and **the
notebook waits for `applied.seq` to reach the `seq` its `/set` returned before it discards or
captures anything.** That says the page painted, not that the backlight settled; the two discards
after a colour change are what cover the rest.

Nothing there is physics — it moves three integers from the notebook to the panel, and what flux
they produce is measured by the camera in Gate 4.

## LEGACY entries consumed

L09 (Gate 6 and rule 7) · L12 (rules 1, 6, 8, and Gate 4 measuring directly what L12 inferred) ·
L28 (rule 5's prediction) · L31 (Gate 5, both arms, and `light-source.md` item 1's fate).

Each verified entry moves to its destination and leaves `LEGACY.md` when notebook 14 publishes.
With these four gone the queue holds only the PixInsight block and L32's sky rate.
