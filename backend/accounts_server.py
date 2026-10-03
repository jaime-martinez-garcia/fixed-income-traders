from mcp.server.fastmcp import FastMCP
from .accounts import Account
from .instruments import UNIVERSE

mcp = FastMCP("accounts_server")


@mcp.tool()
async def get_balance(name: str) -> float:
    """Get the cash balance of the given account.

    Args:
        name: The account holder's name.
    """
    return Account.get(name).balance


@mcp.tool()
async def get_holdings(name: str) -> dict[str, float]:
    """Get the fixed income holdings of the given account.

    Returns a dict mapping instrument ISIN to face value (notional) held.

    Args:
        name: The account holder's name.
    """
    return Account.get(name).holdings


@mcp.tool()
async def buy_instrument(name: str, isin: str, notional: float, rationale: str) -> str:
    """Buy a fixed income instrument.

    Args:
        name:      Account holder's name.
        isin:      Instrument ISIN (e.g. 'UST10Y', 'AAPL5Y', 'TY'). Use list_instruments to see all.
        notional:  Face value to buy in USD (minimum 1000, multiples of 1000).
        rationale: Your reasoning for the trade and how it fits your strategy.
    """
    return Account.get(name).buy_instrument(isin, notional, rationale)


@mcp.tool()
async def sell_instrument(name: str, isin: str, notional: float, rationale: str) -> str:
    """Sell a fixed income instrument.

    Args:
        name:      Account holder's name.
        isin:      Instrument ISIN to sell.
        notional:  Face value to sell in USD (must be ≤ current holding).
        rationale: Your reasoning for the trade and how it fits your strategy.
    """
    return Account.get(name).sell_instrument(isin, notional, rationale)


@mcp.tool()
async def change_strategy(name: str, strategy: str) -> str:
    """Update your investment strategy based on lessons learned.

    Args:
        name:     Account holder's name.
        strategy: New strategy text describing your approach.
    """
    return Account.get(name).change_strategy(strategy)


@mcp.resource("accounts://accounts_server/{name}")
async def read_account_resource(name: str) -> str:
    account = Account.get(name.lower())
    return account.report()


@mcp.resource("accounts://strategy/{name}")
async def read_strategy_resource(name: str) -> str:
    account = Account.get(name.lower())
    return account.get_strategy()


if __name__ == "__main__":
    mcp.run(transport='stdio')
