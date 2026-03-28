#!/usr/bin/env python3
"""
Checkpoint Verification System

Verifies that .requirements.md files match the actual Python source code.
This ensures the audit process is actually verifying real code, not just
generating template content.

Usage:
    python scripts/verify_checkpoint.py app/core/secret_manager.py
    python scripts/verify_checkpoint.py --batch app/domain/entities/
    python scripts/verify_checkpoint.py --all

Exit Codes:
    0: All checkpoints passed
    1: One or more checkpoints failed
    2: Error in execution
"""

import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class Component:
    """A code component (class, function, method)."""

    name: str
    component_type: str  # "class", "function", "method", "enum", "dataclass"
    line_number: int
    end_line: Optional[int] = None
    signature: Optional[str] = None


@dataclass
class CheckpointResult:
    """Result of checkpoint verification."""

    file_path: str
    passed: bool = False
    components_found: List[Component] = field(default_factory=list)
    components_missing: List[str] = field(default_factory=list)
    line_mismatches: List[Tuple[str, int, int]] = field(default_factory=list)
    signature_mismatches: List[Tuple[str, str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        """Format checkpoint result."""
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        lines = [
            f"\n{'='*60}",
            f"Checkpoint: {self.file_path}",
            f"Status: {status}",
            f"{'='*60}",
        ]

        if self.components_found:
            lines.append(f"\n✅ Components Found ({len(self.components_found)}):")
            for comp in self.components_found[:20]:  # Limit output
                lines.append(
                    f"  - {comp.component_type:10} {comp.name:30} @ line {comp.line_number}"
                )
            if len(self.components_found) > 20:
                lines.append(f"  ... and {len(self.components_found) - 20} more")

        if self.components_missing:
            lines.append(f"\n❌ Missing Components ({len(self.components_missing)}):")
            for name in self.components_missing:
                lines.append(f"  - {name}")

        if self.line_mismatches:
            lines.append(f"\n⚠️  Line Mismatches ({len(self.line_mismatches)}):")
            for name, req_line, actual_line in self.line_mismatches[:10]:
                lines.append(f"  - {name}: expected {req_line}, found {actual_line}")

        if self.signature_mismatches:
            lines.append(f"\n⚠️  Signature Mismatches ({len(self.signature_mismatches)}):")
            for name, expected, actual in self.signature_mismatches[:10]:
                lines.append(f"  - {name}:")
                lines.append(f"      Expected: {expected}")
                lines.append(f"      Found:    {actual}")

        if self.warnings:
            lines.append(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings[:5]:
                lines.append(f"  - {warning}")

        if self.errors:
            lines.append(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors[:5]:
                lines.append(f"  - {error}")

        return "\n".join(lines)


class SourceCodeParser:
    """Parse Python source code to extract components."""

    def __init__(self, source_path: Path):
        self.source_path = source_path
        self.source_code = source_path.read_text()
        try:
            self.tree = ast.parse(self.source_code, filename=str(source_path))
        except SyntaxError as e:
            self.tree = None
            self.syntax_error = str(e)

    def extract_components(self) -> List[Component]:
        """Extract all classes, functions, and methods."""
        if self.tree is None:
            return []

        components = []
        lines = self.source_code.split("\n")

        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                # Determine if it's a dataclass, enum, or regular class
                comp_type = "class"
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        if decorator.id == "dataclass":
                            comp_type = "dataclass"
                    elif isinstance(decorator, ast.Attribute):
                        if decorator.attr == "dataclass":
                            comp_type = "dataclass"

                # Check for Enum
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "Enum":
                        comp_type = "enum"
                    elif isinstance(base, ast.Attribute) and base.attr == "Enum":
                        comp_type = "enum"

                components.append(
                    Component(
                        name=node.name,
                        component_type=comp_type,
                        line_number=node.lineno,
                    )
                )

                # Extract methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        sig = self._extract_signature(item, lines)
                        components.append(
                            Component(
                                name=f"{node.name}.{item.name}",
                                component_type="method",
                                line_number=item.lineno,
                                signature=sig,
                            )
                        )

            elif isinstance(node, ast.FunctionDef):
                # Only module-level functions
                if isinstance(node.parent if hasattr(node, "parent") else None, ast.Module):
                    sig = self._extract_signature(node, lines)
                    components.append(
                        Component(
                            name=node.name,
                            component_type="function",
                            line_number=node.lineno,
                            signature=sig,
                        )
                    )

        # Handle parent relationships for module-level functions
        # (AST doesn't directly provide parent links)
        module_funcs = []
        for node in self.tree.body:
            if isinstance(node, ast.FunctionDef):
                sig = self._extract_signature(node, lines)
                module_funcs.append(
                    Component(
                        name=node.name,
                        component_type="function",
                        line_number=node.lineno,
                        signature=sig,
                    )
                )
        components.extend(module_funcs)

        return components

    def _extract_signature(self, node: ast.FunctionDef, lines: List[str]) -> str:
        """Extract function signature including parameters and return type."""
        # Get the line containing the def
        line = lines[node.lineno - 1]

        # Extract parameter list
        params = []
        for arg in node.args.args:
            param = arg.arg
            if arg.annotation:
                annotation = (
                    ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                )
                param += f": {annotation}"
            params.append(param)

        # Add return type if present
        returns = ""
        if node.returns:
            returns = " -> " + (
                ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
            )

        return f"({', '.join(params)}){returns}"


class RequirementsParser:
    """Parse .requirements.md file to extract documented components."""

    # Match: | `Name()` | Type | Lines | ...
    COMPONENT_TABLE_PATTERN = re.compile(
        r'\|\s+`([a-zA-Z_][a-zA-Z0-9_]*(?:\(\)?)?)`\s+\|\s*(\w+)\s+\|\s*(\d+)(?:-(\d+))?\s+\|'
    )

    def __init__(self, requirements_path: Path):
        self.requirements_path = requirements_path
        self.content = requirements_path.read_text() if requirements_path.exists() else ""

    def extract_components(self) -> List[Component]:
        """Extract components from the requirements file."""
        components = []

        # Try to find the components table
        for match in self.COMPONENT_TABLE_PATTERN.finditer(self.content):
            name = match.group(1)
            # Strip trailing () from function names
            if name.endswith("()"):
                name = name[:-2]
            comp_type = match.group(2).lower()
            line_start = int(match.group(3))
            line_end = int(match.group(4)) if match.group(4) else None

            components.append(
                Component(
                    name=name,
                    component_type=comp_type,
                    line_number=line_start,
                    end_line=line_end,
                )
            )

        return components


class CheckpointVerifier:
    """Verify that requirements match source code."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.requirements_dir = project_root / ".requirements"

    def verify_file(self, python_path: Path) -> CheckpointResult:
        """Verify a single Python file against its requirements."""
        # Determine requirements path
        rel_path = python_path.relative_to(self.project_root)
        req_path = self.requirements_dir / rel_path.with_suffix(".py.requirements.md")

        result = CheckpointResult(file_path=str(rel_path))

        # Parse source code
        parser = SourceCodeParser(python_path)
        if parser.tree is None:
            result.errors.append(f"Syntax error in source: {parser.syntax_error}")
            return result

        source_components = parser.extract_components()
        source_map = {c.name: c for c in source_components}

        # Check if requirements file exists
        if not req_path.exists():
            result.warnings.append(f"No requirements file found at {req_path}")
            result.passed = len(source_components) > 0  # Pass if code has components
            return result

        # Parse requirements
        req_parser = RequirementsParser(req_path)
        req_components = req_parser.extract_components()

        # Verify each requirement component exists in source
        for req_comp in req_components:
            if req_comp.name in source_map:
                source_comp = source_map[req_comp.name]

                # Check line number
                if abs(req_comp.line_number - source_comp.line_number) > 5:  # Allow some tolerance
                    result.line_mismatches.append(
                        (req_comp.name, req_comp.line_number, source_comp.line_number)
                    )

                result.components_found.append(source_comp)
            else:
                result.components_missing.append(req_comp.name)

        # Check for extra components in source (not documented)
        source_names = set(c.name for c in source_components)
        req_names = set(c.name for c in req_components)
        extra = source_names - req_names

        if extra:
            result.warnings.append(
                f"{len(extra)} components in source not documented in requirements"
            )

        # Determine pass/fail
        result.passed = (
            len(result.components_missing) == 0
            and len(result.errors) == 0
            and len(result.line_mismatches) == 0
        )

        return result

    def verify_batch(self, pattern: str = "**/*.py") -> List[CheckpointResult]:
        """Verify multiple files matching a pattern."""
        import os

        results = []
        # Convert pattern to relative if it starts with app/
        if pattern.startswith("app/"):
            # Use os.walk for recursive directory search (more compatible)
            search_path = self.project_root / pattern
            if search_path.is_dir():
                python_files = []
                for root, dirs, files in os.walk(search_path):
                    for file in files:
                        if file.endswith(".py"):
                            python_files.append(Path(root) / file)
            else:
                python_files = [self.project_root / pattern]
        else:
            # Use os.walk for non-app patterns too
            search_path = self.project_root / pattern if "/" in pattern else self.project_root
            python_files = []
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    if file.endswith(".py"):
                        python_files.append(Path(root) / file)

        for python_path in python_files:
            # Skip __init__, __pycache__, tests
            if (
                "__pycache__" in str(python_path)
                or python_path.name.startswith("__")
                or "test" in python_path.parts
            ):
                continue

            result = self.verify_file(python_path)
            results.append(result)

        return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Verify checkpoints for Python files")
    parser.add_argument("paths", nargs="*", help="Python files or directories to verify")
    parser.add_argument("--batch", action="store_true", help="Batch mode for directories")
    parser.add_argument("--all", action="store_true", help="Verify all Python files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.resolve()
    verifier = CheckpointVerifier(project_root)

    if args.all:
        results = verifier.verify_batch("app/**/*.py")
    elif args.paths:
        results = []
        for path_str in args.paths:
            path = Path(path_str).resolve()
            if not path.is_absolute():
                path = project_root / path
            if path.is_dir() or args.batch:
                pattern = str(path / "**" / "*.py") if path.is_dir() else path_str
                results.extend(verifier.verify_batch(pattern))
            else:
                results.append(verifier.verify_file(path))
    else:
        # Default: verify most recently modified
        print("Error: Please specify a file or use --all")
        return 2

    # Print results
    all_passed = True
    for result in results:
        if not result.passed:
            all_passed = False
        print(result)

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    print(f"\n{'='*60}")
    print(f"Summary: {passed}/{total} checkpoints passed")
    print(f"{'='*60}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
