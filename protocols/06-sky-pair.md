# Session 06 — the sky terms, and the first pair the model is asked to rank

**No light source. On sky, guided, through the ASIAIR. One target, one night, ~5 hours.**

This is the first protocol that points the camera at the sky. Everything before it characterised
the sensor with the cap on or a panel in front of it; the three constants left in MISSION's table
— `F_sky`, `η_comb`, `t_dead` — cannot be measured any other way. It is also the first session
that produces a **pair the model must rank**, which is the shape of MISSION's definition of done.

It runs before `05-linearity.md` finishes. Nothing here needs `ceiling(gain)`: no cell approaches
the top of the scale except star cores, and clipped star cores are the constraint being observed,
not a fault. Weather decides which of the two runs on a given night, and only this one needs sky.

## What this session is for

| pins | how |
|---|---|
| `F_sky` per CFA plane, e⁻/px/s | modal level of a nebula-free ROI, pedestal subtracted, × `g(gain)`, per frame |
| `t_dead`, s | frame-to-frame `DATE-OBS` gaps minus exposure, split into download and dither settle |
| `η_comb` on **registered** lights | measured sd reduction against ideal √N, subsampled at N = 2, 4, 8, 16, 32 to sit beside session 03's dark ladder |
| **the repeatability of the SNR estimator** | each cell split into two disjoint halves, stacked separately, differenced |
| **four ranked pairs**, two of them straddling HCG | four settings shot interleaved on one night, at matched wall clock |
| MISSION's third assumption — that the dimmest and brightest planes differ | `F_sky` per plane. If R, G and B agree, the per-plane Pareto framing buys nothing |
| **L32** — the retired suburban sky rate, 1.594 e⁻/px/s green | reproduce or refute it on our own frames |

**What it is not for.** `g(gain)` and `R(gain)` are **inputs**, consumed from
`results/ptc_constants.json` and `results/ptc_gain.csv` and never re-measured here. Not a gain
sweep — two gains, chosen, not scanned. Not `ceiling(gain)`. Not vignetting, focus, guiding or
seeing, all of which MISSION scopes out. And **not a picture**: a beautiful stack is a by-product,
and no framing, filtering or processing decision is made to improve one.

## Why these four settings

Two gains and two sub lengths, every combination:

| | 30 s | 120 s |
|---|---|---|
| **gain 50** | cell A | cell B |
| **gain 200** | cell C | cell D |

**Gain 50 and gain 200 are both swept points**, so every constant this night leans on is measured
rather than fitted. Session 02 published `gain_law.residual_pct` at 1.344 % against its own 1 %
rule, so `g` is **not interpolable** — which is exactly why gain 252, the setting the archive was
shot at, cannot be used to publish anything. That is the sharp reason this night must be reshot
rather than mined out of `Z:`.

**200 is the HCG threshold itself**, measured at 200 ± 2 in session 01. One gain unit below it the
sensor is in its noisy branch. From `ptc_gain.csv`, at −10 °C and offset 15:

| gain | `g`, e⁻/count | `R`, e⁻ | pedestal, counts | full well, e⁻ |
|---|---|---|---|---|
| 50 | 5.389 | 4.94 | 64.8 | 21 719 |
| 190 | 1.046 | 3.45 | — | — |
| 200 | 0.922 | **0.99** | 69.3 | **3 710** |

Five times less read noise, and just under six times less well. **That trade is the Pareto curve
MISSION exists to draw**, and this is the first night that puts a number on both ends of it.

**30 s and 120 s are both rungs of the archive's own NGC 7000 ladder** (15 / 30 / 60 / 120 / 240 /
480 s, gains 50 and 252, seven nights, 2 002 frames). They are chosen for that: the archive is a
cross-check, never a source, and a cross-check needs matching settings.

`D` does not appear in the choice. Session 03 bounded dark current at **0.000534 e⁻/px/s** at
−10 °C, three orders below L32's predicted sky rate, so `D` is arithmetically absent from every
number here and is carried only to be shown negligible.

### What the model predicts, before a frame is taken

`SNR ∝ √(t/(t+t_dead)) / √(F_sky + D + R²/t)`, with `F_sky` from L32 and `R` from session 02.
Percentages are how much better the second setting is than the first. Two values of `t_dead`
bracket the answer: 0.7 s is the archive's bare download, 19 s is its measured mean once dithering
is counted (see *Dithering* below).

| pair | plane | `t_dead` = 0.7 s | `t_dead` = 19 s |
|---|---|---|---|
| A → B (t-pair at gain 50) | G | +16.7 % | +37.4 % |
| C → D (t-pair at gain 200) | G | **+1.6 %** | +19.7 % |
| A → C (**straddles HCG**, t = 30 s) | G | +21.6 % | +21.6 % |
| B → D (**straddles HCG**, t = 120 s) | G | +5.9 % | +5.9 % |
| A → B | B | +25.5 % | +47.7 % |
| C → D | B | +2.2 % | +20.3 % |
| A → C | B | +35.2 % | +35.2 % |
| B → D | B | +10.1 % | +10.1 % |

MISSION's definition of done wants **three pairs the model predicts apart, one straddling HCG**.
This night offers four, two of them straddling. It also shows why the night is designed around
`t_dead`: the C → D pair is a **near-tie at 1.6 % if dead time is small**, and a 20 % separation if
it is not. `t_dead` is not a bookkeeping constant here — it is what decides whether one of the four
pairs is a test at all.

The blue plane separates harder than green in every pair, because L32 puts blue sky flux at 0.910
e⁻/px/s against green's 1.594. If that survives measurement, MISSION's third assumption holds and
blue is the plane that sets the exposure floor.

## Target — NGC 7000, and why

| | |
|---|---|
| RA / Dec | 20h 59m, +44° 31′ |
| transits | ≈ 22:10 local in early September, near zenith |
| field | 2.42° × 1.37° at 263 mm and 2.27″/px — the nebula roughly fills it |
| archive | **2 002 frames over 7 nights**, gains 50 and 252, the same exposure ladder |

Four things make it the right target and each is a requirement, not a preference:

1. **Faint extended signal fills the central ROI.** That is MISSION's criterion verbatim. A small
   galaxy on a blank field measures the estimator, not the signal.
2. **Cygnus is dense in stars of every brightness**, which is what the star-colour constraint needs
   observed. The clipping fraction at gain 200 against gain 50 is the constraint's first real
   datum.
3. **It has genuinely dark structure** — the Gulf of Mexico — so a sky ROI can be placed on the
   same frame as the signal ROI. See *Framing*.
4. **It transits mid-session**, so airmass runs down and back up roughly symmetrically and the
   interleave averages it out rather than fighting it.

**Framing is a constraint here, not an aesthetic.** Rotate and centre so that the **Gulf of Mexico
occupies one corner**, then keep that framing for the whole night and record the plate solution.
Two ROIs are defined from it and never moved:

- **Signal ROI** — 1024 × 1024 at (1408, 568), the same box sessions 01 and 03 used, placed on
  bright nebula. Every SNR number comes from here.
- **Sky ROI** — 512 × 512 in the darkest corner, on no visible nebula. Every `F_sky` number comes
  from here.

**`F_sky` from this field is an upper bound on true sky**, because unresolved nebulosity is inside
it and cannot be separated. It is published as such. It is also the *right* upper bound for the
model, which needs the level sitting under the faint signal, not the zodiacal sky in the abstract.

## Settings

- **Offset 15** throughout, on every cell and every bias — `project_offset`, fixed and not swept
  again.
- **−10 °C**, held in band for a continuous 10 minutes before the first frame, and **logged per
  frame**. A frame outside ±0.5 °C is flagged, not silently kept.
- **Guided**, 32 mm f/4 guide scope. Guide RMS logged per frame; the rejection threshold is fixed
  before the night (see rule 3) and never adjusted while looking at the data.
- **Autofocus at the start, and only between laps thereafter.** A refocus inside a lap breaks the
  one thing the lap exists to protect. Every autofocus event is timestamped and the surrounding
  lap is flagged.
- **No filter.** None owned; MISSION scopes a purchase out until the data argues for one.

## Capture — the rotation

**One frame per setting, rotating, all night.** Never in blocks.

```
lap = [ gain 50 @ 30s ] [ gain 50 @ 120s ] [ gain 200 @ 30s ] [ gain 200 @ 120s ]
```

The sky brightens and darkens, the target climbs and falls, dew forms, the mount's guiding drifts.
Shot in blocks, none of that can be told apart from the setting. **This is session 04's mistake and
it is not repeated**: its two arms differed in what was being tested *and* in when they ran, and
one of them turned out to have been warming. Interleaved, every slow drift hits all four cells
equally and cancels out of every ratio.

**Dither after every frame, not every second frame.** This is the one place the protocol departs
from the archive, and the reason is a confound, not a preference. A dither costs a long settle;
if dithering happens on some frames and not others, whichever cell sits after the dither pays an
overhead the others do not, and that overhead lands inside `t_dead` where it cannot be separated
from the setting. Dithering uniformly makes `t_dead` **one number** and makes it fair. It also
gives `η_comb` the maximum number of distinct dither positions, which is what the registration
half of that loss is measured against.

**What the archive says this costs, and it is the night's likely headline.** Frame-to-frame gaps
across all 2 002 NGC 7000 frames, exposure subtracted:

| | |
|---|---|
| download and save | **0.68 s**, flat across every gain and exposure |
| dither settle | **≈ 35 s** median |
| frames paying a settle | ≈ 48 % — dithering was on every second frame |
| **mean `t_dead`** | **17–20 s**, independent of exposure length |

At 30 s subs a mean `t_dead` of 19 s means **39 % of the night is spent not collecting photons**,
and dithering every frame will push that higher. That is a prediction, and measuring it properly
is one of this session's three constants. It is not a reason to change the plan: the number is what
the model consumes, and it must be the number from the workflow actually used.

Do **not** tune the dither settle threshold to make this look better. Tonight measures the rig as
it is run; changing the settle is a separate, deliberate experiment with its own before-and-after.

### Frame counts

With a 35 s settle, one lap is `300 s` of exposure plus `4 × 35.7 s` of overhead ≈ **7.4 minutes**.

| | |
|---|---|
| capture window | 5.0 h |
| laps | ≈ 40 |
| frames per cell | **≈ 40** |
| integration, each 30 s cell | 20 min |
| integration, each 120 s cell | 80 min |

40 per cell is the design minimum and it is set by two things, not by taste: it splits into two
disjoint halves of 20 for the repeatability test, and it subsamples at N = 2, 4, 8, 16, 32 to lay
`η_comb` directly beside session 03's dark ladder, which published 0.9864 / 0.9762 / 0.9439 /
0.8830 / 0.7902 at those N. **A short night that yields fewer than 24 per cell is a session that
did not run** — say so and reshoot, rather than publishing a stack the ladder cannot reach.

### Bias brackets

**20 bias frames at each gain, at the start and again at the end**, through the same ASIAIR, at
offset 15 and minimum exposure. They cost under a minute.

They are not optional bookkeeping. `F_sky` is defined on the pedestal-subtracted frame, so pedestal
error goes straight into the sky rate. Session 03 found the pedestal hops by **0.9931 counts on
4.1 % of frames** — the offset state — and session 04 traced it to something exposure-correlated.
A bracket at each end is what lets the notebook say which state the night sat in, per gain, rather
than assuming the fitted pedestal.

**No flats.** Nothing here needs one: both ROIs are fixed, small and analysed on their own, and
optics/vignetting is phase 2 in MISSION. Saying so is the point — an unexplained missing flat is
how a silent substitution starts.

## Gates

In this order, each needing the one above it. **Gates 1 and 2 are blocking**: a failure ends the
night, it does not get worked around.

| gate | settles |
|---|---|
| 1 | white balance, from the pixels |
| 2 | the cooler holds |
| 3 | guiding is settled, and what counts as a bad frame |
| 4 | the framing, and that both ROIs land where they should |
| 5 | the first lap's timing, before committing five hours to it |

### Gate 1 — white balance, from the pixels

**`stats.value_step` must return 16 on all four planes.** This is gate 1 of every protocol in this
repo and it is not skipped because the frames come from the ASIAIR rather than from `asi.py`.
`asi.neutralise_white_balance` runs when *this project* opens the camera. **The ASIAIR opens it
independently**, and a control this project never set is a control this project cannot vouch for.

Take **one frame off the ASIAIR, pull it over, and run the check before committing to the night.**

Three archive frames were tested while writing this protocol — gain 50 at 30 s and 120 s, gain 252
at 60 s — and all three returned step 16 on R, G1, G2 and B. So the ASIAIR is expected to pass and
the gate is expected to be a formality. **It is still blocking.** Greens at 16 with red at 17/18 and
blue at 24 is the fingerprint of white balance still being applied, and nothing captured after that
fingerprint appears is usable.

### Gate 2 — the cooler holds

−10 °C, in band for a continuous 10 minutes before the first frame. Logged per frame thereafter.
On sky the ambient is not the bench's, and a TEC at its limit in September air is a real
possibility rather than a formality.

### Gate 3 — guiding, and the rejection rule fixed in advance

Record guide RMS per frame. **The rejection threshold is written down before the first frame and
not touched afterwards.** A threshold chosen after seeing which cell it hurts is not a threshold.

Cloud and gust rejection likewise: the rule is stated in advance, applied to all four cells
identically, and the count rejected per cell is published. **If the four cells lose materially
different numbers of frames, the interleave has been broken** and that must be reported, not
averaged over.

### Gate 4 — framing, and the two ROIs

Plate-solve, confirm the signal ROI sits on bright nebula and the sky ROI on none, record the
solution. Then do not touch it. A meridian flip rotates the field 180°; **either avoid the flip
inside the capture window or redefine both ROIs after it and treat the two halves as separate
blocks.** Deciding this in advance is what stops the flip becoming a silent confound.

### Gate 5 — the first lap's timing

Run one lap. Pull the four frames. Check the `DATE-OBS` gaps against exposure and confirm
`t_dead` is what the archive predicts, per frame and uniformly across the four cells. A dither
that fires on some frames and not others shows up here and nowhere else until the analysis, five
hours later.

## Analysis rules

The notebook does the loop; the library does one frame. These are the rules it follows.

1. **Everything on the CFA mosaic, split into RGGB sub-planes.** Never debayer. Every number in
   this session is per plane, and the ones quoted as one number are stated as a mean over four.
2. **Pedestal from the brackets, per gain**, with the offset state assigned before subtraction —
   never from the fitted law alone when a measured bracket exists.
3. **`F_sky` is the modal level of the sky ROI**, not the mean and not the median. The mean is
   dragged by stars, the median by unresolved nebulosity; the mode is what the background actually
   sits at. Converted to e⁻/px/s with `g(gain)` from session 02, published per plane and per frame,
   with its variation across the night stated — L32's own figure fell about 5 % across two hours as
   its target rose, and reproducing *that* is as much the test as reproducing the number.
4. **`t_dead` is published as a mean and a decomposition**, never as a median. The archive's median
   is 0.8 s and its mean is 19 s, and the model consumes the mean. A constant published as a median
   here would understate the overhead by a factor of twenty.
5. **`η_comb` is measured on registered, dithered lights** and reported at the same N as session
   03's dark ladder, beside it. The dark figure is an upper bound by construction — no registration,
   no resampling — so the gap between the two **is** the resampling loss, and that is the number
   this session adds. Provenance records stack size, rejection settings and the dither cadence.
6. **The SNR estimator's repeatability is measured before any pair is judged.** Split each cell into
   two disjoint halves of 20, stack each, measure SNR in the signal ROI, take the difference. **A
   predicted separation smaller than that difference is a tie and is published as a tie**, not as a
   pass. MISSION is explicit that a pair the model calls a tie is a null result every model passes.
7. **Star clipping is counted, not eyeballed.** Fraction of stars with a clipped core, per plane,
   per cell, against the same detection list. Gain 200 against gain 50 at matched integration is
   the star-colour half of the Pareto point, and it is the first time this project measures it.
8. **The archive comparison is recorded beside the bench numbers and never averaged into them.**
   No published constant comes from `Z:`. The seven NGC 7000 nights are a cross-check on `F_sky`
   and on `t_dead`, and that is all they are.

## What lands where

| result | destination |
|---|---|
| `F_sky` per plane, e⁻/px/s, with its variation across the night | `results/sky_constants.json` |
| `t_dead`, mean and decomposition, with the dither cadence it was measured under | `results/sky_constants.json` |
| `η_comb` on registered lights, at N = 2 … 32 | `results/sky_constants.json` |
| SNR estimator repeatability | `results/sky_constants.json` |
| per-frame sky, guiding, temperature, rejection | `results/sky_frames.csv` |
| the four cells' SNR, predicted and measured, with the ranking verdict | `results/sky_pairs.csv` |
| star clipping fraction per plane per cell | `results/sky_pairs.csv` |
| **L32**, reproduced or refuted | `results/` as the working suburban sky rate, and deleted from `LEGACY.md` |

`LEGACY.md`'s L32 is the only entry this session consumes. L31 needs the light source and stays
queued for `05-linearity.md`.

The measuring notebook is `17_sky_pair.ipynb`; its explainer is `18_sky_pair_read.ipynb`. (This
protocol was written expecting 14 and 15; the linearity pair took those numbers, and the repair
session this night's setpoint forced — `07-cold-constants.md` — took 15 and 16.)
