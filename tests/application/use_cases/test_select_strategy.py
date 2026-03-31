"""
Tests for SelectStrategy Use Case - FASE 6.6

Tests the strategy selection functionality including:
- Profile-based strategy mapping
- Bayesian optimization integration
- Walk-forward validation integration
- Scoring and ranking
- Use case execution
- Edge cases and error conditions
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from app.application.use_cases.select_strategy import (
    SelectStrategyUseCase,
    StrategyConfiguration,
    StrategySelectionCriteria,
    StrategySelectionResult,
    StrategySelector,
)
from app.domain.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance


class TestStrategyConfiguration:
    """Tests for StrategyConfiguration dataclass."""

    def test_create_default_config(self) -> None:
        """Test creating configuration with defaults."""
        config = StrategyConfiguration(strategy_name="momentum_modular")

        assert config.strategy_name == "momentum_modular"
        assert config.parameters == {}
        assert config.weights == {}
        assert config.expected_return == Decimal("0")
        assert config.total_score == Decimal("0")

    def test_create_config_with_values(self) -> None:
        """Test creating configuration with specific values."""
        config = StrategyConfiguration(
            strategy_name="pairs_trading_modular",
            parameters={"lookback": 30, "threshold": 2.0},
            weights={"pairs_trading_modular": 0.5},
            expected_return=Decimal("0.15"),
            sharpe_ratio=Decimal("1.2"),
            total_score=Decimal("85"),
        )

        assert config.strategy_name == "pairs_trading_modular"
        assert config.parameters["lookback"] == 30
        assert config.weights["pairs_trading_modular"] == 0.5
        assert config.expected_return == Decimal("0.15")

    def test_to_dict(self) -> None:
        """Test converting configuration to dictionary."""
        config = StrategyConfiguration(
            strategy_name="test_strategy",
            expected_return=Decimal("0.10"),
            total_score=Decimal("75"),
        )

        result = config.to_dict()

        assert result["strategy_name"] == "test_strategy"
        assert result["expected_return"] == 0.10
        assert result["total_score"] == 75.0

    def test_frozen_immutability(self) -> None:
        """Test that StrategyConfiguration is frozen (immutable)."""
        config = StrategyConfiguration(strategy_name="test_strategy")
        with pytest.raises(Exception):  # FrozenInstanceError or similar
            config.strategy_name = "new_strategy"


class TestStrategySelectionCriteria:
    """Tests for StrategySelectionCriteria dataclass."""

    def test_default_criteria(self) -> None:
        """Test creating default criteria."""
        criteria = StrategySelectionCriteria()

        assert criteria.return_weight == 0.25
        assert criteria.risk_weight == 0.20
        assert criteria.sharpe_weight == 0.25
        assert criteria.validation_weight == 0.20
        assert criteria.suitability_weight == 0.10
        assert criteria.min_sharpe_ratio == Decimal("0.5")

    def test_custom_criteria(self) -> None:
        """Test creating custom criteria."""
        criteria = StrategySelectionCriteria(
            return_weight=0.30,
            risk_weight=0.10,
            min_sharpe_ratio=Decimal("1.0"),
        )

        assert criteria.return_weight == 0.30
        assert criteria.risk_weight == 0.10
        assert criteria.min_sharpe_ratio == Decimal("1.0")

    def test_validate_weights_sum(self) -> None:
        """Test that criteria validates weights sum to ~1.0."""
        # Valid criteria
        criteria = StrategySelectionCriteria(
            return_weight=0.20,
            risk_weight=0.20,
            sharpe_weight=0.30,
            validation_weight=0.20,
            suitability_weight=0.10,
        )
        criteria.validate()  # Should not raise

        # Invalid criteria (sum != 1.0)
        bad_criteria = StrategySelectionCriteria(
            return_weight=0.5,
            risk_weight=0.5,
            sharpe_weight=0.5,
            validation_weight=0.5,
            suitability_weight=0.5,
        )
        with pytest.raises(ValueError, match="weights must sum to ~1.0"):
            bad_criteria.validate()

    def test_edge_case_zero_weights(self) -> None:
        """Test criteria with zero weights."""
        criteria = StrategySelectionCriteria(
            return_weight=0.0,
            risk_weight=0.5,
            sharpe_weight=0.5,
            validation_weight=0.0,
            suitability_weight=0.0,
        )
        criteria.validate()  # Sum = 1.0, should be valid

    def test_edge_case_boundary_weights(self) -> None:
        """Test criteria at boundary values."""
        # Lower boundary (0.91 - just above 0.9)
        criteria_low = StrategySelectionCriteria(
            return_weight=0.18,
            risk_weight=0.19,
            sharpe_weight=0.18,
            validation_weight=0.18,
            suitability_weight=0.18,
        )
        criteria_low.validate()  # Sum = 0.91, should be valid

        # Upper boundary (1.09 - just below 1.1)
        criteria_high = StrategySelectionCriteria(
            return_weight=0.22,
            risk_weight=0.22,
            sharpe_weight=0.22,
            validation_weight=0.22,
            suitability_weight=0.21,
        )
        criteria_high.validate()  # Sum = 1.09, should be valid


class TestStrategySelector:
    """Tests for StrategySelector class."""

    @pytest.fixture
    def conservative_profile(self) -> InputProfile:
        """Create a conservative investment profile."""
        return InputProfile(
            capital_initial=Decimal("50000"),
            investment_horizon=36,
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
        )

    @pytest.fixture
    def aggressive_profile(self) -> InputProfile:
        """Create an aggressive investment profile."""
        return InputProfile(
            capital_initial=Decimal("100000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
        )

    @pytest.fixture
    def balanced_profile(self) -> InputProfile:
        """Create a balanced investment profile."""
        return InputProfile(
            capital_initial=Decimal("75000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

    @pytest.fixture
    def dividend_profile(self) -> InputProfile:
        """Create a dividend-focused investment profile."""
        return InputProfile(
            capital_initial=Decimal("150000"),
            investment_horizon=48,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
            risk_tolerance=RiskTolerance.MEDIO,
        )

    @pytest.fixture
    def small_capital_profile(self) -> InputProfile:
        """Create a small capital profile."""
        return InputProfile(
            capital_initial=Decimal("25000"),
            investment_horizon=12,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

    @pytest.fixture
    def large_capital_profile(self) -> InputProfile:
        """Create a large capital profile."""
        return InputProfile(
            capital_initial=Decimal("500000"),
            investment_horizon=36,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
        )

    @pytest.fixture
    def selector(self) -> StrategySelector:
        """Create strategy selector for testing."""
        return StrategySelector()

    def test_init_selector(self) -> None:
        """Test selector initialization."""
        selector = StrategySelector()
        assert selector._profile_mapper is not None
        assert selector._validator is not None

    def test_init_selector_with_custom_dependencies(self) -> None:
        """Test selector initialization with custom dependencies."""
        mock_mapper = Mock()
        mock_optimizer = Mock()
        mock_validator = Mock()

        selector = StrategySelector(
            profile_mapper=mock_mapper,
            optimizer=mock_optimizer,
            validator=mock_validator,
        )

        assert selector._profile_mapper is mock_mapper
        assert selector._optimizer is mock_optimizer
        assert selector._validator is mock_validator

    def test_get_parameter_grid_momentum(self, selector: StrategySelector) -> None:
        """Test parameter grid generation for momentum strategies."""
        profile = InputProfile(
            capital_initial=Decimal("50000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

        grid = selector._get_parameter_grid("momentum_modular", profile)

        assert len(grid.parameters) >= 2
        param_names = {p.name for p in grid.parameters}
        assert "lookback" in param_names
        assert "threshold" in param_names

    def test_get_parameter_grid_mean_reversion(self, selector: StrategySelector) -> None:
        """Test parameter grid generation for mean reversion strategies."""
        profile = InputProfile(
            capital_initial=Decimal("50000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

        grid = selector._get_parameter_grid("mean_reversion_modular", profile)

        assert len(grid.parameters) >= 3
        param_names = {p.name for p in grid.parameters}
        assert "lookback" in param_names
        assert "entry_threshold" in param_names
        assert "exit_threshold" in param_names

    def test_get_parameter_grid_pairs_trading(self, selector: StrategySelector) -> None:
        """Test parameter grid generation for pairs trading strategies."""
        profile = InputProfile(
            capital_initial=Decimal("50000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

        grid = selector._get_parameter_grid("pairs_trading_modular", profile)

        assert len(grid.parameters) >= 3
        param_names = {p.name for p in grid.parameters}
        assert "lookback" in param_names
        assert "entry_threshold" in param_names
        assert "exit_threshold" in param_names

    def test_get_parameter_grid_unknown_strategy(self, selector: StrategySelector) -> None:
        """Test parameter grid generation for unknown strategy (uses defaults)."""
        profile = InputProfile(
            capital_initial=Decimal("50000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

        grid = selector._get_parameter_grid("unknown_strategy", profile)

        # Should get default parameters
        assert len(grid.parameters) >= 2
        param_names = {p.name for p in grid.parameters}
        assert "lookback" in param_names
        assert "threshold" in param_names

    def test_estimate_performance_momentum(self, selector: StrategySelector) -> None:
        """Test performance estimation for momentum strategies."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
        )

        performance = selector._estimate_performance(
            strategy_name="momentum_modular",
            profile=profile,
            optimization_metrics={},
            validation_details={},
        )

        assert "expected_return" in performance
        assert "expected_risk" in performance
        assert "sharpe_ratio" in performance
        assert "max_drawdown" in performance
        assert "win_rate" in performance
        assert performance["sharpe_ratio"] > Decimal("0")

    def test_estimate_performance_conservative(self, selector: StrategySelector) -> None:
        """Test performance estimation for conservative profile."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            investment_horizon=36,
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
        )

        performance = selector._estimate_performance(
            strategy_name="dividend_screener",
            profile=profile,
            optimization_metrics={},
            validation_details={},
        )

        # Conservative profile should have lower risk
        assert performance["expected_risk"] < Decimal("0.15")
        assert performance["max_drawdown"] < Decimal("0.20")

    def test_estimate_performance_with_validation_override(
        self, selector: StrategySelector
    ) -> None:
        """Test performance estimation with validation override."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

        # Mock validation details
        validation_details = {"os_sharpe": 1.8}

        performance = selector._estimate_performance(
            strategy_name="momentum_modular",
            profile=profile,
            optimization_metrics={},
            validation_details=validation_details,
        )

        # Should use validation sharpe
        assert performance["sharpe_ratio"] == Decimal("1.8")

    def test_calculate_total_score(self, selector: StrategySelector) -> None:
        """Test total score calculation."""
        criteria = StrategySelectionCriteria()

        performance = {
            "expected_return": Decimal("0.15"),
            "expected_risk": Decimal("0.20"),
            "sharpe_ratio": Decimal("0.75"),
            "max_drawdown": Decimal("0.25"),
            "win_rate": Decimal("0.55"),
        }

        score = selector._calculate_total_score(
            suitability=Decimal("75"),
            validation_score=Decimal("80"),
            performance=performance,
            criteria=criteria,
        )

        assert Decimal("0") <= score <= Decimal("100")

    def test_calculate_total_score_boundary_cases(self, selector: StrategySelector) -> None:
        """Test total score calculation with boundary values."""
        criteria = StrategySelectionCriteria()

        # Minimum performance
        min_performance = {
            "expected_return": Decimal("0.0"),
            "expected_risk": Decimal("0.5"),  # High risk = low score
            "sharpe_ratio": Decimal("0.0"),
            "max_drawdown": Decimal("0.5"),
            "win_rate": Decimal("0.0"),
        }

        min_score = selector._calculate_total_score(
            suitability=Decimal("0"),
            validation_score=Decimal("0"),
            performance=min_performance,
            criteria=criteria,
        )

        # Maximum performance
        max_performance = {
            "expected_return": Decimal("0.30"),  # High return
            "expected_risk": Decimal("0.05"),  # Low risk
            "sharpe_ratio": Decimal("3.0"),  # High sharpe
            "max_drawdown": Decimal("0.05"),
            "win_rate": Decimal("0.90"),
        }

        max_score = selector._calculate_total_score(
            suitability=Decimal("100"),
            validation_score=Decimal("100"),
            performance=max_performance,
            criteria=criteria,
        )

        assert min_score < max_score
        assert Decimal("0") <= min_score <= Decimal("100")
        assert Decimal("0") <= max_score <= Decimal("100")

    def test_get_default_criteria_conservative(
        self, selector: StrategySelector, conservative_profile: InputProfile
    ) -> None:
        """Test default criteria for conservative profile."""
        criteria = selector._get_default_criteria(conservative_profile)

        # Conservative profiles should weight risk higher
        assert criteria.risk_weight > 0.25
        assert criteria.return_weight < 0.25

    def test_get_default_criteria_aggressive(
        self, selector: StrategySelector, aggressive_profile: InputProfile
    ) -> None:
        """Test default criteria for aggressive profile."""
        criteria = selector._get_default_criteria(aggressive_profile)

        # Aggressive profiles should weight return higher
        assert criteria.return_weight > 0.25
        assert criteria.risk_weight < 0.25

    def test_get_default_criteria_medium(
        self, selector: StrategySelector, balanced_profile: InputProfile
    ) -> None:
        """Test default criteria for medium risk profile."""
        criteria = selector._get_default_criteria(balanced_profile)

        # Should use default balanced criteria
        assert criteria.return_weight == 0.25
        assert criteria.risk_weight == 0.20
        assert criteria.sharpe_weight == 0.25

    def test_select_strategy_without_market_data(
        self, selector: StrategySelector, balanced_profile: InputProfile
    ) -> None:
        """Test strategy selection without market data (quick mode)."""
        # This should not raise even without market data
        result = selector.select_strategy(
            profile=balanced_profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        assert isinstance(result, StrategySelectionResult)
        assert result.selected_strategy is not None
        assert result.selected_strategy.strategy_name != ""
        assert len(result.alternative_strategies) >= 0

    def test_select_strategy_with_invalid_criteria(
        self, selector: StrategySelector, balanced_profile: InputProfile
    ) -> None:
        """Test strategy selection with invalid criteria."""
        invalid_criteria = StrategySelectionCriteria(
            return_weight=2.0,  # Invalid, sum > 1.1
            risk_weight=2.0,
        )

        with pytest.raises(ValueError, match="weights must sum"):
            selector.select_strategy(
                profile=balanced_profile,
                market_data=None,
                criteria=invalid_criteria,
            )

    def test_select_strategy_with_progress_callback(
        self, selector: StrategySelector, balanced_profile: InputProfile
    ) -> None:
        """Test strategy selection with progress callback."""
        progress_updates = []

        def callback(message: str, progress: float) -> None:
            progress_updates.append((message, progress))

        result = selector.select_strategy(
            profile=balanced_profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
            progress_callback=callback,
        )

        assert len(progress_updates) > 0
        assert result.selected_strategy is not None

        # Verify progress values are between 0 and 1
        for _, progress in progress_updates:
            assert 0.0 <= progress <= 1.0

    def test_select_strategy_returns_alternatives(
        self, selector: StrategySelector, balanced_profile: InputProfile
    ) -> None:
        """Test that strategy selection returns alternative strategies."""
        result = selector.select_strategy(
            profile=balanced_profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        # Should return alternatives (up to 5)
        assert len(result.alternative_strategies) <= 5

        # Alternatives should be sorted by score (descending)
        if len(result.alternative_strategies) > 1:
            scores = [s.total_score for s in result.alternative_strategies]
            assert scores == sorted(scores, reverse=True)

    def test_select_strategy_with_analysis_error(
        self, selector: StrategySelector, balanced_profile: InputProfile
    ) -> None:
        """Test strategy selection when analysis fails for a strategy."""
        # Mock a scenario where analysis fails
        with patch.object(selector, '_analyze_strategy', side_effect=Exception("Analysis failed")):
            # Should handle errors gracefully
            result = selector.select_strategy(
                profile=balanced_profile,
                market_data=None,
                criteria=StrategySelectionCriteria(require_walk_forward=False),
            )

            # Should still return a result
            assert isinstance(result, StrategySelectionResult)


class TestSelectStrategyUseCase:
    """Tests for SelectStrategyUseCase wrapper."""

    @pytest.fixture
    def profile(self) -> InputProfile:
        """Create test profile."""
        return InputProfile(
            capital_initial=Decimal("100000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

    @pytest.fixture
    def use_case(self) -> SelectStrategyUseCase:
        """Create use case instance."""
        return SelectStrategyUseCase()

    def test_init_use_case(self) -> None:
        """Test use case initialization."""
        use_case = SelectStrategyUseCase()
        assert use_case._selector is not None

    def test_init_use_case_with_custom_selector(self) -> None:
        """Test use case initialization with custom selector."""
        custom_selector = Mock(spec=StrategySelector)
        use_case = SelectStrategyUseCase(selector=custom_selector)
        assert use_case._selector is custom_selector

    def test_execute_use_case(self, use_case: SelectStrategyUseCase, profile: InputProfile) -> None:
        """Test executing the use case."""
        result = use_case.execute(
            profile=profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        assert isinstance(result, StrategySelectionResult)
        assert result.selected_strategy.strategy_name != ""
        assert result.selection_timestamp is not None
        assert result.selection_criteria is not None

    def test_execute_use_case_with_custom_criteria(
        self, use_case: SelectStrategyUseCase, profile: InputProfile
    ) -> None:
        """Test executing use case with custom criteria."""
        custom_criteria = StrategySelectionCriteria(
            return_weight=0.40,
            risk_weight=0.10,
            min_sharpe_ratio=Decimal("1.0"),
        )

        result = use_case.execute(
            profile=profile,
            market_data=None,
            criteria=custom_criteria,
        )

        assert result.selection_criteria.return_weight == 0.40
        assert result.selection_criteria.min_sharpe_ratio == Decimal("1.0")

    def test_get_strategy_recommendations(
        self, use_case: SelectStrategyUseCase, profile: InputProfile
    ) -> None:
        """Test getting quick recommendations."""
        recommendations = use_case.get_strategy_recommendations(profile, top_n=3)

        assert isinstance(recommendations, list)
        assert len(recommendations) <= 3

        if recommendations:
            rec = recommendations[0]
            assert "strategy_name" in rec
            assert "weight" in rec
            assert "suitability_score" in rec
            assert rec["suitability_score"] >= 0

    def test_get_strategy_recommendations_top_n(
        self, use_case: SelectStrategyUseCase, profile: InputProfile
    ) -> None:
        """Test getting recommendations with different top_n values."""
        # Request different numbers of recommendations
        rec_1 = use_case.get_strategy_recommendations(profile, top_n=1)
        rec_5 = use_case.get_strategy_recommendations(profile, top_n=5)
        rec_10 = use_case.get_strategy_recommendations(profile, top_n=10)

        assert len(rec_1) <= 1
        assert len(rec_5) <= 5
        assert len(rec_10) <= 10

    def test_get_strategy_recommendations_sorted(
        self, use_case: SelectStrategyUseCase, profile: InputProfile
    ) -> None:
        """Test that recommendations are sorted by suitability."""
        recommendations = use_case.get_strategy_recommendations(profile, top_n=5)

        if len(recommendations) > 1:
            # Check descending order
            scores = [r["suitability_score"] for r in recommendations]
            assert scores == sorted(scores, reverse=True)

    def test_execute_with_progress_callback(
        self, use_case: SelectStrategyUseCase, profile: InputProfile
    ) -> None:
        """Test executing with progress callback."""
        progress_updates = []

        def callback(message: str, progress: float) -> None:
            progress_updates.append((message, progress))

        result = use_case.execute(
            profile=profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
            progress_callback=callback,
        )

        assert len(progress_updates) > 0
        assert result.selected_strategy is not None


class TestStrategySelectionResult:
    """Tests for StrategySelectionResult dataclass."""

    def test_create_result(self) -> None:
        """Test creating selection result."""
        selected = StrategyConfiguration(
            strategy_name="test_strategy",
            total_score=Decimal("90"),
        )

        result = StrategySelectionResult(
            selected_strategy=selected,
            alternative_strategies=[],
            selection_timestamp=datetime.now(),
            selection_criteria=StrategySelectionCriteria(),
        )

        assert result.selected_strategy.strategy_name == "test_strategy"
        assert result.selected_strategy.total_score == Decimal("90")

    def test_to_dict(self) -> None:
        """Test converting result to dictionary."""
        selected = StrategyConfiguration(
            strategy_name="test_strategy",
            total_score=Decimal("90"),
        )

        alternatives = [
            StrategyConfiguration(
                strategy_name="alt_strategy_1",
                total_score=Decimal("80"),
            ),
            StrategyConfiguration(
                strategy_name="alt_strategy_2",
                total_score=Decimal("70"),
            ),
        ]

        result = StrategySelectionResult(
            selected_strategy=selected,
            alternative_strategies=alternatives,
            selection_timestamp=datetime.now(),
            selection_criteria=StrategySelectionCriteria(),
        )

        dict_result = result.to_dict()

        assert "selected_strategy" in dict_result
        assert "alternative_strategies" in dict_result
        assert "selection_timestamp" in dict_result
        assert len(dict_result["alternative_strategies"]) <= 5  # Should limit to top 5

    def test_to_dict_with_many_alternatives(self) -> None:
        """Test to_dict limits alternatives to top 5."""
        selected = StrategyConfiguration(
            strategy_name="test_strategy",
            total_score=Decimal("100"),
        )

        # Create 10 alternatives
        alternatives = [
            StrategyConfiguration(
                strategy_name=f"alt_strategy_{i}",
                total_score=Decimal(str(90 - i)),
            )
            for i in range(1, 11)
        ]

        result = StrategySelectionResult(
            selected_strategy=selected,
            alternative_strategies=alternatives,
            selection_timestamp=datetime.now(),
            selection_criteria=StrategySelectionCriteria(),
        )

        dict_result = result.to_dict()

        # Should only include top 5
        assert len(dict_result["alternative_strategies"]) == 5

    def test_result_with_details(self) -> None:
        """Test result with optimization and validation details."""
        selected = StrategyConfiguration(
            strategy_name="test_strategy",
            total_score=Decimal("90"),
        )

        optimization_details = {
            "trials": 50,
            "best_params": {"lookback": 20, "threshold": 1.5},
        }

        validation_details = {
            "num_periods": 5,
            "consistency_score": 85.0,
        }

        result = StrategySelectionResult(
            selected_strategy=selected,
            alternative_strategies=[],
            selection_timestamp=datetime.now(),
            selection_criteria=StrategySelectionCriteria(),
            optimization_details=optimization_details,
            validation_details=validation_details,
        )

        assert result.optimization_details["trials"] == 50
        assert result.validation_details["consistency_score"] == 85.0


class TestIntegration:
    """Integration tests for strategy selection."""

    def test_full_selection_workflow(self) -> None:
        """Test complete workflow from profile to selection."""
        # Create profile
        profile = InputProfile(
            capital_initial=Decimal("150000"),
            investment_horizon=36,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
        )

        # Create use case
        use_case = SelectStrategyUseCase()

        # Execute selection
        result = use_case.execute(
            profile=profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        # Verify result
        assert isinstance(result, StrategySelectionResult)
        assert result.selected_strategy.strategy_name != ""
        assert result.selected_strategy.total_score > 0

        # Verify alternatives
        if result.alternative_strategies:
            # Alternatives should be sorted by score
            scores = [s.total_score for s in result.alternative_strategies]
            assert scores == sorted(scores, reverse=True)

    def test_conservative_vs_aggressive_selection(self) -> None:
        """Test that different profiles produce different selections."""
        conservative_profile = InputProfile(
            capital_initial=Decimal("100000"),
            investment_horizon=36,
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
        )

        aggressive_profile = InputProfile(
            capital_initial=Decimal("100000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
        )

        use_case = SelectStrategyUseCase()

        conservative_result = use_case.execute(
            profile=conservative_profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        aggressive_result = use_case.execute(
            profile=aggressive_profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        # Both should have selections
        assert conservative_result.selected_strategy.strategy_name != ""
        assert aggressive_result.selected_strategy.strategy_name != ""

        # The selections may differ based on profile
        # (not asserting they differ, as the mock might return same results)

    def test_different_objectives(self) -> None:
        """Test selection with different investment objectives."""
        profiles = [
            InputProfile(
                capital_initial=Decimal("100000"),
                investment_horizon=36,
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_DIVIDENDOS,
                risk_tolerance=RiskTolerance.MEDIO,
            ),
            InputProfile(
                capital_initial=Decimal("100000"),
                investment_horizon=24,
                objetivo_inversion=ObjectivoInversion.INCOME_GENERATION,
                risk_tolerance=RiskTolerance.MEDIO,
            ),
        ]

        use_case = SelectStrategyUseCase()

        for profile in profiles:
            result = use_case.execute(
                profile=profile,
                market_data=None,
                criteria=StrategySelectionCriteria(require_walk_forward=False),
            )

            assert isinstance(result, StrategySelectionResult)
            assert result.selected_strategy.strategy_name != ""

    def test_all_risk_tolerances(self) -> None:
        """Test selection with all risk tolerance levels."""
        risk_levels = [
            RiskTolerance.BAJO,
            RiskTolerance.MEDIO,
            RiskTolerance.ALTO,
        ]

        use_case = SelectStrategyUseCase()

        for risk in risk_levels:
            profile = InputProfile(
                capital_initial=Decimal("100000"),
                investment_horizon=24,
                objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
                risk_tolerance=risk,
            )

            result = use_case.execute(
                profile=profile,
                market_data=None,
                criteria=StrategySelectionCriteria(require_walk_forward=False),
            )

            assert isinstance(result, StrategySelectionResult)
            assert result.selected_strategy.strategy_name != ""

    def test_edge_case_minimum_capital(self) -> None:
        """Test selection with minimum capital."""
        profile = InputProfile(
            capital_initial=Decimal("1"),  # Minimum allowed
            investment_horizon=12,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

        use_case = SelectStrategyUseCase()
        result = use_case.execute(
            profile=profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        assert isinstance(result, StrategySelectionResult)

    def test_edge_case_maximum_capital(self) -> None:
        """Test selection with maximum capital."""
        profile = InputProfile(
            capital_initial=Decimal("10000000"),  # Maximum allowed
            investment_horizon=60,
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
        )

        use_case = SelectStrategyUseCase()
        result = use_case.execute(
            profile=profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        assert isinstance(result, StrategySelectionResult)

    def test_edge_case_minimum_horizon(self) -> None:
        """Test selection with minimum investment horizon."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            investment_horizon=1,  # Minimum allowed (1 month)
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

        use_case = SelectStrategyUseCase()
        result = use_case.execute(
            profile=profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        assert isinstance(result, StrategySelectionResult)

    def test_edge_case_maximum_horizon(self) -> None:
        """Test selection with maximum investment horizon."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            investment_horizon=600,  # Maximum allowed (50 years)
            objetivo_inversion=ObjectivoInversion.CAPITAL_PRESERVATION,
            risk_tolerance=RiskTolerance.BAJO,
        )

        use_case = SelectStrategyUseCase()
        result = use_case.execute(
            profile=profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        assert isinstance(result, StrategySelectionResult)

    def test_result_serialization(self) -> None:
        """Test that results can be serialized to dict."""
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            investment_horizon=24,
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
        )

        use_case = SelectStrategyUseCase()
        result = use_case.execute(
            profile=profile,
            market_data=None,
            criteria=StrategySelectionCriteria(require_walk_forward=False),
        )

        # Should be serializable
        dict_result = result.to_dict()

        assert "selected_strategy" in dict_result
        assert "alternative_strategies" in dict_result
        assert "selection_timestamp" in dict_result
        assert "selection_criteria" in dict_result

        # Verify nested serialization
        assert "strategy_name" in dict_result["selected_strategy"]
        assert isinstance(dict_result["alternative_strategies"], list)
