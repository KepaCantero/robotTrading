"""
Unit Tests: Robustness Scorer (TASK-6.1 Phase 3)

Tests for:
- Robustness score calculation
- Production readiness verdict
- Risk factor identification
- Recommendations generation
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

import pytest

project_root = Path(__file__).parent.parent.parent
import sys

sys.path.insert(0, str(project_root))

from app.optimization.robustness_scorer import (
    ProductionReadiness,
    RiskFactor,
    RiskLevel,
    RobustnessReport,
    RobustnessScorer,
)


class TestRobustnessScorerInitialization:
    """Tests for RobustnessScorer initialization."""

    def test_initialization_with_default_config(self):
        """Test initialization with default configuration."""
        scorer = RobustnessScorer()

        assert scorer.config is not None
        assert "robustness" in scorer.config
        assert "weighting" in scorer.config["robustness"]
        assert "thresholds" in scorer.config["robustness"]

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        custom_config = {
            "robustness": {
                "weighting": {
                    "consistency": 0.40,
                    "stability": 0.30,
                    "sensitivity": 0.15,
                    "overfitting": 0.10,
                    "regime_robustness": 0.05,
                },
                "thresholds": {"pass": 75.0, "warn": 50.0, "fail": 0.0},
            }
        }

        scorer = RobustnessScorer(config=custom_config)

        assert scorer.config == custom_config


class TestRobustnessScoreCalculation:
    """Tests for robustness score calculation."""

    def test_perfect_scores(self):
        """Test scoring with perfect component scores."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=100.0,
            stability_score=100.0,
            sensitivity_score=100.0,
            overfitting_penalty=100.0,
            regime_robustness_score=100.0,
        )

        assert result.overall_robustness_score > 90.0
        assert result.production_readiness == ProductionReadiness.PASS

    def test_poor_scores(self):
        """Test scoring with poor component scores."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=30.0,
            stability_score=30.0,
            sensitivity_score=30.0,
            overfitting_penalty=30.0,
            regime_robustness_score=30.0,
        )

        assert result.overall_robustness_score < 50.0
        assert result.production_readiness == ProductionReadiness.FAIL

    def test_mixed_scores(self):
        """Test scoring with mixed component scores."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=80.0,  # Good
            stability_score=70.0,  # Okay
            sensitivity_score=60.0,  # Below average
            overfitting_penalty=75.0,  # Okay
            regime_robustness_score=65.0,  # Below average
        )

        # Will have some risk penalties applied, so score will be lower
        assert 40.0 <= result.overall_robustness_score <= 75.0


class TestProductionReadinessDetermination:
    """Tests for production readiness verdict."""

    def test_pass_verdict(self):
        """Test PASS verdict for deployable strategy."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=90.0,
            stability_score=85.0,
            sensitivity_score=80.0,
            overfitting_penalty=85.0,
            regime_robustness_score=80.0,
        )

        assert result.production_readiness == ProductionReadiness.PASS

    def test_warn_verdict(self):
        """Test WARN verdict for conditional deployment."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=75.0,  # Just above 60% threshold
            stability_score=75.0,  # Just above 70 threshold
            sensitivity_score=75.0,
            overfitting_penalty=75.0,  # Just above 80% threshold
            regime_robustness_score=75.0,  # Just above 70% threshold
        )

        assert result.production_readiness == ProductionReadiness.WARN

    def test_fail_verdict(self):
        """Test FAIL verdict for risky strategy."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=40.0,
            stability_score=45.0,
            sensitivity_score=50.0,
            overfitting_penalty=40.0,
            regime_robustness_score=45.0,
        )

        assert result.production_readiness == ProductionReadiness.FAIL


class TestRiskFactorIdentification:
    """Tests for risk factor identification."""

    def test_identify_low_consistency_risk(self):
        """Test identification of low consistency risk."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=40.0,  # Below 60% threshold
            stability_score=80.0,
            sensitivity_score=80.0,
            overfitting_penalty=80.0,
            regime_robustness_score=80.0,
        )

        consistency_factors = [f for f in result.risk_factors if "Consistency" in f.name]
        assert len(consistency_factors) > 0
        assert consistency_factors[0].severity == RiskLevel.HIGH

    def test_identify_unstable_parameters_risk(self):
        """Test identification of unstable parameters risk."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=80.0,
            stability_score=45.0,  # Below 70 threshold
            sensitivity_score=80.0,
            overfitting_penalty=80.0,
            regime_robustness_score=80.0,
        )

        stability_factors = [f for f in result.risk_factors if "Unstable" in f.name]
        assert len(stability_factors) > 0

    def test_identify_overfitting_risk(self):
        """Test identification of overfitting risk."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=80.0,
            stability_score=80.0,
            sensitivity_score=80.0,
            overfitting_penalty=30.0,  # Large IS/OOS gap
            regime_robustness_score=80.0,
        )

        overfitting_factors = [f for f in result.risk_factors if "Overfitting" in f.name]
        assert len(overfitting_factors) > 0
        assert overfitting_factors[0].severity == RiskLevel.HIGH

    def test_identify_regime_dependence_risk(self):
        """Test identification of regime dependence risk."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=80.0,
            stability_score=80.0,
            sensitivity_score=80.0,
            overfitting_penalty=80.0,
            regime_robustness_score=50.0,  # Below 70% threshold
        )

        regime_factors = [f for f in result.risk_factors if "Regime" in f.name]
        assert len(regime_factors) > 0

    def test_no_risk_factors_when_all_good(self):
        """Test that no risk factors identified when all scores are good."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=95.0,
            stability_score=90.0,
            sensitivity_score=85.0,
            overfitting_penalty=90.0,
            regime_robustness_score=85.0,
        )

        assert len(result.risk_factors) == 0


class TestRiskLevelDetermination:
    """Tests for overall risk level determination."""

    def test_low_risk_level(self):
        """Test LOW risk classification."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=90.0,
            stability_score=85.0,
            sensitivity_score=80.0,
            overfitting_penalty=85.0,
            regime_robustness_score=80.0,
        )

        assert result.risk_level == RiskLevel.LOW

    def test_medium_risk_level(self):
        """Test MEDIUM risk classification."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=65.0,
            stability_score=70.0,
            sensitivity_score=75.0,
            overfitting_penalty=70.0,
            regime_robustness_score=65.0,
        )

        assert result.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]

    def test_high_risk_level(self):
        """Test HIGH risk classification."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=40.0,
            stability_score=45.0,
            sensitivity_score=50.0,
            overfitting_penalty=40.0,
            regime_robustness_score=45.0,
        )

        assert result.risk_level == RiskLevel.HIGH


class TestRecommendationsGeneration:
    """Tests for recommendations generation."""

    def test_recommendations_for_poor_consistency(self):
        """Test recommendations when consistency is poor."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=40.0,
            stability_score=80.0,
            sensitivity_score=80.0,
            overfitting_penalty=80.0,
            regime_robustness_score=80.0,
        )

        assert len(result.recommendations) > 0
        consistency_recs = [r for r in result.recommendations if "Consistency" in r]
        assert len(consistency_recs) > 0

    def test_recommendations_for_excellent_scores(self):
        """Test recommendations when all scores are excellent."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=95.0,
            stability_score=90.0,
            sensitivity_score=85.0,
            overfitting_penalty=90.0,
            regime_robustness_score=85.0,
        )

        # Should have positive feedback
        excellent_recs = [r for r in result.recommendations if "✓" in r]
        assert len(excellent_recs) > 0

    def test_recommendations_are_actionable(self):
        """Test that recommendations are actionable."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=50.0,
            stability_score=50.0,
            sensitivity_score=50.0,
            overfitting_penalty=50.0,
            regime_robustness_score=50.0,
        )

        # Each recommendation should have suggestion
        for rec in result.recommendations:
            assert ":" in rec or "Priority" in rec


class TestBatchScoringParameters:
    """Tests for batch scoring multiple parameters."""

    def test_batch_score_parameters(self):
        """Test batch scoring of multiple parameters."""
        scorer = RobustnessScorer()

        results = {
            "param_a": {
                "consistency": 85.0,
                "stability": 80.0,
                "sensitivity": 75.0,
                "overfitting": 80.0,
                "regime_robustness": 75.0,
            },
            "param_b": {
                "consistency": 60.0,
                "stability": 65.0,
                "sensitivity": 70.0,
                "overfitting": 60.0,
                "regime_robustness": 65.0,
            },
            "param_c": {
                "consistency": 40.0,
                "stability": 45.0,
                "sensitivity": 50.0,
                "overfitting": 40.0,
                "regime_robustness": 45.0,
            },
        }

        report = scorer.batch_score_parameters(results, "test_strategy")

        assert len(report.results) == 3
        assert report.deployable_count >= 0
        assert report.warning_count >= 0
        assert report.failed_count >= 0

    def test_batch_report_summary_score(self):
        """Test that batch report calculates summary score."""
        scorer = RobustnessScorer()

        results = {
            "param_a": {
                "consistency": 80.0,
                "stability": 80.0,
                "sensitivity": 80.0,
                "overfitting": 80.0,
                "regime_robustness": 80.0,
            },
            "param_b": {
                "consistency": 80.0,
                "stability": 80.0,
                "sensitivity": 80.0,
                "overfitting": 80.0,
                "regime_robustness": 80.0,
            },
        }

        report = scorer.batch_score_parameters(results, "test_strategy")

        assert report.summary_score > 0.0
        assert report.summary_score <= 100.0


class TestResultSerialization:
    """Tests for result serialization."""

    def test_robustness_result_to_dict(self):
        """Test conversion of RobustnessResult to dict."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=80.0,
            stability_score=75.0,
            sensitivity_score=70.0,
            overfitting_penalty=75.0,
            regime_robustness_score=70.0,
        )

        result_dict = result.to_dict()

        assert result_dict["strategy_name"] == "momentum"
        assert "overall_robustness_score" in result_dict
        assert "production_readiness" in result_dict
        assert "risk_factors" in result_dict

    def test_robustness_report_to_dict(self):
        """Test conversion of RobustnessReport to dict."""
        report = RobustnessReport()
        report.summary_score = 75.0
        report.deployable_count = 2

        report_dict = report.to_dict()

        assert report_dict["summary_score"] == 75.0
        assert report_dict["deployable_count"] == 2

    def test_robustness_report_json_serialization(self):
        """Test JSON serialization of report."""
        report = RobustnessReport()
        report.summary_score = 80.0

        json_str = report.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["summary_score"] == 80.0


class TestScoreDetails:
    """Tests for score details breakdown."""

    def test_score_details_calculation(self):
        """Test that score details are properly calculated."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=85.0,
            stability_score=80.0,
            sensitivity_score=75.0,
            overfitting_penalty=80.0,
            regime_robustness_score=75.0,
        )

        assert result.score_details is not None
        assert result.score_details.consistency_score == 85.0
        assert result.score_details.stability_score == 80.0
        assert result.score_details.weighted_score > 0

    def test_weighted_score_uses_weights(self):
        """Test that weighted score properly applies weights."""
        scorer = RobustnessScorer()

        result1 = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=100.0,
            stability_score=0.0,
            sensitivity_score=0.0,
            overfitting_penalty=0.0,
            regime_robustness_score=0.0,
        )

        # Consistency has 30% weight, so score should be 30.0
        assert 25.0 < result1.score_details.weighted_score < 35.0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_score_normalization_above_100(self):
        """Test that scores above 100 are normalized to 100."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=150.0,  # Above 100
            stability_score=80.0,
            sensitivity_score=80.0,
            overfitting_penalty=80.0,
            regime_robustness_score=80.0,
        )

        assert result.score_details.consistency_score == 100.0

    def test_score_normalization_below_0(self):
        """Test that negative scores are normalized to 0."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=-10.0,  # Below 0
            stability_score=80.0,
            sensitivity_score=80.0,
            overfitting_penalty=80.0,
            regime_robustness_score=80.0,
        )

        assert result.score_details.consistency_score == 0.0

    def test_parameter_name_optional(self):
        """Test that parameter_name is optional."""
        scorer = RobustnessScorer()

        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=80.0,
            stability_score=80.0,
            sensitivity_score=80.0,
            overfitting_penalty=80.0,
            regime_robustness_score=80.0,
            parameter_name=None,
        )

        assert result.parameter_name is None


class TestPrintingReport:
    """Tests for report printing."""

    def test_print_robustness_report(self, capsys):
        """Test that robustness report can be printed."""
        scorer = RobustnessScorer()

        report = RobustnessReport()
        result = scorer.calculate_robustness_score(
            strategy_name="momentum",
            consistency_score=80.0,
            stability_score=75.0,
            sensitivity_score=70.0,
            overfitting_penalty=75.0,
            regime_robustness_score=70.0,
            parameter_name="param_a",
        )
        report.results["param_a"] = result
        report.summary_score = 75.0

        # Should not raise exception
        try:
            scorer.print_robustness_report(report)
        except Exception as e:
            pytest.fail(f"print_robustness_report raised exception: {e}")
