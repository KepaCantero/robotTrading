"""
T2.2 - Large Position Builder

Builds large positions (€50k+) intelligently using intraday tranches.

Strategy:
- Divide position into 3-5 tranches over 4-6 hours
- Avoid volatility peaks (opening, lunch, close)
- Increase size in later windows (better price discovery)
- Integrate with SmartOrderRouter for cost optimization
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from app.services.smart_order_routing.models import ExecutionPlan, OrderTranche, TimeWindow

logger = logging.getLogger(__name__)


class IntraDayExecutionScheduler:
    """
    Schedules optimal intraday execution windows.

    Avoids:
    - 9:30-10:00 (opening volatility spike)
    - 11:30-13:00 (lunch volatility)
    - 15:00-16:00 (closing volatility spike)

    Prefers:
    - 10:30-11:15 (post-opening calm)
    - 13:00-14:15 (post-lunch calm)
    - 14:30-15:00 (pre-close calm, good liquidity)
    - 16:00-16:30 (after-hours, if allowed)
    """

    # Market hours: US equity markets
    MARKET_OPEN = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
    MARKET_CLOSE = datetime.now().replace(hour=16, minute=0, second=0, microsecond=0)

    # Good execution windows (volatility calm zones)
    GOOD_EXECUTION_WINDOWS = [
        TimeWindow(start="10:30", end="11:15", name="post_open"),
        TimeWindow(start="13:00", end="14:15", name="post_lunch"),
        TimeWindow(start="14:30", end="15:00", name="pre_close"),
        TimeWindow(start="16:00", end="16:30", name="after_hours"),
    ]

    # Volatility peaks to avoid
    VOLATILITY_PEAKS = [
        ("09:30", "10:00"),  # Opening auction
        ("11:30", "13:00"),  # Lunch
        ("15:00", "16:00"),  # Closing auction
    ]

    def __init__(self):
        """Initialize scheduler."""
        logger.info("IntraDayExecutionScheduler initialized")

    def find_good_windows(
        self,
        num_windows: int = 3,
        max_total_hours: int = 6,
    ) -> List[TimeWindow]:
        """
        Find optimal execution windows within market hours.

        Args:
            num_windows: Number of execution windows (3-5)
            max_total_hours: Maximum hours for entire execution

        Returns:
            List of TimeWindow objects sorted chronologically
        """

        if num_windows < 1 or num_windows > 5:
            raise ValueError("num_windows must be between 1 and 5")

        # Return best windows for requested count
        available = self.GOOD_EXECUTION_WINDOWS[:num_windows]

        if len(available) < num_windows:
            logger.warning(f"Only {len(available)} good windows available, requested {num_windows}")

        logger.info(f"Selected {len(available)} good execution windows")
        return available

    def time_window_to_datetime(self, window: TimeWindow) -> datetime:
        """
        Convert TimeWindow (HH:MM format) to datetime.

        Args:
            window: TimeWindow with start time

        Returns:
            datetime object for today at the specified time
        """

        parts = window.start.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        return datetime.now().replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )

    def is_in_volatile_period(self, time_str: str) -> bool:
        """
        Check if time is in a volatile period to avoid.

        Args:
            time_str: Time in HH:MM format

        Returns:
            True if in volatile period
        """

        return any(start <= time_str < end for start, end in self.VOLATILITY_PEAKS)


class LargePositionBuilder:
    """
    Intelligently builds large positions (€50k+) over intraday tranches.

    Divides large orders into 3-5 tranches across optimal execution windows
    to minimize market impact and avoid volatility peaks.

    Key features:
    - Avoids opening, lunch, and closing volatility
    - Increases size in later windows (better price discovery)
    - Integrates with SmartOrderRouter for cost optimization
    - Provides execution plan with timing and size allocation
    """

    # Minimum position size for large position building
    MIN_POSITION_SIZE = Decimal("25000")

    # Maximum position size (beyond this, special handling needed)
    MAX_RECOMMENDED_SIZE = Decimal("500000")

    # Default number of tranches
    DEFAULT_NUM_TRANCHES = 4

    # Size allocation weights (increase for later windows)
    # e.g., [0.20, 0.24, 0.26, 0.30] for 4 tranches = 100%
    TRANCHE_WEIGHTS_BY_COUNT = {
        1: [Decimal("1.00")],
        2: [Decimal("0.40"), Decimal("0.60")],
        3: [Decimal("0.25"), Decimal("0.35"), Decimal("0.40")],
        4: [Decimal("0.20"), Decimal("0.24"), Decimal("0.26"), Decimal("0.30")],
        5: [Decimal("0.15"), Decimal("0.20"), Decimal("0.22"), Decimal("0.23"), Decimal("0.20")],
    }

    def __init__(self):
        """Initialize position builder."""
        self.scheduler = IntraDayExecutionScheduler()
        logger.info("LargePositionBuilder initialized")

    async def build_position(
        self,
        symbol: str,
        target_size: Decimal,
        target_avg_price: Optional[Decimal] = None,
        max_execution_hours: int = 6,
        num_tranches: Optional[int] = None,
    ) -> ExecutionPlan:
        """
        Create phased execution plan for large position.

        Divides position into optimal tranches across intraday windows.

        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            target_size: Total position size to build (€)
            target_avg_price: Target average execution price (optional)
            max_execution_hours: Maximum hours for execution (4-6 typical)
            num_tranches: Number of tranches (3-5, default 4)

        Returns:
            ExecutionPlan with tranches, timing, and cost estimates

        Raises:
            ValueError: If position size invalid or parameters inconsistent

        Example:
            >>> builder = LargePositionBuilder()
            >>> plan = await builder.build_position(
            ...     symbol="AAPL",
            ...     target_size=Decimal("50000"),
            ...     max_execution_hours=6,
            ...     num_tranches=4,
            ... )
            >>> len(plan.tranches)
            4
        """

        target_size = Decimal(str(target_size))

        # Validate position size
        if target_size < self.MIN_POSITION_SIZE:
            raise ValueError(
                f"Position size €{target_size:,.0f} below minimum "
                f"€{self.MIN_POSITION_SIZE:,.0f} for large position building"
            )

        if target_size > self.MAX_RECOMMENDED_SIZE:
            logger.warning(
                f"Position size €{target_size:,.0f} exceeds recommended maximum "
                f"€{self.MAX_RECOMMENDED_SIZE:,.0f}. Consider splitting further."
            )

        # Determine number of tranches
        if num_tranches is None:
            num_tranches = self.DEFAULT_NUM_TRANCHES
        elif num_tranches < 1 or num_tranches > 5:
            raise ValueError("num_tranches must be between 1 and 5")

        logger.info(
            f"Building position: {symbol} €{target_size:,.0f} "
            f"over {num_tranches} tranches in {max_execution_hours}h"
        )

        # =====================================================================
        # STEP 1: Determine execution windows
        # =====================================================================

        windows = self.scheduler.find_good_windows(
            num_windows=num_tranches,
            max_total_hours=max_execution_hours,
        )

        if len(windows) < num_tranches:
            raise ValueError(
                f"Only {len(windows)} good windows available, " f"requested {num_tranches} tranches"
            )

        logger.info(f"Selected {len(windows)} execution windows for {symbol}")

        # =====================================================================
        # STEP 2: Allocate size to tranches
        # =====================================================================

        tranches = self._allocate_size_to_windows(
            symbol=symbol,
            total_size=target_size,
            windows=windows,
            target_price=target_avg_price,
        )

        # =====================================================================
        # STEP 3: Create execution plan
        # =====================================================================

        execution_plan = ExecutionPlan(
            symbol=symbol,
            total_size=target_size,
            tranches=tranches,
            strategy="intraday_phased",
            max_execution_time_ms=max_execution_hours * 3_600_000,
            estimated_avg_price=target_avg_price,
            constraints={
                "num_windows": Decimal(num_tranches),
                "avoid_volatility_peaks": Decimal("1"),  # Always avoid peaks
                "increase_size_over_time": Decimal("1"),  # Increase in later windows
            },
        )

        logger.info(
            f"Execution plan created: {len(tranches)} tranches, " f"strategy: intraday_phased"
        )

        return execution_plan

    def _allocate_size_to_windows(
        self,
        symbol: str,
        total_size: Decimal,
        windows: List[TimeWindow],
        target_price: Optional[Decimal] = None,
    ) -> List[OrderTranche]:
        """
        Allocate position size across execution windows.

        Uses pre-defined weights that increase for later windows
        (better price discovery as market opens up).

        Args:
            symbol: Trading symbol
            total_size: Total position size
            windows: Execution windows
            target_price: Target execution price for all tranches

        Returns:
            List of OrderTranche objects with sizes and timings

        Example allocation for €50k across 4 windows:
        - Window 1 (10:30): €10k (20%)
        - Window 2 (13:00): €12k (24%)
        - Window 3 (14:30): €13k (26%)
        - Window 4 (16:00): €15k (30%)
        """

        num_windows = len(windows)

        if num_windows not in self.TRANCHE_WEIGHTS_BY_COUNT:
            raise ValueError(f"Unsupported number of tranches: {num_windows}. " f"Must be 1-5.")

        weights = self.TRANCHE_WEIGHTS_BY_COUNT[num_windows]

        tranches = []
        remaining = total_size

        for i, (window, weight) in enumerate(zip(windows, weights)):
            # For last tranche, use remaining amount to avoid rounding issues
            if i == len(windows) - 1:
                size = remaining
            else:
                size = (total_size * weight).quantize(Decimal("0.01"))

            # Parse window start time to execution datetime
            window_datetime = self.scheduler.time_window_to_datetime(window)

            # Create tranche
            tranche = OrderTranche(
                symbol=symbol,
                size=size,
                execution_time=window_datetime,
                execution_window=window,
                target_price=target_price,
                status="pending",
            )

            tranches.append(tranche)
            remaining -= size

            logger.info(
                f"{symbol}: Tranche {i+1}/{num_windows} → "
                f"€{size:,.2f} at {window.name} ({window.start})"
            )

        # Validate sum
        total_allocated = sum(t.size for t in tranches)
        if total_allocated != total_size:
            logger.warning(
                f"Rounding: allocated €{total_allocated:,.2f} vs "
                f"target €{total_size:,.2f} (diff: €{(total_size - total_allocated):,.2f})"
            )

        return tranches

    def calculate_position_impact(
        self,
        symbol: str,
        position_size: Decimal,
        daily_volume: Decimal,
        num_tranches: int = 4,
    ) -> dict:
        """
        Estimate market impact reduction from splitting into tranches.

        Compares:
        - Executing entire position at once
        - Splitting into N tranches over day

        Args:
            symbol: Trading symbol
            position_size: Total position size
            daily_volume: Expected daily volume
            num_tranches: Number of tranches to split into

        Returns:
            Dict with impact analysis and comparison
        """

        position_size = Decimal(str(position_size))
        daily_volume = Decimal(str(daily_volume))

        # Single execution participation rate
        single_exec_participation = position_size / daily_volume

        # Per-tranche participation rate
        tranche_size = position_size / Decimal(num_tranches)
        tranche_participation = tranche_size / daily_volume

        # Market impact scales with sqrt(participation_rate)
        #
        # SINGLE EXECUTION:
        #   Impact = k × sqrt(participation_rate) = k × sqrt(Q/V)
        #
        # N TRANCHES (spreading over time reduces effective volume pressure):
        #   Each tranche has participation = (Q/N) / V
        #   But temporal spreading means we don't see cumulative impact
        #   Effective impact = k × sqrt(Q / (N × V)) = k × sqrt(participation_rate / N)
        #
        # IMPACT REDUCTION RATIO:
        #   Reduction factor = sqrt(Q/V) / sqrt(Q/(N×V)) = sqrt(N)
        #   So splitting into N tranches reduces impact by sqrt(N) factor

        single_exec_impact = single_exec_participation.sqrt()

        # Tranches reduce impact by sqrt(N) factor due to temporal spreading
        # Effective impact with tranches = single_impact / sqrt(N)
        tranche_impacts_combined = single_exec_impact / Decimal(num_tranches).sqrt()

        # Impact reduction
        impact_reduction = single_exec_impact - tranche_impacts_combined
        impact_reduction_pct = (
            (impact_reduction / single_exec_impact) * Decimal("100")
            if single_exec_impact > 0
            else Decimal("0")
        )

        logger.info(
            f"Position impact analysis for {symbol}: "
            f"Single execution impact {single_exec_impact:.4f} vs "
            f"{num_tranches} tranches {tranche_impacts_combined:.4f} "
            f"({impact_reduction_pct:.1f}% reduction)"
        )

        return {
            "symbol": symbol,
            "position_size": position_size,
            "daily_volume": daily_volume,
            "single_execution_participation": single_exec_participation,
            "single_execution_impact": single_exec_impact,
            "num_tranches": num_tranches,
            "tranche_size": tranche_size,
            "tranche_participation": tranche_participation,
            "tranche_impacts_combined": tranche_impacts_combined,
            "impact_reduction": impact_reduction,
            "impact_reduction_pct": impact_reduction_pct,
            "recommendation": (
                "Split into tranches"
                if impact_reduction_pct > Decimal("20")
                else "Single execution acceptable"
            ),
        }

    def estimate_build_duration(
        self,
        symbol: str,
        num_tranches: int,
    ) -> Tuple[timedelta, str]:
        """
        Estimate total duration for building position.

        Args:
            symbol: Trading symbol (not used, for API consistency)
            num_tranches: Number of tranches

        Returns:
            Tuple of (timedelta, human_readable_string)
        """

        # Windows are typically spaced 2-3 hours apart
        # Total time: from first window start to last window end
        # More tranches = more time needed (minimum 2 hours between tranches)

        if num_tranches == 1:
            hours = 1  # Single execution window
        elif num_tranches == 2:
            hours = 3  # ~2-3 hours between windows
        elif num_tranches == 3:
            hours = 5  # Spread across more windows
        elif num_tranches == 4:
            hours = 6  # Full market day usage
        else:  # 5 tranches
            hours = 7  # Extended into after-hours

        duration = timedelta(hours=hours)
        readable = f"{hours} hours"

        logger.info(f"Estimated build duration for {num_tranches} tranches: {readable}")

        return duration, readable


# Global singleton
_large_position_builder: LargePositionBuilder = None


def get_large_position_builder() -> LargePositionBuilder:
    """Get or create global LargePositionBuilder instance."""
    global _large_position_builder
    if _large_position_builder is None:
        _large_position_builder = LargePositionBuilder()

    return _large_position_builder
