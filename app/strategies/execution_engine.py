"""
ExecutionEngine - Motor de ejecución centralizado.

Coordina la ejecución de estrategias activas, generación de señales,
validación de riesgo y ejecución de órdenes.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.models.market_data import Quote
from app.models.portfolio import Portfolio
from app.models.signal import Signal

from .registry import StrategyRegistry
from .strategy_logger import StrategyLogger

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Motor de ejecución centralizado."""

    def __init__(self, registry: StrategyRegistry, logger: StrategyLogger):
        """
        Inicializar motor de ejecución.

        Args:
            registry: Registry de estrategias
            logger: Logger de estrategias
        """
        self.registry = registry
        self.logger = logger
        self.is_running = False
        self.created_at = datetime.utcnow()
        self.cycle_count = 0
        self.total_signals_generated = 0
        self.total_signals_executed = 0

    def start(self) -> None:
        """Iniciar motor de ejecución."""
        if self.is_running:
            logger.warning("Execution engine already running")
            return

        self.is_running = True
        logger.info("Execution engine started")

    def stop(self) -> None:
        """Detener motor de ejecución."""
        if not self.is_running:
            logger.warning("Execution engine not running")
            return

        self.is_running = False
        logger.info("Execution engine stopped")

    def run_cycle(self, market_data: Quote, portfolio: Portfolio) -> List[Signal]:
        """
        Ejecutar ciclo de trading.

        Args:
            market_data: Datos de mercado actuales
            portfolio: Estado actual del portfolio

        Returns:
            Lista de señales generadas y validadas
        """
        if not self.is_running:
            logger.warning("Execution engine not running, skipping cycle")
            return []

        signals = []
        self.cycle_count += 1

        # Obtener estrategia activa
        active_strategy = self.registry.get_active_strategy()
        if not active_strategy:
            logger.debug("No active strategy, skipping cycle")
            return signals

        try:
            # Generar señales
            strategy_signals = active_strategy.generate_signals(market_data)
            self.total_signals_generated += len(strategy_signals)

            logger.debug(
                f"Strategy '{active_strategy.name}' generated {len(strategy_signals)} signals"
            )

            # Validar señales con risk check
            for signal in strategy_signals:
                try:
                    if active_strategy.risk_check(signal, portfolio):
                        signals.append(signal)
                        self.logger.log_signal_generated(active_strategy.name, signal)
                        logger.debug(f"Signal validated: {signal.symbol} {signal.signal_type}")
                    else:
                        self.logger.log_signal_rejected(
                            active_strategy.name, signal, "Risk check failed"
                        )
                        logger.debug(f"Signal rejected by risk check: {signal.symbol}")

                except Exception as e:
                    self.logger.log_strategy_error(active_strategy.name, str(e), "risk_check")
                    logger.error(f"Risk check error for signal {signal.symbol}: {e}")

        except Exception as e:
            self.logger.log_strategy_error(active_strategy.name, str(e), "generate_signals")
            logger.error(f"Error generating signals for strategy '{active_strategy.name}': {e}")

        logger.debug(f"Cycle {self.cycle_count} completed: {len(signals)} signals validated")
        return signals

    def execute_signal(self, signal: Signal, execution_price: Optional[Decimal] = None) -> bool:
        """
        Ejecutar señal de trading.

        Args:
            signal: Señal a ejecutar
            execution_price: Precio de ejecución (opcional)

        Returns:
            True si la ejecución fue exitosa, False en caso contrario
        """
        try:
            # Aquí se integraría con el broker o paper trading
            # Por ahora, simulamos ejecución exitosa

            # Obtener estrategia activa para logging
            active_strategy = self.registry.get_active_strategy()
            strategy_name = active_strategy.name if active_strategy else "unknown"

            # Log de ejecución
            self.logger.log_signal_executed(strategy_name, signal, execution_price)
            self.total_signals_executed += 1

            logger.info(
                f"Signal executed: {signal.symbol} {signal.signal_type} at {execution_price or signal.price}"
            )
            return True

        except Exception as e:
            # Log de error de ejecución
            active_strategy = self.registry.get_active_strategy()
            strategy_name = active_strategy.name if active_strategy else "unknown"
            self.logger.log_execution_error(strategy_name, signal, str(e))

            logger.error(f"Execution error for signal {signal.symbol}: {e}")
            return False

    def execute_signals(
        self,
        signals: List[Signal],
        execution_prices: Optional[Dict[str, Decimal]] = None,
    ) -> Dict[str, bool]:
        """
        Ejecutar múltiples señales.

        Args:
            signals: Lista de señales a ejecutar
            execution_prices: Diccionario con precios de ejecución por símbolo

        Returns:
            Diccionario con resultados de ejecución por señal
        """
        if execution_prices is None:
            execution_prices = {}

        results = {}

        for signal in signals:
            execution_price = execution_prices.get(signal.symbol, signal.price)
            success = self.execute_signal(signal, execution_price)
            results[f"{signal.symbol}_{signal.direction}"] = success

        logger.info(f"Executed {len(signals)} signals: {sum(results.values())} successful")
        return results

    def get_execution_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de ejecución.

        Returns:
            Diccionario con estadísticas del motor
        """
        execution_rate = (
            self.total_signals_executed / self.total_signals_generated
            if self.total_signals_generated > 0
            else 0
        )

        return {
            "is_running": self.is_running,
            "cycle_count": self.cycle_count,
            "total_signals_generated": self.total_signals_generated,
            "total_signals_executed": self.total_signals_executed,
            "execution_rate": round(execution_rate, 4),
            "created_at": self.created_at.isoformat(),
            "active_strategy": self.registry.active_strategy,
        }

    def reset_stats(self) -> None:
        """Resetear estadísticas de ejecución."""
        self.cycle_count = 0
        self.total_signals_generated = 0
        self.total_signals_executed = 0
        logger.info("Execution engine stats reset")

    def validate_market_data(self, market_data: Quote) -> bool:
        """
        Validar datos de mercado.

        Args:
            market_data: Datos de mercado a validar

        Returns:
            True si los datos son válidos, False en caso contrario
        """
        try:
            # Validaciones básicas
            if not market_data.symbol:
                logger.error("Market data missing symbol")
                return False

            if not market_data.price or market_data.price <= 0:
                logger.error(f"Invalid price for {market_data.symbol}: {market_data.price}")
                return False

            if not market_data.volume or market_data.volume < 0:
                logger.error(f"Invalid volume for {market_data.symbol}: {market_data.volume}")
                return False

            return True

        except Exception as e:
            logger.error(f"Market data validation error: {e}")
            return False

    def validate_portfolio(self, portfolio: Portfolio) -> bool:
        """
        Validar estado del portfolio.

        Args:
            portfolio: Portfolio a validar

        Returns:
            True si el portfolio es válido, False en caso contrario
        """
        try:
            # Validaciones básicas
            if portfolio.cash < 0:
                logger.error(f"Invalid cash amount: {portfolio.cash}")
                return False

            # Validar posiciones
            for position in portfolio.positions:
                if position.quantity < 0:
                    logger.error(
                        f"Invalid position quantity for {position.symbol}: {position.quantity}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Portfolio validation error: {e}")
            return False

    def run_cycle_with_validation(self, market_data: Quote, portfolio: Portfolio) -> List[Signal]:
        """
        Ejecutar ciclo con validación completa.

        Args:
            market_data: Datos de mercado
            portfolio: Estado del portfolio

        Returns:
            Lista de señales generadas y validadas
        """
        # Validar datos de entrada
        if not self.validate_market_data(market_data):
            logger.error("Invalid market data, skipping cycle")
            return []

        if not self.validate_portfolio(portfolio):
            logger.error("Invalid portfolio, skipping cycle")
            return []

        # Ejecutar ciclo normal
        return self.run_cycle(market_data, portfolio)

    def __str__(self) -> str:
        """Representación string del motor."""
        status = "running" if self.is_running else "stopped"
        return f"ExecutionEngine(status={status}, cycles={self.cycle_count})"

    def __repr__(self) -> str:
        """Representación detallada del motor."""
        return (
            "ExecutionEngine("
            f"running={self.is_running}, "
            f"cycles={self.cycle_count}, "
            f"signals_generated={self.total_signals_generated}, "
            f"signals_executed={self.total_signals_executed})"
        )
