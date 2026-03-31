"""
Signal Integrator - Multi-source trading signal integration.

Combines trading signals from multiple sources (RL, momentum, mean reversion)
using confidence-weighted voting and produces a unified signal set.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from .models import SignalSet

logger = logging.getLogger(__name__)


class SignalIntegrator:
    """
    Integrates trading signals from multiple sources.

    Features:
    - Confidence-weighted voting
    - Source-specific signal aggregation
    - Conflict resolution
    - Signal quality assessment
    """

    def __init__(
        self,
        rl_weight: float = 0.4,
        momentum_weight: float = 0.35,
        mean_reversion_weight: float = 0.25,
        min_confidence_threshold: float = 0.3,
        consensus_threshold: float = 0.6,
    ):
        """
        Initialize signal integrator.

        Args:
            rl_weight: Weight for RL signals in voting (default: 0.4)
            momentum_weight: Weight for momentum signals (default: 0.35)
            mean_reversion_weight: Weight for mean reversion signals (default: 0.25)
            min_confidence_threshold: Minimum confidence to include signal (default: 0.3)
            consensus_threshold: Minimum agreement for consensus signal (default: 0.6)
        """
        self.rl_weight = rl_weight
        self.momentum_weight = momentum_weight
        self.mean_reversion_weight = mean_reversion_weight
        self.min_confidence_threshold = min_confidence_threshold
        self.consensus_threshold = consensus_threshold

        # Normalize weights
        total_weight = rl_weight + momentum_weight + mean_reversion_weight
        self.rl_weight /= total_weight
        self.momentum_weight /= total_weight
        self.mean_reversion_weight /= total_weight

        logger.info(
            f"✅ SignalIntegrator initialized "
            f"(RL={self.rl_weight:.2f}, Mom={self.momentum_weight:.2f}, MR={self.mean_reversion_weight:.2f})"
        )

    def combine_signals(
        self,
        rl_signals: Optional[dict[str, tuple[str, float]]] = None,
        momentum_signals: Optional[dict[str, tuple[str, float]]] = None,
        mean_reversion_signals: Optional[dict[str, tuple[str, float]]] = None,
    ) -> SignalSet:
        """
        Combine signals from multiple sources using confidence-weighted voting.

        Args:
            rl_signals: Dict mapping symbol to (action, confidence) tuple from RL
            momentum_signals: Dict mapping symbol to (action, confidence) tuple from momentum
            mean_reversion_signals: Dict mapping symbol to (action, confidence) tuple from mean reversion

        Returns:
            SignalSet with combined signals
        """
        rl_signals = rl_signals or {}
        momentum_signals = momentum_signals or {}
        mean_reversion_signals = mean_reversion_signals or {}

        signal_set = SignalSet()

        # Get all unique symbols
        all_symbols = set(
            list(rl_signals.keys())
            + list(momentum_signals.keys())
            + list(mean_reversion_signals.keys())
        )

        logger.info(f"🔄 Combining signals for {len(all_symbols)} symbols")

        for symbol in all_symbols:
            # Get signals from each source
            rl_action, rl_conf = rl_signals.get(symbol, ("HOLD", 0.0))
            mom_action, mom_conf = momentum_signals.get(symbol, ("HOLD", 0.0))
            mr_action, mr_conf = mean_reversion_signals.get(symbol, ("HOLD", 0.0))

            # Store individual signals
            if symbol in rl_signals:
                signal_set.add_signal(symbol, rl_action, "rl", rl_conf)
            if symbol in momentum_signals:
                signal_set.add_signal(symbol, mom_action, "momentum", mom_conf)
            if symbol in mean_reversion_signals:
                signal_set.add_signal(symbol, mr_action, "mean_reversion", mr_conf)

            # Weighted voting
            combined_action, combined_conf = self._weighted_vote(
                (rl_action, rl_conf, self.rl_weight),
                (mom_action, mom_conf, self.momentum_weight),
                (mr_action, mr_conf, self.mean_reversion_weight),
            )

            # Only update combined signal if confidence exceeds threshold
            if combined_conf >= self.min_confidence_threshold:
                # Update the primary signal (overwrites previous add_signal calls)
                signal_set.signals[symbol] = combined_action
                signal_set.confidence_scores[symbol] = combined_conf

        logger.info(
            f"✅ Signal combination complete: "
            f"{signal_set.buy_count} BUY, {signal_set.sell_count} SELL, {signal_set.hold_count} HOLD"
        )

        return signal_set

    def _weighted_vote(
        self,
        *signal_tuples: tuple[str, float, float],
    ) -> tuple[str, float]:
        """
        Perform weighted voting on signals.

        Args:
            *signal_tuples: Variable number of (action, confidence, weight) tuples

        Returns:
            Tuple of (combined_action, combined_confidence)
        """
        # Convert actions to numeric values
        action_values = {"BUY": 1, "HOLD": 0, "SELL": -1}

        # Calculate weighted score
        weighted_sum = 0.0
        total_weight = 0.0
        total_conf_weighted = 0.0

        for action, confidence, weight in signal_tuples:
            if confidence < self.min_confidence_threshold:
                # Skip low-confidence signals
                continue

            action_value = action_values.get(action, 0)
            weighted_sum += action_value * confidence * weight
            total_weight += confidence * weight
            total_conf_weighted += confidence * weight

        # Determine combined action
        if total_weight == 0:
            return "HOLD", 0.0

        weighted_avg = weighted_sum / total_weight
        combined_conf = total_conf_weighted / sum(
            w for _, _, w in signal_tuples
        )  # Avg confidence weighted by source weights

        # Convert back to action
        if weighted_avg > 0.3:
            combined_action = "BUY"
        elif weighted_avg < -0.3:
            combined_action = "SELL"
        else:
            combined_action = "HOLD"

        return combined_action, combined_conf

    def check_consensus(
        self,
        signal_set: SignalSet,
        symbol: str,
    ) -> tuple[bool, str]:
        """
        Check if there's consensus among signal sources for a symbol.

        Args:
            signal_set: SignalSet to check
            symbol: Symbol to check consensus for

        Returns:
            Tuple of (has_consensus, dominant_action)
        """
        actions = []

        if symbol in signal_set.rl_signals:
            actions.append(signal_set.rl_signals[symbol])
        if symbol in signal_set.momentum_signals:
            actions.append(signal_set.momentum_signals[symbol])
        if symbol in signal_set.mean_reversion_signals:
            actions.append(signal_set.mean_reversion_signals[symbol])

        if not actions:
            return False, "HOLD"

        # Count action frequencies
        from collections import Counter

        action_counts = Counter(actions)
        most_common = action_counts.most_common(1)[0]
        dominant_action, count = most_common

        # Check if consensus threshold met
        consensus_ratio = count / len(actions)
        has_consensus = consensus_ratio >= self.consensus_threshold

        return has_consensus, dominant_action

    def get_signal_quality_score(
        self,
        signal_set: SignalSet,
        symbol: str,
    ) -> float:
        """
        Calculate overall quality score for a symbol's signal.

        Higher scores indicate more reliable signals.

        Args:
            signal_set: SignalSet containing the signal
            symbol: Symbol to score

        Returns:
            Quality score between 0 and 1
        """
        confidence = signal_set.confidence_scores.get(symbol, 0.0)

        # Check consensus
        has_consensus, _ = self.check_consensus(signal_set, symbol)

        # Check if multiple sources agree
        source_count = 0
        if symbol in signal_set.rl_signals and signal_set.rl_signals[symbol] != "HOLD":
            source_count += 1
        if symbol in signal_set.momentum_signals and signal_set.momentum_signals[symbol] != "HOLD":
            source_count += 1
        if (
            symbol in signal_set.mean_reversion_signals
            and signal_set.mean_reversion_signals[symbol] != "HOLD"
        ):
            source_count += 1

        # Calculate quality score
        consensus_bonus = 0.3 if has_consensus else 0.0
        source_bonus = min(0.2 * source_count, 0.4)

        quality_score = min(confidence + consensus_bonus + source_bonus, 1.0)

        return float(quality_score)

    def filter_by_quality(
        self,
        signal_set: SignalSet,
        min_quality: float = 0.5,
    ) -> SignalSet:
        """
        Filter signals by quality score.

        Args:
            signal_set: SignalSet to filter
            min_quality: Minimum quality score (default: 0.5)

        Returns:
            New SignalSet with only high-quality signals
        """
        filtered_set = SignalSet()

        for symbol, action in signal_set.signals.items():
            quality = self.get_signal_quality_score(signal_set, symbol)

            if quality >= min_quality:
                filtered_set.signals[symbol] = action
                filtered_set.confidence_scores[symbol] = signal_set.confidence_scores.get(
                    symbol, 0.0
                )

                # Copy source signals
                if symbol in signal_set.rl_signals:
                    filtered_set.rl_signals[symbol] = signal_set.rl_signals[symbol]
                if symbol in signal_set.momentum_signals:
                    filtered_set.momentum_signals[symbol] = signal_set.momentum_signals[symbol]
                if symbol in signal_set.mean_reversion_signals:
                    filtered_set.mean_reversion_signals[symbol] = signal_set.mean_reversion_signals[
                        symbol
                    ]

                # Update counts
                if action == "BUY":
                    filtered_set.buy_count += 1
                elif action == "SELL":
                    filtered_set.sell_count += 1
                else:
                    filtered_set.hold_count += 1

        logger.info(
            f"🔍 Filtered {len(signal_set.signals)} → {len(filtered_set.signals)} signals "
            f"(min_quality={min_quality:.2f})"
        )

        return filtered_set

    def generate_signal_report(self, signal_set: SignalSet) -> dict[str, any]:
        """
        Generate comprehensive report on signal set.

        Args:
            signal_set: SignalSet to analyze

        Returns:
            Dict with signal statistics and insights
        """
        summary = signal_set.get_summary()

        # Calculate additional metrics
        high_confidence_signals = {
            s: c for s, c in signal_set.confidence_scores.items() if c >= 0.7
        }

        consensus_symbols = []
        for symbol in signal_set.signals:
            has_consensus, action = self.check_consensus(signal_set, symbol)
            if has_consensus:
                consensus_symbols.append((symbol, action))

        # Quality distribution
        quality_scores = {
            symbol: self.get_signal_quality_score(signal_set, symbol)
            for symbol in signal_set.signals
        }

        avg_quality = np.mean(list(quality_scores.values())) if quality_scores else 0.0

        report = {
            "summary": summary,
            "high_confidence_count": len(high_confidence_signals),
            "high_confidence_symbols": list(high_confidence_signals.keys()),
            "consensus_count": len(consensus_symbols),
            "consensus_symbols": consensus_symbols[:10],  # Top 10
            "avg_quality_score": float(avg_quality),
            "quality_distribution": {
                "excellent": sum(1 for q in quality_scores.values() if q >= 0.8),
                "good": sum(1 for q in quality_scores.values() if 0.6 <= q < 0.8),
                "fair": sum(1 for q in quality_scores.values() if 0.4 <= q < 0.6),
                "poor": sum(1 for q in quality_scores.values() if q < 0.4),
            },
        }

        return report
