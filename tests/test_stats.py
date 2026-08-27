"""stats.py -- reducing sampled blocks to features, and the frame verdict."""

import os

import numpy as np
from astropy.io import fits as _afits

from astropix import fits as F
from astropix import stats

from .synthetic import STEP, tmp_frame, tmpdir, write_frame


# --------------------------------------------------------------------------
# features
# --------------------------------------------------------------------------

def test_features_see_the_bit_shift():
    blocks, _ = F.sample_blocks(tmp_frame("dark"))
    assert stats.frame_features(blocks)["mult16_frac"] == 1.0


def test_features_separate_stars_from_hot_pixels():
    dark = stats.frame_features(F.sample_blocks(tmp_frame("dark"))[0])
    light = stats.frame_features(F.sample_blocks(tmp_frame("light"))[0])
    assert dark["clump_frac"] < stats.LIGHT_MIN_CLUMP <= light["clump_frac"]
    assert dark["tail_frac"] > 0, "hot pixels should still register as a tail"


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------

def test_every_type_classifies_as_itself():
    for kind in ("bias", "dark", "flat", "light"):
        rec = F.scan_frame(tmp_frame(kind))
        assert rec["measured_type"] == kind, (kind, rec["measured_type"], rec["level"],
                                              rec["clump_frac"], rec["tail_frac"])


def test_a_clipped_frame_falls_back_on_exposure():
    """Identical pixels, different exposures, different answers.

    A clipped frame has no pixel evidence left -- level pins to full scale,
    sigma and clump to zero -- so this branch is an inference and the test
    pins down exactly what it infers from.  Every flat in the archive is 1-3 s,
    so a clipped long exposure is a light that ran into dawn.
    """
    dawn = F.scan_frame(tmp_frame("saturated"))
    blown = F.scan_frame(tmp_frame("blown_flat"))
    assert dawn["sat_frac"] == blown["sat_frac"] == 1.0
    assert dawn["level"] == blown["level"]
    assert dawn["measured_type"] == "light"
    assert blown["measured_type"] == "flat"


def test_saturation_stays_recoverable_as_a_quality_flag():
    """Folding saturation into the type must not lose it: sat_frac is what
    downstream excludes on, and it is a stored column."""
    rec = F.scan_frame(tmp_frame("saturated"))
    assert rec["sat_frac"] >= stats.SATURATED_FRAC
    assert F.scan_frame(tmp_frame("light"))["sat_frac"] < stats.SATURATED_FRAC


def test_a_bright_long_exposure_is_twilight_not_a_flat():
    """Found in the ladder: 64 frames at gain 252 / 240-480 s sit above the flat
    level cut without clipping.  They are dawn sky, not a panel, and level alone
    cannot tell the difference -- exposure can."""
    twilight = {"level": 20000.0, "sat_frac": 0.0, "clump_frac": 0.0, "tail_frac": 0.0}
    assert stats.classify(twilight, 240.0) == "light"
    assert stats.classify(twilight, 3.0) == "flat"


def test_a_clipped_bias_is_still_a_bias():
    """Exposure settles bias before the clipping branch is reached."""
    feats = {"level": 65520.0, "sat_frac": 1.0, "clump_frac": 0.0, "tail_frac": 0.0}
    assert stats.classify(feats, 0.001) == "bias"


def test_the_label_is_evidence_not_truth():
    """D18: a flat captured under a Light subframe type must still read as a
    flat, and the disagreement must be recorded rather than resolved."""
    path = os.path.join(tmpdir(), "mislabelled.fit")
    write_frame(path, "flat")
    with _afits.open(path, mode="update") as hdul:
        hdul[0].header["IMAGETYP"] = "Light"
    rec = F.scan_frame(path)
    assert rec["measured_type"] == "flat"
    assert rec["declared_type"] == "light"
    assert rec["type_agrees"] is False


def test_exposure_decides_bias_before_any_pixel_argument():
    feats = {"level": 1040.0, "sat_frac": 0.0, "clump_frac": 0.9, "tail_frac": 0.1}
    assert stats.classify(feats, 0.001) == "bias"
    assert stats.classify(feats, 60.0) == "light"
