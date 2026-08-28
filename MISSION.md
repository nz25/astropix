# Mission

Shoot the best possible astronomical images with the rig I own, under the skies I have,
by choosing capture settings from measured evidence rather than convention.

## The criterion

**SNR of faint extended signal in the integrated image**, measured in a fixed central ROI,
maximised subject to a **star-colour constraint** (no more than a chosen fraction of stars
clipping their cores, since a clipped core renders white and no processing recovers it).

The trade between the two is not resolved in advance. The deliverable is the **Pareto
curve** — for a given target and night, what SNR costs what in star colour — and the
choice of point on it is mine, per target.

## Free knobs

| Knob | Status |
|---|---|
| Sub-exposure length | free — primary axis |
| Gain | free — primary axis |
| Total integration time | free |
| Offset | fixed once, from the offset sweep |
| Cooling setpoint | fixed at **−10 °C** (measured as reachable and holdable) |
| Filter | none owned; a purchase only if the data argues for one |
| Scope | SQA55 f/4.8 imaging, 32 mm f/4 guiding — fixed |
| Target scheduling (altitude, moon) | phase 2 |

## Definition of done

Not a feeling — a passed test. **The model must correctly predict the SNR *ranking* of two
settings to within 10%, on at least three pairs, one of which straddles the HCG threshold.**

Ranking, not absolute SNR: absolute prediction would require a throughput budget (atmospheric
extinction, lens transmission, QE integrated over the sky spectrum) that cannot be measured on
this rig, and importing vendor curves would make the result vendor-driven rather than
data-driven. Ranking needs only terms we can measure ourselves.

## The model

Per pixel, per CFA channel, for one sub of length `t` at a given gain:

All pixel values here are **ADC counts** — the project's one unit, defined in `CLAUDE.md` (D41).

```
electrons        e     = (ADU − pedestal) · g(gain)      ADU = ADC counts
signal           S_obj = F_obj · t
noise variance   σ²    = (F_obj + F_sky + D(T)) · t  +  R(gain)²
                         └──────── shot noise ───────┘  └─ read ─┘

SNR_sub = F_obj·t / sqrt((F_obj + F_sky + D)·t + R²)
SNR_N   = η · sqrt(N) · SNR_sub          η = measured stacking efficiency, not assumed 1

with total time T = N·t:

SNR(T, t) = η · F_obj · sqrt(T) / sqrt(F_obj + F_sky + D + R²/t)
```

The whole sub-exposure question lives in the single term **R²/t**: lengthening a sub buys
SNR only until read noise is small against sky and thermal signal. The whole gain question
lives in **R(gain)** traded against the full well it costs.

Star-colour constraint, per channel:

```
pedestal + (F_star_peak + F_sky + D) · t / g(gain)  ≤  ADC ceiling
```

## Measured constants the model consumes

Every one carries provenance; none is taken from a spec sheet without checking.

| Constant | Source |
|---|---|
| `g(gain)` — e⁻ per **ADC count** | PTC sweep. Same unit as header `EGAIN`, which is therefore a direct check on the result rather than a trap (`CLAUDE.md`, D41 — supersedes the earlier file-units definition) |
| `R(gain)` — read noise, e⁻ | PTC sweep, re-measured at −10 °C |
| HCG threshold | dedicated fine gain sweep (ZWO's own figure moved 252 → ~200) |
| `D(T)` — dark current, e⁻/px/s | dark-current-vs-temperature sweep |
| `pedestal` — ADC counts | offset sweep |
| ADC ceiling / full well — ADC counts, ceiling ≤ 4095 | linearity sweep |
| `η` — stacking efficiency | measured from real stacks, not assumed √N |
| `F_sky` — sky flux | extracted per frame from the light frames themselves |

## Scope boundaries

**In:** the signal/noise model, camera and sensor characterisation, sub-exposure and gain
optimisation, the tooling to attribute a pixel's value to its sources.

**Out:** image processing and PixInsight technique (PixInsight is a referee and an
integration engine, not a subject); sharpness, focus, guiding and seeing; optics/vignetting
characterisation (phase 2); scheduling (phase 2); anything premised on gear I do not own.
