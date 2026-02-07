#!/usr/bin/env python3
"""
Checkpoint Tracker System

Tracks audit progress across all Python files in the project.
Saves progress to resume from where we left off.

Usage:
    python scripts/checkpoint_tracker.py status     # Show current status
    python scripts/checkpoint_tracker.py next core   # Get next batch from core
    python scripts/checkpoint_tracker.py reset core   # Reset core progress
    python scripts/checkpoint_tracker.py verify file  # Verify single file
    python scripts/checkpoint_tracker.py batch core   # Process entire core batch
"""

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class FileStatus:
    """Status of a single file."""

    path: str
    has_requirements: bool
    verified: bool
    passed: bool
    last_checked: Optional[str] = None
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "has_requirements": self.has_requirements,
            "verified": self.verified,
            "passed": self.passed,
            "last_checked": self.last_checked,
            "issues": self.issues,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FileStatus":
        return cls(**data)


class CheckpointTracker:
    """Tracks audit progress with checkpoint persistence."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.checkpoint_file = self.project_root / ".ralphex" / "checkpoint_progress.json"
        self.progress = self._load_progress()
        self._scan_files()

    def _load_progress(self) -> Dict[str, dict]:
        """Load saved progress from checkpoint file."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r") as f:
                return json.load(f)
        return {}

    def _save_progress(self):
        """Save progress to checkpoint file."""
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, "w") as f:
            json.dump(self.progress, f, indent=2)

    def _scan_files(self):
        """Scan all Python files and update status."""
        app_dir = self.project_root / "app"

        for py_file in app_dir.rglob("*.py"):
            # Skip test files and __pycache__
            if (
                "__pycache__" in str(py_file)
                or py_file.name.startswith("__")
                or "test" in py_file.parts
            ):
                continue

            rel_path = str(py_file.relative_to(self.project_root))

            # Check if requirements exist
            req_path = self.project_root / ".requirements" / f"{rel_path}.requirements.md"
            has_req = req_path.exists()

            # Get existing status or create new
            if rel_path not in self.progress:
                self.progress[rel_path] = FileStatus(
                    path=rel_path,
                    has_requirements=has_req,
                    verified=False,
                    passed=False,
                    last_checked=None,
                    issues=[],
                ).to_dict()
            else:
                # Update has_requirements if changed
                self.progress[rel_path]["has_requirements"] = has_req

        self._save_progress()

    def get_status(self, layer: Optional[str] = None) -> Dict[str, any]:
        """Get status summary for a layer or all files."""
        files = self._filter_by_layer(layer) if layer else self.progress

        total = len(files)
        verified = sum(1 for f in files.values() if f.get("verified", False))
        passed = sum(1 for f in files.values() if f.get("passed", False))
        has_req = sum(1 for f in files.values() if f.get("has_requirements", False))
        failed = sum(1 for f in files.values() if f.get("verified", True) and not f.get("passed", True))

        return {
            "layer": layer or "all",
            "total": total,
            "verified": verified,
            "passed": passed,
            "failed": failed,
            "with_requirements": has_req,
            "pending": total - verified,
            "pass_rate": f"{(passed/verified*100):.1f}%" if verified > 0 else "0%",
        }

    def _filter_by_layer(self, layer: str) -> Dict[str, dict]:
        """Filter files by layer."""
        layer_map = {
            "core": "app/core/",
            "domain": "app/domain/",
            "entities": "app/domain/entities/",
            "services": "app/domain/services/",
            "backtesting": "app/backtesting/",
            "strategies": "app/strategies/",
            "analysis": "app/analysis/",
            "api": "app/api/",
            "presentation": "app/presentation/",
            "application": "app/application/",
            "database": "app/database/",
            "microstructure": "app/market_microstructure/",
        }

        prefix = layer_map.get(layer.lower())
        if not prefix:
            return self.progress

        return {
            k: v for k, v in self.progress.items() if k.startswith(prefix)
        }

    def get_next_batch(self, layer: str, batch_size: int = 10) -> List[str]:
        """Get next batch of unverified files from a layer."""
        files = self._filter_by_layer(layer)

        # Get unverified files
        unverified = [
            k for k, v in files.items()
            if not v.get("verified", False)
        ]

        return unverified[:batch_size]

    def mark_verified(self, file_path: str, passed: bool, issues: List[str] = None):
        """Mark a file as verified."""
        if file_path in self.progress:
            self.progress[file_path]["verified"] = True
            self.progress[file_path]["passed"] = passed
            self.progress[file_path]["last_checked"] = datetime.utcnow().isoformat()
            self.progress[file_path]["issues"] = issues or []
            self._save_progress()

    def print_status(self, layer: Optional[str] = None):
        """Print status summary."""
        status = self.get_status(layer)

        print(f"\n{'='*60}")
        print(f"CHECKPOINT STATUS: {status['layer'].upper()}")
        print(f"{'='*60}")
        print(f"📊 Total Files:      {status['total']}")
        print(f"✅ Verified:         {status['verified']}")
        print(f"✔️  Passed:           {status['passed']}")
        print(f"❌ Failed:           {status['failed']}")
        print(f"📝 With Requirements:{status['with_requirements']}")
        print(f"⏳ Pending:          {status['pending']}")
        print(f"📈 Pass Rate:        {status['pass_rate']}")
        print(f"{'='*60}\n")

        # Show next batch if pending
        if status['pending'] > 0:
            next_batch = self.get_next_batch(layer or "all", 5)
            print(f"📋 Next {len(next_batch)} files to verify:")
            for f in next_batch:
                print(f"   - {f}")
            print()

    def verify_file(self, file_path: str) -> bool:
        """Verify a single file using the checkpoint verification script."""
        import subprocess

        result = subprocess.run(
            ["python", "scripts/verify_checkpoint.py", file_path],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )

        # Check if PASSED in output
        passed = "Status: ✅ PASSED" in result.stdout

        # Extract any errors
        issues = []
        if "Status: ❌ FAILED" in result.stdout or "Status: ❌ FAILED" in result.stdout:
            # Extract error lines
            for line in result.stdout.split("\n"):
                if "❌" in line or "Error:" in line:
                    issues.append(line.strip())

        # Mark as verified
        rel_path = file_path if file_path.startswith("app/") else f"app/{file_path.lstrip('/')}"
        self.mark_verified(rel_path, passed, issues)

        return passed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Checkpoint Tracker for GAP Audit")
    parser.add_argument("command", nargs="?", default="status",
                        choices=["status", "next", "reset", "verify", "batch"],
                        help="Command to run")
    parser.add_argument("layer", nargs="?", default="all",
                        help="Layer to check (core, domain, backtesting, etc.)")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Batch size for 'next' command")
    parser.add_argument("--file", help="File path for 'verify' command")

    args = parser.parse_args()

    tracker = CheckpointTracker()

    if args.command == "status":
        tracker.print_status(args.layer if args.layer != "all" else None)

    elif args.command == "next":
        batch = tracker.get_next_batch(args.layer, args.batch_size)
        print(f"\n📋 Next {len(batch)} files from {args.layer}:")
        for i, f in enumerate(batch, 1):
            print(f"   {i}. {f}")
        print(f"\n💾 To save progress, run:")
        for f in batch:
            print(f"   python scripts/checkpoint_tracker.py verify {f}")

    elif args.command == "verify":
        if not args.file:
            print("Error: --file required for verify command")
            return 1

        print(f"🔍 Verifying: {args.file}")
        passed = tracker.verify_file(args.file)
        if passed:
            print(f"✅ PASSED")
        else:
            print(f"❌ FAILED")

    elif args.command == "reset":
        # Reset progress for a layer
        files = tracker._filter_by_layer(args.layer)
        for f in files:
            tracker.progress[f]["verified"] = False
            tracker.progress[f]["passed"] = False
        tracker._save_progress()
        print(f"✅ Reset {len(files)} files in {args.layer}")

    elif args.command == "batch":
        # Process entire batch for a layer
        batch = tracker.get_next_batch(args.layer, 50)
        print(f"🔄 Processing {len(batch)} files from {args.layer}...")

        import subprocess
        passed = 0
        failed = 0

        for f in batch:
            print(f"\n🔍 {f}...", end=" ")
            result = subprocess.run(
                ["python", "scripts/verify_checkpoint.py", f],
                capture_output=True,
                text=True,
                cwd=tracker.project_root,
            )

            is_passed = "Status: ✅ PASSED" in result.stdout
            if is_passed:
                print("✅")
                passed += 1
            else:
                print("❌")
                failed += 1

            # Mark verified
            tracker.mark_verified(f, is_passed)

        print(f"\n{'='*60}")
        print(f"Batch Complete: {passed} PASSED, {failed} FAILED")
        print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
