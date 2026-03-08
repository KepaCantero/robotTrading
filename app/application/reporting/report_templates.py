"""
Report Templates Module

Re-exports from app.services.reporting for backward compatibility.
"""

from app.services.reporting.report_templates import ReportTemplates, get_report_templates

__all__ = ["ReportTemplates", "get_report_templates"]
