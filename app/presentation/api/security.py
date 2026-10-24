"""
Security utilities for API endpoints.

This module provides decorators and middleware for:
- Rate limiting (in-memory, suitable for single-instance deployments)
- Authentication/authorization (placeholder for future JWT integration)
- Audit logging for sensitive operations

GAP Fixes:
- API-005: Added security decorators (rate_limit, require_auth, audit_log)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, TypeVar, cast

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from . import audit_logger, get_correlation_id

if TYPE_CHECKING:
    from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., object])

# Roles válidos del principal único (Fase 1 del plan de producción paper).
VALID_ROLES: tuple[str, ...] = ("viewer", "trader", "admin")


# ============================================================================
# Rate Limiting
# ============================================================================


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    This implementation is suitable for single-instance deployments.
    For multi-instance deployments, consider using Redis-based rate limiting.

    Thread-safety: This implementation uses asyncio.Lock for concurrency safety.
    """

    def __init__(self, default_max_requests: int = 100, default_window_seconds: int = 60):
        """
        Initialize the rate limiter.

        Args:
            default_max_requests: Default maximum requests per window
            default_window_seconds: Default time window in seconds
        """
        self.default_max_requests = default_max_requests
        self.default_window_seconds = default_window_seconds

        # Store request timestamps by key: {key: [timestamp1, timestamp2, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Cleanup task
        self._cleanup_task: asyncio.Task | None = None

    def _get_client_key(self, request: Request) -> str:
        """
        Extract a unique key for rate limiting from the request.

        Args:
            request: FastAPI Request object

        Returns:
            str: Unique key for the client
        """
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"

        # Try to get API key from headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"api_key:{key_hash}"

        # Fall back to client IP
        # Handle proxies by checking X-Forwarded-For or X-Real-IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            real_ip = request.headers.get("X-Real-IP")
            client_ip = real_ip if real_ip else request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    async def is_allowed(
        self,
        key: str,
        max_requests: int | None = None,
        window_seconds: int | None = None,
    ) -> tuple[bool, dict[str, int | str]]:
        """
        Check if a request is allowed under rate limiting rules.

        Args:
            key: Unique key for the client
            max_requests: Maximum requests allowed (uses default if None)
            window_seconds: Time window in seconds (uses default if None)

        Returns:
            Tuple[bool, Dict]: (is_allowed, rate_limit_info)
        """
        max_requests = max_requests or self.default_max_requests
        window_seconds = window_seconds or self.default_window_seconds

        current_time = time.time()
        window_start = current_time - window_seconds

        async with self._lock:
            # Get existing requests for this key
            requests = self._requests[key]

            # Filter out requests outside the current window
            requests = [ts for ts in requests if ts > window_start]
            self._requests[key] = requests

            # Check if limit is exceeded
            request_count = len(requests)
            is_allowed = request_count < max_requests

            # Add current request if allowed
            if is_allowed:
                requests.append(current_time)

            # Calculate rate limit info for headers
            reset_time = max(requests) if requests else current_time
            reset_at = datetime.fromtimestamp(reset_time + window_seconds).isoformat()

            return is_allowed, {
                "limit": max_requests,
                "remaining": max_requests - request_count,
                "reset": reset_at,
                "window": window_seconds,
            }

    async def cleanup_old_entries(self, older_than_seconds: int = 3600):
        """
        Clean up old entries to prevent memory leaks.

        Args:
            older_than_seconds: Remove entries older than this
        """
        cutoff_time = time.time() - older_than_seconds

        async with self._lock:
            keys_to_remove = []

            for key, timestamps in self._requests.items():
                # Filter old timestamps
                self._requests[key] = [ts for ts in timestamps if ts > cutoff_time]

                # Mark empty keys for removal
                if not self._requests[key]:
                    keys_to_remove.append(key)

            # Remove empty keys
            for key in keys_to_remove:
                del self._requests[key]

            if keys_to_remove:
                logger.debug(f"Cleaned up {len(keys_to_remove)} old rate limit entries")


# Global rate limiter instance
_global_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


def rate_limit(
    max_requests: int = 100,
    window_seconds: int = 60,
    key_func: Callable[[Request], str] | None = None,
) -> Callable[[F], F]:
    """
    Decorator to apply rate limiting to an endpoint.

    Args:
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds
        key_func: Optional function to extract rate limit key from request

    Returns:
        Decorator function

    Example:
        @router.get("/api/data")
        @rate_limit(max_requests=10, window_seconds=60)
        async def get_data():
            return {"data": "..."}
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> object:
            # Extract Request from positional args or ANY keyword argument
            # value (A14: http_request-named parameters skipped rate limiting).
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break

            if not request:
                # No request object, skip rate limiting
                return await func(*args, **kwargs)

            rate_limiter = get_rate_limiter()

            # Get rate limit key
            key = key_func(request) if key_func else rate_limiter._get_client_key(request)

            # Check if allowed
            is_allowed, info = await rate_limiter.is_allowed(key, max_requests, window_seconds)

            # Set rate limit headers
            # Note: These will be attached to the response if possible
            request.state.rate_limit_info = info

            if not is_allowed:
                correlation_id = get_correlation_id()
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "correlation_id": correlation_id,
                        "key": key,
                        "limit": info["limit"],
                        "window": info["window"],
                    },
                )

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": info["limit"],
                        "window": info["window"],
                        "reset": info["reset"],
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": info["reset"],
                        "Retry-After": str(window_seconds),
                    },
                )

            return await func(*args, **kwargs)

        return cast("F", wrapper)

    return decorator


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to apply rate limiting to all requests.

    This middleware adds rate limit headers to responses and handles
    rate limit checking globally or per-route.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,
        window_seconds: int = 60,
        exclude_paths: list[str] | None = None,
    ) -> None:
        """
        Initialize the rate limit middleware.

        Args:
            app: The ASGI application
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response: The response with rate limit headers
        """
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        rate_limiter = get_rate_limiter()
        key = rate_limiter._get_client_key(request)

        # Check rate limit
        is_allowed, info = await rate_limiter.is_allowed(
            key, self.max_requests, self.window_seconds
        )

        # Store info in request state for access in endpoints
        request.state.rate_limit_info = info

        if not is_allowed:
            correlation_id = get_correlation_id()
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "correlation_id": correlation_id,
                    "key": key,
                    "path": request.url.path,
                    "limit": info["limit"],
                },
            )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": info["limit"],
                    "window": info["window"],
                    "reset": info["reset"],
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": info["reset"],
                    "Retry-After": str(self.window_seconds),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = info["reset"]

        return response


# ============================================================================
# Authentication & Authorization
# ============================================================================


class SecurityConfig:
    """Security configuration settings."""

    # NOTE: Move these to environment variables or config file
    AUTH_ENABLED = True  # Authentication must be enabled for production
    AUTH_REQUIRED_BY_DEFAULT = True
    ADMIN_ROLE_REQUIRED = False


# Tracks whether the "no API keys configured" critical error was already
# logged, so a misconfigured deployment logs once instead of per request.
_api_keys_missing_logged = False


def _get_configured_api_keys() -> list[str]:
    """Read valid API keys from configuration.

    Keys are read from the API_ACCESS_KEYS environment variable
    (comma-separated list), falling back to a single API_KEY variable.

    Returns:
        List of configured API keys (empty if none are configured).
    """
    raw_keys = os.getenv("API_ACCESS_KEYS", "")
    keys = [key.strip() for key in raw_keys.split(",") if key.strip()]
    if not keys:
        single_key = os.getenv("API_KEY", "").strip()
        if single_key:
            keys.append(single_key)
    return keys


# Roles por defecto de una clave sin mapeo explícito: puede consultar y
# operar, pero no ejecutar acciones administrativas (resets, umbrales,
# despliegue). El rol admin NUNCA se concede automáticamente (A13).
DEFAULT_API_KEY_ROLES: tuple[str, ...] = ("viewer", "trader")


def _get_key_roles_map() -> dict[str, tuple[str, ...]]:
    """Read the key→roles mapping from the API_KEY_ROLES variable.

    Format: JSON object mapping a FULL key to the list of roles, e.g.::

        API_KEY_ROLES='{"aaaa...": ["admin"], "bbbb...": ["viewer"]}'

    Keys absent from the map keep DEFAULT_API_KEY_ROLES. Unknown roles are
    ignored with a warning (never widened).
    """
    raw = os.getenv("API_KEY_ROLES", "").strip()
    if not raw:
        return {}
    try:
        parsed: Any = json.loads(raw)
    except ValueError:
        logger.warning("API_KEY_ROLES is not valid JSON: role mapping ignored")
        return {}
    if not isinstance(parsed, dict):
        logger.warning("API_KEY_ROLES must be a JSON object: role mapping ignored")
        return {}
    mapping: dict[str, tuple[str, ...]] = {}
    for key, roles in parsed.items():
        if not isinstance(key, str) or not isinstance(roles, list):
            continue
        clean = tuple(r for r in roles if isinstance(r, str) and r in VALID_ROLES)
        if len(clean) != len(roles):
            logger.warning(
                "API_KEY_ROLES contains unknown roles for key %s...: ignored",
                key[:8],
            )
        if clean:
            mapping[key] = clean
    return mapping


@dataclass(frozen=True)
class Principal:
    """Authenticated identity shared by every router (Fase 1).

    One principal object travels through dependencies and decorators alike;
    roles gate authorization (403) while its mere presence proves
    authentication (401 otherwise).
    """

    user_id: str
    roles: tuple[str, ...]
    auth_method: str
    key_prefix: str = ""

    def has_any_role(self, *allowed: str) -> bool:
        """True if the principal holds at least one of ``allowed``."""
        return any(role in self.roles for role in allowed)

    def as_user_dict(self) -> dict[str, Any]:
        """Legacy dict shape consumed by ``require_auth`` and logs."""
        return {
            "id": self.user_id,
            "type": self.auth_method,
            "roles": list(self.roles),
            "key_prefix": self.key_prefix,
        }


def get_principal_from_request(request: Request) -> Principal | None:
    """Resolve the single Principal from the request, fail-closed.

    X-API-Key must constant-time match a key configured via
    API_ACCESS_KEYS/API_KEY; its roles come from API_KEY_ROLES or the
    default (viewer, trader). Bearer tokens stay rejected while JWT is
    unimplemented. No request is authenticated by key length or format.
    """
    global _api_keys_missing_logged

    api_key = request.headers.get("X-API-Key")
    if api_key:
        configured_keys = _get_configured_api_keys()
        if not configured_keys:
            if SecurityConfig.AUTH_ENABLED and not _api_keys_missing_logged:
                logger.critical(
                    "AUTH_ENABLED but no API keys configured: rejecting all "
                    "X-API-Key requests. Set API_ACCESS_KEYS to a comma-separated "
                    "list of valid keys (or API_KEY for a single key) to enable "
                    "API key authentication."
                )
                _api_keys_missing_logged = True
            return None
        _api_keys_missing_logged = False
        for key in configured_keys:
            if hmac.compare_digest(api_key.encode("utf-8"), key.encode("utf-8")):
                roles = _get_key_roles_map().get(key, DEFAULT_API_KEY_ROLES)
                return Principal(
                    user_id=f"api_key_{key[:8]}",
                    roles=roles,
                    auth_method="api_key",
                    key_prefix=api_key[:8],
                )
        return None

    # JWT bearer authentication is not implemented yet: reject unvalidated
    # tokens instead of trusting them (fail-closed).
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return None

    # A previously resolved principal on request state (set by
    # get_current_principal upstream in the same request).
    return getattr(request.state, "principal", None)


async def get_current_principal(request: Request) -> Principal:
    """FastAPI dependency: authenticate or raise 401 (never 500).

    Mounted at router level for protect-by-default; endpoints that need
    authorization use require_roles instead/as well.
    """
    if not SecurityConfig.AUTH_ENABLED:
        # Auth explicitly disabled (development flag): anonymous principal.
        principal = Principal(user_id="anonymous", roles=(), auth_method="disabled")
        request.state.principal = principal
        request.state.user = principal.as_user_dict()
        return principal

    principal = get_principal_from_request(request)
    if principal is None:
        logger.warning(
            "Authentication failed: no valid credentials",
            extra={"path": request.url.path, "method": request.method},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Authentication required",
                "message": "Valid authentication credentials required",
            },
            headers={"WWW-Authenticate": 'Bearer realm="algotrading", X-API-Key'},
        )

    request.state.principal = principal
    # Backwards-compatible attribute for code reading request.state.user.
    request.state.user = principal.as_user_dict()
    return principal


def require_roles(*allowed_roles: str) -> Callable[[Request], Any]:
    """FastAPI dependency factory: require at least one of ``allowed_roles``.

    Usage::

        @router.post("/reset")
        async def reset(principal: Principal = Depends(require_roles("admin"))):
            ...
    """
    valid = tuple(role for role in allowed_roles if role in VALID_ROLES)
    if len(valid) != len(allowed_roles):
        raise ValueError(
            f"Unknown roles {set(allowed_roles) - set(VALID_ROLES)}; valid: {VALID_ROLES}"
        )

    async def dependency(request: Request) -> Principal:
        principal = await get_current_principal(request)
        if valid and not principal.has_any_role(*valid):
            logger.warning(
                "Authorization failed: insufficient permissions",
                extra={
                    "user_id": principal.user_id,
                    "required_roles": list(valid),
                    "user_roles": list(principal.roles),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient permissions",
                    "message": f"This endpoint requires one of the following roles: {', '.join(valid)}",
                    "required_roles": list(valid),
                },
            )
        return principal

    return dependency


def get_user_from_request(request: Request) -> dict[str, Any] | None:
    """
    Extract user information from the request (legacy dict shape).

    Delegates to get_principal_from_request so decorators and dependencies
    share ONE authentication source; the returned dict carries the
    principal's roles.
    """
    principal = get_principal_from_request(request)
    return principal.as_user_dict() if principal else None


def require_auth(
    allow_api_key: bool = True,
    roles: list[str] | None = None,
    require_verified: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to require authentication for an endpoint.

    This decorator checks for authenticated users and optionally verifies roles.

    Args:
        allow_api_key: Whether to allow API key authentication
        roles: Optional list of required roles (user must have at least one)
        require_verified: Whether to require email verification

    Returns:
        Decorator function

    Example:
        @router.post("/api/trade")
        @require_auth(roles=["trader", "admin"])
        async def execute_trade():
            return {"status": "executed"}
    """
    del allow_api_key  # aceptado por compatibilidad; sin uso aquí

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> object:
            # Extract Request from positional args or ANY keyword argument
            # value: FastAPI injects parameters by name, and several routers
            # declare it as http_request (A14).
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break

            if not request:
                logger.warning("Authentication check failed: No request object")
                if SecurityConfig.AUTH_ENABLED:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            "error": "Authentication required",
                            "message": "Valid authentication credentials required",
                        },
                    )
                # Auth not enabled, allow request
                return await func(*args, **kwargs)

            # Check if auth is enabled
            if not SecurityConfig.AUTH_ENABLED:
                logger.warning(
                    "Authentication required but not configured",
                    extra={"endpoint": func.__name__},
                )
                # Log that this endpoint would require auth if enabled
                # For now, allow the request but log a warning
                return await func(*args, **kwargs)

            # Get user from request
            user = get_user_from_request(request)

            if not user:
                correlation_id = get_correlation_id()
                logger.warning(
                    "Authentication failed: No valid credentials",
                    extra={"correlation_id": correlation_id, "endpoint": func.__name__},
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "Authentication required",
                        "message": "Valid authentication credentials required",
                    },
                    headers={
                        "WWW-Authenticate": 'Bearer realm="algotrading"',
                    },
                )

            # Check role requirements
            if roles:
                user_roles = user.get("roles", [])
                if not any(role in user_roles for role in roles):
                    correlation_id = get_correlation_id()
                    logger.warning(
                        "Authorization failed: Insufficient permissions",
                        extra={
                            "correlation_id": correlation_id,
                            "user_id": user.get("id"),
                            "required_roles": roles,
                            "user_roles": user_roles,
                        },
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "error": "Insufficient permissions",
                            "message": f"This endpoint requires one of the following roles: {', '.join(roles)}",
                            "required_roles": roles,
                        },
                    )

            # Check verification requirement
            if require_verified and not user.get("is_verified", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Email verification required",
                        "message": "Please verify your email address to access this resource",
                    },
                )

            # Store user in request state for access in endpoint
            request.state.user = user

            return await func(*args, **kwargs)

        return cast("F", wrapper)

    return decorator


def require_admin(func: F) -> F:
    """
    Decorator to require admin role for an endpoint.

    This is a shorthand for @require_auth(roles=["admin"]).

    Args:
        func: The function to decorate

    Returns:
        Callable: Wrapped function requiring admin role

    Example:
        @router.delete("/api/users/{user_id}")
        @require_admin
        async def delete_user(user_id: str):
            return {"message": "User deleted"}
    """
    return require_auth(roles=["admin"])(func)


# ============================================================================
# Audit Logging
# ============================================================================


def audit_log(
    operation: str,
    log_args: bool = False,
    log_result: bool = False,
    sensitive_params: list[str] | None = None,
) -> Callable[[F], F]:
    """
    Decorator to add comprehensive audit logging to an endpoint.

    Args:
        operation: Name of the operation for audit trail
        log_args: Whether to log function arguments
        log_result: Whether to log function return values
        sensitive_params: List of parameter names to redact from logs

    Returns:
        Decorator function

    Example:
        @router.post("/api/trade")
        @audit_log("trade_execution", log_args=True, sensitive_params=["api_key"])
        async def execute_trade(symbol: str, quantity: int):
            return {"status": "executed"}
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> object:
            correlation_id = get_correlation_id()
            start_time = time.time()

            # Extract request for context
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request_candidate = kwargs.get("request")
                if isinstance(request_candidate, Request):
                    request = request_candidate

            # Prepare audit log data
            audit_data: dict[str, object] = {
                "operation": operation,
                "function": func.__name__,
                "correlation_id": correlation_id,
                "start_time": datetime.utcnow().isoformat(),
            }

            # Add request context if available
            if request:
                audit_data["method"] = request.method
                audit_data["path"] = request.url.path
                client_id = getattr(request.state, "user_id", None) or request.headers.get(
                    "X-Client-ID"
                )
                if client_id:
                    audit_data["client_id"] = client_id

            # Log arguments if requested
            if log_args:
                args_to_log = {}
                for key, value in kwargs.items():
                    # Redact sensitive parameters
                    if sensitive_params and key in sensitive_params:
                        args_to_log[key] = "***REDACTED***"
                    elif not key.startswith("_"):  # Skip private params
                        # Convert to string safely
                        try:
                            args_to_log[key] = str(value)[:1000]  # Limit length
                        except Exception:
                            args_to_log[key] = "<unable to serialize>"
                audit_data["args"] = args_to_log

            # Log operation start
            logger.info("Audit: Operation started", extra={"audit": audit_data})

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                audit_data["duration_ms"] = round(duration_ms, 2)
                audit_data["status"] = "success"

                # Log result if requested
                if log_result and result is not None:
                    try:
                        audit_data["result"] = str(result)[:1000]  # Limit length
                    except Exception:
                        audit_data["result"] = "<unable to serialize>"

                # Log success
                logger.info("Audit: Operation completed", extra={"audit": audit_data})

                # Also log via audit_logger if request available
                if request:
                    audit_logger.log_action(
                        action=operation,
                        method=request.method,
                        path=request.url.path,
                        details={"duration_ms": duration_ms, "status": "success"},
                    )

                return result

            except Exception as e:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                audit_data["duration_ms"] = round(duration_ms, 2)
                audit_data["status"] = "failed"
                audit_data["error"] = {
                    "type": type(e).__name__,
                    "message": str(e),
                    "stack_trace": traceback.format_exc(),
                }

                # Log failure
                logger.error(
                    "Audit: Operation failed",
                    extra={"audit": audit_data},
                    exc_info=True,
                )

                # Also log via audit_logger if request available
                if request:
                    audit_logger.log_error(
                        method=request.method,
                        path=request.url.path,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        stack_trace=traceback.format_exc(),
                    )

                raise

        return cast("F", wrapper)

    return decorator


# ============================================================================
# Security Headers
# ============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds headers like:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response: The response with security headers
        """
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


# ============================================================================
# CORS Configuration
# ============================================================================


def get_cors_config() -> dict[str, list[str] | bool | int]:
    """
    Get CORS configuration for FastAPI.

    Returns:
        Dict: CORS configuration

    TODO: Move to environment variables or config file
    """
    return {
        "allow_origins": [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
        ],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Client-ID",
            "X-Correlation-ID",
        ],
        "expose_headers": [
            "X-Correlation-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        "max_age": 600,
    }


__all__ = [
    "RateLimitMiddleware",
    # Rate limiting
    "RateLimiter",
    "SecurityConfig",
    # Security headers
    "SecurityHeadersMiddleware",
    # Audit logging
    "audit_log",
    # CORS
    "get_cors_config",
    "get_rate_limiter",
    "get_user_from_request",
    "rate_limit",
    "require_admin",
    # Authentication
    "require_auth",
]
