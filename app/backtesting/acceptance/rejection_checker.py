"""
Rejection Criteria Checker Service.

Checks rejection criteria for strategy acceptance.
Follows Single Responsibility Principle (SOL-001).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.backtesting.acceptance.models import CriterionResult


@dataclass
class RejectionCriteriaChecker:
    """
    Checks rejection criteria for strategy acceptance.

    Rejection criteria:
    - Commission Impact <= 20% of gross profit
    - Failed Market Regimes <= 2
    - Equity Curve Trend (Last 2 Years) > 0
    """

    MAX_COMMISSION_IMPACT: float = 0.20
    MAX_FAILED_REGIMES: int = 2
    NEGATIVE_EQUITY_YEARS_THRESHOLD: int = 2

    def check_commission_impact(self, commission_impact: float | None) -> CriterionResult | None:
        """
        Check commission impact criterion.

        Args:
            commission_impact: Commissions as % of gross profit

        Returns:
            CriterionResult if commission_impact is not None, else None
        """
        if commission_impact is None:
            return None

        passed = commission_impact <= self.MAX_COMMISSION_IMPACT

        return CriterionResult(
            name="Commission Impact",
            passed=passed,
            value=commission_impact,
            threshold=self.MAX_COMMISSION_IMPACT,
            description=f"Commissions must be < {self.MAX_COMMISSION_IMPACT * 100}% of gross profit",
        )

    def check_failed_regimes(self, failed_regimes: int | None) -> CriterionResult | None:
        """
        Check failed market regimes criterion.

        Args:
            failed_regimes: Number of market regimes where strategy failed

        Returns:
            CriterionResult if failed_regimes is not None, else None
        """
        if failed_regimes is None:
            return None

        passed = failed_regimes <= self.MAX_FAILED_REGIMES

        return CriterionResult(
            name="Failed Market Regimes",
            passed=passed,
            value=failed_regimes,
            threshold=self.MAX_FAILED_REGIMES,
            description=f"Must not fail in > {self.MAX_FAILED_REGIMES} market regimes",
        )

    def check_equity_curve_trend(
        self, equity_curve_last_years: list[float] | None
    ) -> CriterionResult | None:
        """
        Check equity curve trend criterion.

        Args:
            equity_curve_last_years: Equity values for last 2 years

        Returns:
            CriterionResult if equity_curve has enough data, else None
        """
        if (
            not equity_curve_last_years
            or len(equity_curve_last_years) < self.NEGATIVE_EQUITY_YEARS_THRESHOLD
        ):
            return None

        # Compare end to start
        equity_change = equity_curve_last_years[-1] - equity_curve_last_years[0]
        passed = equity_change > 0

        return CriterionResult(
            name="Equity Curve Trend (Last 2 Years)",
            passed=passed,
            value=equity_change,
            threshold=0.0,
            description="Equity curve must be positive in last 2 years",
        )

    def check_all(
        self,
        commission_impact: float | None = None,
        failed_regimes: int | None = None,
        equity_curve_last_years: list[float] | None = None,
    ) -> list[CriterionResult]:
        """
        Check all rejection criteria.

        Args:
            commission_impact: Commissions as % of gross profit
            failed_regimes: Number of failed market regimes
            equity_curve_last_years: Equity values for last 2 years

        Returns:
            List of CriterionResult (only non-None results)
        """
        results: list[CriterionResult] = []

        commission_result = self.check_commission_impact(commission_impact)
        if commission_result:
            results.append(commission_result)

        regime_result = self.check_failed_regimes(failed_regimes)
        if regime_result:
            results.append(regime_result)

        equity_result = self.check_equity_curve_trend(equity_curve_last_years)
        if equity_result:
            results.append(equity_result)

        return results
