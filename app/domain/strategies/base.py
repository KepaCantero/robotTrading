"""
BaseStrategy - Clase base abstracta para todas las estrategias de trading.

Implementa la interfaz común que todas las estrategias deben seguir,
permitiendo hot-swapping y gestión dinámica de estrategias.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.core.centralized_config import get_config
from app.domain.models.market_data import Quote
from app.domain.models.portfolio import Portfolio
from app.domain.models.signal import Signal, SignalType

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """Clase base abstracta para todas las estrategias de trading."""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Inicializar estrategia con configuración.

        Args:
            config: Diccionario con parámetros de configuración
        """
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.description = config.get("description", "")
        self.version = config.get("version", "1.0.0")
        self.is_active = False
        self.created_at = datetime.now(timezone.utc)

        logger.info(
            "Strategy initialized",
            extra={
                "strategy_name": self.name,
                "strategy_class": self.__class__.__name__,
                "version": self.version,
                "is_active": self.is_active,
            },
        )

    @abstractmethod
    def generate_signals(self, market_data: Quote) -> list[Signal]:
        """
        Genera señales de trading basadas en datos del mercado.

        Args:
            market_data: Datos de mercado actuales

        Returns:
            Lista de señales generadas
        """

    @abstractmethod
    def risk_check(self, signal: Signal, portfolio: Portfolio) -> bool:
        """
        Verifica si la señal cumple criterios de riesgo.

        Args:
            signal: Señal a verificar
            portfolio: Estado actual del portfolio

        Returns:
            True si la señal pasa el risk check, False en caso contrario
        """

    def get_parameters(self) -> dict[str, Any]:
        """
        Obtener parámetros actuales de la estrategia.

        Returns:
            Copia del diccionario de configuración
        """
        return self.config.copy()

    def update_parameters(self, params: dict[str, Any]) -> None:
        """
        Actualizar parámetros dinámicamente.

        Args:
            params: Nuevos parámetros a aplicar
        """
        old_config = self.config.copy()
        self.config.update(params)

        logger.info(
            "Strategy parameters updated",
            extra={
                "strategy_name": self.name,
                "updated_params": list(params.keys()),
                "old_config": old_config,
                "new_config": self.config,
            },
        )

    def validate_config(self) -> bool:
        """
        Validar configuración de la estrategia.

        Returns:
            True si la configuración es válida, False en caso contrario
        """
        required_params = self.get_required_parameters()
        is_valid = all(param in self.config for param in required_params)

        if not is_valid:
            missing_params = [p for p in required_params if p not in self.config]
            logger.warning(
                "Strategy configuration validation failed",
                extra={
                    "strategy_name": self.name,
                    "missing_params": missing_params,
                    "required_params": required_params,
                    "is_valid": is_valid,
                },
            )
        else:
            logger.debug(
                "Strategy configuration validated",
                extra={
                    "strategy_name": self.name,
                    "is_valid": is_valid,
                },
            )

        return is_valid

    @abstractmethod
    def get_required_parameters(self) -> list[str]:
        """
        Obtener parámetros requeridos para la estrategia.

        Returns:
            Lista de nombres de parámetros requeridos
        """

    def get_position_size(self, signal: Signal, portfolio: Portfolio) -> Decimal:
        """
        Calcular tamaño de posición basado en la señal y portfolio.

        Args:
            signal: Señal de trading
            portfolio: Estado del portfolio

        Returns:
            Tamaño de posición calculado (en número de acciones/shares)
        """
        # First try strategy-specific config, then fall back to centralized config
        if "max_position_size" in self.config:
            max_position_size = Decimal(str(self.config["max_position_size"]))
        else:
            try:
                config = get_config()
                max_position_size = Decimal(str(getattr(
                    config.trading, 'max_position_size', 0.1
                )))
            except (AttributeError, ValueError):
                max_position_size = Decimal("0.1")
        available_cash = portfolio.cash

        if signal.signal_type == SignalType.BUY:
            # FIX: Para BUY, calcular tamaño basado en capital disponible, no en signal.volume
            # signal.volume es solo un placeholder (1) para señales
            # El tamaño real se calcula basado en:
            # - Capital disponible
            # - max_position_size (% del capital que podemos usar)
            # - Precio de la acción

            # Capital máximo que podemos usar para esta posición
            max_position_value = available_cash * max_position_size

            # Número máximo de acciones que podemos comprar
            position_size = max_position_value / signal.price

            # Asegurar mínimo 1 acción
            position_size = max(position_size, Decimal("1"))

            return position_size.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        else:
            # FIX: Para SELL, usar la posición existente, no signal.volume
            # Buscar posición existente para este símbolo
            existing_position = None
            for pos in portfolio.positions:
                if pos.symbol == signal.symbol:
                    existing_position = pos
                    break

            if existing_position:
                # Vender toda la posición o una fracción
                # Por defecto, usar toda la posición disponible
                return existing_position.quantity
            else:
                # No hay posición, no podemos vender
                return Decimal("0")

    def get_stop_loss_price(self, signal: Signal) -> Decimal | None:
        """
        TASK-IND-2: Calcular precio de stop loss dinámico basado en ATR.

        Usa ATR * 2 para calcular stop loss adaptativo a la volatilidad.
        Si ATR no está disponible, usa stop loss porcentual fijo.

        Args:
            signal: Señal de trading

        Returns:
            Precio de stop loss o None si no aplica
        """
        # TASK-IND-2: Intentar usar ATR dinámico si está disponible
        atr_multiplier = Decimal(str(self.config.get("atr_multiplier", 2.0)))

        # Verificar si tenemos ATR en los metadatos de la señal
        if hasattr(signal, 'metadata') and signal.metadata:
            atr = signal.metadata.get('atr')
            if atr is not None:
                atr_value = Decimal(str(atr))
                stop_distance = atr_value * atr_multiplier

                # FIX: Use signal_type instead of direction
                if signal.signal_type == SignalType.BUY:
                    return signal.price - stop_distance
                elif signal.signal_type == SignalType.SELL:
                    return signal.price + stop_distance

        # Fallback: usar stop loss porcentual desde config centralizado
        # First try strategy-specific config, then fall back to centralized config
        stop_loss_pct = None
        if "stop_loss" in self.config:
            stop_loss_pct = Decimal(str(self.config["stop_loss"]))
        else:
            try:
                config = get_config()
                stop_loss_pct = Decimal(str(getattr(
                    config.trading, 'stop_loss_pct', 0.05
                )))
            except (AttributeError, ValueError):
                stop_loss_pct = Decimal("0.05")

        # FIX: Use signal_type instead of direction
        if signal.signal_type == SignalType.BUY:
            return signal.price * (1 - stop_loss_pct)
        elif signal.signal_type == SignalType.SELL:
            return signal.price * (1 + stop_loss_pct)

        return None

    def get_take_profit_price(self, signal: Signal) -> Decimal | None:
        """
        Calcular precio de take profit.

        Args:
            signal: Señal de trading

        Returns:
            Precio de take profit o None si no aplica
        """
        # First try strategy-specific config, then fall back to centralized config
        take_profit_pct = None
        if "take_profit" in self.config:
            take_profit_pct = Decimal(str(self.config["take_profit"]))
        else:
            try:
                config = get_config()
                take_profit_pct = Decimal(str(getattr(
                    config.trading, 'take_profit_pct', 0.10
                )))
            except (AttributeError, ValueError):
                take_profit_pct = Decimal("0.10")

        # FIX: Use signal_type instead of direction
        if signal.signal_type == SignalType.BUY:
            return signal.price * (1 + take_profit_pct)
        elif signal.signal_type == SignalType.SELL:
            return signal.price * (1 - take_profit_pct)

        return None

    def __str__(self) -> str:
        """Representación string de la estrategia."""
        return f"{self.__class__.__name__}(name={self.name}, active={self.is_active})"

    def __repr__(self) -> str:
        """Representación detallada de la estrategia."""
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"version='{self.version}', "
            f"active={self.is_active}, "
            f"created_at={self.created_at})"
        )
