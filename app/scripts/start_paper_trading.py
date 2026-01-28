#!/usr/bin/env python3
"""
AlgoTrading - Paper Trading Startup Script

This script initializes and starts the paper trading system with:
- Paper trading service
- Market data connection
- API server
- Dashboard

Usage:
    python -m app.scripts.start_paper_trading

    Or with custom parameters:
    python -m app.scripts.start_paper_trading --capital 100000 --commission 1.0
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import uvicorn

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import get_global_settings
from app.models.market_data import DataFeedConfig, DataFeedType
from app.models.paper_trading import PaperTradingSession
from app.services.market_data_service import MarketDataService
from app.services.paper_trading_service import PaperTradingService

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging for paper trading."""
    settings = get_global_settings()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler("logs/paper_trading.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def create_paper_trading_session(
    service: PaperTradingService,
    name: str,
    initial_capital: Decimal,
    commission_per_trade: Decimal,
) -> PaperTradingSession:
    """
    Create a new paper trading session.

    Args:
        service: Paper trading service instance
        name: Session name
        initial_capital: Starting capital
        commission_per_trade: Commission per trade

    Returns:
        Created session
    """
    logger.info(f"Creating paper trading session: {name}")
    logger.info(f"  Initial Capital: €{initial_capital:,.2f}")
    logger.info(f"  Commission: €{commission_per_trade}")

    session = service.create_session(
        name=name,
        initial_capital=initial_capital,
        commission_per_trade=commission_per_trade,
    )

    logger.info(f"✅ Session created: {session.session_id}")
    logger.info(f"   Account: {session.account_id}")
    logger.info(f"   Status: {session.status}")

    return session


async def start_market_data_service() -> MarketDataService:
    """
    Initialize and start the market data service.

    Returns:
        Market data service instance
    """
    logger.info("Initializing market data service...")

    settings = get_global_settings()
    service = MarketDataService()

    # Configure data feed with priority: Polygon > Alpha Vantage > Yahoo Finance
    data_feed_name = "Unknown"
    if settings.polygon_api_key and settings.polygon_api_key != "your_polygon_api_key_here":
        logger.info("   Configuring Polygon.io for real-time market data")
        polygon_config = DataFeedConfig(
            name="Polygon.io",
            feed_type=DataFeedType.POLYGON,
            base_url="https://api.polygon.io",
            api_key=settings.polygon_api_key,
            rate_limit=5,  # Adjust based on your Polygon plan
            timeout_seconds=30,
            is_active=True,
        )
        await service.add_feed_config(polygon_config)
        await service.connect_feed(polygon_config.id)
        data_feed_name = "Polygon.io"
        logger.info("   ✅ Connected to Polygon.io")
    elif (
        settings.alpha_vantage_api_key
        and settings.alpha_vantage_api_key != "your_alpha_vantage_key_here"
    ):
        logger.info("   Configuring Alpha Vantage for market data")
        alpha_vantage_config = DataFeedConfig(
            name="Alpha Vantage",
            feed_type=DataFeedType.ALPHA_VANTAGE,
            base_url="https://www.alphavantage.co/query",
            api_key=settings.alpha_vantage_api_key,
            rate_limit=5,  # Alpha Vantage free tier: 5 calls/minute
            timeout_seconds=30,
            is_active=True,
        )
        await service.add_feed_config(alpha_vantage_config)
        await service.connect_feed(alpha_vantage_config.id)
        data_feed_name = "Alpha Vantage"
        logger.info("   ✅ Connected to Alpha Vantage")
    else:
        logger.info("   Using Yahoo Finance (free, real data with 15-min delay)")
        data_feed_name = "Yahoo Finance"

    # Subscribe to popular symbols
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "AMD"]
    for symbol in symbols:
        await service.subscribe_symbol(symbol)

    logger.info(
        f"✅ Market data service started with {len(symbols)} symbols using {data_feed_name}"
    )

    return service


def print_banner():
    """Print startup banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║                  🚀 ALGOTRADING - PAPER TRADING 🚀                    ║
║                                                                        ║
║                    Professional Trading System                          ║
║                        v1.0.0 - Production Ready                        ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_info(session: PaperTradingSession):
    """Print session information."""
    settings = get_global_settings()
    info = f"""
╔══════════════════════════════════════════════════════════════════════╗
║  SESSION INFO                                                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  Session ID:   {session.session_id:<50} ║
║  Account:      {session.account_id:<50} ║
║  Name:         {session.name:<50} ║
║  Capital:      €{float(session.initial_capital):>48,.2f} ║
║  Commission:   €{float(session.commission_per_trade):>48,.2f} ║
║  Status:       {session.status.value:<50} ║
╠══════════════════════════════════════════════════════════════════════╣
║  ENDPOINTS                                                             ║
╠══════════════════════════════════════════════════════════════════════╣
║  API:          http://{settings.api_host}:{settings.api_port:<39} ║
║  Dashboard:    http://{settings.dashboard_host}:{settings.dashboard_port:<37} ║
║  Docs:         http://{settings.api_host}:{settings.api_port}/docs<{35} ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    print(info)


def print_next_steps():
    """Print next steps for the user."""
    steps = """
╔══════════════════════════════════════════════════════════════════════╗
║  NEXT STEPS                                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  1. Open the Dashboard:                                                ║
║     → Visit http://localhost:8501                                       ║
║     → Monitor your portfolio in real-time                               ║
║     → Execute trades manually or connect a strategy                     ║
║                                                                        ║
║  2. API Documentation:                                                  ║
║     → Visit http://localhost:8000/docs                                  ║
║     → Interactive API playground                                        ║
║     → Test endpoints with Swagger UI                                    ║
║                                                                        ║
║  3. Connect a Strategy:                                                 ║
║     → Implement your strategy in app/strategies/                        ║
║     → Use the PaperTradingService for order execution                   ║
║     → Monitor performance in real-time                                  ║
║                                                                        ║
║  4. Market Data:                                                        ║
║     → Currently using: Yahoo Finance (FREE, real data)                    ║
║     → For real-time data, add to .env:                                 ║
║       - POLYGON_API_KEY=your_key (Polygon.io - real-time)               ║
║       - ALPHA_VANTAGE_API_KEY=your_key (Alpha Vantage)                  ║
║       - ALPACA_API_KEY=your_key (Alpaca - real-time)                   ║
║                                                                        ║
║  5. Interactive Brokers (Optional):                                     ║
║     → Install TWS or IB Gateway                                         ║
║     → Configure in .env:                                                ║
║       - IB_PORT=7497                                                    ║
║       - IB_HOST=127.0.0.1                                               ║
║       - IB_CLIENT_ID=1                                                  ║
║       - IB_PAPER_TRADING=True                                           ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    print(steps)


async def main_async(args):
    """Main async function."""
    print_banner()

    # Setup logging
    setup_logging()
    logger.info("Starting AlgoTrading Paper Trading System...")

    # Initialize services
    market_data_service = await start_market_data_service()
    paper_trading_service = PaperTradingService(market_data_service=market_data_service)

    # Create session
    session = create_paper_trading_session(
        service=paper_trading_service,
        name=args.session_name or f"PaperTrading_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        initial_capital=Decimal(str(args.capital)),
        commission_per_trade=Decimal(str(args.commission)),
    )

    # Print session info
    print_info(session)
    print_next_steps()

    # Start API server
    settings = get_global_settings()
    logger.info("Starting API server...")
    logger.info(f"   Host: {settings.api_host}")
    logger.info(f"   Port: {settings.api_port}")
    logger.info("")
    logger.info("🚀 Paper trading system is ready!")
    logger.info("")
    logger.info("Press Ctrl+C to stop")

    try:
        # Run uvicorn in async mode
        config = uvicorn.Config(
            "app.api.paper_trading:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_reload,
            log_level=settings.log_level.lower(),
        )
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        logger.info("\n")
        logger.info("Shutting down paper trading system...")
        logger.info("✅ Session saved")
        logger.info("✅ Goodbye!")


def main():
    """Main entry point."""
    settings = get_global_settings()

    parser = argparse.ArgumentParser(
        description="Start AlgoTrading Paper Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default settings (€100K, €1 commission)
  python -m app.scripts.start_paper_trading

  # Start with custom capital
  python -m app.scripts.start_paper_trading --capital 50000

  # Start with custom session name
  python -m app.scripts.start_paper_trading --session-name "MyTradingSession"

  # Start with custom commission
  python -m app.scripts.start_paper_trading --commission 0.5
        """,
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=float(settings.paper_trading_initial_capital),
        help=f"Initial capital (default: {settings.paper_trading_initial_capital})",
    )

    parser.add_argument(
        "--commission",
        type=float,
        default=float(settings.paper_trading_commission_per_trade),
        help=f"Commission per trade (default: {settings.paper_trading_commission_per_trade})",
    )

    parser.add_argument(
        "--session-name",
        type=str,
        default=None,
        help="Custom session name (default: auto-generated)",
    )

    args = parser.parse_args()

    # Run async main
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
