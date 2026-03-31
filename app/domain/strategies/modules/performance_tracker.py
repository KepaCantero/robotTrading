"""
PerformanceTracker - Sistema de tracking de desempeño para aprendizaje continuo.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


class FilterPerformanceTracker:
    """
    Rastrea el desempeño de un filtro individual para aprendizaje continuo.

    Registra:
    - Señales generadas vs señales que resultaron en trades exitosos
    - P&L generado por señales que pasaron este filtro
    - Tasa de aciertos en diferentes contextos de mercado
    """

    def __init__(self, filter_name: str, lookback_window: int = 100):
        """
        Inicializar tracker de desempeño.

        Args:
            filter_name: Nombre del filtro
            lookback_window: Número de señales a mantener en memoria
        """
        self.filter_name = filter_name
        self.lookback_window = lookback_window

        # Histórico de señales
        self.signal_history: deque = deque(maxlen=lookback_window)

        # Métricas agregadas
        self.total_signals: int = 0
        self.passed_signals: int = 0
        self.led_to_trade: int = 0
        self.successful_trades: int = 0
        self.total_pnl: Decimal = Decimal("0.0")

        # Por contexto de mercado
        self.context_performance: dict[str, dict] = {}

        # Por threshold usado
        self.threshold_performance: dict[str, dict] = {}

    def record_signal(
        self,
        passed: bool,
        confidence: float,
        market_context: dict,
        metadata: dict,
        led_to_trade: bool = False,
        trade_result: Optional[dict] = None,
    ) -> None:
        """
        Registrar una señal evaluada por el filtro.

        Args:
            passed: Si el filtro pasó
            confidence: Confianza del filtro
            market_context: Contexto de mercado
            trade_result: Resultado del trade si aplica (con pnl, success, etc.)
        """
        self.total_signals += 1

        if passed:
            self.passed_signals += 1

        if led_to_trade:
            self.led_to_trade += 1

            if trade_result:
                if trade_result.get("success", False):
                    self.successful_trades += 1

                pnl = trade_result.get("pnl", Decimal("0.0"))
                if isinstance(pnl, (int, float)):
                    pnl = Decimal(str(pnl))
                self.total_pnl += pnl

        # Registrar en histórico
        signal_record = {
            "timestamp": datetime.now(),
            "passed": passed,
            "confidence": confidence,
            "market_context": market_context.get("type", "unknown"),
            "metadata": metadata,
            "led_to_trade": led_to_trade,
            "trade_result": trade_result,
        }
        self.signal_history.append(signal_record)

        # Actualizar métricas por contexto
        context_type = market_context.get("type", "unknown")
        if context_type not in self.context_performance:
            self.context_performance[context_type] = {
                "total": 0,
                "passed": 0,
                "trades": 0,
                "successful": 0,
                "pnl": Decimal("0.0"),
            }

        ctx_metrics = self.context_performance[context_type]
        ctx_metrics["total"] += 1
        if passed:
            ctx_metrics["passed"] += 1
        if led_to_trade:
            ctx_metrics["trades"] += 1
            if trade_result and trade_result.get("success"):
                ctx_metrics["successful"] += 1
            if trade_result:
                pnl = trade_result.get("pnl", Decimal("0.0"))
                if isinstance(pnl, (int, float)):
                    pnl = Decimal(str(pnl))
                ctx_metrics["pnl"] += pnl

    def get_win_rate(self) -> float:
        """Calcular tasa de aciertos reciente."""
        if self.led_to_trade == 0:
            return 0.0
        return self.successful_trades / self.led_to_trade

    def get_pass_rate(self) -> float:
        """Calcular tasa de señales que pasan el filtro."""
        if self.total_signals == 0:
            return 0.0
        return self.passed_signals / self.total_signals

    def get_average_pnl_per_trade(self) -> Decimal:
        """Calcular P&L promedio por trade."""
        if self.led_to_trade == 0:
            return Decimal("0.0")
        return self.total_pnl / Decimal(str(self.led_to_trade))

    def get_effectiveness_score(self) -> float:
        """
        Calcular score de efectividad del filtro.

        Combina:
        - Win rate
        - Pass rate (normalizado)
        - P&L promedio (normalizado)

        Returns:
            Score de 0.0 a 1.0
        """
        win_rate = self.get_win_rate()
        pass_rate = self.get_pass_rate()
        avg_pnl = float(self.get_average_pnl_per_trade())

        # Normalizar P&L (asumiendo -10% a +10% como rango razonable)
        normalized_pnl = max(0.0, min(1.0, (avg_pnl + 0.1) / 0.2))

        # Score ponderado
        score = (win_rate * 0.4) + (pass_rate * 0.3) + (normalized_pnl * 0.3)
        return score

    def get_recommendations(self) -> dict:
        """
        Generar recomendaciones para ajustar el filtro.

        Returns:
            Dict con sugerencias de ajustes
        """
        recommendations = {
            "should_enable": True,
            "should_disable": False,
            "adjust_confidence_threshold": None,
            "context_specific_adjustments": {},
        }

        effectiveness = self.get_effectiveness_score()
        win_rate = self.get_win_rate()
        pass_rate = self.get_pass_rate()

        # Si efectividad muy baja, considerar desactivar
        if effectiveness < 0.3 and self.led_to_trade >= 20:
            recommendations["should_disable"] = True
            recommendations["should_enable"] = False

        # Si win rate bajo pero pass rate alto, sugerir ser más estricto
        if win_rate < 0.4 and pass_rate > 0.7:
            recommendations["adjust_confidence_threshold"] = "increase"

        # Si win rate alto pero pass rate bajo, sugerir ser más permisivo
        if win_rate > 0.6 and pass_rate < 0.3:
            recommendations["adjust_confidence_threshold"] = "decrease"

        # Ajustes por contexto
        for context, metrics in self.context_performance.items():
            if metrics["trades"] >= 10:
                ctx_win_rate = (
                    metrics["successful"] / metrics["trades"] if metrics["trades"] > 0 else 0
                )
                ctx_avg_pnl = (
                    float(metrics["pnl"] / Decimal(str(metrics["trades"])))
                    if metrics["trades"] > 0
                    else 0
                )

                if ctx_win_rate < 0.35 or ctx_avg_pnl < -0.02:
                    recommendations["context_specific_adjustments"][context] = {
                        "action": "be_more_strict",
                        "reason": f"Low performance: win_rate={ctx_win_rate:.2f}, avg_pnl={ctx_avg_pnl:.4f}",
                    }
                elif ctx_win_rate > 0.65 and ctx_avg_pnl > 0.02:
                    recommendations["context_specific_adjustments"][context] = {
                        "action": "be_more_permissive",
                        "reason": f"High performance: win_rate={ctx_win_rate:.2f}, avg_pnl={ctx_avg_pnl:.4f}",
                    }

        return recommendations


class StrategyPerformanceTracker:
    """
    Rastrea el desempeño general de la estrategia y coordina trackers de filtros.
    """

    def __init__(self, strategy_name: str):
        """Inicializar tracker de estrategia."""
        self.strategy_name = strategy_name
        self.filter_trackers: dict[str, FilterPerformanceTracker] = {}
        self.overall_pnl: Decimal = Decimal("0.0")
        self.total_trades: int = 0
        self.successful_trades: int = 0

    def get_filter_tracker(self, filter_name: str) -> FilterPerformanceTracker:
        """Obtener o crear tracker para un filtro."""
        if filter_name not in self.filter_trackers:
            self.filter_trackers[filter_name] = FilterPerformanceTracker(filter_name)
        return self.filter_trackers[filter_name]

    def record_trade_result(self, trade_result: dict, filter_signals: list[dict]) -> None:
        """
        Registrar resultado de un trade y actualizar trackers de filtros.

        Args:
            trade_result: Resultado del trade con pnl, success, etc.
            filter_signals: Lista de resultados de filtros que participaron
        """
        self.total_trades += 1
        if trade_result.get("success", False):
            self.successful_trades += 1

        pnl = trade_result.get("pnl", Decimal("0.0"))
        if isinstance(pnl, (int, float)):
            pnl = Decimal(str(pnl))
        self.overall_pnl += pnl

        # Actualizar cada filtro que participó
        for filter_signal in filter_signals:
            filter_name = filter_signal.get("filter_name")
            if filter_name:
                tracker = self.get_filter_tracker(filter_name)
                tracker.record_signal(
                    passed=filter_signal.get("passed", False),
                    confidence=filter_signal.get("confidence", 0.0),
                    market_context=filter_signal.get("market_context", {}),
                    metadata=filter_signal.get("metadata", {}),
                    led_to_trade=True,
                    trade_result=trade_result,
                )

    def get_overall_performance(self) -> dict:
        """Obtener métricas generales de desempeño."""
        win_rate = self.successful_trades / self.total_trades if self.total_trades > 0 else 0.0
        avg_pnl = float(self.overall_pnl / Decimal(str(self.total_trades)))

        return {
            "total_trades": self.total_trades,
            "win_rate": win_rate,
            "total_pnl": float(self.overall_pnl),
            "avg_pnl_per_trade": avg_pnl,
            "filter_performance": {
                name: {
                    "effectiveness": tracker.get_effectiveness_score(),
                    "win_rate": tracker.get_win_rate(),
                    "recommendations": tracker.get_recommendations(),
                }
                for name, tracker in self.filter_trackers.items()
            },
        }
