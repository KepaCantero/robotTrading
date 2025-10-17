"""
Testing Orchestrator

Coordinates the testing process by managing specialized agents
and synthesizing their results into comprehensive test reports.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from .agents import (
    LeadTester,
    TestExecutor,
    FailureDiagnostician,
    AutoFixerAgent,
    IntegrationVerifier,
    QAQualityGuardian,
    EnvironmentAuditor
)
from .agents.base_test_agent import TestContext, TestResult, TestStatus
from .report_generator import TestReportGenerator


class TestingOrchestrator:
    """
    Orchestrates the testing process using specialized agents.
    
    This class coordinates the entire testing workflow:
    1. Initializes the test context
    2. Coordinates specialized testing agents
    3. Manages failure diagnosis and fixing
    4. Generates comprehensive test reports
    """
    
    def __init__(self, project_path: str, memory_bank_path: str = ".memory"):
        self.project_path = Path(project_path)
        self.memory_bank_path = Path(memory_bank_path)
        self.lead_tester = LeadTester()
        self.report_generator = TestReportGenerator()
        
        # Initialize all agents
        self.agents = {
            "lead_tester": self.lead_tester,
            "test_executor": TestExecutor(),
            "failure_diagnostician": FailureDiagnostician(),
            "auto_fixer": AutoFixerAgent(),
            "integration_verifier": IntegrationVerifier(),
            "qa_guardian": QAQualityGuardian(),
            "environment_auditor": EnvironmentAuditor()
        }
    
    async def run_tests(self, 
                       test_scope: str = "all",
                       environment: str = "local",
                       branch_name: Optional[str] = None,
                       commit_hash: Optional[str] = None) -> Dict[str, Any]:
        """
        Run comprehensive test suite.
        
        Args:
            test_scope: Test scope ("all", "unit", "integration", "e2e", "module:name", "task:T001")
            environment: Test environment ("local", "ci", "docker")
            branch_name: Branch name for context
            commit_hash: Commit hash for context
            
        Returns:
            Comprehensive test report
        """
        
        # Create test context
        context = TestContext(
            project_path=str(self.project_path),
            memory_bank_path=str(self.memory_bank_path),
            test_scope=test_scope,
            environment=environment,
            branch_name=branch_name,
            commit_hash=commit_hash
        )
        
        # Execute tests with lead tester (coordinates all agents)
        results = await self.lead_tester.execute(context)
        
        # Generate comprehensive report
        report = await self.report_generator.generate_report(
            results=results,
            context=context,
            test_summary=self.lead_tester.get_test_summary()
        )
        
        return report
    
    async def test_all(self) -> Dict[str, Any]:
        """Run all tests."""
        return await self.run_tests(test_scope="all")
    
    async def test_unit(self) -> Dict[str, Any]:
        """Run unit tests only."""
        return await self.run_tests(test_scope="unit")
    
    async def test_integration(self) -> Dict[str, Any]:
        """Run integration tests only."""
        return await self.run_tests(test_scope="integration")
    
    async def test_e2e(self) -> Dict[str, Any]:
        """Run end-to-end tests only."""
        return await self.run_tests(test_scope="e2e")
    
    async def test_module(self, module_name: str) -> Dict[str, Any]:
        """Run tests for a specific module."""
        return await self.run_tests(test_scope=f"module:{module_name}")
    
    async def test_task(self, task_name: str) -> Dict[str, Any]:
        """Run tests for a specific task."""
        return await self.run_tests(test_scope=f"task:{task_name}")
    
    async def test_with_fixes(self, test_scope: str = "all") -> Dict[str, Any]:
        """Run tests with automatic fixing enabled."""
        
        # Create test context
        context = TestContext(
            project_path=str(self.project_path),
            memory_bank_path=str(self.memory_bank_path),
            test_scope=test_scope,
            environment="local"
        )
        
        # Run initial tests
        initial_results = await self.lead_tester.execute(context)
        
        # Check if there are failures
        if self.lead_tester.has_failures():
            # Run auto-fixer
            auto_fixer = self.agents["auto_fixer"]
            fix_results = await auto_fixer.execute(context)
            
            # Re-run tests after fixes
            if fix_results:
                final_results = await self.lead_tester.execute(context)
                
                # Generate report with fix information
                report = await self.report_generator.generate_report(
                    results=final_results,
                    context=context,
                    test_summary=self.lead_tester.get_test_summary(),
                    fix_summary=auto_fixer.get_fixes_summary()
                )
                
                return report
        
        # Generate normal report
        report = await self.report_generator.generate_report(
            results=initial_results,
            context=context,
            test_summary=self.lead_tester.get_test_summary()
        )
        
        return report
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all testing agents."""
        return {
            agent_name: {
                "name": agent.name,
                "description": agent.description,
                "results_count": len(agent.results),
                "failures_count": len(agent.failures),
                "has_failures": agent.has_failures(),
                "success_rate": agent.get_success_rate()
            }
            for agent_name, agent in self.agents.items()
        }
    
    def get_system_stability(self) -> str:
        """Get overall system stability status."""
        return self.lead_tester.get_stability_status()
    
    def should_continue_testing(self) -> bool:
        """Determine if testing should continue after failures."""
        return self.lead_tester.should_continue_testing()
    
    async def generate_test_summary(self) -> str:
        """Generate a summary of the testing process and results."""
        summary = {
            "test_timestamp": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "agents_used": list(self.agents.keys()),
            "agent_status": self.get_agent_status(),
            "system_stability": self.get_system_stability(),
            "should_continue": self.should_continue_testing(),
            "test_summary": self.lead_tester.get_test_summary()
        }
        
        return json.dumps(summary, indent=2)
    
    async def export_test_results(self, format: str = "json") -> str:
        """Export test results in specified format."""
        all_results = []
        
        for agent_name, agent in self.agents.items():
            agent_data = agent.to_dict()
            agent_data["agent_name"] = agent_name
            all_results.append(agent_data)
        
        if format.lower() == "json":
            return json.dumps(all_results, indent=2)
        elif format.lower() == "csv":
            # Convert to CSV format
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "Agent", "Test Name", "Status", "Duration", "Output", 
                "Error Message", "Failure Type", "File Path", "Line Number"
            ])
            
            # Write results
            for agent_data in all_results:
                for result in agent_data["results"]:
                    writer.writerow([
                        agent_data["agent_name"],
                        result["test_name"],
                        result["status"],
                        result["duration"],
                        result["output"],
                        result.get("error_message", ""),
                        result.get("failure_type", ""),
                        result.get("file_path", ""),
                        result.get("line_number", "")
                    ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


# Convenience functions for easy usage
async def test_all(project_path: str, memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Run all tests."""
    orchestrator = TestingOrchestrator(project_path, memory_bank_path)
    return await orchestrator.test_all()


async def test_unit(project_path: str, memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Run unit tests only."""
    orchestrator = TestingOrchestrator(project_path, memory_bank_path)
    return await orchestrator.test_unit()


async def test_integration(project_path: str, memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Run integration tests only."""
    orchestrator = TestingOrchestrator(project_path, memory_bank_path)
    return await orchestrator.test_integration()


async def test_e2e(project_path: str, memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Run end-to-end tests only."""
    orchestrator = TestingOrchestrator(project_path, memory_bank_path)
    return await orchestrator.test_e2e()


async def test_module(project_path: str, module_name: str, memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Run tests for a specific module."""
    orchestrator = TestingOrchestrator(project_path, memory_bank_path)
    return await orchestrator.test_module(module_name)


async def test_task(project_path: str, task_name: str, memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Run tests for a specific task."""
    orchestrator = TestingOrchestrator(project_path, memory_bank_path)
    return await orchestrator.test_task(task_name)


async def test_with_fixes(project_path: str, test_scope: str = "all", memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Run tests with automatic fixing enabled."""
    orchestrator = TestingOrchestrator(project_path, memory_bank_path)
    return await orchestrator.test_with_fixes(test_scope)
