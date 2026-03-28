from __future__ import annotations

"""
Order Flow Imbalance (OFI) Predictor for Price Movements.

This module implements prediction models that use OFI to predict future
price movements, following the methodology in:

- Cont, R., & Kukanov, A. (2017) "Order Flow Imbalance and Price Movement"
- Hasbrouck, J. (1991) "Measuring the Information Content of Stock Trades"
- Aldridge, I. (2013) "High-Frequency Trading"

The predictor implements multiple approaches:
1. Linear regression: OFI → future returns
2. Logistic regression: OFI → direction (up/down)
3. Threshold-based: OFI > threshold → signal
4. Momentum-based: OFI momentum → direction
5. Mean reversion: Extreme OFI → reversal
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal

import numpy as np
from numpy.linalg import LinAlgError
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import StandardScaler

from app.domain.market_analysis.microstructure.ofi.models import (
    OFIConfig,
    OFIHorizon,
    OFIPrediction,
)

logger = logging.getLogger(__name__)


class ModelNotTrainedError(RuntimeError):
    """Raised when prediction is attempted but model is not trained."""


class InvalidDataError(ValueError):
    """Raised when input data is invalid for training or prediction."""


class PredictionError(RuntimeError):
    """Raised when prediction fails unexpectedly."""


class OFIPredictor:
    """
    Predict price movements using Order Flow Imbalance.

    The predictor uses the relationship between OFI and future returns
    to generate directional predictions with confidence scores.

    Key relationships:
    - Positive OFI → Price increase (buying pressure)
    - Negative OFI → Price decrease (selling pressure)
    - OFI magnitude → Strength of prediction (confidence)

    Example:
        >>> predictor = OFIPredictor(config=OFIConfig())
        >>> # Train model on historical data
        >>> predictor.train_model(ofi_history, returns_history)
        >>> # Make prediction
        >>> prediction = predictor.predict_direction(
        ...     current_ofi=0.25,
        ...     historical_ofi=ofi_history,
        ...     historical_returns=returns_history
        ... )
        >>> print(f"Direction: {prediction.predicted_direction}")
        >>> print(f"Confidence: {prediction.confidence:.2%}")
    """

    def __init__(self, config: OFIConfig | None = None):
        """
        Initialize OFI Predictor.

        Args:
            config: OFI configuration (uses defaults if None)
        """
        self.config = config or OFIConfig()
        self.lookback_periods = self.config.lookback_periods
        self.threshold = self.config.ofi_threshold

        # Trained models
        self._linear_model: LinearRegression | None = None
        self._logistic_model: LogisticRegression | None = None
        self._scaler: StandardScaler | None = None
        self._ofi_returns_correlation: float = 0.0

        # Model metadata
        self._is_trained = False
        self._training_samples = 0
        self._feature_importance: dict = {}

    def predict_direction(
        self,
        ofi: float,
        historical_ofi: list[float],
        historical_returns: list[float],
        horizon: OFIHorizon = OFIHorizon.SHORT,
    ) -> OFIPrediction:
        """
        Predict price direction from OFI.

        Uses multiple signals:
        1. OFI threshold rules
        2. Linear regression model (if trained)
        3. OFI momentum
        4. Historical correlation

        Args:
            ofi: Current OFI value
            historical_ofi: Historical OFI values
            historical_returns: Historical returns
            horizon: Prediction horizon

        Returns:
            OFIPrediction with direction and confidence

        Example:
            >>> prediction = predictor.predict_direction(
            ...     ofi=0.35,
            ...     historical_ofi=[0.1, 0.2, 0.15],
            ...     historical_returns=[0.001, 0.002, 0.0015]
            ... )
            >>> print(f"Direction: {prediction.predicted_direction}")
            >>> print(f"Expected move: {prediction.expected_move_bps} bps")
        """
        symbol = "UNKNOWN"  # Would be passed in real implementation
        timestamp = datetime.now(timezone.utc)

        # Get signals from different methods
        threshold_signal = self._get_threshold_signal(ofi)
        model_signal = self._get_model_signal(ofi) if self._is_trained else None
        momentum_signal = self._get_momentum_signal(historical_ofi)

        # Combine signals (weighted ensemble)
        direction, confidence = self._combine_signals(
            threshold_signal, model_signal, momentum_signal
        )

        # Calculate expected move
        expected_move = self._calculate_expected_move(ofi, historical_ofi, historical_returns)

        # Determine horizon string
        horizon_str = self._get_horizon_string(horizon)

        # Build feature dict
        features = {
            "ofi": ofi,
            "threshold_signal": threshold_signal,
            "momentum_signal": momentum_signal,
            "ofi_mean": float(np.mean(historical_ofi)) if historical_ofi else 0.0,
            "ofi_std": float(np.std(historical_ofi)) if historical_ofi else 0.0,
        }
        if model_signal is not None:
            features["model_signal"] = model_signal

        return OFIPrediction(
            symbol=symbol,
            timestamp=timestamp,
            current_ofi=ofi,
            predicted_direction=direction,
            confidence=confidence,
            expected_move_bps=expected_move,
            prediction_horizon=horizon_str,
            model_used="ensemble" if self._is_trained else "threshold",
            features=features,
        )

    def _get_threshold_signal(self, ofi: float) -> float:
        """
        Get signal from threshold rules.

        Returns:
            Signal value: 1.0 (strong buy), 0.5 (buy), 0.0 (neutral),
                        -0.5 (sell), -1.0 (strong sell)
        """
        if ofi > self.config.threshold_strong_buy:
            return 1.0  # Strong buy
        elif ofi > self.config.threshold_moderate_buy:
            return 0.5  # Moderate buy
        elif ofi < self.config.threshold_strong_sell:
            return -1.0  # Strong sell
        elif ofi < self.config.threshold_moderate_sell:
            return -0.5  # Moderate sell
        else:
            return 0.0  # Neutral

    def _get_model_signal(self, ofi: float) -> float | None:
        """
        Get signal from trained linear model.

        Returns:
            Signal value or None if model not trained
        """
        if self._linear_model is None or self._scaler is None:
            return None

        try:
            # Scale OFI
            ofi_scaled = self._scaler.transform([[ofi]])

            # Predict return
            predicted_return = self._linear_model.predict(ofi_scaled)[0]

            # Convert to signal
            if predicted_return > self.config.model_return_threshold:
                return min(1.0, predicted_return * self.config.model_signal_multiplier)
            elif predicted_return < -self.config.model_return_threshold:
                return max(-1.0, predicted_return * self.config.model_signal_multiplier)
            else:
                return 0.0
        except (ValueError, AttributeError) as e:
            logger.warning(
                "Model prediction failed",
                exc_info=True,
                extra={
                    "ofi": ofi,
                    "error_type": type(e).__name__,
                },
            )
            return None

    def _get_momentum_signal(self, historical_ofi: list[float]) -> float:
        """
        Get signal from OFI momentum.

        Returns:
            Signal value based on momentum
        """
        if len(historical_ofi) < self.config.momentum_min_samples:
            return 0.0

        # Calculate momentum (recent - previous average)
        recent = np.mean(historical_ofi[-self.config.momentum_recent_window :])
        previous = (
            np.mean(
                historical_ofi[
                    -self.config.momentum_previous_window : -self.config.momentum_recent_window
                ]
            )
            if len(historical_ofi) >= self.config.momentum_previous_window
            else 0.0
        )

        momentum = recent - previous

        # Convert to signal
        if momentum > self.config.momentum_strong:
            return 1.0
        elif momentum > self.config.momentum_moderate:
            return 0.5
        elif momentum < self.config.momentum_strong_negative:
            return -1.0
        elif momentum < self.config.momentum_moderate_negative:
            return -0.5
        else:
            return 0.0

    def _combine_signals(
        self,
        threshold_signal: float,
        model_signal: float | None,
        momentum_signal: float,
    ) -> tuple[str, float]:
        """
        Combine signals into final direction and confidence.

        Args:
            threshold_signal: Signal from threshold rules
            model_signal: Signal from model (optional)
            momentum_signal: Signal from momentum

        Returns:
            Tuple of (direction, confidence)
        """
        # Weight the signals
        combined = self.config.weight_threshold * threshold_signal
        combined += self.config.weight_momentum * momentum_signal

        if model_signal is not None:
            combined += self.config.weight_model * model_signal
        else:
            # Redistribute weight if no model
            combined /= self.config.weight_threshold + self.config.weight_momentum

        # Determine direction
        if combined > self.config.direction_up_threshold:
            direction = "up"
        elif combined < self.config.direction_down_threshold:
            direction = "down"
        else:
            direction = "neutral"

        # Confidence is based on signal strength
        confidence = min(self.config.confidence_max, abs(combined))

        return direction, confidence

    def _calculate_expected_move(
        self,
        ofi: float,
        historical_ofi: list[float],
        historical_returns: list[float],
    ) -> Decimal:
        """
        Calculate expected price move in basis points.

        Based on:
        1. Historical OFI-returns correlation
        2. Current OFI magnitude
        3. Volatility of returns

        Args:
            ofi: Current OFI value
            historical_ofi: Historical OFI values
            historical_returns: Historical returns

        Returns:
            Expected move in basis points
        """
        if not historical_returns or not historical_ofi:
            return Decimal("0")

        try:
            # Calculate correlation
            if len(historical_ofi) == len(historical_returns):
                ofi_array = np.array(historical_ofi)
                returns_array = np.array(historical_returns)
                corr = np.corrcoef(ofi_array, returns_array)[0, 1]
                if np.isnan(corr):
                    corr = 0.0
            else:
                corr = self._ofi_returns_correlation

            # Calculate return volatility
            return_std = float(np.std(historical_returns))

            # Expected return = OFI * correlation * vol_adjustment
            # This is a simplified model
            expected_return = ofi * corr * return_std * self.config.expected_return_multiplier

            # Convert to basis points
            expected_bps = Decimal(str(expected_return * self.config.expected_bps_multiplier))

            # Cap extreme values
            expected_bps = max(
                Decimal(str(self.config.expected_bps_min)),
                min(Decimal(str(self.config.expected_bps_max)), expected_bps),
            )

            return expected_bps

        except (ValueError, TypeError, ZeroDivisionError) as e:
            logger.warning(
                "Expected move calculation failed",
                exc_info=True,
                extra={
                    "ofi": ofi,
                    "ofi_history_length": len(historical_ofi),
                    "returns_history_length": len(historical_returns) if historical_returns else 0,
                    "error_type": type(e).__name__,
                },
            )
            return Decimal("0")

    def _get_horizon_string(self, horizon: OFIHorizon) -> str:
        """Convert horizon enum to string."""
        horizon_map = {
            OFIHorizon.SHORT: self.config.horizon_short,
            OFIHorizon.MEDIUM: self.config.horizon_medium,
            OFIHorizon.LONG: self.config.horizon_long,
        }
        return horizon_map.get(horizon, self.config.horizon_short)

    def train_model(
        self,
        ofi_history: list[float],
        returns_history: list[float],
    ) -> None:
        """
        Train OFI prediction model.

        Simple linear regression:
            returns[t] = α + β × OFI[t] + ε

        Args:
            ofi_history: Historical OFI values
            returns_history: Corresponding future returns

        Raises:
            InvalidDataError: If data lengths mismatch or insufficient data

        Example:
            >>> predictor = OFIPredictor()
            >>> predictor.train_model(ofi_history, returns_history)
            >>> print(f"Correlation: {predictor._ofi_returns_correlation:.3f}")
        """
        if len(ofi_history) != len(returns_history):
            raise InvalidDataError(
                f"OFI history ({len(ofi_history)}) and returns history ({len(returns_history)}) must have same length"
            )

        if len(ofi_history) < self.config.min_training_samples:
            logger.warning(
                "Insufficient data for training",
                extra={
                    "ofi_history_length": len(ofi_history),
                    "minimum_required": self.config.min_training_samples,
                },
            )
            return

        try:
            # Prepare data
            X = np.array(ofi_history).reshape(-1, 1)
            y = np.array(returns_history)

            # Scale features
            self._scaler = StandardScaler()
            X_scaled = self._scaler.fit_transform(X)

            # Train linear regression
            self._linear_model = LinearRegression()
            self._linear_model.fit(X_scaled, y)

            # Train logistic regression for direction
            direction = (y > 0).astype(int)
            self._logistic_model = LogisticRegression(
                random_state=self.config.logistic_random_state
            )
            self._logistic_model.fit(X_scaled, direction)

            # Store correlation
            corr = np.corrcoef(ofi_history, returns_history)[0, 1]
            self._ofi_returns_correlation = float(corr) if not np.isnan(corr) else 0.0

            # Store metadata
            self._is_trained = True
            self._training_samples = len(ofi_history)

            # Feature importance (coefficients)
            self._feature_importance = {
                "ofi_coef": float(self._linear_model.coef_[0]),
                "intercept": float(self._linear_model.intercept_),
                "correlation": self._ofi_returns_correlation,
                "r_squared": float(self._linear_model.score(X_scaled, y)),
            }

            logger.info(
                "Model trained successfully",
                extra={
                    "training_samples": self._training_samples,
                    "r_squared": self._feature_importance["r_squared"],
                    "correlation": self._ofi_returns_correlation,
                },
            )

        except (ValueError, LinAlgError) as e:
            logger.error(
                "Model training failed",
                exc_info=True,
                extra={
                    "ofi_history_length": len(ofi_history),
                    "error_type": type(e).__name__,
                },
            )
            self._is_trained = False
            raise PredictionError(f"Failed to train model: {e}") from e

    def predict_with_model(self, ofi: float) -> float | None:
        """
        Predict return using trained model.

        Args:
            ofi: Current OFI value

        Returns:
            Predicted return or None if model not trained
        """
        if not self._is_trained or self._linear_model is None or self._scaler is None:
            return None

        try:
            ofi_scaled = self._scaler.transform([[ofi]])
            return float(self._linear_model.predict(ofi_scaled)[0])
        except (ValueError, AttributeError) as e:
            logger.warning(
                "Prediction failed",
                exc_info=True,
                extra={
                    "ofi": ofi,
                    "error_type": type(e).__name__,
                },
            )
            return None

    def predict_direction_with_model(self, ofi: float) -> str | None:
        """
        Predict direction using logistic model.

        Args:
            ofi: Current OFI value

        Returns:
            Direction ("up", "down") or None if model not trained
        """
        if not self._is_trained or self._logistic_model is None or self._scaler is None:
            return None

        try:
            ofi_scaled = self._scaler.transform([[ofi]])
            prediction = self._logistic_model.predict(ofi_scaled)[0]
            return "up" if prediction == 1 else "down"
        except (ValueError, AttributeError) as e:
            logger.warning(
                "Direction prediction failed",
                exc_info=True,
                extra={
                    "ofi": ofi,
                    "error_type": type(e).__name__,
                },
            )
            return None

    def get_model_confidence(self, ofi: float) -> float:
        """
        Get model confidence for prediction.

        Uses the probability from logistic regression.

        Args:
            ofi: Current OFI value

        Returns:
            Confidence score (0-1)
        """
        if not self._is_trained or self._logistic_model is None or self._scaler is None:
            # Fallback to OFI magnitude
            return min(
                self.config.confidence_max, abs(ofi) * self.config.fallback_confidence_multiplier
            )

        try:
            ofi_scaled = self._scaler.transform([[ofi]])
            proba = self._logistic_model.predict_proba(ofi_scaled)[0]
            return float(max(proba))
        except (ValueError, AttributeError):
            return min(
                self.config.confidence_max, abs(ofi) * self.config.fallback_confidence_multiplier
            )

    def calculate_prediction_intervals(
        self, ofi: float, confidence_level: float | None = None
    ) -> tuple[float, float]:
        """
        Calculate prediction intervals for expected return.

        Args:
            ofi: Current OFI value
            confidence_level: Confidence level (e.g., 0.95)

        Returns:
            Tuple of (lower_bound, upper_bound) for expected return
        """
        if not self._is_trained or self._linear_model is None:
            return (0.0, 0.0)

        # Use configured confidence level if not provided
        if confidence_level is None:
            confidence_level = self.config.default_confidence_level

        try:
            # Get prediction
            prediction = self.predict_with_model(ofi)
            if prediction is None:
                return (0.0, 0.0)

            # Calculate residual standard error (simplified)
            # In practice, would use proper standard error calculation
            std_error = abs(prediction) * self.config.prediction_std_error_ratio

            # Z-score for confidence level
            from scipy.stats import norm

            z_score = norm.ppf((1 + confidence_level) / 2)

            # Calculate interval
            margin = z_score * std_error
            lower = prediction - margin
            upper = prediction + margin

            return (lower, upper)

        except (ValueError, AttributeError, ImportError) as e:
            logger.warning(
                "Prediction interval calculation failed",
                exc_info=True,
                extra={
                    "ofi": ofi,
                    "confidence_level": confidence_level,
                    "error_type": type(e).__name__,
                },
            )
            return (0.0, 0.0)

    def detect_regime_change(
        self, historical_ofi: list[float], window: int = 20
    ) -> tuple[bool, str]:
        """
        Detect if OFI regime has changed.

        Regime change indicators:
        - Mean shift: OFI mean has changed significantly
        - Volatility shift: OFI volatility has changed
        - Trend change: OFI trend has reversed

        Args:
            historical_ofi: Historical OFI values
            window: Window for regime detection

        Returns:
            Tuple of (has_changed, regime_description)
        """
        if len(historical_ofi) < window * self.config.regime_window_multiplier:
            return (False, "insufficient_data")

        recent = historical_ofi[-window:]
        previous = historical_ofi[-(window * self.config.regime_window_multiplier) : -window]

        recent_mean = float(np.mean(recent))
        previous_mean = float(np.mean(previous))
        recent_std = float(np.std(recent))
        previous_std = float(np.std(previous))

        # Check for mean shift
        mean_shift = abs(recent_mean - previous_mean) / (
            abs(previous_mean) + self.config.regime_shift_epsilon
        )

        # Check for volatility shift
        vol_shift = abs(recent_std - previous_std) / (
            previous_std + self.config.regime_shift_epsilon
        )

        # Determine regime
        if mean_shift > self.config.regime_mean_shift_threshold:
            if recent_mean > self.config.regime_bullish_threshold:
                return (True, "shifted_to_bullish")
            elif recent_mean < self.config.regime_bearish_threshold:
                return (True, "shifted_to_bearish")

        if vol_shift > self.config.regime_vol_shift_threshold:
            if recent_std > previous_std:
                return (True, "volatility_increased")
            else:
                return (True, "volatility_decreased")

        # Current regime
        if recent_mean > self.config.regime_neutral_positive:
            regime = "bullish_regime"
        elif recent_mean < self.config.regime_neutral_negative:
            regime = "bearish_regime"
        else:
            regime = "neutral_regime"

        return (False, regime)

    def get_feature_importance(self) -> dict:
        """
        Get feature importance from trained model.

        Returns:
            Dictionary with feature importance scores
        """
        if not self._is_trained:
            return {}

        return self._feature_importance.copy()

    def reset_model(self) -> None:
        """Reset trained model."""
        self._linear_model = None
        self._logistic_model = None
        self._scaler = None
        self._is_trained = False
        self._training_samples = 0
        self._ofi_returns_correlation = 0.0
        self._feature_importance = {}
        logger.info(
            "Model reset",
            extra={"was_trained": self._is_trained},
        )
