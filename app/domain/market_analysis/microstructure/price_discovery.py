"""
Price Discovery and Information Aggregation Module

This module implements price discovery models and information aggregation concepts
from Maureen O'Hara's "Market Microstructure Theory" (Chapter 7-8).

Key Concepts:
- Price formation models
- Information aggregation in market prices
- Efficient price discovery measurement
- Price adjustment dynamics
- Market efficiency testing

References:
- O'Hara, M. (1995) "Market Microstructure Theory", Chapters 7-8
- Hasbrouck, J. (1995) "One Security, Many Markets"
- Hasbrouck, J. (1991) "Measuring the Information Content of Stock Trades"
- Madhavan, A. (2000) "Market Microstructure: A Survey"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# Import statsmodels with fallback
try:
    from statsmodels.tsa.stattools import adfuller as sm_adfuller, coint as sm_coint

    STATSMODELS_AVAILABLE = True

    def coint(*args, **kwargs):
        return sm_coint(*args, **kwargs)

    def adfuller(*args, **kwargs):
        return sm_adfuller(*args, **kwargs)

except ImportError:
    STATSMODELS_AVAILABLE = False

    # Fallback implementations for cointegration and unit root tests
    # Using scipy to avoid circular import with app.core
    def coint(*args, **kwargs):
        """
        Fallback cointegration test using Engle-Granger two-step method
        with scipy instead of statsmodels
        """
        y1 = args[0]
        y2 = args[1]
        # Ensure same length
        min_len = min(len(y1), len(y2))
        y1 = y1.iloc[-min_len:] if hasattr(y1, 'iloc') else y1[-min_len:]
        y2 = y2.iloc[-min_len:] if hasattr(y2, 'iloc') else y2[-min_len:]

        # Step 1: Estimate long-run relationship: y1 = alpha + beta*y2 + epsilon
        X = np.vstack([np.ones(len(y2)), y2.values if hasattr(y2, 'values') else y2]).T
        y1_vals = y1.values if hasattr(y1, 'values') else y1

        # OLS regression
        beta = np.linalg.lstsq(X, y1_vals, rcond=None)[0]

        # Step 2: Get residuals
        residuals = y1_vals - X @ beta

        # Step 3: ADF test on residuals
        # Calculate test statistic
        residual_diff = np.diff(residuals)
        residual_lag = residuals[:-1]

        # Simple ADF regression: delta(residual) = alpha + beta*residual_lag + error
        if len(residual_lag) > 0:
            X_adf = np.vstack([np.ones(len(residual_lag)), residual_lag]).T
            beta_adf = np.linalg.lstsq(X_adf, residual_diff, rcond=None)[0]
            t_stat = beta_adf[1] / np.std(residual_diff) if len(residual_diff) > 1 else 0
        else:
            t_stat = 0

        # Critical values (approximate for large samples)
        critical_values = {-3.90: 0.01, -3.34: 0.05, -3.04: 0.10}

        # Find p-value by interpolation
        if t_stat < min(critical_values.keys()):
            pvalue = 0.01
        elif t_stat > max(critical_values.keys()):
            pvalue = 0.10
        else:
            # Linear interpolation
            sorted_cv = sorted(critical_values.items())
            for i in range(len(sorted_cv) - 1):
                if sorted_cv[i][0] <= t_stat <= sorted_cv[i + 1][0]:
                    # Interpolate p-value
                    p1, p2 = sorted_cv[i][1], sorted_cv[i + 1][1]
                    t1, t2 = sorted_cv[i][0], sorted_cv[i + 1][0]
                    pvalue = p1 + (p2 - p1) * (t_stat - t1) / (t2 - t1)
                    break
            else:
                pvalue = 0.05  # Default

        return t_stat, pvalue, beta

    def adfuller(*args, **kwargs):
        """
        Fallback Augmented Dickey-Fuller test using scipy
        """
        x = args[0]
        regression = kwargs.get('regression', args[2] if len(args) > 2 else 'c')

        # Convert to numpy array if needed
        if hasattr(x, 'values'):
            x = x.values

        # Calculate differences
        diff_x = np.diff(x)

        # Create lagged values
        lagged_x = x[:-1]

        # Prepare design matrix based on regression type
        if regression == 'c':  # Constant only
            X = np.vstack([np.ones(len(lagged_x)), lagged_x]).T
        elif regression == 'ct':  # Constant and trend
            trend = np.arange(len(lagged_x))
            X = np.vstack([np.ones(len(lagged_x)), trend, lagged_x]).T
        else:  # No constant
            X = lagged_x.reshape(-1, 1)

        # OLS regression
        if len(X) > 0 and len(diff_x) > 0:
            beta = np.linalg.lstsq(X, diff_x, rcond=None)[0]

            # Test statistic is t-stat of coefficient on lagged level
            if regression == 'c':
                coef_idx = 1
            elif regression == 'ct':
                coef_idx = 2
            else:
                coef_idx = 0

            coef = beta[coef_idx]

            # Estimate standard error
            residuals = diff_x - X @ beta
            n = len(residuals)
            sigma2 = np.sum(residuals**2) / (n - X.shape[1])

            # Standard error of coefficient
            XtX_inv = np.linalg.inv(X.T @ X)
            se = np.sqrt(sigma2 * XtX_inv[coef_idx, coef_idx])

            t_stat = coef / se if se > 0 else 0
        else:
            t_stat = 0

        # Critical values (MacKinnon approximate)
        critical_values = {'1%': -3.43, '5%': -2.86, '10%': -2.57}

        # Approximate p-value
        if t_stat < critical_values['1%']:
            pvalue = 0.01
        elif t_stat < critical_values['5%']:
            pvalue = 0.05
        elif t_stat < critical_values['10%']:
            pvalue = 0.10
        else:
            pvalue = 0.99  # Cannot reject null

        return (
            t_stat,
            pvalue,
            False,
            len(diff_x),
            {
                '1%': critical_values['1%'],
                '5%': critical_values['5%'],
                '10%': critical_values['10%'],
            },
        )


class PriceDiscoveryModel(Enum):
    """Price discovery model types"""

    ROLL = "ROLL"  # Roll (1984) spread model
    HASBROUCK = "HASBROUCK"  # Hasbrouck (1991) information share
    GLOSTEN_MILGROM = "GLOSTEN_MILGROM"  # Sequential trade model
    KYLE = "KYLE"  # Kyle (1985) auction model
    MADHAVAN_RICHARDSON = "MADHAVAN_RICHARDSON"  # Order flow model


class MarketEfficiency(Enum):
    """Market efficiency classification"""

    STRONG_FORM = "STRONG_FORM"  # All information reflected
    SEMI_STRONG = "SEMI_STRONG"  # Public information reflected
    WEAK_FORM = "WEAK_FORM"  # Past prices reflected
    INEFFICIENT = "INEFFICIENT"  # Deviations from efficiency


@dataclass
class PriceDiscoveryMetrics:
    """
    Metrics for price discovery efficiency

    Attributes:
        timestamp: Measurement time
        information_share: Hasbrouck information share (0-1)
        price_adjustment_speed: Speed of price adjustment
        pricing_error: Deviation from efficient price
        discovery_quality_score: Composite score (0-100)
        efficiency_level: Market efficiency classification
    """

    timestamp: datetime
    information_share: float
    price_adjustment_speed: float
    pricing_error: float
    discovery_quality_score: float
    efficiency_level: MarketEfficiency

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'information_share': self.information_share,
            'price_adjustment_speed': self.price_adjustment_speed,
            'pricing_error': self.pricing_error,
            'discovery_quality_score': self.discovery_quality_score,
            'efficiency_level': self.efficiency_level.value,
        }


@dataclass
class EfficientPriceEstimate:
    """
    Estimate of the efficient (fundamental) price

    The efficient price is the price that would prevail in a frictionless
    market with full information (O'Hara 7.2)

    Attributes:
        timestamp: Estimate time
        observed_price: Current market price
        efficient_price: Estimated efficient price
        pricing_error: Difference between observed and efficient
        confidence_interval: 95% confidence interval
        estimation_method: Method used for estimation
    """

    timestamp: datetime
    observed_price: Decimal
    efficient_price: Decimal
    pricing_error: Decimal
    confidence_interval: Tuple[Decimal, Decimal]
    estimation_method: str

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'observed_price': str(self.observed_price),
            'efficient_price': str(self.efficient_price),
            'pricing_error': str(self.pricing_error),
            'confidence_interval': (
                str(self.confidence_interval[0]),
                str(self.confidence_interval[1]),
            ),
            'estimation_method': self.estimation_method,
        }


@dataclass
class InformationFlowMetrics:
    """
    Metrics for information flow into prices

    Attributes:
        timestamp: Measurement time
        information_content: Information content of trades
        price_impact: Average price impact per trade
        flow_persistence: Persistence of information effects
        information_decay_rate: Rate at which information decays
    """

    timestamp: datetime
    information_content: float
    price_impact: float
    flow_persistence: float
    information_decay_rate: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'information_content': self.information_content,
            'price_impact': self.price_impact,
            'flow_persistence': self.flow_persistence,
            'information_decay_rate': self.information_decay_rate,
        }


@dataclass
class MarketIntegrationMetrics:
    """
    Metrics for market integration and price discovery across venues

    Attributes:
        timestamp: Measurement time
        cointegration_coefficient: Cointegration with reference market
        information_share: Contribution to price discovery (0-1)
        lead_lag_relationship: Positive if leads, negative if lags
        price_convergence_rate: Speed of convergence to equilibrium
    """

    timestamp: datetime
    cointegration_coefficient: float
    information_share: float
    lead_lag_relationship: float
    price_convergence_rate: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cointegration_coefficient': self.cointegration_coefficient,
            'information_share': self.information_share,
            'lead_lag_relationship': self.lead_lag_relationship,
            'price_convergence_rate': self.price_convergence_rate,
        }


class PriceDiscoveryAnalyzer:
    """
    Analyzes price discovery and information aggregation

    Implements O'Hara Chapter 7 concepts on price formation
    """

    def __init__(
        self,
        lookback_periods: int = 100,
        min_observations: int = 30,
    ):
        """
        Initialize price discovery analyzer

        Args:
            lookback_periods: Number of periods for analysis
            min_observations: Minimum observations required
        """
        logger.debug(
            "Initializing PriceDiscoveryAnalyzer",
            extra={
                "lookback_periods": lookback_periods,
                "min_observations": min_observations,
            },
        )
        self.lookback_periods = lookback_periods
        self.min_observations = min_observations
        self._historical_errors: list[float] = []

    def estimate_efficient_price_roll(
        self,
        price_history: pd.DataFrame,
    ) -> EfficientPriceEstimate:
        """
        Estimate efficient price using Roll (1984) model

        Roll model: Efficient price follows random walk, observed prices
        have bid-ask bounce

        Pt = Pt* + St/2 * Qt
        Where:
        - Pt* = efficient price
        - St = bid-ask spread
        - Qt = +1 for buy, -1 for sell

        Args:
            price_history: DataFrame with price data
                Columns: ['timestamp', 'close', 'volume']

        Returns:
            EfficientPriceEstimate with Roll model estimate
        """
        logger.debug(
            "Estimating efficient price using Roll model",
            extra={
                "price_history_length": len(price_history),
            },
        )
        if len(price_history) < 2:
            logger.error(
                "Insufficient data for Roll model",
                extra={"price_history_length": len(price_history)},
            )
            raise ValueError("Insufficient data for Roll model")

        prices = price_history['close'].values
        returns = np.diff(np.log(prices))

        # Estimate spread from autocovariance
        # Cov(ΔPt, ΔPt-1) = -S²/4
        autocov = np.cov(returns[1:], returns[:-1])[0, 1]

        if autocov < 0:
            estimatedSpread = 2 * np.sqrt(-autocov)
        else:
            estimatedSpread = 0.0001  # Default spread

        # Efficient price is midpoint
        observed_price = Decimal(str(prices[-1]))
        half_spread = estimatedSpread / 2

        efficient_price = observed_price * Decimal(str(1 - half_spread))
        pricing_error = observed_price - efficient_price

        # Confidence interval
        std_error = np.std(returns) / np.sqrt(len(returns))
        ci_width = Decimal(str(std_error * 1.96))

        logger.info(
            "Efficient price estimated using Roll model",
            extra={
                "observed_price": float(observed_price),
                "efficient_price": float(efficient_price),
                "pricing_error": float(pricing_error),
                "estimated_spread": estimatedSpread,
            },
        )
        return EfficientPriceEstimate(
            timestamp=datetime.now(),
            observed_price=observed_price,
            efficient_price=efficient_price,
            pricing_error=pricing_error,
            confidence_interval=(
                efficient_price - ci_width,
                efficient_price + ci_width,
            ),
            estimation_method="ROLL",
        )

    def calculate_information_share_hasbrouck(
        self,
        price_series: pd.Series,
        trade_series: pd.Series,
    ) -> float:
        """
        Calculate Hasbrouck (1991) information share

        Information share measures how much of the efficient price innovation
        comes from this market/venue

        Args:
            price_series: Price time series
            trade_series: Trade indicator series (+1 buy, -1 sell)

        Returns:
            Information share between 0 and 1
        """
        logger.debug(
            "Calculating Hasbrouck information share",
            extra={
                "price_series_length": len(price_series),
                "trade_series_length": len(trade_series),
            },
        )
        if len(price_series) < self.min_observations:
            logger.warning(
                "Insufficient data for Hasbrouck information share",
                extra={
                    "price_series_length": len(price_series),
                    "min_observations": self.min_observations,
                },
            )
            return 0.5  # Default equal share

        # Vector error correction model (simplified)
        # In full implementation, use VECM from statsmodels

        # Calculate price impact of trades
        price_changes = price_series.diff().dropna()
        trade_impact = np.cov(price_changes, trade_series)[0, 1]

        # Calculate variance of price changes
        price_variance = price_changes.var()

        if price_variance == 0:
            logger.warning(
                "Price variance is zero for Hasbrouck calculation",
                extra={"price_variance": price_variance},
            )
            return 0.5

        # Information share proportional to trade impact
        information_share = min(1.0, max(0.0, abs(trade_impact) / price_variance))

        logger.info(
            "Hasbrouck information share calculated",
            extra={
                "information_share": information_share,
                "trade_impact": trade_impact,
                "price_variance": price_variance,
            },
        )
        return float(information_share)

    def measure_price_adjustment_speed(
        self,
        price_history: pd.DataFrame,
        event_times: list[datetime],
        adjustment_window_seconds: int = 300,
    ) -> float:
        """
        Measure speed of price adjustment to information

        Faster adjustment = more efficient market

        Args:
            price_history: Price history
            event_times: Times of information events
            adjustment_window_seconds: Window to measure adjustment

        Returns:
            Adjustment speed (higher = faster adjustment)
        """
        if price_history.empty or not event_times:
            return 0.0

        adjustment_times = []

        for event_time in event_times:
            # Get pre-event price
            pre_window = price_history[
                (price_history.index >= event_time - timedelta(seconds=60))
                & (price_history.index < event_time)
            ]

            if pre_window.empty:
                continue

            pre_event_price = pre_window['close'].iloc[-1]

            # Get post-event adjustment
            post_window = price_history[
                (price_history.index > event_time)
                & (price_history.index <= event_time + timedelta(seconds=adjustment_window_seconds))
            ]

            if post_window.empty:
                continue

            # Find when price reaches new level (95% of total move)
            total_move = abs(post_window['close'].iloc[-1] - pre_event_price)
            if total_move == 0:
                continue

            target_move = total_move * 0.95

            for idx, row in post_window.iterrows():
                current_move = abs(row['close'] - pre_event_price)
                if current_move >= target_move:
                    adjustment_time = (idx - event_time).total_seconds()
                    adjustment_times.append(adjustment_time)
                    break

        if not adjustment_times:
            return 0.0

        # Adjustment speed: inverse of average time
        avg_time = float(np.mean(adjustment_times))
        speed = 1000 / max(avg_time, 1.0)  # Normalize to 0-100 scale

        return float(min(100, speed))

    def calculate_pricing_error(
        self,
        observed_prices: pd.Series,
        fundamental_value: float,
    ) -> tuple[float, float]:
        """
        Calculate pricing error (deviation from fundamental value)

        Args:
            observed_prices: Observed price series
            fundamental_value: Fundamental value

        Returns:
            Tuple of (mean_pricing_error, std_pricing_error)
        """
        errors = (observed_prices - fundamental_value) / fundamental_value

        mean_error = errors.mean()
        std_error = errors.std()

        return float(mean_error), float(std_error)

    def test_market_efficiency(
        self,
        price_history: pd.DataFrame,
    ) -> MarketEfficiency:
        """
        Test market efficiency level

        Uses multiple tests:
        1. Random walk test (weak form)
        2. Return predictability (semi-strong)
        3. Fundamental deviation (strong)

        Args:
            price_history: Price history

        Returns:
            MarketEfficiency classification
        """
        if len(price_history) < 30:
            return MarketEfficiency.INEFFICIENT

        # Test 1: Random walk (weak form efficiency)
        returns = price_history['close'].pct_change().dropna()

        # Autocorrelation test
        autocorr = returns.autocorr(lag=1)

        # If returns are predictable, not even weak form efficient
        if abs(autocorr) > 0.1:
            return MarketEfficiency.INEFFICIENT

        # Test 2: Variance ratio (more sophisticated weak form test)
        # If market is efficient, variance should scale linearly with time
        if len(returns) >= 20:
            var_1 = returns.var()
            var_5 = returns.rolling(5).sum().var() / 5

            if var_1 > 0:
                variance_ratio = var_5 / var_1
                # Deviations from 1 suggest inefficiency
                if abs(variance_ratio - 1) > 0.3:
                    return MarketEfficiency.INEFFICIENT

        # Test 3: Runs test (non-parametric)
        # Count runs in returns
        signs = np.sign(returns.values)
        runs = 1 + sum(signs[i] != signs[i - 1] for i in range(1, len(signs)))

        # Expected runs under randomness
        n_pos = sum(signs > 0)
        n_neg = sum(signs < 0)
        expected_runs = 1 + 2 * n_pos * n_neg / (n_pos + n_neg)

        # If actual runs differ significantly from expected
        if abs(runs - expected_runs) > 2 * np.sqrt(expected_runs):
            return MarketEfficiency.INEFFICIENT

        # If passed all tests, at least weak form efficient
        # Distinguishing between semi-strong and strong requires more data
        return MarketEfficiency.WEAK_FORM

    def analyze_information_flow(
        self,
        price_history: pd.DataFrame,
        trade_data: pd.DataFrame,
    ) -> InformationFlowMetrics:
        """
        Analyze information flow into prices

        Args:
            price_history: Price history
            trade_data: Trade data with columns: ['timestamp', 'side', 'size', 'price']

        Returns:
            InformationFlowMetrics
        """
        if trade_data.empty:
            return InformationFlowMetrics(
                timestamp=datetime.now(),
                information_content=0.0,
                price_impact=0.0,
                flow_persistence=0.0,
                information_decay_rate=0.0,
            )

        # Calculate price impact of trades
        trade_data['price_change'] = trade_data['price'].pct_change()

        # Trade direction: +1 for buy, -1 for sell
        trade_data['direction'] = np.where(trade_data['side'].str.upper() == 'BUY', 1, -1)

        # Weight by size
        trade_data['signed_flow'] = trade_data['direction'] * trade_data['size']

        # Information content: correlation between order flow and price changes
        if len(trade_data) > 1:
            information_content = abs(trade_data['signed_flow'].corr(trade_data['price_change']))
        else:
            information_content = 0.0

        # Average price impact per unit flow
        if trade_data['size'].sum() > 0:
            price_impact = (
                (abs(trade_data['price_change'].mean()) / trade_data['size'].mean())
                if trade_data['size'].mean() > 0
                else 0.0
            )
        else:
            price_impact = 0.0

        # Flow persistence: autocorrelation of signed flow
        if len(trade_data) > 10:
            flow_persistence = abs(trade_data['signed_flow'].autocorr())
        else:
            flow_persistence = 0.0

        # Information decay: how quickly impact dissipates
        # Estimate from price series autocorrelation
        if len(price_history) > 10:
            returns = price_history['close'].pct_change().dropna()
            decay_rate = 1 - abs(returns.autocorr(lag=1))
        else:
            decay_rate = 0.5

        return InformationFlowMetrics(
            timestamp=datetime.now(),
            information_content=float(information_content),
            price_impact=float(price_impact),
            flow_persistence=float(flow_persistence),
            information_decay_rate=float(max(0, min(1, decay_rate))),
        )

    def compare_markets_price_discovery(
        self,
        market1_prices: pd.Series,
        market2_prices: pd.Series,
    ) -> MarketIntegrationMetrics:
        """
        Compare price discovery across two markets

        Tests cointegration and measures information shares

        Args:
            market1_prices: Prices from market 1
            market2_prices: Prices from market 2

        Returns:
            MarketIntegrationMetrics
        """
        # Ensure same length
        min_len = min(len(market1_prices), len(market2_prices))
        m1 = market1_prices.tail(min_len)
        m2 = market2_prices.tail(min_len)

        # Cointegration test
        try:
            score, pvalue, _ = coint(m1, m2)

            # Cointegration coefficient (beta)
            # From regression: m1 = alpha + beta * m2 + epsilon
            if len(m1) > 1 and len(m2) > 1:
                beta = np.cov(m1, m2)[0, 1] / np.var(m2)
            else:
                beta = 1.0

            cointegrated = pvalue < 0.05

        except Exception:
            cointegrated = False
            beta = 1.0

        # Information share (simplified)
        # In full implementation, use Gonzalo-Granger decomposition
        var1 = m1.pct_change().var()
        var2 = m2.pct_change().var()
        total_var = var1 + var2

        if total_var > 0:
            information_share = var1 / total_var
        else:
            information_share = 0.5

        # Lead-lag relationship
        # Correlate market 1 returns with market 2 lagged returns
        returns1 = m1.pct_change().dropna()
        returns2 = m2.pct_change().dropna()

        if len(returns1) > 2 and len(returns2) > 2:
            corr_leading = returns1.corr(returns2.shift(-1))
            corr_lagging = returns1.corr(returns2.shift(1))

            # Positive if market 1 leads
            lead_lag = corr_leading - corr_lagging
        else:
            lead_lag = 0.0

        # Price convergence rate
        if cointegrated:
            # Error correction speed (simplified)
            convergence = 0.1  # Placeholder
        else:
            convergence = 0.0

        return MarketIntegrationMetrics(
            timestamp=datetime.now(),
            cointegration_coefficient=float(beta),
            information_share=float(information_share),
            lead_lag_relationship=float(lead_lag),
            price_convergence_rate=float(convergence),
        )

    def calculate_discovery_quality_score(
        self,
        information_share: float,
        adjustment_speed: float,
        pricing_error: float,
        efficiency_level: MarketEfficiency,
    ) -> float:
        """
        Calculate composite price discovery quality score

        Args:
            information_share: Hasbrouck information share
            adjustment_speed: Price adjustment speed
            pricing_error: Pricing error magnitude
            efficiency_level: Market efficiency level

        Returns:
            Quality score from 0 to 100
        """
        # Information share score (higher is better)
        info_score = information_share * 40

        # Adjustment speed score (higher is better)
        speed_score = min(40, adjustment_speed * 0.4)

        # Pricing error score (lower error = higher score)
        error_score = max(0, 20 - abs(pricing_error) * 1000)

        # Efficiency bonus
        efficiency_bonus = {
            MarketEfficiency.STRONG_FORM: 10,
            MarketEfficiency.SEMI_STRONG: 8,
            MarketEfficiency.WEAK_FORM: 5,
            MarketEfficiency.INEFFICIENT: 0,
        }.get(efficiency_level, 0)

        total_score = info_score + speed_score + error_score + efficiency_bonus

        return float(min(100, max(0, total_score)))

    def generate_price_discovery_report(
        self,
        symbol: str,
        price_history: pd.DataFrame,
        trade_data: pd.DataFrame | None = None,
    ) -> dict:
        """
        Generate comprehensive price discovery report

        Args:
            symbol: Trading symbol
            price_history: Price history
            trade_data: Optional trade data for analysis

        Returns:
            Dictionary with complete price discovery analysis
        """
        # Estimate efficient price
        efficient_price = self.estimate_efficient_price_roll(price_history)

        # Calculate information share
        if trade_data is not None and not trade_data.empty:
            info_share = self.calculate_information_share_hasbrouck(
                price_history['close'],
                trade_data['size'] * np.where(trade_data['side'] == 'BUY', 1, -1),
            )
        else:
            info_share = 0.5

        # Measure price adjustment speed
        # Simulate event times at large price moves
        if len(price_history) >= 10:
            returns = price_history['close'].pct_change()
            event_times = price_history.index[returns.abs() > returns.std() * 2].tolist()
        else:
            event_times = []

        adjustment_speed = self.measure_price_adjustment_speed(price_history, event_times)

        # Calculate pricing error
        fundamental_value = float(efficient_price.efficient_price)
        if len(price_history) >= 10:
            mean_error, std_error = self.calculate_pricing_error(
                price_history['close'].tail(20), fundamental_value
            )
        else:
            mean_error = 0.0
            std_error = 0.0

        # Test market efficiency
        efficiency_level = self.test_market_efficiency(price_history)

        # Calculate discovery quality score
        quality_score = self.calculate_discovery_quality_score(
            information_share=info_share,
            adjustment_speed=adjustment_speed,
            pricing_error=mean_error,
            efficiency_level=efficiency_level,
        )

        # Analyze information flow
        if trade_data is not None:
            info_flow = self.analyze_information_flow(price_history, trade_data)
        else:
            info_flow = InformationFlowMetrics(
                timestamp=datetime.now(),
                information_content=0.0,
                price_impact=0.0,
                flow_persistence=0.0,
                information_decay_rate=0.0,
            )

        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'efficient_price': efficient_price.to_dict(),
            'information_share': info_share,
            'price_adjustment_speed': adjustment_speed,
            'pricing_error': {
                'mean': mean_error,
                'std': std_error,
            },
            'market_efficiency': efficiency_level.value,
            'discovery_quality_score': quality_score,
            'information_flow': info_flow.to_dict(),
            'recommendations': self._generate_discovery_recommendations(
                efficiency_level, quality_score, info_share
            ),
        }

    def _generate_discovery_recommendations(
        self,
        efficiency_level: MarketEfficiency,
        quality_score: float,
        information_share: float,
    ) -> list[str]:
        """Generate recommendations based on price discovery analysis"""
        recommendations = []

        if efficiency_level == MarketEfficiency.INEFFICIENT:
            recommendations.append("Market appears inefficient - potential arbitrage opportunities")
            recommendations.append("Use caution: inefficiencies may reflect higher risks")

        if quality_score < 50:
            recommendations.append("Poor price discovery quality - execution costs likely high")

        if information_share < 0.3:
            recommendations.append("Low information share - this market lags others")

        if information_share > 0.7:
            recommendations.append("High information share - this market leads price discovery")

        if not recommendations:
            recommendations.append("Normal price discovery conditions")

        return recommendations


class PriceDiscoveryMonitor:
    """
    Monitors price discovery in real-time

    Tracks how efficiently prices incorporate new information
    """

    def __init__(
        self,
        efficiency_threshold: float = 50.0,
    ):
        """
        Initialize price discovery monitor

        Args:
            efficiency_threshold: Threshold for discovery quality alert
        """
        self.efficiency_threshold = efficiency_threshold
        self._historical_scores: list[tuple[datetime, float]] = []

    def check_discovery_quality(
        self,
        current_score: float,
    ) -> dict | None:
        """
        Check if discovery quality alert should be triggered

        Args:
            current_score: Current discovery quality score

        Returns:
            Alert dictionary or None
        """
        if current_score < self.efficiency_threshold:
            return {
                'type': 'LOW_DISCOVERY_QUALITY',
                'severity': 'HIGH' if current_score < 30 else 'MEDIUM',
                'message': f"Price discovery quality ({current_score:.1f}) below threshold ({self.efficiency_threshold})",
                'timestamp': datetime.now().isoformat(),
            }

        return None

    def get_discovery_trend(self) -> str:
        """
        Get trend in price discovery quality

        Returns:
            Trend direction
        """
        if len(self._historical_scores) < 5:
            return 'UNKNOWN'

        recent = [score for _, score in self._historical_scores[-5:]]
        older = [score for _, score in self._historical_scores[:-5]]

        if not older:
            return 'STABLE'

        recent_avg = float(np.mean(recent))
        older_avg = float(np.mean(older))
        change = (recent_avg - older_avg) / max(older_avg, 1.0)

        if change > 0.05:
            return 'IMPROVING'
        elif change < -0.05:
            return 'DETERIORATING'
        else:
            return 'STABLE'


# Singleton instances
_price_discovery_analyzer: PriceDiscoveryAnalyzer | None = None
_price_discovery_monitor: PriceDiscoveryMonitor | None = None


def get_price_discovery_analyzer(
    lookback_periods: int = 100,
    min_observations: int = 30,
) -> PriceDiscoveryAnalyzer:
    """Get or create singleton PriceDiscoveryAnalyzer instance"""
    global _price_discovery_analyzer
    if _price_discovery_analyzer is None:
        _price_discovery_analyzer = PriceDiscoveryAnalyzer(
            lookback_periods=lookback_periods,
            min_observations=min_observations,
        )
    return _price_discovery_analyzer


def get_price_discovery_monitor(
    efficiency_threshold: float = 50.0,
) -> PriceDiscoveryMonitor:
    """Get or create singleton PriceDiscoveryMonitor instance"""
    global _price_discovery_monitor
    if _price_discovery_monitor is None:
        _price_discovery_monitor = PriceDiscoveryMonitor(
            efficiency_threshold=efficiency_threshold,
        )
    return _price_discovery_monitor


__all__ = [
    "PriceDiscoveryModel",
    "MarketEfficiency",
    "PriceDiscoveryMetrics",
    "EfficientPriceEstimate",
    "InformationFlowMetrics",
    "MarketIntegrationMetrics",
    "PriceDiscoveryAnalyzer",
    "PriceDiscoveryMonitor",
    "get_price_discovery_analyzer",
    "get_price_discovery_monitor",
]
