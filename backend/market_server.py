"""MCP server exposing fixed income market data tools.

Agents call these tools to look up yield curves, instrument prices,
duration, DV01, and the full tradeable universe.
"""

import json
from mcp.server.fastmcp import FastMCP
from .market import get_yield_curve, get_instrument_data
from .instruments import UNIVERSE

mcp = FastMCP("market_server")


@mcp.tool()
async def get_treasury_yield_curve() -> str:
    """Return the current US Treasury yield curve as a JSON object.

    Keys are tenor labels (1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y, 30Y).
    Values are yields in percent (e.g. 4.5 means 4.50%).
    Use this to analyse curve shape, identify relative value, and infer
    duration positioning opportunities.
    """
    curve = get_yield_curve()
    return json.dumps(curve)


@mcp.tool()
async def get_instrument_price_and_risk(isin: str) -> str:
    """Return current price and risk metrics for a fixed income instrument.

    Returns a JSON object with:
      - price: clean price as % of par (e.g. 98.50)
      - ytm: yield to maturity in percent
      - modified_duration: price sensitivity in years
      - dv01_per_1k: dollar change per 1bp yield move, per $1,000 notional
      - treasury_yield: the underlying Treasury rate for this maturity
      - spread_bps: credit spread over Treasury

    Args:
        isin: Instrument identifier (e.g. 'UST10Y', 'AAPL5Y', 'TY'). Use
              list_tradeable_instruments to see all available ISINs.
    """
    data = get_instrument_data(isin)
    return json.dumps(data)


@mcp.tool()
async def list_tradeable_instruments() -> str:
    """Return the full universe of tradeable fixed income instruments as JSON.

    Each entry includes the ISIN, name, type (treasury/ig_corp/hy_corp/future/swap),
    maturity in years, coupon rate, credit rating, issuer, and spread over Treasury.
    Use this to find instruments that fit your strategy.
    """
    universe = [
        {
            "isin": isin,
            "name": inst.name,
            "instrument_type": inst.instrument_type,
            "maturity_years": inst.maturity_years,
            "coupon_rate": inst.coupon_rate,
            "credit_rating": inst.credit_rating,
            "issuer": inst.issuer,
            "spread_bps": inst.spread_bps,
        }
        for isin, inst in UNIVERSE.items()
    ]
    return json.dumps(universe)


if __name__ == "__main__":
    mcp.run(transport='stdio')
