"""
Drawdown Controllers

Implementa control dinámico de drawdowns:
- Rolling maximum drawdown tracking
- Circuit breakers por drawdown (por estrategia, global)
- Recovery protocols después de drawdowns
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

from app.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class BaseDrawdownController(ABC):
    """Clase base para drawdown controllers."""

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializar drawdown controller.

        Args:
            config: Configuración del controller
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def assess_drawdown(self, portfolio: Portfolio, **kwargs) -> Dict[str, Any]:
        """
        Evaluar drawdown del portfolio.

        Args:
            portfolio: Portfolio a evaluar
            **kwargs: Argumentos adicionales

        Returns:
            Evaluación de drawdown
        """


class DrawdownController(BaseDrawdownController):
    """
    Drawdown Controller principal.

    Controla drawdowns del portfolio y estrategias individuales.
    """

    def __init__(self, config: Dict[str, Any]):
        """Inicializar drawdown controller."""
        super().__init__(config)

        # Configuración de circuit breakers
        self.max_drawdown_limit = config.get('max_drawdown_limit', 0.20)  # 20% por defecto
        self.strategy_max_drawdown_limit = config.get(
            'strategy_max_drawdown_limit', 0.25
        )  # 25% por estrategia
        self.recovery_threshold = config.get('recovery_threshold', 0.05)  # 5% recovery

        # Historial de valores
        self.portfolio_value_history: List[Dict[str, Any]] = []
        self.strategy_value_history: Dict[str, List[Dict[str, Any]]] = {}

        # Estado de circuit breakers
        self.circuit_breaker_active = False
        self.circuit_breaker_reason = None
        self.circuit_breaker_timestamp: Optional[datetime] = None

        self.strategy_circuit_breakers: Dict[str, bool] = {}

        # Estado de recovery
        self.recovery_mode = False
        self.recovery_start_value: Optional[Decimal] = None

        # Configuración de tracking
        self.lookback_period = config.get('lookback_period', 252)  # 1 año de trading
        self.rolling_window = config.get('rolling_window', 20)  # 20 días

    def assess_drawdown(
        self,
        portfolio: Portfolio,
        strategy_performance: Optional[Dict[str, Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Evaluar drawdown completo del portfolio.

        Args:
            portfolio: Portfolio a evaluar
            strategy_performance: Performance por estrategia (opcional)
            **kwargs: Argumentos adicionales

        Returns:
            Evaluación completa de drawdown
        """
        try:
            # Actualizar historial
            self._update_portfolio_history(portfolio)

            # Calcular drawdowns
            portfolio_drawdown = self._calculate_portfolio_drawdown()
            rolling_drawdown = self._calculate_rolling_drawdown()

            # Evaluar drawdowns por estrategia
            strategy_drawdowns = {}
            if strategy_performance:
                strategy_drawdowns = self._assess_strategy_drawdowns(strategy_performance)

            # Verificar circuit breakers
            circuit_breaker_status = self._check_circuit_breakers(
                portfolio_drawdown, strategy_drawdowns
            )

            # Evaluar recovery
            recovery_status = self._assess_recovery(portfolio_drawdown)

            return {
                'portfolio_drawdown': portfolio_drawdown,
                'rolling_drawdown': rolling_drawdown,
                'strategy_drawdowns': strategy_drawdowns,
                'circuit_breaker_status': circuit_breaker_status,
                'recovery_status': recovery_status,
                'timestamp': datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error evaluando drawdown: {e}", exc_info=True)
            return {'error': str(e)}

    def _update_portfolio_history(self, portfolio: Portfolio) -> None:
        """Actualizar historial de valores del portfolio."""
        entry = {
            'timestamp': datetime.utcnow(),
            'portfolio_value': portfolio.total_equity,
            'cash': portfolio.cash,
            'positions_value': portfolio.total_equity - portfolio.cash,
        }

        self.portfolio_value_history.append(entry)

        # Mantener solo lookback_period días
        cutoff = datetime.utcnow() - timedelta(days=self.lookback_period)
        self.portfolio_value_history = [
            entry for entry in self.portfolio_value_history if entry['timestamp'] > cutoff
        ]

    def _calculate_portfolio_drawdown(self) -> Dict[str, Any]:
        """Calcular drawdown del portfolio."""
        if len(self.portfolio_value_history) < 2:
            return {
                'current_drawdown': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0,
                'underwater_curve': [],
            }

        # Extraer valores
        values = [entry['portfolio_value'] for entry in self.portfolio_value_history]
        timestamps = [entry['timestamp'] for entry in self.portfolio_value_history]

        # Calcular máximo acumulado (peak)
        peak_values = []
        current_peak = Decimal("0")
        for value in values:
            if value > current_peak:
                current_peak = value
            peak_values.append(current_peak)

        # Calcular drawdowns
        drawdowns = []
        for i, (value, peak) in enumerate(zip(values, peak_values)):
            if peak > 0:
                drawdown = float((peak - value) / peak)
            else:
                drawdown = 0.0
            drawdowns.append(drawdown)

        # Drawdown actual
        current_drawdown = drawdowns[-1] if drawdowns else 0.0

        # Maximum drawdown
        max_drawdown = max(drawdowns) if drawdowns else 0.0

        # Duración del máximo drawdown
        max_drawdown_duration = self._calculate_drawdown_duration(drawdowns, timestamps)

        return {
            'current_drawdown': current_drawdown,
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_duration,
            'peak_value': float(peak_values[-1]) if peak_values else 0.0,
            'current_value': float(values[-1]) if values else 0.0,
            'underwater_curve': drawdowns,
        }

    def _calculate_rolling_drawdown(self) -> Dict[str, Any]:
        """Calcular drawdown rolling."""
        if len(self.portfolio_value_history) < self.rolling_window:
            return {'rolling_max_drawdown': 0.0, 'rolling_avg_drawdown': 0.0}

        # Últimos N valores
        recent_values = [
            float(entry['portfolio_value'])
            for entry in self.portfolio_value_history[-self.rolling_window:]
        ]

        # Peak en ventana
        window_peak = max(recent_values)
        current_value = recent_values[-1]

        # Drawdown en ventana
        if window_peak > 0:
            rolling_drawdown = (window_peak - current_value) / window_peak
        else:
            rolling_drawdown = 0.0

        # Promedio de drawdowns en ventana
        if len(self.portfolio_value_history) >= self.rolling_window:
            drawdowns_window = []
            for i in range(
                len(self.portfolio_value_history) - self.rolling_window,
                len(self.portfolio_value_history),
            ):
                window_values = [
                    float(entry['portfolio_value'])
                    for entry in self.portfolio_value_history[
                        max(0, i - self.rolling_window): i + 1
                    ]
                ]
                if window_values:
                    window_peak = max(window_values)
                    window_current = window_values[-1]
                    if window_peak > 0:
                        drawdown = (window_peak - window_current) / window_peak
                        drawdowns_window.append(drawdown)

            rolling_avg_drawdown = np.mean(drawdowns_window) if drawdowns_window else 0.0
        else:
            rolling_avg_drawdown = 0.0

        return {
            'rolling_max_drawdown': float(rolling_drawdown),
            'rolling_avg_drawdown': float(rolling_avg_drawdown),
            'window_size': self.rolling_window,
        }

    def _calculate_drawdown_duration(
        self, drawdowns: List[float], timestamps: List[datetime]
    ) -> int:
        """Calcular duración del máximo drawdown en días."""
        if not drawdowns or not timestamps:
            return 0

        max_drawdown = max(drawdowns)
        max_dd_idx = drawdowns.index(max_drawdown)

        # Encontrar inicio del drawdown (último peak antes del max DD)
        start_idx = max_dd_idx
        for i in range(max_dd_idx - 1, -1, -1):
            if drawdowns[i] < drawdowns[start_idx]:
                start_idx = i
                break

        # Encontrar fin del drawdown (cuando vuelve al peak)
        end_idx = max_dd_idx
        for i in range(max_dd_idx + 1, len(drawdowns)):
            if drawdowns[i] == 0:
                end_idx = i
                break

        if start_idx < len(timestamps) and end_idx < len(timestamps):
            duration = (timestamps[end_idx] - timestamps[start_idx]).days
            return max(0, duration)

        return 0

    def _assess_strategy_drawdowns(
        self, strategy_performance: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Evaluar drawdowns por estrategia."""
        strategy_drawdowns = {}

        for strategy, performance in strategy_performance.items():
            # Obtener drawdown de performance
            max_drawdown = performance.get('max_drawdown', 0.0)
            current_drawdown = performance.get('current_drawdown', 0.0)

            # Verificar circuit breaker por estrategia
            circuit_breaker_active = False
            if current_drawdown > self.strategy_max_drawdown_limit:
                circuit_breaker_active = True
                self.strategy_circuit_breakers[strategy] = True
                self.logger.warning(
                    f"Circuit breaker activado para estrategia {strategy}: "
                    f"drawdown {current_drawdown:.2%} > límite {self.strategy_max_drawdown_limit:.2%}"
                )
            else:
                self.strategy_circuit_breakers[strategy] = False

            strategy_drawdowns[strategy] = {
                'current_drawdown': current_drawdown,
                'max_drawdown': max_drawdown,
                'circuit_breaker_active': circuit_breaker_active,
                'limit': self.strategy_max_drawdown_limit,
            }

        return strategy_drawdowns

    def _check_circuit_breakers(
        self, portfolio_drawdown: Dict[str, Any], strategy_drawdowns: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Verificar y activar circuit breakers."""
        current_drawdown = portfolio_drawdown.get('current_drawdown', 0.0)
        portfolio_drawdown.get('max_drawdown', 0.0)

        # Verificar circuit breaker global
        if current_drawdown > self.max_drawdown_limit:
            if not self.circuit_breaker_active:
                self.circuit_breaker_active = True
                self.circuit_breaker_reason = (
                    f"Drawdown global {current_drawdown:.2%} > límite {self.max_drawdown_limit:.2%}"
                )
                self.circuit_breaker_timestamp = datetime.utcnow()
                self.logger.critical(f"🚨 CIRCUIT BREAKER ACTIVADO: {self.circuit_breaker_reason}")

        # Verificar si debe desactivarse
        if self.circuit_breaker_active and current_drawdown <= self.max_drawdown_limit * 0.9:
            # Desactivar si drawdown baja a 90% del límite
            self.circuit_breaker_active = False
            self.logger.info("✅ Circuit breaker desactivado: drawdown bajo control")

        # Contar estrategias con circuit breakers activos
        active_strategy_breakers = sum(1 for cb in self.strategy_circuit_breakers.values() if cb)

        return {
            'global_circuit_breaker_active': self.circuit_breaker_active,
            'global_circuit_breaker_reason': self.circuit_breaker_reason,
            'global_circuit_breaker_timestamp': (
                self.circuit_breaker_timestamp.isoformat()
                if self.circuit_breaker_timestamp
                else None
            ),
            'strategy_circuit_breakers_active': active_strategy_breakers,
            'strategy_circuit_breakers': dict(self.strategy_circuit_breakers),
            'max_drawdown_limit': self.max_drawdown_limit,
            'current_drawdown': current_drawdown,
        }

    def _assess_recovery(self, portfolio_drawdown: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluar estado de recovery después de drawdown."""
        current_drawdown = portfolio_drawdown.get('current_drawdown', 0.0)
        portfolio_drawdown.get('peak_value', 0.0)
        current_value = portfolio_drawdown.get('current_value', 0.0)

        # Entrar en recovery mode si drawdown es significativo
        if current_drawdown > self.recovery_threshold and not self.recovery_mode:
            self.recovery_mode = True
            self.recovery_start_value = Decimal(str(current_value))
            self.logger.info(f"Recovery mode activado: drawdown {current_drawdown:.2%}")

        # Salir de recovery mode si recuperamos
        recovery_complete = False
        recovery_percentage = 0.0

        if self.recovery_mode:
            if self.recovery_start_value and current_value > 0:
                recovery_from_peak = (current_value - float(self.recovery_start_value)) / float(
                    self.recovery_start_value
                )
                recovery_percentage = recovery_from_peak

                # Recovery completo si recuperamos el threshold
                if recovery_percentage >= self.recovery_threshold:
                    recovery_complete = True
                    self.recovery_mode = False
                    self.logger.info(
                        f"✅ Recovery completo: {recovery_percentage:.2%} desde inicio recovery"
                    )

        return {
            'recovery_mode_active': self.recovery_mode,
            'recovery_complete': recovery_complete,
            'recovery_percentage': recovery_percentage,
            'recovery_start_value': (
                float(self.recovery_start_value) if self.recovery_start_value else None
            ),
            'current_drawdown': current_drawdown,
            'recovery_threshold': self.recovery_threshold,
        }

    def reset_circuit_breaker(self, strategy: Optional[str] = None) -> bool:
        """
        Resetear circuit breaker manualmente.

        Args:
            strategy: Estrategia específica (None = global)

        Returns:
            True si se reseteó exitosamente
        """
        if strategy:
            if strategy in self.strategy_circuit_breakers:
                self.strategy_circuit_breakers[strategy] = False
                self.logger.info(f"Circuit breaker reseteado para estrategia {strategy}")
                return True
        else:
            self.circuit_breaker_active = False
            self.circuit_breaker_reason = None
            self.circuit_breaker_timestamp = None
            self.logger.info("Circuit breaker global reseteado")
            return True

        return False

    def get_status(self) -> Dict[str, Any]:
        """Obtener estado del controller."""
        return {
            'circuit_breaker_active': self.circuit_breaker_active,
            'strategy_circuit_breakers': dict(self.strategy_circuit_breakers),
            'recovery_mode': self.recovery_mode,
            'history_size': len(self.portfolio_value_history),
            'max_drawdown_limit': self.max_drawdown_limit,
            'strategy_max_drawdown_limit': self.strategy_max_drawdown_limit,
        }
