"""
Data models for parameter optimization.

Defines the core data structures used across all optimization algorithms.
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator

logger = logging.getLogger(__name__)

# Type aliases for parameter values
ParameterValue = Union[str, int, float, bool, Decimal]
ParameterDict = dict[str, ParameterValue]
ParameterValuesList = list[ParameterValue]


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
    values: Optional[ParameterValuesList] = None
    min_value: Optional[Union[float, Decimal]] = None
    max_value: Optional[Union[float, Decimal]] = None
    step: Optional[Union[float, Decimal]] = None
    scale: ParameterScale = ParameterScale.LINEAR
    log_base: float = 10.0

    def __post_init__(self):
        """Validate parameter range after initialization."""
        logger.debug(
            "Initializing parameter range",
            extra={
                "parameter_name": self.name,
                "parameter_type": self.parameter_type.value,
                "scale": self.scale.value,
            },
        )

        # Auto-detect parameter type if not specified
        if self.parameter_type == ParameterType.CONTINUOUS and self.values is not None:
            if all(isinstance(v, (int, bool)) for v in self.values):
                self.parameter_type = ParameterType.CATEGORICAL
                logger.debug(
                    f"Auto-detected parameter type as {ParameterType.CATEGORICAL.value}",
                    extra={"parameter_name": self.name},
                )
            elif all(isinstance(v, int) for v in self.values):
                self.parameter_type = ParameterType.DISCRETE
                logger.debug(
                    f"Auto-detected parameter type as {ParameterType.DISCRETE.value}",
                    extra={"parameter_name": self.name},
                )

        # Validate based on type
        if self.parameter_type == ParameterType.CATEGORICAL:
            if not self.values:
                logger.error(
                    "Categorical parameter missing values", extra={"parameter_name": self.name}
                )
                raise ValueError(f"Categorical parameter '{self.name}' must have values")

        elif self.parameter_type in (ParameterType.CONTINUOUS, ParameterType.INTEGER):
            if self.min_value is None or self.max_value is None:
                logger.error(
                    "Parameter missing min/max values",
                    extra={
                        "parameter_name": self.name,
                        "parameter_type": self.parameter_type.value,
                    },
                )
                raise ValueError(
                    f"Parameter '{self.name}' of type {self.parameter_type} "
                    "must have min_value and max_value"
                )
            if self.min_value >= self.max_value:
                logger.error(
                    "Invalid parameter range: min >= max",
                    extra={
                        "parameter_name": self.name,
                        "min_value": float(self.min_value),
                        "max_value": float(self.max_value),
                    },
                )
                raise ValueError(
                    f"Parameter '{self.name}': min_value ({self.min_value}) "
                    f"must be less than max_value ({self.max_value})"
                )
            if self.scale == ParameterScale.LOG and self.min_value <= 0:
                logger.error(
                    "Log scale requires positive min_value",
                    extra={
                        "parameter_name": self.name,
                        "min_value": float(self.min_value),
                    },
                )
                raise ValueError(f"Parameter '{self.name}': log scale requires positive min_value")

        logger.info(
            "Parameter range initialized successfully",
            extra={
                "parameter_name": self.name,
                "parameter_type": self.parameter_type.value,
            },
        )

    def sample(self) -> ParameterValue:
        """
        Sample a random value from this parameter's range.

        Returns:
            A randomly sampled value

        Raises:
            ValueError: If sampling fails
        """
        import random

        logger.debug(
            "Sampling parameter value",
            extra={
                "parameter_name": self.name,
                "parameter_type": self.parameter_type.value,
            },
        )

        if self.parameter_type == ParameterType.CATEGORICAL:
            if self.values is None:
                raise ValueError(f"Categorical parameter '{self.name}' has no values")
            value = random.choice(self.values)
            logger.debug(
                "Sampled categorical value",
                extra={"parameter_name": self.name, "value": str(value)},
            )
            return value

        elif self.parameter_type == ParameterType.DISCRETE:
            if self.values is None:
                raise ValueError(f"Discrete parameter '{self.name}' has no values")
            value = random.choice(self.values)
            logger.debug(
                "Sampled discrete value", extra={"parameter_name": self.name, "value": str(value)}
            )
            return value

        elif self.parameter_type == ParameterType.INTEGER:
            if self.min_value is None or self.max_value is None:
                raise ValueError(f"Integer parameter '{self.name}' missing min/max values")
            int_min = int(self.min_value)
            int_max = int(self.max_value)
            int_step = int(self.step) if self.step is not None else 1

            if int_step == 1:
                value = random.randint(int_min, int_max)
            else:
                num_steps = (int_max - int_min) // int_step
                random_step = random.randint(0, num_steps)
                value = int_min + random_step * int_step

            logger.debug(
                "Sampled integer value", extra={"parameter_name": self.name, "value": value}
            )
            return value

        elif self.parameter_type == ParameterType.CONTINUOUS:
            if self.min_value is None or self.max_value is None:
                raise ValueError(f"Continuous parameter '{self.name}' missing min/max values")
            float_min = float(self.min_value)
            float_max = float(self.max_value)

            if self.scale == ParameterScale.LOG:
                log_min = self._log(float_min)
                log_max = self._log(float_max)
                log_value = random.uniform(log_min, log_max)
                value = self._exp(log_value)
            else:
                value = random.uniform(float_min, float_max)

            logger.debug(
                "Sampled continuous value", extra={"parameter_name": self.name, "value": value}
            )
            return value

        logger.error(
            "Failed to sample parameter",
            extra={
                "parameter_name": self.name,
                "parameter_type": self.parameter_type.value,
            },
        )
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

    def get_grid_values(self) -> ParameterValuesList:
        """
        Generate grid values for this parameter.

        Returns:
            List of values to use in grid search
        """
        if self.parameter_type == ParameterType.CATEGORICAL:
            if self.values is None:
                raise ValueError(f"Categorical parameter '{self.name}' has no values")
            return self.values

        elif self.parameter_type == ParameterType.DISCRETE:
            if self.values is None:
                raise ValueError(f"Discrete parameter '{self.name}' has no values")
            return self.values

        elif self.parameter_type == ParameterType.INTEGER:
            if self.min_value is None or self.max_value is None:
                raise ValueError(f"Integer parameter '{self.name}' missing min/max values")
            int_min = int(self.min_value)
            int_max = int(self.max_value)
            int_step = int(self.step) if self.step is not None else 1

            return list(range(int_min, int_max + 1, int_step))

        elif self.parameter_type == ParameterType.CONTINUOUS:
            if self.min_value is None or self.max_value is None:
                raise ValueError(f"Continuous parameter '{self.name}' missing min/max values")
            float_min = float(self.min_value)
            float_max = float(self.max_value)
            float_step = float(self.step) if self.step is not None else None

            if float_step:
                if self.scale == ParameterScale.LOG:
                    log_min = self._log(float_min)
                    log_max = self._log(float_max)
                    log_values = []
                    current = log_min
                    while current <= log_max:
                        log_values.append(current)
                        current += self._log(float_step + 1)  # Approximate
                    return [self._exp(v) for v in log_values]
                else:
                    num_steps = int((float_max - float_min) / float_step) + 1
                    return [float_min + i * float_step for i in range(num_steps)]
            else:
                # Default to 10 steps
                if self.scale == ParameterScale.LOG:
                    log_min = self._log(float_min)
                    log_max = self._log(float_max)
                    return [self._exp(log_min + (log_max - log_min) * i / 10) for i in range(11)]
                else:
                    return [float_min + (float_max - float_min) * i / 10 for i in range(11)]

        return []

    def to_dict(self) -> dict[str, Any]:
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
    constraint_func: Callable[[ParameterDict], bool]
    description: str = ""
    violation_penalty: float = float("inf")

    def check(self, params: ParameterDict) -> bool:
        """
        Check if parameters satisfy this constraint.

        Args:
            params: Parameter dictionary

        Returns:
            True if constraint is satisfied
        """
        try:
            result = self.constraint_func(params)
            if not result:
                logger.debug(
                    "Constraint check failed",
                    extra={
                        "constraint_name": self.name,
                        "description": self.description,
                        "params": {k: str(v) for k, v in params.items()},
                    },
                )
            return result
        except Exception as e:
            logger.warning(
                "Constraint check raised exception",
                extra={
                    "constraint_name": self.name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
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

    parameters: list[ParameterRange]
    constraints: list[ParameterConstraint] = field(default_factory=list)

    def __post_init__(self):
        """Validate parameter grid."""
        logger.debug("Initializing parameter grid", extra={"parameter_count": len(self.parameters)})

        if not self.parameters:
            logger.error("Parameter grid has no parameters")
            raise ValueError("ParameterGrid must have at least one parameter")

        # Check for duplicate parameter names
        names = [p.name for p in self.parameters]
        if len(names) != len(set(names)):
            logger.error("Duplicate parameter names found", extra={"parameter_names": names})
            raise ValueError("Duplicate parameter names in ParameterGrid")

        logger.info(
            "Parameter grid initialized",
            extra={
                "parameter_count": len(self.parameters),
                "constraint_count": len(self.constraints),
                "parameter_names": names,
            },
        )

    def generate_combinations(self) -> list[ParameterDict]:
        """
        Generate all parameter combinations for grid search.

        Returns:
            List of parameter dictionaries
        """
        from itertools import product

        logger.debug(
            "Generating parameter combinations for grid search",
            extra={"parameter_count": len(self.parameters)},
        )

        grid_values = [p.get_grid_values() for p in self.parameters]
        param_names = [p.name for p in self.parameters]

        combinations = []
        for combo in product(*grid_values):
            params = dict(zip(param_names, combo))
            # Check constraints
            if self._check_constraints(params):
                combinations.append(params)

        logger.info(
            "Parameter combinations generated",
            extra={
                "total_combinations": len(combinations),
                "parameter_count": len(self.parameters),
            },
        )

        return combinations

    def sample_random(self) -> ParameterDict:
        """
        Sample a random parameter combination.

        Returns:
            Random parameter dictionary
        """
        logger.debug("Sampling random parameter combination", extra={"max_attempts": 100})

        max_attempts = 100
        for attempt in range(max_attempts):
            params = {p.name: p.sample() for p in self.parameters}
            if self._check_constraints(params):
                logger.info(
                    "Random parameter combination sampled",
                    extra={
                        "attempt": attempt + 1,
                        "params": {k: str(v) for k, v in params.items()},
                    },
                )
                return params

        # If no valid combination found after many attempts, return without constraints
        logger.warning(
            "Failed to find valid parameter combination after max attempts",
            extra={"max_attempts": max_attempts},
        )
        return {p.name: p.sample() for p in self.parameters}

    def _check_constraints(self, params: ParameterDict) -> bool:
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

    def to_dict(self) -> dict[str, Any]:
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
    values: Optional[ParameterValuesList] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    scale: ParameterScale = ParameterScale.LINEAR
    log_base: float = 10.0

    @field_validator("parameter_type", "scale", mode="before")
    @classmethod
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

    parameters: list[PydanticParameterRange]
    constraints: list[dict[str, Any]] = []
    total_combinations: int = 0
