# Findings

What we have learned about *this* rig and *this* data. Prose for humans; each entry cites the
`results/` file that proves it. An entry with no citation is an observation awaiting measurement,
and says so.

---

## 2026-08-27 — Archive survey (observations, not yet measurements)

These came from reading headers during the founding session. None is a measurement yet; each is
a fact about the data holdings or a hypothesis to test.

**The NGC7000 ladder is a well-designed experiment that was never analysed.** 1701 frames over
four nights, six sub-exposure lengths, each totalling exactly 9600 s, fully interleaved across
nights. It contains the answer to the sub-exposure question for gain 252 under those skies. It
is the primary validation dataset (D7).

**The cooler did not reach its setpoint in August 2026.** Bias frames carry `SET-TEMP = -20` with
`CCD-TEMP = -10.5`. The 2025 ladder frames, by contrast, requested -10 and held -10.0. This is
why the setpoint is now fixed at -10 C (D10), and it is why the sweep driver must record achieved
temperature, not requested (D12).

**The dark library is not organised the way its folders imply.** Frames are foldered by exposure
but mixed by gain and temperature inside. Two likely gaps for the ladder: 15 s darks appear to be
gain 50 only, and 240 s darks appear to be gain 50 at -20 C. To be settled by the header index
(D15) before any re-shoot is scheduled.

**The archive holds far more than the ladder.** ~10,500 lights across 18 targets and six exposure
lengths, plus 520 bias, 2180 dark, 1860 flat. Sessions before ~2025-09 used gain 252; later ones
gain 50 — so gain is confounded with epoch and target throughout, which is precisely why the gain
grid must be shot fresh (D11).

**Frame type labels are not reliable.** Denis recalls capturing some flats and darks under a Light
subframe type, so `IMAGETYP` cannot be trusted for classification and neither can the folder a
frame sits in. How widespread this is, is unknown — the index will quantify it by classifying from
pixel statistics and flagging every disagreement (D18). That disagreement list is also the seed of
the archive cleanup (D20).

**Suspected unit trap, highest priority to settle.** Headers report `EGAIN = 5.286 e-/ADU` at gain
50, but the ASI585's ADC is 12-bit and ASIAIR stores 16-bit files bit-shifted by 16x. The gain in
the units of the numbers actually stored is therefore expected near 0.33 e-/ADU. The harvested PTC
sweep settles this, and nothing downstream is trustworthy until it does. **This is step 3 of the
build order and it gates everything.**

---

## 2026-08-27 — The archive index: 15,102 frames measured

First pass of `results/frame_index.csv` (snapshot `2026-08-27T13:24:22`, 106.8 min, ~0.42 s
per frame over SMB). Every frame classified from its own pixels, not its label or its folder.
15,090 readable, 12 not. Companion files: `results/archive_census.csv`,
`results/ladder_census.csv`, `results/unreadable_frames.csv`. Notebook: `notebooks/01`.

### The 12-bit ADC is confirmed, on every frame in the archive

`mult16_frac = 1.000000` for all 15,090 readable frames — minimum, mean and maximum. Every
stored value is an exact multiple of 16, and the largest value anywhere is 65520 = 4095 x 16.
The bit-shift is no longer a hypothesis. **One count in a file is 1/16 of one ADC count**, and
the fifteen values between are unreachable. Header `EGAIN` is in 12-bit ADU; using it against
file values inflates electron counts 16x. This is the unit trap of build step 3, now settled
in evidence if not yet in the constant.

### Read noise is below the quantiser almost everywhere — MAD cannot see it

The consequence nobody was looking for. MAD is a median of absolute deviations, so on a grid of
step 16 it can only return multiples of 1.4826 x 16 = 23.7216. Across the archive:

| frames | at exactly sigma = 23.7216 |
|---|---|
| bias + dark, gain 50 | **85.8%** of 1,807 |
| bias + dark, gain 252 | **91.4%** of 1,374 |
| lights, gain 50 | 14.2% of 7,845 (median sigma 47.4) |
| lights, gain 252 | 0.0% of 1,160 (median sigma 269.8) |

So it is not a low-gain problem, as first thought: **nine tenths of every calibration frame in
the archive, at both gains, reads out at exactly one ADC step.** That number is a property of
the quantiser. Simulation puts MAD's error at -100% at 0.25 steps (it returns zero), +48% at
1 step, -26% at 2 steps, settling inside 5% only above ~8 steps; standard deviation is nearly
immune (+4.0% at 1 step, +1.0% at 2). Hence D24: the estimator is sigma-clipped std, and the
`sigma` column of the index is a classification feature, **not** a noise measurement.

Lights escape because sky shot noise dithers the quantiser for free — which is itself the reason
the PTC works at all, and a warning that bias-frame read noise is the hardest number here.

### The pedestal is fixed, and it moves with gain

Bias level is *identical* across every frame at a gain: 1040.0 ADU at gain 50 (320 frames),
1232.0 at gain 252 (200 frames). Not a median of a spread — the same number every time. In
12-bit units that is 65 and 77.

### Frame labels: 684 disagreements, and the folders are right

Of 15,090 frames, **684 declare `IMAGETYP = Light` and measure as dark** — 200 sitting in
`dark/`, 484 in `light/`. Nothing declares dark-as-light. The disagreement is entirely
one-directional, which is the signature of a capture-time subframe-type left on "Light", not of
random mislabelling. **Every other label agrees** — all 520 bias, 1,977 dark, 1,852 flat.
This is the D20 cleanup work-list, in `results/archive_census.csv` (`n_mislabelled`).

Worth recording honestly: a first version of the classifier reported another 1,052
disagreements. Those were **the classifier being wrong, not the labels** — bright twilight
lights at long exposure passing a level-only flat cut (see D27). The labels were right and the
measurement was wrong, which is exactly the failure mode that a one-directional error pattern
should make you suspect.

### Dawn is real: clipped frames end sessions

Denis's hypothesis, tested rather than assumed. 538 clipped frames (`sat_frac >= 0.5`) across
20 observing nights, ordered by `DATE-OBS` with the night boundary at local noon:

- **20 of 20 sessions have clipping reaching the final frame.**
- **18 of 20 are an unbroken run to the end** — clipping starts and never stops.
- Last frame timestamps run 02:47-07:49 UTC, tracking the season, as dawn does at 49.5 N.

The two ragged cases (`NGC7000|2025-08-08`, `NGC7000_tests|2025-08-19`) still end clipped but
have gaps, consistent with broken cloud during twilight. No session clips in the middle and
recovers. Morning twilight, not light leaks.

### D7 is wrong about the primary validation dataset — in an interesting way

`NGC7000_tests` holds 1,701 frames, all measuring as light. But it is **not** a six-rung ladder
at gain 252 totalling 9600 s per rung, captured 2025-08-17 to 20 and interleaved across four
nights. It is a **2 x 6 grid**:

| gain | rungs | frames per rung | total per rung | observing nights |
|---|---|---|---|---|
| 50 | 15/30/60/120/240/480 s | 448/224/112/56/28/14 | **6720 s** | 2025-08-19, **2025-09-18** |
| 252 | 15/30/60/120/240/480 s | 416/208/104/52/26/13 | **6240 s** | 2025-08-17, 2025-08-18 |

Equal-integration holds *exactly* within each gain — 448x15 = 224x30 = ... = 6720 s — so the
sub-exposure experiment is sound, and it exists **twice**, at two gains. That is more than D7
promised.

**But gain is perfectly confounded with night.** The two gains share no observing night, and the
fourth night is a month later than D7 states. Sky brightness, moon and transparency all differ
between the gain-50 and gain-252 halves, so a cross-gain comparison drawn from this dataset
would be measuring the weather. Within a gain, the rungs *are* interleaved across that gain's
two nights, which is what the design needed.

This vindicates D11: the gain axis must be shot fresh, interleaved. It also upgrades the ladder
from one validation dataset to two independent ones.

56 ladder frames are clipped (3.3%), concentrated at 15 s where the rung runs latest into dawn.

### Sky flux is already extractable, and it cross-checks the gain ratio

Median frame level against exposure, from `results/ladder_census.csv`, minus the measured
pedestal, gives a sky rate that is **linear in exposure** to within a few percent:

| gain | from the 15 s rung | from the 480 s rung |
|---|---|---|
| 252 | (2052-1232)/15 = 54.7 ADU/s | (27696-1232)/480 = 55.1 ADU/s |
| 50 | (1112-1040)/15 = 4.8 ADU/s | (3698-1040)/480 = 5.54 ADU/s |

The ratio between gains, 55.1/5.54 = 9.95, sits within 3% of the ratio of header `EGAIN` values
(5.286/0.5166 = 10.23) — two independent routes to the same number, one from sky photons and
one from the vendor. The sky term of the model has a measurement path, and the gain ratio has a
first sanity check.

**A number that matters for the sub-exposure question, visible already:** at gain 252, a 480 s
sub sits at 27,696 ADU of *sky alone* — 42% of full scale before any object light. Read noise
stopped mattering long before that.

### 12 zero-byte frames

All 12 unreadable files are **exactly 0 bytes**, and every one is the last or near-last frame of
its capture run by sequence number: `dark/002` 0098-0100, `flat/20260320` 0059-0060,
`flat/20260813` 0055-0060, `light/M 106` 0096. Interrupted writes at session end, not corruption.
Listed in `results/unreadable_frames.csv`; safe to delete, and no calibration set loses coverage.
