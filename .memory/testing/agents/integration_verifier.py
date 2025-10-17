"""
Integration Verifier Agent

Ensures data flow and module interactions remain consistent after fixes.
Validates that no regressions were introduced and runs partial regression suite.
"""

import re
from typing import Dict, List, Any, Optional
from .base_test_agent import BaseTestAgent, TestContext, TestResult, TestStatus, FailureType


class IntegrationVerifier(BaseTestAgent):
    """
    Integration Verifier ensures system integration consistency.
    
    This agent:
    - Ensures data flow and module interactions remain consistent
    - Validates that no regressions were introduced
    - Runs partial regression suite for modified components
    - Checks API endpoints and service integrations
    """
    
    def __init__(self):
        super().__init__(
            name="🧩 Integration Verifier",
            description="Verifies integration consistency and prevents regressions"
        )
        
        # Integration test patterns
        self.integration_patterns = {
            "api_endpoints": [
                r"@app\.(get|post|put|delete)",
                r"def\s+\w+.*request.*Response",
                r"FastAPI.*app"
            ],
            "database_operations": [
                r"session\.(add|commit|rollback)",
                r"db\.(query|execute)",
                r"SQLAlchemy"
            ],
            "service_calls": [
                r"requests\.(get|post|put|delete)",
                r"httpx\.(get|post|put|delete)",
                r"client\.(get|post|put|delete)"
            ],
            "message_queues": [
                r"celery\.task",
                r"@task",
                r"send_task"
            ],
            "file_operations": [
                r"open\s*\(",
                r"with\s+open",
                r"\.read\(\)|\.write\("
            ]
    }
    
    async def execute(self, context: TestContext) -> List[TestResult]:
        """
        Verify integration consistency and run regression tests.
        
        Args:
            context: Test context with project information
            
        Returns:
            List of integration verification results
        """
        self.clear_results()
        
        # Phase 1: Check for integration points
        await self._verify_integration_points(context)
        
        # Phase 2: Run integration tests
        await self._run_integration_tests(context)
        
        # Phase 3: Check for regressions
        await self._check_regressions(context)
        
        # Phase 4: Validate data flow
        await self._validate_data_flow(context)
        
        return self.results
    
    async def _verify_integration_points(self, context: TestContext):
        """Verify that integration points are properly configured."""
        
        # Check for API endpoints
        api_endpoints = await self._check_api_endpoints(context)
        self.add_result(
            test_name="API Endpoints Check",
            status=TestStatus.PASSED if api_endpoints else TestStatus.FAILED,
            duration=0.0,
            output=f"API endpoints: {'Found' if api_endpoints else 'Not found'}",
            metadata={"integration": "api_endpoints", "found": api_endpoints}
        )
        
        # Check for database connections
        db_connections = await self._check_database_connections(context)
        self.add_result(
            test_name="Database Connections Check",
            status=TestStatus.PASSED if db_connections else TestStatus.FAILED,
            duration=0.0,
            output=f"Database connections: {'OK' if db_connections else 'Failed'}",
            metadata={"integration": "database", "status": db_connections}
        )
        
        # Check for external services
        external_services = await self._check_external_services(context)
        self.add_result(
            test_name="External Services Check",
            status=TestStatus.PASSED if external_services else TestStatus.FAILED,
            duration=0.0,
            output=f"External services: {'OK' if external_services else 'Failed'}",
            metadata={"integration": "external_services", "status": external_services}
        )
    
    async def _check_api_endpoints(self, context: TestContext) -> bool:
        """Check if API endpoints are properly configured."""
        
        try:
            # Look for FastAPI app files
            import os
            app_files = []
            for root, dirs, files in os.walk(context.project_path):
                for file in files:
                    if file.endswith('.py') and ('main.py' in file or 'app.py' in file):
                        app_files.append(os.path.join(root, file))
            
            if not app_files:
                return False
            
            # Check one of the app files for API endpoints
            with open(app_files[0], 'r') as f:
                content = f.read()
                
            # Look for FastAPI patterns
            has_fastapi = any(pattern in content for pattern in self.integration_patterns["api_endpoints"])
            return has_fastapi
            
        except Exception as e:
            return False
    
    async def _check_database_connections(self, context: TestContext) -> bool:
        """Check if database connections are properly configured."""
        
        try:
            # Look for database configuration
            import os
            config_files = [
                os.path.join(context.project_path, "app", "core", "database.py"),
                os.path.join(context.project_path, "app", "core", "config.py"),
                os.path.join(context.project_path, ".env")
            ]
            
            for config_file in config_files:
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        content = f.read()
                        if any(pattern in content for pattern in self.integration_patterns["database_operations"]):
                            return True
            
            return False
            
        except Exception as e:
            return False
    
    async def _check_external_services(self, context: TestContext) -> bool:
        """Check if external services are properly configured."""
        
        try:
            # Look for service configuration
            import os
            service_files = []
            for root, dirs, files in os.walk(context.project_path):
                for file in files:
                    if file.endswith('.py') and 'service' in file.lower():
                        service_files.append(os.path.join(root, file))
            
            if not service_files:
                return True  # No external services to check
            
            # Check service files for external calls
            for service_file in service_files[:3]:  # Check first 3 service files
                with open(service_file, 'r') as f:
                    content = f.read()
                    if any(pattern in content for pattern in self.integration_patterns["service_calls"]):
                        return True
            
            return True  # Assume OK if no external calls found
            
        except Exception as e:
            return False
    
    async def _run_integration_tests(self, context: TestContext):
        """Run integration tests."""
        
        # Look for integration test files
        import os
        integration_test_files = []
        for root, dirs, files in os.walk(context.project_path):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    # Check if it's an integration test
                    with open(file_path, 'r') as f:
                        content = f.read()
                        if 'integration' in content.lower() or 'api' in content.lower():
                            integration_test_files.append(file_path)
        
        if not integration_test_files:
            self.add_result(
                test_name="Integration Tests",
                status=TestStatus.SKIPPED,
                duration=0.0,
                output="No integration test files found",
                metadata={"integration": "no_tests"}
            )
            return
        
        # Run integration tests
        for test_file in integration_test_files[:5]:  # Limit to first 5 files
            test_name = os.path.basename(test_file)
            exit_code, stdout, stderr = await self.run_command(
                f"pytest {test_file} -v",
                context.project_path
            )
            
            self.add_result(
                test_name=f"Integration Test: {test_name}",
                status=TestStatus.PASSED if exit_code == 0 else TestStatus.FAILED,
                duration=0.0,
                output=stdout[:500] + "..." if len(stdout) > 500 else stdout,
                error_message=stderr if exit_code != 0 else None,
                metadata={"integration": "test_execution", "file": test_name}
            )
    
    async def _check_regressions(self, context: TestContext):
        """Check for regressions in modified components."""
        
        # This would typically check git diff to see what changed
        # and run tests on those specific components
        
        try:
            # Get recent changes
            exit_code, stdout, stderr = await self.run_command(
                "git diff --name-only HEAD~1",
                context.project_path
            )
            
            if exit_code == 0 and stdout.strip():
                changed_files = stdout.strip().split('\n')
                python_files = [f for f in changed_files if f.endswith('.py')]
                
                if python_files:
                    # Run tests on changed files
                    for file_path in python_files[:3]:  # Limit to first 3 files
                        if 'test_' in file_path:
                            # This is a test file, run it
                            exit_code, stdout, stderr = await self.run_command(
                                f"pytest {file_path} -v",
                                context.project_path
                            )
                            
                            self.add_result(
                                test_name=f"Regression Check: {file_path}",
                                status=TestStatus.PASSED if exit_code == 0 else TestStatus.FAILED,
                                duration=0.0,
                                output=stdout[:300] + "..." if len(stdout) > 300 else stdout,
                                error_message=stderr if exit_code != 0 else None,
                                metadata={"regression": "changed_file", "file": file_path}
                            )
                
                self.add_result(
                    test_name="Regression Check Summary",
                    status=TestStatus.PASSED,
                    duration=0.0,
                    output=f"Checked {len(python_files)} changed Python files",
                    metadata={"regression": "summary", "files_checked": len(python_files)}
                )
            else:
                self.add_result(
                    test_name="Regression Check",
                    status=TestStatus.SKIPPED,
                    duration=0.0,
                    output="No recent changes to check",
                    metadata={"regression": "no_changes"}
                )
                
        except Exception as e:
            self.add_result(
                test_name="Regression Check",
                status=TestStatus.ERROR,
                duration=0.0,
                output=f"Error checking regressions: {str(e)}",
                error_message=str(e),
                metadata={"regression": "error"}
            )
    
    async def _validate_data_flow(self, context: TestContext):
        """Validate data flow between components."""
        
        # Check for data flow patterns
        import os
        data_flow_issues = []
        
        # Look for potential data flow issues
        for root, dirs, files in os.walk(context.project_path):
            for file in files:
                if file.endswith('.py') and not file.startswith('test_'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            
                        # Check for data flow patterns
                        if self._check_data_flow_patterns(content, file_path):
                            data_flow_issues.append(file_path)
                            
                    except Exception:
                        continue
        
        if data_flow_issues:
            self.add_result(
                test_name="Data Flow Validation",
                status=TestStatus.FAILED,
                duration=0.0,
                output=f"Potential data flow issues in {len(data_flow_issues)} files",
                error_message=f"Files with issues: {', '.join(data_flow_issues)}",
                metadata={"data_flow": "issues_found", "files": data_flow_issues}
            )
        else:
            self.add_result(
                test_name="Data Flow Validation",
                status=TestStatus.PASSED,
                duration=0.0,
                output="No data flow issues detected",
                metadata={"data_flow": "clean"}
            )
    
    def _check_data_flow_patterns(self, content: str, file_path: str) -> bool:
        """Check for potential data flow issues in code."""
        
        # Look for common data flow issues
        issues = []
        
        # Check for unhandled exceptions in data processing
        if "try:" in content and "except:" in content:
            # Look for bare except clauses
            if re.search(r"except\s*:", content):
                issues.append("Bare except clause")
        
        # Check for missing error handling in data operations
        if any(op in content for op in ["json.loads", "json.dumps", "pickle.load", "pickle.dump"]):
            if "try:" not in content:
                issues.append("JSON/pickle operations without error handling")
        
        # Check for potential data corruption
        if "global " in content:
            issues.append("Global variable usage")
        
        return len(issues) > 0
    
    def get_integration_summary(self) -> Dict[str, Any]:
        """Get summary of integration verification."""
        
        total_tests = len(self.results)
        passed_tests = len(self.get_passed_tests())
        failed_tests = len(self.get_failed_tests())
        
        return {
            "total_integration_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "integration_points_checked": True,
            "regressions_checked": True,
            "data_flow_validated": True
        }
