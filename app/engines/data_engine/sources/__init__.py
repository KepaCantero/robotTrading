"""
Data Sources - Implementaciones de fuentes de datos.

Fuentes soportadas:
- OHLCV: IBKR, Binance, Alpaca, Polygon, Yahoo Finance, Alpha Vantage
- Fundamentales: Financial Modeling Prep, Alpha Vantage
- Sentimiento: Twitter API, Reddit API, News APIs
- Opciones: Volatility surfaces
"""

from .base_source import BaseDataSource
from .fundamental_sources import AlphaVantageFundamentalSource, FinancialModelingPrepSource
from .ohlcv_sources import AlpacaSource, BinanceSource, IBKRSource, PolygonSource
from .options_sources import OptionsVolatilitySource
from .sentiment_sources import NewsSentimentSource, RedditSentimentSource, TwitterSentimentSource

__all__ = [
    "BaseDataSource",
    "IBKRSource",
    "BinanceSource",
    "AlpacaSource",
    "PolygonSource",
    "FinancialModelingPrepSource",
    "AlphaVantageFundamentalSource",
    "TwitterSentimentSource",
    "RedditSentimentSource",
    "NewsSentimentSource",
    "OptionsVolatilitySource",
]
