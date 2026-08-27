# CLAUDE.md

How a session boots. Read these first, in this order:

1. `MISSION.md` — what we are optimising and how we know we succeeded
2. `DECISIONS.md` — what was already decided, and what was rejected and why
3. `FINDINGS.md` — what we have measured about this rig so far
4. `results/` — the numbers themselves, with provenance

Do not re-litigate a decision in `DECISIONS.md`. If one turns out to be wrong, append a new
dated entry that supersedes it; never edit history.

## The user

Denis. Fluent in Python — do not explain the language. He wants the *signal-processing
reasoning* made explicit, and intuition over formalism. Two prior attempts at this project
(`astro/`, `learn_astro/`, both retired) died of scope growth. Scope discipline is a feature
request, not pedantry.

## Rules that are not negotiable

- **Noise statistics happen on the CFA mosaic, split into RGGB sub-planes. Never debayer first.**
  Interpolated pixels have correlated noise and silently invalidate every variance estimate.
- **Every measured constant carries provenance** — `value, unit, uncertainty, source_frames,
  measured_on, notebook`. The model refuses to run on constants that lack it.
- **Spec sheets are hypotheses, not facts.** Header `EGAIN` in particular is in 12-bit ADC units
  while the files are 16-bit (bit-shifted x16); using it directly inflates electron counts 16x.
- **Trust neither folder nor `IMAGETYP` for frame type — determine it from the pixels.** Dark
  folders mix gain and temperature inside one exposure folder, *and* some flats and darks were
  captured under a Light subframe type. Capture settings in the header (gain, offset, exposure,
  set-temp, achieved temp) are trusted; the type label is not.
- **The archive is frozen while an analysis is producing numbers for `results/`.** Refresh the
  index between runs, never during. New frames land in `raw\_inbox\`, not in the archive.
- **If something cannot be done properly, say so and state the fallback.** Never substitute a
  mismatched dark, flat or constant silently.
- **A measurement must name the model coefficient it pins down.** If a sweep does not feed a term
  in the SNR equation, we do not run it.

## Library budget

Six modules — `fits.py`, `cfa.py`, `stats.py`, `model.py`, `sweep.py`, `pixinsight.py` — and
roughly 1000 lines total until the model passes its validation gate. A seventh module, or
crossing the budget, is a conversation, not a commit. Notebooks are the workspace and the
narrative; the library is only the distilled residue; `results/` is the record of truth.

## Layout

```
astropix/     the library
notebooks/    numbered, narrative, markdown + code
data/         gitignored; bulk frames live on Z:
protocols/    capture protocols, written before each bench session
pjsr/         headless PixInsight scripts
results/      committed CSV (sweeps) and JSON (constants with provenance)
vendor/       third-party binaries, licence beside each (D35)
```

## Environment

- Python 3.14 venv. Verified to resolve: numpy 2.5.2, astropy 8.0.1, scipy 1.18.1,
  photutils 3.0.0, sep, jupyterlab 4.6.3, zwoasi 0.2.0.
- PixInsight: `C:\Program Files\PixInsight\bin\PixInsight.exe`, driven headless via PJSR.
- ZWO SDK: vendored at `vendor/zwo-asi-sdk/ASICamera2.dll` (v1.41.0.0, MIT), loaded with
  `zwoasi.init(...)`. Full SDK at `C:\Users\denis\Documents\ASI SDK` (D35).
- Frame archive: `Z:\pix\_astro\raw\_by_type\{light,dark,flat,bias}` — ~15,000 frames.
  **C: has ~12 GB free.** Nothing bulky lands on C:.
- Harvested from `learn_astro`: PTC sweep (61 gain steps), offset sweep, two linearity runs.

## The rig

ZWO ASI585MC Pro (OSC, RGGB, 3840x2160, 2.9 um, 12-bit ADC stored bit-shifted into 16-bit FITS)
on a SharpStar SQA55 (263-264 mm, f/4.8), ZWO AM5N mount, ASIAIR Plus, ZWO EAF.
32 mm f/4 guide scope. No filters. Cooling setpoint fixed at -10 C.
