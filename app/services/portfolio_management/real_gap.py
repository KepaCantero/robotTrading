"""The live account vs the adopted target — gap, buy path, sell cost.

The /portfolio page governs a PAPER account; the owner also holds a REAL
broker account (tracked in his own ``portfolio`` project, fed by IBKR
activity statements). This module connects the two without ever touching
the real broker:

- import real holdings by pasting the ``holdings.csv`` of the portfolio
  project (ticker, quantity, avg cost — the paste is parsed, not linked);
- price every position from the repo's own corpus (last real close; USD
  positions converted with the ECB reference rate, no guessed fx);
- show the GAP against the active target per sleeve, the "outside the
  target" block (frozen legacy positions), a buy-only path for new money
  (the dilution philosophy: new cash closes the underweights, nothing is
  sold), and an ESTIMATED tax cost should the owner choose to trim an
  overweight (average-cost basis, Spain savings rates, 2-month rule
  flagged — a preview, never advice).

Everything here is read-only against the outside world and per-slug
persisted under ``data/real_holdings_<slug>.json``.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .models import Holding, LotSnapshot
from .tax import SpainRebalanceTax

logger = logging.getLogger(__name__)

D = Decimal
_DATA_DIR = Path("data")
_FX_CSV = _DATA_DIR / "fx" / "ecb_exr.csv"
_CORPUS = _DATA_DIR / "historical"

#: corpus symbols quoted in EUR. Suffixed listings (.DE/.AS/…) are EUR by
#: construction; this set covers the unsuffixed UCITS tickers the Yahoo
#: CSV import wrote without an exchange suffix.
_EUR_SYMBOLS = {
    "VWCE",
    "VHYL",
    "IBTS",
    "IDVY",
    "QDIV",
    "EUNL",
    "IBGS",
}
_EUR_SUFFIXES = (".DE", ".AS", ".MC", ".MI", ".PA", ".SW")

#: a buy allocation below this € is dust and folded into the last sleeve
_BUY_DUST_EUR = Decimal("1")


@dataclass
class RealPosition:
    """One real holding as pasted (quantity + average cost in EUR)."""

    symbol: str
    quantity: Decimal
    avg_cost_eur: Decimal

    def __post_init__(self) -> None:
        self.symbol = self.symbol.strip().upper()


@dataclass
class RealSnapshot:
    """The whole live account, stored verbatim after import."""

    captured_at: str = ""
    cash_eur: Decimal = Decimal("0")
    fx_usd_eur: Decimal | None = None
    positions: list[RealPosition] = field(default_factory=list)


@dataclass
class GapRow:
    """One target sleeve vs the live account."""

    symbol: str
    target_weight: Decimal  # 0..1
    live_value_eur: Decimal | None  # None = not priced locally
    live_weight: Decimal | None  # 0..1
    gap_eur: Decimal | None  # target € − live € (positive → buy)


@dataclass
class TrimCost:
    """Estimated cost of selling a sleeve's excess (average-cost basis)."""

    symbol: str
    excess_value_eur: Decimal
    quantity: Decimal
    est_tax_eur: Decimal
    marginal_rate: Decimal
    notes: list[str] = field(default_factory=list)


@dataclass
class GapReport:
    """Everything the live-gap card shows, pre-computed in one pass."""

    total_eur: Decimal
    cash_eur: Decimal
    fx_usd_eur: Decimal | None
    rows: list[GapRow] = field(default_factory=list)
    outside_target: list[tuple[str, Decimal]] = field(default_factory=list)  # (symbol, €)
    unpriced: list[str] = field(default_factory=list)  # symbols with no local CSV
    price_date: str = ""


def parse_holdings_paste(text: str) -> tuple[list[RealPosition], Decimal, list[str]]:
    """Parse the portfolio project's holdings.csv columns 1-3.

    Accepts ``ticker,quantity,avg_cost_eur`` per line (extra columns are
    ignored), skips a header row, treats a ``CASH`` row as account cash.
    Returns (positions, cash_eur, skipped-lines).
    """
    positions: list[RealPosition] = []
    cash = Decimal("0")
    skipped: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        cells = [c.strip() for c in next(csv.reader([line]))]
        if len(cells) < 2 or cells[0].lower() in ("ticker", "symbol"):
            continue
        symbol = cells[0].upper()
        try:
            quantity = Decimal(cells[1])
            cost = Decimal(cells[2]) if len(cells) > 2 and cells[2] else Decimal("0")
        except (InvalidOperation, ValueError):
            skipped.append(line)
            continue
        if symbol == "CASH":
            cash += quantity  # the quantity column holds the EUR amount
            continue
        if quantity <= 0:
            skipped.append(line)
            continue
        positions.append(RealPosition(symbol=symbol, quantity=quantity, avg_cost_eur=cost))
    return positions, cash, skipped


def latest_usd_eur() -> Decimal | None:
    """Last ECB USD→EUR reference rate from the repo's own fx corpus."""
    if not _FX_CSV.exists():
        return None
    try:
        lines = _FX_CSV.read_text().strip().splitlines()
        for line in reversed(lines):
            date, currency, rate = line.split(",")
            if currency == "USD":
                eur_usd = Decimal(rate)
                if eur_usd > 0:
                    return (Decimal("1") / eur_usd).quantize(Decimal("0.0001"))
    except (OSError, ValueError, InvalidOperation):
        logger.warning("ECB fx corpus unreadable — USD positions need a manual rate")
    return None


def _last_close(symbol: str) -> tuple[Decimal, str] | None:
    """(last close, ISO date) from the corpus; None when there is no CSV."""
    path = _CORPUS / f"{symbol.upper()}.csv"
    if not path.exists():
        return None
    try:
        lines = [ln for ln in path.read_text().strip().splitlines() if ln]
        if len(lines) < 2:
            return None
        cells = lines[-1].split(",")
        return Decimal(cells[4]), cells[0]
    except (OSError, ValueError, InvalidOperation):
        return None


def _is_eur(symbol: str) -> bool:
    return symbol in _EUR_SYMBOLS or symbol.upper().endswith(_EUR_SUFFIXES)


def price_snapshot(
    snapshot: RealSnapshot, fx_usd_eur: Decimal | None = None
) -> tuple[dict[str, Decimal], Decimal, list[str], str]:
    """Price every position in EUR via the corpus.

    Returns (symbol → value_eur, total_positions_eur, unpriced, price_date).
    USD symbols without an fx rate stay unpriced — never a guessed number.
    """
    fx = fx_usd_eur or snapshot.fx_usd_eur or latest_usd_eur()
    values: dict[str, Decimal] = {}
    unpriced: list[str] = []
    price_date = ""
    for pos in snapshot.positions:
        quote = _last_close(pos.symbol)
        if quote is None:
            unpriced.append(pos.symbol)
            continue
        close, on = quote
        price_date = max(price_date, on)
        if _is_eur(pos.symbol):
            values[pos.symbol] = (pos.quantity * close).quantize(Decimal("0.01"))
        elif fx is not None:
            values[pos.symbol] = (pos.quantity * close * fx).quantize(Decimal("0.01"))
        else:
            unpriced.append(pos.symbol)
    total = sum(values.values(), Decimal("0"))
    return values, total, sorted(set(unpriced)), price_date


def compute_gap(
    holdings: list[Holding], snapshot: RealSnapshot, fx_usd_eur: Decimal | None = None
) -> GapReport:
    """Target sleeves vs the live account, plus the outside-target block."""
    values, positions_total, unpriced, price_date = price_snapshot(snapshot, fx_usd_eur)
    cash = snapshot.cash_eur
    total = positions_total + cash
    report = GapReport(
        total_eur=total,
        cash_eur=cash,
        fx_usd_eur=fx_usd_eur or snapshot.fx_usd_eur or latest_usd_eur(),
        unpriced=unpriced,
        price_date=price_date,
    )
    target_symbols = {h.symbol for h in holdings}
    held = {p.symbol for p in snapshot.positions}
    report.outside_target = sorted(
        ((sym, val) for sym, val in values.items() if sym not in target_symbols),
        key=lambda kv: (-kv[1], kv[0]),
    )
    if total <= 0:
        return report
    for holding in holdings:
        value = values.get(holding.symbol)
        if value is None and holding.symbol not in held:
            # a sleeve the account does not hold yet is a full buy gap, not
            # an unknown — only HELD-but-unpriced positions stay unknown
            value = Decimal("0")
        live_weight = (value / total).quantize(Decimal("0.0001")) if value is not None else None
        report.rows.append(
            GapRow(
                symbol=holding.symbol,
                target_weight=holding.weight,
                live_value_eur=value,
                live_weight=live_weight,
                gap_eur=(
                    (holding.weight * total - value).quantize(Decimal("0.01"))
                    if value is not None
                    else None
                ),
            )
        )
    return report


def plan_buys(report: GapReport, new_money_eur: Decimal) -> list[tuple[str, Decimal]]:
    """Spend new money on the underweights only — the dilution path.

    Allocation is proportional to each sleeve's € gap, iterating until the
    money or the gaps run out (proportional-to-gap twice-cycled is enough
    in practice; the loop caps at 20 passes). Never proposes a sell.
    """
    rows = [r for r in report.rows if r.gap_eur is not None]
    remaining = {r.symbol: r.gap_eur for r in rows if r.gap_eur > 0}
    if not remaining or new_money_eur <= 0:
        return []
    bought: dict[str, Decimal] = {sym: Decimal("0") for sym in remaining}
    money = new_money_eur
    for _ in range(20):
        open_gaps = {sym: gap for sym, gap in remaining.items() if gap > _BUY_DUST_EUR}
        if money < _BUY_DUST_EUR or not open_gaps:
            break
        pot = sum(open_gaps.values(), Decimal("0"))
        spent_this_pass = Decimal("0")
        for sym, gap in open_gaps.items():
            share = (money * gap / pot).quantize(Decimal("0.01"))
            take = min(share, remaining[sym])
            bought[sym] += take
            remaining[sym] -= take
            spent_this_pass += take
        money -= spent_this_pass
    plan = sorted(
        ((sym, amount) for sym, amount in bought.items() if amount >= _BUY_DUST_EUR),
        key=lambda kv: (-kv[1], kv[0]),
    )
    return plan


def trim_costs(
    report: GapReport,
    snapshot: RealSnapshot,
    fx_usd_eur: Decimal | None = None,
) -> list[TrimCost]:
    """Estimated tax of selling each sleeve's excess ABOVE target.

    Basis is the pasted average cost (one synthetic old lot per symbol:
    the 2-month rule can only trigger on real recent lots, which a paste
    cannot know). A preview in €, marked as an estimate.
    """
    fx = fx_usd_eur or snapshot.fx_usd_eur or latest_usd_eur()
    by_symbol = {p.symbol: p for p in snapshot.positions}
    tax = SpainRebalanceTax()
    out: list[TrimCost] = []
    for row in report.rows:
        if row.gap_eur is None or row.gap_eur >= 0 or row.live_value_eur is None:
            continue
        pos = by_symbol.get(row.symbol)
        quote = _last_close(row.symbol)
        if pos is None or quote is None or pos.quantity <= 0:
            continue
        close, _on = quote
        price_eur = close if _is_eur(row.symbol) else (close * fx if fx else None)
        if price_eur is None or price_eur <= 0:
            continue
        excess_value = -row.gap_eur
        quantity = (pos.quantity * excess_value / row.live_value_eur).quantize(
            Decimal("0.0001")
        )
        lot = LotSnapshot(
            lot_id=f"real-{row.symbol}",
            symbol=row.symbol,
            quantity=pos.quantity,
            purchase_price=pos.avg_cost_eur,
            # a paste carries no purchase dates: an old synthetic date keeps
            # the 2-month rule out of an estimate it cannot inform
            purchased_at=datetime(2000, 1, 1),
            source="real_import",
        )
        impact = tax.preview_sell(row.symbol, quantity, price_eur, [lot])
        notes = ["average-cost estimate from the pasted holdings"] + list(impact.notes)
        out.append(
            TrimCost(
                symbol=row.symbol,
                excess_value_eur=excess_value.quantize(Decimal("0.01")),
                quantity=quantity,
                est_tax_eur=impact.tax,
                marginal_rate=impact.marginal_rate,
                notes=notes,
            )
        )
    return sorted(out, key=lambda t: (-t.excess_value_eur, t.symbol))


# ── per-slug persistence (the paper-state pattern: a JSON per portfolio) ──


def _state_path(slug: str) -> Path:
    return _DATA_DIR / f"real_holdings_{slug}.json"


def save_real_holdings(slug: str, snapshot: RealSnapshot) -> Path:
    path = _state_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "captured_at": snapshot.captured_at or datetime.utcnow().isoformat(timespec="seconds"),
        "cash_eur": str(snapshot.cash_eur),
        "fx_usd_eur": str(snapshot.fx_usd_eur) if snapshot.fx_usd_eur else None,
        "positions": [
            {
                "symbol": p.symbol,
                "quantity": str(p.quantity),
                "avg_cost_eur": str(p.avg_cost_eur),
            }
            for p in snapshot.positions
        ],
    }
    path.write_text(json.dumps(payload, indent=2))
    return path


def load_real_holdings(slug: str) -> RealSnapshot | None:
    path = _state_path(slug)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text())
        return RealSnapshot(
            captured_at=str(raw.get("captured_at", "")),
            cash_eur=Decimal(str(raw.get("cash_eur", "0"))),
            fx_usd_eur=(
                Decimal(str(raw["fx_usd_eur"])) if raw.get("fx_usd_eur") else None
            ),
            positions=[
                RealPosition(
                    symbol=str(p["symbol"]),
                    quantity=Decimal(str(p["quantity"])),
                    avg_cost_eur=Decimal(str(p.get("avg_cost_eur", "0"))),
                )
                for p in raw.get("positions", [])
            ],
        )
    except (ValueError, KeyError, InvalidOperation) as exc:
        logger.warning("real holdings file for '%s' unreadable: %s", slug, exc)
        return None
