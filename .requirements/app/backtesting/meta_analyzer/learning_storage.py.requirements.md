# learning_storage.py

## Purpose
Secure persistence system for learning engine model weights. Supports PyTorch, Joblib, and MsgPack formats. Explicitly forbids pickle for security reasons. Enables incremental learning and model sharing.

---

## Type Definitions / Data Classes

### LearningEngineStorage Class
```python
class LearningEngineStorage:
    base_dir: Path                          # REQUIRED - Base directory for model storage
```

**Validation Rules:**
- `base_dir` is created with `parents=True, exist_ok=True` on init
- Must be writable
- All model formats EXCEPT .pkl are supported for security

---

## Function Signatures (Contracts)

### `LearningEngineStorage.save_weights(engine_name, weights, test_id, metadata, format) -> str`
**Pre:** engine_name must be non-empty string, weights must be serializable, test_id must be unique identifier
**Post:** Returns path to saved file, rejects 'pkl' format with ValueError
**Raises:** ValueError if format='pkl', TypeError/KeyError for invalid weights
**Retry:** ❌ No
**Side Effects:** Creates engine subdirectory, writes model file, writes metadata JSON

### `LearningEngineStorage.save_weights_async(engine_name, weights, test_id, metadata, format) -> str`
**Pre:** engine_name non-empty, weights serializable, test_id unique
**Post:** Returns path to saved file, rejects 'pkl' format
**Raises:** ValueError if format='pkl', requires aiofiles
**Retry:** ❌ No
**Side Effects:** Creates engine subdirectory, writes model file asynchronously using aiofiles

### `LearningEngineStorage.load_weights(engine_name, test_id, latest) -> Dict[str, Any]`
**Pre:** engine_name must have saved weights, test_id must exist or latest=True
**Post:** Returns dict with 'weights' and 'metadata' keys
**Raises:** FileNotFoundError if no weights found, ValueError for unsupported format
**Retry:** ❌ No
**Side Effects:** May migrate old .pkl files to secure format, reads model file

### `LearningEngineStorage.list_available_weights(engine_name, test_id_filter) -> List[Dict[str, Any]]`
**Pre:** engine_name must be valid string
**Post:** Returns list of weight info dicts (excludes .pkl files)
**Raises:** None (returns empty list if engine_dir doesn't exist)
**Retry:** ❌ No
**Side Effects:** Scans directory for model files

### `LearningEngineStorage.delete_weights(engine_name, test_id, keep_latest) -> int`
**Pre:** engine_name must be valid
**Post:** Returns number of deleted files, keeps latest if keep_latest=True
**Raises:** None (logs errors, returns count)
**Retry:** ❌ No
**Side Effects:** Deletes model files from disk

---

## Acceptance Criteria
- [ ] save_weights() raises ValueError for format='pkl' (security requirement)
- [ ] save_weights() auto-detects format when format='auto'
- [ ] save_weights() detects torch tensors and uses .pt format
- [ ] save_weights_async() uses aiofiles for async writes (REQUIRED)
- [ ] load_weights() migrates old .pkl files to secure format (one-time migration)
- [ ] load_weights() excludes .pkl files from normal listing
- [ ] list_available_weights() only returns safe formats (.pt, .pth, .joblib, .msgpack)
- [ ] delete_weights() preserves latest file if keep_latest=True
- [ ] All file operations use context managers (with statements)
- [ ] Metadata is saved separately as JSON file
- [ ] PyTorch models use torch.save() (line 296: nosec B614 comment)
- [ ] Migration from .pkl only for trusted files (line 480: noqa S403, S301)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../../BASE_RULES.md` (96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - No secrets |
| SEC-008 | BASE_RULES.md | Strong crypto / secure serialization | ✅ OK - Rejects pickle, uses secure formats |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ OK - exc_info=True used |
| TYP-001 | BASE_RULES.md | 100% type coverage | ❌ GAP - Some methods lack type hints |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK - Clear naming |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Specific exceptions caught |
| ASYNC-001 | BASE_RULES.md | Use async def | ✅ OK - save_weights_async is async |
| ASYNC-003 | BASE_RULES.md | Async context managers | ✅ OK - async with used |
| SEC-010 | BASE_RULES.md | aiofiles REQUIRED | ✅ OK - Comment states REQUIRED |
| ARCH-001 | BASE_RULES.md | Layered architecture | ✅ OK - Infrastructure component |
| QL-001 | BASE_RULES.md | Complexity < 10 | ✅ OK - Methods are simple |

**NOTE:** This analysis should consider ALL 96 rules from BASE_RULES.md.

---

## Dependencies
- **External:** joblib (REQUIRED), msgpack (REQUIRED), torch (REQUIRED), aiofiles (REQUIRED), json, logging, datetime, pathlib
- **Internal:** None

---

## Required Tests
- **tests/backtesting/meta_analyzer/test_learning_storage.py:**
  - Test save_weights() with torch.Tensor auto-detects .pt format
  - Test save_weights() with sklearn model auto-detects .joblib format
  - Test save_weights() raises ValueError for format='pkl'
  - Test save_weights() creates engine subdirectory
  - Test save_weights() saves metadata JSON separately
  - Test save_weights_async() uses aiofiles (async test)
  - Test load_weights() loads .pt files with torch.load()
  - Test load_weights() loads .joblib files with joblib.load()
  - Test load_weights() loads .msgpack files correctly
  - Test load_weights() migrates old .pkl to secure format
  - Test load_weights() raises FileNotFoundError for non-existent engine
  - Test list_available_weights() excludes .pkl files
  - Test list_available_weights() includes only safe formats
  - Test list_available_weights() filters by test_id
  - Test list_available_weights() sorts by modified time descending
  - Test delete_weights() deletes all but latest when keep_latest=True
  - Test delete_weights() returns correct count
  - Test delete_weights() handles file permission errors gracefully
  - Test _detect_format() returns 'pt' for torch tensors
  - Test _detect_format() returns 'joblib' for other types
  - Test _migrate_pkl_weights() migrates to secure format
  - Test _migrate_pkl_weights() deletes original .pkl after migration
  - Test all file operations handle errors gracefully

---

## Notes
- Security-focused: explicitly rejects pickle format (lines 78-82, 173-177)
- Supports 3 secure formats: PyTorch (.pt/.pth), Joblib (.joblib), MsgPack (.msgpack)
- One-time migration from .pkl to secure format (only for trusted files)
- PyTorch load uses nosec B614 comment (line 296) - torch is considered safe
- aiofiles is REQUIRED for async operations
- Metadata saved separately as JSON (more portable than embedding in binary formats)
- TORCH_AVAILABLE constant checked but not defined (line 496) - potential bug
- Migration uses pickle.load with noqa S403, S301 comments (lines 480, 483)
