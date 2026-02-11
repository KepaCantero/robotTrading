"""
Signal Evaluation Engine - TASK-15: Refactorización de Servicios

Este módulo implementa el motor de evaluación de señales, separando la lógica
de evaluación de la gestión de señales y ejecución.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.centralized_config import get_config
from app.models.signal import MarketData, SignalType

logger = logging.getLogger(__name__)


class SignalEvaluationEngine:
    """
    Motor de evaluación de señales.

    Responsabilidades:
    - Evaluar la calidad de las señales
    - Calcular scores de confianza
    - Validar criterios de entrada
    - Filtrar señales por thresholds
    """

    def __init__(self):
        """Inicializar motor de evaluación."""
        self.config = get_config().trading

        # Thresholds de evaluación
        self.min_signal_strength = self.config.min_signal_strength
        self.min_signal_confidence = self.config.min_signal_confidence
        self.min_liquidity_score = self.config.min_liquidity_score

        # Métricas de rendimiento
        self.evaluations_count = 0
        self.accepted_signals = 0
        self.rejected_signals = 0

    def evaluate_signal_quality(
        self,
        symbol: str,
        signal_type: SignalType,
        market_data: MarketData,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluar la calidad de una señal.

        Args:
            symbol: Símbolo del activo
            signal_type: Tipo de señal
            market_data: Datos de mercado
            metadata: Metadatos adicionales

        Returns:
            Diccionario con scores y evaluación
        """
        self.evaluations_count += 1

        # Calcular scores básicos
        strength_score = self._calculate_strength_score(market_data, metadata)
        confidence_score = self._calculate_confidence_score(market_data, metadata)
        liquidity_score = self._calculate_liquidity_score(market_data, metadata)

        # Score combinado
        combined_score = self._calculate_combined_score(
            strength_score, confidence_score, liquidity_score
        )

        # Determinar si la señal es aceptable
        is_acceptable = self._is_signal_acceptable(
            strength_score, confidence_score, liquidity_score
        )

        if is_acceptable:
            self.accepted_signals += 1
        else:
            self.rejected_signals += 1

        evaluation_result = {
            "symbol": symbol,
            "signal_type": signal_type,
            "strength_score": strength_score,
            "confidence_score": confidence_score,
            "liquidity_score": liquidity_score,
            "combined_score": combined_score,
            "is_acceptable": is_acceptable,
            "evaluation_time": datetime.utcnow(),
            "metadata": metadata,
        }

        logger.debug(f"Signal evaluation for {symbol}: {evaluation_result}")
        return evaluation_result

    def _calculate_strength_score(self, market_data: MarketData, metadata: Dict[str, Any]) -> float:
        """Calcular score de fuerza de la señal."""
        # Implementación simplificada basada en volatilidad y volumen
        volatility = metadata.get("volatility", 0.0)
        volume_ratio = metadata.get("volume_ratio", 1.0)

        # Score basado en volatilidad (mayor volatilidad = mayor fuerza
        # potencial)
        volatility_score = min(volatility * 2, 100.0)

        # Score basado en volumen (mayor volumen = mayor confianza)
        volume_score = min(volume_ratio * 50, 100.0)

        # Combinar scores
        strength_score = volatility_score * 0.6 + volume_score * 0.4

        return min(max(strength_score, 0.0), 100.0)

    def _calculate_confidence_score(
        self, market_data: MarketData, metadata: Dict[str, Any]
    ) -> float:
        """Calcular score de confianza de la señal."""
        # Implementación simplificada basada en consistencia de datos
        data_quality = metadata.get("data_quality", 0.8)
        trend_consistency = metadata.get("trend_consistency", 0.7)

        # Score de calidad de datos
        quality_score = data_quality * 100

        # Score de consistencia de tendencia
        consistency_score = trend_consistency * 100

        # Combinar scores
        confidence_score = quality_score * 0.7 + consistency_score * 0.3

        return min(max(confidence_score, 0.0), 100.0)

    def _calculate_liquidity_score(
        self, market_data: MarketData, metadata: Dict[str, Any]
    ) -> float:
        """Calcular score de liquidez."""
        # Implementación simplificada basada en spread y volumen
        spread_pct = metadata.get("spread_pct", 0.01)
        avg_volume = metadata.get("avg_volume", 1000000)

        # Score basado en spread (menor spread = mayor liquidez) - use config BPS multiplier
        tt = get_config().trading_thresholds
        spread_score = max(0, 100 - (spread_pct * tt.bps_multiplier))

        # Score basado en volumen promedio
        volume_score = min(avg_volume / 1000000 * 50, 100.0)

        # Combinar scores
        liquidity_score = spread_score * 0.6 + volume_score * 0.4

        return min(max(liquidity_score, 0.0), 100.0)

    def _calculate_combined_score(
        self, strength_score: float, confidence_score: float, liquidity_score: float
    ) -> float:
        """Calcular score combinado ponderado."""
        # Pesos para cada componente
        weights = {"strength": 0.4, "confidence": 0.4, "liquidity": 0.2}

        combined_score = (
            strength_score * weights["strength"]
            + confidence_score * weights["confidence"]
            + liquidity_score * weights["liquidity"]
        )

        return min(max(combined_score, 0.0), 100.0)

    def _is_signal_acceptable(
        self, strength_score: float, confidence_score: float, liquidity_score: float
    ) -> bool:
        """Determinar si la señal cumple los criterios mínimos."""
        return (
            strength_score >= self.min_signal_strength
            and confidence_score >= self.min_signal_confidence
            and liquidity_score >= self.min_liquidity_score
        )

    def get_evaluation_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de evaluación."""
        total_evaluations = self.evaluations_count
        acceptance_rate = (
            self.accepted_signals / total_evaluations if total_evaluations > 0 else 0.0
        )

        return {
            "total_evaluations": total_evaluations,
            "accepted_signals": self.accepted_signals,
            "rejected_signals": self.rejected_signals,
            "acceptance_rate": acceptance_rate,
            "min_signal_strength": self.min_signal_strength,
            "min_signal_confidence": self.min_signal_confidence,
            "min_liquidity_score": self.min_liquidity_score,
        }

    def update_thresholds(
        self,
        min_strength: Optional[float] = None,
        min_confidence: Optional[float] = None,
        min_liquidity: Optional[float] = None,
    ) -> None:
        """Actualizar thresholds de evaluación."""
        if min_strength is not None:
            self.min_signal_strength = min_strength
            logger.info(f"Updated min_signal_strength to {min_strength}")

        if min_confidence is not None:
            self.min_signal_confidence = min_confidence
            logger.info(f"Updated min_signal_confidence to {min_confidence}")

        if min_liquidity is not None:
            self.min_liquidity_score = min_liquidity
            logger.info(f"Updated min_liquidity_score to {min_liquidity}")

    def reset_statistics(self) -> None:
        """Resetear estadísticas de evaluación."""
        self.evaluations_count = 0
        self.accepted_signals = 0
        self.rejected_signals = 0
        logger.info("Reset signal evaluation statistics")
