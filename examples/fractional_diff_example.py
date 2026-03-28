"""
Fractional Differentiation Example - Complete Usage Demonstration.

This script demonstrates the practical application of fractional differentiation
for financial time series, following López de Prado's methodology from
"Advances in Financial Machine Learning", Chapter 3, Section 3.4.

Key Concepts Demonstrated:
1. Finding the optimal differentiation order (d)
2. Applying fractional differentiation to achieve stationarity
3. Preserving memory while creating stationary features
4. Comparison with standard integer differentiation
5. Visualization and analysis

Author: Advanced Financial Machine Learning Implementation
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Import fractional differentiation module
import sys

sys.path.append(str(Path(__file__).parent.parent))

from app.backtesting.feature_engineering import (
    FractionalDifferentiation,
    FractionalDiffTransformer,
    apply_frac_diff_to_dataframe,
)
from app.backtesting.feature_engineering.fracdiff_visualizations import (
    plot_frac_diff_comparison,
    plot_weights,
    plot_memory_preservation,
    plot_stationarity_test,
    plot_optimal_d_search,
    create_summary_report,
)


def generate_synthetic_data(n_points: int = 1000, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic financial data for demonstration.

    Creates multiple time series with different characteristics:
    - Random walk (simulating price)
    - Mean-reverting (simulating spreads)
    - Volatility clustering (simulating returns)
    """
    np.random.seed(seed)

    # Generate time index
    dates = pd.date_range(start='2020-01-01', periods=n_points, freq='D')

    # Random walk (price-like)
    price = 100 + np.random.randn(n_points).cumsum()

    # Mean-reverting (spread-like)
    spread = np.random.randn(n_points)
    for i in range(1, n_points):
        spread[i] = 0.5 * spread[i - 1] + 0.5 * np.random.randn()

    # Returns with volatility clustering
    returns = np.random.randn(n_points) * 0.02
    volatility = np.ones(n_points)
    for i in range(10, n_points):
        volatility[i] = 0.8 * volatility[i - 1] + 0.2 * abs(returns[i - 1])
        returns[i] *= volatility[i]

    # Volume (log-normal)
    volume = np.exp(np.random.randn(n_points) * 0.5 + 10)

    df = pd.DataFrame(
        {'date': dates, 'price': price, 'spread': spread, 'returns': returns, 'volume': volume}
    ).set_index('date')

    return df


def example_1_basic_fractional_diff():
    """Example 1: Basic fractional differentiation."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Fractional Differentiation")
    print("=" * 70)

    # Generate data
    df = generate_synthetic_data(n_points=500)
    price_series = df['price']

    print(f"\nOriginal price series:")
    print(f"  Length: {len(price_series)}")
    print(f"  Mean: {price_series.mean():.4f}")
    print(f"  Std: {price_series.std():.4f}")
    print(f"  Min: {price_series.min():.4f}")
    print(f"  Max: {price_series.max():.4f}")

    # Initialize fractional differentiation
    fd = FractionalDifferentiation(threshold=1e-5, adfuller_alpha=0.05)

    # Apply fractional differentiation with d=0.5
    frac_diff_series = fd.fractional_diff(price_series, d=0.5)

    print(f"\nFractionally differenced series (d=0.5):")
    print(f"  Length: {len(frac_diff_series)}")
    print(f"  Non-NaN values: {frac_diff_series.notna().sum()}")
    print(f"  Mean: {frac_diff_series.mean():.4f}")
    print(f"  Std: {frac_diff_series.std():.4f}")

    print("\n✓ Example 1 completed successfully")


def example_2_finding_optimal_d():
    """Example 2: Finding optimal differentiation order."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Finding Optimal Differentiation Order")
    print("=" * 70)

    # Generate data
    df = generate_synthetic_data(n_points=1000)
    price_series = df['price']

    # Initialize fractional differentiation
    fd = FractionalDifferentiation(adfuller_alpha=0.05)

    print("\nSearching for optimal d...")

    # Find optimal d using binary search
    optimal_d, p_value, metadata = fd.find_optimal_d(
        price_series, min_d=0.0, max_d=1.0, method='binary'
    )

    print(f"\nResults:")
    print(f"  Optimal d: {optimal_d:.4f}")
    print(f"  P-value: {p_value:.4f}")
    print(f"  Is stationary: {p_value < fd.adfuller_alpha}")
    print(f"  Search iterations: {metadata['iterations']}")

    # Compare different d values
    print("\nComparing different d values:")
    comparison = fd.compare_d_values(price_series, d_values=[0.0, 0.3, 0.5, 0.7, 1.0])
    print(
        comparison[
            ['d', 'p_value', 'is_stationary', 'memory_preservation', 'memory_loss_pct']
        ].to_string(index=False)
    )

    print("\n✓ Example 2 completed successfully")


def example_3_memory_preservation():
    """Example 3: Memory preservation analysis."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Memory Preservation Analysis")
    print("=" * 70)

    # Generate data
    df = generate_synthetic_data(n_points=1000)
    price_series = df['price']

    fd = FractionalDifferentiation()

    print("\nAnalyzing memory preservation for different d values:")

    # Compare memory preservation
    d_values = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    memory_results = []

    for d in d_values:
        if d == 0.0:
            diff_series = price_series
        else:
            diff_series = fd.fractional_diff(price_series, d=d)

        memory_metrics = fd.calculate_memory_loss(price_series, diff_series)
        memory_results.append(
            {
                'd': d,
                'memory_preservation': memory_metrics['memory_preservation_ratio'],
                'memory_loss_pct': memory_metrics['memory_loss_pct'],
            }
        )

        print(
            f"  d={d:.1f}: Memory preserved={memory_metrics['memory_preservation_ratio']:.3f}, "
            f"Loss={memory_metrics['memory_loss_pct']:.1f}%"
        )

    print("\nKey insight: Fractional differentiation (d<1) preserves significant memory")
    print("while achieving stationarity, unlike standard differentiation (d=1).")

    print("\n✓ Example 3 completed successfully")


def example_4_dataframe_application():
    """Example 4: Applying to DataFrame with multiple features."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Applying to Multiple Features")
    print("=" * 70)

    # Generate multi-feature data
    df = generate_synthetic_data(n_points=1000)

    print("\nOriginal DataFrame:")
    print(df.head())

    # Apply fractional differentiation to all numeric columns
    df_fracdiff = apply_frac_diff_to_dataframe(
        df, d=0.4, columns=['price', 'spread'], threshold=1e-5
    )

    print("\nDataFrame with fractional differentiation:")
    print(df_fracdiff.head())

    print("\nNew columns created:")
    new_cols = [col for col in df_fracdiff.columns if '_fracdiff' in col]
    print(f"  {new_cols}")

    print("\n✓ Example 4 completed successfully")


def example_5_sklearn_transformer():
    """Example 5: Using scikit-learn compatible transformer."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Scikit-learn Compatible Transformer")
    print("=" * 70)

    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    # Generate data
    df = generate_synthetic_data(n_points=1000)
    features = df[['price', 'spread', 'volume']]

    print("\nOriginal features shape:", features.shape)

    # Create transformer
    transformer = FractionalDiffTransformer(d=0.4, threshold=1e-5, auto_find_d=False)

    # Fit and transform
    features_fracdiff = transformer.fit_transform(features)

    print(f"Transformed features shape: {features_fracdiff.shape}")
    print(f"Optimal d used: {transformer.optimal_d_:.4f}")

    # Create a pipeline
    pipeline = Pipeline(
        [('fracdiff', FractionalDiffTransformer(d=0.4)), ('scaler', StandardScaler())]
    )

    features_scaled = pipeline.fit_transform(features)
    print(f"Pipeline output shape: {features_scaled.shape}")

    print("\n✓ Example 5 completed successfully")


def example_6_visualizations():
    """Example 6: Creating visualizations."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Visualizations and Analysis")
    print("=" * 70)

    # Generate data
    df = generate_synthetic_data(n_points=1000)
    price_series = df['price']

    # Create output directory
    output_dir = Path("examples/output")
    output_dir.mkdir(exist_ok=True)

    print("\nCreating visualizations...")

    # 1. Fractional diff comparison
    print("  1. Fractional diff comparison...")
    fig1 = plot_frac_diff_comparison(price_series, d_values=[0.0, 0.3, 0.5, 1.0])
    fig1.savefig(output_dir / "fracdiff_comparison.png", dpi=150, bbox_inches='tight')
    plt.close(fig1)

    # 2. Weights visualization
    print("  2. Weights visualization...")
    fig2 = plot_weights(d=0.5, threshold=1e-5)
    fig2.savefig(output_dir / "fracdiff_weights.png", dpi=150, bbox_inches='tight')
    plt.close(fig2)

    # 3. Memory preservation
    print("  3. Memory preservation...")
    fig3 = plot_memory_preservation(price_series, d_values=[0.0, 0.3, 0.5, 1.0])
    fig3.savefig(output_dir / "memory_preservation.png", dpi=150, bbox_inches='tight')
    plt.close(fig3)

    # 4. Stationarity test
    print("  4. Stationarity test...")
    fig4 = plot_stationarity_test(price_series)
    fig4.savefig(output_dir / "stationarity_test.png", dpi=150, bbox_inches='tight')
    plt.close(fig4)

    # 5. Optimal d search
    print("  5. Optimal d search...")
    fig5 = plot_optimal_d_search(price_series)
    fig5.savefig(output_dir / "optimal_d_search.png", dpi=150, bbox_inches='tight')
    plt.close(fig5)

    # 6. Summary report
    print("  6. Summary report...")
    fig6 = create_summary_report(
        price_series,
        d_values=[0.0, 0.3, 0.5, 0.7, 1.0],
        save_path=str(output_dir / "fracdiff_report.png"),
    )
    plt.close(fig6)

    print(f"\n✓ All visualizations saved to {output_dir}/")
    print("\n✓ Example 6 completed successfully")


def example_7_practical_trading_scenario():
    """Example 7: Practical trading scenario."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Practical Trading Scenario")
    print("=" * 70)

    # Generate realistic price data
    np.random.seed(42)
    n_points = 1000
    dates = pd.date_range(start='2020-01-01', periods=n_points, freq='D')

    # Create price with trend and noise
    trend = np.linspace(100, 150, n_points)
    noise = np.random.randn(n_points).cumsum() * 0.5
    price = trend + noise

    price_series = pd.Series(price, index=dates)

    print("\nScenario: Creating stationary features for machine learning")
    print("-" * 70)

    fd = FractionalDifferentiation()

    # Find optimal d
    print("\nStep 1: Finding optimal differentiation order...")
    optimal_d, p_value, _ = fd.find_optimal_d(price_series)
    print(f"  Optimal d: {optimal_d:.4f}")
    print(f"  P-value: {p_value:.4f}")

    # Apply fractional differentiation
    print("\nStep 2: Applying fractional differentiation...")
    frac_diff_price = fd.fractional_diff(price_series, d=optimal_d)

    # Calculate memory preservation
    print("\nStep 3: Analyzing memory preservation...")
    memory_metrics = fd.calculate_memory_loss(price_series, frac_diff_price)
    print(f"  Memory preserved: {memory_metrics['memory_preservation_ratio']:.3f}")
    print(f"  Memory loss: {memory_metrics['memory_loss_pct']:.1f}%")

    # Create additional features
    print("\nStep 4: Creating feature set...")
    features = pd.DataFrame(
        {
            'price_fracdiff': frac_diff_price,
            'price_ma': price_series.rolling(window=20).mean(),
            'price_std': price_series.rolling(window=20).std(),
            'returns': price_series.pct_change(),
        }
    )

    print(f"  Features shape: {features.shape}")
    print(f"  Non-NaN values per feature:")
    for col in features.columns:
        print(f"    {col}: {features[col].notna().sum()}")

    print("\nKey insights:")
    print("  - Fractional differentiation creates stationary features")
    print("  - Memory is preserved (unlike standard differentiation)")
    print("  - Features are suitable for machine learning models")
    print("  - The optimal d balances stationarity and memory preservation")

    print("\n✓ Example 7 completed successfully")


def example_8_comparison_integer_vs_fractional():
    """Example 8: Integer vs Fractional differentiation comparison."""
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Integer vs Fractional Differentiation")
    print("=" * 70)

    # Generate data
    df = generate_synthetic_data(n_points=1000)
    price_series = df['price']

    fd = FractionalDifferentiation()

    print("\nComparing differentiation methods:")
    print("-" * 70)

    # No differentiation
    print("\n1. No differentiation (d=0.0):")
    memory_0 = fd.calculate_memory_loss(price_series, price_series)
    print(f"   Memory preserved: {memory_0['memory_preservation_ratio']:.3f}")

    # Fractional differentiation
    print("\n2. Fractional differentiation (d=0.4):")
    frac_diff_04 = fd.fractional_diff(price_series, d=0.4)
    memory_04 = fd.calculate_memory_loss(price_series, frac_diff_04)
    print(f"   Memory preserved: {memory_04['memory_preservation_ratio']:.3f}")

    # Standard first difference
    print("\n3. Standard first difference (d=1.0):")
    first_diff = price_series.diff()
    memory_1 = fd.calculate_memory_loss(price_series, first_diff)
    print(f"   Memory preserved: {memory_1['memory_preservation_ratio']:.3f}")

    print("\nConclusion:")
    print("  - d=0.0: Maximum memory but not stationary")
    print("  - d=0.4: Good balance of stationarity and memory")
    print("  - d=1.0: Stationary but destroys all memory")

    print("\n✓ Example 8 completed successfully")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("FRACTIONAL DIFFERENTIATION - COMPLETE EXAMPLE SUITE")
    print("=" * 70)
    print("\nBased on López de Prado, 'Advances in Financial Machine Learning'")
    print("Chapter 3, Section 3.4: Fractional Differentiation")

    try:
        # Run all examples
        example_1_basic_fractional_diff()
        example_2_finding_optimal_d()
        example_3_memory_preservation()
        example_4_dataframe_application()
        example_5_sklearn_transformer()
        example_6_visualizations()
        example_7_practical_trading_scenario()
        example_8_comparison_integer_vs_fractional()

        print("\n" + "=" * 70)
        print("ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nKey Takeaways:")
        print("  1. Fractional differentiation creates stationary features")
        print("  2. Memory is preserved (unlike standard differentiation)")
        print("  3. Optimal d balances stationarity and memory preservation")
        print("  4. Critical for ML applications on financial time series")
        print("\nNext steps:")
        print("  - Check examples/output/ for visualizations")
        print("  - Integrate into your feature engineering pipeline")
        print("  - Experiment with different d values for your data")

    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
