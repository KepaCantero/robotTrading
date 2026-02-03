# Template: Tester Data (Refactoring)

**Role:** `.claude/roles/TESTER.md` (@agent-python-testing-expert)
**Data format for refactoring testing**

---

## Context Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{PYTHON_FILE}}` | File that was refactored | `app/api/portfolio.py` |
| `{{TEST_FILE}}` | Test file to update/create | `tests/api/test_portfolio.py` |
| `{{CHANGES_SUMMARY}}` | Summary of changes from implementer | [from Step 1 output] |

---

## Required Resources

```bash
# Read the refactored source file
Read {{PYTHON_FILE}}

# Read existing test file
Read {{TEST_FILE}}

# Read changes summary from implementer
# [Provided as context]
```

---

## Output Format

```markdown
## Testing Complete

**File:** {{PYTHON_FILE}}
**Test File:** {{TEST_FILE}}
**Status:** ✅ PASS / ❌ FAIL

**Tests Created/Updated:**
| Test | Description | Status |
|------|-------------|--------|
| test_service_singleton | Verify singleton behavior | ✅ PASS |

**Test Results Summary:**
- Total tests: N
- Passed: N
- Failed: N
- Coverage: X%

**Next:** [Ready for code review OR Fix needed]
```

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
