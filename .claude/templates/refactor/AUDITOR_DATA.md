# Template: Auditor Data (Refactoring)

**Role:** `.claude/roles/AUDITOR.md` (@agent-code-auditor)
**Data format for refactoring compliance audit**

---

## Context Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{PYTHON_FILE}}` | File to audit | `app/api/portfolio.py` |
| `{{VIOLATION_TYPE}}` | Type of violation | `DP-004`, `ARCH-001` |
| `{{REQUIREMENTS_FILE}}` | Requirements file | `.requirements/app/api/portfolio.py.requirements.md` |
| `{{CODE_REVIEW_STATUS}}` | Status from code review | [from Step 3] |
| `{{TIMESTAMP}}` | Current timestamp | [from `date -u +%Y-%m-%dT%H:%M:%SZ`] |

---

## Required Resources

```bash
# Read requirements document
Read {{REQUIREMENTS_FILE}}

# Read current code
Read {{PYTHON_FILE}}

# Get timestamp
date -u +%Y-%m-%dT%H:%M:%SZ
```

---

## Verification Checklist

**For DP-004 (Dependency Injection):**
- [ ] DI Container exists
- [ ] No direct instantiation
- [ ] Depends() used correctly
- [ ] Singleton pattern implemented

**For ARCH-001 (Layering):**
- [ ] No DB imports in API
- [ ] Service class exists
- [ ] API delegates to service
- [ ] No business logic in API

---

## Output Format

```markdown
## Refactoring Audit Complete

**File:** {{PYTHON_FILE}}
**Requirements:** {{REQUIREMENTS_FILE}}
**Date:** {{TIMESTAMP}}
**Refactoring Type:** {{VIOLATION_TYPE}}
**Status:** [PASS / FAIL]

**Violations Audited:**
| Rule | Source | Status | Evidence |
|------|--------|--------|----------|
| DP-004 | BASE_RULES | ✅ FIXED | Line 43: DI container implemented |

**Summary:**
- Total violations: N
- Verified fixed: N
- Remaining: N

**Requirements Document:** [UPDATED / NOT UPDATED]

**Next:** [Task complete OR Back to implementer]
```

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
