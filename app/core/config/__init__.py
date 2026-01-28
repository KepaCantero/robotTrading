"""
Core Configuration Module

This module provides centralized configuration management for the entire application.
"""

import sys
from pathlib import Path

# Import from sibling config.py file (not the config directory)
config_py_path = Path(__file__).parent.parent / "config.py"
if config_py_path.exists():
    # Import the config.py module (not the config directory)
    import importlib.util

    spec = importlib.util.spec_from_file_location("app.core.config_module", config_py_path)
    config_module = importlib.util.module_from_spec(spec)
    sys.modules["app.core.config_module"] = config_module
    spec.loader.exec_module(config_module)

    # Export get_settings, Settings, and helper functions from config.py
    get_settings = config_module.get_settings
    Settings = config_module.Settings
    get_database_url = config_module.get_database_url
    get_redis_url = config_module.get_redis_url

from .profile_config_loader import (
    ProfileConfigLoader,
    clear_loader_cache,
    get_common_params,
    get_model_params,
    get_profile_config_loader,
    get_rl_config,
    get_threshold_ranges,
)

__all__ = [
    "ProfileConfigLoader",
    "get_profile_config_loader",
    "get_common_params",
    "get_model_params",
    "get_threshold_ranges",
    "get_rl_config",
    "clear_loader_cache",
    "get_settings",
    "Settings",
    "get_database_url",
    "get_redis_url",
]
