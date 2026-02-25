"""
Configuration Parameters Module

Extracted from centralized_config.py for SRP compliance.
TASK-24: SRP Refactoring
"""

from app.shared.config.params.trading_thresholds import TradingThresholds
from app.shared.config.params.strategy_config import StrategyConfig, StockAllocationSettings
from app.shared.config.params.backtest_config import (
    BacktestingConfig,
    CommissionModel,
    FixedCommission,
    HybridCommission,
    TierBracket,
    TieredCommission,
)
from app.shared.config.params.infrastructure_config import (
    APIConfig,
    DatabaseConfig,
    LoggingConfig,
    MonitoringConfig,
    RedisConfig,
)
from app.shared.config.params.risk_config import (
    ComplianceConfig,
    CurrencyHedgingConfig,
    SectorCountryDiversificationConfig,
)

__all__ = [
    # Trading
    "TradingThresholds",
    # Strategy
    "StrategyConfig",
    "StockAllocationSettings",
    # Backtesting
    "BacktestingConfig",
    "CommissionModel",
    "FixedCommission",
    "HybridCommission",
    "TierBracket",
    "TieredCommission",
    # Infrastructure
    "DatabaseConfig",
    "RedisConfig",
    "APIConfig",
    "LoggingConfig",
    "MonitoringConfig",
    # Risk & Compliance
    "CurrencyHedgingConfig",
    "SectorCountryDiversificationConfig",
    "ComplianceConfig",
]
