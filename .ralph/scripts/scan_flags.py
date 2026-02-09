#!/usr/bin/env python3
"""
AlgoTrading Scripts - Flag Scanner

Escanea el código en busca de flags (@todo, @skip-import, @clarify, @review, @fixme, @hack, XXX, TODO, FIXME)
y genera un reporte detallado para el proceso de cleanup.

Uso:
    python .ralph/scripts/scan_flags.py [opciones]

Opciones:
    --dir, -d       Directorio a escanear (default: app/)
    --output, -o    Archivo de salida JSON (default: .ralph/outputs/flags_found.json)
    --format, -f    Formato de salida: json|text|markdown (default: json)
    --types, -t     Tipos de flag a buscar (separados por coma, default: todos)
    --fix           Intenta arreglar flags encontrados (experimental)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict


# Flag patterns con regex
FLAG_PATTERNS = {
    "@skip-import": r'@skip-import:\s*(.+)',
    "@todo": r'@todo:\s*(.+)',
    "@clarify": r'@clarify:\s*(.+)',
    "@review": r'@review:\s*(.+)',
    "@fixme": r'@fixme:\s*(.+)',
    "@hack": r'@hack:\s*(.+)',
    "XXX": r'XXX:\s*(.+)',
    "TODO": r'TODO:\s*(.+)',
    "FIXME": r'FIXME:\s*(.+)',
}


class FlagScanner:
    """Escanea código en busca de flags"""

    # Directorios y archivos a excluir del escaneo
    EXCLUDE_DIRS = {
        "__pycache__",
        ".pyc",
        ".pytest_cache",
        ".mypy_cache",
        "venv",
        ".venv",
        "env",
        ".git",
        ".ralph/scripts",  # Scripts de herramienta, no código de producción
        ".ralph/_archived",
        "scripts/archived",
    }

    # Archivos específicos a excluir
    EXCLUDE_FILES = {
        "scan_flags.py",  # Este script mismo
    }

    def __init__(self, root_dir: str = "app/"):
        self.root_dir = Path(root_dir)
        self.flags_found: List[Dict[str, Any]] = []
        self.summary = defaultdict(lambda: 0)

    def scan_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Escanea un archivo en busca de flags

        Args:
            file_path: Path al archivo a escanear

        Returns:
            Lista de flags encontrados en el archivo
        """
        flags = []

        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                for flag_type, pattern in FLAG_PATTERNS.items():
                    match = re.search(pattern, line)
                    if match:
                        flag = {
                            "file": str(file_path.relative_to(self.root_dir.parent)),
                            "line": line_num,
                            "flag_type": flag_type,
                            "reason": match.group(1).strip(),
                            "context": self._get_context(lines, line_num - 1),
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        }
                        flags.append(flag)
                        self.summary[flag_type] += 1

        except Exception as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)

        return flags

    def _get_context(self, lines: List[str], line_index: int, context_lines: int = 2) -> Dict[str, str]:
        """
        Obtiene contexto alrededor de una línea

        Args:
            lines: Lista de líneas del archivo
            line_index: Índice de la línea actual
            context_lines: Número de líneas de contexto

        Returns:
            Dict con before, current, after
        """
        start = max(0, line_index - context_lines)
        end = min(len(lines), line_index + context_lines + 1)

        return {
            "before": "\n".join(lines[start:line_index]),
            "current": lines[line_index],
            "after": "\n".join(lines[line_index + 1:end])
        }

    def scan_directory(self, directory: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Escanea todos los archivos Python en un directorio

        Args:
            directory: Directorio a escanear (default: self.root_dir)

        Returns:
            Lista de todos los flags encontrados
        """
        scan_dir = directory or self.root_dir

        if not scan_dir.exists():
            print(f"Directory {scan_dir} does not exist")
            return []

        # Encontrar todos los archivos Python
        python_files = list(scan_dir.rglob("*.py"))

        # Filtrar directorios excluidos y archivos específicos
        python_files = [
            f for f in python_files
            if not any(
                excluded_dir in f.parts
                for excluded_dir in self.EXCLUDE_DIRS
            )
            and f.name not in self.EXCLUDE_FILES
            and ".pyc" not in str(f)
        ]

        print(f"Scanning {len(python_files)} Python files in {scan_dir}...")

        for file_path in python_files:
            flags = self.scan_file(file_path)
            self.flags_found.extend(flags)

        return self.flags_found

    def get_summary(self) -> Dict[str, int]:
        """Obtiene resumen de flags encontrados"""
        return dict(self.summary)

    def generate_report(self) -> Dict[str, Any]:
        """
        Genera reporte completo de flags

        Returns:
            Dict con el reporte completo
        """
        # Agrupar flags por tipo
        by_type = defaultdict(list)
        for flag in self.flags_found:
            by_type[flag["flag_type"]].append(flag)

        # Agrupar flags por archivo
        by_file = defaultdict(list)
        for flag in self.flags_found:
            by_file[flag["file"]].append(flag)

        return {
            "scan_timestamp": datetime.utcnow().isoformat() + "Z",
            "scan_directory": str(self.root_dir),
            "total_flags": len(self.flags_found),
            "summary": self.get_summary(),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "flags_by_type": dict(by_type),
            "flags_by_file": dict(by_file),
            "all_flags": self.flags_found
        }

    def export_markdown(self, report: Dict[str, Any]) -> str:
        """
        Exporta reporte a formato Markdown

        Args:
            report: Reporte generado

        Returns:
            String en formato Markdown
        """
        md_lines = [
            "# Flag Scanner Report",
            f"\n**Generated:** {report['scan_timestamp']}",
            f"**Directory:** `{report['scan_directory']}`",
            f"**Total Flags:** {report['total_flags']}\n",
            "## Summary\n",
            "| Flag Type | Count |",
            "|-----------|-------|"
        ]

        for flag_type, count in sorted(report['summary'].items()):
            md_lines.append(f"| {flag_type} | {count} |")

        md_lines.append("\n## Flags by Type\n")

        for flag_type, flags in sorted(report['flags_by_type'].items()):
            md_lines.append(f"### {flag_type} ({len(flags)})\n")

            for flag in flags:
                md_lines.append(f"**File:** `{flag['file']}` (line {flag['line']})")
                md_lines.append(f"**Reason:** {flag['reason']}")
                md_lines.append(f"**Context:**\n```python")
                if flag['context']['before']:
                    md_lines.append(flag['context']['before'])
                md_lines.append(f"> {flag['context']['current']}")
                if flag['context']['after']:
                    md_lines.append(flag['context']['after'])
                md_lines.append("```\n")

        return "\n".join(md_lines)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Scan code for flags (@todo, @skip-import, etc.)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan app/ directory and output JSON
  python .ralph/scripts/scan_flags.py

  # Scan specific directory
  python .ralph/scripts/scan_flags.py --dir app/services

  # Output as markdown
  python .ralph/scripts/scan_flags.py --format markdown --output flags_report.md

  # Only scan for specific flag types
  python .ralph/scripts/scan_flags.py --types @todo,@fixme
        """
    )

    parser.add_argument(
        "--dir", "-d",
        default="app/",
        help="Directory to scan (default: app/)"
    )

    parser.add_argument(
        "--output", "-o",
        default=".ralph/outputs/flags_found.json",
        help="Output file path (default: .ralph/outputs/flags_found.json)"
    )

    parser.add_argument(
        "--format", "-f",
        choices=["json", "text", "markdown"],
        default="json",
        help="Output format (default: json)"
    )

    parser.add_argument(
        "--types", "-t",
        help="Comma-separated flag types to scan (default: all)"
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="[EXPERIMENTAL] Attempt to fix found flags"
    )

    args = parser.parse_args()

    # Create scanner
    scanner = FlagScanner(args.dir)

    # Filter flag types if specified
    if args.types:
        types_list = [t.strip() for t in args.types.split(",")]
        FLAG_PATTERNS.clear()
        for flag_type in types_list:
            if flag_type in FLAG_PATTERNS or flag_type in ["@skip-import", "@todo", "@clarify", "@review", "@fixme", "@hack", "XXX", "TODO", "FIXME"]:
                FLAG_PATTERNS[flag_type] = FLAG_PATTERNS.get(flag_type, "")

    # Scan directory
    flags = scanner.scan_directory()

    # Generate report
    report = scanner.generate_report()

    # Output format
    if args.format == "json":
        output = json.dumps(report, indent=2)
    elif args.format == "markdown":
        output = scanner.export_markdown(report)
    else:  # text
        output = f"Total flags found: {report['total_flags']}\n"
        for flag_type, count in report['summary'].items():
            output += f"  {flag_type}: {count}\n"

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    with open(output_path, "w") as f:
        f.write(output)

    print(f"Scan complete. Found {report['total_flags']} flags.")
    print(f"Report saved to: {output_path}")

    # Print summary to stdout
    print("\nSummary:")
    for flag_type, count in sorted(report['summary'].items()):
        print(f"  {flag_type}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
