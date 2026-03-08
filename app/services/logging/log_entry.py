"""
Log Entry - Inmutable append-only log entry

Cada entrada es inmutable y se añade al log append-only.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LogEntry:
    """
    Entrada de log inmutable (append-only)

    Atributos:
        correlation_id: ID único que relaciona todas las entradas de una operación
        timestamp: Timestamp ISO 8601
        event_type: Tipo de evento (signal, validation, execution, result)
        data: Datos del evento (JSON serializable)
        metadata: Metadatos adicionales
    """

    correlation_id: str
    timestamp: str
    event_type: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]

    @classmethod
    def create(cls, event_type: str, data: dict, metadata: Optional[dict] = None) -> "LogEntry":
        """
        Crear nueva entrada de log con correlation ID único

        Args:
            event_type: Tipo de evento
            data: Datos del evento
            metadata: Metadatos opcionales

        Returns:
            LogEntry con correlation_id generado
        """
        correlation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"

        return cls(
            correlation_id=correlation_id,
            timestamp=timestamp,
            event_type=event_type,
            data=data,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización JSON"""
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "data": self.data,
            "metadata": self.metadata,
        }

    def with_correlation_id(self, correlation_id: str) -> "LogEntry":
        """
        Crear nueva entrada con correlation_id existente

        Usado para añadir entradas relacionadas a una operación existente.

        Args:
            correlation_id: Correlation ID existente

        Returns:
            Nuevo LogEntry con mismo correlation_id
        """
        return LogEntry(
            correlation_id=correlation_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type=self.event_type,
            data=self.data,
            metadata=self.metadata,
        )
