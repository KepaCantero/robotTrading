"""
Fallback Tracker Service

Thread-safe tracking of fallback metrics when configuration loaders
or strategy mappers fail and the system falls back to default values.

Responsibilities:
- Thread-safe fallback counter incrementing
- Fallback metrics retrieval
- Fallback summary logging with interpretation
"""

from __future__ import annotations

import logging
import threading
from typing import Dict

logger = logging.getLogger(__name__)


class FallbackTracker:
    """
    Thread-safe tracker for fallback metrics.

    Tracks how often the system falls back to default behaviors when
    configuration loaders or strategy mappers fail. This helps identify
    configuration issues that need attention.

    Attributes:
        _profile_config_loader_fallback_count: Times ProfileConfigLoader failed/None
        _profile_strategy_mapper_fallback_count: Times ProfileStrategyMapper failed/None
        _config_key_mismatch_count: Times config keys didn't exist
        _fallback_lock: Thread lock for thread-safe operations
    """

    def __init__(self) -> None:
        """Initialize fallback tracker with zero counts."""
        self._profile_config_loader_fallback_count = 0
        self._profile_strategy_mapper_fallback_count = 0
        self._config_key_mismatch_count = 0
        self._fallback_lock = threading.Lock()

    def increment_fallback_counter(self, fallback_type: str) -> None:
        """
        Thread-safe increment of fallback counter.

        Args:
            fallback_type: Type of fallback ("profile_config_loader",
                          "profile_strategy_mapper", "config_key_mismatch")

        Example:
            >>> tracker = FallbackTracker()
            >>> tracker.increment_fallback_counter("profile_config_loader")
        """
        with self._fallback_lock:
            if fallback_type == "profile_config_loader":
                self._profile_config_loader_fallback_count += 1
            elif fallback_type == "profile_strategy_mapper":
                self._profile_strategy_mapper_fallback_count += 1
            elif fallback_type == "config_key_mismatch":
                self._config_key_mismatch_count += 1
            else:
                logger.warning(f"Unknown fallback type: {fallback_type}")

    def get_fallback_metrics(self) -> Dict[str, int]:
        """
        Get current fallback metrics (thread-safe).

        Returns:
            Dictionary with fallback counts:
            - profile_config_loader_fallback_count: Times ProfileConfigLoader failed/None
            - profile_strategy_mapper_fallback_count: Times ProfileStrategyMapper failed/None
            - config_key_mismatch_count: Times config keys didn't exist

        Example:
            >>> tracker = FallbackTracker()
            >>> metrics = tracker.get_fallback_metrics()
            >>> print(f"Config loader fallbacks: {metrics['profile_config_loader_fallback_count']}")
        """
        with self._fallback_lock:
            return {
                "profile_config_loader_fallback_count": self._profile_config_loader_fallback_count,
                "profile_strategy_mapper_fallback_count": self._profile_strategy_mapper_fallback_count,
                "config_key_mismatch_count": self._config_key_mismatch_count,
            }

    def log_fallback_summary(self) -> None:
        """
        Log a summary of all fallback metrics at INFO level.

        This method provides a comprehensive overview of how often the system
        fell back to default behaviors during backtesting.

        Example:
            >>> tracker = FallbackTracker()
            >>> tracker.increment_fallback_counter("profile_config_loader")
            >>> tracker.log_fallback_summary()
            INFO - Fallback Metrics Summary:
            INFO -   ProfileConfigLoader fallbacks: 1
            INFO -   ProfileStrategyMapper fallbacks: 0
            INFO -   Config key mismatches: 0
            INFO - Total fallbacks: 1
        """
        metrics = self.get_fallback_metrics()
        total_fallbacks = sum(metrics.values())
        logger.info("=" * 60)
        logger.info("Fallback Metrics Summary:")
        logger.info(
            f"  ProfileConfigLoader fallbacks: {metrics['profile_config_loader_fallback_count']}"
        )
        logger.info(
            f"  ProfileStrategyMapper fallbacks: {metrics['profile_strategy_mapper_fallback_count']}"
        )
        logger.info(f"  Config key mismatches: {metrics['config_key_mismatch_count']}")
        logger.info(f"Total fallbacks: {total_fallbacks}")
        logger.info("=" * 60)

        # Provide interpretation
        if total_fallbacks == 0:
            logger.info("No fallbacks occurred - all components loaded successfully")
        elif total_fallbacks < 5:
            logger.info(f"Low fallback count ({total_fallbacks}) - minimal impact on backtesting")
        elif total_fallbacks < 20:
            logger.warning(
                f"Moderate fallback count ({total_fallbacks}) - some configurations may need review"
            )
        else:
            logger.error(
                f"High fallback count ({total_fallbacks}) - review configuration files immediately"
            )
