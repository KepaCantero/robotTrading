#!/usr/bin/env python3
"""
Ralph Task Resume

Reanuda una tarea desde su checkpoint más reciente.

Usage:
    python .ralph/scripts/resume.py <task_id>

Example:
    python .ralph/scripts/resume.py "01_protocol_interfaces"
"""
import sys
import json
from pathlib import Path
from typing import Any


def load_checkpoint(task_id: str) -> dict[str, Any]:
    """
    Carga checkpoint de una tarea

    Args:
        task_id: ID de la tarea (ej: "01_protocol_interfaces")

    Returns:
        Diccionario con el checkpoint o None si no existe
    """
    checkpoint_file = Path(f".ralph/checkpoints/{task_id}_checkpoint.json")

    if not checkpoint_file.exists():
        return None

    with open(checkpoint_file) as f:
        return json.load(f)


def get_task_status(task_id: str) -> str:
    """
    Obtiene estado de una tarea desde checkpoint

    Args:
        task_id: ID de la tarea

    Returns:
        Estado de la tarea (PENDING, IN_PROGRESS, COMPLETED, FAILED, BLOCKED)
    """
    checkpoint = load_checkpoint(task_id)

    if not checkpoint:
        return "NOT_STARTED"

    return checkpoint.get("status", "UNKNOWN")


def print_resume_info(task_id: str, checkpoint: dict[str, Any]) -> None:
    """Imprime información de resumen"""
    status = checkpoint.get("status", "UNKNOWN")
    started_at = checkpoint.get("started_at", "N/A")
    completed_at = checkpoint.get("completed_at", "N/A")

    print(f"\n{'='*60}")
    print(f"Task Resume Information: {task_id}")
    print(f"{'='*60}")
    print(f"Status:          {status}")
    print(f"Started At:      {started_at}")
    print(f"Completed At:    {completed_at}")

    if status == "FAILED":
        errors = checkpoint.get("errors", [])
        print(f"\nErrors ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")

    if status == "BLOCKED":
        dependencies = checkpoint.get("blocked_by", [])
        print(f"\nBlocked By:")
        for dep in dependencies:
            print(f"  - {dep}")

    if status in ["COMPLETED", "FAILED"]:
        progress = checkpoint.get("progress", {})
        print(f"\nProgress:")
        for key, value in progress.items():
            print(f"  - {key}: {value}")

    print(f"{'='*60}\n")


def main() -> int:
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python resume.py <task_id>", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print('  python resume.py "01_protocol_interfaces"', file=sys.stderr)
        print('  python resume.py "02_spain_tax_engine"', file=sys.stderr)
        return 1

    task_id = sys.argv[1]

    # Cargar checkpoint
    checkpoint = load_checkpoint(task_id)

    if not checkpoint:
        print(f"Error: No checkpoint found for task '{task_id}'", file=sys.stderr)
        print(f"Expected file: .ralph/checkpoints/{task_id}_checkpoint.json", file=sys.stderr)
        print(f"\nTask status: NOT_STARTED")
        print(f"Suggestion: Run task from beginning")
        return 1

    # Imprimir información
    print_resume_info(task_id, checkpoint)

    # Sugerir acción basada en estado
    status = checkpoint.get("status")

    if status == "COMPLETED":
        print("Task is already completed.")
        print("Suggestion: Run next task or verify outputs")
        return 0

    elif status == "FAILED":
        print("Task failed during execution.")
        print("Suggestion: Review errors above and retry task")
        return 1

    elif status == "BLOCKED":
        print("Task is blocked by dependencies.")
        print("Suggestion: Complete dependent tasks first")
        return 1

    elif status == "IN_PROGRESS":
        print("Task is currently in progress.")
        print("Suggestion: Check if task is still running or resume from last checkpoint")
        return 0

    elif status == "PENDING":
        print("Task has not started yet.")
        print("Suggestion: Run task to begin execution")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
