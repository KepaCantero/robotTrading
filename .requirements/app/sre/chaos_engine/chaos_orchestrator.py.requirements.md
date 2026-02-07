# Requirements: sre/chaos_engine/chaos_orchestrator.py

## Source File Analysis
- **File Path**: `app/sre/chaos_engine/chaos_orchestrator.py`
- **Lines of Code**: 692
- **Purpose**: Coordinates chaos engineering experiments
- **Audit Status**: PASSED

## Purpose
Implements Google SRE chaos engineering practices:
- Hypothesis-driven experimentation
- Controlled failure injection
- Automated validation
- Blast radius control
- Rollback automation

## Dependencies

### Internal Dependencies
- `.blast_radius.BlastRadiusController`
- `.hypothesis.ChaosHypothesis, HypothesisValidator, ValidationResult`

### External Dependencies
- `aiosqlite`: Async database operations
- `uuid`: Unique identifiers
- `pathlib`: Path manipulation

## Classes/Functions

### Main Classes

1. **ExperimentStatus (Enum)**
   - PENDING, RUNNING, COMPLETED, FAILED, ROLLED_BACK, CANCELLED

2. **ChaosExperiment (dataclass)**
   - Complete experiment definition and results

3. **ChaosConfig (dataclass)**
   - Safety limits, rollback settings, monitoring config

4. **ChaosOrchestrator** (Main class)
   - `__init__(service_name, failure_injectors, blast_radius_controller, hypothesis_validator, metrics_collector, config)`
   - `initialize()`
   - `run_experiment(name, hypothesis, injectors, ...) -> ChaosExperiment`
   - `_validate_experiment_request(injectors, duration_minutes, approved_by)`
   - `_execute_experiment(experiment)`
   - `_inject_failures(experiment)`
   - `_monitor_experiment(experiment)`
   - `_validate_hypothesis(experiment, baseline_metrics)`
   - `_rollback_failures(experiment)`
   - `cancel_experiment(experiment_id) -> bool`

## Business Logic

### Experiment Phases
1. Pre-experiment baseline collection
2. Blast radius controls application
3. Failure injection
4. Monitoring and validation
5. Hypothesis validation
6. Rollback failures

### Safety Features
- Time window restrictions (allowed_hours)
- Duration limits (max_duration_minutes)
- Daily experiment limits (max_experiments_per_day)
- Approval gates (require_approval)
- Auto-rollback on failure

## API Contracts

### run_experiment()
```python
async def run_experiment(
    name: str,
    hypothesis: str,
    injectors: List[str],
    duration_minutes: int = 30,
    description: str = "",
    blast_radius_config: Optional[Dict[str, Any]] = None,
    approved_by: Optional[str] = None,
) -> ChaosExperiment
```

**Preconditions:**
- Within allowed hours
- Duration <= max_duration_minutes
- Injectors exist in registry
- Approval provided if required
- Daily limit not exceeded

**Postconditions:**
- Experiment executed through all phases
- Results saved to database
- Rollback completed on failure

## Error Handling

### Current Approach
- Try-except around experiment execution
- Auto-rollback on failure
- Comprehensive error logging
- Incident tracking

### Passed Rules
- **LOG-004**: Error logging with context
- **CC-006**: Explicit error handling with rollback

## Performance Considerations

### Time Complexity
- O(duration_minutes / check_interval) for monitoring

### Recommendations
- Add timeout for experiment execution
- Prune experiment history

## Testing Strategy

### Unit Tests Required
1. Test experiment validation
2. Test hypothesis validation logic
3. Test rollback logic
4. Test incident tracking
5. Test safety limits enforcement

## Compliance with BASE_RULES.md

### Passed Rules
- **TYP-001**: Type hints throughout
- **ASYNC-001**: Proper async usage
- **LOG-001**: Structured logging with service_name
- **LOG-004**: Error logging with context
- **SOL-001**: Single responsibility (orchestration only)
- **DP-004**: Dependency injection
- **SEC-005**: Audit logging (experiment tracking)

### Audit Status: PASSED

Excellent chaos orchestration implementation:
1. Comprehensive safety features
2. Phase-based execution
3. Rollback automation
4. Incident tracking
5. Approval workflow
6. Database persistence

---
*Audited on 2025-02-07*
*Reference: BASE_RULES.md*
