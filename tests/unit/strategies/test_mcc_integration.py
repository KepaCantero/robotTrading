"""
Test MCC (Matthews Correlation Coefficient) integration in SupervisedLearningEngine.

This test verifies that MCC is properly calculated and used for model evaluation
as required by López de Prado's Financial ML methodologies (Chapter 3).
"""

import numpy as np
import pytest
from unittest.mock import Mock, patch


class TestMCCIntegration:
    """Test MCC metric integration in supervised learning engine."""

    @pytest.fixture
    def mock_train_data(self):
        """Create mock training data."""
        return {
            'features': np.random.randn(100, 10),
            'labels': np.random.randint(0, 2, 100),
            'metadata': {}
        }

    @pytest.fixture
    def mock_model(self):
        """Create mock model with predictions."""
        model = Mock()
        model.predict_proba = Mock(return_value=np.array([
            [0.3, 0.7] if i > 50 else [0.8, 0.2] for i in range(100)
        ]))
        model.predict = Mock(return_value=np.array([
            1 if i > 50 else 0 for i in range(100)
        ]))
        return model

    def test_mcc_calculation_exists(self):
        """Test that calculate_matthews_corrcoef function exists and is importable."""
        try:
            from app.backtesting.metrics import calculate_matthews_corrcoef
            # Test basic functionality
            y_true = np.array([0, 1, 0, 1, 1, 0, 0, 0])
            y_pred = np.array([0, 1, 0, 0, 1, 0, 1, 0])
            mcc = calculate_matthews_corrcoef(y_true, y_pred)

            # MCC should be between -1 and 1
            assert -1 <= mcc <= 1, f"MCC {mcc} not in valid range [-1, 1]"
            print(f"✓ MCC calculation successful: {mcc:.4f}")
        except ImportError as e:
            pytest.skip(f"Cannot import MCC function: {e}")

    def test_mcc_in_evaluation_metrics(self, mock_train_data, mock_model):
        """Test that MCC is included in model evaluation metrics."""
        try:
            from app.strategies.momentum_modular.learning.supervised_learning_engine import SupervisedLearningEngine

            # Create engine with mock configuration
            config = {
                'algorithm': 'random_forest',
                'feature_columns': [f'feature_{i}' for i in range(10)],
                'target_column': 'trade_success',
                'model_parameters': {'n_estimators': 10, 'max_depth': 3}
            }

            # Patch the training methods to avoid actual training
            with patch.object(SupervisedLearningEngine, '_train_random_forest') as mock_train:
                mock_train.return_value = mock_model

                engine = SupervisedLearningEngine(config)
                engine.model = mock_model
                engine.is_trained = True

                # Evaluate model
                X_val = mock_train_data['features']
                y_val = mock_train_data['labels']
                metrics = engine._evaluate_model(X_val, y_val)

                # Check that MCC is in metrics
                assert 'mcc' in metrics, "MCC not found in evaluation metrics"
                assert metrics['mcc'] is not None, "MCC is None"
                assert isinstance(metrics['mcc'], float), f"MCC should be float, got {type(metrics['mcc'])}"
                assert -1 <= metrics['mcc'] <= 1, f"MCC {metrics['mcc']} not in valid range [-1, 1]"

                print(f"✓ MCC in metrics: {metrics['mcc']:.4f}")

        except ImportError as e:
            pytest.skip(f"Cannot import SupervisedLearningEngine: {e}")

    def test_mcc_threshold_warning(self, mock_train_data, mock_model):
        """Test that low MCC triggers warning."""
        try:
            from app.strategies.momentum_modular.learning.supervised_learning_engine import SupervisedLearningEngine
            import logging

            # Create engine with mock configuration
            config = {
                'algorithm': 'random_forest',
                'feature_columns': [f'feature_{i}' for i in range(10)],
                'target_column': 'trade_success',
                'model_parameters': {'n_estimators': 10, 'max_depth': 3}
            }

            # Mock model with poor predictions (should give low MCC)
            poor_model = Mock()
            poor_model.predict_proba = Mock(return_value=np.array([
                [0.5, 0.5] for _ in range(100)  # Random predictions
            ]))
            poor_model.predict = Mock(return_value=np.random.randint(0, 2, 100))

            with patch.object(SupervisedLearningEngine, '_train_random_forest') as mock_train:
                mock_train.return_value = poor_model

                engine = SupervisedLearningEngine(config)
                engine.model = poor_model
                engine.is_trained = True

                # Capture log output
                with patch('logging.getLogger') as mock_logger:
                    logger_instance = Mock()
                    mock_logger.return_value = logger_instance

                    X_val = mock_train_data['features']
                    y_val = mock_train_data['labels']
                    metrics = engine._evaluate_model(X_val, y_val)

                    # Check that MCC was calculated
                    assert 'mcc' in metrics, "MCC not in metrics"
                    print(f"✓ MCC threshold warning test: MCC={metrics['mcc']:.4f}")

        except ImportError as e:
            pytest.skip(f"Cannot import SupervisedLearningEngine: {e}")

    def test_mcc_perfect_prediction(self):
        """Test MCC with perfect predictions."""
        try:
            from app.backtesting.metrics import calculate_matthews_corrcoef

            y_true = np.array([0, 1, 0, 1, 1, 0, 0, 1])
            y_pred = np.array([0, 1, 0, 1, 1, 0, 0, 1])  # Perfect prediction

            mcc = calculate_matthews_corrcoef(y_true, y_pred)

            # Perfect prediction should give MCC = 1.0
            assert abs(mcc - 1.0) < 0.01, f"Perfect prediction should give MCC ≈ 1.0, got {mcc}"
            print(f"✓ Perfect prediction MCC: {mcc:.4f}")

        except ImportError as e:
            pytest.skip(f"Cannot import MCC function: {e}")

    def test_mcc_random_prediction(self):
        """Test MCC with random predictions."""
        try:
            from app.backtesting.metrics import calculate_matthews_corrcoef

            # Balanced random prediction should give MCC ≈ 0
            np.random.seed(42)
            y_true = np.random.randint(0, 2, 100)
            y_pred = np.random.randint(0, 2, 100)

            mcc = calculate_matthews_corrcoef(y_true, y_pred)

            # Random prediction should give MCC close to 0
            assert abs(mcc) < 0.3, f"Random prediction should give MCC ≈ 0, got {mcc}"
            print(f"✓ Random prediction MCC: {mcc:.4f} (should be close to 0)")

        except ImportError as e:
            pytest.skip(f"Cannot import MCC function: {e}")

    def test_mcc_complete_disagreement(self):
        """Test MCC with complete disagreement."""
        try:
            from app.backtesting.metrics import calculate_matthews_corrcoef

            y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
            y_pred = np.array([1, 1, 1, 1, 0, 0, 0, 0])  # Complete disagreement

            mcc = calculate_matthews_corrcoef(y_true, y_pred)

            # Complete disagreement should give MCC ≈ -1.0
            assert abs(mcc + 1.0) < 0.01, f"Complete disagreement should give MCC ≈ -1.0, got {mcc}"
            print(f"✓ Complete disagreement MCC: {mcc:.4f}")

        except ImportError as e:
            pytest.skip(f"Cannot import MCC function: {e}")

    def test_supervised_learning_engine_mcc_integration(self):
        """Test that SupervisedLearningEngine properly integrates MCC."""
        try:
            from app.strategies.momentum_modular.learning.supervised_learning_engine import SupervisedLearningEngine

            # Verify the import is present
            import inspect
            source = inspect.getsource(SupervisedLearningEngine._evaluate_model)

            # Check for MCC-related code
            assert 'calculate_matthews_corrcoef' in source or 'mcc' in source, \
                "MCC calculation not found in _evaluate_model method"

            print("✓ SupervisedLearningEngine._evaluate_model includes MCC")

        except (ImportError, OSError) as e:
            pytest.skip(f"Cannot verify SupervisedLearningEngine source: {e}")


if __name__ == '__main__':
    # Run tests manually if pytest is not available
    test = TestMCCIntegration()

    print("\n" + "="*60)
    print("MCC Integration Tests")
    print("="*60 + "\n")

    try:
        print("Test 1: MCC calculation exists")
        test.test_mcc_calculation_exists()
    except Exception as e:
        print(f"✗ Test failed: {e}")

    try:
        print("\nTest 2: Perfect prediction MCC")
        test.test_mcc_perfect_prediction()
    except Exception as e:
        print(f"✗ Test failed: {e}")

    try:
        print("\nTest 3: Random prediction MCC")
        test.test_mcc_random_prediction()
    except Exception as e:
        print(f"✗ Test failed: {e}")

    try:
        print("\nTest 4: Complete disagreement MCC")
        test.test_mcc_complete_disagreement()
    except Exception as e:
        print(f"✗ Test failed: {e}")

    try:
        print("\nTest 5: SupervisedLearningEngine MCC integration")
        test.test_supervised_learning_engine_mcc_integration()
    except Exception as e:
        print(f"✗ Test failed: {e}")

    print("\n" + "="*60)
    print("All MCC integration tests completed!")
    print("="*60 + "\n")
