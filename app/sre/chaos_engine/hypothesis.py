from __future__ import annotations

# mypy: ignore-errors
"""
Chaos Hypothesis - Scientific Approach to Chaos (SRE Rule 20)

Implements hypothesis-driven chaos engineering:
- Formulate hypotheses
- Design experiments
- Validate results
- Calculate confidence
- Document findings

Usage:
    hypothesis = ChaosHypothesis(
        name="pod-kill-resilience",
        description="System remains available when pods are killed"
    )
    validator = HypothesisValidator()
    result = await validator.validate(hypothesis)
"""


import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import aiosqlite

from app.shared.utils.safe_parse import safe_parse

logger = logging.getLogger(__name__)


class HypothesisStatus(str, Enum):
    """Status of hypothesis validation."""

    PASSED = "passed"  # Hypothesis confirmed
    FAILED = "failed"  # Hypothesis rejected
    INCONCLUSIVE = "inconclusive"  # Insufficient data
    PARTIAL = "partial"  # Partially confirmed


@dataclass
class ChaosHypothesis:
    """
    Chaos engineering hypothesis.

    A testable prediction about system behavior under chaos.
    """

    name: str
    description: str
    expected_behavior: str
    baseline_metrics: dict[str, Any]
    actual_metrics: dict[str, Any]
    steady_state_threshold: Decimal = Decimal("0.95")  # 95% of baseline
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Metrics to validate
    validate_availability: bool = True
    validate_latency: bool = True
    validate_error_rate: bool = True
    validate_throughput: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "expected_behavior": self.expected_behavior,
            "baseline_metrics": self.baseline_metrics,
            "actual_metrics": self.actual_metrics,
            "steady_state_threshold": f"{self.steady_state_threshold * 100}%",
            "created_at": self.created_at.isoformat(),
            "validate_availability": self.validate_availability,
            "validate_latency": self.validate_latency,
            "validate_error_rate": self.validate_error_rate,
            "validate_throughput": self.validate_throughput,
        }


@dataclass
class ValidationResult:
    """
    Result of hypothesis validation.

    Provides statistical analysis and confidence levels.
    """

    hypothesis_name: str
    status: HypothesisStatus
    confidence: Decimal  # 0.0 to 1.0
    details: dict[str, Any]
    validated_at: datetime = field(default_factory=datetime.utcnow)

    # Metric comparisons
    availability_delta: Decimal | None = None
    latency_delta: Decimal | None = None
    error_rate_delta: Decimal | None = None
    throughput_delta: Decimal | None = None

    # Statistical analysis
    p_value: Decimal | None = None
    effect_size: Decimal | None = None
    sample_size: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hypothesis_name": self.hypothesis_name,
            "status": self.status.value,
            "confidence": f"{self.confidence * 100:.1f}%",
            "details": self.details,
            "validated_at": self.validated_at.isoformat(),
            "deltas": {
                "availability": (
                    f"{self.availability_delta * 100:.2f}%" if self.availability_delta else None
                ),
                "latency": f"{self.latency_delta:.1f}%" if self.latency_delta else None,
                "error_rate": (
                    f"{self.error_rate_delta * 100:.2f}%" if self.error_rate_delta else None
                ),
                "throughput": f"{self.throughput_delta:.1f}%" if self.throughput_delta else None,
            },
            "statistics": {
                "p_value": f"{self.p_value:.4f}" if self.p_value else None,
                "effect_size": f"{self.effect_size:.4f}" if self.effect_size else None,
                "sample_size": self.sample_size,
            },
        }

    def is_passed(self) -> bool:
        """Check if hypothesis passed."""
        return self.status == HypothesisStatus.PASSED


class HypothesisValidator:
    """
    Chaos hypothesis validation.

    Responsibilities:
    - Compare baseline vs actual metrics
    - Calculate statistical significance
    - Determine hypothesis status
    - Calculate confidence levels
    - Generate detailed reports
    """

    def __init__(
        self,
        service_name: str,
        db_path: str = "data/chaos_hypotheses.db",
    ):
        """
        Initialize hypothesis validator.

        Args:
            service_name: Name of service
            db_path: Path to database
        """
        self.service_name = service_name
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    async def initialize(self) -> None:
        """Initialize hypothesis validator."""
        try:
            await self._init_database()
            self.logger.info("HypothesisValidator initialized")
        except (asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error initializing: {e}")
            raise

    async def _init_database(self) -> None:
        """Initialize database schema."""
        try:
            from pathlib import Path

            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS chaos_hypotheses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        expected_behavior TEXT NOT NULL,
                        baseline_metrics TEXT NOT NULL,
                        actual_metrics TEXT NOT NULL,
                        steady_state_threshold TEXT NOT NULL,
                        status TEXT NOT NULL,
                        confidence TEXT NOT NULL,
                        availability_delta TEXT,
                        latency_delta TEXT,
                        error_rate_delta TEXT,
                        throughput_delta TEXT,
                        p_value TEXT,
                        effect_size TEXT,
                        sample_size INTEGER NOT NULL,
                        details TEXT NOT NULL,
                        validated_at TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT (datetime('utc'))
                    )
                """
                )

                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_hypotheses_service_status
                    ON chaos_hypotheses(service_name, status)
                """
                )

                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise

    async def validate(self, hypothesis: ChaosHypothesis) -> ValidationResult:
        """
        Validate chaos hypothesis.

        Args:
            hypothesis: Hypothesis to validate

        Returns:
            ValidationResult with analysis
        """
        self.logger.info(f"Validating hypothesis: {hypothesis.name}")

        # Compare metrics
        comparisons = await self._compare_metrics(hypothesis)

        # Calculate deltas
        deltas = await self._calculate_deltas(hypothesis, comparisons)

        # Determine steady state
        steady_state = await self._check_steady_state(hypothesis, deltas)

        # Calculate statistical significance
        statistics = await self._calculate_statistics(hypothesis, comparisons)

        # Determine status
        status = await self._determine_status(steady_state, statistics)

        # Calculate confidence
        confidence = await self._calculate_confidence(status, statistics)

        # Create result
        result = ValidationResult(
            hypothesis_name=hypothesis.name,
            status=status,
            confidence=confidence,
            details={
                "steady_state": steady_state,
                "comparisons": comparisons,
                "statistics": statistics,
            },
            availability_delta=deltas.get("availability"),
            latency_delta=deltas.get("latency"),
            error_rate_delta=deltas.get("error_rate"),
            throughput_delta=deltas.get("throughput"),
            p_value=statistics.get("p_value"),
            effect_size=statistics.get("effect_size"),
            sample_size=statistics.get("sample_size", 0),
        )

        # Save to database
        await self._save_result(hypothesis, result)

        return result

    async def _compare_metrics(
        self,
        hypothesis: ChaosHypothesis,
    ) -> dict[str, dict[str, Any]]:
        """Compare baseline vs actual metrics."""
        baseline = hypothesis.baseline_metrics
        actual = hypothesis.actual_metrics

        comparisons = {}

        # Availability
        if hypothesis.validate_availability:
            baseline_avail = Decimal(str(baseline.get("availability", 1.0)))
            actual_avail = Decimal(str(actual.get("availability", 1.0)))
            comparisons["availability"] = {
                "baseline": baseline_avail,
                "actual": actual_avail,
                "delta": actual_avail - baseline_avail,
                "delta_pct": (
                    ((actual_avail - baseline_avail) / baseline_avail * 100)
                    if baseline_avail > 0
                    else Decimal("0")
                ),
            }

        # Latency
        if hypothesis.validate_latency:
            baseline_latency = baseline.get("latency_p95", 0)
            actual_latency = actual.get("latency_p95", 0)
            comparisons["latency"] = {
                "baseline": baseline_latency,
                "actual": actual_latency,
                "delta": actual_latency - baseline_latency,
                "delta_pct": (
                    ((actual_latency - baseline_latency) / baseline_latency * 100)
                    if baseline_latency > 0
                    else 0
                ),
            }

        # Error rate
        if hypothesis.validate_error_rate:
            baseline_errors = Decimal(str(baseline.get("error_rate", 0.0)))
            actual_errors = Decimal(str(actual.get("error_rate", 0.0)))
            comparisons["error_rate"] = {
                "baseline": baseline_errors,
                "actual": actual_errors,
                "delta": actual_errors - baseline_errors,
                "delta_pct": (
                    ((actual_errors - baseline_errors) / baseline_errors * 100)
                    if baseline_errors > 0
                    else Decimal("0")
                ),
            }

        # Throughput
        if hypothesis.validate_throughput:
            baseline_throughput = baseline.get("throughput", 0)
            actual_throughput = actual.get("throughput", 0)
            comparisons["throughput"] = {
                "baseline": baseline_throughput,
                "actual": actual_throughput,
                "delta": actual_throughput - baseline_throughput,
                "delta_pct": (
                    ((actual_throughput - baseline_throughput) / baseline_throughput * 100)
                    if baseline_throughput > 0
                    else 0
                ),
            }

        return comparisons

    async def _calculate_deltas(
        self,
        hypothesis: ChaosHypothesis,
        comparisons: dict[str, dict[str, Any]],
    ) -> dict[str, Decimal]:
        """Calculate metric deltas."""
        deltas = {}

        for metric_name, comparison in comparisons.items():
            delta = comparison.get("delta_pct", 0)
            if isinstance(delta, (int, float)):
                deltas[metric_name] = Decimal(str(delta / 100))
            else:
                deltas[metric_name] = delta

        return deltas

    async def _check_steady_state(
        self,
        hypothesis: ChaosHypothesis,
        deltas: dict[str, Decimal],
    ) -> dict[str, bool]:
        """Check if system maintained steady state."""
        steady_state = {}
        threshold = hypothesis.steady_state_threshold

        # Availability should stay high
        if "availability" in deltas:
            delta = deltas["availability"]
            steady_state["availability"] = delta >= (Decimal("1.0") - threshold)

        # Latency should not increase too much
        if "latency" in deltas:
            delta = deltas["latency"]
            steady_state["latency"] = delta <= (Decimal("1.0") - threshold)

        # Error rate should not increase
        if "error_rate" in deltas:
            delta = deltas["error_rate"]
            steady_state["error_rate"] = delta <= threshold

        # Throughput should not drop too much
        if "throughput" in deltas:
            delta = deltas["throughput"]
            steady_state["throughput"] = delta >= -(Decimal("1.0") - threshold)

        return steady_state

    async def _calculate_statistics(
        self,
        hypothesis: ChaosHypothesis,
        comparisons: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate statistical significance."""
        # This is a simplified implementation
        # In production, you would use proper statistical tests

        statistics = {
            "p_value": Decimal("0.05"),  # Placeholder
            "effect_size": Decimal("0.5"),  # Placeholder
            "sample_size": 100,  # Placeholder
            "test_used": "t-test",  # Placeholder
        }

        return statistics

    async def _determine_status(
        self,
        steady_state: dict[str, bool],
        statistics: dict[str, Any],
    ) -> HypothesisStatus:
        """Determine hypothesis status."""
        # Check if all metrics maintained steady state
        all_steady = all(steady_state.values())

        if all_steady:
            return HypothesisStatus.PASSED

        # Check if most metrics maintained steady state
        steady_count = sum(1 for v in steady_state.values() if v)
        total_count = len(steady_state)

        if steady_count >= total_count * 0.7:
            return HypothesisStatus.PARTIAL

        if steady_count >= total_count * 0.3:
            return HypothesisStatus.INCONCLUSIVE

        return HypothesisStatus.FAILED

    async def _calculate_confidence(
        self,
        status: HypothesisStatus,
        statistics: dict[str, Any],
    ) -> Decimal:
        """Calculate confidence in result."""
        # Simplified confidence calculation
        if status == HypothesisStatus.PASSED:
            return Decimal("0.95")
        elif status == HypothesisStatus.PARTIAL:
            return Decimal("0.70")
        elif status == HypothesisStatus.INCONCLUSIVE:
            return Decimal("0.50")
        else:
            return Decimal("0.30")

    async def _save_result(
        self,
        hypothesis: ChaosHypothesis,
        result: ValidationResult,
    ) -> None:
        """Save validation result to database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO chaos_hypotheses
                    (service_name, name, description, expected_behavior, baseline_metrics,
                     actual_metrics, steady_state_threshold, status, confidence,
                     availability_delta, latency_delta, error_rate_delta, throughput_delta,
                     p_value, effect_size, sample_size, details, validated_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        self.service_name,
                        hypothesis.name,
                        hypothesis.description,
                        hypothesis.expected_behavior,
                        str(hypothesis.baseline_metrics),
                        str(hypothesis.actual_metrics),
                        str(hypothesis.steady_state_threshold),
                        result.status.value,
                        str(result.confidence),
                        str(result.availability_delta) if result.availability_delta else None,
                        str(result.latency_delta) if result.latency_delta else None,
                        str(result.error_rate_delta) if result.error_rate_delta else None,
                        str(result.throughput_delta) if result.throughput_delta else None,
                        str(result.p_value) if result.p_value else None,
                        str(result.effect_size) if result.effect_size else None,
                        result.sample_size,
                        str(result.details),
                        result.validated_at.isoformat(),
                        hypothesis.created_at.isoformat(),
                    ),
                )
                await db.commit()

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error saving result: {e}")

    async def get_hypothesis_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get hypothesis validation history."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT name, status, confidence, validated_at, details
                    FROM chaos_hypotheses
                    WHERE service_name = ?
                    ORDER BY validated_at DESC
                    LIMIT ?
                """,
                    (self.service_name, limit),
                )

                rows = await cursor.fetchall()

                return [
                    {
                        "name": row[0],
                        "status": row[1],
                        "confidence": row[2],
                        "validated_at": row[3],
                        "details": safe_parse(row[4], default={}),
                    }
                    for row in rows
                ]

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error getting history: {e}")
            return []

    async def get_summary(self) -> dict[str, Any]:
        """Get hypothesis validator summary."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get total count
                cursor = await db.execute(
                    """
                    SELECT COUNT(*) FROM chaos_hypotheses
                    WHERE service_name = ?
                """,
                    (self.service_name,),
                )
                total = (await cursor.fetchone())[0]

                # Get passed count
                cursor = await db.execute(
                    """
                    SELECT COUNT(*) FROM chaos_hypotheses
                    WHERE service_name = ? AND status = 'passed'
                """,
                    (self.service_name,),
                )
                passed = (await cursor.fetchone())[0]

                return {
                    "service": self.service_name,
                    "total_hypotheses": total,
                    "passed": passed,
                    "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "N/A",
                }

        except (aiosqlite.Error, asyncio.TimeoutError, OSError) as e:
            self.logger.error(f"Error getting summary: {e}")
            return {}
