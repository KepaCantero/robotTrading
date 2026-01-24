"""
Robustness Scorer (TASK-6.1 Phase 3)

Composite production readiness metric (0-100) answering: "Is this deployable?"

Scoring Formula:
- Consistency (30%): % windows passing performance thresholds (min 60% profitable)
- Stability (25%): Parameter variance across windows (low = stable)
- Sensitivity (20%): Elasticity measure (low elasticity = robust)
- Overfitting Penalty (15%): In-sample vs out-of-sample degradation
- Regime Robustness (10%): Performance across different market regimes

Overall Score >= 80: PASS (Safe for production)
Overall Score 60-79: WARN (Conditional - monitor closely)
Overall Score < 60: FAIL (Too risky - needs improvement)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class ProductionReadiness(str, Enum):
    """Production readiness verdict."""

    PASS = "PASS"  # Score >= 80, safe for production
    WARN = "WARN"  # Score 60-79, use with caution
    FAIL = "FAIL"  # Score < 60, too risky


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "LOW"  # No significant issues
    MEDIUM = "MEDIUM"  # Some concerns, manageable
    HIGH = "HIGH"  # Major concerns, needs attention
    CRITICAL = "CRITICAL"  # Critical issues, do not deploy


@dataclass
class RiskFactor:
    """Individual risk factor identified during robustness assessment."""

    name: str
    severity: RiskLevel
    description: str
    recommendation: str
    impact_on_score: float  # Points deducted from robustness score


@dataclass
class RobustnessScoreDetail:
    """Detailed breakdown of robustness score components."""

    consistency_score: float  # 0-100
    stability_score: float  # 0-100
    sensitivity_score: float  # 0-100
    overfitting_penalty: float  # 0-100 (lower is worse)
    regime_robustness_score: float  # 0-100
    overall_score: float  # 0-100
    weighted_score: float  # 0-100 (with weights applied)


@dataclass
class RobustnessResult:
    """Result of robustness analysis."""

    strategy_name: str
    parameter_name: Optional[str] = None
    overall_robustness_score: float = 0.0
    production_readiness: ProductionReadiness = ProductionReadiness.FAIL
    risk_level: RiskLevel = RiskLevel.HIGH
    score_details: Optional[RobustnessScoreDetail] = None
    risk_factors: List[RiskFactor] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "strategy_name": self.strategy_name,
            "parameter_name": self.parameter_name,
            "overall_robustness_score": float(self.overall_robustness_score),
            "production_readiness": self.production_readiness.value,
            "risk_level": self.risk_level.value,
            "risk_factors": [
                {
                    "name": rf.name,
                    "severity": rf.severity.value,
                    "description": rf.description,
                    "recommendation": rf.recommendation,
                    "impact": float(rf.impact_on_score),
                }
                for rf in self.risk_factors
            ],
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RobustnessReport:
    """Comprehensive robustness analysis report."""

    analysis_date: datetime = field(default_factory=datetime.now)
    results: Dict[str, RobustnessResult] = field(default_factory=dict)
    summary_score: float = 0.0
    deployable_count: int = 0
    warning_count: int = 0
    failed_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "summary_score": float(self.summary_score),
            "deployable_count": self.deployable_count,
            "warning_count": self.warning_count,
            "failed_count": self.failed_count,
            "results": {name: result.to_dict() for name, result in self.results.items()},
        }

    def to_json(self, filepath: Optional[Path] = None) -> str:
        """Serialize to JSON string or file."""
        json_str = json.dumps(self.to_dict(), indent=2)
        if filepath:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, "w") as f:
                f.write(json_str)
            logger.info(f"Robustness report saved to {filepath}")
        return json_str


class RobustnessScorer:
    """
    Score parameters/strategies for production readiness.

    Answers: "Is this safe to deploy in live trading?"
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize robustness scorer.

        Args:
            config: Configuration dictionary with thresholds
        """
        self.config = config or self._get_default_config()

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "robustness": {
                "weighting": {
                    "consistency": 0.30,  # % windows profitable
                    "stability": 0.25,  # Parameter consistency
                    "sensitivity": 0.20,  # Elasticity (inverse)
                    "overfitting": 0.15,  # IS/OOS gap
                    "regime_robustness": 0.10,  # Cross-regime performance
                },
                "thresholds": {
                    "pass": 80.0,  # >= 80 = PASS
                    "warn": 60.0,  # 60-79 = WARN
                    "fail": 0.0,  # < 60 = FAIL
                },
                "component_targets": {
                    "min_consistency": 0.60,  # 60% windows profitable
                    "min_stability": 70.0,  # Stability score >= 70
                    "max_sensitivity": 2.0,  # Elasticity <= 2.0
                    "max_overfitting_gap": 0.20,  # IS/OOS gap <= 20%
                    "min_regime_robustness": 0.70,  # 70% across regimes
                },
            }
        }

    def calculate_robustness_score(
        self,
        strategy_name: str,
        consistency_score: float,  # 0-100: % windows profitable
        stability_score: float,  # 0-100: parameter consistency
        sensitivity_score: float,  # 0-100: inverse of elasticity
        overfitting_penalty: float,  # 0-100: (1 - IS/OOS gap)
        regime_robustness_score: float,  # 0-100: cross-regime performance
        parameter_name: Optional[str] = None,
    ) -> RobustnessResult:
        """
        Calculate comprehensive robustness score.

        Args:
            strategy_name: Name of strategy
            consistency_score: 0-100, % of windows meeting thresholds
            stability_score: 0-100, from ParameterStabilityMetrics
            sensitivity_score: 0-100, inverse of elasticity
            overfitting_penalty: 0-100, (1 - IS/OOS_gap)
            regime_robustness_score: 0-100, performance across regimes
            parameter_name: Optional specific parameter being scored

        Returns:
            RobustnessResult with score and verdict
        """
        result = RobustnessResult(
            strategy_name=strategy_name,
            parameter_name=parameter_name,
        )

        # Normalize all scores to 0-100 range
        scores = {
            "consistency": max(0.0, min(100.0, consistency_score)),
            "stability": max(0.0, min(100.0, stability_score)),
            "sensitivity": max(0.0, min(100.0, sensitivity_score)),
            "overfitting": max(0.0, min(100.0, overfitting_penalty)),
            "regime_robustness": max(0.0, min(100.0, regime_robustness_score)),
        }

        # Apply weights
        weights = self.config["robustness"]["weighting"]
        weighted_score = (
            scores["consistency"] * weights["consistency"]
            + scores["stability"] * weights["stability"]
            + scores["sensitivity"] * weights["sensitivity"]
            + scores["overfitting"] * weights["overfitting"]
            + scores["regime_robustness"] * weights["regime_robustness"]
        )

        result.score_details = RobustnessScoreDetail(
            consistency_score=scores["consistency"],
            stability_score=scores["stability"],
            sensitivity_score=scores["sensitivity"],
            overfitting_penalty=scores["overfitting"],
            regime_robustness_score=scores["regime_robustness"],
            overall_score=np.mean(list(scores.values())),  # type: ignore
            weighted_score=weighted_score,
        )

        # Identify risk factors
        result.risk_factors = self._identify_risk_factors(scores)

        # Calculate final score with risk adjustments
        risk_penalty = self._calculate_risk_penalty(result.risk_factors)
        result.overall_robustness_score = weighted_score - risk_penalty

        # Determine production readiness
        result.production_readiness = self._determine_readiness(result.overall_robustness_score)
        result.risk_level = self._determine_risk_level(result.risk_factors)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(scores, result.risk_factors)

        logger.info(
            f"{strategy_name}: robustness={result.overall_robustness_score:.1f}, "
            f"readiness={result.production_readiness.value}"
        )

        return result

    def _identify_risk_factors(self, scores: Dict[str, float]) -> List[RiskFactor]:
        """Identify risk factors from score components."""
        factors = []
        thresholds = self.config["robustness"]["component_targets"]

        # Check consistency
        if scores["consistency"] < thresholds["min_consistency"] * 100:
            factors.append(
                RiskFactor(
                    name="Low Consistency",
                    severity=RiskLevel.HIGH,
                    description=f"Only {scores['consistency']:.1f}% of windows meet performance thresholds "
                    f"(target: {thresholds['min_consistency']*100:.0f}%)",
                    recommendation="Improve parameter selection or lower thresholds",
                    impact_on_score=15.0,
                )
            )

        # Check stability
        if scores["stability"] < thresholds["min_stability"]:
            factors.append(
                RiskFactor(
                    name="Unstable Parameters",
                    severity=RiskLevel.MEDIUM if scores["stability"] > 50 else RiskLevel.HIGH,
                    description=f"Parameter consistency score {scores['stability']:.1f} "
                    f"(target: {thresholds['min_stability']})",
                    recommendation="Parameters vary too much across windows - likely curve-fitted",
                    impact_on_score=10.0,
                )
            )

        # Check sensitivity (high elasticity = critical parameter)
        if scores["sensitivity"] < 50.0:
            factors.append(
                RiskFactor(
                    name="High Parameter Sensitivity",
                    severity=RiskLevel.MEDIUM,
                    description="Parameters are very sensitive to small changes "
                    f"(sensitivity score: {scores['sensitivity']:.1f})",
                    recommendation="Small parameter changes cause large performance swings",
                    impact_on_score=8.0,
                )
            )

        # Check overfitting
        if scores["overfitting"] < (1 - thresholds["max_overfitting_gap"]) * 100:
            factors.append(
                RiskFactor(
                    name="Overfitting Detected",
                    severity=RiskLevel.HIGH,
                    description="Large in-sample vs out-of-sample gap "
                    f"(overfitting penalty: {scores['overfitting']:.1f})",
                    recommendation="Strategy performs much better on training data than test data",
                    impact_on_score=15.0,
                )
            )

        # Check regime robustness
        if scores["regime_robustness"] < thresholds["min_regime_robustness"] * 100:
            factors.append(
                RiskFactor(
                    name="Regime Dependence",
                    severity=RiskLevel.MEDIUM,
                    description="Performance varies significantly across market regimes "
                    f"(score: {scores['regime_robustness']:.1f})",
                    recommendation="Strategy may fail in different market conditions",
                    impact_on_score=10.0,
                )
            )

        return factors

    def _calculate_risk_penalty(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate total penalty from risk factors."""
        return sum(rf.impact_on_score for rf in risk_factors)

    def _determine_readiness(self, score: float) -> ProductionReadiness:
        """Determine production readiness based on score."""
        thresholds = self.config["robustness"]["thresholds"]

        if score >= thresholds["pass"]:
            return ProductionReadiness.PASS
        elif score >= thresholds["warn"]:
            return ProductionReadiness.WARN
        else:
            return ProductionReadiness.FAIL

    def _determine_risk_level(self, risk_factors: List[RiskFactor]) -> RiskLevel:
        """Determine overall risk level from risk factors."""
        if not risk_factors:
            return RiskLevel.LOW

        # Check for critical factors
        if any(rf.severity == RiskLevel.CRITICAL for rf in risk_factors):
            return RiskLevel.CRITICAL

        # Check for multiple high severity factors
        high_factors = [rf for rf in risk_factors if rf.severity == RiskLevel.HIGH]
        if len(high_factors) >= 2:
            return RiskLevel.HIGH

        if high_factors:
            return RiskLevel.HIGH

        # Check for medium factors
        medium_factors = [rf for rf in risk_factors if rf.severity == RiskLevel.MEDIUM]
        if len(medium_factors) >= 2:
            return RiskLevel.MEDIUM

        if medium_factors:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _generate_recommendations(
        self, scores: Dict[str, float], risk_factors: List[RiskFactor]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Add recommendations from risk factors
        for factor in risk_factors:
            recommendations.append(f"• {factor.name}: {factor.recommendation}")

        # Add positive feedback for strong areas
        if scores["consistency"] >= 80:
            recommendations.append("✓ Consistency is excellent - strategy wins in most periods")

        if scores["stability"] >= 80:
            recommendations.append("✓ Parameters are stable - consistent across time periods")

        if scores["sensitivity"] >= 80:
            recommendations.append("✓ Parameters are robust - insensitive to small changes")

        # Priority action if failing
        if not recommendations:
            if scores["consistency"] < 60:
                recommendations.append("Priority: Improve parameter optimization and selection")
            elif scores["stability"] < 60:
                recommendations.append("Priority: Reduce overfitting and improve generalization")
            elif scores["overfitting"] < 60:
                recommendations.append("Priority: Address in-sample vs out-of-sample degradation")

        return recommendations

    def batch_score_parameters(
        self,
        results: Dict[str, Dict[str, float]],
        strategy_name: str,
    ) -> RobustnessReport:
        """
        Score multiple parameters and generate report.

        Args:
            results: Dict mapping parameter names to score dicts with keys:
                     consistency, stability, sensitivity, overfitting, regime_robustness
            strategy_name: Name of strategy

        Returns:
            RobustnessReport with all scores
        """
        report = RobustnessReport()

        for param_name, scores in results.items():
            robustness_result = self.calculate_robustness_score(
                strategy_name=strategy_name,
                consistency_score=scores.get("consistency", 50.0),
                stability_score=scores.get("stability", 50.0),
                sensitivity_score=scores.get("sensitivity", 50.0),
                overfitting_penalty=scores.get("overfitting", 50.0),
                regime_robustness_score=scores.get("regime_robustness", 50.0),
                parameter_name=param_name,
            )

            report.results[param_name] = robustness_result

            # Count readiness
            if robustness_result.production_readiness == ProductionReadiness.PASS:
                report.deployable_count += 1
            elif robustness_result.production_readiness == ProductionReadiness.WARN:
                report.warning_count += 1
            else:
                report.failed_count += 1

        # Calculate summary score
        scores_list = [r.overall_robustness_score for r in report.results.values()]
        if scores_list:
            report.summary_score = float(np.mean(scores_list))

        logger.info(
            f"Batch scoring complete: {report.deployable_count} PASS, "
            f"{report.warning_count} WARN, {report.failed_count} FAIL"
        )

        return report

    def print_robustness_report(self, report: RobustnessReport) -> None:
        """Print human-readable robustness report."""
        print("\n" + "=" * 90)
        print("ROBUSTNESS ASSESSMENT REPORT")
        print("=" * 90)
        print(f"Analysis Date: {report.analysis_date.isoformat()}")
        print(f"Summary Score: {report.summary_score:.1f}/100")
        print("\nDeployment Status:")
        print(f"  ✓ PASS (Ready):   {report.deployable_count}")
        print(f"  ⚠ WARN (Caution): {report.warning_count}")
        print(f"  ✗ FAIL (Too risky): {report.failed_count}")

        print("\n" + "-" * 90)
        print("PARAMETER ASSESSMENTS")
        print("-" * 90)

        for param_name, result in sorted(report.results.items()):
            status_icon = (
                "✓"
                if result.production_readiness == ProductionReadiness.PASS
                else "⚠" if result.production_readiness == ProductionReadiness.WARN else "✗"
            )

            print(
                f"\n{status_icon} {param_name:25s} | "
                f"Score: {result.overall_robustness_score:6.1f}/100 | "
                f"{result.production_readiness.value:4s} | "
                f"Risk: {result.risk_level.value:8s}"
            )

            if result.score_details:
                details = result.score_details
                print("  Breakdown:")
                print(
                    f"    - Consistency: {details.consistency_score:6.1f} " "(% windows profitable)"
                )
                print(
                    f"    - Stability:   {details.stability_score:6.1f} " f"(parameter consistency)"
                )
                print(
                    f"    - Sensitivity: {details.sensitivity_score:6.1f} "
                    "(robustness to changes)"
                )
                print(f"    - Overfitting: {details.overfitting_penalty:6.1f} (IS/OOS gap)")
                print(
                    f"    - Regime Robust: {details.regime_robustness_score:6.1f} " "(cross-regime)"
                )

            if result.risk_factors:
                print("  Risk Factors:")
                for factor in result.risk_factors:
                    print(f"    [{factor.severity.value}] {factor.name}: {factor.description}")

            if result.recommendations:
                print("  Recommendations:")
                for rec in result.recommendations:
                    print(f"    {rec}")

        print("\n" + "=" * 90)
