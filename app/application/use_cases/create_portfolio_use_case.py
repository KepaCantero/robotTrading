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
        """
        return self._factory.create_portfolio(
            portfolio_id=portfolio_id,
            initial_capital=initial_capital,
            currency=currency,
            max_position_size_pct=max_position_size_pct,
            max_portfolio_exposure_pct=max_portfolio_exposure_pct,
        )
