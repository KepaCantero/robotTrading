"""
Failure Diagnostician Agent

Analyzes failed tests to identify root causes and suggest fixes.
Parses error logs and stack traces to categorize failures by type.
"""

import re
import traceback
from typing import Dict, List, Any, Optional
from .base_test_agent import BaseTestAgent, TestContext, TestResult, TestStatus, TestFailure, FailureType, FixConfidence


class FailureDiagnostician(BaseTestAgent):
    """
    Failure Diagnostician analyzes test failures to identify root causes.
    
    This agent:
    - Parses failed test logs and stack traces
    - Identifies root causes (logic bug, dependency issue, etc.)
    - Categorizes failures by type (Regression, Environment, etc.)
    - Suggests minimal viable fix strategies
    """
    
    def __init__(self):
        super().__init__(
            name="🧠 Failure Diagnostician",
            description="Analyzes test failures and identifies root causes"
        )
        
        # Error pattern matchers
        self.error_patterns = {
            "import_error": [
                r"ModuleNotFoundError: No module named '([^']+)'",
                r"ImportError: cannot import name '([^']+)'",
                r"ImportError: No module named ([^\s]+)"
            ],
            "assertion_error": [
                r"AssertionError: (.+)",
                r"assert (.+) failed",
                r"Expected (.+) but got (.+)"
            ],
            "attribute_error": [
                r"AttributeError: '([^']+)' object has no attribute '([^']+)'",
                r"AttributeError: module '([^']+)' has no attribute '([^']+)'"
            ],
            "type_error": [
                r"TypeError: (.+)",
                r"TypeError: '([^']+)' object is not (.+)"
            ],
            "value_error": [
                r"ValueError: (.+)",
                r"ValueError: invalid literal for (.+)"
            ],
            "key_error": [
                r"KeyError: '([^']+)'",
                r"KeyError: (.+)"
            ],
            "connection_error": [
                r"ConnectionError: (.+)",
                r"ConnectionRefusedError: (.+)",
                r"TimeoutError: (.+)"
            ],
            "file_not_found": [
                r"FileNotFoundError: (.+)",
                r"No such file or directory: (.+)"
            ],
            "permission_error": [
                r"PermissionError: (.+)",
                r"Permission denied: (.+)"
            ],
            "syntax_error": [
                r"SyntaxError: (.+)",
                r"IndentationError: (.+)"
            ]
        }
        
        # Fix suggestions by error type
        self.fix_suggestions = {
            "import_error": {
                "root_cause": "Missing or incorrect import statement",
                "suggested_fix": "Add missing import or fix import path",
                "confidence": FixConfidence.HIGH
            },
            "assertion_error": {
                "root_cause": "Test assertion failed - logic or data mismatch",
                "suggested_fix": "Review test data or fix logic in code under test",
                "confidence": FixConfidence.MEDIUM
            },
            "attribute_error": {
                "root_cause": "Object missing expected attribute or method",
                "suggested_fix": "Add missing attribute/method or fix object type",
                "confidence": FixConfidence.HIGH
            },
            "type_error": {
                "root_cause": "Incorrect data type passed to function or method",
                "suggested_fix": "Fix data type or add type conversion",
                "confidence": FixConfidence.HIGH
            },
            "value_error": {
                "root_cause": "Invalid value passed to function or method",
                "suggested_fix": "Validate input values or fix test data",
                "confidence": FixConfidence.MEDIUM
            },
            "key_error": {
                "root_cause": "Dictionary key not found",
                "suggested_fix": "Add missing key or fix key name",
                "confidence": FixConfidence.HIGH
            },
            "connection_error": {
                "root_cause": "Network or service connection failed",
                "suggested_fix": "Check service availability or use mocks for testing",
                "confidence": FixConfidence.MEDIUM
            },
            "file_not_found": {
                "root_cause": "Required file or directory not found",
                "suggested_fix": "Create missing file or fix file path",
                "confidence": FixConfidence.HIGH
            },
            "permission_error": {
                "root_cause": "Insufficient permissions to access resource",
                "suggested_fix": "Fix file permissions or run with appropriate privileges",
                "confidence": FixConfidence.MEDIUM
            },
            "syntax_error": {
                "root_cause": "Python syntax error in code",
                "suggested_fix": "Fix syntax error in source code",
                "confidence": FixConfidence.HIGH
            }
        }
    
    async def execute(self, context: TestContext) -> List[TestResult]:
        """
        Analyze failed tests and diagnose root causes.
        
        Args:
            context: Test context with project information
            
        Returns:
            List of diagnosis results
        """
        self.clear_results()
        
        # Get failed tests from previous execution
        failed_tests = self._get_failed_tests_from_context(context)
        
        if not failed_tests:
            self.add_result(
                test_name="No Failed Tests",
                status=TestStatus.PASSED,
                duration=0.0,
                output="No failed tests to diagnose",
                metadata={"diagnosis": "no_failures"}
            )
            return self.results
        
        # Analyze each failed test
        for test_result in failed_tests:
            await self._diagnose_test_failure(test_result, context)
        
        # Add diagnosis summary
        total_diagnosed = len(self.failures)
        self.add_result(
            test_name="Diagnosis Summary",
            status=TestStatus.PASSED,
            duration=0.0,
            output=f"Diagnosed {total_diagnosed} test failures",
            metadata={
                "diagnosis": "summary",
                "total_diagnosed": total_diagnosed,
                "high_confidence": len([f for f in self.failures if f.confidence == FixConfidence.HIGH]),
                "medium_confidence": len([f for f in self.failures if f.confidence == FixConfidence.MEDIUM])
            }
        )
        
        return self.results
    
    def _get_failed_tests_from_context(self, context: TestContext) -> List[TestResult]:
        """Get failed tests from the test context."""
        
        # This would typically come from the previous test execution
        # For now, we'll simulate by looking for common failure patterns
        failed_tests = []
        
        # Check if there are any test result files or logs
        import os
        test_log_files = [
            f"{context.project_path}/test_results.json",
            f"{context.project_path}/pytest.log",
            f"{context.project_path}/test_output.log"
        ]
        
        for log_file in test_log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        content = f.read()
                        # Parse for failed tests
                        failed_tests.extend(self._parse_failed_tests_from_log(content))
                except:
                    continue
        
        return failed_tests
    
    def _parse_failed_tests_from_log(self, log_content: str) -> List[TestResult]:
        """Parse failed tests from log content."""
        
        failed_tests = []
        
        # Look for pytest failure patterns
        pytest_failures = re.findall(
            r"FAILED\s+([^\s]+)\s+-\s+(.+)",
            log_content
        )
        
        for test_name, error_msg in pytest_failures:
            failed_tests.append(TestResult(
                test_name=test_name,
                status=TestStatus.FAILED,
                duration=0.0,
                output=error_msg,
                error_message=error_msg,
                metadata={"parsed_from_log": True}
            ))
        
        return failed_tests
    
    async def _diagnose_test_failure(self, test_result: TestResult, context: TestContext):
        """Diagnose a single test failure."""
        
        error_message = test_result.error_message or test_result.output
        if not error_message:
            return
        
        # Classify the error type
        error_type = self._classify_error_type(error_message)
        
        # Determine failure type
        failure_type = self._determine_failure_type(error_type, error_message)
        
        # Extract root cause
        root_cause = self._extract_root_cause(error_type, error_message)
        
        # Get fix suggestion
        fix_info = self.fix_suggestions.get(error_type, {
            "root_cause": "Unknown error type",
            "suggested_fix": "Manual investigation required",
            "confidence": FixConfidence.UNCERTAIN
        })
        
        # Identify affected files
        affected_files = self._identify_affected_files(test_result, error_message)
        
        # Create failure diagnosis
        failure = TestFailure(
            test_name=test_result.test_name,
            error_type=error_type,
            error_message=error_message,
            stack_trace=self._extract_stack_trace(error_message),
            failure_type=failure_type,
            root_cause=fix_info["root_cause"],
            suggested_fix=fix_info["suggested_fix"],
            confidence=fix_info["confidence"],
            affected_files=affected_files,
            metadata={
                "original_test": test_result.test_name,
                "diagnosis_timestamp": "2025-01-14T00:00:00Z"
            }
        )
        
        self.failures.append(failure)
        
        # Add diagnosis result
        self.add_result(
            test_name=f"Diagnosis: {test_result.test_name}",
            status=TestStatus.PASSED,
            duration=0.0,
            output=f"Error Type: {error_type}\nRoot Cause: {root_cause}\nSuggested Fix: {fix_info['suggested_fix']}",
            metadata={
                "diagnosis": True,
                "error_type": error_type,
                "failure_type": failure_type.value,
                "confidence": fix_info["confidence"].value,
                "affected_files": affected_files
            }
        )
    
    def _classify_error_type(self, error_message: str) -> str:
        """Classify the type of error based on error message."""
        
        for error_type, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return error_type
        
        return "unknown_error"
    
    def _determine_failure_type(self, error_type: str, error_message: str) -> FailureType:
        """Determine the broader failure type category."""
        
        if error_type in ["import_error", "file_not_found"]:
            return FailureType.DEPENDENCY
        elif error_type in ["connection_error", "permission_error"]:
            return FailureType.ENVIRONMENT
        elif error_type in ["assertion_error", "type_error", "value_error", "key_error"]:
            return FailureType.LOGIC
        elif error_type == "syntax_error":
            return FailureType.CONFIGURATION
        else:
            return FailureType.REGRESSION
    
    def _extract_root_cause(self, error_type: str, error_message: str) -> str:
        """Extract the root cause from the error message."""
        
        if error_type == "import_error":
            match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", error_message)
            if match:
                return f"Missing module: {match.group(1)}"
        
        elif error_type == "assertion_error":
            match = re.search(r"AssertionError: (.+)", error_message)
            if match:
                return f"Assertion failed: {match.group(1)}"
        
        elif error_type == "attribute_error":
            match = re.search(r"AttributeError: '([^']+)' object has no attribute '([^']+)'", error_message)
            if match:
                return f"Object {match.group(1)} missing attribute {match.group(2)}"
        
        elif error_type == "type_error":
            match = re.search(r"TypeError: (.+)", error_message)
            if match:
                return f"Type error: {match.group(1)}"
        
        elif error_type == "key_error":
            match = re.search(r"KeyError: '([^']+)'", error_message)
            if match:
                return f"Missing dictionary key: {match.group(1)}"
        
        return f"Root cause analysis for {error_type}"
    
    def _extract_stack_trace(self, error_message: str) -> str:
        """Extract stack trace from error message."""
        
        # Look for stack trace patterns
        stack_trace_pattern = r"(Traceback \(most recent call last\):.*?)(?=\n\w+:|$)"
        match = re.search(stack_trace_pattern, error_message, re.DOTALL)
        
        if match:
            return match.group(1)
        
        return error_message[:500] + "..." if len(error_message) > 500 else error_message
    
    def _identify_affected_files(self, test_result: TestResult, error_message: str) -> List[str]:
        """Identify files affected by the test failure."""
        
        affected_files = []
        
        # Add test file if available
        if test_result.file_path:
            affected_files.append(test_result.file_path)
        
        # Look for file references in error message
        file_patterns = [
            r'File "([^"]+)"',
            r'File ([^\s,]+)',
            r'([^\s]+\.py)',
            r'([^\s]+\.js)',
            r'([^\s]+\.ts)'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, error_message)
            for match in matches:
                if match not in affected_files and not match.startswith('"'):
                    affected_files.append(match)
        
        return affected_files
    
    def get_high_confidence_fixes(self) -> List[TestFailure]:
        """Get failures with high confidence fixes."""
        return [f for f in self.failures if f.confidence == FixConfidence.HIGH]
    
    def get_medium_confidence_fixes(self) -> List[TestFailure]:
        """Get failures with medium confidence fixes."""
        return [f for f in self.failures if f.confidence == FixConfidence.MEDIUM]
    
    def get_fixable_failures(self) -> List[TestFailure]:
        """Get failures that can be automatically fixed."""
        return [f for f in self.failures if f.confidence in [FixConfidence.HIGH, FixConfidence.MEDIUM]]
    
    def get_diagnosis_summary(self) -> Dict[str, Any]:
        """Get summary of failure diagnoses."""
        
        total_failures = len(self.failures)
        high_confidence = len(self.get_high_confidence_fixes())
        medium_confidence = len(self.get_medium_confidence_fixes())
        fixable = len(self.get_fixable_failures())
        
        # Count by failure type
        failure_types = {}
        for failure in self.failures:
            failure_type = failure.failure_type.value
            failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
        
        return {
            "total_failures": total_failures,
            "high_confidence_fixes": high_confidence,
            "medium_confidence_fixes": medium_confidence,
            "fixable_failures": fixable,
            "fix_rate": (fixable / total_failures * 100) if total_failures > 0 else 0,
            "failure_types": failure_types
        }
