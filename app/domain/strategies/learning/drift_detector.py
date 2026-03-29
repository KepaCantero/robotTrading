"""
DriftDetector - Sistema de detección de concept drift y data drift [TASK-4.2-DRIFT]

Detecta:
1. Concept drift: Cambios en la distribución de datos (KS test, PSI, ADWIN, MMD)
2. Feature drift: Cambios en features individuales
3. Prediction drift: Cambios en distribución de predicciones
4. Overfitting: Gap entre train/val, learning curves
5. Auto-retraining triggers: Decide cuándo reentrenar modelos

Detectores implementados:
- KS Test (Kolmogorov-Smirnov): Compara distribuciones
- PSI (Population Stability Index): Estándar en finanzas
- ADWIN (Adaptive Windowing): Para streaming data
- MMD (Maximum Mean Discrepancy): Compara en RKHS
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml
from scipy.stats import ks_2samp

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration Loading
# ============================================================================


def load_drift_config(config_path: str = "config/drift_detection.yaml") -> dict[str, Any]:
    """Load drift detection configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Drift config not found at {config_path}, using defaults")
        return get_default_drift_config()

    with open(path) as f:
        return yaml.safe_load(f)


def get_default_drift_config() -> dict[str, Any]:
    """Return default drift detection configuration."""
    return {
        "enabled": True,
        "detectors": {
            "ks_test": {
                "enabled": True,
                "p_value_threshold": 0.05,
            },
            "psi": {
                "enabled": True,
                "threshold": 0.25,  # >0.25 = significant drift
                "n_bins": 10,
            },
            "adwin": {
                "enabled": True,
                "delta": 0.002,  # Confidence parameter
            },
            "mmd": {
                "enabled": False,  # Computationally expensive
                "threshold": 0.1,
            },
        },
        "monitoring": {
            "window_size": 500,
            "min_samples": 30,
            "check_interval_minutes": 60,
            "feature_level": True,
            "prediction_level": True,
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


def load_overfitting_config(
    config_path: str = "config/overfitting_detection.yaml",
) -> dict[str, Any]:
    """Load overfitting detection configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Overfitting config not found at {config_path}, using defaults")
        return get_default_overfitting_config()

    with open(path) as f:
        return yaml.safe_load(f)


def get_default_overfitting_config() -> dict[str, Any]:
    """Return default overfitting detection configuration."""
    return {
        "enabled": True,
        "detection": {
            "train_val_gap_threshold": 0.1,  # 10% divergence triggers detection
            "test_set_analysis": True,
            "cross_validation_enabled": True,
            "cv_folds": 5,
        },
        "learning_curves": {
            "min_epochs": 10,
            "analyze_trends": True,
            "extrapolation_window": 5,
            "divergence_sensitivity": 0.05,
        },
        "regularization": {
            "monitor_l1": True,
            "monitor_l2": True,
            "analyze_weight_magnitudes": True,
        },
        "model_complexity": {
            "track_parameters": True,
            "track_layers": True,
            "complexity_penalty": 0.1,
        },
        "severity_thresholds": {
            "low": 20.0,  # Overfitting score for LOW severity
            "medium": 40.0,  # Overfitting score for MEDIUM severity
            "high": 60.0,  # Overfitting score for HIGH severity
            "critical": 80.0,  # Overfitting score for CRITICAL severity
        },
    }


# ============================================================================
# Data Classes
# ============================================================================


class DriftSeverity(Enum):
    """Severity levels for drift detection."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftResult:
    """Result from a drift detection check."""

    drift_detected: bool
    detector_name: str
    statistic: float
    p_value: Optional[float] = None
    threshold: float = 0.0
    severity: DriftSeverity = DriftSeverity.NONE
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "drift_detected": self.drift_detected,
            "detector_name": self.detector_name,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class FeatureDriftReport:
    """Report for feature-level drift analysis."""

    feature_name: str
    results: list[DriftResult]
    overall_drift: bool
    severity: DriftSeverity
    recommendation: str


@dataclass
class ComprehensiveDriftReport:
    """Comprehensive drift report combining all detectors."""

    timestamp: datetime
    overall_drift_detected: bool
    overall_severity: DriftSeverity
    recommendation: str  # 'ok', 'monitor', 'retrain'
    feature_reports: list[FeatureDriftReport]
    prediction_drift: Optional[DriftResult]
    detector_results: dict[str, DriftResult]
    should_retrain: bool


# ============================================================================
# PSI (Population Stability Index) Detector
# ============================================================================


class PSIDetector:
    """
    Population Stability Index (PSI) detector.

    PSI es estándar en la industria financiera para detectar drift.

    Interpretación:
    - PSI < 0.1: No hay cambio significativo
    - 0.1 <= PSI < 0.25: Cambio menor
    - PSI >= 0.25: Cambio significativo (requiere investigación)
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize PSI detector."""
        config = config or {}
        self.threshold = config.get("threshold", 0.25)
        self.n_bins = config.get("n_bins", 10)
        self.min_samples = config.get("min_samples", 30)

    def calculate_psi(
        self,
        expected: np.ndarray,
        actual: np.ndarray,
        buckets: Optional[np.ndarray] = None,
    ) -> tuple[float, dict[str, Any]]:
        """
        Calculate Population Stability Index.

        Args:
            expected: Reference/baseline distribution
            actual: Current/actual distribution
            buckets: Optional bucket boundaries

        Returns:
            Tuple of (PSI value, details dict)
        """
        if len(expected) < self.min_samples or len(actual) < self.min_samples:
            return 0.0, {"error": "insufficient_samples"}

        # Create buckets if not provided
        if buckets is None:
            # Use percentiles from expected distribution
            buckets = np.percentile(expected, np.linspace(0, 100, self.n_bins + 1))
            buckets[0] = -np.inf
            buckets[-1] = np.inf

        # Calculate bucket percentages
        expected_percents = self._calculate_bucket_percentages(expected, buckets)
        actual_percents = self._calculate_bucket_percentages(actual, buckets)

        # Calculate PSI for each bucket
        psi_values = []
        bucket_details = []

        for i, (exp_pct, act_pct) in enumerate(zip(expected_percents, actual_percents)):
            # Avoid division by zero and log(0)
            exp_pct = max(exp_pct, 0.0001)
            act_pct = max(act_pct, 0.0001)

            psi_bucket = (act_pct - exp_pct) * np.log(act_pct / exp_pct)
            psi_values.append(psi_bucket)

            bucket_details.append(
                {
                    "bucket": i,
                    "expected_pct": exp_pct,
                    "actual_pct": act_pct,
                    "psi_contribution": psi_bucket,
                }
            )

        total_psi = sum(psi_values)

        details = {
            "n_buckets": self.n_bins,
            "bucket_details": bucket_details,
            "expected_samples": len(expected),
            "actual_samples": len(actual),
        }

        return total_psi, details

    def _calculate_bucket_percentages(
        self,
        data: np.ndarray,
        buckets: np.ndarray,
    ) -> list[float]:
        """Calculate percentage of data in each bucket."""
        n_total = len(data)
        percentages = []

        for i in range(len(buckets) - 1):
            lower = buckets[i]
            upper = buckets[i + 1]
            count = np.sum((data >= lower) & (data < upper))
            percentages.append(count / n_total)

        return percentages

    def detect(
        self,
        expected: np.ndarray,
        actual: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> DriftResult:
        """
        Detect drift using PSI.

        Args:
            expected: Reference distribution
            actual: Current distribution
            timestamp: Optional timestamp

        Returns:
            DriftResult with PSI analysis
        """
        psi_value, details = self.calculate_psi(expected, actual)

        # Determine severity
        if psi_value < 0.1:
            severity = DriftSeverity.NONE
        elif psi_value < 0.25:
            severity = DriftSeverity.LOW
        elif psi_value < 0.4:
            severity = DriftSeverity.MEDIUM
        elif psi_value < 0.6:
            severity = DriftSeverity.HIGH
        else:
            severity = DriftSeverity.CRITICAL

        drift_detected = psi_value >= self.threshold

        return DriftResult(
            drift_detected=drift_detected,
            detector_name="psi",
            statistic=psi_value,
            p_value=None,  # PSI doesn't have p-value
            threshold=self.threshold,
            severity=severity,
            details=details,
            timestamp=timestamp or datetime.now(),
        )


# ============================================================================
# ADWIN (Adaptive Windowing) Detector
# ============================================================================


class ADWINDetector:
    """
    ADWIN (Adaptive Windowing) detector for streaming data.

    ADWIN mantiene una ventana de tamaño variable que crece cuando no hay
    drift y se reduce cuando se detecta drift.

    Reference: Bifet, A., & Gavalda, R. (2007). Learning from time-changing data
    with adaptive windowing.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize ADWIN detector."""
        config = config or {}
        self.delta = config.get("delta", 0.002)  # Confidence parameter
        self.min_window = config.get("min_window", 5)
        self.max_window = config.get("max_window", 1000)

        # Internal state
        self.window: deque = deque(maxlen=self.max_window)
        self.total = 0.0
        self.variance = 0.0
        self.width = 0
        self.drift_count = 0

    def add_element(self, value: float) -> bool:
        """
        Add element and check for drift.

        Args:
            value: New value to add

        Returns:
            True if drift detected
        """
        self.window.append(value)
        self.width = len(self.window)

        if self.width < self.min_window * 2:
            return False

        # Check for drift by comparing subwindows
        drift_detected = self._detect_change()

        if drift_detected:
            self.drift_count += 1
            # Shrink window
            self._shrink_window()

        return drift_detected

    def _detect_change(self) -> bool:
        """
        Detect change by comparing subwindows.

        Uses Hoeffding bound to detect statistically significant change.
        """
        if self.width < self.min_window * 2:
            return False

        window_list = list(self.window)

        # Try different split points
        for i in range(self.min_window, self.width - self.min_window):
            n0 = i
            n1 = self.width - i

            # Calculate means
            mean0 = np.mean(window_list[:i])
            mean1 = np.mean(window_list[i:])

            # Hoeffding bound
            m = 1.0 / (1.0 / n0 + 1.0 / n1)
            epsilon = np.sqrt((1.0 / (2.0 * m)) * np.log(4.0 / self.delta))

            if abs(mean0 - mean1) > epsilon:
                return True

        return False

    def _shrink_window(self) -> None:
        """Shrink window by removing oldest elements."""
        # Remove first half of window
        remove_count = self.width // 2
        for _ in range(min(remove_count, len(self.window))):
            self.window.popleft()

    def detect(
        self,
        data: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> DriftResult:
        """
        Detect drift in a batch of data.

        Args:
            data: Array of values to check
            timestamp: Optional timestamp

        Returns:
            DriftResult
        """
        drift_points = []

        for i, value in enumerate(data):
            if self.add_element(value):
                drift_points.append(i)

        drift_detected = len(drift_points) > 0

        # Calculate drift score as proportion of drift points
        drift_score = len(drift_points) / len(data) if len(data) > 0 else 0

        if drift_score == 0:
            severity = DriftSeverity.NONE
        elif drift_score < 0.1:
            severity = DriftSeverity.LOW
        elif drift_score < 0.25:
            severity = DriftSeverity.MEDIUM
        elif drift_score < 0.5:
            severity = DriftSeverity.HIGH
        else:
            severity = DriftSeverity.CRITICAL

        return DriftResult(
            drift_detected=drift_detected,
            detector_name="adwin",
            statistic=drift_score,
            threshold=0.0,  # ADWIN uses statistical bounds
            severity=severity,
            details={
                "drift_points": drift_points,
                "n_drifts": len(drift_points),
                "window_size": len(self.window),
                "total_drift_count": self.drift_count,
            },
            timestamp=timestamp or datetime.now(),
        )

    def reset(self) -> None:
        """Reset detector state."""
        self.window.clear()
        self.total = 0.0
        self.variance = 0.0
        self.width = 0
        self.drift_count = 0


# ============================================================================
# Concept Drift Detector (KS + MMD)
# ============================================================================


class ConceptDriftDetector:
    """
    Detecta concept drift usando tests estadísticos.

    Tests soportados:
    - Kolmogorov-Smirnov (KS) test: Compara distribuciones
    - Maximum Mean Discrepancy (MMD): Compara distribuciones en RKHS
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize detector."""
        config = config or {}
        self.window_size = config.get("window_size", 500)
        self.drift_threshold_ks = config.get("p_value_threshold", 0.05)
        self.drift_threshold_mmd = config.get("mmd_threshold", 0.1)
        self.use_ks_test = config.get("use_ks_test", True)
        self.use_mmd = config.get("use_mmd", False)
        self.min_samples = config.get("min_samples", 30)

        # Reference data
        self.reference_data: deque = deque(maxlen=self.window_size)
        self.reference_timestamp: Optional[datetime] = None

        # History
        self.drift_history: list[DriftResult] = []

    def update_reference(
        self,
        data: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Update reference data."""
        if data.ndim == 1:
            for sample in data:
                self.reference_data.append(sample)
        else:
            for sample in data:
                self.reference_data.append(sample)

        if timestamp:
            self.reference_timestamp = timestamp

    def detect_drift_ks(
        self,
        current_data: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> DriftResult:
        """Detect drift using Kolmogorov-Smirnov test."""
        if len(self.reference_data) < self.min_samples:
            return DriftResult(
                drift_detected=False,
                detector_name="ks_test",
                statistic=0.0,
                details={"error": "insufficient_reference_data"},
            )

        # Flatten first, then check
        reference_array = np.array(list(self.reference_data)).flatten()
        current_flat = current_data.flatten()

        # Check minimum sample requirements on flattened data
        if len(reference_array) < self.min_samples or len(current_flat) < self.min_samples:
            result = DriftResult(
                drift_detected=False,
                detector_name="ks_test",
                statistic=0.0,
                details={
                    "error": "insufficient_data_after_flatten",
                    "reference_samples": len(reference_array),
                    "current_samples": len(current_flat),
                },
            )
            self.drift_history.append(result)
            return result

        ks_stat, ks_pvalue = ks_2samp(reference_array, current_flat)

        drift_detected = ks_pvalue < self.drift_threshold_ks

        # Determine severity based on p-value
        if ks_pvalue >= 0.1:
            severity = DriftSeverity.NONE
        elif ks_pvalue >= 0.05:
            severity = DriftSeverity.LOW
        elif ks_pvalue >= 0.01:
            severity = DriftSeverity.MEDIUM
        elif ks_pvalue >= 0.001:
            severity = DriftSeverity.HIGH
        else:
            severity = DriftSeverity.CRITICAL

        result = DriftResult(
            drift_detected=drift_detected,
            detector_name="ks_test",
            statistic=float(ks_stat),
            p_value=float(ks_pvalue),
            threshold=self.drift_threshold_ks,
            severity=severity,
            details={
                "reference_samples": len(reference_array),
                "current_samples": len(current_flat),
            },
            timestamp=timestamp or datetime.now(),
        )

        self.drift_history.append(result)
        return result

    def detect_drift_mmd(
        self,
        current_data: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> DriftResult:
        """Detect drift using Maximum Mean Discrepancy."""
        if len(self.reference_data) < self.min_samples:
            return DriftResult(
                drift_detected=False,
                detector_name="mmd",
                statistic=0.0,
                details={"error": "insufficient_data"},
            )

        reference_array = np.array(list(self.reference_data))
        if reference_array.ndim == 1:
            reference_array = reference_array.reshape(-1, 1)
        if current_data.ndim == 1:
            current_data = current_data.reshape(-1, 1)

        try:
            # Compute MMD
            mmd_stat = self._compute_mmd(reference_array, current_data)

            drift_detected = mmd_stat > self.drift_threshold_mmd

            if mmd_stat < 0.05:
                severity = DriftSeverity.NONE
            elif mmd_stat < 0.1:
                severity = DriftSeverity.LOW
            elif mmd_stat < 0.2:
                severity = DriftSeverity.MEDIUM
            elif mmd_stat < 0.4:
                severity = DriftSeverity.HIGH
            else:
                severity = DriftSeverity.CRITICAL

            return DriftResult(
                drift_detected=drift_detected,
                detector_name="mmd",
                statistic=float(mmd_stat),
                threshold=self.drift_threshold_mmd,
                severity=severity,
                timestamp=timestamp or datetime.now(),
            )

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.warning(f"Error in MMD: {e}")
            return DriftResult(
                drift_detected=False,
                detector_name="mmd",
                statistic=0.0,
                details={"error": str(e)},
            )

    def _compute_mmd(
        self,
        X: np.ndarray,
        Y: np.ndarray,
        gamma: float = 1.0,
    ) -> float:
        """Compute Maximum Mean Discrepancy using RBF kernel."""
        X_mean = np.mean(X, axis=0)
        Y_mean = np.mean(Y, axis=0)
        mmd = np.linalg.norm(X_mean - Y_mean)
        return float(mmd)

    def detect(
        self,
        current_data: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> dict[str, DriftResult]:
        """Run all configured detectors."""
        results = {}

        if self.use_ks_test:
            results["ks_test"] = self.detect_drift_ks(current_data, timestamp)

        if self.use_mmd:
            results["mmd"] = self.detect_drift_mmd(current_data, timestamp)

        return results

    def detect_drift(
        self,
        current_data: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Detect drift and return results as a dictionary.

        Args:
            current_data: Current data to check for drift
            timestamp: Optional timestamp for the detection

        Returns:
            Dict with keys: 'drift_detected', 'drift_score', 'recommendation'
        """
        results = self.detect(current_data, timestamp)

        # Aggregate results from all detectors
        drift_detected = False
        max_score = 0.0
        recommendation = "ok"

        for _detector_name, result in results.items():
            if result.drift_detected:
                drift_detected = True
            # Get p-value as score if available, otherwise use statistic
            score = result.p_value if result.p_value is not None else result.statistic
            if score > max_score:
                max_score = score

        # Determine recommendation based on severity
        if results:
            max_severity = max(
                (r.severity for r in results.values()),
                key=lambda s: list(DriftSeverity).index(s),
                default=DriftSeverity.NONE,
            )

            if max_severity == DriftSeverity.CRITICAL:
                recommendation = "retrain_immediately"
            elif max_severity == DriftSeverity.HIGH:
                recommendation = "investigate_and_retrain"
            elif max_severity == DriftSeverity.MEDIUM:
                recommendation = "monitor_closely"
            elif max_severity == DriftSeverity.LOW:
                recommendation = "monitor"
            else:
                recommendation = "ok"

        return {
            "drift_detected": drift_detected,
            "drift_score": float(max_score),
            "recommendation": recommendation,
        }

    def get_drift_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get drift detection history."""
        return [r.to_dict() for r in self.drift_history[-limit:]]


# ============================================================================
# Feature Drift Monitor
# ============================================================================


class FeatureDriftMonitor:
    """
    Monitors drift for individual features.

    Tracks each feature independently to identify which features
    are causing drift.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize feature drift monitor."""
        config = config or {}
        self.feature_names: list[str] = []
        self.detectors: dict[str, dict[str, Any]] = {}
        self.config = config

        # Detector configs
        self.psi_config = config.get("psi", {"threshold": 0.25, "n_bins": 10})
        self.ks_config = config.get("ks_test", {"p_value_threshold": 0.05})

    def initialize_features(self, feature_names: list[str]) -> None:
        """Initialize detectors for each feature."""
        self.feature_names = feature_names
        self.detectors = {}

        for name in feature_names:
            self.detectors[name] = {
                "psi": PSIDetector(self.psi_config),
                "ks": ConceptDriftDetector(self.ks_config),
                "reference_data": None,
            }

    def set_reference(
        self,
        data: np.ndarray,
        feature_names: Optional[list[str]] = None,
    ) -> None:
        """
        Set reference data for all features.

        Args:
            data: 2D array (n_samples, n_features)
            feature_names: Optional feature names
        """
        if feature_names:
            self.initialize_features(feature_names)
        elif not self.feature_names:
            # Create default names
            n_features = data.shape[1] if data.ndim > 1 else 1
            self.initialize_features([f"feature_{i}" for i in range(n_features)])

        if data.ndim == 1:
            data = data.reshape(-1, 1)

        for i, name in enumerate(self.feature_names):
            if i < data.shape[1]:
                feature_data = data[:, i]
                self.detectors[name]["reference_data"] = feature_data.copy()
                self.detectors[name]["ks"].update_reference(feature_data)

    def detect_feature_drift(
        self,
        current_data: np.ndarray,
        timestamp: Optional[datetime] = None,
    ) -> list[FeatureDriftReport]:
        """
        Detect drift for all features.

        Args:
            current_data: 2D array (n_samples, n_features)
            timestamp: Optional timestamp

        Returns:
            List of FeatureDriftReport for each feature
        """
        if current_data.ndim == 1:
            current_data = current_data.reshape(-1, 1)

        reports = []

        for i, name in enumerate(self.feature_names):
            if i >= current_data.shape[1]:
                continue

            feature_current = current_data[:, i]
            detector_info = self.detectors.get(name, {})
            reference = detector_info.get("reference_data")

            if reference is None:
                continue

            results = []

            # PSI
            psi_detector = detector_info.get("psi")
            if psi_detector:
                psi_result = psi_detector.detect(reference, feature_current, timestamp)
                results.append(psi_result)

            # KS Test
            ks_detector = detector_info.get("ks")
            if ks_detector:
                ks_result = ks_detector.detect_drift_ks(feature_current, timestamp)
                results.append(ks_result)

            # Aggregate results
            drift_detected = any(r.drift_detected for r in results)
            max_severity = max(
                (r.severity for r in results), key=lambda s: list(DriftSeverity).index(s)
            )

            if max_severity == DriftSeverity.CRITICAL:
                recommendation = "retrain_immediately"
            elif max_severity == DriftSeverity.HIGH:
                recommendation = "investigate_and_retrain"
            elif max_severity == DriftSeverity.MEDIUM:
                recommendation = "monitor_closely"
            elif max_severity == DriftSeverity.LOW:
                recommendation = "monitor"
            else:
                recommendation = "ok"

            reports.append(
                FeatureDriftReport(
                    feature_name=name,
                    results=results,
                    overall_drift=drift_detected,
                    severity=max_severity,
                    recommendation=recommendation,
                )
            )

        return reports


# ============================================================================
# Overfitting Severity and Data Classes [TASK-4.2-PHASE-4]
# ============================================================================


class OverfittingSeverity(Enum):
    """Severity levels for overfitting detection."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class OverfittingMetrics:
    """Metrics for a single training epoch."""

    epoch: int
    train_loss: float
    val_loss: Optional[float]
    train_metric: float  # accuracy/f1/r2 depending on task
    val_metric: Optional[float]
    test_loss: Optional[float] = None
    test_metric: Optional[float] = None
    l1_regularization: Optional[float] = None
    l2_regularization: Optional[float] = None
    model_params_count: Optional[int] = None
    timestamp: Optional[datetime] = None

    def generalization_gap(self) -> Optional[float]:
        """Calculate generalization gap (val - train loss)."""
        if self.val_loss is None or self.train_loss is None:
            return None
        return self.val_loss - self.train_loss

    def gap_ratio(self) -> Optional[float]:
        """Calculate gap ratio for normalization."""
        gap = self.generalization_gap()
        if gap is None or self.train_loss == 0:
            return None
        return gap / self.train_loss


@dataclass
class OverfittingResult:
    """Result from overfitting detection."""

    overfitting_detected: bool
    severity: OverfittingSeverity
    overfitting_score: float  # 0-100, similar to RobustnessScorer
    gap_ratio: float  # Normalized train/val gap
    generalization_gap: float  # Absolute gap
    learning_curve_trend: str  # diverging, converging, plateau
    cross_validation_std: Optional[float] = None
    root_causes: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    divergence_point: Optional[int] = None  # Epoch where overfitting starts
    optimal_stopping_point: Optional[int] = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overfitting_detected": self.overfitting_detected,
            "severity": self.severity.value,
            "overfitting_score": self.overfitting_score,
            "gap_ratio": self.gap_ratio,
            "generalization_gap": self.generalization_gap,
            "learning_curve_trend": self.learning_curve_trend,
            "cross_validation_std": self.cross_validation_std,
            "root_causes": self.root_causes,
            "recommendations": self.recommendations,
            "divergence_point": self.divergence_point,
            "optimal_stopping_point": self.optimal_stopping_point,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class OverfittingReport:
    """Comprehensive overfitting analysis report."""

    timestamp: datetime
    model_name: str
    overall_overfitting_detected: bool
    severity: OverfittingSeverity
    latest_result: OverfittingResult
    results_history: list[OverfittingResult]
    trend_analysis: dict[str, Any]
    actionable_recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "model_name": self.model_name,
            "overall_overfitting_detected": self.overall_overfitting_detected,
            "severity": self.severity.value,
            "latest_result": self.latest_result.to_dict(),
            "results_history_size": len(self.results_history),
            "trend_analysis": self.trend_analysis,
            "actionable_recommendations": self.actionable_recommendations,
        }


# ============================================================================
# Overfitting Detector (Basic - Phase 3)
# ============================================================================


class OverfittingDetector:
    """Detects overfitting using train/val gap and learning curves."""

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize detector."""
        config = config or {}
        self.overfitting_threshold = config.get("overfitting_threshold", 0.1)
        self.min_epochs = config.get("min_epochs", 10)

        self.train_metrics_history: list[float] = []
        self.val_metrics_history: list[float] = []
        self.epoch_history: list[int] = []

    def update_metrics(
        self,
        epoch: int,
        train_metric: float,
        val_metric: Optional[float] = None,
    ) -> None:
        """Update training metrics."""
        self.epoch_history.append(epoch)
        self.train_metrics_history.append(train_metric)
        self.val_metrics_history.append(val_metric)

    def detect_overfitting(self) -> dict[str, Any]:
        """Detect overfitting based on metric history."""
        if len(self.train_metrics_history) < self.min_epochs:
            return {
                "overfitting_detected": False,
                "reason": "insufficient_data",
                "recommendation": "continue_training",
            }

        valid_indices = [i for i, v in enumerate(self.val_metrics_history) if v is not None]

        if len(valid_indices) < 5:
            return {
                "overfitting_detected": False,
                "reason": "insufficient_validation_data",
                "recommendation": "continue_training",
            }

        recent_train = [self.train_metrics_history[i] for i in valid_indices[-10:]]
        recent_val = [self.val_metrics_history[i] for i in valid_indices[-10:]]

        train_mean = np.mean(recent_train)
        val_mean = np.mean(recent_val)
        gap = val_mean - train_mean

        gap_ratio = gap / train_mean if train_mean > 0 else abs(gap)

        results = {
            "overfitting_detected": False,
            "train_val_gap": float(gap),
            "gap_ratio": float(gap_ratio),
            "train_metric_mean": float(train_mean),
            "val_metric_mean": float(val_mean),
            "recommendation": "ok",
        }

        if gap_ratio > self.overfitting_threshold:
            results["overfitting_detected"] = True
            if gap_ratio > 0.3:
                results["recommendation"] = "stop_training"
            elif gap_ratio > 0.2:
                results["recommendation"] = "reduce_complexity"
            else:
                results["recommendation"] = "monitor"

        # Learning curve trend
        if len(recent_train) >= 5:
            train_trend = self._calculate_trend(recent_train)
            val_trend = self._calculate_trend(recent_val)

            if train_trend < 0 and val_trend > 0:
                results["learning_curve_trend"] = "diverging"
                results["overfitting_detected"] = True
            elif train_trend < 0 and val_trend < 0:
                results["learning_curve_trend"] = "improving"
            else:
                results["learning_curve_trend"] = "plateau"
        else:
            results["learning_curve_trend"] = "unknown"

        return results

    def _calculate_trend(self, values: list[float]) -> float:
        """Calculate trend using linear regression."""
        if len(values) < 2:
            return 0.0
        x = np.arange(len(values))
        y = np.array(values)
        slope = np.polyfit(x, y, 1)[0]
        return float(slope)

    def get_learning_curves(self) -> dict[str, list]:
        """Get learning curves."""
        return {
            "epochs": self.epoch_history.copy(),
            "train_metrics": self.train_metrics_history.copy(),
            "val_metrics": self.val_metrics_history.copy(),
        }


# ============================================================================
# Advanced Overfitting Detector [TASK-4.2-PHASE-4]
# ============================================================================


class AdvancedOverfittingDetector:
    """
    Advanced overfitting detection system with comprehensive analysis.

    Detects:
    1. Train/val gap divergence
    2. Test set performance degradation
    3. Cross-validation stability
    4. Regularization effectiveness
    5. Learning curve extrapolation
    6. Root cause identification
    7. Actionable recommendations
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize advanced overfitting detector.

        Args:
            config: Configuration dict or load from YAML
        """
        if config is None:
            config = load_overfitting_config()

        self.config = config

        # Thresholds
        self.train_val_gap_threshold = config.get("detection", {}).get(
            "train_val_gap_threshold", 0.1
        )
        self.test_set_analysis = config.get("detection", {}).get("test_set_analysis", True)
        self.cross_validation_enabled = config.get("detection", {}).get(
            "cross_validation_enabled", True
        )
        self.cv_folds = config.get("detection", {}).get("cv_folds", 5)

        # Learning curves
        self.min_epochs = config.get("learning_curves", {}).get("min_epochs", 10)
        self.analyze_trends = config.get("learning_curves", {}).get("analyze_trends", True)
        self.extrapolation_window = config.get("learning_curves", {}).get("extrapolation_window", 5)
        self.divergence_sensitivity = config.get("learning_curves", {}).get(
            "divergence_sensitivity", 0.05
        )

        # Regularization
        self.monitor_l1 = config.get("regularization", {}).get("monitor_l1", True)
        self.monitor_l2 = config.get("regularization", {}).get("monitor_l2", True)

        # Model complexity
        self.track_parameters = config.get("model_complexity", {}).get("track_parameters", True)
        self.complexity_penalty = config.get("model_complexity", {}).get("complexity_penalty", 0.1)

        # Severity thresholds
        self.severity_thresholds = config.get("severity_thresholds", {})

        # Internal state
        self.metrics_history: list[OverfittingMetrics] = []
        self.cv_scores_history: list[list[float]] = []
        self.results_history: list[OverfittingResult] = []

    def update_metrics(
        self,
        epoch: int,
        train_loss: float,
        val_loss: Optional[float] = None,
        train_metric: float = 0.0,
        val_metric: Optional[float] = None,
        test_loss: Optional[float] = None,
        test_metric: Optional[float] = None,
        l1_regularization: Optional[float] = None,
        l2_regularization: Optional[float] = None,
        model_params_count: Optional[int] = None,
    ) -> None:
        """
        Update metrics for a training epoch.

        Args:
            epoch: Epoch number
            train_loss: Training loss
            val_loss: Validation loss
            train_metric: Training metric (accuracy/F1/R2)
            val_metric: Validation metric
            test_loss: Test loss (optional)
            test_metric: Test metric (optional)
            l1_regularization: L1 regularization value
            l2_regularization: L2 regularization value
            model_params_count: Total model parameters
        """
        metrics = OverfittingMetrics(
            epoch=epoch,
            train_loss=train_loss,
            val_loss=val_loss,
            train_metric=train_metric,
            val_metric=val_metric,
            test_loss=test_loss,
            test_metric=test_metric,
            l1_regularization=l1_regularization,
            l2_regularization=l2_regularization,
            model_params_count=model_params_count,
            timestamp=datetime.now(),
        )
        self.metrics_history.append(metrics)

    def add_cv_scores(self, cv_scores: list[float]) -> None:
        """
        Add cross-validation scores for stability analysis.

        Args:
            cv_scores: List of scores from K-fold cross-validation
        """
        self.cv_scores_history.append(cv_scores)

    def detect_overfitting(self) -> OverfittingResult:
        """
        Detect overfitting using all available signals.

        Returns:
            OverfittingResult with comprehensive analysis
        """
        timestamp = datetime.now()

        # Check minimum data
        if len(self.metrics_history) < self.min_epochs:
            return OverfittingResult(
                overfitting_detected=False,
                severity=OverfittingSeverity.NONE,
                overfitting_score=0.0,
                gap_ratio=0.0,
                generalization_gap=0.0,
                learning_curve_trend="unknown",
                root_causes=["insufficient_epochs"],
                recommendations=["continue_training"],
                details={"epochs_collected": len(self.metrics_history)},
                timestamp=timestamp,
            )

        # Get latest metrics
        latest = self.metrics_history[-1]

        # 1. Calculate gap ratio
        gap_ratio, gap = self._calculate_gap_ratio()

        # 2. Analyze learning curves
        lc_trend = self._analyze_learning_curve_trend()
        divergence_point = self._detect_divergence_point()

        # 3. Detect overfitting signals
        overfitting_signals = self._detect_overfitting_signals(
            gap_ratio, lc_trend, divergence_point
        )

        # 4. Analyze cross-validation stability
        cv_std = self._analyze_cross_validation_stability()

        # 5. Identify root causes
        root_causes = self._identify_root_causes(overfitting_signals, cv_std)

        # 6. Calculate overfitting score (0-100)
        overfitting_score = self._calculate_overfitting_score(
            gap_ratio, lc_trend, cv_std, divergence_point
        )

        # 7. Determine severity
        severity = self._determine_severity(overfitting_score)

        # 8. Generate recommendations
        recommendations = self._generate_recommendations(root_causes, severity, overfitting_score)

        # 9. Calculate optimal stopping point
        optimal_stopping = self._estimate_optimal_stopping_point()

        # Create result
        result = OverfittingResult(
            overfitting_detected=overfitting_score > 30.0,  # 30+ score = detection
            severity=severity,
            overfitting_score=overfitting_score,
            gap_ratio=gap_ratio,
            generalization_gap=gap,
            learning_curve_trend=lc_trend,
            cross_validation_std=cv_std,
            root_causes=root_causes,
            recommendations=recommendations,
            divergence_point=divergence_point,
            optimal_stopping_point=optimal_stopping,
            details={
                "epochs_analyzed": len(self.metrics_history),
                "has_test_metrics": latest.test_loss is not None,
                "has_regularization": latest.l1_regularization is not None
                or latest.l2_regularization is not None,
                "model_parameters": latest.model_params_count,
            },
            timestamp=timestamp,
        )

        self.results_history.append(result)
        return result

    def _calculate_gap_ratio(self) -> tuple[float, float]:
        """Calculate train/val gap ratio."""
        if not self.metrics_history:
            return 0.0, 0.0

        # Use last 10 epochs or all if less
        recent_metrics = self.metrics_history[-10:]

        # Filter metrics with valid val loss
        valid_metrics = [m for m in recent_metrics if m.val_loss is not None]

        if not valid_metrics:
            return 0.0, 0.0

        # Calculate mean losses
        train_losses = [m.train_loss for m in valid_metrics]
        val_losses = [m.val_loss for m in valid_metrics]

        mean_train_loss = np.mean(train_losses)
        mean_val_loss = np.mean(val_losses)

        gap = mean_val_loss - mean_train_loss

        gap_ratio = gap / mean_train_loss if mean_train_loss > 0 else abs(gap) if gap != 0 else 0.0

        return float(gap_ratio), float(gap)

    def _analyze_learning_curve_trend(self) -> str:
        """Analyze learning curve trends."""
        if len(self.metrics_history) < 5:
            return "unknown"

        recent_metrics = self.metrics_history[-self.extrapolation_window :]

        # Get valid training and validation metrics
        train_losses = [m.train_loss for m in recent_metrics]
        val_metrics = [m.val_loss for m in recent_metrics if m.val_loss is not None]

        if not val_metrics:
            return "unknown"

        # Calculate trends
        train_trend = self._calculate_trend(train_losses)
        val_trend = self._calculate_trend(val_metrics)

        # Classify trend
        if train_trend < -self.divergence_sensitivity and val_trend > self.divergence_sensitivity:
            return "diverging"  # Train improves, val worsens
        elif (
            train_trend < -self.divergence_sensitivity and val_trend < -self.divergence_sensitivity
        ):
            return "converging"  # Both improve
        elif (
            abs(train_trend) < self.divergence_sensitivity
            and abs(val_trend) < self.divergence_sensitivity
        ):
            return "plateau"  # Both plateau
        else:
            return "unstable"

    def _detect_divergence_point(self) -> Optional[int]:
        """Detect where overfitting divergence starts."""
        if len(self.metrics_history) < 5:
            return None

        recent = self.metrics_history[-10:]
        valid_indices = [i for i, m in enumerate(recent) if m.val_loss is not None]

        if len(valid_indices) < 3:
            return None

        for i in range(1, len(valid_indices)):
            current_idx = valid_indices[i]
            prev_idx = valid_indices[i - 1]

            current_m = recent[current_idx]
            prev_m = recent[prev_idx]

            # Check if train improves but val worsens
            if current_m.train_loss < prev_m.train_loss and current_m.val_loss > prev_m.val_loss:
                return len(self.metrics_history) - len(recent) + current_idx

        return None

    def _detect_overfitting_signals(
        self,
        gap_ratio: float,
        lc_trend: str,
        divergence_point: Optional[int],
    ) -> dict[str, bool]:
        """Detect multiple overfitting signals."""
        return {
            "large_gap": gap_ratio > self.train_val_gap_threshold,
            "diverging_curves": lc_trend == "diverging",
            "has_divergence_point": divergence_point is not None,
        }

    def _analyze_cross_validation_stability(self) -> Optional[float]:
        """Analyze cross-validation score stability."""
        if not self.cv_scores_history or not self.cross_validation_enabled:
            return None

        # Use last CV scores
        latest_cv = self.cv_scores_history[-1]

        if len(latest_cv) < 2:
            return None

        return float(np.std(latest_cv))

    def _identify_root_causes(
        self,
        overfitting_signals: dict[str, bool],
        cv_std: Optional[float],
    ) -> list[str]:
        """Identify root causes of overfitting."""
        causes = []

        if overfitting_signals.get("diverging_curves"):
            causes.append("learning_curves_diverging")

        if overfitting_signals.get("large_gap"):
            causes.append("large_train_validation_gap")

        if cv_std is not None and cv_std > 0.1:
            causes.append("high_cross_validation_variance")

        if self.metrics_history:
            latest = self.metrics_history[-1]
            if (
                latest.model_params_count is not None
                and len(self.metrics_history) < 1000
                and latest.model_params_count > 1000000
            ):
                causes.append("model_too_complex_for_data")

            if latest.l2_regularization is not None and latest.l2_regularization < 0.0001:
                causes.append("insufficient_l2_regularization")

        if not causes:
            causes.append("unknown")

        return causes

    def _calculate_overfitting_score(
        self,
        gap_ratio: float,
        lc_trend: str,
        cv_std: Optional[float],
        divergence_point: Optional[int],
    ) -> float:
        """
        Calculate overfitting score (0-100).

        Similar scoring approach to RobustnessScorer.
        """
        score = 0.0

        # 1. Gap ratio contribution (40%)
        gap_score = min(100.0, gap_ratio * 100.0)
        score += gap_score * 0.4

        # 2. Learning curve trend contribution (35%)
        if lc_trend == "diverging":
            trend_score = 100.0
        elif lc_trend == "converging":
            trend_score = 20.0
        elif lc_trend == "plateau":
            trend_score = 40.0
        else:
            trend_score = 30.0

        score += trend_score * 0.35

        # 3. Cross-validation stability (15%)
        cv_score = min(100.0, cv_std * 100.0) if cv_std is not None else 0.0
        score += cv_score * 0.15

        # 4. Divergence point penalty (10%)
        if divergence_point is not None:
            epochs_since_divergence = len(self.metrics_history) - divergence_point
            divergence_score = min(100.0, (epochs_since_divergence / 10.0) * 100.0)
        else:
            divergence_score = 0.0
        score += divergence_score * 0.1

        return float(min(100.0, score))

    def _determine_severity(self, overfitting_score: float) -> OverfittingSeverity:
        """Determine severity based on overfitting score."""
        thresholds = self.severity_thresholds

        if overfitting_score < thresholds.get("low", 20.0):
            return OverfittingSeverity.NONE
        elif overfitting_score < thresholds.get("medium", 40.0):
            return OverfittingSeverity.LOW
        elif overfitting_score < thresholds.get("high", 60.0):
            return OverfittingSeverity.MEDIUM
        elif overfitting_score < thresholds.get("critical", 80.0):
            return OverfittingSeverity.HIGH
        else:
            return OverfittingSeverity.CRITICAL

    def _generate_recommendations(
        self,
        root_causes: list[str],
        severity: OverfittingSeverity,
        overfitting_score: float,
    ) -> list[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Severity-based recommendations
        if severity == OverfittingSeverity.CRITICAL:
            recommendations.append("immediately_stop_training")
            recommendations.append("reduce_model_complexity")
        elif severity == OverfittingSeverity.HIGH:
            recommendations.append("stop_training_soon")
            recommendations.append("apply_regularization")
        elif severity == OverfittingSeverity.MEDIUM:
            recommendations.append("monitor_closely")
            recommendations.append("consider_early_stopping")
        elif severity == OverfittingSeverity.LOW:
            recommendations.append("monitor_trends")

        # Root cause-based recommendations
        if "model_too_complex_for_data" in root_causes:
            recommendations.append("simplify_model_architecture")
            recommendations.append("reduce_number_of_layers")

        if "insufficient_l2_regularization" in root_causes:
            recommendations.append("increase_l2_regularization_weight")

        if "high_cross_validation_variance" in root_causes:
            recommendations.append("increase_training_data")
            recommendations.append("apply_data_augmentation")

        if "learning_curves_diverging" in root_causes:
            recommendations.append("apply_early_stopping")
            recommendations.append("add_dropout_layers")

        # Ensure at least one recommendation
        if not recommendations:
            recommendations.append("continue_monitoring")

        return list(set(recommendations))  # Remove duplicates

    def _estimate_optimal_stopping_point(self) -> Optional[int]:
        """Estimate optimal epoch to stop training."""
        if len(self.metrics_history) < 5:
            return None

        # Find epoch with best validation metric
        best_val_loss = float("inf")
        best_epoch = None

        for _i, m in enumerate(self.metrics_history):
            if m.val_loss is not None and m.val_loss < best_val_loss:
                best_val_loss = m.val_loss
                best_epoch = m.epoch

        return best_epoch

    def _calculate_trend(self, values: list[float]) -> float:
        """Calculate trend using linear regression."""
        if len(values) < 2:
            return 0.0

        x = np.arange(len(values))
        y = np.array(values)

        try:
            slope = np.polyfit(x, y, 1)[0]
            return float(slope)
        except (ValueError, TypeError, KeyError, AttributeError):
            return 0.0

    def get_learning_curves(self) -> dict[str, Any]:
        """Get learning curves history."""
        epochs = [m.epoch for m in self.metrics_history]
        train_losses = [m.train_loss for m in self.metrics_history]
        val_losses = [m.val_loss for m in self.metrics_history]
        train_metrics = [m.train_metric for m in self.metrics_history]
        val_metrics = [m.val_metric for m in self.metrics_history]

        return {
            "epochs": epochs,
            "train_losses": train_losses,
            "val_losses": val_losses,
            "train_metrics": train_metrics,
            "val_metrics": val_metrics,
        }

    def generate_report(self, model_name: str = "unnamed") -> OverfittingReport:
        """
        Generate comprehensive overfitting report.

        Args:
            model_name: Name of the model being analyzed

        Returns:
            OverfittingReport with full analysis
        """
        timestamp = datetime.now()

        if not self.results_history:
            latest_result = self.detect_overfitting()
        else:
            latest_result = self.results_history[-1]

        # Analyze trend over all results
        trend_scores = [r.overfitting_score for r in self.results_history[-10:]]
        trend_direction = "unknown"

        if len(trend_scores) >= 3:
            slope = np.polyfit(np.arange(len(trend_scores)), trend_scores, 1)[0]
            if slope > 0.5:
                trend_direction = "worsening"
            elif slope < -0.5:
                trend_direction = "improving"
            else:
                trend_direction = "stable"

        trend_analysis = {
            "direction": trend_direction,
            "recent_scores": trend_scores[-5:] if trend_scores else [],
            "average_score": float(np.mean(trend_scores)) if trend_scores else 0.0,
        }

        # Aggregate recommendations from recent results
        all_recommendations = set()
        for result in self.results_history[-5:]:
            all_recommendations.update(result.recommendations)

        return OverfittingReport(
            timestamp=timestamp,
            model_name=model_name,
            overall_overfitting_detected=latest_result.overfitting_detected,
            severity=latest_result.severity,
            latest_result=latest_result,
            results_history=self.results_history,
            trend_analysis=trend_analysis,
            actionable_recommendations=list(all_recommendations),
        )

    def reset(self) -> None:
        """Reset detector state."""
        self.metrics_history.clear()
        self.cv_scores_history.clear()
        self.results_history.clear()


# ============================================================================
# Comprehensive Drift Detector (Facade)
# ============================================================================


class ComprehensiveDriftDetector:
    """
    Comprehensive drift detection system combining all detectors.

    Provides a unified interface for:
    - Multiple statistical tests (KS, PSI, ADWIN, MMD)
    - Feature-level monitoring
    - Prediction drift monitoring
    - Overfitting detection
    - Auto-retraining triggers
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Initialize comprehensive drift detector.

        Args:
            config: Configuration dict or None to load from YAML
        """
        if config is None:
            config = load_drift_config()

        self.config = config
        self.enabled = config.get("enabled", True)

        # Initialize detectors
        detector_config = config.get("detectors", {})

        self.psi_detector = PSIDetector(detector_config.get("psi", {}))
        self.adwin_detector = ADWINDetector(detector_config.get("adwin", {}))
        self.ks_detector = ConceptDriftDetector(detector_config.get("ks_test", {}))
        self.overfitting_detector = OverfittingDetector(config.get("overfitting", {}))
        self.feature_monitor = FeatureDriftMonitor(detector_config)

        # Thresholds
        self.thresholds = config.get(
            "thresholds",
            {
                "warning": 0.1,
                "critical": 0.25,
                "retrain": 0.4,
            },
        )

        # Auto-retrain config
        self.auto_retrain_config = config.get(
            "auto_retrain",
            {
                "enabled": True,
                "min_interval_hours": 24,
                "require_multiple_detectors": True,
            },
        )

        # State
        self.last_check_timestamp: Optional[datetime] = None
        self.last_retrain_timestamp: Optional[datetime] = None
        self.reference_data: Optional[np.ndarray] = None
        self.reference_predictions: Optional[np.ndarray] = None

    def set_reference(
        self,
        data: np.ndarray,
        predictions: Optional[np.ndarray] = None,
        feature_names: Optional[list[str]] = None,
    ) -> None:
        """
        Set reference data for drift detection.

        Args:
            data: Feature data (n_samples, n_features)
            predictions: Model predictions (optional)
            feature_names: Feature names (optional)
        """
        self.reference_data = data.copy()
        self.reference_predictions = predictions.copy() if predictions is not None else None

        # Update all detectors
        if data.ndim == 1:
            self.ks_detector.update_reference(data)
        else:
            # Update KS with flattened data
            self.ks_detector.update_reference(data.flatten())

        # Feature monitor
        self.feature_monitor.set_reference(data, feature_names)

    def update_reference(
        self,
        data: np.ndarray,
        predictions: Optional[np.ndarray] = None,
        feature_names: Optional[list[str]] = None,
    ) -> None:
        """
        Update reference data for drift detection (alias for set_reference).

        Args:
            data: Feature data (n_samples, n_features)
            predictions: Model predictions (optional)
            feature_names: Feature names (optional)
        """
        self.set_reference(data, predictions, feature_names)

    def detect(
        self,
        current_data: np.ndarray,
        current_predictions: Optional[np.ndarray] = None,
        timestamp: Optional[datetime] = None,
    ) -> ComprehensiveDriftReport:
        """
        Run comprehensive drift detection.

        Args:
            current_data: Current feature data
            current_predictions: Current model predictions (optional)
            timestamp: Optional timestamp

        Returns:
            ComprehensiveDriftReport with all results
        """
        timestamp = timestamp or datetime.now()
        self.last_check_timestamp = timestamp

        if not self.enabled:
            return ComprehensiveDriftReport(
                timestamp=timestamp,
                overall_drift_detected=False,
                overall_severity=DriftSeverity.NONE,
                recommendation="disabled",
                feature_reports=[],
                prediction_drift=None,
                detector_results={},
                should_retrain=False,
            )

        if self.reference_data is None:
            return ComprehensiveDriftReport(
                timestamp=timestamp,
                overall_drift_detected=False,
                overall_severity=DriftSeverity.NONE,
                recommendation="set_reference_first",
                feature_reports=[],
                prediction_drift=None,
                detector_results={},
                should_retrain=False,
            )

        detector_results = {}

        # 1. PSI
        psi_result = self.psi_detector.detect(
            self.reference_data.flatten(),
            current_data.flatten(),
            timestamp,
        )
        detector_results["psi"] = psi_result

        # 2. KS Test
        ks_result = self.ks_detector.detect_drift_ks(current_data.flatten(), timestamp)
        detector_results["ks_test"] = ks_result

        # 3. ADWIN
        adwin_result = self.adwin_detector.detect(current_data.flatten(), timestamp)
        detector_results["adwin"] = adwin_result

        # 4. Feature-level drift
        feature_reports = self.feature_monitor.detect_feature_drift(current_data, timestamp)

        # 5. Prediction drift
        prediction_drift = None
        if current_predictions is not None and self.reference_predictions is not None:
            prediction_drift = self.psi_detector.detect(
                self.reference_predictions.flatten(),
                current_predictions.flatten(),
                timestamp,
            )
            detector_results["prediction_psi"] = prediction_drift

        # Aggregate results
        all_results = list(detector_results.values())
        drift_detected = any(r.drift_detected for r in all_results if r)
        max_severity = max(
            (r.severity for r in all_results if r),
            key=lambda s: list(DriftSeverity).index(s),
            default=DriftSeverity.NONE,
        )

        # Determine recommendation
        if max_severity == DriftSeverity.CRITICAL:
            recommendation = "retrain_immediately"
        elif max_severity == DriftSeverity.HIGH:
            recommendation = "retrain"
        elif max_severity == DriftSeverity.MEDIUM or max_severity == DriftSeverity.LOW:
            recommendation = "monitor"
        else:
            recommendation = "ok"

        # Should retrain?
        should_retrain = self._should_retrain(detector_results, timestamp)

        return ComprehensiveDriftReport(
            timestamp=timestamp,
            overall_drift_detected=drift_detected,
            overall_severity=max_severity,
            recommendation=recommendation,
            feature_reports=feature_reports,
            prediction_drift=prediction_drift,
            detector_results=detector_results,
            should_retrain=should_retrain,
        )

    def _should_retrain(
        self,
        detector_results: dict[str, DriftResult],
        timestamp: datetime,
    ) -> bool:
        """Determine if model should be retrained."""
        if not self.auto_retrain_config.get("enabled", True):
            return False

        # Check minimum interval
        if self.last_retrain_timestamp:
            hours_since = (timestamp - self.last_retrain_timestamp).total_seconds() / 3600
            if hours_since < self.auto_retrain_config.get("min_interval_hours", 24):
                return False

        # Count detectors that found drift
        drifts_detected = sum(1 for r in detector_results.values() if r and r.drift_detected)

        if self.auto_retrain_config.get("require_multiple_detectors", True):
            return drifts_detected >= 2
        else:
            return drifts_detected >= 1

    def record_retrain(self, timestamp: Optional[datetime] = None) -> None:
        """Record that a retrain was performed."""
        self.last_retrain_timestamp = timestamp or datetime.now()

    def reset(self) -> None:
        """Reset all detector states."""
        self.adwin_detector.reset()
        self.reference_data = None
        self.reference_predictions = None
        self.last_check_timestamp = None


# ============================================================================
# Auto-Retraining Trigger (Enhanced)
# ============================================================================


class AutoRetrainingTrigger:
    """
    Sistema de triggers automáticos para reentrenamiento.

    Combina detección de drift y overfitting para decidir cuándo reentrenar.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """Initialize trigger system."""
        config = config or {}

        self.drift_detector = ConceptDriftDetector(config.get("drift_detector_config", {}))
        self.overfitting_detector = OverfittingDetector(config.get("overfitting_config", {}))

        # Triggers
        self.retrain_on_drift = config.get("retrain_on_drift", True)
        self.retrain_on_overfitting = config.get("retrain_on_overfitting", True)
        self.retrain_interval_days = config.get("retrain_interval_days", 30)
        self.performance_degradation_threshold = config.get(
            "performance_degradation_threshold", 0.2
        )

        # State
        self.last_retrain_timestamp: Optional[datetime] = None
        self.performance_history: list[dict[str, Any]] = []
        self.retrain_history: list[dict[str, Any]] = []
        self._last_drift_event: Optional[dict[str, Any]] = None
        self._last_overfitting_event: Optional[dict[str, Any]] = None

    def should_retrain(
        self,
        current_data: Optional[np.ndarray] = None,
        current_predictions: Optional[np.ndarray] = None,
        current_performance: Optional[dict[str, float]] = None,
        timestamp: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Decide if model should be retrained.

        Args:
            current_data: Current feature data
            current_predictions: Current predictions
            current_performance: Performance metrics
            timestamp: Optional timestamp

        Returns:
            Dict with decision and reasons
        """
        timestamp = timestamp or datetime.now()
        reasons = []
        should_retrain = False

        results = {
            "should_retrain": False,
            "reasons": [],
            "drift_detection": None,
            "overfitting_detection": None,
            "performance_degradation": None,
            "time_based": False,
        }

        # 1. Time-based check
        if self.last_retrain_timestamp:
            days_since = (timestamp - self.last_retrain_timestamp).days
            if days_since >= self.retrain_interval_days:
                should_retrain = True
                reasons.append(f"time_based: {days_since} days since last retrain")
                results["time_based"] = True

        # 2. Drift-based check
        if self.retrain_on_drift and current_data is not None:
            drift_result = self.drift_detector.detect_drift(current_data, timestamp)
            results["drift_detection"] = drift_result

            if drift_result.get("drift_detected", False):
                should_retrain = True
                recommendation = drift_result.get("recommendation", "monitor")
                reasons.append(f"drift_detected: recommendation={recommendation}")

        # 3. Overfitting check
        if self.retrain_on_overfitting:
            overfitting_result = self.overfitting_detector.detect_overfitting()
            results["overfitting_detection"] = overfitting_result

            if overfitting_result.get("overfitting_detected", False) and overfitting_result.get(
                "recommendation"
            ) in [
                "stop_training",
                "reduce_complexity",
            ]:
                should_retrain = True
                reasons.append(
                    f"overfitting: gap_ratio={overfitting_result.get('gap_ratio', 0):.3f}"
                )

        # 4. Performance degradation check
        if current_performance:
            perf_result = self._check_performance_degradation(current_performance)
            results["performance_degradation"] = perf_result

            if perf_result.get("degradation_detected", False):
                should_retrain = True
                reasons.append(
                    f"performance_degradation: {perf_result.get('degradation_score', 0):.3f}"
                )

        results["should_retrain"] = should_retrain
        results["reasons"] = reasons

        return results

    def _check_performance_degradation(
        self,
        current_performance: dict[str, float],
    ) -> dict[str, Any]:
        """Check for performance degradation."""
        if len(self.performance_history) < 3:
            return {"degradation_detected": False, "reason": "insufficient_history"}

        historical_avg = {}
        for metric_name in current_performance:
            values = [
                p.get(metric_name)
                for p in self.performance_history[-10:]
                if p.get(metric_name) is not None
            ]
            if values:
                historical_avg[metric_name] = np.mean(values)

        degradation_scores = {}
        for metric_name, current_value in current_performance.items():
            if metric_name in historical_avg:
                hist_val = historical_avg[metric_name]
                degradation = (hist_val - current_value) / hist_val if hist_val > 0 else 0
                degradation_scores[metric_name] = degradation

        if not degradation_scores:
            return {"degradation_detected": False, "reason": "no_comparable_metrics"}

        avg_degradation = np.mean(list(degradation_scores.values()))

        return {
            "degradation_detected": avg_degradation > self.performance_degradation_threshold,
            "degradation_score": float(avg_degradation),
            "metric_degradations": degradation_scores,
        }

    def record_retrain(
        self,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record that a retrain was performed."""
        timestamp = timestamp or datetime.now()
        self.last_retrain_timestamp = timestamp

        self.retrain_history.append(
            {
                "timestamp": timestamp.isoformat(),
                "metadata": metadata or {},
            }
        )

    def record_performance(
        self,
        performance: dict[str, float],
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Record current performance."""
        self.performance_history.append(
            {
                "timestamp": (timestamp or datetime.now()).isoformat(),
                **performance,
            }
        )

    def record_drift(
        self,
        drift_detected: bool,
        severity: DriftSeverity,
        detectors_triggered: list[str],
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record drift detection event for trigger decision.

        Args:
            drift_detected: Whether drift was detected
            severity: Severity level of drift
            detectors_triggered: List of detector names that triggered
            timestamp: Optional timestamp
        """
        if drift_detected:
            self._last_drift_event = {
                "timestamp": (timestamp or datetime.now()).isoformat(),
                "severity": severity.value,
                "detectors_triggered": detectors_triggered,
            }
            # Update drift detector's internal state
            if self.drift_detector:
                self.drift_detector._last_drift_detected = True
                self.drift_detector._last_drift_severity = severity

    def record_overfitting(
        self,
        overfitting_detected: bool,
        train_val_gap: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record overfitting detection event for trigger decision.

        Args:
            overfitting_detected: Whether overfitting was detected
            train_val_gap: Train/validation gap ratio
            timestamp: Optional timestamp
        """
        if overfitting_detected:
            self._last_overfitting_event = {
                "timestamp": (timestamp or datetime.now()).isoformat(),
                "train_val_gap": train_val_gap,
            }

    def get_retrain_history(self) -> list[dict[str, Any]]:
        """Get retrain history."""
        return self.retrain_history.copy()
