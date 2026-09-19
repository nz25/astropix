"""The SNR model: what a setting buys, and what it costs in star colour.

This is the module MISSION exists to produce.  Everything before it measured a
term; this one puts the terms together and turns them into a comparison between
two capture settings.  The equation it implements is written out in full in
`MISSION.md` and is not restated here -- what *is* here is the reasoning that
the equation alone does not carry.

**Nothing in this module measures anything.**  It consumes constants that other
notebooks published, and it refuses to run on a constant that does not carry
its provenance (`CLAUDE.md`).  That refusal is the first third of the file and
it is not ceremony: the whole point of the project is that a recommendation can
be traced back to the frames behind it, and a model that accepts a bare float
has broken that chain at the last possible moment.

**Units.**  Fluxes are electrons per pixel per second, times are seconds, read
noise is electrons, and pixel levels are ADC counts (`CLAUDE.md`).  The two
meet in exactly two places -- `peak_counts` and `t_max_colour`, the star-colour
constraint -- and both divide by `g` explicitly so the conversion is visible.

**The result that shapes everything else: there is no interior optimum in t.**
Differentiate the SNR at fixed wall clock and the stationary condition reduces
to `t(R^2 + A*t_dead) + 2*R^2*t_dead = 0`, whose left side is strictly positive
for every positive t.  So SNR climbs monotonically with sub length and flattens
towards an asymptote; it never turns over.  Longer is always better, and
`eta_comb` pushes the same way, because a longer sub means fewer subs and this
rig's combination efficiency falls with stack size.

That is why this module has no `optimal_t`.  Asking for the maximum of a
monotonic function is asking the wrong question, and a function called
`optimal_t` would have had to invent a stopping rule to return anything at all.
The optimum is set by the *constraints* -- the star-colour ceiling, what the
mount tracks, what a passing cloud costs -- so what the model owes the decision
is **how much of the asymptote a given t reaches** (`efficiency`) and **where
the ceiling bites** (`t_max_colour`).  The gap between those two is MISSION's
Pareto curve.

`efficiency` is also the piece that runs in your head at the mount, which
MISSION requires of the whole model: it is one square root over two products,
and at 120 s against this rig's measured 31.5 s of dead time it says most of
the loss is overhead rather than read noise.

**What is assumed here, and is not the model's to fix.**  MISSION's four
assumptions are the model's shape, and three of them are now measured.  The
survivor is the first: sigma^2 is shot plus read and nothing else.  The PTC
session disagrees -- `fpn_term_present` is True and `prnu` is 1.02% of signal
-- and a fixed-pattern term does not scale with t, so it would weaken the
claim that `R^2/t` is the whole question.  **No FPN term is added here**, for
the reason MISSION gives: a term earns its place by changing a decision, and
nothing has yet shown that this one does.  Where it will show up if it does is
`eta_comb`, which is where noise that fails to average away goes to be counted.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

# --- the provenance gate (CLAUDE.md) -----------------------------------------
PROVENANCE = ("value", "unit", "uncertainty", "source_frames",
              "measured_on", "notebook")

# --- the gain domain (CLAUDE.md; cited, not restated) ------------------------
GAIN_MIN, GAIN_MAX = 0, 450


class Conflict:
    """A name published by two files with different values.

    Kept as a value rather than raised at load time, so that loading a set of
    files does not fail over a name nobody in this run is going to ask for.
    `setpoint` is the standing example: the bench sessions published -10 C and
    the cold session published -20 C, both correctly, and a model that wanted
    neither should still be able to load both files.
    """

    def __init__(self, name, sources):
        self.name, self.sources = name, sources

    def raise_(self):
        where = ", ".join(f"{s} = {v!r}" for s, v in self.sources)
        raise KeyError(f"{self.name!r} is published by more than one file with "
                       f"different values ({where}); load one of them, or pass "
                       f"the value you mean explicitly")


class Constants:
    """Published constants, with the provenance that licenses using them.

    Load with `Constants.load(paths)` and read with `c["name"]`.  Four things
    are refused rather than worked around, and each one is a way a number has
    historically got into a result without anybody deciding it should:

    1.  **A missing provenance field.**  All six of `value`, `unit`,
        `uncertainty`, `source_frames`, `measured_on`, `notebook` or the entry
        does not load.  This is the rule from `CLAUDE.md`, enforced where the
        constant is consumed rather than where it is written, because the
        writer is the one party who already knows the number is good.
    2.  **A published null.**  `results/` deliberately holds constants whose
        value is `None` with a `note` saying why -- `ceiling` is a null with a
        reason on all twelve gain-plane fits, and that null *is* the finding.
        It is still not a number, so reading one raises and quotes the note,
        which is almost always the explanation of what to use instead.
    3.  **A name two files disagree about.**  See `Conflict`.
    4.  **A value that is a table, asked for as a scalar.**  Use `pick`.

    What it does *not* do is check the number is right.  Provenance is a chain
    of custody, not a proof; `results/` is the record of truth and this class
    only refuses to launder it.
    """

    def __init__(self, entries):
        self._e = entries

    @classmethod
    def load(cls, *paths):
        """Read one or more `results/*.json` files into one namespace."""
        entries = {}
        for p in paths:
            p = Path(p)
            for name, entry in json.loads(p.read_text()).items():
                if not isinstance(entry, dict):
                    raise ValueError(f"{p.name}:{name} is a bare value, not a "
                                     f"constant with provenance")
                missing = [f for f in PROVENANCE if f not in entry]
                if missing:
                    raise ValueError(f"{p.name}:{name} lacks {', '.join(missing)}; "
                                     f"the model does not run on unprovenanced "
                                     f"constants (CLAUDE.md)")
                entry = dict(entry, source=p.name)
                prev = entries.get(name)
                if isinstance(prev, Conflict):
                    prev.sources.append((p.name, entry["value"]))
                elif prev is not None and prev["value"] != entry["value"]:
                    entries[name] = Conflict(name, [(prev["source"], prev["value"]),
                                                    (p.name, entry["value"])])
                else:
                    entries[name] = entry
        return cls(entries)

    def __contains__(self, name):
        return name in self._e

    def entry(self, name):
        """The whole stanza -- value, unit, uncertainty, note, source."""
        try:
            e = self._e[name]
        except KeyError:
            raise KeyError(f"{name!r} is not published in the files loaded; "
                           f"have {sorted(self._e)}") from None
        if isinstance(e, Conflict):
            e.raise_()
        return e

    def __getitem__(self, name):
        e = self.entry(name)
        if e["value"] is None:
            raise ValueError(f"{name!r} is published null with a reason, not "
                             f"measured: {e.get('note', '(no note)')}")
        return e["value"]

    def pick(self, name, key):
        """One entry out of a constant whose value is a table.

        Tables here are keyed by gain or by CFA plane, and JSON makes every key
        a string, so `pick(name, 200)` and `pick(name, '200')` mean the same
        thing.  A `None` inside a table is the same kind of published null as a
        `None` at the top, and raises the same way.
        """
        table = self[name]
        if not isinstance(table, dict):
            raise TypeError(f"{name!r} is not a table")
        k = str(key)
        if k not in table:
            raise KeyError(f"{name!r} has no entry for {key!r}; "
                           f"has {sorted(table)}")
        if table[k] is None:
            note = self.entry(name).get("note", "(no note)")
            reasons = self._e.get("not_measured")
            why = (reasons["value"].get(k) if isinstance(reasons, dict)
                   and isinstance(reasons.get("value"), dict) else None)
            raise ValueError(f"{name!r}[{key!r}] is published null with a "
                             f"reason, not measured: {why or note}")
        return table[k]

    def cite(self, *names):
        """`name (notebook, date)` for each, for a notebook to print.

        The explaining notebook's job is to say where a number came from, and
        the provenance is already loaded here; making it print is cheaper than
        making somebody retype it and get the date wrong.
        """
        out = []
        for n in names:
            e = self.entry(n)
            out.append(f"{n} = {e['value']!r} {e['unit']} "
                       f"({e['notebook']}, {e['measured_on']})")
        return "\n".join(out)


# --- the two gain-dependent terms --------------------------------------------

def check_gain(gain):
    """Refuse a gain outside the characterised domain (`CLAUDE.md`)."""
    if not GAIN_MIN <= gain <= GAIN_MAX:
        raise ValueError(f"gain {gain} is outside the characterised domain "
                         f"{GAIN_MIN}-{GAIN_MAX}; see the gain-domain rule in "
                         f"CLAUDE.md")
    return gain


def _interp_table(table, x, log_y=False, log_x=False):
    """Linear interpolation over a numeric-keyed table, refusing to extrapolate.

    Refusing is the point.  Every table this module reads is a sweep with a
    first and a last rung, and a value past either end is a statement about a
    setting nobody measured.
    """
    pts = sorted((float(k), v) for k, v in table.items() if v is not None)
    xs = [p[0] for p in pts]
    if not xs:
        raise ValueError("the table has no measured points")
    if not xs[0] <= x <= xs[-1]:
        raise ValueError(f"{x} is outside the measured range {xs[0]}-{xs[-1]}; "
                         f"the model does not extrapolate a sweep")
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            break
    if x1 == x0:
        return float(y0)
    fx = (math.log(x / x0) / math.log(x1 / x0)) if log_x else (x - x0) / (x1 - x0)
    if log_y:
        return 10.0 ** (math.log10(y0) + fx * (math.log10(y1) - math.log10(y0)))
    return y0 + fx * (y1 - y0)


def g_at(gain, table):
    """System gain in electrons per ADC count, at an arbitrary gain setting.

    Interpolated in **log g against linear gain**, over the measured rungs --
    not from the fitted gain law, and the difference matters at exactly one
    place.  Log-linear is the right interpolant by construction: the control is
    in units of 0.1 dB, so an ideal amplifier makes log g exactly linear in it,
    and the published law fits that line to 1.34%.

    But the sensor has an HCG threshold, where the readout switches conversion
    branch and g steps discontinuously -- the PTC session measured -0.884%
    across it.  A single fitted line smears that step across the whole domain;
    interpolating between the measured points at 190 and 200 keeps it inside
    the one segment that brackets it, where it belongs.  Everywhere else the
    two agree, so this costs nothing and is right in the one place it differs.
    """
    return _interp_table(table, check_gain(gain), log_y=True)


def read_noise_e(gain, counts_table, g_table):
    """Read noise in electrons: counts at this gain, times electrons per count.

    Two tables rather than one because they are measured by different sessions
    on different frames -- read noise from bias pairs, `g` from a photon
    transfer curve -- and keeping the multiplication here means the electron
    figure is never stored anywhere it could drift out of step with either.

    The tables need not share rungs.  The bias sweep walks the gain axis in
    tens, the PTC sits at eight gains, and each is interpolated on its own.
    """
    return _interp_table(counts_table, check_gain(gain)) * g_at(gain, g_table)


def pedestal_counts(gain, fit, hcg_threshold):
    """The black level in ADC counts at this project's offset.

    Two branches, split at the HCG threshold, each of the form
    `A + B * 10**(gain/200)`.  The exponent is not a fitted shape: the control
    is in units of 0.1 dB, so the amplifier's voltage gain is `10**(dB/20)` and
    the analogue part of the pedestal rides on it exactly.  `A` is the digital
    part, and it comes out at 4.0 counts per offset unit on both branches --
    the same number, from two independent fits, which is what says the split is
    real and the form is right.

    Two branches because the conversion stage changes at the threshold and the
    black level changes with it: `B` falls from 2.67 to 0.97 across it.  One
    fit over the whole domain would be a curve through two different sensors.
    """
    branch = fit["hcg" if check_gain(gain) >= hcg_threshold else "lcg"]
    return branch["A"] + branch["B"] * 10 ** (gain / 200)


def eta_at(n_subs, table):
    """Combination efficiency at a stack size, interpolated in log2 N.

    Log in N because that is how the ladder was shot -- doublings -- and
    because whatever makes a real stack fall short of `sqrt(N)` is a fraction
    per doubling rather than per frame.

    **This number carries its rejection settings with it and they are not
    optional context.**  With rejection off, PixInsight reaches the ideal
    `sqrt(N)` to within 0.2% at every rung, so the arithmetic is exact and
    every part of `eta_comb` is the *combination*: the rejection algorithm and
    its thresholds, the weighting, and on registered frames the resampling
    kernel.  The same Winsorized setting costs 7.3% at N=3 and 1.5% at N=32, so
    a table measured under one set of settings says nothing about another.
    Which table is passed in is the caller's decision, and the caller should
    print its provenance beside the answer.
    """
    if n_subs < 1:
        raise ValueError(f"a stack of {n_subs} subs is not a stack")
    return _interp_table(table, n_subs, log_x=True)


# --- the model ---------------------------------------------------------------

def subs_in(t_night, t, t_dead):
    """How many subs a night of `t_night` seconds holds, at `t` plus overhead.

    Floored, because a part-finished sub collects photons and contributes
    nothing: it is either saved whole or it is lost to the dawn.  The floor is
    also what makes the cost of `t_dead` visible at short subs -- at this rig's
    measured 31.5 s, a 30 s sub spends more than half the night not exposing.
    """
    if t <= 0 or t_dead < 0 or t_night <= 0:
        raise ValueError("times must be positive, and overhead non-negative")
    return int(t_night // (t + t_dead))


def snr_sub(f_obj, t, *, f_sky, dark, read_e):
    """SNR of the faint signal in one sub of length `t`.

    All four fluxes are electrons per pixel per second and `read_e` is
    electrons.  `f_obj` appears in the numerator and inside the shot term,
    which is what makes this the *faint* signal case: drop it from the
    denominator and the answer is wrong by half a percent on a source at 1% of
    sky, and by a great deal on one that is not faint.
    """
    if t <= 0:
        raise ValueError("a sub has positive length")
    var = (f_obj + f_sky + dark) * t + read_e ** 2
    if var <= 0:
        raise ValueError("a variance of zero has no SNR; check the fluxes")
    return f_obj * t / math.sqrt(var)


def snr_stack(f_obj, t, t_night, *, f_sky, dark, read_e, t_dead, eta_table):
    """SNR of the integrated image, for a night of fixed length.

    Returns the SNR, the sub count it assumed, and the `eta_comb` that stack
    size implied -- all three, because the sub count is the thing the reader
    will want to sanity-check and the efficiency is the thing that is least
    transferable between sessions.

    Fixed *wall clock*, not fixed integration: the night is what is fixed and
    the overhead comes out of it.  That single choice is what stops the answer
    running away to arbitrarily short subs the moment read noise is beaten.
    """
    n = subs_in(t_night, t, t_dead)
    if n < 1:
        raise ValueError(f"a {t} s sub plus {t_dead} s overhead does not fit "
                         f"in {t_night} s")
    eta = eta_at(n, eta_table)
    return {"snr": eta * math.sqrt(n) * snr_sub(f_obj, t, f_sky=f_sky,
                                                dark=dark, read_e=read_e),
            "n_subs": n, "eta_comb": eta}


def efficiency(t, *, f_obj=0.0, f_sky, dark, read_e, t_dead):
    """Fraction of the asymptotic SNR that a sub of length `t` reaches.

    The SNR at fixed wall clock has no maximum -- see the module docstring --
    so the useful question is not where the peak is but how close to the
    ceiling a given sub length gets.  Against the `t -> infinity` limit, every
    term that does not depend on `t` cancels and what is left is

        eff(t) = sqrt( A*t^2 / ((t + t_dead) * (A*t + R^2)) ),   A = sum of fluxes

    which is the whole sub-exposure question in one line.  The two factors are
    separable and worth reading apart: `t/(t + t_dead)` is the fraction of the
    night that is actually exposing, and `A*t/(A*t + R^2)` is the fraction of
    the noise that is sky and thermal rather than read.  On this rig at
    -10 C the first is usually the smaller of the two, which is not the
    received wisdom about sub length.

    `eta_comb` is deliberately **not** in here.  It also rises with `t`, so
    including it would make the efficiency look better than the photon
    argument alone justifies, and it is the one factor that depends on the
    rejection settings rather than on the sky.  Multiply it in outside if you
    want the whole picture; keep them apart if you want to know why.
    """
    if t <= 0:
        raise ValueError("a sub has positive length")
    a = f_obj + f_sky + dark
    if a <= 0:
        raise ValueError("no sky, no object and no dark current is not a night")
    return math.sqrt(a * t * t / ((t + t_dead) * (a * t + read_e ** 2)))


def t_for_efficiency(target, *, f_obj=0.0, f_sky, dark, read_e, t_dead):
    """The shortest sub that reaches `target` of the asymptotic SNR.

    The inverse of `efficiency`, and the form the answer is usually wanted in:
    "how long until I am within 10% of the best this night can do".  Squaring
    the definition and clearing denominators gives a quadratic in `t` whose
    positive root is the answer, and it always has exactly one, because the
    constant term is negative whenever there is any read noise or any
    overhead at all.

    `target` of 1 has no finite answer -- that is what asymptotic means -- and
    asking for it raises rather than returning something large.
    """
    if not 0 < target < 1:
        raise ValueError("an efficiency target lies strictly between 0 and 1")
    a = f_obj + f_sky + dark
    q = target ** 2
    qa, qb = a * (1 - q), -q * (read_e ** 2 + a * t_dead)
    qc = -q * read_e ** 2 * t_dead
    if qb == 0 and qc == 0:
        return 0.0                 # no read noise and no overhead: any t will do
    return (-qb + math.sqrt(qb * qb - 4 * qa * qc)) / (2 * qa)


# --- the star-colour constraint ----------------------------------------------

def peak_counts(f_star_peak, t, *, f_sky, dark, pedestal, g):
    """Where a star's brightest pixel lands, in ADC counts.

    The one place in the model where electrons become counts, and it is written
    as a division by `g` rather than folded into a constant so that the
    conversion is visible at the point of use.  Compare the answer against
    `linear_to_at_least` and not against 4095: MISSION takes the conservative
    branch, and the difference between the two is 3-6% on this sensor.
    """
    if t <= 0:
        raise ValueError("a sub has positive length")
    return pedestal + (f_star_peak + f_sky + dark) * t / g


def t_max_colour(f_star_peak, *, f_sky, dark, pedestal, ceiling, g):
    """The longest sub that keeps that star's core below the trusted ceiling.

    `ceiling` is `linear_to_at_least` -- the highest level the linearity sweep
    *proved* straight -- for the reason MISSION gives: under-exposing a star by
    a few percent costs almost nothing, and trusting counts nobody proved costs
    a star colour, which no processing recovers.

    Per CFA plane, and that is the whole point of the per-plane framing: the
    exposure floor is set by the dimmest plane and this ceiling by the
    brightest, and on this sensor under these skies they differ by 74%.  A rule
    written for a mono camera hides the gap that is the Pareto curve.
    """
    head = ceiling - pedestal
    if head <= 0:
        raise ValueError(f"ceiling {ceiling} is at or below the pedestal "
                         f"{pedestal}; there is no room for signal")
    rate = f_star_peak + f_sky + dark
    if rate <= 0:
        raise ValueError("a star with no flux never clips")
    return head * g / rate


# --- the verdict -------------------------------------------------------------

def rank(snr_a, snr_b, repeatability_pct):
    """Does the model call these two settings apart, and which way?

    MISSION's definition of done needs both halves of this.  The prediction is
    a *ranking*, so what is compared is the ratio; and a pair the model calls a
    tie is not a test, because every model passes a tie and the efficiency
    curve is flat enough over the usual range that most pairs picked at random
    are one.

    `repeatability_pct` is the measured repeatability of the SNR estimator --
    two half-stacks of the same frames, differenced.  It has no default and
    cannot have one: the whole force of "predicts them apart" comes from the
    separation being compared against a number somebody measured, and a
    plausible-looking default would quietly turn the gate into a formality.
    """
    if snr_a <= 0 or snr_b <= 0:
        raise ValueError("an SNR of zero or less cannot be ranked")
    if repeatability_pct <= 0:
        raise ValueError("repeatability must be measured and positive; see "
                         "MISSION's definition of done")
    sep = 100.0 * (snr_a - snr_b) / min(snr_a, snr_b)
    return {"ratio": snr_a / snr_b,
            "separation_pct": sep,
            "winner": "a" if snr_a > snr_b else "b",
            "apart": abs(sep) > repeatability_pct,
            "repeatability_pct": repeatability_pct}
