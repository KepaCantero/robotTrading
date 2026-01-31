# audit_trail.py

## Purpose
Provides audit trail system for backtesting reproducibility. Generates unique SHA256 hashes per configuration and code version, enables exact reproduction of past executions.

---

## Type Definitions / Data Classes

### AuditTrail Class
```python
class AuditTrail:
    log_file: Path                          # REQUIRED - Path to JSONL audit log file
    enable_git_tracking: bool                # OPTIONAL - Enable git metadata tracking (default: True)
```

**Validation Rules:**
- `log_file` parent directory is created with `parents=True, exist_ok=True`
- `log_file` must be writable
- `enable_git_tracking` controls whether git metadata is included in hashes

---

## Function Signatures (Contracts)

### `AuditTrail.generate_hash(config_path, code_version, additional_data) -> str`
**Pre:** config_path must exist and be readable file
**Post:** Returns 64-character SHA256 hex string
**Raises:** FileNotFoundError if config_path doesn't exist
**Retry:** ❌ No
**Side Effects:** Reads config file, runs git subprocesses, logs hash generation

### `AuditTrail.save_audit_record(config_path, hash_value, metadata, result_path) -> None`
**Pre:** All parameters must be valid strings or dicts
**Post:** Appends JSONL record to log_file
**Raises:** OSError, IOError for file write failures
**Retry:** ❌ No
**Side Effects:** Writes single line JSON to log file (async version uses aiofiles)

### `AuditTrail.save_audit_record_sync(config_path, hash_value, metadata, result_path) -> None`
**Pre:** All parameters must be valid strings or dicts
**Post:** Appends JSONL record to log_file synchronously
**Raises:** OSError, IOError for file write failures
**Retry:** ❌ No
**Side Effects:** Writes single line JSON to log file

### `AuditTrail.verify_reproducibility(target_hash) -> Dict[str, Any]`
**Pre:** target_hash must be valid 64-char hex string
**Post:** Returns dict with 'reproducible' bool and detailed status
**Raises:** None (returns dict with error info if hash not found)
**Retry:** ❌ No
**Side Effects:** Reads log file, runs git subprocesses, no writes

### `AuditTrail.list_audit_records(limit, filter_by_config) -> List[Dict[str, Any]]`
**Pre:** limit must be positive int or None, filter_by_config must be string or None
**Post:** Returns list of audit records sorted by timestamp (newest first)
**Raises:** None (returns empty list on errors)
**Retry:** ❌ No
**Side Effects:** Reads and parses log file

---

## Acceptance Criteria
- [ ] generate_hash() returns unique SHA256 for same config + code version
- [ ] generate_hash() includes git commit hash in hash input if git tracking enabled
- [ ] generate_hash() includes timestamp in hash input (makes hashes time-dependent)
- [ ] save_audit_record() appends single JSONL line to log file
- [ ] save_audit_record_async() uses aiofiles for async file writes
- [ ] verify_reproducibility() checks code_version match
- [ ] verify_reproducibility() checks config file existence
- [ ] verify_reproducibility() checks git dirty state if git tracking enabled
- [ ] list_audit_records() returns records sorted by timestamp descending
- [ ] list_audit_records() respects limit parameter
- [ ] list_audit_records() filters by config path if specified
- [ ] All git subprocess calls have 5-second timeout
- [ ] Git subprocess failures don't crash the program (graceful fallback)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ❌ GAP - Git subprocess errors logged without exc_info |
| TYP-001 | BASE_RULES.md | 100% type coverage | ❌ GAP - Missing return type on _get_code_version |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ASYNC-001 | BASE_RULES.md | Use async def | ✅ OK - save_audit_record is async |
| ASYNC-003 | BASE_RULES.md | Async context managers | ✅ OK - async with aiofiles.open |
| SEC-010 | BASE_RULES.md | aiofiles REQUIRED | ✅ OK - Comment states REQUIRED |
| QL-001 | BASE_RULES.md | Complexity < 10 | ✅ OK - Simple methods |
| TRD-004 | BASE_RULES.md | Audit trail logging | ✅ OK - Core purpose of file |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** hashlib, json, logging, subprocess, datetime, pathlib, aiofiles (REQUIRED)
- **Internal:** None

---

## Required Tests
- **tests/backtesting/meta_analyzer/test_audit_trail.py:**
  - Test generate_hash() creates consistent hash for same inputs
  - Test generate_hash() includes git commit in hash calculation
  - Test generate_hash() raises FileNotFoundError for missing config
  - Test generate_hash() includes additional_data in hash
  - Test save_audit_record() writes valid JSONL to file
  - Test save_audit_record() appends to existing log file
  - Test save_audit_record_async() writes valid JSONL (async test)
  - Test verify_reproducibility() returns reproducible=True for matching conditions
  - Test verify_reproducibility() returns reproducible=False for code version mismatch
  - Test verify_reproducibility() returns reproducible=False for missing config
  - Test verify_reproducibility() returns reproducible=False for dirty git repo
  - Test verify_reproducibility() returns error dict for hash not found
  - Test list_audit_records() returns records sorted by timestamp
  - Test list_audit_records() respects limit parameter
  - Test list_audit_records() filters by config path
  - Test list_audit_records() returns empty list for non-existent log
  - Test _get_git_info() handles subprocess timeouts gracefully
  - Test _get_git_info() handles git not available (graceful degradation)
  - Test _find_record_by_hash() finds correct record
  - Test _find_record_by_hash() returns None for non-existent hash

---

## Notes
- aiofiles is explicitly marked as REQUIRED (line 18-19 comment)
- Git subprocess calls all have 5-second timeout to prevent hanging
- Hash includes timestamp, making same config reproducible only at same time
- verify_reproducibility() checks multiple conditions: code match, config exists, git clean
- Git tracking can be disabled via enable_git_tracking=False
- JSONL format (one JSON per line) used for audit log
- Spanish comments used in error logging
- Line 143: typo 'git dif' should be 'git diff' (missing 'f')
