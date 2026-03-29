"""
Temp Config Manager - Context manager for temporary YAML config files.

Eliminates 8+ duplicate implementations across:
- profile_batch_backtester.py (2 implementations)
- bayesian_optimizer.py
- baseline_executor.py
- optimization_validators.py (3 implementations)
- And more...

Provides automatic cleanup with context manager pattern.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import yaml

logger = logging.getLogger(__name__)


class TempConfigManager:
    """
    Manages temporary YAML configuration files with automatic cleanup.

    Usage:
        with TempConfigManager(config, output_dir) as temp_path:
            runner = ComprehensiveBacktestRunner(str(temp_path))
            results = runner.run_baseline_backtest()
        # File automatically deleted after context exits
    """

    def __init__(
        self,
        config: dict[str, Any],
        output_dir: Path,
        prefix: str = "temp",
        suffix: str = ".yaml",
    ):
        """
        Initialize temp config manager.

        Args:
            config: Configuration dict to write to temp file
            output_dir: Directory for temp files
            prefix: Filename prefix (default: "temp")
            suffix: Filename suffix (default: ".yaml")
        """
        self.config = config
        self.output_dir = Path(output_dir)
        self.prefix = prefix
        self.suffix = suffix
        self.temp_path: Optional[Path] = None

    def __enter__(self) -> Path:
        """Create temp file and return path."""
        self.temp_path = self._create_temp_file()
        return self.temp_path

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up temp file."""
        self._cleanup()

    def _create_temp_file(self) -> Path:
        """Create temporary YAML config file."""
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        unique_id = uuid4().hex[:8]
        filename = f"{self.prefix}_{unique_id}{self.suffix}"
        temp_path = self.output_dir / filename

        # Write config
        with open(temp_path, "w") as f:
            yaml.dump(self.config, f)

        logger.debug(f"Created temp config: {temp_path}")
        return temp_path

    def _cleanup(self) -> None:
        """Remove temporary file if it exists."""
        if self.temp_path and self.temp_path.exists():
            try:
                self.temp_path.unlink()
                logger.debug(f"Cleaned up temp config: {self.temp_path}")
            except OSError as e:
                logger.warning(f"Failed to cleanup temp config {self.temp_path}: {e}")
        self.temp_path = None


@contextmanager
def temp_config_file(
    config: dict[str, Any],
    output_dir: Path,
    prefix: str = "temp",
) -> Generator[Path, None, None]:
    """
    Context manager for temporary YAML config files.

    Convenience function that wraps TempConfigManager.

    Args:
        config: Configuration dict to write
        output_dir: Directory for temp files
        prefix: Filename prefix

    Yields:
        Path to temporary config file

    Example:
        with temp_config_file(updated_config, output_dir) as temp_path:
            runner = ComprehensiveBacktestRunner(str(temp_path))
            results = runner.run_baseline_backtest()
    """
    manager = TempConfigManager(config, output_dir, prefix=prefix)
    with manager:
        yield manager


class TempConfigFactory:
    """
    Factory for creating common temp config variations.

    Provides factory methods for different use cases to ensure
    consistent naming and handling.
    """

    def __init__(self, output_dir: Path):
        """
        Initialize factory.

        Args:
            output_dir: Base directory for temp files
        """
        self.output_dir = Path(output_dir)

    def create_backtest_config(
        self, config: dict[str, Any], profile_id: Optional[str] = None
    ) -> TempConfigManager:
        """
        Create temp config for backtest execution.

        Args:
            config: Configuration dict
            profile_id: Optional profile ID for naming

        Returns:
            TempConfigManager instance
        """
        prefix = f"temp_{profile_id[:8]}" if profile_id else "temp_backtest"
        return TempConfigManager(config, self.output_dir, prefix=prefix)

    def create_optimization_config(
        self, config: dict[str, Any], trial_num: Optional[int] = None
    ) -> TempConfigManager:
        """
        Create temp config for optimization trial.

        Args:
            config: Configuration dict
            trial_num: Optional trial number for naming

        Returns:
            TempConfigManager instance
        """
        prefix = f"temp_opt_{trial_num}" if trial_num is not None else "temp_opt"
        return TempConfigManager(config, self.output_dir, prefix=prefix)

    def create_validation_config(
        self, config: dict[str, Any], validation_type: str
    ) -> TempConfigManager:
        """
        Create temp config for validation (walk-forward, monte-carlo, etc).

        Args:
            config: Configuration dict
            validation_type: Type of validation (wf, mc, oos)

        Returns:
            TempConfigManager instance
        """
        return TempConfigManager(config, self.output_dir, prefix=f"temp_{validation_type}")


def cleanup_orphaned_temp_files(output_dir: Path, prefix: str = "temp_") -> int:
    """
    Clean up orphaned temp files left from previous crashes.

    Should be called on application startup to clean up any
    temp files that weren't properly deleted.

    Args:
        output_dir: Directory to search for temp files
        prefix: File prefix to match

    Returns:
        Number of files deleted
    """
    output_dir = Path(output_dir)
    if not output_dir.exists():
        return 0

    deleted = 0
    for temp_file in output_dir.glob(f"{prefix}*.yaml"):
        try:
            temp_file.unlink()
            deleted += 1
            logger.debug(f"Cleaned up orphaned temp file: {temp_file}")
        except OSError as e:
            logger.warning(f"Failed to delete {temp_file}: {e}")

    if deleted > 0:
        logger.info(f"Cleaned up {deleted} orphaned temp files from {output_dir}")

    return deleted
