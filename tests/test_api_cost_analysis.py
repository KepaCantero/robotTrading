"""
Tests for Cost Analysis API endpoints.

This module contains tests for the cost analysis API endpoints
including trade cost analysis, strategy cost analysis, and profitability validation.
"""

import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.main import app
from app.services.cost_analysis_service import CostAnalysisService
from app.backtesting.models import TradeStatus


class TestCostAnalysisAPI:
    """Test cases for Cost Analysis API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)
        self.base_time = datetime.utcnow()
        
        # Sample trade data for API requests
        self.sample_trade_data = {
            "id": "test_trade_1",
            "symbol": "AAPL",
            "side": "buy",
            "order_type": "market",
            "quantity": 100,
            "entry_price": 150.00,
            "exit_price": 155.00,
            "entry_time": self.base_time.isoformat(),
            "exit_time": (self.base_time + timedelta(hours=1)).isoformat(),
            "pnl": 500.00,
            "status": "closed",
            "commission": 0.75,
            "metadata": {},
            "market_data": {
                "AAPL": {
                    "volatility": 0.02,
                    "avg_volume": 1000000,
                    "bid": 149.95,
                    "ask": 150.05,
                    "spread": 0.10
                }
            }
        }
        
        self.sample_strategy_data = {
            "strategy_name": "Test Strategy",
            "trades": [self.sample_trade_data],
            "market_data": {
                "AAPL": {
                    "volatility": 0.02,
                    "avg_volume": 1000000,
                    "bid": 149.95,
                    "ask": 150.05,
                    "spread": 0.10
                }
            }
        }
    
    def test_analyze_trade_costs_success(self):
        """Test successful trade cost analysis."""
        response = self.client.post("/cost-analysis/analyze-trade", json=self.sample_trade_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "trade_id" in data
        assert "symbol" in data
        assert "costs" in data
        assert "metrics" in data
        assert "timestamp" in data
        
        # Check cost structure
        costs = data["costs"]
        assert "commission" in costs
        assert "slippage" in costs
        assert "market_impact" in costs
        assert "infrastructure" in costs
        assert "borrowing" in costs
        assert "total" in costs
        
        # Check metrics structure
        metrics = data["metrics"]
        assert "cost_percentage" in metrics
        assert "cost_impact_ratio" in metrics
        
        # Verify values are reasonable
        assert costs["total"] > 0
        assert metrics["cost_percentage"] > 0
    
    def test_analyze_trade_costs_invalid_data(self):
        """Test trade cost analysis with invalid data."""
        invalid_data = {
            "id": "invalid_trade",
            "symbol": "INVALID",
            "side": "invalid_side",  # Invalid side
            "order_type": "market",
            "quantity": 100,
            "entry_price": 150.00,
            "entry_time": self.base_time.isoformat(),
            "pnl": 500.00,
            "status": "closed"
        }
        
        response = self.client.post("/cost-analysis/analyze-trade", json=invalid_data)
        
        assert response.status_code == 400
        assert "Error analyzing trade costs" in response.json()["detail"]
    
    def test_analyze_strategy_costs_success(self):
        """Test successful strategy cost analysis."""
        response = self.client.post("/cost-analysis/analyze-strategy", json=self.sample_strategy_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "strategy_name" in data
        assert "analysis_period" in data
        assert "summary" in data
        assert "cost_breakdown" in data
        assert "validation" in data
        assert "recommendations" in data
        assert "trade_breakdowns" in data
        
        # Check summary structure
        summary = data["summary"]
        assert "total_trades" in summary
        assert "total_costs" in summary
        assert "gross_profit" in summary
        assert "net_profit" in summary
        assert "cost_impact_ratio" in summary
        
        # Check cost breakdown structure
        cost_breakdown = data["cost_breakdown"]
        assert "commission" in cost_breakdown
        assert "slippage" in cost_breakdown
        assert "market_impact" in cost_breakdown
        assert "infrastructure" in cost_breakdown
        assert "borrowing" in cost_breakdown
        
        # Check validation structure
        validation = data["validation"]
        assert "is_profitable" in validation
        assert "exceeds_cost_threshold" in validation
        assert "is_valid" in validation
        
        # Verify values
        assert summary["total_trades"] == 1
        assert summary["total_costs"] > 0
        assert isinstance(data["recommendations"], list)
        assert len(data["trade_breakdowns"]) == 1
    
    def test_analyze_strategy_costs_empty_trades(self):
        """Test strategy cost analysis with empty trades."""
        empty_strategy_data = {
            "strategy_name": "Empty Strategy",
            "trades": [],
            "market_data": {}
        }
        
        response = self.client.post("/cost-analysis/analyze-strategy", json=empty_strategy_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["summary"]["total_trades"] == 0
        assert data["summary"]["total_costs"] == 0
        assert not data["validation"]["is_profitable"]
        assert "No trades to analyze" in data["recommendations"][0]
    
    def test_validate_profitability_success(self):
        """Test successful profitability validation."""
        profitability_data = {
            "strategy_name": "Test Strategy",
            "analysis_period": {
                "start": self.base_time.isoformat(),
                "end": (self.base_time + timedelta(days=1)).isoformat()
            },
            "total_trades": 10,
            "total_costs": 90.00,
            "gross_profit": 1000.00,
            "net_profit": 910.00,
            "cost_impact_ratio": 9.0,
            "is_profitable": True,
            "exceeds_cost_threshold": False,
            "recommendations": []
        }
        
        response = self.client.post("/cost-analysis/validate-profitability", json=profitability_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["strategy_name"] == "Test Strategy"
        assert data["is_profitable"] is True
        assert data["exceeds_cost_threshold"] is False
        assert data["is_valid"] is True
        assert data["cost_impact_ratio"] == 9.0
        assert data["max_allowed_cir"] == 0.3  # 30% as decimal
    
    def test_validate_profitability_unprofitable(self):
        """Test profitability validation for unprofitable strategy."""
        unprofitable_data = {
            "strategy_name": "Unprofitable Strategy",
            "analysis_period": {
                "start": self.base_time.isoformat(),
                "end": (self.base_time + timedelta(days=1)).isoformat()
            },
            "total_trades": 10,
            "total_costs": 90.00,
            "gross_profit": 50.00,  # Less than costs
            "net_profit": -40.00,
            "cost_impact_ratio": 180.0,  # High CIR
            "is_profitable": False,
            "exceeds_cost_threshold": True,
            "recommendations": ["Strategy is not profitable"]
        }
        
        response = self.client.post("/cost-analysis/validate-profitability", json=unprofitable_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["is_profitable"] is False
        assert data["exceeds_cost_threshold"] is True
        assert data["is_valid"] is False
        assert data["cost_impact_ratio"] == 180.0
    
    def test_get_cost_parameters(self):
        """Test getting cost parameters."""
        response = self.client.get("/cost-analysis/cost-parameters")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "commission_rates" in data
        assert "slippage_rates" in data
        assert "infrastructure_cost_per_trade" in data
        assert "borrowing_cost_rate" in data
        assert "profitability_thresholds" in data
        
        # Check commission rates
        commission_rates = data["commission_rates"]
        assert "equity" in commission_rates
        assert "crypto" in commission_rates
        assert "forex" in commission_rates
        
        # Check slippage rates
        slippage_rates = data["slippage_rates"]
        assert "equity" in slippage_rates
        assert "crypto" in slippage_rates
        assert "forex" in slippage_rates
        
        # Check profitability thresholds
        thresholds = data["profitability_thresholds"]
        assert "min_profitability_threshold" in thresholds
        assert "max_cost_impact_ratio" in thresholds
    
    def test_update_cost_parameters(self):
        """Test updating cost parameters."""
        new_parameters = {
            "commission_rates": {
                "equity": 0.006,  # 0.6%
                "crypto": 0.0015,  # 0.15%
                "forex": 0.0003  # 0.03%
            },
            "slippage_rates": {
                "equity": 0.0015,  # 0.15%
                "crypto": 0.0008,  # 0.08%
                "forex": 0.0002  # 0.02%
            },
            "infrastructure_cost_per_trade": 0.75,
            "borrowing_cost_rate": 0.06,  # 6%
            "profitability_thresholds": {
                "min_profitability_threshold": 0.025,  # 2.5%
                "max_cost_impact_ratio": 0.25  # 25%
            }
        }
        
        response = self.client.post("/cost-analysis/cost-parameters", json=new_parameters)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Cost parameters updated successfully"
        assert data["updated_parameters"] == new_parameters
    
    def test_update_cost_parameters_invalid(self):
        """Test updating cost parameters with invalid values."""
        invalid_parameters = {
            "commission_rates": {
                "equity": 0.15,  # Too high (15%)
                "crypto": 0.001,
                "forex": 0.0002
            }
        }
        
        response = self.client.post("/cost-analysis/cost-parameters", json=invalid_parameters)
        
        assert response.status_code == 400
        assert "Error updating cost parameters" in response.json()["detail"]
    
    def test_get_cost_breakdown_placeholder(self):
        """Test getting cost breakdown for specific trade (placeholder)."""
        response = self.client.get("/cost-analysis/cost-breakdown/test_trade_1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["trade_id"] == "test_trade_1"
        assert "message" in data
        assert "not yet implemented" in data["message"]
    
    def test_get_strategy_costs_placeholder(self):
        """Test getting strategy costs (placeholder)."""
        response = self.client.get("/cost-analysis/strategy-costs/Test Strategy")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["strategy_name"] == "Test Strategy"
        assert "message" in data
        assert "not yet implemented" in data["message"]
    
    def test_analyze_trade_costs_missing_fields(self):
        """Test trade cost analysis with missing required fields."""
        incomplete_data = {
            "id": "test_trade",
            "symbol": "AAPL",
            # Missing required fields
        }
        
        response = self.client.post("/cost-analysis/analyze-trade", json=incomplete_data)
        
        assert response.status_code == 400
        assert "Error analyzing trade costs" in response.json()["detail"]
    
    def test_analyze_strategy_costs_missing_fields(self):
        """Test strategy cost analysis with missing required fields."""
        incomplete_data = {
            "strategy_name": "Test Strategy",
            # Missing trades field
        }
        
        response = self.client.post("/cost-analysis/analyze-strategy", json=incomplete_data)
        
        assert response.status_code == 400
        assert "Error analyzing strategy costs" in response.json()["detail"]
    
    def test_validate_profitability_missing_fields(self):
        """Test profitability validation with missing required fields."""
        incomplete_data = {
            "strategy_name": "Test Strategy",
            # Missing required fields
        }
        
        response = self.client.post("/cost-analysis/validate-profitability", json=incomplete_data)
        
        assert response.status_code == 400
        assert "Error validating profitability" in response.json()["detail"]
    
    def test_cost_analysis_with_different_asset_classes(self):
        """Test cost analysis with different asset classes."""
        # Test equity trade
        equity_trade = self.sample_trade_data.copy()
        equity_trade["symbol"] = "AAPL"
        
        equity_response = self.client.post("/cost-analysis/analyze-trade", json=equity_trade)
        assert equity_response.status_code == 200
        
        # Test crypto trade
        crypto_trade = self.sample_trade_data.copy()
        crypto_trade["symbol"] = "BTCUSDT"
        crypto_trade["quantity"] = 0.1
        crypto_trade["entry_price"] = 50000.00
        crypto_trade["exit_price"] = 51000.00
        
        crypto_response = self.client.post("/cost-analysis/analyze-trade", json=crypto_trade)
        assert crypto_response.status_code == 200
        
        # Test forex trade
        forex_trade = self.sample_trade_data.copy()
        forex_trade["symbol"] = "EURUSD"
        forex_trade["quantity"] = 1000
        forex_trade["entry_price"] = 1.1000
        forex_trade["exit_price"] = 1.1100
        
        forex_response = self.client.post("/cost-analysis/analyze-trade", json=forex_trade)
        assert forex_response.status_code == 200
        
        # Compare costs - crypto should have lower commission rate
        equity_costs = equity_response.json()["costs"]
        crypto_costs = crypto_response.json()["costs"]
        
        # Crypto commission rate should be lower than equity
        assert crypto_costs["commission"] < equity_costs["commission"]
    
    def test_cost_analysis_with_short_position(self):
        """Test cost analysis with short position (borrowing costs)."""
        short_trade = self.sample_trade_data.copy()
        short_trade["side"] = "sell"
        short_trade["entry_price"] = 150.00
        short_trade["exit_price"] = 145.00
        short_trade["pnl"] = 500.00  # Short profit
        short_trade["entry_time"] = self.base_time.isoformat()
        short_trade["exit_time"] = (self.base_time + timedelta(days=5)).isoformat()
        
        response = self.client.post("/cost-analysis/analyze-trade", json=short_trade)
        
        assert response.status_code == 200
        data = response.json()
        
        # Short position should have borrowing costs
        assert data["costs"]["borrowing"] > 0
        assert data["costs"]["total"] > 0
