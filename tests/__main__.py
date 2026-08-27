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
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
