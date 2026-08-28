"""Driving the camera: one exposure at a time.

`asi.py` is to the camera what `fits.py` is to a file.  It moves device state
and bytes, and it interprets no pixel: every statistic on what comes back
belongs to `stats.py`.  White balance is the clearest case of that split --
`neutralise_white_balance` sets the control and reads it back, which is a
device operation, but the *evidence* that it took is a modal step of 16 in the
pixels (L01), and that lives in `stats.value_step` where the pixels are.

**No loops over frames** (CLAUDE.md).  `capture` takes one exposure and
returns.  A gain sweep is orchestration and belongs in the notebook that runs
it.  The one loop here is `cool_to`, which polls a thermometer and not frames,
and which is here rather than in a notebook because the settle band and the
settle duration are thresholds -- physics, not orchestration.

**Controls are resolved by name, from the camera itself.**  Not from module
constants, for two reasons.  The SDK's own naming has already cost a session:
the cooler duty control is `CoolPowerPerc`, not `CoolerPowerPerc`, and a lookup
on the wrong name returned a hard 0 forever while the cooler was working
perfectly (L03).  Reading the list back turns that into a KeyError that prints
the names the camera actually has.  And every control carries its own
`MinValue`/`MaxValue`, so the gain range is *read* rather than assumed -- the
retired project assumed 0-400 and the range is 0-600 (L05).

**Nothing here rescales a pixel.**  The camera writes 12-bit values shifted
into a 16-bit container and that is what reaches disk, untouched, so that
`stats.frame_features` can run its `% 16` check on evidence rather than on
something this module already normalised (CLAUDE.md, the units rule).
"""

from __future__ import annotations

import datetime as _dt
import pathlib
import time

import numpy as np

from . import fits

# --- the rig (CLAUDE.md) -----------------------------------------------------
# Anchored at the repo, not at the working directory.  A notebook runs from
# `notebooks/` and a probe from wherever it was written, and a relative path
# here fails in both -- as a swallowed load error and an AttributeError three
# frames deep, which is the least informative way this can possibly break.
SDK_DLL = pathlib.Path(__file__).resolve().parents[1] / "vendor" / "zwo-asi-sdk" / "ASICamera2.dll"
SETPOINT_C = -10.0        # every bench run and the model's first pass
RAW16 = 2                 # ASI_IMG_RAW16; resolved from the SDK when there is one

# --- cooling thresholds (L03, L04) -------------------------------------------
# The sensor reports in steps of 0.5 C -- measured, not assumed: every reading
# in a 589-second cool-down from 14 C was a multiple of 0.5.  So this band is
# exactly one quantiser step, admitting the three codes either side of setpoint,
# and a tighter one would be unsatisfiable except at the exact code.  The number
# it guards against is the archive's 2,132 frames more than 1 C off setpoint.
BAND_C = 0.5
SETTLE_S = 600.0          # a TEC overshoots and rings; in-band once is not settled
TREND_S = 60.0            # falling after a minute is the only cooler test that works
TREND_MIN_FALL_C = 1.0    # ~3 C/min from ambient, so a minute is a wide margin

NEUTRAL_WB = 50           # the camera ships WB_R=55, WB_B=75, applied to RAW16 (L01)


class Rig:
    """One open camera, plus its control table.

    A thin handle rather than a wrapper: it exists because the control table is
    a USB round trip that would otherwise be paid on every set, and because
    range checking wants the table anyway.
    """

    def __init__(self, cam, raw16=RAW16):
        self.cam = cam
        self.raw16 = raw16
        self.controls = cam.get_controls()

    # --- controls ---------------------------------------------------------
    def _control(self, name):
        try:
            return self.controls[name]
        except KeyError:
            raise KeyError(
                f"no control named {name!r}; this camera reports "
                f"{sorted(self.controls)}"
            ) from None

    def get(self, name):
        """The control's current value, as the camera reports it."""
        value = self.cam.get_control_value(self._control(name)["ControlType"])
        return value[0] if isinstance(value, (tuple, list)) else value

    def set(self, name, value, verify=True):
        """Set a control, range-checked against its own limits, and read back.

        The readback is not paranoia.  A control that silently clamps turns a
        sweep into a set of frames whose headers disagree with the hardware
        that made them, and every number derived from them is then wrong in a
        way no later analysis can detect.  Better to stop at 2 a.m. with both
        numbers printed.
        """
        c = self._control(name)
        lo, hi = c["MinValue"], c["MaxValue"]
        if not lo <= value <= hi:
            raise ValueError(f"{name}={value} outside the camera's own range {lo}..{hi}")
        self.cam.set_control_value(c["ControlType"], int(value))
        if verify:
            got = self.get(name)
            if got != int(value):
                raise RuntimeError(f"{name} set to {int(value)} but reads back {got}")
        return self

    def range(self, name):
        """`(min, max)` for a control -- L05's "read the gain range from the SDK"."""
        c = self._control(name)
        return c["MinValue"], c["MaxValue"]

    def min_exposure_s(self):
        """The shortest exposure this camera takes.  Bias frames use it, and the
        protocol requires the value be recorded rather than assumed."""
        return self.range("Exposure")[0] / 1e6

    def close(self):
        """Release the camera.  **This drops the cooler.**

        Measured on 2026-08-28: set `CoolerOn = 1`, close, reopen, and it reads
        0 -- while `Gain` and `Offset` come back exactly as they were left.
        Control values live in the camera; the TEC is tied to the open session.
        So a run cools and captures in one process or not at all, and "it should
        still be cold from last time" is never true.  Nothing contradicts that
        belief on its own, either: with the cooler off the sensor reports a flat
        0, which `temperature` reports as None rather than as a measurement.
        """
        self.cam.close()


def open_camera(index=0, dll=SDK_DLL, raw16=None):
    """Open the camera, or explain which of the two failures this is (L02).

    ZWO ship the driver and the SDK as separate downloads, and the SDK alone
    gives the state where `init()` succeeds and no camera is found.  The
    ASIAIR is the other cause: powered on with the camera attached it claims
    the USB device exclusively, and the PC sees nothing regardless of drivers.
    Both present identically as zero cameras, so the message names both.
    """
    import zwoasi

    if not pathlib.Path(dll).exists():
        raise RuntimeError(f"no ASI SDK at {dll} -- the DLL is vendored in this "
                           "repo, so this means the path is wrong, not that the "
                           "SDK is missing")
    try:
        zwoasi.init(str(dll))
    except Exception:
        # `init` returns early and harmlessly when the library is already
        # loaded, which is the common case in a notebook.  Everything else is
        # swallowed here and caught on the next line instead: `zwolib` is the
        # thing that has to be true, and checking it directly cannot be fooled
        # by which exception type this version of the binding happens to raise.
        pass
    if getattr(zwoasi, "zwolib", None) is None:
        raise RuntimeError(f"the ASI SDK at {dll} did not load; on Windows this "
                           "is usually a 32/64-bit mismatch with the interpreter")
    if zwoasi.get_num_cameras() == 0:
        raise RuntimeError(
            "no ASI camera found.  Either the Windows *driver* is missing (the "
            "SDK alone is not enough -- check Get-PnpDevice for VID_03C3), or "
            "the ASIAIR is powered on and holding the camera over USB (L02)"
        )
    return Rig(zwoasi.Camera(index),
               raw16=raw16 if raw16 is not None else getattr(zwoasi, "ASI_IMG_RAW16", RAW16))


def neutralise_white_balance(rig):
    """Set WB_R and WB_B to 50 and confirm the camera took it (L01).

    The camera ships 55/75 and applies them to RAW16 *before* the data reaches
    us, which inflated read noise by ~17% at every gain in the retired project.
    This is half the check.  The other half is in the pixels -- the modal step
    between adjacent values must be 16 on all four planes -- and it is a gate
    in `protocols/01-bias-sweep.md`, run through `stats.value_step`, because a
    setting that reads back correctly is not proof that the pipeline honoured it.
    """
    for name in ("WB_R", "WB_B"):
        rig.set(name, NEUTRAL_WB)
    return rig


def set_roi(rig, x, y, w, h):
    """Set the region of interest, with the two guards that matter (L05).

    Even origin and extent, or the Bayer phase shifts and `spatial.split` hands
    back the wrong plane under the right name -- a failure with no symptom
    except numbers that are quietly about a different colour.  Width divisible
    by 8 is the SDK's own transfer constraint.
    """
    if any(v % 2 for v in (x, y, w, h)):
        raise ValueError(f"ROI ({x},{y},{w},{h}) must be even throughout, "
                         "or the Bayer phase shifts (L05)")
    if w % 8:
        raise ValueError(f"ROI width {w} must be a multiple of 8 for the ASI transfer")
    rig.cam.set_roi(start_x=x, start_y=y, width=w, height=h, image_type=rig.raw16)
    return rig


def configure(rig, *, gain=None, offset=None, roi=None):
    """Apply the settings one block of a sweep holds fixed."""
    if roi is not None:
        set_roi(rig, *roi)
    if gain is not None:
        rig.set("Gain", gain)
    if offset is not None:
        rig.set("Offset", offset)
    return rig


def temperature(rig):
    """Sensor temperature in C, or None when the camera is not reporting one.

    `ASI_TEMPERATURE` reads a flat 0 on an idle camera and an exposure does not
    wake it (L03).  Zero is also a perfectly legitimate temperature, so the two
    cannot be told apart from the number alone -- with the cooler off, a reading
    of 0 is reported as None rather than as a measurement.  Nothing downstream
    may treat "not reported" as a temperature, which is exactly what the
    retired project's hard 0 did.
    """
    raw = rig.get("Temperature") / 10.0
    if raw == 0.0 and not rig.get("CoolerOn"):
        return None
    return raw


def cool_to(rig, setpoint=SETPOINT_C, *, band=BAND_C, settle_s=SETTLE_S,
            timeout_s=1800.0, poll_s=1.0, log=None,
            _sleep=time.sleep, _now=time.monotonic):
    """Cool, and return only once the temperature has *stayed* in band (L04).

    Two failures this guards against.  A TEC overshoots and rings, so the first
    touch of the setpoint is the middle of a swing, not the end of one -- the
    settle window requires `settle_s` of *continuous* in-band readings and
    restarts the clock on any excursion.  And a hard-killed process leaves the
    TEC latched off until the 12 V is physically replugged (L03), which looks
    exactly like a slow cool; the trend test catches it in a minute, because
    diagnosing a cooler by its duty cycle is what does not work.

    Returns the trace as `[(elapsed_s, temp_C, duty_pct), ...]` -- the session
    record wants the curve, and L04's own advice is that the curve is the answer.

    `log` is called with each reading as it is taken.  Returning the trace at
    the end is not enough: a cool-down runs for ten minutes or more, and a run
    that shows nothing until it finishes cannot be watched, cannot be judged
    early, and loses everything if it is interrupted.  Worse, the reading is
    only observable *while we are the ones cooling* -- switch the cooler off
    and `Temperature` returns to a flat 0 (L03), taking the answer with it.
    """
    rig.set("TargetTemp", int(round(setpoint)), verify=False)
    rig.set("CoolerOn", 1, verify=False)

    t0 = _now()
    trace, start_temp, in_band_since = [], None, None
    while True:
        elapsed = _now() - t0
        temp = temperature(rig)
        reading = (elapsed, temp, rig.get("CoolPowerPerc"))
        trace.append(reading)
        if log is not None:
            log(*reading)

        if temp is not None:
            if start_temp is None:
                start_temp = temp
            # Only a camera that has somewhere to fall from can be judged on
            # falling; one already near setpoint is not evidence of anything.
            if (elapsed >= TREND_S and start_temp > setpoint + 2 * band
                    and temp > start_temp - TREND_MIN_FALL_C):
                raise RuntimeError(
                    f"temperature has not fallen ({start_temp:.1f} -> {temp:.1f} C "
                    f"in {elapsed:.0f} s): the TEC is latched off.  Power-cycle "
                    "the 12 V, do not debug it (L03)")
            if abs(temp - setpoint) <= band:
                in_band_since = elapsed if in_band_since is None else in_band_since
                if elapsed - in_band_since >= settle_s:
                    return trace
            else:
                in_band_since = None

        if elapsed > timeout_s:
            raise TimeoutError(
                f"not settled at {setpoint} C +/-{band} within {timeout_s:.0f} s "
                f"(last reading {temp})")
        _sleep(poll_s)


def capture(rig, exposure_s, imagetyp="BIAS"):
    """One exposure.  Returns `(mosaic, header)` -- pixels, and what the camera
    says it just did.

    The header is read back from the controls *after* the exposure rather than
    composed from what was asked for, so a frame carries the settings that made
    it.  That is the same trust boundary the archive taught (`CLAUDE.md`):
    capture settings are trusted, the type label is not -- and `imagetyp` is
    passed through only because FITS convention expects the card, never as
    evidence of anything.
    """
    rig.set("Exposure", int(round(exposure_s * 1e6)))
    date_obs = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    mosaic = np.asarray(rig.cam.capture())
    temp = temperature(rig)
    header = {
        "IMAGETYP": imagetyp,
        "EXPTIME": rig.get("Exposure") / 1e6,
        "GAIN": rig.get("Gain"),
        "OFFSET": rig.get("Offset"),
        "SET-TEMP": rig.get("TargetTemp"),
        "CCD-TEMP": temp,
        "DATE-OBS": date_obs,
        "BAYERPAT": "RGGB",
        "XBINNING": 1,
        "INSTRUME": fits.RIG_INSTRUME,
        "CREATOR": "astropix.asi",
    }
    return mosaic, header
