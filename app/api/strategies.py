"""
API endpoints para gestión de estrategias - TASK-31

Proporciona endpoints REST para gestionar el sistema de estrategias múltiples,
incluyendo carga, activación, métricas y configuración.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.strategies import ExecutionEngine, StrategyConfigLoader, StrategyLogger, StrategyRegistry

logger = logging.getLogger(__name__)

# Router para estrategias
router = APIRouter(prefix="/strategies", tags=["Strategies"])

# Instancias globales (en producción usar dependency injection)
_strategy_registry: Optional[StrategyRegistry] = None
_config_loader: Optional[StrategyConfigLoader] = None
_execution_engine: Optional[ExecutionEngine] = None
_strategy_logger: Optional[StrategyLogger] = None


def get_strategy_registry() -> StrategyRegistry:
    """Obtener instancia del registry de estrategias."""
    global _strategy_registry
    if _strategy_registry is None:
        pass

    return _strategy_registry


def get_config_loader() -> StrategyConfigLoader:
    """Obtener instancia del cargador de configuración."""
    global _config_loader
    if _config_loader is None:
        pass

    return _config_loader


def get_strategy_logger() -> StrategyLogger:
    """Obtener instancia del logger de estrategias."""
    global _strategy_logger
    if _strategy_logger is None:
        pass

    return _strategy_logger


def get_execution_engine() -> ExecutionEngine:
    """Obtener instancia del motor de ejecución."""
    global _execution_engine
    if _execution_engine is None:
        get_strategy_registry()
        get_strategy_logger()

    return _execution_engine


# Modelos Pydantic para requests/responses
class StrategyConfigRequest(BaseModel):
    """Request para configuración de estrategia."""

    config: Dict[str, Any]


class StrategyLoadRequest(BaseModel):
    """Request para cargar estrategia."""

    name: str
    config: Dict[str, Any]


class StrategyActivateRequest(BaseModel):
    """Request para activar estrategia."""

    name: str


class StrategyUpdateRequest(BaseModel):
    """Request para actualizar estrategia."""

    parameters: Dict[str, Any]


class StrategyResponse(BaseModel):
    """Response de estrategia."""

    name: str
    is_active: bool
    is_currently_active: bool
    version: str
    description: str
    created_at: str
    parameters: Dict[str, Any]


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
    first_log: Optional[str]
    last_log: Optional[str]


class ExecutionStatsResponse(BaseModel):
    """Response de estadísticas de ejecución."""

    is_running: bool
    cycle_count: int
    total_signals_generated: int
    total_signals_executed: int
    execution_rate: float
    created_at: str
    active_strategy: Optional[str]


# Endpoints


@router.get("/", response_model=Dict[str, Any])
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
            detail=f"Error getting strategies overview: {str(e)}",
        )


@router.get("/available", response_model=List[str])
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
            detail=f"Error getting available strategies: {str(e)}",
        )


@router.get("/loaded", response_model=List[str])
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
            detail=f"Error getting loaded strategies: {str(e)}",
        )


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error loading strategy {request.name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading strategy: {str(e)}",
        )


@router.post("/activate", response_model=Dict[str, str])
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating strategy {request.name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error activating strategy: {str(e)}",
        )


@router.post("/deactivate", response_model=Dict[str, str])
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
            detail=f"Error deactivating strategy: {str(e)}",
        )


@router.delete("/unload/{strategy_name}", response_model=Dict[str, str])
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error unloading strategy {strategy_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error unloading strategy: {str(e)}",
        )


@router.get("/{strategy_name}", response_model=StrategyResponse)
async def get_strategy(
    strategy_name: str, registry: StrategyRegistry = Depends(get_strategy_registry)
):
    """Obtener información de una estrategia."""
    try:
        status_info = registry.get_strategy_status(strategy_name)

        return StrategyResponse(
            name=status_info["name"],
            is_active=status_info["is_active"],
            is_currently_active=status_info["is_currently_active"],
            version=status_info["version"],
            description=status_info["description"],
            created_at=status_info["created_at"],
            parameters=status_info["parameters"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting strategy: {str(e)}",
        )


@router.put("/{strategy_name}/parameters", response_model=Dict[str, str])
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
            detail=f"Error updating parameters: {str(e)}",
        )


@router.get("/{strategy_name}/metrics", response_model=StrategyMetricsResponse)
async def get_strategy_metrics(
    strategy_name: str, logger_instance: StrategyLogger = Depends(get_strategy_logger)
):
    """Obtener métricas de una estrategia."""
    try:
        metrics = logger_instance.get_strategy_metrics(strategy_name)

        return StrategyMetricsResponse(
            strategy=metrics["strategy"],
            signals_generated=metrics["signals_generated"],
            signals_executed=metrics["signals_executed"],
            signals_rejected=metrics["signals_rejected"],
            execution_rate=metrics["execution_rate"],
            rejection_rate=metrics["rejection_rate"],
            error_count=metrics["error_count"],
            error_rate=metrics["error_rate"],
            total_logs=metrics["total_logs"],
            first_log=metrics["first_log"],
            last_log=metrics["last_log"],
        )
    except Exception as e:
        logger.error(f"Error getting strategy metrics {strategy_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting metrics: {str(e)}",
        )


@router.get("/metrics/all", response_model=Dict[str, Any])
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
            detail=f"Error getting metrics: {str(e)}",
        )


@router.get("/execution/stats", response_model=ExecutionStatsResponse)
async def get_execution_stats(engine: ExecutionEngine = Depends(get_execution_engine)):
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
            detail=f"Error getting execution stats: {str(e)}",
        )


@router.post("/execution/start", response_model=Dict[str, str])
async def start_execution_engine(
    engine: ExecutionEngine = Depends(get_execution_engine),
):
    """Iniciar motor de ejecución."""
    try:
        engine.start()
        return {"message": "Execution engine started successfully"}
    except Exception as e:
        logger.error(f"Error starting execution engine: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting execution engine: {str(e)}",
        )


@router.post("/execution/stop", response_model=Dict[str, str])
async def stop_execution_engine(
    engine: ExecutionEngine = Depends(get_execution_engine),
):
    """Detener motor de ejecución."""
    try:
        engine.stop()
        return {"message": "Execution engine stopped successfully"}
    except Exception as e:
        logger.error(f"Error stopping execution engine: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping execution engine: {str(e)}",
        )


@router.post("/execution/reset-stats", response_model=Dict[str, str])
async def reset_execution_stats(
    engine: ExecutionEngine = Depends(get_execution_engine),
):
    """Resetear estadísticas del motor de ejecución."""
    try:
        engine.reset_stats()
        return {"message": "Execution stats reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting execution stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting stats: {str(e)}",
        )
