"""
T2.1.2 - Order Splitting Optimizer

Implements intelligent order splitting algorithms:
- VWAP (Volume-Weighted Average Price)
- TWAP (Time-Weighted Average Price)
- POI (Percentage of Involvement)
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional

from .models import ExecutionPlan, OrderTranche, TimeWindow

logger = logging.getLogger(__name__)


class OrderSplittingOptimizer:
    """
    Splits large orders into optimal tranches using various strategies.

    VWAP: Executes proportional to historical volume (best avg price)
    TWAP: Executes evenly over time (simple & effective)
    POI: Executes as % of real-time volume (most sophisticated)
    """

    # Default intraday volume profile (% of daily volume by hour)
    # Based on typical US market patterns
    TYPICAL_VOLUME_PROFILE = {
        "09:30-10:00": Decimal("0.15"),  # High volatility opening
        "10:00-11:00": Decimal("0.12"),  # Post-open calm
        "11:00-12:00": Decimal("0.08"),  # Pre-lunch
        "12:00-13:00": Decimal("0.05"),  # Lunch low volume
        "13:00-14:00": Decimal("0.10"),  # Post-lunch
        "14:00-15:00": Decimal("0.12"),  # Mid-afternoon
        "15:00-16:00": Decimal("0.20"),  # End of day rally
        "16:00-": Decimal("0.18"),  # After-hours
    }

    def __init__(self):
        """Initialize optimizer."""
        logger.info("OrderSplittingOptimizer initialized")

    async def optimize_execution(
        self,
        symbol: str,
        total_size: Decimal,
        strategy: str = "vwap",
        max_exec_time: int = 300_000,  # 5 minutes default
        constraints: Optional[Dict[str, Decimal]] = None,
    ) -> ExecutionPlan:
        """
        Create optimal execution plan using specified strategy.

        Args:
            symbol: Trading symbol
            total_size: Total order size in EUR
            strategy: Splitting strategy (vwap | twap | poi | intraday_phased)
            max_exec_time: Maximum execution time in ms
            constraints: Dict with max_per_tranche, max_spread, etc

        Returns:
            ExecutionPlan with list of tranches

        Example:
            >>> optimizer = OrderSplittingOptimizer()
            >>> plan = await optimizer.optimize_execution(
            ...     symbol="AAPL",
            ...     total_size=Decimal("50000"),
            ...     strategy="vwap",
            ...     max_exec_time=300_000,
            ... )
        """

        constraints = constraints or {}

        if strategy == "vwap":
            return self._vwap_split(symbol, total_size, max_exec_time, constraints)
        elif strategy == "twap":
            return self._twap_split(symbol, total_size, max_exec_time, constraints)
        elif strategy == "poi":
            return self._poi_split(symbol, total_size, max_exec_time, constraints)
        elif strategy == "intraday_phased":
            return self._intraday_phased_split(symbol, total_size, max_exec_time, constraints)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _vwap_split(
        self,
        symbol: str,
        total_size: Decimal,
        max_exec_time: int,
        constraints: Dict[str, Decimal],
    ) -> ExecutionPlan:
        """
        VWAP Split: Execute proportional to historical volume.

        Ensures best average fill price by trading when volume is high.
        """

        logger.info(f"Creating VWAP split for {symbol}: €{total_size:,.0f}")

        tranches = []
        remaining = total_size
        current_time = datetime.now()

        # Distribute execution over time proportional to volume
        for time_slot, vol_pct in self.TYPICAL_VOLUME_PROFILE.items():
            if remaining <= Decimal("0"):
                break

            # Get max per tranche from constraints or use default (20% per tranche)
            max_per_tranche = constraints.get("max_per_tranche", total_size * Decimal("0.2"))

            tranche_size = min(remaining, total_size * vol_pct, max_per_tranche)

            tranches.append(
                OrderTranche(
                    symbol=symbol,
                    size=tranche_size,
                    execution_time=current_time,
                    execution_window=TimeWindow(
                        start=time_slot.split("-")[0],
                        end=time_slot.split("-")[1] if "-" in time_slot else "16:30",
                        name=f"vwap_slot_{len(tranches)}",
                    ),
                )
            )
            remaining -= tranche_size
            current_time += timedelta(hours=1)

        return ExecutionPlan(
            symbol=symbol,
            total_size=total_size,
            tranches=tranches,
            strategy="vwap",
            max_execution_time_ms=max_exec_time,
            constraints=constraints,
        )

    def _twap_split(
        self,
        symbol: str,
        total_size: Decimal,
        max_exec_time: int,
        constraints: Dict[str, Decimal],
    ) -> ExecutionPlan:
        """
        TWAP Split: Execute evenly over time.

        Simple strategy that minimizes timing risk by spreading execution.
        """

        logger.info(f"Creating TWAP split for {symbol}: €{total_size:,.0f}")

        # Calculate number of tranches (one every 5 minutes)
        num_tranches = max(1, max_exec_time // 300_000)  # 300s = 5 min
        tranche_size = total_size / Decimal(num_tranches)

        tranches = []
        current_time = datetime.now()

        for i in range(int(num_tranches)):
            tranches.append(
                OrderTranche(
                    symbol=symbol,
                    size=tranche_size,
                    execution_time=current_time + timedelta(minutes=i * 5),
                )
            )

        return ExecutionPlan(
            symbol=symbol,
            total_size=total_size,
            tranches=tranches,
            strategy="twap",
            max_execution_time_ms=max_exec_time,
            constraints=constraints,
        )

    def _poi_split(
        self,
        symbol: str,
        total_size: Decimal,
        max_exec_time: int,
        constraints: Dict[str, Decimal],
    ) -> ExecutionPlan:
        """
        POI Split: Execute as % of real-time volume (dynamic).

        Most sophisticated approach: adapts to market conditions in real-time.
        Never exceeds X% of any single tick's volume.
        """

        logger.info(f"Creating POI split for {symbol}: €{total_size:,.0f}")

        # Max involvement % (default 20% of any tick's volume)
        max_involvement_pct = constraints.get("max_involvement_pct", Decimal("0.20"))

        return ExecutionPlan(
            symbol=symbol,
            total_size=total_size,
            tranches=[],  # Tranches filled dynamically during execution
            strategy="poi",
            max_execution_time_ms=max_exec_time,
            constraints={"max_involvement_pct": max_involvement_pct, **constraints},
        )

    def _intraday_phased_split(
        self,
        symbol: str,
        total_size: Decimal,
        max_exec_time: int,
        constraints: Dict[str, Decimal],
    ) -> ExecutionPlan:
        """
        Intraday Phased: Execute in good windows, avoid volatility peaks.

        Divides position across 3-5 time windows, increasing size in later windows.
        Avoids: opening (9:30-10:00), lunch (11:30-13:00), closing (15:00-16:00)
        """

        logger.info(f"Creating intraday_phased split for {symbol}: €{total_size:,.0f}")

        good_windows = [
            TimeWindow(start="10:30", end="11:15", name="post_open"),
            TimeWindow(start="13:00", end="14:15", name="post_lunch"),
            TimeWindow(start="14:30", end="15:00", name="pre_close"),
        ]

        # Weight later windows more heavily (better price discovery)
        weights = [Decimal("0.25"), Decimal("0.35"), Decimal("0.40")]

        tranches = []
        remaining = total_size
        current_time = datetime.now()

        for i, (window, weight) in enumerate(zip(good_windows, weights)):
            if remaining <= Decimal("0"):
                break

            if i == len(good_windows) - 1:
                # Last tranche gets remaining
                size = remaining
            else:
                size = min(remaining, total_size * weight)

            # Parse window times
            start_hour = int(window.start.split(":")[0])
            execution_time = current_time.replace(hour=start_hour, minute=0, second=0)

            tranches.append(
                OrderTranche(
                    symbol=symbol,
                    size=size,
                    execution_time=execution_time,
                    execution_window=window,
                )
            )
            remaining -= size

        return ExecutionPlan(
            symbol=symbol,
            total_size=total_size,
            tranches=tranches,
            strategy="intraday_phased",
            max_execution_time_ms=max_exec_time,
            constraints=constraints,
        )


# Global singleton
_order_splitting_optimizer: OrderSplittingOptimizer = None


def get_order_splitting_optimizer() -> OrderSplittingOptimizer:
    """Get or create global OrderSplittingOptimizer instance."""
    global _order_splitting_optimizer
    if _order_splitting_optimizer is None:

    return _order_splitting_optimizer
