# Ralph System Architecture Diagram

**Date:** 2026-02-08

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RALPH WRAPPER SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐              │
│  │   Task 1     │────▶│   Task 2     │────▶│   Task 3     │              │
│  │              │     │              │     │              │              │
│  │  Config:     │     │  Config:     │     │  Config:     │              │
│  │  task.yml    │     │  task.yml    │     │  task.yml    │              │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘              │
│         │                     │                     │                       │
│         ▼                     ▼                     ▼                       │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐              │
│  │   Agent 1    │────▶│   Agent 2    │────▶│   Agent 3    │              │
│  │              │     │              │     │              │              │
│  │  Hat:        │     │  Hat:        │     │  Hat:        │              │
│  │  Implementer │     │  Validator   │     │  Reviewer    │              │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘              │
│         │                     │                     │                       │
│         ▼                     ▼                     ▼                       │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐              │
│  │  Output 1    │────▶│  Output 2    │────▶│  Output 3    │              │
│  │              │     │              │     │              │              │
│  │  JSON:       │     │  JSON:       │     │  JSON:       │              │
│  │  task_id     │     │  task_id     │     │  task_id     │              │
│  │  status      │     │  status      │     │  status      │              │
│  │  results     │     │  results     │     │  results     │              │
│  │  next_steps  │     │  next_steps  │     │  next_steps  │              │
│  └──────────────┘     └──────────────┘     └──────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Input/Output Flow

### Agent Input Template

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT INPUT DATA                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐             │
│  │ Previous Results │    │   Requirements    │             │
│  │                  │    │                   │             │
│  │ - files[]        │    │ - spec_file       │             │
│  │ - metrics{}      │    │ - templates[]     │             │
│  │ - validation{}   │    │ - constraints[]   │             │
│  └──────────────────┘    └──────────────────┘             │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐             │
│  │   Checkpoint     │    │     Context       │             │
│  │                  │    │                   │             │
│  │ - phase          │    │ - current_task    │             │
│  │ - completed[]    │    │ - task_type       │             │
│  │ - pending[]      │    │ - phase           │             │
│  └──────────────────┘    └──────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Agent Output Template

```
┌─────────────────────────────────────────────────────────────┐
│                   AGENT OUTPUT DATA                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐             │
│  │      Status      │    │     Results       │             │
│  │                  │    │                   │             │
│  │ - state          │    │ - files[]         │             │
│  │ - success        │    │ - metrics{}       │             │
│  │ - completion%    │    │ - custom_data{}   │             │
│  └──────────────────┘    └──────────────────┘             │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐             │
│  │    Validation    │    │    Next Steps     │             │
│  │                  │    │                   │             │
│  │ - total_checks   │    │ - next_task       │             │
│  │ - passed         │    │ - ready           │             │
│  │ - failed         │    │ - required_data   │             │
│  └──────────────────┘    └──────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Template System

```
┌─────────────────────────────────────────────────────────────┐
│                    RALPH TEMPLATES                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              HAT TEMPLATES (Agents)                  │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │                                                      │   │
│  │  validation_hat.yml         ──▶  Validates files    │   │
│  │  implementer_hat.yml        ──▶  Implements code    │   │
│  │  final_reviewer_hat.yml     ──▶  Reviews results    │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            DATA FLOW TEMPLATES                       │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │                                                      │   │
│  │  task_output_template.yml    ──▶  Standardized      │   │
│  │                                  output format       │   │
│  │  agent_input_template.yml    ──▶  Standardized      │   │
│  │                                  input format        │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         CONFIGURATION TEMPLATES                      │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │                                                      │   │
│  │  task_config_template.yml     ──▶  Create new       │   │
│  │                                  tasks               │   │
│  │  pipeline_coordinator_template.yml ──▶  Create      │   │
│  │                                  pipelines           │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              BASE CONFIGURATION                      │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │                                                      │   │
│  │  ralph_base.yml             ──▶  Shared settings    │   │
│  │                                  - Event loop        │   │
│  │                                  - CLI               │   │
│  │                                  - Memories          │   │
│  │                                  - Instructions      │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Pipeline Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│              PIPELINE EXECUTION FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  START                                                      │
│   │                                                         │
│   ▼                                                         │
│  ┌─────────────────┐                                       │
│  │ Load Pipeline   │                                       │
│  │ Configuration   │                                       │
│  └────────┬────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                       │
│  │ Initialize Task │◀──────────────┐                       │
│  │      1          │               │                       │
│  └────────┬────────┘               │                       │
│           │                        │                       │
│           ▼                        │                       │
│  ┌─────────────────┐               │                       │
│  │  Process with   │               │                       │
│  │    Agent 1      │               │                       │
│  └────────┬────────┘               │                       │
│           │                        │                       │
│           ▼                        │                       │
│  ┌─────────────────┐               │                       │
│  │  Generate       │               │                       │
│  │  Output 1       │               │                       │
│  └────────┬────────┘               │                       │
│           │                        │                       │
│           ▼                        │                       │
│  ┌─────────────────┐               │                       │
│  │  Emit Event:    │               │                       │
│  │  task.complete  │───────────────┘                       │
│  └────────┬────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                       │
│  │ Initialize Task │◀──────────────┐                       │
│  │      2          │               │                       │
│  │  (Input from    │               │                       │
│  │   Output 1)     │               │                       │
│  └────────┬────────┘               │                       │
│           │                        │                       │
│           ▼                        │                       │
│  ┌─────────────────┐               │                       │
│  │  Process with   │               │                       │
│  │    Agent 2      │               │                       │
│  └────────┬────────┘               │                       │
│           │                        │                       │
│           ▼                        │                       │
│  ┌─────────────────┐               │                       │
│  │  Generate       │               │                       │
│  │  Output 2       │               │                       │
│  └────────┬────────┘               │                       │
│           │                        │                       │
│           ▼                        │                       │
│  ┌─────────────────┐               │                       │
│  │  Emit Event:    │               │                       │
│  │  task.complete  │───────────────┘                       │
│  └────────┬────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                       │
│  │   Continue...   │                                       │
│  │   (Repeat for   │                                       │
│  │   all tasks)    │                                       │
│  └────────┬────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                       │
│  │  Pipeline       │                                       │
│  │  Complete       │                                       │
│  └────────┬────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  END                                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Event System

```
┌─────────────────────────────────────────────────────────────┐
│                   EVENT SYSTEM                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │    Agent     │    │   Ralph      │    │    Next      │ │
│  │              │───▶│   Wrapper    │───▶│    Agent     │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│       │                    │                    │          │
│       │                    │                    │          │
│       ▼                    ▼                    ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐│
│  │   Emits:     │    │  Processes:  │    │  Triggers:   ││
│  │              │    │              │    │              ││
│  │ - task.next  │    │ - Save       │    │ - Waits for  ││
│  │   _phase     │    │   output     │    │   event      ││
│  │              │    │ - Update     │    │              ││
│  │ - task       │    │   checkpoint │    │ - Reads      ││
│  │   .complete  │    │ - Emit next  │    │   input      ││
│  │              │    │   event      │    │              ││
│  │ - task       │    │              │    │              ││
│  │   .blocked   │    │              │    │              ││
│  │              │    │              │    │              ││
│  └──────────────┘    └──────────────┘    └──────────────┘│
│                                                             │
│  Event Flow:                                                │
│  1. Agent completes work                                    │
│  2. Emits event (e.g., task.complete)                       │
│  3. Ralph wrapper saves output                              │
│  4. Ralph emits next event                                  │
│  5. Next agent triggers on event                            │
│  6. Next agent reads output as input                        │
│  7. Process repeats                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
.ralph/
│
├── docs/                          # Documentation
│   ├── analysis/                  # Analysis documents
│   ├── architecture/              # Architecture docs
│   ├── refactoring/               # Refactoring docs
│   ├── requirements/              # Requirements
│   ├── RALPH_USER_GUIDE.md       # User guide
│   └── RALPH_SYSTEM_DIAGRAM.md   # This file
│
├── ralph_base.yml                 # Base configuration
│
├── ralph_templates/               # Reusable templates
│   ├── validation_hat.yml         # Validator hat
│   ├── implementer_hat.yml        # Implementer hat
│   ├── final_reviewer_hat.yml     # Reviewer hat
│   ├── task_output_template.yml   # Output format
│   ├── task_config_template.yml   # Task config
│   ├── pipeline_coordinator       # Pipeline config
│   └── data_templates/
│       └── agent_input_template.yml # Input format
│
├── ralph_tasks/                   # Task configurations
│   ├── 01_compliance_engine_refactor.yml
│   └── prompts/
│       └── 01_compliance_engine_refactor.md
│
├── outputs/                       # Generated outputs
├── checkpoints/                   # Generated checkpoints
├── logs/                          # Execution logs
├── progress/                      # Progress tracking
│
└── README.md                      # Main documentation
```

---

**Last updated:** 2026-02-08
