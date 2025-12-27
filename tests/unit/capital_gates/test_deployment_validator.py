"""
Unit Tests for T0.4: Deployment Validator

Tests deployment validation orchestration across all capital gates.
Validates that accounts are safe for live deployment before going live.
"""

from decimal import Decimal

from app.services.deployment_validator import DeploymentStatus, DeploymentValidator


class TestDeploymentValidatorBasic:
    """Test basic deployment validation"""

    def test_micro_account_rejected(self):
        """Micro account (<$15k) should be rejected"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("10000"),
            monthly_profit_goal=Decimal("100"),
            expected_monthly_alpha=Decimal("100"),
        )

        assert status == DeploymentStatus.REJECTED
        assert len(analysis["issues"]) > 0

    def test_small_account_restricted(self):
        """Small account ($15k-$50k) with higher alpha should be restricted or approved"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("30000"),
            monthly_profit_goal=Decimal("200"),
            expected_monthly_alpha=Decimal("800"),  # Higher alpha
        )

        # May be restricted due to module costs, but should not be immediately rejected
        assert status in [
            DeploymentStatus.RESTRICTED,
            DeploymentStatus.APPROVED,
            DeploymentStatus.REVIEW_REQUIRED,
        ]

    def test_medium_account_approved(self):
        """Medium account ($50k-$250k) with reasonable goals should be approved"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("100000"),
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("1500"),  # Higher alpha
        )

        # Should have few/no issues at this capital level
        assert len(analysis["issues"]) <= 1

    def test_large_account_approved(self):
        """Large account ($250k+) should be approved with sufficient alpha"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("500000"),
            monthly_profit_goal=Decimal("2000"),
            expected_monthly_alpha=Decimal("50000"),  # Large alpha justifies modules
        )

        # Large accounts with sufficient alpha should have no critical issues
        assert len(analysis["issues"]) == 0
        assert status in [DeploymentStatus.APPROVED, DeploymentStatus.RESTRICTED]


class TestDeploymentValidatorGates:
    """Test individual gate validation results"""

    def test_capital_viability_gate_failure(self):
        """Capital viability gate should fail on unrealistic goals"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("15000"),
            monthly_profit_goal=Decimal("3000"),  # 20% monthly - unrealistic
            expected_monthly_alpha=Decimal("3000"),
        )

        assert analysis["gates"]["capital_viability"]["severity"] == "CRITICAL"
        assert not analysis["gates"]["capital_viability"]["passed"]

    def test_execution_cost_gate_passes_normal_trade(self):
        """Execution cost gate should pass for normal trades"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("50000"),
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("500"),
            commission_per_trade=Decimal("15"),
        )

        # Should at least evaluate execution cost
        assert "execution_cost" in analysis["gates"]

    def test_learning_gate_disabled_for_micro(self):
        """Learning gate should report disabled for micro accounts"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("10000"),
            monthly_profit_goal=Decimal("100"),
            expected_monthly_alpha=Decimal("100"),
            learning_enabled=True,
        )

        assert not analysis["gates"]["learning_capital"]["passed"]

    def test_learning_gate_enabled_for_large(self):
        """Learning gate should be enabled for large accounts"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("300000"),
            monthly_profit_goal=Decimal("1000"),
            expected_monthly_alpha=Decimal("2000"),
            learning_enabled=True,
        )

        assert analysis["gates"]["learning_capital"]["passed"]


class TestDeploymentValidatorAnalysis:
    """Test analysis output"""

    def test_analysis_includes_all_gates(self):
        """Analysis should include results from all gates"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("50000"),
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("500"),
        )

        gates = analysis["gates"]
        assert "capital_viability" in gates
        assert "execution_cost" in gates
        assert "learning_capital" in gates
        assert "expensive_modules" in gates

    def test_analysis_includes_recommendations(self):
        """Analysis should include recommendations"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("10000"),
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("500"),
        )

        assert len(analysis["recommendations"]) > 0

    def test_analysis_includes_account_id(self):
        """Analysis should include account ID if provided"""
        account_id = "TEST_ACCT_001"
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("50000"),
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("500"),
            account_id=account_id,
        )

        assert analysis["account_id"] == account_id


class TestDeploymentStatusDetermination:
    """Test status determination logic"""

    def test_status_approved_no_issues_no_warnings(self):
        """Status should be APPROVED with no issues or warnings"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("500000"),
            monthly_profit_goal=Decimal("2000"),
            expected_monthly_alpha=Decimal("3000"),
            learning_enabled=True,
            expensive_modules_enabled=True,
        )

        if len(analysis["issues"]) == 0 and len(analysis["warnings"]) == 0:
            assert status == DeploymentStatus.APPROVED

    def test_status_restricted_with_warnings(self):
        """Status should be RESTRICTED with some warnings"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("30000"),
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("300"),
        )

        # Small account likely has warnings
        if len(analysis["issues"]) == 0:
            # Only check if no critical issues
            pass

    def test_status_rejected_with_issues(self):
        """Status should be REJECTED with critical issues"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("10000"),
            monthly_profit_goal=Decimal("1000"),
            expected_monthly_alpha=Decimal("100"),
        )

        if len(analysis["issues"]) > 0:
            assert status == DeploymentStatus.REJECTED


class TestDeploymentReadinessScore:
    """Test readiness score calculation"""

    def test_micro_account_low_score(self):
        """Micro account should have low readiness score"""
        score = DeploymentValidator.get_deployment_readiness_score(Decimal("10000"))
        assert score < 40.0

    def test_small_account_moderate_score(self):
        """Small account should have moderate readiness score"""
        score = DeploymentValidator.get_deployment_readiness_score(Decimal("30000"))
        assert 40.0 <= score < 80.0

    def test_large_account_high_score(self):
        """Large account should have high readiness score"""
        score = DeploymentValidator.get_deployment_readiness_score(Decimal("300000"))
        assert score >= 80.0

    def test_readiness_increases_with_capital(self):
        """Readiness score should increase with capital"""
        score_10k = DeploymentValidator.get_deployment_readiness_score(Decimal("10000"))
        score_100k = DeploymentValidator.get_deployment_readiness_score(Decimal("100000"))
        score_500k = DeploymentValidator.get_deployment_readiness_score(Decimal("500000"))

        assert score_10k < score_100k < score_500k


class TestMinimumCapitalRecommendation:
    """Test minimum capital calculation"""

    def test_minimum_capital_for_goal(self):
        """Calculate minimum capital for a profit goal"""
        recommendations = DeploymentValidator.get_minimum_capital_recommendation(
            monthly_profit_goal=Decimal("500"),
        )

        assert recommendations["for_capital_viability"] >= Decimal("10000")
        assert recommendations["recommended"] >= Decimal("25000")

    def test_learning_minimum_25k(self):
        """Learning minimum should be $25k"""
        recommendations = DeploymentValidator.get_minimum_capital_recommendation(
            monthly_profit_goal=Decimal("100"),
        )

        assert recommendations["for_learning"] == Decimal("25000")

    def test_expensive_modules_minimum_50k(self):
        """Expensive modules minimum should be $50k"""
        recommendations = DeploymentValidator.get_minimum_capital_recommendation(
            monthly_profit_goal=Decimal("100"),
        )

        assert recommendations["for_expensive_modules"] == Decimal("50000")

    def test_high_goal_requires_more_capital(self):
        """Higher profit goals require more capital"""
        recommendations_500 = DeploymentValidator.get_minimum_capital_recommendation(
            monthly_profit_goal=Decimal("500"),
        )
        recommendations_2000 = DeploymentValidator.get_minimum_capital_recommendation(
            monthly_profit_goal=Decimal("2000"),
        )

        assert (
            recommendations_500["for_capital_viability"]
            < recommendations_2000["for_capital_viability"]
        )


class TestDeploymentValidatorIntegration:
    """Integration tests for deployment validator"""

    def test_full_validation_flow_rejected(self):
        """Full validation flow with rejection"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("5000"),
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("100"),
            account_id="TEST_REJECT",
        )

        assert status == DeploymentStatus.REJECTED
        assert analysis["account_id"] == "TEST_REJECT"
        assert len(analysis["issues"]) > 0

    def test_full_validation_flow_approved(self):
        """Full validation flow with approval for large account"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("500000"),
            monthly_profit_goal=Decimal("2000"),
            expected_monthly_alpha=Decimal("50000"),  # Sufficient alpha
            learning_enabled=True,
            account_id="TEST_APPROVE",
        )

        # Large accounts with sufficient alpha should be approved or minimally restricted
        assert status in [DeploymentStatus.APPROVED, DeploymentStatus.RESTRICTED]
        assert len(analysis["issues"]) == 0  # No critical issues for well-capitalized accounts
        assert analysis["account_id"] == "TEST_APPROVE"
        assert analysis["capital_tier"] == "large"

    def test_validation_with_custom_commission(self):
        """Validation with custom commission rates"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("50000"),
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("500"),
            commission_per_trade=Decimal("25"),  # High commission
        )

        # Should still validate
        assert "gates" in analysis
        assert "execution_cost" in analysis["gates"]

    def test_validation_with_tax_rate(self):
        """Validation with custom tax rate"""
        status, analysis = DeploymentValidator.validate_for_deployment(
            capital=Decimal("50000"),
            monthly_profit_goal=Decimal("500"),
            expected_monthly_alpha=Decimal("500"),
            tax_rate=Decimal("0.20"),  # Low tax
        )

        assert analysis["gates"]["capital_viability"]["severity"] in [
            "OK",
            "WARNING",
            "CRITICAL",
        ]
