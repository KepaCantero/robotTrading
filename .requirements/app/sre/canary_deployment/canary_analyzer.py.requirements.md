# Requirements: sre/canary_deployment/canary_analyzer.py

## Source File Analysis
- **File Path**: `app/sre/canary_deployment/canary_analyzer.py`
- **Lines of Code**: 506
- **Purpose**: Canary deployment metrics analyzer for progressive rollout
- **Audit Status**: PASSED

## Purpose
Analyzes canary deployment metrics to make rollback/promotion decisions. Implements Google SRE canary deployment practices.

## Dependencies

### External Dependencies
- `aiosqlite`: Async database operations
- `statistics`: Statistical calculations
- `decimal`: Precise financial calculations
- `dataclasses`: Data structures

### Internal Dependencies
None

## Classes/Functions

### Main Classes

1. **RollbackTrigger (Enum)**
   - ERROR_RATE_HIGH, LATENCY_HIGH, AVAILABILITY_LOW, THROUGHPUT_LOW, MANUAL

2. **MetricComparison (dataclass)**
   - Compares canary vs baseline metrics
   - Statistical analysis with p-value, confidence interval

3. **CanaryAnalysisResult (dataclass)**
   - Complete analysis result with rollback decision

4. **CanaryAnalyzer**
   - `__init__(service_name, db_path)`
   - `analyze_stage(deployment_id, stage) -> CanaryAnalysisResult`
   - `_load_stage_metrics(deployment_id, stage)`
   - `_calculate_aggregate_metrics(metrics)`
   - `_compare_metrics(aggregate) -> List[MetricComparison]`
   - `_make_decision(comparisons) -> Dict[str, Any]`

## Business Logic

### Rollback Thresholds
- Error rate increase: 50%
- Latency increase: 50%
- Availability drop: 1%
- Throughput drop: 20%

### Promotion Thresholds
- Max error rate: 1%
- Max latency increase: 10%
- Min availability: 99.5%
- Max throughput drop: 5%

### Decision Logic
1. Check rollback conditions (significant degradation)
2. Check promotion conditions (within acceptable thresholds)
3. Calculate confidence based on decision type
4. Generate recommendations

## Data Models

### MetricComparison
- `metric_name`: Name of metric
- `canary_value`, `baseline_value`: Values
- `delta`, `delta_percentage`: Difference
- `is_significant`: Whether exceeds threshold
- `p_value`: Statistical significance
- `confidence_interval`: Confidence interval

### CanaryAnalysisResult
- `should_rollback`: Whether to rollback
- `should_promote`: Whether to promote
- `confidence`: Decision confidence (0.0-1.0)
- `comparisons`: List of metric comparisons
- `rollback_trigger`: Trigger if rollback
- `recommendations`: List of recommendations

## API Contracts

### analyze_stage()
```python
async def analyze_stage(
    deployment_id: int,
    stage: int,
) -> CanaryAnalysisResult
```

**Preconditions:**
- Deployment exists in database
- Stage has collected metrics

**Postconditions:**
- Returns CanaryAnalysisResult with decision
- Recommendations list is populated

## Error Handling

### Current Approach
- Returns empty metrics result if no metrics found (graceful degradation)
- Logs errors but doesn't raise exceptions

### Passed Rules
- Graceful handling of missing data
- Error logging with context

## Performance Considerations

### Time Complexity
- `_calculate_aggregate_metrics`: O(n) where n = metrics samples
- `_compare_metrics`: O(1) for fixed number of metrics

### Space Complexity
- O(n) for metrics storage in database

## Testing Strategy

### Unit Tests Required
1. Test metric comparison logic
2. Test rollback decision thresholds
3. Test promotion decision thresholds
4. Test edge cases (no metrics, single metric)
5. Test confidence calculation

### Integration Tests
- Test with database (canary_metrics table)
- Test aggregate calculation with real data

## Compliance with BASE_RULES.md

### Passed Rules
- **TYP-001**: All functions have type hints
- **ASYNC-001**: Async functions properly marked
- **LOG-001**: Structured logging with service_name
- **LOG-004**: Exceptions logged with context
- **CC-006**: Explicit return types
- **DP-004**: Dependency injection via constructor

### Gaps Found
- **P2**: Some methods exceed 20 lines (acceptable for aggregation logic)
- **P2**: Missing input validation for deployment_id (could be negative)

### Audit Status: PASSED

Clean implementation of canary analysis:
1. Proper async/await patterns
2. Clear separation of concerns
3. Graceful error handling
4. Well-documented with docstrings
5. Type hints throughout

**Minor gaps** (P2):
- Add validation for deployment_id > 0
- Consider adding timeout for database operations

---
*Audited on 2025-02-07*
*Reference: BASE_RULES.md*
