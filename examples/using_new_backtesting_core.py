"""
Example: Using the new backtesting core modules.

This script demonstrates how to use the refactored backtesting system
with the new core modules (config_loader, executor, orchestrator, facade).
"""

import asyncio
from pathlib import Path

# Example 1: Using the Facade (simplest approach)
def example_using_facade():
    """Example using BacktestRunnerFacade for simple backtesting."""
    from app.backtesting.core import create_backtest_runner

    # Create runner with config
    config_path = "config/backtesting/comprehensive_backtest.yaml"
    runner = create_backtest_runner(config_path)

    # Load data (now async)
    asyncio.run(runner.load_data())

    # Create a simple strategy
    from app.strategies.momentum_modular.strategy import ModularMomentumStrategy

    strategy_config = {
        'preset': 'balanced',
        'modules': {
            'filters': {
                'ema_filter': {'enabled': True},
                'rsi_filter': {'enabled': True},
            }
        }
    }
    strategy = ModularMomentumStrategy(strategy_config)

    # Run baseline backtest
    result = runner.run_baseline(strategy)
    print(f"Baseline PnL: ${result['total_pnl']:.2f}")
    print(f"Sharpe Ratio: {result['sharpe_ratio']:.2f}")

    # Save results
    runner.save_results(['csv', 'json'])


# Example 2: Using ConfigLoader directly
def example_using_config_loader():
    """Example using BacktestConfigLoader for configuration management."""
    from app.backtesting.core import BacktestConfigLoader
    from decimal import Decimal

    # Load configuration
    config_path = "config/backtesting/comprehensive_backtest.yaml"
    loader = BacktestConfigLoader(config_path)

    # Get backtest configuration
    backtest_config = loader.get_backtest_config()
    print(f"Initial Capital: ${backtest_config.initial_capital}")
    print(f"Commission: ${backtest_config.commission_per_trade}")
    print(f"Slippage: {backtest_config.slippage_percentage}%")

    # Get other configuration sections
    modules_config = loader.get_modules_config()
    print(f"Available filters: {list(modules_config.get('filters', {}).keys())}")


# Example 3: Using Executor directly
def example_using_executor():
    """Example using BacktestExecutor for fine-grained control."""
    from app.backtesting.core import BacktestExecutorFactory
    from app.backtesting.models import BacktestConfig
    from decimal import Decimal
    from app.strategies.momentum_modular.strategy import ModularMomentumStrategy
    from app.backtesting.data_loader import DataLoader
    from datetime import datetime

    # Create configuration
    config = BacktestConfig(
        initial_capital=Decimal('100000'),
        commission_per_trade=Decimal('1.0'),
        slippage_percentage=Decimal('0.1'),
    )

    # Create executor
    executor = BacktestExecutorFactory.create(config, parallel=False)

    # Load data
    data_loader = DataLoader()
    quotes = data_loader.load_data(
        symbol='AAPL',
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31)
    )

    # Create strategy
    strategy = ModularMomentumStrategy({'preset': 'conservative'})

    # Execute backtest
    result = executor.execute(quotes, strategy, strategy_name='example')
    print(f"Final Capital: ${result.final_capital}")
    print(f"Total Return: {result.total_return}%")


# Example 4: Using Orchestrator for multiple backtests
def example_using_orchestrator():
    """Example using BacktestOrchestrator for coordinated execution."""
    from app.backtesting.core import BacktestOrchestrator
    from app.backtesting.models import BacktestConfig
    from decimal import Decimal
    from app.strategies.momentum_modular.strategy import ModularMomentumStrategy

    # Create configuration
    config = BacktestConfig(
        initial_capital=Decimal('100000'),
        commission_per_trade=Decimal('1.0'),
        slippage_percentage=Decimal('0.1'),
    )

    # Create orchestrator
    orchestrator = BacktestOrchestrator(config)

    # Create multiple strategies
    strategies = [
        ModularMomentumStrategy({'preset': 'conservative'}),
        ModularMomentumStrategy({'preset': 'balanced'}),
        ModularMomentumStrategy({'preset': 'aggressive'}),
    ]

    # Load quotes (simplified)
    quotes = []  # In real usage, load from data source

    # Run all backtests
    results = orchestrator.run_all(quotes, strategies)

    # Get summary
    print(f"Total backtests: {results.total}")
    print(f"Successful: {results.summary['successful']}")
    print(f"Best Sharpe: {results.summary.get('best_sharpe', 'N/A')}")


# Example 5: Using BacktestDefaults for constants
def example_using_defaults():
    """Example using BacktestDefaults for centralized constants."""
    from app.backtesting.core import BacktestDefaults

    print("Default backtest parameters:")
    print(f"  Commission: ${BacktestDefaults.COMMISSION}")
    print(f"  Slippage: {BacktestDefaults.SLIPPAGE}")
    print(f"  Initial Capital: ${BacktestDefaults.INITIAL_CAPITAL}")

    print("\nMetric thresholds:")
    print(f"  Sharpe Excellent: {BacktestDefaults.SHARPE_RATIO_EXCELLENT}")
    print(f"  Sharpe Good: {BacktestDefaults.SHARPE_RATIO_GOOD}")
    print(f"  Win Rate Excellent: {BacktestDefaults.WIN_RATE_EXCELLENT}")


# Example 6: Custom parameter sweep
def example_parameter_sweep():
    """Example running parameter sweep using facade."""
    from app.backtesting.core import create_backtest_runner
    from app.strategies.momentum_modular.strategy import ModularMomentumStrategy

    # Create runner
    runner = create_backtest_runner("config/backtesting/comprehensive_backtest.yaml")
    asyncio.run(runner.load_data())

    # Define parameter ranges
    parameters = {
        'preset': ['conservative', 'balanced', 'aggressive'],
    }

    # Create strategy factory
    def strategy_factory(preset):
        return ModularMomentumStrategy({'preset': preset})

    # Run parameter sweep
    results = runner.run_parameter_sweep(
        strategy_factory=strategy_factory,
        parameters=parameters,
        test_name_prefix='preset_comparison'
    )

    # Find best result
    best = runner.get_best_result('sharpe_ratio')
    print(f"Best preset: {best['parameters']['preset']}")
    print(f"Sharpe Ratio: {best['sharpe_ratio']:.2f}")


if __name__ == "__main__":
    print("=== Backtesting Core Modules Examples ===\n")

    # Example 1: Using defaults
    print("Example 1: BacktestDefaults")
    example_using_defaults()
    print("\n" + "="*50 + "\n")

    # Example 2: Using config loader (if config exists)
    config_file = Path("config/backtesting/comprehensive_backtest.yaml")
    if config_file.exists():
        print("Example 2: BacktestConfigLoader")
        example_using_config_loader()
        print("\n" + "="*50 + "\n")
    else:
        print(f"Config file not found: {config_file}")
        print("Skipping config loader example.\n")
