"""
Configuration File Loaders

Implements FileConfigLoader protocol with YAML and JSON loaders.
Each loader has a single responsibility: loading a specific format.

TASK-24: SRP Compliance - Separate loaders for different formats
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

    from app.shared.config.protocols import FileConfigLoader

logger = logging.getLogger(__name__)


class YAMLConfigLoader:
    """YAML configuration file loader."""

    def load(self, config_path: Path) -> dict[str, Any]:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Dictionary containing configuration data

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML is invalid
        """
        logger.debug(f"Loading configuration from YAML: {config_path}")

        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                logger.info(
                    f"Successfully loaded configuration from {config_path}",
                    extra={"config_path": str(config_path)},
                )
                return config_data if config_data is not None else {}
        except yaml.YAMLError as e:
            logger.error(
                f"Invalid YAML in {config_path}: {e}",
                extra={"config_path": str(config_path), "error": str(e)},
            )
            raise ValueError(f"Invalid YAML in {config_path}: {e}") from e

    def supports(self, file_extension: str) -> bool:
        """Check if loader supports YAML files."""
        return file_extension.lower() in [".yaml", ".yml"]


class JSONConfigLoader:
    """JSON configuration file loader."""

    def load(self, config_path: Path) -> dict[str, Any]:
        """
        Load configuration from JSON file.

        Args:
            config_path: Path to JSON configuration file

        Returns:
            Dictionary containing configuration data

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If JSON is invalid
        """
        logger.debug(f"Loading configuration from JSON: {config_path}")

        if not config_path.exists():
            logger.error(f"Configuration file not found: {config_path}")
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path) as f:
                config_data = json.load(f)
                logger.info(
                    f"Successfully loaded configuration from {config_path}",
                    extra={"config_path": str(config_path)},
                )
                return config_data if config_data is not None else {}
        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in {config_path}: {e}",
                extra={"config_path": str(config_path), "error": str(e)},
            )
            raise ValueError(f"Invalid JSON in {config_path}: {e}") from e

    def supports(self, file_extension: str) -> bool:
        """Check if loader supports JSON files."""
        return file_extension.lower() == ".json"


class ConfigLoaderRegistry:
    """
    Registry for configuration loaders.
    Implements automatic loader selection based on file extension.
    """

    def __init__(self):
        self._loaders: list = []
        self._register_default_loaders()

    def _register_default_loaders(self) -> None:
        """Register default loaders."""
        self.register(YAMLConfigLoader())
        self.register(JSONConfigLoader())

    def register(self, loader: FileConfigLoader) -> None:
        """Register a configuration loader."""
        self._loaders.append(loader)

    def get_loader(self, file_extension: str) -> FileConfigLoader | None:
        """Get appropriate loader for file extension."""
        for loader in self._loaders:
            if loader.supports(file_extension):
                return loader
        return None

    def load(self, config_path: Path) -> dict[str, Any]:
        """
        Load configuration using appropriate loader.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary

        Raises:
            ValueError: If no loader supports the file extension
        """
        loader = self.get_loader(config_path.suffix)
        if loader is None:
            raise ValueError(f"Unsupported config file type: {config_path.suffix}")
        return dict(loader.load(config_path))
