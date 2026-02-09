# Ralph User Guide

**Fecha:** 2026-02-08
**Version:** 1.0

---

## What is Ralph

Ralph is a task automation system that:

1. Defines tasks in YAML templates
2. Processes results with standardized JSON output
3. Passes data between agents via event-driven pipeline
4. Emits completion promises for automatic verification

---

## Quick Start

### Run a Task

```bash
ralph run .ralph/ralph_tasks/01_compliance_engine_refactor.yml
```

### Run a Pipeline

```bash
ralph pipeline run .ralph/my_pipeline.yml
```

### Check Progress

```bash
ralph pipeline status .ralph/my_pipeline.yml
```

---

## Task Structure

```
.ralph/ralph_tasks/
├── 01_compliance_engine_refactor.yml
└── prompts/
    └── 01_compliance_engine_refactor.md
```

---

## For Complete Documentation

See the main README at ../README.md

---

**Last updated:** 2026-02-08
