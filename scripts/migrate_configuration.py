#!/usr/bin/env python3
"""
Configuration Migration Script
TASK-10: Centralización de Configuración

Este script migra valores mágicos dispersos en el código a la configuración centralizada.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple
import ast
import argparse

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.centralized_config import (
    CentralizedConfig,
    TradingThresholds,
    StrategyConfig,
    get_config,
    update_strategy_config,
    save_strategy_config
)


class ConfigurationMigrator:
    """Migrates hardcoded values to centralized configuration."""
    
    def __init__(self):
        self.config = get_config()
        self.magic_values_found: Dict[str, List[Tuple[str, int, str]]] = {}
        self.migration_log: List[str] = []
    
    def scan_for_magic_values(self, directory: str = "app") -> None:
        """Scan directory for magic values."""
        print(f"🔍 Scanning {directory} for magic values...")
        
        patterns = {
            "decimal_values": r"Decimal\(['\"](0\.\d+)['\"]\)",
            "float_values": r"(\d+\.\d+)(?![a-zA-Z])",
            "threshold_patterns": r"(threshold|limit|max_|min_|pct|ratio)",
            "hardcoded_percentages": r"(\d+\.\d+)(?=\s*%)",
            "hardcoded_ratios": r"(\d+\.\d+)(?=\s*ratio)",
        }
        
        for file_path in Path(directory).rglob("*.py"):
            if "test_" in file_path.name or "__pycache__" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        for pattern_name, pattern in patterns.items():
                            matches = re.finditer(pattern, line, re.IGNORECASE)
                            for match in matches:
                                value = match.group(1) if match.groups() else match.group(0)
                                
                                if pattern_name not in self.magic_values_found:
                                    self.magic_values_found[pattern_name] = []
                                
                                self.magic_values_found[pattern_name].append((
                                    str(file_path),
                                    i,
                                    line.strip()
                                ))
                                
            except Exception as e:
                print(f"⚠️  Error scanning {file_path}: {e}")
    
    def analyze_magic_values(self) -> None:
        """Analyze found magic values and categorize them."""
        print("\n📊 Analysis of Magic Values:")
        
        for category, values in self.magic_values_found.items():
            print(f"\n{category.upper()}:")
            unique_values = set()
            
            for file_path, line_num, line_content in values:
                # Extract numeric values
                numeric_matches = re.findall(r'\d+\.\d+', line_content)
                for match in numeric_matches:
                    unique_values.add(match)
                
                print(f"  📄 {file_path}:{line_num}")
                print(f"     {line_content}")
            
            print(f"  🔢 Unique values found: {sorted(unique_values)}")
    
    def create_migration_plan(self) -> Dict[str, any]:
        """Create a migration plan for identified magic values."""
        print("\n📋 Creating Migration Plan...")
        
        migration_plan = {
            "trading_thresholds": {},
            "strategy_configs": {},
            "file_modifications": []
        }
        
        # Common threshold values found
        common_thresholds = {
            "0.05": "stop_loss_pct",
            "0.1": "max_position_size", 
            "0.15": "max_drawdown_limit",
            "0.2": "max_sector_exposure",
            "0.3": "max_sector_exposure",
            "0.7": "max_correlation",
            "0.8": "max_total_exposure",
            "30.0": "rsi_oversold",
            "70.0": "rsi_overbought",
            "40": "rsi_threshold",
            "2.0": "z_score_threshold",
            "1.5": "volume_threshold"
        }
        
        # Map found values to configuration
        for category, values in self.magic_values_found.items():
            for file_path, line_num, line_content in values:
                numeric_matches = re.findall(r'\d+\.\d+|\d+', line_content)
                
                for match in numeric_matches:
                    if match in common_thresholds:
                        threshold_name = common_thresholds[match]
                        
                        if threshold_name not in migration_plan["trading_thresholds"]:
                            migration_plan["trading_thresholds"][threshold_name] = {
                                "current_value": match,
                                "files": []
                            }
                        
                        migration_plan["trading_thresholds"][threshold_name]["files"].append({
                            "file": file_path,
                            "line": line_num,
                            "content": line_content
                        })
        
        return migration_plan
    
    def apply_migration_plan(self, migration_plan: Dict[str, any]) -> None:
        """Apply the migration plan."""
        print("\n🚀 Applying Migration Plan...")
        
        # Update trading thresholds
        for threshold_name, data in migration_plan["trading_thresholds"].items():
            print(f"  📝 Updating {threshold_name} = {data['current_value']}")
            
            # Update configuration
            if hasattr(self.config.trading, threshold_name):
                setattr(self.config.trading, threshold_name, float(data['current_value']))
                self.migration_log.append(f"Updated {threshold_name} to {data['current_value']}")
        
        # Update strategy configurations
        self.update_strategy_configurations()
        
        print(f"✅ Migration completed. {len(self.migration_log)} changes applied.")
    
    def update_strategy_configurations(self) -> None:
        """Update strategy configurations with centralized values."""
        print("\n🔧 Updating Strategy Configurations...")
        
        # Momentum strategy
        momentum_config = {
            "enabled": True,
            "weight": 1.0,
            "parameters": {
                "rsi_threshold": 40,
                "momentum_threshold": 0.02,
                "volume_threshold": 1.5,
                "lookback_period": 14
            },
            "max_position_size": self.config.trading.max_position_size,
            "stop_loss_pct": self.config.trading.stop_loss_pct,
            "take_profit_pct": self.config.trading.take_profit_pct,
            "min_sharpe_ratio": 1.2,
            "max_drawdown": self.config.trading.max_drawdown_limit,
            "min_win_rate": 0.45
        }
        
        update_strategy_config("momentum", momentum_config)
        save_strategy_config("momentum")
        self.migration_log.append("Updated momentum strategy configuration")
        
        # Mean reversion strategy
        mean_reversion_config = {
            "enabled": True,
            "weight": 0.8,
            "parameters": {
                "z_score_threshold": 2.0,
                "lookback_period": 20,
                "volatility_threshold": 0.05,
                "mean_reversion_speed": 0.1
            },
            "max_position_size": self.config.trading.max_position_size * 0.8,
            "stop_loss_pct": self.config.trading.stop_loss_pct * 0.6,
            "take_profit_pct": self.config.trading.take_profit_pct * 0.4,
            "min_sharpe_ratio": 1.0,
            "max_drawdown": self.config.trading.max_drawdown_limit,
            "min_win_rate": 0.40
        }
        
        update_strategy_config("mean_reversion", mean_reversion_config)
        save_strategy_config("mean_reversion")
        self.migration_log.append("Updated mean reversion strategy configuration")
        
        # Pairs trading strategy
        pairs_trading_config = {
            "enabled": True,
            "weight": 0.6,
            "parameters": {
                "cointegration_threshold": 0.05,
                "min_correlation": 0.7,
                "max_pair_exposure": 0.2,
                "lookback_period": 30,
                "hedge_ratio_threshold": 0.1
            },
            "max_position_size": self.config.trading.max_position_size * 1.5,
            "stop_loss_pct": self.config.trading.stop_loss_pct * 0.8,
            "take_profit_pct": self.config.trading.take_profit_pct * 0.53,
            "min_sharpe_ratio": 1.5,
            "max_drawdown": self.config.trading.max_drawdown_limit * 0.67,
            "min_win_rate": 0.50
        }
        
        update_strategy_config("pairs_trading", pairs_trading_config)
        save_strategy_config("pairs_trading")
        self.migration_log.append("Updated pairs trading strategy configuration")
    
    def generate_migration_report(self) -> None:
        """Generate a migration report."""
        print("\n📊 Migration Report:")
        print("=" * 50)
        
        print(f"Total magic values found: {sum(len(v) for v in self.magic_values_found.values())}")
        print(f"Categories analyzed: {len(self.magic_values_found)}")
        print(f"Changes applied: {len(self.migration_log)}")
        
        print("\n📝 Changes Applied:")
        for change in self.migration_log:
            print(f"  ✅ {change}")
        
        print("\n🔧 Configuration Files Updated:")
        print("  📄 config/strategies/momentum.yaml")
        print("  📄 config/strategies/mean_reversion.yaml")
        print("  📄 config/strategies/pairs_trading.yaml")
        print("  📄 config/centralized.env")
        
        print("\n📋 Next Steps:")
        print("  1. Review updated configuration files")
        print("  2. Test strategies with new configuration")
        print("  3. Update environment variables if needed")
        print("  4. Run tests to ensure everything works")
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful."""
        print("\n🔍 Validating Migration...")
        
        try:
            # Validate configuration
            is_valid = self.config.validate_configuration()
            
            if is_valid:
                print("✅ Configuration validation passed")
            else:
                print("❌ Configuration validation failed")
                return False
            
            # Check strategy configurations
            strategies = ["momentum", "mean_reversion", "pairs_trading"]
            for strategy_name in strategies:
                strategy_config = self.config.get_strategy_config(strategy_name)
                if strategy_config:
                    print(f"✅ {strategy_name} strategy configuration loaded")
                else:
                    print(f"❌ {strategy_name} strategy configuration not found")
                    return False
            
            print("✅ Migration validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Migration validation failed: {e}")
            return False


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate magic values to centralized configuration")
    parser.add_argument("--scan-only", action="store_true", help="Only scan for magic values, don't migrate")
    parser.add_argument("--directory", default="app", help="Directory to scan (default: app)")
    parser.add_argument("--validate-only", action="store_true", help="Only validate current configuration")
    
    args = parser.parse_args()
    
    migrator = ConfigurationMigrator()
    
    if args.validate_only:
        print("🔍 Validating current configuration...")
        is_valid = migrator.validate_migration()
        sys.exit(0 if is_valid else 1)
    
    print("🚀 Starting Configuration Migration")
    print("=" * 50)
    
    # Scan for magic values
    migrator.scan_for_magic_values(args.directory)
    
    if args.scan_only:
        migrator.analyze_magic_values()
        return
    
    # Create and apply migration plan
    migration_plan = migrator.create_migration_plan()
    migrator.apply_migration_plan(migration_plan)
    
    # Validate migration
    is_valid = migrator.validate_migration()
    
    # Generate report
    migrator.generate_migration_report()
    
    if not is_valid:
        print("\n❌ Migration validation failed. Please check the configuration.")
        sys.exit(1)
    
    print("\n🎉 Migration completed successfully!")


if __name__ == "__main__":
    main()
