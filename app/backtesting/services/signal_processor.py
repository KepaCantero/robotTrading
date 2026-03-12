"""
Signal Processor service for backtesting.

This service is responsible for validating trading signals and deciding
whether to execute them based on risk checks and profitability validation.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from app.backtesting.models import BacktestConfig
from app.domain.models.signal import Signal, SignalType
from app.domain.services.compliance.compliance_engine import ComplianceEngine

logger = logging.getLogger(__name__)


class SignalProcessor:
    """
    Processes and validates trading signals before execution.

    This service handles:
    - Risk envelope validation (via ComplianceEngine)
    - Strategy risk checks
    - Trade profitability validation
    - Signal rejection logging

    Dependencies:
    - TradingValidator: Position size and stop-loss validation
    - ComplianceEngine: Portfolio-level risk management (includes risk envelope validation)
    - strategy: Strategy instance for custom risk checks
    - diagnostic_logger: Optional logging for rejected signals
    """

    def __init__(
        self,
        config: BacktestConfig,
        strategy: Optional[Any] = None,
        compliance_engine: Optional[ComplianceEngine] = None,
        enable_risk_envelope: bool = True,
        diagnostic_logger: Optional[Any] = None,
        total_portfolio_capital: Optional[Decimal] = None,
        strategy_name: str = "unknown",
    ):
        """
        Initialize the SignalProcessor.

        Args:
            config: Backtest configuration
            strategy: Optional strategy instance for risk_check validation
            compliance_engine: Optional ComplianceEngine instance (uses singleton if not provided)
            enable_risk_envelope: Enable risk envelope validation (default True)
            diagnostic_logger: Optional diagnostic logger for rejected signals
            total_portfolio_capital: Total portfolio capital for multi-strategy scenarios
            strategy_name: Name of strategy for logging purposes
        """
        from app.domain.services.trading_validators import TradingValidator

        self.config = config
        self.strategy = strategy
        self.enable_risk_envelope = enable_risk_envelope
        self.compliance_engine = compliance_engine or ComplianceEngine()
        self.diagnostic_logger = diagnostic_logger
        self.total_portfolio_capital = total_portfolio_capital or config.initial_capital
        self.strategy_name = strategy_name

        # Initialize Trading Validator for position size and stop-loss validation
        self.trading_validator = TradingValidator()

        if enable_risk_envelope:
            logger.info(
                f"Risk Envelope validation enabled for {strategy_name} (via ComplianceEngine)"
            )

    def process_signal(
        self,
        signal: Signal,
        market_data: Any,
        positions: Dict[str, Decimal],
        capital: Decimal,
        last_known_prices: Dict[str, Decimal],
        create_portfolio_func,
        validate_profitability_func,
    ) -> Optional[str]:
        """
        Process a trading signal with full validation pipeline.

        Args:
            signal: Trading signal to process
            market_data: Current market data
            positions: Current positions dictionary
            capital: Current available capital
            last_known_prices: Last known prices for each symbol
            create_portfolio_func: Function to create portfolio from state
            validate_profitability_func: Function to validate trade profitability

        Returns:
            "BUY" if signal should be executed as buy
            "SELL" if signal should be executed as sell
            None if signal should be rejected
        """
        from app.backtesting.engine import get_price

        strategy_name = signal.metadata.get("strategy", "unknown") if signal.metadata else "unknown"

        # Step 1: Apply risk_check if strategy is available
        if not self._validate_strategy_risk_check(
            signal, market_data, positions, last_known_prices, create_portfolio_func
        ):
            return None

        # Step 2: Apply Risk Envelope validation if enabled
        if not self._validate_risk_envelope(
            signal, market_data, positions, capital, last_known_prices, create_portfolio_func
        ):
            return None

        # Step 3: Validate trade profitability
        current_price = get_price(market_data)
        if not validate_profitability_func(signal, current_price):
            return None

        # Return signal type for execution
        if signal.signal_type == SignalType.BUY:
            logger.info(f"Processing BUY signal for {signal.symbol} (strategy={strategy_name})")
            return "BUY"
        elif signal.signal_type == SignalType.SELL:
            logger.info(f"Processing SELL signal for {signal.symbol} (strategy={strategy_name})")
            return "SELL"
        elif signal.signal_type == SignalType.HOLD:
            logger.debug(f"Processing HOLD signal for {signal.symbol} (skipped)")
            return None

        return None

    def _validate_strategy_risk_check(
        self,
        signal: Signal,
        market_data: Any,
        positions: Dict[str, Decimal],
        last_known_prices: Dict[str, Decimal],
        create_portfolio_func,
    ) -> bool:
        """
        Validate signal using strategy's risk_check method.

        Args:
            signal: Trading signal to validate
            market_data: Current market data
            positions: Current positions
            last_known_prices: Last known prices
            create_portfolio_func: Function to create portfolio

        Returns:
            True if signal passes risk check, False otherwise
        """
        from app.backtesting.engine import get_price

        if not self.strategy:
            logger.warning(
                f"No strategy provided, skipping risk_check for {signal.symbol} "
                f"(strategy={self.strategy_name})"
            )
            return True

        try:
            # Create a Portfolio object from current state for risk_check
            current_price = get_price(market_data)
            portfolio = create_portfolio_func(
                current_price_func=lambda s: (
                    current_price if s == signal.symbol else last_known_prices.get(s, current_price)
                )
            )

            # Apply risk_check
            risk_check_result = self.strategy.risk_check(signal, portfolio)

            if not risk_check_result:
                rejection_reason = self._build_rejection_reason(signal, portfolio, current_price)

                logger.info(
                    f"REJECTED {signal.signal_type} {signal.symbol} "
                    f"(strategy={self.strategy_name}): {rejection_reason}"
                )

                # Log rejection to diagnostic logger
                if self.diagnostic_logger:
                    signal_type_str = (
                        signal.signal_type.value
                        if hasattr(signal.signal_type, "value")
                        else str(signal.signal_type)
                    )
                    self.diagnostic_logger.log_signal_rejected(
                        self.strategy_name,
                        signal.symbol,
                        rejection_reason,
                        failed_check="risk_check",
                        metadata=signal.metadata if hasattr(signal, "metadata") else {},
                    )

                return False
            else:
                logger.debug(
                    f"PASSED risk_check: {signal.signal_type} {signal.symbol} "
                    f"(strategy={self.strategy_name})"
                )

        except (AttributeError, ValueError, TypeError, KeyError) as e:
            logger.error(
                f"ERROR in risk_check for {signal.symbol} (strategy={self.strategy_name}): {e}",
                exc_info=True,
            )
            # On error, reject the signal for safety
            if self.diagnostic_logger:
                signal_type_str = (
                    signal.signal_type.value
                    if hasattr(signal.signal_type, "value")
                    else str(signal.signal_type)
                )
                self.diagnostic_logger.log_signal_rejected(
                    self.strategy_name,
                    signal.symbol,
                    signal_type_str,
                    f"Risk check error: {str(e)}",
                    signal.metadata if hasattr(signal, "metadata") else {},
                )
            return False

        return True

    def _build_rejection_reason(
        self, signal: Signal, portfolio: Any, current_price: Decimal
    ) -> str:
        """Build detailed rejection reason for logging."""
        rejection_reason = "Risk check failed"

        if signal.signal_type == SignalType.BUY:
            position_size = self.strategy.get_position_size(signal, portfolio)
            required_cash = signal.price * position_size if position_size > 0 else Decimal("0")
            rejection_reason += (
                f" (BUY: cash=${portfolio.cash:.2f}, required=${required_cash:.2f}, "
                f"position_size={position_size:.6f})"
            )
        elif signal.signal_type == SignalType.SELL:
            # For SELL signals, check if position exists to provide context
            existing_pos = next((p for p in portfolio.positions if p.symbol == signal.symbol), None)
            if not existing_pos:
                rejection_reason += " (SELL: no position exists)"
            else:
                rejection_reason += f" (SELL: position_qty={existing_pos.quantity:.6f})"

        return rejection_reason

    def _validate_risk_envelope(
        self,
        signal: Signal,
        market_data: Any,
        positions: Dict[str, Decimal],
        capital: Decimal,
        last_known_prices: Dict[str, Decimal],
        create_portfolio_func,
    ) -> bool:
        """
        Validate signal using Risk Envelope constraints via ComplianceEngine.

        Args:
            signal: Trading signal to validate
            market_data: Current market data
            positions: Current positions
            capital: Current available capital
            last_known_prices: Last known prices
            create_portfolio_func: Function to create portfolio

        Returns:
            True if signal passes risk envelope validation, False otherwise
        """
        from app.backtesting.engine import get_price

        if not self.enable_risk_envelope:
            return True

        current_price = get_price(market_data)

        # Calculate current portfolio positions for validation
        current_portfolio_exposure = {}  # symbol -> position value
        strategy_positions = {}  # symbol -> position value for this strategy

        # Build exposure maps from current positions
        for symbol, quantity in positions.items():
            if quantity > 0:
                # Get current price for this symbol
                if symbol == signal.symbol:
                    pos_price = current_price
                elif symbol in last_known_prices:
                    pos_price = last_known_prices[symbol]
                else:
                    # Fallback: use current_price
                    pos_price = current_price

                position_value = quantity * pos_price
                current_portfolio_exposure[symbol] = position_value
                strategy_positions[symbol] = position_value

        # Calculate trade value
        if signal.signal_type == SignalType.BUY:
            portfolio = create_portfolio_func(
                current_price_func=lambda s: (
                    current_price if s == signal.symbol else last_known_prices.get(s, current_price)
                )
            )
            # Use strategy's position sizing or fallback to config default minimum
            position_size = (
                self.strategy.get_position_size(signal, portfolio)
                if self.strategy
                else self.config.max_position_size
            )
            trade_value = signal.price * position_size
        elif signal.signal_type == SignalType.SELL:
            existing_pos = positions.get(signal.symbol, Decimal("0"))
            trade_value = existing_pos * current_price
        else:
            trade_value = Decimal("0")

        # Validate trade using ComplianceEngine
        if trade_value > 0:
            is_valid, reason = self.compliance_engine.validate_risk_envelope(
                symbol=signal.symbol,
                trade_value=trade_value,
                strategy_name=self.strategy_name,
                current_portfolio=current_portfolio_exposure,
                strategy_positions=strategy_positions,
                total_capital=self.total_portfolio_capital,
                strategy_capital=self.config.initial_capital,
            )

            if not is_valid:
                logger.warning(
                    f"RISK ENVELOPE REJECTED {signal.signal_type} {signal.symbol} "
                    f"(strategy={self.strategy_name}): {reason}"
                )
                if self.diagnostic_logger:
                    signal_type_str = (
                        signal.signal_type.value
                        if hasattr(signal.signal_type, "value")
                        else str(signal.signal_type)
                    )
                    self.diagnostic_logger.log_signal_rejected(
                        self.strategy_name,
                        signal.symbol,
                        signal_type_str,
                        f"Risk envelope: {reason}",
                        signal.metadata if hasattr(signal, "metadata") else {},
                    )
                return False

        return True
