"""
Base Test Agent

Abstract base class for all testing agents.
Defines the common interface and functionality for specialized test agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import os
import subprocess
import asyncio
from datetime import datetime


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "✅ Passed"
    FAILED = "❌ Failed"
    ERROR = "🔴 Error"
    SKIPPED = "⏭️ Skipped"
    RUNNING = "🔄 Running"


class FailureType(Enum):
    """Types of test failures."""
    REGRESSION = "Regression"
    ENVIRONMENT = "Environment"
    INTEGRATION = "Integration"
    DATA = "Data"
    LOGIC = "Logic"
    DEPENDENCY = "Dependency"
    CONFIGURATION = "Configuration"


class FixConfidence(Enum):
    """Confidence level for automated fixes."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNCERTAIN = "Uncertain"


@dataclass
class TestResult:
    """Individual test result."""
    test_name: str
    status: TestStatus
    duration: float
    output: str
    error_message: Optional[str] = None
    failure_type: Optional[FailureType] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TestFailure:
    """Detailed test failure information."""
    test_name: str
    error_type: str
    error_message: str
    stack_trace: str
    failure_type: FailureType
    root_cause: str
    suggested_fix: str
    confidence: FixConfidence
    affected_files: List[str]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TestContext:
    """Context information for test execution."""
    project_path: str
    memory_bank_path: str
    test_scope: str  # "all", "unit", "integration", "e2e", "module:name", "task:T001"
    environment: str  # "local", "ci", "docker"
    branch_name: Optional[str] = None
    commit_hash: Optional[str] = None
    test_runner: str = "pytest"  # pytest, unittest, jest, etc.
    coverage_threshold: float = 90.0


class BaseTestAgent(ABC):
    """
    Abstract base class for all testing agents.
    
    Each specialized agent should inherit from this class and implement
    the execute method to provide domain-specific testing functionality.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.results: List[TestResult] = []
        self.failures: List[TestFailure] = []
    
    @abstractmethod
    async def execute(self, context: TestContext) -> List[TestResult]:
        """
        Execute the agent's testing functionality.
        
        Args:
            context: Test context with project information
            
        Returns:
            List of test results
        """
        pass
    
    def load_memory_bank(self, memory_bank_path: str) -> Dict[str, Any]:
        """Load project context from memory bank."""
        try:
            memory_data = {}
            
            # Load core memory bank files
            core_files = ["project_brief.md", "tech_context.md", "system_patterns.md", "progress.md"]
            for file_name in core_files:
                file_path = os.path.join(memory_bank_path, "core", file_name)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        key = file_name.replace('.md', '')
                        memory_data[key] = f.read()
            
            # Load active context
            active_path = os.path.join(memory_bank_path, "active_context.md")
            if os.path.exists(active_path):
                with open(active_path, 'r', encoding='utf-8') as f:
                    memory_data['active_context'] = f.read()
            
            return memory_data
            
        except Exception as e:
            print(f"Warning: Could not load memory bank: {e}")
            return {}
    
    async def run_command(self, command: str, cwd: Optional[str] = None) -> Tuple[int, str, str]:
        """
        Run a shell command and return exit code, stdout, and stderr.
        
        Args:
            command: Command to execute
            cwd: Working directory
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            
            stdout, stderr = await process.communicate()
            
            return (
                process.returncode,
                stdout.decode('utf-8', errors='ignore'),
                stderr.decode('utf-8', errors='ignore')
            )
            
        except Exception as e:
            return (-1, "", str(e))
    
    def add_result(self, 
                  test_name: str,
                  status: TestStatus,
                  duration: float,
                  output: str,
                  error_message: Optional[str] = None,
                  failure_type: Optional[FailureType] = None,
                  file_path: Optional[str] = None,
                  line_number: Optional[int] = None,
                  metadata: Optional[Dict[str, Any]] = None):
        """Add a test result."""
        result = TestResult(
            test_name=test_name,
            status=status,
            duration=duration,
            output=output,
            error_message=error_message,
            failure_type=failure_type,
            file_path=file_path,
            line_number=line_number,
            metadata=metadata
        )
        self.results.append(result)
    
    def add_failure(self,
                   test_name: str,
                   error_type: str,
                   error_message: str,
                   stack_trace: str,
                   failure_type: FailureType,
                   root_cause: str,
                   suggested_fix: str,
                   confidence: FixConfidence,
                   affected_files: List[str],
                   metadata: Optional[Dict[str, Any]] = None):
        """Add a test failure."""
        failure = TestFailure(
            test_name=test_name,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            failure_type=failure_type,
            root_cause=root_cause,
            suggested_fix=suggested_fix,
            confidence=confidence,
            affected_files=affected_files,
            metadata=metadata
        )
        self.failures.append(failure)
    
    def get_passed_tests(self) -> List[TestResult]:
        """Get all passed tests."""
        return [r for r in self.results if r.status == TestStatus.PASSED]
    
    def get_failed_tests(self) -> List[TestResult]:
        """Get all failed tests."""
        return [r for r in self.results if r.status == TestStatus.FAILED]
    
    def get_error_tests(self) -> List[TestResult]:
        """Get all error tests."""
        return [r for r in self.results if r.status == TestStatus.ERROR]
    
    def has_failures(self) -> bool:
        """Check if there are any test failures."""
        return len(self.get_failed_tests()) > 0 or len(self.get_error_tests()) > 0
    
    def get_success_rate(self) -> float:
        """Calculate test success rate."""
        if not self.results:
            return 0.0
        
        passed = len(self.get_passed_tests())
        total = len(self.results)
        return (passed / total) * 100
    
    def clear_results(self):
        """Clear all results and failures."""
        self.results.clear()
        self.failures.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent results to dictionary format."""
        return {
            "agent": self.name,
            "description": self.description,
            "results_count": len(self.results),
            "failures_count": len(self.failures),
            "success_rate": self.get_success_rate(),
            "results": [
                {
                    "test_name": r.test_name,
                    "status": r.status.value,
                    "duration": r.duration,
                    "output": r.output,
                    "error_message": r.error_message,
                    "failure_type": r.failure_type.value if r.failure_type else None,
                    "file_path": r.file_path,
                    "line_number": r.line_number,
                    "metadata": r.metadata
                }
                for r in self.results
            ],
            "failures": [
                {
                    "test_name": f.test_name,
                    "error_type": f.error_type,
                    "error_message": f.error_message,
                    "stack_trace": f.stack_trace,
                    "failure_type": f.failure_type.value,
                    "root_cause": f.root_cause,
                    "suggested_fix": f.suggested_fix,
                    "confidence": f.confidence.value,
                    "affected_files": f.affected_files,
                    "metadata": f.metadata
                }
                for f in self.failures
            ]
        }
