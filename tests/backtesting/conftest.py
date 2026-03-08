"""
Pytest configuration and shared fixtures for backtesting tests.

This module provides fixtures for multi-symbol backtesting tests.
All tests should use these fixtures instead of hardcoded symbols.

Usage in tests:
    def test_something(default_symbol):
        # Uses first available symbol (e.g., AAPL)
        ...

    def test_with_all_symbols(all_available_symbols):
        # Uses ALL 61 downloaded symbols
        for symbol in all_available_symbols:
            ...

    def test_quick(sample_symbols):
        # Uses only 5 symbols for quick tests
        for symbol in sample_symbols:
            ...
"""

import pytest
from typing import List
from pathlib import Path

# Historical data directory
HISTORICAL_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "historical"


def get_available_symbols() -> List[str]:
    """Get all available symbols from data/historical/ directory."""
    symbols = []
    if HISTORICAL_DATA_DIR.exists():
        for csv_file in HISTORICAL_DATA_DIR.glob("*.csv"):
            symbols.append(csv_file.stem)
    return sorted(symbols)


# Pre-computed constants for direct import
AVAILABLE_SYMBOLS = get_available_symbols()
DEFAULT_SYMBOL = AVAILABLE_SYMBOLS[0] if AVAILABLE_SYMBOLS else "AAPL"
QUICK_TEST_SYMBOLS = AVAILABLE_SYMBOLS[:5] if len(AVAILABLE_SYMBOLS) >= 5 else AVAILABLE_SYMBOLS
SAMPLE_TEST_SYMBOLS = QUICK_TEST_SYMBOLS


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture(scope="session")
def all_symbols() -> List[str]:
    """Return all available symbols from data/historical/."""
    return AVAILABLE_SYMBOLS


@pytest.fixture(scope="session")
def default_symbol() -> str:
    """Return the first available symbol (or AAPL as fallback)."""
    return DEFAULT_SYMBOL


@pytest.fixture(scope="session")
def quick_test_symbols() -> List[str]:
    """Return a sample of 5 symbols for quick tests."""
    return QUICK_TEST_SYMBOLS


# Alias for convenience
sample_symbols = quick_test_symbols


# Export for direct import
__all__ = [
    "AVAILABLE_SYMBOLS",
    "DEFAULT_SYMBOL",
    "QUICK_TEST_SYMBOLS",
    "SAMPLE_TEST_SYMBOLS",
    "get_available_symbols",
    "all_symbols",
    "default_symbol",
    "quick_test_symbols",
    "sample_symbols",
]
