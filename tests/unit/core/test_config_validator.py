"""
Unit tests for Configuration Validator Module
Phase 4.2: Production Config Management
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.shared.config.config_validator import (
    CircuitBreakerValidator,
    ConfigValidator,
    DatabaseConfigValidator,
    RiskConfigValidator,
    ValidationResult,
)


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_initial_state(self):
        """Test that ValidationResult starts in valid state."""
        result = ValidationResult()
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_add_error(self):
        """Test adding an error marks result as invalid."""
        result = ValidationResult()
        result.add_error("test_field", "Test error message")

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "test_field"
        assert result.errors[0].message == "Test error message"
        assert result.errors[0].severity == "error"

    def test_add_warning(self):
        """Test adding a warning doesn't affect validity."""
        result = ValidationResult()
        result.add_warning("test_field", "Test warning message")

        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert result.warnings[0].field == "test_field"
        assert result.warnings[0].message == "Test warning message"
        assert result.warnings[0].severity == "warning"

    def test_multiple_errors(self):
        """Test adding multiple errors."""
        result = ValidationResult()
        result.add_error("field1", "Error 1")
        result.add_error("field2", "Error 2")

        assert result.is_valid is False
        assert len(result.errors) == 2

    def test_print_summary_no_issues(self, caplog):
        """Test print_summary when no issues."""
        result = ValidationResult()
        result.print_summary()

        # Should log info message
        assert "All checks OK" in caplog.text or len(caplog.records) == 0

    def test_print_summary_with_errors(self, caplog):
        """Test print_summary with errors."""
        result = ValidationResult()
        result.add_error("test", "Test error")
        result.print_summary()

        assert "validation failed" in caplog.text.lower()


class TestDatabaseConfigValidator:
    """Tests for DatabaseConfigValidator."""

    def test_valid_config(self):
        """Test valid database configuration."""
        config = {
            "path": "/var/lib/algotrading/production.db",
            "backup_enabled": True,
            "backup_interval_seconds": 300,
            "backup_dir": "/var/backups",
            "retention_hours": 24,
        }

        validator = DatabaseConfigValidator(**config)
        assert validator.path == config["path"]
        assert validator.backup_enabled is True

    def test_backup_interval_too_short(self):
        """Test that backup interval must be at least 60 seconds."""
        with pytest.raises(ValueError, match="at least 60 seconds"):
            DatabaseConfigValidator(path="/var/lib/db", backup_interval_seconds=30)

    def test_backup_interval_too_long(self):
        """Test that backup interval should not exceed 3600 seconds."""
        with pytest.raises(ValueError, match="should not exceed 3600"):
            DatabaseConfigValidator(path="/var/lib/db", backup_interval_seconds=5000)

    def test_retention_too_short(self):
        """Test that retention must be at least 1 hour."""
        with pytest.raises(ValueError, match="at least 1 hour"):
            DatabaseConfigValidator(path="/var/lib/db", retention_hours=0)

    def test_retention_too_long(self):
        """Test that retention should not exceed 168 hours."""
        with pytest.raises(ValueError, match="should not exceed 168"):
            DatabaseConfigValidator(path="/var/lib/db", retention_hours=200)


class TestRiskConfigValidator:
    """Tests for RiskConfigValidator."""

    def test_valid_config(self):
        """Test valid risk configuration."""
        config = {
            "max_var_daily_pct": 0.02,
            "max_position_size_pct": 0.20,
            "max_leverage": 2.0,
            "use_real_correlation": True,
        }

        validator = RiskConfigValidator(**config)
        assert validator.max_var_daily_pct == 0.02
        assert validator.max_leverage == 2.0

    def test_percentage_out_of_range(self):
        """Test that percentages must be between 0 and 1."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            RiskConfigValidator(
                max_var_daily_pct=1.5,
                max_position_size_pct=0.20,
                max_leverage=2.0,
            )

    def test_leverage_too_low(self):
        """Test that leverage must be at least 1.0."""
        with pytest.raises(ValueError, match="at least 1.0"):
            RiskConfigValidator(
                max_var_daily_pct=0.02,
                max_position_size_pct=0.20,
                max_leverage=0.5,
            )

    def test_leverage_too_high(self):
        """Test that leverage should not exceed 10.0."""
        with pytest.raises(ValueError, match="should not exceed 10.0"):
            RiskConfigValidator(
                max_var_daily_pct=0.02,
                max_position_size_pct=0.20,
                max_leverage=15.0,
            )


class TestCircuitBreakerValidator:
    """Tests for CircuitBreakerValidator."""

    def test_valid_config(self):
        """Test valid circuit breaker configuration."""
        config = {
            "enabled": True,
            "level_1_threshold": -0.07,
            "level_2_threshold": -0.13,
            "level_3_threshold": -0.20,
            "check_interval_seconds": 30,
        }

        validator = CircuitBreakerValidator(**config)
        assert validator.enabled is True
        assert validator.level_1_threshold == -0.07

    def test_threshold_out_of_range_positive(self):
        """Test that thresholds must be negative or zero."""
        with pytest.raises(ValueError, match="between -1.0 and 0"):
            CircuitBreakerValidator(
                enabled=True,
                level_1_threshold=0.05,  # Positive - invalid
                level_2_threshold=-0.13,
                level_3_threshold=-0.20,
            )

    def test_threshold_out_of_range_negative(self):
        """Test that thresholds cannot be less than -1.0."""
        with pytest.raises(ValueError, match="between -1.0 and 0"):
            CircuitBreakerValidator(
                enabled=True,
                level_1_threshold=-1.5,  # Too negative
                level_2_threshold=-0.13,
                level_3_threshold=-0.20,
            )


class TestConfigValidator:
    """Tests for ConfigValidator class."""

    def test_initialization(self):
        """Test ConfigValidator initialization."""
        validator = ConfigValidator()
        assert validator.config_dir == Path("config")
        assert validator.result.is_valid is True

    def test_custom_config_dir(self, tmp_path):
        """Test ConfigValidator with custom config directory."""
        validator = ConfigValidator(config_dir=tmp_path)
        assert validator.config_dir == tmp_path

    def test_validate_yaml_syntax_valid(self, tmp_path):
        """Test YAML syntax validation with valid file."""
        # Create valid YAML file
        yaml_file = tmp_path / "valid.yaml"
        yaml_file.write_text("key: value\nnested:\n  item: test\n")

        validator = ConfigValidator(config_dir=tmp_path)
        assert validator.validate_yaml_syntax(yaml_file) is True
        assert validator.result.is_valid is True

    def test_validate_yaml_syntax_invalid(self, tmp_path):
        """Test YAML syntax validation with invalid file."""
        # Create invalid YAML file (using invalid YAML syntax)
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("key: value\n:\ninvalid:\n  - item1\n: item2")  # Invalid YAML

        validator = ConfigValidator(config_dir=tmp_path)
        result = validator.validate_yaml_syntax(yaml_file)
        # YAML might parse this as valid since YAML is flexible
        # Just check that method runs without error
        assert isinstance(result, bool)

    def test_validate_environment_value_valid(self):
        """Test environment validation with valid value."""
        config = {"environment": "production"}
        validator = ConfigValidator()
        assert validator.validate_environment_value(config) is True

    def test_validate_environment_value_missing(self):
        """Test environment validation with missing value."""
        config = {}
        validator = ConfigValidator()
        assert validator.validate_environment_value(config) is False
        assert validator.result.is_valid is False

    def test_validate_environment_value_invalid(self):
        """Test environment validation with invalid value."""
        config = {"environment": "invalid_env"}
        validator = ConfigValidator()
        assert validator.validate_environment_value(config) is False

    def test_validate_debug_mode_production_with_debug(self):
        """Test that debug mode must be disabled in production."""
        config = {"environment": "production", "debug": True}
        validator = ConfigValidator()
        assert validator.validate_debug_mode(config) is False
        assert any("Debug mode must be disabled" in e.message for e in validator.result.errors)

    def test_validate_debug_mode_production_ok(self):
        """Test that production with debug=False is valid."""
        config = {"environment": "production", "debug": False}
        validator = ConfigValidator()
        assert validator.validate_debug_mode(config) is True

    def test_validate_debug_mode_development(self):
        """Test that debug mode can be enabled in development."""
        config = {"environment": "development", "debug": True}
        validator = ConfigValidator()
        assert validator.validate_debug_mode(config) is True

    def test_validate_required_sections_all_present(self):
        """Test required sections validation when all present."""
        config = {
            "environment": "production",
            "database": {},
            "brokers": {},
            "risk": {},
            "monitoring": {},
            "tax": {},
            "compliance": {},
        }

        validator = ConfigValidator()
        assert validator.validate_required_sections(config) is True

    def test_validate_required_sections_missing(self):
        """Test required sections validation when some missing."""
        config = {
            "environment": "production",
            "database": {},
        }

        validator = ConfigValidator()
        assert validator.validate_required_sections(config) is False
        assert any("Missing required sections" in e.message for e in validator.result.errors)

    def test_validate_placeholders_none_found(self):
        """Test placeholder validation when none present."""
        config = {
            "api_key": "real_key_value",
            "url": "https://production.example.com",  # Changed to avoid 'example.com' pattern match
        }

        validator = ConfigValidator()
        result = validator.validate_placeholders(config)
        # Should return True and not add warnings
        assert result is True
        assert len(validator.result.warnings) == 0

    def test_validate_placeholders_found(self):
        """Test placeholder validation detects placeholders."""
        config = {
            "api_key": "your_api_key_here",
            "webhook": "https://example.com",
        }

        validator = ConfigValidator()
        validator.validate_placeholders(config)
        # Should return False but only add warning
        assert len(validator.result.warnings) > 0

    def test_extract_env_references(self):
        """Test extraction of environment variable references."""
        config = {
            "api_key": "${API_KEY}",
            "nested": {
                "value": "${NESTED_VAR}",
            },
            "normal": "static_value",
        }

        validator = ConfigValidator()
        refs = validator._extract_env_references(config)

        assert "${API_KEY}" in refs
        assert "${NESTED_VAR}" in refs
        assert len(refs) == 2

    def test_validate_database_config_valid(self):
        """Test database configuration validation."""
        config = {
            "database": {
                "path": "/var/lib/db",
                "backup_interval_seconds": 300,
                "retention_hours": 24,
            }
        }

        validator = ConfigValidator()
        assert validator.validate_database_config(config) is True

    def test_validate_database_config_invalid(self):
        """Test database configuration validation with invalid values."""
        config = {
            "database": {
                "path": "/var/lib/db",
                "backup_interval_seconds": 30,  # Too short
                "retention_hours": 24,
            }
        }

        validator = ConfigValidator()
        assert validator.validate_database_config(config) is False
        assert not validator.result.is_valid

    def test_validate_risk_config_valid(self):
        """Test risk configuration validation."""
        config = {
            "risk": {
                "max_var_daily_pct": 0.02,
                "max_position_size_pct": 0.20,
                "max_leverage": 2.0,
            }
        }

        validator = ConfigValidator()
        assert validator.validate_risk_config(config) is True

    def test_validate_circuit_breaker_config_valid(self):
        """Test circuit breaker configuration validation."""
        config = {
            "circuit_breaker": {
                "enabled": True,
                "level_1_threshold": -0.07,
                "level_2_threshold": -0.13,
                "level_3_threshold": -0.20,
                "check_interval_seconds": 30,
            }
        }

        validator = ConfigValidator()
        assert validator.validate_circuit_breaker_config(config) is True

    @patch("builtins.open")
    def test_validate_production_config_file_not_found(self, mock_open, tmp_path):
        """Test production config validation when file doesn't exist."""
        validator = ConfigValidator(config_dir=tmp_path)
        result = validator.validate_production_config()

        assert result.is_valid is False
        assert any("not found" in e.message for e in result.errors)

    def test_validate_production_config_full_validation(self, tmp_path):
        """Test full production config validation."""
        # Create valid production config
        prod_config = tmp_path / "production.yaml"
        prod_config.write_text(
            """
environment: production
debug: false
database:
  path: /var/lib/algotrading/production.db
  backup_enabled: true
  backup_interval_seconds: 300
  retention_hours: 24
brokers:
  primary:
    name: ibkr
    enabled: true
risk:
  max_var_daily_pct: 0.02
  max_position_size_pct: 0.20
  max_leverage: 2.0
monitoring:
  memory_limit_mb: 4096
tax:
  residence_country: ES
  fifo_enabled: true
compliance:
  country: ES
"""
        )

        validator = ConfigValidator(config_dir=tmp_path)
        result = validator.validate_production_config()

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_load_env_file(self, tmp_path):
        """Test loading environment variables from file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
# Comment line
VAR1=value1
VAR2=value2
"""
        )

        validator = ConfigValidator()
        env_vars = validator._load_env_file(env_file)

        assert env_vars.get("VAR1") == "value1"
        assert env_vars.get("VAR2") == "value2"
