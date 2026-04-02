"""
Log Entry - Inmutable append-only log entry

Cada entrada es inmutable y se anade al log append-only.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LogEntry:
    """
    Entrada de log inmutable (append-only)

    Atributos:
        correlation_id: ID unico que relaciona todas las entradas de una operacion
        timestamp: Timestamp ISO 8601
        event_type: Tipo de evento (signal, validation, execution, result)
        data: Datos del evento (JSON serializable)
        metadata: Metadatos adicionales
    """

    correlation_id: str
    timestamp: str
    event_type: str
    data: dict[str, Any]
    metadata: dict[str, Any]

    @classmethod
    def create(cls, event_type: str, data: dict, metadata: dict | None = None) -> LogEntry:
        """
        Crear nueva entrada de log con correlation ID unico

        Args:
            event_type: Tipo de evento
            data: Datos del evento
            metadata: Metadatos opcionales

        Returns:
            LogEntry con correlation_id generado
        """
        correlation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        logger.debug(
            "Creating new log entry",
            extra={
                "component": "log_entry",
                "operation": "create",
                "correlation_id": correlation_id,
                "event_type": event_type,
                "timestamp": timestamp,
            },
        )

        entry = cls(
            correlation_id=correlation_id,
            timestamp=timestamp,
            event_type=event_type,
            data=data,
            metadata=metadata or {},
        )

        logger.info(
            "Log entry created",
            extra={
                "component": "log_entry",
                "operation": "create_complete",
                "correlation_id": correlation_id,
                "event_type": event_type,
            },
        )

        return entry

    def to_dict(self) -> dict:
        """Convertir a diccionario para serializacion JSON"""
        result = {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "data": self.data,
            "metadata": self.metadata,
        }

        logger.debug(
            "Converting log entry to dict",
            extra={
                "component": "log_entry",
                "operation": "to_dict",
                "correlation_id": self.correlation_id,
                "event_type": self.event_type,
            },
        )

        return result

    def with_correlation_id(self, correlation_id: str) -> LogEntry:
        """
        Crear nueva entrada con correlation_id existente

        Usado para anadir entradas relacionadas a una operacion existente.

        Args:
            correlation_id: Correlation ID existente

        Returns:
            Nuevo LogEntry con mismo correlation_id
        """
        logger.debug(
            "Creating log entry with existing correlation_id",
            extra={
                "component": "log_entry",
                "operation": "with_correlation_id",
                "correlation_id": correlation_id,
                "event_type": self.event_type,
            },
        )

        entry = LogEntry(
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type=self.event_type,
            data=self.data,
            metadata=self.metadata,
        )

        logger.info(
            "Log entry with correlation_id created",
            extra={
                "component": "log_entry",
                "operation": "with_correlation_id_complete",
                "correlation_id": correlation_id,
                "event_type": self.event_type,
            },
        )

        return entry
