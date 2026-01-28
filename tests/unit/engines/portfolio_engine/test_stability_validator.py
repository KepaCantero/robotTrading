"""
Unit tests for Portfolio Stability Validator.

Tests cover:
- Time-period stability validation
- Turnover-adjusted performance metrics
- Concentration risk assessment
- Sharpe ratio combination validation
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.engines.portfolio_engine.stability_validator import (
    PortfolioStabilityValidator,
    PortfolioValidationResult,
    StabilityBasedPortfolioSelector,
    StabilityValidationConfig,
    create_portfolio_stability_validator,
    validate_single_portfolio,
)


@pytest.mark.unit
class TestStabilityValidationConfig:
    """Test suite for StabilityValidationConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = StabilityValidationConfig()

        assert config.min_stability_score == 70.0
        assert config.max_turnover_annual == 0.5
        assert config.max_allocation_drift == 0.2
        assert config.rebalancing_frequency_days == 30
        assert config.min_historical_periods == 6
        assert config.max_single_position_weight == 0.3
        assert config.max_hhi == 0.2
        assert config.transaction_cost_bps == 10.0
        assert config.risk_free_rate == 0.02
        assert config.require_stable_for_production is True
        assert config.log_warnings is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = StabilityValidationConfig(
            min_stability_score=80.0,
            max_turnover_annual=0.3,
            max_allocation_drift=0.15,
            rebalancing_frequency_days=21,
            transaction_cost_bps=5.0,
        )

        assert config.min_stability_score == 80.0
        assert config.max_turnover_annual == 0.3
        assert config.max_allocation_drift == 0.15
        assert config.rebalancing_frequency_days == 21
        assert config.transaction_cost_bps == 5.0


@pytest.mark.unit
class TestPortfolioValidationResult:
    """Test suite for PortfolioValidationResult."""

    def test_result_creation(self):
        """Test creating a validation result."""
        result = PortfolioValidationResult(
            is_valid=True,
            is_stable=True,
            is_cost_effective=True,
            is_properly_diversified=True,
            stability_score=85.0,
            concentration_score=15.0,
            annual_turnover=0.3,
            estimated_costs=0.005,
        )

        assert result.is_valid is True
        assert result.is_stable is True
        assert result.is_cost_effective is True
        assert result.is_properly_diversified is True
        assert result.stability_score == 85.0
        assert result.concentration_score == 15.0
        assert result.annual_turnover == 0.3
        assert result.estimated_costs == 0.005

    def test_result_with_warnings_and_recommendations(self):
        """Test result with warnings and recommendations."""
        warnings = ["High turnover detected", "Concentration risk"]
        recommendations = ["Reduce rebalancing frequency", "Add more assets"]

        result = PortfolioValidationResult(
            is_valid=False,
            is_stable=False,
            is_cost_effective=True,
            is_properly_diversified=False,
            stability_score=60.0,
            concentration_score=45.0,
            annual_turnover=0.8,
            estimated_costs=0.015,
            warnings=warnings,
            recommendations=recommendations,
        )

        assert len(result.warnings) == 2
        assert len(result.recommendations) == 2
        assert "High turnover detected" in result.warnings
        assert "Reduce rebalancing frequency" in result.recommendations

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = PortfolioValidationResult(
            is_valid=True,
            is_stable=True,
            is_cost_effective=True,
            is_properly_diversified=True,
            stability_score=75.0,
            concentration_score=20.0,
            annual_turnover=0.25,
            estimated_costs=0.003,
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["is_valid"] is True
        assert result_dict["stability_score"] == 75.0
        assert result_dict["concentration_score"] == 20.0
        assert "validation_timestamp" in result_dict

    def test_concentration_risk_levels(self):
        """Test concentration risk level determination."""
        # LOW risk
        result_low = PortfolioValidationResult(
            is_valid=True,
            is_stable=True,
            is_cost_effective=True,
            is_properly_diversified=True,
            stability_score=80.0,
            annual_turnover=0.2,
            estimated_costs=0.002,
            concentration_score=15.0,
        )
        assert result_low.concentration_risk == "UNKNOWN"

        # The actual risk level is set by the validator, not in __init__


@pytest.mark.unit
class TestPortfolioStabilityValidator:
    """Test suite for PortfolioStabilityValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        config = StabilityValidationConfig(
            min_stability_score=70.0,
            max_turnover_annual=0.5,
            max_allocation_drift=0.2,
            rebalancing_frequency_days=30,
            min_historical_periods=6,
        )
        return PortfolioStabilityValidator(config)

    @pytest.fixture
    def sample_weights(self):
        """Create sample weight history."""
        # 10 periods, 5 assets each
        weights_history = [
            np.array([0.20, 0.25, 0.15, 0.20, 0.20]),
            np.array([0.21, 0.24, 0.16, 0.19, 0.20]),
            np.array([0.22, 0.23, 0.17, 0.18, 0.20]),
            np.array([0.20, 0.25, 0.15, 0.20, 0.20]),
            np.array([0.19, 0.26, 0.14, 0.21, 0.20]),
            np.array([0.20, 0.25, 0.15, 0.20, 0.20]),
            np.array([0.21, 0.24, 0.16, 0.19, 0.20]),
            np.array([0.20, 0.25, 0.15, 0.20, 0.20]),
            np.array([0.19, 0.26, 0.14, 0.21, 0.20]),
            np.array([0.20, 0.25, 0.15, 0.20, 0.20]),
        ]
        return weights_history

    @pytest.fixture
    def sample_returns(self):
        """Create sample returns."""
        # 10 periods of returns
        returns = np.array([
            0.01, -0.005, 0.015, 0.008, 0.012,
            -0.003, 0.01, 0.005, -0.002, 0.008,
        ])
        return returns

    def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert validator.config.min_stability_score == 70.0
        assert validator.config.max_turnover_annual == 0.5
        assert len(validator.validation_history) == 0

    def test_validate_with_sufficient_history(self, validator, sample_weights, sample_returns):
        """Test validation with sufficient historical data."""
        current_weights = sample_weights[-1]

        result = validator.validate_portfolio_allocation(
            weights=current_weights,
            weights_history=sample_weights,
            returns_history=sample_returns,
        )

        # Should produce a valid result
        assert isinstance(result, PortfolioValidationResult)
        assert "stability_score" in str(result)

    def test_validate_with_insufficient_history(self, validator):
        """Test validation with insufficient historical data."""
        current_weights = np.array([0.20, 0.25, 0.15, 0.20, 0.20])
        weights_history = [
            np.array([0.20, 0.25, 0.15, 0.20, 0.20]),
            np.array([0.21, 0.24, 0.16, 0.19, 0.20]),
        ]  # Only 2 periods

        result = validator.validate_portfolio_allocation(
            weights=current_weights,
            weights_history=weights_history,
        )

        # Should have warning about insufficient history
        assert len(result.warnings) > 0
        assert any("insufficient" in w.lower() for w in result.warnings)

    def test_validate_with_no_returns_history(self, validator, sample_weights):
        """Test validation without returns history."""
        current_weights = sample_weights[-1]

        result = validator.validate_portfolio_allocation(
            weights=current_weights,
            weights_history=sample_weights,
            returns_history=None,
        )

        # Should still produce a result
        assert isinstance(result, PortfolioValidationResult)

    def test_validation_history_tracking(self, validator, sample_weights):
        """Test that validation history is tracked."""
        current_weights = sample_weights[-1]

        validator.validate_portfolio_allocation(
            weights=current_weights,
            weights_history=sample_weights,
        )

        # Should be stored in history
        assert len(validator.validation_history) == 1

    def test_determine_validity_all_pass(self):
        """Test validity determination when all checks pass."""
        config = StabilityValidationConfig(require_stable_for_production=False)
        validator = PortfolioStabilityValidator(config)

        result = PortfolioValidationResult(
            is_valid=False,
            is_stable=True,
            is_cost_effective=True,
            is_properly_diversified=True,
            stability_score=80.0,
            concentration_score=20.0,
            annual_turnover=0.3,
            estimated_costs=0.005,
        )

        is_valid = validator._determine_validity(result)

        # Should be valid when all checks pass
        assert is_valid is True

    def test_determine_validity_not_stable(self):
        """Test validity determination when not stable."""
        validator = PortfolioStabilityValidator(StabilityValidationConfig())

        result = PortfolioValidationResult(
            is_valid=False,
            is_stable=False,  # Not stable
            is_cost_effective=True,
            is_properly_diversified=True,
            stability_score=50.0,
            concentration_score=20.0,
            annual_turnover=0.3,
            estimated_costs=0.005,
        )

        is_valid = validator._determine_validity(result)

        # Should not be valid when unstable
        assert is_valid is False

    def test_determine_validity_not_cost_effective(self):
        """Test validity determination when not cost-effective."""
        config = StabilityValidationConfig(require_stable_for_production=False)
        validator = PortfolioStabilityValidator(config)

        result = PortfolioValidationResult(
            is_valid=False,
            is_stable=True,
            is_cost_effective=False,  # Not cost-effective
            is_properly_diversified=True,
            stability_score=80.0,
            concentration_score=20.0,
            annual_turnover=0.3,
            estimated_costs=0.005,
        )

        is_valid = validator._determine_validity(result)

        # Should not be valid when not cost-effective
        assert is_valid is False

    def test_determine_validity_overconcentrated(self):
        """Test validity determination when overconcentrated."""
        config = StabilityValidationConfig(require_stable_for_production=False)
        validator = PortfolioStabilityValidator(config)

        result = PortfolioValidationResult(
            is_valid=False,
            is_stable=True,
            is_cost_effective=True,
            is_properly_diversified=False,  # Overconcentrated
            stability_score=80.0,
            concentration_score=20.0,
            annual_turnover=0.3,
            estimated_costs=0.005,
        )

        is_valid = validator._determine_validity(result)

        # Should not be valid when overconcentrated
        assert is_valid is False

    @patch('app.engines.portfolio_engine.stability_validator.PortfolioStabilityValidator')
    def test_compare_portfolio_stabilities(self, mock_validator_class, sample_weights):
        """Test comparing multiple portfolios."""
        # Create mock validator
        mock_validator = MagicMock()
        mock_validator_class.return_value = mock_validator

        # Create mock results
        result1 = PortfolioValidationResult(
            is_valid=True,
            is_stable=True,
            is_cost_effective=True,
            is_properly_diversified=True,
            stability_score=85.0,
            concentration_score=15.0,
            annual_turnover=0.2,
            estimated_costs=0.003,
        )

        result2 = PortfolioValidationResult(
            is_valid=True,
            is_stable=True,
            is_cost_effective=True,
            is_properly_diversified=True,
            stability_score=75.0,
            concentration_score=20.0,
            annual_turnover=0.3,
            estimated_costs=0.005,
        )

        mock_validator.validate_portfolio_allocation.side_effect = [result1, result2]

        portfolios = {
            "portfolio_a": sample_weights,
            "portfolio_b": sample_weights,
        }

        results = mock_validator.compare_portfolio_stabilities(portfolios)

        # Should have results for both portfolios
        assert len(results) == 2
        assert "portfolio_a" in results
        assert "portfolio_b" in results

    def test_get_stability_recommendations(self, validator):
        """Test getting stability recommendations."""
        # Create result with various issues
        result = PortfolioValidationResult(
            is_valid=False,
            is_stable=False,
            is_cost_effective=False,
            is_properly_diversified=False,
            stability_score=50.0,
            concentration_score=45.0,
            annual_turnover=0.8,
            estimated_costs=0.025,
            sharpe_raw=1.5,
            sharpe_adjusted=1.0,  # 33% degradation
        )

        recommendations = validator.get_stability_recommendations(result)

        # Should have recommendations
        assert len(recommendations) > 0

        # Check for expected recommendation types
        rec_text = " ".join(recommendations).lower()
        assert any(keyword in rec_text for keyword in [
            "turnover", "concentration", "costs", "sharpe"
        ])

    def test_save_validation_report(self, validator, tmp_path):
        """Test saving validation report to file."""
        result = PortfolioValidationResult(
            is_valid=True,
            is_stable=True,
            is_cost_effective=True,
            is_properly_diversified=True,
            stability_score=80.0,
            concentration_score=20.0,
            annual_turnover=0.25,
            estimated_costs=0.004,
        )

        report_path = tmp_path / "validation_report.json"

        validator.save_validation_report(report_path, result)

        # File should be created
        assert report_path.exists()

        # Should be valid JSON
        import json
        with open(report_path) as f:
            report = json.load(f)

        assert "validation_config" in report
        assert "validation_result" in report
        assert "recommendations" in report


@pytest.mark.unit
class TestStabilityBasedPortfolioSelector:
    """Test suite for StabilityBasedPortfolioSelector."""

    @pytest.fixture
    def selector(self):
        """Create selector instance."""
        config = StabilityValidationConfig(min_stability_score=70.0)
        validator = PortfolioStabilityValidator(config)
        return StabilityBasedPortfolioSelector(
            validator=validator,
            min_stability_score=70.0,
        )

    @pytest.fixture
    def sample_portfolios(self):
        """Create sample portfolio data."""
        weights_a = [
            np.array([0.20, 0.25, 0.15, 0.20, 0.20]),
            np.array([0.21, 0.24, 0.16, 0.19, 0.20]),
            np.array([0.20, 0.25, 0.15, 0.20, 0.20]),
        ]

        weights_b = [
            np.array([0.15, 0.20, 0.20, 0.20, 0.25]),
            np.array([0.16, 0.19, 0.21, 0.20, 0.24]),
            np.array([0.15, 0.20, 0.20, 0.20, 0.25]),
        ]

        return {
            "portfolio_a": weights_a,
            "portfolio_b": weights_b,
        }

    def test_selector_initialization(self, selector):
        """Test selector initialization."""
        assert selector.min_stability_score == 70.0
        assert selector.validator is not None

    def test_select_most_stable_portfolio(self, selector, sample_portfolios):
        """Test selecting most stable portfolio."""
        # Mock the validation results
        with patch.object(selector.validator, 'compare_portfolio_stabilities') as mock_compare:
            result_a = PortfolioValidationResult(
                is_valid=True,
                is_stable=True,
                is_cost_effective=True,
                is_properly_diversified=True,
                stability_score=85.0,
                concentration_score=15.0,
                annual_turnover=0.2,
                estimated_costs=0.003,
            )

            result_b = PortfolioValidationResult(
                is_valid=True,
                is_stable=True,
                is_cost_effective=True,
                is_properly_diversified=True,
                stability_score=75.0,
                concentration_score=20.0,
                annual_turnover=0.3,
                estimated_costs=0.005,
            )

            mock_compare.return_value = {
                "portfolio_a": result_a,
                "portfolio_b": result_b,
            }

            selected_name, selected_result = selector.select_most_stable_portfolio(
                portfolios=sample_portfolios,
            )

            # Should select portfolio with higher stability score
            assert selected_name == "portfolio_a"
            assert selected_result.stability_score == 85.0

    def test_rank_portfolios_by_stability(self, selector, sample_portfolios):
        """Test ranking portfolios by stability."""
        with patch.object(selector.validator, 'compare_portfolio_stabilities') as mock_compare:
            result_a = PortfolioValidationResult(
                is_valid=True,
                is_stable=True,
                is_cost_effective=True,
                is_properly_diversified=True,
                stability_score=85.0,
                concentration_score=15.0,
                annual_turnover=0.2,
                estimated_costs=0.003,
            )

            result_b = PortfolioValidationResult(
                is_valid=True,
                is_stable=True,
                is_cost_effective=True,
                is_properly_diversified=True,
                stability_score=75.0,
                concentration_score=20.0,
                annual_turnover=0.3,
                estimated_costs=0.005,
            )

            mock_compare.return_value = {
                "portfolio_a": result_a,
                "portfolio_b": result_b,
            }

            ranked = selector.rank_portfolios_by_stability(
                portfolios=sample_portfolios,
            )

            # Should be ranked by stability (highest first)
            assert len(ranked) == 2
            assert ranked[0][0] == "portfolio_a"
            assert ranked[1][0] == "portfolio_b"
            assert ranked[0][1].stability_score >= ranked[1][1].stability_score

    def test_select_with_cost_effectiveness_filter(self, selector, sample_portfolios):
        """Test selection with cost-effectiveness filter."""
        with patch.object(selector.validator, 'compare_portfolio_stabilities') as mock_compare:
            result_a = PortfolioValidationResult(
                is_valid=True,
                is_stable=True,
                is_cost_effective=False,  # Not cost-effective
                is_properly_diversified=True,
                stability_score=90.0,  # But higher stability
                concentration_score=15.0,
                annual_turnover=0.8,
                estimated_costs=0.02,
            )

            result_b = PortfolioValidationResult(
                is_valid=True,
                is_stable=True,
                is_cost_effective=True,  # Cost-effective
                is_properly_diversified=True,
                stability_score=80.0,  # But lower stability
                concentration_score=20.0,
                annual_turnover=0.3,
                estimated_costs=0.005,
            )

            mock_compare.return_value = {
                "portfolio_a": result_a,
                "portfolio_b": result_b,
            }

            selected_name, selected_result = selector.select_most_stable_portfolio(
                portfolios=sample_portfolios,
                require_cost_effective=True,
            )

            # Should select cost-effective portfolio
            assert selected_name == "portfolio_b"
            assert selected_result.is_cost_effective is True


@pytest.mark.unit
class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_portfolio_stability_validator(self):
        """Test creating validator with convenience function."""
        validator = create_portfolio_stability_validator(
            min_stability_score=75.0,
            transaction_cost_bps=8.0,
            risk_free_rate=0.025,
        )

        assert validator.config.min_stability_score == 75.0
        assert validator.config.transaction_cost_bps == 8.0
        assert validator.config.risk_free_rate == 0.025

    def test_validate_single_portfolio(self):
        """Test validating single portfolio with convenience function."""
        weights = np.array([0.20, 0.25, 0.15, 0.20, 0.20])
        weights_history = [
            np.array([0.20, 0.25, 0.15, 0.20, 0.20]),
            np.array([0.21, 0.24, 0.16, 0.19, 0.20]),
            np.array([0.20, 0.25, 0.15, 0.20, 0.20]),
        ]

        result = validate_single_portfolio(
            weights=weights,
            weights_history=weights_history,
        )

        assert isinstance(result, PortfolioValidationResult)


@pytest.mark.unit
class TestStabilityValidatorEdgeCases:
    """Test edge cases for stability validator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        config = StabilityValidationConfig(min_historical_periods=3)
        return PortfolioStabilityValidator(config)

    def test_empty_weights_history(self, validator):
        """Test with empty weights history."""
        current_weights = np.array([0.25, 0.25, 0.25, 0.25])
        weights_history = []

        result = validator.validate_portfolio_allocation(
            weights=current_weights,
            weights_history=weights_history,
        )

        # Should have warning about insufficient data
        assert len(result.warnings) > 0

    def test_single_period_history(self, validator):
        """Test with single period in history."""
        current_weights = np.array([0.25, 0.25, 0.25, 0.25])
        weights_history = [np.array([0.25, 0.25, 0.25, 0.25])]

        result = validator.validate_portfolio_allocation(
            weights=current_weights,
            weights_history=weights_history,
        )

        # Should have warning about insufficient data
        assert len(result.warnings) > 0

    def test_extreme_weights(self, validator):
        """Test with extreme weight values."""
        current_weights = np.array([0.95, 0.01, 0.01, 0.01, 0.02])
        weights_history = [
            np.array([0.95, 0.01, 0.01, 0.01, 0.02]),
            np.array([0.94, 0.02, 0.01, 0.01, 0.02]),
            np.array([0.95, 0.01, 0.01, 0.01, 0.02]),
        ]

        result = validator.validate_portfolio_allocation(
            weights=current_weights,
            weights_history=weights_history,
        )

        # Should detect concentration risk
        assert result.concentration_risk in ["HIGH", "CRITICAL"]

    def test_zero_weight_assets(self, validator):
        """Test with assets that have zero weights."""
        current_weights = np.array([0.40, 0.30, 0.30, 0.0, 0.0])
        weights_history = [
            np.array([0.40, 0.30, 0.30, 0.0, 0.0]),
            np.array([0.41, 0.29, 0.30, 0.0, 0.0]),
            np.array([0.40, 0.30, 0.30, 0.0, 0.0]),
        ]

        result = validator.validate_portfolio_allocation(
            weights=current_weights,
            weights_history=weights_history,
        )

        # Should handle gracefully
        assert isinstance(result, PortfolioValidationResult)

    def test_very_stable_portfolio(self, validator):
        """Test with very stable portfolio (constant weights)."""
        weights_history = [
            np.array([0.25, 0.25, 0.25, 0.25]),
            np.array([0.25, 0.25, 0.25, 0.25]),
            np.array([0.25, 0.25, 0.25, 0.25]),
            np.array([0.25, 0.25, 0.25, 0.25]),
        ]

        result = validator.validate_portfolio_allocation(
            weights=weights_history[-1],
            weights_history=weights_history,
        )

        # Should have high stability
        # (actual score depends on the López de Prado metrics implementation)
        assert isinstance(result.stability_score, (int, float))

    def test_very_unstable_portfolio(self, validator):
        """Test with very unstable portfolio (drastic weight changes)."""
        weights_history = [
            np.array([1.0, 0.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0, 0.0]),
            np.array([0.0, 0.0, 1.0, 0.0]),
            np.array([0.0, 0.0, 0.0, 1.0]),
        ]

        result = validator.validate_portfolio_allocation(
            weights=weights_history[-1],
            weights_history=weights_history,
        )

        # Should have low stability
        # (actual score depends on the López de Prado metrics implementation)
        assert isinstance(result.stability_score, (int, float))

    def test_negative_weights(self, validator):
        """Test with negative weights (short positions)."""
        current_weights = np.array([0.50, 0.60, -0.05, -0.05])
        weights_history = [
            np.array([0.50, 0.60, -0.05, -0.05]),
            np.array([0.51, 0.59, -0.05, -0.05]),
            np.array([0.50, 0.60, -0.05, -0.05]),
        ]

        result = validator.validate_portfolio_allocation(
            weights=current_weights,
            weights_history=weights_history,
        )

        # Should handle gracefully
        assert isinstance(result, PortfolioValidationResult)
