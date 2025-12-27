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
        sharpe_ratio = Decimal("0")
        consecutive_losses = 0
        current_dd = Decimal("0")
        max_dd = Decimal("0")

        if prices:
            try:
                current_atr = self.volatility_monitor.calculate_atr(prices)
            except:
                pass

        if daily_returns:
            try:
                sharpe_ratio = await self.sharpe_monitor.calculate_rolling_sharpe(daily_returns)
            except:
                pass

        if trade_results:
            consecutive_losses = self.loss_monitor.detect_consecutive_losses(trade_results)

        if equity_curve:
            try:
                current_dd, max_dd = self.drawdown_monitor.calculate_drawdown(equity_curve)
            except:
                pass

        # Create snapshot
        snapshot = RiskScalingSnapshot(
            scaling_factors=scaling_factors,
            current_atr=current_atr,
            average_atr=current_atr,  # TODO: get actual average
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
        return RiskScalingReport(
            portfolio_id=state.portfolio_id,
            period=period,
            current_combined_scale=state.scaling_factors.combined_scale,
            volatility_scale=state.scaling_factors.volatility_scale,
            sharpe_scale=state.scaling_factors.sharpe_scale,
            loss_scale=state.scaling_factors.loss_scale,
            drawdown_scale=state.scaling_factors.drawdown_scale,
            current_atr=state.current_atr,
            avg_atr=state.current_atr,  # TODO: track average
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
                f"Review market conditions and positions immediately."
            )
        elif combined < Decimal("0.8"):
            summary = (
                f"Significant risk reduction applied (scale {combined:.2f}x). "
                f"Monitor conditions closely."
            )
        elif combined < Decimal("1.0"):
            summary = (
                f"Moderate risk reduction in effect (scale {combined:.2f}x). "
                f"Normal trading with caution."
            )
        else:
            summary = (
                f"Normal trading conditions (scale {combined:.2f}x). "
                f"All risk metrics within acceptable ranges."
            )

        return summary
