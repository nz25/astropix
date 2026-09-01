# Session 04 — the offset state, mapped in bias

**No light source. Cap on. About three hours, and almost all of it is bias frames.**

Numbered protocols are ordered by execution. This is planning session E. It runs after the dark
bound, and it exists because of what that night found rather than because of anything anyone
planned.

## What this session is for

Session 03 found that **the camera's black level occupies discrete states about one ADC count
apart** (`dark_constants.json` → `offset_state_step` = 0.9931, in 4.1% of 244 frames, first seen
161 minutes into a five-hour run that changed nothing). It could not say why, because it varied
nothing that might cause it. This session varies things.

**It pins no term in σ².** That is stated first because CLAUDE.md requires a measurement to name
the coefficient it pins down, and this one does not have an answer of that shape. What it protects
instead is the *validity* of three coefficients that are already published:

| already published | how the state could reach it |
|---|---|
| `pedestal` (offset sweep, 77 gains) | a level, measured as a level |
| `R(gain)` (session 01, 77 gains) | a pair difference — immune *if* both frames share a state, and nobody checked |
| `g(gain)` (session 02, 8 gains) | signal is a difference of two levels; the variance is not, but the signal is |

Everything in `bias_sweep.csv` and `ptc_gain.csv` is a difference against a bias level. If the step
is one count everywhere, those tables are safe and this session ends as a gate. **If the step is
larger at high gain, they are not safe**, and the session has found a systematic in two published
sweeps. Section *The decisive test* says why that is a live possibility and not a worry.

**Not a repair of `D`.** The dark bound is 3,000× below L32's sky rate; sharpening it changes no
recommended exposure and no recommended gain. The 300 s / 600 s confound session 03 left open is
**deliberately not attacked here** — see *What is out of scope, and what would put it back*.

## The three hypotheses, and what separates them

The step's size against gain is the discriminator, and the two classes are cleanly separated by
session 01's own pedestal model, `pedestal = A + B · 10^(gain/200)` with `A` the digital term
(4.0032 counts per offset unit, gain-independent) and `B · 10^(gain/200)` the analog term the gain
stage amplifies.

**H1 — after the gain stage.** A digital or post-ADC level. The step is **fixed in counts**, the
same 0.993 at every gain. Note that 0.9931 is within one uncertainty of **a quarter of an offset
unit** (4.0032 / 4 = 1.0008), which is a specific and checkable version of this hypothesis.

**H2 — before the gain stage.** An analog reference shift, or a fixed number of electrons at the
sense node. These are the same signature: the step scales with the analog term, so it is tiny at
low gain and large at high gain, and it **jumps at the HCG threshold** exactly as `B` does.

**H3 — a firmware event.** The camera re-applies or recalculates something. Distinguished not by
size but by *when*: transitions happen only across a reconfiguration, never in a quiet stream.

Pre-registered predictions, in ADC counts, normalised to the measured 0.9931 at gain 250:

| gain | H1 (after) | H2 (before) |
|---|---|---|
| 0 | 0.993 | 0.154 |
| 100 | 0.993 | 0.488 |
| 190 | 0.993 | 1.375 |
| 200 | 0.993 | 0.558 |
| 250 | 0.993 | **0.993** — the anchor |
| 450 | 0.993 | 9.931 |

The two predictions differ by a factor of 6 at gain 0 and a factor of 10 at gain 450, against a
measurement precision on a plane mean of about 0.007 counts. **This is not a close call**, and it
is the reason the session is worth three hours.

## Settings, and why

- **Gain 250, offset 15, ROI 1024 × 1024 at (1408, 568)** as the baseline arm — session 03's
  configuration exactly, so the anchor point is commensurable with a night that has already been
  analysed. Every other gain in the sweep (0, 100, 450) is a **swept point in session 01 and
  session 02**, which matters because `g` is not interpolable (session 02's gain law fails its own
  1% test) and the step must be quotable in electrons as well as counts.
- **The ROI is not shrunk.** A 512² plane mean would still be far below the threshold, but the
  point of comparison is session 03's own levels and they were measured on this ROI. Data cost is
  ~2 MB a frame, and the budget below is built on it.
- Cooler at −10 °C, held in band for a continuous 10 minutes before the first frame, and **logged
  per frame with cooler duty**. Duty is not decoration here: session 03's smoke test showed duty
  climbing 13 points through the same half hour in which the pedestal moved, while sensor
  temperature sat flat at −10.0. If the state tracks duty, that is the answer, and it is free.
- **Ambient at start and end**, read and written down. Arm A's whole claim is about a machine
  warming up in a room; the room is a variable.

## Capture

Three arms. Arm A must run **first and from a cold power-on**, because it is the only one that can
see the onset; B and C follow it and may be reordered freely.

### Arm A — onset and idle gap (~2 h)

A continuous stream of bias frames at the baseline setting, from a camera that has just been
powered on and cooled. **The gap before each frame is drawn at random from {2, 15, 60} s** rather
than fixed, so that "time since the last readout" and "time since power-on" are estimated from the
same stream instead of being confounded. Mean gap ≈ 26 s.

| block | setting | frames | wall clock |
|---|---|---|---|
| A | gain 250, offset 15, ROI 1024² | ~290 | ~2 h, randomised gaps |

Nothing changes during arm A. No gain change, no offset change, no ROI change, no reconfiguration
— the arm's value is that it is the null condition, and session 03 already showed the state
appears in one.

### Arm B — the decisive test (~40 min)

Gain and offset, **interleaved and cycled**, never blocked. Session 03's ladder ran short to long
and left an exposure/time confound it could not resolve; that mistake is not repeated here.

| block | setting | frames | cycles |
|---|---|---|---|
| B-gain | gain ∈ {0, 100, 250, 450}, offset 15 | 20 per setting | **3**, order reshuffled each cycle |
| B-offset | gain 250, offset ∈ {15, 30, 60} | 20 per setting | **3**, order reshuffled each cycle |

420 frames. Three cycles is the minimum that lets a setting effect be separated from a time
effect: a state that appears once, mid-run, contaminates one cycle and is visible as an
inconsistency between cycles rather than as a spurious setting effect.

**Offset 60 is included deliberately.** If H1's quarter-of-an-offset-unit version is right, the
step is a property of the offset DAC and should be unchanged by which offset is selected; if the
step scales with the offset *setting*, it is somewhere else entirely.

### Arm C — reconfiguration (~20 min)

| block | what | pairs |
|---|---|---|
| C-set | bias, `configure(gain=250, offset=15)` re-asserted with **identical values**, bias | 40 |
| C-open | bias, `rig.close()` then `open_camera()` and re-cool to band, bias | 10 |

C-set is cheap and answers H3 directly: 40 paired frames straddling a no-op reconfiguration,
against arm A's 290 frames straddling nothing. C-open is slower because the camera must come back
into band, and 10 pairs is enough to see a large effect, which is the only kind worth acting on.

**Budget: ~830 frames, ~1.7 GB, ~3 h including the cool-down.** C: is the working drive and it is
tight; the frames are disposable once `results/` is written.

## Analysis rules, fixed before the data exists

Per CFA plane, on the mosaic, in ADC counts. Never debayer.

1. **Classification.** A frame's level is the mean of a plane; its *departure* is that level minus
   the median level of its peer group, where a peer group is every frame sharing gain, offset,
   exposure and ROI. A frame is in a far state when the departure exceeds **half the modal
   separation** of that setting's departure distribution, subject to a floor of **5× the
   within-state scatter**. This generalises session 03's fixed 0.5-count threshold, which is only
   correct if the step is 0.993 — that is the thing being tested, so the threshold cannot assume
   it. Report both, and report the within-state scatter per setting; if they disagree anywhere,
   the modal rule is the published one and the disagreement is a result.
2. **The step against gain, which is the session's headline.** Fit the measured step to both
   predictions in the table above and report each residual. **The published verdict is whichever
   the data supports, stated as one of H1 or H2, with the losing prediction's residual quoted
   beside it.** Two further readings come free: whether the step is constant *within* a
   conversion-gain branch, and whether it jumps at gain 200 — H2 predicts both, H1 predicts
   neither.
   **Quote the step in electrons as well as counts**, using session 02's `g` at each swept gain. A
   step that is a constant number of *electrons* is a statement about the sense node and is the
   most physically specific outcome this session can reach.
3. **Occupancy and transitions.** From arm A: the fraction of frames in each state, per 20-minute
   window; the run-length distribution; and the per-frame transition probability in each direction.
   **Report whether the process has memory** — a slow drift dithering across a threshold gives long
   runs and no isolated frames, an independent per-frame event gives geometric run lengths.
4. **A third state is a pre-registered outcome, not a surprise.** Report the largest |departure|
   seen in units of the step. If a departure of 2 steps ever appears, H2's "slow drift across
   quantisation boundaries" gains a lot and H3 loses.
5. **Regress occupancy on cooler duty, sensor temperature and elapsed time**, in that order of
   suspicion, and report all three even when they are null. Arm A's randomised gap is the fourth
   regressor: a state that depends on the idle time before a frame is a sensor-idle effect and
   nothing to do with warm-up.
6. **The rejection filter costs something, and the cost is measured.** Report what fraction of
   frames a session at each setting would lose to the filter. A 4% loss is a rounding error; a 40%
   loss at gain 450 would change how future sweeps are budgeted.

### What each outcome decides

| observation | consequence |
|---|---|
| step fixed in counts at every gain (H1) | **the published sweeps are safe.** The state is a post-gain level, the filter goes into every bench protocol as a gate, and this closes |
| step scales with the analog term (H2) | **session 01's `R` and session 02's `g` need re-examination at high gain**, where the step is several counts. That is a re-analysis of existing frames, not a re-shoot, and it is the next session |
| step = 4.0032/4 exactly, and independent of the offset setting | the state is a quarter of an offset unit — a mechanism, publishable as one, and a thing to ask ZWO about |
| transitions only across a reconfiguration (H3) | the fix is a protocol rule — do not reconfigure mid-block — and the filter becomes a check rather than a gate |
| occupancy tracks cooler duty | the first hour of every night is the suspect hour, and the settle criterion in every protocol needs a duty condition added to its temperature condition |
| no state appears at all in three hours | **report it as such.** The 2026-09-01 night stands; a null here bounds the recurrence rate and says the effect is rarer than one night suggested. It does not delete the finding |

## What is out of scope, and what would put it back

**The 300 s / 600 s confound.** Session 03's two exposure lengths differ by 0.811 counts against a
0.993 step, and because its ladder ran short to long, an exposure effect and a time effect are
indistinguishable in that data. Attacking it costs a night of long darks, and it is out of scope
here for a reason that is about the model and not about the interest of the question: `D` has left
σ², so a biased dark level changes nothing this project publishes — unless the bias is larger than
one step, which no observation suggests.

**What would put it back in scope:** arm B finding H2. If the step scales with gain, then a
1-count effect at gain 250 is a 10-count effect at gain 450, and 10 counts on a calibration frame
is no longer a curiosity. In that case the exposure question is asked at high gain, where it is
answerable in far less than a night.

**Not in scope either:** temperature as an axis (MISSION fixes the setpoint), the archive (no
published constant comes from it, and its frames were shot before any of this existed), and any
attempt to *fix* the state. We characterise the camera we own; we do not modify its firmware.

## Gates, before anything is kept

1. **White balance, proved in the pixels** (L01). Modal step of 16 on all four planes, run on
   stored values. Nothing captured before this passes is usable. It runs again after every gain
   change in arm B, because arm B changes gain 24 times and the gate is cheap.
2. **The pedestal is where session 01 left it.** At gain 250, offset 15, within 5 counts of 76.66.
   This catches a wrong *setting*, not a drift.
3. **The run starts in one state.** The first 20 frames of arm A must have a departure spread under
   0.1 counts. If the camera is already switching at minute zero, arm A's onset question is
   already answered and the analysis says so rather than pretending to look for an onset.

## Record for the session

Ambient at start and end, settle duration, the sensor-temperature and duty range over the run, the
random seed used for arm A's gaps and arm B's cycle order — **the seed is part of the record**,
because an interleave that cannot be reconstructed cannot be checked — and any block that ran with
a changed configuration.

## Notebooks

`09` measures and writes `results/`; `10` reads those files back and explains them. The pair is
the unit of work, and both purposes are agreed in conversation before either is created.

## LEGACY entries consumed

**None.** Nothing in the queue anticipated this — the state is a finding of this project's own
bench, not an inherited claim, and the queue stays at 14. This line exists to say that
deliberately, because a protocol that opens without harvesting `LEGACY` should have to explain
itself.
