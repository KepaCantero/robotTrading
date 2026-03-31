"""
Strategy manager component.

SOLID Principles:
- SRP: Only manages momentum strategies
- OCP: Extensible through new strategy types
- LSP: Implements StrategyManager protocol
- ISP: Focused on strategy CRUD operations
- DIP: Depends on StorageBackend protocol
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from app.domain.models.momentum import (
    MomentumFilter,
    MomentumSignal,
    MomentumStrategy,
    MomentumType,
    Timeframe,
)
from app.services.momentum.protocols import StorageBackend
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class StrategyManager:
    """
    Momentum strategy lifecycle management.

    Single Responsibility:
    - Manage momentum strategies
    - Create, read, update, delete strategies
    - Get signals for strategies

    Dependency Inversion:
    - Depends on StorageBackend protocol for persistence
    """

    def __init__(self, storage: StorageBackend) -> None:
        """
        Initialize strategy manager with storage backend.

        Args:
            storage: Storage backend for strategy persistence
        """
        self.storage = storage
        self.strategies: dict[str, MomentumStrategy] = {}
        self.initialize_default_strategies()

    def initialize_default_strategies(self) -> None:
        """Initialize default momentum strategies using centralized configuration."""
        trading_config = get_config().trading

        strategies = [
            MomentumStrategy(
                name="Daily Price Momentum",
                description="Daily momentum strategy based on price and volume",
                momentum_type=MomentumType.PRICE_MOMENTUM,
                timeframe=Timeframe.DAILY,
                min_strength=trading_config.min_signal_strength,
                min_confidence=trading_config.min_signal_confidence,
                signal_duration=24,
                rsi_oversold=trading_config.rsi_oversold,
                rsi_overbought=trading_config.rsi_overbought,
                ema_short_period=9,
                ema_long_period=21,
                min_volume_ratio=1.2,
                volume_spike_threshold=2.0,
                max_position_size=trading_config.max_position_size,
                stop_loss_pct=trading_config.stop_loss_pct,
                take_profit_pct=trading_config.take_profit_pct,
            ),
            MomentumStrategy(
                name="Volume Momentum",
                description="Volume-based momentum strategy",
                momentum_type=MomentumType.VOLUME_MOMENTUM,
                timeframe=Timeframe.DAILY,
                min_strength=trading_config.min_signal_strength + 10.0,
                min_confidence=trading_config.min_signal_confidence + 5.0,
                signal_duration=12,
                min_volume_ratio=1.5,
                volume_spike_threshold=2.5,
                max_position_size=trading_config.max_position_size * 0.8,
                stop_loss_pct=trading_config.stop_loss_pct * 0.8,
                take_profit_pct=trading_config.take_profit_pct * 0.8,
            ),
            MomentumStrategy(
                name="Combined Momentum",
                description="Combined price, volume, and volatility momentum",
                momentum_type=MomentumType.COMBINED_MOMENTUM,
                timeframe=Timeframe.DAILY,
                min_strength=trading_config.min_signal_strength + 15.0,
                min_confidence=trading_config.min_signal_confidence + 10.0,
                signal_duration=18,
                rsi_oversold=trading_config.rsi_oversold - 5.0,
                rsi_overbought=trading_config.rsi_overbought + 5.0,
                ema_short_period=12,
                ema_long_period=26,
                min_volume_ratio=1.3,
                volume_spike_threshold=2.0,
                max_position_size=trading_config.max_position_size * 1.2,
                stop_loss_pct=trading_config.stop_loss_pct * 1.2,
                take_profit_pct=trading_config.take_profit_pct * 1.2,
            ),
        ]

        for strategy in strategies:
            self.strategies[strategy.name] = strategy

    async def create_strategy(self, strategy: MomentumStrategy) -> MomentumStrategy:
        """
        Create a new momentum strategy.

        Args:
            strategy: Strategy to create

        Returns:
            Created strategy

        Raises:
            ValueError: If strategy already exists
        """
        if strategy.name in self.strategies:
            raise ValueError(f"Strategy {strategy.name} already exists")

        self.strategies[strategy.name] = strategy
        await self.storage.save_strategy(strategy)

        logger.info(f"Created momentum strategy: {strategy.name}")
        return strategy

    async def get_strategy(self, strategy_name: str) -> Optional[MomentumStrategy]:
        """
        Get a momentum strategy by name.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Strategy if found, None otherwise
        """
        return self.strategies.get(strategy_name)

    async def update_strategy(
        self, strategy_name: str, updated_fields: dict[str, Any]
    ) -> Optional[MomentumStrategy]:
        """
        Update a momentum strategy.

        Args:
            strategy_name: Name of the strategy to update
            updated_fields: Dictionary of fields to update

        Returns:
            Updated strategy if found, None otherwise
        """
        if strategy_name not in self.strategies:
            return None

        strategy = self.strategies[strategy_name]
        for field, value in updated_fields.items():
            if hasattr(strategy, field):
                setattr(strategy, field, value)

        strategy.updated_at = datetime.utcnow()
        await self.storage.save_strategy(strategy)

        logger.info(f"Updated momentum strategy: {strategy_name}")
        return strategy

    async def delete_strategy(self, strategy_name: str) -> bool:
        """
        Delete a momentum strategy.

        Args:
            strategy_name: Name of the strategy to delete

        Returns:
            True if deleted, False if not found
        """
        if strategy_name not in self.strategies:
            return False

        del self.strategies[strategy_name]

        logger.info(f"Deleted momentum strategy: {strategy_name}")
        return True

    async def get_strategy_signals(
        self, strategy_name: str, all_signals: list[MomentumSignal]
    ) -> list[MomentumSignal]:
        """
        Get signals for a specific strategy.

        Args:
            strategy_name: Name of the strategy
            all_signals: List of all available signals

        Returns:
            Filtered list of signals for the strategy
        """
        if strategy_name not in self.strategies:
            return []

        strategy = self.strategies[strategy_name]
        filter_criteria = MomentumFilter(
            min_strength=strategy.min_strength,
            min_confidence=strategy.min_confidence,
            active_only=True,
        )

        filtered_signals = [s for s in all_signals if filter_criteria.matches(s)]
        strategy_signals = [s for s in filtered_signals if s.signal_type == strategy.momentum_type]

        return strategy_signals

    async def get_top_momentum_assets(
        self, all_signals: list[MomentumSignal], limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get top momentum assets.

        Args:
            all_signals: List of all available signals
            limit: Maximum number of assets to return (default 10)

        Returns:
            List of top momentum assets with their metrics
        """
        asset_signals: dict[str, MomentumSignal] = {}
        for signal in all_signals:
            if (
                signal.symbol not in asset_signals
                or signal.momentum_score > asset_signals[signal.symbol].momentum_score
            ):
                asset_signals[signal.symbol] = signal

        sorted_assets = sorted(asset_signals.values(), key=lambda x: x.momentum_score, reverse=True)

        top_assets = []
        for signal in sorted_assets[:limit]:
            top_assets.append(
                {
                    "symbol": signal.symbol,
                    "momentum_score": signal.momentum_score,
                    "strength": signal.strength,
                    "confidence": signal.confidence,
                    "direction": signal.direction,
                    "signal_type": signal.signal_type.value,
                    "timestamp": signal.timestamp,
                }
            )

        return top_assets

    def get_all_strategies(self) -> dict[str, MomentumStrategy]:
        """
        Get all strategies.

        Returns:
            Dictionary of all strategies
        """
        return self.strategies.copy()
