"""
AlgoTrading Testing System

A comprehensive testing system with specialized agents that execute tests,
diagnose failures, and apply automated fixes.

Usage:
    from .orchestrator import TestingOrchestrator
    
    orchestrator = TestingOrchestrator(project_path=".", memory_bank_path=".memory")
    report = await orchestrator.test_all()
"""

from .orchestrator import TestingOrchestrator, test_all, test_unit, test_integration, test_e2e, test_module, test_task, test_with_fixes
from .agents import (
    LeadTester,
    TestExecutor,
    FailureDiagnostician,
    AutoFixerAgent,
    IntegrationVerifier,
    QAQualityGuardian,
    EnvironmentAuditor
)
from .report_generator import TestReportGenerator

__version__ = "1.0.0"
__author__ = "AlgoTrading MVP Team"

__all__ = [
    "TestingOrchestrator",
    "test_all",
    "test_unit",
    "test_integration",
    "test_e2e",
    "test_module",
    "test_task",
    "test_with_fixes",
    "LeadTester",
    "TestExecutor",
    "FailureDiagnostician",
    "AutoFixerAgent",
    "IntegrationVerifier",
    "QAQualityGuardian",
    "EnvironmentAuditor",
    "TestReportGenerator"
]
