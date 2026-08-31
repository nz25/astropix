"""asi.py -- driving the camera, with no camera attached.

Every test here runs against `FakeCamera`, which implements the small surface
`asi.py` actually uses.  That is deliberate and not a compromise: the whole
point of the module is the handful of traps in L01-L05, and each of those is a
*decision* -- what to do when a control is missing, when a value clamps, when
the temperature stops falling -- that can be exercised exactly once the device
underneath is scripted.  A test that needed the camera plugged in would be run
never, and the traps it guards cost bench nights, not minutes.

What these cannot check is whether the SDK behaves as scripted here.  That is
first-light work, and `protocols/01-bias-sweep.md` gates on it.
"""

import numpy as np

from astropix import asi


# --------------------------------------------------------------------------
# the stand-in
# --------------------------------------------------------------------------

# name -> (id, min, max, default).  Ids, ranges and defaults are the ASI585MC
# Pro's own, read off the camera on 2026-08-28 -- a fixture that invents its
# ranges would let a guard pass here and fail at the bench, which is the one
# thing these tests exist to prevent.  Note `Offset` tops out at 200, not 600.
_CONTROLS = {
    "Gain": (0, 0, 600, 200),
    "Offset": (5, 0, 200, 3),
    "Exposure": (1, 32, 2000000000, 10000),
    "WB_R": (3, 1, 99, 55),
    "WB_B": (4, 1, 99, 75),
    "Temperature": (8, -500, 1000, 0),
    "CoolerOn": (17, 0, 1, 0),
    "TargetTemp": (16, -40, 30, 0),
    "CoolPowerPerc": (15, 0, 100, 0),
}


class FakeCamera:
    def __init__(self, temps=None, clamp=None):
        self.controls = {
            name: {"ControlType": cid, "MinValue": lo, "MaxValue": hi}
            for name, (cid, lo, hi, _) in _CONTROLS.items()
        }
        self._by_id = {cid: name for name, (cid, _, _, _) in _CONTROLS.items()}
        self.values = {name: d for name, (_, _, _, d) in _CONTROLS.items()}
        # a scripted temperature series, in C; the last value repeats forever
        self.temps = list(temps) if temps else [0.0]
        self.clamp = clamp or {}
        self.roi = None
        self.closed = False
        self.closes = 0

    def get_controls(self):
        return self.controls

    def get_control_value(self, cid):
        name = self._by_id[cid]
        if name == "Temperature":
            t = self.temps[0] if len(self.temps) == 1 else self.temps.pop(0)
            return int(round(t * 10)), False
        return self.values[name], False

    def set_control_value(self, cid, value):
        name = self._by_id[cid]
        self.values[name] = self.clamp.get(name, value)

    def set_roi(self, start_x, start_y, width, height, image_type=None):
        self.roi = (start_x, start_y, width, height, image_type)

    def capture(self):
        return np.full((8, 8), 1232, np.uint16)

    def close(self):
        self.closes += 1
        self.closed = True


class Clock:
    """A fake monotonic clock that only advances when something sleeps."""

    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, dt):
        self.t += dt


def rig(**kwargs):
    return asi.Rig(FakeCamera(**kwargs), raw16=2)


# --------------------------------------------------------------------------
# controls: resolved by name, ranged by the camera (L03, L05)
# --------------------------------------------------------------------------

def test_a_missing_control_names_the_ones_the_camera_has():
    """L03's first trap: a lookup on `CoolerPowerPerc` returned a hard 0
    forever while the cooler worked.  A KeyError that prints the real names
    turns a silent wrong number into a five-second fix."""
    try:
        rig().get("CoolerPowerPerc")
    except KeyError as exc:
        assert "CoolPowerPerc" in str(exc)
        return
    raise AssertionError("expected KeyError")


def test_range_is_read_from_the_camera_not_assumed():
    """L05: the retired project assumed gain 0-400 and the range is 0-600, so
    a fifth of the sweep it thought it was running did not exist."""
    r = rig()
    assert r.range("Gain") == (0, 600)
    r.set("Gain", 600)
    for bad in (601, -1):
        try:
            r.set("Gain", bad)
        except ValueError:
            continue
        raise AssertionError(f"gain {bad} should be refused")


def test_a_clamped_control_is_an_error_not_a_shrug():
    """A control that silently clamps produces frames whose headers disagree
    with the hardware that made them, undetectably, forever after."""
    r = rig(clamp={"Gain": 100})
    try:
        r.set("Gain", 300)
    except RuntimeError as exc:
        assert "300" in str(exc) and "100" in str(exc)
        return
    raise AssertionError("expected RuntimeError")


def test_min_exposure_comes_from_the_control():
    assert rig().min_exposure_s() == 32 / 1e6


# --------------------------------------------------------------------------
# white balance (L01) and ROI (L05)
# --------------------------------------------------------------------------

def test_white_balance_is_neutralised_from_the_shipped_values():
    r = rig()
    assert (r.get("WB_R"), r.get("WB_B")) == (55, 75), "the fixture must ship ZWO's"
    asi.neutralise_white_balance(r)
    assert (r.get("WB_R"), r.get("WB_B")) == (50, 50)


def test_roi_must_be_even_or_the_bayer_phase_shifts():
    r = rig()
    for bad in [(1409, 568, 1024, 1024), (1408, 569, 1024, 1024),
                (1408, 568, 1023, 1024), (1408, 568, 1024, 1023)]:
        try:
            asi.set_roi(r, *bad)
        except ValueError:
            continue
        raise AssertionError(f"ROI {bad} should be refused")
    asi.set_roi(r, 1408, 568, 1024, 1024)
    assert r.cam.roi == (1408, 568, 1024, 1024, 2)


def test_roi_width_honours_the_transfer_constraint():
    try:
        asi.set_roi(rig(), 0, 0, 1020, 1024)   # even, but not a multiple of 8
    except ValueError as exc:
        assert "multiple of 8" in str(exc)
        return
    raise AssertionError("expected ValueError")


# --------------------------------------------------------------------------
# cooling (L03, L04)
# --------------------------------------------------------------------------

def test_temperature_reports_none_rather_than_a_fake_zero():
    """L03: `ASI_TEMPERATURE` reads a flat 0 until the cooler is on.  Zero is
    also a real temperature, so with the cooler off it is not a measurement."""
    r = rig(temps=[0.0])
    assert asi.temperature(r) is None
    r.set("CoolerOn", 1)
    assert asi.temperature(r) == 0.0


def test_cool_to_needs_a_continuous_settle_window():
    """L04: a TEC overshoots and rings, so the first touch of the setpoint is
    the middle of a swing.  An excursion restarts the clock."""
    clock = Clock()
    r = rig(temps=[17.0, 5.0, -5.0, -10.0, -10.2, -8.0, -10.1, -10.0, -10.0, -10.0])
    trace = asi.cool_to(r, -10.0, settle_s=3.0, poll_s=1.0,
                        _sleep=clock.sleep, _now=clock.now)
    # in band at t=3, out at t=5, in again from t=6 -> settled at t=9, not t=6
    assert len(trace) == 10 and trace[-1][0] == 9.0
    assert r.get("CoolerOn") == 1 and r.get("TargetTemp") == -10


def test_cool_to_catches_a_latched_tec():
    """L03's third trap: a hard-killed process leaves the TEC off until the
    12 V is replugged, and it looks exactly like a slow cool."""
    clock = Clock()
    try:
        asi.cool_to(rig(temps=[17.0]), -10.0, poll_s=1.0,
                    _sleep=clock.sleep, _now=clock.now)
    except RuntimeError as exc:
        assert "Power-cycle" in str(exc)
        return
    raise AssertionError("expected RuntimeError")


def test_cool_to_gives_up_rather_than_polling_forever():
    clock = Clock()
    # falls steadily but never reaches the setpoint: not a latched TEC, and
    # not a settle either -- the timeout is the only thing that ends it
    temps = [17.0 - 0.1 * i for i in range(200)] + [-3.0]
    try:
        asi.cool_to(rig(temps=temps), -10.0, timeout_s=30.0, poll_s=1.0,
                    _sleep=clock.sleep, _now=clock.now)
    except TimeoutError:
        return
    raise AssertionError("expected TimeoutError")


# --------------------------------------------------------------------------
# capture
# --------------------------------------------------------------------------

def test_capture_reports_what_the_camera_did_not_what_it_was_asked():
    r = rig(temps=[-10.1])
    r.set("CoolerOn", 1)
    asi.configure(r, gain=252, offset=15, roi=(1408, 568, 1024, 1024))
    mosaic, header = asi.capture(r, 0.001, imagetyp="BIAS")

    assert mosaic.dtype == np.uint16 and np.all(mosaic % 16 == 0), \
        "nothing in asi.py may rescale a pixel (CLAUDE.md units rule)"
    assert header["GAIN"] == 252 and header["OFFSET"] == 15
    assert abs(header["EXPTIME"] - 0.001) < 1e-9
    assert header["CCD-TEMP"] == -10.1
    assert header["BAYERPAT"] == "RGGB"
    assert header["DATE-OBS"].startswith("20") and "T" in header["DATE-OBS"]
    assert header["INSTRUME"] == "ZWO ASI585MC Pro"


def test_cool_to_reports_each_reading_as_it_is_taken():
    """A ten-minute cool-down that shows nothing until it finishes cannot be
    watched, and loses everything if it is interrupted -- which is not
    hypothetical: the temperature is only observable while we are the ones
    cooling, so an interrupted run takes its answer with it (L03b)."""
    clock, seen = Clock(), []
    temps = [17.0, 5.0, -10.0, -10.0, -10.0]
    trace = asi.cool_to(rig(temps=temps), -10.0, settle_s=2.0, poll_s=1.0,
                        log=lambda *r: seen.append(r),
                        _sleep=clock.sleep, _now=clock.now)
    assert seen == trace, "every reading must be reported, in order, as taken"
    assert seen[0][0] == 0.0, "the first reading comes before the first sleep"


# --------------------------------------------------------------------------
# closing: the SDK addresses cameras by index, so a stale close is not free
# --------------------------------------------------------------------------

def test_closing_twice_only_closes_once():
    r = rig()
    r.close()
    r.close()
    assert r.cam.closes == 1


def test_a_dead_handle_does_not_close_the_camera_that_replaced_it():
    """The session 02 failure: reopening in a notebook killed the new camera.

    `_camera_class` is handed a stand-in binding whose cameras share one bus
    keyed by index, which is the part of the real SDK that makes this bite.
    """
    bus = {}

    class Binding:
        class Camera:
            def __init__(self, id_):
                self.id = id_
                bus[id_] = True
                self.closed = False

            def __del__(self):
                self.close()

            def close(self):
                bus[self.id] = False
                self.closed = True

            def get_controls(self):
                return {}

    cam = asi._camera_class(Binding)
    scout = cam(0)
    scout.close()                     # the scout half of the notebook ends here
    assert bus[0] is False

    session = cam(0)                  # the session half opens a fresh one ...
    del scout                         # ... and the old handle is dropped
    assert bus[0] is True, "a dead handle closed the live camera"
    assert session.closed is False
