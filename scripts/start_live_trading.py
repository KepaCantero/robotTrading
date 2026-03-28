#!/usr/bin/env python3
"""
Live Trading CLI - Command-line interface for algo trading operations.

This script provides the main entry point for live trading with:
- Configuration validation
- Broker connection testing
- Trading bridge start/stop
- Manual order placement
- Position monitoring
- Risk status checking
"""
import asyncio
import argparse
import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.compliance_engine import get_compliance_engine
from app.services.live_trading.trading_bridge_orchestrator import get_trading_bridge_orchestrator
from app.services.live_trading.broker_connector import get_broker_connector, OrderSide

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('logs/live_trading.log')],
)
logger = logging.getLogger(__name__)


class LiveTradingCLI:
    """Command-line interface for live trading operations."""

    def __init__(self):
        self.compliance_engine = get_compliance_engine(enable_logging=True)
        self.bridge = get_trading_bridge_orchestrator()
        self.broker = get_broker_connector()
        self.is_running = False

    async def start_trading(self) -> bool:
        """Start the trading bridge and begin monitoring for alerts."""
        try:
            logger.info("Starting live trading...")

            # Validate configuration
            if not await self.validate_config():
                logger.error("Configuration validation failed")
                return False

            # Test broker connection
            if not await self.validate_broker_connection():
                logger.error("Broker connection test failed")
                return False

            # Check kill switch status
            if self.compliance_engine.check_kill_switch():
                logger.error("KILL SWITCH ACTIVE - Cannot start trading")
                return False

            # Start trading bridge
            success = await self.bridge.start()
            if success:
                self.is_running = True
                logger.info("Live trading started successfully")
                logger.info(f"Portfolio value: ${await self._get_portfolio_value():,.2f}")
                return True
            else:
                logger.error("Failed to start trading bridge")
                return False

        except Exception as e:
            logger.error(f"Error starting trading: {e}")
            return False

    async def stop_trading(self) -> bool:
        """Stop the trading bridge."""
        try:
            logger.info("Stopping live trading...")
            success = await self.bridge.stop()
            if success:
                self.is_running = False
                logger.info("Live trading stopped")
                return True
            else:
                logger.error("Failed to stop trading bridge")
                return False
        except Exception as e:
            logger.error(f"Error stopping trading: {e}")
            return False

    async def validate_config(self) -> bool:
        """Validate trading configuration."""
        try:
            logger.info("Validating configuration...")

            # Check if broker is configured
            account = await self.broker.get_account_info()
            if not account:
                logger.error("Broker account not accessible")
                return False

            logger.info("Configuration validation: PASSED")
            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    async def validate_broker_connection(self) -> bool:
        """Test broker connection."""
        try:
            logger.info("Testing broker connection...")

            # Get account info
            account = await self.broker.get_account_info()
            if not account:
                logger.error("Cannot retrieve account info")
                return False

            logger.info(f"Account ID: {account.get('account_id', 'N/A')}")
            logger.info(f"Buying power: ${account.get('buying_power', 0):,.2f}")

            # Get portfolio value
            portfolio_value = await self.broker.calculate_portfolio_value()
            logger.info(f"Portfolio value: ${portfolio_value:,.2f}")

            logger.info("Broker connection: PASSED")
            return True

        except Exception as e:
            logger.error(f"Broker connection test failed: {e}")
            return False

    async def place_order(self, symbol: str, side: str, quantity: int, price: float = None) -> bool:
        """Place a manual order."""
        try:
            logger.info(f"Placing {side.upper()} order: {quantity} shares of {symbol}")

            # Convert side
            order_side = OrderSide.BUY if side.upper() == "BUY" else OrderSide.SELL

            # Convert price
            limit_price = Decimal(str(price)) if price else None

            # Use bridge to execute (includes risk validation)
            from app.services.live_trading.alert_to_trade_mapper import TradeSignal, TradeSignalType
            from app.services.alerting_system import AlertSeverity
            from app.services.live_trading.broker_connector import OrderType

            signal = TradeSignal(
                signal_id=f"manual_{datetime.now().timestamp()}",
                alert_id=f"manual_alert_{datetime.now().timestamp()}",
                alert_rule_id="manual_cli",
                symbol=symbol.upper(),
                signal_type=TradeSignalType.LONG,
                order_side=order_side,
                order_type=OrderType.MARKET if not limit_price else OrderType.LIMIT,
                quantity=Decimal(str(quantity)),
                price=limit_price,
                severity=AlertSeverity.WARNING,
                reason="Manual order via CLI",
            )

            # Execute via compliance engine (includes all risk checks)
            result = await self.compliance_engine.execute_trade(
                signal=signal,
                portfolio_value=Decimal(str(await self._get_portfolio_value())),
            )

            if result.success:
                logger.info(f"Order placed successfully: {result.order_id}")
                return True
            else:
                logger.error(f"Order failed: {result.error}")
                return False

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return False

    async def check_risk_status(self) -> dict:
        """Check current risk status."""
        try:
            logger.info("Checking risk status...")

            # Get daily P&L summary
            pnl_summary = self.compliance_engine.get_daily_pnl_summary()

            # Get SLO metrics
            slo_metrics = self.compliance_engine.get_slo_metrics()

            # Get system status
            system_status = self.compliance_engine.get_system_status()

            status_report = {
                "daily_pnl": pnl_summary,
                "slo_metrics": slo_metrics,
                "system_status": system_status,
                "kill_switch_active": self.compliance_engine.check_kill_switch(),
            }

            # Print summary
            print("\n" + "=" * 60)
            print("RISK STATUS REPORT")
            print("=" * 60)
            print(f"Kill Switch Active: {status_report['kill_switch_active']}")
            print(
                f"Daily P&L: ${pnl_summary['total_pnl']:,.2f} ({pnl_summary['daily_return_pct']:.2%})"
            )
            print(f"Total Trades: {pnl_summary['total_trades']}")
            print(f"Win Rate: {pnl_summary['win_rate']:.1%}")
            print(f"SLO Compliance: {slo_metrics['slo_compliance_rate']:.1%}")
            print(
                f"Systems Available: {system_status['availability']['available_systems']}/{system_status['availability']['total_systems']}"
            )
            print("=" * 60 + "\n")

            return status_report

        except Exception as e:
            logger.error(f"Error checking risk status: {e}")
            return {}

    async def show_positions(self) -> list:
        """Show current positions."""
        try:
            logger.info("Retrieving positions...")
            positions = await self.broker.get_positions()
            return positions
        except Exception as e:
            logger.error(f"Error retrieving positions: {e}")
            return []

    async def _get_portfolio_value(self) -> float:
        """Get current portfolio value."""
        try:
            return float(await self.broker.calculate_portfolio_value())
        except Exception:
            return float(self.compliance_engine._starting_capital)


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="AlgoTrading Live Trading CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Start command
    subparsers.add_parser('start', help='Start live trading')

    # Stop command
    subparsers.add_parser('stop', help='Stop live trading')

    # Validate command
    subparsers.add_parser('validate', help='Validate configuration')

    # Test broker command
    subparsers.add_parser('test-broker', help='Test broker connection')

    # Risk status command
    subparsers.add_parser('risk-status', help='Check risk status')

    # Positions command
    subparsers.add_parser('positions', help='Show current positions')

    # Order command
    order_parser = subparsers.add_parser('order', help='Place manual order')
    order_parser.add_argument('symbol', help='Stock symbol')
    order_parser.add_argument('side', choices=['buy', 'sell'], help='Order side')
    order_parser.add_argument('quantity', type=int, help='Number of shares')
    order_parser.add_argument('--price', type=float, help='Limit price (for limit orders)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = LiveTradingCLI()

    if args.command == 'start':
        success = await cli.start_trading()
        if success:
            logger.info("Trading started. Press Ctrl+C to stop.")
            try:
                # Keep running
                while cli.is_running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                await cli.stop_trading()

    elif args.command == 'stop':
        await cli.stop_trading()

    elif args.command == 'validate':
        valid = await cli.validate_config()
        sys.exit(0 if valid else 1)

    elif args.command == 'test-broker':
        valid = await cli.validate_broker_connection()
        sys.exit(0 if valid else 1)

    elif args.command == 'risk-status':
        await cli.check_risk_status()

    elif args.command == 'positions':
        positions = await cli.show_positions()
        if positions:
            print("\nCurrent Positions:")
            print("-" * 60)
            for pos in positions:
                print(
                    f"{pos.get('symbol', 'N/A')}: {pos.get('quantity', 0)} shares @ ${pos.get('avg_price', 0):.2f}"
                )
            print("-" * 60 + "\n")

    elif args.command == 'order':
        success = await cli.place_order(args.symbol, args.side, args.quantity, args.price)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
