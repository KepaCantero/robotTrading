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
from typing import Dict, List, Optional

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
from app.strategies.momentum import MomentumStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.pairs_trading import PairsTradingStrategy
from app.dashboard.report_generator import save_backtest_result, update_summary_index

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
        key="module_selector"
    )
    
    st.markdown(f"**Selected Module**: `{selected_module}`")
    
    st.divider()
    
    # STRATEGY SELECTOR
    st.subheader("🎯 Select Strategy")
    
    strategies = {
        "momentum": "Momentum Strategy (RSI + EMA + Volume)",
        "mean_reversion": "Mean Reversion (Z-score)",
        "pairs_trading": "Pairs Trading (Cointegration)",
    }
    
    selected_strategy = st.selectbox(
        "Select Strategy",
        options=list(strategies.keys()),
        help="Choose which trading strategy to backtest",
        key="strategy_selector",
        format_func=lambda x: strategies[x]
    )
    
    st.markdown(f"**Selected Strategy**: `{strategies[selected_strategy]}`")
    
    # Show available results for this strategy
    if "backtest_results" in session_state and session_state.backtest_results:
        strategy_results = [k for k in session_state.backtest_results.keys() if selected_strategy in k.lower()]
        if strategy_results:
            st.success(f"✓ {len(strategy_results)} backtest(s) for {selected_strategy}")
        else:
            st.warning(f"⚠ No backtests yet for {selected_strategy}")
    
    st.divider()
    st.subheader("⚙️ Configuration Preset")
    
    # Configuration presets
    config_presets = {
        "Conservative": {
            "rsi_threshold": 30,
            "momentum_threshold": 0.01,
            "stop_loss": 2.0,
            "take_profit": 5.0,
            "z_score_threshold": 2.5,  # For mean_reversion
            "min_z_score": 1.5,  # For mean_reversion
            "volatility_threshold": 0.05,  # For mean_reversion
        },
        "Moderate": {
            "rsi_threshold": 40,
            "momentum_threshold": 0.005,
            "stop_loss": 3.0,
            "take_profit": 7.0,
            "z_score_threshold": 1.5,  # For mean_reversion - more permissive
            "min_z_score": 1.0,  # For mean_reversion - more permissive
            "volatility_threshold": 0.10,  # For mean_reversion - more permissive
        },
        "Aggressive": {
            "rsi_threshold": 50,
            "momentum_threshold": 0.001,
            "stop_loss": 5.0,
            "take_profit": 10.0,
            "z_score_threshold": 1.0,  # For mean_reversion - very permissive
            "min_z_score": 0.5,  # For mean_reversion - very permissive
            "volatility_threshold": 0.20,  # For mean_reversion - very permissive
        },
    }
    
    selected_preset = st.selectbox(
        "🎛️ Select Configuration Preset",
        options=list(config_presets.keys()),
        help="Choose a preset configuration",
        key="config_selector"
    )
    
    # Show preset details
    with st.expander(f"View {selected_preset} Preset Parameters"):
        st.json(config_presets[selected_preset])
    
    st.divider()
    
    # Symbol and date range
    symbol = st.text_input("Symbol", value="AAPL")
    start_date = st.date_input("Start Date", value=datetime(2023, 1, 1))
    end_date = st.date_input("End Date", value=datetime(2024, 12, 31))
    initial_capital = st.number_input(
        "Initial Capital ($)", min_value=1000, value=100000, step=1000
    )
    
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
                    key = f"{module_name}_{strategy_key}_{config_name}_{timestamp}" if timestamp else f"{module_name}_{strategy_key}_{config_name}"
                    
                    # Load once per JSON file (not per strategy)
                    if key not in session_state.backtest_results:
                        # Try to create a basic BacktestResult from the metrics
                        try:
                            from app.backtesting.models import BacktestResult, PerformanceMetrics, Trade
                            
                            # Convert metrics JSON to BacktestResult
                            perf_metrics = PerformanceMetrics(
                                total_trades=int(metrics_data.get('total_trades', 0)),
                                win_rate=float(metrics_data.get('win_rate', 0)),
                                total_pnl=float(metrics_data.get('total_pnl', 0)),
                                sharpe_ratio=float(metrics_data.get('sharpe_ratio', 0)) if metrics_data.get('sharpe_ratio') else None,
                                max_drawdown=float(metrics_data.get('max_drawdown', 0)),
                                final_capital=float(metrics_data.get('final_capital', 0)),
                                cagr=float(metrics_data.get('cagr', 0)) if metrics_data.get('cagr') else None,
                                sortino_ratio=float(metrics_data.get('sortino_ratio', 0)) if metrics_data.get('sortino_ratio') else None,
                                profit_factor=float(metrics_data.get('profit_factor', 0)) if metrics_data.get('profit_factor') else None,
                            )
                            
                            # Load trades if available
                            trades = []
                            trade_log_file = module_dir / f"trade_log_{config_name}_{timestamp}.csv" if timestamp else module_dir / f"trade_log_{config_name}.csv"
                            if trade_log_file.exists():
                                df = pd.read_csv(trade_log_file)
                                for _, row in df.iterrows():
                                    trades.append(Trade(
                                        timestamp=datetime.fromisoformat(str(row['timestamp'])),
                                        type=row['type'],
                                        price=float(row['price']),
                                        quantity=float(row['quantity']),
                                        reason=row.get('reason', ''),
                                        pnl=float(row.get('pnl', 0)),
                                        status='CLOSED'
                                    ))
                            
                            result = BacktestResult(
                                symbol=metrics_data.get('symbol', 'UNKNOWN'),
                                start_date=datetime.fromisoformat(metrics_data['start_date']) if 'start_date' in metrics_data else datetime.now(),
                                end_date=datetime.fromisoformat(metrics_data['end_date']) if 'end_date' in metrics_data else datetime.now(),
                                initial_capital=float(metrics_data.get('initial_capital', 100000)),
                                final_capital=float(metrics_data.get('final_capital', 0)),
                                trades=trades,
                                performance=perf_metrics,
                                equity_curve=[],  # Would need to load separately
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
            
            # Run backtests for each module
            for current_module in modules_to_run:
                # Create strategy based on selected strategy
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
                
                # Generate signals (collect all quotes first for strategies that need history)
                signals = []
                for quote in quotes:
                    try:
                        signals.extend(strategy.generate_signals(quote))
                    except Exception as e:
                        logger.debug(f"Signal error: {e}")
                
                if not signals:
                    st.warning(f"⚠️ Strategy '{selected_strategy}' for {current_module} generated 0 signals.")
                    continue
                
                # Create config with module and strategy info
                config = BacktestConfig(
                    strategy_name=f"{current_module}_{selected_strategy}".lower(),
                    initial_capital=Decimal(str(initial_capital)),
                    commission_per_trade=Decimal("1.0"),
                    slippage_percentage=Decimal("0.05"),
                    stop_loss_percentage=Decimal(str(config_presets[selected_preset]["stop_loss"])),
                    take_profit_percentage=Decimal(str(config_presets[selected_preset]["take_profit"])),
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
                    saved_files = save_backtest_result(
                        result_key=key,
                        result={
                            "total_trades": result.performance.total_trades,
                            "win_rate": result.performance.win_rate,
                            "total_return": result.total_return,
                            "final_capital": result.final_capital,
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
            module_results = [k for k in session_state.backtest_results.keys() if k.startswith(selected_module)]
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
        st.info(f"""
**Description**: {info['description']}

**Metrics**: {info['metrics']}

**Good Indicators**: {info['indicators']}
        """)
    else:
        st.info("Showing results from all modules. Select a specific module to see detailed information.")
        
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
    # Try both case-sensitive and case-insensitive matching
    combined_key_lower = f"{selected_module.lower()}_{selected_strategy.lower()}"
    combined_key_exact = f"{selected_module}_{selected_strategy}"
    
    filtered_keys = [
        k for k in all_keys 
        if k.lower().startswith(combined_key_lower) or k.startswith(combined_key_exact)
    ]
    
    # If no results for this specific combination, show message and no results
    if not filtered_keys:
        st.warning(f"⚠️ No results for {selected_module} + {selected_strategy}. Execute backtest to see results.")
        st.stop()  # Don't show any results
    
    available_keys = filtered_keys
    
    # Create selector for results
    if len(available_keys) > 1:
        result_key = st.selectbox(
            "📊 Select Backtest Result",
            options=available_keys,
            index=len(available_keys)-1,  # Default to most recent
            help="Select which backtest result to display",
            key=f"result_selector_{selected_module}_{selected_strategy}"
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
        sharpe = f"{float(result.performance.sharpe_ratio):.2f}" if result.performance.sharpe_ratio else "N/A"
        st.metric("📈 Sharpe Ratio", sharpe)
    with col5:
        st.metric("📉 Max Drawdown", f"{float(result.performance.max_drawdown_percentage):.2f}%")
    with col6:
        st.metric("💼 Capital Final", f"${float(result.final_capital):,.2f}")
    
    # Equity curve
    st.subheader("📈 Equity Curve")
    equity_df = pd.DataFrame(
        [
            {"Date": eq[0], "Equity": float(eq[1])}
            for eq in result.equity_curve
        ]
    )
    
    fig = px.line(
        equity_df,
        x="Date",
        y="Equity",
        title="Portfolio Value Over Time",
        labels={"Equity": "Portfolio Value ($)"},
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Trade log
    st.subheader("📋 Trade Log")
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
    
    st.dataframe(trades_df, use_container_width=True, height=400)
    
    # Comparison section
    st.subheader("📊 Compare Configurations")
    
    if len(session_state.backtest_results) > 1:
        # Multi-select for comparison
        all_keys = list(session_state.backtest_results.keys())
        compare_keys = st.multiselect(
            "Select configurations to compare",
            options=all_keys,
            default=all_keys[-2:] if len(all_keys) >= 2 else all_keys,
            help="Compare multiple module configurations"
        )
        
        if len(compare_keys) >= 2:
            # Create comparison DataFrame
            comparison_data = []
            for key in compare_keys:
                result = session_state.backtest_results[key]
                comparison_data.append({
                    "Configuration": key,
                    "Total Trades": result.performance.total_trades,
                    "Win Rate": f"{float(result.performance.win_rate):.1f}%",
                    "Total Return": f"{float(result.total_return):.2f}%",
                    "Final Capital": f"${float(result.final_capital):,.2f}",
                    "Max Drawdown": f"{float(result.performance.max_drawdown):.2f}%",
                })
            
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            
            # Comparison chart (equity curves)
            st.subheader("📈 Equity Curve Comparison")
            fig = go.Figure()
            
            colors = px.colors.qualitative.Set3[:len(compare_keys)]
            for idx, key in enumerate(compare_keys):
                result = session_state.backtest_results[key]
                if result.equity_curve:
                    dates = [point[0] for point in result.equity_curve]
                    values = [float(point[1]) for point in result.equity_curve]
                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=values,
                        mode='lines',
                        name=key,
                        line=dict(color=colors[idx]),
                    ))
            
            fig.update_layout(
                title="Portfolio Value Over Time - Comparison",
                xaxis_title="Date",
                yaxis_title="Portfolio Value ($)",
                height=400,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                ),
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
        csv_str = trades_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_str,
            file_name=f"backtest_{result_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

