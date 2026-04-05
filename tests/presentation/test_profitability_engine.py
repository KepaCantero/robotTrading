"""Tests for ProfitabilityEngine.

TDD tests written first -- exercise verdict logic, score computation,
batch evaluation, and edge cases for the backtesting dashboard.
"""

from __future__ import annotations

from app.infrastructure.persistence.backtest_result_store import BacktestRunRecord
from app.presentation.dashboard.profitability_engine import ProfitabilityEngine, ProfitabilityResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run(
    *,
    strategy: str = "test_strategy",
    profile: str | None = "maximizar_capital",
    total_return: float | None = 0.25,
    sharpe_ratio: float | None = 1.5,
    sortino_ratio: float | None = 2.0,
    max_drawdown: float | None = -0.08,
    win_rate: float | None = 0.60,
    profit_factor: float | None = 2.0,
    total_trades: int | None = 100,
) -> BacktestRunRecord:
    """Build a BacktestRunRecord with sensible defaults for testing."""
    return BacktestRunRecord(
        strategy_name=strategy,
        investor_profile=profile,
        total_return=total_return,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_trades=total_trades,
    )


# ===================================================================
# 1. PASS verdict tests
# ===================================================================


class TestPassVerdict:
    """When all profile thresholds are met the verdict must be PASS."""

    def test_maximizar_capital_pass(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=1.5,
            total_return=0.20,
            max_drawdown=-0.08,
            win_rate=0.60,
            profit_factor=2.0,
            total_trades=50,
        )
        result = engine.evaluate(run)
        assert result.verdict == "PASS"
        assert result.profile == "maximizar_capital"
        assert result.strategy == "test_strategy"

    def test_balanced_growth_pass(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="balanced_growth",
            sharpe_ratio=1.2,
            total_return=0.15,
        )
        result = engine.evaluate(run)
        assert result.verdict == "PASS"

    def test_maximizar_dividendos_pass(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_dividendos",
            sharpe_ratio=0.9,
            total_return=0.12,
        )
        result = engine.evaluate(run)
        assert result.verdict == "PASS"

    def test_capital_preservation_pass(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="capital_preservation",
            sharpe_ratio=0.6,
            total_return=0.06,
            max_drawdown=-0.05,
        )
        result = engine.evaluate(run)
        assert result.verdict == "PASS"

    def test_income_generation_pass(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="income_generation",
            sharpe_ratio=0.8,
            total_return=0.12,
        )
        result = engine.evaluate(run)
        assert result.verdict == "PASS"


# ===================================================================
# 2. FAIL verdict tests
# ===================================================================


class TestFailVerdict:
    """FAIL when primary metric is below threshold or drawdown exceeds limit."""

    def test_maximizar_capital_low_sharpe(self) -> None:
        """Primary metric (sharpe_ratio) below threshold => FAIL."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=0.8,  # below 1.0 threshold
            total_return=0.20,
        )
        result = engine.evaluate(run)
        assert result.verdict == "FAIL"

    def test_maximizar_capital_low_return(self) -> None:
        """min_return not met => FAIL."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=1.5,
            total_return=0.05,  # below 0.10 threshold
        )
        result = engine.evaluate(run)
        assert result.verdict == "FAIL"

    def test_capital_preservation_excessive_drawdown(self) -> None:
        """Drawdown exceeds the profile-specific limit => FAIL."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="capital_preservation",
            sharpe_ratio=0.6,
            total_return=0.06,
            max_drawdown=-0.15,  # exceeds 0.10 limit
        )
        result = engine.evaluate(run)
        assert result.verdict == "FAIL"

    def test_capital_preservation_low_sharpe(self) -> None:
        """Sharpe below threshold for capital_preservation => FAIL."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="capital_preservation",
            sharpe_ratio=0.3,  # below 0.5
            total_return=0.06,
            max_drawdown=-0.05,
        )
        result = engine.evaluate(run)
        assert result.verdict == "FAIL"

    def test_income_generation_low_sharpe(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="income_generation",
            sharpe_ratio=0.5,  # below 0.7
            total_return=0.12,
        )
        result = engine.evaluate(run)
        assert result.verdict == "FAIL"

    def test_maximizar_dividendos_low_return(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_dividendos",
            sharpe_ratio=0.9,
            total_return=0.05,  # below 0.10
        )
        result = engine.evaluate(run)
        assert result.verdict == "FAIL"


# ===================================================================
# 3. INCONCLUSIVE verdict tests
# ===================================================================


class TestInconclusiveVerdict:
    """INCONCLUSIVE when None metrics prevent full evaluation."""

    def test_missing_primary_metric(self) -> None:
        """When the primary metric is None, cannot determine pass/fail."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=None,  # primary metric missing
            total_return=0.20,
        )
        result = engine.evaluate(run)
        assert result.verdict == "INCONCLUSIVE"

    def test_missing_return(self) -> None:
        """When total_return is None => INCONCLUSIVE."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=1.5,
            total_return=None,
        )
        result = engine.evaluate(run)
        assert result.verdict == "INCONCLUSIVE"

    def test_all_metrics_none(self) -> None:
        engine = ProfitabilityEngine()
        run = BacktestRunRecord(
            strategy_name="empty_strategy",
            investor_profile="maximizar_capital",
        )
        result = engine.evaluate(run)
        assert result.verdict == "INCONCLUSIVE"

    def test_missing_drawdown_for_preservation(self) -> None:
        """capital_preservation needs drawdown; missing => INCONCLUSIVE."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="capital_preservation",
            sharpe_ratio=0.6,
            total_return=0.06,
            max_drawdown=None,
        )
        result = engine.evaluate(run)
        assert result.verdict == "INCONCLUSIVE"

    def test_inconclusive_has_warnings(self) -> None:
        """INCONCLUSIVE result should list missing metrics as warnings."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=None,
            total_return=None,
        )
        result = engine.evaluate(run)
        assert result.verdict == "INCONCLUSIVE"
        assert len(result.warnings) > 0


# ===================================================================
# 4. Score computation tests
# ===================================================================


class TestScoreComputation:
    """Verify the 0-100 risk-adjusted score formula."""

    def test_score_clamped_at_100(self) -> None:
        """Excellent metrics should clamp at 100."""
        engine = ProfitabilityEngine()
        run = _make_run(
            sharpe_ratio=3.0,
            total_return=1.0,
            max_drawdown=-0.01,
            win_rate=0.90,
            profit_factor=5.0,
        )
        score = engine.compute_score(run)
        assert score == 100.0

    def test_score_clamped_at_0(self) -> None:
        """Terrible metrics should clamp at 0."""
        engine = ProfitabilityEngine()
        run = _make_run(
            sharpe_ratio=-1.0,
            total_return=-0.5,
            max_drawdown=-0.30,
            win_rate=0.10,
            profit_factor=0.5,
        )
        score = engine.compute_score(run)
        assert score == 0.0

    def test_score_with_none_metrics(self) -> None:
        """None metrics contribute 0 to their component."""
        engine = ProfitabilityEngine()
        run = BacktestRunRecord(strategy_name="sparse")
        score = engine.compute_score(run)
        assert score == 0.0

    def test_score_reasonable_run(self) -> None:
        """Manually verify score components for a typical run."""
        engine = ProfitabilityEngine()
        # sharpe * 20 = 1.5 * 20 = 30
        # min(abs(0.25) * 100, 30) = min(25, 30) = 25
        # drawdown penalty = abs(-0.08) * 100 = 8
        # win_rate * 30 = 0.60 * 30 = 18
        # profit_factor bonus = min((2.0 - 1) * 10, 20) = min(10, 20) = 10
        # Total = 30 + 25 - 8 + 18 + 10 = 75
        run = _make_run(
            sharpe_ratio=1.5,
            total_return=0.25,
            max_drawdown=-0.08,
            win_rate=0.60,
            profit_factor=2.0,
        )
        score = engine.compute_score(run)
        assert score == 75.0

    def test_score_sharpe_capped_at_40(self) -> None:
        """Sharpe contribution: sharpe * 20, max 40."""
        engine = ProfitabilityEngine()
        run = _make_run(
            sharpe_ratio=3.0,  # 3.0 * 20 = 60 -> capped at 40
            total_return=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            profit_factor=1.0,
        )
        score = engine.compute_score(run)
        assert score == 40.0

    def test_score_return_capped_at_30(self) -> None:
        """Return contribution: min(abs(return)*100, 30)."""
        engine = ProfitabilityEngine()
        run = _make_run(
            sharpe_ratio=0.0,
            total_return=0.50,  # 0.50 * 100 = 50 -> capped at 30
            max_drawdown=0.0,
            win_rate=0.0,
            profit_factor=1.0,
        )
        score = engine.compute_score(run)
        assert score == 30.0

    def test_score_drawdown_penalty_max_20(self) -> None:
        """Drawdown penalty: abs(max_drawdown) * 100, max 20."""
        engine = ProfitabilityEngine()
        run = _make_run(
            sharpe_ratio=0.0,
            total_return=0.0,
            max_drawdown=-0.50,  # 0.50 * 100 = 50 -> capped at 20
            win_rate=0.0,
            profit_factor=1.0,
        )
        score = engine.compute_score(run)
        assert score == 0.0  # 0 + 0 - 20 + 0 + 0 = -20 -> clamped to 0

    def test_score_win_rate_capped_at_30(self) -> None:
        """Win rate bonus: win_rate * 30, max 30."""
        engine = ProfitabilityEngine()
        run = _make_run(
            sharpe_ratio=0.0,
            total_return=0.0,
            max_drawdown=0.0,
            win_rate=1.0,  # 1.0 * 30 = 30 -> capped at 30
            profit_factor=1.0,
        )
        score = engine.compute_score(run)
        assert score == 30.0

    def test_score_profit_factor_capped_at_20(self) -> None:
        """Profit factor bonus: min((pf - 1) * 10, 20)."""
        engine = ProfitabilityEngine()
        run = _make_run(
            sharpe_ratio=0.0,
            total_return=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            profit_factor=5.0,  # (5.0 - 1) * 10 = 40 -> capped at 20
        )
        score = engine.compute_score(run)
        assert score == 20.0

    def test_score_in_result(self) -> None:
        """The score is reflected in the ProfitabilityResult."""
        engine = ProfitabilityEngine()
        run = _make_run(
            sharpe_ratio=1.5,
            total_return=0.25,
            max_drawdown=-0.08,
            win_rate=0.60,
            profit_factor=2.0,
        )
        result = engine.evaluate(run)
        assert result.score == 75.0


# ===================================================================
# 5. Details dict tests
# ===================================================================


class TestDetailsDict:
    """The details dict should contain per-metric evaluation info."""

    def test_details_keys_present(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(profile="maximizar_capital")
        result = engine.evaluate(run)
        assert "sharpe_ratio" in result.details
        assert "total_return" in result.details

    def test_details_structure(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(profile="maximizar_capital")
        result = engine.evaluate(run)
        sharpe_detail = result.details["sharpe_ratio"]
        assert "value" in sharpe_detail
        assert "threshold" in sharpe_detail
        assert "passed" in sharpe_detail

    def test_details_passed_flag(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=1.5,
        )
        result = engine.evaluate(run)
        assert result.details["sharpe_ratio"]["passed"] is True

    def test_details_failed_flag(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=0.5,
        )
        result = engine.evaluate(run)
        assert result.details["sharpe_ratio"]["passed"] is False


# ===================================================================
# 6. evaluate_with_profile tests
# ===================================================================


class TestEvaluateWithProfile:
    """evaluate_with_profile overrides the record's own profile."""

    def test_override_profile(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(profile="maximizar_capital")
        result = engine.evaluate_with_profile(run, "capital_preservation")
        assert result.profile == "capital_preservation"

    def test_uses_overridden_thresholds(self) -> None:
        """capital_preservation has a max_drawdown_limit."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=0.6,
            total_return=0.06,
            max_drawdown=-0.15,  # exceeds capital_preservation 0.10 limit
        )
        result = engine.evaluate_with_profile(run, "capital_preservation")
        assert result.verdict == "FAIL"

    def test_none_profile_falls_back(self) -> None:
        """When record has no profile, evaluate_with_profile sets one."""
        engine = ProfitabilityEngine()
        run = _make_run(profile=None, sharpe_ratio=1.5, total_return=0.20)
        result = engine.evaluate_with_profile(run, "balanced_growth")
        assert result.profile == "balanced_growth"
        assert result.verdict == "PASS"


# ===================================================================
# 7. Unknown profile fallback tests
# ===================================================================


class TestUnknownProfile:
    """When the profile is unknown/None, fall back to default criteria."""

    def test_unknown_profile_uses_defaults(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(profile="nonexistent_profile")
        # With default criteria, sharpe 1.5 > 0.5, so should pass
        # primary_metric is unknown -> fall back to sharpe_ratio check
        result = engine.evaluate(run)
        assert result.profile == "nonexistent_profile"

    def test_none_profile_uses_defaults(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(profile=None, sharpe_ratio=1.5, total_return=0.20)
        result = engine.evaluate(run)
        assert result.profile == "unknown"

    def test_unknown_profile_with_good_metrics(self) -> None:
        """Even with unknown profile, good metrics should yield PASS."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="mystery",
            sharpe_ratio=2.0,
            total_return=0.30,
            max_drawdown=-0.05,
            win_rate=0.70,
            profit_factor=2.5,
            total_trades=50,
        )
        result = engine.evaluate(run)
        assert result.verdict == "PASS"

    def test_unknown_profile_with_bad_metrics(self) -> None:
        """Unknown profile, bad metrics should yield FAIL."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="mystery",
            sharpe_ratio=0.2,
            total_return=-0.10,
            max_drawdown=-0.30,
            win_rate=0.30,
            profit_factor=0.8,
            total_trades=10,
        )
        result = engine.evaluate(run)
        assert result.verdict == "FAIL"


# ===================================================================
# 8. Batch evaluation tests
# ===================================================================


class TestBatchEvaluate:
    """batch_evaluate processes multiple runs and returns a list."""

    def test_batch_returns_correct_count(self) -> None:
        engine = ProfitabilityEngine()
        runs = [
            _make_run(strategy="s1"),
            _make_run(strategy="s2"),
            _make_run(strategy="s3"),
        ]
        results = engine.batch_evaluate(runs)
        assert len(results) == 3

    def test_batch_preserves_strategies(self) -> None:
        engine = ProfitabilityEngine()
        runs = [
            _make_run(strategy="alpha"),
            _make_run(strategy="beta"),
        ]
        results = engine.batch_evaluate(runs)
        assert results[0].strategy == "alpha"
        assert results[1].strategy == "beta"

    def test_batch_empty_list(self) -> None:
        engine = ProfitabilityEngine()
        results = engine.batch_evaluate([])
        assert results == []

    def test_batch_mixed_verdicts(self) -> None:
        engine = ProfitabilityEngine()
        runs = [
            _make_run(strategy="good", sharpe_ratio=1.5, total_return=0.20),
            _make_run(strategy="bad", sharpe_ratio=0.3, total_return=0.02),
            _make_run(strategy="incomplete", sharpe_ratio=None, total_return=None),
        ]
        results = engine.batch_evaluate(runs)
        verdicts = [r.verdict for r in results]
        assert verdicts[0] == "PASS"
        assert verdicts[1] == "FAIL"
        assert verdicts[2] == "INCONCLUSIVE"

    def test_batch_results_are_profitability_results(self) -> None:
        engine = ProfitabilityEngine()
        runs = [_make_run()]
        results = engine.batch_evaluate(runs)
        assert isinstance(results[0], ProfitabilityResult)


# ===================================================================
# 9. ProfitabilityResult model tests
# ===================================================================


class TestProfitabilityResultModel:
    """Validate the ProfitabilityResult Pydantic model."""

    def test_fields_present(self) -> None:
        result = ProfitabilityResult(
            verdict="PASS",
            score=80.0,
            profile="maximizar_capital",
            strategy="test",
            details={"sharpe_ratio": {"value": 1.5, "threshold": 1.0, "passed": True}},
        )
        assert result.verdict == "PASS"
        assert result.score == 80.0
        assert result.profile == "maximizar_capital"
        assert result.strategy == "test"
        assert result.warnings == []

    def test_warnings_default_empty(self) -> None:
        result = ProfitabilityResult(
            verdict="PASS",
            score=90.0,
            profile="balanced_growth",
            strategy="s",
            details={},
        )
        assert result.warnings == []

    def test_invalid_verdict_accepted(self) -> None:
        """The model does not restrict verdict values at the model level."""
        result = ProfitabilityResult(
            verdict="MAYBE",
            score=50.0,
            profile="test",
            strategy="s",
            details={},
        )
        assert result.verdict == "MAYBE"


# ===================================================================
# 10. Edge cases
# ===================================================================


class TestEdgeCases:
    """Boundary and corner-case scenarios."""

    def test_exact_threshold_pass(self) -> None:
        """Metrics exactly at the threshold should pass."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=1.0,  # exactly at threshold
            total_return=0.10,  # exactly at threshold
        )
        result = engine.evaluate(run)
        assert result.verdict == "PASS"

    def test_just_below_threshold_fail(self) -> None:
        """Metrics just below threshold should fail."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=0.99,  # just below
            total_return=0.10,
        )
        result = engine.evaluate(run)
        assert result.verdict == "FAIL"

    def test_negative_sharpe(self) -> None:
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="maximizar_capital",
            sharpe_ratio=-0.5,
            total_return=-0.10,
        )
        result = engine.evaluate(run)
        assert result.verdict == "FAIL"

    def test_zero_drawdown_pass(self) -> None:
        """Zero drawdown is valid (no losses)."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="capital_preservation",
            sharpe_ratio=0.6,
            total_return=0.06,
            max_drawdown=0.0,
        )
        result = engine.evaluate(run)
        assert result.verdict == "PASS"

    def test_drawdown_at_exact_limit(self) -> None:
        """Drawdown exactly at the limit should pass (<= check)."""
        engine = ProfitabilityEngine()
        run = _make_run(
            profile="capital_preservation",
            sharpe_ratio=0.6,
            total_return=0.06,
            max_drawdown=-0.10,  # exactly at limit
        )
        result = engine.evaluate(run)
        assert result.verdict == "PASS"

    def test_score_negative_clamps_to_zero(self) -> None:
        """Even if raw score is negative, result is clamped to 0."""
        engine = ProfitabilityEngine()
        run = _make_run(
            sharpe_ratio=-2.0,
            total_return=-0.50,
            max_drawdown=-0.30,
            win_rate=0.10,
            profit_factor=0.3,
        )
        score = engine.compute_score(run)
        assert score == 0.0

    def test_evaluate_uses_record_profile(self) -> None:
        """evaluate() reads the profile from the BacktestRunRecord."""
        engine = ProfitabilityEngine()
        run = _make_run(profile="income_generation")
        result = engine.evaluate(run)
        assert result.profile == "income_generation"
