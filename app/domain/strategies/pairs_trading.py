"""
Pairs Trading Strategy Domain Service

Implements statistical arbitrage based on cointegration between
pairs of assets that move together in the long run.

Reference: Rule 49-papers-gatev-pairs-trading.md
Paper: Gatev, E., et al. (2006). "Pairs Trading: Performance of a Relative-Value Arbitrage Rule"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class PairSignal(str, Enum):
    """Signal for pairs trading."""

    LONG_SHORT = "long_short"  # Long asset A, Short asset B
    SHORT_LONG = "short_long"  # Short asset A, Long asset B
    CLOSE_LONG_SHORT = "close_long_short"  # Close existing position
    CLOSE_SHORT_LONG = "close_short_long"  # Close existing position
    NO_ACTION = "no_action"


@dataclass
class CointegrationResult:
    """Result of cointegration test."""

    is_cointegrated: bool
    test_statistic: float  # Engle-Granger or Johansen statistic
    p_value: float  # Statistical significance
    critical_value: float  # Critical value at confidence level
    hedge_ratio: float  # Optimal hedge ratio (beta)
    half_life: float  # Expected half-life of spread
    confidence: float  # Confidence in cointegration (0-1)


@dataclass
class PairPosition:
    """Position for a pairs trade."""

    symbol_a: str
    symbol_b: str
    signal: PairSignal
    weight_a: float  # Weight for asset A
    weight_b: float  # Weight for asset B
    spread: float  # Current spread
    z_score: float  # Z-score of spread
    entry_spread: float  # Spread at entry
    stop_loss_spread: Optional[float] = None  # Stop loss based on spread
    take_profit_spread: Optional[float] = None  # Take profit based on spread

    @property
    def net_exposure(self) -> float:
        """Get net market exposure."""
        return abs(self.weight_a) + abs(self.weight_b)

    def is_long_short(self) -> bool:
        """Check if position is long A, short B."""
        return self.signal == PairSignal.LONG_SHORT

    def is_short_long(self) -> bool:
        """Check if position is short A, long B."""
        return self.signal == PairSignal.SHORT_LONG


@dataclass
class TradingPair:
    """A pair of assets for pairs trading."""

    symbol_a: str
    symbol_b: str
    coint_result: CointegrationResult
    p_value: float  # Historical p-value
    avg_half_life: float  # Average historical half-life
    trade_count: int  # Number of historical trades

    @property
    def pair_id(self) -> str:
        """Get unique pair identifier."""
        return f"{self.symbol_a}_{self.symbol_b}"

    def is_valid_pair(self) -> bool:
        """Check if pair is valid for trading."""
        return (
            self.coint_result.is_cointegrated
            and self.coint_result.p_value < 0.05
            and self.coint_result.half_life < 60  # Max 60 days half-life
        )


class PairsTrading:
    """
    Pairs trading strategy using cointegration.

    Identifies pairs of assets that are cointegrated (move together
    in the long run) and trades mean reversion of the spread.

    This is a pure domain service that can be used with any data source.

    Reference: Gatev, E., et al. (2006)
    """

    def __init__(
        self,
        formation_period: int = 252,  # Days to form pairs (1 year)
        trading_period: int = 126,  # Days to trade pairs (6 months)
        z_score_entry: float = 2.0,  # Z-score for entry
        z_score_exit: float = 0.5,  # Z-score for exit
        min_half_life: float = 5.0,  # Minimum acceptable half-life
        max_half_life: float = 60.0,  # Maximum acceptable half-life
        num_pairs: int = 20,  # Number of pairs to trade
    ):
        """
        Initialize pairs trading strategy.

        Args:
            formation_period: Period to identify cointegrated pairs
            trading_period: Period to trade identified pairs
            z_score_entry: Z-score threshold for entry
            z_score_exit: Z-score threshold for exit
            min_half_life: Minimum acceptable half-life
            max_half_life: Maximum acceptable half-life
            num_pairs: Number of pairs to select
        """
        self._formation_period = formation_period
        self._trading_period = trading_period
        self._z_entry = z_score_entry
        self._z_exit = z_score_exit
        self._min_half_life = min_half_life
        self._max_half_life = max_half_life
        self._num_pairs = num_pairs

        # Load trading thresholds from config
        trading_config = get_config()
        self._tt = trading_config.trading_thresholds

    def find_cointegrated_pairs(
        self,
        price_data: Dict[str, np.ndarray],
    ) -> List[TradingPair]:
        """
        Find cointegrated pairs from price data.

        Args:
            price_data: Dictionary of symbol -> price history

        Returns:
            List of TradingPair sorted by p-value
        """
        symbols = list(price_data.keys())
        pairs = []

        # Test all possible pairs
        for i, symbol_a in enumerate(symbols):
            for symbol_b in symbols[i + 1 :]:
                prices_a = price_data[symbol_a]
                prices_b = price_data[symbol_b]

                # Skip if insufficient data
                if len(prices_a) < self._formation_period or len(prices_b) < self._formation_period:
                    continue

                # Test for cointegration
                coint_result = self._test_cointegration(prices_a, prices_b)

                if coint_result.is_cointegrated:
                    trading_pair = TradingPair(
                        symbol_a=symbol_a,
                        symbol_b=symbol_b,
                        coint_result=coint_result,
                        p_value=coint_result.p_value,
                        avg_half_life=coint_result.half_life,
                        trade_count=0,
                    )
                    pairs.append(trading_pair)

        # Sort by p-value (lowest first) and return top pairs
        pairs.sort(key=lambda p: p.p_value)

        return pairs[: self._num_pairs]

    def _test_cointegration(
        self,
        prices_a: np.ndarray,
        prices_b: np.ndarray,
    ) -> CointegrationResult:
        """
        Test if two price series are cointegrated using Engle-Granger method.

        Steps:
        1. Estimate hedge ratio via OLS: log(price_a) = alpha + beta * log(price_b) + epsilon
        2. Test residuals for stationarity using ADF test

        Args:
            prices_a: Price series for asset A
            prices_b: Price series for asset B

        Returns:
            CointegrationResult with test results
        """
        try:
            # Input validation
            if len(prices_a) < 10 or len(prices_b) < 10:
                logger.warning("Insufficient data for cointegration test")
                return CointegrationResult(
                    is_cointegrated=False,
                    test_statistic=0.0,
                    p_value=1.0,
                    critical_value=0.0,
                    hedge_ratio=1.0,
                    half_life=float('inf'),
                    confidence=0.0,
                )

            # Handle NaN and inf values
            valid_mask_a = ~np.isnan(prices_a) & ~np.isinf(prices_a) & (prices_a > 0)
            valid_mask_b = ~np.isnan(prices_b) & ~np.isinf(prices_b) & (prices_b > 0)

            prices_a_clean = prices_a[valid_mask_a]
            prices_b_clean = prices_b[valid_mask_b]

            if len(prices_a_clean) < 10 or len(prices_b_clean) < 10:
                logger.warning("Insufficient valid data after filtering NaN/inf")
                return CointegrationResult(
                    is_cointegrated=False,
                    test_statistic=0.0,
                    p_value=1.0,
                    critical_value=0.0,
                    hedge_ratio=1.0,
                    half_life=float('inf'),
                    confidence=0.0,
                )

            # Ensure same length
            min_len = min(len(prices_a_clean), len(prices_b_clean))
            prices_a_clean = prices_a_clean[-min_len:]
            prices_b_clean = prices_b_clean[-min_len:]

            # Use log prices
            try:
                log_a = np.log(prices_a_clean)
                log_b = np.log(prices_b_clean)
            except Exception as e:
                logger.warning(f"Error calculating log prices: {e}")
                return self._simple_cointegration_test(prices_a_clean, prices_b_clean)

            # Validate log prices
            if not (np.all(np.isfinite(log_a)) and np.all(np.isfinite(log_b))):
                logger.warning("Non-finite log prices, using simple test")
                return self._simple_cointegration_test(prices_a_clean, prices_b_clean)

            # Step 1: Estimate hedge ratio (beta) via OLS
            # Regression: log_a = alpha + beta * log_b + epsilon
            try:
                beta, alpha = np.polyfit(log_b, log_a, 1)
                hedge_ratio = float(beta)

                # Validate hedge ratio
                if not np.isfinite(hedge_ratio):
                    hedge_ratio = 1.0

                # Calculate spread (residuals)
                spread = log_a - (alpha + beta * log_b)

                # Validate spread
                if not np.all(np.isfinite(spread)):
                    logger.warning("Non-finite spread values")
                    return self._simple_cointegration_test(prices_a_clean, prices_b_clean)

            except Exception as e:
                logger.warning(f"Error in OLS regression: {e}")
                return self._simple_cointegration_test(prices_a_clean, prices_b_clean)

            # Step 2: Test spread for stationarity (ADF test)
            from statsmodels.tsa.stattools import adfuller

            try:
                adf_result = adfuller(spread, maxlag=1)
                test_statistic = float(adf_result[0])
                p_value = float(adf_result[1])
                critical_value = float(adf_result[4]['5%'])

                # Validate results
                if not (
                    np.isfinite(test_statistic)
                    and np.isfinite(p_value)
                    and np.isfinite(critical_value)
                ):
                    logger.warning("Non-finite ADF test results")
                    return self._simple_cointegration_test(prices_a_clean, prices_b_clean)

                is_cointegrated = test_statistic < critical_value and p_value < 0.05

                # Calculate half-life of spread
                half_life = self._calculate_half_life(spread)

                # Validate half-life
                if not np.isfinite(half_life) or half_life <= 0:
                    half_life = float('inf')

                # Confidence based on p-value
                confidence = max(0.0, min(1.0, 1.0 - p_value))

                return CointegrationResult(
                    is_cointegrated=is_cointegrated,
                    test_statistic=test_statistic,
                    p_value=p_value,
                    critical_value=critical_value,
                    hedge_ratio=hedge_ratio,
                    half_life=half_life,
                    confidence=confidence,
                )

            except Exception as e:
                logger.warning(f"Error in ADF test: {e}")
                return self._simple_cointegration_test(prices_a_clean, prices_b_clean)

        except Exception:
            # Fallback: simple correlation-based test
            return self._simple_cointegration_test(prices_a, prices_b)

    def _simple_cointegration_test(
        self,
        prices_a: np.ndarray,
        prices_b: np.ndarray,
    ) -> CointegrationResult:
        """
        Simple fallback cointegration test based on correlation and spread.

        Args:
            prices_a: Price series for asset A
            prices_b: Price series for asset B

        Returns:
            CointegrationResult with test results
        """
        # Input validation
        if len(prices_a) < 10 or len(prices_b) < 10:
            return CointegrationResult(
                is_cointegrated=False,
                test_statistic=0.0,
                p_value=1.0,
                critical_value=0.7,
                hedge_ratio=1.0,
                half_life=float('inf'),
                confidence=0.0,
            )

        # Ensure same length
        min_len = min(len(prices_a), len(prices_b))
        prices_a = prices_a[-min_len:]
        prices_b = prices_b[-min_len:]

        # Handle NaN and inf
        valid_mask = (
            ~np.isnan(prices_a)
            & ~np.isinf(prices_a)
            & (prices_a > 0)
            & ~np.isnan(prices_b)
            & ~np.isinf(prices_b)
            & (prices_b > 0)
        )

        prices_a_clean = prices_a[valid_mask]
        prices_b_clean = prices_b[valid_mask]

        if len(prices_a_clean) < 10:
            return CointegrationResult(
                is_cointegrated=False,
                test_statistic=0.0,
                p_value=1.0,
                critical_value=0.7,
                hedge_ratio=1.0,
                half_life=float('inf'),
                confidence=0.0,
            )

        # Calculate returns
        try:
            returns_a = np.diff(np.log(prices_a_clean))
            returns_b = np.diff(np.log(prices_b_clean))
        except Exception as e:
            logger.warning(f"Error calculating log returns: {e}")
            return CointegrationResult(
                is_cointegrated=False,
                test_statistic=0.0,
                p_value=1.0,
                critical_value=0.7,
                hedge_ratio=1.0,
                half_life=float('inf'),
                confidence=0.0,
            )

        # Validate returns
        if not (np.all(np.isfinite(returns_a)) and np.all(np.isfinite(returns_b))):
            return CointegrationResult(
                is_cointegrated=False,
                test_statistic=0.0,
                p_value=1.0,
                critical_value=0.7,
                hedge_ratio=1.0,
                half_life=float('inf'),
                confidence=0.0,
            )

        # Correlation of returns
        try:
            correlation = np.corrcoef(returns_a, returns_b)[0, 1]

            # Validate correlation
            if not np.isfinite(correlation):
                correlation = 0.0
        except Exception as e:
            logger.warning(f"Error calculating correlation: {e}")
            correlation = 0.0

        # Simple hedge ratio from volatility ratio
        std_a = np.std(returns_a)
        std_b = np.std(returns_b)
        hedge_ratio = std_a / std_b if std_b > 1e-10 else 1.0

        # Validate hedge_ratio
        if not np.isfinite(hedge_ratio):
            hedge_ratio = 1.0

        # Calculate spread
        spread = prices_a_clean - hedge_ratio * prices_b_clean

        # Validate spread
        if not np.all(np.isfinite(spread)):
            spread = prices_a_clean - prices_b_clean  # Fallback to simple difference

        # Calculate half-life
        half_life = self._calculate_half_life(spread)

        # Validate half_life
        if not np.isfinite(half_life) or half_life <= 0:
            half_life = float('inf')

        # Simple cointegration criterion
        is_cointegrated = correlation > self._tt.pairs_correlation_min and half_life < self._max_half_life

        return CointegrationResult(
            is_cointegrated=is_cointegrated,
            test_statistic=correlation if np.isfinite(correlation) else 0.0,
            p_value=1.0 - correlation if np.isfinite(correlation) else 1.0,  # Rough approximation
            critical_value=0.7,
            hedge_ratio=float(hedge_ratio),
            half_life=half_life,
            confidence=max(0.0, correlation) if np.isfinite(correlation) else 0.0,
        )

    def _calculate_half_life(self, spread: np.ndarray) -> float:
        """
        Calculate half-life of mean reversion for spread.

        Args:
            spread: Spread series

        Returns:
            Half-life in periods
        """
        if len(spread) < 10:
            return 0.0

        # Calculate deviations
        deviations = spread - np.mean(spread)

        # Lagged values
        lagged = deviations[:-1]
        current = deviations[1:]

        if len(lagged) < 2:
            return 0.0

        # OLS: delta_x = theta * (mu - x) -> slope = -theta
        delta = current - lagged
        slope, _ = np.polyfit(lagged, delta, 1)

        theta = -slope

        if theta <= 0:
            return float('inf')

        half_life = np.log(2) / theta

        return float(half_life)

    def calculate_spread_z_score(
        self,
        trading_pair: TradingPair,
        prices_a: np.ndarray,
        prices_b: np.ndarray,
    ) -> float:
        """
        Calculate Z-score of the current spread.

        Args:
            trading_pair: Trading pair with hedge ratio
            prices_a: Current prices for asset A
            prices_b: Current prices for asset B

        Returns:
            Z-score of spread
        """
        hedge_ratio = trading_pair.coint_result.hedge_ratio

        # Use log prices for spread calculation
        log_a = np.log(prices_a)
        log_b = np.log(prices_b)

        # Calculate spread
        spread = log_a - hedge_ratio * log_b

        # Use only recent history for Z-score
        lookback = min(self._formation_period, len(spread))
        recent_spread = spread[-lookback:]

        # Z-score
        mean = np.mean(recent_spread)
        std = np.std(recent_spread)

        if std < 1e-10:
            return 0.0

        current_spread = spread[-1]
        z_score = (current_spread - mean) / std

        return float(z_score)

    def generate_signal(
        self,
        trading_pair: TradingPair,
        prices_a: np.ndarray,
        prices_b: np.ndarray,
        current_position: Optional[PairPosition] = None,
    ) -> PairSignal:
        """
        Generate trading signal for a pair.

        Args:
            trading_pair: Trading pair to analyze
            prices_a: Price history for asset A
            prices_b: Price history for asset B
            current_position: Existing position (if any)

        Returns:
            PairSignal with action
        """
        # Calculate Z-score
        z_score = self.calculate_spread_z_score(trading_pair, prices_a, prices_b)

        # Calculate current spread
        log_a = float(np.log(prices_a[-1]))
        log_b = float(np.log(prices_b[-1]))
        spread = log_a - trading_pair.coint_result.hedge_ratio * log_b

        # Check if we have an existing position
        if current_position:
            # Check exit conditions
            if current_position.is_long_short():
                # Close if Z-score crossed zero or reached exit threshold
                if abs(z_score) < self._z_exit:
                    return PairSignal.CLOSE_LONG_SHORT
            elif current_position.is_short_long():
                if abs(z_score) < self._z_exit:
                    return PairSignal.CLOSE_SHORT_LONG

            # Check stop loss / take profit
            if current_position.stop_loss_spread and current_position.take_profit_spread:
                if (
                    spread >= current_position.take_profit_spread
                    or spread <= current_position.stop_loss_spread
                ):
                    if current_position.is_long_short():
                        return PairSignal.CLOSE_LONG_SHORT
                    else:
                        return PairSignal.CLOSE_SHORT_LONG

            return PairSignal.NO_ACTION

        # No existing position - check entry conditions
        if z_score > self._z_entry:
            # Spread is high - short A, long B
            return PairSignal.SHORT_LONG
        elif z_score < -self._z_entry:
            # Spread is low - long A, short B
            return PairSignal.LONG_SHORT

        return PairSignal.NO_ACTION

    def create_pair_position(
        self,
        trading_pair: TradingPair,
        signal: PairSignal,
        prices_a: np.ndarray,
        prices_b: np.ndarray,
        capital: float = 100000.0,
    ) -> PairPosition:
        """
        Create a pair position based on signal.

        Args:
            trading_pair: Trading pair
            signal: Trading signal
            prices_a: Price history for asset A
            prices_b: Price history for asset B
            capital: Total capital for the pair trade

        Returns:
            PairPosition with weights and risk levels
        """
        # Calculate Z-score and spread
        z_score = self.calculate_spread_z_score(trading_pair, prices_a, prices_b)

        log_a = float(np.log(prices_a[-1]))
        log_b = float(np.log(prices_b[-1]))
        spread = log_a - trading_pair.coint_result.hedge_ratio * log_b

        # Calculate hedge ratio
        hedge_ratio = trading_pair.coint_result.hedge_ratio

        # Equal-weight allocation (dollar neutral)
        # Long A: +50%, Short B: -50% (or vice versa)

        if signal == PairSignal.LONG_SHORT:
            weight_a = 0.5
            weight_b = -0.5 * hedge_ratio
        elif signal == PairSignal.SHORT_LONG:
            weight_a = -0.5
            weight_b = 0.5 * hedge_ratio
        else:
            weight_a = 0.0
            weight_b = 0.0

        # Calculate risk levels
        spread_std = np.std(log_a - hedge_ratio * log_b) if len(prices_a) > 1 else 0.01

        entry_spread = spread
        stop_loss = (
            entry_spread + 3 * spread_std
            if signal == PairSignal.LONG_SHORT
            else entry_spread - 3 * spread_std
        )
        take_profit = (
            entry_spread - spread_std
            if signal == PairSignal.LONG_SHORT
            else entry_spread + spread_std
        )

        return PairPosition(
            symbol_a=trading_pair.symbol_a,
            symbol_b=trading_pair.symbol_b,
            signal=signal,
            weight_a=weight_a,
            weight_b=weight_b,
            spread=spread,
            z_score=z_score,
            entry_spread=entry_spread,
            stop_loss_spread=float(stop_loss),
            take_profit_spread=float(take_profit),
        )

    def update_pair_position(
        self,
        position: PairPosition,
        prices_a: np.ndarray,
        prices_b: np.ndarray,
    ) -> PairPosition:
        """
        Update an existing pair position with current prices.

        Args:
            position: Existing position
            prices_a: Current price history for asset A
            prices_b: Current price history for asset B

        Returns:
            Updated PairPosition
        """
        log_a = float(np.log(prices_a[-1]))
        log_b = float(np.log(prices_b[-1]))

        # Recalculate spread
        hedge_ratio = position.weight_b / position.weight_a if position.weight_a != 0 else 1.0
        spread = log_a - hedge_ratio * log_b

        position.spread = spread
        return position
