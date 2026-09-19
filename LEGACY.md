# Legacy

Claims inherited from the two retired attempts at this project, both now deleted.

**This file is a queue, not a library. It exists to be emptied.** Nothing here is knowledge this
project holds; it is knowledge someone else's project claimed, kept because rediscovering it
would cost bench nights. Each entry is verified when the build step that needs it arrives, then
**moved to its destination and deleted from here**. When the file is empty it is deleted, and
this repo is back to four Markdown files.

Entries are cited by number from wherever they land — `results/`, `CLAUDE.md`, `DECISIONS`,
`protocols/`, `pjsr/` — so the trail survives after this file is gone. A measured number lands in
`results/` with its provenance, never in prose alone.

**Schema.** No entry is admitted without all four fields. `Consumed by` and `Lands in` are what
make the queue drain; an entry without them is a note, not a work item.

| field | meaning |
|---|---|
| **Claim** | what the retired project believed |
| **Consumed by** | the build step that needs it |
| **How to check** | the specific test, not "verify this" |
| **Lands in** | where it goes when confirmed |

**What was deliberately excluded:** anything MISSION scopes out (auto-STF and stretching);
anything already independently confirmed here (the 12-bit shift, MAD on quantised data); and
method aphorisms, which are writing advice rather than hypotheses.

**Nothing here has been verified by this project, and there is nothing left to check it
against.** The retired trees are gone; these entries are all that remains of them, so no claim
can be re-read at its origin. The numbers came from a codebase without this project's
provenance discipline, and that codebase retracted at least one of its own published fits.
Treat every number as a prediction to falsify — there is no longer anywhere to appeal.

---

## PixInsight — build step 5

### L23. Subtracting two 16-bit unsigned images clips every negative difference
**Claim.** For a bias pair this **halves the apparent read noise**, and it fails quietly — the
number is plausible, just wrong. Do the subtraction in **32-bit float with a +0.5 pedestal**
(`A - B + 0.5`, `rescale = false`, `truncate = false`): the pedestal moves the mean without
touching the standard deviation and keeps the distribution inside [0,1].
**Consumed by.** Build step 5, **contract 2** — the first thing it must verify, before any number
it produces is believed. Contract 1 subtracts nothing, which is why this entry outlived its eight
neighbours.
**How to check.** Inject a known sigma into a synthetic pair and assert recovery. Not by
inspecting a real bias pair: a halved read noise there looks exactly like a good camera.
**Lands in.** `pjsr/NOTES.md`, whose *Still unchecked* section already states the claim, with the
test alongside.

---

## Open questions inherited

### L31. The panel drifts while it warms, and nobody has watched it from cold
**Claim.** The retired project's version of this — gain 100 irreproducible at 1.79% while gain 200
managed 0.011% — **has been run and is not reproduced.** Session 05's arm 2 interleaved a short
and a long exposure at gain 100 throughout a block: repeat scatter **0.089% long, 0.299% short**,
six times better than L31 at the same gain, with a long/short flux ratio of 0.9886. Their confound
(exposure length and elapsed time varying together) is gone and nothing was hiding under it.

**What is left is one untested candidate: backlight thermal drift.** LED backlights dim as they
warm, a panel at 100% brightness reaches equilibrium over minutes, and session 05 measured a real
drift of **+0.314 ± 0.047 ADC counts/min** — small, seven sigma from zero, and upstream of the
sensor, because session 01's dark arm over the same timescale was −0.00133 ± 0.254 counts/min with
the light taken out. **But that arm was run with the panel already warm**, which is the one state
that cannot distinguish a panel still heating from a panel that has settled. So the mechanism is
consistent with the measurement and remains unproven by it.

**Consumed by.** `protocols/light-source.md` item 1, the ten-minute warm-up, which is currently a
precaution whose reason has been neither confirmed nor falsified.
**How to check.** One block, no ladder: wake the panel from genuinely cold, start capturing
immediately at a fixed gain and exposure, and run for twenty minutes with timestamps. If the trace
is flat from the first frame, **delete item 1** rather than keeping a ritual with no reason behind
it. If it decays to a floor, item 1 stays and its duration should be set from where the trace
flattens rather than from a round number.
**Lands in.** `protocols/light-source.md` — either item 1 deleted, or its ten minutes replaced by
a measured settling time. `results/` gains nothing either way: this is a property of the bench
light, not of the camera.

*(Session 05 resolved the repeatability half of this entry; see DECISIONS D79. The 5.5%
single-rung outlier the retired project saw did not recur either, and its most likely cause —
the screen briefly sleeping — is now caught during capture rather than after it, per D78.)*
