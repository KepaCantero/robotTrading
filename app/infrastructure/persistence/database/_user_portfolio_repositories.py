"""
User and Portfolio Repository Implementations.

Split from repositories.py to improve maintainability index.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn, cast

from sqlalchemy import and_
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)

from app.infrastructure.persistence.database._base_repository import BaseRepository, logger
from app.infrastructure.persistence.database.models import Asset, Portfolio, Position, User
from app.shared.exceptions.exceptions import raise_database_error

if TYPE_CHECKING:
    import uuid
    from decimal import Decimal


def _raise_db_error(message: str, operation: str, table: str) -> NoReturn:
    """Typed wrapper to ensure mypy knows this never returns."""
    raise_database_error(message, operation, table)
    raise AssertionError("unreachable")  # safeguard


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        try:
            result = self.session.query(User).filter(User.username == username).first()
            logger.debug(
                "queried_user_by_username",
                username=username,
                found=result is not None,
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_username_failed",
                username=username,
                error=str(e),
            )
            _raise_db_error(f"Failed to get user by username: {e!s}", "get_by_username", "users")

    def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        try:
            result = self.session.query(User).filter(User.email == email).first()
            logger.debug(
                "queried_user_by_email",
                email=email,
                found=result is not None,
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_email_failed",
                email=email,
                error=str(e),
            )
            _raise_db_error(f"Failed to get user by email: {e!s}", "get_by_email", "users")

    def get_active_users(self) -> list[User]:
        """Get all active users."""
        try:
            result = cast("list[User]", self.session.query(User).filter(User.is_active).all())
            logger.debug(
                "queried_active_users",
                count=len(result),
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_active_users_failed",
                error=str(e),
            )
            _raise_db_error(f"Failed to get active users: {e!s}", "get_active_users", "users")


class PortfolioRepository(BaseRepository[Portfolio]):
    """Repository for Portfolio model."""

    def get_by_user(self, user_id: uuid.UUID) -> list[Portfolio]:
        """Get portfolios by user ID."""
        try:
            result = cast(
                "list[Portfolio]",
                self.session.query(Portfolio).filter(Portfolio.user_id == user_id).all(),
            )
            logger.debug(
                "queried_portfolios_by_user",
                user_id=str(user_id),
                count=len(result),
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_user_failed",
                user_id=str(user_id),
                error=str(e),
            )
            _raise_db_error(
                f"Failed to get portfolios by user: {e!s}",
                "get_by_user",
                "portfolios",
            )

    def get_active_by_user(self, user_id: uuid.UUID) -> list[Portfolio]:
        """Get active portfolios by user ID."""
        try:
            result = cast(
                "list[Portfolio]",
                (
                    self.session.query(Portfolio)
                    .filter(and_(Portfolio.user_id == user_id, Portfolio.is_active))
                    .all()
                ),
            )
            logger.debug(
                "queried_active_portfolios_by_user",
                user_id=str(user_id),
                count=len(result),
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_active_by_user_failed",
                user_id=str(user_id),
                error=str(e),
            )
            _raise_db_error(
                f"Failed to get active portfolios by user: {e!s}",
                "get_active_by_user",
                "portfolios",
            )

    def update_total_value(self, portfolio_id: uuid.UUID, total_value: Decimal) -> bool:
        """Update portfolio total value."""
        try:
            self.session.query(Portfolio).filter(Portfolio.id == portfolio_id).update(
                {"total_value": total_value}
            )
            self.session.commit()
            logger.info(
                "updated_portfolio_total_value",
                portfolio_id=str(portfolio_id),
                total_value=float(total_value),
            )
            return True
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            self.session.rollback()
            logger.error(
                "update_total_value_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            _raise_db_error(
                f"Failed to update portfolio total value: {e!s}",
                "update_total_value",
                "portfolios",
            )


class AssetRepository(BaseRepository[Asset]):
    """Repository for Asset model."""

    def get_by_symbol(self, symbol: str) -> Asset | None:
        """Get asset by symbol."""
        try:
            result = self.session.query(Asset).filter(Asset.symbol == symbol).first()
            logger.debug(
                "queried_asset_by_symbol",
                symbol=symbol,
                found=result is not None,
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_symbol_failed",
                symbol=symbol,
                error=str(e),
            )
            _raise_db_error(f"Failed to get asset by symbol: {e!s}", "get_by_symbol", "assets")

    def get_by_asset_class(self, asset_class: str) -> list[Asset]:
        """Get assets by asset class."""
        try:
            result = cast(
                "list[Asset]",
                self.session.query(Asset).filter(Asset.asset_class == asset_class).all(),
            )
            logger.debug(
                "queried_assets_by_class",
                asset_class=asset_class,
                count=len(result),
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_asset_class_failed",
                asset_class=asset_class,
                error=str(e),
            )
            _raise_db_error(
                f"Failed to get assets by class: {e!s}",
                "get_by_asset_class",
                "assets",
            )

    def get_active_assets(self) -> list[Asset]:
        """Get all active assets."""
        try:
            result = cast("list[Asset]", self.session.query(Asset).filter(Asset.is_active).all())
            logger.debug(
                "queried_active_assets",
                count=len(result),
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_active_assets_failed",
                error=str(e),
            )
            _raise_db_error(f"Failed to get active assets: {e!s}", "get_active_assets", "assets")

    def search_by_name(self, name_pattern: str) -> list[Asset]:
        """Search assets by name pattern."""
        try:
            result = cast(
                "list[Asset]",
                self.session.query(Asset).filter(Asset.name.ilike(f"%{name_pattern}%")).all(),
            )
            logger.debug(
                "searched_assets_by_name",
                pattern=name_pattern,
                count=len(result),
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "search_by_name_failed",
                pattern=name_pattern,
                error=str(e),
            )
            _raise_db_error(f"Failed to search assets by name: {e!s}", "search_by_name", "assets")


class PositionRepository(BaseRepository[Position]):
    """Repository for Position model."""

    def get_by_portfolio(self, portfolio_id: uuid.UUID) -> list[Position]:
        """Get positions by portfolio ID."""
        try:
            result = cast(
                "list[Position]",
                self.session.query(Position).filter(Position.portfolio_id == portfolio_id).all(),
            )
            logger.debug(
                "queried_positions_by_portfolio",
                portfolio_id=str(portfolio_id),
                count=len(result),
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_portfolio_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            _raise_db_error(
                f"Failed to get positions by portfolio: {e!s}",
                "get_by_portfolio",
                "positions",
            )

    def get_by_portfolio_and_asset(
        self, portfolio_id: uuid.UUID, asset_id: uuid.UUID
    ) -> Position | None:
        """Get position by portfolio and asset IDs."""
        try:
            result = (
                self.session.query(Position)
                .filter(
                    and_(
                        Position.portfolio_id == portfolio_id,
                        Position.asset_id == asset_id,
                    )
                )
                .first()
            )
            logger.debug(
                "queried_position_by_portfolio_and_asset",
                portfolio_id=str(portfolio_id),
                asset_id=str(asset_id),
                found=result is not None,
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_by_portfolio_and_asset_failed",
                portfolio_id=str(portfolio_id),
                asset_id=str(asset_id),
                error=str(e),
            )
            _raise_db_error(
                f"Failed to get position by portfolio and asset: {e!s}",
                "get_by_portfolio_and_asset",
                "positions",
            )

    def get_open_positions(self, portfolio_id: uuid.UUID) -> list[Position]:
        """Get all open positions for a portfolio."""
        try:
            result = cast(
                "list[Position]",
                (
                    self.session.query(Position)
                    .filter(
                        and_(
                            Position.portfolio_id == portfolio_id,
                            Position.quantity > 0,
                        )
                    )
                    .all()
                ),
            )
            logger.debug(
                "queried_open_positions",
                portfolio_id=str(portfolio_id),
                count=len(result),
            )
            return result
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            logger.error(
                "get_open_positions_failed",
                portfolio_id=str(portfolio_id),
                error=str(e),
            )
            _raise_db_error(
                f"Failed to get open positions: {e!s}",
                "get_open_positions",
                "positions",
            )

    def update_position_price(self, position_id: uuid.UUID, current_price: Decimal) -> bool:
        """Update position current price."""
        try:
            self.session.query(Position).filter(Position.id == position_id).update(
                {"current_price": current_price}
            )
            self.session.commit()
            logger.debug(
                "updated_position_price",
                position_id=str(position_id),
                current_price=float(current_price),
            )
            return True
        except (
            IntegrityError,
            DataError,
            OperationalError,
            ProgrammingError,
            DatabaseError,
        ) as e:
            self.session.rollback()
            logger.error(
                "update_position_price_failed",
                position_id=str(position_id),
                error=str(e),
            )
            _raise_db_error(
                f"Failed to update position price: {e!s}",
                "update_position_price",
                "positions",
            )
