"""
Refactored Signal Scorer Service - TASK-15: Refactorización de Servicios

Este módulo implementa el servicio de scoring de señales refactorizado,
utilizando los nuevos motores especializados.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.shared.config.centralized_config import get_config
from app.domain.models.signal import (
    MarketData,
    Signal,
    SignalPriorityQueue,
    SignalScorer,
    SignalSource,
    SignalStrength,
    SignalType,
)
from app.services.portfolio_service import PortfolioService
from app.services.position_sizing_engine import PositionSizingEngine
from app.services.signal_evaluation_engine import SignalEvaluationEngine
from app.services.signal_execution_engine import SignalExecutionEngine

logger = logging.getLogger(__name__)


class SignalScorerService:
    """
    Servicio de scoring de señales refactorizado.

    Ahora utiliza motores especializados para:
    - Evaluación de señales
    - Cálculo de tamaño de posición
    - Ejecución de señales
    """

    def __init__(self, portfolio_service: PortfolioService):
        """Inicializar servicio refactorizado."""
        self.portfolio_service = portfolio_service

        # Motores especializados
        self.evaluation_engine = SignalEvaluationEngine()
        self.sizing_engine = PositionSizingEngine()
        self.execution_engine = SignalExecutionEngine()

        # Componentes originales mantenidos para compatibilidad
        self.scorer = SignalScorer()
        self.priority_queue = SignalPriorityQueue(max_size=1000)
        self.signal_history: List[Signal] = []
        self.max_history_size = 10000

        # Configuración
        self.config = get_config().trading

        # Métricas de rendimiento
        self.signals_processed = 0
        self.signals_executed = 0
        self.total_pnl = Decimal("0")

    async def evaluate_signal(
        self,
        symbol: str,
        signal_type: SignalType,
        market_data: MarketData,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """
        Evaluar señal usando el motor de evaluación especializado.
        """
        try:
            # Usar motor de evaluación
            evaluation_result = self.evaluation_engine.evaluate_signal_quality(
                symbol, signal_type, market_data, metadata
            )

            # Solo crear señal si es aceptable
            if not evaluation_result["is_acceptable"]:
                logger.debug(f"Signal rejected for {symbol}: below thresholds")
                return None

            # Crear señal con scores calculados
            signal = Signal(
                signal_id=f"signal_{datetime.utcnow().timestamp()}",
                symbol=symbol,
                signal_type=signal_type,
                strength=SignalStrength.STRONG,  # Basado en evaluation_result
                confidence=evaluation_result["confidence_score"],
                price=market_data.price,
                volume=market_data.volume,
                source=SignalSource.TECHNICAL_ANALYSIS,
                metadata={
                    "strength_score": evaluation_result["strength_score"],
                    "liquidity_score": evaluation_result["liquidity_score"],
                    "combined_score": evaluation_result["combined_score"],
                    **metadata,
                },
            )

            # Agregar a historial
            self._add_to_history(signal)
            self.signals_processed += 1

            logger.info(f"Signal evaluated for {symbol}: {evaluation_result['combined_score']:.2f}")
            return signal

        except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
            logger.error(f"Error evaluating signal for {symbol}: {e}")
            return None

    async def calculate_position_size(self, signal: Signal) -> Decimal:
        """
        Calcular tamaño de posición usando el motor especializado.
        """
        try:
            # Obtener portafolio actual
            portfolio = await self.portfolio_service.get_portfolio()
            if not portfolio:
                logger.warning("No portfolio available for position sizing")
                return Decimal("0")

            # Calcular capital disponible
            available_capital = portfolio.cash

            # Usar motor de sizing
            position_size, sizing_details = self.sizing_engine.calculate_position_size(
                signal, portfolio, available_capital, signal.metadata
            )

            logger.debug(f"Position size calculated for {signal.symbol}: {position_size}")
            return position_size

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error calculating position size for {signal.symbol}: {e}")
            return Decimal("0")

    async def execute_signal(self, signal: Signal) -> bool:
        """
        Ejecutar señal usando el motor de ejecución especializado.
        """
        try:
            # Calcular tamaño de posición
            position_size = await self.calculate_position_size(signal)
            if position_size <= 0:
                logger.warning(f"Cannot execute signal for {signal.symbol}: invalid position size")
                return False

            # Obtener portafolio actual
            portfolio = await self.portfolio_service.get_portfolio()
            if not portfolio:
                logger.warning("No portfolio available for signal execution")
                return False

            # Definir callback de ejecución
            async def execution_callback(order, portfolio):
                # Usar portfolio service para simular trade
                success = await self.portfolio_service.simulate_trade(
                    order.symbol, order.quantity, order.price
                )
                return {
                    "success": success,
                    "order_status": "filled" if success else "failed",
                    "executed_price": order.price,
                    "executed_quantity": order.quantity,
                }

            # Usar motor de ejecución
            success, execution_details = await self.execution_engine.execute_signal(
                signal, position_size, portfolio, execution_callback
            )

            if success:
                self.signals_executed += 1
                logger.info(f"Signal executed successfully for {signal.symbol}")
            else:
                logger.warning(f"Signal execution failed for {signal.symbol}")

            return success

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error executing signal for {signal.symbol}: {e}")
            return False

    async def get_signal_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del servicio."""
        # Calcular success rate
        success_rate = (
            (self.signals_executed / self.signals_processed * 100)
            if self.signals_processed > 0
            else 0.0
        )

        # Queue size from priority queue
        queue_size = 0
        queue_summary = {}
        if hasattr(self, "priority_queue") and self.priority_queue:
            queue_size = len(self.priority_queue.queue)
            queue_summary = {
                "high_priority": sum(1 for s in self.priority_queue.queue if s.priority_score > 80),
                "medium_priority": sum(
                    1 for s in self.priority_queue.queue if 50 <= s.priority_score <= 80
                ),
                "low_priority": sum(1 for s in self.priority_queue.queue if s.priority_score < 50),
            }

        # Thresholds from config - use default values
        thresholds = {
            "confidence": 60.0,
            "liquidity": 50.0,
            "max_position_size": 10.0,
        }

        return {
            "signals_processed": self.signals_processed,
            "signals_executed": self.signals_executed,
            "success_rate": success_rate,
            "total_pnl": float(self.total_pnl),
            "queue_size": queue_size,
            "queue_summary": queue_summary,
            "min_confidence_threshold": thresholds["confidence"],
            "min_liquidity_threshold": thresholds["liquidity"],
            "max_position_size_percent": thresholds["max_position_size"],
        }

    def _add_to_history(self, signal: Signal) -> None:
        """Agregar señal al historial."""
        self.signal_history.append(signal)

        # Mantener tamaño máximo del historial
        if len(self.signal_history) > self.max_history_size:
            self.signal_history = self.signal_history[-self.max_history_size :]

    # Métodos de compatibilidad mantenidos
    async def get_next_actionable_signal(self) -> Optional[Signal]:
        """Obtener siguiente señal accionable."""
        if self.priority_queue.is_empty():
            return None

        return self.priority_queue.get_highest_priority_signal()

    async def get_signals_by_symbol(self, symbol: str) -> List[Signal]:
        """Obtener señales por símbolo."""
        return [s for s in self.signal_history if s.symbol == symbol]

    async def clear_expired_signals(self, max_age_minutes: int = 60) -> int:
        """Limpiar señales expiradas."""
        current_time = datetime.utcnow()
        expired_threshold = current_time - timedelta(minutes=max_age_minutes)

        original_count = len(self.signal_history)
        self.signal_history = [s for s in self.signal_history if s.timestamp > expired_threshold]

        cleared_count = original_count - len(self.signal_history)
        logger.info(f"Cleared {cleared_count} expired signals")
        return cleared_count

    def update_thresholds(
        self,
        min_strength: Optional[float] = None,
        min_confidence: Optional[float] = None,
        min_liquidity: Optional[float] = None,
    ) -> None:
        """Actualizar thresholds de evaluación."""
        self.evaluation_engine.update_thresholds(min_strength, min_confidence, min_liquidity)

    def reset_statistics(self) -> None:
        """Resetear estadísticas."""
        self.signals_processed = 0
        self.signals_executed = 0
        self.total_pnl = Decimal("0")

        # Resetear motores
        self.evaluation_engine.reset_statistics()
        self.sizing_engine.reset_statistics()
        self.execution_engine.reset_statistics()

        logger.info("Reset signal scorer service statistics")

    def update_position_size_limit(self, max_percent: float) -> None:
        """Actualizar límite máximo de tamaño de posición."""
        if not (0 < max_percent <= 100):
            raise ValueError("Max position size must be between 0 and 100%")

        # Actualizar configuración del motor de sizing
        self.sizing_engine.max_position_size_percent = max_percent
        logger.info(f"Updated max position size limit to {max_percent}%")
