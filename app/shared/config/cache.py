"""
Configuration Cache

Implements ConfigCache protocol with file-based cache invalidation.
Single responsibility: manage configuration caching.

TASK-24: SRP Compliance - Separate caching logic
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class FileBasedConfigCache:
    """
    File-based configuration cache with automatic invalidation.
    Invalidates cache when source file changes.
    """

    def __init__(self):
        self._cache: dict[Path, dict[str, Any]] = {}
        self._timestamps: dict[Path, float] = {}

    def get_cached(self, config_path: Path) -> Optional[dict[str, Any]]:
        """
        Get cached configuration if available and valid.

        Args:
            config_path: Path to configuration file

        Returns:
            Cached configuration if valid, None otherwise
        """
        if config_path not in self._cache:
            return None

        # Check if file has been modified
        if not config_path.exists():
            # File was deleted, invalidate cache
            self.invalidate(config_path)
            return None

        cached_time = self._timestamps.get(config_path, 0)
        file_mtime = os.path.getmtime(config_path)

        if file_mtime > cached_time:
            # File has been modified, invalidate cache
            logger.debug(f"Cache invalidated for {config_path} (file modified)")
            self.invalidate(config_path)
            return None

        logger.debug(f"Cache hit for {config_path}")
        return self._cache[config_path]

    def set_cached(self, config_path: Path, config: dict[str, Any]) -> None:
        """
        Cache configuration.

        Args:
            config_path: Path to configuration file
            config: Configuration dictionary to cache
        """
        self._cache[config_path] = config
        self._timestamps[config_path] = time.time()
        logger.debug(f"Cached configuration for {config_path}")

    def invalidate(self, config_path: Path) -> None:
        """
        Invalidate cached configuration.

        Args:
            config_path: Path to configuration file
        """
        self._cache.pop(config_path, None)
        self._timestamps.pop(config_path, None)
        logger.debug(f"Invalidated cache for {config_path}")

    def clear_all(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._timestamps.clear()
        logger.info("Cleared all cached configurations")

    def get_cache_size(self) -> int:
        """Get number of cached configurations."""
        return len(self._cache)
