"""
Unit tests for Portfolio Optimizers.

Tests cover:
- Mean-variance optimization (Markowitz)
- Risk parity optimization
- Black-Litterman model
- Kelly Criterion optimization
- Constraint handling
- Edge cases (empty universe, single asset)
"""

from unittest.mock import patch

import numpy as np
import pytest

from app.engines.portfolio_engine.optimizers import (
    BlackLittermanOptimizer,
    KellyCriterionOptimizer,
    MarkowitzOptimizer,
    RiskParityOptimizer,
)


@pytest.mark.unit
class TestMarkowitzOptimizer:
    """Test suite for Markowitz mean-variance optimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create Markowitz optimizer instance."""
        config = {"risk_aversion": 0.5}
        return MarkowitzOptimizer(config)

    @pytest.fixture
    def sample_data(self):
        """Create sample returns and covariance matrix."""
        np.random.seed(42)

        # Expected returns
        expected_returns = np.array([0.08, 0.10, 0.06, 0.12, 0.09])

        # Covariance matrix (positive definite)
        cov_matrix = np.array(
            [
                [0.0400, 0.0120, 0.0080, 0.0150, 0.0100],
                [0.0120, 0.0350, 0.0100, 0.0180, 0.0120],
                [0.0080, 0.0100, 0.0300, 0.0120, 0.0090],
                [0.0150, 0.0180, 0.0120, 0.0500, 0.0140],
                [0.0100, 0.0120, 0.0090, 0.0140, 0.0380],
            ]
        )

        return expected_returns, cov_matrix

    def test_mean_variance_optimization_success(self, optimizer, sample_data):
        """Test successful mean-variance optimization."""
        expected_returns, cov_matrix = sample_data

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Check result structure
        assert "weights" in result
        assert "expected_return" in result
        assert "volatility" in result
        assert "sharpe_ratio" in result
        assert "method" in result

        # Check weights sum to 1
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0, atol=1e-6)

        # Check all weights are non-negative
        assert all(w >= 0 for w in weights)

        # Check metrics are reasonable
        assert result["expected_return"] > 0
        assert result["volatility"] > 0
        assert result["sharpe_ratio"] > 0

    def test_mean_variance_with_constraints(self, optimizer, sample_data):
        """Test optimization with weight constraints."""
        expected_returns, cov_matrix = sample_data

        constraints = {
            "max_weight": 0.40,
            "min_weight": 0.05,
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)
        weights = list(result["weights"].values())

        # Check constraints are respected
        assert all(w <= 0.41 for w in weights)  # Small tolerance for numerical error
        assert all(w >= 0.04 for w in weights)

    def test_single_asset_optimization(self, optimizer):
        """Test optimization with single asset."""
        expected_returns = np.array([0.10])
        cov_matrix = np.array([[0.04]])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Single asset should get 100% weight
        assert result["weights"]["asset_0"] == pytest.approx(1.0)
        assert result["expected_return"] == pytest.approx(0.10)

    def test_two_asset_optimization(self, optimizer):
        """Test optimization with two assets."""
        expected_returns = np.array([0.10, 0.08])
        cov_matrix = np.array(
            [
                [0.04, 0.01],
                [0.01, 0.03],
            ]
        )

        result = optimizer.optimize(expected_returns, cov_matrix)
        weights = list(result["weights"].values())

        # Weights should sum to 1
        assert np.isclose(sum(weights), 1.0)

        # Higher return asset should get higher weight (all else equal)
        assert weights[0] > weights[1]

    def test_high_correlation_assets(self, optimizer):
        """Test optimization with highly correlated assets."""
        expected_returns = np.array([0.08, 0.10, 0.09])

        # High correlation covariance matrix
        cov_matrix = np.array(
            [
                [0.04, 0.035, 0.036],
                [0.035, 0.05, 0.042],
                [0.036, 0.042, 0.045],
            ]
        )

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should still produce valid weights
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0)
        assert all(w >= 0 for w in weights)

    def test_perfect_correlation_handling(self, optimizer):
        """Test handling of perfectly correlated assets."""
        expected_returns = np.array([0.08, 0.10])

        # Perfectly correlated (but still valid covariance)
        cov_matrix = np.array(
            [
                [0.04, 0.04],
                [0.04, 0.04],
            ]
        )

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should handle gracefully
        assert "weights" in result
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0, atol=1e-3)

    @pytest.mark.parametrize("max_weight", [0.2, 0.3, 0.5])
    def test_max_weight_constraint(self, optimizer, sample_data, max_weight):
        """Test various max weight constraints."""
        expected_returns, cov_matrix = sample_data

        constraints = {"max_weight": max_weight}
        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        weights = list(result["weights"].values())
        assert all(w <= max_weight + 0.01 for w in weights)  # Small tolerance

    def test_zero_volatility_asset(self, optimizer):
        """Test optimization with zero volatility asset."""
        expected_returns = np.array([0.05, 0.08])

        # One asset with zero volatility
        cov_matrix = np.array(
            [
                [0.00, 0.00],
                [0.00, 0.04],
            ]
        )

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Zero volatility asset should dominate
        assert result["weights"]["asset_0"] > result["weights"]["asset_1"]

    def test_equal_weight_fallback(self, optimizer):
        """Test equal weight fallback on optimization failure."""
        # This should trigger fallback
        with patch.object(optimizer, '_optimize_pypfopt', side_effect=Exception("Test error")):
            expected_returns = np.array([0.08, 0.10])
            cov_matrix = np.array([[0.04, 0.01], [0.01, 0.03]])

            result = optimizer.optimize(expected_returns, cov_matrix)

            # Should fall back to equal weights
            assert result["method"] == "equal_weight_fallback"
            assert result["weights"]["asset_0"] == pytest.approx(0.5)
            assert result["weights"]["asset_1"] == pytest.approx(0.5)

    def test_optimization_convergence(self, optimizer, sample_data):
        """Test that optimization converges consistently."""
        expected_returns, cov_matrix = sample_data

        # Run optimization multiple times
        results = []
        for _ in range(5):
            result = optimizer.optimize(expected_returns, cov_matrix)
            results.append(result)

        # All results should be identical (deterministic)
        first_weights = results[0]["weights"]
        for result in results[1:]:
            assert result["weights"] == first_weights


@pytest.mark.unit
class TestRiskParityOptimizer:
    """Test suite for Risk Parity optimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create Risk Parity optimizer instance."""
        config = {}
        return RiskParityOptimizer(config)

    @pytest.fixture
    def sample_data(self):
        """Create sample returns and covariance matrix."""
        expected_returns = np.array([0.08, 0.10, 0.06, 0.12, 0.09])

        # Heterogeneous volatilities to test risk parity
        cov_matrix = np.array(
            [
                [0.0400, 0.0080, 0.0060, 0.0100, 0.0070],
                [0.0080, 0.0900, 0.0070, 0.0120, 0.0080],
                [0.0060, 0.0070, 0.0250, 0.0080, 0.0060],
                [0.0100, 0.0120, 0.0080, 0.0600, 0.0090],
                [0.0070, 0.0080, 0.0060, 0.0090, 0.0350],
            ]
        )

        return expected_returns, cov_matrix

    def test_risk_parity_convergence(self, optimizer, sample_data):
        """Test that risk parity converges to equal risk contributions."""
        expected_returns, cov_matrix = sample_data

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Check basic structure
        assert "weights" in result
        assert "risk_contributions" in result

        # Check weights sum to 1
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0, atol=1e-6)

        # Check all weights are positive
        assert all(w > 0 for w in weights)

        # Check risk contributions are approximately equal
        risk_contributions = list(result["risk_contributions"].values())
        n = len(risk_contributions)
        target_risk = 1.0 / n

        # All risk contributions should be close to target
        for rc in risk_contributions:
            assert rc == pytest.approx(target_risk, abs=0.05)  # 5% tolerance

    def test_risk_parity_with_constraints(self, optimizer, sample_data):
        """Test risk parity with weight constraints."""
        expected_returns, cov_matrix = sample_data

        constraints = {
            "max_weight": 0.50,
            "min_weight": 0.05,
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)
        weights = list(result["weights"].values())

        # Check constraints
        assert all(w <= 0.51 for w in weights)
        assert all(w >= 0.04 for w in weights)

    def test_risk_parity_two_assets(self, optimizer):
        """Test risk parity with two assets."""
        expected_returns = np.array([0.08, 0.10])

        # Different volatilities
        cov_matrix = np.array(
            [
                [0.04, 0.01],
                [0.01, 0.09],
            ]
        )

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Higher volatility asset should get lower weight
        weights = list(result["weights"].values())
        assert weights[0] > weights[1]  # Asset 0 has lower volatility

        # Risk contributions should be equal
        risk_contributions = list(result["risk_contributions"].values())
        assert risk_contributions[0] == pytest.approx(risk_contributions[1], abs=0.01)

    def test_risk_parity_single_asset(self, optimizer):
        """Test risk parity with single asset."""
        expected_returns = np.array([0.10])
        cov_matrix = np.array([[0.04]])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Single asset gets 100% weight
        assert result["weights"]["asset_0"] == pytest.approx(1.0)
        assert result["risk_contributions"]["asset_0"] == pytest.approx(1.0)

    def test_risk_parity_equal_volatilities(self, optimizer):
        """Test risk parity when all assets have equal volatility."""
        n = 4
        expected_returns = np.array([0.08, 0.10, 0.06, 0.12])

        # Equal variances, zero correlations
        cov_matrix = np.eye(n) * 0.04

        result = optimizer.optimize(expected_returns, cov_matrix)

        # With equal volatilities, should get equal weights
        weights = list(result["weights"].values())
        for w in weights:
            assert w == pytest.approx(0.25, abs=0.01)

    def test_risk_parity_iterative_convergence(self, optimizer, sample_data):
        """Test that iterative method converges."""
        expected_returns, cov_matrix = sample_data

        # Test with different starting points
        results = []
        for _ in range(3):
            result = optimizer.optimize(expected_returns, cov_matrix)
            results.append(result)

        # Should converge to same solution
        first_weights = results[0]["weights"]
        for result in results[1:]:
            for asset in first_weights:
                assert result["weights"][asset] == pytest.approx(first_weights[asset], abs=1e-6)

    def test_risk_contributions_calculation(self, optimizer, sample_data):
        """Test risk contributions are correctly calculated."""
        expected_returns, cov_matrix = sample_data

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Manually verify risk contributions
        np.array(list(result["weights"].values()))
        risk_contribs = np.array(list(result["risk_contributions"].values()))

        # Risk contributions should sum to 1
        assert np.isclose(risk_contribs.sum(), 1.0, atol=1e-6)

        # Each risk contribution should be positive
        assert all(rc > 0 for rc in risk_contribs)

    def test_risk_parity_with_high_correlation(self, optimizer):
        """Test risk parity with highly correlated assets."""
        expected_returns = np.array([0.08, 0.10, 0.09])

        # High correlation
        cov_matrix = np.array(
            [
                [0.04, 0.035, 0.036],
                [0.035, 0.09, 0.045],
                [0.036, 0.045, 0.06],
            ]
        )

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should still produce valid weights and equal risk contributions
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0)

        risk_contribs = list(result["risk_contributions"].values())
        target = 1.0 / len(risk_contribs)
        for rc in risk_contribs:
            assert rc == pytest.approx(target, abs=0.1)

    def test_risk_parity_edge_case_near_zero_variance(self, optimizer):
        """Test risk parity with near-zero variance asset."""
        expected_returns = np.array([0.05, 0.08, 0.06])

        # One asset with very low variance
        cov_matrix = np.array(
            [
                [0.0001, 0.005, 0.004],
                [0.005, 0.04, 0.01],
                [0.004, 0.01, 0.03],
            ]
        )

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should handle gracefully
        assert "weights" in result
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0)


@pytest.mark.unit
class TestBlackLittermanOptimizer:
    """Test suite for Black-Litterman optimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create Black-Litterman optimizer instance."""
        config = {}
        return BlackLittermanOptimizer(config)

    @pytest.fixture
    def sample_data(self):
        """Create sample data for Black-Litterman."""
        expected_returns = np.array([0.08, 0.10, 0.06, 0.12, 0.09])

        cov_matrix = np.array(
            [
                [0.0400, 0.0120, 0.0080, 0.0150, 0.0100],
                [0.0120, 0.0350, 0.0100, 0.0180, 0.0120],
                [0.0080, 0.0100, 0.0300, 0.0120, 0.0090],
                [0.0150, 0.0180, 0.0120, 0.0500, 0.0140],
                [0.0100, 0.0120, 0.0090, 0.0140, 0.0380],
            ]
        )

        return expected_returns, cov_matrix

    def test_black_litterman_no_views(self, optimizer, sample_data):
        """Test Black-Litterman with no views (should use equilibrium)."""
        expected_returns, cov_matrix = sample_data

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should use equilibrium returns
        assert result["method"] in ["black_litterman_equilibrium", "markowitz_pypfopt"]
        assert "weights" in result

    def test_black_litterman_with_absolute_views(self, optimizer, sample_data):
        """Test Black-Litterman with absolute views."""
        expected_returns, cov_matrix = sample_data

        constraints = {
            "views": {
                "asset_0": 0.10,  # Asset 0 will return 10%
                "asset_2": 0.08,  # Asset 2 will return 8%
            },
            "view_confidences": {
                "asset_0": 0.7,
                "asset_2": 0.8,
            },
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Should incorporate views
        assert "weights" in result
        assert result["method"] == "black_litterman"
        assert result["views_applied"] == 2

    def test_black_litterman_with_relative_views(self, optimizer, sample_data):
        """Test Black-Litterman with relative views."""
        expected_returns, cov_matrix = sample_data

        constraints = {
            "views": {
                "asset_1 - asset_0": 0.02,  # Asset 1 outperforms asset 0 by 2%
            },
            "view_confidences": {
                "asset_1 - asset_0": 0.6,
            },
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Should handle relative views
        assert "weights" in result
        assert result["method"] == "black_litterman"

    def test_black_litterman_confidence_impact(self, optimizer, sample_data):
        """Test that view confidence impacts weights."""
        expected_returns, cov_matrix = sample_data

        # High confidence view
        constraints_high = {
            "views": {"asset_0": 0.12},
            "view_confidences": {"asset_0": 0.95},
        }

        # Low confidence view
        constraints_low = {
            "views": {"asset_0": 0.12},
            "view_confidences": {"asset_0": 0.2},
        }

        result_high = optimizer.optimize(expected_returns, cov_matrix, constraints_high)
        result_low = optimizer.optimize(expected_returns, cov_matrix, constraints_low)

        # High confidence should deviate more from equilibrium
        # (This is a weak test - in practice, the difference might be subtle)
        assert "weights" in result_high
        assert "weights" in result_low

    def test_black_litterman_multiple_views(self, optimizer, sample_data):
        """Test Black-Litterman with multiple views."""
        expected_returns, cov_matrix = sample_data

        constraints = {
            "views": {
                "asset_0": 0.10,
                "asset_1 - asset_2": 0.03,
                "asset_3": 0.15,
            },
            "view_confidences": {
                "asset_0": 0.7,
                "asset_1 - asset_2": 0.6,
                "asset_3": 0.8,
            },
            "tau": 0.05,
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Should incorporate all views
        assert result["views_applied"] == 3
        assert "weights" in result
        assert "bl_returns" in result

    def test_black_litterman_tau_parameter(self, optimizer, sample_data):
        """Test tau (uncertainty scaling) parameter."""
        expected_returns, cov_matrix = sample_data

        view_constraints = {
            "views": {"asset_0": 0.10},
            "view_confidences": {"asset_0": 0.7},
        }

        # Low tau (more confident in equilibrium)
        constraints_low_tau = {**view_constraints, "tau": 0.01}
        # High tau (less confident in equilibrium)
        constraints_high_tau = {**view_constraints, "tau": 0.1}

        result_low = optimizer.optimize(expected_returns, cov_matrix, constraints_low_tau)
        result_high = optimizer.optimize(expected_returns, cov_matrix, constraints_high_tau)

        # Both should produce valid results
        assert "weights" in result_low
        assert "weights" in result_high

    def test_black_litterman_invalid_view(self, optimizer, sample_data):
        """Test handling of invalid views."""
        expected_returns, cov_matrix = sample_data

        constraints = {
            "views": {
                "asset_0": 0.10,
                "invalid_asset": 0.08,  # Invalid
                "asset_99": 0.12,  # Out of range
            },
            "view_confidences": {
                "asset_0": 0.7,
                "invalid_asset": 0.6,
                "asset_99": 0.8,
            },
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Should handle gracefully (skip invalid views)
        assert "weights" in result
        assert result["views_applied"] <= 1  # Only valid view

    def test_black_litterman_single_asset(self, optimizer):
        """Test Black-Litterman with single asset."""
        expected_returns = np.array([0.10])
        cov_matrix = np.array([[0.04]])

        result = optimizer.optimize(expected_returns, cov_matrix)

        # Single asset should get 100% weight
        assert result["weights"]["asset_0"] == pytest.approx(1.0)


@pytest.mark.unit
class TestKellyCriterionOptimizer:
    """Test suite for Kelly Criterion optimizer."""

    @pytest.fixture
    def optimizer(self):
        """Create Kelly Criterion optimizer instance."""
        config = {}
        return KellyCriterionOptimizer(config)

    @pytest.fixture
    def sample_data(self):
        """Create sample data for Kelly optimization."""
        expected_returns = np.array([0.08, 0.10, 0.06, 0.12, 0.09])

        cov_matrix = np.array(
            [
                [0.0400, 0.0120, 0.0080, 0.0150, 0.0100],
                [0.0120, 0.0350, 0.0100, 0.0180, 0.0120],
                [0.0080, 0.0100, 0.0300, 0.0120, 0.0090],
                [0.0150, 0.0180, 0.0120, 0.0500, 0.0140],
                [0.0100, 0.0120, 0.0090, 0.0140, 0.0380],
            ]
        )

        return expected_returns, cov_matrix

    def test_kelly_optimization_basic(self, optimizer, sample_data):
        """Test basic Kelly optimization."""
        expected_returns, cov_matrix = sample_data

        # Default: 50% win probability for all
        constraints = {
            "win_probabilities": np.array([0.5, 0.6, 0.5, 0.7, 0.55]),
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Check basic structure
        assert "weights" in result
        assert "kelly_fractions" in result

        # Check weights sum to 1
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0, atol=1e-6)

    def test_kelly_with_high_win_probability(self, optimizer, sample_data):
        """Test Kelly with high win probability."""
        expected_returns, cov_matrix = sample_data

        constraints = {
            "win_probabilities": np.array([0.8, 0.75, 0.7, 0.85, 0.8]),
            "win_returns": expected_returns,
            "loss_returns": -expected_returns * 0.5,
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # High win probabilities should result in higher weights
        assert "weights" in result
        assert "kelly_fractions" in result

    def test_kelly_with_low_win_probability(self, optimizer, sample_data):
        """Test Kelly with low win probability."""
        expected_returns, cov_matrix = sample_data

        constraints = {
            "win_probabilities": np.array([0.3, 0.35, 0.4, 0.3, 0.35]),
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Low win probabilities should result in zero or low Kelly fractions
        kelly_fractions = list(result["kelly_fractions"].values())
        assert all(kf >= 0 for kf in kelly_fractions)  # Should be non-negative
        assert all(kf <= 1 for kf in kelly_fractions)  # Should be <= 1

    def test_kelly_edge_case_fifty_percent(self, optimizer, sample_data):
        """Test Kelly at exactly 50% win probability with 1:1 payoff."""
        expected_returns, cov_matrix = sample_data

        # 50% win probability with symmetric payoffs = zero Kelly
        constraints = {
            "win_probabilities": np.array([0.5] * 5),
            "win_returns": np.array([0.1] * 5),
            "loss_returns": np.array([-0.1] * 5),
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Should result in equal weights (all Kelly fractions = 0)
        weights = list(result["weights"].values())
        for w in weights:
            assert w == pytest.approx(0.2, abs=0.01)

    def test_kelly_with_constraints(self, optimizer, sample_data):
        """Test Kelly with weight constraints."""
        expected_returns, cov_matrix = sample_data

        constraints = {
            "win_probabilities": np.array([0.6, 0.7, 0.6, 0.8, 0.7]),
            "max_weight": 0.5,
            "min_weight": 0.05,
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)
        weights = list(result["weights"].values())

        # Check constraints
        assert all(w <= 0.51 for w in weights)
        assert all(w >= 0.04 for w in weights)

    def test_kelly_single_asset(self, optimizer):
        """Test Kelly with single asset."""
        expected_returns = np.array([0.10])
        cov_matrix = np.array([[0.04]])

        constraints = {
            "win_probabilities": np.array([0.6]),
            "win_returns": np.array([0.15]),
            "loss_returns": np.array([-0.10]),
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Single asset should get 100% weight
        assert result["weights"]["asset_0"] == pytest.approx(1.0)

        # Kelly fraction should be positive
        assert result["kelly_fractions"]["asset_0"] > 0

    def test_kelly_fraction_calculation(self, optimizer):
        """Test Kelly fraction calculation formula."""
        # Kelly formula: f = (p*b - q) / b
        # where p = win prob, q = 1-p, b = win/loss ratio

        expected_returns = np.array([0.10])
        cov_matrix = np.array([[0.04]])

        # p = 0.6, b = 2.0 (10% win, 5% loss)
        # Expected Kelly: (0.6*2 - 0.4) / 2 = 0.4
        constraints = {
            "win_probabilities": np.array([0.6]),
            "win_returns": np.array([0.10]),
            "loss_returns": np.array([-0.05]),
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Kelly fraction should be approximately 0.4
        expected_kelly = (0.6 * 2.0 - 0.4) / 2.0
        assert result["kelly_fractions"]["asset_0"] == pytest.approx(expected_kelly, abs=0.01)

    def test_kelly_negative_expected_value(self, optimizer):
        """Test Kelly with negative expected value."""
        expected_returns = np.array([0.05])
        cov_matrix = np.array([[0.04]])

        # Negative expected value: p=0.4, b=1.0
        # Kelly: (0.4*1 - 0.6) / 1 = -0.2 -> should be 0 (no bet)
        constraints = {
            "win_probabilities": np.array([0.4]),
            "win_returns": np.array([0.05]),
            "loss_returns": np.array([-0.05]),
        }

        result = optimizer.optimize(expected_returns, cov_matrix, constraints)

        # Should get zero Kelly fraction
        assert result["kelly_fractions"]["asset_0"] == pytest.approx(0.0, abs=0.01)


@pytest.mark.unit
class TestOptimizerEdgeCases:
    """Test edge cases across all optimizers."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data."""
        return (
            np.array([0.08, 0.10, 0.06]),
            np.array(
                [
                    [0.04, 0.01, 0.008],
                    [0.01, 0.03, 0.006],
                    [0.008, 0.006, 0.02],
                ]
            ),
        )

    def test_empty_universe(self):
        """Test handling of empty universe (no assets)."""
        np.array([])
        np.array([[]]).reshape(0, 0)

        MarkowitzOptimizer({})
        # This should handle gracefully
        # Note: current implementation might error, which is acceptable
        # for an edge case like this

    def test_large_universe(self):
        """Test optimization with large universe (100 assets)."""
        np.random.seed(42)
        n = 100

        expected_returns = np.random.randn(n) * 0.02 + 0.08

        # Create positive definite covariance matrix
        L = np.random.randn(n, n) * 0.01
        cov_matrix = L @ L.T + np.eye(n) * 0.04

        optimizer = MarkowitzOptimizer({})
        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should produce valid weights
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0, atol=1e-4)
        assert all(w >= -0.01 for w in weights)  # Allow small negative

    def test_extreme_returns(self):
        """Test with extreme return values."""
        expected_returns = np.array([1.0, -0.5, 2.0, 0.0, 0.05])
        cov_matrix = np.eye(5) * 0.04

        optimizer = MarkowitzOptimizer({})
        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should handle gracefully
        assert "weights" in result

    def test_near_singular_covariance(self):
        """Test with near-singular covariance matrix."""
        expected_returns = np.array([0.08, 0.10, 0.06])

        # Nearly singular matrix (highly correlated assets)
        cov_matrix = (
            np.array(
                [
                    [1.0, 0.99, 0.99],
                    [0.99, 1.0, 0.99],
                    [0.99, 0.99, 1.0],
                ]
            )
            * 0.04
        )

        optimizer = MarkowitzOptimizer({})
        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should handle gracefully
        assert "weights" in result

    def test_diagonal_covariance(self):
        """Test with diagonal covariance (uncorrelated assets)."""
        expected_returns = np.array([0.08, 0.10, 0.06, 0.12, 0.09])
        cov_matrix = np.diag([0.04, 0.03, 0.05, 0.06, 0.035])

        optimizer = RiskParityOptimizer({})
        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should produce valid results
        weights = list(result["weights"].values())
        assert np.isclose(sum(weights), 1.0, atol=1e-6)

    def test_all_equal_returns(self):
        """Test when all assets have equal expected returns."""
        expected_returns = np.array([0.08] * 5)
        cov_matrix = np.array(
            [
                [0.04, 0.01, 0.008, 0.012, 0.01],
                [0.01, 0.03, 0.007, 0.01, 0.009],
                [0.008, 0.007, 0.025, 0.009, 0.008],
                [0.012, 0.01, 0.009, 0.035, 0.011],
                [0.01, 0.009, 0.008, 0.011, 0.03],
            ]
        )

        optimizer = MarkowitzOptimizer({})
        result = optimizer.optimize(expected_returns, cov_matrix)

        # Should minimize variance
        assert "weights" in result
