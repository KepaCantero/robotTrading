#!/usr/bin/env python3
"""
Script para ejecutar SOLO el backtest de Deep Learning con Simple Strategy

Uso:
    python scripts/run_deep_learning_backtest.py
"""

import sys
import os
import logging
from pathlib import Path

# ============================================================================
# SOLUCIÓN DEFINITIVA: Configurar variables de entorno ANTES de cualquier import
# Esto previene bloqueos de threading con mutex.cc
# Debe ir ANTES de importar numpy, pandas, torch, o cualquier otra librería
# ============================================================================
# Variables de threading (CRÍTICAS - deben ir primero)
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['NUMEXPR_MAX_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'

# Variables MKL específicas (importantes para evitar bloqueos)
os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['MKL_DYNAMIC'] = 'FALSE'  # Forzar estático
os.environ['MKL_INTERFACE_LAYER'] = 'LP64,GNU'

# Variables PyTorch/CUDA
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Deshabilitar CUDA completamente
os.environ['TORCH_USE_CUDA_DSA'] = '0'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'  # macOS Metal fallback

# Variables TensorFlow (si está instalado)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Variables adicionales de sistema
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'  # Windows

# Forzar modo single-threaded en nivel de sistema
import threading
threading.settrace(None)  # Deshabilitar tracing de threads

# Agregar raíz del proyecto al path PRIMERO
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Configurar logging usando la configuración del proyecto
# Esto asegura que warnings.log y errors.log se llenen correctamente
try:
    from app.core.logging_config import setup_file_logging, setup_module_loggers
    # Configurar logging con handlers para warnings.log y errors.log
    setup_file_logging(
        log_dir="logs",
        root_level=logging.INFO,
        file_level=logging.WARNING,
        console_level=logging.INFO,
    )
    setup_module_loggers()
except Exception as e:
    # Fallback a basicConfig si no se puede importar
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )
    logging.warning(f"No se pudo configurar logging avanzado: {e}")

logger = logging.getLogger(__name__)
logger.info("🚀 Iniciando Backtest Comparativo: Baseline + 4 Learning Engines...")

try:
    from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
    logger.info("✅ ComprehensiveBacktestRunner importado")
except Exception as e:
    logger.error(f"❌ Error importando ComprehensiveBacktestRunner: {e}", exc_info=True)
    raise

def main():
    """Ejecutar backtest de Baseline + todos los Learning Engines y mostrar comparativa."""
    config_path = project_root / "config" / "backtesting" / "comprehensive_backtest.yaml"
    
    if not config_path.exists():
        logger.error(f"❌ Archivo de configuración no encontrado: {config_path}")
        return
    
    logger.info(f"📋 Configuración: {config_path}")
    
    try:
        # Crear runner
        runner = ComprehensiveBacktestRunner(str(config_path))
        
        all_results = []
        
        # ===== OPCIÓN RÁPIDA: Saltar Baseline, solo Deep Learning =====
        # Para ejecutar más rápido, comenta esta sección y descomenta la sección 1 arriba
        SKIP_BASELINE = True  # Cambiar a False si quieres incluir Baseline
        
        if not SKIP_BASELINE:
            # ===== 1. EJECUTAR BASELINE =====
            logger.info("=" * 80)
            logger.info("📊 Ejecutando Baseline Backtest...")
            logger.info("=" * 80)
            try:
                baseline_result = runner.run_baseline_backtest()
                if baseline_result:
                    baseline_result['test_name'] = 'Baseline'
                    baseline_result['learning_engine'] = None
                    all_results.append(baseline_result)
                    logger.info("✅ Baseline completado")
            except Exception as e:
                logger.error(f"❌ Error en Baseline: {e}")
        
        # ===== 2. EJECUTAR DEEP LEARNING SOLO =====
        logger.info("=" * 80)
        logger.info("📊 Ejecutando Deep Learning Backtest (sin Baseline)...")
        logger.info("=" * 80)
        
        # Guardar configuración original
        original_config = runner.config.get('learning_engines', {}).copy()
        
        # Lista de engines a probar - SOLO DEEP
        engines_to_test = ['deep']
        
        for engine_name in engines_to_test:
            logger.info(f"\n{'─' * 80}")
            logger.info(f"🔬 Ejecutando {engine_name.upper()} Learning Engine...")
            logger.info(f"{'─' * 80}")
            
            # Asegurar que el engine existe en la configuración
            if 'learning_engines' not in runner.config:
                runner.config['learning_engines'] = {}
            
            if engine_name not in runner.config['learning_engines']:
                # Crear configuración mínima para el engine si no existe
                logger.info(f"📝 Creando configuración para {engine_name}...")
                runner.config['learning_engines'][engine_name] = {
                    'enabled': True,
                    'parameters': {}
                }
            
            # Deshabilitar todos excepto el actual
            for other_engine in engines_to_test:
                if other_engine in runner.config.get('learning_engines', {}):
                    runner.config['learning_engines'][other_engine]['enabled'] = (other_engine == engine_name)
            
            # Asegurar que el engine actual esté habilitado
            runner.config['learning_engines'][engine_name]['enabled'] = True
            
            logger.info(f"✅ {engine_name} habilitado (otros deshabilitados temporalmente)")
            
            try:
                # Ejecutar learning engine
                results = runner.run_learning_engines_backtest()
                
                # Filtrar resultados de este engine
                engine_results = [r for r in results if r.get('learning_engine') == engine_name]
                
                if engine_results:
                    result = engine_results[0]
                    result['test_name'] = f"{engine_name.capitalize()} Learning"
                    
                    # Verificar si el entrenamiento fue exitoso
                    if 'after_training_metrics' in result:
                        after = result['after_training_metrics']
                        before = result.get('before_training_metrics', {})
                        
                        # Si las métricas son idénticas, el entrenamiento probablemente falló
                        if (after.get('total_pnl') == before.get('total_pnl') and 
                            after.get('sharpe_ratio') == before.get('sharpe_ratio')):
                            logger.warning(f"⚠️ {engine_name}: Métricas idénticas a baseline - posible fallo en entrenamiento")
                            result['training_status'] = 'failed'
                        else:
                            result['training_status'] = 'success'
                    
                    all_results.append(result)
                    logger.info(f"✅ {engine_name.capitalize()} completado")
                else:
                    logger.warning(f"⚠️ No se encontraron resultados para {engine_name} - puede no haberse ejecutado")
            except Exception as e:
                logger.error(f"❌ Error ejecutando {engine_name}: {e}", exc_info=True)
        
        # Restaurar configuración original
        runner.config['learning_engines'] = original_config
        
        # ===== 3. MOSTRAR COMPARATIVA FINAL =====
        if all_results:
            print("\n" + "=" * 100)
            print("📊 COMPARATIVA DE ESTRATEGIAS")
            print("=" * 100)
            
            # Preparar datos para tabla
            comparison_data = []
            for result in all_results:
                test_name = result.get('test_name', 'Unknown')
                # Extraer métricas después del entrenamiento si existen
                if 'after_training_metrics' in result:
                    metrics = result['after_training_metrics']
                    improvement = result.get('improvement_pct', {})
                else:
                    metrics = result
                    improvement = {}
                
                # Indicador de estado de entrenamiento
                training_status = result.get('training_status', 'unknown')
                status_icon = "✅" if training_status == 'success' else "⚠️" if training_status == 'failed' else "❓"
                
                comparison_data.append({
                    'Estrategia': f"{status_icon} {test_name}",
                    'PnL ($)': f"${metrics.get('total_pnl', 0):,.2f}",
                    'Return (%)': f"{metrics.get('return_pct', 0):.2f}%",
                    'Sharpe': f"{metrics.get('sharpe_ratio', 0):.2f}",
                    'Sortino': f"{metrics.get('sortino_ratio', 0):.2f}",
                    'Max DD (%)': f"{metrics.get('max_drawdown', 0):.2f}%",
                    'Win Rate (%)': f"{metrics.get('win_rate', 0):.2f}%",
                    'Trades': metrics.get('total_trades', 0),
                    'Profit Factor': f"{metrics.get('profit_factor', 0):.2f}",
                    'Mejora Sharpe': f"{improvement.get('sharpe_ratio', 0):+.2f}%" if improvement else "N/A"
                })
            
            # Mostrar tabla formateada
            print(f"\n{'Estrategia':<20} {'PnL ($)':>12} {'Return (%)':>10} {'Sharpe':>8} {'Sortino':>8} {'Max DD (%)':>10} {'Win Rate (%)':>12} {'Trades':>8} {'P.Factor':>9} {'Mejora':>9}")
            print("-" * 100)
            
            for data in comparison_data:
                print(f"{data['Estrategia']:<20} {data['PnL ($)']:>12} {data['Return (%)']:>10} "
                      f"{data['Sharpe']:>8} {data['Sortino']:>8} {data['Max DD (%)']:>10} "
                      f"{data['Win Rate (%)']:>12} {data['Trades']:>8} {data['Profit Factor']:>9} "
                      f"{data['Mejora Sharpe']:>9}")
            
            # Rankings
            print("\n" + "=" * 100)
            print("🏆 RANKINGS")
            print("=" * 100)
            
            # Mejor Sharpe Ratio
            best_sharpe = max(all_results, key=lambda x: x.get('after_training_metrics', x).get('sharpe_ratio', -999) if 'after_training_metrics' in x else x.get('sharpe_ratio', -999))
            print(f"\n🥇 Mejor Sharpe Ratio: {best_sharpe.get('test_name', 'Unknown')} "
                  f"({best_sharpe.get('after_training_metrics', best_sharpe).get('sharpe_ratio', 0):.2f})")
            
            # Mejor Return
            best_return = max(all_results, key=lambda x: x.get('after_training_metrics', x).get('return_pct', -999) if 'after_training_metrics' in x else x.get('return_pct', -999))
            print(f"💰 Mejor Return: {best_return.get('test_name', 'Unknown')} "
                  f"({best_return.get('after_training_metrics', best_return).get('return_pct', 0):.2f}%)")
            
            # Mejor Profit Factor
            best_pf = max(all_results, key=lambda x: x.get('after_training_metrics', x).get('profit_factor', 0) if 'after_training_metrics' in x else x.get('profit_factor', 0))
            print(f"📈 Mejor Profit Factor: {best_pf.get('test_name', 'Unknown')} "
                  f"({best_pf.get('after_training_metrics', best_pf).get('profit_factor', 0):.2f})")
            
            # Menor Drawdown
            best_dd = min(all_results, key=lambda x: x.get('after_training_metrics', x).get('max_drawdown', 999) if 'after_training_metrics' in x else x.get('max_drawdown', 999))
            print(f"🛡️  Menor Drawdown: {best_dd.get('test_name', 'Unknown')} "
                  f"({best_dd.get('after_training_metrics', best_dd).get('max_drawdown', 0):.2f}%)")
            
            # Mejor Win Rate
            best_wr = max(all_results, key=lambda x: x.get('after_training_metrics', x).get('win_rate', 0) if 'after_training_metrics' in x else x.get('win_rate', 0))
            print(f"🎯 Mejor Win Rate: {best_wr.get('test_name', 'Unknown')} "
                  f"({best_wr.get('after_training_metrics', best_wr).get('win_rate', 0):.2f}%)")
            
            # Comparativa vs Baseline (solo si Baseline fue ejecutado)
            baseline_result = next((r for r in all_results if r.get('test_name') == 'Baseline'), None)
            if baseline_result:
                baseline_metrics = baseline_result
                print("\n" + "=" * 100)
                print("📊 MEJORA vs BASELINE")
                print("=" * 100)
                
                for result in all_results:
                    if result.get('test_name') == 'Baseline':
                        continue
                    
                    if 'after_training_metrics' in result:
                        metrics = result['after_training_metrics']
                        test_name = result.get('test_name', 'Unknown')
                        
                        sharpe_diff = metrics.get('sharpe_ratio', 0) - baseline_metrics.get('sharpe_ratio', 0)
                        return_diff = metrics.get('return_pct', 0) - baseline_metrics.get('return_pct', 0)
                        pnl_diff = metrics.get('total_pnl', 0) - baseline_metrics.get('total_pnl', 0)
                        
                        sharpe_arrow = "⬆️" if sharpe_diff > 0 else "⬇️" if sharpe_diff < 0 else "➡️"
                        return_arrow = "⬆️" if return_diff > 0 else "⬇️" if return_diff < 0 else "➡️"
                        pnl_arrow = "⬆️" if pnl_diff > 0 else "⬇️" if pnl_diff < 0 else "➡️"
                        
                        print(f"\n{test_name}:")
                        print(f"  Sharpe: {baseline_metrics.get('sharpe_ratio', 0):.2f} → {metrics.get('sharpe_ratio', 0):.2f} "
                              f"({sharpe_diff:+.2f}) {sharpe_arrow}")
                        print(f"  Return: {baseline_metrics.get('return_pct', 0):.2f}% → {metrics.get('return_pct', 0):.2f}% "
                              f"({return_diff:+.2f}%) {return_arrow}")
                        print(f"  PnL: ${baseline_metrics.get('total_pnl', 0):,.2f} → ${metrics.get('total_pnl', 0):,.2f} "
                              f"({pnl_diff:+,.2f}) {pnl_arrow}")
            else:
                print("\n" + "=" * 100)
                print("ℹ️  Baseline no ejecutado (SKIP_BASELINE=True) - Solo resultados de Deep Learning")
                print("=" * 100)
            
            print("\n" + "=" * 100)
            logger.info("✅ Comparativa de estrategias completada!")
        else:
            logger.warning("⚠️ No se encontraron resultados para comparar")
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando backtests: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

