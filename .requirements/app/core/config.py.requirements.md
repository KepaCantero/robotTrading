# config.py Requirements

**File Path:** `app/core/config.py`  
**Last Updated:** 2025-02-06  
**Audit Status:** NEEDS_AUDIT

## Purpose

Centralized application configuration using Pydantic Settings. Loads from environment variables, validates types, provides defaults, and enforces security rules.

## Type Definitions

### Classes
```python
class Settings(BaseSettings):
    """Application settings with environment variable loading."""
    
    # Core Application
    APP_NAME: str = "Algorithmic Trading System"
    VERSION: str = "0.3.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1
    
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "algotrading"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""  # MUST come from environment
    DB_POOL_SIZE: int = 10
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Trading
    MAX_POSITION_SIZE: float = 0.25
    STOP_LOSS_PCT: float = 0.05
    TAKE_PROFIT_PCT: float = 0.15
    DAILY_LOSS_LIMIT: float = 0.05
    
    # Security
    SECRET_KEY: str = ""  # MUST come from environment
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # CFG-004: Extra forbid
    )
```

## Function Signatures

### Singleton Access
```python
def get_settings() -> Settings:
    """Get global settings instance (singleton)."""

def reload_settings() -> Settings:
    """Reload settings from environment."""

def validate_settings(settings: Settings) -> bool:
    """Validate all settings."""
```

## Acceptance Criteria

### AC-CONFIG-001: Environment Variable Loading
```bash
# Test: Environment variables override defaults
python -c "
import os
os.environ['API_PORT'] = '9000'
from app.core.config import get_settings
settings = get_settings()
assert settings.API_PORT == 9000
"
```

### AC-CONFIG-002: Type Validation
```bash
# Test: Invalid types raise validation error
python -c "
import os
os.environ['API_PORT'] = 'not_a_number'
from app.core.config import get_settings
import pydantic
try:
    settings = get_settings()
    assert False, 'Should have raised ValidationError'
except pydantic.ValidationError:
    pass
"
```

### AC-CONFIG-003: Required Secrets
```bash
# Test: Missing required secrets in production raise error
python -c "
import os
os.environ['ENVIRONMENT'] = 'production'
os.environ['SECRET_KEY'] = ''  # Empty in production
from app.core.config import get_settings
try:
    settings = get_settings()
    assert False, 'Should have raised error for empty SECRET_KEY in production'
except ValueError:
    pass
"
```

### AC-CONFIG-004: Singleton Pattern
```bash
# Test: Multiple calls return same instance
python -c "
from app.core.config import get_settings
s1 = get_settings()
s2 = get_settings()
assert s1 is s2
"
```

## Critical Rules

### Rule CONFIG-001: Pydantic Settings
**Priority:** P0  
**Description:** Must use `pydantic_settings.BaseSettings` for configuration. No manual environment variable parsing.

### Rule CONFIG-002: Environment Variables
**Priority:** P0  
**Description:** All configuration must come from environment variables. No hardcoded secrets or credentials.

### Rule CONFIG-003: Validation
**Priority:** P0  
**Description:** All settings must have type hints and validation rules.

### Rule CONFIG-004: Extra Forbid
**Priority:** P1  
**Description:** Use `extra="ignore"` for flexibility. Change to `extra="forbid"` in production for stricter validation.

### Rule CONFIG-SEC-001: No Default Secrets
**Priority:** P0  
**Description:** Never provide default values for secrets (DB_PASSWORD, SECRET_KEY). Must come from environment.

### Rule CONFIG-SEC-002: Production Validation
**Priority:** P0  
**Description:** In production mode, validate that all secrets are non-empty.

## Dependencies

### Internal Dependencies
```python
from app.core.logging_config import get_logger
```

### External Dependencies
```python
import os
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
```

## Required Tests

### Unit Tests (app/tests/core/test_config.py)
```python
def test_settings_initialization():
    """Test Settings initialization with defaults."""
    
def test_settings_from_environment():
    """Test loading settings from environment variables."""
    
def test_settings_type_validation():
    """Test type validation for settings."""
    
def test_settings_port_validation():
    """Test port number validation (1-65535)."""
    
def test_settings_percentage_validation():
    """Test percentage validation (0-1)."""
    
def test_settings_secret_key_validation():
    """Test secret key validation."""
    
def test_settings_db_password_empty_in_production():
    """Test empty DB_PASSWORD raises error in production."""
    
def test_settings_secret_key_empty_in_production():
    """Test empty SECRET_KEY raises error in production."""
    
def test_get_settings_singleton():
    """Test singleton pattern."""
    
def test_reload_settings():
    """Test settings reload."""
    
def test_validate_settings():
    """Test settings validation."""
```

### Integration Tests
```python
def test_load_settings_from_env_file():
    """Test loading settings from .env file."""
    
def test_case_insensitive_environment():
    """Test environment variables are case-insensitive."""
```

## File-Specific Rules

### Rule CONFIG-FS-001: Field Validators
**Priority:** P0  
**Description:** Use `@field_validator` for custom validation logic.

### Rule CONFIG-FS-002: Model Config
**Priority:** P0  
**Description:** Must include `model_config` class attribute with proper settings.

### Rule CONFIG-FS-003: Type Imports
**Priority:** P1  
**Description:** Use `SettingsConfigDict` from `pydantic_settings` for model config type hint.

## Configuration File Format

### .env File Example
```bash
# Core Application
ENVIRONMENT=production
DEBUG=false

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=algotrading
DB_USER=postgres
DB_PASSWORD=must_come_from_environment  # Rule CONFIG-SEC-001

# Security
SECRET_KEY=must_come_from_environment  # Rule CONFIG-SEC-001

# Trading
MAX_POSITION_SIZE=0.25
STOP_LOSS_PCT=0.05

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## References

- **BASE_RULES.md:** See ../../BASE_RULES.md for universal rules
  - CFG-001: Pydantic Settings
  - CFG-002: Environment variables
  - CFG-003: Validation
  - CFG-004: Extra forbid
  - SEC-001: No hardcoded secrets
- **Related Files:**
  - `app/core/centralized_config.py` - More complex configuration system
  - `.env` - Environment variables file

## Changelog

### 2025-02-06
- Initial requirements documentation created
- Documented Pydantic Settings usage
- Documented environment variable loading
- Audit Status: NEEDS_AUDIT
