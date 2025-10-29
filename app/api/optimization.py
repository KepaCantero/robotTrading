"""
API endpoints for parameter optimization and overfitting prevention.

This module provides FastAPI endpoints for walk-forward analysis, out-of-sample testing,
and parameter optimization to prevent overfitting in trading strategies.
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.models.optimization import (
    OptimizationArtifact,
    OptimizationConfig,
    OptimizationMethod,
    OptimizationMetrics,
    OptimizationParameter,
    OptimizationResult,
    OptimizationSummary,
    OutOfSampleResult,
    OutOfSampleTestRequest,
    ParameterConstraint,
    ParameterOptimizationRequest,
    ParameterType,
)
from app.services.cost_analysis_service import CostAnalysisService
from app.services.parameter_optimization_service import ParameterOptimizationService

router = APIRouter(prefix="/optimization", tags=["Parameter Optimization"])


# Dependency injection
def get_optimization_service() -> ParameterOptimizationService:
    """Get parameter optimization service instance."""
    cost_service = CostAnalysisService()
    return ParameterOptimizationService(cost_service)


@router.post("/optimize-parameters", response_model=OptimizationResult)
async def optimize_parameters(
    request: ParameterOptimizationRequest,
    background_tasks: BackgroundTasks,
    service: ParameterOptimizationService = Depends(get_optimization_service),
):
    """
    Optimize parameters for a trading strategy.

    This endpoint performs parameter optimization using the specified method:
    - Walk-forward analysis
    - Purged K-fold cross validation
    - Out-of-sample testing
    - Monte Carlo optimization

    Args:
        request: Parameter optimization request
        background_tasks: FastAPI background tasks
        service: Parameter optimization service

    Returns:
        Optimization result with optimized parameters

    Raises:
        HTTPException: If optimization fails
    """
    try:
        result = await service.optimize_parameters(request)

        # Store result in background for persistence
        background_tasks.add_task(
            _store_optimization_result, service, request.strategy_name, result
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/out-of-sample-test", response_model=OutOfSampleResult)
async def perform_out_of_sample_test(
    request: OutOfSampleTestRequest,
    service: ParameterOptimizationService = Depends(get_optimization_service),
):
    """
    Perform out-of-sample testing for a strategy.

    This endpoint tests strategy performance on unseen data to validate
    parameter optimization results and detect overfitting.

    Args:
        request: Out-of-sample test request
        service: Parameter optimization service

    Returns:
        Out-of-sample test results

    Raises:
        HTTPException: If test fails
    """
    try:
        result = await service.perform_out_of_sample_test(request)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/artifacts", response_model=List[OptimizationArtifact])
async def get_optimization_artifacts(
    strategy_name: Optional[str] = None,
    service: ParameterOptimizationService = Depends(get_optimization_service),
):
    """
    Get optimization artifacts.

    Args:
        strategy_name: Optional strategy name to filter artifacts
        service: Parameter optimization service

    Returns:
        List of optimization artifacts
    """
    try:
        artifacts = await service.get_optimization_artifacts(strategy_name)
        return artifacts

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/artifacts/{artifact_id}", response_model=OptimizationArtifact)
async def get_optimization_artifact(
    artifact_id: str,
    service: ParameterOptimizationService = Depends(get_optimization_service),
):
    """
    Get a specific optimization artifact.

    Args:
        artifact_id: Artifact identifier
        service: Parameter optimization service

    Returns:
        Optimization artifact

    Raises:
        HTTPException: If artifact not found
    """
    try:
        artifacts = await service.get_optimization_artifacts()
        artifact = next((a for a in artifacts if a.artifact_id == artifact_id), None)

        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        return artifact

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/summary", response_model=OptimizationSummary)
async def get_optimization_summary(
    service: ParameterOptimizationService = Depends(get_optimization_service),
):
    """
    Get optimization summary.

    Args:
        service: Parameter optimization service

    Returns:
        Optimization summary
    """
    try:
        summary = await service.get_optimization_summary()
        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/artifacts/{artifact_id}/metrics", response_model=OptimizationMetrics)
async def get_optimization_metrics(
    artifact_id: str,
    service: ParameterOptimizationService = Depends(get_optimization_service),
):
    """
    Get optimization metrics for an artifact.

    Args:
        artifact_id: Artifact identifier
        service: Parameter optimization service

    Returns:
        Optimization metrics

    Raises:
        HTTPException: If artifact not found
    """
    try:
        artifacts = await service.get_optimization_artifacts()
        artifact = next((a for a in artifacts if a.artifact_id == artifact_id), None)

        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")

        metrics = await service.calculate_optimization_metrics(artifact)
        return metrics

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/methods", response_model=List[str])
async def get_optimization_methods():
    """
    Get available optimization methods.

    Returns:
        List of available optimization methods
    """
    return [method.value for method in OptimizationMethod]


@router.get("/parameter-types", response_model=List[str])
async def get_parameter_types():
    """
    Get available parameter types.

    Returns:
        List of available parameter types
    """
    return [param_type.value for param_type in ParameterType]


@router.post("/validate-config")
async def validate_optimization_config(
    config: OptimizationConfig,
    service: ParameterOptimizationService = Depends(get_optimization_service),
):
    """
    Validate optimization configuration.

    Args:
        config: Optimization configuration to validate
        service: Parameter optimization service

    Returns:
        Validation result
    """
    try:
        # Create a mock request to validate the config
        mock_request = ParameterOptimizationRequest(
            strategy_name="test_strategy",
            parameters=[
                OptimizationParameter(
                    name="test_param",
                    current_value=0.5,
                    constraints=ParameterConstraint(
                        min_value=0.0,
                        max_value=1.0,
                        parameter_type=ParameterType.THRESHOLD,
                    ),
                )
            ],
            optimization_config=config,
            data_start_date=date(2020, 1, 1),
            data_end_date=date(2023, 12, 31),
        )

        await service._validate_optimization_request(mock_request)

        return JSONResponse(
            status_code=200,
            content={"message": "Configuration is valid", "valid": True},
        )

    except ValueError as e:
        return JSONResponse(status_code=400, content={"message": str(e), "valid": False})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Unexpected error: {str(e)}", "valid": False},
        )


@router.get("/strategies/{strategy_name}/best-parameters")
async def get_best_parameters(
    strategy_name: str,
    service: ParameterOptimizationService = Depends(get_optimization_service),
):
    """
    Get best parameters for a strategy.

    Args:
        strategy_name: Name of the strategy
        service: Parameter optimization service

    Returns:
        Best parameters for the strategy

    Raises:
        HTTPException: If no optimization found for strategy
    """
    try:
        artifacts = await service.get_optimization_artifacts(strategy_name)

        if not artifacts:
            raise HTTPException(
                status_code=404,
                detail=f"No optimization artifacts found for strategy: {strategy_name}",
            )

        # Get the most recent artifact
        latest_artifact = artifacts[0]

        return {
            "strategy_name": strategy_name,
            "best_parameters": latest_artifact.optimization_result.optimized_parameters,
            "best_score": latest_artifact.optimization_result.best_score,
            "optimization_date": latest_artifact.optimization_date,
            "method_used": latest_artifact.optimization_result.method_used,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.delete("/artifacts/{artifact_id}")
async def delete_optimization_artifact(
    artifact_id: str,
    service: ParameterOptimizationService = Depends(get_optimization_service),
):
    """
    Delete an optimization artifact.

    Args:
        artifact_id: Artifact identifier
        service: Parameter optimization service

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If artifact not found
    """
    try:
        if artifact_id in service.optimization_artifacts:
            del service.optimization_artifacts[artifact_id]
            service.optimization_summary.artifacts_count = len(service.optimization_artifacts)

            return JSONResponse(
                status_code=200,
                content={"message": f"Artifact {artifact_id} deleted successfully"},
            )
        else:
            raise HTTPException(status_code=404, detail="Artifact not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for optimization service.

    Returns:
        Health status
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "parameter_optimization",
            "timestamp": datetime.now().isoformat(),
        },
    )


# Background task functions
async def _store_optimization_result(
    service: ParameterOptimizationService,
    strategy_name: str,
    result: OptimizationResult,
):
    """Store optimization result in background."""
    try:
        # This would typically store the result in a database
        # For now, it's already stored in the service
        pass
    except Exception as e:
        # Log error but don't raise exception in background task
        logger.error(f"Error storing optimization result: {str(e)}")
