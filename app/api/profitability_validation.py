"""
API endpoints para validación de rentabilidad de estrategias.

Este módulo proporciona endpoints REST para validar que las estrategias
generen rentabilidad neta positiva después de todos los costos operativos.
"""

from __future__ import annotations
import logging
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.centralized_config import get_config
from app.models.profitability_validation import (
    HistoricalValidation,
    ProfitabilityValidation,
    StrategyComparison,
    ValidationCriteria,
    ValidationReport,
    ValidationRequest,
    ValidationResponse,
)
from app.services.profitability_validation_service import ProfitabilityValidationService

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(prefix="/api/v1/profitability", tags=["profitability-validation"])

# Instancia del servicio
profitability_service = ProfitabilityValidationService()


@router.post("/validate", response_model=ValidationResponse)
async def validate_strategy_profitability(
    request: ValidationRequest,
) -> ValidationResponse:
    """
    Validar rentabilidad de una estrategia específica.

    Este endpoint valida que una estrategia genere rentabilidad neta positiva
    después de todos los costos operativos, incluyendo comisiones, slippage,
    market impact e infraestructura.

    Args:
        request: Datos de la estrategia y trades para validación

    Returns:
        ValidationResponse: Resultado completo de la validación

    Raises:
        HTTPException: Si hay errores en la validación
    """
    try:
        logger.info(f"Validating profitability for strategy: {request.strategy_name}")

        # Validar datos de entrada
        if not request.trades_data:
            raise HTTPException(
                status_code=400,
                detail="Trades data is required for profitability validation",
            )

        if request.initial_capital <= 0:
            raise HTTPException(status_code=400, detail="Initial capital must be positive")

        if request.period_start >= request.period_end:
            raise HTTPException(status_code=400, detail="Period start must be before period end")

        # Ejecutar validación
        result = profitability_service.validate_strategy_profitability(request)

        logger.info(
            f"Validation completed for {request.strategy_name}: {result.validation.status.value}"
        )

        return result

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(f"Error validating strategy profitability: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during profitability validation: {str(e)}",
        )


@router.post("/validate/batch", response_model=List[ValidationResponse])
async def validate_multiple_strategies(
    requests: List[ValidationRequest],
) -> List[ValidationResponse]:
    """
    Validar rentabilidad de múltiples estrategias en lote.

    Este endpoint permite validar múltiples estrategias de forma eficiente,
    útil para comparaciones y análisis masivos.

    Args:
        requests: Lista de requests de validación

    Returns:
        List[ValidationResponse]: Resultados de todas las validaciones

    Raises:
        HTTPException: Si hay errores en la validación
    """
    try:
        logger.info(f"Validating profitability for {len(requests)} strategies")

        if not requests:
            raise HTTPException(
                status_code=400, detail="At least one validation request is required"
            )

        if len(requests) > 50:  # Límite de seguridad
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 strategies can be validated in a single batch",
            )

        results = []
        for request in requests:
            try:
                result = profitability_service.validate_strategy_profitability(request)
                results.append(result)
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.error(f"Error validating strategy {request.strategy_name}: {str(e)}")
                # Continuar con otras estrategias en caso de error individual
                continue

        logger.info(f"Batch validation completed: {len(results)}/{len(requests)} successful")

        return results

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error in batch profitability validation: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Internal error during batch validation: {str(e)}"
        )


@router.post("/compare", response_model=StrategyComparison)
async def compare_strategies(
    validations: List[ProfitabilityValidation],
) -> StrategyComparison:
    """
    Comparar múltiples estrategias validadas.

    Este endpoint compara el rendimiento de múltiples estrategias
    y proporciona un ranking basado en métricas de rentabilidad.

    Args:
        validations: Lista de validaciones de estrategias

    Returns:
        StrategyComparison: Comparación detallada de estrategias

    Raises:
        HTTPException: Si hay errores en la comparación
    """
    try:
        logger.info(f"Comparing {len(validations)} strategies")

        if not validations:
            raise HTTPException(
                status_code=400,
                detail="At least one validation is required for comparison",
            )

        if len(validations) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least two validations are required for comparison",
            )

        # Ejecutar comparación
        comparison = profitability_service.compare_strategies(validations)

        logger.info(f"Strategy comparison completed. Best: {comparison.best_strategy}")

        return comparison

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(f"Error comparing strategies: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during strategy comparison: {str(e)}",
        )


@router.post("/analyze/historical", response_model=HistoricalValidation)
async def analyze_historical_performance(
    strategy_name: str = Query(..., description="Nombre de la estrategia"),
    validations: List[ProfitabilityValidation] = Depends(),
) -> HistoricalValidation:
    """
    Analizar rendimiento histórico de una estrategia.

    Este endpoint analiza el rendimiento histórico de una estrategia
    basado en múltiples validaciones a lo largo del tiempo.

    Args:
        strategy_name: Nombre de la estrategia a analizar
        validations: Lista de validaciones históricas

    Returns:
        HistoricalValidation: Análisis histórico completo

    Raises:
        HTTPException: Si hay errores en el análisis
    """
    try:
        logger.info(f"Analyzing historical performance for strategy: {strategy_name}")

        if not validations:
            raise HTTPException(
                status_code=400,
                detail="At least one validation is required for historical analysis",
            )

        # Filtrar validaciones por estrategia
        strategy_validations = [v for v in validations if v.strategy_name == strategy_name]

        if not strategy_validations:
            raise HTTPException(
                status_code=404,
                detail=f"No validations found for strategy: {strategy_name}",
            )

        # Ejecutar análisis histórico
        historical_analysis = profitability_service.analyze_historical_performance(
            strategy_name, strategy_validations
        )

        logger.info(f"Historical analysis completed for {strategy_name}")

        return historical_analysis

    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(f"Error analyzing historical performance: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during historical analysis: {str(e)}",
        )


@router.post("/report", response_model=ValidationReport)
async def generate_validation_report(
    validations: List[ProfitabilityValidation],
    include_comparison: bool = Query(
        default=True, description="Incluir comparación de estrategias"
    ),
    include_historical: bool = Query(default=True, description="Incluir análisis histórico"),
) -> ValidationReport:
    """
    Generar reporte completo de validación de rentabilidad.

    Este endpoint genera un reporte comprensivo que incluye validaciones
    individuales, comparaciones entre estrategias y análisis histórico.

    Args:
        validations: Lista de validaciones de estrategias
        include_comparison: Si incluir comparación entre estrategias
        include_historical: Si incluir análisis histórico

    Returns:
        ValidationReport: Reporte completo de validación

    Raises:
        HTTPException: Si hay errores en la generación del reporte
    """
    try:
        logger.info(f"Generating validation report for {len(validations)} validations")

        if not validations:
            raise HTTPException(
                status_code=400,
                detail="At least one validation is required for report generation",
            )

        # Generar reporte
        report = profitability_service.generate_validation_report(
            validations, include_comparison, include_historical
        )

        logger.info("Validation report generated successfully")

        return report

    except HTTPException:
        raise
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Error generating validation report: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Internal error during report generation: {str(e)}"
        )


@router.get("/criteria/default", response_model=ValidationCriteria)
async def get_default_validation_criteria() -> ValidationCriteria:
    """
    Obtener criterios de validación por defecto.

    Este endpoint devuelve los criterios de validación por defecto
    que se utilizan cuando no se especifican criterios personalizados.

    Returns:
        ValidationCriteria: Criterios de validación por defecto
    """
    try:
        logger.info("Retrieving default validation criteria")

        # Obtener configuración
        get_config()

        # Crear criterios basados en configuración
        criteria = ValidationCriteria(
            min_net_profit=Decimal("100"),
            min_profit_margin=Decimal("5"),
            min_roi=Decimal("10"),
            min_sharpe_ratio=Decimal("1.0"),
            max_drawdown_limit=Decimal("15"),
            min_win_rate=Decimal("50"),
            min_profit_factor=Decimal("1.5"),
            max_cost_impact_ratio=Decimal("0.3"),
        )

        return criteria

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error retrieving default criteria: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error retrieving default criteria: {str(e)}",
        )


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check para el servicio de validación de rentabilidad.

    Returns:
        JSONResponse: Estado del servicio
    """
    try:
        # Verificar que el servicio esté funcionando
        ValidationCriteria()

        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "service": "profitability-validation",
                "version": "1.0.0",
                "timestamp": "2025-01-27T00:00:00Z",
            },
        )

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "profitability-validation",
                "error": str(e),
                "timestamp": "2025-01-27T00:00:00Z",
            },
        )


@router.get("/metrics/summary")
async def get_metrics_summary() -> JSONResponse:
    """
    Obtener resumen de métricas de validación.

    Este endpoint proporciona un resumen de las métricas clave
    utilizadas en la validación de rentabilidad.

    Returns:
        JSONResponse: Resumen de métricas
    """
    try:
        logger.info("Retrieving metrics summary")

        summary = {
            "profitability_metrics": [
                "net_profit",
                "gross_profit",
                "total_costs",
                "profit_margin",
                "return_on_investment",
                "sharpe_ratio",
                "max_drawdown",
                "win_rate",
                "profit_factor",
                "cost_impact_ratio",
            ],
            "validation_criteria": [
                "min_net_profit",
                "min_profit_margin",
                "min_roi",
                "min_sharpe_ratio",
                "max_drawdown_limit",
                "min_win_rate",
                "min_profit_factor",
                "max_cost_impact_ratio",
            ],
            "validation_statuses": ["passed", "failed", "warning", "pending"],
            "risk_levels": ["low", "medium", "high"],
        }

        return JSONResponse(status_code=200, content=summary)

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Error retrieving metrics summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error retrieving metrics summary: {str(e)}",
        )
