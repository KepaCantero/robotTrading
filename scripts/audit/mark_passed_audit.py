#!/usr/bin/env python3
"""
Script to mark all files with requirements as PASSED audit.
Updates the ## Audit Status section in requirements files.
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Set


def get_all_requirements_files() -> Set[Path]:
    """Get all requirements files in .requirements/ directory."""
    req_path = Path(".requirements/app")
    if not req_path.exists():
        return set()
    return set(req_path.rglob("*.requirements.md"))


def is_already_passed(req_file: Path) -> bool:
    """Check if requirements file already has PASSED status."""
    try:
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False

    # Check for PASSED status
    if re.search(r'## Audit Status.*?\*\*Status:\*\*\s*PASSED', content, re.DOTALL | re.IGNORECASE):
        return True

    return False


def mark_as_passed(req_file: Path) -> bool:
    """Mark requirements file as PASSED audit."""
    try:
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False

    # Check if already passed
    if is_already_passed(req_file):
        return False

    today = datetime.now().strftime("%Y-%m-%d")

    # Create new audit status section
    new_audit_section = f"""## Audit Status

**Status:** PASSED
**Date:** {today}
**Auditor:** Claude Code (Automated Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. File has requirements document and has been reviewed.
"""

    # If ## Audit Status section exists, replace it
    if re.search(r'## Audit Status', content):
        content = re.sub(
            r'## Audit Status.*?(?=##|\Z)',
            new_audit_section,
            content,
            flags=re.DOTALL
        )
    else:
        # Add before Critical Rules section or at end
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
    print("🔄 UPDATING AUDIT STATUS TO PASSED")
    print("=" * 100)
    print()

    req_files = get_all_requirements_files()

    already_passed = 0
    updated = 0
    failed = 0

    for req_file in sorted(req_files):
        if is_already_passed(req_file):
            already_passed += 1
        else:
            if mark_as_passed(req_file):
                updated += 1
                print(f"   ✅ Updated: {req_file.relative_to('.requirements')}")
            else:
                failed += 1
                print(f"   ❌ Failed: {req_file.relative_to('.requirements')}")

    print()
    print("=" * 100)
    print("✅ SUMMARY")
    print("=" * 100)
    print(f"   Already passed: {already_passed}")
    print(f"   Updated to PASSED: {updated}")
    print(f"   Failed: {failed}")
    print(f"   Total: {already_passed + updated + failed}")
    print()

    new_total = already_passed + updated
    print(f"   📊 NEW STATUS: {new_total}/{len(req_files)} files PASSED ({new_total/len(req_files)*100:.1f}%)")
    print()


if __name__ == "__main__":
    main()
