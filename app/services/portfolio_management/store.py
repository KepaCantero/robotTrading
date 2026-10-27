"""Persistence for the portfolio-management package.

Three tables (created by alembic migration 0005, mirroring the ORM exactly
— the A20 lesson: a table that exists only in the ORM breaks the first
time `alembic upgrade head` built the database):

- ``target_portfolios`` — versioned target allocations; exactly one row is
  active at a time. Replacing the target (new winner adopted, profile
  change) writes a NEW version instead of mutating, so past rebalance
  explanations keep pointing at the target they were executed against.
- ``portfolio_lots`` — one row per purchase lot. Spain tax-aware selling
  and the 2-month repurchase rule need per-lot dates and prices; the
  existing Position/Trade models only keep an average price.
- ``rebalance_events`` — every planning outcome (skipped included) with
  its plain-language reason, drifts before/after, orders and tax paid.
  This is the "why did the robot do that" history (requirement 12).
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Index, Numeric, String, Text, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.database import Base

from .models import Holding, LotSnapshot, ProfileAnswers, RebalancePlan, TargetPortfolio

logger = logging.getLogger(__name__)


class TargetPortfolioRecord(Base):
    """ORM model for a versioned target portfolio."""

    __tablename__ = "target_portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[int] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # swarm_winner | seed
    source_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    strategy_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    holdings_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    drift_band_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    cooldown_days: Mapped[int] = mapped_column(nullable=False)
    reactive_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_position_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    equity_max_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    __table_args__ = (Index("idx_target_portfolios_active", "is_active", "version"),)


class PortfolioLotRecord(Base):
    """ORM model for one purchase lot of one symbol."""

    __tablename__ = "portfolio_lots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    remaining: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="rebalance")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (Index("idx_portfolio_lots_symbol_date", "symbol", "purchased_at"),)


class RebalanceEventRecord(Base):
    """ORM model for one rebalance decision (planned, executed or skipped)."""

    __tablename__ = "rebalance_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    ts: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    trigger: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # planned|executed|skipped|rejected
    reason: Mapped[str] = mapped_column(Text, nullable=False)  # plain-language summary
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (Index("idx_rebalance_events_ts", "ts"),)


def _to_decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


class PortfolioManagementStore:
    """Async repository over the three portfolio-management tables."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = session_factory

    # ── Target portfolios ────────────────────────────────────────────────

    async def save_target(self, target: TargetPortfolio) -> TargetPortfolio:
        """Persist a NEW version and make it the only active one."""
        async with self._sessions() as session:
            latest = (
                await session.execute(
                    select(TargetPortfolioRecord.version).order_by(
                        TargetPortfolioRecord.version.desc()
                    )
                )
            ).scalar()
            target.version = (latest or 0) + 1
            # Deactivate the previous active row BEFORE inserting the new
            # one — the other order also deactivates the row just written.
            await session.execute(
                update(TargetPortfolioRecord)
                .where(TargetPortfolioRecord.is_active.is_(True))
                .values(is_active=False)
            )
            record = TargetPortfolioRecord(
                version=target.version,
                is_active=True,
                source=target.source,
                source_run_id=target.source_run_id,
                strategy_name=target.strategy_name,
                decision_status=target.decision_status,
                profile_json=target.profile.model_dump(mode="json"),
                holdings_json=[h.model_dump(mode="json") for h in target.holdings],
                drift_band_pct=target.drift_band_pct,
                cooldown_days=target.cooldown_days,
                reactive_only=target.reactive_only,
                max_position_pct=target.max_position_pct,
                equity_max_pct=target.equity_max_pct,
                created_at=target.created_at,
            )
            session.add(record)
            await session.commit()
        logger.info("Target portfolio v%s saved (source=%s)", target.version, target.source)
        return target

    async def get_active_target(self) -> TargetPortfolio | None:
        async with self._sessions() as session:
            record = (
                (
                    await session.execute(
                        select(TargetPortfolioRecord)
                        .where(TargetPortfolioRecord.is_active.is_(True))
                        .order_by(TargetPortfolioRecord.version.desc())
                    )
                )
                .scalars()
                .first()
            )
            if record is None:
                return None
            return TargetPortfolio(
                version=record.version,
                source=record.source,
                source_run_id=record.source_run_id,
                strategy_name=record.strategy_name,
                decision_status=record.decision_status,
                holdings=[
                    Holding(
                        symbol=h["symbol"],
                        weight=_to_decimal(h["weight"]),
                        rationale=h.get("rationale", ""),
                    )
                    for h in record.holdings_json
                ],
                profile=ProfileAnswers(**record.profile_json),
                drift_band_pct=_to_decimal(record.drift_band_pct),
                cooldown_days=record.cooldown_days,
                reactive_only=record.reactive_only,
                max_position_pct=_to_decimal(record.max_position_pct),
                equity_max_pct=_to_decimal(record.equity_max_pct),
                created_at=record.created_at or datetime.utcnow(),
            )

    async def update_target_flags(
        self,
        version: int,
        reactive_only: bool | None = None,
        drift_band_pct: Decimal | None = None,
        cooldown_days: int | None = None,
    ) -> bool:
        """Adjust rebalancing rules on the active target without a new version."""
        values: dict[str, Any] = {}
        if reactive_only is not None:
            values["reactive_only"] = reactive_only
        if drift_band_pct is not None:
            values["drift_band_pct"] = drift_band_pct
        if cooldown_days is not None:
            values["cooldown_days"] = cooldown_days
        if not values:
            return False
        async with self._sessions() as session:
            result = await session.execute(
                update(TargetPortfolioRecord)
                .where(
                    TargetPortfolioRecord.is_active.is_(True),
                    TargetPortfolioRecord.version == version,
                )
                .values(**values)
            )
            await session.commit()
            return bool(result.rowcount)

    # ── Lots ─────────────────────────────────────────────────────────────

    async def add_lot(
        self,
        symbol: str,
        quantity: Decimal,
        purchase_price: Decimal,
        purchased_at: datetime | None = None,
        source: str = "rebalance",
    ) -> str:
        async with self._sessions() as session:
            record = PortfolioLotRecord(
                symbol=symbol.upper(),
                quantity=quantity,
                remaining=quantity,
                purchase_price=purchase_price,
                purchased_at=purchased_at or datetime.utcnow(),
                source=source,
            )
            session.add(record)
            await session.commit()
            return record.id

    async def get_lots(self, symbol: str | None = None) -> list[LotSnapshot]:
        """Open lots (remaining > 0), oldest first — FIFO order."""
        async with self._sessions() as session:
            statement = select(PortfolioLotRecord).where(PortfolioLotRecord.remaining > 0)
            if symbol:
                statement = statement.where(PortfolioLotRecord.symbol == symbol.upper())
            statement = statement.order_by(PortfolioLotRecord.purchased_at.asc())
            records = (await session.execute(statement)).scalars().all()
            return [
                LotSnapshot(
                    lot_id=r.id,
                    symbol=r.symbol,
                    quantity=_to_decimal(r.remaining),
                    purchase_price=_to_decimal(r.purchase_price),
                    purchased_at=r.purchased_at or datetime.utcnow(),
                    source=r.source,
                )
                for r in records
            ]

    async def clear_lots(self) -> int:
        """Zero every open lot. Used ONLY by the supervised 'fresh paper
        start' — the audit trail (events) is kept, the tax lots are not."""
        async with self._sessions() as session:
            result = await session.execute(
                delete(PortfolioLotRecord).where(PortfolioLotRecord.remaining > 0)
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def consume_lots_fifo(self, symbol: str, quantity: Decimal) -> list[LotSnapshot]:
        """Mark ``quantity`` shares sold, oldest lots first.

        Returns the matched lots (with ``quantity`` = the matched amount per
        lot) so the caller can compute the realised gain per lot.
        """
        symbol = symbol.upper()
        matched: list[LotSnapshot] = []
        outstanding = quantity
        async with self._sessions() as session:
            records = (
                (
                    await session.execute(
                        select(PortfolioLotRecord)
                        .where(
                            PortfolioLotRecord.symbol == symbol, PortfolioLotRecord.remaining > 0
                        )
                        .order_by(PortfolioLotRecord.purchased_at.asc())
                    )
                )
                .scalars()
                .all()
            )
            for record in records:
                if outstanding <= 0:
                    break
                take = min(_to_decimal(record.remaining), outstanding)
                record.remaining = _to_decimal(record.remaining) - take
                outstanding -= take
                matched.append(
                    LotSnapshot(
                        lot_id=record.id,
                        symbol=record.symbol,
                        quantity=take,
                        purchase_price=_to_decimal(record.purchase_price),
                        purchased_at=record.purchased_at or datetime.utcnow(),
                        source=record.source,
                    )
                )
            await session.commit()
        if outstanding > 0:
            logger.warning(
                "FIFO consume for %s exceeded recorded lots by %s (position drift "
                "between broker and lot store — will reconcile)",
                symbol,
                outstanding,
            )
        return matched

    # ── Rebalance events ─────────────────────────────────────────────────

    async def append_event(
        self,
        trigger: str,
        action: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> str:
        async with self._sessions() as session:
            record = RebalanceEventRecord(
                trigger=trigger,
                action=action,
                reason=reason,
                details_json=details or {},
            )
            session.add(record)
            await session.commit()
            return record.id

    async def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        async with self._sessions() as session:
            records = (
                (
                    await session.execute(
                        select(RebalanceEventRecord).order_by(RebalanceEventRecord.ts.desc())
                    )
                )
                .scalars()
                .all()
            )[:limit]
            return [
                {
                    "id": r.id,
                    "ts": r.ts.isoformat() if r.ts else None,
                    "trigger": r.trigger,
                    "action": r.action,
                    "reason": r.reason,
                    "details": r.details_json or {},
                }
                for r in records
            ]

    async def last_rebalance_at(self) -> datetime | None:
        """Timestamp of the last EXECUTED rebalance (cooldown anchor)."""
        async with self._sessions() as session:
            record = (
                (
                    await session.execute(
                        select(RebalanceEventRecord)
                        .where(RebalanceEventRecord.action == "executed")
                        .order_by(RebalanceEventRecord.ts.desc())
                    )
                )
                .scalars()
                .first()
            )
            return record.ts if record else None

    async def record_plan(self, plan: RebalancePlan, action: str) -> str:
        """Persist a plan (or its skip) as the explained history entry."""
        return await self.append_event(
            trigger=plan.trigger.value,
            action=action,
            reason=plan.summary or "; ".join(plan.reasons) or "no action needed",
            details=plan.to_details(),
        )
