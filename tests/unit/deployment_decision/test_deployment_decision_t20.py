"""
T20.1: Deployment Decision Orchestrator Tests (Focused Suite)

Tests for DeploymentDecisionOrchestrator, DeploymentDecision, and DeploymentAnalysis.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from app.services.deployment_decision import (
    DeploymentDecisionOrchestrator,
    DeploymentDecision,
    DeploymentAnalysis,
    get_deployment_decision_orchestrator,
)


# DEPLOYMENT DECISION ORCHESTRATOR TESTS (65+ tests)
class TestDeploymentDecisionInitialization:
    def test_orchestrator_init(self):
        """Test orchestrator initialization."""
        orchestrator = DeploymentDecisionOrchestrator()
        assert len(orchestrator.decision_history) == 0
        assert len(orchestrator.decision_metrics) == 0

    def test_orchestrator_singleton(self):
        """Test orchestrator singleton pattern."""
        o1 = get_deployment_decision_orchestrator()
        o2 = get_deployment_decision_orchestrator()
        assert o1 is o2


class TestApprovedDecisions:
    @pytest.mark.asyncio
    async def test_full_approval_strong(self):
        """Test approval with all strong indicators."""
        orchestrator = DeploymentDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            # Validation: all passed
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],

            # Feasibility: strong
            feasibility_ratio=Decimal("1.35"),
            backtest_return=Decimal("0.15"),
            backtest_sharpe=Decimal("2.0"),
            backtest_max_drawdown=Decimal("-0.08"),

            # Recommendation: high confidence, strong score
            recommendation_score=Decimal("85"),
            recommendation_confidence="high",
            recommendation_alternatives=["Strategy_B", "Strategy_C"],

            # Portfolio: excellent quality
            portfolio_quality=Decimal("88"),
            portfolio_diversification_score=Decimal("85"),
            portfolio_concentration_risk=Decimal("15"),
            portfolio_num_assets=12,

            # Risk: compatible
            portfolio_risk_level="medium",
            estimated_max_loss=Decimal("-30000"),

            # User profile
            capital_tier="medium",
            objective="balanced_growth",
            risk_profile="moderate",
            target_monthly_return=Decimal("1000"),
            initial_capital=Decimal("250000")
        )

        assert decision.decision_status == "APPROVED"
        assert decision.confidence_level == "high"
        assert len(decision.supporting_reasons) > 0
        assert len(decision.risk_warnings) == 0

    @pytest.mark.asyncio
    async def test_approval_with_warnings(self):
        """Test approval with some warnings but passing."""
        orchestrator = DeploymentDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["Minor constraint"],

            feasibility_ratio=Decimal("1.2"),
            backtest_return=Decimal("0.12"),
            backtest_sharpe=Decimal("1.8"),
            backtest_max_drawdown=Decimal("-0.12"),

            recommendation_score=Decimal("78"),
            recommendation_confidence="high",
            recommendation_alternatives=["Alt_1"],

            portfolio_quality=Decimal("82"),
            portfolio_diversification_score=Decimal("80"),
            portfolio_concentration_risk=Decimal("18"),
            portfolio_num_assets=10,

            portfolio_risk_level="medium",
            estimated_max_loss=Decimal("-35000"),

            capital_tier="medium",
            objective="growth",
            risk_profile="moderate",
            target_monthly_return=Decimal("1200"),
            initial_capital=Decimal("300000")
        )

        assert decision.decision_status == "APPROVED"
        assert decision.analysis.validation_warnings == ["Minor constraint"]


class TestConditionalDecisions:
    @pytest.mark.asyncio
    async def test_conditional_marginal_feasibility(self):
        """Test conditional decision with marginal feasibility."""
        orchestrator = DeploymentDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],

            feasibility_ratio=Decimal("0.85"),  # MARGINAL
            backtest_return=Decimal("0.10"),
            backtest_sharpe=Decimal("1.2"),
            backtest_max_drawdown=Decimal("-0.15"),

            recommendation_score=Decimal("70"),
            recommendation_confidence="medium",
            recommendation_alternatives=["Alt_1", "Alt_2"],

            portfolio_quality=Decimal("72"),
            portfolio_diversification_score=Decimal("70"),
            portfolio_concentration_risk=Decimal("22"),
            portfolio_num_assets=8,

            portfolio_risk_level="medium",
            estimated_max_loss=Decimal("-40000"),

            capital_tier="small",
            objective="balanced_growth",
            risk_profile="moderate",
            target_monthly_return=Decimal("800"),
            initial_capital=Decimal("200000")
        )

        assert decision.decision_status == "CONDITIONAL"
        assert decision.confidence_level == "medium"
        assert any("optimize" in reason.lower() for reason in decision.remediation_steps)

    @pytest.mark.asyncio
    async def test_conditional_low_recommendation(self):
        """Test conditional decision with low recommendation confidence."""
        orchestrator = DeploymentDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],

            feasibility_ratio=Decimal("1.1"),
            backtest_return=Decimal("0.13"),
            backtest_sharpe=Decimal("1.5"),
            backtest_max_drawdown=Decimal("-0.10"),

            recommendation_score=Decimal("55"),
            recommendation_confidence="low",
            recommendation_alternatives=[],

            portfolio_quality=Decimal("68"),
            portfolio_diversification_score=Decimal("65"),
            portfolio_concentration_risk=Decimal("25"),
            portfolio_num_assets=7,

            portfolio_risk_level="low",
            estimated_max_loss=Decimal("-25000"),

            capital_tier="medium",
            objective="income_generation",
            risk_profile="conservative",
            target_monthly_return=Decimal("600"),
            initial_capital=Decimal("250000")
        )

        assert decision.decision_status == "CONDITIONAL"
        assert "promise" in decision.primary_reason.lower()
        assert any("low" in reason.lower() for reason in decision.supporting_reasons)


class TestRejectedDecisions:
    @pytest.mark.asyncio
    async def test_rejected_validation_failure(self):
        """Test rejection due to validation failure."""
        orchestrator = DeploymentDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_passed=False,
            validation_failures=["Capital gate failed", "Risk limit exceeded"],
            validation_warnings=["Monitor concentration"],

            feasibility_ratio=Decimal("1.5"),
            backtest_return=Decimal("0.18"),
            backtest_sharpe=Decimal("2.5"),
            backtest_max_drawdown=Decimal("-0.05"),

            recommendation_score=Decimal("90"),
            recommendation_confidence="high",
            recommendation_alternatives=[],

            portfolio_quality=Decimal("95"),
            portfolio_diversification_score=Decimal("90"),
            portfolio_concentration_risk=Decimal("10"),
            portfolio_num_assets=15,

            portfolio_risk_level="low",
            estimated_max_loss=Decimal("-15000"),

            capital_tier="large",
            objective="balanced_growth",
            risk_profile="moderate",
            target_monthly_return=Decimal("2000"),
            initial_capital=Decimal("500000")
        )

        assert decision.decision_status == "REJECTED"
        assert decision.confidence_level == "low"
        assert not decision.analysis.validation_passed
        assert len(decision.analysis.validation_failures) > 0

    @pytest.mark.asyncio
    async def test_rejected_not_viable_feasibility(self):
        """Test rejection due to not viable feasibility ratio."""
        orchestrator = DeploymentDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],

            feasibility_ratio=Decimal("0.5"),  # NOT_VIABLE
            backtest_return=Decimal("0.05"),
            backtest_sharpe=Decimal("0.8"),
            backtest_max_drawdown=Decimal("-0.20"),

            recommendation_score=Decimal("45"),
            recommendation_confidence="low",
            recommendation_alternatives=["Better_Option_A"],

            portfolio_quality=Decimal("55"),
            portfolio_diversification_score=Decimal("50"),
            portfolio_concentration_risk=Decimal("40"),
            portfolio_num_assets=5,

            portfolio_risk_level="high",
            estimated_max_loss=Decimal("-60000"),

            capital_tier="micro",
            objective="capital_preservation",
            risk_profile="conservative",
            target_monthly_return=Decimal("1500"),
            initial_capital=Decimal("100000")
        )

        assert decision.decision_status == "REJECTED"
        assert decision.analysis.feasibility_assessment == "NOT_VIABLE"

    @pytest.mark.asyncio
    async def test_rejected_all_poor_indicators(self):
        """Test rejection with multiple poor indicators."""
        orchestrator = DeploymentDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_passed=False,
            validation_failures=["Multiple failures"],
            validation_warnings=["Warning 1", "Warning 2"],

            feasibility_ratio=Decimal("0.4"),
            backtest_return=Decimal("0.03"),
            backtest_sharpe=Decimal("0.5"),
            backtest_max_drawdown=Decimal("-0.35"),

            recommendation_score=Decimal("35"),
            recommendation_confidence="low",
            recommendation_alternatives=[],

            portfolio_quality=Decimal("35"),
            portfolio_diversification_score=Decimal("30"),
            portfolio_concentration_risk=Decimal("65"),
            portfolio_num_assets=3,

            portfolio_risk_level="high",
            estimated_max_loss=Decimal("-90000"),

            capital_tier="micro",
            objective="capital_preservation",
            risk_profile="conservative",
            target_monthly_return=Decimal("500"),
            initial_capital=Decimal("50000")
        )

        assert decision.decision_status == "REJECTED"
        assert len(decision.remediation_steps) > 0


class TestDecisionAnalysis:
    @pytest.mark.asyncio
    async def test_validation_assessment(self):
        """Test validation assessment logic."""
        orchestrator = DeploymentDecisionOrchestrator()

        # Passing validation
        assessment1 = await orchestrator._assess_validation(
            passed=True,
            failures=[],
            warnings=[]
        )
        assert assessment1["passed"] is True
        assert assessment1["assessment"] == "PASSED"

        # Failing validation
        assessment2 = await orchestrator._assess_validation(
            passed=False,
            failures=["Failure 1", "Failure 2"],
            warnings=["Warning"]
        )
        assert assessment2["passed"] is False
        assert assessment2["num_failures"] == 2
        assert assessment2["assessment"] == "FAILED"

    @pytest.mark.asyncio
    async def test_feasibility_assessment(self):
        """Test feasibility ratio assessment."""
        orchestrator = DeploymentDecisionOrchestrator()

        # Viable
        viable = await orchestrator._assess_feasibility(Decimal("1.2"))
        assert viable["assessment"] == "VIABLE"
        assert viable["level"] == "strong"

        # Marginal
        marginal = await orchestrator._assess_feasibility(Decimal("0.85"))
        assert marginal["assessment"] == "MARGINAL"
        assert marginal["level"] == "moderate"

        # Not viable
        not_viable = await orchestrator._assess_feasibility(Decimal("0.5"))
        assert not_viable["assessment"] == "NOT_VIABLE"
        assert not_viable["level"] == "weak"

    @pytest.mark.asyncio
    async def test_recommendation_assessment(self):
        """Test recommendation assessment."""
        orchestrator = DeploymentDecisionOrchestrator()

        # High confidence, strong score
        high = await orchestrator._assess_recommendation(
            Decimal("85"), "high"
        )
        assert high["confidence"] == "high"
        assert high["score_level"] == "strong"
        assert high["confidence_weight"] == Decimal("1.0")

        # Medium confidence, moderate score
        med = await orchestrator._assess_recommendation(
            Decimal("70"), "medium"
        )
        assert med["confidence"] == "medium"
        assert med["score_level"] == "moderate"
        assert med["confidence_weight"] == Decimal("0.7")

        # Low confidence
        low = await orchestrator._assess_recommendation(
            Decimal("45"), "low"
        )
        assert low["confidence"] == "low"
        assert low["score_level"] == "weak"
        assert low["confidence_weight"] == Decimal("0.4")

    @pytest.mark.asyncio
    async def test_portfolio_quality_assessment(self):
        """Test portfolio quality assessment."""
        orchestrator = DeploymentDecisionOrchestrator()

        # Excellent portfolio
        excellent = await orchestrator._assess_portfolio_quality(
            quality=Decimal("88"),
            diversification=Decimal("85"),
            concentration=Decimal("15"),
            num_assets=12,
            risk_level="medium"
        )
        assert excellent["quality_level"] == "excellent"
        assert excellent["diversification_level"] == "well_diversified"
        assert excellent["concentration_risk"] == "low"

        # Poor portfolio
        poor = await orchestrator._assess_portfolio_quality(
            quality=Decimal("35"),
            diversification=Decimal("30"),
            concentration=Decimal("65"),
            num_assets=3,
            risk_level="high"
        )
        assert poor["quality_level"] == "poor"
        assert poor["diversification_level"] == "concentrated"
        assert poor["concentration_risk"] == "high"

    @pytest.mark.asyncio
    async def test_risk_assessment(self):
        """Test risk assessment logic."""
        orchestrator = DeploymentDecisionOrchestrator()

        # Compatible risk
        compatible = await orchestrator._assess_risk(
            max_drawdown=Decimal("-0.08"),
            estimated_max_loss=Decimal("-20000"),
            portfolio_risk_level="medium",
            user_risk_profile="moderate",
            initial_capital=Decimal("250000")
        )
        assert compatible["risk_compatible"] is True
        assert len(compatible["warnings"]) == 0

        # Incompatible risk
        incompatible = await orchestrator._assess_risk(
            max_drawdown=Decimal("-0.50"),
            estimated_max_loss=Decimal("-150000"),
            portfolio_risk_level="high",
            user_risk_profile="conservative",
            initial_capital=Decimal("250000")
        )
        assert incompatible["risk_compatible"] is False
        assert len(incompatible["warnings"]) > 0


class TestReasoningGeneration:
    @pytest.mark.asyncio
    async def test_approved_reasoning(self):
        """Test reasoning generation for approved decision."""
        orchestrator = DeploymentDecisionOrchestrator()

        primary, supporting = await orchestrator._generate_reasoning(
            decision="APPROVED",
            validation={"passed": True, "num_failures": 0},
            feasibility={"assessment": "VIABLE"},
            recommendation={"confidence": "high"},
            portfolio={"quality_level": "excellent"}
        )

        assert "viable" in primary.lower()
        assert "approved" not in primary.lower()
        assert len(supporting) >= 2

    @pytest.mark.asyncio
    async def test_conditional_reasoning(self):
        """Test reasoning generation for conditional decision."""
        orchestrator = DeploymentDecisionOrchestrator()

        primary, supporting = await orchestrator._generate_reasoning(
            decision="CONDITIONAL",
            validation={"passed": True, "num_failures": 0},
            feasibility={"assessment": "MARGINAL"},
            recommendation={"confidence": "low"},
            portfolio={"quality_level": "acceptable"}
        )

        assert "promise" in primary.lower()
        assert len(supporting) >= 1

    @pytest.mark.asyncio
    async def test_rejected_reasoning(self):
        """Test reasoning generation for rejected decision."""
        orchestrator = DeploymentDecisionOrchestrator()

        primary, supporting = await orchestrator._generate_reasoning(
            decision="REJECTED",
            validation={"passed": False, "num_failures": 2},
            feasibility={"assessment": "NOT_VIABLE"},
            recommendation={"confidence": "low"},
            portfolio={"quality_level": "poor"}
        )

        assert "cannot be approved" in primary.lower()
        assert len(supporting) >= 1


class TestRemediationGeneration:
    @pytest.mark.asyncio
    async def test_approved_remediation(self):
        """Test remediation for approved decision."""
        orchestrator = DeploymentDecisionOrchestrator()

        steps = await orchestrator._generate_remediation(
            decision="APPROVED",
            validation_failures=[],
            feasibility={"assessment": "VIABLE"},
            recommendation={"confidence": "high"}
        )

        assert len(steps) > 0
        assert any("monitor" in step.lower() for step in steps)

    @pytest.mark.asyncio
    async def test_conditional_remediation(self):
        """Test remediation for conditional decision."""
        orchestrator = DeploymentDecisionOrchestrator()

        steps = await orchestrator._generate_remediation(
            decision="CONDITIONAL",
            validation_failures=[],
            feasibility={"assessment": "MARGINAL"},
            recommendation={"confidence": "low"}
        )

        assert len(steps) > 0
        assert any("optimize" in step.lower() for step in steps)

    @pytest.mark.asyncio
    async def test_rejected_remediation(self):
        """Test remediation for rejected decision."""
        orchestrator = DeploymentDecisionOrchestrator()

        steps = await orchestrator._generate_remediation(
            decision="REJECTED",
            validation_failures=["Capital gate failed"],
            feasibility={"assessment": "NOT_VIABLE"},
            recommendation={"confidence": "low"}
        )

        assert len(steps) > 0
        assert any("address" in step.lower() or "adjust" in step.lower() for step in steps)


class TestDecisionHistory:
    @pytest.mark.asyncio
    async def test_decision_history_tracking(self):
        """Test decision history tracking."""
        orchestrator = DeploymentDecisionOrchestrator()

        # Make multiple decisions
        for i in range(3):
            await orchestrator.orchestrate(
                validation_passed=True,
                validation_failures=[],
                validation_warnings=[],

                feasibility_ratio=Decimal("1.1") + Decimal(i) * Decimal("0.1"),
                backtest_return=Decimal("0.12"),
                backtest_sharpe=Decimal("1.5"),
                backtest_max_drawdown=Decimal("-0.10"),

                recommendation_score=Decimal("75"),
                recommendation_confidence="high",
                recommendation_alternatives=[],

                portfolio_quality=Decimal("80"),
                portfolio_diversification_score=Decimal("80"),
                portfolio_concentration_risk=Decimal("20"),
                portfolio_num_assets=10,

                portfolio_risk_level="medium",
                estimated_max_loss=Decimal("-30000"),

                capital_tier="medium",
                objective="growth",
                risk_profile="moderate",
                target_monthly_return=Decimal("1000"),
                initial_capital=Decimal("250000")
            )

        history = await orchestrator.get_decision_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_decision_history_filtering(self):
        """Test decision history filtering by status."""
        orchestrator = DeploymentDecisionOrchestrator()

        # Create mixed decisions
        await orchestrator.orchestrate(
            validation_passed=True, validation_failures=[], validation_warnings=[],
            feasibility_ratio=Decimal("1.2"),
            backtest_return=Decimal("0.15"), backtest_sharpe=Decimal("2.0"),
            backtest_max_drawdown=Decimal("-0.08"),
            recommendation_score=Decimal("85"), recommendation_confidence="high",
            recommendation_alternatives=[],
            portfolio_quality=Decimal("88"),
            portfolio_diversification_score=Decimal("85"),
            portfolio_concentration_risk=Decimal("15"),
            portfolio_num_assets=12,
            portfolio_risk_level="medium", estimated_max_loss=Decimal("-20000"),
            capital_tier="medium", objective="growth", risk_profile="moderate",
            target_monthly_return=Decimal("1000"), initial_capital=Decimal("250000")
        )

        await orchestrator.orchestrate(
            validation_passed=False, validation_failures=["Failed"], validation_warnings=[],
            feasibility_ratio=Decimal("0.5"),
            backtest_return=Decimal("0.05"), backtest_sharpe=Decimal("0.8"),
            backtest_max_drawdown=Decimal("-0.20"),
            recommendation_score=Decimal("45"), recommendation_confidence="low",
            recommendation_alternatives=[],
            portfolio_quality=Decimal("35"),
            portfolio_diversification_score=Decimal("30"),
            portfolio_concentration_risk=Decimal("65"),
            portfolio_num_assets=3,
            portfolio_risk_level="high", estimated_max_loss=Decimal("-60000"),
            capital_tier="micro", objective="preservation", risk_profile="conservative",
            target_monthly_return=Decimal("500"), initial_capital=Decimal("50000")
        )

        approved = await orchestrator.get_decision_history(status_filter="APPROVED")
        rejected = await orchestrator.get_decision_history(status_filter="REJECTED")

        assert len(approved) >= 1
        assert len(rejected) >= 1

    @pytest.mark.asyncio
    async def test_deployment_statistics(self):
        """Test deployment decision statistics."""
        orchestrator = DeploymentDecisionOrchestrator()

        # Create multiple decisions
        for i in range(5):
            status = "high" if i < 3 else "low"
            await orchestrator.orchestrate(
                validation_passed=(i < 4),
                validation_failures=[] if i < 4 else ["Failed"],
                validation_warnings=[],

                feasibility_ratio=Decimal("1.2") if i < 3 else Decimal("0.5"),
                backtest_return=Decimal("0.15") if i < 3 else Decimal("0.05"),
                backtest_sharpe=Decimal("2.0") if i < 3 else Decimal("0.8"),
                backtest_max_drawdown=Decimal("-0.08"),

                recommendation_score=Decimal("80"),
                recommendation_confidence=status,
                recommendation_alternatives=[],

                portfolio_quality=Decimal("85") if i < 3 else Decimal("40"),
                portfolio_diversification_score=Decimal("80"),
                portfolio_concentration_risk=Decimal("20"),
                portfolio_num_assets=10,

                portfolio_risk_level="medium", estimated_max_loss=Decimal("-30000"),
                capital_tier="medium", objective="growth", risk_profile="moderate",
                target_monthly_return=Decimal("1000"), initial_capital=Decimal("250000")
            )

        stats = await orchestrator.get_deployment_statistics()
        assert stats["total_decisions"] == 5
        assert stats["approved_count"] > 0
        assert stats["approval_rate"] > Decimal("0")

    def test_orchestrator_status(self):
        """Test orchestrator operational status."""
        orchestrator = DeploymentDecisionOrchestrator()
        status = orchestrator.get_orchestrator_status()

        assert status["total_decisions_processed"] == 0
        assert status["metrics_entries"] == 0
        assert status["last_decision"] is None


class TestDecisionEdgeCases:
    @pytest.mark.asyncio
    async def test_decision_with_exact_boundaries(self):
        """Test decision logic at exact thresholds."""
        orchestrator = DeploymentDecisionOrchestrator()

        # Exactly at feasibility boundary (1.0)
        decision = await orchestrator.orchestrate(
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],

            feasibility_ratio=Decimal("1.00"),
            backtest_return=Decimal("0.10"),
            backtest_sharpe=Decimal("1.5"),
            backtest_max_drawdown=Decimal("-0.10"),

            recommendation_score=Decimal("75"),
            recommendation_confidence="high",
            recommendation_alternatives=[],

            portfolio_quality=Decimal("75"),
            portfolio_diversification_score=Decimal("75"),
            portfolio_concentration_risk=Decimal("25"),
            portfolio_num_assets=8,

            portfolio_risk_level="medium",
            estimated_max_loss=Decimal("-30000"),

            capital_tier="medium",
            objective="balanced_growth",
            risk_profile="moderate",
            target_monthly_return=Decimal("1000"),
            initial_capital=Decimal("250000")
        )

        assert decision.decision_status in ["APPROVED", "CONDITIONAL"]

    @pytest.mark.asyncio
    async def test_decision_with_no_alternatives(self):
        """Test decision when no alternative strategies exist."""
        orchestrator = DeploymentDecisionOrchestrator()

        decision = await orchestrator.orchestrate(
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],

            feasibility_ratio=Decimal("1.15"),
            backtest_return=Decimal("0.13"),
            backtest_sharpe=Decimal("1.8"),
            backtest_max_drawdown=Decimal("-0.09"),

            recommendation_score=Decimal("82"),
            recommendation_confidence="high",
            recommendation_alternatives=[],

            portfolio_quality=Decimal("85"),
            portfolio_diversification_score=Decimal("82"),
            portfolio_concentration_risk=Decimal("18"),
            portfolio_num_assets=10,

            portfolio_risk_level="medium",
            estimated_max_loss=Decimal("-25000"),

            capital_tier="medium",
            objective="growth",
            risk_profile="moderate",
            target_monthly_return=Decimal("1100"),
            initial_capital=Decimal("250000")
        )

        assert decision.decision_status == "APPROVED"
        assert len(decision.alternative_strategies) == 0

    @pytest.mark.asyncio
    async def test_decision_with_extreme_capital(self):
        """Test decision logic with extreme capital amounts."""
        orchestrator = DeploymentDecisionOrchestrator()

        # Very small capital (micro)
        micro_decision = await orchestrator.orchestrate(
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],

            feasibility_ratio=Decimal("1.1"),
            backtest_return=Decimal("0.12"),
            backtest_sharpe=Decimal("1.5"),
            backtest_max_drawdown=Decimal("-0.10"),

            recommendation_score=Decimal("75"),
            recommendation_confidence="high",
            recommendation_alternatives=[],

            portfolio_quality=Decimal("75"),
            portfolio_diversification_score=Decimal("70"),
            portfolio_concentration_risk=Decimal("30"),
            portfolio_num_assets=5,

            portfolio_risk_level="medium",
            estimated_max_loss=Decimal("-500"),

            capital_tier="micro",
            objective="growth",
            risk_profile="moderate",
            target_monthly_return=Decimal("50"),
            initial_capital=Decimal("10000")
        )

        assert micro_decision.analysis.capital_tier == "micro"

        # Very large capital
        large_decision = await orchestrator.orchestrate(
            validation_passed=True,
            validation_failures=[],
            validation_warnings=[],

            feasibility_ratio=Decimal("1.1"),
            backtest_return=Decimal("0.12"),
            backtest_sharpe=Decimal("1.5"),
            backtest_max_drawdown=Decimal("-0.10"),

            recommendation_score=Decimal("80"),
            recommendation_confidence="high",
            recommendation_alternatives=[],

            portfolio_quality=Decimal("85"),
            portfolio_diversification_score=Decimal("85"),
            portfolio_concentration_risk=Decimal("15"),
            portfolio_num_assets=20,

            portfolio_risk_level="medium",
            estimated_max_loss=Decimal("-200000"),

            capital_tier="large",
            objective="growth",
            risk_profile="moderate",
            target_monthly_return=Decimal("5000"),
            initial_capital=Decimal("2000000")
        )

        assert large_decision.analysis.capital_tier == "large"


class TestDecisionDataStructures:
    def test_deployment_analysis_dataclass(self):
        """Test DeploymentAnalysis dataclass."""
        analysis = DeploymentAnalysis(
            validation_passed=True,
            validation_failures=[],
            validation_warnings=["Minor warning"],

            feasibility_ratio=Decimal("1.15"),
            feasibility_assessment="VIABLE",

            recommendation_confidence="high",
            recommendation_score=Decimal("85"),

            portfolio_quality=Decimal("85"),
            portfolio_risk_assessment="medium",

            capital_tier="medium",
            objective="growth",
            risk_profile="moderate"
        )

        assert analysis.validation_passed is True
        assert analysis.feasibility_assessment == "VIABLE"
        assert analysis.analysis_timestamp is not None

    def test_deployment_decision_dataclass(self):
        """Test DeploymentDecision dataclass."""
        decision = DeploymentDecision(
            decision_status="APPROVED",
            confidence_level="high",
            primary_reason="Strong metrics",
            supporting_reasons=["Reason 1"],
            risk_warnings=[],
            analysis=DeploymentAnalysis(
                validation_passed=True,
                validation_failures=[],
                validation_warnings=[],
                feasibility_ratio=Decimal("1.15"),
                feasibility_assessment="VIABLE",
                recommendation_confidence="high",
                recommendation_score=Decimal("85"),
                portfolio_quality=Decimal("85"),
                portfolio_risk_assessment="medium",
                capital_tier="medium",
                objective="growth",
                risk_profile="moderate"
            ),
            remediation_steps=[],
            alternative_strategies=[]
        )

        assert decision.decision_status == "APPROVED"
        assert decision.decision_id != ""
        assert decision.decision_timestamp is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
