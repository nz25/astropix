"""Tests for the astropix package.

One module per library module, plus `test_record.py` for the repo-level rule
that `results/` is only ever written by a notebook.

Everything runs on synthetic frames in a temp directory, so the suite needs
neither Z: nor clear sky, and it is safe to run while the archive is frozen
for a measurement (D19).

    python -m tests            # no dependencies beyond the library
    pytest tests               # if pytest happens to be installed
"""
