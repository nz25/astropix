"""spatial.py -- the Bayer lattice."""

import numpy as np

from astropix import spatial


def test_split_takes_the_four_bayer_positions():
    a = np.arange(36).reshape(6, 6)
    p = spatial.split(a)
    assert set(p) == set(spatial.PLANES)
    assert all(v.shape == (3, 3) for v in p.values())
    # every mosaic pixel lands in exactly one plane, none twice
    got = sorted(int(v) for pl in p.values() for v in pl.ravel())
    assert got == list(range(36))
    assert p["R"][0, 0] == 0 and p["G1"][0, 0] == 1
    assert p["G2"][0, 0] == 6 and p["B"][0, 0] == 7


def test_split_returns_views_not_copies():
    """Views matter: the index splits thousands of blocks and must not copy."""
    a = np.zeros((4, 4), np.uint16)
    spatial.split(a)["R"][0, 0] = 5
    assert a[0, 0] == 5


def test_split_drops_an_odd_trailing_row_and_column():
    """All four planes must come back the same shape.  Plain striding on a 5x5
    would give (3,3), (3,2), (2,3), (2,2), which breaks anything that stacks
    them -- and would do it silently, on some other sensor, years from now."""
    p = spatial.split(np.zeros((5, 5)))
    assert {v.shape for v in p.values()} == {(2, 2)}
    assert {v.shape for v in spatial.split(np.zeros((2160, 3840))).values()} == {(1080, 1920)}


def test_split_rejects_what_it_cannot_handle():
    for bad, kwargs in [(np.zeros((4, 4)), {"pattern": "GRBG"}),
                        (np.zeros((4, 4, 3)), {})]:
        try:
            spatial.split(bad, **kwargs)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")
