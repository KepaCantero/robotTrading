"""
Alpha Models - Rishi Narang "Inside the Black Box" Chapter 3

This module implements the Alpha Model architecture from Narang's framework:
- Alpha generation framework
- Signal generation with confidence levels
- Alpha decay analysis
- Multi-factor alpha models

Key concepts from "Inside the Black Box":
- Alpha models generate trading signals (direction and confidence)
- Alpha decay measures how quickly signals lose predictive power
- Multiple alpha sources can be combined for robustness
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.domain.models.signal import Signal, SignalSource, SignalStrength, SignalType

logger = logging.getLogger(__name__)


class AlphaType(str, Enum):
    """Types of alpha models."""

    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    SENTIMENT = "sentiment"
    FUNDAMENTAL = "fundamental"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    MACRO = "macro"
    MACHINE_LEARNING = "machine_learning"


class AlphaDecayRegime(str, Enum):
    """Alpha decay regimes."""

    LINEAR = "linear"  # Alpha decays linearly over time
    EXPONENTIAL = "exponential"  # Alpha decays exponentially
    STEP = "step"  # Alpha drops at specific time intervals
    NONE = "none"  # Alpha persists indefinitely


@dataclass
class AlphaSignal:
    """
    Alpha signal with metadata.

    From Narang: Alpha signals should include:
    - Direction (long/short)
    - Confidence level
    - Expected holding period
    - Decay characteristics
    - Risk/reward profile
    """

    symbol: str
    alpha_type: AlphaType
    direction: SignalType  # BUY (long) or SELL (short)
    raw_alpha: float  # Raw alpha value (e.g., expected return)
    confidence: float  # 0-1, probability of positive return
    expected_return: float  # Expected return in basis points
    holding_period_days: int  # Expected holding period
    decay_regime: AlphaDecayRegime
    decay_half_life: Optional[int] = None  # Days until alpha loses half its value
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_signal(self, price: Decimal) -> Signal:
        """Convert AlphaSignal to trading Signal."""
        # Map confidence (0-1) to SignalStrength
        if self.confidence >= 0.8:
            strength = SignalStrength.VERY_STRONG
        elif self.confidence >= 0.7:
            strength = SignalStrength.STRONG
        elif self.confidence >= 0.5:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK

        # Map AlphaType to SignalSource
        alpha_to_signal_source = {
            AlphaType.MOMENTUM: SignalSource.MOMENTUM,
            AlphaType.MEAN_REVERSION: SignalSource.MEAN_REVERSION,
            AlphaType.SENTIMENT: SignalSource.TECHNICAL,
            AlphaType.FUNDAMENTAL: SignalSource.FUNDAMENTAL,
            AlphaType.STATISTICAL_ARBITRAGE: SignalSource.ARBITRAGE,
            AlphaType.MACRO: SignalSource.FUNDAMENTAL,
            AlphaType.MACHINE_LEARNING: SignalSource.TECHNICAL,
        }

        source = alpha_to_signal_source.get(self.alpha_type, SignalSource.TECHNICAL)

        return Signal(
            symbol=self.symbol,
            signal_type=self.direction,
            strength=strength,
            price=price,
            timestamp=self.timestamp,
            confidence=self.confidence * 100,
            liquidity_score=self.metadata.get("liquidity_score", 50.0),
            priority_score=self.metadata.get("priority_score", 50.0),
            volume=Decimal(str(self.metadata.get("volume", 1000))),
            source=source,
            metadata={
                "alpha_type": self.alpha_type.value,
                "expected_return": self.expected_return,
                "holding_period_days": self.holding_period_days,
                "decay_regime": self.decay_regime.value,
                "raw_alpha": self.raw_alpha,
            },
        )


@dataclass
class AlphaDecayMetrics:
    """Metrics for alpha decay analysis."""

    symbol: str
    alpha_type: AlphaType
    total_observations: int
    decay_regime: AlphaDecayRegime
    half_life_days: float
    decay_rate: float  # For exponential decay
    predictive_power_by_day: Dict[int, float]  # Day -> R²
    is_significant: bool  # Whether alpha is statistically significant


class AlphaModel(ABC):
    """
    Abstract base class for Alpha Models.

    From Narang: Alpha models are the core of quantitative strategies.
    They should:
    1. Generate signals with clear direction and confidence
    2. Estimate expected returns
    3. Provide holding period guidance
    4. Track alpha decay characteristics
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.alpha_type = AlphaType(config.get("alpha_type", "momentum"))
        self.min_confidence = config.get("min_confidence", 0.6)
        self.min_holding_period = config.get("min_holding_period", 1)
        self.max_holding_period = config.get("max_holding_period", 30)
        self.signal_history: List[AlphaSignal] = []
        self.performance_history: List[Dict[str, Any]] = []

    @abstractmethod
    def generate_alpha(
        self, symbol: str, market_data: pd.DataFrame, timestamp: datetime
    ) -> Optional[AlphaSignal]:
        """
        Generate alpha signal for a symbol.

        Args:
            symbol: Ticker symbol
            market_data: Historical price/volume data
            timestamp: Current timestamp

        Returns:
            AlphaSignal or None if no alpha detected
        """

    def generate_multi_alpha(
        self, symbols: List[str], market_data: Dict[str, pd.DataFrame], timestamp: datetime
    ) -> List[AlphaSignal]:
        """Generate alpha signals for multiple symbols."""
        signals = []
        for symbol in symbols:
            if symbol in market_data:
                try:
                    signal = self.generate_alpha(symbol, market_data[symbol], timestamp)
                    if signal and signal.confidence >= self.min_confidence:
                        signals.append(signal)
                except (ValueError, TypeError, KeyError) as e:
                    logger.error(
                        "Error generating alpha", symbol=symbol, error=str(e), exc_info=True
                    )
        return signals

    def analyze_alpha_decay(
        self,
        symbol: str,
        realized_returns: pd.Series,
        signal_dates: List[datetime],
        min_observations: int = 30,
    ) -> Optional[AlphaDecayMetrics]:
        """
        Analyze how alpha decays over time after signal generation.

        From Narang: Understanding alpha decay is critical for:
        - Optimal holding period selection
        - Signal timing
        - Portfolio turnover management

        Args:
            symbol: Symbol to analyze
            realized_returns: Actual returns after signals
            signal_dates: Dates when signals were generated
            min_observations: Minimum observations required

        Returns:
            AlphaDecayMetrics or None if insufficient data
        """
        if len(signal_dates) < min_observations:
            logger.debug(
                f"Insufficient data for alpha decay analysis: {len(signal_dates)} < {min_observations}"
            )
            return None

        # Calculate predictive power by day
        max_days = min(30, len(realized_returns) // 2)
        predictive_power = {}

        for day in range(1, max_days + 1):
            # Calculate correlation between signal and realized return
            # For simplicity, using realized_returns as proxy
            if day < len(realized_returns):
                day_returns = realized_returns.shift(-day).dropna()
                if len(day_returns) > 5:
                    # Simplified: use autocorrelation as proxy
                    corr = realized_returns.autocorr(lag=day)
                    predictive_power[day] = abs(corr) if not np.isnan(corr) else 0.0

        if not predictive_power:
            return None

        # Determine decay regime
        decay_regime = self._determine_decay_regime(predictive_power)

        # Calculate half-life
        half_life = self._calculate_half_life(predictive_power)

        # Calculate decay rate (for exponential)
        decay_rate = self._calculate_decay_rate(predictive_power)

        return AlphaDecayMetrics(
            symbol=symbol,
            alpha_type=self.alpha_type,
            total_observations=len(signal_dates),
            decay_regime=decay_regime,
            half_life_days=half_life,
            decay_rate=decay_rate,
            predictive_power_by_day=predictive_power,
            is_significant=max(predictive_power.values()) > 0.1 if predictive_power else False,
        )

    def _determine_decay_regime(self, predictive_power: Dict[int, float]) -> AlphaDecayRegime:
        """Determine the decay regime based on predictive power pattern."""
        if not predictive_power:
            return AlphaDecayRegime.NONE

        days = sorted(predictive_power.keys())
        powers = [predictive_power[d] for d in days]

        # Check if power stays relatively constant
        if max(powers) - min(powers) < 0.1:
            return AlphaDecayRegime.NONE

        # Check for exponential decay
        if len(powers) >= 3:
            # Fit exponential: y = a * exp(-b * x)
            log_powers = [np.log(p) if p > 0.001 else np.log(0.001) for p in powers]
            if len(set(log_powers)) > 1:
                corr = np.corrcoef(days, log_powers)[0, 1]
                if corr < -0.7:  # Strong negative correlation = exponential decay
                    return AlphaDecayRegime.EXPONENTIAL

        # Check for step decay (sudden drops)
        if len(powers) >= 4:
            for i in range(1, len(powers) - 1):
                if powers[i] - powers[i + 1] > 0.2:  # Sudden drop
                    return AlphaDecayRegime.STEP

        # Default to linear
        return AlphaDecayRegime.LINEAR

    def _calculate_half_life(self, predictive_power: Dict[int, float]) -> float:
        """Calculate half-life in days (time until predictive power halves)."""
        if not predictive_power:
            return 0.0

        max_power = max(predictive_power.values())
        half_power = max_power / 2

        # Find first day where power drops below half
        for day, power in sorted(predictive_power.items()):
            if power < half_power:
                return float(day)

        # If never drops below half, return max day
        return float(max(predictive_power.keys()))

    def _calculate_decay_rate(self, predictive_power: Dict[int, float]) -> float:
        """Calculate decay rate for exponential decay."""
        if not predictive_power or len(predictive_power) < 3:
            return 0.0

        try:
            days = sorted(predictive_power.keys())
            powers = [predictive_power[d] for d in days]

            # Fit exponential using linear regression on log-transformed data
            log_powers = []
            valid_days = []
            for d, p in zip(days, powers):
                if p > 0.001:
                    log_powers.append(np.log(p))
                    valid_days.append(d)

            if len(log_powers) < 3:
                return 0.0

            # Simple linear regression: log(y) = log(a) - b*x
            # Decay rate is -b
            coeffs = np.polyfit(valid_days, log_powers, 1)
            decay_rate = -coeffs[0]  # Negative slope

            return max(0.0, decay_rate)

        except (ValueError, TypeError, np.linalg.LinAlgError):
            return 0.0

    def get_optimal_holding_period(
        self, decay_metrics: Optional[AlphaDecayMetrics], default_days: int = 5
    ) -> int:
        """
        Determine optimal holding period based on alpha decay.

        From Narang: Exit positions when alpha decays significantly.
        """
        if not decay_metrics or decay_metrics.decay_regime == AlphaDecayRegime.NONE:
            return default_days

        # For exponential decay, use half-life as guideline
        if decay_metrics.decay_regime == AlphaDecayRegime.EXPONENTIAL:
            return max(self.min_holding_period, int(decay_metrics.half_life_days * 0.8))

        # For linear decay, exit when predictive power drops below threshold
        if decay_metrics.decay_regime == AlphaDecayRegime.LINEAR:
            threshold_power = max(decay_metrics.predictive_power_by_day.values()) * 0.5
            for day, power in sorted(decay_metrics.predictive_power_by_day.items()):
                if power < threshold_power:
                    return max(self.min_holding_period, day)

        # For step decay, exit just before step
        if decay_metrics.decay_regime == AlphaDecayRegime.STEP:
            sorted_days = sorted(decay_metrics.predictive_power_by_day.items())
            for i in range(len(sorted_days) - 1):
                day, power = sorted_days[i]
                next_day, next_power = sorted_days[i + 1]
                if next_power < power * 0.7:  # Significant drop
                    return max(self.min_holding_period, day - 1)

        return default_days

    def combine_alpha_signals(
        self, signals: List[AlphaSignal], method: str = "weighted"
    ) -> Optional[AlphaSignal]:
        """
        Combine multiple alpha signals into one.

        From Narang: Combining multiple alpha sources can improve robustness.
        Methods:
        - weighted: Weight by confidence
        - voting: Majority vote
        - ensemble: Machine learning ensemble
        """
        if not signals:
            return None

        if len(signals) == 1:
            return signals[0]

        if method == "voting":
            return self._voting_combine(signals)
        elif method == "weighted":
            return self._weighted_combine(signals)
        else:
            return self._weighted_combine(signals)

    def _voting_combine(self, signals: List[AlphaSignal]) -> Optional[AlphaSignal]:
        """Combine signals by voting."""
        # Count votes for long vs short
        long_votes = sum(1 for s in signals if s.direction == SignalType.BUY)
        short_votes = len(signals) - long_votes

        if long_votes == short_votes:
            return None  # No consensus

        # Determine direction by majority
        direction = SignalType.BUY if long_votes > short_votes else SignalType.SELL
        winning_signals = [s for s in signals if s.direction == direction]

        # Average metrics from winning signals
        avg_confidence = np.mean([s.confidence for s in winning_signals])
        avg_expected_return = np.mean([s.expected_return for s in winning_signals])
        avg_holding = int(np.mean([s.holding_period_days for s in winning_signals]))

        return AlphaSignal(
            symbol=signals[0].symbol,
            alpha_type=AlphaType.MACHINE_LEARNING,  # Combined alpha
            direction=direction,
            raw_alpha=avg_expected_return,
            confidence=avg_confidence,
            expected_return=avg_expected_return,
            holding_period_days=avg_holding,
            decay_regime=AlphaDecayRegime.LINEAR,
            metadata={"combined_from": len(signals)},
        )

    def _weighted_combine(self, signals: List[AlphaSignal]) -> Optional[AlphaSignal]:
        """Combine signals by weighting by confidence."""
        # Separate long and short signals
        long_signals = [s for s in signals if s.direction == SignalType.BUY]
        short_signals = [s for s in signals if s.direction == SignalType.SELL]

        # Calculate weighted scores
        long_score = sum(s.confidence * s.expected_return for s in long_signals)
        short_score = sum(s.confidence * s.expected_return for s in short_signals)

        if long_score <= 0 and short_score <= 0:
            return None

        # Determine direction
        direction = SignalType.BUY if long_score > short_score else SignalType.SELL
        chosen_signals = long_signals if long_score > short_score else short_signals

        if not chosen_signals:
            return None

        # Weight by confidence
        total_confidence = sum(s.confidence for s in chosen_signals)
        if total_confidence == 0:
            return None

        weighted_return = (
            sum(s.confidence * s.expected_return for s in chosen_signals) / total_confidence
        )
        weighted_holding = int(
            sum(s.confidence * s.holding_period_days for s in chosen_signals) / total_confidence
        )
        weighted_confidence = total_confidence / len(chosen_signals)

        return AlphaSignal(
            symbol=signals[0].symbol,
            alpha_type=AlphaType.MACHINE_LEARNING,
            direction=direction,
            raw_alpha=weighted_return,
            confidence=weighted_confidence,
            expected_return=weighted_return,
            holding_period_days=weighted_holding,
            decay_regime=AlphaDecayRegime.LINEAR,
            metadata={"combined_from": len(signals)},
        )


class MomentumAlphaModel(AlphaModel):
    """Momentum-based alpha model."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lookback_period = config.get("lookback_period", 20)
        self.alpha_type = AlphaType.MOMENTUM

    def generate_alpha(
        self, symbol: str, market_data: pd.DataFrame, timestamp: datetime
    ) -> Optional[AlphaSignal]:
        """Generate momentum alpha signal."""
        if len(market_data) < self.lookback_period:
            return None

        # Calculate momentum (ROC)
        prices = market_data["close"]
        momentum = (prices.iloc[-1] / prices.iloc[-self.lookback_period] - 1) * 100

        # Calculate volatility for confidence
        returns = prices.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100  # Annualized

        # Direction based on momentum
        direction = SignalType.BUY if momentum > 0 else SignalType.SELL

        # Confidence based on momentum strength and volatility
        # Higher momentum + lower volatility = higher confidence
        momentum_strength = abs(momentum) / 10  # Normalize: 10% = full strength
        volatility_penalty = min(1.0, volatility / 50)  # 50% vol = max penalty
        confidence = max(0.0, min(1.0, momentum_strength * (1 - volatility_penalty * 0.5)))

        # Expected return proportional to momentum (with dampening)
        expected_return = momentum * 0.5  # Conservative estimate

        # Holding period based on momentum persistence
        # Higher momentum = longer holding
        holding_period = min(
            self.max_holding_period,
            max(self.min_holding_period, int(abs(momentum) / 2)),
        )

        return AlphaSignal(
            symbol=symbol,
            alpha_type=self.alpha_type,
            direction=direction,
            raw_alpha=momentum,
            confidence=confidence,
            expected_return=expected_return,
            holding_period_days=holding_period,
            decay_regime=AlphaDecayRegime.EXPONENTIAL,
            decay_half_life=holding_period // 2,
            metadata={
                "momentum": momentum,
                "volatility": volatility,
                "lookback_period": self.lookback_period,
            },
        )


class MeanReversionAlphaModel(AlphaModel):
    """Mean reversion alpha model."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lookback_period = config.get("lookback_period", 20)
        self.z_score_threshold = config.get("z_score_threshold", 2.0)
        self.alpha_type = AlphaType.MEAN_REVERSION

    def generate_alpha(
        self, symbol: str, market_data: pd.DataFrame, timestamp: datetime
    ) -> Optional[AlphaSignal]:
        """Generate mean reversion alpha signal."""
        if len(market_data) < self.lookback_period:
            return None

        prices = market_data["close"]

        # Calculate z-score
        mean = prices.rolling(window=self.lookback_period).mean().iloc[-1]
        std = prices.rolling(window=self.lookback_period).std().iloc[-1]
        current_price = prices.iloc[-1]

        if std == 0:
            return None

        z_score = (current_price - mean) / std

        # Signal only if significantly deviated from mean
        if abs(z_score) < self.z_score_threshold:
            return None

        # Direction: opposite to deviation
        direction = SignalType.SELL if z_score > 0 else SignalType.BUY

        # Confidence based on z-score magnitude
        confidence = min(1.0, abs(z_score) / (self.z_score_threshold * 2))

        # Expected return: reversion to mean
        expected_return = -z_score * 2  # Expected bps return

        # Holding period: quick reversion expected
        holding_period = max(self.min_holding_period, min(5, int(abs(z_score))))

        return AlphaSignal(
            symbol=symbol,
            alpha_type=self.alpha_type,
            direction=direction,
            raw_alpha=-z_score,
            confidence=confidence,
            expected_return=expected_return,
            holding_period_days=holding_period,
            decay_regime=AlphaDecayRegime.EXPONENTIAL,
            decay_half_life=holding_period // 3,
            metadata={
                "z_score": z_score,
                "mean": mean,
                "std": std,
                "lookback_period": self.lookback_period,
            },
        )


class MultiFactorAlphaModel(AlphaModel):
    """Combines multiple alpha sources for robustness."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.sub_models: List[AlphaModel] = []
        self.alpha_type = AlphaType.MACHINE_LEARNING
        self.combination_method = config.get("combination_method", "weighted")

    def add_sub_model(self, model: AlphaModel) -> None:
        """Add a sub-model to the ensemble."""
        self.sub_models.append(model)

    def generate_alpha(
        self, symbol: str, market_data: pd.DataFrame, timestamp: datetime
    ) -> Optional[AlphaSignal]:
        """Generate combined alpha from all sub-models."""
        if not self.sub_models:
            return None

        # Get signals from all sub-models
        signals = []
        for model in self.sub_models:
            try:
                signal = model.generate_alpha(symbol, market_data, timestamp)
                if signal:
                    signals.append(signal)
            except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
                logger.error(
                    "Error in sub-model", model_name=model.name, error=str(e), exc_info=True
                )

        if not signals:
            return None

        # Combine signals
        return self.combine_alpha_signals(signals, method=self.combination_method)


def get_alpha_model(config: Dict[str, Any]) -> AlphaModel:
    """
    Factory function to create alpha models.

    Args:
        config: Configuration dictionary with 'model_type' key

    Returns:
        AlphaModel instance
    """
    model_type = config.get("model_type", "momentum")

    if model_type == "momentum":
        return MomentumAlphaModel(config)
    elif model_type == "mean_reversion":
        return MeanReversionAlphaModel(config)
    elif model_type == "multi_factor":
        return MultiFactorAlphaModel(config)
    else:
        raise ValueError(f"Unknown alpha model type: {model_type}")


__all__ = [
    "AlphaType",
    "AlphaDecayRegime",
    "AlphaSignal",
    "AlphaDecayMetrics",
    "AlphaModel",
    "MomentumAlphaModel",
    "MeanReversionAlphaModel",
    "MultiFactorAlphaModel",
    "get_alpha_model",
]
