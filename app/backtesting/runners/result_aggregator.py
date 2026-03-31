"""
Result Aggregator Module

Extracted from comprehensive_backtest_runner.py for SRP compliance.

Provides result aggregation and persistence functionality for backtesting:
- Saving results to CSV and JSON
- Aggregating statistics across multiple backtests
- Weight persistence for learning engines
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ResultAggregator:
    """
    Aggregates and persists backtest results.

    Provides methods for:
    - Saving results to multiple formats (CSV, JSON)
    - Aggregating statistics across multiple runs
    - Calculating summary metrics
    """

    # Default output formats
    DEFAULT_OUTPUT_FORMATS: ClassVar[list] = ["csv", "json"]

    def __init__(
        self,
        output_dir: Path,
        output_formats: Optional[list[str]] = None,
    ):
        """
        Initialize result aggregator.

        Args:
            output_dir: Directory for output files
            output_formats: List of output formats (default: ['csv', 'json'])
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_formats = output_formats or self.DEFAULT_OUTPUT_FORMATS

    def save_results(
        self,
        results: list[dict[str, Any]],
        prefix: str = "backtest_results",
    ) -> dict[str, Path]:
        """
        Guardar resultados a archivos.

        Args:
            results: Lista de resultados
            prefix: Filename prefix

        Returns:
            Dictionary mapping format to file path
        """
        if not results:
            logger.warning("No results to save")
            return {}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = {}

        # Guardar CSV
        if "csv" in self.output_formats:
            csv_path = self.output_dir / f"{prefix}_{timestamp}.csv"
            try:
                df = pd.DataFrame(results)
                df.to_csv(csv_path, index=False)
                logger.info(f"Results saved to CSV: {csv_path}")
                saved_files["csv"] = csv_path
            except Exception as e:
                logger.error(f"Failed to save CSV: {e}")

        # Guardar JSON
        if "json" in self.output_formats:
            json_path = self.output_dir / f"{prefix}_{timestamp}.json"
            try:
                with open(json_path, "w") as f:
                    json.dump(results, f, indent=2, default=str)
                logger.info(f"Results saved to JSON: {json_path}")
                saved_files["json"] = json_path
            except Exception as e:
                logger.error(f"Failed to save JSON: {e}")

        return saved_files

    def aggregate_statistics(
        self,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Calculate aggregated statistics across multiple backtest results.

        Args:
            results: List of backtest result dictionaries

        Returns:
            Dictionary with aggregated statistics
        """
        if not results:
            return {}

        # Extract numeric metrics
        all_metrics = {}
        for result in results:
            metrics = result.get("metrics", result)
            for key, value in metrics.items():
                if isinstance(value, (int, float)) and not key.startswith("_"):
                    if key not in all_metrics:
                        all_metrics[key] = []
                    all_metrics[key].append(value)

        # Calculate statistics
        aggregated = {}
        for metric_name, values in all_metrics.items():
            if values:
                values_array = np.array(values)
                aggregated[metric_name] = {
                    "mean": float(np.mean(values_array)),
                    "std": float(np.std(values_array)),
                    "min": float(np.min(values_array)),
                    "max": float(np.max(values_array)),
                    "median": float(np.median(values_array)),
                    "count": len(values),
                }

        # Add summary counts
        aggregated["_summary"] = {
            "total_backtests": len(results),
            "backtest_types": list({r.get("test_type", "unknown") for r in results}),
        }

        return aggregated

    def extract_best_results(
        self,
        results: list[dict[str, Any]],
        metric: str = "sharpe_ratio",
        top_n: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Extract top N results by a specific metric.

        Args:
            results: List of backtest result dictionaries
            metric: Metric to sort by
            top_n: Number of top results to return

        Returns:
            List of top N results
        """
        if not results:
            return []

        # Sort by metric
        def get_metric(result):
            metrics = result.get("metrics", result)
            value = metrics.get(metric, 0)
            return value if isinstance(value, (int, float)) else 0

        sorted_results = sorted(results, key=get_metric, reverse=True)
        return sorted_results[:top_n]

    def generate_summary_report(
        self,
        results: list[dict[str, Any]],
    ) -> str:
        """
        Generate a human-readable summary report.

        Args:
            results: List of backtest result dictionaries

        Returns:
            Markdown-formatted summary report
        """
        if not results:
            return "# Backtest Results Summary\n\nNo results to report."

        aggregated = self.aggregate_statistics(results)
        best_sharpe = self.extract_best_results(results, "sharpe_ratio", 3)
        best_return = self.extract_best_results(results, "total_return", 3)

        report = []
        report.append("# Backtest Results Summary")
        report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Total Backtests:** {len(results)}")

        # Summary by type
        types = {}
        for r in results:
            t = r.get("test_type", "unknown")
            types[t] = types.get(t, 0) + 1

        report.append("\n## Backtests by Type")
        for t, count in types.items():
            report.append(f"- {t}: {count}")

        # Key metrics
        report.append("\n## Key Metrics (Aggregated)")
        for metric, stats in aggregated.items():
            if metric.startswith("_"):
                continue
            report.append(f"\n### {metric}")
            report.append(f"- Mean: {stats['mean']:.4f}")
            report.append(f"- Std: {stats['std']:.4f}")
            report.append(f"- Min: {stats['min']:.4f}")
            report.append(f"- Max: {stats['max']:.4f}")

        # Top performers by Sharpe
        report.append("\n## Top 3 by Sharpe Ratio")
        for i, r in enumerate(best_sharpe, 1):
            metrics = r.get("metrics", r)
            report.append(
                f"{i}. {r.get('test_name', 'unknown')}: Sharpe={metrics.get('sharpe_ratio', 0):.2f}"
            )

        # Top performers by Return
        report.append("\n## Top 3 by Total Return")
        for i, r in enumerate(best_return, 1):
            metrics = r.get("metrics", r)
            report.append(
                f"{i}. {r.get('test_name', 'unknown')}: Return={metrics.get('total_return', 0):.2%}"
            )

        return "\n".join(report)


# Module-level convenience functions
def save_results(
    results: list[dict[str, Any]],
    output_dir: Path,
    prefix: str = "backtest_results",
) -> dict[str, Path]:
    """Convenience function for saving results."""
    aggregator = ResultAggregator(output_dir)
    return aggregator.save_results(results, prefix)


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Convenience function for aggregating statistics."""
    aggregator = ResultAggregator(Path("."))
    return aggregator.aggregate_statistics(results)
