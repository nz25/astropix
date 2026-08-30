# CLAUDE.md

How a session boots. Read these first, in this order:

1. `MISSION.md` — what we are optimising and how we know we succeeded
2. this file — how we work, and the rules that are not negotiable
3. `results/` — the numbers themselves, with provenance
4. `LEGACY.md` — claims inherited from the retired attempts, none of them verified here.
   A **queue that exists to be emptied**, not a fifth permanent document: each entry is checked
   when the build step that needs it arrives, moved to its destination, and deleted. When it is
   empty the file goes and this repo is back to four Markdown files.
   **Scan it whenever a build step or a notebook begins** — entries are grouped by the step that
   consumes them, and each carries a `Consumed by` line saying when it is due. Reading L14 before
   the dark session is the difference between an honest upper bound and a negative dark current.

## Document status

**`MISSION.md` and this file are canonical.** Every live rule is stated in one of them, in
full. Nothing you are required to follow lives behind a citation: if understanding a rule means
opening a second document, the rule is in the wrong place. If a rule turns out to be wrong,
change it *here* — deliberately, in conversation — never work around it, and never leave the
written rule and the working practice disagreeing.

The repo holds two other Markdown files, and neither is read for rules. They are named here
once, so a new session knows not to reach for them, and are cited from nowhere:

- **`DECISIONS.md` is the archive.** Append-only history of what changed and why: choices made,
  choices rejected, and the work that followed from them. It is a log, and the name is older
  than the habit. Open it when you want the reasoning *behind* a rule — never to find out what the
  rule is. Never edit it; a reversal is a new dated entry.
- **`FINDINGS.md` is Denis's.** His own notes on what he has learned. Do not cite it, do not
  treat it as authority, and do not write to it unless he asks. It is overwritten freely as his
  understanding improves; git is its log.

## The user

Denis. Fluent in Python — do not explain the language. He wants the *signal-processing
reasoning* made explicit, and intuition over formalism. **Scope discipline is a feature request,
not pedantry** — a measurement that pins down no term in the model is not a harmless extra, it
is the thing that stops the model ever being finished.

## Rules that are not negotiable

- **Noise statistics happen on the CFA mosaic, split into RGGB sub-planes. Never debayer first.**
  Interpolated pixels have correlated noise and silently invalidate every variance estimate.
- **"RAW" is not raw until the white balance is neutralised, and the proof is in the pixels.**
  The camera ships `WB_R = 55`, `WB_B = 75` — ratios against 50, applied to RAW16 *before the data
  reaches us*, multiplying red by 1.10 and blue by 1.50 in integer arithmetic. One sensor then
  looks like it has three gains, and the rounding perturbs the very noise being measured: read
  noise came out ~17% high at every gain in a retired attempt until this was found.
  `asi.neutralise_white_balance` runs unconditionally on open, and reading the control back only
  proves the *control* took. The evidence is `stats.value_step`: the modal step between adjacent
  distinct values must be **16 on all four planes**. Greens 16 with red at 17/18 and blue at 24 is
  the fingerprint of white balance still being applied — greens are untouched because WB is
  defined relative to green, which is what makes the pattern readable at all. **Nothing captured
  before that check passes is usable**, so it is gate 1 of every bench protocol (L01).
- **Every measured constant carries provenance** — `value, unit, uncertainty, source_frames,
  measured_on, notebook`. The model refuses to run on constants that lack it.
- **Spec sheets are hypotheses, not facts.** A vendor number is something to reproduce, never
  something to import. Where one is used as a prediction it is named as such.
  **ZWO's published curves for this camera are in `vendor/asi585specs/`** — three charts, the
  tables read off them by eye, and a README saying what each one does and does not let us check.
  That folder is the only place a vendor number may be quoted from, and quoting one means
  carrying its uncertainty: read off a plot, ±5% at best. **Read it before designing a sweep.**
  Its charts are not independent of each other — full well and dynamic range are *derived* from
  the gain and read-noise curves, so reproducing them tests nothing new — and its gain axis stops
  at 450 while this camera's gain control runs to 600.
- **One unit, and this is where it is defined: the ADC count.** The camera digitises to 12 bits
  and stores the value bit-shifted x16 into a 16-bit FITS container, so a stored value is 16x the
  number the ADC actually produced. Measured, not assumed: `mult16_frac` in
  `results/frame_index.csv` is that check, and it is run on the index rather than believed.
  **Everything this project measures, publishes or models is in ADC counts = stored / 16.** Full
  scale is **4095**, and header `EGAIN` — quoted per ADC count — applies directly, with no
  factor to remember. That is the whole point of the convention. Pedestals are not quoted
  here: they are published with provenance in `results/bias_constants.json`.
  Cite this rule; do not restate it.
  - `stats.to_adc` is the only conversion, and it raises rather than truncate.
  - `fits.read` returns stored values untouched: the check that licenses the conversion cannot be
    run on data that has already been converted.
  - **Stored units survive in exactly four places, all deliberate.** The raw reader and its
    `% 16` test; `mult16_frac` itself, which is the check and not a curiosity; L01's
    white-balance step-of-16 diagnostic in `protocols/bench-setup.md`, which goes vacuous in ADC
    counts; and the PixInsight boundary, where PI normalises by 65535, so a PI value converts as
    `v * 65535 >> 4` and **never** as `v * 4095` (L20 — 65535/16 is 4095.9375).
- **Two data sources, and only one of them owes us anything.**
  1. **`data/` — frames captured for this project.** Bench runs and deliberate on-sky tests, shot
     to a protocol in `protocols/` at -10 C. Gitignored. **Headers are trusted in full, type
     label included**, because the protocol is what set them. Every published constant comes from
     here.
  2. **`Z:\pix\_astro\raw\_by_type\{light,dark,flat,bias}` — the historic archive.** Frames
     from a year of ordinary imaging, shot before this project or any of its conventions existed.
     It is a **test corpus** — real pixels to exercise code against, and the route into the
     NGC 7000 exposure ladder — and **no published constant comes from it**. Mixed gains,
     exposures and setpoints (it holds -20 C material; the -10 C convention came later). Indexed
     in `results/frame_index.csv`.
     - **Trust neither folder nor `IMAGETYP` for frame type — determine it from the pixels.** Dark
       folders mix gain and temperature inside one exposure folder, *and* some flats and darks
       were captured under a Light subframe type. Capture settings (gain, offset, exposure,
       set-temp, achieved temp) are trusted; the type label is not. **How a type is decided is
       physics, so it lives with the code**: `stats.classify`'s docstring states the rule, why
       `light` is the deliberate fallback, and why the pedestal is passed in rather than
       hard-coded. Change it there, not here.
     - **`measured_type` is trustworthy on this corpus and is still not a warrant.** It agrees
       with every readable frame in the index whose type has been established by hand or by
       label. But it is a statement about *how much light arrived*, not about whether a frame
       is usable: a good number of its lights were shot through trees and cloud, and it is
       right about them and useless as a quality filter. Check `sat_frac`, `block_spread` and
       the plane medians before a selection becomes a dataset.
     - **Frozen while an analysis is producing numbers for `results/`** — refresh the index
       between runs, never during. New frames land in `raw\_inbox\`, not in the archive.
     - **If a frame or a verdict looks unreliable, reshoot.** Reasoning around suspect frames
       costs more than re-taking them and leaves a number nobody can defend.
- **If something cannot be done properly, say so and state the fallback.** Never substitute a
  mismatched dark, flat or constant silently.
- **A measurement must name the model coefficient it pins down.** If a sweep does not feed a term
  in the SNR equation, we do not run it.

## How work is recorded

These are rules, not conventions. **The record is the only thing that survives a restart**, and
work that outruns its record is work that has to be done again.

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
  also the context that stops later readers misreading the data, so it lives in that
  notebook's own opening cell and is copied nowhere else — two copies of a purpose become
  two purposes the moment one of them is edited.
- **Nothing appears in `results/` except through a notebook.** Every file there is written by a
  cell in a numbered notebook, so the route from frames to a published number is readable end to
  end. Asserted by `tests/test_record.py`, which reads the notebook JSON and needs neither Z: nor
  an execution.
- **Notebooks are committed with their outputs stripped.** Run them freely — a working copy full
  of outputs is what a notebook is *for* — but what git stores is source only: no `outputs`, no
  `execution_count`. A pasted table is not a record; the numbers belong in `results/`, where they
  carry provenance and a diff means something. There is no `nbstripout` filter configured, so
  this is a manual step before staging, and `tests/test_record.py` checks what `HEAD` actually
  holds rather than trusting anyone to remember.
- **Nothing is committed without Denis's review and explicit confirmation.** Finish the change,
  run the suite, say what changed and what it cost — then stop, and leave it in the working tree.
  A commit is a claim that the work was checked, and the only person who can make that claim is
  the one who checked it. Silence is not confirmation and neither is an approving remark about
  the work; the instruction to commit is. This covers everything that moves the record —
  `commit`, `push`, `amend`, `rebase`, `reset` — and it is not waived by a previous session
  having said yes, because approval is given for a change, not for a habit.

The bar is *a cell writes it*, not *it byte-reproduces*: re-running an acquisition correctly
yields a **new** snapshot, and demanding byte equality would forbid the artifacts that cost hours
to make.

- **A measuring notebook is followed by an explaining one.** The pair is the unit of work: the
  numbered notebook that talks to the camera and writes `results/` is written for someone
  *checking* it, and a second numbered notebook reads those published files back and explains
  what was done, why, and what it changed, for someone *deciding what to do next*. The explainer
  measures nothing and writes nothing; if it ever disagrees with `results/`, `results/` is right
  and the explainer is the bug. Splitting them is what lets the first stay dense and the second
  stay slow, instead of one notebook doing both badly. The statistics they lean on are explained
  once, in `00`, and cited from there rather than re-derived per session.

## Library budget

Six modules — `fits.py`, `spatial.py`, `stats.py`, `model.py`, `asi.py`, `pixinsight.py` — and
roughly 1000 lines total until the model passes its validation gate. A seventh module, or
crossing the budget, is a conversation, not a commit. Notebooks are the workspace and the
narrative; the library is only the distilled residue; `results/` is the record of truth.

**Two invariants keep the first three apart.** *Only `spatial.py` and `stats.py` touch pixel
arrays* — `fits.py` moves bytes and never interprets a value. And *nothing in the package
loops over frames*: every function here takes one frame, or one array, and returns. `spatial.py`
asks *where* things are: the Bayer lattice today, vignetting and source detection when something
needs them. `stats.py` asks *how much* they vary, and carries the frame verdict those
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
reference/    gitignored; third-party texts. A source of hypotheses to check, never of constants
vendor/       third-party binaries and vendor documents; licence or source beside each.
              asi585specs/ holds ZWO's published curves and the tables read off them
```

## Environment

- Python 3.14 venv. The packages and their versions are `requirements.txt`; it is the only
  place they are written down, because a version repeated here is a version that goes stale
  silently.
- PixInsight: `C:\Program Files\PixInsight\bin\PixInsight.exe`, driven headless via PJSR.
- ZWO SDK: vendored at `vendor/zwo-asi-sdk/ASICamera2.dll` (MIT), loaded with
  `zwoasi.init(...)` from `asi.py`.
- **C: is the working drive and it is tight.** Everything this project writes lives there —
  `data/`, caches, intermediates — inside a budget of a few tens of GB, so intermediates are
  disposable and a run cleans up after itself. **The archive stays on `Z:` and is never copied
  to C:.**

## The rig

ZWO ASI585MC Pro (OSC, RGGB, 3840x2160, 2.9 um, 12-bit ADC — see the units rule above)
on a SharpStar SQA55 (263-264 mm, f/4.8), ZWO AM5N mount, ASIAIR Plus, ZWO EAF.
32 mm f/4 guide scope. No filters.

**Cooling: -10 C** for every bench run and for the model's first pass, which treats temperature
as fixed rather than as an axis — a simplification to be revisited when the thermal term is
explored.
