# Requirements: sre/chaos_engine/blast_radius.py

## Source File Analysis
- **File Path**: `app/sre/chaos_engine/blast_radius.py`
- **Lines of Code**: 431
- **Purpose**: Controls blast radius for chaos experiments
- **Audit Status**: PASSED

## Purpose
Implements blast radius control to prevent widespread outages during chaos engineering:
- Isolates failures to specific segments
- Prevents cascading failures
- Enables safe experimentation
- Automatic containment

## Dependencies

### External Dependencies
- `aiosqlite`: Async database operations
- `pathlib`: Path manipulation
- `decimal`: Precise calculations

### Internal Dependencies
None

## Classes/Functions

### Main Classes

1. **BlastRadiusScope (Enum)**
   - SINGLE_POD, SINGLE_NODE, SINGLE_ZONE, SINGLE_REGION, PERCENTAGE, CUSTOM

2. **BlastRadiusConfig (dataclass)**
   - Scope configuration
   - Traffic splitting
   - Constraints (max_failure_domains, require_quorum, min_healthy_pods)

3. **ContainmentState (dataclass)**
   - Current containment state
   - Active failures, isolated domains, health status

4. **BlastRadiusController** (Main class)
   - `__init__(service_name, db_path)`
   - `initialize()`
   - `apply_controls(config_dict) -> ContainmentState`
   - `_validate_config(config)`
   - `_apply_containment(config) -> ContainmentState`
   - `_apply_traffic_split(traffic_split, state)`
   - `_isolate_failure_domains(config, state)`
   - `remove_controls() -> bool`

## Business Logic

### Validation Rules
- `min_healthy_pods >= 1` for POD/PERCENTAGE scope
- Cannot fail majority when quorum required (percentage > 50%)

### Containment Actions
- Apply traffic splitting rules
- Isolate failure domains (zones, regions, nodes)
- Maintain quorum when required
- Track health status

## API Contracts

### apply_controls()
```python
async def apply_controls(config_dict: Dict[str, Any]) -> ContainmentState
```

**Preconditions:**
- Config valid per validation rules
- Blast radius within acceptable limits

**Postconditions:**
- Containment applied and saved to database
- State returned with current status

### remove_controls()
```python
async def remove_controls() -> bool
```

**Preconditions:**
- Active containment exists

**Postconditions:**
- Containment marked as removed in database
- State cleared

## Error Handling

### Current Approach
- Exception handling in database operations
- Validation before applying controls

### Passed Rules
- **LOG-004**: Error logging with context
- **CC-006**: Explicit validation

## Performance Considerations

### Time Complexity
- O(1) for all operations

### Space Complexity
- O(n) for containment history

## Testing Strategy

### Unit Tests Required
1. Test config validation (edge cases)
2. Test traffic splitting
3. Test failure domain isolation
4. Test rollback (remove_controls)
5. Test quorum requirements

## Compliance with BASE_RULES.md

### Passed Rules
- **TYP-001**: Type hints throughout
- **ASYNC-001**: Proper async usage
- **LOG-001**: Structured logging
- **SOL-001**: Single responsibility
- **DP-004**: Dependency injection

### Audit Status: PASSED

Clean implementation with proper safety controls:
1. Validation prevents dangerous configurations
2. State persistence for recovery
3. Clear separation of concerns
4. Comprehensive logging

---
*Audited on 2025-02-07*
*Reference: BASE_RULES.md*
