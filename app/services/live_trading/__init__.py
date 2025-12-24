"""
T16.1: Live Trading Bridge - Integration with broker APIs and live execution

Provides:
- BrokerConnector: API integration with brokers (Interactive Brokers, Alpaca, etc.)
- OrderManager: Order lifecycle management (placement, execution, cancellation)
- RiskGates: Pre-trade risk validation (position limits, leverage, drawdown)
- AccountSynchronizer: Portfolio reconciliation and balance sync
"""

from .broker_connector import (
    BrokerConnector,
    get_broker_connector,
)
from .order_manager import (
    OrderManager,
    get_order_manager,
)
from .risk_gates import (
    RiskGates,
    get_risk_gates,
)
from .account_synchronizer import (
    AccountSynchronizer,
    get_account_synchronizer,
)

__all__ = [
    "BrokerConnector",
    "get_broker_connector",
    "OrderManager",
    "get_order_manager",
    "RiskGates",
    "get_risk_gates",
    "AccountSynchronizer",
    "get_account_synchronizer",
]
