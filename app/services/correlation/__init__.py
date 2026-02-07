"""
Real-Time Correlation Matrix Service - Phase 2.4

This module provides real-time correlation calculation from historical prices,
replacing simulated correlation (0.3 if same sector) with actual correlation
calculated from historical price movements.

Key Features:
- Calculate correlation matrix from historical returns (60-day lookback)
- Update correlation every hour
- Cache for performance
- Use in portfolio risk calculations
- Fallback to simulated if data unavailable
"""

from app.services.correlation.analyzer import CorrelationAnalyzer, CorrelationConfig

__all__ = [
    "CorrelationAnalyzer",
    "CorrelationConfig",
]
