"""
Security & Performance Auditor Agent

Analyzes code for security vulnerabilities and performance issues.
Focuses on common security pitfalls and performance bottlenecks.
"""

import re
from typing import Dict, List, Any
from .base_agent import BaseReviewAgent, ReviewContext, ReviewFinding, Severity


class SecurityAuditor(BaseReviewAgent):
    """
    Security & Performance Auditor identifies security and performance issues.
    
    This agent checks for:
    - Security vulnerabilities (SQL injection, XSS, etc.)
    - Performance bottlenecks
    - Memory leaks and resource management
    - Input validation issues
    - Authentication and authorization problems
    """
    
    def __init__(self):
        super().__init__(
            name="🔒 Security & Performance Auditor",
            description="Identifies security vulnerabilities and performance issues"
        )
        
        # Security vulnerability patterns
        self.security_patterns = {
            "sql_injection": [
                r"execute\s*\(\s*[\"'].*%s.*[\"']",
                r"cursor\.execute\s*\(\s*f\s*[\"'].*\{.*\}.*[\"']",
                r"query\s*=\s*[\"'].*\+.*[\"']"
            ],
            "xss_vulnerability": [
                r"render_template_string\s*\(",
                r"Markup\s*\(",
                r"\.innerHTML\s*="
            ],
            "hardcoded_secrets": [
                r"password\s*=\s*[\"'][^\"']{8,}[\"']",
                r"api_key\s*=\s*[\"'][^\"']{16,}[\"']",
                r"secret\s*=\s*[\"'][^\"']{16,}[\"']",
                r"token\s*=\s*[\"'][^\"']{16,}[\"']"
            ],
            "weak_crypto": [
                r"hashlib\.md5\s*\(",
                r"hashlib\.sha1\s*\(",
                r"DES\s*\(",
                r"MD5\s*\("
            ],
            "insecure_random": [
                r"random\.random\s*\(",
                r"random\.choice\s*\(",
                r"random\.randint\s*\("
            ],
            "path_traversal": [
                r"open\s*\(\s*[\"'].*\+.*[\"']",
                r"file\s*=\s*[\"'].*\+.*[\"']",
                r"\.\.\/"
            ],
            "eval_usage": [
                r"eval\s*\(",
                r"exec\s*\(",
                r"compile\s*\("
            ]
        }
        
        # Performance issue patterns
        self.performance_patterns = {
            "n_plus_one": [
                r"for\s+.*in\s+.*:\s*.*\.get\s*\(",
                r"for\s+.*in\s+.*:\s*.*\.filter\s*\("
            ],
            "inefficient_queries": [
                r"\.all\s*\(\s*\)\s*\.filter",
                r"\.all\s*\(\s*\)\s*\.order_by",
                r"SELECT\s+\*\s+FROM"
            ],
            "memory_leaks": [
                r"global\s+\w+",
                r"\.append\s*\(\s*self\s*\)",
                r"circular\s+reference"
            ],
            "blocking_operations": [
                r"time\.sleep\s*\(",
                r"requests\.get\s*\(",
                r"urllib\.request\.urlopen"
            ],
            "inefficient_loops": [
                r"for\s+.*in\s+range\s*\(\s*len\s*\(",
                r"while\s+True:",
                r"for\s+.*in\s+.*:\s*for\s+.*in\s+.*:"
            ]
        }
    
    async def analyze(self, code_content: str, context: ReviewContext) -> List[ReviewFinding]:
        """Analyze code for security and performance issues."""
        self.clear_findings()
        
        # Analyze security vulnerabilities
        await self._analyze_security_vulnerabilities(code_content)
        
        # Analyze performance issues
        await self._analyze_performance_issues(code_content)
        
        # Analyze input validation
        await self._analyze_input_validation(code_content)
        
        # Analyze authentication and authorization
        await self._analyze_auth_issues(code_content)
        
        # Analyze resource management
        await self._analyze_resource_management(code_content)
        
        return self.findings
    
    async def _analyze_security_vulnerabilities(self, code_content: str):
        """Check for common security vulnerabilities."""
        
        # SQL Injection
        for pattern in self.security_patterns["sql_injection"]:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Security",
                    summary="Potential SQL injection vulnerability detected",
                    severity=Severity.CRITICAL,
                    recommendation="Use parameterized queries or ORM methods instead of string concatenation"
                )
                break
        
        # XSS Vulnerabilities
        for pattern in self.security_patterns["xss_vulnerability"]:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Security",
                    summary="Potential XSS vulnerability detected",
                    severity=Severity.HIGH,
                    recommendation="Sanitize user input and use template escaping"
                )
                break
        
        # Hardcoded secrets
        for pattern in self.security_patterns["hardcoded_secrets"]:
            matches = re.findall(pattern, code_content, re.IGNORECASE)
            if matches:
                self.add_finding(
                    category="Security",
                    summary=f"Hardcoded secrets detected: {len(matches)} instances",
                    severity=Severity.CRITICAL,
                    recommendation="Move secrets to environment variables or secure configuration"
                )
                break
        
        # Weak cryptography
        for pattern in self.security_patterns["weak_crypto"]:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Security",
                    summary="Weak cryptographic algorithm detected",
                    severity=Severity.HIGH,
                    recommendation="Use strong cryptographic algorithms (SHA-256, bcrypt, etc.)"
                )
                break
        
        # Insecure random
        for pattern in self.security_patterns["insecure_random"]:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Security",
                    summary="Insecure random number generation detected",
                    severity=Severity.MEDIUM,
                    recommendation="Use secrets module for cryptographically secure random numbers"
                )
                break
        
        # Path traversal
        for pattern in self.security_patterns["path_traversal"]:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Security",
                    summary="Potential path traversal vulnerability detected",
                    severity=Severity.HIGH,
                    recommendation="Validate and sanitize file paths, use os.path.join()"
                )
                break
        
        # Code execution
        for pattern in self.security_patterns["eval_usage"]:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Security",
                    summary="Dangerous code execution function detected",
                    severity=Severity.CRITICAL,
                    recommendation="Avoid eval(), exec(), and compile() with user input"
                )
                break
    
    async def _analyze_performance_issues(self, code_content: str):
        """Check for performance bottlenecks."""
        
        # N+1 query problem
        for pattern in self.performance_patterns["n_plus_one"]:
            if re.search(pattern, code_content, re.MULTILINE):
                self.add_finding(
                    category="Performance",
                    summary="Potential N+1 query problem detected",
                    severity=Severity.HIGH,
                    recommendation="Use eager loading or batch queries to reduce database calls"
                )
                break
        
        # Inefficient database queries
        for pattern in self.performance_patterns["inefficient_queries"]:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Performance",
                    summary="Inefficient database query detected",
                    severity=Severity.MEDIUM,
                    recommendation="Optimize queries with proper indexing and selective field loading"
                )
                break
        
        # Memory leaks
        for pattern in self.performance_patterns["memory_leaks"]:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Performance",
                    summary="Potential memory leak detected",
                    severity=Severity.MEDIUM,
                    recommendation="Review object lifecycle and avoid circular references"
                )
                break
        
        # Blocking operations
        for pattern in self.performance_patterns["blocking_operations"]:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Performance",
                    summary="Blocking I/O operation detected",
                    severity=Severity.MEDIUM,
                    recommendation="Use async/await for I/O operations to avoid blocking"
                )
                break
        
        # Inefficient loops
        for pattern in self.performance_patterns["inefficient_loops"]:
            if re.search(pattern, code_content, re.MULTILINE):
                self.add_finding(
                    category="Performance",
                    summary="Inefficient loop structure detected",
                    severity=Severity.LOW,
                    recommendation="Optimize loop structure or use more efficient algorithms"
                )
                break
    
    async def _analyze_input_validation(self, code_content: str):
        """Check for input validation issues."""
        
        # Check for user input handling
        input_patterns = [
            r"request\.(get|post|args|form|json)",
            r"input\s*\(",
            r"sys\.argv",
            r"environ\s*\["
        ]
        
        has_input = any(re.search(pattern, code_content, re.IGNORECASE) for pattern in input_patterns)
        
        if has_input:
            # Check for validation
            validation_patterns = [
                r"validate\s*\(",
                r"isinstance\s*\(",
                r"len\s*\(",
                r"strip\s*\(",
                r"escape\s*\("
            ]
            
            has_validation = any(re.search(pattern, code_content, re.IGNORECASE) for pattern in validation_patterns)
            
            if not has_validation:
                self.add_finding(
                    category="Security",
                    summary="User input detected without validation",
                    severity=Severity.HIGH,
                    recommendation="Add input validation and sanitization for all user inputs"
                )
        
        # Check for file upload handling
        if "upload" in code_content.lower() or "file" in code_content.lower():
            if "content_type" not in code_content and "mimetype" not in code_content:
                self.add_finding(
                    category="Security",
                    summary="File upload without content type validation",
                    severity=Severity.HIGH,
                    recommendation="Validate file types and content to prevent malicious uploads"
                )
        
        # Check for command injection
        command_patterns = [
            r"os\.system\s*\(",
            r"subprocess\.call\s*\(",
            r"subprocess\.run\s*\(",
            r"shell\s*=\s*True"
        ]
        
        for pattern in command_patterns:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Security",
                    summary="Command execution with potential injection risk",
                    severity=Severity.CRITICAL,
                    recommendation="Avoid shell execution or properly sanitize command arguments"
                )
                break
    
    async def _analyze_auth_issues(self, code_content: str):
        """Check for authentication and authorization issues."""
        
        # Check for authentication
        auth_patterns = [
            r"@login_required",
            r"authenticate\s*\(",
            r"login\s*\(",
            r"session\s*\["
        ]
        
        has_auth = any(re.search(pattern, code_content, re.IGNORECASE) for pattern in auth_patterns)
        
        if has_auth:
            # Check for session security
            if "session" in code_content.lower():
                if "secure" not in code_content.lower() and "httponly" not in code_content.lower():
                    self.add_finding(
                        category="Security",
                        summary="Session configuration without security flags",
                        severity=Severity.MEDIUM,
                        recommendation="Configure secure and httponly flags for session cookies"
                    )
            
            # Check for password handling
            if "password" in code_content.lower():
                if "hash" not in code_content.lower() and "bcrypt" not in code_content.lower():
                    self.add_finding(
                        category="Security",
                        summary="Password handling without hashing",
                        severity=Severity.CRITICAL,
                        recommendation="Always hash passwords using bcrypt or similar secure methods"
                    )
        
        # Check for authorization
        if "admin" in code_content.lower() or "role" in code_content.lower():
            if "permission" not in code_content.lower() and "authorize" not in code_content.lower():
                self.add_finding(
                    category="Security",
                    summary="Role-based access without proper authorization checks",
                    severity=Severity.HIGH,
                    recommendation="Implement proper authorization checks for role-based access"
                )
    
    async def _analyze_resource_management(self, code_content: str):
        """Check for resource management issues."""
        
        # Check for file handling
        if "open(" in code_content:
            if "with open(" not in code_content and "try:" not in code_content:
                self.add_finding(
                    category="Performance",
                    summary="File operations without proper resource management",
                    severity=Severity.MEDIUM,
                    recommendation="Use context managers (with statement) for file operations"
                )
        
        # Check for database connections
        if "connect(" in code_content or "connection" in code_content.lower():
            if "close(" not in code_content and "with" not in code_content:
                self.add_finding(
                    category="Performance",
                    summary="Database connections without proper cleanup",
                    severity=Severity.MEDIUM,
                    recommendation="Ensure database connections are properly closed or use connection pooling"
                )
        
        # Check for memory-intensive operations
        memory_patterns = [
            r"\.read\s*\(\s*\)",
            r"\.load\s*\(\s*\)",
            r"list\s*\(\s*.*\.all\s*\(\s*\)\s*\)"
        ]
        
        for pattern in memory_patterns:
            if re.search(pattern, code_content, re.IGNORECASE):
                self.add_finding(
                    category="Performance",
                    summary="Memory-intensive operation detected",
                    severity=Severity.LOW,
                    recommendation="Consider streaming or pagination for large data operations"
                )
                break
        
        # Check for thread safety
        if "thread" in code_content.lower() or "multiprocessing" in code_content.lower():
            if "lock" not in code_content.lower() and "mutex" not in code_content.lower():
                self.add_finding(
                    category="Performance",
                    summary="Concurrent operations without synchronization",
                    severity=Severity.MEDIUM,
                    recommendation="Add proper synchronization mechanisms for thread-safe operations"
                )
