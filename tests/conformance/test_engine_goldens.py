"""The conformance corpus in CI — any semantic drift of the engine fails.

See conformance/scenarios.py for what each scenario locks (t+1 fills,
liquidity deferral, the Sharpe convention, the twin definition, the
weight override). Goldens are re-frozen ONLY deliberately, with the
change that justifies them, via `python -m conformance.run --update`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from conformance.run import compare_all  # noqa: E402


def test_engine_goldens_frozen() -> None:
    failures = compare_all()
    assert not failures, (
        "engine semantics DRIFTED from the frozen goldens: "
        + "; ".join(f"{name}: {why}" for name, why in failures)
        + " — if the change is deliberate, re-freeze with "
        "`python -m conformance.run --update` and commit goldens + reason together"
    )
