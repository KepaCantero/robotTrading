#!/usr/bin/env python3
"""
Test script to verify the new risk validation logic in compliance_engine.py

This script tests that:
1. Position limits are enforced (10% of portfolio)
2. Drawdown limits are enforced (25% max)
3. Leverage ratios are enforced (2.0x max)
4. Data quality checks work (NaN detection, staleness)
5. Trades are blocked when limits are exceeded
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.compliance_engine import ComplianceEngine, PreTradeAnalysis


class MockRiskEngine:
    """Mock risk engine for testing."""

    def __init__(self, portfolio_value=100000, peak_value=100000, gross_exposure=50000, capital=50000):
        self._portfolio_value = portfolio_value
        self._peak_value = peak_value
        self._gross_exposure = gross_exposure
        self._capital = capital
        self._positions = {}

    def get_current_positions(self):
        return self._positions

    def get_portfolio_value(self):
        return self._portfolio_value

    def get_peak_portfolio_value(self):
        return self._peak_value

    def get_gross_exposure(self):
        return self._gross_exposure

    def get_capital(self):
        return self._capital


def create_test_price_history(days=30, include_nan=False, stale_days=0):
    """Create test price history data."""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    prices = np.random.randn(days).cumsum() + 100

    df = pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'volume': np.random.randint(100000, 1000000, days)
    })

    # Add NaN values if requested
    if include_nan:
        df.loc[df.index[5], 'close'] = np.nan

    # Make data stale if requested
    if stale_days > 0:
        df['timestamp'] = df['timestamp'] - timedelta(days=stale_days)

    return df


def test_position_limit():
    """Test that position limits are enforced."""
    print("\n" + "="*80)
    print("TEST 1: Position Limit Check (10% of portfolio)")
    print("="*80)

    engine = ComplianceEngine(enable_logging=False)
    system_bus = engine._system_bus

    # Test case 1: Position within limit (5% of portfolio)
    print("\nTest 1a: Position within limit (5%)")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine(portfolio_value=100000)

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("10"),
        price=Decimal("500"),  # $5000 = 5% of $100k
        price_history=create_test_price_history(),
        urgency=0.5,
        signal_time=None
    )

    print(f"  Position ratio: 5.0%")
    print(f"  Position limit OK: {result.position_limit_ok}")
    print(f"  Can execute: {result.can_execute}")
    assert result.position_limit_ok == True, "Should allow position within limit"
    assert result.can_execute == True, "Should allow trade"
    print("  ✓ PASSED")

    # Test case 2: Position exceeds limit (15% of portfolio)
    print("\nTest 1b: Position exceeds limit (15%)")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine(portfolio_value=100000)

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("30"),
        price=Decimal("500"),  # $15000 = 15% of $100k
        price_history=create_test_price_history(),
        urgency=0.5,
        signal_time=None
    )

    print(f"  Position ratio: 15.0%")
    print(f"  Position limit OK: {result.position_limit_ok}")
    print(f"  Can execute: {result.can_execute}")
    print(f"  Reasons: {result.reasons}")
    assert result.position_limit_ok == False, "Should block position over 10%"
    assert result.can_execute == False, "Should block trade"
    assert any("Position limit exceeded" in r for r in result.reasons), "Should have reason"
    print("  ✓ PASSED")


def test_drawdown_limit():
    """Test that drawdown limits are enforced."""
    print("\n" + "="*80)
    print("TEST 2: Drawdown Limit Check (25% max)")
    print("="*80)

    engine = ComplianceEngine(enable_logging=False)
    system_bus = engine._system_bus

    # Test case 1: Drawdown within limit (20%)
    print("\nTest 2a: Drawdown within limit (20%)")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine(portfolio_value=80000, peak_value=100000)  # 20% drawdown

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("10"),
        price=Decimal("500"),
        price_history=create_test_price_history(),
        urgency=0.5,
        signal_time=None
    )

    print(f"  Current drawdown: 20.0%")
    print(f"  Drawdown limit OK: {result.drawdown_limit_ok}")
    print(f"  Can execute: {result.can_execute}")
    assert result.drawdown_limit_ok == True, "Should allow drawdown under 25%"
    assert result.can_execute == True, "Should allow trade"
    print("  ✓ PASSED")

    # Test case 2: Drawdown exceeds limit (30%)
    print("\nTest 2b: Drawdown exceeds limit (30%)")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine(portfolio_value=70000, peak_value=100000)  # 30% drawdown

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("10"),
        price=Decimal("500"),
        price_history=create_test_price_history(),
        urgency=0.5,
        signal_time=None
    )

    print(f"  Current drawdown: 30.0%")
    print(f"  Drawdown limit OK: {result.drawdown_limit_ok}")
    print(f"  Can execute: {result.can_execute}")
    print(f"  Reasons: {result.reasons}")
    assert result.drawdown_limit_ok == False, "Should block drawdown over 25%"
    assert result.can_execute == False, "Should block trade"
    assert any("Drawdown limit exceeded" in r for r in result.reasons), "Should have reason"
    print("  ✓ PASSED")


def test_leverage_ratio():
    """Test that leverage ratios are enforced."""
    print("\n" + "="*80)
    print("TEST 3: Leverage Ratio Check (2.0x max)")
    print("="*80)

    engine = ComplianceEngine(enable_logging=False)
    system_bus = engine._system_bus

    # Test case 1: Leverage within limit (1.5x)
    print("\nTest 3a: Leverage within limit (1.5x)")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine(gross_exposure=75000, capital=50000)  # 1.5x leverage

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("10"),
        price=Decimal("500"),
        price_history=create_test_price_history(),
        urgency=0.5,
        signal_time=None
    )

    print(f"  Leverage ratio: 1.5x")
    print(f"  Can execute: {result.can_execute}")
    print(f"  Leverage stored: {result.leverage_ratio}")
    assert result.leverage_ratio == 1.5, "Should calculate leverage correctly"
    assert result.can_execute == True, "Should allow trade"
    print("  ✓ PASSED")

    # Test case 2: Leverage exceeds limit (2.5x)
    print("\nTest 3b: Leverage exceeds limit (2.5x)")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine(gross_exposure=125000, capital=50000)  # 2.5x leverage

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("10"),
        price=Decimal("500"),
        price_history=create_test_price_history(),
        urgency=0.5,
        signal_time=None
    )

    print(f"  Leverage ratio: 2.5x")
    print(f"  Can execute: {result.can_execute}")
    print(f"  Leverage stored: {result.leverage_ratio}")
    print(f"  Reasons: {result.reasons}")
    assert result.leverage_ratio == 2.5, "Should calculate leverage correctly"
    assert result.can_execute == False, "Should block trade"
    assert any("Leverage too high" in r for r in result.reasons), "Should have reason"
    print("  ✓ PASSED")


def test_data_quality():
    """Test that data quality checks work."""
    print("\n" + "="*80)
    print("TEST 4: Data Quality Check")
    print("="*80)

    engine = ComplianceEngine(enable_logging=False)
    system_bus = engine._system_bus

    # Test case 1: Good quality data
    print("\nTest 4a: Good quality data")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine()

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("10"),
        price=Decimal("500"),
        price_history=create_test_price_history(),
        urgency=0.5,
        signal_time=None
    )

    print(f"  Data quality score: {result.data_quality_score:.0f}%")
    print(f"  Can execute: {result.can_execute}")
    assert result.data_quality_score >= 80, "Should have good data quality"
    assert result.can_execute == True, "Should allow trade with good data"
    print("  ✓ PASSED")

    # Test case 2: Data with NaN values
    print("\nTest 4b: Data with NaN values")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine()

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("10"),
        price=Decimal("500"),
        price_history=create_test_price_history(include_nan=True),
        urgency=0.5,
        signal_time=None
    )

    print(f"  Data quality score: {result.data_quality_score:.0f}%")
    print(f"  Can execute: {result.can_execute}")
    print(f"  Reasons: {result.reasons}")
    assert result.data_quality_score < 100, "Should penalize NaN values"
    assert any("NaN" in r for r in result.reasons), "Should mention NaN in reasons"
    print("  ✓ PASSED")

    # Test case 3: Stale data (2 days old)
    print("\nTest 4c: Stale data (2 days old)")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine()

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("10"),
        price=Decimal("500"),
        price_history=create_test_price_history(stale_days=2),
        urgency=0.5,
        signal_time=None
    )

    print(f"  Data quality score: {result.data_quality_score:.0f}%")
    print(f"  Can execute: {result.can_execute}")
    print(f"  Reasons: {result.reasons}")
    assert result.data_quality_score < 100, "Should penalize stale data"
    assert any("stale" in r.lower() for r in result.reasons), "Should mention stale data"
    print("  ✓ PASSED")

    # Test case 4: No price history
    print("\nTest 4d: No price history provided")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine()

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("10"),
        price=Decimal("500"),
        price_history=None,
        urgency=0.5,
        signal_time=None
    )

    print(f"  Data quality score: {result.data_quality_score:.0f}%")
    print(f"  Can execute: {result.can_execute}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Reasons: {result.reasons}")
    assert result.data_quality_score == 0, "Should have 0% quality without data"
    assert result.can_execute == False, "Should block trade without data"
    assert result.confidence == 0, "Should have 0 confidence without data"
    print("  ✓ PASSED")


def test_combined_violations():
    """Test multiple violations at once."""
    print("\n" + "="*80)
    print("TEST 5: Combined Violations")
    print("="*80)

    engine = ComplianceEngine(enable_logging=False)
    system_bus = engine._system_bus

    # Multiple violations: position too large, high drawdown, high leverage
    print("\nTest 5a: Multiple violations simultaneously")
    result = PreTradeAnalysis(can_execute=True, confidence=1.0)
    mock_risk = MockRiskEngine(
        portfolio_value=50000,      # Small portfolio
        peak_value=100000,          # 50% drawdown
        gross_exposure=150000,      # 3x leverage
        capital=50000
    )

    system_bus._handle_risk_engine(
        subsystem=mock_risk,
        result=result,
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("100"),    # $50000 = 100% of portfolio
        price=Decimal("500"),
        price_history=create_test_price_history(),
        urgency=0.5,
        signal_time=None
    )

    print(f"  Can execute: {result.can_execute}")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Position limit OK: {result.position_limit_ok}")
    print(f"  Drawdown limit OK: {result.drawdown_limit_ok}")
    print(f"  Leverage ratio: {result.leverage_ratio:.2f}x")
    print(f"  Number of reasons: {len(result.reasons)}")
    for i, reason in enumerate(result.reasons, 1):
        print(f"    {i}. {reason}")

    assert result.can_execute == False, "Should block trade with violations"
    assert result.position_limit_ok == False, "Should catch position violation"
    assert result.drawdown_limit_ok == False, "Should catch drawdown violation"
    assert result.leverage_ratio > 2.0, "Should calculate high leverage"
    assert len(result.reasons) >= 3, "Should have multiple violation reasons"
    print("  ✓ PASSED")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("RISK VALIDATION TEST SUITE")
    print("Testing real validation logic in compliance_engine.py")
    print("="*80)

    try:
        test_position_limit()
        test_drawdown_limit()
        test_leverage_ratio()
        test_data_quality()
        test_combined_violations()

        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        print("\nSummary:")
        print("  - Position limits (10%): Working correctly")
        print("  - Drawdown limits (25%): Working correctly")
        print("  - Leverage limits (2.0x): Working correctly")
        print("  - Data quality checks: Working correctly")
        print("  - Trade blocking: Working correctly")
        print("\nThe compliance engine now has REAL validation logic!")
        print("="*80 + "\n")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
