#!/usr/bin/env python
"""
Quick verification script to check fallback values match config.

Usage:
    python scripts/verify_fallback_values.py

This script verifies that hardcoded fallback values in profile_batch_backtester.py
match the defaults in profile_optimization.yaml.
"""

import sys
from pathlib import Path
import yaml


def load_config_defaults():
    """Load default values from profile_optimization.yaml."""
    config_path = Path("config/backtesting/profile_optimization.yaml")

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return None

    with open(config_path) as f:
        config = yaml.safe_load(f)

    threshold_config = config.get("threshold_optimization", {})

    return {
        "rsi_buy": {
            "min": threshold_config.get("rsi", {}).get("buy_threshold", {}).get("min", 20),
            "max": threshold_config.get("rsi", {}).get("buy_threshold", {}).get("max", 35),
        },
        "volume_ratio": {
            "min": threshold_config.get("volume_ratio", {}).get("min", 1.0),
            "max": threshold_config.get("volume_ratio", {}).get("max", 1.5),
        },
    }


def check_code_values():
    """Check hardcoded values in profile_batch_backtester.py."""
    code_path = Path("app/backtesting/profile_batch_backtester.py")

    if not code_path.exists():
        print(f"❌ Code file not found: {code_path}")
        return None

    with open(code_path) as f:
        content = f.read()

    # Check for correct values
    has_correct_rsi = "rsi_buy_min, rsi_buy_max = 20, 35" in content
    has_correct_vol = "vol_min, vol_max = 1.0, 1.5" in content

    # Check for old incorrect values
    has_old_rsi = "rsi_buy_min, rsi_buy_max = 30, 70" in content
    has_old_vol = "vol_min, vol_max = 1.0, 3.0" in content

    # Check for config comments
    has_rsi_comment = "rsi.buy_threshold" in content
    has_vol_comment = "volume_ratio" in content

    return {
        "correct_rsi": has_correct_rsi,
        "correct_vol": has_correct_vol,
        "old_rsi": has_old_rsi,
        "old_vol": has_old_vol,
        "has_comments": has_rsi_comment and has_vol_comment,
    }


def main():
    """Main verification function."""
    print("=" * 70)
    print("FALLBACK VALUES VERIFICATION")
    print("=" * 70)
    print()

    # Load config values
    print("1. Loading config values from profile_optimization.yaml...")
    config_defaults = load_config_defaults()
    if config_defaults is None:
        return 1

    print(
        f"   ✓ RSI buy range: min={config_defaults['rsi_buy']['min']}, max={config_defaults['rsi_buy']['max']}"
    )
    print(
        f"   ✓ Volume range: min={config_defaults['volume_ratio']['min']}, max={config_defaults['volume_ratio']['max']}"
    )
    print()

    # Check code values
    print("2. Checking code values in profile_batch_backtester.py...")
    code_values = check_code_values()
    if code_values is None:
        return 1

    print()

    # Verify RSI
    print("3. Verifying RSI buy threshold...")
    if code_values["correct_rsi"]:
        print("   ✓ Code has correct RSI values: (20, 35)")
    else:
        print("   ❌ Code missing correct RSI values: (20, 35)")

    if code_values["old_rsi"]:
        print("   ❌ Code still has old incorrect RSI values: (30, 70)")
    else:
        print("   ✓ Old incorrect RSI values removed")

    print()

    # Verify Volume
    print("4. Verifying volume ratio...")
    if code_values["correct_vol"]:
        print("   ✓ Code has correct volume values: (1.0, 1.5)")
    else:
        print("   ❌ Code missing correct volume values: (1.0, 1.5)")

    if code_values["old_vol"]:
        print("   ❌ Code still has old incorrect volume values: (1.0, 3.0)")
    else:
        print("   ✓ Old incorrect volume values removed")

    print()

    # Check comments
    print("5. Checking for config reference comments...")
    if code_values["has_comments"]:
        print("   ✓ Code has comments referencing config keys")
    else:
        print("   ⚠ Code missing config reference comments")

    print()
    print("=" * 70)

    # Final verdict
    all_checks_passed = (
        code_values["correct_rsi"]
        and code_values["correct_vol"]
        and not code_values["old_rsi"]
        and not code_values["old_vol"]
        and code_values["has_comments"]
    )

    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Fallback values match config!")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Review the output above")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
