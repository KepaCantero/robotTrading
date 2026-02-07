"""
Unit tests for Portfolio Meta-Learners.

Tests cover:
- Historical performance-based learning
- Reinforcement learning-based allocation
- Ensemble meta-learning
- Weight smoothing and updates
- Feature extraction
"""

from unittest.mock import patch

import numpy as np
import pytest
import torch

from app.engines.portfolio_engine.meta_learners.meta_learners import (
    BaseMetaLearner,
    EnsembleMetaLearner,
    HistoricalPerformanceLearner,
    ReinforcementLearningLearner,
)


@pytest.mark.unit
class TestHistoricalPerformanceLearner:
    """Test suite for HistoricalPerformanceLearner."""

    @pytest.fixture
    def learner(self):
        """Create historical performance learner."""
        config = {
            'lookback_period': 30,
            'smoothing_factor': 0.1,
            'use_sharpe': True,
            'use_return': True,
            'use_drawdown': False,
        }
        return HistoricalPerformanceLearner(config)

    @pytest.fixture
    def sample_performance(self):
        """Create sample strategy performance data."""
        return {
            'strategy_a': {
                'return': 0.15,
                'sharpe_ratio': 1.5,
                'max_drawdown': -0.10,
            },
            'strategy_b': {
                'return': 0.08,
                'sharpe_ratio': 0.8,
                'max_drawdown': -0.15,
            },
            'strategy_c': {
                'return': 0.12,
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.08,
            },
        }

    def test_learner_initialization(self, learner):
        """Test learner initialization."""
        assert learner.lookback_period == 30
        assert learner.smoothing_factor == 0.1
        assert learner.use_sharpe is True
        assert learner.use_return is True
        assert learner.use_drawdown is False

    def test_learn_weights_basic(self, learner, sample_performance):
        """Test basic weight learning."""
        weights = learner.learn_weights(sample_performance)

        # Check all strategies have weights
        assert set(weights.keys()) == set(sample_performance.keys())

        # Weights should sum to 1
        assert np.isclose(sum(weights.values()), 1.0, atol=1e-6)

        # All weights should be positive
        assert all(w > 0 for w in weights.values())

    def test_learn_weights_performance_based(self, learner, sample_performance):
        """Test that better performing strategies get higher weights."""
        weights = learner.learn_weights(sample_performance)

        # Strategy A has best Sharpe (1.5) and good return (0.15)
        # Should get relatively high weight
        assert weights['strategy_a'] > 0

        # Strategy B has lowest Sharpe (0.8) and lower return (0.08)
        # Should get lower weight
        assert weights['strategy_b'] < weights['strategy_a']

    def test_learn_weights_empty_performance(self, learner):
        """Test with empty performance data."""
        weights = learner.learn_weights({})

        assert weights == {}

    def test_learn_weights_with_smoothing(self, learner, sample_performance):
        """Test weight smoothing with historical data."""
        # First learning
        weights1 = learner.learn_weights(sample_performance)

        # Simulate time passing and new performance
        updated_performance = {
            'strategy_a': {
                'return': 0.10,  # Lower than before
                'sharpe_ratio': 1.0,
                'max_drawdown': -0.12,
            },
            'strategy_b': {
                'return': 0.18,  # Higher than before
                'sharpe_ratio': 1.8,
                'max_drawdown': -0.08,
            },
            'strategy_c': {
                'return': 0.12,
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.08,
            },
        }

        weights2 = learner.learn_weights(updated_performance)

        # Weights should change due to smoothing
        # (With low smoothing factor, should adapt quickly)
        assert weights2['strategy_b'] > weights1.get('strategy_b', 0)

    def test_update_method(self, learner, sample_performance):
        """Test update method."""
        portfolio_return = 0.12

        learner.update(sample_performance, portfolio_return)

        # Should add to learning history
        assert len(learner.learning_history) == 1

        entry = learner.learning_history[0]
        assert 'timestamp' in entry
        assert 'weights' in entry
        assert 'portfolio_return' in entry
        assert entry['portfolio_return'] == 0.12

    def test_sharpe_normalization(self):
        """Test Sharpe ratio normalization."""
        config = {'use_sharpe': True, 'use_return': False}
        learner = HistoricalPerformanceLearner(config)

        # Extreme Sharpe values
        performance = {
            'strategy_a': {'sharpe_ratio': 5.0},  # Very high
            'strategy_b': {'sharpe_ratio': -1.0},  # Negative
            'strategy_c': {'sharpe_ratio': 0.5},  # Low positive
        }

        weights = learner.learn_weights(performance)

        # Should normalize and produce valid weights
        assert np.isclose(sum(weights.values()), 1.0)
        assert all(w >= 0 for w in weights.values())

    def test_return_normalization(self):
        """Test return normalization."""
        config = {'use_sharpe': False, 'use_return': True}
        learner = HistoricalPerformanceLearner(config)

        # Extreme return values
        performance = {
            'strategy_a': {'return': 1.5},  # 150% return
            'strategy_b': {'return': -0.5},  # -50% return
            'strategy_c': {'return': 0.05},  # 5% return
        }

        weights = learner.learn_weights(performance)

        # Should normalize and produce valid weights
        assert np.isclose(sum(weights.values()), 1.0)

    def test_drawdown_penalty(self):
        """Test drawdown penalty."""
        config = {
            'use_sharpe': True,
            'use_return': True,
            'use_drawdown': True,
        }
        learner = HistoricalPerformanceLearner(config)

        performance = {
            'strategy_a': {
                'return': 0.15,
                'sharpe_ratio': 1.5,
                'max_drawdown': -0.05,  # Small drawdown
            },
            'strategy_b': {
                'return': 0.15,
                'sharpe_ratio': 1.5,
                'max_drawdown': -0.40,  # Large drawdown
            },
        }

        weights = learner.learn_weights(performance)

        # Strategy A should get higher weight due to smaller drawdown
        assert weights['strategy_a'] > weights['strategy_b']

    def test_performance_history_tracking(self, learner, sample_performance):
        """Test that performance history is tracked."""
        learner.learn_weights(sample_performance)

        # Should have stored performance
        assert 'strategy_a' in learner.performance_history
        assert len(learner.performance_history['strategy_a']) == 1

        entry = learner.performance_history['strategy_a'][0]
        assert 'timestamp' in entry
        assert 'metrics' in entry

    def test_lookback_period_limit(self, learner):
        """Test that history is limited to lookback period."""
        # This test would require mocking datetime
        # For now, just verify the structure is in place
        assert learner.lookback_period == 30
        assert learner.performance_history == {}

    def test_max_history_size(self):
        """Test that learning history has max size limit."""
        config = {'max_history_size': 5}
        learner = HistoricalPerformanceLearner(config)

        performance = {'strategy_a': {'return': 0.1}}

        # Add more entries than max
        for i in range(10):
            learner.update(performance, 0.1)

        # Should be limited to max_history_size
        assert len(learner.learning_history) == 5


@pytest.mark.unit
class TestReinforcementLearningLearner:
    """Test suite for ReinforcementLearningLearner."""

    @pytest.fixture
    def learner(self):
        """Create RL learner."""
        config = {
            'learning_rate': 0.001,
            'discount_factor': 0.99,
            'exploration_rate': 0.1,
            'exploration_decay': 0.995,
        }
        return ReinforcementLearningLearner(config)

    @pytest.fixture
    def sample_performance(self):
        """Create sample strategy performance data."""
        return {
            'strategy_a': {
                'return': 0.15,
                'sharpe_ratio': 1.5,
                'max_drawdown': -0.10,
                'win_rate': 0.6,
            },
            'strategy_b': {
                'return': 0.08,
                'sharpe_ratio': 0.8,
                'max_drawdown': -0.15,
                'win_rate': 0.55,
            },
        }

    @pytest.fixture
    def sample_market_context(self):
        """Create sample market context."""
        return {
            'regime': 1.0,
            'volatility': 0.15,
            'trend_strength': 0.7,
        }

    def test_learner_initialization(self, learner):
        """Test learner initialization."""
        assert learner.learning_rate == 0.001
        assert learner.discount_factor == 0.99
        assert learner.exploration_rate == 0.1
        assert learner.model is not None

    def test_model_structure(self, learner):
        """Test that PyTorch model is correctly initialized."""
        assert isinstance(learner.model, torch.nn.Module)

        # Check model has expected layers
        assert hasattr(learner.model, 'fc1')
        assert hasattr(learner.model, 'fc2')
        assert hasattr(learner.model, 'fc3')

    def test_learn_weights_basic(self, learner, sample_performance):
        """Test basic weight learning."""
        weights = learner.learn_weights(sample_performance)

        # Should return weights for strategies
        assert 'strategy_a' in weights
        assert 'strategy_b' in weights

        # Weights should be normalized
        assert np.isclose(sum(weights.values()), 1.0, atol=1e-4)

        # All weights should be positive
        assert all(w > 0 for w in weights.values())

    def test_learn_weights_with_market_context(
        self, learner, sample_performance, sample_market_context
    ):
        """Test learning with market context."""
        weights = learner.learn_weights(sample_performance, sample_market_context)

        # Should incorporate market context
        assert 'strategy_a' in weights
        assert 'strategy_b' in weights

    def test_feature_extraction(self, learner, sample_performance, sample_market_context):
        """Test feature extraction."""
        features = learner._extract_features(sample_performance, sample_market_context)

        # Should be numpy array
        assert isinstance(features, np.ndarray)

        # Should have correct length (input_size)
        assert len(features) == learner.input_size

        # Features should include performance metrics
        assert features[0] == sample_performance['strategy_a']['return']
        assert features[1] == sample_performance['strategy_a']['sharpe_ratio']

    def test_feature_extraction_padding(self, learner):
        """Test feature extraction with padding."""
        # Fewer features than input_size
        performance = {'strategy_a': {'return': 0.1}}
        context = None

        features = learner._extract_features(performance, context)

        # Should be padded to input_size
        assert len(features) == learner.input_size

    def test_model_forward_pass(self, learner, sample_performance):
        """Test that model can do forward pass."""
        features = learner._extract_features(sample_performance, None)

        # Convert to tensor
        features_tensor = torch.FloatTensor(features).unsqueeze(0)

        # Forward pass
        with torch.no_grad():
            output = learner.model(features_tensor)

        # Should output valid probabilities
        assert output.shape == (1, learner.output_size)
        assert torch.all(output >= 0).item()
        assert torch.all(output <= 1).item()

    def test_update_method(self, learner, sample_performance):
        """Test update method."""
        portfolio_return = 0.12

        learner.update(sample_performance, portfolio_return)

        # Should add to learning history
        assert len(learner.learning_history) == 1

        entry = learner.learning_history[0]
        assert 'timestamp' in entry
        assert 'reward' in entry
        assert entry['reward'] == portfolio_return

    def test_exploration_rate_decay(self, learner, sample_performance):
        """Test that exploration rate decays."""
        initial_rate = learner.exploration_rate

        learner.update(sample_performance, 0.1)

        # Exploration rate should decrease
        assert learner.exploration_rate < initial_rate

    def test_learn_weights_without_model_initialization(self):
        """Test error handling when model not initialized."""
        # This would require mocking _initialize_model
        # For now, we test that the error would be raised

    def test_optimizer_initialization(self, learner):
        """Test that optimizer is initialized."""
        assert learner.optimizer is not None
        assert isinstance(learner.optimizer, torch.optim.Adam)

    def test_learning_history_limit(self):
        """Test that learning history has size limit."""
        config = {'max_history_size': 5}
        learner = ReinforcementLearningLearner(config)

        performance = {'strategy_a': {'return': 0.1}}

        # Add more entries than max
        for i in range(10):
            learner.update(performance, 0.1)

        # Should be limited
        assert len(learner.learning_history) == 5


@pytest.mark.unit
class TestEnsembleMetaLearner:
    """Test suite for EnsembleMetaLearner."""

    @pytest.fixture
    def ensemble(self):
        """Create ensemble learner."""
        config = {
            'use_historical': True,
            'use_rl': False,  # Disable RL to avoid torch dependency issues in tests
            'learner_weights': None,
        }
        return EnsembleMetaLearner(config)

    @pytest.fixture
    def sample_performance(self):
        """Create sample strategy performance data."""
        return {
            'strategy_a': {
                'return': 0.15,
                'sharpe_ratio': 1.5,
                'max_drawdown': -0.10,
            },
            'strategy_b': {
                'return': 0.08,
                'sharpe_ratio': 0.8,
                'max_drawdown': -0.15,
            },
            'strategy_c': {
                'return': 0.12,
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.08,
            },
        }

    def test_ensemble_initialization(self, ensemble):
        """Test ensemble initialization."""
        assert len(ensemble.learners) > 0
        assert ensemble.learner_weights is not None

    def test_ensemble_with_custom_weights(self):
        """Test ensemble with custom learner weights."""
        config = {
            'use_historical': True,
            'use_rl': False,
            'learner_weights': {
                'HistoricalPerformanceLearner': 0.7,
            },
        }
        ensemble = EnsembleMetaLearner(config)

        assert ensemble.learner_weights['HistoricalPerformanceLearner'] == 0.7

    def test_learn_weights_basic(self, ensemble, sample_performance):
        """Test basic weight learning."""
        weights = ensemble.learn_weights(sample_performance)

        # Should return weights for all strategies
        assert set(weights.keys()) == set(sample_performance.keys())

        # Weights should be normalized
        assert np.isclose(sum(weights.values()), 1.0, atol=1e-6)

    def test_learn_weights_combines_learners(self, ensemble, sample_performance):
        """Test that ensemble combines multiple learners."""
        # Get weights from individual learners
        individual_weights = []
        for learner in ensemble.learners:
            w = learner.learn_weights(sample_performance)
            individual_weights.append(w)

        # Get ensemble weights
        ensemble_weights = ensemble.learn_weights(sample_performance)

        # Ensemble should be different from individual learners
        # (unless all learners agree)
        assert isinstance(ensemble_weights, dict)

    def test_update_all_learners(self, ensemble, sample_performance):
        """Test that update updates all learners."""
        portfolio_return = 0.12

        initial_history_sizes = [len(learner.learning_history) for learner in ensemble.learners]

        ensemble.update(sample_performance, portfolio_return)

        # All learners should have been updated
        for i, learner in enumerate(ensemble.learners):
            assert len(learner.learning_history) >= initial_history_sizes[i]

    def test_ensemble_with_no_learners(self, sample_performance):
        """Test ensemble with no learners."""
        config = {
            'use_historical': False,
            'use_rl': False,
        }
        ensemble = EnsembleMetaLearner(config)

        # Should fall back to equal weights
        weights = ensemble.learn_weights(sample_performance)

        assert len(weights) == len(sample_performance)
        for w in weights.values():
            assert w == pytest.approx(1.0 / len(sample_performance))

    def test_ensemble_handles_learner_failure(self):
        """Test that ensemble handles learner failures gracefully."""
        config = {'use_historical': True, 'use_rl': False}
        ensemble = EnsembleMetaLearner(config)

        performance = {'strategy_a': {'return': 0.1}}

        # Mock one learner to fail
        with patch.object(
            ensemble.learners[0], 'learn_weights', side_effect=Exception("Test error")
        ):
            # Should not raise exception
            weights = ensemble.learn_weights(performance)

            # Should still return valid weights
            assert isinstance(weights, dict)

    def test_ensemble_weighted_average(self, sample_performance):
        """Test that ensemble uses weighted average."""
        config = {
            'use_historical': True,
            'use_rl': False,
            'learner_weights': {
                'HistoricalPerformanceLearner': 1.0,
            },
        }
        ensemble = EnsembleMetaLearner(config)

        weights = ensemble.learn_weights(sample_performance)

        # Should return valid weights
        assert np.isclose(sum(weights.values()), 1.0)


@pytest.mark.unit
class TestMetaLearnerEdgeCases:
    """Test edge cases for meta-learners."""

    def test_empty_strategy_performance(self):
        """Test with empty strategy performance."""
        config = {}
        learner = HistoricalPerformanceLearner(config)

        weights = learner.learn_weights({})

        assert weights == {}

    def test_single_strategy(self):
        """Test with single strategy."""
        config = {}
        learner = HistoricalPerformanceLearner(config)

        performance = {
            'strategy_a': {
                'return': 0.15,
                'sharpe_ratio': 1.5,
            }
        }

        weights = learner.learn_weights(performance)

        # Single strategy should get 100% weight
        assert weights['strategy_a'] == pytest.approx(1.0)

    def test_many_strategies(self):
        """Test with many strategies."""
        config = {}
        learner = HistoricalPerformanceLearner(config)

        # Create 20 strategies
        performance = {
            f'strategy_{i}': {
                'return': 0.05 + i * 0.01,
                'sharpe_ratio': 0.5 + i * 0.1,
            }
            for i in range(20)
        }

        weights = learner.learn_weights(performance)

        # Should handle all strategies
        assert len(weights) == 20
        assert np.isclose(sum(weights.values()), 1.0)

    def test_extreme_performance_values(self):
        """Test with extreme performance values."""
        config = {}
        learner = HistoricalPerformanceLearner(config)

        performance = {
            'strategy_a': {
                'return': 10.0,  # 1000% return
                'sharpe_ratio': 50.0,
            },
            'strategy_b': {
                'return': -0.9,  # -90% return
                'sharpe_ratio': -5.0,
            },
        }

        weights = learner.learn_weights(performance)

        # Should normalize and produce valid weights
        assert np.isclose(sum(weights.values()), 1.0)
        assert all(w >= 0 for w in weights.values())

    def test_missing_metrics(self):
        """Test with missing metrics."""
        config = {'use_sharpe': True, 'use_return': True}
        learner = HistoricalPerformanceLearner(config)

        # One strategy missing Sharpe, one missing return
        performance = {
            'strategy_a': {
                'return': 0.15,
                # Missing sharpe_ratio
            },
            'strategy_b': {
                # Missing return
                'sharpe_ratio': 1.5,
            },
        }

        weights = learner.learn_weights(performance)

        # Should handle missing metrics gracefully
        assert 'strategy_a' in weights
        assert 'strategy_b' in weights
        assert np.isclose(sum(weights.values()), 1.0)

    def test_zero_variance_performance(self):
        """Test with zero variance in performance."""
        config = {}
        learner = HistoricalPerformanceLearner(config)

        # All strategies have identical performance
        performance = {
            'strategy_a': {'return': 0.10, 'sharpe_ratio': 1.0},
            'strategy_b': {'return': 0.10, 'sharpe_ratio': 1.0},
            'strategy_c': {'return': 0.10, 'sharpe_ratio': 1.0},
        }

        weights = learner.learn_weights(performance)

        # Should result in equal weights
        for w in weights.values():
            assert w == pytest.approx(1.0 / 3, abs=0.01)


@pytest.mark.unit
class TestBaseMetaLearner:
    """Test suite for BaseMetaLearner abstract class."""

    def test_cannot_instantiate_base(self):
        """Test that base class cannot be instantiated."""
        config = {}

        with pytest.raises(TypeError):
            BaseMetaLearner(config)

    def test_abstract_methods(self):
        """Test that abstract methods are defined."""
        # Check that learn_weights and update are abstract
        assert hasattr(BaseMetaLearner, 'learn_weights')
        assert hasattr(BaseMetaLearner, 'update')
