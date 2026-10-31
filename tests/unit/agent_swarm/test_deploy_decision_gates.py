"""FIX 3 (owner 31-10): the swarm T10.1 verdict is BINARY.

Hard gates, none compensable by score: validation passed, Sharpe >= 0.50,
drawdown within the risk profile's tolerance, feasibility >= 1.0, and the
strategy at least matches its passive twin after costs (2 pp execution
tolerance). REJECTED carries the exact list of failures and the structural
change that would approve it. CONDITIONAL is retired.
"""

from decimal import Decimal

import pytest

from app.services.deployment.deploy_decision_orchestrator import DeployDecisionOrchestrator


def _input(
    *,
    sharpe: float = 0.8,
    feasibility: float = 1.2,
    drawdown: float = 20.0,
    twin: float = 100.0,
    strategy_return: float = 105.0,
    validation: str = "APPROVED",
    risk_profile: str = "AGGRESSIVE",
    executed_strategy: str = "static_ew",
    weight_dev_pp: float | None = 0.3,
    avg_cash_pct: float | None = 0.5,
    total_trades: int = 8,
    commissions_pp: float = 0.05,
) -> dict:
    return {
        "validation_report": {"overall_status": validation},
        "backtest_result": {
            "feasibility_ratio": feasibility,
            "sharpe_ratio": sharpe,
            "total_return": strategy_return,
            "max_drawdown": drawdown,
            "total_trades": total_trades,
            "commissions_paid_pct": commissions_pp,
            "universe_ew_return_pct": twin,
            "universe_ew_sharpe": 0.9,
        },
        "recommendation": {"score": 65.0, "executed_strategy": executed_strategy},
        "allocation": {
            "allocation": {"A": 0.5, "B": 0.5},
            "sharpe_ratio": sharpe,
            "diversification_ratio": 1.0,
            "max_weight_deviation_pct": weight_dev_pp,
            "avg_cash_pct": avg_cash_pct,
        },
        "investment_profile": {"risk_profile": risk_profile},
    }


class TestBinaryVerdicts:
    @pytest.mark.asyncio
    async def test_all_gates_pass_is_approved(self):
        decision = await DeployDecisionOrchestrator().orchestrate(**_input())
        assert decision.status == "APPROVED"
        assert not any("CONDITIONAL" in r for r in decision.reasons)

    @pytest.mark.asyncio
    async def test_score_never_compensates_a_failed_gate(self):
        # score 95 but Sharpe 0.49: REJECTED — gates are hard (FIX 3)
        payload = _input(sharpe=0.49)
        payload["recommendation"]["score"] = 95.0
        decision = await DeployDecisionOrchestrator().orchestrate(**payload)
        assert decision.status == "REJECTED"
        assert any("Sharpe 0.49" in r for r in decision.reasons)

    @pytest.mark.asyncio
    async def test_sharpe_below_floor_rejects_with_exact_number(self):
        decision = await DeployDecisionOrchestrator().orchestrate(**_input(sharpe=0.40))
        assert decision.status == "REJECTED"
        assert any("Sharpe 0.40 < 0.50" in r for r in decision.reasons)
        assert any("0.40" in s for s in decision.next_steps)

    @pytest.mark.asyncio
    async def test_drawdown_gate_uses_risk_profile_tolerance(self):
        # 32% DD: within aggressive 35, over moderate 30
        ok = await DeployDecisionOrchestrator().orchestrate(
            **_input(drawdown=32.0, risk_profile="AGGRESSIVE")
        )
        assert ok.status == "APPROVED"
        rejected = await DeployDecisionOrchestrator().orchestrate(
            **_input(drawdown=32.0, risk_profile="MODERATE")
        )
        assert rejected.status == "REJECTED"
        assert any("32.0% > 30%" in r for r in rejected.reasons)

    @pytest.mark.asyncio
    async def test_feasibility_below_one_rejects(self):
        decision = await DeployDecisionOrchestrator().orchestrate(**_input(feasibility=0.95))
        assert decision.status == "REJECTED"
        assert any("feasibility ratio 0.95" in r.lower() for r in decision.reasons)

    @pytest.mark.asyncio
    async def test_trailing_the_twin_beyond_two_pp_rejects(self):
        # twin +100, strategy +97.5: 2.5 pp trail > 2 pp tolerance
        decision = await DeployDecisionOrchestrator().orchestrate(
            **_input(twin=100.0, strategy_return=97.5)
        )
        assert decision.status == "REJECTED"
        assert any("passive twin" in r for r in decision.reasons)
        # exactly within tolerance (2.0 pp) stays APPROVED
        edge = await DeployDecisionOrchestrator().orchestrate(
            **_input(twin=100.0, strategy_return=98.0)
        )
        assert edge.status == "APPROVED"

    @pytest.mark.asyncio
    async def test_validation_failure_rejects(self):
        decision = await DeployDecisionOrchestrator().orchestrate(**_input(validation="REJECTED"))
        assert decision.status == "REJECTED"
        assert any("validation gates failed" in r for r in decision.reasons)

    @pytest.mark.asyncio
    async def test_conditional_is_never_emitted(self):
        # the old CONDITIONAL band (feasibility 0.8, score 68) is now REJECTED
        payload = _input(feasibility=0.8)
        payload["recommendation"]["score"] = 68.0
        decision = await DeployDecisionOrchestrator().orchestrate(**payload)
        assert decision.status == "REJECTED"

    @pytest.mark.asyncio
    async def test_rejected_names_the_structural_change(self):
        decision = await DeployDecisionOrchestrator().orchestrate(**_input(sharpe=0.40))
        assert any("structural" in s.lower() for s in decision.next_steps)


class TestPassiveHonestyCopy:
    @pytest.mark.asyncio
    async def test_approved_static_ew_within_bars_claims_passive(self):
        decision = await DeployDecisionOrchestrator().orchestrate(
            **_input(weight_dev_pp=0.4, avg_cash_pct=0.6)
        )
        assert decision.status == "APPROVED"
        assert any("This IS the passive portfolio" in s for s in decision.next_steps)
        assert any("0.40 pp" in s and "0.60%" in s for s in decision.next_steps)

    @pytest.mark.asyncio
    async def test_deviated_weights_say_not_passive_with_numbers(self):
        decision = await DeployDecisionOrchestrator().orchestrate(
            **_input(weight_dev_pp=4.4, avg_cash_pct=0.6)
        )
        assert decision.status == "APPROVED"
        assert any(
            "This is NOT the passive portfolio" in s and "4.40 pp" in s for s in decision.next_steps
        )

    @pytest.mark.asyncio
    async def test_cash_above_one_percent_says_not_passive(self):
        decision = await DeployDecisionOrchestrator().orchestrate(
            **_input(weight_dev_pp=0.4, avg_cash_pct=2.1)
        )
        assert any(
            "This is NOT the passive portfolio" in s and "2.10%" in s for s in decision.next_steps
        )

    @pytest.mark.asyncio
    async def test_twin_rejection_with_few_trades_is_a_deployment_bug(self):
        # twin +100, strategy +97.5 (2.5 pp > 2 pp tolerance), 8 trades:
        # REJECTED — and the >2 pp gap on <20 trades is labelled a
        # DEPLOYMENT BUG, never execution cost (honesty rule 31-10)
        bugged = await DeployDecisionOrchestrator().orchestrate(
            **_input(twin=100.0, strategy_return=97.5, total_trades=8)
        )
        assert bugged.status == "REJECTED"
        assert any("DEPLOYMENT BUG" in r for r in bugged.reasons)
        assert any("deployment bug" in s.lower() for s in bugged.next_steps)

        # the same gap with 40 trades is honest cost-shaped, not a bug label
        costly = await DeployDecisionOrchestrator().orchestrate(
            **_input(twin=100.0, strategy_return=97.5, total_trades=40)
        )
        assert costly.status == "REJECTED"
        assert not any("DEPLOYMENT BUG" in r for r in costly.reasons)

    @pytest.mark.asyncio
    async def test_approved_static_ew_gap_decomposes_honestly(self):
        # within the 2 pp gate the gap is decomposed: cash + commissions +
        # residual — informational, no bug label possible there
        decision = await DeployDecisionOrchestrator().orchestrate(
            **_input(twin=100.0, strategy_return=98.5, avg_cash_pct=0.5)
        )
        assert decision.status == "APPROVED"
        assert any("decomposed honestly" in r for r in decision.reasons)
        assert any("residual" in r for r in decision.reasons)
        assert not any("DEPLOYMENT BUG" in r for r in decision.reasons)

    @pytest.mark.asyncio
    async def test_managed_strategy_trailing_twin_gets_passive_advice(self):
        payload = _input(twin=100.0, strategy_return=104.0, executed_strategy="mean_reversion")
        decision = await DeployDecisionOrchestrator().orchestrate(**payload)
        assert decision.status == "APPROVED"
        # a managed strategy barely beating the twin still gets the honest
        # pointer when it trails; here it beats it, so no passive advice
        assert not any("subtracted value" in r for r in decision.reasons)


class TestAllocationHonestyMetrics:
    """T7.1 metrics feeding the copy: deviation vs 1/N and average cash."""

    def test_twisted_sleeves_measure_high_deviation_and_cash(self):
        from app.services.agent_swarm.portfolio_allocation import allocation_from_backtest

        # the twisted 8fb715 pattern: bond/world sleeves at 29.4%, equity
        # at 21.3/19.9% — never the 1/N passive it claimed to be
        trades = [
            {
                "symbol": "EUNL.DE",
                "entry_price": "38.10",
                "quantity": "624",
                "entry_time": "2016-11-02",
                "exit_time": "2026-10-30",
            },
            {
                "symbol": "IBGS.AS",
                "entry_price": "134.18",
                "quantity": "177.2",
                "entry_time": "2016-11-02",
                "exit_time": "2026-10-30",
            },
            {
                "symbol": "IUSQ.DE",
                "entry_price": "37.41",
                "quantity": "472.8",
                "entry_time": "2017-02-06",
                "exit_time": "2026-10-30",
            },
            {
                "symbol": "EIMI.MI",
                "entry_price": "20.13",
                "quantity": "801.35",
                "entry_time": "2016-11-03",
                "exit_time": "2026-10-30",
            },
        ]
        allocation = allocation_from_backtest(
            profile_id="P",
            capital_eur=Decimal("100000"),
            trades_summary=trades,
            annual_return_pct=Decimal("7.8"),
            sharpe_ratio=Decimal("0.4"),
            max_drawdown_pct=Decimal("-22"),
            window_days=3652,
        )
        assert allocation.max_weight_deviation_pct is not None
        assert allocation.max_weight_deviation_pct > Decimal("4")  # 29.4 vs 25
        assert allocation.avg_cash_pct is not None
        assert allocation.avg_cash_pct > Decimal("15")  # ~18.6% never deployed

    def test_equal_sleeves_measure_passive(self):
        from app.services.agent_swarm.portfolio_allocation import allocation_from_backtest

        # 99% deployed: two sleeves at 49.5% of capital each (price 100,
        # 495 shares each) -> weights 50/50, cash ~1% (entry t+1 aside)
        trades = [
            {
                "symbol": s,
                "entry_price": "100",
                "quantity": "495",
                "entry_time": "2021-05-17",
                "exit_time": "2026-10-30",
            }
            for s in ("VWCE", "AGGH.AS")
        ]
        allocation = allocation_from_backtest(
            profile_id="P",
            capital_eur=Decimal("100000"),
            trades_summary=trades,
            annual_return_pct=Decimal("6"),
            sharpe_ratio=Decimal("0.8"),
            max_drawdown_pct=Decimal("-15"),
            window_days=1990,
        )
        assert allocation.max_weight_deviation_pct < Decimal("1")
        assert allocation.avg_cash_pct < Decimal("1.5")
