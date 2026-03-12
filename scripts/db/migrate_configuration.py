"""
Configuration Migration Service
TASK-10: Centralización de Configuración

This service helps migrate magic values from the codebase to the
centralized configuration system.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class MagicValue:
    """Represents a magic value found in the code."""

    file_path: str
    line_number: int
    value: Any
    context: str
    category: str
    suggested_config_key: str


class MagicValueDetector:
    """Detects magic values in Python code."""

    def __init__(self):
        self.numeric_patterns = [
            r"\b\d+\.\d+\b",  # Float numbers
            r"\b\d+\b",  # Integer numbers
        ]

        self.string_patterns = [
            r'"[^"]*"',  # Double quoted strings
            r"'[^']*'",  # Single quoted strings
        ]

        self.timeout_patterns = [
            r"timeout\s*=\s*(\d+)",
            r"timeout\s*:\s*(\d+)",
            r"timeout\s*=\s*(\d+\.\d+)",
        ]

        self.retry_patterns = [
            r"retry\s*=\s*(\d+)",
            r"retries\s*=\s*(\d+)",
            r"max_retries\s*=\s*(\d+)",
        ]

    def scan_file(self, file_path: Path) -> List[MagicValue]:
        """Scan a single file for magic values."""
        magic_values = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            # Parse AST for better analysis
            try:
                tree = ast.parse(content)
                magic_values.extend(self._analyze_ast(tree, file_path, lines))
            except SyntaxError:
                # Fallback to regex analysis
                magic_values.extend(self._analyze_regex(content, file_path, lines))

        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            print(f"Error scanning {file_path}: {e}")

        return magic_values

    def _analyze_ast(
        self, tree: ast.AST, file_path: Path, lines: List[str]
    ) -> List[MagicValue]:
        """Analyze AST for magic values."""
        magic_values = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        magic_values.extend(
                            self._check_assignment(node, target.id, file_path, lines)
                        )
            elif isinstance(node, ast.Call):
                magic_values.extend(self._check_function_call(node, file_path, lines))

        return magic_values

    def _check_assignment(
        self, node: ast.Assign, var_name: str, file_path: Path, lines: List[str]
    ) -> List[MagicValue]:
        """Check assignment for magic values."""
        magic_values = []

        # Check for numeric assignments
        if isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, (int, float)):
                category = self._categorize_numeric(var_name, node.value.value)
                if category:
                    magic_values.append(
                        MagicValue(
                            file_path=str(file_path),
                            line_number=node.lineno,
                            value=node.value.value,
                            context=lines[node.lineno - 1].strip(),
                            category=category,
                            suggested_config_key=self._suggest_config_key(
                                var_name, node.value.value
                            ),
                        )
                    )

        return magic_values

    def _check_function_call(
        self, node: ast.Call, file_path: Path, lines: List[str]
    ) -> List[MagicValue]:
        """Check function calls for magic values."""
        magic_values = []

        # Check keyword arguments
        for keyword in node.keywords:
            if isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, (int, float)):
                    category = self._categorize_numeric(
                        keyword.arg, keyword.value.value
                    )
                    if category:
                        magic_values.append(
                            MagicValue(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                value=keyword.value.value,
                                context=lines[node.lineno - 1].strip(),
                                category=category,
                                suggested_config_key=self._suggest_config_key(
                                    keyword.arg, keyword.value.value
                                ),
                            )
                        )

        return magic_values

    def _analyze_regex(
        self, content: str, file_path: Path, lines: List[str]
    ) -> List[MagicValue]:
        """Fallback regex analysis for magic values."""
        magic_values = []

        for i, line in enumerate(lines):
            # Check for timeout patterns
            for pattern in self.timeout_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    magic_values.append(
                        MagicValue(
                            file_path=str(file_path),
                            line_number=i + 1,
                            value=int(match.group(1)),
                            context=line.strip(),
                            category="timeout",
                            suggested_config_key=f"timeout_{match.group(1)}",
                        )
                    )

            # Check for retry patterns
            for pattern in self.retry_patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    magic_values.append(
                        MagicValue(
                            file_path=str(file_path),
                            line_number=i + 1,
                            value=int(match.group(1)),
                            context=line.strip(),
                            category="retry",
                            suggested_config_key=f"retry_{match.group(1)}",
                        )
                    )

        return magic_values

    def _categorize_numeric(self, var_name: str, value: Any) -> str:
        """Categorize numeric values based on variable name and value."""
        var_lower = var_name.lower()

        # Thresholds
        if any(
            keyword in var_lower for keyword in ["threshold", "limit", "max", "min"]
        ):
            return "threshold"

        # Percentages
        if any(keyword in var_lower for keyword in ["pct", "percent", "ratio"]) or (
            isinstance(value, float) and 0 < value <= 1
        ):
            return "percentage"

        # Timeouts
        if any(keyword in var_lower for keyword in ["timeout", "delay", "wait"]):
            return "timeout"

        # Retries
        if any(keyword in var_lower for keyword in ["retry", "attempt", "max_retries"]):
            return "retry"

        # Ports
        if "port" in var_lower and isinstance(value, int) and 1 <= value <= 65535:
            return "port"

        # Sizes
        if any(keyword in var_lower for keyword in ["size", "count", "number"]):
            return "size"

        return ""

    def _suggest_config_key(self, var_name: str, value: Any) -> str:
        """Suggest a configuration key for a magic value."""
        var_lower = var_name.lower()

        # Convert snake_case to UPPER_CASE
        config_key = var_name.upper()

        # Add prefixes based on category
        if any(keyword in var_lower for keyword in ["threshold", "limit"]):
            config_key = f"THRESHOLD_{config_key}"
        elif any(keyword in var_lower for keyword in ["timeout", "delay"]):
            config_key = f"TIMEOUT_{config_key}"
        elif any(keyword in var_lower for keyword in ["retry", "attempt"]):
            config_key = f"RETRY_{config_key}"

        return config_key


class ConfigurationMigrator:
    """Migrates magic values to centralized configuration."""

    def __init__(self):
        self.detector = MagicValueDetector()
        self.magic_values: List[MagicValue] = []

    def scan_codebase(self, root_path: Path) -> Dict[str, List[MagicValue]]:
        """Scan the entire codebase for magic values."""
        results = {
            "threshold": [],
            "percentage": [],
            "timeout": [],
            "retry": [],
            "port": [],
            "size": [],
            "other": [],
        }

        # Scan Python files
        for py_file in root_path.rglob("*.py"):
            if "test" in str(py_file) or "__pycache__" in str(py_file):
                continue

            magic_values = self.detector.scan_file(py_file)
            self.magic_values.extend(magic_values)

            for mv in magic_values:
                category = mv.category or "other"
                results[category].append(mv)

        return results

    def generate_migration_report(self, results: Dict[str, List[MagicValue]]) -> str:
        """Generate a migration report."""
        report = []
        report.append("# Magic Values Migration Report")
        report.append("=" * 50)
        report.append("")

        total_values = sum(len(values) for values in results.values())
        report.append(f"Total magic values found: {total_values}")
        report.append("")

        for category, values in results.items():
            if not values:
                continue

            report.append(f"## {category.title()} Values ({len(values)})")
            report.append("")

            for mv in values[:10]:  # Show first 10
                report.append(f"- **{mv.file_path}:{mv.line_number}**")
                report.append(f"  - Value: `{mv.value}`")
                report.append(f"  - Context: `{mv.context}`")
                report.append(f"  - Suggested config: `{mv.suggested_config_key}`")
                report.append("")

            if len(values) > 10:
                report.append(f"... and {len(values) - 10} more")
                report.append("")

        return "\n".join(report)

    def generate_config_additions(self, results: Dict[str, List[MagicValue]]) -> str:
        """Generate configuration additions for .env file."""
        config_lines = []
        config_lines.append("# Additional configuration from magic values migration")
        config_lines.append("")

        # Group by suggested config key to avoid duplicates
        unique_configs = {}

        for category, values in results.items():
            for mv in values:
                key = mv.suggested_config_key
                if key not in unique_configs:
                    unique_configs[key] = mv.value

        for key, value in sorted(unique_configs.items()):
            config_lines.append(f"{key}={value}")

        return "\n".join(config_lines)

    def save_migration_report(self, output_path: Path):
        """Save migration report to file."""
        results = self.scan_codebase(Path("."))
        report = self.generate_migration_report(results)
        config_additions = self.generate_config_additions(results)

        with open(output_path, "w") as f:
            f.write(report)
            f.write("\n\n")
            f.write("## Configuration Additions\n")
            f.write("=" * 30)
            f.write("\n\n")
            f.write("Add these to your .env file:\n\n")
            f.write(config_additions)


def main():
    """Main function for configuration migration."""
    migrator = ConfigurationMigrator()

    # Scan codebase
    print("Scanning codebase for magic values...")
    results = migrator.scan_codebase(Path("."))

    # Generate report
    print("Generating migration report...")
    migrator.save_migration_report(Path("magic_values_report.md"))

    # Print summary
    total_values = sum(len(values) for values in results.values())
    print(f"\nMigration complete!")
    print(f"Total magic values found: {total_values}")
    print(f"Report saved to: magic_values_report.md")

    for category, values in results.items():
        if values:
            print(f"- {category}: {len(values)} values")


if __name__ == "__main__":
    main()
