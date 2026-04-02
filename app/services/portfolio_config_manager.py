"""
Portfolio Configuration Manager.

Manages automated sector allocation, market type filtering, and strategy
capital allocation based on portfolio.yaml configuration.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import yaml

from app.services.multi_strategy_allocation import MultiStrategyAllocationManager

logger = logging.getLogger(__name__)


class SectorFilter:
    """Filters market data by sector."""

    def __init__(self, sector_symbols: dict[str, list[str]]):
        """
        Initialize sector filter.

        Args:
            sector_symbols: Dictionary mapping sector names to symbol lists
        """
        self.sector_symbols = sector_symbols
        # Create reverse mapping: symbol -> sectors
        self.symbol_to_sectors: dict[str, set[str]] = {}
        for sector, symbols in sector_symbols.items():
            for symbol in symbols:
                if symbol not in self.symbol_to_sectors:
                    self.symbol_to_sectors[symbol] = set()
                self.symbol_to_sectors[symbol].add(sector)

    def symbol_belongs_to_sector(self, symbol: str, sectors: list[str]) -> bool:
        """
        Check if symbol belongs to any of the specified sectors.

        Args:
            symbol: Trading symbol
            sectors: List of sector names

        Returns:
            True if symbol belongs to any sector
        """
        symbol_sectors = self.symbol_to_sectors.get(symbol, set())
        return any(s in symbol_sectors for s in sectors)

    def filter_symbols_by_sector(self, symbols: list[str], allowed_sectors: list[str]) -> list[str]:
        """
        Filter symbols by allowed sectors.

        Args:
            symbols: List of symbols to filter
            allowed_sectors: List of allowed sector names

        Returns:
            Filtered list of symbols
        """
        return [s for s in symbols if self.symbol_belongs_to_sector(s, allowed_sectors)]


class PortfolioConfigManager:
    """
    Manages portfolio configuration with sector and market type filtering.

    Loads configuration from portfolio.yaml and provides:
    - Sector-based symbol filtering
    - Market type validation
    - Capital allocation per strategy
    - Rebalancing configuration
    """

    def __init__(self, config_path: str = "config/portfolio.yaml"):
        """
        Initialize portfolio configuration manager.

        Args:
            config_path: Path to portfolio configuration file
        """
        self.config_path = Path(config_path)
        self.config: dict[str, Any] = {}
        self.sector_filter: SectorFilter | None = None
        self.allocation_manager: MultiStrategyAllocationManager | None = None

        if self.config_path.exists():
            self.load_config()

    def load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}

            # Initialize sector filter
            sectors = self.config.get("sectors", {})
            sector_symbols = {
                sector_name: sector_data.get("symbols", [])
                for sector_name, sector_data in sectors.items()
            }
            self.sector_filter = SectorFilter(sector_symbols)

            # Initialize allocation manager
            portfolio_config = self.config.get("portfolio", {})
            total_capital = Decimal(str(portfolio_config.get("total_capital", 100000)))
            self.allocation_manager = MultiStrategyAllocationManager(total_capital)

            # Configure strategy allocations from config
            self._configure_strategy_allocations()

            logger.info(f"Loaded portfolio configuration from {self.config_path}")

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Failed to load portfolio config: {e}")
            raise

    def _configure_strategy_allocations(self) -> None:
        """Configure strategy allocations from config file."""
        strategy_allocations = self.config.get("strategy_allocations", {})

        for strategy_name, strategy_config in strategy_allocations.items():
            if not strategy_config.get("enabled", True):
                continue

            capital_config = strategy_config.get("capital_allocation", {})

            if (
                self.allocation_manager is not None
                and strategy_name in self.allocation_manager.strategy_allocations
            ):
                allocation = self.allocation_manager.strategy_allocations[strategy_name]
                allocation.target_weight = Decimal(str(capital_config.get("target_weight", 0.25)))
                allocation.min_weight = Decimal(str(capital_config.get("min_weight", 0.10)))
                allocation.max_weight = Decimal(str(capital_config.get("max_weight", 0.40)))

                logger.info(
                    f"Configured {strategy_name}: {allocation.target_weight:.1%} "
                    f"(range: {allocation.min_weight:.1%} - {allocation.max_weight:.1%})"
                )

    def get_strategy_sectors(self, strategy_name: str) -> list[str]:
        """
        Get allowed sectors for a strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            List of allowed sector names
        """
        strategy_config = self.config.get("strategy_allocations", {}).get(strategy_name, {})
        return cast("list[str]", strategy_config.get("sectors", []))

    def get_strategy_market_types(self, strategy_name: str) -> list[str]:
        """
        Get allowed market types for a strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            List of allowed market type names
        """
        strategy_config = self.config.get("strategy_allocations", {}).get(strategy_name, {})
        return cast("list[str]", strategy_config.get("market_types", []))

    def get_strategy_symbols(self, strategy_name: str) -> list[str]:
        """
        Get allowed symbols for a strategy (based on sectors).

        Args:
            strategy_name: Name of the strategy

        Returns:
            List of allowed symbols
        """
        sectors = self.get_strategy_sectors(strategy_name)

        if not sectors or not self.sector_filter:
            return []  # No filtering if no sectors specified

        # Collect all symbols from allowed sectors
        allowed_symbols = set()
        sector_symbols = self.config.get("sectors", {})

        for sector_name in sectors:
            sector_data = sector_symbols.get(sector_name, {})
            symbols = sector_data.get("symbols", [])
            allowed_symbols.update(symbols)

        return sorted(allowed_symbols)

    def should_filter_symbol(self, symbol: str, strategy_name: str) -> bool:
        """
        Check if symbol should be filtered for a strategy.

        Args:
            symbol: Trading symbol
            strategy_name: Name of the strategy

        Returns:
            True if symbol should be included (not filtered)
        """
        sectors = self.get_strategy_sectors(strategy_name)

        # If no sectors specified, don't filter
        if not sectors:
            return True

        # Check if symbol belongs to allowed sectors
        if not self.sector_filter:
            return True

        return self.sector_filter.symbol_belongs_to_sector(symbol, sectors)

    def get_allocation_manager(self) -> MultiStrategyAllocationManager:
        """
        Get the multi-strategy allocation manager.

        Returns:
            MultiStrategyAllocationManager instance
        """
        if not self.allocation_manager:
            total_capital = Decimal(
                str(self.config.get("portfolio", {}).get("total_capital", 100000))
            )
            self.allocation_manager = MultiStrategyAllocationManager(total_capital)

        return self.allocation_manager

    def get_rebalancing_config(self, strategy_name: str | None = None) -> dict[str, Any]:
        """
        Get rebalancing configuration.

        Args:
            strategy_name: Optional strategy name for strategy-specific config

        Returns:
            Rebalancing configuration dictionary
        """
        if strategy_name:
            strategy_config = self.config.get("strategy_allocations", {}).get(strategy_name, {})
            return cast("dict[str, Any]", strategy_config.get("rebalancing", {}))
        else:
            portfolio_config = self.config.get("portfolio", {})
            return cast("dict[str, Any]", portfolio_config.get("global_rebalancing", {}))

    def get_reporting_config(self) -> dict[str, Any]:
        """Get reporting configuration."""
        portfolio_config = self.config.get("portfolio", {})
        return cast("dict[str, Any]", portfolio_config.get("reporting", {}))

    def update_total_capital(self, new_capital: Decimal) -> None:
        """
        Update total capital and reload allocations.

        Args:
            new_capital: New total capital amount
        """
        if self.allocation_manager:
            self.allocation_manager.update_total_capital(new_capital)

        # Update config
        if "portfolio" not in self.config:
            self.config["portfolio"] = {}
        self.config["portfolio"]["total_capital"] = float(new_capital)

    def get_enabled_strategies(self) -> list[str]:
        """
        Get list of enabled strategies.

        Returns:
            List of enabled strategy names
        """
        strategy_allocations = self.config.get("strategy_allocations", {})
        return [
            name for name, config in strategy_allocations.items() if config.get("enabled", True)
        ]


# Global instance
_portfolio_config_manager: PortfolioConfigManager | None = None


def get_portfolio_config_manager(
    config_path: str = "config/portfolio.yaml",
) -> PortfolioConfigManager:
    """Get global portfolio configuration manager instance."""
    global _portfolio_config_manager
    if _portfolio_config_manager is None:
        _portfolio_config_manager = PortfolioConfigManager()

    return _portfolio_config_manager
