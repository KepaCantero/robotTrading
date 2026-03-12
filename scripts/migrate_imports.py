#!/usr/bin/env python3
"""
Import Migration Script for AlgoTrading Reorganization

This script automatically updates import statements when moving directories
from the old structure to the new Clean Architecture structure.

Usage:
    python scripts/migrate_imports.py [--dry-run] [--verbose]

The script will:
1. Find all Python files in the project
2. Update imports according to the mapping
3. Show a summary of changes

Mapping:
    app.strategies → app.domain.strategies
    app.models → app.domain.models
    app.api → app.presentation.api
    app.dashboard → app.presentation.dashboard
    app.database → app.infrastructure.persistence
    app.data → app.infrastructure.data
    app.providers → app.infrastructure.providers
    app.microstructure → app.domain.market_analysis.microstructure
    app.market_microstructure → app.domain.market_analysis.microstructure
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Root directory of the project
PROJECT_ROOT = Path(__file__).parent.parent

# Import mapping: old_path -> new_path
IMPORT_MAPPING: Dict[str, str] = {
    # Consolidated duplicates
    "app.microstructure": "app.domain.market_analysis.microstructure",
    "app.market_microstructure": "app.domain.market_analysis.microstructure",

    # To Domain layer
    "app.strategies": "app.domain.strategies",
    "app.models": "app.domain.models",
    "app.portfolio": "app.domain.portfolio",
    "app.optimization": "app.domain.optimization",
    "app.analysis": "app.domain.analysis",
    "app.tax": "app.domain.tax",
    "app.ensemble": "app.domain.ensemble",
    "app.market_making": "app.domain.trading.market_making",

    # To Infrastructure layer
    "app.database": "app.infrastructure.persistence",
    "app.data": "app.infrastructure.data",
    "app.providers": "app.infrastructure.providers",
    "app.middleware": "app.infrastructure.middleware",
    "app.user_config": "app.infrastructure.config",

    # To Presentation layer
    "app.api": "app.presentation.api",
    "app.dashboard": "app.presentation.dashboard",

    # To Application layer
    "app.maestro": "app.application.orchestration",

    # Services → Domain Services (business logic)
    "app.services.risk_management_chan": "app.domain.services.risk.chan",
    "app.services.portfolio_risk_manager": "app.domain.services.risk.portfolio",
    "app.services.advanced_risk_manager": "app.domain.services.risk.advanced",
    "app.services.risk_envelope_validator": "app.domain.services.risk.envelope",
    "app.services.var_position_limiter": "app.domain.services.risk.var_limiter",
    "app.services.trailing_stop_manager": "app.domain.services.risk.trailing_stop",
    "app.services.position_sizing_engine": "app.domain.services.position.sizing",
    "app.services.execution_algorithms": "app.domain.services.execution.algorithms",
    "app.services.signal_scoring_engine": "app.domain.services.signals.scoring",
    "app.services.signal_scorer": "app.domain.services.signals.scorer",
    "app.services.factor_models": "app.domain.services.factors.models",
    "app.services.hurst_exponent_analyzer": "app.domain.services.analysis.hurst",
    "app.services.momentum_analysis": "app.domain.services.analysis.momentum",
    "app.services.portfolio_analytics_service": "app.domain.services.portfolio.analytics",
    "app.services.portfolio_builder": "app.domain.services.portfolio.builder",
    "app.services.multi_strategy_allocation": "app.domain.services.portfolio.allocation",
    "app.services.risk_scaling": "app.domain.services.risk.scaling",
    "app.services.risk_scaling_application": "app.domain.services.risk.scaling_application",
    "app.services.forex_risk": "app.domain.services.risk.forex",
    "app.services.correlation": "app.domain.services.analysis.correlation",
    "app.services.tax_efficiency": "app.domain.services.tax.efficiency",

    # Services → Application Services (orchestration)
    "app.services.validation_engine": "app.application.validation.engine",
    "app.services.validation_orchestration": "app.application.validation.orchestration",
    "app.services.alerting_system": "app.application.alerting",
    "app.services.reporting": "app.application.reporting",
    "app.services.reporting_generator": "app.application.reporting.generator",
    "app.services.market_universe_orchestrator": "app.application.orchestration.market_universe",
    "app.services.multi_market_orchestrator": "app.application.orchestration.multi_market",
    "app.services.strategy_stock_allocator": "app.application.orchestration.strategy_allocation",
    "app.services.strategy_recommender": "app.application.orchestration.strategy_recommendation",
    "app.services.profile_generator": "app.application.orchestration.profile_generation",
    "app.services.reconciliation": "app.application.reconciliation",
    "app.services.backtest_orchestration": "app.application.orchestration.backtest",
    "app.services.backtesting_orchestration": "app.application.orchestration.backtesting",
    "app.services.live_trading": "app.application.orchestration.live_trading",
    "app.services.emergency_handler": "app.application.handlers.emergency",
    "app.services.scheduling": "app.application.scheduling",

    # Services → Infrastructure (external integrations)
    "app.services.market_data_service": "app.infrastructure.feeds.market_data",
    "app.services.crypto_data_service": "app.infrastructure.feeds.crypto",
    "app.services.forex_data_service": "app.infrastructure.feeds.forex",
    "app.services.paper_trading_service": "app.infrastructure.brokers.paper",
    "app.services.circuit_breaker": "app.infrastructure.resilience.circuit_breaker",
    "app.services.broker_failover": "app.infrastructure.resilience.broker_failover",
    "app.services.configuration_persistence": "app.infrastructure.persistence.configuration",
    "app.services.metrics_database": "app.infrastructure.persistence.metrics",
    "app.services.external_integrations": "app.infrastructure.external.integrations",
    "app.services.smart_order_routing": "app.infrastructure.execution.smart_routing",
    "app.services.rate_limiting": "app.infrastructure.security.rate_limiting",
    "app.services.logging": "app.infrastructure.logging",
    "app.services.monitoring": "app.infrastructure.monitoring",
    "app.services.news_processor": "app.infrastructure.data.news_processor",
    "app.services.synthetic_data": "app.infrastructure.data.synthetic",
    "app.services.task_queue": "app.infrastructure.queues.task_queue",

    # Core → shared/config/
    "app.core.config": "app.shared.config.config",
    "app.core.config_loader": "app.shared.config.config_loader",
    "app.core.config_validator": "app.shared.config.config_validator",
    "app.core.centralized_config": "app.shared.config.centralized_config",
    "app.core.environment_config": "app.shared.config.environment_config",
    "app.core.yaml_config_updater": "app.shared.config.yaml_config_updater",
    "app.core.test_config": "app.shared.config.test_config",
    "app.core.di_config": "app.shared.config.di_config",
    "app.core.di_container": "app.shared.config.di_container",

    # Core → shared/utils/
    "app.core.decimal_utils": "app.shared.utils.decimal_utils",
    "app.core.timezone_utils": "app.shared.utils.timezone_utils",
    "app.core.symbol_mapper": "app.shared.utils.symbol_mapper",
    "app.core.tier_mapper": "app.shared.utils.tier_mapper",

    # Core → shared/performance/
    "app.core.numba_accelerators": "app.shared.performance.numba_accelerators",
    "app.core.numba_enforcer": "app.shared.performance.numba_enforcer",
    "app.core.statsmodels_fallback": "app.shared.performance.statsmodels_fallback",

    # Core → shared/
    "app.core.exceptions": "app.shared.exceptions.exceptions",
    "app.core.audit": "app.shared.audit",

    # Core → security/
    "app.core.auth": "app.security.auth",
    "app.core.secret_manager": "app.security.secret_manager",
    "app.core.secure_serialization": "app.security.secure_serialization",

    # Core → infrastructure/
    "app.core.database": "app.infrastructure.persistence.database",
    "app.core.logging_config": "app.infrastructure.logging.logging_config",
    "app.core.messaging": "app.infrastructure.messaging.messaging",
    "app.core.rate_limit_governor": "app.infrastructure.resilience.rate_limit_governor",
    "app.core.reconnection_manager": "app.infrastructure.resilience.reconnection_manager",

    # Core → domain/
    "app.core.compliance_engine": "app.domain.services.compliance.compliance_engine",
    "app.core.compliance_integration": "app.domain.services.compliance.compliance_integration",
    "app.core.trading_validators": "app.domain.services.trading_validators",
    "app.core.shadow_mode": "app.domain.services.shadow_mode",
    "app.core.contracts": "app.domain.contracts",

    # Core → presentation/
    "app.core.api_endpoints": "app.presentation.api.api_endpoints",

    # Core subdirectories
    "app.core.config": "app.shared.config",
    "app.core.interfaces": "app.shared.interfaces",
    "app.core.models": "app.domain.models",
    "app.core.protocols": "app.shared.protocols",
    "app.core.strategy_config": "app.domain.strategies.config",
    "app.core.utils": "app.shared.utils",
}


def find_python_files(root: Path, exclude_dirs: List[str] = None) -> List[Path]:
    """Find all Python files in the project."""
    if exclude_dirs is None:
        exclude_dirs = [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "build",
            "dist",
            "*.egg-info",
        ]

    python_files = []
    for path in root.rglob("*.py"):
        # Skip excluded directories
        if any(excluded in str(path) for excluded in exclude_dirs):
            continue
        python_files.append(path)

    return python_files


def update_imports_in_file(
    file_path: Path,
    mapping: Dict[str, str],
    dry_run: bool = False,
    verbose: bool = False,
) -> Tuple[int, List[str]]:
    """
    Update imports in a single file.

    Returns:
        Tuple of (number_of_changes, list_of_changes)
    """
    try:
        content = file_path.read_text()
    except Exception as e:
        return 0, [f"Error reading {file_path}: {e}"]

    original_content = content
    changes = []
    total_changes = 0

    # Sort by length (longest first) to avoid partial replacements
    sorted_mapping = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)

    for old_import, new_import in sorted_mapping:
        # Pattern for "from X import" style imports (including submodules)
        # Matches: "from app.strategies import" and "from app.strategies.base import"
        pattern_from = rf"(from\s+){re.escape(old_import)}((?:\.\w+)*)\s+(import)"
        replacement_from = rf"\1{new_import}\2 \3"

        # Pattern for "import X" style imports (including submodules)
        pattern_import = rf"(import\s+){re.escape(old_import)}((?:\.\w+)*)(\s*(?:as|,|$|\n))"
        replacement_import = rf"\1{new_import}\2\3"

        # Count occurrences
        from_matches = re.findall(pattern_from, content)
        import_matches = re.findall(pattern_import, content)
        num_matches = len(from_matches) + len(import_matches)

        if num_matches > 0:
            # Apply replacements
            content = re.sub(pattern_from, replacement_from, content)
            content = re.sub(pattern_import, replacement_import, content)

            change_msg = f"  {old_import} → {new_import} ({num_matches} occurrences)"
            changes.append(change_msg)
            total_changes += num_matches

    if total_changes > 0:
        if verbose:
            print(f"\n{file_path}:")
            for change in changes:
                print(change)

        if not dry_run:
            try:
                file_path.write_text(content)
            except Exception as e:
                return 0, [f"Error writing {file_path}: {e}"]

    return total_changes, changes


def migrate_imports(
    root: Path,
    mapping: Dict[str, str],
    dry_run: bool = False,
    verbose: bool = False,
) -> Dict[str, int]:
    """
    Migrate imports across all Python files.

    Returns:
        Dictionary with statistics
    """
    python_files = find_python_files(root)

    stats = {
        "files_scanned": len(python_files),
        "files_modified": 0,
        "total_changes": 0,
    }

    print(f"Scanning {len(python_files)} Python files...")

    for file_path in python_files:
        changes, _ = update_imports_in_file(file_path, mapping, dry_run, verbose)
        if changes > 0:
            stats["files_modified"] += 1
            stats["total_changes"] += changes
            if not verbose:
                print(f"  {file_path.relative_to(root)}: {changes} changes")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Migrate imports for AlgoTrading reorganization"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed changes for each file",
    )
    parser.add_argument(
        "--mapping-only",
        action="store_true",
        help="Just show the import mapping and exit",
    )

    args = parser.parse_args()

    if args.mapping_only:
        print("Import Mapping:")
        print("=" * 60)
        for old, new in sorted(IMPORT_MAPPING.items()):
            print(f"  {old}")
            print(f"    → {new}")
        return

    print("=" * 60)
    print("AlgoTrading Import Migration Script")
    print("=" * 60)

    if args.dry_run:
        print("DRY RUN MODE - No files will be modified")
        print()

    stats = migrate_imports(
        PROJECT_ROOT / "app",
        IMPORT_MAPPING,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    print()
    print("=" * 60)
    print("Summary:")
    print(f"  Files scanned: {stats['files_scanned']}")
    print(f"  Files to modify: {stats['files_modified']}")
    print(f"  Total import changes: {stats['total_changes']}")

    if args.dry_run:
        print()
        print("This was a dry run. Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
