"""Fixed income account model.

Holdings are stored as {isin: notional_face_value}. All monetary values are in
USD. Prices are expressed as percentage of par (e.g. 98.50 = $98.50 per $100
face value), so a $10,000 notional position at 98.50 has a market value of $9,850.

Minimum trade size is $1,000 notional; trades must be in $1,000 increments.
"""

from pydantic import BaseModel
import json
from dotenv import load_dotenv
from datetime import datetime
from .market import get_instrument_data, get_instrument_price, get_instrument_sell_price
from .instruments import UNIVERSE
from .database import write_account, read_account, write_log

load_dotenv(override=True)

INITIAL_BALANCE = 100_000.0
MIN_NOTIONAL = 1_000.0


class Transaction(BaseModel):
    isin: str
    instrument_name: str
    notional: float     # face value traded (positive = buy, negative = sell)
    price: float        # execution price as % of par
    ytm: float          # yield at execution (%)
    timestamp: str
    rationale: str

    def market_value(self) -> float:
        return self.notional * self.price / 100

    def __repr__(self):
        side = "Bought" if self.notional > 0 else "Sold"
        return (
            f"{side} ${abs(self.notional):,.0f} notional of {self.instrument_name} "
            f"at {self.price:.2f} (YTM {self.ytm:.2f}%)"
        )


class Account(BaseModel):
    name: str
    balance: float
    strategy: str
    holdings: dict[str, float]          # isin → notional face value
    transactions: list[Transaction]
    portfolio_value_time_series: list[tuple[str, float]]

    @classmethod
    def get(cls, name: str):
        fields = read_account(name.lower())
        if not fields:
            fields = {
                "name": name.lower(),
                "balance": INITIAL_BALANCE,
                "strategy": "",
                "holdings": {},
                "transactions": [],
                "portfolio_value_time_series": [],
            }
            write_account(name, fields)
        return cls(**fields)

    def save(self):
        write_account(self.name.lower(), self.model_dump())

    def reset(self, strategy: str = ""):
        self.balance = INITIAL_BALANCE
        self.strategy = strategy
        self.holdings = {}
        self.transactions = []
        self.portfolio_value_time_series = []
        self.save()

    # ── Trading ──────────────────────────────────────────────────────────────

    def buy_instrument(self, isin: str, notional: float, rationale: str) -> str:
        """Buy a fixed income instrument.

        Args:
            isin:      Instrument identifier from the universe.
            notional:  Face value to buy (must be ≥ 1,000 and a multiple of 1,000).
            rationale: Reasoning for the trade.
        """
        if isin not in UNIVERSE:
            raise ValueError(f"Unknown instrument: {isin}. Check list_instruments for valid ISINs.")
        if notional < MIN_NOTIONAL or notional % MIN_NOTIONAL != 0:
            raise ValueError(
                f"Notional must be a positive multiple of {MIN_NOTIONAL:,.0f}. Got {notional:,.0f}."
            )

        price = get_instrument_price(isin)    # buy price (ask side, spread applied)
        data  = get_instrument_data(isin)
        cost  = notional * price / 100

        if cost > self.balance:
            raise ValueError(
                f"Insufficient funds. Cost ${cost:,.2f} exceeds balance ${self.balance:,.2f}."
            )

        self.holdings[isin] = self.holdings.get(isin, 0.0) + notional
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tx = Transaction(
            isin=isin,
            instrument_name=UNIVERSE[isin].name,
            notional=notional,
            price=price,
            ytm=data["ytm"],
            timestamp=timestamp,
            rationale=rationale,
        )
        self.transactions.append(tx)
        self.balance -= cost
        self.save()
        write_log(self.name, "account", f"Bought ${notional:,.0f} of {isin}")
        return "Completed. Latest details:\n" + self.report()

    def sell_instrument(self, isin: str, notional: float, rationale: str) -> str:
        """Sell a fixed income instrument.

        Args:
            isin:      Instrument identifier from the universe.
            notional:  Face value to sell (must be ≤ current holding).
            rationale: Reasoning for the trade.
        """
        if isin not in UNIVERSE:
            raise ValueError(f"Unknown instrument: {isin}.")
        held = self.holdings.get(isin, 0.0)
        if notional > held:
            raise ValueError(
                f"Cannot sell ${notional:,.0f} of {isin}; only ${held:,.0f} held."
            )
        if notional < MIN_NOTIONAL or notional % MIN_NOTIONAL != 0:
            raise ValueError(
                f"Notional must be a positive multiple of {MIN_NOTIONAL:,.0f}."
            )

        price    = get_instrument_sell_price(isin)    # sell price (bid side)
        data     = get_instrument_data(isin)
        proceeds = notional * price / 100

        self.holdings[isin] -= notional
        if self.holdings[isin] < MIN_NOTIONAL:
            del self.holdings[isin]

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tx = Transaction(
            isin=isin,
            instrument_name=UNIVERSE[isin].name,
            notional=-notional,
            price=price,
            ytm=data["ytm"],
            timestamp=timestamp,
            rationale=rationale,
        )
        self.transactions.append(tx)
        self.balance += proceeds
        self.save()
        write_log(self.name, "account", f"Sold ${notional:,.0f} of {isin}")
        return "Completed. Latest details:\n" + self.report()

    # ── Portfolio valuation ───────────────────────────────────────────────────

    def calculate_portfolio_value(self) -> float:
        total = self.balance
        for isin, notional in self.holdings.items():
            try:
                mid_price = get_instrument_data(isin)["price"]
                total += notional * mid_price / 100
            except Exception:
                pass
        return total

    def calculate_profit_loss(self, portfolio_value: float) -> float:
        """Total P&L = portfolio value − initial capital deployed."""
        cost_basis = sum(
            tx.notional * tx.price / 100
            for tx in self.transactions
            if tx.notional > 0
        )
        proceeds = sum(
            abs(tx.notional) * tx.price / 100
            for tx in self.transactions
            if tx.notional < 0
        )
        return portfolio_value - self.balance - (cost_basis - proceeds)

    def get_holdings(self) -> dict[str, float]:
        return self.holdings

    def report(self) -> str:
        portfolio_value = self.calculate_portfolio_value()
        self.portfolio_value_time_series.append(
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), portfolio_value)
        )
        self.save()
        pnl = self.calculate_profit_loss(portfolio_value)
        data = self.model_dump()
        data["total_portfolio_value"] = portfolio_value
        data["total_profit_loss"] = pnl
        write_log(self.name, "account", "Retrieved account details")
        return json.dumps(data)

    def get_strategy(self) -> str:
        write_log(self.name, "account", "Retrieved strategy")
        return self.strategy

    def change_strategy(self, strategy: str) -> str:
        self.strategy = strategy
        self.save()
        write_log(self.name, "account", "Changed strategy")
        return "Changed strategy"
