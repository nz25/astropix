"""Pixels to numbers, and the frame verdict those numbers support.

Nothing here opens a file.  Everything takes arrays and returns numbers, which
is why almost all of it is testable without a FITS file, a Z: mount, or a sky.

Two layers:

1.  `frame_features` reduces sampled blocks to numbers describing one frame,
    every statistic per CFA sub-plane (D4).
2.  `classify` turns one of those numbers plus two trusted inputs -- the
    exposure time, and the pedestal for the frame's gain -- into a frame type
    (D18, D50).

**Units are ADC counts** -- see the units rule in `CLAUDE.md` (D41).  `to_adc`
is the only conversion in the project, and `frame_features` applies it once,
after checking the container is the one we think it is.  Everything downstream
of that line is in counts; nothing below needs to remember a factor of 16.

**Only `level` is read by the classifier.**  Everything else `frame_features`
returns is description: it exists to make the corpus queryable and to be
explained in notebook `02`, and no branch below consults it.  That is a
deliberate narrowing (D50) -- the classifier used to argue from bright-pixel
shape, and that argument failed exactly where it mattered most.

`frame_features` also returns a whole-frame summary -- `mean`, `median`, `min`,
`max`, `std` over the pooled sample.  **`std` there is across the CFA planes and
is therefore dominated by channel balance**, not by noise: across the archive it
runs a median 14.5x `sigma` on flats and 10.3x on lights, while on bias and dark
-- which have no colour -- the two agree at 0.6-1.2x.  `sigma` is the
uncontaminated per-plane counterpart, and the two sit side by side so that gap
can be seen rather than asserted.  It is the whole reason D4 exists.

**The `sigma` here is MAD, and MAD is the wrong estimator for noise.** MAD is an
order statistic of quantised deviations, so it can only return multiples of
1.4826 counts -- one quantiser step -- and read noise on this rig lives below
that (D24, whose arithmetic is in the older stored units).  It is kept as a
*description* of a frame's per-plane scale, and because a calibration frame
whose MAD has left the floor has something wrong with it: across 2,497
zero-light frames in the archive exactly one does, and it is also the one with
structure and colour it should not have.  It is not a noise measurement and
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
FLAT_MIN_LEVEL = 0.15       # fraction of full scale above pedestal, so unit-free
FLAT_MAX_EXPTIME = 5.0      # s; measured -- every flat in the archive is 1-3 s
DARK_MAX_ABOVE_PEDESTAL = 1.5    # counts; the archive gap runs 1.00 -> 1.75 (D50)

# --- quality, not type (D25, D27) --------------------------------------------
SATURATED_FRAC = 0.5        # clipped everywhere; recorded, never classified on


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


def value_step(a):
    """The modal spacing between adjacent distinct values in one CFA plane.

    On this rig it must be 16: the ADC produces 12 bits and the container
    stores them shifted, so nothing between two stored codes exists.  The
    number is a *fingerprint*, and the thing it fingerprints is white balance
    (L01).  The camera ships `WB_R=55`, `WB_B=75` and applies them to RAW16
    before the data reaches us, which multiplies each plane by a different
    factor and smears the step: greens stay at 16 while red reads 17 or 18 and
    blue reads 24.  That inflated read noise by ~17% at every gain, and it is
    invisible in every other statistic.

    Per plane, never on the mosaic -- pooling four differently-scaled planes
    gives a step of 1 and tells you nothing.  Take it on a zero-light frame,
    where the distribution is narrow enough that adjacent codes are all
    populated.
    """
    u = np.unique(np.asarray(a))
    if u.size < 2:
        raise ValueError("need at least two distinct values to measure a step")
    gaps, counts = np.unique(np.diff(u.astype(np.int64)), return_counts=True)
    return int(gaps[np.argmax(counts)])


def frame_features(blocks):
    """Reduce sampled blocks to the numbers the index stores about one frame.

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
        block_meds.append(float(np.mean(meds)))

    med = {p: float(np.median(per_plane[p]["med"])) for p in spatial.PLANES}
    sig = {p: float(np.median(per_plane[p]["sig"])) for p in spatial.PLANES}
    level = float(np.mean(list(med.values())))
    sample = np.concatenate([b.ravel() for b in blocks]).astype(np.float32)

    feats = {
        # the only number `classify` reads
        "level": level,
        # Whole-frame summary, pooled across planes and blocks.  Context, not
        # evidence.  `std` in particular is a mixture of four colour
        # populations -- see the module docstring.
        "mean": float(sample.mean()),
        "median": float(np.median(sample)),
        "min": float(sample.min()),
        "max": float(sample.max()),
        "std": float(sample.std()),
        # the denominator behind every number in this row: the frame is
        # sampled, not read whole, so it will not match a full-frame tool
        "sampled_px": int(sample.size),
        "sigma": float(np.mean(list(sig.values()))),
        # large-scale structure: vignetting, amp glow, sky gradient
        "block_spread": float((max(block_meds) - min(block_meds)) / max(level, 1.0)),
        # measured above, on the stored values, before the conversion
        "mult16_frac": mult16_frac,
        "sat_frac": float(np.mean(sample >= ADC_FULL_SCALE)),
    }
    # Per-plane *medians* are stored; per-plane *spreads* are not.  Both are
    # computed per plane, because D4 is about how a statistic is computed and
    # not about how many columns it becomes.  The medians earn a column each:
    # they are the index's only colour, `level` is exactly their mean, and a
    # calibration frame whose planes disagree has a light leak.  The spreads
    # do not: across 2,497 zero-light frames the four are identical to the
    # digit in every single one, so `sigma` -- their mean -- loses nothing.
    for p in spatial.PLANES:
        feats["med_" + p.lower()] = med[p]
    return feats


def _known(x):
    """A header value, or None if there isn't one.  None and NaN mean the same
    thing here and must not be told apart by the caller."""
    if x is None:
        return None
    x = float(x)
    return None if np.isnan(x) else x


def classify(features, exptime, pedestal):
    """Decide the frame type from one measured number and two trusted inputs (D50).

    The whole argument is **how far the frame sits above its pedestal**, which
    is what "how much light reached the sensor" means once the offset the
    camera adds has been taken off.  Working from a difference rather than a
    level is what lets the same three thresholds hold at every gain.

    Order matters.  Exposure is a trusted capture setting, so the bias case is
    settled before any pixel argument is made.  A flat sits three orders of
    magnitude above the pedestal at an exposure of seconds; a frame that bright
    at minutes is sky, not a panel.  What remains is dark or light, and the
    archive separates them cleanly: 2,177 darks reach at most pedestal + 1.00
    counts, and 10,465 lights start at pedestal + 1.75.

    **`light` is the fallback, deliberately.**  Every frame the earlier
    branches do not claim lands there, because that is the harmless direction:
    a light wrongly called dark enters a calibration master and is subtracted
    from every science frame, while a dark wrongly called light is thrown out
    by registration.

    **Domain of validity.**  The dark branch holds only while dark current
    stays below the quantiser floor, which on this rig it does -- 480 s darks
    sit on the pedestal to the digit, identical to 3 s darks, at -20 and -10 C
    (L14).  Warm the sensor far enough and darks will climb into the gap; this
    function would then need a per-exposure allowance and is wrong without one.

    `pedestal` is the zero-light level for *this frame's gain*, in ADC counts,
    measured from bias frames -- which are settled by exposure alone, so there
    is no circularity.  It is a parameter rather than a constant because it is
    not a number this project has measured to publication standard yet, and
    because baking in the two gains the archive happens to use would break on
    the third.  Passing `None` returns "unknown" rather than guessing.
    """
    # A missing header value arrives as None from a header and as NaN from a
    # CSV round-trip.  Both mean "not known", and neither may reach a
    # comparison, because every comparison against NaN is False and the frame
    # would slide down to the terminal `light` on no evidence at all.
    exptime = _known(exptime)
    pedestal = _known(pedestal)
    if exptime is not None and exptime <= BIAS_MAX_EXPTIME:
        return "bias"
    if exptime is None or pedestal is None:
        return "unknown"

    above = features["level"] - pedestal
    if above >= FLAT_MIN_LEVEL * ADC_FULL_SCALE and exptime <= FLAT_MAX_EXPTIME:
        return "flat"
    if above <= DARK_MAX_ABOVE_PEDESTAL:
        return "dark"
    return "light"
