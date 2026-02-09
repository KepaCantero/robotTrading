#!/usr/bin/env python3
"""
Recreate batches excluding PASSED files and files with placeholders.
"""
import json
import re
from pathlib import Path
from datetime import datetime


def has_placeholders(req_file: Path) -> bool:
    """Check if requirements file has placeholders."""
    if not req_file.exists():
        return True  # No requirements = needs audit

    content = req_file.read_text()

    # Check for placeholders
    placeholders = [
        r"\[Document the purpose",
        r"\[List internal dependencies\]",
        r"\[List external dependencies\]",
        r"\[Document main classes",
        r"\[Document core business",
        r"\[Document data models",
        r"\[Document API contracts",
    ]

    for pattern in placeholders:
        if re.search(pattern, content):
            return True

    return False


def is_passed(req_file: Path) -> bool:
    """Check if file is marked as PASSED."""
    if not req_file.exists():
        return False

    content = req_file.read_text()

    # Look for PASSED status
    passed_match = re.search(r'\|\s+\*\*Audit Status\*\*\s+\|\s*\*?\*?PASSED\*?\*?\s*\|', content)
    if not passed_match:
        passed_match = re.search(r'\*\*Audit Status\*\*:\s*PASSED', content)

    return bool(passed_match)


def needs_audit(req_file: Path) -> bool:
    """Check if file needs auditing."""
    # Has placeholders → needs audit
    if has_placeholders(req_file):
        return True

    # Is PASSED → doesn't need audit
    if is_passed(req_file):
        return False

    # Has NEEDS_AUDIT or FAILED status → needs audit
    if req_file.exists():
        content = req_file.read_text()
        audit_match = re.search(r'\|\s+\*\*Audit Status\*\*\s+\|\s*\*?\*?(\w+)\*?\*?\s*\|', content)
        if audit_match:
            status = audit_match.group(1)
            if status in ["NEEDS_AUDIT", "FAILED"]:
                return True

    # Default: needs audit
    return True


def count_lines(file_path: Path) -> int:
    """Count non-empty lines in a Python file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
    except Exception:
        return 0


def categorize_by_size(lines: int) -> str:
    """Categorize file by line count."""
    if lines < 100:
        return "small"
    elif lines < 300:
        return "medium"
    elif lines < 600:
        return "large"
    return "xlarge"


def main():
    """Main entry point."""
    print("=" * 60)
    print("RECREATING BATCHES - CLEAN VERSION")
    print("=" * 60)

    repo_root = Path.cwd()
    app_dir = repo_root / "app"

    # Layers in order
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

    # Collect files that need audit
    files_to_audit = []
    processed = set()

    for layer_name, patterns in layers:
        for pattern in patterns:
            for py_file in sorted(app_dir.glob(pattern.replace("app/", ""))):
                if "__pycache__" in str(py_file) or py_file.name.startswith("_") or "test" in py_file.parts:
                    continue
                if py_file in processed:
                    continue

                processed.add(py_file)

                # Get requirements file
                rel_path = py_file.relative_to(repo_root)
                req_file = repo_root / ".requirements" / f"{rel_path}.requirements.md"

                # Check if needs audit
                if needs_audit(req_file):
                    lines = count_lines(py_file)
                    size_cat = categorize_by_size(lines)

                    reason = []
                    if has_placeholders(req_file):
                        reason.append("placeholders")
                    if req_file.exists() and not is_passed(req_file):
                        content = req_file.read_text()
                        if "NEEDS_AUDIT" in content:
                            reason.append("needs_audit")
                        if "FAILED" in content:
                            reason.append("failed")
                    if not req_file.exists():
                        reason.append("no_req_file")

                    files_to_audit.append({
                        "path": str(rel_path),
                        "layer": layer_name,
                        "lines": lines,
                        "size_category": size_cat,
                        "reason": reason,
                    })

    print(f"\nFiles needing audit: {len(files_to_audit)}")

    # Show breakdown
    print("\nBreakdown by reason:")
    by_reason = {}
    for f in files_to_audit:
        for r in f["reason"]:
            by_reason[r] = by_reason.get(r, 0) + 1
    for reason, count in sorted(by_reason.items()):
        print(f"  {reason}: {count}")

    print("\nBreakdown by layer:")
    by_layer = {}
    for f in files_to_audit:
        layer = f["layer"]
        by_layer[layer] = by_layer.get(layer, 0) + 1
    for layer, count in sorted(by_layer.items()):
        print(f"  {layer}: {count}")

    # Create batches
    print("\nCreating batches...")
    layer_order = [l[0] for l in layers]

    def sort_key(f):
        layer_idx = layer_order.index(f["layer"]) if f["layer"] in layer_order else 999
        size_order = {"small": 0, "medium": 1, "large": 2, "xlarge": 3}
        size_idx = size_order.get(f["size_category"], 99)
        return (layer_idx, size_idx, f["path"])

    sorted_files = sorted(files_to_audit, key=sort_key)

    batches = []
    batch_counter = 1
    current_batch = []
    current_lines = 0
    current_layer = None
    current_size_cat = None

    for file_info in sorted_files:
        max_batch_size = {
            "small": 20,
            "medium": 10,
            "large": 5,
            "xlarge": 2,
        }.get(file_info["size_category"], 10)

        need_new_batch = (
            current_layer != file_info["layer"] or
            (current_size_cat and current_size_cat != file_info["size_category"] and len(current_batch) >= max_batch_size // 2) or
            len(current_batch) >= max_batch_size
        )

        if need_new_batch and current_batch:
            batches.append({
                "batch_id": f"batch_{batch_counter:04d}",
                "layer": current_layer,
                "files": [f["path"] for f in current_batch],
                "file_count": len(current_batch),
                "total_lines": current_lines,
                "size_category": current_size_cat,
                "estimated_time_minutes": max(2, current_lines // 100),
                "status": "pending",
            })
            batch_counter += 1
            current_batch = []
            current_lines = 0

        current_batch.append(file_info)
        current_lines += file_info["lines"]
        current_layer = file_info["layer"]
        current_size_cat = file_info["size_category"]

    if current_batch:
        batches.append({
            "batch_id": f"batch_{batch_counter:04d}",
            "layer": current_layer,
            "files": [f["path"] for f in current_batch],
            "file_count": len(current_batch),
            "total_lines": current_lines,
            "size_category": current_size_cat,
            "estimated_time_minutes": max(2, current_lines // 100),
            "status": "pending",
        })

    # Save batches
    ralph_dir = repo_root / ".ralph"
    ralph_dir.mkdir(exist_ok=True)

    batches_file = ralph_dir / "batches.json"
    with open(batches_file, "w") as f:
        json.dump({
            "created_at": datetime.utcnow().isoformat() + "Z",
            "total_files": len(files_to_audit),
            "total_batches": len(batches),
            "estimated_total_time_minutes": sum(b["estimated_time_minutes"] for b in batches),
            "batches": batches,
        }, f, indent=2)

    # Reset checkpoint
    checkpoint_file = ralph_dir / "checkpoint_progress.json"
    with open(checkpoint_file, "w") as f:
        json.dump({
            "meta": {
                "started_at": datetime.utcnow().isoformat() + "Z",
                "total_files": len(files_to_audit),
                "total_batches": len(batches),
                "current_batch": "batch_0001",
            },
            "files": {},
            "batches": {},
        }, f, indent=2)

    print(f"\nSaved to {batches_file}")
    print(f"Reset checkpoint: {checkpoint_file}")

    # Summary
    print("\n" + "=" * 60)
    print("BATCH RECREATION COMPLETE")
    print("=" * 60)
    print(f"Total files needing audit: {len(files_to_audit)}")
    print(f"Total batches: {len(batches)}")
    print(f"Est. time: {sum(b['estimated_time_minutes'] for b in batches)} minutes")
    print("=" * 60)


if __name__ == "__main__":
    main()
