"""
Dependency Injection Configuration

This module configures the DI container with all application dependencies.
It follows the Dependency Inversion Principle - high-level modules depend
on abstractions, not concrete implementations.

Reference: Rule 05-architecture.md, Rule 11-enterprise-architecture.md
"""

from app.core.di_container import DIContainer, get_container
from app.domain.factories import AbstractEntityFactory, TradingEntityFactory


def configure_container() -> DIContainer:
    """
    Configure the DI container with all application dependencies.

    This function sets up:
    - Domain factories
    - Repository implementations
    - Application services
    - Infrastructure components

    Returns:
        Configured DI container
    """
    container = get_container()

    # Domain Factories
    container.register_singleton(
        AbstractEntityFactory,
        TradingEntityFactory(),
    )

    # TODO: Register repositories when implementations are available
    # container.register_singleton(
    #     AbstractRepository,
    #     SqlAlchemyRepository(...),
    # )

    # TODO: Register application services
    # container.register_factory(
    #     "portfolio_service",
    #     lambda c: PortfolioService(
    #         repository=c.get(AbstractRepository),
    #         factory=c.get(AbstractEntityFactory),
    #     ),
    # )

    return container


def initialize_container() -> DIContainer:
    """
    Initialize the global DI container.

    This should be called once at application startup.

    Returns:
        Initialized DI container
    """
    return configure_container()
