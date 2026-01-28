"""
Data models for vectorization verification.

This module defines the core data structures used throughout the vectorization
verification system, including issues, reports, and benchmark results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class VectorizationIssue:
    """Non-vectorized code issue found during audit.

    Attributes:
        file_path: Path to the file containing the issue
        line_number: Line number where the issue was found
        issue_type: Type of issue (e.g., "for_loop", "list_comp", "apply")
        severity: Severity level ("critical", "high", "medium", "low")
        description: Human-readable description of the issue
        suggestion: Suggestion for fixing the issue
        vectorized_alternative: Code snippet showing vectorized alternative
        code_snippet: Optional snippet of the problematic code
        context_lines: Optional surrounding lines for context
    """

    file_path: str
    line_number: int
    issue_type: str
    severity: str
    description: str
    suggestion: str
    vectorized_alternative: str
    code_snippet: str | None = None
    context_lines: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate the issue data.

        Raises:
            ValueError: If severity or issue_type is invalid.
        """
        valid_severities = {"critical", "high", "medium", "low"}
        if self.severity not in valid_severities:
            msg = f"Invalid severity: {self.severity}. Must be one of {valid_severities}"
            raise ValueError(msg)

        valid_types = {
            "for_loop",
            "list_comp",
            "apply",
            "iterrows",
            "itertuples",
            "enumerate",
            "range_len",
            "while_loop",
            "nested_loop",
        }
        if self.issue_type not in valid_types:
            msg = f"Invalid issue_type: {self.issue_type}. Must be one of {valid_types}"
            raise ValueError(msg)

    def get_severity_weight(self) -> int:
        """Get the weight of this issue for score calculation.

        Returns:
            Weight multiplier for scoring (critical=10, high=5, medium=2, low=1).
        """
        weights = {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 1,
        }
        return weights.get(self.severity, 1)

    def get_display_summary(self) -> str:
        """Get a concise display summary of the issue.

        Returns:
            Formatted summary string.
        """
        return (
            f"[{self.severity.upper()}] {self.file_path}:{self.line_number} "
            f"- {self.issue_type}: {self.description}"
        )


@dataclass
class VectorizationReport:
    """Vectorization audit report for a codebase.

    Attributes:
        total_files_scanned: Number of Python files scanned
        total_issues_found: Total number of vectorization issues found
        issues_by_type: Dictionary counting issues by type
        issues_by_severity: Dictionary counting issues by severity
        issues: List of all issues found
        vectorization_score: Overall score from 0-100 (higher is better)
        recommendations: List of actionable recommendations
        scan_duration: Time taken to perform the scan in seconds
        files_with_issues: Number of files that have at least one issue
        top_offenders: List of files with the most issues
    """

    total_files_scanned: int
    total_issues_found: int
    issues_by_type: dict[str, int]
    issues_by_severity: dict[str, int]
    issues: list[VectorizationIssue]
    vectorization_score: Decimal
    recommendations: list[str]
    scan_duration: float = 0.0
    files_with_issues: int = 0
    top_offenders: list[tuple[str, int]] = field(default_factory=list)

    def get_grade(self) -> str:
        """Get letter grade based on vectorization score.

        Returns:
            Letter grade (A, B, C, D, or F).
        """
        score = float(self.vectorization_score)
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 60:
            return "C"
        if score >= 40:
            return "D"
        return "F"

    def get_summary(self) -> str:
        """Get a human-readable summary of the report.

        Returns:
            Formatted summary string.
        """
        grade = self.get_grade()
        return (
            f"Vectorization Audit Report\n"
            f"{'=' * 40}\n"
            f"Score: {self.vectorization_score:.1f}/100 (Grade: {grade})\n"
            f"Files Scanned: {self.total_files_scanned}\n"
            f"Files with Issues: {self.files_with_issues}\n"
            f"Total Issues: {self.total_issues_found}\n"
            f"Scan Duration: {self.scan_duration:.2f}s\n\n"
            f"Issues by Severity:\n"
            f"  Critical: {self.issues_by_severity.get('critical', 0)}\n"
            f"  High: {self.issues_by_severity.get('high', 0)}\n"
            f"  Medium: {self.issues_by_severity.get('medium', 0)}\n"
            f"  Low: {self.issues_by_severity.get('low', 0)}\n"
        )

    def get_top_issues(self, limit: int = 10) -> list[VectorizationIssue]:
        """Get the highest priority issues.

        Args:
            limit: Maximum number of issues to return.

        Returns:
            List of issues sorted by severity and type.
        """
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_issues = sorted(
            self.issues,
            key=lambda x: (severity_order.get(x.severity, 4), x.issue_type),
        )
        return sorted_issues[:limit]

    def is_compliant(self, threshold: float = 80.0) -> bool:
        """Check if the codebase meets the vectorization compliance threshold.

        Args:
            threshold: Minimum score required for compliance (default: 80.0).

        Returns:
            True if the score meets or exceeds the threshold.
        """
        return float(self.vectorization_score) >= threshold


@dataclass
class BenchmarkResult:
    """Result of benchmarking vectorized vs non-vectorized code.

    Attributes:
        function_name: Name of the function being benchmarked
        vectorized_time: Execution time for vectorized version (seconds)
        non_vectorized_time: Execution time for non-vectorized version (seconds)
        speedup: Speedup factor (non_vectorized_time / vectorized_time)
        n_elements: Number of elements processed
        per_element_time_vectorized: Time per element for vectorized (ns)
        per_element_time_non_vectorized: Time per element for non-vectorized (ns)
        memory_usage_vectorized: Optional memory usage for vectorized (bytes)
        memory_usage_non_vectorized: Optional memory usage for non-vectorized (bytes)
        timestamp: When the benchmark was run
    """

    function_name: str
    vectorized_time: float
    non_vectorized_time: float
    speedup: float
    n_elements: int
    per_element_time_vectorized: float
    per_element_time_non_vectorized: float
    memory_usage_vectorized: int | None = None
    memory_usage_non_vectorized: int | None = None
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        """Validate and calculate derived fields.

        Raises:
            ValueError: If times are invalid or speedup cannot be calculated.
        """
        if self.vectorized_time <= 0:
            msg = f"vectorized_time must be positive, got {self.vectorized_time}"
            raise ValueError(msg)
        if self.non_vectorized_time <= 0:
            msg = f"non_vectorized_time must be positive, got {self.non_vectorized_time}"
            raise ValueError(msg)
        if self.n_elements <= 0:
            msg = f"n_elements must be positive, got {self.n_elements}"
            raise ValueError(msg)

        # Calculate speedup if not provided
        if self.speedup == 0:
            object.__setattr__(self, "speedup", self.non_vectorized_time / self.vectorized_time)

    def get_summary(self) -> str:
        """Get a human-readable summary of the benchmark result.

        Returns:
            Formatted summary string.
        """
        speedup_str = (
            f"{self.speedup:.2f}x" if self.speedup >= 1 else f"{1/self.speedup:.2f}x slower"
        )

        return (
            f"Benchmark: {self.function_name}\n"
            f"  Elements: {self.n_elements:,}\n"
            f"  Vectorized: {self.vectorized_time * 1000:.4f}ms "
            f"({self.per_element_time_vectorized:.2f} ns/element)\n"
            f"  Non-Vectorized: {self.non_vectorized_time * 1000:.4f}ms "
            f"({self.per_element_time_non_vectorized:.2f} ns/element)\n"
            f"  Speedup: {speedup_str}\n"
        )

    def get_performance_grade(self) -> str:
        """Get a performance grade based on speedup.

        Returns:
            Letter grade (A+ to F) based on speedup factor.
        """
        if self.speedup >= 100:
            return "A+"
        if self.speedup >= 50:
            return "A"
        if self.speedup >= 20:
            return "B"
        if self.speedup >= 10:
            return "C"
        if self.speedup >= 2:
            return "D"
        return "F"

    def is_significant_speedup(self, threshold: float = 2.0) -> bool:
        """Check if the speedup is statistically significant.

        Args:
            threshold: Minimum speedup to consider significant (default: 2.0).

        Returns:
            True if speedup meets or exceeds threshold.
        """
        return self.speedup >= threshold

    def to_dict(self) -> dict[str, Any]:
        """Convert the benchmark result to a dictionary.

        Returns:
            Dictionary representation of the result.
        """
        return {
            "function_name": self.function_name,
            "vectorized_time": self.vectorized_time,
            "non_vectorized_time": self.non_vectorized_time,
            "speedup": self.speedup,
            "n_elements": self.n_elements,
            "per_element_time_vectorized": self.per_element_time_vectorized,
            "per_element_time_non_vectorized": self.per_element_time_non_vectorized,
            "memory_usage_vectorized": self.memory_usage_vectorized,
            "memory_usage_non_vectorized": self.memory_usage_non_vectorized,
            "timestamp": self.timestamp,
            "performance_grade": self.get_performance_grade(),
        }


@dataclass
class CodeSnippet:
    """Represents a code snippet with context.

    Attributes:
        code: The actual code snippet
        line_start: Starting line number
        line_end: Ending line number
        file_path: Path to the source file
        language: Programming language (default: "python")
    """

    code: str
    line_start: int
    line_end: int
    file_path: str
    language: str = "python"

    def get_relative_path(self, base_path: str) -> str:
        """Get the file path relative to a base path.

        Args:
            base_path: Base directory path.

        Returns:
            Relative file path.
        """
        try:
            return str(self.file_path).replace(base_path, "").lstrip("/")
        except Exception:
            return self.file_path

    def get_formatted_display(self) -> str:
        """Get formatted display string with line numbers.

        Returns:
            Formatted code snippet with line numbers.
        """
        lines = self.code.split("\n")
        formatted_lines = []
        width = len(str(self.line_end))

        for i, line in enumerate(lines):
            line_num = self.line_start + i
            formatted_lines.append(f"{line_num:>{width}} | {line}")

        return "\n".join(formatted_lines)
