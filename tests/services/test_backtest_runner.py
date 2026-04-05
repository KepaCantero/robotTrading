"""
Tests for BacktestRunner service (TDD - tests written first).

Covers:
- BacktestParams validation
- BacktestRunner.run() flow (Phase 2 placeholder)
- git_commit_hash capture with fallback
- config_snapshot serialization
- Integration with BacktestResultStore
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from app.infrastructure.persistence.backtest_result_store import BacktestResultStore
from app.services.backtest_runner import BacktestParams, BacktestRunner

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def store(tmp_path: Path) -> BacktestResultStore:
    """Create an initialized BacktestResultStore backed by a temp database."""
    db_path = tmp_path / "test_backtest_runs.db"
    s = BacktestResultStore(db_path)
    await s.initialize()
    return s


@pytest.fixture
async def runner(store: BacktestResultStore) -> BacktestRunner:
    """Create a BacktestRunner with a real (temp) store."""
    return BacktestRunner(store)


@pytest.fixture
def valid_params() -> BacktestParams:
    """Minimal valid BacktestParams."""
    return BacktestParams(strategy_name="momentum")


@pytest.fixture
def full_params() -> BacktestParams:
    """Fully populated BacktestParams."""
    return BacktestParams(
        strategy_name="mean_reversion",
        investor_profile="aggressive",
        time_window="6mo",
        symbols=["AAPL", "MSFT"],
        initial_capital=250000.0,
    )


# ===================================================================
# BacktestParams dataclass
# ===================================================================


class TestBacktestParams:
    """Tests for the BacktestParams dataclass."""

    def test_default_values(self):
        """BacktestParams should have sensible defaults."""
        params = BacktestParams(strategy_name="test_strategy")

        assert params.strategy_name == "test_strategy"
        assert params.investor_profile is None
        assert params.time_window == "1y"
        assert params.symbols is None
        assert params.initial_capital == 100000.0

    def test_custom_values(self, full_params: BacktestParams):
        """BacktestParams should accept all custom values."""
        assert full_params.strategy_name == "mean_reversion"
        assert full_params.investor_profile == "aggressive"
        assert full_params.time_window == "6mo"
        assert full_params.symbols == ["AAPL", "MSFT"]
        assert full_params.initial_capital == 250000.0


# ===================================================================
# validate_params
# ===================================================================


class TestValidateParams:
    """Tests for BacktestRunner.validate_params()."""

    def test_valid_params_returns_empty_list(
        self, runner: BacktestRunner, valid_params: BacktestParams
    ):
        """Valid parameters should produce no errors."""
        errors = runner.validate_params(valid_params)
        assert errors == []

    def test_valid_full_params_returns_empty_list(
        self, runner: BacktestRunner, full_params: BacktestParams
    ):
        """Fully populated valid parameters should produce no errors."""
        errors = runner.validate_params(full_params)
        assert errors == []

    def test_empty_strategy_name(self, runner: BacktestRunner):
        """Empty strategy_name should be reported as an error."""
        params = BacktestParams(strategy_name="")
        errors = runner.validate_params(params)
        assert len(errors) == 1
        assert "strategy_name" in errors[0].lower()

    def test_whitespace_only_strategy_name(self, runner: BacktestRunner):
        """Whitespace-only strategy_name should be reported as an error."""
        params = BacktestParams(strategy_name="   ")
        errors = runner.validate_params(params)
        assert len(errors) == 1
        assert "strategy_name" in errors[0].lower()

    def test_invalid_time_window(self, runner: BacktestRunner):
        """Invalid time_window should be reported as an error."""
        params = BacktestParams(strategy_name="test", time_window="10y")
        errors = runner.validate_params(params)
        assert len(errors) == 1
        assert "time_window" in errors[0].lower()

    def test_valid_time_windows(self, runner: BacktestRunner):
        """All accepted time_window values should pass validation."""
        for tw in ("1mo", "3mo", "6mo", "1y", "2y", "5y"):
            params = BacktestParams(strategy_name="test", time_window=tw)
            errors = runner.validate_params(params)
            assert errors == [], f"time_window={tw} should be valid"

    def test_zero_initial_capital(self, runner: BacktestRunner):
        """Zero initial_capital should be reported as an error."""
        params = BacktestParams(strategy_name="test", initial_capital=0.0)
        errors = runner.validate_params(params)
        assert len(errors) == 1
        assert "initial_capital" in errors[0].lower()

    def test_negative_initial_capital(self, runner: BacktestRunner):
        """Negative initial_capital should be reported as an error."""
        params = BacktestParams(strategy_name="test", initial_capital=-1000.0)
        errors = runner.validate_params(params)
        assert len(errors) == 1
        assert "initial_capital" in errors[0].lower()

    def test_empty_symbols_list(self, runner: BacktestRunner):
        """Empty symbols list should be reported as an error."""
        params = BacktestParams(strategy_name="test", symbols=[])
        errors = runner.validate_params(params)
        assert len(errors) == 1
        assert "symbol" in errors[0].lower()

    def test_none_symbols_is_valid(self, runner: BacktestRunner):
        """None symbols should be accepted (means use defaults)."""
        params = BacktestParams(strategy_name="test", symbols=None)
        errors = runner.validate_params(params)
        assert errors == []

    def test_nonempty_symbols_is_valid(self, runner: BacktestRunner):
        """Non-empty symbols list should be accepted."""
        params = BacktestParams(strategy_name="test", symbols=["AAPL"])
        errors = runner.validate_params(params)
        assert errors == []

    def test_multiple_errors_reported(self, runner: BacktestRunner):
        """Multiple validation failures should all be reported."""
        params = BacktestParams(
            strategy_name="",
            time_window="invalid",
            initial_capital=-500.0,
            symbols=[],
        )
        errors = runner.validate_params(params)
        assert len(errors) == 4

    def test_two_errors_reported(self, runner: BacktestRunner):
        """Two validation failures should report two errors."""
        params = BacktestParams(
            strategy_name="",
            time_window="invalid",
        )
        errors = runner.validate_params(params)
        assert len(errors) == 2


# ===================================================================
# run() - Phase 2 placeholder
# ===================================================================


class TestRun:
    """Tests for BacktestRunner.run() - Phase 2 placeholder."""

    @pytest.mark.asyncio
    async def test_run_returns_record(self, runner: BacktestRunner, valid_params: BacktestParams):
        """run() should return a BacktestRunRecord."""
        record = await runner.run(valid_params)
        assert record is not None
        assert record.run_id  # non-empty string

    @pytest.mark.asyncio
    async def test_run_sets_strategy_name(
        self, runner: BacktestRunner, valid_params: BacktestParams
    ):
        """run() should propagate strategy_name to the record."""
        record = await runner.run(valid_params)
        assert record.strategy_name == "momentum"

    @pytest.mark.asyncio
    async def test_run_sets_investor_profile(
        self, runner: BacktestRunner, full_params: BacktestParams
    ):
        """run() should propagate investor_profile to the record."""
        record = await runner.run(full_params)
        assert record.investor_profile == "aggressive"

    @pytest.mark.asyncio
    async def test_run_sets_time_window(self, runner: BacktestRunner, full_params: BacktestParams):
        """run() should propagate time_window to the record."""
        record = await runner.run(full_params)
        assert record.time_window == "6mo"

    @pytest.mark.asyncio
    async def test_run_placeholder_metrics_are_none(
        self, runner: BacktestRunner, valid_params: BacktestParams
    ):
        """Phase 2: all metric fields should be None (placeholder)."""
        record = await runner.run(valid_params)
        assert record.total_return is None
        assert record.sharpe_ratio is None
        assert record.sortino_ratio is None
        assert record.max_drawdown is None
        assert record.win_rate is None
        assert record.profit_factor is None
        assert record.total_trades is None
        assert record.full_results_json is None

    @pytest.mark.asyncio
    async def test_run_captures_git_commit_hash(
        self, runner: BacktestRunner, valid_params: BacktestParams
    ):
        """run() should capture a git_commit_hash (string or None)."""
        record = await runner.run(valid_params)
        # The project is a git repo, so this should be a non-None short hash.
        # We accept both: in CI the git metadata might not be available.
        if record.git_commit_hash is not None:
            assert isinstance(record.git_commit_hash, str)
            assert len(record.git_commit_hash) > 0

    @pytest.mark.asyncio
    async def test_run_captures_config_snapshot(
        self, runner: BacktestRunner, full_params: BacktestParams
    ):
        """run() should serialize params to a JSON config_snapshot."""
        record = await runner.run(full_params)
        assert record.config_snapshot is not None
        snapshot = json.loads(record.config_snapshot)
        assert snapshot["strategy_name"] == "mean_reversion"
        assert snapshot["investor_profile"] == "aggressive"
        assert snapshot["time_window"] == "6mo"
        assert snapshot["symbols"] == ["AAPL", "MSFT"]
        assert snapshot["initial_capital"] == 250000.0

    @pytest.mark.asyncio
    async def test_run_persists_to_store(
        self, runner: BacktestRunner, store: BacktestResultStore, valid_params: BacktestParams
    ):
        """run() should persist the record to the BacktestResultStore."""
        record = await runner.run(valid_params)
        # Retrieve from store to verify persistence
        fetched = await store.get(record.run_id)
        assert fetched is not None
        assert fetched.run_id == record.run_id
        assert fetched.strategy_name == "momentum"

    @pytest.mark.asyncio
    async def test_run_raises_on_invalid_params(self, runner: BacktestRunner):
        """run() should raise ValueError when params are invalid."""
        bad_params = BacktestParams(strategy_name="")
        with pytest.raises(ValueError, match=r"[Vv]alidation"):
            await runner.run(bad_params)

    @pytest.mark.asyncio
    async def test_run_record_has_timestamp(
        self, runner: BacktestRunner, valid_params: BacktestParams
    ):
        """run() should set a timestamp on the record."""
        record = await runner.run(valid_params)
        assert record.timestamp is not None

    @pytest.mark.asyncio
    async def test_run_config_snapshot_handles_none_symbols(
        self, runner: BacktestRunner, valid_params: BacktestParams
    ):
        """config_snapshot should handle None symbols correctly."""
        record = await runner.run(valid_params)
        snapshot = json.loads(record.config_snapshot)
        assert snapshot["symbols"] is None

    @pytest.mark.asyncio
    async def test_run_config_snapshot_handles_none_profile(
        self, runner: BacktestRunner, valid_params: BacktestParams
    ):
        """config_snapshot should handle None investor_profile correctly."""
        record = await runner.run(valid_params)
        snapshot = json.loads(record.config_snapshot)
        assert snapshot["investor_profile"] is None

    @pytest.mark.asyncio
    async def test_run_returns_distinct_run_ids(
        self, runner: BacktestRunner, valid_params: BacktestParams
    ):
        """Each call to run() should produce a unique run_id."""
        record1 = await runner.run(valid_params)
        record2 = await runner.run(valid_params)
        assert record1.run_id != record2.run_id


# ===================================================================
# git_commit_hash fallback (subprocess mock)
# ===================================================================


class TestGitCommitHashFallback:
    """Tests for git_commit_hash capture and fallback behavior."""

    @pytest.mark.asyncio
    async def test_git_hash_fallback_on_failure(
        self, runner: BacktestRunner, valid_params: BacktestParams, monkeypatch: pytest.MonkeyPatch
    ):
        """When git rev-parse fails, git_commit_hash should be None."""

        import subprocess

        def _mock_run(*args, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(subprocess, "run", _mock_run)
        record = await runner.run(valid_params)
        assert record.git_commit_hash is None

    @pytest.mark.asyncio
    async def test_git_hash_fallback_on_subprocess_error(
        self, runner: BacktestRunner, valid_params: BacktestParams, monkeypatch: pytest.MonkeyPatch
    ):
        """When git rev-parse returns non-zero, git_commit_hash should be None."""

        import subprocess

        def _mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(1, "git")

        monkeypatch.setattr(subprocess, "run", _mock_run)
        record = await runner.run(valid_params)
        assert record.git_commit_hash is None
