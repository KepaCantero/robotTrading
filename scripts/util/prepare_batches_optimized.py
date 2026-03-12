#!/usr/bin/env python3
"""
Prepare optimized batches for GAP audit with ralph-orchestrator.

Groups files by layer and size, creates batches suitable for parallel processing.
"""
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List


@dataclass
class FileInfo:
    """Information about a file to audit."""
    path: str
    layer: str
    lines: int
    size_category: str  # small, medium, large, xlarge
    has_requirements: bool
    audit_status: str


@dataclass
class Batch:
    """A batch of files to audit together."""
    batch_id: str
    layer: str
    files: List[str]
    total_lines: int
    size_category: str
    estimated_time_minutes: int = field(init=False)

    def __post_init__(self):
        # Estimate time: 1 min per 100 lines, minimum 2 minutes
        self.estimated_time_minutes = max(2, self.total_lines // 100)

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "layer": self.layer,
            "files": self.files,
            "file_count": len(self.files),
            "total_lines": self.total_lines,
            "size_category": self.size_category,
            "estimated_time_minutes": self.estimated_time_minutes,
            "status": "pending",
        }


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


def get_files_to_audit() -> List[FileInfo]:
    """Get all files that need auditing."""
    result = subprocess.run(
        ["python", "scripts/list_files_for_audit.py", "--format", "json"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
    )

    if result.returncode != 0:
        print(f"Error getting files: {result.stderr}")
        return []

    data = json.loads(result.stdout)
    files = []

    for item in data:
        py_file = Path.cwd() / item["file"]
        lines = count_lines(py_file)
        size_cat = categorize_by_size(lines)

        files.append(FileInfo(
            path=item["file"],
            layer=item["layer"],
            lines=lines,
            size_category=size_cat,
            has_requirements=True,  # All have requirements now
            audit_status=item["status"],
        ))

    return files


def create_batches(files: List[FileInfo]) -> List[Batch]:
    """Create optimized batches from file list."""
    # Sort files by layer first, then by size category
    layer_order = [
        "1_Core", "2_Database", "3_Domain_Entities", "4_Domain_Services",
        "5_Domain_Strategies", "6_Application", "7_Backtesting", "8_Strategies",
        "9_Analysis", "10_Microstructure", "11_API", "12_Middleware",
        "13_Presentation", "14_Others",
    ]

    def layer_sort_key(f: FileInfo) -> tuple:
        layer_idx = layer_order.index(f.layer) if f.layer in layer_order else 999
        # Within same layer, sort by size category to group similar sizes
        size_order = {"small": 0, "medium": 1, "large": 2, "xlarge": 3}
        size_idx = size_order.get(f.size_category, 99)
        return (layer_idx, size_idx, f.path)

    sorted_files = sorted(files, key=layer_sort_key)

    batches = []
    batch_counter = 1
    current_batch = []
    current_lines = 0
    current_layer = None
    current_size_cat = None

    for file_info in sorted_files:
        # Get max batch size for this file's size category
        max_batch_size = {
            "small": 20,
            "medium": 10,
            "large": 5,
            "xlarge": 2,
        }.get(file_info.size_category, 10)

        # Create new batch if:
        # 1. Layer changed, OR
        # 2. Size category changed significantly, OR
        # 3. Batch is full
        need_new_batch = (
            current_layer != file_info.layer or
            (current_size_cat and current_size_cat != file_info.size_category and len(current_batch) >= max_batch_size // 2) or
            len(current_batch) >= max_batch_size
        )

        if need_new_batch and current_batch:
            # Save current batch
            batches.append(Batch(
                batch_id=f"batch_{batch_counter:04d}",
                layer=current_layer,
                files=[f.path for f in current_batch],
                total_lines=current_lines,
                size_category=current_size_cat,
            ))
            batch_counter += 1
            current_batch = []
            current_lines = 0

        current_batch.append(file_info)
        current_lines += file_info.lines
        current_layer = file_info.layer
        current_size_cat = file_info.size_category

    # Don't forget the last batch
    if current_batch:
        batches.append(Batch(
            batch_id=f"batch_{batch_counter:04d}",
            layer=current_layer,
            files=[f.path for f in current_batch],
            total_lines=current_lines,
            size_category=current_size_cat,
        ))

    return batches


def main():
    """Main entry point."""
    print("=" * 60)
    print("PREPARING OPTIMIZED BATCHES FOR GAP AUDIT")
    print("=" * 60)

    # Get files to audit
    print("\n[1/3] Getting files to audit...")
    files = get_files_to_audit()
    print(f"Found {len(files)} files needing audit")

    if not files:
        print("No files to audit. Exiting.")
        return

    # Show breakdown by layer
    print("\nFiles by layer:")
    layer_counts: Dict[str, int] = {}
    for f in files:
        layer_counts[f.layer] = layer_counts.get(f.layer, 0) + 1
    for layer, count in sorted(layer_counts.items()):
        print(f"  {layer}: {count} files")

    # Create batches
    print("\n[2/3] Creating optimized batches...")
    batches = create_batches(files)
    print(f"Created {len(batches)} batches")

    # Show batch breakdown
    print("\nBatches by size category:")
    size_counts: Dict[str, int] = {}
    for b in batches:
        size_counts[b.size_category] = size_counts.get(b.size_category, 0) + 1
    for size, count in sorted(size_counts.items()):
        print(f"  {size}: {count} batches")

    # Save batches
    print("\n[3/3] Saving batches configuration...")
    ralph_dir = Path.cwd() / ".ralph"
    ralph_dir.mkdir(exist_ok=True)

    batches_file = ralph_dir / "batches.json"
    with open(batches_file, "w") as f:
        json.dump({
            "created_at": datetime.utcnow().isoformat() + "Z",
            "total_files": len(files),
            "total_batches": len(batches),
            "estimated_total_time_minutes": sum(b.estimated_time_minutes for b in batches),
            "batches": [b.to_dict() for b in batches],
        }, f, indent=2)

    print(f"Saved to {batches_file}")

    # Summary
    print("\n" + "=" * 60)
    print("BATCH PREPARATION COMPLETE")
    print("=" * 60)
    print(f"Total files:    {len(files)}")
    print(f"Total batches:  {len(batches)}")
    print(f"Est. time:      {sum(b.estimated_time_minutes for b in batches)} minutes")
    print(f"Config saved:   {batches_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
