"""
Data models for parameter optimization.

Defines the core data structures used across all optimization algorithms.
"""

import logging

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import BaseModel, ConfigDict, field_validator


class ParameterType(str, Enum):
    """Type of parameter."""

    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    CATEGORICAL = "categorical"
    INTEGER = "integer"


class ParameterScale(str, Enum):
    """Scale for parameter sampling."""

    LINEAR = "linear"
    LOG = "log"


class TrialStatus(str, Enum):
    """Status of an optimization trial."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PRUNED = "pruned"


@dataclass
class ParameterRange:
    """
    Defines a single parameter's search space.

    Supports:
    - Categorical parameters: values list
    - Discrete parameters: values list or step
    - Continuous parameters: min/max with optional step
    - Integer parameters: min/max with integer step

    Examples:
        ```python
        # Categorical
        ParameterRange(name="strategy", values=["momentum", "mean_reversion"])

        # Continuous
        ParameterRange(name="threshold", min_value=0.1, max_value=2.0, step=0.1)

        # Integer
        ParameterRange(name="lookback", min_value=5, max_value=50, step=5, type="integer")

        # Log scale
        ParameterRange(
            name="learning_rate",
            min_value=1e-5,
            max_value=1e-1,
            scale="log"
        )
        ```
    """

    name: str
    parameter_type: ParameterType = ParameterType.CONTINUOUS
    values: Optional[List[Any]] = None
    min_value: Optional[Union[float, Decimal]] = None
    max_value: Optional[Union[float, Decimal]] = None
    step: Optional[Union[float, Decimal]] = None
    scale: ParameterScale = ParameterScale.LINEAR
    log_base: float = 10.0

    def __post_init__(self):
        """Validate parameter range after initialization."""
        # Auto-detect parameter type if not specified
        if self.parameter_type == ParameterType.CONTINUOUS:
            if self.values is not None:
                if all(isinstance(v, (int, bool)) for v in self.values):
                    self.parameter_type = ParameterType.CATEGORICAL
                elif all(isinstance(v, int) for v in self.values):
                    self.parameter_type = ParameterType.DISCRETE

        # Validate based on type
        if self.parameter_type == ParameterType.CATEGORICAL:
            if not self.values:
                raise ValueError(f"Categorical parameter '{self.name}' must have values")

        elif self.parameter_type in (ParameterType.CONTINUOUS, ParameterType.INTEGER):
            if self.min_value is None or self.max_value is None:
                raise ValueError(
                    f"Parameter '{self.name}' of type {self.parameter_type} "
                    "must have min_value and max_value"
                )
            if self.min_value >= self.max_value:
                raise ValueError(
                    f"Parameter '{self.name}': min_value ({self.min_value}) "
                    f"must be less than max_value ({self.max_value})"
                )
            if self.scale == ParameterScale.LOG and self.min_value <= 0:
                raise ValueError(f"Parameter '{self.name}': log scale requires positive min_value")

    def sample(self) -> Any:
        """
        Sample a random value from this parameter's range.

        Returns:
            A randomly sampled value

        Raises:
            ValueError: If sampling fails
        """
        import random

        if self.parameter_type == ParameterType.CATEGORICAL:
            return random.choice(self.values)  # type: ignore

        elif self.parameter_type == ParameterType.DISCRETE:
            return random.choice(self.values)  # type: ignore

        elif self.parameter_type == ParameterType.INTEGER:
            min_val = int(self.min_value)  # type: ignore
            max_val = int(self.max_value)  # type: ignore
            step = int(self.step) if self.step else 1  # type: ignore

            if step == 1:
                return random.randint(min_val, max_val)
            else:
                num_steps = (max_val - min_val) // step
                random_step = random.randint(0, num_steps)
                return min_val + random_step * step

        elif self.parameter_type == ParameterType.CONTINUOUS:
            min_val = float(self.min_value)  # type: ignore
            max_val = float(self.max_value)  # type: ignore

            if self.scale == ParameterScale.LOG:
                log_min = self._log(min_val)
                log_max = self._log(max_val)
                log_value = random.uniform(log_min, log_max)
                return self._exp(log_value)
            else:
                return random.uniform(min_val, max_val)

        raise ValueError(f"Cannot sample parameter '{self.name}' of type {self.parameter_type}")

    def _log(self, value: float) -> float:
        """Compute log based on log_base."""
        import math

        if self.log_base == math.e:
            return math.log(value)
        elif self.log_base == 2:
            return math.log2(value)
        else:
            return math.log(value, self.log_base)

    def _exp(self, value: float) -> float:
        """Compute exp based on log_base."""
        import math

        if self.log_base == math.e:
            return math.exp(value)
        elif self.log_base == 2:
            return 2**value
        else:
            return self.log_base**value

    def get_grid_values(self) -> List[Any]:
        """
        Generate grid values for this parameter.

        Returns:
            List of values to use in grid search
        """
        if self.parameter_type == ParameterType.CATEGORICAL:
            return self.values  # type: ignore

        elif self.parameter_type == ParameterType.DISCRETE:
            return self.values  # type: ignore

        elif self.parameter_type == ParameterType.INTEGER:
            min_val = int(self.min_value)  # type: ignore
            max_val = int(self.max_value)  # type: ignore
            step = int(self.step) if self.step else 1  # type: ignore

            return list(range(min_val, max_val + 1, step))

        elif self.parameter_type == ParameterType.CONTINUOUS:
            min_val = float(self.min_value)  # type: ignore
            max_val = float(self.max_value)  # type: ignore
            step = float(self.step) if self.step else None  # type: ignore

            if step:
                if self.scale == ParameterScale.LOG:
                    log_min = self._log(min_val)
                    log_max = self._log(max_val)
                    log_values = []
                    current = log_min
                    while current <= log_max:
                        log_values.append(current)
                        current += self._log(step + 1)  # Approximate
                    return [self._exp(v) for v in log_values]
                else:
                    num_steps = int((max_val - min_val) / step) + 1
                    return [min_val + i * step for i in range(num_steps)]
            else:
                # Default to 10 steps
                if self.scale == ParameterScale.LOG:
                    log_min = self._log(min_val)
                    log_max = self._log(max_val)
                    return [self._exp(log_min + (log_max - log_min) * i / 10) for i in range(11)]
                else:
                    return [min_val + (max_val - min_val) * i / 10 for i in range(11)]

        return []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "type": self.parameter_type.value,
            "values": self.values,
            "min_value": float(self.min_value) if self.min_value is not None else None,
            "max_value": float(self.max_value) if self.max_value is not None else None,
            "step": float(self.step) if self.step is not None else None,
            "scale": self.scale.value,
            "log_base": self.log_base,
        }


@dataclass
class ParameterConstraint:
    """
    Constraint on parameter combinations.

    Examples:
        ```python
        # Ensure lookback > threshold
        ParameterConstraint(
            name="lookback_threshold_constraint",
            constraint_func=lambda params: params["lookback"] > params["threshold"],
            description="Lookback period must be greater than threshold"
        )

        # Ensure sum of weights equals 1
        ParameterConstraint(
            name="weight_sum_constraint",
            constraint_func=lambda params: abs(sum(params.values()) - 1.0) < 0.01
        )
        ```
    """

    name: str
    constraint_func: Callable[[Dict[str, Any]], bool]
    description: str = ""
    violation_penalty: float = float("inf")

    def check(self, params: Dict[str, Any]) -> bool:
        """
        Check if parameters satisfy this constraint.

        Args:
            params: Parameter dictionary

        Returns:
            True if constraint is satisfied
        """
        try:
            return self.constraint_func(params)
        except Exception:
            return False


@dataclass
class ParameterGrid:
    """
    Complete parameter search space.

    Defines all parameters to optimize and their valid ranges/values.

    Examples:
        ```python
        param_grid = ParameterGrid(parameters=[
            ParameterRange(name="lookback", min_value=5, max_value=50, step=5),
            ParameterRange(name="threshold", min_value=0.1, max_value=2.0, step=0.1),
            ParameterRange(name="strategy", values=["momentum", "mean_reversion"]),
        ])

        # Generate all combinations
        for params in param_grid.generate_combinations():
            logger.debug(params)

        # Sample random parameters
        params = param_grid.sample_random()
        ```
    """

    parameters: List[ParameterRange]
    constraints: List[ParameterConstraint] = field(default_factory=list)

    def __post_init__(self):
        """Validate parameter grid."""
        if not self.parameters:
            raise ValueError("ParameterGrid must have at least one parameter")

        # Check for duplicate parameter names
        names = [p.name for p in self.parameters]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate parameter names in ParameterGrid")

    def generate_combinations(self) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations for grid search.

        Returns:
            List of parameter dictionaries
        """
        from itertools import product

        grid_values = [p.get_grid_values() for p in self.parameters]
        param_names = [p.name for p in self.parameters]

        combinations = []
        for combo in product(*grid_values):
            params = dict(zip(param_names, combo))
            # Check constraints
            if self._check_constraints(params):
                combinations.append(params)

        return combinations

    def sample_random(self) -> Dict[str, Any]:
        """
        Sample a random parameter combination.

        Returns:
            Random parameter dictionary
        """
        max_attempts = 100
        for _ in range(max_attempts):
            params = {p.name: p.sample() for p in self.parameters}
            if self._check_constraints(params):
                return params

        # If no valid combination found after many attempts, return without constraints
        return {p.name: p.sample() for p in self.parameters}

    def _check_constraints(self, params: Dict[str, Any]) -> bool:
        """Check all constraints."""
        return all(constraint.check(params) for constraint in self.constraints)

    def size(self) -> int:
        """
        Calculate total number of combinations.

        Returns:
            Total number of parameter combinations
        """
        total = 1
        for p in self.parameters:
            total *= len(p.get_grid_values())
        return total

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "parameters": [p.to_dict() for p in self.parameters],
            "constraints": [
                {"name": c.name, "description": c.description} for c in self.constraints
            ],
            "total_combinations": self.size(),
        }


class PydanticParameterRange(BaseModel):
    """Pydantic model for ParameterRange serialization."""

    model_config = ConfigDict(use_enum_values=True)

    name: str
    parameter_type: ParameterType
    values: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    scale: ParameterScale = ParameterScale.LINEAR
    log_base: float = 10.0

    @field_validator("parameter_type", "scale", mode="before")
    def parse_enum(cls, v):
        """Parse string to enum if needed."""
        if isinstance(v, str):
            if v in ParameterType.__members__:
                return ParameterType[v]
            if v in ParameterScale.__members__:
                return ParameterScale[v]
        return v


class PydanticParameterGrid(BaseModel):
    """Pydantic model for ParameterGrid serialization."""

    model_config = ConfigDict(use_enum_values=True)

    parameters: List[PydanticParameterRange]
    constraints: List[Dict[str, Any]] = []
    total_combinations: int = 0
