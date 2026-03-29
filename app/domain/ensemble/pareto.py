from __future__ import annotations

"""
Pareto Front Optimization for Multi-Objective Strategy Selection.

This module implements NSGA-II (Non-dominated Sorting Genetic Algorithm II)
for finding optimal strategy weight allocations across multiple objectives.
"""

import logging
import random
from decimal import Decimal

import numpy as np

from app.domain.ensemble.models import ObjectiveConfig, OptimizationObjective, ParetoSolution

logger = logging.getLogger(__name__)


class ParetoFrontOptimizer:
    """NSGA-II based Pareto front optimizer for multi-objective optimization.

    This class implements the NSGA-II algorithm to find the Pareto-optimal
    set of strategy weight allocations for given objectives (e.g., maximizing
    return while minimizing risk).

    Example:
        >>> optimizer = ParetoFrontOptimizer(
        ...     strategies=['momentum', 'mean_reversion', 'trend_following'],
        ...     objectives=['maximize_return', 'minimize_risk']
        ... )
        >>> pareto_front = optimizer.optimize(
        ...     returns_data= getattr(config.trading, 'max_risk_per_trade', 0.02), ...], ...},
        ...     population_size=50,
        ...     generations=100
        ... )
    """

    def __init__(
        self,
        strategies: list[str],
        objective_config: ObjectiveConfig,
        population_size: int = 50,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.9,
    ):
        """Initialize the Pareto front optimizer.

        Args:
            strategies: List of strategy names
            objective_config: Configuration for objectives and weights
            population_size: Size of population for genetic algorithm
            mutation_rate: Mutation probability (0-1)
            crossover_rate: Crossover probability (0-1)

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            if not strategies:
                raise ValueError("Strategies list cannot be empty")

            if len(strategies) < 2:
                raise ValueError("At least 2 strategies required for ensemble")

            if population_size < 10:
                raise ValueError("Population size must be at least 10")

            if not (0 <= mutation_rate <= 1):
                raise ValueError("Mutation rate must be between 0 and 1")

            if not (0 <= crossover_rate <= 1):
                raise ValueError("Crossover rate must be between 0 and 1")

            self.strategies = strategies
            self.objective_config = objective_config
            self.population_size = population_size
            self.mutation_rate = mutation_rate
            self.crossover_rate = crossover_rate
            self.random = random.Random()

        except (TypeError, AttributeError) as e:
            logger.error("ParetoFrontOptimizer initialization failed", exc_info=True)
            raise ValueError(f"Invalid parameters: {e}") from e

    def optimize(
        self,
        returns_data: dict[str, np.ndarray],
        risk_data: dict[str, np.ndarray] | None = None,
        generations: int = 100,
        seed: int | None = None,
    ) -> list[ParetoSolution]:
        """Run NSGA-II optimization to find Pareto front.

        Args:
            returns_data: Historical returns for each strategy
            risk_data: Optional risk metrics for each strategy
            generations: Number of generations to evolve
            seed: Random seed for reproducibility

        Returns:
            List of Pareto-optimal solutions (non-dominated front)

        Raises:
            ValueError: If data is invalid or missing
        """
        try:
            # Validate input data
            self._validate_optimization_data(returns_data, risk_data)

            if seed is not None:
                random.seed(seed)
                np.random.seed(seed)

            # Initialize population
            initial_population: list[dict[str, float]] = self._initialize_population()

            # Evaluate initial population
            population: list[ParetoSolution] = self._evaluate_population(
                initial_population, returns_data, risk_data
            )

            # Filter out invalid solutions
            population = [s for s in population if s.objective_values]

            if not population:
                return []

            # Evolution loop
            for generation in range(generations):
                try:
                    # Non-dominated sort
                    fronts = self._non_dominated_sort(population)

                    if not fronts:
                        break

                    # Calculate crowding distance
                    self._calculate_crowding_distance(fronts)

                    # Create offspring
                    offspring = self._create_offspring(population)

                    # Evaluate offspring
                    offspring = self._evaluate_population(offspring, returns_data, risk_data)

                    # Filter out invalid offspring
                    offspring = [s for s in offspring if s.objective_values]

                    # Combine and select new population
                    combined = population + offspring

                    if combined:
                        population = self._select_new_population(combined)
                    else:
                        break

                except Exception as e:
                    logger.error(f"Error in generation {generation}", exc_info=True)
                    raise RuntimeError(f"Error in generation {generation}: {e}") from e

            # Final sort and return Pareto front
            fronts = self._non_dominated_sort(population)

            return fronts[0] if fronts else []

        except Exception as e:
            logger.error("Optimization failed", exc_info=True)
            raise RuntimeError(f"Optimization failed: {e}") from e

    def _validate_optimization_data(
        self,
        returns_data: dict[str, np.ndarray],
        risk_data: dict[str, np.ndarray] | None,
    ) -> None:
        """Validate optimization input data.

        Args:
            returns_data: Returns data to validate
            risk_data: Risk data to validate

        Raises:
            ValueError: If data is invalid
        """
        if not returns_data:
            raise ValueError("Returns data cannot be empty")

        # Check all strategies have data
        for strategy in self.strategies:
            if strategy not in returns_data:
                raise ValueError(f"Missing returns data for strategy: {strategy}")

            if not isinstance(returns_data[strategy], np.ndarray):
                raise ValueError(f"Returns data for {strategy} must be numpy array")

            if len(returns_data[strategy]) < 2:
                raise ValueError(f"Insufficient data points for {strategy}")

        # Validate risk data if provided
        if risk_data:
            for strategy in self.strategies:
                if strategy in risk_data and not isinstance(risk_data[strategy], np.ndarray):
                    raise ValueError(f"Risk data for {strategy} must be numpy array")

    def _initialize_population(self) -> list[dict[str, float]]:
        """Initialize random population with valid weight allocations.

        Returns:
            List of weight allocations summing to 1.0
        """
        population = []

        for _ in range(self.population_size):
            # Generate random weights using Dirichlet distribution
            weights = np.random.dirichlet(np.ones(len(self.strategies)), size=1)[0]
            allocation = {strategy: float(w) for strategy, w in zip(self.strategies, weights)}
            population.append(allocation)

        return population

    def _evaluate_population(
        self,
        population: list[dict[str, float]] | list[ParetoSolution],
        returns_data: dict[str, np.ndarray],
        risk_data: dict[str, np.ndarray] | None = None,
    ) -> list[ParetoSolution]:
        """Evaluate objective functions for population.

        Args:
            population: Population of weight allocations or unevaluated ParetoSolutions
            returns_data: Historical returns data
            risk_data: Optional risk data

        Returns:
            List of evaluated solutions with objective values
        """
        evaluated: list[ParetoSolution] = []

        for individual in population:
            try:
                # Normalize to a dict[str, float] allocation
                if isinstance(individual, ParetoSolution):
                    allocation: dict[str, float] = {
                        k: float(v) for k, v in individual.strategy_weights.items()
                    }
                else:
                    allocation = individual

                # Calculate objective values
                objective_values = self._calculate_objectives(allocation, returns_data, risk_data)

                # Calculate additional metrics
                metrics = self._calculate_metrics(allocation, returns_data, risk_data)

                # Convert weights to Decimal for ParetoSolution
                strategy_weights = {k: Decimal(str(v)) for k, v in allocation.items()}

                solution = ParetoSolution(
                    strategy_weights=strategy_weights,
                    objective_values=objective_values,
                    metrics=metrics,
                )

                evaluated.append(solution)

            except Exception:
                logger.warning("Skipping invalid solution in Pareto evaluation", exc_info=True)
                continue

        return evaluated

    def _calculate_objectives(
        self,
        allocation: dict[str, float],
        returns_data: dict[str, np.ndarray],
        risk_data: dict[str, np.ndarray] | None = None,
    ) -> dict[str, float]:
        """Calculate objective function values for an allocation.

        Args:
            allocation: Strategy weight allocation
            returns_data: Historical returns data
            risk_data: Optional risk data

        Returns:
            Dictionary of objective values
        """
        objectives = {}

        for obj in self.objective_config.objectives:
            try:
                if obj == OptimizationObjective.MAXIMIZE_RETURN:
                    objectives["return"] = self._calculate_portfolio_return(
                        allocation, returns_data
                    )

                elif obj == OptimizationObjective.MINIMIZE_RISK:
                    objectives["risk"] = self._calculate_portfolio_risk(allocation, returns_data)

                elif obj == OptimizationObjective.MAXIMIZE_SHARPE:
                    ret = self._calculate_portfolio_return(allocation, returns_data)
                    risk = self._calculate_portfolio_risk(allocation, returns_data)
                    objectives["sharpe"] = ret / risk if risk > 0 else 0.0

                elif obj == OptimizationObjective.MAXIMIZE_SORTINO:
                    ret = self._calculate_portfolio_return(allocation, returns_data)
                    downside_risk = self._calculate_downside_risk(allocation, returns_data)
                    objectives["sortino"] = ret / downside_risk if downside_risk > 0 else 0.0

                elif obj == OptimizationObjective.MINIMIZE_DRAWDOWN:
                    objectives["drawdown"] = self._calculate_max_drawdown(allocation, returns_data)

                elif obj == OptimizationObjective.MAXIMIZE_DIVERSIFICATION:
                    objectives["diversification"] = self._calculate_diversification_ratio(
                        allocation, returns_data
                    )

            except Exception:
                logger.warning(f"Objective calculation failed for {obj.value}", exc_info=True)
                objectives[obj.value] = 0.0

        return objectives

    def _calculate_portfolio_return(
        self,
        allocation: dict[str, float],
        returns_data: dict[str, np.ndarray],
    ) -> float:
        """Calculate weighted portfolio return.

        Args:
            allocation: Strategy weights
            returns_data: Returns data

        Returns:
            Portfolio return (annualized)
        """
        try:
            # Calculate weighted returns for each time point
            weighted_returns = np.zeros(len(next(iter(returns_data.values()))))

            for strategy, weight in allocation.items():
                strategy_returns = returns_data[strategy]
                weighted_returns += weight * strategy_returns

            # Annualize return (assuming daily data)
            mean_return = np.mean(weighted_returns)
            annualized_return = mean_return * 252  # Trading days per year

            return float(annualized_return)

        except Exception:
            logger.error("Portfolio return calculation failed", exc_info=True)
            return 0.0

    def _calculate_portfolio_risk(
        self,
        allocation: dict[str, float],
        returns_data: dict[str, np.ndarray],
    ) -> float:
        """Calculate portfolio volatility (standard deviation).

        Args:
            allocation: Strategy weights
            returns_data: Returns data

        Returns:
            Portfolio volatility (annualized)
        """
        try:
            # Calculate weighted returns
            weighted_returns = np.zeros(len(next(iter(returns_data.values()))))

            for strategy, weight in allocation.items():
                strategy_returns = returns_data[strategy]
                weighted_returns += weight * strategy_returns

            # Calculate standard deviation and annualize
            volatility = np.std(weighted_returns) * np.sqrt(252)

            return float(volatility)

        except Exception:
            logger.error("Portfolio risk calculation failed", exc_info=True)
            return 0.0

    def _calculate_downside_risk(
        self,
        allocation: dict[str, float],
        returns_data: dict[str, np.ndarray],
    ) -> float:
        """Calculate downside deviation (Sortino ratio denominator).

        Args:
            allocation: Strategy weights
            returns_data: Returns data

        Returns:
            Downside risk (annualized)
        """
        try:
            # Calculate weighted returns
            weighted_returns = np.zeros(len(next(iter(returns_data.values()))))

            for strategy, weight in allocation.items():
                strategy_returns = returns_data[strategy]
                weighted_returns += weight * strategy_returns

            # Calculate downside deviation (only negative returns)
            negative_returns = weighted_returns[weighted_returns < 0]
            if len(negative_returns) == 0:
                return 0.0

            downside_deviation = np.std(negative_returns) * np.sqrt(252)

            return float(downside_deviation)

        except Exception:
            logger.error("Downside risk calculation failed", exc_info=True)
            return 0.0

    def _calculate_max_drawdown(
        self,
        allocation: dict[str, float],
        returns_data: dict[str, np.ndarray],
    ) -> float:
        """Calculate maximum drawdown.

        Args:
            allocation: Strategy weights
            returns_data: Returns data

        Returns:
            Maximum drawdown (positive value)
        """
        try:
            # Calculate weighted returns
            weighted_returns = np.zeros(len(next(iter(returns_data.values()))))

            for strategy, weight in allocation.items():
                strategy_returns = returns_data[strategy]
                weighted_returns += weight * strategy_returns

            # Calculate cumulative returns
            cumulative = np.cumprod(1 + weighted_returns)

            # Calculate running maximum
            running_max = np.maximum.accumulate(cumulative)

            # Calculate drawdown
            drawdown = (cumulative - running_max) / running_max

            return float(abs(np.min(drawdown)))

        except Exception:
            logger.error("Max drawdown calculation failed", exc_info=True)
            return 0.0

    def _calculate_diversification_ratio(
        self,
        allocation: dict[str, float],
        returns_data: dict[str, np.ndarray],
    ) -> float:
        """Calculate diversification ratio.

        The diversification ratio is the weighted average volatility divided
        by portfolio volatility. Values > 1 indicate diversification benefits.

        Args:
            allocation: Strategy weights
            returns_data: Returns data

        Returns:
            Diversification ratio
        """
        try:
            # Calculate individual volatilities
            volatilities = []
            for strategy in self.strategies:
                returns = returns_data[strategy]
                vol = np.std(returns) * np.sqrt(252)
                volatilities.append(vol)

            # Weighted average volatility
            weighted_avg_vol = sum(w * v for w, v in zip(allocation.values(), volatilities))

            # Portfolio volatility
            portfolio_vol = self._calculate_portfolio_risk(allocation, returns_data)

            if portfolio_vol == 0:
                return 1.0

            return weighted_avg_vol / portfolio_vol

        except Exception:
            logger.error("Diversification ratio calculation failed", exc_info=True)
            return 1.0

    def _calculate_metrics(
        self,
        allocation: dict[str, float],
        returns_data: dict[str, np.ndarray],
        risk_data: dict[str, np.ndarray] | None = None,
    ) -> dict[str, float]:
        """Calculate additional performance metrics.

        Args:
            allocation: Strategy weights
            returns_data: Returns data
            risk_data: Optional risk data

        Returns:
            Dictionary of metrics
        """
        metrics = {}

        try:
            # Calculate portfolio returns series
            weighted_returns = np.zeros(len(next(iter(returns_data.values()))))

            for strategy, weight in allocation.items():
                strategy_returns = returns_data[strategy]
                weighted_returns += weight * strategy_returns

            # Skewness and kurtosis
            metrics["skewness"] = float(self._calculate_skewness(weighted_returns))
            metrics["kurtosis"] = float(self._calculate_kurtosis(weighted_returns))

            # Value at Risk (95%)
            metrics["var_95"] = float(np.percentile(weighted_returns, 5))

            # Expected Shortfall (95%)
            var_95 = np.percentile(weighted_returns, 5)
            metrics["expected_shortfall"] = float(
                np.mean(weighted_returns[weighted_returns <= var_95])
            )

        except Exception:
            logger.error("Metrics calculation failed", exc_info=True)

        return metrics

    def _calculate_skewness(self, returns: np.ndarray) -> float:
        """Calculate skewness of returns."""
        try:
            from scipy.stats import skew

            return float(skew(returns))
        except Exception:
            logger.error("Skewness calculation failed", exc_info=True)
            return 0.0

    def _calculate_kurtosis(self, returns: np.ndarray) -> float:
        """Calculate kurtosis of returns."""
        try:
            from scipy.stats import kurtosis

            return float(kurtosis(returns, fisher=False))
        except Exception:
            logger.error("Kurtosis calculation failed", exc_info=True)
            return 0.0

    def _non_dominated_sort(self, population: list[ParetoSolution]) -> list[list[ParetoSolution]]:
        """Perform non-dominated sorting (NSGA-II).

        Args:
            population: Population to sort

        Returns:
            List of fronts (each front is a list of solutions)
        """
        fronts: list[list[ParetoSolution]] = []
        current_front: list[ParetoSolution] = []

        # Calculate domination counts and dominated sets using indices
        domination_counts: dict[int, int] = {}
        dominated_sets: dict[int, set[int]] = {i: set() for i in range(len(population))}

        for i, solution_i in enumerate(population):
            domination_count = 0

            for j, solution_j in enumerate(population):
                if i == j:
                    continue

                if self._dominates(solution_i, solution_j):
                    dominated_sets[i].add(j)
                elif self._dominates(solution_j, solution_i):
                    domination_count += 1

            domination_counts[i] = domination_count

            if domination_count == 0:
                # Create new solution with rank set
                population[i] = solution_i.model_copy(update={"rank": 0})
                current_front.append(population[i])

        fronts.append(current_front)

        # Build subsequent fronts
        i = 0
        while fronts[i]:
            next_front: list[ParetoSolution] = []

            for solution in fronts[i]:
                # Find the index of this solution
                solution_idx = population.index(solution)

                for dominated_idx in dominated_sets[solution_idx]:
                    domination_counts[dominated_idx] -= 1

                    if domination_counts[dominated_idx] == 0:
                        # Create new solution with rank set
                        population[dominated_idx] = population[dominated_idx].model_copy(
                            update={"rank": i + 1}
                        )
                        next_front.append(population[dominated_idx])

            i += 1
            fronts.append(next_front)

        return fronts[:-1]  # Remove empty last front

    def _dominates(self, solution1: ParetoSolution, solution2: ParetoSolution) -> bool:
        """Check if solution1 dominates solution2.

        Solution1 dominates solution2 if:
        - solution1 is better or equal in all objectives
        - solution1 is strictly better in at least one objective

        Args:
            solution1: First solution
            solution2: Second solution

        Returns:
            True if solution1 dominates solution2
        """
        obj1 = solution1.objective_values
        obj2 = solution2.objective_values

        at_least_one_better = False
        tolerance = self.objective_config.tolerance

        for obj in self.objective_config.objectives:
            obj_name = obj.value

            if obj_name not in obj1 or obj_name not in obj2:
                continue

            val1 = obj1[obj_name]
            val2 = obj2[obj_name]

            # Check if value1 is better than value2
            if obj in [
                OptimizationObjective.MAXIMIZE_RETURN,
                OptimizationObjective.MAXIMIZE_SHARPE,
                OptimizationObjective.MAXIMIZE_SORTINO,
                OptimizationObjective.MAXIMIZE_DIVERSIFICATION,
            ]:
                if val1 < val2 - tolerance:
                    return False
                if val1 > val2 + tolerance:
                    at_least_one_better = True

            else:  # Minimization objectives
                if val1 > val2 + tolerance:
                    return False
                if val1 < val2 - tolerance:
                    at_least_one_better = True

        return at_least_one_better

    def _calculate_crowding_distance(self, fronts: list[list[ParetoSolution]]) -> None:
        """Calculate crowding distance for each front.

        Crowding distance measures how close a solution is to its neighbors,
        promoting diversity in the Pareto front.

        Args:
            fronts: List of fronts to calculate crowding distance for
        """
        for front_idx, front in enumerate(fronts):
            if len(front) <= 2:
                # Boundary solutions get infinite distance
                boundary_front: list[ParetoSolution] = []
                for solution in front:
                    boundary_front.append(
                        solution.model_copy(update={"crowding_distance": float("inf")})
                    )
                fronts[front_idx] = boundary_front
                continue

            # Initialize distances
            distances = [0.0] * len(front)

            # Calculate for each objective
            for obj in self.objective_config.objectives:
                obj_name = obj.value

                # Sort front by this objective
                obj_values = [
                    front[idx].objective_values.get(obj_name, 0) for idx in range(len(front))
                ]
                sorted_indices = sorted(range(len(front)), key=obj_values.__getitem__)

                # Boundary solutions get infinite distance
                distances[sorted_indices[0]] = float("inf")
                distances[sorted_indices[-1]] = float("inf")

                # Get objective range
                min_obj = front[sorted_indices[0]].objective_values.get(obj_name, 0)
                max_obj = front[sorted_indices[-1]].objective_values.get(obj_name, 0)
                obj_range = max_obj - min_obj

                if obj_range == 0:
                    continue

                # Calculate crowding distance for interior solutions
                for j in range(1, len(sorted_indices) - 1):
                    idx = sorted_indices[j]
                    if distances[idx] != float("inf"):
                        distance = (
                            front[sorted_indices[j + 1]].objective_values.get(obj_name, 0)
                            - front[sorted_indices[j - 1]].objective_values.get(obj_name, 0)
                        ) / obj_range

                        distances[idx] += distance

            # Create new front with updated distances
            new_front: list[ParetoSolution] = []
            for i, solution in enumerate(front):
                new_front.append(solution.model_copy(update={"crowding_distance": distances[i]}))

            fronts[front_idx] = new_front

    def _create_offspring(self, population: list[ParetoSolution]) -> list[ParetoSolution]:
        """Create offspring through selection, crossover, and mutation.

        Args:
            population: Current population

        Returns:
            List of offspring solutions
        """
        offspring: list[ParetoSolution] = []

        while len(offspring) < self.population_size:
            # Tournament selection
            parent1 = self._tournament_selection(population)
            parent2 = self._tournament_selection(population)

            # Crossover
            if random.random() < self.crossover_rate:
                child1_weights, child2_weights = self._crossover(
                    parent1.strategy_weights, parent2.strategy_weights
                )
            else:
                child1_weights = parent1.strategy_weights
                child2_weights = parent2.strategy_weights

            # Mutation
            if random.random() < self.mutation_rate:
                child1_weights = self._mutate(child1_weights)
            if random.random() < self.mutation_rate:
                child2_weights = self._mutate(child2_weights)

            # Convert to solutions (without evaluation)
            child1 = ParetoSolution(
                strategy_weights=child1_weights,
                objective_values={},
                metrics={},
            )
            child2 = ParetoSolution(
                strategy_weights=child2_weights,
                objective_values={},
                metrics={},
            )

            offspring.extend([child1, child2])

        return offspring[: self.population_size]

    def _tournament_selection(
        self, population: list[ParetoSolution], tournament_size: int = 2
    ) -> ParetoSolution:
        """Binary tournament selection based on rank and crowding distance.

        Args:
            population: Population to select from
            tournament_size: Size of tournament

        Returns:
            Selected solution
        """
        candidates = random.sample(population, min(tournament_size, len(population)))

        # Sort by rank (lower is better) and crowding distance (higher is better)
        candidates.sort(
            key=lambda s: (
                s.rank,
                -s.crowding_distance if s.crowding_distance != float("inf") else 1e9,
            )
        )

        return candidates[0]

    def _crossover(
        self, parent1: dict[str, Decimal], parent2: dict[str, Decimal]
    ) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
        """Simulated binary crossover (SBX) for weight allocation.

        Args:
            parent1: First parent weights
            parent2: Second parent weights

        Returns:
            Tuple of two child weight allocations
        """
        # Convert to float arrays
        p1 = np.array([float(parent1[s]) for s in self.strategies])
        p2 = np.array([float(parent2[s]) for s in self.strategies])

        # Simulated binary crossover
        eta = 20  # Distribution index
        u = random.random()

        beta = (2 * u) ** (1 / (eta + 1)) if u <= 0.5 else (1 / (2 * (1 - u))) ** (1 / (eta + 1))

        c1 = 0.5 * ((1 + beta) * p1 + (1 - beta) * p2)
        c2 = 0.5 * ((1 - beta) * p1 + (1 + beta) * p2)

        # Ensure non-negative
        c1 = np.maximum(c1, 0)
        c2 = np.maximum(c2, 0)

        # Normalize to sum to 1
        c1 = c1 / np.sum(c1)
        c2 = c2 / np.sum(c2)

        # Convert back to dict
        child1 = {s: Decimal(str(w)) for s, w in zip(self.strategies, c1)}
        child2 = {s: Decimal(str(w)) for s, w in zip(self.strategies, c2)}

        return child1, child2

    def _mutate(self, weights: dict[str, Decimal]) -> dict[str, Decimal]:
        """Polynomial mutation for weight allocation.

        Args:
            weights: Weight allocation to mutate

        Returns:
            Mutated weight allocation
        """
        # Convert to float array
        w = np.array([float(weights[s]) for s in self.strategies])

        # Polynomial mutation
        eta = 20  # Distribution index
        for i, weight in enumerate(w):
            if random.random() < 1.0 / len(w):
                u = random.random()

                if u < 0.5:
                    delta = (2 * u) ** (1 / (eta + 1)) - 1
                else:
                    delta = 1 - (2 * (1 - u)) ** (1 / (eta + 1))

                w[i] = weight + delta

        # Ensure non-negative
        w = np.maximum(w, 0)

        # Normalize to sum to 1
        w = w / np.sum(w)

        # Convert back to dict
        return {s: Decimal(str(weight)) for s, weight in zip(self.strategies, w)}

    def _select_new_population(self, combined: list[ParetoSolution]) -> list[ParetoSolution]:
        """Select new population from combined population using NSGA-II selection.

        Args:
            combined: Combined parent and offspring population

        Returns:
            New population of size population_size
        """
        # Non-dominated sort
        fronts = self._non_dominated_sort(combined)

        # Calculate crowding distance
        self._calculate_crowding_distance(fronts)

        # Select from fronts until population is filled
        new_population: list[ParetoSolution] = []

        for front in fronts:
            if len(new_population) + len(front) <= self.population_size:
                new_population.extend(front)
            else:
                # Sort by crowding distance and select remaining
                remaining = self.population_size - len(new_population)
                front_sorted = sorted(
                    front,
                    key=lambda s: (
                        -s.crowding_distance if s.crowding_distance != float("inf") else 1e9
                    ),
                )
                new_population.extend(front_sorted[:remaining])
                break

        return new_population
