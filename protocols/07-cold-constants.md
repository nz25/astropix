# Session 07 — the constants at −20 °C, and the temperature coefficient nobody has measured

**Light source required. Cap off, panel in front, indoors. No sky, no weather, ~1.5 hours.**

Session 06 ran. It ran at **−20 °C**, not at the −10 °C every other bench run in this repo used,
and every constant the sky analysis consumes — `g(gain)`, `R(gain)`, the pedestal — is published
at −10 °C. Using them on −20 °C pixels is a silent substitution, and this repo forbids those by
name. This session removes the substitution by measuring the constants where the frames were
actually taken.

It is a **repair session**, and that is the honest word for it. It exists because a setpoint
drifted from the protocol, not because a term in the model needed pinning down. It is kept small
for that reason: two gains, not eight; no gain law; no linearity; no dark current.

## What this session is for

| pins | how |
|---|---|
| `g(gain)` at −20 °C, gains 50 and 200 | slope of pair-difference variance against signal, per CFA plane — session 02's rule 3, unchanged |
| `R(gain)` at −20 °C, ADC counts and e⁻ | temporal σ of the bias block at each gain, × `g` for electrons |
| `pedestal(gain)` at −20 °C | plane mean of the bias block, with the offset state assigned before it is used |
| **the temperature coefficient of all three** | the same three quantities measured at −10 °C in the same sitting, against −20 °C |
| **whether this bench still reproduces session 02** | the −10 °C arms against `results/ptc_constants.json`, measured five weeks and one panel reconfiguration later |

**What it is not for.** The gain law — two gains cannot fit it and nothing here needs it, because
50 and 200 are both *measured* points and session 06 leans on no interpolated gain. Linearity,
`ceiling(gain)` and full well: session 05 published those at −10 °C and no sky frame in session 06
comes near the top of the scale except star cores, which are the constraint being observed rather
than a level being trusted. Dark current: session 03 bounded it at **0.000534 e⁻/px/s at −10 °C**
and −20 °C is colder, so the bound is *stronger* at the session-06 setpoint and needs no rerun to
say so. HCG, PRNU, the FPN test: all settled, none temperature-critical to the arithmetic session
06 does.

**And it is not a licence to move the project setpoint.** MISSION fixes cooling at −10 °C. This
session characterises a temperature the camera was accidentally run at; it does not adopt it.

## Why three arms, and why they are not interleaved

```
arm 1:  −10 °C     arm 2:  −20 °C     arm 3:  −10 °C
```

Session 04's mistake was a two-arm session whose arms differed in what was tested *and* in when
they ran, and one of them turned out to have been warming. The fix everywhere else in this repo is
to interleave. **Here interleaving is impossible**: the TEC needs minutes to move 10 °C, so a
frame-by-frame rotation would spend the whole session in transit and none of it in band.

Bracketing is what is available instead. The two −10 °C arms sit either side of the −20 °C arm, so
anything that drifts across the session — the panel warming, the room, the bench — appears as a
**disagreement between arm 1 and arm 3**. That disagreement is not noise to be averaged away: it is
the uncertainty on the temperature comparison, and it is published as such. If the two −10 °C arms
agree to better than their own repeat scatter, the −20 °C arm between them is clean. If they do
not, the session measured the bench and not the sensor, and says so.

The panel configuration is **not touched between arms**. Same patch colour, same grey level, same
sheet count, same `t_sat` per gain, set once before arm 1 and recorded. A reconfiguration between
arms would put a second difference inside the comparison, which is the failure this shape exists to
avoid.

### What the arms are expected to show

A prediction, named as one, and the point of writing it before the data exists.

**`g` should barely move.** System gain is set by the sense-node capacitance and the ADC reference,
neither of which has a strong temperature coefficient over 10 °C. A shift of more than a few tenths
of a percent would be a surprise worth chasing rather than a correction worth applying.

**`R` should fall slightly.** Read noise has a thermal component; colder is quieter. A fall of a few
percent is ordinary.

**The pedestal is the one that may actually move**, and it is the one session 06 is most exposed to.
`F_sky` is defined on the pedestal-subtracted frame, so a pedestal error goes into the sky rate
count for count. At gain 50 the published pedestal is 64.8 counts and 120 s of L32's green sky is
about 35 counts, so **a one-count pedestal error is a 3 % error in `F_sky`**. That is the arithmetic
that makes this session worth an evening.

If all three move less than their own uncertainties, the result is that session 02's constants were
usable at −20 °C after all — and that is a measurement, not a wasted night. It is also the only way
to be *entitled* to say so.

## Settings

- **Offset 15** throughout — `project_offset`, fixed by session 01 and not an axis here.
- **Gains 50 and 200 only.** Both are session 02 swept points, so every comparison is row-for-row
  with no interpolation on either side. They are exactly the two gains session 06 shot.
- **ROI 1024 × 1024 at (1408, 568)** — even origin and extent, or the Bayer phase shifts (L05).
  The same box sessions 01, 02, 03 and 05 used.
- **Panel:** reuse session 05's published `patch_colour_per_gain` and grey level for gains 50 and
  200. Solving the balance again would be a second difference between this session and 02.
- **The whole session runs in one kernel.** Closing the camera drops the cooler, so a session split
  across two processes is not possible and a dead kernel restarts from ambient.

## Gates

In this order, each needing the one above it. **Gates 1 and 2 are blocking.**

### Gate 1 — white balance, from the pixels (L01)

`asi.neutralise_white_balance` runs on open, and reading the control back only proves the control
took. The evidence is `stats.value_step`: the modal step between adjacent distinct values must be
**16 on all four planes**, measured on a zero-light frame. Greens at 16 with red at 17/18 and blue
at 24 is the fingerprint of white balance still being applied.

**Nothing captured before this passes is usable.** Stop; do not correct it later.

### Gate 2 — the cooler reaches −20 °C, and holds it

**This is the gate that can end the session, and it has never been run on this rig.** Every bench
setpoint in this repo has been −10 °C. −20 °C is 10 °C further down, the duty cycle will be far
higher, and a TEC that cannot hold it indoors in a warm room is a real possibility rather than a
formality — session 06 held it under a September night sky, which is not the same test.

The rule: **in band (±0.5 °C) for a continuous 30 seconds, with the duty cycle recorded**, judged by
the temperature trend and not by duty. Then, and this is the part that matters, **the duty at the
end of the −20 °C arm is compared against the duty at its start.** A TEC climbing towards 100 % is
one that will lose the setpoint later in the arm, and a frame shot on the way out of band is a frame
that has to be retaken.

If −20 °C cannot be held, **stop and say so.** The fallback is stated here so nobody has to invent
one at midnight: session 06's frames are then characterised by a *bounded* argument rather than a
measured one — the constants at −10 °C, with the temperature coefficient published as unmeasured
and `F_sky` carrying the full uncertainty that implies. That is a worse answer, published as a worse
answer. It is not a reason to shoot at −15 °C and interpolate.

### Gate 3 — `t_sat(gain)`, measured cold at each gain and each arm

Solve `t_sat` from the *measured* flux at the session-05 patch colour, at the arm's own temperature,
before that arm's ladder. **Never carried across arms and never extrapolated** — it is cheap to
measure and an assumed `t_sat` puts the whole ladder in the wrong place.

That `t_sat` is measured per arm is also a free check on the panel: three numbers at the same colour
and level, and any drift in the backlight shows up in them before it shows up in a gain.

## Capture

Per arm, per gain:

| block | what | frames | why |
|---|---|---|---|
| 1 | bias, at minimum exposure | **20** | pedestal *and* `R` in counts; 20 so the offset state can be assigned rather than assumed |
| 2 | the ladder, 12 geometric rungs | **4** each | two independent pairs per rung, so the variance has a repeat |

Twelve rungs, geometric at ×1.679, from 0.3 % to 90 % of `t_sat` — session 02's ladder, unchanged
and for its reason: with a linearly spaced ladder every point sits in the bright end and the fit's
low end is unconstrained, which is where the slope absorbs its error (L10).

```
0.3  0.5  0.85  1.4  2.4  4.0  6.8  11.4  19.2  32  54  90   (% of t_sat)
```

Neither gain needs session 02's top-rung cap: that cap bound at gains 300 and 450, where a frame's
own sigma stops clearing the top code. At gains 50 and 200 the margin at 90 % is 5–20 σ.

**Discard the first 2 frames after every gain change and the first frame after every exposure
change**, and do not write them. **Discard nothing for a temperature change** — the cool-down gate
already covers it, and a discard rule that fires on the thing being tested is a way to hide it.

Temperature discipline as session 02: a frame whose header says it was shot outside the band is
**not written, it is retaken**, and a warm-side reading holds the run for a continuous
`asi.RECOVER_S` before retaking. **10 retakes of one frame slot, or a hold past 300 s, stops the
arm** — check ambient and the fan.

≈ 3 arms × 2 gains × (20 + 48) = **408 frames**, ≈ 0.8 GB at the 1024 × 1024 ROI.

## Analysis rules, fixed before the data exists

Statistics on the CFA mosaic, split RGGB, never debayered. Values in ADC counts.

1. **The pedestal is the plane mean of that arm-and-gain's own bias block**, with the offset state
   assigned across the 20 frames first (`stats.offset_state`) and the near state used. Never the
   fitted law when a measured block exists, and never another arm's block — that is exactly L14's
   cautionary tale, a dark sitting one count below a bias shot four hours earlier, producing a
   negative dark current.
2. **Signal** = plane mean of (flat − that arm-and-gain's pedestal). Per plane, never on the frame
   mean (L12).
3. **Variance** = σ² of the difference of a frame pair, divided by 2. Blind to fixed pattern by
   construction, which is what makes the FPN cross-check below a test rather than a tautology.
4. **`g`** = the slope of variance against signal, per plane, with read noise **passed in** from
   this session's own bias block and not taken from the intercept (L10). The fitted intercept is
   kept as a cross-check and is never the answer.
5. **`R` in ADC counts** = the temporal standard deviation across the bias block, per plane, on the
   frames in the near offset state only. A state hop is a black-level move, not read noise, and
   including one inflates `R` by the step.
6. **The temperature coefficient is `(value at −20) − (value at −10)`**, with the −10 °C figure
   being the **mean of arms 1 and 3** and its uncertainty being **half their difference**, not the
   scatter within either. Published per gain and per plane.
7. **The session-02 cross-check is recorded beside the new numbers and never averaged into them.**
   Arms 1 and 3 against `results/ptc_constants.json` at gains 50 and 200. Agreement vouches for the
   bench; disagreement is a finding about the bench and is published as one.
8. **Nothing here overwrites `results/ptc_constants.json`.** Session 02's constants are correct at
   their own setpoint and stay exactly as published. This session writes its own file, and the sky
   analysis reads that one because its frames are at that temperature.

### What each outcome decides

| observation | consequence |
|---|---|
| arms 1 and 3 agree inside their repeat scatter | the bench is steady across the session; the −20 °C arm is clean and every number below is publishable |
| arms 1 and 3 disagree | the session measured drift, not temperature. Publish the disagreement, publish no coefficient, and reshoot with a shorter session or a warmed panel |
| arms 1 and 3 reproduce session 02 at gains 50 and 200 | two sittings five weeks apart agree, which is stronger evidence than either alone, and session 02's constants gain a repeat they did not have |
| they do not reproduce session 02 | **do not average them.** Something changed between the sessions — the panel, the room, the camera — and finding it is the work. Session 06 waits |
| `g` moves less than its own uncertainty | the substitution session 06 would have made was harmless after all, which is now a measurement rather than a hope, and `F_sky` may be published with either |
| `g` moves measurably | every electron figure in session 06 uses the −20 °C value, and the coefficient is published so the next accidental setpoint costs an hour instead of an evening |
| the pedestal moves by ~1 count or more | this session paid for itself: at gain 50 that is 3 % of `F_sky`, which is inside L32's own night-to-night variation and would have been invisible |
| −20 °C cannot be held | gate 2's fallback. Session 06 is published with −10 °C constants, an explicit uncertainty, and the coefficient named as unmeasured |

## Record for the session

Ambient at start and end, panel warm-up start time, grey level and patch colour per gain, sheet
count, measured flux and `t_sat` per gain **per arm**, ROI, offset, WB values after setting, gate 1
modal steps per plane, the cool-down trace and settle duration **for each of the three arms**, the
duty cycle at the start and end of the −20 °C arm, capture tool and version, and anything touched
mid-session.

## What lands where

| result | destination |
|---|---|
| `g`, `R` and pedestal at −20 °C, per gain, per plane | `results/cold_constants.json` |
| the same at −10 °C, both arms, and session 02 beside them | `results/cold_constants.json` |
| the temperature coefficient of each, with its uncertainty | `results/cold_constants.json` |
| every rung, every arm | `results/cold_rungs.csv` |
| every bias frame's level and offset state | `results/cold_bias.csv` |

## LEGACY entries consumed

**None.** This session checks no inherited claim and empties no queue entry — it repairs a setpoint
mismatch, and saying plainly that it harvests nothing is better than reaching for an entry it does
not really test.

The measuring notebook is `15_cold_constants.ipynb`; its explainer is `16_cold_constants_read.ipynb`.
