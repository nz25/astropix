"""model.py -- the provenance gate, the two gain terms, and the SNR itself.

Nothing here reads a frame or a Z: mount.  The model consumes published
constants and arithmetic, so its tests are constants and arithmetic, and the
few that touch `results/` read the committed files that are already in git.
"""

import json
import math

import pytest

from astropix import model as M

GOOD = {"value": 1.0, "unit": "e-", "uncertainty": 0.1, "source_frames": 10,
        "measured_on": "2026-09-19", "notebook": "99_test.ipynb"}


def _write(tmp_path, name, entries):
    p = tmp_path / name
    p.write_text(json.dumps(entries))
    return p


# --------------------------------------------------------------------------
# the provenance gate (CLAUDE.md)
# --------------------------------------------------------------------------

def test_a_constant_without_provenance_does_not_load(tmp_path):
    for field in M.PROVENANCE:
        entry = {k: v for k, v in GOOD.items() if k != field}
        p = _write(tmp_path, f"no_{field}.json", {"x": entry})
        with pytest.raises(ValueError, match=field):
            M.Constants.load(p)


def test_a_bare_value_is_not_a_constant(tmp_path):
    p = _write(tmp_path, "bare.json", {"x": 3.0})
    with pytest.raises(ValueError, match="bare value"):
        M.Constants.load(p)


def test_a_published_null_raises_and_quotes_its_reason(tmp_path):
    """A null in `results/` is a finding with a note attached, not a number.
    The note is nearly always the instruction for what to use instead -- as
    `ceiling` is, pointing at `linear_to_at_least` -- so it must reach the
    caller rather than being swallowed by a KeyError."""
    entry = dict(GOOD, value=None, note="no sustained departure before the clip")
    c = M.Constants.load(_write(tmp_path, "null.json", {"ceiling": entry}))
    with pytest.raises(ValueError, match="no sustained departure"):
        c["ceiling"]
    assert c.entry("ceiling")["value"] is None, "the stanza stays readable"


def test_two_files_disagreeing_about_a_name_refuse_rather_than_pick(tmp_path):
    """`setpoint` is the real case: -10 C from the bench sessions and -20 C
    from the cold one, both correct.  Loading both must not silently return
    whichever file was passed second."""
    a = _write(tmp_path, "a.json", {"setpoint": dict(GOOD, value=-10.0)})
    b = _write(tmp_path, "b.json", {"setpoint": dict(GOOD, value=-20.0)})
    c = M.Constants.load(a, b)
    with pytest.raises(KeyError, match="more than one file"):
        c["setpoint"]
    # and a name only one of them publishes is unaffected
    assert M.Constants.load(a, _write(tmp_path, "c.json", {"other": GOOD}))["other"] == 1.0


def test_the_same_value_in_two_files_is_not_a_conflict(tmp_path):
    a = _write(tmp_path, "a.json", {"setpoint": dict(GOOD, value=-10.0)})
    b = _write(tmp_path, "b.json", {"setpoint": dict(GOOD, value=-10.0)})
    assert M.Constants.load(a, b)["setpoint"] == -10.0


def test_pick_reaches_into_a_table_and_refuses_a_null_inside_it(tmp_path):
    table = dict(GOOD, value={"50": 3958.0, "200": None}, note="a note")
    c = M.Constants.load(_write(tmp_path, "t.json", {"lin": table}))
    assert c.pick("lin", 50) == 3958.0, "an int key finds a JSON string key"
    assert c.pick("lin", "50") == 3958.0
    with pytest.raises(ValueError, match="published null"):
        c.pick("lin", 200)
    with pytest.raises(KeyError):
        c.pick("lin", 100)


def test_the_committed_constants_all_pass_their_own_gate():
    """Every JSON file in `results/` must be loadable by the model.  This is
    the one test that would catch a notebook publishing a constant without its
    provenance, and it costs nothing to run."""
    from pathlib import Path
    for p in sorted(Path("results").glob("*.json")):
        M.Constants.load(p)


# --------------------------------------------------------------------------
# the gain domain (CLAUDE.md) and the two gain-dependent terms
# --------------------------------------------------------------------------

@pytest.mark.parametrize("gain", [-1, 451, 600])
def test_gain_outside_the_domain_is_refused(gain):
    with pytest.raises(ValueError, match="characterised domain"):
        M.check_gain(gain)


def test_g_interpolates_log_linearly_and_hits_the_measured_rungs():
    table = {"0": 10.0, "100": 1.0}
    assert M.g_at(0, table) == pytest.approx(10.0)
    assert M.g_at(100, table) == pytest.approx(1.0)
    # halfway in gain is the geometric mean in g, not the arithmetic one
    assert M.g_at(50, table) == pytest.approx(math.sqrt(10.0))


def test_the_model_does_not_extrapolate_a_sweep():
    with pytest.raises(ValueError, match="does not extrapolate"):
        M.g_at(200, {"0": 10.0, "100": 1.0})


def test_read_noise_multiplies_two_independently_measured_tables():
    counts = {"100": 2.0, "200": 1.0}
    g = {"100": 3.0, "200": 3.0}
    assert M.read_noise_e(200, counts, g) == pytest.approx(3.0)
    assert M.read_noise_e(100, counts, g) == pytest.approx(6.0)


def test_the_pedestal_switches_branch_at_the_hcg_threshold():
    """The two branches are two conversion stages, not one curve fitted twice:
    `B` falls from 2.67 to 0.97 across the threshold.  A continuous pedestal
    here would mean the split was an artefact."""
    fit = {"lcg": {"A": 60.0861, "B": 2.665683},
           "hcg": {"A": 59.6217, "B": 0.965156}}
    assert M.pedestal_counts(0, fit, 200) == pytest.approx(62.7518, abs=1e-3)
    assert M.pedestal_counts(200, fit, 200) == pytest.approx(69.2733, abs=1e-3)
    below, above = (M.pedestal_counts(g, fit, 200) for g in (198, 200))
    assert below > above, "the branch change is a step down, not a continuation"


def test_eta_interpolates_in_log_N():
    table = {"2": 1.0, "8": 0.5}
    assert M.eta_at(4, table) == pytest.approx(0.75), "4 is halfway in doublings"
    with pytest.raises(ValueError, match="not a stack"):
        M.eta_at(0, table)


# --------------------------------------------------------------------------
# the model
# --------------------------------------------------------------------------

SKY = {"f_sky": 1.933, "dark": 0.000534, "read_e": 0.881, "t_dead": 31.46}


def test_dead_time_is_floored_because_a_part_sub_is_lost():
    assert M.subs_in(3600, 60, 0) == 60
    assert M.subs_in(3600, 60, 31.46) == 39, "overhead costs a third of the night"
    assert M.subs_in(100, 60, 31.46) == 1, "the remainder is not a sub"


def test_snr_sub_keeps_the_object_in_its_own_shot_term():
    """Dropping `f_obj` from the variance is the standard faint-source
    approximation and this model does not make it: on a source at 1% of sky it
    is worth half a percent, and the whole gate is a 10% ranking."""
    kw = {"f_sky": 2.0, "dark": 0.0, "read_e": 1.0}
    with_obj = M.snr_sub(0.02, 60, **kw)
    without = 0.02 * 60 / math.sqrt(2.0 * 60 + 1.0)
    assert with_obj < without
    assert with_obj == pytest.approx(without, rel=0.01)


def test_snr_at_fixed_wall_clock_never_turns_over():
    """The result the module is shaped around: no interior optimum in `t`.
    If this ever fails, `efficiency` is answering the wrong question and the
    module needs an `optimal_t` after all."""
    flat = {"1": 1.0, "100000": 1.0}       # eta held out of the way
    prev = 0.0
    for t in (5, 10, 20, 40, 80, 160, 320, 640, 1280):
        s = M.snr_stack(0.01, t, 6 * 3600, eta_table=flat, **SKY)["snr"]
        assert s > prev, f"SNR fell at t={t}"
        prev = s


def test_efficiency_is_the_two_fractions_multiplied():
    """`efficiency` must stay readable as exposing-fraction times
    sky-dominance, because that decomposition is what makes it usable at the
    mount."""
    t = 120
    a = SKY["f_sky"] + SKY["dark"]
    expected = math.sqrt((t / (t + SKY["t_dead"]))
                         * (a * t / (a * t + SKY["read_e"] ** 2)))
    assert M.efficiency(t, **SKY) == pytest.approx(expected)


def test_efficiency_rises_to_one_and_t_for_efficiency_inverts_it():
    assert M.efficiency(1e9, **SKY) == pytest.approx(1.0, abs=1e-4)
    for target in (0.5, 0.8, 0.9, 0.95, 0.99):
        t = M.t_for_efficiency(target, **SKY)
        assert M.efficiency(t, **SKY) == pytest.approx(target)
    with pytest.raises(ValueError, match="strictly between"):
        M.t_for_efficiency(1.0, **SKY)


def test_no_read_noise_and_no_overhead_needs_no_exposure_at_all():
    """The degenerate branch is real, not defensive: it is what says that the
    whole sub-length question is made of exactly those two terms."""
    assert M.t_for_efficiency(0.99, f_sky=2.0, dark=0.0,
                              read_e=0.0, t_dead=0.0) == 0.0


# --------------------------------------------------------------------------
# the star-colour constraint
# --------------------------------------------------------------------------

def test_the_colour_ceiling_round_trips_through_peak_counts():
    kw = {"f_sky": 1.933, "dark": 0.000534, "pedestal": 65.0, "g": 0.5005}
    t = M.t_max_colour(400.0, ceiling=3854.0, **kw)
    assert M.peak_counts(400.0, t, **kw) == pytest.approx(3854.0)


def test_a_ceiling_at_the_pedestal_refuses_rather_than_returning_zero():
    with pytest.raises(ValueError, match="no room for signal"):
        M.t_max_colour(400.0, f_sky=1.0, dark=0.0, pedestal=65.0,
                       ceiling=65.0, g=0.5)


# --------------------------------------------------------------------------
# the verdict (MISSION's definition of done)
# --------------------------------------------------------------------------

def test_rank_calls_a_pair_apart_only_against_measured_repeatability():
    close = M.rank(103.0, 100.0, 5.0)
    assert close["winner"] == "a" and not close["apart"], "3% inside a 5% floor"
    far = M.rank(103.0, 100.0, 1.0)
    assert far["apart"] and far["separation_pct"] == pytest.approx(3.0)
    assert M.rank(100.0, 103.0, 1.0)["winner"] == "b"


def test_repeatability_has_no_default_and_no_zero():
    """A default here would turn MISSION's gate into a formality: every pair
    separates from zero."""
    with pytest.raises(TypeError):
        M.rank(100.0, 103.0)
    with pytest.raises(ValueError, match="measured and positive"):
        M.rank(100.0, 103.0, 0.0)
