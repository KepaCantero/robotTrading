#!/usr/bin/env python3
"""
Vectorization Verification Module - Demo Script

This script demonstrates the key features of the vectorization verification module:
1. Code auditing for vectorization issues
2. Benchmarking vectorized vs non-vectorized code
3. Pattern library with examples
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.domain.analysis.vectorization.benchmark import VectorizationBenchmark
from app.domain.analysis.vectorization.patterns import VectorizationPatterns

# Import directly from module files to avoid circular import issues
from app.domain.analysis.vectorization.vectorization_auditor import VectorizationAuditor


def demo_code_auditing() -> None:
    """Demonstrate code auditing for vectorization issues."""
    logger.debug("=" * 70)
    logger.debug("DEMO: Code Auditing for Vectorization Issues")
    logger.debug("=" * 70)
    logger.debug("")  # type: ignore[arg-type]

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

    logger.debug("Analyzing non-vectorized code:")
    logger.debug("-" * 70)
    logger.debug(bad_code)
    logger.debug("-" * 70)
    logger.debug("")  # type: ignore[arg-type]

    # Audit the code
    auditor = VectorizationAuditor()
    issues = auditor.audit_code_snippet(bad_code, filename="demo.py")

    logger.debug(f"Found {len(issues)} vectorization issues:")
    logger.debug("")  # type: ignore[arg-type]

    for i, issue in enumerate(issues, 1):
        logger.debug(f"{i}. [{issue.severity.upper()}] Line {issue.line_number}")
        logger.debug(f"   Type: {issue.issue_type}")
        logger.debug(f"   Description: {issue.description}")
        logger.debug(f"   Suggestion: {issue.suggestion}")
        logger.debug("")  # type: ignore[arg-type]

    # Calculate score
    score = auditor.calculate_score(issues)
    logger.debug(f"Vectorization Score: {score}/100")
    logger.debug("")  # type: ignore[arg-type]


def demo_benchmarking() -> None:
    """Demonstrate benchmarking of vectorized vs non-vectorized code."""
    logger.debug("")  # type: ignore[arg-type]
    logger.debug("=" * 70)
    logger.debug("DEMO: Benchmarking Vectorized vs Non-Vectorized Code")
    logger.debug("=" * 70)
    logger.debug("")  # type: ignore[arg-type]

    benchmark = VectorizationBenchmark(verbose=False)

    logger.debug("Running benchmarks...")
    logger.debug("")  # type: ignore[arg-type]

    # Run a few key benchmarks
    results = [
        benchmark.benchmark_sum(n_elements=100_000),
        benchmark.benchmark_rolling_calculation(n_elements=10_000, window=20),
        benchmark.benchmark_elementwise_operation(n_elements=100_000),
    ]

    for result in results:
        logger.debug(result.get_summary())
        logger.debug("")  # type: ignore[arg-type]

    # Generate summary
    avg_speedup = np.mean([r.speedup for r in results])
    logger.debug(f"Average speedup: {avg_speedup:.2f}x")
    logger.debug("")  # type: ignore[arg-type]


def demo_patterns() -> None:
    """Demonstrate vectorization patterns library."""
    logger.debug("")  # type: ignore[arg-type]
    logger.debug("=" * 70)
    logger.debug("DEMO: Vectorization Patterns Library")
    logger.debug("=" * 70)
    logger.debug("")  # type: ignore[arg-type]

    # Show key patterns
    patterns = [
        ("Element-wise Operations", VectorizationPatterns.elementwise_operation()),
        ("Rolling Calculations", VectorizationPatterns.rolling_calculation()),
        ("Filtering", VectorizationPatterns.filtering()),
    ]

    for name, pattern in patterns:
        logger.debug(f"{name}:")
        logger.debug(pattern)
        logger.debug("")  # type: ignore[arg-type]

    # Show trading-specific examples
    logger.debug("Trading-Specific Examples:")
    logger.debug("-" * 70)
    trading_examples = VectorizationPatterns.get_trading_specific_examples()
    for name, example in list(trading_examples.items())[:3]:
        logger.debug(f"{name.replace('_', ' ').title()}:")
        logger.debug(example)
        logger.debug("")  # type: ignore[arg-type]


def main() -> None:
    """Run all demos."""
    logger.debug("")  # type: ignore[arg-type]
    logger.debug("*" * 70)
    logger.debug(" VECTORIZATION VERIFICATION MODULE - DEMONSTRATION")
    logger.debug("*" * 70)
    logger.debug("")  # type: ignore[arg-type]

    try:
        demo_code_auditing()
        demo_benchmarking()
        demo_patterns()

        logger.debug("")  # type: ignore[arg-type]
        logger.debug("=" * 70)
        logger.debug("DEMO COMPLETE")
        logger.debug("=" * 70)
        logger.debug("")  # type: ignore[arg-type]
        logger.debug("Key Takeaways:")
        logger.debug("1. Vectorization issues are automatically detected in code")
        logger.debug("2. Vectorized code is typically 10-100x faster")
        logger.debug("3. Pattern library provides concrete examples for refactoring")
        logger.debug("")  # type: ignore[arg-type]

    except Exception as e:
        logger.debug(f"Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
