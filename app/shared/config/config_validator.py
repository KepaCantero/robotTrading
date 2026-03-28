"""
Configuration Validator Module
Phase 4.2: Production Config Management

This module provides validation for YAML configuration files and environment
variables to ensure production readiness.

Classes:
    ProfileOptimizationConfigValidator: Validates profile_optimization.yaml
    BatchBacktestConfigValidator: Validates profile_batch_backtest.yaml
    ValidationErrorDetail: Detailed validation error information
    ValidationResult: Result of configuration validation
    DatabaseConfigValidator: Database configuration validation rules
    RiskConfigValidator: Risk management configuration validation rules
    CircuitBreakerValidator: Circuit breaker configuration validation rules
    ConfigValidator: Main configuration validator class

Usage:
    validator = ConfigValidator(config_dir=Path("config"))
    result = validator.validate_production_config()
    result.print_summary()

Example:
    from pathlib import Path
    from app.shared.config.config_validator import ConfigValidator

    validator = ConfigValidator(Path("config"))
    result = validator.validate_batch_backtest_config()
    if result.is_valid:
        print("Configuration is valid")
    else:
        for error in result.errors:
            print(f"Error: {error.field} - {error.message}")
"""

import datetime
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


# ============================================================================
# PROFILE OPTIMIZATION CONFIG VALIDATION
#
# This section contains validators for the profile_optimization.yaml configuration
# file which controls strategy optimization parameters including:
# - Random state for reproducibility
# - Cross-validation settings
# - Threading and parallelization
# - Validation thresholds for backtest results
# ============================================================================


class ProfileOptimizationConfigValidator(BaseModel):
    """
    Validator for profile_optimization.yaml configuration.

    Validates parameter ranges, model configurations, and optimization settings
    for profile-based trading strategy optimization.

    Attributes:
        common_random_state: Random seed for reproducibility
        common_test_size: Fraction of data to use for testing (0-1)
        common_cv_folds: Number of cross-validation folds
        threading_max_workers: Maximum worker threads (None for auto)
        threading_worker_multiplier: Multiplier for CPU count (0-1)
        threading_batch_size: Batch size for parallel processing
        validation_min_sharpe: Minimum acceptable Sharpe ratio
        validation_max_drawdown: Maximum acceptable drawdown (0-1)
        validation_min_win_rate: Minimum acceptable win rate (0-1)
    """

    # Common parameters
    common_random_state: int = Field(default=42)
    common_test_size: float = Field(default=0.2)
    common_cv_folds: int = Field(default=5)

    # Threading
    threading_max_workers: Optional[int] = Field(default=None)
    threading_worker_multiplier: float = Field(default=0.75)
    threading_batch_size: int = Field(default=32)

    # Validation thresholds
    validation_min_sharpe: float = Field(default=0.5)
    validation_max_drawdown: float = Field(default=0.2)
    validation_min_win_rate: float = Field(default=0.45)

    @field_validator("common_test_size")
    @classmethod
    def validate_test_size(cls, v: float) -> float:
        if not 0 < v < 1:
            raise ValueError("test_size must be between 0 and 1")
        return v

    @field_validator("common_cv_folds")
    @classmethod
    def validate_cv_folds(cls, v: int) -> int:
        if v < 2:
            raise ValueError("cv_folds must be at least 2")
        if v > 20:
            raise ValueError("cv_folds should not exceed 20")
        return v

    @field_validator("threading_worker_multiplier")
    @classmethod
    def validate_worker_multiplier(cls, v: float) -> float:
        if not 0 < v <= 1:
            raise ValueError("worker_multiplier must be between 0 and 1")
        return v

    @field_validator("validation_min_sharpe", "validation_min_win_rate")
    @classmethod
    def validate_positive_thresholds(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Threshold values must be non-negative")
        return v

    @field_validator("validation_max_drawdown")
    @classmethod
    def validate_drawdown(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("max_drawdown must be between 0 and 1")
        return v


class BatchBacktestConfigValidator(BaseModel):
    """
    Validator for profile_batch_backtest.yaml configuration.

    Validates workflow settings, database configuration, and profile generation
    parameters for batch backtesting across multiple trading profiles.

    Attributes:
        database_url: Database connection URL (sqlite/postgresql/mysql)
        output_dir: Directory for backtest results
        capital_tiers: Capital tier definitions (micro, small, medium, large)
        investment_horizons: Investment horizon definitions (short, medium, long)
        symbols: List of trading symbols to backtest
        backtest_start_date: Backtest period start (YYYY-MM-DD)
        backtest_end_date: Backtest period end (YYYY-MM-DD)
        optimization_n_trials: Number of optimization trials
        optimization_n_jobs: Number of parallel optimization jobs
        validation_min_sharpe: Minimum Sharpe ratio for valid profiles
        validation_max_drawdown: Maximum drawdown for valid profiles
        parallelization_max_profiles: Maximum profiles to process in parallel
    """

    # Database
    database_url: str = Field(description="Database connection URL")

    # Output
    output_dir: str = Field(default="results/profile_batch_backtesting")

    # Profile generation
    capital_tiers: Dict[str, int] = Field(default_factory=dict)
    investment_horizons: Dict[str, int] = Field(default_factory=dict)

    # Backtest
    symbols: List[str] = Field(default_factory=list)
    backtest_start_date: str = Field(description="Backtest start date (YYYY-MM-DD)")
    backtest_end_date: str = Field(description="Backtest end date (YYYY-MM-DD)")

    # Optimization
    optimization_n_trials: int = Field(default=100)
    optimization_n_jobs: int = Field(default=4)

    # Validation
    validation_min_sharpe: float = Field(default=0.5)
    validation_max_drawdown: float = Field(default=0.2)

    # Parallelization
    parallelization_max_profiles: int = Field(default=20)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """
        Validate database URL format and protocol.

        Ensures the URL is not empty and uses one of the supported
        database protocols: sqlite, postgresql, or mysql.
        """
        if not v or not v.strip():
            raise ValueError("database_url cannot be empty")
        if not any(v.startswith(prefix) for prefix in ["sqlite://", "postgresql://", "mysql://"]):
            raise ValueError(
                "database_url must use a supported protocol (sqlite, postgresql, mysql)"
            )
        return v

    @field_validator("capital_tiers", "investment_horizons")
    @classmethod
    def validate_non_empty_dict(cls, v: Dict[str, object]) -> Dict[str, object]:
        if not v:
            raise ValueError("Must define at least one capital tier or investment horizon")
        return v

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("symbols list cannot be empty")
        if len(v) > 100:
            raise ValueError("symbols list should not exceed 100 symbols")
        return v

    @field_validator("backtest_start_date", "backtest_end_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("optimization_n_trials")
    @classmethod
    def validate_n_trials(cls, v: int) -> int:
        if v < 1:
            raise ValueError("n_trials must be at least 1")
        if v > 10000:
            raise ValueError("n_trials should not exceed 10000")
        return v

    @field_validator("parallelization_max_profiles")
    @classmethod
    def validate_max_profiles(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_profiles must be at least 1")
        if v > 100:
            raise ValueError("max_profiles should not exceed 100")
        return v


class ValidationErrorDetail(BaseModel):
    """
    Detailed validation error information.

    Represents a single validation error or warning with associated metadata.

    Attributes:
        field: The field name or path that failed validation (e.g., 'database.url')
        message: Human-readable error message describing the validation failure
        severity: Error severity level - 'error', 'warning', or 'info'
    """

    field: str = Field(description="Field name that failed validation")
    message: str = Field(description="Error message")
    severity: str = Field(default="error", description="Severity level: error, warning, or info")


class ValidationResult(BaseModel):
    """
    Result of configuration validation.

    Aggregates all validation errors and warnings from a configuration
    validation run. Provides methods to add errors/warnings and print
    a summary of the validation results.

    Attributes:
        is_valid: Whether the overall configuration is valid (no errors)
        errors: List of validation errors that must be fixed
        warnings: List of validation warnings that should be reviewed
    """

    is_valid: bool = Field(default=True, description="Whether configuration is valid")
    errors: List[ValidationErrorDetail] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: List[ValidationErrorDetail] = Field(
        default_factory=list, description="List of validation warnings"
    )

    model_config = {"validate_default": False}

    def add_error(self, field: str, message: str) -> None:
        """
        Add an error to the validation result.

        Errors mark the configuration as invalid and must be fixed
        before the configuration can be used.

        Args:
            field: The field name or path that failed validation
            message: Human-readable description of the error
        """
        self.errors.append(ValidationErrorDetail(field=field, message=message, severity="error"))
        self.is_valid = False

    def add_warning(self, field: str, message: str) -> None:
        """
        Add a warning to the validation result.

        Warnings indicate potential issues that should be reviewed but
        do not prevent the configuration from being used.

        Args:
            field: The field name or path with a potential issue
            message: Human-readable description of the warning
        """
        self.warnings.append(
            ValidationErrorDetail(field=field, message=message, severity="warning")
        )

    def print_summary(self) -> None:
        """
        Print validation summary to console.

        Outputs a formatted summary of all validation errors and warnings
        to the logger. If no errors or warnings exist, prints success message.
        """
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
    """
    Database configuration validation rules.

    Validates database settings including path, backup configuration,
    and retention policies.

    Attributes:
        path: Database file path or connection string
        backup_enabled: Whether automatic backups are enabled
        backup_interval_seconds: Interval between backups in seconds
        backup_dir: Directory for backup files
        retention_hours: How long to keep backups in hours
    """

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
    """
    Risk management configuration validation rules.

    Validates risk management parameters including VaR limits,
    position sizing constraints, and leverage limits.

    Attributes:
        max_var_daily_pct: Maximum daily Value at Risk percentage (0-1)
        max_position_size_pct: Maximum single position size percentage (0-1)
        max_leverage: Maximum allowed leverage (1-10)
        use_real_correlation: Whether to use real correlation matrix
    """

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
    """
    Circuit breaker configuration validation rules.

    Validates circuit breaker thresholds for trading halts.
    All thresholds must be negative values between -1.0 and 0.

    Attributes:
        enabled: Whether circuit breaker is enabled
        level_1_threshold: First level threshold (e.g., -0.05 for 5% drop)
        level_2_threshold: Second level threshold (e.g., -0.10 for 10% drop)
        level_3_threshold: Third level threshold (e.g., -0.20 for 20% drop)
        check_interval_seconds: How often to check thresholds
    """

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

    Validates YAML configuration files and environment-specific settings
    for production readiness and backtesting configurations.

    Attributes:
        PLACEHOLDER_PATTERNS: List of regex patterns for detecting placeholder values
        REQUIRED_SECTIONS: List of required sections in production config
        config_dir: Directory containing configuration files
        result: Current validation result

    Methods:
        validate_yaml_syntax: Validate YAML file syntax
        validate_environment_value: Validate environment configuration value
        validate_debug_mode: Validate debug mode setting for environment
        validate_required_sections: Validate that required sections exist
        validate_placeholders: Check for placeholder values
        validate_environment_variables: Validate referenced environment variables
        validate_database_config: Validate database configuration
        validate_risk_config: Validate risk management configuration
        validate_circuit_breaker_config: Validate circuit breaker configuration
        validate_production_config: Validate production configuration file
        validate_profile_optimization_config: Validate profile_optimization.yaml
        validate_batch_backtest_config: Validate profile_batch_backtest.yaml
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

        Creates a new validator instance pointing to the specified configuration
        directory. If no directory is provided, defaults to 'config/'.

        Args:
            config_dir: Directory containing configuration files.
                            Defaults to 'config' directory in the project root.
        """
        self.config_dir = config_dir or Path("config")
        self.result = ValidationResult(is_valid=True)

    def validate_yaml_syntax(self, file_path: Path) -> bool:
        """
        Validate YAML file syntax.

        Attempts to parse the YAML file and reports any syntax errors.
        This is the first validation step before processing configuration content.

        Args:
            file_path: Path to YAML file to validate

        Returns:
            True if YAML syntax is valid, False otherwise

        Raises:
            No exceptions raised - errors are added to self.result
        """
        try:
            with open(file_path, "r") as f:
                yaml.safe_load(f)
            return True
        except yaml.YAMLError as e:
            self.result.add_error("yaml_syntax", f"Invalid YAML in {file_path.name}: {e}")
            self.result.is_valid = False
            return False
        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            self.result.add_error("file_access", f"Cannot read {file_path.name}: {e}")
            self.result.is_valid = False
            return False

    def validate_environment_value(self, config: Dict[str, object]) -> bool:
        """
        Validate environment configuration value.

        Ensures the environment field is present and contains a valid
        environment name (development, testing, staging, or production).

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if environment value is valid, False otherwise
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

    def validate_debug_mode(self, config: Dict[str, object]) -> bool:
        """
        Validate debug mode setting for environment.

        Ensures debug mode is disabled in production environments.
        Debug mode should only be enabled in development or testing.

        Args:
            config: Configuration dictionary containing 'debug' and 'environment' keys

        Returns:
            True if debug mode setting is valid, False if debug is enabled in production
        """
        debug = config.get("debug", True)
        environment = config.get("environment")

        if environment == "production" and debug:
            self.result.add_error("debug", "Debug mode must be disabled in production")
            return False

        return True

    def validate_required_sections(self, config: Dict[str, object]) -> bool:
        """
        Validate that required sections exist in configuration.

        Checks for the presence of all required configuration sections:
        environment, database, brokers, risk, monitoring, tax, and compliance.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if all required sections are present, False otherwise
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

    def validate_placeholders(self, config: Dict[str, object]) -> bool:
        """
        Check for placeholder values that should be replaced.

        Scans configuration recursively for common placeholder patterns
        like 'your_*_here', 'CHANGE*THIS', and example URLs.
        Placeholders are warnings, not errors, as they may be intentional.

        Args:
            config: Configuration dictionary to scan for placeholders

        Returns:
            True if no placeholders found, False if placeholders detected
        """
        found_placeholders = []

        def check_dict(d: Dict[str, object], prefix: str = "") -> None:
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
        self, config: Dict[str, object], env_file: Optional[Path] = None
    ) -> bool:
        """
        Validate that referenced environment variables are defined.

        Extracts environment variable references (${VAR_NAME}) from the
        configuration and checks if they are defined either in the provided
        env_file or in the system environment.

        Args:
            config: Configuration dictionary to scan for env var references
            env_file: Optional path to .env file to check for definitions

        Returns:
            True if all referenced variables are defined, False otherwise
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

    def validate_database_config(self, config: Dict[str, object]) -> bool:
        """
        Validate database configuration section.

        Validates database path, backup settings, and retention policies
        using the DatabaseConfigValidator pydantic model.

        Args:
            config: Configuration dictionary containing 'database' section

        Returns:
            True if database configuration is valid, False otherwise
        """
        if "database" not in config:
            return True

        try:
            DatabaseConfigValidator(**config["database"])
            return True
        except ValidationError as e:
            self._process_validation_errors(e, "database")
            return False

    def validate_risk_config(self, config: Dict[str, object]) -> bool:
        """
        Validate risk management configuration section.

        Validates VaR limits, position size limits, leverage constraints,
        and correlation settings using the RiskConfigValidator pydantic model.

        Args:
            config: Configuration dictionary containing 'risk' section

        Returns:
            True if risk configuration is valid, False otherwise
        """
        if "risk" not in config:
            return True

        try:
            RiskConfigValidator(**config["risk"])
            return True
        except ValidationError as e:
            self._process_validation_errors(e, "risk")
            return False

    def validate_circuit_breaker_config(self, config: Dict[str, object]) -> bool:
        """
        Validate circuit breaker configuration section.

        Validates the three-level circuit breaker thresholds and check
        interval settings using the CircuitBreakerValidator pydantic model.

        Args:
            config: Configuration dictionary containing 'circuit_breaker' section

        Returns:
            True if circuit breaker configuration is valid, False otherwise
        """
        if "circuit_breaker" not in config:
            return True

        try:
            CircuitBreakerValidator(**config["circuit_breaker"])
            return True
        except ValidationError as e:
            self._process_validation_errors(e, "circuit_breaker")
            return False

    def _process_validation_errors(self, exc: ValidationError, prefix: str) -> None:
        """
        Process and record validation errors from pydantic ValidationError.

        Extracts error details from a pydantic ValidationError and adds them
        to the validation result with the appropriate field prefix.

        Args:
            exc: The ValidationError exception from pydantic validation
            prefix: The prefix to prepend to field names (e.g., 'database', 'risk')
        """
        for error in exc.errors():
            field = ".".join(str(x) for x in error["loc"])
            self.result.add_error(f"{prefix}.{field}", error["msg"])

    def validate_production_config(self, env_file: Optional[Path] = None) -> ValidationResult:
        """
        Validate production configuration file.

        Performs comprehensive validation of production.yaml including:
        - YAML syntax validation
        - Environment value validation (must be 'production')
        - Debug mode validation (must be disabled)
        - Required sections validation
        - Placeholder detection
        - Environment variable references
        - Database, risk, and circuit breaker configuration validation

        Args:
            env_file: Optional path to .env.prod file for env var validation

        Returns:
            ValidationResult containing all validation errors and warnings
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
        except OSError as e:
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

    def _extract_env_references(self, config: Union[Dict[str, object], List[object], str, int, float, bool]) -> List[str]:
        """
        Extract environment variable references from configuration.

        Recursively scans the configuration for values in the format ${VAR_NAME}
        and returns a list of all found references.

        Args:
            config: Configuration value (dict, list, or primitive) to scan

        Returns:
            List of environment variable reference strings (e.g., ['${API_KEY}'])
        """
        refs = []

        def extract(value):
            if isinstance(value, dict):
                for v in value.values():
                    extract(v)
            elif isinstance(value, list):
                for item in value:
                    extract(item)
            elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                refs.append(value)

        extract(config)
        return refs

    def _load_env_file(self, env_file: Path) -> Dict[str, str]:
        """
        Load environment variables from a .env file.

        Parses the file line by line, skipping comments and empty lines,
        and returns a dictionary of key-value pairs.

        Args:
            env_file: Path to the .env file to load

        Returns:
            Dictionary mapping environment variable names to their values
        """
        env_vars = {}
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
        except OSError as e:
            logger.warning(f"Failed to load environment file {env_file}: {e}")

        return env_vars

    # ========================================================================
    # PROFILE OPTIMIZATION CONFIG VALIDATION
    # ========================================================================

    def validate_profile_optimization_config(
        self, config_path: Optional[Path] = None
    ) -> ValidationResult:
        """
        Validate profile_optimization.yaml configuration.

        Validates the profile optimization configuration including:
        - Common parameters (random_state, test_size, cv_folds)
        - Threading settings (max_workers, worker_multiplier, batch_size)
        - Validation thresholds (min_sharpe, max_drawdown, min_win_rate)
        - Threshold optimization ranges
        - Profile and tier-specific overrides

        Args:
            config_path: Path to profile_optimization.yaml file.
                        Defaults to config/backtesting/profile_optimization.yaml

        Returns:
            ValidationResult with validation errors and warnings
        """
        self.result = ValidationResult(is_valid=True)

        config_path = config_path or self.config_dir / "backtesting" / "profile_optimization.yaml"

        if not config_path.exists():
            self.result.add_error("file", f"Configuration file not found: {config_path}")
            return self.result

        # Validate YAML syntax
        if not self.validate_yaml_syntax(config_path):
            return self.result

        # Load configuration
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        except OSError as e:
            self.result.add_error("load", f"Failed to load configuration: {e}")
            return self.result

        # Validate required sections
        required_sections = ["common", "threading", "validation"]
        for section in required_sections:
            if section not in config:
                self.result.add_error("sections", f"Missing required section: {section}")

        # Validate common parameters
        if "common" in config:
            try:
                common = config["common"]
                ProfileOptimizationConfigValidator(
                    common_random_state=common.get("random_state", 42),
                    common_test_size=common.get("test_size", 0.2),
                    common_cv_folds=common.get("cv_folds", 5),
                )
            except ValidationError as e:
                for error in e.errors():
                    field = ".".join(str(x) for x in error["loc"])
                    self.result.add_error(f"common.{field}", error["msg"])

        # Validate threading parameters
        if "threading" in config:
            try:
                threading = config["threading"]
                ProfileOptimizationConfigValidator(
                    threading_max_workers=threading.get("max_workers"),
                    threading_worker_multiplier=threading.get("worker_multiplier", 0.75),
                    threading_batch_size=threading.get("batch_size", 32),
                )
            except ValidationError as e:
                for error in e.errors():
                    field = ".".join(str(x) for x in error["loc"])
                    self.result.add_error(f"threading.{field}", error["msg"])

        # Validate validation thresholds
        if "validation" in config:
            validation = config["validation"]
            if "thresholds" in validation:
                try:
                    thresholds = validation["thresholds"]
                    ProfileOptimizationConfigValidator(
                        validation_min_sharpe=thresholds.get("min_sharpe", 0.5),
                        validation_max_drawdown=thresholds.get("max_drawdown", 0.2),
                        validation_min_win_rate=thresholds.get("min_win_rate", 0.45),
                    )
                except ValidationError as e:
                    for error in e.errors():
                        field = ".".join(str(x) for x in error["loc"])
                        self.result.add_error(f"validation.thresholds.{field}", error["msg"])

        # Validate threshold optimization ranges
        if "threshold_optimization" in config:
            self._validate_threshold_ranges(config["threshold_optimization"])

        # Validate profile and tier overrides
        if "profiles" in config:
            self._validate_profile_overrides(config["profiles"])

        if "tiers" in config:
            self._validate_tier_overrides(config["tiers"])

        return self.result

    def _validate_threshold_ranges(self, threshold_config: Dict[str, object]) -> None:
        """
        Validate threshold optimization ranges.

        Ensures that for each threshold parameter, the min value is less
        than the max value. Adds errors to self.result for invalid ranges.

        Args:
            threshold_config: Dictionary of threshold configurations
                             with min/max range values
        """
        for indicator, params in threshold_config.items():
            if indicator == "optimization":
                continue

            if isinstance(params, dict):
                for param_name, param_range in params.items():
                    if isinstance(param_range, dict):
                        min_val = param_range.get("min")
                        max_val = param_range.get("max")

                        if min_val is not None and max_val is not None and min_val >= max_val:
                            self.result.add_error(
                                f"threshold_optimization.{indicator}.{param_name}",
                                f"min ({min_val}) must be less than max ({max_val})",
                            )

    def _validate_profile_overrides(self, profiles: Dict[str, object]) -> None:
        """
        Validate profile-specific overrides.

        Checks that profile names in the configuration match known valid
        profiles: conservative, balanced, aggressive, income, growth, dividendos.
        Unknown profiles generate warnings.

        Args:
            profiles: Dictionary mapping profile names to their override configurations
        """
        valid_profiles = [
            "conservative",
            "balanced",
            "aggressive",
            "income",
            "growth",
            "dividendos",
        ]

        for profile_name in profiles:
            if profile_name not in valid_profiles:
                self.result.add_warning(
                    "profiles",
                    f"Unknown profile: {profile_name}. Valid profiles: {valid_profiles}",
                )

    def _validate_tier_overrides(self, tiers: Dict[str, object]) -> None:
        """
        Validate tier-specific overrides.

        Checks that tier names in the configuration match known valid
        tiers: micro, small, medium, large. Unknown tiers generate warnings.

        Args:
            tiers: Dictionary mapping tier names to their override configurations
        """
        valid_tiers = ["micro", "small", "medium", "large"]

        for tier_name in tiers:
            if tier_name not in valid_tiers:
                self.result.add_warning(
                    "tiers",
                    f"Unknown tier: {tier_name}. Valid tiers: {valid_tiers}",
                )

    # ========================================================================
    # BATCH BACKTEST CONFIG VALIDATION
    # ========================================================================

    def validate_batch_backtest_config(
        self, config_path: Optional[Path] = None
    ) -> ValidationResult:
        """
        Validate profile_batch_backtest.yaml configuration.

        Performs comprehensive validation of batch backtest configuration including:
        - YAML syntax validation
        - Required sections validation (database, symbols, backtest_period)
        - Database URL validation (sqlite, postgresql, mysql protocols)
        - Capital tiers and investment horizons validation
        - Backtest date range validation
        - Optimization settings validation (n_trials, n_jobs)
        - Parallelization settings validation (max_profiles)
        - Cross-configuration reference validation

        Args:
            config_path: Path to profile_batch_backtest.yaml file.
                        Defaults to config/profile_batch_backtest.yaml

        Returns:
            ValidationResult containing all validation errors and warnings
        """
        self.result = ValidationResult(is_valid=True)

        config_path = config_path or self.config_dir / "profile_batch_backtest.yaml"

        if not config_path.exists():
            self.result.add_error("file", f"Configuration file not found: {config_path}")
            return self.result

        # Validate YAML syntax
        if not self.validate_yaml_syntax(config_path):
            return self.result

        # Load configuration
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        except OSError as e:
            self.result.add_error("load", f"Failed to load configuration: {e}")
            return self.result

        # Validate required sections
        required_sections = ["database", "symbols", "backtest_period"]
        for section in required_sections:
            if section not in config:
                self.result.add_error("sections", f"Missing required section: {section}")

        # Validate database configuration
        if "database" in config:
            database = config["database"]
            try:
                BatchBacktestConfigValidator(
                    database_url=database.get("url", ""),
                    symbols=config.get("symbols", []),
                    backtest_start_date=config.get("backtest_period", {}).get("start_date", ""),
                    backtest_end_date=config.get("backtest_period", {}).get("end_date", ""),
                    capital_tiers=config.get("capital_tiers", {}),
                    investment_horizons=config.get("investment_horizons", {}),
                )
            except ValidationError as e:
                for error in e.errors():
                    field = ".".join(str(x) for x in error["loc"])
                    self.result.add_error(f"{field}", error["msg"])

        # Validate symbols
        if "symbols" not in config:
            self.result.add_error("symbols", "symbols section is required")

        # Validate backtest period
        if "backtest_period" not in config:
            self.result.add_error("backtest_period", "backtest_period section is required")
        else:
            period = config["backtest_period"]
            if "start_date" not in period:
                self.result.add_error("backtest_period.start_date", "start_date is required")
            if "end_date" not in period:
                self.result.add_error("backtest_period.end_date", "end_date is required")

        # Validate capital tiers
        if "capital_tiers" not in config:
            self.result.add_error("capital_tiers", "capital_tiers section is required")

        # Validate investment horizons
        if "investment_horizons" not in config:
            self.result.add_error("investment_horizons", "investment_horizons section is required")

        # Validate optimization settings
        if "optimization" in config:
            opt = config["optimization"]
            try:
                BatchBacktestConfigValidator(
                    database_url=config.get("database", {}).get("url", ""),
                    symbols=config.get("symbols", []),
                    backtest_start_date=config.get("backtest_period", {}).get("start_date", ""),
                    backtest_end_date=config.get("backtest_period", {}).get("end_date", ""),
                    capital_tiers=config.get("capital_tiers", {}),
                    investment_horizons=config.get("investment_horizons", {}),
                    optimization_n_trials=opt.get("n_trials", 100),
                    optimization_n_jobs=opt.get("n_jobs", 4),
                )
            except ValidationError as e:
                for error in e.errors():
                    field = ".".join(str(x) for x in error["loc"])
                    # Only add optimization-related errors
                    if "optimization" in str(field):
                        self.result.add_error(f"{field}", error["msg"])

        # Validate parallelization
        if "parallelization" in config:
            parallel = config["parallelization"]
            try:
                BatchBacktestConfigValidator(
                    database_url=config.get("database", {}).get("url", ""),
                    symbols=config.get("symbols", []),
                    backtest_start_date=config.get("backtest_period", {}).get("start_date", ""),
                    backtest_end_date=config.get("backtest_period", {}).get("end_date", ""),
                    capital_tiers=config.get("capital_tiers", {}),
                    investment_horizons=config.get("investment_horizons", {}),
                    parallelization_max_profiles=parallel.get("max_profiles", 20),
                )
            except ValidationError as e:
                for error in e.errors():
                    field = ".".join(str(x) for x in error["loc"])
                    # Only add parallelization-related errors
                    if "parallelization" in str(field):
                        self.result.add_error(f"{field}", error["msg"])

        # Check for cross-config references
        self._validate_cross_config_references(config)

        return self.result

    def _validate_cross_config_references(self, batch_config: Dict[str, object]) -> None:
        """
        Validate that references to profile_optimization.yaml are valid.

        Checks for cross-configuration consistency including:
        - Module enable flags that reference non-existent filter modules
        - Known filters: momentum, ema, rsi, volume, atr, stoch_rsi

        Args:
            batch_config: Batch backtest configuration dictionary to validate
        """
        # Check enabled modules against known modules
        if "modules" in batch_config:
            modules = batch_config["modules"]
            known_filters = ["momentum", "ema", "rsi", "volume", "atr", "stoch_rsi"]

            if "filters" in modules:
                for filter_name in modules["filters"]:
                    if filter_name not in known_filters:
                        self.result.add_warning(
                            "modules.filters",
                            f"Unknown filter: {filter_name}. Known filters: {known_filters}",
                        )


def main():
    """
    Command-line interface for configuration validation.

    Provides CLI access to validate various configuration files:
    - Production configuration (production.yaml)
    - Batch backtest configuration (profile_batch_backtest.yaml)
    - Profile optimization configuration (profile_optimization.yaml)

    Exit codes:
        0: Validation passed
        1: Validation failed or error occurred

    Example usage:
        python -m app.shared.config.config_validator --environment production
        python -m app.shared.config.config_validator --batch-config
        python -m app.shared.config.config_validator --all-backtesting
    """
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
        default=None,
        help="Environment to validate (use --batch-config or --profile-optimization for backtesting configs)",
    )
    parser.add_argument(
        "--batch-config",
        action="store_true",
        help="Validate profile_batch_backtest.yaml configuration",
    )
    parser.add_argument(
        "--profile-optimization",
        action="store_true",
        help="Validate profile_optimization.yaml configuration",
    )
    parser.add_argument(
        "--all-backtesting",
        action="store_true",
        help="Validate all backtesting configs (profile_batch_backtest.yaml and profile_optimization.yaml)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    validator = ConfigValidator(config_dir=args.config_dir)

    # Route to appropriate validation
    if args.batch_config:
        result = validator.validate_batch_backtest_config()
        result.print_summary()
        sys.exit(0 if result.is_valid else 1)

    elif args.profile_optimization:
        result = validator.validate_profile_optimization_config()
        result.print_summary()
        sys.exit(0 if result.is_valid else 1)

    elif args.all_backtesting:
        logger.info("Validating all backtesting configurations...")
        batch_result = validator.validate_batch_backtest_config()
        profile_result = validator.validate_profile_optimization_config()

        logger.info("\n=== Batch Backtest Config ===")
        batch_result.print_summary()

        logger.info("\n=== Profile Optimization Config ===")
        profile_result.print_summary()

        overall_valid = batch_result.is_valid and profile_result.is_valid
        if overall_valid:
            logger.info("\nAll backtesting configurations are valid!")
        else:
            logger.error("\nSome backtesting configurations have errors")

        sys.exit(0 if overall_valid else 1)

    elif args.environment:
        if args.environment == "production":
            result = validator.validate_production_config(env_file=args.env_file)
        else:
            logger.error(f"Validation for {args.environment} not implemented")
            sys.exit(1)

        result.print_summary()
        sys.exit(0 if result.is_valid else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
