"""fits.py -- reading one frame, and describing it."""

import os

import numpy as np
from astropy.io import fits as _afits

from astropix import fits as F

from .synthetic import PEDESTAL, tmp_frame, tmpdir, write_frame


# --------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------

def test_read_keeps_the_numbers_the_camera_wrote():
    data, header = F.read(tmp_frame("dark"))
    assert data.dtype == np.uint16, "floating the data would invent precision"
    assert np.all(data % 16 == 0)


def test_sample_blocks_reads_the_asked_for_geometry():
    blocks, header = F.sample_blocks(tmp_frame("flat"), n_blocks=4, block_rows=16)
    assert len(blocks) == 4
    assert all(b.shape == (16, 128) for b in blocks)
    assert all(b.dtype == np.uint16 for b in blocks)
    assert header["GAIN"] == 252


def test_capture_settings_are_read_but_the_type_label_is_kept_separate():
    _, header = F.sample_blocks(tmp_frame("light"))
    s = F.capture_settings(header)
    assert s["gain"] == 252 and s["offset"] == 15
    assert s["exptime"] == 60.0 and s["ccd_temp"] == -10.0
    assert s["imagetyp"] == "Light"          # present, and used as evidence only


# --------------------------------------------------------------------------
# describing one frame
# --------------------------------------------------------------------------

def test_scan_frame_describes_a_frame_completely():
    """One call must produce every column the index stores about a frame, so
    that the notebook's loop is a loop and nothing more."""
    rec = F.scan_frame(tmp_frame("dark"), pedestal=PEDESTAL)
    for key in ("gain", "exptime", "ccd_temp", "level", "sigma", "mult16_frac",
                "measured_type", "declared_type", "type_agrees", "status"):
        assert key in rec, key
    assert rec["measured_type"] == "dark"
    assert rec["status"] == "ok"


def test_scan_frame_marks_a_frame_from_another_rig():
    """Marked, not dropped: a foreign frame in the archive is a cleanup item
    (D20, D26), and silence would hide it.  It is still described -- just
    fenced -- so the cleanup list says what the thing actually is."""
    p = write_frame(os.path.join(tmpdir(), "alien.fit"), "light")
    with _afits.open(p, mode="update") as hdul:
        hdul[0].header["INSTRUME"] = "Canon EOS 6D"
    rec = F.scan_frame(p, pedestal=PEDESTAL)
    assert rec["status"] == "other rig: Canon EOS 6D"
    assert rec["measured_type"] == "light"


def test_scan_frame_raises_on_an_unreadable_frame():
    """It raises rather than returning a status, so a caller cannot mistake a
    broken file for a described one.  Whether one bad frame stops a pass is the
    caller's decision, not this module's."""
    p = os.path.join(tmpdir(), "truncated.fit")
    with open(p, "wb") as fh:
        fh.write(b"SIMPLE  =                    T" + b" " * 100)
    try:
        F.scan_frame(p)
    except Exception:
        return
    raise AssertionError("expected an exception")


# --------------------------------------------------------------------------
# the incremental decision
# --------------------------------------------------------------------------

def test_stat_row_keeps_mtime_exact():
    """`mtime` is stored as repr, not as a float.  The index round-trips through
    CSV and this string is compared for equality; going via float would make the
    whole incremental scan depend on text-to-float round-tripping being
    lossless."""
    p = tmp_frame("bias")
    row = F.stat_row(p)
    assert row["mtime"] == repr(os.stat(p).st_mtime)
    assert isinstance(row["mtime"], str)
    assert row["size"] == os.stat(p).st_size


def test_needs_rescan_skips_an_unchanged_frame():
    """The whole reason a refresh is minutes rather than hours."""
    p = tmp_frame("bias")
    prev = dict(F.stat_row(p), status="ok")
    assert F.needs_rescan(p, prev) is False


def test_needs_rescan_survives_a_csv_round_trip():
    """The realistic case: the previous row came back from pandas, so every
    value is a string or a numpy scalar rather than what was written."""
    p = tmp_frame("bias")
    row = dict(F.stat_row(p), status="ok")
    as_csv = {k: str(v) for k, v in row.items()}      # what read_csv hands back
    assert F.needs_rescan(p, as_csv) is False


def test_needs_rescan_notices_a_changed_frame():
    p = write_frame(os.path.join(tmpdir(), "changing.fit"), "dark")
    prev = dict(F.stat_row(p), status="ok")
    os.utime(p, (0, 0))
    assert F.needs_rescan(p, prev) is True

    prev = dict(F.stat_row(p), status="ok")
    prev["size"] = int(prev["size"]) + 1
    assert F.needs_rescan(p, prev) is True


def test_needs_rescan_retries_what_did_not_end_ok():
    """An unreadable frame may since have been repaired, and a frame fenced as
    another rig may have been re-headered.  Neither is skipped on the strength
    of a failure."""
    p = tmp_frame("bias")
    for status in ("unreadable: OSError", "other rig: Canon EOS 6D", "missing"):
        assert F.needs_rescan(p, dict(F.stat_row(p), status=status)) is True
    assert F.needs_rescan(p, None) is True
    assert F.needs_rescan(p, {}) is True


# --------------------------------------------------------------------------
# writing (the bench side: our own frames must be indistinguishable
# from archive frames to this same reader)
# --------------------------------------------------------------------------

def test_write_round_trips_the_exact_numbers_and_the_trusted_settings():
    data = (np.arange(64, dtype=np.uint16) * 16).reshape(8, 8)
    path = os.path.join(tmpdir(), "written.fit")
    F.write(path, data, {"GAIN": 252, "OFFSET": 15, "EXPTIME": 0.001,
                         "CCD-TEMP": -10.1, "BAYERPAT": "RGGB",
                         "INSTRUME": F.RIG_INSTRUME}, overwrite=True)
    back, header = F.read(path)
    assert back.dtype == np.uint16 and np.array_equal(back, data)
    assert header["GAIN"] == 252 and header["OFFSET"] == 15
    assert F.capture_settings(header)["ccd_temp"] == -10.1


def test_write_drops_cards_with_no_value():
    """A temperature the camera did not report must be absent, not zero: a
    header that invents -0.0 C is worse than one that admits it does not know."""
    path = os.path.join(tmpdir(), "no_temp.fit")
    F.write(path, np.zeros((4, 4), np.uint16), {"GAIN": 100, "CCD-TEMP": None},
            overwrite=True)
    assert "CCD-TEMP" not in F.read(path)[1]


def test_write_refuses_to_overwrite_by_default():
    """A capture loop that silently rewrites a frame destroys the one thing a
    sweep cannot reconstruct: how many frames it actually got."""
    path = os.path.join(tmpdir(), "once.fit")
    F.write(path, np.zeros((4, 4), np.uint16), overwrite=True)
    try:
        F.write(path, np.zeros((4, 4), np.uint16))
    except OSError:
        return
    raise AssertionError("expected the second write to be refused")
