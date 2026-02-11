#!/usr/bin/env python3
"""
Backtesting Cleanup Tool

Identifica y limpia/elimina tests de backtesting obsoletos que no aportan valor.

Criteria for obsolescence:
1. Tests que no han sido ejecutados en >6 meses
2. Tests duplicados (mismo functionality)
3. Tests que usan arquitecturas deprecadas
4. Tests en scripts/archived/ que pueden ser eliminados
5. Tests con <10% de compliance score

Usage:
    python .ralph/scripts/cleanup_obsolete_backtests.py --dry-run
    python .ralph/scripts/cleanup_obsolete_backtests.py --clean
    python .ralph/scripts/cleanup_obsolete_backtests.py --audit-file <path>
"""

import argparse
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ObsoleteTest:
    """Representa un test obsoleto."""
    file_path: str
    reason: str
    severity: str  # DELETE, ARCHIVE, KEEP
    last_modified: Optional[str] = None
    duplicate_of: Optional[str] = None
    replacement: Optional[str] = None


class BacktestCleanupAnalyzer:
    """Analiza tests de backtesting para identificar obsoletos."""

    def __init__(self, project_root: Path, audit_file: Optional[Path] = None):
        self.project_root = project_root
        self.audit_data = self._load_audit(audit_file) if audit_file else None
        self.obsolete_tests: List[ObsoleteTest] = []

    def _load_audit(self, audit_file: Path) -> Optional[Dict]:
        """Carga datos de auditoría previa."""
        if audit_file.exists():
            with open(audit_file) as f:
                return json.load(f)
        return None

    def find_all_backtest_files(self) -> List[Path]:
        """Encuentra todos los archivos relacionados con backtesting."""
        files = []

        # Tests
        for pattern in [
            "tests/**/test_*backtest*.py",
            "tests/**/backtesting/test_*.py",
            "tests/integration/backtesting/*.py",
            "tests/unit/backtesting/*.py",
        ]:
            files.extend(self.project_root.rglob(pattern))

        # Scripts
        for pattern in [
            "scripts/**/backtest*.py",
            "scripts/**/*backtest*.py",
        ]:
            files.extend(self.project_root.rglob(pattern))

        # Archived
        archived = self.project_root / "scripts/archived"
        if archived.exists():
            files.extend(archived.glob("*backtest*.py"))
            files.extend(archived.glob("*comprehensive*.py"))

        return [f for f in files if f.is_file()]

    def analyze_file(self, file_path: Path) -> ObsoleteTest:
        """Analiza un archivo para determinar si es obsoleto."""
        content = file_path.read_text()
        last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
        age_days = (datetime.now() - last_modified).days

        # Criterio 1: Archivos en scripts/archived/
        if "scripts/archived" in str(file_path):
            return ObsoleteTest(
                file_path=str(file_path),
                reason="In archived folder - can be deleted if replaced",
                severity="ARCHIVE",
                last_modified=last_modified.isoformat()
            )

        # Criterio 2: No ejecutado en >6 meses
        if age_days > 180:
            return ObsoleteTest(
                file_path=str(file_path),
                reason=f"Not modified in {age_days} days (>6 months)",
                severity="ARCHIVE",
                last_modified=last_modified.isoformat()
            )

        # Criterio 3: Usa arquitecturas deprecadas
        deprecated_patterns = [
            "ComprehensiveBacktestRunner",  # Ya no se debe usar directamente
            "from app.backtesting.comprehensive_backtest_runner import",
        ]
        if any(p in content for p in deprecated_patterns):
            # Verificar si usa BacktestEngine correctamente
            if "BacktestEngine" not in content and "SimpleBacktester" not in content:
                return ObsoleteTest(
                    file_path=str(file_path),
                    reason="Uses deprecated ComprehensiveBacktestRunner directly",
                    severity="DELETE",
                    last_modified=last_modified.isoformat(),
                    replacement="Use BacktestEngine from app.backtesting.engine"
                )

        # Criterio 4: Bajo compliance score (si hay auditoría)
        if self.audit_data:
            for result in self.audit_data.get("detailed_results", []):
                if result["file"] == str(file_path):
                    if result["score"] < 10:
                        return ObsoleteTest(
                            file_path=str(file_path),
                            reason=f"Very low compliance score ({result['score']}%)",
                            severity="ARCHIVE",
                            last_modified=last_modified.isoformat()
                        )

        # Criterio 5: Tests duplicados (por nombre)
        filename = file_path.name
        # Buscar duplicados en otras ubicaciones
        similar_files = [
            f for f in self.find_all_backtest_files()
            if f.name == filename and f != file_path
        ]
        if similar_files:
            # Mantener el más reciente
            similar_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            if file_path != similar_files[0]:  # No es el más reciente
                return ObsoleteTest(
                    file_path=str(file_path),
                    reason=f"Duplicate of newer file: {similar_files[0]}",
                    severity="DELETE",
                    last_modified=last_modified.isoformat(),
                    duplicate_of=str(similar_files[0])
                )

        # No es obsoleto
        return ObsoleteTest(
            file_path=str(file_path),
            reason="Active test - keep",
            severity="KEEP",
            last_modified=last_modified.isoformat()
        )

    def analyze_all(self) -> List[ObsoleteTest]:
        """Analiza todos los archivos."""
        files = self.find_all_backtest_files()
        logger.info(f"Found {len(files)} backtesting-related files")

        for file_path in files:
            try:
                result = self.analyze_file(file_path)
                if result.severity in ["DELETE", "ARCHIVE"]:
                    self.obsolete_tests.append(result)
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")

        return self.obsolete_tests

    def generate_cleanup_plan(self) -> Dict:
        """Genera plan de limpieza."""
        to_delete = [t for t in self.obsolete_tests if t.severity == "DELETE"]
        to_archive = [t for t in self.obsolete_tests if t.severity == "ARCHIVE"]

        return {
            "summary": {
                "total_obsolete": len(self.obsolete_tests),
                "recommended_delete": len(to_delete),
                "recommended_archive": len(to_archive),
                "estimated_freed_space_mb": self._estimate_freed_space()
            },
            "delete": [
                {
                    "file": t.file_path,
                    "reason": t.reason,
                    "replacement": t.replacement,
                    "duplicate_of": t.duplicate_of
                }
                for t in to_delete
            ],
            "archive": [
                {
                    "file": t.file_path,
                    "reason": t.reason,
                    "last_modified": t.last_modified
                }
                for t in to_archive
            ]
        }

    def _estimate_freed_space(self) -> float:
        """Estima el espacio que se liberaría."""
        total_bytes = sum(
            Path(t.file_path).stat().st_size
            for t in self.obsolete_tests
        )
        return round(total_bytes / (1024 * 1024), 2)

    def execute_cleanup(self, cleanup_plan: Dict, dry_run: bool = True) -> List[str]:
        """Ejecuta el plan de limpieza."""
        actions = []

        archive_dir = self.project_root / "scripts" / "archived" / "cleanup_$(date +%Y%m%d)"
        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)

        # Delete files
        for item in cleanup_plan["delete"]:
            file_path = Path(item["file"])
            if file_path.exists():
                if not dry_run:
                    # Backup first
                    backup_path = archive_dir / file_path.name
                    shutil.copy2(file_path, backup_path)
                    file_path.unlink()
                actions.append(f"DELETE: {file_path}")

        # Archive files
        for item in cleanup_plan["archive"]:
            file_path = Path(item["file"])
            if file_path.exists() and not file_path.parent.name == "archived":
                if not dry_run:
                    # Move to archive
                    archive_path = archive_dir / file_path.name
                    shutil.move(str(file_path), str(archive_path))
                actions.append(f"ARCHIVE: {file_path}")

        return actions


def main():
    parser = argparse.ArgumentParser(description="Cleanup obsolete backtesting tests")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Show what would be deleted without actually deleting")
    parser.add_argument("--clean", action="store_true",
                        help="Actually execute the cleanup")
    parser.add_argument("--audit-file",
                        help="Path to audit JSON file",
                        default=".ralph/outputs/BACKTESTING_TRADING_RULES_AUDIT.json")
    parser.add_argument("--output",
                        help="Output cleanup plan file",
                        default=".ralph/outputs/BACKTESTING_CLEANUP_PLAN.json")

    args = parser.parse_args()

    if args.clean:
        args.dry_run = False

    # Detect project root
    project_root = Path.cwd()
    while not (project_root / "rules" / "trading").exists() and project_root != project_root.parent:
        project_root = project_root.parent

    analyzer = BacktestCleanupAnalyzer(
        project_root,
        Path(args.audit_file) if Path(args.audit_file).exists() else None
    )

    logger.info("Analyzing backtesting files...")
    analyzer.analyze_all()

    cleanup_plan = analyzer.generate_cleanup_plan()

    # Save plan
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(cleanup_plan, f, indent=2)

    # Generate markdown report
    md_path = output_path.with_suffix('.md')
    with open(md_path, 'w') as f:
        f.write("# Backtesting Cleanup Plan\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total Obsolete Files: {cleanup_plan['summary']['total_obsolete']}\n")
        f.write(f"- Recommended Delete: {cleanup_plan['summary']['recommended_delete']}\n")
        f.write(f"- Recommended Archive: {cleanup_plan['summary']['recommended_archive']}\n")
        f.write(f"- Estimated Freed Space: {cleanup_plan['summary']['estimated_freed_space_mb']} MB\n\n")

        if cleanup_plan['delete']:
            f.write("## Files to DELETE\n\n")
            for item in cleanup_plan['delete']:
                f.write(f"### `{item['file']}`\n\n")
                f.write(f"**Reason:** {item['reason']}\n\n")
                if item.get('replacement'):
                    f.write(f"**Replacement:** {item['replacement']}\n\n")
                if item.get('duplicate_of'):
                    f.write(f"**Duplicate of:** `{item['duplicate_of']}`\n\n")

        if cleanup_plan['archive']:
            f.write("## Files to ARCHIVE\n\n")
            for item in cleanup_plan['archive']:
                f.write(f"### `{item['file']}`\n\n")
                f.write(f"**Reason:** {item['reason']}\n\n")
                f.write(f"**Last Modified:** {item['last_modified']}\n\n")

    logger.info(f"Cleanup plan saved to: {output_path}")
    logger.info(f"Markdown report saved to: {md_path}")

    # Execute cleanup if requested
    if args.clean or not args.dry_run:
        logger.info("Executing cleanup...")
        if args.dry_run:
            logger.info("DRY RUN - No files will be actually deleted")

        actions = analyzer.execute_cleanup(cleanup_plan, dry_run=args.dry_run)

        # Log actions
        log_path = output_path.parent / "cleanup_actions.log"
        with open(log_path, 'w') as f:
            f.write(f"# Cleanup Actions - {datetime.now().isoformat()}\n\n")
            f.write(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}\n\n")
            for action in actions:
                f.write(f"{action}\n")

        logger.info(f"Actions logged to: {log_path}")
        logger.info(f"Total actions: {len(actions)}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
