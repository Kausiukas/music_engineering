"""Level handling shared by every renderer in the workspace.

Workspace rule (AGENTS.md): rendered audio must stay at or below -0.7 dBFS. ``PEAK_CEILING`` is the
linear ceiling the codebase has always used for that (0.92 ~= -0.72 dBFS).

Note: ``limit_peak``/``normalize_peak`` act on *sample* peak, exactly like the inline code they
replaced. Inter-sample (true) peaks can exceed the sample peak by ~0.5 dB on bright material; use
``true_peak_dbfs`` to measure that, and a true-peak limiter if the rule must hold strictly.
"""
import numpy as np
from scipy.signal import resample_poly

PEAK_CEILING = 0.92


def sample_peak(x):
    return float(np.max(np.abs(x))) if np.size(x) else 0.0


def to_dbfs(linear):
    return 20.0 * np.log10(max(float(linear), 1e-12))


def true_peak_dbfs(x, oversample=4):
    """Inter-sample peak estimate (dBFS) via polyphase oversampling along the last axis."""
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return to_dbfs(0.0)
    return to_dbfs(np.max(np.abs(resample_poly(x, oversample, 1, axis=-1))))


def normalize_peak(x, target=1.0):
    """Scale so the sample peak equals ``target``; silent input is returned unchanged."""
    peak = np.max(np.abs(x))
    if peak > 0:
        return x / peak if target == 1.0 else x * (target / peak)
    return x


def limit_peak(x, ceiling=PEAK_CEILING):
    """Scale down only when the sample peak exceeds ``ceiling`` (no change otherwise)."""
    peak = np.max(np.abs(x))
    if peak > ceiling:
        return (x / peak) * ceiling
    return x
