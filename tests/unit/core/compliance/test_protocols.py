"""
Unit tests for protocols.py
===========================

Tests for compliance service protocol interfaces.
"""

import pytest
import pandas as pd
from decimal import Decimal
from typing import Any

from app.core.compliance.protocols import (
    ComplianceService,
    PreTradeCheckable,
    PostTradeCheckable,
    Optimizable,
    RegimeDetectable,
    AlphaGeneratable,
    RiskCalculable,
    LiquidityAnalyzable,
    ExecutionAlgorithm,
    TransactionCostModel,
)


class MockComplianceService:
    """Mock implementation of ComplianceService protocol."""
    
    def is_available(self) -> bool:
        return True
    
    def get_service_name(self) -> str:
        return "mock_service"
    
    def initialize(self) -> None:
        pass


class MockPreTradeService:
    """Mock implementation of PreTradeCheckable protocol."""
    
    def is_available(self) -> bool:
        return True
    
    def get_service_name(self) -> str:
        return "mock_pre_trade"
    
    def initialize(self) -> None:
        pass
    
    def check_pre_trade(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        current_price: Decimal,
        price_history: Any = None,
        **kwargs: Any,
    ) -> dict:
        return {
            "can_execute": True,
            "confidence": 0.9,
            "reasons": [],
            "risk_factors": {},
        }


class MockPostTradeService:
    """Mock implementation of PostTradeCheckable protocol."""
    
    def is_available(self) -> bool:
        return True
    
    def get_service_name(self) -> str:
        return "mock_post_trade"
    
    def initialize(self) -> None:
        pass
    
    def check_post_trade(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        execution_price: Decimal,
        **kwargs: Any,
    ) -> dict:
        return {
            "implementation_shortfall_bps": 5.0,
            "market_impact_bps": 3.0,
            "execution_quality_score": 85.0,
        }


class TestComplianceService:
    """Tests for ComplianceService protocol."""

    def test_protocol_compliance(self):
        """Test that mock service implements protocol."""
        service = MockComplianceService()
        assert isinstance(service, ComplianceService)
        assert service.is_available() is True
        assert service.get_service_name() == "mock_service"
        service.initialize()  # Should not raise


class TestPreTradeCheckable:
    """Tests for PreTradeCheckable protocol."""

    def test_protocol_compliance(self):
        """Test that mock service implements protocol."""
        service = MockPreTradeService()
        assert isinstance(service, PreTradeCheckable)
        assert isinstance(service, ComplianceService)
        
        result = service.check_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
        )
        assert result["can_execute"] is True
        assert result["confidence"] == 0.9

    def test_check_pre_trade_with_price_history(self, sample_price_history):
        """Test check_pre_trade with price history."""
        service = MockPreTradeService()
        result = service.check_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
            price_history=sample_price_history,
        )
        assert "can_execute" in result

    def test_check_pre_trade_with_kwargs(self):
        """Test check_pre_trade with additional kwargs."""
        service = MockPreTradeService()
        result = service.check_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
            urgency=0.5,
            order_book=None,
        )
        assert "can_execute" in result


class TestPostTradeCheckable:
    """Tests for PostTradeCheckable protocol."""

    def test_protocol_compliance(self):
        """Test that mock service implements protocol."""
        service = MockPostTradeService()
        assert isinstance(service, PostTradeCheckable)
        assert isinstance(service, ComplianceService)
        
        result = service.check_post_trade(
            order_id="order-1",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.00"),
        )
        assert result["implementation_shortfall_bps"] == 5.0
        assert result["execution_quality_score"] == 85.0


class TestProtocolExtensionPoints:
    """Tests for protocol extension points via **kwargs."""

    def test_kwargs_extension_point(self):
        """Test that **kwargs allows extension."""
        service = MockPreTradeService()
        # Should accept any keyword arguments
        result = service.check_pre_trade(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            current_price=Decimal("150.00"),
            custom_param="custom_value",
            another_param=123,
        )
        assert "can_execute" in result


@pytest.fixture
def sample_price_history():
    """Create sample price history DataFrame."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    return pd.DataFrame({
        "close": [100 + i * 0.1 for i in range(100)],
        "volume": [1000000 for _ in range(100)],
    }, index=dates)
