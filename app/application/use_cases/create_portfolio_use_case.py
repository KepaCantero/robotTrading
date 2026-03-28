"""
Create Portfolio Use Case - Create a new portfolio
"""

import logging
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

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
        logger.debug(
            "CreatePortfolioUseCase initialized",
            extra={"factory_type": type(self._factory).__name__},
        )

    def _validate_portfolio_id(self, portfolio_id: str) -> None:
        """Validate portfolio_id."""
        if not portfolio_id or not isinstance(portfolio_id, str) or not portfolio_id.strip():
            logger.warning(
                "Portfolio ID validation failed",
                extra={"portfolio_id": portfolio_id, "validation_error": "empty_or_invalid"},
            )
            raise ValueError("portfolio_id must be a non-empty string")

    def _validate_initial_capital(self, initial_capital: Decimal) -> None:
        """Validate initial_capital."""
        if not isinstance(initial_capital, Decimal):
            logger.warning(
                "Initial capital validation failed - not a Decimal",
                extra={"initial_capital_type": type(initial_capital).__name__},
            )
            raise ValueError("initial_capital must be a Decimal")
        if initial_capital <= 0:
            logger.warning(
                "Initial capital validation failed - not positive",
                extra={"initial_capital": float(initial_capital)},
            )
            raise ValueError("initial_capital must be positive (> 0)")

    def _validate_currency(self, currency: str) -> None:
        """Validate currency (ISO 4217: 3-letter uppercase code)."""
        if not currency or not isinstance(currency, str):
            raise ValueError("currency must be a string")
        if len(currency) != 3 or not currency.isupper() or not currency.isalpha():
            raise ValueError("currency must be a valid ISO 4217 code (3 uppercase letters)")

    def _validate_percentage(self, value: Decimal, name: str) -> None:
        """Validate a percentage value is in range (0, 1]."""
        if not isinstance(value, Decimal):
            raise ValueError(f"{name} must be a Decimal")
        if value <= 0 or value > 1:
            raise ValueError(f"{name} must be in range (0, 1]")

    def execute(
        self,
        portfolio_id: str,
        initial_capital: Decimal,
        currency: str = "USD",
        max_position_size_pct: Optional[Decimal] = None,
        max_portfolio_exposure_pct: Optional[Decimal] = None,
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
        if max_position_size_pct is None:
            max_position_size_pct = Decimal("0.2")
        if max_portfolio_exposure_pct is None:
            max_portfolio_exposure_pct = Decimal("0.8")
        logger.info(
            "Creating portfolio",
            extra={
                "portfolio_id": portfolio_id,
                "initial_capital": float(initial_capital),
                "currency": currency,
                "max_position_size_pct": float(max_position_size_pct),
                "max_portfolio_exposure_pct": float(max_portfolio_exposure_pct),
            },
        )

        # Validate all inputs
        self._validate_portfolio_id(portfolio_id)
        self._validate_initial_capital(initial_capital)
        self._validate_currency(currency)
        self._validate_percentage(max_position_size_pct, "max_position_size_pct")
        self._validate_percentage(max_portfolio_exposure_pct, "max_portfolio_exposure_pct")

        portfolio = self._factory.create_portfolio(
            portfolio_id=portfolio_id,
            initial_capital=initial_capital,
            currency=currency,
            max_position_size_pct=max_position_size_pct,
            max_portfolio_exposure_pct=max_portfolio_exposure_pct,
        )

        logger.info(
            "Portfolio created successfully",
            extra={
                "portfolio_id": portfolio_id,
                "currency": currency,
            },
        )

        return portfolio
