"""Fixed income instrument universe.

All tradeable instruments are defined here. ISINs are short symbolic codes
used throughout the system. Prices are always expressed as percentage of par
(e.g. 98.50 = $98.50 per $100 face value).
"""

from pydantic import BaseModel
from typing import Literal

InstrumentType = Literal["treasury", "ig_corp", "hy_corp", "future", "swap"]

# Bid-ask spreads by instrument type (as fraction of price, applied ±per side)
SPREADS: dict[str, float] = {
    "treasury": 0.0005,   # 5bps
    "ig_corp":  0.0020,   # 20bps
    "hy_corp":  0.0050,   # 50bps
    "future":   0.0010,   # 10bps
    "swap":     0.0010,   # 10bps
}


class Instrument(BaseModel):
    isin: str
    name: str
    instrument_type: InstrumentType
    maturity_years: float
    coupon_rate: float          # annual coupon rate in percent (e.g. 4.5 = 4.5%)
    credit_rating: str
    issuer: str
    spread_bps: float           # credit spread over same-maturity Treasury, in bps


# The tradeable universe. ISINs are symbolic; coupon rates approximate issuance levels.
UNIVERSE: dict[str, Instrument] = {
    # ── US Treasuries ────────────────────────────────────────────────────────
    "UST2Y": Instrument(
        isin="UST2Y", name="US Treasury 2-Year Note",
        instrument_type="treasury", maturity_years=2.0,
        coupon_rate=4.30, credit_rating="AA+", issuer="US Treasury", spread_bps=0,
    ),
    "UST5Y": Instrument(
        isin="UST5Y", name="US Treasury 5-Year Note",
        instrument_type="treasury", maturity_years=5.0,
        coupon_rate=4.20, credit_rating="AA+", issuer="US Treasury", spread_bps=0,
    ),
    "UST10Y": Instrument(
        isin="UST10Y", name="US Treasury 10-Year Note",
        instrument_type="treasury", maturity_years=10.0,
        coupon_rate=4.30, credit_rating="AA+", issuer="US Treasury", spread_bps=0,
    ),
    "UST30Y": Instrument(
        isin="UST30Y", name="US Treasury 30-Year Bond",
        instrument_type="treasury", maturity_years=30.0,
        coupon_rate=4.50, credit_rating="AA+", issuer="US Treasury", spread_bps=0,
    ),

    # ── Investment Grade Corporates ──────────────────────────────────────────
    "AAPL5Y": Instrument(
        isin="AAPL5Y", name="Apple Inc 5-Year Bond",
        instrument_type="ig_corp", maturity_years=5.0,
        coupon_rate=4.90, credit_rating="AA+", issuer="Apple Inc", spread_bps=65,
    ),
    "MSFT7Y": Instrument(
        isin="MSFT7Y", name="Microsoft 7-Year Bond",
        instrument_type="ig_corp", maturity_years=7.0,
        coupon_rate=5.10, credit_rating="AAA", issuer="Microsoft Corp", spread_bps=75,
    ),
    "JPM10Y": Instrument(
        isin="JPM10Y", name="JPMorgan Chase 10-Year Bond",
        instrument_type="ig_corp", maturity_years=10.0,
        coupon_rate=5.40, credit_rating="A+", issuer="JPMorgan Chase", spread_bps=110,
    ),
    "GS5Y": Instrument(
        isin="GS5Y", name="Goldman Sachs 5-Year Bond",
        instrument_type="ig_corp", maturity_years=5.0,
        coupon_rate=5.20, credit_rating="A+", issuer="Goldman Sachs", spread_bps=105,
    ),

    # ── High Yield Corporates ────────────────────────────────────────────────
    "TSLA5Y": Instrument(
        isin="TSLA5Y", name="Tesla 5-Year High Yield",
        instrument_type="hy_corp", maturity_years=5.0,
        coupon_rate=7.00, credit_rating="BB", issuer="Tesla Inc", spread_bps=280,
    ),
    "F7Y": Instrument(
        isin="F7Y", name="Ford Motor 7-Year Bond",
        instrument_type="hy_corp", maturity_years=7.0,
        coupon_rate=7.50, credit_rating="BB-", issuer="Ford Motor Co", spread_bps=330,
    ),

    # ── Treasury Futures (modelled as bonds, CME 6% notional coupon) ────────
    "TY": Instrument(
        isin="TY", name="10Y Treasury Note Future",
        instrument_type="future", maturity_years=10.0,
        coupon_rate=6.00, credit_rating="N/A", issuer="CME Group", spread_bps=0,
    ),
    "US": Instrument(
        isin="US", name="30Y Treasury Bond Future",
        instrument_type="future", maturity_years=30.0,
        coupon_rate=6.00, credit_rating="N/A", issuer="CME Group", spread_bps=0,
    ),
    "TU": Instrument(
        isin="TU", name="2Y Treasury Note Future",
        instrument_type="future", maturity_years=2.0,
        coupon_rate=6.00, credit_rating="N/A", issuer="CME Group", spread_bps=0,
    ),

    # ── SOFR Interest Rate Swaps (pay-fixed / receive-SOFR) ─────────────────
    "IRS5Y": Instrument(
        isin="IRS5Y", name="5Y SOFR Interest Rate Swap",
        instrument_type="swap", maturity_years=5.0,
        coupon_rate=0.0, credit_rating="N/A", issuer="OTC", spread_bps=5,
    ),
    "IRS10Y": Instrument(
        isin="IRS10Y", name="10Y SOFR Interest Rate Swap",
        instrument_type="swap", maturity_years=10.0,
        coupon_rate=0.0, credit_rating="N/A", issuer="OTC", spread_bps=5,
    ),
}
