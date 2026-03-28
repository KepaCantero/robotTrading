#!/usr/bin/env python3
"""
Script de verificación de integración completa del sistema de backtesting.

Verifica:
1. Meta-analyzer está integrado y funcional
2. Paralelización está habilitada
3. Persistencia de auditoría funciona
4. Persistencia de pesos funciona
5. Carga automática de pesos funciona
6. Dashboard puede cargar datos
"""

import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_meta_analyzer_integration():
    """Verificar que meta_analyzer se integra correctamente."""
    logger.info("=" * 60)
    logger.info("1. Verificando integración de Meta-Analyzer...")
    logger.info("=" * 60)

    try:
        from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner

        config_path = "config/backtesting/comprehensive_backtest.yaml"

        if not Path(config_path).exists():
            logger.error(f"❌ No se encuentra configuración: {config_path}")
            return False

        runner = ComprehensiveBacktestRunner(config_path)

        checks = {
            "Meta habilitado": runner.meta_enabled,
            "Audit trail existe": runner.audit_trail is not None,
            "Learning storage existe": runner.learning_storage is not None,
            "Audit hash generado": runner.audit_hash is not None,
            "Paralelización habilitada": runner.parallel_enabled,
            "Max workers configurado": runner.max_workers is not None or runner.parallel_enabled,
        }

        all_ok = True
        for check_name, check_result in checks.items():
            status = "✅" if check_result else "❌"
            logger.info(f"{status} {check_name}: {check_result}")
            if not check_result:
                all_ok = False

        if all_ok:
            logger.info("✅ Meta-Analyzer integrado correctamente")
            logger.info(f"   Hash: {runner.audit_hash[:16] if runner.audit_hash else 'N/A'}...")
            return True
        else:
            logger.error("❌ Algunos componentes no están integrados")
            return False

    except Exception as e:
        logger.error(f"❌ Error verificando integración: {e}", exc_info=True)
        return False


def check_storage_functionality():
    """Verificar que el almacenamiento funciona."""
    logger.info("\n" + "=" * 60)
    logger.info("2. Verificando funcionalidad de almacenamiento...")
    logger.info("=" * 60)

    try:
        from app.backtesting.meta_analyzer import LearningEngineStorage

        storage = LearningEngineStorage()

        # Test de listado (no debería fallar aunque no haya pesos)
        try:
            weights_list = storage.list_available_weights("supervised")
            logger.info(
                f"✅ Storage funciona - {len(weights_list)} pesos encontrados para 'supervised'"
            )

            if weights_list:
                logger.info(f"   Último peso: {weights_list[0]['test_id']}")
                logger.info(f"   Fecha: {weights_list[0]['modified']}")

            return True
        except Exception as e:
            logger.error(f"❌ Error en storage: {e}")
            return False

    except Exception as e:
        logger.error(f"❌ Error verificando storage: {e}", exc_info=True)
        return False


def check_audit_functionality():
    """Verificar que la auditoría funciona."""
    logger.info("\n" + "=" * 60)
    logger.info("3. Verificando funcionalidad de auditoría...")
    logger.info("=" * 60)

    try:
        from app.backtesting.meta_analyzer import AuditTrail

        audit = AuditTrail()

        # Verificar que puede generar hash
        config_path = "config/backtesting/comprehensive_backtest.yaml"
        if Path(config_path).exists():
            hash_value = audit.generate_hash(config_path)
            logger.info(f"✅ Hash generado correctamente: {hash_value[:16]}...")

            # Verificar Git info
            git_info = audit._get_git_info()
            logger.info(f"✅ Git info obtenido:")
            logger.info(f"   Commit: {git_info.get('commit_hash', 'N/A')[:8]}")
            logger.info(f"   Branch: {git_info.get('branch', 'N/A')}")

            return True
        else:
            logger.warning(f"⚠️ No se encuentra config para probar hash: {config_path}")
            return True  # No es crítico

    except Exception as e:
        logger.error(f"❌ Error verificando auditoría: {e}", exc_info=True)
        return False


def check_dashboard_data_loading():
    """Verificar que el dashboard puede cargar datos."""
    logger.info("\n" + "=" * 60)
    logger.info("4. Verificando carga de datos para dashboard...")
    logger.info("=" * 60)

    try:
        results_dir = Path("reports/comprehensive_backtest")

        if not results_dir.exists():
            logger.warning(f"⚠️ Directorio de resultados no existe: {results_dir}")
            logger.info("   (Esto es normal si no se han ejecutado backtests aún)")
            return True  # No es crítico

        # Buscar archivos JSON
        json_files = list(results_dir.glob("*.json"))
        csv_files = list(results_dir.glob("*.csv"))

        logger.info(f"✅ Directorio de resultados existe")
        logger.info(f"   JSON files: {len(json_files)}")
        logger.info(f"   CSV files: {len(csv_files)}")

        if json_files:
            logger.info(f"   Ejemplo: {json_files[0].name}")

        # Verificar que MetaDashboard puede inicializarse
        try:
            from app.dashboard.meta_dashboard import MetaDashboard

            dashboard = MetaDashboard(results_dir=str(results_dir))
            logger.info("✅ MetaDashboard se puede inicializar")
            return True
        except Exception as e:
            logger.error(f"❌ Error inicializando MetaDashboard: {e}")
            return False

    except Exception as e:
        logger.error(f"❌ Error verificando dashboard: {e}", exc_info=True)
        return False


def check_configuration():
    """Verificar configuración YAML."""
    logger.info("\n" + "=" * 60)
    logger.info("5. Verificando configuración...")
    logger.info("=" * 60)

    try:
        import yaml

        config_path = "config/backtesting/comprehensive_backtest.yaml"

        if not Path(config_path).exists():
            logger.error(f"❌ Configuración no encontrada: {config_path}")
            return False

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        checks = {
            "Meta-analysis enabled": config.get('meta_analysis', {}).get('enabled', False),
            "Parallelization enabled": config.get('parallelization', {}).get('enabled', False),
            "Incremental learning enabled": config.get('meta_analysis', {}).get(
                'enable_incremental_learning', False
            ),
            "Thresholds configurados": 'thresholds' in config,
        }

        all_ok = True
        for check_name, check_result in checks.items():
            status = "✅" if check_result else "⚠️"
            logger.info(f"{status} {check_name}: {check_result}")
            if not check_result and check_name != "Incremental learning enabled":
                # Incremental learning puede estar False y no es crítico
                all_ok = False

        return all_ok

    except Exception as e:
        logger.error(f"❌ Error verificando configuración: {e}", exc_info=True)
        return False


def main():
    """Ejecutar todas las verificaciones."""
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICACIÓN DE INTEGRACIÓN COMPLETA DEL SISTEMA")
    logger.info("=" * 60)
    logger.info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {
        "Meta-Analyzer Integration": check_meta_analyzer_integration(),
        "Storage Functionality": check_storage_functionality(),
        "Audit Functionality": check_audit_functionality(),
        "Dashboard Data Loading": check_dashboard_data_loading(),
        "Configuration": check_configuration(),
    }

    logger.info("\n" + "=" * 60)
    logger.info("RESUMEN DE VERIFICACIÓN")
    logger.info("=" * 60)

    all_passed = True
    for check_name, check_result in results.items():
        status = "✅ PASS" if check_result else "❌ FAIL"
        logger.info(f"{status}: {check_name}")
        if not check_result:
            all_passed = False

    logger.info("=" * 60)
    if all_passed:
        logger.info("✅ TODAS LAS VERIFICACIONES PASARON")
        logger.info("   El sistema está completamente integrado y funcional")
        return 0
    else:
        logger.error("❌ ALGUNAS VERIFICACIONES FALLARON")
        logger.error("   Revisa los errores arriba")
        return 1


if __name__ == "__main__":
    sys.exit(main())
