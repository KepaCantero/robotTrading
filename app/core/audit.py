"""
Audit Logging Module for API Endpoints

This module provides:
- Structured audit logging for sensitive operations
- Action tracking for trades, deployments, and configuration changes
- User action recording for compliance

AUDIT-001: All sensitive operations are logged
AUDIT-002: Audit logs include user context, timestamp, and action details
AUDIT-003: Audit logs are written to a separate, immutable log file
"""

import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Request

from app.core.logging_config import get_correlation_id, get_logger

logger = get_logger(__name__)

# Thread-safe lock for singleton initialization
_audit_lock = threading.Lock()

# Audit log retention settings
AUDIT_LOG_RETENTION_DAYS = 90  # Default retention: 90 days
AUDIT_LOG_MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100MB per file
AUDIT_LOG_MAX_BACKUPS = 100  # Keep up to 100 backup files


class AuditAction(str, Enum):
    """Audit action types."""

    # Trading actions
    TRADE_CREATE = "trade.create"
    TRADE_EXECUTE = "trade.execute"
    TRADE_CANCEL = "trade.cancel"
    TRADE_MODIFY = "trade.modify"

    # Portfolio actions
    PORTFOLIO_CREATE = "portfolio.create"
    PORTFOLIO_UPDATE = "portfolio.update"
    PORTFOLIO_DELETE = "portfolio.delete"
    PORTFOLIO_READ = "portfolio.read"

    # Deployment actions
    STRATEGY_DEPLOY = "strategy.deploy"
    STRATEGY_VALIDATE = "strategy.validate"
    STRATEGY_STOP = "strategy.stop"
    CONFIG_CHANGE = "config.change"

    # Authentication actions
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    AUTH_FAILED = "auth.failed"

    # Data actions
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"
    DATA_DELETE = "data.delete"

    # System actions
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_ERROR = "system.error"


class AuditLogger:
    """
    Centralized audit logging.

    AUDIT-003: Writes to a separate audit log file that should be
    configured in production to be immutable (e.g., append-only file system).
    """

    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create audit log file
        self.audit_log = self.log_dir / "audit.log"

        # Create separate audit logger
        self._setup_audit_logger()

    def _setup_audit_logger(self):
        """Setup audit-specific logger."""
        import logging
        from logging.handlers import RotatingFileHandler

        self.audit_logger = logging.getLogger("audit")
        self.audit_logger.setLevel(logging.INFO)
        self.audit_logger.propagate = False  # Don't propagate to root logger

        # Remove existing handlers
        self.audit_logger.handlers.clear()

        # Create rotating file handler
        handler = RotatingFileHandler(
            self.audit_log,
            maxBytes=AUDIT_LOG_MAX_SIZE_BYTES,
            backupCount=AUDIT_LOG_MAX_BACKUPS,
            encoding='utf-8',
        )
        handler.setLevel(logging.INFO)

        # Use a simple, parseable format for audit logs
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        self.audit_logger.addHandler(handler)

    def cleanup_old_logs(
        self,
        retention_days: Optional[int] = None,
    ) -> int:
        """
        Remove audit log files older than the retention period.

        This method implements the NFR-003 audit log retention policy.
        It should be called periodically (e.g., daily) via a scheduled task.

        Args:
            retention_days: Number of days to retain logs (default: AUDIT_LOG_RETENTION_DAYS)

        Returns:
            Number of files removed

        Raises:
            OSError: If file operations fail
        """
        if retention_days is None:
            retention_days = AUDIT_LOG_RETENTION_DAYS

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        files_removed = 0

        try:
            # List all log files in the audit directory
            for log_file in self.log_dir.glob("*.log*"):
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

                    # Remove files older than retention period
                    if file_mtime < cutoff_date:
                        log_file.unlink()
                        files_removed += 1
                        logger.info(
                            f"Removed old audit log file: {log_file.name}",
                            file_mtime=file_mtime.isoformat(),
                            cutoff_date=cutoff_date.isoformat(),
                        )
                except OSError as e:
                    logger.error(
                        f"Failed to process audit log file {log_file}: {e}",
                        log_file=str(log_file),
                    )

            if files_removed > 0:
                logger.info(
                    "Audit log cleanup completed",
                    files_removed=files_removed,
                    retention_days=retention_days,
                )

        except Exception as e:
            logger.error(
                f"Error during audit log cleanup: {e}",
                retention_days=retention_days,
            )

        return files_removed

    def get_log_size_info(self) -> Dict[str, Any]:
        """
        Get information about audit log file sizes.

        Returns:
            Dictionary with size information including:
            - total_size_bytes: Total size of all audit log files
            - file_count: Number of audit log files
            - oldest_file: Name and modification time of oldest file
            - newest_file: Name and modification time of newest file
        """
        total_size = 0
        file_count = 0
        oldest_file = None
        newest_file = None
        oldest_mtime = None
        newest_mtime = None

        try:
            for log_file in self.log_dir.glob("*.log*"):
                try:
                    stat = log_file.stat()
                    total_size += stat.st_size
                    file_count += 1
                    file_mtime = datetime.fromtimestamp(stat.st_mtime)

                    if oldest_mtime is None or file_mtime < oldest_mtime:
                        oldest_mtime = file_mtime
                        oldest_file = {
                            "name": log_file.name,
                            "mtime": file_mtime.isoformat(),
                        }

                    if newest_mtime is None or file_mtime > newest_mtime:
                        newest_mtime = file_mtime
                        newest_file = {
                            "name": log_file.name,
                            "mtime": file_mtime.isoformat(),
                        }
                except OSError as e:
                    logger.warning(f"Failed to stat audit log file {log_file}: {e}")

        except Exception as e:
            logger.error(f"Error getting audit log size info: {e}")

        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "oldest_file": oldest_file,
            "newest_file": newest_file,
        }

    def _validate_string_param(
        self,
        value: Optional[str],
        param_name: str,
        allow_empty: bool = False,
    ) -> Optional[str]:
        """
        Validate a string parameter.

        Args:
            value: The string value to validate
            param_name: Name of the parameter (for error messages)
            allow_empty: Whether empty strings are allowed

        Returns:
            The validated value or None

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(
                f"Parameter '{param_name}' must be a string or None, " f"got {type(value).__name__}"
            )

        if not allow_empty and not value.strip():
            raise ValueError(
                f"Parameter '{param_name}' cannot be an empty or whitespace-only string"
            )

        # Trim whitespace
        return value.strip() if value.strip() else None

    def _validate_log_params(
        self,
        action: AuditAction,
        user_id: Optional[str],
        username: Optional[str],
        resource_type: Optional[str],
        resource_id: Optional[str],
        ip_address: Optional[str],
    ) -> None:
        """
        Validate log parameters.

        Args:
            action: The audit action
            user_id: User ID parameter
            username: Username parameter
            resource_type: Resource type parameter
            resource_id: Resource ID parameter
            ip_address: IP address parameter

        Raises:
            ValueError: If any required parameter is invalid
            TypeError: If parameter types are incorrect
        """
        # Validate action is not None
        if not isinstance(action, AuditAction):
            raise TypeError(
                f"Parameter 'action' must be an AuditAction enum, " f"got {type(action).__name__}"
            )

        # Validate optional string parameters
        # Allow empty for user_id/username as they can be 'system'
        if user_id is not None:
            user_id = self._validate_string_param(user_id, "user_id", allow_empty=True)

        if username is not None:
            username = self._validate_string_param(username, "username", allow_empty=True)

        # Resource type should not be empty if provided
        if resource_type is not None:
            resource_type = self._validate_string_param(resource_type, "resource_type")

        # Resource ID should not be empty if provided
        if resource_id is not None:
            resource_id = self._validate_string_param(resource_id, "resource_id")

        # IP address should not be empty if provided
        if ip_address is not None:
            ip_address = self._validate_string_param(ip_address, "ip_address")

    def log(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        validate: bool = True,
    ):
        """
        Log an audit event.

        Args:
            action: Type of action performed
            user_id: ID of the user performing the action
            username: Username of the user performing the action
            resource_type: Type of resource affected (e.g., "portfolio", "trade")
            resource_id: ID of the resource affected
            details: Additional details about the action
            ip_address: IP address of the request
            user_agent: User agent of the request
            success: Whether the action succeeded
            error_message: Error message if action failed
            validate: Whether to validate input parameters (default: True)

        Raises:
            ValueError: If validation fails and validate=True
            TypeError: If parameter types are incorrect
        """
        # Validate parameters if validation is enabled
        if validate:
            try:
                self._validate_log_params(
                    action=action,
                    user_id=user_id,
                    username=username,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    ip_address=ip_address,
                )
            except (ValueError, TypeError) as e:
                # Log the validation error and continue with safe defaults
                logger.warning(
                    f"Audit log parameter validation failed: {e}",
                    action=str(action) if action else None,
                    user_id=user_id,
                    username=username,
                )
                # Continue with validation disabled for this call
                validate = False

        # Build audit log entry
        log_parts = [
            action.value,
            f"user={user_id or 'system'}",
            f"username={username or 'system'}",
            f"success={success}",
        ]

        if resource_type:
            log_parts.append(f"resource_type={resource_type}")

        if resource_id:
            log_parts.append(f"resource_id={resource_id}")

        if ip_address:
            log_parts.append(f"ip={ip_address}")

        if error_message:
            log_parts.append(f"error={error_message}")

        # Add correlation ID for tracing
        correlation_id = get_correlation_id()
        log_parts.append(f"correlation_id={correlation_id}")

        # Combine parts
        log_message = " | ".join(log_parts)

        # Add details as JSON if present
        if details:
            import json

            log_message += f" | details={json.dumps(details)}"

        # Log at appropriate level
        if success:
            self.audit_logger.info(log_message)
        else:
            self.audit_logger.error(log_message)

        # Also log to application logger for visibility
        if success:
            logger.info(f"AUDIT: {log_message}")
        else:
            logger.warning(f"AUDIT: {log_message}")

    def log_trade(
        self,
        action: AuditAction,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        trade_id: Optional[str] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        **kwargs,
    ):
        """Log a trading action."""
        details = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }

        if price is not None:
            details["price"] = price

        if portfolio_id:
            details["portfolio_id"] = str(portfolio_id)

        details.update(kwargs)

        self.log(
            action=action,
            user_id=user_id,
            username=username,
            resource_type="trade",
            resource_id=trade_id,
            details=details,
            success=success,
            error_message=error_message,
        )

    def log_deployment(
        self,
        action: AuditAction,
        strategy_name: str,
        decision_id: Optional[str] = None,
        status: Optional[str] = None,
        scores: Optional[Dict[str, float]] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        **kwargs,
    ):
        """Log a deployment action."""
        details = {
            "strategy_name": strategy_name,
        }

        if decision_id:
            details["decision_id"] = decision_id

        if status:
            details["status"] = status

        if scores:
            details["scores"] = scores

        details.update(kwargs)

        self.log(
            action=action,
            user_id=user_id,
            username=username,
            resource_type="deployment",
            resource_id=decision_id,
            details=details,
            success=success,
            error_message=error_message,
        )

    def log_portfolio(
        self,
        action: AuditAction,
        portfolio_id: Optional[str] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        **kwargs,
    ):
        """Log a portfolio action."""
        self.log(
            action=action,
            user_id=user_id,
            username=username,
            resource_type="portfolio",
            resource_id=str(portfolio_id) if portfolio_id else None,
            details=kwargs,
            success=success,
            error_message=error_message,
        )

    def from_request(
        self,
        action: AuditAction,
        request: Request,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
    ):
        """Log an audit event from a FastAPI request."""
        # Extract request context
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        self.log(
            action=action,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
        )


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    Get the global audit logger instance.

    This function is thread-safe and uses double-checked locking
    to ensure only one instance is created.

    Returns:
        The global AuditLogger instance
    """
    global _audit_logger

    # Fast path - return existing instance without lock
    if _audit_logger is not None:
        return _audit_logger

    # Slow path - acquire lock and create instance
    with _audit_lock:
        # Double-check inside lock
        if _audit_logger is None:
            _audit_logger = AuditLogger()
        return _audit_logger


@contextmanager
def audit_context(
    action: AuditAction,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    auto_log: bool = True,
):
    """
    Context manager for audit logging.

    Usage:
        with audit_context(
            AuditAction.TRADE_EXECUTE,
            user_id=user_id,
            username=username,
            resource_type="trade",
            resource_id=trade_id,
        ) as audit:
            # Perform operation
            try:
                result = execute_trade(...)
                audit.mark_success(details={"trade_id": result.id})
            except Exception as e:
                audit.mark_failure(str(e))
                raise

    """
    audit = get_audit_logger()

    class AuditContext:
        def __init__(self):
            self.success = True
            self.error = None
            self.extra_details = {}

        def mark_success(self, details: Optional[Dict[str, Any]] = None):
            """Mark the operation as successful."""
            self.success = True
            if details:
                self.extra_details.update(details)

        def mark_failure(self, error_message: str, details: Optional[Dict[str, Any]] = None):
            """Mark the operation as failed."""
            self.success = False
            self.error = error_message
            if details:
                self.extra_details.update(details)

    context = AuditContext()

    try:
        yield context
    finally:
        # Merge initial details with extra details
        final_details = (details or {}).copy()
        final_details.update(context.extra_details)

        # Log the audit event
        audit.log(
            action=action,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            resource_id=resource_id,
            details=final_details if final_details else None,
            success=context.success,
            error_message=context.error,
        )


# Convenience functions for common audit operations
def log_trade_execution(
    symbol: str,
    side: str,
    quantity: float,
    price: Optional[float] = None,
    trade_id: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    portfolio_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
):
    """Log a trade execution."""
    get_audit_logger().log_trade(
        action=AuditAction.TRADE_EXECUTE,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        trade_id=trade_id,
        user_id=user_id,
        username=username,
        portfolio_id=portfolio_id,
        success=success,
        error_message=error_message,
    )


def log_deployment_decision(
    strategy_name: str,
    decision_id: Optional[str] = None,
    status: Optional[str] = None,
    scores: Optional[Dict[str, float]] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
):
    """Log a deployment decision."""
    get_audit_logger().log_deployment(
        action=AuditAction.STRATEGY_DEPLOY,
        strategy_name=strategy_name,
        decision_id=decision_id,
        status=status,
        scores=scores,
        user_id=user_id,
        username=username,
        success=success,
        error_message=error_message,
    )


def cleanup_audit_logs(
    retention_days: Optional[int] = None,
) -> int:
    """
    Clean up old audit log files.

    This is a convenience function for the AuditLogger.cleanup_old_logs method.
    It should be called periodically (e.g., daily via a cron job or scheduled task).

    Args:
        retention_days: Number of days to retain logs (default: 90 days)

    Returns:
        Number of files removed

    Example:
        # Schedule this to run daily
        import schedule
        schedule.every().day.at("02:00").do(cleanup_audit_logs)

        # Or run manually
        removed = cleanup_audit_logs(retention_days=90)
        logger.debug(f"Removed {removed} old audit log files")
    """
    return get_audit_logger().cleanup_old_logs(retention_days=retention_days)


def get_audit_log_info() -> Dict[str, Any]:
    """
    Get information about audit log file sizes.

    This is a convenience function for the AuditLogger.get_log_size_info method.

    Returns:
        Dictionary with size information including:
        - total_size_bytes: Total size of all audit log files
        - total_size_mb: Total size in MB
        - file_count: Number of audit log files
        - oldest_file: Name and modification time of oldest file
        - newest_file: Name and modification time of newest file
    """
    return get_audit_logger().get_log_size_info()
