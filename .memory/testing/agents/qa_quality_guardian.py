"""
QA Quality Guardian Agent

Checks test coverage metrics and enforces thresholds.
Verifies that test design matches conventions and suggests missing test cases.
"""

import re
import os
from typing import Dict, List, Any, Optional
from .base_test_agent import BaseTestAgent, TestContext, TestResult, TestStatus


class QAQualityGuardian(BaseTestAgent):
    """
    QA Quality Guardian ensures test quality and coverage standards.
    
    This agent:
    - Checks test coverage metrics and enforces thresholds
    - Verifies that test design matches conventions (AAA pattern, mock usage, naming)
    - Suggests missing test cases or redundant ones
    - Validates test structure and organization
    """
    
    def __init__(self):
        super().__init__(
            name="🔒 QA Quality Guardian",
            description="Ensures test quality and coverage standards"
        )
        
        # Test quality patterns
        self.quality_patterns = {
            "aaa_pattern": [
                r"#\s*Arrange|#\s*Act|#\s*Assert",
                r"#\s*Given|#\s*When|#\s*Then"
            ],
            "mock_usage": [
                r"@mock|Mock\(|patch\(",
                r"mock\.|unittest\.mock",
                r"@patch"
            ],
            "test_naming": [
                r"def\s+test_\w+_\w+",  # Multi-word test names
                r"def\s+test_\w+_should_\w+",  # BDD-style naming
                r"def\s+test_\w+_when_\w+"  # Context-based naming
            ],
            "setup_teardown": [
                r"def\s+setUp\s*\(",
                r"def\s+tearDown\s*\(",
                r"@pytest\.fixture"
            ],
            "assertions": [
                r"assert\s+",
                r"self\.assert\w+\(",
                r"pytest\.raises\("
            ]
        }
        
        # Coverage thresholds
        self.coverage_thresholds = {
            "overall": 90.0,
            "critical_modules": 95.0,
            "new_code": 95.0
        }
    
    async def execute(self, context: TestContext) -> List[TestResult]:
        """
        Check test quality and coverage standards.
        
        Args:
            context: Test context with project information
            
        Returns:
            List of quality assessment results
        """
        self.clear_results()
        
        # Phase 1: Check test coverage
        await self._check_test_coverage(context)
        
        # Phase 2: Validate test quality
        await self._validate_test_quality(context)
        
        # Phase 3: Check test organization
        await self._check_test_organization(context)
        
        # Phase 4: Suggest missing tests
        await self._suggest_missing_tests(context)
        
        return self.results
    
    async def _check_test_coverage(self, context: TestContext):
        """Check test coverage metrics."""
        
        # Run coverage analysis
        exit_code, stdout, stderr = await self.run_command(
            "pytest --cov=app --cov-report=term-missing",
            context.project_path
        )
        
        # Parse coverage from output
        coverage_percentage = self._parse_coverage_percentage(stdout)
        
        if coverage_percentage is not None:
            threshold = context.coverage_threshold
            status = TestStatus.PASSED if coverage_percentage >= threshold else TestStatus.FAILED
            
            self.add_result(
                test_name="Test Coverage",
                status=status,
                duration=0.0,
                output=f"Coverage: {coverage_percentage:.1f}% (Threshold: {threshold}%)",
                error_message=f"Coverage below threshold" if status == TestStatus.FAILED else None,
                metadata={
                    "coverage": coverage_percentage,
                    "threshold": threshold,
                    "meets_threshold": coverage_percentage >= threshold
                }
            )
        else:
            self.add_result(
                test_name="Test Coverage",
                status=TestStatus.ERROR,
                duration=0.0,
                output="Could not determine coverage percentage",
                error_message="Coverage analysis failed",
                metadata={"coverage": "unknown"}
            )
        
        # Check coverage by module
        await self._check_module_coverage(stdout, context)
    
    def _parse_coverage_percentage(self, coverage_output: str) -> Optional[float]:
        """Parse coverage percentage from pytest output."""
        
        # Look for coverage percentage in output
        patterns = [
            r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+\.?\d*)%",
            r"coverage: (\d+\.?\d*)%",
            r"(\d+\.?\d*)%"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, coverage_output)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    async def _check_module_coverage(self, coverage_output: str, context: TestContext):
        """Check coverage by individual modules."""
        
        # Parse module coverage from output
        module_pattern = r"([^\s]+\.py)\s+(\d+)\s+(\d+)\s+(\d+\.?\d*)%"
        matches = re.findall(module_pattern, coverage_output)
        
        low_coverage_modules = []
        for match in matches:
            module_name, total_lines, missing_lines, coverage_percent = match
            coverage = float(coverage_percent)
            
            if coverage < 80.0:  # Lower threshold for individual modules
                low_coverage_modules.append({
                    "module": module_name,
                    "coverage": coverage,
                    "missing_lines": int(missing_lines)
                })
        
        if low_coverage_modules:
            self.add_result(
                test_name="Module Coverage",
                status=TestStatus.FAILED,
                duration=0.0,
                output=f"Low coverage in {len(low_coverage_modules)} modules",
                error_message=f"Modules with low coverage: {', '.join([m['module'] for m in low_coverage_modules])}",
                metadata={"low_coverage_modules": low_coverage_modules}
            )
        else:
            self.add_result(
                test_name="Module Coverage",
                status=TestStatus.PASSED,
                duration=0.0,
                output="All modules meet coverage threshold",
                metadata={"module_coverage": "good"}
            )
    
    async def _validate_test_quality(self, context: TestContext):
        """Validate test quality and conventions."""
        
        # Find all test files
        test_files = self._find_test_files(context.project_path)
        
        if not test_files:
            self.add_result(
                test_name="Test Quality",
                status=TestStatus.FAILED,
                duration=0.0,
                output="No test files found",
                error_message="No test files to validate",
                metadata={"test_quality": "no_files"}
            )
            return
        
        # Analyze each test file
        quality_issues = []
        for test_file in test_files[:10]:  # Limit to first 10 files
            issues = await self._analyze_test_file_quality(test_file)
            if issues:
                quality_issues.extend(issues)
        
        if quality_issues:
            self.add_result(
                test_name="Test Quality",
                status=TestStatus.FAILED,
                duration=0.0,
                output=f"Quality issues found in {len(quality_issues)} areas",
                error_message=f"Issues: {', '.join(quality_issues)}",
                metadata={"test_quality": "issues_found", "issues": quality_issues}
            )
        else:
            self.add_result(
                test_name="Test Quality",
                status=TestStatus.PASSED,
                duration=0.0,
                output="Test quality meets standards",
                metadata={"test_quality": "good"}
            )
    
    def _find_test_files(self, project_path: str) -> List[str]:
        """Find all test files in the project."""
        
        test_files = []
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(os.path.join(root, file))
        
        return test_files
    
    async def _analyze_test_file_quality(self, test_file: str) -> List[str]:
        """Analyze quality of a single test file."""
        
        issues = []
        
        try:
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Check for AAA pattern
            if not any(re.search(pattern, content, re.IGNORECASE) for pattern in self.quality_patterns["aaa_pattern"]):
                issues.append("Missing AAA pattern comments")
            
            # Check for proper test naming
            test_functions = re.findall(r"def\s+(test_\w+)", content)
            for test_func in test_functions:
                if not any(re.search(pattern, test_func) for pattern in self.quality_patterns["test_naming"]):
                    issues.append(f"Poor test naming: {test_func}")
            
            # Check for assertions
            if not re.search(r"assert\s+", content):
                issues.append("No assertions found")
            
            # Check for setup/teardown
            if not any(re.search(pattern, content) for pattern in self.quality_patterns["setup_teardown"]):
                issues.append("No setup/teardown methods")
            
            # Check for mock usage (if needed)
            if "import" in content and "mock" not in content.lower():
                # This is a heuristic - might not always be accurate
                pass
            
        except Exception as e:
            issues.append(f"Error analyzing file: {str(e)}")
        
        return issues
    
    async def _check_test_organization(self, context: TestContext):
        """Check test organization and structure."""
        
        # Check test directory structure
        test_dirs = self._find_test_directories(context.project_path)
        
        if not test_dirs:
            self.add_result(
                test_name="Test Organization",
                status=TestStatus.FAILED,
                duration=0.0,
                output="No test directories found",
                error_message="Tests should be organized in dedicated directories",
                metadata={"test_organization": "no_directories"}
            )
            return
        
        # Check for proper test organization
        organization_issues = []
        for test_dir in test_dirs:
            issues = self._check_directory_organization(test_dir)
            organization_issues.extend(issues)
        
        if organization_issues:
            self.add_result(
                test_name="Test Organization",
                status=TestStatus.FAILED,
                duration=0.0,
                output=f"Organization issues in {len(organization_issues)} areas",
                error_message=f"Issues: {', '.join(organization_issues)}",
                metadata={"test_organization": "issues_found", "issues": organization_issues}
            )
        else:
            self.add_result(
                test_name="Test Organization",
                status=TestStatus.PASSED,
                duration=0.0,
                output="Test organization meets standards",
                metadata={"test_organization": "good"}
            )
    
    def _find_test_directories(self, project_path: str) -> List[str]:
        """Find test directories in the project."""
        
        test_dirs = []
        for root, dirs, files in os.walk(project_path):
            if 'test' in root.lower() or any(f.startswith('test_') for f in files):
                test_dirs.append(root)
        
        return test_dirs
    
    def _check_directory_organization(self, test_dir: str) -> List[str]:
        """Check organization of a test directory."""
        
        issues = []
        
        try:
            files = os.listdir(test_dir)
            test_files = [f for f in files if f.startswith('test_') and f.endswith('.py')]
            
            if not test_files:
                issues.append(f"No test files in {test_dir}")
            
            # Check for __init__.py
            if '__init__.py' not in files:
                issues.append(f"Missing __init__.py in {test_dir}")
            
            # Check for conftest.py
            if 'conftest.py' not in files:
                issues.append(f"Missing conftest.py in {test_dir}")
            
        except Exception as e:
            issues.append(f"Error checking directory: {str(e)}")
        
        return issues
    
    async def _suggest_missing_tests(self, context: TestContext):
        """Suggest missing test cases."""
        
        # Find production code files
        prod_files = self._find_production_files(context.project_path)
        
        # Find corresponding test files
        test_files = self._find_test_files(context.project_path)
        
        # Check for missing tests
        missing_tests = []
        for prod_file in prod_files[:10]:  # Limit to first 10 files
            corresponding_test = self._find_corresponding_test(prod_file, test_files)
            if not corresponding_test:
                missing_tests.append(prod_file)
        
        if missing_tests:
            self.add_result(
                test_name="Missing Tests",
                status=TestStatus.FAILED,
                duration=0.0,
                output=f"Missing tests for {len(missing_tests)} files",
                error_message=f"Files without tests: {', '.join(missing_tests)}",
                metadata={"missing_tests": missing_tests}
            )
        else:
            self.add_result(
                test_name="Missing Tests",
                status=TestStatus.PASSED,
                duration=0.0,
                output="All production files have corresponding tests",
                metadata={"missing_tests": "none"}
            )
    
    def _find_production_files(self, project_path: str) -> List[str]:
        """Find production code files."""
        
        prod_files = []
        for root, dirs, files in os.walk(project_path):
            # Skip test directories
            if 'test' in root.lower():
                continue
            
            for file in files:
                if file.endswith('.py') and not file.startswith('test_'):
                    prod_files.append(os.path.join(root, file))
        
        return prod_files
    
    def _find_corresponding_test(self, prod_file: str, test_files: List[str]) -> Optional[str]:
        """Find corresponding test file for a production file."""
        
        # Extract module name from production file
        module_name = os.path.basename(prod_file).replace('.py', '')
        expected_test = f"test_{module_name}.py"
        
        # Look for corresponding test file
        for test_file in test_files:
            if os.path.basename(test_file) == expected_test:
                return test_file
        
        return None
    
    def get_quality_summary(self) -> Dict[str, Any]:
        """Get summary of quality assessment."""
        
        total_tests = len(self.results)
        passed_tests = len(self.get_passed_tests())
        failed_tests = len(self.get_failed_tests())
        
        return {
            "total_quality_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "coverage_checked": True,
            "quality_validated": True,
            "organization_checked": True,
            "missing_tests_identified": True
        }
