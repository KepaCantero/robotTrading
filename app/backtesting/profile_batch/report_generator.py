"""
Report Generator Module

Generates HTML reports for batch backtesting results.
Handles report creation and data export.

Responsibilities:
- Generate HTML comparison reports
- Export results to JSON, CSV, Excel
- Create batch summaries
- Format and visualize results
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from jinja2 import Template

from app.core.models.input_profile import ObjectivoInversion

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates reports for batch backtesting results.

    Creates HTML reports with visualizations and exports
    results to various formats (JSON, CSV, Excel).
    """

    def __init__(self, output_dir: Path):
        """
        Initialize report generator.

        Args:
            output_dir: Directory for report files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_comparison_report(self, results: Dict[str, Any]) -> str:
        """
        Generate HTML comparison report.

        Args:
            results: Dictionary of profile_id to ProfileResult

        Returns:
            HTML report as string
        """
        template_str = self._get_html_template()

        # Prepare template data
        results_list = list(results.values())

        # Calculate summary stats
        ready_count = sum(1 for r in results_list if r.ready_for_paper_trading)
        avg_sharpe_imp = np.mean(
            [r.improvement_metrics.get("sharpe_improvement", 0) for r in results_list]
        )
        avg_return_imp = np.mean(
            [r.improvement_metrics.get("return_improvement", 0) for r in results_list]
        )
        optimization_rec_pct = (
            sum(1 for r in results_list if "optimized" in r.recommendation.lower())
            / len(results_list)
            * 100
            if results_list
            else 0
        )

        # Aggregate parameter importance
        param_importance = {}
        for result in results_list:
            for param, imp in result.comparison.parameter_importance.items():
                if param not in param_importance:
                    param_importance[param] = []
                param_importance[param].append(imp)

        param_importance_avg = {
            k: np.mean(v) for k, v in sorted(param_importance.items(), key=lambda x: -np.mean(x[1]))
        }

        # Group best strategies by objective
        best_by_objective = self._group_best_strategies(results_list)

        # Render template
        template = Template(template_str)
        html = template.render(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_profiles=len(results_list),
            ready_count=ready_count,
            avg_sharpe_improvement=f"{avg_sharpe_imp:.1f}",
            avg_return_improvement=f"{avg_return_imp:.1f}",
            optimization_pct=f"{optimization_rec_pct:.0f}",
            results=results_list,
            parameter_importance=param_importance_avg,
            best_strategies=best_by_objective,
        )

        # Save to file
        output_path = (
            self.output_dir / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        with open(output_path, "w") as f:
            f.write(html)

        logger.info(
            "Comparison report generated",
            extra={
                "operation": "generate_comparison_report",
                "output_path": str(output_path),
                "total_profiles": len(results_list),
                "ready_count": ready_count,
                "avg_sharpe_improvement": float(avg_sharpe_imp),
                "avg_return_improvement": float(avg_return_imp),
                "optimization_recommendation_pct": float(optimization_rec_pct),
            },
        )

        return html

    def _group_best_strategies(self, results_list: List[Any]) -> List[Dict[str, Any]]:
        """Group best strategies by objective."""
        best_by_objective = []

        for objective in ObjectivoInversion:
            obj_results = [r for r in results_list if r.profile.objetivo_inversion == objective]

            if obj_results:
                # Group by risk and tier
                grouped = {}
                for r in obj_results:
                    key = (r.profile.risk_tolerance.value, r.profile.capital_flag)
                    if key not in grouped:
                        grouped[key] = r
                    else:
                        if r.optimization_results.get("sharpe_ratio", 0) > grouped[
                            key
                        ].optimization_results.get("sharpe_ratio", 0):
                            grouped[key] = r

                best_by_objective.append(
                    {
                        "objective": objective.value,
                        "results": [
                            {
                                "risk_tolerance": k[0],
                                "capital_tier": k[1],
                                "optimized_sharpe": v.optimization_results.get("sharpe_ratio"),
                                "optimized_return": v.optimization_results.get("return_pct"),
                                "sharpe_improvement": v.improvement_metrics.get(
                                    "sharpe_improvement"
                                ),
                            }
                            for k, v in grouped.items()
                        ],
                    }
                )

        return best_by_objective

    def generate_batch_summary(
        self, results: Dict[str, Any], fallback_metrics: Dict[str, int]
    ) -> None:
        """
        Generate batch execution summary.

        Args:
            results: Dictionary of profile_id to ProfileResult
            fallback_metrics: Fallback metrics dictionary
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_profiles": len(results),
            "ready_for_paper_trading": sum(
                1 for r in results.values() if r.ready_for_paper_trading
            ),
            "rejected": sum(1 for r in results.values() if not r.ready_for_paper_trading),
            "average_improvements": {
                "sharpe": np.mean(
                    [r.improvement_metrics.get("sharpe_improvement", 0) for r in results.values()]
                ),
                "return": np.mean(
                    [r.improvement_metrics.get("return_improvement", 0) for r in results.values()]
                ),
            },
            "best_overall": max(
                results.items(),
                key=lambda x: x[1].optimization_results.get("sharpe_ratio", 0),
                default=(None, None),
            ),
            "fallback_metrics": fallback_metrics,
        }

        summary_path = (
            self.output_dir / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(
            "Batch summary saved",
            extra={
                "operation": "generate_batch_summary",
                "output_path": str(summary_path),
                "total_profiles": len(results),
                "ready_for_paper_trading": summary["ready_for_paper_trading"],
                "rejected": summary["rejected"],
                "avg_sharpe_improvement": summary["average_improvements"]["sharpe"],
                "avg_return_improvement": summary["average_improvements"]["return"],
            },
        )

    def export_results(self, results: Dict[str, Any], format: str = "json") -> Path:
        """
        Export results to file.

        Args:
            results: Dictionary of profile_id to ProfileResult
            format: Export format (json, csv, excel)

        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            return self._export_json(results, timestamp)
        elif format == "csv":
            return self._export_csv(results, timestamp)
        elif format == "excel":
            return self._export_excel(results, timestamp)
        else:
            logger.error(
                "Unsupported export format requested",
                extra={
                    "operation": "export_results",
                    "requested_format": format,
                    "supported_formats": ["json", "csv", "excel"],
                },
            )
            raise ValueError(f"Unsupported format: {format}")

    def _export_json(self, results: Dict[str, Any], timestamp: str) -> Path:
        """Export results to JSON."""
        output_path = self.output_dir / f"profile_batch_results_{timestamp}.json"

        data = {pid: self._result_to_dict(r) for pid, r in results.items()}

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(
            "Results exported to JSON",
            extra={
                "operation": "export_json",
                "output_path": str(output_path),
                "format": "json",
                "results_count": len(results),
            },
        )
        return output_path

    def _export_csv(self, results: Dict[str, Any], timestamp: str) -> Path:
        """Export results to CSV."""
        output_path = self.output_dir / f"profile_batch_results_{timestamp}.csv"

        rows = []
        for pid, result in results.items():
            row = {
                "profile_id": pid,
                "objective": result.profile.objetivo_inversion.value,
                "risk_tolerance": result.profile.risk_tolerance.value,
                "capital_tier": result.profile.capital_flag,
                "investment_horizon": result.profile.investment_horizon,
                **result.baseline_results,
                **{f"opt_{k}": v for k, v in result.optimization_results.items()},
                **{f"imp_{k}": v for k, v in result.improvement_metrics.items()},
                "ready_for_paper_trading": result.ready_for_paper_trading,
                "recommendation": result.recommendation,
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)

        logger.info(
            "Results exported to CSV",
            extra={
                "operation": "export_csv",
                "output_path": str(output_path),
                "format": "csv",
                "results_count": len(results),
                "rows_exported": len(rows),
            },
        )
        return output_path

    def _export_excel(self, results: Dict[str, Any], timestamp: str) -> Path:
        """Export results to Excel."""
        output_path = self.output_dir / f"profile_batch_results_{timestamp}.xlsx"

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Summary sheet
            rows = []
            for pid, result in results.items():
                row = {
                    "profile_id": pid,
                    "objective": result.profile.objetivo_inversion.value,
                    "risk_tolerance": result.profile.risk_tolerance.value,
                    "capital_tier": result.profile.capital_flag,
                    "baseline_sharpe": result.baseline_results.get("sharpe_ratio"),
                    "optimized_sharpe": result.optimization_results.get("sharpe_ratio"),
                    "sharpe_improvement": result.improvement_metrics.get("sharpe_improvement"),
                    "ready": result.ready_for_paper_trading,
                    "recommendation": result.recommendation,
                }
                rows.append(row)

            pd.DataFrame(rows).to_excel(writer, sheet_name="Summary", index=False)

            # Detailed sheets by objective
            for objective in ObjectivoInversion:
                obj_results = [
                    r for r in results.values() if r.profile.objetivo_inversion == objective
                ]
                if obj_results:
                    obj_rows = [self._result_to_dict(r) for r in obj_results]
                    pd.DataFrame(obj_rows).to_excel(
                        writer, sheet_name=objective.value[:31], index=False
                    )

        logger.info(
            "Results exported to Excel",
            extra={
                "operation": "export_excel",
                "output_path": str(output_path),
                "format": "excel",
                "results_count": len(results),
                "sheets_created": 1
                + len(
                    [
                        o
                        for o in ObjectivoInversion
                        if any(r.profile.objetivo_inversion == o for r in results.values())
                    ]
                ),
            },
        )
        return output_path

    def _result_to_dict(self, result: Any) -> Dict[str, Any]:
        """Convert ProfileResult to dictionary."""
        return {
            "profile_id": result.profile_id,
            "objective": result.profile.objetivo_inversion.value,
            "risk_tolerance": result.profile.risk_tolerance.value,
            "capital_tier": result.profile.capital_flag,
            "investment_horizon": result.profile.investment_horizon,
            "baseline_results": result.baseline_results,
            "optimization_results": result.optimization_results,
            "best_parameters": result.best_parameters,
            "improvement_metrics": result.improvement_metrics,
            "ready_for_paper_trading": result.ready_for_paper_trading,
            "recommendation": result.recommendation,
            "created_at": result.created_at.isoformat(),
        }

    def _get_html_template(self) -> str:
        """
        Get HTML template for reports.

        Reads the template from an external file to follow CC-007 (Small functions).
        The template file is located in the templates subdirectory.

        Returns:
            HTML template string for rendering comparison reports.

        Raises:
            FileNotFoundError: If the template file does not exist.
            IOError: If the template file cannot be read.
        """
        template_path = Path(__file__).parent / "templates" / "comparison_report.html"
        return template_path.read_text()
