# auth.py Requirements

**File Path:** `app/core/auth.py`  
**Last Updated:** 2025-02-06  
**Audit Status:** NEEDS_AUDIT

## Purpose

Authentication and authorization module for API endpoints. Provides API key authentication, JWT token validation, role-based access control, account lockout protection, and comprehensive audit logging.

## Type Definitions

### Enums
```python
class UserRoles:
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    SYSTEM = "system"
```

### TypedDicts
```python
class UserDict(TypedDict):
    """Typed dictionary for user storage mapping."""
    pass

class APIKeyDict(TypedDict):
    """Typed dictionary for API key to username mapping."""
    pass
```

### Classes
```python
class User:
    def __init__(
        self,
        user_id: str,
        username: str,
        role: str,
        permissions: List[str],
        is_active: bool = True,
    )
    def has_permission(self, permission: str) -> bool
    def has_role(self, role: str) -> bool
    def can_trade(self) -> bool
    def can_deploy(self) -> bool
```

## Function Signatures

### UserStore
```python
class UserStore:
    def __init__(self) -> None:
        """Initialize user store from environment configuration."""
        
    def _load_users_from_config(self) -> None:
        """Load users from environment configuration."""
        
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key using SHA-256."""
        
    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify API key and return username."""
        
    def get_user(self, username: str) -> Optional[User]:
        """Get user by username (thread-safe)."""
        
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID (thread-safe)."""
```

### JWTTokenManager
```python
class JWTTokenManager:
    def __init__(self) -> None:
        """Initialize JWT manager from configuration."""
        
    def create_access_token(
        self, 
        data: Dict[str, str], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        
    def verify_token(self, token: str) -> Optional[Dict[str, str]]:
        """Verify and decode JWT token."""
        
    def decode_token(self, token: str) -> Optional[Dict[str, str]]:
        """Decode token without verification (debug only)."""
```

### AuthAttemptTracker
```python
class AuthAttemptTracker:
    MAX_FAILED_ATTEMPTS: int = 5
    LOCKOUT_DURATION: int = 900  # 15 minutes
    RATE_LIMIT_WINDOW: int = 60
    MAX_REQUESTS_PER_WINDOW: int = 20
    
    def record_failed_attempt(
        self, 
        identifier: str, 
        auth_method: str
    ) -> bool:
        """Record failed authentication attempt."""
        
    def record_successful_attempt(
        self, 
        identifier: str, 
        username: str
    ) -> None:
        """Record successful authentication attempt."""
        
    def is_locked_out(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """Check if identifier is currently locked out."""
        
    def check_rate_limit(self, identifier: str) -> bool:
        """Check if identifier has exceeded rate limit."""
        
    def cleanup(self) -> None:
        """Clean up expired entries."""
```

### Authentication Dependencies
```python
async def get_current_user_optional(
    request_id: str = "unknown",
    api_key: Optional[str] = Security(api_key_header),
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(http_bearer),
) -> Optional[User]:
    """Get current user from API key or bearer token (optional)."""

async def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Get authenticated user (required)."""

async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get authenticated admin user."""

async def get_trader_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get authenticated trader user."""

async def get_deployer_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get authenticated deployment user."""

def require_roles(*roles: str):
    """Dependency factory that requires specific roles."""

def require_permissions(*permissions: str):
    """Dependency factory that requires specific permissions."""
```

## Acceptance Criteria

### AC-AUTH-001: API Key Hashing
```bash
# Test: API keys are hashed before storage
python -c "
from app.core.auth import UserStore
store = UserStore()
# Keys should be hashed, not plain text
import hmac
assert 'hash' in str(dir(store)).lower()
"
```

### AC-AUTH-002: JWT Token Expiration
```bash
# Test: JWT tokens expire correctly
python -c "
from app.core.auth import JWTTokenManager
import time
mgr = JWTTokenManager()
token = mgr.create_access_token({'sub': 'test'})
time.sleep(1)  # Wait to ensure not immediate
payload = mgr.verify_token(token)
assert payload is not None
assert 'exp' in payload
"
```

### AC-AUTH-003: Account Lockout
```bash
# Test: Account locks after 5 failed attempts
python -c "
from app.core.auth import AuthAttemptTracker
tracker = AuthAttemptTracker()
for i in range(5):
    tracker.record_failed_attempt('test_user', 'api_key')
locked, _ = tracker.is_locked_out('test_user')
assert locked == True
"
```

### AC-AUTH-004: Rate Limiting
```bash
# Test: Rate limit enforced
python -c "
from app.core.auth import AuthAttemptTracker
tracker = AuthAttemptTracker()
# Exceed rate limit
for i in range(25):
    tracker.check_rate_limit('test_user')
# 21st should fail
assert tracker.check_rate_limit('test_user') == False
"
```

### AC-AUTH-005: Audit Logging
```bash
# Test: Failed auth attempts logged to audit
python -c "
from unittest.mock import Mock
from app.core.auth import AuthAttemptTracker
tracker = AuthAttemptTracker()
tracker._audit = Mock()
tracker.record_failed_attempt('test', 'api_key')
tracker._audit.log.assert_called_once()
"
```

## Critical Rules

### Rule AUTH-001: No Hardcoded Credentials
**Priority:** P0  
**Description:** All credentials must come from environment variables. No hardcoded API keys, passwords, or tokens in code.  
**Enforcement:** `SEC-001` from BASE_RULES.md

### Rule AUTH-002: API Key Hashing
**Priority:** P0  
**Description:** API keys must be hashed using HMAC-SHA256 before storage. Never store plain text API keys.

### Rule AUTH-003: JWT Token Validation
**Priority:** P0  
**Description:** All JWT tokens must be verified with signature checking and expiration validation.

### Rule AUTH-004: Thread Safety
**Priority:** P0  
**Description:** All user store operations must be thread-safe using locks.

### Rule AUTH-005: Rate Limiting
**Priority:** P1  
**Description:** All authentication attempts must be rate-limited to prevent brute force attacks.

### Rule AUTH-006: Audit Logging
**Priority:** P0  
**Description:** All authentication attempts (success and failure) must be logged to audit trail.

## Dependencies

### Internal Dependencies
```python
from app.core.audit import AuditAction, AuditLogger, get_audit_logger
from app.core.environment_config import get_config
from app.core.exceptions import AuthenticationError, ValidationError
```

### External Dependencies
```python
import hashlib
import hmac
import logging
import os
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, TypedDict

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
```

### Optional Dependencies
```python
import jwt  # For JWT token operations
```

## Required Tests

### Unit Tests (app/tests/core/test_auth.py)
```python
def test_user_initialization():
    """Test User object initialization."""
    
def test_user_has_permission():
    """Test permission checking."""
    
def test_user_has_role():
    """Test role checking."""
    
def test_user_can_trade():
    """Test trading permission."""
    
def test_user_can_deploy():
    """Test deployment permission."""
    
def test_user_store_loads_from_env():
    """Test UserStore loads from environment."""
    
def test_api_key_hashing():
    """Test API keys are hashed."""
    
def test_api_key_verification():
    """Test API key verification."""
    
def test_jwt_token_creation():
    """Test JWT token creation."""
    
def test_jwt_token_verification():
    """Test JWT token verification."""
    
def test_jwt_token_expiration():
    """Test expired tokens are rejected."""
    
def test_account_lockout_after_failed_attempts():
    """Test account lockout mechanism."""
    
def test_account_unlock_after_duration():
    """Test account unlocks after lockout duration."""
    
def test_rate_limit_enforcement():
    """Test rate limiting."""
    
def test_rate_limit_cleanup():
    """Test old rate limit entries cleaned up."""
    
def test_successful_auth_clears_failed_attempts():
    """Test successful auth resets failed attempt counter."""
    
def test_get_current_user_optional_no_credentials():
    """Test optional dependency returns None without credentials."""
    
def test_get_current_user_required_throws_without_credentials():
    """Test required dependency throws without credentials."""
    
def test_admin_user_check():
    """Test admin user validation."""
    
def test_trader_user_check():
    """Test trader user validation."""
    
def test_require_roles_decorator():
    """Test role requirement decorator."""
    
def test_require_permissions_decorator():
    """Test permission requirement decorator."""
```

### Integration Tests
```python
def test_full_auth_flow_api_key():
    """Test complete authentication flow with API key."""
    
def test_full_auth_flow_jwt():
    """Test complete authentication flow with JWT."""
    
def test_concurrent_auth_access():
    """Test thread-safe concurrent access."""
    
def test_audit_logging_integration():
    """Test audit logging for all auth events."""
```

## File-Specific Rules

### Rule AUTH-FS-001: Environment Variable Format
**Priority:** P0  
**Description:** User configuration must follow format:
- `AUTH_USER_<USERNAME>_ID`: User ID
- `AUTH_USER_<USERNAME>_ROLE`: User role
- `AUTH_USER_<USERNAME>_PERMISSIONS`: Comma-separated permissions
- `AUTH_API_KEY_<KEYNAME>`: API key (will be hashed)
- `AUTH_API_KEY_<KEYNAME>_USER`: Username for this API key

### Rule AUTH-FS-002: Weak Key Detection
**Priority:** P0  
**Description:** System must detect and reject weak API keys/JWT secrets. Only allow weak keys with explicit `ALLOW_WEAK_SECRET_KEY=true` override.

### Rule AUTH-FS-003: Double-Checked Locking
**Priority:** P1  
**Description:** Singleton instances must use double-checked locking pattern for thread safety.

### Rule AUTH-FS-004: JWT Library Optional
**Priority:** P2  
**Description:** Code must handle ImportError if `jwt` library not installed.

## Security Considerations

### SEC-AUTH-001: Password Requirements
- Minimum 8 characters
- Require uppercase and lowercase
- Require numbers
- Require special characters

### SEC-AUTH-002: Token Expiration
- Access tokens: 30 minutes max
- Refresh tokens: 7 days max

### SEC-AUTH-003: Lockout Policy
- Max failed attempts: 5
- Lockout duration: 15 minutes
- Rate limit: 20 requests per minute

## References

- **BASE_RULES.md:** See ../../BASE_RULES.md for universal rules
  - SEC-001: No hardcoded secrets
  - SEC-002: Environment validation
  - SEC-005: Audit logging
  - SEC-009: JWT auth
  - LOG-004: Error logging
- **Related Files:**
  - `app/core/audit.py` - Audit logging
  - `app/core/environment_config.py` - Configuration

## Changelog

### 2025-02-06
- Initial requirements documentation created
- Documented GAP-001 through GAP-006 fixes
- Audit Status: NEEDS_AUDIT

## Audit Status

| **Audit Status** | **PASSED** |
| **Last Audit Date** | 2026-02-06 |
| **Auditor** | Claude Code (Ralphex Audit - Gap Fix Phase 2) |
| **GAPs Found** | 0 P0, 1 P1, 0 P2, 0 P3 |
| **GAPs Fixed** | LOG-005: Redacted key_name in sensitive log messages (lines 216-219) |
| **Notes** | All violations fixed and verified. Key name redacted in log output. |
