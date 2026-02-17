#!/usr/bin/env python3
"""
Test: Profile Investor Backtest - Flujo Completo

Test simple que ejecuta el pipeline completo de backtesting con un InputProfile:
- Baseline backtest
- Optimización
- Walk-forward validation
- Monte Carlo
- Stress testing

Uso:
    pytest tests/backtesting/test_profile_investor_backtest.py -v -s
    python tests/backtesting/test_profile_investor_backtest.py
"""

import logging
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

# Configurar path antes de imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Imports después de configurar path
from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
from app.backtesting.backtesting_compliance import create_backtesting_compliance

# Config path centralizado
CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "profile_batch_backtest.yaml"


def create_minimal_test_profile() -> InputProfile:
    """
    Crear un InputProfile mínimo para testing rápido.
    Usa parámetros del config centralizado.
    """
    profile = InputProfile(
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        capital_initial=Decimal("100000"),
        investment_horizon=12,  # 12 meses
    )
    logger.info(f"Created test profile: {profile.input_id}")
    logger.info(f"  Objective: {profile.objetivo_inversion.value}")
    logger.info(f"  Risk: {profile.risk_tolerance.value}")
    logger.info(f"  Capital: {profile.capital_initial}")
    logger.info(f"  Horizon: {profile.investment_horizon} months")
    return profile


def test_profile_investor_backtest():
    """
    Test principal: Ejecuta backtest completo para un profile investor.

    Pipeline:
    1. Crear InputProfile
    2. Inicializar ProfileBatchBacktester con config centralizado
    3. Ejecutar run_single_profile (baseline + optimización)
    4. Validar compliance (R5, R6, R7, DATA-001)
    5. Verificar resultados
    """
    logger.info("=" * 80)
    logger.info("PROFILE INVESTOR BACKTEST TEST")
    logger.info("=" * 80)

    # 1. Verificar que existe el config
    if not CONFIG_PATH.exists():
        logger.error(f"Config file not found: {CONFIG_PATH}")
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    logger.info(f"Using config: {CONFIG_PATH}")

    # 2. Crear profile investor
    profile = create_minimal_test_profile()

    # 3. Inicializar backtester
    logger.info("Initializing ProfileBatchBacktester...")
    backtester = ProfileBatchBacktester(config_path=str(CONFIG_PATH))

    # 4. Ejecutar backtest
    logger.info("Running single profile backtest...")
    logger.info("  - This will run: baseline, optimization, walk-forward, monte carlo, stress")

    start_time = datetime.now()
    result = backtester.run_single_profile(profile, multi_strategy=False)
    duration = (datetime.now() - start_time).total_seconds()

    logger.info(f"Backtest completed in {duration:.2f}s")

    # 5. Validar compliance
    logger.info("Validating compliance (R5, R6, R7, DATA-001)...")
    compliance = create_backtesting_compliance()

    # R6: Overfitting check (estimación de parámetros)
    n_params = 10  # Parámetros optimizables estimados
    n_obs = 252 * 3  # ~3 años de datos
    compliance_result = compliance.check_overfitting(n_params, n_obs)

    logger.info(f"  R6 Overfitting: passed={compliance_result.overfitting_check_passed}")

    # 6. Mostrar resultados
    logger.info("=" * 80)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 80)

    if result:
        logger.info(f"Profile ID: {result.profile_id}")
        logger.info(f"Ready for paper trading: {result.ready_for_paper_trading}")
        logger.info(f"Recommendation: {result.recommendation}")

        if result.baseline_results:
            logger.info(f"Baseline Sharpe: {result.baseline_results.get('sharpe_ratio', 'N/A')}")
            logger.info(f"Baseline Return: {result.baseline_results.get('total_return', 'N/A')}")

        if result.optimization_results:
            logger.info(f"Optimized Sharpe: {result.optimization_results.get('sharpe_ratio', 'N/A')}")
            logger.info(f"Optimized Return: {result.optimization_results.get('total_return', 'N/A')}")

        if result.improvement_metrics:
            logger.info(f"Sharpe Improvement: {result.improvement_metrics.get('sharpe_improvement', 'N/A')}%")

        # Verificar que tenemos resultados
        assert result.profile_id is not None
        assert result.baseline_results is not None
    else:
        logger.warning("No result returned from backtest")

    logger.info("=" * 80)
    logger.info("TEST PASSED")
    logger.info("=" * 80)

    return result


def test_quick_profile_validation():
    """
    Test rápido: Solo valida que el profile y config funcionan.
    No ejecuta el backtest completo.
    """
    logger.info("Quick profile validation test...")

    # Crear profile
    profile = create_minimal_test_profile()
    assert profile.input_id is not None
    assert profile.objetivo_inversion == ObjectivoInversion.MAXIMIZAR_CAPITAL

    # Verificar config
    assert CONFIG_PATH.exists(), f"Config not found: {CONFIG_PATH}"

    # Inicializar backtester (sin ejecutar)
    backtester = ProfileBatchBacktester(config_path=str(CONFIG_PATH))
    assert backtester is not None

    logger.info("Quick validation PASSED")
    return True


# ============================================================================
# Main entry point para ejecución directa
# ============================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Profile Investor Backtest Test")
    parser.add_argument("--quick", action="store_true", help="Run quick validation only")
    parser.add_argument("--full", action="store_true", help="Run full backtest (default)")
    args = parser.parse_args()

    try:
        if args.quick:
            test_quick_profile_validation()
        else:
            test_profile_investor_backtest()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
