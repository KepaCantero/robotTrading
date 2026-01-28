"""Strategy Type enumeration for trading strategies.

Maps investment objectives to specific strategy implementations based on
academic research and trading literature.

References:
- Gray & Vogel: Quantitative Momentum (11-gray-vogel-quantitative-momentum.md)
- Berkin & Swedroe: Factor-Based Investing (30-berkin-swedroe-factor-based-investing.md)
- Markowitz: Portfolio Selection (48-papers-markowitz-portfolio-selection.md)
- Fama-French: Factor Models (43-papers-fama-french-carhart-factors.md)
- Kissell: Portfolio Management (42-kissell-algorithmic-trading-portfolio-management.md)
"""

from enum import Enum


class StrategyType(str, Enum):
    """Trading strategy types mapped to investment objectives.

    Each strategy type corresponds to specific investment objectives
    and is backed by academic research.

    Mapping:
    - MOMENTUM: MAXIMIZAR_CAPITAL -> Gray & Vogel quantitative momentum
    - DIVIDEND: MAXIMIZAR_DIVIDENDOS -> Berkin & Swedroe dividend investing
    - LOW_VOLATILITY: CAPITAL_PRESERVATION -> Markowitz MVO + Risk Parity
    - MULTI_FACTOR: BALANCED_GROWTH -> Fama-French multi-factor models
    - COVERED_CALL: INCOME_GENERATION -> Kissell portfolio management
    """

    MOMENTUM = "momentum"
    """Momentum/Trend Following strategy.

    Reference: Gray & Vogel - Quantitative Momentum.
    Suitable for: MAXIMIZAR_CAPITAL objective.
    """

    DIVIDEND = "dividend"
    """Dividend investing strategy.

    Reference: Berkin & Swedroe - Factor-Based Investing.
    Suitable for: MAXIMIZAR_DIVIDENDOS objective.
    """

    LOW_VOLATILITY = "low_volatility"
    """Low volatility + Risk Parity strategy.

    Reference: Markowitz - Portfolio Selection (MVO + Risk Parity).
    Suitable for: CAPITAL_PRESERVATION objective.
    """

    MULTI_FACTOR = "multi_factor"
    """Multi-factor strategy (Fama-French-Carhart).

    Reference: Fama-French-Carhart factor models.
    Suitable for: BALANCED_GROWTH objective.
    """

    COVERED_CALL = "covered_call"
    """Covered calls + income generation strategy.

    Reference: Kissell - Algorithmic Trading Portfolio Management.
    Suitable for: INCOME_GENERATION objective.
    """

    def __str__(self) -> str:
        """Return string representation of strategy type."""
        return self.value

    @property
    def description(self) -> str:
        """Get human-readable description of the strategy."""
        descriptions = {
            StrategyType.MOMENTUM: "Momentum/Trend Following - Gray & Vogel",
            StrategyType.DIVIDEND: "Dividend Investing - Berkin & Swedroe",
            StrategyType.LOW_VOLATILITY: "Low Volatility + Risk Parity - Markowitz",
            StrategyType.MULTI_FACTOR: "Multi-Factor - Fama-French-Carhart",
            StrategyType.COVERED_CALL: "Covered Calls - Kissell",
        }
        return descriptions[self]

    @property
    def requires_leverage(self) -> bool:
        """Check if strategy typically requires leverage."""
        return self in {
            StrategyType.MULTI_FACTOR,
            StrategyType.COVERED_CALL,
        }

    @property
    def is_defensive(self) -> bool:
        """Check if strategy is defensive (capital preservation focus)."""
        return self in {
            StrategyType.LOW_VOLATILITY,
            StrategyType.DIVIDEND,
        }
