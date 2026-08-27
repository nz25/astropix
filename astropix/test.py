"""Tests for the astropix library.

Not a seventh library module (D13's budget is about *modelling* code); this file
carries no physics and nothing imports it.

Everything here runs on synthetic frames written to a temp directory, so the
suite needs neither Z: nor clear sky, and it is safe to run while the archive is
frozen for a measurement (D19).

Run either way:

    python -m astropix.test          # no dependencies beyond the library
    pytest astropix/test.py          # if pytest happens to be installed
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import tempfile

import numpy as np
from astropy.io import fits as _afits

from . import cfa
from . import fits as F
from . import stats

RNG = np.random.default_rng(20260827)
STEP = 16          # the 12-bit ADC stored bit-shifted into 16-bit files


# --------------------------------------------------------------------------
# synthetic frames
# --------------------------------------------------------------------------

def _quantised(base, sigma, shape):
    """Noise on the ADC grid: values are always exact multiples of 16, because
    that is the only thing this camera can produce (see notebooks/01)."""
    x = RNG.normal(base, sigma, shape)
    return np.clip(np.round(x / STEP) * STEP, 0, F.FULL_SCALE).astype(np.uint16)


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
        return np.full(shape, F.FULL_SCALE - 15, np.uint16), 15.0
    if kind == "blown_flat":
        # the same pixels, but at a flat's exposure
        return np.full(shape, F.FULL_SCALE - 15, np.uint16), 3.0
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


# --------------------------------------------------------------------------
# cfa
# --------------------------------------------------------------------------

def test_split_takes_the_four_bayer_positions():
    a = np.arange(36).reshape(6, 6)
    p = cfa.split(a)
    assert set(p) == set(cfa.PLANES)
    assert all(v.shape == (3, 3) for v in p.values())
    # every mosaic pixel lands in exactly one plane, none twice
    got = sorted(int(v) for pl in p.values() for v in pl.ravel())
    assert got == list(range(36))
    assert p["R"][0, 0] == 0 and p["G1"][0, 0] == 1
    assert p["G2"][0, 0] == 6 and p["B"][0, 0] == 7


def test_split_returns_views_not_copies():
    """Views matter: the index splits thousands of blocks and must not copy."""
    a = np.zeros((4, 4), np.uint16)
    cfa.split(a)["R"][0, 0] = 5
    assert a[0, 0] == 5


def test_split_drops_an_odd_trailing_row_and_column():
    """All four planes must come back the same shape.  Plain striding on a 5x5
    would give (3,3), (3,2), (2,3), (2,2), which breaks anything that stacks
    them -- and would do it silently, on some other sensor, years from now."""
    p = cfa.split(np.zeros((5, 5)))
    assert {v.shape for v in p.values()} == {(2, 2)}
    assert {v.shape for v in cfa.split(np.zeros((2160, 3840))).values()} == {(1080, 1920)}


def test_split_rejects_what_it_cannot_handle():
    for bad, kwargs in [(np.zeros((4, 4)), {"pattern": "GRBG"}),
                        (np.zeros((4, 4, 3)), {})]:
        try:
            cfa.split(bad, **kwargs)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_label_planes_by_flux_finds_the_greens():
    """The two greens share a filter, so their medians agree most closely; R
    runs above B under broadband sky on this rig."""
    a = np.zeros((4, 4), np.uint16)
    a[0::2, 0::2] = 300      # R
    a[0::2, 1::2] = 500      # G1
    a[1::2, 0::2] = 505      # G2
    a[1::2, 1::2] = 200      # B
    labels, _ = cfa.label_planes_by_flux(cfa.split(a))
    assert labels == {"R": "R", "G1": "G1", "G2": "G2", "B": "B"}


def test_label_planes_by_flux_detects_a_row_flip():
    """A vertical flip swaps R and B.  The point of the check is that it says so
    instead of quietly mislabelling a colour."""
    a = np.zeros((4, 4), np.uint16)
    a[0::2, 0::2] = 200      # sits in the 'R' slot but holds blue
    a[0::2, 1::2] = 500
    a[1::2, 0::2] = 505
    a[1::2, 1::2] = 300
    labels, _ = cfa.label_planes_by_flux(cfa.split(a))
    assert labels["R"] == "B" and labels["B"] == "R"


# --------------------------------------------------------------------------
# features
# --------------------------------------------------------------------------

def test_bright_pixel_stats_separates_stars_columns_and_hot_pixels():
    """The whole dark/light decision rests on this function."""
    z = np.zeros((20, 20), np.float32)

    star = z.copy(); star[8:10, 8:10] = 100          # 2x2 blob
    n, h, v = F._bright_pixel_stats(star, 50)
    assert (n, h, v) == (4, 4, 4)

    hot = z.copy(); hot[3, 3] = 100; hot[11, 15] = 100
    n, h, v = F._bright_pixel_stats(hot, 50)
    assert (n, h, v) == (2, 0, 0)

    col = z.copy(); col[:, 7] = 100                  # hot column: v only
    n, h, v = F._bright_pixel_stats(col, 50)
    assert n == 20 and h == 0 and v == 20
    assert min(h, v) == 0, "the weaker axis must not mistake a column for stars"

    assert F._bright_pixel_stats(z, 50) == (0, 0, 0)


def test_features_see_the_bit_shift():
    blocks, _ = F.sample_blocks(_tmp_frame("dark"))
    assert F.frame_features(blocks)["mult16_frac"] == 1.0


def test_features_separate_stars_from_hot_pixels():
    dark = F.frame_features(F.sample_blocks(_tmp_frame("dark"))[0])
    light = F.frame_features(F.sample_blocks(_tmp_frame("light"))[0])
    assert dark["clump_frac"] < F.LIGHT_MIN_CLUMP <= light["clump_frac"]
    assert dark["tail_frac"] > 0, "hot pixels should still register as a tail"


def test_sample_blocks_reads_the_asked_for_geometry():
    blocks, header = F.sample_blocks(_tmp_frame("flat"), n_blocks=4, block_rows=16)
    assert len(blocks) == 4
    assert all(b.shape == (16, 128) for b in blocks)
    assert all(b.dtype == np.uint16 for b in blocks)
    assert header["GAIN"] == 252


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------

def test_every_type_classifies_as_itself():
    for kind in ("bias", "dark", "flat", "light"):
        rec = F.scan_frame(_tmp_frame(kind))
        assert rec["measured_type"] == kind, (kind, rec["measured_type"], rec["level"],
                                              rec["clump_frac"], rec["tail_frac"])


def test_a_clipped_frame_falls_back_on_exposure():
    """Identical pixels, different exposures, different answers.

    A clipped frame has no pixel evidence left -- level pins to full scale,
    sigma and clump to zero -- so this branch is an inference and the test
    pins down exactly what it infers from.  Every flat in the archive is 1-3 s,
    so a clipped long exposure is a light that ran into dawn.
    """
    dawn = F.scan_frame(_tmp_frame("saturated"))
    blown = F.scan_frame(_tmp_frame("blown_flat"))
    assert dawn["sat_frac"] == blown["sat_frac"] == 1.0
    assert dawn["level"] == blown["level"]
    assert dawn["measured_type"] == "light"
    assert blown["measured_type"] == "flat"


def test_saturation_stays_recoverable_as_a_quality_flag():
    """Folding saturation into the type must not lose it: sat_frac is what
    downstream excludes on, and it is a stored column."""
    rec = F.scan_frame(_tmp_frame("saturated"))
    assert rec["sat_frac"] >= F.SATURATED_FRAC
    assert F.scan_frame(_tmp_frame("light"))["sat_frac"] < F.SATURATED_FRAC


def test_a_bright_long_exposure_is_twilight_not_a_flat():
    """Found in the ladder: 64 frames at gain 252 / 240-480 s sit above the flat
    level cut without clipping.  They are dawn sky, not a panel, and level alone
    cannot tell the difference -- exposure can."""
    twilight = {"level": 20000.0, "sat_frac": 0.0, "clump_frac": 0.0, "tail_frac": 0.0}
    assert F.classify(twilight, 240.0) == "light"
    assert F.classify(twilight, 3.0) == "flat"


def test_a_clipped_bias_is_still_a_bias():
    """Exposure settles bias before the clipping branch is reached."""
    feats = {"level": 65520.0, "sat_frac": 1.0, "clump_frac": 0.0, "tail_frac": 0.0}
    assert F.classify(feats, 0.001) == "bias"


def test_the_label_is_evidence_not_truth():
    """D18: a flat captured under a Light subframe type must still read as a
    flat, and the disagreement must be recorded rather than resolved."""
    path = os.path.join(_TMP, "mislabelled.fit")
    write_frame(path, "flat")
    with _afits.open(path, mode="update") as hdul:
        hdul[0].header["IMAGETYP"] = "Light"
    rec = F.scan_frame(path)
    assert rec["measured_type"] == "flat"
    assert rec["declared_type"] == "light"
    assert rec["type_agrees"] is False


def test_exposure_decides_bias_before_any_pixel_argument():
    feats = {"level": 1040.0, "sat_frac": 0.0, "clump_frac": 0.9, "tail_frac": 0.1}
    assert F.classify(feats, 0.001) == "bias"
    assert F.classify(feats, 60.0) == "light"


# --------------------------------------------------------------------------
# the index
# --------------------------------------------------------------------------

def test_index_round_trip_is_incremental_and_never_forgets():
    d = os.path.join(_TMP, "archive")
    os.makedirs(d, exist_ok=True)
    paths = [write_frame(os.path.join(d, k + ".fit"), k)
             for k in ("bias", "dark", "flat", "light")]
    csv_path = os.path.join(_TMP, "idx.csv")

    rows = F.refresh_index(d, csv_path, verbose=False)
    assert len(rows) == 4
    assert {r["measured_type"] for r in rows.values()} == {"bias", "dark", "flat", "light"}

    # unchanged (path, size, mtime) -> not re-read.  Over SMB this is the
    # difference between a 40-minute refresh and a fresh 4-hour pass.
    before = {p: r["indexed_at"] for p, r in rows.items()}
    again = F.refresh_index(d, csv_path, verbose=False)
    assert all(again[p]["indexed_at"] == t for p, t in before.items())

    # a changed frame is re-read
    os.utime(paths[0], (0, 0))
    again = F.refresh_index(d, csv_path, verbose=False)
    assert again[paths[0]]["mtime"] == repr(os.stat(paths[0]).st_mtime)

    # a vanished frame is marked, never dropped: a published constant must stay
    # traceable to the frame it was measured on (D19)
    os.remove(paths[1])
    again = F.refresh_index(d, csv_path, verbose=False)
    assert len(again) == 4
    assert again[paths[1]]["status"] == "missing"
    assert again[paths[1]]["measured_type"] == "dark"


def test_index_records_an_unreadable_frame_instead_of_dying():
    d = os.path.join(_TMP, "broken")
    os.makedirs(d, exist_ok=True)
    write_frame(os.path.join(d, "good.fit"), "dark")
    with open(os.path.join(d, "truncated.fit"), "wb") as fh:
        fh.write(b"SIMPLE  =                    T" + b" " * 100)
    rows = F.refresh_index(d, os.path.join(_TMP, "broken.csv"), verbose=False)
    assert len(rows) == 2
    statuses = sorted(r["status"].split(":")[0] for r in rows.values())
    assert statuses == ["ok", "unreadable"]


def test_walk_prunes_the_retired_camera():
    """`_canon` holds frames from a retired camera and has its own
    bias/dark/flat/light beneath it.  Point the walk one level too high and they
    land in exactly the buckets where they would look plausible."""
    d = os.path.join(_TMP, "bytype")
    for sub in ("light", os.path.join("_canon", "light")):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
        write_frame(os.path.join(d, sub, "f.fit"), "light")
    found = list(F.walk(d))
    assert len(found) == 1 and "_canon" not in found[0]
    assert len(list(F.walk(d, exclude=()))) == 2, "the skip must be the reason"


def test_index_marks_a_frame_from_another_rig():
    """Marked, not dropped: a foreign frame in the archive is a cleanup item,
    and silence would hide it."""
    d = os.path.join(_TMP, "foreign")
    os.makedirs(d, exist_ok=True)
    p = write_frame(os.path.join(d, "alien.fit"), "light")
    with _afits.open(p, mode="update") as hdul:
        hdul[0].header["INSTRUME"] = "Canon EOS 6D"
    write_frame(os.path.join(d, "ours.fit"), "light")
    rows = F.refresh_index(d, os.path.join(_TMP, "foreign.csv"), verbose=False)
    assert len(rows) == 2
    assert rows[p]["status"] == "other rig: Canon EOS 6D"
    assert rows[p]["measured_type"] == "light"     # still described, just fenced


def test_capture_settings_are_read_but_the_type_label_is_kept_separate():
    _, header = F.sample_blocks(_tmp_frame("light"))
    s = F.capture_settings(header)
    assert s["gain"] == 252 and s["offset"] == 15
    assert s["exptime"] == 60.0 and s["ccd_temp"] == -10.0
    assert s["imagetyp"] == "Light"          # present, and used as evidence only


def test_read_keeps_the_numbers_the_camera_wrote():
    data, header = F.read(_tmp_frame("dark"))
    assert data.dtype == np.uint16, "floating the data would invent precision"
    assert np.all(data % 16 == 0)


# --------------------------------------------------------------------------
# harness
# --------------------------------------------------------------------------

_TMP = None
_CACHE = {}


def _tmp_frame(kind):
    if kind not in _CACHE:
        _CACHE[kind] = write_frame(os.path.join(_TMP, kind + ".fit"), kind)
    return _CACHE[kind]


def setup_module(module=None):
    global _TMP
    if _TMP is None:
        _TMP = tempfile.mkdtemp(prefix="astropix-test-")


def teardown_module(module=None):
    global _TMP
    if _TMP:
        shutil.rmtree(_TMP, ignore_errors=True)
        _TMP = None
        _CACHE.clear()


# --------------------------------------------------------------------------
# the quantiser-bias simulation (D24's open item, for step 3)
# --------------------------------------------------------------------------
#
# Every value this camera stores is a multiple of 16, so a noise estimator never
# sees the noise -- it sees the noise after rounding.  When sigma is large
# against the step that is harmless; when it is comparable, it is not, and ~90%
# of the calibration frames in this archive read out at *one* step of scatter.
#
# The simulation is a loop over a known truth: draw Gaussian noise at a sigma we
# chose, round it to the grid, run the estimator we intend to ship, and compare.
# Sweeping sigma gives a bias curve, and the curve is the error budget for
# R(gain) -- the read noise is the PTC's intercept, and the quantiser's q^2/12
# lands entirely on the intercept.
#
# `phase` is not a detail.  Where the true mean sits relative to the grid changes
# the answer below one step, because there the rounding is no longer scrambling
# anything -- it is a deterministic function of the signal.  The measured
# pedestals on this rig are 1040.0 and 1232.0, both *exact* grid points, which is
# the least forgiving phase.  "grid" simulates that; "random" averages over it.

BIAS_SIGMA_STEPS = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0)


def quantiser_bias(sigma_steps, n=200_000, trials=4, quantum=stats.QUANTUM,
                   phase="grid", seed=20260828):
    """Estimated / true sigma for each estimator, at one true sigma.

    Returns a dict of ratios: `mad` and `std_raw` are the two D24 measured, both
    uncorrected; `sigma` is the shipping estimator with both corrections; `pair`
    is the pair-difference route the PTC uses.  1.0 is unbiased.
    """
    rng = np.random.default_rng(seed)
    true = sigma_steps * quantum
    acc = {"mad": [], "std_raw": [], "sigma": [], "pair": []}

    for _ in range(trials):
        base = 1232.0
        if phase == "random":
            base += rng.uniform(0.0, quantum)
        elif phase != "grid":
            raise ValueError(phase)

        def draw():
            return np.round(rng.normal(base, true, n) / quantum) * quantum

        a, b = draw(), draw()

        med = np.median(a)
        acc["mad"].append(stats.MAD_TO_SIGMA * float(np.median(np.abs(a - med))))
        raw, _, _ = stats.clipped_std(a, quantum=quantum)
        acc["std_raw"].append(raw)
        acc["sigma"].append(stats.sigma(a, quantum=quantum))
        acc["pair"].append(stats.pair_sigma(a, b, quantum=quantum))

    return {k: float(np.mean(v)) / true for k, v in acc.items()}


def bias_table(sigma_steps=BIAS_SIGMA_STEPS, **kw):
    """The bias curve, as rows ready for results/quantiser_bias.csv."""
    rows = []
    for phase in ("grid", "random"):
        for s in sigma_steps:
            r = quantiser_bias(s, phase=phase, **kw)
            rows.append({"phase": phase, "sigma_steps": s,
                         "sigma_file_adu": s * stats.QUANTUM,
                         **{k: round(v, 5) for k, v in r.items()}})
    return rows


# --------------------------------------------------------------------------
# tests: stats.py
# --------------------------------------------------------------------------

def test_truncation_correction_recovers_sigma_off_grid():
    """With the grid effectively absent, the clip must not shrink the answer.
    An uncorrected 4-sigma clipped std reads ~0.7% low; the target is 0.2%."""
    rng = np.random.default_rng(7)
    x = rng.normal(0.0, 100.0, 2_000_000)
    est = stats.sigma(x, quantum=1e-9)
    assert abs(est / 100.0 - 1.0) < 0.002, est


def test_mad_is_blind_on_the_grid():
    """D24's reason for rejecting MAD, reproduced: at one step of true noise it
    can only return multiples of 23.72, and it errs by tens of percent."""
    r1 = quantiser_bias(1.0)
    assert abs(r1["mad"] - 1.0) > 0.2, r1
    r_small = quantiser_bias(0.25)
    assert r_small["mad"] < 0.01, r_small          # returns essentially zero


def test_sheppard_correction_removes_the_bias():
    """At and above one step, both corrections applied, the estimator is within
    2% -- and the *uncorrected* std is measurably worse at one step."""
    for s in (1.0, 2.0, 4.0, 8.0):
        r = quantiser_bias(s)
        assert abs(r["sigma"] - 1.0) < 0.02, (s, r)
    one = quantiser_bias(1.0)
    assert one["std_raw"] - 1.0 > 0.02, one
    assert abs(one["sigma"] - 1.0) < abs(one["std_raw"] - 1.0), one


def test_pair_difference_agrees_with_single_frame():
    """The PTC's estimator and the single-frame one must measure the same thing
    on data with no fixed pattern to separate them."""
    for s in (1.0, 4.0):
        r = quantiser_bias(s)
        assert abs(r["pair"] - 1.0) < 0.02, (s, r)


def test_pair_difference_cancels_fixed_pattern():
    """The whole reason the PTC differences frames.  A flat carries pixel-response
    non-uniformity that a single frame's spatial spread cannot tell from shot
    noise; the pair difference must be blind to it."""
    rng = np.random.default_rng(3)
    prnu = rng.normal(1.0, 0.02, 200_000)          # 2% fixed pattern
    level, shot = 20000.0, 160.0

    def frame():
        return np.round((level * prnu + rng.normal(0.0, shot, prnu.size)) / 16.0) * 16.0

    a, b = frame(), frame()
    assert stats.sigma(a) > 1.5 * shot                       # spatial: sees the PRNU
    assert abs(stats.pair_sigma(a, b) / shot - 1.0) < 0.02   # temporal: does not


def test_estimator_survives_a_collapsed_mad():
    """A frame with no resolvable noise must return 0.0, not nan, and must not
    reject every pixel -- the zero-width-window trap the quantum floor closes."""
    flat = np.full(10_000, 1232.0)
    raw, centre, kept = stats.clipped_std(flat)
    assert kept == 1.0 and centre == 1232.0, (raw, centre, kept)
    assert stats.sigma(flat) == 0.0


def test_sigma_rejects_hot_pixels():
    """The half MAD is there for: std alone must not survive this, sigma must."""
    rng = np.random.default_rng(11)
    a = np.round(rng.normal(1232.0, 160.0, 100_000) / 16.0) * 16.0
    a[::500] = 40000.0
    assert abs(stats.sigma(a) / 160.0 - 1.0) < 0.02, stats.sigma(a)
    assert a.std() > 400.0


# --------------------------------------------------------------------------
# tests: the record itself (D33)
# --------------------------------------------------------------------------
#
# Everything in `results/` must be written by a cell in a numbered notebook, so
# that the route from the archive to a published number is readable end to end.
# This is a static read of the notebook JSON -- no execution, no Z:, no pandas --
# because a check that needs the archive is a check that stops being run.
#
# It is deliberately *not* a reproducibility test.  Re-running an acquisition
# yields a new snapshot rather than the old one (D19), and demanding byte
# equality would forbid the artifacts that cost an hour to produce.

WRITE_CALLS = ("to_csv(", "to_json(", "json.dump(", "refresh_index(",
               "_write_index(")
RESULT_SUFFIXES = (".csv", ".json")


def _repo_root():
    return pathlib.Path(__file__).resolve().parents[1]


def results_writers():
    """Map `results/` filename -> [(notebook, cell index)] that writes it.

    Two ways a cell can name its output, both used in practice:
    a literal (`to_csv(RESULTS / "ladder_census.csv")`) and a module-level alias
    (`INDEX = RESULTS / "frame_index.csv"`, then `refresh_index(roots, INDEX)`).
    The window of three lines covers a call wrapped across lines.
    """
    out = {}
    for nbp in sorted((_repo_root() / "notebooks").glob("*.ipynb")):
        nb = json.loads(nbp.read_text(encoding="utf-8"))
        cells = [(i, "".join(c["source"])) for i, c in enumerate(nb["cells"])
                 if c["cell_type"] == "code"]
        alias = dict(re.findall(r"(\w+)\s*=\s*RESULTS\s*/\s*[\"']([^\"']+)[\"']",
                                "\n".join(s for _, s in cells)))
        for i, source in cells:
            lines = source.splitlines()
            for n, line in enumerate(lines):
                if not any(v in line for v in WRITE_CALLS):
                    continue
                window = "\n".join(lines[n:n + 3])
                names = set(re.findall(r"[\"']([\w.\-]+\.(?:csv|json))[\"']", window))
                names |= {f for var, f in alias.items()
                          if re.search(r"\b" + re.escape(var) + r"\b", window)}
                for name in names:
                    out.setdefault(name, []).append((nbp.name, i))
    return out


def test_every_results_file_has_a_generator():
    """The rule D33 states.  An orphan here means a number was published that
    nobody can regenerate -- which is how the three census CSVs were lost."""
    root = _repo_root()
    if not (root / "notebooks").is_dir() or not (root / "results").is_dir():
        return
    writers = results_writers()
    orphans = sorted(f.name for f in (root / "results").iterdir()
                     if f.suffix in RESULT_SUFFIXES and f.name not in writers)
    assert not orphans, ("no notebook cell writes " + ", ".join(orphans)
                         + " -- see DECISIONS D33")


def test_only_numbered_notebooks_write_to_results():
    """D33's other half: question notebooks are disposable, so nothing durable
    may depend on one.  A `results/` file written by an unnumbered notebook is a
    finding that has not graduated yet."""
    root = _repo_root()
    if not (root / "notebooks").is_dir():
        return
    stray = sorted({nb for hits in results_writers().values()
                    for nb, _ in hits if not re.match(r"^\d\d_", nb)})
    assert not stray, f"unnumbered notebooks writing to results/: {stray}"


def main():
    setup_module()
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = []
    try:
        for name, fn in tests:
            try:
                fn()
                print(f"  ok    {name}")
            except Exception as exc:
                failed.append(name)
                print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
    finally:
        teardown_module()
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
