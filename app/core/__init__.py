"""
Core module for AlgoTrading MVP.

This module contains core functionality including configuration,
database connections, and shared utilities.

Phase 0.3: Added timezone utilities for consistent timezone handling
across all multi-market operations (stocks, forex, crypto).

Compliance Integration (2026-01-28): Added THE ONLY Compliance Engine.
USE ComplianceEngine FOR EVERYTHING.
"""

import logging
from typing import Any, Callable, Optional

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
    # Set these to None to prevent import errors when only using other core modules
    logger.error("Failed to import ComplianceEngine", exc_info=True)
    ComplianceEngine: Optional[type[Any]] = None
    PreTradeAnalysis: Optional[type[Any]] = None
    PostTradeAnalysis: Optional[type[Any]] = None
    PortfolioOptimization: Optional[type[Any]] = None
    get_compliance_engine: Optional[Callable[..., Any]] = None
    quick_check: Optional[Callable[..., Any]] = None
    get_execution_plan: Optional[Callable[..., Any]] = None
    SystemAvailability: Optional[type[Any]] = None
    _compliance_engine_available = False

# Legacy support (DEPRECATED - use ComplianceEngine instead)
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
    logger.error("Failed to import ComplianceIntegrationEngine (legacy)", exc_info=True)
    ComplianceIntegrationEngineDeprecated: Optional[type[Any]] = None
    get_compliance_integration_engine_deprecated: Optional[Callable[..., Any]] = None
    quick_pre_trade_check: Optional[Callable[..., Any]] = None
    get_execution_recommendation: Optional[Callable[..., Any]] = None
    _compliance_integration_available = False

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
    # THE ONLY COMPLIANCE ENGINE - USE THIS
    "ComplianceEngine",
    "PreTradeAnalysis",
    "PostTradeAnalysis",
    "PortfolioOptimization",
    "get_compliance_engine",
    "quick_check",
    "get_execution_plan",
    "SystemAvailability",
    # Legacy (DEPRECATED)
    "ComplianceIntegrationEngineDeprecated",
    "get_compliance_integration_engine_deprecated",
    "quick_pre_trade_check",
    "get_execution_recommendation",
]
