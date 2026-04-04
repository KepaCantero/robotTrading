"""
Test script to verify López de Prado sample weights integration.

This test verifies that:
1. Sample weights are correctly calculated from triple barrier events
2. Sample weights are properly passed to model training
3. All supported algorithms accept and use sample weights
"""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

# Skip all tests if lightgbm is not available
pytest.importorskip("lightgbm")

from app.domain.strategies.learning.supervised_learning_engine import SupervisedLearningEngine


class TestSampleWeightsIntegration:
    """Test López de Prado sample weights integration in ML pipeline."""

    @pytest.fixture
    def sample_training_data(self):
        """Create sample training data with metadata."""
        np.random.seed(42)

        # Create features
        n_samples = 100
        n_features = 10
        features = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f'feature_{i}' for i in range(n_features)],
        )

        # Create binary labels
        labels = pd.Series(np.random.randint(0, 2, n_samples), name='label')

        # Create metadata for sample weight calculation
        # events: timestamp for each sample
        events = pd.date_range('2024-01-01', periods=n_samples, freq='1H')

        # labels_df: DataFrame with bars_to_barrier and label
        labels_df = pd.DataFrame(
            {'bars_to_barrier': np.random.randint(1, 10, n_samples), 'label': labels.values},
            index=events,
        )

        # prices: price series aligned with events
        prices = pd.Series(
            100 + np.random.randn(n_samples + 100).cumsum(),
            index=pd.date_range('2024-01-01', periods=n_samples + 100, freq='1H'),
        )

        metadata = {'events': events, 'labels': labels_df, 'prices': prices}

        return {'features': features, 'labels': labels, 'metadata': metadata}

    def test_sample_weights_calculation(self, sample_training_data):
        """Test that sample weights are calculated correctly."""
        config = {
            'algorithm': 'random_forest',
            'model_parameters': {'n_estimators': 10, 'max_depth': 3},
        }

        engine = SupervisedLearningEngine(config)

        # Mock the calculate_sample_weights_uniqueness function
        with patch(
            'app.strategies.momentum_modular.learning.supervised_learning_engine.calculate_sample_weights_uniqueness'
        ) as mock_calc:
            # Set up mock return value
            mock_weights = pd.Series(np.ones(len(sample_training_data['labels'])))
            mock_calc.return_value = mock_weights

            # Train the model
            engine.train(sample_training_data)

            # Verify that calculate_sample_weights_uniqueness was called
            mock_calc.assert_called_once()
            call_args = mock_calc.call_args

            # Verify correct arguments were passed
            assert 'events' in call_args.kwargs
            assert 'labels' in call_args.kwargs
            assert 'price_series' in call_args.kwargs

    def test_sample_weights_stored(self, sample_training_data):
        """Test that sample weights are stored in the engine."""
        config = {
            'algorithm': 'random_forest',
            'model_parameters': {'n_estimators': 10, 'max_depth': 3},
        }

        engine = SupervisedLearningEngine(config)

        with patch(
            'app.strategies.momentum_modular.learning.supervised_learning_engine.calculate_sample_weights_uniqueness'
        ) as mock_calc:
            mock_weights = pd.Series(
                np.random.uniform(0.5, 1.5, len(sample_training_data['labels']))
            )
            mock_calc.return_value = mock_weights

            # Train the model
            engine.train(sample_training_data)

            # Verify sample weights are stored
            assert engine.sample_weights_ is not None
            assert len(engine.sample_weights_) == len(sample_training_data['labels'])

    def test_sample_weights_in_metrics(self, sample_training_data):
        """Test that sample weight statistics are included in metrics."""
        config = {
            'algorithm': 'random_forest',
            'model_parameters': {'n_estimators': 10, 'max_depth': 3},
        }

        engine = SupervisedLearningEngine(config)

        with patch(
            'app.strategies.momentum_modular.learning.supervised_learning_engine.calculate_sample_weights_uniqueness'
        ) as mock_calc:
            mock_weights = pd.Series(
                np.random.uniform(0.5, 1.5, len(sample_training_data['labels']))
            )
            mock_calc.return_value = mock_weights

            # Train the model
            metrics = engine.train(sample_training_data)

            # Verify sample weight statistics are in metrics
            assert 'sample_weights_mean' in metrics
            assert 'sample_weights_std' in metrics
            assert 'sample_weights_min' in metrics
            assert 'sample_weights_max' in metrics

            # Verify values are reasonable
            assert metrics['sample_weights_mean'] > 0
            assert metrics['sample_weights_std'] >= 0

    def test_sample_weights_random_forest(self, sample_training_data):
        """Test that RandomForest accepts sample weights."""
        config = {
            'algorithm': 'random_forest',
            'model_parameters': {'n_estimators': 10, 'max_depth': 3},
        }

        engine = SupervisedLearningEngine(config)

        with patch(
            'app.strategies.momentum_modular.learning.supervised_learning_engine.calculate_sample_weights_uniqueness'
        ) as mock_calc:
            mock_weights = pd.Series(
                np.random.uniform(0.5, 1.5, len(sample_training_data['labels']))
            )
            mock_calc.return_value = mock_weights

            # Train the model - should not raise an error
            metrics = engine.train(sample_training_data)

            # Verify model is trained
            assert engine.is_trained
            assert 'accuracy' in metrics

    def test_sample_weights_xgboost(self, sample_training_data):
        """Test that XGBoost accepts sample weights."""
        config = {'algorithm': 'xgboost', 'model_parameters': {'n_estimators': 10, 'max_depth': 3}}

        engine = SupervisedLearningEngine(config)

        with patch(
            'app.strategies.momentum_modular.learning.supervised_learning_engine.calculate_sample_weights_uniqueness'
        ) as mock_calc:
            mock_weights = pd.Series(
                np.random.uniform(0.5, 1.5, len(sample_training_data['labels']))
            )
            mock_calc.return_value = mock_weights

            # Train the model - should not raise an error
            metrics = engine.train(sample_training_data)

            # Verify model is trained
            assert engine.is_trained
            assert 'accuracy' in metrics

    def test_sample_weights_gradient_boosting(self, sample_training_data):
        """Test that GradientBoosting accepts sample weights."""
        config = {
            'algorithm': 'gradient_boosting',
            'model_parameters': {'n_estimators': 10, 'max_depth': 3},
        }

        engine = SupervisedLearningEngine(config)

        with patch(
            'app.strategies.momentum_modular.learning.supervised_learning_engine.calculate_sample_weights_uniqueness'
        ) as mock_calc:
            mock_weights = pd.Series(
                np.random.uniform(0.5, 1.5, len(sample_training_data['labels']))
            )
            mock_calc.return_value = mock_weights

            # Train the model - should not raise an error
            metrics = engine.train(sample_training_data)

            # Verify model is trained
            assert engine.is_trained
            assert 'accuracy' in metrics

    def test_no_metadata_no_weights(self, sample_training_data):
        """Test that training works without metadata (no sample weights)."""
        config = {
            'algorithm': 'random_forest',
            'model_parameters': {'n_estimators': 10, 'max_depth': 3},
        }

        engine = SupervisedLearningEngine(config)

        # Remove metadata
        training_data = {
            'features': sample_training_data['features'],
            'labels': sample_training_data['labels'],
        }

        # Train the model - should work without sample weights
        metrics = engine.train(training_data)

        # Verify model is trained but no sample weights
        assert engine.is_trained
        assert engine.sample_weights_ is None
        assert 'sample_weights_mean' not in metrics
        assert 'accuracy' in metrics

    def test_incomplete_metadata_no_weights(self, sample_training_data):
        """Test that incomplete metadata doesn't crash training."""
        config = {
            'algorithm': 'random_forest',
            'model_parameters': {'n_estimators': 10, 'max_depth': 3},
        }

        engine = SupervisedLearningEngine(config)

        # Create incomplete metadata
        training_data = {
            'features': sample_training_data['features'],
            'labels': sample_training_data['labels'],
            'metadata': {
                'events': pd.date_range('2024-01-01', periods=10)
            },  # Missing labels and prices
        }

        # Train the model - should work without sample weights
        metrics = engine.train(training_data)

        # Verify model is trained but no sample weights
        assert engine.is_trained
        assert engine.sample_weights_ is None
        assert 'accuracy' in metrics

    def test_sample_weights_with_validation_data(self, sample_training_data):
        """Test sample weights work with separate validation data."""
        config = {
            'algorithm': 'random_forest',
            'model_parameters': {'n_estimators': 10, 'max_depth': 3},
        }

        engine = SupervisedLearningEngine(config)

        with patch(
            'app.strategies.momentum_modular.learning.supervised_learning_engine.calculate_sample_weights_uniqueness'
        ) as mock_calc:
            mock_weights = pd.Series(
                np.random.uniform(0.5, 1.5, len(sample_training_data['labels']))
            )
            mock_calc.return_value = mock_weights

            # Split data manually
            n = len(sample_training_data['features'])
            train_size = int(n * 0.8)

            train_data = {
                'features': sample_training_data['features'].iloc[:train_size],
                'labels': sample_training_data['labels'].iloc[:train_size],
                'metadata': sample_training_data['metadata'],
            }

            val_data = {
                'features': sample_training_data['features'].iloc[train_size:],
                'labels': sample_training_data['labels'].iloc[train_size:],
            }

            # Train with validation data
            metrics = engine.train(train_data, validation_data=val_data)

            # Verify model is trained
            assert engine.is_trained
            assert 'accuracy' in metrics


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
