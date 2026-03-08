"""
Safe Parsing Utilities - Replaces unsafe eval() with safer alternatives.

Security fix: This module provides safe alternatives to eval() for parsing
stored configuration data, preventing potential code injection attacks.

Usage:
    from app.shared.utils.safe_parse import safe_parse, safe_parse_json

    # Parse Python literals (lists, dicts, numbers, strings, booleans, None)
    data = safe_parse('["item1", "item2"]')  # Returns list

    # Parse JSON strings
    data = safe_parse_json('{"key": "value"}')  # Returns dict
"""

import ast
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def safe_parse(value: str, default: Any = None) -> Any:
    """
    Safely parse a string containing a Python literal.

    Replaces eval() with ast.literal_eval() which only parses:
    - strings, bytes, numbers, tuples, lists, dicts, sets, booleans, None

    Does NOT execute arbitrary code like eval() does.

    Args:
        value: String to parse
        default: Value to return if parsing fails

    Returns:
        Parsed value or default if parsing fails

    Example:
        >>> safe_parse('["a", "b", "c"]')
        ['a', 'b', 'c']
        >>> safe_parse('{"key": 123}')
        {'key': 123}
        >>> safe_parse('invalid', default=[])
        []
    """
    if value is None:
        return default

    if not isinstance(value, str):
        return value

    value = value.strip()
    if not value:
        return default

    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError) as e:
        logger.debug(f"Failed to parse value with literal_eval: {e}")
        return default


def safe_parse_json(value: str, default: Any = None) -> Any:
    """
    Safely parse a JSON string.

    Args:
        value: JSON string to parse
        default: Value to return if parsing fails

    Returns:
        Parsed JSON value or default if parsing fails

    Example:
        >>> safe_parse_json('{"key": "value"}')
        {'key': 'value'}
    """
    if value is None:
        return default

    if not isinstance(value, str):
        return value

    value = value.strip()
    if not value:
        return default

    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        logger.debug(f"Failed to parse JSON: {e}")
        return default


def safe_parse_with_fallback(value: str, default: Any = None) -> Any:
    """
    Try parsing with literal_eval first, then JSON, then return default.

    Use this when you're not sure if the data was stored as Python literal or JSON.

    Args:
        value: String to parse
        default: Value to return if all parsing attempts fail

    Returns:
        Parsed value or default
    """
    if value is None:
        return default

    if not isinstance(value, str):
        return value

    value = value.strip()
    if not value:
        return default

    # Try literal_eval first (for Python-format data)
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        pass

    # Try JSON (for JSON-format data)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass

    logger.debug(f"Failed to parse value with both literal_eval and JSON: {value[:50]}...")
    return default


def serialize_for_storage(value: Any) -> str:
    """
    Serialize a value for safe storage.

    Uses JSON serialization which is safer and more portable than repr().

    Args:
        value: Value to serialize

    Returns:
        JSON string representation
    """
    try:
        return json.dumps(value)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize value to JSON: {e}")
        return str(value)
