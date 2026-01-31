"""
Survivorship Bias Correction for Backtesting

This module implements survivorship bias correction as described in
Ernest Chan's "Algorithmic Trading" (Chapter 3).

Survivorship bias occurs when backtesting only includes currently
traded stocks, ignoring those that were delisted, bankrupt, or merged.
This leads to inflated performance estimates.

Key Features:
- Delisted stock simulation
- Point-in-time universe reconstruction
- Bankruptcy adjustment factors
- Merger/acquisition handling

Reference:
    "Algorithmic Trading" by Ernest P. Chan
    Chapter 3: Backtesting
    Section: Survivorship Bias
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DelistedStockInfo:
    """Information about a delisted stock for bias correction."""

    symbol: str
    delisting_date: datetime
    delisting_reason: str  # 'bankruptcy', 'acquisition', 'delisting'
    last_price: Decimal
    recovery_rate: Decimal  # Typical recovery after delisting
    volatility_before_delisting: float


@dataclass
class SurvivorshipAdjustment:
    """Adjustment factors for survivorship bias."""

    total_universe_size: int
    surviving_count: int
    delisted_count: int
    survivorship_bias_factor: float  # Multiplier to adjust returns
    bankruptcy_adjustment: float
    acquisition_adjustment: float
    average_delisting_date: Optional[datetime]


class SurvivorshipBiasCorrector:
    """
    Corrects survivorship bias in backtesting using Ernest Chan's methodology.

    The correction works by:
    1. Identifying delisted stocks in the historical period
    2. Simulating their inclusion in the universe
    3. Adjusting returns based on delisting outcomes
    4. Applying bankruptcy recovery rates
    """

    # Typical delisting rates (from historical studies)
    ANNUAL_DELISTING_RATE = 0.03  # ~3% of stocks delist annually
    BANKRUPTCY_RATE = 0.01  # ~1% go bankrupt
    ACQUISITION_RATE = 0.015  # ~1.5% are acquired
    OTHER_DELISTING_RATE = 0.005  # ~0.5% for other reasons

    # Recovery rates for different delisting scenarios
    BANKRUPTCY_RECOVERY_RATE = 0.10  # 10% recovery in bankruptcy
    ACQUISITION_PREMIUM = 0.20  # 20% premium in acquisitions
    DELISTING_LOSS = 0.50  # 50% loss in other delistings

    def __init__(
        self,
        delisting_data_path: Optional[Path] = None,
        custom_delisting_rates: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize the survivorship bias corrector.

        Args:
            delisting_data_path: Path to delisting data CSV (optional)
            custom_delisting_rates: Custom delisting rates (optional)
        """
        self.delisting_data_path = delisting_data_path
        self.delisting_rates = custom_delisting_rates or {
            "bankruptcy": self.BANKRUPTCY_RATE,
            "acquisition": self.ACQUISITION_RATE,
            "other": self.OTHER_DELISTING_RATE,
        }

        # Cache for delisting data
        self._delisting_cache: Optional[pd.DataFrame] = None

    def calculate_survivorship_bias(
        self,
        current_universe: List[str],
        backtest_start: datetime,
        backtest_end: datetime,
    ) -> SurvivorshipAdjustment:
        """
        Calculate survivorship bias adjustment for a backtest period.

        Args:
            current_universe: List of currently traded symbols
            backtest_start: Start date of backtest
            backtest_end: End date of backtest

        Returns:
            SurvivorshipAdjustment with bias correction factors
        """
        try:
            # Calculate period length in years
            period_years = (backtest_end - backtest_start).days / 365.25

            # Estimate number of stocks that would have delisted
            current_size = len(current_universe)

            # Working backwards: current survivors + delisted = original universe
            # If we have N survivors now, we started with N / (survival_rate)^t
            annual_survival_rate = 1.0 - self.ANNUAL_DELISTING_RATE
            survival_rate_over_period = annual_survival_rate**period_years

            original_universe_size = int(current_size / survival_rate_over_period)
            estimated_delisted = original_universe_size - current_size

            # Calculate bias factor (returns are inflated by this factor)
            # Bias factor = (original_universe_value) / (survivor_universe_value)
            # Since delisted stocks typically underperform, this is > 1
            bias_factor = self._calculate_bias_factor(
                current_size, estimated_delisted, period_years
            )

            # Calculate specific adjustments
            bankruptcy_adjustment = self._calculate_bankruptcy_adjustment(
                estimated_delisted, period_years
            )
            acquisition_adjustment = self._calculate_acquisition_adjustment(
                estimated_delisted, period_years
            )

            adjustment = SurvivorshipAdjustment(
                total_universe_size=original_universe_size,
                surviving_count=current_size,
                delisted_count=estimated_delisted,
                survivorship_bias_factor=bias_factor,
                bankruptcy_adjustment=bankruptcy_adjustment,
                acquisition_adjustment=acquisition_adjustment,
                average_delisting_date=None,
            )

            logger.info(
                f"SurvivorshipBiasCorrector: Period {backtest_start.date()} to {backtest_end.date()} "
                f"({period_years:.2f} years): "
                f"Original universe: {original_universe_size}, "
                f"Survivors: {current_size}, "
                f"Estimated delisted: {estimated_delisted}, "
                f"Bias factor: {bias_factor:.4f}"
            )

            return adjustment

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating survivorship bias: {e}")
            # Return neutral adjustment (no correction)
            return SurvivorshipAdjustment(
                total_universe_size=len(current_universe),
                surviving_count=len(current_universe),
                delisted_count=0,
                survivorship_bias_factor=1.0,
                bankruptcy_adjustment=1.0,
                acquisition_adjustment=1.0,
                average_delisting_date=None,
            )

    def adjust_returns_for_survivorship(
        self,
        returns: pd.Series,
        adjustment: SurvivorshipAdjustment,
        method: str = "multiplicative",
    ) -> pd.Series:
        """
        Adjust backtest returns for survivorship bias.

        Args:
            returns: Series of returns to adjust
            adjustment: Survivorship adjustment from calculate_survivorship_bias()
            method: Adjustment method ('multiplicative' or 'additive')

        Returns:
            Adjusted returns series
        """
        try:
            if method == "multiplicative":
                # Multiply returns by bias factor (Ernest Chan's preferred method)
                # Adjusted return = Raw return / (1 + bias_adjustment)
                adjusted_returns = returns / adjustment.survivorship_bias_factor

            elif method == "additive":
                # Subtract bias adjustment from returns
                # More conservative approach
                annual_bias_drag = (adjustment.survivorship_bias_factor - 1.0) * 0.05
                daily_bias_drag = annual_bias_drag / 252
                adjusted_returns = returns - daily_bias_drag

            else:
                raise ValueError(f"Unknown adjustment method: {method}")

            logger.info(
                f"SurvivorshipBiasCorrector: Adjusted returns using {method} method. "
                f"Bias factor: {adjustment.survivorship_bias_factor:.4f}, "
                f"Mean return before: {returns.mean():.6f}, "
                f"Mean return after: {adjusted_returns.mean():.6f}"
            )

            return adjusted_returns

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error adjusting returns: {e}")
            return returns

    def simulate_delisted_stocks(
        self,
        current_symbols: List[str],
        backtest_dates: pd.DatetimeIndex,
        delisted_data: Optional[List[DelistedStockInfo]] = None,
    ) -> Dict[datetime, List[str]]:
        """
        Simulate the inclusion of delisted stocks in historical universe.

        This creates a point-in-time universe that includes stocks that
        would have been delisted during the backtest period.

        Args:
            current_symbols: Currently traded symbols
            backtest_dates: Dates for backtest
            delisted_data: Optional actual delisting data

        Returns:
            Dictionary mapping dates to full universe (including delisted)
        """
        try:
            universe_over_time = {}

            for date in backtest_dates:
                # Start with current universe
                universe = set(current_symbols)

                # Simulate adding delisted stocks
                if delisted_data:
                    # Use actual delisting data if available
                    delisted_at_date = [
                        d.symbol
                        for d in delisted_data
                        if d.delisting_date > date and d.delisting_date < date + timedelta(days=365)
                    ]
                    universe.update(delisted_at_date)
                else:
                    # Simulate delisted stocks based on historical rates
                    estimated_delisted_count = int(
                        len(current_symbols) * self.ANNUAL_DELISTING_RATE
                    )
                    # Add placeholder symbols for delisted stocks
                    for i in range(estimated_delisted_count):
                        simulated_symbol = f"DELISTED_{date.year}_{i}"
                        universe.add(simulated_symbol)

                universe_over_time[date] = list(universe)

            return universe_over_time

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error simulating delisted stocks: {e}")
            return {date: current_symbols for date in backtest_dates}

    def _calculate_bias_factor(
        self, survivor_count: int, delisted_count: int, period_years: float
    ) -> float:
        """
        Calculate the survivorship bias factor.

        Based on Ernest Chan's observation that survivorship bias
        typically inflates returns by 1-3% annually.
        """
        if delisted_count == 0:
            return 1.0

        total_original = survivor_count + delisted_count
        survivor_ratio = survivor_count / total_original

        # Delisted stocks typically underperform by ~20% annually
        # Weighted average adjustment
        delisted_performance_drag = 0.20  # 20% annual underperformance
        weighted_drag = (1 - survivor_ratio) * delisted_performance_drag * period_years

        # Bias factor = 1 / (1 - weighted_drag)
        # This inflates the denominator, reducing the adjusted returns
        bias_factor = 1.0 / (1.0 - weighted_drag) if weighted_drag < 1.0 else 1.0

        # Cap at reasonable maximum (3% annual inflation over 10 years = 1.3x)
        max_bias = 1.0 + (0.03 * period_years)
        return min(bias_factor, max_bias)

    def _calculate_bankruptcy_adjustment(self, delisted_count: int, period_years: float) -> float:
        """Calculate adjustment for bankruptcies."""
        bankruptcies = int(delisted_count * (self.BANKRUPTCY_RATE / self.ANNUAL_DELISTING_RATE))
        if bankruptcies == 0:
            return 1.0

        # Bankruptcy recovery rate reduces losses
        recovery_impact = (self.BANKRUPTCY_RECOVERY_RATE - 1.0) * bankruptcies / delisted_count
        return 1.0 + recovery_impact

    def _calculate_acquisition_adjustment(self, delisted_count: int, period_years: float) -> float:
        """Calculate adjustment for acquisitions (typically positive)."""
        acquisitions = int(delisted_count * (self.ACQUISITION_RATE / self.ANNUAL_DELISTING_RATE))
        if acquisitions == 0:
            return 1.0

        # Acquisitions typically provide premium
        premium_impact = self.ACQUISITION_PREMIUM * acquisitions / delisted_count
        return 1.0 + premium_impact

    def load_delisting_data(self, filepath: Path) -> List[DelistedStockInfo]:
        """
        Load actual delisting data from CSV file.

        Expected CSV format:
        symbol,delisting_date,delisting_reason,last_price,recovery_rate

        Args:
            filepath: Path to delisting data CSV

        Returns:
            List of DelistedStockInfo objects
        """
        try:
            if self._delisting_cache is not None:
                return self._delisting_cache.to_dict("records")

            df = pd.read_csv(filepath)
            df["delisting_date"] = pd.to_datetime(df["delisting_date"])

            delisting_list = []
            # Use itertuples instead of iterrows for better performance
            for row in df.itertuples():
                delisting_list.append(
                    DelistedStockInfo(
                        symbol=row.symbol,
                        delisting_date=row.delisting_date,
                        delisting_reason=row.delisting_reason,
                        last_price=Decimal(str(row.last_price)),
                        recovery_rate=Decimal(str(getattr(row, "recovery_rate", 0.1))),
                        volatility_before_delisting=getattr(row, "volatility", 0.5),
                    )
                )

            self._delisting_cache = df
            logger.info(f"Loaded {len(delisting_list)} delisted stocks from {filepath}")
            return delisting_list

        except (FileNotFoundError, ValueError, KeyError) as e:
            logger.warning(f"Could not load delisting data from {filepath}: {e}")
            return []

    def create_point_in_time_universe(
        self,
        current_symbols: List[str],
        backtest_start: datetime,
        backtest_end: datetime,
        frequency: str = "M",
    ) -> Dict[datetime, List[str]]:
        """
        Create a point-in-time universe for backtesting.

        This implements Ernest Chan's recommendation to use only
        stocks that would have been available at each point in time.

        Args:
            current_symbols: Currently traded symbols
            backtest_start: Start date of backtest
            backtest_end: End date of backtest
            frequency: Rebalancing frequency ('D', 'W', 'M', 'Q')

        Returns:
            Dictionary mapping dates to available universe at that time
        """
        try:
            dates = pd.date_range(start=backtest_start, end=backtest_end, freq=frequency)
            pit_universe = {}

            for date in dates:
                # Simulate historical universe at this point in time
                # In production, this would query actual historical data
                universe_size = self._estimate_historical_universe_size(date)
                pit_universe[date] = current_symbols[:universe_size]

            logger.info(
                f"Created point-in-time universe for {len(pit_universe)} dates "
                f"from {backtest_start.date()} to {backtest_end.date()}"
            )
            return pit_universe

        except (ValueError, TypeError) as e:
            logger.error(f"Error creating point-in-time universe: {e}")
            return {backtest_start: current_symbols}

    def _estimate_historical_universe_size(self, date: datetime) -> int:
        """
        Estimate the size of the trading universe at a historical date.

        This is a simplified estimation. In production, use actual data from
        CRSP, Compustat, or other historical databases.
        """
        # Simplified: assume universe grows ~5% annually
        base_universe_size = 3000  # Current approximate size
        years_ago = (datetime.now() - date).days / 365.25
        growth_rate = 1.05
        historical_size = int(base_universe_size / (growth_rate**years_ago))
        return max(1000, historical_size)  # Minimum 1000 stocks


def adjust_backtest_for_survivorship(
    returns: pd.Series,
    current_universe: List[str],
    backtest_start: datetime,
    backtest_end: datetime,
    corrector: Optional[SurvivorshipBiasCorrector] = None,
) -> Tuple[pd.Series, SurvivorshipAdjustment]:
    """
    Convenience function to adjust backtest returns for survivorship bias.

    Args:
        returns: Backtest returns to adjust
        current_universe: List of currently traded symbols
        backtest_start: Backtest start date
        backtest_end: Backtest end date
        corrector: Optional SurvivorshipBiasCorrector instance

    Returns:
        Tuple of (adjusted_returns, adjustment_info)
    """
    if corrector is None:
        corrector = SurvivorshipBiasCorrector()

    adjustment = corrector.calculate_survivorship_bias(
        current_universe, backtest_start, backtest_end
    )
    adjusted_returns = corrector.adjust_returns_for_survivorship(returns, adjustment)

    return adjusted_returns, adjustment
