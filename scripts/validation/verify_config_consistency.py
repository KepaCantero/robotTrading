#!/usr/bin/env python3
"""
Verify Configuration Consistency

Script to verify that parameters in YAML files match what's actually used
in the code, and that optimized parameters are being applied.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_strategy_yaml(strategy_name: str) -> Dict[str, Any]:
    """Load strategy YAML configuration."""
    yaml_file = project_root / "config" / "strategies" / f"{strategy_name}.yaml"
    
    if not yaml_file.exists():
        return {}
    
    with open(yaml_file, 'r') as f:
        return yaml.safe_load(f) or {}


def find_hardcoded_values() -> Dict[str, List[Tuple[str, str, Any]]]:
    """Find hardcoded values in strategy files."""
    strategies_dir = project_root / "app" / "strategies"
    hardcoded = {}
    
    import re
    
    # Patterns to find hardcoded Decimal values
    decimal_pattern = re.compile(r'Decimal\("([0-9.]+)"\)')
    
    for strategy_file in strategies_dir.glob("*.py"):
        if strategy_file.name == "base.py" or strategy_file.name.startswith("__"):
            continue
        
        strategy_name = strategy_file.stem
        hardcoded_values = []
        
        with open(strategy_file, 'r') as f:
            lines = f.readlines()
            for line_num, line in enumerate(lines, 1):
                matches = decimal_pattern.findall(line)
                for match in matches:
                    # Skip if it's in a comment or string format
                    if '#' in line and line.index(match) > line.index('#'):
                        continue
                    
                    hardcoded_values.append((
                        f"{strategy_file.name}:{line_num}",
                        match,
                        line.strip()
                    ))
        
        if hardcoded_values:
            hardcoded[strategy_name] = hardcoded_values
    
    return hardcoded


def verify_optimized_params_applied() -> Dict[str, Dict[str, Any]]:
    """Verify that optimized parameters are in YAML files."""
    results = {}
    
    for strategy_name in ["momentum", "mean_reversion", "pairs_trading"]:
        config = load_strategy_yaml(strategy_name)
        
        # Expected optimized values (from optimization results)
        optimized_values = {
            "momentum": {
                "rsi_threshold": 57,
                "momentum_threshold": 0.025,
                "volume_threshold": 1.39,
                "ema_period": 36,
                "max_position_size": 0.071,
            },
            "mean_reversion": {
                "z_score_threshold": 1.49,
                "lookback_period": 12,
                "stop_loss_pct": 0.017,
                "take_profit_pct": 0.103,
                "max_position_size": 0.07,
            },
            "pairs_trading": {
                "spread_threshold": 1.68,
                "lookback_period": 31,
                "cointegration_threshold": 0.032,
            },
        }
        
        if strategy_name not in optimized_values:
            continue
        
        expected = optimized_values[strategy_name]
        actual = {}
        status = {}
        
        # Check parameters
        params = config.get("parameters", {})
        for key, expected_value in expected.items():
            if key in params:
                actual_value = params[key]
                actual[key] = actual_value
                status[key] = "✅" if abs(actual_value - expected_value) < 0.01 else "❌"
            elif key in config:
                actual_value = config[key]
                actual[key] = actual_value
                status[key] = "✅" if abs(actual_value - expected_value) < 0.01 else "❌"
            else:
                status[key] = "⚠️  NOT FOUND"
        
        results[strategy_name] = {
            "expected": expected,
            "actual": actual,
            "status": status,
        }
    
    return results


def main():
    print("=" * 80)
    print("🔍 CONFIGURATION CONSISTENCY VERIFICATION")
    print("=" * 80)
    print()
    
    # 1. Check hardcoded values
    print("1️⃣ Checking for hardcoded values...")
    print("-" * 80)
    hardcoded = find_hardcoded_values()
    
    if hardcoded:
        print("⚠️  Found hardcoded values:")
        for strategy, values in hardcoded.items():
            print(f"\n   {strategy}:")
            for location, value, line in values[:5]:  # Show first 5
                print(f"      {location}: Decimal(\"{value}\") - {line[:60]}...")
            if len(values) > 5:
                print(f"      ... and {len(values) - 5} more")
    else:
        print("✅ No hardcoded Decimal values found")
    
    print()
    
    # 2. Verify optimized parameters
    print("2️⃣ Verifying optimized parameters are applied...")
    print("-" * 80)
    verification = verify_optimized_params_applied()
    
    all_correct = True
    for strategy_name, data in verification.items():
        print(f"\n   {strategy_name}:")
        for param, status in data["status"].items():
            expected = data["expected"].get(param, "N/A")
            actual = data["actual"].get(param, "N/A")
            
            if status == "✅":
                print(f"      ✅ {param}: {actual} (expected: {expected})")
            elif status == "❌":
                print(f"      ❌ {param}: {actual} (expected: {expected})")
                all_correct = False
            else:
                print(f"      ⚠️  {param}: NOT FOUND (expected: {expected})")
                all_correct = False
    
    print()
    print("=" * 80)
    
    if all_correct and not hardcoded:
        print("✅ ALL CHECKS PASSED")
        print("=" * 80)
        return 0
    else:
        print("⚠️  ISSUES FOUND - Review recommendations above")
        print("=" * 80)
        
        if hardcoded:
            print("\n💡 Recommendation: Move hardcoded values to YAML configuration")
        
        if not all_correct:
            print("\n💡 Recommendation: Run scripts/apply_optimized_parameters.py to apply optimizations")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())

