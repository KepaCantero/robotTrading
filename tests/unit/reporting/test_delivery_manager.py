"""
T9.1 PHASE 5: Tests for ReportDeliveryManager

Tests cover:
- HTML export functionality
- PDF export (with fallback handling)
- Excel export
- Email delivery
- S3 upload
- Error handling
"""

import json
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path


from app.services.reporting_generator.delivery_manager import (
    DeliveryChannel,
    DeliveryResult,
    EmailConfig,
    ExportConfig,
    ExportFormat,
    ExportResult,
    ReportDeliveryManager,
    S3Config,
    get_delivery_manager,
)


class TestExportConfig:
    """Tests for ExportConfig dataclass."""

    def test_export_config_creation(self):
        """Test ExportConfig creation with all fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ExportConfig(
                format=ExportFormat.HTML,
                output_path=Path(tmpdir) / "report.html",
                include_timestamp=True,
                compress=False,
                quality="high",
            )

            assert config.format == ExportFormat.HTML
            assert config.include_timestamp is True
            assert config.quality == "high"

    def test_export_config_defaults(self):
        """Test ExportConfig default values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ExportConfig(
                format=ExportFormat.PDF,
                output_path=Path(tmpdir) / "report.pdf",
            )

            assert config.include_timestamp is True
            assert config.compress is False


class TestEmailConfig:
    """Tests for EmailConfig dataclass."""

    def test_email_config_creation(self):
        """Test EmailConfig creation."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            sender_email="sender@example.com",
            sender_password="password",
            recipient_emails=["user1@example.com", "user2@example.com"],
            subject="Performance Report",
        )

        assert config.smtp_server == "smtp.gmail.com"
        assert config.smtp_port == 587
        assert len(config.recipient_emails) == 2
        assert config.use_tls is True


class TestS3Config:
    """Tests for S3Config dataclass."""

    def test_s3_config_creation(self):
        """Test S3Config creation."""
        config = S3Config(
            bucket_name="my-bucket",
            region="us-east-1",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        assert config.bucket_name == "my-bucket"
        assert config.region == "us-east-1"
        assert config.prefix == "reports"

    def test_s3_config_custom_prefix(self):
        """Test S3Config with custom prefix."""
        config = S3Config(
            bucket_name="my-bucket",
            region="us-east-1",
            access_key_id="key",
            secret_access_key="secret",
            prefix="custom/path",
        )

        assert config.prefix == "custom/path"


class TestExportResult:
    """Tests for ExportResult dataclass."""

    def test_export_result_success(self):
        """Test successful ExportResult."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "report.html"
            file_path.write_text("<html>Test</html>")

            result = ExportResult(
                success=True,
                format=ExportFormat.HTML,
                file_path=file_path,
                file_size_mb=Decimal("0.001"),
                export_time_ms=Decimal("100"),
                message="Success",
                timestamp=datetime.utcnow(),
            )

            assert result.success is True
            assert result.format == ExportFormat.HTML
            assert result.file_path == file_path


class TestDeliveryResult:
    """Tests for DeliveryResult dataclass."""

    def test_delivery_result_success(self):
        """Test successful DeliveryResult."""
        result = DeliveryResult(
            success=True,
            channel=DeliveryChannel.EMAIL,
            delivery_time_ms=Decimal("250"),
            recipient="user@example.com",
            message="Email sent successfully",
            timestamp=datetime.utcnow(),
        )

        assert result.success is True
        assert result.channel == DeliveryChannel.EMAIL
        assert result.recipient == "user@example.com"


class TestReportDeliveryManager:
    """Tests for ReportDeliveryManager class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.manager = ReportDeliveryManager()
        self.sample_html = "<html><head><title>Test</title></head><body>Report</body></html>"
        self.sample_metrics = {
            "sharpe_ratio": 1.5,
            "max_drawdown": -0.15,
            "return": 0.25,
        }

    # ========================================================================
    # INITIALIZATION TESTS
    # ========================================================================

    def test_manager_initialization(self):
        """Test ReportDeliveryManager initialization."""
        assert self.manager.exports_completed == 0
        assert self.manager.deliveries_completed == 0

    # ========================================================================
    # HTML EXPORT TESTS
    # ========================================================================

    def test_export_to_html_basic(self):
        """Test basic HTML export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            result = self.manager.export_to_html(self.sample_html, output_path)

            assert result.success is True
            assert result.format == ExportFormat.HTML
            assert result.file_path.exists()
            assert result.file_path.suffix == ".html"

    def test_export_to_html_creates_directory(self):
        """Test that HTML export creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "reports" / "2024" / "report.html"
            result = self.manager.export_to_html(
                self.sample_html, output_path, include_timestamp=False
            )

            assert result.success is True
            assert output_path.exists()
            assert output_path.parent == Path(tmpdir) / "reports" / "2024"

    def test_export_to_html_with_timestamp(self):
        """Test HTML export with timestamp in filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            result = self.manager.export_to_html(
                self.sample_html, output_path, include_timestamp=True
            )

            assert result.success is True
            assert "_" in result.file_path.stem  # Timestamp separator
            assert result.file_path.suffix == ".html"

    def test_export_to_html_file_size(self):
        """Test HTML export calculates file size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            result = self.manager.export_to_html(
                self.sample_html, output_path, include_timestamp=False
            )

            assert result.success is True
            assert result.file_size_mb > Decimal("0")

    def test_export_to_html_export_time(self):
        """Test HTML export measures export time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            result = self.manager.export_to_html(
                self.sample_html, output_path, include_timestamp=False
            )

            assert result.success is True
            assert result.export_time_ms >= Decimal("0")

    def test_export_to_html_counter_increments(self):
        """Test that exports_completed counter increments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initial_count = self.manager.exports_completed
            output_path = Path(tmpdir) / "report.html"
            self.manager.export_to_html(self.sample_html, output_path, include_timestamp=False)

            assert self.manager.exports_completed == initial_count + 1

    def test_export_to_html_content_preserved(self):
        """Test that HTML content is preserved in export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            result = self.manager.export_to_html(
                self.sample_html, output_path, include_timestamp=False
            )

            assert result.success is True
            content = result.file_path.read_text(encoding="utf-8")
            assert content == self.sample_html

    def test_export_to_html_error_handling(self):
        """Test HTML export error handling."""
        # Use an invalid path that cannot be created
        output_path = Path("/invalid/path/that/does/not/exist/report.html")
        result = self.manager.export_to_html(self.sample_html, output_path, include_timestamp=False)

        assert result.success is False
        assert result.file_path is None
        assert "failed" in result.message.lower()

    # ========================================================================
    # PDF EXPORT TESTS
    # ========================================================================

    def test_export_to_pdf_fallback(self):
        """Test PDF export falls back to HTML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.pdf"
            result = self.manager.export_to_pdf(
                self.sample_html, output_path, include_timestamp=False
            )

            # Should succeed with HTML fallback
            assert result.success is True
            assert result.format == ExportFormat.PDF
            assert result.file_path is not None

    def test_export_to_pdf_quality_parameter(self):
        """Test PDF export accepts quality parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.pdf"
            result = self.manager.export_to_pdf(
                self.sample_html,
                output_path,
                quality="low",
                include_timestamp=False,
            )

            assert result.success is True

    def test_export_to_pdf_with_timestamp(self):
        """Test PDF export with timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.pdf"
            result = self.manager.export_to_pdf(
                self.sample_html, output_path, include_timestamp=True
            )

            assert result.success is True

    # ========================================================================
    # EXCEL EXPORT TESTS
    # ========================================================================

    def test_export_to_excel_basic(self):
        """Test basic Excel export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "metrics.xlsx"
            result = self.manager.export_to_excel(
                self.sample_metrics, output_path, include_timestamp=False
            )

            assert result.success is True
            assert result.format == ExportFormat.EXCEL

    def test_export_to_excel_fallback_json(self):
        """Test Excel export falls back to JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "metrics.xlsx"
            result = self.manager.export_to_excel(
                self.sample_metrics, output_path, include_timestamp=False
            )

            # Should create JSON file as fallback
            assert result.success is True
            json_file = output_path.with_suffix(".json")
            assert json_file.exists()

    def test_export_to_excel_json_content(self):
        """Test Excel export creates valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "metrics.xlsx"
            result = self.manager.export_to_excel(
                self.sample_metrics, output_path, include_timestamp=False
            )

            json_file = output_path.with_suffix(".json")
            content = json.loads(json_file.read_text())
            assert content["sharpe_ratio"] == 1.5
            assert content["max_drawdown"] == -0.15

    def test_export_to_excel_with_timestamp(self):
        """Test Excel export with timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "metrics.xlsx"
            result = self.manager.export_to_excel(
                self.sample_metrics, output_path, include_timestamp=True
            )

            assert result.success is True
            assert "_" in result.file_path.stem

    def test_export_to_excel_counter_increments(self):
        """Test that exports_completed increments for Excel."""
        with tempfile.TemporaryDirectory() as tmpdir:
            initial_count = self.manager.exports_completed
            output_path = Path(tmpdir) / "metrics.xlsx"
            self.manager.export_to_excel(self.sample_metrics, output_path, include_timestamp=False)

            assert self.manager.exports_completed == initial_count + 1

    def test_export_to_excel_error_handling(self):
        """Test Excel export error handling."""
        output_path = Path("/invalid/path/metrics.xlsx")
        result = self.manager.export_to_excel(self.sample_metrics, output_path)

        assert result.success is False

    # ========================================================================
    # EMAIL DELIVERY TESTS
    # ========================================================================

    def test_send_email_basic(self):
        """Test basic email delivery."""
        email_config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            sender_email="sender@example.com",
            sender_password="password",
            recipient_emails=["user@example.com"],
            subject="Test Report",
        )

        result = self.manager.send_email(self.sample_html, email_config)

        assert result.success is True
        assert result.channel == DeliveryChannel.EMAIL
        assert "user@example.com" in result.recipient

    def test_send_email_multiple_recipients(self):
        """Test email delivery to multiple recipients."""
        email_config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            sender_email="sender@example.com",
            sender_password="password",
            recipient_emails=["user1@example.com", "user2@example.com"],
            subject="Test Report",
        )

        result = self.manager.send_email(self.sample_html, email_config)

        assert result.success is True
        assert "user1@example.com" in result.recipient
        assert "user2@example.com" in result.recipient

    def test_send_email_custom_body(self):
        """Test email with custom body text."""
        email_config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            sender_email="sender@example.com",
            sender_password="password",
            recipient_emails=["user@example.com"],
            subject="Report",
            body="Custom email body",
        )

        result = self.manager.send_email(self.sample_html, email_config)

        assert result.success is True

    def test_send_email_delivery_time(self):
        """Test email delivery measures time."""
        email_config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            sender_email="sender@example.com",
            sender_password="password",
            recipient_emails=["user@example.com"],
            subject="Test",
        )

        result = self.manager.send_email(self.sample_html, email_config)

        assert result.success is True
        assert result.delivery_time_ms >= Decimal("0")

    def test_send_email_counter_increments(self):
        """Test deliveries_completed counter increments."""
        email_config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            sender_email="sender@example.com",
            sender_password="password",
            recipient_emails=["user@example.com"],
            subject="Test",
        )

        initial_count = self.manager.deliveries_completed
        self.manager.send_email(self.sample_html, email_config)

        assert self.manager.deliveries_completed == initial_count + 1

    # ========================================================================
    # S3 UPLOAD TESTS
    # ========================================================================

    def test_upload_to_s3_file_exists(self):
        """Test S3 upload with existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "report.html"
            file_path.write_text(self.sample_html)

            s3_config = S3Config(
                bucket_name="test-bucket",
                region="us-east-1",
                access_key_id="key",
                secret_access_key="secret",
            )

            result = self.manager.upload_to_s3(file_path, s3_config)

            assert result.success is True
            assert result.channel == DeliveryChannel.S3

    def test_upload_to_s3_file_not_found(self):
        """Test S3 upload with non-existent file."""
        s3_config = S3Config(
            bucket_name="test-bucket",
            region="us-east-1",
            access_key_id="key",
            secret_access_key="secret",
        )

        result = self.manager.upload_to_s3(Path("/invalid/file.html"), s3_config)

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_upload_to_s3_custom_key(self):
        """Test S3 upload with custom object key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "report.html"
            file_path.write_text(self.sample_html)

            s3_config = S3Config(
                bucket_name="test-bucket",
                region="us-east-1",
                access_key_id="key",
                secret_access_key="secret",
            )

            result = self.manager.upload_to_s3(
                file_path, s3_config, object_key="custom/path/report.html"
            )

            assert result.success is True
            assert "custom/path" in result.recipient

    def test_upload_to_s3_prefix_in_path(self):
        """Test S3 upload includes configured prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "report.html"
            file_path.write_text(self.sample_html)

            s3_config = S3Config(
                bucket_name="test-bucket",
                region="us-east-1",
                access_key_id="key",
                secret_access_key="secret",
                prefix="archived",
            )

            result = self.manager.upload_to_s3(file_path, s3_config)

            assert result.success is True
            assert "archived" in result.recipient

    def test_upload_to_s3_counter_increments(self):
        """Test deliveries_completed increments for S3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "report.html"
            file_path.write_text(self.sample_html)

            s3_config = S3Config(
                bucket_name="test-bucket",
                region="us-east-1",
                access_key_id="key",
                secret_access_key="secret",
            )

            initial_count = self.manager.deliveries_completed
            self.manager.upload_to_s3(file_path, s3_config)

            assert self.manager.deliveries_completed == initial_count + 1

    # ========================================================================
    # UTILITY TESTS
    # ========================================================================

    def test_get_manager_status(self):
        """Test manager status reporting."""
        status = self.manager.get_manager_status()

        assert status["status"] == "operational"
        assert "exports_completed" in status
        assert "deliveries_completed" in status
        assert "last_update" in status

    def test_get_manager_status_format(self):
        """Test manager status format."""
        status = self.manager.get_manager_status()

        assert isinstance(status["exports_completed"], int)
        assert isinstance(status["deliveries_completed"], int)
        assert isinstance(status["last_update"], str)
        # Should be ISO format datetime
        datetime.fromisoformat(status["last_update"])

    # ========================================================================
    # SINGLETON TESTS
    # ========================================================================

    def test_get_delivery_manager_singleton(self):
        """Test that get_delivery_manager returns singleton."""
        manager1 = get_delivery_manager()
        manager2 = get_delivery_manager()

        assert manager1 is manager2

    def test_singleton_persistence(self):
        """Test that singleton state persists."""
        manager1 = get_delivery_manager()
        initial_exports = manager1.exports_completed

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.html"
            manager1.export_to_html("<html></html>", output_path, include_timestamp=False)

        manager2 = get_delivery_manager()
        assert manager2.exports_completed == initial_exports + 1


class TestIntegrationDelivery:
    """Integration tests for delivery operations."""

    def setup_method(self):
        """Setup test fixtures."""
        self.manager = ReportDeliveryManager()
        self.sample_html = (
            "<html><head><title>Full Report</title></head><body>Complete Report</body></html>"
        )
        self.sample_metrics = {
            "sharpe_ratio": 1.8,
            "max_drawdown": -0.12,
            "total_return": 0.35,
            "win_rate": 0.65,
        }

    def test_multi_format_export(self):
        """Test exporting to multiple formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)

            # Export HTML
            html_result = self.manager.export_to_html(
                self.sample_html,
                base_path / "report.html",
                include_timestamp=False,
            )

            # Export Excel
            excel_result = self.manager.export_to_excel(
                self.sample_metrics,
                base_path / "metrics.xlsx",
                include_timestamp=False,
            )

            assert html_result.success
            assert excel_result.success
            assert self.manager.exports_completed == 2

    def test_export_and_upload_workflow(self):
        """Test export followed by upload to S3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Export HTML
            export_result = self.manager.export_to_html(
                self.sample_html,
                tmppath / "report.html",
                include_timestamp=False,
            )

            assert export_result.success

            # Upload to S3
            s3_config = S3Config(
                bucket_name="reports",
                region="us-east-1",
                access_key_id="key",
                secret_access_key="secret",
            )

            upload_result = self.manager.upload_to_s3(export_result.file_path, s3_config)

            assert upload_result.success
            assert self.manager.exports_completed == 1
            assert self.manager.deliveries_completed == 1
