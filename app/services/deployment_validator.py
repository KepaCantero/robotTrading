"""
PHASE 0 - Deployment Validator (T0.4)

Orchestrates all capital gates before live deployment. Ensures that accounts
meet minimum safety standards across all dimensions (capital viability, execution
cost, learning viability, and module expense) before any live trading.

The deployment validator combines:
1. Capital viability gate: Can the account sustain the profit goal?
2. Execution cost analyzer: Are execution costs reasonable?
3. Learning capital gate: Is learning infrastructure economically justified?
4. Expensive module gate: Are expensive ML modules justified by account size?
5. Safety checklist: Are all pre-deployment checks satisfied?
6. Deployment gates: Final authorization before going live

Economics principle: Fail-fast by default. Better to reject trading on underfunded
accounts than to slowly bleed capital on infrastructure costs that exceed returns.
"""

import logging
from decimal import Decimal
from enum import Enum
from typing import Optional

from app.services.capital_viability_gate import CapitalViabilityValidator
from app.services.execution_cost_analyzer import ExecutionCostAnalyzer
from app.services.expensive_module_gate import ExpensiveModuleGate
from app.services.learning_capital_gate import LearningCapitalGate

logger = logging.getLogger(__name__)


class DeploymentStatus(str, Enum):
    """Status of deployment validation"""

    APPROVED = "approved"  # All gates passed - safe to deploy
    RESTRICTED = "restricted"  # Partial gates passed - deploy with restrictions
    REJECTED = "rejected"  # Critical gates failed - do not deploy
    REVIEW_REQUIRED = "review_required"  # Manual review needed


class DeploymentValidator:
    """
    Validates accounts against all capital gates before live deployment.

    Orchestrates a multi-gate check that ensures trading will not erode capital
    through combinations of:
    - Unreachable profit goals
    - Excessive execution costs
    - Unjustified learning infrastructure
    - Expensive ML modules on undersized accounts
    """

    @staticmethod
    def validate_for_deployment(
        capital: Decimal,
        monthly_profit_goal: Decimal,
        expected_monthly_alpha: Decimal,
        tax_rate: Optional[Decimal] = None,
        commission_per_trade: Optional[Decimal] = None,
        expected_trades_per_month: int = 10,
        learning_enabled: bool = True,
        expensive_modules_enabled: bool = True,
        account_id: Optional[str] = None,
    ) -> tuple[DeploymentStatus, dict]:
        """
        Run all capital gates to determine if account is safe for live deployment.

        Args:
            capital: Account capital in dollars
            monthly_profit_goal: Target monthly profit
            expected_monthly_alpha: Expected alpha from strategy
            tax_rate: Tax rate on profits (default 40%)
            commission_per_trade: Commission per trade in dollars
            expected_trades_per_month: Expected monthly trades
            learning_enabled: Whether learning is configured
            expensive_modules_enabled: Whether expensive modules are enabled
            account_id: Account identifier for logging

        Returns:
            (status: DeploymentStatus, analysis: Dict)

        Analysis dict contains:
            - status: Overall deployment status
            - gates: Dict of individual gate results
            - issues: List of critical issues blocking deployment
            - warnings: List of warning-level issues
            - recommendations: List of recommended actions
            - account_id: Account identifier (if provided)
        """
        if tax_rate is None:
            tax_rate = Decimal("0.40")
        if commission_per_trade is None:
            commission_per_trade = Decimal("15")

        analysis = {
            "account_id": account_id,
            "capital": capital,
            "monthly_profit_goal": monthly_profit_goal,
            "expected_monthly_alpha": expected_monthly_alpha,
            "capital_tier": DeploymentValidator._get_capital_tier(capital),
            "gates": {},
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # ===== GATE 1: Capital Viability =====
        cap_analysis = CapitalViabilityValidator.validate_profit_goal(
            capital=capital,
            monthly_goal=monthly_profit_goal,
            tax_rate=tax_rate,
            commission_per_trade=commission_per_trade,
            expected_trades_per_month=expected_trades_per_month,
        )

        analysis["gates"]["capital_viability"] = {
            "passed": cap_analysis["is_viable"],
            "severity": cap_analysis["severity"],
            "reason": cap_analysis.get("summary", ""),
        }

        if cap_analysis["severity"] == "CRITICAL":
            analysis["issues"].append(
                f"Capital viability: Monthly goal ${monthly_profit_goal:.2f} is unrealistic for ${capital:,.0f} capital. "
                "Severity: CRITICAL"
            )
        elif cap_analysis["severity"] == "WARNING":
            analysis["warnings"].append(
                f"Capital viability: Monthly goal ${monthly_profit_goal:.2f} is challenging for ${capital:,.0f} capital. "
                "Consider reducing goal or increasing capital."
            )

        # ===== GATE 2: Execution Cost Analysis =====
        # Estimate typical trade for cost analysis
        analyzer = ExecutionCostAnalyzer(commission_per_trade=commission_per_trade)

        # Estimate position size based on capital
        typical_position_size = capital * Decimal("0.1")  # 10% position
        typical_alpha_per_trade = expected_monthly_alpha / Decimal(expected_trades_per_month)

        should_execute, exec_analysis = analyzer.should_execute_trade(
            position_size=typical_position_size,
            expected_alpha=typical_alpha_per_trade,
            volatility_percentile=50,  # Assume normal volatility
            num_concurrent_trades=1,
        )

        analysis["gates"]["execution_cost"] = {
            "passed": should_execute,
            "estimated_cost_per_trade": exec_analysis.get("cost_estimate"),
            "cost_ratio": exec_analysis.get("cost_ratio"),
        }

        if not should_execute:
            analysis["issues"].append(
                f"Execution cost: Estimated trade cost ${exec_analysis.get('cost_estimate', 0):.2f} "
                f"exceeds acceptable threshold. Cost ratio: {exec_analysis.get('cost_ratio', 0):.0%}"
            )

        # ===== GATE 3: Learning Capital Gate =====
        learning_viable, learning_analysis = LearningCapitalGate.is_learning_viable(
            capital=capital,
            expected_monthly_alpha=expected_monthly_alpha,
            learning_enabled=learning_enabled,
        )

        analysis["gates"]["learning_capital"] = {
            "passed": learning_viable,
            "learning_recommended": learning_analysis["learning_recommended"],
            "learning_cost_monthly": learning_analysis["learning_cost_monthly"],
            "cost_benefit_ratio": learning_analysis["cost_benefit_ratio"],
        }

        if not learning_viable and learning_enabled:
            analysis["warnings"].append(
                f"Learning capital gate: Learning infrastructure cost ${learning_analysis['learning_cost_monthly']:.2f}/mo "
                f"({learning_analysis['cost_benefit_ratio']:.0%} of alpha) exceeds threshold. "
                "Consider disabling learning."
            )

        # ===== GATE 4: Expensive Module Gate =====
        modules_enabled, _modules_analysis = ExpensiveModuleGate.get_enabled_modules(
            capital=capital,
            expected_monthly_alpha=expected_monthly_alpha,
        )

        total_module_cost = ExpensiveModuleGate.get_total_expensive_module_cost(
            capital, modules_enabled
        )
        cost_summary = ExpensiveModuleGate.get_cost_summary(
            capital, modules_enabled, expected_monthly_alpha
        )

        analysis["gates"]["expensive_modules"] = {
            "passed": cost_summary["recommendation"] != "COST_CRITICAL",
            "enabled_module_count": cost_summary["enabled_module_count"],
            "total_module_count": cost_summary["total_module_count"],
            "total_cost_monthly": total_module_cost,
            "cost_ratio": cost_summary["cost_ratio_of_alpha"],
            "recommendation": cost_summary["recommendation"],
        }

        if cost_summary["recommendation"] == "COST_CRITICAL":
            analysis["issues"].append(
                f"Expensive modules: Total module cost ${total_module_cost:.2f}/mo "
                f"({cost_summary['cost_ratio_of_alpha']:.0%} of alpha) is critical. "
                "Disable expensive modules or increase capital."
            )
        elif cost_summary["recommendation"] == "COST_HIGH":
            analysis["warnings"].append(
                f"Expensive modules: Total module cost ${total_module_cost:.2f}/mo "
                f"({cost_summary['cost_ratio_of_alpha']:.0%} of alpha) is high. "
                "Consider disabling some modules."
            )

        # ===== Determine Overall Status =====
        if len(analysis["issues"]) > 0:
            status = DeploymentStatus.REJECTED
        elif len(analysis["warnings"]) > 2:
            status = DeploymentStatus.REVIEW_REQUIRED
        elif len(analysis["warnings"]) > 0:
            status = DeploymentStatus.RESTRICTED
        else:
            status = DeploymentStatus.APPROVED

        analysis["status"] = status.value

        # ===== Generate Recommendations =====
        if status == DeploymentStatus.REJECTED:
            if capital < Decimal("15000"):
                analysis["recommendations"].append(
                    "Increase capital to at least $15,000 for micro-tier account support"
                )
            if capital < Decimal("25000") and learning_enabled:
                analysis["recommendations"].append(
                    "Disable learning infrastructure until capital reaches $25,000+"
                )
            if capital < Decimal("50000") and expensive_modules_enabled:
                analysis["recommendations"].append(
                    "Disable expensive ML modules until capital reaches $50,000+"
                )

        elif status == DeploymentStatus.RESTRICTED:
            analysis["recommendations"].append(
                "Deploy with monitoring enabled and reduced position sizes"
            )
            analysis["recommendations"].append(f"Use {analysis['capital_tier']} tier configuration")

        # ===== Log Decision =====
        DeploymentValidator._log_deployment_decision(analysis, status)

        return status, analysis

    @staticmethod
    def _get_capital_tier(capital: Decimal) -> str:
        """Classify capital into tiers"""
        if capital < Decimal("15000"):
            return "micro"
        elif capital < Decimal("50000"):
            return "small"
        elif capital < Decimal("250000"):
            return "medium"
        else:
            return "large"

    @staticmethod
    def _log_deployment_decision(analysis: dict, status: DeploymentStatus) -> None:
        """Log deployment validation decision"""
        account_id = analysis.get("account_id", "UNKNOWN")
        capital = analysis.get("capital", Decimal("0"))

        log_msg = (
            f"[{account_id}] Deployment validation: {status.value.upper()} | "
            f"Capital: ${capital:,.0f} ({analysis.get('capital_tier', '?')}) | "
            f"Issues: {len(analysis.get('issues', []))} | "
            f"Warnings: {len(analysis.get('warnings', []))}"
        )

        if status == DeploymentStatus.APPROVED:
            logger.info(f"✅ {log_msg}")
        elif status == DeploymentStatus.RESTRICTED:
            logger.warning(f"⚠️  {log_msg}")
        elif status == DeploymentStatus.REVIEW_REQUIRED:
            logger.warning(f"🔍 {log_msg} - Manual review required")
        else:  # REJECTED
            logger.error(f"❌ {log_msg}")

        # Log detailed issues and warnings
        for issue in analysis.get("issues", []):
            logger.error(f"  ISSUE: {issue}")

        for warning in analysis.get("warnings", []):
            logger.warning(f"  WARNING: {warning}")

        for recommendation in analysis.get("recommendations", []):
            logger.info(f"  RECOMMENDATION: {recommendation}")

    @staticmethod
    def get_deployment_readiness_score(capital: Decimal) -> float:
        """
        Calculate a 0-100 readiness score for deployment.

        Based on:
        - Capital size relative to minimum thresholds
        - Infrastructure cost efficiency
        - Tier upgrade potential

        Returns:
            Score from 0-100 (0 = not ready, 100 = fully optimized)
        """
        if capital < Decimal("15000"):
            # Micro tier: only 20% ready
            return 20.0
        elif capital < Decimal("25000"):
            # Below learning threshold: 40% ready
            return 40.0
        elif capital < Decimal("50000"):
            # Small tier: 60% ready
            return 60.0
        elif capital < Decimal("100000"):
            # Medium-small: 80% ready
            return 80.0
        elif capital < Decimal("250000"):
            # Medium tier: 90% ready
            return 90.0
        else:
            # Large tier: fully ready
            return 100.0

    @staticmethod
    def get_minimum_capital_recommendation(
        monthly_profit_goal: Decimal,
        expected_monthly_alpha: Optional[Decimal] = None,
    ) -> dict[str, Decimal]:
        """
        Calculate minimum capital needed based on goals and infrastructure requirements.

        Returns:
            Dict with:
            - for_capital_viability: Capital needed for profit goal
            - for_learning: Capital needed for learning to be viable (min $25k)
            - for_expensive_modules: Capital needed for ML modules
            - recommended: Conservative recommendation
        """
        if expected_monthly_alpha is None:
            expected_monthly_alpha = Decimal("100")
        # For capital viability, estimate capital needed for goal
        # Assuming 3% monthly return on capital
        required_for_goal = monthly_profit_goal / Decimal("0.03")

        return {
            "for_capital_viability": max(required_for_goal, Decimal("10000")),
            "for_learning": LearningCapitalGate.MIN_CAPITAL_FOR_LEARNING,
            "for_expensive_modules": Decimal("50000"),  # Deep learning threshold
            "recommended": max(
                Decimal("25000"),  # Minimum for learning viability
                required_for_goal,  # Plus what's needed for goal
            ),
        }
