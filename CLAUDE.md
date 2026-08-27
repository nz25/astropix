# CLAUDE.md

How a session boots. Read these first, in this order:

1. `MISSION.md` — what we are optimising and how we know we succeeded
2. `DECISIONS.md` — what was already decided, and what was rejected and why
3. `FINDINGS.md` — what we have measured about this rig so far
4. `results/` — the numbers themselves, with provenance
5. `LEGACY.md` — claims inherited from the retired attempts, none of them verified here.
   A **queue that exists to be emptied**, not a fifth permanent document: each entry is checked
   when the build step that needs it arrives, moved to its destination, and deleted. When it is
   empty the file goes and this repo is back to four Markdown files (D38).
   **Scan it whenever a build step or a notebook begins** — entries are grouped by the step that
   consumes them, and each carries a `Consumed by` line saying when it is due. Reading L01 before
   the first bench frame is the difference between a measurement and a silently corrupted one.

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
- **Two data sources, and only one of them owes us anything.** `Z:` holds ~15,000 historic
  frames shot across a year of ordinary imaging, before this project or any of its conventions
  existed: mixed setpoints, mixed gains, labels that do not always match the pixels. That is a
  **test corpus**, not a controlled dataset, and it is not expected to comply with anything here.
  Frames captured *for* this project — bench runs and deliberate on-sky tests — are shot to a
  protocol and land in `data/`.
- **If archive data or a classifier verdict looks unreliable, reshoot.** Reasoning around
  suspect frames costs more than re-taking them and leaves a number nobody can defend.
- **The archive is frozen while an analysis is producing numbers for `results/`.** Refresh the
  index between runs, never during. New frames land in `raw\_inbox\`, not in the archive.
- **If something cannot be done properly, say so and state the fallback.** Never substitute a
  mismatched dark, flat or constant silently.
- **A measurement must name the model coefficient it pins down.** If a sweep does not feed a term
  in the SNR equation, we do not run it.

## How work is recorded

These are rules, not conventions. The previous two attempts at this project died because
work outran the record of it, and the record is the only thing that survives a restart.

- **Reusable code lives in the `astropix/` package.** If a function will be called twice, it
  belongs in a module with a test. One-off analysis belongs in a notebook and stays there.
- **The library does one frame; the notebook does the loop.** `astropix` reads a frame, measures
  it, and describes it. Walking directories, deciding what to re-read, checkpointing, progress
  and assembling a table are *orchestration*, and they belong in the notebook that does them,
  where they can be read and changed without touching the library. What must never move into a
  notebook is physics: a measurement, a threshold, a correction. If a notebook cell starts
  deciding what a number *means*, the meaning is in the wrong place.
- **A build step opens by harvesting its `LEGACY` entries, and closes by deleting them.** Before
  writing the code, read what the retired attempts claimed about it and decide which claims this
  step will check. Afterwards, each verified entry moves to its destination and leaves `LEGACY`.
  A step that ends with its entries still queued has not finished.
- **Every notebook has a purpose, agreed before it is created.** A numbered notebook opens by
  saying what it is for and what it is not for, and that purpose is agreed in conversation
  first. A notebook nobody asked for is scope growth with a table of contents. The purpose is
  also the context that stops later readers misreading the data — see `01` below.
- **Nothing appears in `results/` except through a notebook.** Every file there is written by a
  cell in a numbered notebook, so the route from frames to a published number is readable end to
  end. Asserted by `tests/test_record.py`, which reads the notebook JSON and needs neither Z: nor
  an execution.

The bar is *a cell writes it*, not *it byte-reproduces*: re-running an acquisition correctly
yields a **new** snapshot, and demanding byte equality would forbid the artifacts that cost hours
to make.

Notebook purposes, as agreed:

| notebook | exists to |
|---|---|
| `01_frame_index` | index the historic frames on `Z:` — material of varied reliability, useful as **test data** for exercising code against real pixels, and as the route into the NGC 7000 exposure-ladder set |

## Library budget

Six modules — `fits.py`, `spatial.py`, `stats.py`, `model.py`, `asi.py`, `pixinsight.py` — and
roughly 1000 lines total until the model passes its validation gate. A seventh module, or
crossing the budget, is a conversation, not a commit. Notebooks are the workspace and the
narrative; the library is only the distilled residue; `results/` is the record of truth.

**Two invariants keep the first three apart.** *Only `spatial.py` and `stats.py` touch pixel
arrays* — `fits.py` moves bytes and never interprets a value. And *nothing in the package
loops over frames*: every function here takes one frame, or one array, and returns. `spatial.py`
asks *where* things are: the Bayer lattice, bright-pixel connectivity, later vignetting and
source detection. `stats.py` asks *how much* they vary, and carries the frame verdict those
numbers support. The dependency chain is one-way: `fits.py` → `stats.py` → `spatial.py`.

`tests/` does not count against either limit — it carries no physics, nothing imports it, and a
budget that discourages tests is a budget working against itself. It mirrors the package: one
`test_<module>.py` per library module.

## Layout

```
astropix/     one frame at a time -- fits (bytes) | spatial (where) | stats (how much)
tests/        one test_<module>.py per library module; outside the budget
notebooks/    numbered, narrative, markdown + code
data/         gitignored; frames captured *for* this project (bench and tests)
protocols/    bench pre-flight and capture protocols; `bench-setup.md` is *run*, not just read
pjsr/         headless PixInsight scripts
results/      committed CSV (sweeps) and JSON (constants with provenance)
vendor/       third-party binaries, licence beside each
```

## Environment

- Python 3.14 venv. Verified to resolve: numpy 2.5.2, astropy 8.0.1, scipy 1.18.1,
  photutils 3.0.0, sep, jupyterlab 4.6.3, zwoasi 0.2.0.
- PixInsight: `C:\Program Files\PixInsight\bin\PixInsight.exe`, driven headless via PJSR.
- ZWO SDK: vendored at `vendor/zwo-asi-sdk/ASICamera2.dll` (v1.41.0.0, MIT), loaded with
  `zwoasi.init(...)` from `asi.py`. Full SDK at `C:\Users\denis\Documents\ASI SDK`.
- Historic archive (test corpus): `Z:\pix\_astro\raw\_by_type\{light,dark,flat,bias}` —
  15,102 frames, indexed in `results/frame_index.csv`.
  **C: has ~12 GB free.** Nothing bulky lands on C:.
- Retired attempts `astro/` and `learn_astro/` still exist on disk. **Their data is not
  used** (D39); their *claims* are in `LEGACY.md` as hypotheses to check.

## The rig

ZWO ASI585MC Pro (OSC, RGGB, 3840x2160, 2.9 um, 12-bit ADC stored bit-shifted into 16-bit FITS)
on a SharpStar SQA55 (263-264 mm, f/4.8), ZWO AM5N mount, ASIAIR Plus, ZWO EAF.
32 mm f/4 guide scope. No filters.

**Cooling: -10 C** for every bench run and for the model's first pass, which treats temperature
as fixed rather than as an axis. That is a project convention adopted *after* most of the
archive was shot, and a simplification to be revisited when the thermal term is explored, not a
property of the historic data (which also contains -20 C material).
