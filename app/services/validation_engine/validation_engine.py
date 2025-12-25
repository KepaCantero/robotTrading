"""
T5.1: ValidationEngine - Validation orchestration

Integrates PHASE 0 validators (CapitalViability, ExpensiveModuleGate, LearningCapitalGate)
and orchestrates comprehensive validation of parametrized strategies.

Validates:
1. Capital viability (profit goals achievable)
2. Module viability (expensive modules gated by capital)
3. Learning viability (learning infrastructure economically justified)
4. Feasibility ratio (backtest metrics meet targets)
5. Risk metrics (Sharpe, drawdown within acceptable ranges)
"""

import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional
from .models import (
    ValidationRequest,
    ValidationResult,
    CapitalViabilityAnalysis,
    LearningViabilityAnalysis,
    FeasibilityAnalysis,
    ModuleViabilityAnalysis,
)

logger = logging.getLogger(__name__)


class ValidationEngine:
    """
    Orchestrates comprehensive validation of parametrized trading strategies.

    Integrates PHASE 0 validators and applies additional constraints specific to
    the parametrization framework.
    """

    def __init__(self):
        """Initialize validation engine."""
        self.validation_history: List[ValidationResult] = []
        # Lazy-load validators
        self._capital_viability_validator = None
        self._expensive_module_gate = None
        self._learning_capital_gate = None
        logger.info("✅ ValidationEngine initialized")

    def _get_capital_viability_validator(self):
        """Lazy-load CapitalViabilityValidator."""
        if self._capital_viability_validator is None:
            try:
                from app.services.capital_viability_gate import CapitalViabilityValidator
                self._capital_viability_validator = CapitalViabilityValidator
                logger.debug("✅ CapitalViabilityValidator loaded")
            except ImportError as e:
                logger.error(f"❌ Failed to load CapitalViabilityValidator: {e}")
                raise
        return self._capital_viability_validator

    def _get_expensive_module_gate(self):
        """Lazy-load ExpensiveModuleGate."""
        if self._expensive_module_gate is None:
            try:
                from app.services.expensive_module_gate import ExpensiveModuleGate
                self._expensive_module_gate = ExpensiveModuleGate
                logger.debug("✅ ExpensiveModuleGate loaded")
            except ImportError as e:
                logger.error(f"❌ Failed to load ExpensiveModuleGate: {e}")
                raise
        return self._expensive_module_gate

    def _get_learning_capital_gate(self):
        """Lazy-load LearningCapitalGate."""
        if self._learning_capital_gate is None:
            try:
                from app.services.learning_capital_gate import LearningCapitalGate
                self._learning_capital_gate = LearningCapitalGate
                logger.debug("✅ LearningCapitalGate loaded")
            except ImportError as e:
                logger.error(f"❌ Failed to load LearningCapitalGate: {e}")
                raise
        return self._learning_capital_gate

    async def validate(self, request: ValidationRequest) -> ValidationResult:
        """
        Orchestrate comprehensive validation of a strategy.

        Args:
            request: ValidationRequest with profile and strategy parameters

        Returns:
            ValidationResult with all validation details
        """
        start_time = datetime.utcnow()

        try:
            # Initialize result
            result = ValidationResult(
                success=True,
                profile_id=request.profile_id,
            )

            # Step 1: Validate capital viability
            capital_viability = self._validate_capital_viability(request)
            result.capital_viability = capital_viability

            if not capital_viability.is_viable:
                result.critical_failures.append(
                    f"Capital viability: {capital_viability.reason}"
                )
                logger.warning(f"❌ Capital viability check failed for {request.profile_id}")

            # Step 2: Validate feasibility ratio (if backtest data provided)
            if request.backtest_feasibility_ratio is not None:
                feasibility = self._validate_feasibility_ratio(
                    request.backtest_feasibility_ratio,
                    request.target_monthly_return_eur,
                )
                result.feasibility = feasibility

                if not feasibility.is_viable and request.backtest_feasibility_ratio < Decimal("0.7"):
                    result.critical_failures.append(
                        f"Feasibility: {feasibility.reason}"
                    )
                    logger.warning(f"❌ Feasibility check failed for {request.profile_id}")
                elif not feasibility.is_viable:
                    result.warnings.append(
                        f"Feasibility: {feasibility.reason}"
                    )

            # Step 3: Validate learning viability
            learning_viability = self._validate_learning_viability(request)
            result.learning_viability = learning_viability

            if not learning_viability.learning_recommended and request.learning_enabled:
                result.warnings.append(
                    f"Learning not recommended: {learning_viability.reason}"
                )
                logger.warning(f"⚠️  Learning viability warning for {request.profile_id}")

            # Step 4: Validate module viability (expensive modules)
            module_viabilities = self._validate_module_viability(request)
            result.module_viabilities = module_viabilities

            expensive_modules_disabled = [
                name for name, analysis in module_viabilities.items()
                if not analysis.enabled
            ]
            if expensive_modules_disabled:
                result.warnings.append(
                    f"Expensive modules disabled: {', '.join(expensive_modules_disabled)}"
                )

            # Step 5: Validate risk metrics (if provided)
            if request.backtest_sharpe_ratio is not None:
                risk_warnings = self._validate_risk_metrics(request)
                result.warnings.extend(risk_warnings)

            # Step 6: Determine overall status
            self._determine_overall_status(result, request)

            # Store in history
            self.validation_history.append(result)

            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                f"✅ Validation completed for {request.profile_id}: "
                f"passed={result.passed}, recommendation={result.overall_recommendation}, "
                f"elapsed={elapsed_ms:.0f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Error validating request: {e}")
            return ValidationResult(
                success=False,
                profile_id=request.profile_id,
                error_message=str(e),
            )

    def _validate_capital_viability(
        self,
        request: ValidationRequest,
    ) -> CapitalViabilityAnalysis:
        """Validate capital viability using PHASE 0 validator."""
        try:
            validator = self._get_capital_viability_validator()

            result = validator.validate_profit_goal(
                capital=request.initial_capital,
                monthly_goal=request.target_monthly_return_eur,
                tax_rate=request.tax_rate,
                commission_per_trade=request.commission_per_trade,
                expected_trades_per_month=request.expected_trades_per_month,
            )

            return CapitalViabilityAnalysis(
                is_viable=result["is_viable"],
                required_alpha_pct=result.get("required_alpha_pct", Decimal("0")),
                expected_alpha_pct=result.get("expected_alpha_pct", Decimal("0")),
                reason=result["reason"],
                recommendation=result["recommendation"],
                severity=result["severity"],
            )

        except Exception as e:
            logger.error(f"❌ Error validating capital viability: {e}")
            return CapitalViabilityAnalysis(
                is_viable=False,
                required_alpha_pct=Decimal("0"),
                expected_alpha_pct=Decimal("0"),
                reason=f"Validation error: {str(e)}",
                recommendation="REVIEW_REQUIRED",
                severity="CRITICAL",
            )

    def _validate_feasibility_ratio(
        self,
        feasibility_ratio: Decimal,
        target_monthly_return: Decimal,
    ) -> FeasibilityAnalysis:
        """Validate feasibility ratio."""
        if feasibility_ratio >= Decimal("1.0"):
            status = "APPROVED"
            is_viable = True
            reason = f"Feasibility ratio {feasibility_ratio:.2f} meets target (≥1.0)"
        elif feasibility_ratio >= Decimal("0.7"):
            status = "CONDITIONAL"
            is_viable = True
            reason = f"Feasibility ratio {feasibility_ratio:.2f} is conditional (0.7-1.0)"
        else:
            status = "REJECTED"
            is_viable = False
            reason = f"Feasibility ratio {feasibility_ratio:.2f} below threshold (<0.7)"

        return FeasibilityAnalysis(
            feasibility_ratio=feasibility_ratio,
            feasibility_status=status,
            is_viable=is_viable,
            reason=reason,
        )

    def _validate_learning_viability(
        self,
        request: ValidationRequest,
    ) -> LearningViabilityAnalysis:
        """Validate learning viability using PHASE 0 validator."""
        try:
            gate = self._get_learning_capital_gate()

            # Estimate expected alpha from target monthly return
            expected_alpha = request.target_monthly_return_eur

            learning_viable, analysis = gate.is_learning_viable(
                capital=request.initial_capital,
                expected_monthly_alpha=expected_alpha,
                learning_enabled=request.learning_enabled,
            )

            return LearningViabilityAnalysis(
                learning_recommended=learning_viable,
                reason=analysis["reason"],
                recommendation=analysis["recommendation"],
                severity=analysis["severity"],
                capital_tier=analysis["capital_tier"],
                learning_cost_monthly=analysis["learning_cost_monthly"],
                cost_benefit_ratio=analysis["cost_benefit_ratio"],
            )

        except Exception as e:
            logger.error(f"❌ Error validating learning viability: {e}")
            return LearningViabilityAnalysis(
                learning_recommended=False,
                reason=f"Validation error: {str(e)}",
                recommendation="REVIEW_REQUIRED",
                severity="WARNING",
                capital_tier="unknown",
                learning_cost_monthly=Decimal("0"),
                cost_benefit_ratio=Decimal("0"),
            )

    def _validate_module_viability(
        self,
        request: ValidationRequest,
    ) -> Dict[str, ModuleViabilityAnalysis]:
        """Validate expensive module viability using PHASE 0 gate."""
        try:
            gate = self._get_expensive_module_gate()

            expensive_modules = [
                "transformer_engine",
                "deep_learning_engine",
                "reinforcement_learning_engine",
                "multitask_learning_engine",
                "transfer_learning",
                "hyperparameter_optimizer",
                "feature_importance_analysis",
            ]

            module_viabilities = {}

            for module_name in expensive_modules:
                should_enable, analysis = gate.should_enable_module(
                    module_name=module_name,
                    capital=request.initial_capital,
                )

                module_viabilities[module_name] = ModuleViabilityAnalysis(
                    module_name=module_name,
                    enabled=should_enable,
                    reason=analysis.get("reason", ""),
                    recommendation=analysis.get("recommendation", ""),
                    cost_monthly=analysis.get("cost_estimate_monthly"),
                    cost_ratio=analysis.get("cost_ratio"),
                )

            return module_viabilities

        except Exception as e:
            logger.error(f"❌ Error validating module viability: {e}")
            return {}

    def _validate_risk_metrics(self, request: ValidationRequest) -> List[str]:
        """Validate risk metrics from backtest."""
        warnings = []

        # Validate Sharpe ratio
        if request.backtest_sharpe_ratio is not None:
            if request.backtest_sharpe_ratio < Decimal("1.0"):
                warnings.append(
                    f"⚠️  Low Sharpe ratio ({request.backtest_sharpe_ratio:.2f}) - "
                    f"consider adjusting parameters"
                )

        # Validate max drawdown
        if request.backtest_max_drawdown_pct is not None:
            if request.backtest_max_drawdown_pct > Decimal("20"):
                warnings.append(
                    f"⚠️  High max drawdown ({request.backtest_max_drawdown_pct:.2f}%) - "
                    f"consider adding risk management"
                )

        return warnings

    def _determine_overall_status(
        self,
        result: ValidationResult,
        request: ValidationRequest,
    ) -> None:
        """Determine overall validation status and recommendation."""
        # If there are critical failures, validation fails
        if result.critical_failures:
            result.passed = False
            result.overall_recommendation = "REJECT"
            result.confidence_level = "high"
            return

        # Check feasibility status
        if result.feasibility:
            if result.feasibility.feasibility_status == "REJECTED":
                result.passed = False
                result.overall_recommendation = "REJECT"
                result.confidence_level = "high"
                return
            elif result.feasibility.feasibility_status == "CONDITIONAL":
                result.passed = True
                result.overall_recommendation = "CONDITIONAL"
                result.confidence_level = "medium"
            else:
                result.passed = True
                result.overall_recommendation = "APPROVE"
                result.confidence_level = "high"
        else:
            # No feasibility data - default to conditional
            result.passed = True
            result.overall_recommendation = "CONDITIONAL"
            result.confidence_level = "medium"

        # Adjust based on warnings
        if len(result.warnings) >= 3:
            result.confidence_level = "low"
            if result.overall_recommendation == "APPROVE":
                result.overall_recommendation = "CONDITIONAL"

    async def get_validation_history(
        self,
        limit: Optional[int] = None,
    ) -> List[ValidationResult]:
        """Get validation history."""
        results = self.validation_history
        if limit:
            results = results[-limit:]
        return results

    def get_validation_engine_status(self) -> Dict:
        """Get validation engine operational status."""
        passed = sum(1 for r in self.validation_history if r.passed)
        total = len(self.validation_history)

        return {
            "total_validations": total,
            "passed_validations": passed,
            "validation_pass_rate": passed / max(1, total),
            "history_size": total,
        }


# Singleton
_engine: Optional[ValidationEngine] = None


def get_validation_engine() -> ValidationEngine:
    """Get or create singleton ValidationEngine."""
    global _engine
    if _engine is None:
        _engine = ValidationEngine()
    return _engine
