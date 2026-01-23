"""
PHASE 3: Risk Scaling Orchestrator - Integration of All Risk Monitors

Orchestrates all 4 risk scaling monitors into a unified risk management system.
Coordinates scaling decisions and integrates with SignalExecutionEngine,
PositionSizingEngine, and other portfolio management systems.

Key Formula:
combined_scale = volatility_scale × sharpe_scale × loss_scale × drawdown_scale
"""

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional

from app.services.risk_scaling.drawdown_monitor import DrawdownMonitor
from app.services.risk_scaling.loss_monitor import LossMonitor, TradeResult
from app.services.risk_scaling.models import (
    AdjustedSignal,
    RiskAlert,
    RiskAlertType,
    RiskLevel,
    RiskScalingFactors,
    RiskScalingReport,
    RiskScalingSnapshot,
    RiskScalingState,
)
from app.services.risk_scaling.sharpe_ratio_monitor import SharpeRatioMonitor
from app.services.risk_scaling.volatility_monitor import PriceData, VolatilityMonitor

logger = logging.getLogger(__name__)


class RiskScalingOrchestrator:
    """
    Orchestrates all risk scaling monitors and applies dynamic risk adjustment.

    Responsibilities:
    1. Coordinate scaling factor calculations from 4 monitors
    2. Calculate combined scaling factor
    3. Adjust position sizes and stop losses
    4. Generate alerts and monitoring reports
    5. Validate against portfolio risk limits

    Integration Points:
    - SignalExecutionEngine: Adjust signal sizes before execution
    - PositionSizingEngine: Scale position sizes
    - TrailingStopManager: Adjust stop distances
    - PortfolioRiskManager: Validate adjusted positions
    - DynamicCapitalReallocationEngine: Reweight allocations
    """

    def __init__(
        self,
        atr_period: int = 14,
        sharpe_window_days: int = 30,
        loss_reset_threshold: int = 3,
        max_drawdown_limit: Decimal = Decimal("0.15"),
    ):
        """Initialize orchestrator with all monitors."""
        self.volatility_monitor = VolatilityMonitor(atr_period=atr_period)
        self.sharpe_monitor = SharpeRatioMonitor()
        self.loss_monitor = LossMonitor(reset_threshold=loss_reset_threshold)
        self.drawdown_monitor = DrawdownMonitor(max_drawdown_limit=max_drawdown_limit)

        self.sharpe_window_days = sharpe_window_days
        self.state_history: List[RiskScalingState] = []
        self.active_alerts: List[RiskAlert] = []

    async def calculate_scaling_factors(
        self,
        symbol: str,
        prices: List[PriceData],
        daily_returns: List[Decimal],
        trade_results: Optional[List[TradeResult]] = None,
        equity_curve: Optional[List[Decimal]] = None,
    ) -> RiskScalingFactors:
        """
        Calculate all scaling factors from 4 dimensions.

        Args:
            symbol: Trading symbol
            prices: Historical OHLC prices
            daily_returns: Daily returns for Sharpe calculation
            trade_results: Trade results for loss detection
            equity_curve: Equity curve for drawdown

        Returns:
            RiskScalingFactors with all scaling components
        """
        # 1. Calculate volatility scale (ATR-based)
        try:
            current_atr = self.volatility_monitor.calculate_atr(prices)
            avg_atr = self.volatility_monitor.calculate_average_atr(
                symbol, prices, lookback_periods=60
            )
            volatility_scale = self.volatility_monitor.calculate_volatility_scale(
                symbol, current_atr, avg_atr
            )

            # Check for volatility spike
            if self.volatility_monitor.is_volatility_spike(symbol, current_atr, avg_atr):
                self._generate_alert(
                    RiskAlertType.VOLATILITY_SPIKE,
                    RiskLevel.WARNING,
                    f"Volatility spike detected for {symbol}: ATR {current_atr:.4f}",
                    {"current_atr": str(current_atr), "avg_atr": str(avg_atr)},
                )
        except Exception as e:
            logger.error(f"Error calculating volatility scale: {e}")
            volatility_scale = Decimal("1.0")

        # 2. Calculate Sharpe ratio scale (performance-based)
        try:
            sharpe_ratio = await self.sharpe_monitor.calculate_rolling_sharpe(
                daily_returns, window_days=self.sharpe_window_days
            )
            sharpe_scale = self.sharpe_monitor.calculate_sharpe_scale(sharpe_ratio)

            # Check for Sharpe decline
            if sharpe_ratio < Decimal("0.5"):
                self._generate_alert(
                    RiskAlertType.SHARPE_DECLINE,
                    RiskLevel.WARNING,
                    f"Sharpe ratio below threshold: {sharpe_ratio:.2f}",
                    {"sharpe_ratio": str(sharpe_ratio)},
                )
        except Exception as e:
            logger.error(f"Error calculating Sharpe scale: {e}")
            sharpe_scale = Decimal("0.8")
            sharpe_ratio = Decimal("0")

        # 3. Calculate loss scale (loss streak)
        try:
            if trade_results:
                consecutive_losses = self.loss_monitor.detect_consecutive_losses(
                    trade_results, window_days=30
                )
                loss_scale = self.loss_monitor.calculate_loss_scale(consecutive_losses)

                # Check if reset condition met
                should_reset = self.loss_monitor.should_reset_loss_counter(trade_results)
                if should_reset:
                    logger.info(f"Loss counter reset for {symbol}")

                # Generate alert for loss streak
                if consecutive_losses >= 3:
                    self._generate_alert(
                        RiskAlertType.LOSS_STREAK,
                        RiskLevel.CRITICAL if consecutive_losses >= 4 else RiskLevel.WARNING,
                        f"{consecutive_losses} consecutive losses detected",
                        {"consecutive_losses": str(consecutive_losses)},
                    )
            else:
                consecutive_losses = 0
                loss_scale = Decimal("1.0")
        except Exception as e:
            logger.error(f"Error calculating loss scale: {e}")
            loss_scale = Decimal("1.0")
            consecutive_losses = 0

        # 4. Calculate drawdown scale (circuit breaker)
        try:
            if equity_curve:
                current_dd, max_dd = self.drawdown_monitor.calculate_drawdown(equity_curve)
                drawdown_scale = self.drawdown_monitor.calculate_drawdown_scale(current_dd)

                # Check for halt condition
                if self.drawdown_monitor.should_halt_trading(current_dd):
                    self._generate_alert(
                        RiskAlertType.HALT_TRADING,
                        RiskLevel.CRITICAL,
                        f"Circuit breaker triggered: drawdown {current_dd:.1%}",
                        {
                            "current_drawdown": f"{current_dd:.1%}",
                            "max_drawdown": f"{max_dd:.1%}",
                        },
                    )

                # Check for drawdown warning
                elif current_dd > Decimal("0.10"):
                    self._generate_alert(
                        RiskAlertType.DRAWDOWN_WARNING,
                        RiskLevel.WARNING,
                        f"High drawdown detected: {current_dd:.1%}",
                        {"current_drawdown": f"{current_dd:.1%}"},
                    )
            else:
                drawdown_scale = Decimal("1.0")
                current_dd = Decimal("0")
        except Exception as e:
            logger.error(f"Error calculating drawdown scale: {e}")
            drawdown_scale = Decimal("1.0")
            current_dd = Decimal("0")

        # Create scaling factors
        factors = RiskScalingFactors(
            volatility_scale=volatility_scale,
            sharpe_scale=sharpe_scale,
            loss_scale=loss_scale,
            drawdown_scale=drawdown_scale,
        )

        # Check if extreme
        if factors.is_extreme:
            self._generate_alert(
                RiskAlertType.SCALING_EXTREME,
                RiskLevel.WARNING,
                f"Extreme scaling detected: combined factor {factors.combined_scale:.2f}",
                {
                    "combined_scale": f"{factors.combined_scale:.2f}",
                    "volatility_scale": f"{factors.volatility_scale:.2f}",
                    "sharpe_scale": f"{factors.sharpe_scale:.2f}",
                    "loss_scale": f"{factors.loss_scale:.2f}",
                    "drawdown_scale": f"{factors.drawdown_scale:.2f}",
                },
            )

        logger.info(
            f"{symbol} scaling factors calculated: "
            f"volatility={volatility_scale:.2f}, sharpe={sharpe_scale:.2f}, "
            f"loss={loss_scale:.2f}, drawdown={drawdown_scale:.2f}, "
            f"combined={factors.combined_scale:.2f}"
        )

        return factors

    async def apply_dynamic_scaling(
        self,
        signal: Dict,
        base_position_size: Decimal,
        stop_loss_price: Optional[Decimal],
        scaling_factors: RiskScalingFactors,
        current_price: Optional[Decimal] = None,
    ) -> AdjustedSignal:
        """
        Apply scaling factors to a trade signal.

        Args:
            signal: Trade signal dict with symbol, side, etc.
            base_position_size: Original position size
            stop_loss_price: Original stop loss price
            scaling_factors: All scaling factors
            current_price: Current price (for stop loss adjustment)

        Returns:
            AdjustedSignal with adjusted position size and stop loss
        """
        # Calculate adjusted position size
        combined_scale = scaling_factors.combined_scale
        adjusted_size = base_position_size * combined_scale
        adjusted_size = adjusted_size.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        # Determine if signal should be rejected
        is_rejected = adjusted_size == Decimal("0")
        rejection_reason = None

        if scaling_factors.drawdown_scale == Decimal("0"):
            rejection_reason = "Trading halted due to drawdown circuit breaker"
        elif combined_scale < Decimal("0.2"):
            rejection_reason = "Position size reduced to negligible amount by scaling"

        # Adjust stop loss if possible
        adjusted_stop_loss = stop_loss_price
        if (
            stop_loss_price is not None
            and current_price is not None
            and signal.get("side") == "buy"
        ):
            # For buy positions: increase stop distance in high volatility
            distance_pct = (current_price - stop_loss_price) / current_price
            adjusted_distance = distance_pct * scaling_factors.volatility_scale
            adjusted_stop_loss = current_price - (current_price * adjusted_distance)
            adjusted_stop_loss = adjusted_stop_loss.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        # Build reasons for adjustment
        reasons = []
        if scaling_factors.volatility_scale < Decimal("1.0"):
            reasons.append(f"High volatility: {scaling_factors.volatility_scale:.2f}x")
        if scaling_factors.sharpe_scale < Decimal("1.0"):
            reasons.append(f"Weak performance: {scaling_factors.sharpe_scale:.2f}x")
        if scaling_factors.loss_scale < Decimal("1.0"):
            reasons.append(f"Loss streak: {scaling_factors.loss_scale:.2f}x")
        if scaling_factors.drawdown_scale < Decimal("1.0"):
            reasons.append(f"Drawdown risk: {scaling_factors.drawdown_scale:.2f}x")

        return AdjustedSignal(
            signal_id=signal.get("signal_id", "unknown"),
            symbol=signal.get("symbol", ""),
            side=signal.get("side", "buy"),
            original_position_size=base_position_size,
            adjusted_position_size=adjusted_size,
            is_rejected=is_rejected,
            rejection_reason=rejection_reason,
            scaling_factors=scaling_factors,
            original_stop_loss=stop_loss_price,
            adjusted_stop_loss=adjusted_stop_loss,
        )

    async def get_scaling_state(
        self,
        portfolio_id: str,
        symbol: str,
        prices: Optional[List[PriceData]] = None,
        daily_returns: Optional[List[Decimal]] = None,
        trade_results: Optional[List[TradeResult]] = None,
        equity_curve: Optional[List[Decimal]] = None,
    ) -> RiskScalingState:
        """
        Get complete risk scaling state snapshot.

        Args:
            portfolio_id: Portfolio identifier
            symbol: Trading symbol
            prices: Price data
            daily_returns: Daily returns
            trade_results: Trade results
            equity_curve: Equity curve

        Returns:
            Complete RiskScalingState
        """
        # Calculate scaling factors
        scaling_factors = await self.calculate_scaling_factors(
            symbol, prices or [], daily_returns or [], trade_results, equity_curve
        )

        # Get individual metrics
        current_atr = Decimal("0")
        average_atr = Decimal("0")
        sharpe_ratio = Decimal("0")
        consecutive_losses = 0
        current_dd = Decimal("0")
        max_dd = Decimal("0")

        if prices:
            try:
                current_atr = self.volatility_monitor.calculate_atr(prices)
                # Calculate average ATR using 60-period lookback
                average_atr = self.volatility_monitor.calculate_average_atr(
                    symbol, prices, lookback_periods=60
                )
            except (ValueError, ZeroDivisionError, IndexError) as e:
                self.logger.warning(f"ATR calculation error: {e}")
                average_atr = current_atr  # Fallback to current

        if daily_returns:
            try:
                sharpe_ratio = await self.sharpe_monitor.calculate_rolling_sharpe(daily_returns)
            except (ValueError, ZeroDivisionError, IndexError) as e:
                self.logger.warning(f"Sharpe calculation error: {e}")

        if trade_results:
            consecutive_losses = self.loss_monitor.detect_consecutive_losses(trade_results)

        if equity_curve:
            try:
                current_dd, max_dd = self.drawdown_monitor.calculate_drawdown(equity_curve)
            except (ValueError, ZeroDivisionError, IndexError) as e:
                self.logger.warning(f"Drawdown calculation error: {e}")

        # Create snapshot
        snapshot = RiskScalingSnapshot(
            scaling_factors=scaling_factors,
            current_atr=current_atr,
            average_atr=average_atr,  # Now properly calculated
            sharpe_ratio=sharpe_ratio,
            consecutive_losses=consecutive_losses,
            current_drawdown=current_dd,
            max_drawdown=max_dd,
        )

        # Create state
        state = RiskScalingState(
            portfolio_id=portfolio_id,
            scaling_factors=scaling_factors,
            current_atr=current_atr,
            sharpe_ratio=sharpe_ratio,
            consecutive_losses=consecutive_losses,
            current_drawdown=current_dd,
            max_drawdown=max_dd,
            scaling_history=[snapshot],
            active_alerts=self.active_alerts.copy(),
        )

        # Add to history
        self.state_history.append(state)

        return state

    def generate_scaling_report(
        self,
        state: RiskScalingState,
        period: str = "current",
    ) -> RiskScalingReport:
        """Generate human-readable risk scaling report."""
        # Get average ATR from latest snapshot if available
        avg_atr = state.current_atr  # Default fallback
        if state.scaling_history:
            latest_snapshot = state.scaling_history[-1]
            avg_atr = latest_snapshot.average_atr

        return RiskScalingReport(
            portfolio_id=state.portfolio_id,
            period=period,
            current_combined_scale=state.scaling_factors.combined_scale,
            volatility_scale=state.scaling_factors.volatility_scale,
            sharpe_scale=state.scaling_factors.sharpe_scale,
            loss_scale=state.scaling_factors.loss_scale,
            drawdown_scale=state.scaling_factors.drawdown_scale,
            current_atr=state.current_atr,
            avg_atr=avg_atr,  # Now properly retrieved from snapshot
            sharpe_ratio=state.sharpe_ratio,
            consecutive_losses=state.consecutive_losses,
            current_drawdown=state.current_drawdown,
            max_drawdown=state.max_drawdown,
            active_alerts=[f"{a.alert_type}: {a.message}" for a in state.active_alerts],
            summary=self._generate_summary(state),
        )

    def _generate_alert(
        self,
        alert_type: RiskAlertType,
        severity: RiskLevel,
        message: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> RiskAlert:
        """Generate and store a risk alert."""
        alert = RiskAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            portfolio_id="",  # Set by caller
            metadata=metadata or {},
        )
        self.active_alerts.append(alert)
        logger.warning(f"Alert [{severity.value}] {alert_type.value}: {message}")
        return alert

    def _generate_summary(self, state: RiskScalingState) -> str:
        """Generate human-readable summary of risk status."""
        combined = state.scaling_factors.combined_scale

        if combined < Decimal("0.5"):
            summary = (
                f"Critical risk reduction active (scale {combined:.2f}x). "
                "Review market conditions and positions immediately."
            )
        elif combined < Decimal("0.8"):
            summary = (
                f"Significant risk reduction applied (scale {combined:.2f}x). "
                "Monitor conditions closely."
            )
        elif combined < Decimal("1.0"):
            summary = (
                f"Moderate risk reduction in effect (scale {combined:.2f}x). "
                "Normal trading with caution."
            )
        else:
            summary = (
                f"Normal trading conditions (scale {combined:.2f}x). "
                "All risk metrics within acceptable ranges."
            )

        return summary

    def calculate_position_size(
        self,
        capital: Decimal,
        win_rate: Decimal,
        avg_win: Decimal,
        avg_loss: Decimal,
        current_price: Decimal,
        max_position_pct: Decimal = Decimal("0.10"),
        min_position_value: Decimal = Decimal("100"),
        scaling_factors: Optional[RiskScalingFactors] = None,
    ) -> Decimal:
        """
        Calculate optimal position size using Kelly Criterion adjusted for risk.

        The Kelly Criterion formula: f* = (p * b - q) / b
        Where:
            f* = fraction of capital to bet
            p = probability of winning (win_rate)
            b = ratio of average win to average loss
            q = probability of losing (1 - p)

        We apply a half-Kelly adjustment for safety and combine with risk scaling.

        Args:
            capital: Total available capital
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade return (as decimal, e.g., 0.05 for 5%)
            avg_loss: Average losing trade loss (as decimal, positive, e.g., 0.02 for 2%)
            current_price: Current price per share
            max_position_pct: Maximum position size as % of capital (default 10%)
            min_position_value: Minimum position value in currency (default $100)
            scaling_factors: Optional risk scaling factors to apply

        Returns:
            Decimal: Optimal position size in shares (rounded down)

        Raises:
            ValueError: If inputs are invalid
        """
        # Input validation
        if capital <= Decimal("0"):
            raise ValueError(f"Capital must be positive, got: {capital}")
        if current_price <= Decimal("0"):
            raise ValueError(f"Current price must be positive, got: {current_price}")
        if not (Decimal("0") <= win_rate <= Decimal("1")):
            raise ValueError(f"Win rate must be between 0 and 1, got: {win_rate}")
        if avg_loss <= Decimal("0"):
            raise ValueError(f"Average loss must be positive, got: {avg_loss}")

        # Calculate Kelly fraction
        # f* = (p * b - q) / b where b = avg_win / avg_loss
        p = win_rate
        q = Decimal("1") - p

        if avg_loss == Decimal("0"):
            # Avoid division by zero
            logger.warning("avg_loss is zero, using max_position_pct directly")
            kelly_fraction = max_position_pct
        else:
            b = avg_win / avg_loss  # Win/loss ratio

            if b == Decimal("0"):
                kelly_fraction = Decimal("0")
            else:
                kelly_fraction = (p * b - q) / b

        # Apply half-Kelly for safety (reduces variance)
        half_kelly = kelly_fraction / Decimal("2")

        # Clamp Kelly fraction to valid range
        kelly_clamped = max(Decimal("0"), min(half_kelly, max_position_pct))

        # Apply risk scaling factors if provided
        if scaling_factors is not None:
            combined_scale = scaling_factors.combined_scale
            kelly_adjusted = kelly_clamped * combined_scale
            logger.debug(
                f"Kelly {kelly_clamped:.4f} × scaling {combined_scale:.2f} = {kelly_adjusted:.4f}"
            )
        else:
            kelly_adjusted = kelly_clamped

        # Calculate position value
        position_value = capital * kelly_adjusted

        # Enforce hard limits
        max_position_value = capital * max_position_pct
        position_value = min(position_value, max_position_value)
        position_value = max(position_value, min_position_value)

        # Additional safety: never risk more than 10% of capital per trade
        hard_limit = capital * Decimal("0.10")
        position_value = min(position_value, hard_limit)

        # Convert to shares
        shares = position_value / current_price
        shares = shares.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        # Ensure at least 1 share if position is valid
        if shares < Decimal("1") and position_value >= min_position_value:
            shares = Decimal("1")

        logger.info(
            f"Position size calculated: {shares} shares "
            f"(Kelly={kelly_clamped:.4f}, value=${position_value:.2f}, "
            f"capital=${capital:.2f}, price=${current_price:.2f})"
        )

        return shares

    def calculate_position_size_from_volatility(
        self,
        capital: Decimal,
        current_price: Decimal,
        atr: Decimal,
        risk_per_trade_pct: Decimal = Decimal("0.01"),
        atr_multiplier: Decimal = Decimal("2.0"),
        max_position_pct: Decimal = Decimal("0.10"),
    ) -> Decimal:
        """
        Calculate position size based on ATR (Average True Range) volatility.

        Uses the formula: Position Size = (Capital × Risk%) / (ATR × Multiplier)

        This approach sizes positions so that a move of ATR × multiplier
        results in a loss of risk_per_trade_pct of capital.

        Args:
            capital: Total available capital
            current_price: Current price per share
            atr: Average True Range value
            risk_per_trade_pct: Maximum risk per trade as % of capital (default 1%)
            atr_multiplier: ATR multiplier for stop distance (default 2.0)
            max_position_pct: Maximum position size as % of capital (default 10%)

        Returns:
            Decimal: Position size in shares
        """
        if capital <= Decimal("0") or current_price <= Decimal("0"):
            return Decimal("0")

        if atr <= Decimal("0"):
            logger.warning("ATR is zero or negative, using max_position_pct")
            position_value = capital * max_position_pct
        else:
            # Risk amount per trade
            risk_amount = capital * risk_per_trade_pct

            # Stop distance in price terms
            stop_distance = atr * atr_multiplier

            # Position size in shares = risk_amount / stop_distance
            if stop_distance > Decimal("0"):
                shares_from_risk = risk_amount / stop_distance
                position_value = shares_from_risk * current_price
            else:
                position_value = capital * max_position_pct

        # Enforce limits
        max_value = capital * max_position_pct
        position_value = min(position_value, max_value)

        # Convert to shares
        shares = (position_value / current_price).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        logger.debug(
            f"ATR-based position: {shares} shares "
            f"(ATR={atr:.4f}, risk={risk_per_trade_pct:.2%})"
        )

        return max(shares, Decimal("1"))
