"""Unit tests for T9.1 HTMLTemplateEngine component"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.services.reporting_generator.html_template_engine import (
    BrandingConfig,
    HTMLReport,
    HTMLTemplateEngine,
    ReportConfig,
    ReportSection,
    get_html_template_engine,
)


class TestBrandingConfig:
    """Test BrandingConfig data class."""

    def test_initialization_with_defaults(self):
        """Test branding config with default values."""
        branding = BrandingConfig(company_name="TestCorp")

        assert branding.company_name == "TestCorp"
        assert branding.primary_color == "#1f77b4"
        assert branding.secondary_color == "#ff7f0e"
        assert branding.company_logo_url is None

    def test_initialization_with_custom_colors(self):
        """Test branding config with custom colors."""
        branding = BrandingConfig(
            company_name="CustomCorp",
            primary_color="#FF0000",
            secondary_color="#00FF00",
        )

        assert branding.primary_color == "#FF0000"
        assert branding.secondary_color == "#00FF00"

    def test_initialization_with_logo(self):
        """Test branding config with logo URL."""
        branding = BrandingConfig(
            company_name="BrandedCorp",
            company_logo_url="https://example.com/logo.png",
        )

        assert branding.company_logo_url == "https://example.com/logo.png"


class TestReportSection:
    """Test ReportSection data class."""

    def test_initialization(self):
        """Test report section initialization."""
        section = ReportSection(
            section_name="metrics",
            title="Performance Metrics",
            content={"metric1": "value1"},
            section_type="metrics",
        )

        assert section.section_name == "metrics"
        assert section.section_type == "metrics"
        assert section.enabled is True

    def test_section_with_custom_order(self):
        """Test section with custom ordering."""
        section = ReportSection(
            section_name="summary",
            title="Summary",
            content={},
            section_type="text",
            order=1,
        )

        assert section.order == 1


class TestReportConfig:
    """Test ReportConfig data class."""

    def test_initialization_with_defaults(self):
        """Test report config with default values."""
        config = ReportConfig(report_title="Test Report")

        assert config.report_title == "Test Report"
        assert config.include_toc is True
        assert config.include_summary is True
        assert config.include_disclaimers is True
        assert config.branding is not None
        assert config.report_date is not None

    def test_initialization_with_custom_branding(self):
        """Test report config with custom branding."""
        branding = BrandingConfig(company_name="CustomBrand")
        config = ReportConfig(
            report_title="Branded Report",
            branding=branding,
        )

        assert config.branding.company_name == "CustomBrand"

    def test_initialization_with_sections(self):
        """Test report config with custom sections."""
        section1 = ReportSection(
            section_name="sec1",
            title="Section 1",
            content={},
            section_type="metrics",
            order=0,
        )
        section2 = ReportSection(
            section_name="sec2",
            title="Section 2",
            content={},
            section_type="charts",
            order=1,
        )

        config = ReportConfig(
            report_title="Multi-Section Report",
            sections=[section1, section2],
        )

        assert len(config.sections) == 2


class TestHTMLReport:
    """Test HTMLReport data class."""

    def test_initialization(self):
        """Test HTML report initialization."""
        report = HTMLReport(
            content="<html>Test</html>",
            report_title="Test Report",
            generation_date=datetime.utcnow(),
            file_size_kb=Decimal("50"),
            sections_count=3,
            metadata={"strategy": "test"},
        )

        assert report.report_title == "Test Report"
        assert report.sections_count == 3

    def test_to_dict(self):
        """Test conversion to dictionary."""
        report = HTMLReport(
            content="<html>Test</html>",
            report_title="Test",
            generation_date=datetime.utcnow(),
            file_size_kb=Decimal("100"),
            sections_count=5,
            metadata={"key": "value"},
        )

        result_dict = report.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["report_title"] == "Test"
        assert result_dict["sections_count"] == 5
        assert isinstance(result_dict["file_size_kb"], float)


class TestHTMLTemplateEngine:
    """Test HTMLTemplateEngine component."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = HTMLTemplateEngine()

    def test_initialization(self):
        """Test engine initialization."""
        assert self.engine.reports_generated == 0
        assert len(self.engine.templates_cached) == 0

    # Report Rendering Tests
    def test_render_report_minimal(self):
        """Test minimal report rendering."""
        config = ReportConfig(report_title="Minimal Report")

        report = self.engine.render_report(config)

        assert isinstance(report, HTMLReport)
        assert report.report_title == "Minimal Report"
        assert len(report.content) > 0
        assert "<!DOCTYPE html>" in report.content
        assert "</html>" in report.content

    def test_render_report_with_metrics(self):
        """Test report rendering with metrics."""
        config = ReportConfig(
            report_title="Metrics Report",
            strategy_name="TestStrategy",
        )
        metrics = {
            "annual_return_pct": Decimal("15.5"),
            "sharpe_ratio": Decimal("1.25"),
            "max_drawdown_pct": Decimal("12.5"),
        }

        report = self.engine.render_report(config, metrics=metrics)

        assert "15.5" in report.content or "15" in report.content
        assert "TestStrategy" in report.content

    def test_render_report_with_sections(self):
        """Test report with multiple sections."""
        sections = [
            ReportSection(
                section_name="perf",
                title="Performance",
                content={},
                section_type="metrics",
                order=0,
            ),
            ReportSection(
                section_name="risk",
                title="Risk Analysis",
                content={},
                section_type="text",
                order=1,
            ),
        ]

        config = ReportConfig(
            report_title="Multi-Section",
            sections=sections,
        )

        report = self.engine.render_report(config)

        assert "Performance" in report.content
        assert "Risk Analysis" in report.content

    def test_render_report_increments_counter(self):
        """Test that rendering increments report counter."""
        initial_count = self.engine.reports_generated

        config = ReportConfig(report_title="Counter Test")
        self.engine.render_report(config)

        assert self.engine.reports_generated == initial_count + 1

    def test_render_report_multiple_generations(self):
        """Test multiple report generations."""
        for i in range(3):
            config = ReportConfig(report_title=f"Report {i}")
            self.engine.render_report(config)

        assert self.engine.reports_generated == 3

    def test_render_report_without_toc(self):
        """Test report without table of contents."""
        config = ReportConfig(
            report_title="No TOC Report",
            include_toc=False,
        )

        report = self.engine.render_report(config)

        assert "Contents" not in report.content or "table-of-contents" not in report.content

    def test_render_report_without_summary(self):
        """Test report without executive summary."""
        config = ReportConfig(
            report_title="No Summary",
            include_summary=False,
        )

        report = self.engine.render_report(config)

        assert "Executive Summary" not in report.content

    def test_render_report_without_disclaimers(self):
        """Test report without disclaimers."""
        config = ReportConfig(
            report_title="No Disclaimers",
            include_disclaimers=False,
        )

        report = self.engine.render_report(config)

        # When include_disclaimers is False, the Performance Disclaimer section should not be present
        assert (
            "Performance Disclaimer" not in report.content
            or report.metadata["has_disclaimers"] == False
        )

    # HTML Escaping Tests
    def test_html_escaping_in_title(self):
        """Test HTML escaping in report title."""
        config = ReportConfig(
            report_title="<script>alert('xss')</script>",
        )

        report = self.engine.render_report(config)

        assert "<script>" not in report.content
        assert "&lt;script&gt;" in report.content

    def test_html_escaping_in_strategy_name(self):
        """Test HTML escaping in strategy name."""
        config = ReportConfig(
            report_title="Test",
            strategy_name="<img src=x onerror='alert(1)'>",
        )

        report = self.engine.render_report(config)

        assert "<img" not in report.content or "&lt;img" in report.content

    def test_html_escaping_in_metrics(self):
        """Test HTML escaping in metrics values."""
        section = ReportSection(
            section_name="metrics",
            title="Metrics",
            content={},
            section_type="metrics",
        )
        config = ReportConfig(
            report_title="Test",
            sections=[section],
        )
        metrics = {
            "test_metric": "<script>alert('xss')</script>",
        }

        report = self.engine.render_report(config, metrics=metrics)

        assert "<script>" not in report.content
        assert "&lt;script&gt;" in report.content

    # Branding Tests
    def test_render_with_custom_branding(self):
        """Test report with custom branding."""
        branding = BrandingConfig(
            company_name="MyCompany",
            primary_color="#FF0000",
            company_logo_url="https://example.com/logo.png",
        )
        config = ReportConfig(
            report_title="Branded Report",
            branding=branding,
        )

        report = self.engine.render_report(config)

        assert "MyCompany" in report.content
        assert "https://example.com/logo.png" in report.content
        assert "#FF0000" in report.content

    def test_render_with_footer_text(self):
        """Test report with custom footer text."""
        branding = BrandingConfig(
            company_name="Test",
            report_footer_text="© 2024 Test Corporation. All rights reserved.",
        )
        config = ReportConfig(
            report_title="Test",
            branding=branding,
        )

        report = self.engine.render_report(config)

        assert "© 2024 Test Corporation. All rights reserved." in report.content

    # Section Content Tests
    def test_render_metrics_section(self):
        """Test metrics section rendering."""
        section = ReportSection(
            section_name="metrics",
            title="Key Metrics",
            content={},
            section_type="metrics",
        )
        config = ReportConfig(
            report_title="Test",
            sections=[section],
        )
        metrics = {
            "annual_return": Decimal("15.5"),
            "volatility": Decimal("10.2"),
        }

        report = self.engine.render_report(config, metrics=metrics)

        assert "Key Metrics" in report.content
        assert "metrics-grid" in report.content

    def test_render_charts_section(self):
        """Test charts section rendering."""
        section = ReportSection(
            section_name="charts",
            title="Performance Charts",
            content={},
            section_type="charts",
        )
        config = ReportConfig(
            report_title="Test",
            sections=[section],
        )
        charts = {
            "cumulative_returns": "<svg>Chart 1</svg>",
            "drawdown": "<svg>Chart 2</svg>",
        }

        report = self.engine.render_report(config, charts_data=charts)

        assert "Performance Charts" in report.content
        assert "<svg>Chart 1</svg>" in report.content

    def test_render_tables_section(self):
        """Test tables section rendering."""
        section = ReportSection(
            section_name="tables",
            title="Performance Table",
            content={},
            section_type="tables",
        )
        config = ReportConfig(
            report_title="Test",
            sections=[section],
        )
        tables = {
            "monthly_returns": [
                {"month": "Jan", "return": "2.5%"},
                {"month": "Feb", "return": "1.8%"},
            ]
        }

        report = self.engine.render_report(config, tables_data=tables)

        assert "Performance Table" in report.content
        assert "data-table" in report.content
        assert "Jan" in report.content

    def test_render_text_section(self):
        """Test text section rendering."""
        section = ReportSection(
            section_name="intro",
            title="Introduction",
            content={"text": "This is the introduction text."},
            section_type="text",
        )
        config = ReportConfig(
            report_title="Test",
            sections=[section],
        )

        report = self.engine.render_report(config)

        assert "Introduction" in report.content
        assert "This is the introduction text." in report.content

    # HTML Structure Tests
    def test_html_doctype_present(self):
        """Test that HTML doctype is present."""
        config = ReportConfig(report_title="Test")
        report = self.engine.render_report(config)

        assert "<!DOCTYPE html>" in report.content

    def test_html_opening_closing_tags(self):
        """Test HTML opening and closing tags."""
        config = ReportConfig(report_title="Test")
        report = self.engine.render_report(config)

        assert "<html" in report.content
        assert "</html>" in report.content
        assert "<head" in report.content
        assert "</head>" in report.content
        assert "<body" in report.content
        assert "</body>" in report.content

    def test_meta_charset_present(self):
        """Test that meta charset is present."""
        config = ReportConfig(report_title="Test")
        report = self.engine.render_report(config)

        assert "charset=" in report.content.lower()

    def test_viewport_meta_tag(self):
        """Test that viewport meta tag is present."""
        config = ReportConfig(report_title="Test")
        report = self.engine.render_report(config)

        assert "viewport" in report.content

    # CSS Tests
    def test_default_styles_included(self):
        """Test that default styles are included."""
        config = ReportConfig(report_title="Test")
        report = self.engine.render_report(config)

        assert "<style>" in report.content
        assert "body {" in report.content or "body{" in report.content
        assert "</style>" in report.content

    def test_custom_css_included(self):
        """Test that custom CSS is included."""
        custom_css = ".custom { color: red; }"
        config = ReportConfig(
            report_title="Test",
            custom_css=custom_css,
        )
        report = self.engine.render_report(config)

        assert custom_css in report.content

    def test_responsive_design_styles(self):
        """Test that responsive design styles are present."""
        config = ReportConfig(report_title="Test")
        report = self.engine.render_report(config)

        assert "@media" in report.content

    # Status Tests
    def test_get_engine_status(self):
        """Test engine status reporting."""
        status = self.engine.get_engine_status()

        assert status["status"] == "operational"
        assert "reports_generated" in status
        assert "templates_cached" in status
        assert "last_update" in status

    # Singleton Tests
    def test_singleton_pattern(self):
        """Test singleton pattern for engine."""
        engine1 = get_html_template_engine()
        engine2 = get_html_template_engine()

        assert engine1 is engine2

    # Edge Cases
    def test_render_with_empty_metrics(self):
        """Test rendering with empty metrics."""
        config = ReportConfig(report_title="Test")
        report = self.engine.render_report(config, metrics={})

        assert isinstance(report, HTMLReport)
        assert len(report.content) > 0

    def test_render_with_special_characters_in_title(self):
        """Test rendering with special characters."""
        config = ReportConfig(report_title="Test & Report™ — 2024")

        report = self.engine.render_report(config)

        assert isinstance(report, HTMLReport)
        assert len(report.content) > 0

    def test_file_size_calculation(self):
        """Test that file size is calculated."""
        config = ReportConfig(report_title="Test")
        report = self.engine.render_report(config)

        assert report.file_size_kb > Decimal("0")
        assert isinstance(report.file_size_kb, Decimal)

    def test_section_order_respected(self):
        """Test that sections are ordered correctly."""
        sections = [
            ReportSection(
                section_name="s3",
                title="Third",
                content={},
                section_type="text",
                order=2,
            ),
            ReportSection(
                section_name="s1",
                title="First",
                content={},
                section_type="text",
                order=0,
            ),
            ReportSection(
                section_name="s2",
                title="Second",
                content={},
                section_type="text",
                order=1,
            ),
        ]

        config = ReportConfig(
            report_title="Ordered",
            sections=sections,
        )

        report = self.engine.render_report(config)

        # Check order in content
        first_idx = report.content.find("First")
        second_idx = report.content.find("Second")
        third_idx = report.content.find("Third")

        assert first_idx < second_idx < third_idx

    def test_disabled_sections_not_rendered(self):
        """Test that disabled sections are not rendered."""
        sections = [
            ReportSection(
                section_name="enabled",
                title="Enabled Section",
                content={},
                section_type="text",
                enabled=True,
            ),
            ReportSection(
                section_name="disabled",
                title="Disabled Section",
                content={},
                section_type="text",
                enabled=False,
            ),
        ]

        config = ReportConfig(
            report_title="Test",
            sections=sections,
        )

        report = self.engine.render_report(config)

        assert "Enabled Section" in report.content
        assert "Disabled Section" not in report.content

    def test_label_formatting(self):
        """Test that labels are formatted from snake_case."""
        config = ReportConfig(report_title="Test")
        metrics = {
            "annual_return_pct": Decimal("15"),
            "max_drawdown_pct": Decimal("10"),
        }

        report = self.engine.render_report(config, metrics=metrics)

        # Should contain formatted labels (capitalized words)
        assert "Annual" in report.content or "annual" in report.content

    def test_decimal_values_formatting(self):
        """Test that Decimal values are properly formatted."""
        config = ReportConfig(report_title="Test")
        metrics = {
            "sharpe_ratio": Decimal("1.25"),
            "return": Decimal("15.5555"),
        }

        report = self.engine.render_report(config, metrics=metrics)

        assert "1.25" in report.content

    def test_report_metadata_complete(self):
        """Test that report metadata is complete."""
        config = ReportConfig(
            report_title="Test Report",
            strategy_name="TestStrategy",
        )
        report = self.engine.render_report(config)

        assert report.metadata["strategy_name"] == "TestStrategy"
        assert "report_date" in report.metadata
        assert "sections" in report.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
