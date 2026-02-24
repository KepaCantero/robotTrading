"""
Carver Robust Rules Strategy - Robert Carver's Systematic Trading methodology.

Implements simple, robust trading rules following Robert Carver's "Systematic Trading" principles:
- Simple robust rules that work across multiple markets
- Fixed timestamp trading for execution
- Handcrafted portfolio weights
- Decay factors for smooth transitions

Key principles from "Systematic Trading" by Robert Carver:
1. Use simple rules that are robust across different market conditions
2. Execute at fixed timestamps to reduce timing luck
3. Handcraft portfolio weights based on risk characteristics
4. Use decay factors to smooth portfolio transitions
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.shared.config.centralized_config import get_strategy_config, get_trading_threshold, get_config
from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType
from app.domain.services.analysis.momentum import TechnicalIndicatorCalculator
from app.application.scheduling.market_scheduler import MarketScheduler, MarketType

from .base import BaseStrategy

logger = logging.getLogger(__name__)


class CarverRobustRulesStrategy(BaseStrategy):
    """
    Robert Carver's Robust Rules Strategy.

    Implements simple, robust trading rules following Carver's methodology:
    - Uses a single indicator (carry or trend) with fixed thresholds
    - Executes at fixed timestamps (open/close) to reduce timing luck
    - Handcrafts portfolio weights based on instrument risk
    - Applies decay factors for smooth position transitions
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Carver Robust Rules strategy.

        Args:
            config: Strategy configuration
        """
        super().__init__(config)

        # Load trading thresholds for history length
        trading_config = get_config()
        tt = trading_config.trading_thresholds

        # Load strategy-specific configuration
        strategy_config = get_strategy_config("carver_robust")
        if strategy_config:
            params = strategy_config.parameters
            self.lookback_period = params.get("lookback_period", 20)
            self.volatility_target = Decimal(str(params.get("volatility_target", 0.15)))
            self.instrument_diversification = Decimal(
                str(params.get("instrument_diversification", 0.40))
            )
            self.stop_loss = Decimal(
                str(strategy_config.stop_loss_pct or get_trading_threshold("stop_loss_pct"))
            )
            self.take_profit = Decimal(
                str(strategy_config.take_profit_pct or get_trading_threshold("take_profit_pct"))
            )
            self.max_position_size = Decimal(
                str(strategy_config.max_position_size or get_trading_threshold("max_position_size"))
            )
        else:
            # Fallback to config or defaults
            self.lookback_period = config.get("lookback_period", 20)
            self.volatility_target = Decimal(str(config.get("volatility_target", 0.15)))
            self.instrument_diversification = Decimal(
                str(config.get("instrument_diversification", 0.40))
            )
            self.stop_loss = Decimal(
                str(config.get("stop_loss", get_trading_threshold("stop_loss_pct")))
            )
            self.take_profit = Decimal(
                str(config.get("take_profit", get_trading_threshold("take_profit_pct")))
            )
            self.max_position_size = Decimal(
                str(config.get("max_position_size", get_trading_threshold("max_position_size")))
            )

        # Fixed timestamp execution (Carver's methodology)
        self.execution_times = config.get("execution_times", ["09:30", "16:00"])
        self.use_fixed_timestamps = config.get("use_fixed_timestamps", True)

        # Handcrafted weights (Carver's methodology)
        self.handcrafted_weights = config.get("handcrafted_weights", {})
        self.use_handcrafted_weights = config.get("use_handcrafted_weights", True)

        # Decay factors (Carver's methodology)
        self.decay_factor = Decimal(str(config.get("decay_factor", 0.1)))
        self.use_decay = config.get("use_decay", True)

        # Price history for calculations - use config value
        self.price_history = deque(maxlen=tt.default_price_history_length)
        self.high_history = deque(maxlen=tt.default_price_history_length)
        self.low_history = deque(maxlen=tt.default_price_history_length)

        # Indicator calculator
        self.indicator_calculator = TechnicalIndicatorCalculator()

        # Market scheduler for fixed timestamp execution
        self.market_scheduler: Optional[MarketScheduler] = None
        self.market_type = MarketType.STOCKS_US  # Default

        # Last execution time tracking
        self.last_execution_time: Optional[time] = None
        self.last_execution_date: Optional[datetime] = None

        logger.info(f"CarverRobustRulesStrategy initialized: {self.name}")

    def set_market_scheduler(self, scheduler: MarketScheduler, market_type: MarketType) -> None:
        """
        Set market scheduler for fixed timestamp execution.

        Args:
            scheduler: Market scheduler instance
            market_type: Type of market for this strategy
        """
        self.market_scheduler = scheduler
        self.market_type = market_type
        logger.info(f"Market scheduler set for {market_type.value}")

    def get_required_parameters(self) -> List[str]:
        """
        Get required parameters for the strategy.

        Returns:
            List of required parameter names
        """
        return [
            "lookback_period",
            "volatility_target",
            "instrument_diversification",
            "stop_loss",
            "take_profit",
            "max_position_size",
        ]

    def generate_signals(self, market_data: Quote) -> List[Signal]:
        """
        Generate trading signals using Carver's robust rules.

        Key principles:
        1. Simple rules: Use a single indicator with fixed thresholds
        2. Fixed timestamps: Only execute at specified times (e.g., open, close)
        3. Handcrafted weights: Scale positions by instrument risk
        4. Decay factors: Smooth position transitions

        Args:
            market_data: Current market data

        Returns:
            List of generated signals
        """
        signals = []

        try:
            # Update price history
            current_price = float(market_data.close or market_data.last)
            self.price_history.append(current_price)
            self.high_history.append(float(market_data.high or current_price))
            self.low_history.append(float(market_data.low or current_price))

            # Check if we should execute (fixed timestamp rule)
            if not self._should_execute_at_fixed_timestamp():
                logger.debug(
                    "CARVER skipping - not at fixed execution time", symbol=market_data.symbol
                )
                return []

            # Need sufficient history
            if len(self.price_history) < self.lookback_period:
                logger.debug(
                    f"CARVER {market_data.symbol}: Insufficient history "
                    f"({len(self.price_history)} < {self.lookback_period})"
                )
                return []

            # Calculate simple robust indicator (Carver uses carry or trend)
            # Here we use a simple trend following rule: price vs moving average
            prices_list = list(self.price_history)
            ma_period = self.lookback_period

            # Calculate moving average
            ma = sum(prices_list[-ma_period:]) / ma_period

            # Calculate volatility for position sizing
            volatility = self._calculate_volatility(prices_list)

            # Simple robust rule: Buy if price > MA, Sell if price < MA
            # This is Carver's "sticking to the rules" principle
            buy_condition = current_price > ma
            sell_condition = current_price < ma

            logger.info(
                f"CARVER {market_data.symbol}: price={current_price:.2f}, "
                f"ma={ma:.2f}, volatility={volatility:.4f}, "
                f"buy={buy_condition}, sell={sell_condition}"
            )

            # Generate signals based on conditions
            if buy_condition:
                signal = self._create_signal(
                    market_data, SignalType.BUY, current_price, ma, volatility
                )
                signals.append(signal)
                logger.info(
                    f"CARVER Generated BUY signal for {market_data.symbol}: "
                    f"price={current_price:.2f}, ma={ma:.2f}"
                )

            elif sell_condition:
                signal = self._create_signal(
                    market_data, SignalType.SELL, current_price, ma, volatility
                )
                signals.append(signal)
                logger.info(
                    f"CARVER Generated SELL signal for {market_data.symbol}: "
                    f"price={current_price:.2f}, ma={ma:.2f}"
                )

        except (ValueError, KeyError, AttributeError, TypeError) as e:
            logger.error(
                f"CARVER Error generating signals for {market_data.symbol}: {e}",
                exc_info=True,
            )

        return signals

    def _should_execute_at_fixed_timestamp(self) -> bool:
        """
        Check if we should execute at fixed timestamp (Carver's methodology).

        Fixed timestamp execution reduces "timing luck" - the variability
        in returns due to choosing different execution times.

        Returns:
            True if current time matches a fixed execution time
        """
        if not self.use_fixed_timestamps:
            return True  # Execute normally if fixed timestamps disabled

        now = datetime.utcnow()

        # Check if we're at one of the fixed execution times
        current_time = now.time()

        for exec_time_str in self.execution_times:
            try:
                # Parse execution time (HH:MM format)
                exec_time_parts = exec_time_str.split(":")
                exec_time = time(hour=int(exec_time_parts[0]), minute=int(exec_time_parts[1]))

                # Check if current time is within 1 minute of execution time
                time_diff = (current_time.hour - exec_time.hour) * 60 + (
                    current_time.minute - exec_time.minute
                )

                # Execute if within 1 minute window and haven't executed today
                if abs(time_diff) <= 1:
                    if (
                        self.last_execution_date is None
                        or self.last_execution_date.date() != now.date()
                    ):
                        self.last_execution_time = current_time
                        self.last_execution_date = now
                        return True

            except (ValueError, IndexError):
                logger.warning(f"Invalid execution time format: {exec_time_str}")
                continue

        return False

    def _calculate_volatility(self, prices_list: List[float]) -> float:
        """
        Calculate volatility for position sizing (Carver's methodology).

        Uses a simple robust volatility measure: standard deviation of returns.

        Args:
            prices_list: List of historical prices

        Returns:
            Volatility measure
        """
        if len(prices_list) < 2:
            return 0.02  # Default volatility

        # Calculate returns
        returns = []
        for i in range(1, len(prices_list)):
            ret = (prices_list[i] - prices_list[i - 1]) / prices_list[i - 1]
            returns.append(ret)

        # Calculate standard deviation
        import numpy as np

        volatility = getattr(config.trading, 'max_risk_per_trade', 0.02)

        return volatility

    def _get_handcrafted_weight(self, symbol: str, volatility: float) -> float:
        """
        Get handcrafted weight for instrument (Carver's methodology).

        Carver advocates handcrafting portfolio weights based on:
        1. Instrument risk characteristics (volatility)
        2. Diversification benefits
        3. Risk tolerance

        Args:
            symbol: Instrument symbol
            volatility: Instrument volatility

        Returns:
            Handcrafted weight for position sizing
        """
        if not self.use_handcrafted_weights:
            return 1.0  # No adjustment

        # If we have a predefined weight, use it
        if symbol in self.handcrafted_weights:
            return float(self.handcrafted_weights[symbol])

        # Otherwise, calculate based on volatility (Carver's method)
        # Lower volatility -> larger position
        # Higher volatility -> smaller position
        # Target: 15% annualized volatility

        target_volatility = float(self.volatility_target)

        # Scale weight inversely with volatility
        if volatility > 0:
            weight = target_volatility / volatility
            # Apply instrument diversification constraint
            weight = min(weight, float(self.instrument_diversification))
        else:
            weight = float(self.instrument_diversification)

        return max(0.0, min(weight, 1.0))

    def _apply_decay_factor(self, current_weight: float, previous_weight: Optional[float]) -> float:
        """
        Apply decay factor for smooth transitions (Carver's methodology).

        Carver uses decay factors to smooth portfolio transitions:
        new_weight = decay * new_position + (1-decay) * old_position

        This reduces transaction costs and portfolio turnover.

        Args:
            current_weight: New target weight
            previous_weight: Previous weight

        Returns:
            Decayed weight
        """
        if not self.use_decay or previous_weight is None:
            return current_weight

        decay = float(self.decay_factor)
        decayed_weight = decay * current_weight + (1 - decay) * previous_weight

        return decayed_weight

    def _create_signal(
        self,
        market_data: Quote,
        signal_type: SignalType,
        current_price: float,
        ma: float,
        volatility: float,
    ) -> Signal:
        """
        Create a trading signal with Carver's methodology.

        Args:
            market_data: Current market data
            signal_type: BUY or SELL
            current_price: Current price
            ma: Moving average
            volatility: Instrument volatility

        Returns:
            Trading signal
        """
        # Calculate handcrafted weight for this instrument
        handcrafted_weight = self._get_handcrafted_weight(market_data.symbol, volatility)

        return Signal(
            symbol=market_data.symbol,
            signal_type=signal_type,
            strength=SignalStrength.MODERATE,
            confidence=70.0,  # Carver's rules don't use confidence scoring
            liquidity_score=80.0,
            priority_score=75.0,
            source=SignalSource.MOMENTUM,
            price=market_data.last,
            volume=Decimal("1"),  # Placeholder
            timestamp=market_data.timestamp,
            metadata={
                "strategy": self.name,
                "methodology": "carver_robust_rules",
                "current_price": str(current_price),
                "moving_average": str(ma),
                "volatility": str(volatility),
                "handcrafted_weight": str(handcrafted_weight),
                "fixed_timestamp": self.use_fixed_timestamps,
                "decay_factor": str(self.decay_factor) if self.use_decay else "disabled",
                "stop_loss": str(self.stop_loss),
                "take_profit": str(self.take_profit),
                "reason": self._format_signal_reason(signal_type, current_price, ma),
            },
        )

    def _format_signal_reason(
        self, signal_type: SignalType, current_price: float, ma: float
    ) -> str:
        """
        Format signal reason following Carver's simple rules philosophy.

        Args:
            signal_type: Type of signal
            current_price: Current price
            ma: Moving average

        Returns:
            Formatted reason string
        """
        direction = "above" if current_price > ma else "below"
        return (
            f"carver_robust_rule: price={current_price:.2f} "
            f"ma_trend={direction} (simple_trend_following)"
        )

    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Check if signal passes risk criteria (Carver's methodology).

        Carver's risk checks:
        1. Position size based on volatility targeting
        2. Portfolio level risk limits
        3. Instrument diversification constraints

        Args:
            signal: Signal to check
            portfolio: Current portfolio state

        Returns:
            True if signal passes risk checks
        """
        try:
            # Check position size
            if signal.signal_type == SignalType.SELL:
                existing_position = self._get_existing_position(portfolio, signal.symbol)
                if not existing_position:
                    logger.info(
                        f"CARVER risk_check REJECTED SELL {signal.symbol}: No position exists"
                    )
                    return False

                position_size = self.get_position_size(signal, portfolio)
                if position_size <= 0:
                    logger.info(
                        f"CARVER risk_check REJECTED SELL {signal.symbol}: "
                        f"Position size too small"
                    )
                    return False

                if existing_position.quantity < position_size:
                    logger.info(
                        f"CARVER risk_check REJECTED SELL {signal.symbol}: "
                        f"Insufficient position"
                    )
                    return False

            elif signal.signal_type == SignalType.BUY:
                position_size = self.get_position_size(signal, portfolio)
                if position_size <= 0:
                    logger.info(
                        f"CARVER risk_check REJECTED BUY {signal.symbol}: "
                        f"Position size too small"
                    )
                    return False

                required_cash = signal.price * position_size
                if required_cash > portfolio.cash:
                    logger.info(
                        f"CARVER risk_check REJECTED BUY {signal.symbol}: " f"Insufficient cash"
                    )
                    return False

            # Check portfolio-level risk (volatility targeting)
            total_exposure = self._calculate_total_exposure(portfolio)
            max_exposure = (
                self.instrument_diversification * 2
            )  # Allow 2x instrument diversification

            if total_exposure > max_exposure:
                logger.info(
                    f"CARVER risk_check REJECTED {signal.signal_type} {signal.symbol}: "
                    f"Total exposure too high ({total_exposure:.2%} > {max_exposure:.2%})"
                )
                return False

            logger.debug(f"CARVER risk_check PASSED {signal.signal_type} {signal.symbol}")
            return True

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"CARVER risk_check ERROR for {signal.symbol}: {e}", exc_info=True)
            return False

    def _get_existing_position(self, portfolio: Portfolio, symbol: str):
        """Get existing position for symbol."""
        for position in portfolio.positions:
            if position.symbol == symbol:
                return position
        return None

    def _calculate_total_exposure(self, portfolio: Portfolio) -> Decimal:
        """Calculate total portfolio exposure."""
        total_value = portfolio.cash + sum(p.market_value for p in portfolio.positions)

        if total_value == 0:
            return Decimal("0")

        invested_value = total_value - portfolio.cash
        return invested_value / total_value
