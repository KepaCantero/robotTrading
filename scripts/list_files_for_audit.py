#!/usr/bin/env python3
"""
List files for audit in LAYER ORDER (bottom-up by dependencies).

Finds files that need auditing based on Audit Status in .requirements.md:
- Files with "Audit Status: NEEDS_AUDIT"
- Files with "Audit Status: FAILED"
- Files with "Audit Status: PASSED" but older than N days

Layer order (lowest to highest):
1. Core → 2. Database → 3. Domain Entities → 4. Domain Services → 5. Application → ...
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


def get_audit_status(req_file: Path) -> dict:
    """Parse audit status from requirements file."""
    if not req_file.exists():
        return {"status": "NO_REQ_FILE", "date": None}

    content = req_file.read_text()

    # Look for Audit Status in multiple formats:
    # 1. Table format: | **Audit Status** | **PASSED** |
    # 2. Text format: **Audit Status:** PASSED
    # 3. List format: - Audit Status: NEEDS_AUDIT
    audit_match = re.search(r'\|\s+\*\*Audit Status\*\*\s+\|\s*\*?\*?(\w+)\*?\*?\s*\|', content)
    if not audit_match:
        audit_match = re.search(r'\*\*Audit Status\*\*:\s*(\w+)', content)
    if not audit_match:
        audit_match = re.search(r'- Audit Status:\s*(\w+)', content)

    date_match = re.search(r'\|\s+\*\*Last Audit Date\*\*\s+\|\s*([\dT:Z\-+:]+)\s*\|', content)

    status = audit_match.group(1) if audit_match else "NEEDS_AUDIT"
    date_str = date_match.group(1) if date_match else None

    # Parse date
    audit_date = None
    if date_str:
        try:
            # Handle ISO 8601 format
            date_str = date_str.replace('Z', '+00:00')
            audit_date = datetime.fromisoformat(date_str)
            # Ensure it's timezone-aware
            if audit_date.tzinfo is None:
                audit_date = audit_date.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    return {"status": status, "date": audit_date}


def needs_audit(req_file: Path, max_age_days: int = 7) -> bool:
    """Check if file needs auditing."""
    info = get_audit_status(req_file)

    # No requirements file → needs audit
    if info["status"] == "NO_REQ_FILE":
        return True

    # Status is NEEDS_AUDIT or FAILED → needs audit
    if info["status"] in ["NEEDS_AUDIT", "FAILED"]:
        return True

    # Status is PASSED but old → needs audit
    if info["status"] == "PASSED" and info["date"]:
        age = datetime.now(timezone.utc) - info["date"]
        if age > timedelta(days=max_age_days):
            return True

    # Status is PASSED and recent → skip
    return False


def main():
    repo_root = Path(__file__).parent.parent
    app_dir = repo_root / "app"

    # Define layers in ORDER (bottom-up)
    layers = [
        ("1_Core", ["app/core/*.py"]),
        ("2_Database", ["app/database/*.py", "app/database/**/*.py"]),
        ("3_Domain_Entities", ["app/domain/entities/*.py"]),
        ("4_Domain_Services", ["app/domain/services/*.py"]),
        ("5_Domain_Strategies", ["app/domain/strategies/*.py"]),
        ("6_Application", ["app/application/**/*.py"]),
        ("7_Backtesting", ["app/backtesting/**/*.py"]),
        ("8_Strategies", ["app/strategies/**/*.py"]),
        ("9_Analysis", ["app/analysis/**/*.py"]),
        ("10_Microstructure", ["app/market_microstructure/**/*.py"]),
        ("11_API", ["app/api/*.py"]),
        ("12_Middleware", ["app/middleware/*.py"]),
        ("13_Presentation", ["app/presentation/**/*.py"]),
        ("14_Others", ["app/**/*.py"]),
    ]

    # Parse args
    import argparse
    parser = argparse.ArgumentParser(description="List files needing audit in layer order")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--max-age", type=int, default=7, help="Max age in days for PASSED audits")
    args = parser.parse_args()

    all_needs_audit = []
    processed_files = set()

    # Process layers IN ORDER
    for layer_name, patterns in layers:
        for pattern in patterns:
            for py_file in sorted(app_dir.glob(pattern.replace("app/", ""))):
                # Skip test files and __pycache__
                if "__pycache__" in str(py_file) or py_file.name.startswith("_") or "test" in py_file.parts:
                    continue

                # Skip if already processed
                if py_file in processed_files:
                    continue

                processed_files.add(py_file)

                # Get corresponding requirements file
                # Format: .requirements/app/core/auth.py.requirements.md
                rel_path = py_file.relative_to(repo_root)
                req_file = repo_root / ".requirements" / f"{rel_path}.requirements.md"

                if needs_audit(req_file, args.max_age):
                    status_info = get_audit_status(req_file)
                    all_needs_audit.append((layer_name, py_file, req_file, status_info))

    # Summary
    if args.format == "text":
        print(f"\n{'='*60}")
        print(f"Total files needing audit: {len(all_needs_audit)}")
        print(f"{'='*60}\n")
        for layer, py_file, _, status_info in all_needs_audit:
            rel_py = py_file.relative_to(repo_root)
            print(f"  - {rel_py} [{status_info['status']}]")

    # JSON output
    if args.format == "json":
        import json
        output = []
        for layer, py_file, req_file, status_info in all_needs_audit:
            output.append({
                "layer": layer,
                "file": str(py_file.relative_to(repo_root)),
                "status": status_info["status"],
                "last_audit_date": status_info["date"].isoformat() if status_info["date"] else None,
            })
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
