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

# Sidebar for module selection
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Module selector
    modules = {
        "TechnicalAnalyst": "RSI-MACD Technical Analysis",
        "RiskManager": "Portfolio Risk Management", 
        "SignalCombiner": "Multi-Signal Combination",
        "Momentum": "Momentum Strategy",
        "MeanReversion": "Mean Reversion Strategy",
    }
    
    selected_module = st.selectbox(
        "Select Module",
        options=list(modules.keys()),
        help="Choose which trading module to backtest",
    )
    
    st.markdown(f"**Module**: {modules[selected_module]}")
    
    # Configuration presets
    config_presets = {
        "Conservative": {
            "rsi_threshold": 30,
            "momentum_threshold": 0.01,
            "stop_loss": 2.0,
            "take_profit": 5.0,
        },
        "Moderate": {
            "rsi_threshold": 40,
            "momentum_threshold": 0.005,
            "stop_loss": 3.0,
            "take_profit": 7.0,
        },
        "Aggressive": {
            "rsi_threshold": 50,
            "momentum_threshold": 0.001,
            "stop_loss": 5.0,
            "take_profit": 10.0,
        },
    }
    
    selected_preset = st.selectbox(
        "Configuration Preset",
        options=list(config_presets.keys()),
        help="Choose a preset configuration",
    )
    
    # Symbol and date range
    symbol = st.text_input("Symbol", value="AAPL")
    start_date = st.date_input("Start Date", value=datetime(2023, 1, 1))
    end_date = st.date_input("End Date", value=datetime(2024, 12, 31))
    initial_capital = st.number_input(
        "Initial Capital ($)", min_value=1000, value=100000, step=1000
    )
    
    # Execute button
    execute_button = st.button("🚀 Execute Backtest", type="primary", use_container_width=True)

# Main content area
if "backtest_results" not in session_state:
    session_state.backtest_results = {}

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
            
            # Create strategy
            strategy = MomentumStrategy({
                "name": selected_module.lower(),
                **config_presets[selected_preset],
            })
            
            # Generate signals
            signals = []
            for quote in quotes:
                try:
                    signals.extend(strategy.generate_signals(quote))
                except Exception as e:
                    logger.debug(f"Signal error: {e}")
            
            # Create config
            config = BacktestConfig(
                strategy_name=selected_module.lower(),
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
            
            # Store result
            key = f"{selected_module}_{selected_preset}"
            session_state.backtest_results[key] = result
            
            st.success(f"✅ Backtest completed: {result.performance.total_trades} trades")
            
        except Exception as e:
            st.error(f"❌ Error: {e}")
            logger.exception("Backtest failed")

# Display results
if session_state.backtest_results:
    # Get the most recent result
    last_key = list(session_state.backtest_results.keys())[-1]
    result = session_state.backtest_results[last_key]
    
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
        "module": last_key.split("_")[0],
        "config": last_key.split("_")[1],
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
            file_name=f"backtest_{last_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )
    
    with col2:
        csv_str = trades_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_str,
            file_name=f"backtest_{last_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

