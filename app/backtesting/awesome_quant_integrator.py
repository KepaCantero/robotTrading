"""
AWESOME-QUANT Integration Module - Advanced Metrics from quantstats, empyrical, pyfolio

Provides comprehensive financial metrics using AWESOME-QUANT libraries:
- quantstats: Advanced performance analytics
- empyrical: Risk and performance metrics
- pyfolio: Portfolio analysis and tear sheets
"""

import logging
from typing import Dict, Optional, TypedDict

import numpy as np
import pandas as pd

# Trading days constant - Annual trading days (NYSE convention)
TRADING_DAYS = 252  # Number of trading days per year for US equity markets

# Try to import quantstats with fallback
try:
    import quantstats

    QUANTSTATS_AVAILABLE = True
except ImportError:
    quantstats = None
    QUANTSTATS_AVAILABLE = False

# Try to import empyrical with fallback
try:
    import empyrical

    EMPYRICAL_AVAILABLE = True
except ImportError:
    empyrical = None
    EMPYRICAL_AVAILABLE = False

# Try to import pyfolio with fallback
try:
    import pyfolio

    PYFOLIO_AVAILABLE = True
except ImportError:
    pyfolio = None
    PYFOLIO_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================================
# TYPED DICT DEFINITIONS
# ============================================================================


class QuantstatsMetrics(TypedDict):
    """Metrics from quantstats library."""

    return_pct: float
    cagr: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    avg_drawdown: float
    underwater: float
    volatility: float
    var_95: float
    cvar_95: float
    win_rate: float
    best_day: float
    worst_day: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    payoff_ratio: float
    recovery_factor: float
    beta: Optional[float]
    alpha: Optional[float]
    correlation: Optional[float]


class EmpyricalMetrics(TypedDict, total=False):
    """Metrics from empyrical library."""

    total_return: float
    annual_return: float
    cumulative_returns: float
    volatility: float
    downside_volatility: float
    max_drawdown: float
    avg_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    omega_ratio: float
    win_rate: float
    var_95: float
    cvar_95: float
    skewness: float
    kurtosis: float
    alpha: Optional[float]
    beta: Optional[float]
    information_ratio: Optional[float]


class PyfolioMetrics(TypedDict, total=False):
    """Metrics from pyfolio library."""

    total_return: float
    annual_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    avg_drawdown: float
    win_rate: float
    best_return: float
    worst_return: float
    avg_positive_return: float
    avg_negative_return: float
    skewness: float
    kurtosis: float
    var_95: float
    cvar_95: float


class AwesomeQuantMetricsDict(TypedDict, total=False):
    """Container for all AWESOME-QUANT metrics."""

    quantstats: Dict[str, float]
    empyrical: Dict[str, float]
    pyfolio: PyfolioMetrics


class FallbackMetrics(TypedDict, total=False):
    """Fallback metrics when AWESOME-QUANT libraries are unavailable."""

    total_return: float
    annual_return: float
    cumulative_returns: float
    volatility: float
    downside_volatility: float
    max_drawdown: float
    avg_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    omega_ratio: float
    win_rate: float
    var_95: float
    cvar_95: float
    skewness: float
    kurtosis: float
    best_day: Optional[float]
    worst_day: Optional[float]
    avg_win: Optional[float]
    avg_loss: Optional[float]
    profit_factor: Optional[float]
    return_pct: Optional[float]
    beta: Optional[float]
    alpha: Optional[float]
    information_ratio: Optional[float]


# ============================================================================
# AWESOME-QUANT INTEGRATOR
# ============================================================================


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
                "No AWESOME-QUANT libraries available. "
                "Install with: pip install quantstats empyrical-reloaded pyfolio-reloaded"
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
            logger.warning("quantstats not available - using fallback implementation")
            return self._calculate_fallback_metrics(returns, benchmark_returns)

        try:
            # Calculate drawdown series for avg_drawdown and underwater metrics
            dd_series = quantstats.stats.to_drawdown_series(returns)
            avg_drawdown = float(dd_series[dd_series < 0].mean()) if (dd_series < 0).any() else 0.0

            metrics = {
                "return_pct": float(
                    quantstats.stats.comp(returns)
                ),  # Compound return (total return)
                "cagr": float(quantstats.stats.cagr(returns)),
                "sharpe": float(quantstats.stats.sharpe(returns)),
                "sortino": float(quantstats.stats.sortino(returns)),
                "calmar": float(quantstats.stats.calmar(returns)),
                "max_drawdown": float(quantstats.stats.max_drawdown(returns)),
                "avg_drawdown": avg_drawdown,
                "underwater": float(dd_series.min()),
                "volatility": float(quantstats.stats.volatility(returns)),
                "var_95": float(quantstats.stats.value_at_risk(returns, 0.95)),
                "cvar_95": float(quantstats.stats.conditional_value_at_risk(returns, 0.95)),
                "win_rate": float(quantstats.stats.win_rate(returns)),
                "best_day": float(quantstats.stats.best(returns)),
                "worst_day": float(quantstats.stats.worst(returns)),
                "avg_win": float(quantstats.stats.avg_win(returns)),
                "avg_loss": float(quantstats.stats.avg_loss(returns)),
                "profit_factor": float(quantstats.stats.profit_factor(returns)),
                "payoff_ratio": float(quantstats.stats.payoff_ratio(returns)),
                "recovery_factor": float(quantstats.stats.recovery_factor(returns)),
            }

            # Benchmark comparison (if provided)
            if benchmark_returns is not None:
                # Calculate beta and alpha manually (quantstats doesn't have these directly)
                # Align the series
                aligned_data = pd.DataFrame(
                    {"returns": returns, "benchmark": benchmark_returns}
                ).dropna()
                if len(aligned_data) > 1:
                    covariance = aligned_data["returns"].cov(aligned_data["benchmark"])
                    benchmark_var = aligned_data["benchmark"].var()
                    metrics["beta"] = (
                        float(covariance / benchmark_var) if benchmark_var > 0 else 1.0
                    )
                    # Alpha = returns - beta * benchmark_returns (annualized)
                    metrics["alpha"] = float(
                        (
                            aligned_data["returns"].mean()
                            - metrics["beta"] * aligned_data["benchmark"].mean()
                        )
                        * TRADING_DAYS
                    )
                    metrics["correlation"] = float(
                        aligned_data["returns"].corr(aligned_data["benchmark"])
                    )

            logger.info(f"Calculated {len(metrics)} quantstats metrics")
            return metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
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
            logger.warning("empyrical not available - using fallback implementation")
            return self._calculate_fallback_metrics(returns, benchmark_returns)

        try:
            # Handle empty returns
            if len(returns) == 0:
                return self._calculate_fallback_metrics(returns, benchmark_returns)

            metrics = {
                "total_return": float(
                    empyrical.cum_returns_final(returns)
                ),  # Use cum_returns_final for total return
                "annual_return": float(empyrical.annual_return(returns)),
                "cumulative_returns": float(empyrical.cum_returns(returns).iloc[-1]),
                "volatility": float(empyrical.annual_volatility(returns)),
                "downside_volatility": float(empyrical.downside_risk(returns)),
                "max_drawdown": float(empyrical.max_drawdown(returns)),
                "sharpe_ratio": float(empyrical.sharpe_ratio(returns)),
                "sortino_ratio": float(empyrical.sortino_ratio(returns)),
                "calmar_ratio": float(empyrical.calmar_ratio(returns)),
                "omega_ratio": float(empyrical.omega_ratio(returns)),
                "win_rate": float((returns > 0).mean()),
                "var_95": float(empyrical.value_at_risk(returns, 0.95)),
                "cvar_95": float(empyrical.conditional_value_at_risk(returns, 0.95)),
            }

            # Add skew and kurtosis using scipy if available
            try:
                from scipy.stats import kurtosis, skew

                metrics["skewness"] = float(skew(returns.dropna()))
                metrics["kurtosis"] = float(kurtosis(returns.dropna()))
            except ImportError:
                metrics["skewness"] = 0.0
                metrics["kurtosis"] = 0.0

            # Drawdown analysis (calculate manually)
            cumulative = empyrical.cum_returns(returns)
            running_max = cumulative.expanding().max()
            drawdowns = (cumulative - running_max) / running_max
            metrics["avg_drawdown"] = (
                float(drawdowns[drawdowns < 0].mean()) if (drawdowns < 0).any() else 0.0
            )

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

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
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
    ) -> PyfolioMetrics:
        """
        Calculate portfolio metrics using pyfolio.

        Args:
            returns: Series of returns
            positions: Optional DataFrame of positions over time
            transactions: Optional DataFrame of transactions

        Returns:
            Dictionary of pyfolio-derived metrics
        """
        # pyfolio is REQUIRED

        try:
            metrics = {}

            # Basic metrics
            metrics["total_return"] = float((1 + returns).prod() - 1)
            metrics["annual_return"] = float(returns.mean() * TRADING_DAYS)
            metrics["volatility"] = float(returns.std() * np.sqrt(TRADING_DAYS))

            # Sharpe and Sortino
            excess_returns = returns - (self.risk_free_rate / TRADING_DAYS)
            metrics["sharpe_ratio"] = float(
                excess_returns.mean() / excess_returns.std() * np.sqrt(TRADING_DAYS)
            )

            downside = returns[returns < 0]
            downside_std = downside.std() if len(downside) > 0 else returns.std()
            metrics["sortino_ratio"] = float(
                excess_returns.mean() / downside_std * np.sqrt(TRADING_DAYS)
            )

            # Drawdown
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            metrics["max_drawdown"] = float(drawdown.min())
            metrics["avg_drawdown"] = float(drawdown[drawdown < 0].mean())

            # Win/Loss metrics
            metrics["win_rate"] = float((returns > 0).mean())
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
            metrics["var_95"] = float(np.percentile(returns.astype(float), 5))
            metrics["cvar_95"] = float(
                returns[returns <= np.percentile(returns.astype(float), 5)].astype(float).mean()
            )

            logger.info(f"Calculated {len(metrics)} pyfolio metrics")
            return metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
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
    ) -> AwesomeQuantMetricsDict:
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

        # Get metrics from each library in priority order (all REQUIRED)
        unified.update(self.calculate_quantstats_metrics(returns, benchmark_returns))
        empyrical_metrics = self.calculate_empyrical_metrics(returns, benchmark_returns)
        # Only add metrics not already present
        for k, v in empyrical_metrics.items():
            if k not in unified:
                unified[k] = v
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
            True if library is available
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

    def _calculate_fallback_metrics(
        self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None
    ) -> FallbackMetrics:
        """
        Calculate financial metrics using fallback numpy/scipy implementations.

        This provides basic financial metrics when AWESOME-QUANT libraries are not available.

        Args:
            returns: Series of returns
            benchmark_returns: Optional benchmark returns for comparison

        Returns:
            Dictionary of financial metrics
        """
        try:
            metrics = {}

            # Handle empty returns
            if len(returns) == 0:
                return {
                    "total_return": 0.0,
                    "annual_return": 0.0,
                    "cumulative_returns": 0.0,
                    "volatility": 0.0,
                    "downside_volatility": 0.0,
                    "max_drawdown": 0.0,
                    "avg_drawdown": 0.0,
                    "sharpe_ratio": 0.0,
                    "sortino_ratio": 0.0,
                    "calmar_ratio": 0.0,
                    "omega_ratio": 0.0,
                }

            # Basic return metrics
            metrics["total_return"] = float((1 + returns).prod() - 1)
            metrics["annual_return"] = float(returns.mean() * TRADING_DAYS)
            metrics["cumulative_returns"] = float((1 + returns).cumprod().iloc[-1] - 1)

            # Volatility metrics
            metrics["volatility"] = float(returns.std() * np.sqrt(TRADING_DAYS))

            # Downside volatility
            negative_returns = returns[returns < 0]
            if len(negative_returns) > 0:
                metrics["downside_volatility"] = float(
                    negative_returns.std() * np.sqrt(TRADING_DAYS)
                )
            else:
                metrics["downside_volatility"] = 0.0

            # Drawdown metrics
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            metrics["max_drawdown"] = float(drawdown.min())
            metrics["avg_drawdown"] = (
                float(drawdown[drawdown < 0].mean()) if (drawdown < 0).any() else 0.0
            )

            # Sharpe and Sortino ratios
            excess_returns = returns - (self.risk_free_rate / TRADING_DAYS)
            annual_excess_return = excess_returns.mean() * TRADING_DAYS
            annual_volatility = returns.std() * np.sqrt(TRADING_DAYS)

            if annual_volatility > 0:
                metrics["sharpe_ratio"] = float(annual_excess_return / annual_volatility)
            else:
                metrics["sharpe_ratio"] = 0.0

            # Sortino ratio (using downside deviation)
            if len(negative_returns) > 0:
                downside_std = negative_returns.std() * np.sqrt(TRADING_DAYS)
                if downside_std > 0:
                    metrics["sortino_ratio"] = float(annual_excess_return / downside_std)
                else:
                    metrics["sortino_ratio"] = 0.0
            else:
                metrics["sortino_ratio"] = 0.0

            # Calmar ratio (CAGR / Max Drawdown)
            cagr = metrics["annual_return"]
            max_dd = abs(metrics["max_drawdown"])
            if max_dd > 0:
                metrics["calmar_ratio"] = float(cagr / max_dd)
            else:
                metrics["calmar_ratio"] = 0.0

            # Omega ratio (simplified version)
            threshold = self.risk_free_rate / TRADING_DAYS
            gains = returns[returns > threshold] - threshold
            losses = threshold - returns[returns <= threshold]
            if losses.sum() > 0:
                metrics["omega_ratio"] = float(gains.sum() / losses.sum())
            else:
                metrics["omega_ratio"] = float('inf') if gains.sum() > 0 else 0.0

            # Win rate
            metrics["win_rate"] = (
                float((returns > 0).mean()) if len(returns) > 0 else 0.0
            )

            # Value at Risk metrics
            metrics["var_95"] = float(np.percentile(returns.astype(float), 5))
            metrics["cvar_95"] = float(
                returns[returns <= np.percentile(returns.astype(float), 5)].astype(float).mean()
            )

            # Skewness and Kurtosis
            metrics["skewness"] = float(returns.skew())
            metrics["kurtosis"] = float(returns.kurtosis())

            # Additional metrics
            if len(returns) > 0:
                metrics["best_day"] = float(returns.max())
                metrics["worst_day"] = float(returns.min())

                positive_returns = returns[returns > 0]
                negative_returns = returns[returns < 0]

                metrics["avg_win"] = (
                    float(positive_returns.mean()) if len(positive_returns) > 0 else 0.0
                )
                metrics["avg_loss"] = (
                    float(negative_returns.mean()) if len(negative_returns) > 0 else 0.0
                )

                # Profit factor
                gross_profit = positive_returns.sum() if len(positive_returns) > 0 else 0.0
                gross_loss = abs(negative_returns.sum()) if len(negative_returns) > 0 else 1.0
                metrics["profit_factor"] = (
                    float(gross_profit / gross_loss) if gross_loss > 0 else 0.0
                )

                metrics["return_pct"] = metrics["total_return"]

            # Benchmark comparison (if provided)
            if benchmark_returns is not None and len(benchmark_returns) == len(returns):
                # Alpha and Beta (simplified calculation)
                covariance = np.cov(returns.astype(float), benchmark_returns.astype(float))[0, 1]
                benchmark_variance = np.var(benchmark_returns.astype(float))

                if benchmark_variance > 0:
                    metrics["beta"] = float(covariance / benchmark_variance)
                    # Alpha = Annual Return - (Beta * Benchmark Annual Return + Risk Free)
                    benchmark_annual_return = benchmark_returns.mean() * TRADING_DAYS
                    metrics["alpha"] = float(
                        metrics["annual_return"]
                        - (metrics["beta"] * benchmark_annual_return + self.risk_free_rate)
                    )
                else:
                    metrics["beta"] = 1.0
                    metrics["alpha"] = metrics["annual_return"] - self.risk_free_rate

                # Information ratio
                excess_returns = returns - benchmark_returns
                if excess_returns.std() > 0:
                    metrics["information_ratio"] = float(
                        (excess_returns.mean() * TRADING_DAYS)
                        / (excess_returns.std() * np.sqrt(TRADING_DAYS))
                    )
                else:
                    metrics["information_ratio"] = 0.0

            logger.info(f"Calculated {len(metrics)} fallback metrics")
            return metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating fallback metrics: {e}", exc_info=True)
            return {}
