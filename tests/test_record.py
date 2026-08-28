"""The repo-level rule, not a library module.

Every file in `results/` must be written by a cell in a numbered notebook.
See CLAUDE.md, 'How work is recorded'.
"""

import json
import pathlib
import re



WRITE_CALLS = ("to_csv(", "to_json(", "json.dump(", "refresh_index(",
               "_write_index(")
RESULT_SUFFIXES = (".csv", ".json")


def _repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def results_writers():
    """Map `results/` filename -> [(notebook, cell index)] that writes it.

    Two ways a cell can name its output, both used in practice:
    a literal (`to_csv(RESULTS / "ladder_census.csv")`) and a module-level alias
    (`INDEX = RESULTS / "frame_index.csv"`, then `refresh_index(roots, INDEX)`).
    The window of three lines covers a call wrapped across lines.
    """
    out = {}
    for nbp in sorted((_repo_root() / "notebooks").glob("*.ipynb")):
        nb = json.loads(nbp.read_text(encoding="utf-8"))
        cells = [(i, "".join(c["source"])) for i, c in enumerate(nb["cells"])
                 if c["cell_type"] == "code"]
        alias = dict(re.findall(r"(\w+)\s*=\s*RESULTS\s*/\s*[\"']([^\"']+)[\"']",
                                "\n".join(s for _, s in cells)))
        for i, source in cells:
            lines = source.splitlines()
            for n, line in enumerate(lines):
                if not any(v in line for v in WRITE_CALLS):
                    continue
                window = "\n".join(lines[n:n + 3])
                names = set(re.findall(r"[\"']([\w.\-]+\.(?:csv|json))[\"']", window))
                names |= {f for var, f in alias.items()
                          if re.search(r"\b" + re.escape(var) + r"\b", window)}
                for name in names:
                    out.setdefault(name, []).append((nbp.name, i))
    return out


def test_every_results_file_has_a_generator():
    """The rule D33 states.  An orphan here means a number was published that
    nobody can regenerate -- which is how the three census CSVs were lost."""
    root = _repo_root()
    if not (root / "notebooks").is_dir() or not (root / "results").is_dir():
        return
    writers = results_writers()
    orphans = sorted(f.name for f in (root / "results").iterdir()
                     if f.suffix in RESULT_SUFFIXES and f.name not in writers)
    assert not orphans, ("no notebook cell writes " + ", ".join(orphans)
                         + " -- see DECISIONS D33")


def test_only_numbered_notebooks_write_to_results():
    """D33's other half: question notebooks are disposable, so nothing durable
    may depend on one.  A `results/` file written by an unnumbered notebook is a
    finding that has not graduated yet."""
    root = _repo_root()
    if not (root / "notebooks").is_dir():
        return
    stray = sorted({nb for hits in results_writers().values()
                    for nb, _ in hits if not re.match(r"^\d\d_", nb)})
    assert not stray, f"unnumbered notebooks writing to results/: {stray}"



# --------------------------------------------------------------------------
# LEGACY.md is a queue, not a library
# --------------------------------------------------------------------------
#
# It is the one file in this repo whose success condition is its own deletion
# (DECISIONS D38).  The failure mode is obvious: entries get harvested and never
# removed, and it quietly becomes a fifth permanent document -- exactly what
# D13's four-file rule exists to prevent.  These tests make "queue, not library"
# a property the suite checks rather than a habit anyone has to remember.

LEGACY_FIELDS = ("**Claim.**", "**Source.**", "**Consumed by.**",
                 "**How to check.**", "**Lands in.**")


def legacy_entries():
    """Map entry heading -> body, for every `### Lnn.` section in LEGACY.md."""
    path = _repo_root() / "LEGACY.md"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^### (L\d+\..*)$", text)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts), 2)}


def test_every_legacy_entry_names_its_exit():
    """`Consumed by` and `Lands in` are what make the queue drain.  An entry
    without them is a note, and notes accumulate."""
    missing = {}
    for head, body in legacy_entries().items():
        absent = [f for f in LEGACY_FIELDS if f not in body]
        if absent:
            missing[head.split(".")[0]] = absent
    assert not missing, f"LEGACY entries missing required fields: {missing}"


def test_legacy_entry_numbers_are_unique():
    """Entries are cited by number from wherever they land, so the number has to
    stay a stable identifier even as neighbours are deleted."""
    nums = [h.split(".")[0] for h in legacy_entries()]
    dupes = sorted({n for n in nums if nums.count(n) > 1})
    assert not dupes, f"duplicate LEGACY ids: {dupes}"


def test_legacy_is_deleted_once_empty():
    """The termination condition, asserted rather than hoped for: when the last
    entry is harvested the file goes, and the repo is back to four Markdown
    files (D13)."""
    path = _repo_root() / "LEGACY.md"
    if not path.exists():
        return
    assert legacy_entries(), (
        "LEGACY.md has no entries left -- delete it, and drop its row from "
        "CLAUDE.md's boot list (D38)")


# --------------------------------------------------------------------------
# The document graph: canonical, archive, and Denis's
# --------------------------------------------------------------------------
#
# D42 split the four Markdown files three ways and made the citation graph
# one-way and downhill.  Prose policies decay silently -- the two-hop lookup it
# replaced grew back over three sessions without anyone deciding to -- so the
# shape is asserted here rather than remembered.

CANONICAL = ("MISSION.md", "CLAUDE.md")

# The one block allowed to name the other two files, because its purpose is to
# say they are not read for rules.  A de-reference is the opposite of a citation.
DEREF_HEADING = "## Document status"

CITES = re.compile(r"\bDECISIONS\b|\bFINDINGS\b|\bD\d{1,2}\b")


def _without_deref_block(text):
    """CLAUDE.md's `## Document status` section, up to the next `## ` heading."""
    if DEREF_HEADING not in text:
        return text
    head, rest = text.split(DEREF_HEADING, 1)
    tail = re.split(r"(?m)^## ", rest, maxsplit=1)
    return head + ("## " + tail[1] if len(tail) > 1 else "")


def test_canonical_docs_cite_nothing_out():
    """D42: every live rule is stated in MISSION.md or CLAUDE.md, in full.  A
    citation out of them means a rule you cannot follow without opening a second
    document -- which is how three copies of the units rule came to exist.

    `LEGACY` and `Lnn` are deliberately still allowed: LEGACY.md is a boot
    document until it empties itself, and its entries are hypotheses to check,
    not rules to follow."""
    offenders = {}
    for name in CANONICAL:
        path = _repo_root() / name
        if not path.exists():
            continue
        body = path.read_text(encoding="utf-8")
        if name == "CLAUDE.md":
            body = _without_deref_block(body)
        for n, line in enumerate(body.splitlines(), 1):
            if CITES.search(line):
                offenders.setdefault(name, []).append((n, line.strip()[:70]))
    assert not offenders, (
        "canonical documents must state rules in full, not cite them: "
        f"{offenders}")


def test_nothing_cites_findings():
    """D43: FINDINGS.md is Denis's, and a leaf.  It cites `results/`; nothing
    cites it.  That is what lets him rewrite or empty it without breaking
    anything.

    DECISIONS.md is exempt entirely.  It is append-only history that is never
    edited, its pre-D42 mentions stand as written, and D42-D45 are the very
    entries that de-reference the file.  What this guards is everything still
    live: the canonical documents, LEGACY, the notebooks and the package."""
    root = _repo_root()
    offenders = {}
    for path in sorted(root.rglob("*")):
        if path.suffix not in (".md", ".py", ".ipynb") or not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith((".git/", "venv/", "astro/", "learn_astro/")):
            continue
        if rel in ("FINDINGS.md", "DECISIONS.md", "tests/test_record.py"):
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        if rel == "CLAUDE.md":
            body = _without_deref_block(body)
        hits = [line.strip()[:70] for line in body.splitlines()
                if "FINDINGS" in line]
        if hits:
            offenders[rel] = hits
    assert not offenders, (
        "FINDINGS.md is Denis's and is cited from nowhere; a measured number "
        f"belongs in results/ and a rule in CLAUDE.md: {offenders}")


def test_legacy_lands_somewhere_real():
    """D42 retargeted `Lands in`.  "Lands in prose" is not a destination: it is
    how a number arrives with no unit, uncertainty or source frame, which D14
    exists to forbid."""
    bad = {h.split(".")[0]: "Lands in FINDINGS" for h, b in legacy_entries().items()
           if re.search(r"\*\*Lands in\.\*\*[^\n]*FINDINGS", b)}
    assert not bad, f"LEGACY entries still landing in FINDINGS: {bad}"
