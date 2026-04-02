"""
DataCleaningPipeline - Pipeline completo de limpieza de datos.

Combina:
- Outlier detection
- Gap interpolation
- Quality validation
"""

from __future__ import annotations

import logging
from typing import Any

from .gap_interpolator import GapInterpolator
from .outlier_detector import OutlierDetector
from .quality_validator import QualityValidator

logger = logging.getLogger(__name__)


class DataCleaningPipeline:
    """
    Pipeline completo de limpieza de datos.

    Aplica secuencialmente:
    1. Detección de outliers
    2. Interpolación de gaps
    3. Validación de calidad
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Inicializar pipeline.

        Args:
            config: Configuración
        """
        config = config or {}

        self.outlier_detector = OutlierDetector(config.get("outlier_config", {}))
        self.gap_interpolator = GapInterpolator(config.get("gap_config", {}))
        self.quality_validator = QualityValidator(config.get("quality_config", {}))

        # Configuración del pipeline
        self.detect_outliers = config.get("detect_outliers", True)
        self.interpolate_gaps = config.get("interpolate_gaps", True)
        self.validate_quality = config.get("validate_quality", True)
        self.remove_outliers = config.get("remove_outliers", False)  # O interpolar
        self.min_quality_score = config.get("min_quality_score", 0.7)

    def clean(
        self, data: list[dict[str, Any]], symbol: str, data_type: str = "ohlcv"
    ) -> dict[str, Any]:
        """
        Limpiar datos completos.

        Args:
            data: Lista de datos a limpiar
            symbol: Símbolo
            data_type: Tipo de datos

        Returns:
            Dict con:
                - cleaned_data: List[Dict] - Datos limpiados
                - removed_indices: List[int] - Índices removidos
                - outliers_detected: int
                - gaps_filled: int
                - quality_metrics: Dict
                - cleaning_report: Dict
        """
        cleaned_data = data.copy()
        removed_indices = []
        outliers_detected = 0
        gaps_filled = 0

        # 1. Detectar outliers
        if self.detect_outliers:
            outlier_result = self.outlier_detector.detect_in_ohlcv(cleaned_data)
            outliers_detected = outlier_result.get("total_outliers", 0)

            if self.remove_outliers:
                # Remover outliers
                outlier_indices = set(outlier_result.get("combined_outliers", []))
                cleaned_data = [
                    item for i, item in enumerate(cleaned_data) if i not in outlier_indices
                ]
                removed_indices.extend(sorted(outlier_indices))
            else:
                # Interpolar outliers (marcar para interpolación)
                outlier_indices = set(outlier_result.get("combined_outliers", []))
                # Los outliers se manejarán en la interpolación de gaps

        # 2. Interpolar gaps
        if self.interpolate_gaps:
            gaps_info = self.gap_interpolator.detect_gaps(cleaned_data)
            gaps_filled = gaps_info.get("total_gaps", 0)

            cleaned_data = self.gap_interpolator.interpolate(cleaned_data)

        # 3. Validar calidad
        quality_metrics = {}
        if self.validate_quality:
            self.quality_validator.validate_batch(cleaned_data, data_type)
            quality_metrics = self.quality_validator.get_quality_metrics(cleaned_data)

            # Si calidad es muy baja, advertir
            if quality_metrics.get("overall_score", 0) < self.min_quality_score:
                logger.warning(
                    f"Calidad de datos baja para {symbol}: "
                    f"score={quality_metrics.get('overall_score', 0):.2f}"
                )

        # Generar reporte
        cleaning_report = {
            "symbol": symbol,
            "original_count": len(data),
            "cleaned_count": len(cleaned_data),
            "removed_count": len(removed_indices),
            "outliers_detected": outliers_detected,
            "gaps_filled": gaps_filled,
            "quality_metrics": quality_metrics,
            "cleaning_applied": {
                "outlier_detection": self.detect_outliers,
                "gap_interpolation": self.interpolate_gaps,
                "quality_validation": self.validate_quality,
                "outliers_removed": self.remove_outliers,
            },
        }

        return {
            "cleaned_data": cleaned_data,
            "removed_indices": removed_indices,
            "outliers_detected": outliers_detected,
            "gaps_filled": gaps_filled,
            "quality_metrics": quality_metrics,
            "cleaning_report": cleaning_report,
        }

    def clean_single(
        self, data: dict[str, Any], symbol: str, data_type: str = "ohlcv"
    ) -> dict[str, Any]:
        """
        Limpiar un solo registro.

        Args:
            data: Dict con datos
            symbol: Símbolo
            data_type: Tipo de datos

        Returns:
            Dict con datos limpiados y validación
        """
        validation_result = self.quality_validator.validate(data, data_type)

        if validation_result["is_valid"]:
            return {"cleaned_data": data, "is_valid": True, "errors": []}
        else:
            return {
                "cleaned_data": data,  # Mantener datos originales si no son válidos
                "is_valid": False,
                "errors": validation_result["errors"],
            }
