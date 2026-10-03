"""HTTP API over the fixed income trading floor.

Read-only JSON endpoints consumed by the Vite frontend. The trading floor
engine writes to accounts.db out of band; this only reads.

Run from the project root:
    uv run uvicorn backend.api:app --port 8000
"""

from fastapi import FastAPI, HTTPException

from backend import market
from backend.accounts import Account
from backend.database import read_log
from backend.market import get_instrument_data
from backend.instruments import UNIVERSE
from backend.trading_floor import names, lastnames, short_model_names

LOG_COLORS = {
    "trace":      "#87CEEB",
    "agent":      "#00dddd",
    "function":   "#00dd00",
    "generation": "#dddd00",
    "response":   "#aa00dd",
    "account":    "#dd0000",
}
DEFAULT_LOG_COLOR = "#87CEEB"

roster = [
    {"name": name, "lastname": lastname, "model_name": model_name}
    for name, lastname, model_name in zip(names, lastnames, short_model_names)
]
roster_by_name = {trader["name"].lower(): trader for trader in roster}

app = FastAPI(title="Fixed Income Trading Floor")


def average_cost(account: Account, isin: str) -> float:
    """Weighted-average purchase price (% of par) for this isin."""
    spend  = sum(tx.notional * tx.price / 100 for tx in account.transactions if tx.isin == isin and tx.notional > 0)
    bought = sum(tx.notional                  for tx in account.transactions if tx.isin == isin and tx.notional > 0)
    return (spend / bought * 100) if bought else 0.0  # back to % of par


def holdings_detail(account: Account) -> list[dict]:
    """Current holdings enriched with price, duration, and unrealised P&L."""
    details = []
    for isin, notional in account.holdings.items():
        try:
            data = get_instrument_data(isin)
        except Exception:
            continue
        inst     = UNIVERSE.get(isin)
        avg_pct  = average_cost(account, isin)
        mv       = notional * data["price"] / 100
        upnl     = notional * (data["price"] - avg_pct) / 100
        details.append({
            "isin":              isin,
            "name":              data["name"],
            "instrument_type":   data["instrument_type"],
            "maturity_years":    data["maturity_years"],
            "notional":          notional,
            "price":             data["price"],
            "ytm":               data["ytm"],
            "modified_duration": data["modified_duration"],
            "dv01_per_1k":       data["dv01_per_1k"],
            "avg_cost":          round(avg_pct, 4),
            "market_value":      round(mv,   2),
            "unrealized_pnl":    round(upnl, 2),
            "credit_rating":     inst.credit_rating if inst else "N/A",
        })
    return details


def require_trader(name: str) -> dict:
    trader = roster_by_name.get(name.lower())
    if not trader:
        raise HTTPException(status_code=404, detail=f"Unknown trader: {name}")
    return trader


@app.get("/api/traders")
def get_traders() -> list[dict]:
    """The four portfolio managers on the floor."""
    return roster


@app.get("/api/market")
def get_market() -> dict:
    """Which market data source is live and whether bond markets are open."""
    source = "fred" if market.fred_api_key else "simulator"
    return {"source": source, "is_market_open": market.is_market_open()}


@app.get("/api/market/yield-curve")
def get_yield_curve_endpoint() -> dict:
    """The current US Treasury yield curve."""
    return market.get_yield_curve()


@app.get("/api/traders/{name}")
def get_trader(name: str) -> dict:
    """A trader's full state: value, P&L, holdings, transactions, and history."""
    trader  = require_trader(name)
    account = Account.get(name)
    holdings = holdings_detail(account)
    portfolio_value = account.balance + sum(h["market_value"] for h in holdings)
    return {
        "name":            trader["name"],
        "lastname":        trader["lastname"],
        "model_name":      trader["model_name"],
        "balance":         account.balance,
        "strategy":        account.strategy,
        "portfolio_value": portfolio_value,
        "pnl":             account.calculate_profit_loss(portfolio_value),
        "holdings":        holdings,
        "transactions":    [tx.model_dump() for tx in account.transactions],
        "time_series":     [{"datetime": ts, "value": v} for ts, v in account.portfolio_value_time_series],
    }


@app.get("/api/traders/{name}/logs")
def get_trader_logs(name: str, last_n: int = 13) -> list[dict]:
    """Recent trace and account log lines with their panel colour."""
    require_trader(name)
    rows = list(read_log(name, last_n))
    return [
        {"datetime": ts, "type": kind, "message": message, "color": LOG_COLORS.get(kind, DEFAULT_LOG_COLOR)}
        for ts, kind, message in rows
    ]
