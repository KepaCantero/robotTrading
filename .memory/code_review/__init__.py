"""
AlgoTrading Code Review System

A comprehensive code review system with specialized agents that analyze
code from multiple expert perspectives and generate actionable reports.

Usage:
    from .orchestrator import CodeReviewOrchestrator
    
    orchestrator = CodeReviewOrchestrator(project_path=".", memory_bank_path=".memory")
    report = await orchestrator.review_file("app/main.py")
"""

from .orchestrator import CodeReviewOrchestrator, review_file, review_diff, review_pr
from .agents import (
    LeadReviewer,
    ArchitectureAnalyst,
    AlgorithmExpert,
    CodeQualitySpecialist,
    TestingReviewer,
    SecurityAuditor,
    CICDVerifier
)
from .report_generator import ReportGenerator

__version__ = "1.0.0"
__author__ = "AlgoTrading MVP Team"

__all__ = [
    "CodeReviewOrchestrator",
    "review_file",
    "review_diff", 
    "review_pr",
    "LeadReviewer",
    "ArchitectureAnalyst",
    "AlgorithmExpert",
    "CodeQualitySpecialist",
    "TestingReviewer",
    "SecurityAuditor",
    "CICDVerifier",
    "ReportGenerator"
]
