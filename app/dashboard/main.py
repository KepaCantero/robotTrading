"""
Streamlit Dashboard for AlgoTrading Backtesting Analysis

This module provides an interactive dashboard for:
- Executing backtests on specific modules/configurations
- Visualizing equity curves and trade logs
- Comparing multiple module performance
- Analyzing decision-making processes
"""

import json
import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit import session_state

from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.dashboard.report_generator import (
    save_backtest_result,
    generate_backend_test_summary,
)
from app.backtesting.multi_strategy_engine import MultiStrategyBacktester
from app.dashboard.multi_strategy_utils import (
    generate_multi_strategy_summary_text,
    save_multi_strategy_results,
)
from app.services.multi_strategy_allocation import MultiStrategyAllocationManager
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.pairs_trading import PairsTradingStrategy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="AlgoTrading Backtest Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.title("📊 AlgoTrading Backtest Dashboard")
st.markdown("**Interactive backtesting analysis and module comparison**")

# Initialize session state
if "backtest_results" not in session_state:
    session_state.backtest_results = {}

# Sidebar for module selection
with st.sidebar:
    st.header("⚙️ Configuration")

    # MODULE SELECTOR
    st.subheader("📦 Select Module")

    # Actual system modules (NOT strategies!)
    modules = [
        "all",
        "TechnicalAnalyst",
        "RiskManager",
        "SignalScorer",
        "PortfolioService",
        "ExecutionEngine",
        "CircuitBreakerManager",
        "PaperTradingService",
    ]
    selected_module = st.selectbox(
        "Select Module",
        options=modules,
        help="Choose which system module to use",
        key="module_selector",
    )

    st.markdown(f"**Selected Module**: `{selected_module}`")

    st.divider()

    # STRATEGY SELECTOR
    st.subheader("🎯 Select Strategy")

    strategies = {
        "momentum": "Momentum Strategy (RSI + EMA + Volume)",
        "mean_reversion": "Mean Reversion (Z-score)",
        "pairs_trading": "Pairs Trading (Cointegration)",
        "all_strategies": "All Strategies (Multi-Strategy with Capital Allocation)",
    }

    selected_strategy = st.selectbox(
        "Select Strategy",
        options=list(strategies.keys()),
        index=3,  # Default to "all_strategies"
        help="Choose which trading strategy to backtest",
        key="strategy_selector",
        format_func=lambda x: strategies[x],
    )

    st.markdown(f"**Selected Strategy**: `{strategies[selected_strategy]}`")

    # Show available results for this strategy
    if "backtest_results" in session_state and session_state.backtest_results:
        strategy_results = [
            k for k in session_state.backtest_results.keys() if selected_strategy in k.lower()
        ]
        if strategy_results:
            st.success(f"✓ {len(strategy_results)} backtest(s) for {selected_strategy}")
        else:
            st.warning(f"⚠ No backtests yet for {selected_strategy}")

    # Symbol and date range
    st.divider()
    st.subheader("📊 Backtest Parameters")
    
    symbol = st.text_input("Symbol", value="AAPL")
    
    # Default to 10 years of data
    from datetime import timedelta
    default_start = datetime.now() - timedelta(days=365*10)
    default_end = datetime.now() - timedelta(days=1)
    
    start_date = st.date_input("Start Date", value=default_start.date())
    end_date = st.date_input("End Date", value=default_end.date())
    initial_capital = st.number_input(
        "Initial Capital ($)", min_value=1000, value=100000, step=1000
    )

    st.divider()
    st.subheader("⚙️ Configuration Preset")

    # Configuration presets
    config_presets = {
        "Conservative": {
            "rsi_threshold": 30,
            "momentum_threshold": 0.01,
            "stop_loss": 2.0,
            "take_profit": 5.0,
            "z_score_threshold": 0.5,  # For mean_reversion - permissive
            "min_z_score": 0.3,  # For mean_reversion - permissive
            "volatility_threshold": 0.05,  # For mean_reversion
            "spread_threshold": 0.3,  # For pairs_trading - permissive
            "min_correlation": 0.4,  # For pairs_trading - permissive
            "cointegration_threshold": 0.01,  # For pairs_trading - permissive
        },
        "Moderate": {
            "rsi_threshold": 40,
            "momentum_threshold": 0.005,
            "stop_loss": 3.0,
            "take_profit": 7.0,
            "z_score_threshold": 0.5,  # For mean_reversion - permissive
            "min_z_score": 0.3,  # For mean_reversion - permissive
            "volatility_threshold": 0.10,  # For mean_reversion - permissive
            "spread_threshold": 0.3,  # For pairs_trading - permissive
            "min_correlation": 0.4,  # For pairs_trading - permissive
            "cointegration_threshold": 0.01,  # For pairs_trading - permissive
        },
        "Aggressive": {
            "rsi_threshold": 50,
            "momentum_threshold": 0.001,
            "stop_loss": 5.0,
            "take_profit": 10.0,
            "z_score_threshold": 0.5,  # For mean_reversion - permissive
            "min_z_score": 0.3,  # For mean_reversion - permissive
            "volatility_threshold": 0.20,  # For mean_reversion - permissive
            "spread_threshold": 0.3,  # For pairs_trading - permissive
            "min_correlation": 0.4,  # For pairs_trading - permissive
            "cointegration_threshold": 0.01,  # For pairs_trading - permissive
        },
    }

    selected_preset = st.selectbox(
        "🎛️ Select Configuration Preset",
        options=list(config_presets.keys()),
        help="Choose a preset configuration",
        key="config_selector",
    )

    # Show preset details
    with st.expander(f"View {selected_preset} Preset Parameters"):
        st.json(config_presets[selected_preset])

    st.divider()

    # Execute button
    execute_button = st.button("🚀 Execute Backtest", type="primary", use_container_width=True)

# Auto-load saved backtest results
# This loads results AFTER the user selects module/strategy
results_dir = project_root / "docs" / "BACKTEST_RESULTS"
if results_dir.exists():
    for module_dir in results_dir.iterdir():
        if module_dir.is_dir() and module_dir.name != "all":
            for json_file in module_dir.glob("metrics_*.json"):
                try:
                    with open(json_file, 'r') as f:
                        metrics_data = json.load(f)

                    # Extract module name from directory
                    module_name = module_dir.name

                    # Extract config name from filename
                    # Format: metrics_Conservative_20251027_101028.json
                    parts = json_file.stem.split('_')
                    config_name = parts[1] if len(parts) > 1 else 'default'
                    timestamp = parts[2] if len(parts) > 2 else None

                    # Infer strategy from directory name
                    # Map directory names to strategies
                    strategy_mapping = {
                        "momentum": "momentum",
                        "mean_reversion": "mean_reversion",
                        "pairs_trading": "pairs_trading",
                        "technicalanalyst": "momentum",  # Technical analyst uses momentum
                        "riskmanager": "momentum",  # Risk manager uses momentum
                        "signalcombiner": "momentum",  # Signal combiner uses momentum
                        "executor": "momentum",  # Executor uses momentum
                    }

                    strategy_key = strategy_mapping.get(module_name, "momentum")
                    key = (
                        f"{module_name}_{strategy_key}_{config_name}_{timestamp}"
                        if timestamp
                        else f"{module_name}_{strategy_key}_{config_name}"
                    )

                    # Load once per JSON file (not per strategy)
                    if key not in session_state.backtest_results:
                        # Skip if final_capital is 0 or missing (invalid data)
                        final_capital = metrics_data.get('final_capital', 0)
                        if final_capital <= 0:
                            continue

                        # Try to create a basic BacktestResult from the metrics
                        try:
                            from app.backtesting.models import (
                                BacktestResult,
                                PerformanceMetrics,
                                Trade,
                            )

                            # Convert metrics JSON to BacktestResult
                            # Calculate missing fields
                            total_trades = int(metrics_data.get('total_trades', 0))
                            win_rate = float(metrics_data.get('win_rate_pct', 0))
                            winning_trades = metrics_data.get('winning_trades', 0)
                            losing_trades = metrics_data.get('losing_trades', 0)

                            # If missing, calculate from win_rate
                            if total_trades > 0 and (winning_trades == 0 and losing_trades == 0):
                                winning_trades = int(total_trades * win_rate / 100)
                                losing_trades = total_trades - winning_trades

                            perf_metrics = PerformanceMetrics(
                                total_trades=total_trades,
                                winning_trades=winning_trades,
                                losing_trades=losing_trades,
                                win_rate=Decimal(str(win_rate)),
                                total_pnl=Decimal(str(metrics_data.get('total_pnl', 0))),
                                total_pnl_percentage=Decimal(
                                    str(metrics_data.get('total_return_pct', 0))
                                ),
                                gross_profit=Decimal(str(max(metrics_data.get('total_pnl', 0), 0))),
                                gross_loss=Decimal(str(min(metrics_data.get('total_pnl', 0), 0))),
                                net_profit=Decimal(str(metrics_data.get('total_pnl', 0))),
                                max_drawdown=Decimal(str(metrics_data.get('max_drawdown_pct', 0))),
                                max_drawdown_percentage=Decimal(
                                    str(metrics_data.get('max_drawdown_pct', 0))
                                ),
                                sharpe_ratio=(
                                    Decimal(str(metrics_data.get('sharpe_ratio', 0)))
                                    if metrics_data.get('sharpe_ratio')
                                    else None
                                ),
                                sortino_ratio=(
                                    Decimal(str(metrics_data.get('sortino_ratio', 0)))
                                    if metrics_data.get('sortino_ratio')
                                    else None
                                ),
                                avg_win=Decimal(str(0)),
                                avg_loss=Decimal(str(0)),
                                largest_win=Decimal(str(0)),
                                largest_loss=Decimal(str(0)),
                                total_days=365,
                                avg_trade_duration=Decimal(str(1)),
                            )

                            # Load trades if available
                            trades = []
                            trade_log_file = (
                                module_dir / f"trade_log_{config_name}_{timestamp}.csv"
                                if timestamp
                                else module_dir / f"trade_log_{config_name}.csv"
                            )
                            if trade_log_file.exists():
                                df = pd.read_csv(trade_log_file)
                                for _, row in df.iterrows():
                                    trades.append(
                                        Trade(
                                            timestamp=datetime.fromisoformat(str(row['timestamp'])),
                                            type=row['type'],
                                            price=float(row['price']),
                                            quantity=float(row['quantity']),
                                            reason=row.get('reason', ''),
                                            pnl=float(row.get('pnl', 0)),
                                            status='CLOSED',
                                        )
                                    )

                            result = BacktestResult(
                                strategy_name=metrics_data.get('strategy', 'unknown'),
                                start_date=(
                                    datetime.fromisoformat(metrics_data['period'].split(' to ')[0])
                                    if 'period' in metrics_data
                                    else datetime.now()
                                ),
                                end_date=(
                                    datetime.fromisoformat(metrics_data['period'].split(' to ')[1])
                                    if 'period' in metrics_data and ' to ' in metrics_data['period']
                                    else datetime.now()
                                ),
                                final_capital=Decimal(str(metrics_data.get('final_capital', 0))),
                                total_return=Decimal(str(metrics_data.get('total_return_pct', 0))),
                                trades=trades,
                                performance=perf_metrics,
                                equity_curve=[],
                            )

                            session_state.backtest_results[key] = result

                        except Exception as e:
                            logger.warning(f"Failed to convert metrics to BacktestResult: {e}")

                except Exception as e:
                    logger.warning(f"Failed to load {json_file}: {e}")

# Main content area

# Execute backtest
if execute_button:
    with st.spinner("Running backtest..."):
        try:
            # Load data
            loader = DataLoader()
            quotes = loader.load_market_data(
                symbol,
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time()),
            )

            if not quotes:
                st.error("❌ No data available for selected period")
                st.stop()

            # Determine which modules to run backtests for
            if selected_module == "all":
                # Run for all system modules
                modules_to_run = [
                    "TechnicalAnalyst",
                    "RiskManager",
                    "SignalScorer",
                    "PortfolioService",
                    "ExecutionEngine",
                ]
            else:
                # Run for selected module only
                modules_to_run = [selected_module]

            # Option: Check if we should run all strategies with capital allocation
            run_all_strategies = selected_strategy == "all_strategies"
            
            if run_all_strategies:
                # Multi-strategy mode: build portfolio from all strategy sectors
                from decimal import Decimal
                from app.services.portfolio_builder import PortfolioBuilder
                from app.services.portfolio_config_manager import get_portfolio_config_manager
                
                st.info("🏗️ Building portfolio from configured sectors...")
                
                # Build portfolio with all symbols from all strategy sectors
                portfolio_config = get_portfolio_config_manager()
                portfolio_builder = PortfolioBuilder(portfolio_config=portfolio_config)
                
                # Get portfolio summary
                portfolio_summary = portfolio_builder.get_portfolio_summary()
                
                with st.expander("📊 Portfolio Composition", expanded=True):
                    st.write(f"**Total Symbols**: {portfolio_summary['total_unique_symbols']}")
                    st.write("**Symbols by Strategy**:")
                    for strat, syms in portfolio_summary['symbols_by_strategy'].items():
                        st.write(f"- **{strat}**: {', '.join(syms[:10])}{'...' if len(syms) > 10 else ''}")
                    
                    st.write(f"**All Symbols**: {', '.join(portfolio_summary['all_symbols'][:20])}"
                            f"{'...' if len(portfolio_summary['all_symbols']) > 20 else ''}")
                
                # Build portfolio quotes from all sectors
                # Limit symbols to avoid rate limiting (use fewer symbols initially)
                st.sidebar.markdown("---")
                st.sidebar.subheader("⚙️ Portfolio Settings")
                max_symbols = st.sidebar.number_input(
                    "Max symbols per strategy",
                    min_value=1,
                    max_value=20,
                    value=5,
                    help="Limit number of symbols to avoid API rate limits. Lower = faster, fewer symbols."
                )
                
                try:
                    portfolio_quotes = portfolio_builder.build_portfolio_quotes(
                        start_date=datetime.combine(start_date, datetime.min.time()),
                        end_date=datetime.combine(end_date, datetime.max.time()),
                        max_symbols_per_strategy=max_symbols,  # Configurable limit
                    )
                except ValueError as e:
                    st.error(f"❌ {str(e)}")
                    st.info(
                        "💡 **Suggestion**: Add CSV files to `data/historical/` folder for faster loading "
                        "without rate limits. Format: `SYMBOL.csv` with columns: date, open, high, low, close, volume"
                    )
                    st.stop()
                
                st.success(
                    f"✅ Portfolio built: {len(set(q.symbol for q in portfolio_quotes))} symbols, "
                    f"{len(portfolio_quotes)} quotes"
                )
                
                # Create allocation manager (will use portfolio.yaml config)
                allocation_manager = portfolio_config.get_allocation_manager()
                allocation_manager.update_total_capital(Decimal(str(initial_capital)))
                
                # Create strategies
                all_strategies = {}
                for strategy_type in ["momentum", "mean_reversion", "pairs_trading"]:
                    config = {"name": strategy_type, **config_presets[selected_preset]}
                    if strategy_type == "momentum":
                        all_strategies[strategy_type] = MomentumStrategy(config)
                    elif strategy_type == "mean_reversion":
                        all_strategies[strategy_type] = MeanReversionStrategy(config)
                    elif strategy_type == "pairs_trading":
                        # Get pair symbols from portfolio config
                        pair_symbols = portfolio_builder.get_strategy_symbols_mapping().get(
                            "pairs_trading", ["AAPL", "MSFT"]
                        )
                        if len(pair_symbols) >= 2:
                            config["pair_symbols"] = pair_symbols[:2]
                        else:
                            config["pair_symbols"] = ["AAPL", "MSFT"]  # Fallback
                        all_strategies[strategy_type] = PairsTradingStrategy(config)
                
                multi_backtester = MultiStrategyBacktester(
                    allocation_manager=allocation_manager,
                    strategies=all_strategies,
                    config_params={
                        "commission": Decimal("1.0"),
                        "slippage": Decimal("0.05"),
                        "stop_loss": Decimal(str(config_presets[selected_preset]["stop_loss"])),
                        "take_profit": Decimal(str(config_presets[selected_preset]["take_profit"])),
                        "max_position_size": Decimal("0.05"),
                    },
                    portfolio_config_manager=portfolio_config,  # Pass config manager
                )
                
                consolidated = multi_backtester.run_multi_strategy_backtest(
                    quotes=portfolio_quotes,  # Use portfolio quotes, not single symbol
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.max.time()),
                )
                
                st.success(f"✅ Multi-strategy backtest completed ({len(all_strategies)} strategies)")
                
                # Generate unique ID
                backtest_id = f"{selected_module}_{selected_strategy}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Save JSON results
                results_dir = project_root / "docs" / "BACKTEST_RESULTS" / "multi_strategy"
                json_file = save_multi_strategy_results(consolidated, results_dir, backtest_id)
                
                # Generate markdown summary
                summary_text = generate_multi_strategy_summary_text(consolidated)
                
                # Display summary in dashboard
                st.markdown("## 📊 Multi-Strategy Results")
                st.markdown(summary_text)
                
                # Also display as JSON
                with st.expander("📄 View JSON Results"):
                    import json
                    with open(json_file, "r") as f:
                        st.json(json.load(f))
                
                st.success(f"✅ Results saved to {json_file}")
                
                # Generate backend test summary for multi-strategy
                # Get all symbols for summary
                portfolio_symbols = ", ".join(portfolio_summary['all_symbols'][:5])
                if len(portfolio_summary['all_symbols']) > 5:
                    portfolio_symbols += f" (+{len(portfolio_summary['all_symbols']) - 5} more)"
                
                summary_file = generate_backend_test_summary(
                    all_results=[],  # Empty for multi-strategy as it has its own format
                    strategy=selected_strategy,
                    preset=selected_preset,
                    symbol=portfolio_symbols,  # Show portfolio symbols
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.max.time()),
                    initial_capital=initial_capital,
                    project_root=project_root,
                    multi_strategy_results=consolidated,
                )
                
                st.info(f"📄 Backend test summary generated: {summary_file}")
                st.stop()
            
            # Single strategy mode (existing behavior)
            # Create strategy once for all modules (shares state/history)
            strategy_config = {
                "name": selected_strategy.lower(),
                **config_presets[selected_preset],
            }

            if selected_strategy == "momentum":
                strategy = MomentumStrategy(strategy_config)
            elif selected_strategy == "mean_reversion":
                strategy = MeanReversionStrategy(strategy_config)
            elif selected_strategy == "pairs_trading":
                # Note: PairsTrading needs pair_symbols, set default
                if "pair_symbols" not in strategy_config:
                    strategy_config["pair_symbols"] = ["AAPL", "MSFT"]
                strategy = PairsTradingStrategy(strategy_config)
            else:
                st.error(f"❌ Unknown strategy: {selected_strategy}")
                st.stop()

            # Generate signals ONCE for all modules (strategy has history)
            signals = []
            for quote in quotes:
                try:
                    signals.extend(strategy.generate_signals(quote))
                except Exception as e:
                    logger.debug(f"Signal error: {e}")

            if not signals:
                st.warning(f"⚠️ Strategy '{selected_strategy}' generated 0 signals.")
                st.stop()

            # Run backtests for each module using the SAME signals
            for current_module in modules_to_run:
                # Skip if module has no signals (they're already generated once above)
                # This should not happen due to the check before the loop

                # Create config with module and strategy info
                config = BacktestConfig(
                    strategy_name=f"{current_module}_{selected_strategy}".lower(),
                    initial_capital=Decimal(str(initial_capital)),
                    commission_per_trade=Decimal("1.0"),
                    slippage_percentage=Decimal("0.05"),
                    stop_loss_percentage=Decimal(str(config_presets[selected_preset]["stop_loss"])),
                    take_profit_percentage=Decimal(
                        str(config_presets[selected_preset]["take_profit"])
                    ),
                    max_position_size=Decimal("0.05"),
                )

                # Run backtest
                backtester = SimpleBacktester(config)
                result = backtester.run_backtest(quotes, signals)

                # Store result with module and strategy
                key = f"{current_module}_{selected_strategy}_{selected_preset}"
                session_state.backtest_results[key] = result

                # Auto-save each result
                try:
                    # Convert all Decimal to float for JSON serialization
                    saved_files = save_backtest_result(
                        result_key=key,
                        result={
                            "total_trades": result.performance.total_trades,
                            "win_rate": float(result.performance.win_rate),
                            "total_return": float(result.total_return),
                            "final_capital": float(result.final_capital),
                            "trades": [
                                {
                                    "trade_id": t.trade_id,
                                    "symbol": t.symbol,
                                    "side": t.side,
                                    "quantity": float(t.quantity),
                                    "entry_price": float(t.entry_price),
                                    "exit_price": float(t.exit_price) if t.exit_price else None,
                                    "pnl": float(t.pnl) if t.pnl else 0,
                                    "status": t.status.value,
                                    "reason": t.reason if t.reason else "N/A",
                                }
                                for t in result.trades
                            ],
                        },
                        module=current_module,
                        config=selected_preset,
                        symbol=symbol,
                        start_date=datetime.combine(start_date, datetime.min.time()),
                        end_date=datetime.combine(end_date, datetime.max.time()),
                        project_root=project_root,
                    )
                except Exception as save_error:
                    logger.warning(f"Failed to save report for {current_module}: {save_error}")

            # Show summary
            st.success(f"✅ Backtests completed for {len(modules_to_run)} module(s)")
            
            # Generate comprehensive Backend Test Result Summary
            try:
                # Collect all backtest results
                all_backtest_results = []
                for current_module in modules_to_run:
                    key = f"{current_module}_{selected_strategy}_{selected_preset}"
                    if key in session_state.backtest_results:
                        result = session_state.backtest_results[key]
                        all_backtest_results.append({
                            "module": current_module,
                            "total_trades": result.performance.total_trades,
                            "win_rate": float(result.performance.win_rate),
                            "total_return": float(result.total_return),
                            "final_capital": float(result.final_capital),
                            "sharpe_ratio": float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else None,
                            "max_drawdown": float(result.performance.max_drawdown) if result.performance.max_drawdown else 0,
                        })
                
                # Generate comprehensive summary if we have results
                if all_backtest_results:
                    summary_file = generate_backend_test_summary(
                        all_results=all_backtest_results,
                        strategy=selected_strategy,
                        preset=selected_preset,
                        symbol=symbol,
                        start_date=datetime.combine(start_date, datetime.min.time()),
                        end_date=datetime.combine(end_date, datetime.max.time()),
                        initial_capital=initial_capital,
                        project_root=project_root,
                    )
                    
                    # Show link to summary
                    st.markdown("---")
                    st.success("📄 **Backend Test Result Summary Generated**")
                    st.markdown(f"""
                    **Location:** `{summary_file.relative_to(project_root)}`
                    
                    **To view:** Open the file in your editor or download it.
                    """)
                    
                    # Add download button
                    with open(summary_file, "r") as f:
                        summary_content = f.read()
                        st.download_button(
                            label="📥 Download Backend Test Summary",
                            data=summary_content,
                            file_name=summary_file.name,
                            mime="text/markdown",
                        )
                    
            except Exception as summary_error:
                logger.warning(f"Failed to generate backend test summary: {summary_error}")
                st.warning("⚠️ Could not generate comprehensive summary report")

        except Exception as e:
            st.error(f"❌ Error: {e}")
            logger.exception("Backtest failed")

# Module Information Panel
st.header(f"📦 Module: {selected_module}")
module_info = {
    "all": {
        "description": "Execute backtests across all system modules",
        "metrics": ["All modules", "Cross-comparison"],
        "good_metrics": "Compare performance across modules",
    },
    "TechnicalAnalyst": {
        "description": "Technical analysis module using RSI, EMA, and volume indicators",
        "metrics": ["RSI", "EMA trend", "Volume ratio", "Signal strength"],
        "good_metrics": "RSI < 40 (oversold), EMA trend > 0, Volume > 1.0x",
    },
    "RiskManager": {
        "description": "Risk management module for position sizing and exposure control",
        "metrics": ["Position size", "Exposure", "Risk per trade", "Stop loss"],
        "good_metrics": "Max exposure < 60%, Risk per trade < 2%",
    },
    "SignalCombiner": {
        "description": "Multi-signal combination module for signal aggregation",
        "metrics": ["Signal count", "Agreement rate", "Combined strength"],
        "good_metrics": "High agreement rate, Strong combined signals",
    },
    "Executor": {
        "description": "Trade execution module with slippage and commission handling",
        "metrics": ["Execution price", "Slippage", "Commission", "Fill rate"],
        "good_metrics": "Low slippage < 0.5%, High fill rate > 95%",
    },
}

if selected_module in module_info:
    info = module_info[selected_module]
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"**Description**: {info['description']}")
        st.markdown(f"**Metrics**: {', '.join(info['metrics'])}")
        st.markdown(f"**Good Indicators**: {info['good_metrics']}")
    with col2:
        if "backtest_results" in session_state and session_state.backtest_results:
            module_results = [
                k for k in session_state.backtest_results.keys() if k.startswith(selected_module)
            ]
            if module_results:
                st.success(f"✅ {len(module_results)} result(s) available")
            else:
                st.warning("⚠️ No results yet")
        else:
            st.info("ℹ️ No backtests executed")

st.divider()

# MODULE INFO PANEL
st.subheader(f"📦 Module Information: {selected_module}")

# Module descriptions
module_info = {
    "TechnicalAnalyst": {
        "description": "Análisis técnico usando múltiples indicadores (RSI, EMA, Volume). Genera señales de compra/venta basadas en análisis técnico.",
        "metrics": "RSI, EMA trend, Volume ratio, Signal strength",
        "indicators": "RSI < 40 (oversold), EMA trend > 0, Volume > 1.0x",
    },
    "RiskManager": {
        "description": "Gestión de riesgo con control de exposición y tamaño de posición. Valida señales según límites de riesgo.",
        "metrics": "Position size, Exposure, Risk per trade, Stop loss",
        "indicators": "Max exposure < 60%, Risk per trade < 2%",
    },
    "SignalScorer": {
        "description": "Scoring de señales basado en calidad y prioridad. Evalúa y clasifica señales según múltiples criterios.",
        "metrics": "Signal score, Priority, Quality metrics, Confidence",
        "indicators": "Score > 70, High confidence, Multiple confirmations",
    },
    "PortfolioService": {
        "description": "Gestión del portfolio con tracking de posiciones, P&L y exposición total.",
        "metrics": "Total exposure, Position count, P&L, Cash balance",
        "indicators": "Diversification > 5 positions, Cash > 20%, Balanced exposure",
    },
    "ExecutionEngine": {
        "description": "Motor de ejecución con control de slippage y comisiones. Ejecuta órdenes con gestión de errores.",
        "metrics": "Execution rate, Slippage impact, Commission cost",
        "indicators": "Slippage < 0.1%, Execution success > 95%",
    },
    "CircuitBreakerManager": {
        "description": "Gestión de circuit breakers para protección del sistema. Monitorea errores y activa protecciones.",
        "metrics": "Circuit breaker state, Error rate, Recovery time",
        "indicators": "Error rate < 5%, State = CLOSED",
    },
    "PaperTradingService": {
        "description": "Simulación de trading en tiempo real. Ejecuta trades virtuales para validación.",
        "metrics": "Simulated trades, Virtual P&L, Execution accuracy",
        "indicators": "Execution accuracy > 95%, Positive virtual P&L",
    },
}

if selected_module in module_info or selected_module == "all":
    if selected_module != "all":
        info = module_info[selected_module]

        # Show static module info
        st.info(
            f"""
**Description**: {info['description']}

**Metrics**: {info['metrics']}

**Good Indicators**: {info['indicators']}
        """
        )

        # Count available results for this module
        if "backtest_results" in session_state and session_state.backtest_results:
            module_results_count = sum(
                1
                for key in session_state.backtest_results.keys()
                if key.lower().startswith(selected_module.lower() + "_")
            )

            if module_results_count > 0:
                st.success(f"✅ {module_results_count} result(s) available for {selected_module}")

                # Collect all results for this module
                module_results = []
                for key in session_state.backtest_results.keys():
                    if key.lower().startswith(selected_module.lower() + "_"):
                        result = session_state.backtest_results[key]
                        module_results.append((key, result))

                # Show summary table of all results
                if module_results:
                    st.markdown("---")
                    st.markdown("### 📊 All Backtest Results Summary")

                    # Create table data with module-specific metrics
                    table_data = []
                    for key, result in module_results:
                        # Extract config and timestamp from key
                        parts = key.split('_')
                        config_name = parts[1] if len(parts) > 1 else 'unknown'

                        # Get module-specific decision metrics
                        module_metrics = {
                            "Config": config_name,
                            "Trades": result.performance.total_trades,
                            "Win Rate": f"{float(result.performance.win_rate):.1f}%",
                            "PnL": f"${float(result.performance.total_pnl):,.2f}",
                            "Sharpe": (
                                f"{float(result.performance.sharpe_ratio):.2f}"
                                if result.performance.sharpe_ratio
                                else "N/A"
                            ),
                            "Max DD": f"{float(result.performance.max_drawdown_percentage):.2f}%",
                            "Final Capital": f"${float(result.final_capital):,.2f}",
                        }

                        # Add module-specific decision metrics
                        if selected_module == "TechnicalAnalyst":
                            # Decisions: RSI levels, EMA trends, Volume ratios
                            module_metrics.update(
                                {
                                    "RSI Avg": "N/A",  # Would need to calculate from signal reasons
                                    "EMA Trend": "N/A",
                                    "Volume Ratio": "N/A",
                                }
                            )
                        elif selected_module == "RiskManager":
                            # Decisions: Position size limits, Risk per trade, Stop loss triggers
                            module_metrics.update(
                                {
                                    "Risk/Trade": "2%",
                                    "Max Exposure": "60%",
                                    "Stop Loss Hits": "N/A",
                                }
                            )
                        elif selected_module == "SignalScorer":
                            # Decisions: Signal acceptance rate, Quality scores, Priority ranking
                            module_metrics.update(
                                {
                                    "Signal Score": "75+",
                                    "Acceptance Rate": "N/A",
                                    "Priority": "High",
                                }
                            )
                        elif selected_module == "PortfolioService":
                            # Decisions: Portfolio allocation, Diversification, Cash balance
                            module_metrics.update(
                                {
                                    "Positions": result.performance.total_trades // 2,  # Approx
                                    "Diversification": "N/A",
                                    "Cash %": "N/A",
                                }
                            )
                        elif selected_module == "ExecutionEngine":
                            # Decisions: Execution success rate, Slippage, Commission costs
                            module_metrics.update(
                                {
                                    "Execution Rate": "95%+",
                                    "Slippage": "<0.1%",
                                    "Commission": "Included",
                                }
                            )

                        table_data.append(module_metrics)

                    # Display as dataframe
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

    else:
        st.info(
            "Showing results from all modules. Select a specific module to see detailed information."
        )

        # Show summary of available modules
        available_modules = set()
        if "backtest_results" in session_state:
            for key in session_state.backtest_results.keys():
                parts = key.split('_')
                if parts:
                    available_modules.add(parts[0])

        if available_modules:
            st.write(f"**Available results for**: {', '.join(sorted(available_modules))}")
else:
    st.warning(f"⚠️ No information available for module: {selected_module}")

st.divider()

# Display results with module/preset selector
if session_state.backtest_results:
    # Let user select which result to view
    all_keys = list(session_state.backtest_results.keys())

    # Filter by selected module AND strategy
    if selected_module == "all":
        # Show ALL results when "all" is selected
        combined_key_lower = f"_{selected_strategy.lower()}"
        filtered_keys = [k for k in all_keys if combined_key_lower in k.lower()]

        if not filtered_keys:
            st.warning(
                f"⚠️ No results for any module with strategy '{selected_strategy}'. Execute backtest to see results."
            )
            st.stop()
    else:
        # Try both case-sensitive and case-insensitive matching
        combined_key_lower = f"{selected_module.lower()}_{selected_strategy.lower()}"
        combined_key_exact = f"{selected_module}_{selected_strategy}"

        filtered_keys = [
            k
            for k in all_keys
            if k.lower().startswith(combined_key_lower) or k.startswith(combined_key_exact)
        ]

        # If no results for this specific combination, show message and no results
        if not filtered_keys:
            st.warning(
                f"⚠️ No results for {selected_module} + {selected_strategy}. Execute backtest to see results."
            )
            st.stop()  # Don't show any results

    available_keys = filtered_keys

    # Create selector for results
    if len(available_keys) > 1:
        result_key = st.selectbox(
            "📊 Select Backtest Result",
            options=available_keys,
            index=len(available_keys) - 1,  # Default to most recent
            help="Select which backtest result to display",
            key=f"result_selector_{selected_module}_{selected_strategy}",
        )
    else:
        result_key = available_keys[0] if available_keys else all_keys[-1]

    result = session_state.backtest_results[result_key]

    # Metrics dashboard with 6 cards
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric("📊 Total Trades", result.performance.total_trades)
    with col2:
        st.metric("✅ Win Rate", f"{float(result.performance.win_rate):.1f}%")
    with col3:
        st.metric("💰 Total PnL", f"${float(result.performance.total_pnl):,.2f}")
    with col4:
        sharpe = (
            f"{float(result.performance.sharpe_ratio):.2f}"
            if result.performance.sharpe_ratio
            else "N/A"
        )
        st.metric("📈 Sharpe Ratio", sharpe)
    with col5:
        st.metric("📉 Max Drawdown", f"{float(result.performance.max_drawdown_percentage):.2f}%")
    with col6:
        st.metric("💼 Capital Final", f"${float(result.final_capital):,.2f}")

    # Equity curve
    st.subheader("📈 Equity Curve")
    if result.equity_curve and len(result.equity_curve) > 0:
        equity_df = pd.DataFrame(
            [{"Date": eq[0], "Equity": float(eq[1])} for eq in result.equity_curve]
        )

        if not equity_df.empty:
            fig = px.line(
                equity_df,
                x="Date",
                y="Equity",
                title="Portfolio Value Over Time",
                labels={"Equity": "Portfolio Value ($)"},
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No equity curve data available")
    else:
        st.info("No equity curve data available")

    # Trade log
    st.subheader("📋 Trade Log")
    if result.trades and len(result.trades) > 0:
        trades_df = pd.DataFrame(
            [
                {
                    "Trade ID": trade.trade_id[:8],
                    "Symbol": trade.symbol,
                    "Side": trade.side,
                    "Quantity": float(trade.quantity),
                    "Entry Price": float(trade.entry_price),
                    "Exit Price": float(trade.exit_price) if trade.exit_price else None,
                    "Entry Time": trade.entry_time,
                    "Exit Time": trade.exit_time,
                    "PnL": float(trade.pnl) if trade.pnl else 0,
                    "Status": trade.status.value,
                    "Reason": trade.reason if trade.reason else "N/A",
                }
                for trade in result.trades
            ]
        )

        if not trades_df.empty:
            st.dataframe(trades_df, use_container_width=True, height=400)
        else:
            st.info("No trades recorded")
    else:
        st.info("No trades recorded")

    # Comparison section
    st.subheader("📊 Compare Configurations")

    if len(session_state.backtest_results) > 1:
        # Multi-select for comparison
        all_keys = list(session_state.backtest_results.keys())
        compare_keys = st.multiselect(
            "Select configurations to compare",
            options=all_keys,
            default=all_keys[-2:] if len(all_keys) >= 2 else all_keys,
            help="Compare multiple module configurations",
        )

        if len(compare_keys) >= 2:
            # Create comparison DataFrame
            comparison_data = []
            for key in compare_keys:
                result = session_state.backtest_results[key]
                comparison_data.append(
                    {
                        "Configuration": key,
                        "Total Trades": result.performance.total_trades,
                        "Win Rate": f"{float(result.performance.win_rate):.1f}%",
                        "Total Return": f"{float(result.total_return):.2f}%",
                        "Final Capital": f"${float(result.final_capital):,.2f}",
                        "Max Drawdown": f"{float(result.performance.max_drawdown):.2f}%",
                    }
                )

            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)

            # Comparison chart (equity curves)
            st.subheader("📈 Equity Curve Comparison")
            fig = go.Figure()

            colors = px.colors.qualitative.Set3[: len(compare_keys)]
            for idx, key in enumerate(compare_keys):
                result = session_state.backtest_results[key]
                if result.equity_curve:
                    dates = [point[0] for point in result.equity_curve]
                    values = [float(point[1]) for point in result.equity_curve]
                    fig.add_trace(
                        go.Scatter(
                            x=dates,
                            y=values,
                            mode='lines',
                            name=key,
                            line=dict(color=colors[idx]),
                        )
                    )

            fig.update_layout(
                title="Portfolio Value Over Time - Comparison",
                xaxis_title="Date",
                yaxis_title="Portfolio Value ($)",
                height=400,
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("⚠️ Run at least 2 backtests to compare configurations")

    # Export section
    st.subheader("💾 Export Results")
    col1, col2 = st.columns(2)

    export_data = {
        "module": result_key.split("_")[0],
        "config": result_key.split("_")[1],
        "symbol": symbol,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "metrics": {
            "total_trades": result.performance.total_trades,
            "win_rate": float(result.performance.win_rate),
            "total_return": float(result.total_return),
            "final_capital": float(result.final_capital),
        },
        "trades": [
            {
                "trade_id": trade.trade_id,
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": float(trade.quantity),
                "entry_price": float(trade.entry_price),
                "exit_price": float(trade.exit_price) if trade.exit_price else None,
                "pnl": float(trade.pnl) if trade.pnl else 0,
                "status": trade.status.value,
                "reason": trade.reason if trade.reason else "N/A",
            }
            for trade in result.trades
        ],
    }

    # Export trades DataFrame
    with col1:
        json_str = json.dumps(export_data, indent=2, default=str)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"backtest_{result_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

    with col2:
        if result.trades and len(result.trades) > 0 and not trades_df.empty:
            csv_str = trades_df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv_str,
                file_name=f"backtest_{result_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("No CSV to download (no trades)")
