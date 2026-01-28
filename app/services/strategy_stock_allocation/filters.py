"""
Stock filtering and validation module.

Responsible for filtering stocks based on data quality, liquidity,
and other validation criteria.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from app.core.centralized_config import StockAllocationSettings

logger = logging.getLogger(__name__)


class StockFilter:
    """
    Filters and validates stocks for trading strategies.

    Single Responsibility: Validate stock data quality and filter
    based on configurable criteria.
    """

    def __init__(self, config: StockAllocationSettings) -> None:
        """
        Initialize stock filter with configuration.

        Args:
            config: Stock allocation configuration
        """
        self.config = config

    def filter_stocks(self, historical_data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
        """
        Filter stocks with complete data validation.

        Excludes:
        - Series with NaNs, gaps, or incomplete data
        - Zero or extreme volatility
        - Insufficient historical data
        - Low liquidity

        Args:
            historical_data: Dictionary mapping ticker to DataFrame with OHLCV data

        Returns:
            Dictionary of filtered stocks with valid data
        """
        logger.info(f"Filtering stocks from {len(historical_data)} candidates")
        filtered = {}
        rejection_log = []

        min_days = self.config.LOOKBACK_MAX_DAYS

        for ticker, df in historical_data.items():
            rejection_reasons = []

            # Check if DataFrame is valid
            if df is None or df.empty:
                rejection_reasons.append("Empty or None DataFrame")
                if self.config.LOG_FILTER_REJECTIONS:
                    rejection_log.append(f"{ticker}: Empty or None DataFrame")
                continue

            # Check required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                rejection_reasons.append(
                    f"Missing required columns: {set(required_cols) - set(df.columns)}"
                )
                if self.config.LOG_FILTER_REJECTIONS:
                    rejection_log.append(f"{ticker}: Missing columns")
                continue

            # Check sufficient history
            min_required_days = max(40, min(min_days, 126))
            if len(df) < min_required_days:
                rejection_reasons.append(
                    f"Insufficient history: {len(df)} < {min_required_days} days"
                )
                if self.config.LOG_FILTER_REJECTIONS:
                    rejection_log.append(
                        f"{ticker}: Only {len(df)} days, need at least {min_required_days}"
                    )
                continue

            # Check for NaNs
            nan_counts = df[required_cols].isna().sum()
            if nan_counts.any():
                rejection_reasons.append(f"NaNs found: {nan_counts.to_dict()}")
                if self.config.LOG_FILTER_REJECTIONS:
                    rejection_log.append(
                        f"{ticker}: NaNs in {nan_counts[nan_counts > 0].to_dict()}"
                    )
                continue

            # Check for gaps in time series
            if isinstance(df.index, pd.DatetimeIndex):
                date_diff = df.index.to_series().diff()
                expected_diff = pd.Timedelta(days=1)
                large_gaps = date_diff[date_diff > expected_diff * 2]
                max_allowed_gaps = len(df) * 0.3
                if len(large_gaps) > max_allowed_gaps:
                    rejection_reasons.append(f"Too many time gaps: {len(large_gaps)} gaps")
                    if self.config.LOG_FILTER_REJECTIONS:
                        rejection_log.append(
                            f"{ticker}: {len(large_gaps)} time gaps (exceeds {max_allowed_gaps:.0f})"
                        )
                    continue

            # Check price consistency
            invalid_prices = (
                (df['high'] < df['low']).any()
                or (df['close'] > df['high']).any()
                or (df['close'] < df['low']).any()
                or (df['open'] > df['high']).any()
                or (df['open'] < df['low']).any()
            )
            if invalid_prices:
                rejection_reasons.append("Price inconsistencies (high < low, etc.)")
                if self.config.LOG_FILTER_REJECTIONS:
                    rejection_log.append(f"{ticker}: Price inconsistencies")
                continue

            # Check for zero or negative prices
            if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
                rejection_reasons.append("Zero or negative prices")
                if self.config.LOG_FILTER_REJECTIONS:
                    rejection_log.append(f"{ticker}: Zero or negative prices")
                continue

            # Check volatility
            prices = df['close'].values
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns)

            if volatility == 0 or np.isnan(volatility):
                rejection_reasons.append(f"Zero or NaN volatility: {volatility}")
                if self.config.LOG_FILTER_REJECTIONS:
                    rejection_log.append(f"{ticker}: Zero volatility")
                continue

            # Check for extreme volatility
            if volatility > 0.5:
                rejection_reasons.append(f"Extreme volatility: {volatility:.4f}")
                if self.config.LOG_FILTER_REJECTIONS:
                    rejection_log.append(f"{ticker}: Extreme volatility ({volatility:.2%})")
                continue

            # Check liquidity
            avg_volume = df['volume'].mean()
            avg_price = df['close'].mean()
            avg_liquidity_usd = avg_volume * avg_price
            min_liquidity_required = self.config.MIN_LIQUIDITY_USD * 0.02

            if avg_liquidity_usd < min_liquidity_required:
                rejection_reasons.append(
                    f"Insufficient liquidity: ${avg_liquidity_usd:,.0f} < ${min_liquidity_required:,.0f}"
                )
                if self.config.LOG_FILTER_REJECTIONS:
                    rejection_log.append(
                        f"{ticker}: Low liquidity (${avg_liquidity_usd:,.0f} < ${min_liquidity_required:,.0f})"
                    )
                continue

            # All checks passed
            filtered[ticker] = df

            if self.config.LOG_FILTER_REJECTIONS:
                logger.debug(
                    f"✅ {ticker}: Passed all filters (volatility={volatility:.4f}, liquidity=${avg_liquidity_usd:,.0f})"
                )

        logger.info(f"Filtered stocks: {len(filtered)}/{len(historical_data)} passed validation")

        if self.config.LOG_FILTER_REJECTIONS and rejection_log:
            logger.warning(
                f"❌ Stock rejection summary ({len(rejection_log)} rejections, showing first 20):"
            )
            for i, reason in enumerate(rejection_log[:20], 1):
                logger.warning(f"  {i}. {reason}")
            if len(rejection_log) > 20:
                logger.warning(f"  ... and {len(rejection_log) - 20} more rejections")

        # Log diagnostic info if no stocks passed
        if len(filtered) == 0 and len(historical_data) > 0:
            logger.error(
                f"🚨 CRITICAL: All {len(historical_data)} stocks were rejected! "
                f"Check: LOOKBACK_MAX_DAYS={min_days}, MIN_LIQUIDITY_USD={self.config.MIN_LIQUIDITY_USD}"
            )

        return filtered
