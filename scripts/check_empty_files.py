#!/usr/bin/env python3
"""
Script to find and mark empty/minimal files that should NOT be PASSED.
"""

import re
from pathlib import Path
from datetime import datetime


def get_all_requirements_files():
    """Get all requirements files."""
    req_path = Path(".requirements/app")
    if not req_path.exists():
        return []
    return list(req_path.rglob("*.requirements.md"))


def get_py_file_from_req(req_file):
    """Get corresponding Python file from requirements file."""
    rel = str(req_file.relative_to(".requirements/app"))
    py_rel = rel.replace(".requirements.md", "")
    return Path("app") / py_rel


def is_file_empty_or_minimal(py_file):
    """Check if Python file is empty or has minimal content."""
    if not py_file.exists():
        return True, "File does not exist"

    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return True, "Could not read file"

    lines = content.strip().split('\n')

    # Filter out comments and docstrings
    code_lines = []
    in_docstring = False
    docstring_char = None

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Handle docstrings
        if '"""' in stripped or "'''" in stripped:
            if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                # Single line docstring
                continue
            in_docstring = not in_docstring
            if in_docstring:
                docstring_char = '"""' if '"""' in stripped else "'''"
            continue

        if in_docstring:
            if docstring_char in stripped:
                in_docstring = False
            continue

        # Skip comment lines
        if stripped.startswith('#'):
            continue

        code_lines.append(stripped)

    # Check if file is empty
    if len(code_lines) == 0:
        return True, "Empty file (only docstring/comments)"

    # Check if file is minimal (less than 10 meaningful lines)
    if len(code_lines) < 10:
        return True, f"Minimal file ({len(code_lines)} lines of code)"

    return False, f"Has {len(code_lines)} lines of code"


def mark_as_not_passed(req_file, reason):
    """Mark requirements file as NOT PASSED."""
    try:
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False

    today = datetime.now().strftime("%Y-%m-%d")

    # Update audit status
    new_audit_section = f"""## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** {today}
**Auditor:** Claude Code (Automated Check)
**Reason:** {reason}
**Action Required:** Implement proper code or remove file.
"""

    # Replace or add audit status
    if re.search(r'## Audit Status', content):
        content = re.sub(
            r'## Audit Status.*?(?=##|\Z)',
            new_audit_section,
            content,
            flags=re.DOTALL
        )
    else:
        if re.search(r'## Critical Rules', content):
            content = re.sub(
                r'(## Critical Rules)',
                new_audit_section + '\n\n\\1',
                content
            )
        else:
            content = content + '\n\n' + new_audit_section

    # Write back
    try:
        with open(req_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception:
        return False


def main():
    """Main function."""
    print("=" * 100)
    print("🔍 CHECKING FOR EMPTY/MINIMAL FILES MARKED AS PASSED")
    print("=" * 100)
    print()

    req_files = get_all_requirements_files()

    empty_or_minimal = []
    passed_but_empty = []

    for req_file in req_files:
        py_file = get_py_file_from_req(req_file)

        # Check if file is empty/minimal
        is_empty, reason = is_file_empty_or_minimal(py_file)

        if is_empty:
            empty_or_minimal.append((py_file, req_file, reason))

            # Check if it's marked as PASSED
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if re.search(r'## Audit Status.*?\*\*Status:\*\*\s*PASSED', content, re.DOTALL | re.IGNORECASE):
                    passed_but_empty.append((py_file, req_file, reason))
                    print(f"   ⚠️  {py_file} - {reason}")
            except Exception:
                pass

    print()
    print("=" * 100)
    print(f"📊 RESULTS")
    print("=" * 100)
    print(f"   Empty/Minimal files found: {len(empty_or_minimal)}")
    print(f"   Marked as PASSED but empty: {len(passed_but_empty)}")
    print()

    if passed_but_empty:
        print("=" * 100)
        print("🔄 MARKING AS NOT PASSED")
        print("=" * 100)

        for py_file, req_file, reason in passed_but_empty:
            if mark_as_not_passed(req_file, reason):
                print(f"   ✅ Updated: {py_file}")
            else:
                print(f"   ❌ Failed: {py_file}")

    print()
    print("=" * 100)
    print("✅ COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()
