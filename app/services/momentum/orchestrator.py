"""
Momentum analysis orchestrator.

SOLID Principles:
- SRP: Only orchestrates momentum analysis workflow
- OCP: Extensible through new component implementations
- LSP: All components are substitutable via protocols
- ISP: Focused on orchestration operations
- DIP: Depends on protocol abstractions, not concrete implementations
"""

import logging
from typing import Optional

from app.domain.models.momentum import (
    MomentumAnalysis,
    MomentumFilter,
    MomentumSignal,
    MomentumStrategy,
    Timeframe,
)
from app.services.momentum.analyzer import MomentumAnalyzer
from app.services.momentum.data_provider import MockPriceDataProvider
from app.services.momentum.indicators.calculator import TechnicalIndicatorCalculator
from app.services.momentum.protocols import (
    IndicatorCalculator,
    PriceDataProvider,
)
from app.services.momentum.protocols import (
    MomentumAnalyzer as MomentumAnalyzerProtocol,
)
from app.services.momentum.protocols import (
    SignalGenerator as SignalGeneratorProtocol,
)
from app.services.momentum.protocols import (
    StrategyManager as StrategyManagerProtocol,
)
from app.services.momentum.signal_generator import SignalGenerator
from app.services.momentum.storage import InMemoryStorageBackend
from app.services.momentum.strategy_manager import StrategyManager

logger = logging.getLogger(__name__)


class MomentumAnalysisService:
    """
    Orchestrator for momentum analysis workflow.

    Single Responsibility:
    - Orchestrate the momentum analysis workflow
    - Coordinate between analyzer, signal generator, and strategy manager
    - Provide unified interface for momentum analysis

    Dependency Inversion:
    - Depends on protocol abstractions
    - Uses dependency injection for all components
    """

    def __init__(
        self,
        indicator_calculator: IndicatorCalculator,
        price_data_provider: PriceDataProvider,
        analyzer: MomentumAnalyzerProtocol,
        signal_generator: SignalGeneratorProtocol,
        strategy_manager: StrategyManagerProtocol,
    ) -> None:
        """
        Initialize orchestrator with all required components.

        Args:
            indicator_calculator: Calculator for technical indicators
            price_data_provider: Provider for price data
            analyzer: Core momentum analysis logic
            signal_generator: Signal generation logic
            strategy_manager: Strategy lifecycle management
        """
        self.indicator_calculator = indicator_calculator
        self.price_data_provider = price_data_provider
        self.analyzer = analyzer
        self.signal_generator = signal_generator
        self.strategy_manager = strategy_manager
        self.analyses: dict[str, MomentumAnalysis] = {}

    async def analyze_asset_momentum(
        self, symbol: str, timeframe: Timeframe = Timeframe.DAILY
    ) -> MomentumAnalysis:
        """
        Analyze momentum for a specific asset.

        This method orchestrates the complete workflow:
        1. Get price data
        2. Calculate indicators
        3. Generate signals
        4. Analyze momentum
        5. Store results

        Args:
            symbol: Asset symbol to analyze
            timeframe: Analysis timeframe (default DAILY)

        Returns:
            Complete momentum analysis
        """
        # Get price data
        price_data = await self.price_data_provider.get_price_data(symbol, timeframe)

        # Calculate indicators
        indicators = self.indicator_calculator.calculate_all_indicators(
            symbol,
            price_data["prices"],
            price_data["highs"],
            price_data["lows"],
            price_data["volumes"],
        )

        # Generate signals
        signals = await self.signal_generator.generate_signals(symbol, indicators, timeframe)

        # Create analysis with signals
        from app.domain.models.momentum import MomentumAnalysis

        overall_momentum = self.analyzer.calculate_overall_momentum(signals)
        trend_direction = self.analyzer.determine_trend_direction(indicators)
        risk_level = self.analyzer.assess_risk_level(indicators, signals)
        volatility_level = self.analyzer.assess_volatility_level(indicators)

        analysis = MomentumAnalysis(
            symbol=symbol,
            timeframe=timeframe,
            indicators=indicators,
            signals=signals,
            overall_momentum=overall_momentum,
            trend_direction=trend_direction,
            signal_count=len(signals),
            risk_level=risk_level,
            volatility_level=volatility_level,
        )

        # Store analysis
        analysis_id = f"{symbol}_{timeframe.value}"
        self.analyses[analysis_id] = analysis

        return analysis

    async def get_momentum_signals(
        self, filter_criteria: Optional[MomentumFilter] = None
    ) -> list[MomentumSignal]:
        """
        Get momentum signals based on filter criteria.

        Args:
            filter_criteria: Optional filter criteria

        Returns:
            Filtered list of momentum signals
        """
        all_signals = []

        for analysis in self.analyses.values():
            signals = analysis.get_active_signals()
            if filter_criteria:
                signals = [s for s in signals if filter_criteria.matches(s)]
            all_signals.extend(signals)

        all_signals.sort(key=lambda x: x.momentum_score, reverse=True)
        return all_signals

    async def get_strategy_signals(self, strategy_name: str) -> list[MomentumSignal]:
        """
        Get signals for a specific strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            List of signals for the strategy
        """
        all_signals = await self.get_momentum_signals()
        return await self.strategy_manager.get_strategy_signals(strategy_name, all_signals)

    async def get_top_momentum_assets(self, limit: int = 10) -> list[dict[str, any]]:
        """
        Get top momentum assets.

        Args:
            limit: Maximum number of assets to return (default 10)

        Returns:
            List of top momentum assets
        """
        all_signals = await self.get_momentum_signals()
        return await self.strategy_manager.get_top_momentum_assets(all_signals, limit)

    async def create_strategy(self, strategy: MomentumStrategy) -> MomentumStrategy:
        """
        Create a new momentum strategy.

        Args:
            strategy: Strategy to create

        Returns:
            Created strategy
        """
        return await self.strategy_manager.create_strategy(strategy)

    async def get_strategy(self, strategy_name: str) -> Optional[MomentumStrategy]:
        """
        Get a momentum strategy by name.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Strategy if found, None otherwise
        """
        return await self.strategy_manager.get_strategy(strategy_name)

    async def update_strategy(
        self, strategy_name: str, updated_fields: dict[str, any]
    ) -> Optional[MomentumStrategy]:
        """
        Update a momentum strategy.

        Args:
            strategy_name: Name of the strategy to update
            updated_fields: Dictionary of fields to update

        Returns:
            Updated strategy if found, None otherwise
        """
        return await self.strategy_manager.update_strategy(strategy_name, updated_fields)

    async def delete_strategy(self, strategy_name: str) -> bool:
        """
        Delete a momentum strategy.

        Args:
            strategy_name: Name of the strategy to delete

        Returns:
            True if deleted, False if not found
        """
        return await self.strategy_manager.delete_strategy(strategy_name)

    async def get_analyses(self) -> list[MomentumAnalysis]:
        """
        Get all momentum analyses.

        Returns:
            List of all analyses
        """
        return list(self.analyses.values())

    async def get_analysis(self, analysis_id: str) -> Optional[MomentumAnalysis]:
        """
        Get a momentum analysis by ID.

        Args:
            analysis_id: Unique identifier for the analysis

        Returns:
            Analysis if found, None otherwise
        """
        return self.analyses.get(analysis_id)

    async def delete_analysis(self, analysis_id: str) -> bool:
        """
        Delete a momentum analysis.

        Args:
            analysis_id: Unique identifier for the analysis

        Returns:
            True if deleted, False if not found
        """
        if analysis_id in self.analyses:
            del self.analyses[analysis_id]
            return True
        return False


# Global service instance
_momentum_service: Optional[MomentumAnalysisService] = None


def get_momentum_analysis_service() -> MomentumAnalysisService:
    """
    Get global momentum analysis service instance.

    This function implements the Service Locator pattern with dependency injection.
    All components are injected following SOLID principles.

    Returns:
        Global MomentumAnalysisService instance
    """
    global _momentum_service
    if _momentum_service is None:
        # Initialize components with dependency injection
        indicator_calculator = TechnicalIndicatorCalculator()
        price_data_provider = MockPriceDataProvider()
        storage_backend = InMemoryStorageBackend()

        # Analyzer depends on IndicatorCalculator and PriceDataProvider
        analyzer = MomentumAnalyzer(indicator_calculator, price_data_provider)

        # Signal generator is independent
        signal_generator = SignalGenerator()

        # Strategy manager depends on StorageBackend
        strategy_manager = StrategyManager(storage_backend)

        # Orchestrator depends on all components via protocols
        _momentum_service = MomentumAnalysisService(
            indicator_calculator=indicator_calculator,
            price_data_provider=price_data_provider,
            analyzer=analyzer,
            signal_generator=signal_generator,
            strategy_manager=strategy_manager,
        )

        logger.info("Initialized MomentumAnalysisService with SOLID architecture")

    return _momentum_service
