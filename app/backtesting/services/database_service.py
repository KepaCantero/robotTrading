"""
Database Service

Handles database operations for profile batch backtesting results.

Responsibilities:
- Store profile results in database
- Query results by objective/risk/tier
- Handle database errors gracefully
- Manage database sessions
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)
from sqlalchemy.orm import sessionmaker

from app.backtesting.services.models import ProfileResult, ProfileResultDB
from app.shared.utils.tier_mapper import map_profile_tier_to_config

if TYPE_CHECKING:
    from pathlib import Path

    from app.domain.models.input_profile import InputProfile

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = ProfileResultDB.__class__.__bases__[0].__bases__[0].__bases__[0]


class DatabaseService:
    """
    Service for database operations.

    Handles storing and querying profile results with proper error handling
    and thread-safe operations.
    """

    def __init__(self, db_url: str, output_dir: Path):
        """
        Initialize database service.

        Args:
            db_url: Database connection URL
            output_dir: Output directory for results
        """
        self.db_url = db_url
        self.output_dir = output_dir
        self.engine = create_engine(db_url)
        # Create all tables
        ProfileResultDB.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        # Lock for thread-safe operations
        self._db_lock = threading.Lock()

    def store_result(self, result: ProfileResult) -> None:
        """
        Store a single profile result in the database.

        Args:
            result: ProfileResult to store
        """
        session = self.Session()
        try:
            with self._db_lock:
                # Check if exists
                existing = (
                    session.query(ProfileResultDB).filter_by(profile_id=result.profile_id).first()
                )

                capital_tier_key = self._get_capital_tier_key(result.profile)

                data = {
                    "profile_id": result.profile_id,
                    "objective": result.profile.objetivo_inversion.value,
                    "risk_tolerance": result.profile.risk_tolerance.value,
                    "capital_tier": capital_tier_key,
                    "investment_horizon": result.profile.investment_horizon,
                    "baseline_sharpe": result.baseline_results.get("sharpe_ratio"),
                    "baseline_return": result.baseline_results.get("return_pct"),
                    "baseline_max_dd": result.baseline_results.get("max_drawdown"),
                    "baseline_win_rate": result.baseline_results.get("win_rate"),
                    "optimized_sharpe": result.optimization_results.get("sharpe_ratio"),
                    "optimized_return": result.optimization_results.get("return_pct"),
                    "optimized_max_dd": result.optimization_results.get("max_drawdown"),
                    "optimized_win_rate": result.optimization_results.get("win_rate"),
                    "sharpe_improvement": result.improvement_metrics.get("sharpe_improvement"),
                    "return_improvement": result.improvement_metrics.get("return_improvement"),
                    "max_dd_improvement": result.improvement_metrics.get("max_dd_improvement"),
                    "win_rate_improvement": result.improvement_metrics.get("win_rate_improvement"),
                    "best_parameters": result.best_parameters,
                    "ready_for_paper_trading": result.ready_for_paper_trading,
                    "recommendation": result.recommendation,
                }

                if existing:
                    # Update existing record
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    # Create new record
                    data["id"] = str(uuid4())
                    db_result = ProfileResultDB(**data)
                    session.add(db_result)

                session.commit()
                logger.debug(f"Stored result for {result.profile_id}")

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            session.rollback()
            logger.error(f"Failed to store result: {e}", exc_info=True)
        finally:
            session.close()

    def batch_store_results(self, results: dict[str, ProfileResult]) -> None:
        """
        Store multiple results in database sequentially.

        This method is called after parallel execution to avoid race conditions
        when multiple workers try to write to SQLite simultaneously.

        Args:
            results: Dictionary of profile_id to ProfileResult
        """
        session = self.Session()
        stored_count = 0
        failed_count = 0

        try:
            with self._db_lock:
                for result in results.values():
                    try:
                        # Check if exists
                        existing = (
                            session.query(ProfileResultDB)
                            .filter_by(profile_id=result.profile_id)
                            .first()
                        )

                        capital_tier_key = self._get_capital_tier_key(result.profile)

                        data = {
                            "profile_id": result.profile_id,
                            "objective": result.profile.objetivo_inversion.value,
                            "risk_tolerance": result.profile.risk_tolerance.value,
                            "capital_tier": capital_tier_key,
                            "investment_horizon": result.profile.investment_horizon,
                            "baseline_sharpe": result.baseline_results.get("sharpe_ratio"),
                            "baseline_return": result.baseline_results.get("return_pct"),
                            "baseline_max_dd": result.baseline_results.get("max_drawdown"),
                            "baseline_win_rate": result.baseline_results.get("win_rate"),
                            "optimized_sharpe": result.optimization_results.get("sharpe_ratio"),
                            "optimized_return": result.optimization_results.get("return_pct"),
                            "optimized_max_dd": result.optimization_results.get("max_drawdown"),
                            "optimized_win_rate": result.optimization_results.get("win_rate"),
                            "sharpe_improvement": result.improvement_metrics.get(
                                "sharpe_improvement"
                            ),
                            "return_improvement": result.improvement_metrics.get(
                                "return_improvement"
                            ),
                            "max_dd_improvement": result.improvement_metrics.get(
                                "max_dd_improvement"
                            ),
                            "win_rate_improvement": result.improvement_metrics.get(
                                "win_rate_improvement"
                            ),
                            "best_parameters": result.best_parameters,
                            "ready_for_paper_trading": result.ready_for_paper_trading,
                            "recommendation": result.recommendation,
                        }

                        if existing:
                            # Update
                            for key, value in data.items():
                                setattr(existing, key, value)
                        else:
                            # Create
                            data["id"] = str(uuid4())
                            db_result = ProfileResultDB(**data)
                            session.add(db_result)

                        stored_count += 1

                    except (
                        IntegrityError,
                        OperationalError,
                        DatabaseError,
                        DataError,
                        ProgrammingError,
                    ) as e:
                        failed_count += 1
                        logger.error(f"Failed to store result for {result.profile_id}: {e}")
                        # Continue with next result

                session.commit()
                logger.info(f"Batch store complete: {stored_count} stored, {failed_count} failed")

        except (
            IntegrityError,
            OperationalError,
            DatabaseError,
            DataError,
            ProgrammingError,
        ) as e:
            session.rollback()
            logger.error(f"Batch store failed: {e}", exc_info=True)
        finally:
            session.close()

    def get_best_strategy(self, objective: str, tier: str, risk: str) -> dict[str, Any]:
        """
        Get best strategy for specific objective, tier, and risk.

        Args:
            objective: Investment objective (maximizar_capital, etc.)
            tier: Capital tier (bajo, medio, alto)
            risk: Risk tolerance (bajo, medio, alto)

        Returns:
            Best configuration for the criteria
        """
        session = self.Session()
        try:
            # Query database
            results = (
                session.query(ProfileResultDB)
                .filter_by(objective=objective, capital_tier=tier, risk_tolerance=risk)
                .all()
            )

            if not results:
                logger.warning(f"No results found for {objective}_{tier}_{risk}")
                return {}

            # Sort by optimized Sharpe ratio
            best = max(results, key=lambda r: r.optimized_sharpe or 0)

            return {
                "profile_id": best.profile_id,
                "objective": best.objective,
                "risk_tolerance": best.risk_tolerance,
                "capital_tier": best.capital_tier,
                "baseline_metrics": {
                    "sharpe_ratio": best.baseline_sharpe,
                    "total_return": best.baseline_return,
                    "max_drawdown": best.baseline_max_dd,
                    "win_rate": best.baseline_win_rate,
                },
                "optimized_metrics": {
                    "sharpe_ratio": best.optimized_sharpe,
                    "total_return": best.optimized_return,
                    "max_drawdown": best.optimized_max_dd,
                    "win_rate": best.optimized_win_rate,
                },
                "best_parameters": best.best_parameters,
                "improvement": {
                    "sharpe": best.sharpe_improvement,
                    "return": best.return_improvement,
                    "max_dd": best.max_dd_improvement,
                    "win_rate": best.win_rate_improvement,
                },
                "ready_for_paper_trading": best.ready_for_paper_trading,
                "recommendation": best.recommendation,
            }
        finally:
            session.close()

    @staticmethod
    def _get_capital_tier_key(profile: InputProfile) -> str:
        """
        Map capital_flag to config tier key using unified tier mapping.

        Args:
            profile: InputProfile

        Returns:
            Mapped tier key for config lookups (bajo, medio, or alto)
        """
        try:
            return map_profile_tier_to_config(profile.capital_flag, target_format="spanish")
        except OSError as e:
            logger.warning(f"Tier mapper failed for {profile.capital_flag}, using fallback: {e}")
            tier_map = {"small": "bajo", "medium": "medio", "large": "alto"}
            return tier_map.get(profile.capital_flag, "medio")
