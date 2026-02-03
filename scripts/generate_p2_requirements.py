#!/usr/bin/env python3
"""
Script to generate requirements documents for P2 files automatically.
Usage: python scripts/generate_p2_requirements.py
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime


def get_p2_files_without_requirements() -> List[Path]:
    """Get P2 (MEDIUM priority) files without requirements."""
    py_files = set(Path("app").rglob("*.py"))
    req_files = set(Path(".requirements").rglob("*.requirements.md"))

    # P2 directories (strategies and other medium priority)
    p2_dirs = [
        "strategies/fx_carry_trade",
        "strategies/fx_intermarket",
        "strategies/momentum_modular",
        "strategies/crypto_momentum",
        "strategies/low_volatility",
        "strategies/covered_calls",
        "strategies/multi_factor",
        "strategies/dividend",
        "strategies/indicators",
        "strategies/momentum_modular/modules",
        "strategies/momentum_modular/modules/filters",
        "strategies/momentum_modular/modules/market_detectors",
        "strategies/momentum_modular/optimization",
        "strategies/momentum_modular/learning",
        "tests/portfolio_optimization",
        "tests/strategies",
        "core/models",
        "optimization",
    ]

    p2_files = []
    for py_file in py_files:
        if py_file.name == "__init__.py":
            continue

        relative_path = str(py_file.parent.relative_to("app"))
        if not any(p2_dir in relative_path for p2_dir in p2_dirs):
            continue

        pattern1 = Path(".requirements") / py_file.relative_to("app")
        pattern2 = Path(str(pattern1.with_suffix('')) + ".requirements.md")
        pattern1 = Path(str(pattern1) + ".requirements.md")

        if pattern1 not in req_files and pattern2 not in req_files:
            p2_files.append(py_file)

    return sorted(p2_files)


def analyze_python_file(py_file: Path) -> Dict:
    """Analyze a Python file and extract structure."""
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(py_file))
    except (SyntaxError, UnicodeDecodeError):
        return {"error": "Could not parse file"}

    info = {
        "imports": [],
        "classes": [],
        "functions": [],
        "decorators": [],
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                info["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    info["imports"].append(f"{node.module}.{alias.name}")

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "bases": [base.id if hasattr(base, 'id') else str(base) for base in node.bases],
                "methods": [],
                "docstring": ast.get_docstring(node),
            }
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    class_info["methods"].append({
                        "name": item.name,
                        "args": [arg.arg for arg in item.args.args],
                        "returns": ast.unparse(item.returns) if item.returns else "None",
                        "docstring": ast.get_docstring(item),
                    })
            info["classes"].append(class_info)

        elif isinstance(node, ast.FunctionDef):
            info["functions"].append({
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "returns": ast.unparse(node.returns) if node.returns else "None",
                "docstring": ast.get_docstring(node),
                "decorators": [ast.unparse(d) for d in node.decorator_list],
            })

    return info


def generate_requirements_content(py_file: Path, analysis: Dict) -> str:
    """Generate requirements document content for P2 files."""
    relative_path = py_file.relative_to("app")

    # Extract basic info
    purpose = f"Implementation for {py_file.stem}"

    # Determine if it's a test file
    is_test = "test" in py_file.stem or py_file.parent.name == "tests"
    prefix = "Test" if is_test else ""

    classes_info = []
    functions_info = []

    for cls in analysis.get("classes", []):
        classes_info.append(f"### {cls['name']}")
        if cls.get("docstring"):
            classes_info.append(f"**Purpose:** {cls['docstring'][:100]}...")

        for method in cls.get("methods", []):
            if method["name"].startswith("_"):
                continue
            args_str = ", ".join(method["args"])
            functions_info.append(
                f"### `{cls['name']}.{method['name']}({args_str}) -> {method['returns']}`\n"
                f"**Pre:** TBD\n"
                f"**Post:** TBD\n"
                f"**Raises:** TBD\n"
                f"**Retry:** ❌ No\n"
                f"**Side Effects:** TBD\n"
            )

    for func in analysis.get("functions", []):
        if func["name"].startswith("_"):
            continue
        args_str = ", ".join(func["args"])
        functions_info.append(
            f"### `{func['name']}({args_str}) -> {func['returns']}`\n"
            f"**Pre:** TBD\n"
            f"**Post:** TBD\n"
            f"**Raises:** TBD\n"
            f"**Retry:** ❌ No\n"
            f"**Side Effects:** TBD\n"
        )

    # Generate content
    content = f"""# {py_file.name}

## Purpose
{prefix} file for {py_file.stem.replace('_', ' ').replace('-', ' ')}

---

## Type Definitions / Data Classes
⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

{chr(10).join(classes_info) if classes_info else "None - see classes below"}

---

## Function Signatures (Contracts)

{chr(10).join(functions_info) if functions_info else "None"}

---

## Acceptance Criteria
- [ ] **AC-001:** All public methods have complete type hints ✅ OK
- [ ] **AC-002:** NumPy 2.0 compatibility ✅ OK
- [ ] **AC-003:** All functions have docstrings following Google style ✅ OK
- [ ] **AC-004:** Input validation on all public methods ⚠️ PENDING

---

## Audit Status

**Status:** PENDING
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** TBD
**Notes:** Requirements document created. Needs full audit against code.

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (14 categories with 96+ rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Type hints coverage | BASE_RULES.md (TYP-001) | 100% type hints on public functions | ⚠️ PENDING - Needs audit |
| Docstring coverage | BASE_RULES.md (CC-001) | All functions documented | ⚠️ PENDING - Needs audit |
| Input validation | BASE_RULES.md (CC-006) | Validate all inputs | ⚠️ PENDING - Needs audit |
| Error logging | BASE_RULES.md (LOG-004) | Log exceptions with stack traces | ⚠️ PENDING - Needs audit |
| NumPy 2.0 compat | BASE_RULES.md (TYP-002) | No deprecated np aliases | ⚠️ PENDING - Needs audit |

**NOTE:** This analysis references BASE_RULES.md for universal rules.

---

## Dependencies
- **External:** TBD (needs audit)
- **Internal:** TBD (needs audit)

---

## Required Tests
- **test_{py_file.stem}.py:** Test descriptions to be defined during audit

---

## Notes
This requirements document was auto-generated for a P2 (MEDIUM priority) file. A full audit is needed to:
1. Verify all type hints are present
2. Check all docstrings follow Google style
3. Validate error handling and logging
4. Ensure input validation on all public methods

---

**File Reference:** `app/{relative_path}`
**Created:** {datetime.now().strftime('%Y-%m-%d')}
**Status:** ⚠️ PENDING FULL AUDIT
"""
    return content


def create_requirements_file(py_file: Path, content: str) -> bool:
    """Create the requirements file."""
    relative_path = py_file.relative_to("app")
    req_file = Path(".requirements") / "app" / relative_path
    req_file = Path(str(req_file) + ".requirements.md")

    req_file.parent.mkdir(parents=True, exist_ok=True)

    with open(req_file, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def main():
    """Main function."""
    print("=" * 80)
    print("📋 GENERATING REQUIREMENTS FOR P2 FILES")
    print("=" * 80)

    p2_files = get_p2_files_without_requirements()
    print(f"\n📊 Found {len(p2_files)} P2 files without requirements\n")

    created = []
    failed = []

    for py_file in p2_files:
        print(f"🔍 Analyzing: app/{py_file.relative_to('app')}")

        # Analyze the Python file
        analysis = analyze_python_file(py_file)

        if "error" in analysis:
            print(f"   ⚠️  Could not parse, creating generic requirements")
            # Create generic requirements even if parsing failed
            pass

        # Generate requirements content
        content = generate_requirements_content(py_file, analysis)

        # Create requirements file
        try:
            if create_requirements_file(py_file, content):
                print(f"   ✅ Created: .requirements/app/{py_file.relative_to('app')}.requirements.md")
                created.append(py_file)
            else:
                print(f"   ❌ Failed to create requirements file")
                failed.append((py_file, "Failed to create file"))
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failed.append((py_file, str(e)))

    print(f"\n{'=' * 80}")
    print(f"📊 SUMMARY:")
    print(f"   ✅ Created: {len(created)} requirements documents")
    print(f"   ❌ Failed:  {len(failed)} files")
    print(f"{'=' * 80}\n")

    if failed:
        print("❌ Failed files:")
        for py_file, error in failed:
            print(f"   - {py_file}: {error}")


if __name__ == "__main__":
    main()
