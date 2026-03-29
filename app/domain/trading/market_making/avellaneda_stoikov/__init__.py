"""Avellaneda-Stoikov Market Making Model

This module implements the Avellaneda-Stoikov model for high-frequency market making.
The model provides optimal bid/ask quotes that account for inventory risk and volatility.

Key Features:
- Reservation price calculation with inventory adjustment
- Optimal spread calculation balancing risk and profit
- Dynamic quote generation
- Inventory management and risk control

Mathematical Foundation:

1. Reservation Price (inventory-adjusted mid):
   r(s) = s - (gamma * sigma^2 / k) * q * (T - t) / T

   Where:
   - s: Current mid price
   - gamma (gamma): Risk aversion parameter
   - sigma (sigma): Volatility of the asset
   - k: Order book depth parameter
   - q: Current inventory (positive = long, negative = short)
   - T: Total time horizon
   - t: Current time

2. Optimal Spread:
   delta* = (gamma * sigma^2 / k) * (T - t) + (2/gamma) * ln(1 + gamma/2)

   The spread has two components:
   - Inventory risk term: Increases with time remaining and volatility
   - Adverse selection term: Constant for given risk aversion

3. Bid/Ask Quotes:
   - Bid: r(s) - delta*/2
   - Ask: r(s) + delta*/2

References:
- Avellaneda, M. & Stoikov, S. (2008) "High-frequency trading in a limit order book"
- Guéant, O., Lehalle, C.A. & Fernandez-Tapia, J. (2013) "Dealing with inventory risk"
"""

from app.domain.trading.market_making.avellaneda_stoikov.as_model import (
    ASConfig,
    ASQuote,
    AvellanedaStoikovModel,
)
from app.domain.trading.market_making.avellaneda_stoikov.inventory_manager import (
    InventoryConfig,
    InventoryManager,
    InventoryState,
)
from app.domain.trading.market_making.avellaneda_stoikov.models import ASQuoteParams
from app.domain.trading.market_making.avellaneda_stoikov.quote_generator import ASQuoteGenerator

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
