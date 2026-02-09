#!/usr/bin/env python3
"""
Real Rule-Based Auditor for algoTrading

Uses REAL rules from /rules/ directory:
- /rules/python/ - 36 Python rule files
- /rules/trading/ - 25 Trading rule files
- /rules/sre/ - SRE rules

Smart classification: only applies rules that match the file type.
EXCLUDES: test files, __pycache__
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set


class RuleClassifier:
    """Classifies which rules apply to which files."""

    def __init__(self, rules_dir: Path):
        self.rules_dir = rules_dir
        self.python_rules = self._load_rule_index(rules_dir / "python")
        self.trading_rules = self._load_rule_index(rules_dir / "trading")
        self.sre_rules = self._load_rule_index(rules_dir / "sre")

    def _load_rule_index(self, category_dir: Path) -> Dict[str, List[Path]]:
        """Load rule files by category."""
        rules = {}
        if not category_dir.exists():
            return rules

        for rule_file in category_dir.glob("*.md"):
            name = rule_file.stem
            parts = name.split('-', 1)
            if len(parts) == 2:
                category = parts[1].split('-')[0]
            else:
                category = "general"

            if category not in rules:
                rules[category] = []
            rules[category].append(rule_file)

        return rules

    def classify_file(self, file_path: Path) -> Dict[str, List[Path]]:
        """Determine which rule files apply to a given Python file."""
        applicable = {
            "python": [],
            "trading": [],
            "sre": [],
        }

        try:
            content = file_path.read_text()
        except:
            return applicable

        rel_path = str(file_path)

        # EXCLUDE TESTS
        test_dirs = ['tests/', 'test/', '/tests/', '/test/', '__pycache__']
        if any(td in rel_path.lower() for td in test_dirs):
            return applicable

        # === PYTHON CORE RULES (all production files) ===
        core_python_rules = [
            "01-formatting-style.md",
            "02-type-hints.md",
            "03-solid-principles.md",
            "12-logging-observability.md",
            "17-fluent-python-idiomatic-code.md",
        ]

        for rule_name in core_python_rules:
            rule_file = self.rules_dir / "python" / rule_name
            if rule_file.exists():
                applicable["python"].append(rule_file)

        # === ADDITIONAL PYTHON RULES (by pattern) ===
        if 'config' in rel_path:
            applicable["python"].append(self.rules_dir / "python" / "14-configuration-management.md")

        if 'async' in rel_path or 'asyncio' in content or 'async def' in content:
            applicable["python"].append(self.rules_dir / "python" / "13-async-patterns.md")

        if 'database' in rel_path or 'sql' in content.lower():
            applicable["python"].append(self.rules_dir / "python" / "16-cosmic-python-architecture-patterns.md")

        # === TRADING RULES (trading files only) ===
        trading_dirs = ['strategies', 'backtesting', 'analysis', 'market_microstructure', 'trading', 'portfolio']
        if any(dir in rel_path.lower() for dir in trading_dirs):
            applicable["trading"] = list((self.rules_dir / "trading").glob("*.md"))

        return applicable


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Audit with real rules")
    parser.add_argument("file", help="Python file to audit")
    parser.add_argument("--rules-dir", default="/Users/kepa.cantero/Projects/algoTrading/rules",
                        help="Path to rules directory")
    args = parser.parse_args()

    classifier = RuleClassifier(Path(args.rules_dir))

    # Convert to absolute path
    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    applicable_rules = classifier.classify_file(file_path)

    result = {
        "file": args.file,
        "applicable_rules": {
            "python": [str(p) for p in applicable_rules["python"]],
            "trading": [str(p) for p in applicable_rules["trading"]],
            "sre": [str(p) for p in applicable_rules["sre"]],
        },
        "total_rule_files": (
            len(applicable_rules["python"]) +
            len(applicable_rules["trading"]) +
            len(applicable_rules["sre"])
        )
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
