"""
Risk Attribution

Implementa risk attribution:
- Descomponer riesgo por fuente (estrategia, activo, factor)
- Factor risk models (Fama-French, APT)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import numpy as np

from app.domain.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class BaseRiskAttributor(ABC):
    """Clase base para risk attributors."""

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar risk attributor.

        Args:
            config: Configuración del attributor
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def attribute_risk(self, portfolio: Portfolio, **kwargs) -> dict[str, Any]:
        """
        Atribuir riesgo del portfolio.

        Args:
            portfolio: Portfolio a analizar
            **kwargs: Argumentos adicionales

        Returns:
            Risk attribution
        """


class RiskAttributor(BaseRiskAttributor):
    """
    Risk Attributor principal.

    Descompone riesgo por múltiples fuentes.
    """

    def __init__(self, config: dict[str, Any]):
        """Inicializar risk attributor."""
        super().__init__(config)

        # Configuración de modelos
        self.use_factor_models = config.get("use_factor_models", True)
        self.use_strategy_attribution = config.get("use_strategy_attribution", True)
        self.use_asset_attribution = config.get("use_asset_attribution", True)

        # Factores para modelo Fama-French (simplificado)
        self.factors = ["market", "size", "value", "momentum"]

    def attribute_risk(
        self,
        portfolio: Portfolio,
        returns_history: Optional[dict[str, list[float]]] = None,
        strategy_allocations: Optional[dict[str, list[str]]] = None,
        factor_data: Optional[dict[str, list[float]]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Atribuir riesgo completo del portfolio.

        Args:
            portfolio: Portfolio a analizar
            returns_history: Historial de retornos por símbolo
            strategy_allocations: Asignación de símbolos por estrategia
            factor_data: Datos de factores de riesgo (opcional)
            **kwargs: Argumentos adicionales

        Returns:
            Risk attribution completo
        """
        try:
            attribution: dict[str, Any] = {}

            # Atribución por activo
            if self.use_asset_attribution:
                asset_attribution = self._attribute_by_asset(portfolio, returns_history)
                attribution["by_asset"] = asset_attribution

            # Atribución por estrategia
            if self.use_strategy_attribution and strategy_allocations:
                strategy_attribution = self._attribute_by_strategy(
                    portfolio, strategy_allocations, returns_history
                )
                attribution["by_strategy"] = strategy_attribution

            # Atribución por factores
            if self.use_factor_models:
                factor_attribution = self._attribute_by_factors(
                    portfolio, returns_history, factor_data
                )
                attribution["by_factor"] = factor_attribution

            # Resumen
            attribution["summary"] = self._generate_summary(attribution)
            attribution["timestamp"] = datetime.utcnow().isoformat()

            return attribution
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            self.logger.error(f"Error atribuyendo riesgo: {e}", exc_info=True)
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    def _attribute_by_asset(
        self, portfolio: Portfolio, returns_history: Optional[dict[str, list[float]]]
    ) -> dict[str, Any]:
        """Atribuir riesgo por activo."""
        if portfolio.total_equity == 0:
            return {"attributions": {}, "total_risk": 0.0}

        attributions = {}
        total_risk = 0.0

        for position in portfolio.positions:
            # Calcular peso del activo
            weight = float(position.market_value / portfolio.total_equity)

            # Calcular riesgo del activo (volatilidad)
            asset_risk = 0.0
            if returns_history and position.symbol in returns_history:
                returns = returns_history[position.symbol]
                if len(returns) > 1:
                    asset_risk = float(np.std(returns))

            # Contribución al riesgo total (aproximada)
            # Risk contribution = weight * asset_risk
            risk_contribution = weight * asset_risk

            attributions[position.symbol] = {
                "weight": weight,
                "asset_risk": asset_risk,
                "risk_contribution": risk_contribution,
                "risk_percentage": 0.0,  # Se calculará después
            }

            total_risk += risk_contribution

        # Calcular porcentajes
        if total_risk > 0:
            for symbol in attributions:
                attributions[symbol]["risk_percentage"] = (
                    attributions[symbol]["risk_contribution"] / total_risk * 100
                )

        return {"attributions": attributions, "total_risk": total_risk}

    def _attribute_by_strategy(
        self,
        portfolio: Portfolio,
        strategy_allocations: dict[str, list[str]],
        returns_history: Optional[dict[str, list[float]]],
    ) -> dict[str, Any]:
        """Atribuir riesgo por estrategia."""
        if portfolio.total_equity == 0:
            return {"attributions": {}, "total_risk": 0.0}

        attributions = {}
        total_risk = 0.0

        # Crear mapa símbolo -> estrategia
        symbol_to_strategy = {}
        for strategy, symbols in strategy_allocations.items():
            for symbol in symbols:
                symbol_to_strategy[symbol] = strategy

        # Agrupar por estrategia
        strategy_positions: dict[str, list[Any]] = {}
        for position in portfolio.positions:
            strategy = symbol_to_strategy.get(position.symbol, "unknown")
            if strategy not in strategy_positions:
                strategy_positions[strategy] = []
            strategy_positions[strategy].append(position)

        # Calcular riesgo por estrategia
        for strategy, positions in strategy_positions.items():
            # Calcular peso total de la estrategia
            strategy_value = sum(pos.market_value for pos in positions)
            weight = float(strategy_value / portfolio.total_equity)

            # Calcular riesgo promedio de la estrategia
            strategy_risk = 0.0
            if returns_history:
                strategy_returns = []
                for position in positions:
                    if position.symbol in returns_history:
                        strategy_returns.extend(returns_history[position.symbol])

                if len(strategy_returns) > 1:
                    strategy_risk = float(np.std(strategy_returns))

            # Contribución al riesgo
            risk_contribution = weight * strategy_risk

            attributions[strategy] = {
                "weight": weight,
                "strategy_risk": strategy_risk,
                "risk_contribution": risk_contribution,
                "n_positions": len(positions),
                "risk_percentage": 0.0,  # Se calculará después
            }

            total_risk += risk_contribution

        # Calcular porcentajes
        if total_risk > 0:
            for strategy in attributions:
                attributions[strategy]["risk_percentage"] = (
                    attributions[strategy]["risk_contribution"] / total_risk * 100
                )

        return {"attributions": attributions, "total_risk": total_risk}

    def _attribute_by_factors(
        self,
        portfolio: Portfolio,
        returns_history: Optional[dict[str, list[float]]],
        factor_data: Optional[dict[str, list[float]]],
    ) -> dict[str, Any]:
        """Atribuir riesgo por factores (Fama-French simplificado)."""
        if not factor_data or not returns_history:
            return {
                "attributions": {},
                "total_risk": 0.0,
                "note": "Factor data not available, using simplified model",
            }

        try:
            # Preparar datos de portfolio
            portfolio_returns = self._calculate_portfolio_returns(portfolio, returns_history)

            if len(portfolio_returns) < 10:
                return {
                    "attributions": {},
                    "total_risk": 0.0,
                    "note": "Insufficient data for factor analysis",
                }

            # Regresión de factores (simplificada)
            factor_attributions = {}

            for factor_name in self.factors:
                if factor_name in factor_data:
                    factor_values = factor_data[factor_name]

                    # Asegurar misma longitud
                    min_len = min(len(portfolio_returns), len(factor_values))
                    portfolio_ret = portfolio_returns[:min_len]
                    factor_vals = factor_values[:min_len]

                    if len(portfolio_ret) > 1 and len(factor_vals) > 1:
                        # Calcular correlación y beta
                        correlation = np.corrcoef(portfolio_ret, factor_vals)[0, 1]
                        beta = correlation * (np.std(portfolio_ret) / np.std(factor_vals))

                        # Contribución al riesgo
                        factor_risk = abs(beta * np.std(factor_vals))

                        factor_attributions[factor_name] = {
                            "beta": float(beta),
                            "correlation": float(correlation),
                            "factor_risk": float(factor_risk),
                            "risk_percentage": 0.0,  # Se calculará después
                        }

            # Calcular porcentajes
            total_factor_risk = sum(attr["factor_risk"] for attr in factor_attributions.values())

            if total_factor_risk > 0:
                for factor_name in factor_attributions:
                    factor_attributions[factor_name]["risk_percentage"] = (
                        factor_attributions[factor_name]["factor_risk"] / total_factor_risk * 100
                    )

            return {
                "attributions": factor_attributions,
                "total_risk": float(total_factor_risk),
                "method": "fama_french_simplified",
            }
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.warning(f"Error en factor attribution: {e}")
            return {"attributions": {}, "total_risk": 0.0, "error": str(e)}

    def _calculate_portfolio_returns(
        self, portfolio: Portfolio, returns_history: dict[str, list[float]]
    ) -> list[float]:
        """Calcular retornos del portfolio."""
        if not returns_history:
            return []

        # Encontrar longitud común
        portfolio_symbols = [pos.symbol for pos in portfolio.positions]
        available_symbols = [symbol for symbol in portfolio_symbols if symbol in returns_history]

        if not available_symbols:
            return []

        # Calcular retornos ponderados
        weights = {}
        total_value = portfolio.total_equity
        if total_value > 0:
            for position in portfolio.positions:
                if position.symbol in available_symbols:
                    weights[position.symbol] = float(position.market_value / total_value)

        # Encontrar longitud mínima
        min_len = min(len(returns_history[symbol]) for symbol in available_symbols)

        # Calcular retornos del portfolio
        portfolio_returns = []
        for i in range(min_len):
            portfolio_return = sum(
                weights.get(symbol, 0) * returns_history[symbol][i] for symbol in available_symbols
            )
            portfolio_returns.append(portfolio_return)

        return portfolio_returns

    def _generate_summary(self, attribution: dict[str, Any]) -> dict[str, Any]:
        """Generar resumen de risk attribution."""
        summary: dict[str, Any] = {"top_risk_sources": [], "total_risk_decomposed": 0.0}

        # Top fuentes de riesgo por activo
        if "by_asset" in attribution:
            asset_attrib = attribution["by_asset"]["attributions"]
            top_assets = sorted(
                asset_attrib.items(), key=lambda x: x[1]["risk_contribution"], reverse=True
            )[:5]

            summary["top_risk_sources"].extend(
                [
                    {
                        "type": "asset",
                        "source": symbol,
                        "risk_contribution": info["risk_contribution"],
                        "risk_percentage": info["risk_percentage"],
                    }
                    for symbol, info in top_assets
                ]
            )

        # Top fuentes de riesgo por estrategia
        if "by_strategy" in attribution:
            strategy_attrib = attribution["by_strategy"]["attributions"]
            top_strategies = sorted(
                strategy_attrib.items(), key=lambda x: x[1]["risk_contribution"], reverse=True
            )[:5]

            summary["top_risk_sources"].extend(
                [
                    {
                        "type": "strategy",
                        "source": strategy,
                        "risk_contribution": info["risk_contribution"],
                        "risk_percentage": info["risk_percentage"],
                    }
                    for strategy, info in top_strategies
                ]
            )

        return summary
