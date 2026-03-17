"""
Repository Pattern Implementation for Database Access.

This module re-exports all repository classes from domain-specific modules
for backward compatibility. The implementations have been split into:
- _user_portfolio_repositories.py: User, Portfolio, Asset, Position
- _trading_repositories.py: Trade, Signal
- _analytics_repositories.py: MarketData, Backtest, RiskMetrics, SystemLog

TASK-6: Configuración de base de datos
"""

from app.infrastructure.persistence.database._analytics_repositories import (
    BacktestRepository,
    MarketDataRepository,
    RiskMetricsRepository,
    SystemLogRepository,
)
from app.infrastructure.persistence.database._trading_repositories import (
    SignalRepository,
    TradeRepository,
)
from app.infrastructure.persistence.database._user_portfolio_repositories import (
    AssetRepository,
    PortfolioRepository,
    PositionRepository,
    UserRepository,
)

__all__ = [
    "UserRepository",
    "PortfolioRepository",
    "AssetRepository",
    "PositionRepository",
    "TradeRepository",
    "SignalRepository",
    "MarketDataRepository",
    "BacktestRepository",
    "RiskMetricsRepository",
    "SystemLogRepository",
]
