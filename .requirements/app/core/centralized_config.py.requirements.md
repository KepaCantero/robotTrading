# centralized_config.py

## Purpose
Centralized configuration system using Pydantic Settings for type-safe, validated configuration across the trading system (TASK-10).

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses Pydantic models extensively.

### Core Configuration Classes
```python
class TradingThresholds(BaseModel):
    min_signal_strength: float = Field(default=60.0, ge=0, le=100)
    max_position_size: float = Field(default=0.1, ge=0, le=1)
    stop_loss_pct: float = Field(default=0.05, ge=0, le=1)
    take_profit_pct: float = Field(default=0.15, ge=0)
    circuit_breaker_daily_loss: float = Field(default=0.05, ge=0, le=1)
    volatility_threshold: float = Field(default=0.02, ge=0)
    correlation_threshold: float = Field(default=0.7, ge=-1, le=1)

class DatabaseConfig(BaseSettings):
    url: str = Field(default="sqlite:///data/trading.db")
    pool_size: int = Field(default=5, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0)
    pool_timeout: int = Field(default=30, ge=1)
    echo: bool = Field(default=False)
    
class APIConfig(BaseSettings):
    broker_api_url: str
    broker_api_key: SecretStr
    broker_api_secret: SecretStr
    rate_limit_per_minute: int = Field(default=120, ge=1)
    timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0, le=10)
    
class LoggingConfig(BaseSettings):
    level: str = Field(default="INFO")
    json_logs: bool = Field(default=False)
    log_dir: str = Field(default="logs")
    max_bytes: int = Field(default=10485760, ge=1)  # 10MB
    backup_count: int = Field(default=10, ge=0)
    
class CentralizedConfig(BaseSettings):
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    trading_thresholds: TradingThresholds = Field(default_factory=TradingThresholds)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    api: APIConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TRADING_",
        case_sensitive=False,
        extra="forbid"
    )
```

**Validation Rules:**
- All numeric fields have min/max constraints
- Secrets use SecretStr for security
- extra="forbid" prevents typos
- Environment prefix avoids conflicts

---

## Function Signatures (Contracts)

### `get_config() -> CentralizedConfig`
**Pre:** Environment variables set or .env file present
**Post:** Returns validated configuration singleton
**Raises:** ValidationError if configuration invalid
**Retry:** No
**Side Effects:** Loads from environment, caches singleton

### `reload_config() -> CentralizedConfig`
**Pre:** None
**Post:** Configuration reloaded from environment
**Raises:** ValidationError if configuration invalid
**Retry:** No
**Side Effects:** Clears cache, reloads environment

---

## Acceptance Criteria
- [ ] CFG-001: Pydantic Settings for type-safe config
- [ ] CFG-002: Environment variables for deployment
- [ ] CFG-003: All values validated with constraints
- [ ] CFG-004: extra="forbid" to catch typos
- [ ] CFG-005: Environment prefix "TRADING_"
- [ ] SEC-001: No hardcoded secrets
- [ ] SEC-002: Pydantic Settings with SecretStr
- [ ] LOG-001: Structured logging configurable
- [ ] Singleton pattern for get_config()
- [ ] ValidationError raised on invalid config

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| CFG-001 | BASE_RULES.md | Pydantic Settings | ✅ OK |
| CFG-002 | BASE_RULES.md | Environment variables | ✅ OK |
| CFG-003 | BASE_RULES.md | Validation | ✅ OK - Field constraints |
| CFG-004 | BASE_RULES.md | Extra forbid | ✅ OK |
| CFG-005 | BASE_RULES.md | Environment prefix | ✅ OK - TRADING_ |
| SEC-001 | BASE_RULES.md | No hardcoded secrets | ✅ OK - SecretStr |
| SEC-002 | BASE_RULES.md | Pydantic Settings | ✅ OK |
| TYP-001 | BASE_RULES.md | Type coverage | ✅ OK |

---

## Dependencies
- **External:** pydantic-settings, pydantic
- **Internal:** None

---

## Required Tests
- **tests/core/test_centralized_config.py:**
  - Test valid configuration loads
  - Test ValidationError on invalid values
  - Test environment variable loading
  - Test SecretStr hides values in logs
  - Test extra fields rejected (extra="forbid")
  - Test field validation (ge, le constraints)
  - Test singleton behavior of get_config()
  - Test reload_config() clears cache
  - Test default values applied

---

## Notes
1896 lines of comprehensive configuration. Covers trading thresholds, database, API, logging, and more. Uses Pydantic v2 SettingsConfigDict syntax.
