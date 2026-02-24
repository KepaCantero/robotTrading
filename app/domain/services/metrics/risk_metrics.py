"""
Risk Metrics Calculator

Centralized implementation of risk metrics, consolidating:
- Value at Risk (VaR) - from advanced_metrics.py, risk_calculator.py, numba_metrics.py
- Conditional VaR (CVaR) - from advanced_metrics.py, numba_metrics.py
- Volatility - from advanced_metrics.py, risk_calculator.py, numba_metrics.py
- Beta - from risk_calculator.py
- Correlation - from various sources
- Tracking Error - from chan_metrics.py
- Information Ratio - from chan_metrics.py, numba_metrics.py

Reference:
    - Lopez de Prado, M. (2020). Machine Learning for Asset Managers.
    - Chan, E.P. (2013). Algorithmic Trading.
    - Jorion, P. (2006). Value at Risk.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CONFIDENCE_LEVEL = 0.95


def _to_array(returns: Union[pd.Series, np.ndarray, List[float]]) -> np.ndarray:
    """Convert returns to numpy array, handling various input types."""
    if isinstance(returns, pd.Series):
        arr = returns.values.astype(np.float64)
    elif isinstance(returns, list):
        arr = np.array(returns, dtype=np.float64)
    else:
        arr = np.asarray(returns, dtype=np.float64)
    return arr[~np.isnan(arr)]


@dataclass
class VaRResult:
    """Value at Risk calculation result."""

    var_historical: float  # Historical VaR
    var_parametric: Optional[float] = None  # Parametric VaR (normal assumption)
    var_cornish_fisher: Optional[float] = None  # Cornish-Fisher adjusted VaR
    confidence_level: float = 0.95
    method_used: str = "historical"


@dataclass
class RiskMetricsResult:
    """Complete risk metrics result."""

    # VaR metrics
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float

    # Volatility metrics
    daily_volatility: float
    annualized_volatility: float

    # Distribution metrics
    skewness: Optional[float]
    kurtosis: Optional[float]

    # Beta and correlation (if benchmark provided)
    beta: Optional[float]
    correlation: Optional[float]


class RiskMetricsCalculator:
    """
    Unified risk metrics calculator.

    This class consolidates all risk metric calculations from:
    - app/backtesting/advanced_metrics.py (VaR, CVaR, volatility)
    - app/domain/services/risk_calculator.py (VaR, beta, volatility)
    - app/backtesting/numba_metrics.py (VaR, CVaR, volatility - accelerated)
    - app/backtesting/chan_metrics.py (tracking error, information ratio)

    Supports multiple VaR calculation methods:
    1. Historical simulation (non-parametric)
    2. Parametric (normal distribution assumption)
    3. Cornish-Fisher (adjusted for skewness/kurtosis)
    """

    def __init__(
        self,
        confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
        trading_days: int = None,
    ):
        """
        Initialize risk metrics calculator.

        Args:
            confidence_level: Default confidence level for VaR (default: 95%)
            trading_days: Number of trading days per year (default: from CentralizedConfig)
        """
        self.confidence_level = confidence_level
        self.trading_days = trading_days if trading_days is not None else get_config().backtesting.annual_trading_days

    # =========================================================================
    # VALUE AT RISK (VaR)
    # =========================================================================

    def var(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
        confidence: Optional[float] = None,
        method: str = "historical",
    ) -> float:
        """
        Calculate Value at Risk.

        Consolidated from:
        - advanced_metrics.py:calculate_var
        - risk_calculator.py:_calculate_var
        - numba_metrics.py:calculate_var_numba

        Methods:
        - 'historical': Uses percentile of returns distribution (default)
        - 'parametric': Assumes normal distribution
        - 'cornish_fisher': Adjusts for skewness and kurtosis

        Args:
            returns: Return series
            confidence: Confidence level (default: self.confidence_level)
            method: Calculation method

        Returns:
            VaR value (negative, representing potential loss)

        Example:
            >>> calc = RiskMetricsCalculator()
            >>> returns = pd.Series([0.01, -0.02, 0.015, -0.03, 0.005])
            >>> var_95 = calc.var(returns, confidence=0.95)
            >>> print(f"95% VaR: {var_95:.2%}")  # e.g., "95% VaR: -2.50%"
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return 0.0

        conf = confidence if confidence is not None else self.confidence_level

        if method == "historical":
            return self._var_historical(returns_array, conf)
        elif method == "parametric":
            return self._var_parametric(returns_array, conf)
        elif method == "cornish_fisher":
            return self._var_cornish_fisher(returns_array, conf)
        else:
            logger.warning(f"Unknown VaR method: {method}, using historical")
            return self._var_historical(returns_array, conf)

    def _var_historical(self, returns: np.ndarray, confidence: float) -> float:
        """Historical VaR using percentile."""
        percentile = (1 - confidence) * 100
        return float(np.percentile(returns, percentile))

    def _var_parametric(self, returns: np.ndarray, confidence: float) -> float:
        """Parametric VaR assuming normal distribution."""
        try:
            from scipy import stats

            mean = np.mean(returns)
            std = np.std(returns, ddof=1)
            z_score = stats.norm.ppf(1 - confidence)
            return float(mean + z_score * std)
        except ImportError:
            # Approximate z-scores for common confidence levels
            z_scores = {0.90: -1.28, 0.95: -1.65, 0.99: -2.33}
            z = z_scores.get(confidence, -1.65)
            return float(np.mean(returns) + z * np.std(returns, ddof=1))

    def _var_cornish_fisher(self, returns: np.ndarray, confidence: float) -> float:
        """
        Cornish-Fisher VaR adjusted for skewness and kurtosis.

        More accurate for non-normal distributions.
        """
        try:
            from scipy import stats

            mean = np.mean(returns)
            std = np.std(returns, ddof=1)
            skew = stats.skew(returns)
            kurt = stats.kurtosis(returns)  # Excess kurtosis

            # Cornish-Fisher expansion
            z = stats.norm.ppf(1 - confidence)
            z_cf = (
                z
                + (z**2 - 1) * skew / 6
                + (z**3 - 3 * z) * kurt / 24
                - (2 * z**3 - 5 * z) * skew**2 / 36
            )

            return float(mean + z_cf * std)
        except ImportError:
            return self._var_historical(returns, confidence)

    def var_comprehensive(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
        confidence: Optional[float] = None,
    ) -> VaRResult:
        """
        Calculate VaR using multiple methods.

        Args:
            returns: Return series
            confidence: Confidence level

        Returns:
            VaRResult with all VaR calculations
        """
        returns_array = _to_array(returns)
        conf = confidence if confidence is not None else self.confidence_level

        if len(returns_array) < 2:
            return VaRResult(
                var_historical=0.0,
                confidence_level=conf,
                method_used="none",
            )

        var_hist = self._var_historical(returns_array, conf)
        var_param = self._var_parametric(returns_array, conf)
        var_cf = self._var_cornish_fisher(returns_array, conf)

        return VaRResult(
            var_historical=var_hist,
            var_parametric=var_param,
            var_cornish_fisher=var_cf,
            confidence_level=conf,
            method_used="historical",
        )

    # =========================================================================
    # CONDITIONAL VaR (CVaR / EXPECTED SHORTFALL)
    # =========================================================================

    def cvar(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
        confidence: Optional[float] = None,
    ) -> float:
        """
        Calculate Conditional Value at Risk (Expected Shortfall).

        Consolidated from:
        - advanced_metrics.py:calculate_cvar
        - numba_metrics.py:calculate_cvar_numba

        CVaR is the expected loss given that the loss exceeds VaR.
        More conservative than VaR as it considers tail behavior.

        Args:
            returns: Return series
            confidence: Confidence level (default: self.confidence_level)

        Returns:
            CVaR value (negative, representing expected tail loss)
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return 0.0

        conf = confidence if confidence is not None else self.confidence_level

        # Calculate VaR threshold
        var_threshold = self._var_historical(returns_array, conf)

        # Get returns below VaR threshold
        tail_returns = returns_array[returns_array <= var_threshold]

        if len(tail_returns) == 0:
            return var_threshold

        return float(np.mean(tail_returns))

    # =========================================================================
    # VOLATILITY
    # =========================================================================

    def volatility(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
        annualize: bool = True,
        method: str = "simple",
        window: Optional[int] = None,
    ) -> float:
        """
        Calculate volatility.

        Consolidated from:
        - advanced_metrics.py:calculate_annualized_volatility
        - risk_calculator.py:_estimate_portfolio_volatility
        - numba_metrics.py:calculate_volatility_numba

        Methods:
        - 'simple': Standard deviation (default)
        - 'parkinson': Uses high-low ranges (requires OHLC data)
        - 'garman_klass': Uses OHLC data for more accuracy

        Args:
            returns: Return series
            annualize: Whether to annualize
            method: Calculation method
            window: Rolling window (if None, uses full series)

        Returns:
            Volatility (annualized if annualize=True)
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return 0.0

        if method != "simple":
            logger.warning(f"Volatility method '{method}' not implemented, using simple")

        # Calculate standard deviation
        if window is not None and len(returns_array) >= window:
            # Rolling volatility (use last window)
            std = np.std(returns_array[-window:], ddof=1)
        else:
            std = np.std(returns_array, ddof=1)

        if annualize:
            return float(std * np.sqrt(self.trading_days))

        return float(std)

    def rolling_volatility(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
        window: int = 21,
        annualize: bool = True,
    ) -> np.ndarray:
        """
        Calculate rolling volatility.

        From numba_metrics.py:calculate_rolling_volatility_numba

        Args:
            returns: Return series
            window: Rolling window size
            annualize: Whether to annualize

        Returns:
            Array of rolling volatility values (NaN for initial periods)
        """
        returns_array = _to_array(returns)
        n = len(returns_array)

        if n < window:
            return np.full(n, np.nan)

        rolling_vol = np.full(n, np.nan)

        for i in range(window - 1, n):
            window_returns = returns_array[i - window + 1 : i + 1]
            std = np.std(window_returns, ddof=1)
            if annualize:
                std *= np.sqrt(self.trading_days)
            rolling_vol[i] = std

        return rolling_vol

    # =========================================================================
    # BETA
    # =========================================================================

    def beta(
        self,
        asset_returns: Union[pd.Series, np.ndarray, List[float]],
        market_returns: Union[pd.Series, np.ndarray, List[float]],
    ) -> float:
        """
        Calculate beta (asset sensitivity to market).

        From risk_calculator.py:RiskCalculator.calculate_beta

        Beta = Cov(R_asset, R_market) / Var(R_market)

        Args:
            asset_returns: Asset/strategy returns
            market_returns: Market/benchmark returns

        Returns:
            Beta value (1.0 = same as market, >1 = more volatile, <1 = less volatile)
        """
        asset_array = _to_array(asset_returns)
        market_array = _to_array(market_returns)

        # Align lengths
        min_len = min(len(asset_array), len(market_array))
        if min_len < 2:
            return 1.0

        asset_array = asset_array[:min_len]
        market_array = market_array[:min_len]

        # Calculate covariance and variance
        covariance = np.cov(asset_array, market_array, ddof=1)[0, 1]
        market_variance = np.var(market_array, ddof=1)

        if market_variance < 1e-10:
            return 1.0

        return float(covariance / market_variance)

    # =========================================================================
    # CORRELATION
    # =========================================================================

    def correlation(
        self,
        returns1: Union[pd.Series, np.ndarray, List[float]],
        returns2: Union[pd.Series, np.ndarray, List[float]],
    ) -> float:
        """
        Calculate correlation between two return series.

        Args:
            returns1: First return series
            returns2: Second return series

        Returns:
            Correlation coefficient (-1 to 1)
        """
        arr1 = _to_array(returns1)
        arr2 = _to_array(returns2)

        min_len = min(len(arr1), len(arr2))
        if min_len < 2:
            return 0.0

        arr1 = arr1[:min_len]
        arr2 = arr2[:min_len]

        corr_matrix = np.corrcoef(arr1, arr2)
        return float(corr_matrix[0, 1]) if not np.isnan(corr_matrix[0, 1]) else 0.0

    def correlation_matrix(
        self,
        returns_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix for multiple assets.

        Args:
            returns_df: DataFrame where columns are assets and rows are returns

        Returns:
            Correlation matrix as DataFrame
        """
        return returns_df.corr()

    # =========================================================================
    # TRACKING ERROR
    # =========================================================================

    def tracking_error(
        self,
        portfolio_returns: Union[pd.Series, np.ndarray, List[float]],
        benchmark_returns: Union[pd.Series, np.ndarray, List[float]],
        annualize: bool = True,
    ) -> float:
        """
        Calculate tracking error.

        From chan_metrics.py:ChanStrategyComparator._calculate_tracking_error

        Tracking Error = std(portfolio - benchmark) * sqrt(252) if annualized

        Args:
            portfolio_returns: Portfolio/strategy returns
            benchmark_returns: Benchmark returns
            annualize: Whether to annualize

        Returns:
            Tracking error
        """
        port_array = _to_array(portfolio_returns)
        bench_array = _to_array(benchmark_returns)

        min_len = min(len(port_array), len(bench_array))
        if min_len < 2:
            return 0.0

        port_array = port_array[:min_len]
        bench_array = bench_array[:min_len]

        # Active returns
        active_returns = port_array - bench_array

        # Tracking error
        te = np.std(active_returns, ddof=1)

        if annualize:
            te *= np.sqrt(self.trading_days)

        return float(te)

    # =========================================================================
    # INFORMATION RATIO
    # =========================================================================

    def information_ratio(
        self,
        portfolio_returns: Union[pd.Series, np.ndarray, List[float]],
        benchmark_returns: Union[pd.Series, np.ndarray, List[float]],
        annualize: bool = True,
    ) -> float:
        """
        Calculate information ratio.

        From chan_metrics.py:ChanStrategyComparator._calculate_information_ratio
        From numba_metrics.py:calculate_information_ratio_numba

        IR = (portfolio_return - benchmark_return) / tracking_error

        Args:
            portfolio_returns: Portfolio/strategy returns
            benchmark_returns: Benchmark returns
            annualize: Whether to annualize

        Returns:
            Information ratio
        """
        port_array = _to_array(portfolio_returns)
        bench_array = _to_array(benchmark_returns)

        min_len = min(len(port_array), len(bench_array))
        if min_len < 2:
            return 0.0

        port_array = port_array[:min_len]
        bench_array = bench_array[:min_len]

        # Active returns
        active_returns = port_array - bench_array

        mean_active = np.mean(active_returns)
        std_active = np.std(active_returns, ddof=1)

        if std_active < 1e-10:
            return 0.0

        ir = mean_active / std_active

        if annualize:
            ir *= np.sqrt(self.trading_days)

        return float(ir)

    # =========================================================================
    # UPSIDE / DOWNSIDE CAPTURE
    # =========================================================================

    def upside_capture(
        self,
        portfolio_returns: Union[pd.Series, np.ndarray, List[float]],
        benchmark_returns: Union[pd.Series, np.ndarray, List[float]],
    ) -> float:
        """
        Calculate upside capture ratio.

        Measures how much of the benchmark's upside the portfolio captures.
        >100% = outperforms in up markets

        Args:
            portfolio_returns: Portfolio returns
            benchmark_returns: Benchmark returns

        Returns:
            Upside capture ratio
        """
        port_array = _to_array(portfolio_returns)
        bench_array = _to_array(benchmark_returns)

        min_len = min(len(port_array), len(bench_array))
        if min_len < 2:
            return 0.0

        port_array = port_array[:min_len]
        bench_array = bench_array[:min_len]

        # Up periods
        up_mask = bench_array > 0

        if not np.any(up_mask):
            return 0.0

        port_up_mean = np.mean(port_array[up_mask])
        bench_up_mean = np.mean(bench_array[up_mask])

        if abs(bench_up_mean) < 1e-10:
            return 0.0

        return float(port_up_mean / bench_up_mean)

    def downside_capture(
        self,
        portfolio_returns: Union[pd.Series, np.ndarray, List[float]],
        benchmark_returns: Union[pd.Series, np.ndarray, List[float]],
    ) -> float:
        """
        Calculate downside capture ratio.

        Measures how much of the benchmark's downside the portfolio captures.
        <100% = outperforms in down markets

        Args:
            portfolio_returns: Portfolio returns
            benchmark_returns: Benchmark returns

        Returns:
            Downside capture ratio
        """
        port_array = _to_array(portfolio_returns)
        bench_array = _to_array(benchmark_returns)

        min_len = min(len(port_array), len(bench_array))
        if min_len < 2:
            return 0.0

        port_array = port_array[:min_len]
        bench_array = bench_array[:min_len]

        # Down periods
        down_mask = bench_array < 0

        if not np.any(down_mask):
            return 0.0

        port_down_mean = np.mean(port_array[down_mask])
        bench_down_mean = np.mean(bench_array[down_mask])

        if abs(bench_down_mean) < 1e-10:
            return 0.0

        return float(port_down_mean / bench_down_mean)

    # =========================================================================
    # COMPREHENSIVE CALCULATION
    # =========================================================================

    def calculate_all(
        self,
        returns: Union[pd.Series, np.ndarray, List[float]],
        benchmark_returns: Optional[Union[pd.Series, np.ndarray, List[float]]] = None,
    ) -> RiskMetricsResult:
        """
        Calculate all risk metrics at once.

        Args:
            returns: Return series
            benchmark_returns: Optional benchmark returns

        Returns:
            RiskMetricsResult with all metrics
        """
        returns_array = _to_array(returns)

        if len(returns_array) < 2:
            return RiskMetricsResult(
                var_95=0.0,
                var_99=0.0,
                cvar_95=0.0,
                cvar_99=0.0,
                daily_volatility=0.0,
                annualized_volatility=0.0,
                skewness=None,
                kurtosis=None,
                beta=None,
                correlation=None,
            )

        # VaR metrics
        var_95 = self.var(returns_array, 0.95)
        var_99 = self.var(returns_array, 0.99)
        cvar_95 = self.cvar(returns_array, 0.95)
        cvar_99 = self.cvar(returns_array, 0.99)

        # Volatility
        daily_vol = self.volatility(returns_array, annualize=False)
        annual_vol = self.volatility(returns_array, annualize=True)

        # Distribution
        skewness = self._calculate_skewness(returns_array)
        kurtosis = self._calculate_kurtosis(returns_array)

        # Benchmark-related metrics
        beta_val = None
        corr_val = None

        if benchmark_returns is not None:
            bench_array = _to_array(benchmark_returns)
            if len(bench_array) >= 2:
                beta_val = self.beta(returns_array, bench_array)
                corr_val = self.correlation(returns_array, bench_array)

        return RiskMetricsResult(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            daily_volatility=daily_vol,
            annualized_volatility=annual_vol,
            skewness=skewness,
            kurtosis=kurtosis,
            beta=beta_val,
            correlation=corr_val,
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _calculate_skewness(self, returns: np.ndarray) -> Optional[float]:
        """Calculate skewness of returns."""
        if len(returns) < 3:
            return None

        try:
            from scipy import stats

            return float(stats.skew(returns))
        except ImportError:
            mean = np.mean(returns)
            std = np.std(returns, ddof=1)
            if std < 1e-10:
                return 0.0
            return float(np.mean(((returns - mean) / std) ** 3))

    def _calculate_kurtosis(self, returns: np.ndarray) -> Optional[float]:
        """Calculate excess kurtosis of returns."""
        if len(returns) < 4:
            return None

        try:
            from scipy import stats

            return float(stats.kurtosis(returns))
        except ImportError:
            mean = np.mean(returns)
            std = np.std(returns, ddof=1)
            if std < 1e-10:
                return 0.0
            return float(np.mean(((returns - mean) / std) ** 4) - 3)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_var(
    returns: Union[pd.Series, np.ndarray, List[float]],
    confidence: float = 0.95,
    method: str = "historical",
) -> float:
    """
    Convenience function to calculate Value at Risk.

    Args:
        returns: Return series
        confidence: Confidence level (default: 95%)
        method: Calculation method ('historical', 'parametric', 'cornish_fisher')

    Returns:
        VaR value
    """
    calc = RiskMetricsCalculator(confidence_level=confidence)
    return calc.var(returns, confidence, method)


def get_cvar(
    returns: Union[pd.Series, np.ndarray, List[float]],
    confidence: float = 0.95,
) -> float:
    """
    Convenience function to calculate Conditional VaR.

    Args:
        returns: Return series
        confidence: Confidence level

    Returns:
        CVaR value
    """
    calc = RiskMetricsCalculator(confidence_level=confidence)
    return calc.cvar(returns, confidence)


def get_volatility(
    returns: Union[pd.Series, np.ndarray, List[float]],
    annualize: bool = True,
) -> float:
    """
    Convenience function to calculate volatility.

    Args:
        returns: Return series
        annualize: Whether to annualize

    Returns:
        Volatility
    """
    calc = RiskMetricsCalculator()
    return calc.volatility(returns, annualize)


def get_beta(
    asset_returns: Union[pd.Series, np.ndarray, List[float]],
    market_returns: Union[pd.Series, np.ndarray, List[float]],
) -> float:
    """
    Convenience function to calculate beta.

    Args:
        asset_returns: Asset returns
        market_returns: Market/benchmark returns

    Returns:
        Beta value
    """
    calc = RiskMetricsCalculator()
    return calc.beta(asset_returns, market_returns)


def get_correlation(
    returns1: Union[pd.Series, np.ndarray, List[float]],
    returns2: Union[pd.Series, np.ndarray, List[float]],
) -> float:
    """
    Convenience function to calculate correlation.

    Args:
        returns1: First return series
        returns2: Second return series

    Returns:
        Correlation coefficient
    """
    calc = RiskMetricsCalculator()
    return calc.correlation(returns1, returns2)


def get_tracking_error(
    portfolio_returns: Union[pd.Series, np.ndarray, List[float]],
    benchmark_returns: Union[pd.Series, np.ndarray, List[float]],
    annualize: bool = True,
) -> float:
    """
    Convenience function to calculate tracking error.

    Args:
        portfolio_returns: Portfolio returns
        benchmark_returns: Benchmark returns
        annualize: Whether to annualize

    Returns:
        Tracking error
    """
    calc = RiskMetricsCalculator()
    return calc.tracking_error(portfolio_returns, benchmark_returns, annualize)


def get_information_ratio(
    portfolio_returns: Union[pd.Series, np.ndarray, List[float]],
    benchmark_returns: Union[pd.Series, np.ndarray, List[float]],
    annualize: bool = True,
) -> float:
    """
    Convenience function to calculate information ratio.

    Args:
        portfolio_returns: Portfolio returns
        benchmark_returns: Benchmark returns
        annualize: Whether to annualize

    Returns:
        Information ratio
    """
    calc = RiskMetricsCalculator()
    return calc.information_ratio(portfolio_returns, benchmark_returns, annualize)
