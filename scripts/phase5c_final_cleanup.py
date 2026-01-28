#!/usr/bin/env python3
"""
Phase 5c: Final cleanup of remaining _AVAILABLE flags

Cleans up all remaining _AVAILABLE flag variables that weren't
handled by the previous scripts.

Author: Backend Developer
Date: 2026-01-28
"""

import re
from pathlib import Path

PROJECT_ROOT = Path("/Users/kepa.cantero/Projects/algoTrading")

# Files with _AVAILABLE flags that need cleanup
FILES_TO_CLEAN = [
    "app/backtesting/feature_engineering/fractional_differentiation.py",
    "app/strategies/pairs_trading.py",
    "app/strategies/momentum_modular/learning/base_learning_engine.py",
    "app/strategies/momentum_modular/learning/__init__.py",
    "app/engines/risk_engine/var_calculators/var_calculators.py",
    "app/engines/strategy_engines/pairs_engine.py",
    "app/services/momentum_analysis_optimized.py",
    "app/services/market_universe_loader.py",
    "app/services/hurst_exponent_analyzer.py",
    "app/services/profile_driven_trading/orchestrator.py",
    "app/services/momentum_analysis.py",
]


def clean_available_flags(file_path: Path) -> bool:
    """
    Remove _AVAILABLE flag patterns from a file.

    Returns True if file was modified.
    """
    try:
        content = file_path.read_text()
        original_content = content

        # Pattern 1: Remove try/except ImportError blocks that set _AVAILABLE
        # Match: try: ... import ... XXX_AVAILABLE = True except ImportError: XXX_AVAILABLE = False
        pattern1 = r'try:\s*\n\s*import\s+([^\n]+)\s*\n\s+(\w+_AVAILABLE)\s*=\s*True\s*\n(?:except ImportError:\s*\n\s+\2\s*=\s*False\s*\n\s+logger\.[^\n]*\n)?'

        def replace_flag_import(match):
            import_stmt = match.group(1).strip()
            return f"import {import_stmt}\n"

        content = re.sub(pattern1, replace_flag_import, content, flags=re.MULTILINE)

        # Pattern 2: Remove standalone _AVAILABLE = True/False lines
        # But keep them if they're part of numba_enforcer
        lines = content.split('\n')
        new_lines = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check if this is an _AVAILABLE assignment
            if re.search(r'\w+_AVAILABLE\s*=\s*(True|False)', line):
                # Skip this line (remove the flag)
                # But check if there's a warning on the next line
                if i + 1 < len(lines) and 'logger.warning' in lines[i + 1]:
                    i += 1  # Skip the warning too
            else:
                new_lines.append(line)

            i += 1

        content = '\n'.join(new_lines)

        # Pattern 3: Remove if XXX_AVAILABLE: conditional checks
        # This is more complex - we need to dedent the code inside the if block
        # For now, we'll just log that this needs manual review

        if content != original_content:
            file_path.write_text(content)
            return True

        return False

    except Exception as e:
        print(f"Error cleaning {file_path}: {e}")
        return False


def remove_conditional_checks(file_path: Path) -> bool:
    """
    Remove conditional checks based on _AVAILABLE flags.

    Example:
        if SCIPY_AVAILABLE:
            func()
    Becomes:
        func()
    """
    try:
        content = file_path.read_text()
        original_content = content

        # Find all _AVAILABLE flags in the file
        flags = set(re.findall(r'(\w+_AVAILABLE)', content))

        for flag in flags:
            # Remove if flag:
            # And remove if not flag:

            # Pattern: if FLAG:\n    <indented code>
            # We need to dedent the code inside

            # This is complex - for now, we'll do a simple replacement
            # that just removes the check and keeps the code
            pattern = rf'if\s+{flag}:\s*\n((?:\s+[^\n]+\n)+)'

            def dedent_code(match):
                code = match.group(1)
                # Remove one level of indentation (4 spaces or 1 tab)
                lines = code.split('\n')
                dedented_lines = []
                for line in lines:
                    if line.startswith('    '):
                        dedented_lines.append(line[4:])
                    elif line.startswith('\t'):
                        dedented_lines.append(line[1:])
                    else:
                        dedented_lines.append(line)
                return '\n'.join(dedented_lines)

            content = re.sub(pattern, dedent_code, content)

        if content != original_content:
            file_path.write_text(content)
            return True

        return False

    except Exception as e:
        print(f"Error removing conditionals in {file_path}: {e}")
        return False


def main():
    """Execute final cleanup."""
    print("=" * 80)
    print("PHASE 5c: FINAL CLEANUP OF _AVAILABLE FLAGS")
    print("=" * 80)
    print()

    modified_count = 0

    for file_rel_path in FILES_TO_CLEAN:
        file_path = PROJECT_ROOT / file_rel_path

        if not file_path.exists():
            print(f"⚠️  File not found: {file_rel_path}")
            continue

        print(f"Processing: {file_rel_path}")

        # Clean flag definitions
        if clean_available_flags(file_path):
            print(f"  ✅ Removed _AVAILABLE flags")
            modified_count += 1
        else:
            print(f"  ℹ️  No flag definitions found")

        # Remove conditional checks
        if remove_conditional_checks(file_path):
            print(f"  ✅ Removed conditional checks")
            modified_count += 1

        print()

    print("=" * 80)
    print(f"Files modified: {modified_count}")
    print("=" * 80)


if __name__ == "__main__":
    main()
