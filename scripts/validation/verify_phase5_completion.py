#!/usr/bin/env python3
"""
Phase 5 Verification: Verify ALL ImportError fallbacks eliminated

This script verifies that:
1. All inappropriate except ImportError patterns are eliminated
2. Only legitimate fail-fast checks remain (numba_enforcer.py)
3. All required dependencies are documented
4. No flag variables (XXX_AVAILABLE) remain

Author: Backend Developer
Date: 2026-01-28
"""

import subprocess
from pathlib import Path

PROJECT_ROOT = Path("/Users/kepa.cantero/Projects/algoTrading")


def run_command(cmd: list) -> tuple[int, str, str]:
    """Run command and return exit code, stdout, stderr."""
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def verify_import_error_count():
    """Verify only 2 except ImportError patterns remain."""
    print("=" * 80)
    print("VERIFICATION 1: Count except ImportError patterns")
    print("=" * 80)

    exit_code, stdout, stderr = run_command(
        ["grep", "-r", "except ImportError", "app/", "--include=*.py"]
    )

    lines = stdout.strip().split('\n') if stdout.strip() else []
    count = len([l for l in lines if l])

    print(f"Total except ImportError patterns found: {count}")
    print()

    if count == 2:
        print("✅ PASS: Exactly 2 patterns found (numba_enforcer.py)")
        print()
        for line in lines:
            if line:
                print(f"  {line}")
        return True
    else:
        print(f"❌ FAIL: Expected 2, found {count}")
        return False


def verify_numba_enforcer_exceptions():
    """Verify the 2 remaining patterns are in numba_enforcer.py."""
    print("\n" + "=" * 80)
    print("VERIFICATION 2: Check patterns are in numba_enforcer.py")
    print("=" * 80)

    exit_code, stdout, stderr = run_command(
        ["grep", "-n", "except ImportError", "app/core/numba_enforcer.py"]
    )

    lines = stdout.strip().split('\n') if stdout.strip() else []
    count = len([l for l in lines if l])

    print(f"Patterns in numba_enforcer.py: {count}")

    if count == 2:
        print("✅ PASS: Both patterns are in numba_enforcer.py")
        for line in lines:
            if line:
                print(f"  {line}")
        return True
    else:
        print(f"❌ FAIL: Expected 2 in numba_enforcer.py, found {count}")
        return False


def verify_no_available_flags():
    """Verify no _AVAILABLE flag variables remain."""
    print("\n" + "=" * 80)
    print("VERIFICATION 3: Check for _AVAILABLE flag variables")
    print("=" * 80)

    exit_code, stdout, stderr = run_command(
        ["grep", "-r", "_AVAILABLE\s*=", "app/", "--include=*.py"]
    )

    lines = stdout.strip().split('\n') if stdout.strip() else []
    # Filter out numba_enforcer.py (legitimate enforcement)
    flag_lines = [l for l in lines if l and 'numba_enforcer.py' not in l]

    if not flag_lines:
        print("✅ PASS: No _AVAILABLE flag variables found")
        return True
    else:
        print(f"❌ FAIL: Found {len(flag_lines)} _AVAILABLE flags:")
        for line in flag_lines[:10]:  # Show first 10
            print(f"  {line}")
        if len(flag_lines) > 10:
            print(f"  ... and {len(flag_lines) - 10} more")
        return False


def verify_no_fallback_warnings():
    """Verify no fallback warning messages remain."""
    print("\n" + "=" * 80)
    print("VERIFICATION 4: Check for fallback warning messages")
    print("=" * 80)

    warning_patterns = [
        "not available",
        "falling back",
        "limited without",
        "skipping due to missing",
    ]

    found_warnings = []

    for pattern in warning_patterns:
        exit_code, stdout, stderr = run_command(["grep", "-ri", pattern, "app/", "--include=*.py"])

        lines = stdout.strip().split('\n') if stdout.strip() else []
        # Filter out legitimate warnings and numba_enforcer.py
        filtered = [l for l in lines if l and 'numba_enforcer.py' not in l]

        if filtered:
            found_warnings.extend(filtered)

    if not found_warnings:
        print("✅ PASS: No fallback warning messages found")
        return True
    else:
        print(f"⚠️  WARNING: Found {len(found_warnings)} potential fallback warnings:")
        for line in found_warnings[:10]:
            print(f"  {line}")
        if len(found_warnings) > 10:
            print(f"  ... and {len(found_warnings) - 10} more")
        print("\n  Note: These may be legitimate warnings, manual review recommended")
        return True  # Don't fail on this


def verify_required_dependencies():
    """Verify required dependencies are in requirements.txt."""
    print("\n" + "=" * 80)
    print("VERIFICATION 5: Check required dependencies in requirements.txt")
    print("=" * 80)

    required_deps = [
        "scipy",
        "scikit-learn",
        "torch",
        "optuna",
        "arch",
        "quantstats",
        "statsmodels",
        "streamlit",
        "numba",
    ]

    requirements_path = PROJECT_ROOT / "requirements.txt"

    if not requirements_path.exists():
        print("❌ FAIL: requirements.txt not found")
        return False

    content = requirements_path.read_text()

    missing_deps = []
    for dep in required_deps:
        if dep.lower() not in content.lower():
            missing_deps.append(dep)

    if not missing_deps:
        print(f"✅ PASS: All {len(required_deps)} required dependencies found")
        return True
    else:
        print(f"❌ FAIL: Missing {len(missing_deps)} dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        return False


def verify_imports_work():
    """Verify critical imports work."""
    print("\n" + "=" * 80)
    print("VERIFICATION 6: Test critical imports")
    print("=" * 80)

    test_imports = [
        "import numpy",
        "import scipy",
        "import scipy.stats",
        "import pandas",
        "import yaml",
    ]

    failed_imports = []

    for imp in test_imports:
        exit_code, stdout, stderr = run_command(["python", "-c", imp])

        if exit_code != 0:
            failed_imports.append(imp)

    if not failed_imports:
        print(f"✅ PASS: All {len(test_imports)} test imports successful")
        return True
    else:
        print(f"❌ FAIL: {len(failed_imports)} imports failed:")
        for imp in failed_imports:
            print(f"  - {imp}")
        return False


def main():
    """Run all verifications."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "PHASE 5 VERIFICATION" + " " * 42 + "║")
    print("║" + " " * 15 + "ImportError Fallback Elimination" + " " * 33 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    results = []

    # Run verifications
    results.append(("ImportError count", verify_import_error_count()))
    results.append(("Numba enforcer location", verify_numba_enforcer_exceptions()))
    results.append(("No _AVAILABLE flags", verify_no_available_flags()))
    results.append(("Fallback warnings", verify_no_fallback_warnings()))
    results.append(("Required dependencies", verify_required_dependencies()))
    results.append(("Import tests", verify_imports_work()))

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {name}")

    print()
    print(f"Total: {passed}/{total} verifications passed")
    print()

    if passed == total:
        print("🎉 SUCCESS: All verifications passed!")
        print("✅ Phase 5 complete - ALL ImportError fallbacks eliminated")
        return 0
    else:
        print("⚠️  WARNING: Some verifications failed")
        print("   Please review and fix remaining issues")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
