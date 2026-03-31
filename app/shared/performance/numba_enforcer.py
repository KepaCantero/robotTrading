"""
Numba Enforcement Module - MANDATORY for All Performance-Critical Code

CRITICAL: This module enforces 100% Numba acceleration across ALL performance-critical code paths.
NO fallbacks. NO exceptions. Numba is REQUIRED.

This module MUST be imported at application startup to verify Numba availability before
any performance-critical code is executed.

Enforcement Rules:
- Rule 19: High Performance Python - Numba mandatory for all numerical code
- Rule 23: High Performance Optimization - No slow code allowed
- Rule 9: Hilpisch Python for Finance - Performance is critical

Author: Performance Enforcement Team
Date: 2026-01-28
Version: 2.0.0 - MANDATORY ENFORCEMENT
"""

from __future__ import annotations

import logging
import os
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# MANDATORY NUMBA CHECK - FAIL FAST IF NOT AVAILABLE
# ============================================================================


def enforce_numba_available() -> None:
    """
    MANDATORY: Verify Numba is available at application startup.

    This function MUST be called before any performance-critical code is executed.
    It will raise a RuntimeError with clear instructions if Numba is not available.

    Raises:
        RuntimeError: If Numba is not installed or version is insufficient

    Example:
        >>> from app.shared.performance.numba_enforcer import enforce_numba_available
        >>> enforce_numba_available()  # Raises if Numba not available
    """
    error_message = None

    try:
        import numba

        numba_version = numba.__version__

        # Parse version to ensure it's >= 0.59.0
        version_parts = numba_version.split(".")
        major = int(version_parts[0])
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0

        if major < 0 or (major == 0 and minor < 59):
            error_message = (
                f"Numba version {numba_version} is insufficient. "
                f"Version 0.59.0 or higher is REQUIRED.\n"
                f"Current version: {numba_version}\n"
                f"Required version: >=0.59.0\n\n"
                f"Upgrade with: pip install --upgrade 'numba>=0.59.0'"
            )
        else:
            logger.info(f"✅ Numba enforcement check passed: Numba {numba_version} available")
            return

    except ImportError as e:
        error_message = (
            "❌ CRITICAL: Numba is REQUIRED for this trading system.\n\n"
            "Numba provides 10-100x performance acceleration for all performance-critical code.\n"
            "This system CANNOT operate efficiently without Numba.\n\n"
            "Installation instructions:\n"
            "  pip install 'numba>=0.59.0'\n\n"
            "For the complete requirements:\n"
            "  pip install -r requirements.txt\n\n"
            "Error details: " + str(e)
        )
    except Exception as e:
        error_message = (
            f"❌ CRITICAL: Unexpected error checking Numba availability: {e}\n\n"
            "Please ensure Numba is properly installed:\n"
            "  pip install --upgrade 'numba>=0.59.0'"
        )

    # If we get here, there's an error - FAIL FAST
    logger.error(error_message)
    raise RuntimeError(error_message)


def get_numba_version() -> Optional[str]:
    """
    Get the installed Numba version.

    Returns:
        Numba version string or None if not installed
    """
    try:
        import numba

        return str(numba.__version__)
    except ImportError:
        return None


def verify_numba_function(func: Callable, *args, **kwargs) -> bool:
    """
    Verify that a function is properly Numba-compiled.

    Args:
        func: Function to verify
        *args: Arguments to test the function with
        **kwargs: Keyword arguments to test the function with

    Returns:
        True if function is Numba-compiled and works correctly

    Raises:
        RuntimeError: If function is not Numba-compiled or fails
    """
    try:
        # Check if function has Numba-specific attributes
        # Numba JIT functions have 'signatures' or '__compiled__' attribute
        has_signatures = hasattr(func, "signatures")
        has_compiled = hasattr(func, "__compiled__")
        is_dispatcher = hasattr(func, "_is_jitted")

        if not (has_signatures or has_compiled or is_dispatcher):
            error_msg = (
                f"❌ Function {func.__name__} is NOT Numba-compiled.\n"
                f"All performance-critical functions MUST use @numba.jit(nopython=True, cache=True)"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Try to execute the function to ensure it works
        func(*args, **kwargs)

        logger.debug(f"✅ Function {func.__name__} is Numba-compiled and working")
        return True

    except Exception as e:
        error_msg = f"❌ Failed to verify Numba compilation for {func.__name__}: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


# ============================================================================
# PERFORMANCE CRITICAL CODE DETECTOR
# ============================================================================


def detect_performance_critical_code(file_path: str) -> list:
    """
    Detect performance-critical code patterns in a Python file.

    Args:
        file_path: Path to Python file to analyze

    Returns:
        List of detected performance-critical patterns
    """
    critical_patterns = []

    try:
        with open(file_path) as f:
            content = f.read()
            lines = content.split("\n")

        # Check for performance-critical patterns
        for i, line in enumerate(lines, 1):
            # NumPy operations without Numba
            if "np." in line and "def " in lines[max(0, i - 5) : i]:
                critical_patterns.append(
                    {"line": i, "type": "numpy_function", "code": line.strip(), "severity": "HIGH"}
                )

            # Pandas operations in loops
            if (".apply(" in line or ".iterrows()" in line) and "for " in lines[max(0, i - 3) : i]:
                critical_patterns.append(
                    {
                        "line": i,
                        "type": "pandas_in_loop",
                        "code": line.strip(),
                        "severity": "CRITICAL",
                    }
                )

            # Calculation functions without Numba decorator
            if "def calculate_" in line or "def compute_" in line:
                # Check previous lines for @numba.jit
                has_numba = False
                for j in range(max(0, i - 10), i):
                    if "@numba" in lines[j] or "@jit" in lines[j]:
                        has_numba = True
                        break

                if not has_numba:
                    critical_patterns.append(
                        {
                            "line": i,
                            "type": "calculation_without_numba",
                            "code": line.strip(),
                            "severity": "CRITICAL",
                        }
                    )

    except Exception as e:
        logger.warning(f"Failed to analyze {file_path}: {e}")

    return critical_patterns


# ============================================================================
# AUTOMATIC ENFORCEMENT AT IMPORT TIME
# ============================================================================

# Perform enforcement check when module is imported
_enforcement_checked = False


def _ensure_enforcement():
    """
    Ensure Numba enforcement check has been performed.

    This is called automatically by the module.
    """
    global _enforcement_checked

    if not _enforcement_checked:
        # Check if we're in a testing environment
        if os.environ.get("TESTING") == "1":
            logger.debug("Skipping Numba enforcement check in testing environment")
            _enforcement_checked = True
            return

        # Perform enforcement check
        enforce_numba_available()
        _enforcement_checked = True


# Auto-enforce on module import (unless in test mode)
if os.environ.get("TESTING") != "1":
    _ensure_enforcement()


# ============================================================================
# CONVENIENCE DECORATORS FOR ENFORCEMENT
# ============================================================================


def require_numba(func: Callable) -> Callable:
    """
    Decorator to enforce that a function uses Numba acceleration.

    This decorator will raise an error if the function is not Numba-compiled.

    Args:
        func: Function to enforce Numba compilation on

    Returns:
        Wrapped function that verifies Numba compilation

    Example:
        >>> @require_numba
        >>> @numba.jit(nopython=True, cache=True)
        >>> def my_function(x):
        ...     return x * 2
    """

    def wrapper(*args, **kwargs):
        # Ensure Numba is available
        enforce_numba_available()

        # Verify function is compiled
        verify_numba_function(func, *args, **kwargs)

        # Execute function
        return func(*args, **kwargs)

    return wrapper


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "detect_performance_critical_code",
    "enforce_numba_available",
    "get_numba_version",
    "require_numba",
    "verify_numba_function",
]


# ============================================================================
# MODULE INITIALIZATION LOGGING
# ============================================================================

logger.info("=" * 80)
logger.info("NUMBA ENFORCEMENT MODULE LOADED")
logger.info("=" * 80)
logger.info("All performance-critical code MUST use Numba JIT compilation")
logger.info("Decorator required: @numba.jit(nopython=True, cache=True)")
logger.info("NO fallbacks. NO exceptions. Numba is MANDATORY.")
logger.info("=" * 80)
