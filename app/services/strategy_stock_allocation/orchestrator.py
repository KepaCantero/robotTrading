"""
Main orchestrator for stock allocation across trading strategies.

Coordinates all components of the allocation pipeline:
- Stock filtering
- Statistical calculations
- Strategy scoring
- Capital allocation
- Validation
- Output generation
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, Field

from app.core.centralized_config import StockAllocationSettings
from app.services.momentum_analysis import TechnicalIndicatorCalculator

from .allocators import ERCCapitalAllocator
from .calculators import HalfLifeCalculator, HurstCalculator, StationarityTester
from .classifiers import RegimeClassifier
from .filters import StockFilter
from .output import OutputGenerator
from .scorers import MeanReversionScorer, MomentumScorer, PairsTradingScorer, WCMScoreCalculator
from .validators import AllocationValidator

logger = logging.getLogger(__name__)


# Data models
class StockMetrics(BaseModel):
    """Metrics for a single stock."""

    ticker: str
    strategy: Optional[str] = None
    weight: float = 0.0
    capital: float = 0.0
    sps_score: float = 0.0
    sortino_ratio: Optional[float] = None
    h_long: Optional[float] = None
    h_short: Optional[float] = None
    half_life_tau: Optional[float] = None
    garch_volatility: Optional[float] = None
    decision_log: str = ""


class PairMetrics(BaseModel):
    """Metrics for a trading pair."""

    ticker1: str
    ticker2: str
    cointegration_score: float
    correlation: float
    half_life_tau: Optional[float] = None
    decision_log: str = ""


class AllocationResult(BaseModel):
    """Result of stock allocation."""

    allocations: dict[str, StockMetrics] = Field(default_factory=dict)
    pairs: list[PairMetrics] = Field(default_factory=list)
    residual_capital: float = 0.0
    decision_logs: list[str] = Field(default_factory=list)
    validation_passed: bool = False
    validation_errors: list[str] = Field(default_factory=list)


class StrategyStockAllocator:
    """
    Main orchestrator for stock allocation across trading strategies.

    Coordinates all components through dependency injection following
    the Dependency Inversion Principle (DIP).

    Pipeline:
    1. Filter stocks (validation)
    2. Calculate WCM scores (momentum, mean reversion, pairs)
    3. Assign strategies
    4. Allocate capital (ERC)
    5. Validate
    6. Generate output
    """

    def __init__(
        self,
        config: Optional[StockAllocationSettings] = None,
        tier: Optional[str] = None,
        use_yaml: bool = True,
        # Dependencies (injected)
        stock_filter: Optional[StockFilter] = None,
        hurst_calculator: Optional[HurstCalculator] = None,
        half_life_calculator: Optional[HalfLifeCalculator] = None,
        stationarity_tester: Optional[StationarityTester] = None,
        regime_classifier: Optional[RegimeClassifier] = None,
        momentum_scorer: Optional[MomentumScorer] = None,
        mean_reversion_scorer: Optional[MeanReversionScorer] = None,
        pairs_scorer: Optional[PairsTradingScorer] = None,
        wcm_calculator: Optional[WCMScoreCalculator] = None,
        erc_allocator: Optional[ERCCapitalAllocator] = None,
        validator: Optional[AllocationValidator] = None,
        output_generator: Optional[OutputGenerator] = None,
        technical_indicator_calculator: Optional[Any] = None,
    ) -> None:
        """
        Initialize allocator with dependencies.

        Args:
            config: Stock allocation configuration
            tier: Capital tier for tier-specific overrides
            use_yaml: If True, loads configuration from YAML file when config is None
            stock_filter: Stock filter instance
            hurst_calculator: Hurst calculator instance
            half_life_calculator: Half-life calculator instance
            stationarity_tester: Stationarity tester instance
            regime_classifier: Regime classifier instance
            momentum_scorer: Momentum scorer instance
            mean_reversion_scorer: Mean reversion scorer instance
            pairs_scorer: Pairs trading scorer instance
            wcm_calculator: WCM score calculator instance
            erc_allocator: ERC capital allocator instance
            validator: Allocation validator instance
            output_generator: Output generator instance
            technical_indicator_calculator: Technical indicator calculator instance
        """
        # Load configuration
        if config is None and use_yaml:
            try:
                config = StockAllocationSettings.from_yaml(tier=tier)
                source = f"YAML (tier={tier or 'default'})"
            except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
                logger.warning(f"Failed to load config from YAML: {e}. Using defaults.")
                config = StockAllocationSettings()
                source = "default (Pydantic)"
        elif config is None:
            config = StockAllocationSettings()
            source = "default (Pydantic)"
        else:
            source = "provided"

        self.config = config

        # Initialize technical indicator calculator
        if technical_indicator_calculator is None:
            self.indicator_calculator = TechnicalIndicatorCalculator()
        else:
            self.indicator_calculator = technical_indicator_calculator

        # Initialize dependencies (DIP: inject or create)
        self.stock_filter = stock_filter or StockFilter(config)
        self.hurst_calculator = hurst_calculator or HurstCalculator(config)
        self.half_life_calculator = half_life_calculator or HalfLifeCalculator(config)
        self.stationarity_tester = stationarity_tester or StationarityTester(config)
        self.regime_classifier = regime_classifier or RegimeClassifier(
            config, self.hurst_calculator
        )

        # Scorers
        self.momentum_scorer = momentum_scorer or MomentumScorer(
            config, self.hurst_calculator, self.indicator_calculator
        )
        self.mean_reversion_scorer = mean_reversion_scorer or MeanReversionScorer(
            config, self.hurst_calculator, self.half_life_calculator
        )
        self.pairs_scorer = pairs_scorer or PairsTradingScorer(
            config,
            self.half_life_calculator,
            self.mean_reversion_scorer._calculate_garch_volatility,
        )
        self.wcm_calculator = wcm_calculator or WCMScoreCalculator(
            self.momentum_scorer,
            self.mean_reversion_scorer,
            self.pairs_scorer,
        )

        # Allocator and validator
        self.erc_allocator = erc_allocator or ERCCapitalAllocator(config)
        self.validator = validator or AllocationValidator(config)
        self.output_generator = output_generator or OutputGenerator()

        # Internal state
        self.filtered_stocks: dict[str, pd.DataFrame] = {}
        self.stock_metrics: dict[str, dict[str, Any]] = {}
        self.pair_metrics: list[PairMetrics] = []
        self.decision_logs: list[str] = []

        logger.info(
            f"StrategyStockAllocator initialized with config from {source}: "
            f"LOOKBACK_MAX_DAYS={config.LOOKBACK_MAX_DAYS}, "
            f"MIN_LIQUIDITY_USD=${config.MIN_LIQUIDITY_USD:,.0f}, "
            f"MAX_STRATEGY_EXPOSURE={config.MAX_STRATEGY_EXPOSURE:.0%}"
        )

    def allocate(
        self,
        historical_data: dict[str, pd.DataFrame],
        total_capital: float,
        strategy_allocations: Optional[dict[str, float]] = None,
    ) -> AllocationResult:
        """
        Main allocation method: complete pipeline from data to allocation.

        Args:
            historical_data: Dictionary mapping ticker to DataFrame
            total_capital: Total capital to allocate
            strategy_allocations: Optional strategy-level capital allocations

        Returns:
            AllocationResult with allocations and validation
        """
        logger.info(f"Starting allocation process (total capital: ${total_capital:,.2f})")

        # Step 1: Filter stocks
        self.filtered_stocks = self.stock_filter.filter_stocks(historical_data)

        if len(self.filtered_stocks) == 0:
            logger.error("No stocks passed filtering")
            return AllocationResult(
                validation_passed=False, validation_errors=["No stocks passed filtering"]
            )

        # Step 2: Calculate WCM scores
        all_scores, pair_metrics_list = self.wcm_calculator.calculate_all(
            self.filtered_stocks, self.config
        )

        # Convert pair metrics list to PairMetrics objects
        self.pair_metrics = [PairMetrics(**pm) for pm in pair_metrics_list]

        # Step 3: Resolve conflicts and assign strategies
        strategy_assignments = self._assign_strategies(all_scores)

        # Step 4: Allocate capital using ERC
        final_allocations = self._allocate_capital(
            all_scores, strategy_assignments, total_capital, strategy_allocations
        )

        # Step 5: Validate
        is_valid, errors = self.validator.validate(
            final_allocations, total_capital, strategy_allocations or {}
        )

        # Step 6: Generate output
        self.output_generator.generate(final_allocations, self.pair_metrics)

        # Calculate residual capital
        residual_capital = total_capital - sum(
            alloc.capital for alloc in final_allocations.values()
        )

        result = AllocationResult(
            allocations=final_allocations,
            pairs=self.pair_metrics,
            residual_capital=residual_capital,
            decision_logs=self.decision_logs,
            validation_passed=is_valid,
            validation_errors=errors,
        )

        logger.info(
            f"Allocation complete: {len(final_allocations)} assets allocated, "
            f"${residual_capital:,.2f} residual, validation={'PASSED' if is_valid else 'FAILED'}"
        )

        return result

    def _assign_strategies(self, all_scores: dict[str, dict[str, float]]) -> dict[str, str]:
        """
        Resolve conflicts and assign strategies to tickers.

        Args:
            all_scores: Dictionary mapping ticker to strategy scores

        Returns:
            Dictionary mapping ticker to assigned strategy
        """
        strategy_assignments = {}

        # Prioritize Pairs Trading first
        sorted_pairs = sorted(
            self.pair_metrics,
            key=lambda p: p.cointegration_score if p.cointegration_score is not None else 0.0,
            reverse=True,
        )

        asset_pair_count = defaultdict(int)
        pairs_assigned = 0

        for pair_metrics_obj in sorted_pairs:
            ticker1, ticker2 = pair_metrics_obj.ticker1, pair_metrics_obj.ticker2

            if (
                asset_pair_count[ticker1] < self.config.MAX_ASSETS_PER_PAIR
                and asset_pair_count[ticker2] < self.config.MAX_ASSETS_PER_PAIR
            ):
                strategy_assignments[ticker1] = "pairs_trading"
                strategy_assignments[ticker2] = "pairs_trading"
                asset_pair_count[ticker1] += 1
                asset_pair_count[ticker2] += 1
                pairs_assigned += 1

        if pairs_assigned > 0:
            logger.info(f"✅ Assigned {pairs_assigned} pairs to pairs_trading strategy")

        # Assign remaining assets to Momentum or Mean Reversion
        momentum_tickers = []
        mean_reversion_tickers = []

        for ticker, scores in all_scores.items():
            if ticker in strategy_assignments:
                continue

            momentum_score = scores.get("momentum", 0.0)
            mean_rev_score = scores.get("mean_reversion", 0.0)

            if momentum_score > mean_rev_score or (momentum_score == mean_rev_score == 0.0):
                strategy_assignments[ticker] = "momentum"
                momentum_tickers.append(ticker)
            elif mean_rev_score > 0:
                strategy_assignments[ticker] = "mean_reversion"
                mean_reversion_tickers.append(ticker)
            else:
                strategy_assignments[ticker] = "momentum"
                momentum_tickers.append(ticker)

        # Ensure each strategy has at least 1 ticker
        if len(momentum_tickers) == 0 and len(mean_reversion_tickers) > 1:
            moved_ticker = mean_reversion_tickers.pop(0)
            strategy_assignments[moved_ticker] = "momentum"
            momentum_tickers.append(moved_ticker)
        elif len(mean_reversion_tickers) == 0 and len(momentum_tickers) > 1:
            moved_ticker = momentum_tickers.pop(0)
            strategy_assignments[moved_ticker] = "mean_reversion"
            mean_reversion_tickers.append(moved_ticker)

        # Ensure minimum tickers for capital utilization
        total_assigned = len(strategy_assignments)
        min_target_tickers = 15

        if total_assigned < min_target_tickers:
            unassigned_tickers = [
                ticker for ticker in all_scores.keys() if ticker not in strategy_assignments
            ]

            if len(unassigned_tickers) > 0:
                logger.info(
                    f"⚠️ Only {total_assigned} tickers assigned, "
                    f"assigning ALL {len(unassigned_tickers)} remaining tickers"
                )

                momentum_count = len(momentum_tickers)
                mean_rev_count = len(mean_reversion_tickers)

                for ticker in unassigned_tickers:
                    scores = all_scores.get(ticker, {})
                    momentum_score = scores.get("momentum", 0.0)
                    mean_rev_score = scores.get("mean_reversion", 0.0)

                    if momentum_count < mean_rev_count:
                        strategy_assignments[ticker] = "momentum"
                        momentum_tickers.append(ticker)
                        momentum_count += 1
                    elif mean_rev_count < momentum_count:
                        strategy_assignments[ticker] = "mean_reversion"
                        mean_reversion_tickers.append(ticker)
                        mean_rev_count += 1
                    else:
                        if momentum_score >= mean_rev_score:
                            strategy_assignments[ticker] = "momentum"
                            momentum_tickers.append(ticker)
                            momentum_count += 1
                        else:
                            strategy_assignments[ticker] = "mean_reversion"
                            mean_reversion_tickers.append(ticker)
                            mean_rev_count += 1

        return strategy_assignments

    def _allocate_capital(
        self,
        all_scores: dict[str, dict[str, float]],
        strategy_assignments: dict[str, str],
        total_capital: float,
        strategy_allocations: Optional[dict[str, float]],
    ) -> dict[str, StockMetrics]:
        """
        Allocate capital using ERC within each strategy group.

        Args:
            all_scores: Dictionary mapping ticker to strategy scores
            strategy_assignments: Dictionary mapping ticker to assigned strategy
            total_capital: Total capital to allocate
            strategy_allocations: Strategy-level capital allocations

        Returns:
            Dictionary mapping ticker to StockMetrics
        """
        # Group by strategy
        strategy_groups = defaultdict(list)
        for ticker, strategy in strategy_assignments.items():
            strategy_groups[strategy].append(ticker)

        # Default strategy allocations
        if strategy_allocations is None:
            strategy_allocations = {
                "momentum": total_capital * 0.50,
                "mean_reversion": total_capital * 0.35,
                "pairs_trading": total_capital * 0.15,
            }

        final_allocations: dict[str, StockMetrics] = {}
        allocated_total = 0.0

        # Allocate per strategy
        for strategy, strategy_capital in strategy_allocations.items():
            if strategy not in strategy_groups:
                continue

            strategy_tickers = strategy_groups[strategy]
            if len(strategy_tickers) == 0:
                continue

            # Get price data for covariance matrix
            filtered_stocks_prices = {
                ticker: self.filtered_stocks[ticker]['close'].values
                for ticker in strategy_tickers
                if ticker in self.filtered_stocks
            }

            # Calculate scores for this strategy
            strategy_scores = {ticker: all_scores.get(ticker, {}) for ticker in strategy_tickers}

            # ERC allocation within strategy
            strategy_allocs = self.erc_allocator.allocate(
                strategy_scores,
                strategy_capital,
                filtered_stocks_prices,
                {strategy: strategy_capital},
            )

            # Create StockMetrics objects
            for ticker, capital in strategy_allocs.items():
                sps_score = all_scores.get(ticker, {}).get(strategy, 0.0)

                # Get metrics from scorer results
                momentum_metrics = {}
                mean_rev_metrics = {}

                if strategy == "momentum":
                    momentum_result = self.momentum_scorer.score(
                        ticker, self.filtered_stocks[ticker]
                    )
                    momentum_metrics = {
                        "sortino": momentum_result.get("sortino"),
                        "h_long": momentum_result.get("h_long"),
                    }
                elif strategy == "mean_reversion":
                    mean_rev_result = self.mean_reversion_scorer.score(
                        ticker, self.filtered_stocks[ticker]
                    )
                    mean_rev_metrics = {
                        "half_life": mean_rev_result.get("half_life"),
                        "garch_volatility": mean_rev_result.get("garch_volatility"),
                    }

                decision_log = (
                    f"Assigned to {strategy} (SPS={sps_score:.4f}). "
                    f"H_long={momentum_metrics.get('h_long', 'N/A')}, "
                    f"tau={mean_rev_metrics.get('half_life', 'N/A')}"
                )

                final_allocations[ticker] = StockMetrics(
                    ticker=ticker,
                    strategy=strategy,
                    weight=capital / total_capital if total_capital > 0 else 0.0,
                    capital=capital,
                    sps_score=sps_score,
                    sortino_ratio=momentum_metrics.get("sortino"),
                    h_long=momentum_metrics.get("h_long"),
                    h_short=None,
                    half_life_tau=mean_rev_metrics.get("half_life"),
                    garch_volatility=mean_rev_metrics.get("garch_volatility"),
                    decision_log=decision_log,
                )

                allocated_total += capital

        # Redistribute unused capital
        residual = total_capital - allocated_total
        if residual > 0.01 and len(final_allocations) > 0:
            final_allocations = self._redistribute_capital(
                final_allocations, residual, total_capital
            )

        return final_allocations

    def _redistribute_capital(
        self,
        allocations: dict[str, StockMetrics],
        residual: float,
        total_capital: float,
    ) -> dict[str, StockMetrics]:
        """
        Redistribute unused capital respecting limits.

        Args:
            allocations: Current allocations
            residual: Unused capital to redistribute
            total_capital: Total capital

        Returns:
            Updated allocations
        """
        logger.warning(
            f"⚠️ Redistributing ${residual:,.2f} unused capital to {len(allocations)} allocations"
        )

        max_weight = self.config.MAX_STRATEGY_EXPOSURE
        max_capital_per_ticker = total_capital * max_weight

        # First pass: redistribute proportionally up to limits
        allocated_total = sum(alloc.capital for alloc in allocations.values())

        for ticker in allocations:
            old_capital = allocations[ticker].capital
            if allocated_total > 0.01:
                proportional_capital = old_capital * (allocated_total + residual) / allocated_total
            else:
                proportional_capital = residual / len(allocations)

            capped_capital = min(proportional_capital, max_capital_per_ticker)
            allocations[ticker].capital = capped_capital
            allocations[ticker].weight = (
                capped_capital / total_capital if total_capital > 0 else 0.0
            )

        # Recalculate residual
        allocated_after_cap = sum(alloc.capital for alloc in allocations.values())
        remaining_residual = total_capital - allocated_after_cap

        if remaining_residual > 0.01:
            # Try to distribute to allocations under limit
            available = [
                ticker
                for ticker, alloc in allocations.items()
                if alloc.capital < max_capital_per_ticker and alloc.weight < max_weight
            ]

            if available:
                per_ticker = remaining_residual / len(available)
                for ticker in available:
                    add_amount = min(
                        per_ticker, max_capital_per_ticker - allocations[ticker].capital
                    )
                    allocations[ticker].capital += add_amount
                    allocations[ticker].weight = (
                        allocations[ticker].capital / total_capital if total_capital > 0 else 0.0
                    )

        # Final floating point fix
        allocated_sum = sum(alloc.capital for alloc in allocations.values())
        if abs(allocated_sum - total_capital) > 0.01:
            diff = total_capital - allocated_sum
            if abs(diff) < total_capital * 0.01:
                max_ticker = max(allocations.keys(), key=lambda k: allocations[k].capital)
                allocations[max_ticker].capital += diff
                allocations[max_ticker].weight = (
                    allocations[max_ticker].capital / total_capital if total_capital > 0 else 0.0
                )

        return allocations
