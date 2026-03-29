"""
Configuration Parameters Module

Extracted from centralized_config.py for SRP compliance.
TASK-24: SRP Refactoring
"""

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
from app.shared.config.params.strategy_config import StockAllocationSettings, StrategyConfig
from app.shared.config.params.trading_thresholds import TradingThresholds

__all__ = [
    "APIConfig",
    # Backtesting
    "BacktestingConfig",
    "CommissionModel",
    "ComplianceConfig",
    # Risk & Compliance
    "CurrencyHedgingConfig",
    # Infrastructure
    "DatabaseConfig",
    "FixedCommission",
    "HybridCommission",
    "LoggingConfig",
    "MonitoringConfig",
    "RedisConfig",
    "SectorCountryDiversificationConfig",
    "StockAllocationSettings",
    # Strategy
    "StrategyConfig",
    "TierBracket",
    "TieredCommission",
    # Trading
    "TradingThresholds",
]
