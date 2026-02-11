# config/__init__.py

## Purpose
Configuration module initialization that provides unified access to both Settings (from config.py) and ProfileConfigLoader.

---

## Type Definitions / Data Classes

This module re-exports types from:
- `app.core.config` (config.py): Settings, get_settings, get_database_url, get_redis_url
- `.profile_config_loader`: ProfileConfigLoader and related functions

---

## Function Signatures (Contracts)

This module only provides imports and re-exports. No original functions.

---

## Acceptance Criteria
- [ ] Correctly imports Settings and get_settings from sibling config.py
- [ ] Re-exports all profile config loader functions
- [ ] Module import works without errors
- [ ] No circular imports

---

## Audit Status

| Field | Value |
|-------|-------|
| **Last Audit Date** | 2026-02-04T00:00:00Z |
| **Audit Status** | AUDITED |
| **BASE_RULES Version** | a1b2c3d (2026-01-10) |
| **Audited By** | @agent-code-auditor |
| **GAPs Fixed** | 0 / 0 total |

---

## Critical Rules (MUST NOT BREAK)

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CC-001 | BASE_RULES | Descriptive names | ✅ OK |
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - Only re-exports |
| ARCH-001 | BASE_RULES | Layered architecture | ✅ OK - Infrastructure layer |

---

## Dependencies
- **External:** sys, pathlib, importlib
- **Internal:**
  - app.core.config (sibling config.py file)
  - .profile_config_loader

---

## Required Tests
- **tests/unit/core/config/test_init.py:**
  - Test module imports successfully
  - Test Settings is re-exported
  - Test get_settings is re-exported
  - Test ProfileConfigLoader is re-exported

---

## Notes
- **Dynamic Import:** Uses importlib to load sibling config.py to avoid naming conflicts
- **Re-exports:** Provides unified interface to configuration system
---
