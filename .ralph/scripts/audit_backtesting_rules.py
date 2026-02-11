#!/usr/bin/env python3
"""
Backtesting Trading Rules Auditor

Audita los tests de backtesting contra las reglas de trading en rules/trading/.

Usage:
    python .ralph/scripts/audit_backtesting_rules.py
    python .ralph/scripts/audit_backtesting_rules.py --test-file <path>
    python .ralph/scripts/audit_backtesting_rules.py --report-only
"""

import argparse
import ast
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TradingRule:
    """Representa una regla de trading."""
    rule_id: str
    source: str
    description: str
    requirement: str
    category: str  # CRITICAL, IMPORTANT, OPTIONAL


@dataclass
class Violation:
    """Representa una violación de una regla."""
    rule_id: str
    file_path: str
    line_number: int
    severity: str  # CRITICAL, WARNING, INFO
    message: str
    suggestion: str = ""


@dataclass
class TestAuditResult:
    """Resultado de auditoría de un test."""
    file_path: str
    compliant_rules: List[str] = field(default_factory=list)
    violated_rules: List[Violation] = field(default_factory=list)
    missing_rules: List[str] = field(default_factory=list)
    score: float = 0.0
    notes: str = ""  # Additional notes (e.g., component test marker)


class TradingRulesParser:
    """Parsea reglas de trading desde archivos markdown."""

    def __init__(self, rules_dir: Path):
        self.rules_dir = rules_dir
        self.rules: Dict[str, TradingRule] = {}

    def parse_all(self) -> Dict[str, TradingRule]:
        """Parsea todas las reglas de trading."""
        # Reglas específicas de backtesting desde Ernest Chan
        self._parse_ernest_chan_rules()
        # Reglas de Tomasini & Jaekle
        self._parse_tomasini_rules()
        # Reglas de realistic retail trading
        self._parse_realistic_rules()

        logger.info(f"Parsed {len(self.rules)} trading rules")
        return self.rules

    def _parse_ernest_chan_rules(self):
        """Ernest Chan - Algorithmic Trading rules."""
        self.rules["CHAN-001"] = TradingRule(
            rule_id="CHAN-001",
            source="01-ernest-chan-algorithmic-trading.md",
            description="Sharpe Ratio > 1.0 required",
            requirement="if backtest_result.sharpe_ratio < 1.0: reject",
            category="CRITICAL"
        )
        self.rules["CHAN-002"] = TradingRule(
            rule_id="CHAN-002",
            source="01-ernest-chan-algorithmic-trading.md",
            description="Max Drawdown < 25%",
            requirement="if backtest_result.max_drawdown > 0.25: reject",
            category="CRITICAL"
        )
        self.rules["CHAN-003"] = TradingRule(
            rule_id="CHAN-003",
            source="02-ernest-chan-quantitative-trading.md",
            description="Minimum 5 years backtesting data",
            requirement="MIN_BACKTEST_DAYS = 252 * 5",
            category="CRITICAL"
        )

    def _parse_tomasini_rules(self):
        """Tomasini & Jaekle - Designing Trading Systems rules."""
        self.rules["TOM-001"] = TradingRule(
            rule_id="TOM-001",
            source="14-tomasini-jaekle-designing-trading-systems.md",
            description="Event-driven backtesting (not vectorized)",
            requirement="Use event-driven backtest with realistic execution",
            category="CRITICAL"
        )
        self.rules["TOM-002"] = TradingRule(
            rule_id="TOM-002",
            source="14-tomasini-jaekle-designing-trading-systems.md",
            description="Common interface for backtest and live",
            requirement="Same code for backtest and live trading",
            category="IMPORTANT"
        )

    def _parse_realistic_rules(self):
        """Realistic Retail Trading rules."""
        self.rules["RET-001"] = TradingRule(
            rule_id="RET-001",
            source="64-realistic-retail-trading-rules.md",
            description="Walk-forward validation required",
            requirement="Implement walk_forward_backtest() with train/test windows",
            category="CRITICAL"
        )
        self.rules["RET-002"] = TradingRule(
            rule_id="RET-002",
            source="64-realistic-retail-trading-rules.md",
            description="Monte Carlo stress test (1000 simulations)",
            requirement="Execute 1000 Monte Carlo simulations",
            category="IMPORTANT"
        )
        self.rules["RET-003"] = TradingRule(
            rule_id="RET-003",
            source="64-realistic-retail-trading-rules.md",
            description="Include transaction costs",
            requirement="Backtest must include commission and slippage",
            category="CRITICAL"
        )


class BacktestAnalyzer:
    """Analiza archivos de test de backtesting."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text()
        self.tree = ast.parse(self.content)

    def get_imports(self) -> Set[str]:
        """Extrae imports del archivo."""
        imports = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        return imports

    def uses_compliance_engine(self) -> bool:
        """Verifica si usa ComplianceEngine."""
        return "ComplianceEngine" in self.content

    def is_actual_backtest(self) -> bool:
        """
        Verifica si este es un test real de backtesting (no solo test de componentes).

        Un test real de backtesting debe:
        1. Ejecutar una simulación de trading real, O
        2. Llamar a métodos de ejecución como run_backtest(), execute(), etc.

        Excluye:
        - Tests de componentes (ExecutionEngine, CostCalculator, etc.)
        - Tests de validación de datos
        - Tests de configuración
        """
        # Patrones que indican que es SOLO un test de componente
        component_only_patterns = [
            # Tests de ExecutionEngine
            (r'PessimisticExecutionEngine', r'execute_entry_order|process_intra_bar_execution'),
            # Tests de CostCalculator
            (r'CostCalculator', r'calculate_adv_based_slippage|classify_market_cap'),
            # Tests de WalkForwardValidator
            (r'TomasiniWalkForwardValidator', r'create_rolling_windows|validate_strategy'),
            # Tests de data splitting
            (r'TrainValTestSplitter', r'split_data'),
            # Tests de UniverseManager
            (r'UniverseManager', r'get_universe|calculate_survivorship_bias'),
        ]

        # Verificar si es un test de componente solamente
        for component_class, methods in component_only_patterns:
            if re.search(component_class, self.content):
                # Si tiene el componente pero NO ejecuta backtest real, es un test de componente
                if not re.search(r'\.run_backtest\(|\.execute\(|run_backtest\(', self.content):
                    return False

        # Si no tiene patrones de componente, verificar si es backtest real
        # Buscar patrones de ejecución de backtest
        backtest_execution_patterns = [
            r'\.run_backtest\(',
            r'\.execute\(',
            r'backtest\s*=',
            r'result\s*=\s*\w+\.run\(',
        ]

        return any(re.search(p, self.content) for p in backtest_execution_patterns)

    def uses_backtest_engine(self) -> bool:
        """Verifica si usa BacktestEngine/BacktestRunner."""
        return any(name in self.content for name in [
            "BacktestEngine", "SimpleBacktester", "BacktestRunner"
        ])

    def has_sharpe_validation(self) -> bool:
        """Verifica si valida Sharpe Ratio > 1.0."""
        patterns = [
            r"sharpe.*>.*1\.0",
            r"sharpe_ratio.*>.*1",
            r"if.*sharpe",
        ]
        return any(re.search(p, self.content, re.IGNORECASE) for p in patterns)

    def has_drawdown_validation(self) -> bool:
        """Verifica si valida Max Drawdown < 25%."""
        patterns = [
            r"drawdown.*<.*0\.25",
            r"drawdown.*<.*25%",
            r"max_drawdown",
        ]
        return any(re.search(p, self.content, re.IGNORECASE) for p in patterns)

    def has_walk_forward(self) -> bool:
        """Verifica si implementa walk-forward."""
        patterns = [
            r"walk.*forward",
            r"walk_forward",
            r"rolling.*window",
        ]
        return any(re.search(p, self.content, re.IGNORECASE) for p in patterns)

    def has_monte_carlo(self) -> bool:
        """Verifica si implementa Monte Carlo."""
        patterns = [
            r"monte.*carlo",
            r"monte_carlo",
        ]
        return any(re.search(p, self.content, re.IGNORECASE) for p in patterns)

    def has_transaction_costs(self) -> bool:
        """Verifica si incluye costes de transacción."""
        patterns = [
            r"commission",
            r"slippage",
            r"transaction.*cost",
        ]
        return any(re.search(p, self.content, re.IGNORECASE) for p in patterns)

    def has_correlation_id(self) -> bool:
        """Verifica si usa correlation ID (R15)."""
        patterns = [
            r"correlation.*id",
            r"uuid\.uuid4",
        ]
        return any(re.search(p, self.content, re.IGNORECASE) for p in patterns)

    def get_backtest_types(self) -> Set[str]:
        """Identifica tipos de backtest implementados."""
        types = set()
        backtest_types = [
            "baseline", "learning_engines", "walk_forward",
            "monte_carlo", "grid_search", "ablation",
            "out_of_sample", "multi_strategy", "regime",
            "hyperparameter"
        ]
        content_lower = self.content.lower()
        for bt_type in backtest_types:
            if bt_type in content_lower:
                types.add(bt_type)
        return types


class BacktestingAuditor:
    """Auditor principal de backtesting."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.rules_parser = TradingRulesParser(project_root / "rules/trading")
        self.rules = self.rules_parser.parse_all()
        self.results: List[TestAuditResult] = []

    def audit_file(self, file_path: Path) -> TestAuditResult:
        """Audita un archivo específico."""
        logger.info(f"Auditing: {file_path}")

        analyzer = BacktestAnalyzer(file_path)
        result = TestAuditResult(file_path=str(file_path))

        # NUEVO: Verificar si es un test real de backtesting
        # Si es solo un test de componentes, marcarlo apropiadamente
        if not analyzer.is_actual_backtest():
            # No es un backtest real, es un test de componente
            # Marcamos con una nota especial para no contar como violación
            result.notes = "COMPONENT_TEST - Not a backtesting test, skipping ARCH-001"
            logger.info(f"  -> Skipping ARCH-001 check (component test)")
            # No agregamos ARCH-001 a violated_rules
        else:
            # ES un backtest real, verificar que usa BacktestEngine
            if analyzer.uses_backtest_engine():
                result.compliant_rules.append("ARCH-001")
            else:
                result.violated_rules.append(Violation(
                    rule_id="ARCH-001",
                    file_path=str(file_path),
                    line_number=1,
                    severity="CRITICAL",
                    message="Does not use BacktestEngine/SimpleBacktester",
                    suggestion="Use BacktestEngine from app.backtesting.engine which already has ComplianceEngine integrated"
                ))

        # Verificar cada regla de trading
        for rule_id, rule in self.rules.items():
            compliant = False

            if rule_id == "CHAN-001" and analyzer.has_sharpe_validation():
                compliant = True
            elif rule_id == "CHAN-002" and analyzer.has_drawdown_validation():
                compliant = True
            elif rule_id == "CHAN-003" and "MIN_BACKTEST" in analyzer.content:
                compliant = True
            elif rule_id == "TOM-001" and analyzer.uses_backtest_engine():
                compliant = True
            elif rule_id == "RET-001" and analyzer.has_walk_forward():
                compliant = True
            elif rule_id == "RET-002" and analyzer.has_monte_carlo():
                compliant = True
            elif rule_id == "RET-003" and analyzer.has_transaction_costs():
                compliant = True

            if compliant:
                result.compliant_rules.append(rule_id)
            else:
                if rule.category == "CRITICAL":
                    result.violated_rules.append(Violation(
                        rule_id=rule_id,
                        file_path=str(file_path),
                        line_number=1,
                        severity="CRITICAL",
                        message=f"Missing: {rule.description}",
                        suggestion=rule.requirement
                    ))
                else:
                    result.missing_rules.append(rule_id)

        # Calcular score
        total_rules = len(self.rules)
        if total_rules > 0:
            result.score = (len(result.compliant_rules) / total_rules) * 100

        return result

    def audit_all(self, test_dir: Optional[Path] = None) -> List[TestAuditResult]:
        """Audita todos los tests de backtesting."""
        if test_dir is None:
            test_dir = self.project_root / "tests/backtesting"

        # Encontrar todos los tests de backtesting
        test_files = []
        for pattern in ["**/test_*backtest*.py", "**/backtesting/test_*.py"]:
            test_files.extend(test_dir.rglob(pattern.replace("tests/", "")))

        # También buscar en integration
        integration_dir = self.project_root / "tests/integration/backtesting"
        if integration_dir.exists():
            test_files.extend(integration_dir.glob("test_*.py"))

        logger.info(f"Found {len(test_files)} backtesting test files")

        for file_path in test_files:
            if file_path.is_file():
                try:
                    result = self.audit_file(file_path)
                    self.results.append(result)
                except Exception as e:
                    logger.error(f"Error auditing {file_path}: {e}")

        return self.results

    def generate_report(self) -> Dict:
        """Genera reporte de auditoría."""
        total_files = len(self.results)
        total_violations = sum(len(r.violated_rules) for r in self.results)
        avg_score = sum(r.score for r in self.results) / total_files if total_files > 0 else 0

        critical_files = [
            r.file_path for r in self.results
            if any(v.severity == "CRITICAL" for v in r.violated_rules)
        ]

        return {
            "summary": {
                "total_files_audited": total_files,
                "total_critical_violations": total_violations,
                "average_compliance_score": round(avg_score, 2),
                "critical_files_count": len(critical_files),
            },
            "critical_files": critical_files,
            "detailed_results": [
                {
                    "file": r.file_path,
                    "score": r.score,
                    "compliant_rules": r.compliant_rules,
                    "violations": [
                        {
                            "rule_id": v.rule_id,
                            "severity": v.severity,
                            "message": v.message,
                            "suggestion": v.suggestion
                        }
                        for v in r.violated_rules
                    ],
                    "missing_rules": r.missing_rules
                }
                for r in self.results
            ]
        }


def main():
    parser = argparse.ArgumentParser(description="Audit backtesting tests against trading rules")
    parser.add_argument("--test-file", help="Specific test file to audit")
    parser.add_argument("--test-dir", help="Test directory to audit", default="tests/backtesting")
    parser.add_argument("--report-only", action="store_true", help="Only generate report, don't audit")
    parser.add_argument("--output", help="Output report file", default=".ralph/outputs/BACKTESTING_TRADING_RULES_AUDIT.json")

    args = parser.parse_args()

    # Detect project root
    project_root = Path.cwd()
    while not (project_root / "rules" / "trading").exists() and project_root != project_root.parent:
        project_root = project_root.parent

    auditor = BacktestingAuditor(project_root)

    if args.report_only:
        # Generate report from existing results if any
        report = auditor.generate_report()
    else:
        if args.test_file:
            result = auditor.audit_file(Path(args.test_file))
            auditor.results = [result]
        else:
            auditor.audit_all(Path(args.test_dir))
        report = auditor.generate_report()

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # JSON report
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    # Markdown report
    md_path = output_path.with_suffix('.md')
    with open(md_path, 'w') as f:
        f.write("# Backtesting Trading Rules Audit Report\n\n")
        f.write(f"**Generated:** {Path.cwd()}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total Files Audited: {report['summary']['total_files_audited']}\n")
        f.write(f"- Critical Violations: {report['summary']['total_critical_violations']}\n")
        f.write(f"- Avg Compliance Score: {report['summary']['average_compliance_score']}%\n")
        f.write(f"- Critical Files: {report['summary']['critical_files_count']}\n\n")

        if report['critical_files']:
            f.write("## Critical Files\n\n")
            for file in report['critical_files']:
                f.write(f"- `{file}`\n")

        f.write("\n## Detailed Results\n\n")
        for result in report['detailed_results']:
            f.write(f"### {result['file']}\n\n")
            f.write(f"**Score:** {result['score']}%\n\n")
            if result['violations']:
                f.write("**Violations:**\n\n")
                for v in result['violations']:
                    f.write(f"- **[{v['rule_id']}] ({v['severity']})** {v['message']}\n")
                    if v['suggestion']:
                        f.write(f"  - Suggestion: {v['suggestion']}\n")
                f.write("\n")
            if result['missing_rules']:
                f.write(f"**Missing Rules:** {', '.join(result['missing_rules'])}\n\n")

    logger.info(f"Report saved to: {output_path}")
    logger.info(f"Markdown report saved to: {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
