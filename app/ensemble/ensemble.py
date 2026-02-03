"""
Ensemble Voting Methods for Combining Trading Signals.

This module implements various ensemble voting mechanisms to combine
signals from multiple trading strategies into a single decision.
"""

import logging
from collections import Counter
from typing import Any, Dict, List, Optional

import numpy as np

from app.ensemble.models import EnsembleConfig, EnsembleMethod, EnsembleSignal
from app.models.signal import Signal, SignalType

logger = logging.getLogger(__name__)


class EnsembleVoting:
    """Ensemble voting classifier for combining trading signals.

    This class provides multiple voting methods to combine signals from
    different strategies into a single, more robust trading decision.

    Supported methods:
    - Majority voting: Select the signal with the most votes
    - Weighted voting: Weight votes by strategy performance
    - Soft voting: Average confidence scores and select based on threshold

    Example:
        >>> voting = EnsembleVoting(
        ...     config=EnsembleConfig(
        ...         method=EnsembleMethod.WEIGHTED_VOTING,
        ...         strategies=['momentum', 'mean_reversion']
        ...     )
        ... )
        >>> combined_signal = voting.combine_signals(signals_list)
    """

    def __init__(self, config: EnsembleConfig):
        """Initialize ensemble voting with configuration.

        Args:
            config: Ensemble configuration including method and strategies

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            if not config.strategies or len(config.strategies) < 2:
                raise ValueError("At least 2 strategies required for ensemble")

            self.config = config
            self.method = config.method
            self.strategies = config.strategies
            self.strategy_weights = config.strategy_weights or self._initialize_weights()

            # Track historical performance for weighted voting
            self.performance_history: Dict[str, List[float]] = {
                s: [] for s in self.strategies
            }

        except (TypeError, AttributeError) as e:
            logger.error("Invalid ensemble configuration", exc_info=True)
            raise ValueError(f"Invalid ensemble configuration: {e}") from e

    def combine_signals(self, signals: List[Signal]) -> Optional[EnsembleSignal]:
        """Combine multiple signals into a single ensemble decision.

        Args:
            signals: List of signals from different strategies

        Returns:
            Combined ensemble signal, or None if combination fails

        Raises:
            ValueError: If signals list is invalid
        """
        try:
            if not signals:
                return None

            if len(signals) != len(self.strategies):
                raise ValueError(f"Expected {len(self.strategies)} signals, got {len(signals)}")

            # Filter signals by confidence threshold
            valid_signals = [s for s in signals if s.confidence >= self.config.confidence_threshold]

            if not valid_signals:
                return None

            # Check agreement level
            agreement = self._calculate_agreement(valid_signals)

            if agreement < self.config.min_agreement:
                return None

            # Apply voting method
            if self.method == EnsembleMethod.MAJORITY_VOTING:
                return self._majority_voting(valid_signals, agreement)
            elif self.method == EnsembleMethod.WEIGHTED_VOTING:
                return self._weighted_voting(valid_signals, agreement)
            elif self.method == EnsembleMethod.SOFT_VOTING:
                return self._soft_voting(valid_signals, agreement)
            elif self.method == EnsembleMethod.RANK_AVERAGING:
                return self._rank_averaging(valid_signals, agreement)
            elif self.method == EnsembleMethod.PERFORMANCE_WEIGHTED:
                return self._performance_weighted(valid_signals, agreement)
            elif self.method == EnsembleMethod.CONFIDENCE_WEIGHTED:
                return self._confidence_weighted(valid_signals, agreement)
            else:
                raise ValueError(f"Unsupported ensemble method: {self.method}")

        except Exception:
            logger.error("Signal combination failed", exc_info=True)
            return None

    def _initialize_weights(self) -> Dict[str, float]:
        """Initialize equal weights for all strategies.

        Returns:
            Dictionary mapping strategy names to equal weights
        """
        weight = 1.0 / len(self.strategies)
        return {strategy: weight for strategy in self.strategies}

    def _calculate_agreement(self, signals: List[Signal]) -> float:
        """Calculate agreement level among signals.

        Agreement is defined as the fraction of signals that agree with
        the majority decision.

        Args:
            signals: List of signals to analyze

        Returns:
            Agreement level between 0 and 1
        """
        try:
            if not signals:
                return 0.0

            # Count signal types
            signal_types = [s.signal_type for s in signals]
            counts = Counter(signal_types)

            # Get majority signal type
            majority_type, majority_count = counts.most_common(1)[0]

            # Calculate agreement
            agreement = majority_count / len(signal_types)

            return float(agreement)

        except Exception:
            logger.error("Calculation failed", exc_info=True)
            return 0.0

    def _majority_voting(self, signals: List[Signal], agreement: float) -> EnsembleSignal:
        """Perform majority voting on signals.

        Args:
            signals: List of signals to combine
            agreement: Pre-calculated agreement level

        Returns:
            Combined ensemble signal
        """
        try:
            # Count votes
            signal_types = [s.signal_type for s in signals]
            counts = Counter(signal_types)

            # Get majority decision
            majority_type = counts.most_common(1)[0][0]

            # Calculate average confidence
            avg_confidence = sum(s.confidence for s in signals) / len(signals)

            # Build vote dictionary
            strategy_votes = self._build_strategy_votes(signals)

            # Get symbol from first signal
            symbol = signals[0].symbol if signals else "UNKNOWN"

            return EnsembleSignal(
                symbol=symbol,
                signal_type=(
                    majority_type if isinstance(majority_type, str) else majority_type.value
                ),
                confidence=avg_confidence,
                agreement=agreement,
                strategy_votes=strategy_votes,
                strategy_weights=self.strategy_weights,
            )

        except Exception as e:
            logger.error("Majority voting failed", exc_info=True)
            raise RuntimeError(f"Majority voting failed: {e}") from e

    def _weighted_voting(self, signals: List[Signal], agreement: float) -> EnsembleSignal:
        """Perform weighted voting on signals.

        Votes are weighted by strategy weights. The signal with the
        highest total weight wins.

        Args:
            signals: List of signals to combine
            agreement: Pre-calculated agreement level

        Returns:
            Combined ensemble signal
        """
        try:
            # Calculate weighted scores for each signal type
            signal_scores: Dict[SignalType, float] = {}

            for signal, strategy in zip(signals, self.strategies):
                weight = self.strategy_weights.get(strategy, 0.0)
                signal_type = signal.signal_type

                if signal_type not in signal_scores:
                    signal_scores[signal_type] = 0.0

                signal_scores[signal_type] += weight

            # Get signal type with highest weight
            winning_type = max(signal_scores, key=signal_scores.get)

            # Calculate weighted confidence
            weighted_confidence = self._calculate_weighted_confidence(signals)

            # Build vote dictionary
            strategy_votes = self._build_strategy_votes(signals)

            # Get symbol from first signal
            symbol = signals[0].symbol if signals else "UNKNOWN"

            return EnsembleSignal(
                symbol=symbol,
                signal_type=(
                    winning_type if isinstance(winning_type, str) else winning_type.value
                ),
                confidence=weighted_confidence,
                agreement=agreement,
                strategy_votes=strategy_votes,
                strategy_weights=self.strategy_weights,
            )

        except Exception as e:
            logger.error("Weighted voting failed", exc_info=True)
            raise RuntimeError(f"Weighted voting failed: {e}") from e

    def _soft_voting(self, signals: List[Signal], agreement: float) -> EnsembleSignal:
        """Perform soft voting based on confidence scores.

        Soft voting averages the confidence scores for each signal type
        and selects the type with the highest average confidence.

        Args:
            signals: List of signals to combine
            agreement: Pre-calculated agreement level

        Returns:
            Combined ensemble signal
        """
        try:
            # Group confidence scores by signal type
            confidence_by_type: Dict[SignalType, List[float]] = {}

            for signal in signals:
                signal_type = signal.signal_type

                if signal_type not in confidence_by_type:
                    confidence_by_type[signal_type] = []

                confidence_by_type[signal_type].append(signal.confidence)

            # Calculate average confidence for each type
            avg_confidence_by_type = {
                sig_type: np.mean(confidences)
                for sig_type, confidences in confidence_by_type.items()
            }

            # Get signal type with highest average confidence
            winning_type = max(avg_confidence_by_type, key=avg_confidence_by_type.get)
            max_confidence = avg_confidence_by_type[winning_type]

            # Build vote dictionary
            strategy_votes = self._build_strategy_votes(signals)

            # Get symbol from first signal
            symbol = signals[0].symbol if signals else "UNKNOWN"

            return EnsembleSignal(
                symbol=symbol,
                signal_type=(
                    winning_type if isinstance(winning_type, str) else winning_type.value
                ),
                confidence=max_confidence,
                agreement=agreement,
                strategy_votes=strategy_votes,
                strategy_weights=self.strategy_weights,
            )

        except Exception as e:
            logger.error("Soft voting failed", exc_info=True)
            raise RuntimeError(f"Soft voting failed: {e}") from e

    def _rank_averaging(self, signals: List[Signal], agreement: float) -> EnsembleSignal:
        """Perform rank averaging on signals.

        Signals are ranked by confidence, and ranks are averaged.
        The signal type with the best average rank wins.

        Args:
            signals: List of signals to combine
            agreement: Pre-calculated agreement level

        Returns:
            Combined ensemble signal
        """
        try:
            # Sort all signals by confidence
            sorted_signals = sorted(signals, key=lambda s: s.confidence, reverse=True)

            # Assign ranks (higher confidence = better rank = lower number)
            ranks_by_type: Dict[SignalType, List[int]] = {}

            for rank, signal in enumerate(sorted_signals):
                signal_type = signal.signal_type

                if signal_type not in ranks_by_type:
                    ranks_by_type[signal_type] = []

                ranks_by_type[signal_type].append(rank)

            # Calculate average rank for each signal type
            avg_rank_by_type = {
                sig_type: np.mean(ranks) for sig_type, ranks in ranks_by_type.items()
            }

            # Get signal type with best (lowest) average rank
            winning_type = min(avg_rank_by_type, key=avg_rank_by_type.get)

            # Calculate confidence from inverse rank
            best_avg_rank = avg_rank_by_type[winning_type]
            confidence = 100.0 * (1 - best_avg_rank / len(signals))

            # Build vote dictionary
            strategy_votes = self._build_strategy_votes(signals)

            # Get symbol from first signal
            symbol = signals[0].symbol if signals else "UNKNOWN"

            return EnsembleSignal(
                symbol=symbol,
                signal_type=(
                    winning_type if isinstance(winning_type, str) else winning_type.value
                ),
                confidence=confidence,
                agreement=agreement,
                strategy_votes=strategy_votes,
                strategy_weights=self.strategy_weights,
            )

        except Exception as e:
            logger.error("Rank averaging failed", exc_info=True)
            raise RuntimeError(f"Rank averaging failed: {e}") from e

    def _performance_weighted(self, signals: List[Signal], agreement: float) -> EnsembleSignal:
        """Perform performance-weighted voting.

        Weights are dynamically adjusted based on historical performance
        of each strategy.

        Args:
            signals: List of signals to combine
            agreement: Pre-calculated agreement level

        Returns:
            Combined ensemble signal
        """
        try:
            # Calculate performance-based weights
            perf_weights = self._calculate_performance_weights()

            # Calculate weighted scores
            signal_scores: Dict[SignalType, float] = {}

            for signal, strategy in zip(signals, self.strategies):
                weight = perf_weights.get(strategy, 1.0 / len(self.strategies))
                signal_type = signal.signal_type

                if signal_type not in signal_scores:
                    signal_scores[signal_type] = 0.0

                signal_scores[signal_type] += weight

            # Get winning signal type
            winning_type = max(signal_scores, key=signal_scores.get)

            # Calculate weighted confidence using performance weights
            weighted_confidence = self._calculate_weighted_confidence_with_weights(
                signals, perf_weights
            )

            # Build vote dictionary
            strategy_votes = self._build_strategy_votes(signals)

            # Get symbol from first signal
            symbol = signals[0].symbol if signals else "UNKNOWN"

            return EnsembleSignal(
                symbol=symbol,
                signal_type=(
                    winning_type if isinstance(winning_type, str) else winning_type.value
                ),
                confidence=weighted_confidence,
                agreement=agreement,
                strategy_votes=strategy_votes,
                strategy_weights=perf_weights,
            )

        except Exception as e:
            logger.error("Performance-weighted voting failed", exc_info=True)
            raise RuntimeError(f"Performance-weighted voting failed: {e}") from e

    def _confidence_weighted(self, signals: List[Signal], agreement: float) -> EnsembleSignal:
        """Perform confidence-weighted voting.

        Each signal's vote is weighted by its confidence score.

        Args:
            signals: List of signals to combine
            agreement: Pre-calculated agreement level

        Returns:
            Combined ensemble signal
        """
        try:
            # Calculate total confidence
            total_confidence = sum(s.confidence for s in signals)

            if total_confidence == 0:
                return self._majority_voting(signals, agreement)

            # Calculate weighted scores
            signal_scores: Dict[SignalType, float] = {}

            for signal in signals:
                weight = signal.confidence / total_confidence
                signal_type = signal.signal_type

                if signal_type not in signal_scores:
                    signal_scores[signal_type] = 0.0

                signal_scores[signal_type] += weight

            # Get winning signal type
            winning_type = max(signal_scores, key=signal_scores.get)

            # Calculate weighted confidence
            weighted_confidence = self._calculate_confidence_weighted_confidence(
                signals, total_confidence
            )

            # Build vote dictionary
            strategy_votes = self._build_strategy_votes(signals)

            # Get symbol from first signal
            symbol = signals[0].symbol if signals else "UNKNOWN"

            return EnsembleSignal(
                symbol=symbol,
                signal_type=(
                    winning_type if isinstance(winning_type, str) else winning_type.value
                ),
                confidence=weighted_confidence,
                agreement=agreement,
                strategy_votes=strategy_votes,
                strategy_weights=self.strategy_weights,
            )

        except Exception as e:
            logger.error("Confidence-weighted voting failed", exc_info=True)
            raise RuntimeError(f"Confidence-weighted voting failed: {e}") from e

    def _calculate_performance_weights(self) -> Dict[str, float]:
        """Calculate performance-based weights for strategies.

        Strategies with better historical performance get higher weights.

        Returns:
            Dictionary mapping strategy names to weights
        """
        try:
            weights = {}

            for strategy in self.strategies:
                history = self.performance_history.get(strategy, [])

                if not history:
                    # Use default weight if no history
                    weights[strategy] = 1.0 / len(self.strategies)
                else:
                    # Use average performance as weight
                    avg_perf = np.mean(history)
                    weights[strategy] = max(0.0, avg_perf)

            # Normalize weights to sum to 1
            total = sum(weights.values())

            if total == 0:
                return self._initialize_weights()

            return {k: v / total for k, v in weights.items()}

        except Exception:
            logger.error("Performance weight calculation failed", exc_info=True)
            return self._initialize_weights()

    def update_performance(self, strategy: str, performance: float) -> None:
        """Update performance history for a strategy.

        Args:
            strategy: Strategy name
            performance: Performance metric (e.g., return, Sharpe ratio)

        Raises:
            ValueError: If strategy is not in ensemble
        """
        if strategy not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy}")

        if strategy not in self.performance_history:
            self.performance_history[strategy] = []

        self.performance_history[strategy].append(performance)

        # Keep only recent history
        max_history = self.config.lookback_period
        if len(self.performance_history[strategy]) > max_history:
            self.performance_history[strategy] = self.performance_history[strategy][-max_history:]

    def get_strategy_weights(self) -> Dict[str, float]:
        """Get current strategy weights.

        Returns:
            Dictionary of current strategy weights
        """
        return self.strategy_weights.copy()

    def set_strategy_weights(self, weights: Dict[str, float]) -> None:
        """Set custom strategy weights.

        Args:
            weights: Dictionary of strategy weights

        Raises:
            ValueError: If weights are invalid
        """
        if not weights:
            raise ValueError("Weights dictionary cannot be empty")

        if set(weights.keys()) != set(self.strategies):
            raise ValueError(
                f"Weights must match strategies. "
                f"Expected: {set(self.strategies)}, Got: {set(weights.keys())}"
            )

        total = sum(weights.values())

        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        if any(w < 0 for w in weights.values()):
            raise ValueError("Weights cannot be negative")

        self.strategy_weights = weights.copy()

    def _infer_strategy(self, signal: Signal) -> str:
        """Infer strategy name from signal metadata.

        Args:
            signal: Signal to analyze

        Returns:
            Inferred strategy name
        """
        # Try to get strategy from metadata
        if signal.metadata and "strategy" in signal.metadata:
            return signal.metadata["strategy"]

        # Try to get from source
        if hasattr(signal, "source") and signal.source:
            return signal.source.value

        # Fallback: use signal source
        return "unknown"

    def _build_strategy_votes(self, signals: List[Signal]) -> Dict[str, str]:
        """Build strategy votes dictionary from signals.

        Args:
            signals: List of signals

        Returns:
            Dictionary mapping strategy/source to signal type
        """
        strategy_votes = {}
        for signal in signals:
            strategy = signal.symbol if signal.symbol else self._infer_strategy(signal)
            signal_type_str = (
                signal.signal_type
                if isinstance(signal.signal_type, str)
                else signal.signal_type.value
            )
            strategy_votes[strategy] = signal_type_str
        return strategy_votes

    def _calculate_weighted_confidence(self, signals: List[Signal]) -> float:
        """Calculate weighted confidence using strategy weights.

        Args:
            signals: List of signals

        Returns:
            Weighted confidence score
        """
        return sum(
            s.confidence * self.strategy_weights.get(strategy, 0.0)
            for s, strategy in zip(signals, self.strategies)
        )

    def _calculate_weighted_confidence_with_weights(
        self, signals: List[Signal], weights: Dict[str, float]
    ) -> float:
        """Calculate weighted confidence using provided weights.

        Args:
            signals: List of signals
            weights: Strategy weights to use

        Returns:
            Weighted confidence score
        """
        return sum(
            s.confidence * weights.get(strategy, 0.0)
            for s, strategy in zip(signals, self.strategies)
        )

    def _calculate_confidence_weighted_confidence(
        self, signals: List[Signal], total_confidence: float
    ) -> float:
        """Calculate confidence-weighted confidence score.

        Args:
            signals: List of signals
            total_confidence: Sum of all signal confidences

        Returns:
            Weighted confidence score
        """
        return sum(
            s.confidence * (s.confidence / total_confidence) for s in signals
        )

    def calculate_disagreement(self, signals: List[Signal]) -> float:
        """Calculate disagreement level among signals.

        Disagreement is the complement of agreement.

        Args:
            signals: List of signals to analyze

        Returns:
            Disagreement level between 0 and 1
        """
        return 1.0 - self._calculate_agreement(signals)

    def calculate_entropy(self, signals: List[Signal]) -> float:
        """Calculate entropy of signal distribution.

        Higher entropy indicates more diversity/disagreement.

        Args:
            signals: List of signals to analyze

        Returns:
            Entropy value
        """
        try:
            if not signals:
                return 0.0

            # Count signal types
            signal_types = [s.signal_type for s in signals]
            counts = Counter(signal_types)

            # Calculate probabilities
            total = len(signals)
            probabilities = [count / total for count in counts.values()]

            # Calculate entropy
            entropy = -sum(p * np.log(p) for p in probabilities if p > 0)

            # Normalize by max possible entropy
            max_entropy = np.log(len(counts))

            if max_entropy > 0:
                return entropy / max_entropy

            return 0.0

        except Exception:
            logger.error("Calculation failed", exc_info=True)
            return 0.0

    def get_voting_summary(self, signals: List[Signal]) -> Dict[str, Any]:
        """Get a summary of the voting process.

        Args:
            signals: List of signals to analyze

        Returns:
            Dictionary with voting summary statistics
        """
        try:
            if not signals:
                return {
                    "total_signals": 0,
                    "agreement": 0.0,
                    "disagreement": 0.0,
                    "entropy": 0.0,
                    "signal_distribution": {},
                }

            signal_types = [s.signal_type for s in signals]
            counts = Counter(signal_types)

            return {
                "total_signals": len(signals),
                "agreement": self._calculate_agreement(signals),
                "disagreement": self.calculate_disagreement(signals),
                "entropy": self.calculate_entropy(signals),
                "signal_distribution": {k.value: v for k, v in counts.most_common()},
                "avg_confidence": float(np.mean([s.confidence for s in signals])),
                "min_confidence": float(min(s.confidence for s in signals)),
                "max_confidence": float(max(s.confidence for s in signals)),
            }

        except Exception:
            logger.error("Voting summary calculation failed", exc_info=True)
            return {
                "total_signals": len(signals) if signals else 0,
                "agreement": 0.0,
                "disagreement": 0.0,
                "entropy": 0.0,
                "signal_distribution": {},
            }
