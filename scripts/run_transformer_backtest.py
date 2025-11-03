#!/usr/bin/env python3
"""
Script para ejecutar SOLO el backtest de Transformer con Simple Strategy y Baseline

Uso:
    python scripts/run_transformer_backtest.py
"""

import sys
import os
import logging
from pathlib import Path

# CRÍTICO: Configurar variables de entorno ANTES de cualquier import
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
os.environ.setdefault('NUMEXPR_MAX_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('VECLIB_MAXIMUM_THREADS', '1')
if 'CUDA_VISIBLE_DEVICES' not in os.environ:
    os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Configurar logging PRIMERO
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

logger = logging.getLogger(__name__)
logger.info("🚀 Iniciando Transformer Backtest (Simple Strategy + Baseline)...")

# Agregar raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
    logger.info("✅ ComprehensiveBacktestRunner importado")
except Exception as e:
    logger.error(f"❌ Error importando ComprehensiveBacktestRunner: {e}", exc_info=True)
    raise

def main():
    """Ejecutar solo el backtest de Transformer con Baseline."""
    config_path = project_root / "config" / "backtesting" / "comprehensive_backtest.yaml"
    
    if not config_path.exists():
        logger.error(f"❌ Archivo de configuración no encontrado: {config_path}")
        return
    
    logger.info(f"📋 Configuración: {config_path}")
    
    try:
        # Crear runner
        runner = ComprehensiveBacktestRunner(str(config_path))
        
        # Ejecutar SOLO el test de Transformer
        logger.info("📊 Ejecutando Transformer Backtest (Simple Strategy + Baseline)...")
        logger.info("=" * 80)
        
        # Temporalmente modificar config para solo habilitar "transformer"
        original_config = runner.config.get('learning_engines', {}).copy()
        
        # Deshabilitar todos excepto "transformer"
        for engine_name in ['supervised', 'deep', 'reinforcement']:
            if engine_name in runner.config.get('learning_engines', {}):
                runner.config['learning_engines'][engine_name]['enabled'] = False
        
        # Asegurar que "transformer" esté habilitado
        if 'transformer' not in runner.config.get('learning_engines', {}):
            logger.error("❌ Transformer learning engine no está configurado en learning_engines")
            return
        runner.config['learning_engines']['transformer']['enabled'] = True
        logger.info("✅ Transformer learning engine habilitado (otros deshabilitados temporalmente)")
        
        # Ejecutar learning engines (solo ejecutará "transformer")
        results = runner.run_learning_engines_backtest()
        
        # Restaurar configuración original
        runner.config['learning_engines'] = original_config
        
        # Filtrar solo resultados de "transformer"
        transformer_results = [r for r in results if r.get('learning_engine') == 'transformer']
        
        if transformer_results:
            result = transformer_results[0]
            logger.info("=" * 80)
            logger.info("📊 RESULTADOS - Transformer Engine (Simple Strategy)")
            logger.info("=" * 80)
            logger.info(f"Test Name: {result.get('test_name', 'Unknown')}")
            logger.info(f"Total PnL: ${result.get('total_pnl', 0):,.2f}")
            logger.info(f"Return %: {result.get('return_pct', 0):.2f}%")
            logger.info(f"Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}")
            logger.info(f"Sortino Ratio: {result.get('sortino_ratio', 0):.2f}")
            logger.info(f"Max Drawdown: {result.get('max_drawdown', 0):.2f}%")
            logger.info(f"Win Rate: {result.get('win_rate', 0):.2f}%")
            logger.info(f"Total Trades: {result.get('total_trades', 0)}")
            logger.info(f"Profit Factor: {result.get('profit_factor', 0):.2f}")
            
            # Mostrar comparativa antes/después si existe
            if 'before_training_metrics' in result:
                logger.info("=" * 80)
                logger.info("📈 COMPARATIVA (Baseline vs Transformer)")
                logger.info("=" * 80)
                before = result['before_training_metrics']
                after = result['after_training_metrics']
                improvement = result.get('improvement_pct', {})
                
                logger.info("BASELINE (Sin Transformer):")
                logger.info(f"  Sharpe Ratio: {before.get('sharpe_ratio', 0):.2f}")
                logger.info(f"  Return %: {before.get('return_pct', 0):.2f}%")
                logger.info(f"  Total PnL: ${before.get('total_pnl', 0):,.2f}")
                logger.info(f"  Win Rate: {before.get('win_rate', 0):.2f}%")
                
                logger.info("\nTRANSFORMER (Con Entrenamiento):")
                logger.info(f"  Sharpe Ratio: {after.get('sharpe_ratio', 0):.2f} ({improvement.get('sharpe_ratio', 0):+.2f}%)")
                logger.info(f"  Return %: {after.get('return_pct', 0):.2f}% ({improvement.get('return_pct', 0):+.2f}%)")
                logger.info(f"  Total PnL: ${after.get('total_pnl', 0):,.2f}")
                logger.info(f"  Win Rate: {after.get('win_rate', 0):.2f}% ({improvement.get('win_rate', 0):+.2f}%)")
                
                logger.info("\nMEJORA:")
                logger.info(f"  Sharpe: {improvement.get('sharpe_ratio', 0):.2f}%")
                logger.info(f"  Return: {improvement.get('return_pct', 0):.2f}%")
                logger.info(f"  Total PnL: ${after.get('total_pnl', 0) - before.get('total_pnl', 0):,.2f}")
                
            logger.info("=" * 80)
            logger.info("✅ Transformer Backtest completado!")
        else:
            logger.warning("⚠️ No se encontraron resultados de Transformer")
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando backtest: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

