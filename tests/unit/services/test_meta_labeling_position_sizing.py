"""
Tests for Meta-Labeling Position Sizing Integration

Tests the integration between López de Prado's meta-labeling framework
and the position sizing engine for ML-based bet sizing.
"""

from decimal import Decimal

import numpy as np
import pytest

from app.services.position_sizing_engine import (
    MetaLabelingPositionSizer,
    PositionSizingEngineWithMetaLabeling,
)


class TestMetaLabelingPositionSizer:
    """Test suite for MetaLabelingPositionSizer class."""

    @pytest.fixture
    def sample_data(self):
        """Generate sample data for testing."""
        np.random.seed(42)

        n_train, n_test = 500, 100
        n_features = 10

        # Training data
        X_train = np.random.randn(n_train, n_features)
        y_train = np.random.choice([-1, 0, 1], size=n_train, p=[0.3, 0.4, 0.3])

        # Test data
        X_test = np.random.randn(n_test, n_features)
        y_test = np.random.choice([-1, 0, 1], size=n_test, p=[0.3, 0.4, 0.3])

        # Expected returns
        expected_returns = np.random.randn(n_test) * 0.02

        return {
            "X_train": X_train,
            "y_train": y_train,
            "X_test": X_test,
            "y_test": y_test,
            "expected_returns": expected_returns,
        }

    @pytest.fixture
    def sizer(self):
        """Create a MetaLabelingPositionSizer instance."""
        return MetaLabelingPositionSizer(
            config={
                "bet_sizing_method": "meta_kelly",
                "confidence_threshold": 0.5,
                "max_bet_size": 0.25,
                "min_bet_size": 0.01,
            }
        )

    def test_initialization(self, sizer):
        """Test sizer initialization."""
        assert sizer.bet_sizing_method == "meta_kelly"
        assert sizer.confidence_threshold == 0.5
        assert sizer.max_bet_size == 0.25
        assert sizer.min_bet_size == 0.01

    def test_initialization_with_default_config(self):
        """Test initialization with default configuration."""
        sizer = MetaLabelingPositionSizer()
        assert sizer.bet_sizing_method == "meta_kelly"
        assert sizer.confidence_threshold == 0.5
        assert sizer.max_bet_size == 1.0
        assert sizer.min_bet_size == 0.0

    def test_calculate_position_size_basic(self, sizer, sample_data):
        """Test basic position size calculation."""
        signals = sample_data["y_test"]
        meta_proba = np.random.uniform(0.3, 0.9, size=len(signals))

        position_sizes = sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
        )

        # Check output shape
        assert len(position_sizes) == len(signals)

        # Check that position sizes are within bounds
        assert np.all(position_sizes >= -sizer.max_bet_size)
        assert np.all(position_sizes <= sizer.max_bet_size)

    def test_calculate_position_size_with_expected_returns(self, sizer, sample_data):
        """Test position size calculation with expected returns."""
        signals = sample_data["y_test"]
        meta_proba = np.random.uniform(0.3, 0.9, size=len(signals))
        expected_returns = sample_data["expected_returns"]

        position_sizes = sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
            expected_returns=expected_returns,
        )

        # Check output shape
        assert len(position_sizes) == len(signals)
        assert len(position_sizes) == len(expected_returns)

    def test_calculate_position_size_signal_direction(self, sizer):
        """Test that position sizes respect signal direction."""
        signals = np.array([1, -1, 1, -1, 0])
        meta_proba = np.array([0.7, 0.7, 0.6, 0.6, 0.5])

        position_sizes = sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
        )

        # Positive signals should give positive or zero positions
        assert position_sizes[0] >= 0 or position_sizes[0] == 0
        assert position_sizes[2] >= 0 or position_sizes[2] == 0

        # Negative signals should give negative or zero positions
        assert position_sizes[1] <= 0 or position_sizes[1] == 0
        assert position_sizes[3] <= 0 or position_sizes[3] == 0

        # Zero signal should give zero position
        assert position_sizes[4] == 0

    def test_calculate_position_size_confidence_threshold(self, sizer):
        """Test that confidence threshold filters trades."""
        signals = np.array([1, 1, 1])
        meta_proba = np.array([0.4, 0.5, 0.7])

        position_sizes = sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
        )

        # Low confidence (< 0.5) should give zero position
        assert position_sizes[0] == 0

        # Medium confidence (= 0.5) should give zero or minimal position
        assert position_sizes[1] == 0

        # High confidence (> 0.5) should give positive position
        assert position_sizes[2] > 0

    def test_calculate_position_size_input_validation(self, sizer):
        """Test input validation for position size calculation."""
        signals = np.array([1, -1, 1])
        meta_proba_wrong_length = np.array([0.7, 0.6])

        with pytest.raises(ValueError, match="must have same length"):
            sizer.calculate_position_size(
                signals=signals,
                meta_proba=meta_proba_wrong_length,
            )

    def test_calculate_position_size_with_capital(self, sizer):
        """Test position size calculation with capital parameter."""
        signals = np.array([1, -1, 1])
        meta_proba = np.array([0.7, 0.6, 0.8])
        capital = Decimal("10000")

        position_sizes = sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
            capital=capital,
        )

        # Position sizes should be fractions of capital
        assert len(position_sizes) == len(signals)
        assert np.all(position_sizes >= -1.0)
        assert np.all(position_sizes <= 1.0)

    def test_fit_meta_model(self, sizer, sample_data):
        """Test meta-model fitting."""
        result = sizer.fit_meta_model(
            X_train=sample_data["X_train"],
            y_train=sample_data["y_train"],
            X_test=sample_data["X_test"],
            y_test=sample_data["y_test"],
        )

        # Check result structure
        assert "meta_model" in result
        assert "meta_proba" in result
        assert "bet_sizes" in result
        assert "metrics" in result

        # Check metrics structure
        assert "primary_accuracy" in result["metrics"]
        assert "meta_accuracy" in result["metrics"]
        assert "combined_accuracy" in result["metrics"]

        # Check metrics are in valid range
        assert 0.0 <= result["metrics"]["primary_accuracy"] <= 1.0
        assert 0.0 <= result["metrics"]["meta_accuracy"] <= 1.0
        assert 0.0 <= result["metrics"]["combined_accuracy"] <= 1.0

    def test_fit_meta_model_without_test_data(self, sizer, sample_data):
        """Test meta-model fitting without test data."""
        result = sizer.fit_meta_model(
            X_train=sample_data["X_train"],
            y_train=sample_data["y_train"],
        )

        # Should still return valid result
        assert "meta_model" in result
        assert "meta_proba" in result
        assert "metrics" in result

    def test_fallback_sizing_when_ml_unavailable(self, sample_data):
        """Test fallback sizing when ML modules are unavailable."""
        sizer = MetaLabelingPositionSizer()
        sizer._has_ml_modules = False  # Simulate unavailable ML modules

        signals = sample_data["y_test"]
        meta_proba = np.random.uniform(0.3, 0.9, size=len(signals))

        position_sizes = sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
        )

        # Should still return valid position sizes
        assert len(position_sizes) == len(signals)
        assert np.all(position_sizes >= -1.0)
        assert np.all(position_sizes <= 1.0)

    def test_different_bet_sizing_methods(self, sample_data):
        """Test different bet sizing methods."""
        methods = ["meta_kelly", "meta_probability", "meta_expected_value"]

        for method in methods:
            sizer = MetaLabelingPositionSizer(config={"bet_sizing_method": method})

            signals = sample_data["y_test"]
            meta_proba = np.random.uniform(0.3, 0.9, size=len(signals))

            position_sizes = sizer.calculate_position_size(
                signals=signals,
                meta_proba=meta_proba,
            )

            # Should return valid position sizes for each method
            assert len(position_sizes) == len(signals)
            assert np.all(position_sizes >= -1.0)
            assert np.all(position_sizes <= 1.0)


class TestPositionSizingEngineWithMetaLabeling:
    """Test suite for PositionSizingEngineWithMetaLabeling class."""

    @pytest.fixture
    def engine(self):
        """Create a PositionSizingEngineWithMetaLabeling instance."""
        return PositionSizingEngineWithMetaLabeling()

    @pytest.fixture
    def sample_data(self):
        """Generate sample data for testing."""
        np.random.seed(42)

        n_train, n_test = 500, 100
        n_features = 10

        X_train = np.random.randn(n_train, n_features)
        y_train = np.random.choice([-1, 0, 1], size=n_train)

        X_test = np.random.randn(n_test, n_features)
        y_test = np.random.choice([-1, 0, 1], size=n_test)

        expected_returns = np.random.randn(n_test) * 0.02

        return {
            "X_train": X_train,
            "y_train": y_train,
            "X_test": X_test,
            "y_test": y_test,
            "expected_returns": expected_returns,
        }

    def test_initialization(self, engine):
        """Test engine initialization."""
        assert isinstance(engine.meta_sizer, MetaLabelingPositionSizer)
        assert hasattr(engine, "calculate_meta_labeling_sizes")
        assert hasattr(engine, "calculate_hybrid_sizes")

    def test_inherits_from_position_sizing_engine(self, engine):
        """Test that engine inherits from PositionSizingEngine."""
        # Should have all parent class methods
        assert hasattr(engine, "calculate_kelly_position_size")
        assert hasattr(engine, "calculate_position_size_from_atr")
        assert hasattr(engine, "calculate_stop_loss_price")

    def test_calculate_meta_labeling_sizes(self, engine, sample_data):
        """Test meta-labeling position sizing through engine."""
        signals = sample_data["y_test"]
        meta_proba = np.random.uniform(0.3, 0.9, size=len(signals))

        position_sizes = engine.calculate_meta_labeling_sizes(
            signals=signals,
            meta_proba=meta_proba,
        )

        assert len(position_sizes) == len(signals)

    def test_calculate_hybrid_sizes(self, engine, sample_data):
        """Test hybrid meta-labeling + Kelly sizing."""
        signals = sample_data["y_test"]
        meta_proba = np.random.uniform(0.3, 0.9, size=len(signals))

        result = engine.calculate_hybrid_sizes(
            signals=signals,
            meta_proba=meta_proba,
            win_rate=0.55,
            avg_win=100.0,
            avg_loss=75.0,
            capital=Decimal("10000"),
        )

        # Check result structure
        assert "position_sizes" in result
        assert "meta_sizes" in result
        assert "kelly_fraction" in result
        assert "filter_mask" in result

        # Check arrays
        assert len(result["position_sizes"]) == len(signals)
        assert len(result["meta_sizes"]) == len(signals)
        assert len(result["filter_mask"]) == len(signals)

        # Check Kelly fraction
        assert 0.0 <= result["kelly_fraction"] <= 0.25  # Half-Kelly cap

    def test_hybrid_sizes_apply_kelly_cap(self, engine):
        """Test that hybrid sizes respect Kelly cap."""
        signals = np.array([1, 1, 1])
        meta_proba = np.array([0.9, 0.9, 0.9])  # High confidence

        # Low win rate should result in low Kelly fraction
        result = engine.calculate_hybrid_sizes(
            signals=signals,
            meta_proba=meta_proba,
            win_rate=0.51,  # Marginal win rate
            avg_win=50.0,
            avg_loss=49.0,
            capital=Decimal("10000"),
        )

        # Position sizes should be capped at Kelly fraction
        kelly_fraction = result["kelly_fraction"]
        position_sizes = np.abs(result["position_sizes"])

        for i, size in enumerate(position_sizes):
            if size > 0:
                assert size <= kelly_fraction + 1e-6  # Allow small numerical error

    def test_hybrid_sizes_filter_by_confidence(self, engine):
        """Test that hybrid sizes filter by meta-model confidence."""
        signals = np.array([1, 1, 1])
        meta_proba = np.array([0.4, 0.6, 0.8])

        result = engine.calculate_hybrid_sizes(
            signals=signals,
            meta_proba=meta_proba,
            win_rate=0.55,
            avg_win=100.0,
            avg_loss=75.0,
            capital=Decimal("10000"),
        )

        # Low confidence should be filtered out
        assert not result["filter_mask"][0]
        assert result["filter_mask"][1]
        assert result["filter_mask"][2]

        # Filtered signal should have zero position
        assert result["position_sizes"][0] == 0

    def test_combined_with_traditional_kelly(self, engine):
        """Test that engine can use both meta-labeling and traditional Kelly."""
        # Traditional Kelly
        kelly_result = engine.calculate_kelly_position_size(
            win_rate=0.55,
            avg_win=100.0,
            avg_loss=75.0,
            capital=Decimal("10000"),
        )

        assert "kelly_fraction" in kelly_result
        assert "position_value" in kelly_result

        # Meta-labeling
        signals = np.array([1, -1, 1])
        meta_proba = np.array([0.7, 0.6, 0.8])

        meta_sizes = engine.calculate_meta_labeling_sizes(
            signals=signals,
            meta_proba=meta_proba,
        )

        assert len(meta_sizes) == len(signals)


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    @pytest.fixture
    def engine(self):
        """Create engine for integration tests."""
        return PositionSizingEngineWithMetaLabeling(
            config={"bet_sizing_method": "meta_kelly", "confidence_threshold": 0.5}
        )

    def test_high_confidence_scenario(self, engine):
        """Test position sizing with high meta-model confidence."""
        signals = np.array([1, 1, 1, 1, 1])
        meta_proba = np.array([0.8, 0.85, 0.9, 0.95, 0.99])

        position_sizes = engine.calculate_meta_labeling_sizes(
            signals=signals,
            meta_proba=meta_proba,
        )

        # All positions should be positive
        assert np.all(position_sizes > 0)

        # Higher confidence should generally lead to larger positions
        # (though not strictly monotonic due to Kelly cap)
        assert np.mean(position_sizes) > 0

    def test_low_confidence_scenario(self, engine):
        """Test position sizing with low meta-model confidence."""
        signals = np.array([1, 1, 1, 1, 1])
        meta_proba = np.array([0.3, 0.35, 0.4, 0.45, 0.49])

        position_sizes = engine.calculate_meta_labeling_sizes(
            signals=signals,
            meta_proba=meta_proba,
        )

        # All positions should be zero (below confidence threshold)
        assert np.all(position_sizes == 0)

    def test_mixed_signals_scenario(self, engine):
        """Test position sizing with mixed buy/sell/hold signals."""
        signals = np.array([1, 1, 0, -1, -1])
        meta_proba = np.array([0.7, 0.6, 0.8, 0.7, 0.6])

        position_sizes = engine.calculate_meta_labeling_sizes(
            signals=signals,
            meta_proba=meta_proba,
        )

        # Check signal directions
        assert position_sizes[0] >= 0  # Buy
        assert position_sizes[1] >= 0  # Buy
        assert position_sizes[2] == 0  # Hold
        assert position_sizes[3] <= 0  # Sell
        assert position_sizes[4] <= 0  # Sell

    def test_portfolio_exposure_limit(self, engine):
        """Test that portfolio exposure can be limited."""
        # Generate many signals
        n_signals = 50
        signals = np.random.choice([-1, 0, 1], size=n_signals)
        meta_proba = np.random.uniform(0.5, 0.9, size=n_signals)

        position_sizes = engine.calculate_meta_labeling_sizes(
            signals=signals,
            meta_proba=meta_proba,
        )

        # Calculate total exposure
        total_exposure = np.abs(position_sizes).sum()

        # With random high-confidence signals, exposure should be reasonable
        # (not exceeding 1.0 significantly due to Kelly cap)
        assert total_exposure <= n_signals * 0.25  # Each position max 25%

    def test_risk_adjusted_sizing(self, engine):
        """Test risk-adjusted position sizing."""
        # Scenario: Higher expected returns should get larger positions
        signals = np.array([1, 1, 1])
        meta_proba = np.array([0.7, 0.7, 0.7])
        expected_returns = np.array([0.01, 0.02, 0.03])

        position_sizes = engine.calculate_meta_labeling_sizes(
            signals=signals,
            meta_proba=meta_proba,
            expected_returns=expected_returns,
        )

        # All should have positive positions
        assert np.all(position_sizes > 0)

        # Positions should vary based on expected returns (if method supports it)
        # Note: With meta_kelly, sizing may not vary with identical meta_proba
        # This is expected behavior - meta_kelly uses meta_proba for sizing


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def sizer(self):
        """Create sizer for edge case tests."""
        return MetaLabelingPositionSizer()

    def test_empty_arrays(self, sizer):
        """Test handling of empty arrays."""
        signals = np.array([])
        meta_proba = np.array([])

        position_sizes = sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
        )

        assert len(position_sizes) == 0

    def test_all_zero_signals(self, sizer):
        """Test handling of all zero signals."""
        signals = np.array([0, 0, 0])
        meta_proba = np.array([0.7, 0.8, 0.9])

        position_sizes = sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
        )

        # All positions should be zero
        assert np.all(position_sizes == 0)

    def test_extreme_meta_proba(self, sizer):
        """Test handling of extreme meta-model probabilities."""
        signals = np.array([1, 1, 1, 1])
        meta_proba = np.array([0.0, 0.5, 1.0, 0.99])

        position_sizes = sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
        )

        # Should handle extreme values gracefully
        assert len(position_sizes) == len(signals)
        assert np.all(np.isfinite(position_sizes))

    def test_single_signal(self, sizer):
        """Test handling of single signal."""
        signals = np.array([1])
        meta_proba = np.array([0.7])

        position_sizes = sizer.calculate_position_size(
            signals=signals,
            meta_proba=meta_proba,
        )

        assert len(position_sizes) == 1
        assert position_sizes[0] >= 0
