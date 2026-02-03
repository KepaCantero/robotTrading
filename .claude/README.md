# Claude Agent Task Structure

This directory contains the organized structure for agent workflows, templates, and tasks.

## Directory Structure

```
.claude/
├── base/                   # Base task templates (extended by specific tasks)
│   ├── REFACTOR_BASE.md   # Base template for all refactoring tasks
│   └── audit_and_fix_gaps.md  # Base template for GAP audit workflow
│
├── tasks/                  # Specific task definitions
│   ├── refactor_portfolio_di.md
│   ├── refactor_signals_di.md
│   ├── refactor_strategies_di.md
│   ├── refactor_health_db_layer.md
│   └── REFACTORING_TASKS_INDEX.md
│
├── roles/                  # Agent role definitions
│   ├── AUDITOR.md          # @agent-code-auditor role definition
│   ├── CODE_REVIEWER.md    # @agent-code-reviewer role definition
│   ├── IMPLEMENTER.md      # @agent-backend-developer role definition
│   ├── TESTER.md           # @agent-python-testing-expert role definition
│   ├── REQUIREMENT_EXPERT.md  # @agent-requirement-expert role definition
│   └── TECH_LEAD_ORCHESTRATOR.md  # @agent-tech-lead-orchestrator role definition
│
└── templates/              # Data format templates (only variable definitions)
    ├── refactor/           # Refactoring workflow data templates
    │   ├── IMPLEMENTER_DATA.md      # Data format for Step 1: Implementer
    │   ├── TESTER_DATA.md           # Data format for Step 2: Tester
    │   ├── CODE_REVIEWER_DATA.md    # Data format for Step 3: Code Reviewer
    │   └── AUDITOR_DATA.md          # Data format for Step 4: Auditor
    │
    └── gap/                 # GAP audit workflow templates
        ├── GAP_ANALYSIS_OUTPUT.md   # Output format for GAP analysis
        ├── GAP_FIX_PATTERNS.md      # Common fix patterns for GAP violations
        └── REQUIREMENT_TEMPLATE.md  # Template for requirements documents
```

## How It Works

### 1. Task Definition Pattern

Each specific task in `tasks/` follows this pattern:

```markdown
# Task: [Description]

## Extends
- **Base:** `.claude/base/[BASE_FILE].md`
- **Orchestrator:** @agent-tech-lead-orchestrator

## Context Variables (Pre-filled)
- `{{VARIABLE}}` = `actual value`

## Filled Templates (Pre-filled with Context Variables)
### Step 1: [Role]
**Template:** `.claude/templates/[workflow]/[ROLE]_DATA.md`
**All variables pre-filled:** [actual values instead of {{placeholders}}]
```

### 2. Agent Invocation Flow

When invoking an agent for a task:

```
User Request
    ↓
@agent-tech-lead-orchestrator
    ↓
Reads task file from `.claude/tasks/[task].md`
    ↓
Extracts pre-filled context variables
    ↓
Delegates to specialist agent with:
  - Role definition from `.claude/roles/[ROLE].md`
  - Data template from `.claude/templates/[workflow]/[ROLE]_DATA.md`
  - Pre-filled variables from task file
    ↓
Specialist agent executes and returns output
```

### 3. Template Types

**Role Definitions (`roles/`):**
- Full instructions for each agent type
- Steps to follow
- Quality checklists
- Output format requirements

**Data Templates (`templates/`):**
- Only variable definitions and output formats
- No detailed instructions (those are in roles)
- Used to fill context for each agent invocation

### 4. Step-by-Step Communication

Each step in a workflow passes data to the next:

```
Step 1: Implementer → Output includes changes summary
                      ↓
Step 2: Tester     → Uses Step 1 output as {{CHANGES_SUMMARY}}
                      ↓
Step 3: Reviewer   → Uses Step 1 and Step 2 outputs
                      ↓
Step 4: Auditor    → Uses all previous outputs
```

## Quick Reference

| File | Purpose | When Used |
|------|---------|-----------|
| `base/REFACTOR_BASE.md` | Base refactoring workflow | All refactor tasks |
| `base/audit_and_fix_gaps.md` | Base GAP audit workflow | GAP audit tasks |
| `roles/[ROLE].md` | Agent role definition | When invoking agent |
| `templates/refactor/[ROLE]_DATA.md` | Refactoring data format | Refactoring workflow |
| `templates/gap/*.md` | GAP audit templates | GAP audit workflow |
| `tasks/[task].md` | Specific task definition | Executing specific task |

## Creating New Tasks

1. Copy relevant base template from `base/`
2. Fill in context variables with actual values
3. Reference appropriate data templates from `templates/`
4. Save to `tasks/` directory
5. Update index file if applicable

---

**Last Updated:** 2026-02-02
**Structure Version:** 2.0
