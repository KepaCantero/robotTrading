#!/usr/bin/env python3
"""
List files for audit by batch, checking timestamps to skip already-audited files.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


def get_audit_status(req_file: Path) -> dict:
    """Parse audit status from requirements file."""
    if not req_file.exists():
        return {"status": "NO_REQ_FILE", "date": None}

    content = req_file.read_text()

    # Look for Audit Status section
    audit_match = re.search(r'\|\s+\*\*Audit Status\*\*\s+\|\s*(\w+)\s*\|', content)
    date_match = re.search(r'\|\s+\*\*Last Audit Date\*\*\s+\|\s*([\dT:Z\-]+)\s*\|', content)

    status = audit_match.group(1) if audit_match else "NEEDS_AUDIT"
    date_str = date_match.group(1) if date_match else None

    # Parse date
    audit_date = None
    if date_str:
        try:
            audit_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            pass

    return {"status": status, "date": audit_date}


def needs_audit(req_file: Path, max_age_days: int = 7) -> bool:
    """Check if file needs auditing based on timestamp."""
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


def list_batch(repo_root: Path, batch_name: str, patterns: list, max_age_days: int = 7):
    """List files in a batch that need auditing."""
    print(f"\n{'='*60}")
    print(f"Batch: {batch_name}")
    print(f"{'='*60}")

    all_files = []
    needs_audit_files = []

    for pattern in patterns:
        for py_file in (repo_root / "app").glob(pattern):
            if "__pycache__" in str(py_file) or py_file.name.startswith("_"):
                continue

            # Get corresponding requirements file
            rel_path = py_file.relative_to(repo_root / "app")
            req_file = repo_root / ".requirements" / rel_path.with_suffix(".requirements.md")

            all_files.append(py_file)

            if needs_audit(req_file, max_age_days):
                needs_audit_files.append((py_file, req_file, get_audit_status(req_file)))

    print(f"Total files: {len(all_files)}")
    print(f"Files needing audit: {len(needs_audit_files)}")
    print(f"Files already audited (recent): {len(all_files) - len(needs_audit_files)}")

    if needs_audit_files:
        print(f"\nFiles to audit:")
        for py_file, req_file, status_info in needs_audit_files:
            rel_py = py_file.relative_to(repo_root)
            print(f"  - {rel_py}")
            if status_info["date"]:
                print(f"    Last audit: {status_info['date'].strftime('%Y-%m-%d')} ({status_info['status']})")
            else:
                print(f"    Status: {status_info['status']}")
    else:
        print(f"\n✅ All files in this batch are up to date!")

    return needs_audit_files


def main():
    repo_root = Path(__file__).parent.parent

    # Define batches
    batches = {
        "Batch 1: Core Infrastructure": [
            "core/*.py",
            "database/*.py",
        ],
        "Batch 2: Domain Layer": [
            "domain/entities/*.py",
            "domain/services/*.py",
            "domain/strategies/*.py",
        ],
        "Batch 3: Application Layer": [
            "application/**/*.py",
        ],
        "Batch 4: Backtesting": [
            "backtesting/**/*.py",
        ],
        "Batch 5: API & Middleware": [
            "api/*.py",
            "middleware/*.py",
        ],
        "Batch 6: Analysis & Microstructure": [
            "analysis/**/*.py",
            "market_microstructure/**/*.py",
        ],
    }

    # Parse args
    import argparse
    parser = argparse.ArgumentParser(description="List files needing audit by batch")
    parser.add_argument("--batch", type=int, help="Specific batch number (1-6)")
    parser.add_argument("--max-age", type=int, default=7, help="Max age in days for PASSED audits (default: 7)")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    all_needs_audit = {}

    # Process batches
    for batch_name, patterns in batches.items():
        if args.batch:
            batch_num = int(batch_name.split(":")[0].split()[1])
            if batch_num != args.batch:
                continue

        files = list_batch(repo_root, batch_name, patterns, args.max_age)
        if files:
            all_needs_audit[batch_name] = files

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    total_files = sum(len(files) for files in all_needs_audit.values())
    print(f"Total files needing audit: {total_files}")
    for batch_name, files in all_needs_audit.items():
        print(f"  {batch_name}: {len(files)} files")

    # Output list for processing
    if args.format == "text" and all_needs_audit:
        print(f"\n{'='*60}")
        print("FILES TO PROCESS (in order)")
        print(f"{'='*60}")
        for batch_name, files in all_needs_audit.items():
            for py_file, req_file, _ in files:
                rel_py = py_file.relative_to(repo_root)
                print(f"  {rel_py}")

    # JSON output for automation
    if args.format == "json":
        import json
        output = []
        for batch_name, files in all_needs_audit.items():
            for py_file, req_file, status_info in files:
                output.append({
                    "file": str(py_file.relative_to(repo_root)),
                    "requirements": str(req_file.relative_to(repo_root)),
                    "batch": batch_name,
                    "last_audit_status": status_info["status"],
                    "last_audit_date": status_info["date"].isoformat() if status_info["date"] else None,
                })
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
