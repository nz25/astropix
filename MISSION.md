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
| Sub-exposure length | free — primary axis, inside the bounds below |
| Gain | free — primary axis, but see *gain nearly cancels* under the model |
| Total integration time | free |
| Sub-exposure bounds | **constrained, not free**: an upper bound from what the mount tracks unguided-error-free and from cloud/gust loss risk, a lower bound from the sub count that outlier rejection and dithering need, and from `t_dead` |
| Offset | fixed once, from the offset sweep |
| Cooling setpoint | fixed at **−10 °C** (measured as reachable and holdable) |
| Filter | none owned; a purchase only if the data argues for one |
| Scope | SQA55 f/4.8 imaging, 32 mm f/4 guiding — fixed |
| Target scheduling (altitude, moon) | phase 2 |

## Definition of done

Not a feeling — a passed test. **The model must correctly predict the SNR *ranking* of two
settings to within 10%, on at least three pairs, one of which straddles the HCG threshold.**

**Each pair must be one the model predicts apart.** The separation predicted must exceed the
measured repeatability of the SNR estimator itself. A pair the model calls a tie is not a test —
it is a null result that every model passes, and the efficiency curve is flat enough over the
usual range that most pairs picked at random are ties.

Ranking, not absolute SNR: absolute prediction would require a throughput budget (atmospheric
extinction, lens transmission, QE integrated over the sky spectrum) that cannot be measured on
this rig, and importing vendor curves would make the result vendor-driven rather than
data-driven. Ranking needs only terms we can measure ourselves.

**Simplicity is a requirement, not a compromise.** A term earns its place by changing a
decision — the recommended `t`, the gain, or the shape of the Pareto curve. The target is the
smallest model that passes the test above, not the most complete one, and every simplification
is recorded with a bound on what it discards. A model that cannot be run approximately in my
head at the mount has failed even if its arithmetic is right.

## The model

Per pixel, per CFA channel, for one sub of length `t` at a given gain. All pixel values here are
**ADC counts** — the project's one unit, defined in `CLAUDE.md`.

```
electrons        e     = (ADU − pedestal) · g(gain)      ADU = ADC counts
signal           S_obj = F_obj · t
noise variance   σ²    = (F_obj + F_sky + D) · t  +  R(gain)²
                         └──────── shot noise ────┘  └─ read ─┘

SNR_sub = F_obj·t / sqrt((F_obj + F_sky + D)·t + R²)
SNR_N   = η_comb · sqrt(N) · SNR_sub

with T = N·t total integration and, since what is fixed is the night and not T,
with t_dead of overhead per sub (download, save, dither settle), N = T_night/(t + t_dead):

SNR(T_night, t) = η_comb · F_obj · sqrt(T_night) · sqrt(t / (t + t_dead))
                  / sqrt(F_obj + F_sky + D + R²/t)
```

`D` is dark current at the fixed −10 °C setpoint, so it is a constant in this pass. `η_comb` is
the **measured** loss of a real stack against the ideal `√N` — registration resampling, outlier
rejection, unequal weighting — and its provenance records the stack size and rejection settings
it was measured under, because it is not independent of them.

The whole sub-exposure question lives in **`R²/t`**: lengthening a sub buys SNR only until read
noise is small against sky and thermal signal. **`t_dead`** is what stops the optimum running
away to short subs once it is — at fixed wall clock, every sub costs its overhead whether or not
it collects anything.

Star-colour constraint, per channel:

```
pedestal + (F_star_peak + F_sky + D) · t / g(gain)  ≤  ceiling(gain)
```

`ceiling(gain)` is the **measured** saturation level, not 4095: whichever binds first, the ADC's
top code or the full well, and below either if linearity rolls off before it.

**The two constraints bind on different CFA planes, and the gap between them is the Pareto
curve.** Sky flux differs per plane, so `m = F_sky·t/R²` is per channel: the exposure floor is
set by the *dimmest* plane, the clipping ceiling by the *brightest*. A rule written for a mono
camera hides that.

### What the model assumes

It is a hypothesis with a definition of done, not a result. Four things in it are assumed rather
than measured, and each is one where failure changes the model's *shape*, not just a coefficient.
Named here with the sweep that settles each; this list is the live one, and it shrinks as bench
and sky data arrive.

- **No noise term that fails to scale with `t`.** σ² is shot plus read and nothing else — no
  fixed-pattern noise, no excess low-frequency noise, no per-plane dark structure. *Settled by
  the PTC sweep. An FPN term would weaken "`R²/t` is the whole question", since it survives
  lengthening the sub.*
- **Gain nearly cancels.** At fixed total time with `t` free to scale as `R²`, holding `m`
  constant makes `R²/t = F_sky/m` and read noise leaves the SNR entirely — gain then only
  relabels electrons as counts. This is why the definition of done demands a pair straddling
  HCG. *Settled by the gain sweep. If the mount or cloud risk caps `t` below the useful range,
  the substitution is blocked everywhere and gain is a live axis in general, not an exception.*
- **The dimmest and the brightest plane are different planes.** True of this sensor under these
  skies, or the Pareto gap between floor and ceiling closes and the per-plane framing buys
  nothing. *Settled by `F_sky` per plane, extracted from the lights themselves.*
- **The HCG threshold sits near gain 200.** ZWO's own figure, moved from 252 — a vendor number,
  and therefore a hypothesis (`CLAUDE.md`). *Settled by the fine gain sweep.*

## Measured constants the model consumes

Every one carries provenance; none is taken from a spec sheet without checking.

| Constant | Source |
|---|---|
| `g(gain)` — e⁻ per **ADC count** | PTC sweep. Same unit as header `EGAIN`, which is therefore a direct check on the result rather than a trap (`CLAUDE.md`) |
| `R(gain)` — read noise, e⁻ | PTC sweep, re-measured at −10 °C |
| HCG threshold | dedicated fine gain sweep (ZWO's own figure moved 252 → ~200) |
| `D(T)` — dark current, e⁻/px/s | dark-current-vs-temperature sweep |
| `pedestal` — ADC counts | offset sweep |
| `ceiling(gain)` / full well — ADC counts, ceiling ≤ 4095 | linearity sweep. Gain-dependent: the ADC top code and the well bind at different gains |
| `η_comb` — combination efficiency | measured from real stacks, not assumed √N. Provenance records stack size and rejection settings |
| `t_dead` — per-sub overhead, s | measured from frame timestamps: download, save and dither settle between subs |
| `F_sky` — sky flux, per CFA plane | extracted per frame from the light frames themselves, on the uncalibrated sub after pedestal subtraction |

## Scope boundaries

**In:** the signal/noise model, camera and sensor characterisation, sub-exposure and gain
optimisation, the tooling to attribute a pixel's value to its sources.

**Out:** image processing and PixInsight technique (PixInsight is a referee and an
integration engine, not a subject); sharpness, focus, guiding and seeing; optics/vignetting
characterisation (phase 2); scheduling (phase 2); anything premised on gear I do not own.
