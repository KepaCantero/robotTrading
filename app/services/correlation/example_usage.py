"""
Example Usage of Real-Time Correlation Analyzer - Phase 2.4

This example demonstrates how to use the CorrelationAnalyzer
to calculate real correlation from historical prices.
"""

import asyncio
from decimal import Decimal

from app.services.correlation.analyzer import CorrelationAnalyzer, CorrelationConfig
from app.services.portfolio_risk_manager import PortfolioRiskManager
from app.services.market_data_service import MarketDataService
from app.models.portfolio import Portfolio, Position, AssetClass


async def example_basic_usage():
    """Example: Basic correlation calculation."""
    # Create market data service
    market_data_service = MarketDataService()

    # Create correlation analyzer
    config = CorrelationConfig(
        lookback_days=60,
        update_interval_seconds=3600.0,
        min_data_points=20,
        cache_enabled=True,
    )
    analyzer = CorrelationAnalyzer(
        data_service=market_data_service,
        config=config,
    )

    # Calculate correlation matrix for multiple symbols
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    correlation_matrix = await analyzer.calculate_correlation_matrix(symbols)

    print("Correlation Matrix:")
    print(correlation_matrix)

    # Get pairwise correlation
    correlation = await analyzer.get_correlation("AAPL", "MSFT")
    print(f"\nAAPL-MSFT Correlation: {correlation:.3f}")

    # Get statistics
    stats = analyzer.get_statistics()
    print(f"\nStatistics: {stats}")


async def example_with_background_updates():
    """Example: Background updates for continuous correlation monitoring."""
    market_data_service = MarketDataService()

    analyzer = CorrelationAnalyzer(
        data_service=market_data_service,
        config=CorrelationConfig(),
    )

    # Start background updates (updates every hour)
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
    await analyzer.start_background_updates(symbols)

    # Correlation is now automatically updated in background
    # Get correlation quickly from cache
    correlation = await analyzer.get_correlation("AAPL", "MSFT")
    print(f"Correlation (from cache): {correlation:.3f}")

    # Later, stop background updates
    await analyzer.stop_background_updates()


def example_with_portfolio_risk_manager():
    """Example: Integration with PortfolioRiskManager."""
    # Create market data service and correlation analyzer
    market_data_service = MarketDataService()
    analyzer = CorrelationAnalyzer(
        data_service=market_data_service,
        config=CorrelationConfig(),
    )

    # Create portfolio risk manager with correlation analyzer
    risk_manager = PortfolioRiskManager(correlation_analyzer=analyzer)

    # Create a portfolio
    portfolio = Portfolio(
        portfolio_id="my_portfolio",
        cash=Decimal("100000.00"),
        broker="test_broker",
        currency="USD",
        positions=[
            Position(
                symbol="AAPL",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("100"),
                avg_price=Decimal("150.00"),
                market_price=Decimal("155.00"),
                unrealized_pnl=Decimal("500"),
                broker="test_broker",
                sector="Technology",
                country="US",
            ),
            Position(
                symbol="MSFT",
                asset_class=AssetClass.EQUITY,
                quantity=Decimal("50"),
                avg_price=Decimal("300.00"),
                market_price=Decimal("310.00"),
                unrealized_pnl=Decimal("500"),
                broker="test_broker",
                sector="Technology",
                country="US",
            ),
        ],
    )

    # Assess portfolio risk (uses real correlation from analyzer)
    risk_assessment = risk_manager.assess_portfolio_risk(portfolio)

    print(f"Risk Level: {risk_assessment['risk_level']}")
    print(f"Correlations: {risk_assessment['risk_metrics']['correlations']}")

    # Check for correlation violations
    correlation_violations = [
        v for v in risk_assessment['violations']
        if v['type'] == 'correlation'
    ]

    if correlation_violations:
        print("High correlations detected:")
        for violation in correlation_violations:
            print(f"  {violation['pair']}: {violation['current_value']:.3f}")


async def example_fallback_behavior():
    """Example: Fallback behavior when real data unavailable."""
    market_data_service = MarketDataService()

    # Disable fallback to see error handling
    config = CorrelationConfig(use_fallback=False)
    analyzer = CorrelationAnalyzer(
        data_service=market_data_service,
        config=config,
    )

    # Set symbol metadata for better fallback
    analyzer.set_symbol_metadata("AAPL", sector="Technology", market="US")
    analyzer.set_symbol_metadata("MSFT", sector="Technology", market="US")
    analyzer.set_symbol_metadata("JNJ", sector="Healthcare", market="US")

    # Try to get correlation (will use fallback if real data unavailable)
    correlation = await analyzer.get_correlation("AAPL", "MSFT")
    print(f"AAPL-MSFT Correlation: {correlation:.3f}")  # Should be 0.5 (same sector)

    correlation = await analyzer.get_correlation("AAPL", "JNJ")
    print(f"AAPL-JNJ Correlation: {correlation:.3f}")  # Should be 0.3 (same market)


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    await example_basic_usage()

    print("\n" + "=" * 60)
    print("Example 2: Background Updates")
    print("=" * 60)
    await example_with_background_updates()

    print("\n" + "=" * 60)
    print("Example 3: Portfolio Risk Manager Integration")
    print("=" * 60)
    example_with_portfolio_risk_manager()

    print("\n" + "=" * 60)
    print("Example 4: Fallback Behavior")
    print("=" * 60)
    await example_fallback_behavior()


if __name__ == "__main__":
    asyncio.run(main())
