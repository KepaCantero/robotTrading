"""
Profile Batch Backtesting Services

This package contains service classes extracted from ProfileBatchBacktester
following the Single Responsibility Principle.

Services:
- ConfigurationService: Load and validate configurations
- ProfileGenerationService: Generate profile combinations
- BatchExecutionService: Execute batch tests (parallel/sequential)
- DatabaseService: Store and query results
- MetricsCalculationService: Calculate improvements and comparisons
- FallbackTracker: Track fallback metrics thread-safely
- ReportGenerationService: Generate HTML reports and exports
- models: Data models for database and in-memory results
"""

from __future__ import annotations

from app.backtesting.services.batch_execution_service import BatchExecutionService
from app.backtesting.services.configuration_service import ConfigurationService
from app.backtesting.services.database_service import DatabaseService
from app.backtesting.services.fallback_tracker import FallbackTracker
from app.backtesting.services.metrics_service import MetricsCalculationService
from app.backtesting.services.models import (
    BaselineOptimizationComparison,
    OptimizedStrategy,
    ProfileResult,
    ProfileResultDB,
)
from app.backtesting.services.profile_generation_service import (
    ProfileGenerationService,
)
from app.backtesting.services.report_generation_service import (
    ReportGenerationService,
)

__all__ = [
    "ConfigurationService",
    "ProfileGenerationService",
    "BatchExecutionService",
    "DatabaseService",
    "MetricsCalculationService",
    "FallbackTracker",
    "ReportGenerationService",
    "BaselineOptimizationComparison",
    "OptimizedStrategy",
    "ProfileResult",
    "ProfileResultDB",
]
