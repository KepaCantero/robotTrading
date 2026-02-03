# Wrapper: Tech Lead Orchestrator

**This is the MASTER COORDINATION TEMPLATE for the GAP audit and fix workflow**

The Tech Lead Orchestrator coordinates all specialist agents through this workflow. Other templates wrap specific tasks; this template orchestrates the entire process.

---

## Agent Role

**@agent-tech-lead-orchestrator** - The coordinator that delegates to specialist agents based on workflow state.

---

## Repository Context

```
Repository: /Users/kepa.cantero/Projects/algoTrading
Working Directory: /Users/kepa.cantero/Projects/algoTrading
Branch: main
Requirements Location: .requirements/
BASE_RULES: .requirements/BASE_RULES.md (96+ universal rules)
Templates Location: .tasks/templates/
Task Definition: .claude/tasks/audit_and_fix_gaps.md
```

---

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TECH LEAD ORCHESTRATOR                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. SCAN CODE FOR GAPS (LLM-Based Analysis)                        │   │
│  │     Call @agent-python-expert to analyze file against BASE_RULES.md  │   │
│  │     Output: List of actual GAP violations with line numbers         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  2. FOR EACH FILE (in priority order P0→P1→P2→P3):                  │   │
│  │                                                                      │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────┐ │   │
│  │  │ Requirements     │───▶│ Implementer      │───▶│ Tester         │ │   │
│  │  │ (if missing)     │    │ @python-expert   │    │ @testing-expert│ │   │
│  │  │ @python-expert   │    │                  │    │                │ │   │
│  │  └──────────────────┘    └──────────────────┘    └────────────────┘ │   │
│  │                                                          ↓           │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────┐ │   │
│  │  │ Auditor          │◀───│ Code Reviewer    │◀───│ Tests Created  │ │   │
│  │  │ @code-auditor    │    │ @code-reviewer   │    │                │ │   │
│  │  └──────────────────┘    └──────────────────┘    └────────────────┘ │   │
│  │           ↓                                                          │   │
│  │  ┌──────────────────┐                                                  │   │
│  │  │ COMPLETE / RETRY │                                                  │   │
│  │  └──────────────────┘                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Instructions

### Step 0: List Files Needing Audit

**Use the script to find files that need auditing:**

```bash
cd /Users/kepa.cantero/Projects/algoTrading
python scripts/list_files_for_audit.py
```

**The script checks:**
1. If requirements file exists
2. If "Audit Status" is PASSED and recent (< 7 days) → SKIP
3. If "Audit Status" is PASSED but old (> 7 days) → RE-AUDIT
4. If "Audit Status" is NEEDS_AUDIT or FAILED → AUDIT
5. If no requirements file → CREATE + AUDIT

**Process output:** Get list of files by batch/layer

---

### Step 1: Scan for GAP Violations (LLM-Based)

**For EACH file that needs audit:**

```
Call @agent-python-expert with:

Analyze app/[PATH]/[FileName].py for GAP violations.

1. Read BASE_RULES.md: .requirements/BASE_RULES.md (96+ universal rules)
2. Read file requirements: .requirements/[PATH]/[FileName].requirements.md (if exists)
3. Read Python file: app/[PATH]/[FileName].py

For EACH rule from BOTH sources:
A. From BASE_RULES.md (universal rules):
   1. Check if the rule applies to this file type/context
   2. Verify if the code follows the rule
   3. Report violations with line numbers

B. From file-specific requirements (in requirements.md):
   1. Check "Critical Rules (MUST NOT BREAK)" table
   2. For rules marked as ❌ GAP:
      - Verify if still violated in current code
      - Report if still needs fixing
   3. For rules marked as ⚠️ PARTIAL:
      - Verify what's missing
      - Report completion status

Report violations with:
   - Rule ID (e.g., LOG-001, CC-006, TRD-005)
   - Source (BASE_RULES.md or file-specific)
   - Description
   - Line number
   - Priority (P0/P1/P2/P3)
   - Current status (❌ VIOLATED / ✅ OK / ⚠️ NOT APPLIED / ⚠️ PARTIAL)

Return a structured list of GAP violations found, grouped by source.
```

**Output format:** Use `.tasks/templates/GAP_ANALYSIS_OUTPUT.md` template

---

### Step 2: Process Each File (Bottom-Up by Layer)

**Processing Order:** L10 → L9 → L7 → L6 → L8 → L3-L5 → L11 → L1 → L12-L13

**For each file with GAPs:**

#### 2.1 Check Requirements Exist

**IF requirements document does NOT exist:**

```
Call @agent-tech-lead-orchestrator with template: REQUIREMENT_EXPERT.md

Context:
- Python File: app/[PATH]/[FileName].py
- Requirements Output: .requirements/[PATH]/[FileName].requirements.md
- BASE_RULES: .requirements/BASE_RULES.md
- Template: .tasks/templates/REQUIREMENT_TEMPLATE.md

Expected output: Requirements document created with:
- Type definitions
- Function signatures with contracts
- Acceptance criteria
- Critical rules analysis (BASE_RULES + file-specific)
- Dependencies
- Required tests
- Notes
- Audit Status: NEEDS_AUDIT
```

#### 2.2 Call Implementer

```
Call @agent-tech-lead-orchestrator with template: IMPLEMENTER.md

Context:
- Python File: app/[PATH]/[FileName].py
- Requirements: .requirements/[PATH]/[FileName].requirements.md
- BASE_RULES: .requirements/BASE_RULES.md
- Fix Patterns: .tasks/templates/GAP_FIX_PATTERNS.md
- Mode: Minimal (only fix specific GAPs)

GAPs from analysis:
- RULE-ID:line - Description
- RULE-ID:line - Description

Expected output:
- GAP violations fixed using Edit tool
- Syntax check passes
- Implementation summary
```

#### 2.3 Call Tester

```
Call @agent-tech-lead-orchestrator with template: TESTER.md

Context:
- Python File: app/[PATH]/[FileName].py
- Requirements: .requirements/[PATH]/[FileName].requirements.md
- Test File: tests/[PATH]/test_[FileName].py
- Changes: [Summary from implementer]

Expected output:
- Tests created/updated
- All tests pass
- Coverage report
```

#### 2.4 Call Code Reviewer

```
Call @agent-tech-lead-orchestrator with template: CODE_REVIEWER.md

Context:
- Python File: app/[PATH]/[FileName].py
- Requirements: .requirements/[PATH]/[FileName].requirements.md
- Test File: tests/[PATH]/test_[FileName].py
- BASE_RULES: .requirements/BASE_RULES.md

QA commands:
```bash
cd /Users/kepa.cantero/Projects/algoTrading

# 1. Syntax check
python -m py_compile app/[PATH]/[FileName].py

# 2. Type check
mypy --strict app/[PATH]/[FileName].py

# 3. Lint
ruff check app/[PATH]/[FileName].py

# 4. Format check
black --check app/[PATH]/[FileName].py

# 5. Tests
pytest tests/[PATH]/test_[FileName].py -v
```

Expected output:
- All QA checks with status
- Code review findings
- Approval decision
```

#### 2.5 Call Auditor

```
Call @agent-tech-lead-orchestrator with template: AUDITOR.md

Context:
- Python File: app/[PATH]/[FileName].py
- Requirements: .requirements/[PATH]/[FileName].requirements.md
- BASE_RULES: .requirements/BASE_RULES.md

Verify:
1. All GAP violations from requirements are fixed
2. No new GAP violations introduced
3. Update requirements document:
   - Change ❌ GAP to ✅ FIXED
   - Add line numbers where fixes were applied
   - Update Audit Status with timestamp
   - Add fixes applied to Notes

Timestamp format: YYYY-MM-DDTHH:MM:SSZ
Get timestamp: date -u +%Y-%m-%dT%H:%M:%SZ

Expected output:
- Audit report
- Requirements document updated
- Audit Status: PASSED or FAILED
```

#### 2.6 Complete or Retry

**If ALL checks pass:**
- Mark task as COMPLETED
- Move to next file

**If ANY check fails:**
- Document what failed
- Retry from Step 2.2 (Implementer)

---

## Available Specialist Agents

| Agent | Role | Template | When Called |
|-------|------|----------|-------------|
| @agent-python-expert | Analyze code + Create requirements + Fix code | REQUIREMENT_EXPERT.md, IMPLEMENTER.md | GAP analysis, Requirements missing, Fixing violations |
| @agent-python-testing-expert | Create/update tests | TESTER.md | After code changes |
| @agent-code-reviewer | Review and QA | CODE_REVIEWER.md | After tests created |
| @agent-code-auditor | Audit compliance | AUDITOR.md | After code review |

---

## Layer-Based Processing Order

**Bottom-up processing reduces dependency conflicts:**

| Order | Layer | Files | Batch | Status |
|-------|-------|-------|-------|--------|
| 1 | L10: Data | 2 | Batch 1 | ⏳ Pending |
| 2 | L9: Core | 29 | Batch 1 | ⏳ Pending |
| 3 | L7: Domain Entities | 8 | Batch 2 | ⏳ Pending |
| 4 | L6: Domain Services/Strategies | 13 | Batch 2 | ⏳ Pending |
| 5 | L8: Application | 12 | Batch 3 | ⏳ Pending |
| 6 | L3-L5: Backtesting | 105 | Batch 4 | ⏳ Pending |
| 7 | L11: Analysis | 9 | Batch 6 | ⏳ Pending |
| 8 | L1: Microstructure | 5 | Batch 6 | ⏳ Pending |
| 9 | L12-L13: API & Middleware | 18 | Batch 5 | ⏳ Pending |

---

## Progress Reporting

After processing each file, report:

```markdown
## Progress Report

**File:** app/[PATH]/[FileName].py
**Status:** [COMPLETED / FAILED / IN_PROGRESS]
**Date:** {{TIMESTAMP}}

**Steps Completed:**
- [x] Requirements document checked/created
- [x] GAP violations analyzed ({{N}} found)
- [x] GAP violations fixed ({{N}} fixed)
- [x] Tests created/updated ({{N}} tests)
- [x] Code review passed (APPROVED)
- [x] Requirements audit passed (PASSED)

**Results:**
- GAPs found: {{N}}
- GAPs fixed: {{N}}
- Tests created/updated: {{N}}
- QA checks: [ALL PASS]

**Next:** [Next file to process]
```

---

## Success Criteria

For EACH file processed:
- [ ] Code analyzed against BASE_RULES.md (96+ rules)
- [ ] Code analyzed against file-specific requirements
- [ ] All GAP violations fixed
- [ ] Syntax check passes
- [ ] Type check passes (if available)
- [ ] Lint check passes (if available)
- [ ] Tests pass
- [ ] Requirements document updated with ✅ FIXED
- [ ] Audit Status updated with timestamp

---

## Priority Order (Within Each Layer)

1. **P0** - Critical (Security, Crashes, Data Loss)
2. **P1** - High (Production Standards)
3. **P2** - Medium (Code Quality)
4. **P3** - Low (Nice to Have)

---

## Task Status Flow

Each task flows through these states:

1. **PLANNED** - File identified for analysis
2. **SCANNING** - LLM analyzing code for GAPs
3. **IN_PROGRESS** - Implementation started
4. **VALIDATING** - Implementation complete, QA in progress
5. **COMPLETED** - All checks pass
6. **FAILED** - Validation failed → Retry

---

**Template Version:** 1.0
**Last Updated:** 2026-02-02
**Orchestrator:** @agent-tech-lead-orchestrator
