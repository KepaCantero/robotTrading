# Requirements: sre/chaos_engine/game_days.py

## Source File Analysis
- **File Path**: `app/sre/chaos_engine/game_days.py`
- **Lines of Code**: 561
- **Purpose**: Game day exercise orchestration
- **Audit Status**: PASSED

## Purpose
Implements Google SRE game day practices:
- Controlled failure exercises
- Team training for incidents
- Validation of runbooks
- Performance under pressure
- Postmortem generation

## Dependencies

### Internal Dependencies
- `.chaos_orchestrator.ChaosOrchestrator`
- `.failure_injectors.FailureInjectorRegistry`

### External Dependencies
- `aiosqlite`: Async database operations
- `pathlib`: Path manipulation

## Classes/Functions

### Main Classes

1. **ExerciseStatus (Enum)**
   - PLANNED, RUNNING, COMPLETED, CANCELLED

2. **ExerciseDifficulty (Enum)**
   - BEGINNER, INTERMEDIATE, ADVANCED

3. **ExerciseObjective (Enum)**
   - RUNBOOK_VALIDATION, TEAM_TRAINING, SYSTEM_RECOVERY, etc.

4. **GameDayExercise (dataclass)**
   - Complete exercise definition

5. **GameDayResult (dataclass)**
   - Exercise results and metrics

6. **GameDayOrchestrator** (Main class)
   - `__init__(chaos_orchestrator, failure_registry, db_path)`
   - `initialize()`
   - `create_exercise(name, description, difficulty, ...) -> GameDayExercise`
   - `run_exercise(exercise_id) -> GameDayResult`
   - `_prepare_scenario(exercise)`
   - `_monitor_progress(exercise)`
   - `_generate_postmortem(exercise, result)`

## Business Logic

### Exercise Phases
1. Planning and scenario setup
2. Briefing participants
3. Injecting failures
4. Monitoring response
5. Debrief and postmortem

### Objectives
- Validate runbooks work
- Train new team members
- Test communication channels
- Measure MTTR

## API Contracts

### run_exercise()
```python
async def run_exercise(exercise_id: str) -> GameDayResult
```

**Preconditions:**
- Exercise exists
- Participants briefed

**Postconditions:**
- Scenarios executed
- Results collected
- Postmortem generated

## Error Handling

- Exception handling with status tracking
- Postmortem generation even on failure

## Compliance with BASE_RULES.md

### Passed Rules
- **TYP-001**: Type hints
- **ASYNC-001**: Proper async
- **LOG-001**: Structured logging
- **SEC-005**: Audit logging (exercises tracked)

### Audit Status: PASSED

Excellent game day implementation:
1. Clear objectives
2. Difficulty levels
3. Postmortem generation
4. Team coordination

---
*Audited on 2025-02-07*
*Reference: BASE_RULES.md*
