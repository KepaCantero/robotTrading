"""
Storage backend for momentum analysis.

SOLID Principles:
- SRP: Only handles storage operations
- OCP: Extensible through new storage implementations
- LSP: Implements StorageBackend protocol
- ISP: Focused on storage operations
- DIP: High-level modules depend on this abstraction
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domain.models.momentum import MomentumAnalysis, MomentumStrategy

logger = logging.getLogger(__name__)


class InMemoryStorageBackend:
    """
    In-memory storage backend for momentum analysis.

    Single Responsibility:
    - Store and retrieve momentum analyses
    - Store and retrieve momentum strategies

    Open/Closed:
    - Open for extension (can be replaced with database backend)
    - Closed for modification (core storage logic stable)

    Liskov Substitution:
    - Implements StorageBackend protocol
    - Substitutable with any StorageBackend implementation
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        self.analyses: dict[str, MomentumAnalysis] = {}
        self.strategies: dict[str, MomentumStrategy] = {}

    async def save_analysis(self, analysis_id: str, analysis: MomentumAnalysis) -> None:
        """
        Save momentum analysis to storage.

        Args:
            analysis_id: Unique identifier for the analysis
            analysis: Analysis to save
        """
        self.analyses[analysis_id] = analysis
        logger.debug(f"Saved analysis: {analysis_id}")

    async def get_analysis(self, analysis_id: str) -> Optional[MomentumAnalysis]:
        """
        Get momentum analysis by ID.

        Args:
            analysis_id: Unique identifier for the analysis

        Returns:
            Analysis if found, None otherwise
        """
        return self.analyses.get(analysis_id)

    async def get_all_analyses(self) -> list[MomentumAnalysis]:
        """
        Get all momentum analyses.

        Returns:
            List of all analyses
        """
        return list(self.analyses.values())

    async def delete_analysis(self, analysis_id: str) -> bool:
        """
        Delete momentum analysis.

        Args:
            analysis_id: Unique identifier for the analysis

        Returns:
            True if deleted, False if not found
        """
        if analysis_id in self.analyses:
            del self.analyses[analysis_id]
            logger.debug(f"Deleted analysis: {analysis_id}")
            return True
        return False

    async def save_strategy(self, strategy: MomentumStrategy) -> None:
        """
        Save momentum strategy to storage.

        Args:
            strategy: Strategy to save
        """
        self.strategies[strategy.name] = strategy
        logger.debug(f"Saved strategy: {strategy.name}")

    async def load_strategies(self) -> dict[str, MomentumStrategy]:
        """
        Load all momentum strategies.

        Returns:
            Dictionary of all strategies
        """
        return self.strategies.copy()
