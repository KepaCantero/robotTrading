# Task: Audit and Fix Codebase GAP Violations

## Overview

Systematic audit and fix workflow for Python files. Uses **LLM-based code analysis** via @agent-python-expert to find actual GAP violations against **TWO sources**:

1. **BASE_RULES.md** - 96+ universal rules that apply to all files
2. **File-specific requirements** - Rules specific to each file in its `.requirements/[PATH]/[FileName].requirements.md`

## Context

- **Repository:** `/Users/kepa.cantero/Projects/algoTrading`
- **Working Directory:** `/Users/kepa.cantero/Projects/algoTrading`
- **Branch:** `main`
- **BASE_RULES:** `.requirements/BASE_RULES.md` (96+ universal rules)
- **File Requirements:** `.requirements/[PATH]/[FileName].requirements.md` (file-specific rules)
- **Task Templates:** `.tasks/templates/`

## Rule Sources

### Source 1: BASE_RULES.md (Universal Rules)
- 96+ rules across 14 categories
- Apply to ALL Python files in the codebase
- Categories: Logging, Type Hints, Error Handling, Trading, Security, Architecture, Performance, etc.

### Source 2: File-Specific Requirements
- Located in `.requirements/[PATH]/[FileName].requirements.md`
- Contains "Critical Rules (MUST NOT BREAK)" table
- Each rule has:
  - Rule ID (e.g., LOG-001, CC-006)
  - Source (BASE_RULES or file-specific)
  - Requirement description
  - Current Status (✅ OK / ❌ GAP / ⚠️ NOT APPLIED / ⚠️ PARTIAL)

## Specialist Agents

| Agent | Role | When Called |
|-------|------|-------------|
| @agent-tech-lead-orchestrator | Coordinator | Always - delegates to specialists |
| @agent-python-expert | Analyze code + Implement fixes | GAP analysis + fixing violations |
| @agent-requirement-expert | Create requirements docs | Requirements document missing |
| @agent-python-testing-expert | Create/update tests | After code changes |
| @agent-code-reviewer | Review and QA | After tests created |
| @agent-code-auditor | Audit compliance | After code review |

## Workflow

The Tech Lead Orchestrator coordinates this workflow for EACH file:

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
│  │  │ @requirement-expert│  │                  │    │                │ │   │
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

## Parallelization Strategy

**MAXIMUM PARALLELIZATION - Execute as many tasks concurrently as possible:**

### Level 1: Batch-Level Parallelization (Multiple Files)

Files within the **same layer/batch** can be processed in **parallel** when they have **no dependencies**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PARALLEL BATCH PROCESSING                               │
│                                                                             │
│  Batch 1 (L10: Data Layer - 2 files):                                     │
│  ┌──────────────────────────┐  ┌──────────────────────────┐               │
│  │ models.py                │  │ repositories.py          │               │
│  │ (Scan→Fix→Test→Review)   │  │ (Scan→Fix→Test→Review)   │               │
│  └──────────────────────────┘  └──────────────────────────┘               │
│           ↓                                                           ↓    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  BOTH COMPLETE → Next Batch                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Batch 2 (L9: Core Layer - 29 files):                                     │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ... (parallel groups of 5-10)     │
│  │file1 │ │file2 │ │file3 │ │file4 │                                    │
│  └──────┘ └──────┘ └──────┘ └──────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Level 2: Inter-File Parallelization (Pipeline)

**While auditing File A, scan File B:**

```
File A: [Scanned] → [Fixed] → [Tested] → [Reviewed] → [AUDITING ← YOU ARE HERE]
                                                              ↓
File B: [SCANNING IN PARALLEL ← START NOW]
File C: [WAITING]
```

### Level 3: Intra-File Parallelization

**Within a single file, these can run in parallel:**
- Create requirements document + Scan for GAPs (if starting fresh)
- Update requirements + Run QA checks (after fixes)

### Level 4: Cross-Layer Parallelization

**Different layers with NO dependencies can run in parallel:**
- L10 (Data) and L9 (Core) have minimal dependencies → can overlap
- L7 (Domain Entities) and L6 (Domain Services) → can overlap partially

### Parallelization Rules

| Scenario | Can Parallelize? | Limit |
|----------|-----------------|-------|
| Same layer, different files | ✅ YES | 5-10 files |
| Same file, dependent steps | ❌ NO | N/A |
| Same file, independent steps | ✅ YES | 2-3 tasks |
| File A audit + File B scan | ✅ YES | 2 files |
| Different layers (no deps) | ✅ YES | 2 layers |
| Different layers (has deps) | ⚠️ CAUTION | 1 layer at a time |

### Execution Command Pattern

**ALWAYS use single message with multiple Task calls:**

```python
# ✅ CORRECT - Parallel execution
Task(agent=python-expert, file="models.py")      # In parallel
Task(agent=python-expert, file="repositories.py") # In parallel
Task(agent=python-expert, file="migrations.py")   # In parallel

# ❌ WRONG - Sequential (wastes time)
Task(agent=python-expert, file="models.py")      # Wait...
# Then call next task...
```

### Parallel Batch Processing Example

**Batch 1 (L10: Data Layer) - Process 2 files in parallel:**

```
# Send ALL in one message:
┌─────────────────────────────────────────────────────────────────────────────┐
│  Task(agent=python-expert, "Analyze models.py for GAPs")                  │
│  Task(agent=python-expert, "Analyze repositories.py for GAPs")             │
└─────────────────────────────────────────────────────────────────────────────┘

# After both complete, send fixes in parallel:
┌─────────────────────────────────────────────────────────────────────────────┐
│  Task(agent=python-expert, "Fix models.py GAPs")                          │
│  Task(agent=python-expert, "Fix repositories.py GAPs")                     │
└─────────────────────────────────────────────────────────────────────────────┘

# Code review in parallel:
┌─────────────────────────────────────────────────────────────────────────────┐
│  Task(agent=code-reviewer, "Review models.py")                            │
│  Task(agent=code-reviewer, "Review repositories.py")                       │
└─────────────────────────────────────────────────────────────────────────────┘

# Audit in parallel:
┌─────────────────────────────────────────────────────────────────────────────┐
│  Task(agent=python-expert, "Audit models.py compliance")                   │
│  Task(agent=python-expert, "Audit repositories.py compliance")              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Instructions

### Step 0: List Files Needing Audit (Script-Based)

**Use the script to find files that need auditing:**

```bash
# List all files that need audit (checks timestamps)
python scripts/list_files_for_audit.py

# List specific batch
python scripts/list_files_for_audit.py --batch 1

# List with JSON output for automation
python scripts/list_files_for_audit.py --format json

# Change max age for PASSED audits (default: 7 days)
python scripts/list_files_for_audit.py --max-age 30
```

**The script checks:**
1. If requirements file exists
2. If "Audit Status" is PASSED and recent (< 7 days) → SKIP
3. If "Audit Status" is PASSED but old (> 7 days) → RE-AUDIT
4. If "Audit Status" is NEEDS_AUDIT or FAILED → AUDIT
5. If no requirements file → CREATE + AUDIT

**Output:**
- Total files per batch
- Files needing audit (with reason)
- Files already audited (recent) - skipped

### Step 1: Scan for GAP Violations (LLM-Based)

**Call @agent-python-expert to analyze code against BOTH rule sources:**

```
Analyze app/[PATH]/[FileName].py for GAP violations.

1. Read BASE_RULES.md: .requirements/BASE_RULES.md (96+ universal rules)
2. Read file requirements: .requirements/[PATH]/[FileName].requirements.md (if exists)
3. Read Python file: app/[PATH]/[FileName].py

For EACH rule from BOTH sources:
A. From BASE_RULES.md (universal rules):
   1. Check if the rule applies to this file type/context
   2. Verify if the code follows the rule
   3. Report violations

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
   - Current status (❌ VIOLATED / ✅ OK / ⚠️ NOT APPLIED)

Return a structured list of GAP violations found, grouped by source.
```

**Output format:**
Use `.tasks/templates/GAP_ANALYSIS_OUTPUT.md` template for the report.

The report must include:
- Summary table with violation counts by priority and source
- Violations grouped by: BASE_RULES.md (Universal) vs File-Specific Requirements
- For each violation: Rule ID, line number, description, code snippet, fix required
- Status indicators: ❌ VIOLATED, ✅ OK, ⚠️ NOT APPLIED, ⚠️ PARTIAL, ✅ FIXED

### Step 2: Process Each File

For each file with GAPs, follow this sequence:

#### 2.1 Check Requirements Exist

**IF requirements document does NOT exist:**

```
Call @agent-requirement-expert

Create requirements document for: app/[PATH]/[FileName].py

Use template: .tasks/templates/REQUIREMENT_TEMPLATE.md
Read BASE_RULES.md: .requirements/BASE_RULES.md
Read Python file: app/[PATH]/[FileName].py
Create comprehensive requirements document
Save to: .requirements/[PATH]/[FileName].requirements.md
```

#### 2.2 Call Implementer

```
Call @agent-python-expert

Fix GAP violations in: app/[PATH]/[FileName].py

GAPs from analysis:
- LOG-001:45: f-string in logging call
- LOG-004:89: Exception logging without exc_info=True
- CC-006:123: Generic Exception catching

Use Minimal mode - only fix the specific GAP violations reported.
```

#### 2.3 Call Tester

```
Call @agent-python-testing-expert

Create/update tests for: app/[PATH]/[FileName].py

Changes: [Summary of changes made]

Create or update unit tests to cover the fixes
Test file: tests/[PATH]/test_[FileName].py
```

#### 2.4 Call Code Reviewer

```
Call @agent-code-reviewer

Review code for: app/[PATH]/[FileName].py

Run QA commands:
```bash
cd /Users/kepa.cantero/Projects/algoTrading

# 1. Syntax check
python -m py_compile app/[PATH]/[FileName].py

# 2. Type check (if mypy available)
mypy --strict app/[PATH]/[FileName].py

# 3. Lint (if ruff available)
ruff check app/[PATH]/[FileName].py

# 4. Format check (if black available)
black --check app/[PATH]/[FileName].py

# 5. Tests
pytest tests/[PATH]/test_[FileName].py -v
```

Report findings and validate all checks pass
```

#### 2.5 Call Auditor

```
Call @agent-code-auditor

Audit requirements compliance for: app/[PATH]/[FileName].py

1. Verify BASE_RULES.md compliance:
   - Re-check all 96+ universal rules
   - Confirm all violations are fixed

2. Verify file-specific requirements:
   - Read: .requirements/[PATH]/[FileName].requirements.md
   - Check "Critical Rules (MUST NOT BREAK)" table
   - Verify all ❌ GAP violations are now ✅ FIXED

3. Update requirements document:
   - Change ❌ GAP to ✅ FIXED for resolved violations
   - Add line numbers where fixes were applied
   - Update ⚠️ PARTIAL to ✅ OK if fully resolved
   - Document any new violations found

Example update in requirements.md:
| LOG-001 | BASE_RULES | Structured logging | ✅ FIXED - Fixed at line 45 |
| CC-006 | BASE_RULES | Explicit error handling | ✅ FIXED - Fixed at lines 67, 89 |
```

#### 2.6 Complete or Retry

**If ALL checks pass:**
- Mark task as COMPLETED
- Move to next file

**If ANY check fails:**
- Document what failed
- Retry from Step 2.2 (Implementer)

## Fix Pattern Reference

For common GAP violation fixes, use `.tasks/templates/GAP_FIX_PATTERNS.md` template which includes:

- LOG-001: Structured Logging
- LOG-004: Exception Logging with Stack Traces
- CC-006: Explicit Error Handling
- TYP-001: Missing Return Type Annotations
- TYP-003: Using Any Without Justification
- TRD-001: Validate Mathematical Relationships
- TRD-005: Price Validation
- SEC-001: No Hardcoded Secrets
- ARCH-004: Function Length Limits

Each pattern shows ❌ BAD vs ✅ GOOD with explanations.

---

## QA Commands Reference

These commands should be run for each file after fixing:

```bash
# 1. Syntax check (always available)
python -m py_compile [FILE]

# 2. Type check (if mypy installed)
mypy --strict [FILE]

# 3. Lint (if ruff installed)
ruff check [FILE]

# 4. Format check (if black installed)
black --check [FILE]

# 5. Tests (if test file exists)
pytest [TEST_FILE] -v
```

## Processing Order: Layer-Based (Bottom-Up)

**Process layers from LOWEST to HIGHEST to reduce dependency conflicts:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LAYER DEPENDENCY ORDER                              │
│  (Process from bottom to top)                                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L10: Data Layer                                                    │   │
│  │  ├─ app/database/*.py                                              │   │
│  │  └─ Dependencies: None (lowest level)                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↑                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L9: Core Layer                                                     │   │
│  │  ├─ app/core/*.py                                                   │   │
│  │  └─ Dependencies: Database                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↑                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L7: Domain Entities                                               │   │
│  │  ├─ app/domain/entities/*.py                                       │   │
│  │  └─ Dependencies: Core                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↑                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L6: Domain Services & Strategies                                  │   │
│  │  ├─ app/domain/services/*.py                                       │   │
│  │  ├─ app/domain/strategies/*.py                                     │   │
│  │  └─ Dependencies: Domain Entities                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↑                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L8: Application Layer                                             │   │
│  │  ├─ app/application/**/*.py                                        │   │
│  │  └─ Dependencies: Domain Services                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↑                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L3-L5: Backtesting Layer                                          │   │
│  │  ├─ app/backtesting/**/*.py                                         │   │
│  │  └─ Dependencies: Domain, Application                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↑                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L11: Analysis Layer                                                │   │
│  │  ├─ app/analysis/**/*.py                                            │   │
│  │  └─ Dependencies: Domain                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↑                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L1: Market Microstructure                                         │   │
│  │  ├─ app/market_microstructure/**/*.py                               │   │
│  │  └─ Dependencies: Data                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   ↑                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L12-L13: API & Middleware (Highest Level)                         │   │
│  │  ├─ app/api/*.py                                                    │   │
│  │  ├─ app/middleware/*.py                                             │   │
│  │  └─ Dependencies: ALL lower layers                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Batch Processing Order (Bottom-Up):**

| Order | Layer | Files | Script | Status |
|-------|-------|-------|--------|--------|
| 1 | L10: Data | 2 | Batch 1 | ⏳ Pending |
| 2 | L9: Core | 29 | Batch 1 | ⏳ Pending |
| 3 | L7: Domain Entities | 8 | Batch 2 | ⏳ Pending |
| 4 | L6: Domain Services/Strategies | 13 | Batch 2 | ⏳ Pending |
| 5 | L8: Application | 12 | Batch 3 | ⏳ Pending |
| 6 | L3-L5: Backtesting | 105 | Batch 4 | ⏳ Pending |
| 7 | L11: Analysis | 9 | Batch 6 | ⏳ Pending |
| 8 | L1: Microstructure | 5 | Batch 6 | ⏳ Pending |
| 9 | L12-L13: API & Middleware | 18 | Batch 5 | ⏳ Pending |

**Why Bottom-Up?**
- Lower layers have fewer dependencies
- Fixing base layers first prevents cascading fixes
- Higher layers depend on lower layers being correct
- Reduces need to re-audit after fixing dependencies

## Priority Order (Within Each Layer)

Within each layer, process by PRIORITY:

1. **P0** - Critical (Security, Crashes, Data Loss)
2. **P1** - High (Production Standards)
3. **P2** - Medium (Code Quality)
4. **P3** - Low (Nice to Have)

## Task Status Flow

Each task flows through these states:

1. **PLANNED** - File identified for analysis
2. **SCANNING** - LLM analyzing code for GAPs
3. **IN_PROGRESS** - Implementation started
4. **VALIDATING** - Implementation complete, QA in progress
5. **COMPLETED** - All checks pass
6. **FAILED** - Validation failed → Retry

## Progress Tracking

Track completed files:

### 2026-02-02
- [ ] P0: 0/?? files completed
- [ ] P1: 0/?? files completed
- [ ] P2: 0/?? files completed
- [ ] P3: 0/?? files completed

## Files to Process

**Use the script to get the current list:**

```bash
# Get current list of files needing audit
python scripts/list_files_for_audit.py

# Get JSON for automation
python scripts/list_files_for_audit.py --format json -o files_to_audit.json
```

**Script automatically:**
1. Scans all Python files in the codebase
2. Checks requirements files for audit timestamps
3. Skips files with recent PASSED audits
4. Returns only files that need auditing

**Current status:**
```bash
# Run this to see current status
python scripts/list_files_for_audit.py
```

## Success Criteria

For EACH file processed:
- [ ] Code analyzed against BASE_RULES.md (96+ rules)
- [ ] All GAP violations fixed
- [ ] Syntax check passes
- [ ] Type check passes (if available)
- [ ] Lint check passes (if available)
- [ ] Tests pass
- [ ] Requirements document updated with ✅ FIXED

---

**Orchestrator:** @agent-tech-lead-orchestrator
**Created:** 2026-02-02
**Status:** PLANNED
**Method:** LLM-based code analysis via Task tool
