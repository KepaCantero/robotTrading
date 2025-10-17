"""
Lead Reviewer Agent

Coordinates the code review process by:
1. Loading project context from memory bank
2. Distributing review tasks to specialized agents
3. Synthesizing results into unified report
4. Managing the overall review workflow
"""

import asyncio
from typing import Dict, List, Any, Optional
from .base_agent import BaseReviewAgent, ReviewContext, ReviewFinding, Severity
from .architecture_analyst import ArchitectureAnalyst
from .algorithm_expert import AlgorithmExpert
from .code_quality_specialist import CodeQualitySpecialist
from .testing_reviewer import TestingReviewer
from .security_auditor import SecurityAuditor
from .cicd_verifier import CICDVerifier


class LeadReviewer(BaseReviewAgent):
    """
    Lead Reviewer coordinates the entire code review process.
    
    This agent acts as the orchestrator, delegating specific analysis
    tasks to specialized agents and synthesizing their findings.
    """
    
    def __init__(self):
        super().__init__(
            name="🧑‍💻 Lead Reviewer",
            description="Coordinates code review process and synthesizes findings"
        )
        
        # Initialize specialized agents
        self.agents = {
            "architecture": ArchitectureAnalyst(),
            "algorithm": AlgorithmExpert(),
            "code_quality": CodeQualitySpecialist(),
            "testing": TestingReviewer(),
            "security": SecurityAuditor(),
            "cicd": CICDVerifier()
        }
        
        self.project_context: Dict[str, Any] = {}
        self.review_scope: Optional[str] = None
    
    async def analyze(self, code_content: str, context: ReviewContext) -> List[ReviewFinding]:
        """
        Coordinate the full code review process.
        
        Args:
            code_content: The code to review
            context: Review context with project information
            
        Returns:
            List of synthesized review findings
        """
        self.clear_findings()
        
        # Load project context from memory bank
        self.project_context = self.load_memory_bank(context.memory_bank_path)
        
        # Determine review scope
        self.review_scope = self._determine_review_scope(context)
        
        # Add lead reviewer findings about project context
        await self._analyze_project_context(context)
        
        # Delegate to specialized agents
        all_findings = await self._delegate_to_agents(code_content, context)
        
        # Synthesize and prioritize findings
        synthesized_findings = self._synthesize_findings(all_findings)
        
        # Add synthesis findings
        self.findings.extend(synthesized_findings)
        
        return self.findings
    
    def _determine_review_scope(self, context: ReviewContext) -> str:
        """Determine the scope of the review based on context."""
        if context.review_type == "pr":
            return "Pull Request Review"
        elif context.review_type == "diff":
            return "Code Diff Review"
        elif context.review_type == "file":
            return f"File Review: {', '.join(context.target_files)}"
        else:
            return "General Code Review"
    
    async def _analyze_project_context(self, context: ReviewContext):
        """Analyze project context and add relevant findings."""
        
        # Check if memory bank is properly loaded
        if not self.project_context:
            self.add_finding(
                category="Project Context",
                summary="Memory bank not found or incomplete",
                severity=Severity.HIGH,
                recommendation="Ensure .memory directory exists with core files (project_brief.md, tech_context.md, etc.)"
            )
            return
        
        # Validate project context completeness
        required_files = ["project_brief", "tech_context", "system_patterns"]
        missing_files = [f for f in required_files if f not in self.project_context]
        
        if missing_files:
            self.add_finding(
                category="Project Context",
                summary=f"Missing memory bank files: {', '.join(missing_files)}",
                severity=Severity.MEDIUM,
                recommendation="Complete memory bank with missing core files for better context"
            )
        
        # Check if we're in the right project phase
        if "active_context" in self.project_context:
            active_context = self.project_context["active_context"]
            if "T001" in active_context and "T002" not in active_context:
                self.add_finding(
                    category="Project Context",
                    summary="Reviewing code in early project phase (T001 complete)",
                    severity=Severity.LOW,
                    recommendation="Focus on foundational patterns and architecture decisions"
                )
    
    async def _delegate_to_agents(self, code_content: str, context: ReviewContext) -> Dict[str, List[ReviewFinding]]:
        """Delegate analysis to specialized agents."""
        all_findings = {}
        
        # Run all agents in parallel for efficiency
        tasks = []
        for agent_name, agent in self.agents.items():
            task = asyncio.create_task(agent.analyze(code_content, context))
            tasks.append((agent_name, task))
        
        # Collect results
        for agent_name, task in tasks:
            try:
                findings = await task
                all_findings[agent_name] = findings
            except Exception as e:
                self.add_finding(
                    category="Review Process",
                    summary=f"Agent {agent_name} failed: {str(e)}",
                    severity=Severity.HIGH,
                    recommendation=f"Check {agent_name} agent implementation and dependencies"
                )
                all_findings[agent_name] = []
        
        return all_findings
    
    def _synthesize_findings(self, all_findings: Dict[str, List[ReviewFinding]]) -> List[ReviewFinding]:
        """Synthesize findings from all agents into coherent insights."""
        synthesized = []
        
        # Count findings by severity across all agents
        severity_counts = {severity: 0 for severity in Severity}
        agent_counts = {agent: 0 for agent in self.agents.keys()}
        
        for agent_name, findings in all_findings.items():
            agent_counts[agent_name] = len(findings)
            for finding in findings:
                severity_counts[finding.severity] += 1
        
        # Add synthesis findings
        total_findings = sum(agent_counts.values())
        critical_count = severity_counts[Severity.CRITICAL]
        high_count = severity_counts[Severity.HIGH]
        
        if total_findings == 0:
            synthesized.append(ReviewFinding(
                category="Review Summary",
                agent=self.name,
                summary="No issues found in code review",
                severity=Severity.LOW,
                recommendation="Code appears to meet quality standards"
            ))
        else:
            # Overall assessment
            if critical_count > 0:
                assessment = f"Critical issues found ({critical_count} critical, {high_count} high)"
                severity = Severity.CRITICAL
                recommendation = "Address critical issues before proceeding"
            elif high_count > 0:
                assessment = f"High priority issues found ({high_count} high)"
                severity = Severity.HIGH
                recommendation = "Address high priority issues"
            else:
                assessment = f"Minor issues found ({total_findings} total)"
                severity = Severity.LOW
                recommendation = "Consider addressing minor issues for code quality"
            
            synthesized.append(ReviewFinding(
                category="Review Summary",
                agent=self.name,
                summary=assessment,
                severity=severity,
                recommendation=recommendation
            ))
        
        # Agent performance summary
        active_agents = [agent for agent, count in agent_counts.items() if count > 0]
        if active_agents:
            synthesized.append(ReviewFinding(
                category="Review Process",
                agent=self.name,
                summary=f"Active review agents: {', '.join(active_agents)}",
                severity=Severity.LOW,
                recommendation="All specialized agents completed analysis successfully"
            ))
        
        return synthesized
    
    def get_review_summary(self) -> Dict[str, Any]:
        """Get a summary of the review process and results."""
        return {
            "review_scope": self.review_scope,
            "project_context_loaded": bool(self.project_context),
            "agents_used": list(self.agents.keys()),
            "total_findings": len(self.findings),
            "critical_findings": len(self.get_critical_findings()),
            "high_findings": len(self.get_high_findings()),
            "review_status": "completed"
        }
    
    def should_block_merge(self) -> bool:
        """Determine if the review findings should block a merge."""
        return self.has_critical_issues() or len(self.get_high_findings()) > 3
