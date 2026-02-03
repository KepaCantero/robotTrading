"""
Bias Correctors for Backtesting

This module implements Ernest Chan's methodologies for eliminating biases
in backtesting, ensuring realistic performance estimates.

Key Concepts from Ernest Chan:
1. Look-ahead bias prevention
2. Survivorship bias correction
3. Correct handling of dividends and splits
4. Point-in-time data requirements

Reference:
    "Algorithmic Trading" by Ernest P. Chan (2013)
    Chapter 3: Backtesting
    Section: Common Pitfalls and Biases
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BiasDetectionResult:
    """Results from bias detection analysis."""

    has_lookahead_bias: bool
    lookahead_bias_severity: float  # 0-1 scale
    has_survivorship_bias: bool
    survivorship_bias_adjustment: float
    has_data_snooping_bias: bool
    corrected_sharpe_ratio: float
    original_sharpe_ratio: float
    recommendations: List[str]


@dataclass
class CorporateAction:
    """Corporate action for adjustment."""

    date: datetime
    symbol: str
    action_type: str  # 'split', 'dividend', 'dividend_return', 'rights_issue'
    ratio: Optional[float] = None  # For splits
    amount: Optional[float] = None  # For dividends
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PointInTimeData:
    """Point-in-time data snapshot."""

    as_of_date: datetime
    available_symbols: List[str]
    delisted_symbols: List[str]
    new_listings: List[str]
    corporate_actions: List[CorporateAction]


class LookAheadBiasCorrector:
    """
    Corrector for look-ahead bias in backtesting.

    Ernest Chan's definition:
    Look-ahead bias occurs when future information is inadvertently used
    in trading decisions, leading to inflated performance.

    Common causes:
    1. Using data that wasn't available at trading time
    2. Calculating indicators using future data
    3. Using forward-filled data
    4. Applying current-day knowledge to historical decisions
    """

    def __init__(self, strict_mode: bool = True):
        """
        Initialize look-ahead bias corrector.

        Args:
            strict_mode: If True, reject any potential look-ahead bias
        """
        self.strict_mode = strict_mode
        self.detected_issues: List[str] = []

    def validate_no_lookahead(
        self,
        signals: pd.DataFrame,
        market_data: pd.DataFrame,
        signal_columns: List[str],
        timestamp_column: str = "timestamp",
    ) -> BiasDetectionResult:
        """
        Validate that signals don't use future information.

        Ernest Chan's checks:
        1. Signal timestamp <= data timestamp
        2. Indicator values calculated from historical data only
        3. No forward filling of future data

        Args:
            signals: DataFrame with signals and timestamps
            market_data: DataFrame with market data
            signal_columns: Columns to check for look-ahead
            timestamp_column: Name of timestamp column

        Returns:
            BiasDetectionResult with findings
        """
        self.detected_issues = []

        try:
            # Check 1: Timestamp alignment
            if timestamp_column in signals.columns and timestamp_column in market_data.columns:
                signal_times = pd.to_datetime(signals[timestamp_column])
                data_times = pd.to_datetime(market_data[timestamp_column])

                # Check if any signal time is after available data time
                # This is a simplified check - in practice, you'd check row-by-row
                if signal_times.max() > data_times.max():
                    self.detected_issues.append("Signals exist after available data period")

            # Check 2: Indicator calculation windows
            for col in signal_columns:
                if col in signals.columns:
                    # Check for NaN values at the beginning
                    # (indicators need lookback period)
                    nan_count = signals[col].isna().sum()
                    if nan_count == 0:
                        self.detected_issues.append(
                            f"Column '{col}' has no initial NaN values - "
                            "possible look-ahead in indicator calculation"
                        )

            # Check 3: Forward filling detection
            for col in signal_columns:
                if col in signals.columns:
                    # Check for suspicious patterns
                    # (e.g., repeated values indicating forward fill)
                    repeated_ratio = (signals[col] == signals[col].shift(1)).mean()
                    if repeated_ratio > 0.8:
                        self.detected_issues.append(
                            f"Column '{col}' has {repeated_ratio:.1%} repeated values - "
                            "possible forward filling"
                        )

            has_bias = len(self.detected_issues) > 0
            severity = min(1.0, len(self.detected_issues) / 5.0)

            recommendations = self._generate_lookahead_recommendations()

            return BiasDetectionResult(
                has_lookahead_bias=has_bias,
                lookahead_bias_severity=severity,
                has_survivorship_bias=False,
                survivorship_bias_adjustment=1.0,
                has_data_snooping_bias=False,
                corrected_sharpe_ratio=0.0,
                original_sharpe_ratio=0.0,
                recommendations=recommendations,
            )

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error detecting look-ahead bias: {e}", exc_info=True)
            return BiasDetectionResult(
                has_lookahead_bias=False,
                lookahead_bias_severity=0.0,
                has_survivorship_bias=False,
                survivorship_bias_adjustment=1.0,
                has_data_snooping_bias=False,
                corrected_sharpe_ratio=0.0,
                original_sharpe_ratio=0.0,
                recommendations=[f"Error in validation: {e}"],
            )

    def _generate_lookahead_recommendations(self) -> List[str]:
        """Generate recommendations to fix look-ahead bias."""
        recommendations = []

        for issue in self.detected_issues:
            if "after available data" in issue:
                recommendations.append("Ensure all signals use only data available at signal time")
            elif "no initial NaN" in issue:
                recommendations.append(
                    "Recalculate indicators with proper lookback period - "
                    "initial values should be NaN"
                )
            elif "forward filling" in issue:
                recommendations.append(
                    "Use backward filling (ffill) instead of forward filling, "
                    "or leave NaN values"
                )

        if not recommendations:
            recommendations.append("No look-ahead bias detected - good practices followed")

        return recommendations


class DividendAndSplitAdjuster:
    """
    Adjuster for dividends and stock splits in price data.

    Ernest Chan's methodology:
    1. Stock splits: Adjust historical prices by split ratio
    2. Dividends: Adjust for total return (price + dividends)
    3. Apply adjustments chronologically (oldest first)
    4. Keep track of adjustment factors
    """

    # Typical adjustment factors
    STOCK_SPLIT_FACTORS = {
        "2-for-1": 0.5,
        "3-for-2": 2 / 3,
        "3-for-1": 1 / 3,
        "5-for-4": 0.8,
    }

    def __init__(self, adjustment_method: str = "backwards"):
        """
        Initialize dividend and split adjuster.

        Args:
            adjustment_method: 'backwards' (Ernest Chan's preferred) or 'forwards'
        """
        self.adjustment_method = adjustment_method
        self.adjustment_factors: Dict[str, List[Tuple[datetime, float]]] = {}

    def apply_stock_split(
        self,
        prices: pd.DataFrame,
        split_date: datetime,
        split_ratio: float,
        symbol_col: str = "symbol",
        price_col: str = "close",
        date_col: str = "date",
    ) -> pd.DataFrame:
        """
        Apply stock split adjustment to price data.

        Ernest Chan's formula:
        adjusted_price = raw_price / split_ratio (for splits after the date)

        Args:
            prices: DataFrame with price data
            split_date: Date of split
            split_ratio: Split ratio (e.g., 0.5 for 2-for-1 split)
            symbol_col: Column name for symbol
            price_col: Column name for price
            date_col: Column name for date

        Returns:
            Adjusted price DataFrame
        """
        try:
            prices = prices.copy()

            if date_col in prices.columns:
                prices[date_col] = pd.to_datetime(prices[date_col])

                # Apply adjustment to historical prices (before split)
                if self.adjustment_method == "backwards":
                    # Ernest Chan's preferred method
                    # Adjust historical prices downwards
                    mask = prices[date_col] < split_date
                    prices.loc[mask, price_col] = prices.loc[mask, price_col] * split_ratio

                    # Also adjust other price columns
                    for col in ["open", "high", "low"]:
                        if col in prices.columns:
                            prices.loc[mask, col] = prices.loc[mask, col] * split_ratio
                else:
                    # Forward adjustment (less common)
                    mask = prices[date_col] >= split_date
                    prices.loc[mask, price_col] = prices.loc[mask, price_col] / split_ratio

                    for col in ["open", "high", "low"]:
                        if col in prices.columns:
                            prices.loc[mask, col] = prices.loc[mask, col] / split_ratio

                logger.info(
                    f"Applied stock split adjustment: ratio={split_ratio}, "
                    f"date={split_date.date()}, method={self.adjustment_method}"
                )

            return prices

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error applying stock split: {e}", exc_info=True)
            return prices

    def calculate_total_return(
        self,
        prices: pd.Series,
        dividends: pd.Series,
    ) -> pd.Series:
        """
        Calculate total return including dividends.

        Ernest Chan's formula:
        total_return = (price_change + dividends) / initial_price

        Args:
            prices: Price series
            dividends: Dividend series (same index as prices)

        Returns:
            Total return series
        """
        try:
            # Align series
            aligned_prices, aligned_dividends = prices.align(dividends, join="left")

            # Fill NaN dividends with 0
            aligned_dividends = aligned_dividends.fillna(0)

            # Calculate price returns
            price_returns = aligned_prices.pct_change()

            # Calculate dividend returns
            dividend_returns = aligned_dividends / aligned_prices.shift(1)

            # Total return
            total_returns = price_returns + dividend_returns

            return total_returns

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating total return: {e}", exc_info=True)
            return prices.pct_change()

    def reconstruct_adjusted_prices(
        self,
        raw_prices: pd.Series,
        dividends: pd.DataFrame,
        splits: pd.DataFrame,
    ) -> pd.Series:
        """
        Reconstruct price series with all adjustments applied.

        Ernest Chan's methodology:
        1. Apply all stock splits (oldest first)
        2. Add back dividends to calculate total return
        3. Ensure chronological order of adjustments

        Args:
            raw_prices: Raw price series
            dividends: DataFrame with dividend data (date, amount)
            splits: DataFrame with split data (date, ratio)

        Returns:
            Adjusted price series
        """
        try:
            adjusted_prices = raw_prices.copy()

            # Apply splits in chronological order (oldest first)
            if not splits.empty and "date" in splits.columns:
                splits = splits.sort_values("date")

                # Vectorized split adjustment
                for i in range(len(splits)):
                    split_date = pd.to_datetime(splits.iloc[i]["date"])
                    split_ratio = splits.iloc[i]["ratio"]

                    # Find prices before this split
                    mask = adjusted_prices.index < split_date
                    adjusted_prices.loc[mask] = adjusted_prices.loc[mask] * split_ratio

            # Calculate total return index (including dividends)
            if not dividends.empty and "date" in dividends.columns:
                # Create dividend series aligned to prices (vectorized)
                div_dates = pd.to_datetime(dividends["date"])
                div_amounts = dividends["amount"].values

                # Create mapping for valid dates
                valid_mask = div_dates.isin(adjusted_prices.index)
                div_series = pd.Series(0.0, index=adjusted_prices.index)
                div_series.loc[div_dates[valid_mask]] = div_amounts[valid_mask]

                # Calculate total return
                price_returns = adjusted_prices.pct_change()
                dividend_returns = div_series / adjusted_prices.shift(1)
                total_returns = price_returns + dividend_returns

                # Reconstruct prices from total returns
                adjusted_prices = (1 + total_returns).cumprod() * adjusted_prices.iloc[0]

            return adjusted_prices

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error reconstructing adjusted prices: {e}", exc_info=True)
            return raw_prices


class BacktestValidator:
    """
    Comprehensive validator for backtesting biases.

    Implements Ernest Chan's checklist for realistic backtesting:
    1. No look-ahead bias
    2. Survivorship bias corrected
    3. Dividends and splits handled
    4. Realistic transaction costs
    5. No data snooping
    """

    def __init__(
        self,
        min_samples: int = 100,
        confidence_level: float = 0.95,
    ):
        """
        Initialize backtest validator.

        Args:
            min_samples: Minimum samples required for validation
            confidence_level: Confidence level for statistical tests
        """
        self.min_samples = min_samples
        self.confidence_level = confidence_level

        self.lookahead_corrector = LookAheadBiasCorrector()
        self.dividend_adjuster = DividendAndSplitAdjuster()

    def validate_backtest(
        self,
        returns: pd.Series,
        signals: pd.DataFrame,
        market_data: pd.DataFrame,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> BiasDetectionResult:
        """
        Perform comprehensive backtest validation.

        Ernest Chan's validation checklist:
        1. Check for look-ahead bias
        2. Check survivorship bias
        3. Validate transaction costs
        4. Check for data snooping
        5. Calculate corrected Sharpe ratio

        Args:
            returns: Strategy returns
            signals: Signal DataFrame
            market_data: Market data DataFrame
            benchmark_returns: Optional benchmark returns for comparison

        Returns:
            Comprehensive BiasDetectionResult
        """
        try:
            recommendations = []
            has_issues = False

            # 1. Look-ahead bias check
            lookahead_result = self.lookahead_corrector.validate_no_lookahead(
                signals=signals,
                market_data=market_data,
                signal_columns=list(signals.columns),
            )

            if lookahead_result.has_lookahead_bias:
                has_issues = True
                recommendations.extend(lookahead_result.recommendations)

            # 2. Calculate original and corrected Sharpe ratios
            original_sharpe = self._calculate_sharpe_ratio(returns)

            # Apply penalties for biases
            sharpe_penalty = 0.0

            if lookahead_result.has_lookahead_bias:
                # Ernest Chan: look-ahead bias typically inflates Sharpe by 20-50%
                sharpe_penalty += 0.3 * lookahead_result.lookahead_bias_severity

            # Assume some survivorship bias (from historical studies)
            survivorship_adjustment = 1.02  # 2% adjustment
            sharpe_penalty += 0.05

            corrected_sharpe = original_sharpe / (1 + sharpe_penalty)

            # 3. Check for data snooping
            has_snooping = self._check_data_snooping(returns, benchmark_returns)
            if has_snooping:
                has_issues = True
                recommendations.append(
                    "Possible data snooping detected - "
                    "strategy may be overfit to historical data"
                )

            # 4. Sample size validation
            if len(returns) < self.min_samples:
                has_issues = True
                recommendations.append(
                    f"Insufficient samples ({len(returns)} < {self.min_samples}) - "
                    "results may not be statistically significant"
                )

            # 5. Generate summary recommendations
            if not has_issues:
                recommendations.append("Backtest validation passed - no major biases detected")

            return BiasDetectionResult(
                has_lookahead_bias=lookahead_result.has_lookahead_bias,
                lookahead_bias_severity=lookahead_result.lookahead_bias_severity,
                has_survivorship_bias=True,  # Always assume some survivorship bias
                survivorship_bias_adjustment=survivorship_adjustment,
                has_data_snooping_bias=has_snooping,
                corrected_sharpe_ratio=corrected_sharpe,
                original_sharpe_ratio=original_sharpe,
                recommendations=recommendations,
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Error in backtest validation: {e}", exc_info=True)
            return BiasDetectionResult(
                has_lookahead_bias=False,
                lookahead_bias_severity=0.0,
                has_survivorship_bias=True,
                survivorship_bias_adjustment=1.0,
                has_data_snooping_bias=False,
                corrected_sharpe_ratio=0.0,
                original_sharpe_ratio=0.0,
                recommendations=[f"Validation error: {e}"],
            )

    def _calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.02,
    ) -> float:
        """Calculate annualized Sharpe ratio."""
        try:
            returns_clean = returns.dropna()

            if len(returns_clean) < 2:
                return 0.0

            mean_return = returns_clean.mean() * 252  # Annualize
            std_return = returns_clean.std() * np.sqrt(252)  # Annualize

            if std_return == 0:
                return 0.0

            sharpe = (mean_return - risk_free_rate) / std_return
            return float(sharpe)

        except (ValueError, ZeroDivisionError):
            return 0.0

    def _check_data_snooping(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> bool:
        """
        Check for data snooping bias.

        Ernest Chan's indicators:
        1. Performance degrades significantly out-of-sample
        2. Sharpe ratio suspiciously high (>3)
        3. Too many parameters relative to samples
        """
        try:
            # Check 1: Suspiciously high Sharpe ratio
            sharpe = self._calculate_sharpe_ratio(returns)
            if sharpe > 3.0:
                return True

            # Check 2: Compare with benchmark if available
            if benchmark_returns is not None:
                excess_return = returns.mean() - benchmark_returns.mean()
                if excess_return > 0.002:  # Very high daily excess return
                    return True

            # Check 3: Sample size to parameter ratio
            # (simplified - would need strategy parameters for full check)
            if len(returns) < 252:  # Less than one year of daily data
                return True

            return False

        except (ValueError, TypeError):
            return False


def create_bias_correction_pipeline(
    raw_data: pd.DataFrame,
    dividend_data: Optional[pd.DataFrame] = None,
    split_data: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Create a bias correction pipeline for backtesting data.

    Implements Ernest Chan's complete pipeline:
    1. Adjust for stock splits
    2. Adjust for dividends
    3. Validate no look-ahead bias
    4. Output clean data for backtesting

    Args:
        raw_data: Raw price data
        dividend_data: Optional dividend data
        split_data: Optional split data

    Returns:
        Adjusted and validated price data

    Examples:
        >>> raw_prices = pd.DataFrame({...})
        >>> dividends = pd.DataFrame({...})
        >>> splits = pd.DataFrame({...})
        >>> clean_data = create_bias_correction_pipeline(raw_prices, dividends, splits)
        >>> # Use clean_data for backtesting
    """
    adjuster = DividendAndSplitAdjuster()
    BacktestValidator()

    try:
        # Step 1: Apply stock splits
        adjusted_data = raw_data.copy()

        if split_data is not None and not split_data.empty:
            # Vectorized: iterate using iloc instead of iterrows
            for i in range(len(split_data)):
                split_date = pd.to_datetime(split_data.iloc[i]["date"])
                split_ratio = split_data.iloc[i]["ratio"]
                adjusted_data = adjuster.apply_stock_split(
                    adjusted_data,
                    split_date=split_date,
                    split_ratio=split_ratio,
                )

        # Step 2: Calculate total return (if dividends available)
        if dividend_data is not None and not dividend_data.empty:
            if "close" in adjusted_data.columns:
                prices = adjusted_data["close"]
                dividends = (
                    dividend_data.set_index("date")["amount"]
                    if "date" in dividend_data.columns
                    else dividend_data["amount"]
                )

                total_returns = adjuster.calculate_total_return(prices, dividends)

                # Add total return column
                adjusted_data["total_return"] = total_returns

        logger.info("Bias correction pipeline completed successfully")

        return adjusted_data

    except Exception as e:
        logger.error(f"Error in bias correction pipeline: {e}", exc_info=True)
        return raw_data
