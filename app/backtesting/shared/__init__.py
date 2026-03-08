"""
Shared utilities for backtesting module.

This module consolidates duplicated code from across the backtesting package:

- metrics.py: Eliminates 6+ implementations of _get_empty_metrics
- parameter_mapper.py: Eliminates 4+ implementations of parameter mapping
- temp_config.py: Eliminates 8+ implementations of temp file creation
- types.py: Consolidates type aliases from 4+ files

Usage:
    from app.backtesting.shared import (
        MetricsFactory,
        get_empty_metrics,
        ParameterMappingService,
        map_params_to_config,
        TempConfigManager,
        temp_config_file,
        ConfigDict,
        MetricsDict,
    )

    # Get empty metrics
    metrics = get_empty_metrics()

    # Map optimization params to config
    config = map_params_to_config(params, base_config)

    # Use temp config with automatic cleanup
    with temp_config_file(config, output_dir) as temp_path:
        runner = ComprehensiveBacktestRunner(str(temp_path))
        results = runner.run_baseline_backtest()
"""

from app.backtesting.shared.metrics import MetricsFactory, get_empty_metrics
from app.backtesting.shared.parameter_mapper import ParameterMappingService, map_params_to_config
from app.backtesting.shared.temp_config import (
    TempConfigFactory,
    TempConfigManager,
    cleanup_orphaned_temp_files,
    temp_config_file,
)
from app.backtesting.shared.types import (
    ConfigDict,
    ConfigKeys,
    MetricKeys,
    MetricsDict,
    ParameterDict,
)

__all__ = [
    # Metrics
    "MetricsFactory",
    "get_empty_metrics",
    # Parameter mapping
    "ParameterMappingService",
    "map_params_to_config",
    # Temp config
    "TempConfigManager",
    "TempConfigFactory",
    "temp_config_file",
    "cleanup_orphaned_temp_files",
    # Types
    "ConfigDict",
    "ConfigKeys",
    "MetricKeys",
    "MetricsDict",
    "ParameterDict",
]
