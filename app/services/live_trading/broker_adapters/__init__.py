"""
Broker Adapters - Implementation-specific broker connectors.

This package provides concrete implementations for different brokers.
Each adapter implements the BrokerConnector interface for a specific broker.

Available Adapters:
- AlpacaAdapter: Alpaca broker integration
- PaperAdapter: Paper trading for testing/simulation
- (Future) InteractiveBrokersAdapter: Interactive Brokers integration
- (Future) TradierAdapter: Tradier broker integration
"""

from .alpaca_adapter import AlpacaAdapter
from .paper_adapter import PaperAdapter

__all__ = [
    "AlpacaAdapter",
    "PaperAdapter",
]
