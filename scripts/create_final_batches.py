#!/usr/bin/env python3
"""
Create CORRECT batches for GAP audit.

ONLY includes:
- Files under app/
- EXCLUDES: test files, __pycache__
- EXCLUDES: Files already PASSED
"""
import json
from datetime import datetime
from pathlib import Path


def should_include_file(py_file: Path) -> bool:
    """Check if file should be included in audit."""
    # Must be under app/
    if "app/" not in str(py_file):
        return False

    # Exclude tests
    if "test" in str(py_file).lower():
        return False

    # Exclude __pycache__
    if "__pycache__" in str(py_file):
        return False

    # Check if already PASSED
    rel_path = py_file.relative_to(Path.cwd())
    req_file = Path.cwd() / ".requirements" / f"{rel_path}".replace(".py", ".requirements.md")
    if req_file.exists():
        content = req_file.read_text()
        if "Audit Status" in content and "PASSED" in content:
            # Also check if the PASSED is recent (last 7 days)
            # and if it was validated with real tools
            return False

    return True


def count_lines(file_path: Path) -> int:
    """Count non-empty lines."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
    except Exception:
        return 0


def main():
    repo_root = Path.cwd()
    app_dir = repo_root / "app"

    files_to_audit = []

    # Find all Python files under app/
    for py_file in sorted(app_dir.rglob("*.py")):
        if should_include_file(py_file):
            lines = count_lines(py_file)

            # Determine layer
            rel_path = py_file.relative_to(repo_root)
            parts = str(rel_path).split('/')

            if 'core' in parts:
                layer = "1_Core"
            elif 'database' in parts:
                layer = "2_Database"
            elif 'domain/entities' in parts:
                layer = "3_Domain_Entities"
            elif 'domain/services' in parts:
                layer = "4_Domain_Services"
            elif 'domain/strategies' in parts:
                layer = "5_Domain_Strategies"
            elif 'application' in parts:
                layer = "6_Application"
            elif 'backtesting' in parts:
                layer = "7_Backtesting"
            elif 'strategies' in parts:
                layer = "8_Strategies"
            elif 'analysis' in parts:
                layer = "9_Analysis"
            elif 'market_microstructure' in parts:
                layer = "10_Microstructure"
            elif 'api' in parts:
                layer = "11_API"
            elif 'middleware' in parts:
                layer = "12_Middleware"
            elif 'presentation' in parts:
                layer = "13_Presentation"
            else:
                layer = "14_Others"

            # Size category
            if lines < 100:
                size_cat = "small"
            elif lines < 300:
                size_cat = "medium"
            elif lines < 600:
                size_cat = "large"
            else:
                size_cat = "xlarge"

            files_to_audit.append({
                "path": str(rel_path),
                "layer": layer,
                "lines": lines,
                "size_category": size_cat,
            })

    print(f"Found {len(files_to_audit)} files to audit")

    # Sort by layer, then size
    layer_order = [
        "1_Core", "2_Database", "3_Domain_Entities", "4_Domain_Services",
        "5_Domain_Strategies", "6_Application", "7_Backtesting", "8_Strategies",
        "9_Analysis", "10_Microstructure", "11_API", "12_Middleware",
        "13_Presentation", "14_Others",
    ]

    def sort_key(f):
        layer_idx = layer_order.index(f["layer"]) if f["layer"] in layer_order else 999
        size_order = {"small": 0, "medium": 1, "large": 2, "xlarge": 3}
        size_idx = size_order.get(f["size_category"], 99)
        return (layer_idx, size_idx, f["path"])

    sorted_files = sorted(files_to_audit, key=sort_key)

    # Create batches
    batches = []
    batch_counter = 1
    current_batch = []
    current_lines = 0
    current_layer = None
    current_size_cat = None

    for file_info in sorted_files:
        max_batch_size = {"small": 20, "medium": 10, "large": 5, "xlarge": 2}.get(file_info["size_category"], 10)

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

    # Save
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
                "validation_mode": "REAL_COMPLETE"
            },
            "files": {},
            "batches": {},
        }, f, indent=2)

    print(f"\nBatches created: {len(batches)}")
    print(f"Total files: {len(files_to_audit)}")
    print(f"Checkpoint reset: {checkpoint_file}")


if __name__ == "__main__":
    main()
