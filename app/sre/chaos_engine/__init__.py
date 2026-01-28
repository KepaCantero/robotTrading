"""
Chaos Engineering Module - Proactive Failure Testing (SRE Rule 20)

This module implements chaos engineering practices to proactively test
system resilience by injecting controlled failures.

Components:
- Failure Injection: Inject failures (pod kills, delays, errors)
- Stress Testing: Apply load to find breaking points
- Game Days: Automated chaos experiments
- Blast Radius Control: Limit failure scope
- Hypothesis Testing: Scientific approach to chaos
"""

from .blast_radius import BlastRadiusConfig, BlastRadiusController
from .chaos_orchestrator import ChaosExperiment, ChaosOrchestrator
from .failure_injectors import (
    ErrorInjector,
    FailureInjector,
    LatencyInjector,
    NetworkDelayInjector,
    PodKiller,
    ResourceStarver,
)
from .game_days import GameDay, GameDayReport, GameDayScenario
from .hypothesis import ChaosHypothesis, HypothesisValidator, ValidationResult
from .stress_tester import LoadTest, StressTester, StressTestReport

__all__ = [
    "ChaosOrchestrator",
    "ChaosExperiment",
    "FailureInjector",
    "PodKiller",
    "NetworkDelayInjector",
    "ErrorInjector",
    "LatencyInjector",
    "ResourceStarver",
    "StressTester",
    "LoadTest",
    "StressTestReport",
    "GameDay",
    "GameDayScenario",
    "GameDayReport",
    "BlastRadiusController",
    "BlastRadiusConfig",
    "ChaosHypothesis",
    "HypothesisValidator",
    "ValidationResult",
]
