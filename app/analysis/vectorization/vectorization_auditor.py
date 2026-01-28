"""
Vectorization auditor for detecting non-vectorized code patterns.

This module provides tools to audit Python code for non-vectorized patterns
that can significantly impact performance in numerical computing and trading
systems. It uses AST (Abstract Syntax Tree) analysis to detect problematic
patterns without executing the code.
"""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.analysis.vectorization.models import (
    VectorizationIssue,
    VectorizationReport,
)
from app.analysis.vectorization.patterns import VectorizationPatterns


class VectorizationAuditor:
    """
    Audit code for vectorization compliance.

    This auditor scans Python source code and detects patterns that indicate
    non-vectorized numerical operations which can cause significant
    performance degradation in trading systems.

    Rules enforced:
    1. No for loops for numerical calculations
    2. Use numpy/pandas vectorized operations
    3. Avoid .apply() on DataFrames (use vectorized ops)
    4. Avoid list comprehensions for numerical work
    5. Use numba JIT for critical loops (when vectorization not possible)

    Attributes:
        exclude_dirs: Directories to exclude from scanning.
        file_patterns: File patterns to include (default: ["*.py"]).
        severity_weights: Weights for different severity levels.

    Examples:
        >>> auditor = VectorizationAuditor()
        >>> report = auditor.audit_directory("app/strategies")
        >>> print(report.get_summary())
    """

    # Default directories to exclude
    DEFAULT_EXCLUDE_DIRS = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        "dist",
        "build",
        "*.egg-info",
        ".pytest_cache",
        ".mypy_cache",
        "tests",
        "migrations",
    }

    def __init__(
        self,
        exclude_dirs: set[str] | None = None,
        file_patterns: list[str] | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize the vectorization auditor.

        Args:
            exclude_dirs: Directories to exclude from scanning.
            file_patterns: File patterns to include (default: ["*.py"]).
            verbose: Whether to print detailed information.
        """
        self.exclude_dirs = exclude_dirs or self.DEFAULT_EXCLUDE_DIRS.copy()
        self.file_patterns = file_patterns or ["*.py"]
        self.verbose = verbose
        self.patterns = VectorizationPatterns()

    def audit_file(
        self,
        file_path: str | Path,
    ) -> list[VectorizationIssue]:
        """Audit a Python file for vectorization issues.

        Args:
            file_path: Path to the Python file to audit.

        Returns:
            List of VectorizationIssue objects found.

        Raises:
            FileNotFoundError: If the file does not exist.
            SyntaxError: If the file has invalid Python syntax.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        # Read and parse the file
        try:
            with file_path.open("r", encoding="utf-8") as f:
                source_code = f.read()
                tree = ast.parse(source_code, filename=str(file_path))
        except SyntaxError as e:
            msg = f"Syntax error in {file_path}: {e}"
            raise SyntaxError(msg) from e

        issues: list[VectorizationIssue] = []

        # Run all checks
        issues.extend(self._check_for_loops(tree, str(file_path), source_code))
        issues.extend(self._check_apply_usage(tree, str(file_path), source_code))
        issues.extend(self._check_iterrows(tree, str(file_path), source_code))
        issues.extend(self._check_list_comprehensions(tree, str(file_path), source_code))
        issues.extend(self._check_enumerate_loops(tree, str(file_path), source_code))
        issues.extend(self._check_range_len_loops(tree, str(file_path), source_code))
        issues.extend(self._check_while_loops(tree, str(file_path), source_code))

        return issues

    def audit_directory(
        self,
        directory: str | Path,
        pattern: str = "*.py",
        recursive: bool = True,
    ) -> VectorizationReport:
        """Audit all Python files in directory.

        Args:
            directory: Directory path to scan.
            pattern: File pattern to match (default: "*.py").
            recursive: Whether to scan recursively (default: True).

        Returns:
            VectorizationReport with all findings.
        """
        start_time = time.time()
        directory = Path(directory)

        if not directory.exists():
            msg = f"Directory not found: {directory}"
            raise FileNotFoundError(msg)

        # Find all Python files
        if recursive:
            python_files = [
                f
                for f in directory.rglob(pattern)
                if not any(excluded in f.parts for excluded in self.exclude_dirs)
            ]
        else:
            python_files = list(directory.glob(pattern))

        # Collect all issues
        all_issues: list[VectorizationIssue] = []
        issues_by_file: dict[str, int] = {}

        for file_path in python_files:
            try:
                file_issues = self.audit_file(file_path)
                all_issues.extend(file_issues)
                if file_issues:
                    issues_by_file[str(file_path)] = len(file_issues)
            except (SyntaxError, UnicodeDecodeError):
                # Skip files that can't be parsed
                continue

        # Calculate statistics
        total_files = len(python_files)
        total_issues = len(all_issues)
        scan_duration = time.time() - start_time

        # Count by type and severity
        issues_by_type: dict[str, int] = {}
        issues_by_severity: dict[str, int] = {}

        for issue in all_issues:
            issues_by_type[issue.issue_type] = issues_by_type.get(issue.issue_type, 0) + 1
            issues_by_severity[issue.severity] = issues_by_severity.get(issue.severity, 0) + 1

        # Calculate score
        vectorization_score = self.calculate_score(all_issues)

        # Generate recommendations
        recommendations = self._generate_recommendations(all_issues)

        # Get top offenders
        top_offenders = sorted(
            issues_by_file.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return VectorizationReport(
            total_files_scanned=total_files,
            total_issues_found=total_issues,
            issues_by_type=issues_by_type,
            issues_by_severity=issues_by_severity,
            issues=all_issues,
            vectorization_score=vectorization_score,
            recommendations=recommendations,
            scan_duration=scan_duration,
            files_with_issues=len(issues_by_file),
            top_offenders=top_offenders,
        )

    def _check_for_loops(
        self,
        tree: ast.AST,
        file_path: str,
        source_code: str,
    ) -> list[VectorizationIssue]:
        """Check for for loops that should be vectorized.

        Patterns to flag:
        - for i in range(len(array)):
        - for row in df.iterrows():
        - for idx, val in enumerate(series):
        - for x in array: (when doing numerical calculations)

        Args:
            tree: AST of the code.
            file_path: Path to the file.
            source_code: Original source code for context.

        Returns:
            List of VectorizationIssue objects.
        """
        issues: list[VectorizationIssue] = []

        class ForLoopVisitor(ast.NodeVisitor):
            """Visitor to detect problematic for loops."""

            def __init__(self, outer: VectorizationAuditor) -> None:
                self.outer = outer
                self.issues: list[VectorizationIssue] = []

            def visit_For(self, node: ast.For) -> None:
                # Check for range(len(array)) or range(len(array) +/- N) pattern
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                        if node.iter.args:
                            # Check if it's range(len(x)) or range(len(x) +/- N)
                            first_arg = node.iter.args[0]
                            if isinstance(first_arg, ast.Call):
                                if (
                                    isinstance(first_arg.func, ast.Name)
                                    and first_arg.func.id == "len"
                                ):
                                    self.issues.append(
                                        VectorizationIssue(
                                            file_path=file_path,
                                            line_number=node.lineno,
                                            issue_type="range_len",
                                            severity="high",
                                            description="For loop using range(len(array)) pattern",
                                            suggestion="Use vectorized operations instead of indexing",
                                            vectorized_alternative="# Instead of:\n"
                                            "# for i in range(len(arr)):\n"
                                            "#     result[i] = arr[i] * 2\n"
                                            "# Use:\n"
                                            "# result = arr * 2",
                                        )
                                    )
                            # Also check for range() calls with any len() inside
                            if self._contains_len_call(first_arg):
                                self.issues.append(
                                    VectorizationIssue(
                                        file_path=file_path,
                                        line_number=node.lineno,
                                        issue_type="range_len",
                                        severity="high",
                                        description="For loop using range with len() pattern",
                                        suggestion="Use vectorized operations instead of indexing",
                                        vectorized_alternative="# Instead of:\n"
                                        "# for i in range(len(arr)):\n"
                                        "#     result[i] = arr[i] * 2\n"
                                        "# Use:\n"
                                        "# result = arr * 2",
                                    )
                                )

                # Check for array indexing operations in loop body (subscript access)
                has_subscript_ops = self._check_for_subscript_operations(node)
                if has_subscript_ops:
                    self.issues.append(
                        VectorizationIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            issue_type="for_loop",
                            severity="medium",
                            description="For loop with array indexing that could be vectorized",
                            suggestion="Consider using NumPy vectorized operations",
                            vectorized_alternative=self.outer.patterns.get_suggestion_for_issue(
                                "for_loop"
                            ),
                        )
                    )

                # Check for numerical operations in loop body
                has_numerical_ops = self._check_for_numerical_operations(node)
                if has_numerical_ops and not has_subscript_ops:
                    # Check if it's a simple iteration that could be vectorized
                    if isinstance(node.iter, (ast.Name, ast.Attribute)):
                        self.issues.append(
                            VectorizationIssue(
                                file_path=file_path,
                                line_number=node.lineno,
                                issue_type="for_loop",
                                severity="low",
                                description="For loop with numerical operations that could be vectorized",
                                suggestion="Consider using NumPy vectorized operations",
                                vectorized_alternative=self.outer.patterns.get_suggestion_for_issue(
                                    "for_loop"
                                ),
                            )
                        )

                self.generic_visit(node)

            def _contains_len_call(self, node: ast.AST) -> bool:
                """Check if AST node contains a len() call."""
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "len":
                        return True
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name) and child.func.id == "len":
                            return True
                return False

            def _check_for_subscript_operations(self, node: ast.For) -> bool:
                """Check if loop body contains array subscript operations."""
                for child in ast.walk(node):
                    if isinstance(child, ast.Subscript):
                        # Check if subscripting with the loop variable
                        if isinstance(child.slice, ast.Name):
                            # Check if this name matches loop target
                            for target in ast.walk(node.target):
                                if isinstance(target, ast.Name):
                                    if child.slice.id == target.id:
                                        return True
                        # Also check for subscript with ast.Constant (integer indexing)
                        if isinstance(child.slice, (ast.Constant, ast.Num)):
                            return True
                return False

            def _check_for_numerical_operations(self, node: ast.For) -> bool:
                """Check if loop body contains numerical operations."""
                for child in ast.walk(node):
                    if isinstance(child, (ast.BinOp, ast.AugAssign)):
                        # Check if operating on numbers/arrays
                        if isinstance(child.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
                            return True
                return False

        visitor = ForLoopVisitor(self)
        visitor.visit(tree)
        return visitor.issues

    def _check_apply_usage(
        self,
        tree: ast.AST,
        file_path: str,
        source_code: str,
    ) -> list[VectorizationIssue]:
        """Check for .apply() usage that could be vectorized.

        .apply() is often slower than vectorized operations.

        Bad: df['col'].apply(lambda x: x * 2)
        Good: df['col'] * 2

        Args:
            tree: AST of the code.
            file_path: Path to the file.
            source_code: Original source code for context.

        Returns:
            List of VectorizationIssue objects.
        """
        issues: list[VectorizationIssue] = []

        class ApplyVisitor(ast.NodeVisitor):
            """Visitor to detect .apply() usage."""

            def visit_Call(self, node: ast.Call) -> None:
                # Check for .apply() calls
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "apply":
                        issues.append(
                            VectorizationIssue(
                                file_path=file_path,
                                line_number=node.lineno,
                                issue_type="apply",
                                severity="high",
                                description="DataFrame/Series .apply() usage - consider vectorized alternative",
                                suggestion="Use vectorized operations instead of .apply()",
                                vectorized_alternative="# Instead of:\n"
                                "# df['col'].apply(lambda x: x * 2)\n"
                                "# Use:\n"
                                "# df['col'] * 2",
                            )
                        )
                self.generic_visit(node)

        visitor = ApplyVisitor()
        visitor.visit(tree)
        return issues

    def _check_iterrows(
        self,
        tree: ast.AST,
        file_path: str,
        source_code: str,
    ) -> list[VectorizationIssue]:
        """Check for .iterrows() usage which is very slow.

        Args:
            tree: AST of the code.
            file_path: Path to the file.
            source_code: Original source code for context.

        Returns:
            List of VectorizationIssue objects.
        """
        issues: list[VectorizationIssue] = []

        class IterrowsVisitor(ast.NodeVisitor):
            """Visitor to detect .iterrows() usage."""

            def visit_Call(self, node: ast.Call) -> None:
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("iterrows", "itertuples"):
                        severity = "critical" if node.func.attr == "iterrows" else "high"
                        issues.append(
                            VectorizationIssue(
                                file_path=file_path,
                                line_number=node.lineno,
                                issue_type=(
                                    "iterrows" if node.func.attr == "iterrows" else "itertuples"
                                ),
                                severity=severity,
                                description=f".{node.func.attr}() usage - extremely slow, avoid",
                                suggestion="Use vectorized operations or .values instead",
                                vectorized_alternative="# Instead of:\n"
                                "# for idx, row in df.iterrows():\n"
                                "#     print(row['col'])\n"
                                "# Use:\n"
                                "# print(df['col'].values)",
                            )
                        )
                self.generic_visit(node)

        visitor = IterrowsVisitor()
        visitor.visit(tree)
        return issues

    def _check_list_comprehensions(
        self,
        tree: ast.AST,
        file_path: str,
        source_code: str,
    ) -> list[VectorizationIssue]:
        """Check for list comprehensions that could be vectorized.

        Args:
            tree: AST of the code.
            file_path: Path to the file.
            source_code: Original source code for context.

        Returns:
            List of VectorizationIssue objects.
        """
        issues: list[VectorizationIssue] = []

        class ListCompVisitor(ast.NodeVisitor):
            """Visitor to detect problematic list comprehensions."""

            def visit_ListComp(self, node: ast.ListComp) -> None:
                # Check if it's doing numerical operations
                has_numerical_ops = False
                for child in ast.walk(node):
                    if isinstance(child, ast.BinOp):
                        has_numerical_ops = True
                        break

                if has_numerical_ops:
                    issues.append(
                        VectorizationIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            issue_type="list_comp",
                            severity="low",
                            description="List comprehension with numerical operations - consider NumPy",
                            suggestion="Use NumPy vectorized operations for better performance",
                            vectorized_alternative="# Instead of:\n"
                            "# [x * 2 for x in arr]\n"
                            "# Use:\n"
                            "# arr * 2",
                        )
                    )
                self.generic_visit(node)

        visitor = ListCompVisitor()
        visitor.visit(tree)
        return issues

    def _check_enumerate_loops(
        self,
        tree: ast.AST,
        file_path: str,
        source_code: str,
    ) -> list[VectorizationIssue]:
        """Check for enumerate() loops that could be vectorized.

        Args:
            tree: AST of the code.
            file_path: Path to the file.
            source_code: Original source code for context.

        Returns:
            List of VectorizationIssue objects.
        """
        issues: list[VectorizationIssue] = []

        class EnumerateVisitor(ast.NodeVisitor):
            """Visitor to detect enumerate loops."""

            def visit_For(self, node: ast.For) -> None:
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "enumerate":
                        issues.append(
                            VectorizationIssue(
                                file_path=file_path,
                                line_number=node.lineno,
                                issue_type="enumerate",
                                severity="medium",
                                description="For loop with enumerate() - consider vectorized alternative",
                                suggestion="Use NumPy operations or direct array operations",
                                vectorized_alternative="# Instead of:\n"
                                "# for i, x in enumerate(arr):\n"
                                "#     result[i] = x * 2\n"
                                "# Use:\n"
                                "# result = arr * 2",
                            )
                        )
                self.generic_visit(node)

        visitor = EnumerateVisitor()
        visitor.visit(tree)
        return issues

    def _check_range_len_loops(
        self,
        tree: ast.AST,
        file_path: str,
        source_code: str,
    ) -> list[VectorizationIssue]:
        """Check for range(len()) loops specifically.

        Args:
            tree: AST of the code.
            file_path: Path to the file.
            source_code: Original source code for context.

        Returns:
            List of VectorizationIssue objects.
        """
        issues: list[VectorizationIssue] = []

        class RangeLenVisitor(ast.NodeVisitor):
            """Visitor to detect range(len()) patterns."""

            def visit_For(self, node: ast.For) -> None:
                if isinstance(node.iter, ast.Call):
                    if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                        if node.iter.args:
                            first_arg = node.iter.args[0]
                            if isinstance(first_arg, ast.Call):
                                if (
                                    isinstance(first_arg.func, ast.Name)
                                    and first_arg.func.id == "len"
                                ):
                                    issues.append(
                                        VectorizationIssue(
                                            file_path=file_path,
                                            line_number=node.lineno,
                                            issue_type="range_len",
                                            severity="high",
                                            description="range(len()) pattern - use direct array operations",
                                            suggestion="Replace with vectorized NumPy operations",
                                            vectorized_alternative="# Instead of:\n"
                                            "# for i in range(len(arr)):\n"
                                            "#     arr[i] *= 2\n"
                                            "# Use:\n"
                                            "# arr *= 2",
                                        )
                                    )
                self.generic_visit(node)

        visitor = RangeLenVisitor()
        visitor.visit(tree)
        return issues

    def _check_while_loops(
        self,
        tree: ast.AST,
        file_path: str,
        source_code: str,
    ) -> list[VectorizationIssue]:
        """Check for while loops with numerical operations.

        Args:
            tree: AST of the code.
            file_path: Path to the file.
            source_code: Original source code for context.

        Returns:
            List of VectorizationIssue objects.
        """
        issues: list[VectorizationIssue] = []

        class WhileLoopVisitor(ast.NodeVisitor):
            """Visitor to detect problematic while loops."""

            def visit_While(self, node: ast.While) -> None:
                # Check for numerical operations in loop body
                has_numerical_ops = False
                for child in ast.walk(node):
                    if isinstance(child, ast.BinOp):
                        if isinstance(child.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
                            has_numerical_ops = True
                            break

                if has_numerical_ops:
                    issues.append(
                        VectorizationIssue(
                            file_path=file_path,
                            line_number=node.lineno,
                            issue_type="while_loop",
                            severity="medium",
                            description="While loop with numerical operations - review for vectorization",
                            suggestion="Consider if the loop can be replaced with vectorized operations",
                            vectorized_alternative="# While loops with numerical operations\n"
                            "# should be reviewed for vectorization opportunities.\n"
                            "# Consider using NumPy's vectorized operations.",
                        )
                    )
                self.generic_visit(node)

        visitor = WhileLoopVisitor()
        visitor.visit(tree)
        return issues

    def calculate_score(
        self,
        issues: list[VectorizationIssue],
    ) -> Decimal:
        """Calculate vectorization score (0-100).

        Score = 100 - (critical × 10) - (high × 5) - (medium × 2) - (low × 1)

        Args:
            issues: List of vectorization issues.

        Returns:
            Score as Decimal between 0 and 100.
        """
        if not issues:
            return Decimal("100.0")

        # Calculate penalty
        penalty = 0
        for issue in issues:
            penalty += issue.get_severity_weight()

        # Calculate score (ensure it's not negative)
        score = max(0, 100 - penalty)

        return Decimal(str(score))

    def _generate_recommendations(
        self,
        issues: list[VectorizationIssue],
    ) -> list[str]:
        """Generate actionable recommendations based on findings.

        Args:
            issues: List of vectorization issues.

        Returns:
            List of recommendation strings.
        """
        recommendations: list[str] = []

        if not issues:
            recommendations.append("Excellent! No vectorization issues found.")
            return recommendations

        # Count by type
        issues_by_type: dict[str, int] = {}
        for issue in issues:
            issues_by_type[issue.issue_type] = issues_by_type.get(issue.issue_type, 0) + 1

        # Generate recommendations based on issue types
        if issues_by_type.get("for_loop", 0) > 5:
            recommendations.append(
                f"High number of for loops ({issues_by_type['for_loop']}) found. "
                "Prioritize refactoring these to vectorized operations."
            )

        if issues_by_type.get("iterrows", 0) > 0:
            recommendations.append(
                f"Critical: {issues_by_type['iterrows']} iterrows() usage found. "
                "This is extremely slow and should be replaced immediately."
            )

        if issues_by_type.get("apply", 0) > 3:
            recommendations.append(
                f"Multiple .apply() calls ({issues_by_type['apply']}) found. "
                "Consider using vectorized operations for significant performance gains."
            )

        # Check for critical issues
        critical_count = sum(1 for issue in issues if issue.severity == "critical")
        if critical_count > 0:
            recommendations.append(
                f"{critical_count} critical issues found that should be addressed immediately."
            )

        # General recommendation
        if len(issues) > 20:
            recommendations.append(
                "Large number of vectorization issues detected. "
                "Consider a systematic refactoring effort prioritized by criticality."
            )

        return recommendations

    def audit_code_snippet(
        self,
        code: str,
        filename: str = "<snippet>",
    ) -> list[VectorizationIssue]:
        """Audit a code snippet (string) for vectorization issues.

        Args:
            code: Python code as string.
            filename: Optional filename for reporting (default: "<snippet>").

        Returns:
            List of VectorizationIssue objects.
        """
        try:
            tree = ast.parse(code, filename=filename)
        except SyntaxError as e:
            msg = f"Syntax error in code snippet: {e}"
            raise SyntaxError(msg) from e

        issues: list[VectorizationIssue] = []

        issues.extend(self._check_for_loops(tree, filename, code))
        issues.extend(self._check_apply_usage(tree, filename, code))
        issues.extend(self._check_iterrows(tree, filename, code))
        issues.extend(self._check_list_comprehensions(tree, filename, code))
        issues.extend(self._check_enumerate_loops(tree, filename, code))
        issues.extend(self._check_range_len_loops(tree, filename, code))
        issues.extend(self._check_while_loops(tree, filename, code))

        return issues
