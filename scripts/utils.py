#!/usr/bin/env python3
"""
AlgoTrading Scripts - Unified CLI
=================================

Uso:
    python scripts/utils.py <comando> [argumentos]

Comandos disponibles:
    validate       Validar archivo con todas las herramientas
    list_files     Listar archivos por categoría
    audit_files    Auditar archivos y generar reporte
    check_progress Verificar progreso de tarea
    mark_files     Marcar archivos con estado

Ejemplos:
    python scripts/utils.py validate app/services/compliance_engine.py
    python scripts/utils.py list_files --category critical
    python scripts/utils.py audit_files --batch batch_01
    python scripts/utils.py check_progress --task compliance_refactor
    python scripts/utils.py mark_files --status PASSED app/**/*.py
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
        return subprocess.run(cmd, capture_output=capture, text=True, check=False)
    except Exception as e:
        print(f"Error ejecutando comando: {e}", file=sys.stderr)
        sys.exit(1)


# ============================================================================
# VALIDATE
# ============================================================================


def validate_file(file_path: str, fix: bool = False) -> dict:
    """
    Valida un archivo con todas las herramientas.

    Args:
        file_path: Ruta al archivo a validar
        fix: Si True, intenta arreglar errores automáticamente

    Returns:
        Dict con resultados de validación
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    script_path = Path(__file__).parent / "validation" / "validate_file_complete.sh"

    if not script_path.exists():
        return {"success": False, "error": f"Validation script not found: {script_path}"}

    # Si se pidió fix, intentar auto-fix primero
    if fix:
        run_command(["black", str(file_path)])
        run_command(["isort", str(file_path)])
        run_command(["ruff", "check", str(file_path), "--fix"])

    # Ejecutar validación
    result = run_command([str(script_path), str(file_path)])

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON output", "raw": result.stdout}


def cmd_validate(args):
    """Maneja comando validate"""
    result = validate_file(args.file, fix=args.fix)
    print(json.dumps(result, indent=2))

    if not result.get("success"):
        sys.exit(1)


# ============================================================================
# LIST FILES
# ============================================================================


def list_files(category: Optional[str] = None, pattern: str = "app/**/*.py") -> List[str]:
    """
    Lista archivos por categoría.

    Args:
        category: Categoría (critical, p1, p2, all)
        pattern: Patrón glob para buscar

    Returns:
        Lista de rutas de archivos
    """
    # Usar scripts de audit para obtener archivos
    if category == "critical":
        script = Path(__file__).parent / "audit" / "get_critical_files.py"
    elif category == "p1":
        script = Path(__file__).parent / "audit" / "get_p1_files.py"
    elif category == "p2":
        script = Path(__file__).parent / "audit" / "get_p2_files.py"
    else:
        # Usar find directamente
        result = run_command(["find", "app", "-name", "*.py", "-type", "f"])
        return result.stdout.strip().split("\n")

    if script and script.exists():
        result = run_command(["python", str(script)])
        return result.stdout.strip().split("\n")

    return []


def cmd_list_files(args):
    """Maneja comando list_files"""
    files = list_files(category=args.category, pattern=args.pattern)
    for f in files:
        print(f)


# ============================================================================
# AUDIT FILES
# ============================================================================


def audit_files(files: List[str], parallel: int = 1) -> dict:
    """
    Audita archivos y genera reporte.

    Args:
        files: Lista de archivos a auditar
        parallel: Número de procesos paralelos

    Returns:
        Dict con resultados de auditoría
    """
    results = {"total": len(files), "passed": 0, "failed": 0, "files": {}}

    for file_path in files:
        result = validate_file(file_path)
        results["files"][file_path] = result

        if result.get("success"):
            results["passed"] += 1
        else:
            results["failed"] += 1

    results["success"] = results["failed"] == 0
    return results


def cmd_audit_files(args):
    """Maneja comando audit_files"""
    if args.batch:
        # Leer archivos desde batch file
        batch_file = Path(f".ralph/batches/{args.batch}.json")
        if batch_file.exists():
            batch_data = json.loads(batch_file.read_text())
            files = batch_data.get("files", [])
        else:
            print(f"Batch file not found: {batch_file}", file=sys.stderr)
            sys.exit(1)
    else:
        files = list_files(category=args.category)

    results = audit_files(files, parallel=args.parallel)
    print(json.dumps(results, indent=2))

    if not results.get("success"):
        sys.exit(1)


# ============================================================================
# CHECK PROGRESS
# ============================================================================


def check_progress(task_name: str) -> dict:
    """
    Verifica progreso de una tarea.

    Args:
        task_name: Nombre de la tarea

    Returns:
        Dict con progreso
    """
    checkpoint_file = Path(f".ralph/checkpoints/{task_name}.json")

    if not checkpoint_file.exists():
        return {"error": "Checkpoint not found", "task": task_name}

    return json.loads(checkpoint_file.read_text())


def cmd_check_progress(args):
    """Maneja comando check_progress"""
    result = check_progress(args.task)
    print(json.dumps(result, indent=2))


# ============================================================================
# MARK FILES
# ============================================================================


def mark_files(files: List[str], status: str) -> dict:
    """
    Marca archivos con un estado.

    Args:
        files: Lista de archivos
        status: Estado a marcar

    Returns:
        Dict con resultado
    """
    # Actualizar requirements files o checkpoint
    results = {"marked": 0, "failed": 0}

    for file_path in files:
        req_file = Path(f".requirements/{file_path}.requirements.md")
        if req_file.exists():
            content = req_file.read_text()
            # Actualizar Audit Status
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "Audit Status:" in line:
                    lines[i] = f"| **Audit Status** | {status} |"
                    break
            req_file.write_text("\n".join(lines))
            results["marked"] += 1
        else:
            results["failed"] += 1

    return results


def cmd_mark_files(args):
    """Maneja comando mark_files"""
    files = list_files(category=args.category)
    result = mark_files(files, args.status)
    print(json.dumps(result, indent=2))


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="AlgoTrading Scripts - Unified CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # validate
    parser_validate = subparsers.add_parser("validate", help="Validar archivo")
    parser_validate.add_argument("file", help="Ruta del archivo")
    parser_validate.add_argument("--fix", action="store_true", help="Intentar arreglar errores")

    # list_files
    parser_list = subparsers.add_parser("list_files", help="Listar archivos")
    parser_list.add_argument(
        "--category", choices=["critical", "p1", "p2", "all"], help="Categoría"
    )
    parser_list.add_argument("--pattern", default="app/**/*.py", help="Patrón glob")

    # audit_files
    parser_audit = subparsers.add_parser("audit_files", help="Auditar archivos")
    parser_audit.add_argument("--batch", help="Batch file name")
    parser_audit.add_argument("--category", choices=["critical", "p1", "p2"], help="Categoría")
    parser_audit.add_argument("--parallel", type=int, default=1, help="Procesos paralelos")

    # check_progress
    parser_progress = subparsers.add_parser("check_progress", help="Verificar progreso")
    parser_progress.add_argument("--task", required=True, help="Nombre de la tarea")

    # mark_files
    parser_mark = subparsers.add_parser("mark_files", help="Marcar archivos")
    parser_mark.add_argument("--status", required=True, help="Estado a marcar")
    parser_mark.add_argument("--category", choices=["critical", "p1", "p2"], help="Categoría")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "validate": cmd_validate,
        "list_files": cmd_list_files,
        "audit_files": cmd_audit_files,
        "check_progress": cmd_check_progress,
        "mark_files": cmd_mark_files,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
