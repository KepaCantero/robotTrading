#!/usr/bin/env python3
import logging
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

import pandas as pd

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.backtesting.multi_strategy_engine import MultiStrategyBacktester
from app.models.market_data import Quote
from app.services.portfolio_builder import PortfolioBuilder
from app.services.portfolio_config_manager import get_portfolio_config_manager
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.pairs_trading import PairsTradingStrategy
from tests.integration.data.test_data_loader import load_all_csv_data

"""
Test de comparación de estrategias - Ejecuta 4 backtests y genera comparativa.

Este test ejecuta backtests con:
1. Multi-strategy (all_strategies)
2. Solo Momentum
3. Solo Pairs Trading
4. Solo Mean Reversion

Y genera una comparativa de resultados al final.
"""


# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def dataframe_to_quotes(symbol: str, df: pd.DataFrame) -> List[Quote]:
    """Convert DataFrame to list of Quote objects."""
    quotes = []
    for idx, row in df.iterrows():
        try:
            timestamp = idx if isinstance(idx, datetime) else pd.to_datetime(idx).to_pydatetime()

            # Handle volume
            volume_raw = Decimal(str(row.get("volume", 0)))
            max_volume = Decimal("10000000000")  # 10B shares limit
            volume = min(volume_raw, max_volume) if volume_raw > 0 else Decimal("0")

            quote = Quote(
                symbol=symbol,
                bid=Decimal(str(row["close"])),
                ask=Decimal(str(row["close"])),
                last=Decimal(str(row["close"])),
                volume=volume,
                timestamp=timestamp,
                high=Decimal(str(row["high"])),
                low=Decimal(str(row["low"])),
                open=Decimal(str(row["open"])),
                close=Decimal(str(row["close"])),
            )
            quotes.append(quote)
        except Exception as e:
            logger.debug(f"Skipping row for {symbol} due to error: {e}")
            continue

    return quotes


class StrategyComparisonBacktest:
    """Ejecuta backtests de diferentes estrategias y genera comparativa."""

    def __init__(self, initial_capital: Decimal = Decimal("100000")):
        """Initialize with initial capital."""
        self.initial_capital = initial_capital
        self.results = {}

        # Common config preset
        self.config_preset = {
            "rsi_threshold": 40,
            "momentum_threshold": 0.005,
            "stop_loss": 3.0,
            "take_profit": 7.0,
            "z_score_threshold": 0.5,
            "min_z_score": 0.3,
            "volatility_threshold": 0.10,
            "spread_threshold": 0.3,
            "min_correlation": 0.4,
            "cointegration_threshold": 0.01,
        }

    def run_multi_strategy_backtest(self, portfolio_quotes: List[Quote]) -> Dict:
        """Ejecutar backtest multi-strategy."""
        logger.info("=" * 80)
        logger.info("TEST 1: Multi-Strategy Backtest")
        logger.info("=" * 80)

        try:
            # Get portfolio config
            portfolio_config = get_portfolio_config_manager()
            allocation_manager = portfolio_config.get_allocation_manager()
            allocation_manager.update_total_capital(self.initial_capital)

            # Create all strategies
            strategies = {}
            for strategy_type in ["momentum", "mean_reversion", "pairs_trading"]:
                config = {"name": strategy_type, **self.config_preset}
                if strategy_type == "momentum":
                    strategies[strategy_type] = MomentumStrategy(config)
                elif strategy_type == "mean_reversion":
                    strategies[strategy_type] = MeanReversionStrategy(config)
                elif strategy_type == "pairs_trading":
                    # Get pair symbols
                    portfolio_builder = PortfolioBuilder(portfolio_config=portfolio_config)
                    pair_symbols = portfolio_builder.get_strategy_symbols_mapping().get(
                        "pairs_trading", ["AAPL", "MSFT"]
                    )
                    if len(pair_symbols) >= 2:
                        config["pair_symbols"] = pair_symbols[:2]
                    else:
                        config["pair_symbols"] = ["AAPL", "MSFT"]
                    strategies[strategy_type] = PairsTradingStrategy(config)

            # Create multi-strategy backtester
            multi_backtester = MultiStrategyBacktester(
                allocation_manager=allocation_manager,
                strategies=strategies,
                config_params={
                    "commission": Decimal("1.0"),
                    "slippage": Decimal("0.05"),
                    "stop_loss": Decimal(str(self.config_preset["stop_loss"])),
                    "take_profit": Decimal(str(self.config_preset["take_profit"])),
                    "max_position_size": Decimal("0.05"),
                },
                portfolio_config_manager=portfolio_config,
            )

            # Get date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * 2)  # 2 years

            # Run backtest
            result = multi_backtester.run_multi_strategy_backtest(
                quotes=portfolio_quotes,
                start_date=start_date,
                end_date=end_date,
            )

            logger.info("✅ Multi-strategy backtest completed")
            return result

        except Exception as e:
            logger.error(f"❌ Multi-strategy backtest failed: {e}", exc_info=True)
            return None

    def run_single_strategy_backtest(self, strategy_name: str, quotes: List[Quote]) -> Dict:
        """Ejecutar backtest para una estrategia individual."""
        logger.info("=" * 80)
        logger.info(f"TEST: {strategy_name.upper()} Strategy Backtest")
        logger.info("=" * 80)

        try:
            # Create strategy
            config = {"name": strategy_name, **self.config_preset}

            if strategy_name == "momentum":
                strategy = MomentumStrategy(config)
            elif strategy_name == "mean_reversion":
                strategy = MeanReversionStrategy(config)
            elif strategy_name == "pairs_trading":
                # Get pair symbols from quotes
                symbols = list(set(q.symbol for q in quotes))
                if len(symbols) >= 2:
                    config["pair_symbols"] = symbols[:2]
                else:
                    config["pair_symbols"] = ["AAPL", "MSFT"]
                strategy = PairsTradingStrategy(config)
            else:
                raise ValueError(f"Unknown strategy: {strategy_name}")

            # Generate signals
            signals = []
            for quote in quotes:
                try:
                    signals.extend(strategy.generate_signals(quote))
                except Exception as e:
                    logger.debug(f"Signal error: {e}")

            if not signals:
                logger.warning(f"⚠️ {strategy_name} generated 0 signals")
                return None

            logger.info(f"✅ Generated {len(signals)} signals for {strategy_name}")

            # Create backtester config
            backtest_config = BacktestConfig(
                strategy_name=strategy_name,
                initial_capital=self.initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.05"),
                stop_loss_percentage=Decimal(str(self.config_preset["stop_loss"])),
                take_profit_percentage=Decimal(str(self.config_preset["take_profit"])),
                max_position_size=Decimal("0.05"),
            )

            # Run backtest
            backtester = SimpleBacktester(backtest_config)
            result = backtester.run_backtest(quotes, signals)

            logger.info(f"✅ {strategy_name} backtest completed")
            return result

        except Exception as e:
            logger.error(f"❌ {strategy_name} backtest failed: {e}", exc_info=True)
            return None

    def generate_comparison_report(self) -> str:
        """Generar reporte de comparativa."""
        logger.info("=" * 80)
        logger.info("📊 COMPARATIVE REPORT")
        logger.info("=" * 80)

        if not self.results:
            return "No results to compare"

        # Extract metrics
        comparison_data = []

        # Ensure we show all strategies, even if they failed
        expected_strategies = ["multi_strategy", "momentum", "pairs_trading", "mean_reversion"]
        for strategy_name in expected_strategies:
            result = self.results.get(strategy_name)

            if result is None:
                # Strategy failed or returned None - show placeholder
                metrics = {
                    "Strategy": strategy_name.replace("_", " ").title(),
                    "Total Trades": 0,
                    "Win Rate": "N/A",
                    "Total P&L": "$0.00",
                    "Final Capital": f"${float(self.initial_capital):,.2f}",
                    "Return %": "0.00%",
                    "Sharpe Ratio": "N/A",
                    "Max Drawdown": "N/A",
                }
                comparison_data.append(metrics)
                logger.warning(f"⚠️ {strategy_name} result is None - showing placeholder in report")
                continue

            if strategy_name == "multi_strategy":
                # Multi-strategy uses 'combined' metrics in MultiStrategyBacktester
                if isinstance(result, dict) and "combined" in result:
                    combined = result["combined"]
                    total_initial = float(combined.get("total_initial_capital", 0))
                    total_final = float(combined.get("total_final_capital", 0))
                    total_pnl = total_final - total_initial
                    total_return_pct = float(combined.get("total_return", 0))
                    weighted_sharpe = combined.get("weighted_sharpe", None)
                    weighted_max_dd = combined.get("weighted_max_dd", None)

                    metrics = {
                        "Strategy": "Multi-Strategy",
                        "Total Trades": int(combined.get("total_trades", 0)),
                        "Win Rate": "N/A",  # Not directly available in combined metrics
                        "Total P&L": f"${total_pnl:,.2f}",
                        "Final Capital": f"${total_final:,.2f}",
                        "Return %": f"{total_return_pct:.2f}%",
                        "Sharpe Ratio": (
                            f"{float(weighted_sharpe):.2f}"
                            if weighted_sharpe is not None
                            else "N/A"
                        ),
                        "Max Drawdown": (
                            f"{float(weighted_max_dd):.2f}%"
                            if weighted_max_dd is not None
                            else "N/A"
                        ),
                    }
                else:
                    continue
            else:
                # Single strategy - BacktestResult object
                metrics = {
                    "Strategy": strategy_name.replace("_", " ").title(),
                    "Total Trades": result.performance.total_trades,
                    "Win Rate": f"{float(result.performance.win_rate):.2f}%",
                    "Total P&L": f"${float(result.performance.total_pnl):,.2f}",
                    "Final Capital": f"${float(result.final_capital):,.2f}",
                    "Return %": f"{float(result.total_return):.2f}%",
                    "Sharpe Ratio": (
                        f"{float(result.performance.sharpe_ratio):.2f}"
                        if result.performance.sharpe_ratio
                        else "N/A"
                    ),
                    "Max Drawdown": f"{float(result.performance.max_drawdown_percentage):.2f}%",
                }

            comparison_data.append(metrics)

        # Create DataFrame
        df = pd.DataFrame(comparison_data)

        # Print formatted report
        print("\n" + "=" * 100)
        print("📊 STRATEGY COMPARISON REPORT")
        print("=" * 100)
        print(df.to_string(index=False))
        print("=" * 100 + "\n")

        # Find best strategy by different metrics
        if len(comparison_data) > 1:
            print("🏆 BEST PERFORMERS:")
            print("-" * 100)

            # Best by Win Rate (skip entries with N/A)
            win_rate_candidates = [
                s
                for s in comparison_data
                if isinstance(s.get("Win Rate"), str)
                and s["Win Rate"].endswith('%')
                and s["Win Rate"] != "N/A"
            ]
            if win_rate_candidates:
                best_win_rate = max(
                    win_rate_candidates, key=lambda x: float(x["Win Rate"].replace("%", ""))
                )
                print(
                    f"  ✅ Best Win Rate: {best_win_rate['Strategy']} ({best_win_rate['Win Rate']})"
                )

            # Best by Total P&L
            best_pnl = max(
                comparison_data,
                key=lambda x: float(x["Total P&L"].replace("$", "").replace(",", "")),
            )
            print(f"  💰 Best Total P&L: {best_pnl['Strategy']} ({best_pnl['Total P&L']})")

            # Best by Return %
            best_return = max(comparison_data, key=lambda x: float(x["Return %"].replace("%", "")))
            print(f"  📈 Best Return: {best_return['Strategy']} ({best_return['Return %']})")

            # Best by Sharpe Ratio (if available)
            sharpe_strategies = [s for s in comparison_data if s["Sharpe Ratio"] != "N/A"]
            if sharpe_strategies:
                best_sharpe = max(sharpe_strategies, key=lambda x: float(x["Sharpe Ratio"]))
                print(
                    f"  📊 Best Sharpe Ratio: {best_sharpe['Strategy']} ({best_sharpe['Sharpe Ratio']})"
                )

            # Best by Max Drawdown (lowest is best)
            best_dd = min(comparison_data, key=lambda x: float(x["Max Drawdown"].replace("%", "")))
            print(f"  📉 Lowest Max Drawdown: {best_dd['Strategy']} ({best_dd['Max Drawdown']})")

            print("-" * 100 + "\n")

        return df.to_string(index=False)


def run_strategy_comparison_tests():
    """Ejecutar todos los tests de comparación."""
    logger.info("🚀 Starting Strategy Comparison Backtests")

    # Load historical data
    logger.info("Loading historical data...")
    historical_data = load_all_csv_data()

    if len(historical_data) == 0:
        logger.error("❌ No historical data loaded!")
        return

    logger.info(f"✅ Loaded {len(historical_data)} symbols")

    # Convert to quotes
    all_quotes = []
    for symbol, df in list(historical_data.items())[:20]:  # Limit to 20 symbols for speed
        quotes = dataframe_to_quotes(symbol, df)
        all_quotes.extend(quotes[-500:])  # Last 500 quotes per symbol

    logger.info(f"✅ Prepared {len(all_quotes)} quotes")

    # Initialize comparison runner
    comparator = StrategyComparisonBacktest(initial_capital=Decimal("100000"))

    # TEST 1: Multi-strategy
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1/4: Multi-Strategy")
    logger.info("=" * 80)
    multi_result = comparator.run_multi_strategy_backtest(all_quotes)
    comparator.results["multi_strategy"] = multi_result

    # TEST 2: Momentum only
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2/4: Momentum Only")
    logger.info("=" * 80)
    momentum_quotes = [
        q for q in all_quotes if q.symbol in ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"][:3]
    ]
    momentum_result = comparator.run_single_strategy_backtest("momentum", momentum_quotes)
    comparator.results["momentum"] = momentum_result

    # TEST 3: Pairs Trading only
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3/4: Pairs Trading Only")
    logger.info("=" * 80)
    pairs_quotes = [q for q in all_quotes if q.symbol in ["AAPL", "MSFT", "GOOGL", "AMZN"][:2]]
    pairs_result = comparator.run_single_strategy_backtest("pairs_trading", pairs_quotes)
    comparator.results["pairs_trading"] = pairs_result

    # TEST 4: Mean Reversion only
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4/4: Mean Reversion Only")
    logger.info("=" * 80)
    meanrev_quotes = [
        q for q in all_quotes if q.symbol in ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"][:3]
    ]
    meanrev_result = comparator.run_single_strategy_backtest("mean_reversion", meanrev_quotes)
    comparator.results["mean_reversion"] = meanrev_result

    # Generate comparison report
    logger.info("\n" + "=" * 80)
    logger.info("Generating Comparison Report...")
    logger.info("=" * 80)
    report = comparator.generate_comparison_report()

    # Save report to file
    report_file = (
        project_root
        / "docs"
        / "BACKTEST_RESULTS"
        / f"strategy_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w") as f:
        f.write("STRATEGY COMPARISON BACKTEST REPORT\n")
        f.write("=" * 100 + "\n\n")
        f.write(report)
        f.write("\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    logger.info(f"✅ Report saved to: {report_file}")
    logger.info("\n✅ All comparison tests completed!")


if __name__ == "__main__":
    run_strategy_comparison_tests()
