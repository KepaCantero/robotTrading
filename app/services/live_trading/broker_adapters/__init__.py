"""
Broker Adapters - Implementation-specific broker connectors.

This package provides concrete implementations for different brokers.
Each adapter implements the BrokerConnector interface for a specific broker.

Available Adapters:
- AlpacaAdapter: Alpaca broker integration
- PaperAdapter: Paper trading for testing/simulation
- IBAdapter: Interactive Brokers integration (legacy)
- IBKRSpainAdapter: Interactive Brokers for Spain (implements IBrokerAdapter Protocol)
- CurrencyConverter: EUR/USD currency conversion
- (Future) TradierAdapter: Tradier broker integration
"""

from .alpaca_adapter import AlpacaAdapter
from .currency_converter import CurrencyConverter, get_currency_converter
from .ib_adapter import IBAdapter, IBConnection, get_ib_adapter
from .ibex35_contracts import (
    create_index_contract,
    create_stock_contract,
    get_ibex35_symbols,
    is_ibex35_symbol,
)
from .ibkr_adapter_spain import IBKRSpainAdapter, get_ibkr_spain_adapter
from .paper_adapter import PaperAdapter

__all__ = [
    "AlpacaAdapter",
    "CurrencyConverter",
    "IBAdapter",
    "IBConnection",
    "IBKRSpainAdapter",
    "PaperAdapter",
    "create_index_contract",
    "create_stock_contract",
    "get_currency_converter",
    "get_ib_adapter",
    "get_ibex35_symbols",
    "get_ibkr_spain_adapter",
    "is_ibex35_symbol",
]
