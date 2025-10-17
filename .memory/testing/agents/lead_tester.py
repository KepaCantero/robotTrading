"""
Lead Tester Agent

Coordinates the testing process by:
1. Loading project context from memory bank
2. Determining test scope and strategy
3. Coordinating all specialized testing agents
4. Managing the overall testing workflow
"""

import asyncio
from typing import Dict, List, Any, Optional
from .base_test_agent import BaseTestAgent, TestContext, TestResult, TestStatus
from .test_executor import TestExecutor
from .failure_diagnostician import FailureDiagnostician
from .auto_fixer_agent import AutoFixerAgent
from .integration_verifier import IntegrationVerifier
from .qa_quality_guardian import QAQualityGuardian
from .environment_auditor import EnvironmentAuditor


class LeadTester(BaseTestAgent):
    """
    Lead Tester coordinates the entire testing process.
    
    This agent acts as the orchestrator, determining test scope,
    delegating tasks to specialized agents, and managing the workflow.
    """
    
    def __init__(self):
        super().__init__(
            name="🧑‍🔬 Lead Tester",
            description="Coordinates testing process and manages workflow"
        )
        
        # Initialize specialized agents
        self.agents = {
            "test_executor": TestExecutor(),
            "failure_diagnostician": FailureDiagnostician(),
            "auto_fixer": AutoFixerAgent(),
            "integration_verifier": IntegrationVerifier(),
            "qa_guardian": QAQualityGuardian(),
            "environment_auditor": EnvironmentAuditor()
        }
        
        self.project_context: Dict[str, Any] = {}
        self.test_strategy: Optional[str] = None
        self.current_phase: str = "initialization"
    
    async def execute(self, context: TestContext) -> List[TestResult]:
        """
        Coordinate the full testing process.
        
        Args:
            context: Test context with project information
            
        Returns:
            List of test results from all agents
        """
        self.clear_results()
        
        # Load project context from memory bank
        self.project_context = self.load_memory_bank(context.memory_bank_path)
        
        # Determine test strategy
        self.test_strategy = self._determine_test_strategy(context)
        
        # Phase 1: Environment and dependency validation
        await self._phase_environment_validation(context)
        
        # Phase 2: Test execution
        await self._phase_test_execution(context)
        
        # Phase 3: Failure analysis and fixing (if needed)
        if self.has_failures():
            await self._phase_failure_handling(context)
        
        # Phase 4: Integration verification
        await self._phase_integration_verification(context)
        
        # Phase 5: Quality assessment
        await self._phase_quality_assessment(context)
        
        return self.results
    
    def _determine_test_strategy(self, context: TestContext) -> str:
        """Determine the appropriate test strategy based on context."""
        
        if context.test_scope == "all":
            return "comprehensive"
        elif context.test_scope.startswith("unit"):
            return "unit_focused"
        elif context.test_scope.startswith("integration"):
            return "integration_focused"
        elif context.test_scope.startswith("e2e"):
            return "e2e_focused"
        elif context.test_scope.startswith("module:"):
            return "module_focused"
        elif context.test_scope.startswith("task:"):
            return "task_focused"
        else:
            return "default"
    
    async def _phase_environment_validation(self, context: TestContext):
        """Phase 1: Validate environment and dependencies."""
        self.current_phase = "environment_validation"
        
        # Run environment auditor
        env_agent = self.agents["environment_auditor"]
        env_results = await env_agent.execute(context)
        
        # Add environment validation results
        for result in env_results:
            self.add_result(
                test_name=f"Environment: {result.test_name}",
                status=result.status,
                duration=result.duration,
                output=result.output,
                error_message=result.error_message,
                metadata={"phase": "environment_validation", "agent": "environment_auditor"}
            )
        
        # Check if environment is ready
        env_failures = [r for r in env_results if r.status != TestStatus.PASSED]
        if env_failures:
            self.add_result(
                test_name="Environment Readiness",
                status=TestStatus.FAILED,
                duration=0.0,
                output=f"Environment validation failed: {len(env_failures)} issues",
                error_message="Environment not ready for testing",
                metadata={"phase": "environment_validation", "critical": True}
            )
    
    async def _phase_test_execution(self, context: TestContext):
        """Phase 2: Execute tests based on strategy."""
        self.current_phase = "test_execution"
        
        # Run test executor
        executor_agent = self.agents["test_executor"]
        executor_results = await executor_agent.execute(context)
        
        # Add test execution results
        for result in executor_results:
            self.add_result(
                test_name=result.test_name,
                status=result.status,
                duration=result.duration,
                output=result.output,
                error_message=result.error_message,
                failure_type=result.failure_type,
                file_path=result.file_path,
                line_number=result.line_number,
                metadata={"phase": "test_execution", "agent": "test_executor"}
            )
        
        # Add summary result
        passed = len([r for r in executor_results if r.status == TestStatus.PASSED])
        failed = len([r for r in executor_results if r.status == TestStatus.FAILED])
        errors = len([r for r in executor_results if r.status == TestStatus.ERROR])
        
        self.add_result(
            test_name="Test Execution Summary",
            status=TestStatus.PASSED if failed == 0 and errors == 0 else TestStatus.FAILED,
            duration=sum(r.duration for r in executor_results),
            output=f"Tests executed: {passed} passed, {failed} failed, {errors} errors",
            metadata={
                "phase": "test_execution",
                "summary": True,
                "passed": passed,
                "failed": failed,
                "errors": errors
            }
        )
    
    async def _phase_failure_handling(self, context: TestContext):
        """Phase 3: Handle test failures with diagnosis and fixing."""
        self.current_phase = "failure_handling"
        
        # Get failed tests
        failed_tests = self.get_failed_tests() + self.get_error_tests()
        
        if not failed_tests:
            return
        
        # Run failure diagnostician
        diagnostician_agent = self.agents["failure_diagnostician"]
        diagnostician_results = await diagnostician_agent.execute(context)
        
        # Add diagnosis results
        for result in diagnostician_results:
            self.add_result(
                test_name=f"Diagnosis: {result.test_name}",
                status=result.status,
                duration=result.duration,
                output=result.output,
                error_message=result.error_message,
                metadata={"phase": "failure_handling", "agent": "failure_diagnostician"}
            )
        
        # Run auto-fixer if diagnoses are available
        if diagnostician_agent.failures:
            fixer_agent = self.agents["auto_fixer"]
            fixer_results = await fixer_agent.execute(context)
            
            # Add fix results
            for result in fixer_results:
                self.add_result(
                    test_name=f"Fix: {result.test_name}",
                    status=result.status,
                    duration=result.duration,
                    output=result.output,
                    error_message=result.error_message,
                    metadata={"phase": "failure_handling", "agent": "auto_fixer"}
                )
            
            # Re-run tests if fixes were applied
            if any(r.status == TestStatus.PASSED for r in fixer_results):
                await self._phase_test_execution(context)
    
    async def _phase_integration_verification(self, context: TestContext):
        """Phase 4: Verify integration consistency."""
        self.current_phase = "integration_verification"
        
        # Run integration verifier
        verifier_agent = self.agents["integration_verifier"]
        verifier_results = await verifier_agent.execute(context)
        
        # Add verification results
        for result in verifier_results:
            self.add_result(
                test_name=f"Integration: {result.test_name}",
                status=result.status,
                duration=result.duration,
                output=result.output,
                error_message=result.error_message,
                metadata={"phase": "integration_verification", "agent": "integration_verifier"}
            )
    
    async def _phase_quality_assessment(self, context: TestContext):
        """Phase 5: Assess overall test quality."""
        self.current_phase = "quality_assessment"
        
        # Run QA guardian
        qa_agent = self.agents["qa_guardian"]
        qa_results = await qa_agent.execute(context)
        
        # Add quality assessment results
        for result in qa_results:
            self.add_result(
                test_name=f"Quality: {result.test_name}",
                status=result.status,
                duration=result.duration,
                output=result.output,
                error_message=result.error_message,
                metadata={"phase": "quality_assessment", "agent": "qa_guardian"}
            )
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get a summary of the testing process and results."""
        
        # Count results by phase
        phase_counts = {}
        for result in self.results:
            phase = result.metadata.get("phase", "unknown") if result.metadata else "unknown"
            if phase not in phase_counts:
                phase_counts[phase] = {"passed": 0, "failed": 0, "errors": 0}
            
            if result.status == TestStatus.PASSED:
                phase_counts[phase]["passed"] += 1
            elif result.status == TestStatus.FAILED:
                phase_counts[phase]["failed"] += 1
            elif result.status == TestStatus.ERROR:
                phase_counts[phase]["errors"] += 1
        
        return {
            "test_strategy": self.test_strategy,
            "current_phase": self.current_phase,
            "total_results": len(self.results),
            "success_rate": self.get_success_rate(),
            "phase_breakdown": phase_counts,
            "agents_used": list(self.agents.keys()),
            "has_failures": self.has_failures(),
            "project_context_loaded": bool(self.project_context)
        }
    
    def should_continue_testing(self) -> bool:
        """Determine if testing should continue after failures."""
        # Continue if we have high-confidence fixes available
        auto_fixer = self.agents["auto_fixer"]
        if auto_fixer.failures:
            high_confidence_fixes = [
                f for f in auto_fixer.failures 
                if f.confidence.value in ["High", "Medium"]
            ]
            return len(high_confidence_fixes) > 0
        
        return False
    
    def get_stability_status(self) -> str:
        """Get overall system stability status."""
        if not self.has_failures():
            return "✅ Stable Build"
        elif self.should_continue_testing():
            return "🔄 Fixing in Progress"
        else:
            return "❌ Unstable Build"
