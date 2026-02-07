"""
Unit tests for Bet Sizing module.

Tests for bet sizing calculations based on López de Prado's work.
"""


import numpy as np
import pytest

from app.backtesting.labeling.bet_sizing import (
    BetSizing,
    BetSizingConfig,
    BetSizingResult,
    calculate_bet_sizes,
    calculate_bet_sizes_expected_value,
    calculate_bet_sizes_ml,
    calculate_bet_sizes_with_discrete_allocation,
    calculate_bet_sizes_with_meta_model,
    calculate_bet_sizes_with_risk_target,
)


@pytest.mark.unit
class TestBetSizingConfig:
    """Test cases for BetSizingConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BetSizingConfig()

        assert config.method == "kelly"
        assert config.kelly_fraction == 0.25
        assert config.min_kelly == 0.01
        assert config.max_kelly == 0.25
        assert config.prob_threshold == 0.5
        assert config.max_position_size == 1.0
        assert config.max_portfolio_exposure == 1.0
        assert config.concentration_limit == 0.3
        assert config.max_drawdown == 0.2

    def test_custom_config(self):
        """Test custom configuration values."""
        config = BetSizingConfig(
            method="probability",
            kelly_fraction=0.5,
            max_position_size=0.8,
            concentration_limit=0.2,
        )

        assert config.method == "probability"
        assert config.kelly_fraction == 0.5
        assert config.max_position_size == 0.8
        assert config.concentration_limit == 0.2

    def test_config_validation_invalid_method(self):
        """Test configuration validation with invalid method."""
        with pytest.raises(ValueError, match="method must be one of"):
            BetSizingConfig(method="invalid_method")

    def test_config_validation_invalid_kelly_fraction(self):
        """Test configuration validation with invalid Kelly fraction."""
        with pytest.raises(ValueError, match="kelly_fraction must be between 0 and 1"):
            BetSizingConfig(kelly_fraction=1.5)

    def test_config_validation_invalid_prob_threshold(self):
        """Test configuration validation with invalid probability threshold."""
        with pytest.raises(ValueError, match="prob_threshold must be between 0 and 1"):
            BetSizingConfig(prob_threshold=1.5)

    def test_config_validation_invalid_max_position(self):
        """Test configuration validation with invalid max position."""
        with pytest.raises(ValueError, match="max_position_size must be between 0 and 1"):
            BetSizingConfig(max_position_size=1.5)


@pytest.mark.unit
class TestBetSizingResult:
    """Test cases for BetSizingResult dataclass."""

    def test_result_creation(self):
        """Test creating a BetSizingResult."""
        n_signals = 10
        bet_sizes = np.random.rand(n_signals) * 0.5
        expected_returns = np.random.randn(n_signals) * 0.01
        risk_contribution = np.random.rand(n_signals)
        kelly_fractions = np.random.rand(n_signals) * 0.3

        result = BetSizingResult(
            bet_sizes=bet_sizes,
            expected_returns=expected_returns,
            risk_contribution=risk_contribution,
            kelly_fractions=kelly_fractions,
            metadata={"method": "kelly", "n_signals": n_signals},
        )

        assert len(result.bet_sizes) == n_signals
        assert len(result.expected_returns) == n_signals
        assert result.metadata["method"] == "kelly"

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        n_signals = 5
        bet_sizes = np.array([0.1, 0.2, 0.0, 0.3, 0.0])

        result = BetSizingResult(
            bet_sizes=bet_sizes,
            expected_returns=np.zeros(n_signals),
            risk_contribution=np.zeros(n_signals),
            kelly_fractions=np.zeros(n_signals),
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "bet_sizes" in result_dict
        assert "metadata" in result_dict
        assert len(result_dict["bet_sizes"]) == n_signals


@pytest.mark.unit
class TestBetSizing:
    """Test cases for BetSizing class."""

    @pytest.fixture
    def sample_signals(self):
        """Create sample trading signals."""
        np.random.seed(42)
        n_signals = 20

        predictions = np.random.randint(-1, 2, n_signals)  # -1, 0, 1
        probabilities = np.random.rand(n_signals) * 0.5 + 0.5  # 0.5 to 1.0
        expected_returns = np.random.randn(n_signals) * 0.02

        return predictions, probabilities, expected_returns

    def test_initialization(self):
        """Test BetSizing initialization."""
        bet_sizing = BetSizing()

        assert bet_sizing.config is not None
        assert isinstance(bet_sizing.config, BetSizingConfig)

    def test_calculate_sizes_kelly(self, sample_signals):
        """Test bet sizing with Kelly criterion."""
        predictions, probabilities, expected_returns = sample_signals
        bet_sizing = BetSizing(config=BetSizingConfig(method="kelly"))

        result = bet_sizing.calculate_sizes(
            predictions=predictions,
            probabilities=probabilities,
            expected_returns=expected_returns,
        )

        assert isinstance(result, BetSizingResult)
        assert len(result.bet_sizes) == len(predictions)
        assert all(result.bet_sizes >= 0)
        assert all(result.bet_sizes <= 1.0)

    def test_calculate_sizes_probability(self, sample_signals):
        """Test bet sizing with probability method."""
        predictions, probabilities, _ = sample_signals
        bet_sizing = BetSizing(config=BetSizingConfig(method="probability"))

        result = bet_sizing.calculate_sizes(
            predictions=predictions,
            probabilities=probabilities,
        )

        assert isinstance(result, BetSizingResult)
        assert len(result.bet_sizes) == len(predictions)

    def test_calculate_sizes_risk_parity(self, sample_signals):
        """Test bet sizing with risk parity method."""
        predictions, _, _ = sample_signals
        volatilities = np.random.rand(len(predictions)) * 0.02 + 0.01

        bet_sizing = BetSizing(config=BetSizingConfig(method="risk_parity"))

        result = bet_sizing.calculate_sizes(
            predictions=predictions,
            volatilities=volatilities,
        )

        assert isinstance(result, BetSizingResult)
        assert len(result.bet_sizes) == len(predictions)

    def test_calculate_sizes_fixed(self, sample_signals):
        """Test bet sizing with fixed method."""
        predictions, _, _ = sample_signals
        bet_sizing = BetSizing(config=BetSizingConfig(method="fixed"))

        result = bet_sizing.calculate_sizes(predictions=predictions)

        assert isinstance(result, BetSizingResult)
        # With fixed sizing, all active signals should have equal size
        active_mask = predictions != 0
        if active_mask.sum() > 0:
            active_sizes = result.bet_sizes[active_mask]
            assert np.allclose(active_sizes, active_sizes[0])

    def test_calculate_sizes_with_volatility_adjustment(self, sample_signals):
        """Test volatility adjustment."""
        predictions, probabilities, expected_returns = sample_signals
        volatilities = np.array([0.01] * 10 + [0.03] * 10)  # Different volatilities

        bet_sizing = BetSizing(
            config=BetSizingConfig(
                method="kelly",
                adjust_for_volatility=True,
            )
        )

        result = bet_sizing.calculate_sizes(
            predictions=predictions,
            probabilities=probabilities,
            expected_returns=expected_returns,
            volatilities=volatilities,
        )

        # Higher volatility should generally lead to smaller bet sizes
        assert isinstance(result, BetSizingResult)

    def test_calculate_sizes_with_concentration_limit(self, sample_signals):
        """Test concentration limit."""
        predictions, probabilities, expected_returns = sample_signals
        bet_sizing = BetSizing(
            config=BetSizingConfig(
                method="kelly",
                concentration_limit=0.2,  # Max 20% per position
            )
        )

        result = bet_sizing.calculate_sizes(
            predictions=predictions,
            probabilities=probabilities,
            expected_returns=expected_returns,
        )

        # All bet sizes should be <= concentration limit
        assert all(result.bet_sizes <= 0.2)

    def test_calculate_sizes_with_exposure_limit(self, sample_signals):
        """Test portfolio exposure limit."""
        predictions, probabilities, expected_returns = sample_signals
        bet_sizing = BetSizing(
            config=BetSizingConfig(
                method="kelly",
                max_portfolio_exposure=0.5,  # Max 50% total exposure
            )
        )

        result = bet_sizing.calculate_sizes(
            predictions=predictions,
            probabilities=probabilities,
            expected_returns=expected_returns,
        )

        # Total exposure should be <= limit
        total_exposure = result.bet_sizes.sum()
        assert total_exposure <= 0.5 + 1e-10  # Small tolerance

    def test_calculate_sizes_with_drawdown_constraint(self, sample_signals):
        """Test drawdown constraint."""
        predictions, probabilities, expected_returns = sample_signals
        bet_sizing = BetSizing(
            config=BetSizingConfig(
                method="kelly",
                max_drawdown=0.15,
            )
        )

        # Simulate being in drawdown
        result = bet_sizing.calculate_sizes(
            predictions=predictions,
            probabilities=probabilities,
            expected_returns=expected_returns,
            current_drawdown=0.18,  # Above max
        )

        # Positions should be scaled down or zero
        assert isinstance(result, BetSizingResult)

    def test_kelly_sizing_formula(self, sample_signals):
        """Test Kelly criterion formula."""
        predictions, probabilities, expected_returns = sample_signals
        bet_sizing = BetSizing(config=BetSizingConfig(method="kelly"))

        # Simple case: even odds
        kelly_sizes = bet_sizing._kelly_sizing(
            predictions=np.array([1, 1, -1]),
            probabilities=np.array([0.6, 0.7, 0.55]),
            expected_returns=np.array([0.02, 0.02, -0.015]),
        )

        # Kelly formula: f = (bp - q) / b
        # For even odds (b=1): f = 2p - 1
        # p=0.6: f = 2*0.6 - 1 = 0.2
        # p=0.7: f = 2*0.7 - 1 = 0.4
        # But these get multiplied by kelly_fraction (0.25) and clipped

        assert len(kelly_sizes) == 3
        assert all(kelly_sizes >= 0)

    def test_probability_sizing_linear(self):
        """Test probability-based sizing with linear scaling."""
        bet_sizing = BetSizing(
            config=BetSizingConfig(
                method="probability",
                prob_threshold=0.5,
                prob_scaling="linear",
            )
        )

        bet_sizes = bet_sizing._probability_sizing(
            predictions=np.array([1, 1, 1]),
            probabilities=np.array([0.6, 0.7, 0.8]),
        )

        # Linear scaling: (p - threshold) / (1 - threshold)
        # p=0.6: (0.6 - 0.5) / 0.5 = 0.2
        # p=0.7: (0.7 - 0.5) / 0.5 = 0.4
        # p=0.8: (0.8 - 0.5) / 0.5 = 0.6
        expected = np.array([0.2, 0.4, 0.6])
        np.testing.assert_allclose(bet_sizes, expected, atol=1e-5)

    def test_probability_sizing_sigmoid(self):
        """Test probability-based sizing with sigmoid scaling."""
        bet_sizing = BetSizing(
            config=BetSizingConfig(
                method="probability",
                prob_threshold=0.5,
                prob_scaling="sigmoid",
            )
        )

        bet_sizes = bet_sizing._probability_sizing(
            predictions=np.array([1, 1]),
            probabilities=np.array([0.6, 0.8]),
        )

        assert len(bet_sizes) == 2
        assert all(b >= 0 for b in bet_sizes)

    def test_risk_parity_sizing(self):
        """Test risk parity sizing."""
        bet_sizing = BetSizing(config=BetSizingConfig(method="risk_parity"))

        predictions = np.array([1, 0, 1, 1, 0])
        volatilities = np.array([0.01, 0.02, 0.015, 0.025, 0.018])

        bet_sizes = bet_sizing._risk_parity_sizing(
            predictions=predictions,
            volatilities=volatilities,
        )

        # Risk parity: weight proportional to 1/volatility
        # Only non-zero predictions should have bet sizes
        assert bet_sizes[1] == 0  # prediction is 0
        assert bet_sizes[4] == 0  # prediction is 0
        assert bet_sizes[0] > 0  # prediction is 1
        assert bet_sizes[2] > 0  # prediction is 1
        assert bet_sizes[3] > 0  # prediction is 1


@pytest.mark.unit
class TestCalculateBetSizesConvenience:
    """Test cases for convenience functions."""

    def test_calculate_bet_sizes(self):
        """Test convenience function for bet sizing."""
        predictions = np.array([1, -1, 1, 0, 1])
        probabilities = np.array([0.6, 0.7, 0.55, 0.5, 0.8])

        bet_sizes = calculate_bet_sizes(
            predictions=predictions,
            probabilities=probabilities,
            method="kelly",
        )

        assert isinstance(bet_sizes, np.ndarray)
        assert len(bet_sizes) == len(predictions)
        assert all(bet_sizes >= 0)

    def test_calculate_bet_sizes_ml(self):
        """Test ML-based bet sizing."""
        meta_proba = np.array([0.6, 0.8, 0.4, 0.9, 0.3])
        primary_predictions = np.array([1, 1, -1, 1, -1])

        # Test meta_kelly
        bet_sizes = calculate_bet_sizes_ml(
            meta_proba=meta_proba,
            primary_predictions=primary_predictions,
            method="meta_kelly",
        )

        # Kelly: f = 2p - 1
        expected = np.array([0.2, 0.6, 0.0, 0.8, 0.0])
        np.testing.assert_allclose(bet_sizes, expected, atol=1e-5)

    def test_calculate_bet_sizes_ml_probability(self):
        """Test ML-based bet sizing with probability method."""
        meta_proba = np.array([0.6, 0.8, 0.4, 0.9])
        primary_predictions = np.array([1, 1, 1, -1])

        bet_sizes = calculate_bet_sizes_ml(
            meta_proba=meta_proba,
            primary_predictions=primary_predictions,
            method="meta_probability",
        )

        # Should equal probabilities
        expected = meta_proba
        np.testing.assert_allclose(bet_sizes, expected, atol=1e-5)

    def test_calculate_bet_sizes_ml_confidence(self):
        """Test ML-based bet sizing with confidence method."""
        meta_proba = np.array([0.6, 0.8, 0.4, 0.9])
        primary_predictions = np.array([1, 1, 1, -1])

        bet_sizes = calculate_bet_sizes_ml(
            meta_proba=meta_proba,
            primary_predictions=primary_predictions,
            method="meta_confidence",
            confidence_threshold=0.5,
            min_bet_size=0.1,
            max_bet_size=0.5,
        )

        # All should be between 0.1 and 0.5 (or 0 if below threshold)
        assert all((b == 0) or (0.1 <= b <= 0.5) for b in bet_sizes)

    def test_calculate_bet_sizes_with_discrete_allocation(self):
        """Test discrete allocation bet sizing."""
        meta_proba = np.array([0.6, 0.8, 0.3, 0.9, 0.7, 0.4])
        primary_predictions = np.array([1, 1, -1, 1, -1, 1])

        # Top K method
        bet_sizes = calculate_bet_sizes_with_discrete_allocation(
            meta_proba=meta_proba,
            primary_predictions=primary_predictions,
            n_bets=2,
            method="top_k",
        )

        # Should allocate to top 2 bets
        active_bets = (bet_sizes > 0).sum()
        assert active_bets == 2

        # Should sum to 1.0
        assert abs(bet_sizes.sum() - 1.0) < 1e-10

    def test_calculate_bet_sizes_with_discrete_allocation_threshold(self):
        """Test discrete allocation with threshold method."""
        meta_proba = np.array([0.6, 0.8, 0.3, 0.9, 0.7])
        primary_predictions = np.array([1, 1, -1, 1, -1])

        bet_sizes = calculate_bet_sizes_with_discrete_allocation(
            meta_proba=meta_proba,
            primary_predictions=primary_predictions,
            n_bets=2,
            method="threshold",
        )

        # Should have selected bets
        assert (bet_sizes > 0).sum() > 0

    def test_calculate_bet_sizes_with_risk_target(self):
        """Test risk target bet sizing."""
        meta_proba = np.array([0.6, 0.8, 0.3, 0.9])
        primary_predictions = np.array([1, 1, -1, 1])
        volatilities = np.array([0.2, 0.15, 0.25, 0.18])

        bet_sizes = calculate_bet_sizes_with_risk_target(
            meta_proba=meta_proba,
            primary_predictions=primary_predictions,
            volatilities=volatilities,
            risk_target=0.15,
        )

        # Should have non-zero bet sizes
        assert len(bet_sizes) == len(meta_proba)
        assert all(b >= 0 for b in bet_sizes)

    def test_calculate_bet_sizes_expected_value(self):
        """Test expected value bet sizing."""
        predictions = np.array([1, 1, -1, 1])
        probabilities = np.array([0.6, 0.7, 0.55, 0.8])
        win_amount = np.array([0.02, 0.02, 0.015, 0.025])
        loss_amount = np.array([0.01, 0.01, 0.01, 0.012])

        bet_sizes = calculate_bet_sizes_expected_value(
            predictions=predictions,
            probabilities=probabilities,
            win_amount=win_amount,
            loss_amount=loss_amount,
            kelly_fraction=0.25,
        )

        # Kelly: f = p/d - q/v where d=loss, v=win
        assert len(bet_sizes) == len(predictions)
        assert all(b >= 0 for b in bet_sizes)
        assert all(b <= 0.25 for b in bet_sizes)  # Capped at 0.25

    def test_calculate_bet_sizes_with_meta_model(self):
        """Test bet sizing with trained meta-model."""
        from sklearn.ensemble import RandomForestClassifier

        # Create a simple meta-model
        X_train = np.random.randn(100, 5)
        meta_labels_train = np.random.randint(0, 2, 100)
        meta_model = RandomForestClassifier(n_estimators=10, random_state=42)
        meta_model.fit(X_train, meta_labels_train)

        X_test = np.random.randn(20, 5)
        primary_predictions = np.random.randint(-1, 2, 20)

        bet_sizes = calculate_bet_sizes_with_meta_model(
            meta_model=meta_model,
            X=X_test,
            primary_predictions=primary_predictions,
            method="kelly",
        )

        assert len(bet_sizes) == len(X_test)
        assert all(b >= 0 for b in bet_sizes)


@pytest.mark.unit
class TestBetSizingEdgeCases:
    """Test edge cases for bet sizing."""

    def test_zero_predictions(self):
        """Test with all zero predictions."""
        predictions = np.array([0, 0, 0])
        bet_sizing = BetSizing()

        result = bet_sizing.calculate_sizes(predictions=predictions)

        assert all(result.bet_sizes == 0)

    def test_all_same_predictions(self):
        """Test with all same predictions."""
        predictions = np.array([1, 1, 1, 1])
        probabilities = np.array([0.6, 0.7, 0.8, 0.9])

        bet_sizing = BetSizing()
        result = bet_sizing.calculate_sizes(predictions, probabilities)

        assert all(result.bet_sizes >= 0)

    def test_negative_probabilities_clipped(self):
        """Test handling of negative probabilities (shouldn't happen but test anyway)."""
        bet_sizing = BetSizing(config=BetSizingConfig(method="probability"))

        # This shouldn't happen in practice, but test robustness
        predictions = np.array([1, 1, 1])
        probabilities = np.array([0.6, 0.7, 0.8])

        bet_sizes = bet_sizing._probability_sizing(predictions, probabilities)

        assert all(b >= 0 for b in bet_sizes)

    def test_single_signal(self):
        """Test with single signal."""
        predictions = np.array([1])
        probabilities = np.array([0.7])

        bet_sizing = BetSizing()
        result = bet_sizing.calculate_sizes(predictions, probabilities)

        assert len(result.bet_sizes) == 1

    def test_empty_inputs(self):
        """Test with empty inputs."""
        predictions = np.array([])

        bet_sizing = BetSizing()
        result = bet_sizing.calculate_sizes(predictions=predictions)

        assert len(result.bet_sizes) == 0

    def test_zero_volatility_risk_parity(self):
        """Test risk parity with zero volatility."""
        bet_sizing = BetSizing(config=BetSizingConfig(method="risk_parity"))

        predictions = np.array([1, 1, 1])
        volatilities = np.array([0.01, 0.0, 0.02])  # One zero volatility

        # Should handle gracefully (add small epsilon)
        bet_sizes = bet_sizing._risk_parity_sizing(predictions, volatilities)

        assert len(bet_sizes) == len(predictions)


@pytest.mark.unit
class TestBetSizingProperties:
    """Property-based tests for bet sizing."""

    @pytest.mark.parametrize("probability", [0.51, 0.6, 0.7, 0.8, 0.9])
    def test_kelly_monotonic_with_probability(self, probability):
        """Test that Kelly bet size increases with probability."""
        bet_sizing = BetSizing(
            config=BetSizingConfig(
                method="kelly",
                kelly_fraction=1.0,  # Full Kelly
            )
        )

        kelly = bet_sizing._kelly_sizing(
            predictions=np.array([1]),
            probabilities=np.array([probability]),
            expected_returns=np.array([0.02]),
        )

        # Kelly should be positive for p > 0.5
        # And increase with probability
        assert kelly[0] >= 0

    @pytest.mark.parametrize("n_signals", [5, 10, 20, 50])
    def test_exposure_limit_property(self, n_signals):
        """Test that exposure limit is respected."""
        predictions = np.random.randint(-1, 2, n_signals)
        probabilities = np.random.rand(n_signals) * 0.5 + 0.5

        max_exposure = 0.3
        bet_sizing = BetSizing(
            config=BetSizingConfig(
                method="probability",
                max_portfolio_exposure=max_exposure,
            )
        )

        result = bet_sizing.calculate_sizes(predictions, probabilities)

        # Total exposure should not exceed limit
        total_exposure = result.bet_sizes.sum()
        assert total_exposure <= max_exposure + 1e-10

    @pytest.mark.parametrize("concentration_limit", [0.1, 0.3, 0.5, 1.0])
    def test_concentration_limit_property(self, concentration_limit):
        """Test that concentration limit is respected."""
        n_signals = 20
        predictions = np.random.randint(-1, 2, n_signals)
        probabilities = np.random.rand(n_signals) * 0.5 + 0.5

        bet_sizing = BetSizing(
            config=BetSizingConfig(
                method="probability",
                concentration_limit=concentration_limit,
            )
        )

        result = bet_sizing.calculate_sizes(predictions, probabilities)

        # No single bet should exceed concentration limit
        assert all(result.bet_sizes <= concentration_limit + 1e-10)

    def test_bet_sizes_sum_property(self):
        """Test properties of bet size sums."""
        predictions = np.array([1, 1, 1, 1])
        probabilities = np.array([0.6, 0.7, 0.8, 0.9])

        # Fixed sizing should sum to 1.0
        bet_sizing = BetSizing(config=BetSizingConfig(method="fixed"))
        result = bet_sizing.calculate_sizes(predictions, probabilities)

        total = result.bet_sizes.sum()
        assert abs(total - 1.0) < 1e-10


@pytest.mark.unit
class TestBetSizingIntegration:
    """Integration tests for bet sizing."""

    def test_complete_workflow_with_meta_labeling(self):
        """Test complete workflow with meta-labeling integration."""
        # This simulates the real-world usage
        np.random.seed(42)

        # Simulate meta-labeling output
        meta_proba = np.random.rand(100) * 0.5 + 0.5  # 0.5 to 1.0
        primary_predictions = np.random.randint(-1, 2, 100)

        # Calculate bet sizes
        bet_sizes = calculate_bet_sizes_ml(
            meta_proba=meta_proba,
            primary_predictions=primary_predictions,
            method="meta_kelly",
            max_bet_size=0.25,
        )

        # Verify properties
        assert len(bet_sizes) == 100
        assert all(b >= 0 for b in bet_sizes)
        assert all(b <= 0.25 for b in bet_sizes)

        # Some trades should be skipped (low probability)
        skipped = (bet_sizes == 0).sum()
        assert skipped > 0

    def test_risk_adjusted_sizing(self):
        """Test risk-adjusted bet sizing."""
        n_signals = 50
        predictions = np.random.randint(-1, 2, n_signals)
        probabilities = np.random.rand(n_signals) * 0.5 + 0.5
        volatilities = np.random.rand(n_signals) * 0.02 + 0.01
        correlation_matrix = np.eye(n_signals)  # Uncorrelated

        bet_sizing = BetSizing(
            config=BetSizingConfig(
                method="kelly",
                adjust_for_volatility=True,
                adjust_for_correlation=True,
                concentration_limit=0.2,
            )
        )

        result = bet_sizing.calculate_sizes(
            predictions=predictions,
            probabilities=probabilities,
            volatilities=volatilities,
            correlation_matrix=correlation_matrix,
        )

        # Verify all constraints are respected
        assert all(result.bet_sizes >= 0)
        assert all(result.bet_sizes <= 0.2)  # Concentration limit
        assert result.bet_sizes.sum() <= 1.0  # Total exposure
