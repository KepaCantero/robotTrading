"""
API endpoints para gestión de estrategias - TASK-31

Proporciona endpoints REST para gestionar el sistema de estrategias múltiples,
incluyendo carga, activación, métricas y configuración.

GAP Fixes:
- API-002: Added structured logging with correlation IDs
- API-005: FIXED - Added security decorators (rate_limit, require_auth, audit_log)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

# Import protocols for type hints in Depends annotations
# These are imported to avoid circular dependencies
from app.shared.config.di_container import (
    get_execution_engine as di_get_execution_engine,
    get_strategy_config_loader as di_get_strategy_config_loader,
    get_strategy_logger as di_get_strategy_logger,
    get_strategy_registry as di_get_strategy_registry,
)

from . import audit_logger, get_correlation_id
from .security import audit_log, rate_limit, require_auth

if TYPE_CHECKING:
    from app.domain.strategies.execution_engine import ExecutionEngine
    from app.domain.strategies.protocols import (
        StrategyLoggerProto as StrategyLogger,
        StrategyRegistryProto as StrategyRegistry,
    )

logger = logging.getLogger(__name__)

# Router para estrategias
router = APIRouter(prefix="/strategies", tags=["Strategies"])


def get_strategy_registry_dep() -> StrategyRegistry:
    """Obtener instancia del registry de estrategias desde el contenedor de DI."""
    return di_get_strategy_registry()


def get_config_loader():
    """Obtener instancia del cargador de configuración desde el contenedor de DI."""
    return di_get_strategy_config_loader()


def get_strategy_logger_dep() -> StrategyLogger:
    """Obtener instancia del logger de estrategias desde el contenedor de DI."""
    return di_get_strategy_logger()


def get_execution_engine_dep() -> ExecutionEngine:
    """Obtener instancia del motor de ejecución desde el contenedor de DI."""
    return di_get_execution_engine()


# Modelos Pydantic para requests/responses
class StrategyConfigRequest(BaseModel):
    """Request para configuración de estrategia."""

    config: dict[str, Any]


class StrategyLoadRequest(BaseModel):
    """Request para cargar estrategia."""

    name: str
    config: dict[str, Any]


class StrategyActivateRequest(BaseModel):
    """Request para activar estrategia."""

    name: str


class StrategyUpdateRequest(BaseModel):
    """Request para actualizar estrategia."""

    parameters: dict[str, Any]


class StrategyResponse(BaseModel):
    """Response de estrategia."""

    name: str
    is_active: bool
    is_currently_active: bool
    version: str
    description: str
    created_at: str
    parameters: dict[str, Any]


class StrategyMetricsResponse(BaseModel):
    """Response de métricas de estrategia."""

    strategy: str
    signals_generated: int
    signals_executed: int
    signals_rejected: int
    execution_rate: float
    rejection_rate: float
    error_count: int
    error_rate: float
    total_logs: int
    first_log: str | None
    last_log: str | None


class ExecutionStatsResponse(BaseModel):
    """Response de estadísticas de ejecución."""

    is_running: bool
    cycle_count: int
    total_signals_generated: int
    total_signals_executed: int
    execution_rate: float
    created_at: str
    active_strategy: str | None


# Endpoints


@router.get("/", response_model=dict[str, Any])
@rate_limit(max_requests=30, window_seconds=60)
@require_auth(roles=["admin", "user"])
@audit_log("strategies_overview")
async def get_strategies_overview(
    request: Request,
    registry: Annotated[StrategyRegistry, Depends(get_strategy_registry_dep)],
):
    """Obtener resumen de todas las estrategias."""
    correlation_id = get_correlation_id(request)
    try:
        audit_logger.info(
            "strategies_overview_requested",
            extra={"correlation_id": correlation_id},
        )
        return registry.get_all_strategies_status()
    except Exception as e:
        audit_logger.error(
            "strategies_overview_error",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )
        logger.error(f"Error getting strategies overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting strategies overview: {e!s}",
        ) from e


@router.get("/available", response_model=list[str])
@rate_limit(max_requests=30, window_seconds=60)
@require_auth(roles=["admin", "user"])
@audit_log("available_strategies_listed")
async def get_available_strategies(
    request: Request,
    registry: Annotated[StrategyRegistry, Depends(get_strategy_registry_dep)],
):
    """Obtener lista de estrategias disponibles."""
    correlation_id = get_correlation_id(request)
    try:
        audit_logger.info(
            "available_strategies_requested",
            extra={"correlation_id": correlation_id},
        )
        return registry.list_available_strategies()
    except Exception as e:
        audit_logger.error(
            "available_strategies_error",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )
        logger.error(f"Error getting available strategies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting available strategies: {e!s}",
        ) from e


@router.get("/loaded", response_model=list[str])
@rate_limit(max_requests=30, window_seconds=60)
@require_auth(roles=["admin", "user"])
@audit_log("loaded_strategies_listed")
async def get_loaded_strategies(
    request: Request,
    registry: Annotated[StrategyRegistry, Depends(get_strategy_registry_dep)],
):
    """Obtener lista de estrategias cargadas."""
    correlation_id = get_correlation_id(request)
    try:
        audit_logger.info(
            "loaded_strategies_requested",
            extra={"correlation_id": correlation_id},
        )
        return registry.list_loaded_strategies()
    except Exception as e:
        audit_logger.error(
            "loaded_strategies_error",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )
        logger.error(f"Error getting loaded strategies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting loaded strategies: {e!s}",
        ) from e


@router.post("/load", response_model=StrategyResponse)
@rate_limit(max_requests=10, window_seconds=60)
@require_auth(roles=["admin"])
@audit_log("strategy_loaded")
async def load_strategy(
    request: Request,
    load_request: StrategyLoadRequest,
    registry: Annotated[StrategyRegistry, Depends(get_strategy_registry_dep)],
    logger_instance: Annotated[StrategyLogger, Depends(get_strategy_logger_dep)],
):
    """Cargar una estrategia."""
    correlation_id = get_correlation_id(request)
    try:
        audit_logger.info(
            "strategy_load_requested",
            extra={"correlation_id": correlation_id, "strategy": load_request.name},
        )
        strategy = registry.load_strategy(load_request.name, load_request.config)
        logger_instance.log_strategy_loaded(load_request.name, load_request.config)

        return StrategyResponse(
            name=strategy.name,
            is_active=strategy.is_active,
            is_currently_active=registry.active_strategy == load_request.name,
            version=strategy.version,
            description=strategy.description,
            created_at=strategy.created_at.isoformat(),
            parameters=strategy.get_parameters(),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        audit_logger.error(
            "strategy_load_error",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )
        logger.error(f"Error loading strategy {load_request.name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading strategy: {e!s}",
        ) from e


@router.post("/activate", response_model=dict[str, str])
@rate_limit(max_requests=10, window_seconds=60)
@require_auth(roles=["admin"])
@audit_log("strategy_activated")
async def activate_strategy(
    request: Request,
    activate_request: StrategyActivateRequest,
    registry: Annotated[StrategyRegistry, Depends(get_strategy_registry_dep)],
    logger_instance: Annotated[StrategyLogger, Depends(get_strategy_logger_dep)],
):
    """Activar una estrategia."""
    correlation_id = get_correlation_id(request)
    try:
        audit_logger.info(
            "strategy_activate_requested",
            extra={"correlation_id": correlation_id, "strategy": activate_request.name},
        )
        registry.set_active_strategy(activate_request.name)
        logger_instance.log_strategy_activated(activate_request.name)

        return {"message": f"Strategy '{activate_request.name}' activated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        audit_logger.error(
            "strategy_activate_error",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )
        logger.error(f"Error activating strategy {activate_request.name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error activating strategy: {e!s}",
        ) from e


@router.post("/deactivate", response_model=dict[str, str])
@rate_limit(max_requests=10, window_seconds=60)
@require_auth(roles=["admin"])
@audit_log("strategy_deactivated")
async def deactivate_strategy(
    request: Request,
    registry: Annotated[StrategyRegistry, Depends(get_strategy_registry_dep)],
    logger_instance: Annotated[StrategyLogger, Depends(get_strategy_logger_dep)],
):
    """Desactivar estrategia activa."""
    correlation_id = get_correlation_id(request)
    try:
        audit_logger.info(
            "strategy_deactivate_requested",
            extra={"correlation_id": correlation_id},
        )
        active_strategy = registry.get_active_strategy()
        if not active_strategy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active strategy to deactivate",
            )

        strategy_name = active_strategy.name
        registry.set_active_strategy("")  # Desactivar
        logger_instance.log_strategy_deactivated(strategy_name)

        return {"message": f"Strategy '{strategy_name}' deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        audit_logger.error(
            "strategy_deactivate_error",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )
        logger.error(f"Error deactivating strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deactivating strategy: {e!s}",
        ) from e


@router.delete("/unload/{strategy_name}", response_model=dict[str, str])
@rate_limit(max_requests=10, window_seconds=60)
@require_auth(roles=["admin"])
@audit_log("strategy_unloaded")
async def unload_strategy(
    strategy_name: str,
    request: Request,
    registry: Annotated[StrategyRegistry, Depends(get_strategy_registry_dep)],
    logger_instance: Annotated[StrategyLogger, Depends(get_strategy_logger_dep)],
):
    """Descargar una estrategia."""
    correlation_id = get_correlation_id(request)
    try:
        audit_logger.info(
            "strategy_unload_requested",
            extra={"correlation_id": correlation_id, "strategy": strategy_name},
        )
        registry.unload_strategy(strategy_name)
        logger_instance.log_strategy_unloaded(strategy_name)

        return {"message": f"Strategy '{strategy_name}' unloaded successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        audit_logger.error(
            "strategy_unload_error",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )
        logger.error(f"Error unloading strategy {strategy_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error unloading strategy: {e!s}",
        ) from e


@router.get("/{strategy_name}", response_model=StrategyResponse)
@rate_limit(max_requests=30, window_seconds=60)
@require_auth(roles=["admin", "user"])
@audit_log("strategy_details")
async def get_strategy(
    strategy_name: str,
    request: Request,
    registry: Annotated[StrategyRegistry, Depends(get_strategy_registry_dep)],
):
    """Obtener información de una estrategia."""
    correlation_id = get_correlation_id(request)
    try:
        audit_logger.info(
            "strategy_details_requested",
            extra={"correlation_id": correlation_id, "strategy": strategy_name},
        )
        status_info = registry.get_strategy_status(strategy_name)

        return StrategyResponse(
            name=str(status_info["name"]),
            is_active=bool(status_info["is_active"]),
            is_currently_active=bool(status_info["is_currently_active"]),
            version=str(status_info["version"]),
            description=str(status_info["description"]),
            created_at=str(status_info["created_at"]),
            parameters=(
                status_info["parameters"] if isinstance(status_info["parameters"], dict) else {}
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        audit_logger.error(
            "strategy_details_error",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )
        logger.error(f"Error getting strategy {strategy_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting strategy: {e!s}",
        ) from e


@router.put("/{strategy_name}/parameters", response_model=dict[str, str])
@rate_limit(max_requests=10, window_seconds=60)
@require_auth(roles=["admin"])
@audit_log("strategy_parameters_updated")
async def update_strategy_parameters(
    strategy_name: str,
    request: Request,
    update_request: StrategyUpdateRequest,
    registry: Annotated[StrategyRegistry, Depends(get_strategy_registry_dep)],
):
    """Actualizar parámetros de una estrategia."""
    correlation_id = get_correlation_id(request)
    try:
        audit_logger.info(
            "strategy_parameters_update_requested",
            extra={"correlation_id": correlation_id, "strategy": strategy_name},
        )
        strategy = registry.get_strategy(strategy_name)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy '{strategy_name}' not found",
            )

        strategy.update_parameters(update_request.parameters)

        return {"message": f"Parameters updated for strategy '{strategy_name}'"}
    except HTTPException:
        raise
    except Exception as e:
        audit_logger.error(
            "strategy_parameters_update_error",
            extra={"correlation_id": correlation_id, "error": str(e)},
        )
        logger.error(f"Error updating strategy parameters {strategy_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating parameters: {e!s}",
        ) from e


@router.get("/{strategy_name}/metrics", response_model=StrategyMetricsResponse)
@rate_limit(max_requests=30, window_seconds=60)
@require_auth(roles=["admin", "user"])
@audit_log("strategy_metrics")
async def get_strategy_metrics(
    strategy_name: str,
    logger_instance: Annotated[StrategyLogger, Depends(get_strategy_logger_dep)],
):
    """Obtener métricas de una estrategia."""
    try:
        metrics = logger_instance.get_strategy_metrics(strategy_name)

        return StrategyMetricsResponse(
            strategy=str(metrics["strategy"]),
            signals_generated=int(metrics["signals_generated"]),
            signals_executed=int(metrics["signals_executed"]),
            signals_rejected=int(metrics["signals_rejected"]),
            execution_rate=float(metrics["execution_rate"]),
            rejection_rate=float(metrics["rejection_rate"]),
            error_count=int(metrics["error_count"]),
            error_rate=float(metrics["error_rate"]),
            total_logs=int(metrics["total_logs"]),
            first_log=(str(metrics["first_log"]) if metrics["first_log"] is not None else None),
            last_log=(str(metrics["last_log"]) if metrics["last_log"] is not None else None),
        )
    except Exception as e:
        logger.error(f"Error getting strategy metrics {strategy_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting metrics: {e!s}",
        ) from e


@router.get("/metrics/all", response_model=dict[str, Any])
async def get_all_metrics(
    logger_instance: Annotated[StrategyLogger, Depends(get_strategy_logger_dep)],
):
    """Obtener métricas de todas las estrategias."""
    try:
        return logger_instance.get_all_metrics()
    except Exception as e:
        logger.error(f"Error getting all metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting metrics: {e!s}",
        ) from e


@router.get("/execution/stats", response_model=ExecutionStatsResponse)
async def get_execution_stats(
    engine: Annotated[ExecutionEngine, Depends(get_execution_engine_dep)],
):
    """Obtener estadísticas del motor de ejecución."""
    try:
        stats = engine.get_execution_stats()

        return ExecutionStatsResponse(
            is_running=stats["is_running"],
            cycle_count=stats["cycle_count"],
            total_signals_generated=stats["total_signals_generated"],
            total_signals_executed=stats["total_signals_executed"],
            execution_rate=stats["execution_rate"],
            created_at=stats["created_at"],
            active_strategy=stats["active_strategy"],
        )
    except Exception as e:
        logger.error(f"Error getting execution stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting execution stats: {e!s}",
        ) from e


@router.post("/execution/start", response_model=dict[str, str])
@rate_limit(max_requests=10, window_seconds=60)
@require_auth(roles=["admin"])
@audit_log("execution_engine_started")
async def start_execution_engine(
    engine: Annotated[ExecutionEngine, Depends(get_execution_engine_dep)],
):
    """Iniciar motor de ejecución."""
    try:
        engine.start()
        return {"message": "Execution engine started successfully"}
    except Exception as e:
        logger.error(f"Error starting execution engine: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting execution engine: {e!s}",
        ) from e


@router.post("/execution/stop", response_model=dict[str, str])
@rate_limit(max_requests=10, window_seconds=60)
@require_auth(roles=["admin"])
@audit_log("execution_engine_stopped")
async def stop_execution_engine(
    engine: Annotated[ExecutionEngine, Depends(get_execution_engine_dep)],
):
    """Detener motor de ejecución."""
    try:
        engine.stop()
        return {"message": "Execution engine stopped successfully"}
    except Exception as e:
        logger.error(f"Error stopping execution engine: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping execution engine: {e!s}",
        ) from e


@router.post("/execution/reset-stats", response_model=dict[str, str])
@rate_limit(max_requests=5, window_seconds=60)
@require_auth(roles=["admin"])
@audit_log("execution_stats_reset")
async def reset_execution_stats(
    engine: Annotated[ExecutionEngine, Depends(get_execution_engine_dep)],
):
    """Resetear estadísticas del motor de ejecución."""
    try:
        engine.reset_stats()
        return {"message": "Execution stats reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting execution stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting stats: {e!s}",
        ) from e
