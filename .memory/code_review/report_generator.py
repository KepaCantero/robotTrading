"""
Report Generator

Generates comprehensive code review reports from agent findings.
Creates structured, actionable reports with prioritized recommendations.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import asdict

from .agents.base_agent import ReviewFinding, Severity, ReviewContext


class ReportGenerator:
    """
    Generates comprehensive code review reports.
    
    This class takes findings from all agents and creates:
    - Structured markdown reports
    - Prioritized recommendations
    - Executive summaries
    - Actionable next steps
    """
    
    def __init__(self):
        self.report_templates = {
            "markdown": self._generate_markdown_report,
            "json": self._generate_json_report,
            "html": self._generate_html_report
        }
    
    async def generate_report(self, 
                            findings: List[ReviewFinding],
                            context: ReviewContext,
                            review_summary: Dict[str, Any],
                            format: str = "markdown") -> Dict[str, Any]:
        """
        Generate comprehensive code review report.
        
        Args:
            findings: List of review findings from all agents
            context: Review context information
            review_summary: Summary of the review process
            format: Output format ("markdown", "json", "html")
            
        Returns:
            Generated report in specified format
        """
        
        # Organize findings by category and severity
        organized_findings = self._organize_findings(findings)
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(findings, review_summary)
        
        # Generate prioritized recommendations
        recommendations = self._generate_recommendations(findings)
        
        # Generate report based on format
        if format in self.report_templates:
            report_content = await self.report_templates[format](
                findings, context, review_summary, organized_findings, 
                executive_summary, recommendations
            )
        else:
            raise ValueError(f"Unsupported report format: {format}")
        
        return {
            "format": format,
            "content": report_content,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "review_type": context.review_type,
                "target_files": context.target_files,
                "total_findings": len(findings),
                "critical_findings": len([f for f in findings if f.severity == Severity.CRITICAL]),
                "high_findings": len([f for f in findings if f.severity == Severity.HIGH]),
                "medium_findings": len([f for f in findings if f.severity == Severity.MEDIUM]),
                "low_findings": len([f for f in findings if f.severity == Severity.LOW])
            }
        }
    
    def _organize_findings(self, findings: List[ReviewFinding]) -> Dict[str, Dict[str, List[ReviewFinding]]]:
        """Organize findings by category and severity."""
        organized = {}
        
        for finding in findings:
            category = finding.category
            severity = finding.severity.value
            
            if category not in organized:
                organized[category] = {}
            
            if severity not in organized[category]:
                organized[category][severity] = []
            
            organized[category][severity].append(finding)
        
        return organized
    
    def _generate_executive_summary(self, findings: List[ReviewFinding], review_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary of the review."""
        
        # Count findings by severity
        severity_counts = {
            "critical": len([f for f in findings if f.severity == Severity.CRITICAL]),
            "high": len([f for f in findings if f.severity == Severity.HIGH]),
            "medium": len([f for f in findings if f.severity == Severity.MEDIUM]),
            "low": len([f for f in findings if f.severity == Severity.LOW])
        }
        
        # Determine overall status
        if severity_counts["critical"] > 0:
            status = "❌ Not mergeable - Critical issues found"
            status_color = "red"
        elif severity_counts["high"] > 3:
            status = "⚠️ Requires fixes before merge - Multiple high priority issues"
            status_color = "orange"
        elif severity_counts["high"] > 0:
            status = "⚠️ Requires fixes before merge - High priority issues found"
            status_color = "orange"
        elif severity_counts["medium"] > 5:
            status = "✅ Code ready for merge - Minor issues to consider"
            status_color = "yellow"
        else:
            status = "✅ Code ready for merge"
            status_color = "green"
        
        # Generate key insights
        key_insights = []
        
        if severity_counts["critical"] > 0:
            key_insights.append(f"🔴 {severity_counts['critical']} critical security/architecture issues")
        
        if severity_counts["high"] > 0:
            key_insights.append(f"🟠 {severity_counts['high']} high priority issues")
        
        # Find most common categories
        category_counts = {}
        for finding in findings:
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1
        
        if category_counts:
            most_common_category = max(category_counts.items(), key=lambda x: x[1])
            key_insights.append(f"📊 Most issues in: {most_common_category[0]} ({most_common_category[1]} issues)")
        
        return {
            "status": status,
            "status_color": status_color,
            "total_findings": len(findings),
            "severity_breakdown": severity_counts,
            "key_insights": key_insights,
            "review_scope": review_summary.get("review_scope", "Unknown"),
            "agents_used": review_summary.get("agents_used", [])
        }
    
    def _generate_recommendations(self, findings: List[ReviewFinding]) -> List[Dict[str, Any]]:
        """Generate prioritized recommendations."""
        
        # Group findings by recommendation similarity
        recommendation_groups = {}
        
        for finding in findings:
            # Create a key based on the first few words of the recommendation
            key = finding.recommendation.split()[:5]
            key = " ".join(key).lower()
            
            if key not in recommendation_groups:
                recommendation_groups[key] = {
                    "recommendation": finding.recommendation,
                    "severity": finding.severity,
                    "count": 0,
                    "categories": set(),
                    "findings": []
                }
            
            recommendation_groups[key]["count"] += 1
            recommendation_groups[key]["categories"].add(finding.category)
            recommendation_groups[key]["findings"].append(finding)
        
        # Convert to list and sort by priority
        recommendations = []
        for group in recommendation_groups.values():
            # Determine priority based on severity and count
            if group["severity"] == Severity.CRITICAL:
                priority = 1
            elif group["severity"] == Severity.HIGH:
                priority = 2
            elif group["severity"] == Severity.MEDIUM:
                priority = 3
            else:
                priority = 4
            
            recommendations.append({
                "priority": priority,
                "severity": group["severity"].value,
                "recommendation": group["recommendation"],
                "affected_categories": list(group["categories"]),
                "finding_count": group["count"],
                "findings": [asdict(f) for f in group["findings"]]
            })
        
        # Sort by priority
        recommendations.sort(key=lambda x: x["priority"])
        
        return recommendations
    
    async def _generate_markdown_report(self, 
                                      findings: List[ReviewFinding],
                                      context: ReviewContext,
                                      review_summary: Dict[str, Any],
                                      organized_findings: Dict[str, Dict[str, List[ReviewFinding]]],
                                      executive_summary: Dict[str, Any],
                                      recommendations: List[Dict[str, Any]]) -> str:
        """Generate markdown report."""
        
        report_lines = []
        
        # Header
        report_lines.append("# Code Review Report")
        report_lines.append("")
        report_lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**Review Type**: {context.review_type}")
        report_lines.append(f"**Target Files**: {', '.join(context.target_files)}")
        report_lines.append("")
        
        # Executive Summary
        report_lines.append("## 📊 Executive Summary")
        report_lines.append("")
        report_lines.append(f"**Status**: {executive_summary['status']}")
        report_lines.append("")
        report_lines.append("### Key Metrics")
        report_lines.append(f"- **Total Findings**: {executive_summary['total_findings']}")
        report_lines.append(f"- **Critical**: {executive_summary['severity_breakdown']['critical']}")
        report_lines.append(f"- **High**: {executive_summary['severity_breakdown']['high']}")
        report_lines.append(f"- **Medium**: {executive_summary['severity_breakdown']['medium']}")
        report_lines.append(f"- **Low**: {executive_summary['severity_breakdown']['low']}")
        report_lines.append("")
        
        # Key Insights
        if executive_summary['key_insights']:
            report_lines.append("### Key Insights")
            for insight in executive_summary['key_insights']:
                report_lines.append(f"- {insight}")
            report_lines.append("")
        
        # Detailed Findings Table
        report_lines.append("## 🔍 Detailed Findings")
        report_lines.append("")
        report_lines.append("| Category | Agent | Summary | Severity | Recommendation |")
        report_lines.append("|----------|-------|---------|----------|----------------|")
        
        for finding in findings:
            # Escape markdown special characters
            category = finding.category.replace("|", "\\|")
            agent = finding.agent.replace("|", "\\|")
            summary = finding.summary.replace("|", "\\|")[:100] + ("..." if len(finding.summary) > 100 else "")
            severity = finding.severity.value
            recommendation = finding.recommendation.replace("|", "\\|")[:100] + ("..." if len(finding.recommendation) > 100 else "")
            
            report_lines.append(f"| {category} | {agent} | {summary} | {severity} | {recommendation} |")
        
        report_lines.append("")
        
        # Recommendations
        report_lines.append("## 💡 Prioritized Recommendations")
        report_lines.append("")
        
        for i, rec in enumerate(recommendations[:10], 1):  # Top 10 recommendations
            report_lines.append(f"### {i}. {rec['severity']} - {rec['affected_categories'][0]}")
            report_lines.append("")
            report_lines.append(f"**Recommendation**: {rec['recommendation']}")
            report_lines.append("")
            report_lines.append(f"**Affected Categories**: {', '.join(rec['affected_categories'])}")
            report_lines.append(f"**Finding Count**: {rec['finding_count']}")
            report_lines.append("")
        
        # Findings by Category
        report_lines.append("## 📋 Findings by Category")
        report_lines.append("")
        
        for category, severities in organized_findings.items():
            report_lines.append(f"### {category}")
            report_lines.append("")
            
            for severity, category_findings in severities.items():
                report_lines.append(f"#### {severity} ({len(category_findings)} issues)")
                report_lines.append("")
                
                for finding in category_findings:
                    report_lines.append(f"- **{finding.agent}**: {finding.summary}")
                    report_lines.append(f"  - *Recommendation*: {finding.recommendation}")
                    if finding.file_path:
                        report_lines.append(f"  - *File*: {finding.file_path}")
                    if finding.line_number:
                        report_lines.append(f"  - *Line*: {finding.line_number}")
                    report_lines.append("")
        
        # Next Steps
        report_lines.append("## 🚀 Next Steps")
        report_lines.append("")
        
        if executive_summary['severity_breakdown']['critical'] > 0:
            report_lines.append("### Immediate Actions Required")
            report_lines.append("1. Address all critical issues before proceeding")
            report_lines.append("2. Review security and architecture findings")
            report_lines.append("3. Re-run code review after fixes")
            report_lines.append("")
        
        if executive_summary['severity_breakdown']['high'] > 0:
            report_lines.append("### High Priority Items")
            report_lines.append("1. Address high priority issues")
            report_lines.append("2. Focus on performance and security items")
            report_lines.append("3. Consider architectural improvements")
            report_lines.append("")
        
        report_lines.append("### General Improvements")
        report_lines.append("1. Address medium and low priority items when time permits")
        report_lines.append("2. Consider implementing suggested best practices")
        report_lines.append("3. Update development guidelines based on findings")
        report_lines.append("")
        
        return "\n".join(report_lines)
    
    async def _generate_json_report(self, 
                                  findings: List[ReviewFinding],
                                  context: ReviewContext,
                                  review_summary: Dict[str, Any],
                                  organized_findings: Dict[str, Dict[str, List[ReviewFinding]]],
                                  executive_summary: Dict[str, Any],
                                  recommendations: List[Dict[str, Any]]) -> str:
        """Generate JSON report."""
        
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "review_type": context.review_type,
                "target_files": context.target_files,
                "branch_name": context.branch_name,
                "commit_hash": context.commit_hash
            },
            "executive_summary": executive_summary,
            "findings": [asdict(finding) for finding in findings],
            "organized_findings": {
                category: {
                    severity: [asdict(f) for f in findings_list]
                    for severity, findings_list in severities.items()
                }
                for category, severities in organized_findings.items()
            },
            "recommendations": recommendations,
            "review_summary": review_summary
        }
        
        return json.dumps(report_data, indent=2)
    
    async def _generate_html_report(self, 
                                  findings: List[ReviewFinding],
                                  context: ReviewContext,
                                  review_summary: Dict[str, Any],
                                  organized_findings: Dict[str, Dict[str, List[ReviewFinding]]],
                                  executive_summary: Dict[str, Any],
                                  recommendations: List[Dict[str, Any]]) -> str:
        """Generate HTML report."""
        
        html_lines = []
        
        # HTML header
        html_lines.append("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Review Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background-color: #f5f5f5; padding: 20px; border-radius: 5px; }
        .critical { color: #d32f2f; }
        .high { color: #f57c00; }
        .medium { color: #fbc02d; }
        .low { color: #388e3c; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .recommendation { background-color: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #2196f3; }
    </style>
</head>
<body>
""")
        
        # Header
        html_lines.append('<div class="header">')
        html_lines.append('<h1>Code Review Report</h1>')
        html_lines.append(f'<p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')
        html_lines.append(f'<p><strong>Review Type:</strong> {context.review_type}</p>')
        html_lines.append(f'<p><strong>Target Files:</strong> {", ".join(context.target_files)}</p>')
        html_lines.append('</div>')
        
        # Executive Summary
        html_lines.append('<h2>📊 Executive Summary</h2>')
        html_lines.append(f'<p><strong>Status:</strong> {executive_summary["status"]}</p>')
        html_lines.append('<h3>Key Metrics</h3>')
        html_lines.append('<ul>')
        html_lines.append(f'<li><strong>Total Findings:</strong> {executive_summary["total_findings"]}</li>')
        html_lines.append(f'<li><strong>Critical:</strong> {executive_summary["severity_breakdown"]["critical"]}</li>')
        html_lines.append(f'<li><strong>High:</strong> {executive_summary["severity_breakdown"]["high"]}</li>')
        html_lines.append(f'<li><strong>Medium:</strong> {executive_summary["severity_breakdown"]["medium"]}</li>')
        html_lines.append(f'<li><strong>Low:</strong> {executive_summary["severity_breakdown"]["low"]}</li>')
        html_lines.append('</ul>')
        
        # Findings Table
        html_lines.append('<h2>🔍 Detailed Findings</h2>')
        html_lines.append('<table>')
        html_lines.append('<tr><th>Category</th><th>Agent</th><th>Summary</th><th>Severity</th><th>Recommendation</th></tr>')
        
        for finding in findings:
            severity_class = finding.severity.value.lower().replace(" ", "-")
            html_lines.append(f'''
            <tr>
                <td>{finding.category}</td>
                <td>{finding.agent}</td>
                <td>{finding.summary}</td>
                <td class="{severity_class}">{finding.severity.value}</td>
                <td>{finding.recommendation}</td>
            </tr>
            ''')
        
        html_lines.append('</table>')
        
        # Recommendations
        html_lines.append('<h2>💡 Prioritized Recommendations</h2>')
        for i, rec in enumerate(recommendations[:10], 1):
            html_lines.append(f'''
            <div class="recommendation">
                <h3>{i}. {rec["severity"]} - {rec["affected_categories"][0]}</h3>
                <p><strong>Recommendation:</strong> {rec["recommendation"]}</p>
                <p><strong>Affected Categories:</strong> {", ".join(rec["affected_categories"])}</p>
                <p><strong>Finding Count:</strong> {rec["finding_count"]}</p>
            </div>
            ''')
        
        # Close HTML
        html_lines.append('</body></html>')
        
        return "\n".join(html_lines)
