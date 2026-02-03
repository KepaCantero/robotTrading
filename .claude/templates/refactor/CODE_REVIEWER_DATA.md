# Template: Code Reviewer Data (Refactoring)

**Role:** `.claude/roles/CODE_REVIEWER.md` (@agent-code-reviewer)
**Data format for refactoring code review**

---

## Context Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{PYTHON_FILE}}` | File to review | `app/api/portfolio.py` |
| `{{VIOLATION_TYPE}}` | Type of violation fixed | `DP-004`, `ARCH-001` |
| `{{REQUIREMENTS_FILE}}` | Requirements file | `.requirements/app/api/portfolio.py.requirements.md` |
| `{{TEST_FILE}}` | Test file | `tests/api/test_portfolio.py` |
| `{{CHANGES_SUMMARY}}` | Summary of changes | [from Step 1] |
| `{{DATE}}` | Current timestamp | [from `date -u +%Y-%m-%dT%H:%M:%SZ`] |

---

## Required Resources

```bash
# Read the refactored source file
Read {{PYTHON_FILE}}

# Read requirements to understand what was fixed
Read {{REQUIREMENTS_FILE}}

# Read BASE_RULES for verification
Read .requirements/BASE_RULES.md

# Get current date
date -u +%Y-%m-%dT%H:%M:%SZ
```

---

## QA Commands

```bash
cd /Users/kepa.cantero/Projects/algoTrading

python -m py_compile {{PYTHON_FILE}}
mypy --strict {{PYTHON_FILE}}
ruff check {{PYTHON_FILE}}
black --check {{PYTHON_FILE}}
pytest {{TEST_FILE}} -v
```

---

## Output Format

```markdown
## Code Review Complete

**File:** {{PYTHON_FILE}}
**Refactoring Type:** {{VIOLATION_TYPE}}
**Date:** {{DATE}}
**Status:** [APPROVED / NEEDS_CHANGES]

**QA Checks Summary:**
| Check | Status | Notes |
|-------|--------|-------|
| Syntax | ✅/❌ | |
| Type Checking | ✅/❌/N/A | |
| Linting | ✅/❌/N/A | |
| Tests | ✅/❌/N/A | |

**Overall Assessment:**
[Summary]

**Next:** [Ready for audit OR Back to implementer]
```

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
