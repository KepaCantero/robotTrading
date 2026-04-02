#!/usr/bin/env python3
"""Generate .requirements.txt files for Python files missing them."""

import ast
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path("/Users/kepa.cantero/Projects/algoTrading")
APP_DIR = PROJECT_ROOT / "app"
REQ_DIR = PROJECT_ROOT / ".requirements" / "app"

# Files missing requirements (from the comm diff)
MISSING_FILES = [
    "application/alerting/__init__.py",
    "backtesting/drift_detection/__init__.py",
    "backtesting/reports/__init__.py",
    "backtesting/test_summary.py",
    "core/models/__init__.py",
    "core/protocols/signal_scoring.py",
    "domain/engines/__init__.py",
    "domain/engines/execution_engine.py",
    "domain/engines/portfolio_construction_engine.py",
    "domain/engines/rebalance_engine.py",
    "domain/engines/tax_optimization_engine.py",
    "domain/services/execution/__init__.py",
    "domain/services/risk/validators/__init__.py",
    "domain/strategies/covered_call_strategy/__init__.py",
    "domain/strategies/covered_call_strategy/covered_call.py",
    "domain/strategies/covered_call_strategy/greeks_calculator.py",
    "domain/strategies/covered_call_strategy/models.py",
    "domain/strategies/covered_call_strategy/option_screener.py",
    "domain/strategies/covered_call_strategy/position_manager.py",
    "domain/strategies/covered_call_strategy/roll_analyzer.py",
    "domain/strategies/covered_call_strategy/strategy.py",
    "domain/strategies/fx_carry_trade/__init__.py",
    "domain/strategies/fx_carry_trade/carry_calculator.py",
    "domain/strategies/fx_carry_trade/fx_rates_provider.py",
    "domain/strategies/fx_carry_trade/models.py",
    "domain/strategies/fx_intermarket/__init__.py",
    "domain/strategies/fx_intermarket/correlation_analyzer.py",
    "domain/strategies/fx_intermarket/models.py",
    "infrastructure/execution/execution_adapter.py",
    "infrastructure/execution/order_manager_adapter.py",
    "infrastructure/execution/trading_bridge_adapter.py",
    "infrastructure/monitoring/__init__.py",
    "infrastructure/persistence/database/_analytics_repositories.py",
    "infrastructure/persistence/database/_base_repository.py",
    "infrastructure/persistence/database/_trading_repositories.py",
    "infrastructure/persistence/database/_user_portfolio_repositories.py",
    "infrastructure/persistence/tax/__init__.py",
    "infrastructure/persistence/tax/fifo_schema.py",
    "models/__init__.py",
    "presentation/api/api_helpers.py",
    "security/_internal/test_refactoring.py",
    "security/_internal/verify_refactoring.py",
    "security/authentication/__init__.py",
    "security/authentication/auth_attempt_tracker.py",
    "security/authentication/auth.py",
    "security/authentication/jwt_token_manager.py",
    "security/authentication/user_store.py",
    "security/authentication/user.py",
    "security/interfaces.py",
    "security/secrets/__init__.py",
    "security/secrets/secret_manager.py",
    "security/secrets/secrets_manager.py",
    "security/secrets/secure_serialization.py",
    "security/web_security/__init__.py",
    "security/web_security/csrf_protection.py",
    "security/web_security/output_encoding.py",
    "security/web_security/security_headers.py",
    "services/_strategy_stock_allocator.py",
    "services/automated_backtest.py",
    "services/compliance/compliance_engine.py",
    "services/compliance/service_registry.py",
    "services/hurst_analysis/hurst_calculations.py",
    "services/multi_strategy_optimizer_v2.py",
    "services/multi_strategy_optimizer.py",
    "services/portfolio_analytics/__init__.py",
    "services/portfolio_analytics/_performance_calculations.py",
    "services/portfolio_analytics/_portfolio_calculations.py",
    "services/portfolio_analytics/_risk_calculations.py",
    "services/portfolio_analytics/service.py",
    "services/strategy_stock_allocator/__init__.py",
    "shared/config/base/__init__.py",
    "shared/config/base/base.py",
    "shared/config/base/defaults.py",
    "shared/config/base/environment_config.py",
    "shared/config/cache.py",
    "shared/config/legacy_wrapper.py",
    "shared/config/loaders.py",
    "shared/config/mergers.py",
    "shared/config/protocols.py",
    "shared/config/validators.py",
    "shared/protocols/i_data_feed.py",
    "sre/data_integrity/__init__.py",
    "sre/reconciliation/__init__.py",
    "sre/state_machine/__init__.py",
]


def extract_info(filepath: Path) -> dict:
    """Extract imports, classes, and functions from a Python file using AST."""
    info = {
        "imports": [],
        "classes": [],
        "functions": [],
        "is_init": filepath.name == "__init__.py",
    }

    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return info

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                info["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                info["imports"].append(node.module)
        elif isinstance(node, ast.ClassDef):
            info["classes"].append(node.name)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            if not node.name.startswith("_"):
                info["functions"].append(node.name)

    return info


def determine_domain(rel_path: str) -> str:
    """Determine the domain category from the file path."""
    parts = rel_path.split("/")
    domain_map = {
        "backtesting": "Backtest",
        "domain": "Domain",
        "engines": "Engine",
        "infrastructure": "Infrastructure",
        "presentation": "Presentation",
        "security": "Security",
        "services": "Service",
        "shared": "Shared",
        "simulation": "Simulation",
        "sre": "SRE",
        "models": "Models",
        "core": "Core",
        "api": "API",
        "application": "Application",
    }
    for part in parts:
        if part in domain_map:
            return domain_map[part]
    return "General"


def determine_applicable_rules(rel_path: str) -> list:
    """Determine which trading rules apply based on file content/domain."""
    rules = []

    if "backtesting" in rel_path or "metrics" in rel_path:
        rules.extend(
            [
                ("R5", "Walk-Forward Analysis (70/30 train/test split, min 50 trades OOS, max 30% degradation)"),
                ("R6", "Overfitting Prevention (min 30 samples per parameter, purged cross-validation)"),
                ("R7", "Monte Carlo Risk Analysis (1000 simulations, validate DD within 5-95 percentile)"),
            ]
        )

    if "risk" in rel_path or "drawdown" in rel_path:
        rules.append(
            ("R2", "Drawdown Monitor (15% warning, 25% halt trading, auto cooldown)")
        )

    if "execution" in rel_path or "trading" in rel_path or "order" in rel_path:
        rules.extend(
            [
                ("R8", "Bid-Ask Spread Management (avoid market orders for low-liquidity)"),
                ("R9", "Execution Timing (avoid first/last 15 min, VWAP/TWAP for large orders)"),
                ("R10", "Slippage Monitor (track actual vs expected fill, alert if >0.5%)"),
            ]
        )

    if "position" in rel_path or "portfolio" in rel_path:
        rules.extend(
            [
                ("R1", "Kelly Criterion + Max Position Size (max 5% per position)"),
                ("R3", "Correlation & Concentration Limits (max 20% per sector)"),
                ("R11", "Dynamic Trailing Stop (ATR-based, never loosen)"),
            ]
        )

    if "tax" in rel_path or "fifo" in rel_path:
        rules.append(
            ("R28", "Trade Record Retention (keep all records 5+ years)")
        )

    if "security" in rel_path or "auth" in rel_path or "secret" in rel_path:
        rules.append(
            ("R29", "API Key Security (rotate every 90 days, never in code)")
        )

    if "data" in rel_path or "persistence" in rel_path:
        rules.extend(
            [
                ("R14", "Data Quality Validation (OHLCV sanity checks, detect gaps/stale data)"),
                ("R15", "Complete Logging (log all decisions, trade journal format)"),
                ("R16", "Daily Reconciliation (compare broker vs internal, alert discrepancies >1%)"),
            ]
        )

    if "strategy" in rel_path or "signal" in rel_path:
        rules.extend(
            [
                ("R19", "Market Regime Detection (trend/range/volatile classification)"),
                ("R20", "Multi-Confirmation (min 2 independent signals before trade)"),
                ("R24", "Strategy Diversification (min 3 uncorrelated strategies)"),
            ]
        )

    if "capital" in rel_path or "allocation" in rel_path:
        rules.extend(
            [
                ("R25", "Phase 1: 5K-15K EUR, max 3 positions, 2% risk/trade"),
                ("R26", "Phase 2: 15K-50K EUR, max 5 positions, 1.5% risk/trade"),
                ("R27", "Phase 3: 50K+ EUR, max 10 positions, 1% risk/trade"),
            ]
        )

    if not rules:
        rules.append(("R15", "Complete Logging (log all decisions, trade journal format)"))

    return rules


def generate_requirements(rel_path: str, info: dict) -> str:
    """Generate a requirements document for a file."""
    filename = Path(rel_path).name
    domain = determine_domain(rel_path)
    applicable_rules = determine_applicable_rules(rel_path)

    # Clean up imports - remove duplicates and sort
    imports = sorted(set(info["imports"]))
    internal_imports = [i for i in imports if i.startswith("app.") or i.startswith("app ")]
    external_imports = [i for i in imports if not i.startswith("app.") and not i.startswith("app ")]

    lines = []
    lines.append(f"# Requirements Document: app/{rel_path}")
    lines.append("")
    lines.append("## 1. Module Overview")
    lines.append(f"File: {filename}")
    lines.append(f"Domain: {domain}")
    lines.append("Generated: 2026-04-02")

    # Dependencies
    lines.append("")
    lines.append("## 2. Dependencies")
    for imp in sorted(imports):
        lines.append(f"- `{imp}`")

    # Core Components
    lines.append("")
    lines.append("## 3. Core Components")
    if info["classes"]:
        lines.append("### Classes")
        for cls in info["classes"]:
            lines.append(f"- `{cls}()`")
    if info["functions"]:
        lines.append("### Public Functions")
        for func in info["functions"]:
            lines.append(f"- `{func}()`")

    if not info["classes"] and not info["functions"]:
        if info["is_init"]:
            lines.append("### Module Initialization")
            lines.append("- Package/module initialization file")
        else:
            lines.append("### No public exports detected")

    # SOLID Principles
    lines.append("")
    lines.append("## 4. SOLID Principles (from rules/python/03-solid-principles.md)")
    lines.append("")
    lines.append("### SRP - Single Responsibility Principle")
    lines.append("Single Responsibility: One class, one reason to change. Split when class has multiple responsibilities.")
    lines.append("- [ ] This file has ONE primary responsibility")
    lines.append("- [ ] Classes have one reason to change")
    lines.append("")
    lines.append("### OCP - Open/Closed Principle")
    lines.append("Open/Closed: Open for extension, closed for modification. Use interfaces/protocols.")
    lines.append("- [ ] Uses Protocol interfaces for extension")
    lines.append("- [ ] No modification needed for new implementations")
    lines.append("")
    lines.append("### LSP - Liskov Substitution Principle")
    lines.append("Liskov Substitution: Subtypes must be substitutable for base types without breaking behavior.")
    lines.append("- [ ] Subclasses can replace parent classes without breaking behavior")
    lines.append("- [ ] No surprising overrides in child classes")
    lines.append("")
    lines.append("### ISP - Interface Segregation Principle")
    lines.append("Interface Segregation: Small, focused interfaces. Don't force clients to implement unused methods.")
    lines.append("- [ ] Interfaces are small and focused")
    lines.append("- [ ] Clients don't depend on methods they don't use")
    lines.append("")
    lines.append("### DIP - Dependency Inversion Principle")
    lines.append("Dependency Inversion: Depend on abstractions, not concretions. Use dependency injection.")
    lines.append("- [ ] High-level modules depend on abstractions (Protocols)")
    lines.append("- [ ] Dependencies injected via __init__ or function parameters")

    # Python Coding Standards
    lines.append("")
    lines.append("## 5. Python Coding Standards (from rules/python/)")
    lines.append("")
    lines.append("### Type Hints (rules/python/02-type-hints.md)")
    lines.append("- [ ] Use typing module for all function signatures")
    lines.append("- [ ] Prefer typing.Protocol over ABC for interfaces")
    lines.append("- [ ] Use | for Union types (Python 3.10+)")
    lines.append("- [ ] Avoid Any, use specific types or generics")
    lines.append("- [ ] Return types must be explicit")
    lines.append("")
    lines.append("### Formatting (rules/python/01-formatting-style.md)")
    lines.append("- [ ] Black formatter (line length 88)")
    lines.append("- [ ] isort for import sorting")
    lines.append("- [ ] Ruff for linting")
    lines.append("- [ ] Docstrings for all public functions/classes")
    lines.append("- [ ] Max 100 characters per line")
    lines.append("")
    lines.append("### Logging (rules/python/09-logging-observability.md)")
    lines.append("- [ ] Use structured logging (JSON format)")
    lines.append("- [ ] Never log sensitive data (API keys, passwords)")
    lines.append("- [ ] Use correlation IDs for tracing")
    lines.append("- [ ] Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    lines.append("- [ ] Append-only log files for audit trails")
    lines.append("")
    lines.append("### Security (rules/trading/28-security-and-secrets.md)")
    lines.append("- [ ] Never hardcode secrets or API keys")
    lines.append("- [ ] Use .env files (gitignored) for credentials")
    lines.append("- [ ] Validate all external inputs")
    lines.append("- [ ] Use parameterized queries (no SQL injection)")
    lines.append("- [ ] Hash passwords with bcrypt/argon2")

    # Trading Rules
    lines.append("")
    lines.append("## 6. Trading Rules (from rules/trading/64-realistic-retail-trading-rules.md)")
    lines.append("")
    lines.append("### Applicable Rules")
    for rule_id, rule_desc in applicable_rules:
        lines.append("")
        lines.append(f"#### {rule_id}")
        lines.append(rule_desc)
        lines.append("")
        lines.append("- [ ] Implementation verified")
        lines.append("- [ ] Tests pass")

    # Trading Rules Reference Table
    lines.append("")
    lines.append("### All Trading Rules Reference")
    lines.append("")
    lines.append("| Rule | Category | Description |")
    lines.append("|------|----------|-------------|")
    lines.append("| R1 | Capital Management | Kelly Criterion + Max Position Size... |")
    lines.append("| R2 | Capital Management | Drawdown Monitor... |")
    lines.append("| R3 | Capital Management | Correlation & Concentration Limits... |")
    lines.append("| R4 | Capital Management | Risk/Reward Ratio Minimum 2:1... |")
    lines.append("| R5 | Backtesting | Walk-Forward Analysis... |")
    lines.append("| R6 | Backtesting | Overfitting Prevention... |")
    lines.append("| R7 | Backtesting | Monte Carlo Risk Analysis... |")
    lines.append("| R8 | Execution | Bid-Ask Spread Management... |")
    lines.append("| R9 | Execution | Execution Timing... |")
    lines.append("| R10 | Execution | Slippage Monitor... |")
    lines.append("| R11 | Position Management | Dynamic Trailing Stop... |")
    lines.append("| R12 | Position Management | Partial Take Profit... |")
    lines.append("| R13 | Position Management | Pyramiding... |")
    lines.append("| R14 | Data & Infrastructure | Data Quality Validation... |")
    lines.append("| R15 | Data & Infrastructure | Complete Logging... |")
    lines.append("| R16 | Data & Infrastructure | Daily Reconciliation... |")
    lines.append("| R17 | Psychology | Emotion Control... |")
    lines.append("| R18 | Psychology | Trade Journal... |")
    lines.append("| R19 | Technical Analysis | Market Regime Detection... |")
    lines.append("| R20 | Technical Analysis | Multi-Confirmation... |")
    lines.append("| R21 | Technical Analysis | Volume Filter... |")
    lines.append("| R22 | Adaptation | Monthly Review... |")
    lines.append("| R23 | Adaptation | A/B Testing... |")
    lines.append("| R24 | Adaptation | Strategy Diversification... |")
    lines.append("| R25 | Capital Phases | Phase 1... |")
    lines.append("| R26 | Capital Phases | Phase 2... |")
    lines.append("| R27 | Capital Phases | Phase 3... |")
    lines.append("| R28 | Compliance | Trade Record Retention... |")
    lines.append("| R29 | Compliance | API Key Security... |")

    # Spain Tax
    lines.append("")
    lines.append("## 7. Spain Tax Compliance (from app/services/tax/)")
    lines.append("")
    lines.append("### IRPF Brackets")
    lines.append("- 19%: 0 - 6,000 EUR")
    lines.append("- 21%: 6,000 - 50,000 EUR")
    lines.append("- 23%: 50,000+ EUR")
    lines.append("")
    lines.append("### Modelo 720")
    lines.append("- [ ] Foreign assets >50,000 EUR reported")
    lines.append("- [ ] Annual declaration by March 31")
    lines.append("")
    lines.append("### Loss Carryforward")
    lines.append("- [ ] Losses can offset gains for 4 years")
    lines.append("- [ ] Track realized losses separately")

    # Execution Checklist
    lines.append("")
    lines.append("## 8. Execution Checklist")
    lines.append("")
    lines.append("### Pre-Deployment")
    lines.append("- [ ] All SOLID principles verified")
    lines.append("- [ ] Type hints complete and correct")
    lines.append("- [ ] Logging implemented")
    lines.append("- [ ] Security reviewed (no hardcoded secrets)")
    lines.append("- [ ] Trading rules implemented (if applicable)")
    lines.append("")
    lines.append("### Code Quality")
    lines.append("- [ ] Black formatting passes")
    lines.append("- [ ] isort passes")
    lines.append("- [ ] Ruff linting passes")
    lines.append("- [ ] Mypy type checking passes (warnings acceptable)")
    lines.append("")
    lines.append("### Testing")
    lines.append("- [ ] Unit tests pass")
    lines.append("- [ ] Integration tests pass (if applicable)")
    lines.append("- [ ] Backtesting validation (if strategy)")
    lines.append("")
    lines.append("---")
    lines.append("Generated by Requirements Generator v2.0")
    lines.append("Reference: rules/trading/64-realistic-retail-trading-rules.md")
    lines.append("Reference: rules/python/03-solid-principles.md")

    return "\n".join(lines)


def main():
    generated = 0
    errors = 0

    for rel_path in MISSING_FILES:
        source_path = APP_DIR / rel_path
        req_path = REQ_DIR / f"{rel_path}.requirements.txt"

        if not source_path.exists():
            print(f"SKIP: {rel_path} (source does not exist)")
            errors += 1
            continue

        if req_path.exists():
            print(f"SKIP: {rel_path} (requirements already exist)")
            continue

        # Create directory if needed
        req_path.parent.mkdir(parents=True, exist_ok=True)

        # Extract info and generate
        info = extract_info(source_path)
        content = generate_requirements(rel_path, info)

        req_path.write_text(content, encoding="utf-8")
        print(f"OK: {rel_path} -> {req_path.name}")
        generated += 1

    print(f"\nGenerated: {generated}, Skipped/Errors: {errors}")

    # Verify coverage
    py_count = sum(
        1
        for f in APP_DIR.rglob("*.py")
        if "__pycache__" not in str(f)
    )
    req_count = sum(1 for f in REQ_DIR.rglob("*.requirements.txt"))
    coverage = (req_count / py_count * 100) if py_count > 0 else 0
    print(f"Python files: {py_count}, Requirements: {req_count}, Coverage: {coverage:.1f}%")


if __name__ == "__main__":
    main()
