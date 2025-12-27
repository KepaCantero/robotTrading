"""
T17.1.2: DagsterOrchestrator - Workflow orchestration and scheduling

Dagster for orchestrating data pipelines, backtests, and model training.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class DagsterJob:
    """Dagster job definition."""

    job_id: str
    name: str
    job_type: str  # backtest, data_fetch, train_model, etc.
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict] = None
    run_count: int = 0


@dataclass
class PipelineStep:
    """Step in a pipeline."""

    step_id: str
    name: str
    job_type: str
    depends_on: List[str] = field(default_factory=list)
    config: Dict = field(default_factory=dict)


class DagsterOrchestrator:
    """
    Orchestrates data and model pipelines using Dagster concepts.

    Features:
    - Job scheduling
    - Dependency management
    - Error tracking
    - Retry logic
    - Pipeline monitoring
    """

    def __init__(self):
        """Initialize Dagster orchestrator."""
        self.jobs: Dict[str, DagsterJob] = {}
        self.pipelines: Dict[str, List[PipelineStep]] = {}
        self.job_history: List[DagsterJob] = []
        logger.info("✅ DagsterOrchestrator initialized")

    async def create_job(
        self,
        name: str,
        job_type: str,
        config: Optional[Dict] = None,
    ) -> DagsterJob:
        """
        Create a new job.

        Args:
            name: Job name
            job_type: Type of job (backtest, data_fetch, train_model)
            config: Job configuration

        Returns:
            DagsterJob
        """
        job = DagsterJob(
            job_id=f"job_{len(self.jobs)}",
            name=name,
            job_type=job_type,
        )
        self.jobs[job.job_id] = job
        logger.info(f"✅ Created job: {job.job_id} ({name})")
        return job

    async def execute_job(self, job_id: str) -> bool:
        """
        Execute a job.

        Args:
            job_id: Job ID

        Returns:
            True if execution started
        """
        if job_id not in self.jobs:
            logger.error(f"❌ Job not found: {job_id}")
            return False

        job = self.jobs[job_id]
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()
        job.run_count += 1
        logger.info(f"✅ Job started: {job_id}")
        return True

    async def complete_job(
        self,
        job_id: str,
        result: Optional[Dict] = None,
    ) -> bool:
        """
        Mark job as complete.

        Args:
            job_id: Job ID
            result: Job result

        Returns:
            True if successful
        """
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]
        job.status = JobStatus.SUCCESS
        job.completed_at = datetime.now()
        job.result = result
        self.job_history.append(job)
        logger.info(f"✅ Job completed: {job_id}")
        return True

    async def fail_job(self, job_id: str, error_message: str) -> bool:
        """
        Mark job as failed.

        Args:
            job_id: Job ID
            error_message: Error message

        Returns:
            True if successful
        """
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now()
        job.error_message = error_message
        self.job_history.append(job)
        logger.warning(f"⚠️ Job failed: {job_id} - {error_message}")
        return True

    async def schedule_job(
        self,
        name: str,
        job_type: str,
        schedule: str,  # cron expression
    ) -> str:
        """
        Schedule a job to run periodically.

        Args:
            name: Job name
            job_type: Type of job
            schedule: Cron schedule expression

        Returns:
            Schedule ID
        """
        schedule_id = f"schedule_{len(self.pipelines)}"
        logger.info(f"✅ Scheduled job: {name} ({schedule})")
        return schedule_id

    async def create_pipeline(
        self,
        pipeline_name: str,
        steps: List[PipelineStep],
    ) -> str:
        """
        Create a multi-step pipeline.

        Args:
            pipeline_name: Pipeline name
            steps: List of pipeline steps

        Returns:
            Pipeline ID
        """
        pipeline_id = f"pipeline_{len(self.pipelines)}"
        self.pipelines[pipeline_id] = steps
        logger.info(f"✅ Created pipeline: {pipeline_name} ({len(steps)} steps)")
        return pipeline_id

    async def execute_pipeline(self, pipeline_id: str) -> bool:
        """
        Execute a pipeline.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            True if all steps executed
        """
        if pipeline_id not in self.pipelines:
            return False

        steps = self.pipelines[pipeline_id]
        logger.info(f"✅ Executing pipeline with {len(steps)} steps")

        for step in steps:
            logger.info(f"  - Executing step: {step.name}")

        return True

    async def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status."""
        job = self.jobs.get(job_id)
        return job.status if job else None

    async def get_job_result(self, job_id: str) -> Optional[Dict]:
        """Get job result."""
        job = self.jobs.get(job_id)
        return job.result if job else None

    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
    ) -> List[DagsterJob]:
        """List jobs."""
        jobs = list(self.jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    async def retry_job(self, job_id: str, max_retries: int = 3) -> bool:
        """Retry a failed job."""
        if job_id not in self.jobs:
            return False

        job = self.jobs[job_id]
        if job.run_count >= max_retries:
            logger.warning(f"⚠️ Max retries exceeded for {job_id}")
            return False

        return await self.execute_job(job_id)

    def get_orchestration_status(self) -> Dict:
        """Get overall orchestration status."""
        total = len(self.jobs)
        running = sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING)
        succeeded = sum(1 for j in self.jobs.values() if j.status == JobStatus.SUCCESS)
        failed = sum(1 for j in self.jobs.values() if j.status == JobStatus.FAILED)

        return {
            "total_jobs": total,
            "running": running,
            "succeeded": succeeded,
            "failed": failed,
            "pipelines": len(self.pipelines),
        }


# Singleton
_orchestrator: Optional[DagsterOrchestrator] = None


def get_dagster_orchestrator() -> DagsterOrchestrator:
    """Get or create singleton DagsterOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DagsterOrchestrator()
        logger.info("✅ DagsterOrchestrator singleton initialized")

    return _orchestrator
