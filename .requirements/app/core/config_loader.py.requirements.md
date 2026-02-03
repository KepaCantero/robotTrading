# config_loader.py Requirements

**File Path:** `app/core/config_loader.py`  
**Last Updated:** 2025-02-06  
**Audit Status:** NEEDS_AUDIT

## Purpose

YAML configuration loader with validation, fallback to defaults, thread-safe caching, and tier-specific override support.

## Type Definitions

### Class
```python
class YAMLConfigLoader:
    """Cargador de configuraciones YAML con validación y soporte para defaults."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Inicializa el cargador de configuración."""
```

## Function Signatures

### Core Methods
```python
def load(self, filename: str, use_cache: bool = True) -> Dict[str, Any]:
    """Carga un archivo YAML desde el directorio de configuración."""
    
def get_nested(
    self,
    config: Dict[str, Any],
    key_path: str,
    default: Any = None,
    separator: str = ".",
) -> Any:
    """Obtiene un valor anidado usando notación de puntos."""
    
def load_with_tier_override(
    self,
    filename: str,
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """Carga configuración con overrides por capital tier."""
    
def _apply_overrides(self, base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Aplica overrides recursivamente a la configuración base."""
```

### Convenience Methods
```python
def get_strategy_stock_allocator_config(self, tier: Optional[str] = None) -> Dict[str, Any]:
    """Carga la configuración del Strategy Stock Allocator."""
    
def clear_cache(self) -> None:
    """Limpia la caché de configuraciones."""
```

### Validation
```python
def _validate_config(self, config: Dict[str, Any], filename: str) -> Dict[str, Any]:
    """Validate configuration values after loading."""
    
def _validate_dict_values(
    self,
    config: Dict[str, Any],
    validation_rules: Dict[str, Any],
    filename: str,
    path: str = "",
) -> Dict[str, Any]:
    """Recursively validate dictionary values against rules."""
```

### Module-Level Functions
```python
def get_config_loader() -> YAMLConfigLoader:
    """Obtiene la instancia singleton del cargador de configuración."""
    
def load_strategy_stock_allocator_config(tier: Optional[str] = None) -> Dict[str, Any]:
    """Función de conveniencia para cargar la configuración del Strategy Stock Allocator."""
    
def load_momentum_filters_config(tier: Optional[str] = None) -> Dict[str, Any]:
    """Función de conveniencia para cargar la configuración de Momentum Filters."""
    
def load_market_detectors_config(tier: Optional[str] = None) -> Dict[str, Any]:
    """Función de conveniencia para cargar la configuración de Market Detectors."""
    
def get_filter_config(filter_name: str, tier: Optional[str] = None, preset: str = "balanced") -> Dict[str, Any]:
    """Obtiene la configuración de un filtro específico desde momentum_filters.yaml."""
    
def get_detector_config(detector_name: str, tier: Optional[str] = None) -> Dict[str, Any]:
    """Obtiene la configuración de un detector específico desde market_detectors.yaml."""
```

## Acceptance Criteria

### AC-CFG-001: Thread-Safe Cache Access
```bash
# Test: Cache access is thread-safe
python -c "
from app.core.config_loader import YAMLConfigLoader
import threading
loader = YAMLConfigLoader()
results = []
def load_config():
    results.append(loader.load('test.yaml'))
threads = [threading.Thread(target=load_config) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert len(results) == 10
"
```

### AC-CFG-002: YAML Safe Loading
```bash
# Test: YAML loaded safely (no code execution)
python -c "
from app.core.config_loader import YAMLConfigLoader
loader = YAMLConfigLoader()
# Should use yaml.safe_load, not yaml.load
import yaml
assert yaml.safe_load in loader.load.__code__.co_names
"
```

### AC-CFG-003: Tier Override Application
```bash
# Test: Tier overrides applied correctly
python -c "
from app.core.config_loader import load_strategy_stock_allocator_config
config = load_strategy_stock_allocator_config(tier='micro')
# Should have tier-specific overrides applied
assert 'tiers' not in config or 'micro' not in config.get('tiers', {})
"
```

### AC-CFG-004: Sensitive Data Detection
```bash
# Test: Sensitive data keys detected and warned
python -c "
from unittest.mock import patch
from app.core.config_loader import YAMLConfigLoader
loader = YAMLConfigLoader()
# Config with sensitive keys
config = {'api_key': 'secret', 'password': 'pass'}
with patch('structlog.get_logger') as mock_logger:
    loader._validate_config(config, 'test.yaml')
    # Should log warnings about sensitive keys
    assert mock_logger.return_value.warning.called
"
```

## Critical Rules

### Rule CFG-001: Environment Variable Config Directory
**Priority:** P0  
**Description:** Configuration directory must be configurable via `CONFIG_DIR` environment variable. Defaults to `config/`.

### Rule CFG-002: Thread-Safe Caching
**Priority:** P0  
**Description:** All cache access must be protected by `threading.RLock()` to prevent race conditions.

### Rule CFG-003: Input Validation
**Priority:** P0  
**Description:** All loaded configuration values must be validated for type and range before use.

### Rule CFG-004: Safe YAML Loading
**Priority:** P0  
**Description:** Must use `yaml.safe_load()` to prevent arbitrary code execution.

### Rule CFG-SEC-001: Sensitive Data Warning
**Priority:** P1  
**Description:** Log warning when detecting sensitive data keys (password, api_key, secret, token) in YAML files.

## Dependencies

### Internal Dependencies
None (pure configuration module)

### External Dependencies
```python
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Union

import structlog
import yaml
```

## Required Tests

### Unit Tests (app/tests/core/test_config_loader.py)
```python
def test_yaml_config_loader_initialization():
    """Test YAMLConfigLoader initialization."""
    
def test_yaml_config_loader_custom_config_dir():
    """Test custom config directory."""
    
def test_load_yaml_file():
    """Test loading YAML file."""
    
def test_load_yaml_file_with_cache():
    """Test cached loading returns same result."""
    
def test_load_yaml_file_cache_disabled():
    """Test cache bypass when use_cache=False."""
    
def test_load_nonexistent_file_returns_empty():
    """Test loading non-existent file returns empty dict."""
    
def test_load_invalid_yaml_returns_empty():
    """Test loading invalid YAML returns empty dict."""
    
def test_get_nested_key():
    """Test getting nested key with dot notation."""
    
def test_get_nested_key_default():
    """Test getting nested key returns default if not found."""
    
def test_get_nested_key_custom_separator():
    """Test custom separator for nested keys."""
    
def test_load_with_tier_override():
    """Test loading with tier-specific overrides."""
    
def test_apply_overrides_recursive():
    """Test recursive override application."""
    
def test_clear_cache():
    """Test cache clearing."""
    
def test_validate_config_type_check():
    """Test config type validation."""
    
def test_validate_config_sensitive_key_detection():
    """Test sensitive key detection."""
    
def test_validate_config_value_ranges():
    """Test configuration value range validation."""
    
def test_get_strategy_stock_allocator_config():
    """Test loading strategy stock allocator config."""
    
def test_get_config_loader_singleton():
    """Test singleton pattern."""
    
def test_get_filter_config():
    """Test getting filter configuration."""
    
def test_get_detector_config():
    """Test getting detector configuration."""
```

### Integration Tests
```python
def test_load_actual_strategy_config():
    """Test loading actual strategy configuration file."""
    
def test_concurrent_cache_access():
    """Test thread-safe concurrent cache access."""
    
def test_tier_override_in_actual_config():
    """Test tier override in real configuration."""
```

## File-Specific Rules

### Rule CFG-FS-001: Spanish Documentation
**Priority:** P2  
**Description:** Module documentation and comments are in Spanish. Code should use English for consistency.

### Rule CFG-FS-002: Filename Validation
**Priority:** P1  
**Description:** Validate filename parameter to prevent path traversal attacks.

### Rule CFG-FS-003: Error Handling
**Priority:** P0  
**Description:** All YAML errors must be caught and logged, returning empty dict instead of raising.

## Configuration File Format

### Expected YAML Structure
```yaml
# strategy_stock_allocator.yaml
data_validation:
  lookback_max_days: 126
  min_liquidity_usd: 500000.0

statistical_tests:
  adf:
    p_value_threshold: 0.01
    p_value_mean_reversion: 0.05
  kpss:
    p_value_threshold: 0.05

exposure:
  max_strategy_exposure: 0.50
  max_pair_exposure: 0.15

tiers:
  micro:
    exposure:
      max_strategy_exposure: 0.30
```

### Validation Rules
```python
validation_rules = {
    "max_strategy_exposure": lambda v: isinstance(v, (int, float)) and 0 <= v <= 1,
    "lookback_max_days": lambda v: isinstance(v, int) and v > 0,
    "enabled": lambda v: isinstance(v, bool),
    "tier": lambda v: v in ["micro", "small", "medium", "large"],
}
```

## References

- **BASE_RULES.md:** See ../../BASE_RULES.md for universal rules
  - CFG-001: Pydantic Settings
  - CFG-002: Environment variables
  - CFG-003: Validation
  - CFG-004: Extra forbid
- **Related Files:**
  - `app/core/centralized_config.py` - Centralized configuration system
  - `app/core/yaml_config_updater.py` - YAML config updates

## Changelog

### 2025-02-06
- Initial requirements documentation created
- Documented thread-safe caching
- Documented tier-specific override support
- Audit Status: NEEDS_AUDIT

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-06 |
| **Auditor** | Claude Code (Ralphex Audit - Gap Fix Phase 2) |
| **GAPs Found** | 0 P0, 0 P1, 1 P2, 0 P3 |
| **GAPs Fixed** | CFG-FS-001: Translated all Spanish docstrings and comments to English |
| **Notes** | All documentation translated from Spanish to English for consistency. |
