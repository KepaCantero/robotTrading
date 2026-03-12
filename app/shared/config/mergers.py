"""
Configuration Mergers

Implements ConfigMerger protocol with recursive merging logic.
Single responsibility: merge configuration dictionaries.

TASK-24: SRP Compliance - Separate merger logic
"""

import logging
from copy import deepcopy
from typing import Any, Dict


logger = logging.getLogger(__name__)


class RecursiveConfigMerger:
    """
    Recursively merges configuration dictionaries.
    Handles nested structures and preserves base values when not overridden.
    """

    def merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries recursively.

        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary

        Returns:
            Merged configuration dictionary

        Example:
            >>> base = {'level1': {'key1': 'value1'}}
            >>> override = {'level1': {'key2': 'value2'}}
            >>> merged = merger.merge(base, override)
            >>> merged['level1']['key1']
            'value1'
            >>> merged['level1']['key2']
            'value2'
        """
        result = deepcopy(base)

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                # Recursively merge nested dictionaries
                result[key] = self.merge(result[key], value)
            else:
                # Override value
                result[key] = deepcopy(value)

        logger.debug(
            "Merged configurations",
            extra={"base_keys": list(base.keys()), "override_keys": list(override.keys())},
        )

        return result


class ReplaceConfigMerger:
    """
    Simple replace merger that completely replaces sections.
    Does not perform recursive merging.
    """

    def merge(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge by replacing base sections with override sections.

        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary

        Returns:
            Merged configuration dictionary
        """
        result = deepcopy(base)
        result.update(deepcopy(override))

        logger.debug(
            "Replaced configuration sections",
            extra={"base_keys": list(base.keys()), "override_keys": list(override.keys())},
        )

        return result
