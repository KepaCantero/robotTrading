"""
Create Portfolio Use Case - Create a new portfolio
"""

from decimal import Decimal
from typing import Optional

from app.domain.entities.portfolio import Portfolio
from app.domain.factories import TradingEntityFactory


class CreatePortfolioUseCase:
    """
    Use case for creating a new portfolio.

    This use case orchestrates the creation of a portfolio entity
    with appropriate capital and risk parameters.
    """

    def __init__(self, factory: Optional[TradingEntityFactory] = None):
        """Initialize use case with optional factory."""
        self._factory = factory or TradingEntityFactory()

    def execute(
        self,
        portfolio_id: str,
        initial_capital: Decimal,
        currency: str = "USD",
        max_position_size_pct: Decimal = Decimal("0.2"),
        max_portfolio_exposure_pct: Decimal = Decimal("0.8"),
    ) -> Portfolio:
        """
        Execute the use case - create a portfolio.

        Args:
            portfolio_id: Unique portfolio identifier
            initial_capital: Initial capital amount
            currency: Currency code
            max_position_size_pct: Max position size as percentage
            max_portfolio_exposure_pct: Max portfolio exposure as percentage

        Returns:
            Created Portfolio entity

        Raises:
            ValueError: If any input validation fails
        """
        # Validate portfolio_id
        if not portfolio_id or not isinstance(portfolio_id, str) or not portfolio_id.strip():
            raise ValueError("portfolio_id must be a non-empty string")

        # Validate initial_capital
        if not isinstance(initial_capital, Decimal):
            raise ValueError("initial_capital must be a Decimal")
        if initial_capital <= 0:
            raise ValueError("initial_capital must be positive (> 0)")

        # Validate currency (ISO 4217: 3-letter uppercase code)
        if not currency or not isinstance(currency, str):
            raise ValueError("currency must be a string")
        if len(currency) != 3 or not currency.isupper() or not currency.isalpha():
            raise ValueError("currency must be a valid ISO 4217 code (3 uppercase letters)")

        # Validate max_position_size_pct
        if not isinstance(max_position_size_pct, Decimal):
            raise ValueError("max_position_size_pct must be a Decimal")
        if max_position_size_pct <= 0 or max_position_size_pct > 1:
            raise ValueError("max_position_size_pct must be in range (0, 1]")

        # Validate max_portfolio_exposure_pct
        if not isinstance(max_portfolio_exposure_pct, Decimal):
            raise ValueError("max_portfolio_exposure_pct must be a Decimal")
        if max_portfolio_exposure_pct <= 0 or max_portfolio_exposure_pct > 1:
            raise ValueError("max_portfolio_exposure_pct must be in range (0, 1]")

        return self._factory.create_portfolio(
            portfolio_id=portfolio_id,
            initial_capital=initial_capital,
            currency=currency,
            max_position_size_pct=max_position_size_pct,
            max_portfolio_exposure_pct=max_portfolio_exposure_pct,
        )
