"""
Workflow Manager - Pipeline execution and state management.

Handles the execution of the trading pipeline stages with proper error handling,
state tracking, and rollback capabilities.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Optional

from .models import StageResult, StageType

logger = logging.getLogger(__name__)


class PipelineResult:
    """
    Result of pipeline execution.

    Contains all stage results and overall success status.
    """

    def __init__(
        self,
        success: bool,
        stage_results: list[StageResult],
        total_duration_ms: float,
        error_message: str = "",
    ):
        self.success = success
        self.stage_results = stage_results
        self.total_duration_ms = total_duration_ms
        self.error_message = error_message

    def get_stage_by_type(self, stage_type: StageType) -> Optional[StageResult]:
        """Get result for a specific stage type."""
        for result in self.stage_results:
            if result.stage_type == stage_type:
                return result
        return None


class WorkflowManager:
    """
    Manages the execution workflow of the trading lifecycle.

    Features:
    - Sequential or parallel stage execution
    - Error handling and rollback
    - State tracking and persistence
    - Performance monitoring
    - Comprehensive logging
    """

    def __init__(self, max_concurrent_stages: int = 4):
        """
        Initialize workflow manager.

        Args:
            max_concurrent_stages: Maximum number of stages to run concurrently
        """
        self.max_concurrent_stages = max_concurrent_stages
        self.execution_history: list[PipelineResult] = []
        self._current_state: dict[str, Any] = {}

        logger.info(f"✅ WorkflowManager initialized (max_concurrent={max_concurrent_stages})")

    async def execute_stage(
        self,
        stage_type: StageType,
        stage_func: Callable,
        **kwargs,
    ) -> StageResult:
        """
        Execute a single stage with error handling and timing.

        Args:
            stage_type: Type of stage being executed
            stage_func: Async function to execute
            **kwargs: Arguments to pass to stage_func

        Returns:
            StageResult with execution details
        """
        start_time = datetime.utcnow()
        errors = []
        warnings = []
        data = None

        logger.info(f"▶️  Starting stage: {stage_type.value}")

        try:
            # Execute the stage function
            if asyncio.iscoroutinefunction(stage_func):
                data = await stage_func(**kwargs)
            else:
                data = stage_func(**kwargs)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            result = StageResult(
                stage_type=stage_type,
                success=True,
                data=data,
                message=f"Stage {stage_type.value} completed successfully",
                duration_ms=duration_ms,
                errors=[],
                warnings=warnings,
                metadata={"kwargs": kwargs},
            )

            logger.info(f"✅ Stage {stage_type.value} completed in {duration_ms:.2f}ms")

            # Update state
            self._current_state[stage_type.value] = data

            return result

        except (asyncio.TimeoutError, OSError) as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            error_msg = f"Stage {stage_type.value} failed: {e!s}"
            errors.append(error_msg)

            logger.error(f"❌ {error_msg}", exc_info=True)

            result = StageResult(
                stage_type=stage_type,
                success=False,
                data=None,
                message=error_msg,
                duration_ms=duration_ms,
                errors=errors,
                warnings=warnings,
                metadata={"kwargs": kwargs},
            )

            return result

    async def execute_pipeline(
        self,
        stages: list[tuple[StageType, Callable, dict[str, Any]]],
        stop_on_error: bool = True,
    ) -> PipelineResult:
        """
        Execute a pipeline of stages.

        Args:
            stages: List of (stage_type, stage_func, kwargs) tuples
            stop_on_error: Whether to stop pipeline on first error

        Returns:
            PipelineResult with all stage results
        """
        start_time = datetime.utcnow()
        stage_results: list[StageResult] = []
        pipeline_success = True
        error_message = ""

        logger.info(f"🚀 Starting pipeline execution ({len(stages)} stages)")

        for stage_type, stage_func, kwargs in stages:
            # Execute stage
            result = await self.execute_stage(stage_type, stage_func, **kwargs)
            stage_results.append(result)

            # Check if stage failed
            if not result.success:
                pipeline_success = False
                error_message = f"Pipeline failed at stage: {stage_type.value}"

                if stop_on_error:
                    logger.error(f"🛑 Pipeline stopped due to error in {stage_type.value}")
                    break
                else:
                    logger.warning(f"⚠️ Stage {stage_type.value} failed, continuing pipeline")

        total_duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Store in history
        pipeline_result = PipelineResult(
            success=pipeline_success,
            stage_results=stage_results,
            total_duration_ms=total_duration_ms,
            error_message=error_message,
        )
        self.execution_history.append(pipeline_result)

        logger.info(
            f"🏁 Pipeline execution complete: {'SUCCESS' if pipeline_success else 'FAILED'} "
            f"({total_duration_ms:.2f}ms)"
        )

        return pipeline_result

    async def execute_parallel_stages(
        self,
        stages: list[tuple[StageType, Callable, dict[str, Any]]],
    ) -> list[StageResult]:
        """
        Execute multiple stages in parallel.

        Args:
            stages: List of (stage_type, stage_func, kwargs) tuples

        Returns:
            List of StageResult objects
        """
        logger.info(f"⚡ Executing {len(stages)} stages in parallel")

        # Create tasks for all stages
        tasks = [
            self.execute_stage(stage_type, stage_func, **kwargs)
            for stage_type, stage_func, kwargs in stages
        ]

        # Execute in parallel with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_stages)

        async def bounded_execute(task):
            async with semaphore:
                return await task

        bounded_tasks = [bounded_execute(task) for task in tasks]
        results = await asyncio.gather(*bounded_tasks)

        logger.info(f"✅ Parallel execution complete ({len(results)} stages)")

        return results

    def get_current_state(self) -> dict[str, Any]:
        """Get current workflow state."""
        return self._current_state.copy()

    def reset_state(self):
        """Reset workflow state."""
        self._current_state = {}
        logger.info("🔄 Workflow state reset")

    def get_execution_statistics(self) -> dict[str, Any]:
        """
        Get statistics about pipeline executions.

        Returns:
            Dict with execution metrics
        """
        if not self.execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
            }

        total_executions = len(self.execution_history)
        successful_executions = sum(1 for r in self.execution_history if r.success)
        avg_duration = sum(r.total_duration_ms for r in self.execution_history) / total_executions

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": total_executions - successful_executions,
            "success_rate": successful_executions / total_executions,
            "avg_duration_ms": avg_duration,
            "last_execution": (
                self.execution_history[-1].to_dict() if self.execution_history else None
            ),
        }

    def create_rollback_checkpoint(self) -> dict[str, Any]:
        """
        Create a checkpoint of current state for potential rollback.

        Returns:
            Dict containing current state snapshot
        """
        checkpoint = {
            "state": self.get_current_state(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        logger.debug("📸 Rollback checkpoint created")
        return checkpoint

    async def rollback_to_checkpoint(self, checkpoint: dict[str, Any]) -> bool:
        """
        Rollback to a previous checkpoint.

        Args:
            checkpoint: Checkpoint dict from create_rollback_checkpoint()

        Returns:
            True if rollback successful
        """
        try:
            self._current_state = checkpoint["state"].copy()
            logger.info(f"✅ Rolled back to checkpoint from {checkpoint['timestamp']}")
            return True
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"❌ Rollback failed: {e}", exc_info=True)
            return False
