#!/usr/bin/env python3
"""
Simple Trading Rules Index - Índice simple de las reglas críticas para backtesting

Basado en 64-realistic-retail-trading-rules.md (29 reglas R1-R29)

Este módulo define las reglas críticas que DEBEN validarse en backtesting.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class RuleCategory(str, Enum):
    """Categorías de reglas."""
    CAPITAL_RISK = "capital_risk"
    BACKTESTING = "backtesting"
    EXECUTION = "execution"
    DATA = "data"
    MARKET_ANALYSIS = "market_analysis"


class RulePriority(str, Enum):
    """Prioridad de implementación."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TradingRule:
    """Representa una regla de trading."""
    id: str
    title: str
    category: RuleCategory
    priority: RulePriority
    description: str
    validation_method: str  # "compliance_engine", "test", "config"


# ==============================================================================
# REGLAS CRÍTICAS PARA BACKTESTING (64-realistic-retail-trading-rules.md)
# ==============================================================================

BACKTESTING_CRITICAL_RULES: List[TradingRule] = [
    # BLOQUE 1: GESTIÓN DE CAPITAL Y RIESGO (R1-R4)
    TradingRule(
        id="R1",
        title="Kelly Criterion + Tamaño Máximo de Posición",
        category=RuleCategory.CAPITAL_RISK,
        priority=RulePriority.CRITICAL,
        description="Usar Kelly Criterion fraccional (25-50%). NUNCA arriesgar más del 2% del capital por trade. Máximo 20% del capital en una sola posición.",
        validation_method="compliance_engine",
    ),
    TradingRule(
        id="R2",
        title="Drawdown Máximo - Stop Trading Automático",
        category=RuleCategory.CAPITAL_RISK,
        priority=RulePriority.CRITICAL,
        description="Drawdown warning al 15%, parada automática al 25%. Kill switch que detiene trading.",
        validation_method="compliance_engine",
    ),
    TradingRule(
        id="R3",
        title="Correlación y Concentración Máxima",
        category=RuleCategory.CAPITAL_RISK,
        priority=RulePriority.HIGH,
        description="Límites de posición según fase de capital: 1k-10k (max 2 posiciones, 40% sector), 10k-50k (max 3 posiciones, 35% sector), 50k-500k (max 5 posiciones, 25% sector).",
        validation_method="config",
    ),
    TradingRule(
        id="R4",
        title="Ratio Riesgo/Beneficio Mínimo 2:1",
        category=RuleCategory.CAPITAL_RISK,
        priority=RulePriority.CRITICAL,
        description="NUNCA entrar en trade con R:R < 2:1. Para setups de alta probabilidad (>80%), permitir 1.5:1.",
        validation_method="compliance_engine",
    ),

    # BLOQUE 2: BACKTESTING Y VALIDACIÓN (R5-R7)
    TradingRule(
        id="R5",
        title="Walk-Forward Analysis",
        category=RuleCategory.BACKTESTING,
        priority=RulePriority.CRITICAL,
        description="SIEMPRE validar con Walk-Forward Analysis. 70% train, 30% test. Mínimo 60 períodos de train. Degradación OOS no debe exceder 30%.",
        validation_method="test",
    ),
    TradingRule(
        id="R6",
        title="Prevención de Overfitting",
        category=RuleCategory.BACKTESTING,
        priority=RulePriority.HIGH,
        description="Validar ratio parámetros/datos < 1:30. Usar Purged Cross-Validation con embargo temporal.",
        validation_method="test",
    ),
    TradingRule(
        id="R7",
        title="Monte Carlo para Riesgo",
        category=RuleCategory.BACKTESTING,
        priority=RulePriority.CRITICAL,
        description="Ejecutar 1000 simulaciones Monte Carlo para estimar distribución de métricas.",
        validation_method="test",
    ),

    # BLOQUE 3: EJECUCIÓN Y GESTIÓN (R8-R13)
    TradingRule(
        id="R8",
        title="Gestión de Spread Bid-Ask",
        category=RuleCategory.EXECUTION,
        priority=RulePriority.MEDIUM,
        description="Gestionar spread bid-ask en la ejecución. Usar límites de orden.",
        validation_method="config",
    ),
    TradingRule(
        id="R9",
        title="Timing de Ejecución",
        category=RuleCategory.EXECUTION,
        priority=RulePriority.MEDIUM,
        description="Ejecutar órdenes en momentos óptimos para minimizar slippage.",
        validation_method="config",
    ),
    TradingRule(
        id="R10",
        title="Slippage Máximo 0.1%",
        category=RuleCategory.EXECUTION,
        priority=RulePriority.HIGH,
        description="Slippage máximo del 0.1% en la ejecución.",
        validation_method="config",
    ),
    TradingRule(
        id="R11",
        title="Trailing Stop Dinámico",
        category=RuleCategory.EXECUTION,
        priority=RulePriority.MEDIUM,
        description="Implementar trailing stop que se ajusta con el precio a favor.",
        validation_method="test",
    ),
    TradingRule(
        id="R12",
        title="Take Profit Parcial",
        category=RuleCategory.EXECUTION,
        priority=RulePriority.MEDIUM,
        description="Cerrar parcialmente posiciones en ganancias para reducir riesgo.",
        validation_method="test",
    ),
    TradingRule(
        id="R13",
        title="Pyramiding - Añadir a Ganadores",
        category=RuleCategory.EXECUTION,
        priority=RulePriority.LOW,
        description="Añadir a posiciones ganadoras conforme se mueve el stop loss.",
        validation_method="test",
    ),

    # BLOQUE 4: DATOS Y LOGGING (R14-R18)
    TradingRule(
        id="R14",
        title="Calidad de Datos",
        category=RuleCategory.DATA,
        priority=RulePriority.HIGH,
        description="Validar calidad de datos: sin missing values, sin outliers extremos, timestamps consistentes.",
        validation_method="test",
    ),
    TradingRule(
        id="R15",
        title="Logging Completo",
        category=RuleCategory.DATA,
        priority=RulePriority.HIGH,
        description="Registrar TODAS las decisiones de trading con timestamps.",
        validation_method="config",
    ),
    TradingRule(
        id="R16",
        title="Reconciliación Diaria",
        category=RuleCategory.DATA,
        priority=RulePriority.MEDIUM,
        description="Reconciliar posiciones diariamente contra broker.",
        validation_method="test",
    ),
    TradingRule(
        id="R17",
        title="Sin Emociones - Control Automático",
        category=RuleCategory.DATA,
        priority=RulePriority.CRITICAL,
        description="TODO automatizado. Sin intervención manual en decisiones de trading.",
        validation_method="architecture",
    ),
    TradingRule(
        id="R18",
        title="Journal de Trades",
        category=RuleCategory.DATA,
        priority=RulePriority.LOW,
        description="Mantener journal de trades con razón de entrada/exit.",
        validation_method="output",
    ),

    # BLOQUE 5: ANÁLISIS DE MERCADO (R19-R24)
    TradingRule(
        id="R19",
        title="Identificación de Régimen de Mercado",
        category=RuleCategory.MARKET_ANALYSIS,
        priority=RulePriority.HIGH,
        description="Identificar régimen de mercado (bull, bear, sideways) y ajustar estrategia.",
        validation_method="test",
    ),
    TradingRule(
        id="R20",
        title="Confirmación Múltiple",
        category=RuleCategory.MARKET_ANALYSIS,
        priority=RulePriority.MEDIUM,
        description="Requerir confirmación de múltiples indicadores antes de entrar.",
        validation_method="config",
    ),
    TradingRule(
        id="R21",
        title="Volumen como Filtro",
        category=RuleCategory.MARKET_ANALYSIS,
        priority=RulePriority.MEDIUM,
        description="Filtrar señales por volumen. Solo trade cuando hay volumen suficiente.",
        validation_method="config",
    ),
    TradingRule(
        id="R22",
        title="Revisión Mensual",
        category=RuleCategory.MARKET_ANALYSIS,
        priority=RulePriority.LOW,
        description="Revisar rendimiento mensualmente y ajustar parámetros si es necesario.",
        validation_method="output",
    ),
    TradingRule(
        id="R23",
        title="A/B Testing",
        category=RuleCategory.MARKET_ANALYSIS,
        priority=RulePriority.LOW,
        description="Ejecutar A/B testing de diferentes variantes de estrategia.",
        validation_method="test",
    ),
    TradingRule(
        id="R24",
        title="Diversificación de Estrategias",
        category=RuleCategory.MARKET_ANALYSIS,
        priority=RulePriority.MEDIUM,
        description="Diversificar entre múltiples estrategias no correlacionadas.",
        validation_method="config",
    ),

    # Reglas adicionales (R28-R29)
    TradingRule(
        id="R28",
        title="Registro de Operaciones",
        category=RuleCategory.DATA,
        priority=RulePriority.HIGH,
        description="Registrar todas las operaciones con timestamps y metadata.",
        validation_method="output",
    ),
    TradingRule(
        id="R29",
        title="Seguridad de API Keys",
        category=RuleCategory.DATA,
        priority=RulePriority.CRITICAL,
        description="Proteger API keys. Nunca hardcodear. Usar environment variables.",
        validation_method="architecture",
    ),
]


def get_rules_by_category(category: RuleCategory) -> List[TradingRule]:
    """Obtiene reglas por categoría."""
    return [r for r in BACKTESTING_CRITICAL_RULES if r.category == category]


def get_rules_by_priority(priority: RulePriority) -> List[TradingRule]:
    """Obtiene reglas por prioridad."""
    return [r for r in BACKTESTING_CRITICAL_RULES if r.priority == priority]


def get_critical_rules() -> List[TradingRule]:
    """Obtiene reglas críticas para backtesting."""
    return [r for r in BACKTESTING_CRITICAL_RULES if r.priority in [RulePriority.CRITICAL, RulePriority.HIGH]]


def print_rules_summary():
    """Imprime resumen de reglas."""
    print("\n" + "="*70)
    print("TRADING RULES FOR BACKTESTING - SUMMARY")
    print("="*70)

    print(f"\nTotal Rules: {len(BACKTESTING_CRITICAL_RULES)}")

    print("\nBy Category:")
    for cat in RuleCategory:
        rules = get_rules_by_category(cat)
        if rules:
            print(f"  {cat.value}: {len(rules)}")

    print("\nBy Priority:")
    for pri in RulePriority:
        rules = get_rules_by_priority(pri)
        if rules:
            print(f"  {pri.value}: {len(rules)}")

    critical = get_critical_rules()
    print(f"\nCritical for Backtesting: {len(critical)}")

    print("\n" + "="*70)


if __name__ == "__main__":
    print_rules_summary()
