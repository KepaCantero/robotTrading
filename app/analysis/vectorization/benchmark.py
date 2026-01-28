"""
Benchmarking utilities for vectorized vs non-vectorized code.

This module provides comprehensive benchmarking tools to compare the performance
of vectorized and non-vectorized implementations of common numerical operations
found in algorithmic trading systems.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

from app.analysis.vectorization.models import BenchmarkResult


class VectorizationBenchmark:
    """
    Benchmark vectorized vs non-vectorized implementations.

    This class provides methods to benchmark common numerical operations
    and demonstrate the performance benefits of vectorization. It includes
    benchmarks for operations commonly used in trading systems.

    Attributes:
        warmup_iterations: Number of warmup iterations before benchmarking.
        benchmark_iterations: Number of iterations for timing.
        verbose: Whether to print detailed benchmark information.

    Examples:
        >>> benchmark = VectorizationBenchmark()
        >>> result = benchmark.benchmark_sum(n_elements=1_000_000)
        >>> print(result.get_summary())
    """

    def __init__(
        self,
        warmup_iterations: int = 3,
        benchmark_iterations: int = 10,
        verbose: bool = False,
    ) -> None:
        """Initialize the benchmark suite.

        Args:
            warmup_iterations: Number of warmup iterations (default: 3).
            benchmark_iterations: Number of timing iterations (default: 10).
            verbose: Whether to print detailed information (default: False).
        """
        self.warmup_iterations = warmup_iterations
        self.benchmark_iterations = benchmark_iterations
        self.verbose = verbose

    def _time_function(
        self,
        func: Callable[[], Any],
        warmup: bool = True,
    ) -> float:
        """Time a function with warmup.

        Args:
            func: Function to time.
            warmup: Whether to perform warmup iterations (default: True).

        Returns:
            Average execution time in seconds.
        """
        # Warmup
        if warmup:
            for _ in range(self.warmup_iterations):
                func()

        # Benchmark
        times: list[float] = []
        for _ in range(self.benchmark_iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times.append(end - start)

        # Return average time
        return np.mean(times)

    def benchmark_sum(
        self,
        n_elements: int = 1_000_000,
    ) -> BenchmarkResult:
        """Benchmark array sum operation.

        Summing arrays is one of the most fundamental operations in
        numerical computing and provides a clear demonstration of
        vectorization benefits.

        Args:
            n_elements: Number of elements to sum (default: 1,000,000).

        Returns:
            BenchmarkResult with timing information.
        """
        # Generate test data
        np.random.seed(42)
        data = np.random.randn(n_elements)

        # Non-vectorized implementation
        def sum_non_vectorized() -> float:
            total = 0.0
            for i in range(len(data)):
                total += data[i]
            return total

        # Vectorized implementation
        def sum_vectorized() -> float:
            return float(np.sum(data))

        # Time both implementations
        non_vectorized_time = self._time_function(sum_non_vectorized)
        vectorized_time = self._time_function(sum_vectorized)

        # Calculate speedup
        speedup = non_vectorized_time / vectorized_time

        # Calculate per-element times (in nanoseconds)
        per_element_nv = (non_vectorized_time / n_elements) * 1e9
        per_element_v = (vectorized_time / n_elements) * 1e9

        if self.verbose:
            print(f"Sum benchmark (n={n_elements:,}):")
            print(f"  Non-vectorized: {non_vectorized_time*1000:.4f}ms")
            print(f"  Vectorized: {vectorized_time*1000:.4f}ms")
            print(f"  Speedup: {speedup:.2f}x")

        return BenchmarkResult(
            function_name="array_sum",
            vectorized_time=vectorized_time,
            non_vectorized_time=non_vectorized_time,
            speedup=speedup,
            n_elements=n_elements,
            per_element_time_vectorized=per_element_v,
            per_element_time_non_vectorized=per_element_nv,
            timestamp=time.time(),
        )

    def benchmark_ewm_calculate(
        self,
        n_elements: int = 100_000,
        span: int = 20,
    ) -> BenchmarkResult:
        """Benchmark exponential weighted mean calculation.

        EWM is critical for many trading indicators including
        exponential moving averages and EWMA volatility.

        Args:
            n_elements: Number of elements (default: 100,000).
            span: Span parameter for EWM (default: 20).

        Returns:
            BenchmarkResult with timing information.
        """
        # Generate test data
        np.random.seed(42)
        data = pd.Series(np.random.randn(n_elements))

        # Non-vectorized implementation
        def ewm_non_vectorized() -> pd.Series:
            alpha = 2.0 / (span + 1)
            result = pd.Series(np.nan, index=data.index)
            if len(data) > 0:
                result.iloc[0] = data.iloc[0]
                for i in range(1, len(data)):
                    result.iloc[i] = alpha * data.iloc[i] + (1 - alpha) * result.iloc[i - 1]
            return result

        # Vectorized implementation
        def ewm_vectorized() -> pd.Series:
            return data.ewm(span=span).mean()

        # Warmup and time
        non_vectorized_time = self._time_function(ewm_non_vectorized)
        vectorized_time = self._time_function(ewm_vectorized)

        speedup = non_vectorized_time / vectorized_time
        per_element_nv = (non_vectorized_time / n_elements) * 1e9
        per_element_v = (vectorized_time / n_elements) * 1e9

        if self.verbose:
            print(f"EWM benchmark (n={n_elements:,}, span={span}):")
            print(f"  Non-vectorized: {non_vectorized_time*1000:.4f}ms")
            print(f"  Vectorized: {vectorized_time*1000:.4f}ms")
            print(f"  Speedup: {speedup:.2f}x")

        return BenchmarkResult(
            function_name="ewm_mean",
            vectorized_time=vectorized_time,
            non_vectorized_time=non_vectorized_time,
            speedup=speedup,
            n_elements=n_elements,
            per_element_time_vectorized=per_element_v,
            per_element_time_non_vectorized=per_element_nv,
            timestamp=time.time(),
        )

    def benchmark_rolling_calculation(
        self,
        n_elements: int = 50_000,
        window: int = 20,
    ) -> BenchmarkResult:
        """Benchmark rolling window calculation.

        Rolling calculations are ubiquitous in trading for technical
        indicators like moving averages, rolling volatility, etc.

        Args:
            n_elements: Number of elements (default: 50,000).
            window: Rolling window size (default: 20).

        Returns:
            BenchmarkResult with timing information.
        """
        # Generate test data
        np.random.seed(42)
        data = pd.Series(np.random.randn(n_elements))

        # Non-vectorized implementation
        def rolling_non_vectorized() -> list[float]:
            result: list[float] = []
            for i in range(window - 1, len(data)):
                window_data = data.iloc[i - window + 1 : i + 1]
                result.append(float(window_data.mean()))
            return result

        # Vectorized implementation
        def rolling_vectorized() -> pd.Series:
            return data.rolling(window).mean()

        # Time both implementations
        non_vectorized_time = self._time_function(rolling_non_vectorized)
        vectorized_time = self._time_function(rolling_vectorized)

        speedup = non_vectorized_time / vectorized_time
        per_element_nv = (non_vectorized_time / n_elements) * 1e9
        per_element_v = (vectorized_time / n_elements) * 1e9

        if self.verbose:
            print(f"Rolling benchmark (n={n_elements:,}, window={window}):")
            print(f"  Non-vectorized: {non_vectorized_time*1000:.4f}ms")
            print(f"  Vectorized: {vectorized_time*1000:.4f}ms")
            print(f"  Speedup: {speedup:.2f}x")

        return BenchmarkResult(
            function_name="rolling_mean",
            vectorized_time=vectorized_time,
            non_vectorized_time=non_vectorized_time,
            speedup=speedup,
            n_elements=n_elements,
            per_element_time_vectorized=per_element_v,
            per_element_time_non_vectorized=per_element_nv,
            timestamp=time.time(),
        )

    def benchmark_correlation(
        self,
        n_elements: int = 10_000,
        n_assets: int = 100,
    ) -> BenchmarkResult:
        """Benchmark correlation matrix calculation.

        Correlation matrices are essential for portfolio optimization
        and risk management.

        Args:
            n_elements: Number of time periods (default: 10,000).
            n_assets: Number of assets (default: 100).

        Returns:
            BenchmarkResult with timing information.
        """
        # Generate test data
        np.random.seed(42)
        data = np.random.randn(n_elements, n_assets)

        # Non-vectorized implementation
        def corr_non_vectorized() -> np.ndarray:
            n = n_assets
            corr_matrix = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    if i == j:
                        corr_matrix[i, j] = 1.0
                    else:
                        corr_matrix[i, j] = np.corrcoef(data[:, i], data[:, j])[0, 1]
            return corr_matrix

        # Vectorized implementation
        def corr_vectorized() -> np.ndarray:
            return np.corrcoef(data, rowvar=False)

        # Time both implementations
        non_vectorized_time = self._time_function(corr_non_vectorized)
        vectorized_time = self._time_function(corr_vectorized)

        speedup = non_vectorized_time / vectorized_time
        per_element_nv = (non_vectorized_time / (n_elements * n_assets)) * 1e9
        per_element_v = (vectorized_time / (n_elements * n_assets)) * 1e9

        if self.verbose:
            print(f"Correlation benchmark (n={n_elements:,}, assets={n_assets}):")
            print(f"  Non-vectorized: {non_vectorized_time*1000:.4f}ms")
            print(f"  Vectorized: {vectorized_time*1000:.4f}ms")
            print(f"  Speedup: {speedup:.2f}x")

        return BenchmarkResult(
            function_name="correlation_matrix",
            vectorized_time=vectorized_time,
            non_vectorized_time=non_vectorized_time,
            speedup=speedup,
            n_elements=n_elements * n_assets,
            per_element_time_vectorized=per_element_v,
            per_element_time_non_vectorized=per_element_nv,
            timestamp=time.time(),
        )

    def benchmark_elementwise_operation(
        self,
        n_elements: int = 1_000_000,
    ) -> BenchmarkResult:
        """Benchmark element-wise arithmetic operations.

        Element-wise operations are the bread and butter of numerical
        computing and show dramatic speedups with vectorization.

        Args:
            n_elements: Number of elements (default: 1,000,000).

        Returns:
            BenchmarkResult with timing information.
        """
        # Generate test data
        np.random.seed(42)
        arr1 = np.random.randn(n_elements)
        arr2 = np.random.randn(n_elements)

        # Non-vectorized implementation
        def elementwise_non_vectorized() -> np.ndarray:
            result = np.zeros_like(arr1)
            for i in range(len(arr1)):
                result[i] = arr1[i] * 2 + arr2[i]
            return result

        # Vectorized implementation
        def elementwise_vectorized() -> np.ndarray:
            return arr1 * 2 + arr2

        # Time both implementations
        non_vectorized_time = self._time_function(elementwise_non_vectorized)
        vectorized_time = self._time_function(elementwise_vectorized)

        speedup = non_vectorized_time / vectorized_time
        per_element_nv = (non_vectorized_time / n_elements) * 1e9
        per_element_v = (vectorized_time / n_elements) * 1e9

        if self.verbose:
            print(f"Elementwise benchmark (n={n_elements:,}):")
            print(f"  Non-vectorized: {non_vectorized_time*1000:.4f}ms")
            print(f"  Vectorized: {vectorized_time*1000:.4f}ms")
            print(f"  Speedup: {speedup:.2f}x")

        return BenchmarkResult(
            function_name="elementwise_arithmetic",
            vectorized_time=vectorized_time,
            non_vectorized_time=non_vectorized_time,
            speedup=speedup,
            n_elements=n_elements,
            per_element_time_vectorized=per_element_v,
            per_element_time_non_vectorized=per_element_nv,
            timestamp=time.time(),
        )

    def benchmark_filtering(
        self,
        n_elements: int = 1_000_000,
    ) -> BenchmarkResult:
        """Benchmark filtering operations with boolean conditions.

        Filtering is commonly used for signal generation and data cleaning.

        Args:
            n_elements: Number of elements (default: 1,000,000).

        Returns:
            BenchmarkResult with timing information.
        """
        # Generate test data
        np.random.seed(42)
        data = np.random.randn(n_elements)

        # Non-vectorized implementation
        def filter_non_vectorized() -> list[float]:
            result: list[float] = []
            for x in data:
                if x > 0:
                    result.append(x * 2)
            return result

        # Vectorized implementation
        def filter_vectorized() -> np.ndarray:
            mask = data > 0
            return data[mask] * 2

        # Time both implementations
        non_vectorized_time = self._time_function(filter_non_vectorized)
        vectorized_time = self._time_function(filter_vectorized)

        speedup = non_vectorized_time / vectorized_time
        per_element_nv = (non_vectorized_time / n_elements) * 1e9
        per_element_v = (vectorized_time / n_elements) * 1e9

        if self.verbose:
            print(f"Filtering benchmark (n={n_elements:,}):")
            print(f"  Non-vectorized: {non_vectorized_time*1000:.4f}ms")
            print(f"  Vectorized: {vectorized_time*1000:.4f}ms")
            print(f"  Speedup: {speedup:.2f}x")

        return BenchmarkResult(
            function_name="boolean_filtering",
            vectorized_time=vectorized_time,
            non_vectorized_time=non_vectorized_time,
            speedup=speedup,
            n_elements=n_elements,
            per_element_time_vectorized=per_element_v,
            per_element_time_non_vectorized=per_element_nv,
            timestamp=time.time(),
        )

    def benchmark_groupby(
        self,
        n_elements: int = 100_000,
        n_groups: int = 50,
    ) -> BenchmarkResult:
        """Benchmark group-by aggregation operations.

        Group-by operations are essential for cross-sectional analysis
        and portfolio attribution.

        Args:
            n_elements: Number of elements (default: 100,000).
            n_groups: Number of groups (default: 50).

        Returns:
            BenchmarkResult with timing information.
        """
        # Generate test data
        np.random.seed(42)
        df = pd.DataFrame(
            {
                "group": np.random.randint(0, n_groups, n_elements),
                "value": np.random.randn(n_elements),
            }
        )

        # Non-vectorized implementation
        def groupby_non_vectorized() -> dict[int, float]:
            result: dict[int, float] = {}
            for group in df["group"].unique():
                subset = df[df["group"] == group]
                result[group] = subset["value"].mean()
            return result

        # Vectorized implementation
        def groupby_vectorized() -> pd.Series:
            return df.groupby("group")["value"].mean()

        # Time both implementations
        non_vectorized_time = self._time_function(groupby_non_vectorized)
        vectorized_time = self._time_function(groupby_vectorized)

        speedup = non_vectorized_time / vectorized_time
        per_element_nv = (non_vectorized_time / n_elements) * 1e9
        per_element_v = (vectorized_time / n_elements) * 1e9

        if self.verbose:
            print(f"GroupBy benchmark (n={n_elements:,}, groups={n_groups}):")
            print(f"  Non-vectorized: {non_vectorized_time*1000:.4f}ms")
            print(f"  Vectorized: {vectorized_time*1000:.4f}ms")
            print(f"  Speedup: {speedup:.2f}x")

        return BenchmarkResult(
            function_name="groupby_aggregation",
            vectorized_time=vectorized_time,
            non_vectorized_time=non_vectorized_time,
            speedup=speedup,
            n_elements=n_elements,
            per_element_time_vectorized=per_element_v,
            per_element_time_non_vectorized=per_element_nv,
            timestamp=time.time(),
        )

    def benchmark_percentage_change(
        self,
        n_elements: int = 100_000,
    ) -> BenchmarkResult:
        """Benchmark percentage change (returns) calculation.

        This is one of the most common operations in trading systems.

        Args:
            n_elements: Number of elements (default: 100,000).

        Returns:
            BenchmarkResult with timing information.
        """
        # Generate test data
        np.random.seed(42)
        prices = pd.Series(100 + np.random.randn(n_elements).cumsum())

        # Non-vectorized implementation
        def pct_change_non_vectorized() -> list[float]:
            result: list[float] = [0.0]
            for i in range(1, len(prices)):
                result.append((prices.iloc[i] - prices.iloc[i - 1]) / prices.iloc[i - 1])
            return result

        # Vectorized implementation
        def pct_change_vectorized() -> pd.Series:
            return prices.pct_change()

        # Time both implementations
        non_vectorized_time = self._time_function(pct_change_non_vectorized)
        vectorized_time = self._time_function(pct_change_vectorized)

        speedup = non_vectorized_time / vectorized_time
        per_element_nv = (non_vectorized_time / n_elements) * 1e9
        per_element_v = (vectorized_time / n_elements) * 1e9

        if self.verbose:
            print(f"Percentage change benchmark (n={n_elements:,}):")
            print(f"  Non-vectorized: {non_vectorized_time*1000:.4f}ms")
            print(f"  Vectorized: {vectorized_time*1000:.4f}ms")
            print(f"  Speedup: {speedup:.2f}x")

        return BenchmarkResult(
            function_name="percentage_change",
            vectorized_time=vectorized_time,
            non_vectorized_time=non_vectorized_time,
            speedup=speedup,
            n_elements=n_elements,
            per_element_time_vectorized=per_element_v,
            per_element_time_non_vectorized=per_element_nv,
            timestamp=time.time(),
        )

    def run_all_benchmarks(
        self,
        n_elements: int | None = None,
    ) -> list[BenchmarkResult]:
        """Run all standard benchmarks.

        Args:
            n_elements: Optional custom size for benchmarks.
                      If None, uses default sizes for each benchmark.

        Returns:
            List of BenchmarkResult objects.
        """
        results: list[BenchmarkResult] = []

        if self.verbose:
            print("Running comprehensive vectorization benchmarks...\n")

        # Run all benchmarks with custom or default sizes
        size = n_elements if n_elements is not None else 1_000_000
        results.append(self.benchmark_sum(n_elements=size))

        size = n_elements if n_elements is not None else 100_000
        results.append(self.benchmark_ewm_calculate(n_elements=size))
        results.append(self.benchmark_rolling_calculation(n_elements=size))
        results.append(self.benchmark_percentage_change(n_elements=size))

        size = n_elements if n_elements is not None else 1_000_000
        results.append(self.benchmark_elementwise_operation(n_elements=size))
        results.append(self.benchmark_filtering(n_elements=size))

        results.append(self.benchmark_correlation())

        size = n_elements if n_elements is not None else 100_000
        results.append(self.benchmark_groupby(n_elements=size))

        return results

    def generate_report(
        self,
        results: list[BenchmarkResult],
    ) -> str:
        """Generate benchmark report.

        Args:
            results: List of benchmark results.

        Returns:
            Formatted report string.
        """
        report_lines = [
            "=" * 70,
            "VECTORIZATION BENCHMARK REPORT",
            "=" * 70,
            "",
        ]

        # Summary statistics
        speedups = [r.speedup for r in results]
        avg_speedup = np.mean(speedups)
        max_speedup = np.max(speedups)
        min_speedup = np.min(speedups)

        report_lines.extend(
            [
                f"Total benchmarks: {len(results)}",
                f"Average speedup: {avg_speedup:.2f}x",
                f"Best speedup: {max_speedup:.2f}x",
                f"Worst speedup: {min_speedup:.2f}x",
                "",
                "-" * 70,
                "DETAILED RESULTS",
                "-" * 70,
                "",
            ]
        )

        # Individual results
        for result in results:
            report_lines.append(result.get_summary())
            report_lines.append("")

        # Performance grades
        report_lines.extend(
            [
                "-" * 70,
                "PERFORMANCE GRADES",
                "-" * 70,
                "",
            ]
        )

        for result in results:
            grade = result.get_performance_grade()
            report_lines.append(f"{result.function_name:30s} : Grade {grade}")

        report_lines.extend(
            [
                "",
                "=" * 70,
            ]
        )

        return "\n".join(report_lines)

    def generate_latex_table(
        self,
        results: list[BenchmarkResult],
    ) -> str:
        """Generate LaTeX formatted table of benchmark results.

        Args:
            results: List of benchmark results.

        Returns:
            LaTeX table string.
        """
        table_lines = [
            "\\begin{table}[h]",
            "\\centering",
            "\\begin{tabular}{lcccc}",
            "\\hline",
            "Operation & Elements & Vectorized (ms) & Non-Vectorized (ms) & Speedup \\\\",
            "\\hline",
        ]

        for result in results:
            table_lines.append(
                f"{result.function_name.replace('_', ' ').title()} & "
                f"{result.n_elements:,} & "
                f"{result.vectorized_time * 1000:.4f} & "
                f"{result.non_vectorized_time * 1000:.4f} & "
                f"{result.speedup:.2f}x \\\\"
            )

        table_lines.extend(
            [
                "\\hline",
                "\\end{tabular}",
                "\\caption{Vectorization Performance Comparison}",
                "\\label{tab:vectorization_benchmark}",
                "\\end{table}",
            ]
        )

        return "\n".join(table_lines)
