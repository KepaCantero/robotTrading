"""
Append-Only Log Storage

Almacenamiento append-only para logs de trading.
"""
from datetime import date, datetime, timedelta
from pathlib import Path
import json
from typing import List


from app.infrastructure.logging.log_entry import LogEntry


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

    def _get_log_file(self, date: date) -> Path:
        """Obtener archivo de log para fecha específica"""
        return self.log_dir / f"trading_{date.isoformat()}.log"

    def append(self, entry: LogEntry) -> None:
        """
        Añadir entrada al log (append-only)

        Args:
            entry: Entrada a añadir
        """
        # Rotar si cambió el día
        current_date = datetime.utcnow().date()
        if current_date != self._current_date:
            self._current_date = current_date
            self._current_file = self._get_log_file(current_date)

        # Añadir entrada al archivo (append-only)
        with open(self._current_file, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def get_entries_by_correlation_id(self, correlation_id: str) -> List[dict]:
        """
        Obtener todas las entradas con un correlation_id

        Args:
            correlation_id: Correlation ID a buscar

        Returns:
            Lista de entradas con ese correlation_id
        """
        entries = []

        # Buscar en archivos de logs (últimos 7 días por defecto)
        for days_ago in range(7):
            date_obj = datetime.utcnow().date() - timedelta(days=days_ago)
            log_file = self._get_log_file(date_obj)

            if not log_file.exists():
                continue

            with open(log_file, "r") as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if entry.get("correlation_id") == correlation_id:
                        entries.append(entry)

        return entries

    def export_date_range(self, start_date: date, end_date: date) -> List[dict]:
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

        while current <= end_date:
            log_file = self._get_log_file(current)

            if log_file.exists():
                with open(log_file, "r") as f:
                    for line in f:
                        entries.append(json.loads(line.strip()))

            current += timedelta(days=1)

        return entries
