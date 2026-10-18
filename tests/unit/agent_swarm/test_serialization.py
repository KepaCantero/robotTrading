"""Unit tests for safe_json payload serialization."""

import dataclasses
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.services.agent_swarm.serialization import safe_json


class Color(Enum):
    RED = "red"


@dataclasses.dataclass
class Inner:
    value: Decimal


@dataclasses.dataclass
class Outer:
    name: str
    when: datetime
    inner: Inner
    tags: set


class TestPrimitives:
    def test_scalars_pass_through(self):
        assert safe_json(5) == 5
        assert safe_json("x") == "x"
        assert safe_json(None) is None
        assert safe_json([1, "a", None]) == [1, "a", None]

    def test_decimal_becomes_string(self):
        assert safe_json(Decimal("100000.50")) == "100000.50"

    def test_enum_becomes_value(self):
        assert safe_json(Color.RED) == "red"

    def test_datetime_becomes_isoformat(self):
        stamp = datetime(2026, 10, 17, 12, 0, 0)
        assert safe_json(stamp) == "2026-10-17T12:00:00"

    def test_set_and_tuple_become_list(self):
        assert sorted(safe_json({"a", "b"})) == ["a", "b"]
        assert safe_json((1, 2)) == [1, 2]


class TestStructured:
    def test_nested_dataclass(self):
        obj = Outer(
            name="run",
            when=datetime(2026, 1, 1),
            inner=Inner(Decimal("1.5")),
            tags={"x"},
        )
        result = safe_json(obj)
        assert result["name"] == "run"
        assert result["inner"]["value"] == "1.5"
        assert isinstance(result["tags"], list)

    def test_pydantic_model(self):
        from pydantic import BaseModel

        class Model(BaseModel):
            capital: Decimal
            count: int

        result = safe_json(Model(capital=Decimal("10"), count=2))
        assert result["count"] == 2
        assert "capital" in result

    def test_object_with_to_dict(self):
        class HasToDict:
            def to_dict(self):
                return {"ok": True}

        assert safe_json(HasToDict()) == {"ok": True}

    def test_dataframe_summarized(self):
        import pandas as pd

        frame = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = safe_json(frame)
        assert result["__type__"] == "DataFrame"
        assert result["shape"] == [2, 2]
        assert result["columns"] == ["a", "b"]

    def test_broken_to_dict_degrades_to_repr(self):
        class Broken:
            def to_dict(self):
                raise RuntimeError("boom")

        result = safe_json(Broken())
        assert result["__type__"] == "Broken"

    def test_result_is_json_serializable(self):
        import json

        payload = safe_json({"d": Decimal("1"), "e": Color.RED, "t": (1, 2)})
        json.dumps(payload)  # must not raise


class TestTruncation:
    def test_huge_payload_truncated(self):
        # El umbral de safe_json es MAX_PAYLOAD_CHARS * 4 (256 KB): el payload
        # debe SUPERARLO para truncarse. 200 KB pasa limpio (por diseño, para
        # curvas de equity completas); usamos 600 KB.
        huge = {"data": "x" * 600_000}
        result = safe_json(huge)
        assert result.get("__truncated__") is True
        assert len(result["preview"]) < 70_000  # preview = MAX_PAYLOAD_CHARS (65_536)

    def test_equity_curve_sized_payload_not_truncated(self):
        """Equity curves (~200 points + metrics) must survive serialization."""
        payload = {
            "equity_curve": [
                {"ts": f"2024-01-{i:02d}T00:00:00", "value": "100000"} for i in range(1, 29)
            ]
        }
        result = safe_json(payload)
        assert "__truncated__" not in result
        assert len(result["equity_curve"]) == 28

    def test_normal_payload_not_truncated(self):
        result = safe_json({"data": "small"})
        assert result == {"data": "small"}
