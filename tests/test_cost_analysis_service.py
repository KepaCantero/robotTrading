"""
Tests for Cost Analysis Service.

This module contains comprehensive tests for the cost analysis functionality
including cost calculation, profitability validation, and Cost Impact Ratio (CIR) analysis.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from app.backtesting.models import Trade, TradeStatus
from app.models.order import OrderSide, OrderType
from app.services.cost_analysis_service import (CostAnalysisResult,
                                                CostAnalysisService,
                                                CostBreakdown, CostType)


class TestCostAnalysisService:
    """Test cases for CostAnalysisService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = CostAnalysisService()
        self.base_time = datetime.utcnow()

        # Sample trade data
        self.sample_trade = Trade(
            trade_id="test_trade_1",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("150.00"),
            exit_price=Decimal("155.00"),
            entry_time=self.base_time,
            exit_time=self.base_time + timedelta(hours=1),
            pnl=Decimal("500.00"),  # 100 * (155 - 150)
            status=TradeStatus.CLOSED,
            commission=Decimal("0.75"),  # 0.5% of 15000
            slippage=Decimal("0.15"),
        )
        self.sample_market_data = {
            "AAPL": {
                "volatility": 0.02,
                "avg_volume": Decimal("1000000"),
                "bid": Decimal("149.95"),
                "ask": Decimal("150.05"),
                "spread": Decimal("0.10"),
            }
        }

    def test_analyze_trade_costs_market_order(self):
        """Test cost analysis for market order."""
        breakdown = self.service.analyze_trade_costs(self.sample_trade, self.sample_market_data)

        assert breakdown.trade_id == "test_trade_1"
        assert breakdown.symbol == "AAPL"
        assert breakdown.commission > Decimal("0")
        assert breakdown.slippage > Decimal("0")
        assert breakdown.infrastructure_cost == Decimal("0.50")
        assert breakdown.borrowing_cost == Decimal("0")  # BUY order
        assert breakdown.total_cost > Decimal("0")
        assert breakdown.cost_percentage > Decimal("0")

    def test_analyze_trade_costs_limit_order(self):
        """Test cost analysis for limit order."""
        limit_trade = Trade(
            trade_id="test_trade_2",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("150.00"),
            exit_price=Decimal("155.00"),
            entry_time=self.base_time,
            exit_time=self.base_time + timedelta(hours=1),
            pnl=Decimal("500.00"),
            status=TradeStatus.CLOSED,
            commission=Decimal("0.75"),
            slippage=Decimal("0.00"),  # Limit orders have no slippage
        )
        breakdown = self.service.analyze_trade_costs(limit_trade, self.sample_market_data)

        # Still calculates slippage based on market conditions
        assert breakdown.slippage > Decimal("0")
        assert breakdown.commission > Decimal("0")
        assert breakdown.total_cost > Decimal("0")

    def test_analyze_trade_costs_short_position(self):
        """Test cost analysis for short position with borrowing costs."""
        short_trade = Trade(
            trade_id="test_trade_3",
            symbol="AAPL",
            side="sell",
            quantity=Decimal("100"),
            entry_price=Decimal("150.00"),
            exit_price=Decimal("145.00"),
            entry_time=self.base_time,
            exit_time=self.base_time + timedelta(days=5),
            pnl=Decimal("500.00"),  # Short profit
            status=TradeStatus.CLOSED,
            commission=Decimal("0.75"),
            slippage=Decimal("0.15"),
        )
        breakdown = self.service.analyze_trade_costs(short_trade, self.sample_market_data)

        assert breakdown.borrowing_cost > Decimal("0")  # Short position has borrowing cost
        assert breakdown.total_cost > Decimal("0")

    def test_analyze_strategy_costs_profitable(self):
        """Test cost analysis for profitable strategy."""
        trades = [self.sample_trade]

        result = self.service.analyze_strategy_costs(
            trades, "Test Strategy", self.sample_market_data
        )

        assert result.strategy_name == "Test Strategy"
        assert result.total_trades == 1
        assert result.total_costs > Decimal("0")
        assert result.gross_profit == Decimal("500.00")
        # Net profit should be less due to costs
        assert result.net_profit < result.gross_profit
        assert result.cost_impact_ratio > Decimal("0")
        assert len(result.cost_breakdowns) == 1
        assert len(result.recommendations) >= 0

    def test_analyze_strategy_costs_unprofitable(self):
        """Test cost analysis for unprofitable strategy."""
        unprofitable_trade = Trade(
            trade_id="test_trade_4",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("150.00"),
            exit_price=Decimal("149.00"),  # Loss
            entry_time=self.base_time,
            exit_time=self.base_time + timedelta(hours=1),
            pnl=Decimal("-100.00"),  # Loss
            status=TradeStatus.CLOSED,
            commission=Decimal("0.75"),
            slippage=Decimal("0.15"),
        )
        trades = [unprofitable_trade]
        result = self.service.analyze_strategy_costs(
            trades, "Unprofitable Strategy", self.sample_market_data
        )

        assert result.gross_profit == Decimal("-100.00")
        assert result.net_profit < result.gross_profit  # Even more loss due to costs
        assert not result.is_profitable

    def test_analyze_strategy_costs_empty_trades(self):
        """Test cost analysis with empty trades list."""
        result = self.service.analyze_strategy_costs([], "Empty Strategy", self.sample_market_data)

        assert result.strategy_name == "Empty Strategy"
        assert result.total_trades == 0
        assert result.total_costs == Decimal("0")
        assert not result.is_profitable
        assert "No trades to analyze" in result.recommendations[0]

    def test_validate_profitability_profitable(self):
        """Test profitability validation for profitable strategy."""
        profitable_result = CostAnalysisResult(
            strategy_name="Profitable Strategy",
            analysis_period=(self.base_time, self.base_time + timedelta(days=1)),
            total_trades=10,
            total_commission=Decimal("50.00"),
            total_slippage=Decimal("25.00"),
            total_market_impact=Decimal("10.00"),
            total_infrastructure=Decimal("5.00"),
            total_borrowing=Decimal("0.00"),
            total_costs=Decimal("90.00"),
            gross_profit=Decimal("1000.00"),
            net_profit=Decimal("910.00"),
            cost_impact_ratio=Decimal("9.0"),  # 9% CIR
            profitability_threshold=Decimal("2.0"),
            cost_breakdowns=[],
            is_profitable=True,
            exceeds_cost_threshold=False,
            recommendations=[],
        )
        assert self.service.validate_profitability(profitable_result) is True

    def test_validate_profitability_unprofitable(self):
        """Test profitability validation for unprofitable strategy."""
        unprofitable_result = CostAnalysisResult(
            strategy_name="Unprofitable Strategy",
            analysis_period=(self.base_time, self.base_time + timedelta(days=1)),
            total_trades=10,
            total_commission=Decimal("50.00"),
            total_slippage=Decimal("25.00"),
            total_market_impact=Decimal("10.00"),
            total_infrastructure=Decimal("5.00"),
            total_borrowing=Decimal("0.00"),
            total_costs=Decimal("90.00"),
            gross_profit=Decimal("50.00"),  # Less than costs
            net_profit=Decimal("-40.00"),
            cost_impact_ratio=Decimal("180.0"),  # 180% CIR
            profitability_threshold=Decimal("2.0"),
            cost_breakdowns=[],
            is_profitable=False,
            exceeds_cost_threshold=True,
            recommendations=[],
        )
        assert self.service.validate_profitability(unprofitable_result) is False

    def test_cost_impact_ratio_calculation(self):
        """Test Cost Impact Ratio (CIR) calculation."""
        trades = [self.sample_trade]
        result = self.service.analyze_strategy_costs(trades, "CIR Test", self.sample_market_data)

        # CIR should be (total_costs / gross_profit) * 100
        expected_cir = (result.total_costs / result.gross_profit) * 100
        assert abs(result.cost_impact_ratio - expected_cir) < Decimal("0.01")

    def test_asset_class_detection(self):
        """Test asset class detection from symbols."""
        assert self.service._determine_asset_class("AAPL") == "equity"
        assert self.service._determine_asset_class("BTCUSDT") == "crypto"
        assert self.service._determine_asset_class("EURUSD") == "forex"
        assert self.service._determine_asset_class("ETHBTC") == "crypto"

    def test_commission_calculation_by_asset_class(self):
        """Test commission calculation for different asset classes."""
        equity_trade = Trade(
            trade_id="equity_trade",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),
            entry_price=Decimal("150.00"),
            exit_price=Decimal("155.00"),
            entry_time=self.base_time,
            exit_time=self.base_time + timedelta(hours=1),
            pnl=Decimal("500.00"),
            status=TradeStatus.CLOSED,
            commission=Decimal("0.75"),
            slippage=Decimal("0.15"),
        )
        crypto_trade = Trade(
            trade_id="crypto_trade",
            symbol="BTCUSDT",
            side="buy",
            quantity=Decimal("0.1"),
            entry_price=Decimal("50000.00"),
            exit_price=Decimal("51000.00"),
            entry_time=self.base_time,
            exit_time=self.base_time + timedelta(hours=1),
            pnl=Decimal("100.00"),
            status=TradeStatus.CLOSED,
            commission=Decimal("5.00"),
            slippage=Decimal("25.00"),
        )
        equity_breakdown = self.service.analyze_trade_costs(equity_trade, self.sample_market_data)
        crypto_breakdown = self.service.analyze_trade_costs(crypto_trade, self.sample_market_data)

        # Crypto should have lower commission rate
        assert crypto_breakdown.commission < equity_breakdown.commission

    def test_slippage_calculation_with_volatility(self):
        """Test slippage calculation with market volatility."""
        high_vol_market_data = {
            "AAPL": {
                "volatility": 0.05,  # High volatility
                "avg_volume": Decimal("1000000"),
                "bid": Decimal("149.95"),
                "ask": Decimal("150.05"),
                "spread": Decimal("0.10"),
            }
        }

        low_vol_market_data = {
            "AAPL": {
                "volatility": 0.01,  # Low volatility
                "avg_volume": Decimal("1000000"),
                "bid": Decimal("149.95"),
                "ask": Decimal("150.05"),
                "spread": Decimal("0.10"),
            }
        }

        high_vol_breakdown = self.service.analyze_trade_costs(
            self.sample_trade, high_vol_market_data
        )
        low_vol_breakdown = self.service.analyze_trade_costs(self.sample_trade, low_vol_market_data)

        # High volatility should result in higher slippage
        assert high_vol_breakdown.slippage > low_vol_breakdown.slippage

    def test_market_impact_calculation(self):
        """Test market impact calculation based on order size."""
        large_order_trade = Trade(
            trade_id="large_order",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("10000"),  # Large order
            entry_price=Decimal("150.00"),
            exit_price=Decimal("155.00"),
            entry_time=self.base_time,
            exit_time=self.base_time + timedelta(hours=1),
            pnl=Decimal("50000.00"),
            status=TradeStatus.CLOSED,
            commission=Decimal("75.00"),
            slippage=Decimal("150.00"),
        )
        small_order_trade = Trade(
            trade_id="small_order",
            symbol="AAPL",
            side="buy",
            quantity=Decimal("100"),  # Small order
            entry_price=Decimal("150.00"),
            exit_price=Decimal("155.00"),
            entry_time=self.base_time,
            exit_time=self.base_time + timedelta(hours=1),
            pnl=Decimal("500.00"),
            status=TradeStatus.CLOSED,
            commission=Decimal("0.75"),
            slippage=Decimal("1.50"),
        )
        large_breakdown = self.service.analyze_trade_costs(
            large_order_trade, self.sample_market_data
        )
        small_breakdown = self.service.analyze_trade_costs(
            small_order_trade, self.sample_market_data
        )

        # Large order should have higher market impact
        assert large_breakdown.market_impact > small_breakdown.market_impact

    def test_recommendations_generation(self):
        """Test recommendations generation based on cost analysis."""
        # Create trades with high costs
        high_cost_trades = []
        for i in range(5):
            trade = Trade(
                trade_id=f"high_cost_trade_{i}",
                symbol="AAPL",
                side="buy",
                quantity=Decimal("100"),
                entry_price=Decimal("150.00"),
                exit_price=Decimal("149.00"),  # Loss
                entry_time=self.base_time,
                exit_time=self.base_time + timedelta(hours=1),
                pnl=Decimal("-100.00"),
                status=TradeStatus.CLOSED,
                commission=Decimal("0.75"),
                slippage=Decimal("0.15"),
            )
            high_cost_trades.append(trade)

        result = self.service.analyze_strategy_costs(
            high_cost_trades, "High Cost Strategy", self.sample_market_data
        )

        assert len(result.recommendations) > 0
        assert any("not profitable" in rec.lower() for rec in result.recommendations)

    def test_error_handling_invalid_trade(self):
        """Test error handling with invalid trade data."""
        # Create a trade with minimal valid values to test error handling
        invalid_trade = Trade(
            trade_id="invalid_trade",
            symbol="INVALID",
            side="buy",
            quantity=Decimal("1"),  # Minimum valid quantity
            entry_price=Decimal("0.01"),  # Minimum valid price
            exit_price=Decimal("0.01"),
            entry_time=self.base_time,
            exit_time=self.base_time + timedelta(hours=1),
            pnl=Decimal("0"),
            status=TradeStatus.CLOSED,
            commission=Decimal("0"),
            slippage=Decimal("0"),
        )
        # Should not raise exception, should calculate costs normally
        breakdown = self.service.analyze_trade_costs(invalid_trade, {})

        # Even with invalid symbol, it should calculate costs (infrastructure
        # cost is always applied)
        # Infrastructure cost is always applied
        assert breakdown.total_cost > Decimal("0")
        assert breakdown.infrastructure_cost == Decimal("0.50")  # Fixed infrastructure cost
        assert breakdown.cost_percentage > Decimal("0")  # Should calculate percentage
        assert breakdown.cost_impact_ratio == Decimal("0")  # No profit, so CIR is 0

    def test_cost_breakdown_serialization(self):
        """Test that cost breakdown can be serialized."""
        breakdown = self.service.analyze_trade_costs(self.sample_trade, self.sample_market_data)

        # Test that all fields are present and have correct types
        assert isinstance(breakdown.trade_id, str)
        assert isinstance(breakdown.symbol, str)
        assert isinstance(breakdown.commission, Decimal)
        assert isinstance(breakdown.slippage, Decimal)
        assert isinstance(breakdown.total_cost, Decimal)
        assert isinstance(breakdown.cost_percentage, Decimal)
        assert isinstance(breakdown.cost_impact_ratio, Decimal)
        assert isinstance(breakdown.timestamp, datetime)

    def test_cost_analysis_result_serialization(self):
        """Test that cost analysis result can be serialized."""
        trades = [self.sample_trade]
        result = self.service.analyze_strategy_costs(
            trades, "Test Strategy", self.sample_market_data
        )

        # Test that all fields are present and have correct types
        assert isinstance(result.strategy_name, str)
        assert isinstance(result.total_trades, int)
        assert isinstance(result.total_costs, Decimal)
        assert isinstance(result.gross_profit, Decimal)
        assert isinstance(result.net_profit, Decimal)
        assert isinstance(result.cost_impact_ratio, Decimal)
        assert isinstance(result.is_profitable, bool)
        assert isinstance(result.recommendations, list)
        assert isinstance(result.cost_breakdowns, list)
