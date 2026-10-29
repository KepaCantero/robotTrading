#!/usr/bin/env python3
"""Import a real portfolio as the baseline target of a NEW named portfolio.

Sources (pick exactly one):
- --from-ibkr : the account TWS is logged into, read-only
  (IbkrAdapter(read_only=True) — this script cannot place orders)
- --from-json : a snapshot file (see app/services/portfolio_management/
  import_snapshot.py for the format) — works without TWS

The import writes ONLY the new portfolio's own database
(data/portfolio_management_<slug>.db + meta), never 'main'. Risk caps are
applied as rebalancing rules and their violations REPORTED — a snapshot
describes reality, it does not fix it.

  .venv/bin/python scripts/import_portfolio.py --name "Live IBKR" \
      --from-json data/import/live_ibkr_20261029.json
  .venv/bin/python scripts/import_portfolio.py --name "Live IBKR" \
      --from-ibkr --port 7496

Exit codes: 0 imported · 1 broker/connection problem · 2 wrong account ·
3 snapshot or app-side error.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.portfolio_management.import_snapshot import (  # noqa: E402
    ImportedPosition,
    ImportReport,
    Snapshot,
    SnapshotError,
    import_portfolio,
    load_snapshot,
)
from app.services.portfolio_management.models import OBJECTIVES, RISK_SETTINGS  # noqa: E402

#: distinct from the executor (77001), the viewer (78002) and the
#: comparer (78003) so all four sessions can coexist on the same TWS
IMPORT_CLIENT_ID = 78004


async def _snapshot_from_ibkr(args: argparse.Namespace) -> Snapshot:
    from app.services.live_trading.broker_adapters.ibkr_adapter import IbkrAdapter

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
        sys.exit(1)
    try:
        account = adapter.account
        assert account is not None
        if args.expect_account and account.account_id != args.expect_account:
            print(
                f"ERROR: connected to {account.account_id} but expected {args.expect_account}",
                file=sys.stderr,
            )
            sys.exit(2)
        await adapter.reconcile()
        positions = await adapter.get_positions()
        unmarked = [p.symbol for p in positions if p.market_value <= 0]
        if unmarked:
            print(
                "ERROR: no broker marks for " + ", ".join(unmarked) + " — wait for "
                "TWS to price them (or import from a snapshot instead)",
                file=sys.stderr,
            )
            sys.exit(1)
        mode = "PAPER" if adapter.is_paper_trading() else "LIVE (read-only)"
        print(f"Broker: {account.account_id} — {mode}")
        return Snapshot(
            base_currency=account.currency,
            cash=account.cash_available or Decimal("0"),
            positions=[
                ImportedPosition(
                    symbol=p.symbol,
                    market_value=p.market_value,
                    quantity=p.quantity,
                    avg_price=p.avg_price,
                )
                for p in positions
            ],
        )
    finally:
        await adapter.disconnect()


def _print_report(report: ImportReport) -> None:
    print(
        f"\nImported '{report.slug}' v{report.version}: "
        f"{len(report.holdings)} holdings, cash {report.cash:,.2f} "
        f"{report.base_currency}, total {report.total_value:,.2f} {report.base_currency}"
    )
    print(f"\n{'SYMBOL':<8} {'WEIGHT':>7}")
    for holding in report.holdings:
        print(f"{holding.symbol:<8} {holding.weight * 100:>6.2f}%")
    for row in report.skipped:
        print(f"  skipped {row['symbol']}: {row['why']}")
    if report.warnings:
        print("\nRule violations REPORTED (not fixed) — this is what you hold:")
        for warning in report.warnings:
            print(f"  ! {warning}")
    print(
        f"\nNext: .venv/bin/python scripts/compare_live_portfolio.py "
        f"--slug {report.slug} --port 7496"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-ibkr", action="store_true", help="pull read-only from TWS")
    source.add_argument("--from-json", type=Path, help="snapshot file path")
    parser.add_argument("--name", required=True, help="portfolio name (not 'main')")
    parser.add_argument(
        "--risk",
        default="aggressive",
        choices=sorted(RISK_SETTINGS),
        help="risk level whose rebalancing rules apply (default: aggressive — "
        "the level whose caps a real account is least likely to break)",
    )
    parser.add_argument("--objective", default="BALANCED_GROWTH", choices=sorted(OBJECTIVES))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7497, help="7497 paper, 7496 live")
    parser.add_argument("--client-id", type=int, default=IMPORT_CLIENT_ID)
    parser.add_argument("--expect-account", default=None)
    parser.add_argument("--debug", action="store_true")
    return parser


async def _run(args: argparse.Namespace) -> int:
    if args.from_ibkr:
        snapshot = await _snapshot_from_ibkr(args)
    else:
        snapshot = load_snapshot(args.from_json)
    report = await import_portfolio(
        name=args.name,
        snapshot=snapshot,
        risk_level=args.risk,
        objective=args.objective,
    )
    _print_report(report)
    return 0


def main() -> int:
    logging.basicConfig(
        level=logging.DEBUG if "--debug" in sys.argv else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args()
    try:
        return asyncio.run(_run(args))
    except SnapshotError as exc:
        print(f"ERROR: snapshot: {exc}", file=sys.stderr)
        return 3
    except ValueError as exc:  # refused import (e.g. name 'main')
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
