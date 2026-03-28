"""
Order Flow Imbalance (OFI) Module

This module implements Order Flow Imbalance calculations and predictions for
algorithmic trading, following the research by:

- Cont, R., & Kukanov, A. (2017) "Order Flow Imbalance and Price Movement"
- Aldridge, I. (2013) "High-Frequency Trading"
- Hasbrouck, J. (1991) "Measuring the Information Content of Stock Trades"

Key Features:
1. OFI calculation from order book snapshots
2. OFI prediction models for price movements
3. OFI-based trading signal generation
4. Tick-level OFI processing
5. Cumulative OFI (COFI) tracking
6. OFI momentum calculations

Example Usage:
    >>> from app.domain.market_analysis.microstructure.ofi import OFICalculator, OFIPredictor
    >>> calculator = OFICalculator()
    >>> ofi = calculator.calculate_ofi(order_book_snapshot)
    >>> predictor = OFIPredictor()
    >>> prediction = predictor.predict_direction(ofi, historical_ofi, historical_returns)
"""

from app.domain.market_analysis.microstructure.ofi.models import (
    CumulativeOFI,
    OFIConfig,
    OFIPrediction,
    OFISignal,
    OFISignalConfig,
    OrderBookSnapshot,
    TickData,
)
from app.domain.market_analysis.microstructure.ofi.ofi_calculator import OFICalculator
from app.domain.market_analysis.microstructure.ofi.ofi_predictor import OFIPredictor
from app.domain.market_analysis.microstructure.ofi.ofi_signals import OFISignalGenerator
from app.domain.market_analysis.microstructure.ofi.tick_processor import TickLevelOFIProcessor

__all__ = [
    # Models
    "OrderBookSnapshot",
    "TickData",
    "OFIConfig",
    "OFISignalConfig",
    "OFIPrediction",
    "OFISignal",
    "CumulativeOFI",
    # Main Classes
    "OFICalculator",
    "OFIPredictor",
    "OFISignalGenerator",
    "TickLevelOFIProcessor",
]
