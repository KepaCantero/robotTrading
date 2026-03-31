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

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.backtesting.acceptance import (
    BenchmarkComparisonValidator,
    DrawdownValidator,
    MonteCarloValidator,
    ProfitFactorValidator,
    RejectionCriteriaChecker,
    ScoringService,
    SharpeValidator,
    VerdictDeterminer,
)

# Import models for backward compatibility (they're now in acceptance/models.py)
from app.backtesting.acceptance.models import AcceptanceReport, CriterionResult, VerdictStatus
from app.backtesting.models import BacktestResult

logger = logging.getLogger(__name__)

# Re-export models for backward compatibility
__all__ = [
    "AcceptanceCriteria",
    "AcceptanceReport",
    "CriterionResult",
    "VerdictStatus",
]


class AcceptanceCriteria:
    """
    Acceptance Criteria Validator (Req #17).

    Validates strategy viability based on institutional standards.
    Uses service layer pattern for Single Responsibility Principle (SOL-001).
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

    def __init__(
        self,
        min_sharpe: float = MIN_SHARPE_OOS,
        max_drawdown: float = MAX_MAX_DRAWDOWN,
        min_profit_factor: float = MIN_PROFIT_FACTOR,
        min_monte_carlo_p5: float = MIN_MONTE_CARLO_P5,
        min_excess_return: float = MIN_EXCESS_RETURN_VS_BENCHMARK,
        # Injected validator services (for testing/customization)
        sharpe_validator: Optional[SharpeValidator] = None,
        drawdown_validator: Optional[DrawdownValidator] = None,
        profit_factor_validator: Optional[ProfitFactorValidator] = None,
        monte_carlo_validator: Optional[MonteCarloValidator] = None,
        benchmark_validator: Optional[BenchmarkComparisonValidator] = None,
        rejection_checker: Optional[RejectionCriteriaChecker] = None,
        scoring_service: Optional[ScoringService] = None,
        verdict_determiner: Optional[VerdictDeterminer] = None,
    ):
        """Initialize acceptance criteria with custom thresholds and validators."""
        # Store thresholds for backward compatibility
        self.min_sharpe = min_sharpe
        self.max_drawdown = max_drawdown
        self.min_profit_factor = min_profit_factor
        self.min_monte_carlo_p5 = min_monte_carlo_p5
        self.min_excess_return = min_excess_return

        # Initialize validator services (dependency injection with defaults)
        self._sharpe_validator = sharpe_validator or SharpeValidator(min_sharpe=min_sharpe)
        self._drawdown_validator = drawdown_validator or DrawdownValidator(
            max_drawdown_threshold=max_drawdown
        )
        self._profit_factor_validator = profit_factor_validator or ProfitFactorValidator(
            min_profit_factor=min_profit_factor
        )
        self._monte_carlo_validator = monte_carlo_validator or MonteCarloValidator(
            min_monte_carlo_p5=min_monte_carlo_p5
        )
        self._benchmark_validator = benchmark_validator or BenchmarkComparisonValidator(
            min_excess_return=min_excess_return
        )
        self._rejection_checker = rejection_checker or RejectionCriteriaChecker()
        self._scoring_service = scoring_service or ScoringService()
        self._verdict_determiner = verdict_determiner or VerdictDeterminer()

    def validate_strategy(
        self,
        backtest_result: BacktestResult,
        benchmark_return: float,
        monte_carlo_p5_return: Optional[float] = None,
        commission_impact: Optional[float] = None,
        failed_regimes: Optional[int] = None,
        equity_curve_last_years: Optional[list[float]] = None,
    ) -> AcceptanceReport:
        """
        Validate strategy against all acceptance criteria (Req #17).

        Delegates validation to specialized validator services (SOL-001).

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
        strategy_name = backtest_result.strategy_name or "unknown"
        perf = backtest_result.performance

        if not perf:
            logger.error(
                "Cannot validate strategy: performance data is None",
                extra={"strategy": strategy_name},
            )
            return self._create_invalid_report(strategy_name)

        # Extract metrics
        metrics = self._extract_metrics(backtest_result, perf)
        # Validate all criteria
        validation = self._perform_validation(
            metrics,
            benchmark_return,
            monte_carlo_p5_return,
            commission_impact,
            failed_regimes,
            equity_curve_last_years,
        )
        # Log and return report
        self._log_validation(strategy_name, validation)
        return self._create_report(backtest_result, validation)

    def _extract_metrics(self, backtest_result: BacktestResult, perf) -> dict:
        """Extract metrics from backtest result."""
        return {
            "sharpe": float(perf.sharpe_ratio or 0),
            "max_dd": float(perf.max_drawdown_percentage or 0),
            "profit_factor": float(perf.profit_factor or 0),
            "strategy_return": float(backtest_result.total_return),
        }

    def _perform_validation(
        self,
        metrics: dict,
        benchmark_return: float,
        monte_carlo_p5_return: Optional[float],
        commission_impact: Optional[float],
        failed_regimes: Optional[int],
        equity_curve_last_years: Optional[list[float]],
    ) -> dict:
        """Perform all validation steps."""
        criteria_results = self._validate_basic_criteria(
            metrics["sharpe"],
            metrics["max_dd"],
            metrics["profit_factor"],
            monte_carlo_p5_return,
            metrics["strategy_return"],
            benchmark_return,
        )
        rejection_results = self._rejection_checker.check_all(
            commission_impact=commission_impact,
            failed_regimes=failed_regimes,
            equity_curve_last_years=equity_curve_last_years,
        )
        score = self._scoring_service.calculate_score(criteria_results)
        verdict, warnings, recommendations = self._verdict_determiner.determine_verdict(
            criteria_results, rejection_results, score
        )
        excess_return = self._benchmark_validator.get_excess_return(
            metrics["strategy_return"], benchmark_return
        )
        return {
            "criteria_results": criteria_results,
            "rejection_results": rejection_results,
            "score": score,
            "verdict": verdict,
            "warnings": warnings,
            "recommendations": recommendations,
            "excess_return": excess_return,
        }

    def _log_validation(self, strategy_name: str, validation: dict) -> None:
        """Log validation results."""
        logger.info(
            "Strategy acceptance validation completed",
            extra={
                "strategy": strategy_name,
                "verdict": validation["verdict"].value,
                "score": validation["score"],
            },
        )

    def _create_report(self, backtest_result: BacktestResult, validation: dict) -> AcceptanceReport:
        """Create acceptance report from validation results."""
        perf = backtest_result.performance
        return AcceptanceReport(
            strategy_name=backtest_result.strategy_name or "unknown",
            timestamp=datetime.now(),
            verdict=validation["verdict"],
            overall_score=validation["score"],
            basic_criteria=validation["criteria_results"],
            advanced_criteria=[],
            rejection_criteria=validation["rejection_results"],
            beats_benchmark=validation["excess_return"] >= self.min_excess_return,
            excess_return=validation["excess_return"],
            warnings=validation["warnings"],
            recommendations=validation["recommendations"],
            sharpe_ratio=float(perf.sharpe_ratio or 0) if perf else None,
            max_drawdown=float(perf.max_drawdown_percentage or 0) if perf else None,
            profit_factor=float(perf.profit_factor or 0) if perf else None,
        )

    def _validate_basic_criteria(
        self,
        sharpe: float,
        max_dd: float,
        profit_factor: float,
        monte_carlo_p5_return: Optional[float],
        strategy_return: float,
        benchmark_return: float,
    ) -> list[CriterionResult]:
        """
        Validate all basic criteria using validator services.

        Args:
            sharpe: Sharpe Ratio value
            max_dd: Maximum drawdown value
            profit_factor: Profit Factor value
            monte_carlo_p5_return: Monte Carlo P5 return value
            strategy_return: Strategy total return
            benchmark_return: Benchmark total return

        Returns:
            List of CriterionResult for all basic criteria
        """
        results: list[CriterionResult] = []

        # Validate Sharpe Ratio
        results.append(self._sharpe_validator.validate(sharpe))

        # Validate Max Drawdown
        results.append(self._drawdown_validator.validate(max_dd))

        # Validate Profit Factor
        results.append(self._profit_factor_validator.validate(profit_factor))

        # Validate Monte Carlo P5
        results.append(self._monte_carlo_validator.validate(monte_carlo_p5_return))

        # Validate Benchmark Comparison
        results.append(self._benchmark_validator.validate(strategy_return, benchmark_return))

        return results

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
