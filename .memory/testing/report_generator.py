"""
Test Report Generator

Generates comprehensive test reports from agent results.
Creates structured, actionable reports with test results and recommendations.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import asdict

from .agents.base_test_agent import TestResult, TestStatus, TestContext


class TestReportGenerator:
    """
    Generates comprehensive test reports.
    
    This class takes results from all testing agents and creates:
    - Structured test reports
    - Failure analysis and recommendations
    - Coverage and quality metrics
    - Actionable next steps
    """
    
    def __init__(self):
        self.report_templates = {
            "markdown": self._generate_markdown_report,
            "json": self._generate_json_report,
            "html": self._generate_html_report
        }
    
    async def generate_report(self, 
                            results: List[TestResult],
                            context: TestContext,
                            test_summary: Dict[str, Any],
                            fix_summary: Optional[Dict[str, Any]] = None,
                            format: str = "markdown") -> Dict[str, Any]:
        """
        Generate comprehensive test report.
        
        Args:
            results: List of test results from all agents
            context: Test context information
            test_summary: Summary of the testing process
            fix_summary: Summary of applied fixes (optional)
            format: Output format ("markdown", "json", "html")
            
        Returns:
            Generated report in specified format
        """
        
        # Organize results by phase and agent
        organized_results = self._organize_results(results)
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(results, test_summary, fix_summary)
        
        # Generate test metrics
        test_metrics = self._generate_test_metrics(results, test_summary)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results, test_summary)
        
        # Generate report based on format
        if format in self.report_templates:
            report_content = await self.report_templates[format](
                results, context, test_summary, organized_results, 
                executive_summary, test_metrics, recommendations, fix_summary
            )
        else:
            raise ValueError(f"Unsupported report format: {format}")
        
        return {
            "format": format,
            "content": report_content,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "test_scope": context.test_scope,
                "environment": context.environment,
                "total_results": len(results),
                "passed_tests": len([r for r in results if r.status == TestStatus.PASSED]),
                "failed_tests": len([r for r in results if r.status == TestStatus.FAILED]),
                "error_tests": len([r for r in results if r.status == TestStatus.ERROR]),
                "skipped_tests": len([r for r in results if r.status == TestStatus.SKIPPED])
            }
        }
    
    def _organize_results(self, results: List[TestResult]) -> Dict[str, Dict[str, List[TestResult]]]:
        """Organize results by phase and status."""
        organized = {}
        
        for result in results:
            phase = result.metadata.get("phase", "unknown") if result.metadata else "unknown"
            status = result.status.value
            
            if phase not in organized:
                organized[phase] = {}
            
            if status not in organized[phase]:
                organized[phase][status] = []
            
            organized[phase][status].append(result)
        
        return organized
    
    def _generate_executive_summary(self, results: List[TestResult], 
                                  test_summary: Dict[str, Any], 
                                  fix_summary: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate executive summary of the test results."""
        
        # Count results by status
        status_counts = {
            "passed": len([r for r in results if r.status == TestStatus.PASSED]),
            "failed": len([r for r in results if r.status == TestStatus.FAILED]),
            "errors": len([r for r in results if r.status == TestStatus.ERROR]),
            "skipped": len([r for r in results if r.status == TestStatus.SKIPPED])
        }
        
        total_tests = len(results)
        success_rate = (status_counts["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        # Determine overall status
        if status_counts["failed"] > 0 or status_counts["errors"] > 0:
            if fix_summary and fix_summary.get("fixes_applied", 0) > 0:
                status = "🔄 Fixed and Stable"
                status_color = "green"
            else:
                status = "❌ Unstable Build"
                status_color = "red"
        elif status_counts["skipped"] > total_tests * 0.5:
            status = "⚠️ Partial Coverage"
            status_color = "yellow"
        else:
            status = "✅ Stable Build"
            status_color = "green"
        
        # Generate key insights
        key_insights = []
        
        if status_counts["failed"] > 0:
            key_insights.append(f"🔴 {status_counts['failed']} tests failed")
        
        if status_counts["errors"] > 0:
            key_insights.append(f"🔴 {status_counts['errors']} tests errored")
        
        if fix_summary and fix_summary.get("fixes_applied", 0) > 0:
            key_insights.append(f"🔧 {fix_summary['fixes_applied']} fixes applied")
        
        if success_rate >= 90:
            key_insights.append(f"📊 High success rate: {success_rate:.1f}%")
        
        return {
            "status": status,
            "status_color": status_color,
            "total_tests": total_tests,
            "success_rate": success_rate,
            "status_breakdown": status_counts,
            "key_insights": key_insights,
            "test_strategy": test_summary.get("test_strategy", "unknown"),
            "current_phase": test_summary.get("current_phase", "unknown")
        }
    
    def _generate_test_metrics(self, results: List[TestResult], 
                             test_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test metrics and statistics."""
        
        # Calculate durations
        total_duration = sum(r.duration for r in results)
        avg_duration = total_duration / len(results) if results else 0
        
        # Count by phase
        phase_counts = {}
        for result in results:
            phase = result.metadata.get("phase", "unknown") if result.metadata else "unknown"
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        # Count by agent
        agent_counts = {}
        for result in results:
            agent = result.metadata.get("agent", "unknown") if result.metadata else "unknown"
            agent_counts[agent] = agent_counts.get(agent, 0) + 1
        
        return {
            "total_duration": total_duration,
            "average_duration": avg_duration,
            "phase_breakdown": phase_counts,
            "agent_breakdown": agent_counts,
            "test_coverage": test_summary.get("coverage", "unknown"),
            "environment_ready": test_summary.get("environment_ready", False)
        }
    
    def _generate_recommendations(self, results: List[TestResult], 
                                test_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate recommendations based on test results."""
        
        recommendations = []
        
        # Check for failed tests
        failed_tests = [r for r in results if r.status == TestStatus.FAILED]
        if failed_tests:
            recommendations.append({
                "priority": "high",
                "category": "Test Failures",
                "recommendation": f"Address {len(failed_tests)} failed tests",
                "action": "Review failed test outputs and fix underlying issues"
            })
        
        # Check for error tests
        error_tests = [r for r in results if r.status == TestStatus.ERROR]
        if error_tests:
            recommendations.append({
                "priority": "high",
                "category": "Test Errors",
                "recommendation": f"Fix {len(error_tests)} test errors",
                "action": "Check test environment and configuration"
            })
        
        # Check for coverage
        if test_summary.get("coverage", 0) < 90:
            recommendations.append({
                "priority": "medium",
                "category": "Test Coverage",
                "recommendation": f"Improve test coverage (current: {test_summary.get('coverage', 0)}%)",
                "action": "Add tests for uncovered code paths"
            })
        
        # Check for environment issues
        if not test_summary.get("environment_ready", True):
            recommendations.append({
                "priority": "high",
                "category": "Environment",
                "recommendation": "Fix test environment configuration",
                "action": "Check dependencies, configuration files, and environment setup"
            })
        
        # Check for quality issues
        quality_issues = [r for r in results if "quality" in r.test_name.lower()]
        if quality_issues:
            failed_quality = [r for r in quality_issues if r.status != TestStatus.PASSED]
            if failed_quality:
                recommendations.append({
                    "priority": "medium",
                    "category": "Test Quality",
                    "recommendation": f"Address {len(failed_quality)} test quality issues",
                    "action": "Improve test structure, naming, and organization"
                })
        
        return recommendations
    
    async def _generate_markdown_report(self, 
                                      results: List[TestResult],
                                      context: TestContext,
                                      test_summary: Dict[str, Any],
                                      organized_results: Dict[str, Dict[str, List[TestResult]]],
                                      executive_summary: Dict[str, Any],
                                      test_metrics: Dict[str, Any],
                                      recommendations: List[Dict[str, Any]],
                                      fix_summary: Optional[Dict[str, Any]]) -> str:
        """Generate markdown test report."""
        
        report_lines = []
        
        # Header
        report_lines.append("# Automated Test Report")
        report_lines.append("")
        report_lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**Test Scope**: {context.test_scope}")
        report_lines.append(f"**Environment**: {context.environment}")
        report_lines.append("")
        
        # Executive Summary
        report_lines.append("## 📊 Executive Summary")
        report_lines.append("")
        report_lines.append(f"**Status**: {executive_summary['status']}")
        report_lines.append("")
        report_lines.append("### Key Metrics")
        report_lines.append(f"- **Total Tests**: {executive_summary['total_tests']}")
        report_lines.append(f"- **Success Rate**: {executive_summary['success_rate']:.1f}%")
        report_lines.append(f"- **Passed**: {executive_summary['status_breakdown']['passed']}")
        report_lines.append(f"- **Failed**: {executive_summary['status_breakdown']['failed']}")
        report_lines.append(f"- **Errors**: {executive_summary['status_breakdown']['errors']}")
        report_lines.append(f"- **Skipped**: {executive_summary['status_breakdown']['skipped']}")
        report_lines.append("")
        
        # Key Insights
        if executive_summary['key_insights']:
            report_lines.append("### Key Insights")
            for insight in executive_summary['key_insights']:
                report_lines.append(f"- {insight}")
            report_lines.append("")
        
        # Test Results Table
        report_lines.append("## 🔍 Test Results")
        report_lines.append("")
        report_lines.append("| Phase | Agent | Test Name | Status | Duration | Output |")
        report_lines.append("|-------|-------|-----------|--------|----------|--------|")
        
        for result in results:
            phase = result.metadata.get("phase", "unknown") if result.metadata else "unknown"
            agent = result.metadata.get("agent", "unknown") if result.metadata else "unknown"
            status = result.status.value
            duration = f"{result.duration:.2f}s"
            output = result.output[:100] + "..." if len(result.output) > 100 else result.output
            
            # Escape markdown special characters
            phase = phase.replace("|", "\\|")
            agent = agent.replace("|", "\\|")
            test_name = result.test_name.replace("|", "\\|")
            output = output.replace("|", "\\|")
            
            report_lines.append(f"| {phase} | {agent} | {test_name} | {status} | {duration} | {output} |")
        
        report_lines.append("")
        
        # Test Metrics
        report_lines.append("## 📈 Test Metrics")
        report_lines.append("")
        report_lines.append(f"- **Total Duration**: {test_metrics['total_duration']:.2f}s")
        report_lines.append(f"- **Average Duration**: {test_metrics['average_duration']:.2f}s")
        report_lines.append("")
        
        # Phase Breakdown
        report_lines.append("### Phase Breakdown")
        for phase, count in test_metrics['phase_breakdown'].items():
            report_lines.append(f"- **{phase}**: {count} tests")
        report_lines.append("")
        
        # Agent Breakdown
        report_lines.append("### Agent Breakdown")
        for agent, count in test_metrics['agent_breakdown'].items():
            report_lines.append(f"- **{agent}**: {count} tests")
        report_lines.append("")
        
        # Fixes Applied (if any)
        if fix_summary:
            report_lines.append("## 🔧 Fixes Applied")
            report_lines.append("")
            report_lines.append(f"- **Fixes Applied**: {fix_summary.get('fixes_applied', 0)}")
            report_lines.append(f"- **Fix Branch**: {fix_summary.get('fix_branch', 'N/A')}")
            report_lines.append("")
        
        # Recommendations
        report_lines.append("## 💡 Recommendations")
        report_lines.append("")
        
        for i, rec in enumerate(recommendations, 1):
            priority_emoji = "🔴" if rec["priority"] == "high" else "🟡" if rec["priority"] == "medium" else "🟢"
            report_lines.append(f"### {i}. {priority_emoji} {rec['category']}")
            report_lines.append("")
            report_lines.append(f"**Recommendation**: {rec['recommendation']}")
            report_lines.append("")
            report_lines.append(f"**Action**: {rec['action']}")
            report_lines.append("")
        
        # Next Steps
        report_lines.append("## 🚀 Next Steps")
        report_lines.append("")
        
        if executive_summary['status_breakdown']['failed'] > 0:
            report_lines.append("### Immediate Actions")
            report_lines.append("1. Review failed test outputs")
            report_lines.append("2. Fix underlying issues")
            report_lines.append("3. Re-run tests to verify fixes")
            report_lines.append("")
        
        if executive_summary['status_breakdown']['errors'] > 0:
            report_lines.append("### Environment Issues")
            report_lines.append("1. Check test environment configuration")
            report_lines.append("2. Verify dependencies and setup")
            report_lines.append("3. Ensure all required services are running")
            report_lines.append("")
        
        report_lines.append("### General Improvements")
        report_lines.append("1. Add more test coverage for critical paths")
        report_lines.append("2. Improve test quality and organization")
        report_lines.append("3. Set up continuous integration")
        report_lines.append("")
        
        return "\n".join(report_lines)
    
    async def _generate_json_report(self, 
                                  results: List[TestResult],
                                  context: TestContext,
                                  test_summary: Dict[str, Any],
                                  organized_results: Dict[str, Dict[str, List[TestResult]]],
                                  executive_summary: Dict[str, Any],
                                  test_metrics: Dict[str, Any],
                                  recommendations: List[Dict[str, Any]],
                                  fix_summary: Optional[Dict[str, Any]]) -> str:
        """Generate JSON test report."""
        
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "test_scope": context.test_scope,
                "environment": context.environment,
                "branch_name": context.branch_name,
                "commit_hash": context.commit_hash
            },
            "executive_summary": executive_summary,
            "test_metrics": test_metrics,
            "results": [asdict(result) for result in results],
            "organized_results": {
                phase: {
                    status: [asdict(result) for result in results_list]
                    for status, results_list in status_dict.items()
                }
                for phase, status_dict in organized_results.items()
            },
            "recommendations": recommendations,
            "test_summary": test_summary,
            "fix_summary": fix_summary
        }
        
        return json.dumps(report_data, indent=2)
    
    async def _generate_html_report(self, 
                                  results: List[TestResult],
                                  context: TestContext,
                                  test_summary: Dict[str, Any],
                                  organized_results: Dict[str, Dict[str, List[TestResult]]],
                                  executive_summary: Dict[str, Any],
                                  test_metrics: Dict[str, Any],
                                  recommendations: List[Dict[str, Any]],
                                  fix_summary: Optional[Dict[str, Any]]) -> str:
        """Generate HTML test report."""
        
        html_lines = []
        
        # HTML header
        html_lines.append("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automated Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background-color: #f5f5f5; padding: 20px; border-radius: 5px; }
        .passed { color: #4caf50; }
        .failed { color: #f44336; }
        .error { color: #ff9800; }
        .skipped { color: #9e9e9e; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .recommendation { background-color: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #2196f3; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background-color: #e3f2fd; border-radius: 5px; }
    </style>
</head>
<body>
""")
        
        # Header
        html_lines.append('<div class="header">')
        html_lines.append('<h1>Automated Test Report</h1>')
        html_lines.append(f'<p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>')
        html_lines.append(f'<p><strong>Test Scope:</strong> {context.test_scope}</p>')
        html_lines.append(f'<p><strong>Environment:</strong> {context.environment}</p>')
        html_lines.append('</div>')
        
        # Executive Summary
        html_lines.append('<h2>📊 Executive Summary</h2>')
        html_lines.append(f'<p><strong>Status:</strong> {executive_summary["status"]}</p>')
        
        # Metrics
        html_lines.append('<div class="metric">')
        html_lines.append(f'<strong>Total Tests:</strong> {executive_summary["total_tests"]}')
        html_lines.append('</div>')
        html_lines.append('<div class="metric">')
        html_lines.append(f'<strong>Success Rate:</strong> {executive_summary["success_rate"]:.1f}%')
        html_lines.append('</div>')
        html_lines.append('<div class="metric">')
        html_lines.append(f'<strong>Passed:</strong> {executive_summary["status_breakdown"]["passed"]}')
        html_lines.append('</div>')
        html_lines.append('<div class="metric">')
        html_lines.append(f'<strong>Failed:</strong> {executive_summary["status_breakdown"]["failed"]}')
        html_lines.append('</div>')
        
        # Test Results Table
        html_lines.append('<h2>🔍 Test Results</h2>')
        html_lines.append('<table>')
        html_lines.append('<tr><th>Phase</th><th>Agent</th><th>Test Name</th><th>Status</th><th>Duration</th><th>Output</th></tr>')
        
        for result in results:
            phase = result.metadata.get("phase", "unknown") if result.metadata else "unknown"
            agent = result.metadata.get("agent", "unknown") if result.metadata else "unknown"
            status_class = result.status.value.lower().replace(" ", "-")
            duration = f"{result.duration:.2f}s"
            output = result.output[:100] + "..." if len(result.output) > 100 else result.output
            
            html_lines.append(f'''
            <tr>
                <td>{phase}</td>
                <td>{agent}</td>
                <td>{result.test_name}</td>
                <td class="{status_class}">{result.status.value}</td>
                <td>{duration}</td>
                <td>{output}</td>
            </tr>
            ''')
        
        html_lines.append('</table>')
        
        # Recommendations
        html_lines.append('<h2>💡 Recommendations</h2>')
        for i, rec in enumerate(recommendations, 1):
            priority_emoji = "🔴" if rec["priority"] == "high" else "🟡" if rec["priority"] == "medium" else "🟢"
            html_lines.append(f'''
            <div class="recommendation">
                <h3>{i}. {priority_emoji} {rec["category"]}</h3>
                <p><strong>Recommendation:</strong> {rec["recommendation"]}</p>
                <p><strong>Action:</strong> {rec["action"]}</p>
            </div>
            ''')
        
        # Close HTML
        html_lines.append('</body></html>')
        
        return "\n".join(html_lines)
