"""
Data Sources - Implementaciones de fuentes de datos.

Fuentes soportadas:
- OHLCV: IBKR, Binance, Alpaca, Polygon, Yahoo Finance, Alpha Vantage
- Fundamentales: Financial Modeling Prep, Alpha Vantage
- Sentimiento: Twitter API, Reddit API, News APIs
- Opciones: Volatility surfaces
"""

from .base_source import BaseDataSource
from .ohlcv_sources import (
    IBKRSource,
    BinanceSource,
    AlpacaSource,
    PolygonSource
)
from .fundamental_sources import (
    FinancialModelingPrepSource,
    AlphaVantageFundamentalSource
)
from .sentiment_sources import (
    TwitterSentimentSource,
    RedditSentimentSource,
    NewsSentimentSource
)
from .options_sources import (
    OptionsVolatilitySource
)

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
    "OptionsVolatilitySource"
]

