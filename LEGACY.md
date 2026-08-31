# Legacy

Claims inherited from the two retired attempts at this project, both now deleted.

**This file is a queue, not a library. It exists to be emptied.** Nothing here is knowledge this
project holds; it is knowledge someone else's project claimed, kept because rediscovering it
would cost bench nights. Each entry is verified when the build step that needs it arrives, then
**moved to its destination and deleted from here**. When the file is empty it is deleted, and
this repo is back to four Markdown files.

Entries are cited by number from wherever they land — `results/`, `CLAUDE.md`, `DECISIONS`,
`protocols/`, `pjsr/` — so the trail survives after this file is gone. A measured number lands in
`results/` with its provenance, never in prose alone.

**Schema.** No entry is admitted without all four fields. `Consumed by` and `Lands in` are what
make the queue drain; an entry without them is a note, not a work item.

| field | meaning |
|---|---|
| **Claim** | what the retired project believed |
| **Consumed by** | the build step that needs it |
| **How to check** | the specific test, not "verify this" |
| **Lands in** | where it goes when confirmed |

**What was deliberately excluded:** anything MISSION scopes out (auto-STF and stretching);
anything already independently confirmed here (the 12-bit shift, MAD on quantised data); and
method aphorisms, which are writing advice rather than hypotheses.

**Nothing here has been verified by this project, and there is nothing left to check it
against.** The retired trees are gone; these entries are all that remains of them, so no claim
can be re-read at its origin. The numbers came from a codebase without this project's
provenance discipline, and that codebase retracted at least one of its own published fits.
Treat every number as a prediction to falsify — there is no longer anywhere to appeal.

---

## Linearity, full well and `ceiling(gain)` — the linearity session

### L09. Illumination is uneven enough to smear a linearity bend
**Claim.** The light source varies **3.8% peak-to-peak across 1024×1024**, so the bright corner
saturates ~4% of exposure before the dim one. For a measurement defined as a 1% departure from a
straight line, that smears the bend over more range than the effect. Central 512 gives 1.25%;
central **256 gives 0.53%**. Use a small ROI for linearity — and note this does *not* affect the
PTC, which differences frame pairs and is blind to fixed pattern.
**Consumed by.** The linearity measurement, whenever scheduled.
**How to check.** Measure peak-to-peak variation across a real flat at each candidate ROI size.
**Lands in.** `protocols/` for the linearity session.

### L12. Saturation and linearity must be measured per CFA channel
**Claim.** The four channels have different sensitivities, so under a white-ish source they
saturate at **exposures differing by 1.34×**. The pinned-pixel fraction plateaus at exactly 25%,
then 75% — one channel topping out, then three. Reading the bend off the frame mean gets it
wrong by −11.5% at gain 200 and +18.7% at gain 100, in opposite directions. Measured per channel,
all four bend at the same *level* to within 1.6%, which is what shows **the converter bends, not
the pixel**.
**Consumed by.** The linearity measurement.
**How to check.** Per-channel bend levels; if they agree while the saturating exposures differ,
the ADC is the limit.
**Lands in.** `results/` as per-channel bend levels, and `DECISIONS` if it changes how full
well is defined.

### L28. The linear limit is 63 744 reported ADU, below the hard clip
**Claim.** The response departs 1% from a straight line at **63 744 reported = 3 984 real ADU =
97.3% of the top code**, measured twice with 0.05% agreement. The hard clip is 65 520 / 4 095;
the two are 2.9% apart, or 0.041 stops. Adopting the measured limit raised full well by 0.47%.
**Consumed by.** The linearity measurement; MISSION lists `ceiling(gain)` / full well as a
constant, gain-dependent and at or below 4 095.
**How to check.** A 20-rung ladder from 50% to 115% of the saturating exposure, per CFA channel,
on a small ROI (see L09 and L12).
**Lands in.** `results/`, as the clip level every other analysis rejects against.

---

## Dark current — `protocols/03-dark-bound.md`, written and unrun

### L14. Dark current here may be below the detection floor, and must be reported as such
**Claim.** At −10.5 °C over 120 s the mean dark signal came out at **−0.23 e⁻** — negative,
because the master dark sat one reported ADU below the master bias, which is pedestal drift
between sessions four hours apart. Quote it as **"below the detection floor, < 0.01 e⁻/s"**,
never as a signed value. The 12-bit quantisation makes it worse: the *median* dark and *median*
bias land on the same code and the difference reads as a clean zero; only the mean over millions
of pixels reveals the sub-code offset. **Do not fit a temperature-scaling model on it** — with no
measurable signal at either end there is nothing to fit a doubling temperature to.
**Consumed by.** The `D(T)` measurement, which MISSION lists as a model constant.
**How to check.** Take darks at the extremes of the achievable temperature range and see whether
the difference exceeds its own uncertainty before attempting a fit.
**Lands in.** `results/` as `D(T)` with its detection floor — an upper bound is a result and
is recorded as one — and `MISSION`'s constants table if `D(T)` turns out to be unmeasurable
rather than merely small.

---

## Stacking — how `η_comb` may be measured

### L15. Per-pixel statistics across a stack of lights are meaningless before registration
**Claim.** Measuring σ in a star-free patch as more frames were averaged tracked √N to N ≈ 8 then
stalled hard — 3.5× at N = 50 against an ideal of 7.1×. The cause was **not** fixed-pattern
noise: the mount drifts and dithers, so the patch looks at different sky in every frame, stars
wander in, and sigma-clipping hides them from the statistic but not from the mean. Use frames
where pointing does not exist — bias, darks and flats are perfectly registered by construction.
**Consumed by.** The combination-efficiency constant `η_comb`, which MISSION requires be measured
rather than assumed √N.
**How to check.** The tell: the stalled curve did not move when flat-field correction was
applied. Had PRNU been the floor, flat-fielding would have lowered it.
**Lands in.** `DECISIONS`, as a constraint on how `η_comb` may be measured.

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
which happen before the automation machinery is up. A short `-r=` form with comma-separated
arguments was also recorded; where the two conflict, prefer the mechanism above.
**Consumed by.** Build step 5, the first line of the harness.
**How to check.** A probe script reporting core version, instance slot, working
directory and whether a real frame opens — the first thing to write in `pjsr/`, and to
re-run after any PixInsight upgrade.
**Lands in.** `pjsr/NOTES.md` and `pixinsight.py`.

### L17. Never wait on PixInsight unbounded, and never trust its exit code
**Claim.** Launch with a timeout and kill on expiry, or one typo in a flag hangs the suite
indefinitely with no diagnostic. **Absence of the expected output file is the reliable failure
signal**; the exit code is not — a killed process reports −1 and the modal-dialog case never
exits at all. `--terminate=<slot>` shuts down a wedged instance but the invoking process itself
may not exit, so give even that a timeout.
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
**Consumed by.** Build step 5, contract 1.
**How to check.** A dozen known values through both.
**Lands in.** `pixinsight.py`, as `ddof=1` on our side of any exact comparison.

### L23. Subtracting two 16-bit unsigned images clips every negative difference
**Claim.** For a bias pair this **halves the apparent read noise**, and it fails quietly — the
number is plausible, just wrong. Do the subtraction in **32-bit float with a +0.5 pedestal**
(`A - B + 0.5`, `rescale = false`, `truncate = false`): the pedestal moves the mean without
touching the standard deviation and keeps the distribution inside [0,1].
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
automation mode — which shows up as a timeout rather than an error. **These numbers cannot be reproduced — the
frames behind them are gone. The API facts stand; the numbers are predictions.**
**Consumed by.** Build step 5, PixInsight contract 1 (D6).
**How to check.** Run both estimators against `stats.sigma` and a pair difference on the same
bias frame. Expect an *ordering* rather than equality: PI's multiresolution rejects harder than
our clip, PI's plain σ rejects nothing, and ours should sit between them with the spread widening
as gain amplifies the outlier tail.
**Lands in.** `results/` as contract 1's measured ordering, and `pixinsight.py`.

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
still heating rather than having settled once. `protocols/light-source.md` item 1 carries a
ten-minute warm-up as a precaution against this; **if the trace is flat from cold, delete that
item** rather than keeping a ritual whose reason has been falsified.

**The dark arm has run, and it was flat.** Session 01's drift block — 450 bias frames at gain 100
over 15 minutes at −10 °C, `results/pedestal_drift.csv` — is the first half of that clean test
with the light source taken out of it: **−0.00133 ± 0.254 ADC counts/min**, a slope two orders of
magnitude inside its own uncertainty. So nothing in the *camera* drifts on this timescale, and
whatever is left is upstream of the sensor. That is the arm this project could run without the
light source; arms 1 and 2 still need it, and `light-source.md` item 1 stands until they do.

The separate 5.5% single-rung outlier looks like a different mechanism — an occasional bad frame
rather than drift. A notification, or the Screen Wake Lock briefly lapsing.
**Lands in.** `results/` as a repeatability figure if reproduced, or deleted from here if it
turns out to be an artefact of their setup.

### L32. The suburban sky rate, to be re-derived from our own frames
**Claim.** Sky **1.594 e⁻/px/s** green (R 1.500, B 0.910) at f/4.8, 2.27″/px, unfiltered, near
zenith, suburban Bortle 5–6 — implying ≈19.1 mag/arcsec². The figure is explicitly "a rate for
that night, at that altitude" and fell about 5% across a two-hour session as the target rose.
**Consumed by.** MISSION lists `F_sky` as extracted per frame from the lights themselves, so this
is a sanity check rather than a constant.
**How to check.** Extract sky per frame from our indexed archive and compare. The NGC 7000 set
gives eight nights at two gains to do it across.
**Lands in.** `results/` as the working suburban sky rate, with its variability stated.

**Its PRNU half left in D54**, measured at 1.02% and published as `prnu`. The sky rate is what
is left.
