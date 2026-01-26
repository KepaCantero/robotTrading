"""
Core module for AlgoTrading MVP.

This module contains core functionality including configuration,
database connections, and shared utilities.

Phase 0.3: Added timezone utilities for consistent timezone handling
across all multi-market operations (stocks, forex, crypto).
"""

from app.core.config_loader import (
    YAMLConfigLoader,
    get_config_loader,
    load_strategy_stock_allocator_config,
)
from app.core.yaml_config_updater import YAMLConfigUpdater
from app.core.timezone_utils import (
    utc_now,
    to_utc,
    to_market_time,
    format_utc,
    format_market_time,
    get_market_timezone,
    is_market_open,
    get_market_open_close_time,
)

__all__ = [
    # Configuration
    "YAMLConfigLoader",
    "get_config_loader",
    "load_strategy_stock_allocator_config",
    "YAMLConfigUpdater",
    # Timezone utilities (Phase 0.3)
    "utc_now",
    "to_utc",
    "to_market_time",
    "format_utc",
    "format_market_time",
    "get_market_timezone",
    "is_market_open",
    "get_market_open_close_time",
]
