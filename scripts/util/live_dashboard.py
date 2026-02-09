#!/usr/bin/env python3
"""
Live Dashboard for GAP Audit Progress

Real-time monitoring of batch processing, file status, and metrics.
"""
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.text import Text


class AuditDashboard:
    """Real-time dashboard for GAP audit progress."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.batches_file = self.project_root / ".ralph" / "batches.json"
        self.checkpoint_file = self.project_root / ".ralph" / "checkpoint_progress.json"
        self.log_file = self.project_root / ".ralph" / "audit.log"

        self.console = Console()
        self.batches = self._load_batches()
        self.checkpoint = self._load_checkpoint()

    def _load_batches(self) -> dict:
        """Load batches configuration."""
        if self.batches_file.exists():
            with open(self.batches_file, "r") as f:
                return json.load(f)
        return {"batches": [], "total_batches": 0}

    def _load_checkpoint(self) -> dict:
        """Load checkpoint progress."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r") as f:
                return json.load(f)
        return {}

    def _get_progress_stats(self) -> Dict:
        """Calculate progress statistics."""
        meta = self.checkpoint.get("meta", {})
        batches_checkpoint = self.checkpoint.get("batches", {})

        total = meta.get("total_batches", self.batches.get("total_batches", 0))

        # Count from checkpoint
        completed = sum(1 for b in batches_checkpoint.values() if b.get("status") == "completed")
        in_progress = sum(1 for b in batches_checkpoint.values() if b.get("status") == "in_progress")
        failed = sum(1 for b in batches_checkpoint.values() if b.get("status") == "failed")

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "pending": total - completed - in_progress - failed,
            "percentage": (completed / total * 100) if total > 0 else 0,
        }

    def _get_file_stats(self) -> Dict:
        """Get file statistics from checkpoint."""
        files = self.checkpoint.get("files", {})
        meta = self.checkpoint.get("meta", {})
        total = meta.get("total_files", len(files))
        verified = sum(1 for f in files.values() if f.get("verified", False))
        passed = sum(1 for f in files.values() if f.get("status") == "PASSED")
        failed = sum(1 for f in files.values() if f.get("status") == "FAILED")

        return {
            "total": total,
            "verified": verified,
            "passed": passed,
            "failed": failed,
            "pending": total - verified,
            "pass_rate": (passed / verified * 100) if verified > 0 else 0,
        }

    def _create_progress_panel(self) -> Panel:
        """Create progress overview panel."""
        stats = self._get_progress_stats()
        file_stats = self._get_file_stats()

        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress"),
            Layout(name="files", size=8),
            Layout(name="time", size=3),
        )

        # Header
        layout["header"].update(
            Panel(
                Text("GAP AUDIT PROGRESS", style="bold cyan"),
                style="on blue",
            )
        )

        # Progress bar
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            expand=True,
        )
        task = progress.add_task("Processing batches...", total=stats["total"], completed=stats["completed"])
        layout["progress"].update(progress)

        # File stats table
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Batches", justify="right")
        table.add_column("Files", justify="right")

        table.add_row("Total", str(stats["total"]), str(file_stats["total"]))
        table.add_row("Completed", f"[green]{stats['completed']}[/green]", f"[green]{file_stats['passed']}[/green]")
        table.add_row("In Progress", f"[yellow]{stats['in_progress']}[/yellow]", str(file_stats["verified"] - file_stats["passed"] - file_stats["failed"]))
        table.add_row("Failed", f"[red]{stats['failed']}[/red]", f"[red]{file_stats['failed']}[/red]")
        table.add_row("Pending", str(stats["pending"]), str(file_stats["pending"]))
        table.add_row("Pass Rate", "", f"[cyan]{file_stats['pass_rate']:.1f}%[/cyan]")

        layout["files"].update(Panel(table, title="Statistics", border_style="blue"))

        # Time estimate
        est_time = (stats["total"] - stats["completed"]) * 5  # 5 min per batch avg
        layout["time"].update(
            Panel(
                Text(f"Est. remaining: {est_time} min ({est_time//60}h {est_time%60}m)", style="yellow"),
                border_style="dim",
            )
        )

        return Panel(layout, title="Audit Progress", border_style="bright_blue")

    def _create_current_batch_panel(self) -> Panel:
        """Create current batch panel."""
        batches_checkpoint = self.checkpoint.get("batches", {})
        meta = self.checkpoint.get("meta", {})

        # Find in_progress batch from checkpoint
        current_batch_id = None
        current_batch_data = None

        for batch_id, batch_data in batches_checkpoint.items():
            if batch_data.get("status") == "in_progress":
                current_batch_id = batch_id
                current_batch_data = batch_data
                break

        if not current_batch_id and meta.get("current_batch"):
            # Use current_batch from meta as fallback
            current_batch_id = meta.get("current_batch")
            # Try to find batch info from batches.json
            for b in self.batches.get("batches", []):
                if b["batch_id"] == current_batch_id:
                    current_batch_data = b
                    break

        if not current_batch_id:
            return Panel(
                Text("No batch currently processing", style="dim"),
                title="Current Batch",
                border_style="dim",
            )

        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        table.add_row("Batch ID", Text(current_batch_id, style="bold yellow"))

        # Add batch info if available
        if current_batch_data:
            if isinstance(current_batch_data, dict):
                table.add_row("Files Processed", str(current_batch_data.get("files_processed", "?")))
                if "total_files" in current_batch_data:
                    table.add_row("Total Files", str(current_batch_data["total_files"]))
                if "started_at" in current_batch_data:
                    table.add_row("Started", current_batch_data["started_at"])

        # Try to get more info from batches.json
        for b in self.batches.get("batches", []):
            if b["batch_id"] == current_batch_id:
                table.add_row("Layer", b.get("layer", "?"))
                table.add_row("Total Files", str(b.get("file_count", "?")))
                table.add_row("Size", b.get("size_category", "?"))
                break

        return Panel(table, title="Current Batch", border_style="yellow")

    def _create_recent_files_panel(self) -> Panel:
        """Create recent files panel."""
        # Get recently verified files
        files = self.checkpoint.get("files", {})
        recent = []
        for path, data in sorted(
            files.items(),
            key=lambda x: x[1].get("timestamp", ""),
            reverse=True,
        )[:10]:
            if data.get("verified", False):
                status = "[green]✓[/green]" if data.get("status") == "PASSED" else "[red]✗[/red]"
                recent.append((status, path))

        if not recent:
            return Panel(
                Text("No files verified yet", style="dim"),
                title="Recent Files",
                border_style="dim",
            )

        table = Table(show_header=False, box=None)
        table.add_column("Status")
        table.add_column("File")

        for status, path in recent:
            # Shorten path
            short_path = path.replace("app/", "").replace(".py", "")
            table.add_row(status, Text(short_path, style="dim"))

        return Panel(table, title="Recent Files (Last 10)", border_style="green")

    def _create_errors_panel(self) -> Panel:
        """Create errors/warnings panel."""
        errors = []

        # Collect errors from checkpoint
        files = self.checkpoint.get("files", {})
        for path, data in files.items():
            if data.get("issues"):
                for issue in data["issues"]:
                    errors.append((path, issue))

        if not errors:
            return Panel(
                Text("No errors or warnings", style="green"),
                title="Errors & Warnings",
                border_style="green",
            )

        # Show last 10 errors
        text = Text()
        for path, issue in errors[-10:]:
            text.append(f"[dim]{path}:[/dim]\n", style="cyan")
            text.append(f"  {issue}\n\n")

        return Panel(text, title="Errors & Warnings", border_style="red")

    def _create_layout(self) -> Layout:
        """Create main dashboard layout."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3),
        )

        layout["header"].update(
            Panel(
                Text("RALPH ORCHESTRATOR - GAP AUDIT DASHBOARD", style="bold white"),
                style="on blue",
            )
        )

        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1),
        )

        layout["left"].split_column(
            Layout(self._create_progress_panel(), ratio=2),
            Layout(self._create_current_batch_panel(), ratio=1),
        )

        layout["right"].split_column(
            Layout(self._create_recent_files_panel(), ratio=1),
            Layout(self._create_errors_panel(), ratio=1),
        )

        # Footer
        layout["footer"].update(
            Panel(
                Text(f"Last update: {datetime.now().strftime('%H:%M:%S')} | Press Ctrl+C to exit", style="dim"),
                border_style="dim",
            )
        )

        return layout

    def run(self, refresh_seconds: int = 2):
        """Run the live dashboard."""
        try:
            with Live(
                self._create_layout(),
                console=self.console,
                refresh_per_second=1 / refresh_seconds,
                screen=False,
            ) as live:
                while True:
                    # Reload data
                    self.batches = self._load_batches()
                    self.checkpoint = self._load_checkpoint()

                    # Update display
                    live.update(self._create_layout())
                    time.sleep(refresh_seconds)

        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]Dashboard stopped.[/bold yellow]")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Live Dashboard for GAP Audit")
    parser.add_argument("--refresh", type=int, default=2, help="Refresh interval in seconds")
    args = parser.parse_args()

    dashboard = AuditDashboard()
    dashboard.run(refresh_seconds=args.refresh)


if __name__ == "__main__":
    main()
