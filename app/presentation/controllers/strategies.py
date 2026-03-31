"""
API endpoints para gestión de estrategias - TASK-DEFAULT_VALUE_31

Proporciona endpoints REST para gestionar el sistema de estrategias múltiples,
incluyendo carga, activación, métricas y configuración.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

if TYPE_CHECKING:
    from app.domain.strategies.protocols import (
        StrategyLoggerProto as StrategyLogger,
    )
    from app.domain.strategies.strategy_registry import StrategyRegistry

# Constants
DEFAULT_VALUE_31 = 31


logger = logging.getLogger(__name__)

# Router para estrategias
router = APIRouter(prefix="/strategies", tags=["Strategies"])

# Instancias globales (en producción usar dependency injection)
_strategy_registry: StrategyRegistry | None = None
_config_loader: object | None = None
_execution_engine: object | None = None
_strategy_logger: StrategyLogger | None = None


def get_strategy_registry() -> StrategyRegistry:
    """Obtener instancia del registry de estrategias."""
    global _strategy_registry
    if _strategy_registry is None:
        # Lazy import to avoid circular dependencies
        from app.domain.strategies.strategy_registry import (
            StrategyRegistry as ConcreteStrategyRegistry,
        )

        _strategy_registry = ConcreteStrategyRegistry()

    return _strategy_registry


def get_config_loader():
    """Obtener instancia del cargador de configuración."""
    global _config_loader
    if _config_loader is None:
        # Lazy import to avoid circular dependencies
        from app.domain.strategies.config_loader import StrategyConfigLoader

        _config_loader = StrategyConfigLoader()

    return _config_loader


def get_strategy_logger() -> StrategyLogger:
    """Obtener instancia del logger de estrategias."""
    global _strategy_logger
    if _strategy_logger is None:
        # Lazy import to avoid circular dependencies
        from app.domain.strategies.strategy_logger import StrategyLogger as StrategyLoggerImpl

        _strategy_logger = StrategyLoggerImpl()

    return _strategy_logger


def get_execution_engine():
    """Obtener instancia del motor de ejecución."""
    global _execution_engine

    if _execution_engine is None:
        # Lazy import to avoid circular dependencies
        from app.domain.strategies.execution_engine import ExecutionEngine

        registry = get_strategy_registry()
        strategy_logger = get_strategy_logger()
        _execution_engine = ExecutionEngine(registry, strategy_logger)
        logging.getLogger(__name__).info("ExecutionEngine singleton initialized")

    return _execution_engine


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
async def get_strategies_overview(
    registry: StrategyRegistry = Depends(get_strategy_registry),
):
    """Obtener resumen de todas las estrategias."""
    try:
        return registry.get_all_strategies_status()
    except Exception as e:
        logger.error(f"Error getting strategies overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting strategies overview: {e!s}",
        ) from e


@router.get("/available", response_model=list[str])
async def get_available_strategies(
    registry: StrategyRegistry = Depends(get_strategy_registry),
):
    """Obtener lista de estrategias disponibles."""
    try:
        return registry.list_available_strategies()
    except Exception as e:
        logger.error(f"Error getting available strategies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting available strategies: {e!s}",
        ) from e


@router.get("/loaded", response_model=list[str])
async def get_loaded_strategies(
    registry: StrategyRegistry = Depends(get_strategy_registry),
):
    """Obtener lista de estrategias cargadas."""
    try:
        return registry.list_loaded_strategies()
    except Exception as e:
        logger.error(f"Error getting loaded strategies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting loaded strategies: {e!s}",
        ) from e


@router.post("/load", response_model=StrategyResponse)
async def load_strategy(
    request: StrategyLoadRequest,
    registry: StrategyRegistry = Depends(get_strategy_registry),
    logger_instance: StrategyLogger = Depends(get_strategy_logger),
):
    """Cargar una estrategia."""
    try:
        strategy = registry.load_strategy(request.name, request.config)
        logger_instance.log_strategy_loaded(request.name, request.config)

        return StrategyResponse(
            name=strategy.name,
            is_active=strategy.is_active,
            is_currently_active=registry.active_strategy == request.name,
            version=strategy.version,
            description=strategy.description,
            created_at=strategy.created_at.isoformat(),
            parameters=strategy.get_parameters(),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error loading strategy {request.name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading strategy: {e!s}",
        ) from e


@router.post("/activate", response_model=dict[str, str])
async def activate_strategy(
    request: StrategyActivateRequest,
    registry: StrategyRegistry = Depends(get_strategy_registry),
    logger_instance: StrategyLogger = Depends(get_strategy_logger),
):
    """Activar una estrategia."""
    try:
        registry.set_active_strategy(request.name)
        logger_instance.log_strategy_activated(request.name)

        return {"message": f"Strategy '{request.name}' activated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error activating strategy {request.name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error activating strategy: {e!s}",
        ) from e


@router.post("/deactivate", response_model=dict[str, str])
async def deactivate_strategy(
    registry: StrategyRegistry = Depends(get_strategy_registry),
    logger_instance: StrategyLogger = Depends(get_strategy_logger),
):
    """Desactivar estrategia activa."""
    try:
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
        logger.error(f"Error deactivating strategy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deactivating strategy: {e!s}",
        ) from e


@router.delete("/unload/{strategy_name}", response_model=dict[str, str])
async def unload_strategy(
    strategy_name: str,
    registry: StrategyRegistry = Depends(get_strategy_registry),
    logger_instance: StrategyLogger = Depends(get_strategy_logger),
):
    """Descargar una estrategia."""
    try:
        registry.unload_strategy(strategy_name)
        logger_instance.log_strategy_unloaded(strategy_name)

        return {"message": f"Strategy '{strategy_name}' unloaded successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error unloading strategy {strategy_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error unloading strategy: {e!s}",
        ) from e


@router.get("/{strategy_name}", response_model=StrategyResponse)
async def get_strategy(
    strategy_name: str, registry: StrategyRegistry = Depends(get_strategy_registry)
):
    """Obtener información de una estrategia."""
    try:
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
        logger.error(f"Error getting strategy {strategy_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting strategy: {e!s}",
        ) from e


@router.put("/{strategy_name}/parameters", response_model=dict[str, str])
async def update_strategy_parameters(
    strategy_name: str,
    request: StrategyUpdateRequest,
    registry: StrategyRegistry = Depends(get_strategy_registry),
):
    """Actualizar parámetros de una estrategia."""
    try:
        strategy = registry.get_strategy(strategy_name)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy '{strategy_name}' not found",
            )

        strategy.update_parameters(request.parameters)

        return {"message": f"Parameters updated for strategy '{strategy_name}'"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy parameters {strategy_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating parameters: {e!s}",
        ) from e


@router.get("/{strategy_name}/metrics", response_model=StrategyMetricsResponse)
async def get_strategy_metrics(
    strategy_name: str, logger_instance: StrategyLogger = Depends(get_strategy_logger)
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
    logger_instance: StrategyLogger = Depends(get_strategy_logger),
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
async def get_execution_stats(engine=Depends(get_execution_engine)):
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
async def start_execution_engine(
    engine=Depends(get_execution_engine),
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
async def stop_execution_engine(
    engine=Depends(get_execution_engine),
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
async def reset_execution_stats(
    engine=Depends(get_execution_engine),
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
