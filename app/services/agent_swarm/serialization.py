"""Best-effort JSON serialization for arbitrary pipeline inputs/outputs.

The CAPA 2 components exchange Pydantic models, dataclasses, Decimals, enums
and the occasional DataFrame. The dashboard (and the event store) need plain
JSON. This module converts anything to a JSON-ready structure and never
raises: on failure it degrades to a truncated ``repr``.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

MAX_PAYLOAD_CHARS = 65_536  # large enough for equity curves + full metrics


def truncate(text: str, limit: int = MAX_PAYLOAD_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n… [truncated {len(text) - limit} chars]"


def _dataframe_summary(obj: Any) -> dict:
    return {
        "__type__": "DataFrame",
        "shape": list(obj.shape),
        "columns": [str(c) for c in obj.columns[:50]],
    }


def _json_default(obj: Any) -> Any:
    # DataFrames first: they also define to_dict(), which would dump them whole
    if obj.__class__.__name__ == "DataFrame":
        return _dataframe_summary(obj)
    # Pydantic models (v2)
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return obj.model_dump(mode="json")
        except TypeError:
            try:
                return obj.model_dump()
            except Exception:  # noqa: BLE001 - fall through to other strategies
                pass
        except Exception:  # noqa: BLE001
            pass
    # Objects with explicit to_dict (dataclass-based components)
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return obj.to_dict()
        except Exception:  # noqa: BLE001 - a broken to_dict must not break the run
            pass
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, (set, frozenset, tuple)):
        return list(obj)
    if isinstance(obj, BaseException):
        return {"__type__": type(obj).__name__, "message": str(obj)}
    return {"__type__": type(obj).__name__, "repr": repr(obj)[:200]}


def safe_json(value: Any) -> Any:
    """Convert any value into a JSON-ready structure, never raising."""
    try:
        text = json.dumps(value, default=_json_default, ensure_ascii=False)
    except (TypeError, ValueError, RecursionError):
        return {"__serialization_error__": type(value).__name__, "repr": truncate(repr(value))}

    if len(text) > MAX_PAYLOAD_CHARS * 4:
        return {"__truncated__": True, "preview": truncate(text, MAX_PAYLOAD_CHARS)}

    try:
        return json.loads(text)
    except ValueError:  # pragma: no cover - json round-trip of dumps is safe
        return {"__truncated__": True, "preview": truncate(text, MAX_PAYLOAD_CHARS)}


def pretty(value: Any, indent: int = 2) -> str:
    """Pretty-print a value through :func:`safe_json` for UI display."""
    return truncate(json.dumps(safe_json(value), indent=indent, ensure_ascii=False))
