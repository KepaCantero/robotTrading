"""
Broker Adapters - Implementation-specific broker connectors.

This package provides concrete implementations for different brokers.
Each adapter implements the BrokerConnector interface for a specific broker.

Available Adapters:
- AlpacaAdapter: Alpaca broker integration
- PaperAdapter: Paper trading for testing/simulation
- IBAdapter: Interactive Brokers integration
- (Future) TradierAdapter: Tradier broker integration
"""

from .alpaca_adapter import AlpacaAdapter
from .ib_adapter import IBAdapter, IBConnection, get_ib_adapter
from .paper_adapter import PaperAdapter

__all__ = [
    "AlpacaAdapter",
    "IBAdapter",
    "IBConnection",
    "PaperAdapter",
    "get_ib_adapter",
]
