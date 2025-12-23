"""
AWESOME-QUANT Integration Module - Advanced Metrics from quantstats, empyrical, pyfolio

Provides comprehensive financial metrics using AWESOME-QUANT libraries:
- quantstats: Advanced performance analytics
- empyrical: Risk and performance metrics
- pyfolio: Portfolio analysis and tear sheets
"""

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Optional library imports with graceful fallback
QUANTSTATS_AVAILABLE = False
EMPYRICAL_AVAILABLE = False
PYFOLIO_AVAILABLE = False

try:
    import quantstats as qs

    QUANTSTATS_AVAILABLE = True
    logger.info("quantstats library available")
except ImportError:
    logger.debug("quantstats not available - some features will be disabled")

try:
    import empyrical

    EMPYRICAL_AVAILABLE = True
    logger.info("empyrical library available")
except ImportError:
    logger.debug("empyrical not available - some features will be disabled")

try:
    import pyfolio

    PYFOLIO_AVAILABLE = True
    logger.info("pyfolio library available")
except ImportError:
    logger.debug("pyfolio not available - some features will be disabled")


class AwesomeQuantIntegrator:
    """Integrate AWESOME-QUANT libraries for advanced metrics and analysis."""

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize AWESOME-QUANT integrator.

        Args:
            risk_free_rate: Risk-free rate for calculations (default: 2%)
        """
        self.risk_free_rate = risk_free_rate
        self._check_availability()

    def _check_availability(self) -> None:
        """Log which AWESOME-QUANT libraries are available."""
        available = []
        if QUANTSTATS_AVAILABLE:
            available.append("quantstats")
        if EMPYRICAL_AVAILABLE:
            available.append("empyrical")
        if PYFOLIO_AVAILABLE:
            available.append("pyfolio")

        if available:
            logger.info(f"AWESOME-QUANT libraries available: {', '.join(available)}")
        else:
            logger.warning(
                "No AWESOME-QUANT libraries available. Install quantstats, "
                "empyrical-reloaded, or pyfolio-reloaded for advanced metrics."
            )

    # =========================================================================
    # QUANTSTATS METRICS
    # =========================================================================

    def calculate_quantstats_metrics(
        self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None
    ) -> Dict[str, float]:
        """
        Calculate comprehensive metrics using quantstats.

        Args:
            returns: Series of returns
            benchmark_returns: Optional benchmark returns for comparison

        Returns:
            Dictionary of quantstats-derived metrics
        """
        if not QUANTSTATS_AVAILABLE:
            logger.warning("quantstats not available")
            return {}

        try:
            metrics = {}

            # Basic stats
            metrics["return_pct"] = float(qs.stats.total_return(returns))
            metrics["cagr"] = float(qs.stats.cagr(returns))
            metrics["sharpe"] = float(qs.stats.sharpe(returns))
            metrics["sortino"] = float(qs.stats.sortino(returns))
            metrics["calmar"] = float(qs.stats.calmar(returns))

            # Drawdown metrics
            metrics["max_drawdown"] = float(qs.stats.max_drawdown(returns))
            metrics["avg_drawdown"] = float(qs.stats.avg_drawdown(returns))
            metrics["underwater"] = float(qs.stats.underwater(returns).min())

            # Volatility and risk
            metrics["volatility"] = float(qs.stats.volatility(returns))
            metrics["var_95"] = float(qs.stats.value_at_risk(returns, 0.95))
            metrics["cvar_95"] = float(qs.stats.conditional_value_at_risk(returns, 0.95))

            # Win metrics
            metrics["win_rate"] = float(qs.stats.win_rate(returns))
            metrics["best_day"] = float(qs.stats.best(returns))
            metrics["worst_day"] = float(qs.stats.worst(returns))
            metrics["avg_win"] = float(qs.stats.avg_win(returns))
            metrics["avg_loss"] = float(qs.stats.avg_loss(returns))

            # Other metrics
            metrics["profit_factor"] = float(qs.stats.profit_factor(returns))
            metrics["payoff_ratio"] = float(qs.stats.payoff_ratio(returns))
            metrics["recovery_factor"] = float(qs.stats.recovery_factor(returns))

            # Benchmark comparison (if provided)
            if benchmark_returns is not None:
                metrics["beta"] = float(qs.stats.beta(returns, benchmark_returns))
                metrics["alpha"] = float(qs.stats.alpha(returns, benchmark_returns))
                metrics["correlation"] = float(
                    qs.stats.correlation(returns, benchmark_returns)
                )

            logger.info(f"Calculated {len(metrics)} quantstats metrics")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating quantstats metrics: {e}", exc_info=True)
            return {}

    # =========================================================================
    # EMPYRICAL METRICS
    # =========================================================================

    def calculate_empyrical_metrics(
        self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None
    ) -> Dict[str, float]:
        """
        Calculate metrics using empyrical library.

        Args:
            returns: Series of returns
            benchmark_returns: Optional benchmark for comparison

        Returns:
            Dictionary of empyrical-derived metrics
        """
        if not EMPYRICAL_AVAILABLE:
            logger.warning("empyrical not available")
            return {}

        try:
            metrics = {}

            # Return metrics
            metrics["total_return"] = float(empyrical.total_return(returns))
            metrics["annual_return"] = float(empyrical.annual_return(returns))
            metrics["cumulative_returns"] = float(empyrical.cum_returns(returns).iloc[-1])

            # Risk metrics
            metrics["volatility"] = float(empyrical.annual_volatility(returns))
            metrics["downside_volatility"] = float(empyrical.downside_volatility(returns))
            metrics["max_drawdown"] = float(empyrical.max_drawdown(returns))

            # Risk-adjusted metrics
            metrics["sharpe_ratio"] = float(empyrical.sharpe_ratio(returns))
            metrics["sortino_ratio"] = float(empyrical.sortino_ratio(returns))
            metrics["calmar_ratio"] = float(empyrical.calmar_ratio(returns))
            metrics["omega_ratio"] = float(empyrical.omega_ratio(returns))

            # Win metrics
            metrics["win_rate"] = float(
                (returns > 0).sum() / len(returns) if len(returns) > 0 else 0
            )

            # Tail metrics
            metrics["var_95"] = float(np.percentile(returns, 5))
            metrics["cvar_95"] = float(returns[returns <= np.percentile(returns, 5)].mean())
            metrics["skewness"] = float(empyrical.skewness(returns))
            metrics["kurtosis"] = float(empyrical.kurtosis(returns))

            # Drawdown analysis
            drawdowns = empyrical.drawdown(returns)
            metrics["avg_drawdown"] = float(drawdowns[drawdowns < 0].mean())

            # Benchmark metrics (if provided)
            if benchmark_returns is not None and len(benchmark_returns) == len(returns):
                metrics["alpha"] = float(empyrical.alpha(returns, benchmark_returns))
                metrics["beta"] = float(empyrical.beta(returns, benchmark_returns))
                excess_returns = returns - benchmark_returns
                metrics["information_ratio"] = float(
                    empyrical.annual_return(excess_returns)
                    / empyrical.annual_volatility(excess_returns)
                )

            logger.info(f"Calculated {len(metrics)} empyrical metrics")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating empyrical metrics: {e}", exc_info=True)
            return {}

    # =========================================================================
    # PYFOLIO METRICS
    # =========================================================================

    def calculate_pyfolio_metrics(
        self,
        returns: pd.Series,
        positions: Optional[pd.DataFrame] = None,
        transactions: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Calculate portfolio metrics using pyfolio.

        Args:
            returns: Series of returns
            positions: Optional DataFrame of positions over time
            transactions: Optional DataFrame of transactions

        Returns:
            Dictionary of pyfolio-derived metrics
        """
        if not PYFOLIO_AVAILABLE:
            logger.warning("pyfolio not available")
            return {}

        try:
            metrics = {}

            # Basic metrics
            metrics["total_return"] = float((1 + returns).prod() - 1)
            metrics["annual_return"] = float(returns.mean() * 252)
            metrics["volatility"] = float(returns.std() * np.sqrt(252))

            # Sharpe and Sortino
            excess_returns = returns - (self.risk_free_rate / 252)
            metrics["sharpe_ratio"] = float(
                excess_returns.mean() / excess_returns.std() * np.sqrt(252)
            )

            downside = returns[returns < 0]
            downside_std = downside.std() if len(downside) > 0 else returns.std()
            metrics["sortino_ratio"] = float(
                excess_returns.mean() / downside_std * np.sqrt(252)
            )

            # Drawdown
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            metrics["max_drawdown"] = float(drawdown.min())
            metrics["avg_drawdown"] = float(drawdown[drawdown < 0].mean())

            # Win/Loss metrics
            metrics["win_rate"] = float((returns > 0).sum() / len(returns))
            metrics["best_return"] = float(returns.max())
            metrics["worst_return"] = float(returns.min())
            metrics["avg_positive_return"] = float(
                returns[returns > 0].mean() if (returns > 0).any() else 0
            )
            metrics["avg_negative_return"] = float(
                returns[returns < 0].mean() if (returns < 0).any() else 0
            )

            # Risk metrics
            metrics["skewness"] = float(returns.skew())
            metrics["kurtosis"] = float(returns.kurtosis())
            metrics["var_95"] = float(np.percentile(returns, 5))
            metrics["cvar_95"] = float(
                returns[returns <= np.percentile(returns, 5)].mean()
            )

            logger.info(f"Calculated {len(metrics)} pyfolio metrics")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating pyfolio metrics: {e}", exc_info=True)
            return {}

    # =========================================================================
    # COMBINED METRICS
    # =========================================================================

    def calculate_all_awesome_quant_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        positions: Optional[pd.DataFrame] = None,
        transactions: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate all available AWESOME-QUANT metrics.

        Args:
            returns: Series of returns
            benchmark_returns: Optional benchmark returns
            positions: Optional positions DataFrame
            transactions: Optional transactions DataFrame

        Returns:
            Dictionary with metrics from all available libraries
        """
        all_metrics = {
            "quantstats": self.calculate_quantstats_metrics(returns, benchmark_returns),
            "empyrical": self.calculate_empyrical_metrics(returns, benchmark_returns),
            "pyfolio": self.calculate_pyfolio_metrics(returns, positions, transactions),
        }

        # Log aggregated results
        total_metrics = sum(len(m) for m in all_metrics.values())
        logger.info(f"Calculated total of {total_metrics} metrics from AWESOME-QUANT")

        return all_metrics

    def get_unified_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict[str, float]:
        """
        Get unified view of key metrics across all libraries.

        Consolidates metrics from all available AWESOME-QUANT libraries,
        preferring library order: quantstats > empyrical > pyfolio

        Args:
            returns: Series of returns
            benchmark_returns: Optional benchmark returns

        Returns:
            Unified dictionary of key metrics
        """
        unified = {}

        # Try to get metrics from each library in priority order
        if QUANTSTATS_AVAILABLE:
            unified.update(self.calculate_quantstats_metrics(returns, benchmark_returns))
        if EMPYRICAL_AVAILABLE:
            empyrical_metrics = self.calculate_empyrical_metrics(
                returns, benchmark_returns
            )
            # Only add metrics not already present
            for k, v in empyrical_metrics.items():
                if k not in unified:
                    unified[k] = v
        if PYFOLIO_AVAILABLE:
            pyfolio_metrics = self.calculate_pyfolio_metrics(returns)
            for k, v in pyfolio_metrics.items():
                if k not in unified:
                    unified[k] = v

        logger.info(f"Generated unified metrics with {len(unified)} total items")
        return unified

    def is_available(self, library: str) -> bool:
        """
        Check if AWESOME-QUANT library is available.

        Args:
            library: Library name ("quantstats", "empyrical", or "pyfolio")

        Returns:
            True if library is available, False otherwise
        """
        if library == "quantstats":
            return QUANTSTATS_AVAILABLE
        elif library == "empyrical":
            return EMPYRICAL_AVAILABLE
        elif library == "pyfolio":
            return PYFOLIO_AVAILABLE
        return False

    def get_available_libraries(self) -> list:
        """Get list of available AWESOME-QUANT libraries."""
        available = []
        if QUANTSTATS_AVAILABLE:
            available.append("quantstats")
        if EMPYRICAL_AVAILABLE:
            available.append("empyrical")
        if PYFOLIO_AVAILABLE:
            available.append("pyfolio")
        return available
