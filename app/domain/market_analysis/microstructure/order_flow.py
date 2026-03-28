"""
Order Flow and Information Analysis Module

This module implements order flow modeling and information asymmetry concepts
from Maureen O'Hara's "Market Microstructure Theory" (Chapter 3-4).

Key Concepts:
- Order flow modeling and prediction
- Information asymmetry measurement
- Adverse selection risk assessment
- Informed vs uninformed trader behavior

References:
- O'Hara, M. (1995) "Market Microstructure Theory", Chapters 3-4
- Glosten, L.R., & Milgrom, P.R. (1985) "Bid, Ask and Transaction Prices"
- Easley, D., et al. (1996) "Liquidity, Information, and Infrequently Traded Stocks"
"""
from __future__ import annotations  # Enable Python 3.10+ union syntax in Python 3.9

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

import numpy as np
import pandas as pd

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)

# mypy: ignore-errors


class OrderType(Enum):
    """Order type classification"""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    ICEBERG = "ICEBERG"


class OrderSide(Enum):
    """Order side classification"""

    BUY = "BUY"
    SELL = "SELL"


class TraderType(Enum):
    """Trader type classification based on information"""

    INFORMED = "INFORMED"  # Trades with private information
    UNINFORMED = "UNINFORMED"  # Trades for liquidity reasons
    NOISE = "NOISE"  # Random trades


@dataclass
class Order:
    """
    Represents a single order in the order flow

    Attributes:
        order_id: Unique order identifier
        timestamp: Order submission time
        side: Buy or sell
        order_type: Market, limit, stop, etc.
        price: Limit price (None for market orders)
        size: Order quantity
        trader_type: Inferred trader type
    """

    order_id: str
    timestamp: datetime
    side: OrderSide
    order_type: OrderType
    price: Decimal | None
    size: Decimal
    trader_type: TraderType | None = None

    def __post_init__(self):
        if isinstance(self.side, str):
            self.side = OrderSide(self.side)
        if isinstance(self.order_type, str):
            self.order_type = OrderType(self.order_type)
        if isinstance(self.trader_type, str):
            self.trader_type = TraderType(self.trader_type)


@dataclass
class OrderFlowSnapshot:
    """
    Order flow state at a point in time

    Attributes:
        timestamp: Snapshot time
        buy_volume: Total buy volume
        sell_volume: Total sell volume
        buy_count: Number of buy orders
        sell_count: Number of sell orders
        order_imbalance: Net order flow (-1 to +1)
    """

    timestamp: datetime
    buy_volume: Decimal
    sell_volume: Decimal
    buy_count: int
    sell_count: int
    order_imbalance: Decimal = field(init=False)

    def __post_init__(self):
        total = self.buy_volume + self.sell_volume
        if total > 0:
            self.order_imbalance = (self.buy_volume - self.sell_volume) / total
        else:
            self.order_imbalance = Decimal('0')


@dataclass
class InformationAsymmetryMetrics:
    """
    Metrics for information asymmetry in the market

    Attributes:
        timestamp: Measurement time
        probability_of_informed_trading: PIN score (0-1)
        order_flow_toxicity: Toxicity score (0-1)
        informed_trader_intensity: Rate of informed trading
        information asymmetry_index: Composite asymmetry measure
        adverse_selection_risk: Risk level (LOW/MEDIUM/HIGH)
    """

    timestamp: datetime
    probability_of_informed_trading: float
    order_flow_toxicity: float
    informed_trader_intensity: float
    information_asymmetry_index: float
    adverse_selection_risk: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'probability_of_informed_trading': self.probability_of_informed_trading,
            'order_flow_toxicity': self.order_flow_toxicity,
            'informed_trader_intensity': self.informed_trader_intensity,
            'information_asymmetry_index': self.information_asymmetry_index,
            'adverse_selection_risk': self.adverse_selection_risk,
        }


@dataclass
class OrderFlowForecast:
    """
    Forecast of future order flow

    Attributes:
        forecast_time: Time for forecast
        expected_buy_volume: Expected buy volume
        expected_sell_volume: Expected sell volume
        expected_imbalance: Expected order imbalance
        confidence_interval: 95% confidence interval
        forecast_method: Method used for forecasting
    """

    forecast_time: datetime
    expected_buy_volume: Decimal
    expected_sell_volume: Decimal
    expected_imbalance: Decimal
    confidence_interval: tuple[Decimal, Decimal]
    forecast_method: str


class OrderFlowAnalyzer:
    """
    Analyzes order flow dynamics and information content

    Implements concepts from O'Hara Chapter 3:
    - Order flow as a source of information
    - Information-based trading
    - Adverse selection
    """

    def __init__(
        self,
        lookback_seconds: int = 300,
        alpha_threshold: float = 0.3,
    ):
        """
        Initialize order flow analyzer

        Args:
            lookback_seconds: Lookback period for analysis (default 5 min)
            alpha_threshold: Threshold for high informed trading probability
        """
        self.lookback_seconds = lookback_seconds
        self.alpha_threshold = alpha_threshold
        self._order_history: list[Order] = []
        logger.info(
            "OrderFlowAnalyzer initialized",
            extra={"lookback_seconds": lookback_seconds, "alpha_threshold": alpha_threshold},
        )

    def add_order(self, order: Order) -> None:
        """Add an order to the history"""
        self._order_history.append(order)
        # Keep only recent orders
        cutoff = datetime.now() - timedelta(seconds=self.lookback_seconds * 2)
        self._order_history = [o for o in self._order_history if o.timestamp > cutoff]
        logger.debug(
            "Order added to history",
            extra={
                "order_id": order.order_id,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "size": str(order.size),
                "history_size": len(self._order_history),
            },
        )

    def calculate_order_imbalance(self, window_seconds: int | None = None) -> Decimal:
        """
        Calculate current order flow imbalance

        Order imbalance is a key predictor of price movements (O'Hara 3.2)

        Args:
            window_seconds: Time window for calculation (default: lookback_seconds)

        Returns:
            Order imbalance from -1 (all sells) to +1 (all buys)
        """
        window = window_seconds or self.lookback_seconds
        cutoff = datetime.now() - timedelta(seconds=window)

        recent_orders = [o for o in self._order_history if o.timestamp > cutoff]

        if not recent_orders:
            return Decimal('0')

        buy_volume = sum(o.size for o in recent_orders if o.side == OrderSide.BUY)
        sell_volume = sum(o.size for o in recent_orders if o.side == OrderSide.SELL)

        total = buy_volume + sell_volume
        if total == 0:
            return Decimal('0')

        return (buy_volume - sell_volume) / total

    def estimate_order_flow_toxicity(
        self,
        recent_trades: pd.DataFrame,
        price_changes: pd.Series,
    ) -> float:
        """
        Estimate order flow toxicity (Easley et al. model)

        Toxic order flow is associated with informed traders who trade
        in the direction of future price movements.

        Args:
            recent_trades: DataFrame with trade data
                Columns: ['timestamp', 'side', 'size', 'price']
            price_changes: Series of price changes after each trade

        Returns:
            Toxicity score from 0 (benign) to 1 (highly toxic)
        """
        logger.debug(
            "Estimating order flow toxicity",
            extra={"num_trades": len(recent_trades), "num_price_changes": len(price_changes)},
        )
        if recent_trades.empty:
            logger.debug("Empty trades data, returning toxicity 0.0")
            return 0.0

        # Calculate correlation between order flow and price changes
        # Buy orders coded as +1, sell as -1
        flow_direction = np.where(recent_trades['side'].str.upper() == 'BUY', 1, -1)

        # Weight by trade size
        weighted_flow = flow_direction * recent_trades['size'].values

        # Normalize
        if len(weighted_flow) > 0 and weighted_flow.std() > 0:
            normalized_flow = (weighted_flow - weighted_flow.mean()) / weighted_flow.std()
        else:
            return 0.0

        # Align price changes
        aligned_changes = price_changes.values[: len(normalized_flow)]

        if len(aligned_changes) != len(normalized_flow):
            return 0.0

        # Toxicity is positive correlation between order flow and price changes
        correlation = np.corrcoef(normalized_flow, aligned_changes)[0, 1]

        # Map correlation to 0-1 scale
        toxicity = max(0, correlation)

        logger.info(
            "Order flow toxicity calculated",
            extra={"toxicity": float(toxicity), "correlation": float(correlation)},
        )

        return float(toxicity)

    def calculate_probability_of_informed_trading(
        self,
        order_snapshots: list[OrderFlowSnapshot],
        price_volatility: float,
    ) -> float:
        """
        Calculate PIN (Probability of INformed Trading)

        Based on the Easley et al. (1996) model:
        PIN = α * μ / (α * μ + ε_s + ε_b)

        Where:
        - α = probability of information event
        - μ = arrival rate of informed traders
        - ε = arrival rate of uninformed traders

        Args:
            order_snapshots: Historical order flow snapshots
            price_volatility: Current price volatility

        Returns:
            PIN score between 0 and 1
        """
        if len(order_snapshots) < 10:
            return 0.0

        # Estimate parameters from order flow data
        # Use order imbalance variance as proxy for information events

        imbalances = [float(s.order_imbalance) for s in order_snapshots]

        if not imbalances:
            return 0.0

        # High variance in order imbalance suggests information events
        imbalance_variance = np.var(imbalances)
        mean_absolute_imbalance = np.mean([abs(x) for x in imbalances])

        # Estimate components
        # α (alpha) - probability of information event
        alpha = min(1.0, imbalance_variance * 10)

        # μ (mu) - informed trader arrival rate
        mu = mean_absolute_imbalance * price_volatility * 100

        # ε (epsilon) - uninformed trader arrival
        epsilon_b = 1.0  # Normalized buy pressure
        epsilon_s = 1.0  # Normalized sell pressure

        # Calculate PIN
        numerator = alpha * mu
        denominator = alpha * mu + epsilon_b + epsilon_s

        if denominator == 0:
            return 0.0

        pin = numerator / denominator

        return float(min(1.0, max(0.0, pin)))

    def detect_informed_trading(
        self,
        current_orders: list[Order],
        price_history: pd.DataFrame,
    ) -> tuple[bool, float, str]:
        """
        Detect presence of informed trading in current order flow

        Args:
            current_orders: Recent orders to analyze
            price_history: Recent price history

        Returns:
            Tuple of (is_detected, confidence, explanation)
        """
        logger.debug(
            "Detecting informed trading",
            extra={"num_orders": len(current_orders), "price_history_length": len(price_history)},
        )
        if not current_orders or price_history.empty:
            logger.debug("Insufficient data for informed trading detection")
            return False, 0.0, "Insufficient data"

        # Calculate order imbalance
        buy_volume = sum(o.size for o in current_orders if o.side == OrderSide.BUY)
        sell_volume = sum(o.size for o in current_orders if o.side == OrderSide.SELL)

        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return False, 0.0, "No volume"

        imbalance = float((buy_volume - sell_volume) / total_volume)

        # Calculate price momentum
        returns = price_history['close'].pct_change().dropna()
        if len(returns) < 5:
            return False, 0.0, "Insufficient price history"

        momentum = returns.tail(5).mean()

        # Informed trading: order imbalance aligns with price momentum
        # and shows significant deviation from normal
        if abs(imbalance) > 0.3:  # Significant imbalance
            # Check if imbalance aligns with price direction
            alignment = (imbalance > 0 and momentum > 0) or (imbalance < 0 and momentum < 0)

            if alignment:
                confidence = min(1.0, abs(imbalance) * 2)
                logger.info(
                    "Informed trading detected",
                    extra={
                        "confidence": confidence,
                        "imbalance": imbalance,
                        "momentum": float(momentum),
                        "explanation": f"Order flow ({imbalance:+.2f}) aligns with price momentum ({momentum:+.4f})",
                    },
                )
                return (
                    True,
                    confidence,
                    f"Order flow ({imbalance:+.2f}) aligns with price momentum ({momentum:+.4f})",
                )

        logger.debug("No informed trading detected")
        return False, 0.0, "No informed trading detected"

    def measure_adverse_selection_cost(
        self,
        executions: pd.DataFrame,
        subsequent_prices: pd.Series,
    ) -> dict[str, float]:
        """
        Measure cost of adverse selection

        Adverse selection occurs when market makers trade against
        better-informed traders, resulting in losses.

        Args:
            executions: DataFrame with execution data
                Columns: ['timestamp', 'side', 'price', 'size']
            subsequent_prices: Prices after each execution

        Returns:
            Dictionary with adverse selection metrics
        """
        logger.debug(
            "Measuring adverse selection cost",
            extra={"num_executions": len(executions), "num_prices": len(subsequent_prices)},
        )
        if executions.empty or subsequent_prices.empty:
            logger.debug("Empty data, returning zero adverse selection metrics")
            return {
                'avg_adverse_cost_bps': 0.0,
                'adverse_selection_rate': 0.0,
                'total_adverse_cost_usd': 0.0,
            }

        adverse_costs = []
        adverse_count = 0
        total_cost = 0.0

        for idx, exec_row in executions.iterrows():
            exec_price = exec_row['price']
            exec_side = exec_row['side']
            exec_size = exec_row['size']

            # Get subsequent price (next period)
            if idx >= len(subsequent_prices):
                break

            future_price = subsequent_prices.iloc[idx]

            # Calculate adverse cost
            # For buys: adverse if price goes down after
            # For sells: adverse if price goes up after
            if exec_side.upper() == 'BUY':
                price_move = (exec_price - future_price) / exec_price
                if price_move > 0:  # Price went down - adverse
                    cost = price_move * float(exec_size) * exec_price
                    adverse_costs.append(abs(price_move))
                    total_cost += cost
                    adverse_count += 1
            else:  # SELL
                price_move = (future_price - exec_price) / exec_price
                if price_move > 0:  # Price went up - adverse
                    cost = price_move * float(exec_size) * exec_price
                    adverse_costs.append(abs(price_move))
                    total_cost += cost
                    adverse_count += 1

        if not adverse_costs:
            logger.debug("No adverse costs found")
            return {
                'avg_adverse_cost_bps': 0.0,
                'adverse_selection_rate': 0.0,
                'total_adverse_cost_usd': 0.0,
            }

        result = {
            'avg_adverse_cost_bps': np.mean(adverse_costs) * 10000,
            'adverse_selection_rate': adverse_count / len(executions),
            'total_adverse_cost_usd': total_cost,
        }
        logger.info("Adverse selection cost measured", extra=result)
        return result

    def forecast_order_flow(
        self,
        forecast_horizon_seconds: int = 60,
        method: str = "exponential_smoothing",
    ) -> OrderFlowForecast:
        """
        Forecast future order flow

        Implements multiple forecasting methods:
        - exponential_smoothing: EWM with decay
        - linear_regression: Trend extrapolation
        - markov_chain: State transition model

        Args:
            forecast_horizon_seconds: Time horizon for forecast
            method: Forecasting method to use

        Returns:
            OrderFlowForecast with predictions
        """
        logger.debug(
            "Forecasting order flow",
            extra={"horizon_seconds": forecast_horizon_seconds, "method": method},
        )
        if len(self._order_history) < 10:
            # Not enough data, return neutral forecast
            logger.warning(
                "Insufficient order history for forecasting",
                extra={"history_size": len(self._order_history), "required_min": 10},
            )
            now = datetime.now()
            future = now + timedelta(seconds=forecast_horizon_seconds)
            return OrderFlowForecast(
                forecast_time=future,
                expected_buy_volume=Decimal('0'),
                expected_sell_volume=Decimal('0'),
                expected_imbalance=Decimal('0'),
                confidence_interval=(Decimal('0'), Decimal('0')),
                forecast_method="insufficient_data",
            )

        # Create time series of order snapshots
        snapshot_times = []
        buy_volumes = []
        sell_volumes = []

        # Group orders by time windows
        window_size = 10  # 10 second windows
        now = datetime.now()

        for i in range(0, self.lookback_seconds, window_size):
            window_start = now - timedelta(seconds=self.lookback_seconds - i)
            window_end = window_start + timedelta(seconds=window_size)

            window_orders = [
                o for o in self._order_history if window_start <= o.timestamp < window_end
            ]

            buy_vol = sum(o.size for o in window_orders if o.side == OrderSide.BUY)
            sell_vol = sum(o.size for o in window_orders if o.side == OrderSide.SELL)

            snapshot_times.append(i)
            buy_volumes.append(float(buy_vol))
            sell_volumes.append(float(sell_vol))

        if method == "exponential_smoothing":
            # Exponential smoothing forecast
            buy_forecast = buy_volumes[-1]  # Simple: use last value
            sell_forecast = sell_volumes[-1]

            # Trend adjustment
            if len(buy_volumes) >= 3:
                buy_trend = (buy_volumes[-1] - buy_volumes[-3]) / 2
                sell_trend = (sell_volumes[-1] - sell_volumes[-3]) / 2

                buy_forecast = buy_volumes[-1] + buy_trend * (
                    forecast_horizon_seconds / window_size
                )
                sell_forecast = sell_volumes[-1] + sell_trend * (
                    forecast_horizon_seconds / window_size
                )

        elif method == "linear_regression":
            # Simple linear regression
            if len(snapshot_times) >= 2:
                buy_coef = np.polyfit(snapshot_times, buy_volumes, 1)
                sell_coef = np.polyfit(snapshot_times, sell_volumes, 1)

                future_time = snapshot_times[-1] + forecast_horizon_seconds
                buy_forecast = buy_coef[0] * future_time + buy_coef[1]
                sell_forecast = sell_coef[0] * future_time + sell_coef[1]
            else:
                buy_forecast = buy_volumes[-1]
                sell_forecast = sell_volumes[-1]

        else:  # Default to simple average
            buy_forecast = np.mean(buy_volumes[-5:])
            sell_forecast = np.mean(sell_volumes[-5:])

        # Ensure non-negative
        buy_forecast = max(0, buy_forecast)
        sell_forecast = max(0, sell_forecast)

        # Calculate expected imbalance
        total = buy_forecast + sell_forecast
        if total > 0:
            expected_imbalance = (buy_forecast - sell_forecast) / total
        else:
            expected_imbalance = 0.0

        # Confidence interval (simplified)
        std = np.std([b - s for b, s in zip(buy_volumes, sell_volumes)])
        ci_width = std * 1.96  # 95% CI

        future_time = now + timedelta(seconds=forecast_horizon_seconds)

        logger.info(
            "Order flow forecast completed",
            extra={
                "forecast_time": future_time.isoformat(),
                "expected_buy_volume": float(buy_forecast),
                "expected_sell_volume": float(sell_forecast),
                "expected_imbalance": expected_imbalance,
                "method": method,
            },
        )

        return OrderFlowForecast(
            forecast_time=future_time,
            expected_buy_volume=Decimal(str(buy_forecast)),
            expected_sell_volume=Decimal(str(sell_forecast)),
            expected_imbalance=Decimal(str(expected_imbalance)),
            confidence_interval=(
                Decimal(str(max(-1, expected_imbalance - ci_width))),
                Decimal(str(min(1, expected_imbalance + ci_width))),
            ),
            forecast_method=method,
        )

    def calculate_information_content(
        self,
        orders: list[Order],
        market_price: Decimal,
    ) -> dict[str, float]:
        """
        Calculate information content of order flow

        Measures how much information orders contain about future prices.
        Based on O'Hara's analysis of information asymmetry.

        Args:
            orders: Orders to analyze
            market_price: Current market price

        Returns:
            Dictionary with information metrics
        """
        if not orders:
            return {
                'information_content': 0.0,
                'signal_to_noise_ratio': 0.0,
                'information_quality': 'LOW',
            }

        # Separate by order type
        market_orders = [o for o in orders if o.order_type == OrderType.MARKET]
        limit_orders = [o for o in orders if o.order_type == OrderType.LIMIT]

        # Market orders contain more information (trade immediacy)
        market_volume = sum(o.size for o in market_orders)
        limit_volume = sum(o.size for o in limit_orders)

        total_volume = market_volume + limit_volume
        if total_volume == 0:
            return {
                'information_content': 0.0,
                'signal_to_noise_ratio': 0.0,
                'information_quality': 'LOW',
            }

        # Information content: market orders are more informative
        information_content = float(market_volume / total_volume)

        # Signal-to-noise: order imbalance relative to total volume
        buy_volume = sum(o.size for o in orders if o.side == OrderSide.BUY)
        sell_volume = sum(o.size for o in orders if o.side == OrderSide.SELL)

        signal = abs(float(buy_volume - sell_volume))
        noise = float(total_volume)

        if noise > 0:
            snr = signal / noise
        else:
            snr = 0.0

        # Information quality classification
        if information_content > 0.7 and snr > 0.3:
            quality = 'HIGH'
        elif information_content > 0.4 and snr > 0.15:
            quality = 'MEDIUM'
        else:
            quality = 'LOW'

        return {
            'information_content': information_content,
            'signal_to_noise_ratio': snr,
            'information_quality': quality,
        }

    def generate_order_flow_report(
        self,
        current_orders: list[Order],
        price_history: pd.DataFrame,
    ) -> dict:
        """
        Generate comprehensive order flow analysis report

        Args:
            current_orders: Current order flow to analyze
            price_history: Price history for context

        Returns:
            Dictionary with complete order flow analysis
        """
        logger.info(
            "Generating order flow report",
            extra={"num_orders": len(current_orders), "price_history_length": len(price_history)},
        )
        # Add orders to history
        for order in current_orders:
            self.add_order(order)

        # Calculate metrics
        imbalance = self.calculate_order_imbalance()

        # Detect informed trading
        is_informed, confidence, explanation = self.detect_informed_trading(
            current_orders, price_history
        )

        # Calculate information content
        info_metrics = self.calculate_information_content(
            current_orders,
            (
                Decimal(str(price_history['close'].iloc[-1]))
                if not price_history.empty
                else Decimal('0')
            ),
        )

        # Forecast order flow
        forecast = self.forecast_order_flow()

        # Determine risk level
        if imbalance > 0.4 or imbalance < -0.4:
            risk_level = 'HIGH'
        elif imbalance > 0.2 or imbalance < -0.2:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        report = {
            'timestamp': datetime.now().isoformat(),
            'order_imbalance': float(imbalance),
            'informed_trading_detected': is_informed,
            'informed_trading_confidence': confidence,
            'informed_trading_explanation': explanation,
            'information_content': info_metrics['information_content'],
            'signal_to_noise_ratio': info_metrics['signal_to_noise_ratio'],
            'information_quality': info_metrics['information_quality'],
            'forecast_imbalance': float(forecast.expected_imbalance),
            'forecast_time': forecast.forecast_time.isoformat(),
            'adverse_selection_risk': risk_level,
            'recommendations': self._generate_recommendations(imbalance, is_informed, info_metrics),
        }
        logger.info(
            "Order flow report generated",
            extra={
                "order_imbalance": float(imbalance),
                "informed_trading_detected": is_informed,
                "risk_level": risk_level,
            },
        )
        return report

    def _generate_recommendations(
        self,
        imbalance: float,
        is_informed: bool,
        info_metrics: dict,
    ) -> list[str]:
        """Generate trading recommendations based on order flow analysis"""
        recommendations = []

        if is_informed:
            recommendations.append("DECREASE trading size - informed traders detected")
            recommendations.append("Use LIMIT orders to avoid adverse selection")

        if abs(imbalance) > 0.4:
            recommendations.append(
                f"Order imbalance extreme ({imbalance:+.2f}) - expect volatility"
            )

        if info_metrics['information_content'] > 0.7:
            recommendations.append("High information content - market likely to move")

        if info_metrics['signal_to_noise_ratio'] < 0.1:
            recommendations.append("Low signal-to-noise - weak trading signals")

        if not recommendations:
            recommendations.append("Normal order flow conditions")

        return recommendations


class OrderFlowSimulator:
    """
    Simulates order flow for testing and strategy development

    Based on O'Hara's models of order arrival processes
    """

    def __init__(
        self,
        informed_trader_probability: float = 0.2,
        information_event_probability: float = 0.05,
    ):
        """
        Initialize order flow simulator

        Args:
            informed_trader_probability: Probability trader is informed
            information_event_probability: Probability of information event
        """
        self.informed_trader_probability = informed_trader_probability
        self.info_event_probability = information_event_probability
        self.current_info_direction = None  # +1 for positive info, -1 for negative
        logger.info(
            "OrderFlowSimulator initialized",
            extra={
                "informed_trader_probability": informed_trader_probability,
                "information_event_probability": information_event_probability,
            },
        )

    def generate_order_flow(
        self,
        num_orders: int,
        base_price: float,
        price_impact: float = 0.001,
        spread_bps: float = None,
    ) -> list[Order]:
        """
        Generate simulated order flow

        Args:
            num_orders: Number of orders to generate
            base_price: Base price for orders
            price_impact: Price impact per order
            spread_bps: Bid-ask spread in bps (uses config if None)

        Returns:
            List of simulated orders
        """
        logger.debug(
            "Generating simulated order flow",
            extra={"num_orders": num_orders, "base_price": base_price},
        )
        # Get default spread from config if not provided
        if spread_bps is None:
            config = get_config()
            spread_bps = float(config.compliance.ESTIMATED_SPREAD_BPS)

        orders = []
        current_time = datetime.now()

        spread = base_price * spread_bps / 10000

        for i in range(num_orders):
            # Determine if information event occurs
            if np.random.random() < self.info_event_probability:
                self.current_info_direction = np.random.choice([1, -1])

            # Determine trader type
            if np.random.random() < self.informed_trader_probability:
                trader_type = TraderType.INFORMED
            else:
                trader_type = TraderType.UNINFORMED

            # Determine order side
            if trader_type == TraderType.INFORMED and self.current_info_direction:
                # Informed traders trade in direction of information
                side = OrderSide.BUY if self.current_info_direction > 0 else OrderSide.SELL
                order_type = OrderType.MARKET  # Informed traders use market orders
            else:
                # Uninformed traders random
                side = np.random.choice([OrderSide.BUY, OrderSide.SELL])
                order_type = np.random.choice(
                    [OrderType.LIMIT, OrderType.LIMIT, OrderType.MARKET],  # Fewer market orders
                    p=[0.6, 0.3, 0.1],
                )

            # Determine price
            if order_type == OrderType.MARKET:
                price = None  # Market orders
            else:
                # Limit orders placed within spread
                if side == OrderSide.BUY:
                    price = base_price - spread * np.random.uniform(0.1, 0.9)
                else:
                    price = base_price + spread * np.random.uniform(0.1, 0.9)

            # Determine size (log-normal distribution)
            size = Decimal(str(int(np.random.lognormal(7, 1))))  # Mean ~1000 shares

            order = Order(
                order_id=f"sim_{i}",
                timestamp=current_time + timedelta(milliseconds=i * 100),
                side=side,
                order_type=order_type,
                price=Decimal(str(price)) if price else None,
                size=size,
                trader_type=trader_type,
            )

            orders.append(order)

        logger.info("Order flow simulation completed", extra={"num_orders_generated": len(orders)})

        return orders


# Singleton instances
_order_flow_analyzer: OrderFlowAnalyzer | None = None
_order_flow_simulator: OrderFlowSimulator | None = None


def get_order_flow_analyzer(
    lookback_seconds: int = 300,
    alpha_threshold: float = 0.3,
) -> OrderFlowAnalyzer:
    """Get or create singleton OrderFlowAnalyzer instance"""
    global _order_flow_analyzer
    if _order_flow_analyzer is None:
        _order_flow_analyzer = OrderFlowAnalyzer(
            lookback_seconds=lookback_seconds,
            alpha_threshold=alpha_threshold,
        )
    return _order_flow_analyzer


def get_order_flow_simulator(
    informed_trader_probability: float = 0.2,
    information_event_probability: float = 0.05,
) -> OrderFlowSimulator:
    """Get or create singleton OrderFlowSimulator instance"""
    global _order_flow_simulator
    if _order_flow_simulator is None:
        _order_flow_simulator = OrderFlowSimulator(
            informed_trader_probability=informed_trader_probability,
            information_event_probability=information_event_probability,
        )
    return _order_flow_simulator


__all__ = [
    "OrderType",
    "OrderSide",
    "TraderType",
    "Order",
    "OrderFlowSnapshot",
    "InformationAsymmetryMetrics",
    "OrderFlowForecast",
    "OrderFlowAnalyzer",
    "OrderFlowSimulator",
    "get_order_flow_analyzer",
    "get_order_flow_simulator",
]
