#!/usr/bin/env python3
"""
Script para comparar todos los reportes de trading generados.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List


def load_reports(results_dir: Path) -> List[Dict]:
    """Cargar todos los reportes JSON del directorio."""
    reports = []
    for report_file in sorted(results_dir.glob("*.json")):
        if report_file.name == "RESUMEN.md":
            continue
        with open(report_file, 'r') as f:
            reports.append(json.load(f))
    return reports


def compare_reports(reports: List[Dict]) -> None:
    """Generar comparación de todos los reportes."""

    print("=" * 100)
    print(" " * 38 + "COMPARATIVA DE PERFILS DE TRADING")
    print("=" * 100)
    print()

    # Tabla comparativa
    print(f"{'#':<3} {'Perfil':<30} {'Capital':>12} {'Objetivo':<25} {'Riesgo':<8} {'Horizonte':<10} {'Target/Mes':>12} {'Profile ID':<25}")
    print("-" * 140)

    for i, report in enumerate(reports, 1):
        name = Path(report.get("_file", "")).stem if "_file" in report else f"Reporte {i}"

        # Extraer info del reporte
        input_data = report.get("input", {})
        profile_data = report.get("profile", {})
        summary = report.get("summary", {})

        capital = input_data.get("capital", 0)
        objective = input_data.get("objective", "N/A")
        risk = input_data.get("risk", "N/A")
        horizon = input_data.get("horizon_months", 0)
        target = input_data.get("target_monthly", 0)
        profile_id = profile_data.get("profile_id", "N/A")
        exec_time = summary.get("execution_time_seconds", 0)
        success_stages = summary.get("successful_stages", 0)

        print(f"{i:<3} {name:<30} €{capital:>10,.0f}  {objective:<25} {risk:<8} {horizon:>5} meses  €{target:>10,.0f}  {profile_id:<25} ({success_stages}/8 stages)")

    print()
    print("=" * 100)
    print("DETALLES POR PERFIL")
    print("=" * 100)
    print()

    for i, report in enumerate(reports, 1):
        print(f"\n{'─' * 100}")
        print(f"PERFIL {i}: {Path(report.get('_file', f'Reporte {i}')).stem}")
        print(f"{'─' * 100}")

        # Input parameters
        input_data = report.get("input", {})
        print(f"📊 Parámetros de Entrada:")
        print(f"   Capital:           €{input_data.get('capital', 0):,.2f}")
        print(f"   Objetivo:          {input_data.get('objective', 'N/A')}")
        print(f"   Riesgo:            {input_data.get('risk', 'N/A')}")
        print(f"   Horizonte:         {input_data.get('horizon_months', 0)} meses")
        print(f"   Target Mensual:    €{input_data.get('target_monthly', 0):,.2f}")

        # Profile
        profile_data = report.get("profile", {})
        print(f"\n🎯 Perfil Generado:")
        print(f"   Profile ID:        {profile_data.get('profile_id', 'N/A')}")

        # Config
        config = report.get("config", {})
        print(f"\n⚙️  Configuración:")
        print(f"   RL Signals:        {'✅' if config.get('enable_rl_signals') else '❌'}")
        print(f"   Tax Optimization:  {'✅' if config.get('enable_tax_optimization') else '❌'}")
        print(f"   Backtest:          {'✅' if config.get('enable_backtest_validation') else '❌'}")
        print(f"   Risk Gates:        {'✅' if config.get('enable_risk_gates') else '❌'}")
        print(f"   Auto-Execute:      {'⚠️  DANGER' if config.get('auto_execute_trades') else '✅ Dry-run'}")
        print(f"   Interactive Brokers: {'✅ Enabled' if config.get('use_ibkr') else '❌ Mock mode'}")

        # Allocation
        allocation = report.get("allocation", {})
        print(f"\n💰 Asignación de Capital:")
        print(f"   Total Posiciones:  {allocation.get('total_positions', 0)}")
        print(f"   Capital Residual:  €{allocation.get('residual_capital', 0):,.2f}")

        # Signals
        signals = report.get("signals", {})
        print(f"\n📡 Señales de Trading:")
        print(f"   Total Señales:     {signals.get('total_signals', 0)}")
        print(f"   BUY:               {signals.get('buy_signals', 0)}")
        print(f"   SELL:              {signals.get('sell_signals', 0)}")
        print(f"   HOLD:              {signals.get('hold_signals', 0)}")
        print(f"   Confianza Promedio: {signals.get('avg_confidence', 0):.2%}")

        # Stages timing
        stages = report.get("stages", {})
        print(f"\n⏱️  Tiempos de Ejecución por Stage:")
        for stage_name, stage_data in stages.items():
            duration = stage_data.get("duration_ms", 0)
            status = "✅" if stage_data.get("success") else "❌"
            print(f"   {status} {stage_name:<25} {duration:>8.2f} ms")

        # Risk
        risk = report.get("risk", {})
        print(f"\n🛡️  Validación de Riesgo:")
        print(f"   Estado:            {'✅ PASSED' if risk.get('passed') else '❌ FAILED'}")
        print(f"   Nivel Riesgo:      {risk.get('risk_level', 'N/A')}")
        print(f"   Violaciones:       {risk.get('violation_count', 0)}")
        print(f"   Advertencias:      {risk.get('warning_count', 0)}")

        # Execution
        execution = report.get("execution", {})
        print(f"\n💱 Ejecución:")
        print(f"   Modo:              {'DRY-RUN' if execution.get('dry_run') else 'LIVE'}")
        print(f"   Órdenes Enviadas:  {execution.get('orders_submitted', 0)}")
        print(f"   Órdenes Ejecutadas:{execution.get('orders_filled', 0)}")
        print(f"   Valor Total:       €{execution.get('total_value_eur', 0):,.2f}")

        # Summary
        summary = report.get("summary", {})
        print(f"\n📊 Resumen:")
        print(f"   Estado:            {'✅ SUCCESS' if summary.get('success') else '❌ FAILED'}")
        print(f"   Tiempo Total:      {summary.get('execution_time_seconds', 0):.2f} segundos")
        print(f"   Stages Exitosos:   {summary.get('successful_stages', 0)}/{summary.get('total_stages', 0)}")

        # Errors and warnings
        errors = summary.get("errors", [])
        warnings = summary.get("warnings", [])
        if errors:
            print(f"\n❌ Errores:")
            for error in errors:
                print(f"   - {error}")
        if warnings:
            print(f"\n⚠️  Advertencias:")
            for warning in warnings:
                print(f"   - {warning}")

    print()
    print("=" * 100)
    print("RESUMEN EJECUTIVO")
    print("=" * 100)

    total_capital = sum(r.get("input", {}).get("capital", 0) for r in reports)
    total_target = sum(r.get("input", {}).get("target_monthly", 0) for r in reports)
    avg_time = sum(r.get("summary", {}).get("execution_time_seconds", 0) for r in reports) / len(reports)
    all_passed = all(r.get("risk", {}).get("passed", False) for r in reports)
    all_success = all(r.get("summary", {}).get("success", False) for r in reports)

    print(f"Total Capital Analizado:     €{total_capital:,.2f}")
    print(f"Total Target Mensual:        €{total_target:,.2f}/mes")
    print(f"Promedio Tiempo Ejecución:   {avg_time:.2f} segundos")
    print(f"Validación Riesgo:           {'✅ TODAS PASARON' if all_passed else '❌ ALGUNAS FALLARON'}")
    print(f"Estado General:              {'✅ TODAS EXITOSAS' if all_success else '❌ ALGUNAS FALLARON'}")
    print()


def main():
    """Función principal."""
    results_dir = Path("results/profile_driven_trading")

    if not results_dir.exists():
        print(f"Error: No existe el directorio {results_dir}")
        return

    reports = load_reports(results_dir)

    if not reports:
        print(f"No se encontraron reportes en {results_dir}")
        return

    # Agregar nombre de archivo a cada reporte
    report_files = sorted(results_dir.glob("*.json"))
    for i, report in enumerate(reports):
        if i < len(report_files):
            report["_file"] = str(report_files[i])

    compare_reports(reports)


if __name__ == "__main__":
    main()
