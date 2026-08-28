# Findings

My notes on what I have learned about this rig. Not a log — I overwrite this freely as my
understanding improves, and git keeps the old versions if I ever want them.

Nothing else in the repo cites this file, and nothing should. Rules live in `CLAUDE.md`, numbers
live in `results/` with their provenance, and the reasoning behind past choices lives in
`DECISIONS.md`. This is just what I want to remember.

Everything below is in **ADC counts**, the project's one unit.

Current source: `results/frame_index.csv`, snapshot `2026-08-28T10:58:06` — 15,102 archive
frames, 15,090 readable, 12 zero-byte.

---

## The 12-bit container is exact, and that closes a question

Every stored value is an exact multiple of 16, on all 15,090 readable frames — `mult16_frac` is
1.000000 at min, mean *and* max. Not "usually" or "on average". So the camera really does
digitise to 12 bits and shift left into a 16-bit file, dividing by 16 loses nothing, and header
`EGAIN` applies directly with no factor to remember.

Full scale is **4095**. The bias pedestal is **65 at gain 50** and **77 at gain 252** — and the
standard deviation of the pedestal across 520 bias frames is **exactly 0.0** at both gains. The
offset is digital: it is added after the ADC, so it does not vary at all.

## MAD cannot measure this camera's read noise

`sigma` in the index is a median absolute deviation, and MAD on quantised data can only return
multiples of 1.4826 counts — one quantiser step. Median `sigma` on a bias frame is **1.4826 at
both gains**, i.e. exactly the floor.

That is not a measurement of read noise. It means read noise lives *below* one ADC count and MAD
is the wrong instrument for it. The index's `sigma` is fine as a classifier feature and useless
as a noise number. The PTC needs a sigma-clipped std, not this.

## Whole-frame `std` measures colour balance, not noise

The index now carries a pooled whole-frame `std` alongside the per-plane `sig_*`. The ratio
between them, median across the archive:

| type | `std` / mean `sig_*` |
|---|---:|
| bias | 0.6 |
| dark | 1.2 |
| flat | **14.5** |
| light | **10.3** |

On a flat, the pooled number is roughly **15x** the actual per-plane spread — almost all of it is
the R-to-G offset, not noise. This is the mosaic rule made visible: debayering or pooling first
does not add a little error, it swamps the quantity by an order of magnitude.

## The cooler does not always reach setpoint

**2,132 of 14,856 frames (14%) sit more than 1 °C from what was commanded.** Worst case: flats
commanded −20 °C that read **+4.5 °C** — effectively uncooled.

| commanded | type | n off | achieved range |
|---|---|---:|---|
| −20 °C | flat | 253 | −18.5 … **+4.5** |
| −20 °C | light | 1,095 | −18.5 … −13.0 |
| −20 °C | dark | 362 | −18.5 … −10.5 |
| −20 °C | bias | 120 | −12.0 … −10.5 |
| −10 °C | flat | 302 | −8.5 … +4.0 |

The excursions cluster on summer nights (2026-07-12, 2026-08-11…16). −20 °C is simply
unreachable above roughly 15 °C ambient with a ~35 °C ΔT, and the camera delivers what it can
without complaining. **Match calibration by achieved temperature, never by setpoint.** And this
is the concrete reason −10 °C is the project's convention: it is reachable year-round.

At −10 °C, flats are the *only* type that ever missed by more than 1 °C — darks, lights and
biases all held it.

## The archive is a test corpus, with one designed dataset inside it

15,102 frames shot across a year of ordinary imaging, before this project existed. Mixed
setpoints, mixed gains, labels that do not always match the pixels. Useful for exercising code
against real pixels; not something to draw constants from.

The exception is **NGC 7000**: 2,002 lights shot as a deliberate 2 × 6 grid, both gains, six
sub-exposure lengths, total integration held constant on every rung. That is exactly the
comparison `SNR(T, t)` asks for, and it is temperature-consistent in a way nothing else here is.

Two things to remember about it, both of which cost me a wrong conclusion once:
- **Only 2025-08-19 has both gains.** Every other night is single-gain, and the two gains are
  otherwise a month apart, so any other cross-gain comparison confounds gain with sky.
- **301 frames in the folder are not part of the grid** — two unrelated sessions on 08-08 and
  08-09 at 2.4x to 5.1x the sky level. Included, they make the design look broken.

## The classifier's one open question

684 frames labelled `light` measure as `dark` — the only disagreement in the whole 4 × 4 table.
Two different situations sharing one symptom: 317 at gain 252 sitting *exactly* on the pedestal
(genuine darks shot under a Light subframe type), and 367 at gain 50 carrying real signal and
naming bright targets but showing no connected bright structure.

I have not settled which of the gain-50 group are mislabelled and which are lights the clump test
missed, and the two demand opposite responses. The check is cheap — open a dozen of each and look
at the whole frame instead of the sampled rows — and I have not done it.
