# Session 08 — dithering every fourth frame, and what it costs

**No light source. On sky, guided, through the ASIAIR. NGC 7000, one setting, one moonless
evening, as long as the dark lasts.**

## Checklist — at the mount

Tick in order. **The first item is the one session 06 got wrong**: it ran at −20 °C, and a whole
repair session (07) existed only because of it.

**Before the first light frame**

- [ ] **Cooler set to −10 °C. Not −20.** Read the setpoint back on the ASIAIR screen, then wait
      until the sensor *reads* −10 °C and has held it for 10 minutes.
- [ ] Gain **50**. Offset **15**.
- [ ] Exposure **120 s**.
- [ ] Dither **every 4 frames**. Same dither size and settle settings as session 06 — do not tune
      them.
- [ ] NGC 7000, framed as session 06: **Gulf of Mexico in the bottom-right corner**. Plate-solve
      and write the solution down.
- [ ] **Meridian flip done before the first light frame.** NGC 7000 transits around 20:10 local in
      early October. Last time the flip came 22 minutes in and cost 13 frames.
- [ ] Autofocus.
- [ ] **20 bias frames**: gain 50, offset 15, shortest exposure.
- [ ] **Gate 1**: pull one of those bias frames to the laptop and run, from the repo root:
      `python -c "from astropix import fits, spatial, stats; m, _ = fits.read(r'PATH'); print({k: stats.value_step(v) for k, v in spatial.split(m).items()})"`
      — it must print **16 for R, G1, G2 and B**. Anything else: stop, the night is not usable.

**The first eight light frames** (two dither cycles)

- [ ] Pull them and read the `DATE-OBS` gaps. Expect, in each cycle of four, **three short gaps and
      one long one** (the dither). Four long gaps means dither is still on every frame; no long gap
      means it is off. Fix it now, not after four hours.
- [ ] Check `CCD-TEMP` in the header reads about −10.

**During**

- [ ] Note the clock time of any refocus, cloud, pause or restart.
- [ ] Stop at moonrise or at dawn, whichever comes first.

**After**

- [ ] **20 bias frames** again, same settings as before.
- [ ] Copy the night to `Z:\pix\_astro\astropix\data\session08\` — not to C: (the working-drive
      rule in `CLAUDE.md`).

---

## What this session is for

Session 06 dithered after every frame, on purpose, so that four interleaved settings paid the same
overhead. That made `t_dead` one fair number, and it hid the two things the dead-time work in `33`
needs: how long saving a frame takes on its own, and what stacking loses when frames share a
dither position. Tonight shoots **one setting**, so nobody is treated unfairly by a dither landing
on their frame, and the dither cadence can finally be changed.

| pins | how |
|---|---|
| **download and save**, s — `t_dead`'s split, until now inferred | `DATE-OBS` gaps minus exposure on frames **not** following a dither |
| **dither settle**, s | the same on frames that follow a dither, minus the download |
| **`t_dead` at one dither per 4 frames** — the cadence formula `download + settle / 4`, tested | the mean gap over the whole night, against the formula built from the two lines above |
| **`η_comb` with 4 frames per dither position**, past N = 18 | registered lights, `25`'s method, subsampled to N = 32 and 64 |
| **star clipping on a second night**, gain 50 at 120 s | counted as `29` counted it, against session 06's cell B at the same setting |
| `F_sky` per plane on a moonless evening | as session 06, rule 3 — a by-product, recorded and not a headline |

**What it is not for.** Not a gain comparison: gain 50 only, because `33` already prices gain 200
from published constants, and nothing tonight could change that except the download, which this
night measures anyway. Not a ranked pair. Not the mount's limit on long subs: 120 s is a setting
session 06 already shot for 37 frames with none rejected. Not seeing, focus or guiding. And **not
a picture**, though one comes out of it.

## Why this setting

**Gain 50 at 120 s** is session 06's cell B, repeated. That buys two things. It is the setting the
trade-off curve puts at about 1.2% of stars clipped, which Denis chose for star colour. And it is
the one setting where **last night's measured answer can be laid beside tonight's**, so the
star-colour half gets a second night without anything else changing.

**Every fourth frame** is where `33`'s arithmetic says most of the gain is, and it leaves three
frames out of four with no dither in front of them — which is what measures the download directly.

### What the model predicts, before a frame is taken

From `results/dither_flip_constants.json`, `results/sky_constants.json` and the archive figures
quoted in session 06 (cross-checks, never sources):

| quantity | prediction |
|---|---|
| download, frames with no dither in front | **0.68 s** (the archive measured it directly); our own night only bounds it at ≤ 7.99 s |
| dither settle | **31–35 s** (ours inferred, archive measured) |
| mean `t_dead` at one dither per 4 frames | **8.4–9.4 s** with the archive's download; **13.9 s** if the download is really 8 s |
| SNR gain over dithering every frame, *if stacking loses nothing* | **+8.6%** (fast download) to **+6.4%** (slow download) |
| star clipping, any plane, at 4095 | **1.15%** — 92 of 8033 stars on session 06's cell B. The model's figure at the safe ceiling is 1.23% |

**The decision rule, written before the data.** Dithering every fourth frame is worth keeping if
the stacking efficiency it costs is smaller than the dead time it saves. At matched stack size,
against `25`'s every-frame ladder:

> **keep every-4th-frame dithering if `η_comb(4 per position) / η_comb(every frame)` stays above
> 0.92–0.94** — 0.92 if the download comes out fast, 0.94 if slow. Below that, every-frame
> dithering was right and the 6–9% was never real.

`25`'s every-frame ladder only reaches N = 18, so the comparison is made at N ≤ 18. Above 18 tonight
has the only ladder, and it is published as such: how far the "no stacking loss" assumption under
`31`'s whole curve survives, at this cadence.

**Star clipping is not pass/fail.** Same field, same setting, a different night: what moves it is
seeing and focus. The number is the night-to-night spread of the star-colour constraint, which says
how far a curve drawn from one night can be trusted on another.

## Target and framing

NGC 7000, for the reasons session 06 gives, and for one more: `27`'s star mask, `29`'s star
method and `register.js` all exist for this field already.

**Framing is session 06's.** Gulf of Mexico in the bottom-right corner, so the same ROIs apply
unchanged: signal ROI 1024 × 1024 at (1408, 568), sky ROI 512 × 512 at (3264, 1584). Plate-solve
and record the solution. A framing that cannot reach those ROIs is fixed before the first frame,
not after.

**No meridian flip inside the capture window.** By astronomical dark in early October the target
is already past transit, so the flip is done before the first light frame and never during.

## Settings

- **−10 °C**, held for 10 minutes before the first frame and logged per frame. A frame outside
  ±0.5 °C is flagged, not silently kept. **This is MISSION's setpoint, and the model's main
  constants are measured there** — tonight needs no `cold_constants.json` repair.
- **Gain 50, offset 15**, `project_offset`, not swept again.
- **120 s**.
- **Dither every 4 frames**, same dither size and settle threshold as session 06. Do not tune the
  settle to make the numbers look better: tonight measures the rig as it is run.
- **Guided.** If the ASIAIR's guiding log can be exported for the night, keep it beside the frames.
  If not, the cloud test below is the rejection rule, as in session 06.
- **Autofocus at the start.** A later refocus is allowed if the stars visibly soften, timestamped,
  and its gap is excluded from `t_dead` by rule 3 below.
- **No filter, no flats, no darks**, as session 06. `D` at −10 °C is three orders below the sky.

## Frame counts

One cycle is 4 × 120 s plus one settle and four downloads: about **8.5–9.0 minutes**, or roughly
27 frames an hour.

| | |
|---|---|
| capture window | astronomical dark to moonrise — about 4 h in early October |
| frames | **≈ 100–110** |
| dither positions | ≈ 26 |
| **minimum** | **64 usable frames** — two disjoint stacks of 32, which is what lets the ladder pass 18 with a check beside it |

**Fewer than 64 usable frames is a session that did not run.** Say so and reshoot on the next clear
evening, rather than publishing a ladder that stops where session 06's did.

## Bias brackets

**20 at the start, 20 at the end**, gain 50, offset 15, shortest exposure. Same reason as session
06: `F_sky` and every star peak sit on the pedestal, and the offset state hops. The first bracket
also feeds gate 1, which wants a zero-light frame.

## Gates

**Gates 1 and 2 are blocking**: a failure ends the night.

| gate | settles |
|---|---|
| 1 | white balance, from the pixels: `stats.value_step` is 16 on all four planes of a bias frame |
| 2 | the cooler reads −10 °C and has held it for 10 minutes |
| 3 | the rejection rule, fixed now: a frame is rejected if its sky mode departs from the night's median by more than 4.0 MADs — session 06's cloud test, unchanged |
| 4 | framing: plate-solved, ROIs where session 06 had them, flip already done |
| 5 | the first two dither cycles show three short gaps and one long one, each |

## Analysis rules

1. **CFA mosaic, RGGB sub-planes, never debayered.** As every session.
2. **Pedestal from the brackets**, offset state assigned before subtraction.
3. **A gap counts as an interruption** — refocus, cloud wait, restart — if it is over 3× the
   **median dither-frame gap**. Not 3× the night's median gap, as session 06 used: tonight three
   gaps in four are a bare download, so the night's median *is* the download, and the old rule
   would throw away every dither.
4. **Download** is the mean gap minus exposure over frames with no dither in front of them.
   **Settle** is the mean over dither frames, minus the download. **`t_dead`** is the mean over all
   frames, interruptions excluded. Published as means, never medians, with the cadence they were
   measured under. Which frames follow a dither is read from the gaps and checked against the
   cadence the ASIAIR was set to; a disagreement is reported, not smoothed.
5. **`η_comb`** exactly as `25` measured it — same rejection, normalisation, registration
   (`register.js`, each Bayer plane on its own), binning and ROI — so the only thing that differs
   is the cadence. Provenance records the cadence and the number of distinct dither positions.
6. **Star clipping** counted as `29` counted it, against 4095 and against `linear_to_at_least`,
   on stars detected tonight. Compared with session 06's cell B, never pooled with it.
7. **The comparison against session 06 is across setpoints** (−20 °C then, −10 °C now). At this
   gain and sky level the dark term is negligible at both, and that is stated beside every
   cross-night number rather than assumed silently.

## What lands where

| result | destination |
|---|---|
| download, settle and `t_dead` at one dither per 4 frames | `results/cadence_constants.json` |
| `η_comb` at one dither per 4 frames, N = 2 … 64 | `results/cadence_constants.json` |
| the decision rule's verdict | `results/cadence_constants.json` |
| star clipping per plane, beside session 06's cell B | `results/cadence_constants.json` |
| per-frame gap, dither flag, sky, temperature, rejection | `results/cadence_frames.csv` |

**`LEGACY.md` is not consumed.** Its only entry, L31, needs the light panel, not the sky.

The measuring notebook is expected at `35`, its explainer at `36`. Both purposes are agreed in
conversation before either is created.
