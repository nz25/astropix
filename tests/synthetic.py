"""Synthetic frames, and the temp directory they live in.

Each frame is built to have the *feature* its type is defined by rather than
to look pretty -- a star is a connected blob, a hot pixel is not, and a bias
is short.  That is what the classifier is being asked about.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile

import numpy as np
from astropy.io import fits as _afits

from astropix import stats

RNG = np.random.default_rng(20260827)

# Synthetic frames are written in **stored** units, on purpose: a synthetic FITS
# has to look like what the camera writes, or it stops exercising the conversion
# `frame_features` performs.  Features measured from them come back in ADC
# counts, 16x smaller (CLAUDE.md, D41).
STEP = 1 << stats.ADC_SHIFT
SENSOR_CEILING = stats.ADC_FULL_SCALE * STEP     # 65520 -- what the sensor can produce

_TMP = None
_CACHE = {}


def tmpdir():
    """One temp directory for the whole run, cleaned up at exit."""
    global _TMP
    if _TMP is None:
        _TMP = tempfile.mkdtemp(prefix="astropix-test-")
        atexit.register(shutil.rmtree, _TMP, ignore_errors=True)
    return _TMP


def tmp_frame(kind):
    """A written frame of `kind`, made once and reused."""
    if kind not in _CACHE:
        _CACHE[kind] = write_frame(os.path.join(tmpdir(), kind + ".fit"), kind)
    return _CACHE[kind]


def _quantised(base, sigma, shape):
    """Noise on the ADC grid: values are always exact multiples of 16, because
    that is the only thing this camera can produce (see notebooks/01)."""
    x = RNG.normal(base, sigma, shape)
    return np.clip(np.round(x / STEP) * STEP, 0, SENSOR_CEILING).astype(np.uint16)


def make_frame(kind, shape=(128, 128)):
    """A frame of each type, built to have the *feature* each type is defined by
    rather than to look pretty."""
    ny, nx = shape
    if kind == "bias":
        return _quantised(1040, 24, shape), 0.001
    if kind == "flat":
        return _quantised(30000, 300, shape), 3.0
    if kind == "saturated":
        # a light that ran into dawn: long exposure, clipped everywhere
        return np.full(shape, SENSOR_CEILING, np.uint16), 15.0
    if kind == "blown_flat":
        # the same pixels, but at a flat's exposure
        return np.full(shape, SENSOR_CEILING, np.uint16), 3.0
    if kind == "dark":
        a = _quantised(1232, 100, shape)
        # hot pixels: isolated single sites, the thing a star is not
        a[7::37, 5::41] = 40000
        return a, 60.0
    if kind == "light":
        a = _quantised(2000, 100, shape)
        # stars: 4x4 in the mosaic, so 2x2 within each sub-plane -- connected
        # both horizontally and vertically, which is the discriminator
        for y in range(6, ny - 6, 24):
            for x in range(6, nx - 6, 24):
                a[y:y + 4, x:x + 4] = 20000
        return a, 60.0
    raise ValueError(kind)


def write_frame(path, kind, shape=(128, 128), gain=252, ccd_temp=-10.0):
    data, exptime = make_frame(kind, shape)
    hdu = _afits.PrimaryHDU(data)
    h = hdu.header
    h["IMAGETYP"] = kind.capitalize()
    h["EXPTIME"] = exptime
    h["EXPOSURE"] = exptime
    h["GAIN"] = gain
    h["OFFSET"] = 15
    h["SET-TEMP"] = -10
    h["CCD-TEMP"] = ccd_temp
    h["BAYERPAT"] = "RGGB"
    h["EGAIN"] = 0.516568422317505
    h["DATE-OBS"] = "2026-08-27T00:00:00"
    h["INSTRUME"] = "ZWO ASI585MC Pro"
    hdu.writeto(path, overwrite=True)
    return path

