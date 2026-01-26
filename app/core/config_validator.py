"""
Configuration Validator Module
Phase 4.2: Production Config Management

This module provides validation for YAML configuration files and environment
variables to ensure production readiness.
"""

import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field, field_validator, ValidationError

logger = logging.getLogger(__name__)


class ValidationErrorDetail(BaseModel):
    """Detailed validation error information."""

    field: str = Field(description="Field name that failed validation")
    message: str = Field(description="Error message")
    severity: str = Field(
        default="error", description="Severity level: error, warning, or info"
    )


class ValidationResult(BaseModel):
    """Result of configuration validation."""

    is_valid: bool = Field(default=True, description="Whether configuration is valid")
    errors: List[ValidationErrorDetail] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: List[ValidationErrorDetail] = Field(
        default_factory=list, description="List of validation warnings"
    )

    model_config = {"validate_default": False}

    def add_error(self, field: str, message: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(
            ValidationErrorDetail(field=field, message=message, severity="error")
        )
        self.is_valid = False

    def add_warning(self, field: str, message: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(
            ValidationErrorDetail(field=field, message=message, severity="warning")
        )

    def print_summary(self) -> None:
        """Print validation summary to console."""
        if self.is_valid and not self.warnings:
            logger.info("Configuration validation passed: All checks OK")
            return

        if self.errors:
            logger.error(f"Configuration validation failed with {len(self.errors)} error(s)")
            for error in self.errors:
                logger.error(f"  [{error.field}] {error.message}")

        if self.warnings:
            logger.warning(f"Configuration validation has {len(self.warnings)} warning(s)")
            for warning in self.warnings:
                logger.warning(f"  [{warning.field}] {warning.message}")


class DatabaseConfigValidator(BaseModel):
    """Database configuration validation rules."""

    path: str = Field(description="Database path")
    backup_enabled: bool = Field(default=True)
    backup_interval_seconds: int = Field(default=300)
    backup_dir: Optional[str] = Field(default=None)
    retention_hours: int = Field(default=24)

    @field_validator("backup_interval_seconds")
    @classmethod
    def validate_backup_interval(cls, v: int) -> int:
        if v < 60:
            raise ValueError("Backup interval must be at least 60 seconds")
        if v > 3600:
            raise ValueError("Backup interval should not exceed 3600 seconds (1 hour)")
        return v

    @field_validator("retention_hours")
    @classmethod
    def validate_retention(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Retention must be at least 1 hour")
        if v > 168:  # 1 week
            raise ValueError("Retention should not exceed 168 hours (1 week)")
        return v


class RiskConfigValidator(BaseModel):
    """Risk management configuration validation rules."""

    max_var_daily_pct: float = Field(description="Maximum daily VaR percentage")
    max_position_size_pct: float = Field(description="Maximum position size percentage")
    max_leverage: float = Field(description="Maximum leverage")
    use_real_correlation: bool = Field(default=True)

    @field_validator("max_var_daily_pct", "max_position_size_pct")
    @classmethod
    def validate_percentages(cls, v: float) -> float:
        if not 0 < v <= 1:
            raise ValueError("Percentage values must be between 0 and 1")
        return v

    @field_validator("max_leverage")
    @classmethod
    def validate_leverage(cls, v: float) -> float:
        if v < 1:
            raise ValueError("Leverage must be at least 1.0")
        if v > 10:  # Conservative limit
            raise ValueError("Leverage should not exceed 10.0")
        return v


class CircuitBreakerValidator(BaseModel):
    """Circuit breaker configuration validation rules."""

    enabled: bool = Field(default=True)
    level_1_threshold: float = Field(description="Level 1 threshold")
    level_2_threshold: float = Field(description="Level 2 threshold")
    level_3_threshold: float = Field(description="Level 3 threshold")
    check_interval_seconds: int = Field(default=30)

    @field_validator("level_1_threshold", "level_2_threshold", "level_3_threshold")
    @classmethod
    def validate_thresholds(cls, v: float) -> float:
        if not -1.0 <= v <= 0:
            raise ValueError("Thresholds must be between -1.0 and 0")
        return v


class ConfigValidator:
    """
    Main configuration validator class.

    Validates YAML configuration files and environment-specific settings.
    """

    # Placeholders that should not be in production config
    PLACEHOLDER_PATTERNS = [
        r"your_.*_here",
        r"CHANGE.*THIS",
        r"https://example\.com",
        r"http://example\.com",
        r"12345678901234567890123456789012",  # Default secret key
    ]

    # Required sections for production config
    REQUIRED_SECTIONS = [
        "environment",
        "database",
        "brokers",
        "risk",
        "monitoring",
        "tax",
        "compliance",
    ]

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the configuration validator.

        Args:
            config_dir: Directory containing configuration files. Defaults to config/
        """
        self.config_dir = config_dir or Path("config")
        self.result = ValidationResult(is_valid=True)

    def validate_yaml_syntax(self, file_path: Path) -> bool:
        """
        Validate YAML file syntax.

        Args:
            file_path: Path to YAML file

        Returns:
            True if valid, False otherwise
        """
        try:
            with open(file_path, "r") as f:
                yaml.safe_load(f)
            return True
        except yaml.YAMLError as e:
            self.result.add_error("yaml_syntax", f"Invalid YAML in {file_path.name}: {e}")
            self.result.is_valid = False
            return False
        except Exception as e:
            self.result.add_error("file_access", f"Cannot read {file_path.name}: {e}")
            self.result.is_valid = False
            return False

    def validate_environment_value(self, config: Dict[str, Any]) -> bool:
        """
        Validate environment configuration value.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        environment = config.get("environment")

        if not environment:
            self.result.add_error("environment", "Environment field is missing")
            return False

        valid_environments = ["development", "testing", "staging", "production"]
        if environment not in valid_environments:
            self.result.add_error(
                "environment",
                f"Invalid environment: {environment}. Must be one of {valid_environments}",
            )
            return False

        return True

    def validate_debug_mode(self, config: Dict[str, Any]) -> bool:
        """
        Validate debug mode setting for environment.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        debug = config.get("debug", True)
        environment = config.get("environment")

        if environment == "production" and debug:
            self.result.add_error("debug", "Debug mode must be disabled in production")
            return False

        return True

    def validate_required_sections(self, config: Dict[str, Any]) -> bool:
        """
        Validate that required sections exist in configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if all sections present, False otherwise
        """
        missing_sections = []

        for section in self.REQUIRED_SECTIONS:
            if section not in config:
                missing_sections.append(section)

        if missing_sections:
            self.result.add_error(
                "sections", f"Missing required sections: {', '.join(missing_sections)}"
            )
            return False

        return True

    def validate_placeholders(self, config: Dict[str, Any]) -> bool:
        """
        Check for placeholder values that should be replaced.

        Args:
            config: Configuration dictionary

        Returns:
            True if no placeholders found, False otherwise
        """
        found_placeholders = []

        def check_dict(d: Dict[str, Any], prefix: str = "") -> None:
            """Recursively check dictionary for placeholders."""
            for key, value in d.items():
                full_key = f"{prefix}.{key}" if prefix else key

                if isinstance(value, dict):
                    check_dict(value, full_key)
                elif isinstance(value, str):
                    for pattern in self.PLACEHOLDER_PATTERNS:
                        if re.search(pattern, value, re.IGNORECASE):
                            found_placeholders.append(full_key)
                            break

        check_dict(config)

        if found_placeholders:
            self.result.add_warning(
                "placeholders",
                f"Found placeholder values in: {', '.join(found_placeholders[:5])}",
            )
            # Don't mark as invalid, just warn - placeholders are warnings not errors
            return False

        return True

    def validate_environment_variables(
        self, config: Dict[str, Any], env_file: Optional[Path] = None
    ) -> bool:
        """
        Validate that referenced environment variables are defined.

        Args:
            config: Configuration dictionary
            env_file: Path to .env file to check

        Returns:
            True if all variables defined, False otherwise
        """
        # Extract environment variable references
        env_refs = self._extract_env_references(config)

        if not env_refs:
            return True

        # Load environment variables from file if provided
        env_vars = {}
        if env_file and env_file.exists():
            env_vars = self._load_env_file(env_file)

        # Also check system environment
        missing_vars = []
        for var_ref in env_refs:
            var_name = var_ref[2:-1]  # Remove ${ and }
            if var_name not in env_vars and var_name not in os.environ:
                missing_vars.append(var_name)

        if missing_vars:
            self.result.add_warning(
                "environment_variables",
                f"Environment variables not defined: {', '.join(missing_vars)}",
            )
            return False

        return True

    def validate_database_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate database configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        if "database" not in config:
            return True

        try:
            DatabaseConfigValidator(**config["database"])
            return True
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                self.result.add_error(f"database.{field}", error["msg"])
            return False

    def validate_risk_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate risk management configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        if "risk" not in config:
            return True

        try:
            RiskConfigValidator(**config["risk"])
            return True
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                self.result.add_error(f"risk.{field}", error["msg"])
            return False

    def validate_circuit_breaker_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate circuit breaker configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        if "circuit_breaker" not in config:
            return True

        try:
            CircuitBreakerValidator(**config["circuit_breaker"])
            return True
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                self.result.add_error(f"circuit_breaker.{field}", error["msg"])
            return False

    def validate_production_config(
        self, env_file: Optional[Path] = None
    ) -> ValidationResult:
        """
        Validate production configuration file.

        Args:
            env_file: Path to .env.prod file to validate against

        Returns:
            ValidationResult with details
        """
        self.result = ValidationResult(is_valid=True)

        prod_config_path = self.config_dir / "production.yaml"

        if not prod_config_path.exists():
            self.result.add_error("file", "Production configuration file not found")
            return self.result

        # Validate YAML syntax
        if not self.validate_yaml_syntax(prod_config_path):
            return self.result

        # Load configuration
        try:
            with open(prod_config_path, "r") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            self.result.add_error("load", f"Failed to load configuration: {e}")
            return self.result

        # Validate environment
        if not self.validate_environment_value(config):
            return self.result

        # For production, ensure environment is correct
        if config.get("environment") != "production":
            self.result.add_error(
                "environment",
                f"Expected environment 'production', got '{config.get('environment')}'",
            )

        # Validate debug mode
        self.validate_debug_mode(config)

        # Validate required sections
        self.validate_required_sections(config)

        # Validate no placeholders
        self.validate_placeholders(config)

        # Validate environment variables
        self.validate_environment_variables(config, env_file)

        # Validate database configuration
        self.validate_database_config(config)

        # Validate risk configuration
        self.validate_risk_config(config)

        # Validate circuit breaker configuration
        self.validate_circuit_breaker_config(config)

        return self.result

    def _extract_env_references(self, config: Any) -> List[str]:
        """Extract environment variable references from configuration."""
        refs = []

        def extract(value):
            if isinstance(value, dict):
                for v in value.values():
                    extract(v)
            elif isinstance(value, list):
                for item in value:
                    extract(item)
            elif isinstance(value, str):
                if value.startswith("${") and value.endswith("}"):
                    refs.append(value)

        extract(config)
        return refs

    def _load_env_file(self, env_file: Path) -> Dict[str, str]:
        """Load environment variables from file."""
        env_vars = {}
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            logger.warning(f"Failed to load environment file {env_file}: {e}")

        return env_vars


def main():
    """Command-line interface for configuration validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate AlgoTrading configuration")
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path("config"),
        help="Configuration directory",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env.prod"),
        help="Environment file to validate against",
    )
    parser.add_argument(
        "--environment",
        choices=["production", "staging", "development"],
        default="production",
        help="Environment to validate",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    validator = ConfigValidator(config_dir=args.config_dir)

    if args.environment == "production":
        result = validator.validate_production_config(env_file=args.env_file)
    else:
        logger.error(f"Validation for {args.environment} not implemented")
        sys.exit(1)

    result.print_summary()

    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()
