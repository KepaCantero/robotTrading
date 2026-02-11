#!/usr/bin/env python3
"""
Trading Rules Extractor - Extrae y prioriza reglas de trading

Este script analiza todos los archivos en rules/trading/ y:
1. Identifica todas las reglas
2. Las clasifica por tipo y prioridad
3. Genera un índice de reglas críticas para backtesting

Usage:
    python trading_rules_extractor.py --output .ralph/outputs/TRADING_RULES_INDEX.json
"""

import argparse
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class RuleCategory(str, Enum):
    """Categorías de reglas de trading."""

    CAPITAL_RISK = "capital_risk"          # Gestión de capital y riesgo
    BACKTESTING = "backtesting"            # Validación y backtesting
    EXECUTION = "execution"                # Ejecución de órdenes
    DATA = "data"                          # Calidad y gestión de datos
    MARKET_ANALYSIS = "market_analysis"    # Análisis de mercado
    STRATEGY = "strategy"                  # Estrategia y señales
    PORTFOLIO = "portfolio"                # Gestión de portafolio
    ML = "machine_learning"                # Machine Learning
    MICROSTRUCTURE = "microstructure"      # Microestructura de mercado
    COMPLIANCE = "compliance"              # Compliance y regulación


class RulePriority(str, Enum):
    """Prioridad de implementación."""

    CRITICAL = "critical"      # MUST implement immediately
    HIGH = "high"             # SHOULD implement soon
    MEDIUM = "medium"         # NICE to have
    LOW = "low"               # Optional/Later


@dataclass
class TradingRule:
    """Representa una regla de trading extraída."""

    id: str                          # ID único (ej: "R1", "CHAN-001")
    title: str                       # Título de la regla
    category: RuleCategory            # Categoría
    priority: RulePriority           # Prioridad
    source_file: str                 # Archivo fuente
    source_line: int                 # Línea en el archivo fuente
    description: str                 # Descripción completa
    is_backtesting_relevant: bool = False  # ¿Es relevante para backtesting?

    # Metadata
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category.value,
            "priority": self.priority.value,
            "source_file": self.source_file,
            "source_line": self.source_line,
            "description": self.description[:200] + "..." if len(self.description) > 200 else self.description,
            "is_backtesting_relevant": self.is_backtesting_relevant,
            "tags": self.tags,
        }


class TradingRulesExtractor:
    """Extrae y prioriza reglas de trading de los archivos MD."""

    # Patrones para detectar reglas
    RULE_PATTERNS = [
        r'^###\s*R(\d+)\.\s*(.+)',           # R1. Kelly Criterion
        r'^###\s*([A-Z]+-\d+):\s*(.+)',      # CHAN-001: Sharpe Ratio
        r'^#{1,3}\s*(\d+)\.\s*(.+)',          # 1. Fundamental Law
        r'^#{1,3}\s*Regla\s+(\d+)[\s\-]+(.+)', # Regla 1 - Multi-Horizon (fixed dash)
        r'^#{1,3}\s*Rule\s+(\d+)[\s\-:]+(.+)',  # Rule 1: Multi-Horizon (fixed dash)
    ]

    BACKTESTING_KEYWORDS = [
        "backtest", "walk-forward", "monte carlo", "out-of-sample",
        "overfitting", "validation", "sharpe", "drawdown",
        "kelly", "position size", "risk-reward", "stop-loss",
    ]

    def __init__(self, rules_dir: Path):
        """Initialize extractor."""
        self.rules_dir = Path(rules_dir).resolve()  # Resolve to absolute path
        self.rules: List[TradingRule] = []
        self.rule_index: Dict[str, TradingRule] = {}

    def extract_all(self) -> List[TradingRule]:
        """Extrae todas las reglas de todos los archivos."""
        md_files = list(self.rules_dir.rglob("*.md"))

        logger.info(f"Found {len(md_files)} markdown files")

        for md_file in md_files:
            self._extract_from_file(md_file)

        # Build index
        for rule in self.rules:
            if rule.id not in self.rule_index:
                self.rule_index[rule.id] = rule

        logger.info(f"Extracted {len(self.rules)} rules total")

        return self.rules

    def _extract_from_file(self, md_file: Path) -> None:
        """Extrae reglas de un archivo específico."""
        try:
            content = md_file.read_text()
            lines = content.split('\n')

            current_section = None
            rule_buffer = []

            for i, line in enumerate(lines, start=1):
                # Detectar sección
                if line.startswith('##'):
                    current_section = line.strip('#').strip()
                    continue

                # Detectar regla - añadir logging para debug
                rule_match = None
                for pattern in self.RULE_PATTERNS:
                    match = re.match(pattern, line, re.IGNORECASE)
                    if match:
                        rule_match = match
                        logger.debug(f"Rule matched: {line.strip()} in {md_file.name}:{i}")
                        break

                if rule_match:
                    # Guardar regla anterior si existe
                    if rule_buffer:
                        self._process_rule_buffer(
                            rule_buffer,
                            str(md_file.relative_to(self.rules_dir.parent.parent)),
                            current_section
                        )
                        rule_buffer = []

                    # Iniciar nueva regla
                    rule_buffer.append({
                        "line": i,
                        "content": line,
                        "section": current_section,
                        "file": str(md_file),  # Usar path completo
                    })
                elif rule_buffer:
                    # Continuar descripción de regla
                    rule_buffer.append({
                        "line": i,
                        "content": line,
                        "section": current_section,
                        "file": str(md_file),  # Usar path completo
                    })

            # Guardar última regla
            if rule_buffer:
                self._process_rule_buffer(
                    rule_buffer,
                    str(md_file.relative_to(self.rules_dir.parent.parent)),
                    current_section
                )

        except Exception as e:
            logger.warning(f"Error processing {md_file}: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    def _process_rule_buffer(self, buffer: List[Dict], file: str, section: str) -> None:
        """Procesa un buffer de líneas que forman una regla."""
        if not buffer:
            return

        first_line = buffer[0]["content"]

        # Extraer ID y título
        rule_id = None
        title = first_line

        for pattern in self.RULE_PATTERNS:
            match = re.match(pattern, first_line, re.IGNORECASE)
            if match:
                if len(match.groups()) >= 2:
                    rule_id = match.group(1)
                    title = match.group(2).strip()
                break

        if not rule_id:
            return  # No es una regla válida

        # Construir descripción
        description = "\n".join(
            b["content"] for b in buffer[1:]
            if b["content"].strip() and not b["content"].startswith('#')
        )

        # Determinar categoría y prioridad
        category = self._classify_rule(title, description, section)
        priority = self._prioritize_rule(title, description, category)

        # Determinar si es relevante para backtesting
        is_backtesting_relevant = self._is_backtesting_relevant(title, description, category)

        # Extraer tags
        tags = self._extract_tags(title, description)

        rule = TradingRule(
            id=rule_id,
            title=title,
            category=category,
            priority=priority,
            source_file=file,
            source_line=buffer[0]["line"],
            description=description,
            is_backtesting_relevant=is_backtesting_relevant,
            tags=tags,
        )

        self.rules.append(rule)

    def _classify_rule(self, title: str, description: str, section: str) -> RuleCategory:
        """Clasifica una regla en una categoría."""
        text = f"{title} {description} {section}".lower()

        if any(kw in text for kw in ["kelly", "position", "drawdown", "risk", "capital"]):
            return RuleCategory.CAPITAL_RISK
        elif any(kw in text for kw in ["backtest", "walk-forward", "monte carlo", "validation"]):
            return RuleCategory.BACKTESTING
        elif any(kw in text for kw in ["execution", "slippage", "spread", "timing"]):
            return RuleCategory.EXECUTION
        elif any(kw in text for kw in ["data", "quality", "cleaning"]):
            return RuleCategory.DATA
        elif any(kw in text for kw in ["regime", "market", "trend", "signal"]):
            return RuleCategory.MARKET_ANALYSIS
        elif any(kw in text for kw in ["machine learning", "neural", "random forest"]):
            return RuleCategory.ML
        elif any(kw in text for kw in ["microstructure", "bid-ask", "order book"]):
            return RuleCategory.MICROSTRUCTURE
        elif any(kw in text for kw in ["portfolio", "diversification", "allocation"]):
            return RuleCategory.PORTFOLIO
        else:
            return RuleCategory.STRATEGY

    def _prioritize_rule(self, title: str, description: str, category: RuleCategory) -> RulePriority:
        """Determina la prioridad de una regla."""
        text = f"{title} {description}".lower()

        # Reglas críticas siempre tienen prioridad alta
        if category == RuleCategory.CAPITAL_RISK:
            return RulePriority.CRITICAL
        elif category == RuleCategory.BACKTESTING:
            return RulePriority.CRITICAL

        # Palabras clave de alta prioridad
        high_priority_keywords = ["must", "always", "never", "critical", "mandatory"]
        if any(kw in text for kw in high_priority_keywords):
            return RulePriority.HIGH

        # Palabras clave de prioridad media
        medium_priority_keywords = ["should", "recommend", "consider"]
        if any(kw in text for kw in medium_priority_keywords):
            return RulePriority.MEDIUM

        return RulePriority.LOW

    def _is_backtesting_relevant(self, title: str, description: str, category: RuleCategory) -> bool:
        """Determina si una regla es relevante para backtesting."""
        if category == RuleCategory.BACKTESTING:
            return True
        if category == RuleCategory.CAPITAL_RISK:
            return True
        if category == RuleCategory.DATA:
            return True

        text = f"{title} {description}".lower()
        return any(kw in text for kw in self.BACKTESTING_KEYWORDS)

    def _extract_tags(self, title: str, description: str) -> List[str]:
        """Extrae tags de una regla."""
        text = f"{title} {description}".lower()
        tags = []

        # Tags comunes
        if "kelly" in text:
            tags.append("kelly")
        if "drawdown" in text:
            tags.append("drawdown")
        if "walk-forward" in text or "walk forward" in text:
            tags.append("walk-forward")
        if "monte carlo" in text:
            tags.append("monte-carlo")
        if "sharpe" in text:
            tags.append("sharpe")
        if "position" in text and "size" in text:
            tags.append("position-sizing")

        return tags

    def get_backtesting_critical_rules(self) -> List[TradingRule]:
        """Obtiene reglas críticas para backtesting."""
        return [
            r for r in self.rules
            if r.is_backtesting_relevant and r.priority in [RulePriority.CRITICAL, RulePriority.HIGH]
        ]

    def generate_index(self, output_path: Path) -> None:
        """Genera un índice JSON de todas las reglas."""
        index = {
            "generated_at": datetime.now().isoformat(),
            "total_rules": len(self.rules),
            "by_category": {},
            "by_priority": {},
            "backtesting_critical": len(self.get_backtesting_critical_rules()),
            "rules": [r.to_dict() for r in self.rules],
        }

        # Agrupar por categoría
        for category in RuleCategory:
            category_rules = [r for r in self.rules if r.category == category]
            index["by_category"][category.value] = len(category_rules)

        # Agrupar por prioridad
        for priority in RulePriority:
            priority_rules = [r for r in self.rules if r.priority == priority]
            index["by_priority"][priority.value] = len(priority_rules)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(index, f, indent=2)

        logger.info(f"Index saved to {output_path}")

    def print_summary(self) -> None:
        """Imprime un resumen de las reglas extraídas."""
        print("\n" + "="*70)
        print("TRADING RULES SUMMARY")
        print("="*70)

        print(f"\nTotal Rules Extracted: {len(self.rules)}")

        print("\nBy Category:")
        for category in RuleCategory:
            count = len([r for r in self.rules if r.category == category])
            print(f"  {category.value}: {count}")

        print("\nBy Priority:")
        for priority in RulePriority:
            count = len([r for r in self.rules if r.priority == priority])
            print(f"  {priority.value}: {count}")

        critical = self.get_backtesting_critical_rules()
        print(f"\nBacktesting Critical: {len(critical)}")

        print("\nTop 10 Critical Rules for Backtesting:")
        for rule in sorted(critical, key=lambda r: r.source_line)[:10]:
            print(f"  {rule.id}: {rule.title}")

        print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Extract and prioritize trading rules")
    parser.add_argument(
        "--rules-dir",
        type=str,
        default="rules/trading",
        help="Path to rules directory"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".ralph/outputs/TRADING_RULES_INDEX.json",
        help="Output JSON file"
    )
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    extractor = TradingRulesExtractor(Path(args.rules_dir))
    extractor.extract_all()
    extractor.print_summary()
    extractor.generate_index(Path(args.output))

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
