"""
Strategy scoring modules.

Provides specialized scorers for Momentum, Mean Reversion, and
Pairs Trading strategies following Single Responsibility Principle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from scipy import stats

if TYPE_CHECKING:
    from app.shared.config.params.strategy_config import StockAllocationSettings

from .calculators import HalfLifeCalculator, HurstCalculator

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    from statsmodels.regression.linear_model import OLS as sm_OLS
    from statsmodels.tsa.stattools import adfuller

    STATSMODELS_AVAILABLE = True

    def OLS(*args, **kwargs):
        return sm_OLS(*args, **kwargs)

except ImportError:
    from app.shared.performance.statsmodels_fallback import OLS

    STATSMODELS_AVAILABLE = False

    def adfuller(*args, **kwargs):
        """
        Fallback adfuller function when statsmodels is not available.

        Returns a tuple indicating stationarity test failed.
        """
        import warnings

        warnings.warn(
            "statsmodels not installed - ADF test not available. "
            "Install statsmodels for cointegration testing: pip install statsmodels",
            ImportWarning,
        )
        # Return p-value of 1.0 (fail to reject null hypothesis of non-stationarity)
        return (None, 1.0, None, None, None, None, None)


# Check for arch package
try:
    from arch import arch_model

    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False


class MomentumScorer:
    """
    Scores assets for Momentum strategy.

    Metrics: RSI, MACD, ROC, Sortino, slope, Spearman correlation, Hurst.
    """

    def __init__(
        self,
        config: StockAllocationSettings,
        hurst_calculator: HurstCalculator,
        technical_indicator_calculator: Any,
    ) -> None:
        """
        Initialize momentum scorer.

        Args:
            config: Stock allocation configuration
            hurst_calculator: Hurst exponent calculator
            technical_indicator_calculator: Technical indicator calculator
        """
        self.config = config
        self.hurst_calculator = hurst_calculator
        self.indicator_calculator = technical_indicator_calculator

    def score(self, ticker: str, data: pd.DataFrame) -> dict[str, Any]:
        """
        Score asset for Momentum strategy.

        Metrics: RSI, MACD, ROC, Sortino, slope, Spearman correlation.

        Args:
            ticker: Stock ticker
            data: DataFrame with OHLCV data

        Returns:
            Dictionary with scores and metrics
        """
        try:
            prices = data['close'].values
            volumes = data['volume'].values if 'volume' in data.columns else None

            # Calculate technical indicators
            prices_list = prices.tolist()
            rsi = self.indicator_calculator.calculate_rsi(prices_list, 14)
            macd, macd_signal, macd_histogram = self.indicator_calculator.calculate_macd(
                prices_list
            )
            roc = self.indicator_calculator.calculate_roc(prices_list, period=12)

            # Calculate returns
            returns = np.diff(prices) / prices[:-1]

            # Sortino ratio
            sortino = self._calculate_sortino_ratio(returns)

            # Dynamic window selection for slope and ROC
            slope_pct = 0.0
            roc_optimal = roc

            if self.config.DYNAMIC_WINDOW_ENABLED and len(prices) >= self.config.SLOPE_WINDOW_MIN:
                slope_pct, roc_optimal = self._dynamic_window_selection(prices, ticker, roc)
            else:
                # Calculate slope with full price series
                x = np.arange(len(prices))
                if len(prices) > 1 and np.std(x) > 0:
                    slope_coef = np.polyfit(x, prices, 1)[0]
                    slope_pct = (slope_coef / prices[0]) * 100 if prices[0] > 0 else 0

            # Spearman correlation with time
            spearman_rho = 0.0
            if len(prices) > 10:
                x = np.arange(len(prices))
                spearman_corr, _ = stats.spearmanr(x, prices)
                spearman_rho = float(spearman_corr) if not np.isnan(spearman_corr) else 0.0

            # Calculate Hurst (long-term)
            h_long = self.hurst_calculator.calculate(prices)

            # Liquidity score
            liquidity_score = 0.5
            if volumes is not None and len(volumes) > 0:
                avg_volume = np.mean(volumes)
                if avg_volume > 0:
                    liquidity_score = min(1.0, avg_volume / self.config.MIN_LIQUIDITY_USD)

            # Normalize metrics
            (rsi / 100.0) if rsi is not None else 0.5
            (
                min(
                    1.0,
                    max(
                        0.0,
                        (roc_optimal + self.config.MOMENTUM_ROC_NORMALIZATION_OFFSET)
                        / self.config.MOMENTUM_ROC_NORMALIZATION_SCALE,
                    ),
                )
                if roc_optimal is not None
                else 0.5
            )
            sortino_norm = min(1.0, max(0.0, sortino / 2.0)) if sortino is not None else 0.5
            min(
                1.0,
                max(
                    0.0,
                    (slope_pct + self.config.MOMENTUM_SLOPE_NORMALIZATION_OFFSET)
                    / self.config.MOMENTUM_SLOPE_NORMALIZATION_SCALE,
                ),
            )
            min(1.0, max(0.0, (spearman_rho + 1) / 2))
            h_long_norm = (
                (h_long - self.config.MOMENTUM_HURST_NORMALIZATION_OFFSET)
                / self.config.MOMENTUM_HURST_NORMALIZATION_SCALE
                if h_long is not None
                else 0.5
            )

            # Weighted score
            weights = self.config.MOMENTUM_WEIGHTS
            momentum_score = (
                weights.get("H_long", 0.0) * h_long_norm
                + weights.get("Sortino", 0.0) * sortino_norm
                + weights.get("1/tau", 0.0) * 0.5
                + weights.get("Liquidity", 0.0) * liquidity_score
            )

            # Apply Sortino filter
            if sortino is not None and sortino < self.config.MIN_SORTINO_RATIO:
                momentum_score *= 0.5

            result = {
                "score": float(momentum_score),
                "rsi": rsi,
                "macd": macd,
                "roc": roc_optimal,
                "sortino": sortino,
                "slope": slope_pct,
                "spearman_rho": spearman_rho,
                "h_long": h_long,
                "liquidity_score": liquidity_score,
                "weights_used": weights,
            }

            logger.debug(f"Momentum score for {ticker}: {momentum_score:.4f}")
            return result

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error scoring momentum for {ticker}: {e}", exc_info=True)
            return {"score": 0.0}

    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float | None:
        """Calculate Sortino ratio (risk-adjusted return using downside deviation)."""
        if len(returns) < 10:
            return None

        try:
            clean_returns = returns[np.isfinite(returns)]
            if len(clean_returns) < 10:
                return None

            avg_return = np.mean(clean_returns)
            negative_returns = clean_returns[clean_returns < 0]

            if len(negative_returns) == 0:
                downside_dev = np.std(clean_returns)
            else:
                downside_dev = np.std(negative_returns)

            if downside_dev == 0:
                return None

            annualized_return = avg_return * 252
            annualized_downside = downside_dev * np.sqrt(252)

            sortino = annualized_return / annualized_downside if annualized_downside > 0 else None

            return float(sortino) if sortino is not None and np.isfinite(sortino) else None

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Sortino ratio: {e}", exc_info=True)
            return None

    def _dynamic_window_selection(
        self, prices: np.ndarray, ticker: str, roc: float | None
    ) -> tuple[float, float | None]:
        """Select optimal window for slope and ROC calculations."""
        window_min = self.config.SLOPE_WINDOW_MIN
        window_max = min(self.config.SLOPE_WINDOW_MAX, len(prices))
        best_slope_mse = float('inf')
        best_slope_pct = 0.0
        best_roc_mse = float('inf')
        best_roc = roc

        for window in range(window_min, window_max + 1, 5):
            if len(prices) < window:
                continue

            recent_prices = prices[-window:]
            x_window = np.arange(len(recent_prices))

            if len(recent_prices) > 1 and np.std(x_window) > 0:
                try:
                    slope_coef = np.polyfit(x_window, recent_prices, 1)[0]
                    slope_intercept = np.polyfit(x_window, recent_prices, 1)[1]

                    fitted = slope_coef * x_window + slope_intercept
                    mse = np.mean((recent_prices - fitted) ** 2)

                    if mse < best_slope_mse:
                        best_slope_mse = mse
                        slope_pct = (
                            (slope_coef / recent_prices[0]) * 100 if recent_prices[0] > 0 else 0
                        )
                        best_slope_pct = slope_pct

                    if len(recent_prices) >= 12:
                        roc_window = self.indicator_calculator.calculate_roc(
                            recent_prices.tolist(), period=min(12, len(recent_prices) // 4)
                        )
                        if roc_window is not None:
                            returns_window = np.diff(recent_prices) / recent_prices[:-1]
                            if len(returns_window) > 0:
                                roc_error = np.var(returns_window)
                                if roc_error < best_roc_mse:
                                    best_roc_mse = roc_error
                                    best_roc = roc_window
                except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                    logger.debug(f"Error in dynamic window selection (window={window}): {e}")
                    continue

        logger.debug(
            f"{ticker}: Dynamic window selected - slope={best_slope_pct:.4f}%, ROC={best_roc:.4f}"
        )
        return best_slope_pct, best_roc if best_roc is not None else roc


class MeanReversionScorer:
    """
    Scores assets for Mean Reversion strategy.

    Metrics: Half-life (τ), Z-score, GARCH volatility, Hurst.
    """

    def __init__(
        self,
        config: StockAllocationSettings,
        hurst_calculator: HurstCalculator,
        half_life_calculator: HalfLifeCalculator,
    ) -> None:
        """
        Initialize mean reversion scorer.

        Args:
            config: Stock allocation configuration
            hurst_calculator: Hurst exponent calculator
            half_life_calculator: Half-life calculator
        """
        self.config = config
        self.hurst_calculator = hurst_calculator
        self.half_life_calculator = half_life_calculator

    def score(self, ticker: str, data: pd.DataFrame) -> dict[str, Any]:
        """
        Score asset for Mean Reversion strategy.

        Metrics: Half-life (τ), Z-score, GARCH volatility.

        Args:
            ticker: Stock ticker
            data: DataFrame with OHLCV data

        Returns:
            Dictionary with scores and metrics
        """
        try:
            prices = data['close'].values
            volumes = data['volume'].values if 'volume' in data.columns else None

            # Calculate returns
            returns = pd.Series(np.diff(prices) / prices[:-1])

            # Calculate half-life
            prices_series = pd.Series(prices)
            half_life = self.half_life_calculator.calculate(prices_series)

            # Reject if half-life too high or too low
            if half_life is not None and half_life > self.config.MAX_HALF_LIFE_DAYS:
                logger.debug(
                    f"{ticker}: Rejected - half-life {half_life:.2f} > {self.config.MAX_HALF_LIFE_DAYS}"
                )
                return {
                    "score": 0.0,
                    "half_life": half_life,
                    "rejected": True,
                    "reason": f"Half-life {half_life:.2f} exceeds maximum {self.config.MAX_HALF_LIFE_DAYS}",
                }

            if half_life is not None and half_life < self.config.MIN_HALF_LIFE_DAYS:
                logger.debug(
                    f"{ticker}: Rejected - half-life {half_life:.2f} < {self.config.MIN_HALF_LIFE_DAYS}"
                )
                return {
                    "score": 0.0,
                    "half_life": half_life,
                    "rejected": True,
                    "reason": f"Half-life {half_life:.2f} too low (noise)",
                }

            # Calculate Z-score
            mean_price = np.mean(prices)
            std_price = np.std(prices)
            current_price = prices[-1]
            z_score = (current_price - mean_price) / std_price if std_price > 0 else 0.0

            # GARCH volatility
            garch_vol = self._calculate_garch_volatility(returns)

            # Sortino ratio
            sortino = self._calculate_sortino_ratio(returns.values)

            # Hurst (should be low for mean reversion)
            h_long = self.hurst_calculator.calculate(prices)

            # Liquidity
            liquidity_score = 0.5
            if volumes is not None and len(volumes) > 0:
                avg_volume = np.mean(volumes)
                if avg_volume > 0:
                    liquidity_score = min(1.0, avg_volume / self.config.MIN_LIQUIDITY_USD)

            # Normalize metrics
            inv_tau_norm = 0.5
            if half_life is not None:
                inv_tau = 1.0 / half_life
                inv_tau_norm = min(
                    1.0,
                    max(
                        0.0,
                        (inv_tau - self.config.INVERSE_TAU_NORMALIZATION_OFFSET)
                        / self.config.INVERSE_TAU_NORMALIZATION_SCALE,
                    ),
                )

            sortino_norm = min(1.0, max(0.0, sortino / 2.0)) if sortino is not None else 0.5
            h_long_norm = (
                max(
                    0.0,
                    (self.config.MEAN_REVERSION_HURST_NORMALIZATION_CENTER - h_long)
                    / self.config.MEAN_REVERSION_HURST_NORMALIZATION_SCALE,
                )
                if h_long is not None
                else 0.5
            )

            # Weighted score
            weights = self.config.MEAN_REVERSION_WEIGHTS
            mean_reversion_score = (
                weights.get("H_long", 0.0) * h_long_norm
                + weights.get("Sortino", 0.0) * sortino_norm
                + weights.get("1/tau", 0.0) * inv_tau_norm
                + weights.get("Liquidity", 0.0) * liquidity_score
            )

            result = {
                "score": float(mean_reversion_score),
                "half_life": half_life,
                "z_score": float(z_score),
                "garch_volatility": garch_vol,
                "sortino": sortino,
                "h_long": h_long,
                "liquidity_score": liquidity_score,
                "rejected": False,
            }

            logger.debug(
                f"Mean reversion score for {ticker}: {mean_reversion_score:.4f} (tau={half_life})"
            )
            return result

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error scoring mean reversion for {ticker}: {e}", exc_info=True)
            return {"score": 0.0}

    def _calculate_garch_volatility(self, returns: pd.Series) -> float | None:
        """Calculate GARCH volatility forecast."""
        if len(returns) < 50:
            return None

        try:
            clean_returns = returns.dropna()
            if len(clean_returns) < 50:
                return None

            # Try GARCH(1,1) if available
            if ARCH_AVAILABLE:
                try:
                    model = arch_model(clean_returns * 100, vol='Garch', p=1, q=1, rescale=False)
                    fitted = model.fit(disp='of')

                    forecast = fitted.forecast(horizon=self.config.GARCH_FORECAST_HORIZON)
                    forecast_vol = np.sqrt(forecast.variance.values[-1, -1]) / 100

                    return float(forecast_vol * np.sqrt(252))
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    logger.debug(f"GARCH fitting failed: {e}, using EWMA")

            # Use EWMA volatility
            alpha = self.config.EWMA_ALPHA
            ewma_var = clean_returns.ewm(alpha=alpha, adjust=False).var().iloc[-1]
            ewma_vol = np.sqrt(ewma_var)

            return float(ewma_vol * np.sqrt(252))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating GARCH volatility: {e}", exc_info=True)
            return None

    def _calculate_sortino_ratio(self, returns: np.ndarray) -> float | None:
        """Calculate Sortino ratio."""
        if len(returns) < 10:
            return None

        try:
            clean_returns = returns[np.isfinite(returns)]
            if len(clean_returns) < 10:
                return None

            avg_return = np.mean(clean_returns)
            negative_returns = clean_returns[clean_returns < 0]

            if len(negative_returns) == 0:
                downside_dev = np.std(clean_returns)
            else:
                downside_dev = np.std(negative_returns)

            if downside_dev == 0:
                return None

            annualized_return = avg_return * 252
            annualized_downside = downside_dev * np.sqrt(252)

            sortino = annualized_return / annualized_downside if annualized_downside > 0 else None

            return float(sortino) if sortino is not None and np.isfinite(sortino) else None

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error calculating Sortino ratio: {e}", exc_info=True)
            return None


class PairsTradingScorer:
    """
    Scores pairs for Pairs Trading strategy.

    Uses Engle-Granger cointegration test, correlation, half-life.
    """

    def __init__(
        self,
        config: StockAllocationSettings,
        half_life_calculator: HalfLifeCalculator,
        garch_volatility_calculator: Any,
    ) -> None:
        """
        Initialize pairs trading scorer.

        Args:
            config: Stock allocation configuration
            half_life_calculator: Half-life calculator
            garch_volatility_calculator: GARCH volatility calculator
        """
        self.config = config
        self.half_life_calculator = half_life_calculator
        self.garch_calculator = garch_volatility_calculator

    def score(
        self, pair: tuple[str, str], data1: pd.DataFrame, data2: pd.DataFrame
    ) -> dict[str, Any]:
        """
        Score pair for Pairs Trading strategy.

        Uses Engle-Granger cointegration test.

        Args:
            pair: Tuple of (ticker1, ticker2)
            data1: DataFrame for first asset
            data2: DataFrame for second asset

        Returns:
            Dictionary with scores and metrics
        """
        ticker1, ticker2 = pair
        try:
            min_len = min(len(data1), len(data2))
            min_lookback = self.config.MIN_COINTEGRATION_LOOKBACK_DAYS

            if min_len < min_lookback:
                logger.warning(
                    f"Pair {ticker1}-{ticker2}: Insufficient data ({min_len} < {min_lookback})"
                )
                return {
                    "score": 0.0,
                    "rejected": True,
                    "reason": f"Insufficient lookback: {min_len} < {min_lookback}",
                }

            prices1 = data1['close'].values[-min_len:]
            prices2 = data2['close'].values[-min_len:]

            # Correlation
            correlation = np.corrcoef(prices1, prices2)[0, 1]
            if np.isnan(correlation):
                correlation = 0.0

            # Cointegration test
            if not STATSMODELS_AVAILABLE:
                return {
                    "score": 0.0,
                    "rejected": True,
                    "reason": "statsmodels required for cointegration test",
                }

            (
                cointegration_passed,
                cointegration_score,
                hedge_ratio,
                half_life,
                spread_z_score,
                garch_normalized_z,
            ) = self._cointegration_test(ticker1, ticker2, prices1, prices2)

            if not cointegration_passed:
                return {
                    "score": 0.0,
                    "correlation": float(correlation),
                    "cointegration_score": cointegration_score,
                    "rejected": True,
                    "reason": "Cointegration test failed",
                }

            # Reject if half-life too high
            if half_life is not None and half_life > self.config.MAX_HALF_LIFE_DAYS:
                return {
                    "score": 0.0,
                    "half_life": half_life,
                    "rejected": True,
                    "reason": f"Half-life {half_life:.2f} > {self.config.MAX_HALF_LIFE_DAYS}",
                }

            # Liquidity
            volumes1 = data1['volume'].values[-min_len:] if 'volume' in data1.columns else None
            volumes2 = data2['volume'].values[-min_len:] if 'volume' in data2.columns else None

            liquidity_score = 0.5
            if volumes1 is not None and volumes2 is not None:
                avg_vol1 = np.mean(volumes1)
                avg_vol2 = np.mean(volumes2)
                avg_vol = (avg_vol1 + avg_vol2) / 2
                avg_price = (np.mean(prices1) + np.mean(prices2)) / 2
                avg_liquidity = avg_vol * avg_price
                liquidity_score = min(1.0, avg_liquidity / self.config.MIN_LIQUIDITY_USD)

            # Normalize metrics
            inv_tau_norm = 0.5
            if half_life is not None:
                inv_tau = 1.0 / half_life
                inv_tau_norm = min(
                    1.0,
                    max(
                        0.0,
                        (inv_tau - self.config.INVERSE_TAU_NORMALIZATION_OFFSET)
                        / self.config.INVERSE_TAU_NORMALIZATION_SCALE,
                    ),
                )

            # Weighted score
            weights = self.config.PAIRS_TRADING_WEIGHTS
            pairs_score = (
                weights.get("1/tau", 0.0) * inv_tau_norm
                + weights.get("Liquidity", 0.0) * liquidity_score
            )

            # Boost score with cointegration
            pairs_score *= 0.5 + cointegration_score * 0.5

            result = {
                "score": float(pairs_score),
                "correlation": float(correlation),
                "cointegration_score": cointegration_score,
                "half_life": half_life,
                "hedge_ratio": hedge_ratio,
                "liquidity_score": liquidity_score,
                "spread_z_score": float(spread_z_score) if spread_z_score is not None else None,
                "garch_normalized_z": (
                    float(garch_normalized_z) if garch_normalized_z is not None else None
                ),
                "rejected": False,
            }

            logger.debug(f"Pairs trading score for {ticker1}-{ticker2}: {pairs_score:.4f}")
            return result

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error scoring pairs trading for {pair}: {e}", exc_info=True)
            return {"score": 0.0, "rejected": True}

    def _cointegration_test(
        self, ticker1: str, ticker2: str, prices1: np.ndarray, prices2: np.ndarray
    ) -> tuple[bool, float, float, float | None, float | None, float | None]:
        """Perform Engle-Granger cointegration test."""
        cointegration_passed = False
        cointegration_score = 0.0
        half_life = None
        hedge_ratio = 1.0
        spread_z_score = None
        garch_normalized_z = None

        try:
            # OLS regression: prices2 = alpha + beta * prices1
            model = OLS(prices2, prices1).fit()
            hedge_ratio = float(model.params[0])
            residuals = model.resid

            # ADF test on residuals
            adf_result = adfuller(residuals, autolag='AIC')
            adf_pvalue = adf_result[1]

            cointegration_passed = adf_pvalue < self.config.ADF_P_VALUE_THRESHOLD
            cointegration_score = 1.0 - adf_pvalue

            # Calculate half-life of spread
            residual_series = pd.Series(residuals)
            half_life = self.half_life_calculator.calculate(residual_series)

            # Calculate z-score and GARCH normalization
            if len(residuals) > 0:
                spread_mean = np.mean(residuals)
                spread_std = np.std(residuals)
                current_spread = residuals[-1]
                spread_z_score = (
                    (current_spread - spread_mean) / spread_std if spread_std > 0 else 0.0
                )

                # GARCH volatility of spread
                spread_diff = np.diff(residuals)
                spread_returns = pd.Series(spread_diff / (np.abs(residuals[:-1]) + 1e-10))

                garch_vol_spread = self.garch_calculator(spread_returns)

                if garch_vol_spread is not None and garch_vol_spread > 0:
                    garch_normalization_factor = (
                        garch_vol_spread / (spread_std * np.sqrt(252)) if spread_std > 0 else 1.0
                    )
                    garch_normalized_z = spread_z_score / max(
                        garch_normalization_factor, self.config.GARCH_NORMALIZATION_MIN_FACTOR
                    )
                    logger.debug(
                        f"Pair {ticker1}-{ticker2}: z_raw={spread_z_score:.4f}, "
                        f"GARCH_vol={garch_vol_spread:.4f}, z_GARCH={garch_normalized_z:.4f}"
                    )
                else:
                    garch_normalized_z = spread_z_score

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.debug(f"Engle-Granger test failed for {ticker1}-{ticker2}: {e}")

        return (
            cointegration_passed,
            cointegration_score,
            hedge_ratio,
            half_life,
            spread_z_score,
            garch_normalized_z,
        )


class WCMScoreCalculator:
    """
    Calculates Weighted Scoring Model (WCM) scores for all assets.

    Normalizes metrics and calculates SPS_{i,k} = Σ(W_{k,j} × Score_{i,j}^{Norm})
    """

    def __init__(
        self,
        momentum_scorer: MomentumScorer,
        mean_reversion_scorer: MeanReversionScorer,
        pairs_scorer: PairsTradingScorer,
    ) -> None:
        """
        Initialize WCM score calculator.

        Args:
            momentum_scorer: Momentum strategy scorer
            mean_reversion_scorer: Mean reversion strategy scorer
            pairs_scorer: Pairs trading strategy scorer
        """
        self.momentum_scorer = momentum_scorer
        self.mean_reversion_scorer = mean_reversion_scorer
        self.pairs_scorer = pairs_scorer

    def calculate_all(
        self,
        filtered_stocks: dict[str, pd.DataFrame],
        config: Any,
    ) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]]]:
        """
        Calculate WCM scores for all assets.

        Args:
            filtered_stocks: Dictionary of filtered stocks with data
            config: Stock allocation configuration

        Returns:
            Tuple of (ticker scores, pair metrics list)
        """
        logger.info("Calculating WCM scores for all assets")

        all_scores = {}

        for ticker, data in filtered_stocks.items():
            scores = {"momentum": 0.0, "mean_reversion": 0.0, "pairs_trading": 0.0}

            # Score for momentum
            momentum_result = self.momentum_scorer.score(ticker, data)
            scores["momentum"] = momentum_result.get("score", 0.0)

            # Score for mean reversion
            mean_rev_result = self.mean_reversion_scorer.score(ticker, data)
            scores["mean_reversion"] = (
                mean_rev_result.get("score", 0.0)
                if not mean_rev_result.get("rejected", False)
                else 0.0
            )

            all_scores[ticker] = scores

            if config.LOG_ALL_DECISIONS:
                logger.debug(
                    f"{ticker}: Momentum={scores['momentum']:.4f}, "
                    f"MeanRev={scores['mean_reversion']:.4f}"
                )

        # Score pairs
        pair_metrics = self._score_pairs(filtered_stocks, config)

        logger.info(f"Calculated scores for {len(all_scores)} assets and {len(pair_metrics)} pairs")
        return all_scores, pair_metrics

    def _score_pairs(
        self, filtered_stocks: dict[str, pd.DataFrame], config: Any
    ) -> list[dict[str, Any]]:
        """Score all pairs for pairs trading."""
        tickers = list(filtered_stocks.keys())
        pair_metrics = []
        pair_scores = {}

        # Try to get configured pairs
        configured_pairs = self._get_configured_pairs(filtered_stocks, config)

        if configured_pairs:
            pairs_to_evaluate = configured_pairs
        else:
            # Generate all pairs (limit for performance)
            max_pairs = 50
            pairs_to_evaluate = []
            pair_count = 0

            for i, ticker1 in enumerate(tickers):
                if pair_count >= max_pairs:
                    break
                for ticker2 in tickers[i + 1 :]:
                    if pair_count >= max_pairs:
                        break
                    pairs_to_evaluate.append((ticker1, ticker2))
                    pair_count += 1

        # Evaluate pairs
        for ticker1, ticker2 in pairs_to_evaluate:
            if ticker1 not in filtered_stocks or ticker2 not in filtered_stocks:
                continue

            pair = (ticker1, ticker2)
            pair_result = self.pairs_scorer.score(
                pair, filtered_stocks[ticker1], filtered_stocks[ticker2]
            )

            if not pair_result.get("rejected", False):
                pair_scores[pair] = pair_result.get("score", 0.0)
                pair_metrics.append(
                    {
                        "ticker1": ticker1,
                        "ticker2": ticker2,
                        "cointegration_score": pair_result.get("cointegration_score", 0.0),
                        "correlation": pair_result.get("correlation", 0.0),
                        "half_life_tau": pair_result.get("half_life"),
                        "decision_log": f"Cointegration: {pair_result.get('cointegration_score', 0):.4f}",
                    }
                )

        return pair_metrics

    def _get_configured_pairs(
        self, filtered_stocks: dict[str, pd.DataFrame], config: Any
    ) -> list[tuple[str, str]]:
        """Get configured pairs from strategy config."""
        try:
            from app.shared.config.centralized_config import get_config

            config_obj = get_config()
            pairs_strategy_config = config_obj.get_strategy_config("pairs_trading")

            if pairs_strategy_config and pairs_strategy_config.parameters:
                pair_symbols_raw = pairs_strategy_config.parameters.get("pair_symbols")
                if pair_symbols_raw and isinstance(pair_symbols_raw, list):
                    if len(pair_symbols_raw) > 0 and isinstance(pair_symbols_raw[0], list):
                        return [
                            (pair[0], pair[1])
                            for pair in pair_symbols_raw
                            if isinstance(pair, list)
                            and len(pair) >= 2
                            and pair[0] in filtered_stocks
                            and pair[1] in filtered_stocks
                        ]
                    elif len(pair_symbols_raw) >= 2:
                        return [(pair_symbols_raw[0], pair_symbols_raw[1])]
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.debug(f"Could not load configured pairs: {e}")

        return []
