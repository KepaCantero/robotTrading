"""
Code Quality Specialist Agent

Analyzes code for quality issues including:
- Naming conventions
- Code readability
- Code smells
- Maintainability issues
- Style consistency
"""

import re
from typing import Dict, List, Any
from .base_agent import BaseReviewAgent, ReviewContext, ReviewFinding, Severity


class CodeQualitySpecialist(BaseReviewAgent):
    """
    Code Quality Specialist focuses on code maintainability and style.
    
    This agent checks for:
    - Naming conventions (PEP 8 compliance)
    - Code readability and clarity
    - Code smells and anti-patterns
    - Duplication and refactoring opportunities
    - Documentation and comments
    """
    
    def __init__(self):
        super().__init__(
            name="🧱 Code Quality Specialist",
            description="Ensures code quality, readability, and maintainability"
        )
        
        # Code smell patterns
        self.code_smells = {
            "long_method": r"def\s+\w+.*:\s*(.*\n){20,}",  # Methods with 20+ lines
            "long_parameter_list": r"def\s+\w+\([^)]{100,}\)",  # Long parameter lists
            "duplicate_code": r"(.{10,})\n.*\1",  # Simple duplicate detection
            "magic_strings": r'"[A-Z_]{3,}"',  # Magic strings
            "commented_code": r"#\s*(def|class|if|for|while)",  # Commented out code
            "todo_comments": r"#\s*(TODO|FIXME|HACK|XXX)",
            "complex_expression": r"if\s+.*and\s+.*and\s+.*and\s+.*:",
            "deep_nesting": r"if\s+.*:\s*.*if\s+.*:\s*.*if\s+.*:\s*.*if\s+.*:"
        }
        
        # Naming convention patterns
        self.naming_patterns = {
            "snake_case": r"[a-z][a-z0-9_]*",
            "PascalCase": r"[A-Z][a-zA-Z0-9]*",
            "camelCase": r"[a-z][a-zA-Z0-9]*",
            "UPPER_CASE": r"[A-Z][A-Z0-9_]*"
        }
    
    async def analyze(self, code_content: str, context: ReviewContext) -> List[ReviewFinding]:
        """Analyze code for quality issues."""
        self.clear_findings()
        
        # Analyze naming conventions
        await self._analyze_naming_conventions(code_content)
        
        # Analyze code smells
        await self._analyze_code_smells(code_content)
        
        # Analyze readability
        await self._analyze_readability(code_content)
        
        # Analyze documentation
        await self._analyze_documentation(code_content)
        
        # Analyze duplication
        await self._analyze_duplication(code_content)
        
        return self.findings
    
    async def _analyze_naming_conventions(self, code_content: str):
        """Check naming conventions against PEP 8."""
        
        # Extract function names
        function_names = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code_content)
        for func_name in function_names:
            if not re.match(self.naming_patterns["snake_case"], func_name):
                self.add_finding(
                    category="Naming Conventions",
                    summary=f"Function name '{func_name}' doesn't follow snake_case convention",
                    severity=Severity.LOW,
                    recommendation=f"Rename '{func_name}' to follow snake_case (e.g., {func_name.lower()})"
                )
        
        # Extract class names
        class_names = re.findall(r"class\s+([A-Z][a-zA-Z0-9_]*)", code_content)
        for class_name in class_names:
            if not re.match(self.naming_patterns["PascalCase"], class_name):
                self.add_finding(
                    category="Naming Conventions",
                    summary=f"Class name '{class_name}' doesn't follow PascalCase convention",
                    severity=Severity.LOW,
                    recommendation=f"Rename '{class_name}' to follow PascalCase convention"
                )
        
        # Extract variable names
        variable_names = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=", code_content)
        for var_name in variable_names:
            if var_name not in ["self", "cls"] and not re.match(self.naming_patterns["snake_case"], var_name):
                self.add_finding(
                    category="Naming Conventions",
                    summary=f"Variable name '{var_name}' doesn't follow snake_case convention",
                    severity=Severity.LOW,
                    recommendation=f"Rename '{var_name}' to follow snake_case convention"
                )
        
        # Extract constant names
        constant_names = re.findall(r"([A-Z][A-Z0-9_]*)\s*=", code_content)
        for const_name in constant_names:
            if not re.match(self.naming_patterns["UPPER_CASE"], const_name):
                self.add_finding(
                    category="Naming Conventions",
                    summary=f"Constant name '{const_name}' should be UPPER_CASE",
                    severity=Severity.LOW,
                    recommendation=f"Rename '{const_name}' to UPPER_CASE format"
                )
        
        # Check for single letter variables (except common ones)
        single_letter_vars = re.findall(r"\b([a-z])\s*=", code_content)
        common_single_letters = ["i", "j", "k", "x", "y", "z", "n", "m"]
        for var in single_letter_vars:
            if var not in common_single_letters:
                self.add_finding(
                    category="Naming Conventions",
                    summary=f"Single letter variable '{var}' should have descriptive name",
                    severity=Severity.LOW,
                    recommendation=f"Replace '{var}' with a more descriptive variable name"
                )
    
    async def _analyze_code_smells(self, code_content: str):
        """Detect common code smells."""
        
        # Check for long methods
        if re.search(self.code_smells["long_method"], code_content, re.MULTILINE):
            self.add_finding(
                category="Code Smells",
                summary="Long method detected (20+ lines)",
                severity=Severity.MEDIUM,
                recommendation="Break down long methods into smaller, focused functions"
            )
        
        # Check for long parameter lists
        if re.search(self.code_smells["long_parameter_list"], code_content):
            self.add_finding(
                category="Code Smells",
                summary="Long parameter list detected",
                severity=Severity.MEDIUM,
                recommendation="Consider using data classes or configuration objects for many parameters"
            )
        
        # Check for magic strings
        magic_strings = re.findall(self.code_smells["magic_strings"], code_content)
        if magic_strings:
            self.add_finding(
                category="Code Smells",
                summary=f"Magic strings detected: {', '.join(set(magic_strings))}",
                severity=Severity.LOW,
                recommendation="Replace magic strings with named constants"
            )
        
        # Check for commented code
        if re.search(self.code_smells["commented_code"], code_content):
            self.add_finding(
                category="Code Smells",
                summary="Commented out code detected",
                severity=Severity.LOW,
                recommendation="Remove commented out code or explain why it's kept"
            )
        
        # Check for TODO comments
        todo_comments = re.findall(self.code_smells["todo_comments"], code_content, re.IGNORECASE)
        if todo_comments:
            self.add_finding(
                category="Code Smells",
                summary=f"TODO comments found: {len(todo_comments)} items",
                severity=Severity.LOW,
                recommendation="Address TODO comments or create issues to track them"
            )
        
        # Check for complex expressions
        if re.search(self.code_smells["complex_expression"], code_content):
            self.add_finding(
                category="Code Smells",
                summary="Complex boolean expression detected",
                severity=Severity.MEDIUM,
                recommendation="Extract complex conditions into well-named boolean variables or methods"
            )
        
        # Check for deep nesting
        if re.search(self.code_smells["deep_nesting"], code_content, re.MULTILINE):
            self.add_finding(
                category="Code Smells",
                summary="Deep nesting detected (4+ levels)",
                severity=Severity.MEDIUM,
                recommendation="Refactor to reduce nesting depth using early returns or guard clauses"
            )
    
    async def _analyze_readability(self, code_content: str):
        """Analyze code readability and clarity."""
        
        # Check for line length (approximate)
        lines = code_content.split('\n')
        long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 100]
        if long_lines:
            self.add_finding(
                category="Readability",
                summary=f"Long lines detected: {len(long_lines)} lines over 100 characters",
                severity=Severity.LOW,
                recommendation="Break long lines for better readability (PEP 8 recommends 79 characters)"
            )
        
        # Check for inconsistent indentation
        indentations = []
        for line in lines:
            if line.strip():  # Non-empty line
                leading_spaces = len(line) - len(line.lstrip())
                if leading_spaces > 0:
                    indentations.append(leading_spaces)
        
        if indentations:
            unique_indents = set(indentations)
            if len(unique_indents) > 3:  # More than 4-space, 8-space, etc.
                self.add_finding(
                    category="Readability",
                    summary="Inconsistent indentation detected",
                    severity=Severity.MEDIUM,
                    recommendation="Use consistent 4-space indentation throughout the code"
                )
        
        # Check for meaningful variable names
        meaningless_names = ["data", "temp", "tmp", "result", "value", "item", "obj"]
        for name in meaningless_names:
            if f" {name} " in code_content or f" {name}=" in code_content:
                self.add_finding(
                    category="Readability",
                    summary=f"Generic variable name '{name}' used",
                    severity=Severity.LOW,
                    recommendation=f"Replace '{name}' with a more descriptive variable name"
                )
        
        # Check for complex list comprehensions
        complex_comprehensions = re.findall(r"\[.*for.*if.*for.*if.*\]", code_content)
        if complex_comprehensions:
            self.add_finding(
                category="Readability",
                summary="Complex list comprehension detected",
                severity=Severity.LOW,
                recommendation="Consider breaking complex list comprehensions into multiple lines or using loops"
            )
    
    async def _analyze_documentation(self, code_content: str):
        """Analyze documentation and comments quality."""
        
        # Check for missing docstrings in functions
        function_defs = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)", code_content)
        for func_name in function_defs:
            # Look for docstring after function definition
            func_pattern = rf"def\s+{func_name}.*?:\s*(.*?)(?=def|class|\Z)"
            func_match = re.search(func_pattern, code_content, re.DOTALL)
            if func_match:
                func_body = func_match.group(1)
                if '"""' not in func_body and "'''" not in func_body:
                    self.add_finding(
                        category="Documentation",
                        summary=f"Function '{func_name}' missing docstring",
                        severity=Severity.LOW,
                        recommendation=f"Add docstring to function '{func_name}' explaining its purpose and parameters"
                    )
        
        # Check for missing docstrings in classes
        class_defs = re.findall(r"class\s+([A-Z][a-zA-Z0-9_]*)", code_content)
        for class_name in class_defs:
            class_pattern = rf"class\s+{class_name}.*?:\s*(.*?)(?=class|def|\Z)"
            class_match = re.search(class_pattern, code_content, re.DOTALL)
            if class_match:
                class_body = class_match.group(1)
                if '"""' not in class_body and "'''" not in class_body:
                    self.add_finding(
                        category="Documentation",
                        summary=f"Class '{class_name}' missing docstring",
                        severity=Severity.LOW,
                        recommendation=f"Add docstring to class '{class_name}' explaining its purpose"
                    )
        
        # Check for inline comments quality
        comment_lines = [line for line in code_content.split('\n') if line.strip().startswith('#')]
        for comment in comment_lines:
            comment_text = comment.strip('#').strip()
            if len(comment_text) < 5:
                self.add_finding(
                    category="Documentation",
                    summary="Very short comment detected",
                    severity=Severity.LOW,
                    recommendation="Make comments more descriptive or remove if not needed"
                )
        
        # Check for TODO/FIXME comments
        todo_pattern = r"#\s*(TODO|FIXME|HACK|XXX):?\s*(.+)"
        todo_matches = re.findall(todo_pattern, code_content, re.IGNORECASE)
        if todo_matches:
            self.add_finding(
                category="Documentation",
                summary=f"TODO/FIXME comments found: {len(todo_matches)} items",
                severity=Severity.LOW,
                recommendation="Address TODO comments or create issues to track them"
            )
    
    async def _analyze_duplication(self, code_content: str):
        """Analyze code duplication."""
        
        # Simple duplicate code detection
        lines = [line.strip() for line in code_content.split('\n') if line.strip() and not line.strip().startswith('#')]
        
        # Find repeated lines (simple approach)
        line_counts = {}
        for line in lines:
            if len(line) > 10:  # Only consider substantial lines
                line_counts[line] = line_counts.get(line, 0) + 1
        
        duplicates = {line: count for line, count in line_counts.items() if count > 1}
        if duplicates:
            self.add_finding(
                category="Duplication",
                summary=f"Duplicate code detected: {len(duplicates)} repeated lines",
                severity=Severity.MEDIUM,
                recommendation="Extract duplicate code into reusable functions or methods"
            )
        
        # Check for similar function patterns
        function_patterns = re.findall(r"def\s+(\w+).*?:\s*(.*?)(?=def|\Z)", code_content, re.DOTALL)
        if len(function_patterns) > 1:
            # Simple similarity check based on structure
            similar_functions = []
            for i, (name1, body1) in enumerate(function_patterns):
                for name2, body2 in function_patterns[i+1:]:
                    # Check if functions have similar structure
                    if len(body1) > 50 and len(body2) > 50:  # Substantial functions
                        # Simple similarity metric
                        common_lines = set(body1.split('\n')) & set(body2.split('\n'))
                        if len(common_lines) > 5:
                            similar_functions.append((name1, name2))
            
            if similar_functions:
                self.add_finding(
                    category="Duplication",
                    summary=f"Similar functions detected: {len(similar_functions)} pairs",
                    severity=Severity.MEDIUM,
                    recommendation="Consider extracting common functionality into shared methods"
                )
