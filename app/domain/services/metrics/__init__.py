"""
Centralized Metrics Module

This module provides a unified interface for all risk and performance metrics calculations.
It consolidates multiple implementations that were scattered across the codebase:

ORIGINAL LOCATIONS (to be deprecated):
- /app/backtesting/bias_correctors.py - Sharpe ratio in BacktestValidator
- /app/backtesting/metrics.py - Main MetricsCalculator with Sharpe, Sortino, etc.
- /app/backtesting/numba_metrics.py - Numba-accelerated versions
- /app/backtesting/chan_metrics.py - Ernest Chan methodologies
- /app/backtesting/advanced_metrics.py - Calmar, Omega, VaR, CVaR, etc.
- /app/backtesting/lopez_de_prado_metrics.py - Lopez de Prado methodologies
- /app/domain/services/risk_calculator.py - RiskCalculator with VaR, beta, etc.

USAGE:
    from app.domain.services.metrics import (
        PerformanceMetricsCalculator,
        RiskMetricsCalculator,
        get_sharpe_ratio,
        get_var,
    )

    # Using the unified calculator
    calc = PerformanceMetricsCalculator()
    sharpe = calc.sharpe_ratio(returns)

    # Using convenience functions
    sharpe = get_sharpe_ratio(returns, risk_free_rate=0.02)  # or use CentralizedConfig.backtesting.default_risk_free_rate

ARCHITECTURE:
    - performance_metrics.py: Sharpe, Sortino, Calmar, Omega, etc.
    - risk_metrics.py: VaR, CVaR, Beta, Volatility, Correlation
    - numba_metrics.py: Numba-accelerated versions (preserved)
    - lopez_de_prado.py: Advanced Lopez de Prado methodologies
    - chan_metrics.py: Ernest Chan methodologies

Reference:
    - Lopez de Prado, M. (2020). Machine Learning for Asset Managers.
    - Chan, E.P. (2013). Algorithmic Trading.
"""

from app.domain.services.metrics.performance_metrics import (
    PerformanceMetricsCalculator,
    get_sharpe_ratio,
    get_sortino_ratio,
    get_calmar_ratio,
    get_omega_ratio,
    get_max_drawdown,
    get_ulcer_index,
)
from app.domain.services.metrics.risk_metrics import (
    RiskMetricsCalculator,
    get_var,
    get_cvar,
    get_volatility,
    get_beta,
    get_correlation,
    get_tracking_error,
    get_information_ratio,
)

__all__ = [
    # Performance Metrics Calculator
    "PerformanceMetricsCalculator",
    # Risk Metrics Calculator
    "RiskMetricsCalculator",
    # Convenience functions - Performance
    "get_sharpe_ratio",
    "get_sortino_ratio",
    "get_calmar_ratio",
    "get_omega_ratio",
    "get_max_drawdown",
    "get_ulcer_index",
    # Convenience functions - Risk
    "get_var",
    "get_cvar",
    "get_volatility",
    "get_beta",
    "get_correlation",
    "get_tracking_error",
    "get_information_ratio",
]
