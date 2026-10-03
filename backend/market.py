"""Market data: live Treasury yields from FRED, or the synthetic simulator.

Set FRED_API_KEY in .env to use live data from the Federal Reserve's FRED API
(free registration at fred.stlouisfed.org). Without it the simulator runs out
of the box with a realistic Nelson-Siegel yield curve.

All yields are expressed in percent (e.g. 4.5 means 4.5%). Bond prices are
returned as percentage of par (e.g. 98.50 = $98.50 per $100 face value).
"""

import os
import math
from datetime import datetime, timezone
from functools import lru_cache
from dotenv import load_dotenv
from .instruments import UNIVERSE, SPREADS, Instrument

load_dotenv(override=True)

fred_api_key = os.getenv("FRED_API_KEY")

# FRED series IDs for on-the-run Treasury constant-maturity yields
_FRED_TREASURY_SERIES: dict[str, str] = {
    "1M": "DGS1MO", "3M": "DGS3MO", "6M": "DGS6MO",
    "1Y": "DGS1",   "2Y": "DGS2",   "5Y": "DGS5",
    "10Y": "DGS10", "30Y": "DGS30",
}

# Tenor order for interpolation
_TENOR_YEARS: dict[str, float] = {
    "1M": 1/12, "3M": 3/12, "6M": 6/12,
    "1Y": 1.0, "2Y": 2.0, "5Y": 5.0, "10Y": 10.0, "30Y": 30.0,
}

# Simple in-process cache so we don't hammer FRED on every price lookup
_curve_cache: dict[str, float] | None = None
_curve_cached_at: datetime | None = None
_CACHE_TTL_SECONDS = 3600  # refresh at most once per hour


# ── Yield curve retrieval ────────────────────────────────────────────────────

def _fetch_fred_curve() -> dict[str, float]:
    """Fetch the latest Treasury CMT yields from FRED."""
    from fredapi import Fred  # optional dependency; only imported when key is set
    fred = Fred(api_key=fred_api_key)
    curve: dict[str, float] = {}
    for tenor, series_id in _FRED_TREASURY_SERIES.items():
        try:
            data = fred.get_series(series_id).dropna()
            if len(data):
                curve[tenor] = float(data.iloc[-1])
        except Exception as e:
            print(f"FRED fetch failed for {series_id}: {e}")
    return curve


def get_yield_curve() -> dict[str, float]:
    """Return the current Treasury yield curve as {tenor: yield%}.

    Uses FRED when a key is available (cached hourly), otherwise the
    Nelson-Siegel simulator.
    """
    global _curve_cache, _curve_cached_at
    if fred_api_key:
        now = datetime.now(timezone.utc)
        stale = (
            _curve_cache is None
            or _curve_cached_at is None
            or (now - _curve_cached_at).total_seconds() > _CACHE_TTL_SECONDS
        )
        if stale:
            try:
                _curve_cache = _fetch_fred_curve()
                _curve_cached_at = now
            except Exception as e:
                print(f"FRED unavailable ({e}); using simulated curve")
                if _curve_cache is None:
                    from .market_simulator import simulated_yield_curve
                    _curve_cache = simulated_yield_curve()
        return _curve_cache or {}
    from .market_simulator import simulated_yield_curve
    return simulated_yield_curve()


# ── Yield interpolation ──────────────────────────────────────────────────────

def interpolate_yield(curve: dict[str, float], maturity_years: float) -> float:
    """Log-linearly interpolate a yield for an arbitrary maturity."""
    points = sorted(
        [(years, curve[tenor]) for tenor, years in _TENOR_YEARS.items() if tenor in curve],
        key=lambda x: x[0],
    )
    if not points:
        return 4.0  # fallback

    if maturity_years <= points[0][0]:
        return points[0][1]
    if maturity_years >= points[-1][0]:
        return points[-1][1]

    for i in range(len(points) - 1):
        t0, y0 = points[i]
        t1, y1 = points[i + 1]
        if t0 <= maturity_years <= t1:
            # Linear interpolation in log-maturity space
            frac = (math.log(maturity_years) - math.log(t0)) / (math.log(t1) - math.log(t0))
            return y0 + frac * (y1 - y0)
    return points[-1][1]


# ── Bond pricing ─────────────────────────────────────────────────────────────

def price_from_yield(coupon_rate_pct: float, maturity_years: float, ytm_pct: float, freq: int = 2) -> float:
    """Standard bond price as percentage of par.

    Args:
        coupon_rate_pct: Annual coupon rate in percent (e.g. 4.5).
        maturity_years:  Years to maturity.
        ytm_pct:         Yield to maturity in percent.
        freq:            Coupon frequency (2 = semi-annual).

    Returns:
        Price as percentage of par (e.g. 98.50).
    """
    n = max(1, round(maturity_years * freq))
    c = (coupon_rate_pct / 100) / freq    # periodic coupon per $1 face
    y = (ytm_pct / 100) / freq            # periodic yield

    if coupon_rate_pct == 0.0:
        # Zero-coupon / futures approximation
        price = 1.0 / (1 + y) ** n
    elif abs(y) < 1e-9:
        price = c * n + 1.0
    else:
        price = c * (1 - (1 + y) ** (-n)) / y + (1 + y) ** (-n)

    return round(price * 100, 4)


def modified_duration(coupon_rate_pct: float, maturity_years: float, ytm_pct: float, freq: int = 2) -> float:
    """Modified duration in years."""
    n = max(1, round(maturity_years * freq))
    c = (coupon_rate_pct / 100) / freq
    y = (ytm_pct / 100) / freq

    if abs(y) < 1e-9:
        # Approximate for near-zero yield
        mac = sum(t * c for t in range(1, n + 1)) + n * 1.0
        mac /= (c * n + 1.0)
        return mac / freq

    price_per_1 = price_from_yield(coupon_rate_pct, maturity_years, ytm_pct, freq) / 100

    mac = 0.0
    for t in range(1, n + 1):
        cf = c if t < n else (c + 1.0)
        mac += t * cf / (1 + y) ** t
    mac /= price_per_1

    return round(mac / freq / (1 + y), 4)


def dv01_per_unit(coupon_rate_pct: float, maturity_years: float, ytm_pct: float) -> float:
    """DV01 per $1 face value (dollar change for a 1bp move in yield)."""
    dur = modified_duration(coupon_rate_pct, maturity_years, ytm_pct)
    price = price_from_yield(coupon_rate_pct, maturity_years, ytm_pct) / 100
    return round(dur * price * 0.0001, 8)


# ── Instrument data ──────────────────────────────────────────────────────────

def get_instrument_data(isin: str) -> dict:
    """Return current market data for an instrument.

    Returns a dict with price (% of par), ytm (%), modified_duration,
    dv01 per $1k notional, and current yield curve.
    """
    instrument = UNIVERSE.get(isin)
    if not instrument:
        raise ValueError(f"Unknown instrument: {isin}")

    curve = get_yield_curve()
    tsy_yield = interpolate_yield(curve, instrument.maturity_years)

    # YTM = Treasury yield + credit spread
    ytm_pct = tsy_yield + instrument.spread_bps / 100

    # For swaps: use Treasury yield + small swap spread (swap rate ≈ OIS ≈ Treasury)
    if instrument.instrument_type == "swap":
        # Swap fixed rate is approximately the Treasury yield at that tenor
        swap_fixed_rate = tsy_yield + instrument.spread_bps / 100
        # Value the swap as a bond: pay fixed = short a fixed-rate bond at par
        # We model the "price" as the NPV expressed as % of notional
        # Use the coupon = swap_fixed_rate, price starts near 100
        ytm_pct = swap_fixed_rate
        coupon = tsy_yield  # current market swap rate ≈ current treasury yield
    else:
        coupon = instrument.coupon_rate

    price = price_from_yield(coupon, instrument.maturity_years, ytm_pct)
    dur = modified_duration(coupon, instrument.maturity_years, ytm_pct)
    dv01 = dv01_per_unit(coupon, instrument.maturity_years, ytm_pct) * 1000  # per $1k

    return {
        "isin": isin,
        "name": instrument.name,
        "instrument_type": instrument.instrument_type,
        "maturity_years": instrument.maturity_years,
        "coupon_rate": coupon,
        "credit_rating": instrument.credit_rating,
        "price": price,
        "ytm": round(ytm_pct, 4),
        "modified_duration": dur,
        "dv01_per_1k": round(dv01, 4),
        "treasury_yield": round(tsy_yield, 4),
        "spread_bps": instrument.spread_bps,
    }


def get_instrument_price(isin: str) -> float:
    """Return the current clean price as % of par (buy-side, spread applied)."""
    data = get_instrument_data(isin)
    instrument = UNIVERSE[isin]
    spread = SPREADS.get(instrument.instrument_type, 0.002)
    return round(data["price"] * (1 + spread), 4)


def get_instrument_sell_price(isin: str) -> float:
    """Return the current clean price as % of par (sell-side, spread applied)."""
    data = get_instrument_data(isin)
    instrument = UNIVERSE[isin]
    spread = SPREADS.get(instrument.instrument_type, 0.002)
    return round(data["price"] * (1 - spread), 4)


def is_market_open() -> bool:
    """Bond markets are open weekdays; always True when using the simulator."""
    if not fred_api_key:
        return True
    now = datetime.now()
    return now.weekday() < 5  # Mon–Fri
