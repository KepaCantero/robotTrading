#!/usr/bin/env python3
"""
Script to list all Python files that HAVE requirements documents.
Ordered by layer (least dependencies to most).
Usage: python scripts/get_files_with_requirements.py
"""

import os
from pathlib import Path
from typing import List, Set, Tuple, Dict

def get_all_python_files() -> Set[Path]:
    """Get all Python files in app/ directory."""
    app_path = Path("app")
    if not app_path.exists():
        return set()
    return set(app_path.rglob("*.py"))


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
    """
    Determine the layer for a given file path.
    Returns: (layer_number, layer_name, layer_description)
    Layers are ordered by dependencies (1 = least, 8 = most)
    """
    path_str = str(relative_path)

    # LAYER 1: Domain (Deepest) - NO dependencies
    if path_str.startswith("domain/entities"):
        return (1, "1.1", "Domain Entities")
    if path_str.startswith("domain/value_objects"):
        return (1, "1.2", "Value Objects")
    if path_str.startswith("domain/services"):
        return (1, "1.3", "Domain Services")
    if path_str.startswith("domain/services/portfolio_optimization"):
        return (1, "1.4", "Portfolio Optimization")
    if path_str.startswith("domain/strategies"):
        return (1, "1.5", "Strategy Definitions")
    if path_str.startswith("domain/repositories"):
        return (1, "1.6", "Repository Interfaces")
    if path_str.startswith("domain/models"):
        return (1, "1.7", "Domain Models")
    if path_str.startswith("domain/configurators"):
        return (1, "1.8", "Domain Configurators")
    if path_str.startswith("domain/portfolio_optimization"):
        return (1, "1.9", "Portfolio Optimization (alt)")

    # LAYER 2: Infrastructure
    if path_str.startswith("database"):
        return (2, "2.1", "Database/Infrastructure")
    if path_str.startswith("infrastructure"):
        return (2, "2.2", "Infrastructure")

    # LAYER 3: Core/Shared
    if path_str.startswith("core/config"):
        return (3, "3.1", "Core Configuration")
    if path_str.startswith("core/compliance"):
        return (3, "3.2", "Compliance Module")
    if path_str.startswith("core/interfaces"):
        return (3, "3.3", "Core Interfaces")
    if path_str.startswith("core"):
        return (3, "3.4", "Core Utilities")

    # LAYER 4: Application
    if path_str.startswith("application/use_cases"):
        return (4, "4.1", "Use Cases")
    if path_str.startswith("application/services"):
        return (4, "4.2", "Application Services")
    if path_str.startswith("application/routers"):
        return (4, "4.3", "Application Routers")
    if path_str.startswith("application/interfaces"):
        return (4, "4.4", "Application Interfaces")

    # LAYER 5: Backtesting
    if path_str.startswith("backtesting/core"):
        return (5, "5.1", "Backtesting Core")
    if path_str.startswith("backtesting/labeling"):
        return (5, "5.2", "Labeling")
    if path_str.startswith("backtesting/feature_engineering"):
        return (5, "5.3", "Feature Engineering")
    if path_str.startswith("backtesting/acceptance"):
        return (5, "5.4", "Acceptance Criteria")
    if path_str.startswith("backtesting/execution"):
        return (5, "5.5", "Execution")
    if path_str.startswith("backtesting/services"):
        return (5, "5.6", "Backtesting Services")
    if path_str.startswith("backtesting/validation"):
        return (5, "5.7", "Validation")
    if path_str.startswith("backtesting/meta_analyzer"):
        return (5, "5.8", "Meta Analyzer")
    if path_str.startswith("backtesting/profile_batch"):
        return (5, "5.9", "Profile Batch")
    if path_str.startswith("backtesting/robust_engine"):
        return (5, "5.10", "Robust Engine")
    if path_str.startswith("backtesting/reports"):
        return (5, "5.11", "Reports")
    if path_str.startswith("backtesting"):
        return (5, "5.12", "Backtesting (Other)")

    # LAYER 6: Strategies
    if path_str.startswith("strategies/base"):
        return (6, "6.1", "Strategy Base")
    if path_str.startswith("strategies/fx_carry_trade"):
        return (6, "6.2", "FX Carry Trade")
    if path_str.startswith("strategies/fx_intermarket"):
        return (6, "6.3", "FX Intermarket")
    if path_str.startswith("strategies/crypto_momentum"):
        return (6, "6.4", "Crypto Momentum")
    if path_str.startswith("strategies/low_volatility"):
        return (6, "6.5", "Low Volatility")
    if path_str.startswith("strategies/momentum_modular"):
        return (6, "6.6", "Momentum Modular")
    if path_str.startswith("strategies/covered_calls"):
        return (6, "6.7", "Covered Calls")
    if path_str.startswith("strategies/multi_factor"):
        return (6, "6.8", "Multi Factor")
    if path_str.startswith("strategies/dividend"):
        return (6, "6.9", "Dividend")
    if path_str.startswith("strategies/indicators"):
        return (6, "6.10", "Strategy Indicators")
    if path_str.startswith("strategies"):
        return (6, "6.11", "Strategies (Other)")

    # LAYER 7: Advanced Features
    if path_str.startswith("market_microstructure/ofi"):
        return (7, "7.1", "Market Microstructure (OFI)")
    if path_str.startswith("microstructure"):
        return (7, "7.2", "Microstructure")
    if path_str.startswith("ensemble"):
        return (7, "7.3", "Ensemble Methods")
    if path_str.startswith("optimization/parameter"):
        return (7, "7.4", "Parameter Optimization")
    if path_str.startswith("optimization"):
        return (7, "7.5", "Optimization (Other)")

    # LAYER 8: API/Presentation (Highest dependencies)
    if path_str.startswith("api"):
        return (8, "8.1", "API Endpoints")
    if path_str.startswith("middleware"):
        return (8, "8.2", "Middleware")
    if path_str.startswith("presentation"):
        return (8, "8.3", "Presentation")
    if path_str.startswith("security"):
        return (8, "8.4", "Security")
    if path_str.startswith("tests"):
        return (9, "9.0", "Tests")
    if path_str.startswith("sre"):
        return (9, "9.1", "SRE")
    if path_str.startswith("services"):
        return (9, "9.2", "Services (Other)")
    if path_str.startswith("engines"):
        return (9, "9.3", "Engines")

    # Default: put at the end
    return (99, "99.0", "Unknown")


def get_files_with_requirements() -> List[Tuple[int, str, str, Path, Path]]:
    """
    Get all Python files that HAVE requirements documents.
    Returns: List of (layer_number, sublayer, layer_desc, py_file, req_file)
    """
    py_files = get_all_python_files()
    req_files = get_all_requirements_files()

    files_with_req = []

    for py_file in py_files:
        # Skip __init__.py
        if py_file.name == "__init__.py":
            continue

        relative_path = py_file.relative_to("app")

        # Check if requirements exist
        pattern1, pattern2 = python_file_to_requirement_path(py_file)
        req_file = None
        if pattern1 in req_files:
            req_file = pattern1
        elif pattern2 in req_files:
            req_file = pattern2

        if req_file is not None:
            layer_num, sublayer, layer_desc = get_layer_for_path(str(relative_path))
            files_with_req.append((layer_num, sublayer, layer_desc, py_file, req_file))

    # Sort by layer number, then sublayer, then filename
    return sorted(files_with_req, key=lambda x: (x[0], x[1], x[3]))


def main():
    """Main function."""
    print("=" * 100)
    print("📋 PYTHON FILES WITH REQUIREMENTS (Ordered by Layer - Least to Most Dependencies)")
    print("=" * 100)
    print()

    files_with_req = get_files_with_requirements()

    # Group by layer
    by_layer = {}
    for layer_num, sublayer, layer_desc, py_file, req_file in files_with_req:
        layer_key = f"L{layer_num:02d} - {layer_desc}"
        if layer_key not in by_layer:
            by_layer[layer_key] = []
        by_layer[layer_key].append((sublayer, py_file, req_file))

    # Print summary
    print(f"📊 SUMMARY: {len(files_with_req)} files WITH requirements\n")

    # Print by layer
    current_layer_num = 0
    for layer_key in sorted(by_layer.keys()):
        # Extract layer number from key
        layer_num = int(layer_key.split()[0].replace("L", "").split("-")[0])
        if layer_num != current_layer_num:
            current_layer_num = layer_num
            print(f"{'=' * 100}")
            print(f"📍 {layer_key}")
            print(f"{'=' * 100}")

        files = sorted(by_layer[layer_key], key=lambda x: x[0])
        print(f"   📁 Total: {len(files)} files\n")

        for sublayer, py_file, req_file in files:
            relative_py = py_file.relative_to("app")
            relative_req = req_file.relative_to(".requirements")
            print(f"   ✅ app/{relative_py}")
            print(f"      → .requirements/{relative_req}")

    # Print total count by layer
    print(f"\n{'=' * 100}")
    print(f"📊 FILES WITH REQUIREMENTS BY LAYER:")
    print(f"{'=' * 100}")

    layer_counts = {}
    for layer_num, sublayer, layer_desc, py_file, req_file in files_with_req:
        layer_key = f"L{layer_num:02d}"
        layer_counts[layer_key] = layer_counts.get(layer_key, 0) + 1

    for layer_key in sorted(layer_counts.keys()):
        count = layer_counts[layer_key]
        # Determine layer name
        layer_num = int(layer_key.replace("L", ""))
        if layer_num == 1:
            name = "Domain (P0)"
        elif layer_num == 2:
            name = "Infrastructure (P2)"
        elif layer_num == 3:
            name = "Core (P2)"
        elif layer_num == 4:
            name = "Application (P1)"
        elif layer_num == 5:
            name = "Backtesting (P1)"
        elif layer_num == 6:
            name = "Strategies (P2)"
        elif layer_num == 7:
            name = "Advanced Features (P2)"
        elif layer_num == 8:
            name = "API/Presentation (P3)"
        else:
            name = "Other"
        print(f"   {layer_key}: {name:30s} {count:4d} files")

    print(f"\n{'=' * 100}")
    print(f"✅ TOTAL: {len(files_with_req)} files WITH requirements")
    print(f"{'=' * 100}\n")


if __name__ == "__main__":
    main()
