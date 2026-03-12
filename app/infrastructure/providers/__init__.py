"""
Portfolio providers.

This module exports portfolio providers for different brokers and trading modes.
"""

import logging

logger = logging.getLogger(__name__)

from .paper_trading import PaperTradingPortfolioProvider

__all__ = [
    "PaperTradingPortfolioProvider",
]

logger.debug(
    "Providers module initialized",
    extra={
        "component": "providers",
        "operation": "module_init",
        "exports": __all__,
    }
)
