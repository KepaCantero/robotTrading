# Task: Refactor app/api/signals.py - Implement Dependency Injection

## Extends
- **Base:** `.claude/base/REFACTOR_BASE.md`
- **Orchestrator:** @agent-tech-lead-orchestrator

## Context Variables (Pre-filled)
- `{{PYTHON_FILE}}` = `app/api/signals.py`
- `{{VIOLATION_TYPE}}` = `DP-004`
- `{{PATTERN}}` = `DI Container`
- `{{REQUIREMENTS_FILE}}` = `.requirements/app/api/signals.py.requirements.md`
- `{{INSTRUCTIONS_FILE}}` = `.claude/tasks/refactor_signals_di.md`
- `{{TEST_FILE}}` = `tests/api/test_signals.py`

---

## Refactoring Details

**File:** `app/api/signals.py`
**Lines:** 36-38
**Violation:** DP-004 (Direct Instantiation)
**Pattern:** DI Container with FastAPI Depends

### Current Code
```python
portfolio_provider = PaperTradingPortfolioProvider()
portfolio_service = PortfolioService(portfolio_provider)
_signal_scorer_service = SignalScorerService(portfolio_service)
```

### Target Code
```python
from app.core.di_container import DIContainer

_di_container = DIContainer()

def get_signal_scorer_service() -> SignalScorerService:
    """FastAPI dependency for signal scorer service."""
    return _di_container.get_signal_scorer_service()

# All endpoints use:
# signal_scorer_service: SignalScorerService = Depends(get_signal_scorer_service)
```

---

## Filled Templates (Pre-filled with Context Variables)

### Step 1: Implementer (@agent-backend-developer)

**Template:** `.tasks/templates/REFACTOR_IMPLEMENTER.md`

**All variables pre-filled:**

```markdown
## Agent to Delegate
@agent-tech-lead-orchestrator (delegates to @agent-backend-developer)

## Repository Information
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
BASE_RULES: .requirements/BASE_RULES.md

## Task
Refactor: `app/api/signals.py`
Violation Type: `DP-004`
Refactoring Pattern: `DI Container`

## Required Resources
Python File: app/api/signals.py
Requirements: .requirements/app/api/signals.py.requirements.md
BASE_RULES: .requirements/BASE_RULES.md
Refactoring Instructions: .claude/tasks/refactor_signals_di.md

## Implementation Steps
1. Read app/api/signals.py
2. Read .requirements/BASE_RULES.md
3. Extend app/core/di_container.py with SignalScorerService
4. Add get_signal_scorer_service() dependency function
5. Update all endpoints to use Depends(get_signal_scorer_service)
6. Remove service chain instantiation at lines 36-38
7. Verify: python -m py_compile app/api/signals.py
```

---

### Step 2: Tester (@agent-python-testing-expert)

**Template:** `.tasks/templates/REFACTOR_TESTER.md`

**All variables pre-filled:**

```markdown
## Agent to Delegate
@agent-tech-lead-orchestrator (delegates to @agent-python-testing-expert)

## Repository Information
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main

## Task
Test refactored code for: `app/api/signals.py`
Refactoring changes: [TO BE FILLED FROM STEP 1 OUTPUT]

## Required Resources
Python File: app/api/signals.py
Test File: tests/api/test_signals.py
Changes Summary: [FROM STEP 1]

## Tests to Create
```python
def test_get_signal_scorer_service_dependency_chain():
    """Test signal scorer depends on portfolio service."""
    container = DIContainer()
    signal_service = container.get_signal_scorer_service()
    assert signal_service.portfolio_service is not None

def test_di_container_singleton():
    """Test service is singleton."""
    service1 = get_signal_scorer_service()
    service2 = get_signal_scorer_service()
    assert service1 is service2
```
```

---

### Step 3: Code Reviewer (@agent-code-reviewer)

**Template:** `.tasks/templates/REFACTOR_CODE_REVIEWER.md`

**All variables pre-filled:**

```markdown
## Agent to Delegate
@agent-tech-lead-orchestrator (delegates to @agent-code-reviewer)

## Repository Information
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
BASE_RULES: .requirements/BASE_RULES.md

## Task
Review refactored code for: `app/api/signals.py`
Refactoring Type: `DP-004`
Changes: [TO BE FILLED FROM STEP 1 OUTPUT]

## Required Resources
Python File: app/api/signals.py
Requirements: .requirements/app/api/signals.py.requirements.md
Test File: tests/api/test_signals.py
Changes Summary: [FROM STEP 1]
BASE_RULES: .requirements/BASE_RULES.md

## QA Commands
cd /Users/kepa.cantero/Projects/algoTrading
python -m py_compile app/api/signals.py
mypy --strict app/api/signals.py
ruff check app/api/signals.py
pytest tests/api/test_signals.py -v
```

---

### Step 4: Auditor (@agent-code-auditor)

**Template:** `.tasks/templates/REFACTOR_AUDITOR.md`

**All variables pre-filled:**

```markdown
## Agent to Delegate
@agent-tech-lead-orchestrator (delegates to @agent-code-auditor)

## Repository Information
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
Requirements Location: .requirements/
BASE_RULES: .requirements/BASE_RULES.md

## Task
Audit refactoring compliance for: `app/api/signals.py`
Refactoring Type: `DP-004`
Code Review Status: [TO BE FILLED FROM STEP 3]

## Required Resources
Python File: app/api/signals.py
Requirements: .requirements/app/api/signals.py.requirements.md
BASE_RULES: .requirements/BASE_RULES.md
Verification Checklist: .tasks/templates/GAP_FIX_PATTERNS.md

## Verification Checklist
- DI Container exists
- No direct instantiation
- Depends() used correctly
- Singleton pattern implemented
- Service dependency chain managed by container
```

---

## Acceptance Criteria

- [ ] `app/core/di_container.py` extended with SignalScorerService
- [ ] `app/api/signals.py` uses DI container
- [ ] Service dependency chain managed by container
- [ ] Tests pass
- [ ] QA checks pass
- [ ] Requirements updated: DP-004 → ✅ FIXED

---

## Files

| File | Action |
|------|--------|
| `app/core/di_container.py` | EXTEND |
| `app/api/signals.py` | MODIFY |
| `tests/api/test_signals.py` | UPDATE |
| `.requirements/app/api/signals.py.requirements.md` | UPDATE |

---

**Priority:** P1
**Estimated:** 2-3 hours
**Dependencies:** `refactor_portfolio_di.md` (requires DI container)
