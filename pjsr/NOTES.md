# Driving PixInsight headless

What this folder assumes about PixInsight, and what has been checked rather than believed.

**Checked against:** core **1.9.2, build 1632**, instance slot 1, on this machine,
2026-09-19. Every number and every API fact below was produced by running `probe.js` and
`frame_stats.js` through `astropix.pixinsight.run`. **Re-run `probe.js` after any PixInsight
upgrade** — it measures nothing and takes forty seconds, and it is the only thing that tells you
whether a later failure is your script or the core.

The rules live in `astropix/pixinsight.py`, beside the code that obeys them. This file is the
PJSR side: what a script in this folder has to do, and why.

---

## 1. PixInsight has no console, and everything follows from that

It is a GUI-subsystem binary. `console.writeln()` goes nowhere the calling process can see,
`--help` launches the full GUI instead of printing, and `--enumerate` writes its report to a
*message box*.

So: **every script writes its result to a file, and writes it on the failure path too.** That is
what `report()` in `harness.jsh` is for, and `tests/test_pixinsight.py` asserts that every
`*.js` here goes through it. A script that throws without reporting exits silently, and the only
way to find where it died is to bisect it — which is how the retired project spent an afternoon
on a `DataType_ByteArray` error that could have arrived as one line of JSON.

`.jsh` headers are outside that rule and outside the glob. They are included, not run.

**But the console can be retrieved from inside the script, and it is.**
`console.endLog()` returns the log as a **string** in this build, so
`harness.jsh` wraps every run in `beginLog()`/`endLog()` and attaches the tail to
the result on both paths. That is not a refinement: a process can refuse to run
and return a bare `false`, writing its reason to the console and nowhere else —
`ImageIntegration` does exactly this — and without the log such a failure has no
diagnosis attached at all. Truncated to the last 8 kB, because a long
integration's log is tens of kilobytes of per-file chatter and only the tail says
what went wrong.

## 2. The command line

```
PixInsight.exe -n --automation-mode --run=<absolute path> --force-exit
```

Confirmed working. Each flag earns its place:

- **`-n` is not optional.** Without it PixInsight yields to an already running instance by
  default, and a harness run is silently handed to whatever GUI session is open.
- **Always the long `--run=`.** `-r` means `--run` to the OS launcher but `--runtime` to
  PixInsight's own internal `run` command — a different argument layer.
- **`--automation-mode`** suppresses informative and warning messages. It does **not** suppress a
  fatal argument-parse error: that happens before the automation machinery exists, and arrives as
  a modal dialog that waits forever for a click.
- **`--force-exit`** so a finished script does not leave the core resident holding the slot.

`-a=` and `-p=` belong to the internal layer only. On the OS command line they are what produces
the dialog that never gets clicked. **Never pass them.**

**A launch costs about 40 s** on this machine, almost all of it core startup. That is the floor
on any per-frame loop through PixInsight, and it is why a script that can do four planes in one
run should.

## 3. Never wait unbounded, and never read the exit code

`run()` takes a timeout and kills the **process tree** on expiry — `taskkill /T`, not a kill on
the handle we hold, because the launcher is not always the process that hangs, and a surviving
core holds the instance slot and breaks the *next* run instead.

**The absence of the result file is the failure signal.** The exit code is not evidence: a killed
process reports −1, and the modal-dialog case never exits at all. It is reported in the error
message as context and never tested.

`--terminate=<slot>` shuts down a wedged instance, but the invoking process may itself not exit,
so even that needs a timeout.

## 4. Parameters go in a JSON file, and numbers stay numbers

Since `-p=` is unavailable, the harness writes `job.json` into a **per-run working directory** and
launches with that directory as cwd. The script reads it by relative name through
`File.currentWorkingDirectory`, which is inherited from the launching process — confirmed by
`probe.js`, which reports the directory it woke up in and got ours back.

Per-run, not shared, so two concurrent runs cannot read each other's parameters.

This is better than `-p=` would have been in any case: PixInsight's own help says parameters
passed that way "are always String objects". Through JSON they are not — `probe.js` echoes each
value with its `typeof`, and `42`, `1.5` and `"42"` came back as `number`, `number`, `string`.

`File.readTextFile` works. **`DataType_ByteArray` is not defined in this build**, so the obvious
file-*writing* idiom throws; `harness.jsh` writes through a `File` object instead.

**PJSR is ECMAScript 5.** The ES6 string methods are not reliably present — `String.endsWith`
among them. Use `charAt`.

## 5. The unit boundary: 65535, never 4095

PixInsight normalises pixel data to [0, 1] by the **container maximum 65535**. Not by the sensor's
saturation level of 65520, and not by full scale.

Verified twice. L20's own case: PI reported `0.0229495689` for a frame whose stored median is
1504, and `1504/65535` is that number to ten digits. And here, on a session 06 light: PI reported
`0.02612344548662627` where our reader gives a stored median of `1712`, and `1712/65535` matches
to ten digits.

A PI value converts to this project's ADC counts as `v * 65535 / 16`, which is
`astropix.pixinsight.to_adc` and nothing else. **65535/16 is 4095.9375**, so multiplying by 4095
is wrong by 0.023% — small enough to look like rounding, which is what makes it worth a test
rather than a comment.

PixInsight opens a CFA frame as a **single-channel mono image and does not debayer on load**.
Confirmed: 3840×2160, 1 channel, 16 bits per sample. That is the same array we read, which is
what makes the whole comparison like-for-like rather than a comparison against interpolated
pixels.

## 6. SplitCFA returns R, G2, G1, B — and medians will not catch the error

`SplitCFA` enumerates the 2×2 tile in PixInsight's `(x, y)` order with `y` varying fastest, and
PI's first coordinate is the column. In numpy `(row, col)` terms:

| PI output | tile position (row, col) | plane |
|---|---|---|
| `CFA0` | (0, 0) | R |
| `CFA1` | (1, 0) | **G2** |
| `CFA2` | (0, 1) | **G1** |
| `CFA3` | (1, 1) | B |

**The two greens are transposed** against a naive reading of RGGB. R and B sit on the diagonal and
are unmoved. This is the ordinary `(x,y)` vs `(row,col)` transposition, and it should be expected
of any PI process that enumerates CFA positions by index.

Confirmed on a session 06 light, and so was the trap: under the naive order the two greens'
**minima** disagree (90 vs 92 ADC counts) while their **medians are identical to the digit** (109
both ways). **Do not compare medians.** The minimum is the cheapest statistic a single displaced
pixel can move, which is what makes it the one that catches this.

`outputViewId0..3` are **outputs, not inputs** — setting them before `executeOn()` has no effect.

## 7. Variance: PixInsight divides by n−1, numpy by n

`pcl::Variance` (`include/pcl/Math.h`) returns `(var - eps*eps/n)/(n - 1)` — the **sample**
variance. `ndarray.std()` is the **population** one. The ratio is `sqrt(n/(n-1))`: on a Bayer
sub-plane of a full frame that is 1 + 2.4e−7 and nothing would notice, but on the dozen-value
array a test uses it is 4.4%. So `pixinsight.matching_stats` carries `ddof=1` on our side of any
exact comparison, and the test that proves it runs at small n on purpose.

The `eps` term is compensated summation (*Numerical Recipes* 2nd ed., p. 613) — an accuracy
refinement, not a different estimator.

## 8. stderr is noise, not failure

PixInsight prints GLES errors to stderr on **every** headless launch:

```
ERROR:gpu_channel_manager.cc(959) Failed to create GLES3 context, fallback to GLES2.
ERROR:gpu_channel_manager.cc(970) ContextResult::kFatalFailure: Failed to create shared context
```

Harmless. `run()` captures stderr and returns it in the result; a harness that treated stderr as
failure would fail every run it ever made.

An open GUI instance can block automation mode. With `-n` that should not happen, and if it does
it shows up as a **timeout**, not an error — which is the other reason the timeout is not
optional.

## 9. Windows paths

PixInsight takes forward slashes on Windows, and a backslash inside a JSON string is an escape
character. `pixinsight.pi_path` does the conversion once, so no script has to get it right.

---

## 10. `for...in` over a process prototype takes the core down

Enumerating the properties of a process instance or its prototype with a
`for ( var k in P )` loop is an **access violation** in 1.9.2 — `C0000005`,
invalid memory read, with a fifty-frame backtrace through `mozjs-24.dll`. It is
not a thrown exception that a `try` can catch; it kills the process.

Probe by *name* instead: `("truncate" in P)`, or read `P[name]` inside a `try`
for a list of names you already have. That is what the API probe did in the end,
and it costs nothing.

This is also the best evidence so far that `report()` earns its place. The crash
arrived as `{"ok": false, "error": "Access violation…"}` in the result file, with
the PJSR line number of the offending loop — not as a process that vanished.

## 11. PixelMath's defaults are exactly the trap, and the pedestal is the fix

**A fresh `PixelMath` has `truncate = true` and `newImageSampleFormat =
SameAsTarget`.** So the obvious way to subtract two 16-bit frames — new instance,
`a - b`, execute — is the failing configuration, with nothing to warn you.

L23 said to subtract in 32-bit float with a `+0.5` pedestal, `rescale` and
`truncate` off. That was checked here the way the entry asked, by injecting a
known sigma into a synthetic pair rather than by inspecting a real bias, and it
**splits into two claims that are not equally load-bearing**.

At a realistic bias-pair spread — sigma 20 ADC counts per frame, so 28.3 counts
in the difference, which is 0.7% of PI's range:

| pedestal | format | truncate | sigma of the difference | |
|---|---|---|---|---|
| 0.5 | f32 | false | **exact** | the prescribed fix |
| 0.5 | f32 | true | **exact** | |
| 0.5 | i16 | false | **exact** | |
| 0.5 | i16 | true | **exact** | |
| 0.0 | f32 | false | **exact** | negatives survive in float |
| 0.0 | f32 | true | **−41.6%** | the trap |
| 0.0 | i16 | false | **+7063%** | unsigned wrap |
| 0.0 | i16 | true | **−41.6%** | the trap |

**The pedestal is doing all the work; the 32-bit float is doing none of it.** At
this spread every format and both truncation settings agree exactly once the
difference is moved off zero, and every failure is a difference that was left
centred on zero.

**−41.6% is the half-normal, and it is not "half".** Clipping a zero-centred
normal at zero leaves a distribution of standard deviation
`sqrt(1/2 − 1/(2π))` = **0.5838** of the original. L23 said "halves"; 0.584 is
what that turns out to mean, and the engine and numpy agree on it to two
decimals. The reason it cannot be caught downstream is that a read noise 42% low
looks like a better camera.

**The wrap is the failure mode L23 did not name, and it is the safe one.**
Storing a negative in an unsigned 16-bit container with truncation off gives a
sigma seventy times too large — unmistakable garbage. That makes
`truncate = false` safe in a second sense: where it fails, it fails loudly.
`truncate = true` is the dangerous setting precisely because it is the quiet one,
and it is the default.

**Where 32-bit float does earn its place is a wide difference.** At sigma 600
counts per frame — 846 in the difference, 21% of PI's range — 3 sigma exceeds the
0.5 pedestal and 0.8% of pixels go below zero anyway. Only `f32` with truncation
off stays exact there; `i16` costs 2.5% and truncation costs 1.4%. No bias pair
is ever that wide, so this is the belt rather than the braces — but it is why the
prescribed configuration is the one to use, rather than the pedestal alone.

**Rescale is off in every arm and is a separate hazard.** It maps the result's
own range onto [0, 1], which changes the standard deviation by a factor nobody
asked for and which depends on the data.

## 12. ImageIntegration: the cache is off, and the settings are read back

`useCache` defaults to **true**, and a ladder is exactly the shape a cache keyed
on inputs gets wrong: the same file paths, run after run, under different
settings. `integrate.js` sets it false.

Every setting in the result is read back **off the process instance after
execution**, never echoed from the job. What a process was asked to do and what
it did are the same thing right up until they are not, and `eta_comb`'s
provenance — which MISSION requires to record the stack size and the rejection
settings — cannot rest on the request.

Defaults worth knowing: `rejection = NoRejection` (0), `normalization =
AdditiveWithScaling` (3), `combination = Average` (0), `weightMode = 7`,
`sigmaLow = 4`, `sigmaHigh = 3`. The rejection enum has no `ESD` in this build.

**Three source images is a hard floor.** Fewer and `executeGlobal` refuses with
"This instance of ImageIntegration defines less than three source images",
whatever the rejection setting. So the **N=2 rung of a doubling ladder cannot be
measured through this engine at all** — which matters, because session 03's
`eta_comb` ladder on darks has one. A ladder through PixInsight starts at 3.

**A run that fails reports itself instead of throwing the batch away.** Each
entry in `runs` carries its own `ok`, and a caller wanting a clean ladder checks
every one. The three-image floor was found exactly this way, and losing eight
good rungs to it would have cost another launch to learn the same thing.

## 13. `weightMode` defaults to PSF Signal Weight, and that refuses a starless frame

This is the one that cost the most, and it arrives as a bare `false`.

`weightMode` defaults to **7, PSF Signal Weight**: each frame weighted by the
signal of the stars detected in it. On a star field that is the right
instrument. On anything **without** stars — a bias, a dark, a flat, or a
synthetic frame — there are no valid PSF samples, and `executeGlobal()` returns
`false` having logged:

```
** Warning: No valid PSF signal samples (channel 0).
*** Error: <file> (channel #0): Zero or insignificant PSF Signal Weight estimate.
```

Nothing reaches the caller but the `false`. It is what section 1's log capture
was added for, and it stayed undiagnosed across three launches without it.

**So `integrate.js` always states the weighting and never inherits it.**
`dont_care` weights every frame equally, which is what an efficiency measurement
wants regardless: `eta_comb` against the ideal `sqrt(N)` is *defined* on equally
weighted frames, and unequal weighting is one of the costs it exists to measure
rather than something it should have applied to itself. `evaluateSNR` is off for
the same reason — it runs even when nothing weights by it, and warns per file.

## 14. The engine itself is exact, and rejection is what `eta_comb` measures

Thirty-two synthetic frames, sigma 20 ADC counts injected, integrated in one
launch. The single frame measures 20.0042 counts, and `eta_comb` is the ideal
`sigma/sqrt(N)` over what the stack achieved:

| N | no rejection | Winsorized sigma clip (4.0 / 3.0) |
|---|---|---|
| 3 | 0.9995 | 0.9269 |
| 4 | 0.9999 | 0.9679 |
| 8 | 0.9983 | 0.9624 |
| 16 | 0.9994 | 0.9753 |
| 32 | 1.0003 | 0.9851 |

**Averaging loses nothing.** With rejection off, the engine hits `sqrt(N)` to
within 0.2% at every rung — noise on the estimate rather than a loss. Anything
below 1.0 in a real `eta_comb` is therefore the *combination*, never the
arithmetic.

**Rejection costs 1.5% to 7.3%, and the cost shrinks as the stack grows.**
Winsorized clipping at 4.0/3.0 discards real pixels, and at N=3 there are too few
left for the survivors to average well. That is the whole reason MISSION requires
`eta_comb`'s provenance to record the stack size and the rejection settings: the
number is a strong function of both, and quoting it without them says nothing.

These are synthetic frames with no structure, no registration and no outliers to
reject, so the rejection column is the *pure cost* of rejecting when there is
nothing to reject. On real frames it buys something back.

## 15. Registration: the split approach, and what StarAlignment will not do

Contract 3 registers each Bayer plane on its own: `SplitCFA`, then `StarAlignment` per plane
against the same plane of one shared reference. Nothing is debayered. Checked on session 06
lights on 2026-09-26: every plane solves, blue included - at gain 200 and 30 s the blue plane
still finds about 1 100 stars and matches over a thousand, with an RMS error of 0.2-0.6 plane
pixels. Four things were found on the way:

- **StarAlignment writes XISF whatever `outputExtension` says.** Asked for `.fits`, it wrote
  `_r.xisf`. `register.js` no longer asks. `astropix.fits.read_xisf` reads the result; it was
  checked against the XISF 1.0 specification and, pixel for pixel, against PixInsight's own FITS
  export of the same files.
- **`File.createDirectory` fails on a UNC path** - Win32 error 161, walking up to `//ds1513`.
  The caller creates the directories; the script only checks they exist.
- **The core's error text is in the system code page**, so a German Windows message puts a
  non-UTF-8 byte in `result.json`. `pixinsight.run` reads it with `errors="replace"`: one umlaut in
  the only diagnosis there is must not be what makes it unreadable.
- **`outputData` is a positional array.** Output path, mask path, match count, inliers,
  overlapping, regularity, quality, RMS error and its deviation, peak errors in x and y, then the
  3x3 homography row by row, then star coordinates. `register.js` names the first twenty and drops
  the rest, which would make a result file megabytes long.

StarAlignment also does not stop on a frame it cannot solve - it skips it and the batch still
returns - so success is read per frame, from whether its output file exists.

## The scripts

| script | what it does |
|---|---|
| `harness.jsh` | job in, result out, report on both paths. Included by every script. |
| `probe.js` | measures nothing. Core version, instance slot, working directory, job round-trip with types, and whether a real frame opens. Run it after every upgrade. |
| `frame_stats.js` | contract 1. Opens one CFA frame, splits it with `SplitCFA`, reports min/max/mean/median/std/MAD for the mosaic and each plane, plus both noise estimators. Compares nothing — the comparison is the notebook's, because a referee that knew the answer we wanted would not be one. |
| `pair_diff.js` | contract 2. `a - b + pedestal` through PixelMath, under settings the job states rather than the script chooses — which is what lets it demonstrate the unsafe ones. Reports the difference's statistics and a census of where its pixels sit relative to 0 and 1. Many arms per launch. |
| `integrate.js` | contract 2. Integrates a list of frames with `ImageIntegration` and reports the result, its noise, and every setting read back off the instance. Computes no efficiency: `eta_comb` is the notebook's arithmetic. Many runs per launch. Contract 3 added `output`, which saves the stack as 32-bit float FITS. |
| `register.js` | contract 3. Splits each CFA frame with `SplitCFA` and registers each plane against the same plane of one reference, with `StarAlignment`. Reports the match and the transform per frame and plane. The split planes are deleted; the registered ones are kept as 16-bit XISF. |

## Still unchecked

Nothing. L23 was the last inherited claim about this folder and section 11 is its
verdict.
