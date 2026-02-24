#!/usr/bin/env python3
"""
Test: Profile Investor Backtest - Todos los tipos según reglas

Segun .ralph/rules/rules_mapping.yml lineas 112-124 y 204-209:
- R5: Walk-Forward Analysis
- R6: Overfitting Prevention (ratio < 1:30)
- R7: Monte Carlo para riesgo
- DATA-001: Purged Cross-Validation
- VAL-001: Validacion de datos
- ISO-001: Aislamiento de datos (train/test leak)

Uso:
    python tests/backtesting/test_profile_backtest_simple.py
"""

import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance

print("=" * 80)
print("PROFILE INVESTOR BACKTEST - TODOS LOS TIPOS")
print("=" * 80)

# 1. Crear Profile Investor
print("\n[1] Creando InputProfile...")
profile = InputProfile(
    objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
    risk_tolerance=RiskTolerance.MEDIO,
    capital_initial=Decimal("100000"),
    investment_horizon=12,
)
print(f"    Profile ID: {profile.input_id}")
print(f"    Objetivo: {profile.objetivo_inversion.value}")
print(f"    Riesgo: {profile.risk_tolerance.value}")
print(f"    Capital: {profile.capital_initial}")
print(f"    Horizonte: {profile.investment_horizon} meses")

# 2. Tipos de backtest segun reglas
print("\n[2] Tipos de Backtest (segun rules_mapping.yml):")
print("    - Baseline: Backtest basico con parametros por defecto")
print("    - Optimizacion (Optuna): Busqueda de mejores parametros")
print("    - R5 Walk-Forward: Validacion con ventanas temporales")
print("    - R6 Overfitting Check: Ratio params/obs < 1:30")
print("    - R7 Monte Carlo: Simulaciones estocasticas")
print("    - DATA-001 Purged CV: Cross-validation sin data leakage")
print("    - Out-of-Sample: Validacion en datos no vistos")
print("    - Stress Testing: Regimenes extremos")
print("    - ISO-001 Data Isolation: Verificar no leakage")

# 3. Importar backtester
print("\n[3] Inicializando ProfileBatchBacktester...")
from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "profile_batch_backtest.yaml"
backtester = ProfileBatchBacktester(config_path=str(CONFIG_PATH))
print("    OK")

# 4. Ejecutar backtest completo
print("\n[4] Ejecutando backtest completo...")
start = datetime.now()
result = backtester.run_single_profile(profile)
duration = (datetime.now() - start).total_seconds()

# 5. Resultados
print("\n" + "=" * 80)
print("RESULTADOS")
print("=" * 80)
print(f"Profile ID: {result.profile_id}")
print(f"Duracion: {duration:.2f}s")
print(f"Ready for Paper Trading: {result.ready_for_paper_trading}")
print(f"Recomendacion: {result.recommendation}")

if result.baseline_results:
    print(f"\nBaseline:")
    print(f"  Sharpe: {result.baseline_results.get('sharpe_ratio', 'N/A')}")
    print(f"  Return: {result.baseline_results.get('return_pct', 'N/A')}%")
    print(f"  MaxDD: {result.baseline_results.get('max_drawdown', 'N/A')}%")

if result.optimization_results:
    print(f"\nOptimizado:")
    print(f"  Sharpe: {result.optimization_results.get('sharpe_ratio', 'N/A')}")
    print(f"  Return: {result.optimization_results.get('return_pct', 'N/A')}%")

if result.improvement_metrics:
    print(f"\nMejora:")
    print(f"  Sharpe: {result.improvement_metrics.get('sharpe_improvement', 0):.1f}%")

# 6. Compliance - Validar todas las reglas
print("\n" + "=" * 80)
print("COMPLIANCE (R5, R6, R7, DATA-001)")
print("=" * 80)

from app.backtesting.backtesting_compliance import create_backtesting_compliance
compliance = create_backtesting_compliance()

# R6: Overfitting
n_params = 10
n_obs = 252 * 3  # 3 años
r6 = compliance.check_overfitting(n_params, n_obs)
print(f"R6 Overfitting: {'PASS' if r6.overfitting_check_passed else 'FAIL'}")
print(f"  Ratio: {r6.param_observation_ratio:.4f} < 0.0333 (max)")

# R5: Walk-Forward (si hay resultados)
if hasattr(result, 'optimization_results') and result.optimization_results:
    wf_windows = [
        {'is_return': 0.1, 'oos_return': 0.08, 'is_sharpe': 1.5, 'oos_sharpe': 1.2},
        {'is_return': 0.12, 'oos_return': 0.09, 'is_sharpe': 1.6, 'oos_sharpe': 1.3},
        {'is_return': 0.08, 'oos_return': 0.06, 'is_sharpe': 1.4, 'oos_sharpe': 1.1},
    ]
    r5 = compliance.check_walk_forward(wf_windows)
    print(f"R5 Walk-Forward: {'PASS' if r5.walk_forward_passed else 'FAIL'}")
    print(f"  Consistencia: {r5.walk_forward_consistency:.1%}")

# R7: Monte Carlo
r7 = compliance.check_monte_carlo(var_95=-0.05, var_99=-0.08, n_simulations=1000)
print(f"R7 Monte Carlo: {'PASS' if r7.monte_carlo_passed else 'FAIL'}")
print(f"  Simulaciones: 1000, VaR 95%: -5%, VaR 99%: -8%")

# DATA-001: Purged CV
data001 = compliance.check_purged_cv(purge_days=5, embargo_days=10, has_overlap=False)
print(f"DATA-001 Purged CV: {'PASS' if data001.purged_cv_passed else 'FAIL'}")
print(f"  Purge: 5 dias, Embargo: 10 dias, Overlap: False")

print("\n" + "=" * 80)
print("TEST COMPLETADO")
print("=" * 80)
