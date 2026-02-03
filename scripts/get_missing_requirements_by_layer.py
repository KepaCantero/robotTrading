#!/usr/bin/env python3
"""
Script to find Python files WITHOUT requirements documents by layer.
Usage: python scripts/get_missing_requirements_by_layer.py [layer_number]
Arguments:
    layer_number: Optional layer number (1-9). If not provided, shows all layers.
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


# Layer definitions ordered by dependencies (least to most)
LAYERS = [
    # Layer 1: Domain
    (1, "1.1", "Domain Entities", "domain/entities"),
    (1, "1.2", "Value Objects", "domain/value_objects"),
    (1, "1.3", "Domain Services", "domain/services"),
    (1, "1.4", "Portfolio Optimization (Services)", "domain/services/portfolio_optimization"),
    (1, "1.5", "Strategy Definitions", "domain/strategies"),
    (1, "1.6", "Repository Interfaces", "domain/repositories"),
    (1, "1.7", "Domain Models", "domain/models"),
    (1, "1.8", "Domain Configurators", "domain/configurators"),
    (1, "1.9", "Portfolio Optimization (Alt)", "domain/portfolio_optimization"),
    # Layer 2: Infrastructure
    (2, "2.1", "Database/Infrastructure", "database"),
    (2, "2.2", "Infrastructure", "infrastructure"),
    # Layer 3: Core
    (3, "3.1", "Core Configuration", "core/config"),
    (3, "3.2", "Compliance Module", "core/compliance"),
    (3, "3.3", "Core Interfaces", "core/interfaces"),
    (3, "3.4", "Core Utilities", "core"),
    # Layer 4: Application
    (4, "4.1", "Use Cases", "application/use_cases"),
    (4, "4.2", "Application Services", "application/services"),
    (4, "4.3", "Application Routers", "application/routers"),
    (4, "4.4", "Application Interfaces", "application/interfaces"),
    # Layer 5: Backtesting
    (5, "5.1", "Backtesting Core", "backtesting/core"),
    (5, "5.2", "Labeling", "backtesting/labeling"),
    (5, "5.3", "Feature Engineering", "backtesting/feature_engineering"),
    (5, "5.4", "Acceptance Criteria", "backtesting/acceptance"),
    (5, "5.5", "Execution", "backtesting/execution"),
    (5, "5.6", "Backtesting Services", "backtesting/services"),
    (5, "5.7", "Validation", "backtesting/validation"),
    (5, "5.8", "Meta Analyzer", "backtesting/meta_analyzer"),
    (5, "5.9", "Profile Batch", "backtesting/profile_batch"),
    (5, "5.10", "Robust Engine", "backtesting/robust_engine"),
    (5, "5.11", "Reports", "backtesting/reports"),
    (5, "5.12", "Backtesting (Other)", "backtesting"),
    # Layer 6: Strategies
    (6, "6.1", "Strategy Base", "strategies/base"),
    (6, "6.2", "FX Carry Trade", "strategies/fx_carry_trade"),
    (6, "6.3", "FX Intermarket", "strategies/fx_intermarket"),
    (6, "6.4", "Crypto Momentum", "strategies/crypto_momentum"),
    (6, "6.5", "Low Volatility", "strategies/low_volatility"),
    (6, "6.6", "Momentum Modular", "strategies/momentum_modular"),
    (6, "6.7", "Covered Calls", "strategies/covered_calls"),
    (6, "6.8", "Multi Factor", "strategies/multi_factor"),
    (6, "6.9", "Dividend", "strategies/dividend"),
    (6, "6.10", "Strategy Indicators", "strategies/indicators"),
    (6, "6.11", "Strategies (Other)", "strategies"),
    # Layer 7: Advanced Features
    (7, "7.1", "Market Microstructure (OFI)", "market_microstructure/ofi"),
    (7, "7.2", "Microstructure", "microstructure"),
    (7, "7.3", "Ensemble Methods", "ensemble"),
    (7, "7.4", "Parameter Optimization", "optimization/parameter"),
    (7, "7.5", "Optimization (Other)", "optimization"),
    # Layer 8: API/Presentation
    (8, "8.1", "API Endpoints", "api"),
    (8, "8.2", "Middleware", "middleware"),
    (8, "8.3", "Presentation", "presentation"),
    (8, "8.4", "Security", "security"),
    # Layer 9: Other
    (9, "9.0", "Tests", "tests"),
    (9, "9.1", "Services (Other)", "services"),
    (9, "9.2", "Engines", "engines"),
]


def get_all_python_files() -> Set[Path]:
    """Get all Python files in app/ directory."""
    app_path = Path("app")
    if not app_path.exists():
        return set()
    return {f for f in app_path.rglob("*.py") if f.name != "__init__.py"}


def get_all_requirements_files() -> Set[Path]:
    """Get all requirements files in .requirements/ directory."""
    req_path = Path(".requirements")
    if not req_path.exists():
        return set()
    return set(req_path.rglob("*.requirements.md"))


def python_file_to_requirement_path(py_file: Path) -> Tuple[Path, Path]:
    """Convert a Python file path to its expected requirements file paths."""
    relative_path = py_file.relative_to("app")
    req_base = Path(".requirements") / "app" / relative_path
    pattern1 = Path(str(req_base) + ".requirements.md")
    pattern2 = Path(str(req_base.with_suffix('')) + ".requirements.md")
    return pattern1, pattern2


def get_layer_for_path(relative_path: str) -> Tuple[int, str, str]:
    """Determine the layer for a given file path."""
    path_str = str(relative_path)

    for layer_num, sublayer_id, sublayer_name, dir_path in LAYERS:
        if path_str.startswith(dir_path):
            return (layer_num, sublayer_id, sublayer_name)

    return (99, "99.0", "Unknown")


def get_files_without_requirements(target_layer: int = None) -> Dict[int, List[Tuple[str, Path]]]:
    """
    Get Python files that DON'T have requirements documents, grouped by layer.
    Args:
        target_layer: If specified, only return files from this layer
    Returns: Dict mapping layer number to list of (sublayer, py_file) tuples
    """
    py_files = get_all_python_files()
    req_files = get_all_requirements_files()

    # Group missing files by layer
    missing_by_layer = {i: [] for i in range(1, 10)}
    missing_by_layer[99] = []  # Unknown layer

    for py_file in py_files:
        relative_path = str(py_file.relative_to("app"))

        # Check if requirements exist
        pattern1, pattern2 = python_file_to_requirement_path(py_file)
        has_requirements = pattern1 in req_files or pattern2 in req_files

        if not has_requirements:
            layer_num, sublayer_id, sublayer_name = get_layer_for_path(relative_path)
            if target_layer is None or layer_num == target_layer:
                missing_by_layer[layer_num].append((f"L{layer_num}{sublayer_id} - {sublayer_name}", py_file))

    # Remove empty layers
    return {k: v for k, v in missing_by_layer.items() if v}


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Find Python files WITHOUT requirements by layer"
    )
    parser.add_argument(
        "layer",
        nargs="?",
        type=int,
        choices=range(1, 10),
        help="Layer number (1-9). If not provided, shows all layers.",
    )
    parser.add_argument(
        "--format",
        choices=["human", "list"],
        default="human",
        help="Output format (default: human)",
    )

    args = parser.parse_args()
    target_layer = args.layer

    missing_by_layer = get_files_without_requirements(target_layer)

    if args.format == "list":
        # Simple list format for scripting
        for layer_num in sorted(missing_by_layer.keys()):
            for sublayer, py_file in missing_by_layer[layer_num]:
                print(f"app/{py_file.relative_to('app')}")
        return 0 if not missing_by_layer else 1

    # Human-readable format
    print("=" * 100)
    if target_layer:
        print(f"🔍 LAYER {target_layer} - Files WITHOUT Requirements")
    else:
        print("🔍 ALL LAYERS - Files WITHOUT Requirements")
    print("=" * 100)
    print()

    total_missing = sum(len(files) for files in missing_by_layer.values())

    if total_missing == 0:
        print("✅ All files have requirements documents!")
        print()
        return 0

    print(f"📊 SUMMARY: {total_missing} files WITHOUT requirements\\n")

    for layer_num in sorted(missing_by_layer.keys()):
        files = missing_by_layer[layer_num]
        if not files:
            continue

        # Group by sublayer
        by_sublayer = {}
        for sublayer, py_file in files:
            if sublayer not in by_sublayer:
                by_sublayer[sublayer] = []
            by_sublayer[sublayer].append(py_file)

        for sublayer in sorted(by_sublayer.keys()):
            sublayer_files = by_sublayer[sublayer]
            print(f"{'=' * 100}")
            print(f"📍 {sublayer}")
            print(f"{'=' * 100}")
            print(f"   📁 Total: {len(sublayer_files)} files\\n")

            for py_file in sorted(sublayer_files):
                relative_py = py_file.relative_to("app")
                print(f"   ❌ app/{relative_py}")

    print(f"\\n{'=' * 100}")
    print(f"✅ TOTAL: {total_missing} files WITHOUT requirements")
    print(f"{'=' * 100}\\n")

    return 1 if total_missing > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
