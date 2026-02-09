#!/usr/bin/env python3
"""
Smart Rule-Based Auditor for algoTrading

Uses REAL rules from /rules/ directory with INTELLIGENT CLASSIFICATION:
- /rules/python/ - Python rules (universal + category-specific)
- /rules/trading/ - Trading rules (universal + category-specific)
- /rules/sre/ - SRE rules (universal + category-specific)

SMART FEATURE: Only applies rules that are RELEVANT to each file type.
Each file gets:
1. Universal rules (all production files)
2. Category-specific rules (based on file type/pattern)

EXCLUDES: test files, __pycache__
"""
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


class SmartRuleClassifier:
    """Intelligently classifies which rules apply to which files."""

    def __init__(self, rules_dir: Path):
        self.rules_dir = rules_dir

        # Load Python rules mapping
        python_mapping_file = Path(".ralph/python_rules_mapping.yml")
        if python_mapping_file.exists():
            with open(python_mapping_file) as f:
                mapping = yaml.safe_load(f)
                self.python_mapping = mapping.get("python_rule_categories", {})
                self.python_universal = mapping.get("python_universal", [])
                self.python_patterns = mapping.get("pattern_mappings", {})
        else:
            self.python_mapping = {}
            self.python_universal = []
            self.python_patterns = {}

        # Load trading rules mapping
        trading_mapping_file = Path(".ralph/trading_rules_mapping.yml")
        if trading_mapping_file.exists():
            with open(trading_mapping_file) as f:
                mapping = yaml.safe_load(f)
                self.trading_mapping = mapping.get("trading_rule_categories", {})
                self.trading_universal = mapping.get("trading_universal", [])
        else:
            self.trading_mapping = {}
            self.trading_universal = []

        # Load SRE rules mapping
        sre_mapping_file = Path(".ralph/sre_rules_mapping.yml")
        if sre_mapping_file.exists():
            with open(sre_mapping_file) as f:
                mapping = yaml.safe_load(f)
                self.sre_mapping = mapping.get("sre_rule_categories", {})
                self.sre_universal = mapping.get("sre_universal", [])
                self.sre_patterns = mapping.get("pattern_mappings", {})
        else:
            self.sre_mapping = {}
            self.sre_universal = []
            self.sre_patterns = {}

    def classify_file(self, file_path: Path) -> Dict[str, List[str]]:
        """Determine which rules apply to a given Python file.

        Returns:
            Dict with three keys:
            - "python": list of Python rule file paths
            - "trading": list of Trading rule file paths
            - "sre": list of SRE rule file paths

            Each list contains:
            1. Universal rules (apply to ALL production files)
            2. Category-specific rules (based on file type/pattern)
        """
        applicable = {
            "python": [],
            "trading": [],
            "sre": [],
        }

        try:
            content = file_path.read_text()
        except Exception:
            return applicable

        rel_path = str(file_path).lower()

        # EXCLUDE TESTS
        test_dirs = ['tests/', 'test/', '/tests/', '/test/', '__pycache__']
        if any(td in rel_path for td in test_dirs):
            return applicable

        # === PYTHON RULES (universal + category-specific) ===
        applicable["python"] = self._get_python_rules(rel_path, content)

        # === TRADING RULES (universal + category-specific) ===
        applicable["trading"] = self._get_trading_rules(rel_path, content)

        # === SRE RULES (universal + category-specific) ===
        applicable["sre"] = self._get_sre_rules(rel_path, content)

        return applicable

    def _get_python_rules(self, rel_path: str, content: str) -> List[str]:
        """Get applicable Python rules based on file type."""
        rules = []

        # Add universal Python rules first
        for rule_name in self.python_universal:
            rule_file = self.rules_dir / "python" / f"{rule_name}.md"
            if rule_file.exists():
                rules.append(str(rule_file))

        # Determine category based on patterns
        category = self._match_category(rel_path, self.python_patterns)

        # Add category-specific rules (avoid duplicates)
        if category and category in self.python_mapping:
            for rule_name in self.python_mapping[category]:
                rule_file = self.rules_dir / "python" / f"{rule_name}.md"
                if rule_file.exists():
                    rule_path = str(rule_file)
                    if rule_path not in rules:  # Avoid duplicates
                        rules.append(rule_path)

        return rules

    def _get_trading_rules(self, rel_path: str, content: str) -> List[str]:
        """Get applicable trading rules based on file type."""
        rules = []

        # Add universal trading rules first
        for rule_name in self.trading_universal:
            rule_file = self.rules_dir / "trading" / f"{rule_name}.md"
            if rule_file.exists():
                rules.append(str(rule_file))

        # Determine file type and apply category-specific rules
        file_type_rules = []

        # Check in order of specificity
        if 'backtesting' in rel_path or 'backtest' in rel_path:
            file_type_rules = self.trading_mapping.get("backtesting", [])

        elif 'market_microstructure' in rel_path or 'microstructure' in rel_path:
            file_type_rules = self.trading_mapping.get("microstructure", [])

        elif 'market_making' in rel_path or 'liquidity' in rel_path:
            file_type_rules = self.trading_mapping.get("market_making", [])

        elif 'strategies' in rel_path or 'strategy' in rel_path:
            file_type_rules = self.trading_mapping.get("strategies", [])

        elif 'portfolio' in rel_path:
            file_type_rules = self.trading_mapping.get("portfolio", [])

        elif 'analysis' in rel_path:
            file_type_rules = self.trading_mapping.get("analysis", [])

        elif any(kw in rel_path for kw in ['signal', 'indicator', 'screener']):
            file_type_rules = self.trading_mapping.get("signals", [])

        elif 'risk' in rel_path or 'risk' in content:
            file_type_rules = self.trading_mapping.get("risk", [])

        elif 'execution' in rel_path or 'order' in rel_path:
            file_type_rules = self.trading_mapping.get("execution", [])

        elif 'data' in rel_path or 'market_data' in rel_path or 'database' in rel_path:
            file_type_rules = self.trading_mapping.get("data", [])

        # Add category-specific rules (avoid duplicates)
        for rule_name in file_type_rules:
            rule_file = self.rules_dir / "trading" / f"{rule_name}.md"
            if rule_file.exists():
                rule_path = str(rule_file)
                if rule_path not in rules:  # Avoid duplicates
                    rules.append(rule_path)

        return rules

    def _get_sre_rules(self, rel_path: str, content: str) -> List[str]:
        """Get applicable SRE rules based on file type."""
        rules = []

        # Add universal SRE rules first
        for rule_name in self.sre_universal:
            rule_file = self.rules_dir / "sre" / f"{rule_name}.md"
            if rule_file.exists():
                rules.append(str(rule_file))

        # Determine category based on patterns
        category = self._match_category(rel_path, self.sre_patterns)

        # Add category-specific rules (avoid duplicates)
        if category and category in self.sre_mapping:
            for rule_name in self.sre_mapping[category]:
                rule_file = self.rules_dir / "sre" / f"{rule_name}.md"
                if rule_file.exists():
                    rule_path = str(rule_file)
                    if rule_path not in rules:  # Avoid duplicates
                        rules.append(rule_path)

        return rules

    def _match_category(self, rel_path: str, pattern_mappings: Dict[str, List[str]]) -> Optional[str]:
        """Match file path to a category based on patterns."""
        for category, patterns in pattern_mappings.items():
            for pattern in patterns:
                if pattern in rel_path:
                    return category
        return None


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Smart rule-based audit")
    parser.add_argument("file", help="Python file to audit")
    parser.add_argument("--rules-dir", default="/Users/kepa.cantero/Projects/algoTrading/rules",
                        help="Path to rules directory")
    args = parser.parse_args()

    classifier = SmartRuleClassifier(Path(args.rules_dir))

    # Convert to absolute path
    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    if not file_path.exists():
        print(json.dumps({"error": f"File not found: {args.file}"}))
        return 1

    applicable_rules = classifier.classify_file(file_path)

    result = {
        "file": args.file,
        "applicable_rules": applicable_rules,
        "total_rule_files": sum(len(v) for v in applicable_rules.values())
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
