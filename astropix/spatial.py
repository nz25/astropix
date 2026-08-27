"""Where things sit in the frame: the Bayer lattice, and bright-pixel shape.

The counterpart to `stats.py`.  That module asks how much a set of pixels
varies; this one asks where they are and what they are next to.  Both work on
plain arrays and neither opens a file.

The rule this module exists to enforce (DECISIONS D4): every noise statistic is
computed on the raw mosaic, split into its four Bayer sub-planes.  Debayering
interpolates, and an interpolated pixel's noise is correlated with its
neighbours', which silently destroys every variance estimate downstream.

**RGGB is a project constant, not a parameter.** One rig, one sensor, one
orientation (`CLAUDE.md`); `split` raises on anything else rather than quietly
handling a mosaic this project has never characterised.
"""

from __future__ import annotations

import numpy as np

# Offsets into the 2x2 tile, for a BAYERPAT of 'RGGB' read with array row 0 as
# the pattern's first row.  A vertical flip between how the sensor read out and
# how the array is indexed would swap R and B; `bayerpat` is a column in the
# index, so that check is a groupby away if a frame from elsewhere ever appears.
RGGB_OFFSETS = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}
PLANES = ("R", "G1", "G2", "B")

TAIL_K = 5.0          # sigma above the plane median for "bright pixel"


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



def bright_pixels(plane, thr):
    """Count bright pixels and how many have a bright neighbour, per axis.

    Splitting horizontal from vertical matters: a hot *column* -- a common CMOS
    defect -- is vertically connected and would otherwise read as a star.  A
    real PSF is connected both ways, so the weaker axis is the honest one.
    """
    m = plane > thr
    n = int(m.sum())
    if n == 0:
        return 0, 0, 0
    h = np.zeros_like(m)
    h[:, 1:] |= m[:, :-1]
    h[:, :-1] |= m[:, 1:]
    v = np.zeros_like(m)
    v[1:, :] |= m[:-1, :]
    v[:-1, :] |= m[1:, :]
    return n, int((m & h).sum()), int((m & v).sum())

