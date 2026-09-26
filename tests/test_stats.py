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


# --------------------------------------------------------------------------
# the modal sky level (protocols/06-sky-pair.md, rule 3)
# --------------------------------------------------------------------------

def _sky_box(level, sigma, n=256, seed=0):
    """A quantised sky core: Gaussian noise on the ADC's integer grid."""
    rng = np.random.default_rng(seed)
    return np.rint(rng.normal(level, sigma, (n, n)))


def test_sky_level_recovers_a_known_background():
    """The whole point of the estimator: on a clean symmetric core it must
    agree with the mean it was built from, well inside the ADC's own spacing."""
    for level in (100.0, 100.4, 277.7):
        got = stats.sky_level(_sky_box(level, 2.6))
        assert abs(got - level) < 0.25, f"{got} vs {level}"


def test_sky_level_beats_mean_and_median_on_a_contaminated_box():
    """Rule 3's reason, as a test, with both contaminants it names.

    Stars are a few bright pixels and they wreck the *mean*; a median shrugs
    them off, which is why the rule does not stop at the median.  What the
    median cannot survive is unresolved nebulosity -- faint light over a large
    fraction of the box, which is exactly what a sky ROI on a nebula field
    has in it.  The mode follows neither.
    """
    rng = np.random.default_rng(2)
    box = _sky_box(100.0, 2.6, seed=1)
    nebula = rng.random(box.shape) < 0.3         # 30% carries a faint pedestal
    box = box + nebula * rng.uniform(2.0, 6.0, box.shape)
    star = rng.random(box.shape) < 0.002         # and a sparse, bright star field
    box = box + star * rng.uniform(500, 3000, box.shape)

    mode = stats.sky_level(box)
    assert abs(mode - 100.0) < 0.5, f"mode dragged to {mode}"
    assert float(np.median(box)) - 100.0 > 0.9, "the median should be dragged"
    assert float(box.mean()) - 100.0 > 2.0, "the mean should be dragged harder"


def test_sky_level_resolves_inside_one_adc_count():
    """A 30 s sub at gain 50 puts the whole core inside about five codes, so
    the bare peak bin quantises F_sky at ~0.8 sigma.  The parabola is what
    makes a sub-count shift measurable rather than rounded away."""
    fine = [stats.sky_level(_sky_box(100.0 + d, 1.3, seed=3)) for d in (0.0, 0.4)]
    assert 0.15 < fine[1] - fine[0] < 0.65, fine
    assert fine[0] != fine[1]


def test_sky_level_refuses_a_box_too_small_to_have_a_mode():
    try:
        stats.sky_level(np.full((8, 8), 100.0))
    except ValueError:
        return
    raise AssertionError("expected ValueError on a box with too few pixels")


# --------------------------------------------------------------------------
# the offset state (protocols/04-offset-state.md, rule 1)
# --------------------------------------------------------------------------
#
# Session 03 detected the state against a fixed 0.5-count threshold, which is
# only right if the step is ~1 count.  Session 04 exists to test the step
# against gain, so these check that the rule finds the step it is given rather
# than the step it was written against.

def _two_states(step, n_far=4, n=100, scatter=0.01, seed=0):
    """A peer group: `n` levels around 76.66 counts, `n_far` of them one state up."""
    rng = np.random.default_rng(seed)
    levels = 76.66 + rng.normal(0, scatter, n)
    levels[:n_far] += step
    return levels


def test_the_step_is_measured_and_not_assumed():
    """H2 predicts 9.93 counts at gain 450 and H1 predicts 0.993 everywhere.
    A rule that only finds one of them cannot separate the hypotheses."""
    for step in (0.9931, 9.931, 0.154):
        found = stats.offset_state(_two_states(step))
        assert abs(found["separation"] - step) < 0.01, step
        assert found["far"].sum() == 4, step


def test_one_state_is_not_split_into_two():
    """The null outcome is pre-registered: three hours and no state at all.
    It must come back as no state, not as a separation invented from noise."""
    found = stats.offset_state(_two_states(0.0, n_far=0))
    assert found["separation"] is None
    assert not found["far"].any()
    assert found["worst_steps"] is None


def test_the_floor_binds_when_the_step_is_small():
    """At gain 0 H2 predicts 0.154 counts.  Against a scatter of 0.02 the two
    states are 7.7 sigma apart, so they resolve -- but half the separation
    would put the threshold under 4 sigma and admit noise as a state.  The
    floor, not the separation, is what the threshold must be there."""
    found = stats.offset_state(_two_states(0.154, scatter=0.02))
    assert found["separation"] is not None
    assert found["threshold"] == stats.STATE_FLOOR_SIGMAS * found["scatter"]
    assert found["threshold"] > found["separation"] / 2


def test_a_step_inside_the_scatter_is_reported_as_no_state():
    """The resolution limit, made explicit.  H2 at gain 0 predicts 0.154 counts
    and this session must be able to tell "no state" from "a state I cannot
    see": a group whose states sit closer than the clustering gap comes back
    with no separation, and the notebook quotes the limit beside the null
    rather than reporting a measured zero."""
    found = stats.offset_state(_two_states(0.154, scatter=0.05))
    assert found["separation"] is None
    assert found["threshold"] == stats.STATE_FLOOR_SIGMAS * found["scatter"]


def test_a_third_state_announces_itself_in_units_of_the_step():
    """Rule 4: a departure of two steps is a pre-registered outcome.  The
    separation must stay the unit even when a state in between is unoccupied."""
    levels = _two_states(0.993, n_far=4)
    levels[:2] += 0.993                       # two frames two steps out
    found = stats.offset_state(levels)
    assert abs(found["separation"] - 0.993) < 0.02
    assert round(found["worst_steps"]) == 2
    assert sorted(set(found["state"].tolist())) == [0, 1, 2]


def test_the_scatter_is_within_state_and_not_across_states():
    """The floor is 5x the *within*-state scatter.  Pooling the far frames into
    it would inflate it by the step and disable the floor exactly where the
    step is small, which is where the floor is the only thing protecting it."""
    found = stats.offset_state(_two_states(0.993, n_far=20, scatter=0.01))
    assert found["scatter"] < 0.02, found["scatter"]


def test_a_peer_group_too_small_to_have_a_median_refuses():
    try:
        stats.offset_state([76.6, 76.7])
    except ValueError:
        return
    raise AssertionError("two frames are not a peer group")



# --------------------------------------------------------------------------
# contract 3: noise from a difference, at a scale
# --------------------------------------------------------------------------

def test_bin_mean_averages_blocks_and_drops_the_ragged_edge():
    a = np.arange(5 * 9, dtype=float).reshape(5, 9)
    got = stats.bin_mean(a, 4)
    assert got.shape == (1, 2)
    assert got[0, 0] == a[:4, :4].mean() and got[0, 1] == a[:4, 4:8].mean()


def test_diff_sigma_recovers_injected_noise_under_any_shared_signal():
    """The signal is everywhere in a light, so the estimator must not see it:
    a star field and a gradient shared by both images, plus a sky offset and
    a tilt that differ between them, and still the injected sigma back."""
    rng = np.random.default_rng(3)
    yy, xx = np.indices((512, 512))
    scene = 50 * np.exp(-((xx - 200) ** 2 + (yy - 300) ** 2) / 50.0) + 0.1 * xx
    a = scene + rng.normal(0, 5.0, scene.shape)
    b = scene + 3.0 + 0.002 * yy + rng.normal(0, 5.0, scene.shape)
    assert abs(stats.diff_sigma(a, b, 1) / 5.0 - 1) < 0.02
    assert abs(stats.diff_sigma(a, b, 4) / (5.0 / 4) - 1) < 0.05, (
        "white noise averages over 16 pixels to a quarter")


def test_diff_sigma_sees_correlated_noise_that_a_pixel_spread_hides():
    """Why contract 3 bins, and why binning alone is not enough.  Smooth white
    noise with [1/4, 1/2, 1/4] each way -- linear interpolation at a half-pixel
    shift, the worst case -- and the per-pixel spread falls to sqrt(3/8)^2 =
    0.375 of the truth.  A 4x4 block recovers most of it, because a kernel
    that sums to one moves noise between neighbours rather than removing it;
    only what leaks across the block edges is lost, and in 1-D that leaves a
    variance of 3.25 of 4.  So the binned spread reads 0.8125, not 1."""
    rng = np.random.default_rng(4)
    raw = [rng.normal(0, 5.0, (512, 512)) for _ in range(2)]
    k = np.array([0.25, 0.5, 0.25])
    smooth = [np.apply_along_axis(np.convolve, 0,
                                  np.apply_along_axis(np.convolve, 1, r, k, "same"),
                                  k, "same") for r in raw]
    pix = stats.diff_sigma(*smooth, 1) / stats.diff_sigma(*raw, 1)
    binned = stats.diff_sigma(*smooth, 4) / stats.diff_sigma(*raw, 4)
    assert abs(pix - 0.375) < 0.02, "the per-pixel spread is fooled"
    assert abs(binned - 0.8125) < 0.03, "the binned spread much less so"


def test_diff_sigma_is_not_fooled_by_whole_counts_or_stars():
    """Two raw frames: integers, a sigma of 1.2 counts -- well under the MAD's
    1.4826-count grid -- and a scatter of bright stars that did not line up,
    as in an unregistered pair.  The quantisation noise is real and stays in
    (sqrt(1.2^2 + 1/12)); the stars are clipped out."""
    rng = np.random.default_rng(6)
    a = np.rint(100 + rng.normal(0, 1.2, (256, 256)))
    b = np.rint(100 + rng.normal(0, 1.2, (256, 256)))
    a[rng.integers(0, 256, 300), rng.integers(0, 256, 300)] += 500
    b[rng.integers(0, 256, 300), rng.integers(0, 256, 300)] += 500
    assert abs(stats.diff_sigma(a, b, 1) / np.hypot(1.2, np.sqrt(1 / 12)) - 1) < 0.02


def test_diff_sigma_refuses_too_few_pixels():
    try:
        stats.diff_sigma(np.zeros((40, 40)), np.zeros((40, 40)), 4)
    except ValueError:
        return
    raise AssertionError("100 binned pixels is not a spread")


def test_extended_signal_is_level_above_sky_and_ignores_stars():
    rng = np.random.default_rng(5)
    sky = 100 + rng.normal(0, 2, (64, 64))
    sig = 112 + rng.normal(0, 2, (64, 64))
    sig[::8, ::8] = 4000
    assert abs(stats.extended_signal(sig, sky) - 12) < 0.3
