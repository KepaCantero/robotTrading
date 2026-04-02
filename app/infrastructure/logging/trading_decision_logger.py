"""
Trading Decision Logger - R15, R28

Logger append-only con correlation ID para todas las decisiones de trading.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.infrastructure.logging.append_only_log import AppendOnlyLog
from app.services.logging.log_entry import LogEntry

logger = logging.getLogger(__name__)


class TradingDecisionLogger:
    """
    Logger de decisiones de trading (R15, R28)

    Implementa:
    - R15: Logging append-only con correlation ID
    - R28: Registro para Hacienda (5 años)
    """

    def __init__(self, log_dir: str = ".ralph/logs/trading"):
        logger.debug(
            "Initializing TradingDecisionLogger",
            extra={"log_dir": log_dir},
        )
        self._log = AppendOnlyLog(log_dir)
        logger.info(
            "TradingDecisionLogger initialized",
            extra={"log_dir": log_dir},
        )

    def log_signal(self, signal: dict, metadata: dict | None = None) -> str:
        """
        Log signal con correlation ID

        Args:
            signal: Datos de la señal
            metadata: Metadatos adicionales

        Returns:
            Correlation ID para esta operacion
        """
        logger.debug(
            "Logging signal",
            extra={
                "symbol": signal.get("symbol"),
                "action": signal.get("action"),
                "quantity": signal.get("quantity"),
            },
        )
        entry = LogEntry.create(
            event_type="signal_received",
            data={
                "symbol": signal.get("symbol"),
                "action": signal.get("action"),
                "quantity": signal.get("quantity"),
                "price": signal.get("price"),
            },
            metadata=metadata or {},
        )

        self._log.append(entry)
        logger.info(
            "Signal logged successfully",
            extra={
                "correlation_id": entry.correlation_id,
                "symbol": signal.get("symbol"),
                "action": signal.get("action"),
                "event_type": "signal_received",
            },
        )
        return entry.correlation_id

    def log_execution(self, correlation_id: str, result: dict) -> None:
        """
        Log execution result

        Args:
            correlation_id: ID de correlación de la operación
            result: Resultado de la ejecución
        """
        logger.debug(
            "Logging execution result",
            extra={
                "correlation_id": correlation_id,
                "order_id": result.get("order_id"),
                "status": result.get("status"),
            },
        )
        entry = LogEntry(
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type="execution_result",
            data={
                "order_id": result.get("order_id"),
                "status": result.get("status"),
                "filled_price": result.get("filled_price"),
                "filled_quantity": result.get("filled_quantity"),
                "commission": result.get("commission"),
            },
            metadata={},
        )

        self._log.append(entry)
        logger.info(
            "Execution result logged",
            extra={
                "correlation_id": correlation_id,
                "order_id": result.get("order_id"),
                "status": result.get("status"),
                "event_type": "execution_result",
            },
        )

    def log_validation_result(
        self, correlation_id: str, validator: str, passed: bool, details: dict | None = None
    ) -> None:
        """
        Log validation result

        Args:
            correlation_id: ID de correlación
            validator: Nombre del validador (ej: "R1_Kelly", "R2_Drawdown")
            passed: Si pasó la validación
            details: Detalles adicionales
        """
        logger.debug(
            "Logging validation result",
            extra={
                "correlation_id": correlation_id,
                "validator": validator,
                "passed": passed,
            },
        )
        entry = LogEntry(
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type="validation_result",
            data={
                "validator": validator,
                "passed": passed,
                "details": details or {},
            },
            metadata={},
        )

        self._log.append(entry)
        logger.info(
            "Validation result logged",
            extra={
                "correlation_id": correlation_id,
                "validator": validator,
                "passed": passed,
                "event_type": "validation_result",
            },
        )

    def get_logs_by_correlation_id(self, correlation_id: str) -> list[dict]:
        """
        Obtener logs por correlation ID

        Args:
            correlation_id: ID de correlación

        Returns:
            Lista de entradas con ese ID
        """
        logger.debug(
            "Retrieving logs by correlation ID",
            extra={"correlation_id": correlation_id},
        )
        entries = self._log.get_entries_by_correlation_id(correlation_id)
        logger.info(
            "Logs retrieved by correlation ID",
            extra={
                "correlation_id": correlation_id,
                "entry_count": len(entries),
            },
        )
        return entries

    def export_for_hacienda(self, year: int) -> list[dict]:
        """
        R28: Exportar logs para Hacienda (5 años)

        Args:
            year: Año a exportar

        Returns:
            Lista de todas las operaciones del año
        """
        logger.info(
            "Exporting logs for Hacienda",
            extra={
                "year": year,
                "export_type": "hacienda",
            },
        )
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()

        entries = self._log.export_date_range(start_date, end_date)
        logger.debug(
            "Retrieved entries for date range",
            extra={
                "year": year,
                "entry_count": len(entries),
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )

        # Agrupar por correlation_id y formatear para Hacienda
        operations: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            corr_id = entry["correlation_id"]
            if corr_id not in operations:
                operations[corr_id] = []

            operations[corr_id].append(entry)

        # Formatear para Hacienda
        formatted = []
        for corr_id, entries_list in operations.items():
            # Extraer datos relevantes
            signal_entry = next(
                (e for e in entries_list if e["event_type"] == "signal_received"), None
            )
            execution_entry = next(
                (e for e in entries_list if e["event_type"] == "execution_result"), None
            )

            if signal_entry and execution_entry:
                formatted.append(
                    {
                        "correlation_id": corr_id,
                        "timestamp": signal_entry["timestamp"],
                        "symbol": signal_entry["data"]["symbol"],
                        "action": signal_entry["data"]["action"],
                        "quantity": signal_entry["data"]["quantity"],
                        "entry_price": signal_entry["data"].get("price"),
                        "exit_price": execution_entry["data"].get("filled_price"),
                        "profit_loss": self._calculate_pnl(signal_entry, execution_entry),
                    }
                )

        logger.info(
            "Hacienda export completed",
            extra={
                "year": year,
                "total_operations": len(formatted),
                "total_entries": len(entries),
            },
        )
        return formatted

    def _calculate_pnl(self, signal_entry: dict, execution_entry: dict) -> float:
        """
        Calcular P&L desde entradas de log

        Args:
            signal_entry: Entrada de señal
            execution_entry: Entrada de ejecución

        Returns:
            Profit/Loss calculado

        @todo: Implementar cálculo real de P&L con comisiones y ajustes
        """
        # @todo: Incluir comisiones y ajustes
        entry_price = signal_entry["data"].get("price", 0)
        exit_price = execution_entry["data"].get("filled_price", 0)
        quantity = signal_entry["data"].get("quantity", 0)

        if signal_entry["data"].get("action") == "BUY":
            return (exit_price - entry_price) * quantity
        else:  # SELL
            return (entry_price - exit_price) * quantity
