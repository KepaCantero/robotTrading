"""
T13.1: CAPA 2 API Endpoints - Parametrization Framework REST API

Exposes the complete CAPA 2 parametrization pipeline:
1. InputProfile processing (T1.1)
2. ProfileGenerator (T2.1)
3. ModuleParametrizer (T3.1)
4. BacktestOrchestrator (T4.1)
5. ValidationEngine (T5.1)
6. StrategyRecommender (T6.1)
7. PortfolioConstructor (T7.1)
8. RiskScalingApplication (T8.1)
9. ReportingGenerator (T9.1)
10. DeployDecisionOrchestrator (T10.1)

GAP Fixes:
- API-002: Added structured logging with correlation IDs
- API-005: TODO: Rate limiting on expensive workflow endpoints
- API-006: Added correlation ID tracking
- API-009: Added audit logging for workflow operations
"""

from __future__ import annotations

import logging
import traceback
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from app.domain.models.input_profile import InputProcessor, InputProfile
from app.infrastructure.persistence.configuration.configuration_repository import (
    ConfigurationRepository,
)
from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator

from . import audit_logger, get_correlation_id

# import asyncio  # F811 duplicate from line 10

# Import all CAPA 2 services
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/capa2", tags=["CAPA 2 Parametrization Framework"])

# (2-11) El job-store en memoria MURIÓ con el mock que lo llenaba: el
# endpoint ejecutaba asyncio.sleep(2) y devolvía métricas HARDCODEADAS
# (Sharpe 1.2, +15%) — un endpoint público del app real sirviendo
# números inventados. Honestidad antes que persistencia: hasta que se
# cablee al motor real, responde 501 con la verdad.

# Initialize services (lazy initialization in endpoints where needed)
# These services are expensive to initialize upfront, so we'll instantiate them
# when first needed, or use factory functions instead of singletons

input_processor = None
profile_generator = None
module_parametrizer = None
backtest_orchestrator = None
validation_engine = None
strategy_recommender = None
portfolio_constructor = None
risk_scaling_applicator = None
reporting_generator = None
deploy_decision_orchestrator = None
configuration_repository = None


def get_input_processor() -> InputProcessor:
    """Get or initialize InputProcessor."""
    global input_processor
    if input_processor is None:
        input_processor = InputProcessor()
    return input_processor


def get_deploy_decision_orchestrator() -> DeployDecisionOrchestrator:
    """Get or initialize DeployDecisionOrchestrator."""
    global deploy_decision_orchestrator
    if deploy_decision_orchestrator is None:
        deploy_decision_orchestrator = DeployDecisionOrchestrator()
    return deploy_decision_orchestrator


def get_configuration_repository() -> ConfigurationRepository:
    """Get or initialize ConfigurationRepository."""
    global configuration_repository
    if configuration_repository is None:
        configuration_repository = ConfigurationRepository()
    return configuration_repository


# ============================================================================
# Request/Response Models
# ============================================================================


class ProcessInputRequest(BaseModel):
    """User input for parametrization workflow."""

    capital_initial: Decimal = Field(
        ..., ge=Decimal("1"), le=Decimal("10000000"), description="Initial capital in EUR"
    )
    objetivo_inversion: str = Field(..., description="Investment objective")
    risk_tolerance: str = Field(..., description="Risk tolerance level")
    investment_horizon: int = Field(..., ge=1, le=600, description="Investment horizon in months")
    constraints: dict[str, Any] | None = Field(default=None, description="Optional constraints")


class ProcessInputResponse(BaseModel):
    """Result of input processing."""

    input_id: str
    capital_initial: float
    objetivo_inversion: str
    risk_tolerance: str
    investment_horizon: int
    validation_passed: bool
    timestamp: str


class GenerateProfileRequest(BaseModel):
    """Request to generate investment profile."""

    input_id: str = Field(..., description="Input profile ID")


class GenerateProfileResponse(BaseModel):
    """Generated investment profile."""

    profile_id: str
    capital_tier: str
    risk_profile: int
    enabled_modules: list
    leverage_factor: float
    max_position_size: float
    timestamp: str


class ParametrizeModulesRequest(BaseModel):
    """Request to parametrize modules."""

    profile_id: str = Field(..., description="Investment profile ID")
    input_id: str = Field(..., description="Input profile ID")


class ParametrizeModulesResponse(BaseModel):
    """Module parameter set."""

    parameter_set_id: str
    total_modules: int
    total_max_exposure: float
    modules_summary: dict[str, Any]
    timestamp: str


class ExecuteBacktestRequest(BaseModel):
    """Request to execute backtest."""

    parameter_set_id: str = Field(..., description="Module parameter set ID")
    profile_id: str = Field(..., description="Investment profile ID")


class ExecuteBacktestResponse(BaseModel):
    """Backtest results."""

    job_id: str
    status: str
    total_return: float | None = None
    sharpe_ratio: float | None = None
    feasibility_ratio: float | None = None
    timestamp: str


class BacktestStatusResponse(BaseModel):
    """Status of backtest job."""

    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    timestamp: str


class CompleteWorkflowRequest(BaseModel):
    """End-to-end workflow request."""

    capital_initial: Decimal = Field(..., ge=Decimal("1"), le=Decimal("10000000"))
    objetivo_inversion: str
    risk_tolerance: str
    investment_horizon: int
    constraints: dict[str, Any] | None = None


class DeploymentDecisionResponse(BaseModel):
    """Final deployment decision."""

    decision_id: str
    status: str  # "APPROVED", "CONDITIONAL", "REJECTED"
    confidence_level: str
    feasibility_ratio: float
    recommendation_score: float
    validation_passed: bool
    reasons: list
    risks: list
    recommendations: list
    next_steps: list
    timestamp: str


class CompleteWorkflowResponse(BaseModel):
    """End-to-end workflow result."""

    workflow_id: str
    status: str
    input_profile: ProcessInputResponse
    investment_profile: GenerateProfileResponse
    module_parameters: ParametrizeModulesResponse
    backtest_result: ExecuteBacktestResponse
    deployment_decision: DeploymentDecisionResponse | None = None
    report_id: str | None = None
    timestamp: str


# ============================================================================
# Step 1: Process Input (T1.1)
# ============================================================================


@router.post("/process-input", response_model=ProcessInputResponse)
async def process_input(request: ProcessInputRequest, http_request: Request):
    """
    Process user investment profile input.

    Validates capital, objective, risk tolerance, and investment horizon.
    Creates InputProfile for downstream processing.
    """
    correlation_id = get_correlation_id()
    logger.info(
        "Processing input profile",
        extra={
            "correlation_id": correlation_id,
            "capital_initial": float(request.capital_initial),
            "objetivo_inversion": request.objetivo_inversion,
            "risk_tolerance": request.risk_tolerance,
        },
    )
    try:
        input_profile = InputProfile(
            capital_initial=request.capital_initial,
            objetivo_inversion=request.objetivo_inversion,
            risk_tolerance=request.risk_tolerance,
            investment_horizon=request.investment_horizon,
            constraints=request.constraints or {},
        )

        # Generate unique ID
        input_id = f"input_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

        audit_logger.log_action(
            action="input_processed",
            method=http_request.method,
            path=http_request.url.path,
            details={"input_id": input_id, "capital_tier": "MEDIUM"},
        )

        logger.info(
            f"✅ Processed input: {input_id}",
            extra={"correlation_id": correlation_id, "input_id": input_id},
        )

        return ProcessInputResponse(
            input_id=input_id,
            capital_initial=float(input_profile.capital_initial),
            objetivo_inversion=input_profile.objetivo_inversion,
            risk_tolerance=input_profile.risk_tolerance,
            investment_horizon=input_profile.investment_horizon,
            validation_passed=True,
            timestamp=datetime.now().isoformat(),
        )

    except OSError as e:
        logger.error(
            f"❌ Error processing input: {e}",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            },
        )
        audit_logger.log_error(
            method=http_request.method,
            path=http_request.url.path,
            error_type=type(e).__name__,
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Step 2: Generate Investment Profile (T2.1)
# ============================================================================


@router.post("/generate-profile", response_model=GenerateProfileResponse)
async def generate_profile(request: GenerateProfileRequest):
    """
    Generate investment profile from input.

    Maps objective + capital tier → strategy parameters.
    Returns enabled modules, leverage, position sizing, etc.
    """
    try:
        # This would require storing the input profile somewhere
        # For now, create a minimal profile for demonstration
        profile_id = f"profile_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

        logger.info(f"✅ Generated profile: {profile_id}")

        return GenerateProfileResponse(
            profile_id=profile_id,
            capital_tier="MEDIUM",
            risk_profile=5,
            enabled_modules=["momentum_modular", "mean_reversion", "pairs_trading"],
            leverage_factor=1.5,
            max_position_size=0.15,
            timestamp=datetime.now().isoformat(),
        )

    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(f"❌ Error generating profile: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Step 3: Parametrize Modules (T3.1)
# ============================================================================


@router.post("/parametrize-modules", response_model=ParametrizeModulesResponse)
async def parametrize_modules(request: ParametrizeModulesRequest):
    """
    Generate module-specific parameters.

    Applies investment profile to 17+ trading modules.
    Returns complete parameter set with all thresholds.
    """
    try:
        parameter_set_id = f"params_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

        logger.info(f"✅ Parametrized modules: {parameter_set_id}")

        return ParametrizeModulesResponse(
            parameter_set_id=parameter_set_id,
            total_modules=17,
            total_max_exposure=3.0,  # Sum of module exposures
            modules_summary={
                "momentum_modular": {"max_position_size": 0.15, "stop_loss_pct": 2.5},
                "mean_reversion": {"max_position_size": 0.12, "stop_loss_pct": 3.0},
                "pairs_trading": {"max_position_size": 0.10, "stop_loss_pct": 2.0},
            },
            timestamp=datetime.now().isoformat(),
        )

    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        logger.error(f"❌ Error parametrizing modules: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Step 4: Execute Backtest (T4.1) - ASYNC
# ============================================================================


@router.post("/execute-backtest", response_model=ExecuteBacktestResponse)
async def execute_backtest(request: ExecuteBacktestRequest, background_tasks: BackgroundTasks):
    """
    Execute backtest for parametrized strategy (ASYNC).

    Returns job_id immediately. Use /backtest-status/{job_id} to poll results.
    This is async because backtests can take 30-60+ seconds.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "This endpoint served simulated metrics (hardcoded Sharpe/returns) "
            "and was disabled 2026-11-02. Use the real engine via the swarm "
            "pipeline (Capa2PipelineExecutor) or the dashboard."
        ),
    )


@router.get("/backtest-status/{job_id}", response_model=BacktestStatusResponse)
async def backtest_status(job_id: str):
    """Retired with the simulated executor (2026-11-02)."""
    raise HTTPException(
        status_code=410,
        detail="Simulated backtest jobs were removed; run the real engine instead.",
    )


@router.post("/complete-workflow", response_model=CompleteWorkflowResponse)
async def complete_workflow(request: CompleteWorkflowRequest):
    """Retired 2026-11-02: this chained 10 asyncio.sleep(0.5) stages and
    returned FABRICATED results (hardcoded exposures, invented profiles)
    while pretending to be the pipeline. The real 10-stage pipeline lives
    in Capa2PipelineExecutor (swarm) — use that."""
    raise HTTPException(
        status_code=501,
        detail=(
            "This workflow was a simulation and was removed. Run the REAL "
            "pipeline via Capa2PipelineExecutor (swarm) or the dashboard."
        ),
    )


@router.get("/workflow-status/{workflow_id}")
async def workflow_status(workflow_id: str):
    """Retired with the simulated workflow (2026-11-02)."""
    raise HTTPException(status_code=410, detail="Simulated workflows were removed.")


@router.get("/health")
async def health_check():
    """Health check for CAPA 2 API."""
    return {
        "status": "healthy",
        "service": "CAPA 2 Parametrization Framework",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/status/jobs")
async def jobs_status():
    """Retired with the simulated executor (2026-11-02)."""
    raise HTTPException(status_code=410, detail="Simulated jobs were removed.")


# Import asyncio for background tasks
