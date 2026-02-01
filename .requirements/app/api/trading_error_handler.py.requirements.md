# trading_error_handler.py

## Purpose
REST API endpoints for unified trading error handling including error processing, circuit breaker management, error statistics, and health monitoring. (TASK-14)

---

## Type Definitions / Data Classes

### ErrorContext (Enum)
- **ORDER_EXECUTION**: Order execution context
- **MARKET_DATA**: Market data context
- **PORTFOLIO_MANAGEMENT**: Portfolio management context
- **RISK_MANAGEMENT**: Risk management context
- **SIGNAL_GENERATION**: Signal generation context
- **API**: API context
- **DATABASE**: Database context
- **EXTERNAL_SERVICE**: External service context

### ErrorCategory (Enum)
- **NETWORK**: Network-related errors
- **TIMEOUT**: Timeout errors
- **VALIDATION**: Validation errors
- **BUSINESS_LOGIC**: Business logic errors
- **SYSTEM**: System errors
- **UNKNOWN**: Unknown errors

### ErrorAction (Enum)
- **RETRY**: Retry the operation
- **SKIP**: Skip and continue
- **CIRCUIT_BREAKER**: Open circuit breaker
- **ALERT**: Send alert
- **LOG_ONLY**: Log only
- **FAIL_FAST**: Fail immediately

### ErrorHandlingRequest (Pydantic BaseModel)
```python
class ErrorHandlingRequest:
    error_message: str               # REQUIRED - error description
    error_type: str                  # REQUIRED - type of error
    context: ErrorContext            # REQUIRED - error context
    operation_id: Optional[str]       # OPTIONAL - operation identifier
    metadata: Optional[Dict[str, Any]] # OPTIONAL - additional metadata
```

### ErrorHandlingResponse (Pydantic BaseModel)
```python
class ErrorHandlingResponse:
    operation_id: str                # REQUIRED - operation identifier
    context: str                     # REQUIRED - error context
    error: Dict[str, Any]            # REQUIRED - error details
    actions_taken: Dict[str, Any]    # REQUIRED - actions taken
    timestamp: str                   # REQUIRED - ISO format timestamp
```

### CircuitBreakerStatus (Pydantic BaseModel)
```python
class CircuitBreakerStatus:
    context: str                     # REQUIRED - context name
    is_open: bool                    # REQUIRED - whether breaker is open
    error_count: int                 # REQUIRED - current error count
    last_error_time: Optional[str]   # OPTIONAL - last error timestamp
```

### ErrorStatistics (Pydantic BaseModel)
```python
class ErrorStatistics:
    error_counts: Dict[str, int]         # REQUIRED - errors by context and category
    circuit_breakers: Dict[str, bool]    # REQUIRED - circuit breaker statuses
    last_error_times: Dict[str, str]     # REQUIRED - last error times
    retry_counts: Dict[str, int]         # REQUIRED - retry counts
    timestamp: str                       # REQUIRED - statistics timestamp
```

### CircuitBreakerResetRequest (Pydantic BaseModel)
```python
class CircuitBreakerResetRequest:
    context: ErrorContext            # REQUIRED - context to reset
```

---

## Function Signatures (Contracts)

### `handle_error_endpoint(request: ErrorHandlingRequest) -> ErrorHandlingResponse`
**Pre:** request has valid error_message, error_type, and context
**Post:** Processes error according to rules and returns response with actions
**Raises:** HTTPException(500) on handling failures
**Retry:** No (error handler determines retry)
**Side Effects:** May open circuit breaker, send alerts, update statistics

### `get_error_statistics_endpoint() -> ErrorStatistics`
**Pre:** None
**Post:** Returns current error statistics and circuit breaker statuses
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_circuit_breaker_status_endpoint() -> List[CircuitBreakerStatus]`
**Pre:** None
**Post:** Returns status of all circuit breakers
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `reset_circuit_breaker_endpoint(request: CircuitBreakerResetRequest) -> Dict`
**Pre:** request.context is valid ErrorContext
**Post:** Resets circuit breaker for context, clears error counts
**Raises:** HTTPException(500) on reset errors
**Retry:** No
**Side Effects:** Closes circuit breaker, resets error count

### `get_error_contexts_endpoint() -> Dict`
**Pre:** None
**Post:** Returns list of available error contexts
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_error_actions_endpoint() -> Dict`
**Pre:** None
**Post:** Returns list of available error actions
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_error_rules_endpoint(context: ErrorContext) -> Dict`
**Pre:** context is valid ErrorContext
**Post:** Returns error handling rules for the context
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `health_check_endpoint() -> Dict`
**Pre:** None
**Post:** Returns health status with circuit breaker information
**Raises:** None (returns error status on failure)
**Retry:** No
**Side Effects:** None (read-only)

---

## Acceptance Criteria
- [ ] All error contexts are valid enum values
- [ ] Error handler applies correct actions based on rules
- [ ] Circuit breakers open after threshold errors
- [ ] Circuit breaker reset clears error counts
- [ ] Statistics track errors by context and category
- [ ] Health check returns degraded status with open breakers
- [ ] All timestamps use ISO format
- [ ] Error responses include operation_id for tracing
- [ ] Context endpoint returns all ErrorContext values
- [ ] Actions endpoint returns all ErrorAction values

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-001 | 28-security-and-secrets.md | No hardcoded credentials | ✅ OK |
| API-002 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - Has logging |
| API-003 | 08-configuration.md | Input validation | ✅ OK - Pydantic validation |
| API-004 | 06-testing.md | Test coverage | ❌ GAP - No test evidence |
| API-005 | 28-security-and-secrets.md | Authentication for reset operations | ❌ GAP - No auth visible |
| API-006 | 07-async-patterns.md | Async operations | ⚠️ PARTIAL - Endpoints are async but service calls sync |
| API-007 | 05-architecture.md | API layer only handles HTTP | ✅ OK - Delegates to service |
| API-008 | 12-logging-observability.md | Error handling with context | ✅ OK - Comprehensive error handling |
| API-009 | 09-logging-observability.md | Circuit breaker logging | ⚠️ PARTIAL - Basic logging |
| API-010 | 04-design-patterns.md | Circuit breaker pattern | ✅ OK - Implemented |

---

## Dependencies
- **External:** fastapi, pydantic, requests
- **Internal:** app.exceptions.trading_exceptions, app.services.trading_error_handler

---

## Required Tests
- **test_trading_error_handler_endpoints.py:**
  - Test handle_error_endpoint processes error correctly
  - Test handle_error_endpoint returns proper response structure
  - Test get_error_statistics_endpoint returns statistics
  - Test get_error_statistics_endpoint tracks error counts
  - Test get_circuit_breaker_status_endpoint returns all breakers
  - Test get_circuit_breaker_status_endpoint shows correct states
  - Test reset_circuit_breaker_endpoint closes breaker
  - Test reset_circuit_breaker_endpoint resets error count
  - Test get_error_contexts_endpoint returns all contexts
  - Test get_error_actions_endpoint returns all actions
  - Test get_error_rules_endpoint returns rules for context
  - Test health_check_endpoint returns healthy status
  - Test health_check_endpoint returns degraded with open breakers
  - Test all endpoints handle errors gracefully

---

## Notes
- Part of TASK-14 (Unificación de Error Handling)
- Centralized error handling for entire trading system
- Circuit breaker pattern for resilience
- Uses trading_error_handler singleton
- MockError class used for demonstration
- No authentication visible for circuit breaker reset
- Health check integrates with circuit breaker status
