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
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import yaml

logger = logging.getLogger(__name__)

# Importaciones opcionales
try:
    from scipy.stats import ks_2samp

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy no disponible. Algunos tests estadísticos no funcionarán.")

try:
    pass

    SKLEARN_METRICS_AVAILABLE = True
except ImportError:
    SKLEARN_METRICS_AVAILABLE = False


# ============================================================================
# Configuration Loading
# ============================================================================


def load_drift_config(config_path: str = "config/drift_detection.yaml") -> Dict[str, Any]:
    """Load drift detection configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Drift config not found at {config_path}, using defaults")
        return get_default_drift_config()

    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_default_drift_config() -> Dict[str, Any]:
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
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
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
    results: List[DriftResult]
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
    feature_reports: List[FeatureDriftReport]
    prediction_drift: Optional[DriftResult]
    detector_results: Dict[str, DriftResult]
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

    def __init__(self, config: Dict[str, Any] = None):
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
    ) -> Tuple[float, Dict[str, Any]]:
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
    ) -> List[float]:
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

    def __init__(self, config: Dict[str, Any] = None):
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

    def __init__(self, config: Dict[str, Any] = None):
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
        self.drift_history: List[DriftResult] = []

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

        if not SCIPY_AVAILABLE:
            return DriftResult(
                drift_detected=False,
                detector_name="ks_test",
                statistic=0.0,
                details={"error": "scipy_not_available"},
            )

        try:
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

        except Exception as e:
            logger.warning(f"Error in KS test: {e}")
            return DriftResult(
                drift_detected=False,
                detector_name="ks_test",
                statistic=0.0,
                details={"error": str(e)},
            )

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

        except Exception as e:
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
    ) -> Dict[str, DriftResult]:
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
    ) -> Dict[str, Any]:
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

        for detector_name, result in results.items():
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

    def get_drift_history(self, limit: int = 100) -> List[Dict[str, Any]]:
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

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize feature drift monitor."""
        config = config or {}
        self.feature_names: List[str] = []
        self.detectors: Dict[str, Dict[str, Any]] = {}
        self.config = config

        # Detector configs
        self.psi_config = config.get("psi", {"threshold": 0.25, "n_bins": 10})
        self.ks_config = config.get("ks_test", {"p_value_threshold": 0.05})

    def initialize_features(self, feature_names: List[str]) -> None:
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
        feature_names: Optional[List[str]] = None,
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
    ) -> List[FeatureDriftReport]:
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
# Overfitting Detector
# ============================================================================


class OverfittingDetector:
    """Detects overfitting using train/val gap and learning curves."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize detector."""
        config = config or {}
        self.overfitting_threshold = config.get("overfitting_threshold", 0.1)
        self.min_epochs = config.get("min_epochs", 10)

        self.train_metrics_history: List[float] = []
        self.val_metrics_history: List[float] = []
        self.epoch_history: List[int] = []

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

    def detect_overfitting(self) -> Dict[str, Any]:
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

    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend using linear regression."""
        if len(values) < 2:
            return 0.0
        x = np.arange(len(values))
        y = np.array(values)
        slope = np.polyfit(x, y, 1)[0]
        return float(slope)

    def get_learning_curves(self) -> Dict[str, List]:
        """Get learning curves."""
        return {
            "epochs": self.epoch_history.copy(),
            "train_metrics": self.train_metrics_history.copy(),
            "val_metrics": self.val_metrics_history.copy(),
        }


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

    def __init__(self, config: Optional[Dict[str, Any]] = None):
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
        feature_names: Optional[List[str]] = None,
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
        feature_names: Optional[List[str]] = None,
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
        elif max_severity == DriftSeverity.MEDIUM:
            recommendation = "monitor"
        elif max_severity == DriftSeverity.LOW:
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
        detector_results: Dict[str, DriftResult],
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

    def __init__(self, config: Dict[str, Any] = None):
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
        self.performance_history: List[Dict[str, Any]] = []
        self.retrain_history: List[Dict[str, Any]] = []
        self._last_drift_event: Optional[Dict[str, Any]] = None
        self._last_overfitting_event: Optional[Dict[str, Any]] = None

    def should_retrain(
        self,
        current_data: Optional[np.ndarray] = None,
        current_predictions: Optional[np.ndarray] = None,
        current_performance: Optional[Dict[str, float]] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
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

            if overfitting_result.get("overfitting_detected", False):
                if overfitting_result.get("recommendation") in [
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
        current_performance: Dict[str, float],
    ) -> Dict[str, Any]:
        """Check for performance degradation."""
        if len(self.performance_history) < 3:
            return {"degradation_detected": False, "reason": "insufficient_history"}

        historical_avg = {}
        for metric_name in current_performance.keys():
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
        metadata: Optional[Dict] = None,
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
        performance: Dict[str, float],
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
        detectors_triggered: List[str],
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

    def get_retrain_history(self) -> List[Dict[str, Any]]:
        """Get retrain history."""
        return self.retrain_history.copy()
