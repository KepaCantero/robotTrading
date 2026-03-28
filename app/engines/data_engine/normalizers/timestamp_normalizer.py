"""
TimestampNormalizer - Normalización de timestamps.

Convierte timestamps de diferentes formatos y timezones a UTC estándar.
"""

import contextlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

import pytz

logger = logging.getLogger(__name__)


class TimestampNormalizer:
    """
    Normalizador de timestamps.

    Convierte timestamps a UTC y maneja diferentes formatos y timezones.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar normalizador.

        Args:
            config: Configuración
        """
        config = config or {}
        self.default_timezone = config.get('default_timezone', 'UTC')
        self.output_timezone = pytz.UTC  # Siempre output UTC
        self.assume_local_if_naive = config.get('assume_local_if_naive', False)

    def normalize(self, timestamp: Union[datetime, int, float, str], source_timezone: Optional[str] = None) -> datetime:
        """
        Normalizar timestamp a UTC.

        Args:
            timestamp: Timestamp en cualquier formato (datetime, int, str, etc.)
            source_timezone: Timezone del timestamp si es naive (opcional)

        Returns:
            datetime en UTC (timezone-aware)
        """
        try:
            # Convertir a datetime si no lo es
            if isinstance(timestamp, datetime):
                dt = timestamp
            elif isinstance(timestamp, (int, float)):
                # Timestamp Unix (segundos o milisegundos)
                if timestamp > 1e10:  # Milisegundos
                    dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                else:  # Segundos
                    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif isinstance(timestamp, str):
                # String ISO format o otros formatos comunes
                dt = self._parse_string_timestamp(timestamp)
            else:
                raise ValueError(f"Tipo de timestamp no soportado: {type(timestamp)}")

            # Manejar timezone
            if dt.tzinfo is None:
                # Naive datetime - asignar timezone
                if source_timezone:
                    tz = pytz.timezone(source_timezone)
                    dt = tz.localize(dt)
                elif self.assume_local_if_naive:
                    # Asumir timezone local (no recomendado para producción)
                    dt = dt.replace(tzinfo=pytz.UTC)
                else:
                    # Asumir UTC por defecto
                    dt = dt.replace(tzinfo=pytz.UTC)

            # Convertir a UTC
            if dt.tzinfo != pytz.UTC:
                dt = dt.astimezone(pytz.UTC)

            return dt

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error normalizando timestamp {timestamp}: {e}")
            # Fallback: retornar UTC now
            return datetime.now(pytz.UTC)

    def _parse_string_timestamp(self, timestamp_str: str) -> datetime:
        """
        Parsear string timestamp.

        Soporta múltiples formatos comunes.
        """
        # Formato ISO
        with contextlib.suppress(ValueError, TypeError, KeyError, AttributeError):
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        # Formato común: YYYY-MM-DD HH:MM:SS
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except (ValueError, TypeError, KeyError, AttributeError):
                continue

        raise ValueError(f"No se pudo parsear timestamp string: {timestamp_str}")

    def normalize_batch(self, timestamps: list, source_timezone: Optional[str] = None) -> list:
        """
        Normalizar múltiples timestamps.

        Args:
            timestamps: Lista de timestamps
            source_timezone: Timezone del source (opcional)

        Returns:
            Lista de datetimes normalizados en UTC
        """
        return [self.normalize(ts, source_timezone) for ts in timestamps]
