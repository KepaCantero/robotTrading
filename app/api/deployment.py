"""
Deployment decision API endpoints.

Provides REST API for validating strategies, making deployment decisions,
and accessing deployment status information.

GAP Fixes:
- API-002: Added structured logging with correlation IDs
- API-005: FIXED - Added security decorators (rate_limit, require_auth, audit_log)
- API-006: Added correlation ID tracking
- API-009: Added audit logging
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException, Query, Request
from requests.exceptions import HTTPError, RequestException

from app.models.deployment import DeploymentInput
from app.services.deploy_decision_orchestrator import get_deploy_orchestrator
from app.services.external_integrations.health_check_manager import get_health_check_manager

from . import audit_logger, get_correlation_id
from .security import audit_log, rate_limit, require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deployment", tags=["deployment"])


@router.post("/validate-strategy")
@rate_limit(max_requests=20, window_seconds=60)
@require_auth(roles=["admin", "trader"])
@audit_log("strategy_validated", log_args=True)
async def validate_strategy(
    deployment_input: DeploymentInput,
    http_request: Request,
) -> Dict:
    """
    Validate a strategy and make deployment decision.

    Args:
        deployment_input: Complete deployment input with strategy details
        http_request: FastAPI Request object

    Returns:
        Deployment decision with approval status and rationale
    """
    correlation_id = get_correlation_id()
    logger.info(
        "Validating strategy for deployment",
        extra={
            "correlation_id": correlation_id,
            "strategy_name": deployment_input.strategy_name,
            "profile_id": str(deployment_input.profile_id),
        },
    )
    try:
        orchestrator = get_deploy_orchestrator()
        decision = await asyncio.wait_for(
            orchestrator.make_decision(deployment_input),
            timeout=60.0,  # API-010: Add timeout configuration
        )

        audit_logger.log_action(
            action="strategy_validated",
            method=http_request.method,
            path=http_request.url.path,
            details={
                "strategy_name": deployment_input.strategy_name,
                "decision_id": decision.decision_id,
                "status": decision.status,
            },
        )

        return {
            "success": decision.success,
            "decision_id": decision.decision_id,
            "profile_id": decision.profile_id,
            "strategy_name": decision.strategy_name,
            "status": decision.status,
            "confidence_level": decision.confidence_level,
            "overall_score": float(decision.overall_score),
            "scores": {
                "feasibility": float(decision.feasibility_score),
                "validation": float(decision.validation_score),
                "recommendation": float(decision.recommendation_score),
                "risk": float(decision.risk_score),
                "capacity_fade": float(decision.capacity_fade_score),
            },
            "rationale": {
                "feasibility_assessment": decision.rationale.feasibility_assessment,
                "validation_assessment": decision.rationale.validation_assessment,
                "recommendation_assessment": decision.rationale.recommendation_assessment,
                "risk_assessment": decision.rationale.risk_assessment,
                "overall_assessment": decision.rationale.overall_assessment,
                "critical_factors": decision.rationale.critical_factors,
                "improvement_areas": decision.rationale.improvement_areas,
            },
            "recommendation_text": decision.recommendation_text,
            "next_steps": decision.next_steps,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout validating strategy",
            extra={
                "correlation_id": correlation_id,
                "strategy_name": deployment_input.strategy_name,
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            },
        )
        audit_logger.log_error(
            method=http_request.method,
            path=http_request.url.path,
            error_type="TimeoutError",
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        raise HTTPException(status_code=504, detail=f"Validation timeout: {str(e)}")
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(
            "Error validating strategy",
            extra={
                "correlation_id": correlation_id,
                "strategy_name": deployment_input.strategy_name,
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
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/decision/{decision_id}")
async def get_deployment_decision(decision_id: str) -> Dict:
    """
    Retrieve a previous deployment decision by ID.

    Args:
        decision_id: ID of the deployment decision

    Returns:
        Deployment decision details
    """
    try:
        orchestrator = get_deploy_orchestrator()

        # Search decision history
        for decision in orchestrator.decision_history:
            if decision.decision_id == decision_id:
                return {
                    "success": decision.success,
                    "decision_id": decision.decision_id,
                    "profile_id": decision.profile_id,
                    "strategy_name": decision.strategy_name,
                    "status": decision.status,
                    "confidence_level": decision.confidence_level,
                    "overall_score": float(decision.overall_score),
                    "created_at": datetime.utcnow().isoformat(),
                }

        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"❌ Error retrieving decision: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")


@router.get("/decisions")
async def list_deployment_decisions(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Dict:
    """
    List recent deployment decisions.

    Args:
        limit: Maximum number of decisions to return
        offset: Number of decisions to skip

    Returns:
        List of recent decisions
    """
    try:
        orchestrator = get_deploy_orchestrator()

        # Get decisions from history
        history = orchestrator.decision_history
        total = len(history)
        decisions = history[offset : offset + limit]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "decisions": [
                {
                    "decision_id": d.decision_id,
                    "profile_id": d.profile_id,
                    "strategy_name": d.strategy_name,
                    "status": d.status,
                    "overall_score": float(d.overall_score),
                }
                for d in decisions
            ],
        }

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"❌ Error listing decisions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Listing failed: {str(e)}")


@router.get("/health")
async def health_check() -> Dict:
    """
    Check health of deployment service and external dependencies.

    Returns:
        Health status of service and dependencies
    """
    try:
        health_manager = get_health_check_manager()
        all_health = health_manager.get_all_health_status()

        # Determine overall health
        unhealthy_count = len(health_manager.get_unhealthy_services())
        degraded_count = len(health_manager.get_degraded_services())

        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                name: {
                    "status": health.status,
                    "last_check": health.last_check.isoformat(),
                    "response_time_ms": health.response_time_ms,
                    "consecutive_failures": health.consecutive_failures,
                }
                for name, health in all_health.items()
            },
            "summary": {
                "total_services": len(all_health),
                "healthy_services": len([s for s in all_health.values() if s.status == "healthy"]),
                "degraded_services": degraded_count,
                "unhealthy_services": unhealthy_count,
            },
        }

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"❌ Error checking health: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/status")
async def deployment_status() -> Dict:
    """
    Get overall status of deployment system.

    Returns:
        System status and metrics
    """
    try:
        orchestrator = get_deploy_orchestrator()
        health_manager = get_health_check_manager()

        decision_count = len(orchestrator.decision_history)
        approved_count = sum(1 for d in orchestrator.decision_history if d.status == "APPROVED")
        rejected_count = sum(1 for d in orchestrator.decision_history if d.status == "REJECTED")
        conditional_count = sum(
            1 for d in orchestrator.decision_history if d.status == "CONDITIONAL"
        )

        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "orchestrator": {
                "initialized": orchestrator is not None,
                "decisions_made": decision_count,
                "decisions_approved": approved_count,
                "decisions_conditional": conditional_count,
                "decisions_rejected": rejected_count,
            },
            "health": {
                "overall": health_manager.get_all_health_status(),
                "unhealthy_services": health_manager.get_unhealthy_services(),
                "degraded_services": health_manager.get_degraded_services(),
            },
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"❌ Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")
