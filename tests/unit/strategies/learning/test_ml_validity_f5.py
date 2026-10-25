"""Fase 5 — ML validity (hallazgos A11/A12).

- A11: features only see trades CLOSED BEFORE the evaluated instant — the
  audit's reproduction was a trade closing Jan-10 contributing 100% win
  rate to a Jan-2 signal (future information).
- A12: when purged CV fails, training FAILS loudly — the old fallback to a
  shuffled train_test_split dressed a methodological breach as a valid
  score.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.domain.strategies.learning.training_data_preparator import TrainingDataPreparator


@pytest.fixture
def preparator():
    return TrainingDataPreparator()


def closed_trade(entry: str, exit_: str, pnl: float):
    return SimpleNamespace(
        entry_time=datetime.fromisoformat(entry),
        exit_time=datetime.fromisoformat(exit_),
        status="CLOSED",
        pnl=pnl,
    )


class TestA11PointInTimeTrades:
    def test_future_close_not_visible(self, preparator):
        # Cierra el 10-ene: en el instante 2-ene NO puede alimentar features.
        trades = [closed_trade("2026-01-02T10:00", "2026-01-10T16:00", 100.0)]
        visible = preparator._get_recent_trades_before_timestamp(
            trades, datetime(2026, 1, 2, 12, 0), max_trades=10
        )
        assert visible == []

    def test_past_close_visible(self, preparator):
        trades = [closed_trade("2026-01-02T10:00", "2026-01-03T16:00", 100.0)]
        visible = preparator._get_recent_trades_before_timestamp(
            trades, datetime(2026, 1, 5, 12, 0), max_trades=10
        )
        assert len(visible) == 1 and visible[0]["pnl"] == 100.0

    def test_win_rate_ignores_future_closes(self, preparator):
        trades = [
            closed_trade("2026-01-01T10:00", "2026-01-02T16:00", 50.0),  # known: win
            closed_trade("2026-01-02T10:00", "2026-01-10T16:00", -50.0),  # future
        ]
        rate = preparator._calculate_recent_win_rate(
            trades, datetime(2026, 1, 3, 12, 0), window_days=30
        )
        assert rate == 1.0  # solo el cierre CONOCIDO cuenta

    def test_open_trade_without_exit_never_counts(self, preparator):
        open_trade = SimpleNamespace(
            entry_time=datetime.fromisoformat("2026-01-01T10:00"),
            exit_time=None,
            status="CLOSED",  # estado final global, sin fecha de cierre
            pnl=100.0,
        )
        visible = preparator._get_recent_trades_before_timestamp(
            [open_trade], datetime(2026, 2, 1, 12, 0), max_trades=10
        )
        assert visible == []


class TestA12NoRandomSplitFallback:
    def test_purged_cv_failure_fails_training(self, monkeypatch):
        import numpy as np

        from app.domain.strategies.learning.supervised_learning_engine import (
            SupervisedLearningEngine,
        )

        class ExplodingKFold:
            def __init__(self, *args, **kwargs):
                pass

            def split(self, *args, **kwargs):
                raise RuntimeError("boom: no valid temporal splits")

        monkeypatch.setattr(
            "app.backtesting.validation.cross_validation.PurgedKFold", ExplodingKFold
        )
        engine = SupervisedLearningEngine(config={})
        training_data = {
            "features": np.random.default_rng(7).normal(size=(60, 3)),
            "labels": np.array([0, 1] * 30),
        }
        # purged CV explota → el entrenamiento DEBE fallar explícitamente,
        # jamás degradar a un split aleatorio con score "válido"
        with pytest.raises(ValueError, match="Temporal validation"):
            engine.train(training_data)

    def test_no_train_test_split_import_remains(self):
        """The random-split escape hatch is gone from the module."""
        import inspect

        from app.domain.strategies.learning import supervised_learning_engine as module

        source = inspect.getsource(module)
        assert "train_test_split(" not in source
