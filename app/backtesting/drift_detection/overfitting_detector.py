"""
Overfitting Detector - Detects overfitting in machine learning models

This module provides methods for detecting overfitting through
cross-validation analysis, learning curves, and performance gaps.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from app.domain.value_objects.backtest_result import BacktestResultValue

logger = logging.getLogger(__name__)

# Design Note: DOM-001 - OverfittingResult is a plain dataclass (not a domain Value Object)
# Rationale: Overfitting detection is an analytical utility that operates on domain
# objects (BacktestResultValue) but produces analysis results that are not themselves
# domain entities. The detector is a service that analyzes existing domain objects.
# Converting the result to a VO would add complexity without domain benefit since
# overfitting results are analysis metadata, not trading domain concepts.


@dataclass
class OverfittingResult:
    """Result of overfitting detection."""

    is_overfitting: bool
    severity: str  # 'none', 'mild', 'moderate', 'severe'
    train_val_gap: Optional[float] = None
    confidence: float = 0.0
    timestamp: datetime = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}


class OverfittingDetector:
    """
    Detects overfitting in trading strategies and models.

    Uses multiple methods:
    - Train/validation performance gap
    - Cross-validation stability
    - Learning curve analysis
    - Out-of-sample degradation
    """

    def __init__(
        self,
        max_acceptable_gap: float = 0.15,
        cv_threshold: float = 0.10,
        oos_threshold: float = 0.20,
    ):
        """
        Initialize overfitting detector.

        Args:
            max_acceptable_gap: Maximum acceptable train/val gap
            cv_threshold: CV stability threshold
            oos_threshold: Out-of-sample degradation threshold
        """
        self.max_acceptable_gap = max_acceptable_gap
        self.cv_threshold = cv_threshold
        self.oos_threshold = oos_threshold

    def detect_from_results(
        self,
        train_result: BacktestResultValue,
        val_result: BacktestResultValue,
        oos_result: Optional[BacktestResultValue] = None,
    ) -> OverfittingResult:
        """
        Detect overfitting from backtest results.

        Args:
            train_result: Training set results
            val_result: Validation set results
            oos_result: Out-of-sample results (optional)

        Returns:
            Overfitting detection result
        """
        # Extract and validate results
        train_return, val_return, gap = self._validate_detection_results(train_result, val_result)

        # Calculate overfitting metrics
        severity, is_overfitting, confidence = self._calculate_overfitting_metrics(gap)

        # Build details dict
        details = self._build_detection_details(train_return, val_return, gap)

        # Apply OOS degradation if available
        if oos_result:
            severity, is_overfitting, details = self._apply_oos_degradation(
                val_result, oos_result, severity, is_overfitting, details
            )

        # Create result object
        result = OverfittingResult(
            is_overfitting=is_overfitting,
            severity=severity,
            train_val_gap=gap,
            confidence=confidence,
            details=details,
        )

        # Log detection event
        self._log_detection_result(result, train_return, val_return, gap, oos_result is not None)

        return result

    def _validate_detection_results(
        self,
        train_result: BacktestResultValue,
        val_result: BacktestResultValue,
    ) -> tuple[float, float, float]:
        """
        Validate and extract metrics from detection results.

        Args:
            train_result: Training set results
            val_result: Validation set results

        Returns:
            Tuple of (train_return, val_return, gap)
        """
        train_return = float(train_result.total_return_pct)
        val_return = float(val_result.total_return_pct)
        gap = train_return - val_return
        return train_return, val_return, gap

    def _calculate_overfitting_metrics(
        self,
        gap: float,
    ) -> tuple[str, bool, float]:
        """
        Calculate overfitting severity and confidence from gap.

        Args:
            gap: Performance gap between train and validation

        Returns:
            Tuple of (severity, is_overfitting, confidence)
        """
        if gap > self.max_acceptable_gap * 2:
            return 'severe', True, 0.95
        elif gap > self.max_acceptable_gap:
            return 'moderate', True, 0.80
        elif gap > self.max_acceptable_gap * 0.5:
            return 'mild', True, 0.60
        else:
            return 'none', False, 0.90

    def _build_detection_details(
        self,
        train_return: float,
        val_return: float,
        gap: float,
    ) -> Dict[str, Any]:
        """
        Build details dictionary for detection result.

        Args:
            train_return: Training return value
            val_return: Validation return value
            gap: Performance gap

        Returns:
            Details dictionary
        """
        return {
            'train_return': train_return,
            'val_return': val_return,
            'gap': gap,
            'gap_threshold': self.max_acceptable_gap,
        }

    # pylint: disable=R0913
    def _apply_oos_degradation(
        self,
        val_result: BacktestResultValue,
        oos_result: BacktestResultValue,
        severity: str,
        is_overfitting: bool,
        details: Dict[str, Any],
    ) -> tuple[str, bool, Dict[str, Any]]:
        """
        Apply out-of-sample degradation to severity assessment.

        Args:
            val_result: Validation result
            oos_result: Out-of-sample result
            severity: Current severity level
            is_overfitting: Current overfitting flag
            details: Details dictionary to update

        Returns:
            Updated tuple of (severity, is_overfitting, details)
        """
        val_return = float(val_result.total_return_pct)
        oos_return = float(oos_result.total_return_pct)
        oos_degradation = val_return - oos_return

        if oos_degradation > self.oos_threshold:
            severity = max(
                severity,
                'moderate',
                key=lambda x: ['none', 'mild', 'moderate', 'severe'].index(x),
            )
            is_overfitting = True

        details['oos_return'] = oos_return
        details['oos_degradation'] = oos_degradation

        return severity, is_overfitting, details

    # pylint: disable=R0913
    def _log_detection_result(
        self,
        result: OverfittingResult,
        train_return: float,
        val_return: float,
        gap: float,
        has_oos: bool,
    ) -> None:
        """
        Log overfitting detection result with structured logging.

        Args:
            result: Overfitting detection result
            train_return: Training return value
            val_return: Validation return value
            gap: Performance gap
            has_oos: Whether OOS result was provided
        """
        logger.info(
            "overfitting_detection_complete",
            extra={
                "detector": "OverfittingDetector",
                "method": "detect_from_results",
                "is_overfitting": result.is_overfitting,
                "severity": result.severity,
                "confidence": result.confidence,
                "train_return": train_return,
                "val_return": val_return,
                "gap": gap,
                "gap_threshold": self.max_acceptable_gap,
                "has_oos_result": has_oos,
            },
        )

        if result.is_overfitting:
            logger.warning(
                "overfitting_detected",
                extra={
                    "detector": "OverfittingDetector",
                    "method": "detect_from_results",
                    "severity": result.severity,
                    "confidence": result.confidence,
                    "train_return": train_return,
                    "val_return": val_return,
                    "gap": gap,
                    "gap_threshold": self.max_acceptable_gap,
                    "oos_degradation": result.details.get('oos_degradation'),
                },
            )

    def detect_from_cv_scores(
        self, cv_scores: List[float], train_scores: Optional[List[float]] = None
    ) -> OverfittingResult:
        """
        Detect overfitting from cross-validation scores.

        Args:
            cv_scores: Cross-validation scores
            train_scores: Training scores (optional)

        Returns:
            Overfitting detection result
        """
        if not cv_scores:
            logger.warning(
                "overfitting_detection_failed",
                extra={
                    "detector": "OverfittingDetector",
                    "method": "detect_from_cv_scores",
                    "error": "No CV scores provided",
                },
            )
            return OverfittingResult(
                is_overfitting=False,
                severity='none',
                confidence=0.0,
                details={'error': 'No CV scores provided'},
            )

        # Calculate CV stability
        cv_mean = np.mean(cv_scores)
        cv_std = np.std(cv_scores)
        cv_cv = cv_std / cv_mean if cv_mean != 0 else float('inf')

        # Check if CV is too unstable
        is_unstable = cv_cv > self.cv_threshold

        # Check train/val gap if train scores provided
        gap = None
        if train_scores:
            train_mean = np.mean(train_scores)
            gap = train_mean - cv_mean
            is_overfitting = is_unstable or gap > self.max_acceptable_gap
        else:
            is_overfitting = is_unstable

        # Determine severity
        if is_overfitting:
            if gap and gap > self.max_acceptable_gap * 2:
                severity = 'severe'
                confidence = 0.90
            elif is_unstable:
                severity = 'moderate'
                confidence = 0.80
            else:
                severity = 'mild'
                confidence = 0.70
        else:
            severity = 'none'
            confidence = 0.85

        result = OverfittingResult(
            is_overfitting=is_overfitting,
            severity=severity,
            train_val_gap=gap,
            confidence=confidence,
            details={
                'cv_mean': cv_mean,
                'cv_std': cv_std,
                'cv_cv': cv_cv,
                'is_unstable': is_unstable,
            },
        )

        # Structured logging for overfitting detection event (LOG-001)
        logger.info(
            "overfitting_detection_complete",
            extra={
                "detector": "OverfittingDetector",
                "method": "detect_from_cv_scores",
                "is_overfitting": is_overfitting,
                "severity": severity,
                "confidence": confidence,
                "cv_mean": float(cv_mean),
                "cv_std": float(cv_std),
                "cv_cv": float(cv_cv),
                "is_unstable": is_unstable,
                "cv_threshold": self.cv_threshold,
                "train_val_gap": gap,
                "has_train_scores": train_scores is not None,
                "n_cv_folds": len(cv_scores),
            },
        )

        if is_overfitting:
            logger.warning(
                "overfitting_detected",
                extra={
                    "detector": "OverfittingDetector",
                    "method": "detect_from_cv_scores",
                    "severity": severity,
                    "confidence": confidence,
                    "cv_cv": float(cv_cv),
                    "cv_threshold": self.cv_threshold,
                    "train_val_gap": gap,
                    "reason": "cv_unstable" if is_unstable else "train_val_gap",
                },
            )

        return result

    def calculate_learning_curve_gap(
        self, train_sizes: List[int], train_scores: List[float], val_scores: List[float]
    ) -> Dict[str, Any]:
        """
        Analyze learning curve for overfitting patterns.

        Args:
            train_sizes: Training set sizes
            train_scores: Training scores at each size
            val_scores: Validation scores at each size

        Returns:
            Learning curve analysis
        """
        if len(train_sizes) < 2:
            logger.warning(
                "learning_curve_analysis_failed",
                extra={
                    "detector": "OverfittingDetector",
                    "method": "calculate_learning_curve_gap",
                    "error": "Insufficient data points for learning curve",
                    "data_points": len(train_sizes),
                },
            )
            return {'error': 'Insufficient data points for learning curve'}

        # Calculate average gaps
        gaps = [train_scores[i] - val_scores[i] for i in range(len(train_sizes))]
        avg_gap = np.mean(gaps)
        final_gap = gaps[-1]

        # Check for convergence
        val_score_range = max(val_scores) - min(val_scores)
        is_converged = val_score_range < self.cv_threshold

        # Check for high variance
        train_score_std = np.std(train_scores)
        val_score_std = np.std(val_scores)
        is_high_variance = train_score_std > self.cv_threshold or val_score_std > self.cv_threshold

        result = {
            'avg_gap': avg_gap,
            'final_gap': final_gap,
            'is_converged': is_converged,
            'is_high_variance': is_high_variance,
            'val_score_range': val_score_range,
            'train_score_std': train_score_std,
            'val_score_std': val_score_std,
            'overfitting_indicated': avg_gap > self.max_acceptable_gap or not is_converged,
        }

        # Structured logging for learning curve analysis (LOG-001)
        logger.info(
            "learning_curve_analysis_complete",
            extra={
                "detector": "OverfittingDetector",
                "method": "calculate_learning_curve_gap",
                "avg_gap": float(avg_gap),
                "final_gap": float(final_gap),
                "is_converged": is_converged,
                "is_high_variance": is_high_variance,
                "val_score_range": float(val_score_range),
                "train_score_std": float(train_score_std),
                "val_score_std": float(val_score_std),
                "overfitting_indicated": result['overfitting_indicated'],
                "n_data_points": len(train_sizes),
                "cv_threshold": self.cv_threshold,
                "max_acceptable_gap": self.max_acceptable_gap,
            },
        )

        if result['overfitting_indicated']:
            logger.warning(
                "overfitting_indicated_in_learning_curve",
                extra={
                    "detector": "OverfittingDetector",
                    "method": "calculate_learning_curve_gap",
                    "avg_gap": float(avg_gap),
                    "final_gap": float(final_gap),
                    "is_converged": is_converged,
                    "is_high_variance": is_high_variance,
                    "reason": "high_gap" if avg_gap > self.max_acceptable_gap else "not_converged",
                },
            )

        return result
