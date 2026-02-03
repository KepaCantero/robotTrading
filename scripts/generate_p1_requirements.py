#!/usr/bin/env python3
"""
Script to generate requirements documents for P1 files automatically.
Usage: python scripts/generate_p1_requirements.py
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime


def get_p1_files_without_requirements() -> List[Path]:
    """Get P1 (HIGH priority) files without requirements."""
    py_files = set(Path("app").rglob("*.py"))
    req_files = set(Path(".requirements").rglob("*.requirements.md"))

    p1_dirs = [
        "backtesting/acceptance",
        "backtesting/services",
        "services/risk_scaling_application",
        "tests/backtesting",
        "services/backtesting_orchestration",
    ]

    p1_files = []
    for py_file in py_files:
        if py_file.name == "__init__.py":
            continue

        relative_path = str(py_file.parent.relative_to("app"))
        if not any(p1_dir in relative_path for p1_dir in p1_dirs):
            continue

        pattern1 = Path(".requirements") / py_file.relative_to("app")
        pattern2 = Path(str(pattern1.with_suffix('')) + ".requirements.md")
        pattern1 = Path(str(pattern1) + ".requirements.md")

        if pattern1 not in req_files and pattern2 not in req_files:
            p1_files.append(py_file)

    return sorted(p1_files)


def analyze_python_file(py_file: Path) -> Dict:
    """Analyze a Python file and extract structure."""
    with open(py_file, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=str(py_file))
        except SyntaxError as e:
            return {"error": str(e)}

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
            methods = []
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
    """Generate requirements document content."""
    relative_path = py_file.relative_to("app")

    # Extract basic info
    purpose = f"Implementation for {py_file.stem}"
    classes_info = []
    functions_info = []

    for cls in analysis.get("classes", []):
        classes_info.append(f"### {cls['name']}")
        if cls.get("docstring"):
            classes_info.append(f"**Purpose:** {cls['docstring'][:100]}...")
        for method in cls.get("methods", []):
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
{purpose}

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
| Domain layer purity | BASE_RULES.md (ARCH-002) | No infrastructure imports (if domain) | ⚠️ PENDING - Needs audit |
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
This requirements document was auto-generated. A full audit is needed to:
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
    print("📋 GENERATING REQUIREMENTS FOR P1 FILES")
    print("=" * 80)

    p1_files = get_p1_files_without_requirements()
    print(f"\n📊 Found {len(p1_files)} P1 files without requirements\n")

    created = []
    failed = []

    for py_file in p1_files:
        print(f"🔍 Analyzing: app/{py_file.relative_to('app')}")

        # Analyze the Python file
        analysis = analyze_python_file(py_file)

        if "error" in analysis:
            print(f"   ❌ ERROR: {analysis['error']}")
            failed.append((py_file, analysis["error"]))
            continue

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
