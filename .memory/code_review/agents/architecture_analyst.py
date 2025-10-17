"""
Architecture Analyst Agent

Analyzes code for architectural compliance, design patterns,
and alignment with system architecture defined in memory bank.
"""

import re
from typing import Dict, List, Any
from .base_agent import BaseReviewAgent, ReviewContext, ReviewFinding, Severity


class ArchitectureAnalyst(BaseReviewAgent):
    """
    Architecture Analyst validates code against architectural principles.
    
    This agent checks for:
    - Domain-driven design compliance
    - Layering violations
    - Design pattern adherence
    - Module boundaries and dependencies
    - Consistency with system architecture
    """
    
    def __init__(self):
        super().__init__(
            name="🧠 Architecture Analyst",
            description="Validates architectural compliance and design patterns"
        )
        
        # Common architectural patterns to check
        self.patterns = {
            "repository": r"class\s+\w*Repository\w*",
            "service": r"class\s+\w*Service\w*",
            "controller": r"class\s+\w*Controller\w*|@app\.(get|post|put|delete)",
            "model": r"class\s+\w*Model\w*|class\s+\w*\(Base\)",
            "middleware": r"class\s+\w*Middleware\w*|@app\.middleware",
            "strategy": r"class\s+\w*Strategy\w*|def\s+\w*strategy\w*",
            "factory": r"class\s+\w*Factory\w*|def\s+\w*factory\w*"
        }
        
        # Anti-patterns to detect
        self.anti_patterns = {
            "god_class": r"class\s+\w+.*:\s*$.*def\s+\w+.*def\s+\w+.*def\s+\w+.*def\s+\w+.*def\s+\w+",
            "circular_import": r"from\s+.*import\s+.*\n.*from\s+.*import\s+.*",
            "tight_coupling": r"import\s+\w+\.\w+\.\w+\.\w+",
            "violation_of_single_responsibility": r"class\s+\w+.*:\s*.*def\s+\w+.*def\s+\w+.*def\s+\w+.*def\s+\w+.*def\s+\w+.*def\s+\w+"
        }
    
    async def analyze(self, code_content: str, context: ReviewContext) -> List[ReviewFinding]:
        """Analyze code for architectural compliance."""
        self.clear_findings()
        
        # Load project context
        memory_data = self.load_memory_bank(context.memory_bank_path)
        
        # Analyze architectural patterns
        await self._analyze_design_patterns(code_content)
        await self._analyze_layer_compliance(code_content, memory_data)
        await self._analyze_dependencies(code_content, context)
        await self._analyze_anti_patterns(code_content)
        await self._analyze_fastapi_compliance(code_content)
        
        return self.findings
    
    async def _analyze_design_patterns(self, code_content: str):
        """Check for proper use of design patterns."""
        
        # Check for Strategy pattern (important for trading system)
        if "strategy" in code_content.lower():
            if not re.search(self.patterns["strategy"], code_content, re.IGNORECASE):
                self.add_finding(
                    category="Design Patterns",
                    summary="Strategy pattern mentioned but not properly implemented",
                    severity=Severity.MEDIUM,
                    recommendation="Implement proper Strategy pattern with abstract base class and concrete implementations"
                )
        
        # Check for Repository pattern
        if re.search(self.patterns["repository"], code_content, re.IGNORECASE):
            self.add_finding(
                category="Design Patterns",
                summary="Repository pattern detected - good for data access abstraction",
                severity=Severity.LOW,
                recommendation="Ensure repository implements proper interface and follows single responsibility"
            )
        
        # Check for Service layer
        if re.search(self.patterns["service"], code_content, re.IGNORECASE):
            self.add_finding(
                category="Design Patterns",
                summary="Service layer detected - good for business logic separation",
                severity=Severity.LOW,
                recommendation="Ensure services are stateless and contain only business logic"
            )
    
    async def _analyze_layer_compliance(self, code_content: str, memory_data: Dict[str, Any]):
        """Check compliance with architectural layers."""
        
        # Check for proper FastAPI structure
        if "from fastapi import" in code_content:
            # Should be in API layer
            if "app/" in code_content or "api/" in code_content:
                self.add_finding(
                    category="Layer Compliance",
                    summary="FastAPI imports in appropriate API layer",
                    severity=Severity.LOW,
                    recommendation="Good separation - API layer properly isolated"
                )
            else:
                self.add_finding(
                    category="Layer Compliance",
                    summary="FastAPI imports outside API layer",
                    severity=Severity.MEDIUM,
                    recommendation="Move FastAPI dependencies to API layer (app/api/ or app/routes/)"
                )
        
        # Check for database imports
        if "from sqlalchemy" in code_content or "import sqlalchemy" in code_content:
            # Should be in models or database layer
            if "models/" in code_content or "database" in code_content:
                self.add_finding(
                    category="Layer Compliance",
                    summary="SQLAlchemy imports in appropriate data layer",
                    severity=Severity.LOW,
                    recommendation="Good separation - data layer properly isolated"
                )
            else:
                self.add_finding(
                    category="Layer Compliance",
                    summary="SQLAlchemy imports outside data layer",
                    severity=Severity.MEDIUM,
                    recommendation="Move SQLAlchemy dependencies to models or database layer"
                )
        
        # Check for business logic in wrong layer
        if "def calculate_" in code_content or "def process_" in code_content:
            if "services/" in code_content or "business/" in code_content:
                self.add_finding(
                    category="Layer Compliance",
                    summary="Business logic in appropriate service layer",
                    severity=Severity.LOW,
                    recommendation="Good separation - business logic properly isolated"
                )
            elif "api/" in code_content or "routes/" in code_content:
                self.add_finding(
                    category="Layer Compliance",
                    summary="Business logic detected in API layer",
                    severity=Severity.HIGH,
                    recommendation="Move business logic to service layer (app/services/)"
                )
    
    async def _analyze_dependencies(self, code_content: str, context: ReviewContext):
        """Analyze module dependencies and imports."""
        
        # Check for circular imports (improved logic)
        imports = re.findall(r"from\s+(\w+(?:\.\w+)*)\s+import", code_content)
        if len(imports) > 1:
            # Improved check for actual circular imports
            for i, imp1 in enumerate(imports):
                for imp2 in imports[i+1:]:
                    # Only flag if it's a real circular import (same base module)
                    base1 = imp1.split('.')[0]
                    base2 = imp2.split('.')[0]
                    if base1 == base2 and imp1 != imp2 and len(imp1.split('.')) > 1 and len(imp2.split('.')) > 1:
                        # This is likely a false positive for standard library imports
                        if base1 not in ['fastapi', 'pydantic', 'sqlalchemy', 'pytest', 'unittest']:
                            self.add_finding(
                                category="Dependencies",
                                summary=f"Potential circular import between {imp1} and {imp2}",
                                severity=Severity.MEDIUM,  # Reduced from HIGH to MEDIUM
                                recommendation="Refactor to avoid circular dependencies using dependency injection or interfaces"
                            )
        
        # Check for deep imports (tight coupling)
        deep_imports = [imp for imp in imports if len(imp.split('.')) > 3]
        if deep_imports:
            self.add_finding(
                category="Dependencies",
                summary=f"Deep imports detected: {', '.join(deep_imports)}",
                severity=Severity.MEDIUM,
                recommendation="Consider using dependency injection or facade pattern to reduce coupling"
            )
        
        # Check for external dependencies in core modules
        external_deps = ["requests", "httpx", "redis", "celery"]
        for dep in external_deps:
            if f"import {dep}" in code_content or f"from {dep}" in code_content:
                if "core/" in code_content or "models/" in code_content:
                    self.add_finding(
                        category="Dependencies",
                        summary=f"External dependency {dep} in core module",
                        severity=Severity.MEDIUM,
                        recommendation=f"Move {dep} usage to service layer or use dependency injection"
                    )
    
    async def _analyze_anti_patterns(self, code_content: str):
        """Detect architectural anti-patterns."""
        
        # Check for God Class (too many methods)
        class_matches = re.findall(r"class\s+(\w+).*?:\s*(.*?)(?=class|\Z)", code_content, re.DOTALL)
        for class_name, class_body in class_matches:
            method_count = len(re.findall(r"def\s+\w+", class_body))
            if method_count > 10:
                self.add_finding(
                    category="Anti-patterns",
                    summary=f"God Class detected: {class_name} has {method_count} methods",
                    severity=Severity.HIGH,
                    recommendation=f"Split {class_name} into smaller, focused classes following single responsibility principle"
                )
        
        # Check for long methods
        method_matches = re.findall(r"def\s+(\w+).*?:\s*(.*?)(?=def|\Z)", code_content, re.DOTALL)
        for method_name, method_body in method_matches:
            line_count = len(method_body.strip().split('\n'))
            if line_count > 50:
                self.add_finding(
                    category="Anti-patterns",
                    summary=f"Long method detected: {method_name} has {line_count} lines",
                    severity=Severity.MEDIUM,
                    recommendation=f"Break down {method_name} into smaller, focused methods"
                )
        
        # Check for magic numbers
        magic_numbers = re.findall(r"\b\d{2,}\b", code_content)
        if magic_numbers:
            self.add_finding(
                category="Anti-patterns",
                summary=f"Magic numbers detected: {', '.join(set(magic_numbers))}",
                severity=Severity.LOW,
                recommendation="Replace magic numbers with named constants or configuration values"
            )
    
    async def _analyze_fastapi_compliance(self, code_content: str):
        """Check FastAPI-specific architectural compliance."""
        
        # Check for proper async/await usage
        if "async def" in code_content:
            if "await" not in code_content:
                self.add_finding(
                    category="FastAPI Compliance",
                    summary="Async function defined but no await calls found",
                    severity=Severity.MEDIUM,
                    recommendation="Either add await calls for I/O operations or make function synchronous"
                )
        
        # Check for proper dependency injection
        if "@app.get" in code_content or "@app.post" in code_content:
            if "Depends(" not in code_content:
                self.add_finding(
                    category="FastAPI Compliance",
                    summary="FastAPI endpoints without dependency injection",
                    severity=Severity.LOW,
                    recommendation="Consider using FastAPI's Depends() for dependency injection"
                )
        
        # Check for proper error handling
        if "HTTPException" not in code_content and ("@app.get" in code_content or "@app.post" in code_content):
            self.add_finding(
                category="FastAPI Compliance",
                summary="FastAPI endpoints without proper error handling",
                severity=Severity.MEDIUM,
                recommendation="Add HTTPException handling for proper error responses"
            )
        
        # Check for proper response models
        if "@app.get" in code_content or "@app.post" in code_content:
            if "response_model" not in code_content:
                self.add_finding(
                    category="FastAPI Compliance",
                    summary="FastAPI endpoints without response models",
                    severity=Severity.LOW,
                    recommendation="Add response_model parameter for better API documentation and validation"
                )
