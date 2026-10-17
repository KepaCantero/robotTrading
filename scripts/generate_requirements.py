#!/usr/bin/env python3
"""Sync .requirements.txt spec stubs for every Python file in app/.

Usage:
    python scripts/generate_requirements.py           # full sync
    python scripts/generate_requirements.py --dry-run # report only, write nothing

For each app/**/*.py this regenerates .requirements/app/<path>.requirements.txt
(only writing files whose content changed) and deletes stubs whose source file
no longer exists. Universal rules are NOT repeated per file: they live once in
.requirements/BASE_RULES.md and each stub links to it.

Format contract (consumed by scripts/production_audit.py):
    - classes listed as:        - `ClassName`
    - public functions as:      - `function_name()`
Do not change these line formats without updating production_audit.py.
"""

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "app"
REQ_DIR = PROJECT_ROOT / ".requirements" / "app"


def extract_info(filepath: Path) -> dict:
    """Extract imports, classes, and public functions from a Python file using AST."""
    info = {
        "imports": [],
        "classes": [],
        "functions": [],
        "is_init": filepath.name == "__init__.py",
    }

    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
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
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                info["functions"].append(node.name)

    return info


def determine_domain(rel_path: str) -> str:
    """Determine the domain category from the file path."""
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
    for part in rel_path.split("/"):
        if part in domain_map:
            return domain_map[part]
    return "General"


def determine_applicable_rules(rel_path: str) -> list:
    """Determine which trading rules apply based on file content/domain."""
    rules = []

    if "backtesting" in rel_path or "metrics" in rel_path:
        rules.extend(
            [
                (
                    "R5",
                    "Walk-Forward Analysis (70/30 train/test split, min 50 trades OOS, max 30% degradation)",
                ),
                (
                    "R6",
                    "Overfitting Prevention (min 30 samples per parameter, purged cross-validation)",
                ),
                (
                    "R7",
                    "Monte Carlo Risk Analysis (1000 simulations, validate DD within 5-95 percentile)",
                ),
            ]
        )

    if "risk" in rel_path or "drawdown" in rel_path:
        rules.append(("R2", "Drawdown Monitor (15% warning, 25% halt trading, auto cooldown)"))

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
        rules.append(("R28", "Trade Record Retention (keep all records 5+ years)"))

    if "security" in rel_path or "auth" in rel_path or "secret" in rel_path:
        rules.append(("R29", "API Key Security (rotate every 90 days, never in code)"))

    if "data" in rel_path or "persistence" in rel_path:
        rules.extend(
            [
                ("R14", "Data Quality Validation (OHLCV sanity checks, detect gaps/stale data)"),
                ("R15", "Complete Logging (log all decisions, trade journal format)"),
                (
                    "R16",
                    "Daily Reconciliation (compare broker vs internal, alert discrepancies >1%)",
                ),
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
    """Generate a per-file spec stub. Universal rules stay in BASE_RULES.md."""
    filename = Path(rel_path).name
    domain = determine_domain(rel_path)
    applicable_rules = determine_applicable_rules(rel_path)

    lines = []
    lines.append(f"# Requirements Document: app/{rel_path}")
    lines.append("")
    lines.append("## 1. Module Overview")
    lines.append(f"File: {filename}")
    lines.append(f"Domain: {domain}")

    lines.append("")
    lines.append("## 2. Dependencies")
    for imp in sorted(set(info["imports"])):
        lines.append(f"- `{imp}`")

    lines.append("")
    lines.append("## 3. Core Components")
    if info["classes"]:
        lines.append("### Classes")
        for cls in info["classes"]:
            lines.append(f"- `{cls}`")
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

    lines.append("")
    lines.append("## 4. Applicable Trading Rules")
    for rule_id, rule_desc in applicable_rules:
        lines.append("")
        lines.append(f"#### {rule_id}")
        lines.append(rule_desc)
        lines.append("")
        lines.append("- [ ] Implementation verified")
        lines.append("- [ ] Tests pass")

    lines.append("")
    lines.append("---")
    lines.append("Universal rules (SOLID, type hints, formatting, security, logging) live in")
    lines.append(".requirements/BASE_RULES.md and apply to every file.")
    lines.append("Resync this stub with: python scripts/generate_requirements.py")

    return "\n".join(lines) + "\n"


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    # Map every source file to its stub path.
    source_files = {}
    for src in sorted(APP_DIR.rglob("*.py")):
        if "__pycache__" in src.parts:
            continue
        rel = src.relative_to(APP_DIR).as_posix()
        source_files[REQ_DIR / f"{rel}.requirements.txt"] = (rel, src)

    existing_stubs = set(REQ_DIR.rglob("*.requirements.txt"))

    created = updated = unchanged = deleted = 0
    errors = []

    # Regenerate stubs for existing sources (write only on change).
    for req_path, (rel, src) in source_files.items():
        try:
            content = generate_requirements(rel, extract_info(src))
        except OSError as exc:
            errors.append(f"{rel}: {exc}")
            continue

        if req_path in existing_stubs:
            if req_path.read_text(encoding="utf-8") == content:
                unchanged += 1
                continue
            updated += 1
        else:
            created += 1

        if not dry_run:
            req_path.parent.mkdir(parents=True, exist_ok=True)
            req_path.write_text(content, encoding="utf-8")

    # Delete stubs whose source file is gone.
    orphans = existing_stubs - set(source_files)
    for req_path in orphans:
        deleted += 1
        if not dry_run:
            req_path.unlink()

    # Prune directories left empty by deletions.
    if not dry_run:
        for dirpath in sorted(REQ_DIR.rglob("*"), reverse=True):
            if dirpath.is_dir() and not any(dirpath.iterdir()):
                dirpath.rmdir()

    print(f"Sources in app/: {len(source_files)}")
    print(f"Stubs created: {created}, updated: {updated}, unchanged: {unchanged}")
    print(f"Orphaned stubs deleted: {deleted}")
    if errors:
        print("Errors:")
        for err in errors:
            print(f"  {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
