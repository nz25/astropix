# Findings

What we have learned about *this* rig and *this* data. Prose for humans; each entry cites the
`results/` file that proves it. An entry with no citation is an observation awaiting measurement,
and says so.

Entries are dated and appended. A published number that later turns out wrong is corrected in
place with the correction marked and dated, never silently — unlike `DECISIONS`, which is
append-only, this file is meant to state what is currently true.

---

*Reset 2026-08-27 (`DECISIONS` D30). The archive survey and the index measurements written here
during build sessions 1-3 were derived from a `results/` set that no notebook could rebuild.
They are preserved in git history at `9019bfe` and will be re-established by running
`notebooks/01_frame_index.ipynb`.*

## 2026-08-27 — The archive index: 15,102 frames, and what kind of data they are

`results/frame_index.csv`, written by `notebooks/01`. 100.6 minutes over SMB, 15,090 readable,
12 zero-byte. Every frame classified from its own pixels rather than its label or its folder
(D18). Snapshot `2026-08-27T20:27:50`.

**Read this as a description of a test corpus, not as a measurement of the rig.** These frames
were shot across a year of ordinary imaging, before this project existed and before any of its
conventions did. Nothing below is a defect. It is what a year of real observing looks like, and
the reason for indexing it is to know which subsets are usable for which purpose.

The one thing here that *is* a measurement of the rig: `mult16_frac` is **1.000000** at min,
mean and max across all 15,090 readable frames. Every stored value is an exact multiple of 16.
The 12-bit ADC in a 16-bit container is no longer a hypothesis, and header `EGAIN` — quoted per
12-bit ADU — cannot be applied to a stored pixel without dividing by 16.

### Temperature is not consistent, and the cooler does not always reach setpoint

Two setpoints in the archive: 8,716 frames at −20 °C, 6,140 at −10 °C, 246 with none recorded.
**2,132 frames (14%) sit more than 1 °C from what was commanded.**

| commanded | type | n | achieved |
|---|---|---:|---|
| −20 °C | flat | 253 | up to **+4.5 °C** |
| −10 °C | flat | 302 | up to +4.0 °C |
| −20 °C | bias | 120 | −12.0 … −10.5 |
| −20 °C | dark | 362 | −18.5 … −10.5 |
| −20 °C | light | 1,095 | −18.5 … −13.0 |

The excursions cluster on summer nights — 2026-07-12 and 2026-08-11…16 — which is what a 35 °C
ΔT predicts: −20 °C is unreachable above roughly 15 °C ambient, and the camera delivers
whatever it can without complaint. The flats are the extreme case; several were taken with the
cooler effectively not engaged.

**How to use the corpus given this:** match calibration by *achieved* temperature, never by
setpoint (D9 already requires it; this is the scale of the problem it was guarding against).
Where a subset matters and its temperature is doubtful, reshoot rather than reason around it.

### 684 frames are labelled `light` but measure as `dark`

The only off-diagonal cell in the whole 4 × 4 confusion table — every other frame's pixels agree
with its label. The disagreement runs one way only.

It is **two different situations sharing one symptom**, and the index separates them:

| | gain 252 (n = 317) | gain 50 (n = 367) |
|---|---|---|
| median level | 1232 — *exactly* the dark pedestal | 1288, ranging to 9524 |
| pedestal at that gain | 1232 | 1040 |
| median `clump_frac` | — | 0.00 (accepted lights: 0.73) |
| `tail_frac` ≥ 1e−5 | — | 72% of them |
| `OBJECT` | — | M 42, M 45, C 50, M 31, M 38 panels |

The gain-252 group sits precisely on the dark pedestal: those look like genuine darks captured
under a `Light` subframe type, inheriting the session's object name. The gain-50 group carries
real signal above pedestal and names bright targets, but shows no connected bright structure in
the sampled rows — cloud, moonlight, or a field too sparse for six 32-row blocks to catch a
star.

### The classification is therefore uncertain, and deliberately left so

**Which of the 684 are mislabelled darks and which are lights the classifier missed is not
settled, and the two demand opposite responses.** Mislabelled darks are an archive-cleanup item.
Missed lights mean `LIGHT_MIN_CLUMP` has a blind spot, and those frames would be silently
excluded from every light-frame analysis that trusts `measured_type`.

Recorded as an open observation rather than a conclusion. The discriminator is to open a dozen
of each group and look at the *whole* frame instead of the sampled rows — cheap, and not yet
done. Until then, anything selecting on `measured_type == "light"` should know it may be
short by up to 367 frames at gain 50.

### The NGC 7000 set is the exception, and the most useful thing in the archive

2,002 lights, and the only substantial subset shot to a deliberate design — a **2 x 6 grid**
(D28), both gains, six sub-exposure lengths, with **total integration held constant across every
rung**:

| | 15 s | 30 s | 60 s | 120 s | 240 s | 480 s | per rung |
|---|---:|---:|---:|---:|---:|---:|---:|
| **gain 50** | 448 | 224 | 112 | 56 | 28 | 14 | **6 720 s** |
| **gain 252** | 416 | 208 | 104 | 52 | 26 | 13 | **6 240 s** |

Every cell is exact. Holding total time fixed and varying only sub-exposure length is precisely
the comparison `SNR(T, t)` asks for, and it was shot deliberately that way.

**The ladder nights and the stray nights are different things.** The folder also contains 300
frames from 2025-08-08 and 2025-08-09 which are *not* part of the grid: 60 s only, gain 252, and
sitting at a sky level of 11 272 and 24 054 ADU against the ladder's 4 500–4 720 on the same
exposure — between 2.4x and 5.1x brighter, so moonlit or twilight, or a different framing. The
gain-252 counts above exclude them; included, the 60 s rung reads 404 frames and appears to
break the design, which it does not.

**Within each gain the ladder is repeated whole, per night, at a consistent sky.** Gain 50 ran
complete on four nights (2025-08-19, 08-20, 09-18, 09-19), gain 252 on three (08-17, 08-18,
08-19). Median sky at 15 s varies by under 4% across the nights of either gain. All frames
commanded −10 °C, all achieved between −10.5 and −9.0 °C — this subset is
temperature-consistent in a way the rest of the archive is not.

**And 2025-08-19 carries both gains**, each a complete ladder: 219 frames at gain 50 and 221 at
gain 252, same night, same target, same sky. Every other night is single-gain, so a cross-gain
comparison drawn from the set as a whole confounds gain with observing conditions — the two
gains are otherwise a month apart. **That one night is the controlled gain comparison**, and it
is the most valuable night in the archive.

*Corrected 2026-08-27, shortly after first publication. The original entry showed only the
gain-50 ladder, described gain 252 as "repeated" without its numbers, and reported its 60 s rung
as departing from the design. Denis flagged that the set was shot at two gains, which prompted
the recheck: the grid is exact at both gains, and the apparent anomaly was 300 frames from two
unrelated 60 s sessions in the same folder. The confound between gain and night, and the single
night that resolves it, were missed entirely.*
