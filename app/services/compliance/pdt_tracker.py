"""
Pattern Day Trader (PDT) Rule Tracker for USA Accounts.

FINRA PDT Rule:
- Account must have >= $25,000 equity to day trade
- Maximum 3 day trades in 5-business-day rolling period
- Day trade = opening and closing same position same day
- Violation results in restricted account

IMPORTANT: Spain and most other countries do NOT have PDT rules.
This tracker only enforces PDT for USA accounts.

Reference:
    https://www.finra.org/rules-guidance/rulebooks
    Rule 4210 (Margin Requirements)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

from app.shared.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class Country(Enum):
    """Country for compliance rules."""

    US = "US"
    ES = "ES"  # Spain
    UK = "UK"
    EU = "EU"


@dataclass
class DayTradeRecord:
    """Record of a day trade for PDT tracking."""

    symbol: str
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    close_price: Decimal
    quantity: Decimal
    realized_pnl: Decimal

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "open_time": self.open_time.isoformat(),
            "close_time": self.close_time.isoformat(),
            "open_price": str(self.open_price),
            "close_price": str(self.close_price),
            "quantity": str(self.quantity),
            "realized_pnl": str(self.realized_pnl),
        }


@dataclass
class PDTStatus:
    """Current PDT status for account."""

    day_trades_last_5_days: int
    max_day_trades_allowed: int
    account_equity: Decimal
    min_equity_required: Decimal
    is_restricted: bool
    restriction_reason: Optional[str] = None
    days_until_reset: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "day_trades_last_5_days": self.day_trades_last_5_days,
            "max_day_trades_allowed": self.max_day_trades_allowed,
            "account_equity": str(self.account_equity),
            "min_equity_required": str(self.min_equity_required),
            "is_restricted": self.is_restricted,
            "restriction_reason": self.restriction_reason,
            "days_until_reset": self.days_until_reset,
        }


class PDTTracker:
    """
    Track Pattern Day Trader rule (USA only).

    USA PDT Rule:
    - Account must have >= $25k equity to day trade
    - Maximum 3 day trades in 5-business-day rolling period
    - Day trade = opened and closed same position same day

    Spain and other countries: No PDT rule

    Usage:
        tracker = PDTTracker(country=Country.US)

        # Check if trade would violate PDT
        allowed, message = tracker.check_pdt_limit(
            account_equity=Decimal("30000"),
            symbol="AAPL",
            side="BUY",
        )

        # Record a trade
        tracker.record_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            price=Decimal("150"),
            trade_date=date.today(),
        )
    """

    PDT_MIN_EQUITY = Decimal("25000")
    MAX_DAY_TRADES = 3
    ROLLING_WINDOW_DAYS = 5

    def __init__(self, country: Country = Country.ES):
        """
        Initialize PDT tracker.

        Args:
            country: Country for compliance rules (ES, US, UK, EU)
        """
        self.country = country

        # Position tracking
        self._open_positions: dict[str, list[dict]] = defaultdict(list)
        self._closed_positions: list[dict] = []

        # Day trade tracking
        self._day_trades: list[DayTradeRecord] = []
        self._day_trades_by_date: dict[date, int] = defaultdict(int)

        # Trade history
        self._all_trades: list[dict] = []

        logger.info(f"PDTTracker initialized for {country.value}")

    def check_pdt_limit(
        self,
        account_equity: Decimal,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Check if account would violate PDT rule with a new trade.

        Args:
            account_equity: Current account equity
            symbol: Optional symbol to check
            side: Optional side (BUY/SELL)

        Returns:
            Tuple of (allowed, message)

        Examples:
            >>> tracker = PDTTracker(country=Country.US)
            >>> allowed, msg = tracker.check_pdt_limit(
            ...     account_equity=Decimal("30000"),
            ...     symbol="AAPL",
            ...     side="BUY",
            ... )
            >>> allowed
            True
        """
        # Spain: No PDT rule
        if self.country != Country.US:
            return True, "PDT rule not applicable (Spain/International)"

        # Check equity requirement
        if account_equity < self.PDT_MIN_EQUITY:
            return False, (
                f"PDT restriction: Account equity ${account_equity:,.2f} < "
                f"${self.PDT_MIN_EQUITY:,.2f} minimum. "
                f"Day trading requires $25k equity."
            )

        # Check day trade count
        day_trades_5days = self._get_day_trades_last_5_days()

        # Would this create a day trade?
        would_create_day_trade = False
        if symbol and side == "SELL":
            would_create_day_trade = self._would_create_day_trade(symbol)

        if would_create_day_trade:
            day_trades_5days += 1

        if day_trades_5days >= self.MAX_DAY_TRADES:
            return False, (
                f"PDT limit reached: {day_trades_5days}/{self.MAX_DAY_TRADES} "
                f"day trades in 5-day period. "
                f"Maximum 3 day trades allowed."
            )

        return True, "PDT check passed"

    def record_trade(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        trade_date: date,
    ) -> None:
        """
        Record a trade for PDT tracking.

        Args:
            symbol: Symbol traded
            side: BUY or SELL
            quantity: Quantity traded
            price: Price per share
            trade_date: Date of trade
        """
        trade = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "trade_date": trade_date,
        }

        self._all_trades.append(trade)

        # Track positions for day trade detection
        if side == "BUY":
            self._open_positions[symbol].append(trade)
        elif side == "SELL" and self._open_positions[symbol]:
            # Check if this closes a position opened today (day trade)
            open_trade = self._open_positions[symbol].pop(0)

            # Check if opened today
            if open_trade["trade_date"] == trade_date:
                # This is a day trade!
                self._record_day_trade(
                    symbol=symbol,
                    open_price=open_trade["price"],
                    close_price=price,
                    quantity=quantity,
                    trade_date=trade_date,
                )

        logger.debug(f"Recorded trade: {side} {quantity} {symbol} @ {price}")

    def get_status(self, account_equity: Decimal) -> PDTStatus:
        """
        Get current PDT status.

        Args:
            account_equity: Current account equity

        Returns:
            PDTStatus with current state
        """
        day_trades_count = self._get_day_trades_last_5_days()

        is_restricted = False
        restriction_reason = None

        # Check equity restriction
        if self.country == Country.US and account_equity < self.PDT_MIN_EQUITY:
            is_restricted = True
            restriction_reason = (
                f"Account equity ${account_equity:,.2f} below ${self.PDT_MIN_EQUITY:,.2f} minimum"
            )

        # Check day trade count restriction
        if self.country == Country.US and day_trades_count >= self.MAX_DAY_TRADES:
            is_restricted = True
            restriction_reason = (
                f"Day trade limit reached: {day_trades_count}/{self.MAX_DAY_TRADES}"
            )

        return PDTStatus(
            day_trades_last_5_days=day_trades_count,
            max_day_trades_allowed=self.MAX_DAY_TRADES,
            account_equity=account_equity,
            min_equity_required=self.PDT_MIN_EQUITY,
            is_restricted=is_restricted,
            restriction_reason=restriction_reason,
        )

    def get_day_trades(self, days: int = 5) -> list[DayTradeRecord]:
        """
        Get day trades in last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of day trade records
        """
        cutoff = date.today() - timedelta(days=days)

        return [dt for dt in self._day_trades if dt.open_time.date() >= cutoff]

    def _get_day_trades_last_5_days(self) -> int:
        """Get day trades in last 5 business days."""
        cutoff = date.today() - timedelta(days=self.ROLLING_WINDOW_DAYS)

        return sum(
            count for trade_date, count in self._day_trades_by_date.items() if trade_date >= cutoff
        )

    def _would_create_day_trade(self, symbol: str) -> bool:
        """
        Check if selling this symbol would create a day trade.

        Args:
            symbol: Symbol to check

        Returns:
            True if selling would close a position opened today
        """
        today = date.today()

        # Check if we have open positions in this symbol from today
        return any(trade["trade_date"] == today for trade in self._open_positions.get(symbol, []))

    def _record_day_trade(
        self,
        symbol: str,
        open_price: Decimal,
        close_price: Decimal,
        quantity: Decimal,
        trade_date: date,
    ) -> None:
        """Record a day trade."""
        now = utc_now()

        # Calculate realized PnL
        if symbol.endswith("BUY"):
            pnl = (close_price - open_price) * quantity
        else:
            pnl = (open_price - close_price) * quantity

        day_trade = DayTradeRecord(
            symbol=symbol,
            open_time=now,
            close_time=now,
            open_price=open_price,
            close_price=close_price,
            quantity=quantity,
            realized_pnl=pnl,
        )

        self._day_trades.append(day_trade)
        self._day_trades_by_date[trade_date] += 1

        logger.info(f"Day trade recorded: {symbol} - PnL: ${pnl:.2f}")

    def reset(self) -> None:
        """Reset all tracking (for testing)."""
        self._open_positions.clear()
        self._closed_positions.clear()
        self._day_trades.clear()
        self._day_trades_by_date.clear()
        self._all_trades.clear()

        logger.info("PDTTracker reset")
