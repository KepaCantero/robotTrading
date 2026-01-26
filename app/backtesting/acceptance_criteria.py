"""
Acceptance Criteria Validator for Professional Backtesting (Req #17)

Implements automated validation of strategy viability based on:
- Sharpe Ratio > 1.0 (Out-of-Sample)
- Max Drawdown < 25%
- Profit Factor > 1.3
- Monte Carlo Percentile 5 > -20% DD
- Return > Benchmark + 3%

REJECTION CRITERIA:
- Commissions > 20% of gross profit
- Failure in > 2 market regimes
- Flat or negative equity curve in last 2 years
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from app.backtesting.models import BacktestResult

logger = logging.getLogger(__name__)


class VerdictStatus(str, Enum):
    """Strategy verdict status."""

    APPROVED = "APPROVED"
    REVISION = "REVISION"
    REJECTED = "REJECTED"


@dataclass
class CriterionResult:
    """Result of a single criterion check."""

    name: str
    passed: bool
    value: float
    threshold: float
    description: str


@dataclass
class AcceptanceReport:
    """Complete acceptance criteria report."""

    strategy_name: str
    timestamp: datetime
    verdict: VerdictStatus
    overall_score: float  # 0-100

    # Criterion results
    basic_criteria: List[CriterionResult] = field(default_factory=list)
    advanced_criteria: List[CriterionResult] = field(default_factory=list)
    rejection_criteria: List[CriterionResult] = field(default_factory=list)

    # Benchmark comparison
    beats_benchmark: bool = False
    excess_return: float = 0.0

    # Warnings and recommendations
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Detailed metrics
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    profit_factor: Optional[float] = None
    commission_impact: Optional[float] = None
    monte_carlo_p5: Optional[float] = None


class AcceptanceCriteria:
    """
    Acceptance Criteria Validator (Req #17).

    Validates strategy viability based on institutional standards.
    """

    # APPROVAL THRESHOLDS (Req #17)
    MIN_SHARPE_OOS = 1.0
    MAX_MAX_DRAWDOWN = -0.25  # -25%
    MIN_PROFIT_FACTOR = 1.3
    MIN_MONTE_CARLO_P5 = -0.20  # -20% DD
    MIN_EXCESS_RETURN_VS_BENCHMARK = 0.03  # +3%

    # REJECTION THRESHOLDS (Req #17)
    MAX_COMMISSION_IMPACT = 0.20  # 20% of gross profit
    MAX_FAILED_REGIMES = 2
    NEGATIVE_EQUIITY_YEARS_THRESHOLD = 2

    # SCORING WEIGHTS
    SHARPE_WEIGHT = 0.25
    DRAWDOWN_WEIGHT = 0.20
    PROFIT_FACTOR_WEIGHT = 0.20
    MONTE_CARLO_WEIGHT = 0.15
    BENCHMARK_WEIGHT = 0.20

    def __init__(
        self,
        min_sharpe: float = MIN_SHARPE_OOS,
        max_drawdown: float = MAX_MAX_DRAWDOWN,
        min_profit_factor: float = MIN_PROFIT_FACTOR,
        min_monte_carlo_p5: float = MIN_MONTE_CARLO_P5,
        min_excess_return: float = MIN_EXCESS_RETURN_VS_BENCHMARK,
    ):
        """Initialize acceptance criteria with custom thresholds."""
        self.min_sharpe = min_sharpe
        self.max_drawdown = max_drawdown
        self.min_profit_factor = min_profit_factor
        self.min_monte_carlo_p5 = min_monte_carlo_p5
        self.min_excess_return = min_excess_return

    def validate_strategy(
        self,
        backtest_result: BacktestResult,
        benchmark_return: float,
        monte_carlo_p5_return: Optional[float] = None,
        commission_impact: Optional[float] = None,
        failed_regimes: Optional[int] = None,
        equity_curve_last_years: Optional[List[float]] = None,
    ) -> AcceptanceReport:
        """
        Validate strategy against all acceptance criteria (Req #17).

        Args:
            backtest_result: Complete backtest result
            benchmark_return: Benchmark total return
            monte_carlo_p5_return: Monte Carlo 5th percentile return
            commission_impact: Commissions as % of gross profit
            failed_regimes: Number of market regimes where strategy failed
            equity_curve_last_years: Equity values for last 2 years

        Returns:
            AcceptanceReport with verdict and details
        """
        perf = backtest_result.performance
        if not perf:
            return self._create_invalid_report(backtest_result.strategy_name or "unknown")

        criteria_results = []
        rejection_results = []

        # Basic criteria (Req #17)
        sharpe = float(perf.sharpe_ratio or 0)
        max_dd = float(perf.max_drawdown_percentage or 0)
        profit_factor = float(perf.profit_factor or 0)

        sharpe_result = CriterionResult(
            name="Sharpe Ratio (OOS)",
            passed=sharpe >= self.min_sharpe,
            value=sharpe,
            threshold=self.min_sharpe,
            description=f"Sharpe Ratio must be > {self.min_sharpe}",
        )
        criteria_results.append(sharpe_result)

        dd_result = CriterionResult(
            name="Max Drawdown",
            passed=max_dd >= self.max_drawdown,  # Less negative is better
            value=max_dd,
            threshold=self.max_drawdown,
            description=f"Max Drawdown must be < {abs(self.max_drawdown) * 100}%",
        )
        criteria_results.append(dd_result)

        pf_result = CriterionResult(
            name="Profit Factor",
            passed=profit_factor >= self.min_profit_factor,
            value=profit_factor,
            threshold=self.min_profit_factor,
            description=f"Profit Factor must be > {self.min_profit_factor}",
        )
        criteria_results.append(pf_result)

        # Monte Carlo criterion (Req #17)
        mc_p5_result = CriterionResult(
            name="Monte Carlo P5 Return",
            passed=(monte_carlo_p5_return or 0) >= self.min_monte_carlo_p5,
            value=monte_carlo_p5_return or 0,
            threshold=self.min_monte_carlo_p5,
            description="Monte Carlo 5th percentile must be > -20%",
        )
        criteria_results.append(mc_p5_result)

        # Benchmark comparison (Req #17)
        strategy_return = float(backtest_result.total_return)
        excess_return = strategy_return - benchmark_return

        beats_benchmark_result = CriterionResult(
            name="Excess Return vs Benchmark",
            passed=excess_return >= self.min_excess_return,
            value=excess_return,
            threshold=self.min_excess_return,
            description=f"Must outperform benchmark by > {self.min_excess_return * 100}%",
        )
        criteria_results.append(beats_benchmark_result)

        # Rejection criteria (Req #17)
        if commission_impact is not None:
            commission_result = CriterionResult(
                name="Commission Impact",
                passed=commission_impact <= self.MAX_COMMISSION_IMPACT,
                value=commission_impact,
                threshold=self.MAX_COMMISSION_IMPACT,
                description=f"Commissions must be < {self.MAX_COMMISSION_IMPACT * 100}% of gross profit",
            )
            rejection_results.append(commission_result)

        if failed_regimes is not None:
            regime_result = CriterionResult(
                name="Failed Market Regimes",
                passed=failed_regimes <= self.MAX_FAILED_REGIMES,
                value=failed_regimes,
                threshold=self.MAX_FAILED_REGIMES,
                description=f"Must not fail in > {self.MAX_FAILED_REGIMES} market regimes",
            )
            rejection_results.append(regime_result)

        # Check for flat/negative equity curve in last 2 years
        equity_warning = False
        if equity_curve_last_years and len(equity_curve_last_years) >= 2:
            # Compare end to start
            equity_change = equity_curve_last_years[-1] - equity_curve_last_years[0]
            equity_warning = equity_change <= 0

        if equity_warning:
            equity_result = CriterionResult(
                name="Equity Curve Trend (Last 2 Years)",
                passed=not equity_warning,
                value=equity_curve_last_years[-1] - equity_curve_last_years[0],
                threshold=0,
                description="Equity curve must be positive in last 2 years",
            )
            rejection_results.append(equity_result)

        # Calculate overall score
        score = self._calculate_score(criteria_results)

        # Determine verdict
        verdict, warnings, recommendations = self._determine_verdict(
            criteria_results, rejection_results, score
        )

        return AcceptanceReport(
            strategy_name=backtest_result.strategy_name or "unknown",
            timestamp=datetime.now(),
            verdict=verdict,
            overall_score=score,
            basic_criteria=criteria_results,
            advanced_criteria=[],
            rejection_criteria=rejection_results,
            beats_benchmark=excess_return >= self.min_excess_return,
            excess_return=excess_return,
            warnings=warnings,
            recommendations=recommendations,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            profit_factor=profit_factor,
            commission_impact=commission_impact,
            monte_carlo_p5=monte_carlo_p5_return,
        )

    def _create_invalid_report(self, strategy_name: str) -> AcceptanceReport:
        """Create report for invalid backtest result."""
        return AcceptanceReport(
            strategy_name=strategy_name,
            timestamp=datetime.now(),
            verdict=VerdictStatus.REJECTED,
            overall_score=0.0,
            warnings=["Invalid backtest result - no performance data"],
            recommendations=["Run a valid backtest before evaluation"],
        )

    def _calculate_score(self, criteria: List[CriterionResult]) -> float:
        """Calculate overall score (0-100) based on criteria."""
        if not criteria:
            return 0.0

        score = 0.0

        for criterion in criteria:
            if criterion.passed:
                score += 20.0  # Each criterion is worth 20 points

        return min(100.0, score)

    def _determine_verdict(
        self,
        criteria: List[CriterionResult],
        rejection: List[CriterionResult],
        score: float,
    ) -> tuple[VerdictStatus, List[str], List[str]]:
        """Determine verdict based on criteria and rejection factors."""
        warnings = []
        recommendations = []

        # Check rejection criteria first (Req #17)
        rejected = False
        for crit in rejection:
            if not crit.passed:
                rejected = True
                warnings.append(f"REJECTED: {crit.description}")

        if rejected:
            return VerdictStatus.REJECTED, warnings, recommendations

        # Check if all basic criteria passed
        all_passed = all(c.passed for c in criteria)

        if all_passed:
            verdict = VerdictStatus.APPROVED
            recommendations.append("Strategy meets all acceptance criteria")
        elif score >= 60.0:
            verdict = VerdictStatus.REVISION
            warnings.append("Strategy partially meets criteria - review recommended")
            recommendations.extend([f"Improve {c.name}" for c in criteria if not c.passed])
        else:
            verdict = VerdictStatus.REJECTED
            warnings.append("Strategy fails too many criteria")
            recommendations.extend([f"Address {c.name}" for c in criteria if not c.passed])

        return verdict, warnings, recommendations

    def generate_summary_markdown(self, report: AcceptanceReport) -> str:
        """Generate markdown summary of acceptance report."""
        lines = [
            "# Acceptance Criteria Report",
            "",
            f"**Strategy:** {report.strategy_name}",
            f"**Date:** {report.timestamp.strftime('%Y-%m-%d %H:%M')}",
            f"**Verdict:** {self._format_verdict(report.verdict)}",
            f"**Overall Score:** {report.overall_score:.0f}/100",
            "",
        ]

        if report.sharpe_ratio is not None:
            lines.extend(
                [
                    "## Key Metrics",
                    "",
                    f"- **Sharpe Ratio:** {report.sharpe_ratio:.2f} (threshold: {self.min_sharpe})",
                    f"- **Max Drawdown:** {report.max_drawdown:.2%} (threshold: {abs(self.max_drawdown):.0%})",
                    f"- **Profit Factor:** {report.profit_factor:.2f} (threshold: {self.min_profit_factor})",
                    "",
                ]
            )

        lines.extend(
            [
                "## Criteria Results",
                "",
                "| Criterion | Passed | Value | Threshold |",
                "|-----------|--------|-------|----------|",
            ]
        )

        all_criteria = report.basic_criteria + report.advanced_criteria
        for crit in all_criteria:
            status = "✅" if crit.passed else "❌"
            lines.append(f"| {crit.name} | {status} | {crit.value:.2f} | {crit.threshold:.2f} |")

        if report.rejection_criteria:
            lines.extend(
                [
                    "",
                    "## Rejection Criteria",
                    "",
                ]
            )
            for crit in report.rejection_criteria:
                status = "✅" if crit.passed else "❌"
                lines.append(
                    f"- {status} **{crit.name}**: {crit.value:.2f} (threshold: {crit.threshold:.2f})"
                )

        if report.warnings:
            lines.extend(
                [
                    "",
                    "## Warnings",
                    "",
                ]
            )
            for warning in report.warnings:
                lines.append(f"- ⚠️ {warning}")

        if report.recommendations:
            lines.extend(
                [
                    "",
                    "## Recommendations",
                    "",
                ]
            )
            for rec in report.recommendations:
                lines.append(f"- {rec}")

        return "\n".join(lines)

    def _format_verdict(self, verdict: VerdictStatus) -> str:
        """Format verdict with emoji."""
        emoji = {
            VerdictStatus.APPROVED: "✅",
            VerdictStatus.REVISION: "⚠️",
            VerdictStatus.REJECTED: "❌",
        }
        return f"{emoji.get(verdict, '')} {verdict.value}"
