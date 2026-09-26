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


def test_plane_roi_halves_a_mosaic_box_and_refuses_an_odd_one():
    """The sky-pair signal ROI, which every contract 3 number is measured in."""
    assert spatial.plane_roi((1408, 568, 1024, 1024)) == (704, 284, 512, 512)
    try:
        spatial.plane_roi((1, 0, 2, 2))
    except ValueError:
        return
    raise AssertionError("an odd corner starts the box on the other colour")


def test_integer_offset_finds_a_dither_in_both_directions():
    """A star field moved by a known whole-pixel dither, with fresh noise on
    each copy, as two subs of one field are."""
    rng = np.random.default_rng(7)
    field = np.zeros((300, 400))
    field[rng.integers(0, 300, 200), rng.integers(0, 400, 200)] = 500
    for dx, dy in [(17, -9), (-23, 4)]:
        b = np.roll(field, (dy, dx), axis=(0, 1)) + rng.normal(0, 3, field.shape)
        a = field + rng.normal(0, 3, field.shape)
        assert spatial.integer_offset(a, b) == (dx, dy)
        x, y = 100, 100
        assert np.array_equal(spatial.cut(field, (x, y, 50, 50)),
                              spatial.cut(np.roll(field, (dy, dx), axis=(0, 1)),
                                          (x + dx, y + dy, 50, 50)))


def test_cut_is_x_y_w_h_and_refuses_to_run_off_the_edge():
    a = np.arange(20).reshape(4, 5)
    assert np.array_equal(spatial.cut(a, (1, 2, 3, 2)), a[2:4, 1:4])
    try:
        spatial.cut(a, (3, 0, 3, 1))
    except ValueError:
        return
    raise AssertionError("a box that runs off the array must not shrink quietly")
