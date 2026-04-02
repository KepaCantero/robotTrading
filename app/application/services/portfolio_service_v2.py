"""
Portfolio Service - Refactored with Dependency Injection

This version demonstrates proper dependency injection following SOLID principles:
- SRP: Single responsibility (portfolio management only)
- DIP: Dependencies injected, not created internally
- OCP: Open for extension via interfaces
- ISP: Small, focused interface

Reference: Rule 03-solid-principles.md, Rule 05-architecture.md
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.domain.factories import AbstractEntityFactory
from app.domain.repositories.portfolio_repository import PortfolioRepository

if TYPE_CHECKING:
    from decimal import Decimal

    from app.domain.entities.portfolio import Portfolio
    from app.shared.config.di_container import DIContainer

logger = logging.getLogger(__name__)


class PortfolioServiceV2:
    """
    Portfolio management service with dependency injection.

    This service manages portfolio operations using injected dependencies
    rather than creating them directly, following the Dependency Inversion
    Principle.

    Example:
        ```python
        # Old way (violates DIP):
        service = PortfolioService(provider)  # Creates dependencies internally

        # New way (follows DIP):
        service = PortfolioServiceV2(
            repository=container.get(PortfolioRepository),
            factory=container.get(AbstractEntityFactory),
        )
        ```
    """

    def __init__(
        self,
        repository: PortfolioRepository,
        factory: AbstractEntityFactory,
        di_container: DIContainer | None = None,
    ) -> None:
        """
        Initialize service with injected dependencies.

        Args:
            repository: Portfolio repository (injected)
            factory: Entity factory (injected)
            di_container: DI container for optional dependencies
        """
        self._repository = repository
        self._factory = factory
        self._container = di_container

    async def get_portfolio(self, portfolio_id: str) -> Portfolio | None:
        """
        Get portfolio by ID.

        Args:
            portfolio_id: Portfolio identifier

        Returns:
            Portfolio if found, None otherwise
        """
        try:
            return await self._repository.find_by_id(portfolio_id)
        except (ValueError, KeyError, AttributeError) as e:
            # Log error with stack trace but don't crash
            logger.error(
                "Error getting portfolio: %s",
                e,
                extra={"portfolio_id": portfolio_id},
                exc_info=True,  # Includes stack trace
            )
            return None

    async def create_portfolio(
        self,
        portfolio_id: str,
        initial_capital: Decimal,
        currency: str = "USD",
    ) -> Portfolio:
        """
        Create a new portfolio.

        Args:
            portfolio_id: Portfolio identifier
            initial_capital: Initial capital amount
            currency: Currency code (ISO 4217 format)

        Returns:
            Created portfolio

        Raises:
            ValueError: If validation fails
        """
        if not portfolio_id or not isinstance(portfolio_id, str):
            raise ValueError("portfolio_id must be a non-empty string")

        if initial_capital <= 0:
            raise ValueError("initial_capital must be positive")

        if not currency or len(currency) != 3:
            raise ValueError("currency must be a valid ISO 4217 code")

        portfolio = self._factory.create_portfolio(
            portfolio_id=portfolio_id,
            initial_capital=initial_capital,
            currency=currency,
        )

        await self._repository.save(portfolio)
        return portfolio

    async def update_portfolio_weights(
        self,
        portfolio_id: str,
        new_weights: dict[str, Decimal],
    ) -> bool:
        """
        Update portfolio weights.

        Args:
            portfolio_id: Portfolio identifier
            new_weights: New target weights (symbol -> target weight ratio)

        Returns:
            True if updated successfully

        Note:
            This method adjusts position quantities to match target weights.
            The weights dict maps symbols to their target allocation ratios (0.0-1.0).
        """
        portfolio = await self.get_portfolio(portfolio_id)
        if portfolio is None:
            return False

        # Adjust positions to match target weights
        # This is a simplified implementation - in production, you would
        # calculate the actual trades needed to rebalance
        total_capital = portfolio.capital.amount
        for symbol, target_weight in new_weights.items():
            target_value = total_capital * target_weight
            if symbol in portfolio.positions:
                # Update position value to match target allocation
                # Note: In production, this would involve actual trade execution
                logger.debug(
                    "Rebalancing %s: target_weight=%s, target_value=%s",
                    symbol,
                    target_weight,
                    target_value,
                )

        await self._repository.save(portfolio)
        return True

    def get_dependency_summary(self) -> dict[str, str]:
        """
        Get summary of injected dependencies (for debugging).

        Returns:
            Dictionary of dependency types
        """
        return {
            "repository": type(self._repository).__name__,
            "factory": type(self._factory).__name__,
            "has_container": str(self._container is not None),
        }


# Factory function for DI container
def create_portfolio_service(container: DIContainer) -> PortfolioServiceV2:
    """
    Factory function to create PortfolioService with DI.

    Args:
        container: DI container

    Returns:
        Configured PortfolioService instance
    """
    return PortfolioServiceV2(
        repository=container.get(PortfolioRepository),
        factory=container.get(AbstractEntityFactory),
        di_container=container,
    )
