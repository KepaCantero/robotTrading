"""
Execution Algorithms - Rishi Narang "Inside the Black Box" Chapter 7

This module implements the Execution algorithms from Narang's framework:
- Order routing
- Execution algorithms (VWAP, TWAP, POV, etc.)
- Market impact minimization
- Execution quality analysis

Key concepts from "Inside the Black Box":
- Execution is where theoretical alpha becomes realized P&L
- Execution algorithms minimize market impact for large orders
- Choice of algorithm depends on order size, urgency, and market conditions
- Execution quality should be monitored and continuously improved

From Narang: "Execution is the process of trading the portfolio determined
by the portfolio construction model. The goal is to minimize the cost of
trading while achieving the desired portfolio position."
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.services.transaction_costs import ExecutionAlgorithm  # Enum
from app.services.transaction_costs import MarketData, OrderSpecification, TransactionCostModel
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    """Status of an order."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(str, Enum):
    """Types of orders."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class TimeInForce(str, Enum):
    """Time in force for orders."""

    DAY = "DAY"  # Valid for the trading day only
    GTC = "GTC"  # Good til cancelled
    IOC = "IOC"  # Immediate or cancel
    FOK = "FOK"  # Fill or kill
    OPG = "OPG"  # At the open
    CLS = "CLS"  # At the close


class OrderSide(str, Enum):
    """Side of an order."""

    BUY = "buy"
    SELL = "sell"
    SHORT = "short"


@dataclass
class ChildOrder:
    """A child order in an execution algorithm."""

    order_id: str
    parent_order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    target_time: Optional[datetime] = None
    target_participation_rate: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Decimal = Decimal("0")
    average_fill_price: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None


@dataclass
class ExecutionReport:
    """Report on execution quality."""

    order_id: str
    symbol: str
    side: OrderSide
    target_quantity: Decimal
    filled_quantity: Decimal
    average_price: Decimal
    benchmark_price: Decimal  # VWAP, decision price, etc.
    implementation_shortfall_bps: float  # Difference from benchmark
    market_impact_bps: float
    timing_cost_bps: float
    total_cost_bps: float
    execution_duration_seconds: float
    fill_rate: float  # filled_quantity / target_quantity
    slippage_bps: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IntradayVolumeProfile:
    """Historical intraday volume distribution for VWAP/TWAP."""

    symbol: str
    time_bins: List[datetime.time]  # Time intervals
    volume_distribution: List[float]  # % of volume at each interval
    total_daily_volume: Decimal


class ExecutionAlgoBase(ABC):
    """
    Abstract base class for execution algorithms.

    From Narang: Execution algorithms should:
    1. Minimize market impact
    2. Control timing risk
    3. Handle market conditions
    4. Achieve target participation or benchmark
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.algorithm_type = ExecutionAlgorithm[config.get("algorithm_type", "MARKET").upper()]
        self.max_participation_rate = config.get("max_participation_rate", 0.20)
        self.min_fill_size = config.get("min_fill_size", Decimal("100"))

    @abstractmethod
    def generate_child_orders(
        self,
        parent_order: OrderSpecification,
        market_data: MarketData,
        start_time: datetime,
        end_time: datetime,
    ) -> List[ChildOrder]:
        """
        Generate child orders for execution.

        Args:
            parent_order: The parent order to execute
            market_data: Current market data
            start_time: Start of execution window
            end_time: End of execution window

        Returns:
            List of child orders to execute
        """

    @abstractmethod
    def should_update_child_orders(
        self,
        parent_order: OrderSpecification,
        child_orders: List[ChildOrder],
        market_data: MarketData,
    ) -> Tuple[bool, List[ChildOrder]]:
        """
        Determine if child orders should be updated based on market conditions.

        Returns:
            Tuple of (should_update, updated_child_orders)
        """

    def calculate_implementation_shortfall(
        self,
        execution_report: ExecutionReport,
    ) -> float:
        """
        Calculate implementation shortfall.

        From Narang: Implementation shortfall = (decision_price - execution_price) +
        (market_movement during execution) + (opportunity cost of unfilled shares)

        Simplified: (benchmark_price - avg_price) / benchmark_price * BPS_MULTIPLIER
        """
        if execution_report.benchmark_price == 0:
            return 0.0

        tt = get_config().trading_thresholds
        shortfall = (
            float(execution_report.benchmark_price - execution_report.average_price)
            / float(execution_report.benchmark_price)
            * tt.bps_multiplier
        )

        return shortfall


class VWAPExecution(ExecutionAlgoBase):
    """
    Volume-Weighted Average Price (VWAP) execution algorithm.

    From Narang: VWAP is the most common execution algorithm.
    It splits orders proportionally to historical volume patterns.

    Key benefits:
    - Minimizes market impact by trading with volume
    - Predictable execution pattern
    - Benchmark commonly used by traders
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.algorithm_type = ExecutionAlgorithm.VWAP
        self.volume_profile_lookback = config.get("volume_profile_lookback", 20)  # days

    def generate_child_orders(
        self,
        parent_order: OrderSpecification,
        market_data: MarketData,
        start_time: datetime,
        end_time: datetime,
    ) -> List[ChildOrder]:
        """
        Generate VWAP child orders.

        From Narang: "Dividir orden en child orders proporcionales a volumen histórico"
        """
        # Get intraday volume profile
        volume_profile = self._get_intraday_volume_profile(
            parent_order.symbol, market_data.timestamp
        )

        if not volume_profile:
            logger.warning(f"No volume profile available for {parent_order.symbol}")
            return []

        # Calculate time slices (e.g., every 5 minutes)
        time_slices = self._generate_time_slices(start_time, end_time, minutes=5)

        child_orders = []
        total_quantity = parent_order.quantity
        allocated_quantity = Decimal("0")

        for i, slice_time in enumerate(time_slices[:-1]):
            # Find corresponding volume distribution
            slice_pct = self._get_volume_percentage(slice_time.time(), volume_profile)

            # Calculate quantity for this slice
            slice_quantity = total_quantity * Decimal(str(slice_pct))

            if slice_quantity < self.min_fill_size:
                continue

            # Estimate limit price (near current price with some tolerance)
            limit_price = self._calculate_vwap_limit_price(market_data, parent_order.side)

            child_order = ChildOrder(
                order_id=f"vwap_{parent_order.symbol}_{i}_{slice_time.strftime('%H%M')}",
                parent_order_id=f"parent_{parent_order.symbol}",
                symbol=parent_order.symbol,
                side=OrderSide.BUY if parent_order.side == "buy" else OrderSide.SELL,
                quantity=slice_quantity,
                order_type=OrderType.LIMIT,
                limit_price=limit_price,
                time_in_force=TimeInForce.IOC,  # Immediate or cancel for VWAP
                target_time=slice_time,
            )

            child_orders.append(child_order)
            allocated_quantity += slice_quantity

        # Allocate remaining quantity to last slice
        remaining = total_quantity - allocated_quantity
        if remaining > Decimal("0"):
            child_orders.append(
                ChildOrder(
                    order_id=f"vwap_{parent_order.symbol}_{len(time_slices)}_{time_slices[-1].strftime('%H%M')}",
                    parent_order_id=f"parent_{parent_order.symbol}",
                    symbol=parent_order.symbol,
                    side=OrderSide.BUY if parent_order.side == "buy" else OrderSide.SELL,
                    quantity=remaining,
                    order_type=OrderType.LIMIT,
                    limit_price=self._calculate_vwap_limit_price(market_data, parent_order.side),
                    time_in_force=TimeInForce.IOC,
                    target_time=time_slices[-1],
                )
            )

        logger.info(f"Generated {len(child_orders)} VWAP child orders for {parent_order.symbol}")
        return child_orders

    def should_update_child_orders(
        self,
        parent_order: OrderSpecification,
        child_orders: List[ChildOrder],
        market_data: MarketData,
    ) -> Tuple[bool, List[ChildOrder]]:
        """VWAP typically doesn't update child orders."""
        return False, child_orders

    def _get_intraday_volume_profile(
        self, symbol: str, current_time: datetime
    ) -> Optional[IntradayVolumeProfile]:
        """
        Get historical intraday volume distribution.

        In production, this would query a database of historical intraday volume.
        For now, return a default profile (U-shaped: higher at open and close).
        """
        # Default U-shaped volume profile
        time_bins = []
        volume_dist = []

        # Create 5-minute bins from 9:30 to 16:00
        base_time = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        end_time = current_time.replace(hour=16, minute=0, second=0, microsecond=0)

        while base_time < end_time:
            time_bins.append(base_time.time())
            base_time += timedelta(minutes=5)

        # U-shaped distribution: higher at open and close
        n_bins = len(time_bins)
        for i in range(n_bins):
            # Normalized position from 0 to 1
            pos = i / max(1, n_bins - 1)
            # U-shape: higher at ends (0 and 1)
            base_volume = 0.5 + 2 * ((pos - 0.5) ** 2)
            volume_dist.append(base_volume)

        # Normalize to sum to 1
        total = sum(volume_dist)
        volume_dist = [v / total for v in volume_dist]

        # Use default total daily volume (in production, query from database)
        total_daily_volume = Decimal("1000000")

        return IntradayVolumeProfile(
            symbol=symbol,
            time_bins=[t for t in time_bins],
            volume_distribution=volume_dist,
            total_daily_volume=total_daily_volume,
        )

    def _generate_time_slices(
        self, start_time: datetime, end_time: datetime, minutes: int = 5
    ) -> List[datetime]:
        """Generate time slices for execution."""
        slices = []
        current = start_time

        while current < end_time:
            slices.append(current)
            current += timedelta(minutes=minutes)

        # Add end time as final slice
        if slices and slices[-1] != end_time:
            slices.append(end_time)

        return slices

    def _get_volume_percentage(self, time: datetime.time, profile: IntradayVolumeProfile) -> float:
        """Get volume percentage for a given time."""
        for i, bin_time in enumerate(profile.time_bins):
            if time.hour == bin_time.hour and time.minute >= bin_time.minute:
                if i + 1 < len(profile.time_bins):
                    next_time = profile.time_bins[i + 1]
                    if time.minute < next_time.minute:
                        return profile.volume_distribution[i]

        # Default to last bin
        return profile.volume_distribution[-1] if profile.volume_distribution else 0.0

    def _calculate_vwap_limit_price(self, market_data: MarketData, side: str) -> Decimal:
        """Calculate limit price for VWAP child order."""
        # Set limit price near mid price with tolerance
        mid = market_data.mid_price
        tolerance = market_data.spread * Decimal("0.5")

        if side == "buy":
            return mid + tolerance  # Slightly above mid
        else:
            return mid - tolerance  # Slightly below mid


class TWAPExecution(ExecutionAlgoBase):
    """
    Time-Weighted Average Price (TWAP) execution algorithm.

    From Narang: TWAP spreads orders evenly over time.
    Simpler than VWAP but less effective at minimizing impact.

    Best for:
    - Stocks with stable volume throughout the day
    - Simplicity over optimization
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.algorithm_type = ExecutionAlgorithm.TWAP

    def generate_child_orders(
        self,
        parent_order: OrderSpecification,
        market_data: MarketData,
        start_time: datetime,
        end_time: datetime,
    ) -> List[ChildOrder]:
        """
        Generate TWAP child orders.

        Splits order evenly across time slices.
        """
        # Generate time slices
        time_slices = self._generate_time_slices(start_time, end_time, minutes=10)

        if not time_slices:
            return []

        # Equal quantity per slice
        quantity_per_slice = (parent_order.quantity / Decimal(str(len(time_slices)))).quantize(
            Decimal("0.01")
        )

        child_orders = []

        for i, slice_time in enumerate(time_slices):
            if quantity_per_slice < self.min_fill_size:
                continue

            limit_price = self._calculate_twap_limit_price(market_data, parent_order.side)

            child_order = ChildOrder(
                order_id=f"twap_{parent_order.symbol}_{i}_{slice_time.strftime('%H%M')}",
                parent_order_id=f"parent_{parent_order.symbol}",
                symbol=parent_order.symbol,
                side=OrderSide.BUY if parent_order.side == "buy" else OrderSide.SELL,
                quantity=quantity_per_slice,
                order_type=OrderType.LIMIT,
                limit_price=limit_price,
                time_in_force=TimeInForce.IOC,
                target_time=slice_time,
            )

            child_orders.append(child_order)

        logger.info(f"Generated {len(child_orders)} TWAP child orders for {parent_order.symbol}")
        return child_orders

    def should_update_child_orders(
        self,
        parent_order: OrderSpecification,
        child_orders: List[ChildOrder],
        market_data: MarketData,
    ) -> Tuple[bool, List[ChildOrder]]:
        """TWAP typically doesn't update child orders."""
        return False, child_orders

    def _generate_time_slices(
        self, start_time: datetime, end_time: datetime, minutes: int = 10
    ) -> List[datetime]:
        """Generate time slices for execution."""
        slices = []
        current = start_time

        while current < end_time:
            slices.append(current)
            current += timedelta(minutes=minutes)

        if slices and slices[-1] != end_time:
            slices.append(end_time)

        return slices

    def _calculate_twap_limit_price(self, market_data: MarketData, side: str) -> Decimal:
        """Calculate limit price for TWAP child order."""
        mid = market_data.mid_price
        tolerance = market_data.spread * Decimal("0.5")

        if side == "buy":
            return mid + tolerance
        else:
            return mid - tolerance


class POVExecution(ExecutionAlgoBase):
    """
    Percentage of Volume (POV) execution algorithm.

    From Narang: POV executes at a fixed percentage of market volume.
    Adapts to actual market conditions in real-time.

    Best for:
    - Very large orders
    - Controlling participation rate
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.algorithm_type = ExecutionAlgorithm.POV
        self.target_participation_rate = config.get("target_participation_rate", 0.10)  # 10%

    def generate_child_orders(
        self,
        parent_order: OrderSpecification,
        market_data: MarketData,
        start_time: datetime,
        end_time: datetime,
    ) -> List[ChildOrder]:
        """
        Generate POV child orders.

        Creates a single order that will be managed to maintain target participation.
        """
        # For POV, we create a single child order that will be sliced dynamically
        child_order = ChildOrder(
            order_id=f"pov_{parent_order.symbol}_{start_time.strftime('%H%M')}",
            parent_order_id=f"parent_{parent_order.symbol}",
            symbol=parent_order.symbol,
            side=OrderSide.BUY if parent_order.side == "buy" else OrderSide.SELL,
            quantity=parent_order.quantity,
            order_type=OrderType.LIMIT,
            limit_price=self._calculate_pov_limit_price(market_data, parent_order.side),
            time_in_force=TimeInForce.DAY,
            target_participation_rate=self.target_participation_rate,
        )

        logger.info(
            f"Generated POV child order for {parent_order.symbol} at {self.target_participation_rate:.1%} participation"
        )
        return [child_order]

    def should_update_child_orders(
        self,
        parent_order: OrderSpecification,
        child_orders: List[ChildOrder],
        market_data: MarketData,
    ) -> Tuple[bool, List[ChildOrder]]:
        """
        POV should update based on actual volume traded.

        In a real implementation, this would track actual volume and adjust.
        """
        # Simplified: return current orders
        return False, child_orders

    def _calculate_pov_limit_price(self, market_data: MarketData, side: str) -> Decimal:
        """Calculate limit price for POV order."""
        mid = market_data.mid_price
        tolerance = market_data.spread * Decimal("0.3")  # Tighter for POV

        if side == "buy":
            return mid - tolerance  # Slightly below mid for POV buy
        else:
            return mid + tolerance  # Slightly above mid for POV sell


class MarketExecution(ExecutionAlgoBase):
    """
    Immediate market execution.

    From Narang: Only for small orders where market impact is negligible.
    WARNING: "NUNCA uses Market Orders para órdenes > 1% ADV"
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.algorithm_type = ExecutionAlgorithm.MARKET
        self.max_order_size_pct = config.get("max_order_size_pct", 0.01)  # 1% of ADV

    def generate_child_orders(
        self,
        parent_order: OrderSpecification,
        market_data: MarketData,
        start_time: datetime,
        end_time: datetime,
    ) -> List[ChildOrder]:
        """
        Generate immediate market order.

        WARNING: Only use for small orders!
        """
        participation_rate = float(parent_order.quantity) / float(market_data.average_daily_volume)

        if participation_rate > self.max_order_size_pct:
            logger.warning(
                f"Order size {participation_rate:.2%} of ADV exceeds recommended "
                f"threshold {self.max_order_size_pct:.2%} for market execution. "
                f"Consider VWAP or TWAP instead."
            )

        child_order = ChildOrder(
            order_id=f"market_{parent_order.symbol}",
            parent_order_id=f"parent_{parent_order.symbol}",
            symbol=parent_order.symbol,
            side=OrderSide.BUY if parent_order.side == "buy" else OrderSide.SELL,
            quantity=parent_order.quantity,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.IOC,
        )

        logger.info(
            f"Generated market order for {parent_order.symbol} (size: {participation_rate:.2%} ADV)"
        )
        return [child_order]

    def should_update_child_orders(
        self,
        parent_order: OrderSpecification,
        child_orders: List[ChildOrder],
        market_data: MarketData,
    ) -> Tuple[bool, List[ChildOrder]]:
        """Market orders execute immediately - no updates."""
        return False, child_orders


class ExecutionEngine:
    """
    Main execution engine coordinating execution algorithms.

    From Narang Chapter 7: The execution engine is responsible for:
    1. Selecting appropriate execution algorithm
    2. Generating and managing child orders
    3. Monitoring execution quality
    4. Handling exceptions and market conditions
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cost_model: Optional[TransactionCostModel] = None

        # Execution algorithms
        self.algorithms: Dict[ExecutionAlgorithm, ExecutionAlgoBase] = {
            ExecutionAlgorithm.VWAP: VWAPExecution(config.get("vwap_config", {})),
            ExecutionAlgorithm.TWAP: TWAPExecution(config.get("twap_config", {})),
            ExecutionAlgorithm.POV: POVExecution(config.get("pov_config", {})),
            ExecutionAlgorithm.MARKET: MarketExecution(config.get("market_config", {})),
        }

        # Execution history
        self.execution_reports: List[ExecutionReport] = []

    def set_cost_model(self, cost_model: TransactionCostModel) -> None:
        """Set transaction cost model for algorithm selection."""
        self.cost_model = cost_model

    def select_execution_algorithm(
        self, order: OrderSpecification, market_data: MarketData
    ) -> ExecutionAlgorithm:  # Returns the enum, not the ABC
        """
        Select the best execution algorithm for an order.

        From Narang: Algorithm choice depends on order size, urgency, and market conditions.
        """
        # If algorithm is explicitly specified, use it
        if order.execution_algorithm != ExecutionAlgorithm.IMPLEMENTATION_SHORTFALL:
            return order.execution_algorithm

        # Calculate participation rate
        participation_rate = float(order.quantity) / float(market_data.average_daily_volume)

        # Decision tree based on Narang's guidelines
        if participation_rate < 0.01:
            # Very small orders: market is fine
            if order.urgency > 0.7:
                return ExecutionAlgorithm.MARKET
            else:
                return ExecutionAlgorithm.LIMIT

        elif participation_rate < 0.05:
            # Small to medium orders
            if order.urgency > 0.8:
                return ExecutionAlgorithm.POV
            else:
                return ExecutionAlgorithm.TWAP

        elif participation_rate < 0.10:
            # Medium orders
            if order.urgency > 0.7:
                return ExecutionAlgorithm.POV
            else:
                return ExecutionAlgorithm.VWAP

        else:
            # Large orders: always use VWAP or POV
            if order.urgency > 0.8:
                return ExecutionAlgorithm.POV
            else:
                return ExecutionAlgorithm.VWAP

    def execute_order(
        self,
        order: OrderSpecification,
        market_data: MarketData,
        start_time: datetime,
        end_time: Optional[datetime] = None,
    ) -> Tuple[ExecutionReport, List[ChildOrder]]:
        """
        Execute an order using the appropriate algorithm.

        Args:
            order: Order to execute
            market_data: Current market data
            start_time: Execution start time
            end_time: Execution end time (defaults to end of trading day)

        Returns:
            Tuple of (execution_report, child_orders)
        """
        if end_time is None:
            end_time = start_time.replace(hour=16, minute=0)  # End of trading day

        # Select algorithm
        algorithm_type = self.select_execution_algorithm(order, market_data)
        algorithm = self.algorithms.get(algorithm_type)

        if not algorithm:
            logger.error(f"Algorithm {algorithm_type} not found")
            algorithm = self.algorithms[ExecutionAlgorithm.MARKET]

        # Generate child orders
        child_orders = algorithm.generate_child_orders(order, market_data, start_time, end_time)

        # In a real implementation, we would:
        # 1. Submit child orders to the exchange/broker
        # 2. Monitor fills
        # 3. Update based on market conditions
        # 4. Generate execution report

        # For now, generate a mock execution report
        execution_report = self._generate_mock_execution_report(order, market_data, child_orders)

        self.execution_reports.append(execution_report)

        return execution_report, child_orders

    def _generate_mock_execution_report(
        self, order: OrderSpecification, market_data: MarketData, child_orders: List[ChildOrder]
    ) -> ExecutionReport:
        """Generate a mock execution report for testing."""
        total_quantity = sum(co.quantity for co in child_orders)

        # Simulate execution price (near mid price with some slippage)
        slippage_bps = 5.0  # Assume 5 bps slippage
        mid_price = float(market_data.mid_price)

        if order.side == "buy":
            avg_price = Decimal(str(mid_price * (1 + slippage_bps / 10000)))
        else:
            avg_price = Decimal(str(mid_price * (1 - slippage_bps / 10000)))

        return ExecutionReport(
            order_id=f"report_{order.symbol}",
            symbol=order.symbol,
            side=OrderSide.BUY if order.side == "buy" else OrderSide.SELL,
            target_quantity=order.quantity,
            filled_quantity=total_quantity,
            average_price=avg_price,
            benchmark_price=market_data.mid_price,
            implementation_shortfall_bps=slippage_bps,
            market_impact_bps=slippage_bps * 0.7,
            timing_cost_bps=slippage_bps * 0.3,
            total_cost_bps=slippage_bps,
            execution_duration_seconds=300.0,  # 5 minutes
            fill_rate=(
                1.0 if total_quantity >= order.quantity else float(total_quantity / order.quantity)
            ),
            slippage_bps=slippage_bps,
        )

    def analyze_execution_quality(self, execution_report: ExecutionReport) -> Dict[str, Any]:
        """
        Analyze execution quality and generate recommendations.

        From Narang: Continuous monitoring of execution quality is essential.
        """
        analysis = {
            "is_good": True,
            "issues": [],
            "recommendations": [],
        }

        # Check implementation shortfall
        if execution_report.implementation_shortfall_bps > 20:
            analysis["is_good"] = False
            analysis["issues"].append(
                f"High implementation shortfall: {execution_report.implementation_shortfall_bps:.1f} bps"
            )
            analysis["recommendations"].append(
                "Consider using a more sophisticated execution algorithm (VWAP/POV)"
            )

        # Check market impact
        if execution_report.market_impact_bps > 15:
            analysis["is_good"] = False
            analysis["issues"].append(
                f"High market impact: {execution_report.market_impact_bps:.1f} bps"
            )
            analysis["recommendations"].append(
                "Reduce order size or extend execution time to reduce impact"
            )

        # Check fill rate
        if execution_report.fill_rate < 0.95:
            analysis["is_good"] = False
            analysis["issues"].append(f"Low fill rate: {execution_report.fill_rate:.1%}")
            analysis["recommendations"].append(
                "Review limit price placement or use market orders for small remaining quantities"
            )

        # Check execution duration
        if execution_report.execution_duration_seconds > 3600:  # > 1 hour
            analysis["issues"].append(
                f"Long execution duration: {execution_report.execution_duration_seconds / 60:.0f} minutes"
            )

        return analysis


def get_execution_engine(config: Dict[str, Any]) -> ExecutionEngine:
    """
    Factory function to create execution engine.

    Args:
        config: Configuration dictionary

    Returns:
        ExecutionEngine instance
    """
    return ExecutionEngine(config)


__all__ = [
    "OrderStatus",
    "OrderType",
    "TimeInForce",
    "OrderSide",
    "ChildOrder",
    "ExecutionReport",
    "IntradayVolumeProfile",
    "ExecutionAlgoBase",
    "VWAPExecution",
    "TWAPExecution",
    "POVExecution",
    "MarketExecution",
    "ExecutionEngine",
    "get_execution_engine",
]
