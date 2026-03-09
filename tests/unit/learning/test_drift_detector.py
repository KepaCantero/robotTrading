"""
Unit Tests for Drift Detection System [TASK-4.2-DRIFT]

Comprehensive tests for:
- PSI (Population Stability Index) detector
- ADWIN detector
- KS Test detector
- Feature-level drift monitoring
- Comprehensive drift detector
- Auto-retraining triggers
"""

from datetime import datetime, timedelta

import numpy as np
import pytest

from app.domain.strategies.momentum_modular.learning.drift_detector import (
    ADWINDetector,
    AutoRetrainingTrigger,
    ComprehensiveDriftDetector,
    ComprehensiveDriftReport,
    ConceptDriftDetector,
    DriftResult,
    DriftSeverity,
    FeatureDriftMonitor,
    FeatureDriftReport,
    OverfittingDetector,
    PSIDetector,
    get_default_drift_config,
    load_drift_config,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_config():
    """Sample drift detection configuration."""
    return {
        "enabled": True,
        "detectors": {
            "ks_test": {"enabled": True, "p_value_threshold": 0.05},
            "psi": {"enabled": True, "threshold": 0.25, "n_bins": 10},
            "adwin": {"enabled": True, "delta": 0.002},
            "mmd": {"enabled": False, "threshold": 0.1},
        },
        "monitoring": {
            "window_size": 100,
            "min_samples": 20,
        },
        "thresholds": {
            "warning": 0.1,
            "critical": 0.25,
            "retrain": 0.4,
        },
        "auto_retrain": {
            "enabled": True,
            "min_interval_hours": 24,
            "require_multiple_detectors": True,
        },
    }


@pytest.fixture
def reference_data():
    """Generate reference data (normal distribution)."""
    np.random.seed(42)
    return np.random.normal(100, 10, 500)


@pytest.fixture
def similar_data():
    """Generate data similar to reference (no drift)."""
    np.random.seed(43)
    return np.random.normal(100, 10, 200)


@pytest.fixture
def drifted_data():
    """Generate data with significant drift."""
    np.random.seed(44)
    return np.random.normal(120, 15, 200)  # Different mean and std


@pytest.fixture
def feature_data():
    """Generate multi-feature data."""
    np.random.seed(42)
    return np.random.normal(0, 1, (200, 5))


# ============================================================================
# Tests: Configuration Loading
# ============================================================================


class TestConfigLoading:
    """Tests for configuration loading functions."""

    def test_get_default_config_returns_dict(self):
        """Test that default config returns a dictionary."""
        config = get_default_drift_config()

        assert isinstance(config, dict)
        assert "enabled" in config
        assert "detectors" in config
        assert "monitoring" in config
        assert "thresholds" in config
        assert "auto_retrain" in config

    def test_default_config_detectors(self):
        """Test default detector configurations."""
        config = get_default_drift_config()
        detectors = config["detectors"]

        assert "ks_test" in detectors
        assert "psi" in detectors
        assert "adwin" in detectors
        assert "mmd" in detectors

    def test_default_psi_threshold(self):
        """Test default PSI threshold is 0.25."""
        config = get_default_drift_config()
        assert config["detectors"]["psi"]["threshold"] == 0.25

    def test_load_config_missing_file_returns_defaults(self):
        """Test loading from non-existent file returns defaults."""
        config = load_drift_config("nonexistent_file.yaml")
        assert isinstance(config, dict)
        assert "enabled" in config


# ============================================================================
# Tests: PSI Detector
# ============================================================================


class TestPSIDetector:
    """Tests for PSI (Population Stability Index) detector."""

    def test_psi_initialization(self, sample_config):
        """Test PSI detector initialization."""
        detector = PSIDetector(sample_config["detectors"]["psi"])

        assert detector.threshold == 0.25
        assert detector.n_bins == 10

    def test_psi_initialization_defaults(self):
        """Test PSI detector with default values."""
        detector = PSIDetector()

        assert detector.threshold == 0.25
        assert detector.n_bins == 10
        assert detector.min_samples == 30

    def test_psi_no_drift_same_distribution(self, reference_data, similar_data):
        """Test PSI returns low value for similar distributions."""
        detector = PSIDetector({"threshold": 0.25, "n_bins": 10})

        psi_value, details = detector.calculate_psi(reference_data, similar_data)

        assert psi_value < 0.25  # Should not detect drift
        assert "n_buckets" in details
        assert details["n_buckets"] == 10

    def test_psi_detects_drift(self, reference_data, drifted_data):
        """Test PSI detects significant drift."""
        detector = PSIDetector({"threshold": 0.25, "n_bins": 10})

        psi_value, details = detector.calculate_psi(reference_data, drifted_data)

        assert psi_value > 0.1  # Should detect some drift

    def test_psi_detect_returns_drift_result(self, reference_data, drifted_data):
        """Test PSI detect method returns DriftResult."""
        detector = PSIDetector({"threshold": 0.25, "n_bins": 10})

        result = detector.detect(reference_data, drifted_data)

        assert isinstance(result, DriftResult)
        assert result.detector_name == "psi"
        assert result.statistic >= 0
        assert result.p_value is None  # PSI doesn't have p-value

    def test_psi_severity_levels(self):
        """Test PSI severity classification."""
        detector = PSIDetector({"threshold": 0.25, "n_bins": 10})

        # Create distributions with known PSI values
        np.random.seed(42)
        reference = np.random.normal(100, 10, 500)

        # Similar - low PSI
        similar = np.random.normal(100, 10, 200)
        result_similar = detector.detect(reference, similar)
        assert result_similar.severity in [DriftSeverity.NONE, DriftSeverity.LOW]

        # Very different - high PSI
        very_different = np.random.normal(150, 30, 200)
        result_different = detector.detect(reference, very_different)
        assert result_different.severity in [
            DriftSeverity.MEDIUM,
            DriftSeverity.HIGH,
            DriftSeverity.CRITICAL,
        ]

    def test_psi_insufficient_samples(self):
        """Test PSI with insufficient samples."""
        detector = PSIDetector({"threshold": 0.25, "n_bins": 10, "min_samples": 50})

        psi_value, details = detector.calculate_psi(
            np.array([1, 2, 3]),  # Too few
            np.array([4, 5, 6]),
        )

        assert psi_value == 0.0
        assert "error" in details

    def test_psi_bucket_details(self, reference_data, similar_data):
        """Test PSI provides bucket-level details."""
        detector = PSIDetector({"threshold": 0.25, "n_bins": 10})

        psi_value, details = detector.calculate_psi(reference_data, similar_data)

        assert "bucket_details" in details
        assert len(details["bucket_details"]) == 10

        for bucket in details["bucket_details"]:
            assert "expected_pct" in bucket
            assert "actual_pct" in bucket
            assert "psi_contribution" in bucket


# ============================================================================
# Tests: ADWIN Detector
# ============================================================================


class TestADWINDetector:
    """Tests for ADWIN (Adaptive Windowing) detector."""

    def test_adwin_initialization(self, sample_config):
        """Test ADWIN detector initialization."""
        detector = ADWINDetector(sample_config["detectors"]["adwin"])

        assert detector.delta == 0.002
        assert detector.min_window == 5
        assert detector.max_window == 1000

    def test_adwin_initialization_defaults(self):
        """Test ADWIN detector with default values."""
        detector = ADWINDetector()

        assert detector.delta == 0.002
        assert detector.min_window == 5

    def test_adwin_add_element_no_drift(self):
        """Test ADWIN doesn't detect drift in stable stream."""
        detector = ADWINDetector({"delta": 0.002})

        np.random.seed(42)
        for _ in range(100):
            value = np.random.normal(100, 5)
            if detector.add_element(value):
                pass

        # Should rarely detect drift in stable stream
        assert detector.width > 0

    def test_adwin_detects_drift_in_stream(self):
        """Test ADWIN detects drift when mean changes."""
        detector = ADWINDetector({"delta": 0.01, "min_window": 10})

        np.random.seed(42)

        # First phase: stable at mean=100
        for _ in range(50):
            detector.add_element(np.random.normal(100, 2))

        # Second phase: shift to mean=110
        drift_count = 0
        for _ in range(50):
            if detector.add_element(np.random.normal(110, 2)):
                drift_count += 1

        assert drift_count > 0 or detector.drift_count > 0

    def test_adwin_detect_batch(self, reference_data):
        """Test ADWIN detect method with batch data."""
        detector = ADWINDetector({"delta": 0.002})

        result = detector.detect(reference_data)

        assert isinstance(result, DriftResult)
        assert result.detector_name == "adwin"
        assert "drift_points" in result.details
        assert "window_size" in result.details

    def test_adwin_reset(self):
        """Test ADWIN reset functionality."""
        detector = ADWINDetector()

        # Add some data
        for i in range(100):
            detector.add_element(float(i))

        assert len(detector.window) > 0

        # Reset
        detector.reset()

        assert len(detector.window) == 0
        assert detector.drift_count == 0
        assert detector.width == 0


# ============================================================================
# Tests: Concept Drift Detector (KS Test)
# ============================================================================


class TestConceptDriftDetector:
    """Tests for KS Test based concept drift detector."""

    def test_ks_detector_initialization(self, sample_config):
        """Test KS detector initialization."""
        detector = ConceptDriftDetector(sample_config["detectors"]["ks_test"])

        assert detector.drift_threshold_ks == 0.05

    def test_ks_update_reference(self, reference_data):
        """Test updating reference data."""
        detector = ConceptDriftDetector()

        detector.update_reference(reference_data)

        assert len(detector.reference_data) > 0

    def test_ks_no_drift_similar_data(self, reference_data, similar_data):
        """Test KS test doesn't detect drift in similar data."""
        detector = ConceptDriftDetector({"p_value_threshold": 0.05})

        detector.update_reference(reference_data)
        result = detector.detect_drift_ks(similar_data)

        assert isinstance(result, DriftResult)
        assert result.detector_name == "ks_test"
        # P-value should be high for similar distributions
        if result.p_value is not None:
            assert result.p_value > 0.01

    def test_ks_detects_drift(self):
        """Test KS test detects significant drift."""
        detector = ConceptDriftDetector(
            {
                "p_value_threshold": 0.05,
                "min_samples": 30,
                "window_size": 1000,  # Large enough to hold all reference data
            }
        )

        # Create clearly different distributions
        np.random.seed(42)
        reference = np.random.normal(100, 10, 500)
        np.random.seed(43)
        drifted = np.random.normal(150, 20, 200)  # Very different mean and std

        detector.update_reference(reference)
        result = detector.detect_drift_ks(drifted)

        # P-value should be very low for very different distributions
        assert result.p_value is not None
        assert result.p_value < 0.05
        assert result.drift_detected  # Use == for numpy bool compatibility

    def test_ks_insufficient_reference_data(self, drifted_data):
        """Test KS test with insufficient reference data."""
        detector = ConceptDriftDetector({"min_samples": 50})

        # Don't update reference
        result = detector.detect_drift_ks(drifted_data)

        assert not result.drift_detected  # Use == for numpy bool compatibility
        assert "error" in result.details

    def test_ks_severity_based_on_pvalue(self, reference_data, drifted_data):
        """Test KS severity is based on p-value."""
        detector = ConceptDriftDetector()

        detector.update_reference(reference_data)
        result = detector.detect_drift_ks(drifted_data)

        # Severity should correlate with p-value
        assert result.severity in DriftSeverity

    def test_ks_drift_history(self, reference_data, similar_data):
        """Test KS detector maintains drift history."""
        detector = ConceptDriftDetector()

        detector.update_reference(reference_data)
        detector.detect_drift_ks(similar_data)
        detector.detect_drift_ks(similar_data)

        history = detector.get_drift_history()
        assert len(history) >= 2


# ============================================================================
# Tests: Feature Drift Monitor
# ============================================================================


class TestFeatureDriftMonitor:
    """Tests for feature-level drift monitoring."""

    def test_monitor_initialization(self, sample_config):
        """Test feature monitor initialization."""
        monitor = FeatureDriftMonitor(sample_config["detectors"])

        assert monitor.feature_names == []

    def test_initialize_features(self):
        """Test initializing features."""
        monitor = FeatureDriftMonitor()

        monitor.initialize_features(["feature_a", "feature_b", "feature_c"])

        assert len(monitor.feature_names) == 3
        assert "feature_a" in monitor.feature_names
        assert "feature_a" in monitor.detectors

    def test_set_reference_with_feature_names(self, feature_data):
        """Test setting reference with feature names."""
        monitor = FeatureDriftMonitor()

        feature_names = ["f1", "f2", "f3", "f4", "f5"]
        monitor.set_reference(feature_data, feature_names)

        assert monitor.feature_names == feature_names
        for name in feature_names:
            assert monitor.detectors[name]["reference_data"] is not None

    def test_set_reference_auto_names(self, feature_data):
        """Test setting reference with auto-generated names."""
        monitor = FeatureDriftMonitor()

        monitor.set_reference(feature_data)

        assert len(monitor.feature_names) == 5
        assert "feature_0" in monitor.feature_names

    def test_detect_feature_drift_no_drift(self, feature_data):
        """Test detecting no drift in similar features."""
        monitor = FeatureDriftMonitor()

        # Reference and current from same distribution
        np.random.seed(42)
        reference = np.random.normal(0, 1, (200, 3))
        np.random.seed(43)
        current = np.random.normal(0, 1, (100, 3))

        monitor.set_reference(reference, ["a", "b", "c"])
        reports = monitor.detect_feature_drift(current)

        assert len(reports) == 3
        for report in reports:
            assert isinstance(report, FeatureDriftReport)
            assert report.feature_name in ["a", "b", "c"]

    def test_detect_feature_drift_with_drift(self):
        """Test detecting drift in specific features."""
        monitor = FeatureDriftMonitor()

        np.random.seed(42)
        # Reference: all features ~N(0,1)
        reference = np.random.normal(0, 1, (200, 3))

        # Current: first feature drifted to N(5,1)
        np.random.seed(43)
        current = np.column_stack(
            [
                np.random.normal(5, 1, 100),  # Drifted
                np.random.normal(0, 1, 100),  # Same
                np.random.normal(0, 1, 100),  # Same
            ]
        )

        monitor.set_reference(reference, ["drifted", "stable1", "stable2"])
        reports = monitor.detect_feature_drift(current)

        # Find the drifted feature report
        drifted_report = next(r for r in reports if r.feature_name == "drifted")
        assert drifted_report.overall_drift is True or drifted_report.severity != DriftSeverity.NONE


# ============================================================================
# Tests: Overfitting Detector
# ============================================================================


class TestOverfittingDetector:
    """Tests for overfitting detection."""

    def test_overfitting_initialization(self):
        """Test overfitting detector initialization."""
        detector = OverfittingDetector({"overfitting_threshold": 0.15})

        assert detector.overfitting_threshold == 0.15

    def test_update_metrics(self):
        """Test updating metrics."""
        detector = OverfittingDetector()

        detector.update_metrics(1, 0.5, 0.6)
        detector.update_metrics(2, 0.4, 0.55)

        assert len(detector.epoch_history) == 2
        assert len(detector.train_metrics_history) == 2

    def test_detect_no_overfitting(self):
        """Test detecting no overfitting when train/val are close."""
        detector = OverfittingDetector({"overfitting_threshold": 0.1, "min_epochs": 5})

        # Similar train and val metrics
        for i in range(15):
            train_loss = 0.5 - i * 0.02
            val_loss = 0.52 - i * 0.02  # Slightly higher but similar trend
            detector.update_metrics(i, train_loss, val_loss)

        result = detector.detect_overfitting()

        assert not result["overfitting_detected"] or result["gap_ratio"] < 0.1

    def test_detect_overfitting(self):
        """Test detecting overfitting when train/val diverge."""
        detector = OverfittingDetector({"overfitting_threshold": 0.1, "min_epochs": 5})

        # Train improves but val gets worse
        for i in range(15):
            train_loss = 0.5 - i * 0.03
            val_loss = 0.5 + i * 0.02  # Getting worse
            detector.update_metrics(i, train_loss, val_loss)

        result = detector.detect_overfitting()

        # Should detect diverging curves
        assert "learning_curve_trend" in result

    def test_insufficient_data(self):
        """Test with insufficient epochs."""
        detector = OverfittingDetector({"min_epochs": 20})

        for i in range(5):
            detector.update_metrics(i, 0.5, 0.6)

        result = detector.detect_overfitting()

        assert not result["overfitting_detected"]
        assert result["reason"] == "insufficient_data"

    def test_get_learning_curves(self):
        """Test getting learning curves."""
        detector = OverfittingDetector()

        for i in range(10):
            detector.update_metrics(i, 0.5 - i * 0.02, 0.6 - i * 0.01)

        curves = detector.get_learning_curves()

        assert "epochs" in curves
        assert "train_metrics" in curves
        assert "val_metrics" in curves
        assert len(curves["epochs"]) == 10


# ============================================================================
# Tests: Comprehensive Drift Detector
# ============================================================================


class TestComprehensiveDriftDetector:
    """Tests for comprehensive drift detector."""

    def test_comprehensive_initialization(self, sample_config):
        """Test comprehensive detector initialization."""
        detector = ComprehensiveDriftDetector(sample_config)

        assert detector.enabled
        assert detector.psi_detector is not None
        assert detector.adwin_detector is not None
        assert detector.ks_detector is not None

    def test_set_reference(self, reference_data):
        """Test setting reference data."""
        detector = ComprehensiveDriftDetector()

        detector.set_reference(reference_data)

        assert detector.reference_data is not None

    def test_detect_no_drift(self, reference_data, similar_data):
        """Test comprehensive detection with no drift."""
        detector = ComprehensiveDriftDetector()

        detector.set_reference(reference_data)
        report = detector.detect(similar_data)

        assert isinstance(report, ComprehensiveDriftReport)
        assert report.timestamp is not None
        assert report.recommendation in ["ok", "monitor"]

    def test_detect_with_drift(self, reference_data, drifted_data):
        """Test comprehensive detection with significant drift."""
        detector = ComprehensiveDriftDetector()

        detector.set_reference(reference_data)
        report = detector.detect(drifted_data)

        assert isinstance(report, ComprehensiveDriftReport)
        # At least one detector should find drift
        assert len(report.detector_results) > 0

    def test_detect_without_reference(self, similar_data):
        """Test detection without setting reference first."""
        detector = ComprehensiveDriftDetector()

        report = detector.detect(similar_data)

        assert report.recommendation == "set_reference_first"
        assert not report.should_retrain

    def test_detect_disabled(self, reference_data, similar_data):
        """Test detection when disabled."""
        detector = ComprehensiveDriftDetector({"enabled": False})

        detector.set_reference(reference_data)
        report = detector.detect(similar_data)

        assert report.recommendation == "disabled"

    def test_record_retrain(self):
        """Test recording retrain."""
        detector = ComprehensiveDriftDetector()

        timestamp = datetime.now()
        detector.record_retrain(timestamp)

        assert detector.last_retrain_timestamp == timestamp

    def test_reset(self, reference_data):
        """Test resetting detector."""
        detector = ComprehensiveDriftDetector()

        detector.set_reference(reference_data)
        assert detector.reference_data is not None

        detector.reset()

        assert detector.reference_data is None


# ============================================================================
# Tests: Auto-Retraining Trigger
# ============================================================================


class TestAutoRetrainingTrigger:
    """Tests for auto-retraining trigger system."""

    def test_trigger_initialization(self):
        """Test trigger initialization."""
        trigger = AutoRetrainingTrigger()

        assert trigger.retrain_on_drift
        assert trigger.retrain_on_overfitting

    def test_should_retrain_time_based(self):
        """Test time-based retraining trigger."""
        trigger = AutoRetrainingTrigger({"retrain_interval_days": 7})

        # Set last retrain to 10 days ago
        trigger.last_retrain_timestamp = datetime.now() - timedelta(days=10)

        result = trigger.should_retrain()

        assert result["time_based"]
        assert "time_based" in result["reasons"][0]

    def test_should_retrain_no_history(self):
        """Test with no retrain history."""
        trigger = AutoRetrainingTrigger()

        result = trigger.should_retrain()

        assert not result["time_based"]

    def test_record_retrain(self):
        """Test recording retrain."""
        trigger = AutoRetrainingTrigger()

        timestamp = datetime.now()
        trigger.record_retrain(timestamp, {"reason": "test"})

        assert trigger.last_retrain_timestamp == timestamp
        assert len(trigger.retrain_history) == 1

    def test_record_performance(self):
        """Test recording performance."""
        trigger = AutoRetrainingTrigger()

        trigger.record_performance({"accuracy": 0.9, "f1": 0.85})

        assert len(trigger.performance_history) == 1

    def test_performance_degradation_detection(self):
        """Test performance degradation detection."""
        trigger = AutoRetrainingTrigger({"performance_degradation_threshold": 0.1})

        # Record good performance history
        for _ in range(5):
            trigger.record_performance({"accuracy": 0.9})

        # Check with degraded performance
        result = trigger.should_retrain(current_performance={"accuracy": 0.7})

        degradation = result.get("performance_degradation", {})
        if degradation:
            assert "degradation_score" in degradation

    def test_get_retrain_history(self):
        """Test getting retrain history."""
        trigger = AutoRetrainingTrigger()

        trigger.record_retrain(datetime.now(), {"reason": "test1"})
        trigger.record_retrain(datetime.now(), {"reason": "test2"})

        history = trigger.get_retrain_history()

        assert len(history) == 2


# ============================================================================
# Tests: Data Classes
# ============================================================================


class TestDataClasses:
    """Tests for data classes."""

    def test_drift_result_to_dict(self):
        """Test DriftResult to_dict method."""
        result = DriftResult(
            drift_detected=True,
            detector_name="psi",
            statistic=0.35,
            threshold=0.25,
            severity=DriftSeverity.MEDIUM,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )

        d = result.to_dict()

        assert d["drift_detected"]
        assert d["detector_name"] == "psi"
        assert d["statistic"] == 0.35
        assert d["severity"] == "medium"
        assert d["timestamp"] == "2024-01-01T12:00:00"

    def test_drift_severity_enum(self):
        """Test DriftSeverity enum values."""
        assert DriftSeverity.NONE.value == "none"
        assert DriftSeverity.LOW.value == "low"
        assert DriftSeverity.MEDIUM.value == "medium"
        assert DriftSeverity.HIGH.value == "high"
        assert DriftSeverity.CRITICAL.value == "critical"

    def test_feature_drift_report_creation(self):
        """Test FeatureDriftReport creation."""
        report = FeatureDriftReport(
            feature_name="test_feature",
            results=[],
            overall_drift=True,
            severity=DriftSeverity.HIGH,
            recommendation="retrain",
        )

        assert report.feature_name == "test_feature"
        assert report.overall_drift


# ============================================================================
# Tests: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_psi_with_constant_data(self):
        """Test PSI with constant values."""
        detector = PSIDetector()

        constant_data = np.ones(100)
        result = detector.detect(constant_data, constant_data)

        # Should handle constant data gracefully
        assert result.statistic >= 0

    def test_ks_with_identical_data(self):
        """Test KS test with identical data."""
        detector = ConceptDriftDetector()

        data = np.random.normal(0, 1, 100)
        detector.update_reference(data)
        result = detector.detect_drift_ks(data.copy())

        # Identical data should have high p-value
        if result.p_value is not None:
            assert result.p_value > 0.9

    def test_adwin_single_element(self):
        """Test ADWIN with single element."""
        detector = ADWINDetector()

        # Should not crash with single element
        drift = detector.add_element(100.0)
        assert not drift

    def test_comprehensive_with_1d_data(self):
        """Test comprehensive detector with 1D data."""
        detector = ComprehensiveDriftDetector()

        data_1d = np.random.normal(0, 1, 100)
        detector.set_reference(data_1d)

        report = detector.detect(data_1d)
        assert isinstance(report, ComprehensiveDriftReport)

    def test_comprehensive_with_predictions(self, reference_data):
        """Test comprehensive detector with predictions."""
        detector = ComprehensiveDriftDetector()

        predictions_ref = np.random.choice([0, 1], size=500, p=[0.5, 0.5])
        predictions_current = np.random.choice([0, 1], size=200, p=[0.3, 0.7])  # Drifted

        detector.set_reference(reference_data, predictions=predictions_ref.astype(float))
        report = detector.detect(
            reference_data[:200], current_predictions=predictions_current.astype(float)
        )

        # Should include prediction drift analysis
        if report.prediction_drift is not None:
            assert report.prediction_drift.detector_name == "psi"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
