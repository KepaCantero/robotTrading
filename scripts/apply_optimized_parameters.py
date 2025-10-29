#!/usr/bin/env python3
"""
Apply Optimized Parameters to Configuration Files

Script to automatically apply optimized parameters from grid search results
or optimization outputs to the strategy YAML configuration files.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_optimized_params(source: str) -> Optional[Dict[str, Any]]:
    """
    Load optimized parameters from various sources.
    
    Args:
        source: Path to JSON file or "best_config" to use latest grid search result
        
    Returns:
        Dictionary with optimized parameters by strategy
    """
    if source == "best_config":
        # Find latest grid search result
        results_dir = project_root / "docs" / "GRID_SEARCH_RESULTS"
        if not results_dir.exists():
            print(f"❌ Grid search results directory not found: {results_dir}")
            return None
        
        config_files = list(results_dir.glob("best_grid_search_config_*.json"))
        if not config_files:
            print(f"❌ No best config files found in {results_dir}")
            return None
        
        # Use most recent
        latest = sorted(config_files, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        source = str(latest)
        print(f"📂 Using latest config: {latest.name}")
    
    # Load JSON file
    config_file = Path(source)
    if not config_file.exists():
        print(f"❌ Config file not found: {source}")
        return None
    
    with open(config_file, 'r') as f:
        data = json.load(f)
    
    # Extract strategy parameters
    params = {}
    for strategy_name in ["momentum", "mean_reversion", "pairs_trading"]:
        if strategy_name in data:
            params[strategy_name] = data[strategy_name]
    
    return params


def apply_to_yaml(strategy_name: str, params: Dict[str, Any], dry_run: bool = False) -> bool:
    """
    Apply parameters to strategy YAML file.
    
    Args:
        strategy_name: Name of strategy (momentum, mean_reversion, pairs_trading)
        params: Dictionary of parameters to apply
        dry_run: If True, only show what would be changed
        
    Returns:
        True if successful
    """
    yaml_file = project_root / "config" / "strategies" / f"{strategy_name}.yaml"
    
    if not yaml_file.exists():
        print(f"❌ Strategy config not found: {yaml_file}")
        return False
    
    # Load current config
    with open(yaml_file, 'r') as f:
        config = yaml.safe_load(f)
    
    if not config:
        print(f"❌ Failed to load config from {yaml_file}")
        return False
    
    # Map parameter names to config structure
    changes = []
    
    # Update parameters section
    if "parameters" not in config:
        config["parameters"] = {}
    
    # Map common parameter names
    param_mapping = {
        "rsi_threshold": "rsi_threshold",
        "momentum_threshold": "momentum_threshold",
        "volume_threshold": "volume_threshold",
        "ema_period": "ema_period",
        "z_score_threshold": "z_score_threshold",
        "lookback_period": "lookback_period",
        "spread_threshold": "spread_threshold",
        "cointegration_threshold": "cointegration_threshold",
        "stop_loss_pct": "stop_loss_pct",
        "take_profit_pct": "take_profit_pct",
        "max_position_size": "max_position_size",
    }
    
    for param_key, config_key in param_mapping.items():
        if param_key in params:
            old_value = config["parameters"].get(config_key) if config_key in config["parameters"] else config.get(config_key)
            new_value = params[param_key]
            
            if old_value != new_value:
                changes.append({
                    "key": config_key,
                    "old": old_value,
                    "new": new_value,
                    "location": "parameters" if config_key in config.get("parameters", {}) else "root"
                })
                
                if not dry_run:
                    if config_key in config.get("parameters", {}):
                        config["parameters"][config_key] = new_value
                    else:
                        # Some params might be at root level (stop_loss_pct, take_profit_pct)
                        config[config_key] = new_value
    
    # Also check for root-level risk parameters
    for risk_param in ["stop_loss_pct", "take_profit_pct", "max_position_size"]:
        if risk_param in params:
            old_value = config.get(risk_param)
            new_value = params[risk_param]
            
            if old_value != new_value and risk_param not in [c["key"] for c in changes]:
                changes.append({
                    "key": risk_param,
                    "old": old_value,
                    "new": new_value,
                    "location": "root"
                })
                
                if not dry_run:
                    config[risk_param] = new_value
    
    if not changes:
        print(f"✅ No changes needed for {strategy_name}")
        return True
    
    # Display changes
    print(f"\n📝 Changes for {strategy_name}:")
    for change in changes:
        print(f"   {change['key']}: {change['old']} → {change['new']} ({change['location']})")
    
    if not dry_run:
        # Backup original
        backup_file = yaml_file.with_suffix(f".yaml.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        with open(backup_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"💾 Backed up to: {backup_file.name}")
        
        # Write updated config
        with open(yaml_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"✅ Updated: {yaml_file.name}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Apply optimized parameters to strategy configuration files"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="best_config",
        help="Path to JSON config file or 'best_config' to use latest grid search result",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["momentum", "mean_reversion", "pairs_trading", "all"],
        default="all",
        help="Strategy to update (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without applying",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🔧 APPLY OPTIMIZED PARAMETERS")
    print("=" * 80)
    
    if args.dry_run:
        print("🧪 DRY RUN MODE - No changes will be made")
    
    print(f"📂 Source: {args.source}")
    print(f"🎯 Strategy: {args.strategy}")
    print()
    
    # Load optimized parameters
    optimized = load_optimized_params(args.source)
    if not optimized:
        print("❌ Failed to load optimized parameters")
        return 1
    
    print(f"✅ Loaded parameters for {len(optimized)} strategies")
    print()
    
    # Apply to selected strategies
    strategies_to_update = [args.strategy] if args.strategy != "all" else list(optimized.keys())
    
    success_count = 0
    for strategy_name in strategies_to_update:
        if strategy_name not in optimized:
            print(f"⚠️  No parameters found for {strategy_name}, skipping")
            continue
        
        if apply_to_yaml(strategy_name, optimized[strategy_name], dry_run=args.dry_run):
            success_count += 1
    
    print()
    print("=" * 80)
    if args.dry_run:
        print(f"🧪 Dry run complete: {success_count}/{len(strategies_to_update)} strategies reviewed")
    else:
        print(f"✅ Successfully updated {success_count}/{len(strategies_to_update)} strategies")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

