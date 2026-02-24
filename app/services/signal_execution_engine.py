"""
Signal Execution Engine - TASK-15: Refactorización de Servicios

Este módulo implementa el motor de ejecución de señales, separando la lógica
de ejecución de la evaluación y gestión de señales.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.shared.config.centralized_config import get_config
from app.models.order import Order, OrderSide, OrderStatus, OrderType
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalType, SignalSource

logger = logging.getLogger(__name__)


class SignalExecutionEngine:
    """
    Motor de ejecución de señales.

    Responsabilidades:
    - Ejecutar señales de trading
    - Gestionar órdenes
    - Manejar errores de ejecución
    - Tracking de rendimiento
    """

    def __init__(self):
        """Inicializar motor de ejecución."""
        self.config = get_config().trading
        tt = get_config().trading_thresholds

        # Configuración de ejecución
        self.max_execution_time_ms = self.config.max_execution_time_ms
        self.max_latency_ms = self.config.max_latency_ms

        # Use config for history size
        self.max_history_size = tt.execution_history_max_size

        # Métricas de rendimiento
        self.executions_attempted = 0
        self.executions_successful = 0
        self.executions_failed = 0
        self.total_execution_time_ms = 0.0

        # Historial de ejecuciones
        self.execution_history: List[Dict[str, Any]] = []

        # Store config for simulated latency
        self._simulated_latency_seconds = tt.simulated_latency_ms / 1000.0

    async def execute_signal(
        self,
        signal: Signal,
        position_size: Decimal,
        portfolio: Portfolio,
        execution_callback: Optional[callable] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Ejecutar una señal de trading.

        Args:
            signal: Señal a ejecutar
            position_size: Tamaño de posición calculado
            portfolio: Portafolio objetivo
            execution_callback: Callback para ejecución real

        Returns:
            Tupla con (éxito, detalles_ejecución)
        """
        start_time = datetime.utcnow()
        self.executions_attempted += 1

        try:
            # Validar señal antes de ejecutar
            validation_result = self._validate_signal_for_execution(signal, position_size)
            if not validation_result["is_valid"]:
                return False, validation_result

            # Crear orden
            order = self._create_order(signal, position_size)

            # Ejecutar orden
            execution_result = await self._execute_order(order, portfolio, execution_callback)

            # Calcular tiempo de ejecución
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.total_execution_time_ms += execution_time

            # Determinar éxito
            success = execution_result["success"]

            if success:
                self.executions_successful += 1
                logger.info(f"Signal executed successfully for {signal.symbol}")
            else:
                self.executions_failed += 1
                logger.warning(f"Signal execution failed for {signal.symbol}")

            # Crear detalles de ejecución
            execution_details = {
                "signal_id": signal.signal_id,
                "symbol": signal.symbol,
                "signal_type": signal.signal_type,
                "position_size": position_size,
                "order": order,
                "success": success,
                "execution_time_ms": execution_time,
                "execution_result": execution_result,
                "timestamp": start_time,
            }

            # Guardar en historial
            self._add_to_history(execution_details)

            return success, execution_details

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.executions_failed += 1
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            error_details = {
                "signal_id": signal.signal_id,
                "symbol": signal.symbol,
                "error": str(e),
                "execution_time_ms": execution_time,
                "timestamp": start_time,
            }

            logger.error(f"Error executing signal for {signal.symbol}: {e}")
            return False, error_details

    def _validate_signal_for_execution(
        self, signal: Signal, position_size: Decimal
    ) -> Dict[str, Any]:
        """Validar señal antes de ejecutar."""
        validation_errors = []

        # Validar tamaño de posición
        if position_size <= 0:
            validation_errors.append("Invalid position size")

        # Validar precio
        if signal.price <= 0:
            validation_errors.append("Invalid signal price")

        # Validar símbolo
        if not signal.symbol or len(signal.symbol.strip()) == 0:
            validation_errors.append("Invalid symbol")

        # Validar tipo de señal
        if signal.signal_type not in [SignalType.BUY, SignalType.SELL]:
            validation_errors.append("Invalid signal type for execution")

        is_valid = len(validation_errors) == 0

        return {
            "is_valid": is_valid,
            "errors": validation_errors,
            "position_size": position_size,
            "signal_price": signal.price,
        }

    def _create_order(self, signal: Signal, position_size: Decimal) -> Order:
        """Crear orden basada en la señal."""
        # Calcular cantidad
        quantity = position_size / signal.price

        # Determinar lado de la orden
        if signal.signal_type == SignalType.BUY:
            side = OrderSide.BUY
        else:
            side = OrderSide.SELL

        # Crear orden
        order = Order(
            id=f"order_{signal.signal_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}",
            symbol=signal.symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=signal.price,
            status=OrderStatus.PENDING,
        )

        return order

    async def _execute_order(
        self,
        order: Order,
        portfolio: Portfolio,
        execution_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Ejecutar orden."""
        try:
            if execution_callback:
                # Usar callback personalizado para ejecución real
                result = await execution_callback(order, portfolio)
            else:
                # Ejecución simulada por defecto
                result = await self._simulate_order_execution(order, portfolio)

            return result

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error executing order for {order.symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "order_status": OrderStatus.FAILED,
            }

    async def _simulate_order_execution(self, order: Order, portfolio: Portfolio) -> Dict[str, Any]:
        """Simular ejecución de orden - use config for latency."""
        # Simular latencia de ejecución - use config value
        await asyncio.sleep(self._simulated_latency_seconds)

        # Simular ejecución exitosa
        order.status = OrderStatus.FILLED

        return {
            "success": True,
            "order_status": OrderStatus.FILLED,
            "executed_price": order.price,
            "executed_quantity": order.quantity,
            "execution_time": datetime.utcnow(),
        }

    def _add_to_history(self, execution_details: Dict[str, Any]) -> None:
        """Agregar ejecución al historial."""
        self.execution_history.append(execution_details)

        # Mantener tamaño máximo del historial
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size :]

    def get_execution_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de ejecución."""
        total_executions = self.executions_attempted
        success_rate = (
            self.executions_successful / total_executions if total_executions > 0 else 0.0
        )

        avg_execution_time = (
            self.total_execution_time_ms / total_executions if total_executions > 0 else 0.0
        )

        return {
            "total_executions": total_executions,
            "successful_executions": self.executions_successful,
            "failed_executions": self.executions_failed,
            "success_rate": success_rate,
            "average_execution_time_ms": avg_execution_time,
            "total_execution_time_ms": self.total_execution_time_ms,
            "max_execution_time_ms": self.max_execution_time_ms,
            "max_latency_ms": self.max_latency_ms,
        }

    def get_recent_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener ejecuciones recientes."""
        return self.execution_history[-limit:] if self.execution_history else []

    def get_executions_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Obtener ejecuciones por símbolo."""
        return [
            execution for execution in self.execution_history if execution.get("symbol") == symbol
        ]

    def clear_history(self) -> None:
        """Limpiar historial de ejecuciones."""
        self.execution_history.clear()
        logger.info("Cleared execution history")

    def reset_statistics(self) -> None:
        """Resetear estadísticas de ejecución."""
        self.executions_attempted = 0
        self.executions_successful = 0
        self.executions_failed = 0
        self.total_execution_time_ms = 0.0
        logger.info("Reset execution statistics")
