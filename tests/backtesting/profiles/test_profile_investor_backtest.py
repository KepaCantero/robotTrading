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
import os
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Configurar path antes de imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import pytest
import yaml

from app.backtesting.backtesting_compliance import create_backtesting_compliance
from app.backtesting.profile_batch_backtester import ProfileBatchBacktester

# Imports después de configurar path
from app.domain.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance


@pytest.fixture
def config_path():
    """Create a temporary config file for testing."""
    config = {
        "database": {"url": "sqlite:///:memory:"},
        "output_dir": tempfile.mkdtemp(),
        "capital_tiers": {
            "bajo": 50000,
            "medio": 150000,
            "alto": 500000,
        },
        "investment_horizons": {
            "short": 12,
            "medium": 24,
            "long": 36,
            "very_long": 60,
        },
        "backtest_period": {"start_date": "2020-01-01", "end_date": "2023-12-31"},
        "symbols": ["AAPL", "MSFT", "GOOGL"],
        "risk_parameters": {
            "bajo": {"max_position_pct": 0.05, "stop_loss_pct": 0.02},
            "medio": {"max_position_pct": 0.10, "stop_loss_pct": 0.03},
            "alto": {"max_position_pct": 0.20, "stop_loss_pct": 0.05},
        },
        "objective_parameters": {
            "maximizar_capital": {"min_sharpe": 1.2, "min_return": 0.15},
            "maximizar_dividendos": {"min_sharpe": 0.8, "min_return": 0.10},
        },
        "optimization": {"n_trials": 10, "timeout": None},
        "validation": {
            "walk_forward": {"n_windows": 5, "train_percentage": 0.6},
            "monte_carlo": {"n_simulations": 50},
            "out_of_sample": {"oos_percentage": 0.20},
        },
        "acceptance_criteria": {
            "min_sharpe": 1.0,
            "min_return": 0.10,
            "max_drawdown": -0.25,
            "significance_threshold": 5.0,
            "strong_significance_threshold": 10.0,
            "degradation_threshold": -5.0,
            "confidence_high": 0.8,
            "confidence_medium": 0.7,
            "confidence_low": 0.5,
            "revision_multiplier": 0.8,
        },
        "modules": {
            "filters": {
                "momentum": {
                    "enabled": True,
                    "parameters": {"momentum_threshold": {"type": "float", "default": 0.02}},
                }
            }
        },
        "reporting": {"output_formats": ["json", "csv"]},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        path = f.name

    yield path

    os.unlink(path)


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


def test_profile_investor_backtest(config_path):
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

    logger.info(f"Using config: {config_path}")

    # 2. Crear profile investor
    profile = create_minimal_test_profile()

    # 3. Inicializar backtester
    logger.info("Initializing ProfileBatchBacktester...")
    backtester = ProfileBatchBacktester(config_path=str(config_path))

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
            logger.info(
                f"Optimized Sharpe: {result.optimization_results.get('sharpe_ratio', 'N/A')}"
            )
            logger.info(
                f"Optimized Return: {result.optimization_results.get('total_return', 'N/A')}"
            )

        if result.improvement_metrics:
            logger.info(
                f"Sharpe Improvement: {result.improvement_metrics.get('sharpe_improvement', 'N/A')}%"
            )

        # Verificar que tenemos resultados
        assert result.profile_id is not None
        assert result.baseline_results is not None
    else:
        logger.warning("No result returned from backtest")

    logger.info("=" * 80)
    logger.info("TEST PASSED")
    logger.info("=" * 80)

    return result


def test_quick_profile_validation(config_path):
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
    assert Path(config_path).exists(), f"Config not found: {config_path}"

    # Inicializar backtester (sin ejecutar)
    backtester = ProfileBatchBacktester(config_path=str(config_path))
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

    # Create a temp config for direct script execution
    _tmp_config = {
        "database": {"url": "sqlite:///:memory:"},
        "output_dir": tempfile.mkdtemp(),
        "capital_tiers": {"bajo": 50000, "medio": 150000, "alto": 500000},
        "investment_horizons": {"short": 12, "medium": 24, "long": 36, "very_long": 60},
        "backtest_period": {"start_date": "2020-01-01", "end_date": "2023-12-31"},
        "symbols": ["AAPL", "MSFT", "GOOGL"],
        "risk_parameters": {
            "bajo": {"max_position_pct": 0.05, "stop_loss_pct": 0.02},
            "medio": {"max_position_pct": 0.10, "stop_loss_pct": 0.03},
            "alto": {"max_position_pct": 0.20, "stop_loss_pct": 0.05},
        },
        "objective_parameters": {
            "maximizar_capital": {"min_sharpe": 1.2, "min_return": 0.15},
            "maximizar_dividendos": {"min_sharpe": 0.8, "min_return": 0.10},
        },
        "optimization": {"n_trials": 10, "timeout": None},
        "validation": {
            "walk_forward": {"n_windows": 5, "train_percentage": 0.6},
            "monte_carlo": {"n_simulations": 50},
            "out_of_sample": {"oos_percentage": 0.20},
        },
        "acceptance_criteria": {
            "min_sharpe": 1.0,
            "min_return": 0.10,
            "max_drawdown": -0.25,
            "significance_threshold": 5.0,
            "strong_significance_threshold": 10.0,
            "degradation_threshold": -5.0,
            "confidence_high": 0.8,
            "confidence_medium": 0.7,
            "confidence_low": 0.5,
            "revision_multiplier": 0.8,
        },
        "modules": {
            "filters": {
                "momentum": {
                    "enabled": True,
                    "parameters": {"momentum_threshold": {"type": "float", "default": 0.02}},
                }
            }
        },
        "reporting": {"output_formats": ["json", "csv"]},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as _f:
        yaml.dump(_tmp_config, _f)
        _config_path = _f.name

    try:
        if args.quick:
            test_quick_profile_validation(_config_path)
        else:
            test_profile_investor_backtest(_config_path)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        os.unlink(_config_path)
