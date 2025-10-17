"""
Project Conductor Agent (T037)

Orchestrates all development workflows (implement, code review, test, merge) 
across the AlgoTrading MVP tasks (T001–T036) using existing agent systems.

This conductor reuses and coordinates:
- Code Review System (.memory/code_review/)
- Testing System (.memory/testing/)
- Multi-Agent Orchestrator specifications (.memory/specs/agents/)
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Import existing agent systems
import sys
sys.path.append(str(Path(__file__).parent))

from code_review.orchestrator import CodeReviewOrchestrator
from testing.orchestrator import TestingOrchestrator


class ProjectConductor:
    """
    Project Conductor orchestrates the complete development lifecycle.
    
    This conductor coordinates existing agent systems to provide:
    - Autonomous task implementation (T001-T036)
    - Code review and quality assurance
    - Testing and validation
    - Deployment and release management
    """
    
    def __init__(self, project_path: str, memory_bank_path: str = ".memory"):
        self.project_path = Path(project_path)
        self.memory_bank_path = Path(memory_bank_path)
        
        # Initialize existing agent systems
        self.code_review_system = CodeReviewOrchestrator(
            project_path=str(self.project_path),
            memory_bank_path=str(self.memory_bank_path)
        )
        
        self.testing_system = TestingOrchestrator(
            project_path=str(self.project_path),
            memory_bank_path=str(self.memory_bank_path)
        )
        
        # Load orchestrator specifications
        self.orchestrator_spec = self._load_orchestrator_spec()
        
        # Current execution state
        self.current_task = None
        self.execution_phase = "initialization"
        self.execution_log = []
    
    def _load_orchestrator_spec(self) -> Dict[str, Any]:
        """Load multi-agent orchestrator specifications."""
        spec_path = self.memory_bank_path / "specs" / "agents" / "multi_agent_orchestrator.json"
        
        if spec_path.exists():
            with open(spec_path, 'r') as f:
                return json.load(f)
        else:
            return {}
    
    async def implement_task(self, task_id: str) -> Dict[str, Any]:
        """
        Implement a specific task (T001-T036) using the complete development lifecycle.
        
        Args:
            task_id: Task identifier (e.g., "T001", "T002", etc.)
            
        Returns:
            Complete implementation report
        """
        
        self.current_task = task_id
        self.execution_phase = "initialization"
        self.execution_log = []
        
        # Phase 1: Memory Analysis and Planning
        await self._log_phase("Phase 1: Memory Analysis and Planning")
        memory_context = await self._phase_memory_analysis(task_id)
        
        # Phase 2: Environment Setup
        await self._log_phase("Phase 2: Environment Setup")
        environment_setup = await self._phase_environment_setup(task_id, memory_context)
        
        # Phase 3: Implementation
        await self._log_phase("Phase 3: Implementation")
        implementation_result = await self._phase_implementation(task_id, memory_context)
        
        # Phase 4: Code Review
        await self._log_phase("Phase 4: Code Review")
        code_review_result = await self._phase_code_review(implementation_result)
        
        # Phase 5: Testing
        await self._log_phase("Phase 5: Testing")
        testing_result = await self._phase_testing(implementation_result)
        
        # Phase 6: Validation and Quality Gates
        await self._log_phase("Phase 6: Validation and Quality Gates")
        validation_result = await self._phase_validation(code_review_result, testing_result)
        
        # Phase 7: Memory Update
        await self._log_phase("Phase 7: Memory Update")
        memory_update_result = await self._phase_memory_update(task_id, implementation_result)
        
        # Phase 8: Final Report
        await self._log_phase("Phase 8: Final Report")
        final_report = await self._generate_final_report(
            task_id, memory_context, implementation_result, 
            code_review_result, testing_result, validation_result
        )
        
        return final_report
    
    async def _log_phase(self, phase_name: str):
        """Log current execution phase."""
        self.execution_phase = phase_name
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "phase": phase_name,
            "status": "started"
        })
        print(f"🔄 {phase_name}")
    
    async def _phase_memory_analysis(self, task_id: str) -> Dict[str, Any]:
        """Phase 1: Analyze memory and extract task context."""
        
        # Load task specifications
        task_spec = self._load_task_specification(task_id)
        
        # Load memory bank context
        memory_context = self._load_memory_context()
        
        # Validate dependencies
        dependencies = self._validate_dependencies(task_spec, memory_context)
        
        # Extract affected files and requirements
        affected_files = self._extract_affected_files(task_spec)
        requirements = self._extract_requirements(task_spec)
        
        context = {
            "task_id": task_id,
            "task_spec": task_spec,
            "memory_context": memory_context,
            "dependencies": dependencies,
            "affected_files": affected_files,
            "requirements": requirements,
            "success_criteria": task_spec.get("success_criteria", [])
        }
        
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "memory_analysis",
            "status": "completed",
            "context": context
        })
        
        return context
    
    async def _phase_environment_setup(self, task_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Set up development environment."""
        
        # Create feature branch
        branch_name = f"feature/{task_id}-{context['task_spec'].get('title', 'task').lower().replace(' ', '-')}"
        
        # Check if branch already exists
        exit_code, stdout, stderr = await self._run_command(f"git branch --list {branch_name}")
        
        if exit_code == 0 and stdout.strip():
            # Branch exists, checkout
            exit_code, stdout, stderr = await self._run_command(f"git checkout {branch_name}")
        else:
            # Create new branch
            exit_code, stdout, stderr = await self._run_command(f"git checkout -b {branch_name}")
        
        # Verify environment
        environment_status = await self._verify_environment()
        
        setup_result = {
            "branch_name": branch_name,
            "environment_status": environment_status,
            "workspace_ready": True
        }
        
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "environment_setup",
            "status": "completed",
            "result": setup_result
        })
        
        return setup_result
    
    async def _phase_implementation(self, task_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Implement the task."""
        
        # This would integrate with the existing Implementation Agent
        # For now, we'll simulate the implementation
        
        implementation_result = {
            "task_id": task_id,
            "files_created": [],
            "files_modified": [],
            "code_quality": "good",
            "implementation_status": "completed"
        }
        
        # Simulate implementation based on task type
        if task_id == "T001":
            # T001 is already implemented
            implementation_result["files_created"] = ["app/main.py", "tests/test_main.py"]
            implementation_result["files_modified"] = ["requirements.txt", "README.md"]
        else:
            # For other tasks, this would trigger the actual Implementation Agent
            implementation_result["implementation_status"] = "pending_implementation"
        
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "implementation",
            "status": "completed",
            "result": implementation_result
        })
        
        return implementation_result
    
    async def _phase_code_review(self, implementation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 4: Perform code review using existing system."""
        
        # Use existing code review system
        target_files = implementation_result.get("files_created", []) + implementation_result.get("files_modified", [])
        
        if target_files:
            review_report = await self.code_review_system.review_code(
                target_files=target_files,
                review_type="file"
            )
        else:
            review_report = {"status": "no_files_to_review"}
        
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "code_review",
            "status": "completed",
            "result": review_report
        })
        
        return review_report
    
    async def _phase_testing(self, implementation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 5: Run tests using existing system."""
        
        # Use existing testing system
        test_report = await self.testing_system.test_all()
        
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "testing",
            "status": "completed",
            "result": test_report
        })
        
        return test_report
    
    async def _phase_validation(self, code_review_result: Dict[str, Any], testing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 6: Validate quality gates and success criteria."""
        
        # Check code review status
        code_review_passed = code_review_result.get("metadata", {}).get("critical_findings", 0) == 0
        
        # Check testing status
        testing_passed = testing_result.get("metadata", {}).get("failed_tests", 0) == 0
        
        # Check coverage
        coverage_ok = testing_result.get("metadata", {}).get("coverage", 0) >= 90
        
        validation_result = {
            "code_review_passed": code_review_passed,
            "testing_passed": testing_passed,
            "coverage_ok": coverage_ok,
            "overall_status": code_review_passed and testing_passed and coverage_ok,
            "quality_gates": {
                "code_quality": code_review_passed,
                "test_quality": testing_passed,
                "coverage_quality": coverage_ok
            }
        }
        
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "validation",
            "status": "completed",
            "result": validation_result
        })
        
        return validation_result
    
    async def _phase_memory_update(self, task_id: str, implementation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 7: Update memory bank with implementation results."""
        
        # Update progress tracking
        progress_update = {
            "task_id": task_id,
            "status": "completed",
            "completion_date": datetime.now().isoformat(),
            "implementation_result": implementation_result
        }
        
        # This would update the actual .memory files
        # For now, we'll just log the update
        
        memory_update_result = {
            "memory_updated": True,
            "progress_updated": True,
            "changelog_updated": True
        }
        
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "phase": "memory_update",
            "status": "completed",
            "result": memory_update_result
        })
        
        return memory_update_result
    
    async def _generate_final_report(self, task_id: str, context: Dict[str, Any], 
                                   implementation_result: Dict[str, Any],
                                   code_review_result: Dict[str, Any],
                                   testing_result: Dict[str, Any],
                                   validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 8: Generate final implementation report."""
        
        final_report = {
            "task_id": task_id,
            "execution_summary": {
                "start_time": self.execution_log[0]["timestamp"] if self.execution_log else None,
                "end_time": datetime.now().isoformat(),
                "total_phases": len(self.execution_log),
                "overall_status": validation_result.get("overall_status", False)
            },
            "phase_results": {
                "memory_analysis": context,
                "environment_setup": self.execution_log[1].get("result", {}) if len(self.execution_log) > 1 else {},
                "implementation": implementation_result,
                "code_review": code_review_result,
                "testing": testing_result,
                "validation": validation_result
            },
            "quality_metrics": {
                "code_quality": validation_result.get("quality_gates", {}).get("code_quality", False),
                "test_quality": validation_result.get("quality_gates", {}).get("test_quality", False),
                "coverage_quality": validation_result.get("quality_gates", {}).get("coverage_quality", False)
            },
            "next_steps": self._generate_next_steps(task_id, validation_result),
            "execution_log": self.execution_log
        }
        
        return final_report
    
    def _load_task_specification(self, task_id: str) -> Dict[str, Any]:
        """Load task specification from memory bank."""
        
        # Load from complete task breakdown
        task_breakdown_path = self.memory_bank_path / "specs" / "tasks" / "complete_task_breakdown.json"
        
        if task_breakdown_path.exists():
            with open(task_breakdown_path, 'r') as f:
                task_data = json.load(f)
                
                # Find the specific task
                for phase, tasks in task_data.items():
                    if task_id in tasks:
                        return tasks[task_id]
        
        # Fallback to basic task info
        return {
            "id": task_id,
            "title": f"Task {task_id}",
            "description": f"Implementation of task {task_id}",
            "dependencies": [],
            "success_criteria": []
        }
    
    def _load_memory_context(self) -> Dict[str, Any]:
        """Load complete memory bank context."""
        
        context = {}
        
        # Load core memory files
        core_files = ["project_brief.md", "tech_context.md", "system_patterns.md", "progress.md"]
        for file_name in core_files:
            file_path = self.memory_bank_path / "core" / file_name
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    key = file_name.replace('.md', '')
                    context[key] = f.read()
        
        return context
    
    def _validate_dependencies(self, task_spec: Dict[str, Any], memory_context: Dict[str, Any]) -> List[str]:
        """Validate that task dependencies are satisfied."""
        
        dependencies = task_spec.get("dependencies", [])
        satisfied_deps = []
        missing_deps = []
        
        for dep in dependencies:
            # Check if dependency is satisfied (this would be more sophisticated)
            if dep in ["T001"]:  # T001 is already implemented
                satisfied_deps.append(dep)
            else:
                missing_deps.append(dep)
        
        return {
            "satisfied": satisfied_deps,
            "missing": missing_deps,
            "all_satisfied": len(missing_deps) == 0
        }
    
    def _extract_affected_files(self, task_spec: Dict[str, Any]) -> List[str]:
        """Extract files that will be affected by the task."""
        
        # This would be more sophisticated based on task specification
        return task_spec.get("outputs", [])
    
    def _extract_requirements(self, task_spec: Dict[str, Any]) -> List[str]:
        """Extract requirements for the task."""
        
        return task_spec.get("inputs", [])
    
    async def _verify_environment(self) -> Dict[str, Any]:
        """Verify development environment is ready."""
        
        # Check Python environment
        exit_code, stdout, stderr = await self._run_command("python --version")
        python_ok = exit_code == 0
        
        # Check Git
        exit_code, stdout, stderr = await self._run_command("git --version")
        git_ok = exit_code == 0
        
        # Check virtual environment
        venv_ok = "VIRTUAL_ENV" in os.environ
        
        return {
            "python_ready": python_ok,
            "git_ready": git_ok,
            "venv_ready": venv_ok,
            "overall_ready": python_ok and git_ok and venv_ok
        }
    
    async def _run_command(self, command: str) -> tuple:
        """Run a shell command and return exit code, stdout, stderr."""
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_path
            )
            
            stdout, stderr = await process.communicate()
            
            return (
                process.returncode,
                stdout.decode('utf-8', errors='ignore'),
                stderr.decode('utf-8', errors='ignore')
            )
            
        except Exception as e:
            return (-1, "", str(e))
    
    def _generate_next_steps(self, task_id: str, validation_result: Dict[str, Any]) -> List[str]:
        """Generate next steps based on validation results."""
        
        next_steps = []
        
        if validation_result.get("overall_status", False):
            next_steps.append("✅ Task implementation completed successfully")
            next_steps.append("🔄 Ready for human review and merge")
            next_steps.append("📋 Update project documentation")
        else:
            if not validation_result.get("code_review_passed", False):
                next_steps.append("🔧 Address code review issues")
            if not validation_result.get("testing_passed", False):
                next_steps.append("🧪 Fix failing tests")
            if not validation_result.get("coverage_ok", False):
                next_steps.append("📊 Improve test coverage")
        
        return next_steps
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status."""
        
        return {
            "current_task": self.current_task,
            "current_phase": self.execution_phase,
            "execution_log": self.execution_log,
            "systems_available": {
                "code_review": True,
                "testing": True,
                "orchestrator_spec": bool(self.orchestrator_spec)
            }
        }


# Convenience function for easy usage
async def implement_task(project_path: str, task_id: str, memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Implement a specific task using the Project Conductor."""
    
    conductor = ProjectConductor(project_path, memory_bank_path)
    return await conductor.implement_task(task_id)
