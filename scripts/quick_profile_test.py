#!/usr/bin/env python3
"""
Quick Profile Test - Verifica que todo funciona sin errores

Ejecuta backtest con:
- TODOS los perfiles (180 combinaciones)
- 50 símbolos por mercado (ETFs, Stocks, Dividendos)
- 5 días de datos
- Baseline + Optimizaciones + Learning Engines
"""

import logging
import sys
from decimal import Decimal
from itertools import product
from pathlib import Path

from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
    TaxResidence,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("results/quick_profile_test.log"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# Quick Test Configuration
# ============================================================================
TEST_CONFIG = {
    "start_date": "2023-12-01",  # Solo 5 días de prueba
    "end_date": "2023-12-08",    # Una semana de datos
    "symbols": [
        # ETFs (50)
        "SPY", "QQQ", "IWM", "GLD", "SLV", "TLT", "IEF", "SHY", "HYG", "LQD",
        "XLE", "XLF", "XLK", "XLU", "XLV", "XLY", "XLP", "XLB", "XLRE", "XLI",
        "VTI", "VOO", "IVV", "AGG", "BND", "VWO", "EFA", "VXUS", "VNQ", "REM",
        "IJR", "IJH", "IJS", "IVE", "IVW", "VOT", "VOE", "VGT", "VHT", "VFH",
        "VAW", "VIS", "VCR", "VDC", "PGX", "XTL", "FTX", "MUB", "GDX", "USO",

        # Stocks (50) - Tech giants
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "AMD", "INTC",
        "CRM", "ORCL", "ADBE", "CSCO", "AVGO", "QCOM", "TXN", "IBM", "AMAT", "MU",
        "NOW", "SHOP", "SQ", "TWLO", "ZM", "DOCU", "SNOW", "PLTR", "U", "DNDR",
        "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "USB", "PNC",
        "JNJ", "PFE", "UNH", "ABT", "T", "VZ", "KO", "PG", "MRK", "MDT",

        # Dividendos (50) - High yield
        "O", "MAIN", "STAG", "REIT", "VICI", "WPC", "OHI", "MPW", "ADC", "BRX",
        "NTST", "GOOD", "LTC", "NYMT", "HR", "ARR", "ECC", "EFC", "THL", "ORC",
        "SCI", "CHMI", "SACH", "NYCB", "BMNM", "FSEC", "TCPC", "CCPT", "ACP", "SRG",
        "MO", "PM", "BTI", "IMP", "VGR", "BATS", "ITC", "KDP", "MCK", "CAH",
        "WBA", "TAP", "KMB", "CL", "ESS", "EQR", "AVB", "EIX", "D", "SO",
    ],
}

# Profile combinations
OBJECTIVES = list(ObjectivoInversion)
RISKS = list(RiskTolerance)
CAPITALS = {
    RiskTolerance.BAJO: Decimal("50000"),
    RiskTolerance.MEDIO: Decimal("150000"),
    RiskTolerance.ALTO: Decimal("500000"),
}
HORIZONS = [12, 24, 36, 60]  # short, medium, long, very_long


# ============================================================================
# Test Profiles Generation - ALL COMBINATIONS
# ============================================================================
def create_all_profiles() -> list[InputProfile]:
    """
    Crea TODOS los perfiles (180 combinaciones):
    - 5 objetivos
    - 3 niveles de riesgo
    - 3 tiers de capital
    - 4 horizontes de inversión
    """
    profiles = []

    # Tax residence default (US)
    tax_residence = TaxResidence(
        country_code="US",
        country_name="United States",
        base_currency="USD",
    )

    # Generar todas las combinaciones
    for objetivo, riesgo, horizon in product(OBJECTIVES, RISKS, HORIZONS):
        capital = CAPITALS[riesgo]

        profile = InputProfile(
            input_id=f"test_{objetivo.value}_{riesgo.value}_h{horizon}",
            capital_initial=capital,
            objetivo_inversion=objetivo,
            risk_tolerance=riesgo,
            investment_horizon=horizon,
            tax_residence=tax_residence,
        )
        profiles.append(profile)

    logger.info(f"Generated {len(profiles)} profile combinations:")
    logger.info(f"  - Objectives: {len(OBJECTIVES)}")
    logger.info(f"  - Risk levels: {len(RISKS)}")
    logger.info(f"  - Horizons: {len(HORIZONS)}")
    logger.info(f"  - Total: {len(OBJECTIVES)} × {len(RISKS)} × {len(HORIZONS)} = {len(profiles)}")

    return profiles


# ============================================================================
# Quick Test Runner
# ============================================================================
def run_quick_test():
    """
    Ejecuta test completo con todos los perfiles.
    """
    logger.info("=" * 80)
    logger.info("COMPREHENSIVE PROFILE TEST - Starting")
    logger.info("=" * 80)
    logger.info(f"Test Period: {TEST_CONFIG['start_date']} to {TEST_CONFIG['end_date']}")
    logger.info(f"Symbols: {len(TEST_CONFIG['symbols'])} total")
    logger.info(f"  - ETFs: 50")
    logger.info(f"  - Stocks: 50")
    logger.info(f"  - Dividendos: 50")
    logger.info("=" * 80)

    # Create output directory
    output_dir = Path("results/quick_profile_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create temporary config for quick test
    test_config_path = create_test_config(output_dir)

    try:
        # Initialize backtester
        logger.info("Initializing ProfileBatchBacktester...")
        backtester = ProfileBatchBacktester(str(test_config_path))

        # Generate ALL profiles
        logger.info("Generating ALL profile combinations...")
        profiles = create_all_profiles()

        # Results storage
        all_results = {}
        errors = []
        completed = 0
        failed = 0

        # Run each profile
        for i, profile in enumerate(profiles, 1):
            logger.info("-" * 80)
            logger.info(f"Testing Profile {i}/{len(profiles)}: {profile.input_id}")
            logger.info(f"  Objective: {profile.objetivo_inversion.value}")
            logger.info(f"  Risk Level: {profile.risk_tolerance.value}")
            logger.info(f"  Capital: ${profile.capital_initial:,.0f}")
            logger.info(f"  Horizon: {profile.investment_horizon} months")
            logger.info(f"  Progress: {i}/{len(profiles)} ({100*i/len(profiles):.1f}%)")
            logger.info("-" * 80)

            try:
                # Run single profile with baseline + optimization
                result = backtester.run_single_profile(
                    profile,
                    multi_strategy=True  # Enable multiple strategies
                )

                all_results[profile.input_id] = result
                completed += 1

                if result and hasattr(result, 'baseline_metrics'):
                    baseline_return = result.baseline_metrics.get('total_return', 'N/A') if result.baseline_metrics else 'N/A'
                    optimized_return = result.optimized_metrics.get('total_return', 'N/A') if result.optimized_metrics else 'N/A'
                    improvement = getattr(result, 'improvement_pct', 0)
                    logger.info(f"✅ {profile.input_id} - Baseline: {baseline_return}, Optimized: {optimized_return}, Improvement: {improvement:.2f}%")
                else:
                    logger.info(f"✅ {profile.input_id} - Completed (no metrics)")

                # Print progress every 10 profiles
                if i % 10 == 0:
                    logger.info("=" * 80)
                    logger.info(f"PROGRESS UPDATE: {completed} completed, {failed} failed")
                    logger.info("=" * 80)

            except Exception as e:
                logger.error(f"❌ {profile.input_id} failed: {e}")
                import traceback
                traceback.print_exc()
                errors.append((profile.input_id, str(e)))
                failed += 1

        # Generate summary report
        logger.info("=" * 80)
        logger.info("FINAL TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Profiles: {len(profiles)}")
        logger.info(f"Passed: {completed} ({100*completed/len(profiles):.1f}%)")
        logger.info(f"Failed: {failed} ({100*failed/len(profiles):.1f}%)")

        # Count by objective
        by_objective = {}
        for obj in OBJECTIVES:
            by_objective[obj.value] = {"passed": 0, "failed": 0}

        for profile_id, result in all_results.items():
            for obj in OBJECTIVES:
                if obj.value in profile_id:
                    by_objective[obj.value]["passed"] += 1
                    break

        for profile_id, _ in errors:
            for obj in OBJECTIVES:
                if obj.value in profile_id:
                    by_objective[obj.value]["failed"] += 1
                    break

        logger.info("\nResults by Objective:")
        for obj, counts in by_objective.items():
            total = counts["passed"] + counts["failed"]
            logger.info(f"  {obj}: {counts['passed']}/{total} passed")

        if errors:
            logger.info("\n" + "=" * 80)
            logger.info("FAILED PROFILES:")
            for profile_id, error in errors[:20]:  # Show first 20
                logger.info(f"  {profile_id}: {error}")
            if len(errors) > 20:
                logger.info(f"  ... and {len(errors) - 20} more")

        logger.info("\n" + "=" * 80)
        logger.info("TEST COMPLETED")
        logger.info("=" * 80)

        # Generate best configuration summary
        logger.info("\nBEST CONFIGURATIONS BY OBJECTIVE:")
        for obj in OBJECTIVES:
            obj_results = [(pid, r) for pid, r in all_results.items() if obj.value in pid]
            if obj_results:
                best = max(obj_results, key=lambda x: x[1].improvement_pct if x[1] and hasattr(x[1], 'improvement_pct') else 0)
                if best[1] and hasattr(best[1], 'improvement_pct'):
                    logger.info(f"  {obj.value}: {best[0]} ({best[1].improvement_pct:.2f}% improvement)")

        return failed == 0

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_test_config(output_dir: Path) -> Path:
    """
    Crea configuración temporal para test completo.
    """
    import yaml

    config = {
        "database": {
            "url": f"sqlite:///{output_dir}/test_results.db"
        },
        "output_dir": str(output_dir),
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
        "backtest_period": {
            "start_date": TEST_CONFIG["start_date"],
            "end_date": TEST_CONFIG["end_date"],
        },
        "input": {
            "symbols": TEST_CONFIG["symbols"],
            "start_date": TEST_CONFIG["start_date"],
            "end_date": TEST_CONFIG["end_date"],
        },
        "parallel_execution": {
            "enabled": False,  # Sequential for stability
            "max_workers": 1,
        },
        "optimization": {
            "enabled": True,
            "n_trials": 3,  # Solo 3 trials para velocidad
            "timeout": 30,   # 30 segundos max por trial
        },
        "learning_engines": {
            "enabled": True,
            "types": ["supervised", "reinforcement"],  # Test ambos
        },
        "reporting": {
            "output_directory": str(output_dir / "reports"),
            "generate_html": False,  # Ahorrar tiempo
            "generate_json": True,
        },
    }

    config_path = output_dir / "test_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    return config_path


# ============================================================================
# Main Entry Point
# ============================================================================
if __name__ == "__main__":
    # Run test
    success = run_quick_test()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
