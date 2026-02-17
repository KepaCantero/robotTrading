"""
Compliance-Aware Trading Wrapper

This module provides wrapper classes that integrate THE Compliance Engine
into the three main trading systems:
1. Backtesting
2. Live Trading
3. Paper Trading

THE ONLY ENGINE: ComplianceEngine
Everything goes through ComplianceEngine.

Usage:
    # In backtesting
    from app.trading_compliance import ComplianceAwareBacktester

    backtester = ComplianceAwareBacktester(
        base_backtester=original_backtester,
    )

    # In live trading
    from app.trading_compliance import ComplianceAwareLiveTrader

    trader = ComplianceAwareLiveTrader(
        base_adapter=alpaca_adapter,
    )

    # In paper trading
    from app.trading_compliance import ComplianceAwarePaperTrader

    paper_trader = ComplianceAwarePaperTrader(
        base_adapter=paper_adapter,
    )
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pandas as pd

# USE THE NEW COMPLIANCE ENGINE
from app.core.compliance_engine import PostTradeAnalysis, PreTradeAnalysis, get_compliance_engine
from app.core.centralized_config import get_config

# Avoid circular imports
if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# COMPLIANCE-AWARE BACKTESTER
# =============================================================================


class ComplianceAwareBacktester:
    """
    Wrapper for backtester that uses THE Compliance Engine.

    This is the ONLY wrapper that should be used for backtesting.
    """

    def __init__(
        self,
        base_backtester: Any,
        enable_compliance: bool = True,
        log_compliance: bool = True,
    ):
        """
        Initialize compliance-aware backtester.

        Args:
            base_backtester: The original backtester to wrap
            enable_compliance: Whether to enable compliance checks
            log_compliance: Whether to log compliance decisions
        """
        self.base_backtester = base_backtester
        self.enable_compliance = enable_compliance
        self.log_compliance = log_compliance

        # THE ONLY ENGINE
        if enable_compliance:
            self.engine = get_compliance_engine(enable_logging=log_compliance)
        else:
            self.engine = None

        # Track compliance metrics
        self.compliance_metrics = {
            "total_signals": 0,
            "blocked_by_compliance": 0,
            "passed_through": 0,
            "avg_market_impact_bps": 0.0,
        }

        logger.info("ComplianceAwareBacktester initialized")

    def execute_with_compliance(
        self,
        quotes: List[Any],
        price_history: Optional[pd.DataFrame] = None,
    ) -> Any:
        """
        Execute backtest with compliance awareness.

        Args:
            quotes: Historical quote data
            price_history: Price history DataFrame for compliance analysis

        Returns:
            BacktestResult with compliance enhancements
        """
        if not self.enable_compliance:
            return self.base_backtester.execute(quotes)

        logger.info("Running backtest with COMPLIANCE ENGINE")

        # Store price history for compliance checks
        self._price_history = price_history

        # Run backtest (this will call our wrapped methods)
        result = self.base_backtester.execute(quotes)

        # Enhance result with compliance metrics
        if hasattr(result, '__dict__'):
            result.compliance_metrics = self.compliance_metrics
            result.compliance_enabled = True

        logger.info(
            f"Compliance Backtest Complete: "
            f"{self.compliance_metrics['passed_through']}/{self.compliance_metrics['total_signals']} signals executed"
        )

        return result

    def check_signal(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        timestamp: datetime,
    ) -> Tuple[bool, Optional[str], Optional[PreTradeAnalysis]]:
        """
        Check if a trading signal passes compliance checks.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            price: Current price
            timestamp: Signal timestamp

        Returns:
            Tuple of (can_execute, reason, analysis)
        """
        self.compliance_metrics["total_signals"] += 1

        if not self.enable_compliance or not self.engine:
            return True, None, None

        # Get price history slice up to this timestamp
        price_history_slice = None
        if hasattr(self, '_price_history') and self._price_history is not None:
            price_history_slice = (
                self._price_history[self._price_history.index <= timestamp]
                if hasattr(self._price_history, 'index')
                else None
            )

        # Use THE Compliance Engine
        analysis = self.engine.analyze_pre_trade(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            price_history=price_history_slice,
            urgency=0.5,
        )

        # Log compliance decision
        if self.log_compliance:
            logger.info(
                f"Compliance Check {symbol}: "
                f"can_execute={analysis.can_execute}, "
                f"confidence={analysis.confidence:.0%}, "
                f"regime={analysis.market_regime}, "
                f"liquidity={analysis.liquidity_regime}"
            )

        # Update metrics
        if not analysis.can_execute:
            self.compliance_metrics["blocked_by_compliance"] += 1
            reason = "; ".join(analysis.reasons)
            return False, reason, analysis

        # Get high cost threshold from config
        config = get_config()
        high_cost_threshold = config.compliance.MAX_SLIPPAGE_BPS * 2  # Example: 2x max slippage

        if analysis.total_cost_bps > high_cost_threshold:
            self.compliance_metrics["passed_through"] += 1
            return True, f"High cost - consider splitting ({analysis.total_cost_bps:.1f} bps)", analysis

        self.compliance_metrics["passed_through"] += 1

        # Update average market impact
        n = self.compliance_metrics["total_signals"]
        if n > 0:
            self.compliance_metrics["avg_market_impact_bps"] = (
                self.compliance_metrics["avg_market_impact_bps"] * (n - 1) + analysis.total_cost_bps
            ) / n

        return True, None, analysis

    def simulate_execution(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        timestamp: datetime,
    ) -> Tuple[Decimal, float]:
        """
        Simulate execution with realistic transaction costs.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            price: Intended price
            timestamp: Execution timestamp

        Returns:
            Tuple of (execution_price, market_impact_bps)
        """
        if not self.enable_compliance or not self.engine:
            return price, 0.0

        # Get compliance analysis
        can_execute, reason, analysis = self.check_signal(symbol, side, quantity, price, timestamp)

        if not can_execute:
            # Return with high cost to discourage execution
            # Use config for high penalty value
            config = get_config()
            high_penalty_bps = config.compliance.MAX_SLIPPAGE_BPS * 100  # 1000 bps penalty
            return price, float(high_penalty_bps)

        # Calculate execution price with market impact
        impact_bps = analysis.total_cost_bps

        # Get BPS multiplier from config
        config = get_config()
        bps_multiplier = Decimal(str(config.trading.bps_multiplier))

        if side == "BUY":
            execution_price = price * (Decimal("1") + Decimal(str(impact_bps)) / bps_multiplier)
        else:  # SELL
            execution_price = price * (Decimal("1") - Decimal(str(impact_bps)) / bps_multiplier)

        return execution_price, impact_bps

    def optimize_portfolio(
        self,
        symbols: List[str],
        returns: pd.DataFrame,
        current_prices: Dict[str, Decimal],
    ) -> Dict[str, Decimal]:
        """
        Get portfolio weights using THE Compliance Engine.

        Args:
            symbols: List of symbols
            returns: Returns DataFrame
            current_prices: Current prices for each symbol

        Returns:
            Dictionary of symbol -> weight
        """
        if not self.enable_compliance or not self.engine:
            weight = Decimal("1") / Decimal(str(len(symbols)))
            return {s: weight for s in symbols}

        result = self.engine.optimize_portfolio(
            symbols=symbols,
            returns=returns,
            current_prices=current_prices,
        )

        return result.weights


# =============================================================================
# COMPLIANCE-AWARE LIVE TRADER
# =============================================================================


class ComplianceAwareLiveTrader:
    """
    Wrapper for live trading adapter that uses THE Compliance Engine.

    This is the ONLY wrapper that should be used for live trading.
    """

    def __init__(
        self,
        base_adapter: Any,
        enable_compliance: bool = True,
        strict_mode: bool = True,
        max_latency_ms: float = 100.0,
    ):
        """
        Initialize compliance-aware live trader.

        Args:
            base_adapter: The original broker adapter (Alpaca, etc.)
            enable_compliance: Whether to enable compliance checks
            strict_mode: If True, block orders that fail compliance
            max_latency_ms: Maximum acceptable latency (SLO)
        """
        self.base_adapter = base_adapter
        self.enable_compliance = enable_compliance
        self.strict_mode = strict_mode
        self.max_latency_ms = max_latency_ms

        # THE ONLY ENGINE
        if enable_compliance:
            self.engine = get_compliance_engine(enable_logging=True)
        else:
            self.engine = None

        # Track orders
        self._order_tracking: Dict[str, Dict[str, Any]] = {}

        logger.info(f"ComplianceAwareLiveTrader initialized (strict={strict_mode})")

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str = "LIMIT",
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "DAY",
        urgency: float = 0.5,
        signal_time: Optional[datetime] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Place order with comprehensive compliance checks.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            order_type: MARKET, LIMIT, STOP, etc.
            price: Limit price (if applicable)
            stop_price: Stop price (if applicable)
            time_in_force: DAY, GTC, IOC, etc.
            urgency: Execution urgency (0-1)
            signal_time: When the signal was generated

        Returns:
            Tuple of (success, order_id_or_error, venue_or_algorithm)
        """
        order_id = f"cmp_{uuid.uuid4().hex[:8]}"
        submission_time = datetime.now()

        # Track order
        self._order_tracking[order_id] = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "submission_time": submission_time,
            "signal_time": signal_time,
            "order_type": order_type,
        }

        # -------------------------------------------------------------------------
        # STEP 1: Pre-trade Compliance Check using THE Compliance Engine
        # -------------------------------------------------------------------------
        if self.enable_compliance and self.engine:
            current_price = price or Decimal("100.00")

            # Use THE Compliance Engine
            analysis = self.engine.analyze_pre_trade(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=current_price,
                price_history=None,  # Would need real-time data feed
                urgency=urgency,
                signal_time=signal_time,
            )

            # Track submission in engine
            self.engine.track_order_submission(
                order_id=order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                submission_time=submission_time,
            )

            logger.info(
                f"Pre-trade check for {symbol}: "
                f"can_execute={analysis.can_execute}, "
                f"confidence={analysis.confidence:.0%}"
            )

            if not analysis.can_execute:
                error_msg = f"Compliance check failed: {'; '.join(analysis.reasons)}"
                logger.warning(f"Order BLOCKED: {error_msg}")
                return False, error_msg, None

            # Apply compliance recommendations
            if analysis.limit_price and not price:
                price = analysis.limit_price

            order_type = analysis.algorithm
            venue = analysis.venue

            logger.info(
                f"Compliance recommendations: "
                f"algorithm={order_type}, venue={venue}, "
                f"limit_price={price}, est_cost={analysis.total_cost_bps:.1f}bps"
            )
        else:
            venue = "lit_exchange"

        # -------------------------------------------------------------------------
        # STEP 2: Submit Order to Base Adapter
        # -------------------------------------------------------------------------
        try:
            from app.services.live_trading.broker_connector import OrderSide

            side_enum = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

            actual_order_id = await self.base_adapter.place_order(
                symbol=symbol,
                side=side_enum,
                quantity=quantity,
                order_type=order_type,  # type: ignore
                price=price,
                stop_price=stop_price,
            )

            self._order_tracking[order_id]["actual_order_id"] = actual_order_id
            self._order_tracking[order_id]["submitted"] = True

            logger.info(f"Order submitted: {actual_order_id} ({venue})")

            return True, actual_order_id, venue

        except Exception as e:
            error_msg = f"Order submission failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None

    async def analyze_execution(
        self,
        order_id: str,
        execution_price: Decimal,
        execution_time: datetime,
        nbbo: Optional[Tuple[Decimal, Decimal]] = None,
    ) -> Optional[PostTradeAnalysis]:
        """
        Analyze execution quality after order is filled.

        Args:
            order_id: Internal order ID
            execution_price: Actual execution price
            execution_time: Execution timestamp
            nbbo: NBBO at execution time (bid, ask)

        Returns:
            PostTradeAnalysis or None
        """
        if order_id not in self._order_tracking:
            logger.warning(f"Unknown order ID: {order_id}")
            return None

        tracking = self._order_tracking[order_id]

        # Use THE Compliance Engine for post-trade analysis
        if self.enable_compliance and self.engine:
            analysis = self.engine.analyze_post_trade(
                order_id=order_id,
                symbol=tracking["symbol"],
                side=tracking["side"],
                quantity=Decimal(str(tracking["quantity"])),
                execution_price=execution_price,
                signal_price=None,
                signal_time=tracking.get("signal_time"),
                submission_time=tracking["submission_time"],
                execution_time=execution_time,
                nbbo=nbbo,
            )

            # Track completion in engine
            self.engine.track_order_completion(
                order_id=order_id,
                execution_price=execution_price,
                execution_time=execution_time,
            )

            logger.info(
                f"Post-trade analysis for {tracking['symbol']}: "
                f"quality_score={analysis.execution_quality_score:.0f}, "
                f"implementation_shortfall={analysis.implementation_shortfall_bps:.1f}bps"
            )

            return analysis

        return None

    def get_slo_metrics(self) -> Dict[str, Any]:
        """Get current SLO metrics from THE Compliance Engine."""
        if self.enable_compliance and self.engine:
            return self.engine.get_slo_metrics()

        return {
            "total_trades": 0,
            "slo_violations": 0,
            "slo_compliance_rate": 1.0,
            "avg_latency_ms": 0.0,
        }


# =============================================================================
# COMPLIANCE-AWARE PAPER TRADER
# =============================================================================


class ComplianceAwarePaperTrader:
    """
    Wrapper for paper trading adapter that uses THE Compliance Engine.

    This is the ONLY wrapper that should be used for paper trading.
    """

    def __init__(
        self,
        base_adapter: Any,
        enable_compliance: bool = True,
        realistic_simulation: bool = True,
    ):
        """
        Initialize compliance-aware paper trader.

        Args:
            base_adapter: The original paper trading adapter
            enable_compliance: Whether to enable compliance checks
            realistic_simulation: Use realistic market microstructure simulation
        """
        self.base_adapter = base_adapter
        self.enable_compliance = enable_compliance
        self.realistic_simulation = realistic_simulation

        # THE ONLY ENGINE
        if enable_compliance:
            self.engine = get_compliance_engine(enable_logging=True)
        else:
            self.engine = None

        # Simulation parameters - use config for default spread
        config = get_config()
        self._default_spread_bps = config.compliance.ESTIMATED_SPREAD_BPS

        logger.info("ComplianceAwarePaperTrader initialized")

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str = "LIMIT",
        price: Optional[Decimal] = None,
        urgency: float = 0.5,
    ) -> Tuple[bool, str, Optional[float]]:
        """
        Place order with realistic market simulation.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            order_type: Order type
            price: Limit price
            urgency: Execution urgency (0-1)

        Returns:
            Tuple of (success, order_id, execution_price_with_impact)
        """
        base_price = price or Decimal("100.00")

        # -------------------------------------------------------------------------
        # STEP 1: Calculate Realistic Execution Price using THE Compliance Engine
        # -------------------------------------------------------------------------
        if self.realistic_simulation and self.engine:
            # Get BPS multiplier from config
            config = get_config()
            bps_multiplier = Decimal(str(config.trading.bps_multiplier))

            # Use THE Compliance Engine
            analysis = self.engine.analyze_pre_trade(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=base_price,
                price_history=None,
                urgency=urgency,
            )

            impact_bps = analysis.total_cost_bps

            if side == "BUY":
                execution_price = base_price * (
                    Decimal("1")
                    + (
                        Decimal(str(self._default_spread_bps)) / Decimal("2")
                        + Decimal(str(impact_bps))
                    )
                    / bps_multiplier
                )
            else:  # SELL
                execution_price = base_price * (
                    Decimal("1")
                    - (
                        Decimal(str(self._default_spread_bps)) / Decimal("2")
                        + Decimal(str(impact_bps))
                    )
                    / bps_multiplier
                )

            logger.info(
                f"Realistic simulation: {symbol} {side} {quantity} "
                f"@ ${float(execution_price):.2f} "
                f"(impact: {impact_bps:.1f}bps)"
            )

        else:
            execution_price = base_price
            impact_bps = 0.0

        # -------------------------------------------------------------------------
        # STEP 2: Submit Order to Base Adapter
        # -------------------------------------------------------------------------
        from app.services.live_trading.broker_connector import OrderSide

        side_enum = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

        order_id = await self.base_adapter.place_order(
            symbol=symbol,
            side=side_enum,
            quantity=quantity,
            order_type=order_type,  # type: ignore
            price=execution_price,
        )

        return True, order_id, float(execution_price)

    def get_simulation_stats(self) -> Dict[str, Any]:
        """Get simulation statistics."""
        return {
            "realistic_simulation": self.realistic_simulation,
            "default_spread_bps": self._default_spread_bps,
            "compliance_enabled": self.enable_compliance,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def wrap_backtester(
    backtester: Any,
    enable_compliance: bool = True,
) -> ComplianceAwareBacktester:
    """Wrap a backtester with compliance awareness."""
    return ComplianceAwareBacktester(
        base_backtester=backtester,
        enable_compliance=enable_compliance,
    )


def wrap_live_trader(
    adapter: Any,
    enable_compliance: bool = True,
    strict_mode: bool = True,
) -> ComplianceAwareLiveTrader:
    """Wrap a live trading adapter with compliance awareness."""
    return ComplianceAwareLiveTrader(
        base_adapter=adapter,
        enable_compliance=enable_compliance,
        strict_mode=strict_mode,
    )


def wrap_paper_trader(
    adapter: Any,
    enable_compliance: bool = True,
    realistic_simulation: bool = True,
) -> ComplianceAwarePaperTrader:
    """Wrap a paper trading adapter with compliance awareness."""
    return ComplianceAwarePaperTrader(
        base_adapter=adapter,
        enable_compliance=enable_compliance,
        realistic_simulation=realistic_simulation,
    )


if __name__ == "__main__":
    # Test the wrappers
    logging.basicConfig(level=logging.INFO)

    logger.debug("=" * 80)
    logger.debug("COMPLIANCE-AWARE TRADING WRAPPERS")
    logger.debug("=" * 80)
    logger.debug("\nAll wrappers use THE ComplianceEngine:")
    logger.debug("  1. ComplianceAwareBacktester - For backtesting")
    logger.debug("  2. ComplianceAwareLiveTrader - For live trading")
    logger.debug("  3. ComplianceAwarePaperTrader - For paper trading")
    logger.debug("\nConvenience functions:")
    logger.debug("  - wrap_backtester()")
    logger.debug("  - wrap_live_trader()")
    logger.debug("  - wrap_paper_trader()")
    logger.debug("=" * 80)
