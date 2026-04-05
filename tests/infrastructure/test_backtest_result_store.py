"""
Tests for BacktestResultStore - SQLite persistence of backtest results.

Follows TDD approach: tests are written before the implementation.
Uses tmp_path fixture for test databases to avoid real DB pollution.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.infrastructure.persistence.backtest_result_store import (
    BacktestResultStore,
    BacktestRunRecord,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(**overrides) -> BacktestRunRecord:
    """Create a BacktestRunRecord with sensible defaults, allowing overrides."""
    defaults = {
        "strategy_name": "sma_crossover",
        "investor_profile": "moderate",
        "time_window": "1y",
        "total_return": 12.5,
        "sharpe_ratio": 1.8,
        "sortino_ratio": 2.1,
        "max_drawdown": -8.3,
        "win_rate": 62.0,
        "profit_factor": 1.9,
        "total_trades": 42,
        "git_commit_hash": "abc1234",
        "config_snapshot": json.dumps({"initial_capital": 100000}),
        "full_results_json": json.dumps({"final_capital": 112500}),
    }
    defaults.update(overrides)
    return BacktestRunRecord(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def store(tmp_path: Path) -> BacktestResultStore:
    """Provide a fresh BacktestResultStore with an initialized temporary database."""
    db_path = tmp_path / "test_backtest.db"
    s = BacktestResultStore(db_path)
    await s.initialize()
    return s


# ===========================================================================
# TEST: initialize creates tables
# ===========================================================================


class TestInitialize:
    """Tests for store initialization."""

    async def test_initialize_creates_database_file(self, tmp_path: Path) -> None:
        """initialize() must create the SQLite database file."""
        db_path = tmp_path / "fresh.db"
        store = BacktestResultStore(db_path)
        assert not db_path.exists()

        await store.initialize()

        assert db_path.exists()

    async def test_initialize_idempotent(self, tmp_path: Path) -> None:
        """Calling initialize() twice must not raise an error."""
        db_path = tmp_path / "idempotent.db"
        store = BacktestResultStore(db_path)
        await store.initialize()
        await store.initialize()  # second call must succeed

    async def test_initialize_creates_backtest_runs_table(self, store: BacktestResultStore) -> None:
        """The backtest_runs table must exist after initialization."""
        import aiosqlite

        async with aiosqlite.connect(store.db_path) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_runs'"
            )
            row = await cursor.fetchone()
            assert row is not None, "backtest_runs table must exist"


# ===========================================================================
# TEST: save returns run_id
# ===========================================================================


class TestSave:
    """Tests for saving backtest run records."""

    async def test_save_returns_run_id(self, store: BacktestResultStore) -> None:
        """save() must return the UUID string run_id of the saved record."""
        record = _make_record()
        run_id = await store.save(record)

        assert isinstance(run_id, str)
        assert len(run_id) == 36  # UUID format: 8-4-4-4-12
        assert run_id.count("-") == 4

    async def test_save_preserves_custom_run_id(self, store: BacktestResultStore) -> None:
        """When a record has a pre-set run_id, save() must preserve it."""
        record = _make_record(run_id="11111111-2222-3333-4444-555555555555")
        returned_id = await store.save(record)

        assert returned_id == "11111111-2222-3333-4444-555555555555"

    async def test_save_multiple_runs(self, store: BacktestResultStore) -> None:
        """Saving multiple records must not overwrite previous ones."""
        id_a = await store.save(_make_record(strategy_name="strategy_a"))
        id_b = await store.save(_make_record(strategy_name="strategy_b"))

        assert id_a != id_b

        runs = await store.list_runs()
        assert len(runs) == 2

    async def test_save_with_nullable_fields(self, store: BacktestResultStore) -> None:
        """Saving a record with None optional fields must succeed."""
        record = BacktestRunRecord(
            strategy_name="minimal",
            total_return=5.0,
        )
        run_id = await store.save(record)
        assert isinstance(run_id, str)

        retrieved = await store.get(run_id)
        assert retrieved is not None
        assert retrieved.investor_profile is None
        assert retrieved.git_commit_hash is None
        assert retrieved.config_snapshot is None
        assert retrieved.full_results_json is None


# ===========================================================================
# TEST: get retrieves run
# ===========================================================================


class TestGet:
    """Tests for retrieving a single backtest run."""

    async def test_get_existing_run(self, store: BacktestResultStore) -> None:
        """get() must return the correct BacktestRunRecord for a known run_id."""
        record = _make_record()
        run_id = await store.save(record)

        retrieved = await store.get(run_id)

        assert retrieved is not None
        assert retrieved.run_id == run_id
        assert retrieved.strategy_name == "sma_crossover"
        assert retrieved.investor_profile == "moderate"
        assert retrieved.time_window == "1y"
        assert retrieved.total_return == 12.5
        assert retrieved.sharpe_ratio == 1.8
        assert retrieved.sortino_ratio == 2.1
        assert retrieved.max_drawdown == -8.3
        assert retrieved.win_rate == 62.0
        assert retrieved.profit_factor == 1.9
        assert retrieved.total_trades == 42
        assert retrieved.git_commit_hash == "abc1234"

    async def test_get_nonexistent_run(self, store: BacktestResultStore) -> None:
        """get() must return None for a non-existent run_id."""
        result = await store.get("00000000-0000-0000-0000-000000000000")
        assert result is None

    async def test_get_preserves_json_fields(self, store: BacktestResultStore) -> None:
        """JSON fields (config_snapshot, full_results_json) must round-trip correctly."""
        config = {"initial_capital": 100000, "commission": 1.0}
        results = {"final_capital": 112500, "trades": []}
        record = _make_record(
            config_snapshot=json.dumps(config),
            full_results_json=json.dumps(results),
        )
        run_id = await store.save(record)

        retrieved = await store.get(run_id)
        assert retrieved is not None

        assert json.loads(retrieved.config_snapshot) == config
        assert json.loads(retrieved.full_results_json) == results

    async def test_get_preserves_timestamp(self, store: BacktestResultStore) -> None:
        """The timestamp field must round-trip without corruption."""
        record = _make_record()
        run_id = await store.save(record)

        retrieved = await store.get(run_id)
        assert retrieved is not None
        # Verify timestamp is a datetime and is recent (within the last minute)
        assert isinstance(retrieved.timestamp, datetime)
        delta = datetime.now(tz=timezone.utc) - retrieved.timestamp
        assert delta.total_seconds() < 60


# ===========================================================================
# TEST: list_runs returns sorted by timestamp desc
# ===========================================================================


class TestListRuns:
    """Tests for listing backtest runs."""

    async def test_list_runs_empty(self, store: BacktestResultStore) -> None:
        """list_runs() on an empty database must return an empty list."""
        runs = await store.list_runs()
        assert runs == []

    async def test_list_returns_all_runs(self, store: BacktestResultStore) -> None:
        """list_runs() must return all saved records."""
        await store.save(_make_record(strategy_name="a"))
        await store.save(_make_record(strategy_name="b"))
        await store.save(_make_record(strategy_name="c"))

        runs = await store.list_runs()
        assert len(runs) == 3

    async def test_list_sorted_by_timestamp_desc(self, store: BacktestResultStore) -> None:
        """list_runs() must return runs sorted by timestamp descending (newest first)."""
        import asyncio

        t1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2024, 3, 10, 8, 0, 0, tzinfo=timezone.utc)

        await store.save(_make_record(strategy_name="oldest", timestamp=t1))
        await asyncio.sleep(0.01)  # Ensure different timestamps
        await store.save(_make_record(strategy_name="newest", timestamp=t2))
        await asyncio.sleep(0.01)
        await store.save(_make_record(strategy_name="middle", timestamp=t3))

        runs = await store.list_runs()
        assert len(runs) == 3
        assert runs[0].strategy_name == "newest"
        assert runs[1].strategy_name == "middle"
        assert runs[2].strategy_name == "oldest"

    async def test_list_respects_limit(self, store: BacktestResultStore) -> None:
        """list_runs(limit=N) must return at most N records."""
        for i in range(10):
            await store.save(_make_record(strategy_name=f"strategy_{i}"))

        runs = await store.list_runs(limit=3)
        assert len(runs) == 3

    async def test_list_default_limit_is_50(self, store: BacktestResultStore) -> None:
        """The default limit must be 50."""
        for i in range(55):
            await store.save(_make_record(strategy_name=f"s_{i}"))

        runs = await store.list_runs()
        assert len(runs) == 50

    async def test_list_filter_by_strategy(self, store: BacktestResultStore) -> None:
        """list_runs(strategy=X) must return only runs matching that strategy."""
        await store.save(_make_record(strategy_name="sma_crossover"))
        await store.save(_make_record(strategy_name="rsi_reversal"))
        await store.save(_make_record(strategy_name="sma_crossover"))

        runs = await store.list_runs(strategy="sma_crossover")
        assert len(runs) == 2
        assert all(r.strategy_name == "sma_crossover" for r in runs)

    async def test_list_filter_nonexistent_strategy(self, store: BacktestResultStore) -> None:
        """Filtering by a non-existent strategy must return an empty list."""
        await store.save(_make_record(strategy_name="sma_crossover"))

        runs = await store.list_runs(strategy="nonexistent")
        assert runs == []


# ===========================================================================
# TEST: delete removes run
# ===========================================================================


class TestDelete:
    """Tests for deleting backtest runs."""

    async def test_delete_existing_run(self, store: BacktestResultStore) -> None:
        """delete() must remove the run and return True."""
        run_id = await store.save(_make_record())

        result = await store.delete(run_id)

        assert result is True
        retrieved = await store.get(run_id)
        assert retrieved is None

    async def test_delete_nonexistent_run(self, store: BacktestResultStore) -> None:
        """delete() for a non-existent run_id must return False."""
        result = await store.delete("00000000-0000-0000-0000-000000000000")
        assert result is False

    async def test_delete_does_not_affect_other_runs(self, store: BacktestResultStore) -> None:
        """Deleting one run must not affect other stored runs."""
        id_a = await store.save(_make_record(strategy_name="keep"))
        id_b = await store.save(_make_record(strategy_name="delete"))

        await store.delete(id_b)

        retrieved = await store.get(id_a)
        assert retrieved is not None
        assert retrieved.strategy_name == "keep"

    async def test_double_delete_returns_false(self, store: BacktestResultStore) -> None:
        """Deleting the same run twice: first True, then False."""
        run_id = await store.save(_make_record())

        first = await store.delete(run_id)
        second = await store.delete(run_id)

        assert first is True
        assert second is False


# ===========================================================================
# TEST: compare returns metrics diff
# ===========================================================================


class TestCompare:
    """Tests for comparing two backtest runs."""

    async def test_compare_two_runs(self, store: BacktestResultStore) -> None:
        """compare() must return a dict with metric diffs for two valid run_ids."""
        id_a = await store.save(
            _make_record(
                total_return=10.0,
                sharpe_ratio=1.5,
                sortino_ratio=2.0,
                max_drawdown=-5.0,
                win_rate=55.0,
                profit_factor=1.7,
                total_trades=30,
            )
        )
        id_b = await store.save(
            _make_record(
                total_return=15.0,
                sharpe_ratio=2.0,
                sortino_ratio=2.5,
                max_drawdown=-8.0,
                win_rate=65.0,
                profit_factor=2.2,
                total_trades=40,
            )
        )

        diff = await store.compare(id_a, id_b)

        assert diff is not None
        assert diff["total_return"]["a"] == 10.0
        assert diff["total_return"]["b"] == 15.0
        assert diff["total_return"]["delta"] == pytest.approx(5.0)
        assert diff["sharpe_ratio"]["delta"] == pytest.approx(0.5)
        assert diff["sortino_ratio"]["delta"] == pytest.approx(0.5)
        assert diff["max_drawdown"]["delta"] == pytest.approx(-3.0)
        assert diff["win_rate"]["delta"] == pytest.approx(10.0)
        assert diff["profit_factor"]["delta"] == pytest.approx(0.5)
        assert diff["total_trades"]["delta"] == 10

    async def test_compare_returns_none_if_first_missing(self, store: BacktestResultStore) -> None:
        """compare() must return None if run_id_a does not exist."""
        id_b = await store.save(_make_record())

        result = await store.compare("00000000-0000-0000-0000-000000000000", id_b)
        assert result is None

    async def test_compare_returns_none_if_second_missing(self, store: BacktestResultStore) -> None:
        """compare() must return None if run_id_b does not exist."""
        id_a = await store.save(_make_record())

        result = await store.compare(id_a, "00000000-0000-0000-0000-000000000000")
        assert result is None

    async def test_compare_returns_none_if_both_missing(self, store: BacktestResultStore) -> None:
        """compare() must return None if both run_ids do not exist."""
        result = await store.compare(
            "00000000-0000-0000-0000-000000000000",
            "11111111-1111-1111-1111-111111111111",
        )
        assert result is None

    async def test_compare_handles_null_metrics(self, store: BacktestResultStore) -> None:
        """compare() must handle None metrics gracefully."""
        id_a = await store.save(
            BacktestRunRecord(strategy_name="s1", total_return=5.0, sharpe_ratio=None)
        )
        id_b = await store.save(
            BacktestRunRecord(strategy_name="s2", total_return=None, sharpe_ratio=1.5)
        )

        diff = await store.compare(id_a, id_b)
        assert diff is not None
        assert diff["total_return"]["a"] == 5.0
        assert diff["total_return"]["b"] is None
        assert diff["sharpe_ratio"]["a"] is None
        assert diff["sharpe_ratio"]["b"] == 1.5

    async def test_compare_includes_run_metadata(self, store: BacktestResultStore) -> None:
        """compare() result must include run metadata (strategy_name, time_window)."""
        id_a = await store.save(_make_record(strategy_name="strategy_a", time_window="6m"))
        id_b = await store.save(_make_record(strategy_name="strategy_b", time_window="1y"))

        diff = await store.compare(id_a, id_b)
        assert diff is not None
        assert diff["strategy_name"]["a"] == "strategy_a"
        assert diff["strategy_name"]["b"] == "strategy_b"
        assert diff["time_window"]["a"] == "6m"
        assert diff["time_window"]["b"] == "1y"


# ===========================================================================
# TEST: edge cases and robustness
# ===========================================================================


class TestEdgeCases:
    """Edge-case and robustness tests."""

    async def test_path_accepts_string(self, tmp_path: Path) -> None:
        """The constructor must accept a plain string path."""
        db_path = str(tmp_path / "string_path.db")
        store = BacktestResultStore(db_path)
        await store.initialize()
        assert Path(store.db_path).exists()

    async def test_path_accepts_path_object(self, tmp_path: Path) -> None:
        """The constructor must accept a pathlib.Path object."""
        db_path = tmp_path / "path_object.db"
        store = BacktestResultStore(db_path)
        await store.initialize()
        assert db_path.exists()

    async def test_save_and_get_with_all_none_metrics(self, store: BacktestResultStore) -> None:
        """A record with all metrics set to None must round-trip correctly."""
        record = BacktestRunRecord(strategy_name="bare")
        run_id = await store.save(record)

        retrieved = await store.get(run_id)
        assert retrieved is not None
        assert retrieved.total_return is None
        assert retrieved.sharpe_ratio is None
        assert retrieved.total_trades is None

    async def test_list_runs_with_limit_and_strategy(self, store: BacktestResultStore) -> None:
        """list_runs() must support both limit and strategy filter simultaneously."""
        for _ in range(5):
            await store.save(_make_record(strategy_name="alpha"))
        for _ in range(3):
            await store.save(_make_record(strategy_name="beta"))

        runs = await store.list_runs(limit=2, strategy="alpha")
        assert len(runs) == 2
        assert all(r.strategy_name == "alpha" for r in runs)
