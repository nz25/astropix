# Legacy

Claims inherited from the two retired attempts at this project, `astro/` and `learn_astro/`.

**This file is a queue, not a library. It exists to be emptied.** Nothing here is knowledge this
project holds; it is knowledge someone else's project claimed, kept because rediscovering it
would cost bench nights. Each entry is verified when the build step that needs it arrives, then
**moved to its destination and deleted from here**. When the file is empty it is deleted, and
this repo is back to four Markdown files (D13).

Entries are cited by number from wherever they land — `DECISIONS`, `FINDINGS`, `CLAUDE.md`,
`protocols/`, `pjsr/` — so the trail survives after this file is gone.

**Schema.** No entry is admitted without all five fields. `Consumed by` and `Lands in` are what
make the queue drain; an entry without them is a note, not a work item.

| field | meaning |
|---|---|
| **Claim** | what the retired project believed |
| **Source** | which repo and file, so it can be re-read |
| **Consumed by** | the build step that needs it |
| **How to check** | the specific test, not "verify this" |
| **Lands in** | where it goes when confirmed |

**What was deliberately excluded:** anything MISSION scopes out (auto-STF and stretching);
anything already independently confirmed here (the 12-bit shift, MAD on quantised data); and
method aphorisms, which are writing advice rather than hypotheses.

**Nothing here has been verified by this project.** The retired numbers came from a different
codebase without this project's provenance discipline, and `learn_astro/kb/measurements.md`
retracts at least one of its own published fits. Treat every number as a prediction to falsify.

---

## Before any bench frame is captured — build step 6 (`asi.py`)

### L01. ZWO applies white balance to RAW16 data
**Claim.** The camera ships `WB_R = 55`, `WB_B = 75`. These are ratios against 50, so red is
multiplied by 1.10 and blue by 1.50 **before the data reaches us, in RAW16 mode**. "Raw" is not
raw. Two consequences: red and blue gains come out scaled, so one sensor looks like it has
three; and the multiply is integer arithmetic, so output lands on a stretched lattice and the
rounding perturbs the very noise statistics being measured. Read noise came out ~17% high at
every gain until it was neutralised.
**Source.** `learn_astro/kb/gotchas.md`, confirmed 2026-08-25.
**Consumed by.** Build step 6, before the first bench frame — this invalidates everything
captured before it is fixed.
**How to check.** Read `WB_R`/`WB_B` from the SDK on open. Independently, the fingerprint on a
dark is the modal step between adjacent distinct values *per CFA channel*: greens 16, red 17/18
alternating, blue 24. Greens are untouched because WB is defined relative to green, which is
what makes the pattern readable at all.
**Lands in.** `CLAUDE.md` as a non-negotiable rule, plus a `neutralise_white_balance()` call in
`asi.py` that runs unconditionally on open.

### L02. The ASI SDK is not the ASI driver, and the ASIAIR takes the camera
**Claim.** ZWO ship two separate things: the **Camera Driver** (Windows USB driver) and the
**ASI Camera SDK** (`ASICamera2.dll`, no `.inf`). `zwoasi` needs the SDK, but the SDK needs the
driver underneath. Installing only the SDK gives the confusing state where `zwoasi.init()`
succeeds and `get_num_cameras()` returns 0. Separately: **the ASIAIR claims the camera
exclusively over USB** — powered on with the camera attached, the PC will not see it regardless
of drivers.
**Source.** `learn_astro/kb/gotchas.md`, hit 2026-08-25.
**Consumed by.** Build step 6, first attempt to open the camera.
**How to check.** `Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_03C3' }`
— ZWO's vendor ID; the ASI585MC Pro is `PID_585F`. A healthy camera shows `Status: OK` with a
real device class. Code 28 means the driver is missing and says so unambiguously.
**Lands in.** `protocols/bench-setup.md` as the first pre-flight item.

### L03. The cooler lies in three different ways
**Claim.** Three separate traps, which together made a working cooler look dead and a genuine
fault look like a bug. (a) The control is called **`CoolPowerPerc`**, not `CoolerPowerPerc`; a
lookup on the wrong name returned a hard 0 forever. (b) **`ASI_TEMPERATURE` reads a flat 0 until
the cooler is switched on** — it is not a live thermometer on an idle camera, and an exposure
does not wake it. (c) **A hard-killed process leaves the TEC latched off** until 12 V is
physically unplugged and replugged.
**Source.** `learn_astro/kb/gotchas.md`, 2026-08-25.
**Consumed by.** Build step 6, the cooling routine.
**How to check.** Enumerate the controls and read the names back. Then diagnose cooling **by the
temperature trend, not the duty cycle**: command the cooler on, watch the sensor temperature for
60 s. Falling means it works. That test needs no control the camera might not implement. Return
−1 for "not reported" rather than 0, since 0 is a legitimate reading for an idle TEC.
**Lands in.** `asi.py`, plus `protocols/bench-setup.md` for the power-cycle rule.

### L04. Cooling takes minutes, and must be allowed to settle
**Claim.** About 3 °C/min at the start from ~17 °C ambient, accelerating as power ramps. Budget
several minutes to reach −10 °C. A TEC **overshoots and rings**, so sampling at first touch of
the setpoint starts a sweep on a drifting temperature; require the temperature to stay in band
for a continuous settle period before returning.
**Source.** `learn_astro/kb/gotchas.md`, measured 2026-08-25.
**Consumed by.** Build step 6, and every bench protocol.
**How to check.** Log temperature every second from cooler-on to settled; the curve is the
answer. Our own archive already shows the failure mode this guards against — 2,132 frames more
than 1 °C off setpoint (`FINDINGS`, 2026-08-27).
**Lands in.** `asi.py` (`cool_to` with a settle window) and `protocols/bench-setup.md`.

### L05. The gain range is 0–600, and the ROI must be even
**Claim.** Gain runs **0–600**, not 0–400 as assumed — 61 points at step 10, not 41. Separately,
any ROI must have **even x and y origin and even width and height**, or the Bayer phase shifts
and "the red pixels" are no longer where the header says. The retired PTC used 1024×1024 at
origin (1408, 568), both even.
**Source.** `learn_astro/kb/measurements.md` and `gotchas.md`, read from the SDK 2026-08-25.
**Consumed by.** Build step 6, sweep planning.
**How to check.** Read the gain control's range from the SDK. For the ROI, assert evenness in
code — it is a one-line guard, and `spatial.split` already assumes RGGB phase.
**Lands in.** `asi.py` as a validated parameter, and a note in `protocols/`.

---

## The light source — build step 6

### L06. The light source is an iPad LCD, and three iOS settings will ruin a run
**Claim.** Camera stands face-down on 2–3 sheets of paper on the screen; contact with an
extended emitter is the most uniform geometry available. **iPad 7th generation (2019)**, 10.2″
LCD, 60 Hz, no True Tone. Three settings change the light mid-run with nothing in the data to
show it: **Auto-Brightness** (re-levels from the ambient sensor), **Auto-Lock** (must be Never; a
sleeping screen dims on the way down), **Night Shift** (warms colour balance on a schedule,
hitting each Bayer channel differently). LCD is the favourable case — backlight and attenuation
are separate layers, unlike OLED. **Run at 100% brightness and attenuate with paper and grey
level**: LED backlights are PWM-dimmed at reduced brightness and closer to constant-current at
full, so maximum brightness is the *least*-flickering setting.
**Source.** `learn_astro/kb/gotchas.md`; `lessons/0001-sensor-three-numbers/grey-patch.html`
holds the patch page and requests a Screen Wake Lock.
**Consumed by.** Build step 6, first bench session.
**How to check.** Capture an exposure ladder and fit `variance = signal/g + R²`; a flickering
point sits *above* the line. The retired run found no measurable flicker from 1 ms to 200 ms,
r² = 0.999971.
**Lands in.** `protocols/bench-setup.md`.

### L07. Grey level is exhausted below ~25% of full scale
**Claim.** An LCD does not go black — the liquid crystal attenuates the backlight but never
blocks it. Fitting `L = leak + k·value^2.2` gave a backlight leakage of 6218 ADU/s against 3359
from grey 48 and 731 from grey 24. Predicted flux at grey 1 is 6219 ADU/s, i.e. **1.12× less
than grey 24, and that is the entire remaining range**. Below ~25%, attenuate optically instead.
**Source.** `learn_astro/kb/gotchas.md`, confirmed by a failed prediction 2026-08-25.
**Consumed by.** Build step 6, when setting flux for a sweep.
**How to check.** Two grey levels and a flux measurement each; the tell is the implied exponent.
Fitting `L = k·value^g` to two points gave g = 0.46, and an exponent below 1 is not a display
gamma at all — that mismatch is the signature of an additive floor.
**Lands in.** `protocols/bench-setup.md`.

### L08. Stacked diffusers give diminishing returns
**Claim.** Sheets of 80 gsm printer paper attenuate by 1.68× each at 3–4 sheets, 1.47× at 5,
1.29× at 6, 1.24× at 7. **A stack of diffusers is not a stack of independent filters** — each
sheet scatters light forward as well as backward, so part of what sheet *n* rejects is passed on
by sheet *n+1*. Any per-sheet figure is valid only at the depth it was measured; extrapolating
1.5× per sheet came up 1.1× short and needed a seventh sheet.
**Source.** `learn_astro/kb/gotchas.md`, confirmed by a failed prediction 2026-08-25.
**Consumed by.** Build step 6, sweep pre-flight.
**How to check.** Do not predict — measure the flux directly in the pre-flight, which takes under
a minute, and solve for the saturating exposure at every gain from the measured value.
**Lands in.** `protocols/bench-setup.md`, as "measure, never extrapolate".

### L09. Illumination is uneven enough to smear a linearity bend
**Claim.** The light source varies **3.8% peak-to-peak across 1024×1024**, so the bright corner
saturates ~4% of exposure before the dim one. For a measurement defined as a 1% departure from a
straight line, that smears the bend over more range than the effect. Central 512 gives 1.25%;
central **256 gives 0.53%**. Use a small ROI for linearity — and note this does *not* affect the
PTC, which differences frame pairs and is blind to fixed pattern.
**Source.** `learn_astro/kb/measurements.md`, linearity run 2026-08-26.
**Consumed by.** The linearity measurement, whenever scheduled.
**How to check.** Measure peak-to-peak variation across a real flat at each candidate ROI size.
**Lands in.** `protocols/` for the linearity session.

---

## Estimator and PTC method — build steps 2 and 3

### L10. Measure read noise from a bias pair, not from the PTC intercept
**Claim.** In principle one PTC gives both numbers. In practice the intercept is close to
worthless if the illumination levels are all bright: with read noise of 1.2 ADU the intercept is
1.44 ADU², extrapolated back from variances in the thousands, and ordinary scatter in the bright
points swamps it. A linearly-spaced sweep from 500 to 35 000 e⁻ returned **7.1 e⁻ for a true
3.0 e⁻** while the gain from the same fit was accurate to 3%. Two fixes: measure read noise
directly from a bias pair and pass it in; and **log-space the exposure ladder** so several points
sit near zero signal where the intercept is actually constrained.
**Source.** `learn_astro/kb/gotchas.md`, confirmed in simulation 2026-08-25.
**Consumed by.** Build step 3, PTC design — this determines the ladder before any frame is shot.
**How to check.** Fit a synthetic PTC with a known intercept, linear vs log spacing, and compare
the recovered read noise. A test, not a bench night.
**Lands in.** `DECISIONS`, as the reason the ladder is geometric; and the fitted intercept
retained as a cross-check rather than as the answer.

### L11. Two-point photon transfer works on ordinary imaging frames
**Claim.** `g = signal / (var_flat − var_bias)` in real ADU, from one flat level and one bias
level, recovered the bench constants from Denis's own ASIAIR archive: read noise within **0.62%**
and system gain within **1.23%** of a full 61-point bench sweep. Per-channel gains agreed to
0.6% across channels carrying half the signal of one another.
**Source.** `learn_astro/kb/measurements.md`, Lesson 00, 2026-08-26.
**Consumed by.** Build step 3 — a cross-check on the bench PTC that costs no bench time, since
the archive already holds the frames.
**How to check.** Run it on our own indexed archive at gain 50 and 252 and compare against
whatever the bench PTC returns. Two datasets with nothing in common agreeing is far stronger
evidence than either alone.
**Lands in.** `FINDINGS` as a cross-validation, and a notebook cell.

### L12. Saturation and linearity must be measured per CFA channel
**Claim.** The four channels have different sensitivities, so under a white-ish source they
saturate at **exposures differing by 1.34×**. The pinned-pixel fraction plateaus at exactly 25%,
then 75% — one channel topping out, then three. Reading the bend off the frame mean gets it
wrong by −11.5% at gain 200 and +18.7% at gain 100, in opposite directions. Measured per channel,
all four bend at the same *level* to within 1.6%, which is what shows **the converter bends, not
the pixel**.
**Source.** `learn_astro/kb/measurements.md`, linearity run 2026-08-26.
**Consumed by.** The linearity measurement.
**How to check.** Per-channel bend levels; if they agree while the saturating exposures differ,
the ADC is the limit.
**Lands in.** `FINDINGS`, and `DECISIONS` if it changes how full well is defined.

### L13. Clipping is a fraction, not a minimum — and cold pixels are not clipping
**Claim.** An offset check flagged "the offset is too low and data is being clipped" because the
darkest pixel in a gain-600 bias read 0. It was **58 pixels of 1 048 576** — 0.0055% — while the
bulk of the distribution sat 11.3 read noises clear of zero. Those are defective cold pixels,
identifiable as 23σ outliers at gain 300 where nothing else is near the floor. Measure the
**fraction** of clipped pixels, threshold 0.1%; genuine clipping eats the noise distribution and
shows up in percent, a defect count shows up in parts per hundred thousand.
**Source.** `learn_astro/kb/gotchas.md`, 2026-08-25.
**Consumed by.** Build step 3, and any offset choice.
**How to check.** Compare the clipped *fraction* against the distribution's distance from zero in
read noises, at several gains.
**Lands in.** `stats.py` as the saturation/clipping test, with the threshold recorded.

### L14. Dark current here may be below the detection floor, and must be reported as such
**Claim.** At −10.5 °C over 120 s the mean dark signal came out at **−0.23 e⁻** — negative,
because the master dark sat one reported ADU below the master bias, which is pedestal drift
between sessions four hours apart. Quote it as **"below the detection floor, < 0.01 e⁻/s"**,
never as a signed value. The 12-bit quantisation makes it worse: the *median* dark and *median*
bias land on the same code and the difference reads as a clean zero; only the mean over millions
of pixels reveals the sub-code offset. **Do not fit a temperature-scaling model on it** — with no
measurable signal at either end there is nothing to fit a doubling temperature to.
**Source.** `learn_astro/kb/gotchas.md`.
**Consumed by.** The `D(T)` measurement, which MISSION lists as a model constant.
**How to check.** Take darks at the extremes of the achievable temperature range and see whether
the difference exceeds its own uncertainty before attempting a fit.
**Lands in.** `FINDINGS`, and `MISSION`'s constants table if `D(T)` turns out to be
unmeasurable rather than merely small.

### L15. Per-pixel statistics across a stack of lights are meaningless before registration
**Claim.** Measuring σ in a star-free patch as more frames were averaged tracked √N to N ≈ 8 then
stalled hard — 3.5× at N = 50 against an ideal of 7.1×. The cause was **not** fixed-pattern
noise: the mount drifts and dithers, so the patch looks at different sky in every frame, stars
wander in, and sigma-clipping hides them from the statistic but not from the mean. Use frames
where pointing does not exist — bias, darks and flats are perfectly registered by construction.
**Source.** `learn_astro/kb/gotchas.md`.
**Consumed by.** The stacking-efficiency constant `η`, which MISSION requires be measured rather
than assumed √N.
**How to check.** The tell: the stalled curve did not move when flat-field correction was
applied. Had PRNU been the floor, flat-fielding would have lowered it.
**Lands in.** `DECISIONS`, as a constraint on how `η` may be measured.

---

## PixInsight — build step 5

### L16. The CLI invocation, and the flag that hangs a headless run forever
**Claim.** Use `PixInsight.exe -n --automation-mode --run=<absolute-path> --force-exit`. Each
flag earns its place: **`-n` is not optional** — without it PixInsight *yields to an already
running instance by default*, so a harness run is silently handed to an open GUI session.
**Always the long `--run=`**: `-r` means `--run` at the OS level but `--runtime` in PixInsight's
own internal `run` command, which is a different argument layer. `-a=` and `-p=` belong to that
internal layer only; passing them on the OS command line produces a **modal GUI "Fatal Error"
dialog even under `--automation-mode`**, and the process then waits forever for a click.
`--automation-mode` suppresses informative and warning messages, not fatal argument-parse errors,
which happen before the automation machinery is up.
**Source.** `astro/docs/pixinsight-notes/cli.md`, verified twice. Note `learn_astro` records the
short `-r=` form with comma-separated arguments; where they conflict, `astro` explains the
mechanism and should be preferred.
**Consumed by.** Build step 5, the first line of the harness.
**How to check.** `astro/scripts/pjsr/cli_probe.js` reports core version, instance slot, working
directory and whether a real frame opens. Run it after any PixInsight upgrade.
**Lands in.** `pjsr/NOTES.md` and `pixinsight.py`.

### L17. Never wait on PixInsight unbounded, and never trust its exit code
**Claim.** Launch with a timeout and kill on expiry, or one typo in a flag hangs the suite
indefinitely with no diagnostic. **Absence of the expected output file is the reliable failure
signal**; the exit code is not — a killed process reports −1 and the modal-dialog case never
exits at all. `--terminate=<slot>` shuts down a wedged instance but the invoking process itself
may not exit, so give even that a timeout.
**Source.** `astro/docs/pixinsight-notes/cli.md`.
**Consumed by.** Build step 5.
**How to check.** Deliberately pass a bad flag and confirm the harness fails in bounded time.
**Lands in.** `pixinsight.py`, as the process-launch contract.

### L18. A PJSR script must report by writing a file
**Claim.** `PixInsight.exe` is a **GUI-subsystem binary** with no console: `--help` launches the
full GUI instead of printing, `console.writeln()` is invisible to the calling shell, and
`--enumerate` writes its report to a *message box* on Windows. Therefore every PJSR script must
write its results to a file. **And it must write that file even when it fails** — the retired
project's `DataType_ByteArray` error arrived as `{"ok":false,...}` in a file instead of as a
silent process that had to be debugged by bisection.
**Source.** `astro/docs/pixinsight-notes/cli.md`; `learn_astro/kb/gotchas.md` for the
write-on-failure defence.
**Consumed by.** Build step 5, every script in `pjsr/`.
**How to check.** Structural — assert every `pjsr/*.js` writes a result file on both paths.
**Lands in.** `pjsr/NOTES.md`, and plausibly a test.

### L19. Parameters go in a JSON file, and numeric types survive
**Claim.** Since `-p=` is unavailable, pass a JSON file: `JSON.parse(File.readTextFile(path))`.
This is better than `-p=` would have been in any case — the help states parameters passed that
way "are always String objects", whereas JSON preserves numbers. `File.readTextFile` works;
`DataType_ByteArray` is **not defined** in this PJSR build, so the obvious file-reading idiom
throws. The working directory is inherited from the launching process, so scripts can resolve
paths relative to the repo.
**Source.** `astro/docs/pixinsight-notes/cli.md`; `learn_astro/kb/gotchas.md`.
**Consumed by.** Build step 5.
**How to check.** Round-trip a float and an integer through the job file and assert types.
**Lands in.** `pjsr/NOTES.md` and the harness in `pixinsight.py`.

### L20. Scale by 65535, not by 65520
**Claim.** PixInsight normalises pixel data to [0,1] and the divisor is the **container maximum
65535**, not the sensor's saturation level of 65520. Verified exactly: PI reported a median of
`0.0229495689` and `1504 / 65535 = 0.0229495689`. The two are different questions — 65520 is
what the sensor can produce, 65535 is what PI divides by. PixInsight also opens a CFA frame as a
**single-channel mono image** and does **not** debayer on load, which matches our raw array and
makes the comparison like-for-like (D4).
**Source.** `astro/docs/pixinsight-notes/cli.md`; independently in `learn_astro/kb/gotchas.md`.
**Consumed by.** Build step 5, PixInsight contract 1.
**How to check.** One frame, one median, both tools.
**Lands in.** `pixinsight.py` as the unit conversion, with the check as a test.

### L21. SplitCFA returns R, G2, G1, B — and medians will not catch the error
**Claim.** `SplitCFA` enumerates the 2×2 tile in PixInsight's `(x, y)` order with `y` varying
fastest, and PI's first coordinate is the column. In numpy `(row, col)` terms: `CFA0`→(0,0) R,
`CFA1`→(1,0) G2, `CFA2`→(0,1) G1, `CFA3`→(1,1) B. **The two greens are transposed** relative to
a naive mapping; R and B are unaffected because transposing the diagonal leaves them put. This is
the ordinary `(x,y)` vs `(row,col)` transposition and should be expected of any PI process that
enumerates CFA positions by index. Also: `outputViewId0..3` are **outputs, not inputs** — setting
them before `executeOn()` has no effect.
**Source.** `astro/docs/pixinsight-notes/splitcfa-ordering.md`.
**Consumed by.** Build step 5, comparing `spatial.split` against PI.
**How to check.** **Do not compare medians.** Under the wrong mapping exactly 2 of 24 numbers
disagreed, and the medians matched anyway because both greens share a median on a real frame. Use
a statistic sensitive to individual pixels — **the minimum is the cheapest** — alongside the mean
and standard deviation.
**Lands in.** `pjsr/NOTES.md`, and the contract-1 test.

### L22. PixInsight's variance divides by n−1; numpy's divides by n
**Claim.** `pcl::Variance` (in `include/pcl/Math.h`, ~line 2784) returns
`(var - eps*eps/n)/(n - 1)` — the **sample** variance. `ndarray.std()` is the **population**
variance. The two differ by exactly `sqrt(n/(n-1))`: negligible on a Bayer sub-plane
(1 + 2.4e−7) but not on the hand-checkable dozen-value array a test would use. The `eps` term is
compensated summation (*Numerical Recipes* 2nd ed., p. 613), an accuracy refinement that does not
change which estimator it is.
**Source.** `astro/docs/pcl-notes/variance-denominator.md`.
**Consumed by.** Build step 5, contract 1.
**How to check.** A dozen known values through both.
**Lands in.** `pixinsight.py`, as `ddof=1` on our side of any exact comparison.

### L23. Subtracting two 16-bit unsigned images clips every negative difference
**Claim.** For a bias pair this **halves the apparent read noise**, and it fails quietly — the
number is plausible, just wrong. Do the subtraction in **32-bit float with a +0.5 pedestal**
(`A - B + 0.5`, `rescale = false`, `truncate = false`): the pedestal moves the mean without
touching the standard deviation and keeps the distribution inside [0,1].
**Source.** `learn_astro/kb/gotchas.md`, confirmed 2026-08-25.
**Consumed by.** Build step 5, any pair-difference done inside PixInsight.
**How to check.** Inject a known sigma into a synthetic pair and assert recovery.
**Lands in.** `pjsr/NOTES.md`, with the test alongside.

### L24. PixInsight's own noise estimators, and how it chooses between them
**Claim.** `image.noiseMRS(n)` and `image.noiseKSigma()` both return `[sigma, count]`.
`NoiseEvaluation.js` calls MRS with decreasing layer counts and falls back to k-sigma only if the
noisy-pixel set stays below 1% of the frame; on the retired project's frames MRS converged at 4
layers and the fallback was never taken. Measured on one bias frame: PI MRS **13.909 ADU**, pair
difference 14.234, clipped std 14.349, MAD **23.722**. Also worth knowing: PixInsight prints
harmless GLES errors to stderr on every headless launch, and an open GUI instance can block
automation mode — which shows up as a timeout rather than an error.
**Source.** `astro/docs/pixinsight-notes/lesson01-stf-and-noise.md` and `dataset-quantization.md`
— **both carry retirement banners**: the frames are gone and the values cannot be reproduced. The
API facts stand; the numbers are predictions.
**Consumed by.** Build step 5, PixInsight contract 1 (D6).
**How to check.** Run both estimators against `stats.sigma` and a pair difference on the same
bias frame. Expect an *ordering* rather than equality: PI's multiresolution rejects harder than
our clip, PI's plain σ rejects nothing, and ours should sit between them with the spread widening
as gain amplifies the outlier tail.
**Lands in.** `FINDINGS` as contract 1's result, and `pixinsight.py`.

---

## Numbers to reproduce — build step 3

### L25. The headline sensor constants
**Claim.** From a 61-gain PTC sweep, per **real** (12-bit) ADU:

| gain | e⁻/ADU | read noise (e⁻) | full well (e⁻) | DR (stops) |
|---:|---:|---:|---:|---:|
| 0 | 9.382 | 6.18 | 36 057 | 12.51 |
| 50 | 5.425 | 4.95 | 20 837 | 12.04 |
| 100 | 2.994 | 4.22 | 11 492 | 11.41 |
| 190 | 1.051 | 3.39 | 4 017 | 10.21 |
| **200** | **0.927** | **1.13** | **3 558** | **11.62** |
| 250 | 0.513 | 1.03 | 1 964 | 10.89 |
| 300 | 0.284 | 0.97 | 1 083 | 10.12 |
| 600 | 0.009 | 0.85 | 26 | 4.92 |

These are already in this project's unit — **e⁻ per ADC count** (`CLAUDE.md`, D41) — so the table
is directly comparable to our own PTC with no conversion. "Full well" is the **ADC-limited** well,
not the physical one.
**Source.** `learn_astro/kb/measurements.md`, 2026-08-25.
**Consumed by.** Build step 3 — as the prediction our own PTC either reproduces or refutes.
**How to check.** Our own sweep, measured independently, compared afterwards. Not used as input.
**Lands in.** `results/constants_ptc.json` if reproduced; `FINDINGS` either way, since a
disagreement is as informative as a match.

### L26. The HCG threshold is gain 200, not 252
**Claim.** Read noise falls **3.39 → 1.13 e⁻** between gain 190 and 200 — a 67% drop in one step
of 10, about 49× the typical step-to-step change, with nothing comparable near 252. ZWO revised
their own published figure from 252 to 200 in late 2025. Dynamic range peaks *within* the HCG
branch at exactly gain 200 and falls monotonically above it, so **everything above gain 200 is a
bad trade**: read noise only creeps from 1.13 to 0.83 e⁻ by gain 530 while full well collapses
from 3 558 e⁻ to under 100.
**Source.** `learn_astro/kb/measurements.md`; MISSION already lists this as needing a dedicated
fine gain sweep.
**Consumed by.** Build step 3, and directly the gain recommendation.
**How to check.** Fine steps either side of 200. Three independent fingerprints are claimed:
the read-noise cliff, the same cliff in ADU (ruling out a scaling artefact), and a
**discontinuity in the pedestal** at the same gain — 1360→1104 at offset 15, 2288→2064 at
offset 30.
**Lands in.** `results/constants_ptc.json` and `FINDINGS`.

### L27. The pedestal has two branches, and the offset is purely digital
**Claim.** Pedestal fits `A + B × amplification` **per conversion-gain branch**, not across the
transition: a single smooth fit lands between the branches and mispredicts both by 8–17%, while
per-branch it is 0.8–1.4%. The digital constant `A` scales with the offset setting (ratio 2.007
for offsets 15→30, i.e. **≈4.0 real ADU per offset unit**) while `B` is untouched by it — so the
offset is applied after everything else and is a constant, not a distortion. `B` falls 43.5 →
15.3 across the transition, consistent with a change ahead of the amplifier. **This claim
supersedes an earlier one in the same file** (`pedestal = 1984 + 15.66 × amplification` "to
within 0.2%") which is explicitly retracted as least-squares dominated by high-gain points.
**Source.** `learn_astro/kb/measurements.md`, offset sweep 2026-08-26.
**Consumed by.** Build step 3, the offset choice; `pedestal` is a MISSION constant.
**How to check.** Our own bias frames already show the pedestal is *exactly* constant per gain
(1040.0 at gain 50, 1232.0 at gain 252, std 0.0 — `FINDINGS` 2026-08-27), which is a start.
Also claimed: read noise must **not** depend on offset — worst disagreement 0.38% across 61
gains — which is a prediction that could have failed.
**Lands in.** `results/` as the pedestal constant, and `FINDINGS`.

### L28. The linear limit is 63 744 reported ADU, below the hard clip
**Claim.** The response departs 1% from a straight line at **63 744 reported = 3 984 real ADU =
97.3% of the top code**, measured twice with 0.05% agreement. The hard clip is 65 520 / 4 095;
the two are 2.9% apart, or 0.041 stops. Adopting the measured limit raised full well by 0.47%.
**Source.** `learn_astro/kb/measurements.md`, linearity runs 2026-08-26.
**Consumed by.** The linearity measurement; MISSION lists "ADC ceiling / full well" as a
constant.
**How to check.** A 20-rung ladder from 50% to 115% of the saturating exposure, per CFA channel,
on a small ROI (see L09 and L12).
**Lands in.** `results/`, as the clip level every other analysis rejects against.

### L29. The gain law is 0.1 dB per unit, and unity gain lands at ~194
**Claim.** Fitting log₁₀(system gain) against gain setting over gains 0–150 gives a slope of
**−0.00502 per unit** against the −0.00500 the 0.1 dB law predicts — agreement 1.005 over 16
points with 1.0% scatter. System gain crosses **1.000 e⁻ per real ADU at gain 194**, and ZWO
annotate `GAIN=195` on their own published panel. Unity gain is a landmark, not a target.
**Source.** `learn_astro/kb/measurements.md`.
**Consumed by.** Build step 3 — it makes `g(gain)` interpolable between measured steps, which the
archive needs since it uses gain 252 and a sweep would step by 10.
**How to check.** Our own sweep, fitted in log space.
**Lands in.** `results/constants_ptc.json`, as the interpolation rule.

### L30. ZWO's four published panels are two measurements and two derived quantities
**Claim.** Their e⁻/ADU and read-noise panels are measured; **"FW" is `4095 × e⁻/ADU`** — the ADC
ceiling, not the physical well — and DR is FW ÷ read noise. The evidence is the HCG
discontinuity: it appears in the read-noise and DR panels and **not** in the FW or e⁻/ADU panels,
which is only possible if FW is arithmetic on a smooth input. The size confirms it: published DR
moves 10.00 → 11.85 stops, and `log2(3.95/1.10) = 1.844`. A "full well" curve that *falls* with
gain is nonsense read literally — a bucket does not shrink because you amplified its readout.
**Source.** `astro/docs/sensor-notes/asi585mc-gain-curves.md`.
**Consumed by.** Build step 3, when comparing our measurement against the vendor's.
**How to check.** Arithmetic on their published table; no data needed.
**Lands in.** `FINDINGS`, as the basis for any vendor comparison — and it settles what "full
well" means in that comparison.

---

## Open questions inherited

### L31. Gain 100 was not repeatable and gain 200 was, and nobody knows why
**Claim.** In two linearity runs, frame pairs at each rung should have differed only by noise.
At gain 200 the repeat-to-repeat spread was **0.011%**; at gain 100 it was **1.79%**, with one
rung 5.5% off on its own. Ruled out: source settling (a second run minutes later with a
demonstrably steady source failed identically), display-refresh beating (gain 100 integrates over
*more* refresh cycles, which should average better), and dark current (orders of magnitude too
small at −10 °C over 2 s). What is left is something varying on a timescale of tens of seconds —
gain 200's whole ladder was ~11 s of exposure inside one quiet stretch, gain 100's spanned ~70 s.
**Marked UNRESOLVED, and worth resolving before any measurement relies on second-long exposures
at a fixed light level.** It does not affect a PTC, which plots variance against measured signal
and never against exposure time.
**Source.** `learn_astro/kb/measurements.md`, 2026-08-26.
**Consumed by.** Any bench measurement using exposures of order seconds.
**How to check.** Their comparison could not settle it: gain 100 and gain 200 differ in
*exposure length* (1.08–2.48 s vs 0.33–0.77 s) **and** in *elapsed time* (~70 s vs ~11 s), so the
confound was built in. A clean version, ~15 minutes at one gain and no ladder: fix everything,
capture continuously for five minutes with timestamps, and plot mean level against wall-clock
time; then repeat interleaving a short and a long exposure throughout. The first separates drift
from noise, the second separates elapsed time from exposure duration.

**One candidate they did not test: backlight thermal drift.** LED backlights dim as they warm, a
panel at 100% brightness reaches equilibrium over minutes, and that fits the leftover timescale.
It also survives their settling check — re-running minutes later does not help if the panel is
still heating rather than having settled once. `protocols/bench-setup.md` item 0 carries a
ten-minute warm-up as a precaution against this; **if the trace is flat from cold, delete that
item** rather than keeping a ritual whose reason has been falsified.

The separate 5.5% single-rung outlier looks like a different mechanism — an occasional bad frame
rather than drift. A notification, or the Screen Wake Lock briefly lapsing.
**Lands in.** `FINDINGS` if reproduced, or deleted from here if it turns out to be an artefact of
their setup.

### L32. Sky rate and PRNU, to be re-derived from our own frames
**Claim.** Sky **1.594 e⁻/px/s** green (R 1.500, B 0.910) at f/4.8, 2.27″/px, unfiltered, near
zenith, suburban Bortle 5–6 — implying ≈19.1 mag/arcsec². And **PRNU of 0.61%** over a crop
(1.00% over the full channel), measured as the fixed pattern that stops a stack of flats
following √N. The sky figure is explicitly "a rate for that night, at that altitude" and fell
about 5% across a two-hour session as the target rose.
**Source.** `learn_astro/kb/measurements.md`, Lesson 00, from Denis's own IC 5070 frames.
**Consumed by.** MISSION lists `F_sky` as extracted per frame from the lights themselves, so this
is a sanity check rather than a constant.
**How to check.** Extract sky per frame from our indexed archive and compare. The NGC 7000 set
gives eight nights at two gains to do it across.
**Lands in.** `FINDINGS`, as the working suburban figure with its variability stated.
