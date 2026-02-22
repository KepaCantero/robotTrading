"""Market Making Module

This module provides market making strategies and models for algorithmic trading.
It implements high-frequency market making techniques including the Avellaneda-Stoikov
model and related inventory management approaches.

Key Components:
- AvellanedaStoikov: Optimal market making with inventory risk management
- Quote generation: Dynamic bid/ask quote calculation
- Inventory management: Position and risk control

References:
- Avellaneda, M. & Stoikov, S. (2008) "High-frequency trading in a limit order book"
- Guéant, O., Lehalle, C.A. & Fernandez-Tapia, J. (2013) "Dealing with inventory risk"
"""

from app.domain.trading.market_making.avellaneda_stoikov import (
    ASConfig,
    ASQuote,
    ASQuoteGenerator,
    ASQuoteParams,
    AvellanedaStoikovModel,
    InventoryConfig,
    InventoryManager,
    InventoryState,
)

__all__ = [
    "ASConfig",
    "ASQuote",
    "ASQuoteGenerator",
    "ASQuoteParams",
    "AvellanedaStoikovModel",
    "InventoryConfig",
    "InventoryManager",
    "InventoryState",
]
