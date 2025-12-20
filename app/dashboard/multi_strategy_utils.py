"""
Multi-Strategy Backtesting Utilities.

Provides utilities for saving and generating multi-strategy results.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def save_multi_strategy_results(
    consolidated_results: Dict[str, Any],
    output_dir: Path,
    backtest_id: str,
) -> Path:
    """
    Save multi-strategy results to JSON file.

    Args:
        consolidated_results: Consolidated results from MultiStrategyBacktester
        output_dir: Directory to save results
        backtest_id: Unique backtest identifier

    Returns:
        Path to saved JSON file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract strategy metrics
    strategy_metrics = []
    for strategy_name, result in consolidated_results.get("per_strategy", {}).items():
        metrics = {
            "name": strategy_name,
            "allocation_pct": result.get("initial_capital", 0)
            / consolidated_results["combined"]["total_initial_capital"]
            * 100,
            "trades": result.get("total_trades", 0),
            "pnl": result.get("final_capital", 0) - result.get("initial_capital", 0),
            "sharpe": result.get("sharpe_ratio"),
            "max_drawdown": result.get("max_drawdown", 0),
            "win_rate": result.get("win_rate", 0),
            "total_return": result.get("total_return", 0),
            "initial_capital": result.get("initial_capital", 0),
            "final_capital": result.get("final_capital", 0),
        }

        # Add strategy-specific configuration
        if strategy_name == "pairs_trading":
            metrics["config"] = {
                "max_pair_exposure": 0.2,
                "max_total_exposure": 0.4,
                "conservative_risk": True,
            }
        elif strategy_name == "mean_reversion":
            metrics["config"] = {
                "max_exposure": 0.6,
                "z_score_threshold": 2.0,
                "moderate_risk": True,
            }
        elif strategy_name == "momentum":
            metrics["config"] = {
                "max_exposure": 0.5,
                "aggressive_risk": True,
            }

        strategy_metrics.append(metrics)

    # Combined metrics
    combined = consolidated_results.get("combined", {})

    output_data = {
        "timestamp": datetime.now().isoformat(),
        "backtest_id": backtest_id,
        "strategies": strategy_metrics,
        "combined": {
            "total_pnl": combined.get("total_final_capital", 0)
            - combined.get("total_initial_capital", 0),
            "sharpe": combined.get("weighted_sharpe", 0),
            "max_drawdown": combined.get("weighted_max_dd", 0),
            "total_return": combined.get("total_return", 0),
            "total_trades": combined.get("total_trades", 0),
        },
        "allocation": consolidated_results.get("allocation", {}),
        "stock_allocation": consolidated_results.get(
            "stock_allocation"
        ),  # StrategyStockAllocator results
    }

    # Save to JSON
    output_file = (
        output_dir / f"multi_strategy_{backtest_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2, default=str)

    logger.info(f"Saved multi-strategy results to {output_file}")
    return output_file


def generate_multi_strategy_summary_text(
    consolidated_results: Dict[str, Any],
) -> str:
    """
    Generate text summary for multi-strategy results.

    Args:
        consolidated_results: Consolidated results from MultiStrategyBacktester

    Returns:
        Markdown-formatted summary text
    """
    combined = consolidated_results.get("combined", {})
    per_strategy = consolidated_results.get("per_strategy", {})

    summary = "# Multi-Strategy Backtest Summary\n\n"

    # Combined Results
    summary += "## Combined Results\n\n"
    summary += f"- **Total Initial Capital**: ${combined.get('total_initial_capital', 0):,.2f}\n"
    summary += f"- **Total Final Capital**: ${combined.get('total_final_capital', 0):,.2f}\n"
    summary += f"- **Total Return**: {combined.get('total_return', 0):.2f}%\n"
    summary += f"- **Total Trades**: {combined.get('total_trades', 0)}\n"
    summary += f"- **Weighted Sharpe**: {combined.get('weighted_sharpe', 0):.3f}\n"
    summary += f"- **Weighted Max Drawdown**: {combined.get('weighted_max_dd', 0):.2f}%\n\n"

    # Strategy Performance Table
    summary += "## Strategy Performance\n\n"
    summary += "| Strategy | Capital | Trades | Win Rate | Return | Sharpe | Max DD |\n"
    summary += "|----------|---------|--------|----------|--------|--------|--------|\n"

    for strategy_name, result in per_strategy.items():
        sharpe = result.get('sharpe_ratio', 0) or 0
        max_dd = result.get('max_drawdown', 0) or 0

        summary += f"| {strategy_name} | "
        summary += f"${result.get('initial_capital', 0):,.0f} | "
        summary += f"{result.get('total_trades', 0)} | "
        summary += f"{result.get('win_rate', 0):.1f}% | "
        summary += f"{result.get('total_return', 0):.2f}% | "
        summary += f"{sharpe:.3f} | "
        summary += f"{max_dd:.2f}% |\n"

    summary += "\n"

    # Capital Allocation
    summary += "## Capital Allocation\n\n"
    allocation = consolidated_results.get("allocation", {})
    for strategy_name, allocation_info in allocation.items():
        summary += f"- **{strategy_name}**: {allocation_info.get('weight', 0):.1%} (${allocation_info.get('capital', 0):,.0f})\n"

    summary += "\n"

    # Performance Analysis
    summary += "## Performance Analysis\n\n"

    # Best/Worst performers
    strategy_list = [(name, result) for name, result in per_strategy.items()]
    if strategy_list:
        best = max(strategy_list, key=lambda x: x[1].get('total_return', 0))
        worst = min(strategy_list, key=lambda x: x[1].get('total_return', 0))

        summary += f"- **Best Performer**: {best[0]} ({best[1].get('total_return', 0):.2f}%)\n"
        summary += f"- **Worst Performer**: {worst[0]} ({worst[1].get('total_return', 0):.2f}%)\n"
        summary += f"- **Performance Variance**: {best[1].get('total_return', 0) - worst[1].get('total_return', 0):.2f}%\n"

    # Strategy-Specific Metrics
    summary += "\n## Strategy-Specific Metrics\n\n"

    for strategy_name, result in per_strategy.items():
        if strategy_name == "pairs_trading":
            summary += f"### {strategy_name.upper()} Details\n\n"
            summary += (
                f"- **Allocation**: {allocation.get(strategy_name, {}).get('weight', 0):.1%}\n"
            )
            summary += "- **Risk Profile**: Conservative (max_pair_exposure: 20%, max_total_exposure: 40%)\n"
            summary += f"- **Capital Allocated**: ${result.get('initial_capital', 0):,.0f}\n"
            summary += f"- **Final Capital**: ${result.get('final_capital', 0):,.0f}\n"
            summary += f"- **PnL**: ${result.get('final_capital', 0) - result.get('initial_capital', 0):,.2f}\n"
            summary += f"- **Trades Executed**: {result.get('total_trades', 0)}\n\n"
        elif strategy_name == "mean_reversion":
            summary += f"### {strategy_name.upper()} Details\n\n"
            summary += (
                f"- **Allocation**: {allocation.get(strategy_name, {}).get('weight', 0):.1%}\n"
            )
            summary += "- **Risk Profile**: Moderate (max_exposure: 60%)\n"
            summary += f"- **Capital Allocated**: ${result.get('initial_capital', 0):,.0f}\n"
            summary += f"- **Final Capital**: ${result.get('final_capital', 0):,.0f}\n"
            summary += f"- **PnL**: ${result.get('final_capital', 0) - result.get('initial_capital', 0):,.2f}\n"
            summary += f"- **Trades Executed**: {result.get('total_trades', 0)}\n\n"
        elif strategy_name == "momentum":
            summary += f"### {strategy_name.upper()} Details\n\n"
            summary += (
                f"- **Allocation**: {allocation.get(strategy_name, {}).get('weight', 0):.1%}\n"
            )
            summary += "- **Risk Profile**: Aggressive (max_exposure: 50%)\n"
            summary += f"- **Capital Allocated**: ${result.get('initial_capital', 0):,.0f}\n"
            summary += f"- **Final Capital**: ${result.get('final_capital', 0):,.0f}\n"
            summary += f"- **PnL**: ${result.get('final_capital', 0) - result.get('initial_capital', 0):,.2f}\n"
            summary += f"- **Trades Executed**: {result.get('total_trades', 0)}\n\n"

    summary += "\n---\n\n"
    summary += f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"

    return summary


def generate_backend_test_summary_with_multi_strategy(
    consolidated_results: Dict[str, Any],
    selected_module: str,
    selected_strategy: str,
) -> Dict[str, Any]:
    """
    Generate backend test summary including multi-strategy metrics.

    Args:
        consolidated_results: Consolidated results from MultiStrategyBacktester
        selected_module: Selected system module
        selected_strategy: Selected strategy

    Returns:
        Dictionary with summary data for report generator
    """
    combined = consolidated_results.get("combined", {})
    per_strategy = consolidated_results.get("per_strategy", {})
    allocation = consolidated_results.get("allocation", {})

    # Extract metrics per strategy
    strategy_metrics = []
    for strategy_name, result in per_strategy.items():
        strategy_metrics.append(
            {
                "name": strategy_name,
                "allocation_pct": allocation.get(strategy_name, {}).get("weight", 0) * 100,
                "trades": result.get("total_trades", 0),
                "pnl": result.get("final_capital", 0) - result.get("initial_capital", 0),
                "sharpe": result.get("sharpe_ratio", 0),
                "max_drawdown": result.get("max_drawdown", 0),
                "win_rate": result.get("win_rate", 0),
                "total_return": result.get("total_return", 0),
            }
        )

    summary = {
        "module": selected_module,
        "strategy": selected_strategy,
        "timestamp": datetime.now().isoformat(),
        "strategies": strategy_metrics,
        "combined": {
            "total_pnl": combined.get("total_final_capital", 0)
            - combined.get("total_initial_capital", 0),
            "sharpe": combined.get("weighted_sharpe", 0),
            "max_drawdown": combined.get("weighted_max_dd", 0),
            "total_return": combined.get("total_return", 0),
            "total_trades": combined.get("total_trades", 0),
        },
        "allocation": allocation,
    }

    return summary
