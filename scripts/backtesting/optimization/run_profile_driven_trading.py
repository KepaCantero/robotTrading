#!/usr/bin/env python3
"""
Profile-Driven Trading CLI

Command-line interface for the Profile-Driven Trading Algorithm Orchestrator.

Usage:
    # Run with default parameters (dry-run mode)
    python run_profile_driven_trading.py run

    # Run with custom parameters
    python run_profile_driven_trading.py run --capital 50000 --objective maximizar_capital --risk medio --horizon 24

    # Interactive mode
    python run_profile_driven_trading.py interactive

    # Enable live trading (USE WITH CAUTION)
    python run_profile_driven_trading.py run --auto-execute
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
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
        logging.FileHandler('profile_driven_trading.log'),
    ],
)
logger = logging.getLogger(__name__)


def generate_report(result, report_path: str, input_params: dict) -> None:
    """
    Generate comprehensive execution report.

    Report includes:
    - Input parameters
    - Profile details
    - Allocation results
    - Trading signals
    - Stage results
    - Performance metrics
    - Execution summary

    Args:
        result: TradingResult object from orchestrator execution
        report_path: Path where report should be saved
        input_params: Dictionary of input parameters used
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "input": {
            "capital": float(input_params.get("capital", 0)),
            "objective": input_params.get("objective"),
            "risk": input_params.get("risk"),
            "horizon_months": input_params.get("horizon"),
            "target_monthly": input_params.get("target_monthly", 2000),
            "top_n": input_params.get("top_n", 100),
        },
        "config": {
            "enable_rl_signals": input_params.get("enable_rl", True),
            "enable_tax_optimization": input_params.get("enable_tax", True),
            "enable_backtest_validation": input_params.get("enable_backtest", True),
            "enable_risk_gates": input_params.get("enable_risk", True),
            "auto_execute_trades": input_params.get("auto_execute", False),
            "use_ibkr": input_params.get("use_ibkr", False),
        },
        "profile": {
            "profile_id": result.profile_id,
        },
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

    logger.info(f"Report saved to: {report_path}")


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Profile-Driven Trading Algorithm Orchestrator CLI."""
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
        ['maximizar_capital', 'maximizar_dividendos', 'preservar_capital', 'crecimiento_equilibrado'],
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
    '--auto-execute',
    is_flag=True,
    default=False,
    help='Enable automatic trade execution (DANGEROUS! Use with caution)',
)
@click.option(
    '--use-ibkr/--no-ibkr',
    default=False,
    help='Use Interactive Brokers (default: disabled/mock mode)',
)
@click.option(
    '--report/--no-report',
    default=True,
    help='Generate execution report (default: enabled)',
)
@click.option(
    '--report-path',
    type=str,
    default=None,
    help='Custom report file path (default: reports/profile_driven_trading_report_YYYYMMDD_HHMMSS.json)',
)
@click.option(
    '--top-n',
    type=int,
    default=100,
    help='Top N stocks per universe (default: 100)',
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
    enable_rl,
    enable_tax,
    enable_backtest,
    enable_risk,
    auto_execute,
    use_ibkr,
    report,
    report_path,
    top_n,
    log_level,
):
    """
    Run the profile-driven trading lifecycle.

    Executes the complete 8-stage trading pipeline from profile to execution.
    By default, runs in dry-run mode (no real trades executed).
    """
    # Set log level
    logging.getLogger().setLevel(getattr(logging, log_level))

    logger.info("=" * 80)
    logger.info("PROFILE-DRIVEN TRADING ALGORITHM")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Configuration:")
    logger.info(f"   Capital: EUR{capital:,.2f}")
    logger.info(f"   Objective: {objective}")
    logger.info(f"   Risk: {risk}")
    logger.info(f"   Horizon: {horizon} months")
    logger.info(f"   Target Monthly: EUR{target_monthly:,.2f}")
    logger.info(f"   RL Signals: {'Enabled' if enable_rl else 'Disabled'}")
    logger.info(f"   Tax Optimization: {'Enabled' if enable_tax else 'Disabled'}")
    logger.info(f"   Backtest Validation: {'Enabled' if enable_backtest else 'Disabled'}")
    logger.info(f"   Risk Gates: {'Enabled' if enable_risk else 'Disabled'}")
    logger.info(f"   Auto-Execute: {'YES (WARNING)' if auto_execute else 'NO (dry-run)'}")
    logger.info(f"   Interactive Brokers: {'Enabled' if use_ibkr else 'Disabled (mock mode)'}")
    logger.info(f"   Report Generation: {'Enabled' if report else 'Disabled'}")
    if report and report_path:
        logger.info(f"   Report Path: {report_path}")
    logger.info(f"   Top N: {top_n}")
    logger.info("")
    logger.info("=" * 80)
    logger.info("")

    # Safety warning for auto-execute
    if auto_execute:
        logger.warning("⚠️  AUTO-EXECUTION IS ENABLED!")
        logger.warning("⚠️  REAL TRADES WILL BE EXECUTED!")
        logger.warning("⚠️  PRESS Ctrl+C NOW TO CANCEL!")
        logger.warning("")

        # Give user time to cancel
        import time

        for i in range(5, 0, -1):
            logger.warning(f"⚠️  Starting in {i} seconds...")
            time.sleep(1)

        logger.warning("")

    # Map inputs to enums (using correct enum values)
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
        auto_execute_trades=auto_execute,
        use_ibkr=use_ibkr,
        top_n_per_universe=top_n,
    )

    # Create orchestrator
    orchestrator = ProfileDrivenTradingOrchestrator(config)

    # Run lifecycle
    try:
        result = asyncio.run(orchestrator.execute_trading_lifecycle(input_profile))

        # Print summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("EXECUTION SUMMARY")
        logger.info("=" * 80)

        summary = result.get_summary()

        logger.info(f"Status: {'SUCCESS ✅' if result.success else 'FAILED ❌'}")
        logger.info(f"Execution Time: {result.execution_time_ms / 1000:.2f} seconds")
        logger.info(f"Profile ID: {result.profile_id}")
        logger.info("")

        logger.info("Stages:")
        for stage_result in result.stage_results:
            status = "✅" if stage_result.success else "❌"
            logger.info(f"  {status} {stage_result.stage_type.value}: {stage_result.duration_ms:.2f}ms")

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

        if result.execution_result:
            logger.info("")
            logger.info("Execution:")
            exec_summary = result.execution_result.get_summary()
            logger.info(f"  Mode: {'LIVE' if not result.execution_result.dry_run else 'DRY-RUN'}")
            logger.info(f"  Orders: {exec_summary['orders_submitted']} submitted, {exec_summary['orders_filled']} filled")
            logger.info(f"  Total Value: €{result.execution_result.total_value_eur:,.2f}")

        if result.warnings:
            logger.info("")
            logger.info("Warnings:")
            for warning in result.warnings[:5]:
                logger.warning(f"  ⚠️  {warning}")

        if result.errors:
            logger.info("")
            logger.error("Errors:")
            for error in result.errors[:5]:
                logger.error(f"  ❌ {error}")

        logger.info("")
        logger.info("=" * 80)

        # Generate report if enabled
        if report:
            # Determine report path
            if report_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_path = f'reports/profile_driven_trading_report_{timestamp}.json'

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
                'auto_execute': auto_execute,
                'use_ibkr': use_ibkr,
                'top_n': top_n,
            }

            try:
                generate_report(result, report_path, input_params)
            except (ConnectionError, TimeoutError, HTTPError, ValueError) as e:
                logger.error(f"Failed to generate report: {e}")

        # Exit with appropriate code
        sys.exit(0 if result.success else 1)

    except KeyboardInterrupt:
        logger.warning("")
        logger.warning("⚠️  Execution cancelled by user")
        sys.exit(130)
    except (ConnectionError, TimeoutError, HTTPError, ValueError) as e:
        logger.error("")
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def interactive():
    """
    Interactive mode for profile-driven trading.

    Prompts user for configuration parameters interactively.
    """
    logger.info("=" * 80)
    logger.info("PROFILE-DRIVEN TRADING - INTERACTIVE MODE")
    logger.info("=" * 80)
    logger.info("")

    # Prompt for configuration
    try:
        capital = float(click.prompt('Initial capital (EUR)', default=100000.0))
        logger.info("")

        click.echo("Investment Objectives:")
        click.echo("  1. Maximizar Capital")
        click.echo("  2. Maximizar Dividendos")
        click.echo("  3. Preservar Capital")
        click.echo("  4. Crecimiento Equilibrado")

        objective_choice = click.prompt(
            'Select objective (1-4)',
            type=click.IntRange(1, 4),
            default=1,
        )
        objective_map = {
            1: 'maximizar_capital',
            2: 'maximizar_dividendos',
            3: 'preservar_capital',
            4: 'crecimiento_equilibrado',
        }
        objective = objective_map[objective_choice]
        logger.info("")

        click.echo("Risk Tolerance:")
        click.echo("  1. Bajo (Low)")
        click.echo("  2. Medio (Medium)")
        click.echo("  3. Alto (High)")

        risk_choice = click.prompt(
            'Select risk tolerance (1-3)',
            type=click.IntRange(1, 3),
            default=2,
        )
        risk_map = {1: 'bajo', 2: 'medio', 3: 'alto'}
        risk = risk_map[risk_choice]
        logger.info("")

        horizon = click.prompt('Investment horizon (months)', default=12)
        logger.info("")

        # Feature flags
        enable_rl = click.confirm('Enable RL signals?', default=True)
        enable_tax = click.confirm('Enable tax optimization?', default=True)
        enable_backtest = click.confirm('Enable backtest validation?', default=True)
        enable_risk = click.confirm('Enable risk gates?', default=True)
        logger.info("")

        auto_execute = click.confirm(
            'Enable automatic trade execution (DANGEROUS)?',
            default=False,
            show_default=True,
        )
        logger.info("")

        use_ibkr = click.confirm(
            'Use Interactive Brokers (vs mock mode)?',
            default=False,
            show_default=True,
        )
        logger.info("")

        report = click.confirm(
            'Generate execution report?',
            default=True,
            show_default=True,
        )
        logger.info("")

        top_n = click.prompt('Top N stocks per universe', default=100)
        logger.info("")

        # Show configuration and confirm
        logger.info("=" * 80)
        logger.info("CONFIGURATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"   Capital: EUR{capital:,.2f}")
        logger.info(f"   Objective: {objective}")
        logger.info(f"   Risk: {risk}")
        logger.info(f"   Horizon: {horizon} months")
        logger.info(f"   RL: {'Enabled' if enable_rl else 'Disabled'}")
        logger.info(f"   Tax: {'Enabled' if enable_tax else 'Disabled'}")
        logger.info(f"   Backtest: {'Enabled' if enable_backtest else 'Disabled'}")
        logger.info(f"   Risk Gates: {'Enabled' if enable_risk else 'Disabled'}")
        logger.info(f"   Auto-Execute: {'YES (WARNING)' if auto_execute else 'NO (dry-run)'}")
        logger.info(f"   Interactive Brokers: {'Enabled' if use_ibkr else 'Disabled (mock mode)'}")
        logger.info(f"   Report Generation: {'Enabled' if report else 'Disabled'}")
        logger.info(f"   Top N: {top_n}")
        logger.info("=" * 80)
        logger.info("")

        if not click.confirm('Proceed with execution?', default=True):
            logger.info("Execution cancelled.")
            sys.exit(0)

        # Run with the provided configuration
        from click.testing import CliRunner

        runner = CliRunner()

        result = runner.invoke(
            run,
            [
                '--capital', str(capital),
                '--objective', objective,
                '--risk', risk,
                '--horizon', str(horizon),
                '--top-n', str(top_n),
            ] + (
                ['--enable-rl'] if enable_rl else ['--disable-rl']
            ) + (
                ['--enable-tax'] if enable_tax else ['--disable-tax']
            ) + (
                ['--enable-backtest'] if enable_backtest else ['--disable-backtest']
            ) + (
                ['--enable-risk'] if enable_risk else ['--disable-risk']
            ) + (
                ['--auto-execute'] if auto_execute else []
            ) + (
                ['--use-ibkr'] if use_ibkr else ['--no-ibkr']
            ) + (
                ['--report'] if report else ['--no-report']
            ),
        )

        click.echo(result.output)
        sys.exit(result.exit_code)

    except KeyboardInterrupt:
        logger.warning("")
        logger.warning("⚠️  Interactive mode cancelled by user")
        sys.exit(130)
    except (ConnectionError, TimeoutError, HTTPError, ValueError) as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def status():
    """Show system status and statistics."""
    logger.info("Profile-Driven Trading System Status")
    logger.info("")

    # Create default orchestrator to check status
    config = OrchestratorConfig()
    orchestrator = ProfileDrivenTradingOrchestrator(config)

    status = orchestrator.get_status()

    logger.info("Configuration:")
    for key, value in status["config"].items():
        logger.info(f"  {key}: {value}")

    logger.info("")
    logger.info("Execution Statistics:")
    for key, value in status["execution"].items():
        logger.info(f"  {key}: {value}")

    logger.info("")
    logger.info("Workflow Statistics:")
    for key, value in status["workflow_statistics"].items():
        if key != "last_execution":
            logger.info(f"  {key}: {value}")


if __name__ == '__main__':
    cli()
