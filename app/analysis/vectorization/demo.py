#!/usr/bin/env python3
"""
Vectorization Verification Module - Demo Script

This script demonstrates the key features of the vectorization verification module:
1. Code auditing for vectorization issues
2. Benchmarking vectorized vs non-vectorized code
3. Pattern library with examples
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.analysis.vectorization.benchmark import VectorizationBenchmark
from app.analysis.vectorization.patterns import VectorizationPatterns

# Import directly from module files to avoid circular import issues
from app.analysis.vectorization.vectorization_auditor import VectorizationAuditor


def demo_code_auditing() -> None:
    """Demonstrate code auditing for vectorization issues."""
    print("=" * 70)
    print("DEMO: Code Auditing for Vectorization Issues")
    print("=" * 70)
    print()

    # Non-vectorized code sample
    bad_code = '''
import numpy as np
import pandas as pd

def calculate_returns(prices):
    """Calculate returns - non-vectorized version."""
    returns = np.zeros(len(prices) - 1)
    for i in range(len(prices) - 1):
        returns[i] = (prices[i+1] - prices[i]) / prices[i]
    return returns

def moving_average(prices, window=20):
    """Calculate moving average - non-vectorized version."""
    ma = np.zeros(len(prices) - window + 1)
    for i in range(window - 1, len(prices)):
        ma[i - window + 1] = np.mean(prices[i-window+1:i+1])
    return ma

def process_dataframe(df):
    """Process dataframe - using .apply()"""
    df['returns'] = df['price'].apply(lambda x: x * 1.1)
    df['adjusted'] = df['value'].apply(lambda x: x + 100)
    return df

def iterate_rows(df):
    """Iterate over rows - using .iterrows()"""
    result = []
    for idx, row in df.iterrows():
        result.append(row['price'] * row['volume'])
    return result
'''

    print("Analyzing non-vectorized code:")
    print("-" * 70)
    print(bad_code)
    print("-" * 70)
    print()

    # Audit the code
    auditor = VectorizationAuditor()
    issues = auditor.audit_code_snippet(bad_code, filename="demo.py")

    print(f"Found {len(issues)} vectorization issues:")
    print()

    for i, issue in enumerate(issues, 1):
        print(f"{i}. [{issue.severity.upper()}] Line {issue.line_number}")
        print(f"   Type: {issue.issue_type}")
        print(f"   Description: {issue.description}")
        print(f"   Suggestion: {issue.suggestion}")
        print()

    # Calculate score
    score = auditor.calculate_score(issues)
    print(f"Vectorization Score: {score}/100")
    print()


def demo_benchmarking() -> None:
    """Demonstrate benchmarking of vectorized vs non-vectorized code."""
    print()
    print("=" * 70)
    print("DEMO: Benchmarking Vectorized vs Non-Vectorized Code")
    print("=" * 70)
    print()

    benchmark = VectorizationBenchmark(verbose=False)

    print("Running benchmarks...")
    print()

    # Run a few key benchmarks
    results = [
        benchmark.benchmark_sum(n_elements=100_000),
        benchmark.benchmark_rolling_calculation(n_elements=10_000, window=20),
        benchmark.benchmark_elementwise_operation(n_elements=100_000),
    ]

    for result in results:
        print(result.get_summary())
        print()

    # Generate summary
    avg_speedup = sum(r.speedup for r in results) / len(results)
    print(f"Average speedup: {avg_speedup:.2f}x")
    print()


def demo_patterns() -> None:
    """Demonstrate vectorization patterns library."""
    print()
    print("=" * 70)
    print("DEMO: Vectorization Patterns Library")
    print("=" * 70)
    print()

    # Show key patterns
    patterns = [
        ("Element-wise Operations", VectorizationPatterns.elementwise_operation()),
        ("Rolling Calculations", VectorizationPatterns.rolling_calculation()),
        ("Filtering", VectorizationPatterns.filtering()),
    ]

    for name, pattern in patterns:
        print(f"{name}:")
        print(pattern)
        print()

    # Show trading-specific examples
    print("Trading-Specific Examples:")
    print("-" * 70)
    trading_examples = VectorizationPatterns.get_trading_specific_examples()
    for name, example in list(trading_examples.items())[:3]:
        print(f"{name.replace('_', ' ').title()}:")
        print(example)
        print()


def main() -> None:
    """Run all demos."""
    print()
    print("*" * 70)
    print(" VECTORIZATION VERIFICATION MODULE - DEMONSTRATION")
    print("*" * 70)
    print()

    try:
        demo_code_auditing()
        demo_benchmarking()
        demo_patterns()

        print()
        print("=" * 70)
        print("DEMO COMPLETE")
        print("=" * 70)
        print()
        print("Key Takeaways:")
        print("1. Vectorization issues are automatically detected in code")
        print("2. Vectorized code is typically 10-100x faster")
        print("3. Pattern library provides concrete examples for refactoring")
        print()

    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
