"""Catálogo ÚNICO de estrategias backtesteables del producto.

Nombre → ``"module:Class"`` (resuelto por importlib en el consumidor). Es
la única fuente de verdad de qué estrategias existen y dónde viven:

- ``BacktestOrchestrator._STRATEGIES`` (camino productivo: swarm y home)
- ``StrategyFactory._register_default_strategies`` (camino use_cases)

Antes había dos registros independientes que divergían (el orchestrator
no conocía pairs; el factory no conocía dividend/low_vol/static) y un
tercero vacío en el DI container. Cualquier estrategia nueva se registra
AQUÍ y solo aquí.
"""

from __future__ import annotations

STRATEGY_CATALOG: dict[str, str] = {
    "mean_reversion": "app.domain.strategies.mean_reversion:MeanReversionStrategy",
    "momentum_modular": "app.domain.strategies.strategy:ModularMomentumStrategy",
    # objetivo maximo dividendo: core-satellite evidenciado. Precios
    # ajustados → el momentum incluye las distribuciones (dividend
    # momentum, RFS 2026). La gemela "dividend_etf_rotation" se eliminó:
    # rotación top-3 demostradamente inferior al core-satellite y al
    # pasivo (rotation ≠ alpha, 37-ETF VectorBT).
    "dividend_tracking": "app.domain.strategies.dividend_core_satellite:DividendCoreSatelliteStrategy",
    # objetivo preservar capital: anomalía de baja volatilidad (tramo de
    # menor vol realizada del universo sectorial, equiponderado) —
    # Blitz & van Vliet 2007, Baker/Bradley/Wurgler 2011.
    "low_volatility": "app.domain.strategies.low_volatility:LowVolatilityStrategy",
    # conclusión ejecutable del protocolo cuantitativo (criterio 6):
    # cuando el equiponderado pasivo batió a toda gestión medida, la
    # cartera desplegable ES el pasivo
    "static_ew": "app.domain.strategies.static_ew:StaticEqualWeightStrategy",
    # pares cointegrados (spread z-score + correlación): el engine vive en
    # app/engines pero ES un BaseStrategy completo y testeado — ve el
    # timeline intercalado de ambos símbolos (is_cross_sectional)
    "pairs_trading": "app.engines.strategy_engines.pairs_engine:PairsTradingStrategyEngine",
}


def resolve_strategy(path: str) -> type:
    """Resuelve una entrada ``"module:Class"`` del catálogo a su clase."""
    import importlib

    module_path, class_name = path.split(":")
    return getattr(importlib.import_module(module_path), class_name)
