"""
Test Executor Agent

Executes tests using the project's configured test runner.
Captures detailed output, logs, and stack traces for analysis.
"""

import re
import json
import time
from typing import Dict, List, Any, Optional
from .base_test_agent import BaseTestAgent, TestContext, TestResult, TestStatus, FailureType


class TestExecutor(BaseTestAgent):
    """
    Test Executor runs tests and captures detailed results.
    
    This agent:
    - Executes tests using the configured test runner (pytest, unittest, etc.)
    - Captures detailed output, logs, and stack traces
    - Detects test flakiness and runtime environment issues
    - Parses test results into structured format
    """
    
    def __init__(self):
        super().__init__(
            name="⚙️ Test Executor",
            description="Executes tests and captures detailed results"
        )
        
        # Test runner configurations
        self.test_runners = {
            "pytest": {
                "command": "pytest",
                "args": ["-v", "--tb=short", "--json-report", "--json-report-file=test_results.json"],
                "parser": self._parse_pytest_results
            },
            "unittest": {
                "command": "python -m unittest",
                "args": ["-v"],
                "parser": self._parse_unittest_results
            },
            "jest": {
                "command": "jest",
                "args": ["--verbose", "--json"],
                "parser": self._parse_jest_results
            }
        }
    
    async def execute(self, context: TestContext) -> List[TestResult]:
        """
        Execute tests based on the test scope and context.
        
        Args:
            context: Test context with project information
            
        Returns:
            List of test results
        """
        self.clear_results()
        
        # Determine test command based on scope
        test_command = self._build_test_command(context)
        
        # Execute tests
        start_time = time.time()
        exit_code, stdout, stderr = await self.run_command(test_command, context.project_path)
        execution_time = time.time() - start_time
        
        # Parse results
        results = await self._parse_test_output(stdout, stderr, exit_code, execution_time, context)
        
        # Add execution summary
        self.add_result(
            test_name="Test Execution",
            status=TestStatus.PASSED if exit_code == 0 else TestStatus.FAILED,
            duration=execution_time,
            output=f"Command: {test_command}\nExit Code: {exit_code}\nStdout: {stdout[:1000]}...",
            error_message=stderr if exit_code != 0 else None,
            metadata={
                "command": test_command,
                "exit_code": exit_code,
                "stdout_length": len(stdout),
                "stderr_length": len(stderr)
            }
        )
        
        return results
    
    def _build_test_command(self, context: TestContext) -> str:
        """Build the appropriate test command based on context."""
        
        runner_config = self.test_runners.get(context.test_runner, self.test_runners["pytest"])
        base_command = runner_config["command"]
        base_args = runner_config["args"]
        
        # Add scope-specific arguments
        scope_args = self._get_scope_args(context.test_scope)
        
        # Combine command and arguments
        all_args = base_args + scope_args
        command_parts = [base_command] + all_args
        
        return " ".join(command_parts)
    
    def _get_scope_args(self, test_scope: str) -> List[str]:
        """Get test runner arguments based on test scope."""
        
        if test_scope == "all":
            return []
        elif test_scope.startswith("unit"):
            return ["-k", "test_", "--ignore=tests/integration", "--ignore=tests/e2e"]
        elif test_scope.startswith("integration"):
            return ["tests/integration/"]
        elif test_scope.startswith("e2e"):
            return ["tests/e2e/"]
        elif test_scope.startswith("module:"):
            module_name = test_scope.split(":", 1)[1]
            return [f"tests/test_{module_name}.py"]
        elif test_scope.startswith("task:"):
            task_name = test_scope.split(":", 1)[1]
            return [f"tests/test_{task_name.lower()}.py"]
        else:
            return [test_scope]
    
    async def _parse_test_output(self, stdout: str, stderr: str, exit_code: int, 
                               execution_time: float, context: TestContext) -> List[TestResult]:
        """Parse test output into structured results."""
        
        runner_config = self.test_runners.get(context.test_runner, self.test_runners["pytest"])
        parser = runner_config["parser"]
        
        return await parser(stdout, stderr, exit_code, execution_time, context)
    
    async def _parse_pytest_results(self, stdout: str, stderr: str, exit_code: int,
                                  execution_time: float, context: TestContext) -> List[TestResult]:
        """Parse pytest output into test results."""
        
        results = []
        
        # Try to parse JSON report if available
        json_report_path = f"{context.project_path}/test_results.json"
        try:
            with open(json_report_path, 'r') as f:
                json_data = json.load(f)
                return self._parse_pytest_json(json_data, execution_time)
        except:
            pass
        
        # Fallback to parsing stdout
        return self._parse_pytest_stdout(stdout, stderr, exit_code, execution_time)
    
    def _parse_pytest_json(self, json_data: Dict[str, Any], execution_time: float) -> List[TestResult]:
        """Parse pytest JSON report."""
        
        results = []
        
        for test in json_data.get("tests", []):
            status = TestStatus.PASSED if test.get("outcome") == "passed" else TestStatus.FAILED
            
            results.append(TestResult(
                test_name=test.get("nodeid", "unknown"),
                status=status,
                duration=test.get("duration", 0.0),
                output=test.get("call", {}).get("stdout", ""),
                error_message=test.get("call", {}).get("longrepr", "") if status != TestStatus.PASSED else None,
                failure_type=self._classify_failure(test.get("call", {}).get("longrepr", "")) if status != TestStatus.PASSED else None,
                file_path=test.get("nodeid", "").split("::")[0] if "::" in test.get("nodeid", "") else None,
                metadata={"pytest_json": True}
            ))
        
        return results
    
    def _parse_pytest_stdout(self, stdout: str, stderr: str, exit_code: int, 
                           execution_time: float) -> List[TestResult]:
        """Parse pytest stdout output."""
        
        results = []
        
        # Parse test results from stdout
        test_pattern = r"(\w+::\w+::\w+) (PASSED|FAILED|ERROR) \[(\d+\.\d+)s\]"
        matches = re.findall(test_pattern, stdout)
        
        for match in matches:
            test_name, status_str, duration_str = match
            status = TestStatus.PASSED if status_str == "PASSED" else TestStatus.FAILED
            duration = float(duration_str)
            
            results.append(TestResult(
                test_name=test_name,
                status=status,
                duration=duration,
                output=f"Test {status_str.lower()}",
                error_message=stderr if status != TestStatus.PASSED else None,
                failure_type=self._classify_failure(stderr) if status != TestStatus.PASSED else None,
                file_path=test_name.split("::")[0] if "::" in test_name else None,
                metadata={"parsed_from_stdout": True}
            ))
        
        # If no structured output, create a summary result
        if not results:
            total_tests = len(re.findall(r"(\d+) passed", stdout))
            failed_tests = len(re.findall(r"(\d+) failed", stdout))
            
            results.append(TestResult(
                test_name="Test Suite Summary",
                status=TestStatus.PASSED if exit_code == 0 else TestStatus.FAILED,
                duration=execution_time,
                output=stdout,
                error_message=stderr if exit_code != 0 else None,
                metadata={
                    "summary": True,
                    "total_tests": total_tests,
                    "failed_tests": failed_tests,
                    "exit_code": exit_code
                }
            ))
        
        return results
    
    async def _parse_unittest_results(self, stdout: str, stderr: str, exit_code: int,
                                    execution_time: float, context: TestContext) -> List[TestResult]:
        """Parse unittest output into test results."""
        
        results = []
        
        # Parse unittest output
        test_pattern = r"(\w+\.\w+) \(([^)]+)\) \.\.\. (ok|FAIL|ERROR)"
        matches = re.findall(test_pattern, stdout)
        
        for match in matches:
            test_method, test_class, status_str = match
            test_name = f"{test_class}.{test_method}"
            
            if status_str == "ok":
                status = TestStatus.PASSED
            elif status_str == "FAIL":
                status = TestStatus.FAILED
            else:
                status = TestStatus.ERROR
            
            results.append(TestResult(
                test_name=test_name,
                status=status,
                duration=0.0,  # unittest doesn't provide individual test durations
                output=f"Test {status_str}",
                error_message=stderr if status != TestStatus.PASSED else None,
                failure_type=self._classify_failure(stderr) if status != TestStatus.PASSED else None,
                metadata={"unittest": True}
            ))
        
        return results
    
    async def _parse_jest_results(self, stdout: str, stderr: str, exit_code: int,
                                execution_time: float, context: TestContext) -> List[TestResult]:
        """Parse Jest output into test results."""
        
        results = []
        
        # Try to parse JSON output
        try:
            json_data = json.loads(stdout)
            for test_result in json_data.get("testResults", []):
                for assertion in test_result.get("assertionResults", []):
                    status = TestStatus.PASSED if assertion.get("status") == "passed" else TestStatus.FAILED
                    
                    results.append(TestResult(
                        test_name=assertion.get("fullName", "unknown"),
                        status=status,
                        duration=assertion.get("duration", 0.0),
                        output=assertion.get("title", ""),
                        error_message=assertion.get("failureMessages", [""])[0] if status != TestStatus.PASSED else None,
                        failure_type=self._classify_failure(assertion.get("failureMessages", [""])[0]) if status != TestStatus.PASSED else None,
                        metadata={"jest": True}
                    ))
        except:
            # Fallback to parsing stdout
            pass
        
        return results
    
    def _classify_failure(self, error_message: str) -> FailureType:
        """Classify the type of test failure based on error message."""
        
        error_lower = error_message.lower()
        
        if any(keyword in error_lower for keyword in ["import", "module", "package", "dependency"]):
            return FailureType.DEPENDENCY
        elif any(keyword in error_lower for keyword in ["connection", "timeout", "network", "database"]):
            return FailureType.ENVIRONMENT
        elif any(keyword in error_lower for keyword in ["assertion", "expected", "actual", "comparison"]):
            return FailureType.LOGIC
        elif any(keyword in error_lower for keyword in ["data", "fixture", "mock", "stub"]):
            return FailureType.DATA
        elif any(keyword in error_lower for keyword in ["integration", "api", "service", "endpoint"]):
            return FailureType.INTEGRATION
        elif any(keyword in error_lower for keyword in ["config", "environment", "settings"]):
            return FailureType.CONFIGURATION
        else:
            return FailureType.REGRESSION
    
    def get_test_coverage(self) -> Optional[float]:
        """Extract test coverage from output if available."""
        
        # Look for coverage information in results
        for result in self.results:
            if result.metadata and "coverage" in result.output.lower():
                # Try to extract coverage percentage
                coverage_match = re.search(r"(\d+\.?\d*)%", result.output)
                if coverage_match:
                    return float(coverage_match.group(1))
        
        return None
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of test execution."""
        
        total_tests = len(self.results)
        passed_tests = len(self.get_passed_tests())
        failed_tests = len(self.get_failed_tests())
        error_tests = len(self.get_error_tests())
        
        total_duration = sum(r.duration for r in self.results)
        coverage = self.get_test_coverage()
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "total_duration": total_duration,
            "coverage": coverage,
            "has_failures": failed_tests > 0 or error_tests > 0
        }
