#!/usr/bin/env python3
"""
Script principal para ejecutar backtesting comprehensivo

Uso:
    # Ejecutar todos los backtests habilitados en la configuración
    python scripts/run_comprehensive_backtest.py

    # Ejecutar backtests específicos
    python scripts/run_comprehensive_backtest.py baseline ablation grid_search

Backtests disponibles:
    - baseline: Línea base con todos los módulos activos
    - learning_engines: Prueba cada learning engine individualmente (supervised, deep, reinforcement)
    - walk_forward: Optimización por ventana temporal
    - monte_carlo: Stress test con simulaciones aleatorias
    - transformer_optimization: Optimización iterativa con Transformer
    - ablation: Impacto individual de cada módulo
    - grid_search: Búsqueda de parámetros óptimos
    - out_of_sample: Validación forward
    - regime_test: Desempeño por régimen de mercado
"""

import sys
import os

# ============================================================================
# SOLUCIÓN DEFINITIVA: Configurar variables de entorno ANTES de cualquier import
# Esto previene bloqueos de threading con mutex.cc
# Debe ir ANTES de importar numpy, pandas, torch, o cualquier otra librería
# ============================================================================
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Deshabilitar CUDA para evitar bloqueos
os.environ['TORCH_USE_CUDA_DSA'] = '0'

import argparse
import logging
from pathlib import Path

# Configurar logging PRIMERO, antes de cualquier import que pueda bloquearse
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Forzar reconfiguración si ya estaba configurado
)

logger = logging.getLogger(__name__)
logger.info("🚀 Script iniciado - Configurando logging...")

# Agregar raíz del proyecto al path
# scripts/backtesting/ -> scripts/ -> project_root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger.info("📦 Intentando importar ComprehensiveBacktestRunner...")
print("📦 Importando módulos (esto puede tardar 10-30 segundos)...", flush=True)

try:
    from app.backtesting.comprehensive_backtest_runner import ComprehensiveBacktestRunner
    logger.info("✅ ComprehensiveBacktestRunner importado correctamente")
    print("✅ Módulos importados correctamente", flush=True)
except (ValueError, TypeError, KeyError, AttributeError) as e:
    logger.error(f"❌ Error importando ComprehensiveBacktestRunner: {e}", exc_info=True)
    print(f"❌ Error en import: {e}", flush=True)
    raise


def main():
    """Ejecutar pipeline completo de backtesting."""
    parser = argparse.ArgumentParser(
        description='Ejecutar backtesting comprehensivo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Ejecutar todos los backtests habilitados
  python scripts/run_comprehensive_backtest.py

  # Ejecutar solo baseline
  python scripts/run_comprehensive_backtest.py baseline

  # Ejecutar múltiples backtests
  python scripts/run_comprehensive_backtest.py baseline learning_engines ablation grid_search
        """
    )
    
    parser.add_argument(
        'backtests',
        nargs='*',
        default=None,
        help='Nombres de backtests específicos a ejecutar. Si no se especifica, ejecuta todos los habilitados en la configuración.'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Ruta al archivo de configuración YAML (default: config/backtesting/comprehensive_backtest.yaml)'
    )
    
    args = parser.parse_args()
    
    # Ruta a la configuración
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = project_root / "config" / "backtesting" / "comprehensive_backtest.yaml"
    
    if not config_path.exists():
        logger.error(f"❌ Archivo de configuración no encontrado: {config_path}")
        logger.info("💡 Crea el archivo de configuración en config/backtesting/comprehensive_backtest.yaml")
        return
    
    logger.info("🚀 Iniciando Comprehensive Backtest Runner...")
    logger.info(f"📋 Configuración: {config_path}")
    
    try:
        # Crear runner
        runner = ComprehensiveBacktestRunner(str(config_path))
        
        # Ejecutar backtests
        if args.backtests:
            # Ejecutar backtests específicos
            logger.info(f"📊 Ejecutando backtests específicos: {args.backtests}")
            results = runner.run_specific_backtests(args.backtests)
            # Convertir a DataFrame para mostrar
            if results:
                import pandas as pd
                results_df = pd.DataFrame(results)
            else:
                results_df = pd.DataFrame()
        else:
            # Ejecutar todos los backtests habilitados
            logger.info("📊 Ejecutando todos los backtests habilitados...")
            results = runner.run_all_backtests()
            # Convertir a DataFrame para mostrar
            if results:
                import pandas as pd
                results_df = pd.DataFrame(results)
            else:
                results_df = pd.DataFrame()
        
        # Mostrar resumen
        print("\n" + "=" * 80)
        print("RESUMEN DE RESULTADOS")
        print("=" * 80)
        if not results_df.empty:
            print(f"\nTotal de backtests ejecutados: {len(results_df)}")
            print(f"\nTop 5 por Sharpe Ratio:")
            print("-" * 80)
            top_5 = results_df.head(5)
            # VECTORIZED: Usar to_dict('records') en lugar de iterrows
            for row in top_5.to_dict('records'):
                print(f"\n{row.get('test_name', 'Unknown')}:")
                print(f"  Sharpe Ratio: {row.get('sharpe_ratio', 0):.2f}")
                print(f"  Total PnL: ${row.get('total_pnl', 0):,.2f}")
                print(f"  Return %: {row.get('return_pct', 0):.2f}%")
                print(f"  Win Rate: {row.get('win_rate', 0):.2f}%")
                print(f"  Max Drawdown: {row.get('max_drawdown', 0):.2f}%")
        else:
            print("⚠️ No se ejecutaron backtests. Verifica la configuración.")
        
        print("\n" + "=" * 80)
        logger.info("✅ Pipeline completado exitosamente!")
        
    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"❌ Error ejecutando backtests: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

