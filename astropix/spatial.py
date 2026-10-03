"""Where things sit in the frame: the Bayer lattice.

The counterpart to `stats.py`.  That module asks how much a set of pixels
varies; this one asks where they are.  Both work on plain arrays and neither
opens a file.

`split` is the lattice.  `plane_roi` and `cut` are the boxes contract 3
measures in: a mosaic ROI carried onto one sub-plane, and the box itself.
`star_mask` is source detection, which arrived when a noise measurement needed
to know where the stars were.  It briefly also held `bright_pixels`, which
counted pixels above a threshold and asked whether they touched -- the old
dark/light discriminator.  That test was retired (D50) and the function went
with it rather than sitting here uncalled.

The rule this module exists to enforce (`CLAUDE.md`): every noise statistic is
computed on the raw mosaic, split into its four Bayer sub-planes.  Debayering
interpolates, and an interpolated pixel's noise is correlated with its
neighbours', which silently destroys every variance estimate downstream.

**RGGB is a project constant, not a parameter.** One rig, one sensor, one
orientation (`CLAUDE.md`); `split` raises on anything else rather than quietly
handling a mosaic this project has never characterised.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

# Offsets into the 2x2 tile, for a BAYERPAT of 'RGGB' read with array row 0 as
# the pattern's first row.  A vertical flip between how the sensor read out and
# how the array is indexed would swap R and B; `bayerpat` is a column in the
# index, so that check is a groupby away if a frame from elsewhere ever appears.
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


def plane_roi(roi):
    """A mosaic ROI `(x, y, w, h)` as the same box on one Bayer sub-plane.

    Every coordinate halves.  An odd one raises: it would start the box on
    the other colour's row or column, and the plane box would then not be
    the patch of sky the mosaic box names.
    """
    if any(v % 2 for v in roi):
        raise ValueError(f"mosaic ROI {roi} has an odd coordinate")
    return tuple(v // 2 for v in roi)


def integer_offset(a, b):
    """Where `a`'s content sits in `b`, to the nearest whole pixel: `(dx, dy)`
    such that `a[y, x]` is the same sky as `b[y + dy, x + dx]`.

    Phase correlation: the cross-power spectrum normalised to unit magnitude
    has an inverse transform that is a spike at the shift.  Whole pixels on
    purpose.  Moving a frame by an integer relabels its pixels and leaves
    every pixel's noise alone, which is the one thing contract 3 needs from a
    raw frame -- a sub that has not been resampled, lined up well enough that
    its stars and nebula cancel against another.  The residual misfit is at
    most half a pixel, and what it leaves behind is measurable: white noise
    binned 4x4 falls to exactly a quarter, and whatever does not is structure.

    Shifts wrap, so an offset beyond half the array in either axis comes back
    with the wrong sign; a dither is tens of pixels on a 1920 x 1080 plane.
    """
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    if a.shape != b.shape:
        raise ValueError(f"shapes differ: {a.shape} and {b.shape}")
    cross = np.fft.rfft2(b - b.mean()) * np.conj(np.fft.rfft2(a - a.mean()))
    peak = np.fft.irfft2(cross / (np.abs(cross) + 1e-12), s=a.shape)
    iy, ix = np.unravel_index(int(np.argmax(peak)), peak.shape)
    h, w = a.shape
    return (int(ix if ix < w // 2 else ix - w), int(iy if iy < h // 2 else iy - h))


def cut(a, roi):
    """The `(x, y, w, h)` box of a 2-D array.  A view, and it raises rather
    than silently returning a smaller box when the ROI runs off the edge."""
    x, y, w, h = roi
    if x < 0 or y < 0 or y + h > a.shape[0] or x + w > a.shape[1]:
        raise ValueError(f"ROI {roi} does not fit in an array of shape {a.shape}")
    return a[y:y + h, x:x + w]


def star_mask(image, nsigma=5.0, grow=3, background=31):
    """Where the stars are: True on every pixel within `grow` of one.

    Pass a *deep* image -- a stack, not a sub -- so the faint stars stand out
    of the noise and the mask reaches as far into their wings as the data can
    see.  A star is anything more than `nsigma` above its local background,
    and the background is a running median `background` pixels wide.  A median
    because it steps over a star without rising into it, and a local one
    because the field this project measures in is nebula: a single level for
    the whole box would call the bright side of it a star.  The threshold is in
    units of the noise of what is left, from its MAD -- the same 1.4826 as
    `stats.MAD_TO_SIGMA`, written out here because `stats` imports this module.

    Then every detection is grown by a disc of radius `grow` pixels.  The
    threshold finds a star's core; what the mask is *for* is the wings around
    it, which lie below any threshold and are the part `stats.diff_sigma`'s
    clip cannot reach.
    """
    a = np.asarray(image, np.float64)
    if a.ndim != 2:
        raise ValueError(f"expected a 2-D image, got shape {a.shape}")
    resid = a - ndimage.median_filter(a, size=background, mode="reflect")
    scale = 1.4826 * float(np.median(np.abs(resid - np.median(resid))))
    if not scale > 0:
        raise ValueError("the image has no noise to set a threshold against")
    found = resid > nsigma * scale
    if grow > 0:
        yy, xx = np.indices((2 * grow + 1, 2 * grow + 1)) - grow
        found = ndimage.binary_dilation(found, structure=xx ** 2 + yy ** 2 <= grow ** 2)
    return found
