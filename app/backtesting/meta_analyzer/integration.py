"""
Integration helpers para integrar meta_analyzer con ComprehensiveBacktestRunner.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .audit_trail import AuditTrail
from .learning_storage import LearningEngineStorage
from .meta_analyzer import BacktestMetaAnalyzer

logger = logging.getLogger(__name__)


def integrate_meta_analyzer_with_runner(
    runner,
    config_path: str,
    enable_audit: bool = True,
    enable_storage: bool = True,
    enable_analysis: bool = True,
) -> Dict[str, Any]:
    """
    Integrar meta_analyzer con ComprehensiveBacktestRunner.

    Args:
        runner: Instancia de ComprehensiveBacktestRunner
        config_path: Ruta al archivo de configuración YAML
        enable_audit: Habilitar auditoría
        enable_storage: Habilitar almacenamiento de pesos
        enable_analysis: Habilitar análisis posterior

    Returns:
        Dict con instancias creadas
    """
    integration_results = {
        'audit_trail': None,
        'storage': None,
        'analyzer': None,
        'audit_hash': None,
    }

    # 1. Auditoría
    if enable_audit:
        audit_trail = AuditTrail()
        audit_hash = audit_trail.generate_hash(config_path)
        integration_results['audit_trail'] = audit_trail
        integration_results['audit_hash'] = audit_hash
        logger.info(f"✅ Auditoría habilitada: {audit_hash[:16]}...")

    # 2. Almacenamiento de pesos
    if enable_storage:
        storage = LearningEngineStorage()
        integration_results['storage'] = storage
        logger.info("✅ Almacenamiento de pesos habilitado")

    # 3. Analizador meta (para análisis posterior)
    if enable_analysis:
        # El analizador se puede usar después de ejecutar los backtests
        results_dir = (
            runner.output_dir
            if hasattr(runner, 'output_dir')
            else Path("reports/comprehensive_backtest")
        )
        analyzer = BacktestMetaAnalyzer(data_dir=str(results_dir))
        integration_results['analyzer'] = analyzer
        logger.info(f"✅ Analizador meta habilitado: {results_dir}")

    return integration_results


async def save_backtest_audit_and_weights(
    runner,
    audit_trail: AuditTrail,
    storage: Optional[LearningEngineStorage],
    test_result: Dict[str, Any],
    test_type: str,
    learning_engine_name: Optional[str] = None,
    learning_engine_weights: Optional[Any] = None,
) -> None:
    """
    Guardar auditoría y pesos después de un backtest.

    Args:
        runner: ComprehensiveBacktestRunner
        audit_trail: Instancia de AuditTrail
        storage: Instancia de LearningEngineStorage (opcional)
        test_result: Resultados del backtest
        test_type: Tipo de test ejecutado
        learning_engine_name: Nombre del learning engine usado (si aplica)
        learning_engine_weights: Pesos del learning engine (si aplica)
    """
    # Guardar registro de auditoría
    if audit_trail and hasattr(runner, 'config_path'):
        result_path = test_result.get('result_path') or str(runner.output_dir)
        await audit_trail.save_audit_record(
            config_path=runner.config_path,
            hash_value=runner.audit_hash if hasattr(runner, 'audit_hash') else None,
            metadata={
                'test_type': test_type,
                'timestamp': datetime.now().isoformat(),
                'result_summary': {
                    'total_pnl': test_result.get('total_pnl'),
                    'sharpe_ratio': test_result.get('sharpe_ratio'),
                    'total_trades': test_result.get('total_trades'),
                },
            },
            result_path=result_path,
        )

    # Guardar pesos de learning engine
    if storage and learning_engine_name and learning_engine_weights:
        test_id = f"{test_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            await storage.save_weights_async(
                engine_name=learning_engine_name,
                weights=learning_engine_weights,
                test_id=test_id,
                metadata={
                    'test_type': test_type,
                    'timestamp': datetime.now().isoformat(),
                    'result_summary': test_result,
                },
            )
        except (asyncio.TimeoutError, ConnectionError, OSError) as e:
            logger.warning(f"No se pudieron guardar pesos: {e}")
