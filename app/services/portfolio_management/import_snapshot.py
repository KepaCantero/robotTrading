"""Import a real portfolio as the baseline target of a named portfolio.

The use case: the user already holds a live IBKR account (or wants to
start from any real snapshot). Importing captures TODAY's real weights as
the active target of a NEW named portfolio, so:

- ``compare_live_portfolio.py --slug <slug>`` measures how the live
  account drifts away from the import day,
- the /portfolio page shows and manages it like any other portfolio,
- the robot's rules (position cap, equity ceiling) are checked against
  reality and the violations REPORTED — an import describes what you
  hold, it never pretends you hold something else. This is the opposite
  of winner adoption, which clamps a proposal to the caps.

Sources of positions:
- live IBKR (read-only): :class:`IbkrAdapter` marks are already in the
  account base currency;
- a JSON snapshot file (per-position currency + an fx map), for days TWS
  is closed or for accounts at other brokers.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .models import ASSET_CLASS, Holding, ProfileAnswers, TargetPortfolio
from .named_portfolios import DEFAULT_SLUG, create_portfolio, open_store, prepare_store, slugify

logger = logging.getLogger(__name__)

_WEIGHT_Q = Decimal("0.000001")
#: below this share of the account a position is dust and skipped (0.1%)
DUST_WEIGHT = Decimal("0.001")


class SnapshotError(ValueError):
    """A malformed snapshot — the importer refuses instead of guessing."""


@dataclass
class ImportedPosition:
    """One real holding; ``market_value`` in the account base currency."""

    symbol: str
    market_value: Decimal
    quantity: Decimal = Decimal("0")
    avg_price: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        self.symbol = self.symbol.strip().upper()


@dataclass
class Snapshot:
    """A captured account, everything already in the base currency."""

    base_currency: str = "EUR"
    cash: Decimal = Decimal("0")
    positions: list[ImportedPosition] = field(default_factory=list)
    captured_at: str = ""


@dataclass
class ImportReport:
    """What the import wrote, plus everything it refused to hide."""

    slug: str
    version: int
    base_currency: str
    total_value: Decimal
    cash: Decimal
    holdings: list[Holding]
    skipped: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _dec(value: Any, what: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SnapshotError(f"{what}: not a number ({value!r})") from exc


def _to_base(value: Any, currency: str, base: str, fx: dict[str, Decimal], what: str) -> Decimal:
    amount = _dec(value, what)
    if currency == base:
        return amount
    rate = fx.get(currency)
    if rate is None:
        raise SnapshotError(f"{what}: currency {currency} has no fx rate to {base}")
    return amount * rate


def load_snapshot(path: Path) -> Snapshot:
    """Parse a JSON snapshot into base-currency positions and cash.

    Expected shape::

        {
          "base_currency": "EUR",
          "captured_at": "2026-10-29T17:18",
          "fx": {"USD": "1.12"},              # price of 1 foreign unit in base
          "cash": [{"currency": "EUR", "value": "562"}],
          "positions": [
            {"symbol": "VHYL", "market_value": "41156", "currency": "EUR"},
            {"symbol": "VZ", "quantity": "111.7", "price": "43.70",
             "currency": "USD"}
          ]
        }

    ``market_value`` wins when present; otherwise quantity × price. Every
    non-base currency (positions and cash alike) must have an fx rate.
    """
    try:
        raw = json.loads(Path(path).read_text())
    except OSError as exc:
        raise SnapshotError(f"cannot read snapshot: {exc}") from exc
    except ValueError as exc:
        raise SnapshotError(f"snapshot is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise SnapshotError("snapshot root must be a JSON object")

    base = str(raw.get("base_currency", "EUR")).strip().upper() or "EUR"
    fx = {
        str(cur).strip().upper(): _dec(rate, f"fx[{cur}]")
        for cur, rate in (raw.get("fx") or {}).items()
    }

    cash_raw = raw.get("cash", 0)
    if isinstance(cash_raw, list):
        cash = sum(
            (
                _to_base(
                    entry.get("value", 0),
                    str(entry.get("currency", base)).upper(),
                    base,
                    fx,
                    f"cash {entry.get('currency', base)}",
                )
                for entry in cash_raw
            ),
            Decimal("0"),
        )
    else:
        cash = _to_base(cash_raw, base, base, fx, "cash")

    positions: list[ImportedPosition] = []
    rows = raw.get("positions")
    if not isinstance(rows, list) or not rows:
        raise SnapshotError("snapshot has no positions list")
    for row in rows:
        if not isinstance(row, dict) or not row.get("symbol"):
            raise SnapshotError(f"position row without symbol: {row!r}")
        symbol = str(row["symbol"]).strip().upper()
        currency = str(row.get("currency", base)).strip().upper()
        quantity = _dec(row.get("quantity", 0), f"{symbol} quantity")
        price = _dec(row.get("price", row.get("avg_price", 0)), f"{symbol} price")
        if row.get("market_value") is not None:
            market_value = _to_base(
                row["market_value"], currency, base, fx, f"{symbol} market_value"
            )
        elif quantity and price:
            market_value = _to_base(quantity * price, currency, base, fx, f"{symbol} value")
        else:
            raise SnapshotError(f"{symbol}: needs market_value, or quantity + price (got neither)")
        if market_value <= 0:
            raise SnapshotError(
                f"{symbol}: non-positive market value {market_value} — long-only import"
            )
        positions.append(
            ImportedPosition(
                symbol=symbol,
                market_value=market_value,
                quantity=quantity,
                avg_price=price,
            )
        )

    return Snapshot(
        base_currency=base,
        cash=cash,
        positions=positions,
        captured_at=str(raw.get("captured_at", "")),
    )


def to_holdings(
    positions: list[ImportedPosition],
    cash: Decimal,
    min_weight: Decimal = DUST_WEIGHT,
) -> tuple[list[Holding], list[dict[str, str]], Decimal]:
    """Real positions → target holdings.

    Weights are shares of the WHOLE account (positions + cash), the same
    denominator :func:`drift.compute_drift` uses, so an imported target
    and the live account can be compared line by line. Cash keeps the
    remainder: holdings sum to ``1 - cash/total``.
    """
    total = sum((p.market_value for p in positions), Decimal("0")) + cash
    if total <= 0:
        raise SnapshotError("account total is zero — nothing to import")
    holdings: list[Holding] = []
    skipped: list[dict[str, str]] = []
    for position in sorted(positions, key=lambda p: p.market_value, reverse=True):
        weight = (position.market_value / total).quantize(_WEIGHT_Q)
        if weight < min_weight:
            skipped.append(
                {
                    "symbol": position.symbol,
                    "why": f"dust: {weight * 100:.3f}% of account (< {min_weight * 100:.2f}%)",
                }
            )
            continue
        holdings.append(
            Holding(
                symbol=position.symbol,
                weight=weight,
                rationale=f"Imported live position — {weight * 100:.1f}% of the account at import day.",
            )
        )
    return holdings, skipped, total


def portfolio_warnings(holdings: list[Holding], target: TargetPortfolio) -> list[str]:
    """Honest-report the rules the real portfolio breaks (never fixes)."""
    warnings: list[str] = []
    for holding in holdings:
        pct = holding.weight * Decimal("100")
        if pct > target.max_position_pct:
            warnings.append(
                f"{holding.symbol} {pct:.1f}% exceeds the {target.max_position_pct}% "
                "single-position cap of this risk level"
            )
    equity = sum(
        (h.weight for h in holdings if ASSET_CLASS.get(h.symbol, "equity") == "equity"),
        Decimal("0"),
    )
    if equity * Decimal("100") > target.equity_max_pct:
        warnings.append(
            f"equity share {equity * 100:.1f}% exceeds the {target.equity_max_pct}% "
            "ceiling of this risk level"
        )
    return warnings


async def import_portfolio(
    name: str,
    snapshot: Snapshot,
    risk_level: str = "aggressive",
    objective: str = "BALANCED_GROWTH",
    min_weight: Decimal = DUST_WEIGHT,
) -> ImportReport:
    """Write the snapshot as the active target of a NEW named portfolio.

    Refuses the default slug ``main`` — importing must never replace the
    default engine's target, the same boundary the paper loop enforces.
    """
    slug = slugify(name)
    if slug == DEFAULT_SLUG:
        raise ValueError(
            "refusing to import into the default portfolio 'main' — pass a distinct --name"
        )
    holdings, skipped, total = to_holdings(snapshot.positions, snapshot.cash, min_weight)

    target = TargetPortfolio(
        source="import",
        strategy_name="live_import",
        decision_status="IMPORTED",
        holdings=holdings,
        profile=ProfileAnswers(objective=objective, risk_level=risk_level),
    )
    target.settings_from_risk_level()

    create_portfolio(
        name,
        strategy_name="live_import",
        decision_status="IMPORTED",
        initial_cash=total,
    )
    engine, store = open_store(slug)
    try:
        await prepare_store(engine)
        await store.save_target(target)
    finally:
        await engine.dispose()
    logger.info(
        "Imported portfolio '%s' (%s): v%s, %s holdings, total %s %s",
        name,
        slug,
        target.version,
        len(holdings),
        total,
        snapshot.base_currency,
    )
    return ImportReport(
        slug=slug,
        version=target.version,
        base_currency=snapshot.base_currency,
        total_value=total,
        cash=snapshot.cash,
        holdings=holdings,
        skipped=skipped,
        warnings=portfolio_warnings(holdings, target),
    )
