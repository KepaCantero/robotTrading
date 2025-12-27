"""
TASK-SC-1 to SC-5: Signal Scoring and Cooldown Engine.

Implements comprehensive signal scoring system with cooldown periods,
compound scoring, priority ranking, and portfolio signal filtering.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from app.models.signal import Signal, SignalType

logger = logging.getLogger(__name__)


class SignalCooldownManager:
    """
    TASK-SC-1: Signal Cooldown Manager.

    Prevents over-trading by enforcing cooldown periods per symbol.
    """

    def __init__(self, default_cooldown_minutes: int = 10):
        """
        Initialize cooldown manager.

        Args:
            default_cooldown_minutes: Default cooldown period in minutes
        """
        self.default_cooldown_minutes = default_cooldown_minutes
        self.cooldowns: Dict[str, datetime] = {}  # symbol -> last_signal_time
        self.custom_cooldowns: Dict[str, int] = {}  # symbol -> custom_cooldown_minutes

    def set_cooldown(self, symbol: str, minutes: Optional[int] = None) -> None:
        """
        Set cooldown for a symbol.

        Args:
            symbol: Symbol to set cooldown for
            minutes: Cooldown duration in minutes (uses default if None)
        """
        cooldown_minutes = minutes if minutes is not None else self.default_cooldown_minutes
        self.cooldowns[symbol] = datetime.utcnow()
        if minutes is not None:
            self.custom_cooldowns[symbol] = cooldown_minutes
        logger.debug(f"Set cooldown for {symbol}: {cooldown_minutes} minutes")

    def is_in_cooldown(self, symbol: str) -> bool:
        """
        Check if symbol is in cooldown period.

        Args:
            symbol: Symbol to check

        Returns:
            True if in cooldown, False otherwise
        """
        if symbol not in self.cooldowns:
            return False

        last_signal_time = self.cooldowns[symbol]
        cooldown_minutes = self.custom_cooldowns.get(symbol, self.default_cooldown_minutes)
        cooldown_duration = timedelta(minutes=cooldown_minutes)
        elapsed = datetime.utcnow() - last_signal_time

        if elapsed < cooldown_duration:
            remaining = cooldown_duration - elapsed
            logger.debug(
                f"{symbol} in cooldown: {remaining.total_seconds() / 60:.1f} minutes remaining"
            )
            return True

        # Cooldown expired, remove it
        del self.cooldowns[symbol]
        if symbol in self.custom_cooldowns:
            del self.custom_cooldowns[symbol]
        return False

    def reset_cooldown(self, symbol: str) -> None:
        """Reset cooldown for a symbol."""
        if symbol in self.cooldowns:
            del self.cooldowns[symbol]
        if symbol in self.custom_cooldowns:
            del self.custom_cooldowns[symbol]


class SignalCompoundScoreCalculator:
    """
    TASK-SC-2: Signal Compound Score Calculator.

    Calculates compound score using weighted components:
    - confidence (30%)
    - volume_ratio (25%)
    - volatility (20%)
    - liquidity (15%)
    - timing (10%)
    """

    def __init__(self):
        self.weights = {
            "confidence": 0.30,
            "volume_ratio": 0.25,
            "volatility": 0.20,
            "liquidity": 0.15,
            "timing": 0.10,
        }

    def calculate_compound_score(
        self,
        signal: Signal,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate compound score for a signal.

        Args:
            signal: Trading signal
            metadata: Optional additional metadata

        Returns:
            Compound score (0-100)
        """
        # Extract components from signal and metadata
        confidence = signal.confidence / 100.0  # Normalize to 0-1
        liquidity = signal.liquidity_score / 100.0  # Normalize to 0-1

        # Extract volume ratio from metadata
        volume_ratio = self._extract_volume_ratio(signal, metadata)

        # Extract volatility from metadata
        volatility = self._extract_volatility(signal, metadata)

        # Extract timing from signal
        timing = self._calculate_timing_score(signal)

        # Calculate weighted average
        scores = {
            "confidence": confidence,
            "volume_ratio": volume_ratio,
            "volatility": volatility,
            "liquidity": liquidity,
            "timing": timing,
        }

        compound_score = sum(scores[k] * self.weights[k] for k in self.weights)

        # Scale to 0-100
        return round(compound_score * 100, 2)

    def _extract_volume_ratio(self, signal: Signal, metadata: Optional[Dict[str, Any]]) -> float:
        """Extract and normalize volume ratio from signal metadata."""
        if not metadata:
            return 0.5  # Neutral value if no data

        volume_ratio = metadata.get("volume_ratio", 1.0)
        # Normalize: 1.0+ is good, <1.0 is below average
        # Map to 0-1 scale: 1.0 => 0.5, 2.0 => 1.0, 0.5 => 0.0
        if volume_ratio >= 1.0:
            return min(1.0, 0.5 + (volume_ratio - 1.0) * 0.5)
        else:
            return max(0.0, 0.5 - (1.0 - volume_ratio))

    def _extract_volatility(self, signal: Signal, metadata: Optional[Dict[str, Any]]) -> float:
        """Extract and normalize volatility from signal metadata."""
        if not metadata:
            return 0.5  # Neutral value if no data

        volatility = metadata.get("volatility", 0.02)
        # Prefer moderate volatility (0.01-0.03)
        # Normalize to 0-1
        if 0.01 <= volatility <= 0.03:
            return 1.0
        elif volatility < 0.01:
            return max(0.0, volatility / 0.01)
        else:
            return max(0.0, 1.0 - (volatility - 0.03) * 10)

    def _calculate_timing_score(self, signal: Signal) -> float:
        """Calculate timing score based on signal recency."""
        if not signal.timestamp:
            return 0.5

        elapsed_minutes = (datetime.utcnow() - signal.timestamp).total_seconds() / 60

        # Fresh signals are better
        if elapsed_minutes < 5:
            return 1.0
        elif elapsed_minutes < 15:
            return 0.8
        elif elapsed_minutes < 30:
            return 0.6
        elif elapsed_minutes < 60:
            return 0.4
        else:
            return 0.2


class SignalPriorityRanker:
    """
    TASK-SC-3: Signal Priority Ranker.

    Ranks signals by priority based on compound score:
    - >80 = high priority
    - 50-80 = medium priority
    - <50 = low priority
    """

    def __init__(
        self,
        high_threshold: float = 80.0,
        medium_threshold: float = 50.0,
    ):
        """
        Initialize priority ranker.

        Args:
            high_threshold: Score threshold for high priority
            medium_threshold: Score threshold for medium priority
        """
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def get_priority(self, compound_score: float) -> str:
        """
        Get priority level for a compound score.

        Args:
            compound_score: Compound score (0-100)

        Returns:
            Priority level: "high", "medium", or "low"
        """
        if compound_score >= self.high_threshold:
            return "high"
        elif compound_score >= self.medium_threshold:
            return "medium"
        else:
            return "low"

    def rank_signals(self, signals: List[Signal]) -> List[Signal]:
        """
        Rank signals by priority.

        Args:
            signals: List of signals to rank

        Returns:
            Signals sorted by priority (high -> medium -> low)
        """
        priority_order = {"high": 0, "medium": 1, "low": 2}

        def priority_key(signal: Signal) -> tuple:
            # Extract compound score from signal metadata
            compound_score = signal.metadata.get("compound_score", 0.0)
            priority = self.get_priority(compound_score)
            return (priority_order[priority], -compound_score)  # Negate for descending

        return sorted(signals, key=priority_key)


class PortfolioSignalFilter:
    """
    TASK-SC-4: Portfolio Signal Filter.

    Filters conflicting signals by strategy and symbol to prevent
    contradictory positions in the portfolio.
    """

    def __init__(self):
        self.active_positions: Set[str] = set()  # Set of symbols with active positions
        self.recent_signals: Dict[str, List[Signal]] = defaultdict(list)

    def filter_signals(
        self,
        signals: List[Signal],
        max_signals_per_symbol: int = 1,
        filter_conflicts: bool = True,
    ) -> List[Signal]:
        """
        Filter signals to avoid conflicts.

        Args:
            signals: List of signals to filter
            max_signals_per_symbol: Maximum signals per symbol
            filter_conflicts: Whether to filter conflicting signals

        Returns:
            Filtered list of signals
        """
        if not filter_conflicts:
            return signals

        filtered = []
        symbol_signals: Dict[str, List[Signal]] = defaultdict(list)

        # Group signals by symbol
        for signal in signals:
            symbol_signals[signal.symbol].append(signal)

        # Filter each symbol
        for symbol, symbol_signal_list in symbol_signals.items():
            # Check for conflicts with active positions
            valid_signals = []
            for signal in symbol_signal_list:
                if signal.signal_type == SignalType.SELL and symbol not in self.active_positions:
                    # SELL signal but no position - skip
                    logger.debug(f"Filtered SELL signal for {symbol}: no active position")
                    continue
                valid_signals.append(signal)

            # Limit signals per symbol
            if len(valid_signals) > max_signals_per_symbol:
                # Sort by compound score and take best
                valid_signals.sort(
                    key=lambda s: s.metadata.get("compound_score", 0.0), reverse=True
                )
                valid_signals = valid_signals[:max_signals_per_symbol]

            filtered.extend(valid_signals)

        return filtered

    def add_position(self, symbol: str) -> None:
        """Track active position."""
        self.active_positions.add(symbol)

    def remove_position(self, symbol: str) -> None:
        """Remove active position."""
        self.active_positions.discard(symbol)


class SignalScoringEngine:
    """
    TASK-SC-1 to SC-5: Complete Signal Scoring Engine.

    Integrates all signal scoring components:
    - Cooldown management
    - Compound score calculation
    - Priority ranking
    - Portfolio signal filtering
    """

    def __init__(self, default_cooldown_minutes: int = 10):
        """
        Initialize signal scoring engine.

        Args:
            default_cooldown_minutes: Default cooldown period in minutes
        """
        self.cooldown_manager = SignalCooldownManager(default_cooldown_minutes)
        self.score_calculator = SignalCompoundScoreCalculator()
        self.priority_ranker = SignalPriorityRanker()
        self.portfolio_filter = PortfolioSignalFilter()

    def process_signals(self, signals: List[Signal], apply_cooldown: bool = True) -> List[Signal]:
        """
        Process signals through the complete scoring pipeline.

        Args:
            signals: Raw signals from strategies
            apply_cooldown: Whether to apply cooldown (False for backtesting)

        Returns:
            Processed and filtered signals
        """
        if not signals:
            return []

        processed_signals = []

        for signal in signals:
            # Check cooldown (skip in backtesting mode)
            if apply_cooldown and self.cooldown_manager.is_in_cooldown(signal.symbol):
                logger.debug(f"Signal suppressed for {signal.symbol}: in cooldown")
                continue

            # Calculate compound score
            compound_score = self.score_calculator.calculate_compound_score(signal)

            # Add score to metadata
            signal.metadata["compound_score"] = compound_score

            # Get priority
            priority = self.priority_ranker.get_priority(compound_score)
            signal.metadata["priority"] = priority

            # Set cooldown after processing (only if enabled)
            if apply_cooldown:
                self.cooldown_manager.set_cooldown(signal.symbol)

            processed_signals.append(signal)

        # Filter portfolio conflicts (only if not backtesting)
        if apply_cooldown:
            filtered_signals = self.portfolio_filter.filter_signals(processed_signals)
        else:
            filtered_signals = processed_signals

        # Rank by priority
        ranked_signals = self.priority_ranker.rank_signals(filtered_signals)

        logger.info(
            f"Processed {len(signals)} signals -> {len(filtered_signals)} filtered -> {len(ranked_signals)} ranked"
        )

        return ranked_signals

    def get_scoring_stats(self) -> Dict[str, Any]:
        """Get scoring statistics."""
        return {
            "active_cooldowns": len(self.cooldown_manager.cooldowns),
            "active_positions": len(self.portfolio_filter.active_positions),
        }


# Global engine instance
_signal_scoring_engine: Optional[SignalScoringEngine] = None


def get_signal_scoring_engine(cooldown_minutes: int = 10) -> SignalScoringEngine:
    """Get global signal scoring engine instance."""
    global _signal_scoring_engine
    if _signal_scoring_engine is None:

    return _signal_scoring_engine
