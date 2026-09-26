"""Driving PixInsight headless, and the unit boundary at its edge.

PixInsight is the integration engine and the referee (D6), never a subject.
This module is the process contract and the conversions that make a number
from PI comparable with a number from us.  It does not decide anything about
an image; it launches a PJSR script, waits in bounded time, and hands back
what that script wrote.

**The whole design follows from PixInsight having no console.**  It is a
GUI-subsystem binary: `console.writeln()` is invisible to the caller, `--help`
launches the full GUI rather than printing, and a bad command-line argument
produces a *modal dialog* that waits forever for a click that no headless run
will ever provide (L16, L18).  So every script reports by writing a file, the
absence of that file is the failure signal, and every launch has a timeout
with a kill behind it.  The exit code is not evidence: a killed process
reports -1 and the modal-dialog case never exits at all (L17).

Parameters travel the same way, in the opposite direction.  PixInsight's `-p=`
is one of the arguments that raises the fatal dialog, and its own documentation
says values passed that way are always strings, so a job goes in as JSON --
which is better than `-p=` would have been, because numbers survive as numbers
(L19).  The script finds its job file by *relative path*, resolved against a
working directory this module sets per run, which is what keeps two runs from
reading each other's job.

Nothing here loops over frames and nothing here interprets a pixel.  One
launch, one job, one result.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from . import fits
from .stats import ADC_SHIFT, STORED_FULL_SCALE

EXE = Path(r"C:\Program Files\PixInsight\bin\PixInsight.exe")

# Long enough that a real integration is not cut off, short enough that a typo
# costs ten minutes rather than a session.  A caller that knows its job is
# longer passes its own; what must never happen is `None` (L17).
DEFAULT_TIMEOUT = 600.0

JOB_NAME = "job.json"
RESULT_NAME = "result.json"

# `SplitCFA` enumerates the 2x2 tile in PixInsight's (x, y) order with y
# varying fastest, and PI's first coordinate is the column.  In numpy's
# (row, col) terms that transposes the two greens; R and B sit on the diagonal
# and are unmoved (L21).  The trap is that the error is invisible to a median
# comparison, because both greens share a median on a real frame -- so the
# contract compares the minimum, which is a single pixel and cannot hide it.
CFA_ORDER = ("R", "G2", "G1", "B")


def to_adc(v):
    """A PixInsight pixel value, in ADC counts.

    PI normalises to [0, 1] by the **container** maximum 65535, not by the
    sensor's saturation level and not by full scale (L20).  So a PI value is
    a stored value over 65535, and this project's one unit is the stored value
    over 16 (`CLAUDE.md`).  The two divisions compose to 65535/16 = 4095.9375,
    which is the number that matters here: multiplying a PI value by 4095 is
    wrong by 0.023% and looks right, which is the worst way for it to be wrong.

    This is one of the four places stored units are allowed to survive, and it
    is the reason the constant below is spelled out of `stats` rather than
    written as a literal.
    """
    a = np.asarray(v, dtype=np.float64)
    if np.any(a < 0.0) or np.any(a > 1.0):
        raise ValueError("PixInsight values are normalised to [0, 1]; "
                         f"got range {float(a.min())} to {float(a.max())}")
    return a * (STORED_FULL_SCALE / (1 << ADC_SHIFT))


def matching_stats(plane):
    """Our numbers for one plane, in PixInsight's own conventions.

    Only for the contract comparison.  `pcl::Variance` returns the **sample**
    variance, dividing by n-1, where `ndarray.std()` divides by n (L22).  On a
    Bayer sub-plane of a full frame the two differ by a factor of 1 + 2.4e-7
    and nothing would ever notice -- but the test that proves this mapping runs
    on a dozen hand-checkable values, where the same factor is 4%, and a
    contract that only holds at large n is not a contract.

    `min` is here because it is the cheapest statistic that a single misplaced
    pixel can move, which is what makes it the one that catches a wrong CFA
    mapping (L21).
    """
    a = np.asarray(plane, dtype=np.float64)
    return {"min": float(a.min()), "max": float(a.max()),
            "mean": float(a.mean()), "median": float(np.median(a)),
            "std": float(a.std(ddof=1))}


def run(script, job=None, timeout=DEFAULT_TIMEOUT, workdir=None, keep=False):
    """Run one PJSR script headless and return what it wrote.

    `job` is written as JSON beside the script's working directory and read
    back by the script as a relative path; the result comes back the same way.
    Returns the parsed result dict.

    Raises `TimeoutError` if the process outlives `timeout` -- and kills the
    process *tree*, because PixInsight's launcher is not always the process
    that hangs.  Raises `RuntimeError` if the run ends with no result file,
    which is the only reliable statement of failure available: PixInsight's
    exit code says nothing (L17), so it is reported in the error message as
    context and never tested.

    `stderr` is captured and returned rather than raised on.  PixInsight prints
    GLES errors to it on every headless launch and they are harmless (L24); a
    harness that treated stderr as failure would fail every single run.
    """
    script = Path(script).resolve()
    if not script.is_file():
        raise FileNotFoundError(f"no such PJSR script: {script}")
    if not EXE.is_file():
        raise FileNotFoundError(f"PixInsight not found at {EXE}")

    cwd = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="pjsr-"))
    cwd.mkdir(parents=True, exist_ok=True)
    result_path = cwd / RESULT_NAME
    if result_path.exists():
        result_path.unlink()
    (cwd / JOB_NAME).write_text(json.dumps(job or {}, indent=2), encoding="utf-8")

    try:
        completed = _launch(script, cwd, timeout)
        if not result_path.exists():
            raise RuntimeError(
                f"{script.name} wrote no {RESULT_NAME}. PixInsight returned "
                f"{completed.returncode}, which proves nothing either way.\n"
                f"stderr: {completed.stderr[-2000:] if completed.stderr else '(none)'}")
        # `errors="replace"`: the file is UTF-8 until the core puts its own
        # words in it, and those come in the system code page -- a Windows
        # error on this machine is German, and one umlaut in the only
        # diagnosis there is must not be what makes it unreadable.
        result = json.loads(result_path.read_text(encoding="utf-8",
                                                  errors="replace"))
        result["stderr"] = completed.stderr
        result["returncode"] = completed.returncode
        result["workdir"] = str(cwd)
        return result
    finally:
        if not keep and not workdir:
            shutil.rmtree(cwd, ignore_errors=True)


def _launch(script, cwd, timeout):
    """The command line, and the bounded wait around it.

    Every flag earns its place (L16):

    - `-n` is **not optional**.  Without it PixInsight yields to an already
      running instance by default, so a harness run is silently handed to
      whatever GUI session happens to be open, and the result never appears.
    - `--run=` is always the long form.  `-r` means `--run` to the OS launcher
      but `--runtime` to PixInsight's own internal `run` command, which is a
      different argument layer entirely.
    - `--automation-mode` suppresses informative and warning messages.  It does
      **not** suppress a fatal argument-parse error, which happens before the
      automation machinery exists and arrives as a modal dialog.
    - `--force-exit` so a finished script does not leave the core resident.

    `-a=` and `-p=` belong to the internal layer only and are never passed
    here; on the OS command line they are exactly what produces the dialog
    that waits forever.
    """
    argv = [str(EXE), "-n", "--automation-mode",
            f"--run={script}", "--force-exit"]
    proc = subprocess.Popen(argv, cwd=str(cwd), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True,
                            errors="replace", stdin=subprocess.DEVNULL)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc.pid)
        out, err = proc.communicate()
        raise TimeoutError(
            f"{Path(script).name} did not finish in {timeout:.0f} s and was "
            "killed. A modal dialog under --automation-mode is the usual "
            "cause, and an open GUI instance is the other (L16, L24).")
    return subprocess.CompletedProcess(argv, proc.returncode, out, err)


def _kill_tree(pid):
    """Kill the process and its children.

    `taskkill /T` rather than `Popen.kill`, because killing the launcher alone
    can leave the core running and holding the instance slot -- which makes the
    *next* run fail for a reason that has nothing to do with the next run.
    `--terminate=<slot>` exists for a wedged instance but the invoking process
    may itself not exit, so even that would need a timeout (L17).
    """
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=30, check=False)


def scripts_dir():
    """Where the PJSR scripts live.  Resolved from the package so that a
    notebook run from anywhere finds them."""
    return Path(__file__).resolve().parents[1] / "pjsr"


def pi_path(p):
    """A path as PJSR wants it: absolute, forward slashes.

    PixInsight accepts forward slashes on Windows and a backslash inside a
    JSON string is an escape character, so a Windows path that survives
    `json.dumps` intact still has to survive whatever reads it back.  Doing the
    conversion once, here, is cheaper than one script at a time getting it
    right.
    """
    return str(Path(p).resolve()).replace(os.sep, "/")


# --------------------------------------------------------------------------
# contract 2: what a difference and a stack are worth
# --------------------------------------------------------------------------

# The pedestal PixelMath adds to a difference so that the negative half of it
# survives.  Half of [0, 1] is the only value that is safe for *any* sigma the
# difference can have without running off either end, and it is subtracted back
# out by nothing: it moves the mean and leaves the standard deviation alone,
# which is the whole trick (L23).
DIFF_PEDESTAL = 0.5


def sigma_from_pair(sigma_diff):
    """Per-frame sigma from the sigma of a difference of two frames.

    Two frames drawn from the same distribution and subtracted give a
    difference whose variance is the *sum* of theirs, so `sigma_diff` is
    `sigma * sqrt(2)` and the frame's own sigma is this.  It is the estimator
    every bias pair in this project uses, and it is the reason a pair
    difference is blind to anything fixed: whatever is common to both frames
    cancels before the variance is taken.

    **It is also the number L23's trap halves.**  A difference of two unsigned
    16-bit images clips every negative value at zero, and a difference centred
    on zero is negative half the time -- so the surviving distribution is a
    half-normal, whose standard deviation is smaller by a factor that looks
    entirely plausible on a real bias.  Nothing in the arithmetic here can
    detect that; it has to be prevented upstream, by subtracting in 32-bit
    float about `DIFF_PEDESTAL` with truncation off.
    """
    return float(sigma_diff) / np.sqrt(2.0)


def eta_comb(sigma_single, sigma_stack, n):
    """Combination efficiency: what a real stack achieved against the ideal.

    Averaging `n` independent frames divides the noise by `sqrt(n)`, and no
    stack reaches that.  `eta_comb` is the ratio of the ideal to the achieved
    -- 1.0 for a perfect stack, below 1.0 for every real one -- and MISSION's
    model carries it as the factor between `sqrt(N) * SNR_sub` and the SNR the
    integrated image actually has.

    What it is *not* is a property of the camera.  It is a property of the
    combination: the rejection algorithm and its thresholds, the normalisation,
    the weighting, and -- once frames are registered -- the resampling kernel.
    Two of those change it by more than the sensor ever could, which is why
    MISSION requires its provenance to record the stack size and the rejection
    settings it was measured under.  A number quoted without them is not a
    measurement of anything.

    Measured on unregistered frames it is an **upper bound**, because the one
    term that is guaranteed to cost something -- resampling a rotated, dithered
    frame onto a common grid -- has been left out by construction.  The gap
    between that bound and the same measurement on registered lights *is* the
    resampling loss, and there is no other way to get at it.
    """
    n = int(n)
    if n < 2:
        raise ValueError(f"a stack of {n} frames has nothing to combine")
    ideal = float(sigma_single) / np.sqrt(n)
    return ideal / float(sigma_stack)


# --------------------------------------------------------------------------
# contract 3: registered planes and stacks, read back
# --------------------------------------------------------------------------

def read_adc(path):
    """A file PixInsight wrote, in ADC counts.

    Two shapes arrive, and both cross the unit boundary here and nowhere
    else.  StarAlignment writes 16-bit XISF in **stored** units, and its
    values are interpolated, so they are no longer multiples of 16 and
    `stats.to_adc` would rightly refuse them; stored over 65535 is exactly
    PixInsight's own normalised value (L20), so they go through `to_adc` like
    any other PI value.  ImageIntegration writes 32-bit float already in
    [0, 1].
    """
    p = Path(path)
    a = fits.read_xisf(p) if p.suffix.lower() == ".xisf" else fits.read(p)[0]
    a = np.asarray(a)
    if np.issubdtype(a.dtype, np.integer):
        return to_adc(a.astype(np.float64) / STORED_FULL_SCALE)
    return to_adc(a)
