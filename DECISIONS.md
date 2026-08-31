# Decisions

Append-only. Each entry: what we decided, why, and what we rejected. Never rewritten — a
decision that changes gets a new entry that supersedes the old one by date.

---

## 2026-08-27 — Founding session (grilling)

### D1. New repo, reduced scope
`astro/` and `learn_astro/` are retired. Both were structured as **courses** (Bracken chapter
order, lessons, web pages); this is a **decision engine**. The prior failure mode was stated
plainly: the code grew past what could be held in one head.
**Rejected:** continuing in `learn_astro`. Its data is harvested; its structure is not.

### D2. Success is a ranking test, not absolute SNR
The model must predict SNR *ratios* between settings within 10%, on three pairs, one straddling
the HCG threshold.
**Why:** absolute prediction needs an unmeasurable throughput budget (extinction, transmission,
QE over the sky spectrum); ranking survives calibration errors that break absolute accuracy.
**Rejected:** absolute SNR prediction (ambition, not gate); PixInsight-agreement-only.

### D3. Dual objective: faint-signal SNR, star colour as a Pareto trade
**Rejected:** a hard saturation veto (hides the cost); two-exposure HDR (phase 2 — the Pareto
curve will say whether it is needed); sharpness as an objective (dominated by focus, seeing and
guiding, none of which are the free knobs).

### D4. All noise statistics on the CFA mosaic, never debayered
Split RGGB into four sub-planes. Debayering interpolates, and interpolated pixels carry
correlated noise that invalidates every variance estimate downstream. **This is a rule.**

### D5. Stacking efficiency is measured, not assumed
Measure the real SNR-vs-N curve rather than assuming sqrt(N). The gap between ideal and measured
is itself a finding.
**Rejected:** analytic sqrt(N); full end-to-end drizzle/interpolation modelling (scope death).

### D6. PixInsight is integration engine and referee, on exactly three contracts
1. our sigma estimator vs. PI noise evaluation, same frame
2. our gain / read noise vs. PI's estimate, same bias+flat pairs
3. our predicted stacking noise reduction vs. `ImageIntegration`'s reported figure

Driven by **explicit PJSR chains run headless**, every parameter written by us and logged.
Measurement runs use **no output normalization or weighting**, plus a rejection-off baseline so
rejection's cost is measured rather than assumed.
**Rejected:** WBPP — it makes dozens of noise-relevant decisions invisibly.

### D7. NGC7000_tests is the primary validation dataset
`Z:\pix\_astro\raw\_by_type\light\NGC7000_tests` — 1701 frames, 2025-08-17 to 20, gain 252,
offset 15, −10 °C. Six exposure rungs (15/30/60/120/240/480 s) at **exactly 9600 s each**,
**fully interleaved across all four nights**. Equal-integration design: whichever rung stacks
best *is* the empirical optimum, and the model must predict that ranking.
Sky variation between nights is corrected using per-frame sky level — which forces the sky term
to be modelled properly rather than fitted away.
**Rejected:** equal-*count* subsetting to save disk; it would trivially favour long subs and
destroy the experiment.

### D8. Bulk data stays on Z:; C: is cleared first
C: has ~12 GB free; the ladder alone is 27 GB and its calibrated intermediates ~110 GB. Repo and
`results/` on C:, all frames and PixInsight intermediates on Z:. `astro/` and `learn_astro/`
(~11 GB) archive to Z: **after** harvesting their sweep data.
**Open:** an external SSD would materially speed up the PixInsight runs if one exists.

### D9. Calibration: darks and flats matched by header, no silent substitutes
Darks are foldered by exposure but **mixed by gain and temperature inside those folders** — the
`060` folder holds both gain 252 @ −10.0 °C and gain 50 @ −10.5 °C. Selection is by header
(gain 252, offset 15, −10 °C, matching exposure), never by folder. Flats for the ladder nights
exist: `flat/20250818|19|20`, gain 252, −10.5 °C.
**Known gaps:** the 15 s darks sampled are gain 50 only; the 240 s darks are gain 50 @ −20 °C.
Both re-shot if the header index confirms the gap. Fallback for a rung that cannot be matched:
pedestal subtraction only, **stated explicitly in the results, never substituted silently.**

### D10. Cooling fixed at −10 °C
The 2026 bias frames requested −20 °C and sat at −10.5 °C — a library calibrated to a label it
never met. −10 °C is measured as reachable and holdable year-round, which maximises calibration
library reuse.
**Rejected:** seasonal setpoints (library fragmentation); analytic dark scaling (fragile on CMOS,
since amp glow and hot pixels do not scale linearly).
**Expectation to test:** the thermal term is negligible against sky glow at f/4.8. If so, cooling
leaves the optimisation entirely and becomes a calibration-stability decision only. A negative
result here is a real result.

### D11. Gain axis: full on-sky grid, driven by an ASIAIR plan
4 gains (50, 100, 200, 252) × 4 exposures (30, 60, 120, 240 s), 1200 s per cell
(40/20/10/5 frames) ≈ 5.3 h of integration, 2–3 nights. **Interleaved across nights**, one
target held in a high-altitude window so altitude does not confound.
Gain and exposure are *separable* for background SNR — gain enters only through read noise and
full well — and *coupled* only through the star-saturation constraint, which is analytic. So the
grid is a falsification check, not a discovery instrument. A minimal 3-gain check was proposed on
cost grounds and withdrawn once ASIAIR planning made the full grid nearly free in human effort.

### D12. Camera control: sweep automation only
A thin driver over `zwoasi` pointed at `~/Documents/ASI SDK/lib/x64/ASICamera2.dll`. One entry
point: a list of `(gain, exposure_s, temperature_C, n_frames)` plans producing labelled FITS plus
a `manifest.json` recording **requested vs. achieved** for every value.
**Non-negotiable:** wait for the sensor to reach *and stabilise at* setpoint, with a timeout, and
record the achieved temperature — that is the documented failure in the existing data.
**Rejected:** ROI (changes noise statistics), binning (a different regime needing its own
characterisation), EAF control (sharpness is out of scope), live view, any general capture app.

### D13. Repo, documents and formats
Layout: `astropix/` (library) · `notebooks/` · `data/` · `protocols/` · `pjsr/` · `results/`.
Library budget: **~1000 lines until the model is validated**, six modules — `fits.py`, `cfa.py`,
`stats.py`, `model.py`, `sweep.py`, `pixinsight.py`. A seventh requires a conversation.
Git yes; remote `github.com/nz25/astropix` as offsite backup, added when convenient.
Tracked: code, notebooks with **outputs stripped**, `protocols/`, `pjsr/`, `results/`, the four
Markdown files. Ignored: `data/`, `venv/`, all FITS.

**Formats:** CSV for sweep results — many rows, one per condition, diffs readably in git, opens in
pandas or Excel. JSON for derived constants — a handful of scalars, each needing nested provenance,
which is exactly what CSV is bad at.

**Exactly four Markdown files, and no fifth without deleting one.** `learn_astro` carried eight
overlapping documents and the knowledge thinned until restarting beat reading:
- `MISSION.md` — scope and success criteria; rarely changes
- `DECISIONS.md` — this file; append-only
- `FINDINGS.md` — what we learned about *this* rig, in prose, each entry citing its `results/` file
- `CLAUDE.md` — how a new session boots

### D14. Every constant carries provenance, enforced in code
`{value, unit, uncertainty, source_frames, measured_on, notebook}`. The model refuses to run on a
constant that lacks provenance. Confidence, in practice, *is* traceability: in three months
neither of us should have to remember whether a number was measured or assumed.

### D15. Header index, folded into `fits.py`
One pass over ~15,000 frames on Z: writing a local CSV into `results/`. Header scanning over SMB
is slow enough to have timed out a 5-minute census during this session. Three consumers already
exist: dark/flat matching (D9), per-frame sky extraction (the model's sky term), and phase-2
scheduling. Folded into `fits.py` rather than becoming a seventh module, preserving D13's budget.

### D16. Build order — steps 1 to 4 need no hardware and no clear sky
1. `fits.py` (read, header ground truth) + `cfa.py` (RGGB plane split)
   - 1.5 header index over Z:
2. `stats.py` — robust sigma, validated against PixInsight (contract 1)
3. Re-analyse the harvested PTC / offset / linearity sweeps; **settle the e-/ADU unit question first**
4. `model.py`, built from measured constants
5. `pixinsight.py` plus the PJSR harness
6. `sweep.py` plus camera automation, for the gaps the old sweeps leave

### D17. Phase 2, explicitly deferred
Scheduling (altitude and moon), optics and vignetting characterisation, the two-exposure HDR
strategy, filter evaluation. Sky brightness is a **model input from day one**, so scheduling later
plugs into a slot rather than forcing a rewrite.

### D18. Frame type is determined from pixel statistics, not from `IMAGETYP`
Supersedes the "match by header" rule of D9 in its strong form. Some flats and darks in the
archive were captured under a Light subframe type, so **neither folder nor header is
authoritative**. The index classifies each frame from its own data — bias sits at the pedestal
with small spread; dark sits near the pedestal with a hot-pixel tail and scales with exposure;
flat has a high, smooth, structureless median; light has a low median plus point sources — then
records the measured type, the declared `IMAGETYP`, and a `type_agrees` flag.
Disagreements are a **finding and a cleanup work-list**, not a hazard. Header fields that describe
*capture settings* (gain, offset, exposure, set-temp, achieved temp) remain trusted; only the
frame-type label does not.

### D19. The index is incremental, and the archive freezes during a measurement run
Keyed by `(path, size, mtime)`. A refresh walks the tree — cheap — and reads headers only for new
or changed paths, since header reads over SMB are the expensive part. **Rows are never deleted:** a
vanished path is marked `missing`, so a result citing a file that later moved stays traceable.
Each snapshot records `indexed_at`; each file in `results/` records the snapshot it used.
**The archive is frozen while an analysis is producing numbers for `results/`** — refresh between
runs, never during — because an archive that moves mid-analysis produces irreproducible results.
Content hashing is **not** done wholesale (a 16 MB read per file over SMB), but **is** done for the
specific frames underpinning a published constant, with the hash stored in that constant's
provenance record.

### D20. Archive reorganisation is deferred and index-driven; ingest gets an inbox
The cleanup is an **output** of the index, not a prerequisite for it — re-sorting by the same
metadata that proved unreliable would only re-encode the error. It becomes a standing side project
runnable any time after build step 1.5, verifiable by re-indexing and confirming nothing changed
but paths. The index yields three cleanup products nearly free: frames whose measured type
disagrees with their label, calibration sets orphaned from any usable session, and near-duplicates.
**Do not delete calibration frames on "not useful" grounds until the model is validated.** A dark
set that looks pointless today may be the only evidence for a dark-current point at a temperature
that is hard to reproduce. Lights from a poor night are far safer to cull than any calibration frame.
Phase 1 is unaffected either way: it needs the six NGC7000 rungs, their matching darks and the
ladder-night flats, which the index locates regardless of where they sit.

**Ingest is manual, so new sessions land in a staging folder** (`raw\_inbox\`), indexed separately
and promoted into the archive only after classification and verification. This makes ingest the
single point where mislabeling is caught, and it makes the freeze rule trivial to honour — the
archive proper never changes mid-run; only the inbox grows.

### D21. Hardware: RAM before SSD; integrate rung by rung
The workstation is a Lenovo 20NU — **i3-8145U (2C/4T), 7.7 GB RAM, one 8 GB SO-DIMM in a
two-slot board (32 GB max), USB 3.1 xHCI (~450 MB/s practical port ceiling)**. A calibrated
32-bit float frame is 33.2 MB, so the ladder's peak working set is ~170–200 GB.

- **A 1 TB external SSD at ~1 GB/s is correctly sized** (5x headroom) and more than fast enough;
  the port caps below the drive anyway. Prioritise **sustained write and a DRAM cache (TLC, not
  QLC)** over headline speed — writing 56 GB exhausts any SLC cache, and a QLC drive then drops
  to ~100–150 MB/s, *slower than the network drive*, precisely when it matters.
- **RAM is the tighter constraint and the cheaper fix.** With 8 GB, PixInsight cannot hold a stack
  in memory and falls back to buffered row-chunk processing, multiplying I/O. A second 8 GB SO-DIMM
  costs a fraction of the SSD, relieves that pressure and enables dual-channel. Buy RAM first.
- **Integrate rung by rung, never the full 1701-frame ladder at once.** Each rung is a separate
  stack by design — comparing them *is* the experiment — so nothing is gained by a combined
  integration, and the memory pressure is avoidable. This rule holds regardless of hardware.
- The 2 TB "General UDisk" USB stick is **unproven and not to be used**: it failed to mount
  (partition present, volume reports size 0), and the generic controller string at that capacity
  matches the counterfeit-capacity pattern. Not to be trusted with frames until verified end to end
  with `h2testw` or `f3`.

Until the SSD arrives, bulk data and PixInsight intermediates stay on Z: as per D8. Phase 1
steps 1–4 are not I/O-bound — indexing reads headers, not pixels — so nothing is blocked.

---

## 2026-08-27 — Build session 1 (steps 1 and 1.5)

### D22. `sep` is dropped; `photutils` does source detection
`sep` ships no wheel for Python 3.14 and its C extension will not build here — the Visual
Studio toolchain is present but the Windows SDK headers are not (`io.h` missing), and the
maintained `sep-pjw` fork fails identically. `photutils` 3.0.0 is already a dependency, is pure
Python over numpy, and covers what the star-colour constraint needs: detection, centroids and
aperture photometry on a CFA sub-plane.
**Rejected:** installing the Windows SDK to build one package; pinning Python back to 3.11 —
the environment was verified against 3.14 and nothing else needs downgrading.
**Revisit if:** star photometry turns out to be throughput-bound, which on 1701 frames it may.

### D23. `astropix/test.py` sits outside the library budget
D13's ~1000-line, six-module budget governs *modelling* code — the part that has to be held in
one head. Tests are the opposite: they exist so that nothing has to be remembered. `test.py`
carries no physics, nothing imports it, and it runs entirely on synthetic frames written to a
temp directory, so it needs neither Z: nor clear sky and is safe to run while the archive is
frozen (D19). It runs as `python -m astropix.test` with no test framework, or under `pytest`.
**Rejected:** a `tests/` directory outside the package (a seventh top-level thing in the layout,
for no gain); depending on `pytest` (an install for a suite that is 18 asserts).

### D24. The robust sigma estimator is sigma-clipped std, not MAD
Superseding nothing — this is new evidence, and it changes the design of `stats.py` (step 2).

Measured: every stored value on this rig is an exact multiple of 16 (the 12-bit ADC bit-shifted
into a 16-bit file), so the quantiser step is 16 file-ADU. **MAD is itself an order statistic of
those quantised deviations, so it can only return multiples of 1.4826 x 16 = 23.72.** On
simulated Gaussian noise quantised to that grid, MAD errs by -100% at sigma = 0.25 steps
(it returns exactly zero), +48% at 1 step, -26% at 2 steps, and only settles inside 5% above
~8 steps. It never raises; it returns a plausible number.

Standard deviation is nearly immune (+4.0% at 1 step, +1.0% at 2, 0.0% above 4) because rounding
error averages over millions of pixels instead of being read off a single order statistic — but
std is not robust to stars and hot pixels, which is why MAD was reached for first.

So: **reject outliers with a percentile/MAD cut (robust, and only needs to be roughly right),
then take the standard deviation of the survivors.** Neither half suffices alone.

Consequence for existing numbers: the `sigma` column in `results/frame_index.csv` is MAD-based.
It is a valid *classification feature* and it is **not** a noise measurement. Every gain-50 frame
in the archive reports sigma = 23.72 exactly — one ADC step — which is the failure, not the
sensor. Nothing may feed that column to the PTC.
**Open, for step 3:** at gain 50 the read noise is around 0.5-1 quantiser step, where even
sigma-clipped std carries a 4-15% bias. The low-gain end of R(gain) needs the PTC variance fit,
not a single-frame sigma, and the residual bias must be quantified before that point is published.

### D25. Saturation is a quality flag, not a frame type — supersedes the `saturated` class of D24's session
Build session 1 introduced a fifth measured type, `saturated`, for frames clipped across the
sensor. Denis's read: those are almost certainly lights at the end of a planned session, taken
into morning twilight. Folding them into `light` is right, and for a better reason than
convenience — **saturation is orthogonal to what a frame is.** A blown flat and a dawn light are
both saturated and are not the same kind of frame; mixing a quality attribute into the type
taxonomy is a category error, and it would have made `measured_type` unable to answer the only
question it exists to answer.

Supporting evidence from the partial index (4,489 calibration frames):
- **Not one bias, dark or flat clips anywhere** — the largest `sat_frac` among them is 4e-6. In
  this archive, saturation occurs only in the lights.
- **Every flat is 1, 2 or 3 s** (1,792 frames, max 3.0 s), against 15-480 s for the ladder lights.

So exposure separates a blown flat from a dawn light, and `FLAT_MAX_EXPTIME = 5.0 s` is a
*measured* threshold with 5x margin, not a guess.

**Stated honestly, because it is the one branch that is not a measurement.** A fully clipped
frame has no pixel evidence left: level pins to full scale, sigma and clump go to zero. The
classifier therefore falls back on a capture setting, which D18 leaves trusted, and the code says
so at the branch. Saturation stays recoverable from the stored `sat_frac` column, which is what
downstream excludes on — nothing is lost by folding the type.

**Still to verify, once the lights are indexed:** that the clipped frames really do sit at the
*end* of their sessions in time order. The index carries `DATE-OBS`, so this is a check, not a
belief. If clipped frames turn up mid-session, the cause is a light leak or a passing car and the
attribution needs revisiting.

**Note on revising classifier thresholds at all:** every input `classify` takes is a stored column
in the index, so a threshold change can be replayed over the whole archive without re-reading a
frame (`reclassify()` in notebooks/01). Classification is cheap to revisit; the sampled read is not.

### D26. One rig, enforced in code — `_canon` is out of scope
`Z:\pix\_astro\raw\_by_type\_canon` holds frames from a retired camera. They are outside the
project by definition: every constant here is a property of *this* sensor, and a mixed archive
would let a foreign frame contribute to a PTC fit or a dark library without announcing itself.

Nothing has been contaminated — the index was pointed at the four type folders, which are
`_canon`'s siblings, and all 7,239 frames indexed so far report `INSTRUME = ZWO ASI585MC Pro`.
The risk is future, not past, and it is a sharp one: **`_canon` has its own
`bias/dark/flat/light` beneath it**, so pointing the walk one level higher at `_by_type` pulls
those frames into exactly the buckets where they would look plausible.

Two guards, deliberately redundant:
- `walk()` prunes `EXCLUDE_DIRS = ("_canon",)` from the traversal, so nothing under it is ever
  stat'd, let alone read. Cheap, and it is the one that saves the time.
- `refresh_index()` marks any frame whose `INSTRUME` is not `ZWO ASI585MC Pro` with
  `status = "other rig: <name>"`. This one survives a folder rename, and it is the backstop.

**Marked, not dropped.** A foreign frame that reaches the archive is a cleanup item (D20) and
silence would hide it; the row is still written, with its measured type intact, and simply
fenced off from `status == "ok"` — the same treatment a `missing` path gets under D19.
**Rejected:** deleting or moving `_canon` (not ours to reorganise, and D20 defers archive
reshuffling); trusting the folder layout alone, which is precisely the assumption D18 broke.

### D27. A bright frame is separated from a flat by exposure, not by level alone
The first classifier called any frame above `0.15 x full scale` a flat. The index found 1,052
frames that break it: lights at gain 252 and 120-480 s whose *sky* sits at 8,000-28,000 ADU
without clipping. Twilight and a flat panel look identical to a level cut.

`classify` now folds the bright and clipped cases into one branch — above the level cut **or**
clipped, the answer is `flat` if the exposure is <= `FLAT_MAX_EXPTIME` (5 s) and `light`
otherwise. This is the same reasoning as D25 and it is the one branch in the classifier that is
an *inference* rather than a measurement, which the code says at the branch.

**The lesson is bigger than the fix.** Those 1,052 frames were first reported as label
disagreements — as the archive being wrong. The archive was right; the measurement was wrong.
The tell was in the shape of the error: a genuine capture-time labelling fault is
*one-directional* (light-declared-as-dark, never the reverse), and 1,052 flats appearing only
inside light folders on long exposures at high gain is not that pattern. Before a disagreement
between our number and the world is written down as a finding about the world, the number gets
checked.

Replayed over the full index without re-reading a frame; 1,052 rows moved `flat` -> `light`, and
the label disagreement count fell from 1,736 to 684.

### D28. NGC7000_tests is a 2 x 6 grid, not a 6-rung ladder — supersedes D7's description
Measured from the index (`results/ladder_census.csv`), D7 is wrong on four counts. The dataset is
1,701 frames, all lights, but:

| | D7 says | measured |
|---|---|---|
| gain | 252 | **both 50 and 252** |
| integration per rung | 9600 s | **6720 s (gain 50), 6240 s (gain 252)** |
| nights | 2025-08-17 to 20 | 2025-08-17, 18, 19 and **2025-09-18** |
| interleaving | all four nights | **each gain spans only its own two nights** |

**What survives, and is better than promised.** Equal-integration holds *exactly* within each
gain (448x15 = 224x30 = 112x60 = 56x120 = 28x240 = 14x480 = 6720 s), and the six rungs are
interleaved across that gain's two nights. So the sub-exposure experiment is sound and there are
**two independent instances of it**, at opposite ends of the gain axis. The equal-integration
logic of D7 — whichever rung stacks best *is* the empirical optimum — holds within each gain.

**What is lost.** Gain is perfectly confounded with night: the two halves share no observing
night and are a month apart. Any cross-gain SNR comparison from this dataset measures the
weather. **The HCG-straddling pair required by the D2 validation gate cannot come from here** —
it must come from the fresh interleaved grid of D11, which this confirms as necessary rather
than merely prudent.

56 ladder frames (3.3%) are clipped, concentrated in the 15 s rung which runs latest into dawn;
they are excluded by `sat_frac`, not by re-typing.

### D29. Zero-byte frames are a delete list, not a mystery
All 12 unreadable files in the archive are exactly 0 bytes, and each is the last or near-last
frame of its run by sequence number (`dark/002` 0098-0100, `flat/20260320` 0059-0060,
`flat/20260813` 0055-0060, `light/M 106` 0096). Interrupted writes at session end.
Listed in `results/unreadable_frames.csv`. Safe to delete — no calibration set loses coverage —
but under D20 nothing is deleted from the archive until the model is validated, so they stay,
marked `unreadable: OSError` and fenced out of `status == "ok"`.

---

## 2026-08-27 — Build session 4 (reset)

### D30. The record is reset to the index, and three policies move to `CLAUDE.md`
Sessions 2 and 3 built `stats.py`, notebook 02 and a set of conventions on top of an index whose
own notebook could not rebuild it. Rather than patch that, the state is reset to the point the
archive index was the only artifact, and rebuilt from there. **Removed:** `astropix/stats.py`,
`notebooks/02`, every file in `results/`, the `FINDINGS` entries derived from them, and the
former D30–D36. All of it remains in git history at `9019bfe`; nothing is lost, it is
de-published.

**Kept deliberately:** D1–D29, because D24–D29 are the recorded reasons for thresholds still live
in `fits.py` — `FLAT_MAX_EXPTIME`, `EXCLUDE_DIRS`, saturation as a quality flag. Deleting the
reasoning while keeping the code is the failure this project exists to avoid. `vendor/` is kept
too; the DLL is real and its licence is beside it.

**Two kept entries now cite files that are gone.** D28 cites `results/ladder_census.csv` and
D29 cites `results/unreadable_frames.csv`. History is not edited, so the citations stand as
written; both files are at `9019bfe`, and both conclusions are re-derivable from a rebuilt index.
Treat them as claims awaiting a citation until a notebook regenerates the evidence.

**Three policies move out of here and into `CLAUDE.md`** ("How work is recorded"): reusable code
lives in the package, notebooks stay minimal and import the library, and nothing reaches
`results/` except through a notebook. They belong in the boot document because they govern every
session, not one. `DECISIONS` records *what was chosen and rejected*; `CLAUDE.md` records *how we
work*. The third is asserted by `tests/test_record.py`.

**Rejected:** rolling the git history back to `f09bdcc` and force-pushing. `CLAUDE.md` says never
edit history, the two commits are already on the remote, and the notebook 01 committed there had
no cell that writes the index at all — the rollback would have restored exactly the orphaned
state that prompted it.

### D31. `sweep.py` becomes `asi.py` — supersedes D13 and D16's module list
The sixth module is `asi.py`: the `zwoasi`/`ASICamera2.dll` wrapper and everything camera-facing.
D13 and D16 called it `sweep.py`, naming it after one use rather than after what it owns. Sweep
orchestration is a caller, and callers of a camera live in notebooks until they earn a module.

### D32. Tests live in `tests/`, outside the budget — supersedes D23
D23 kept the suite in `astropix/test.py` and exempted it from the line budget. It is now a
package, `tests/`, with one `test_<module>.py` per library module plus `test_record.py` for the
repo rule. `tests` rather than `test` because Python's standard library already owns `test`, and
shadowing it is the kind of failure that shows up somewhere unrelated. Run with `python -m tests`
or `pytest tests`; still no dependency beyond the library, so it runs on the capture machine
mid-session.

### D33. Build step 3 is not settled — the reordering is open
D16 step 3 is "re-analyse the harvested sweeps"; the alternative is bench capture first, with
`asi.py` and a setup notebook ahead of the PTC. Left open deliberately rather than decided in
passing. **What is known:** a re-analysis of the harvested 61-step sweep does settle the
`EGAIN` unit question — measured gain agreed with header `EGAIN` to 2% once the factor of 16 was
accounted for. That result is not carried forward here; it is in this session's transcript only,
and would have to be re-derived by whichever path is chosen.

### D34. `cfa.py` becomes `spatial.py`, and `fits.py` gives up pixel interpretation — supersedes D31's list
`fits.py` was two modules wearing one name: FITS reading and index maintenance on one side,
`frame_features`, `classify` and seven classification thresholds on the other. They shared a file
and nothing else. Split along one invariant, stated in `CLAUDE.md`:

> **Only `spatial.py` and `stats.py` touch pixel arrays.**

- **`spatial.py`** (was `cfa.py`) — *where* things are. `split`, `PLANES`, `bright_pixels`
  (public, was `fits._bright_pixel_stats`), `TAIL_K`. Later: vignetting, amp glow, source
  detection (D22). All of those are "where in the frame", and none of them belonged in a module
  named after a Bayer pattern.
- **`stats.py`** — *how much* things vary, plus the verdict those numbers support.
  `frame_features`, `classify`, the thresholds, `FULL_SCALE`.
- **`fits.py`** — files in, index rows out. 325 → 216 lines.

Dependency chain is one-way, `fits.py` → `stats.py` → `spatial.py`, which is what makes almost
every test runnable on a bare numpy array.

**`classify` sits in `stats.py` and returns a verdict, not a statistic.** Acknowledged wart; the
alternative was leaving it beside `scan_frame`. It reads a features *dict*, never pixels, so the
invariant holds either way — but it and `frame_features` are read together and change together
(D25 and D27 each moved both), and seven classification thresholds in a module called `fits` was
the smell that started this.

**`label_planes_by_flux` is deleted.** It guessed which sub-plane held red, from the data, as a
check on `BAYERPAT`. Nothing ever called it but its own two tests. **RGGB is a project constant**
— one rig, one sensor, one orientation — and `split` already raises on any other pattern, so the
guesser was a check on a guard that already existed. `bayerpat` remains a column in the index, so
if a frame from elsewhere ever appears the check is a groupby, not a module.

**Pure code motion: the index CSV is byte-identical either way.** Done before the scan only
because `results/` is empty and there is nothing to invalidate. Library: 417 lines of ~1000.

### D35. The library takes one frame; the notebook takes the loop — supersedes D15
`fits.py` owned `walk`, `load_index`, `_write_index` and a 70-line `refresh_index` that
walked the archive, decided what to re-read, checkpointed, marked vanished frames and printed
progress. None of that is about a FITS file. Orchestration moves to `notebooks/01`, and the
package keeps only what is true of a single frame:

| stays in `astropix` | moved to the notebook |
|---|---|
| `read`, `sample_blocks`, `capture_settings` | walking the four archive roots |
| `scan_frame` — every column the index records about one frame, `status` included | the loop, progress, checkpointing |
| `needs_rescan`, `stat_row` — the per-frame incremental decision | reading and writing the CSV |
| `sha256` | marking vanished frames `missing` |

`fits.py`: 216 → 138 lines. Library total 339 of ~1000. D15 folded the index into `fits.py` to
avoid a seventh module; the module was never the problem, the loop was.

**`needs_rescan` deliberately did not move.** Deciding whether *one* frame changed is per-frame
work, it is the single most consequential line in the scan — wrong one way and every refresh
re-reads 15,000 frames, wrong the other and a changed frame is never re-read — and it carries a
real trap: `mtime` round-trips through CSV, so the comparison is on `repr` strings rather than
floats. That belongs in tested code. Five tests cover it, including the CSV round-trip.

**Accepted cost.** The D19 guarantees that used to be asserted by
`test_index_round_trip_is_incremental_and_never_forgets` — rows never deleted, atomic write,
vanished frames marked — are now notebook code and untested. Mitigated, not solved, by a dry run
of the notebook against a synthetic archive covering a first pass, an unchanged re-run, a touched
frame and a deleted frame. If that loop grows a third behaviour, it has earned a test and should
come back into the package.

**`scan_frame` gained `status`.** The rig check (D26) was in `refresh_index`; it is per-frame, so
it belongs with the frame description. A foreign frame is still described and fenced, never
dropped.

### D36. The `Z:` archive is a test corpus; project data is shot for the purpose
The index made it tempting to read the archive as a rig that had failed a temperature policy —
14% of frames off setpoint, two setpoints, 684 labels disagreeing with their pixels. That
reading is wrong, and correcting it is the decision.

**Those frames predate this project and every convention in it.** They are ~15,000 frames from a
year of ordinary imaging: material of varied reliability, valuable as **test data** for
exercising code against real pixels, and as the route into the NGC 7000 exposure ladder. They
are not expected to comply with anything here, and non-compliance is not a finding about the
sensor.

**`CLAUDE.md`'s −10 °C is a bench convention and a modelling simplification**, adopted after most
of the archive was shot. The model's first pass treats temperature as fixed rather than as an
axis; that is a scope boundary to revisit when the thermal term is explored, not a claim about
historic data. The line said "fixed at −10 C" and now says which of those two things it means.

**Two sources, different expectations.** `Z:` is the corpus. `data/` holds frames captured *for*
this project — bench runs and deliberate on-sky tests, shot to a protocol. The layout entry for
`data/` said "bulk frames live on Z:", which had it backwards.

**And a preference, stated so it is not re-argued each time: reshoot rather than reason around
suspect data.** Where an archive subset or a classifier verdict looks unreliable, re-taking the
frames costs less than the argument and leaves a number that can be defended. This is why the
684 disagreements are recorded in `FINDINGS` as an open observation rather than resolved by
inference.

### D37. Every notebook has an agreed purpose before it exists
Added to `CLAUDE.md` under "How work is recorded", alongside the three rules already there.

A numbered notebook opens by saying what it is for and what it is not for, and that purpose is
agreed in conversation before the notebook is written. Two reasons, and the second is the one
that prompted this:

1. **A notebook nobody asked for is scope growth with a table of contents.** Two prior attempts
   at this project died that way.
2. **The purpose is the context that stops a later reader misreading the data.** Without
   "`01` indexes historic frames of varied reliability, for testing", the temperature spread in
   that index looks like a rig fault instead of a description of a corpus — which is precisely
   the mistake this session made before Denis corrected it.

`CLAUDE.md` carries the table of agreed purposes, so a session that reads its boot documents
knows what each notebook is claiming to be.

### D38. `LEGACY.md` — a fifth Markdown file that exists to be deleted
D13 allows exactly four Markdown files, "and no fifth without deleting one". This is the fifth,
and the exception is granted on one property no other document has: **its success condition is
its own deletion.**

D13 exists because `learn_astro` carried eight overlapping *permanent* documents and the
knowledge thinned until restarting beat reading. A queue with a termination condition has the
opposite failure mode — it either drains or visibly does not. So the exception is safe only while
draining stays mechanical, which is what the schema and the tests are for.

**What it holds.** 32 claims harvested from `astro/` and `learn_astro/`, none verified here. Five
required fields per entry: `Claim`, `Source`, `Consumed by`, `How to check`, `Lands in`. The last
two are what make it a work item rather than a note. Entries are grouped by the build step that
consumes them and cited by number from wherever they land, so the trail survives the deletion.

**What was excluded, deliberately:** anything MISSION scopes out (auto-STF, stretching); anything
already independently confirmed here (the 12-bit shift, MAD on quantised data — D24); and method
aphorisms, which are writing advice rather than hypotheses.

**Nothing in it is treated as fact.** It came from a codebase without this project's provenance
discipline, and `learn_astro/kb/measurements.md` explicitly retracts one of its own published
fits (L27). Every number is a prediction to falsify — which is the more useful form in any case:
if our own PTC independently reproduces their 9.382 e⁻/ADU, that is far stronger evidence than
inheriting the number would have been.

**Enforced by three tests** in `tests/test_record.py`: every entry carries all five fields, ids
are unique, and the file must not survive empty — the last one asserts the termination condition
rather than hoping for it.

**Rejected:** copying `kb/` wholesale into `vendor/` (2 547 lines of another project's docs,
mixing verified and unverified); citing the retired repos by path instead (they are retired and
may be deleted); and folding the entries into the existing four (they are neither decisions nor
findings until checked, and would distort both files).

### D39. No data is harvested from the retired projects — supersedes D33 and D16's step 3
Denis's call, 2026-08-27. The old sweeps are not re-analysed and their frames are not used. What
crosses over is **claims, not data**, and those go through `LEGACY.md` as hypotheses this project
verifies for itself (D38).

D33 left the ordering of build step 3 open between re-analysing the harvested sweeps and
capturing fresh. That question is now closed: there is nothing to re-analyse. D16's step 3,
"re-analyse the harvested PTC / offset / linearity sweeps", is void, and every constant in
MISSION's table comes from a measurement this project makes.

**The reason is the one the whole record discipline rests on.** A number inherited from a
codebase without this project's provenance rules cannot carry `{value, unit, uncertainty,
source_frames, measured_on, notebook}` (D14), so it could never enter the model anyway. Held as
a *prediction* instead it is worth more: an independent measurement that lands on 9.382 e⁻/ADU
is far stronger evidence than the number would have been on its own.

**The cost, stated plainly: D16's promise that "steps 1 to 4 need no hardware" no longer holds.**
`asi.py` and a working bench become prerequisites for `model.py` rather than build step 6. The
"no clear sky" half survives — the PTC, dark current, linearity and offset are all desk
measurements with the camera on a table.

**Consequence for `results/`:** it stays empty of constants until the bench runs. `frame_index.csv`
is the only artifact, and it indexes a test corpus rather than measuring the sensor (D36).

### D40. `protocols/` opens, and its items cite `LEGACY` rather than restating it
`protocols/bench-setup.md` is the first file in a folder D13 allocated and nothing had used. It
is a **pre-flight to be run**, not a document to be read: an ordered sequence of actions before
the first frame of any bench session.

**Each item cites the `LEGACY` entry that justifies it instead of repeating the reasoning.** That
keeps a claim in exactly one place while it is unverified — writing L01's white-balance argument
into both files is the duplication D13 exists to prevent. As an entry is verified and harvested
out of `LEGACY`, the action stays and its citation is replaced by the destination it landed in.
The protocol is therefore useful immediately, before any of it is confirmed.

**Item 0 is ours, not inherited: run the iPad for ten minutes before the first frame.** It is a
precaution against an untested hypothesis — LED backlights dim as they warm, which fits the
timescale of L31's unexplained 1.79% instability at gain 100 and survives the settling check the
retired project ran. It costs ten minutes of a session lasting hours.

**And it carries its own removal condition**, which is the part worth keeping: *if the L31
stability trace shows a flat line from cold, delete item 0.* A precaution whose reason has been
falsified is a ritual, and rituals are how a protocol grows until nobody reads it.

**Rejected:** adding the warm-up to `LEGACY.md`. That file holds claims *inherited* from the
retired attempts; putting our own ideas in it blurs what it is and breaks the story that it
empties itself.

### D41. One unit for the whole project: the ADC count — supersedes MISSION's file-units `g(gain)`
The camera digitises to 12 bits and stores the value bit-shifted ×16 into a 16-bit FITS
container. That has been true since the first frame; what changes here is that we stop
*compensating* for it at every use site and instead convert once, at the edge.

**Everything this project measures, publishes or models is in ADC counts = stored / 16.** Full
scale 4095, gain-252 pedestal 77. The canonical statement lives in `CLAUDE.md` under "Rules that
are not negotiable", and every other document cites it rather than restating it — the same
discipline D40 applied to `protocols/` and `LEGACY`.

**The reason is a trap with a countdown on it.** Header `EGAIN` is quoted per ADC count, so in
file units it must be divided by 16 before use or electron counts inflate 16×. That rider was
repeated in seven places, and a fact that has to be remembered at every use site eventually is
not. In ADC counts `EGAIN` simply applies, and every external figure — L25's table, the ZWO
datasheet, SharpCap — is directly comparable instead of needing a conversion first.

**The conversion is exact, and that is not an assumption.** `mult16_frac` is 1.000000 at min,
mean and max across all 15,090 readable frames (`FINDINGS`, 2026-08-27), so `x >> 4` loses
nothing and stays integer. `stats.to_adc` performs it and **raises rather than truncates**: a
value with low bits set did not come from this camera's raw path, and shifting it away would turn
a file we do not understand into a plausible number. `frame_features` measures `mult16_frac` on
the stored values *first*, because reading the check off converted data would be circular.

**Four places keep stored units, deliberately**, and `CLAUDE.md` names them so they are not
"fixed" later: the raw reader `fits.read` and its `% 16` test; `mult16_frac` itself; L01's
white-balance step-of-16 diagnostic in `protocols/bench-setup.md`, which goes vacuous when the
step is 1; and the PixInsight boundary, where PI normalises by 65535 and the conversion is
therefore `v × 65535 >> 4`, never `v × 4095` (L20 — 65535/16 is 4095.9375).

**Consequences.** `stats.FULL_SCALE` becomes `ADC_FULL_SCALE = 4095`, and `sat_frac` tests
`>= 4095` exactly instead of the `65535 - 15` fudge that existed only because 65535 is
unreachable. `FLAT_MIN_LEVEL` is a *fraction* of full scale and so needs no change. The
bright-pixel floor `max(sig, 1.0)` now means one quantiser step rather than a sixteenth of one,
which is the correct semantics and will lower `tail_frac` on the 546 frames whose sub-plane MAD
is exactly zero — all saturated lights, typed by the `sat_frac` branch before clumping is
consulted, so no `measured_type` should move.

**D24 is not edited.** This file is append-only and its arithmetic (MAD lands on multiples of
1.4826 × 16 = 23.72) is correct in the units it was written in. In ADC counts the same statement
reads: MAD returns multiples of 1.4826, one quantiser step. The reasoning is untouched.

**Not yet done at the time of writing:** `results/frame_index.csv` is still in stored units and
must be rebuilt by re-running `notebooks/01` — with the existing CSV moved aside first, since
`needs_rescan` skips unchanged frames and would otherwise preserve the old numbers under a fresh
timestamp. `FINDINGS` and `notebooks/02` restate their figures afterwards. `CLAUDE.md` carries a
dated pending line until that lands.

**Rejected:** converting the index arithmetically instead of re-running it — the file would no
longer be what `stats.py` produces, which is exactly the traceability D33 exists to protect.
Also rejected: converting inside `fits.read`, which would destroy the evidence for the check that
licenses the conversion, and would make `fits.py` interpret a value.

---

## 2026-08-28 — Build session 5

### D42. The documents split three ways: canonical, archive, and Denis's — supersedes D13's four-file symmetry
D13 gave four Markdown files equal standing and `CLAUDE.md` a boot order that read all of them.
In practice that made every rule a two-hop lookup: `CLAUDE.md` stated a rule and cited `D41`,
which stated it again with the reasoning, and `FINDINGS` restated the numbers a third time. Three
copies of a rule is three chances for them to disagree, and no way to tell which one is live.

**The four files no longer have equal standing.**

- **`MISSION.md` and `CLAUDE.md` are canonical.** Every live rule is stated in one of them, in
  full. Nothing a session must follow sits behind a citation. They reference each other and
  `results/` and nothing else.
- **`DECISIONS.md` is the archive.** Still append-only, still the record of what was chosen and
  rejected and why. It is *history*, consulted for the reasoning behind a rule, never to find out
  what the rule is. It drops out of the boot order.
- **`FINDINGS.md` is Denis's** — see D43.

The direction of citation is now one-way and downhill: the archive cites the canonical documents,
the canonical documents cite `results/`, and `results/` cites the frames. Nothing cites upward.

**What moved to stay canonical.** The classifier's known blind spot — the 684 `light`-labelled
frames measuring as `dark`, and the warning that selecting `measured_type == "light"` may be
short by up to 367 frames — was only ever in `FINDINGS`. It changes how frames are selected, so
it is a rule, and it now sits in `CLAUDE.md` under the frame-type rule it qualifies. The x16
container fact now cites `results/frame_index.csv` directly instead of prose about it, which is
one link shorter and one interpretation fewer.

**`LEGACY`'s `Lands in` field is retargeted.** Ten entries named `FINDINGS` as their destination.
A measured number now lands in `results/` with provenance; a rule lands in `CLAUDE.md`; a choice
lands here. "Lands in prose" was never a real destination — it is how a number arrives without a
unit, an uncertainty or a source frame, which D14 exists to forbid.

**The four `FINDINGS` citations already in this file are not edited.** This file is append-only.
They stand as historical text; from here, entries cite `results/`.

**Enforced, not just agreed.** `tests/test_record.py` asserts that the canonical documents carry
no citation out (excepting the one "Document status" block that names the other two in order to
de-reference them), and that nothing in the repo cites `FINDINGS.md`.

**Rejected:** keeping bare `D41`-style tags in `CLAUDE.md` as provenance-only markers. A tag you
are not meant to follow is decoration, and it is how the two-hop lookup grows back. Also
rejected: deleting `DECISIONS.md` outright. The reasoning behind a live threshold is the thing
this project exists to preserve; de-referencing it is not the same as discarding it.

### D43. `FINDINGS.md` is Denis's, and it is not a log
It changes owner. It is his own notes on what he has learned from this rig — kept small, written
for him, and **overwritten freely** rather than appended to. The dated-entries-and-marked-
corrections contract it carried is dropped: git is its log, and a file that must never lose a
sentence grows until nobody reads it, which is exactly how `learn_astro` died.

**The consequence that matters: nothing may depend on it.** It is cited from nowhere, so it can
be rewritten or emptied without breaking anything. Anything load-bearing that lived there has
moved — to `CLAUDE.md` if it is a rule, to `results/` if it is a number, to here if it is a
choice. An agent does not write to it unless asked.

**Rejected:** leaving it as the shared findings log and merely relaxing the append-only rule. The
problem was never the rule; it was that a file Denis wants to keep small was also the place ten
`LEGACY` entries and two notebooks pointed at. Ownership without dereferencing would have lasted
one session.

### D44. The index is rebuilt in ADC counts, and D41's predictions are checked
D41 left the rebuild undone. It is done: `results/frame_index.csv`, 15,102 rows, 15,090 readable,
12 zero-byte, snapshot `2026-08-28T10:58:06`, with the previous CSV moved aside first so
`needs_rescan` could not preserve stale numbers under a fresh timestamp.

Compared row-by-row against the stored-unit index at `a7d81ab`:

- **The conversion is exact everywhere.** `old.level / new.level` is 16.0 at min, median *and*
  max across all 15,102 rows — not 16.0 on average, 16.0 on every frame.
- **No frame changed `measured_type`.** D41 predicted none should; zero did. The thresholds D24
  through D28 reasoned about are unaffected by the unit change, which is what licenses keeping
  their reasoning without re-deriving it.
- **One prediction did not hold, and it cost nothing.** D41 expected the bright-pixel floor
  `max(sig, 1.0)` — one quantiser step in counts rather than a sixteenth of one — to lower
  `tail_frac` on the frames whose sub-plane MAD is exactly zero. It did not: mean `tail_frac`
  moved from 0.00896739 to 0.00896736, and **no frame moved from a non-zero `tail_frac` to
  zero**. 546 frames have at least one sub-plane MAD of zero and 532 of them already read
  `tail_frac == 0` in both indices. The 520 with *all four* planes at zero are all lights with a
  median `sat_frac` of 1.0 — saturated frames, typed by the `sat_frac` branch before clumping is
  consulted, so the floor never reached them. Recorded because a prediction that turns out
  immaterial is still a prediction that was checked.

Six columns are new this run — `mean`, `median`, `min`, `max`, `std`, `sampled_px` — whole-frame
orientation for `notebooks/02`, read by nothing in `classify`. `std` there is pooled across the
CFA planes and so is dominated by channel balance rather than noise; `sig_*` is the uncontaminated
counterpart, and the two sit side by side so the gap D4 exists to prevent can be seen.

### D45. The controlled gain comparison is one night: 2025-08-19
Rescued from a `FINDINGS` correction footnote before that file changed owner (D43), because it is
a constraint on how the NGC 7000 set may be used, not an observation about it.

The set is a 2 x 6 grid (D28), and **verified exact at both gains** against the rebuilt index:
gain 50 runs 448/224/112/56/28/14 and gain 252 runs 416/208/104/52/26/13, every rung landing on
exactly 6 720 s and 6 240 s of integration respectively.

**But gain is confounded with night everywhere except one date.** Gain 252 ran 2025-08-17, 08-18
and 08-19; gain 50 ran 08-19, 08-20, 09-18 and 09-19 — a month apart but for the overlap. Only
**2025-08-19 carries both gains, each a complete ladder**, 221 frames at gain 252 and 219 at gain
50, same target, same sky. Any cross-gain comparison drawn from the set as a whole is comparing
observing conditions as much as gain. **Cross-gain comparisons come from 2025-08-19.**

**And the folder is not the dataset.** It also holds **301** frames from 2025-08-08 and 08-09 that
are not part of the grid — 300 at 60 s plus a single 120 s frame — at sky levels of 704 and 1 503
counts against the ladder's 281–295 at the same exposure, so moonlit, twilit or differently
framed. Included, they make the 60 s rung read 404 and the 120 s rung 53, and the design looks
broken when it is not. That single stray 120 s frame is the whole of the second discrepancy; the
earlier record described the strays as "300 frames, 60 s only" and missed it.

Sky is otherwise consistent within a gain: median level at the 15 s rung varies under 4% across
the gain-50 nights and under 5% across the gain-252 nights. All frames commanded −10 °C, all
achieved between −10.5 and −9.0 °C — the one temperature-consistent subset in the archive.

### D46. Two rules that were only ever habits: stripped notebooks, and no unreviewed commits
Both were already true in practice and neither was written anywhere a session would find it.

**Notebooks are committed with outputs stripped.** D13 has said so since the repo was laid out,
but D13 is the archive now, there is no `nbstripout` filter configured, and notebook 01 reached
the staging area with six cells of execution outputs during this session — caught by looking,
not by anything checking. The rule moves to `CLAUDE.md` where a live rule belongs, states plainly
that stripping is a manual step before staging, and `tests/test_record.py` now asserts it.

The test reads **`HEAD`, not the working tree**. A working copy full of outputs is the normal
state right after a run, and a suite that goes red every time `01` finishes is a suite that gets
ignored; what must never happen is that state reaching a commit. An `execution_count` fails on
its own, without outputs beside it — that is the half left behind when someone clears outputs by
hand, and a notebook carrying it looks clean in a diff while it is not.

**Nothing is committed without Denis's review and explicit confirmation.** The realistic failure
is not a commit from nowhere, it is reading "that looks right" as a green light, so the clause
says in as many words that silence is not confirmation and neither is an approving remark. It
covers `push`, `amend`, `rebase` and `reset`, because a rule naming only `commit` is satisfied by
an amend — which is worse, since an amend rewrites something already reviewed. And it is not
waived by a previous session having said yes: approval attaches to a change, not to a habit.

This is the first rule in `CLAUDE.md` that no test can assert, because it constrains behaviour
rather than an artifact. Recorded here so that limitation is deliberate rather than an oversight
someone later tries to "fix" with a hook.

**Rejected:** configuring a `filter.nbstripout` clean filter instead of the test. It would
prevent rather than catch, which is better — but it rewrites content silently on the way into
git, and this repo's habit is to assert rules visibly rather than hide them in machinery. Worth
revisiting if stripping is ever missed twice.

### D47. Notebook 02 re-executed against the ADC-count index, and what a unit change broke in it
D41 renamed `stats.FULL_SCALE` to `ADC_FULL_SCALE`. **`notebooks/02` referenced the old name and
had been broken since a7d81ab** — nothing noticed, because the test suite reads notebook JSON
for `results/` writers and never executes a cell. Re-running it was the first time anyone found
out.

Four more things were wrong in it, all the same species: a unit convention changed and the
notebook's *prose* was updated last session while its *arithmetic* was not.

- **The raw-pixel branch was still in stored units.** `F.sample_blocks` returns stored values
  deliberately (converting in the reader would destroy the evidence for the check that licenses
  converting), so 02 must convert, and did not. It now calls `ST.to_adc` once where the blocks
  arrive. The quantisation demonstration printed `MAD = 16 -> sigma = 23.72` directly under
  markdown asserting 1.4826, and the bright-pixel figure applied `max(sig, 1.0)` to stored values
  — a sixteenth of a quantiser step, which is the exact wrong-semantics D41 was written to fix.
- **A threshold silently loosened 16x.** `sigma < 100` meant 6.25 counts when it was written and
  100 counts once the index converted, turning a claim about 70% of frames into one about 98%.
  Replaced with a threshold expressed in rungs, which cannot rot the same way.
- **`0.9% of the frame` was wrong by 10x.** Six 32-row blocks of a 2160-row frame is 8.9%, and
  `sampled_px` now says so in the notebook rather than being left to arithmetic.
- **The `35x` figure does not exist in the data.** `stats.py`'s docstring and `01` both claimed
  the pooled `std` runs about 35x the per-plane `sig_*` on an archive flat. **No flat in the
  archive reaches 19x** — the distribution is a median of 14.5x, a maximum of 18.9x, and 02's own
  exemplar flat is 5.6x. Corrected in both places to the measured distribution. The claim was
  never checked against the index; it is retracted rather than adjusted.

**02 also gains the section it was missing.** `01` forward-referenced "see `02`, where `std` sits
next to `sig_*`" and 02 had no such content: the six summary columns D44 added were unexplained,
which contradicts 02's agreed purpose of explaining the measured columns. It now covers them, and
the ratio turns out to be worth having on its own — **bias and dark sit at 0.6-1.2x, where the
pooled and per-plane spreads agree because there is no colour, and everything with colour sits
above 5x.** That makes the ratio a light-leak detector: a "dark" reading 5 saw light.

**The lesson, and it is not about units.** Nothing in this repo executes a notebook. A notebook
can reference a symbol that no longer exists, print a number that contradicts the paragraph above
it, and pass every test — because the tests read notebooks as JSON, never as code. That is a real
gap in "the record is the only thing that survives a restart", and it is why 02 is now re-run
whenever the library's public names or units change, not merely re-read.

**Rejected for now:** executing notebooks in the test suite. It needs `Z:`, takes minutes, and
the suite is deliberately runnable on a copy that has neither the archive nor a checkout.
**Left open:** a cheap middle path — a test that parses `ST.`/`F.`/`S.` attribute references out
of the notebook JSON and asserts each one still exists in the package. That would have caught
`FULL_SCALE` in milliseconds with no frames and no kernel. Not written yet, and not written
without agreeing it first.

### D48. The off-diagonal cell resolved, and the frame-type rule scoped to the archive
*2026-08-28.*

**Two changes to the same rule.** D18 said frame type is determined from pixels, not from
`IMAGETYP`, and said it about every frame. It was only ever an argument about `Z:` — a year of
ordinary imaging shot before this project had conventions, where dark folders mix gain and
temperature and some darks carry a Light subframe type. Frames captured *for* this project land
in `data/` under a protocol that sets the subframe type deliberately. **Their declared type is
trusted.** Running a classifier on them is a diagnostic worth reaching for when a bench run looks
wrong, not a gate every frame must pass; a project that does not trust its own capture protocol
has a protocol problem, not a classification problem.

**The blind spot is resolved, and it was four populations wearing one number.** 684 frames
labelled `light` measured as `dark`. A dozen of each group opened whole:

- **200 genuine darks.** Gain 252, object `FOV`, sitting in `dark/002` and `dark/003` under a
  Light subframe type. Level exactly 77.000 on all 200 — the gain-252 pedestal — spread at the
  MAD floor, `block_spread` 0. The classifier was right.
- **117 genuine lights.** Gain 252, `Barnard142`, level 304-613 against that same pedestal of 77.
- **150 genuine lights.** Gain 50, level ≥ 85 against a pedestal of 65; whole-frame star
  clumping 0.86-0.96.
- **141 blanks.** Gain 50, level ≤ 75, spread at the MAD floor, no clumped bright pixels at full
  frame. Lights by intent that caught neither sky nor stars. `dark` is honest about the pixels,
  but at 4-10 counts above the gain-50 pedestal they are not usable as darks either — a third
  category the index has no word for.
- 76 more at level 75-85, mixed, whole-frame clumping averaging 0.30.

**The prior text was wrong about its own numbers**, and the correction matters more than the
count. It claimed all 317 gain-252 frames "sit exactly on the pedestal"; only 200 do, and the
other 117 are five times above it. It warned that darks "may be contaminated by up to 317" when
the 200 are the soundest darks in the group and the contamination is 141 frames at the *other*
gain. Reading the level column would have shown this at any point. The lesson is that a
disagreement between two labels is not a finding — the pixels are the finding, and nobody had
looked at them.

**The cause is a self-referential threshold.** `bright_pixels` is called at `med + 5·sigma` with
sigma being that frame's own MAD. Sky raises the MAD, which raises the star threshold, which
empties the tail; `tail_frac` goes to zero, `clump_frac` divides by nothing, and `classify` falls
through to its terminal `return "dark"`. **The brighter the sky, the more star-blind the test
becomes** — the failure lands hardest on the frames with the most signal, which is why the worst
cases name real targets. Re-measured with the threshold pinned to the dark MAD floor, whole-frame
clumping across the gain-50 level bins runs 0.00 → 0.02 → 0.30 → 0.86 → 0.84 → 0.96, and the
transition sits where the sky lifts off the pedestal.

**Not fixed here, deliberately.** The repair is a threshold that does not scale with the frame's
own sky, and that is physics in `stats.py` plus a rebuild of `results/frame_index.csv`. Both are
a build step, agreed before written. Until then the selection warning stands, corrected:
`measured_type == "light"` is short by 267 real lights and up to 76 more, and
`measured_type == "dark"` is contaminated by 141 blanks and not by the 200 `FOV` darks.

**Rejected:** classifying on `level` above a per-gain pedestal. It reads as the obvious fix and it
is unavailable — the pedestal is a measured constant this project has not measured yet (it is the
offset sweep, build step 3), and hard-coding 65 and 77 from the index would put an unprovenanced
constant inside the classifier that produced the index. **Left open:** whether the 141 blanks earn
a fourth measured type. They are neither light nor dark in any usable sense, and calling them
`dark` is what would put them in a master.

### D49. `LEGACY` loses its `Source` field, and CLAUDE.md stops arguing from the dead projects
*2026-08-28.*

`astro/` and `learn_astro/` have been deleted from disk. Three consequences, taken deliberately.

**`Source` is dropped from the `LEGACY` schema — five fields become four.** Its stated meaning
was "which repo and file, so it can be re-read", and there is nothing left to read. A field that
names an unreachable file is not provenance, it is decoration, and 32 entries carried one.
`tests/test_record.py` enforces the four-field schema and records why the fifth went. Four
fragments were folded into their claims first, because they were content wearing a provenance
label: the patch page's screen wake lock; the conflicting short `-r=` CLI form; the warning that
the PixInsight noise-estimator numbers cannot be reproduced because their frames are gone; and
one dead `How to check` that told a reader to run a script that no longer exists.

The header now says plainly that no claim can be re-read at its origin. **That is the real
change.** `LEGACY` was written assuming an entry that looked wrong could be checked against its
source; with that closed, the cost of a bad transcription goes from "go look" to "reshoot", and
a file whose whole job is to be believed provisionally has to say so at the top.

**`CLAUDE.md` stops justifying its rules by the retired projects.** Scope discipline and the
recording rules were each argued from "the previous two attempts died of it". A rule that leans
on a story about dead code is a rule a reader can discount once the code is gone; both now assert
the principle directly. The retired attempts survive in this file, which is where history
belongs.

**The archive is described once, and the description shrank.** `Z:` had been spread across a
frame-type rule, a "two data sources" rule, a reshoot rule, a freeze rule and an `Environment`
entry. All of it is now nested under the two-sources rule, in the order source-then-properties,
with the archive second — because *no published constant comes from it*, a sentence that was
nowhere and is the thing that makes the rest safe to condense. Nesting the frame-type rule under
the corpus it governs also removed the scope caveat added earlier the same day: the nesting says
it. `Environment` lost the duplicate archive entry, the ASI SDK path, and a free-space figure
that would have gone stale.

**Rejected:** keeping `Source` in a compressed form that preserved the date and the kind of note
(`gotchas` versus `measurements`). It is defensible — the date says how stale a claim is — but it
keeps a field alive for a fraction of its purpose, and `LEGACY` is a queue that exists to be
emptied, not a bibliography.

### D50. The classifier reads one number, and `light` becomes the fallback
*2026-08-28.*

**The rule.** A frame's type is decided by how far it sits above the pedestal for its gain.
Exposure settles bias before a pixel is read; a frame three orders of magnitude above the
pedestal is a panel at seconds and sky at minutes; what remains is `dark` if it sits on its
pedestal and `light` if it does not. `classify` reads exactly one feature, `level`, plus two
trusted inputs — the exposure time and the pedestal.

**Why the old rule failed, and it was not a tuning error.** D48 traced it: `bright_pixels` was
called at `med + 5·sigma` with sigma being the frame's own MAD, so sky raised the MAD, which
raised the star threshold, which emptied the tail. The brighter the sky, the more star-blind the
test became — the failure landed hardest on the frames with the most signal. But the deeper
problem was that no repair to a star test could have worked: **141 of the misclassified frames
have no stars in them at all.** Denis opened them; they are lights shot through trees and cloud,
on four nights, in five contiguous runs, each one a session where the sky went away and came
back. A discriminator that requires stars cannot type a frame that has none.

**The evidence.** Against a hand-established truth for all 15,090 readable frames, `level` minus
the pedestal separates with **no overlap**: 2,177 darks reach at most pedestal + 1.00 counts,
10,465 lights start at pedestal + 1.75, flats start at + 983. `DARK_MAX_ABOVE_PEDESTAL = 1.5`
sits in the gap. Zero disagreements. 484 frames move from `dark` to `light`; the 200 `FOV` darks
D48 identified stay `dark`.

**`light` is the fallback, and that is the safety property.** The old classifier fell through to
`return "dark"`, so every failure of the star test drained into the one bucket where
contamination does real damage — a light in a dark master is subtracted from every science frame.
A dark wrongly called light is thrown out by registration. Inverting the default makes the
classifier fail toward the harmless direction.

**The pedestal is a parameter, not a constant, and this is what unblocked the rule.** D48
rejected classifying on level because the pedestal is unmeasured (the offset sweep is build
step 3) and hard-coding 65 and 77 from the index would put an unprovenanced constant inside the
code that produced it. Both objections dissolve when the pedestal is *passed in*: `01` measures
it from bias frames, which are selected by **exposure time alone** — a trusted capture setting,
so no pixel argument is made and there is no circularity — and hands it to `classify`. It is
exact: 65.000 over 320 gain-50 bias frames, 77.000 over 200 at gain 252, standard deviation zero
in both. A gain with no bias frames behind it returns `unknown` rather than a guess, and the same
three thresholds hold at gains this archive does not contain. The header cannot supply it:
`OFFSET` is 15 across the whole archive at both gains.

**Domain of validity, stated in the docstring.** The dark branch holds only while dark current
sits below the quantiser floor. On this rig it does — 480 s darks sit on the pedestal to the
digit, identical to 3 s darks, at −20 and −10 °C, which is strong confirmation of **L14** (not
consumed here; its exit is the `D(T)` measurement). Warm the sensor far enough and darks climb
into the gap, and this function would need a per-exposure allowance.

**What the index lost.** `tail_frac`, `clump_frac`, `clump_h`, `clump_v` — the bright-pixel
family, which existed only to feed the retired test. `spatial.bright_pixels` and `TAIL_K` went
with them rather than sit uncalled, and `CLAUDE.md` no longer lists bright-pixel connectivity as
`spatial.py`'s remit; `spatial.py` is now `split` alone. Also dropped: `sig_r`, `sig_g1`,
`sig_g2`, `sig_b`. Per-plane spreads are still *computed* — D4 governs how a statistic is
computed, not how many columns it becomes — but only their mean is stored, as `sigma`, because
across 2,497 zero-light frames the four planes are identical to the digit in every one.

**What the index kept, and why each earned it.** `med_*`: the index's only colour, `level` is
exactly their mean, and 60 zero-light frames show plane disagreement — a light leak, findable
with a `sort_values`. `block_spread`: 111 zero-light frames carry structure they should not,
and 51 of those are invisible to `med_*`, so the two are not redundant. `sigma`: of 2,497
zero-light frames exactly one has left the MAD floor —
`dark/tests/480/Dark_480.0s_Bin1_20250908-230957_0001.fit`, at gain 252, which is *also* the
frame with the most structure and colour. One column, one catch, and the catch is real. `sigma`
is also what makes the classifier's domain-of-validity assumption auditable from the index.

**Rejected: chromaticity as the discriminator.** Darks are achromatic by construction — dark
current does not know which filter sits above the pixel — so `max(med_*) − min(med_*)` detects
transmitted light without mentioning stars *or* the pedestal. It works, and it is worse: 22 of
the 141 collide with 20 darks at a plane-spread of exactly 1.0 count, and no second feature
separates them. Level above the pedestal has no overlap at all. Kept as a *quality* query, which
is what the `med_*` columns are now for.

**Rejected: a fourth measured type for the 141.** D48 left it open. Denis opened the frames and
settled it: they are lights with an obstruction in frame, and `light` is what the classifier
should say. `measured_type` answers "how much light arrived", not "is this frame usable" — the
quality columns answer that, and conflating the two is what a fourth type would have done.

**Consequence for the record.** `results/frame_index.csv` must be deleted and `01` re-run; the
incremental rule keys on file identity, not on code identity, so a refresh would skip every row
over a stale schema.

---

## 2026-08-28 — Mission review

### D51. `MISSION.md`'s model section keeps the statement and sheds the derivation

**The problem.** `## The model` had grown to ~80 lines and was doing three jobs at once: stating
the SNR model, *deriving* consequences from it, and *arguing* for a decision already recorded in
the definition of done. Only the first is mission-level. Worse, the section read as settled —
same rhetorical register as `## The criterion`, which is a commitment that no measurement can
overturn — while containing claims that the PTC and gain sweeps can falsify outright.

**What stays in `MISSION.md`.** The equation, `η_comb`'s status as measured, the `R²/t` and
`t_dead` sentence, the star-colour inequality, and the per-plane point that the exposure floor
and the clipping ceiling bind on different CFA planes. Plus a new `### What the model assumes` —
four bullets, each naming the assumption and the sweep that settles it. That list is deliberately
*in* the canonical document and self-contained: an assumption a bench session must check is a
live thing, and D13's rule that nothing required lives behind a citation applies to it. The
argument for each assumption is here; the fact of it is there.

**What moved here: the sky-limited derivation.** MISSION carried the standard form as a
reassurance that this model reproduces the textbook rule:

```
SNR(T, t) / SNR(T, t→∞) = sqrt((F_obj + F_sky + D) / (F_obj + F_sky + D + R²/t))
                        = sqrt(m / (m+1))    when sky dominates, m = F_sky·t / R²
```

with the familiar anchors 3·R² → 87%, 10·R² → 95%. It is a *special case* of the model, obtained
by dropping `F_obj` and `D` from the denominator — never an input to it, and nothing consumes it.
It belongs in the model notebook where it can be plotted against our own denominator, not in the
spec. Its one load-bearing job — distinguishing this derived quantity from `η_comb`, which is
measured — survives as the word "measured" on `η_comb` in MISSION and in the constants table.

**What moved here: the three exceptions to gain cancellation.** MISSION listed where the
`R²/t = F_sky/m` substitution is blocked and gain therefore becomes a live axis:

1. `t` capped, by the mount or by cloud and gust loss — lower `R` is then not paid for by a
   longer sub, and it is worth real SNR;
2. the **HCG discontinuity**, where `R` drops without the full well shrinking in proportion, so
   the usual read-noise-for-well trade does not apply across it;
3. the star-colour constraint, which binds on full well and therefore on gain directly.

This is rationale for a decision already made — D2's ranking test requires a pair straddling HCG,
and (2) is why. Rationale is what this file is for. MISSION now states the requirement and the
cancellation that motivates it; the enumeration lives here.

**Rejected: moving the assumptions here too.** Denis asked for details *and* assumptions to move.
The details did. The assumptions did not, because this file is cited from nowhere and is opened
to find out *why* a rule is, never *what* it is. An assumption list that only exists in the
archive is invisible on the morning of the PTC sweep, which is the one morning it matters. Split
instead: fact in MISSION, argument here.

**Rejected: a fifth Markdown file for the provisional.** The document set distinguishes canonical,
archive and Denis's, with no slot for "true today, under test". A subsection with an honest
heading is cheaper than a file, and `LEGACY.md` — the only existing queue-that-empties — is
scoped to claims inherited from the retired attempts, which these are not.

**Consequence.** `MISSION.md` goes 148 → 135 lines; the model section proper goes ~80 → ~45, and
the 20 lines it gained back are the assumption list, which is new. No code, no constants and no
`results/` artifact is affected — nothing in the package had consumed the derivation.

---

## 2026-08-29 — Harvest of session 01's LEGACY entries

**Eleven entries leave the queue: L01–L08, L13, L26, L27.** Each had its consuming build step run
and its claim land somewhere durable, which is the whole condition for deletion. `LEGACY.md` goes
32 entries → 21. Numbers are never reused, so every citation already written keeps pointing at a
claim that can still be traced through this entry.

| entry | where it landed |
|---|---|
| L01 white balance on RAW16 | `CLAUDE.md` non-negotiable rule (new, below), `asi.neutralise_white_balance`, `stats.value_step`, `bench-setup.md` §2, gate 1 of `01-bias-sweep.md` |
| L02 SDK vs driver, ASIAIR holds the camera | `bench-setup.md` §1, and the two-cause message in `asi.open_camera` |
| L03 the three cooler lies | `asi.py` (`CoolPowerPerc`, `temperature` returning −1, the power-cycle rule), `bench-setup.md` |
| L04 cooling settles, and rings | `asi.cool_to` with its settle window, `bench-setup.md` |
| L05 gain 0–600, ROI must be even | `asi.py` validated range and the `set_roi` guard, with tests |
| L06 iPad as light source, three iOS settings | `bench-setup.md` §3 |
| L07 grey level exhausted below ~25% | `bench-setup.md` |
| L08 diffusers are not independent filters | `bench-setup.md`, as "measure, never extrapolate" |
| L13 clipping is a fraction | `results/bias_constants.json` — `offset_min_safe`, `offset_zero_clipping`, `project_offset` |
| L26 HCG threshold is 200 | `results/bias_constants.json` — `hcg_threshold_gain`, reproduced |
| L27 the pedestal has two branches | `results/bias_constants.json` — `pedestal_fit`, `pedestal_per_offset_unit` |

**L13's destination moved, deliberately.** The entry said `stats.py`, "as the saturation/clipping
test, with the threshold recorded". It landed in `results/` instead. The reason is that the thing
worth keeping turned out not to be a function: `zero_frac` is one line of arithmetic, and the
*judgement* — 0.1% clipped **and** at least 15 R of headroom above the floor — is a pair of
measured numbers with a bracketing argument behind them, which is a constant with provenance and
not a library predicate. Putting it in `stats.py` would have hard-coded a threshold the sweep had
just finished measuring.

**L31 is trimmed rather than deleted.** Its dark arm ran as session 01's drift block and came back
flat (−0.00133 ± 0.254 counts/min), so the camera is cleared; the backlight hypothesis needs arms
that need the light source. The entry now says so, and `bench-setup.md` item 0 survives on the
grounds it was written on.

**Rejected: deleting L10 as well.** Session 01 *used* its method — `R` from bias pairs, and
`read_noise_at_hcg` is the result — but the entry's `Consumed by` is the PTC ladder design, and
the second half of the claim (log-space the ladder, keep the fitted intercept as a cross-check)
has nothing to check it against until the PTC runs. Half a claim is not a harvest.

**One new rule in `CLAUDE.md`, which is L01's stated destination.** The white balance is stated as
a non-negotiable, with the pixel-level test rather than the control read-back, because "the
control took" is exactly the evidence that failed before. `CLAUDE.md`'s own instruction on reading
`LEGACY` used L01 as its worked example; it now uses L14, which is live and is the next session's.

---

## 2026-08-29 — The explainer pair, and notebooks `00` and `04`

**Denis's rule, adopted:** a measuring notebook is followed by an explaining one. The measuring
notebook talks to the camera and writes `results/`, and is written for someone checking it. The
explainer reads those published files back and is written for someone deciding what to do next.
It measures nothing, writes nothing, and if it disagrees with `results/` then `results/` is right
and the explainer is the bug. `CLAUDE.md` now states this under *How work is recorded*.

**Both were built rather than one.** Denis offered them as alternatives — an explainer per
session, *or* a single `00` bringing him up to speed on the statistics. They are not
alternatives: with an explainer per session, a shared `00` is what stops each one re-teaching
sigma, quadrature and standard error from scratch. `00` was written first so `04` could cite it.

- **`00_statistics`** — twelve ideas, in the order the work needs them, every one demonstrated on
  session 01's own frames. It requires `data/session01/frames/` and has **no simulated fallback**:
  fabricated pixels in a repository this careful about provenance is a habit bought cheaply.
- **`04_sweep_read`** — session 01 explained, in nine sections. `04_dark_bound` becomes
  **`05_dark_bound`**; nothing else referenced the old number.

**Three claims died on contact with the executed output**, which is the argument for executing an
explainer rather than reasoning about it:

1. **`R_mad` is not a robustness diagnostic at low gain — it is pinned to the quantisation grid.**
   `bias_sweep.csv` carries *exactly* 1.048356 at gains 0 through 100 and at 200, because
   `median(|d|)` on quantised data lands on the integer 1 every time, and
   1.4826 / sqrt(2) = 1.0484. The ratio `R_sd / R_mad` therefore runs 0.63 at gain 0 (MAD
   over-states) to 1.36 at gain 100 (MAD under-states) for reasons that have nothing to do with
   outliers. Above ~190 it means what the textbook says it means. `00` section 6 now says so.
2. **The branch-split residuals must be read as percentages.** In absolute counts the per-branch
   fit looks *worse* at its extreme — 16 counts against the single fit's 13 — because the
   pedestal itself spans 63 to 1035 and the largest residual lands where the pedestal is largest.
   As a fraction of the value being predicted, which is how a subtraction error actually
   propagates, it is 14.5% against 0.8% and 2.4%. The wrong denominator reverses the conclusion.
3. **Excluding gain 600 from the offset criterion does not prevent a contradiction, it prevents a
   wrong answer.** With gain 600 left in, offsets 45 and 50 still pass, so the criterion would
   have returned **45** — a number set by where telegraph pixels clear an arbitrary headroom line,
   wearing the label of an answer about clipping. That is worse than an obvious failure.

**Found, not fixed: `pedestal_drift_rate`'s `uncertainty` field is the wrong uncertainty.** It
carries 0.254, the scatter of the points about the fitted line. The uncertainty on the published
*slope* is 0.00277 counts/min — about ninety times smaller, because 450 points over 15 minutes
pin a line far better than any single point is known. The conclusion is unchanged and stronger:
slope over its own error is −0.48, under half an error bar, so the honest statement is a bound of
|rate| < 0.0055 counts/min. The published field is conservative rather than wrong, but it answers
a different question from the one an `uncertainty` field is asked. Left for Denis to decide, since
changing it means re-running `03` and reissuing a constant.

## 2026-08-30 — `00` is rebuilt to a slow build-up, and section 0 becomes physics

Denis asked why read noise "cannot be averaged away", and the answer that satisfied him was
longer and slower than the notebook that was supposed to have already explained it. `00` was
written dense, for a reader who mostly knows this material and wants it pinned down. That is the
wrong reader: the notebook exists so a later session does not have to re-derive the vocabulary,
and a dense reference does not teach the thing it is being cited for.

**The rebuild rule is one sentence: every term is defined before it is used, and no section
leans on one that has not happened yet.** Nothing else about the notebook's purpose changed — it
still measures nothing, writes nothing, and introduces no threshold.

**Three choices, all Denis's, all deliberate:**

- **Section 0 is physics, and that widens the notebook's stated purpose.** The old header claimed
  "nothing here is specific to astronomy", which was already a slight fiction — every example is
  a bias frame from this camera. The chain from photodiode to FITS value now opens the notebook,
  because *where* an effect enters it is what makes the statistics that follow reasons rather
  than rules. `CLAUDE.md`'s purpose row is amended to say so, and to scope it: section 0 is the
  section that says what the gain multiplies and what it does not. It is not a sensor
  engineering text and must not grow into one.
- **Renumber freely, and fix the citations.** Variances-add moves from 4 to 3, because section 2
  was forward-referencing it — the exact defect the rebuild exists to remove. Two directions of
  spread moves from 3 to 4. Sections 5 to 12 keep their numbers, so `04`'s five citations of `00`
  needed two repointed, not five.
- **Delivered in passes, reviewable between them.** Pass 1 is the header, section 0 and sections
  1 to 4.

**The state this leaves, and it is not an accident.** Sections 5 to 12 are still in the old dense
voice, kept verbatim apart from one cross-reference the swap invalidated. **A future session
should not "fix" that inconsistency by compressing sections 0 to 4 to match** — the arrow points
the other way. Pass 2 rebuilds 5 to 12 in the pass 1 voice, and it is gated on Denis reading
sections 0 to 4 and giving a verdict on the pace, because that verdict governs eight sections and
is cheaper to get wrong at four. Sections 6 and 10 are the ones judged to need the most
expansion: both currently state a conclusion before the reader has the machinery to see it
coming.

**One finding came out of writing section 0, and it is a reading of published data, not a new
constant.** The pedestal is two things added at two different points in the chain. Fitting
`pedestal` against `offset` separately at each gain in `bias_sweep.csv` gives a slope of
**4.000 ADC counts per offset unit, unmoved in the fourth decimal across amplifications spanning
1x to 1000x**, while the fitted intercept climbs from 2.7 counts to 978. Since the gain stage
multiplies everything upstream of it and nothing downstream, the `Offset` control is applied
after the amplifier and the intercept is the analogue baseline that the gain does amplify.
`R_at_offset` is flat across offsets at every gain, so the addition carries no noise of its own —
which is what integer arithmetic looks like and what an analogue injection would not.

This does **not** license 4.000 as a constant. Nothing was written to `results/`, it carries no
provenance block, and it is a straight-line fit through eleven points that `03` already
published. What it licenses is section 11's model, `pedestal = A + B * amplification`, which now
has a measured reason for its shape instead of an assumed one. It also cannot separate "an
integer added after the ADC" from "a noiseless analogue offset at the ADC's own reference" —
both are downstream of the gain, which is all any later section needs.

## 2026-08-30 — `CLAUDE.md` sheds operational state, and the numbers that proved its rules land here

Adding a mid-rebuild note about notebook `00` to `CLAUDE.md`'s notebook table made a problem
visible that predated it: the canonical file had been accumulating things that change. Denis
asked for it stripped back to what is stable and canonical, and asked first whether `DECISIONS.md`
should join the boot sequence instead.

**It should not, and the reason is what the file is for.** `DECISIONS.md` is append-only and a
reversal is a new entry, so it deliberately holds *both sides* of every reversed decision with
nothing inside an entry marking it superseded. Booting it means loading retracted claims with no
marker saying which are live. It is also 1,238 lines against `CLAUDE.md`'s 242 and grows every
session, so the boot cost would scale with project age rather than staying flat. And it would
corrode the promise that makes `CLAUDE.md` worth trusting — *nothing you are required to follow
lives behind a citation* — because once the archive is read on boot, rules start migrating into
it. The archive stays out of the boot sequence.

**The test that decided each line, and the one to apply next time:**

> A line belongs in `CLAUDE.md` if a session must **follow** it. If a session only needs to
> **know** it, it belongs with the thing it describes. If it only **proves** a rule, it belongs
> here or in `results/`.

**What left `CLAUDE.md`, and where it went:**

- **The notebook purposes table.** All five notebooks already state their purpose in their own
  opening cell — the rule requires it. The table was a second copy of five things, and it had
  already drifted: it said "twelve ideas" while `00` said thirteen. The rule stays and now says
  the purpose lives in the notebook's opening cell and is copied nowhere else.
- **"How a frame's type is decided".** `stats.classify`'s docstring already carries the same
  argument in more detail, with the evidence. Deciding a frame's type is physics, and physics
  lives with the code. One line under the archive rule points at it.
- **The mid-rebuild note about `00`.** Moved into `00`'s own header cell, where it is visible to
  exactly the session that needs it and cannot drift from the thing it describes. A separate
  `STATE.md` in the `LEGACY.md` mould was considered and rejected as a mechanism built for n=1;
  if a second and third case appear, that is the signal to build it.
- **Package versions** (numpy 2.5.2, astropy 8.0.1, scipy 1.18.1, photutils 3.0.0, jupyterlab
  4.6.3, zwoasi 0.2.0, ZWO SDK v1.41.0.0). `requirements.txt` is now the only place they are
  written down. The disk-budget rule in the same section is canonical and stays.
- **Proof-numbers inside rules.** `mult16_frac` is 1.000000 at min, mean and max across all
  15,090 readable frames; the archive holds 15,102 frames; 141 of its lights were shot through
  trees and cloud. Each proved a rule rather than letting anyone follow one, and each tracks
  `results/frame_index.csv`, which is rebuilt. They are recorded here and the rules now point at
  the index instead of quoting it.

**One number was deliberately kept**, against the same test: *"read noise came out ~17% high at
every gain in a retired attempt until this was found"*, in the white-balance rule. It fails the
letter of the test and passes its purpose. Every number removed above tracks an artifact that
gets rebuilt and can therefore go stale; this one is the frozen outcome of a project that no
longer exists, so it cannot drift — and it is the consequence that makes gate 1 read as
non-negotiable rather than fussy. **Stale-risk, not word count, is what the strip was for.**

**Raised separately, then checked and resolved: *"the gain-252 pedestal is 77"* leaves the units
rule.** It was raised on the suspicion that it was stale, and that suspicion was wrong on both
counts. **The number is right**: session 01's own sweep gives gain 252 at offset 15 as 77.169 ADC
counts — the per-offset fit at that gain has slope exactly 4.0000 and intercept 17.169, and the
value is bracketed by measured rows at offsets 10 and 20. **And the gain is the right gain.** Two
different 252s were conflated: 252 is wrong as an *HCG threshold*, which is the L26 belief that
died and was replaced by 200, but 252 is the archive's dominant working gain — the 1,701 NGC 7000
frames were shot at it — and so it is the gain a classifier most often needs a pedestal for.

It goes anyway, for the reason the rest of this entry is about rather than for being wrong.
`results/bias_constants.json` publishes `pedestal_fit` and `pedestal_per_offset_unit`, so the
value is derivable from `results/` *with* provenance. A bare 77 in `CLAUDE.md` was a second,
uncredentialed copy of a published constant — the same pattern as the notebook table, which had
already drifted. The rule keeps full scale 4095, which is the anchor the convention actually
needs, and now says pedestals are published in `results/` and not quoted here.

**A real data gap surfaced while checking, and it is left open.** `bias_sweep.csv` has gain 252
at offsets 0, 5, 10, 20, 25, ... 50 and **no offset-15 row**, with `R_sd` and `n_pairs` empty at
that gain throughout. The seven other offset-sweep gains all have an offset-15 row because they
are also in the 77-gain grid, which runs at offset 15; 252 is not in that grid — it steps by 10
through 250 and 260 — so its offset-15 cell had nothing to merge with. Nothing published depends
on it, and `00` section 0's table quietly shows seven gains rather than eight for this reason.
Worth a row when `03` is next re-run, not worth a re-run of its own.

Net: 242 lines to 226. The length saving is modest and was never the point — every item removed
was one of the few things in the file that changes.

### D52. Gain above 450 leaves the project
Four things happened, in order. The decision is the fourth, and it is only defensible because of
the three before it.

**1. The camera turned out to run to 600, past where anyone publishes.** The retired project
assumed the gain control stopped at 400. It does not: the SDK's own range says **0–600**, and that
is where L05 came from. ZWO's published charts stop at **450**. So the moment the range was read
off the hardware rather than assumed, the top third of it had no vendor curve to be checked
against — which was a reason to *measure* it, not a reason to avoid it. Session 01 measured it:
the coarse block walks 0 to 600 in steps of 10.

**2. It measured it, and 450–600 does not behave like the rest of the range.** Four findings, all
in `04_sweep_read`, none fatal alone:

- **Gain 600 has pixels reading zero at *every* offset in the arm** — including offsets where the
  pedestal sits over a thousand counts clear of the floor and clipping is arithmetically
  impossible. Left in the offset criterion it produces no contradiction, which would at least be
  obvious. It quietly drags `offset_min_safe` from **10 to 45**: a threshold answering a question
  about telegraph pixels while wearing the label of an answer about clipping. It had to be
  excluded by hand, and the exclusion needed the pixels themselves to justify it.
- **The fixed-pattern ratio breaks its own flat line there.** 1.011 ± 0.007 across 77 gains, and
  **1.02 at gain 600** — the same telegraph pixels turning up in the spatial spread.
- **The pedestal fit is an order of magnitude worse on the branch that contains them.** Worst
  residual **0.62 counts on LCG, 16.17 on HCG**, and HCG is the branch where the exponential term
  reaches 965 counts.
- **The vendor comparison degrades exactly where the vendor curve ends.** The ratio to ZWO's
  read-noise prediction holds 0.94–1.05 from gain 0 to 300, then drifts to 0.85 at 350 and 1.27 at
  450.

Together they are a pattern rather than four separate curiosities: **every analysis in session 01
needed an exception carved for the top of the gain range.** An exception is a term in the model
that exists to describe a setting nobody uses, and it is paid for at every future use site.

**3. And the bench is dramatically easier below 450.** The attenuation scout measured 839,000
counts/s at gain 100 on a bare screen — `t_sat(gain 0)` of 15.2 ms. Gain 600 is 1000× gain 0, so
the faintest ladder rung (0.3% of `t_sat`) lands at **0.035 µs**, three orders of magnitude under
the camera's 32 µs floor; clearing it needs **~4000×** of attenuation, which paper and grey level
cannot deliver. Gain 450 is 178×, and the same rung needs **125×** to clear the floor or ~790× for
comfortable margin. Capping the range turns an infeasible light source into a reachable one and
the session into about five minutes of shutter-open time.

**4. So gain above 450 is out of scope, because there is no practical use to pay for the
trouble.** Session 01's own `pedestal_fit` puts the pedestal at **1025 of 4095 counts** at gain
600: a quarter of the scale gone before a photon arrives, leaving 3070 of headroom and, at ZWO's
predicted `g₀ = 9.4`, about **29 e⁻ of full well**. L25's retired-project table — measured
independently, years earlier, on the same sensor model — says **26 e⁻ and 4.92 stops** of dynamic
range there, against 12.51 stops at gain 0. Two sources with nothing in common agree that gain 600
cannot hold a sky background. Nobody was ever going to shoot with it.

**450 is kept as a comparison point and not as a usable one.** Its own well is only ~204 e⁻ and it
would fail the practical test on its merits. It stays because it is the vendor chart's last point,
and dropping it would leave the top third of the gain law with no external check at all.

**What this is not.** It is a scope decision, not a finding about the sensor. The claim that gain
600 is useless rests on a *prediction* — ZWO's `g₀` carried up by the gain law — together with
session 01's measured telegraph noise. Nothing in this project will measure it now, and the record
must not later read as though something did.

**Measurements already taken above 450 stay.** Session 01's rows above the ceiling remain in
`results/bias_sweep.csv` exactly as measured, and `04_sweep_read`'s account of the gain-600
exclusion stays with them: it is the evidence for this entry. Descoping decides what we
characterise from here; it is never a licence to delete data that cost a night.

**Rejected:** teaching `asi.py` to refuse gains above 450. The camera's control runs to 600 and the
library reads its range from the SDK (L05). A library that lies about what the hardware does in
order to enforce a project policy is a library that cannot be trusted about anything else.

### D53. `bench-setup.md` becomes `light-source.md`, and loses five of its eight items
D40 opened `protocols/` with an eight-item bench pre-flight because nothing else existed to hold
those actions. Since then the library grew guards and the numbered protocols grew gates, and the
file was quietly hollowed out — which is how a reader came to open it and ask what it was for.

**Five items left because code now refuses rather than reminds.** `asi.open_camera` raises naming
both the ASIAIR and the missing Windows driver (item 1); `neutralise_white_balance` runs on every
open and gate 1 of each protocol checks the pixels (item 2); `asi.cool_to` holds its settle window
and carries the power-cycle rule (item 4); `asi.set_roi` rejects an odd ROI before the Bayer phase
can shift (item 5). **A checklist item whose failure mode is already an exception is a checklist
item nobody needs to read.** Item 7's shrink-the-ROI-for-linearity rule left too, but for a
different reason: L09 and L12 are still queued in `LEGACY`, so the claim already has a home and a
consuming session.

**Worse than redundant, it was contradictory in shape.** `01-bias-sweep.md` said "run items 1, 2,
4, 5" and then stated gates that restate items 2 and 4 in full. Two documents describing the same
action is the duplication D13 exists to prevent, and it had grown inside the folder D13 created.

**What survives is what no code can check**: the ten-minute panel warm-up, the three iOS settings,
and the attenuation measurement. All three are light-source items, so the file is named for that
and cap-on sessions do not run it at all. It is deliberately *not* folded into `02-ptc.md`: the
linearity sweep that MISSION needs for `ceiling(gain)` uses the same panel, the same warm-up and
the same settings, and would otherwise copy them back out.

**Two dangling citations were cleaned up on the way.** L06, L07 and L08 were harvested in D51 with
`bench-setup.md` named as their destination, but the file kept citing them — pointers to entries
that no longer exist. Their content is stated in full in the new file and the citations are gone,
which is what harvesting was supposed to leave behind.

**Rejected:** deleting the pre-flight entirely and folding its two human-only items into
`02-ptc.md`. It reads well today, with one document open at the bench, and costs a silent
duplication the moment the linearity protocol is written.

---

## 2026-08-31 — Harvest of session 02's LEGACY entries

### D54. Five and a half entries leave the queue: L10, L11, L25, L29, L30, and L32's PRNU half
Build step 3 has run, so the entries whose `Consumed by` named it are due. Each has a verdict
published with provenance in `results/ptc_constants.json`, which is the condition for deletion.
`LEGACY.md` goes 21 entries → 16.

| entry | verdict | where it landed |
|---|---|---|
| L10 read noise from a bias pair, not the intercept | used, not merely believed | `protocols/02-ptc.md` — the geometric ladder (×1.679, 0.3–90%) and the one-parameter fit; the free-intercept fit retained as `R_fit` and `g_free` in `results/ptc_gain.csv`; the argument in `00_statistics` and `06_ptc_read` §3 |
| L11 two-point photon transfer on ordinary frames | agreed: **+1.31%** at gain 50, **−0.33%** at gain 252 | `ptc_constants.json` → `archive_cross_check` |
| L25 the headline sensor constants | `g₀` **9.3967** against a predicted 9.382, inside the 9.38–9.46 band named in advance; six of seven shared gains inside 0.7% | `ptc_constants.json` → `g_at_gain0`, `system_gain`, `vendor_prediction` |
| L29 the 0.1 dB gain law, unity gain ~194 | shape reproduced, precision refuted: slope **−0.005102** (1.020× the law), unity gain **192.6**, residual **1.34%** against a 1% test | `ptc_constants.json` → `gain_law` |
| L30 two of ZWO's panels are measured, two derived | confirmed: **no step in `g`** at the HCG threshold, −0.88% against 1.34% fit scatter | `ptc_constants.json` → `hcg_step_in_gain`; `06_ptc_read` §7, where well and DR are computed as arithmetic and labelled as such |
| L32's PRNU half | refuted: **1.02% ± 0.45%** against a claimed 0.61% | `ptc_constants.json` → `prnu`, `fpn_term_present` |

**L25's table is carried here in full, because a citation outlives the entry.** `CLAUDE.md`'s
gain-domain rule quotes its 4.92 stops at gain 600, and D52 quotes its 26 e⁻; both must still
resolve. Per **real** (12-bit) ADU, from the retired 61-gain sweep:

| gain | e⁻/ADU | read noise (e⁻) | full well (e⁻) | DR (stops) |
|---:|---:|---:|---:|---:|
| 0 | 9.382 | 6.18 | 36 057 | 12.51 |
| 50 | 5.425 | 4.95 | 20 837 | 12.04 |
| 100 | 2.994 | 4.22 | 11 492 | 11.41 |
| 190 | 1.051 | 3.39 | 4 017 | 10.21 |
| 200 | 0.927 | 1.13 | 3 558 | 11.62 |
| 250 | 0.513 | 1.03 | 1 964 | 10.89 |
| 300 | 0.284 | 0.97 | 1 083 | 10.12 |
| 600 | 0.009 | 0.85 | 26 | 4.92 |

**Its read-noise column got a verdict too, and it splits at the cliff.** `R_e` in `ptc_gain.csv`
is session 01's `R` in counts carried by this session's `g`, so the comparison is a composite of
two sessions against one: **+0.4%, −0.2%, +0.9%, +1.7%** at gains 0, 50, 100, 190, and then
**−12.2%, −13.9%, −17.3%** at 200, 250, 300. Below the HCG threshold the two rigs agree to under
2%; above it this camera reads materially quieter than theirs. Two readings are available — a
genuinely better part, or a threshold that lands differently — and nothing here separates them.
The measured value is ours and stands on session 01's bias pairs; L25's is recorded above as the
prediction it is.

**Its full-well and DR columns were not reproduced, and were never going to be.** Both are
arithmetic on `g` and the pedestal — L30's point, now confirmed — so reproducing them tests the
multiplication and not the sensor. The measurement that would make a well figure real is L28's
1%-departure point, and L28 stays in the queue with a note saying so.

**L29 leaves even though half of it failed.** An entry's job is to be tested, not to be right,
and its verdict is published: the slope is 1.020× the 0.1 dB law rather than L29's 1.005×, and
the 1.34% residual fails the interpolation test `02-ptc.md` set in advance. What follows from
that failure — widen the gain set, densest around the two suspect points 0 and 300, before any
`g` is read off between measured gains — is *this* project's work item, recorded in
`ptc_constants.json`'s `gain_law` note and in `06_ptc_read` §11. `LEGACY` holds inherited claims;
it is not the backlog.

**L32 is split rather than deleted.** The PRNU half has a measurement and leaves; the sky rate
needs lights and stays, with a line inside the entry saying where its other half went. Same
treatment L31 got on 2026-08-29, and for the same reason — an entry that is half consumed is not
harvested, but it should not keep advertising the half that is.

**Rejected: harvesting L09 and L12 as well.** Session 02 *used* both — the full 1024×1024 ROI
rests on L09's own PTC exemption, and every rung is placed against a `t_sat` solved per plane on
L12's grounds. Relying on a claim is not checking it: nothing in this session read a bend, so the
1.34× saturating-exposure spread and the shared bend level are as unverified as they were. Both
entries now carry a note saying they were leaned on, which is the honest version of the record.

**Rejected: cleaning the citations out of `02-ptc.md` and the notebooks.** D53 removed L06–L08
from `light-source.md` because that file restated their content in full and the numbers had become
dangling pointers in a live instruction. These are the opposite case: a protocol that says
"geometric and not linear because of L10", and a notebook that prints `vs_L25`, are recording
*which prediction was tested*, and the number is the trail `LEGACY`'s preamble promises will
survive the file. They stay.

**The queue is regrouped, not just shortened.** Sections are named for the consuming step —
linearity (L09, L12, L28), the dark bound (L14), stacking (L15), PixInsight (L16–L24), open
questions (L31, L32) — because the old "Numbers to reproduce — build step 3" heading would
otherwise have been left holding one linearity entry. Fifteen of the sixteen survivors are now
one bench session away from a verdict; L32's sky rate is the exception, and needs a clear night.
