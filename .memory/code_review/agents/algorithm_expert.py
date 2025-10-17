"""
Algorithm & Logic Expert Agent

Analyzes code for algorithmic correctness, efficiency,
and logic flaws. Specialized in trading algorithms and data processing.
"""

import re
import ast
from typing import Dict, List, Any
from .base_agent import BaseReviewAgent, ReviewContext, ReviewFinding, Severity


class AlgorithmExpert(BaseReviewAgent):
    """
    Algorithm & Logic Expert validates algorithmic correctness and efficiency.
    
    This agent checks for:
    - Algorithmic correctness and edge cases
    - Performance optimization opportunities
    - Logic flaws and bugs
    - Trading-specific algorithm validation
    - Data structure efficiency
    """
    
    def __init__(self):
        super().__init__(
            name="🧮 Algorithm & Logic Expert",
            description="Validates algorithmic correctness and efficiency"
        )
        
        # Trading-specific patterns to check
        self.trading_patterns = {
            "price_calculation": r"(price|value|amount)\s*[\+\-\*\/]\s*(price|value|amount)",
            "position_sizing": r"(position|size|quantity)\s*=\s*.*\*.*",
            "risk_calculation": r"(risk|var|volatility|sharpe)",
            "signal_generation": r"(signal|buy|sell|hold)",
            "backtesting": r"(backtest|historical|simulate)",
            "portfolio": r"(portfolio|allocation|weight)"
        }
        
        # Performance anti-patterns
        self.performance_issues = {
            "nested_loops": r"for\s+.*:\s*.*for\s+.*:",
            "inefficient_search": r"\.index\(|\.find\(.*\)\s*!=\s*-1",
            "string_concat": r"\w+\s*\+\s*\"",
            "list_comprehension_missed": r"for\s+\w+\s+in\s+.*:\s*.*\.append\(",
            "unnecessary_computation": r"len\(.*\)\s*>\s*0"
        }
    
    async def analyze(self, code_content: str, context: ReviewContext) -> List[ReviewFinding]:
        """Analyze code for algorithmic correctness and efficiency."""
        self.clear_findings()
        
        # Parse code to AST for deeper analysis
        try:
            tree = ast.parse(code_content)
            await self._analyze_ast(tree, code_content)
        except SyntaxError as e:
            self.add_finding(
                category="Syntax",
                summary=f"Syntax error in code: {str(e)}",
                severity=Severity.CRITICAL,
                recommendation="Fix syntax errors before proceeding with review"
            )
            return self.findings
        
        # Analyze trading-specific algorithms
        await self._analyze_trading_algorithms(code_content)
        
        # Analyze performance issues
        await self._analyze_performance(code_content)
        
        # Analyze logic flaws
        await self._analyze_logic_flaws(code_content)
        
        # Analyze edge cases
        await self._analyze_edge_cases(code_content)
        
        return self.findings
    
    async def _analyze_ast(self, tree: ast.AST, code_content: str):
        """Analyze Abstract Syntax Tree for deeper insights."""
        
        class AlgorithmVisitor(ast.NodeVisitor):
            def __init__(self, agent):
                self.agent = agent
                self.function_complexity = {}
                self.loop_depth = 0
                self.max_loop_depth = 0
            
            def visit_FunctionDef(self, node):
                # Analyze function complexity
                complexity = self._calculate_complexity(node)
                if complexity > 10:
                    self.agent.add_finding(
                        category="Algorithm Complexity",
                        summary=f"High complexity function: {node.name} (complexity: {complexity})",
                        severity=Severity.MEDIUM,
                        recommendation=f"Refactor {node.name} to reduce cyclomatic complexity"
                    )
                self.generic_visit(node)
            
            def visit_For(self, node):
                self.loop_depth += 1
                self.max_loop_depth = max(self.max_loop_depth, self.loop_depth)
                self.generic_visit(node)
                self.loop_depth -= 1
            
            def visit_While(self, node):
                self.loop_depth += 1
                self.max_loop_depth = max(self.max_loop_depth, self.loop_depth)
                self.generic_visit(node)
                self.loop_depth -= 1
            
            def visit_If(self, node):
                # Check for nested if statements (potential logic issues)
                if self.loop_depth > 0:
                    self.agent.add_finding(
                        category="Logic Structure",
                        summary="Nested conditional inside loop detected",
                        severity=Severity.LOW,
                        recommendation="Consider extracting complex conditions to separate functions"
                    )
                self.generic_visit(node)
            
            def _calculate_complexity(self, node):
                """Calculate cyclomatic complexity of a function."""
                complexity = 1  # Base complexity
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                return complexity
        
        visitor = AlgorithmVisitor(self)
        visitor.visit(tree)
        
        # Check for excessive nesting
        if visitor.max_loop_depth > 3:
            self.add_finding(
                category="Algorithm Structure",
                summary=f"Deep nesting detected (max depth: {visitor.max_loop_depth})",
                severity=Severity.MEDIUM,
                recommendation="Consider refactoring to reduce nesting depth"
            )
    
    async def _analyze_trading_algorithms(self, code_content: str):
        """Analyze trading-specific algorithms."""
        
        # Check for price calculation logic
        if re.search(self.trading_patterns["price_calculation"], code_content, re.IGNORECASE):
            self.add_finding(
                category="Trading Algorithm",
                summary="Price calculation logic detected",
                severity=Severity.LOW,
                recommendation="Ensure price calculations handle edge cases (zero prices, negative values)"
            )
        
        # Check for position sizing
        if re.search(self.trading_patterns["position_sizing"], code_content, re.IGNORECASE):
            self.add_finding(
                category="Trading Algorithm",
                summary="Position sizing logic detected",
                severity=Severity.MEDIUM,
                recommendation="Validate position sizing calculations and add risk limits"
            )
        
        # Check for risk calculations
        if re.search(self.trading_patterns["risk_calculation"], code_content, re.IGNORECASE):
            self.add_finding(
                category="Trading Algorithm",
                summary="Risk calculation logic detected",
                severity=Severity.HIGH,
                recommendation="Ensure risk calculations are mathematically correct and handle edge cases"
            )
        
        # Check for signal generation
        if re.search(self.trading_patterns["signal_generation"], code_content, re.IGNORECASE):
            self.add_finding(
                category="Trading Algorithm",
                summary="Trading signal generation detected",
                severity=Severity.HIGH,
                recommendation="Validate signal logic and ensure proper state management"
            )
        
        # Check for backtesting logic
        if re.search(self.trading_patterns["backtesting"], code_content, re.IGNORECASE):
            self.add_finding(
                category="Trading Algorithm",
                summary="Backtesting logic detected",
                severity=Severity.MEDIUM,
                recommendation="Ensure backtesting accounts for realistic execution costs and slippage"
            )
    
    async def _analyze_performance(self, code_content: str):
        """Analyze performance issues and optimization opportunities."""
        
        # Check for nested loops
        if re.search(self.performance_issues["nested_loops"], code_content, re.MULTILINE):
            self.add_finding(
                category="Performance",
                summary="Nested loops detected - potential O(n²) complexity",
                severity=Severity.MEDIUM,
                recommendation="Consider using more efficient algorithms or data structures"
            )
        
        # Check for inefficient search operations
        if re.search(self.performance_issues["inefficient_search"], code_content):
            self.add_finding(
                category="Performance",
                summary="Inefficient search operations detected",
                severity=Severity.MEDIUM,
                recommendation="Use sets or dictionaries for O(1) lookups instead of linear search"
            )
        
        # Check for string concatenation in loops
        if "for" in code_content and "+" in code_content and '"' in code_content:
            self.add_finding(
                category="Performance",
                summary="Potential string concatenation in loop",
                severity=Severity.LOW,
                recommendation="Use join() method for efficient string concatenation"
            )
        
        # Check for missed list comprehension opportunities
        if re.search(self.performance_issues["list_comprehension_missed"], code_content, re.MULTILINE):
            self.add_finding(
                category="Performance",
                summary="List comprehension opportunity detected",
                severity=Severity.LOW,
                recommendation="Consider using list comprehension for better performance"
            )
        
        # Check for unnecessary computations
        if re.search(self.performance_issues["unnecessary_computation"], code_content):
            self.add_finding(
                category="Performance",
                summary="Unnecessary computation detected",
                severity=Severity.LOW,
                recommendation="Use direct boolean evaluation instead of len() > 0"
            )
    
    async def _analyze_logic_flaws(self, code_content: str):
        """Analyze potential logic flaws and bugs."""
        
        # Check for division by zero
        if "/" in code_content or "//" in code_content:
            if "if" not in code_content or "!= 0" not in code_content:
                self.add_finding(
                    category="Logic Flaws",
                    summary="Division operation without zero check",
                    severity=Severity.HIGH,
                    recommendation="Add zero division checks before division operations"
                )
        
        # Check for off-by-one errors in loops
        loop_patterns = [
            r"for\s+\w+\s+in\s+range\(len\(.*\)\)",
            r"for\s+\w+\s+in\s+range\(.*,\s*len\(.*\)\)"
        ]
        for pattern in loop_patterns:
            if re.search(pattern, code_content):
                self.add_finding(
                    category="Logic Flaws",
                    summary="Potential off-by-one error in loop",
                    severity=Severity.MEDIUM,
                    recommendation="Verify loop bounds and indexing logic"
                )
        
        # Check for missing return statements
        function_defs = re.findall(r"def\s+(\w+).*?:\s*(.*?)(?=def|\Z)", code_content, re.DOTALL)
        for func_name, func_body in function_defs:
            if "return" not in func_body and "yield" not in func_body:
                # Check if function should return something
                if "=" in func_body or "calculate" in func_name.lower():
                    self.add_finding(
                        category="Logic Flaws",
                        summary=f"Function {func_name} may be missing return statement",
                        severity=Severity.MEDIUM,
                        recommendation=f"Add return statement to {func_name} if it should return a value"
                    )
        
        # Check for unreachable code
        if "return" in code_content:
            lines = code_content.split('\n')
            for i, line in enumerate(lines):
                if "return" in line and i < len(lines) - 1:
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith(('def ', 'class ', '#', '"', "'")):
                        self.add_finding(
                            category="Logic Flaws",
                            summary="Potential unreachable code after return statement",
                            severity=Severity.MEDIUM,
                            recommendation="Remove unreachable code or restructure logic"
                        )
    
    async def _analyze_edge_cases(self, code_content: str):
        """Analyze edge case handling."""
        
        # Check for empty collection handling
        if "for" in code_content and "in" in code_content:
            if "if" not in code_content or "len(" not in code_content:
                self.add_finding(
                    category="Edge Cases",
                    summary="Loop without empty collection check",
                    severity=Severity.LOW,
                    recommendation="Consider adding checks for empty collections before loops"
                )
        
        # Check for None value handling
        if "None" in code_content:
            if "is None" not in code_content and "is not None" not in code_content:
                self.add_finding(
                    category="Edge Cases",
                    summary="None values used without proper None checks",
                    severity=Severity.MEDIUM,
                    recommendation="Add explicit None checks to prevent AttributeError"
                )
        
        # Check for negative number handling in trading context
        if any(pattern in code_content.lower() for pattern in ["price", "amount", "quantity", "volume"]):
            if "abs(" not in code_content and "max(" not in code_content:
                self.add_finding(
                    category="Edge Cases",
                    summary="Trading values without negative number validation",
                    severity=Severity.MEDIUM,
                    recommendation="Add validation for negative values in trading calculations"
                )
        
        # Check for floating point precision issues
        if "float(" in code_content or "decimal" not in code_content.lower():
            if any(op in code_content for op in ["+", "-", "*", "/"]):
                self.add_finding(
                    category="Edge Cases",
                    summary="Floating point arithmetic without precision handling",
                    severity=Severity.LOW,
                    recommendation="Consider using Decimal for financial calculations to avoid precision issues"
                )
