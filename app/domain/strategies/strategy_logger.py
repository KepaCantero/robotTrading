"""
StrategyLogger - Logger centralizado para estrategias.

Proporciona logging estructurado y métricas para todas las estrategias,
incluyendo señales generadas, ejecutadas, rechazadas y errores.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.domain.models.signal import Signal

logger = logging.getLogger(__name__)


class StrategyLogger:
    """Logger centralizado para estrategias."""

    def __init__(self, log_path: str = "logs/strategy_logs.json"):
        """
        Inicializar logger de estrategias.

        Args:
            log_path: Ruta al archivo de logs
        """
        self.log_path = Path(log_path)
        self.logs: List[Dict[str, Any]] = []
        self.created_at = datetime.utcnow()

        # Crear directorio de logs si no existe
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Cargar logs existentes si el archivo existe
        self._load_existing_logs()

    def _load_existing_logs(self) -> None:
        """Cargar logs existentes desde archivo."""
        if self.log_path.exists():
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    self.logs = json.load(f)
                logger.info(f"Loaded {len(self.logs)} existing logs from {self.log_path}")
            except (FileNotFoundError, PermissionError, IOError, OSError) as e:
                logger.warning("Could not load existing logs: %s", str(e), exc_info=True)
                self.logs = []
        else:
            # Archivo no existe, inicializar lista vacía sin warning
            self.logs = []

    def _save_logs(self) -> None:
        """Guardar logs en archivo."""
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(self.logs, f, indent=2, default=str)
        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            logger.error("Failed to save logs: %s", str(e), exc_info=True)

    def _create_log_entry(
        self, event: str, strategy_name: str, level: str = "INFO", **kwargs
    ) -> Dict[str, Any]:
        """
        Crear entrada de log.

        Args:
            event: Tipo de evento
            strategy_name: Nombre de la estrategia
            level: Nivel de log
            **kwargs: Datos adicionales

        Returns:
            Entrada de log creada
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "strategy": strategy_name,
            "level": level,
            **kwargs,
        }

    def log_signal_generated(self, strategy_name: str, signal: Signal) -> None:
        """
        Log de señal generada.

        Args:
            strategy_name: Nombre de la estrategia
            signal: Señal generada
        """
        log_entry = self._create_log_entry(
            "signal_generated",
            strategy_name,
            "INFO",
            signal_data=self._serialize_signal(signal),
        )
        self.logs.append(log_entry)
        self._save_logs()
        logger.debug(f"Strategy '{strategy_name}' generated signal: {signal.symbol}")

    def log_signal_rejected(self, strategy_name: str, signal: Signal, reason: str) -> None:
        """
        Log de señal rechazada.

        Args:
            strategy_name: Nombre de la estrategia
            signal: Señal rechazada
            reason: Razón del rechazo
        """
        log_entry = self._create_log_entry(
            "signal_rejected",
            strategy_name,
            "WARNING",
            signal_data=self._serialize_signal(signal),
            reason=reason,
        )
        self.logs.append(log_entry)
        self._save_logs()
        logger.warning(f"Strategy '{strategy_name}' rejected signal: {reason}")

    def log_signal_executed(
        self,
        strategy_name: str,
        signal: Signal,
        execution_price: Optional[Decimal] = None,
    ) -> None:
        """
        Log de señal ejecutada.

        Args:
            strategy_name: Nombre de la estrategia
            signal: Señal ejecutada
            execution_price: Precio de ejecución (opcional)
        """
        log_entry = self._create_log_entry(
            "signal_executed",
            strategy_name,
            "INFO",
            signal_data=self._serialize_signal(signal),
            execution_price=str(execution_price) if execution_price else None,
        )
        self.logs.append(log_entry)
        self._save_logs()
        logger.info(f"Strategy '{strategy_name}' executed signal: {signal.symbol}")

    def log_strategy_error(
        self, strategy_name: str, error: str, error_type: Optional[str] = None
    ) -> None:
        """
        Log de error de estrategia.

        Args:
            strategy_name: Nombre de la estrategia
            error: Mensaje de error
            error_type: Tipo de error (opcional)
        """
        log_entry = self._create_log_entry(
            "strategy_error", strategy_name, "ERROR", error=error, error_type=error_type
        )
        self.logs.append(log_entry)
        self._save_logs()
        logger.error(f"Strategy '{strategy_name}' error: {error}")

    def log_execution_error(self, strategy_name: str, signal: Signal, error: str) -> None:
        """
        Log de error de ejecución.

        Args:
            strategy_name: Nombre de la estrategia
            signal: Señal que falló
            error: Mensaje de error
        """
        log_entry = self._create_log_entry(
            "execution_error",
            strategy_name,
            "ERROR",
            signal_data=self._serialize_signal(signal),
            error=error,
        )
        self.logs.append(log_entry)
        self._save_logs()
        logger.error(f"Strategy '{strategy_name}' execution error: {error}")

    def log_strategy_loaded(self, strategy_name: str, config: Dict[str, Any]) -> None:
        """
        Log de estrategia cargada.

        Args:
            strategy_name: Nombre de la estrategia
            config: Configuración de la estrategia
        """
        log_entry = self._create_log_entry(
            "strategy_loaded", strategy_name, "INFO", config_keys=list(config.keys())
        )
        self.logs.append(log_entry)
        self._save_logs()
        logger.info(f"Strategy '{strategy_name}' loaded")

    def log_strategy_unloaded(self, strategy_name: str) -> None:
        """
        Log de estrategia descargada.

        Args:
            strategy_name: Nombre de la estrategia
        """
        log_entry = self._create_log_entry("strategy_unloaded", strategy_name, "INFO")
        self.logs.append(log_entry)
        self._save_logs()
        logger.info(f"Strategy '{strategy_name}' unloaded")

    def log_strategy_activated(self, strategy_name: str) -> None:
        """
        Log de estrategia activada.

        Args:
            strategy_name: Nombre de la estrategia
        """
        log_entry = self._create_log_entry("strategy_activated", strategy_name, "INFO")
        self.logs.append(log_entry)
        self._save_logs()
        logger.info(f"Strategy '{strategy_name}' activated")

    def log_strategy_deactivated(self, strategy_name: str) -> None:
        """
        Log de estrategia desactivada.

        Args:
            strategy_name: Nombre de la estrategia
        """
        log_entry = self._create_log_entry("strategy_deactivated", strategy_name, "INFO")
        self.logs.append(log_entry)
        self._save_logs()
        logger.info(f"Strategy '{strategy_name}' deactivated")

    def _serialize_signal(self, signal: Signal) -> Dict[str, Any]:
        """
        Serializar señal para logging.

        Args:
            signal: Señal a serializar

        Returns:
            Diccionario serializado
        """
        return {
            "symbol": signal.symbol,
            "signal_type": signal.signal_type.value,
            "strength": signal.strength.value,
            "confidence": signal.confidence,
            "liquidity_score": signal.liquidity_score,
            "priority_score": signal.priority_score,
            "source": signal.source.value,
            "price": str(signal.price),
            "volume": str(signal.volume),
            "timestamp": signal.timestamp.isoformat() if signal.timestamp else None,
            "metadata": signal.metadata,
        }

    def get_strategy_metrics(self, strategy_name: str) -> Dict[str, Any]:
        """
        Obtener métricas de estrategia.

        Args:
            strategy_name: Nombre de la estrategia

        Returns:
            Diccionario con métricas de la estrategia
        """
        strategy_logs = [log for log in self.logs if log.get("strategy") == strategy_name]

        signals_generated = len(
            [log for log in strategy_logs if log["event"] == "signal_generated"]
        )
        signals_executed = len([log for log in strategy_logs if log["event"] == "signal_executed"])
        signals_rejected = len([log for log in strategy_logs if log["event"] == "signal_rejected"])
        errors = len([log for log in strategy_logs if log["event"] == "strategy_error"])
        execution_errors = len([log for log in strategy_logs if log["event"] == "execution_error"])

        # Calcular métricas adicionales
        total_signals = signals_generated
        execution_rate = signals_executed / total_signals if total_signals > 0 else 0
        rejection_rate = signals_rejected / total_signals if total_signals > 0 else 0
        error_rate = (errors + execution_errors) / total_signals if total_signals > 0 else 0

        return {
            "strategy": strategy_name,
            "signals_generated": signals_generated,
            "signals_executed": signals_executed,
            "signals_rejected": signals_rejected,
            "execution_rate": round(execution_rate, 4),
            "rejection_rate": round(rejection_rate, 4),
            "error_count": errors + execution_errors,
            "error_rate": round(error_rate, 4),
            "total_logs": len(strategy_logs),
            "first_log": strategy_logs[0]["timestamp"] if strategy_logs else None,
            "last_log": strategy_logs[-1]["timestamp"] if strategy_logs else None,
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Obtener métricas de todas las estrategias.

        Returns:
            Diccionario con métricas de todas las estrategias
        """
        strategies = set(log.get("strategy") for log in self.logs if log.get("strategy"))

        metrics = {}
        for strategy_name in strategies:
            metrics[strategy_name] = self.get_strategy_metrics(strategy_name)

        return {
            "total_strategies": len(strategies),
            "total_logs": len(self.logs),
            "logger_created_at": self.created_at.isoformat(),
            "strategies": metrics,
        }

    def clear_logs(self) -> None:
        """Limpiar todos los logs."""
        self.logs = []
        self._save_logs()
        logger.info("Cleared all strategy logs")

    def export_logs(self, export_path: str) -> None:
        """
        Exportar logs a archivo específico.

        Args:
            export_path: Ruta del archivo de exportación
        """
        export_file = Path(export_path)
        export_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump(self.logs, f, indent=2, default=str)
            logger.info(f"Exported {len(self.logs)} logs to {export_path}")
        except (FileNotFoundError, PermissionError, IOError, OSError) as e:
            logger.error("Failed to export logs: %s", str(e), exc_info=True)
            raise

    def __str__(self) -> str:
        """Representación string del logger."""
        return f"StrategyLogger(logs={len(self.logs)}, path={self.log_path})"

    def __repr__(self) -> str:
        """Representación detallada del logger."""
        return (
            "StrategyLogger("
            f"logs={len(self.logs)}, "
            f"path={self.log_path}, "
            f"created={self.created_at})"
        )
