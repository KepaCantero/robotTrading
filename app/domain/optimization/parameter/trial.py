# mypy: ignore-errors
"""
Trial tracking for parameter optimization.

Tracks individual optimization trials, their status, and results.
"""

import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

from .models import TrialStatus


@dataclass
class TrialResult:
    """
    Result of a single optimization trial.

    Stores all information about a parameter evaluation including
    parameters used, metrics obtained, and execution metadata.
    """

    trial_id: str
    params: Dict[str, Any]
    objective_value: float
    status: TrialStatus = TrialStatus.COMPLETED
    metrics: Dict[str, float] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    iteration: int = 0
    additional_info: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate duration if timestamps are available."""
        if self.start_time and self.end_time:
            if isinstance(self.start_time, str):
                self.start_time = datetime.fromisoformat(self.start_time)
            if isinstance(self.end_time, str):
                self.end_time = datetime.fromisoformat(self.end_time)

            delta = self.end_time - self.start_time
            self.duration_seconds = delta.total_seconds()

    @property
    def is_success(self) -> bool:
        """Check if trial was successful."""
        return self.status == TrialStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if trial failed."""
        return self.status == TrialStatus.FAILED

    @property
    def is_pruned(self) -> bool:
        """Check if trial was pruned."""
        return self.status == TrialStatus.PRUNED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "trial_id": self.trial_id,
            "params": self.params,
            "objective_value": self.objective_value,
            "status": self.status.value,
            "metrics": self.metrics,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "iteration": self.iteration,
            "additional_info": self.additional_info,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrialResult":
        """Create TrialResult from dictionary."""
        return cls(
            trial_id=data["trial_id"],
            params=data["params"],
            objective_value=data["objective_value"],
            status=TrialStatus(data.get("status", "completed")),
            metrics=data.get("metrics", {}),
            start_time=(
                datetime.fromisoformat(data["start_time"]) if data.get("start_time") else None
            ),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            duration_seconds=data.get("duration_seconds", 0.0),
            error_message=data.get("error_message"),
            iteration=data.get("iteration", 0),
            additional_info=data.get("additional_info", {}),
        )


@dataclass
class TrialHistory:
    """
    History of all trials in an optimization run.

    Tracks all trials, provides statistics, and manages convergence tracking.
    """

    trials: List[TrialResult] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def __post_init__(self):
        """Initialize start time if not set."""
        if not self.start_time:
            self.start_time = datetime.now()

    def add_trial(self, trial: TrialResult) -> None:
        """
        Add a trial to history.

        Args:
            trial: TrialResult to add
        """
        self.trials.append(trial)
        logger.debug(
            "Trial added to history",
            extra={
                "trial_id": trial.trial_id,
                "status": trial.status.value,
                "objective_value": trial.objective_value,
                "iteration": trial.iteration,
                "total_trials": len(self.trials),
            },
        )

    def get_best_trial(self) -> Optional[TrialResult]:
        """
        Get the best trial so far.

        Returns:
            TrialResult with highest objective value, or None if no trials
        """
        if not self.trials:
            logger.debug("No trials in history to find best")
            return None

        successful_trials = [t for t in self.trials if t.is_success]
        if not successful_trials:
            logger.warning(
                "No successful trials found",
                extra={"total_trials": len(self.trials)},
            )
            return None

        best = max(successful_trials, key=lambda t: t.objective_value)
        logger.info(
            "Best trial found",
            extra={
                "trial_id": best.trial_id,
                "objective_value": best.objective_value,
                "iteration": best.iteration,
                "total_successful_trials": len(successful_trials),
            },
        )
        return best

    def get_best_params(self) -> Optional[Dict[str, Any]]:
        """
        Get best parameters from all trials.

        Returns:
            Best parameter dictionary, or None if no successful trials
        """
        best_trial = self.get_best_trial()
        return best_trial.params if best_trial else None

    def get_best_score(self) -> float:
        """
        Get best objective value.

        Returns:
            Best score, or -inf if no successful trials
        """
        best_trial = self.get_best_trial()
        return best_trial.objective_value if best_trial else float("-inf")

    def get_worst_score(self) -> float:
        """
        Get worst objective value from successful trials.

        Returns:
            Worst score, or inf if no successful trials
        """
        successful_trials = [t for t in self.trials if t.is_success]
        if not successful_trials:
            return float("inf")

        return min(t.objective_value for t in successful_trials)

    def get_mean_score(self) -> float:
        """
        Get mean objective value from successful trials.

        Returns:
            Mean score, or 0.0 if no successful trials
        """
        successful_trials = [t for t in self.trials if t.is_success]
        if not successful_trials:
            return 0.0

        return np.mean([t.objective_value for t in successful_trials])

    def get_std_score(self) -> float:
        """
        Get standard deviation of objective values from successful trials.

        Returns:
            Standard deviation, or 0.0 if less than 2 successful trials
        """
        import statistics

        successful_trials = [t for t in self.trials if t.is_success]
        if len(successful_trials) < 2:
            return 0.0

        values = [t.objective_value for t in successful_trials]
        return statistics.stdev(values)

    def get_success_rate(self) -> float:
        """
        Get success rate of trials.

        Returns:
            Ratio of successful to total trials
        """
        if not self.trials:
            return 0.0

        successful = sum(1 for t in self.trials if t.is_success)
        return successful / len(self.trials)

    def get_convergence_iteration(
        self,
        patience: int = 10,
        min_improvement: float = 0.001,
    ) -> Optional[int]:
        """
        Get iteration where optimization converged.

        Convergence is defined as no improvement for 'patience' iterations.

        Args:
            patience: Number of iterations without improvement
            min_improvement: Minimum improvement to reset patience counter

        Returns:
            Iteration number where converged, or None if not converged
        """
        if len(self.trials) < patience:
            return None

        successful = [t for t in self.trials if t.is_success]
        if len(successful) < patience:
            return None

        best_values = []
        for trial in successful:
            if not best_values or trial.objective_value > max(best_values):
                best_values.append(trial.objective_value)
            else:
                best_values.append(best_values[-1])

        # Check for convergence
        for i in range(len(best_values) - patience):
            values_since = best_values[i : i + patience + 1]
            improvement = max(values_since) - min(values_since)

            if improvement < min_improvement:
                return i + patience

        return None

    def check_convergence(
        self,
        patience: int = 10,
        min_improvement: float = 0.001,
    ) -> bool:
        """
        Check if optimization has converged.

        Args:
            patience: Number of iterations without improvement
            min_improvement: Minimum improvement to reset patience counter

        Returns:
            True if converged
        """
        return self.get_convergence_iteration(patience, min_improvement) is not None

    def get_recent_best(self, window: int = 10) -> float:
        """
        Get best score from recent trials.

        Args:
            window: Number of recent trials to consider

        Returns:
            Best score in window, or -inf if insufficient trials
        """
        recent_trials = self.trials[-window:] if len(self.trials) >= window else self.trials
        successful_trials = [t for t in recent_trials if t.is_success]

        if not successful_trials:
            return float("-inf")

        return max(t.objective_value for t in successful_trials)

    def get_improvement_trend(self, window: int = 10) -> List[float]:
        """
        Get trend of best scores over time.

        Args:
            window: Window size for rolling best

        Returns:
            List of best scores in each window
        """
        if not self.trials:
            return []

        trend = []
        for i in range(len(self.trials)):
            window_trials = self.trials[max(0, i - window + 1) : i + 1]
            successful = [t for t in window_trials if t.is_success]

            if successful:
                trend.append(max(t.objective_value for t in successful))
            else:
                trend.append(float("-inf"))

        return trend

    def get_execution_times(self) -> List[float]:
        """Get list of execution times for all trials."""
        return [t.duration_seconds for t in self.trials]

    def get_mean_execution_time(self) -> float:
        """Get mean execution time."""
        times = self.get_execution_times()
        return np.mean(times) if times else 0.0

    def get_total_time(self) -> float:
        """Get total optimization time."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds()

        # Sum of all trial durations
        return sum(self.get_execution_times())

    def finish(self) -> None:
        """Mark optimization as finished."""
        self.end_time = datetime.now()
        logger.info(
            "Optimization finished",
            extra={
                "total_trials": len(self.trials),
                "successful_trials": sum(1 for t in self.trials if t.is_success),
                "failed_trials": sum(1 for t in self.trials if t.is_failed),
                "pruned_trials": sum(1 for t in self.trials if t.is_pruned),
                "best_score": self.get_best_score(),
                "total_time_seconds": self.get_total_time(),
            },
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics.

        Returns:
            Dictionary with summary statistics
        """
        return {
            "total_trials": len(self.trials),
            "successful_trials": sum(1 for t in self.trials if t.is_success),
            "failed_trials": sum(1 for t in self.trials if t.is_failed),
            "pruned_trials": sum(1 for t in self.trials if t.is_pruned),
            "success_rate": self.get_success_rate(),
            "best_score": self.get_best_score(),
            "worst_score": self.get_worst_score(),
            "mean_score": self.get_mean_score(),
            "std_score": self.get_std_score(),
            "best_params": self.get_best_params(),
            "converged": self.get_convergence_iteration() is not None,
            "convergence_iteration": self.get_convergence_iteration(),
            "total_time_seconds": self.get_total_time(),
            "mean_trial_time_seconds": self.get_mean_execution_time(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "trials": [t.to_dict() for t in self.trials],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "summary": self.get_summary(),
        }

    def save(self, filepath: str) -> None:
        """
        Save trial history to file.

        Args:
            filepath: Path to save file (JSON format)
        """
        import json

        logger.info(
            "Saving trial history to file",
            extra={
                "filepath": filepath,
                "total_trials": len(self.trials),
            },
        )

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

        logger.info(
            "Trial history saved successfully",
            extra={"filepath": filepath},
        )

    @classmethod
    def load(cls, filepath: str) -> "TrialHistory":
        """
        Load trial history from file.

        Args:
            filepath: Path to load file (JSON format)

        Returns:
            Loaded TrialHistory
        """
        import json

        logger.info(
            "Loading trial history from file",
            extra={"filepath": filepath},
        )

        with open(filepath, "r") as f:
            data = json.load(f)

        trials = [TrialResult.from_dict(t) for t in data["trials"]]
        history = cls(trials=trials)

        if data.get("start_time"):
            history.start_time = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            history.end_time = datetime.fromisoformat(data["end_time"])

        logger.info(
            "Trial history loaded successfully",
            extra={
                "filepath": filepath,
                "total_trials": len(trials),
            },
        )

        return history


def create_trial_id() -> str:
    """Generate a unique trial ID."""
    import uuid

    return f"trial_{uuid.uuid4().hex[:12]}"


class TrialContext:
    """
    Context manager for running trials.

    Handles timing, error tracking, and result recording.
    """

    def __init__(
        self,
        trial_id: str,
        params: Dict[str, Any],
        iteration: int = 0,
    ):
        self.trial_id = trial_id
        self.params = params
        self.iteration = iteration
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.error: Optional[Exception] = None

        logger.debug(
            "TrialContext created",
            extra={
                "trial_id": trial_id,
                "iteration": iteration,
                "params": params,
            },
        )

    def __enter__(self) -> "TrialContext":
        """Start trial timing."""
        self.start_time = datetime.now()
        logger.info(
            "Trial started",
            extra={
                "trial_id": self.trial_id,
                "iteration": self.iteration,
                "start_time": self.start_time.isoformat(),
            },
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """End trial timing and capture errors."""
        self.end_time = datetime.now()

        if exc_type is not None:
            self.error = exc_val
            logger.error(
                "Trial failed with exception",
                extra={
                    "trial_id": self.trial_id,
                    "iteration": self.iteration,
                    "error_type": exc_type.__name__ if exc_type else None,
                    "error_message": str(exc_val) if exc_val else None,
                },
                exc_info=True,
            )
        else:
            logger.info(
                "Trial completed successfully",
                extra={
                    "trial_id": self.trial_id,
                    "iteration": self.iteration,
                    "duration_seconds": (
                        self.end_time - self.start_time
                    ).total_seconds() if self.start_time else 0,
                },
            )

        # Don't suppress exceptions
        return False

    def create_result(
        self,
        objective_value: float,
        metrics: Optional[Dict[str, float]] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> TrialResult:
        """
        Create TrialResult from this context.

        Args:
            objective_value: Objective function value
            metrics: Additional metrics dictionary
            additional_info: Additional information

        Returns:
            TrialResult populated with context data
        """
        if self.error:
            status = TrialStatus.FAILED
            error_message = str(self.error)
            error_traceback = traceback.format_exception(
                type(self.error), self.error, self.error.__traceback__
            )
        else:
            status = TrialStatus.COMPLETED
            error_message = None
            error_traceback = None

        return TrialResult(
            trial_id=self.trial_id,
            params=self.params,
            objective_value=objective_value,
            status=status,
            metrics=metrics or {},
            start_time=self.start_time,
            end_time=self.end_time,
            error_message=error_message,
            traceback="".join(error_traceback) if error_traceback else None,
            iteration=self.iteration,
            additional_info=additional_info or {},
        )
