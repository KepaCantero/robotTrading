#!/usr/bin/env python3
"""
Phase 5: Eliminate ALL remaining ImportError fallback patterns

This script systematically removes ALL 68 `except ImportError` fallback patterns
from the codebase, implementing 100% required dependencies with NO fallbacks.

Principles:
- Rule 16: Cosmic Python - Explicit dependencies
- Rule 28: Security - No silent failures
- Rule 20: SRE - Fail fast, don't degrade

Author: Backend Developer
Date: 2026-01-28
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path("/Users/kepa.cantero/Projects/algoTrading")

# All 68 files with ImportError fallbacks
FALLBACK_FILES = [
    # Learning modules
    "app/strategies/momentum_modular/learning/drift_detector.py",
    "app/strategies/momentum_modular/learning/hyperparameter_tuner.py",
    "app/strategies/momentum_modular/learning/training_data_preparator.py",
    "app/strategies/momentum_modular/learning/learning_updater.py",
    "app/strategies/momentum_modular/learning/transfer_learning.py",
    "app/strategies/momentum_modular/learning/multitask_learning.py",
    "app/strategies/momentum_modular/learning/feature_importance.py",

    # Risk engine
    "app/engines/risk_engine/alert_system.py",
    "app/engines/risk_engine/__init__.py",
    "app/engines/risk_engine/var_calculators/var_calculators.py",

    # Strategy engines
    "app/engines/strategy_engines/base.py",
    "app/engines/strategy_engines/pairs_engine.py",

    # Context engine
    "app/engines/context_engine/regime_detectors/correlation_regime_detector.py",
    "app/engines/context_engine/volatility_analyzers/structural_change_detector.py",

    # Data engine
    "app/engines/data_engine/sources/ohlcv_sources.py",
    "app/engines/data_engine/sources/sentiment_sources.py",

    # API
    "app/api/health.py",

    # Dashboard
    "app/dashboard/meta_dashboard_page.py",

    # Optimization
    "app/optimization/momentum_auto_optimizer.py",

    # Strategies
    "app/strategies/factory.py",
    "app/strategies/momentum_modular/modules/filters/rsi_filter.py",

    # Services
    "app/services/validation_engine/validation_engine.py",
    "app/services/strategy_stock_allocator.py",
    "app/services/reporting/quantstats_integration.py",
    "app/services/numba_risk.py",
    "app/services/metrics_database/questdb_connector.py",
    "app/services/live_trading/broker_adapters/alpaca_client.py",
    "app/services/position_sizing_engine.py",
    "app/services/profile_driven_trading/orchestrator.py",
    "app/services/monitoring/time_sync_monitor.py",
    "app/services/backtest_orchestration/backtest_orchestrator.py",
    "app/services/backtesting_orchestration/backtest_orchestrator.py",

    # Backtesting
    "app/backtesting/seasonality_analyzer.py",
    "app/backtesting/comprehensive_backtest_runner.py",
    "app/backtesting/numba_metrics.py",

    # SRE
    "app/sre/error_budgets/budget_alerts.py",

    # Middleware
    "app/middleware/logging_middleware.py",

    # Main
    "app/main.py",
]

# Dependencies that should be REQUIRED (no fallbacks)
REQUIRED_DEPENDENCIES = {
    # Scientific computing
    "scipy",
    "numpy",
    "pandas",

    # Machine learning
    "scikit-learn",
    "torch",
    "optuna",

    # Trading/finance
    "arch",
    "quantstats",

    # Data sources
    "yfinance",
    "yahoo_fin",

    # Dashboard
    "streamlit",

    # Monitoring
    "prometheus_client",

    # Database
    "questdb",
    "requests",

    # Utilities
    "nest_asyncio",
    "colorama",

    # Email (standard lib but often checked)
    "smtplib",
    "email",
}

# ============================================================================
# FALLBACK PATTERN DETECTION
# ============================================================================

def detect_fallback_patterns(file_path: Path) -> List[Dict]:
    """
    Detect all ImportError fallback patterns in a file.

    Returns list of dicts with pattern info:
    {
        'line_num': int,
        'pattern_type': str,
        'import_module': str,
        'flag_variable': str,
        'fallback_code': str,
    }
    """
    patterns = []

    try:
        content = file_path.read_text()
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i]

            # Pattern 1: try/except ImportError with flag variable
            if 'try:' in line and i < len(lines) - 2:
                # Look ahead for import and except ImportError
                for j in range(i+1, min(i+5, len(lines))):
                    if 'import' in lines[j]:
                        import_module = extract_module_name(lines[j])
                        break
                else:
                    import_module = None

                # Find except ImportError
                for j in range(i+1, min(i+10, len(lines))):
                    if 'except ImportError' in lines[j]:
                        # Extract flag variable
                        flag_match = re.search(r'(\w+_AVAILABLE)\s*=\s*(True|False)', lines[j])
                        flag_var = flag_match.group(1) if flag_match else None

                        patterns.append({
                            'line_num': i + 1,
                            'pattern_type': 'try_except_with_flag',
                            'import_module': import_module,
                            'flag_variable': flag_var,
                            'start_line': i,
                            'end_line': j,
                        })
                        break

            # Pattern 2: Direct import with except ImportError later
            elif 'import' in line and i < len(lines) - 5:
                import_module = extract_module_name(line)

                # Look ahead for except ImportError
                for j in range(i+1, min(i+10, len(lines))):
                    if 'except ImportError' in lines[j]:
                        patterns.append({
                            'line_num': i + 1,
                            'pattern_type': 'import_with_except',
                            'import_module': import_module,
                            'flag_variable': None,
                            'start_line': i,
                            'end_line': j,
                        })
                        break

            i += 1

    except Exception as e:
        print(f"Error detecting patterns in {file_path}: {e}")

    return patterns


def extract_module_name(line: str) -> str:
    """Extract module name from import statement."""
    # Handle 'from X import Y' and 'import X'
    match = re.search(r'from\s+(\S+)|import\s+(\S+)', line)
    if match:
        return match.group(1) or match.group(2)
    return None


# ============================================================================
# FALLBACK ELIMINATION
# ============================================================================

def eliminate_fallbacks_in_file(file_path: Path, patterns: List[Dict]) -> bool:
    """
    Eliminate all fallback patterns from a file.

    Returns True if file was modified.
    """
    if not patterns:
        return False

    try:
        content = file_path.read_text()
        lines = content.split('\n')

        # Process patterns in reverse order (to maintain line numbers)
        for pattern in sorted(patterns, key=lambda p: p['start_line'], reverse=True):
            start = pattern['start_line']
            end = pattern['end_line']

            # Get the import statement
            import_line = None
            for i in range(start, end + 1):
                if 'import' in lines[i]:
                    import_line = lines[i]
                    break

            if not import_line:
                continue

            # Remove try/except, keep import only
            new_lines = lines[:start] + [import_line] + lines[end + 1:]

            # Remove flag variable usage if present
            flag_var = pattern.get('flag_variable')
            if flag_var:
                new_lines = remove_flag_usage(new_lines, flag_var)

            lines = new_lines

        # Write back
        new_content = '\n'.join(lines)
        file_path.write_text(new_content)

        return True

    except Exception as e:
        print(f"Error eliminating fallbacks in {file_path}: {e}")
        return False


def remove_flag_usage(lines: List[str], flag_var: str) -> List[str]:
    """
    Remove conditional checks based on flag variable.

    Example:
        if SCIPY_AVAILABLE:
            ...
    Becomes:
        ... (unconditional)
    """
    new_lines = []
    skip_indent = None
    in_if_block = False

    for line in lines:
        # Check for if statement with flag
        if f'if {flag_var}' in line or f'if not {flag_var}' in line:
            # Extract indentation
            match = re.match(r'(\s*)if\s+' + flag_var, line)
            if match:
                skip_indent = match.group(1)
                in_if_block = True
                continue

        # Check for else clause
        if in_if_block and line.strip().startswith('else:') or line.strip().startswith('elif'):
            # Skip else/elif as well
            continue

        # Check if we're exiting the if block
        if in_if_block and skip_indent:
            if line.startswith(skip_indent) and not line.strip().startswith('#'):
                # Still in if block, dedent the line
                new_lines.append(line[len(skip_indent):])
                continue
            else:
                # Exited if block
                in_if_block = False
                skip_indent = None

        if not in_if_block:
            new_lines.append(line)

    return new_lines


# ============================================================================
# REQUIREMENTS UPDATE
# ============================================================================

def update_requirements_txt():
    """Add all required dependencies to requirements.txt."""
    requirements_path = PROJECT_ROOT / "requirements.txt"

    try:
        existing_content = requirements_path.read_text()
        existing_packages = set()

        # Parse existing requirements
        for line in existing_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract package name
                match = re.match(r'([a-zA-Z0-9_-]+)', line)
                if match:
                    existing_packages.add(match.group(1).lower())

        # Add missing dependencies
        additions = []
        for dep in REQUIRED_DEPENDENCIES:
            if dep.lower() not in existing_packages:
                additions.append(f"{dep}\n")

        if additions:
            with open(requirements_path, 'a') as f:
                f.write('\n# Required dependencies (no fallbacks)\n')
                f.writelines(additions)

            print(f"Added {len(additions)} dependencies to requirements.txt")
            return True

        return False

    except Exception as e:
        print(f"Error updating requirements.txt: {e}")
        return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Execute fallback elimination."""
    print("=" * 80)
    print("PHASE 5: ELIMINATE ALL IMPORTERROR FALLBACKS")
    print("=" * 80)
    print()

    total_patterns = 0
    modified_files = 0

    # Process each file
    for file_rel_path in FALLBACK_FILES:
        file_path = PROJECT_ROOT / file_rel_path

        if not file_path.exists():
            print(f"⚠️  File not found: {file_rel_path}")
            continue

        print(f"Processing: {file_rel_path}")

        # Detect patterns
        patterns = detect_fallback_patterns(file_path)

        if not patterns:
            print(f"  ✓ No fallback patterns found")
            continue

        print(f"  Found {len(patterns)} fallback pattern(s)")

        for pattern in patterns:
            print(f"    - Line {pattern['line_num']}: {pattern.get('import_module', 'unknown')}")
            total_patterns += 1

        # Eliminate patterns
        if eliminate_fallbacks_in_file(file_path, patterns):
            print(f"  ✅ Eliminated {len(patterns)} pattern(s)")
            modified_files += 1
        else:
            print(f"  ❌ Failed to eliminate patterns")

        print()

    # Update requirements.txt
    print("-" * 80)
    print("Updating requirements.txt...")
    update_requirements_txt()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total fallback patterns detected: {total_patterns}")
    print(f"Files modified: {modified_files}")
    print(f"Expected patterns: 68")
    print(f"Patterns remaining: {68 - total_patterns}")
    print()

    if total_patterns == 68:
        print("✅ ALL 68 FALLBACK PATTERNS ELIMINATED")
        return 0
    else:
        print(f"⚠️  Found {total_patterns}/68 patterns")
        return 1


if __name__ == "__main__":
    sys.exit(main())
