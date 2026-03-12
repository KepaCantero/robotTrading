#!/usr/bin/env python3
"""
Requirements Generator v2.0
Generates requirements files with specific trading rules and SOLID principles.

This version includes:
- Trading rules R1-R29 from rules/trading/64-realistic-retail-trading-rules.md
- SOLID principles from rules/python/03-solid-principles.md
- Domain-specific rules based on file location
"""

import ast
from pathlib import Path
from typing import Dict, List, Set
from dataclasses import dataclass, field


@dataclass
class TradingRules:
    """Trading rules R1-R29 organized by category."""

    CAPITAL_MANAGEMENT = {
        "R1": "Kelly Criterion + Max Position Size (2% max risk per trade, 25% Kelly fraction)",
        "R2": "Drawdown Monitor (15% warning, 25% halt trading, auto cooldown)",
        "R3": "Correlation & Concentration Limits (max positions, sector limits, correlation checks)",
        "R4": "Risk/Reward Ratio Minimum 2:1 (1.5:1 for high probability setups >=80% confidence)",
    }

    BACKTESTING = {
        "R5": "Walk-Forward Analysis (70/30 train/test split, min 50 trades OOS, max 30% degradation)",
        "R6": "Overfitting Prevention (min 30 samples per parameter, purged cross-validation)",
        "R7": "Monte Carlo Risk Analysis (1000 simulations, validate DD within 5-95 percentile)",
    }

    EXECUTION = {
        "R8": "Bid-Ask Spread Management (limit orders <0.1%, market only strong signals)",
        "R9": "Execution Timing (avoid market open/close 15min, optimal 10AM-1PM EST)",
        "R10": "Slippage Monitor (max 0.1% warning, 0.2% reject)",
    }

    POSITION_MANAGEMENT = {
        "R11": "Dynamic Trailing Stop (breakeven at 2R, 50% trailing at 3R)",
        "R12": "Partial Take Profit (50% at 2R, 25% at 3R, 25% at 5R)",
        "R13": "Pyramiding (add to winners only, max 2 additions at 50%/25% of initial)",
    }

    DATA_INFRASTRUCTURE = {
        "R14": "Data Quality Validation (missing values, duplicates, outliers >3std)",
        "R15": "Complete Logging (append-only, correlation ID, every decision logged)",
        "R16": "Daily Reconciliation (system vs broker positions, 0.1% tolerance)",
    }

    PSYCHOLOGY = {
        "R17": "Emotion Control (no rule changes during market hours, cooldown after 3 losses)",
        "R18": "Trade Journal (record every trade with emotional context, weekly analysis)",
    }

    TECHNICAL_ANALYSIS = {
        "R19": "Market Regime Detection (ADX >25=trend, <15=range, select strategy accordingly)",
        "R20": "Multi-Confirmation (min 2 confirmations: signal + volume + market alignment)",
        "R21": "Volume Filter (breakouts need 1.5x avg volume, watch for divergences)",
    }

    ADAPTATION = {
        "R22": "Monthly Review (analyze Sharpe, Sortino, DD, win rate vs benchmark)",
        "R23": "A/B Testing (paper trade changes, >10% improvement required)",
        "R24": "Strategy Diversification (min 2 uncorrelated strategies, max 0.7 correlation)",
    }

    CAPITAL_PHASES = {
        "R25": "Phase 1 (1k-10k): 1% risk, 2 positions max, 2.5:1 R:R, momentum only",
        "R26": "Phase 2 (10k-50k): 1.5% risk, 3 positions max, 2.2:1 R:R, momentum + mean reversion",
        "R27": "Phase 3 (50k-500k): 2% risk, 5 positions max, 2.0:1 R:R, all strategies",
    }

    COMPLIANCE = {
        "R28": "Trade Record Retention (5 years minimum, append-only, monthly reports)",
        "R29": "API Key Security (2FA required, min permissions, 90-day rotation, no withdraw)",
    }


@dataclass
class SOLIDPrinciples:
    """SOLID principles from rules/python/03-solid-principles.md"""

    SRP = "Single Responsibility: One class, one reason to change. Split when class has multiple responsibilities."
    OCP = "Open/Closed: Open for extension, closed for modification. Use interfaces/protocols."
    LSP = "Liskov Substitution: Subtypes must be substitutable for base types without breaking behavior."
    ISP = "Interface Segregation: Small, focused interfaces. Don't force clients to implement unused methods."
    DIP = "Dependency Inversion: Depend on abstractions, not concretions. Use dependency injection."


@dataclass
class PythonRules:
    """Python coding standards from rules/python/"""

    TYPE_HINTS = [
        "Use typing module for all function signatures",
        "Prefer typing.Protocol over ABC for interfaces",
        "Use | for Union types (Python 3.10+)",
        "Avoid Any, use specific types or generics",
        "Return types must be explicit",
    ]

    FORMATTING = [
        "Black formatter (line length 88)",
        "isort for import sorting",
        "Ruff for linting",
        "Docstrings for all public functions/classes",
        "Max 100 characters per line",
    ]

    LOGGING = [
        "Use structured logging (JSON format)",
        "Never log sensitive data (API keys, passwords)",
        "Use correlation IDs for tracing",
        "Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL",
        "Append-only log files for audit trails",
    ]

    SECURITY = [
        "Never hardcode secrets or API keys",
        "Use .env files (gitignored) for credentials",
        "Validate all external inputs",
        "Use parameterized queries (no SQL injection)",
        "Hash passwords with bcrypt/argon2",
    ]

    ASYNC = [
        "Use async/await for I/O operations",
        "Avoid blocking calls in async functions",
        "Use asyncio.gather for concurrent operations",
        "Handle CancelledError properly",
        "Use connection pools for database/API",
    ]


@dataclass
class FileAnalysis:
    """Analysis of a Python file."""

    path: Path
    imports: Set[str] = field(default_factory=set)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)
    domain: str = "general"
    applies_trading_rules: List[str] = field(default_factory=list)


class RequirementsGeneratorV2:
    """Generates comprehensive requirements files with trading rules."""

    def __init__(self, app_dir: Path, output_dir: Path):
        self.app_dir = app_dir
        self.output_dir = output_dir
        self.trading_rules = TradingRules()
        self.solid = SOLIDPrinciples()
        self.python_rules = PythonRules()

        # Domain mapping for trading rules
        self.domain_mapping = {
            "risk": ["R1", "R2", "R3", "R4"],
            "portfolio": ["R1", "R3", "R11", "R12", "R13"],
            "backtest": ["R5", "R6", "R7"],
            "execution": ["R8", "R9", "R10"],
            "position": ["R11", "R12", "R13"],
            "data": ["R14", "R15"],
            "infrastructure": ["R14", "R15", "R16"],
            "strategy": ["R19", "R20", "R21"],
            "signal": ["R19", "R20", "R21"],
            "tax": ["R28"],
            "compliance": ["R28", "R29"],
            "api": ["R29"],
            "security": ["R29"],
            "journal": ["R17", "R18"],
            "analysis": ["R19", "R20", "R21", "R22"],
            "optimization": ["R5", "R6", "R23"],
        }

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """Analyze a Python file to extract components and determine domain."""
        analysis = FileAnalysis(path=file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis.imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        analysis.imports.add(node.module)
                elif isinstance(node, ast.ClassDef):
                    analysis.classes.append(node.name)
                    # Check if it's a Protocol
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "Protocol":
                            analysis.protocols.append(node.name)
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    if not node.name.startswith("_"):
                        analysis.functions.append(node.name)

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        # Determine domain from path
        path_str = str(file_path).lower()
        for domain, rules in self.domain_mapping.items():
            if domain in path_str:
                analysis.domain = domain
                analysis.applies_trading_rules = rules
                break

        # Additional domain detection from content
        if "kelly" in content.lower() or "position_size" in content.lower():
            if "R1" not in analysis.applies_trading_rules:
                analysis.applies_trading_rules.append("R1")
        if "drawdown" in content.lower():
            if "R2" not in analysis.applies_trading_rules:
                analysis.applies_trading_rules.append("R2")
        if "backtest" in content.lower() or "walk_forward" in content.lower():
            for r in ["R5", "R6", "R7"]:
                if r not in analysis.applies_trading_rules:
                    analysis.applies_trading_rules.append(r)
        if "trailing" in content.lower() or "stop_loss" in content.lower():
            if "R11" not in analysis.applies_trading_rules:
                analysis.applies_trading_rules.append("R11")
        if "tax" in content.lower() or "irpf" in content.lower() or "modelo_720" in content.lower():
            if "R28" not in analysis.applies_trading_rules:
                analysis.applies_trading_rules.append("R28")

        return analysis

    def get_all_trading_rules(self) -> Dict[str, str]:
        """Get all trading rules as a single dict."""
        all_rules = {}
        all_rules.update(self.trading_rules.CAPITAL_MANAGEMENT)
        all_rules.update(self.trading_rules.BACKTESTING)
        all_rules.update(self.trading_rules.EXECUTION)
        all_rules.update(self.trading_rules.POSITION_MANAGEMENT)
        all_rules.update(self.trading_rules.DATA_INFRASTRUCTURE)
        all_rules.update(self.trading_rules.PSYCHOLOGY)
        all_rules.update(self.trading_rules.TECHNICAL_ANALYSIS)
        all_rules.update(self.trading_rules.ADAPTATION)
        all_rules.update(self.trading_rules.CAPITAL_PHASES)
        all_rules.update(self.trading_rules.COMPLIANCE)
        return all_rules

    def generate_requirements(self, analysis: FileAnalysis) -> str:
        """Generate comprehensive requirements document."""
        all_rules = self.get_all_trading_rules()

        # Get relative path from app/
        rel_path = analysis.path.relative_to(self.app_dir.parent)

        content = f"""# Requirements Document: {rel_path}

## 1. Module Overview
File: {analysis.path.name}
Domain: {analysis.domain.capitalize()}
Generated: 2026-03-09

## 2. Dependencies
"""
        # Add imports
        if analysis.imports:
            for imp in sorted(analysis.imports):
                content += f"- `{imp}`\n"
        else:
            content += "- No external dependencies detected\n"

        # Add classes and functions
        content += "\n## 3. Core Components\n"
        if analysis.classes:
            content += "### Classes\n"
            for cls in analysis.classes:
                is_protocol = cls in analysis.protocols
                marker = " (Protocol)" if is_protocol else ""
                content += f"- `{cls}`{marker}\n"

        if analysis.functions:
            content += "### Public Functions\n"
            for func in analysis.functions:
                content += f"- `{func}()`\n"

        if analysis.protocols:
            content += "\n### Protocol Interfaces (ISP Compliance)\n"
            for proto in analysis.protocols:
                content += f"- `{proto}`: Defines contract for dependency injection (DIP)\n"

        # SOLID Principles Section
        content += f"""
## 4. SOLID Principles (from rules/python/03-solid-principles.md)

### SRP - Single Responsibility Principle
{self.solid.SRP}
- [ ] This file has ONE primary responsibility
- [ ] Classes have one reason to change

### OCP - Open/Closed Principle
{self.solid.OCP}
- [ ] Uses Protocol interfaces for extension
- [ ] No modification needed for new implementations

### LSP - Liskov Substitution Principle
{self.solid.LSP}
- [ ] Subclasses can replace parent classes without breaking behavior
- [ ] No surprising overrides in child classes

### ISP - Interface Segregation Principle
{self.solid.ISP}
- [ ] Interfaces are small and focused
- [ ] Clients don't depend on methods they don't use

### DIP - Dependency Inversion Principle
{self.solid.DIP}
- [ ] High-level modules depend on abstractions (Protocols)
- [ ] Dependencies injected via __init__ or function parameters

## 5. Python Coding Standards (from rules/python/)

### Type Hints (rules/python/02-type-hints.md)
"""
        for rule in self.python_rules.TYPE_HINTS:
            content += f"- [ ] {rule}\n"

        content += "\n### Formatting (rules/python/01-formatting-style.md)\n"
        for rule in self.python_rules.FORMATTING:
            content += f"- [ ] {rule}\n"

        content += "\n### Logging (rules/python/09-logging-observability.md)\n"
        for rule in self.python_rules.LOGGING:
            content += f"- [ ] {rule}\n"

        content += "\n### Security (rules/trading/28-security-and-secrets.md)\n"
        for rule in self.python_rules.SECURITY:
            content += f"- [ ] {rule}\n"

        # Trading Rules Section
        content += "\n## 6. Trading Rules (from rules/trading/64-realistic-retail-trading-rules.md)\n\n"

        if analysis.applies_trading_rules:
            content += "### Applicable Rules\n\n"
            for rule_id in sorted(set(analysis.applies_trading_rules)):
                if rule_id in all_rules:
                    content += f"#### {rule_id}\n{all_rules[rule_id]}\n\n"
                    content += f"- [ ] Implementation verified\n"
                    content += f"- [ ] Tests pass\n\n"
        else:
            content += "### General Compliance\n"
            content += "This file should comply with all applicable trading rules based on its functionality.\n\n"

        # Add all rules for reference
        content += "### All Trading Rules Reference\n\n"
        content += "| Rule | Category | Description |\n"
        content += "|------|----------|-------------|\n"

        categories = [
            ("Capital Management", self.trading_rules.CAPITAL_MANAGEMENT),
            ("Backtesting", self.trading_rules.BACKTESTING),
            ("Execution", self.trading_rules.EXECUTION),
            ("Position Management", self.trading_rules.POSITION_MANAGEMENT),
            ("Data & Infrastructure", self.trading_rules.DATA_INFRASTRUCTURE),
            ("Psychology", self.trading_rules.PSYCHOLOGY),
            ("Technical Analysis", self.trading_rules.TECHNICAL_ANALYSIS),
            ("Adaptation", self.trading_rules.ADAPTATION),
            ("Capital Phases", self.trading_rules.CAPITAL_PHASES),
            ("Compliance", self.trading_rules.COMPLIANCE),
        ]

        for category, rules in categories:
            for rule_id, description in rules.items():
                # Short description for table
                short_desc = description.split("(")[0].strip()[:50]
                content += f"| {rule_id} | {category} | {short_desc}... |\n"

        # Spain Tax Section
        content += """
## 7. Spain Tax Compliance (from app/services/tax/)

### IRPF Brackets
- 19%: 0 - 6,000 EUR
- 21%: 6,000 - 50,000 EUR
- 23%: 50,000+ EUR

### Modelo 720
- [ ] Foreign assets >50,000 EUR reported
- [ ] Annual declaration by March 31

### Loss Carryforward
- [ ] Losses can offset gains for 4 years
- [ ] Track realized losses separately

## 8. Execution Checklist

### Pre-Deployment
- [ ] All SOLID principles verified
- [ ] Type hints complete and correct
- [ ] Logging implemented
- [ ] Security reviewed (no hardcoded secrets)
- [ ] Trading rules implemented (if applicable)

### Code Quality
- [ ] Black formatting passes
- [ ] isort passes
- [ ] Ruff linting passes
- [ ] Mypy type checking passes (warnings acceptable)

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] Backtesting validation (if strategy)

---
Generated by Requirements Generator v2.0
Reference: rules/trading/64-realistic-retail-trading-rules.md
Reference: rules/python/03-solid-principles.md
"""
        return content

    def process_all_files(self) -> Dict[str, int]:
        """Process all Python files in app/ directory."""
        stats = {"total": 0, "success": 0, "errors": 0}

        python_files = list(self.app_dir.rglob("*.py"))
        stats["total"] = len(python_files)

        print(f"Processing {stats['total']} Python files...")

        for i, file_path in enumerate(python_files, 1):
            try:
                # Analyze file
                analysis = self.analyze_file(file_path)

                # Generate requirements
                requirements = self.generate_requirements(analysis)

                # Determine output path
                rel_path = file_path.relative_to(self.app_dir)
                output_path = self.output_dir / rel_path.parent / f"{file_path.name}.requirements.txt"

                # Create directory if needed
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Write requirements
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(requirements)

                stats["success"] += 1

                if i % 100 == 0:
                    print(f"  Processed {i}/{stats['total']} files...")

            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                stats["errors"] += 1

        return stats


def main():
    """Main entry point."""
    project_root = Path("/Users/kepa.cantero/Projects/algoTrading")
    app_dir = project_root / "app"
    output_dir = project_root / ".requirements" / "app"

    print("=" * 60)
    print("Requirements Generator v2.0")
    print("Including Trading Rules R1-R29 and SOLID Principles")
    print("=" * 60)

    generator = RequirementsGeneratorV2(app_dir, output_dir)
    stats = generator.process_all_files()

    print("\n" + "=" * 60)
    print("Generation Complete!")
    print(f"  Total files: {stats['total']}")
    print(f"  Success: {stats['success']}")
    print(f"  Errors: {stats['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
