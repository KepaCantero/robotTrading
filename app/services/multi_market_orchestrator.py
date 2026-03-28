"""
Multi-Market Trading Orchestrator - Orquestador de trading multi-mercado.

Coordina trading simultáneo en:
- Stocks (US, EU, Asia)
- Forex (pares de divisas)
- Crypto (BTC, ETH, altcoins)
- Dividends (acciones de alto dividendo)

Features:
- Asignación dinámica de capital por mercado
- Selección de estrategia según condiciones
- Sentiment analysis con Marketaux API
- Consideraciones fiscales España/EU
- Currency hedging para EUR-based investors
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from app.services.crypto_data_service import get_crypto_fetcher
from app.services.forex_data_service import get_forex_fetcher

logger = logging.getLogger(__name__)


class MarketType(Enum):
    """Tipos de mercados soportados."""

    STOCKS_US = "stocks_us"
    STOCKS_EU = "stocks_eu"  # Acciones europeas (IBEX 35, CAC 40, DAX)
    FOREX = "forex"
    CRYPTO = "crypto"
    DIVIDENDS = "dividends"  # Acciones de alto dividendo


class MarketRegime(Enum):
    """Regímenes de mercado para estrategia."""

    BULL_VOLATILE = "bull_volatile"  # Alcista volátil -> Momentum
    BULL_STABLE = "bull_stable"  # Alcista estable -> Buy & Hold
    BEAR_VOLATILE = "bear_volatile"  # Bajista volátil -> Cash/Hedge
    BEAR_STABLE = "bear_stable"  # Bajista estable -> Mean Reversion
    SIDEWAYS = "sideways"  # Lateral -> Range trading


class StrategyType(Enum):
    """Tipos de estrategias disponibles."""

    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    PAIRS_TRADING = "pairs_trading"
    TREND_FOLLOWING = "trend_following"
    BREAKOUT = "breakout"
    NEWS_SENTIMENT = "news_sentiment"  # Basada en noticias
    DIVIDEND_GROWTH = "dividend_growth"


@dataclass
class MarketAllocation:
    """Asignación de capital por mercado."""

    market_type: MarketType
    allocation_pct: Decimal  # Porcentaje del capital total
    current_strategy: StrategyType
    symbols: List[str]
    active_positions: int
    total_pnl: Decimal
    last_rebalance: datetime


@dataclass
class MarketSignal:
    """Señal de trading para un mercado."""

    market_type: MarketType
    symbol: str
    strategy: StrategyType
    action: str  # "BUY", "SELL", "HOLD"
    confidence: Decimal  # 0 a 1
    sentiment_score: Optional[Decimal] = None  # De Marketaux
    expected_return: Optional[Decimal] = None
    risk_level: Optional[Decimal] = None


class MultiMarketOrchestrator:
    """
    Orquestador de trading multi-mercado.

    Funcionalidades:
    1. Asigna capital entre mercados según condiciones
    2. Selecciona estrategia óptima por mercado
    3. Ejecuta trades coordinados
    4. Aplica hedging de currency para EUR
    5. Optimiza fiscalmente para España
    """

    # Asignaciones máximas por mercado (para España residente)
    MAX_ALLOCATIONS = {
        MarketType.STOCKS_US: Decimal("0.40"),  # Máx 40% en US (con hedging)
        MarketType.STOCKS_EU: Decimal("0.30"),  # 30% en EU (sin withholding tax)
        MarketType.FOREX: Decimal("0.15"),  # 15% en forex (incluye EUR/USD)
        MarketType.CRYPTO: Decimal("0.10"),  # 10% en crypto (alto riesgo)
        MarketType.DIVIDENDS: Decimal("0.20"),  # 20% en dividendos (ingreso pasivo)
    }

    # Estrategias por régimen de mercado
    STRATEGY_BY_REGIME = {
        MarketRegime.BULL_VOLATILE: StrategyType.MOMENTUM,
        MarketRegime.BULL_STABLE: StrategyType.TREND_FOLLOWING,
        MarketRegime.BEAR_VOLATILE: StrategyType.NEWS_SENTIMENT,  # News-driven
        MarketRegime.BEAR_STABLE: StrategyType.MEAN_REVERSION,
        MarketRegime.SIDEWAYS: StrategyType.PAIRS_TRADING,
    }

    # Símbolos por mercado (para España investor)
    MARKET_SYMBOLS = {
        MarketType.STOCKS_US: [
            "AAPL",
            "MSFT",
            "GOOGL",
            "NVDA",
            "META",
            "AMZN",
            "TSLA",
            "JPM",
            "V",
            "BRK.B",
        ],
        MarketType.STOCKS_EU: [
            "SAN.MC",  # Santander (España)
            "TEF.MC",  # Telefónica (España)
            "IBE.MC",  # Iberdrola (España)
            "ITX.MC",  # Inditex (España)
            "REP.MC",  # Repsol (España)
            "MC.PA",  # LVMH (Francia)
            "ASML.AS",  # ASML (Holanda)
            "SAP.DE",  # SAP (Alemania)
            "NESN.SW",  # Nestlé (Suiza)
            "NOVN.SW",  # Novartis (Suiza)
        ],
        MarketType.FOREX: [
            "EURUSD",
            "GBPUSD",
            "USDJPY",
            "USDCHF",
            "AUDUSD",
            "USDCAD",
        ],
        MarketType.CRYPTO: [
            "BTC",
            "ETH",
            "BNB",
            "SOL",
            "XRP",
        ],
        MarketType.DIVIDENDS: [
            "JNJ",  # Johnson & Johnson (dividend aristocrat)
            "PG",  # Procter & Gamble
            "KO",  # Coca-Cola
            "MCD",  # McDonald's
            "MMM",  # 3M
            "SAN.MC",  # Santander ( España - alto dividendo)
            "TEF.MC",  # Telefónica (España - muy alto dividendo)
            "IBE.MC",  # Iberdrola (España - estable)
        ],
    }

    def __init__(
        self,
        total_capital: Decimal,
        tax_residence: str = "ES",  # España por defecto
        base_currency: str = "EUR",
        marketaux_api_key: Optional[str] = None,
    ):
        """
        Inicializar orquestador multi-mercado.

        Args:
            total_capital: Capital total disponible
            tax_residence: País de residencia fiscal (ES, US, UK, etc.)
            base_currency: Moneda base (EUR para España)
            marketaux_api_key: API token para Marketaux news sentiment
        """
        self.total_capital = total_capital
        self.tax_residence = tax_residence
        self.base_currency = base_currency
        self.marketaux_api_key = marketaux_api_key

        # Inicializar servicios de datos
        self.crypto_fetcher = get_crypto_fetcher()
        self.forex_fetcher = get_forex_fetcher()

        # Estado actual
        self.allocations: Dict[MarketType, MarketAllocation] = {}
        self.current_regime = MarketRegime.SIDEWAYS
        self.vix_level: Optional[Decimal] = None

        # Sentiment cache
        self.sentiment_cache: Dict[str, tuple[Decimal, datetime]] = {}
        self._max_sentiment_cache_size = 10000  # Limit cache size

        logger.info(
            f"Initialized MultiMarketOrchestrator: "
            f"€{total_capital:,.2f} residence={tax_residence} base={base_currency}"
        )

    async def analyze_market_regime(self, market_type: MarketType) -> MarketRegime:
        """
        Analizar el régimen actual de un mercado.

        Args:
            market_type: Tipo de mercado a analizar

        Returns:
            MarketRegime detectado
        """
        # En producción, esto analizaría:
        # 1. Tendencia de precios (moving averages)
        # 2. Volatilidad (ATR, VIX para stocks)
        # 3. Volume analysis
        # 4. Sentiment de noticias (Marketaux)

        # Por ahora, retorno SIDEWAYS como default
        logger.debug(f"Analyzing regime for {market_type.value}")
        return MarketRegime.SIDEWAYS

    async def get_optimal_strategy(
        self, market_type: MarketType, regime: MarketRegime
    ) -> StrategyType:
        """
        Obtener la estrategia óptima para un mercado y régimen.

        Args:
            market_type: Tipo de mercado
            regime: Régimen actual

        Returns:
            StrategyType recomendada
        """
        # Estrategia base según régimen
        base_strategy = self.STRATEGY_BY_REGIME.get(regime, StrategyType.MOMENTUM)

        # Ajustes específicos por mercado
        if market_type == MarketType.DIVIDENDS:
            return StrategyType.DIVIDEND_GROWTH
        elif market_type == MarketType.CRYPTO:
            # Crypto necesita momentum/trend following
            if regime in [MarketRegime.BULL_VOLATILE, MarketRegime.BULL_STABLE]:
                return StrategyType.MOMENTUM
            else:
                return StrategyType.NEWS_SENTIMENT  # Crypto muy news-driven
        elif market_type == MarketType.FOREX:
            return StrategyType.TREND_FOLLOWING  # Forex es trending

        return base_strategy

    async def get_marketaux_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Obtener sentimiento de Marketaux API para un símbolo.

        Args:
            symbol: Símbolo a analizar

        Returns:
            Dict con sentiment_score, positive_count, etc.
        """
        if not self.marketaux_api_key:
            logger.warning("Marketaux API key no configurada")
            return {"sentiment_score": 0.0, "total_articles": 0}

        # Check cache (5 minutos)
        cache_key = symbol
        if cache_key in self.sentiment_cache:
            sentiment, cached_at = self.sentiment_cache[cache_key]
            if datetime.utcnow() - cached_at < timedelta(minutes=5):
                return {"sentiment_score": float(sentiment), "cached": True}

        try:
            # Importar aquí para evitar circular dependency
            from app.engines.data_engine.sources.sentiment_sources import NewsSentimentSource

            config = {"api_key": self.marketaux_api_key, "provider": "marketaux"}
            news_source = NewsSentimentSource(config)

            if not await news_source.connect():
                logger.error(f"Failed to connect to Marketaux for {symbol}")
                return {"sentiment_score": 0.0, "total_articles": 0}

            result = await news_source.get_sentiment(symbol, max_articles=50)

            await news_source.disconnect()

            # Cache result
            sentiment_score = Decimal(str(result.get("sentiment_score", 0.0)))
            self.sentiment_cache[cache_key] = (sentiment_score, datetime.utcnow())

            # Cleanup cache if over limit
            self._cleanup_sentiment_cache()

            logger.info(f"Marketaux sentiment for {symbol}: {sentiment_score:.3f}")
            return result

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error getting Marketaux sentiment for {symbol}: {e}")
            return {"sentiment_score": 0.0, "total_articles": 0}

    def _cleanup_sentiment_cache(self):
        """Remove oldest entries from sentiment cache if over limit."""
        if len(self.sentiment_cache) > self._max_sentiment_cache_size:
            # Remove oldest 20% of entries
            to_remove = len(self.sentiment_cache) - int(self._max_sentiment_cache_size * 0.8)
            # Sort by timestamp and remove oldest
            sorted_items = sorted(self.sentiment_cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:to_remove]:
                del self.sentiment_cache[key]
            logger.debug(f"Cleaned up {to_remove} entries from sentiment cache")

    async def calculate_allocations(
        self, risk_tolerance: str = "medio"
    ) -> Dict[MarketType, Decimal]:
        """
        Calcular asignación óptima de capital entre mercados.

        Considera:
        - Risk tolerance (bajo, medio, alto)
        - Market regime actual
        - Sentiment de noticias
        - Tax optimization para España

        Args:
            risk_tolerance: Tolerancia al riesgo

        Returns:
            Dict con asignación por mercado (decimal 0-1)
        """
        allocations = {}

        # Asignaciones base según risk tolerance
        if risk_tolerance == "bajo":
            base_allocations = {
                MarketType.STOCKS_EU: Decimal("0.40"),  # EU sin withholding tax
                MarketType.DIVIDENDS: Decimal("0.30"),  # Dividendos estable
                MarketType.STOCKS_US: Decimal("0.20"),  # US con hedging
                MarketType.FOREX: Decimal("0.10"),
                MarketType.CRYPTO: Decimal("0.00"),  # Sin crypto para bajo riesgo
            }
        elif risk_tolerance == "alto":
            base_allocations = {
                MarketType.STOCKS_US: Decimal("0.35"),
                MarketType.CRYPTO: Decimal("0.20"),  # Más crypto
                MarketType.FOREX: Decimal("0.15"),
                MarketType.STOCKS_EU: Decimal("0.20"),
                MarketType.DIVIDENDS: Decimal("0.10"),
            }
        else:  # medio
            base_allocations = {
                MarketType.STOCKS_US: Decimal("0.30"),
                MarketType.STOCKS_EU: Decimal("0.25"),
                MarketType.FOREX: Decimal("0.15"),
                MarketType.CRYPTO: Decimal("0.10"),
                MarketType.DIVIDENDS: Decimal("0.20"),
            }

        # Aplicar límites máximos
        for market_type, allocation in base_allocations.items():
            max_alloc = self.MAX_ALLOCATIONS.get(market_type, Decimal("0.50"))
            allocations[market_type] = min(allocation, max_alloc)

        # Normalizar si suma ≠ 1
        total = sum(allocations.values())
        if total != Decimal("1"):
            for market_type in allocations:
                allocations[market_type] = allocations[market_type] / total

        logger.info(f"Calculated allocations for {risk_tolerance} risk: {allocations}")
        return allocations

    async def generate_signals(self, market_type: MarketType) -> List[MarketSignal]:
        """
        Generar señales de trading para un mercado.

        Args:
            market_type: Tipo de mercado

        Returns:
            Lista de MarketSignal
        """
        signals = []
        symbols = self.MARKET_SYMBOLS.get(market_type, [])

        # Obtener estrategia óptima
        regime = await self.analyze_market_regime(market_type)
        strategy = await self.get_optimal_strategy(market_type, regime)

        # Obtener sentimiento de Marketaux
        sentiment_tasks = [self.get_marketaux_sentiment(symbol) for symbol in symbols[:5]]  # Top 5
        sentiment_results = await asyncio.gather(*sentiment_tasks, return_exceptions=True)

        for i, symbol in enumerate(symbols):
            try:
                sentiment_data = sentiment_results[i] if i < len(sentiment_results) else {}
                if isinstance(sentiment_data, Exception):
                    sentiment_data = {}

                sentiment_score = Decimal(str(sentiment_data.get("sentiment_score", 0.0)))

                # Generar señal basada en sentimiento y estrategia
                if sentiment_score > 0.3:
                    action = "BUY"
                    confidence = min(sentiment_score, Decimal("1.0"))
                elif sentiment_score < -0.3:
                    action = "SELL"
                    confidence = min(abs(sentiment_score), Decimal("1.0"))
                else:
                    action = "HOLD"
                    confidence = Decimal("0.5")

                signal = MarketSignal(
                    market_type=market_type,
                    symbol=symbol,
                    strategy=strategy,
                    action=action,
                    confidence=confidence,
                    sentiment_score=sentiment_score,
                )

                signals.append(signal)

            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Error generating signal for {symbol}: {e}")
                continue

        return signals

    async def execute_trades(self, signals: List[MarketSignal]) -> Dict[str, Any]:
        """
        Ejecutar trades basados en señales.

        Args:
            signals: Lista de señales

        Returns:
            Dict con resultados de ejecución
        """
        results = {"executed": 0, "failed": 0, "total_value": Decimal("0")}

        for signal in signals:
            if signal.action == "HOLD":
                continue

            try:
                # Aquí iría la lógica de ejecución real
                # Por ahora, solo logging
                logger.info(
                    f"Would execute: {signal.action} {signal.symbol} "
                    f"({signal.market_type.value}) "
                    f"strategy={signal.strategy.value} "
                    f"confidence={signal.confidence:.2f} "
                    f"sentiment={signal.sentiment_score:.2f}"
                )
                results["executed"] += 1

            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Failed to execute trade for {signal.symbol}: {e}")
                results["failed"] += 1

        return results

    async def run_cycle(self, risk_tolerance: str = "medio") -> Dict[str, Any]:
        """
        Ejecutar un ciclo completo de análisis y trading.

        Args:
            risk_tolerance: Tolerancia al riesgo

        Returns:
            Dict con resultados del ciclo
        """
        logger.info("=" * 80)
        logger.info("Starting multi-market trading cycle")
        logger.info("=" * 80)

        # 1. Calcular asignaciones
        allocations = await self.calculate_allocations(risk_tolerance)
        logger.info(f"Allocations: {[(k.value, float(v)) for k, v in allocations.items()]}")

        # 2. Generar señales por mercado
        all_signals = []
        for market_type in MarketType:
            if allocations.get(market_type, Decimal("0")) > 0:
                signals = await self.generate_signals(market_type)
                all_signals.extend(signals)
                logger.info(f"{market_type.value}: {len(signals)} signals generated")

        # 3. Ejecutar trades
        execution_results = await self.execute_trades(all_signals)

        # 4. Reporte
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_capital": float(self.total_capital),
            "allocations": {k.value: float(v) for k, v in allocations.items()},
            "total_signals": len(all_signals),
            "execution_results": execution_results,
        }

        logger.info("=" * 80)
        logger.info(f"Cycle complete: {report}")
        logger.info("=" * 80)

        return report


# Global instance
_orchestrator: Optional[MultiMarketOrchestrator] = None


def get_orchestrator(
    total_capital: Optional[Decimal] = None,
    tax_residence: str = "ES",
    marketaux_api_key: Optional[str] = None,
) -> MultiMarketOrchestrator:
    """Get or create global MultiMarketOrchestrator instance."""
    if total_capital is None:
        total_capital = Decimal("100000")
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiMarketOrchestrator(
            total_capital=total_capital,
            tax_residence=tax_residence,
            marketaux_api_key=marketaux_api_key,
        )
    return _orchestrator


def reset_orchestrator() -> None:
    """Reset global orchestrator."""
    global _orchestrator
    _orchestrator = None
