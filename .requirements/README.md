# Requirements Documents - AlgoTrading Codebase

This directory contains **deterministic audit requirements** for each production code file in the algoTrading system.

## Purpose

Each `.requirements.md` file documents:
1. **Current Code Analysis** - What the file does, function contracts
2. **Rule Compliance** - Status against 2800+ rules from `docs/auditoria/`
3. **Critical Gaps** - Issues that MUST be fixed (P0-P1)
4. **Acceptance Criteria** - Deterministic, automatable checks
5. **Test Requirements** - Unit and integration test coverage

## Structure

```
.requirements/
├── app/
│   ├── domain/
│   │   ├── entities/           # Domain entities requirements
│   │   ├── value_objects/      # Value objects requirements
│   │   ├── services/           # Domain services requirements
│   │   ├── strategies/         # Trading strategies requirements
│   │   └── repositories/       # Repository interfaces requirements
│   ├── application/
│   │   ├── use_cases/          # Use cases requirements
│   │   ├── services/           # Application services requirements
│   │   ├── routers/            # API routers requirements
│   │   └── dto/                # Data transfer objects requirements
│   └── infrastructure/
│       ├── persistence/        # Database repositories requirements
│       └── external/           # External APIs requirements
└── tests/
    └── requirements/           # Automated acceptance tests
```

## How to Create a Requirements Document

1. **Read the task:**
   ```bash
   view .ralphex/tasks/audit_codebase_requirements.md
   ```

2. **Read the template:**
   ```bash
   view .ralphex/templates/REQUIREMENTS_TEMPLATE.md
   ```

3. **Pick a file to audit:**
   ```bash
   # Start with Phase 1: Domain Layer
   find app/domain/services -name "*.py" | head -1
   ```

4. **Analyze the code:**
   - Extract all function signatures
   - Document preconditions, postconditions, side effects
   - Identify error handling

5. **Read relevant rules:**
   ```bash
   view docs/auditoria/03-solid-principles.md
   view docs/auditoria/02-type-hints.md
   # ... etc
   ```

6. **Create requirements document:**
   - Use the template EXACTLY
   - Mark rules as ✅ OK or ❌ GAP
   - Only include GAPs that add REAL VALUE (skip overengineering)
   - Define deterministic acceptance criteria

7. **Create automated test:**
   ```bash
   # Create test file
   touch tests/requirements/[filename]_requirements_test.py
   ```

## Running Audits

### Check All Requirements Documents

```bash
# Count requirements documents
find .requirements -name "*.requirements.md" | wc -l

# List all requirements documents
find .requirements -name "*.requirements.md"

# Verify completeness
for f in $(find .requirements -name "*.requirements.md"); do
    echo "Checking: $f"
    grep -q "## Acceptance Criteria" "$f" || echo "  ❌ Missing Acceptance Criteria"
    grep -q "## Function Contracts" "$f" || echo "  ❌ Missing Function Contracts"
done
```

### Run Automated Acceptance Tests

```bash
# Run all requirements tests
pytest tests/requirements/ -v

# Run specific requirements test
pytest tests/requirements/mean_variance_optimizer_requirements_test.py -v
```

## Priority Files to Audit

### Phase 1: Domain Layer (Critical Business Logic)

| Priority | File | Status |
|----------|------|--------|
| 1 | `app/domain/services/portfolio_optimization/mean_variance_optimizer.py` | ✅ Done |
| 2 | `app/domain/services/portfolio_optimization/hrp.py` | ⏳ Pending |
| 3 | `app/domain/services/portfolio_optimization/nco.py` | ⏳ Pending |
| 4 | `app/domain/services/portfolio_optimization/black_litterman.py` | ⏳ Pending |
| 5 | `app/domain/strategies/momentum.py` | ⏳ Pending |
| 6 | `app/domain/strategies/mean_reversion.py` | ⏳ Pending |
| 7 | `app/domain/strategies/pairs_trading.py` | ⏳ Pending |

### Phase 2: Application Layer (Use Cases & Coordination)

| Priority | File | Status |
|----------|------|--------|
| 1 | `app/application/use_cases/select_strategy.py` | ⏳ Pending |
| 2 | `app/application/services/input_profile_router.py` | ⏳ Pending |
| 3 | `app/application/services/risk_configurator.py` | ⏳ Pending |
| 4 | `app/application/services/tax_optimizer.py` | ⏳ Pending |

### Phase 3: Backtesting Engine (Validation)

| Priority | File | Status |
|----------|------|--------|
| 1 | `app/backtesting/walk_forward_validator.py` | ⏳ Pending |
| 2 | `app/backtesting/labeling/triple_barrier.py` | ⏳ Pending |
| 3 | `app/backtesting/labeling/meta_labeling.py` | ⏳ Pending |

## Metrics

### Overall Compliance

| Category | Total Files | Audited | Compliant | Has Gaps | % Complete |
|----------|-------------|---------|-----------|----------|------------|
| **Domain Layer** | ~50 | 1 | 1 | 1 | 2% |
| **Application Layer** | ~30 | 0 | 0 | 0 | 0% |
| **Infrastructure** | ~40 | 0 | 0 | 0 | 0% |
| **Backtesting** | ~25 | 0 | 0 | 0 | 0% |
| **TOTAL** | **~145** | **1** | **1** | **2** | **<1%** |

*Last updated: 2026-02-01*

---

## Recent Updates

### 2026-02-01
- ✅ Created `CRITICAL_RULES.md` with 50+ universal rules organized in 12 categories
- ✅ Created Python requirements template (`REQUIREMENTS_TEMPLATE_PYTHON.md`)
- ✅ First requirements document: `mean_variance_optimizer.requirements.md`
  - 7 acceptance criteria defined
  - 3 gaps identified (PSD validation, error logging, magic numbers)
  - 8 test cases specified

## Rules Reference

All rules are documented in `docs/auditoria/`:

- **Python QA (26 files, ~400 rules):** Code quality, style, testing
- **Architecture (8 files, ~150 rules):** SOLID, Clean Architecture, DDD
- **Trading (50 files, ~2200 rules):** Strategies, risk management, optimization

## Status Legend

| Icon | Meaning |
|------|---------|
| ⏳ | Pending - Not yet audited |
| 🔄 | In Progress - Currently being audited |
| ✅ | Compliant - All critical rules passed |
| ⚠️ | Has Gaps - Non-critical issues found |
| ❌ | Critical Issues - P0/P1 gaps must be fixed |

## Quick Start

To start the audit process:

```bash
# 1. Read the task instructions
view .ralphex/tasks/audit_codebase_requirements.md

# 2. Read the template
view .ralphex/templates/REQUIREMENTS_TEMPLATE.md

# 3. Pick the first file to audit
# Start with: app/domain/services/portfolio_optimization/mean_variance_optimizer.py

# 4. Create the requirements document
# Follow the template and fill in all sections

# 5. Create automated acceptance test
# Tests should verify all acceptance criteria are met
```

---

**IMPORTANT:** This is a manual, incremental process. Each file should be audited ONE AT A TIME, with full analysis and documentation before moving to the next file.

**DO NOT** use automated tools to generate these documents without proper human review. The value comes from careful analysis of the code against the rules, not from automatic documentation generation.
