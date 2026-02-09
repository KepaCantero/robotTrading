#!/usr/bin/env python3
"""
AlgoTrading Scripts - Unified CLI (Minimal version for .ralph)

Uso:
    python .ralph/scripts/utils.py <comando> [argumentos]

Comandos disponibles:
    validate       Validar archivo con herramientas básicas
    check_progress Verificar progreso de tarea
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Ejecuta comando y devuelve resultado"""
    try:
        return subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            check=False
        )
    except Exception as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def validate_file(file_path: str, fix: bool = False) -> dict:
    """
    Valida un archivo con herramientas básicas.

    Args:
        file_path: Ruta al archivo a validar
        fix: Si True, intenta arreglar errores automáticamente

    Returns:
        Dict con resultados de validación
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return {
            "success": False,
            "error": f"File not found: {file_path}",
            "summary": {"success": False}
        }

    checks = {}
    all_passed = True

    # Si se pidió fix, intentar auto-fix primero
    if fix:
        run_command(["black", str(file_path)])
        run_command(["isort", str(file_path)])
        run_command(["ruff", "check", str(file_path), "--fix"])

    # 1. Black (formatting)
    result = run_command(["black", "--check", str(file_path)])
    checks["black"] = "passed" if result.returncode == 0 else "failed"
    if result.returncode != 0:
        all_passed = False

    # 2. isort (imports)
    result = run_command(["isort", "--check-only", str(file_path)])
    checks["isort"] = "passed" if result.returncode == 0 else "failed"
    if result.returncode != 0:
        all_passed = False

    # 3. ruff (linting)
    result = run_command(["ruff", "check", str(file_path)])
    checks["ruff"] = "passed" if result.returncode == 0 else "failed"
    if result.returncode != 0:
        all_passed = False

    # 4. mypy (type hints) - opcional, puede no estar instalado
    result = run_command(["mypy", str(file_path)])
    checks["mypy"] = "passed" if result.returncode == 0 else "failed"
    # mypy no es crítico para el éxito general

    return {
        "success": all_passed,
        "summary": {"success": all_passed},
        "checks": checks,
        "file": str(file_path)
    }


def check_progress(task_id: str) -> dict:
    """
    Verifica progreso de una tarea desde su checkpoint

    Args:
        task_id: ID de la tarea (ej: "01_protocol_interfaces")

    Returns:
        Dict con información de progreso
    """
    checkpoint_file = Path(f".ralph/checkpoints/{task_id}_checkpoint.json")

    if not checkpoint_file.exists():
        return {
            "success": False,
            "error": f"Checkpoint not found: {checkpoint_file}",
            "task_id": task_id,
            "status": "NOT_STARTED"
        }

    try:
        with open(checkpoint_file) as f:
            checkpoint = json.load(f)

        return {
            "success": True,
            "task_id": task_id,
            "status": checkpoint.get("status", "UNKNOWN"),
            "progress": checkpoint.get("progress", {}),
            "started_at": checkpoint.get("started_at"),
            "completed_at": checkpoint.get("completed_at")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "task_id": task_id
        }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AlgoTrading Scripts CLI")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validar archivo")
    validate_parser.add_argument("file", help="Archivo a validar")
    validate_parser.add_argument("--fix", action="store_true", help="Auto-arreglar errores")

    # Check progress command
    progress_parser = subparsers.add_parser("check_progress", help="Verificar progreso")
    progress_parser.add_argument("--task", required=True, help="ID de tarea")

    args = parser.parse_args()

    if args.command == "validate":
        result = validate_file(args.file, fix=args.fix)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("success") else 1)

    elif args.command == "check_progress":
        result = check_progress(args.task)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("success") else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
