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
