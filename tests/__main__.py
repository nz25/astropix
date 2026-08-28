"""Run every test in the package without pytest.

Kept dependency-free on purpose: the suite has to be runnable on the capture
machine, mid-session, with nothing installed but the library's own imports.
"""

import importlib
import pathlib


def main():
    tests = []
    here = pathlib.Path(__file__).parent
    for mod in sorted(p.stem for p in here.glob("test_*.py")):
        m = importlib.import_module(f"{__package__}.{mod}")
        tests += [(f"{mod}.{n}", f) for n, f in sorted(vars(m).items())
                  if n.startswith("test_") and callable(f)]

    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ok    {name}")
        except Exception as exc:
            failed.append(name)
            print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    _legacy_reminder()
    return 1 if failed else 0


def _legacy_reminder():
    """Print what is still queued in LEGACY.md.

    The suite is the one thing run often enough to be a reliable nudge.  A
    session can read CLAUDE.md's boot list once and then work for hours without
    reopening it; this puts the outstanding count in front of whoever is
    working, at a moment they are already reading output.
    """
    path = pathlib.Path(__file__).resolve().parents[1] / "LEGACY.md"
    if not path.exists():
        return
    groups, current = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
        elif line.startswith("### L") and current:
            groups[current] = groups.get(current, 0) + 1
    if not groups:
        return
    print(f"\nLEGACY: {sum(groups.values())} inherited claims still unverified "
          f"-- scan before starting a build step (CLAUDE.md item 4)")
    for name, n in groups.items():
        # The suite must never fail on its own output: these headings come
        # from a Markdown file and carry en/em dashes, which a console on a
        # narrow codepage cannot encode.
        flat = name.replace("—", "-").replace("–", "-")
        flat = flat.encode("ascii", "ignore").decode()
        print(f"  {n:3d}  {flat}")


if __name__ == "__main__":
    raise SystemExit(main())
