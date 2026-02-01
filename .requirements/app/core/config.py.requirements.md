# config.py

## Purpose
Centralized configuration management using Pydantic BaseSettings with environment variable loading.

---

## Type Definitions / Data Classes

### Settings Class (Pydantic BaseSettings)
```python
class Settings(BaseSettings):
    # Application
    app_name: str = "AlgoTrading MVP"                  # REQUIRED
    app_version: str = "1.0.0"                         # REQUIRED
    app_description: str                               # REQUIRED
    debug: bool = False                                # REQUIRED

    # API
    api_v1_prefix: str = "/api/v1"                     # REQUIRED
    api_host: str = "0.0.0.0"                          # REQUIRED
    api_port: int = 8000                               # REQUIRED (1-65535)
    api_reload: bool = False                           # REQUIRED
    secret_key: str                                    # REQUIRED (min 32 chars)
    access_token_expire_minutes: int = 30              # REQUIRED (> 0)
    refresh_token_expire_days: int = 7                 # REQUIRED (> 0)

    # Database
    database_url: str                                  # REQUIRED (PostgreSQL format)
    database_echo: bool = False                        # REQUIRED
    database_pool_size: int = 10                       # REQUIRED (> 0)
    database_max_overflow: int = 20                    # REQUIRED (>= 0)

    # Redis
    redis_url: str                                     # REQUIRED (redis:// format)
    redis_password: Optional[str] = None               # OPTIONAL
    redis_db: int = 0                                  # REQUIRED (0-15)
    redis_max_connections: int = 10                    # REQUIRED (> 0)

    # Celery
    celery_broker_url: str                             # REQUIRED
    celery_result_backend: str                         # REQUIRED
    celery_task_serializer: str = "json"               # REQUIRED
    celery_result_serializer: str = "json"             # REQUIRED
    celery_accept_content: List[str] = ["json"]        # REQUIRED

    # Trading APIs
    ib_api_key: Optional[str] = None                   # OPTIONAL
    ib_secret: Optional[str] = None                    # OPTIONAL
    alpaca_api_key: Optional[str] = None               # OPTIONAL
    alpaca_api_secret: Optional[str] = None            # OPTIONAL
    alpaca_base_url: str                               # REQUIRED
    alpaca_paper_trading: bool = True                  # REQUIRED
    binance_api_key: Optional[str] = None              # OPTIONAL
    binance_secret: Optional[str] = None               # OPTIONAL
    alpha_vantage_api_key: Optional[str] = None        # OPTIONAL
    polygon_api_key: Optional[str] = None              # OPTIONAL

    # Trading
    default_currency: str = "USD"                      # REQUIRED (ISO 4217)
    max_position_size: float = 10000.0                 # REQUIRED (> 0)
    risk_free_rate: float = 0.02                       # REQUIRED (>= 0)

    # Paper Trading
    paper_trading_initial_capital: float = 100000.0    # REQUIRED (> 0)
    paper_trading_commission_per_trade: float = 1.0    # REQUIRED (>= 0)

    # Logging
    log_level: str = "INFO"                            # REQUIRED (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    log_format: str                                    # REQUIRED
    log_file: Optional[str] = None                     # OPTIONAL

    # CORS
    cors_origins: List[str] = ["*"]                    # REQUIRED
    cors_allow_credentials: bool = True                # REQUIRED
    cors_allow_methods: List[str] = ["*"]              # REQUIRED
    cors_allow_headers: List[str] = ["*"]              # REQUIRED

    # Security
    password_min_length: int = 8                       # REQUIRED (> 0)
    password_require_uppercase: bool = True             # REQUIRED
    password_require_lowercase: bool = True             # REQUIRED
    password_require_numbers: bool = True               # REQUIRED
    password_require_special: bool = True               # REQUIRED

    # Rate Limiting
    rate_limit_requests: int = 100                     # REQUIRED (> 0)
    rate_limit_window: int = 60                        # REQUIRED (> 0)
```

**Validation Rules:**
- log_level must be in DEBUG, INFO, WARNING, ERROR, CRITICAL
- secret_key must be >= 32 characters
- Weak secret keys only with ALLOW_WEAK_SECRET_KEY=true
- CORS origins/methods/headers can be comma-separated strings
- Celery accept_content can be comma-separated

---

## Function Signatures (Contracts)

### `validate_log_level(cls, v: str) -> str`
**Pre:** v is a string
**Post:** Returns uppercase valid log level
**Raises:** ValueError if invalid
**Retry:** No
**Side Effects:** None

### `validate_secret_key(cls, v: str, info: ValidationInfo) -> str`
**Pre:** v is a string
**Post:** Returns validated secret key
**Raises:** ValueError if too short or weak (without override)
**Retry:** No
**Side Effects:** Logs warning if weak key allowed

### `parse_cors_origins(cls, v) -> List[str]`
**Pre:** v is string or list
**Post:** Returns list of origins
**Raises:** No
**Retry:** No
**Side Effects:** None

### `parse_cors_methods(cls, v) -> List[str]`
**Pre:** v is string or list
**Post:** Returns list of HTTP methods
**Raises:** No
**Retry:** No
**Side Effects:** None

### `parse_cors_headers(cls, v) -> List[str]`
**Pre:** v is string or list
**Post:** Returns list of headers
**Raises:** No
**Retry:** No
**Side Effects:** None

### `parse_celery_content(cls, v) -> List[str]`
**Pre:** v is string or list
**Post:** Returns list of content types
**Raises:** No
**Retry:** No
**Side Effects:** None

### `get_database_url_sync(self) -> str`
**Pre:** database_url is set
**Post:** Returns synchronous database URL
**Raises:** No
**Retry:** No
**Side Effects:** None

### `get_database_url_async(self) -> str`
**Pre:** database_url is set
**Post:** Returns asyncpg/aiosqlite URL
**Raises:** No
**Retry:** No
**Side Effects:** None

### `is_production(self) -> bool`
**Pre:** None
**Post:** Returns True if not debug mode
**Raises:** No
**Retry:** No
**Side Effects:** None

### `is_development(self) -> bool`
**Pre:** None
**Post:** Returns True if debug mode
**Raises:** No
**Retry:** No
**Side Effects:** None

### `get_cors_config(self) -> dict`
**Pre:** All CORS fields set
**Post:** Returns CORS configuration dict
**Raises:** No
**Retry:** No
**Side Effects:** None

### `get_celery_config(self) -> dict`
**Pre:** All Celery fields set
**Post:** Returns Celery configuration dict
**Raises:** No
**Retry:** No
**Side Effects:** None

### `get_global_settings() -> Settings`
**Pre:** None
**Post:** Returns singleton Settings instance
**Raises:** ValidationError if config invalid
**Retry:** No
**Side Effects:** Creates singleton if needed

### `get_settings() -> Settings`
**Pre:** None
**Post:** Returns Settings instance (for FastAPI dependency injection)
**Raises:** ValidationError if config invalid
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] All configuration loaded from environment variables
- [ ] SECRET_KEY must be >= 32 characters (enforced)
- [ ] Weak secret keys blocked without ALLOW_WEAK_SECRET_KEY=true
- [ ] Log level validation enforced
- [ ] CORS parsing supports comma-separated strings
- [ ] Celery config parsing supports comma-separated strings
- [ ] Database URL conversion to async format
- [ ] Singleton pattern for global settings
- [ ] Type-safe configuration with Pydantic

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Secret Key Security | CRITICAL_RULES.md | SECRET_KEY >= 32 chars ALWAYS | ✅ OK |
| No Hardcoded Secrets | CRITICAL_RULES.md | No default secrets in code | ✅ OK |
| Environment Config | BASE_RULES.md | Use environment variables | ✅ OK |
| Type Safety | BASE_RULES.md | Pydantic validation | ✅ OK |
| Validation | BASE_RULES.md | Input validation in validators | ✅ OK |
| Logging | BASE_RULES.md | Security warnings logged | ✅ OK |
| Weak Key Detection | CRITICAL_RULES.md | Detect common weak keys | ✅ OK |

---

## Dependencies
- **External:** pydantic, pydantic_settings, logging, os, typing
- **Internal:** None

---

## Required Tests
- **test_config.py:**
  - Test settings loaded from environment
  - Test SECRET_KEY validation (length)
  - Test weak SECRET_KEY detection
  - Test ALLOW_WEAK_SECRET_KEY override
  - Test log_level validation
  - Test CORS parsing (string and list)
  - Test Celery content parsing
  - Test database URL async conversion
  - Test singleton pattern
  - Test Pydantic validation errors

---

## Notes
- CRITICAL: SECRET_KEY validation enforced in ALL environments
- Weak keys require explicit ALLOW_WEAK_SECRET_KEY=true override
- Singleton pattern prevents duplicate instances
- All API credentials are Optional (loaded from secure vault in production)
