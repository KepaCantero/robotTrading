"""
Tests for RiskScalingApplication (T8.1.3)

Tests end-to-end risk scaling orchestration.
"""

import pytest
import asyncio
from decimal import Decimal

from app.services.risk_scaling.risk_scaling_application import (
    RiskScalingApplication,
    get_risk_scaling_application,
)


class TestRiskScalingApplication:
    """Test suite for RiskScalingApplication."""

    @pytest.fixture
    def app(self):
        """Create application instance."""
        return RiskScalingApplication()

    @pytest.fixture
    def event_loop(self):
        """Create event loop for async tests."""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    # =========================================================================
    # TEST: Risk Scaling Application
    # =========================================================================

    @pytest.mark.asyncio
    async def test_apply_risk_scaling_healthy_scenario(self, app):
        """Test risk scaling in healthy scenario."""
        result = await app.apply_risk_scaling(
            base_position_size=Decimal("50000"),
            feasibility_ratio=Decimal("1.2"),
            capital=Decimal("250000"),
            capital_tier="medium",
            risk_tolerance=4,
            current_volatility=Decimal("1.0"),
            average_volatility=Decimal("1.0"),
            current_drawdown_pct=Decimal("0.03"),
            market_volatility_state="normal",
        )

        # Should maintain good position
        assert result["final_position_size"] >= Decimal("40000")
        assert result["leverage"] >= Decimal("1.0")
        assert result["is_halted"] is False

    @pytest.mark.asyncio
    async def test_apply_risk_scaling_stressed_scenario(self, app):
        """Test risk scaling in stressed scenario."""
        result = await app.apply_risk_scaling(
            base_position_size=Decimal("50000"),
            feasibility_ratio=Decimal("0.5"),
            capital=Decimal("250000"),
            capital_tier="medium",
            risk_tolerance=3,
            current_volatility=Decimal("2.0"),
            average_volatility=Decimal("1.0"),
            current_drawdown_pct=Decimal("0.15"),
            market_volatility_state="stressed",
        )

        # Should reduce position and leverage
        assert result["final_position_size"] <= Decimal("35000")
        assert result["leverage"] < Decimal("1.5")
        assert result["position_capped"] is True

    @pytest.mark.asyncio
    async def test_apply_risk_scaling_returns_all_fields(self, app):
        """Test risk scaling returns all required fields."""
        result = await app.apply_risk_scaling(
            base_position_size=Decimal("50000"),
            feasibility_ratio=Decimal("1.0"),
            capital=Decimal("250000"),
            capital_tier="large",
            risk_tolerance=5,
            current_volatility=Decimal("1.0"),
            average_volatility=Decimal("1.0"),
            current_drawdown_pct=Decimal("0.05"),
        )

        assert "base_position_size" in result
        assert "scaled_position_size" in result
        assert "final_position_size" in result
        assert "position_capped" in result
        assert "position_reason" in result
        assert "leverage" in result
        assert "leverage_reason" in result
        assert "limits" in result
        assert "capital_at_risk" in result
        assert "pct_capital_at_risk" in result
        assert "is_halted" in result

    @pytest.mark.asyncio
    async def test_apply_risk_scaling_halts_on_excessive_drawdown(self, app):
        """Test trading halts on excessive drawdown."""
        result = await app.apply_risk_scaling(
            base_position_size=Decimal("50000"),
            feasibility_ratio=Decimal("1.0"),
            capital=Decimal("250000"),
            capital_tier="medium",
            risk_tolerance=4,
            current_volatility=Decimal("1.0"),
            average_volatility=Decimal("1.0"),
            current_drawdown_pct=Decimal("0.25"),  # >20% drawdown
        )

        assert result["is_halted"] is True
        assert "Excessive drawdown" in result["halt_reason"]

    # =========================================================================
    # TEST: Order Validation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_validate_order_within_limits(self, app):
        """Test order validation when within limits."""
        limits = {
            "max_position_eur": Decimal("50000"),
            "max_leverage": Decimal("2.0"),
        }

        is_valid, msg = await app.validate_order_against_limits(
            order_size=Decimal("40000"),
            account_limits=limits,
            current_capital_deployed=Decimal("50000"),
            capital=Decimal("250000"),
        )

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_order_exceeds_position_limit(self, app):
        """Test order validation when exceeding position limit."""
        limits = {
            "max_position_eur": Decimal("30000"),
            "max_leverage": Decimal("2.0"),
        }

        is_valid, msg = await app.validate_order_against_limits(
            order_size=Decimal("40000"),  # Exceeds 30k limit
            account_limits=limits,
            current_capital_deployed=Decimal("50000"),
            capital=Decimal("250000"),
        )

        assert is_valid is False
        assert "exceeds limit" in msg.lower()

    @pytest.mark.asyncio
    async def test_validate_order_exceeds_leverage_limit(self, app):
        """Test order validation when exceeding leverage limit."""
        limits = {
            "max_position_eur": Decimal("200000"),
            "max_leverage": Decimal("1.5"),
        }

        is_valid, msg = await app.validate_order_against_limits(
            order_size=Decimal("100000"),  # Within position limit but creates 2x leverage (exceeds 1.5x)
            account_limits=limits,
            current_capital_deployed=Decimal("100000"),  # Already deployed 100k
            capital=Decimal("100000"),
        )

        assert is_valid is False
        # Should fail on leverage or position size check
        assert "leverage" in msg.lower() or "exceeds" in msg.lower()

    # =========================================================================
    # TEST: Risk Status
    # =========================================================================

    @pytest.mark.asyncio
    async def test_risk_status_healthy(self, app):
        """Test risk status in healthy state."""
        status = await app.get_risk_status(
            capital=Decimal("250000"),
            current_capital_deployed=Decimal("100000"),
            current_drawdown_pct=Decimal("0.02"),
            capital_tier="medium",
        )

        assert status["risk_state"] == "HEALTHY"
        assert status["can_trade"] is True
        assert status["should_halt"] is False

    @pytest.mark.asyncio
    async def test_risk_status_caution(self, app):
        """Test risk status in caution state."""
        status = await app.get_risk_status(
            capital=Decimal("250000"),
            current_capital_deployed=Decimal("100000"),
            current_drawdown_pct=Decimal("0.07"),  # 7% drawdown
            capital_tier="medium",
        )

        assert status["risk_state"] == "CAUTION"
        assert status["can_trade"] is True
        assert status["should_reduce_positions"] is False

    @pytest.mark.asyncio
    async def test_risk_status_critical(self, app):
        """Test risk status in critical state."""
        status = await app.get_risk_status(
            capital=Decimal("250000"),
            current_capital_deployed=Decimal("100000"),
            current_drawdown_pct=Decimal("0.18"),  # 18% drawdown
            capital_tier="medium",
        )

        assert status["risk_state"] == "CRITICAL"
        assert status["should_reduce_positions"] is True
        assert status["should_halt"] is False

    @pytest.mark.asyncio
    async def test_risk_status_halt(self, app):
        """Test risk status in halt state."""
        status = await app.get_risk_status(
            capital=Decimal("250000"),
            current_capital_deployed=Decimal("100000"),
            current_drawdown_pct=Decimal("0.22"),  # >20% drawdown
            capital_tier="medium",
        )

        assert status["risk_state"] == "HALT"
        assert status["should_halt"] is True
        assert status["can_trade"] is False

    @pytest.mark.asyncio
    async def test_risk_status_includes_all_fields(self, app):
        """Test risk status returns all fields."""
        status = await app.get_risk_status(
            capital=Decimal("250000"),
            current_capital_deployed=Decimal("100000"),
            current_drawdown_pct=Decimal("0.05"),
            capital_tier="medium",
        )

        assert "capital_total" in status
        assert "capital_deployed" in status
        assert "capital_available" in status
        assert "current_leverage" in status
        assert "current_drawdown_pct" in status
        assert "risk_state" in status
        assert "can_trade" in status
        assert "should_reduce_positions" in status
        assert "should_halt" in status

    # =========================================================================
    # TEST: Singleton
    # =========================================================================

    def test_singleton_pattern(self):
        """Test get_risk_scaling_application returns singleton."""
        app1 = get_risk_scaling_application()
        app2 = get_risk_scaling_application()

        assert app1 is app2, "Should return same instance"
