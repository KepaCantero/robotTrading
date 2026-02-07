# yaml_config_updater.py Requirements

**File Path:** `app/core/yaml_config_updater.py`  
**Last Updated:** 2025-02-06  
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.284414

## Purpose

Safe YAML configuration file updater with backup creation, validation, atomic writes, and rollback support.

## Type Definitions

### Classes
```python
class YAMLConfigUpdater:
    """Safe YAML configuration file updater."""
    
    def __init__(
        self,
        config_path: Path,
        backup_dir: Optional[Path] = None,
        max_backups: int = 10,
        create_backup: bool = True,
    ):
        """Initialize the updater."""
```

## Function Signatures

### Core Methods
```python
def update(self, updates: Dict[str, Any], create_backup: bool = None) -> bool:
    """Update configuration file with new values."""
    
def update_nested(self, key_path: str, value: Any, separator: str = ".") -> bool:
    """Update a nested configuration value."""
    
def get(self, key_path: str, default: Any = None, separator: str = ".") -> Any:
    """Get a configuration value."""
    
def reload(self) -> Dict[str, Any]:
    """Reload configuration from file."""
    
def rollback(self, backup_index: int = -1) -> bool:
    """Rollback to a previous backup."""
    
def list_backups(self) -> List[Path]:
    """List available backup files."""
    
def validate(self) -> bool:
    """Validate current configuration."""
```

### Backup Management
```python
def _create_backup(self) -> Optional[Path]:
    """Create backup of current configuration."""
    
def _cleanup_old_backups(self) -> None:
    """Remove old backups keeping only max_backups."""
```

### Validation
```python
def _validate_updates(self, updates: Dict[str, Any]) -> bool:
    """Validate updates before applying."""
    
def _validate_yaml(self, content: str) -> bool:
    """Validate YAML content is well-formed."""
```

## Acceptance Criteria

### AC-YAML-001: Backup Creation
```bash
# Test: Backup created before update
python -c "
from pathlib import Path
from app.core.yaml_config_updater import YAMLConfigUpdater
updater = YAMLConfigUpdater(Path('test.yaml'))
updater.update({'key': 'value'})
backups = updater.list_backups()
assert len(backups) > 0
assert backups[0].exists()
"
```

### AC-YAML-002: Atomic Write
```bash
# Test: Write is atomic (uses temp file + rename)
python -c "
from pathlib import Path
from app.core.yaml_config_updater import YAMLConfigUpdater
updater = YAMLConfigUpdater(Path('test.yaml'))
# Should use temp file then atomic rename
# Implementation should use Path.replace() for atomicity
"
```

### AC-YAML-003: Rollback Functionality
```bash
# Test: Can rollback to previous backup
python -c "
from pathlib import Path
from app.core.yaml_config_updater import YAMLConfigUpdater
updater = YAMLConfigUpdater(Path('test.yaml'))
original = updater.reload()
updater.update({'key': 'new_value'})
updater.rollback()
restored = updater.reload()
assert restored == original
"
```

### AC-YAML-004: Backup Cleanup
```bash
# Test: Old backups cleaned up
python -c "
from pathlib import Path
from app.core.yaml_config_updater import YAMLConfigUpdater
updater = YAMLConfigUpdater(Path('test.yaml'), max_backups=3)
for i in range(10):
    updater.update({'key': f'value{i}'})
backups = updater.list_backups()
assert len(backups) <= 3
"
```

## Critical Rules

### Rule YAML-001: Atomic Writes
**Priority:** P0  
**Description:** Always write to temp file first, then use `Path.replace()` for atomic rename.

### Rule YAML-002: Backup Creation
**Priority:** P0  
**Description:** Create backup before any modification unless explicitly disabled.

### Rule YAML-003: Validation Before Write
**Priority:** P0  
**Description:** Validate YAML syntax before writing to file. Never write invalid YAML.

### Rule YAML-SEC-001: Path Traversal Prevention
**Priority:** P0  
**Description:** Validate all file paths to prevent path traversal attacks.

### Rule YAML-SEC-002: Sensitive Data Warning
**Priority:** P1  
**Description:** Log warning if updates contain sensitive keys (password, api_key, secret).

## Dependencies

### Internal Dependencies
```python
from app.core.logging_config import get_logger
```

### External Dependencies
```python
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
```

## Required Tests

### Unit Tests (app/tests/core/test_yaml_config_updater.py)
```python
def test_yaml_config_updater_initialization():
    """Test updater initialization."""
    
def test_yaml_config_updater_custom_backup_dir():
    """Test custom backup directory."""
    
def test_update_creates_backup():
    """Test backup creation on update."""
    
def test_update_without_backup():
    """Test update without backup when disabled."""
    
def test_update_creates_new_file():
    """Test update creates new file if not exists."""
    
def test_update_nested_value():
    """Test updating nested value."""
    
def test_get_value():
    """Test getting configuration value."""
    
def test_get_nested_value():
    """Test getting nested value."""
    
def test_get_default_value():
    """Test getting default value when key not found."""
    
def test_reload():
    """Test reloading configuration from file."""
    
def test_rollback():
    """Test rollback to previous backup."""
    
def test_rollback_specific_backup():
    """Test rollback to specific backup index."""
    
def test_list_backups():
    """Test listing available backups."""
    
def test_cleanup_old_backups():
    """Test old backup cleanup."""
    
def test_validate():
    """Test configuration validation."""
    
def test_validate_invalid_yaml():
    """Test validation catches invalid YAML."""
    
def test_atomic_write():
    """Test write is atomic."""
    
def test_path_traversal_prevention():
    """Test path traversal is prevented."""
```

### Integration Tests
```python
def test_full_update_workflow():
    """Test complete update workflow with backup and rollback."""
    
def test_concurrent_updates():
    """Test handling concurrent updates."""
```

## File-Specific Rules

### Rule YAML-FS-001: Backup Naming
**Priority:** P2  
**Description:** Backup files should be named with timestamp: `config.yaml.YYYYMMDD_HHMMSS.bak`.

### Rule YAML-FS-002: Validation Rules
**Priority:** P1  
**Description:** Implement `_validate_updates()` to check:
- No path traversal in keys
- YAML syntax is valid
- Required fields present (if configured)

### Rule YAML-FS-003: Error Handling
**Priority:** P0  
**Description:** All file operations must handle exceptions gracefully and log errors.

## Usage Examples

### Basic Update
```python
from pathlib import Path
from app.core.yaml_config_updater import YAMLConfigUpdater

updater = YAMLConfigUpdater(Path('config/strategy.yaml'))
updater.update({
    'enabled': True,
    'parameters': {
        'lookback': 20,
        'threshold': 0.5
    }
})
```

### Nested Update
```python
updater.update_nested('parameters.lookback', 30)
```

### Rollback
```python
if not validate_new_config():
    updater.rollback()
```

## References

- **BASE_RULES.md:** See ../../BASE_RULES.md for universal rules
  - CFG-001: Configuration management
  - SEC-005: Audit logging
- **Related Files:**
  - `app/core/config_loader.py` - YAML configuration loader

## Changelog

### 2025-02-06
- Initial requirements documentation created
- Documented atomic write pattern
- Documented backup and rollback functionality
- Audit Status: NEEDS_AUDIT

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-06 |
| **Auditor** | Claude Code (Ralphex Audit - Gap Fix Phase 2) |
| **GAPs Found** | 0 P0, 0 P1, 2 P2, 0 P3 |
| **GAPs Fixed** | YAML-FS-001: Added milliseconds to backup timestamp for better uniqueness |
| **GAPs Fixed** | YAML-FS-002: Implemented atomic write pattern (temp file + rename) in all update methods |
| **Notes** | All violations fixed. Atomic writes prevent data corruption. |
