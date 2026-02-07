"""
Unit tests for Bonferroni Correction.

Tests multiple testing correction as described in Ernest Chan's
"Quantitative Trading" (Chapter 2).
"""

import numpy as np
import pytest

from app.backtesting.validation.bonferroni_correction import (
    BonferroniCorrector,
    HypothesisTest,
    MultipleTestResult,
    ParameterTestResult,
    correct_for_multiple_testing,
    is_strategy_significant,
)


class TestBonferroniCorrector:
    """Test suite for BonferroniCorrector."""

    @pytest.fixture
    def corrector(self):
        """Create a corrector instance with default FWER."""
        return BonferroniCorrector(family_wise_error_rate=0.05)

    @pytest.fixture
    def sample_p_values(self):
        """Create sample p-values."""
        return [0.001, 0.01, 0.03, 0.10, 0.25, 0.50]

    @pytest.fixture
    def sample_sharpe_ratios(self):
        """Create sample Sharpe ratios."""
        return {
            "strategy_a": 1.5,
            "strategy_b": 1.2,
            "strategy_c": 0.8,
            "strategy_d": 0.5,
            "strategy_e": 0.3,
        }

    def test_initialization(self, corrector):
        """Test corrector initialization."""
        assert corrector.family_wise_error_rate == 0.05

    def test_correct_p_values_bonferroni(self, corrector, sample_p_values):
        """Test standard Bonferroni correction."""
        result = corrector.correct_p_values(sample_p_values, method="bonferroni")

        # Check structure
        assert isinstance(result, MultipleTestResult)
        assert result.num_tests == len(sample_p_values)
        assert len(result.tests) == len(sample_p_values)

        # Check correction (p-values should be multiplied by num_tests)
        num_tests = len(sample_p_values)
        for i, test in enumerate(result.tests):
            expected_corrected = min(sample_p_values[i] * num_tests, 1.0)
            assert test.corrected_p_value == pytest.approx(expected_corrected, rel=0.01)

    def test_correct_p_values_holm(self, corrector, sample_p_values):
        """Test Holm-Bonferroni correction."""
        result = corrector.correct_p_values(sample_p_values, method="holm")

        assert isinstance(result, MultipleTestResult)
        assert result.correction_method == "holm"

        # Holm correction should be less conservative than Bonferroni
        bonf_result = corrector.correct_p_values(sample_p_values, method="bonferroni")

        # At least some corrected p-values should be smaller with Holm
        holm_values = [t.corrected_p_value for t in result.tests]
        bonf_values = [t.corrected_p_value for t in bonf_result.tests]

        # Not all Holm values should be >= Bonferroni values
        # (Holm can be smaller for some tests)
        assert any(h < b for h, b in zip(holm_values, bonf_values))

    def test_correct_p_values_bh(self, corrector, sample_p_values):
        """Test Benjamini-Hochberg correction."""
        result = corrector.correct_p_values(sample_p_values, method="bh")

        assert isinstance(result, MultipleTestResult)
        assert result.correction_method == "bh"

    def test_significance_counts(self, corrector, sample_p_values):
        """Test counting of significant results."""
        result = corrector.correct_p_values(sample_p_values, method="bonferroni")

        # Should have fewer significant results after correction
        sig_uncorrected = sum(1 for p in sample_p_values if p < 0.05)
        sig_corrected = sum(1 for t in result.tests if t.is_significant_corrected)

        assert sig_corrected <= sig_uncorrected

    def test_test_strategy_significance(self, corrector, sample_sharpe_ratios):
        """Test testing strategy significance."""
        result = corrector.test_strategy_significance(
            sample_sharpe_ratios, null_sharpe=0.0, num_observations=252
        )

        assert isinstance(result, MultipleTestResult)
        assert result.num_tests == len(sample_sharpe_ratios)

        # Check that tests are created
        for test in result.tests:
            assert isinstance(test, HypothesisTest)
            assert test.test_name in sample_sharpe_ratios

    def test_test_parameter_combinations(self, corrector):
        """Test testing parameter combinations."""
        backtest_results = [
            {
                "parameters": {"lookback": 10, "threshold": 2.0},
                "sharpe_ratio": 1.5,
                "num_trades": 100,
            },
            {
                "parameters": {"lookback": 20, "threshold": 2.0},
                "sharpe_ratio": 1.2,
                "num_trades": 80,
            },
            {
                "parameters": {"lookback": 30, "threshold": 2.0},
                "sharpe_ratio": 0.8,
                "num_trades": 60,
            },
        ]

        result = corrector.test_parameter_combinations(backtest_results, metric="sharpe_ratio")

        assert isinstance(result, ParameterTestResult)
        assert result.num_parameters_tested == len(backtest_results)
        assert isinstance(result.best_parameters, dict)
        assert result.best_sharpe_ratio == 1.5  # Best Sharpe from the list

    def test_empty_p_values(self, corrector):
        """Test handling of empty p-value list."""
        result = corrector.correct_p_values([])

        assert isinstance(result, MultipleTestResult)
        assert result.num_tests == 0
        assert len(result.tests) == 0

    def test_all_significant_p_values(self, corrector):
        """Test with all significant p-values."""
        all_sig = [0.001, 0.01, 0.02, 0.03, 0.04]

        result = corrector.correct_p_values(all_sig, method="bonferroni")

        # After correction, fewer should be significant
        sig_after = sum(1 for t in result.tests if t.is_significant_corrected)
        assert sig_after < len(all_sig)

    def test_none_significant_p_values(self, corrector):
        """Test with no significant p-values."""
        none_sig = [0.10, 0.20, 0.30, 0.40, 0.50]

        result = corrector.correct_p_values(none_sig, method="bonferroni")

        # None should be significant, even before correction
        assert result.num_significant_uncorrected == 0
        assert result.num_significant_corrected == 0

    def test_corrected_alpha_calculation(self, corrector, sample_p_values):
        """Test corrected significance level."""
        result = corrector.correct_p_values(sample_p_values, method="bonferroni")

        # Corrected alpha should be alpha / num_tests
        expected_alpha = 0.05 / len(sample_p_values)

        for test in result.tests:
            assert test.corrected_alpha == pytest.approx(expected_alpha, rel=0.01)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_correct_for_multiple_testing(self):
        """Test correct_for_multiple_testing function."""
        p_values = [0.01, 0.05, 0.10, 0.20]

        corrected = correct_for_multiple_testing(p_values, family_wise_error_rate=0.05)

        assert isinstance(corrected, list)
        assert len(corrected) == len(p_values)

        # Corrected values should be >= original values
        for orig, corr in zip(p_values, corrected):
            assert corr >= orig

    def test_is_strategy_significant(self):
        """Test is_strategy_significant function."""
        # Test with good Sharpe ratio
        is_sig = is_strategy_significant(
            sharpe_ratio=2.0, num_strategies_tested=10, num_observations=252
        )

        assert isinstance(is_sig, bool)

        # Test with poor Sharpe ratio
        is_sig = is_strategy_significant(
            sharpe_ratio=0.5, num_strategies_tested=10, num_observations=252
        )

        assert isinstance(is_sig, bool)


class TestHypothesisTest:
    """Test HypothesisTest dataclass."""

    def test_creation(self):
        """Test creating HypothesisTest."""
        test = HypothesisTest(
            test_name="test_strategy",
            null_hypothesis="No effect",
            p_value=0.01,
            test_statistic=2.5,
            is_significant_uncorrected=True,
            is_significant_corrected=False,
            corrected_p_value=0.10,
            corrected_alpha=0.01,
        )

        assert test.test_name == "test_strategy"
        assert test.p_value == 0.01
        assert test.is_significant_uncorrected
        assert not test.is_significant_corrected


class TestMultipleTestResult:
    """Test MultipleTestResult dataclass."""

    def test_creation(self):
        """Test creating MultipleTestResult."""
        tests = [
            HypothesisTest(
                test_name="test1",
                null_hypothesis="H0",
                p_value=0.01,
                test_statistic=2.0,
                is_significant_uncorrected=True,
                is_significant_corrected=True,
                corrected_p_value=0.04,
                corrected_alpha=0.025,
            )
        ]

        result = MultipleTestResult(
            family_wise_error_rate=0.05,
            num_tests=1,
            num_significant_uncorrected=1,
            num_significant_corrected=1,
            tests=tests,
            correction_method="bonferroni",
            false_discovery_rate=0.0,
        )

        assert result.num_tests == 1
        assert result.num_significant_corrected == 1
        assert result.correction_method == "bonferroni"


class TestParameterTestResult:
    """Test ParameterTestResult dataclass."""

    def test_creation(self):
        """Test creating ParameterTestResult."""
        result = ParameterTestResult(
            best_parameters={"lookback": 20},
            best_sharpe_ratio=1.5,
            is_significant_after_correction=True,
            num_parameters_tested=10,
            corrected_significance_level=0.005,
            all_results=[],
        )

        assert result.best_parameters == {"lookback": 20}
        assert result.best_sharpe_ratio == 1.5
        assert result.is_significant_after_correction


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_single_test(self):
        """Test with only one test (no correction needed)."""
        corrector = BonferroniCorrector()
        result = corrector.correct_p_values([0.03])

        # With one test, correction shouldn't change p-value much
        assert result.num_tests == 1
        assert result.tests[0].corrected_p_value == pytest.approx(0.03, rel=0.01)

    def test_very_small_p_values(self):
        """Test with very small p-values."""
        corrector = BonferroniCorrector()
        tiny_p_values = [1e-10, 1e-8, 1e-6]

        result = corrector.correct_p_values(tiny_p_values)

        # Even after correction, should still be significant
        assert result.num_significant_corrected > 0

    def test_p_value_exactly_at_threshold(self):
        """Test p-value exactly at significance threshold."""
        corrector = BonferroniCorrector()
        p_values = [0.05, 0.10, 0.15]

        result = corrector.correct_p_values(p_values)

        # Check behavior at threshold
        assert isinstance(result, MultipleTestResult)

    def test_large_number_of_tests(self):
        """Test with large number of tests."""
        corrector = BonferroniCorrector()
        # Simulate testing 100 strategies
        p_values = list(np.random.uniform(0, 0.1, 100))

        result = corrector.correct_p_values(p_values)

        assert result.num_tests == 100
        # Corrected alpha should be very small
        assert result.tests[0].corrected_alpha == pytest.approx(0.05 / 100, rel=0.01)
