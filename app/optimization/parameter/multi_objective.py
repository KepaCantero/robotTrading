# mypy: ignore-errors
# flake8: noqa: SIM111
"""
Multi-Objective Optimization - FASE 6.1 Extension

Provides multi-objective optimization capabilities:
- Pareto front calculation
- Non-dominated sorting
- Crowding distance for diversity
- Weighted criteria selection
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .base_optimizer import OptimizationConfig, OptimizationResult
from .models import ParameterGrid
from .trial import TrialHistory

logger = logging.getLogger(__name__)


@dataclass
class ParetoSolution:
    """
    A solution on the Pareto front.

    Represents a non-dominated solution in multi-objective optimization.
    """

    params: Dict[str, Any]
    objectives: Tuple[float, ...]
    trial_id: str = ""
    rank: int = 0
    crowding_distance: float = 0.0
    additional_metrics: Dict[str, Any] = field(default_factory=dict)

    def dominates(self, other: "ParetoSolution") -> bool:
        """
        Check if this solution dominates another.

        A solution dominates another if it is better or equal in all objectives
        and strictly better in at least one objective.

        Args:
            other: Other solution to compare

        Returns:
            True if this solution dominates other
        """
        at_least_one_better = False

        for obj_a, obj_b in zip(self.objectives, other.objectives):
            if obj_a < obj_b:  # Assuming all objectives are to be maximized
                return False
            elif obj_a > obj_b:
                at_least_one_better = True

        return at_least_one_better

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "params": self.params,
            "objectives": self.objectives,
            "trial_id": self.trial_id,
            "rank": self.rank,
            "crowding_distance": self.crowding_distance,
            "additional_metrics": self.additional_metrics,
        }


@dataclass
class ParetoFront:
    """
    Pareto front of non-dominated solutions.

    Contains all non-dominated solutions from multi-objective optimization.
    """

    solutions: List[ParetoSolution] = field(default_factory=list)
    objective_names: List[str] = field(default_factory=list)
    n_trials: int = 0
    fronts: List[List[ParetoSolution]] = field(default_factory=list)

    def __post_init__(self):
        """Calculate fronts if not provided."""
        if not self.fronts and self.solutions:
            self.fronts = self._non_dominated_sorting()

    def _non_dominated_sorting(self) -> List[List[ParetoSolution]]:
        """
        Perform non-dominated sorting (NSGA-II style).

        Returns:
            List of fronts, where fronts[0] is the Pareto front
        """
        if not self.solutions:
            return []

        # Initialize
        for solution in self.solutions:
            solution.domination_count = 0
            solution.dominated_solutions = []

        # Calculate domination
        for i, sol_a in enumerate(self.solutions):
            for j, sol_b in enumerate(self.solutions):
                if i != j:
                    if sol_a.dominates(sol_b):
                        sol_a.dominated_solutions.append(sol_b)
                    elif sol_b.dominates(sol_a):
                        sol_a.domination_count += 1

        # Find first front
        fronts = []
        current_front = [sol for sol in self.solutions if sol.domination_count == 0]

        if current_front:
            fronts.append(current_front)

        # Find subsequent fronts
        while current_front:
            next_front = []
            for sol in current_front:
                for dominated in getattr(sol, "dominated_solutions", []):
                    dominated.domination_count -= 1
                    if dominated.domination_count == 0:
                        next_front.append(dominated)

            if next_front:
                fronts.append(next_front)

            current_front = next_front

        return fronts

    def calculate_crowding_distance(self, front: List[ParetoSolution]) -> None:
        """
        Calculate crowding distance for a front.

        Crowding distance measures diversity of solutions.
        Larger distance means more unique solution.

        Args:
            front: List of solutions in a front
        """
        if not front:
            return

        n = len(front)
        n_obj = len(front[0].objectives)

        # Initialize
        for solution in front:
            solution.crowding_distance = 0.0

        # Calculate for each objective
        for obj_idx in range(n_obj):
            # Sort by this objective using default argument to avoid cell-var-from-loop
            sorted_front = sorted(front, key=lambda s, idx=obj_idx: s.objectives[idx])

            # Boundary solutions get infinite distance
            sorted_front[0].crowding_distance = float("inf")
            sorted_front[-1].crowding_distance = float("inf")

            # Calculate for intermediate solutions
            obj_range = sorted_front[-1].objectives[obj_idx] - sorted_front[0].objectives[obj_idx]

            if obj_range > 0:
                for i in range(1, n - 1):
                    if sorted_front[i].crowding_distance != float("inf"):
                        distance = (
                            sorted_front[i + 1].objectives[obj_idx]
                            - sorted_front[i - 1].objectives[obj_idx]
                        ) / obj_range
                        sorted_front[i].crowding_distance += distance

    def get_pareto_front(self) -> List[ParetoSolution]:
        """
        Get the first Pareto front (non-dominated solutions).

        Returns:
            List of non-dominated solutions
        """
        if not self.fronts:
            self.fronts = self._non_dominated_sorting()

        return self.fronts[0] if self.fronts else []

    def get_best_by_objective(self, objective_index: int = 0) -> Optional[ParetoSolution]:
        """
        Get best solution for a specific objective.

        Args:
            objective_index: Index of objective to optimize

        Returns:
            Best solution for this objective
        """
        if not self.solutions:
            return None

        return max(self.solutions, key=lambda s: s.objectives[objective_index])

    def get_best_by_weighted_criteria(
        self,
        weights: Optional[List[float]] = None,
    ) -> Optional[ParetoSolution]:
        """
        Get best solution by weighted sum of objectives.

        Args:
            weights: Weights for each objective (defaults to equal weights)

        Returns:
            Best solution according to weighted criteria
        """
        if not self.solutions:
            return None

        n_obj = len(self.solutions[0].objectives)

        if weights is None:
            weights = [1.0 / n_obj] * n_obj

        if len(weights) != n_obj:
            raise ValueError(f"Expected {n_obj} weights, got {len(weights)}")

        # Normalize weights
        total = sum(weights)
        weights = [w / total for w in weights]

        # Find best
        best_solution = None
        best_score = float("-inf")

        for solution in self.solutions:
            score = sum(w * obj for w, obj in zip(weights, solution.objectives))
            if score > best_score:
                best_score = score
                best_solution = solution

        return best_solution

    def get_knee_point(self) -> Optional[ParetoSolution]:
        """
        Find the knee point on the Pareto front.

        The knee point is the solution with maximum curvature,
        representing a good trade-off between objectives.

        Returns:
            Knee point solution, or None if insufficient solutions
        """
        front = self.get_pareto_front()

        if len(front) < 3:
            return None

        # Simple knee detection: maximum angle
        best_knee = None
        best_angle = float("-inf")

        for i, sol in enumerate(front[1:-1], 1):
            # Calculate angle formed by neighbors
            prev_sol = front[i - 1]
            next_sol = front[i + 1]

            # Use distance from line connecting neighbors
            dist = self._point_line_distance(
                sol.objectives,
                prev_sol.objectives,
                next_sol.objectives,
            )

            if dist > best_angle:
                best_angle = dist
                best_knee = sol

        return best_knee

    def _point_line_distance(
        self,
        point: Tuple[float, ...],
        line_start: Tuple[float, ...],
        line_end: Tuple[float, ...],
    ) -> float:
        """Calculate perpendicular distance from point to line."""
        if len(point) < 2:
            return 0.0

        # For 2D case
        if len(point) == 2:
            x0, y0 = point
            x1, y1 = line_start
            x2, y2 = line_end

            # Line equation: ax + by + c = 0
            a = y1 - y2
            b = x2 - x1
            c = x1 * y2 - x2 * y1

            return abs(a * x0 + b * y0 + c) / ((a**2 + b**2) ** 0.5)

        # For higher dimensions, use simplified approach
        return sum(abs(p - s) for p, s in zip(point, line_start))

    def get_diverse_solutions(
        self,
        n_solutions: int = 10,
        use_crowding: bool = True,
    ) -> List[ParetoSolution]:
        """
        Get diverse set of solutions from Pareto front.

        Args:
            n_solutions: Number of solutions to select
            use_crowding: Use crowding distance for selection

        Returns:
            Diverse set of solutions
        """
        front = self.get_pareto_front()

        if not front:
            return []

        if len(front) <= n_solutions:
            return front

        if use_crowding:
            # Calculate crowding distances
            self.calculate_crowding_distance(front)

            # Select by crowding distance
            sorted_front = sorted(
                front,
                key=lambda s: (
                    -s.crowding_distance if s.crowding_distance != float("inf") else float("-inf")
                ),
            )
            return sorted_front[:n_solutions]
        else:
            # Select evenly distributed
            indices = np.linspace(0, len(front) - 1, n_solutions, dtype=int)
            return [front[i] for i in indices]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "solutions": [s.to_dict() for s in self.solutions],
            "objective_names": self.objective_names,
            "n_trials": self.n_trials,
            "n_fronts": len(self.fronts),
            "pareto_front_size": len(self.get_pareto_front()),
            "best_by_objective": (
                {
                    name: self.get_best_by_objective(i).to_dict()
                    for i, name in enumerate(self.objective_names)
                }
                if self.objective_names
                else {}
            ),
        }


class MultiObjectiveOptimizer:
    """
    Multi-objective optimizer using Pareto dominance.

    Finds Pareto front of non-dominated solutions.
    Useful for balancing competing objectives like return vs risk vs Sharpe.
    """

    def __init__(
        self,
        config: OptimizationConfig,
        objective_names: Optional[List[str]] = None,
    ):
        """
        Initialize multi-objective optimizer.

        Args:
            config: Optimization configuration
            objective_names: Names of objectives (for reporting)
        """
        self.config = config
        self.objective_names = objective_names or ["objective_0", "objective_1"]
        self.history = TrialHistory()

    async def optimize_multi_objective(
        self,
        objectives: List[Callable[[Dict[str, Any]], float]],
        param_grid: ParameterGrid,
    ) -> ParetoFront:
        """
        Run multi-objective optimization.

        Args:
            objectives: List of objective functions to optimize
            param_grid: Parameter search space

        Returns:
            ParetoFront with non-dominated solutions
        """
        from .random_search import RandomSearchOptimizer

        if len(objectives) != len(self.objective_names):
            raise ValueError(
                f"Expected {len(self.objective_names)} objectives, " f"got {len(objectives)}"
            )

        # Use random search to sample parameter combinations
        random_optimizer = RandomSearchOptimizer(self.config)
        random_optimizer.config.max_iterations = self.config.max_iterations

        # Define combined objective for random search
        def combined_objective(params):
            # Just run first objective for sampling
            return objectives[0](params)

        # Sample parameters
        await random_optimizer.optimize(combined_objective, param_grid)

        # Evaluate all objectives for each sampled parameter set
        solutions = []

        for trial in random_optimizer.history.trials:
            if trial.is_success:
                try:
                    # Evaluate all objectives
                    obj_values = []
                    for obj_func in objectives:
                        value = obj_func(trial.params)
                        obj_values.append(value)

                    solution = ParetoSolution(
                        params=trial.params,
                        objectives=tuple(obj_values),
                        trial_id=trial.trial_id,
                    )
                    solutions.append(solution)

                except Exception as e:
                    logger.warning(f"Failed to evaluate objectives: {e}")

        # Create Pareto front
        pareto_front = ParetoFront(
            solutions=solutions,
            objective_names=self.objective_names,
            n_trials=len(random_optimizer.history.trials),
        )

        return pareto_front


def find_non_dominated_solutions(
    solutions: List[Tuple[Dict[str, Any], Tuple[float, ...]]],
) -> List[Tuple[Dict[str, Any], Tuple[float, ...]]]:
    """
    Find non-dominated solutions from a list.

    Args:
        solutions: List of (params, objectives) tuples

    Returns:
        List of non-dominated solutions
    """
    non_dominated = []

    for params, objectives in solutions:
        is_dominated = False

        for other_params, other_objectives in solutions:
            if params == other_params:
                continue

            # Check if other dominates this one
            dominates = True
            at_least_one_better = False

            for obj_a, obj_b in zip(objectives, other_objectives):
                if obj_a < obj_b:  # Assuming maximization
                    dominates = False
                    break
                elif obj_a > obj_b:
                    at_least_one_better = True

            if dominates and at_least_one_better:
                is_dominated = True
                break

        if not is_dominated:
            non_dominated.append((params, objectives))

    return non_dominated


def calculate_hypervolume(
    front: List[Tuple[float, ...]],
    reference_point: Tuple[float, ...],
) -> float:
    """
    Calculate hypervolume indicator for a Pareto front.

    Hypervolume measures the volume of objective space dominated
    by the front and bounded by a reference point.

    Args:
        front: List of objective tuples
        reference_point: Reference point for hypervolume calculation

    Returns:
        Hypervolume value
    """
    if not front:
        return 0.0

    if len(front[0]) != len(reference_point):
        raise ValueError("Front dimensionality must match reference point")

    # Simple 2D implementation
    if len(front[0]) == 2:
        # Sort by first objective
        sorted_front = sorted(front, key=lambda x: x[0], reverse=True)

        volume = 0.0
        prev_x = reference_point[0]

        for x, y in sorted_front:
            if x > prev_x and y > reference_point[1]:
                width = x - prev_x
                height = y - reference_point[1]
                volume += width * height
                prev_x = x

        return volume

    # For higher dimensions, use simplified approach
    return 0.0


class ScalarizationOptimizer:
    """
    Multi-objective optimizer using scalarization.

    Converts multi-objective problem to single-objective using
    weighted sum, Chebyshev, or other scalarization methods.
    """

    def __init__(
        self,
        config: OptimizationConfig,
        scalarization_method: str = "weighted_sum",
        weights: Optional[List[float]] = None,
    ):
        """
        Initialize scalarization optimizer.

        Args:
            config: Optimization configuration
            scalarization_method: Method for scalarization
                - 'weighted_sum': Simple weighted sum
                - 'chebyshev': Chebyshev scalarization
                - 'augmented_chebyshev': Augmented Chebyshev
            weights: Weights for each objective
        """
        self.config = config
        self.scalarization_method = scalarization_method
        self.weights = weights

    def scalarize(
        self,
        objectives: Tuple[float, ...],
        ideal_point: Optional[Tuple[float, ...]] = None,
    ) -> float:
        """
        Convert multiple objectives to single value.

        Args:
            objectives: Tuple of objective values
            ideal_point: Ideal point for Chebyshev methods

        Returns:
            Scalarized value
        """
        if self.weights is None:
            weights = tuple(1.0 / len(objectives) for _ in objectives)
        else:
            weights = tuple(self.weights)

        if len(weights) != len(objectives):
            raise ValueError("Weights length must match objectives length")

        if self.scalarization_method == "weighted_sum":
            return sum(w * obj for w, obj in zip(weights, objectives))

        elif self.scalarization_method == "chebyshev":
            if ideal_point is None:
                ideal_point = tuple(0.0 for _ in objectives)

            max_weighted_diff = max(
                w * abs(obj - ideal) for w, obj, ideal in zip(weights, objectives, ideal_point)
            )
            return -max_weighted_diff  # Negative for maximization

        elif self.scalarization_method == "augmented_chebyshev":
            if ideal_point is None:
                ideal_point = tuple(0.0 for _ in objectives)

            # Chebyshev part
            chebyshev = max(
                w * abs(obj - ideal) for w, obj, ideal in zip(weights, objectives, ideal_point)
            )

            # Augmented part (weighted sum)
            weighted_sum = sum(w * obj for w, obj in zip(weights, objectives))

            rho = 0.01  # Small augmentation factor
            return -(chebyshev + rho * weighted_sum)

        else:
            raise ValueError(f"Unknown scalarization method: {self.scalarization_method}")

    async def optimize(
        self,
        objectives: List[Callable[[Dict[str, Any]], float]],
        param_grid: ParameterGrid,
        weights: Optional[List[float]] = None,
    ) -> OptimizationResult:
        """
        Optimize using scalarization.

        Args:
            objectives: List of objective functions
            param_grid: Parameter search space
            weights: Optional weights override

        Returns:
            OptimizationResult with best parameters
        """
        if weights:
            self.weights = weights

        # Create scalarized objective
        def scalarized_objective(params):
            obj_values = tuple(obj(params) for obj in objectives)
            return self.scalarize(obj_values)

        # Use single-objective optimizer
        from .random_search import RandomSearchOptimizer

        optimizer = RandomSearchOptimizer(self.config)
        result = await optimizer.optimize(scalarized_objective, param_grid)

        # Store additional info about objectives
        if result.best_trial:
            obj_values = tuple(obj(result.best_params) for obj in objectives)
            result.additional_metrics["all_objectives"] = obj_values

        return result
