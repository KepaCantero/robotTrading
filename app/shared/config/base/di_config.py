"""
Dependency Injection Configuration

This module configures the DI container with all application dependencies.
It follows the Dependency Inversion Principle - high-level modules depend
on abstractions, not concrete implementations.

Reference: Rule 05-architecture.md, Rule 11-enterprise-architecture.md
"""

import logging

from app.domain.factories import AbstractEntityFactory, TradingEntityFactory
from app.shared.config.di_container import DIContainer, get_container

logger = logging.getLogger(__name__)


def configure_container() -> DIContainer:
    """
    Configure the DI container with all application dependencies.

    This function sets up:
    - Domain factories
    - Repository implementations (when available)
    - Application services (when available)
    - Infrastructure components

    Note:
        Additional repository and service registrations should be added here
        as implementations become available. The container supports both
        singleton and factory registrations depending on the lifecycle
        requirements of each component.

    Returns:
        Configured DI container
    """
    logger.info("Configuring DI container")
    container = get_container()

    # Domain Factories
    logger.debug("Registering domain factory", extra={"factory_type": "AbstractEntityFactory"})
    container.register_singleton(
        AbstractEntityFactory,
        TradingEntityFactory(),
    )
    logger.info(
        "Domain factory registered successfully", extra={"factory_type": "AbstractEntityFactory"}
    )

    # Repository registrations (to be added when implementations are available)
    # Example:
    # container.register_singleton(
    #     AbstractRepository,
    #     SqlAlchemyRepository(...),
    # )

    # Application service registrations (to be added when implementations are available)
    # Example:
    # container.register_factory(
    #     "portfolio_service",
    #     lambda c: PortfolioService(
    #         repository=c.get(AbstractRepository),
    #         factory=c.get(AbstractEntityFactory),
    #     ),
    # )

    logger.info("DI container configuration completed")
    return container


def initialize_container() -> DIContainer:
    """
    Initialize the global DI container.

    This should be called once at application startup.

    Returns:
        Initialized DI container
    """
    logger.info("Initializing DI container")
    container = configure_container()
    logger.info("DI container initialized successfully")
    return container
