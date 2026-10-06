"""The repo-level rule, not a library module.

Every file in `results/` must be written by a cell in a numbered notebook.
See CLAUDE.md, 'How work is recorded'.
"""

import json
import pathlib
import re
import subprocess



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
# The document graph: canonical and archive
# --------------------------------------------------------------------------
#
# D42 split the Markdown files by role and made the citation graph
# one-way and downhill.  Prose policies decay silently -- the two-hop lookup it
# replaced grew back over three sessions without anyone deciding to -- so the
# shape is asserted here rather than remembered.

CANONICAL = ("MISSION.md", "CLAUDE.md")

# The one block allowed to name the archive, because its purpose is to
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
    document -- which is how three copies of the units rule came to exist."""
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


# --------------------------------------------------------------------------
# Notebooks are committed stripped
# --------------------------------------------------------------------------
#
# CLAUDE.md, "How work is recorded".  There is no nbstripout filter in this
# repo -- stripping has always been a thing someone remembered to do, and 01
# reached the staging area with six cells of outputs before anyone looked.
# That is the same failure the document rules exist to prevent, one layer down:
# a rule that lives only in a person's memory.
#
# This checks what HEAD holds, not the working tree.  A working copy full of
# outputs is the normal state right after a run and must not turn the suite
# red; what must never happen is that state reaching a commit.


def _git(*args):
    """Run git in the repo.  None if git, or the repo, is unavailable -- the
    suite has to keep working on a copy that was never a checkout."""
    try:
        done = subprocess.run(("git", "-C", str(_repo_root())) + args,
                              capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def test_committed_notebooks_have_no_outputs():
    """Source only, in what git stores.  An execution_count is enough to fail
    on: it is the half that survives when someone clears outputs by hand."""
    listing = _git("ls-files", "-z", "--", "notebooks/*.ipynb")
    if listing is None:
        return
    dirty = {}
    for name in listing.decode("utf-8").split("\0"):
        if not name:
            continue
        blob = _git("show", "HEAD:" + name)
        if blob is None:      # tracked but not yet in HEAD
            continue
        nb = json.loads(blob.decode("utf-8"))
        cells = [i for i, c in enumerate(nb["cells"])
                 if c["cell_type"] == "code"
                 and (c.get("outputs") or c.get("execution_count") is not None)]
        if cells:
            dirty[name] = cells
    assert not dirty, (
        "notebooks are committed with outputs stripped; these cells carry "
        f"outputs or an execution_count in HEAD: {dirty}")
