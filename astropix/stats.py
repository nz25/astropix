"""Pixels to numbers, and the frame verdict those numbers support.

Nothing here opens a file.  Everything takes arrays and returns numbers, which
is why almost all of it is testable without a FITS file, a Z: mount, or a sky.

Two layers:

1.  `frame_features` reduces sampled blocks to the handful of numbers the
    classifier needs, every statistic per CFA sub-plane (D4).
2.  `classify` turns those numbers plus one trusted capture setting into a
    frame type (D18).

**Units are ADC counts** -- see the units rule in `CLAUDE.md` (D41).  `to_adc`
is the only conversion in the project, and `frame_features` applies it once,
after checking the container is the one we think it is.  Everything downstream
of that line is in counts; nothing below needs to remember a factor of 16.

**The `sigma` here is MAD, and MAD is the wrong estimator for noise.** MAD is an
order statistic of quantised deviations, so it can only return multiples of
1.4826 counts -- one quantiser step -- and read noise on this rig lives below
that (D24, whose arithmetic is in the older stored units).  It is kept because
it is a perfectly good *classification* feature: all `bright_pixels` needs is a
roughly-right scale for "unusually bright".  It is not a noise measurement and
nothing may feed it to a fit.  The real estimator is build step 2 and will land
beside it.
"""

from __future__ import annotations

import numpy as np

from . import spatial

MAD_TO_SIGMA = 1.4826

# --- units (CLAUDE.md, D41) --------------------------------------------------
ADC_SHIFT = 4                    # stored = ADC count << 4
ADC_FULL_SCALE = 4095            # 12 bits; the project's unit of pixel value
STORED_FULL_SCALE = 65535        # the container only -- see the four exceptions

# --- classifier thresholds (calibrated in notebooks/01) ----------------------
BIAS_MAX_EXPTIME = 0.01     # s; a bias is the shortest exposure the camera takes
FLAT_MIN_LEVEL = 0.15       # fraction of full scale, so unit-free
LIGHT_MIN_CLUMP = 0.25      # bright pixels sharing a bright neighbour both ways
LIGHT_MIN_TAIL = 1e-5       # bright-pixel fraction, guards against empty tails
SATURATED_FRAC = 0.5        # clipped everywhere: a quality flag, not a type
FLAT_MAX_EXPTIME = 5.0      # s; measured -- every flat in the archive is 1-3 s


def to_adc(a):
    """Stored file values -> native ADC counts.  Exact, or it raises.

    The only unit conversion in the project (D41).  It refuses rather than
    truncates, because a frame whose low bits are set did not come from this
    camera's raw path, and silently shifting it away would turn "a file we do
    not understand" into a plausible number -- the exact failure mode this
    project keeps legislating against.
    """
    a = np.asarray(a)
    if np.any(a & ((1 << ADC_SHIFT) - 1)):
        raise ValueError("values are not all multiples of 16; "
                         "not this rig's raw output")
    return a >> ADC_SHIFT


def frame_features(blocks):
    """Reduce sampled blocks to the handful of numbers the classifier uses.

    Every statistic is per CFA sub-plane (D4), and in ADC counts.  Level and
    spread are medians *across* blocks rather than pooled over them, so that a
    sky gradient or vignetting inflates `block_spread` -- where it is
    informative -- instead of contaminating `sigma`, where it would be a lie.

    `mult16_frac` is measured on the *stored* values and measured first,
    because it is the evidence that licenses the conversion applied right
    after it.  Reading it off converted data would be circular.
    """
    stored = np.concatenate([b.ravel() for b in blocks])
    # 12-bit ADC in a 16-bit container: the check, then the conversion it allows
    mult16_frac = float(np.mean(stored % (1 << ADC_SHIFT) == 0))
    if mult16_frac != 1.0:
        raise ValueError(f"only {mult16_frac:.6f} of values are multiples of 16; "
                         "not this rig's raw output")
    blocks = [to_adc(b) for b in blocks]

    per_plane = {p: {"med": [], "sig": []} for p in spatial.PLANES}
    n_tot = n_h = n_v = n_px = 0
    block_meds = []

    for blk in blocks:
        planes = spatial.split(blk)
        meds = []
        for name, pl in planes.items():
            pl = pl.astype(np.float32)
            med = float(np.median(pl))
            sig = float(MAD_TO_SIGMA * np.median(np.abs(pl - med)))
            per_plane[name]["med"].append(med)
            per_plane[name]["sig"].append(sig)
            meds.append(med)
            # the floor is one quantiser step: a clipped plane has MAD 0, and
            # "5 x nothing above the median" would call every stuck pixel bright
            n, nh, nv = spatial.bright_pixels(pl, med + spatial.TAIL_K * max(sig, 1.0))
            n_tot += n
            n_h += nh
            n_v += nv
            n_px += pl.size
        block_meds.append(float(np.mean(meds)))

    med = {p: float(np.median(per_plane[p]["med"])) for p in spatial.PLANES}
    sig = {p: float(np.median(per_plane[p]["sig"])) for p in spatial.PLANES}
    level = float(np.mean(list(med.values())))
    sample = np.concatenate([b.ravel() for b in blocks])

    feats = {
        "level": level,
        "sigma": float(np.mean(list(sig.values()))),
        # large-scale structure: vignetting, amp glow, sky gradient
        "block_spread": float((max(block_meds) - min(block_meds)) / max(level, 1.0)),
        "tail_frac": n_tot / max(n_px, 1),
        # weaker axis: a star clumps both ways, a hot column only vertically
        "clump_frac": min(n_h, n_v) / max(n_tot, 1),
        "clump_h": n_h / max(n_tot, 1),
        "clump_v": n_v / max(n_tot, 1),
        # measured above, on the stored values, before the conversion
        "mult16_frac": mult16_frac,
        "sat_frac": float(np.mean(sample >= ADC_FULL_SCALE)),
    }
    for p in spatial.PLANES:
        feats["med_" + p.lower()] = med[p]
        feats["sig_" + p.lower()] = sig[p]
    return feats


def classify(features, exptime):
    """Decide the frame type from the pixels (D18).

    Order matters.  Exposure is a trusted capture setting, so the bias case is
    settled before any pixel argument is made.  Level separates flats, which sit
    an order of magnitude above the pedestal.  What remains -- dark or light at
    the same exposure and pedestal -- is separated by whether its bright pixels
    are blobs (a PSF) or isolated sites (hot pixels).
    """
    if exptime is not None and float(exptime) <= BIAS_MAX_EXPTIME:
        return "bias"

    bright = (features["level"] >= FLAT_MIN_LEVEL * ADC_FULL_SCALE
              or features["sat_frac"] >= SATURATED_FRAC)
    if bright:
        # A frame sitting far above the pedestal saw a lot of light.  Level
        # alone cannot say what kind: a flat panel and a twilight sky look the
        # same, and once clipped every other feature is degenerate too (sigma
        # and clump go to zero).  So this branch is an *inference*, not a
        # measurement, and it leans on the one thing left -- a capture setting,
        # which D18 keeps trusted.  Every flat in this archive is 1-3 s, so a
        # bright long exposure is sky, not a panel: a light that ran into dawn
        # or started in twilight.  Saturation stays recorded in `sat_frac`, a
        # quality attribute orthogonal to what the frame is (D25, D27).
        return "flat" if float(exptime) <= FLAT_MAX_EXPTIME else "light"

    if (features["clump_frac"] >= LIGHT_MIN_CLUMP
            and features["tail_frac"] >= LIGHT_MIN_TAIL):
        return "light"
    return "dark"

