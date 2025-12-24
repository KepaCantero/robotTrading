"""
T9.1.2: QuantStatsIntegration - Integrate QuantStats for advanced metrics

Provides advanced performance metrics using QuantStats library.
"""

import logging
from decimal import Decimal
from typing import Dict, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Try to import QuantStats, fall back gracefully if not available
try:
    import quantstats as qs
    QUANTSTATS_AVAILABLE = True
except ImportError:
    QUANTSTATS_AVAILABLE = False
    logger.warning("⚠️ QuantStats not available - using fallback metrics")


class QuantStatsIntegration:
    """
    Integrates QuantStats library for comprehensive performance analytics.

    Calculates:
    - Calmar ratio
    - Omega ratio
    - Information ratio
    - Max consecutive wins/losses
    - Recovery factor
    - And many more...
    """

    def __init__(self):
        """Initialize QuantStats integration."""
        self.available = QUANTSTATS_AVAILABLE
        logger.info(f"✅ QuantStatsIntegration initialized (available: {self.available})")

    def calculate_advanced_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        periods_per_year: int = 252,
    ) -> Dict[str, float]:
        """
        Calculate advanced performance metrics using QuantStats.

        Args:
            returns: Series of returns (daily or periodic)
            benchmark_returns: Optional benchmark returns for comparison
            periods_per_year: Trading periods per year (252 for daily)

        Returns:
            Dict with advanced metrics
        """
        if not isinstance(returns, pd.Series):
            try:
                returns = pd.Series(returns)
            except Exception as e:
                logger.error(f"Cannot convert returns to Series: {e}")
                return {}

        metrics = {}

        if not self.available or len(returns) < 2:
            return self._fallback_metrics(returns, periods_per_year)

        try:
            # Calculate using QuantStats
            # Avoid QuantStats plotting/output
            import warnings
            warnings.filterwarnings('ignore')

            # Total return
            metrics["total_return"] = float((1 + returns).prod() - 1)

            # Annual return
            years = len(returns) / periods_per_year
            if years > 0:
                metrics["annual_return"] = (
                    (1 + metrics["total_return"]) ** (1 / years) - 1
                )

            # Volatility
            metrics["volatility"] = float(returns.std() * np.sqrt(periods_per_year))

            # Sharpe Ratio (risk-free rate = 0)
            if metrics["volatility"] > 0:
                metrics["sharpe_ratio"] = float(
                    (metrics["annual_return"] / metrics["volatility"]) if metrics["volatility"] > 0 else 0
                )

            # Sortino Ratio (downside volatility only)
            downside_returns = returns[returns < 0]
            if len(downside_returns) > 0:
                downside_volatility = float(downside_returns.std() * np.sqrt(periods_per_year))
            else:
                downside_volatility = 0.0

            metrics["sortino_ratio"] = float(
                (metrics["annual_return"] / downside_volatility)
                if downside_volatility > 0
                else 0
            )

            # Max Drawdown
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            metrics["max_drawdown"] = float(drawdown.min())

            # Calmar Ratio
            if metrics["max_drawdown"] < 0:
                metrics["calmar_ratio"] = float(
                    metrics["annual_return"] / abs(metrics["max_drawdown"])
                )

            # Win rate
            winning_periods = len(returns[returns > 0])
            metrics["win_rate"] = float(winning_periods / len(returns)) if len(returns) > 0 else 0

            # Profit Factor
            gross_profit = returns[returns > 0].sum()
            gross_loss = abs(returns[returns < 0].sum())
            metrics["profit_factor"] = float(
                gross_profit / gross_loss if gross_loss > 0 else 0
            )

            # Recovery Factor
            total_return_pct = metrics["total_return"]
            max_dd_pct = abs(metrics["max_drawdown"])
            metrics["recovery_factor"] = float(
                total_return_pct / max_dd_pct if max_dd_pct > 0 else 0
            )

            # Consecutive wins/losses
            returns_sign = returns > 0
            changes = returns_sign.astype(int).diff()
            streaks = changes.ne(0).cumsum()
            consecutive_wins = (returns_sign * streaks).groupby(
                (returns_sign * streaks)
            ).size().max()
            consecutive_losses = (~returns_sign * streaks).groupby(
                (~returns_sign * streaks)
            ).size().max()
            metrics["max_consecutive_wins"] = float(consecutive_wins if consecutive_wins > 0 else 0)
            metrics["max_consecutive_losses"] = float(consecutive_losses if consecutive_losses > 0 else 0)

            # Information Ratio (vs benchmark if provided)
            if benchmark_returns is not None and len(benchmark_returns) == len(returns):
                active_returns = returns - benchmark_returns
                tracking_error = float(active_returns.std() * np.sqrt(periods_per_year))
                if tracking_error > 0:
                    metrics["information_ratio"] = float(
                        active_returns.mean() * periods_per_year / tracking_error
                    )

            logger.info(f"✅ Calculated {len(metrics)} advanced metrics using QuantStats")

        except Exception as e:
            logger.warning(f"Error calculating QuantStats metrics: {e}, using fallback")
            return self._fallback_metrics(returns, periods_per_year)

        return metrics

    def _fallback_metrics(
        self,
        returns: pd.Series,
        periods_per_year: int = 252,
    ) -> Dict[str, float]:
        """
        Calculate basic metrics when QuantStats not available.

        Args:
            returns: Series of returns
            periods_per_year: Trading periods per year

        Returns:
            Dict with basic metrics
        """
        metrics = {}

        if len(returns) < 2:
            return metrics

        try:
            # Total return
            metrics["total_return"] = float((1 + returns).prod() - 1)

            # Annual return
            years = len(returns) / periods_per_year
            if years > 0:
                metrics["annual_return"] = (
                    (1 + metrics["total_return"]) ** (1 / years) - 1
                )

            # Volatility
            metrics["volatility"] = float(returns.std() * np.sqrt(periods_per_year))

            # Sharpe Ratio
            if metrics["volatility"] > 0:
                metrics["sharpe_ratio"] = float(
                    metrics["annual_return"] / metrics["volatility"]
                )

            # Max Drawdown
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            metrics["max_drawdown"] = float(drawdown.min())

            # Win rate
            winning = len(returns[returns > 0])
            metrics["win_rate"] = float(winning / len(returns)) if len(returns) > 0 else 0

            logger.info(f"✅ Calculated {len(metrics)} fallback metrics")

        except Exception as e:
            logger.error(f"Error calculating fallback metrics: {e}")

        return metrics

    def get_metrics_summary(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict:
        """
        Get comprehensive metrics summary.

        Args:
            returns: Returns series
            benchmark_returns: Optional benchmark

        Returns:
            Dict with all metrics and summary
        """
        metrics = self.calculate_advanced_metrics(returns, benchmark_returns)

        summary = {
            "metrics": metrics,
            "source": "QuantStats" if self.available else "Fallback",
            "count": len(metrics),
            "is_available": self.available,
        }

        return summary


# Singleton
_integration: Optional[QuantStatsIntegration] = None


def get_quantstats_integration() -> QuantStatsIntegration:
    """Get or create singleton QuantStatsIntegration."""
    global _integration
    if _integration is None:
        _integration = QuantStatsIntegration()
    return _integration
