"""
QualityValidator - Validación de calidad de datos.

Incluye:
- Checksums
- Validación de rangos
- Validación de consistencia OHLC
- Data quality metrics
"""

import hashlib
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QualityValidator:
    """
    Validador de calidad de datos.

    Verifica integridad, consistencia y calidad de datos de mercado.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar validador.

        Args:
            config: Configuración
        """
        config = config or {}
        self.min_price = Decimal(str(config.get('min_price', 0.01)))
        self.max_price = Decimal(str(config.get('max_price', 1000000)))
        self.min_volume = Decimal(str(config.get('min_volume', 0)))
        self.max_volume = Decimal(str(config.get('max_volume', 10000000000)))  # 10B
        self.validate_ohlc_consistency = config.get('validate_ohlc_consistency', True)

    def validate(self, data: Dict[str, Any], data_type: str = 'ohlcv') -> Dict[str, Any]:
        """
        Validar datos individuales.

        Args:
            data: Dict con datos a validar
            data_type: Tipo de datos (ohlcv, quote, etc.)

        Returns:
            Dict con resultados de validación:
                - is_valid: bool
                - errors: List[str]
                - warnings: List[str]
        """
        errors = []
        warnings = []

        if data_type == 'ohlcv':
            # Validar OHLCV
            errors.extend(self._validate_ohlc(data))
            errors.extend(self._validate_price_ranges(data))
            errors.extend(self._validate_volume(data))

            if self.validate_ohlc_consistency:
                errors.extend(self._validate_ohlc_consistency(data))

        elif data_type == 'quote':
            # Validar quote
            errors.extend(self._validate_quote(data))

        return {'is_valid': len(errors) == 0, 'errors': errors, 'warnings': warnings}

    def _validate_ohlc(self, data: Dict[str, Any]) -> List[str]:
        """Validar campos OHLC."""
        errors = []

        required_fields = ['open', 'high', 'low', 'close']
        for field in required_fields:
            if field not in data:
                errors.append(f"Campo requerido faltante: {field}")
            else:
                value = data[field]
                if value is None:
                    errors.append(f"Campo {field} es None")
                elif not isinstance(value, (Decimal, int, float)):
                    errors.append(f"Campo {field} debe ser numérico")

        return errors

    def _validate_price_ranges(self, data: Dict[str, Any]) -> List[str]:
        """Validar que precios están en rangos válidos."""
        errors = []

        price_fields = ['open', 'high', 'low', 'close', 'bid', 'ask', 'last']
        for field in price_fields:
            if field in data and data[field] is not None:
                value = Decimal(str(data[field]))
                if value < self.min_price:
                    errors.append(
                        f"{field} ({value}) está por debajo del mínimo ({self.min_price})"
                    )
                if value > self.max_price:
                    errors.append(f"{field} ({value}) excede el máximo ({self.max_price})")

        return errors

    def _validate_volume(self, data: Dict[str, Any]) -> List[str]:
        """Validar volumen."""
        errors = []

        if 'volume' in data and data['volume'] is not None:
            volume = Decimal(str(data['volume']))
            if volume < self.min_volume:
                errors.append(f"Volume ({volume}) está por debajo del mínimo ({self.min_volume})")
            if volume > self.max_volume:
                errors.append(f"Volume ({volume}) excede el máximo ({self.max_volume})")

        return errors

    def _validate_ohlc_consistency(self, data: Dict[str, Any]) -> List[str]:
        """Validar consistencia OHLC."""
        errors = []

        try:
            high = Decimal(str(data.get('high', 0)))
            low = Decimal(str(data.get('low', 0)))
            open_price = Decimal(str(data.get('open', 0)))
            close_price = Decimal(str(data.get('close', 0)))

            if high < low:
                errors.append(f"High ({high}) < Low ({low})")

            if not (low <= open_price <= high):
                errors.append(f"Open ({open_price}) no está entre Low ({low}) y High ({high})")

            if not (low <= close_price <= high):
                errors.append(f"Close ({close_price}) no está entre Low ({low}) y High ({high})")

        except Exception as e:
            errors.append(f"Error validando consistencia OHLC: {e}")

        return errors

    def _validate_quote(self, data: Dict[str, Any]) -> List[str]:
        """Validar quote."""
        errors = []

        # Validar bid/ask
        if 'bid' in data and 'ask' in data:
            bid = Decimal(str(data['bid']))
            ask = Decimal(str(data['ask']))

            if bid > ask:
                errors.append(f"Bid ({bid}) > Ask ({ask})")

        return errors

    def calculate_checksum(self, data: List[Dict[str, Any]]) -> str:
        """
        Calcular checksum de datos.

        Args:
            data: Lista de datos

        Returns:
            Checksum MD5
        """
        try:
            # Serializar datos a string
            data_str = str(sorted([str(d) for d in data]))
            return hashlib.md5(data_str.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculando checksum: {e}")
            return ""

    def validate_batch(
        self, data_list: List[Dict[str, Any]], data_type: str = 'ohlcv'
    ) -> Dict[str, Any]:
        """
        Validar múltiples datos.

        Args:
            data_list: Lista de datos a validar
            data_type: Tipo de datos

        Returns:
            Dict con resultados agregados:
                - total: int
                - valid: int
                - invalid: int
                - errors_by_record: Dict[int, List[str]]
                - checksum: str
        """
        total = len(data_list)
        valid_count = 0
        invalid_count = 0
        errors_by_record = {}

        for i, data in enumerate(data_list):
            result = self.validate(data, data_type)
            if result['is_valid']:
                valid_count += 1
            else:
                invalid_count += 1
                errors_by_record[i] = result['errors']

        checksum = self.calculate_checksum(data_list)

        return {
            'total': total,
            'valid': valid_count,
            'invalid': invalid_count,
            'error_rate': float(invalid_count / total) if total > 0 else 0.0,
            'errors_by_record': errors_by_record,
            'checksum': checksum,
        }

    def get_quality_metrics(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcular métricas de calidad.

        Args:
            data_list: Lista de datos

        Returns:
            Dict con métricas:
                - completeness: float (0-1)
                - consistency: float (0-1)
                - accuracy: float (0-1)
                - timeliness: float (0-1)
        """
        if not data_list:
            return {'completeness': 0.0, 'consistency': 0.0, 'accuracy': 0.0, 'timeliness': 0.0}

        total = len(data_list)

        # Completeness: % de campos no-null
        required_fields = ['open', 'high', 'low', 'close', 'volume']
        completeness_scores = []
        for data in data_list:
            complete_fields = sum(1 for field in required_fields if data.get(field) is not None)
            completeness_scores.append(complete_fields / len(required_fields))
        completeness = (
            sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0
        )

        # Consistency: % de registros con OHLC consistente
        consistent_count = 0
        for data in data_list:
            result = self.validate(data, 'ohlcv')
            if result['is_valid']:
                consistent_count += 1
        consistency = consistent_count / total if total > 0 else 0.0

        # Accuracy: Basado en validación de rangos (simplificado)
        accuracy = consistency  # Por ahora, usar consistencia como proxy

        # Timeliness: Basado en timestamps (simplificado)
        # Verificar que timestamps están en orden y no hay gaps grandes
        timestamps = [data.get('timestamp') for data in data_list if data.get('timestamp')]
        if timestamps and len(timestamps) > 1:
            sorted_timestamps = sorted([ts for ts in timestamps if isinstance(ts, datetime)])
            if len(sorted_timestamps) > 1:
                # Verificar que no hay gaps mayores a 1 día
                from datetime import timedelta

                gaps = [
                    (sorted_timestamps[i] - sorted_timestamps[i - 1])
                    for i in range(1, len(sorted_timestamps))
                ]
                max_gap = max(gaps) if gaps else timedelta(days=0)
                timeliness = 1.0 if max_gap.days <= 1 else max(0.0, 1.0 - (max_gap.days / 365))
            else:
                timeliness = 1.0
        else:
            timeliness = 0.0

        return {
            'completeness': float(completeness),
            'consistency': float(consistency),
            'accuracy': float(accuracy),
            'timeliness': float(timeliness),
            'overall_score': float((completeness + consistency + accuracy + timeliness) / 4),
        }
