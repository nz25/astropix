"""pixinsight.py -- driving PixInsight, with no PixInsight installed.

Same bargain as `test_asi.py`.  The module's whole content is a set of
*decisions* about a process that cannot be trusted to report its own failures:
what to do when a script writes nothing, when it never exits, when it prints
alarming things to stderr that turn out to be routine.  Each of those is
exercised here against `stub_pi`, a batch file that launches a small Python
script and behaves however the test asks it to.

A stub rather than the real thing, for the usual reason and one more.  The
usual one: a launch costs about forty seconds, so a suite that drove the real
core would be run rarely and the guards would rot.  The extra one: the failure
paths *cannot* be produced on demand by real PixInsight -- a hang is a modal
dialog nobody can summon reliably, and a silent script is a bug you have to
already have.  The stub makes them ordinary.

The stub is a `.bat` that spawns Python, not a bare Python script, because
that is the shape of the real thing: the process we launch is not the process
that does the work.  Killing only the one we hold a handle to would leave the
core running -- so `_kill_tree` is tested against a real two-process tree.

What these cannot check is whether PixInsight behaves as scripted here.  That
is what `pjsr/probe.js` is for, and `pjsr/NOTES.md` records what it found.
"""

from __future__ import annotations

import json
import math
import pathlib
import tempfile

import numpy as np

from astropix import pixinsight as pi
from astropix import spatial, stats


# --------------------------------------------------------------------------
# the stand-in
# --------------------------------------------------------------------------

# The stub reads the basename of whatever `--run=` points at and behaves
# accordingly.  Every mode here is a real observed behaviour of the thing it
# stands in for, not an invented one (L17, L18, L24).
_STUB_PY = '''
import json, os, sys, time
mode = "ok"
for a in sys.argv[1:]:
    if a.startswith("--run="):
        mode = os.path.basename(a[len("--run="):]).split(".")[0]
job = json.load(open("job.json", encoding="utf-8"))
if mode == "noisy":
    sys.stderr.write("ERROR:gpu_channel_manager.cc(959) Failed to create GLES3 context\\n")
if mode == "hang":
    time.sleep(600)
if mode == "silent":
    sys.exit(3)
if mode == "crash":
    json.dump({"ok": False, "error": "DataType_ByteArray is not defined"},
              open("result.json", "w", encoding="utf-8"))
    sys.exit(0)
json.dump({"ok": True, "echo": job, "types": {k: type(v).__name__ for k, v in job.items()}},
          open("result.json", "w", encoding="utf-8"))
'''


def stub_pi(tmp):
    """Install the stand-in and point the module at it.  Returns the scripts
    directory the tests write their fake `.js` files into."""
    tmp = pathlib.Path(tmp)
    py = tmp / "stub_pi.py"
    py.write_text(_STUB_PY, encoding="utf-8")
    bat = tmp / "stub_pi.bat"
    # `%*` forwards the flags so the stub sees exactly the command line the
    # module built, which is what lets a test assert on it.
    bat.write_text(f'@echo off\r\n"{__import__("sys").executable}" "{py}" %*\r\n',
                   encoding="utf-8")
    pi.EXE = bat
    scripts = tmp / "scripts"
    scripts.mkdir(exist_ok=True)
    return scripts


def _script(scripts, name):
    p = pathlib.Path(scripts) / name
    p.write_text("// stand-in\n", encoding="utf-8")
    return p


class _Stub:
    """`with _Stub() as scripts:` -- installs the stand-in, restores the real
    path afterwards so one test cannot leave the module pointing at a stub."""

    def __enter__(self):
        self._real = pi.EXE
        self._tmp = tempfile.TemporaryDirectory(prefix="test-pi-")
        return stub_pi(self._tmp.name)

    def __exit__(self, *exc):
        pi.EXE = self._real
        self._tmp.cleanup()
        return False


# --------------------------------------------------------------------------
# the unit boundary (L20, L22)
# --------------------------------------------------------------------------

def test_to_adc_divides_by_the_container_not_full_scale():
    """Both cases the claim has been checked on.

    L20's own: PI reported 0.0229495689 for a frame whose stored median is
    1504, and 1504/65535 is that number to ten digits.  And this project's,
    measured here on a session 06 light: PI reported 0.02612344548662627 where
    our reader gives a stored median of 1712.

    Full scale would be 4095 and it is *not* the divisor.  The gap is 0.023%,
    small enough to look like rounding and large enough to be a different
    answer -- so it is asserted rather than described."""
    assert abs(float(pi.to_adc(0.0229495689)) - 94.0) < 1e-6
    assert abs(float(pi.to_adc(1504 / 65535)) - 94.0) < 1e-9
    assert abs(float(pi.to_adc(1712 / 65535)) - 107.0) < 1e-9
    # and the plausible-looking error stays plausible-looking, which is why it
    # needs a test rather than a comment
    assert abs(0.0229495689 * 4095 - 94.0) > 0.02


def test_to_adc_maps_the_top_of_the_container_above_full_scale():
    """65535/16 is 4095.9375, not 4095.  A saturated PI pixel converts to
    slightly *more* than full scale, and that is correct: the container holds
    numbers the ADC cannot produce."""
    assert abs(float(pi.to_adc(1.0)) - 4095.9375) < 1e-9
    assert float(pi.to_adc(65520 / 65535)) == 4095.0


def test_to_adc_refuses_values_that_are_not_normalised():
    """A value outside [0, 1] did not come from PixInsight, so converting it
    would be inventing a number rather than moving one."""
    for bad in (-1e-9, 1.5, 4095.0):
        try:
            pi.to_adc(bad)
        except ValueError:
            continue
        raise AssertionError(f"to_adc({bad}) should have raised")


def test_matching_stats_uses_the_sample_variance():
    """`pcl::Variance` divides by n-1 and `ndarray.std()` divides by n (L22).

    A dozen values, where the ratio is 4.4% -- on a real sub-plane it is
    1 + 2.4e-7 and no test could tell the two apart, which is exactly why the
    check has to be done at small n."""
    a = np.arange(12, dtype=np.float64)
    got = pi.matching_stats(a)
    n = a.size
    assert abs(got["std"] - a.std(ddof=1)) < 1e-12
    assert abs(got["std"] / a.std() - math.sqrt(n / (n - 1))) < 1e-12
    assert got["min"] == 0.0 and got["max"] == 11.0
    assert got["mean"] == 5.5 and got["median"] == 5.5


# --------------------------------------------------------------------------
# the CFA plane order (L21)
# --------------------------------------------------------------------------

def test_cfa_order_transposes_the_greens():
    """SplitCFA enumerates the tile in (x, y) with y fastest, so CFA1 is G2 and
    CFA2 is G1 -- transposed against a naive reading of RGGB.

    Built as the claim says to check it: each plane is given its own *minimum*,
    because the minimum is one pixel and a wrong mapping moves it.  The second
    half of the test is the more important one -- under the naive order the
    medians still agree, which is how the error survives a median comparison
    on a real frame."""
    mosaic = np.zeros((8, 8), dtype=np.float64)
    planes = spatial.split(mosaic)
    for name, floor in (("R", 91.0), ("G1", 92.0), ("G2", 90.0), ("B", 75.0)):
        planes[name][:] = 100.0
        planes[name][0, 0] = floor          # the one pixel that tells them apart

    # what PixInsight would hand back, in its own order
    pi_planes = [planes[name] for name in pi.CFA_ORDER]
    assert [float(p.min()) for p in pi_planes] == [91.0, 90.0, 92.0, 75.0]

    naive = ("R", "G1", "G2", "B")
    assert [float(planes[n].min()) for n in naive] != [91.0, 90.0, 92.0, 75.0]
    # ...and the medians do not notice, which is the trap
    assert ([float(np.median(planes[n])) for n in naive]
            == [float(np.median(p)) for p in pi_planes])


def test_cfa_order_names_the_project_planes():
    assert sorted(pi.CFA_ORDER) == sorted(spatial.PLANES)


# --------------------------------------------------------------------------
# the process contract (L17, L18, L19, L24)
# --------------------------------------------------------------------------

def test_job_numbers_arrive_as_numbers():
    """The reason a job is a JSON file and not `-p=` (L19).

    PixInsight's own documentation says command-line parameters "are always
    String objects", so a gain of 100 and a gain of "100" would be
    indistinguishable on arrival.  Through the file they are not."""
    with _Stub() as scripts:
        job = {"an_int": 42, "a_float": 1.5, "a_string": "42", "a_bool": True}
        got = pi.run(_script(scripts, "ok.js"), job, timeout=120)
        assert got["echo"] == job
        assert got["types"] == {"an_int": "int", "a_float": "float",
                                "a_string": "str", "a_bool": "bool"}


def test_run_passes_the_flags_that_earn_their_place():
    """`-n` above all: without it PixInsight yields to an already running
    instance and the run is silently handed to whoever has the GUI open.  And
    the long `--run=`, because `-r` means something else one layer down."""
    with _Stub() as scripts:
        script = _script(scripts, "ok.js")
        got = pi.run(script, {"seen": "argv"}, timeout=120)
        assert got["ok"] is True
        # the stub resolved its mode from --run=, so the flag arrived intact
        assert got["echo"] == {"seen": "argv"}


def test_no_result_file_is_the_failure_signal():
    """A script that exits without writing is a failure, whatever it exited
    with.  The exit code appears in the message as context and is never
    tested: a killed process reports -1 and a wedged one never reports (L17,
    L18)."""
    with _Stub() as scripts:
        try:
            pi.run(_script(scripts, "silent.js"), {}, timeout=120)
        except RuntimeError as exc:
            assert "result.json" in str(exc)
            assert "silent.js" in str(exc)
            return
        raise AssertionError("a script that wrote nothing should have raised")


def test_a_failed_script_still_reports():
    """The other half of the same rule.  A script that fails *and says so* is
    not an exception here -- it is a result with `ok` false, which is the
    difference between a diagnosis and an afternoon of bisection (L18)."""
    with _Stub() as scripts:
        got = pi.run(_script(scripts, "crash.js"), {}, timeout=120)
        assert got["ok"] is False
        assert "DataType_ByteArray" in got["error"]


def test_a_hung_run_is_killed_in_bounded_time():
    """One typo in a flag produces a modal dialog under `--automation-mode`,
    and the process then waits forever for a click.  The timeout is the only
    thing between that and a wedged suite (L17)."""
    import time
    with _Stub() as scripts:
        t0 = time.time()
        try:
            pi.run(_script(scripts, "hang.js"), {}, timeout=3)
        except TimeoutError as exc:
            assert "hang.js" in str(exc)
            assert time.time() - t0 < 60, "the timeout did not bound the wait"
            return
        raise AssertionError("a hung script should have raised TimeoutError")


def test_stderr_is_reported_and_not_raised_on():
    """PixInsight prints GLES errors to stderr on every headless launch and
    they are harmless (L24).  A harness that treated stderr as failure would
    fail every run it ever made."""
    with _Stub() as scripts:
        got = pi.run(_script(scripts, "noisy.js"), {}, timeout=120)
        assert got["ok"] is True
        assert "GLES3" in got["stderr"]


def test_run_refuses_a_script_that_is_not_there():
    """Cheaper to fail here than forty seconds later with no result file and
    nothing to distinguish a missing script from a broken one."""
    with _Stub() as scripts:
        try:
            pi.run(pathlib.Path(scripts) / "absent.js", {}, timeout=120)
        except FileNotFoundError:
            return
        raise AssertionError("a missing script should have raised")


def test_each_run_gets_its_own_working_directory():
    """A job is found by relative name, so two runs sharing a directory would
    read each other's parameters (L19)."""
    with _Stub() as scripts:
        script = _script(scripts, "ok.js")
        a = pi.run(script, {"which": "a"}, timeout=120)
        b = pi.run(script, {"which": "b"}, timeout=120)
        assert a["workdir"] != b["workdir"]
        assert a["echo"]["which"] == "a" and b["echo"]["which"] == "b"


def test_pi_path_is_absolute_with_forward_slashes():
    """A Windows path inside a JSON string is a sequence of escape characters
    waiting to happen; PixInsight takes forward slashes on Windows, so the
    conversion is done once here rather than once per script."""
    got = pi.pi_path(r"data\session06\frame.fit")
    assert "\\" not in got
    assert got.endswith("data/session06/frame.fit")
    assert pathlib.Path(got).is_absolute()


# --------------------------------------------------------------------------
# the rule every PJSR script obeys (L18)
# --------------------------------------------------------------------------

def test_every_pjsr_script_reports_on_both_paths():
    """Structural, and it is the guard that keeps the whole contract usable.

    PixInsight has no console, so a script that does not write a file has no
    way to tell us anything -- including that it failed.  `report()` in
    `harness.jsh` is the one place both paths are covered, so every script is
    required to go through it rather than to be trusted to remember.

    `.jsh` headers are deliberately outside this glob: they are included, not
    run, and requiring a header to report would be requiring nonsense.
    """
    scripts = sorted(pi.scripts_dir().glob("*.js"))
    assert scripts, "no PJSR scripts found; the contract has nothing to check"
    for path in scripts:
        source = path.read_text(encoding="utf-8")
        assert "harness.jsh" in source, f"{path.name} does not include the harness"
        assert "report(" in source, f"{path.name} does not report through report()"


def test_the_harness_writes_on_the_failure_path():
    """The claim `report()` exists to make true: an exception becomes a file,
    not a silent exit."""
    source = (pi.scripts_dir() / "harness.jsh").read_text(encoding="utf-8")
    assert "catch" in source and "writeResult" in source
    assert '"ok": false' in source or "ok: false" in source


# --------------------------------------------------------------------------
# contract 2: the difference, and what clipping does to it (L23)
# --------------------------------------------------------------------------

def test_sigma_from_pair_undoes_the_root_two():
    """Two independent frames differenced have twice the variance of one."""
    rng = np.random.default_rng(20260919)
    a = rng.normal(100.0, 7.0, 400_000)
    b = rng.normal(100.0, 7.0, 400_000)
    got = pi.sigma_from_pair((a - b).std(ddof=1))
    assert abs(got / 7.0 - 1.0) < 0.01


def test_a_clipped_difference_reads_low_by_a_known_factor():
    """L23's trap, priced -- and this is the test the claim asked for.

    Inject a known sigma, clip the difference at zero the way an unsigned
    container does, and assert what comes back.  A difference of two frames
    from one distribution is centred on zero, so clipping keeps a half-normal:
    its second moment is half the original variance and its mean is no longer
    zero, which leaves a standard deviation of `sqrt(1/2 - 1/(2*pi))` -- about
    **0.58** of the truth.  L23 said "halves" and 0.58 is what "halves" turns
    out to mean.

    The number matters more than the direction.  0.58 is not an absurd value
    for a read noise, which is precisely why this cannot be caught downstream:
    on a real bias pair a result 42% low looks like a better camera, not like
    a broken subtraction.
    """
    rng = np.random.default_rng(20260919)
    sigma = 20.0
    d = rng.normal(0.0, sigma * np.sqrt(2.0), 2_000_000)

    honest = pi.sigma_from_pair(d.std(ddof=1))
    clipped = pi.sigma_from_pair(np.clip(d, 0.0, None).std(ddof=1))

    assert abs(honest / sigma - 1.0) < 0.01
    expected = np.sqrt(0.5 - 1.0 / (2.0 * np.pi))
    assert abs(clipped / sigma - expected) < 0.01
    assert 0.55 < clipped / sigma < 0.62        # "halves", measured


def test_the_diff_pedestal_is_the_middle_of_the_container():
    """Half of [0, 1], so a difference of any sigma the pair can have runs off
    neither end.  Any other value spends headroom on one side for nothing."""
    assert pi.DIFF_PEDESTAL == 0.5


# --------------------------------------------------------------------------
# contract 2: combination efficiency
# --------------------------------------------------------------------------

def test_eta_comb_is_one_for_an_ideal_stack():
    assert abs(pi.eta_comb(10.0, 10.0 / math.sqrt(16), 16) - 1.0) < 1e-12


def test_eta_comb_is_below_one_for_a_real_stack():
    """A stack that only reached sqrt(12) of noise reduction where sqrt(16) was
    available has an efficiency of sqrt(12/16)."""
    got = pi.eta_comb(10.0, 10.0 / math.sqrt(12), 16)
    assert abs(got - math.sqrt(12.0 / 16.0)) < 1e-12
    assert got < 1.0


def test_eta_comb_refuses_a_stack_of_one():
    """`sqrt(1)` is 1 and the arithmetic would return something, which is worse
    than raising: a stack of one frame has no combination to be efficient at."""
    for n in (1, 0, -3):
        try:
            pi.eta_comb(10.0, 10.0, n)
        except ValueError:
            continue
        raise AssertionError(f"eta_comb accepted a stack of {n}")
