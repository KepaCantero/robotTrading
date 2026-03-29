"""
GapInterpolator - Interpolación de gaps en datos de mercado.

Métodos soportados:
- Forward fill
- Backward fill
- Linear interpolation
- Spline interpolation
"""

import logging
from decimal import Decimal
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class GapInterpolator:
    """
    Interpolador de gaps en datos de mercado.

    Rellena valores faltantes en series temporales.
    """

    def __init__(self, config: Optional[dict[str, Any]] = None):
        """
        Inicializar interpolador.

        Args:
            config: Configuración
        """
        config = config or {}
        self.method = config.get(
            "method", "forward_fill"
        )  # forward_fill, backward_fill, linear, spline
        self.max_gap_days = config.get("max_gap_days", 5)  # Máximo de días para interpolar
        self.interpolate_volume = config.get(
            "interpolate_volume", False
        )  # Interpolar volumen (generalmente 0)

    def interpolate(
        self,
        data: list[dict[str, Any]],
        timestamp_field: str = "timestamp",
        value_fields: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        """
        Interpolar gaps en datos temporales.

        Args:
            data: Lista de dicts con datos temporales
            timestamp_field: Campo con timestamp
            value_fields: Campos a interpolar (default: ['open', 'high', 'low', 'close'])

        Returns:
            Lista de datos con gaps interpolados
        """
        if not data:
            return data

        if value_fields is None:
            value_fields = ["open", "high", "low", "close"]

        # Convertir a DataFrame para facilitar interpolación
        df = pd.DataFrame(data)

        # Asegurar que timestamp es datetime
        if timestamp_field in df.columns:
            df[timestamp_field] = pd.to_datetime(df[timestamp_field])
            df = df.sort_values(timestamp_field)

        # Interpolar cada campo
        for field in value_fields:
            if field in df.columns:
                df[field] = self._interpolate_field(df, field, timestamp_field)

        # Interpolar volumen si está configurado
        if "volume" in df.columns and self.interpolate_volume:
            df["volume"] = self._interpolate_field(df, "volume", timestamp_field)
        elif "volume" in df.columns:
            # Volumen generalmente se rellena con 0
            df["volume"] = df["volume"].fillna(0)

        # Convertir de vuelta a lista de dicts
        result = df.to_dict("records")

        # Convertir Decimal de vuelta si es necesario
        for item in result:
            for field in [*value_fields, "volume"]:
                if field in item and isinstance(item[field], (int, float)):
                    if pd.notna(item[field]):
                        item[field] = Decimal(str(item[field]))
                    else:
                        item[field] = Decimal("0")

        return result

    def _interpolate_field(self, df: pd.DataFrame, field: str, timestamp_field: str) -> pd.Series:
        """
        Interpolar un campo específico.

        Args:
            df: DataFrame con datos
            field: Campo a interpolar
            timestamp_field: Campo con timestamp

        Returns:
            Series interpolada
        """
        if field not in df.columns:
            return df[field]

        method_map = {
            "forward_fill": "ffill",
            "backward_fill": "bfill",
            "linear": "linear",
            "spline": "polynomial",
        }

        pandas_method = method_map.get(self.method, "ffill")

        if self.method == "linear":
            # Linear interpolation
            return df[field].interpolate(method="linear", limit_direction="both")
        elif self.method == "spline":
            # Spline interpolation (requiere scipy)
            try:
                return df[field].interpolate(method="polynomial", order=3, limit_direction="both")
            except (RuntimeError, ValueError, TypeError, KeyError):
                logger.warning("Spline interpolation falló, usando linear")
                return df[field].interpolate(method="linear", limit_direction="both")
        else:
            # Forward fill o backward fill
            return df[field].fillna(method=pandas_method, limit=self.max_gap_days)

    def detect_gaps(
        self,
        data: list[dict[str, Any]],
        timestamp_field: str = "timestamp",
        expected_frequency: str = "1D",  # pandas frequency string
    ) -> dict[str, Any]:
        """
        Detectar gaps en datos temporales.

        Args:
            data: Lista de dicts con datos
            timestamp_field: Campo con timestamp
            expected_frequency: Frecuencia esperada (ej: '1D', '1H', '5T')

        Returns:
            Dict con información de gaps:
                - gaps: List[Dict] - Gaps encontrados
                - total_gaps: int
                - max_gap_days: float
        """
        if not data:
            return {"gaps": [], "total_gaps": 0, "max_gap_days": 0}

        df = pd.DataFrame(data)
        df[timestamp_field] = pd.to_datetime(df[timestamp_field])
        df = df.sort_values(timestamp_field)

        # Crear índice temporal esperado
        start = df[timestamp_field].min()
        end = df[timestamp_field].max()
        expected_index = pd.date_range(start, end, freq=expected_frequency)

        # Encontrar gaps
        gaps = []
        current_ts = None

        for ts in expected_index:
            if ts not in df[timestamp_field].values:
                if current_ts is None:
                    # Inicio de gap
                    current_ts = ts
            else:
                if current_ts is not None:
                    # Fin de gap
                    gap_days = (ts - current_ts).days
                    gaps.append({"start": current_ts, "end": ts, "duration_days": gap_days})
                    current_ts = None

        # Gap final si existe
        if current_ts is not None:
            gaps.append(
                {
                    "start": current_ts,
                    "end": expected_index[-1],
                    "duration_days": (expected_index[-1] - current_ts).days,
                }
            )

        max_gap_days = max([g["duration_days"] for g in gaps], default=0)

        return {"gaps": gaps, "total_gaps": len(gaps), "max_gap_days": float(max_gap_days)}
