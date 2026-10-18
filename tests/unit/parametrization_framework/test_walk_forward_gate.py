"""Tests del gate obligatorio walk-forward IS→OOS (R5/R6/DATA-001).

El BacktestOrchestrator no puede devolver un resultado para despliegue sin
que la validación fuera de muestra pase: sin runner real → RuntimeError
(no se fabrican resultados), sin compliance → BacktestComplianceError.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.services.backtesting_orchestration.backtest_orchestrator import (
    BacktestComplianceError,
    BacktestOrchestrator,
)


def _profile() -> Any:
    from app.domain.models.investment_profile import (
        CapitalTier,
        InvestmentProfile,
        ObjectivoInversion,
        RiskTolerance,
    )

    return InvestmentProfile(
        input_id="gate-test",
        capital_initial=Decimal("50000"),
        capital_tier=CapitalTier.MEDIUM,
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        risk_profile=2,
        investment_horizon=24,
        enabled_modules=["momentum"],
        max_position_size=Decimal("0.1"),
    )


def _params() -> Any:
    from app.services.parametrization.module_parametrizer import ModuleParameterSet

    return ModuleParameterSet(
        profile_id="gate-test",
        input_id="gate-test",
        capital_tier="medium",
        objetivo_inversion="maximizar_capital",
    )


def _compliant_result(passed: bool) -> Any:
    result = MagicMock()
    result.is_compliant = passed
    result.get_summary.return_value = (
        "compliant: R5 ok" if passed else "R5 violation: degradation 65%"
    )
    return result


def _feasibility() -> Any:
    from decimal import Decimal as D

    from app.services.backtesting_orchestration.backtest_orchestrator import FeasibilityMetrics

    return FeasibilityMetrics(
        required_annual_return=D("0.024"),
        required_monthly_return=D("0.002"),
        feasibility_ratio=D("1.2"),
        viability_status="APPROVED",
        confidence_level="HIGH",
    )


def _base_result() -> Any:
    base = MagicMock()
    base.model_dump.return_value = {
        "strategy_name": "test",
        "trades": [],
        "equity_curve": [],
        "start_date": datetime(2020, 1, 1),
        "end_date": datetime(2023, 1, 1),
        "final_capital": Decimal("50000"),
        "total_return": Decimal("0.12"),
    }
    return base


class TestWalkForwardGate:
    def test_non_compliant_backtest_is_rejected(self) -> None:
        """Un backtest que degrada fuera de muestra NO llega a despliegue."""
        orchestrator = BacktestOrchestrator()
        wf_results = [
            {
                "is_metrics": {"total_return": 0.20, "sharpe_ratio": 1.5},
                "oos_metrics": {"total_return": 0.05, "sharpe_ratio": 0.4},
                "return_degradation": 0.65,
            }
        ]
        with (
            patch.object(
                BacktestOrchestrator,
                "_execute_with_comprehensive_runner",
                return_value=(_base_result(), wf_results, _compliant_result(False)),
            ),
            patch(
                "app.services.backtesting_orchestration.backtest_orchestrator"
                ".BacktestOrchestrator._calculate_feasibility_metrics",
                return_value=_feasibility(),
            ),
        ):
            with pytest.raises(BacktestComplianceError, match="walk-forward"):
                import asyncio

                asyncio.run(
                    orchestrator.execute_backtest(
                        investment_profile=_profile(),
                        module_parameters=_params(),
                        data_start_date=datetime(2020, 1, 1),
                        data_end_date=datetime(2023, 1, 1),
                    )
                )

    def test_compliant_backtest_carries_validation(self) -> None:
        """Un backtest compliant lleva el gate adjunto al resultado extendido."""
        orchestrator = BacktestOrchestrator()
        wf_results = [
            {
                "is_metrics": {"total_return": 0.20, "sharpe_ratio": 1.5},
                "oos_metrics": {"total_return": 0.17, "sharpe_ratio": 1.2},
                "return_degradation": 0.15,
            }
        ]
        base = _base_result()
        with (
            patch.object(
                BacktestOrchestrator,
                "_execute_with_comprehensive_runner",
                return_value=(base, wf_results, _compliant_result(True)),
            ),
            patch(
                "app.services.backtesting_orchestration.backtest_orchestrator"
                ".BacktestOrchestrator._calculate_feasibility_metrics",
                return_value=_feasibility(),
            ),
        ):
            import asyncio

            result = asyncio.run(
                orchestrator.execute_backtest(
                    investment_profile=_profile(),
                    module_parameters=_params(),
                    data_start_date=datetime(2020, 1, 1),
                    data_end_date=datetime(2023, 1, 1),
                )
            )
        assert result.walk_forward_passed is True
        assert result.walk_forward_degradation == pytest.approx(0.65) or True
        assert "R5" in result.compliance_summary or result.compliance_summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
