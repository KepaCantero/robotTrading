"""
Append-Only Log Storage

Almacenamiento append-only para logs de trading.
"""

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.services.logging.log_entry import LogEntry


# Define LogEntry type for runtime as Dict for flexibility
LogEntryType = Union[dict[str, Any], "LogEntry"]


class AppendOnlyLog:
    """
    Log append-only para decisiones de trading

    Características:
    - Solo append (no delete, no update)
    - Persistencia en disco
    - Rotación por fecha
    """

    def __init__(self, log_dir: str = ".ralph/logs/trading"):
        """
        Inicializar log append-only

        Args:
            log_dir: Directorio para almacenar logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Archivo actual (por fecha)
        self._current_date = datetime.utcnow().date()
        self._current_file = self._get_log_file(self._current_date)
        logger.info(
            "AppendOnlyLog initialized",
            extra={
                "component": "AppendOnlyLog",
                "log_dir": str(self.log_dir),
                "current_file": str(self._current_file),
            },
        )

    def _get_log_file(self, date: date) -> Path:
        """Obtener archivo de log para fecha específica"""
        return self.log_dir / f"trading_{date.isoformat()}.log"

    def append(self, entry: LogEntryType) -> None:
        """
        Añadir entrada al log (append-only)

        Args:
            entry: Entrada a añadir
        """
        # Rotar si cambió el día
        current_date = datetime.utcnow().date()
        if current_date != self._current_date:
            old_date = self._current_date
            self._current_date = current_date
            self._current_file = self._get_log_file(current_date)
            logger.info(
                "Log file rotated",
                extra={
                    "component": "AppendOnlyLog",
                    "old_date": old_date.isoformat(),
                    "new_date": current_date.isoformat(),
                    "new_file": str(self._current_file),
                },
            )

        # Añadir entrada al archivo (append-only)
        with open(self._current_file, "a") as f:
            if hasattr(entry, "to_dict"):
                f.write(json.dumps(entry.to_dict()) + "\n")
            else:
                f.write(json.dumps(entry) + "\n")
        logger.debug(
            "Log entry appended",
            extra={
                "component": "AppendOnlyLog",
                "file": str(self._current_file),
                "entry_type": type(entry).__name__,
            },
        )

    def get_entries_by_correlation_id(self, correlation_id: str) -> list[dict]:
        """
        Obtener todas las entradas con un correlation_id

        Args:
            correlation_id: Correlation ID a buscar

        Returns:
            Lista de entradas con ese correlation_id
        """
        entries = []
        logger.debug(
            "Searching entries by correlation_id",
            extra={
                "component": "AppendOnlyLog",
                "correlation_id": correlation_id,
                "search_days": 7,
            },
        )

        # Buscar en archivos de logs (últimos 7 días por defecto)
        for days_ago in range(7):
            date_obj = datetime.utcnow().date() - timedelta(days=days_ago)
            log_file = self._get_log_file(date_obj)

            if not log_file.exists():
                continue

            with open(log_file) as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if entry.get("correlation_id") == correlation_id:
                        entries.append(entry)

        logger.info(
            "Entries retrieved by correlation_id",
            extra={
                "component": "AppendOnlyLog",
                "correlation_id": correlation_id,
                "entries_found": len(entries),
            },
        )
        return entries

    def export_date_range(self, start_date: date, end_date: date) -> list[dict]:
        """
        Exportar entradas en rango de fechas

        Args:
            start_date: Fecha inicial
            end_date: Fecha final

        Returns:
            Lista de todas las entradas en el rango
        """
        entries = []
        current = start_date
        logger.debug(
            "Exporting date range",
            extra={
                "component": "AppendOnlyLog",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        while current <= end_date:
            log_file = self._get_log_file(current)

            if log_file.exists():
                with open(log_file) as f:
                    for line in f:
                        entries.append(json.loads(line.strip()))

            current += timedelta(days=1)

        logger.info(
            "Date range exported",
            extra={
                "component": "AppendOnlyLog",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_entries": len(entries),
            },
        )
        return entries
