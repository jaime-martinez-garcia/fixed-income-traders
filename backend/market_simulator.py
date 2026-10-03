"""Synthetic yield curve and spread simulator.

Generates a believable Treasury yield curve using the Nelson-Siegel model with
slow-drifting parameters driven by smooth Perlin-like noise. The curve is fully
deterministic given a timestamp, so replaying history always produces the same
prices. Used when no FRED_API_KEY is configured.
"""

import hashlib
import math
from datetime import datetime, timezone

EPOCH = datetime(2025, 1, 1, tzinfo=timezone.utc)

# Nelson-Siegel baseline parameters (calibrated to a circa-2025 US curve)
NS_BETA0 = 4.50   # long-run yield level (%)
NS_BETA1 = -1.00  # slope — negative = normal upward-sloping curve
NS_BETA2 = 1.20   # medium-term hump
NS_LAMBDA = 2.00  # decay factor (controls where the hump sits)

# How far each parameter can wander from its baseline
NS_SWING = {
    "beta0": 1.20,   # ±120bps level shift
    "beta1": 0.60,   # ±60bps slope change
    "beta2": 0.80,   # ±80bps curvature change
}

# OAS baselines for IG and HY (in %)
OAS_IG_BASE = 0.95   # ~95bps
OAS_HY_BASE = 3.50   # ~350bps
OAS_SWING   = 0.30   # ±30% relative swing

TENORS: dict[str, float] = {
    "1M": 1 / 12, "3M": 3 / 12, "6M": 6 / 12,
    "1Y": 1.0, "2Y": 2.0, "5Y": 5.0, "10Y": 10.0, "30Y": 30.0,
}


# ── Noise primitives (same algorithm as the equity simulator) ────────────────

def _lattice(seed: int, n: int) -> float:
    digest = hashlib.sha256(f"{seed}:{n}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF * 2 - 1


def _noise(seed: int, x: float) -> float:
    low = math.floor(x)
    t = x - low
    smooth = t * t * (3 - 2 * t)
    return _lattice(seed, low) * (1 - smooth) + _lattice(seed, low + 1) * smooth


def _wander(seed: int, x: float, octaves: int = 4) -> float:
    total, normaliser, amplitude, frequency = 0.0, 0.0, 1.0, 1.0
    for _ in range(octaves):
        total += amplitude * _noise(seed, x * frequency)
        normaliser += amplitude
        amplitude /= 2
        frequency *= 2
    return total / normaliser


# ── Nelson-Siegel yield curve ────────────────────────────────────────────────

def _ns_yield(tau: float, beta0: float, beta1: float, beta2: float) -> float:
    """Nelson-Siegel yield for maturity tau in years."""
    if tau <= 0:
        tau = 0.001
    x = tau / NS_LAMBDA
    factor = (1 - math.exp(-x)) / x
    return beta0 + beta1 * factor + beta2 * (factor - math.exp(-x))


def simulated_yield_curve(when: datetime | None = None) -> dict[str, float]:
    """Return a synthetic Treasury yield curve as {tenor: yield%}.

    Parameters drift slowly with a monthly timescale so that yield-curve
    strategies play out realistically over days and weeks.
    """
    when = when or datetime.now(timezone.utc)
    months = (when - EPOCH).total_seconds() / (86400 * 30)

    beta0 = NS_BETA0 + NS_SWING["beta0"] * _wander(1001, months)
    beta1 = NS_BETA1 + NS_SWING["beta1"] * _wander(1002, months)
    beta2 = NS_BETA2 + NS_SWING["beta2"] * _wander(1003, months)

    # Add small intraday noise (hours timescale, ±3bps)
    hours = (when - EPOCH).total_seconds() / 3600
    intraday = 0.03 * _wander(1004, hours / 8)

    curve = {}
    for tenor, tau in TENORS.items():
        raw = _ns_yield(tau, beta0, beta1, beta2) + intraday
        curve[tenor] = round(max(0.05, raw), 4)
    return curve


def simulated_oas(category: str, when: datetime | None = None) -> float:
    """Return a simulated option-adjusted spread (in %) for 'ig' or 'hy'."""
    when = when or datetime.now(timezone.utc)
    months = (when - EPOCH).total_seconds() / (86400 * 30)

    if category == "ig":
        base = OAS_IG_BASE
        seed = 2001
    else:  # hy
        base = OAS_HY_BASE
        seed = 2002

    return round(max(0.10, base * (1 + OAS_SWING * _wander(seed, months))), 4)
