"""
CI/CD & Environment Verifier Agent

Analyzes code for CI/CD compatibility and environment configuration issues.
Focuses on deployment readiness and pipeline compatibility.
"""

import re
import os
from typing import Dict, List, Any
from .base_agent import BaseReviewAgent, ReviewContext, ReviewFinding, Severity


class CICDVerifier(BaseReviewAgent):
    """
    CI/CD & Environment Verifier ensures deployment readiness.
    
    This agent checks for:
    - CI/CD pipeline compatibility
    - Environment configuration issues
    - Docker and containerization readiness
    - Dependency management
    - Build and deployment scripts
    """
    
    def __init__(self):
        super().__init__(
            name="⚙️ CI/CD & Environment Verifier",
            description="Validates CI/CD compatibility and environment configuration"
        )
        
        # CI/CD patterns to check
        self.cicd_patterns = {
            "github_actions": [
                r"\.github/workflows/",
                r"uses:\s*actions/",
                r"on:\s*\[.*push.*\]"
            ],
            "docker": [
                r"FROM\s+\w+",
                r"COPY\s+.*\s+.*",
                r"RUN\s+.*",
                r"EXPOSE\s+\d+"
            ],
            "environment_vars": [
                r"os\.environ\s*\[",
                r"getenv\s*\(",
                r"environ\.get\s*\("
            ],
            "dependency_management": [
                r"requirements\.txt",
                r"pyproject\.toml",
                r"setup\.py",
                r"Pipfile"
            ]
        }
        
        # Environment configuration issues
        self.env_issues = {
            "hardcoded_paths": [
                r"/home/\w+/",
                r"C:\\Users\\",
                r"/usr/local/",
                r"~/"
            ],
            "hardcoded_ports": [
                r"port\s*=\s*8000",
                r"PORT\s*=\s*8000",
                r":8000"
            ],
            "hardcoded_hosts": [
                r"localhost",
                r"127\.0\.0\.1",
                r"0\.0\.0\.0"
            ]
        }
    
    async def analyze(self, code_content: str, context: ReviewContext) -> List[ReviewFinding]:
        """Analyze code for CI/CD and environment compatibility."""
        self.clear_findings()
        
        # Check CI/CD pipeline compatibility
        await self._analyze_cicd_compatibility(code_content, context)
        
        # Check environment configuration
        await self._analyze_environment_config(code_content, context)
        
        # Check Docker readiness
        await self._analyze_docker_readiness(code_content, context)
        
        # Check dependency management
        await self._analyze_dependency_management(code_content, context)
        
        # Check build and deployment scripts
        await self._analyze_build_scripts(code_content, context)
        
        return self.findings
    
    async def _analyze_cicd_compatibility(self, code_content: str, context: ReviewContext):
        """Check CI/CD pipeline compatibility."""
        
        # Check for GitHub Actions
        has_github_actions = any(
            os.path.exists(os.path.join(context.project_path, ".github", "workflows", f))
            for f in os.listdir(os.path.join(context.project_path, ".github", "workflows"))
            if f.endswith('.yml') or f.endswith('.yaml')
        ) if os.path.exists(os.path.join(context.project_path, ".github", "workflows")) else False
        
        if not has_github_actions:
            self.add_finding(
                category="CI/CD",
                summary="No GitHub Actions workflow found",
                severity=Severity.MEDIUM,
                recommendation="Create GitHub Actions workflow for automated testing and deployment"
            )
        
        # Check for test commands in CI
        if has_github_actions:
            workflow_files = []
            workflows_dir = os.path.join(context.project_path, ".github", "workflows")
            if os.path.exists(workflows_dir):
                for f in os.listdir(workflows_dir):
                    if f.endswith(('.yml', '.yaml')):
                        workflow_files.append(os.path.join(workflows_dir, f))
            
            has_test_command = False
            for workflow_file in workflow_files:
                try:
                    with open(workflow_file, 'r') as f:
                        workflow_content = f.read()
                        if 'pytest' in workflow_content or 'test' in workflow_content.lower():
                            has_test_command = True
                            break
                except:
                    continue
            
            if not has_test_command:
                self.add_finding(
                    category="CI/CD",
                    summary="No test commands found in CI workflow",
                    severity=Severity.HIGH,
                    recommendation="Add test execution commands to CI pipeline"
                )
        
        # Check for build commands
        if has_github_actions:
            has_build_command = False
            for workflow_file in workflow_files:
                try:
                    with open(workflow_file, 'r') as f:
                        workflow_content = f.read()
                        if any(cmd in workflow_content.lower() for cmd in ['build', 'install', 'pip install']):
                            has_build_command = True
                            break
                except:
                    continue
            
            if not has_build_command:
                self.add_finding(
                    category="CI/CD",
                    summary="No build commands found in CI workflow",
                    severity=Severity.MEDIUM,
                    recommendation="Add dependency installation and build commands to CI pipeline"
                )
    
    async def _analyze_environment_config(self, code_content: str, context: ReviewContext):
        """Check environment configuration issues."""
        
        # Check for hardcoded paths
        for pattern in self.env_issues["hardcoded_paths"]:
            if re.search(pattern, code_content):
                self.add_finding(
                    category="Environment",
                    summary="Hardcoded file paths detected",
                    severity=Severity.MEDIUM,
                    recommendation="Use environment variables or configuration files for file paths"
                )
                break
        
        # Check for hardcoded ports
        for pattern in self.env_issues["hardcoded_ports"]:
            if re.search(pattern, code_content):
                self.add_finding(
                    category="Environment",
                    summary="Hardcoded port numbers detected",
                    severity=Severity.LOW,
                    recommendation="Use environment variables for port configuration"
                )
                break
        
        # Check for hardcoded hosts
        for pattern in self.env_issues["hardcoded_hosts"]:
            if re.search(pattern, code_content):
                self.add_finding(
                    category="Environment",
                    summary="Hardcoded host addresses detected",
                    severity=Severity.LOW,
                    recommendation="Use environment variables for host configuration"
                )
                break
        
        # Check for environment variable usage
        env_var_patterns = [
            r"os\.environ\s*\[",
            r"getenv\s*\(",
            r"environ\.get\s*\("
        ]
        
        has_env_vars = any(re.search(pattern, code_content) for pattern in env_var_patterns)
        
        if not has_env_vars and ("config" in code_content.lower() or "settings" in code_content.lower()):
            self.add_finding(
                category="Environment",
                summary="Configuration without environment variable support",
                severity=Severity.MEDIUM,
                recommendation="Add environment variable support for configuration"
            )
        
        # Check for .env file usage
        if "python-dotenv" in code_content or "load_dotenv" in code_content:
            self.add_finding(
                category="Environment",
                summary="Environment file loading detected - good practice",
                severity=Severity.LOW,
                recommendation="Ensure .env files are properly configured for different environments"
            )
    
    async def _analyze_docker_readiness(self, code_content: str, context: ReviewContext):
        """Check Docker and containerization readiness."""
        
        # Check for Dockerfile
        dockerfile_path = os.path.join(context.project_path, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            self.add_finding(
                category="Docker",
                summary="No Dockerfile found",
                severity=Severity.MEDIUM,
                recommendation="Create Dockerfile for containerization"
            )
        else:
            # Analyze Dockerfile content
            try:
                with open(dockerfile_path, 'r') as f:
                    dockerfile_content = f.read()
                    
                    # Check for multi-stage build
                    if "FROM" in dockerfile_content:
                        from_count = dockerfile_content.count("FROM")
                        if from_count == 1:
                            self.add_finding(
                                category="Docker",
                                summary="Single-stage Docker build detected",
                                severity=Severity.LOW,
                                recommendation="Consider multi-stage build for smaller production images"
                            )
                    
                    # Check for .dockerignore
                    dockerignore_path = os.path.join(context.project_path, ".dockerignore")
                    if not os.path.exists(dockerignore_path):
                        self.add_finding(
                            category="Docker",
                            summary="No .dockerignore file found",
                            severity=Severity.LOW,
                            recommendation="Create .dockerignore to exclude unnecessary files from Docker context"
                        )
                    
                    # Check for security best practices
                    if "USER root" in dockerfile_content or "RUN chmod 777" in dockerfile_content:
                        self.add_finding(
                            category="Docker",
                            summary="Potential security issues in Dockerfile",
                            severity=Severity.MEDIUM,
                            recommendation="Avoid running as root and use proper file permissions"
                        )
                        
            except Exception as e:
                self.add_finding(
                    category="Docker",
                    summary=f"Error reading Dockerfile: {str(e)}",
                    severity=Severity.LOW,
                    recommendation="Ensure Dockerfile is readable and properly formatted"
                )
        
        # Check for docker-compose
        compose_files = ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]
        has_compose = any(os.path.exists(os.path.join(context.project_path, f)) for f in compose_files)
        
        if not has_compose:
            self.add_finding(
                category="Docker",
                summary="No docker-compose file found",
                severity=Severity.LOW,
                recommendation="Create docker-compose.yml for local development environment"
            )
    
    async def _analyze_dependency_management(self, code_content: str, context: ReviewContext):
        """Check dependency management and requirements."""
        
        # Check for requirements.txt
        requirements_path = os.path.join(context.project_path, "requirements.txt")
        if not os.path.exists(requirements_path):
            self.add_finding(
                category="Dependencies",
                summary="No requirements.txt file found",
                severity=Severity.HIGH,
                recommendation="Create requirements.txt with project dependencies"
            )
        else:
            # Analyze requirements.txt
            try:
                with open(requirements_path, 'r') as f:
                    requirements_content = f.read()
                    
                    # Check for version pinning
                    unpinned_deps = []
                    for line in requirements_content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#') and '==' not in line and '~=' not in line:
                            unpinned_deps.append(line.split('>=')[0].split('>')[0])
                    
                    if unpinned_deps:
                        self.add_finding(
                            category="Dependencies",
                            summary=f"Unpinned dependencies: {', '.join(unpinned_deps)}",
                            severity=Severity.MEDIUM,
                            recommendation="Pin dependency versions for reproducible builds"
                        )
                    
                    # Check for development dependencies
                    if "pytest" not in requirements_content and "test" in code_content.lower():
                        self.add_finding(
                            category="Dependencies",
                            summary="Testing dependencies missing from requirements.txt",
                            severity=Severity.MEDIUM,
                            recommendation="Add testing dependencies to requirements.txt or requirements-dev.txt"
                        )
                        
            except Exception as e:
                self.add_finding(
                    category="Dependencies",
                    summary=f"Error reading requirements.txt: {str(e)}",
                    severity=Severity.LOW,
                    recommendation="Ensure requirements.txt is properly formatted"
                )
        
        # Check for pyproject.toml (modern Python packaging)
        pyproject_path = os.path.join(context.project_path, "pyproject.toml")
        if not os.path.exists(pyproject_path):
            self.add_finding(
                category="Dependencies",
                summary="No pyproject.toml found - consider modern Python packaging",
                severity=Severity.LOW,
                recommendation="Consider using pyproject.toml for modern Python project configuration"
            )
    
    async def _analyze_build_scripts(self, code_content: str, context: ReviewContext):
        """Check build and deployment scripts."""
        
        # Check for build scripts
        build_scripts = ["build.sh", "build.py", "setup.py", "Makefile"]
        has_build_script = any(os.path.exists(os.path.join(context.project_path, script)) for script in build_scripts)
        
        if not has_build_script:
            self.add_finding(
                category="Build",
                summary="No build scripts found",
                severity=Severity.LOW,
                recommendation="Create build scripts for automated deployment"
            )
        
        # Check for deployment scripts
        deploy_scripts = ["deploy.sh", "deploy.py", "deploy.yml"]
        has_deploy_script = any(os.path.exists(os.path.join(context.project_path, script)) for script in deploy_scripts)
        
        if not has_deploy_script:
            self.add_finding(
                category="Deployment",
                summary="No deployment scripts found",
                severity=Severity.LOW,
                recommendation="Create deployment scripts for consistent deployments"
            )
        
        # Check for health check endpoints (important for deployment)
        if "health" in code_content.lower() or "/health" in code_content:
            self.add_finding(
                category="Deployment",
                summary="Health check endpoint detected - good for deployment",
                severity=Severity.LOW,
                recommendation="Ensure health check endpoint is properly configured for load balancers"
            )
        
        # Check for logging configuration
        if "logging" in code_content.lower() or "logger" in code_content.lower():
            self.add_finding(
                category="Deployment",
                summary="Logging configuration detected - good for production",
                severity=Severity.LOW,
                recommendation="Ensure logging is properly configured for production environments"
            )
        
        # Check for graceful shutdown handling
        if "signal" in code_content.lower() or "shutdown" in code_content.lower():
            self.add_finding(
                category="Deployment",
                summary="Graceful shutdown handling detected - good for production",
                severity=Severity.LOW,
                recommendation="Ensure graceful shutdown is properly implemented for containerized deployments"
            )
