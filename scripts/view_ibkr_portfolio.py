#!/usr/bin/env python3
"""Read-only IBKR portfolio viewer (user-requested live viewing, 29-10).

Connects to a running TWS / IB Gateway session and prints the
broker-confirmed account summary and open positions. The adapter is
constructed with ``read_only=True``, so this script CANNOT place, modify
or cancel orders — those methods raise before touching the socket.

It sees whatever account TWS is logged into: port 7497 = TWS paper
session, port 7496 = TWS live session. The port selects the session you
already opened; this script never logs anything in.

  .venv/bin/python scripts/view_ibkr_portfolio.py                    # paper 7497
  .venv/bin/python scripts/view_ibkr_portfolio.py --port 7496 \
      --expect-account U1234567                                     # live session

Exit codes: 0 shown · 1 connection refused/unreachable · 2 account mismatch.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from decimal import Decimal

from app.services.live_trading.broker_adapters.ibkr_adapter import IbkrAdapter

#: distinct from the executor's DEFAULT_CLIENT_ID (77001) so the viewer and
#: a running paper executor can coexist on the same TWS
VIEWER_CLIENT_ID = 78002


def _money(value: Decimal | None, currency: str) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f} {currency}"


async def _run(args: argparse.Namespace) -> int:
    adapter = IbkrAdapter(
        host=args.host,
        port=args.port,
        client_id=args.client_id,
        read_only=True,  # hard contract of this script — no order path exists
    )
    try:
        await adapter.connect()
    except Exception as exc:  # noqa: BLE001 - report any refusal honestly
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        account = adapter.account
        assert account is not None  # connect() syncs it before returning
        if args.expect_account and account.account_id != args.expect_account:
            print(
                f"ERROR: connected to {account.account_id} but expected "
                f"{args.expect_account} — refusing to show the wrong session",
                file=sys.stderr,
            )
            return 2

        mode = "PAPER" if adapter.is_paper_trading() else "LIVE (read-only)"
        print(f"IBKR account {account.account_id} — {mode}")
        print(f"  Net liquidation : {_money(account.portfolio_value, account.currency)}")
        print(f"  Cash            : {_money(account.cash_available, account.currency)}")
        print(f"  Buying power    : {_money(account.buying_power, account.currency)}")

        positions = await adapter.get_positions()
        print(f"\nPositions ({len(positions)}):")
        if not positions:
            print("  (no open positions)")
        else:
            print(f"  {'SYMBOL':<10} {'QTY':>12} {'AVG COST':>14}")
            for pos in sorted(positions, key=lambda p: p.symbol):
                print(f"  {pos.symbol:<10} {pos.quantity:>12} {pos.avg_price:>14}")

        # executions the broker knows but this session never placed (e.g.
        # manual TWS trades) — informational, never acted upon
        divergences = await adapter.reconcile()
        notes = divergences.get("orders", [])
        if notes:
            print(f"\nBroker-side activity this session did not place ({len(notes)}):")
            for note in notes[:10]:
                print(f"  · {note}")
        return 0
    finally:
        await adapter.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="View an IBKR account read-only (orders are impossible by design)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="TWS host (default 127.0.0.1)")
    parser.add_argument(
        "--port",
        type=int,
        default=7497,
        help="TWS socket: 7497 paper session, 7496 live session (default 7497)",
    )
    parser.add_argument(
        "--client-id",
        type=int,
        default=VIEWER_CLIENT_ID,
        help=f"API client id (default {VIEWER_CLIENT_ID})",
    )
    parser.add_argument(
        "--expect-account",
        default=None,
        help="refuse to display anything unless this exact account id answers",
    )
    parser.add_argument("--debug", action="store_true", help="verbose ib_insync logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
