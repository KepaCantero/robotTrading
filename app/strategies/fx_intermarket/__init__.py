"""
FX Intermarket Strategy Module.

This module implements an FX trading strategy based on intermarket relationships
and correlations between FX pairs and external asset classes (equities, commodities,
fixed income, etc.).

The strategy exploits known intermarket relationships:
- Safe haven flows: JPY/CHF appreciate when equities decline
- Commodity linkages: AUD/CAD/NZD track commodity prices
- Carry trade dynamics: High-yield currencies correlate with equities
- Yield differential: Interest rate differentials drive currency movements

Components:
    - models: Data models for correlations, relationships, and signals
    - correlation_analyzer: Statistical correlation analysis engine
    - fx_intermarket_strategy: Main strategy implementation

Examples:
    >>> from app.strategies.fx_intermarket import (
    ...     FXIntermarketStrategy,
    ...     FXIntermarketConfig,
    ...     CorrelationAnalyzer,
    ... )
    >>> config = FXIntermarketConfig(
    ...     correlation_lookback=60,
    ...     min_correlation=Decimal("0.7"),
    ... )
    >>> strategy = FXIntermarketStrategy(config=config)
"""

from app.strategies.fx_intermarket.correlation_analyzer import (
    CorrelationAnalyzer,
)
from app.strategies.fx_intermarket.fx_intermarket_strategy import (
    FXIntermarketStrategy,
)
from app.strategies.fx_intermarket.models import (
    AssetClass,
    FXCorrelationPair,
    FXIntermarketConfig,
    IntermarketRelationship,
    IntermarketSignal,
    RelationshipType,
)

__all__ = [
    # Strategy
    "FXIntermarketStrategy",
    # Configuration
    "FXIntermarketConfig",
    # Data Models
    "AssetClass",
    "RelationshipType",
    "FXCorrelationPair",
    "IntermarketRelationship",
    "IntermarketSignal",
    # Analyzer
    "CorrelationAnalyzer",
]
