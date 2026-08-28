"""stats.py -- reducing sampled blocks to features, and the frame verdict."""

import os

import numpy as np
from astropy.io import fits as _afits

from astropix import fits as F
from astropix import stats

from .synthetic import SENSOR_CEILING, STEP, tmp_frame, tmpdir, write_frame


# --------------------------------------------------------------------------
# units -- the one conversion in the project (CLAUDE.md, D41)
# --------------------------------------------------------------------------

def test_to_adc_is_exact_and_stays_integer():
    stored = np.array([0, 16, 1232, 65520], np.uint16)
    counts = stats.to_adc(stored)
    assert np.array_equal(counts, [0, 1, 77, stats.ADC_FULL_SCALE])
    assert np.issubdtype(counts.dtype, np.integer), "must not silently become float"


def test_to_adc_refuses_rather_than_truncates():
    """A value with low bits set did not come from this camera's raw path.
    Shifting it away would turn a file we do not understand into a plausible
    number, which is the failure this project keeps legislating against."""
    try:
        stats.to_adc(np.array([1232, 1233], np.uint16))
    except ValueError:
        return
    raise AssertionError("to_adc accepted a value that is not a multiple of 16")


def test_features_come_back_in_adc_counts():
    """The synthetic dark is written at a stored level of 1232; measured, it
    must read 77 -- the same pedestal in the project's unit."""
    blocks, _ = F.sample_blocks(tmp_frame("dark"))
    feats = stats.frame_features(blocks)
    assert feats["level"] == 1232 / STEP
    assert feats["med_r"] == feats["med_b"] == 77.0
    assert feats["level"] <= stats.ADC_FULL_SCALE


def test_saturation_is_exact_at_full_scale():
    """65520 stored is 4095 counts -- the ceiling, with no fudge factor."""
    blocks, _ = F.sample_blocks(tmp_frame("saturated"))
    assert stats.frame_features(blocks)["sat_frac"] == 1.0
    assert SENSOR_CEILING >> stats.ADC_SHIFT == stats.ADC_FULL_SCALE


# --------------------------------------------------------------------------
# features
# --------------------------------------------------------------------------

def test_features_see_the_bit_shift():
    """Measured on the stored values, before the conversion it licenses."""
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
    twilight = {"level": 1250.0, "sat_frac": 0.0, "clump_frac": 0.0, "tail_frac": 0.0}
    assert stats.classify(twilight, 240.0) == "light"
    assert stats.classify(twilight, 3.0) == "flat"


def test_a_clipped_bias_is_still_a_bias():
    """Exposure settles bias before the clipping branch is reached."""
    feats = {"level": float(stats.ADC_FULL_SCALE), "sat_frac": 1.0,
             "clump_frac": 0.0, "tail_frac": 0.0}
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
    feats = {"level": 65.0, "sat_frac": 0.0, "clump_frac": 0.9, "tail_frac": 0.1}
    assert stats.classify(feats, 0.001) == "bias"
    assert stats.classify(feats, 60.0) == "light"
