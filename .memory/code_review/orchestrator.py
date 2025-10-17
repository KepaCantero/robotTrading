"""
Code Review Orchestrator

Coordinates the code review process by managing specialized agents
and synthesizing their findings into a comprehensive report.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from .agents import (
    LeadReviewer,
    ArchitectureAnalyst,
    AlgorithmExpert,
    CodeQualitySpecialist,
    TestingReviewer,
    SecurityAuditor,
    CICDVerifier
)
from .agents.base_agent import ReviewContext, ReviewFinding, Severity
from .report_generator import ReportGenerator


class CodeReviewOrchestrator:
    """
    Orchestrates the code review process using specialized agents.
    
    This class coordinates the entire code review workflow:
    1. Initializes the review context
    2. Coordinates specialized agents
    3. Synthesizes findings
    4. Generates comprehensive reports
    """
    
    def __init__(self, project_path: str, memory_bank_path: str = ".memory"):
        self.project_path = Path(project_path)
        self.memory_bank_path = Path(memory_bank_path)
        self.lead_reviewer = LeadReviewer()
        self.report_generator = ReportGenerator()
        
        # Initialize all agents
        self.agents = {
            "lead_reviewer": self.lead_reviewer,
            "architecture": ArchitectureAnalyst(),
            "algorithm": AlgorithmExpert(),
            "code_quality": CodeQualitySpecialist(),
            "testing": TestingReviewer(),
            "security": SecurityAuditor(),
            "cicd": CICDVerifier()
        }
    
    async def review_code(self, 
                         target_files: List[str],
                         review_type: str = "file",
                         branch_name: Optional[str] = None,
                         commit_hash: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform comprehensive code review.
        
        Args:
            target_files: List of files to review
            review_type: Type of review ("diff", "file", "pr")
            branch_name: Branch name for PR reviews
            commit_hash: Commit hash for diff reviews
            
        Returns:
            Comprehensive review report
        """
        
        # Create review context
        context = ReviewContext(
            project_path=str(self.project_path),
            memory_bank_path=str(self.memory_bank_path),
            target_files=target_files,
            review_type=review_type,
            branch_name=branch_name,
            commit_hash=commit_hash
        )
        
        # Read code content from files
        code_content = await self._read_code_content(target_files)
        
        # Perform review with lead reviewer (coordinates all agents)
        findings = await self.lead_reviewer.analyze(code_content, context)
        
        # Generate comprehensive report
        report = await self.report_generator.generate_report(
            findings=findings,
            context=context,
            review_summary=self.lead_reviewer.get_review_summary()
        )
        
        return report
    
    async def review_file(self, file_path: str) -> Dict[str, Any]:
        """Review a single file."""
        return await self.review_code([file_path], review_type="file")
    
    async def review_diff(self, diff_content: str, commit_hash: str) -> Dict[str, Any]:
        """Review a code diff."""
        # For diff reviews, we'll analyze the diff content directly
        context = ReviewContext(
            project_path=str(self.project_path),
            memory_bank_path=str(self.memory_bank_path),
            target_files=["diff"],
            review_type="diff",
            commit_hash=commit_hash
        )
        
        findings = await self.lead_reviewer.analyze(diff_content, context)
        
        report = await self.report_generator.generate_report(
            findings=findings,
            context=context,
            review_summary=self.lead_reviewer.get_review_summary()
        )
        
        return report
    
    async def review_pr(self, branch_name: str, base_branch: str = "main") -> Dict[str, Any]:
        """Review a pull request."""
        # This would integrate with Git to get changed files
        # For now, we'll simulate by reviewing all files
        all_files = await self._get_all_code_files()
        
        return await self.review_code(
            target_files=all_files,
            review_type="pr",
            branch_name=branch_name
        )
    
    async def _read_code_content(self, file_paths: List[str]) -> str:
        """Read code content from multiple files."""
        content_parts = []
        
        for file_path in file_paths:
            if file_path == "diff":
                # Handle diff content directly
                continue
                
            full_path = self.project_path / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        content_parts.append(f"=== {file_path} ===\n{content}\n")
                except Exception as e:
                    content_parts.append(f"=== {file_path} (Error: {str(e)}) ===\n")
            else:
                content_parts.append(f"=== {file_path} (File not found) ===\n")
        
        return "\n".join(content_parts)
    
    async def _get_all_code_files(self) -> List[str]:
        """Get all code files in the project."""
        code_files = []
        
        # Common code file extensions
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs'}
        
        for ext in code_extensions:
            code_files.extend(self.project_path.rglob(f"*{ext}"))
        
        # Convert to relative paths
        return [str(f.relative_to(self.project_path)) for f in code_files if f.is_file()]
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        return {
            agent_name: {
                "name": agent.name,
                "description": agent.description,
                "findings_count": len(agent.findings),
                "has_critical": agent.has_critical_issues()
            }
            for agent_name, agent in self.agents.items()
        }
    
    def should_block_merge(self) -> bool:
        """Determine if the review should block a merge."""
        return self.lead_reviewer.should_block_merge()
    
    async def generate_summary_report(self) -> str:
        """Generate a summary report of the review process."""
        summary = {
            "review_timestamp": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "agents_used": list(self.agents.keys()),
            "agent_status": self.get_agent_status(),
            "should_block_merge": self.should_block_merge(),
            "review_summary": self.lead_reviewer.get_review_summary()
        }
        
        return json.dumps(summary, indent=2)
    
    async def export_findings(self, format: str = "json") -> str:
        """Export findings in specified format."""
        all_findings = []
        
        for agent_name, agent in self.agents.items():
            agent_data = agent.to_dict()
            agent_data["agent_name"] = agent_name
            all_findings.append(agent_data)
        
        if format.lower() == "json":
            return json.dumps(all_findings, indent=2)
        elif format.lower() == "csv":
            # Convert to CSV format
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "Agent", "Category", "Summary", "Severity", "Recommendation", 
                "File Path", "Line Number", "Code Snippet"
            ])
            
            # Write findings
            for agent_data in all_findings:
                for finding in agent_data["findings"]:
                    writer.writerow([
                        agent_data["agent_name"],
                        finding["category"],
                        finding["summary"],
                        finding["severity"],
                        finding["recommendation"],
                        finding.get("file_path", ""),
                        finding.get("line_number", ""),
                        finding.get("code_snippet", "")
                    ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")


# Convenience functions for easy usage
async def review_file(project_path: str, file_path: str, memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Review a single file."""
    orchestrator = CodeReviewOrchestrator(project_path, memory_bank_path)
    return await orchestrator.review_file(file_path)


async def review_diff(project_path: str, diff_content: str, commit_hash: str, memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Review a code diff."""
    orchestrator = CodeReviewOrchestrator(project_path, memory_bank_path)
    return await orchestrator.review_diff(diff_content, commit_hash)


async def review_pr(project_path: str, branch_name: str, base_branch: str = "main", memory_bank_path: str = ".memory") -> Dict[str, Any]:
    """Review a pull request."""
    orchestrator = CodeReviewOrchestrator(project_path, memory_bank_path)
    return await orchestrator.review_pr(branch_name, base_branch)
