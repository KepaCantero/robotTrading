"""
Batch Execution Service

Handles execution of batch backtesting runs in parallel or sequential mode.

Responsibilities:
- Run profiles in parallel using ProcessPoolExecutor
- Run profiles sequentially
- Worker function for parallel execution
- Batch result storage coordination
"""

from __future__ import annotations

import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.backtesting.services.models import ProfileResult

logger = logging.getLogger(__name__)


class BatchExecutionService:
    """
    Service for executing batch backtesting runs.

    Manages parallel and sequential execution of profile backtests
    with proper error handling and result collection.
    """

    def __init__(self, config_path: str, database_service):
        """
        Initialize batch execution service.

        Args:
            config_path: Path to configuration file
            database_service: DatabaseService instance for storing results
        """
        self.config_path = Path(config_path)
        self.database_service = database_service

    def run_all_profiles(
        self,
        profiles: list,
        backtester_class: type,
        parallel: bool = True,
        max_workers: int = 20,
    ) -> dict[str, ProfileResult]:
        """
        Run all profiles with optional parallel execution.

        Args:
            profiles: List of InputProfile objects to test
            backtester_class: ProfileBatchBacktester class (for worker instantiation)
            parallel: Whether to run profiles in parallel
            max_workers: Maximum number of parallel workers

        Returns:
            Dictionary mapping profile_id to ProfileResult
        """
        logger.info(
            f"Running {len(profiles)} profiles (parallel={parallel}, workers={max_workers})"
        )

        if parallel:
            results = self._run_parallel(profiles, backtester_class, max_workers)
        else:
            results = self._run_sequential(profiles, backtester_class)

        return results

    def _run_parallel(
        self, profiles: list, backtester_class: type, max_workers: int
    ) -> dict[str, ProfileResult]:
        """
        Run profiles in parallel using ProcessPoolExecutor.

        Results are collected in parallel and stored sequentially to avoid
        database race conditions with SQLite.

        Args:
            profiles: List of InputProfile objects
            backtester_class: ProfileBatchBacktester class
            max_workers: Maximum number of parallel workers

        Returns:
            Dictionary mapping profile_id to ProfileResult
        """
        results = {}

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_profile = {
                executor.submit(self._run_profile_worker, str(self.config_path), profile): profile
                for profile in profiles
            }

            for future in as_completed(future_to_profile):
                profile = future_to_profile[future]
                try:
                    result = future.result()
                    profile_id = result.profile_id
                    results[profile_id] = result
                    logger.info(f"Completed {profile_id} ({len(results)}/{len(profiles)})")
                except Exception as e:
                    logger.error(f"Profile {profile} failed: {e}", exc_info=True)

        # Batch store all results sequentially after parallel execution completes
        logger.info(f"Parallel execution complete, storing {len(results)} results sequentially...")
        self.database_service.batch_store_results(results)

        return results

    def _run_sequential(self, profiles: list, backtester_class: type) -> dict[str, ProfileResult]:
        """
        Run profiles sequentially.

        Args:
            profiles: List of InputProfile objects
            backtester_class: ProfileBatchBacktester class

        Returns:
            Dictionary mapping profile_id to ProfileResult
        """
        results = {}

        for i, profile in enumerate(profiles, 1):
            try:
                # Create backtester instance for this profile
                backtester = backtester_class(str(self.config_path))
                result = backtester.run_single_profile(profile)
                results[result.profile_id] = result
                logger.info(f"Completed {i}/{len(profiles)}: {result.profile_id}")
            except Exception as e:
                logger.error(f"Profile {profile} failed: {e}", exc_info=True)

        return results

    @staticmethod
    def _run_profile_worker(config_path: str, profile) -> ProfileResult:
        """
        Worker function for parallel execution.

        This static method is called by ProcessPoolExecutor to run
        a single profile in a separate process.

        Args:
            config_path: Path to configuration file
            profile: InputProfile to test

        Returns:
            ProfileResult
        """
        # Import here to avoid pickling issues
        from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

        backtester = ProfileBatchBacktester(config_path)
        return backtester.run_single_profile(profile)
