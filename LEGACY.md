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

### L31. The panel drifts while it warms, and nobody has watched it from cold
**Claim.** The retired project's version of this — gain 100 irreproducible at 1.79% while gain 200
managed 0.011% — **has been run and is not reproduced.** Session 05's arm 2 interleaved a short
and a long exposure at gain 100 throughout a block: repeat scatter **0.089% long, 0.299% short**,
six times better than L31 at the same gain, with a long/short flux ratio of 0.9886. Their confound
(exposure length and elapsed time varying together) is gone and nothing was hiding under it.

**What is left is one untested candidate: backlight thermal drift.** LED backlights dim as they
warm, a panel at 100% brightness reaches equilibrium over minutes, and session 05 measured a real
drift of **+0.314 ± 0.047 ADC counts/min** — small, seven sigma from zero, and upstream of the
sensor, because session 01's dark arm over the same timescale was −0.00133 ± 0.254 counts/min with
the light taken out. **But that arm was run with the panel already warm**, which is the one state
that cannot distinguish a panel still heating from a panel that has settled. So the mechanism is
consistent with the measurement and remains unproven by it.

**Consumed by.** `protocols/light-source.md` item 1, the ten-minute warm-up, which is currently a
precaution whose reason has been neither confirmed nor falsified.
**How to check.** One block, no ladder: wake the panel from genuinely cold, start capturing
immediately at a fixed gain and exposure, and run for twenty minutes with timestamps. If the trace
is flat from the first frame, **delete item 1** rather than keeping a ritual with no reason behind
it. If it decays to a floor, item 1 stays and its duration should be set from where the trace
flattens rather than from a round number.
**Lands in.** `protocols/light-source.md` — either item 1 deleted, or its ten minutes replaced by
a measured settling time. `results/` gains nothing either way: this is a property of the bench
light, not of the camera.

*(Session 05 resolved the repeatability half of this entry; see DECISIONS D79. The 5.5%
single-rung outlier the retired project saw did not recur either, and its most likely cause —
the screen briefly sleeping — is now caught during capture rather than after it, per D78.)*

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
