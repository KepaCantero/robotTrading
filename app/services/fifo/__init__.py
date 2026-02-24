"""
FIFO (First-In, First-Out) Tax Tracking Services

CRITICAL FOR SPAIN RESIDENTS:
- Modelo 721: Cryptocurrency holdings reporting (MANDATORY, ANY amount)
- FIFO tracking: LEGAL REQUIREMENT for Hacienda (Spanish tax authority)
- Multi-exchange tracking: Binance, Coinbase, Kraken, Ledger, etc.
- Accurate cost basis calculation for capital gains

This package integrates FIFO tax lot tracking with the live trading system,
ensuring all trades are recorded for tax compliance purposes.

Architecture:
- Async integration with live trading via events
- PostgreSQL persistence via FIFO schema (app.tax.database.fifo_schema)
- Modelo 721 report generation for annual tax filing
- Dec 31 balance snapshots for crypto holdings

Author: Claude (FIFO Database Integration - Phase 2.1)
Date: 2026-01-25
Status: IMPLEMENTATION
"""

from .fifo_integrator import FIFOIntegrator
from .modelo_721_generator import Modelo721Generator

__all__ = [
    "FIFOIntegrator",
    "Modelo721Generator",
]
