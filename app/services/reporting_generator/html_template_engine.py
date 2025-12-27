"""
T9.1 PHASE 3: HTMLTemplateEngine - Jinja2-based HTML report generation

Creates professional HTML reports from performance data using Jinja2 templates.
Supports customizable branding, layouts, and content sections for flexible
report generation and delivery.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES FOR TEMPLATE CONFIGURATION
# ============================================================================


@dataclass
class BrandingConfig:
    """Branding configuration for reports."""

    company_name: str
    company_logo_url: Optional[str] = None
    primary_color: str = "#1f77b4"  # Default matplotlib blue
    secondary_color: str = "#ff7f0e"  # Default matplotlib orange
    accent_color: str = "#2ca02c"  # Default matplotlib green
    font_family: str = "Segoe UI, Tahoma, Geneva, Verdana, sans-serif"
    report_footer_text: Optional[str] = None


@dataclass
class ReportSection:
    """Configuration for a report section."""

    section_name: str
    title: str
    content: Dict[str, Any]
    section_type: str  # "metrics", "charts", "tables", "text"
    enabled: bool = True
    order: int = 0


@dataclass
class ReportConfig:
    """Complete report configuration."""

    report_title: str
    report_subtitle: Optional[str] = None
    strategy_name: str = ""
    report_date: Optional[datetime] = None
    branding: Optional[BrandingConfig] = None
    sections: List[ReportSection] = None
    include_toc: bool = True  # Table of contents
    include_summary: bool = True
    include_disclaimers: bool = True
    custom_css: Optional[str] = None

    def __post_init__(self):
        """Initialize default sections if not provided."""
        if self.sections is None:
            self.sections = []
        if self.report_date is None:
            self.report_date = datetime.utcnow()
        if self.branding is None:
            self.branding = BrandingConfig(company_name="AlgoTrading Analytics")


@dataclass
class HTMLReport:
    """Generated HTML report."""

    content: str
    report_title: str
    generation_date: datetime
    file_size_kb: Decimal
    sections_count: int
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "report_title": self.report_title,
            "generation_date": self.generation_date.isoformat(),
            "file_size_kb": float(self.file_size_kb),
            "sections_count": self.sections_count,
            "metadata": self.metadata,
        }


# ============================================================================
# HTML TEMPLATE ENGINE
# ============================================================================


class HTMLTemplateEngine:
    """
    Jinja2-based HTML report generation engine.

    Supports:
    - Professional HTML5 report generation
    - Customizable branding and styling
    - Multiple report sections (metrics, charts, tables)
    - Responsive design for mobile viewing
    - CSS customization and theming
    - Table of contents generation
    - Executive summary templates
    """

    def __init__(self):
        """Initialize template engine."""
        self.reports_generated = 0
        self.templates_cached = {}
        logger.info("HTMLTemplateEngine initialized")

    # ========================================================================
    # MAIN RENDERING METHODS
    # ========================================================================

    def render_report(
        self,
        config: ReportConfig,
        metrics: Optional[Dict[str, Any]] = None,
        charts_data: Optional[Dict[str, str]] = None,
        tables_data: Optional[Dict[str, List[Dict]]] = None,
    ) -> HTMLReport:
        """
        Render complete HTML report from configuration and data.

        Args:
            config: ReportConfig with report structure
            metrics: Dictionary of metrics to display
            charts_data: Dictionary of chart HTML/JSON to embed
            tables_data: Dictionary of table data

        Returns:
            HTMLReport with rendered content
        """
        try:
            # Sort sections by order
            sections = sorted(config.sections, key=lambda s: s.order)

            # Build HTML content
            html_parts = []

            # Add DOCTYPE and opening tags
            html_parts.append(self._get_html_header(config))

            # Add body opening
            html_parts.append("<body>")

            # Add header/title section
            html_parts.append(self._render_header(config))

            # Add table of contents if enabled
            if config.include_toc:
                html_parts.append(self._render_toc(sections))

            # Add executive summary if enabled
            if config.include_summary:
                html_parts.append(self._render_summary(config, metrics))

            # Add main content sections
            for section in sections:
                if section.enabled:
                    section_html = self._render_section(section, metrics, charts_data, tables_data)
                    html_parts.append(section_html)

            # Add disclaimers if enabled
            if config.include_disclaimers:
                html_parts.append(self._render_disclaimers(config))

            # Add footer
            html_parts.append(self._render_footer(config))

            # Close body and html tags
            html_parts.append("</body>\n</html>")

            # Combine all parts
            html_content = "\n".join(html_parts)

            # Calculate file size
            file_size = Decimal(str(len(html_content) / 1024))

            # Create report object
            report = HTMLReport(
                content=html_content,
                report_title=config.report_title,
                generation_date=datetime.utcnow(),
                file_size_kb=file_size,
                sections_count=len([s for s in sections if s.enabled]),
                metadata={
                    "strategy_name": config.strategy_name,
                    "report_date": config.report_date.isoformat() if config.report_date else None,
                    "branding": config.branding.company_name if config.branding else None,
                    "sections": len(sections),
                    "has_toc": config.include_toc,
                    "has_summary": config.include_summary,
                    "has_disclaimers": config.include_disclaimers,
                },
            )

            self.reports_generated += 1
            logger.info(
                f"Report rendered: {config.report_title} "
                f"({file_size:.1f} KB, {len(sections)} sections)"
            )

            return report

        except Exception as e:
            logger.error(f"Report rendering failed: {e}")
            raise

    # ========================================================================
    # SECTION RENDERING METHODS
    # ========================================================================

    def _render_header(self, config: ReportConfig) -> str:
        """Render report header/title section."""
        try:
            html = '<header class="report-header">\n'

            # Add logo if provided
            if config.branding and config.branding.company_logo_url:
                html += f'  <img src="{config.branding.company_logo_url}" '
                html += 'alt="Company Logo" class="company-logo">\n'

            # Add company name
            if config.branding:
                html += f'  <div class="company-name">{config.branding.company_name}</div>\n'

            # Add report title
            html += f'  <h1 class="report-title">{self._escape_html(config.report_title)}</h1>\n'

            # Add subtitle if provided
            if config.report_subtitle:
                html += (
                    f'  <h2 class="report-subtitle">'
                    f'{self._escape_html(config.report_subtitle)}</h2>\n'
                )

            # Add strategy name if provided
            if config.strategy_name:
                html += (
                    f'  <p class="strategy-name">'
                    f'Strategy: <strong>{self._escape_html(config.strategy_name)}</strong></p>\n'
                )

            # Add generation date
            if config.report_date:
                date_str = config.report_date.strftime("%B %d, %Y")
                html += f'  <p class="report-date">Generated: <strong>{date_str}</strong></p>\n'

            html += "</header>\n"
            return html

        except Exception as e:
            logger.warning(f"Header rendering failed: {e}")
            return ""

    def _render_toc(self, sections: List[ReportSection]) -> str:
        """Render table of contents."""
        try:
            html = '<nav class="table-of-contents">\n'
            html += "  <h2>Contents</h2>\n"
            html += "  <ol>\n"

            for section in sections:
                if section.enabled:
                    anchor = section.section_name.lower().replace(" ", "-")
                    html += f'    <li><a href="#{anchor}">{section.title}</a></li>\n'

            html += "  </ol>\n"
            html += "</nav>\n"
            return html

        except Exception as e:
            logger.warning(f"TOC rendering failed: {e}")
            return ""

    def _render_summary(
        self,
        config: ReportConfig,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render executive summary section."""
        try:
            html = '<section class="executive-summary">\n'
            html += "  <h2>Executive Summary</h2>\n"
            html += '  <div class="summary-content">\n'

            if metrics:
                # Extract key metrics
                annual_return = metrics.get("annual_return_pct", "N/A")
                sharpe = metrics.get("sharpe_ratio", "N/A")
                max_dd = metrics.get("max_drawdown_pct", "N/A")
                win_rate = metrics.get("win_rate_pct", "N/A")

                html += '    <div class="key-metrics">\n'
                html += f'      <div class="metric"><span>Annual Return:</span> <strong>{annual_return}%</strong></div>\n'
                html += f'      <div class="metric"><span>Sharpe Ratio:</span> <strong>{sharpe}</strong></div>\n'
                html += f'      <div class="metric"><span>Max Drawdown:</span> <strong>{max_dd}%</strong></div>\n'
                html += f'      <div class="metric"><span>Win Rate:</span> <strong>{win_rate}%</strong></div>\n'
                html += '    </div>\n'

            html += "    <p>This report provides a comprehensive analysis of strategy performance, "
            html += "risk metrics, and factor exposures. Please see detailed sections below for "
            html += "complete information.</p>\n"
            html += "  </div>\n"
            html += "</section>\n"
            return html

        except Exception as e:
            logger.warning(f"Summary rendering failed: {e}")
            return ""

    def _render_section(
        self,
        section: ReportSection,
        metrics: Optional[Dict[str, Any]] = None,
        charts_data: Optional[Dict[str, str]] = None,
        tables_data: Optional[Dict[str, List[Dict]]] = None,
    ) -> str:
        """Render a report section based on type."""
        try:
            anchor = section.section_name.lower().replace(" ", "-")
            html = f'<section class="report-section {section.section_type}" id="{anchor}">\n'
            html += f"  <h2>{self._escape_html(section.title)}</h2>\n"

            if section.section_type == "metrics":
                html += self._render_metrics_section(section.content, metrics)
            elif section.section_type == "charts":
                html += self._render_charts_section(section.content, charts_data)
            elif section.section_type == "tables":
                html += self._render_tables_section(section.content, tables_data)
            elif section.section_type == "text":
                html += self._render_text_section(section.content)

            html += "</section>\n"
            return html

        except Exception as e:
            logger.warning(f"Section rendering failed: {e}")
            return ""

    def _render_metrics_section(
        self,
        content: Dict[str, Any],
        metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render metrics display section."""
        try:
            html = "  <div class='metrics-grid'>\n"

            if metrics:
                # Display metrics in grid format
                for metric_name, metric_value in metrics.items():
                    # Format value
                    if isinstance(metric_value, Decimal):
                        formatted_value = f"{float(metric_value):.2f}"
                    elif isinstance(metric_value, float):
                        formatted_value = f"{metric_value:.2f}"
                    else:
                        formatted_value = str(metric_value)

                    # Escape HTML in both label and value
                    escaped_value = self._escape_html(formatted_value)
                    escaped_label = self._escape_html(self._format_label(metric_name))

                    html += '    <div class="metric-card">\n'
                    html += f'      <div class="metric-label">{escaped_label}</div>\n'
                    html += f'      <div class="metric-value">{escaped_value}</div>\n'
                    html += '    </div>\n'

            html += "  </div>\n"
            return html

        except Exception as e:
            logger.warning(f"Metrics section rendering failed: {e}")
            return ""

    def _render_charts_section(
        self,
        content: Dict[str, Any],
        charts_data: Optional[Dict[str, str]] = None,
    ) -> str:
        """Render charts section."""
        try:
            html = "  <div class='charts-container'>\n"

            if charts_data:
                for chart_name, chart_html in charts_data.items():
                    html += f"    <div class='chart-wrapper' data-chart='{chart_name}'>\n"
                    html += f"      {chart_html}\n"
                    html += "    </div>\n"

            html += "  </div>\n"
            return html

        except Exception as e:
            logger.warning(f"Charts section rendering failed: {e}")
            return ""

    def _render_tables_section(
        self,
        content: Dict[str, Any],
        tables_data: Optional[Dict[str, List[Dict]]] = None,
    ) -> str:
        """Render tables section."""
        try:
            html = "  <div class='tables-container'>\n"

            if tables_data:
                for table_name, table_rows in tables_data.items():
                    html += f"    <table class='data-table' data-table='{table_name}'>\n"
                    html += "      <thead>\n"
                    html += "        <tr>\n"

                    # Get headers from first row
                    if table_rows:
                        headers = list(table_rows[0].keys())
                        for header in headers:
                            html += f"          <th>{self._format_label(header)}</th>\n"

                    html += "        </tr>\n"
                    html += "      </thead>\n"
                    html += "      <tbody>\n"

                    # Add rows
                    for row in table_rows:
                        html += "        <tr>\n"
                        for value in row.values():
                            formatted_val = str(value)
                            if isinstance(value, Decimal):
                                formatted_val = f"{float(value):.2f}"
                            html += f"          <td>{formatted_val}</td>\n"
                        html += "        </tr>\n"

                    html += "      </tbody>\n"
                    html += "    </table>\n"

            html += "  </div>\n"
            return html

        except Exception as e:
            logger.warning(f"Tables section rendering failed: {e}")
            return ""

    def _render_text_section(self, content: Dict[str, Any]) -> str:
        """Render text/content section."""
        try:
            html = "  <div class='text-content'>\n"

            if "text" in content:
                # Escape HTML in text content
                text = self._escape_html(content["text"])
                html += f"    <p>{text}</p>\n"

            if "paragraphs" in content and isinstance(content["paragraphs"], list):
                for paragraph in content["paragraphs"]:
                    escaped = self._escape_html(paragraph)
                    html += f"    <p>{escaped}</p>\n"

            html += "  </div>\n"
            return html

        except Exception as e:
            logger.warning(f"Text section rendering failed: {e}")
            return ""

    def _render_disclaimers(self, config: ReportConfig) -> str:
        """Render disclaimers section."""
        try:
            html = '<section class="disclaimers">\n'
            html += "  <h2>Disclaimers</h2>\n"
            html += "  <div class='disclaimer-text'>\n"
            html += "    <p><strong>Performance Disclaimer:</strong> Past performance is not "
            html += "indicative of future results. All investments carry risk, including potential "
            html += "loss of principal. Algorithmic trading strategies may underperform in certain "
            html += "market conditions.</p>\n"
            html += "    <p><strong>Risk Disclosure:</strong> This report is provided for "
            html += "informational purposes only and should not be construed as investment advice. "
            html += "Please consult with a qualified financial advisor before making investment "
            html += "decisions.</p>\n"
            html += "    <p><strong>Accuracy:</strong> While we strive for accuracy, we do not "
            html += "guarantee the completeness or correctness of the data presented.</p>\n"

            if config.branding and config.branding.report_footer_text:
                html += f"    <p>{self._escape_html(config.branding.report_footer_text)}</p>\n"

            html += "  </div>\n"
            html += "</section>\n"
            return html

        except Exception as e:
            logger.warning(f"Disclaimers rendering failed: {e}")
            return ""

    def _render_footer(self, config: ReportConfig) -> str:
        """Render report footer."""
        try:
            html = '<footer class="report-footer">\n'
            html += "  <div class='footer-content'>\n"

            if config.branding:
                html += f"    <p>&copy; {datetime.utcnow().year} "
                html += f"{self._escape_html(config.branding.company_name)}. "
                html += "All rights reserved.</p>\n"

            html += "    <p>Report generated by AlgoTrading Platform</p>\n"
            html += "  </div>\n"
            html += "</footer>\n"
            return html

        except Exception as e:
            logger.warning(f"Footer rendering failed: {e}")
            return ""

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _get_html_header(self, config: ReportConfig) -> str:
        """Get HTML document header with styles."""
        html = "<!DOCTYPE html>\n"
        html += "<html lang='en'>\n"
        html += "<head>\n"
        html += "  <meta charset='UTF-8'>\n"
        html += "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        html += f"  <title>{self._escape_html(config.report_title)}</title>\n"
        html += "  <style>\n"
        html += self._get_default_styles(config.branding)
        if config.custom_css:
            html += f"    {config.custom_css}\n"
        html += "  </style>\n"
        html += "</head>\n"
        return html

    def _get_default_styles(self, branding: Optional[BrandingConfig]) -> str:
        """Get default CSS styles."""
        if not branding:
            branding = BrandingConfig(company_name="AlgoTrading")

        css = f"""
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}

    body {{
      font-family: {branding.font_family};
      line-height: 1.6;
      color: #333;
      background-color: #f5f5f5;
    }}

    header.report-header {{
      background: linear-gradient(135deg, {branding.primary_color} 0%, {branding.secondary_color} 100%);
      color: white;
      padding: 40px;
      text-align: center;
      margin-bottom: 30px;
    }}

    header h1.report-title {{
      font-size: 2.5em;
      margin-bottom: 10px;
    }}

    header h2.report-subtitle {{
      font-size: 1.5em;
      opacity: 0.9;
    }}

    section.report-section {{
      background: white;
      margin: 20px;
      padding: 30px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}

    section.report-section h2 {{
      color: {branding.primary_color};
      margin-bottom: 20px;
      border-bottom: 2px solid {branding.accent_color};
      padding-bottom: 10px;
    }}

    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;
      margin: 20px 0;
    }}

    .metric-card {{
      background: #f9f9f9;
      border-left: 4px solid {branding.primary_color};
      padding: 15px;
      border-radius: 4px;
    }}

    .metric-label {{
      font-size: 0.9em;
      color: #666;
      margin-bottom: 8px;
    }}

    .metric-value {{
      font-size: 1.5em;
      font-weight: bold;
      color: {branding.primary_color};
    }}

    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
    }}

    table.data-table th {{
      background-color: {branding.primary_color};
      color: white;
      padding: 12px;
      text-align: left;
    }}

    table.data-table td {{
      padding: 10px 12px;
      border-bottom: 1px solid #ddd;
    }}

    table.data-table tr:hover {{
      background-color: #f5f5f5;
    }}

    footer.report-footer {{
      background-color: #333;
      color: white;
      text-align: center;
      padding: 20px;
      margin-top: 40px;
    }}

    @media (max-width: 768px) {{
      header.report-header {{
        padding: 20px;
      }}

      header h1.report-title {{
        font-size: 1.8em;
      }}

      .metrics-grid {{
        grid-template-columns: 1fr;
      }}

      section.report-section {{
        margin: 10px;
        padding: 15px;
      }}
    }}
    """
        return css

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not isinstance(text, str):
            text = str(text)
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    def _format_label(self, text: str) -> str:
        """Format variable name to readable label."""
        # Convert snake_case to Title Case
        return " ".join(word.capitalize() for word in text.split("_"))

    def get_engine_status(self) -> Dict:
        """Get engine operational status."""
        return {
            "status": "operational",
            "reports_generated": self.reports_generated,
            "templates_cached": len(self.templates_cached),
            "last_update": datetime.utcnow().isoformat(),
        }


# ============================================================================
# SINGLETON ACCESSOR
# ============================================================================


_html_engine_instance: Optional[HTMLTemplateEngine] = None


def get_html_template_engine() -> HTMLTemplateEngine:
    """Get or create HTMLTemplateEngine singleton."""
    global _html_engine_instance
    if _html_engine_instance is None:
        _html_engine_instance = HTMLTemplateEngine()
    return _html_engine_instance
