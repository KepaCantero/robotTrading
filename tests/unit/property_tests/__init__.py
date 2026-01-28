"""
Property-Based Tests Package

This package contains Hypothesis-based property tests for financial calculations.

Property testing complements traditional unit testing by:
1. Testing invariants and mathematical properties
2. Finding edge cases through random generation
3. Ensuring correctness across wide input ranges
4. Verifying mathematical relationships hold true

Test Files:
- test_position_sizing_properties.py: Kelly Criterion, ATR-based sizing
- test_risk_metrics_properties.py: Sharpe, Sortino, VaR, drawdown
- test_portfolio_properties.py: Weights, returns, optimization
- test_greeks_properties.py: Options Greeks, put-call parity
- test_bet_sizing_properties.py: López de Prado bet sizing

Usage:
    pytest tests/unit/property_tests/ -v
    pytest tests/unit/property_tests/test_position_sizing_properties.py -v

Markers:
    @pytest.mark.unit: Unit test
    @pytest.mark.property: Property-based test
"""

try:
    from hypothesis import settings, Phase

    # Configure Hypothesis settings for property tests
    default_settings = settings(
        max_examples=100,
        phases=[Phase.generate, Phase.target],  # Skip shrink phase for speed
        deadline=None,  # Disable per-test deadline
    )
except ImportError:
    # Hypothesis not installed - property tests will be skipped
    default_settings = None
