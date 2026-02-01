# secret_manager.py

## Purpose
Centralized secret management following Rule 28 (Security and secrets management) - NO hardcoded secrets, environment variable loading with validation, secret masking in logs, and production-readiness checks.

---

## Type Definitions / Data Classes

### SecretCategory Enum
```python
class SecretCategory(str, Enum):
    DATABASE = "database"
    API_KEY = "api_key"
    BROKER = "broker"
    SECURITY = "security"
    NOTIFICATION = "notification"
    EXTERNAL_SERVICE = "external_service"
```

### SecretDefinition DataClass
```python
@dataclass
class SecretDefinition:
    name: str                               # REQUIRED - Environment variable name
    category: SecretCategory                # REQUIRED - Secret category
    description: str                        # REQUIRED - Human-readable description
    required_in_production: bool = True     # REQUIRED - Required in production
    default_value: Optional[str] = None     # OPTIONAL - Default for development
    validation_pattern: Optional[str] = None # OPTIONAL - Regex validation
    min_length: int = 0                     # REQUIRED - Minimum length
    max_length: int = 256                   # REQUIRED - Maximum length
    requires_uppercase: bool = True         # REQUIRED - Requires uppercase
    requires_lowercase: bool = True         # REQUIRED - Requires lowercase
    requires_digit: bool = True             # REQUIRED - Requires digit
    requires_special: bool = False          # REQUIRED - Requires special char
    rotation_days: int = 90                 # REQUIRED - Rotation period
```

### SecretMetadata DataClass
```python
@dataclass
class SecretMetadata:
    name: str                               # REQUIRED - Secret name
    created_at: float                       # REQUIRED - Creation timestamp
    last_rotated: float                     # REQUIRED - Last rotation timestamp
    rotation_count: int = 0                 # REQUIRED - Number of rotations
    last_hash: Optional[str] = None         # OPTIONAL - SHA256 hash
    last_validated: float = 0               # REQUIRED - Last validation timestamp
```

### SecretValidationReport DataClass
```python
@dataclass
class SecretValidationReport:
    is_valid: bool                          # REQUIRED - Overall validity
    missing_secrets: List[str] = []         # REQUIRED - Missing secrets
    weak_secrets: List[str] = []            # REQUIRED - Weak secrets
    warnings: List[str] = []                # REQUIRED - Validation warnings
    compliance_score: float = 0.0           # REQUIRED - Compliance %
    rotation_required: List[str] = []       # REQUIRED - Secrets needing rotation
    strength_scores: Dict[str, int] = {}    # REQUIRED - Strength scores
```

### Exceptions
```python
class SecretValidationError(Exception)     # Secret validation failed
class SecretNotConfiguredError(Exception)  # Required secret not set
```

---

## Function Signatures (Contracts)

### `SecretManager.__init__(self) -> None`
**Pre:** None
**Post:** SecretManager initialized with cache, metadata loaded
**Raises:** No
**Retry:** No
**Side Effects:** Loads metadata from environment

### `SecretManager._load_metadata(self) -> None`
**Pre:** None
**Post:** Metadata loaded for all defined secrets
**Raises:** No
**Retry:** No
**Side Effects:** Populates _metadata dict

### `SecretManager._hash_secret(self, value: str) -> str`
**Pre:** value is non-empty string
**Post:** Returns SHA256 hash
**Raises:** No
**Retry:** No
**Side Effects:** None

### `SecretManager._detect_secret_rotation(self, name: str, current_value: str) -> bool`
**Pre:** name in _metadata, current_value exists
**Post:** Returns True if secret rotated since last check
**Raises:** No
**Retry:** No
**Side Effects:** Updates metadata if rotated

### `SecretManager.calculate_strength_score(self, value: str, definition: SecretDefinition) -> int`
**Pre:** definition valid
**Post:** Returns strength score 0-100
**Raises:** No
**Retry:** No
**Side Effects:** Logs warnings for weak patterns

**Scoring:**
- Length: up to 40 points (len * 2)
- Character variety: up to 40 points (10 each for upper, lower, digit, special)
- Entropy: up to 20 points (unique chars)
- Penalty: -30 points for weak patterns

### `SecretManager.get(self, key: str, default: Optional[str] = None, mask: bool = True) -> Optional[str]`
**Pre:** None
**Post:** Returns secret value or default
**Raises:** SecretNotConfiguredError if not found and no default
**Retry:** No
**Side Effects:** Caches value, adds to masked set

### `SecretManager.require(self, key: str, mask: bool = True) -> str`
**Pre:** None
**Post:** Returns secret value
**Raises:** SecretNotConfiguredError if not found
**Retry:** No
**Side Effects:** Caches value, adds to masked set

### `SecretManager.get_safe(self, key: str, default: str = "") -> str`
**Pre:** None
**Post:** Returns config value (non-sensitive)
**Raises:** No
**Retry:** No
**Side Effects:** None (no caching, no masking)

### `SecretManager.mask_value(self, value: str, visible_chars: int = 4) -> str`
**Pre:** value is string
**Post:** Returns masked value (e.g., "abcd...xyz")
**Raises:** No
**Retry:** No
**Side Effects:** None

### `SecretManager.is_masked(self, value: str) -> bool`
**Pre:** value is string
**Post:** Returns True if value should be masked
**Raises:** No
**Retry:** No
**Side Effects:** None

### `SecretManager.validate_secret(self, definition: SecretDefinition) -> bool`
**Pre:** definition valid
**Post:** Returns True if valid, False if weak pattern
**Raises:** SecretValidationError for validation failures
**Retry:** No
**Side Effects:** Detects rotation, logs strength warnings

**Validations:**
- Required in production check
- Length check (min/max)
- Weak pattern detection (returns False, doesn't raise)
- Character requirements (upper, lower, digit, special)
- Rotation detection
- Strength calculation

### `SecretManager.validate_all(self) -> SecretValidationReport`
**Pre:** SECRET_DEFINITIONS populated
**Post:** Returns validation report with compliance score
**Raises:** No
**Retry:** No
**Side Effects:** Validates all secrets, calculates compliance

### `SecretManager.generate_secure_secret(self, length: int = 32, ...) -> str`
**Pre:** At least one character type selected
**Post:** Returns cryptographically secure random secret
**Raises:** ValueError if no character types selected
**Retry:** No
**Side Effects:** None (uses secrets module)

### `SecretManager.check_rotation_needed(self, secret_name: str, rotation_days: Optional[int] = None) -> bool`
**Pre:** secret_name in _metadata
**Post:** Returns True if rotation needed
**Raises:** No
**Retry:** No
**Side Effects:** None

### `SecretManager.get_secret_metadata(self, secret_name: str) -> Optional[SecretMetadata]`
**Pre:** None
**Post:** Returns metadata or None
**Raises:** No
**Retry:** No
**Side Effects:** None

### `SecretManager.get_connection_string(self, db_type: str) -> str`
**Pre:** db_type is "postgresql", "redis", or "questdb"
**Post:** Returns connection string built from env vars
**Raises:** SecretNotConfiguredError, ValueError
**Retry:** No
**Side Effects:** None

**CRITICAL:** NEVER hardcodes credentials

### `SecretManager.clear_cache(self) -> None`
**Pre:** None
**Post:** Cache cleared
**Raises:** No
**Retry:** No
**Side Effects:** Clears _cache and _masked_values

---

## Module-Level Functions

### `get_secret(key: str, default: Optional[str] = None, mask: bool = True) -> Optional[str]`
**Pre:** None
**Post:** Returns secret from global manager
**Raises:** SecretNotConfiguredError if not found and no default
**Retry:** No
**Side Effects:** None

### `require_secret(key: str, mask: bool = True) -> str`
**Pre:** None
**Post:** Returns secret from global manager
**Raises:** SecretNotConfiguredError if not found
**Retry:** No
**Side Effects:** None

### `validate_secrets_configured() -> SecretValidationReport`
**Pre:** None
**Post:** Returns validation report
**Raises:** No
**Retry:** No
**Side Effects:** None

### `get_connection_string(db_type: str) -> str`
**Pre:** db_type valid
**Post:** Returns connection string
**Raises:** SecretNotConfiguredError, ValueError
**Retry:** No
**Side Effects:** None

**CRITICAL:** RULE 28 COMPLIANT - no hardcoded credentials

### `mask_secret(value: str, visible_chars: int = 4) -> str`
**Pre:** value is string
**Post:** Returns masked value
**Raises:** No
**Retry:** No
**Side Effects:** None

### `is_production() -> bool`
**Pre:** None
**Post:** Returns True if in production
**Raises:** No
**Retry:** No
**Side Effects:** None

### `generate_secure_secret(length: int = 32, use_special_chars: bool = True) -> str`
**Pre:** None
**Post:** Returns secure random secret
**Raises:** No
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] NO hardcoded secrets in code
- [ ] All secrets loaded from environment variables
- [ ] Secret validation enforces strength requirements
- [ ] Weak patterns detected and logged
- [ ] Production secrets required (fail if missing)
- [ ] Development secrets optional (with defaults)
- [ ] Secret masking in logs (first/last 4 chars)
- [ ] Rotation detection (hash comparison)
- [ ] Compliance score calculated
- [ ] Connection strings built from env vars (never hardcoded)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md`

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| No Hardcoded Secrets | CRITICAL_RULES.md | NEVER hardcode secrets | ✅ OK |
| Environment Variables | CRITICAL_RULES.md | Load from env only | ✅ OK |
| Secret Masking | CRITICAL_RULES.md | Mask in logs | ✅ OK |
| Validation | BASE_RULES.md | Validate before use | ✅ OK |
| Type Safety | BASE_RULES.md | All functions typed | ✅ OK |
| Cryptographic Random | CRITICAL_RULES.md | Use secrets module | ✅ OK |
| Hashing | CRITICAL_RULES.md | SHA256 for rotation | ✅ OK |
| Production Detection | CRITICAL_RULES.md | ENVIRONMENT check | ✅ OK |

---

## Dependencies
- **External:** hashlib, logging, os, secrets, time, dataclasses, enum, typing
- **Internal:** None

---

## Required Tests
- **test_secret_manager.py:**
  - Test get_secret with default
  - Test get_secret without default raises
  - Test require_secret raises if missing
  - Test secret masking
  - Test strength score calculation
  - Test weak pattern detection
  - Test validation passes strong secrets
  - Test validation rejects short secrets
  - Test validation rejects weak patterns
  - Test rotation detection
  - Test compliance score calculation
  - Test production detection
  - Test generate_secure_secret
  - Test get_connection_string for postgresql
  - Test get_connection_string for redis
  - Test get_connection_string for questdb
  - Test SECRET_DEFINITIONS all defined
  - Test clear_cache

---

## Notes
- CRITICAL: This is Rule 28 compliance module
- ALL secrets MUST come from environment variables
- NEVER use default values in production
- Mask ALL secrets in logs
- Rotate secrets every 90 days
- Compliance score < 80% = invalid
- Weak patterns: password, secret, changeme, default, 12345678, admin, test
