"""
FX Carry Trade Strategy Implementation.

This module implements the FX Carry Trade strategy based on Antti Ilmanen's
methodology from "Expected Returns" - Rule 12.9.

The strategy exploits interest rate differentials between currency pairs by:
1. Borrowing in low-interest-rate currencies (funding currencies)
2. Investing in high-interest-rate currencies (target currencies)
3. Managing risk through position sizing and stop-loss

Reference:
    Ilmanen, Antti. "Expected Returns: An Investor's Guide"
    Rule 12.9: Carry trade implementation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from app.core.centralized_config import get_config
from app.domain.strategies.base import BaseStrategy
from app.domain.strategies.fx_carry_trade.carry_calculator import CarryCalculator, CarryTradeOpportunity
from app.domain.strategies.fx_carry_trade.fx_rates_provider import FXRateProvider, InMemoryFXRateProvider
from app.domain.strategies.fx_carry_trade.models import (
    FXCarryPosition,
    FXCarrySignal,
    FXCarryTradeConfig,
    FXPair,
)

logger = logging.getLogger(__name__)


@dataclass
class FXCarryTradeState:
    """
    Current state of the FX carry trade strategy.

    Attributes:
        current_positions: Dictionary of active positions by pair
        pending_signals: Signals waiting to be executed
        total_exposure: Total market exposure
        available_capital: Capital available for new positions
        last_update: Last state update timestamp
    """

    current_positions: dict[FXPair, FXCarryPosition] = field(default_factory=dict)
    pending_signals: list[FXCarrySignal] = field(default_factory=list)
    total_exposure: Decimal = field(default=Decimal("0"))
    available_capital: Decimal = field(default=Decimal("100000"))
    last_update: date = field(default_factory=date.today)


class FXCarryTradeStrategy(BaseStrategy):
    """
    FX Carry Trade strategy following Ilmanen's methodology.

    This strategy implements carry trade by:
    1. Calculating carry signals for currency pairs
    2. Selecting best opportunities based on carry value
    3. Managing positions with risk controls
    4. Monitoring carry-to-risk ratios

    The strategy uses the formula:
        carry = interest_rate_differential - forward_premium

    Where:
        - interest_rate_differential = rate_base - rate_quote
        - forward_premium = (forward_rate - spot_rate) / spot_rate

    Attributes:
        config: Strategy configuration
        calculator: Carry signal calculator
        rate_provider: FX rate data provider
        state: Current strategy state

    Examples:
        >>> from app.domain.strategies.fx_carry_trade import (
        ...     FXCarryTradeStrategy,
        ...     FXCarryTradeConfig,
        ...     InMemoryFXRateProvider,
        ... )
        >>> config = FXCarryTradeConfig(min_carry_threshold=Decimal("0.01"))
        >>> provider = InMemoryFXRateProvider()
        >>> strategy = FXCarryTradeStrategy(
        ...     config=config,
        ...     rate_provider=provider,
        ... )
    """

    def __init__(
        self,
        config: dict[str, Any] | FXCarryTradeConfig,
        rate_provider: FXRateProvider | None = None,
        calculator: CarryCalculator | None = None,
    ) -> None:
        """
        Initialize the FX Carry Trade strategy.

        Args:
            config: Strategy configuration (dict or FXCarryTradeConfig)
            rate_provider: FX rate data provider (creates InMemoryFXRateProvider if None)
            calculator: Carry calculator (creates default if None)

        Raises:
            ValueError: If config is invalid
        """
        # Load modular strategy config for defaults
        trading_config = get_config()
        _cfg = trading_config.trading_thresholds.fx_carry  # Modular config

        # Handle dict config for BaseStrategy compatibility
        if isinstance(config, dict):
            # Extract known parameters or use defaults from modular config
            strategy_config = FXCarryTradeConfig(
                min_carry_threshold=Decimal(str(config.get("min_carry_threshold", _cfg.min_carry_threshold))),
                max_positions=config.get("max_positions", _cfg.max_positions_default),
                position_size=Decimal(str(config.get("position_size", _cfg.position_size_default))),
                forward_months=config.get("forward_months", 3),
                stop_loss=Decimal(str(config.get("stop_loss", _cfg.stop_loss_default))),
                take_profit=Decimal(str(config.get("take_profit", _cfg.take_profit_default))),
                max_leverage=Decimal(str(config.get("max_leverage", _cfg.max_leverage))),
                min_liquidity=Decimal(str(config.get("min_liquidity", _cfg.min_liquidity))),
            )
            super().__init__(config)
        else:
            strategy_config = config
            # Convert to dict for BaseStrategy
            super().__init__(
                {
                    "name": "FXCarryTrade",
                    "description": "FX Carry Trade strategy based on Ilmanen's methodology",
                    "version": "1.0.0",
                    "min_carry_threshold": str(strategy_config.min_carry_threshold),
                    "max_positions": strategy_config.max_positions,
                    "position_size": str(strategy_config.position_size),
                    "forward_months": strategy_config.forward_months,
                    "stop_loss": str(strategy_config.stop_loss),
                    "take_profit": str(strategy_config.take_profit),
                    "max_leverage": str(strategy_config.max_leverage),
                    "min_liquidity": str(strategy_config.min_liquidity),
                }
            )

        self.config = strategy_config
        self._cfg = _cfg  # Store modular config reference for use in methods
        self.calculator = calculator or CarryCalculator(
            signal_threshold=strategy_config.min_carry_threshold,
        )
        self.rate_provider = rate_provider or InMemoryFXRateProvider()
        self.state = FXCarryTradeState()

        # Define trading pairs (major G10 currencies)
        self.pairs = self._get_default_pairs()

        logger.info(
            f"FXCarryTradeStrategy initialized with {len(self.pairs)} pairs, "
            f"min_carry_threshold={self.config.min_carry_threshold}"
        )

    def _get_default_pairs(self) -> list[FXPair]:
        """
        Get default FX pairs for carry trading.

        Returns:
            List of major G10 currency pairs
        """
        currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]
        pairs = []

        for i, base in enumerate(currencies):
            for quote in currencies[i + 1 :]:
                pairs.append(FXPair(base_currency=base, quote_currency=quote))

        return pairs

    def generate_signals(self, market_data: Any) -> list[Any]:
        """
        Generate carry trade signals for all configured pairs.

        Args:
            market_data: Market data (not used for carry, uses rate_provider)

        Returns:
            List of FXCarrySignal objects
        """

        signals = []
        as_of = date.today()

        try:
            # Calculate signals for all pairs using provider
            signal_dict = self.calculator.calculate_signals_from_provider(
                pairs=self.pairs,
                provider=self.rate_provider,
                as_of=as_of,
                months=self.config.forward_months,
            )

            # Filter by minimum signal threshold
            filtered_signals = self.calculator.filter_signals(
                signal_dict,
                min_abs_signal=self.config.min_carry_threshold,
            )

            # Rank signals by absolute carry value
            ranked_signals = self.calculator.rank_signals(filtered_signals)

            # Convert to list and limit to max positions
            for pair, signal in ranked_signals[: self.config.max_positions]:
                signals.append(signal)

            logger.info(f"Generated {len(signals)} carry trade signals")

        except Exception as e:
            logger.error(f"Error generating carry signals: {e}")

        return signals

    def analyze_opportunities(self, as_of: date | None = None) -> list[CarryTradeOpportunity]:
        """
        Analyze current carry trade opportunities.

        Args:
            as_of: Analysis date (default: today)

        Returns:
            List of carry trade opportunities ranked by expected return
        """
        as_of = as_of or date.today()

        try:
            signal_dict = self.calculator.calculate_signals_from_provider(
                pairs=self.pairs,
                provider=self.rate_provider,
                as_of=as_of,
                months=self.config.forward_months,
            )

            opportunities = []
            for pair, signal in signal_dict.items():
                if abs(signal.signal) >= float(self.config.min_carry_threshold):
                    # Calculate confidence based on signal strength and carry
                    confidence = self._calculate_confidence(signal)

                    opportunity = CarryTradeOpportunity(
                        pair=signal.pair,
                        expected_carry=signal.carry,
                        forward_premium=signal.forward_premium,
                        signal=signal.signal,
                        confidence=confidence,
                    )
                    opportunities.append(opportunity)

            # Sort by expected carry
            opportunities.sort(key=lambda o: abs(o.expected_carry), reverse=True)

            return opportunities

        except Exception as e:
            logger.error(f"Error analyzing opportunities: {e}")
            return []

    def _calculate_confidence(self, signal: FXCarrySignal) -> float:
        """
        Calculate confidence score for a signal - use config values.

        Args:
            signal: The carry trade signal

        Returns:
            Confidence score (0-100)
        """
        # Base confidence from signal strength - use config multiplier
        signal_strength = abs(float(signal.signal))
        base_confidence = min(signal_strength * self._cfg.base_confidence_multiplier, self._cfg.carry_boost_max)

        # Boost for positive carry (positive expected return) - use config
        if signal.carry > 0:
            carry_boost = min(float(signal.carry) * self._cfg.carry_boost_multiplier, self._cfg.carry_boost_max)
        else:
            carry_boost = 0

        return base_confidence + carry_boost

    def execute_signal(self, signal: FXCarrySignal, capital: Decimal) -> FXCarryPosition | None:
        """
        Execute a carry trade signal.

        Calculates position size based on volatility-adjusted sizing and
        creates a position with appropriate risk controls.

        Args:
            signal: The signal to execute
            capital: Available capital for position sizing

        Returns:
            Created position or None if execution failed
        """
        # Check if we already have a position for this pair
        if signal.pair in self.state.current_positions:
            logger.warning(f"Position already exists for {signal.pair}")
            return None

        # Calculate volatility for position sizing
        volatility = self._calculate_signal_volatility(signal)

        # Calculate position size with volatility adjustment
        position_size = self._calculate_position_size(capital, signal, volatility)

        if position_size <= 0:
            logger.warning(f"Invalid position size for {signal.pair}")
            return None

        # Determine long/short based on signal
        quantity = position_size if signal.signal > 0 else -position_size

        # Create position
        position = FXCarryPosition(
            pair=signal.pair,
            quantity=quantity,
            entry_price=signal.spot_rate,
            current_price=signal.spot_rate,
            carry_return=Decimal("0"),
            price_return=Decimal("0"),
            total_return=Decimal("0"),
            entry_date=signal.timestamp,
            current_date=signal.timestamp,
        )

        self.state.current_positions[signal.pair] = position
        self.state.total_exposure += abs(quantity * signal.spot_rate)

        logger.info(
            f"Opened {signal.pair} position: "
            f"quantity={quantity}, entry_price={signal.spot_rate}, "
            f"volatility={volatility:.2%}"
        )

        return position

    def _calculate_position_size(
        self, capital: Decimal, signal: FXCarrySignal, volatility: Decimal
    ) -> Decimal:
        """
        Calculate position size based on capital, signal, and volatility.

        Uses Kelly criterion-inspired sizing with volatility adjustment.
        Higher volatility leads to smaller position sizes for risk management.

        The calculation follows these steps:
        1. Base position: capital * position_size
        2. Volatility adjustment: 1/volatility (higher vol = smaller position)
        3. Leverage cap: Ensure position doesn't exceed max_leverage

        Args:
            capital: Available capital for trading
            signal: FX carry signal with entry/exit points
            volatility: Current volatility (e.g., ATR or standard deviation)

        Returns:
            Number of units to trade, quantized to 2 decimal places

        Raises:
            ValueError: If capital or signal is invalid
        """
        if capital <= 0:
            raise ValueError(f"Capital must be positive, got {capital}")

        if signal.spot_rate <= 0:
            raise ValueError(f"Spot rate must be positive, got {signal.spot_rate}")

        # Base position using configured fraction
        position_value = capital * self.config.position_size

        # Volatility adjustment (higher vol = smaller position) - use config values
        # Normalize vol: configured baseline is baseline giving 1.0x adjustment
        # Formula: adjustment = baseline_vol / actual_vol
        # If vol is 0.02 (2%), adjustment = getattr(config.trading, 'max_risk_per_trade', 0.02) = 0.5 (halve position)
        # If vol is 0.005 (0.5%), adjustment = baseline/0.005 = 2.0 (double position, capped)
        baseline_volatility = Decimal(str(self._cfg.baseline_volatility))
        vol_adjustment = baseline_volatility / max(volatility, baseline_volatility)
        vol_adjustment = min(vol_adjustment, Decimal(str(self._cfg.vol_adjustment_max)))  # Use config cap

        position_value = position_value * vol_adjustment

        # Apply leverage cap
        max_position_value = capital * self.config.max_leverage
        if position_value > max_position_value:
            position_value = max_position_value

        # Convert to currency units
        position_size = position_value / signal.spot_rate

        return position_size.quantize(Decimal("0.01"))

    def _calculate_signal_volatility(self, signal: FXCarrySignal) -> Decimal:
        """
        Calculate volatility for a signal using ATR-based estimation.

        Approximates volatility using the forward premium as a proxy for
        expected price movement. In practice, this should use historical
        ATR or realized volatility from price data.

        Volatility estimation approach:
        - Use absolute forward premium as base volatility estimate
        - Add a minimum volatility floor for risk management
        - Scale to annualized volatility

        Args:
            signal: FX carry signal with spot and forward rates

        Returns:
            Estimated volatility as a decimal (e.g., 0.10 for 10%)
        """
        # Use absolute forward premium as volatility proxy
        # Forward premium reflects market's expected price movement
        base_volatility = abs(signal.forward_premium)

        # Add minimum volatility floor - use config value
        min_volatility = Decimal(str(self._cfg.min_volatility))

        # Scale: forward premium is typically for 3 months, annualize it
        # Multiply by 4 (for quarters in a year) but cap at reasonable max
        quarterly_volatility = base_volatility * Decimal("4")
        estimated_volatility = max(quarterly_volatility, min_volatility)

        # Cap at configured max annual volatility for safety - use config
        max_volatility = Decimal(str(self._cfg.max_volatility))
        estimated_volatility = min(estimated_volatility, max_volatility)

        return estimated_volatility

    def update_positions(self, as_of: date | None = None) -> dict[FXPair, FXCarryPosition]:
        """
        Update all current positions with latest rates.

        Args:
            as_of: Update date (default: today)

        Returns:
            Dictionary of updated positions
        """
        as_of = as_of or date.today()

        updated_positions = {}

        for pair, position in self.state.current_positions.items():
            try:
                # Get current rate
                current_rate = self.rate_provider.get_spot_rate(pair, as_of)

                # Calculate returns
                price_return = (current_rate - position.entry_price) / position.entry_price

                # Estimate carry return (proportional to days held)
                days_held = (as_of - position.entry_date).days
                daily_carry = float(position.entry_price) * 0.0001  # Approximate
                carry_return = Decimal(str(daily_carry * days_held))

                # Update position
                updated_position = FXCarryPosition(
                    pair=position.pair,
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    current_price=current_rate,
                    carry_return=carry_return,
                    price_return=Decimal(str(price_return)),
                    total_return=carry_return + Decimal(str(price_return)),
                    entry_date=position.entry_date,
                    current_date=as_of,
                )

                updated_positions[pair] = updated_position

            except Exception as e:
                logger.error(f"Error updating position {pair}: {e}")
                # Keep original position on error
                updated_positions[pair] = position

        self.state.current_positions = updated_positions
        self.state.last_update = as_of

        return updated_positions

    def close_position(
        self, pair: FXPair, exit_price: Decimal, exit_date: date
    ) -> FXCarryPosition | None:
        """
        Close a position for a currency pair.

        Args:
            pair: Currency pair to close
            exit_price: Exit price
            exit_date: Exit date

        Returns:
            Closed position or None if not found
        """
        if pair not in self.state.current_positions:
            logger.warning(f"No position found for {pair}")
            return None

        position = self.state.current_positions[pair]

        # Calculate final returns
        price_return = (exit_price - position.entry_price) / position.entry_price

        closed_position = FXCarryPosition(
            pair=position.pair,
            quantity=position.quantity,
            entry_price=position.entry_price,
            current_price=exit_price,
            carry_return=position.carry_return,
            price_return=Decimal(str(price_return)),
            total_return=position.carry_return + Decimal(str(price_return)),
            entry_date=position.entry_date,
            current_date=exit_date,
        )

        # Remove from positions
        del self.state.current_positions[pair]
        self.state.total_exposure -= abs(position.quantity * exit_price)

        logger.info(f"Closed {pair} position: " f"total_return={closed_position.total_return:.2%}")

        return closed_position

    def check_exit_conditions(self, pair: FXPair, current_price: Decimal) -> tuple[bool, str]:
        """
        Check if a position should be closed.

        Args:
            pair: Currency pair to check
            current_price: Current market price

        Returns:
            Tuple of (should_close, reason)
        """
        if pair not in self.state.current_positions:
            return False, "No position"

        position = self.state.current_positions[pair]

        # Check stop loss
        if position.is_long:
            loss_pct = (current_price - position.entry_price) / position.entry_price
            if loss_pct <= -float(self.config.stop_loss):
                return True, f"Stop loss triggered: {loss_pct:.2%}"
        else:
            loss_pct = (position.entry_price - current_price) / position.entry_price
            if loss_pct <= -float(self.config.stop_loss):
                return True, f"Stop loss triggered: {loss_pct:.2%}"

        # Check take profit
        if position.is_long:
            gain_pct = (current_price - position.entry_price) / position.entry_price
            if gain_pct >= float(self.config.take_profit):
                return True, f"Take profit triggered: {gain_pct:.2%}"
        else:
            gain_pct = (position.entry_price - current_price) / position.entry_price
            if gain_pct >= float(self.config.take_profit):
                return True, f"Take profit triggered: {gain_pct:.2%}"

        # Check signal reversal
        try:
            signal = self.calculator.calculate_signals_from_provider(
                pairs=[pair],
                provider=self.rate_provider,
                as_of=date.today(),
                months=self.config.forward_months,
            )

            if pair in signal:
                current_signal = signal[pair].signal
                # If signal flipped and crosses threshold
                if position.is_long and current_signal < -float(self.config.min_carry_threshold):
                    return True, f"Signal reversal to short: {current_signal}"
                if position.is_short and current_signal > float(self.config.min_carry_threshold):
                    return True, f"Signal reversal to long: {current_signal}"

        except Exception as e:
            logger.warning(f"Error checking signal reversal: {e}")

        return False, ""

    def risk_check(self, signal: Any, portfolio: Any) -> bool:
        """
        Check if signal passes risk management criteria.

        Args:
            signal: Trading signal to check
            portfolio: Current portfolio state

        Returns:
            True if signal passes risk checks
        """
        # Check if we're at max positions
        if len(self.state.current_positions) >= self.config.max_positions:
            logger.warning("Max positions reached")
            return False

        # Check available capital
        if self.state.available_capital <= 0:
            logger.warning("No available capital")
            return False

        return True

    def get_required_parameters(self) -> list[str]:
        """
        Get required strategy parameters.

        Returns:
            List of required parameter names
        """
        return [
            "min_carry_threshold",
            "max_positions",
            "position_size",
            "forward_months",
            "stop_loss",
            "take_profit",
        ]

    def get_portfolio_summary(self) -> dict[str, Any]:
        """
        Get summary of current portfolio state.

        Returns:
            Dictionary with portfolio metrics
        """
        positions = list(self.state.current_positions.values())

        if not positions:
            return {
                "num_positions": 0,
                "total_exposure": 0,
                "total_pnl": 0,
                "best_position": None,
                "worst_position": None,
            }

        total_pnl = sum(p.total_return for p in positions)
        best_position = max(positions, key=lambda p: p.total_return)
        worst_position = min(positions, key=lambda p: p.total_return)

        return {
            "num_positions": len(positions),
            "total_exposure": float(self.state.total_exposure),
            "total_pnl": float(total_pnl),
            "best_position": {
                "pair": str(best_position.pair),
                "return": float(best_position.total_return),
            },
            "worst_position": {
                "pair": str(worst_position.pair),
                "return": float(worst_position.total_return),
            },
        }

    def __str__(self) -> str:
        """String representation of the strategy."""
        return (
            f"FXCarryTradeStrategy("
            f"pairs={len(self.pairs)}, "
            f"positions={len(self.state.current_positions)}, "
            f"min_carry={self.config.min_carry_threshold})"
        )

    def __repr__(self) -> str:
        """Detailed representation of the strategy."""
        return (
            f"FXCarryTradeStrategy("
            f"config={self.config}, "
            f"pairs={len(self.pairs)}, "
            f"state.positions={len(self.state.current_positions)})"
        )
