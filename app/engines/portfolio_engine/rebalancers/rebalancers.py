"""
Portfolio Rebalancers

Implementa diferentes estrategias de rebalanceo dinámico:
- Threshold-based rebalancing
- Time-based rebalancing
- Volatility-targeting rebalancing
- Transaction cost-aware rebalancing
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class BaseRebalancer(ABC):
    """Clase base para rebalanceadores."""

    def __init__(self, config: dict[str, Any]):
        """
        Inicializar rebalancer.

        Args:
            config: Configuración del rebalancer
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.last_rebalance_time: datetime | None = None
        self.rebalance_count = 0

    @abstractmethod
    def should_rebalance(
        self,
        current_weights: dict[str, float],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        **kwargs,
    ) -> bool:
        """
        Determinar si se debe rebalancear.

        Args:
            current_weights: Pesos actuales del portfolio
            target_weights: Pesos objetivo
            portfolio_value: Valor total del portfolio
            **kwargs: Argumentos adicionales

        Returns:
            True si se debe rebalancear
        """

    @abstractmethod
    def calculate_rebalance_trades(
        self,
        current_positions: dict[str, Any],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        prices: dict[str, Decimal],
    ) -> list[dict[str, Any]]:
        """
        Calcular trades necesarios para rebalancear.

        Args:
            current_positions: Posiciones actuales
            target_weights: Pesos objetivo
            portfolio_value: Valor total del portfolio
            prices: Precios actuales de los activos

        Returns:
            Lista de trades necesarios
        """


class ThresholdRebalancer(BaseRebalancer):
    """
    Threshold-based Rebalancer.

    Rebalancea cuando los pesos se desvían del objetivo más de un umbral.
    """

    def __init__(self, config: dict[str, Any]):
        """Inicializar threshold rebalancer."""
        super().__init__(config)
        self.threshold = config.get("threshold", 0.05)  # 5% por defecto
        self.min_rebalance_interval = timedelta(days=config.get("min_rebalance_interval_days", 1))

    def should_rebalance(
        self,
        current_weights: dict[str, float],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        **kwargs,
    ) -> bool:
        """Verificar si se debe rebalancear basado en umbral."""
        # Verificar intervalo mínimo
        if self.last_rebalance_time:
            time_since_last = datetime.utcnow() - self.last_rebalance_time
            if time_since_last < self.min_rebalance_interval:
                return False

        # Verificar desviación de pesos
        max_deviation = 0.0
        for symbol in target_weights:
            current_weight = current_weights.get(symbol, 0.0)
            target_weight = target_weights.get(symbol, 0.0)
            deviation = abs(current_weight - target_weight)
            max_deviation = max(max_deviation, deviation)

        should_rebalance = bool(max_deviation > self.threshold)

        if should_rebalance:
            self.logger.info(
                f"Threshold rebalance triggered: max deviation {max_deviation:.2%} > {self.threshold:.2%}"
            )

        return should_rebalance

    def calculate_rebalance_trades(
        self,
        current_positions: dict[str, Any],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        prices: dict[str, Decimal],
    ) -> list[dict[str, Any]]:
        """Calcular trades para rebalancear."""
        trades = []

        for symbol, target_weight in target_weights.items():
            current_position = current_positions.get(symbol, {})
            current_value = Decimal(str(current_position.get("market_value", 0)))
            current_quantity = Decimal(str(current_position.get("quantity", 0)))

            target_value = portfolio_value * Decimal(str(target_weight))
            price = prices.get(symbol, Decimal("1"))

            if price > 0:
                target_quantity = target_value / price
                quantity_diff = target_quantity - current_quantity

                # Solo agregar trade si la diferencia es significativa
                if abs(quantity_diff) > Decimal("0.01"):
                    trades.append(
                        {
                            "symbol": symbol,
                            "quantity": float(quantity_diff),
                            "target_weight": target_weight,
                            "current_weight": (
                                float(current_value / portfolio_value)
                                if portfolio_value > 0
                                else 0.0
                            ),
                            "reason": "threshold_rebalance",
                        }
                    )

        return trades


class TimeBasedRebalancer(BaseRebalancer):
    """
    Time-based Rebalancer.

    Rebalancea en intervalos fijos (diario, semanal, mensual).
    """

    def __init__(self, config: dict[str, Any]):
        """Inicializar time-based rebalancer."""
        super().__init__(config)
        self.rebalance_frequency = config.get("frequency", "daily")  # daily, weekly, monthly
        self._set_frequency_interval()

    def _set_frequency_interval(self) -> None:
        """Establecer intervalo de rebalanceo basado en frecuencia."""
        if self.rebalance_frequency == "daily":
            self.interval = timedelta(days=1)
        elif self.rebalance_frequency == "weekly":
            self.interval = timedelta(weeks=1)
        elif self.rebalance_frequency == "monthly":
            self.interval = timedelta(days=30)
        else:
            self.interval = timedelta(days=1)
            self.logger.warning(
                f"Frecuencia desconocida: {self.rebalance_frequency}. Usando daily."
            )

    def should_rebalance(
        self,
        current_weights: dict[str, float],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        **kwargs,
    ) -> bool:
        """Verificar si es tiempo de rebalancear."""
        if self.last_rebalance_time is None:
            # Primera vez, rebalancear
            return True

        time_since_last = datetime.utcnow() - self.last_rebalance_time
        should_rebalance = time_since_last >= self.interval

        if should_rebalance:
            self.logger.info(
                f"Time-based rebalance triggered: {time_since_last.days} days since last rebalance"
            )

        return should_rebalance

    def calculate_rebalance_trades(
        self,
        current_positions: dict[str, Any],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        prices: dict[str, Decimal],
    ) -> list[dict[str, Any]]:
        """Calcular trades para rebalancear."""
        trades = []

        for symbol, target_weight in target_weights.items():
            current_position = current_positions.get(symbol, {})
            current_value = Decimal(str(current_position.get("market_value", 0)))
            current_quantity = Decimal(str(current_position.get("quantity", 0)))

            target_value = portfolio_value * Decimal(str(target_weight))
            price = prices.get(symbol, Decimal("1"))

            if price > 0:
                target_quantity = target_value / price
                quantity_diff = target_quantity - current_quantity

                if abs(quantity_diff) > Decimal("0.01"):
                    trades.append(
                        {
                            "symbol": symbol,
                            "quantity": float(quantity_diff),
                            "target_weight": target_weight,
                            "current_weight": (
                                float(current_value / portfolio_value)
                                if portfolio_value > 0
                                else 0.0
                            ),
                            "reason": f"time_based_{self.rebalance_frequency}",
                        }
                    )

        return trades


class VolatilityTargetingRebalancer(BaseRebalancer):
    """
    Volatility-targeting Rebalancer.

    Rebalancea para mantener volatilidad objetivo del portfolio.
    """

    def __init__(self, config: dict[str, Any]):
        """Inicializar volatility-targeting rebalancer."""
        super().__init__(config)
        self.target_volatility = config.get("target_volatility", 0.15)  # 15% por defecto
        self.volatility_threshold = config.get("volatility_threshold", 0.02)  # 2% desviación
        self.cov_matrix = None  # Se actualizará con datos reales

    def should_rebalance(
        self,
        current_weights: dict[str, float],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        **kwargs,
    ) -> bool:
        """Verificar si se debe rebalancear basado en volatilidad."""
        # Obtener matriz de covarianza
        cov_matrix = kwargs.get("cov_matrix")
        if cov_matrix is None:
            self.logger.warning("Covariance matrix not provided. Skipping volatility check.")
            return False

        self.cov_matrix = cov_matrix

        # Calcular volatilidad actual del portfolio
        weights_array = np.array(
            [current_weights.get(s, 0.0) for s in sorted(current_weights.keys())]
        )

        # Asegurar que la matriz y los pesos tienen el mismo orden
        if len(weights_array) != len(cov_matrix):
            self.logger.warning("Mismatch entre número de pesos y matriz de covarianza")
            return False

        portfolio_volatility = np.sqrt(np.dot(weights_array, np.dot(cov_matrix, weights_array)))

        # Verificar si se desvia del objetivo
        deviation = abs(float(portfolio_volatility) - self.target_volatility)
        should_rebalance = bool(deviation > self.volatility_threshold)

        if should_rebalance:
            self.logger.info(
                "Volatility-targeting rebalance triggered: "
                f"current volatility {portfolio_volatility:.2%}, "
                f"target {self.target_volatility:.2%}, "
                f"deviation {deviation:.2%}"
            )

        return should_rebalance

    def calculate_rebalance_trades(
        self,
        current_positions: dict[str, Any],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        prices: dict[str, Decimal],
    ) -> list[dict[str, Any]]:
        """Calcular trades para rebalancear."""
        # Similar a threshold rebalancer pero con ajuste de volatilidad
        trades = []

        for symbol, target_weight in target_weights.items():
            current_position = current_positions.get(symbol, {})
            current_value = Decimal(str(current_position.get("market_value", 0)))
            current_quantity = Decimal(str(current_position.get("quantity", 0)))

            target_value = portfolio_value * Decimal(str(target_weight))
            price = prices.get(symbol, Decimal("1"))

            if price > 0:
                target_quantity = target_value / price
                quantity_diff = target_quantity - current_quantity

                if abs(quantity_diff) > Decimal("0.01"):
                    trades.append(
                        {
                            "symbol": symbol,
                            "quantity": float(quantity_diff),
                            "target_weight": target_weight,
                            "current_weight": (
                                float(current_value / portfolio_value)
                                if portfolio_value > 0
                                else 0.0
                            ),
                            "reason": "volatility_targeting",
                        }
                    )

        return trades


class TransactionCostAwareRebalancer(BaseRebalancer):
    """
    Transaction Cost-aware Rebalancer.

    Rebalancea solo si el beneficio esperado supera los costos de transacción.
    """

    def __init__(self, config: dict[str, Any]):
        """Inicializar transaction cost-aware rebalancer."""
        super().__init__(config)
        self.commission_rate = config.get("commission_rate", 0.001)  # 0.1% por defecto
        self.slippage_rate = config.get("slippage_rate", 0.0005)  # 0.05% por defecto
        self.min_benefit_threshold = config.get(
            "min_benefit_threshold", 0.001
        )  # 0.1% beneficio mínimo
        self.base_rebalancer = ThresholdRebalancer(config)  # Usar threshold como base

    def should_rebalance(
        self,
        current_weights: dict[str, float],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        **kwargs,
    ) -> bool:
        """Verificar si se debe rebalancear considerando costos."""
        # Primero verificar si el rebalancer base recomienda rebalancear
        if not self.base_rebalancer.should_rebalance(
            current_weights, target_weights, portfolio_value, **kwargs
        ):
            return False

        # Calcular costos de transacción estimados
        current_positions = kwargs.get("current_positions", {})
        prices = kwargs.get("prices", {})

        trades = self.base_rebalancer.calculate_rebalance_trades(
            current_positions, target_weights, portfolio_value, prices
        )

        total_cost = sum(
            abs(Decimal(str(trade["quantity"])))
            * prices.get(trade["symbol"], Decimal("1"))
            * Decimal(str(self.commission_rate + self.slippage_rate))
            for trade in trades
        )

        # Calcular beneficio esperado del rebalanceo
        # (simplificado: asumir que reduce desviación = mejora eficiencia)
        max_deviation = max(
            abs(current_weights.get(s, 0.0) - target_weights.get(s, 0.0))
            for s in set(list(current_weights.keys()) + list(target_weights.keys()))
        )

        # Beneficio estimado = reducción de desviación * valor del portfolio * factor de mejora
        estimated_benefit = Decimal(str(max_deviation)) * portfolio_value * Decimal("0.01")

        # Rebalancear solo si beneficio > costos
        should_rebalance = bool(estimated_benefit > total_cost)

        if not should_rebalance:
            self.logger.info(
                "Transaction cost-aware rebalance skipped: "
                f"estimated benefit {estimated_benefit:.2f} < total cost {total_cost:.2f}"
            )

        return should_rebalance

    def calculate_rebalance_trades(
        self,
        current_positions: dict[str, Any],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        prices: dict[str, Decimal],
    ) -> list[dict[str, Any]]:
        """Calcular trades considerando costos de transacción."""
        # Usar base rebalancer pero añadir información de costos
        trades = self.base_rebalancer.calculate_rebalance_trades(
            current_positions, target_weights, portfolio_value, prices
        )

        # Añadir estimación de costos a cada trade
        for trade in trades:
            symbol = trade["symbol"]
            quantity = abs(Decimal(str(trade["quantity"])))
            price = prices.get(symbol, Decimal("1"))

            trade_value = quantity * price
            commission = trade_value * Decimal(str(self.commission_rate))
            slippage = trade_value * Decimal(str(self.slippage_rate))
            total_cost = commission + slippage

            trade["estimated_commission"] = float(commission)
            trade["estimated_slippage"] = float(slippage)
            trade["estimated_total_cost"] = float(total_cost)

        return trades


class HybridRebalancer(BaseRebalancer):
    """
    Hybrid Rebalancer.

    Combina múltiples estrategias de rebalanceo.
    """

    def __init__(self, config: dict[str, Any]):
        """Inicializar hybrid rebalancer."""
        super().__init__(config)

        # Crear rebalanceadores base
        self.rebalancers: list[BaseRebalancer] = []

        if config.get("use_threshold", True):
            self.rebalancers.append(ThresholdRebalancer(config))

        if config.get("use_time_based", True):
            self.rebalancers.append(TimeBasedRebalancer(config))

        if config.get("use_volatility_targeting", False):
            self.rebalancers.append(VolatilityTargetingRebalancer(config))

        if config.get("use_transaction_cost_aware", True):
            self.rebalancers.append(TransactionCostAwareRebalancer(config))

    def should_rebalance(
        self,
        current_weights: dict[str, float],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        **kwargs,
    ) -> bool:
        """Verificar si se debe rebalancear usando estrategia híbrida."""
        # Si cualquier rebalancer recomienda rebalancear, hacerlo
        return any(
            rebalancer.should_rebalance(current_weights, target_weights, portfolio_value, **kwargs)
            for rebalancer in self.rebalancers
        )

    def calculate_rebalance_trades(
        self,
        current_positions: dict[str, Any],
        target_weights: dict[str, float],
        portfolio_value: Decimal,
        prices: dict[str, Decimal],
    ) -> list[dict[str, Any]]:
        """Calcular trades usando el primer rebalancer disponible."""
        if self.rebalancers:
            return self.rebalancers[0].calculate_rebalance_trades(
                current_positions, target_weights, portfolio_value, prices
            )
        return []
