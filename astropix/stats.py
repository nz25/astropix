"""Robust noise statistics on a CFA sub-plane.

The estimator is fixed by evidence, not by taste (DECISIONS D24): **reject
outliers with a MAD-scaled cut, then take the standard deviation of the
survivors.**  Neither half works alone.  MAD is an order statistic of deviations
that are quantised to 16 file-ADU, so it can only return multiples of
1.4826 x 16 = 23.72 -- on this rig it reads exactly one ADC step on ~90% of all
calibration frames, and it returns *zero* below about half a step.  Plain
standard deviation is nearly immune to the grid, because rounding error averages
over millions of pixels instead of being read off one order statistic, but it is
not immune to stars and hot pixels.

Two corrections separate this from a naive clipped std, and both matter at the
1% level that the PTC intercept -- the read noise -- is fit at:

**Quantisation (Sheppard).**  Rounding to a grid of step *q* behaves like adding
an independent uniform error of width *q*, and variances of independent things
add, so every variance measured on this rig is inflated by a constant
q^2/12 = 21.33 file-ADU^2.  It is an *additive* offset, so on a variance-vs-signal
plot it moves the intercept and leaves the slope alone: it lands squarely on
R(gain) and not at all on g(gain).  Subtract it.

**Truncation.**  Clipping at +-k sigma throws away the tails of the very
distribution being measured, so the survivors' std runs low -- 1.5% at k = 3.
The shrinkage factor is analytic for a Gaussian, so divide it back out rather
than choosing k large enough not to care.

Where the corrections stop working is a measured question, not an assumed one:
Sheppard's model needs the noise to dither the quantiser, and below roughly one
step the rounding stops being random and becomes a deterministic function of the
signal.  `astropix.test.quantiser_bias` maps that floor; `results/quantiser_bias.csv`
records it.
"""

from __future__ import annotations

import math

import numpy as np

QUANTUM = 16.0    # file-ADU per ADC count: a 12-bit ADC bit-shifted into 16 bits
CLIP_K = 4.0      # rejection window, in robust sigmas
CLIP_ITERS = 3

MAD_TO_SIGMA = 1.4826


def sheppard_variance(quantum=QUANTUM):
    """The variance a quantiser of step `quantum` adds to everything it stores."""
    return quantum * quantum / 12.0


def _truncation_factor(k):
    """var(survivors) / var(parent) for a Gaussian clipped at +-k sigma.

    1 - 2k phi(k) / (2 Phi(k) - 1).  At k = 3 this is 0.971, so an uncorrected
    3-sigma clipped std reads 1.5% low -- comfortably larger than the read-noise
    precision this project needs.
    """
    if not np.isfinite(k) or k > 12.0:
        return 1.0
    phi = math.exp(-0.5 * k * k) / math.sqrt(2.0 * math.pi)
    mass = math.erf(k / math.sqrt(2.0))          # 2 Phi(k) - 1
    return 1.0 - 2.0 * k * phi / mass


def clipped_std(a, k=CLIP_K, iters=CLIP_ITERS, quantum=QUANTUM):
    """Std of the survivors of a MAD-scaled cut, truncation-corrected.

    Returns (sigma_uncorrected, centre, kept_fraction).  `sigma_uncorrected`
    still carries the quantiser's q^2/12; `sigma` applies that subtraction.

    The rejection window is floored at one quantum.  Without the floor a frame
    whose MAD comes back zero -- which happens whenever the noise is under about
    half a step, and it is the *normal* case for bias frames here -- would open a
    zero-width window and reject every pixel that is not exactly at the median.
    D24's "the cut only needs to be roughly right" is what makes the floor safe:
    a distribution narrower than one step has no resolvable outliers to reject.
    """
    x = np.asarray(a, dtype=np.float64).ravel()
    if x.size < 2:
        return float("nan"), float("nan"), 0.0

    centre = float(np.median(x))
    scale = MAD_TO_SIGMA * float(np.median(np.abs(x - centre)))
    kept = 1.0

    for _ in range(iters):
        window = k * max(scale, quantum)
        m = np.abs(x - centre) <= window
        if m.sum() < 2:
            break
        surv = x[m]
        centre = float(surv.mean())
        raw = float(surv.std())
        kept = float(m.mean())
        if raw <= 0.0:
            scale = 0.0
            break
        # k_eff, not k: when the window is held open by the quantum floor the
        # clip is far out in the tails and there is nothing to correct back.
        scale = raw / math.sqrt(_truncation_factor(window / raw))

    return scale, centre, kept


def sigma(a, k=CLIP_K, iters=CLIP_ITERS, quantum=QUANTUM):
    """The shipping estimator: robust, truncation- and Sheppard-corrected.

    Returns noise in file-ADU.  Returns 0.0, not a negative or a nan, when the
    corrected variance goes non-positive -- that is a frame whose noise this
    quantiser cannot resolve, and the honest reading is "below the grid", which
    the caller must handle rather than feed to a fit.
    """
    raw, _, _ = clipped_std(a, k=k, iters=iters, quantum=quantum)
    if not np.isfinite(raw):
        return float("nan")
    return math.sqrt(max(raw * raw - sheppard_variance(quantum), 0.0))


def pair_variance(a, b, k=CLIP_K, iters=CLIP_ITERS, quantum=QUANTUM):
    """Temporal variance from two frames at identical settings, in file-ADU^2.

    var(a - b) / 2.  This is the estimator the PTC wants, because differencing
    cancels every fixed pattern -- pixel-response non-uniformity, amp glow, the
    dust motes in a flat -- and leaves only what changed between two reads.  A
    single frame's spatial variance cannot separate those from shot noise.

    The difference is quantised twice, once per frame, so it carries 2 x q^2/12;
    halving it brings the correction back to the same q^2/12 subtracted
    everywhere else.
    """
    d = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    raw, _, _ = clipped_std(d, k=k, iters=iters, quantum=quantum)
    return 0.5 * raw * raw - sheppard_variance(quantum)


def pair_sigma(a, b, **kw):
    """Per-frame noise in file-ADU, from a pair difference."""
    return math.sqrt(max(pair_variance(a, b, **kw), 0.0))
