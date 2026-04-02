"""
Market Universe Orchestrator - Centralizado para obtener, filtrar y pasar data a StrategyStockAllocator.

Este componente orquestra el flujo completo:
1. Obtiene tickers de mercados reales (S&P 500, IBEX 35, Crypto)
2. Descarga datos OHLCV
3. Filtra por liquidez y volatilidad
4. Pasa data filtrada a StrategyStockAllocator

Author: AlgoTrading System
Created: 2025-01-23
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.services.market_universe_loader import MarketUniverseLoader, get_market_universe_loader
from app.services.strategy_stock_allocator import AllocationResult, StrategyStockAllocator

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


class MarketUniverseOrchestrator:
    """
    Orquestador centralizado para el universo de mercado.

    Conecta:
    - MarketUniverseLoader (fuente de datos)
    - StrategyStockAllocator (consumidor de datos)

    Flujo:
    Mercados → MarketUniverseLoader → Download → Filter → StrategyStockAllocator → Allocation
    """

    def __init__(
        self,
        market_loader: MarketUniverseLoader | None = None,
        stock_allocator: StrategyStockAllocator | None = None,
    ):
        """
        Inicializar el orquestador.

        Args:
            market_loader: MarketUniverseLoader (opcional, usa singleton por defecto)
            stock_allocator: StrategyStockAllocator (opcional, crea uno nuevo por defecto)
        """
        self.market_loader = market_loader or get_market_universe_loader()
        self.stock_allocator = stock_allocator or StrategyStockAllocator()

        logger.info("MarketUniverseOrchestrator inicializado")

    async def get_universe_for_allocation(
        self,
        include_sp500: bool = True,
        include_nasdaq100: bool = False,
        include_ibex35: bool = False,
        include_crypto: bool = False,
        top_n_per_universe: int = 100,
        download_period: str = "6mo",
        download_interval: str = "1d",
        min_avg_volume: int = 1_000_000,
        min_price: float = 5.0,
        max_volatility: float = 0.15,
    ) -> dict[str, pd.DataFrame]:
        """
        Obtiene universo de mercado completo y filtrado para asignación.

        Flujo:
        1. Obtiene tickers de los mercados seleccionados
        2. Descarga datos OHLCV
        3. Filtra por liquidez y volatilidad
        4. Retorna data lista para StrategyStockAllocator

        Args:
            include_sp500: Incluir S&P 500
            include_nasdaq100: Incluir NASDAQ 100
            include_ibex35: Incluir IBEX 35
            include_crypto: Incluir criptomonedas
            top_n_per_universe: Top N tickers por universo
            download_period: Período de descarga (yfinance format)
            download_interval: Intervalo de datos (1d, 1h, etc.)
            min_avg_volume: Volumen promedio mínimo
            min_price: Precio mínimo
            max_volatility: Volatilidad máxima diaria

        Returns:
            Dict[str, pd.DataFrame]: Data filtrada lista para StrategyStockAllocator
        """
        logger.info("🔄 Iniciando obtención de universo de mercado...")

        # STEP 1: Obtener tickers de los universos
        all_tickers = await self.market_loader.get_combined_universe(
            include_sp500=include_sp500,
            include_nasdaq100=include_nasdaq100,
            include_ibex35=include_ibex35,
            include_crypto=include_crypto,
        )

        if not all_tickers:
            logger.error("❌ No se obtuvieron tickers de ningún universo")
            return {}

        # Limitar a top N por universo si es necesario
        if top_n_per_universe and len(all_tickers) > top_n_per_universe:
            all_tickers = all_tickers[:top_n_per_universe]

        logger.info(f"📊 Universe obtenido: {len(all_tickers)} tickers")

        # STEP 2: Descargar datos OHLCV
        logger.info(f"📥 Descargando datos para {len(all_tickers)} tickers...")
        raw_data = await self.market_loader.download_universe_data(
            tickers=all_tickers,
            period=download_period,
            interval=download_interval,
            progress=True,
        )

        if not raw_data:
            logger.error("❌ No se descargaron datos")
            return {}

        logger.info(f"✅ Datos descargados: {len(raw_data)} tickers con datos")

        # STEP 3: Filtrar por liquidez y volatilidad
        logger.info("🔍 Filtrando por liquidez y volatilidad...")
        filtered_data = await self.market_loader.filter_by_liquidity_volatility(
            data=raw_data,
            min_avg_volume=min_avg_volume,
            min_price=min_price,
            max_volatility=max_volatility,
        )

        logger.info(
            f"✅ Data filtrada: {len(filtered_data)}/{len(raw_data)} tickers pasaron filtros"
        )

        return filtered_data

    async def allocate_from_market_universe(
        self,
        total_capital: float,
        strategy_allocations: dict[str, float] | None = None,
        include_sp500: bool = True,
        include_nasdaq100: bool = False,
        include_ibex35: bool = False,
        include_crypto: bool = False,
        top_n_per_universe: int = 100,
        download_period: str = "6mo",
        download_interval: str = "1d",
        min_avg_volume: int = 1_000_000,
        min_price: float = 5.0,
        max_volatility: float = 0.15,
    ) -> AllocationResult:
        """
        Método completo: obtiene universo de mercado y asigna capital.

        Este es el método principal que orquestra todo el flujo:
        1. Obtiene tickers de mercados reales
        2. Descarga datos OHLCV
        3. Filtra por liquidez/volatilidad
        4. Pasa a StrategyStockAllocator para asignación

        Args:
            total_capital: Capital total a asignar
            strategy_allocations: Asignación por estrategia (opcional)
            include_sp500: Incluir S&P 500
            include_nasdaq100: Incluir NASDAQ 100
            include_ibex35: Incluir IBEX 35
            include_crypto: Incluir criptomonedas
            top_n_per_universe: Top N tickers por universo
            download_period: Período de descarga
            download_interval: Intervalo de datos
            min_avg_volume: Volumen mínimo
            min_price: Precio mínimo
            max_volatility: Volatilidad máxima

        Returns:
            AllocationResult con asignaciones completas
        """
        logger.info(f"🚀 Iniciando allocation desde mercado: ${total_capital:,.2f}")

        # STEP 1-3: Obtener universo filtrado
        filtered_data = await self.get_universe_for_allocation(
            include_sp500=include_sp500,
            include_nasdaq100=include_nasdaq100,
            include_ibex35=include_ibex35,
            include_crypto=include_crypto,
            top_n_per_universe=top_n_per_universe,
            download_period=download_period,
            download_interval=download_interval,
            min_avg_volume=min_avg_volume,
            min_price=min_price,
            max_volatility=max_volatility,
        )

        if not filtered_data:
            logger.error("❌ No hay datos para asignar")
            return AllocationResult(
                allocations={},
                pairs=[],
                residual_capital=total_capital,
                decision_logs=["No se obtuvieron datos filtrados del mercado"],
                validation_passed=False,
                validation_errors=["No hay datos disponibles"],
            )

        # STEP 4: Asignar usando StrategyStockAllocator
        logger.info("🎯 Asignando capital con StrategyStockAllocator...")
        allocation_result = self.stock_allocator.allocate(
            historical_data=filtered_data,
            total_capital=total_capital,
            strategy_allocations=strategy_allocations,
        )

        # Log resultados
        if allocation_result.validation_passed:
            logger.info(
                f"✅ Allocation completada: {len(allocation_result.allocations)} activos, "
                f"${allocation_result.residual_capital:,.2f} residual"
            )
        else:
            logger.warning(f"⚠️ Allocation falló validación: {allocation_result.validation_errors}")

        return allocation_result

    async def get_sp500_for_allocation(
        self,
        total_capital: float,
        strategy_allocations: dict[str, float] | None = None,
        top_n: int = 100,
        **kwargs,
    ) -> AllocationResult:
        """
        Shortcut: Obtiene S&P 500 y asigna capital.

        Args:
            total_capital: Capital total
            strategy_allocations: Asignación por estrategia
            top_n: Top N tickers del S&P 500
            **kwargs: Parámetros adicionales de filtrado

        Returns:
            AllocationResult con asignaciones
        """
        logger.info(f"📈 Obteniendo S&P 500 (top {top_n}) para allocation...")
        return await self.allocate_from_market_universe(
            total_capital=total_capital,
            strategy_allocations=strategy_allocations,
            include_sp500=True,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=False,
            top_n_per_universe=top_n,
            **kwargs,
        )

    async def get_ibex35_for_allocation(
        self,
        total_capital: float,
        strategy_allocations: dict[str, float] | None = None,
        top_n: int = 35,
        **kwargs,
    ) -> AllocationResult:
        """
        Shortcut: Obtiene IBEX 35 y asigna capital.

        Args:
            total_capital: Capital total
            strategy_allocations: Asignación por estrategia
            top_n: Top N tickers del IBEX 35
            **kwargs: Parámetros adicionales de filtrado

        Returns:
            AllocationResult con asignaciones
        """
        logger.info(f"🇪🇸 Obteniendo IBEX 35 (top {top_n}) para allocation...")
        return await self.allocate_from_market_universe(
            total_capital=total_capital,
            strategy_allocations=strategy_allocations,
            include_sp500=False,
            include_nasdaq100=False,
            include_ibex35=True,
            include_crypto=False,
            top_n_per_universe=top_n,
            **kwargs,
        )

    async def get_crypto_for_allocation(
        self,
        total_capital: float,
        strategy_allocations: dict[str, float] | None = None,
        top_n: int = 20,
        **kwargs,
    ) -> AllocationResult:
        """
        Shortcut: Obtiene Crypto y asigna capital.

        Args:
            total_capital: Capital total
            strategy_allocations: Asignación por estrategia
            top_n: Top N criptomonedas
            **kwargs: Parámetros adicionales de filtrado

        Returns:
            AllocationResult con asignaciones
        """
        logger.info(f"₿ Obteniendo Crypto (top {top_n}) para allocation...")
        return await self.allocate_from_market_universe(
            total_capital=total_capital,
            strategy_allocations=strategy_allocations,
            include_sp500=False,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=True,
            top_n_per_universe=top_n,
            **kwargs,
        )

    async def get_mixed_universe_for_allocation(
        self,
        total_capital: float,
        strategy_allocations: dict[str, float] | None = None,
        sp500_top: int = 50,
        crypto_top: int = 10,
        **kwargs,
    ) -> AllocationResult:
        """
        Shortcut: Obtiene universo mixto (S&P 500 + Crypto) y asigna capital.

        Args:
            total_capital: Capital total
            strategy_allocations: Asignación por estrategia
            sp500_top: Top N del S&P 500
            crypto_top: Top N de criptomonedas
            **kwargs: Parámetros adicionales de filtrado

        Returns:
            AllocationResult con asignaciones
        """
        logger.info(f"🌐 Obteniendo universo mixto (S&P 500: {sp500_top}, Crypto: {crypto_top})...")
        return await self.allocate_from_market_universe(
            total_capital=total_capital,
            strategy_allocations=strategy_allocations,
            include_sp500=True,
            include_nasdaq100=False,
            include_ibex35=False,
            include_crypto=True,
            top_n_per_universe=max(sp500_top, crypto_top),
            **kwargs,
        )


# ============================================================================
# GLOBAL SINGLETON
# ============================================================================

_market_universe_orchestrator: MarketUniverseOrchestrator | None = None


def get_market_universe_orchestrator() -> MarketUniverseOrchestrator:
    """
    Get the global MarketUniverseOrchestrator instance.

    Returns:
        MarketUniverseOrchestrator: Global orchestrator instance
    """
    global _market_universe_orchestrator
    if _market_universe_orchestrator is None:
        _market_universe_orchestrator = MarketUniverseOrchestrator()
        logger.info("✅ MarketUniverseOrchestrator global instance created")
    return _market_universe_orchestrator
