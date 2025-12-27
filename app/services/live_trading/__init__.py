"""
Live Trading Bridge - Comprehensive alert-to-trade execution system.

This package provides a complete live trading bridge that:
1. Monitors incoming alerts from the alerting system
2. Maps alerts to trade signals using configurable rules
3. Validates trades against risk gates
4. Executes trades through broker APIs
5. Records all executions and maintains audit trails

Main Components:
- TradingBridgeOrchestrator: Main orchestration engine
- BrokerConnector: Unified broker API abstraction
- OrderManager: Order lifecycle management
- RiskGates: Pre-trade risk validation
- AccountSynchronizer: Portfolio synchronization
- AlertToTradeMapper: Alert-to-signal mapping
- TradingAuditTrail: Compliance and audit logging
- TradePersistenceManager: Database persistence
"""

from .account_synchronizer import AccountSynchronizer, get_account_synchronizer
from .alert_to_trade_mapper import AlertToTradeMapper, get_alert_to_trade_mapper
from .broker_connector import BrokerConnector, get_broker_connector
from .order_manager import OrderManager, get_order_manager
from .risk_gates import RiskGates, get_risk_gates
from .trade_persistence import TradePersistenceManager, get_trade_persistence_manager
from .trading_audit_trail import TradingAuditTrail, get_trading_audit_trail
from .trading_bridge_orchestrator import TradingBridgeOrchestrator, get_trading_bridge_orchestrator

# Service Classes
__all__ = [
    "TradingBridgeOrchestrator",
    "BrokerConnector",
    "OrderManager",
    "RiskGates",
    "AccountSynchronizer",
    "AlertToTradeMapper",
    "TradingAuditTrail",
    "TradePersistenceManager",
    # Singleton Getters
    "get_trading_bridge_orchestrator",
    "get_broker_connector",
    "get_order_manager",
    "get_risk_gates",
    "get_account_synchronizer",
    "get_alert_to_trade_mapper",
    "get_trading_audit_trail",
    "get_trade_persistence_manager",
]
