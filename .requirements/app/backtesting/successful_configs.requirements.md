# successful_configs.py

## Purpose
Manage configurations that have demonstrated good performance in backtests - save, load, compare, and retrieve successful backtest configurations for reuse.

---

## Type Definitions / Data Classes

No dataclasses defined - uses dictionaries for config records.

### Config Record Structure (saved to JSON)
```python
{
    'id': str,                    # Unique ID (name_timestamp)
    'name': str,                  # Human-readable name
    'description': str,           # Optional description
    'tags': List[str],            # Categorization tags
    'timestamp': str,             # ISO format timestamp
    'config': dict,               # Complete YAML config as dict
    'metrics': dict,              # Performance metrics (sharpe, return, etc.)
    'before_training_metrics': dict,   # Optional baseline metrics
    'after_training_metrics': dict,    # Optional post-training metrics
    'improvement_pct': dict,      # Improvement by metric
    # Indexed fields for filtering/searching:
    'sharpe_ratio': float,
    'return_pct': float,
    'win_rate': float,
    'max_drawdown': float,
    'total_pnl': float,
}
```

---

## Function Signatures (Contracts)

### `SuccessfulConfigManager.__init__(storage_dir: Optional[Union[str, Path]] = None)`
**Pre:** None
**Post:** Manager initialized, storage_dir created
**Raises:** OSError on directory creation failure
**Retry:** No
**Side Effects:** Creates storage_dir and loads existing configs

### `_load_configs() -> List[Dict[str, Any]]`
**Pre:** None
**Post:** Returns list of config records from JSON file
**Raises:** None (returns [] on file not found or parse error)
**Retry:** No
**Side Effects:** Reads from configs_file

### `_save_configs() -> None`
**Pre:** self._configs populated
**Post:** Configs saved to JSON file
**Raises:** FileNotFoundError, ValueError, KeyError, TypeError on write error
**Retry:** No
**Side Effects:** Overwrites configs_file

### `save_config(name: str, config: Dict[str, Any], metrics: Dict[str, Any], description: Optional[str] = None, tags: Optional[List[str]] = None, before_training_metrics: Optional[Dict[str, Any]] = None, after_training_metrics: Optional[Dict[str, Any]] = None, improvement_pct: Optional[Dict[str, float]] = None) -> str`
**Pre:** name non-empty, config and metrics valid dicts
**Post:** Config saved, returns config_id
**Raises:** None (logs on error)
**Retry:** No
**Side Effects:** Updates _configs, writes to JSON and individual file

### `load_config(config_id: Optional[str] = None, name: Optional[str] = None) -> Optional[Dict[str, Any]]`
**Pre:** config_id or name provided
**Post:** Returns config record or None if not found
**Raises:** None
**Retry:** No
**Side Effects:** None

### `list_configs(min_sharpe: Optional[float] = None, min_return: Optional[float] = None, tags: Optional[List[str]] = None, sort_by: str = 'sharpe_ratio', limit: Optional[int] = None) -> List[Dict[str, Any]]`
**Pre:** None
**Post:** Returns filtered and sorted list of configs
**Raises:** None
**Retry:** No
**Side Effects:** None

### `delete_config(config_id: Optional[str] = None, name: Optional[str] = None) -> bool`
**Pre:** config_id or name provided
**Post:** Config deleted, returns True if deleted else False
**Raises:** None
**Retry:** No
**Side Effects:** Updates _configs, removes individual file

### `get_config_for_runner(config_id: Optional[str] = None, name: Optional[str] = None) -> Optional[Dict[str, Any]]`
**Pre:** config_id or name provided
**Post:** Returns config dict (without metadata) for ComprehensiveBacktestRunner
**Raises:** None
**Retry:** No
**Side Effects:** None

### `compare_configs(config_id1: str, config_id2: str) -> Dict[str, Any]`
**Pre:** Both config_ids exist
**Post:** Returns comparison dict with differences
**Raises:** None (returns error dict if configs not found)
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] Config saved with unique ID (name_timestamp)
- [ ] Existing config updated if name matches
- [ ] Individual config file created for easy access
- [ ] Metrics indexed for filtering (sharpe, return, win_rate, max_drawdown, total_pnl)
- [ ] Load by ID or name
- [ ] Filter by min_sharpe, min_return, tags
- [ ] Sort by sharpe_ratio, return_pct, win_rate, timestamp
- [ ] Limit results
- [ ] Delete removes from list and individual file
- [ ] Comparison calculates absolute and percentage differences
- [ ] Comparison identifies winner
- [ ] Config for runner excludes metadata
- [ ] Handles missing config file gracefully

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| FMT-007 | 01-formatting-style.md | No mutable default arguments | ✅ OK |
| TYP-001 | 02-type-hints.md | All functions have type hints | ⚠️ GAP - Some Any types |
| ARCH-004 | 05-architecture.md | Functions < 20 lines (ideally) | ✅ OK - Most functions small |
| SOL-001 | 03-solid-principles.md | Single Responsibility Principle | ✅ OK - Config management only |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ⚠️ NOT APPLIED - Errors logged without trace |
| LOG-005 | 09-logging-observability.md | Never log sensitive data | ⚠️ GAP - May log API keys in config |
| TST-005 | 06-testing.md | Test coverage > 80% | ⚠️ NOT APPLIED - Needs tests |
| PERSIST-001 | Custom | JSON serialization with default=str | ✅ OK |

**NOTE:** This analysis should consider ALL 200+ rules from /rules directory.

---

## Dependencies
- **External:** json, logging, datetime, pathlib, typing
- **Internal:** None (standalone config management)

---

## Required Tests
- **test_successful_configs.py:**
  - Success: Save new config
  - Success: Update existing config (same name)
  - Success: Load config by ID
  - Success: Load config by name
  - Success: List all configs
  - Success: Filter by min_sharpe
  - Success: Filter by min_return
  - Success: Filter by tags (all must match)
  - Success: Sort by sharpe_ratio
  - Success: Sort by timestamp
  - Success: Limit results
  - Success: Delete config
  - Success: Compare two configs
  - Success: Get config for runner (metadata removed)
  - Success: Individual file created
  - Error: Config not found (returns None)
  - Error: Missing config file (loads empty list)
  - Edge: Save with before/after training metrics
  - Edge: Save with improvement_pct
  - Edge: Empty tags list
  - Edge: No filters (returns all)

---

## Notes
- Default storage_dir: config/successful_configs/
- Main file: successful_configs.json
- Individual files: {config_id}.json
- Filename format: {name}_YYYYMMDD_HHMMSS
- Supports before/after training metrics comparison
- Improvement tracking by metric (sharpe_ratio, return_pct, etc.)
- Tags must all match for filtering (AND logic)
- Sort defaults descending (except timestamp)
