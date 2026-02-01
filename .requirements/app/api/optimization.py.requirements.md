# optimization.py

## Purpose
FastAPI endpoints for parameter optimization and overfitting prevention including walk-forward analysis, out-of-sample testing, and parameter optimization.

---

## Type Definitions / Data Classes

### OptimizationMethod (Enum)
- **WALK_FORWARD**: Walk-forward analysis
- **PURGED_K_FOLD**: Purged K-fold cross validation
- **OUT_OF_SAMPLE**: Out-of-sample testing
- **MONTE_CARLO**: Monte Carlo optimization

### ParameterType (Enum)
- **THRESHOLD**: Threshold parameter
- **PERIOD**: Time period parameter
- **RATIO**: Ratio parameter
- **WEIGHT**: Weight parameter
- **BOOLEAN**: Boolean parameter
- **INTEGER**: Integer parameter

### OptimizationParameter (Pydantic model)
```python
class OptimizationParameter:
    name: str                          # REQUIRED - parameter name
    current_value: float               # REQUIRED - current value
    constraints: ParameterConstraint   # REQUIRED - value constraints
```

### ParameterConstraint (Pydantic model)
```python
class ParameterConstraint:
    min_value: float                   # REQUIRED - minimum allowed value
    max_value: float                   # REQUIRED - maximum allowed value
    parameter_type: ParameterType      # REQUIRED - parameter type
```

### OptimizationConfig (Pydantic model)
```python
class OptimizationConfig:
    method: OptimizationMethod         # REQUIRED - optimization method
    validation_fraction: float         # REQUIRED - fraction for validation (0-1)
    purged_cross_validation_folds: int # OPTIONAL - number of CV folds
    purged_cross_validation_purge: int # OPTIONAL - purge period
    monte_carlo_runs: int              # OPTIONAL - number of MC runs
    custom_split_date: Optional[date]  # OPTIONAL - custom split date
```

### ParameterOptimizationRequest (Pydantic model)
```python
class ParameterOptimizationRequest:
    strategy_name: str                        # REQUIRED
    parameters: List[OptimizationParameter]   # REQUIRED - parameters to optimize
    optimization_config: OptimizationConfig   # REQUIRED
    data_start_date: date                     # REQUIRED
    data_end_date: date                       # REQUIRED
```

### OutOfSampleTestRequest (Pydantic model)
```python
class OutOfSampleTestRequest:
    strategy_name: str          # REQUIRED
    optimized_parameters: Dict  # REQUIRED - optimized parameter values
    test_start_date: date       # REQUIRED
    test_end_date: date         # REQUIRED
```

### OptimizationArtifact (Service model)
```python
class OptimizationArtifact:
    artifact_id: str                    # REQUIRED - unique identifier
    strategy_name: str                  # REQUIRED
    optimization_date: datetime          # REQUIRED
    optimization_result: OptimizationResult  # REQUIRED
```

---

## Function Signatures (Contracts)

### `optimize_parameters(request: ParameterOptimizationRequest, background_tasks: BackgroundTasks, service: ParameterOptimizationService) -> OptimizationResult`
**Pre:** request contains valid parameters, config, and date range
**Post:** Returns optimization result with optimized parameters, stores result in background
**Raises:** HTTPException(400) on validation errors, HTTPException(500) on runtime errors
**Retry:** No
**Side Effects:** Stores optimization result in background task

### `perform_out_of_sample_test(request: OutOfSampleTestRequest, service: ParameterOptimizationService) -> OutOfSampleResult`
**Pre:** request contains valid parameters and date range
**Post:** Returns out-of-sample test results
**Raises:** HTTPException(400) on validation errors, HTTPException(500) on runtime errors
**Retry:** No
**Side Effects:** None (read-only analysis)

### `get_optimization_artifacts(strategy_name: Optional[str], service: ParameterOptimizationService) -> List[OptimizationArtifact]`
**Pre:** None
**Post:** Returns all artifacts or filtered by strategy_name
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_optimization_artifact(artifact_id: str, service: ParameterOptimizationService) -> OptimizationArtifact`
**Pre:** artifact_id exists
**Post:** Returns specific optimization artifact
**Raises:** HTTPException(404) if not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_optimization_summary(service: ParameterOptimizationService) -> OptimizationSummary`
**Pre:** None
**Post:** Returns summary of all optimizations
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_optimization_metrics(artifact_id: str, service: ParameterOptimizationService) -> OptimizationMetrics`
**Pre:** artifact_id exists
**Post:** Returns calculated metrics for the optimization
**Raises:** HTTPException(404) if not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_optimization_methods() -> List[str]`
**Pre:** None
**Post:** Returns list of available optimization methods
**Raises:** None
**Retry:** No
**Side Effects:** None

### `get_parameter_types() -> List[str]`
**Pre:** None
**Post:** Returns list of available parameter types
**Raises:** None
**Retry:** No
**Side Effects:** None

### `validate_optimization_config(config: OptimizationConfig, service: ParameterOptimizationService) -> JSONResponse`
**Pre:** config contains valid optimization configuration
**Post:** Returns validation result (200 or 400)
**Raises:** None (returns JSON response with validation status)
**Retry:** No
**Side Effects:** None

### `get_best_parameters(strategy_name: str, service: ParameterOptimizationService) -> Dict`
**Pre:** strategy_name has at least one optimization artifact
**Post:** Returns best parameters for the strategy
**Raises:** HTTPException(404) if no artifacts found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `delete_optimization_artifact(artifact_id: str, service: ParameterOptimizationService) -> JSONResponse`
**Pre:** artifact_id exists in service storage
**Post:** Deletes artifact and returns confirmation
**Raises:** HTTPException(404) if not found, HTTPException(500) on database errors
**Retry:** No
**Side Effects:** Removes artifact from service storage

### `health_check() -> JSONResponse`
**Pre:** None
**Post:** Returns health status
**Raises:** None
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All optimization methods are valid enum values
- [ ] Date ranges are validated (start_date < end_date)
- [ ] validation_fraction is between 0 and 1
- [ ] Artifact IDs are unique and traceable
- [ ] Background task for storing results completes successfully
- [ ] Out-of-sample testing uses unseen data
- [ ] Configuration validation catches invalid configs
- [ ] Delete operation removes artifact and updates summary count
- [ ] All responses include timestamp

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-001 | 28-security-and-secrets.md | No hardcoded credentials | ✅ OK |
| API-002 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - Has logging in background task |
| API-003 | 08-configuration.md | Input validation | ✅ OK - Good validation |
| API-004 | 06-testing.md | Test coverage | ❌ GAP - No test evidence |
| API-005 | 28-security-and-secrets.md | Authentication for write operations | ❌ GAP - No auth visible |
| API-006 | 07-async-patterns.md | Async operations | ✅ OK - All endpoints async |
| API-007 | 05-architecture.md | API layer only handles HTTP | ✅ OK - Delegates to service |
| API-008 | 12-logging-observability.md | Error handling | ⚠️ PARTIAL - Background task error logging |
| API-009 | 09-logging-observability.md | Audit logging for deletions | ❌ GAP - No audit logging |
| API-010 | 13-async-patterns.md | Background task error handling | ✅ OK - Logs errors in background |

---

## Dependencies
- **External:** fastapi, sqlalchemy
- **Internal:** app.models.optimization, app.services.parameter_optimization_service, app.services.cost_analysis_service

---

## Required Tests
- **test_optimization_endpoints.py:**
  - Test optimize_parameters with valid request
  - Test optimize_parameters handles background task errors
  - Test perform_out_of_sample_test returns valid results
  - Test get_optimization_artifacts filters by strategy_name
  - Test get_optimization_artifact returns 404 for non-existent ID
  - Test get_optimization_metrics calculates metrics correctly
  - Test validate_optimization_config catches invalid configs
  - Test get_best_parameters returns most recent optimization
  - Test delete_optimization_artifact removes artifact
  - Test delete_optimization_artifact updates summary count
  - Test all endpoints handle database errors appropriately

---

## Notes
- Uses SQLAlchemy for potential database operations
- Background task for storing optimization results
- In-memory storage for artifacts (service.optimization_artifacts)
- CostAnalysisService injected as dependency
- Consider persistent storage for artifacts in production
