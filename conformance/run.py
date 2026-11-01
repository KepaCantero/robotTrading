"""Conformance runner — regenerate and byte-compare the frozen goldens.

Usage:
    python conformance/run.py             # compare (CI): any drift FAILS
    python conformance/run.py --update    # re-freeze (DELIBERATE change only)

A golden only changes on purpose: when a fill rule, metric convention or
benchmark definition is INTENTIONALLY changed, re-freeze in the same
commit and say why — the diff of the golden IS the changelog of the
engine's semantics.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

GOLDENS = Path(__file__).resolve().parent / "goldens"


def canonical(payload: dict) -> str:
    """The one canonical serialization: sorted keys, 2-space indent."""
    return json.dumps(payload, indent=2, sort_keys=True, default=str, ensure_ascii=False)


def compare_all() -> list[tuple[str, str]]:
    """Run every scenario; return [(name, failure)] — empty means frozen."""
    from conformance.scenarios import SCENARIOS

    failures: list[tuple[str, str]] = []
    GOLDENS.mkdir(exist_ok=True)
    for scenario in SCENARIOS:
        name, payload = scenario()
        golden = GOLDENS / f"{name}.json"
        fresh = canonical(payload)
        if not golden.exists():
            golden.write_text(fresh + "\n", encoding="utf-8")
            failures.append((name, "golden missing — created; review and commit"))
            continue
        frozen = golden.read_text(encoding="utf-8").rstrip("\n")
        if fresh.rstrip("\n") != frozen:
            failures.append((name, "DRIFT: regeneration differs from the frozen golden"))
    return failures


def update_all() -> None:
    from conformance.scenarios import SCENARIOS

    GOLDENS.mkdir(exist_ok=True)
    for scenario in SCENARIOS:
        name, payload = scenario()
        (GOLDENS / f"{name}.json").write_text(canonical(payload) + "\n", encoding="utf-8")
        print(f"frozen {name}")


if __name__ == "__main__":
    if "--update" in sys.argv:
        update_all()
        print("goldens re-frozen — commit them WITH the change that justified it")
    else:
        bad = compare_all()
        for name, why in bad:
            print(f"FAIL {name}: {why}")
        if bad:
            sys.exit(1)
        print("conformance: all goldens match")
