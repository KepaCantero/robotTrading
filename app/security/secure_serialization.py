"""
Secure Serialization Module - Binary-safe serialization with HMAC signature.

This module provides secure serialization functions that:
1. Automatically detect if data is JSON-serializable
2. Fall back to msgpack for binary/complex data (numpy arrays, pandas DataFrames, etc.)
3. Use HMAC-SHA256 for tamper detection
4. Return base64-encoded strings for safe transport

This REPLACES insecure pickle usage with a secure alternative.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
from decimal import Decimal  # noqa: F401
from typing import Any, Union

# REQUIRED: No fallbacks - fail fast if dependencies are missing
import msgpack  # noqa: F401
import numpy as np  # noqa: F401
import pandas as pd  # noqa: F401

logger = logging.getLogger(__name__)

# Dependency availability flags for testing
# All dependencies are now required (no fallbacks), so these are always True
HAS_MSGPACK = True
HAS_NUMPY = True
HAS_PANDAS = True
HAS_DECIMAL = True


def _get_secret_key() -> bytes:
    """
    Get secret key for signing messages.

    Rule 28 Compliance:
        - Reads SECRET_KEY from environment variable
        - No hardcoded secrets in code
        - Warns if using weak key
    """
    secret_key = os.getenv('SECRET_KEY', '')
    if not secret_key or len(secret_key) < 32:
        logger.warning(
            "SECRET_KEY not set or too short for secure messaging. "
            "Set SECRET_KEY environment variable (minimum 32 characters)."
        )
        # Rule 28: No hardcoded fallback keys
        raise ValueError(
            "SECRET_KEY environment variable not set or too short. "
            "Generate a secure key: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    return secret_key.encode() if isinstance(secret_key, str) else secret_key


def _is_json_serializable(obj: Any) -> bool:
    """
    Check if object is JSON-serializable without conversion.

    This checks if the object is natively JSON-serializable (dicts, lists, strings,
    numbers, bool, None). Objects requiring conversion (numpy arrays, pandas DataFrames,
    bytes, etc.) will return False.

    Args:
        obj: Object to test

    Returns:
        True if JSON-serializable, False otherwise
    """
    # Fast path for common JSON-serializable types
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return True

    # Check dict recursively (but not too deep to avoid performance issues)
    if isinstance(obj, dict):
        try:
            for key, value in obj.items():
                if not isinstance(key, (str, int, float, bool)):
                    return False
                if not _is_json_serializable(value):
                    return False
            return True
        except (TypeError, ValueError):
            return False

    # Check list/tuple recursively (but not too deep)
    if isinstance(obj, (list, tuple)):
        try:
            for item in obj:
                if not _is_json_serializable(item):
                    return False
            return True
        except (TypeError, ValueError):
            return False

    # Everything else is not natively JSON-serializable
    # This includes numpy arrays, pandas DataFrames, bytes, Decimal, etc.
    return False


def _convert_for_msgpack(obj: Any) -> Any:
    """
    Convert complex objects to msgpack-compatible format.

    Handles:
    - numpy arrays → dict with type, shape, and data
    - pandas DataFrames → dict with columns, index, and data
    - pandas Series → dict with index, name, and data
    - Decimal → float (msgpack doesn't support Decimal)
    - bytes → kept as-is (msgpack supports binary)

    Args:
        obj: Object to convert

    Returns:
        Msgpack-compatible representation
    """
    # Handle numpy arrays
    if isinstance(obj, np.ndarray):
        return {
            '__type__': 'numpy.ndarray',
            'dtype': str(obj.dtype),
            'shape': obj.shape,
            'data': obj.tolist(),  # Convert to nested list
        }

    # Handle pandas DataFrames
    if isinstance(obj, pd.DataFrame):
        return {
            '__type__': 'pandas.DataFrame',
            'columns': obj.columns.tolist(),
            'index': obj.index.tolist(),
            'dtypes': [str(dtype) for dtype in obj.dtypes],  # Preserve dtypes
            'data': obj.values.tolist(),  # Convert to nested list
        }

    # Handle pandas Series
    if isinstance(obj, pd.Series):
        return {
            '__type__': 'pandas.Series',
            'name': obj.name,
            'index': obj.index.tolist(),
            'data': obj.values.tolist(),
        }

    # Handle Decimal (convert to float)
    if isinstance(obj, Decimal):
        return {
            '__type__': 'decimal.Decimal',
            'value': str(obj),  # Preserve as string to avoid precision loss
        }

    # Handle dicts recursively
    if isinstance(obj, dict):
        return {k: _convert_for_msgpack(v) for k, v in obj.items()}

    # Handle lists/tuples recursively
    if isinstance(obj, (list, tuple)):
        return [_convert_for_msgpack(item) for item in obj]

    # Everything else (including bytes) return as-is
    return obj


def _restore_from_msgpack(obj: Any) -> Any:
    """
    Restore objects from msgpack-compatible format.

    Reconstructs:
    - numpy arrays from dict representation
    - pandas DataFrames from dict representation
    - pandas Series from dict representation
    - Decimal from string representation

    Args:
        obj: Object to restore

    Returns:
        Original Python object
    """
    # Restore numpy arrays
    if isinstance(obj, dict) and obj.get('__type__') == 'numpy.ndarray':
        return np.array(obj['data'], dtype=obj['dtype']).reshape(obj['shape'])

    # Restore pandas DataFrames
    if isinstance(obj, dict) and obj.get('__type__') == 'pandas.DataFrame':
        df = pd.DataFrame(data=obj['data'], index=obj['index'], columns=obj['columns'])
        # Restore dtypes if available
        if 'dtypes' in obj:
            for col, dtype_str in zip(obj['columns'], obj['dtypes']):
                try:
                    df[col] = df[col].astype(dtype_str)
                except (ValueError, TypeError):
                    # If conversion fails, keep as-is
                    pass
        return df

    # Restore pandas Series
    if isinstance(obj, dict) and obj.get('__type__') == 'pandas.Series':
        return pd.Series(data=obj['data'], index=obj['index'], name=obj['name'])

    # Restore Decimal
    if isinstance(obj, dict) and obj.get('__type__') == 'decimal.Decimal':
        return Decimal(obj['value'])

    # Handle dicts recursively
    if isinstance(obj, dict):
        return {k: _restore_from_msgpack(v) for k, v in obj.items()}

    # Handle lists recursively
    if isinstance(obj, list):
        return [_restore_from_msgpack(item) for item in obj]

    # Everything else return as-is
    return obj


def sign_and_dump(data: Any, secret_key: Union[str, bytes] = None) -> str:
    """
    Sign and serialize data with automatic format detection.

    Uses JSON for simple data (faster, more readable) and msgpack for
    complex/binary data (numpy arrays, pandas DataFrames, etc.).

    Args:
        data: Data to serialize (any Python object)
        secret_key: Secret key for signing (uses default if None)

    Returns:
        Base64-encoded string containing format type, signature, and serialized data

    Raises:
        ValueError: If msgpack is required but not installed, or serialization fails

    Example:
        >>> data = {'array': np.array([1, 2, 3])}
        >>> signed = sign_and_dump(data, 'my_secret_key')
        >>> loaded = verify_and_load(signed, 'my_secret_key')
        >>> assert np.array_equal(loaded['array'], data['array'])
    """
    if secret_key is None:
        secret_key = _get_secret_key()

    # Convert string key to bytes if needed
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf-8')

    try:
        # Try JSON first (faster, more readable, human-friendly)
        if _is_json_serializable(data):
            serialized = json.dumps(data).encode('utf-8')
            format_type = b'json'  # 4 bytes
        else:
            # Use msgpack for binary/complex data
            # Convert complex objects (numpy, pandas) to msgpack-compatible format
            converted_data = _convert_for_msgpack(data)
            serialized = msgpack.packb(converted_data, use_bin_type=True)
            format_type = b'msgp'  # 4 bytes (msgpack prefix)

        # Create HMAC-SHA256 signature
        signature = hmac.new(secret_key, serialized, hashlib.sha256).digest()  # 32 bytes

        # Combine: format_type (4) + signature (32) + data (variable)
        combined = format_type + signature + serialized

        # Base64 encode for safe transport (ASCII-only)
        return base64.b64encode(combined).decode('ascii')

    except (ValueError, TypeError) as e:
        logger.error(f"Failed to serialize data: {e}", exc_info=True)
        raise ValueError(f"Failed to serialize data: {e}") from e
    except (AttributeError, KeyError) as e:
        logger.error(f"Data structure error during serialization: {e}", exc_info=True)
        raise ValueError(f"Invalid data structure for serialization: {e}") from e


def verify_and_load(signed_data: str, secret_key: Union[str, bytes] = None) -> Any:
    """
    Verify HMAC signature and deserialize data.

    Automatically detects format (json/msgpack) and deserializes.

    Args:
        signed_data: Base64-encoded signed data from sign_and_dump()
        secret_key: Secret key for verification (uses default if None)

    Returns:
        Deserialized Python object

    Raises:
        ValueError: If signature is invalid, data is malformed, or format is unknown

    Example:
        >>> data = {'key': 'value'}
        >>> signed = sign_and_dump(data, 'my_secret_key')
        >>> loaded = verify_and_load(signed, 'my_secret_key')
        >>> assert loaded == data
    """
    if secret_key is None:
        secret_key = _get_secret_key()

    # Convert string key to bytes if needed
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf-8')

    try:
        # Decode base64
        combined = base64.b64decode(signed_data.encode('ascii'))

        # Extract components
        # Format: [format_type (4 bytes)] [signature (32 bytes)] [data (rest)]
        if len(combined) < 36:  # Minimum: 4 + 32 + 0
            raise ValueError("Invalid signed data format: too short")

        format_type = combined[:4]  # b'json' or b'msgp'
        received_signature = combined[4:36]  # 32 bytes for SHA256
        serialized = combined[36:]  # Rest is data

        # Verify signature using constant-time comparison
        expected_signature = hmac.new(secret_key, serialized, hashlib.sha256).digest()

        if not hmac.compare_digest(received_signature, expected_signature):
            logger.error("HMAC signature verification failed - data may be tampered")
            raise ValueError("Invalid signature - data may be tampered")

        # Deserialize based on format
        if format_type == b'json':
            return json.loads(serialized.decode('utf-8'))
        elif format_type == b'msgp':
            # Unpack and restore complex objects (numpy, pandas)
            unpacked = msgpack.unpackb(serialized, raw=False)
            return _restore_from_msgpack(unpacked)
        else:
            raise ValueError(f"Unknown format type: {format_type}")

    except ValueError as e:
        # Re-raise ValueError with context (includes signature errors, parsing errors)
        logger.error(f"Failed to verify and load data: {e}", exc_info=True)
        raise
    except (KeyError, AttributeError) as e:
        # Specific errors for data structure issues
        logger.error(f"Data structure error during deserialization: {e}", exc_info=True)
        raise ValueError(f"Invalid data structure during deserialization: {e}") from e
    except (TypeError, IndexError) as e:
        # Specific errors for format/binary issues
        logger.error(f"Format error during deserialization: {e}", exc_info=True)
        raise ValueError(f"Invalid signed data format: {e}") from e
