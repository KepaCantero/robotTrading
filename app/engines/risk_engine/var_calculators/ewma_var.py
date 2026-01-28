"""
EWMA VaR Calculator - Hull Chapter 18

Implements Exponentially Weighted Moving Average (EWMA) for VaR calculation.

EWMA gives more weight to recent observations and less to older ones,
making it more responsive to changing market conditions than simple
historical VaR or equally-weighted parametric VaR.

Key advantages:
1. Volatility clustering - captures periods of high/low volatility
2. Asymmetric response - responds faster to increased volatility
3. RiskMetrics methodology - industry standard for short-term VaR

Formula:
σ²_t = λ * σ²_{t-1} + (1-λ) * r²_{t-1}

Where λ (lambda) is the decay factor:
- λ = 0.94 for daily data (RiskMetrics standard)
- λ = 0.97 for monthly data

Reference: Hull, Options, Futures, and Other Derivatives, Chapter 18
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class EWMAVaRCalculator:
    """
    EWMA VaR Calculator.

    Calculates VaR using Exponentially Weighted Moving Average volatility estimation.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize EWMA VaR calculator.

        Args:
            config: Configuration dictionary
        """
        config = config or {}
        self.confidence_level = config.get('confidence_level', 0.95)
        self.decay_factor = config.get('decay_factor', 0.94)  # RiskMetrics standard
        self.min_observations = config.get('min_observations', 30)
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_ewma_var(
        self,
        returns: List[float],
        portfolio_value: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculate VaR using EWMA volatility estimation.

        Args:
            returns: List of historical returns (most recent last)
            portfolio_value: Current portfolio value (optional)

        Returns:
            Dict with EWMA VaR analysis
        """
        try:
            returns_array = np.array(returns)

            if len(returns_array) < self.min_observations:
                return {
                    'error': f'Insufficient data: {len(returns_array)} observations, '
                    f'need {self.min_observations}+'
                }

            # Calculate EWMA variance
            ewma_variance = self._calculate_ewma_variance(returns_array)
            ewma_volatility = np.sqrt(ewma_variance)

            # Calculate VaR using EWMA volatility
            from scipy import stats

            z_score = stats.norm.ppf(1 - self.confidence_level)
            mean_return = np.mean(returns_array)

            var_ewma = mean_return - z_score * ewma_volatility

            # CVaR (Expected Shortfall) under EWMA
            phi_z = stats.norm.pdf(z_score)
            cvar_ewma = mean_return - ewma_volatility * phi_z / (1 - self.confidence_level)

            # Convert to dollar amount if portfolio value provided
            var_amount = None
            cvar_amount = None
            if portfolio_value is not None:
                var_amount = abs(var_ewma * portfolio_value)
                cvar_amount = abs(cvar_ewma * portfolio_value)

            # Compare with simple historical volatility
            simple_std = np.std(returns_array)
            comparison = {
                'ewma_volatility': float(ewma_volatility),
                'simple_std': float(simple_std),
                'volatility_ratio': float(ewma_volatility / simple_std) if simple_std > 0 else None,
                'ewma_higher': ewma_volatility > simple_std,
            }

            return {
                'var': float(var_ewma),
                'var_amount': float(var_amount) if var_amount is not None else None,
                'cvar': float(cvar_ewma),
                'cvar_amount': float(cvar_amount) if cvar_amount is not None else None,
                'ewma_variance': float(ewma_variance),
                'ewma_volatility': float(ewma_volatility),
                'confidence_level': self.confidence_level,
                'method': 'ewma',
                'decay_factor': self.decay_factor,
                'observations': len(returns_array),
                'comparison': comparison,
                'interpretation': self._interpret_ewma(comparison),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f'Error calculating EWMA VaR: {e}', exc_info=True)
            return {'error': str(e)}

    def _calculate_ewma_variance(self, returns: np.ndarray) -> float:
        """
        Calculate EWMA variance.

        Uses recursive formula:
        σ²_t = λ * σ²_{t-1} + (1-λ) * r²_{t-1}

        Starting with sample variance for initial estimate.
        """
        # Initialize with sample variance
        variance = np.var(returns)

        # Apply EWMA recursively
        lambda_decay = self.decay_factor

        for i in range(1, len(returns)):
            variance = lambda_decay * variance + (1 - lambda_decay) * (returns[i - 1] ** 2)

        return float(variance)

    def _interpret_ewma(self, comparison: Dict[str, Any]) -> str:
        """Interpret EWMA vs simple volatility comparison."""
        if comparison['volatility_ratio'] is None:
            return 'Unable to compare - zero simple volatility'

        ratio = comparison['volatility_ratio']

        if ratio > 1.3:
            return (
                f'EWMA volatility {ratio:.2f}x higher than simple std. '
                f'Recent volatility spike detected - consider reducing positions.'
            )
        elif ratio > 1.1:
            return (
                f'EWMA volatility {ratio:.2f}x higher than simple std. '
                f'Elevating volatility - monitor closely.'
            )
        elif ratio < 0.9:
            return (
                f'EWMA volatility {ratio:.2f}x lower than simple std. '
                f'Volatility decelerating - favorable conditions.'
            )
        else:
            return (
                f'EWMA and simple volatility aligned (ratio {ratio:.2f}). '
                f'Stable volatility environment.'
            )

    def calculate_ewma_correlation(
        self,
        returns1: List[float],
        returns2: List[float],
    ) -> Dict[str, Any]:
        """
        Calculate EWMA correlation between two return series.

        Uses RiskMetrics methodology for dynamic correlation estimation.

        Args:
            returns1: First return series
            returns2: Second return series

        Returns:
            Dict with EWMA correlation analysis
        """
        try:
            min_len = min(len(returns1), len(returns2))

            if min_len < self.min_observations:
                return {
                    'error': f'Insufficient data: {min_len} observations, '
                    f'need {self.min_observations}+'
                }

            r1 = np.array(returns1[:min_len])
            r2 = np.array(returns2[:min_len])

            # Calculate EWMA variances and covariance
            var1 = self._calculate_ewma_variance(r1)
            var2 = self._calculate_ewma_variance(r2)
            covariance = self._calculate_ewma_covariance(r1, r2)

            # EWMA correlation
            denominator = np.sqrt(var1 * var2)
            ewma_correlation = covariance / denominator if denominator > 0 else 0

            # Compare with simple correlation
            simple_correlation = np.corrcoef(r1, r2)[0, 1] if len(r1) > 1 else 0

            return {
                'ewma_correlation': float(ewma_correlation),
                'simple_correlation': float(simple_correlation),
                'ewma_variance_1': float(var1),
                'ewma_variance_2': float(var2),
                'ewma_covariance': float(covariance),
                'correlation_increase': ewma_correlation > simple_correlation,
                'interpretation': self._interpret_correlation_change(
                    ewma_correlation, simple_correlation
                ),
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f'Error calculating EWMA correlation: {e}', exc_info=True)
            return {'error': str(e)}

    def _calculate_ewma_covariance(
        self,
        returns1: np.ndarray,
        returns2: np.ndarray,
    ) -> float:
        """
        Calculate EWMA covariance.

        Formula:
        σ_{xy,t} = λ * σ_{xy,t-1} + (1-λ) * r_{x,t-1} * r_{y,t-1}
        """
        # Initialize with sample covariance
        covariance = np.cov(returns1, returns2)[0, 1]

        # Apply EWMA recursively
        lambda_decay = self.decay_factor

        for i in range(1, len(returns1)):
            covariance = (
                lambda_decay * covariance + (1 - lambda_decay) * returns1[i - 1] * returns2[i - 1]
            )

        return float(covariance)

    def _interpret_correlation_change(
        self,
        ewma_corr: float,
        simple_corr: float,
    ) -> str:
        """Interpret EWMA vs simple correlation change."""
        diff = ewma_corr - simple_corr

        if diff > 0.15:
            return (
                f'EWMA correlation {ewma_corr:.3f} significantly higher than '
                f'simple {simple_corr:.3f}. Correlations INCREASING - '
                f'reduce diversification benefits. Consider de-risking.'
            )
        elif diff > 0.05:
            return (
                f'EWMA correlation {ewma_corr:.3f} moderately higher than '
                f'simple {simple_corr:.3f}. Correlations elevating.'
            )
        elif diff < -0.15:
            return (
                f'EWMA correlation {ewma_corr:.3f} significantly lower than '
                f'simple {simple_corr:.3f}. Correlations DECREASING - '
                f'improving diversification benefits.'
            )
        elif diff < -0.05:
            return (
                f'EWMA correlation {ewma_corr:.3f} moderately lower than '
                f'simple {simple_corr:.3f}. Correlations declining.'
            )
        else:
            return (
                f'EWMA and simple correlations aligned '
                f'(EWMA: {ewma_corr:.3f}, simple: {simple_corr:.3f}). '
                f'Stable correlation regime.'
            )

    def forecast_volatility(
        self,
        returns: List[float],
        horizon_days: int = 10,
    ) -> Dict[str, Any]:
        """
        Forecast future volatility using EWMA.

        Args:
            returns: Historical returns
            horizon_days: Forecast horizon

        Returns:
            Volatility forecast
        """
        try:
            returns_array = np.array(returns)

            if len(returns_array) < self.min_observations:
                return {'error': 'Insufficient data for forecasting'}

            # Calculate current EWMA variance
            current_variance = self._calculate_ewma_variance(returns_array)

            # EWMA assumes mean reversion to long-run variance
            # For short horizons, variance stays relatively constant
            # For longer horizons, we can apply square-root of time rule

            forecasts = []
            current_vol = np.sqrt(current_variance)

            for day in range(1, horizon_days + 1):
                # Square-root of time scaling
                forecast_vol = current_vol * np.sqrt(day)
                forecasts.append(forecast_vol)

            return {
                'current_volatility': float(current_vol),
                'forecasts': [float(f) for f in forecasts],
                'horizon_days': horizon_days,
                'method': 'ewma_sqrt_time',
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error(f'Error forecasting volatility: {e}', exc_info=True)
            return {'error': str(e)}
