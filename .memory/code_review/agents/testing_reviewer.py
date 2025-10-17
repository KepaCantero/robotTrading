"""
Testing Reviewer Agent

Analyzes code for testing coverage, quality, and best practices.
Focuses on ensuring comprehensive test coverage and proper testing patterns.
"""

import re
import os
from typing import Dict, List, Any
from .base_agent import BaseReviewAgent, ReviewContext, ReviewFinding, Severity


class TestingReviewer(BaseReviewAgent):
    """
    Testing Reviewer validates testing practices and coverage.
    
    This agent checks for:
    - Test coverage and missing tests
    - Test quality and best practices
    - Edge case testing
    - Integration test requirements
    - Test organization and structure
    """
    
    def __init__(self):
        super().__init__(
            name="🧪 Testing Reviewer",
            description="Validates testing practices and coverage"
        )
        
        # Test patterns to look for
        self.test_patterns = {
            "test_function": r"def\s+test_\w+",
            "test_class": r"class\s+Test\w+",
            "assert_statement": r"assert\s+",
            "mock_usage": r"@mock|Mock\(|patch\(",
            "fixture_usage": r"@pytest\.fixture|@fixture",
            "parametrize": r"@pytest\.mark\.parametrize",
            "async_test": r"async\s+def\s+test_\w+"
        }
        
        # Test quality indicators
        self.quality_indicators = {
            "descriptive_names": r"def\s+test_\w+_\w+_\w+",  # Multi-word test names
            "setup_teardown": r"(setUp|tearDown|setup_method|teardown_method)",
            "test_isolation": r"def\s+test_\w+.*:\s*.*def\s+test_\w+",  # Multiple tests
            "edge_cases": r"test.*edge|test.*boundary|test.*limit|test.*empty|test.*none"
        }
    
    async def analyze(self, code_content: str, context: ReviewContext) -> List[ReviewFinding]:
        """Analyze code for testing practices and coverage."""
        self.clear_findings()
        
        # Check if this is test code or production code
        is_test_file = self._is_test_file(context.target_files)
        
        if is_test_file:
            await self._analyze_test_quality(code_content)
            await self._analyze_test_structure(code_content)
            await self._analyze_test_coverage(code_content, context)
        else:
            await self._analyze_missing_tests(code_content, context)
            await self._analyze_testability(code_content)
        
        return self.findings
    
    def _is_test_file(self, target_files: List[str]) -> bool:
        """Check if the analyzed file is a test file."""
        for file_path in target_files:
            if any(test_indicator in file_path.lower() for test_indicator in ["test_", "_test", "tests/"]):
                return True
        return False
    
    async def _analyze_test_quality(self, code_content: str):
        """Analyze the quality of test code."""
        
        # Check for test function naming
        test_functions = re.findall(r"def\s+(test_\w+)", code_content)
        for test_func in test_functions:
            if not re.search(self.quality_indicators["descriptive_names"], test_func):
                self.add_finding(
                    category="Test Quality",
                    summary=f"Test function '{test_func}' has non-descriptive name",
                    severity=Severity.LOW,
                    recommendation=f"Rename '{test_func}' to describe what it tests (e.g., test_user_creation_success)"
                )
        
        # Check for proper assertions
        assert_statements = re.findall(r"assert\s+(.+)", code_content)
        if not assert_statements:
            self.add_finding(
                category="Test Quality",
                summary="No assertions found in test code",
                severity=Severity.HIGH,
                recommendation="Add proper assertions to validate test expectations"
            )
        
        # Check for specific assertions vs generic ones
        generic_asserts = [stmt for stmt in assert_statements if stmt.strip() in ["True", "False", "None"]]
        if generic_asserts:
            self.add_finding(
                category="Test Quality",
                summary=f"Generic assertions found: {len(generic_asserts)} instances",
                severity=Severity.MEDIUM,
                recommendation="Use specific assertions with descriptive messages"
            )
        
        # Check for test isolation
        if not re.search(self.quality_indicators["test_isolation"], code_content, re.DOTALL):
            self.add_finding(
                category="Test Quality",
                summary="Test isolation not evident",
                severity=Severity.MEDIUM,
                recommendation="Ensure tests are independent and don't rely on shared state"
            )
        
        # Check for edge case testing
        if not re.search(self.quality_indicators["edge_cases"], code_content, re.IGNORECASE):
            self.add_finding(
                category="Test Quality",
                summary="No edge case tests detected",
                severity=Severity.MEDIUM,
                recommendation="Add tests for edge cases, boundary conditions, and error scenarios"
            )
    
    async def _analyze_test_structure(self, code_content: str):
        """Analyze test structure and organization."""
        
        # Check for test classes
        test_classes = re.findall(r"class\s+(Test\w+)", code_content)
        if not test_classes:
            self.add_finding(
                category="Test Structure",
                summary="No test classes found - consider organizing tests into classes",
                severity=Severity.LOW,
                recommendation="Group related tests into test classes for better organization"
            )
        
        # Check for setup/teardown methods
        if not re.search(self.quality_indicators["setup_teardown"], code_content):
            self.add_finding(
                category="Test Structure",
                summary="No setup/teardown methods found",
                severity=Severity.LOW,
                recommendation="Add setup and teardown methods for test initialization and cleanup"
            )
        
        # Check for fixtures usage
        if not re.search(self.test_patterns["fixture_usage"], code_content):
            self.add_finding(
                category="Test Structure",
                summary="No pytest fixtures detected",
                severity=Severity.LOW,
                recommendation="Consider using pytest fixtures for test data and setup"
            )
        
        # Check for parametrized tests
        if not re.search(self.test_patterns["parametrize"], code_content):
            self.add_finding(
                category="Test Structure",
                summary="No parametrized tests found",
                severity=Severity.LOW,
                recommendation="Use @pytest.mark.parametrize for testing multiple scenarios"
            )
        
        # Check for async test support
        if "async def" in code_content and not re.search(self.test_patterns["async_test"], code_content):
            self.add_finding(
                category="Test Structure",
                summary="Async code found but no async tests detected",
                severity=Severity.MEDIUM,
                recommendation="Add async tests for async functions using pytest-asyncio"
            )
    
    async def _analyze_test_coverage(self, code_content: str, context: ReviewContext):
        """Analyze test coverage and completeness."""
        
        # Check for mock usage
        if not re.search(self.test_patterns["mock_usage"], code_content):
            self.add_finding(
                category="Test Coverage",
                summary="No mocking detected in tests",
                severity=Severity.MEDIUM,
                recommendation="Use mocks to isolate units under test and avoid external dependencies"
            )
        
        # Check for different types of tests
        test_types = {
            "unit": r"def\s+test_\w+.*unit|class\s+TestUnit",
            "integration": r"def\s+test_\w+.*integration|class\s+TestIntegration",
            "e2e": r"def\s+test_\w+.*e2e|def\s+test_\w+.*end.*to.*end"
        }
        
        found_test_types = []
        for test_type, pattern in test_types.items():
            if re.search(pattern, code_content, re.IGNORECASE):
                found_test_types.append(test_type)
        
        if not found_test_types:
            self.add_finding(
                category="Test Coverage",
                summary="Test type not clearly identified",
                severity=Severity.LOW,
                recommendation="Clearly identify test types (unit, integration, e2e) in test names or classes"
            )
        
        # Check for error handling tests
        error_tests = re.findall(r"def\s+test_\w+.*error|def\s+test_\w+.*exception|def\s+test_\w+.*fail", code_content, re.IGNORECASE)
        if not error_tests:
            self.add_finding(
                category="Test Coverage",
                summary="No error handling tests found",
                severity=Severity.MEDIUM,
                recommendation="Add tests for error conditions and exception handling"
            )
    
    async def _analyze_missing_tests(self, code_content: str, context: ReviewContext):
        """Analyze production code for missing test coverage."""
        
        # Check if corresponding test file exists
        test_file_exists = False
        for file_path in context.target_files:
            test_file_path = self._get_test_file_path(file_path)
            if os.path.exists(test_file_path):
                test_file_exists = True
                break
        
        if not test_file_exists:
            self.add_finding(
                category="Missing Tests",
                summary="No corresponding test file found",
                severity=Severity.HIGH,
                recommendation="Create test file for this module following project test structure"
            )
        
        # Analyze functions that need testing
        functions = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code_content)
        public_functions = [f for f in functions if not f.startswith('_')]
        
        if public_functions:
            self.add_finding(
                category="Missing Tests",
                summary=f"Public functions need testing: {', '.join(public_functions)}",
                severity=Severity.MEDIUM,
                recommendation="Add unit tests for all public functions"
            )
        
        # Check for complex functions that definitely need testing
        complex_functions = []
        function_defs = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*).*?:\s*(.*?)(?=def|\Z)", code_content, re.DOTALL)
        for func_name, func_body in function_defs:
            # Check for complexity indicators
            if any(indicator in func_body for indicator in ["if", "for", "while", "try", "except"]):
                complex_functions.append(func_name)
        
        if complex_functions:
            self.add_finding(
                category="Missing Tests",
                summary=f"Complex functions need comprehensive testing: {', '.join(complex_functions)}",
                severity=Severity.HIGH,
                recommendation="Add comprehensive tests for complex functions including edge cases"
            )
    
    async def _analyze_testability(self, code_content: str):
        """Analyze how testable the production code is."""
        
        # Check for dependency injection
        if "def __init__" in code_content:
            if "Depends(" not in code_content and "inject" not in code_content.lower():
                self.add_finding(
                    category="Testability",
                    summary="Constructor without dependency injection",
                    severity=Severity.MEDIUM,
                    recommendation="Use dependency injection to make code more testable"
                )
        
        # Check for hard-coded dependencies
        hard_coded_deps = ["requests.get", "open(", "input(", "print("]
        for dep in hard_coded_deps:
            if dep in code_content:
                self.add_finding(
                    category="Testability",
                    summary=f"Hard-coded dependency detected: {dep}",
                    severity=Severity.MEDIUM,
                    recommendation="Extract hard-coded dependencies to make code more testable"
                )
        
        # Check for static methods that could be instance methods
        static_methods = re.findall(r"@staticmethod\s*def\s+(\w+)", code_content)
        if static_methods:
            self.add_finding(
                category="Testability",
                summary=f"Static methods found: {', '.join(static_methods)}",
                severity=Severity.LOW,
                recommendation="Consider making static methods instance methods for better testability"
            )
        
        # Check for private methods that might need testing
        private_methods = re.findall(r"def\s+(_\w+)", code_content)
        if private_methods:
            self.add_finding(
                category="Testability",
                summary=f"Private methods found: {', '.join(private_methods)}",
                severity=Severity.LOW,
                recommendation="Consider testing private methods through public interfaces or making them protected"
            )
    
    def _get_test_file_path(self, file_path: str) -> str:
        """Generate the expected test file path for a given file."""
        # Convert app/main.py to tests/test_main.py
        if file_path.startswith("app/"):
            return file_path.replace("app/", "tests/test_")
        elif file_path.startswith("src/"):
            return file_path.replace("src/", "tests/test_")
        else:
            # Generic approach
            dir_name = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            name_without_ext = os.path.splitext(file_name)[0]
            return f"tests/test_{name_without_ext}.py"
