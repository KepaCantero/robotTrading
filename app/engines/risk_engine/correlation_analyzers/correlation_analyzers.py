"""
Correlation Analyzers

Implementa análisis de correlaciones:
- Matrices de correlación en tiempo real
- Correlation-based position limits
- Diversification scoring
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from app.domain.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class BaseCorrelationAnalyzer(ABC):
    """Clase base para correlation analyzers."""

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar correlation analyzer.

        Args:
            config: Configuración del analyzer
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def analyze_correlations(
        self, portfolio: Portfolio, prices_history: dict[str, list[float]], **kwargs
    ) -> dict[str, Any]:
        """
        Analizar correlaciones del portfolio.

        Args:
            portfolio: Portfolio a analizar
            prices_history: Historial de precios por símbolo
            **kwargs: Argumentos adicionales

        Returns:
            Análisis de correlaciones
        """


class CorrelationAnalyzer(BaseCorrelationAnalyzer):
    """
    Correlation Analyzer principal.

    Analiza correlaciones entre posiciones del portfolio.
    """

    def __init__(self, config: dict[str, Any]):
        """Inicializar correlation analyzer."""
        super().__init__(config)

        # Configuración
        self.max_correlation = config.get("max_correlation", 0.8)  # 80% máximo
        self.correlation_window = config.get("correlation_window", 60)  # 60 días
        self.diversification_threshold = config.get("diversification_threshold", 0.3)  # 30% mínimo

        # Historial de correlaciones
        self.correlation_history: list[dict[str, Any]] = []

    def analyze_correlations(
        self, portfolio: Portfolio, prices_history: dict[str, list[float]], **kwargs
    ) -> dict[str, Any]:
        """
        Analizar correlaciones completas del portfolio.

        Args:
            portfolio: Portfolio a analizar
            prices_history: Dict con historial de precios por símbolo
            **kwargs: Argumentos adicionales

        Returns:
            Análisis completo de correlaciones
        """
        try:
            # Filtrar símbolos que están en el portfolio
            portfolio_symbols = [pos.symbol for pos in portfolio.positions]
            relevant_prices = {
                symbol: prices
                for symbol, prices in prices_history.items()
                if symbol in portfolio_symbols
            }

            if len(relevant_prices) < 2:
                return {
                    "correlation_matrix": {},
                    "average_correlation": 0.0,
                    "max_correlation": 0.0,
                    "violations": [],
                    "diversification_score": 0.0,
                    "error": "Insufficient data for correlation analysis",
                }

            # Calcular matriz de correlación
            correlation_matrix = self._calculate_correlation_matrix(relevant_prices)

            # Análisis de correlaciones
            correlation_analysis = self._analyze_correlations(correlation_matrix, portfolio_symbols)

            # Detectar violaciones
            violations = self._detect_correlation_violations(correlation_matrix, portfolio_symbols)

            # Calcular diversification score
            diversification_score = self._calculate_diversification_score(
                correlation_matrix, portfolio
            )

            # Correlation-based position limits
            position_limits = self._calculate_position_limits(correlation_matrix, portfolio_symbols)

            return {
                "correlation_matrix": correlation_matrix,
                "average_correlation": correlation_analysis["average"],
                "max_correlation": correlation_analysis["max"],
                "min_correlation": correlation_analysis["min"],
                "violations": violations,
                "diversification_score": diversification_score,
                "position_limits": position_limits,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            self.logger.error(f"Error analizando correlaciones: {e}", exc_info=True)
            return {"error": str(e)}

    def _calculate_correlation_matrix(
        self, prices_history: dict[str, list[float]]
    ) -> dict[str, dict[str, float]]:
        """Calcular matriz de correlación."""
        # Convertir a DataFrame
        df = pd.DataFrame(prices_history)

        # Calcular retornos
        returns_df = df.pct_change().dropna()

        # Asegurar que tenemos suficiente data
        if len(returns_df) < self.correlation_window:
            # Usar toda la data disponible
            window = len(returns_df)
        else:
            # Usar ventana rolling
            window = self.correlation_window

        # Calcular correlación usando ventana rolling
        if len(returns_df) >= window:
            recent_returns = returns_df.tail(window)
            correlation_matrix = recent_returns.corr()
        else:
            correlation_matrix = returns_df.corr()

        # Convertir a dict
        # CRITICAL: Do NOT convert NaN to 0.0 - that would falsely indicate decorrelation
        # NaN means "insufficient data" which is different from "zero correlation"
        result = {}
        for symbol1 in correlation_matrix.index:
            result[symbol1] = {}
            for symbol2 in correlation_matrix.columns:
                corr = correlation_matrix.loc[symbol1, symbol2]
                if pd.notna(corr):
                    result[symbol1][symbol2] = float(corr)
                else:
                    # Use None to indicate missing data, not 0.0
                    # Downstream code must handle None appropriately
                    result[symbol1][symbol2] = None
                    logger.debug(f"Correlation {symbol1}-{symbol2} is NaN (insufficient data)")

        return result

    def _analyze_correlations(
        self, correlation_matrix: dict[str, dict[str, float]], symbols: list[str]
    ) -> dict[str, Any]:
        """Analizar estadísticas de correlaciones."""
        correlations = []

        for symbol1 in symbols:
            for symbol2 in symbols:
                if (
                    symbol1 != symbol2
                    and symbol1 in correlation_matrix
                    and symbol2 in correlation_matrix[symbol1]
                ):
                    corr = correlation_matrix[symbol1][symbol2]
                    # Skip None values (insufficient data)
                    if corr is not None:
                        correlations.append(corr)

        if not correlations:
            return {"average": None, "max": None, "min": None, "std": None, "count": 0}

        return {
            "average": float(np.mean(correlations)),
            "max": float(np.max(correlations)),
            "min": float(np.min(correlations)),
            "std": float(np.std(correlations)),
            "median": float(np.median(correlations)),
        }

    def _detect_correlation_violations(
        self, correlation_matrix: dict[str, dict[str, float]], symbols: list[str]
    ) -> list[dict[str, Any]]:
        """Detectar violaciones de correlación."""
        violations = []

        for symbol1 in symbols:
            for symbol2 in symbols:
                if (
                    symbol1 != symbol2
                    and symbol1 in correlation_matrix
                    and symbol2 in correlation_matrix[symbol1]
                ):
                    corr = abs(correlation_matrix[symbol1][symbol2])

                    if corr > self.max_correlation:
                        violations.append(
                            {
                                "type": "high_correlation",
                                "symbol1": symbol1,
                                "symbol2": symbol2,
                                "correlation": corr,
                                "limit": self.max_correlation,
                                "severity": "high" if corr > 0.9 else "medium",
                            }
                        )

        return violations

    def _calculate_diversification_score(
        self, correlation_matrix: dict[str, dict[str, float]], portfolio: Portfolio
    ) -> float:
        """
        Calcular diversification score.

        Score alto = buena diversificación (correlaciones bajas)
        Score bajo = mala diversificación (correlaciones altas)
        """
        symbols = [pos.symbol for pos in portfolio.positions]

        if len(symbols) < 2:
            return 0.0

        # Calcular promedio de correlaciones absolutas
        correlations = []
        for symbol1 in symbols:
            for symbol2 in symbols:
                if (
                    symbol1 != symbol2
                    and symbol1 in correlation_matrix
                    and symbol2 in correlation_matrix[symbol1]
                ):
                    corr = abs(correlation_matrix[symbol1][symbol2])
                    correlations.append(corr)

        if not correlations:
            return 0.0

        avg_correlation = np.mean(correlations)

        # Score: inverso de correlación promedio (normalizado)
        # Score = 1 - avg_correlation (con ajuste)
        score = max(0.0, min(1.0, 1.0 - avg_correlation))

        return float(score)

    def _calculate_position_limits(
        self, correlation_matrix: dict[str, dict[str, float]], symbols: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Calcular límites de posición basados en correlaciones."""
        position_limits = {}

        for symbol in symbols:
            # Encontrar símbolos altamente correlacionados
            high_corr_symbols = []
            if symbol in correlation_matrix:
                for other_symbol, corr in correlation_matrix[symbol].items():
                    if other_symbol != symbol and abs(corr) > self.max_correlation:
                        high_corr_symbols.append({"symbol": other_symbol, "correlation": corr})

            # Calcular límite sugerido
            # Si hay muchas correlaciones altas, reducir límite
            n_high_corr = len(high_corr_symbols)
            # Reducir límite proporcionalmente si hay correlaciones altas
            suggested_limit = (
                max(0.05, 0.2 - n_high_corr * 0.03) if n_high_corr > 0 else 0.2
            )  # Límite estándar

            position_limits[symbol] = {
                "suggested_limit": suggested_limit,
                "high_correlation_count": n_high_corr,
                "high_correlation_symbols": high_corr_symbols,
            }

        return position_limits

    def get_status(self) -> dict[str, Any]:
        """Obtener estado del analyzer."""
        return {
            "max_correlation": self.max_correlation,
            "correlation_window": self.correlation_window,
            "diversification_threshold": self.diversification_threshold,
            "history_size": len(self.correlation_history),
        }
