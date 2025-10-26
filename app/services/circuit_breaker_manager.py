"""
Circuit Breaker Manager - TASK-15: Refactorización de Servicios

Este módulo implementa el gestor centralizado de circuit breakers, separando
la lógica de circuit breakers de los servicios individuales.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.centralized_config import get_config
from app.models.portfolio import CircuitBreaker, CircuitBreakerState

logger = logging.getLogger(__name__)


class CircuitBreakerType(str, Enum):
    """Tipos de circuit breakers."""

    API_ERRORS = "api_errors"
    SLIPPAGE = "slippage"
    PERFORMANCE = "performance"
    RISK_MANAGEMENT = "risk_management"
    MARKET_DATA = "market_data"
    ORDER_EXECUTION = "order_execution"


class CircuitBreakerManager:
    """
    Gestor centralizado de circuit breakers.

    Responsabilidades:
    - Gestionar múltiples circuit breakers
    - Monitorear estado de servicios
    - Coordinar activación/desactivación
    - Proporcionar métricas centralizadas
    """

    def __init__(self):
        """Inicializar gestor de circuit breakers."""
        self.config = get_config().trading

        # Circuit breakers configurados
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Métricas globales
        self.total_trips = 0
        self.total_resets = 0
        self.active_breakers: List[str] = []

        # Historial de eventos
        self.event_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000

        # Inicializar circuit breakers por defecto
        self._initialize_default_breakers()

    def _initialize_default_breakers(self) -> None:
        """Inicializar circuit breakers por defecto."""
        default_breakers = {
            CircuitBreakerType.API_ERRORS: {
                "max_errors": 5,
                "cooldown_seconds": 300,
                "description": "API errors circuit breaker",
            },
            CircuitBreakerType.SLIPPAGE: {
                "max_errors": 3,
                "cooldown_seconds": 600,
                "description": "Slippage circuit breaker",
            },
            CircuitBreakerType.PERFORMANCE: {
                "max_errors": 3,
                "cooldown_seconds": 1800,
                "description": "Performance circuit breaker",
            },
            CircuitBreakerType.RISK_MANAGEMENT: {
                "max_errors": 2,
                "cooldown_seconds": 3600,
                "description": "Risk management circuit breaker",
            },
            CircuitBreakerType.MARKET_DATA: {
                "max_errors": 10,
                "cooldown_seconds": 120,
                "description": "Market data circuit breaker",
            },
            CircuitBreakerType.ORDER_EXECUTION: {
                "max_errors": 5,
                "cooldown_seconds": 300,
                "description": "Order execution circuit breaker",
            },
        }

        for breaker_type, config in default_breakers.items():
            self.add_circuit_breaker(
                breaker_type.value,
                config["max_errors"],
                config["cooldown_seconds"],
                config["description"],
            )

    def add_circuit_breaker(
        self, name: str, max_errors: int, cooldown_seconds: int, description: str = ""
    ) -> None:
        """Agregar nuevo circuit breaker."""
        breaker = CircuitBreaker(
            name=name, max_errors=max_errors, cooldown_seconds=cooldown_seconds
        )

        self.circuit_breakers[name] = breaker
        logger.info(f"Added circuit breaker: {name}")

        self._log_event(
            "breaker_added",
            {
                "breaker_name": name,
                "max_errors": max_errors,
                "cooldown_seconds": cooldown_seconds,
                "description": description,
            },
        )

    def remove_circuit_breaker(self, name: str) -> bool:
        """Remover circuit breaker."""
        if name in self.circuit_breakers:
            del self.circuit_breakers[name]

            # Remover de activos si estaba activo
            if name in self.active_breakers:
                self.active_breakers.remove(name)

            logger.info(f"Removed circuit breaker: {name}")

            self._log_event("breaker_removed", {"breaker_name": name})

            return True

        return False

    def record_error(self, breaker_name: str, error_message: str = "") -> bool:
        """
        Registrar error en circuit breaker.

        Returns:
            True si el circuit breaker está abierto (debe bloquear operación)
        """
        if breaker_name not in self.circuit_breakers:
            logger.warning(f"Circuit breaker '{breaker_name}' not found")
            return False

        breaker = self.circuit_breakers[breaker_name]

        # Registrar error
        breaker.record_error()

        # Verificar si debe activarse
        if breaker.should_trip() and breaker.state == CircuitBreakerState.CLOSED:
            self._trip_circuit_breaker(breaker_name, error_message)
            return True

        # Si ya está abierto, mantener bloqueado
        if breaker.state == CircuitBreakerState.OPEN:
            return True

        return False

    def record_success(self, breaker_name: str) -> None:
        """Registrar éxito en circuit breaker."""
        if breaker_name not in self.circuit_breakers:
            logger.warning(f"Circuit breaker '{breaker_name}' not found")
            return

        breaker = self.circuit_breakers[breaker_name]

        # Registrar éxito
        breaker.record_success()

        # Si estaba en HALF_OPEN y tiene suficientes éxitos, cerrar
        if breaker.state == CircuitBreakerState.HALF_OPEN and breaker.should_close():
            self._close_circuit_breaker(breaker_name)

    def _trip_circuit_breaker(self, breaker_name: str, error_message: str) -> None:
        """Activar circuit breaker."""
        breaker = self.circuit_breakers[breaker_name]
        breaker.trip()

        self.total_trips += 1
        self.active_breakers.append(breaker_name)

        logger.warning(f"Circuit breaker TRIPPED: {breaker_name}")

        self._log_event(
            "breaker_tripped",
            {
                "breaker_name": breaker_name,
                "error_message": error_message,
                "trip_time": datetime.utcnow(),
                "error_count": breaker.error_count,
            },
        )

    def _close_circuit_breaker(self, breaker_name: str) -> None:
        """Cerrar circuit breaker."""
        breaker = self.circuit_breakers[breaker_name]
        breaker.close()

        self.total_resets += 1
        if breaker_name in self.active_breakers:
            self.active_breakers.remove(breaker_name)

        logger.info(f"Circuit breaker CLOSED: {breaker_name}")

        self._log_event(
            "breaker_closed",
            {
                "breaker_name": breaker_name,
                "close_time": datetime.utcnow(),
                "success_count": breaker.success_count,
            },
        )

    def is_breaker_open(self, breaker_name: str) -> bool:
        """Verificar si circuit breaker está abierto."""
        if breaker_name not in self.circuit_breakers:
            return False

        breaker = self.circuit_breakers[breaker_name]
        return breaker.state == CircuitBreakerState.OPEN

    def get_breaker_status(self, breaker_name: str) -> Optional[Dict[str, Any]]:
        """Obtener estado de circuit breaker."""
        if breaker_name not in self.circuit_breakers:
            return None

        breaker = self.circuit_breakers[breaker_name]

        return {
            "name": breaker.name,
            "state": breaker.state.value,
            "error_count": breaker.error_count,
            "success_count": breaker.success_count,
            "last_error_time": breaker.last_error_time,
            "last_success_time": breaker.last_success_time,
            "is_active": breaker_name in self.active_breakers,
        }

    def get_all_breaker_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Obtener estado de todos los circuit breakers."""
        return {name: self.get_breaker_status(name) for name in self.circuit_breakers.keys()}

    def get_active_breakers(self) -> List[str]:
        """Obtener lista de circuit breakers activos."""
        return self.active_breakers.copy()

    def get_manager_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del gestor."""
        total_breakers = len(self.circuit_breakers)
        active_count = len(self.active_breakers)

        return {
            "total_breakers": total_breakers,
            "active_breakers": active_count,
            "total_trips": self.total_trips,
            "total_resets": self.total_resets,
            "active_breaker_names": self.active_breakers,
            "event_history_size": len(self.event_history),
        }

    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtener eventos recientes."""
        return self.event_history[-limit:] if self.event_history else []

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Registrar evento en historial."""
        event = {"event_type": event_type, "timestamp": datetime.utcnow(), "data": data}

        self.event_history.append(event)

        # Mantener tamaño máximo del historial
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]

    def reset_breaker(self, breaker_name: str) -> bool:
        """Resetear circuit breaker manualmente."""
        if breaker_name not in self.circuit_breakers:
            return False

        breaker = self.circuit_breakers[breaker_name]
        breaker.reset()

        if breaker_name in self.active_breakers:
            self.active_breakers.remove(breaker_name)

        logger.info(f"Manually reset circuit breaker: {breaker_name}")

        self._log_event(
            "breaker_reset",
            {"breaker_name": breaker_name, "reset_time": datetime.utcnow()},
        )

        return True

    def reset_all_breakers(self) -> None:
        """Resetear todos los circuit breakers."""
        for breaker_name in list(self.circuit_breakers.keys()):
            self.reset_breaker(breaker_name)

        logger.info("Reset all circuit breakers")

    def clear_history(self) -> None:
        """Limpiar historial de eventos."""
        self.event_history.clear()
        logger.info("Cleared circuit breaker event history")

    def get_active_breakers(self) -> List[str]:
        """Obtener lista de circuit breakers activos (abiertos)."""
        return [
            name
            for name, breaker in self.circuit_breakers.items()
            if breaker.state == CircuitBreakerState.OPEN
        ]
