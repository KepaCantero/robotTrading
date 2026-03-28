"""
Shadow Mode - CRITICAL Component for Safe Production Testing

This module implements Shadow Mode, which allows the bot to test strategies in
production with the REAL API without actually executing trades.

What is Shadow Mode?
--------------------
Shadow Mode is DIFFERENT from paper trading:
- Paper Trading: Simulated API, simulated execution
- Shadow Mode: REAL API, intercepts execution, records to WAL, simulates ACK

How it Works:
-------------
1. Bot thinks it's trading in production with real API
2. ShadowModeExecutor intercepts place_order calls
3. Records order to WAL (exactly like real execution)
4. Simulates ACK_RECEIVED response
5. Does NOT actually send order to broker
6. Logs with SHADOW prefix for audit trail

Why This is Critical:
---------------------
- Test strategies with real market conditions
- Validate API integration without risk
- Compare shadow vs real execution performance
- Safe ramp-up from testing to production
- Detect slippage and execution issues

Usage:
    shadow_executor = ShadowModeExecutor(
        broker_client=real_broker,
        wal_manager=wal_manager,
        sanity_layer=sanity_layer
    )

    # Execute order in shadow mode
    result = await shadow_executor.execute_order_shadow(
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("100"),
        price=Decimal("150.00")
    )

    # Compare shadow vs real performance
    comparison = await shadow_executor.compare_shadow_vs_real()

Integration Points:
-------------------
- IBroker interface (app/core/interfaces/broker_base.py)
- WAL persistence (app/sre/state_machine/wal_persistence.py)
- Boot Reconciler (app/sre/reconciliation/boot_reconciler.py)
- Data Sanity Layer (app/sre/data_integrity/sanity_layer.py)

Author: SRE Architecture
Date: 2025-01-25
"""

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import aiofiles
import numpy as np

from app.shared.config.centralized_config import get_config
from app.shared.interfaces.broker_base import Order
from app.sre.data_integrity.sanity_layer import DataSanityLayer, SanityCheckResult
from app.sre.state_machine.wal_persistence import OrderLog, OrderState, OrderStateMachine

logger = logging.getLogger(__name__)


class ShadowModeType(str, Enum):
    """Type of shadow mode execution."""

    DRY_RUN = "dry_run"  # Validate only, don't execute
    SHADOW = "shadow"  # Execute in shadow (record to WAL, simulate)
    PRODUCTION = "production"  # Real execution


@dataclass
class ShadowModeConfig:
    """Configuration for Shadow Mode execution."""

    enabled: bool = False
    shadow_type: ShadowModeType = ShadowModeType.DRY_RUN
    fill_simulation_model: str = "realistic"  # 'instant', 'realistic', 'slippage_model'
    slippage_bps: int = None  # Will be loaded from centralized config
    fill_delay_ms: int = None  # Will be loaded from centralized config
    partial_fill_probability: float = None  # Will be loaded from centralized config
    rejection_probability: float = None  # Will be loaded from centralized config
    enable_comparison: bool = True  # Track shadow vs real comparisons
    comparison_window_minutes: int = None  # Will be loaded from centralized config
    max_shadow_orders_per_day: int = None  # Will be loaded from centralized config
    audit_log_path: Optional[str] = None  # Path to audit log file

    def __post_init__(self):
        """Load defaults from centralized config and validate."""
        # Load from centralized config if not explicitly set
        config = get_config().shadow_mode

        if self.slippage_bps is None:
            self.slippage_bps = config.slippage_bps
        if self.fill_delay_ms is None:
            self.fill_delay_ms = config.fill_delay_ms
        if self.partial_fill_probability is None:
            self.partial_fill_probability = config.partial_fill_probability
        if self.rejection_probability is None:
            self.rejection_probability = config.rejection_probability
        if self.comparison_window_minutes is None:
            self.comparison_window_minutes = config.comparison_window_minutes
        if self.max_shadow_orders_per_day is None:
            self.max_shadow_orders_per_day = config.max_shadow_orders_per_day

        # Validate configuration
        if self.slippage_bps < 0:
            raise ValueError("slippage_bps must be non-negative")
        if self.fill_delay_ms < 0:
            raise ValueError("fill_delay_ms must be non-negative")
        if not 0 <= self.partial_fill_probability <= 1:
            raise ValueError("partial_fill_probability must be between 0 and 1")
        if not 0 <= self.rejection_probability <= 1:
            raise ValueError("rejection_probability must be between 0 and 1")


@dataclass
class ShadowExecutionResult:
    """Result of shadow mode execution."""

    order_id: str
    shadow_order_id: str
    symbol: str
    side: str
    quantity: Decimal
    requested_price: Optional[Decimal]
    simulated_fill_price: Optional[Decimal]
    simulated_fill_quantity: Decimal
    status: str
    execution_time_ms: int
    slippage_bps: Optional[int] = None
    was_rejected: bool = False
    rejection_reason: Optional[str] = None
    was_partial_fill: bool = False
    wal_recorded: bool = True
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "order_id": self.order_id,
            "shadow_order_id": self.shadow_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": str(self.quantity),
            "requested_price": str(self.requested_price) if self.requested_price else None,
            "simulated_fill_price": (
                str(self.simulated_fill_price) if self.simulated_fill_price else None
            ),
            "simulated_fill_quantity": str(self.simulated_fill_quantity),
            "status": self.status,
            "execution_time_ms": self.execution_time_ms,
            "slippage_bps": self.slippage_bps,
            "was_rejected": self.was_rejected,
            "rejection_reason": self.rejection_reason,
            "was_partial_fill": self.was_partial_fill,
            "wal_recorded": self.wal_recorded,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ShadowRealComparison:
    """Comparison between shadow and real execution."""

    symbol: str
    shadow_order_id: str
    real_order_id: Optional[str]
    shadow_price: Optional[Decimal]
    real_price: Optional[Decimal]
    shadow_fill_time_ms: int
    real_fill_time_ms: Optional[int]
    price_difference_bps: Optional[int]
    timing_difference_ms: Optional[int]
    shadow_status: str
    real_status: Optional[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ShadowModeExecutor:
    """
    Shadow Mode executor for safe production testing.

    CRITICAL: This component intercepts place_order calls and:
    1. Validates order using Data Sanity Layer
    2. Records to WAL (exactly like real execution)
    3. Simulates execution with realistic fills
    4. Tracks comparison metrics
    5. Maintains comprehensive audit trail

    Key Features:
    - Indistinguishable from real trading in code flow
    - WAL integration for crash recovery testing
    - Boot Reconciler compatibility
    - Shadow vs Real comparison
    - Comprehensive audit logging
    """

    def __init__(
        self,
        broker_client: object,
        wal_manager: OrderStateMachine,
        sanity_layer: Optional[DataSanityLayer] = None,
        config: Optional[ShadowModeConfig] = None,
    ):
        """
        Initialize Shadow Mode executor.

        Args:
            broker_client: Real broker API client (for validation)
            wal_manager: WAL persistence manager
            sanity_layer: Data sanity validation layer
            config: Shadow mode configuration
        """
        self.broker = broker_client
        self.wal = wal_manager
        self.sanity_layer = sanity_layer
        self.config = config or ShadowModeConfig()

        # Tracking
        self.shadow_results: List[ShadowExecutionResult] = []
        self.comparisons: List[ShadowRealComparison] = []
        self.daily_order_count: Dict[str, int] = defaultdict(int)

        # Locking
        self._lock = asyncio.Lock()

    async def is_shadow_mode_enabled(self) -> bool:
        """
        Check if shadow mode is enabled.

        Returns:
            bool: True if shadow mode is enabled
        """
        return self.config.enabled

    async def execute_order_shadow(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        order_type: str = "MARKET",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ShadowExecutionResult:
        """
        Execute order in shadow mode.

        CRITICAL FLOW:
        1. Validate order for shadow mode
        2. Check daily limits
        3. Validate price with Data Sanity Layer
        4. Write to WAL (BEFORE "execution")
        5. Simulate fill
        6. Update WAL with ACK_RECEIVED
        7. Track result
        8. Log with SHADOW prefix

        Args:
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Order price (for LIMIT orders)
            order_type: Order type ('MARKET' or 'LIMIT')
            metadata: Additional metadata

        Returns:
            ShadowExecutionResult with simulated execution details

        Raises:
            ValueError: If order validation fails
            RuntimeError: If shadow mode is disabled
        """
        if not await self.is_shadow_mode_enabled():
            raise RuntimeError("Shadow mode is not enabled")

        start_time = datetime.now(timezone.utc)
        order_id = str(uuid.uuid4())
        shadow_order_id = f"SHADOW_{order_id}"

        logger.info("=" * 80)
        logger.info(f"SHADOW MODE: Executing order {shadow_order_id}")
        logger.info(f"  Symbol: {symbol}")
        logger.info(f"  Side: {side}")
        logger.info(f"  Quantity: {quantity}")
        logger.info(f"  Type: {order_type}")
        logger.info(f"  Price: {price}")
        logger.info("=" * 80)

        try:
            # Step 1: Validate order for shadow mode
            await self.validate_order_for_shadow(symbol, side, quantity, price, order_type)

            # Step 2: Check daily limits
            today = datetime.now(timezone.utc).date()
            date_key = today.isoformat()
            self.daily_order_count[date_key] += 1

            if self.daily_order_count[date_key] > self.config.max_shadow_orders_per_day:
                raise RuntimeError(
                    f"Daily shadow order limit exceeded: "
                    f"{self.daily_order_count[date_key]} > {self.config.max_shadow_orders_per_day}"
                )

            # Step 3: Validate price with Data Sanity Layer
            if price and self.sanity_layer:
                validation = await self.sanity_layer.validate_price(symbol, price)

                if validation.result == SanityCheckResult.FAIL:
                    logger.error(
                        f"SHADOW MODE: Price validation failed for {symbol}: {validation.reason}"
                    )
                    raise ValueError(f"Price validation failed: {validation.reason}")

                if validation.result == SanityCheckResult.STALE:
                    logger.warning(
                        f"SHADOW MODE: Price data is stale for {symbol}: {validation.reason}"
                    )

            # Step 4: Write SUBMITTING to WAL (CRITICAL - before execution)
            log = OrderLog(
                order_id=shadow_order_id,
                state=OrderState.SUBMITTING,
                timestamp=datetime.now(timezone.utc),
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                metadata={
                    **(metadata or {}),
                    "shadow_mode": True,
                    "shadow_order_id": shadow_order_id,
                    "original_order_id": order_id,
                },
            )
            await self.wal.write_state(log)

            # Step 5: Simulate execution
            result = await self.simulate_fill(
                shadow_order_id=shadow_order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                order_type=order_type,
            )

            # Step 6: Write ACK_RECEIVED to WAL
            log.state = OrderState.ACK_RECEIVED
            log.timestamp = datetime.now(timezone.utc)
            log.broker_order_id = shadow_order_id
            await self.wal.write_state(log)

            # Step 7: Write final state to WAL
            if result.was_rejected:
                log.state = OrderState.REJECTED
                log.error = result.rejection_reason
            elif result.was_partial_fill:
                log.state = OrderState.PARTIAL_FILLED
            else:
                log.state = OrderState.FILLED

            log.timestamp = datetime.now(timezone.utc)
            await self.wal.write_state(log)

            # Step 8: Calculate execution time
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            result.execution_time_ms = execution_time_ms

            # Step 9: Track result
            async with self._lock:
                self.shadow_results.append(result)

            # Step 10: Log completion
            logger.info(
                f"SHADOW MODE: Order {shadow_order_id} completed - "
                f"Status: {result.status}, "
                f"Fill Price: {result.simulated_fill_price}, "
                f"Fill Qty: {result.simulated_fill_quantity}, "
                f"Time: {execution_time_ms}ms"
            )

            # Step 11: Write to audit log if configured
            if self.config.audit_log_path:
                await self._write_audit_log(result)

            return result

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"SHADOW MODE: Order {shadow_order_id} failed: {e}")

            # Write failure to WAL
            try:
                log = OrderLog(
                    order_id=shadow_order_id,
                    state=OrderState.FAILED,
                    timestamp=datetime.now(timezone.utc),
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=price,
                    error=str(e),
                    metadata={
                        **(metadata or {}),
                        "shadow_mode": True,
                        "shadow_order_id": shadow_order_id,
                    },
                )
                await self.wal.write_state(log)
            except (asyncio.TimeoutError, OSError) as wal_error:
                logger.critical(f"SHADOW MODE: Failed to write error to WAL: {wal_error}")

            raise

    async def validate_order_for_shadow(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Optional[Decimal],
        order_type: str,
    ) -> None:
        """
        Validate order for shadow mode execution.

        Args:
            symbol: Trading symbol
            side: Order side
            quantity: Order quantity
            price: Order price
            order_type: Order type

        Raises:
            ValueError: If validation fails
        """
        # Basic validation
        if not symbol:
            raise ValueError("Symbol is required")

        if side.upper() not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid side: {side}. Must be BUY or SELL")

        if quantity <= 0:
            raise ValueError(f"Quantity must be positive: {quantity}")

        if order_type == "LIMIT" and price is None:
            raise ValueError("LIMIT orders require a price")

        if price is not None and price <= 0:
            raise ValueError(f"Price must be positive: {price}")

        # Symbol format validation
        if not symbol.isalpha() or len(symbol) > 10:
            raise ValueError(f"Invalid symbol format: {symbol}")

        logger.debug(f"SHADOW MODE: Order validation passed - {symbol} {side} {quantity} @ {price}")

    async def simulate_fill(
        self,
        shadow_order_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Optional[Decimal],
        order_type: str,
    ) -> ShadowExecutionResult:
        """
        Simulate order fill with realistic behavior.

        Simulation Models:
        1. instant: Immediate fill at requested price
        2. realistic: Adds slippage, partial fills, rejections
        3. slippage_model: Advanced slippage modeling

        Args:
            shadow_order_id: Shadow order ID
            symbol: Trading symbol
            side: Order side
            quantity: Order quantity
            price: Order price
            order_type: Order type

        Returns:
            ShadowExecutionResult with simulated fill details
        """
        import random

        # Get centralized config for simulation parameters
        config = get_config().shadow_mode

        # Simulate fill delay with jitter from centralized config
        delay_ms = self.config.fill_delay_ms + random.randint(
            config.fill_delay_jitter_min_ms, config.fill_delay_jitter_max_ms
        )
        await asyncio.sleep(delay_ms / 1000.0)

        # Check for rejection
        if random.random() < self.config.rejection_probability:
            return ShadowExecutionResult(
                order_id=shadow_order_id,
                shadow_order_id=shadow_order_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                requested_price=price,
                simulated_fill_price=None,
                simulated_fill_quantity=Decimal("0"),
                status="REJECTED",
                execution_time_ms=delay_ms,
                was_rejected=True,
                rejection_reason="Simulated broker rejection",
                wal_recorded=True,
                metadata={"simulation_model": self.config.fill_simulation_model},
            )

        # Calculate fill price
        if order_type.upper() == "MARKET":
            # For market orders, get current price from broker
            try:
                ticker = await self.broker.get_live_ticker(symbol)
                base_price = ticker.last
            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                # Fallback price handling with proper error management
                if price is not None:
                    base_price = price
                    logger.warning(
                        f"SHADOW MODE: Broker ticker unavailable for {symbol}, "
                        f"using requested price {price}. Error: {e}"
                    )
                elif config.enable_fallback_price:
                    base_price = config.fallback_price
                    logger.warning(
                        f"SHADOW MODE: Broker ticker unavailable for {symbol}, "
                        f"using fallback price {config.fallback_price}. Error: {e}"
                    )
                else:
                    raise ValueError(
                        f"Cannot determine price for MARKET order {shadow_order_id} "
                        f"for {symbol}: broker ticker unavailable and no fallback price provided. "
                        f"Error: {e}"
                    )
        else:
            # For LIMIT orders, use the limit price
            base_price = price
            if base_price is None:
                raise ValueError("LIMIT orders require a price")

        # Apply slippage
        slippage_bps = self.config.slippage_bps
        slippage_multiplier = Decimal("1") + (Decimal(slippage_bps) / Decimal("10000"))

        if side == "BUY":
            fill_price = base_price * slippage_multiplier
        else:
            fill_price = base_price * (Decimal("2") - slippage_multiplier)

        # Check for partial fill using centralized config parameters
        fill_quantity = quantity
        is_partial = False

        if random.random() < self.config.partial_fill_probability:
            # Partial fill: use configured min/max percentages
            fill_pct = random.uniform(config.partial_fill_min_pct, config.partial_fill_max_pct)
            fill_quantity = quantity * Decimal(str(fill_pct)).quantize(Decimal("0.01"))
            is_partial = True

        # Create result
        if is_partial:
            status = "PARTIAL_FILLED"
        else:
            status = "FILLED"

        result = ShadowExecutionResult(
            order_id=shadow_order_id,
            shadow_order_id=shadow_order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            requested_price=price,
            simulated_fill_price=fill_price.quantize(Decimal("0.01")),
            simulated_fill_quantity=fill_quantity,
            status=status,
            execution_time_ms=delay_ms,
            slippage_bps=slippage_bps,
            was_rejected=False,
            was_partial_fill=is_partial,
            wal_recorded=True,
            metadata={
                "simulation_model": self.config.fill_simulation_model,
                "base_price": str(base_price),
                "slippage_multiplier": str(slippage_multiplier),
            },
        )

        logger.debug(
            f"SHADOW MODE: Simulated fill - Price: {fill_price}, "
            f"Qty: {fill_quantity}, Slippage: {slippage_bps}bps"
        )

        return result

    async def shadow_to_production_transition(
        self, validation_period_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Transition from shadow mode to production.

        CRITICAL: This is a DANGEROUS operation. Validates that shadow mode
        has been running successfully before enabling real execution.

        Validation Steps:
        1. Check shadow order success rate
        2. Validate WAL consistency
        3. Verify no critical errors in shadow results
        4. Compare shadow vs real (if available)
        5. Generate transition report

        Args:
            validation_period_minutes: Minutes of shadow results to validate

        Returns:
            Transition report with validation results
        """
        logger.critical("=" * 80)
        logger.critical("SHADOW TO PRODUCTION TRANSITION REQUESTED")
        logger.critical("THIS IS A CRITICAL OPERATION - VALIDATING...")
        logger.critical("=" * 80)

        report: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "validation_period_minutes": validation_period_minutes,
            "can_transition": False,
            "validations": [],
            "warnings": [],
            "errors": [],
        }

        # Get recent shadow results
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=validation_period_minutes)
        recent_results = [r for r in self.shadow_results if r.timestamp >= cutoff]

        if not recent_results:
            report["errors"].append("No shadow results found in validation period")
            logger.critical("TRANSITION BLOCKED: No shadow results to validate")
            return report

        # Validation 1: Success rate
        success_rate = np.mean([1 for r in recent_results if not r.was_rejected])
        report["validations"].append(
            {
                "name": "success_rate",
                "value": f"{success_rate:.2%}",
                "passed": success_rate >= 0.95,
                "threshold": ">= 95%",
            }
        )

        if success_rate < 0.95:
            report["errors"].append(f"Low success rate: {success_rate:.2%}")

        # Validation 2: WAL consistency
        try:
            pending_orders = await self.wal.get_pending_orders()
            shadow_pending = [o for o in pending_orders if o.metadata.get("shadow_mode")]

            if len(shadow_pending) > len(recent_results) * 0.1:
                report["errors"].append(
                    f"Too many pending shadow orders in WAL: {len(shadow_pending)}"
                )
            else:
                report["validations"].append(
                    {
                        "name": "wal_consistency",
                        "value": f"{len(shadow_pending)} pending",
                        "passed": True,
                    }
                )
        except (asyncio.TimeoutError, OSError) as e:
            report["errors"].append(f"WAL validation failed: {e}")

        # Validation 3: No critical errors
        critical_errors = [
            r for r in recent_results if r.was_rejected and r.rejection_reason == "CRITICAL"
        ]

        if critical_errors:
            report["errors"].append(f"Critical errors found: {len(critical_errors)}")

        # Validation 4: Shadow vs real comparison (if available)
        if self.comparisons:
            avg_price_diff_bps = np.mean([c.price_difference_bps or 0 for c in self.comparisons])

            if abs(avg_price_diff_bps) > 50:  # 50 bps threshold
                report["warnings"].append(
                    f"High shadow vs real price difference: {avg_price_diff_bps:.1f}bps"
                )

            report["validations"].append(
                {
                    "name": "shadow_real_comparison",
                    "value": f"{avg_price_diff_bps:.1f}bps",
                    "passed": abs(avg_price_diff_bps) <= 50,
                }
            )

        # Final decision
        all_passed = all(v.get("passed", False) for v in report["validations"])
        no_errors = len(report["errors"]) == 0

        report["can_transition"] = all_passed and no_errors

        if report["can_transition"]:
            logger.critical("TRANSITION VALIDATED: Shadow to production is SAFE")
        else:
            logger.critical("TRANSITION BLOCKED: Validation failed")

        logger.critical(f"Validation Results: {len(report['validations'])} checks")
        logger.critical(f"Warnings: {len(report['warnings'])}")
        logger.critical(f"Errors: {len(report['errors'])}")
        logger.critical("=" * 80)

        return report

    async def compare_shadow_vs_real(self, limit: int = 100) -> List[ShadowRealComparison]:
        """
        Compare shadow mode execution vs real execution.

        This is used to:
        1. Validate shadow mode accuracy
        2. Detect execution differences
        3. Measure slippage modeling accuracy
        4. Identify pricing discrepancies

        Args:
            limit: Maximum number of comparisons to return

        Returns:
            List of shadow vs real comparisons
        """
        if not self.config.enable_comparison:
            logger.warning("Shadow vs real comparison is disabled")
            return []

        logger.info("Comparing shadow vs real execution...")

        comparisons = []

        # Get recent shadow results
        recent_shadow = sorted(self.shadow_results, key=lambda r: r.timestamp, reverse=True)[:limit]

        for shadow_result in recent_shadow:
            # Try to find corresponding real order
            # This would need to be implemented based on your order matching logic
            # For now, create a comparison without real execution

            comparison = ShadowRealComparison(
                symbol=shadow_result.symbol,
                shadow_order_id=shadow_result.shadow_order_id,
                real_order_id=None,  # No real execution
                shadow_price=shadow_result.simulated_fill_price,
                real_price=None,  # No real execution
                shadow_fill_time_ms=shadow_result.execution_time_ms,
                real_fill_time_ms=None,  # No real execution
                price_difference_bps=None,
                timing_difference_ms=None,
                shadow_status=shadow_result.status,
                real_status=None,
            )

            comparisons.append(comparison)

        self.comparisons.extend(comparisons)

        logger.info(f"Generated {len(comparisons)} shadow vs real comparisons")

        return comparisons

    async def get_shadow_statistics(self, minutes: int = 60) -> Dict[str, Any]:
        """
        Get statistics about shadow mode execution.

        Args:
            minutes: Time window for statistics (default: 60 minutes)

        Returns:
            Dictionary with shadow mode statistics
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent = [r for r in self.shadow_results if r.timestamp >= cutoff]

        if not recent:
            return {
                "period_minutes": minutes,
                "total_orders": 0,
                "message": "No shadow orders in period",
            }

        total = len(recent)
        filled = sum(1 for r in recent if r.status == "FILLED")
        partial = sum(1 for r in recent if r.status == "PARTIAL_FILLED")
        rejected = sum(1 for r in recent if r.was_rejected)

        avg_slippage = sum(r.slippage_bps or 0 for r in recent) / total
        avg_time_ms = sum(r.execution_time_ms for r in recent) / total

        by_symbol = defaultdict(list)
        for r in recent:
            by_symbol[r.symbol].append(r)

        symbol_stats = {}
        for symbol, orders in by_symbol.items():
            symbol_stats[symbol] = {
                "count": len(orders),
                "fill_rate": np.mean([1 for o in orders if not o.was_rejected]),
                "avg_slippage_bps": np.mean([o.slippage_bps or 0 for o in orders]),
            }

        return {
            "period_minutes": minutes,
            "total_orders": total,
            "filled": filled,
            "partial_fills": partial,
            "rejected": rejected,
            "fill_rate": (filled + partial) / total,
            "rejection_rate": rejected / total,
            "avg_slippage_bps": avg_slippage,
            "avg_execution_time_ms": avg_time_ms,
            "by_symbol": symbol_stats,
        }

    async def _write_audit_log(self, result: ShadowExecutionResult) -> None:
        """
        Write shadow execution to audit log.

        Args:
            result: Shadow execution result
        """
        import json

        try:
            async with aiofiles.open(self.config.audit_log_path, mode="a") as f:
                log_entry = {
                    "type": "SHADOW_EXECUTION",
                    "timestamp": result.timestamp.isoformat(),
                    "data": result.to_dict(),
                }
                await f.write(json.dumps(log_entry) + "\n")
        except OSError as e:
            logger.error(f"Failed to write audit log: {e}")

    async def reset_daily_counters(self) -> None:
        """Reset daily order counters (called at midnight)."""
        self.daily_order_count.clear()
        logger.info("SHADOW MODE: Daily counters reset")


class ShadowModeAwareBroker:
    """
    Broker wrapper that integrates Shadow Mode with IBroker interface.

    This wraps a real broker and intercepts execute_order_with_wal calls
    when shadow mode is enabled.
    """

    def __init__(
        self,
        real_broker: object,
        shadow_executor: ShadowModeExecutor,
    ):
        """
        Initialize shadow-aware broker.

        Args:
            real_broker: Real broker implementation
            shadow_executor: Shadow mode executor
        """
        self.real_broker = real_broker
        self.shadow_executor = shadow_executor

    async def execute_order_with_wal(self, order: Order, dry_run: bool = False) -> Any:
        """
        Execute order with WAL, intercepting for shadow mode.

        Args:
            order: Order to execute
            dry_run: If True, only validate

        Returns:
            Order result (real or shadow)
        """
        # Check if shadow mode is enabled
        if await self.shadow_executor.is_shadow_mode_enabled():
            logger.info(f"SHADOW MODE: Intercepting order {order.order_id}")

            # Execute in shadow mode
            result = await self.shadow_executor.execute_order_shadow(
                symbol=order.symbol,
                side=order.side.value,
                quantity=order.quantity,
                price=order.price,
                order_type=order.type.value,
                metadata={"original_order_id": order.order_id},
            )

            # Return in format expected by calling code
            return {
                "order_id": result.shadow_order_id,
                "status": result.status,
                "filled_quantity": float(result.simulated_fill_quantity),
                "execution_price": (
                    float(result.simulated_fill_price) if result.simulated_fill_price else None
                ),
                "shadow_mode": True,
                "metadata": result.to_dict(),
            }

        # Real execution
        return await self.real_broker.execute_order_with_wal(order, dry_run)

    def __getattr__(self, name: str) -> Any:
        """Delegate all other calls to real broker."""
        return getattr(self.real_broker, name)


def detect_shadow_mode_from_env() -> ShadowModeConfig:
    """
    Detect shadow mode configuration from environment variables.

    Environment Variables:
    - SHADOW_MODE_ENABLED: "true" to enable
    - SHADOW_MODE_TYPE: "dry_run", "shadow", or "production"
    - SHADOW_SLIPPAGE_BPS: Slippage in basis points (default from centralized config)
    - SHADOW_FILL_DELAY_MS: Fill delay in milliseconds (default from centralized config)
    - SHADOW_PARTIAL_FILL_PROB: Partial fill probability (default from centralized config)
    - SHADOW_REJECTION_PROB: Rejection probability (default from centralized config)
    - SHADOW_MAX_ORDERS: Max shadow orders per day (default from centralized config)
    - SHADOW_COMPARISON_WINDOW: Comparison window in minutes (default from centralized config)
    - SHADOW_AUDIT_LOG: Path to audit log file

    Returns:
        ShadowModeConfig with environment-based settings
    """
    import os

    enabled = os.getenv("SHADOW_MODE_ENABLED", "false").lower() == "true"

    shadow_type_str = os.getenv("SHADOW_MODE_TYPE", "shadow")
    shadow_type = ShadowModeType(shadow_type_str)

    # Get centralized config defaults
    centralized_config = get_config().shadow_mode

    config = ShadowModeConfig(
        enabled=enabled,
        shadow_type=shadow_type,
        slippage_bps=int(os.getenv("SHADOW_SLIPPAGE_BPS", str(centralized_config.slippage_bps))),
        fill_delay_ms=int(os.getenv("SHADOW_FILL_DELAY_MS", str(centralized_config.fill_delay_ms))),
        partial_fill_probability=float(
            os.getenv("SHADOW_PARTIAL_FILL_PROB", str(centralized_config.partial_fill_probability))
        ),
        rejection_probability=float(
            os.getenv("SHADOW_REJECTION_PROB", str(centralized_config.rejection_probability))
        ),
        max_shadow_orders_per_day=int(
            os.getenv("SHADOW_MAX_ORDERS", str(centralized_config.max_shadow_orders_per_day))
        ),
        comparison_window_minutes=int(
            os.getenv("SHADOW_COMPARISON_WINDOW", str(centralized_config.comparison_window_minutes))
        ),
        audit_log_path=os.getenv("SHADOW_AUDIT_LOG"),
    )

    if enabled:
        logger.info(f"SHADOW MODE ENABLED: {shadow_type.value}")
        logger.info(f"  Slippage: {config.slippage_bps}bps")
        logger.info(f"  Fill delay: {config.fill_delay_ms}ms")
        logger.info(f"  Partial fill prob: {config.partial_fill_probability}")
        logger.info(f"  Rejection prob: {config.rejection_probability}")
        logger.info(f"  Max orders/day: {config.max_shadow_orders_per_day}")

    return config
