"""
Base Review Agent

Abstract base class for all code review agents.
Defines the common interface and functionality for specialized reviewers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import os


class Severity(Enum):
    """Severity levels for code review findings."""
    CRITICAL = "🔴 Critical"
    HIGH = "🟠 High" 
    MEDIUM = "🟡 Medium"
    LOW = "🟢 Low"


@dataclass
class ReviewFinding:
    """Individual finding from a code review agent."""
    category: str
    agent: str
    summary: str
    severity: Severity
    recommendation: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ReviewContext:
    """Context information for code review."""
    project_path: str
    memory_bank_path: str
    target_files: List[str]
    review_type: str  # "diff", "file", "pr"
    branch_name: Optional[str] = None
    commit_hash: Optional[str] = None


class BaseReviewAgent(ABC):
    """
    Abstract base class for all code review agents.
    
    Each specialized agent should inherit from this class and implement
    the analyze method to provide domain-specific code review feedback.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.findings: List[ReviewFinding] = []
    
    @abstractmethod
    async def analyze(self, code_content: str, context: ReviewContext) -> List[ReviewFinding]:
        """
        Analyze code content and return findings.
        
        Args:
            code_content: The code to analyze
            context: Review context with project information
            
        Returns:
            List of review findings
        """
        pass
    
    def load_memory_bank(self, memory_bank_path: str) -> Dict[str, Any]:
        """Load project context from memory bank."""
        try:
            # Load core memory bank files
            memory_data = {}
            
            # Load project brief
            brief_path = os.path.join(memory_bank_path, "core", "project_brief.md")
            if os.path.exists(brief_path):
                with open(brief_path, 'r', encoding='utf-8') as f:
                    memory_data['project_brief'] = f.read()
            
            # Load tech context
            tech_path = os.path.join(memory_bank_path, "core", "tech_context.md")
            if os.path.exists(tech_path):
                with open(tech_path, 'r', encoding='utf-8') as f:
                    memory_data['tech_context'] = f.read()
            
            # Load system patterns
            patterns_path = os.path.join(memory_bank_path, "core", "system_patterns.md")
            if os.path.exists(patterns_path):
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    memory_data['system_patterns'] = f.read()
            
            # Load active context
            active_path = os.path.join(memory_bank_path, "active_context.md")
            if os.path.exists(active_path):
                with open(active_path, 'r', encoding='utf-8') as f:
                    memory_data['active_context'] = f.read()
            
            return memory_data
            
        except Exception as e:
            print(f"Warning: Could not load memory bank: {e}")
            return {}
    
    def add_finding(self, 
                   category: str,
                   summary: str, 
                   severity: Severity,
                   recommendation: str,
                   file_path: Optional[str] = None,
                   line_number: Optional[int] = None,
                   code_snippet: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None):
        """Add a finding to the agent's results."""
        finding = ReviewFinding(
            category=category,
            agent=self.name,
            summary=summary,
            severity=severity,
            recommendation=recommendation,
            file_path=file_path,
            line_number=line_number,
            code_snippet=code_snippet,
            metadata=metadata
        )
        self.findings.append(finding)
    
    def get_findings_by_severity(self, severity: Severity) -> List[ReviewFinding]:
        """Get findings filtered by severity level."""
        return [f for f in self.findings if f.severity == severity]
    
    def get_critical_findings(self) -> List[ReviewFinding]:
        """Get all critical findings."""
        return self.get_findings_by_severity(Severity.CRITICAL)
    
    def get_high_findings(self) -> List[ReviewFinding]:
        """Get all high severity findings."""
        return self.get_findings_by_severity(Severity.HIGH)
    
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return len(self.get_critical_findings()) > 0
    
    def clear_findings(self):
        """Clear all findings."""
        self.findings.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent findings to dictionary format."""
        return {
            "agent": self.name,
            "description": self.description,
            "findings_count": len(self.findings),
            "critical_count": len(self.get_critical_findings()),
            "high_count": len(self.get_high_findings()),
            "findings": [
                {
                    "category": f.category,
                    "summary": f.summary,
                    "severity": f.severity.value,
                    "recommendation": f.recommendation,
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "code_snippet": f.code_snippet,
                    "metadata": f.metadata
                }
                for f in self.findings
            ]
        }
