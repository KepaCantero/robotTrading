"""
Report Generation Service

Handles generation of HTML reports and export of results to various formats.

Responsibilities:
- Generate HTML comparison reports
- Generate batch summaries
- Export results to JSON, CSV, Excel
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

from app.backtesting.services.models import ProfileResult
from app.domain.models.input_profile import ObjectivoInversion

logger = logging.getLogger(__name__)


class ReportGenerationService:
    """
    Service for generating reports and exporting results.

    Creates HTML reports with visualizations and exports results
    to various formats (JSON, CSV, Excel).
    """

    def __init__(self, output_dir: str):
        """
        Initialize report generation service.

        Args:
            output_dir: Directory for report files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_comparison_report(self, results: Dict[str, ProfileResult]) -> str:
        """
        Generate HTML comparison report.

        Report includes:
        - Side-by-side baseline vs optimized metrics
        - Improvement percentages
        - Statistical significance testing
        - Parameter sensitivity analysis
        - Recommendation: baseline or optimized

        Args:
            results: Dictionary mapping profile_id to ProfileResult

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
        logger.info(f"Comparison report generated: {output_path}")

        return html

    def generate_batch_summary(
        self, results: Dict[str, ProfileResult], fallback_metrics: Dict[str, int]
    ) -> None:
        """
        Generate batch execution summary.

        Args:
            results: Dictionary of profile results
            fallback_metrics: Fallback metrics to include in summary
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
            # Include fallback metrics in summary
            "fallback_metrics": fallback_metrics,
        }

        summary_path = (
            self.output_dir / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"Batch summary saved: {summary_path}")

    def export_results(self, results: Dict[str, ProfileResult], format: str = "json") -> Path:
        """
        Export results to file.

        Args:
            results: Dictionary of profile results
            format: Export format (json, csv, excel)

        Returns:
            Path to exported file

        Raises:
            ValueError: If format is not supported
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            output_path = self.output_dir / f"profile_batch_results_{timestamp}.json"
            # Convert results to dict
            data = {pid: self._result_to_dict(r) for pid, r in results.items()}
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2, default=str)

        elif format == "csv":
            output_path = self.output_dir / f"profile_batch_results_{timestamp}.csv"
            # Flatten results
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

        elif format == "excel":
            output_path = self.output_dir / f"profile_batch_results_{timestamp}.xlsx"
            # Create multiple sheets
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
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Results exported to {output_path}")
        return output_path

    def _result_to_dict(self, result: ProfileResult) -> Dict[str, Any]:
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

    def _group_best_strategies(self, results_list: List[ProfileResult]) -> List[Dict[str, Any]]:
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
                        # Keep best Sharpe
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

    def _get_html_template(self) -> str:
        """Get HTML template for comparison report."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Profile Batch Backtesting Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }
        .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .metric-card h3 { margin: 0 0 10px 0; font-size: 14px; opacity: 0.9; }
        .metric-card .value { font-size: 28px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #34495e; color: white; font-weight: 600; }
        tr:hover { background: #f5f5f5; }
        .improvement-positive { color: #27ae60; font-weight: bold; }
        .improvement-negative { color: #e74c3c; font-weight: bold; }
        .recommendation { padding: 15px; border-radius: 8px; margin: 20px 0; font-weight: bold; }
        .recommendation.approved { background: #d4edda; color: #155724; border: 2px solid #c3e6cb; }
        .recommendation.rejected { background: #f8d7da; color: #721c24; border: 2px solid #f5c6cb; }
        .recommendation.revision { background: #fff3cd; color: #856404; border: 2px solid #ffeaa7; }
        .parameter-bar { height: 20px; background: #ecf0f1; border-radius: 10px; overflow: hidden; }
        .parameter-fill { height: 100%; background: linear-gradient(90deg, #3498db, #2ecc71); transition: width 0.3s; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Profile Batch Backtesting Report</h1>
        <p><strong>Generated:</strong> {{ timestamp }}</p>
        <p><strong>Total Profiles:</strong> {{ total_profiles }}</p>
        <div class="summary">
            <div class="metric-card">
                <h3>Profiles Ready</h3>
                <div class="value">{{ ready_count }}</div>
            </div>
            <div class="metric-card">
                <h3>Avg Sharpe Improvement</h3>
                <div class="value">{{ avg_sharpe_improvement }}%</div>
            </div>
            <div class="metric-card">
                <h3>Avg Return Improvement</h3>
                <div class="value">{{ avg_return_improvement }}%</div>
            </div>
            <div class="metric-card">
                <h3>Optimization Recommended</h3>
                <div class="value">{{ optimization_pct }}%</div>
            </div>
        </div>
        <h2>Baseline vs Optimized Comparison</h2>
        <table>
            <thead>
                <tr>
                    <th>Profile</th>
                    <th>Baseline Sharpe</th>
                    <th>Optimized Sharpe</th>
                    <th>Improvement</th>
                    <th>Baseline Return</th>
                    <th>Optimized Return</th>
                    <th>Improvement</th>
                    <th>Recommendation</th>
                </tr>
            </thead>
            <tbody>
                {% for result in results %}
                <tr>
                    <td>{{ result.profile_id }}</td>
                    <td>{{ "%.2f"|format(result.baseline_results.get('sharpe_ratio', 0)) }}</td>
                    <td>{{ "%.2f"|format(result.optimization_results.get('sharpe_ratio', 0)) }}</td>
                    <td class="{% if result.improvement_metrics.get('sharpe_improvement', 0) > 0 %}improvement-positive{% else %}improvement-negative{% endif %}">
                        {{ "%+.1f"|format(result.improvement_metrics.get('sharpe_improvement', 0)) }}%
                    </td>
                    <td>{{ "%.2f"|format(result.baseline_results.get('return_pct', 0)) }}%</td>
                    <td>{{ "%.2f"|format(result.optimization_results.get('return_pct', 0)) }}%</td>
                    <td class="{% if result.improvement_metrics.get('return_improvement', 0) > 0 %}improvement-positive{% else %}improvement-negative{% endif %}">
                        {{ "%+.1f"|format(result.improvement_metrics.get('return_improvement', 0)) }}%
                    </td>
                    <td>
                        {% if result.ready_for_paper_trading %}
                        <span class="recommendation approved">APPROVED</span>
                        {% else %}
                        <span class="recommendation rejected">REJECTED</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% if parameter_importance %}
        <h2>Parameter Importance Analysis</h2>
        <table>
            <thead>
                <tr>
                    <th>Parameter</th>
                    <th>Importance</th>
                    <th>Visual</th>
                </tr>
            </thead>
            <tbody>
                {% for param, importance in parameter_importance.items() %}
                <tr>
                    <td>{{ param }}</td>
                    <td>{{ "%.3f"|format(importance) }}</td>
                    <td>
                        <div class="parameter-bar">
                            <div class="parameter-fill" style="width: {{ (importance * 100)|int }}%"></div>
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}
        <h2>Best Strategies by Objective</h2>
        {% for objective in best_strategies %}
        <h3>{{ objective.objective|upper }}</h3>
        <table>
            <tr>
                <th>Risk Tolerance</th>
                <th>Capital Tier</th>
                <th>Best Sharpe</th>
                <th>Best Return</th>
                <th>Improvement</th>
            </tr>
            {% for tier_result in objective.results %}
            <tr>
                <td>{{ tier_result.risk_tolerance }}</td>
                <td>{{ tier_result.capital_tier }}</td>
                <td>{{ "%.2f"|format(tier_result.optimized_sharpe or 0) }}</td>
                <td>{{ "%.2f"|format(tier_result.optimized_return or 0) }}%</td>
                <td class="{% if tier_result.sharpe_improvement > 0 %}improvement-positive{% else %}improvement-negative{% endif %}">
                    {{ "%+.1f"|format(tier_result.sharpe_improvement) }}%
                </td>
            </tr>
            {% endfor %}
        </table>
        {% endfor %}
    </div>
</body>
</html>
        """
