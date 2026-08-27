"""Colour-filter-array (CFA) plane handling for the ASI585MC (RGGB mosaic).

The rule this module exists to enforce (DECISIONS D4): every noise statistic is
computed on the raw mosaic, split into its four Bayer sub-planes.  Debayering
interpolates, and an interpolated pixel's noise is correlated with its
neighbours', which silently destroys every variance estimate downstream.

Orientation caveat
------------------
Splitting on (row % 2, col % 2) always separates the four Bayer positions
correctly, whatever the row order.  Which of them is *red* does not follow from
the split: a vertical flip between how the sensor read out and how the array is
indexed swaps R and B.  Noise statistics are indifferent to that; anything that
attributes a number to a colour is not.  `label_planes_by_flux` settles it from
the data rather than from the header.
"""

from __future__ import annotations

import numpy as np

# Offsets into the 2x2 tile, in the order implied by a BAYERPAT of 'RGGB' read
# with array row 0 as the pattern's first row.  See the orientation caveat.
RGGB_OFFSETS = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}
PLANES = ("R", "G1", "G2", "B")


def split(mosaic, pattern="RGGB"):
    """Split a raw CFA mosaic into its four Bayer sub-planes.

    Returns a dict name -> view of shape (h//2, w//2).  These are strided
    *views*, not copies: cheap to take, but write to them and you write to the
    mosaic.

    An odd trailing row or column is dropped so that all four planes come back
    the same shape.  Plain striding would hand back (3,3), (3,2), (2,3), (2,2)
    for a 5x5 mosaic, which breaks the moment anything stacks the planes.  The
    sensor is 3840x2160, so in practice nothing is ever dropped.
    """
    if pattern.upper() != "RGGB":
        raise ValueError(f"only RGGB is characterised on this rig, got {pattern!r}")
    a = np.asarray(mosaic)
    if a.ndim != 2:
        raise ValueError(f"expected a 2-D mosaic, got shape {a.shape}")
    h, w = a.shape[0] & ~1, a.shape[1] & ~1
    a = a[:h, :w]
    return {name: a[dy::2, dx::2] for name, (dy, dx) in RGGB_OFFSETS.items()}


def label_planes_by_flux(planes):
    """Guess which physical colour each sub-plane holds, from relative level.

    The two greens sit on the anti-diagonal of the tile and see the same filter,
    so they are the pair whose medians agree most closely; R and B are the other
    two.  Under broadband sky glow with no filter, R runs above B on this rig,
    which breaks the remaining tie.  This is a *check* on the header's BAYERPAT,
    reported as evidence, never applied silently.
    """
    med = {k: float(np.median(v)) for k, v in planes.items()}
    pairs = [(a, b) for i, a in enumerate(PLANES) for b in PLANES[i + 1:]]
    g1, g2 = min(pairs, key=lambda p: abs(med[p[0]] - med[p[1]]))
    rest = [k for k in PLANES if k not in (g1, g2)]
    r, b = sorted(rest, key=lambda k: -med[k])
    return {r: "R", g1: "G1", g2: "G2", b: "B"}, med
