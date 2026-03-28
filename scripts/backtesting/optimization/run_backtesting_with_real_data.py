#!/usr/bin/env python3
"""
Profile-Driven Trading with REAL Market Data from Alpha Vantage

This script runs the profile-driven trading algorithm using REAL market data
from Alpha Vantage API for authentic backtesting results.

Usage:
    # Run with default parameters (top 50 S&P 500 stocks, 1 year data)
    python run_backtesting_with_real_data.py run

    # Run with custom parameters
    python run_backtesting_with_real_data.py run --capital 50000 --symbols 20 --days 180

    # Run with specific symbols
    python run_backtesting_with_real_data.py run --symbols AAPL,MSFT,GOOGL,AMZN

    # Use cached data only (faster, no API calls)
    python run_backtesting_with_real_data.py run --cache-only

    # Clear cache and fetch fresh data
    python run_backtesting_with_real_data.py run --clear-cache

Features:
- Real S&P 500 top 50 stocks by market cap
- Alpha Vantage API integration with rate limiting
- Data caching to avoid re-fetching
- Comprehensive backtesting report
- Works with --no-ibkr flag (mock broker, real data)

Requirements:
- ALPHA_VANTAGE_API_KEY environment variable set
- Internet connection for API calls
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import click
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project to path
# scripts/backtesting/optimization/ -> scripts/backtesting/ -> scripts/ -> project_root
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
)
from app.data.real_market_data import RealMarketDataFetcher, get_default_symbols
from app.services.profile_driven_trading import (
    OrchestratorConfig,
    ProfileDrivenTradingOrchestrator,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('backtesting_real_data.log'),
    ],
)
logger = logging.getLogger(__name__)


def generate_backtest_report(
    result,
    universe_data: dict,
    report_path: str,
    input_params: dict,
) -> None:
    """
    Generate comprehensive backtesting report with real data.

    Report includes:
    - Input parameters and configuration
    - Real data source information
    - Universe statistics
    - Profile details and allocation
    - Trading signals and execution
    - Stage results and performance metrics

    Args:
        result: TradingResult object from orchestrator execution
        universe_data: Dictionary of symbol -> DataFrame with real market data
        report_path: Path where report should be saved
        input_params: Dictionary of input parameters used
    """
    report = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "report_type": "backtesting_with_real_data",
            "data_source": "Alpha Vantage API",
        },
        "input": {
            "capital": float(input_params.get("capital", 0)),
            "objective": input_params.get("objective"),
            "risk": input_params.get("risk"),
            "horizon_months": input_params.get("horizon"),
            "target_monthly": input_params.get("target_monthly", 2000),
        },
        "data_config": {
            "symbols_count": len(universe_data),
            "symbols": list(universe_data.keys())[:20],  # First 20 symbols
            "date_range": {
                "start_date": input_params.get("start_date"),
                "end_date": input_params.get("end_date"),
            },
            "cache_used": input_params.get("use_cache", True),
            "top_n_sp500": input_params.get("num_symbols", 50),
        },
        "config": {
            "enable_rl_signals": input_params.get("enable_rl", True),
            "enable_tax_optimization": input_params.get("enable_tax", True),
            "enable_backtest_validation": input_params.get("enable_backtest", True),
            "enable_risk_gates": input_params.get("enable_risk", True),
            "auto_execute_trades": False,  # Always false for backtesting
            "use_ibkr": False,  # Always false for backtesting
        },
        "profile": {
            "profile_id": result.profile_id,
        },
        "universe_statistics": _calculate_universe_statistics(universe_data),
        "allocation": None,
        "signals": None,
        "stages": {},
        "execution": None,
        "risk": None,
    }

    # Add allocation data if available
    if result.allocation:
        allocations = result.allocation.get("allocations", {})
        report["allocation"] = {
            "total_positions": len(allocations),
            "residual_capital": float(result.allocation.get("residual_capital", 0)),
            "total_capital": float(result.allocation.get("total_capital", 0)),
            "positions": [
                {
                    "symbol": symbol,
                    "capital_eur": float(metrics.capital),
                    "weight": float(metrics.weight),
                    "strategy": metrics.strategy,
                }
                for symbol, metrics in sorted(
                    allocations.items(),
                    key=lambda x: x[1].capital,
                    reverse=True,
                )
            ],
        }

    # Add signals data if available
    if result.signals:
        signal_summary = result.signals.get_summary()
        report["signals"] = {
            "total_signals": signal_summary["total_signals"],
            "buy_signals": signal_summary["buy_signals"],
            "sell_signals": signal_summary["sell_signals"],
            "hold_signals": signal_summary["hold_signals"],
            "buy_pct": signal_summary["buy_pct"],
            "sell_pct": signal_summary["sell_pct"],
            "hold_pct": signal_summary["hold_pct"],
            "rl_signals_count": signal_summary["rl_signals_count"],
            "momentum_signals_count": signal_summary["momentum_signals_count"],
            "mean_reversion_signals_count": signal_summary["mean_reversion_signals_count"],
            "avg_confidence": signal_summary["avg_confidence"],
        }

    # Add stage results
    for stage_result in result.stage_results:
        report["stages"][stage_result.stage_type.value] = {
            "success": stage_result.success,
            "duration_ms": stage_result.duration_ms,
            "message": stage_result.message,
            "errors": stage_result.errors,
            "warnings": stage_result.warnings,
        }

    # Add execution result if available
    if result.execution_result:
        exec_summary = result.execution_result.get_summary()
        report["execution"] = {
            "executed": exec_summary["executed"],
            "dry_run": exec_summary["dry_run"],
            "orders_submitted": exec_summary["orders_submitted"],
            "orders_filled": exec_summary["orders_filled"],
            "orders_failed": exec_summary["orders_failed"],
            "fill_rate": exec_summary["fill_rate"],
            "total_value_eur": exec_summary["total_value_eur"],
        }

    # Add risk validation if available
    if result.risk_validation:
        risk_summary = result.risk_validation.get_summary()
        report["risk"] = {
            "passed": risk_summary["passed"],
            "risk_level": risk_summary["risk_level"],
            "violation_count": risk_summary["violation_count"],
            "warning_count": risk_summary["warning_count"],
            "key_metrics": risk_summary["key_metrics"],
        }

    # Add overall execution summary
    report["summary"] = {
        "success": result.success,
        "execution_time_seconds": result.execution_time_ms / 1000,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        "total_stages": len(result.stage_results),
        "successful_stages": len(result.get_successful_stages()),
        "failed_stages": len(result.get_failed_stages()),
        "errors": result.errors,
        "warnings": result.warnings,
    }

    # Create reports directory if needed
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"Backtesting report saved to: {report_path}")


def _calculate_universe_statistics(universe_data: dict) -> dict:
    """Calculate statistics about the universe data."""
    if not universe_data:
        return {}

    all_dfs = list(universe_data.values())
    total_data_points = sum(len(df) for df in all_dfs)

    # Get date range
    all_dates = []
    for df in all_dfs:
        all_dates.extend(df.index.tolist())

    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
        date_range_days = (max_date - min_date).days
    else:
        min_date = max_date = None
        date_range_days = 0

    return {
        "total_symbols": len(universe_data),
        "total_data_points": total_data_points,
        "avg_data_points_per_symbol": total_data_points / len(universe_data)
        if universe_data
        else 0,
        "date_range": {
            "start": min_date.isoformat() if min_date else None,
            "end": max_date.isoformat() if max_date else None,
            "days": date_range_days,
        },
    }


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Profile-Driven Trading with REAL Market Data from Alpha Vantage."""
    pass


@cli.command()
@click.option(
    '--capital',
    type=float,
    default=100000.0,
    help='Initial capital in EUR (default: 100000)',
)
@click.option(
    '--objective',
    type=click.Choice(
        [
            'maximizar_capital',
            'maximizar_dividendos',
            'preservar_capital',
            'crecimiento_equilibrado',
        ],
        case_sensitive=False,
    ),
    default='maximizar_capital',
    help='Investment objective (default: maximizar_capital)',
)
@click.option(
    '--risk',
    type=click.Choice(['bajo', 'medio', 'alto'], case_sensitive=False),
    default='medio',
    help='Risk tolerance (default: medio)',
)
@click.option(
    '--horizon',
    type=int,
    default=12,
    help='Investment horizon in months (default: 12)',
)
@click.option(
    '--target-monthly',
    type=float,
    default=2000,
    help='Target monthly return in EUR (default: 2000)',
)
@click.option(
    '--symbols',
    type=str,
    default=None,
    help='Comma-separated list of symbols (e.g., "AAPL,MSFT,GOOGL") or number for top N S&P 500 (default: 50)',
)
@click.option(
    '--days',
    type=int,
    default=365,
    help='Number of days of historical data to fetch (default: 365)',
)
@click.option(
    '--start-date',
    type=str,
    default=None,
    help='Start date (YYYY-MM-DD format, overrides --days)',
)
@click.option(
    '--end-date',
    type=str,
    default=None,
    help='End date (YYYY-MM-DD format, default: today)',
)
@click.option(
    '--enable-rl/--disable-rl',
    default=True,
    help='Enable reinforcement learning signals (default: enabled)',
)
@click.option(
    '--enable-tax/--disable-tax',
    default=True,
    help='Enable tax optimization (default: enabled)',
)
@click.option(
    '--enable-backtest/--disable-backtest',
    default=True,
    help='Enable backtest validation (default: enabled)',
)
@click.option(
    '--enable-risk/--disable-risk',
    default=True,
    help='Enable risk gates (default: enabled)',
)
@click.option(
    '--cache/--no-cache',
    default=True,
    help='Use cached data if available (default: enabled)',
)
@click.option(
    '--clear-cache',
    is_flag=True,
    default=False,
    help='Clear cache before fetching fresh data',
)
@click.option(
    '--report/--no-report',
    default=True,
    help='Generate backtesting report (default: enabled)',
)
@click.option(
    '--report-path',
    type=str,
    default=None,
    help='Custom report file path (default: reports/backtesting_real_data_YYYYMMDD_HHMMSS.json)',
)
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
    default='INFO',
    help='Logging level (default: INFO)',
)
def run(
    capital,
    objective,
    risk,
    horizon,
    target_monthly,
    symbols,
    days,
    start_date,
    end_date,
    enable_rl,
    enable_tax,
    enable_backtest,
    enable_risk,
    cache,
    clear_cache,
    report,
    report_path,
    log_level,
):
    """
    Run profile-driven trading backtesting with REAL market data.

    Fetches historical OHLCV data from Alpha Vantage API and runs the
    complete trading lifecycle for authentic backtesting results.

    This is BACKTESTING mode - no real trades are executed.
    """
    # Set log level
    logging.getLogger().setLevel(getattr(logging, log_level))

    logger.info("=" * 80)
    logger.info("PROFILE-DRIVEN TRADING WITH REAL MARKET DATA")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"   Capital: EUR{capital:,.2f}")
    logger.info(f"   Objective: {objective}")
    logger.info(f"   Risk: {risk}")
    logger.info(f"   Horizon: {horizon} months")
    logger.info(f"   Target Monthly: EUR{target_monthly:,.2f}")
    logger.info(f"   Data Source: Alpha Vantage API (REAL DATA)")
    logger.info(f"   Symbols: {symbols if symbols else 'Top 50 S&P 500'}")
    logger.info(f"   Data Period: {days} days")
    logger.info(f"   Cache: {'Enabled' if cache else 'Disabled'}")
    logger.info(f"   Clear Cache: {'Yes' if clear_cache else 'No'}")
    logger.info(f"   RL Signals: {'Enabled' if enable_rl else 'Disabled'}")
    logger.info(f"   Tax Optimization: {'Enabled' if enable_tax else 'Disabled'}")
    logger.info(f"   Backtest Validation: {'Enabled' if enable_backtest else 'Disabled'}")
    logger.info(f"   Risk Gates: {'Enabled' if enable_risk else 'Disabled'}")
    logger.info(f"   Report Generation: {'Enabled' if report else 'Disabled'}")
    logger.info(f"   Mode: BACKTESTING (no real trades)")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    # Parse symbols parameter
    symbol_list = None
    num_symbols = 50

    if symbols:
        if symbols.isdigit():
            num_symbols = int(symbols)
            logger.info(f"Fetching top {num_symbols} S&P 500 stocks...")
        else:
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
            logger.info(f"Fetching {len(symbol_list)} specified symbols: {', '.join(symbol_list)}")
    else:
        logger.info(f"Fetching top {num_symbols} S&P 500 stocks...")

    # Parse dates
    if start_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        end_date_obj = datetime.now() if not end_date else datetime.strptime(end_date, '%Y-%m-%d')
        start_date_obj = end_date_obj - timedelta(days=days)

    if end_date:
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date_obj = datetime.now()

    logger.info(f"Date Range: {start_date_obj.date()} to {end_date_obj.date()}")

    # Clear cache if requested
    if clear_cache:
        logger.info("Clearing data cache...")
        try:
            fetcher = RealMarketDataFetcher()
            fetcher.clear_cache()
            logger.info("Cache cleared successfully")
        except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
            logger.warning(f"Failed to clear cache: {e}")

    # Map inputs to enums
    objective_map = {
        'maximizar_capital': ObjectivoInversion.MAXIMIZAR_CAPITAL,
        'maximizar_dividendos': ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
        'preservar_capital': ObjectivoInversion.CAPITAL_PRESERVATION,
        'crecimiento_equilibrado': ObjectivoInversion.BALANCED_GROWTH,
    }

    risk_map = {
        'bajo': RiskTolerance.BAJO,
        'medio': RiskTolerance.MEDIO,
        'alto': RiskTolerance.ALTO,
    }

    # Create input profile
    input_profile = InputProfile(
        capital_initial=Decimal(str(capital)),
        objetivo_inversion=objective_map[objective],
        risk_tolerance=risk_map[risk],
        investment_horizon=horizon,
    )

    # Create orchestrator config
    config = OrchestratorConfig(
        enable_rl_signals=enable_rl,
        enable_tax_optimization=enable_tax,
        enable_backtest_validation=enable_backtest,
        enable_risk_gates=enable_risk,
        auto_execute_trades=False,  # Always false for backtesting
        use_ibkr=False,  # Always false for backtesting
        top_n_per_universe=num_symbols,
    )

    # Create orchestrator
    orchestrator = ProfileDrivenTradingOrchestrator(config)

    # Run lifecycle with real data
    try:
        logger.info("")
        logger.info("STEP 1: Fetching REAL market data from Alpha Vantage...")
        logger.info("-" * 40)

        # Fetch real market data
        async def fetch_and_run():
            async with RealMarketDataFetcher() as fetcher:
                # Fetch universe data
                if symbol_list:
                    universe_data = await fetcher.fetch_multiple_symbols(
                        symbols=symbol_list,
                        start_date=start_date_obj,
                        end_date=end_date_obj,
                        use_cache=cache,
                    )
                else:
                    universe_data = await fetcher.fetch_sp500_top_n(
                        n=num_symbols,
                        start_date=start_date_obj,
                        end_date=end_date_obj,
                        use_cache=cache,
                    )

                logger.info(f"✅ Fetched {len(universe_data)} symbols with REAL data")

                # Show cache statistics
                cache_stats = fetcher.get_cache_stats()
                logger.info(f"   Cache Statistics:")
                logger.info(f"   - Total cached symbols: {cache_stats['total_cached_symbols']}")
                logger.info(f"   - Cache size: {cache_stats['cache_size_mb']:.2f} MB")

                # Now run the trading lifecycle with real data
                logger.info("")
                logger.info("STEP 2: Running profile-driven trading lifecycle...")
                logger.info("-" * 40)

                # We need to manually execute the lifecycle, using real data for Stage 2
                # This is a modified version that uses real data
                lifecycle_result = await run_lifecycle_with_real_data(
                    orchestrator,
                    input_profile,
                    universe_data,
                )
                # Return both the result and the universe data
                return lifecycle_result, universe_data

        result, universe_data = asyncio.run(fetch_and_run())

        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("BACKTESTING SUMMARY")
        logger.info("=" * 80)

        logger.info(f"Status: {'SUCCESS ✅' if result.success else 'FAILED ❌'}")
        logger.info(f"Execution Time: {result.execution_time_ms / 1000:.2f} seconds")
        logger.info(f"Profile ID: {result.profile_id}")
        logger.info(f"Real Data Symbols: {len(universe_data)}")
        logger.info("")

        logger.info("Stages:")
        for stage_result in result.stage_results:
            status = "✅" if stage_result.success else "❌"
            logger.info(
                f"  {status} {stage_result.stage_type.value}: {stage_result.duration_ms:.2f}ms"
            )

        logger.info("")

        if result.allocation:
            logger.info("Allocation:")
            allocations = result.allocation.get("allocations", {})
            logger.info(f"  Total Positions: {len(allocations)}")
            logger.info(f"  Residual Capital: €{result.allocation.get('residual_capital', 0):,.2f}")
            logger.info("")

            # Show top 5 positions
            sorted_allocations = sorted(
                allocations.items(),
                key=lambda x: x[1].capital,
                reverse=True,
            )[:5]

            logger.info("  Top 5 Positions:")
            for symbol, metrics in sorted_allocations:
                logger.info(
                    f"    {symbol}: €{metrics.capital:,.2f} ({metrics.weight:.2%}) - {metrics.strategy}"
                )

        if result.signals:
            logger.info("")
            logger.info("Signals:")
            signal_summary = result.signals.get_summary()
            logger.info(f"  BUY: {signal_summary['buy_signals']}")
            logger.info(f"  SELL: {signal_summary['sell_signals']}")
            logger.info(f"  HOLD: {signal_summary['hold_signals']}")

        logger.info("")
        logger.info("=" * 80)

        # Generate report if enabled
        if report:
            # Determine report path
            if report_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_path = f'reports/backtesting_real_data_{timestamp}.json'

            # Collect input parameters for report
            input_params = {
                'capital': capital,
                'objective': objective,
                'risk': risk,
                'horizon': horizon,
                'target_monthly': target_monthly,
                'enable_rl': enable_rl,
                'enable_tax': enable_tax,
                'enable_backtest': enable_backtest,
                'enable_risk': enable_risk,
                'num_symbols': num_symbols,
                'start_date': start_date_obj.isoformat(),
                'end_date': end_date_obj.isoformat(),
                'use_cache': cache,
            }

            try:
                # Get universe data from the result
                generate_backtest_report(result, universe_data, report_path, input_params)
            except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
                logger.error(f"Failed to generate report: {e}")

        # Exit with appropriate code
        sys.exit(0 if result.success else 1)

    except KeyboardInterrupt:
        logger.warning("")
        logger.warning("⚠️  Execution cancelled by user")
        sys.exit(130)
    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error("")
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


async def run_lifecycle_with_real_data(
    orchestrator: ProfileDrivenTradingOrchestrator,
    input_profile,
    universe_data: dict,
):
    """
    Run the trading lifecycle with real market data.

    This is a modified version of execute_trading_lifecycle that uses
    the real data we've already fetched.
    """
    start_time = datetime.utcnow()
    logger.info("🚀 STARTING PROFILE-DRIVEN TRADING LIFECYCLE (WITH REAL DATA)")
    logger.info("=" * 80)

    from app.services.profile_driven_trading.models import TradingResult, StageType

    result = TradingResult(
        success=False,
        profile_id=getattr(input_profile, 'input_id', 'unknown'),
        started_at=start_time,
    )

    try:
        # Execute stages with real data
        stages = [
            (
                StageType.PROFILE_GENERATION,
                orchestrator.stage_1_generate_profile,
                {"input_profile": input_profile},
            ),
            # Skip Stage 2 (we already have real universe data)
            (
                StageType.CAPITAL_ALLOCATION,
                orchestrator.stage_3_allocate_capital,
                {"universe": universe_data},
            ),
            (
                StageType.SIGNAL_GENERATION,
                orchestrator.stage_4_generate_signals,
                {"allocation": None},
            ),
            (StageType.TAX_OPTIMIZATION, orchestrator.stage_5_optimize_taxes, {"allocation": None}),
            (StageType.RISK_VALIDATION, orchestrator.stage_6_validate_risk, {"allocation": None}),
            (StageType.BACKTEST_VALIDATION, orchestrator.stage_7_backtest_validate, {}),
            (StageType.TRADE_EXECUTION, orchestrator.stage_8_execute_trades, {}),
        ]

        # Execute pipeline
        pipeline_result = await orchestrator.workflow_manager.execute_pipeline(
            stages,
            stop_on_error=False,
        )

        result.stage_results = pipeline_result.stage_results
        result.completed_at = datetime.utcnow()

        # Extract results from stages
        profile_result = pipeline_result.get_stage_by_type(StageType.PROFILE_GENERATION)
        if profile_result and profile_result.success:
            result.investment_profile = profile_result.data
            result.profile_id = getattr(profile_result.data, 'profile_id', result.profile_id)

        allocation_result = pipeline_result.get_stage_by_type(StageType.CAPITAL_ALLOCATION)
        if allocation_result and allocation_result.success:
            result.allocation = allocation_result.data

        signal_result = pipeline_result.get_stage_by_type(StageType.SIGNAL_GENERATION)
        if signal_result and signal_result.success:
            result.signals = signal_result.data

        tax_result = pipeline_result.get_stage_by_type(StageType.TAX_OPTIMIZATION)
        if tax_result and tax_result.success:
            result.tax_optimized_allocation = tax_result.data

        risk_result = pipeline_result.get_stage_by_type(StageType.RISK_VALIDATION)
        if risk_result and risk_result.success:
            result.risk_validation = risk_result.data

        backtest_result = pipeline_result.get_stage_by_type(StageType.BACKTEST_VALIDATION)
        if backtest_result and backtest_result.success:
            result.backtest_result = backtest_result.data

        execution_result = pipeline_result.get_stage_by_type(StageType.TRADE_EXECUTION)
        if execution_result and execution_result.success:
            result.execution_result = execution_result.data

        # Determine overall success
        critical_stages = [
            StageType.PROFILE_GENERATION,
            StageType.CAPITAL_ALLOCATION,
            StageType.RISK_VALIDATION,
        ]

        result.success = all(
            pipeline_result.get_stage_by_type(s) and pipeline_result.get_stage_by_type(s).success
            for s in critical_stages
        )

        # Collect warnings and errors
        for stage_result in result.stage_results:
            result.warnings.extend(stage_result.warnings)
        for stage_result in (
            result.get_failed_stages() if hasattr(result, 'get_failed_stages') else []
        ):
            result.errors.extend(stage_result.errors)

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"❌ Fatal error in trading lifecycle: {e}", exc_info=True)
        result.errors.append(f"Fatal error: {str(e)}")
        result.success = False

    result.execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

    # Update tracking
    orchestrator.execution_count += 1
    orchestrator.last_execution_time = datetime.utcnow()

    logger.info("=" * 80)
    logger.info(f"🏁 TRADING LIFECYCLE COMPLETE: {'SUCCESS ✅' if result.success else 'FAILED ❌'}")
    logger.info(f"   Execution Time: {result.execution_time_ms:.2f}ms")
    logger.info(f"   Stages: {len(result.stage_results)}")
    logger.info("=" * 80)

    return result


@cli.command()
def cache_info():
    """Show cache statistics."""
    logger.info("Real Market Data Cache Statistics")
    logger.info("")

    try:
        fetcher = RealMarketDataFetcher()
        stats = fetcher.get_cache_stats()

        logger.info(f"Total Cached Symbols: {stats['total_cached_symbols']}")
        logger.info(f"Cache Size: {stats['cache_size_mb']:.2f} MB")

        if 'oldest_cache_days' in stats:
            logger.info(f"Oldest Cache: {stats['oldest_cache_days']:.1f} days old")
        if 'newest_cache_days' in stats:
            logger.info(f"Newest Cache: {stats['newest_cache_days']:.1f} days old")

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Error getting cache info: {e}")


@cli.command()
@click.argument('symbol', required=False)
def clear_cache(symbol):
    """
    Clear cached data.

    Clear all cache or specific symbol cache.

    Usage:
        python run_backtesting_with_real_data.py clear-cache
        python run_backtesting_with_real_data.py clear-cache AAPL
    """
    logger.info("Clearing cache...")

    try:
        fetcher = RealMarketDataFetcher()
        fetcher.clear_cache(symbol=symbol)

        if symbol:
            logger.info(f"✅ Cleared cache for {symbol}")
        else:
            logger.info("✅ Cleared all cache")

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Error clearing cache: {e}")


@cli.command()
def list_symbols():
    """List available S&P 500 top 50 symbols."""
    logger.info("S&P 500 Top 50 Stocks by Market Cap")
    logger.info("")

    symbols = get_default_symbols(50)

    for i, symbol in enumerate(symbols, 1):
        logger.info(f"{i:2d}. {symbol}")


if __name__ == '__main__':
    cli()
