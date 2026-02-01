# strategies.py

## Purpose
REST API endpoints for multi-strategy management system including strategy loading, activation, metrics tracking, and execution engine control. (TASK-31)

---

## Type Definitions / Data Classes

### StrategyConfigRequest (Pydantic BaseModel)
```python
class StrategyConfigRequest:
    config: Dict[str, Any]    # REQUIRED - strategy configuration parameters
```

### StrategyLoadRequest (Pydantic BaseModel)
```python
class StrategyLoadRequest:
    name: str                 # REQUIRED - strategy name
    config: Dict[str, Any]    # REQUIRED - strategy configuration
```

### StrategyActivateRequest (Pydantic BaseModel)
```python
class StrategyActivateRequest:
    name: str                 # REQUIRED - strategy name to activate
```

### StrategyUpdateRequest (Pydantic BaseModel)
```python
class StrategyUpdateRequest:
    parameters: Dict[str, Any]  # REQUIRED - parameters to update
```

### StrategyResponse (Pydantic BaseModel)
```python
class StrategyResponse:
    name: str                      # REQUIRED - strategy name
    is_active: bool                # REQUIRED - whether strategy is active
    is_currently_active: bool      # REQUIRED - whether currently selected
    version: str                   # REQUIRED - strategy version
    description: str               # REQUIRED - strategy description
    created_at: str                # REQUIRED - ISO creation timestamp
    parameters: Dict[str, Any]     # REQUIRED - strategy parameters
```

### StrategyMetricsResponse (Pydantic BaseModel)
```python
class StrategyMetricsResponse:
    strategy: str              # REQUIRED - strategy name
    signals_generated: int     # REQUIRED - total signals generated
    signals_executed: int      # REQUIRED - signals executed
    signals_rejected: int      # REQUIRED - signals rejected
    execution_rate: float      # REQUIRED - execution rate (%)
    rejection_rate: float      # REQUIRED - rejection rate (%)
    error_count: int           # REQUIRED - total errors
    error_rate: float          # REQUIRED - error rate (%)
    total_logs: int            # REQUIRED - total log entries
    first_log: Optional[str]    # OPTIONAL - first log timestamp
    last_log: Optional[str]     # OPTIONAL - last log timestamp
```

### ExecutionStatsResponse (Pydantic BaseModel)
```python
class ExecutionStatsResponse:
    is_running: bool                # REQUIRED - engine running status
    cycle_count: int                # REQUIRED - execution cycles
    total_signals_generated: int    # REQUIRED - total signals
    total_signals_executed: int     # REQUIRED - total executed
    execution_rate: float           # REQUIRED - execution rate
    created_at: str                 # REQUIRED - engine creation time
    active_strategy: Optional[str]  # OPTIONAL - active strategy name
```

---

## Function Signatures (Contracts)

### `get_strategies_overview(registry: StrategyRegistry) -> Dict[str, Any]`
**Pre:** Registry is initialized
**Post:** Returns overview of all strategies with status
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_available_strategies(registry: StrategyRegistry) -> List[str]`
**Pre:** Registry is initialized
**Post:** Returns list of available strategy names
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_loaded_strategies(registry: StrategyRegistry) -> List[str]`
**Pre:** Registry is initialized
**Post:** Returns list of loaded strategy names
**Raises:** HTTPException(500) on service errors
**Retry:** No
**Side Effects:** None (read-only)

### `load_strategy(request: StrategyLoadRequest, registry: StrategyRegistry, logger_instance: StrategyLogger) -> StrategyResponse`
**Pre:** request.name is valid strategy name, request.config is valid
**Post:** Loads strategy and returns strategy details
**Raises:** HTTPException(400) on load failure, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Adds strategy to registry, logs load event

### `activate_strategy(request: StrategyActivateRequest, registry: StrategyRegistry, logger_instance: StrategyLogger) -> Dict[str, str]`
**Pre:** request.name is loaded strategy name
**Post:** Activates strategy as active
**Raises:** HTTPException(400) on invalid strategy, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Sets active strategy in registry, logs activation

### `deactivate_strategy(registry: StrategyRegistry, logger_instance: StrategyLogger) -> Dict[str, str]`
**Pre:** There is an active strategy
**Post:** Deactivates currently active strategy
**Raises:** HTTPException(400) if no active strategy, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Sets active strategy to empty, logs deactivation

### `unload_strategy(strategy_name: str, registry: StrategyRegistry, logger_instance: StrategyLogger) -> Dict[str, str]`
**Pre:** strategy_name is loaded strategy
**Post:** Unloads strategy from registry
**Raises:** HTTPException(400) on unload failure, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Removes strategy from registry, logs unload event

### `get_strategy(strategy_name: str, registry: StrategyRegistry) -> StrategyResponse`
**Pre:** strategy_name is loaded strategy
**Post:** Returns strategy details
**Raises:** HTTPException(404) if not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** None (read-only)

### `update_strategy_parameters(strategy_name: str, request: StrategyUpdateRequest, registry: StrategyRegistry) -> Dict[str, str]`
**Pre:** strategy_name is loaded, request.parameters is valid
**Post:** Updates strategy parameters
**Raises:** HTTPException(404) if not found, HTTPException(500) on errors
**Retry:** No
**Side Effects:** Modifies strategy parameters

### `get_strategy_metrics(strategy_name: str, logger_instance: StrategyLogger) -> StrategyMetricsResponse`
**Pre:** strategy_name exists in logger
**Post:** Returns strategy metrics
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_all_metrics(logger_instance: StrategyLogger) -> Dict[str, Any]`
**Pre:** Logger is initialized
**Post:** Returns metrics for all strategies
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `get_execution_stats(engine: ExecutionEngine) -> ExecutionStatsResponse`
**Pre:** Engine is initialized
**Post:** Returns execution engine statistics
**Raises:** HTTPException(500) on retrieval errors
**Retry:** No
**Side Effects:** None (read-only)

### `start_execution_engine(engine: ExecutionEngine) -> Dict[str, str]`
**Pre:** Engine is initialized and not running
**Post:** Starts execution engine
**Raises:** HTTPException(500) on start errors
**Retry:** No
**Side Effects:** Starts engine execution loop

### `stop_execution_engine(engine: ExecutionEngine) -> Dict[str, str]`
**Pre:** Engine is running
**Post:** Stops execution engine
**Raises:** HTTPException(500) on stop errors
**Retry:** No
**Side Effects:** Stops engine execution loop

### `reset_execution_stats(engine: ExecutionEngine) -> Dict[str, str]`
**Pre:** Engine is initialized
**Post:** Resets execution statistics
**Raises:** HTTPException(500) on reset errors
**Retry:** No
**Side Effects:** Clears execution counters

---

## Acceptance Criteria
- [ ] Strategy names are validated against available strategies
- [ ] Only one strategy can be active at a time
- [ ] Loading non-existent strategy returns 400
- [ ] Activating non-loaded strategy returns 400
- [ ] Deactivating when no active strategy returns 400
- [ ] Unloading strategy removes it from registry
- [ ] Metrics calculate correct rates (execution, rejection, error)
- [ ] Execution engine start/stop changes running status
- [ ] All operations log to StrategyLogger
- [ ] All responses include success/message

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-001 | 28-security-and-secrets.md | No hardcoded credentials | ✅ OK |
| API-002 | 09-logging-observability.md | Structured logging | ⚠️ PARTIAL - Uses StrategyLogger |
| API-003 | 08-configuration.md | Input validation | ✅ OK - Good validation |
| API-004 | 06-testing.md | Test coverage | ❌ GAP - No test evidence |
| API-005 | 28-security-and-secrets.md | Authentication for strategy operations | ❌ GAP - No auth visible |
| API-006 | 07-async-patterns.md | Async operations | ✅ OK - All endpoints async |
| API-007 | 05-architecture.md | API layer only handles HTTP | ✅ OK - Delegates to services |
| API-008 | 12-logging-observability.md | Error handling | ✅ OK - Comprehensive error handling |
| API-009 | 09-logging-observability.md | Audit logging for strategy changes | ✅ OK - Uses StrategyLogger |
| API-010 | 04-design-patterns.md | Singleton pattern | ⚠️ PARTIAL - Global singletons used |

---

## Dependencies
- **External:** fastapi, pydantic
- **Internal:** app.strategies (ExecutionEngine, StrategyConfigLoader, StrategyLogger, StrategyRegistry)

---

## Required Tests
- **test_strategies_endpoints.py:**
  - Test get_strategies_overview returns all strategies
  - Test get_available_strategies returns strategy list
  - Test get_loaded_strategies returns loaded strategies
  - Test load_strategy with valid strategy
  - Test load_strategy rejects invalid strategy
  - Test activate_strategy sets active strategy
  - Test activate_strategy rejects non-loaded strategy
  - Test deactivate_strategy clears active strategy
  - Test deactivate_strategy returns 400 when none active
  - Test unload_strategy removes from registry
  - Test get_strategy returns strategy details
  - Test get_strategy returns 404 for non-existent strategy
  - Test update_strategy_parameters updates parameters
  - Test get_strategy_metrics returns correct metrics
  - Test get_all_metrics returns all strategy metrics
  - Test start_execution_engine starts engine
  - Test stop_execution_engine stops engine
  - Test reset_execution_stats clears counters
  - Test all endpoints log operations appropriately

---

## Notes
- Comments and docstrings in Spanish (gestión de estrategias - TASK-31)
- Uses singleton pattern for all services (global variables)
- Comprehensive strategy lifecycle management
- No authentication/authorization visible
- Execution engine controls strategy execution loop
- StrategyLogger provides audit trail
