# deployment.py

## Purpose
REST API for validating strategies, making deployment decisions, and accessing deployment status information.

---

## Type Definitions / Data Classes

### DeploymentInput (from app.models.deployment)
```python
class DeploymentInput:
    # Contains strategy details, backtest results, and validation criteria
    # Exact fields defined in app.models.deployment
```

### Deployment Decision (from service)
```python
class DeploymentDecision:
    decision_id: str              # REQUIRED - unique decision identifier
    profile_id: str               # REQUIRED - profile ID
    strategy_name: str            # REQUIRED - strategy name
    status: str                   # REQUIRED - "APPROVED", "CONDITIONAL", "REJECTED"
    confidence_level: str         # REQUIRED - confidence assessment
    overall_score: Decimal        # REQUIRED - composite score
    feasibility_score: Decimal    # REQUIRED - feasibility metric
    validation_score: Decimal     # REQUIRED - validation metric
    recommendation_score: Decimal # REQUIRED - recommendation score
    risk_score: Decimal           # REQUIRED - risk metric
    capacity_fade_score: Decimal  # REQUIRED - capacity fade metric
    rationale: Rationale          # REQUIRED - decision rationale
    recommendation_text: str      # REQUIRED - human-readable recommendation
    next_steps: list[str]         # REQUIRED - follow-up actions
```

---

## Function Signatures (Contracts)

### `validate_strategy(deployment_input: DeploymentInput) -> Dict`
**Pre:** deployment_input contains valid strategy data and backtest results
**Post:** Returns deployment decision with scores, rationale, and recommendation
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** May store decision in orchestrator history

### `get_deployment_decision(decision_id: str) -> Dict`
**Pre:** decision_id exists in orchestrator history
**Post:** Returns decision details
**Raises:** HTTPException(404) if decision not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `list_deployment_decisions(limit: int, offset: int) -> Dict`
**Pre:** limit is 1-100, offset is >= 0
**Post:** Returns paginated list of decisions
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `health_check() -> Dict`
**Pre:** Health check manager is initialized
**Post:** Returns health status of service and external dependencies
**Raises:** None (returns error status on failure)
**Retry:** No
**Side Effects:** Checks all registered services

### `deployment_status() -> Dict`
**Pre:** Orchestrator and health manager are initialized
**Post:** Returns system status with decision counts and health
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

---

## Acceptance Criteria
- [ ] validate_strategy returns decision with all score components
- [ ] Decision status is one of: APPROVED, CONDITIONAL, REJECTED
- [ ] list_deployment_decisions respects limit and offset parameters
- [ ] health_check returns degraded status if any service is unhealthy
- [ ] health_check returns unhealthy status if any service has consecutive failures
- [ ] deployment_status counts decisions by status (approved, rejected, conditional)
- [ ] All timestamps use UTC
- [ ] All responses include timestamp field
- [ ] Decision not found returns 404 status

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-001 | 28-security-and-secrets.md | No hardcoded credentials | ✅ OK |
| API-002 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - Has error logging |
| API-003 | 05-architecture.md | API layer only handles HTTP | ✅ OK - Delegates to services |
| API-004 | 06-testing.md | Test coverage | ❌ GAP - No test evidence |
| API-005 | 12-logging-observability.md | Audit logging for deployment decisions | ❌ GAP - No audit logging |
| API-006 | 28-security-and-secrets.md | Authentication for deployment operations | ✅ FIXED - 2026-02-03 - AuthMiddleware added |
| API-007 | 08-configuration.md | Input validation | ⚠️ PARTIAL - Query params validated |
| API-008 | 09-logging-observability.md | Error handling with context | ✅ OK - Error logging present |
| API-009 | 07-async-patterns.md | Async operations | ✅ OK - Endpoints are async |
| API-010 | 12-logging-observability.md | Health check implementation | ✅ OK - Comprehensive health check |

---

## Dependencies
- **External:** fastapi, requests
- **Internal:** app.models.deployment, app.services.deploy_decision_orchestrator, app.services.external_integrations.health_check_manager

---

## Required Tests
- **test_deployment_endpoints.py:**
  - Test validate_strategy with valid deployment input
  - Test validate_strategy returns decision with all fields
  - Test get_deployment_decision returns 404 for non-existent ID
  - Test list_deployment_decisions with various limit/offset values
  - Test health_check returns healthy when all services OK
  - Test health_check returns degraded with degraded services
  - Test health_check returns unhealthy with failed services
  - Test deployment_status counts decisions correctly
  - Test all endpoints handle service errors gracefully
  - Test pagination works correctly with limit/offset

---

## Notes
- Uses factory functions (get_deploy_orchestrator, get_health_check_manager) for service access
- Health check integrates with external service monitoring
- Decision history stored in orchestrator (in-memory, not persistent)
- No rate limiting visible on deployment validation
- Consider adding audit trail for deployment decisions
