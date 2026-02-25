"""
Backward compatibility shim for momentum_analysis.py.

This file maintains backward compatibility with the original monolithic
momentum_analysis.py while delegating to the new SOLID-compliant module.

DEPRECATED: Import from app.services.momentum instead.
"""

import logging
from typing import Dict, List, Optional

from app.domain.models.momentum import (
    MomentumAnalysis,
    MomentumFilter,
    MomentumSignal,
    MomentumStrategy,
    Timeframe,
)
from app.services.momentum import get_momentum_analysis_service
from app.services.momentum.indicators.calculator import TechnicalIndicatorCalculator

logger = logging.getLogger(__name__)

# Export main classes for backward compatibility
__all__ = [
    "TechnicalIndicatorCalculator",
    "MomentumAnalysisService",
    "get_momentum_analysis_service",
]


class MomentumAnalysisService:
    """
    Backward compatibility wrapper for the new SOLID-compliant service.

    DEPRECATED: Use app.services.momentum.get_momentum_analysis_service() instead.

    This wrapper maintains the original API while delegating to the new
    modular architecture following SOLID principles.
    """

    def __init__(self):
        """Initialize backward compatibility wrapper."""
        self._service = get_momentum_analysis_service()
        self.asset_service = None  # Removed in SOLID refactor
        self.strategies: Dict[str, MomentumStrategy] = {}
        self.analyses: Dict[str, MomentumAnalysis] = {}
        self.indicator_calculator = TechnicalIndicatorCalculator()

        # Initialize default strategies for backward compatibility
        self._initialize_default_strategies()

    def _initialize_default_strategies(self):
        """Initialize default strategies (backward compatibility)."""
        # Sync with new service's strategies
        new_strategies = self._service.strategy_manager.get_all_strategies()
        for name, strategy in new_strategies.items():
            self.strategies[name] = strategy

    async def analyze_asset_momentum(
        self, symbol: str, timeframe: Timeframe = Timeframe.DAILY
    ) -> MomentumAnalysis:
        """Analyze momentum for a specific asset."""
        analysis = await self._service.analyze_asset_momentum(symbol, timeframe)
        # Sync to local dict for backward compatibility
        self.analyses[f"{symbol}_{timeframe.value}"] = analysis
        return analysis

    async def get_momentum_signals(
        self, filter_criteria: Optional[MomentumFilter] = None
    ) -> List[MomentumSignal]:
        """Get momentum signals based on filter criteria."""
        return await self._service.get_momentum_signals(filter_criteria)

    async def get_strategy_signals(self, strategy_name: str) -> List[MomentumSignal]:
        """Get signals for a specific strategy."""
        return await self._service.get_strategy_signals(strategy_name)

    async def get_top_momentum_assets(self, limit: int = 10) -> List[Dict]:
        """Get top momentum assets."""
        return await self._service.get_top_momentum_assets(limit)

    async def create_strategy(self, strategy: MomentumStrategy) -> MomentumStrategy:
        """Create a new momentum strategy."""
        new_strategy = await self._service.create_strategy(strategy)
        # Sync to local dict for backward compatibility
        self.strategies[strategy.name] = new_strategy
        return new_strategy

    async def get_strategy(self, strategy_name: str) -> Optional[MomentumStrategy]:
        """Get a momentum strategy by name."""
        return await self._service.get_strategy(strategy_name)

    async def update_strategy(
        self, strategy_name: str, updated_fields: Dict
    ) -> Optional[MomentumStrategy]:
        """Update a momentum strategy."""
        updated_strategy = await self._service.update_strategy(strategy_name, updated_fields)
        # Sync to local dict for backward compatibility
        if updated_strategy:
            self.strategies[strategy_name] = updated_strategy
        return updated_strategy

    async def delete_strategy(self, strategy_name: str) -> bool:
        """Delete a momentum strategy."""
        result = await self._service.delete_strategy(strategy_name)
        # Sync to local dict for backward compatibility
        if result and strategy_name in self.strategies:
            del self.strategies[strategy_name]
        return result

    async def get_analyses(self) -> List[MomentumAnalysis]:
        """Get all momentum analyses."""
        return await self._service.get_analyses()

    async def get_analysis(self, analysis_id: str) -> Optional[MomentumAnalysis]:
        """Get a momentum analysis by ID."""
        return await self._service.get_analysis(analysis_id)

    async def delete_analysis(self, analysis_id: str) -> bool:
        """Delete a momentum analysis."""
        result = await self._service.delete_analysis(analysis_id)
        # Sync to local dict for backward compatibility
        if result and analysis_id in self.analyses:
            del self.analyses[analysis_id]
        return result


# Maintain global function for backward compatibility
def get_momentum_analysis_service_legacy() -> MomentumAnalysisService:
    """
    Get global momentum analysis service instance (legacy).

    DEPRECATED: Use app.services.momentum.get_momentum_analysis_service() instead.
    """
    logger.warning(
        "get_momentum_analysis_service_legacy() is deprecated. "
        "Use app.services.momentum.get_momentum_analysis_service() instead."
    )
    return MomentumAnalysisService()
