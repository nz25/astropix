"""Where things sit in the frame: the Bayer lattice.

The counterpart to `stats.py`.  That module asks how much a set of pixels
varies; this one asks where they are.  Both work on plain arrays and neither
opens a file.

`split` is the lattice.  `plane_roi` and `cut` are the boxes contract 3
measures in: a mosaic ROI carried onto one sub-plane, and the box itself.
`star_mask` is source detection, which arrived when a noise measurement needed
to know where the stars were, and `stars` is the same detection as a list, for
the star-colour constraint, which needs to follow one star from sub to sub.
`tile_offsets` and `realign` are how it is followed: a whole-pixel shift per
tile, which moves no pixel's value and so leaves a star's peak alone, as
resampling does not.  It briefly also held `bright_pixels`, which
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
from scipy.spatial import cKDTree

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


def _tiles(shape, tiles):
    """The row and column bounds of a `tiles = (ny, nx)` grid over `shape`."""
    return [np.linspace(0, n, k + 1).astype(int) for n, k in zip(shape, tiles)]


TILE_TOLERANCE = 2      # px a tile may sit off the frame's shift-and-turn


def tile_offsets(a, b, tiles=(4, 4), tolerance=TILE_TOLERANCE):
    """`integer_offset` tile by tile: an array of shape `(ny, nx, 2)` holding
    each tile's `(dx, dy)`.

    One shift for a whole frame is not enough over a night.  A mount that is
    not perfectly polar-aligned turns the field slowly, and on session 06 the
    corners of a 1920 x 1080 plane drift about two pixels against the centre
    across five hours.  A star followed by one shift lands a pixel or two off
    its own core in the corners; followed by its tile's shift, it lands within
    about one.

    **A tile can fail, and the frame says so.**  A faint sub over a patch with
    few stars has too little to correlate, and the spike lands anywhere: on
    session 06, eight of 36 subs at gain 50 and 30 s each had a tile off by
    50-230 px, nearly always the same tile.  But the field moves as one body
    -- a shift and a small turn -- so the tiles are fitted to that, starting
    from those near the median, and a tile more than `tolerance` px off the
    fit takes the fit's value.  If fewer than half the tiles agree, there is
    no body to fit and it raises.
    """
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        raise ValueError(f"shapes differ: {a.shape} and {b.shape}")
    ys, xs = _tiles(a.shape, tiles)
    off = np.array([[integer_offset(a[y0:y1, x0:x1], b[y0:y1, x0:x1])
                     for x0, x1 in zip(xs[:-1], xs[1:])]
                    for y0, y1 in zip(ys[:-1], ys[1:])]).reshape(-1, 2)
    # tile centres about the frame centre; a small turn by theta moves a
    # tile by (-theta * y, theta * x), so dx = x0 - theta*y, dy = y0 + theta*x
    cy, cx = np.meshgrid((ys[:-1] + ys[1:]) / 2 - a.shape[0] / 2,
                         (xs[:-1] + xs[1:]) / 2 - a.shape[1] / 2, indexing="ij")
    cy, cx, n = cy.ravel(), cx.ravel(), len(off)
    design = np.block([[np.ones((n, 1)), np.zeros((n, 1)), -cy[:, None]],
                       [np.zeros((n, 1)), np.ones((n, 1)), cx[:, None]]])
    keep = (np.abs(off - np.median(off, axis=0)) <= 5 * tolerance).all(axis=1)
    for _ in range(3):
        if keep.sum() < n / 2:
            raise ValueError(f"only {keep.sum()} of {n} tiles agree on how the frame moved")
        rows = np.concatenate([keep, keep])
        fit = design @ np.linalg.lstsq(design[rows], off.T.ravel()[rows], rcond=None)[0]
        fit = fit.reshape(2, n).T
        keep = (np.abs(off - fit) <= tolerance).all(axis=1)
    off[~keep] = np.round(fit[~keep]).astype(int)
    return off.reshape(len(ys) - 1, len(xs) - 1, 2)


def realign(b, offsets, margin):
    """`b` moved onto the reference's grid, tile by tile, by whole pixels.

    `offsets` is what `tile_offsets(reference, b)` returned.  What comes back
    is the reference frame's inner region, `margin` pixels in from every edge,
    with each pixel taken from wherever its tile's offset says that sky sits in
    `b`.  The margin is what keeps every source pixel inside `b`, so it must be
    at least the largest offset, and it raises rather than wrap.  No value is
    changed: every output pixel is a pixel of `b`, which is the point.
    """
    b = np.asarray(b)
    ys, xs = _tiles(b.shape, offsets.shape[:2])
    if np.abs(offsets).max() > margin:
        raise ValueError(f"an offset of {np.abs(offsets).max()} px needs a margin that large, "
                         f"got {margin}")
    h, w = b.shape
    out = np.empty((h - 2 * margin, w - 2 * margin), b.dtype)
    for i, (y0, y1) in enumerate(zip(ys[:-1], ys[1:])):
        for j, (x0, x1) in enumerate(zip(xs[:-1], xs[1:])):
            dx, dy = offsets[i, j]
            y0, y1 = max(y0, margin), min(y1, h - margin)
            x0, x1 = max(x0, margin), min(x1, w - margin)
            out[y0 - margin:y1 - margin, x0 - margin:x1 - margin] = \
                b[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
    return out


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


def stars(image, nsigma=5.0, background=31, isolation=5):
    """Where each star is: an `(n, 2)` array of `(row, col)`, one per star, at
    its brightest pixel.

    The same detection as `star_mask` with no growth, and the same advice: pass
    a deep image.  Each connected detection is one star, placed on its peak.
    Then any star with another within `isolation` pixels is dropped, both of
    the pair.  A star's peak is read later as the brightest pixel in a small
    box around it, and a neighbour that close would put its own core in that
    box.  So the list is of *isolated* stars, and in a crowded field it is not
    every star; what it is fit for is following one star from sub to sub.
    """
    a = np.asarray(image, np.float64)
    labels, n = ndimage.label(star_mask(a, nsigma=nsigma, grow=0, background=background))
    if n == 0:
        return np.empty((0, 2), int)
    pos = np.array(ndimage.maximum_position(a, labels, range(1, n + 1)), int)
    pairs = cKDTree(pos).query_pairs(isolation, output_type="ndarray")
    crowded = np.zeros(n, bool)
    crowded[pairs.ravel()] = True
    return pos[~crowded]
