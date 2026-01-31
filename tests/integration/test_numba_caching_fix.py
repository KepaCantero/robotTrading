"""
Integration test to verify Numba caching fix is working.

This test verifies that the fix for "RuntimeError: cannot cache function 'func_name':
no locator available for file '<string>'" is properly configured in tests/conftest.py.

The fix works by setting NUMBA_CACHE_DIR environment variable before any imports
in conftest.py, which allows Numba JIT functions with cache=True to work correctly
during test execution.
"""

import os
import pytest
import numpy as np
from decimal import Decimal


class TestNumbaCachingFix:
    """Test suite to verify Numba caching configuration."""

    def test_numba_cache_dir_is_set(self):
        """Verify that NUMBA_CACHE_DIR is configured before imports."""
        numba_cache_dir = os.environ.get("NUMBA_CACHE_DIR")
        assert numba_cache_dir is not None, (
            "NUMBA_CACHE_DIR should be set in tests/conftest.py before imports. "
            "If this test fails, the Numba caching fix may not be working."
        )
        # Should be set to /tmp/numba_cache_test or empty string
        assert numba_cache_dir in [
            "/tmp/numba_cache_test",
            "",
        ], f"NUMBA_CACHE_DIR should be '/tmp/numba_cache_test' or '', got: {numba_cache_dir}"

    def test_hurst_exponent_analyzer_imports(self):
        """Test that hurst_exponent_analyzer can be imported without caching errors."""
        from app.services.hurst_exponent_analyzer import (
            HurstExponentAnalyzer,
            calculate_cumulative_deviation_numba,
            calculate_rs_for_window_numba,
        )

        # If we got here without RuntimeError, the fix is working
        assert HurstExponentAnalyzer is not None
        assert calculate_cumulative_deviation_numba is not None
        assert calculate_rs_for_window_numba is not None

    def test_hurst_analyzer_functionality(self):
        """Test that HurstExponentAnalyzer works correctly."""
        from app.services.hurst_exponent_analyzer import HurstExponentAnalyzer

        analyzer = HurstExponentAnalyzer()
        np.random.seed(42)
        series = np.random.randn(100)

        result = analyzer.calculate_hurst_exponent(series)

        assert result is not None
        assert 0 <= result.hurst_exponent <= 1
        assert result.regime is not None
        assert result.strategy is not None

    def test_position_sizing_engine_imports(self):
        """Test that position_sizing_engine can be imported without errors."""
        from app.services.position_sizing_engine import PositionSizingEngine

        engine = PositionSizingEngine(atr_multiplier=2.0)
        assert engine is not None
        assert engine.atr_multiplier == Decimal("2.0")

    def test_position_sizing_functionality(self):
        """Test that PositionSizingEngine works correctly."""
        from app.services.position_sizing_engine import PositionSizingEngine

        engine = PositionSizingEngine(atr_multiplier=2.0)
        capital = Decimal("10000")
        entry_price = Decimal("150.00")
        atr = 3.0

        position_size = engine.calculate_position_size_from_atr(
            capital=capital,
            entry_price=entry_price,
            atr=atr,
        )

        assert position_size is not None
        assert position_size > 0
        # Position should not exceed available capital
        max_shares = capital / entry_price
        assert position_size <= max_shares + Decimal("0.01")

    def test_numba_module_availability(self):
        """Verify that Numba is properly available in the modules."""
        from app.services import hurst_exponent_analyzer

        assert hurst_exponent_analyzer.NUMBA_AVAILABLE is True
        assert hurst_exponent_analyzer.NUMBA_VERSION is not None
        assert len(hurst_exponent_analyzer.NUMBA_VERSION) > 0

    def test_numba_jit_functions_exist(self):
        """Verify that Numba JIT functions are properly defined."""
        from app.services import hurst_exponent_analyzer

        # Check that the module has the expected JIT functions
        assert hasattr(hurst_exponent_analyzer, 'calculate_cumulative_deviation_numba')
        assert hasattr(hurst_exponent_analyzer, 'calculate_rs_for_window_numba')
        assert hasattr(hurst_exponent_analyzer, 'calculate_hurst_rs_numba')
        assert hasattr(hurst_exponent_analyzer, 'calculate_hurst_variance_numba')
        assert hasattr(hurst_exponent_analyzer, 'calculate_aggregated_variance_numba')
