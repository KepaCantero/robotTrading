"""
Unit tests for Capital Phase Manager (R25, R26, R27)

Tests cover:
- Phase determination based on capital
- Phase transitions
- Risk parameter retrieval
- Position size validation
- Phase summaries
- Capital progress calculation
"""

import unittest
from datetime import datetime
from decimal import Decimal

from app.services.capital import (
    PHASE_CONFIGS,
    PHASE_THRESHOLDS,
    CapitalPhase,
    CapitalPhaseEvent,
    CapitalPhaseManager,
    PhaseRiskParameters,
)


class TestPhaseConfig(unittest.TestCase):
    """Test phase configuration constants."""

    def test_three_phases_defined(self) -> None:
        """Test that exactly 3 phases are defined."""
        self.assertEqual(len(PHASE_CONFIGS), 3)
        self.assertIn(CapitalPhase.SURVIVAL, PHASE_CONFIGS)
        self.assertIn(CapitalPhase.GROWTH, PHASE_CONFIGS)
        self.assertIn(CapitalPhase.OPTIMIZATION, PHASE_CONFIGS)

    def test_survival_phase_config(self) -> None:
        """Test R25: Survival phase has correct parameters."""
        params = PHASE_CONFIGS[CapitalPhase.SURVIVAL]

        # R25: 1% max risk per trade
        self.assertEqual(params.max_risk_per_trade_pct, Decimal("0.01"))

        # 5% max portfolio risk
        self.assertEqual(params.max_portfolio_risk_pct, Decimal("0.05"))

        # Max 3 positions
        self.assertEqual(params.max_positions, 3)

        # NO leverage allowed
        self.assertFalse(params.leverage_allowed)

        # Kelly half for conservative sizing
        self.assertEqual(params.position_sizing_method, "kelly_half")

    def test_growth_phase_config(self) -> None:
        """Test R26: Growth phase has correct parameters."""
        params = PHASE_CONFIGS[CapitalPhase.GROWTH]

        # R26: 2% max risk per trade
        self.assertEqual(params.max_risk_per_trade_pct, Decimal("0.02"))

        # 10% max portfolio risk
        self.assertEqual(params.max_portfolio_risk_pct, Decimal("0.10"))

        # Max 5 positions
        self.assertEqual(params.max_positions, 5)

        # NO leverage allowed
        self.assertFalse(params.leverage_allowed)

        # Full Kelly
        self.assertEqual(params.position_sizing_method, "kelly")

    def test_optimization_phase_config(self) -> None:
        """Test R27: Optimization phase has correct parameters."""
        params = PHASE_CONFIGS[CapitalPhase.OPTIMIZATION]

        # R27: 3% max risk per trade
        self.assertEqual(params.max_risk_per_trade_pct, Decimal("0.03"))

        # 15% max portfolio risk
        self.assertEqual(params.max_portfolio_risk_pct, Decimal("0.15"))

        # Max 8 positions
        self.assertEqual(params.max_positions, 8)

        # Leverage ALLOWED
        self.assertTrue(params.leverage_allowed)

        # Optimized Kelly
        self.assertEqual(params.position_sizing_method, "kelly_optimized")

    def test_phase_thresholds(self) -> None:
        """Test phase thresholds are correct."""
        # Survival: €1k - €10k
        min_survival, max_survival = PHASE_THRESHOLDS[CapitalPhase.SURVIVAL]
        self.assertEqual(min_survival, Decimal("1000"))
        self.assertEqual(max_survival, Decimal("10000"))

        # Growth: €10k - €50k
        min_growth, max_growth = PHASE_THRESHOLDS[CapitalPhase.GROWTH]
        self.assertEqual(min_growth, Decimal("10000"))
        self.assertEqual(max_growth, Decimal("50000"))

        # Optimization: €50k+
        min_opt, max_opt = PHASE_THRESHOLDS[CapitalPhase.OPTIMIZATION]
        self.assertEqual(min_opt, Decimal("50000"))
        self.assertEqual(max_opt, Decimal("999999999"))


class TestCapitalPhaseManager(unittest.TestCase):
    """Test CapitalPhaseManager functionality."""

    def test_initialization_requires_minimum_capital(self) -> None:
        """Test that initial capital must be at least €1,000."""
        with self.assertRaises(ValueError) as context:
            CapitalPhaseManager(initial_capital=Decimal("500"))
        self.assertIn("at least €1,000", str(context.exception))

    def test_initialization_at_minimum(self) -> None:
        """Test initialization at exactly €1,000."""
        manager = CapitalPhaseManager(initial_capital=Decimal("1000"))
        self.assertEqual(manager.get_current_capital(), Decimal("1000"))
        self.assertEqual(manager.get_current_phase(), CapitalPhase.SURVIVAL)

    def test_survival_phase_determination(self) -> None:
        """Test phase determination for Survival phase."""
        # Test various capital levels in Survival range
        for capital in [Decimal("1000"), Decimal("5000"), Decimal("9999")]:
            manager = CapitalPhaseManager(initial_capital=capital)
            self.assertEqual(manager.get_current_phase(), CapitalPhase.SURVIVAL)

    def test_growth_phase_determination(self) -> None:
        """Test phase determination for Growth phase."""
        # Test various capital levels in Growth range
        for capital in [Decimal("10000"), Decimal("25000"), Decimal("49999")]:
            manager = CapitalPhaseManager(initial_capital=capital)
            self.assertEqual(manager.get_current_phase(), CapitalPhase.GROWTH)

    def test_optimization_phase_determination(self) -> None:
        """Test phase determination for Optimization phase."""
        # Test various capital levels in Optimization range
        for capital in [Decimal("50000"), Decimal("100000"), Decimal("500000")]:
            manager = CapitalPhaseManager(initial_capital=capital)
            self.assertEqual(manager.get_current_phase(), CapitalPhase.OPTIMIZATION)

    def test_phase_transition_survival_to_growth(self) -> None:
        """Test transition from Survival to Growth phase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
        self.assertEqual(manager.get_current_phase(), CapitalPhase.SURVIVAL)

        # Update to Growth phase
        new_phase = manager.update_capital(Decimal("15000"))
        self.assertEqual(new_phase, CapitalPhase.GROWTH)
        self.assertEqual(manager.get_current_phase(), CapitalPhase.GROWTH)

        # Check history was recorded
        history = manager.get_phase_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["old_phase"], "survival")
        self.assertEqual(history[0]["new_phase"], "growth")

    def test_phase_transition_growth_to_optimization(self) -> None:
        """Test transition from Growth to Optimization phase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("25000"))
        self.assertEqual(manager.get_current_phase(), CapitalPhase.GROWTH)

        # Update to Optimization phase
        new_phase = manager.update_capital(Decimal("75000"))
        self.assertEqual(new_phase, CapitalPhase.OPTIMIZATION)
        self.assertEqual(manager.get_current_phase(), CapitalPhase.OPTIMIZATION)

        # Check history was recorded
        history = manager.get_phase_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["old_phase"], "growth")
        self.assertEqual(history[0]["new_phase"], "optimization")

    def test_no_phase_transition_within_same_phase(self) -> None:
        """Test that no transition occurs within same phase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))

        # Update within same phase
        new_phase = manager.update_capital(Decimal("8000"))
        self.assertEqual(new_phase, CapitalPhase.SURVIVAL)
        self.assertEqual(len(manager.get_phase_history()), 0)

    def test_update_capital_cannot_go_below_minimum(self) -> None:
        """Test that capital cannot fall below €1,000."""
        manager = CapitalPhaseManager(initial_capital=Decimal("10000"))
        with self.assertRaises(ValueError) as context:
            manager.update_capital(Decimal("500"))
        self.assertIn("cannot fall below €1,000", str(context.exception))

    def test_get_risk_parameters_survival(self) -> None:
        """Test getting risk parameters for Survival phase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
        params = manager.get_risk_parameters()

        self.assertIsInstance(params, PhaseRiskParameters)
        self.assertEqual(params.max_risk_per_trade_pct, Decimal("0.01"))
        self.assertEqual(params.max_portfolio_risk_pct, Decimal("0.05"))
        self.assertEqual(params.max_positions, 3)
        self.assertFalse(params.leverage_allowed)

    def test_get_risk_parameters_growth(self) -> None:
        """Test getting risk parameters for Growth phase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("25000"))
        params = manager.get_risk_parameters()

        self.assertIsInstance(params, PhaseRiskParameters)
        self.assertEqual(params.max_risk_per_trade_pct, Decimal("0.02"))
        self.assertEqual(params.max_portfolio_risk_pct, Decimal("0.10"))
        self.assertEqual(params.max_positions, 5)
        self.assertFalse(params.leverage_allowed)

    def test_get_risk_parameters_optimization(self) -> None:
        """Test getting risk parameters for Optimization phase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("75000"))
        params = manager.get_risk_parameters()

        self.assertIsInstance(params, PhaseRiskParameters)
        self.assertEqual(params.max_risk_per_trade_pct, Decimal("0.03"))
        self.assertEqual(params.max_portfolio_risk_pct, Decimal("0.15"))
        self.assertEqual(params.max_positions, 8)
        self.assertTrue(params.leverage_allowed)

    def test_can_increase_position_size_within_limits(self) -> None:
        """Test position size validation within limits."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
        can, reason = manager.can_increase_position_size(
            current_risk_pct=Decimal("0.02"),
            proposed_risk_pct=Decimal("0.01"),
        )

        # Survival: max 1% per trade, so 1% > 1% should fail
        # Actually 1% is exactly at the limit
        self.assertFalse(can)
        self.assertIn("exceeds max", reason)

    def test_can_increase_position_size_exceeds_per_trade_limit(self) -> None:
        """Test that position size exceeding per-trade limit is rejected."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
        can, reason = manager.can_increase_position_size(
            current_risk_pct=Decimal("0.01"),
            proposed_risk_pct=Decimal("0.02"),  # 2% > 1% max for Survival
        )

        self.assertFalse(can)
        self.assertIn("exceeds max", reason)
        self.assertIn("1.0%", reason)

    def test_can_increase_position_size_exceeds_portfolio_limit(self) -> None:
        """Test that position size exceeding portfolio limit is rejected."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))

        # Test within portfolio limit: 4% + 0.9% = 4.9% < 5%
        can, reason = manager.can_increase_position_size(
            current_risk_pct=Decimal("0.04"),  # Already at 4%
            proposed_risk_pct=Decimal("0.009"),  # 0.9% < 1% max, and 4.9% < 5%
        )
        # Should pass since 0.9% < 1% max per trade AND 4.9% < 5% max portfolio
        self.assertTrue(can)
        self.assertEqual(reason, "OK")

        # Test that would exceed portfolio: 4.5% + 0.6% = 5.1% > 5%
        can, reason = manager.can_increase_position_size(
            current_risk_pct=Decimal("0.045"),  # Already at 4.5%
            proposed_risk_pct=Decimal("0.006"),  # Would make 5.1% total > 5%
        )
        self.assertFalse(can)
        self.assertIn("would exceed", reason)
        self.assertIn("5.0%", reason)

    def test_can_increase_position_size_valid(self) -> None:
        """Test valid position size increase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
        can, reason = manager.can_increase_position_size(
            current_risk_pct=Decimal("0.02"),
            proposed_risk_pct=Decimal("0.005"),  # 0.5% < 1% max
        )

        self.assertTrue(can)
        self.assertEqual(reason, "OK")

    def test_get_phase_summary_survival(self) -> None:
        """Test phase summary for Survival phase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
        summary = manager.get_phase_summary()

        self.assertEqual(summary["current_phase"], "survival")
        self.assertIn("€1,000 - €10,000", summary["capital_range"])
        self.assertIn("€5,000", summary["current_capital"])
        self.assertEqual(summary["max_risk_per_trade"], "1.0%")
        self.assertEqual(summary["max_portfolio_risk"], "5.0%")
        self.assertEqual(summary["max_positions"], 3)
        self.assertFalse(summary["leverage_allowed"])
        self.assertEqual(summary["position_sizing"], "kelly_half")

    def test_get_phase_summary_growth(self) -> None:
        """Test phase summary for Growth phase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("25000"))
        summary = manager.get_phase_summary()

        self.assertEqual(summary["current_phase"], "growth")
        self.assertIn("€10,000 - €50,000", summary["capital_range"])
        self.assertEqual(summary["max_risk_per_trade"], "2.0%")
        self.assertEqual(summary["max_portfolio_risk"], "10.0%")
        self.assertEqual(summary["max_positions"], 5)

    def test_get_phase_summary_optimization(self) -> None:
        """Test phase summary for Optimization phase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("75000"))
        summary = manager.get_phase_summary()

        self.assertEqual(summary["current_phase"], "optimization")
        self.assertEqual(summary["max_risk_per_trade"], "3.0%")
        self.assertEqual(summary["max_portfolio_risk"], "15.0%")
        self.assertEqual(summary["max_positions"], 8)
        self.assertTrue(summary["leverage_allowed"])

    def test_get_capital_progress_survival(self) -> None:
        """Test capital progress from Survival to Growth."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
        progress = manager.get_capital_progress()

        self.assertEqual(progress["current_phase"], "survival")
        self.assertEqual(progress["next_phase"], "growth")
        self.assertGreater(progress["progress_pct"], 0)
        self.assertLess(progress["progress_pct"], 100)
        self.assertGreater(progress["remaining"], 0)

    def test_get_capital_progress_growth(self) -> None:
        """Test capital progress from Growth to Optimization."""
        manager = CapitalPhaseManager(initial_capital=Decimal("25000"))
        progress = manager.get_capital_progress()

        self.assertEqual(progress["current_phase"], "growth")
        self.assertEqual(progress["next_phase"], "optimization")
        self.assertGreater(progress["progress_pct"], 0)
        self.assertLess(progress["progress_pct"], 100)

    def test_get_capital_progress_optimization(self) -> None:
        """Test capital progress at Optimization (final) phase."""
        manager = CapitalPhaseManager(initial_capital=Decimal("75000"))
        progress = manager.get_capital_progress()

        self.assertEqual(progress["current_phase"], "optimization")
        self.assertIsNone(progress["next_phase"])
        self.assertEqual(progress["progress_pct"], 100.0)
        self.assertEqual(progress["remaining"], Decimal("0"))

    def test_capital_phase_event_attributes(self) -> None:
        """Test CapitalPhaseEvent dataclass attributes."""
        event = CapitalPhaseEvent(
            timestamp=datetime.utcnow(),
            old_phase=CapitalPhase.SURVIVAL,
            new_phase=CapitalPhase.GROWTH,
            capital_at_transition=Decimal("10000"),
        )

        self.assertIsInstance(event.timestamp, datetime)
        self.assertEqual(event.old_phase, CapitalPhase.SURVIVAL)
        self.assertEqual(event.new_phase, CapitalPhase.GROWTH)
        self.assertEqual(event.capital_at_transition, Decimal("10000"))


class TestR25R26R27Compliance(unittest.TestCase):
    """Test compliance with R25, R26, R27 trading rules."""

    def test_r25_survival_no_leverage(self) -> None:
        """Test R25: Survival phase does not allow leverage."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
        params = manager.get_risk_parameters()
        self.assertFalse(params.leverage_allowed)

    def test_r25_survival_max_1_percent_risk(self) -> None:
        """Test R25: Survival phase max 1% risk per trade."""
        manager = CapitalPhaseManager(initial_capital=Decimal("5000"))
        params = manager.get_risk_parameters()
        self.assertEqual(params.max_risk_per_trade_pct, Decimal("0.01"))

    def test_r26_growth_no_leverage(self) -> None:
        """Test R26: Growth phase does not allow leverage."""
        manager = CapitalPhaseManager(initial_capital=Decimal("25000"))
        params = manager.get_risk_parameters()
        self.assertFalse(params.leverage_allowed)

    def test_r26_growth_max_2_percent_risk(self) -> None:
        """Test R26: Growth phase max 2% risk per trade."""
        manager = CapitalPhaseManager(initial_capital=Decimal("25000"))
        params = manager.get_risk_parameters()
        self.assertEqual(params.max_risk_per_trade_pct, Decimal("0.02"))

    def test_r27_optimization_leverage_allowed(self) -> None:
        """Test R27: Optimization phase allows leverage."""
        manager = CapitalPhaseManager(initial_capital=Decimal("75000"))
        params = manager.get_risk_parameters()
        self.assertTrue(params.leverage_allowed)

    def test_r27_optimization_max_3_percent_risk(self) -> None:
        """Test R27: Optimization phase max 3% risk per trade."""
        manager = CapitalPhaseManager(initial_capital=Decimal("75000"))
        params = manager.get_risk_parameters()
        self.assertEqual(params.max_risk_per_trade_pct, Decimal("0.03"))


if __name__ == "__main__":
    unittest.main()
