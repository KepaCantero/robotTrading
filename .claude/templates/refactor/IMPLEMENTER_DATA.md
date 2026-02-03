# Template: Implementer Data (Refactoring)

**Role:** `.claude/roles/IMPLEMENTER.md` (@agent-backend-developer)
**Data format for refactoring implementation**

---

## Context Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{PYTHON_FILE}}` | File to refactor | `app/api/portfolio.py` |
| `{{VIOLATION_TYPE}}` | Type of violation | `DP-004`, `ARCH-001` |
| `{{PATTERN}}` | Refactoring pattern | `DI Container`, `Service Layer` |
| `{{REQUIREMENTS_FILE}}` | Requirements file | `.requirements/app/api/portfolio.py.requirements.md` |
| `{{INSTRUCTIONS_FILE}}` | Task instructions | `.claude/tasks/refactor_portfolio_di.md` |

---

## Required Resources

```bash
# Read the source file
Read {{PYTHON_FILE}}

# Read BASE_RULES for context
Read .requirements/BASE_RULES.md

# Read refactoring instructions
Read {{INSTRUCTIONS_FILE}}

# Read requirements file
Read {{REQUIREMENTS_FILE}}
```

---

## Output Format

```markdown
## Implementation Complete

**File:** {{PYTHON_FILE}}
**Violation:** {{VIOLATION_TYPE}}
**Pattern:** {{PATTERN}}
**Status:** ✅ IMPLEMENTED

**Changes Applied:**
| Line(s) | Change | Pattern |
|---------|--------|---------|
| 43 | Replaced direct instantiation with DI container | {{VIOLATION_TYPE}} |

**Files Created/Modified:**
- {{PYTHON_FILE}}: [description]
- [NEW_FILE]: [if any]

**Syntax Verification:** ✅ PASS / ❌ FAIL
**Next:** Ready for testing
```

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
