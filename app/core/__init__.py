"""
Core module for AlgoTrading MVP.

This module contains core functionality including configuration,
database connections, and shared utilities.

Phase 0.3: Added timezone utilities for consistent timezone handling
across all multi-market operations (stocks, forex, crypto).

Compliance Integration (2026-01-28): Added THE ONLY Compliance Engine.
USE ComplianceEngine FOR EVERYTHING.
"""

from __future__ import annotations

import logging
from typing import Callable, Union

logger = logging.getLogger(__name__)

# Basic utilities - always import these
from app.shared.config.config_loader import (
    YAMLConfigLoader,
    get_config_loader,
    load_strategy_stock_allocator_config,
)
from app.shared.config.yaml_config_updater import YAMLConfigUpdater
from app.shared.utils.timezone_utils import (
    format_market_time,
    format_utc,
    get_market_open_close_time,
    get_market_timezone,
    is_market_open,
    to_market_time,
    to_utc,
    utc_now,
)

# =============================================================================
# THE ONLY COMPLIANCE ENGINE - USE THIS FOR EVERYTHING
# =============================================================================
# Initialize fallback values first, then attempt import
ComplianceEngine: Union[type, None] = None
PreTradeAnalysis: Union[type, None] = None
PostTradeAnalysis: Union[type, None] = None
PortfolioOptimization: Union[type, None] = None
get_compliance_engine: Union[Callable[..., object], None] = None
quick_check: Union[Callable[..., object], None] = None
get_execution_plan: Union[Callable[..., object], None] = None
SystemAvailability: Union[type, None] = None
_compliance_engine_available = False

try:
    from app.domain.services.compliance.compliance_engine import (
        ComplianceEngine,
        PortfolioOptimization,
        PostTradeAnalysis,
        PreTradeAnalysis,
        SystemAvailability,
        get_compliance_engine,
        get_execution_plan,
        quick_check,
    )

    _compliance_engine_available = True
except ImportError:
    # Import error - likely due to NumPy/matplotlib compatibility issues
    # Values already set to None above
    logger.error("Failed to import ComplianceEngine", exc_info=True)

# =============================================================================
# LEGACY SUPPORT (DEPRECATED - use ComplianceEngine instead)
# =============================================================================
ComplianceIntegrationEngineDeprecated: Union[type, None] = None
get_compliance_integration_engine_deprecated: Union[Callable[..., object], None] = None
quick_pre_trade_check: Union[Callable[..., object], None] = None
get_execution_recommendation: Union[Callable[..., object], None] = None
_compliance_integration_available = False

try:
    from app.domain.services.compliance.compliance_integration import (
        ComplianceIntegrationEngine as ComplianceIntegrationEngineDeprecated,
        get_compliance_integration_engine as get_compliance_integration_engine_deprecated,
        get_execution_recommendation,
        quick_pre_trade_check,
    )

    _compliance_integration_available = True
except ImportError:
    # Import error - likely due to NumPy/matplotlib compatibility issues
    # Values already set to None above
    logger.error("Failed to import ComplianceIntegrationEngine (legacy)", exc_info=True)

__all__ = [
    # THE ONLY COMPLIANCE ENGINE - USE THIS
    "ComplianceEngine",
    # Legacy (DEPRECATED)
    "ComplianceIntegrationEngineDeprecated",
    "PortfolioOptimization",
    "PostTradeAnalysis",
    "PreTradeAnalysis",
    "SystemAvailability",
    # Configuration
    "YAMLConfigLoader",
    "YAMLConfigUpdater",
    "format_market_time",
    "format_utc",
    "get_compliance_engine",
    "get_compliance_integration_engine_deprecated",
    "get_config_loader",
    "get_execution_plan",
    "get_execution_recommendation",
    "get_market_open_close_time",
    "get_market_timezone",
    "is_market_open",
    "load_strategy_stock_allocator_config",
    "quick_check",
    "quick_pre_trade_check",
    "to_market_time",
    "to_utc",
    # Timezone utilities (Phase 0.3)
    "utc_now",
]
