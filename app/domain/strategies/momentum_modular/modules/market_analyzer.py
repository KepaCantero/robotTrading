"""
Market Analyzer Module

Re-exports MarketAnalyzer from the main modules package for backward compatibility.
"""

from app.domain.strategies.modules.market_analyzer import MarketAnalyzer

__all__ = ["MarketAnalyzer"]
