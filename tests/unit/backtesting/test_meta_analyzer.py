"""
Unit tests for Backtest Meta-Analyzer module.

Tests for the meta-analysis of backtesting results including:
- Pattern analysis
- Clustering
- Correlation detection
- Optimal combination suggestions
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock, Mock
from pathlib import Path
import json
import tempfile
import shutil

from app.backtesting.meta_analyzer.meta_analyzer import BacktestMetaAnalyzer


@pytest.mark.unit
class TestBacktestMetaAnalyzerInitialization:
    """Test cases for BacktestMetaAnalyzer initialization."""

    def test_initialization_with_defaults(self):
        """Test initialization with default parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)

            assert analyzer.data_dir == Path(temp_dir)
            assert analyzer.output_dir == Path("reports/meta")
            assert analyzer.enable_visualizations is True
            assert analyzer.results == []
            assert analyzer.df_results is None
            assert analyzer._lock is not None

    def test_initialization_custom_output_dir(self):
        """Test initialization with custom output directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_output = tempfile.mkdtemp()
            analyzer = BacktestMetaAnalyzer(
                data_dir=temp_dir,
                output_dir=custom_output,
                enable_visualizations=False
            )

            assert analyzer.output_dir == Path(custom_output)
            assert analyzer.enable_visualizations is False

            shutil.rmtree(custom_output)

    def test_output_dir_creation(self):
        """Test that output directory is created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = tempfile.mkdtemp()
            # Remove it to test creation
            shutil.rmtree(output_dir)

            analyzer = BacktestMetaAnalyzer(
                data_dir=temp_dir,
                output_dir=output_dir
            )

            assert Path(output_dir).exists()
            shutil.rmtree(output_dir)


@pytest.mark.unit
class TestLoadResults:
    """Test cases for loading backtest results."""

    @pytest.fixture
    def sample_results_dir(self):
        """Create a directory with sample result files."""
        temp_dir = tempfile.mkdtemp()
        results_dir = Path(temp_dir) / "results"
        results_dir.mkdir()

        # Create sample JSON files
        for i in range(3):
            result = {
                "total_pnl": 1000 * (i + 1),
                "return_pct": 0.1 * (i + 1),
                "sharpe_ratio": 1.0 + 0.5 * i,
                "max_drawdown": -0.05 - 0.02 * i,
                "win_rate": 0.5 + 0.1 * i,
                "strategy_name": f"strategy_{i}",
                "test_type": "unit_test",
            }
            with open(results_dir / f"result_{i}.json", 'w') as f:
                json.dump(result, f)

        # Create sample CSV file
        df = pd.DataFrame({
            "total_pnl": [500, 1500, 2500],
            "return_pct": [0.05, 0.15, 0.25],
            "sharpe_ratio": [0.8, 1.2, 1.6],
            "max_drawdown": [-0.08, -0.06, -0.04],
            "win_rate": [0.45, 0.55, 0.65],
            "strategy_name": ["csv_strategy_0", "csv_strategy_1", "csv_strategy_2"],
            "test_type": "unit_test",
        })
        df.to_csv(results_dir / "results.csv", index=False)

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_load_json_files(self, sample_results_dir):
        """Test loading JSON result files."""
        analyzer = BacktestMetaAnalyzer(data_dir=sample_results_dir)

        count = await analyzer.load_results()

        assert count == 6  # 3 JSON + 3 CSV records
        assert len(analyzer.results) == 6
        assert analyzer.df_results is not None
        assert len(analyzer.df_results) == 6

    @pytest.mark.asyncio
    async def test_load_empty_directory(self):
        """Test loading from empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)

            count = await analyzer.load_results()

            assert count == 0
            assert analyzer.results == []
            assert analyzer.df_results is None

    @pytest.mark.asyncio
    async def test_load_nonexistent_directory(self):
        """Test loading from non-existent directory."""
        analyzer = BacktestMetaAnalyzer(data_dir="/nonexistent/path")

        count = await analyzer.load_results()

        assert count == 0

    @pytest.mark.asyncio
    async def test_load_results_with_custom_path(self, sample_results_dir):
        """Test loading results from custom path."""
        analyzer = BacktestMetaAnalyzer(data_dir="/default/path")

        results_dir = Path(sample_results_dir) / "results"
        count = await analyzer.load_results(path=str(results_dir))

        assert count > 0


@pytest.mark.unit
class TestAnalyzePerformance:
    """Test cases for performance analysis."""

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample results DataFrame."""
        return pd.DataFrame({
            "total_pnl": [1000, 1500, 800, 2000, 1200],
            "return_pct": [0.10, 0.15, 0.08, 0.20, 0.12],
            "sharpe_ratio": [1.0, 1.5, 0.8, 2.0, 1.2],
            "sortino_ratio": [1.2, 1.8, 1.0, 2.5, 1.5],
            "max_drawdown": [-0.10, -0.08, -0.12, -0.05, -0.09],
            "win_rate": [0.50, 0.60, 0.45, 0.65, 0.55],
            "total_trades": [100, 120, 80, 150, 110],
            "avg_trade_pnl": [10, 12.5, 10, 13.33, 10.9],
            "profit_factor": [1.5, 1.8, 1.3, 2.2, 1.6],
            "calmar_ratio": [1.0, 1.9, 0.67, 4.0, 1.33],
            "strategy_name": ["strat_a", "strat_b", "strat_a", "strat_c", "strat_b"],
            "test_type": ["unit", "unit", "integration", "unit", "unit"],
        })

    def test_analyze_performance_basic(self, sample_dataframe):
        """Test basic performance analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe.copy()

            analysis = analyzer.analyze_performance()

            assert isinstance(analysis, dict)
            assert "summary_stats" in analysis
            assert "performance_by_category" in analysis
            assert "correlations" in analysis
            assert "best_performers" in analysis
            assert "worst_performers" in analysis

    def test_summary_statistics(self, sample_dataframe):
        """Test summary statistics calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe.copy()

            analysis = analyzer.analyze_performance()

            summary = analysis["summary_stats"]

            # Check sharpe_ratio stats
            assert "sharpe_ratio" in summary
            sharpe_stats = summary["sharpe_ratio"]
            assert "mean" in sharpe_stats
            assert "median" in sharpe_stats
            assert "std" in sharpe_stats
            assert "min" in sharpe_stats
            assert "max" in sharpe_stats

            # Verify values
            assert abs(sharpe_stats["mean"] - 1.3) < 0.01  # Average of [1.0, 1.5, 0.8, 2.0, 1.2]

    def test_performance_by_category(self, sample_dataframe):
        """Test performance analysis by category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe.copy()

            analysis = analyzer.analyze_performance()

            # Check strategy_name category
            by_strategy = analysis["performance_by_category"]["strategy_name"]
            assert "strat_a" in by_strategy
            assert "strat_b" in by_strategy
            assert "strat_c" in by_strategy

            # Verify strat_a has 2 results
            assert by_strategy["strat_a"]["sharpe_ratio"]["count"] == 2

    def test_best_and_worst_performers(self, sample_dataframe):
        """Test identification of best and worst performers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe.copy()

            analysis = analyzer.analyze_performance()

            # Best by Sharpe
            best_sharpe = analysis["best_performers"]["by_sharpe"]
            assert len(best_sharpe) <= 10
            # Should be sorted by sharpe_ratio descending
            if best_sharpe:
                assert best_sharpe[0]["sharpe_ratio"] == 2.0

            # Worst by Sharpe
            worst_sharpe = analysis["worst_performers"]["by_sharpe"]
            assert len(worst_sharpe) <= 10
            # Should be sorted by sharpe_ratio ascending
            if worst_sharpe:
                assert worst_sharpe[0]["sharpe_ratio"] == 0.8

    def test_analyze_performance_no_data(self):
        """Test analysis with no data loaded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)

            analysis = analyzer.analyze_performance()

            assert analysis == {}

    def test_correlation_calculation(self, sample_dataframe):
        """Test correlation calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe.copy()

            analysis = analyzer.analyze_performance()

            correlations = analysis["correlations"]
            assert isinstance(correlations, dict)

            # Check some key correlations
            if "sharpe_ratio" in correlations:
                assert "return_pct" in correlations["sharpe_ratio"]


@pytest.mark.unit
class TestDetectClusters:
    """Test cases for cluster detection."""

    @pytest.fixture
    def sample_dataframe_clustering(self):
        """Create sample data for clustering."""
        np.random.seed(42)
        n = 50

        return pd.DataFrame({
            "sharpe_ratio": np.random.randn(n) * 0.5 + 1.5,
            "total_pnl": np.random.randn(n) * 500 + 1500,
            "max_drawdown": np.random.randn(n) * 0.03 - 0.08,
            "win_rate": np.random.randn(n) * 0.1 + 0.55,
            "return_pct": np.random.randn(n) * 0.05 + 0.12,
            "total_trades": np.random.randint(50, 200, n),
        })

    def test_detect_clusters_basic(self, sample_dataframe_clustering):
        """Test basic cluster detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe_clustering.copy()

            clusters = analyzer.detect_clusters(n_clusters=3)

            assert isinstance(clusters, dict)
            assert "n_clusters" in clusters
            assert clusters["n_clusters"] == 3
            assert "features_used" in clusters
            assert "clusters" in clusters
            assert "inertia" in clusters

    def test_cluster_analysis_structure(self, sample_dataframe_clustering):
        """Test cluster analysis structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe_clustering.copy()

            clusters = analyzer.detect_clusters(n_clusters=2)

            # Check individual cluster structure
            assert "cluster_0" in clusters["clusters"]
            assert "cluster_1" in clusters["clusters"]

            cluster_0 = clusters["clusters"]["cluster_0"]
            assert "size" in cluster_0
            assert "characteristics" in cluster_0
            assert "indices" in cluster_0

            # Check characteristics
            assert "sharpe_ratio" in cluster_0["characteristics"]
            assert "mean" in cluster_0["characteristics"]["sharpe_ratio"]
            assert "std" in cluster_0["characteristics"]["sharpe_ratio"]

    def test_detect_clusters_custom_features(self, sample_dataframe_clustering):
        """Test clustering with custom features."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe_clustering.copy()

            custom_features = ["sharpe_ratio", "total_pnl", "win_rate"]
            clusters = analyzer.detect_clusters(
                n_clusters=3,
                features=custom_features
            )

            assert clusters["features_used"] == custom_features

    def test_detect_clusters_no_data(self):
        """Test clustering with no data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)

            clusters = analyzer.detect_clusters(n_clusters=3)

            assert clusters == {}

    def test_detect_clusters_insufficient_data(self):
        """Test clustering with insufficient data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            # Only 2 samples, trying to make 3 clusters
            analyzer.df_results = pd.DataFrame({
                "sharpe_ratio": [1.0, 1.5],
                "total_pnl": [1000, 1500],
            })

            clusters = analyzer.detect_clusters(n_clusters=3)

            # Should return empty due to insufficient data
            assert clusters == {}

    def test_detect_clusters_insufficient_features(self):
        """Test clustering with insufficient features."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            # Only 1 numeric feature
            analyzer.df_results = pd.DataFrame({
                "sharpe_ratio": [1.0, 1.5, 2.0],
            })

            clusters = analyzer.detect_clusters(n_clusters=2)

            # Should return empty due to insufficient features
            assert clusters == {}


@pytest.mark.unit
class TestSuggestOptimalCombinations:
    """Test cases for optimal combination suggestions."""

    @pytest.fixture
    def sample_dataframe_suggestions(self):
        """Create sample data for suggestions."""
        return pd.DataFrame({
            "sharpe_ratio": [1.0, 2.5, 1.5, 3.0, 0.8, 2.0],
            "total_pnl": [1000, 3000, 1500, 4000, 800, 2500],
            "win_rate": [0.5, 0.7, 0.6, 0.75, 0.45, 0.65],
            "max_drawdown": [-0.10, -0.05, -0.08, -0.04, -0.12, -0.06],
            "strategy_name": [f"strategy_{i}" for i in range(6)],
        })

    def test_suggest_optimal_combinations_default(self, sample_dataframe_suggestions):
        """Test suggestions with default criteria."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe_suggestions.copy()

            suggestions = analyzer.suggest_optimal_combinations(top_n=3)

            assert isinstance(suggestions, list)
            assert len(suggestions) == 3

            # Should be ordered by score
            # Highest Sharpe and PnL should be first
            assert suggestions[0]["sharpe_ratio"] == 3.0

    def test_suggest_optimal_combinations_custom_criteria(self, sample_dataframe_suggestions):
        """Test suggestions with custom criteria."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe_suggestions.copy()

            custom_criteria = {
                "sharpe_ratio": 0.5,
                "win_rate": 0.5,
            }
            suggestions = analyzer.suggest_optimal_combinations(
                top_n=3,
                criteria=custom_criteria
            )

            assert len(suggestions) == 3
            # Should prioritize based on custom weights

    def test_suggest_optimal_combinations_no_data(self):
        """Test suggestions with no data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)

            suggestions = analyzer.suggest_optimal_combinations(top_n=5)

            assert suggestions == []

    def test_suggest_optimal_combinations_scores(self, sample_dataframe_suggestions):
        """Test that scores are calculated correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)
            analyzer.df_results = sample_dataframe_suggestions.copy()

            suggestions = analyzer.suggest_optimal_combinations(top_n=10)

            # All suggestions should have valid metrics
            for suggestion in suggestions:
                assert "sharpe_ratio" in suggestion
                assert "total_pnl" in suggestion
                assert isinstance(suggestion["sharpe_ratio"], (int, float))


@pytest.mark.unit
class TestExportReport:
    """Test cases for report export."""

    @pytest.fixture
    def sample_analysis_results(self):
        """Create sample analysis results."""
        return {
            "summary_stats": {
                "sharpe_ratio": {
                    "mean": 1.5,
                    "median": 1.4,
                    "std": 0.5,
                }
            },
            "best_performers": {
                "by_sharpe": [
                    {"sharpe_ratio": 2.5, "total_pnl": 3000},
                    {"sharpe_ratio": 2.0, "total_pnl": 2500},
                ]
            },
            "timestamp": "2024-01-01T12:00:00",
        }

    def test_export_json_report(self, sample_analysis_results):
        """Test exporting JSON report."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(
                data_dir=temp_dir,
                output_dir=temp_dir,
                enable_visualizations=False
            )
            analyzer.analysis_results = sample_analysis_results.copy()
            analyzer.df_results = pd.DataFrame({
                "sharpe_ratio": [1.0, 2.5, 2.0],
                "total_pnl": [1000, 3000, 2500],
            })

            output_path = analyzer.export_report(format="json")

            assert output_path != ""
            assert Path(output_path).exists()

            # Verify content
            with open(output_path, 'r') as f:
                exported_data = json.load(f)

            assert "summary_stats" in exported_data
            assert exported_data["summary_stats"]["sharpe_ratio"]["mean"] == 1.5

    def test_export_csv_report(self, sample_analysis_results):
        """Test exporting CSV report."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(
                data_dir=temp_dir,
                output_dir=temp_dir,
                enable_visualizations=False
            )
            analyzer.analysis_results = sample_analysis_results.copy()
            analyzer.df_results = pd.DataFrame({
                "sharpe_ratio": [1.0, 2.5, 2.0],
                "total_pnl": [1000, 3000, 2500],
            })

            output_path = analyzer.export_report(format="csv")

            assert output_path != ""
            assert Path(output_path).exists()

            # Verify CSV can be read
            df = pd.read_csv(output_path)
            assert len(df) == 3

    def test_export_report_no_analysis(self):
        """Test export when no analysis has been run."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(
                data_dir=temp_dir,
                output_dir=temp_dir,
                enable_visualizations=False
            )

            output_path = analyzer.export_report()

            assert output_path == ""

    def test_export_report_custom_path(self, sample_analysis_results):
        """Test export with custom path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(
                data_dir=temp_dir,
                enable_visualizations=False
            )
            analyzer.analysis_results = sample_analysis_results.copy()
            analyzer.df_results = pd.DataFrame({"sharpe_ratio": [1.0, 2.5]})

            custom_path = Path(temp_dir) / "custom_report.json"
            output_path = analyzer.export_report(output_path=str(custom_path))

            assert Path(output_path).exists()
            assert output_path == str(custom_path)


@pytest.mark.unit
class TestRunParallelAnalysis:
    """Test cases for parallel analysis execution."""

    @pytest.mark.asyncio
    async def test_run_parallel_analysis_basic(self):
        """Test basic parallel analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample data
            results_dir = Path(temp_dir) / "results"
            results_dir.mkdir()

            result = {
                "total_pnl": 1000,
                "sharpe_ratio": 1.5,
                "max_drawdown": -0.08,
                "win_rate": 0.6,
                "strategy_name": "test_strategy",
            }
            with open(results_dir / "result.json", 'w') as f:
                json.dump(result, f)

            analyzer = BacktestMetaAnalyzer(
                data_dir=str(results_dir),
                enable_visualizations=False
            )

            results = await analyzer.run_parallel_analysis(
                max_workers=2,
                include_clustering=False
            )

            assert isinstance(results, dict)
            assert "performance" in results or "clustering" in results

    @pytest.mark.asyncio
    async def test_run_parallel_analysis_with_clustering(self):
        """Test parallel analysis with clustering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sufficient sample data
            results_dir = Path(temp_dir) / "results"
            results_dir.mkdir()

            for i in range(50):
                result = {
                    "total_pnl": 1000 + i * 100,
                    "sharpe_ratio": 1.0 + i * 0.05,
                    "max_drawdown": -0.08 - i * 0.001,
                    "win_rate": 0.5 + i * 0.01,
                    "return_pct": 0.1 + i * 0.01,
                    "strategy_name": f"strategy_{i}",
                }
                with open(results_dir / f"result_{i}.json", 'w') as f:
                    json.dump(result, f)

            analyzer = BacktestMetaAnalyzer(
                data_dir=str(results_dir),
                enable_visualizations=False
            )

            results = await analyzer.run_parallel_analysis(
                max_workers=2,
                include_clustering=True,
                n_clusters=3
            )

            assert "performance" in results
            assert "clustering" in results
            assert "suggestions" in results


@pytest.mark.unit
class TestMetaAnalyzerEdgeCases:
    """Test edge cases for meta analyzer."""

    def test_single_result(self):
        """Test with single result."""
        with tempfile.TemporaryDirectory() as temp_dir:
            results_dir = Path(temp_dir) / "results"
            results_dir.mkdir()

            result = {
                "total_pnl": 1000,
                "sharpe_ratio": 1.5,
                "max_drawdown": -0.08,
            }
            with open(results_dir / "result.json", 'w') as f:
                json.dump(result, f)

            analyzer = BacktestMetaAnalyzer(data_dir=str(results_dir))

            # Should handle single result
            import asyncio
            count = asyncio.run(analyzer.load_results())
            assert count == 1

    def test_results_with_missing_columns(self):
        """Test results with missing columns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)

            # Results with inconsistent columns
            analyzer.df_results = pd.DataFrame({
                "total_pnl": [1000, 1500, 800],
                "sharpe_ratio": [1.5, 2.0, np.nan],  # One NaN
                # Missing other columns
            })

            analysis = analyzer.analyze_performance()

            # Should handle missing columns gracefully
            assert isinstance(analysis, dict)

    def test_all_nan_values(self):
        """Test with all NaN values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)

            analyzer.df_results = pd.DataFrame({
                "sharpe_ratio": [np.nan, np.nan, np.nan],
                "total_pnl": [np.nan, np.nan, np.nan],
            })

            analysis = analyzer.analyze_performance()

            # Should handle gracefully
            assert isinstance(analysis, dict)

    def test_mixed_data_types(self):
        """Test with mixed data types in columns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)

            analyzer.df_results = pd.DataFrame({
                "sharpe_ratio": [1.5, 2.0, 1.8],
                "total_pnl": [1000, 1500, 1200],
                "strategy_name": ["strat_a", "strat_b", "strat_c"],
                "is_active": [True, False, True],  # Boolean
            })

            analysis = analyzer.analyze_performance()

            # Should handle mixed types
            assert isinstance(analysis, dict)

    def test_duplicate_results(self):
        """Test with duplicate results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)

            analyzer.df_results = pd.DataFrame({
                "sharpe_ratio": [1.5, 1.5, 2.0],  # Duplicate
                "total_pnl": [1000, 1000, 1500],  # Duplicate
            })

            analysis = analyzer.analyze_performance()

            # Should handle duplicates
            assert "summary_stats" in analysis


@pytest.mark.unit
class TestMetaAnalyzerThreadSafety:
    """Test thread-safety of meta analyzer."""

    @pytest.mark.asyncio
    async def test_concurrent_load_operations(self):
        """Test concurrent load operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            results_dir = Path(temp_dir) / "results"
            results_dir.mkdir()

            # Create multiple files
            for i in range(10):
                result = {"total_pnl": 1000 * (i + 1)}
                with open(results_dir / f"result_{i}.json", 'w') as f:
                    json.dump(result, f)

            analyzer = BacktestMetaAnalyzer(data_dir=str(results_dir))

            # Load multiple times concurrently
            import asyncio
            tasks = [analyzer.load_results() for _ in range(3)]
            results = await asyncio.gather(*tasks)

            # All should complete successfully
            assert all(r > 0 for r in results)

    def test_concurrent_analysis_operations(self):
        """Test concurrent analysis operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = BacktestMetaAnalyzer(data_dir=temp_dir)

            analyzer.df_results = pd.DataFrame({
                "sharpe_ratio": [1.0, 1.5, 2.0, 2.5, 3.0],
                "total_pnl": [1000, 1500, 2000, 2500, 3000],
                "max_drawdown": [-0.1, -0.08, -0.06, -0.05, -0.04],
                "win_rate": [0.5, 0.55, 0.6, 0.65, 0.7],
            })

            # Run multiple analyses
            import concurrent.futures

            def run_analysis():
                return analyzer.analyze_performance()

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(run_analysis) for _ in range(3)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

            # All should complete successfully
            assert all(isinstance(r, dict) for r in results)
