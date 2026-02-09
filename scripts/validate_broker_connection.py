#!/usr/bin/env python3
"""
Broker Connection Validation Script

Tests broker connection and retrieves account information.
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.live_trading.broker_connector import get_broker_connector

async def validate_broker_connection():
    """Validate broker connection and retrieve account info."""
    print("Testing broker connection...")
    print("=" * 60)

    try:
        broker = get_broker_connector()
        print("Broker connector initialized: OK")

        # Get account info
        print("\nRetrieving account information...")
        account = await broker.get_account_info()

        if not account:
            print("ERROR: Cannot retrieve account information")
            return False

        print(f"Account ID: {account.get('account_id', 'N/A')}")
        print(f"Account type: {account.get('account_type', 'N/A')}")
        print(f"Buying power: ${account.get('buying_power', 0):,.2f}")
        print(f"Cash balance: ${account.get('cash_balance', 0):,.2f}")

        # Get portfolio value
        print("\nRetrieving portfolio information...")
        portfolio_value = await broker.calculate_portfolio_value()
        print(f"Portfolio value: ${portfolio_value:,.2f}")

        # Get positions
        print("\nRetrieving positions...")
        positions = await broker.get_positions()
        print(f"Number of positions: {len(positions)}")

        if positions:
            print("\nCurrent positions:")
            for pos in positions[:10]:  # Show first 10
                symbol = pos.get('symbol', 'N/A')
                quantity = pos.get('quantity', 0)
                avg_price = pos.get('avg_price', 0)
                current_price = pos.get('current_price', 0)
                pnl = pos.get('unrealized_pnl', 0)
                print(f"  {symbol}: {quantity} shares @ ${avg_price:.2f} | P&L: ${pnl:,.2f}")

        # Test order status query
        print("\nTesting order status query...")
        open_orders = await broker.get_open_orders()
        print(f"Open orders: {len(open_orders)}")

        print("\n" + "=" * 60)
        print("Broker connection test: PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        print("\n" + "=" * 60)
        print("Broker connection test: FAILED")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = asyncio.run(validate_broker_connection())
    sys.exit(0 if success else 1)
