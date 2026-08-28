# ZWO's published curves for the ASI585MC Pro

Three charts, downloaded from ZWO's product pages on 2026-08-28, with the tables read off them.
ZWO's copyright; kept here as **hypotheses to reproduce**, which is the only status a vendor
number has in this project.

| file | source |
|---|---|
| `fullwell-gain-dynamicrange-readnoise-vs-gain.jpg` | `i.zwoastro.com/wp-content/uploads/2025/10/a19423fbe1fb11fe66cd7cfc5961973e.jpg` |
| `dark-current-vs-temperature.jpg` | `i.zwoastro.com/wp-content/uploads/2025/03/4260dd09a55926e21c848a1c4b17f407.jpg` |
| `quantum-efficiency-vs-wavelength.jpg` | `i.zwoastro.com/wp-content/uploads/2025/03/9c83877bc4a07c999895f9bfe470b8fb-1.jpg` |

**The tables are read off charts by eye.** Treat every value as ±5% at best, and worse on the
log axes: `fw_e` is plotted over two and a half decades, so a pixel of reading error is several
per cent. Nothing here carries provenance in the project's sense and nothing here may be
published as a measured constant.

## The gain chart, and what it implies

Four panels against gain in units of 0.1 dB, so gain 200 is 20 dB and a factor of ten in
amplification. Three internal relations hold across the whole chart, which is worth knowing
because it means the four panels are not four independent measurements — they are one
measurement and three derivations, and reproducing any two of them tests the same physics.

1. **`FW = 4096 × g`.** Full well is *defined* as the charge that fills the 12-bit ADC. At gain 0,
   9.8 e⁻/ADU × 4096 = 40,140 e⁻, against the annotated FW = 40K. At gain 200, 1.05 × 4096 =
   4300 against a plotted ~4000.
2. **`DR = log2(FW / R_e)`.** At gain 0: log2(40000/6.6) = 12.56 stops, plotted 12.55. At gain 200
   on the low-conversion-gain branch: log2(4000/4.0) = 9.97, plotted 10.0.
3. **`g(gain) = 9.8 × 10^(−gain/200)`.** The 0.1 dB unit, taken literally. It reproduces the
   plotted e⁻/ADU curve to within the reading error at every point.

So the chart contains exactly two independent curves: **`g(gain)`** and **`R_e(gain)`**. Everything
else follows.

### The one prediction session 01 can test

Session 01 measures read noise in **ADC counts**, because converting to electrons needs `g` and
`g` is what the photon transfer curve has not measured yet. The spec's read noise is in
electrons. The bridge is `R_adu = R_e / g`, and that is the `read_noise_adu_predicted` column of
`gain-curves.csv`:

| gain | 0 | 50 | 100 | 150 | 200 LCG | 200 HCG | 250 | 300 | 350 | 400 | 450 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R (ADC counts) | 0.67 | 0.98 | 1.47 | 2.27 | 3.81 | 1.05 | 1.64 | 3.00 | 5.59 | 8.50 | 10.83 |

This is a **joint** test of both spec curves, and that is its weakness: a disagreement cannot be
attributed to `g` or to `R_e` from session 01 alone. Session 03's PTC measures `g` independently
and turns the joint test into two separate ones.

Note the shape. In ADC counts read noise *rises* with gain on each branch, because the
amplification grows faster than the noise in electrons falls. The cliff at 200 is a **drop** in
both units, which is what makes it findable in session 01's data without knowing `g`.

### Two things the chart says that the project currently believes otherwise

- **ZWO's own chart annotates `HCG = 200`**, not 252. The project has been carrying "ZWO say 252,
  the retired attempt measured 200" as two competing predictions; on this evidence they are one
  prediction, and 252 needs a source or needs dropping. (252 is the ASI2600's HCG threshold,
  which is the likeliest origin of the confusion.) Session 01's fine grid, 180–220 in steps of 2,
  straddles 200 and settles it either way.
- **The chart stops at gain 450. This camera's gain control runs to 600.** Everything above 450
  is unspecified by the manufacturer, so a fifth of session 01's coarse sweep is measuring
  territory no vendor curve covers. That is not a problem — it is the part of the sweep that
  cannot be checked against anything, and the part most worth having.

## The dark current chart

Log₂ y-axis, doubling gridlines from 0.00098 to 0.5 e⁻/s/px, annotated `Y = 0.00107` at −20 °C.

**At the project's −10 °C setpoint the prediction is 0.00185 e⁻/s/px.** The doubling interval is
roughly 5.5–6 °C at the warm end and stretches to ~11 °C below −10, which is the usual signature
of a curve meeting a measurement floor rather than of physics changing.

For session 02, that predicts a 300 s dark accumulating 0.55 e⁻/px — about **1.0 ADC count** at
gain 252, where `g` ≈ 0.55 e⁻/ADU. Per pixel that is well under the read noise, which is why the
session bounds `D` rather than quoting it; across a 1 Mpx plane the *mean* is precise to far
better than that, which is why the bound can still be tight, and why pedestal drift over the
exposure is the thing that actually limits it.

## The QE chart

Peaks: green ≈ 90% at 520 nm, red ≈ 85% at 600 nm, blue ≈ 77% at 445 nm. All three converge near
50% at 810–830 nm and fall together to ~16% at 1000 nm, which is the silicon edge rather than
anything about the filters.

No table for this one, because reading a smooth three-curve plot at 25 nm intervals would
manufacture precision that is not in the image.

**No planned session validates this.** QE needs a calibrated spectral source; the bench has a
tablet screen. It is recorded here because the SNR model's `F_obj` term hides QE inside it, and
knowing which of the model's terms rest on unverified vendor numbers is part of knowing what the
model is worth.

## Validation matrix

| spec curve | pinned by | in what unit | verdict available |
|---|---|---|---|
| `HCG` threshold | session 01, fine grid 180–220 step 2 | gain units | **direct** — a cliff is a cliff in any unit |
| `R_e(gain)` | session 01 (+ session 03 for `g`) | ADC counts; electrons only after the PTC | **joint** with `g` until the PTC runs |
| `g(gain)` | session 03, photon transfer curve | e⁻/ADU | **direct**, once it runs |
| `FW(gain)` | session 03, via `FW = 4096 g` | e⁻ | **derived** — not an independent test |
| `DR(gain)` | sessions 01 + 03, via `log2(FW/R)` | stops | **derived** — not an independent test |
| dark current at −10 °C | session 02 | ADC counts/s; electrons after the PTC | **bound**, one temperature only |
| dark current vs temperature | nothing planned | — | the model treats temperature as fixed at −10 °C |
| QE(λ) | nothing planned | — | needs a calibrated spectral source |

The honest summary: **two of the eight rows get a direct verdict from the sessions now planned,
two more become direct once the PTC runs, one gets a bound, and three get nothing.** The three
that get nothing are exactly the ones the SNR model does not need as separate terms.
