"""
Survivorship Bias Correction

Handles survivorship bias in backtesting by:
- Tracking delisted stocks
- Adjusting returns for delisting events
- Including failed companies in historical data
- Properly handling corporate actions

Reference: Rule 11-lopez-de-prado-advances-in-financial-machine-learning.md
- Survivorship bias leads to overestimation of returns
- Must include delisted securities in backtesting
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


class DelistingReason(str, Enum):
    """Reason for delisting."""

    BANKRUPTCY = "bankruptcy"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    DELISTING = "delisting"  # Forced delisting by exchange
    PRIVATE = "went_private"
    LIQUIDATION = "liquidation"
    OTHER = "other"


class CorporateActionType(str, Enum):
    """Type of corporate action."""

    STOCK_SPLIT = "stock_split"
    REVERSE_SPLIT = "reverse_split"
    SPINOFF = "spinoff"
    DIVIDEND = "dividend"
    RIGHTS_OFFERING = "rights_offering"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    TENDER_OFFER = "tender_offer"
    NAME_CHANGE = "name_change"
    SYMBOL_CHANGE = "symbol_change"


@dataclass
class DelistingEvent:
    """Record of a delisting event."""

    symbol: str
    delisting_date: date
    reason: DelistingReason
    last_price: Decimal
    last_volume: Optional[int] = None
    recovery_rate: Optional[float] = None  # Recovery rate for bankruptcy
    acquired_by: Optional[str] = None  # For mergers/acquisitions
    acquisition_terms: Optional[str] = None  # Terms of acquisition

    @property
    def is_bailout(self) -> bool:
        """Check if delisting resulted in shareholder recovery."""
        return self.recovery_rate is not None and self.recovery_rate > 0

    @property
    def total_loss(self) -> float:
        """Calculate total loss percentage."""
        if self.recovery_rate is not None:
            return 1.0 - self.recovery_rate
        return 1.0  # 100% loss by default


@dataclass
class CorporateAction:
    """Record of a corporate action."""

    symbol: str
    action_date: date
    action_type: CorporateActionType
    ratio: Optional[float] = None  # For splits, spinoffs, etc.
    cash_amount: Optional[Decimal] = None  # For dividends, tender offers
    new_symbol: Optional[str] = None  # For symbol changes, spinoffs
    description: Optional[str] = None

    def adjust_price(self, price: Decimal) -> Decimal:
        """Adjust historical price for corporate action."""
        if self.action_type == CorporateActionType.STOCK_SPLIT and self.ratio:
            # Split: new shares = old shares * ratio
            # Price adjusts by 1/ratio
            return price / Decimal(str(self.ratio))
        elif self.action_type == CorporateActionType.REVERSE_SPLIT and self.ratio:
            # Reverse split: new shares = old shares / ratio
            # Price adjusts by ratio
            return price * Decimal(str(self.ratio))
        else:
            return price

    def adjust_quantity(self, quantity: Decimal) -> Decimal:
        """Adjust position quantity for corporate action."""
        if self.action_type == CorporateActionType.STOCK_SPLIT and self.ratio:
            return quantity * Decimal(str(self.ratio))
        elif self.action_type == CorporateActionType.REVERSE_SPLIT and self.ratio:
            return quantity / Decimal(str(self.ratio))
        else:
            return quantity


@dataclass
class DelistingAdjustment:
    """Adjustment for delisting in returns."""

    symbol: str
    delisting_date: date
    adjustment_factor: float  # Multiplier for returns
    recovery_return: float  # Return on delisting day


class SurvivorshipBiasCorrector:
    """
    Corrects survivorship bias in backtesting.

    Survivorship bias occurs when only currently listed companies
    are included in historical data. This leads to overestimation
    of returns because failed companies are excluded.

    Methods:
    1. Include delisted stocks in universe
    2. Adjust for delisting events
    3. Handle corporate actions properly
    4. Track name/symbol changes
    """

    def __init__(self):
        """Initialize survivorship bias corrector."""
        self._delistings: Dict[str, DelistingEvent] = {}
        self._corporate_actions: Dict[str, List[CorporateAction]] = {}
        self._symbol_changes: Dict[str, str] = {}  # old -> new

    def add_delisting(self, delisting: DelistingEvent) -> None:
        """
        Add a delisting event.

        Args:
            delisting: Delisting event to record
        """
        self._delistings[delisting.symbol] = delisting

    def add_corporate_action(self, action: CorporateAction) -> None:
        """
        Add a corporate action.

        Args:
            action: Corporate action to record
        """
        if action.symbol not in self._corporate_actions:
            self._corporate_actions[action.symbol] = []
        self._corporate_actions[action.symbol].append(action)

        # Track symbol changes
        if action.action_type == CorporateActionType.SYMBOL_CHANGE and action.new_symbol:
            self._symbol_changes[action.symbol] = action.new_symbol

    def get_delisting(self, symbol: str) -> Optional[DelistingEvent]:
        """Get delisting event for symbol."""
        return self._delistings.get(symbol)

    def get_corporate_actions(self, symbol: str) -> List[CorporateAction]:
        """Get all corporate actions for symbol."""
        return self._corporate_actions.get(symbol, [])

    def check_delisting_date(
        self,
        symbol: str,
        current_date: date,
    ) -> Optional[DelistingEvent]:
        """
        Check if symbol was delisted on or before current date.

        Args:
            symbol: Symbol to check
            current_date: Current simulation date

        Returns:
            DelistingEvent if delisted, None otherwise
        """
        delisting = self._delistings.get(symbol)
        if delisting and delisting.delisting_date <= current_date:
            return delisting
        return None

    def adjust_returns_for_delisting(
        self,
        returns: pd.Series,
        symbol: str,
    ) -> pd.Series:
        """
        Adjust returns for delisting.

        Args:
            returns: Series of returns
            symbol: Symbol that was delisted

        Returns:
            Adjusted returns series
        """
        delisting = self._delistings.get(symbol)
        if not delisting:
            return returns

        # Calculate adjustment factor based on delisting reason
        if delisting.reason == DelistingReason.BANKRUPTCY:
            # Assume -50% to -100% return on delisting day
            recovery_rate = delisting.recovery_rate or 0.0
            adjustment_factor = -(1 - recovery_rate)
        elif delisting.reason in (DelistingReason.MERGER, DelistingReason.ACQUISITION):
            # Assume 0-30% premium acquisition
            premium = delisting.recovery_rate or 1.2
            adjustment_factor = premium - 1
        else:
            # Default to -50% for unknown delisting
            adjustment_factor = -0.5

        # Adjust returns from delisting date onwards
        adjusted_returns = returns.copy()
        delisting_idx = (
            adjusted_returns.index.get_loc(pd.Timestamp(delisting.delisting_date))
            if pd.Timestamp(delisting.delisting_date) in adjusted_returns.index
            else None
        )

        if delisting_idx is not None:
            # Apply delisting return
            adjusted_returns.iloc[delisting_idx] = adjustment_factor
            # Set future returns to NaN (stock no longer trades)
            if delisting_idx + 1 < len(adjusted_returns):
                adjusted_returns.iloc[delisting_idx + 1 :] = np.nan

        return adjusted_returns

    def adjust_price_series(
        self,
        prices: pd.Series,
        symbol: str,
    ) -> pd.Series:
        """
        Adjust price series for corporate actions.

        Args:
            prices: Series of prices
            symbol: Symbol to adjust

        Returns:
            Adjusted price series
        """
        adjusted_prices = prices.copy()
        actions = self._corporate_actions.get(symbol, [])

        for action in sorted(actions, key=lambda a: a.action_date, reverse=True):
            action_date = pd.Timestamp(action.action_date)

            # Apply adjustment to prices before action date
            mask = adjusted_prices.index < action_date

            if action.action_type in (
                CorporateActionType.STOCK_SPLIT,
                CorporateActionType.REVERSE_SPLIT,
            ):
                # Adjust prices for split
                for i in mask[mask].index:
                    adjusted_prices.loc[i] = action.adjust_price(adjusted_prices.loc[i])

        return adjusted_prices

    def get_current_symbol(
        self,
        historical_symbol: str,
        as_of_date: date,
    ) -> str:
        """
        Get current symbol for a historical symbol.

        Handles name changes and symbol changes.

        Args:
            historical_symbol: Historical symbol
            as_of_date: Date to check

        Returns:
            Current symbol as of the date
        """
        # Check for corporate actions
        actions = self._corporate_actions.get(historical_symbol, [])

        for action in sorted(actions, key=lambda a: a.action_date):
            if action.action_date <= as_of_date and action.action_type == CorporateActionType.SYMBOL_CHANGE and action.new_symbol:
                # Recursively check new symbol
                return self.get_current_symbol(action.new_symbol, as_of_date)

        return historical_symbol

    def calculate_universe_including_delisted(
        self,
        current_date: date,
        all_symbols: List[str],
        lookback_days: int = 252,
    ) -> List[str]:
        """
        Calculate tradable universe including delisted stocks.

        Args:
            current_date: Current simulation date
            all_symbols: All possible symbols
            lookback_days: Lookback period for filtering

        Returns:
            List of symbols that were tradable at current_date
        """
        tradable = []

        for symbol in all_symbols:
            # Check if symbol exists (not yet delisted or delisted after lookback)
            delisting = self._delistings.get(symbol)

            if delisting is None or delisting.delisting_date > date(
                current_date.year - lookback_days // 365,
                current_date.month,
                current_date.day,
            ):
                # Never delisted (or still trading) or delisted but within lookback period
                tradable.append(symbol)

        return tradable

    def handle_spinoff(
        self,
        parent_symbol: str,
        spinoff_symbol: str,
        spinoff_date: date,
        spinoff_ratio: float,
    ) -> None:
        """
        Handle a spinoff corporate action.

        Args:
            parent_symbol: Parent company symbol
            spinoff_symbol: New spinoff symbol
            spinoff_date: Date of spinoff
            spinoff_ratio: Ratio of new shares per old share
        """
        # Add spinoff action for parent
        self.add_corporate_action(
            CorporateAction(
                symbol=parent_symbol,
                action_date=spinoff_date,
                action_type=CorporateActionType.SPINOFF,
                ratio=spinoff_ratio,
                new_symbol=spinoff_symbol,
                description=f"Spinoff of {spinoff_symbol}",
            )
        )

        # Note: In a full implementation, we would also add
        # the spinoff company as a new tradable security

    def get_adjusted_close(
        self,
        raw_close: Decimal,
        symbol: str,
        as_of_date: date,
    ) -> Decimal:
        """
        Get adjusted close price accounting for corporate actions.

        Args:
            raw_close: Raw closing price
            symbol: Symbol
            as_of_date: Date of price

        Returns:
            Adjusted close price
        """
        adjusted = raw_close
        actions = self._corporate_actions.get(symbol, [])

        # Apply all relevant corporate actions
        for action in actions:
            if action.action_date > as_of_date:
                # Future action - adjust historical price
                adjusted = action.adjust_price(adjusted)

        return adjusted

    def calculate_survivorship_bias(
        self,
        survivor_returns: pd.Series,
        full_universe_returns: pd.DataFrame,
    ) -> float:
        """
        Calculate survivorship bias in returns.

        Args:
            survivor_returns: Returns of surviving companies only
            full_universe_returns: Returns of full universe (including delisted)

        Returns:
            Bias amount (positive = survivor returns are overstated)
        """
        survivor_mean = survivor_returns.mean()
        full_mean = full_universe_returns.mean().mean()

        return float(survivor_mean - full_mean)
