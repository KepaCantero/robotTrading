# centralized_config.py Requirements

**File Path:** `app/core/centralized_config.py`  
**Last Updated:** 2025-02-06  
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.290182

## Purpose

Centralized configuration system that eliminates magic values scattered throughout the codebase. Centralizes all trading thresholds, risk parameters, strategy configurations, and system settings.

## Type Definitions

### Enums
```python
class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
```

### Main Configuration Classes
```python
class TradingThresholds(BaseModel):
    """Centralized trading thresholds."""
    # Signal thresholds
    min_signal_strength: float = 60.0
    min_signal_confidence: float = 70.0
    min_liquidity_score: float = 50.0
    
    # Position sizing
    max_position_size: float = 0.1
    min_position_size: float = 0.01
    
    # Risk management
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.15
    daily_loss_limit: float = 0.05
    
    # And many more...

class StrategyConfig(BaseModel):
    """Configuration for individual strategies."""
    name: str
    enabled: bool = True
    weight: float = 1.0
    parameters: Dict[str, Any] = {}
    max_position_size: Optional[float] = 0.1
    stop_loss_pct: Optional[float] = 0.05
    take_profit_pct: Optional[float] = 0.15

class StockAllocationSettings(BaseSettings):
    """Stock Allocation Configuration with Pydantic validation."""
    LOOKBACK_MAX_DAYS: int = 126
    MIN_LIQUIDITY_USD: float = 500_000.0
    ADF_P_VALUE_THRESHOLD: float = 0.01
    # And many more...

class DatabaseConfig(BaseModel):
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    name: str = "algotrading"
    user: str = "postgres"
    password: str = ""  # MUST come from environment

class CentralizedConfig(BaseSettings):
    """Centralized configuration for the entire application."""
    environment: Environment
    trading: TradingThresholds
    database: DatabaseConfig
    redis: RedisConfig
    api: APIConfig
    logging: LoggingConfig
    monitoring: MonitoringConfig
    strategies: Dict[str, StrategyConfig]
```

## Function Signatures

### Configuration Access
```python
def get_config() -> CentralizedConfig:
    """Get the global configuration instance."""
    
def get_trading_threshold(threshold_name: str = None) -> Any:
    """Get trading thresholds or specific threshold."""
    
def get_strategy_config(strategy_name: str) -> Optional[StrategyConfig]:
    """Get configuration for a specific strategy."""
    
def reload_config():
    """Reload the configuration from files."""
    
def set_config(config: CentralizedConfig):
    """Set the global configuration instance."""
    
def validate_config() -> bool:
    """Validate the current configuration."""
    
def get_config_summary() -> Dict[str, Any]:
    """Get a summary of the current configuration."""
    
def update_strategy_config(strategy_name: str, new_config: dict):
    """Update strategy configuration."""
```

### YAML Loading
```python
def load_config_from_yaml(config_path: Path) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    
def load_config_from_json(config_path: Path) -> Dict[str, Any]:
    """Load configuration from JSON file."""
```

### Configuration Validation
```python
def validate_atr_multipliers(atr_multipliers: Dict[str, float]) -> bool:
    """Validate ATR multiplier configuration."""
    
def validate_risk_percentages(risk_config: Dict[str, float]) -> bool:
    """Validate risk percentage configuration."""
    
def validate_trading_symbols(symbols: List[str]) -> bool:
    """Validate trading symbols list."""
    
def validate_dates(backtest_config: Dict[str, str]) -> bool:
    """Validate backtesting date configuration."""
    
def validate_config(config: 'Configuration') -> bool:
    """Validate complete configuration object."""
```

### Configuration Merging
```python
def merge_configs(
    base_config: Dict[str, Any],
    override_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge two configuration dictionaries recursively."""
```

### Configuration Class
```python
class Configuration:
    """Configuration wrapper class for accessing configuration values."""
    def __init__(self, config_dict: Dict[str, Any])
    def get(self, key: str, default: Any = None) -> Any
    def set(self, key: str, value: Any) -> None
    def get_atr_multiplier(self, multiplier_name: str) -> Optional[float]
    def set_atr_multiplier(self, multiplier_name: str, value: float) -> None
    def get_risk_config(self) -> Dict[str, Any]
    def get_trading_symbols(self) -> List[str]
    def get_backtest_dates(self) -> Dict[str, str]
```

## Acceptance Criteria

### AC-CC-001: Pydantic Validation
```bash
# Test: Invalid values raise ValidationError
python -c "
from app.core.centralized_config import TradingThresholds
import pydantic
try:
    thresholds = TradingThresholds(
        stop_loss_pct=0.8  # Invalid: > 0.5
    )
    assert False, 'Should have raised ValidationError'
except pydantic.ValidationError:
    pass
"
```

### AC-CC-002: Environment Variable Loading
```bash
# Test: Environment variables override defaults
python -c "
import os
os.environ['DB_HOST'] = 'custom-host'
from app.core.centralized_config import get_config
config = get_config()
assert config.database.host == 'custom-host'
"
```

### AC-CC-003: Password Security
```bash
# Test: DB password must come from environment
python -c "
import os
os.environ['DB_PASSWORD'] = 'test-password'
from app.core.centralized_config import get_config
config = get_config()
# Password should come from environment, not default
assert config.database.password == 'test-password'
# Connection string should use environment password
conn_str = config.database.connection_string
assert 'test-password' in conn_str
"
```

### AC-CC-004: Strategy Config Loading
```bash
# Test: Strategy configs loaded from YAML
python -c "
from app.core.centralized_config import get_config
config = get_config()
# Should have loaded strategies from config/strategies/*.yaml
assert isinstance(config.strategies, dict)
"
```

## Critical Rules

### Rule CC-001: Pydantic Models
**Priority:** P0  
**Description:** All configuration must use Pydantic models for validation.

### Rule CC-002: Environment Variables
**Priority:** P0  
**Description:** Database passwords and secrets must come from environment variables.

### Rule CC-003: No Hardcoded Thresholds
**Priority:** P0  
**Description:** All trading thresholds must be in `TradingThresholds`, not hardcoded in strategy code.

### Rule CC-004: Validation Rules
**Priority:** P0  
**Description:** Use `@field_validator` for custom validation logic.

### Rule CC-SEC-001: Connection String Security
**Priority:** P0  
**Description:** Build connection strings dynamically from environment variables. Never hardcode credentials.

## Dependencies

### Internal Dependencies
```python
from app.core.config_loader import load_strategy_stock_allocator_config
```

### External Dependencies
```python
import logging
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
```

## Required Tests

### Unit Tests (app/tests/core/test_centralized_config.py)
```python
def test_trading_thresholds_defaults():
    """Test default trading threshold values."""
    
def test_trading_thresholds_validation():
    """Test trading threshold validation."""
    
def test_strategy_config_defaults():
    """Test default strategy config values."""
    
def test_strategy_config_validation():
    """Test strategy config validation."""
    
def test_database_config_defaults():
    """Test database config defaults."""
    
def test_database_config_password_from_env():
    """Test DB password from environment."""
    
def test_database_config_connection_string():
    """Test connection string generation."""
    
def test_centralized_config_initialization():
    """Test centralized config initialization."""
    
def test_centralized_config_validation():
    """Test centralized config validation."""
    
def test_get_config_singleton():
    """Test singleton pattern."""
    
def test_get_trading_threshold():
    """Test getting specific threshold."""
    
def test_get_strategy_config():
    """Test getting strategy config."""
    
def test_reload_config():
    """Test config reload."""
    
def test_update_strategy_config():
    """Test updating strategy config."""
    
def test_load_config_from_yaml():
    """Test loading from YAML."""
    
def test_load_config_from_json():
    """Test loading from JSON."""
    
def test_validate_atr_multipliers():
    """Test ATR multiplier validation."""
    
def test_validate_risk_percentages():
    """Test risk percentage validation."""
    
def test_validate_trading_symbols():
    """Test trading symbols validation."""
    
def test_validate_dates():
    """Test date validation."""
    
def test_merge_configs():
    """Test config merging."""
    
def test_configuration_class():
    """Test Configuration class."""
    
def test_configuration_get():
    """Test Configuration.get() with dot notation."""
    
def test_configuration_set():
    """Test Configuration.set() with dot notation."""
```

## File-Specific Rules

### Rule CC-FS-001: Field Descriptions
**Priority:** P2  
**Description:** All fields must have `description` parameter for documentation.

### Rule CC-FS-002: Percentage Validation
**Priority:** P0  
**Description:** All percentage fields must validate 0-1 range (or 0-100 for display percentages).

### Rule CC-FS-003: Port Validation
**Priority:** P0  
**Description:** Port fields must validate 1-65535 range.

### Rule CC-FS-004: Weights Sum Validation
**Priority:** P1  
**Description:** Dictionary weights should sum to approximately 1.0 (with 5% tolerance).

## Configuration Migration

### Finding Magic Values
```python
def find_magic_values() -> Dict[str, List[str]]:
    """Find magic values in codebase that should be in config."""
```

### Migrating Magic Values
```python
def migrate_magic_values(magic_values: Dict[str, List[str]]) -> bool:
    """Migrate magic values to centralized configuration."""
```

## References

- **BASE_RULES.md:** See ../../BASE_RULES.md for universal rules
  - CFG-001: Pydantic Settings
  - CFG-002: Environment variables
  - CFG-003: Validation
  - SEC-001: No hardcoded secrets
- **Related Files:**
  - `app/core/config_loader.py` - YAML configuration loading
  - `app/core/config.py` - Simple configuration

## Changelog

### 2025-02-06
- Initial requirements documentation created
- Documented all trading thresholds
- Documented strategy configuration
- Documented validation rules
- Audit Status: NEEDS_AUDIT
