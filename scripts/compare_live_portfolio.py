#!/usr/bin/env python3
"""Compare an app portfolio's TARGET weights against a live IBKR account.

Read-only on both sides:
- app side: the named portfolio's active target (data/portfolio_management_<slug>.db)
- broker side: whatever TWS is logged into, via IbkrAdapter(read_only=True)
  — this script cannot place, modify or cancel any order

The report is a visual diff: target weight vs broker-marked weight per
symbol, plus live holdings the target does not include. It computes what a
rebalance WOULD move, but never suggests sending anything — live order
paths do not exist in this codebase.

  .venv/bin/python scripts/compare_live_portfolio.py \
      --slug portfolio-max-dividends-01 --port 7496

Exit codes: 0 report shown · 1 connection/refusal · 2 wrong account ·
3 app portfolio not found.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sqlite3
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.services.live_trading.broker_adapters.ibkr_adapter import IbkrAdapter

#: distinct from the executor (77001) and the viewer (78002) so all three
#: sessions can coexist on the same TWS
COMPARE_CLIENT_ID = 78003

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Target:
    slug: str
    status: str
    holdings: dict[str, Decimal]  # symbol → weight
    profile: str


def _load_target(slug: str) -> Target:
    db = REPO_ROOT / "data" / f"portfolio_management_{slug}.db"
    if not db.exists():
        print(f"ERROR: no app portfolio DB for slug '{slug}' at {db}", file=sys.stderr)
        sys.exit(3)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT decision_status, profile_json, holdings_json "
            "FROM target_portfolios WHERE is_active = 1 "
            "ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    finally:
        con.close()
    if row is None:
        print(f"ERROR: slug '{slug}' has no active target portfolio", file=sys.stderr)
        sys.exit(3)
    status, profile_json, holdings_json = row
    profile = json.loads(profile_json)
    profile_txt = ", ".join(
        str(profile.get(k, ""))
        for k in ("objective", "risk_level", "tax_province")
        if profile.get(k)
    )
    holdings = {
        str(h["symbol"]).upper(): Decimal(str(h["weight"])) for h in json.loads(holdings_json)
    }
    return Target(slug=slug, status=status, holdings=holdings, profile=profile_txt)


def _pct(weight: Decimal) -> str:
    return f"{(weight * Decimal(100)):.1f}%"


async def _report(args: argparse.Namespace, target: Target) -> int:
    adapter = IbkrAdapter(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        read_only=True,
    )
    try:
        await adapter.connect()
    except Exception as exc:  # noqa: BLE001 - report any refusal honestly
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    try:
        account = adapter.account
        assert account is not None
        if args.expect_account and account.account_id != args.expect_account:
            print(
                f"ERROR: connected to {account.account_id} but expected {args.expect_account}",
                file=sys.stderr,
            )
            return 2

        await adapter.reconcile()
        positions = {p.symbol: p for p in await adapter.get_positions()}
        net_liq = account.portfolio_value or Decimal("0")
        marked_total = sum((p.market_value for p in positions.values()), Decimal("0"))
        base = marked_total if marked_total > 0 else net_liq  # weight denominator

        mode = "PAPER" if adapter.is_paper_trading() else "LIVE (read-only)"
        print(f"App portfolio : {target.slug} ({target.status}; {target.profile})")
        print(f"Broker        : {account.account_id} — {mode}")
        print(
            f"Account value : {net_liq:,.2f} {account.currency} "
            f"(positions marked: {marked_total:,.2f})"
        )

        live_weights = {
            sym: (p.market_value / base if base else Decimal("0")) for sym, p in positions.items()
        }
        cash_weight = (account.cash_available or Decimal("0")) / base if base else Decimal("0")

        symbols = sorted(target.holdings | set(positions))
        print(f"\n{'SYMBOL':<8} {'TARGET':>8} {'BROKER':>8} {'GAP':>9}  NOTE")
        for sym in symbols:
            tgt = target.holdings.get(sym)
            liv = live_weights.get(sym, Decimal("0"))
            if tgt is None:
                print(f"{sym:<8} {'—':>8} {_pct(liv):>8} {_pct(liv):>9}  NOT IN TARGET")
                continue
            gap = tgt - liv
            note = "HELD BY BOTH" if sym in positions else "MISSING IN BROKER"
            if sym in positions:
                note += f" (qty {positions[sym].quantity})"
            print(f"{sym:<8} {_pct(tgt):>8} {_pct(liv):>8} {gap * Decimal(100):>+8.1f}pp {note}")

        print(f"{'CASH':<8} {'—':>8} {_pct(cash_weight):>8}")
        overlap = len(set(target.holdings) & set(positions))
        print(
            f"\nOverlap: {overlap}/{len(target.holdings)} target symbols held in the "
            f"broker account; {len(set(positions) - set(target.holdings))} broker-only "
            "symbols."
        )
        if adapter.is_paper_trading() and not args.allow_paper:
            print(
                "\nNOTE: this is the PAPER session (port 7497). To compare against "
                "your LIVE account, open TWS logged into it and pass --port 7496."
            )
        return 0
    finally:
        await adapter.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare an app portfolio's target weights vs a live IBKR "
        "account (read-only; orders are impossible by design)",
    )
    parser.add_argument(
        "--slug", required=True, help="app portfolio slug, e.g. portfolio-max-dividends-01"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--port", type=int, default=7497, help="7497 paper session, 7496 live session"
    )
    parser.add_argument("--client-id", type=int, default=COMPARE_CLIENT_ID)
    parser.add_argument("--expect-account", default=None)
    parser.add_argument(
        "--allow-paper", action="store_true", help="suppress the paper-session note"
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    target = _load_target(args.slug)
    return asyncio.run(_report(args, target))


if __name__ == "__main__":
    sys.exit(main())
