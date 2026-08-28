"""stats.py -- reducing sampled blocks to features, and the frame verdict."""

import os

import numpy as np
from astropy.io import fits as _afits

from astropix import fits as F
from astropix import stats

from . import synthetic
from .synthetic import (PEDESTAL, SENSOR_CEILING, STEP, tmp_frame, tmpdir,
                        write_frame)


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


def test_summary_stats_are_in_counts_and_bracket_the_frame():
    """The whole-frame summary shares the row's unit and the row's sample."""
    blocks, _ = F.sample_blocks(tmp_frame("dark"))
    f = stats.frame_features(blocks)
    assert f["min"] <= f["median"] <= f["max"] <= stats.ADC_FULL_SCALE
    assert f["median"] == 1232 / STEP          # the pedestal, in counts
    assert f["sampled_px"] == sum(b.size for b in blocks)


def test_pooled_std_is_channel_balance_not_noise():
    """The reason D4 is a rule and not a preference.

    Two blocks of identical noise; the second has an ordinary OSC channel
    imbalance laid over it.  `sigma` is unmoved, because it is measured inside
    each plane and each plane still sees only its own pixels.  The pooled `std`
    is not, because it is now measuring the distance between colours.  Anything
    that fed `std` to a noise fit would read that imbalance as read noise.
    """
    flat = np.full((64, 64), 1600, np.uint16)
    flat[::2, 1::2] = flat[1::2, ::2] = 1600      # G1, G2
    colour = flat.copy()
    colour[::2, ::2] = 800                        # R, half the green level
    colour[1::2, 1::2] = 960                      # B

    neutral = stats.frame_features([flat])
    skewed = stats.frame_features([colour])
    assert neutral["std"] == skewed["sigma"] == 0.0, "noiseless by construction"
    assert skewed["std"] > 10.0, "the colour offset has to show up somewhere"


def test_the_classifier_reads_level_and_nothing_else():
    """D50 in one assertion.  `classify` used to argue from bright-pixel shape,
    and the argument failed on exactly the frames with the most signal.  It now
    reads one feature, so a features dict carrying only `level` must be enough
    -- and a missing `level` must raise rather than fall through to a default.
    """
    assert stats.classify({"level": 300.0}, 60.0, PEDESTAL) == "light"
    try:
        stats.classify({"sigma": 1.4826, "sat_frac": 0.0}, 60.0, PEDESTAL)
    except KeyError:
        return
    raise AssertionError("classify reached a verdict without a level")


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------

def test_every_type_classifies_as_itself():
    for kind in ("bias", "dark", "flat", "light"):
        rec = F.scan_frame(tmp_frame(kind), pedestal=PEDESTAL)
        assert rec["measured_type"] == kind, (kind, rec["measured_type"],
                                              rec["level"], PEDESTAL)


def test_the_dark_light_boundary_is_where_the_archive_put_it():
    """The gap the whole rule rests on: 2,177 archive darks reach at most
    pedestal + 1.00 counts and 10,465 lights start at pedestal + 1.75, so the
    threshold sits between them.  Half a count either side of it must decide."""
    k = stats.DARK_MAX_ABOVE_PEDESTAL
    assert stats.classify({"level": PEDESTAL + k}, 60.0, PEDESTAL) == "dark"
    assert stats.classify({"level": PEDESTAL + k + 0.25}, 60.0, PEDESTAL) == "light"
    assert 1.0 < k < 1.75, "the threshold must sit inside the measured gap"


def test_the_pedestal_is_what_makes_the_rule_gain_free():
    """Identical pixels, two gains, two pedestals, two different answers.  This
    is why the pedestal is an argument and not a constant: 77 counts is a dark
    at gain 252 and a light at gain 50, and only the pedestal knows which."""
    frame = {"level": 77.0}
    assert stats.classify(frame, 60.0, 77.0) == "dark"
    assert stats.classify(frame, 60.0, 65.0) == "light"


def test_an_unknown_pedestal_refuses_rather_than_guesses():
    """A gain with no bias frame behind it cannot be classified.  Saying so is
    the point; defaulting to `dark` is how 484 lights got into the last index."""
    assert stats.classify({"level": 500.0}, 60.0, None) == "unknown"
    # exposure still settles bias, because it needs no pedestal at all
    assert stats.classify({"level": 500.0}, 0.001, None) == "bias"


def test_a_missing_header_value_cannot_slide_into_the_fallback():
    """The trap in a `light`-by-default classifier: every comparison against
    NaN is False, so an unreadable exposure would fall past both branches and
    be published as a light.  A CSV round-trip turns a missing header into NaN
    rather than None, so both spellings have to be caught."""
    for nothing in (None, float("nan")):
        assert stats.classify({"level": 500.0}, nothing, PEDESTAL) == "unknown"
        assert stats.classify({"level": 500.0}, 60.0, nothing) == "unknown"


def test_a_clipped_frame_falls_back_on_exposure():
    """Identical pixels, different exposures, different answers.

    A clipped frame has no pixel evidence left -- level pins to full scale --
    so this branch is an inference and the test pins down exactly what it
    infers from.  Every flat in the archive is 1-3 s, so a clipped long
    exposure is a light that ran into dawn.
    """
    dawn = F.scan_frame(tmp_frame("saturated"), pedestal=PEDESTAL)
    blown = F.scan_frame(tmp_frame("blown_flat"), pedestal=PEDESTAL)
    assert dawn["sat_frac"] == blown["sat_frac"] == 1.0
    assert dawn["level"] == blown["level"]
    assert dawn["measured_type"] == "light"
    assert blown["measured_type"] == "flat"


def test_saturation_stays_recoverable_as_a_quality_flag():
    """`sat_frac` is no longer read by `classify` at all (D50), which makes it
    purely a quality column -- and the one downstream excludes on.  It must
    still be measured and stored."""
    rec = F.scan_frame(tmp_frame("saturated"), pedestal=PEDESTAL)
    assert rec["sat_frac"] >= stats.SATURATED_FRAC
    assert F.scan_frame(tmp_frame("light"), pedestal=PEDESTAL)["sat_frac"] \
        < stats.SATURATED_FRAC


def test_a_bright_long_exposure_is_twilight_not_a_flat():
    """Found in the ladder: 64 frames at gain 252 / 240-480 s sit above the flat
    level cut without clipping.  They are dawn sky, not a panel, and level alone
    cannot tell the difference -- exposure can."""
    twilight = {"level": 1250.0}
    assert stats.classify(twilight, 240.0, PEDESTAL) == "light"
    assert stats.classify(twilight, 3.0, PEDESTAL) == "flat"


def test_a_clipped_bias_is_still_a_bias():
    """Exposure settles bias before any pixel argument is reached."""
    feats = {"level": float(stats.ADC_FULL_SCALE)}
    assert stats.classify(feats, 0.001, PEDESTAL) == "bias"


def test_the_label_is_evidence_not_truth():
    """D18: a flat captured under a Light subframe type must still read as a
    flat, and the disagreement must be recorded rather than resolved."""
    path = os.path.join(tmpdir(), "mislabelled.fit")
    write_frame(path, "flat")
    with _afits.open(path, mode="update") as hdul:
        hdul[0].header["IMAGETYP"] = "Light"
    rec = F.scan_frame(path, pedestal=PEDESTAL)
    assert rec["measured_type"] == "flat"
    assert rec["declared_type"] == "light"
    assert rec["type_agrees"] is False


# --------------------------------------------------------------------------
# value_step -- the white-balance fingerprint (L01)
# --------------------------------------------------------------------------

def test_value_step_is_16_on_this_rigs_raw_output():
    plane = synthetic.make_frame("bias")[0][::2, ::2]
    assert stats.value_step(plane) == 16


def test_value_step_catches_white_balance_still_being_applied():
    """The tell is greens at 16 while red reads 17-18 and blue reads 24: the
    camera ships WB_R=55, WB_B=75 and applies them to RAW16 before the data
    reaches us, which inflated read noise ~17% at every gain."""
    green = synthetic.make_frame("bias")[0][::2, ::2].astype(np.float64)
    assert stats.value_step(green.astype(np.int64)) == 16
    # Red is quoted as 17 *or* 18 because 55/50 does not divide the grid
    # evenly -- the gaps alternate and the mode is a tie-break, not a
    # constant.  What the gate needs is only that it has left 16.
    for factor, expected in ((55 / 50, {17, 18}), (75 / 50, {24})):
        scaled = np.round(green * factor).astype(np.int64)
        assert stats.value_step(scaled) in expected


def test_value_step_refuses_a_plane_with_nothing_to_measure():
    try:
        stats.value_step(np.full((4, 4), 1232, np.uint16))
    except ValueError:
        return
    raise AssertionError("expected ValueError")
