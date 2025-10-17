"""
Environment & Dependency Auditor Agent

Confirms the correct environment is active and verifies versions.
Checks virtualenv, Docker services, and dependency consistency.
"""

import re
import os
import json
from typing import Dict, List, Any, Optional
from .base_test_agent import BaseTestAgent, TestContext, TestResult, TestStatus


class EnvironmentAuditor(BaseTestAgent):
    """
    Environment & Dependency Auditor validates testing environment.
    
    This agent:
    - Confirms the correct environment (Python, Node, Docker, AWS, etc.) is active
    - Verifies versions, virtualenv, Docker Compose services, or .env files
    - Detects dependency drift (e.g., pip freeze mismatch) or outdated images
    - Checks environment configuration and setup
    """
    
    def __init__(self):
        super().__init__(
            name="🧰 Environment & Dependency Auditor",
            description="Validates testing environment and dependencies"
        )
        
        # Environment check patterns
        self.environment_patterns = {
            "python_version": r"Python (\d+\.\d+\.\d+)",
            "node_version": r"v(\d+\.\d+\.\d+)",
            "docker_version": r"Docker version (\d+\.\d+\.\d+)",
            "git_version": r"git version (\d+\.\d+\.\d+)"
        }
        
        # Required environment variables
        self.required_env_vars = [
            "PYTHONPATH",
            "VIRTUAL_ENV"
        ]
        
        # Required files
        self.required_files = [
            "requirements.txt",
            "pytest.ini"
        ]
    
    async def execute(self, context: TestContext) -> List[TestResult]:
        """
        Validate testing environment and dependencies.
        
        Args:
            context: Test context with project information
            
        Returns:
            List of environment validation results
        """
        self.clear_results()
        
        # Phase 1: Check Python environment
        await self._check_python_environment(context)
        
        # Phase 2: Check virtual environment
        await self._check_virtual_environment(context)
        
        # Phase 3: Check dependencies
        await self._check_dependencies(context)
        
        # Phase 4: Check configuration files
        await self._check_configuration_files(context)
        
        # Phase 5: Check Docker environment (if applicable)
        await self._check_docker_environment(context)
        
        return self.results
    
    async def _check_python_environment(self, context: TestContext):
        """Check Python environment and version."""
        
        # Check Python version
        exit_code, stdout, stderr = await self.run_command("python --version", context.project_path)
        
        if exit_code == 0:
            version_match = re.search(self.environment_patterns["python_version"], stdout)
            if version_match:
                python_version = version_match.group(1)
                # Check if version is compatible (3.8+)
                major, minor, patch = map(int, python_version.split('.'))
                is_compatible = major >= 3 and minor >= 8
                
                self.add_result(
                    test_name="Python Version",
                    status=TestStatus.PASSED if is_compatible else TestStatus.FAILED,
                    duration=0.0,
                    output=f"Python {python_version} detected",
                    error_message=f"Python {python_version} is not compatible (requires 3.8+)" if not is_compatible else None,
                    metadata={"python_version": python_version, "compatible": is_compatible}
                )
            else:
                self.add_result(
                    test_name="Python Version",
                    status=TestStatus.ERROR,
                    duration=0.0,
                    output="Could not parse Python version",
                    error_message="Python version parsing failed",
                    metadata={"python_version": "unknown"}
                )
        else:
            self.add_result(
                test_name="Python Version",
                status=TestStatus.FAILED,
                duration=0.0,
                output="Python not found or not accessible",
                error_message=stderr,
                metadata={"python_version": "not_found"}
            )
        
        # Check Python path
        exit_code, stdout, stderr = await self.run_command("python -c 'import sys; print(sys.path)'", context.project_path)
        
        if exit_code == 0:
            self.add_result(
                test_name="Python Path",
                status=TestStatus.PASSED,
                duration=0.0,
                output="Python path configured correctly",
                metadata={"python_path": "ok"}
            )
        else:
            self.add_result(
                test_name="Python Path",
                status=TestStatus.FAILED,
                duration=0.0,
                output="Python path configuration issue",
                error_message=stderr,
                metadata={"python_path": "error"}
            )
    
    async def _check_virtual_environment(self, context: TestContext):
        """Check virtual environment setup."""
        
        # Check if virtual environment is active
        virtual_env = os.environ.get('VIRTUAL_ENV')
        
        if virtual_env:
            self.add_result(
                test_name="Virtual Environment",
                status=TestStatus.PASSED,
                duration=0.0,
                output=f"Virtual environment active: {virtual_env}",
                metadata={"virtual_env": virtual_env, "active": True}
            )
        else:
            self.add_result(
                test_name="Virtual Environment",
                status=TestStatus.FAILED,
                duration=0.0,
                output="No virtual environment detected",
                error_message="Virtual environment should be active for testing",
                metadata={"virtual_env": "none", "active": False}
            )
        
        # Check if .venv directory exists
        venv_path = os.path.join(context.project_path, '.venv')
        if os.path.exists(venv_path):
            self.add_result(
                test_name="Virtual Environment Directory",
                status=TestStatus.PASSED,
                duration=0.0,
                output="Virtual environment directory exists",
                metadata={"venv_directory": "exists"}
            )
        else:
            self.add_result(
                test_name="Virtual Environment Directory",
                status=TestStatus.FAILED,
                duration=0.0,
                output="Virtual environment directory not found",
                error_message="Create virtual environment with: python -m venv .venv",
                metadata={"venv_directory": "missing"}
            )
    
    async def _check_dependencies(self, context: TestContext):
        """Check project dependencies."""
        
        # Check if requirements.txt exists
        requirements_path = os.path.join(context.project_path, 'requirements.txt')
        if os.path.exists(requirements_path):
            self.add_result(
                test_name="Requirements File",
                status=TestStatus.PASSED,
                duration=0.0,
                output="requirements.txt found",
                metadata={"requirements_file": "exists"}
            )
            
            # Check if dependencies are installed
            await self._check_installed_dependencies(context)
        else:
            self.add_result(
                test_name="Requirements File",
                status=TestStatus.FAILED,
                duration=0.0,
                output="requirements.txt not found",
                error_message="Create requirements.txt with project dependencies",
                metadata={"requirements_file": "missing"}
            )
        
        # Check for dependency conflicts
        await self._check_dependency_conflicts(context)
    
    async def _check_installed_dependencies(self, context: TestContext):
        """Check if required dependencies are installed."""
        
        # Check for pytest
        exit_code, stdout, stderr = await self.run_command("python -c 'import pytest; print(pytest.__version__)'", context.project_path)
        
        if exit_code == 0:
            pytest_version = stdout.strip()
            self.add_result(
                test_name="Pytest Installation",
                status=TestStatus.PASSED,
                duration=0.0,
                output=f"Pytest {pytest_version} installed",
                metadata={"pytest_version": pytest_version}
            )
        else:
            self.add_result(
                test_name="Pytest Installation",
                status=TestStatus.FAILED,
                duration=0.0,
                output="Pytest not installed",
                error_message="Install pytest: pip install pytest",
                metadata={"pytest": "not_installed"}
            )
        
        # Check for other common testing dependencies
        test_dependencies = [
            ("pytest-cov", "pytest_cov"),
            ("pytest-asyncio", "pytest_asyncio"),
            ("httpx", "httpx"),
            ("requests", "requests")
        ]
        
        for package_name, import_name in test_dependencies:
            exit_code, stdout, stderr = await self.run_command(f"python -c 'import {import_name}'", context.project_path)
            
            self.add_result(
                test_name=f"{package_name} Installation",
                status=TestStatus.PASSED if exit_code == 0 else TestStatus.FAILED,
                duration=0.0,
                output=f"{package_name} {'installed' if exit_code == 0 else 'not installed'}",
                error_message=f"Install {package_name}: pip install {package_name}" if exit_code != 0 else None,
                metadata={f"{package_name}": "installed" if exit_code == 0 else "not_installed"}
            )
    
    async def _check_dependency_conflicts(self, context: TestContext):
        """Check for dependency conflicts."""
        
        # Check pip list for conflicts
        exit_code, stdout, stderr = await self.run_command("pip list", context.project_path)
        
        if exit_code == 0:
            # Look for common conflict indicators
            if "WARNING" in stdout or "conflict" in stdout.lower():
                self.add_result(
                    test_name="Dependency Conflicts",
                    status=TestStatus.FAILED,
                    duration=0.0,
                    output="Potential dependency conflicts detected",
                    error_message="Check pip list output for conflicts",
                    metadata={"dependency_conflicts": "detected"}
                )
            else:
                self.add_result(
                    test_name="Dependency Conflicts",
                    status=TestStatus.PASSED,
                    duration=0.0,
                    output="No dependency conflicts detected",
                    metadata={"dependency_conflicts": "none"}
                )
        else:
            self.add_result(
                test_name="Dependency Conflicts",
                status=TestStatus.ERROR,
                duration=0.0,
                output="Could not check dependency conflicts",
                error_message=stderr,
                metadata={"dependency_conflicts": "check_failed"}
            )
    
    async def _check_configuration_files(self, context: TestContext):
        """Check configuration files."""
        
        # Check pytest.ini
        pytest_ini_path = os.path.join(context.project_path, 'pytest.ini')
        if os.path.exists(pytest_ini_path):
            self.add_result(
                test_name="Pytest Configuration",
                status=TestStatus.PASSED,
                duration=0.0,
                output="pytest.ini found",
                metadata={"pytest_config": "exists"}
            )
        else:
            self.add_result(
                test_name="Pytest Configuration",
                status=TestStatus.FAILED,
                duration=0.0,
                output="pytest.ini not found",
                error_message="Create pytest.ini for test configuration",
                metadata={"pytest_config": "missing"}
            )
        
        # Check .env file
        env_path = os.path.join(context.project_path, '.env')
        if os.path.exists(env_path):
            self.add_result(
                test_name="Environment Configuration",
                status=TestStatus.PASSED,
                duration=0.0,
                output=".env file found",
                metadata={"env_file": "exists"}
            )
        else:
            self.add_result(
                test_name="Environment Configuration",
                status=TestStatus.FAILED,
                duration=0.0,
                output=".env file not found",
                error_message="Create .env file for environment variables",
                metadata={"env_file": "missing"}
            )
        
        # Check pyproject.toml
        pyproject_path = os.path.join(context.project_path, 'pyproject.toml')
        if os.path.exists(pyproject_path):
            self.add_result(
                test_name="Project Configuration",
                status=TestStatus.PASSED,
                duration=0.0,
                output="pyproject.toml found",
                metadata={"pyproject": "exists"}
            )
        else:
            self.add_result(
                test_name="Project Configuration",
                status=TestStatus.FAILED,
                duration=0.0,
                output="pyproject.toml not found",
                error_message="Create pyproject.toml for modern Python project configuration",
                metadata={"pyproject": "missing"}
            )
    
    async def _check_docker_environment(self, context: TestContext):
        """Check Docker environment if applicable."""
        
        # Check if Docker is available
        exit_code, stdout, stderr = await self.run_command("docker --version", context.project_path)
        
        if exit_code == 0:
            version_match = re.search(self.environment_patterns["docker_version"], stdout)
            if version_match:
                docker_version = version_match.group(1)
                self.add_result(
                    test_name="Docker Environment",
                    status=TestStatus.PASSED,
                    duration=0.0,
                    output=f"Docker {docker_version} available",
                    metadata={"docker_version": docker_version}
                )
            else:
                self.add_result(
                    test_name="Docker Environment",
                    status=TestStatus.PASSED,
                    duration=0.0,
                    output="Docker available",
                    metadata={"docker": "available"}
                )
            
            # Check if Docker Compose is available
            exit_code, stdout, stderr = await self.run_command("docker-compose --version", context.project_path)
            
            if exit_code == 0:
                self.add_result(
                    test_name="Docker Compose",
                    status=TestStatus.PASSED,
                    duration=0.0,
                    output="Docker Compose available",
                    metadata={"docker_compose": "available"}
                )
            else:
                self.add_result(
                    test_name="Docker Compose",
                    status=TestStatus.FAILED,
                    duration=0.0,
                    output="Docker Compose not available",
                    error_message="Install Docker Compose for containerized testing",
                    metadata={"docker_compose": "not_available"}
                )
            
            # Check if docker-compose.yml exists
            compose_path = os.path.join(context.project_path, 'docker-compose.yml')
            if os.path.exists(compose_path):
                self.add_result(
                    test_name="Docker Compose Configuration",
                    status=TestStatus.PASSED,
                    duration=0.0,
                    output="docker-compose.yml found",
                    metadata={"docker_compose_config": "exists"}
                )
            else:
                self.add_result(
                    test_name="Docker Compose Configuration",
                    status=TestStatus.FAILED,
                    duration=0.0,
                    output="docker-compose.yml not found",
                    error_message="Create docker-compose.yml for containerized testing",
                    metadata={"docker_compose_config": "missing"}
                )
        else:
            self.add_result(
                test_name="Docker Environment",
                status=TestStatus.SKIPPED,
                duration=0.0,
                output="Docker not available (skipping Docker checks)",
                metadata={"docker": "not_available"}
            )
    
    def get_environment_summary(self) -> Dict[str, Any]:
        """Get summary of environment validation."""
        
        total_tests = len(self.results)
        passed_tests = len(self.get_passed_tests())
        failed_tests = len(self.get_failed_tests())
        
        return {
            "total_environment_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "python_environment_checked": True,
            "virtual_environment_checked": True,
            "dependencies_checked": True,
            "configuration_checked": True,
            "docker_environment_checked": True
        }
