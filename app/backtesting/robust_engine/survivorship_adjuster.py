"""
Survivorship Bias Adjuster for Robust Backtesting Engine.

This module implements survivorship bias correction for accurate long-term
backtesting over 25+ year periods.

Survivorship bias occurs when backtesting only includes currently traded stocks,
ignoring those that were delisted, bankrupt, or merged. This significantly
inflates backtest returns.

Features:
- Delisted stock database integration
- Point-in-time universe reconstruction
- Survivorship-free return calculation
- Bankruptcy recovery rate adjustments
- Merger/acquisition handling

Reference:
    - Ernest Chan, "Algorithmic Trading" - Chapter 3
    - "The Long and Short of Survivorship Bias" by Clifford Asness
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .models import DelistedStock, DelistingReason

logger = logging.getLogger(__name__)


@dataclass
class SurvivorshipFreeResult:
    """
    Result of survivorship bias correction.

    Attributes:
        original_returns: Original (biased) returns
        adjusted_returns: Survivorship-adjusted returns
        bias_factor: Adjustment factor applied
        delisted_included: Number of delisted stocks included
        delisted_return contribution: Total return contribution from delisted
        warning: Any warnings about the correction
    """

    original_returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    adjusted_returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    bias_factor: float = field(default=1.0)
    delisted_included: int = field(default=0)
    delisted_return_contribution: float = field(default=0.0)
    warning: Optional[str] = field(default=None)


class SurvivorshipAdjuster:
    """
    Adjusts backtest results for survivorship bias.

    This class:
    1. Maintains a database of delisted stocks
    2. Calculates survivorship bias factors
    3. Adjusts returns to include delisted stock performance
    4. Provides point-in-time universe reconstruction
    5. Warns when survivorship bias is detected

    Example:
        ```python
        adjuster = SurvivorshipAdjuster(
            delisted_db_path="data/delisted_stocks.csv"
        )

        # Get survivorship-free returns
        result = adjuster.calculate_survivorship_free_returns(
            current_universe=["AAPL", "MSFT", "GOOGL"],
            returns_data=returns_df,
            backtest_start=date(1999, 1, 1),
            backtest_end=date(2024, 12, 31)
        )
        ```
    """

    # Historical delisting rates (from CRSP data)
    ANNUAL_DELISTING_RATE = 0.03  # ~3% of stocks delist annually
    BANKRUPTCY_RATE = 0.01  # ~1% go bankrupt
    ACQUISITION_RATE = 0.015  # ~1.5% are acquired
    OTHER_DELISTING_RATE = 0.005  # ~0.5% for other reasons

    # Recovery rates for different delisting scenarios
    BANKRUPTCY_RECOVERY = 0.10  # 10% recovery in bankruptcy
    ACQUISITION_PREMIUM = 0.20  # 20% premium in acquisitions
    OTHER_DELISTING_LOSS = 0.50  # 50% loss in other delistings

    def __init__(
        self,
        delisted_db_path: Optional[Path] = None,
        auto_load: bool = True,
    ):
        """
        Initialize the survivorship adjuster.

        Args:
            delisted_db_path: Path to delisted stocks database CSV
            auto_load: Whether to automatically load the database
        """
        self.delisted_db_path = delisted_db_path
        self._delisted_stocks: Dict[str, DelistedStock] = {}
        self._delisting_by_date: Dict[date, List[str]] = defaultdict(list)

        if delisted_db_path and auto_load:
            self.load_delisted_database(delisted_db_path)

    def load_delisted_database(
        self,
        filepath: Path,
    ) -> int:
        """
        Load delisted stocks from a CSV database.

        Expected CSV format:
        symbol,delisting_date,reason,last_price,recovery_rate,returns_csv

        Args:
            filepath: Path to CSV file

        Returns:
            Number of delisted stocks loaded
        """
        try:
            df = pd.read_csv(filepath)
            df["delisting_date"] = pd.to_datetime(df["delisting_date"]).dt.date

            count = 0
            # Use itertuples instead of iterrows for better performance
            for row in df.itertuples():
                stock = DelistedStock(
                    symbol=row.symbol,
                    delisting_date=row.delisting_date,
                    reason=DelistingReason(getattr(row, "reason", "delisting")),
                    last_price=Decimal(str(row.last_price)),
                    recovery_rate=Decimal(str(getattr(row, "recovery_rate", 0.1))),
                )

                # Parse returns if provided
                if hasattr(row, "returns_csv") and pd.notna(row.returns_csv):
                    returns_list = [
                        (date.fromisoformat(d.split(":")[0]), Decimal(d.split(":")[1]))
                        for d in str(row.returns_csv).split(";")
                    ]
                    stock.returns_daily = returns_list

                self._delisted_stocks[stock.symbol] = stock
                self._delisting_by_date[stock.delisting_date].append(stock.symbol)
                count += 1

            logger.info(f"Loaded {count} delisted stocks from {filepath}")
            return count

        except Exception as e:
            logger.error(f"Error loading delisted database from {filepath}: {e}")
            return 0

    def add_delisted_stock(
        self,
        stock: DelistedStock,
    ) -> None:
        """
        Add a delisted stock to the database.

        Args:
            stock: DelistedStock object
        """
        self._delisted_stocks[stock.symbol] = stock
        self._delisting_by_date[stock.delisting_date].append(stock.symbol)

    def get_adjusted_universe(
        self,
        current_universe: List[str],
        as_of_date: date,
    ) -> List[str]:
        """
        Get the point-in-time universe as of a specific date.

        This returns the universe that would have been available at
        the specified date, including stocks that were later delisted.

        Args:
            current_universe: List of currently traded symbols
            as_of_date: Date to get universe as of

        Returns:
            List of symbols available as of the date
        """
        universe = set(current_universe)

        # Add delisted stocks that were active as of this date
        for symbol, stock in self._delisted_stocks.items():
            # Estimate listing date from delisting date
            # In production, this would come from actual data
            estimated_listing_date = stock.delisting_date.replace(
                year=stock.delisting_date.year - 10
            )

            if estimated_listing_date <= as_of_date <= stock.delisting_date:
                universe.add(symbol)

        return sorted(universe)

    def calculate_survivorship_free_returns(
        self,
        current_universe: List[str],
        returns_data: pd.DataFrame,
        backtest_start: date,
        backtest_end: date,
        method: str = "multiplicative",
    ) -> SurvivorshipFreeResult:
        """
        Calculate survivorship-free returns.

        This adjusts returns to include the negative performance from
        stocks that were delisted during the backtest period.

        Args:
            current_universe: Currently traded symbols
            returns_data: DataFrame of returns (indexed by date, columns = symbols)
            backtest_start: Backtest start date
            backtest_end: Backtest end date
            method: Adjustment method ('multiplicative' or 'additive')

        Returns:
            SurvivorshipFreeResult with adjusted returns
        """
        try:
            # Calculate bias adjustment
            adjustment = self._calculate_survivorship_adjustment(
                current_universe=current_universe,
                backtest_start=backtest_start,
                backtest_end=backtest_end,
            )

            # Get delisted returns for the period
            delisted_returns = self._get_delisted_returns(
                backtest_start=backtest_start,
                backtest_end=backtest_end,
            )

            # Calculate portfolio returns (equal-weighted)
            if not returns_data.empty:
                original_returns = returns_data.mean(axis=1)
            else:
                original_returns = pd.Series(dtype=float)

            # Apply adjustment
            if method == "multiplicative":
                # Divide returns by bias factor
                adjusted_returns = original_returns / adjustment["bias_factor"]
            elif method == "additive":
                # Subtract bias drag
                annual_drag = (adjustment["bias_factor"] - 1.0) * 0.05
                daily_drag = annual_drag / 252
                adjusted_returns = original_returns - daily_drag
            else:
                raise ValueError(f"Unknown adjustment method: {method}")

            # Add delisted return contribution
            if delisted_returns:
                delisted_contribution = np.mean(list(delisted_returns.values()))
            else:
                delisted_contribution = 0.0

            # Warning if bias is significant
            warning = None
            if adjustment["bias_factor"] > 1.05:
                warning = (
                    f"Significant survivorship bias detected: "
                    f"bias factor = {adjustment['bias_factor']:.4f}. "
                    f"Returns may be inflated by "
                    f"{(adjustment['bias_factor'] - 1.0) * 100:.2f}%"
                )
                logger.warning(warning)

            result = SurvivorshipFreeResult(
                original_returns=original_returns,
                adjusted_returns=adjusted_returns,
                bias_factor=adjustment["bias_factor"],
                delisted_included=adjustment["delisted_count"],
                delisted_return_contribution=delisted_contribution,
                warning=warning,
            )

            logger.info(
                f"Survivorship adjustment: "
                f"bias_factor={adjustment['bias_factor']:.4f}, "
                f"delisted_included={adjustment['delisted_count']}, "
                f"mean_return_before={original_returns.mean():.6f}, "
                f"mean_return_after={adjusted_returns.mean():.6f}"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating survivorship-free returns: {e}")
            # Return unadjusted on error
            return SurvivorshipFreeResult(
                original_returns=(
                    returns_data.mean(axis=1) if not returns_data.empty else pd.Series(dtype=float)
                ),
                adjusted_returns=(
                    returns_data.mean(axis=1) if not returns_data.empty else pd.Series(dtype=float)
                ),
                bias_factor=1.0,
                delisted_included=0,
                delisted_return_contribution=0.0,
                warning=f"Error in survivorship adjustment: {e}",
            )

    def _calculate_survivorship_adjustment(
        self,
        current_universe: List[str],
        backtest_start: date,
        backtest_end: date,
    ) -> Dict[str, Any]:
        """Calculate the survivorship bias adjustment factor."""
        period_years = (backtest_end - backtest_start).days / 365.25

        # Working backwards from survivors to original universe
        current_size = len(current_universe)
        annual_survival_rate = 1.0 - self.ANNUAL_DELISTING_RATE
        survival_rate_over_period = annual_survival_rate**period_years

        original_universe_size = int(current_size / survival_rate_over_period)
        estimated_delisted = original_universe_size - current_size

        # Calculate bias factor
        bias_factor = self._calculate_bias_factor(
            survivor_count=current_size,
            delisted_count=estimated_delisted,
            period_years=period_years,
        )

        return {
            "original_universe_size": original_universe_size,
            "survivor_count": current_size,
            "delisted_count": estimated_delisted,
            "bias_factor": bias_factor,
            "period_years": period_years,
        }

    def _calculate_bias_factor(
        self,
        survivor_count: int,
        delisted_count: int,
        period_years: float,
    ) -> float:
        """
        Calculate the survivorship bias factor.

        Delisted stocks typically underperform by ~20% annually.
        """
        if delisted_count == 0:
            return 1.0

        total_original = survivor_count + delisted_count
        survivor_ratio = survivor_count / total_original

        # Delisted performance drag
        delisted_performance_drag = 0.20  # 20% annual underperformance
        weighted_drag = (1 - survivor_ratio) * delisted_performance_drag * period_years

        # Bias factor
        bias_factor = 1.0 / (1.0 - weighted_drag) if weighted_drag < 1.0 else 1.0

        # Cap at reasonable maximum
        max_bias = 1.0 + (0.03 * period_years)
        return min(bias_factor, max_bias)

    def _get_delisted_returns(
        self,
        backtest_start: date,
        backtest_end: date,
    ) -> Dict[str, float]:
        """Get returns for delisted stocks during the period."""
        # Use generator to process delisted stocks efficiently
        delisted_returns = {}
        for symbol, total_return in self._generate_delisted_returns(backtest_start, backtest_end):
            delisted_returns[symbol] = total_return
        return delisted_returns

    def _generate_delisted_returns(
        self,
        backtest_start: date,
        backtest_end: date,
    ) -> Tuple[str, float]:
        """
        Generate returns for delisted stocks during the period.

        This is a generator that yields (symbol, total_return) tuples
        for memory-efficient processing of large delisted stock datasets.

        Args:
            backtest_start: Start date of backtest period
            backtest_end: End date of backtest period

        Yields:
            Tuple of (symbol, total_return) for each delisted stock
        """
        for symbol, stock in self._delisted_stocks.items():
            if backtest_start <= stock.delisting_date <= backtest_end:
                # Calculate return from listing to delisting
                if stock.returns_daily:
                    daily_returns = [float(r) for _, r in stock.returns_daily]
                    total_return = np.prod([1 + r for r in daily_returns]) - 1
                else:
                    # Use estimated return based on recovery rate
                    total_return = float(stock.recovery_rate) - 1.0

                yield symbol, total_return

    def create_point_in_time_universe(
        self,
        current_universe: List[str],
        backtest_start: date,
        backtest_end: date,
        frequency: str = "M",
    ) -> Dict[date, List[str]]:
        """
        Create a point-in-time universe for backtesting.

        This implements Ernest Chan's recommendation to use only
        stocks that would have been available at each point in time.

        Args:
            current_universe: Currently traded symbols
            backtest_start: Backtest start date
            backtest_end: Backtest end date
            frequency: Rebalancing frequency ('D', 'W', 'ME', 'QE')

        Returns:
            Dictionary mapping dates to available universe
        """
        # Map old frequency codes to new pandas format
        freq_map = {'M': 'ME', 'Q': 'QE'}
        freq = freq_map.get(frequency, frequency)

        dates = pd.date_range(start=backtest_start, end=backtest_end, freq=freq)
        pit_universe = {}

        for date in dates:
            date_obj = date.date()
            pit_universe[date_obj] = self.get_adjusted_universe(
                current_universe=current_universe,
                as_of_date=date_obj,
            )

        logger.info(
            f"Created point-in-time universe for {len(pit_universe)} dates "
            f"from {backtest_start} to {backtest_end}"
        )

        return pit_universe

    def get_delisting_events(
        self,
        start_date: date,
        end_date: date,
        reason: Optional[DelistingReason] = None,
    ) -> List[DelistedStock]:
        """
        Get delisting events within a date range.

        Args:
            start_date: Start date
            end_date: End date
            reason: Optional filter by delisting reason

        Returns:
            List of delisted stocks
        """
        events = []

        for date in pd.date_range(start=start_date, end=end_date):
            date_obj = date.date()
            if date_obj in self._delisting_by_date:
                for symbol in self._delisting_by_date[date_obj]:
                    stock = self._delisted_stocks[symbol]
                    if reason is None or stock.reason == reason:
                        events.append(stock)

        return sorted(events, key=lambda s: s.delisting_date)

    def calculate_universe_statistics(
        self,
        current_universe: List[str],
        backtest_start: date,
        backtest_end: date,
    ) -> Dict[str, Any]:
        """
        Calculate statistics about the survivorship bias.

        Args:
            current_universe: Currently traded symbols
            backtest_start: Backtest start date
            backtest_end: Backtest end date

        Returns:
            Dictionary with bias statistics
        """
        adjustment = self._calculate_survivorship_adjustment(
            current_universe=current_universe,
            backtest_start=backtest_start,
            backtest_end=backtest_end,
        )

        # Get delisting events
        delistings = self.get_delisting_events(backtest_start, backtest_end)

        # Count by reason
        by_reason = defaultdict(int)
        for stock in delistings:
            by_reason[stock.reason.value] += 1

        return {
            "original_universe_size": adjustment["original_universe_size"],
            "current_universe_size": len(current_universe),
            "estimated_delisted": adjustment["delisted_count"],
            "bias_factor": adjustment["bias_factor"],
            "period_years": adjustment["period_years"],
            "actual_delistings": len(delistings),
            "delistings_by_reason": dict(by_reason),
            "estimated_return_inflation": ((adjustment["bias_factor"] - 1.0) * 100),
        }
