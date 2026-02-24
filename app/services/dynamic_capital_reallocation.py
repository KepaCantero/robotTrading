"""
Dynamic Capital Reallocation Engine

Implements dynamic capital reallocation based on rolling performance metrics:
- Rolling Sharpe ratio (30-day window)
- Rolling return/drawdown ratio
- Volatility-adjusted performance
- Automatic rebalancing every N days (configurable)

Based on diagnosis: Multi-strategy system needs adaptive capital allocation
instead of static weights.

Uses centralized configuration for all thresholds and parameters.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import numpy as np

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Performance metrics for a strategy over a time window."""

    def __init__(
        self,
        returns: List[Decimal],
        sharpe_ratio: Optional[float],
        max_drawdown: float,
        win_rate: float,
        volatility: float,
        total_trades: int,
    ):
        self.returns = returns
        self.sharpe_ratio = sharpe_ratio
        self.max_drawdown = max_drawdown
        self.win_rate = win_rate
        self.volatility = volatility
        self.total_trades = total_trades

    @property
    def return_drawdown_ratio(self) -> float:
        """Calculate return/drawdown ratio (risk-adjusted metric)."""
        if self.max_drawdown == 0:
            return 0.0
        avg_return = float(np.mean(self.returns)) if self.returns else 0.0
        return avg_return / abs(self.max_drawdown) if self.max_drawdown != 0 else 0.0

    @property
    def composite_score(self) -> float:
        """
        Composite score combining multiple metrics.
        Higher is better.
        """
        score = 0.0

        # Sharpe ratio component (0-50 points)
        if self.sharpe_ratio is not None and self.sharpe_ratio > 0:
            score += min(50.0, self.sharpe_ratio * 25.0)  # Cap at 50
        elif self.sharpe_ratio is not None and self.sharpe_ratio < 0:
            score -= min(25.0, abs(self.sharpe_ratio) * 12.5)  # Penalize negative Sharpe

        # Return/Drawdown ratio component (0-30 points)
        rd_ratio = self.return_drawdown_ratio
        if rd_ratio > 0:
            score += min(30.0, rd_ratio * 10.0)
        else:
            score -= min(15.0, abs(rd_ratio) * 5.0)

        # Win rate component (0-20 points)
        if self.total_trades > 0:
            win_rate_score = (self.win_rate - 0.3) * 40.0  # Base 30%, scale up
            score += max(0.0, min(20.0, win_rate_score))

        return score


class DynamicCapitalReallocationEngine:
    """
    Dynamic Capital Reallocation Engine.

    Recalibrates strategy weights based on:
    - Rolling 30-day Sharpe ratio
    - Return/Drawdown ratio
    - Volatility-adjusted performance
    - Minimum viable activity (trades per period)
    """

    def __init__(
        self,
        rebalance_frequency_days: int = None,
        rolling_window_days: int = None,
        min_weight: Decimal = None,
        max_weight: Decimal = None,
        volatility_target: float = None,
        min_trades_threshold: int = None,
    ):
        """
        Initialize reallocation engine.

        Args:
            rebalance_frequency_days: Days between rebalancing (uses centralized config if None)
            rolling_window_days: Rolling window for performance calculation (uses centralized config if None)
            min_weight: Minimum weight per strategy (uses centralized config if None)
            max_weight: Maximum weight per strategy (uses centralized config if None)
            volatility_target: Target annualized volatility (uses centralized config if None)
            min_trades_threshold: Minimum trades required to be considered active (uses centralized config if None)
        """
        # Get centralized config for defaults
        tt = get_config().trading_thresholds
        self._tt = tt

        self.rebalance_frequency_days = rebalance_frequency_days if rebalance_frequency_days is not None else tt.dynamic_realloc_rebalance_days
        self.rolling_window_days = rolling_window_days if rolling_window_days is not None else tt.dynamic_realloc_rolling_window
        self.min_weight = min_weight if min_weight is not None else Decimal(str(tt.dynamic_realloc_min_weight))
        self.max_weight = max_weight if max_weight is not None else Decimal(str(tt.dynamic_realloc_max_weight))
        self.volatility_target = volatility_target if volatility_target is not None else tt.dynamic_realloc_volatility_target
        self.min_trades_threshold = min_trades_threshold if min_trades_threshold is not None else tt.dynamic_realloc_min_trades

        # Performance history per strategy
        self.performance_history: Dict[str, List[Tuple[datetime, PerformanceMetrics]]] = {}

        # Last rebalance date
        self.last_rebalance_date: Optional[datetime] = None

    def update_strategy_performance(
        self,
        strategy_name: str,
        timestamp: datetime,
        pnl: Decimal,
        returns: Decimal,
        total_trades: int,
        winning_trades: int = 0,
        losing_trades: int = 0,
    ) -> None:
        """
        Update strategy performance (compatibility method for SimpleBacktester).

        Converts backtest results to PerformanceMetrics format.
        """
        # Calculate metrics from backtest results
        win_rate = float(winning_trades) / total_trades if total_trades > 0 else 0.0

        # Calculate max drawdown from returns (simplified - would need equity curve for exact)
        # For now, estimate volatility from returns
        returns_list = [returns]  # Single return value for this period

        # Estimate volatility (simplified)
        volatility = abs(float(returns)) if returns != 0 else 0.0

        # Estimate max drawdown (simplified - negative if loss)
        max_drawdown = abs(float(pnl)) if pnl < 0 else 0.0

        # Calculate Sharpe ratio (simplified - would need risk-free rate and period)
        sharpe_ratio = None  # Not calculated from single data point

        # Record performance using existing method
        self.record_performance(
            strategy_name=strategy_name,
            timestamp=timestamp,
            returns=returns_list,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            volatility=volatility,
            total_trades=total_trades,
        )

    def record_performance(
        self,
        strategy_name: str,
        timestamp: datetime,
        returns: List[Decimal],
        sharpe_ratio: Optional[float],
        max_drawdown: float,
        win_rate: float,
        volatility: float,
        total_trades: int,
    ) -> None:
        """Record performance metrics for a strategy."""
        if strategy_name not in self.performance_history:
            self.performance_history[strategy_name] = []

        metrics = PerformanceMetrics(
            returns=returns,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            volatility=volatility,
            total_trades=total_trades,
        )

        self.performance_history[strategy_name].append((timestamp, metrics))

        # Keep only last 90 days
        cutoff = timestamp - timedelta(days=90)
        self.performance_history[strategy_name] = [
            (t, m) for t, m in self.performance_history[strategy_name] if t >= cutoff
        ]

    def calculate_rolling_metrics(
        self, strategy_name: str, current_date: datetime
    ) -> Optional[PerformanceMetrics]:
        """
        Calculate rolling performance metrics for a strategy.

        Args:
            strategy_name: Name of the strategy
            current_date: Current date

        Returns:
            PerformanceMetrics or None if insufficient data
        """
        if strategy_name not in self.performance_history:
            return None

        window_start = current_date - timedelta(days=self.rolling_window_days)

        # Get metrics within window
        window_metrics = [
            metrics
            for timestamp, metrics in self.performance_history[strategy_name]
            if timestamp >= window_start
        ]

        if not window_metrics:
            return None

        # Aggregate metrics
        all_returns = []
        sharpe_ratios = []
        max_drawdowns = []
        win_rates = []
        volatilities = []
        total_trades_sum = 0

        for metrics in window_metrics:
            all_returns.extend(metrics.returns)
            if metrics.sharpe_ratio is not None:
                sharpe_ratios.append(metrics.sharpe_ratio)
            max_drawdowns.append(metrics.max_drawdown)
            win_rates.append(metrics.win_rate)
            volatilities.append(metrics.volatility)
            total_trades_sum += metrics.total_trades

        # Calculate aggregated metrics
        avg_sharpe = np.mean(sharpe_ratios) if sharpe_ratios else None
        worst_drawdown = min(max_drawdowns) if max_drawdowns else 0.0
        avg_win_rate = np.mean(win_rates) if win_rates else 0.0
        avg_volatility = np.mean(volatilities) if volatilities else 0.0

        return PerformanceMetrics(
            returns=all_returns,
            sharpe_ratio=avg_sharpe,
            max_drawdown=worst_drawdown,
            win_rate=avg_win_rate,
            volatility=avg_volatility,
            total_trades=total_trades_sum,
        )

    def should_rebalance(self, current_date: datetime) -> bool:
        """Check if rebalancing should occur."""
        if self.last_rebalance_date is None:
            return True

        days_since_rebalance = (current_date - self.last_rebalance_date).days
        return days_since_rebalance >= self.rebalance_frequency_days

    def calculate_new_allocations(
        self,
        current_allocations: Dict[str, Decimal],
        target_allocations: Dict[str, Decimal],
        total_capital: Decimal,
        current_date: datetime,
    ) -> Dict[str, Decimal]:
        """
        Calculate new allocations based on performance.

        Uses composite score to reallocate capital from underperformers
        to outperformers, while respecting min/max constraints.

        Args:
            current_allocations: Current capital allocation per strategy
            target_allocations: Target allocation weights (0-1)
            total_capital: Total portfolio capital
            current_date: Current date

        Returns:
            New capital allocations per strategy
        """
        if not self.should_rebalance(current_date):
            logger.debug("Rebalancing not due yet")
            return current_allocations

        logger.info("🔄 Executing dynamic capital reallocation...")

        # Calculate performance scores for each strategy
        strategy_scores: Dict[str, float] = {}
        strategy_metrics: Dict[str, PerformanceMetrics] = {}

        for strategy_name in target_allocations.keys():
            metrics = self.calculate_rolling_metrics(strategy_name, current_date)

            if metrics is None:
                # No data - use neutral score
                strategy_scores[strategy_name] = 0.0
                logger.warning(
                    f"{strategy_name}: No performance data available, using neutral score"
                )
            elif metrics.total_trades < self.min_trades_threshold:
                # Insufficient activity - penalize
                strategy_scores[strategy_name] = -10.0
                logger.warning(
                    f"{strategy_name}: Insufficient activity ({metrics.total_trades} trades < "
                    f"{self.min_trades_threshold}), penalizing allocation"
                )
            else:
                score = metrics.composite_score
                strategy_scores[strategy_name] = score
                strategy_metrics[strategy_name] = metrics

                logger.info(
                    f"{strategy_name}: Composite score = {score:.2f} "
                    f"(Sharpe={metrics.sharpe_ratio:.2f if metrics.sharpe_ratio else 'N/A'}, "
                    f"Win Rate={metrics.win_rate:.1%}, Trades={metrics.total_trades})"
                )

        # Normalize scores to be non-negative for allocation calculation
        min_score = min(strategy_scores.values())
        normalized_scores = {
            name: max(0.0, score - min_score + 1.0)  # Shift to make all >= 1.0
            for name, score in strategy_scores.items()
        }

        # Calculate target weights based on scores and original targets
        total_normalized = sum(normalized_scores.values())

        if total_normalized == 0:
            logger.warning("All scores are zero or negative, using target allocations")
            new_allocations = {
                name: total_capital * weight for name, weight in target_allocations.items()
            }
        else:
            # Blend performance-based weights with target weights (50/50)
            new_allocations = {}
            for strategy_name in target_allocations.keys():
                target_weight = float(target_allocations[strategy_name])
                performance_weight = normalized_scores[strategy_name] / total_normalized

                # Blend: 50% target, 50% performance
                blended_weight = (target_weight * 0.5) + (performance_weight * 0.5)

                # Apply volatility targeting adjustment
                if strategy_name in strategy_metrics:
                    metrics = strategy_metrics[strategy_name]
                    if metrics.volatility > 0:
                        # Adjust weight inversely to volatility
                        vol_adjustment = self.volatility_target / metrics.volatility
                        blended_weight *= min(1.5, max(0.5, vol_adjustment))  # Cap adjustment

                # Enforce min/max constraints
                blended_weight = max(
                    float(self.min_weight), min(float(self.max_weight), blended_weight)
                )

                new_allocations[strategy_name] = Decimal(str(blended_weight)) * total_capital

        # Normalize to ensure total = total_capital
        allocated_total = sum(new_allocations.values())
        if allocated_total > 0 and allocated_total != total_capital:
            scale_factor = float(total_capital) / float(allocated_total)
            new_allocations = {
                name: Decimal(str(float(cap) * scale_factor))
                for name, cap in new_allocations.items()
            }

        # Log allocation changes
        logger.info("📊 New allocations calculated:")
        for strategy_name in target_allocations.keys():
            old_cap = current_allocations.get(strategy_name, Decimal("0"))
            new_cap = new_allocations[strategy_name]
            old_weight = float(old_cap / total_capital) if total_capital > 0 else 0.0
            new_weight = float(new_cap / total_capital) if total_capital > 0 else 0.0

            change = new_weight - old_weight
            if abs(change) > 0.01:  # Only log significant changes
                logger.info(
                    f"  {strategy_name}: {old_weight:.1%} → {new_weight:.1%} "
                    f"({change:+.1%}, ${float(new_cap):,.2f})"
                )

        self.last_rebalance_date = current_date

        return new_allocations
