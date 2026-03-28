"""
Result Aggregator Module

Aggregates and analyzes results from batch backtesting.
Handles database operations and result storage.

Responsibilities:
- Store individual results in database
- Batch store results from parallel execution
- Query best strategies
- Calculate improvement metrics
- Evaluate readiness for paper trading
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.exc import (
    DatabaseError,
    DataError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.domain.models.input_profile import InputProfile
from app.services.profile_driven_trading.profile_strategy_mapper import StrategyMapping

logger = logging.getLogger(__name__)

# Type alias for nested JSON-like result dictionaries
JsonDict = Dict[str, Union[int, float, str, bool, None, "JsonDict", List[Union[int, float, str, bool, None, "JsonDict"]]]]

Base = declarative_base()


class ProfileResultDB(Base):
    """Database model for profile results."""

    __tablename__ = "profile_results"

    id = Column(String, primary_key=True)
    profile_id = Column(String, unique=True, index=True)
    objective = Column(String, index=True)
    risk_tolerance = Column(String, index=True)
    capital_tier = Column(String, index=True)
    investment_horizon = Column(Integer)

    # Baseline results
    baseline_sharpe = Column(Float)
    baseline_return = Column(Float)
    baseline_max_dd = Column(Float)
    baseline_win_rate = Column(Float)

    # Optimization results
    optimized_sharpe = Column(Float)
    optimized_return = Column(Float)
    optimized_max_dd = Column(Float)
    optimized_win_rate = Column(Float)

    # Improvement metrics
    sharpe_improvement = Column(Float)
    return_improvement = Column(Float)
    max_dd_improvement = Column(Float)
    win_rate_improvement = Column(Float)

    # Best parameters
    best_parameters = Column(JSON)

    # Validation results
    walk_forward_passed = Column(Boolean)
    monte_carlo_passed = Column(Boolean)
    out_of_sample_passed = Column(Boolean)

    # Final recommendation
    ready_for_paper_trading = Column(Boolean)
    recommendation = Column(String)

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> JsonDict:
        """Convert to dictionary."""
        return {
            "profile_id": self.profile_id,
            "objective": self.objective,
            "risk_tolerance": self.risk_tolerance,
            "capital_tier": self.capital_tier,
            "investment_horizon": self.investment_horizon,
            "baseline_results": {
                "sharpe_ratio": self.baseline_sharpe,
                "total_return": self.baseline_return,
                "max_drawdown": self.baseline_max_dd,
                "win_rate": self.baseline_win_rate,
            },
            "optimization_results": {
                "sharpe_ratio": self.optimized_sharpe,
                "total_return": self.optimized_return,
                "max_drawdown": self.optimized_max_dd,
                "win_rate": self.optimized_win_rate,
            },
            "improvement_metrics": {
                "sharpe_improvement": self.sharpe_improvement,
                "return_improvement": self.return_improvement,
                "max_dd_improvement": self.max_dd_improvement,
                "win_rate_improvement": self.win_rate_improvement,
            },
            "best_parameters": self.best_parameters,
            "ready_for_paper_trading": self.ready_for_paper_trading,
            "recommendation": self.recommendation,
        }


@dataclass
class ProfileResult:
    """Complete result for a single profile."""

    profile_id: str
    profile: InputProfile
    baseline_results: JsonDict
    optimization_results: JsonDict
    best_parameters: JsonDict
    improvement_metrics: Dict[str, float]
    comparison: object  # BaselineOptimizationComparison
    ready_for_paper_trading: bool
    recommendation: str
    created_at: datetime = field(default_factory=datetime.now)

    # Multi-strategy support
    strategy_mapping: Optional[StrategyMapping] = None
    enabled_strategies: List[str] = field(default_factory=list)
    learning_engines: List[str] = field(default_factory=list)
    ensemble_config: JsonDict = field(default_factory=dict)
    per_strategy_results: Dict[str, JsonDict] = field(default_factory=dict)


class ResultAggregator:
    """
    Aggregates and stores backtesting results.

    Handles database operations for storing and querying results.
    Provides methods for batch storage and best strategy queries.
    """

    def __init__(self, db_url: str, get_capital_tier_fn):
        """
        Initialize result aggregator.

        Args:
            db_url: Database connection URL
            get_capital_tier_fn: Function to map profile to capital tier key
        """
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.get_capital_tier_fn = get_capital_tier_fn

    def store_result(self, result: ProfileResult) -> None:
        """
        Store single result in database.

        Args:
            result: ProfileResult to store
        """
        session = self.Session()

        try:
            existing = (
                session.query(ProfileResultDB).filter_by(profile_id=result.profile_id).first()
            )

            capital_tier_key = self.get_capital_tier_fn(result.profile)

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
                for key, value in data.items():
                    setattr(existing, key, value)
            else:
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

    def batch_store_results(self, results: Dict[str, ProfileResult]) -> None:
        """
        Store multiple results in database sequentially.

        Args:
            results: Dictionary of profile_id to ProfileResult
        """
        session = self.Session()
        stored_count = 0
        failed_count = 0

        try:
            for result in results.values():
                try:
                    existing = (
                        session.query(ProfileResultDB)
                        .filter_by(profile_id=result.profile_id)
                        .first()
                    )

                    capital_tier_key = self.get_capital_tier_fn(result.profile)

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
                        "win_rate_improvement": result.improvement_metrics.get(
                            "win_rate_improvement"
                        ),
                        "best_parameters": result.best_parameters,
                        "ready_for_paper_trading": result.ready_for_paper_trading,
                        "recommendation": result.recommendation,
                    }

                    if existing:
                        for key, value in data.items():
                            setattr(existing, key, value)
                    else:
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

            session.commit()
            logger.info(f"Batch store complete: {stored_count} stored, {failed_count} failed")

        except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
            session.rollback()
            logger.error(f"Batch store failed: {e}", exc_info=True)

        finally:
            session.close()

    def get_best_strategy(self, objective: str, tier: str, risk: str) -> JsonDict:
        """
        Get best strategy for specific objective, tier, and risk.

        Args:
            objective: Investment objective
            tier: Capital tier
            risk: Risk tolerance

        Returns:
            Best configuration for the criteria
        """
        session = self.Session()

        try:
            results = (
                session.query(ProfileResultDB)
                .filter_by(objective=objective, capital_tier=tier, risk_tolerance=risk)
                .all()
            )

            if not results:
                logger.warning(f"No results found for {objective}_{tier}_{risk}")
                return {}

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

    def calculate_improvements(
        self, baseline: JsonDict, optimized: JsonDict
    ) -> Dict[str, float]:
        """
        Calculate improvement metrics.

        Args:
            baseline: Baseline metrics
            optimized: Optimized metrics

        Returns:
            Dictionary of improvement percentages
        """
        return {
            "sharpe_improvement": self._pct_improvement(
                baseline.get("sharpe_ratio", 0), optimized.get("sharpe_ratio", 0)
            ),
            "return_improvement": self._pct_improvement(
                baseline.get("return_pct", 0), optimized.get("return_pct", 0)
            ),
            "max_dd_improvement": self._pct_improvement(
                abs(baseline.get("max_drawdown", 0)), abs(optimized.get("max_drawdown", 0))
            ),
            "win_rate_improvement": self._pct_improvement(
                baseline.get("win_rate", 0), optimized.get("win_rate", 0)
            ),
        }

    def evaluate_readiness(
        self,
        profile: InputProfile,
        optimized: object,
        improvements: Dict[str, float],
        acceptance_criteria: JsonDict,
    ) -> Tuple[bool, str]:
        """
        Evaluate if strategy is ready for paper trading.

        Args:
            profile: InputProfile
            optimized: OptimizedStrategy result
            improvements: Improvement metrics
            acceptance_criteria: Acceptance criteria thresholds

        Returns:
            Tuple of (ready, recommendation)
        """
        min_sharpe = acceptance_criteria.get("min_sharpe", 1.0)
        min_return = acceptance_criteria.get("min_return", 0.10)
        max_dd = acceptance_criteria.get("max_drawdown", -0.25)
        revision_multiplier = acceptance_criteria.get("revision_multiplier", 0.8)

        sharpe = optimized.optimized_metrics.get("sharpe_ratio", 0)
        total_return = optimized.optimized_metrics.get("return_pct", 0)
        max_dd_value = optimized.optimized_metrics.get("max_drawdown", 0)

        checks = [
            sharpe >= min_sharpe,
            total_return >= min_return,
            max_dd_value >= max_dd,
            optimized.ready_for_paper_trading,
        ]

        if all(checks):
            return True, "APPROVED: All acceptance criteria met"
        elif sharpe >= min_sharpe * revision_multiplier:
            return False, "REVISION: Marginal performance, review recommended"
        else:
            return False, "REJECTED: Insufficient performance"

    def _pct_improvement(self, baseline: float, optimized: float) -> float:
        """Calculate percentage improvement."""
        if baseline == 0:
            return 0.0
        return ((optimized - baseline) / abs(baseline)) * 100
