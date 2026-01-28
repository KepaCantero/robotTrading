"""
Canary Analyzer - Metrics Comparison and Analysis

Analyzes canary deployment metrics to make rollback/promotion decisions.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from statistics import mean
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class RollbackTrigger(str, Enum):
    """Types of rollback triggers."""

    ERROR_RATE_HIGH = "error_rate_high"
    LATENCY_HIGH = "latency_high"
    AVAILABILITY_LOW = "availability_low"
    THROUGHPUT_LOW = "throughput_low"
    MANUAL = "manual"


@dataclass
class MetricComparison:
    """Comparison between canary and baseline metrics."""

    metric_name: str
    canary_value: Decimal
    baseline_value: Decimal
    delta: Decimal
    delta_percentage: Decimal
    is_significant: bool
    threshold: Decimal

    # Statistical analysis
    p_value: Optional[Decimal] = None
    confidence_interval: Optional[tuple[Decimal, Decimal]] = None
    sample_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric": self.metric_name,
            "canary": f"{self.canary_value:.4f}",
            "baseline": f"{self.baseline_value:.4f}",
            "delta": f"{self.delta:.4f}",
            "delta_pct": f"{self.delta_percentage * 100:.2f}%",
            "significant": self.is_significant,
            "threshold": f"{self.threshold * 100:.2f}%",
            "p_value": f"{self.p_value:.4f}" if self.p_value else None,
            "confidence": (
                f"[{self.confidence_interval[0]:.4f}, {self.confidence_interval[1]:.4f}]"
                if self.confidence_interval
                else None
            ),
        }


@dataclass
class CanaryAnalysisResult:
    """Result of canary analysis."""

    deployment_id: int
    stage: int
    timestamp: datetime

    # Overall decision
    should_rollback: bool
    should_promote: bool
    confidence: Decimal  # 0.0 to 1.0

    # Metric comparisons
    comparisons: List[MetricComparison]

    # Rollback trigger
    rollback_trigger: Optional[RollbackTrigger] = None
    rollback_reason: Optional[str] = None

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "deployment_id": self.deployment_id,
            "stage": self.stage,
            "timestamp": self.timestamp.isoformat(),
            "decision": {
                "rollback": self.should_rollback,
                "promote": self.should_promote,
                "confidence": f"{self.confidence * 100:.1f}%",
            },
            "comparisons": [c.to_dict() for c in self.comparisons],
            "rollback": {
                "trigger": self.rollback_trigger.value if self.rollback_trigger else None,
                "reason": self.rollback_reason,
            },
            "recommendations": self.recommendations,
        }


class CanaryAnalyzer:
    """
    Canary deployment metrics analyzer.

    Responsibilities:
    - Compare canary vs baseline metrics
    - Statistical significance testing
    - Make rollback/promotion decisions
    - Generate recommendations
    """

    def __init__(
        self,
        service_name: str,
        db_path: str = "data/canary_deployments.db",
    ):
        """
        Initialize canary analyzer.

        Args:
            service_name: Name of service
            db_path: Path to database
        """
        self.service_name = service_name
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

        # Thresholds for rollback
        self.rollback_thresholds = {
            "error_rate_increase": Decimal("0.5"),  # 50% increase
            "latency_increase": Decimal("0.5"),  # 50% increase
            "availability_drop": Decimal("0.01"),  # 1% drop
            "throughput_drop": Decimal("0.2"),  # 20% drop
        }

        # Thresholds for promotion
        self.promotion_thresholds = {
            "error_rate_max": Decimal("0.01"),  # Max 1% error rate
            "latency_increase_max": Decimal("0.1"),  # Max 10% increase
            "availability_min": Decimal("0.995"),  # Min 99.5%
            "throughput_drop_max": Decimal("0.05"),  # Max 5% drop
        }

    async def analyze_stage(
        self,
        deployment_id: int,
        stage: int,
    ) -> CanaryAnalysisResult:
        """
        Analyze metrics for a specific stage.

        Args:
            deployment_id: Deployment ID
            stage: Stage number

        Returns:
            CanaryAnalysisResult
        """
        try:
            # Load metrics for this stage
            metrics = await self._load_stage_metrics(deployment_id, stage)

            if not metrics:
                self.logger.warning(f"No metrics found for stage {stage}")
                return CanaryAnalysisResult(
                    deployment_id=deployment_id,
                    stage=stage,
                    timestamp=datetime.utcnow(),
                    should_rollback=False,
                    should_promote=False,
                    confidence=Decimal("0"),
                    comparisons=[],
                    recommendations=["No metrics available for analysis"],
                )

            # Calculate aggregate metrics
            aggregate = await self._calculate_aggregate_metrics(metrics)

            # Compare with baseline
            comparisons = await self._compare_metrics(aggregate)

            # Make decision
            decision = await self._make_decision(comparisons)

            return CanaryAnalysisResult(
                deployment_id=deployment_id,
                stage=stage,
                timestamp=datetime.utcnow(),
                should_rollback=decision["rollback"],
                should_promote=decision["promote"],
                confidence=decision["confidence"],
                comparisons=comparisons,
                rollback_trigger=decision.get("trigger"),
                rollback_reason=decision.get("reason"),
                recommendations=decision.get("recommendations", []),
            )

        except Exception as e:
            self.logger.error(f"Error analyzing stage {stage}: {e}")
            raise

    async def _load_stage_metrics(
        self,
        deployment_id: int,
        stage: int,
    ) -> List[Dict[str, Any]]:
        """Load metrics for a specific stage."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT canary_requests, canary_successful, canary_failed,
                           canary_latency_p50, canary_latency_p95, canary_latency_p99,
                           canary_error_rate, canary_throughput,
                           baseline_requests, baseline_successful, baseline_failed,
                           baseline_latency_p50, baseline_latency_p95, baseline_latency_p99,
                           baseline_error_rate, baseline_throughput
                    FROM canary_metrics
                    WHERE deployment_id = ? AND stage = ?
                    ORDER BY timestamp
                """,
                    (deployment_id, stage),
                )

                rows = await cursor.fetchall()

                return [
                    {
                        "canary_requests": row[0],
                        "canary_successful": row[1],
                        "canary_failed": row[2],
                        "canary_latency_p50": row[3],
                        "canary_latency_p95": row[4],
                        "canary_latency_p99": row[5],
                        "canary_error_rate": Decimal(row[6]),
                        "canary_throughput": row[7],
                        "baseline_requests": row[8],
                        "baseline_successful": row[9],
                        "baseline_failed": row[10],
                        "baseline_latency_p50": row[11],
                        "baseline_latency_p95": row[12],
                        "baseline_latency_p99": row[13],
                        "baseline_error_rate": Decimal(row[14]),
                        "baseline_throughput": row[15],
                    }
                    for row in rows
                ]

        except (aiosqlite.Error, asyncio.TimeoutError, ConnectionError, OSError) as e:
            self.logger.error(f"Error loading metrics: {e}")
            return []

    async def _calculate_aggregate_metrics(
        self,
        metrics: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculate aggregate metrics from multiple samples."""
        if not metrics:
            return {}

        # Sum requests
        total_canary_requests = sum(m["canary_requests"] for m in metrics)
        total_baseline_requests = sum(m["baseline_requests"] for m in metrics)

        # Calculate averages
        canary_latency_p95 = mean(m["canary_latency_p95"] for m in metrics)
        baseline_latency_p95 = mean(m["baseline_latency_p95"] for m in metrics)

        canary_throughput = mean(m["canary_throughput"] for m in metrics)
        baseline_throughput = mean(m["baseline_throughput"] for m in metrics)

        # Calculate error rate (weighted by requests)
        total_canary_errors = sum(m["canary_failed"] for m in metrics)
        total_baseline_errors = sum(m["baseline_failed"] for m in metrics)

        canary_error_rate = (
            Decimal(total_canary_errors) / Decimal(total_canary_requests)
            if total_canary_requests > 0
            else Decimal("0")
        )

        baseline_error_rate = (
            Decimal(total_baseline_errors) / Decimal(total_baseline_requests)
            if total_baseline_requests > 0
            else Decimal("0")
        )

        # Calculate availability
        total_canary_successful = sum(m["canary_successful"] for m in metrics)
        total_baseline_successful = sum(m["baseline_successful"] for m in metrics)

        canary_availability = (
            Decimal(total_canary_successful) / Decimal(total_canary_requests)
            if total_canary_requests > 0
            else Decimal("0")
        )

        baseline_availability = (
            Decimal(total_baseline_successful) / Decimal(total_baseline_requests)
            if total_baseline_requests > 0
            else Decimal("0")
        )

        return {
            "canary": {
                "requests": total_canary_requests,
                "error_rate": canary_error_rate,
                "latency_p95": canary_latency_p95,
                "throughput": canary_throughput,
                "availability": canary_availability,
            },
            "baseline": {
                "requests": total_baseline_requests,
                "error_rate": baseline_error_rate,
                "latency_p95": baseline_latency_p95,
                "throughput": baseline_throughput,
                "availability": baseline_availability,
            },
        }

    async def _compare_metrics(
        self,
        aggregate: Dict[str, Any],
    ) -> List[MetricComparison]:
        """Compare canary and baseline metrics."""
        comparisons = []

        canary = aggregate["canary"]
        baseline = aggregate["baseline"]

        # Error rate comparison
        error_delta = canary["error_rate"] - baseline["error_rate"]
        error_delta_pct = (
            error_delta / baseline["error_rate"] if baseline["error_rate"] > 0 else Decimal("0")
        )

        comparisons.append(
            MetricComparison(
                metric_name="error_rate",
                canary_value=canary["error_rate"],
                baseline_value=baseline["error_rate"],
                delta=error_delta,
                delta_percentage=error_delta_pct,
                is_significant=error_delta_pct > self.rollback_thresholds["error_rate_increase"],
                threshold=self.rollback_thresholds["error_rate_increase"],
            )
        )

        # Latency comparison
        latency_delta = Decimal(str(canary["latency_p95"])) - Decimal(str(baseline["latency_p95"]))
        latency_delta_pct = (
            latency_delta / Decimal(str(baseline["latency_p95"]))
            if baseline["latency_p95"] > 0
            else Decimal("0")
        )

        comparisons.append(
            MetricComparison(
                metric_name="latency_p95",
                canary_value=Decimal(str(canary["latency_p95"])),
                baseline_value=Decimal(str(baseline["latency_p95"])),
                delta=latency_delta,
                delta_percentage=latency_delta_pct,
                is_significant=latency_delta_pct > self.rollback_thresholds["latency_increase"],
                threshold=self.rollback_thresholds["latency_increase"],
            )
        )

        # Availability comparison
        avail_delta = canary["availability"] - baseline["availability"]
        avail_delta_pct = abs(avail_delta)

        comparisons.append(
            MetricComparison(
                metric_name="availability",
                canary_value=canary["availability"],
                baseline_value=baseline["availability"],
                delta=avail_delta,
                delta_percentage=avail_delta_pct,
                is_significant=avail_delta < -self.rollback_thresholds["availability_drop"],
                threshold=self.rollback_thresholds["availability_drop"],
            )
        )

        # Throughput comparison
        throughput_delta = Decimal(str(canary["throughput"])) - Decimal(str(baseline["throughput"]))
        throughput_delta_pct = (
            throughput_delta / Decimal(str(baseline["throughput"]))
            if baseline["throughput"] > 0
            else Decimal("0")
        )

        comparisons.append(
            MetricComparison(
                metric_name="throughput",
                canary_value=Decimal(str(canary["throughput"])),
                baseline_value=Decimal(str(baseline["throughput"])),
                delta=throughput_delta,
                delta_percentage=throughput_delta_pct,
                is_significant=throughput_delta < -self.rollback_thresholds["throughput_drop"],
                threshold=self.rollback_thresholds["throughput_drop"],
            )
        )

        return comparisons

    async def _make_decision(
        self,
        comparisons: List[MetricComparison],
    ) -> Dict[str, Any]:
        """Make rollback/promotion decision."""
        rollback = False
        promote = True
        trigger = None
        reason = None
        recommendations = []

        # Check rollback conditions
        for comp in comparisons:
            if comp.is_significant:
                if comp.metric_name == "error_rate" and comp.delta > 0:
                    rollback = True
                    trigger = RollbackTrigger.ERROR_RATE_HIGH
                    reason = f"Error rate increased by {comp.delta_percentage * 100:.1f}%"
                    recommendations.append(f"ERROR: {reason}")

                elif comp.metric_name == "latency_p95" and comp.delta > 0:
                    rollback = True
                    trigger = RollbackTrigger.LATENCY_HIGH
                    reason = f"Latency increased by {comp.delta_percentage * 100:.1f}%"
                    recommendations.append(f"ERROR: {reason}")

                elif comp.metric_name == "availability" and comp.delta < 0:
                    rollback = True
                    trigger = RollbackTrigger.AVAILABILITY_LOW
                    reason = f"Availability dropped by {abs(comp.delta_percentage) * 100:.1f}%"
                    recommendations.append(f"ERROR: {reason}")

                elif comp.metric_name == "throughput" and comp.delta < 0:
                    rollback = True
                    trigger = RollbackTrigger.THROUGHPUT_LOW
                    reason = f"Throughput dropped by {abs(comp.delta_percentage) * 100:.1f}%"
                    recommendations.append(f"ERROR: {reason}")

        # Check promotion conditions
        if not rollback:
            for comp in comparisons:
                if comp.metric_name == "error_rate":
                    if comp.canary_value > self.promotion_thresholds["error_rate_max"]:
                        promote = False
                        recommendations.append(
                            f"WARNING: Error rate {comp.canary_value * 100:.2f}% exceeds threshold"
                        )

                elif comp.metric_name == "latency_p95":
                    if comp.delta_percentage > self.promotion_thresholds["latency_increase_max"]:
                        promote = False
                        recommendations.append(
                            f"WARNING: Latency increase {comp.delta_percentage * 100:.1f}% exceeds threshold"
                        )

                elif comp.metric_name == "availability":
                    if comp.canary_value < self.promotion_thresholds["availability_min"]:
                        promote = False
                        recommendations.append(
                            f"WARNING: Availability {comp.canary_value * 100:.2f}% below threshold"
                        )

                elif comp.metric_name == "throughput":
                    if comp.delta_percentage < -self.promotion_thresholds["throughput_drop_max"]:
                        promote = False
                        recommendations.append(
                            f"WARNING: Throughput drop {abs(comp.delta_percentage) * 100:.1f}% exceeds threshold"
                        )

        if promote:
            recommendations.append("All metrics within promotion thresholds")

        # Calculate confidence
        if rollback:
            confidence = Decimal("0.95")
        elif promote:
            confidence = Decimal("0.90")
        else:
            confidence = Decimal("0.50")

        return {
            "rollback": rollback,
            "promote": promote,
            "confidence": confidence,
            "trigger": trigger,
            "reason": reason,
            "recommendations": recommendations,
        }
