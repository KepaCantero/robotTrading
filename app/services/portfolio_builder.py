"""
Portfolio Builder Service.

Builds a diversified portfolio based on portfolio configuration with multiple symbols
from different sectors, allocated according to strategy percentages.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from app.backtesting.data_loader import DataLoader
from app.models.market_data import Quote
from app.services.portfolio_config_manager import (
    PortfolioConfigManager,
    get_portfolio_config_manager,
)

logger = logging.getLogger(__name__)


class PortfolioBuilder:
    """
    Builds a multi-symbol portfolio for backtesting based on portfolio configuration.

    Loads market data for all symbols across all strategies' sectors and creates
    a unified portfolio for backtesting.
    """

    def __init__(
        self,
        portfolio_config: Optional[PortfolioConfigManager] = None,
        data_loader: Optional[DataLoader] = None,
    ):
        """
        Initialize portfolio builder.

        Args:
            portfolio_config: Portfolio configuration manager
            data_loader: Data loader instance
        """
        self.portfolio_config = portfolio_config or get_portfolio_config_manager()
        self.data_loader = data_loader or DataLoader()

    def build_portfolio_quotes(
        self,
        start_date: datetime,
        end_date: datetime,
        max_symbols_per_strategy: Optional[int] = None,
    ) -> List[Quote]:
        """
        Build a complete portfolio with quotes from all strategy sectors.

        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            max_symbols_per_strategy: Optional limit on symbols per strategy

        Returns:
            Combined list of quotes from all strategy sectors
        """
        logger.info(f"Building portfolio from {start_date.date()} to {end_date.date()}")

        # Get all enabled strategies
        enabled_strategies = self.portfolio_config.get_enabled_strategies()

        # Collect all symbols needed across all strategies
        all_symbols = self._collect_all_symbols(enabled_strategies, max_symbols_per_strategy)

        logger.info(f"Portfolio will include {len(all_symbols)} symbols: {sorted(all_symbols)}")

        # Load market data for all symbols
        all_quotes = []
        loaded_symbols = []
        failed_symbols = []

        import time

        for i, symbol in enumerate(sorted(all_symbols)):
            try:
                # Try CSV first (faster, no rate limits)
                quotes = self.data_loader.load_market_data(
                    symbol, start_date, end_date, source="csv"
                )

                # If CSV fails, try yfinance but with rate limiting protection
                if not quotes:
                    # Add delay to avoid rate limiting (except for first request)
                    if i > 0:
                        time.sleep(0.5)  # 500ms delay between requests

                    quotes = self.data_loader.load_market_data(
                        symbol, start_date, end_date, source="yfinance"
                    )

                if quotes:
                    all_quotes.extend(quotes)
                    loaded_symbols.append(symbol)
                    logger.debug(f"Loaded {len(quotes)} quotes for {symbol}")
                else:
                    failed_symbols.append(symbol)
                    logger.warning(f"No data available for {symbol}")

            except Exception as e:
                error_msg = str(e).lower()
                if "rate limit" in error_msg or "too many requests" in error_msg:
                    logger.warning(
                        f"Rate limited for {symbol}. Will retry after delay or skip. "
                        "Consider using CSV files for better performance."
                    )
                    failed_symbols.append(symbol)
                    # Add longer delay if rate limited
                    time.sleep(2.0)
                else:
                    failed_symbols.append(symbol)
                    logger.error(f"Error loading {symbol}: {e}")

        logger.info(
            f"Portfolio built: {len(loaded_symbols)} symbols loaded, "
            f"{len(failed_symbols)} failed, {len(all_quotes)} total quotes"
        )

        if failed_symbols:
            logger.warning(f"Failed to load: {', '.join(failed_symbols)}")

        if not all_quotes:
            if failed_symbols and "rate limit" in str(failed_symbols).lower():
                raise ValueError(
                    f"Rate limited by yfinance. Failed to load {len(failed_symbols)} symbols. "
                    f"Please try again later or add CSV files to data/historical/ for: "
                    f"{', '.join(failed_symbols[:5])}{'...' if len(failed_symbols) > 5 else ''}"
                )
            else:
                raise ValueError(
                    f"No market data loaded for portfolio. "
                    f"Failed to load {len(failed_symbols)} symbols: "
                    f"{', '.join(failed_symbols[:5])}{'...' if len(failed_symbols) > 5 else ''}"
                )

        # Sort quotes by timestamp for consistent processing
        all_quotes.sort(key=lambda q: q.timestamp)

        return all_quotes

    def _collect_all_symbols(
        self,
        strategies: List[str],
        max_symbols_per_strategy: Optional[int] = None,
    ) -> Set[str]:
        """
        Collect all symbols needed across strategies.

        Args:
            strategies: List of strategy names
            max_symbols_per_strategy: Optional limit per strategy

        Returns:
            Set of all unique symbols needed
        """
        all_symbols = set()

        for strategy_name in strategies:
            # Get symbols for this strategy from sectors
            strategy_symbols = self.portfolio_config.get_strategy_symbols(strategy_name)

            if not strategy_symbols:
                logger.warning(f"No symbols configured for {strategy_name}")
                continue

            # Handle pairs trading separately - needs both symbols in pair
            if strategy_name == "pairs_trading":
                # For pairs trading, ensure we have both symbols of configured pairs
                strategy_config = self.portfolio_config.config.get("strategy_allocations", {}).get(
                    strategy_name, {}
                )

                # Check if pair_symbols is explicitly configured
                # Otherwise use symbols from sectors
                pair_symbols_raw = strategy_config.get("pair_symbols", strategy_symbols[:2])

                # Handle both formats: list of lists or simple list
                if pair_symbols_raw and isinstance(pair_symbols_raw, list):
                    if len(pair_symbols_raw) > 0 and isinstance(pair_symbols_raw[0], list):
                        # List of lists format - extract all unique symbols from all pairs
                        pair_symbols_flat = []
                        for pair in pair_symbols_raw:
                            if isinstance(pair, list) and len(pair) >= 2:
                                pair_symbols_flat.extend(pair[:2])  # Take first 2 of each pair
                        # Remove duplicates while preserving order
                        pair_symbols_list = list(dict.fromkeys(pair_symbols_flat))
                        logger.info(
                            f"Pairs Trading: Using {len(pair_symbols_list)} symbols from {len(pair_symbols_raw)} configured pairs"
                        )
                    else:
                        # Simple list format
                        pair_symbols_list = (
                            pair_symbols_raw if len(pair_symbols_raw) >= 2 else strategy_symbols[:2]
                        )
                else:
                    # Fallback: use first two symbols from sectors
                    pair_symbols_list = (
                        strategy_symbols[:2] if len(strategy_symbols) >= 2 else strategy_symbols
                    )

                # Add all pair symbols to the set
                if pair_symbols_list:
                    all_symbols.update(pair_symbols_list)
                    logger.info(
                        f"Pairs Trading: Added {len(pair_symbols_list)} symbols: {', '.join(pair_symbols_list[:5])}"
                        f"{'...' if len(pair_symbols_list) > 5 else ''}"
                    )
                else:
                    logger.warning(
                        "Pairs Trading: No pair symbols available, using sector symbols"
                    )
                    all_symbols.update(strategy_symbols)
            else:
                # For other strategies, use symbols from sectors
                if max_symbols_per_strategy:
                    strategy_symbols = strategy_symbols[:max_symbols_per_strategy]

                all_symbols.update(strategy_symbols)
                logger.debug(
                    f"{strategy_name}: Added {len(strategy_symbols)} symbols "
                    f"({', '.join(strategy_symbols[:5])}{'...' if len(strategy_symbols) > 5 else ''})"
                )

        return all_symbols

    def get_strategy_symbols_mapping(self) -> Dict[str, List[str]]:
        """
        Get mapping of strategy to its symbols.

        Returns:
            Dictionary mapping strategy names to their symbol lists
        """
        enabled_strategies = self.portfolio_config.get_enabled_strategies()

        mapping = {}
        for strategy_name in enabled_strategies:
            symbols = self.portfolio_config.get_strategy_symbols(strategy_name)
            mapping[strategy_name] = symbols

        return mapping

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get summary of portfolio configuration.

        Returns:
            Dictionary with portfolio summary
        """
        enabled_strategies = self.portfolio_config.get_enabled_strategies()
        symbol_mapping = self.get_strategy_symbols_mapping()

        # Count total unique symbols
        all_symbols = set()
        for symbols in symbol_mapping.values():
            all_symbols.update(symbols)

        summary = {
            "enabled_strategies": enabled_strategies,
            "total_unique_symbols": len(all_symbols),
            "symbols_by_strategy": symbol_mapping,
            "all_symbols": sorted(all_symbols),
        }

        return summary
