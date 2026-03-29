"""
T2.1.4 - Execution Cost Monitor

Real-time monitoring of execution costs against budgeted limits.

Tracks:
- Planned vs actual costs
- Cost overrun alerts
- Execution progress
- Performance metrics
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import numpy as np

from .models import ExecutionMonitoring

logger = logging.getLogger(__name__)


class ExecutionCostMonitor:
    """
    Monitors execution costs in real-time against budget.

    Provides:
    - Cost tracking per tranche
    - Cumulative cost monitoring
    - Budget overrun alerts
    - Performance metrics (cost vs plan)
    - Execution progress tracking
    """

    # Alert thresholds
    COST_OVERRUN_ALERT_THRESHOLD = Decimal("0.05")  # 5% overrun triggers warning
    COST_OVERRUN_CRITICAL_THRESHOLD = Decimal("0.10")  # 10% overrun triggers critical

    def __init__(self):
        """Initialize cost monitor."""
        self.executions: dict[str, ExecutionMonitoring] = {}
        self.tranche_costs: dict[str, list[dict]] = {}
        logger.info("ExecutionCostMonitor initialized")

    def start_monitoring(
        self,
        execution_id: str,
        planned_cost_budget: Decimal,
        total_tranches: int,
    ) -> ExecutionMonitoring:
        """
        Start monitoring a new execution.

        Args:
            execution_id: Unique execution identifier
            planned_cost_budget: Maximum budgeted cost in €
            total_tranches: Total number of tranches in execution

        Returns:
            ExecutionMonitoring object initialized and ready for tracking
        """

        monitoring = ExecutionMonitoring(
            execution_id=execution_id,
            planned_cost=planned_cost_budget,
            actual_costs=Decimal("0"),
            tranches_completed=0,
            tranches_total=total_tranches,
            started_at=datetime.now(),
            completed_at=None,
        )

        self.executions[execution_id] = monitoring
        self.tranche_costs[execution_id] = []

        logger.info(
            f"Started monitoring execution {execution_id}: "
            f"Budget €{planned_cost_budget:,.2f}, {total_tranches} tranches"
        )

        return monitoring

    def record_tranche_execution(
        self,
        execution_id: str,
        tranche_id: str,
        symbol: str,
        executed_size: Decimal,
        target_price: Decimal,
        executed_price: Decimal,
        commission_cost: Optional[Decimal] = None,
    ) -> tuple[Decimal, dict]:
        """
        Record execution of a single tranche.

        Calculates cost (slippage + commission) and updates monitoring.

        Args:
            execution_id: Parent execution identifier
            tranche_id: Tranche identifier
            symbol: Trading symbol
            executed_size: Actual size executed (€)
            target_price: Target/planned execution price
            executed_price: Actual execution price
            commission_cost: Commission paid for this tranche (€)

        Returns:
            Tuple of (total_tranche_cost, tranche_cost_breakdown)

        Raises:
            ValueError: If execution not found
        """
        if commission_cost is None:
            commission_cost = Decimal("0")

        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found in monitor")

        monitoring = self.executions[execution_id]

        # Calculate slippage cost (price difference * size)
        slippage_cost = abs(executed_price - target_price) * executed_size

        # Total cost for this tranche
        total_cost = slippage_cost + commission_cost

        # Slippage in basis points (for reporting)
        if executed_size > 0:
            slippage_bps = (slippage_cost / executed_size) * Decimal("10000")
        else:
            slippage_bps = Decimal("0")

        # Update cumulative costs
        monitoring.actual_costs += total_cost
        monitoring.tranches_completed += 1

        # Record tranche cost breakdown
        cost_record = {
            "tranche_id": tranche_id,
            "symbol": symbol,
            "executed_size": executed_size,
            "target_price": target_price,
            "executed_price": executed_price,
            "slippage_cost": slippage_cost,
            "slippage_bps": slippage_bps,
            "commission_cost": commission_cost,
            "total_cost": total_cost,
            "recorded_at": datetime.now(),
        }

        self.tranche_costs[execution_id].append(cost_record)

        logger.info(
            f"Execution {execution_id}: Tranche {tranche_id} -> "
            f"Cost €{total_cost:,.2f} ({slippage_bps:.2f} bps slippage + "
            f"€{commission_cost:,.2f} commission)"
        )

        # Check for overrun
        self._check_cost_overrun(execution_id)

        return total_cost, cost_record

    def complete_execution(
        self,
        execution_id: str,
    ) -> ExecutionMonitoring:
        """
        Mark execution as complete.

        Args:
            execution_id: Execution identifier

        Returns:
            Final ExecutionMonitoring object

        Raises:
            ValueError: If execution not found
        """

        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found in monitor")

        monitoring = self.executions[execution_id]
        monitoring.completed_at = datetime.now()

        logger.info(
            f"Execution {execution_id} completed: "
            f"€{monitoring.actual_costs:,.2f} actual vs "
            f"€{monitoring.planned_cost:,.2f} planned "
            f"({monitoring.cost_overrun_pct:.1f}% overrun)"
        )

        return monitoring

    def get_monitoring_status(
        self,
        execution_id: str,
    ) -> ExecutionMonitoring:
        """
        Get current monitoring status for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            ExecutionMonitoring object with current status

        Raises:
            ValueError: If execution not found
        """

        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found in monitor")

        return self.executions[execution_id]

    def get_cost_breakdown(
        self,
        execution_id: str,
    ) -> dict:
        """
        Get detailed cost breakdown for an execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Dict with cost breakdown and metrics

        Raises:
            ValueError: If execution not found
        """

        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")

        monitoring = self.executions[execution_id]
        costs = self.tranche_costs.get(execution_id, [])

        # Calculate aggregates
        total_slippage = sum(c["slippage_cost"] for c in costs)
        total_commission = sum(c["commission_cost"] for c in costs)
        avg_slippage_bps = np.mean([c["slippage_bps"] for c in costs]) if costs else Decimal("0")

        return {
            "execution_id": execution_id,
            "planned_cost": monitoring.planned_cost,
            "actual_costs": monitoring.actual_costs,
            "cost_overrun": monitoring.cost_overrun,
            "cost_overrun_pct": monitoring.cost_overrun_pct,
            "is_within_budget": monitoring.is_within_budget,
            "tranches_completed": monitoring.tranches_completed,
            "tranches_total": monitoring.tranches_total,
            "progress_pct": monitoring.progress_pct,
            "total_slippage": total_slippage,
            "total_commission": total_commission,
            "avg_slippage_bps": avg_slippage_bps,
            "execution_duration": monitoring.execution_duration,
            "tranche_details": costs,
        }

    def compare_to_estimate(
        self,
        execution_id: str,
        estimated_slippage_bps: Decimal,
        estimated_slippage_usd: Decimal,
    ) -> dict:
        """
        Compare actual execution to original estimate.

        Args:
            execution_id: Execution identifier
            estimated_slippage_bps: Original estimated slippage in bps
            estimated_slippage_usd: Original estimated slippage in €

        Returns:
            Dict with comparison metrics
        """

        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")

        self.executions[execution_id]

        # Calculate actual slippage (excluding commission)
        costs = self.tranche_costs.get(execution_id, [])
        actual_slippage = sum(c["slippage_cost"] for c in costs)

        # Variance
        slippage_variance = actual_slippage - estimated_slippage_usd
        variance_pct = (
            (slippage_variance / estimated_slippage_usd) * Decimal("100")
            if estimated_slippage_usd > 0
            else Decimal("0")
        )

        logger.info(
            f"Execution {execution_id}: Actual slippage €{actual_slippage:,.2f} vs "
            f"estimated €{estimated_slippage_usd:,.2f} "
            f"({variance_pct:+.1f}%)"
        )

        return {
            "execution_id": execution_id,
            "estimated_slippage_bps": estimated_slippage_bps,
            "estimated_slippage_usd": estimated_slippage_usd,
            "actual_slippage_usd": actual_slippage,
            "slippage_variance": slippage_variance,
            "variance_pct": variance_pct,
            "estimate_accuracy": variance_pct <= Decimal("5"),  # Within 5% = good estimate
        }

    def _check_cost_overrun(self, execution_id: str):
        """
        Check for cost overrun and log alerts.

        Args:
            execution_id: Execution identifier
        """

        monitoring = self.executions[execution_id]

        if monitoring.cost_overrun <= Decimal("0"):
            return  # Within budget, no alert

        overrun_pct = monitoring.cost_overrun_pct

        if overrun_pct >= self.COST_OVERRUN_CRITICAL_THRESHOLD:
            logger.critical(
                f"CRITICAL: Execution {execution_id} cost overrun {overrun_pct:.1f}% "
                f"(€{monitoring.cost_overrun:,.2f} over budget)"
            )
        elif overrun_pct >= self.COST_OVERRUN_ALERT_THRESHOLD:
            logger.warning(
                f"WARNING: Execution {execution_id} cost overrun {overrun_pct:.1f}% "
                f"(€{monitoring.cost_overrun:,.2f} over budget)"
            )

    def estimate_remaining_budget(
        self,
        execution_id: str,
    ) -> tuple[Decimal, Decimal]:
        """
        Calculate remaining budget and run rate.

        Args:
            execution_id: Execution identifier

        Returns:
            Tuple of (remaining_budget, estimated_total_cost)
        """

        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")

        monitoring = self.executions[execution_id]

        # Remaining budget
        remaining = max(Decimal("0"), monitoring.planned_cost - monitoring.actual_costs)

        # If execution in progress, estimate total cost
        if monitoring.tranches_completed > 0 and monitoring.tranches_total > 0:
            avg_cost_per_tranche = monitoring.actual_costs / monitoring.tranches_completed
            estimated_total = avg_cost_per_tranche * monitoring.tranches_total
        else:
            estimated_total = monitoring.actual_costs

        return remaining, estimated_total

    def should_abort_execution(
        self,
        execution_id: str,
    ) -> tuple[bool, str]:
        """
        Determine if execution should be aborted due to cost overrun.

        Args:
            execution_id: Execution identifier

        Returns:
            Tuple of (should_abort, reason)
        """

        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")

        monitoring = self.executions[execution_id]

        # Abort if critical overrun (>10%)
        if monitoring.cost_overrun_pct >= self.COST_OVERRUN_CRITICAL_THRESHOLD:
            return True, (
                f"Critical cost overrun: {monitoring.cost_overrun_pct:.1f}% "
                f"(€{monitoring.cost_overrun:,.2f})"
            )

        # Estimate total cost and compare to budget
        if monitoring.tranches_completed > 0 and monitoring.tranches_total > 0:
            _remaining, estimated_total = self.estimate_remaining_budget(execution_id)

            if estimated_total > monitoring.planned_cost * Decimal("1.15"):
                # Estimated total >15% over budget
                return True, (
                    f"Estimated total cost exceeds budget by {(estimated_total / monitoring.planned_cost - 1) * 100:.1f}%"
                )

        return False, "Within acceptable cost limits"


# Global singleton
_execution_cost_monitor: ExecutionCostMonitor = None


def get_execution_cost_monitor() -> ExecutionCostMonitor:
    """Get or create global ExecutionCostMonitor instance."""
    global _execution_cost_monitor
    if _execution_cost_monitor is None:
        _execution_cost_monitor = ExecutionCostMonitor()

    return _execution_cost_monitor
