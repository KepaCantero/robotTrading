"""
Drift Detectors - Statistical methods for detecting concept and data drift

This module implements various statistical tests for detecting distribution
shifts in machine learning models and financial time series.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from scipy.stats import ks_2samp

logger = logging.getLogger(__name__)

# Design Note: DOM-001 - DriftResult is a plain dataclass (not a domain Value Object)
# Rationale: Drift detection is a cross-cutting utility concern used across multiple
# bounded contexts (backtesting, monitoring, live trading). Converting to a domain
# VO would create unnecessary coupling. The dataclass provides type safety and
# immutability (frozen=True would be used but we need mutability for __post_init__)
# while remaining framework-agnostic.


class DriftType(Enum):
    """Types of drift to detect."""

    CONCEPT_DRIFT = "concept_drift"
    FEATURE_DRIFT = "feature_drift"
    PREDICTION_DRIFT = "prediction_drift"
    OVERFITTING = "overfitting"


@dataclass
class DriftResult:
    """Result of a drift detection test."""

    drift_detected: bool
    drift_type: DriftType
    p_value: float | None = None
    statistic: float | None = None
    threshold: float | None = None
    confidence: float | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: dict[str, Any] = field(default_factory=dict)


class KSDriftDetector:
    """
    Kolmogorov-Smirnov test for drift detection.

    Compares two samples to test if they come from the same distribution.
    """

    def __init__(self, significance_level: float = 0.05):
        """
        Initialize KS detector.

        Args:
            significance_level: P-value threshold for drift detection
        """
        self.significance_level = significance_level

    def detect(self, reference: np.ndarray, current: np.ndarray) -> DriftResult:
        """
        Detect drift using KS test.

        Args:
            reference: Reference distribution
            current: Current distribution to test

        Returns:
            Drift detection result
        """
        statistic, p_value = ks_2samp(reference, current)

        drift_detected = p_value < self.significance_level
        result = DriftResult(
            drift_detected=drift_detected,
            drift_type=DriftType.FEATURE_DRIFT,
            p_value=p_value,
            statistic=statistic,
            threshold=self.significance_level,
            confidence=1 - p_value,
        )

        # Structured logging for drift detection event (LOG-001)
        logger.info(
            "drift_detection_complete",
            extra={
                "drift_type": DriftType.FEATURE_DRIFT.value,
                "detector": "KSDriftDetector",
                "drift_detected": drift_detected,
                "p_value": float(p_value),
                "statistic": float(statistic),
                "threshold": self.significance_level,
                "confidence": float(1 - p_value),
                "reference_size": len(reference),
                "current_size": len(current),
                "reference_mean": float(np.mean(reference)),
                "current_mean": float(np.mean(current)),
            },
        )

        if drift_detected:
            logger.warning(
                "drift_detected",
                extra={
                    "drift_type": DriftType.FEATURE_DRIFT.value,
                    "detector": "KSDriftDetector",
                    "p_value": float(p_value),
                    "statistic": float(statistic),
                    "threshold": self.significance_level,
                    "severity": (
                        "high" if p_value < 0.01 else "moderate" if p_value < 0.05 else "low"
                    ),
                },
            )

        return result


class PSIDriftDetector:
    """
    Population Stability Index (PSI) for drift detection.

    PSI is a standard metric in finance for detecting distribution shifts.
    """

    def __init__(self, threshold: float = 0.25, n_bins: int = 10):
        """
        Initialize PSI detector.

        Args:
            threshold: PSI threshold for drift detection
            n_bins: Number of bins for discretization
        """
        self.threshold = threshold
        self.n_bins = n_bins

    def detect(self, reference: np.ndarray, current: np.ndarray) -> DriftResult:
        """
        Detect drift using PSI.

        Args:
            reference: Reference distribution
            current: Current distribution to test

        Returns:
            Drift detection result
        """
        psi_value = self._calculate_psi(reference, current)
        drift_detected = psi_value > self.threshold

        result = DriftResult(
            drift_detected=drift_detected,
            drift_type=DriftType.FEATURE_DRIFT,
            statistic=psi_value,
            threshold=self.threshold,
            details={"n_bins": self.n_bins},
        )

        # Structured logging for drift detection event (LOG-001)
        logger.info(
            "drift_detection_complete",
            extra={
                "drift_type": DriftType.FEATURE_DRIFT.value,
                "detector": "PSIDriftDetector",
                "drift_detected": drift_detected,
                "psi_value": float(psi_value),
                "threshold": self.threshold,
                "n_bins": self.n_bins,
                "reference_size": len(reference),
                "current_size": len(current),
                "severity": (
                    "high" if psi_value > 0.5 else "moderate" if psi_value > 0.25 else "low"
                ),
            },
        )

        if drift_detected:
            logger.warning(
                "drift_detected",
                extra={
                    "drift_type": DriftType.FEATURE_DRIFT.value,
                    "detector": "PSIDriftDetector",
                    "psi_value": float(psi_value),
                    "threshold": self.threshold,
                    "n_bins": self.n_bins,
                    "severity": (
                        "high" if psi_value > 0.5 else "moderate" if psi_value > 0.25 else "low"
                    ),
                },
            )

        return result

    def _calculate_psi(self, reference: np.ndarray, current: np.ndarray) -> float:
        """
        Calculate Population Stability Index.

        Args:
            reference: Reference distribution
            current: Current distribution

        Returns:
            PSI value
        """
        # Create bins based on reference distribution
        _, bin_edges = np.histogram(reference, bins=self.n_bins)

        # Calculate frequencies
        ref_freq, _ = np.histogram(reference, bins=bin_edges)
        curr_freq, _ = np.histogram(current, bins=bin_edges)

        # Normalize to get percentages
        ref_pct = ref_freq / len(reference)
        curr_pct = curr_freq / len(current)

        # Avoid division by zero
        ref_pct = np.where(ref_pct == 0, 0.0001, ref_pct)
        curr_pct = np.where(curr_pct == 0, 0.0001, curr_pct)

        # Calculate PSI
        psi = np.sum((ref_pct - curr_pct) * np.log(ref_pct / curr_pct))

        return float(psi)


class ADWINDriftDetector:
    """
    ADWIN (Adaptive Windowing) for streaming drift detection.

    Maintains a sliding window and detects abrupt changes in distribution.
    """

    def __init__(self, delta: float = 0.002, max_window_size: int = 1000):
        """
        Initialize ADWIN detector.

        Args:
            delta: Confidence parameter
            max_window_size: Maximum window size
        """
        self.delta = delta
        self.max_window_size = max_window_size
        self.window: deque = deque(maxlen=max_window_size)

    def detect(self, new_value: float) -> DriftResult | None:
        """
        Detect drift on streaming data.

        Args:
            new_value: New data point

        Returns:
            Drift result if detected, None otherwise
        """
        self.window.append(new_value)

        if len(self.window) < self.max_window_size // 2:
            # Log when window is warming up
            logger.debug(
                "adwin_warming_up",
                extra={
                    "detector": "ADWINDriftDetector",
                    "current_window_size": len(self.window),
                    "required_size": self.max_window_size // 2,
                },
            )
            return None

        # Check for change point
        change_point = self._find_change_point()

        if change_point is not None:
            # Reset window after change point
            for _ in range(change_point):
                self.window.popleft()

            result = DriftResult(
                drift_detected=True,
                drift_type=DriftType.CONCEPT_DRIFT,
                details={"change_point": change_point, "window_size": len(self.window)},
            )

            # Structured logging for drift detection event (LOG-001)
            logger.warning(
                "drift_detected",
                extra={
                    "drift_type": DriftType.CONCEPT_DRIFT.value,
                    "detector": "ADWINDriftDetector",
                    "change_point": change_point,
                    "window_size": len(self.window),
                    "delta": self.delta,
                    "new_value": float(new_value),
                },
            )

            return result

        # Log periodic monitoring for streaming detector
        if len(self.window) % 100 == 0:
            logger.info(
                "adwin_monitoring",
                extra={
                    "detector": "ADWINDriftDetector",
                    "window_size": len(self.window),
                    "delta": self.delta,
                    "window_mean": float(np.mean(list(self.window))),
                    "window_std": float(np.std(list(self.window))),
                },
            )

        return None

    def _find_change_point(self) -> int | None:
        """
        Find change point in window.

        Returns:
            Change point index or None
        """
        window_array = np.array(list(self.window))

        for i in range(1, len(window_array) // 2):
            left = window_array[:i]
            right = window_array[i:]

            # Compare means
            mean_left = np.mean(left)
            mean_right = np.mean(right)

            # Calculate harmonic cutoff
            m = len(window_array)
            epsilon_cut = np.sqrt((1 / (2 * m)) * np.log(2 / self.delta))

            if abs(mean_left - mean_right) > epsilon_cut:
                return i

        return None


class MMDDriftDetector:
    """
    Maximum Mean Discrepancy (MMD) for drift detection.

    Compares distributions in a reproducing kernel Hilbert space.
    More computationally expensive but more powerful than KS test.
    """

    def __init__(self, threshold: float = 0.1, gamma: float = 1.0):
        """
        Initialize MMD detector.

        Args:
            threshold: MMD threshold for drift detection
            gamma: RBF kernel parameter
        """
        self.threshold = threshold
        self.gamma = gamma

    def detect(self, reference: np.ndarray, current: np.ndarray) -> DriftResult:
        """
        Detect drift using MMD.

        Args:
            reference: Reference distribution
            current: Current distribution to test

        Returns:
            Drift detection result
        """
        mmd_value = self._calculate_mmd(reference, current)
        drift_detected = mmd_value > self.threshold

        result = DriftResult(
            drift_detected=drift_detected,
            drift_type=DriftType.FEATURE_DRIFT,
            statistic=mmd_value,
            threshold=self.threshold,
        )

        # Structured logging for drift detection event (LOG-001)
        logger.info(
            "drift_detection_complete",
            extra={
                "drift_type": DriftType.FEATURE_DRIFT.value,
                "detector": "MMDDriftDetector",
                "drift_detected": drift_detected,
                "mmd_value": float(mmd_value),
                "threshold": self.threshold,
                "gamma": self.gamma,
                "reference_size": len(reference),
                "current_size": len(current),
                "reference_mean": float(np.mean(reference)),
                "current_mean": float(np.mean(current)),
            },
        )

        if drift_detected:
            logger.warning(
                "drift_detected",
                extra={
                    "drift_type": DriftType.FEATURE_DRIFT.value,
                    "detector": "MMDDriftDetector",
                    "mmd_value": float(mmd_value),
                    "threshold": self.threshold,
                    "gamma": self.gamma,
                },
            )

        return result

    def _calculate_mmd(self, reference: np.ndarray, current: np.ndarray) -> float:
        """
        Calculate Maximum Mean Discrepancy.

        Args:
            reference: Reference distribution
            current: Current distribution

        Returns:
            MMD value
        """

        def rbf_kernel(x: np.ndarray, y: np.ndarray) -> np.ndarray:
            """RBF kernel function."""
            return np.exp(-self.gamma * np.linalg.norm(x - y) ** 2)

        n = len(reference)
        m = len(current)

        # Calculate kernel matrices
        xx = 0
        for i in range(n):
            for j in range(n):
                xx += rbf_kernel(reference[i], reference[j])
        xx /= n**2

        yy = 0
        for i in range(m):
            for j in range(m):
                yy += rbf_kernel(current[i], current[j])
        yy /= m**2

        xy = 0
        for i in range(n):
            for j in range(m):
                xy += rbf_kernel(reference[i], current[j])
        xy /= n * m

        mmd = xx + yy - 2 * xy

        return float(max(0, mmd))
