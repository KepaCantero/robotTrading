# pylint: disable=import-error,unsupported-binary-operation
# mypy: ignore-errors
"""
Order Flow Imbalance (OFI) Signal Generator.

This module generates trading signals from Order Flow Imbalance calculations.
Signals are generated based on OFI thresholds, confidence scores, and
additional filters for mean reversion and momentum.

References:
- Cont, R., & Kukanov, A. (2017) "Order Flow Imbalance and Price Movement"
- Aldridge, I. (2013) "High-Frequency Trading"
"""

import logging
from datetime import datetime
from typing import List, Optional

import numpy as np

from app.market_microstructure.ofi.models import (
    CumulativeOFI,
    OFIPrediction,
    OFISignal,
    OFISignalConfig,
    OrderBookSnapshot,
)
from app.market_microstructure.ofi.ofi_calculator import OFICalculator, OFIResult
from app.market_microstructure.ofi.ofi_predictor import OFIPredictor

logger = logging.getLogger(__name__)


class SignalGenerationError(RuntimeError):
    """Raised when signal generation fails unexpectedly."""


class InvalidOFIError(ValueError):
    """Raised when OFI value is invalid."""


class OFISignalGenerator:
    """
    Generate trading signals from Order Flow Imbalance.

    Signal generation process:
    1. Calculate OFI from order book
    2. Compare to buy/sell thresholds
    3. Generate signal if threshold crossed
    4. Calculate confidence from OFI magnitude
    5. Apply filters (mean reversion, momentum)

    The generator can produce:
    - Directional signals (BUY/SELL based on OFI thresholds)
    - Mean reversion signals (extreme COFI → reversal)
    - Momentum signals (OFI momentum → continuation)

    Example:
        >>> generator = OFISignalGenerator(config=OFISignalConfig())
        >>> signal = generator.generate_signal(order_book, historical_ofi)
        >>> if signal and signal.is_tradeable():
        ...     print(f"Signal: {signal.action} with {signal.confidence:.0%} confidence")
    """

    def __init__(
        self,
        config: OFISignalConfig | None = None,
        calculator: OFICalculator | None = None,
        predictor: OFIPredictor | None = None,
    ):
        """
        Initialize OFI Signal Generator.

        Args:
            config: Signal configuration (uses defaults if None)
            calculator: OFI calculator (creates new if None)
            predictor: OFI predictor (creates new if None)
        """
        self.config = config or OFISignalConfig()
        self.calculator = calculator or OFICalculator()
        self.predictor = predictor or OFIPredictor()

        self.buy_threshold = self.config.buy_threshold
        self.sell_threshold = self.config.sell_threshold
        self.confidence_scale = self.config.confidence_scale

        # Track recent signals for rate limiting
        self._recent_signals: list[datetime] = []

    def generate_signal(
        self,
        order_book: OrderBookSnapshot,
        historical_ofi: list[float],
        historical_returns: list[float] | None = None,
        cofi_tracker: CumulativeOFI | None = None,
    ) -> OFISignal | None:
        """
        Generate trading signal from order book.

        Args:
            order_book: Current order book snapshot
            historical_ofi: Historical OFI values
            historical_returns: Historical returns (optional, for prediction)
            cofi_tracker: Cumulative OFI tracker (optional, for mean reversion)

        Returns:
            OFISignal or None if no signal generated

        Example:
            >>> signal = generator.generate_signal(
            ...     order_book,
            ...     historical_ofi=[0.1, 0.2, 0.15]
            ... )
            >>> if signal:
            ...     print(f"{signal.action} - {signal.reasoning}")
        """
        # Calculate OFI
        ofi_result = self.calculator.calculate_ofi(order_book)
        if not ofi_result.is_valid:
            logger.debug(
                "Invalid OFI",
                extra={
                    "symbol": order_book.symbol,
                    "reason": ofi_result.reason,
                },
            )
            return None

        ofi_result.ofi

        # Check for mean reversion signal first (highest priority)
        if self.config.enable_mean_reversion and cofi_tracker is not None:
            mr_signal = self._generate_mean_reversion_signal(order_book, cofi_tracker, ofi_result)
            if mr_signal:
                return mr_signal

        # Check for momentum signal
        if self.config.enable_momentum:
            mom_signal = self._generate_momentum_signal(order_book, historical_ofi, ofi_result)
            if mom_signal:
                return mom_signal

        # Generate standard threshold-based signal
        return self._generate_threshold_signal(
            order_book, historical_ofi, historical_returns, ofi_result
        )

    def _generate_threshold_signal(
        self,
        order_book: OrderBookSnapshot,
        historical_ofi: list[float],
        historical_returns: list[float] | None,
        ofi_result: OFIResult,
    ) -> OFISignal | None:
        """
        Generate threshold-based signal.

        Signal rules:
        - OFI > buy_threshold: BUY
        - OFI < sell_threshold: SELL
        - Else: No signal (None)
        """
        ofi = ofi_result.ofi

        # Determine action
        if ofi >= self.buy_threshold:
            action = "BUY"
            threshold_used = self.buy_threshold
        elif ofi <= self.sell_threshold:
            action = "SELL"
            threshold_used = self.sell_threshold
        else:
            return None  # No signal

        # Calculate confidence
        confidence = self._calculate_confidence(ofi, action)

        # Get prediction if returns available
        prediction = None
        if historical_returns:
            try:
                prediction = self.predictor.predict_direction(
                    ofi=ofi,
                    historical_ofi=historical_ofi,
                    historical_returns=historical_returns,
                    horizon=self.config.signal_horizon,
                )
            except (ValueError, AttributeError, TypeError) as e:
                logger.warning(
                    "Prediction failed",
                    exc_info=True,
                    extra={
                        "symbol": order_book.symbol,
                        "ofi": ofi,
                        "error_type": type(e).__name__,
                    },
                )

        # Generate reasoning
        reasoning = self._generate_reasoning(ofi, action, ofi_result, prediction)

        # Determine horizon
        horizon = self._determine_horizon(ofi, historical_ofi)

        return OFISignal(
            symbol=order_book.symbol,
            timestamp=order_book.timestamp,
            action=action,
            ofi_value=ofi,
            ofi_threshold_used=threshold_used,
            confidence=confidence,
            expected_horizon=horizon,
            reasoning=reasoning,
            prediction=prediction,
        )

    def _generate_mean_reversion_signal(
        self,
        order_book: OrderBookSnapshot,
        cofi_tracker: CumulativeOFI,
        ofi_result: OFIResult,
    ) -> OFISignal | None:
        """
        Generate mean reversion signal from extreme COFI.

        When COFI is extreme (>2 std from mean), expect reversal.
        """
        threshold = self.config.mean_reversion_threshold

        if cofi_tracker.is_extreme_high(threshold):
            # Extreme buying pressure → expect reversal → SELL
            action = "SELL"
            reasoning = (
                f"COFI extreme high ({cofi_tracker.current_cofi:.2f}, "
                f"z-score: {cofi_tracker.z_score:.2f}). Mean reversion expected."
            )
        elif cofi_tracker.is_extreme_low(threshold):
            # Extreme selling pressure → expect reversal → BUY
            action = "BUY"
            reasoning = (
                f"COFI extreme low ({cofi_tracker.current_cofi:.2f}, "
                f"z-score: {cofi_tracker.z_score:.2f}). Mean reversion expected."
            )
        else:
            return None

        # Confidence based on z-score magnitude
        z_score = cofi_tracker.z_score or 0
        confidence = min(1.0, abs(z_score) / 3.0)

        return OFISignal(
            symbol=order_book.symbol,
            timestamp=order_book.timestamp,
            action=action,
            ofi_value=ofi_result.ofi,
            ofi_threshold_used=threshold,
            confidence=confidence,
            expected_horizon="short",
            reasoning=reasoning,
            prediction=None,
        )

    def _generate_momentum_signal(
        self,
        order_book: OrderBookSnapshot,
        historical_ofi: list[float],
        ofi_result: OFIResult,
    ) -> OFISignal | None:
        """
        Generate momentum-based signal from OFI momentum.

        Strong OFI momentum indicates continuation.
        """
        if len(historical_ofi) < self.config.momentum_window:
            return None

        momentum = self.calculator.calculate_ofi_momentum(
            historical_ofi, window=self.config.momentum_window
        )

        # Momentum threshold
        mom_threshold = 0.1

        if momentum > mom_threshold:
            # Positive momentum → BUY
            action = "BUY"
            reasoning = f"Strong OFI momentum ({momentum:.3f}). " "Buying pressure accelerating."
        elif momentum < -mom_threshold:
            # Negative momentum → SELL
            action = "SELL"
            reasoning = f"Strong OFI momentum ({momentum:.3f}). " "Selling pressure accelerating."
        else:
            return None

        # Confidence based on momentum strength
        confidence = min(1.0, abs(momentum) / 0.2)

        return OFISignal(
            symbol=order_book.symbol,
            timestamp=order_book.timestamp,
            action=action,
            ofi_value=ofi_result.ofi,
            ofi_threshold_used=mom_threshold,
            confidence=confidence,
            expected_horizon="short",
            reasoning=reasoning,
            prediction=None,
        )

    def _calculate_confidence(self, ofi: float, action: str) -> float:
        """
        Calculate signal confidence from OFI magnitude.

        Confidence = min(1.0, |OFI| / confidence_scale)

        Args:
            ofi: Current OFI value
            action: Signal action (BUY/SELL)

        Returns:
            Confidence score (0-1)
        """
        # Base confidence from OFI magnitude
        raw_confidence = abs(ofi) / self.confidence_scale

        # Adjust based on threshold distance
        if action == "BUY":
            threshold_distance = abs(ofi - self.buy_threshold)
        else:
            threshold_distance = abs(ofi - self.sell_threshold)

        # Increase confidence if far from threshold
        adjusted_confidence = raw_confidence + (threshold_distance * 2)

        return min(1.0, max(self.config.min_confidence, adjusted_confidence))

    def _generate_reasoning(
        self,
        ofi: float,
        action: str,
        ofi_result: OFIResult,
        prediction: OFIPrediction | None,
    ) -> str:
        """Generate human-readable reasoning for signal."""
        parts = []

        # OFI description
        if ofi > 0.3:
            parts.append("Very strong buying pressure")
        elif ofi > 0.1:
            parts.append("Moderate buying pressure")
        elif ofi < -0.3:
            parts.append("Very strong selling pressure")
        elif ofi < -0.1:
            parts.append("Moderate selling pressure")
        else:
            parts.append("Balanced order flow")

        # Volume info
        parts.append(
            f"(bid: {ofi_result.bid_volume}, ask: {ofi_result.ask_volume}, "
            f"total: {ofi_result.total_volume})"
        )

        # Prediction info
        if prediction:
            parts.append(
                f"Model predicts {prediction.predicted_direction} with "
                f"{prediction.confidence:.0%} confidence"
            )

        return ". ".join(parts) + "."

    def _determine_horizon(self, ofi: float, historical_ofi: list[float]) -> str:
        """
        Determine expected holding period for signal.

        Based on:
        - OFI magnitude (stronger = shorter)
        - OFI momentum
        - Regime
        """
        # Strong OFI → short-term signal
        if abs(ofi) > 0.4:
            return "short"

        # Check momentum
        if len(historical_ofi) >= 10:
            momentum = self.calculator.calculate_ofi_momentum(historical_ofi)
            if abs(momentum) > 0.15:
                return "short"

        # Default to configured horizon
        return self.config.signal_horizon.value

    def generate_batch_signals(
        self,
        order_books: list[OrderBookSnapshot],
        historical_ofi: List[list[float]],
        historical_returns: Optional[List[list[float]]] = None,
    ) -> list[OFISignal]:
        """
        Generate signals for multiple symbols.

        Args:
            order_books: List of order book snapshots
            historical_ofi: List of historical OFI per symbol
            historical_returns: Optional list of historical returns per symbol

        Returns:
            List of generated signals
        """
        signals = []

        for i, order_book in enumerate(order_books):
            ofi_hist = historical_ofi[i] if i < len(historical_ofi) else []
            ret_hist = (
                historical_returns[i]
                if historical_returns and i < len(historical_returns)
                else None
            )

            try:
                signal = self.generate_signal(order_book, ofi_hist, ret_hist)
                if signal:
                    signals.append(signal)
            except (ValueError, AttributeError, TypeError) as e:
                logger.error(
                    "Signal generation failed",
                    exc_info=True,
                    extra={
                        "symbol": order_book.symbol,
                        "error_type": type(e).__name__,
                    },
                )

        return signals

    def filter_signals(
        self, signals: list[OFISignal], min_confidence: float | None = None
    ) -> list[OFISignal]:
        """
        Filter signals by confidence.

        Args:
            signals: List of signals to filter
            min_confidence: Minimum confidence (uses config if None)

        Returns:
            Filtered list of signals
        """
        threshold = min_confidence or self.config.min_confidence
        return [s for s in signals if s.confidence >= threshold]

    def rank_signals(self, signals: list[OFISignal]) -> list[OFISignal]:
        """
        Rank signals by confidence.

        Args:
            signals: List of signals to rank

        Returns:
            Sorted list (highest confidence first)
        """
        return sorted(signals, key=lambda s: s.confidence, reverse=True)

    def validate_signal(self, signal: OFISignal) -> bool:
        """
        Validate a signal for trading.

        Checks:
        - Confidence above minimum
        - Reasonable OFI value
        - Valid action

        Args:
            signal: Signal to validate

        Returns:
            True if signal is valid for trading
        """
        # Check confidence
        if signal.confidence < self.config.min_confidence:
            return False

        # Check OFI value
        if not -1.0 <= signal.ofi_value <= 1.0:
            return False

        # Check action
        if signal.action not in ("BUY", "SELL"):
            return False

        return True

    def get_signal_summary(self, signals: list[OFISignal]) -> dict:
        """
        Get summary statistics for a list of signals.

        Args:
            signals: List of signals

        Returns:
            Summary dictionary
        """
        if not signals:
            return {
                "total": 0,
                "buy": 0,
                "sell": 0,
                "hold": 0,
                "avg_confidence": 0.0,
            }

        buy_count = sum(1 for s in signals if s.action == "BUY")
        sell_count = sum(1 for s in signals if s.action == "SELL")
        hold_count = sum(1 for s in signals if s.action == "HOLD")
        avg_conf = float(np.mean([s.confidence for s in signals]))

        return {
            "total": len(signals),
            "buy": buy_count,
            "sell": sell_count,
            "hold": hold_count,
            "avg_confidence": avg_conf,
            "symbols": list(set(s.symbol for s in signals)),
        }

    def update_config(self, **kwargs) -> None:
        """
        Update signal configuration.

        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            elif hasattr(self, key):
                setattr(self, key, value)

        # Update thresholds if changed
        if "buy_threshold" in kwargs:
            self.buy_threshold = kwargs["buy_threshold"]
        if "sell_threshold" in kwargs:
            self.sell_threshold = kwargs["sell_threshold"]
        if "confidence_scale" in kwargs:
            self.confidence_scale = kwargs["confidence_scale"]

        logger.info(
            "Configuration updated",
            extra={"updated_keys": list(kwargs.keys())},
        )
