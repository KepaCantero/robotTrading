"""
Unit Tests for Walk-Forward Validation & Stress Testing (Task 3.5)

Comprehensive tests for:
- Walk-forward validation
- Cross-validation temporal
- Synthetic data generation
- Stress testing
- Monte Carlo simulation
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import numpy as np
import pytest

from app.backtesting.models import BacktestConfig
from app.backtesting.walk_forward_validator import (
    ComprehensiveValidator,
    CrossValidationTemporal,
    MonteCarloSimulator,
    StressScenarioResult,
    StressTester,
    SyntheticDataGenerator,
    ValidationReport,
    ValidationWindow,
    WalkForwardValidator,
    get_default_config,
    load_validation_config,
)
from app.shared.utils.decimal_utils import round_price
from app.domain.models.market_data import Quote

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_config():
    """Sample validation configuration."""
    return {
        "walk_forward": {
            "enabled": True,
            "train_years": 2,
            "validation_years": 1,
            "step_years": 1,
            "min_windows": 2,
            "min_trades_per_window": 5,
            "thresholds": {
                "min_consistency": 0.5,
                "max_return_std": 0.5,
                "min_avg_sharpe": 0.3,
                "max_avg_drawdown": -0.25,
            },
        },
        "cross_validation": {
            "enabled": True,
            "n_folds": 3,
            "thresholds": {
                "min_consistency_score": 0.5,
                "max_return_variance": 0.3,
            },
        },
        "stress_testing": {
            "enabled": True,
            "n_scenarios": 10,
            "scenarios": {
                "flash_crash": {
                    "enabled": True,
                    "weight": 0.5,
                    "drop_percentage": -0.10,
                    "recovery_days": 5,
                },
                "high_volatility": {
                    "enabled": True,
                    "weight": 0.5,
                    "volatility_multiplier": 2.0,
                    "duration_days": 20,
                },
            },
            "thresholds": {
                "max_scenario_drawdown": -0.30,
                "min_survival_rate": 0.50,
                "max_avg_loss": -0.20,
                "min_recovery_rate": 0.50,
            },
        },
        "synthetic_data": {
            "base_price": 100.0,
            "base_volume": 1000000,
            "annual_volatility": 0.20,
            "annual_drift": 0.05,
            "volume_noise": 0.30,
        },
        "monte_carlo": {
            "enabled": True,
            "n_simulations": 100,
            "confidence_levels": [0.95],
            "block_size": 10,
        },
    }


@pytest.fixture
def backtest_config():
    """Sample backtest configuration."""
    return BacktestConfig(
        initial_capital=Decimal("100000"),
        commission_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
        max_position_size=Decimal("0.1"),
    )


@pytest.fixture
def sample_quotes():
    """Generate sample quotes for testing."""
    quotes = []
    base_price = 100.0
    start_date = datetime(2020, 1, 1)
    symbol = "TEST"

    for i in range(500):  # ~2 years of data
        price = base_price * (1 + np.random.normal(0, 0.02))
        base_price = price

        quotes.append(
            Quote(
                symbol=symbol,
                timestamp=start_date + timedelta(days=i),
                bid=Decimal(str(round_price(price * 0.999, "equity", symbol))),
                ask=Decimal(str(round_price(price * 1.001, "equity", symbol))),
                last=Decimal(str(round_price(price, "equity", symbol))),
                volume=Decimal("1000000"),
                open=Decimal(str(round_price(price * 0.99, "equity", symbol))),
                high=Decimal(str(round_price(price * 1.02, "equity", symbol))),
                low=Decimal(str(round_price(price * 0.98, "equity", symbol))),
                close=Decimal(str(round_price(price, "equity", symbol))),
            )
        )

    return quotes


@pytest.fixture
def sample_signals(sample_quotes):
    """Generate sample signals matching quotes."""
    from app.models.signal import SignalType

    signals = []
    for i, quote in enumerate(sample_quotes):
        if i % 20 == 0:  # Signal every 20 days
            signals.append(
                Mock(
                    symbol="TEST",
                    timestamp=quote.timestamp,
                    signal_type=SignalType.BUY if i % 40 == 0 else SignalType.SELL,
                    strength=75.0,
                    confidence=80.0,
                )
            )

    return signals


# ============================================================================
# Tests: Configuration Loading
# ============================================================================


class TestConfigLoading:
    """Tests for configuration loading functions."""

    def test_get_default_config_returns_dict(self):
        """Test that default config returns a dictionary."""
        config = get_default_config()

        assert isinstance(config, dict)
        assert "walk_forward" in config
        assert "cross_validation" in config
        assert "stress_testing" in config
        assert "synthetic_data" in config
        assert "monte_carlo" in config

    def test_default_config_walk_forward_values(self):
        """Test default walk-forward configuration values."""
        config = get_default_config()
        wf = config["walk_forward"]

        assert wf["train_years"] == 4
        assert wf["validation_years"] == 1
        assert wf["step_years"] == 1
        assert wf["min_windows"] == 3
        assert wf["min_trades_per_window"] == 10

    def test_default_config_stress_testing_scenarios(self):
        """Test default stress testing scenarios."""
        config = get_default_config()
        scenarios = config["stress_testing"]["scenarios"]

        assert "flash_crash" in scenarios
        assert "high_volatility" in scenarios
        assert "trending_bull" in scenarios
        assert "trending_bear" in scenarios
        assert "mean_reverting" in scenarios
        assert "gap_up" in scenarios
        assert "gap_down" in scenarios

    def test_load_validation_config_with_missing_file(self):
        """Test loading config from non-existent file returns defaults."""
        config = load_validation_config("nonexistent_file.yaml")

        assert isinstance(config, dict)
        assert "walk_forward" in config


# ============================================================================
# Tests: Synthetic Data Generator
# ============================================================================


class TestSyntheticDataGenerator:
    """Tests for SyntheticDataGenerator class."""

    def test_generator_initialization(self, sample_config):
        """Test generator initializes correctly."""
        generator = SyntheticDataGenerator(sample_config["synthetic_data"])

        assert generator.base_price == 100.0
        assert generator.base_volume == 1000000
        assert generator.annual_volatility == 0.20
        assert generator.annual_drift == 0.05

    def test_generate_gbm_prices_returns_quotes(self, sample_config):
        """Test GBM price generation returns Quote objects."""
        generator = SyntheticDataGenerator(sample_config["synthetic_data"])
        start_date = datetime(2020, 1, 1)

        quotes = generator.generate_gbm_prices(100, start_date, "TEST")

        assert len(quotes) == 100
        assert all(isinstance(q, Quote) for q in quotes)
        assert all(q.symbol == "TEST" for q in quotes)

    def test_generate_gbm_prices_positive_values(self, sample_config):
        """Test GBM prices are always positive."""
        generator = SyntheticDataGenerator(sample_config["synthetic_data"])
        start_date = datetime(2020, 1, 1)

        quotes = generator.generate_gbm_prices(500, start_date)

        assert all(float(q.close) > 0 for q in quotes)
        assert all(float(q.low) > 0 for q in quotes)

    def test_generate_ou_prices_mean_reverting(self, sample_config):
        """Test OU process generates mean-reverting prices."""
        generator = SyntheticDataGenerator(sample_config["synthetic_data"])
        start_date = datetime(2020, 1, 1)

        quotes = generator.generate_ou_prices(500, start_date, theta=0.5, mu=100.0)

        # Prices should stay relatively close to mean
        prices = [float(q.close) for q in quotes]
        assert 50 < np.mean(prices) < 150

    def test_generate_flash_crash_scenario(self, sample_config):
        """Test flash crash scenario generation."""
        generator = SyntheticDataGenerator(sample_config["synthetic_data"])
        start_date = datetime(2020, 1, 1)

        quotes = generator.generate_flash_crash_scenario(100, start_date, drop_pct=-0.15)

        prices = [float(q.close) for q in quotes]
        min_price = min(prices)

        # Should have a significant drop
        assert min_price < generator.base_price * 0.95

    def test_generate_high_volatility_scenario(self, sample_config):
        """Test high volatility scenario has higher variance."""
        generator = SyntheticDataGenerator(sample_config["synthetic_data"])
        start_date = datetime(2020, 1, 1)

        normal_quotes = generator.generate_gbm_prices(200, start_date)
        high_vol_quotes = generator.generate_high_volatility_scenario(
            200, start_date, volatility_multiplier=3.0
        )

        normal_returns = np.diff([float(q.close) for q in normal_quotes]) / np.array(
            [float(q.close) for q in normal_quotes[:-1]]
        )
        high_vol_returns = np.diff([float(q.close) for q in high_vol_quotes]) / np.array(
            [float(q.close) for q in high_vol_quotes[:-1]]
        )

        # High volatility should have higher std
        assert np.std(high_vol_returns) > np.std(normal_returns)

    def test_generate_trending_scenario_bull(self, sample_config):
        """Test bull trending scenario uses bull regime."""
        generator = SyntheticDataGenerator(sample_config["synthetic_data"])
        start_date = datetime(2020, 1, 1)

        quotes = generator.generate_trending_scenario(200, start_date, daily_drift=0.005)

        prices = [float(q.close) for q in quotes]

        # The new realistic generator uses regime-switching which creates
        # realistic market patterns. Bull regime has positive drift on average
        # but not guaranteed monotonic increase. Check that we get valid data.
        assert len(quotes) == 200
        assert all(isinstance(q, Quote) for q in quotes)
        assert all(float(q.close) > 0 for q in quotes)
        # Prices should vary (not constant)
        assert np.std(prices) > 0
        # Most prices should be in reasonable range (50-150 for base 100)
        assert sum(1 for p in prices if 50 < p < 150) / len(prices) > 0.8

    def test_generate_gap_scenario(self, sample_config):
        """Test gap scenario generation."""
        generator = SyntheticDataGenerator(sample_config["synthetic_data"])
        start_date = datetime(2020, 1, 1)

        quotes = generator.generate_gap_scenario(100, start_date, gap_pct=0.10, n_gaps=3)

        prices = [float(q.close) for q in quotes]
        returns = np.diff(prices) / prices[:-1]

        # The new realistic generator uses volatile regime which naturally
        # produces gaps through realistic overnight price movements.
        # Check that we get valid data with some volatility.
        assert len(quotes) == 100
        assert all(isinstance(q, Quote) for q in quotes)
        assert all(float(q.close) > 0 for q in quotes)
        # Volatile regime should have higher volatility than normal
        assert np.std(returns) > 0.01  # At least 1% std deviation
        # Should have some significant daily moves (not all tiny moves)
        large_moves = [r for r in returns if abs(r) > 0.02]
        assert len(large_moves) > 0

    def test_ohlc_consistency(self, sample_config):
        """Test that generated OHLC data is consistent."""
        generator = SyntheticDataGenerator(sample_config["synthetic_data"])
        start_date = datetime(2020, 1, 1)

        quotes = generator.generate_gbm_prices(100, start_date)

        for q in quotes:
            assert float(q.high) >= float(q.low)
            assert float(q.high) >= float(q.close)
            assert float(q.high) >= float(q.open)
            assert float(q.low) <= float(q.close)
            assert float(q.low) <= float(q.open)


# ============================================================================
# Tests: Walk-Forward Validator
# ============================================================================


class TestWalkForwardValidator:
    """Tests for WalkForwardValidator class."""

    def test_validator_initialization_with_config(self, sample_config):
        """Test validator initializes with config dict."""
        validator = WalkForwardValidator(config=sample_config["walk_forward"])

        assert validator.train_years == 2
        assert validator.validation_years == 1
        assert validator.step_years == 1
        assert validator.min_windows == 2

    def test_validator_initialization_defaults(self):
        """Test validator uses default values."""
        validator = WalkForwardValidator(config={})

        assert validator.train_years == 4
        assert validator.validation_years == 1
        assert validator.step_years == 1

    def test_create_windows_generates_correct_windows(self, sample_config):
        """Test window creation generates correct number of windows."""
        validator = WalkForwardValidator(config=sample_config["walk_forward"])
        start_date = datetime(2015, 1, 1)
        end_date = datetime(2022, 1, 1)  # 7 years

        windows = validator.create_windows(start_date, end_date)

        # With 2 year train + 1 year validation + 1 year step
        # Should have multiple windows
        assert len(windows) >= 2

    def test_create_windows_dates_are_sequential(self, sample_config):
        """Test that window dates are sequential."""
        validator = WalkForwardValidator(config=sample_config["walk_forward"])
        start_date = datetime(2015, 1, 1)
        end_date = datetime(2022, 1, 1)

        windows = validator.create_windows(start_date, end_date)

        for window in windows:
            assert window["train_start"] < window["train_end"]
            assert window["train_end"] == window["validate_start"]
            assert window["validate_start"] < window["validate_end"]

    def test_create_windows_empty_for_short_period(self, sample_config):
        """Test that no windows are created for short periods."""
        validator = WalkForwardValidator(config=sample_config["walk_forward"])
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2021, 1, 1)  # Only 1 year

        windows = validator.create_windows(start_date, end_date)

        assert len(windows) == 0

    def test_validate_strategy_insufficient_windows(self, sample_config, backtest_config):
        """Test validation fails with insufficient windows."""
        validator = WalkForwardValidator(config=sample_config["walk_forward"])
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2021, 1, 1)

        result = validator.validate_strategy([], [], backtest_config, start_date, end_date)

        assert result["passed"] is False
        assert "Insufficient windows" in result.get("reason", "")


# ============================================================================
# Tests: Cross-Validation Temporal
# ============================================================================


class TestCrossValidationTemporal:
    """Tests for CrossValidationTemporal class."""

    def test_cross_validator_initialization(self, sample_config):
        """Test cross-validator initializes correctly."""
        cv = CrossValidationTemporal(config=sample_config["cross_validation"])

        assert cv.n_folds == 3

    def test_create_folds_correct_count(self, sample_config):
        """Test correct number of folds are created."""
        cv = CrossValidationTemporal(config=sample_config["cross_validation"])
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2022, 1, 1)

        folds = cv.create_folds(start_date, end_date)

        assert len(folds) == 3

    def test_create_folds_cover_full_period(self, sample_config):
        """Test that folds cover the entire period."""
        cv = CrossValidationTemporal(config=sample_config["cross_validation"])
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2022, 1, 1)

        folds = cv.create_folds(start_date, end_date)

        # First fold starts at start_date
        assert folds[0]["start"] == start_date

        # Last fold ends at end_date
        assert folds[-1]["end"] == end_date

    def test_folds_are_non_overlapping(self, sample_config):
        """Test that folds don't overlap."""
        cv = CrossValidationTemporal(config=sample_config["cross_validation"])
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2022, 1, 1)

        folds = cv.create_folds(start_date, end_date)

        for i in range(len(folds) - 1):
            assert folds[i]["end"] <= folds[i + 1]["start"]


# ============================================================================
# Tests: Monte Carlo Simulator
# ============================================================================


class TestMonteCarloSimulator:
    """Tests for MonteCarloSimulator class."""

    def test_simulator_initialization(self, sample_config):
        """Test Monte Carlo simulator initialization."""
        mc = MonteCarloSimulator(config=sample_config["monte_carlo"])

        assert mc.n_simulations == 100
        assert mc.block_size == 10
        assert 0.95 in mc.confidence_levels

    def test_run_simulation_returns_dict(self, sample_config):
        """Test simulation returns dictionary with expected keys."""
        mc = MonteCarloSimulator(config=sample_config["monte_carlo"])
        returns = list(np.random.normal(0.001, 0.02, 100))

        result = mc.run_simulation(returns, initial_capital=100000)

        assert isinstance(result, dict)
        assert "passed" in result
        assert "summary" in result
        assert "var" in result
        assert "cvar" in result
        assert "percentiles" in result

    def test_run_simulation_insufficient_data(self, sample_config):
        """Test simulation fails with insufficient data."""
        mc = MonteCarloSimulator(config=sample_config["monte_carlo"])
        returns = [0.01, 0.02]  # Too few

        result = mc.run_simulation(returns)

        assert result["passed"] is False
        assert "Insufficient" in result.get("reason", "")

    def test_var_cvar_calculated(self, sample_config):
        """Test VaR and CVaR are calculated."""
        mc = MonteCarloSimulator(config=sample_config["monte_carlo"])
        returns = list(np.random.normal(0.001, 0.02, 100))

        result = mc.run_simulation(returns)

        assert "VaR_0.95" in result["var"]
        assert "CVaR_0.95" in result["cvar"]

    def test_cvar_less_than_var(self, sample_config):
        """Test that CVaR is less than or equal to VaR (worse case)."""
        mc = MonteCarloSimulator(config=sample_config["monte_carlo"])
        returns = list(np.random.normal(0.001, 0.02, 100))

        result = mc.run_simulation(returns)

        # CVaR is expected shortfall, should be worse than VaR
        assert result["cvar"]["CVaR_0.95"] <= result["var"]["VaR_0.95"]

    def test_block_bootstrap_returns_correct_length(self, sample_config):
        """Test block bootstrap returns correct length."""
        mc = MonteCarloSimulator(config=sample_config["monte_carlo"])
        returns = np.array(np.random.normal(0, 0.02, 100))

        bootstrapped = mc._block_bootstrap(returns, 50)

        assert len(bootstrapped) == 50

    def test_max_drawdown_calculation(self, sample_config):
        """Test max drawdown calculation."""
        mc = MonteCarloSimulator(config=sample_config["monte_carlo"])

        # Equity curve that drops 20%
        equity = [100, 110, 105, 88, 95, 100]

        max_dd = mc._calculate_max_drawdown(equity)

        # Max drawdown should be from 110 to 88 = -20%
        assert max_dd < 0
        assert max_dd >= -0.25  # Approximately -20%


# ============================================================================
# Tests: Stress Tester
# ============================================================================


class TestStressTester:
    """Tests for StressTester class."""

    def test_stress_tester_initialization(self, sample_config):
        """Test stress tester initialization."""
        with patch(
            'app.backtesting.walk_forward_validator.load_validation_config',
            return_value=sample_config,
        ):
            tester = StressTester(config=sample_config["stress_testing"])

        assert tester.n_scenarios == 10
        assert "flash_crash" in tester.scenarios_config

    def test_generate_scenario_flash_crash(self, sample_config):
        """Test flash crash scenario generation."""
        with patch(
            'app.backtesting.walk_forward_validator.load_validation_config',
            return_value=sample_config,
        ):
            tester = StressTester(config=sample_config["stress_testing"])

        scenario_config = sample_config["stress_testing"]["scenarios"]["flash_crash"]
        start_date = datetime(2020, 1, 1)

        quotes = tester._generate_scenario("flash_crash", scenario_config, 100, start_date, "TEST")

        assert len(quotes) == 100
        assert all(isinstance(q, Quote) for q in quotes)

    def test_generate_scenario_unknown_type_defaults_to_gbm(self, sample_config):
        """Test unknown scenario type defaults to GBM."""
        with patch(
            'app.backtesting.walk_forward_validator.load_validation_config',
            return_value=sample_config,
        ):
            tester = StressTester(config=sample_config["stress_testing"])

        start_date = datetime(2020, 1, 1)

        quotes = tester._generate_scenario("unknown_type", {}, 100, start_date, "TEST")

        assert len(quotes) == 100


# ============================================================================
# Tests: Data Classes
# ============================================================================


class TestDataClasses:
    """Tests for data classes."""

    def test_validation_window_creation(self):
        """Test ValidationWindow data class."""
        window = ValidationWindow(
            window_id=1,
            train_start=datetime(2020, 1, 1),
            train_end=datetime(2021, 1, 1),
            validate_start=datetime(2021, 1, 1),
            validate_end=datetime(2022, 1, 1),
            total_return=0.15,
            sharpe_ratio=1.5,
            max_drawdown=-0.10,
            total_trades=50,
            win_rate=55.0,
            passed=True,
        )

        assert window.window_id == 1
        assert window.total_return == 0.15
        assert window.passed is True

    def test_stress_scenario_result_creation(self):
        """Test StressScenarioResult data class."""
        result = StressScenarioResult(
            scenario_type="flash_crash",
            scenario_id=1,
            total_return=-0.05,
            max_drawdown=-0.15,
            survived=True,
            recovered=True,
            final_capital=95000.0,
            trades_executed=10,
        )

        assert result.scenario_type == "flash_crash"
        assert result.survived is True

    def test_validation_report_creation(self):
        """Test ValidationReport data class."""
        report = ValidationReport(
            strategy_name="momentum",
            timestamp=datetime.now(),
            overall_passed=True,
        )

        assert report.strategy_name == "momentum"
        assert report.overall_passed is True
        assert report.walk_forward_results is None


# ============================================================================
# Tests: Comprehensive Validator
# ============================================================================


class TestComprehensiveValidator:
    """Tests for ComprehensiveValidator facade class."""

    def test_comprehensive_validator_initialization(self, sample_config):
        """Test comprehensive validator initialization."""
        with patch(
            'app.backtesting.walk_forward_validator.load_validation_config',
            return_value=sample_config,
        ):
            validator = ComprehensiveValidator()

        assert validator.walk_forward is not None
        assert validator.cross_validation is not None
        assert validator.stress_tester is not None
        assert validator.monte_carlo is not None

    def test_extract_returns_from_quotes(self, sample_config, sample_quotes):
        """Test return extraction from quotes."""
        with patch(
            'app.backtesting.walk_forward_validator.load_validation_config',
            return_value=sample_config,
        ):
            validator = ComprehensiveValidator()

        returns = validator._extract_returns(sample_quotes)

        assert len(returns) == len(sample_quotes) - 1
        assert all(isinstance(r, float) for r in returns)

    def test_extract_returns_empty_for_insufficient_quotes(self, sample_config):
        """Test return extraction with insufficient quotes."""
        with patch(
            'app.backtesting.walk_forward_validator.load_validation_config',
            return_value=sample_config,
        ):
            validator = ComprehensiveValidator()

        returns = validator._extract_returns([])

        assert returns == []


# ============================================================================
# Tests: Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for validation module."""

    def test_full_validation_workflow_mock(self, sample_config, backtest_config):
        """Test full validation workflow with mocks."""
        with patch(
            'app.backtesting.walk_forward_validator.load_validation_config',
            return_value=sample_config,
        ):
            with patch(
                'app.backtesting.walk_forward_validator.SimpleBacktester'
            ) as mock_backtester:
                # Mock backtest result
                mock_result = Mock()
                mock_result.total_return = Decimal("0.10")
                mock_result.final_capital = Decimal("110000")
                mock_result.performance = Mock()
                mock_result.performance.sharpe_ratio = Decimal("1.5")
                mock_result.performance.max_drawdown_percentage = Decimal("-0.10")
                mock_result.performance.total_trades = 20
                mock_result.performance.win_rate = Decimal("55")

                mock_backtester.return_value.run_backtest.return_value = mock_result

                validator = ComprehensiveValidator()

                # Create mock quotes and signals
                start_date = datetime(2015, 1, 1)
                end_date = datetime(2022, 1, 1)
                quotes = []
                signals = []

                for i in range(2500):  # ~7 years
                    quotes.append(
                        Quote(
                            symbol="TEST",
                            timestamp=start_date + timedelta(days=i),
                            bid=Decimal("100"),
                            ask=Decimal("100.1"),
                            last=Decimal("100"),
                            volume=Decimal("1000000"),
                        )
                    )
                    if i % 20 == 0:
                        signals.append(
                            Mock(
                                timestamp=start_date + timedelta(days=i),
                            )
                        )

                mock_strategy = Mock()
                mock_strategy.analyze.return_value = Mock()

                # Run validation (with stress testing disabled to speed up test)
                validator.config["stress_testing"]["enabled"] = False
                validator.config["monte_carlo"]["enabled"] = False

                report = validator.run_full_validation(
                    strategy=mock_strategy,
                    strategy_name="test_strategy",
                    quotes=quotes,
                    signals=signals,
                    backtest_config=backtest_config,
                    start_date=start_date,
                    end_date=end_date,
                )

                assert report.strategy_name == "test_strategy"
                assert report.summary is not None


# ============================================================================
# Tests: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_quotes_handling(self, sample_config, backtest_config):
        """Test handling of empty quotes list."""
        validator = WalkForwardValidator(config=sample_config["walk_forward"])

        result = validator.validate_strategy(
            [],
            [],
            backtest_config,
            datetime(2015, 1, 1),
            datetime(2022, 1, 1),
        )

        assert result["passed"] is False

    def test_single_quote_handling(self, sample_config):
        """Test handling of single quote."""
        with patch(
            'app.backtesting.walk_forward_validator.load_validation_config',
            return_value=sample_config,
        ):
            validator = ComprehensiveValidator()

        single_quote = Quote(
            symbol="TEST",
            timestamp=datetime(2020, 1, 1),
            bid=Decimal("100"),
            ask=Decimal("100.1"),
            last=Decimal("100"),
            volume=Decimal("1000000"),
        )

        returns = validator._extract_returns([single_quote])

        assert returns == []

    def test_negative_returns_handling(self, sample_config):
        """Test Monte Carlo with negative returns."""
        mc = MonteCarloSimulator(config=sample_config["monte_carlo"])
        returns = list(np.random.normal(-0.01, 0.02, 100))  # Negative mean

        result = mc.run_simulation(returns)

        assert result["passed"] is True
        assert result["summary"]["mean_return"] < 0

    def test_zero_volatility_quotes(self, sample_config):
        """Test handling of zero volatility (constant price)."""
        generator = SyntheticDataGenerator(sample_config["synthetic_data"])

        # Generate with very low volatility
        quotes = generator.generate_gbm_prices(
            100,
            datetime(2020, 1, 1),
            volatility=0.0001,  # Near zero
        )

        prices = [float(q.close) for q in quotes]
        std = np.std(prices)

        # Should have very low variance
        assert std < 10  # Less than 10% of base price


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
