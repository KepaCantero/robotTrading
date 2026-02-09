#!/usr/bin/env python3
"""
Create batches ONLY for files with broken requirements (placeholders).
"""
import json
from pathlib import Path
from datetime import datetime


def has_placeholders(req_file: Path) -> bool:
    """Check if requirements file has placeholders."""
    if not req_file.exists():
        return False

    content = req_file.read_text()

    # Check for ANY placeholder pattern
    return any(p in content for p in [
        "[Document the purpose",
        "[List internal dependencies]",
        "[List external dependencies]",
        "[Document main classes",
        "[Document core business",
        "[Document data models",
    ])


def count_lines(file_path: Path) -> int:
    """Count lines."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
    except Exception:
        return 0


def main():
    repo_root = Path.cwd()
    req_dir = repo_root / ".requirements"

    # Find ALL files with placeholders
    files_with_placeholders = []

    for req_file in req_dir.rglob("*.requirements.md"):
        if has_placeholders(req_file):
            # Get corresponding Python file path
            rel_req = req_file.relative_to(req_dir)
            py_path = str(rel_req).replace(".requirements.md", "")

            py_file = repo_root / py_path
            if py_file.exists():
                lines = count_lines(py_file)

                # Determine layer from path
                parts = py_path.split("/")
                if parts[0] == "app":
                    if parts[1] == "core":
                        layer = "1_Core"
                    elif parts[1] == "database":
                        layer = "2_Database"
                    elif parts[1] == "domain":
                        if parts[2] == "entities":
                            layer = "3_Domain_Entities"
                        elif parts[2] == "services":
                            layer = "4_Domain_Services"
                        elif parts[2] == "strategies":
                            layer = "5_Domain_Strategies"
                        else:
                            layer = "14_Others"
                    elif parts[1] == "application":
                        layer = "6_Application"
                    elif parts[1] == "backtesting":
                        layer = "7_Backtesting"
                    elif parts[1] == "strategies":
                        layer = "8_Strategies"
                    elif parts[1] == "analysis":
                        layer = "9_Analysis"
                    elif parts[1] == "market_microstructure":
                        layer = "10_Microstructure"
                    elif parts[1] == "api":
                        layer = "11_API"
                    elif parts[1] == "middleware":
                        layer = "12_Middleware"
                    elif parts[1] == "presentation":
                        layer = "13_Presentation"
                    else:
                        layer = "14_Others"
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

                files_with_placeholders.append({
                    "path": py_path,
                    "layer": layer,
                    "lines": lines,
                    "size_category": size_cat,
                })

    print(f"Files with placeholders: {len(files_with_placeholders)}")

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

    sorted_files = sorted(files_with_placeholders, key=sort_key)

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
            "total_files": len(files_with_placeholders),
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
                "total_files": len(files_with_placeholders),
                "total_batches": len(batches),
                "current_batch": "batch_0001",
            },
            "files": {},
            "batches": {},
        }, f, indent=2)

    print(f"\nBatches created: {len(batches)}")
    print(f"Total files: {len(files_with_placeholders)}")
    print(f"Saved to: {batches_file}")


if __name__ == "__main__":
    main()
