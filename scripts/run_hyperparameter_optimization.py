#!/usr/bin/env python3
"""
Script de optimización automatizada de hiperparámetros.
Ejecuta múltiples backtests variando parámetros para encontrar la configuración óptima.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Agregar raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.strategies.momentum_modular.optimization.hyperparameter_optimizer import HyperparameterOptimizer

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/hyperparameter_optimization.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Ejecutar optimización de hiperparámetros."""
    
    # Configuración
    symbol = "AAPL"  # Stock a optimizar
    year = 2023  # Año de datos
    
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    initial_capital = Decimal("100000")
    
    # Métricas de optimización disponibles:
    # - "sharpe_ratio": Optimizar Sharpe Ratio
    # - "total_pnl": Optimizar PnL total
    # - "win_rate": Optimizar Win Rate
    # - "combined": Score combinado
    optimization_metric = "sharpe_ratio"
    
    # Métodos de optimización:
    # - "grid_search": Búsqueda en grilla
    # - "random_search": Búsqueda aleatoria (recomendado para muchas iteraciones)
    optimization_method = "random_search"
    
    # Número de iteraciones/configuraciones a probar
    max_iterations = 1000
    
    logger.info("=" * 80)
    logger.info("🚀 OPTIMIZACIÓN AUTOMATIZADA DE HIPERPARÁMETROS")
    logger.info("=" * 80)
    logger.info(f"Símbolo: {symbol}")
    logger.info(f"Año: {year}")
    logger.info(f"Período: {start_date.date()} - {end_date.date()}")
    logger.info(f"Métrica objetivo: {optimization_metric}")
    logger.info(f"Método: {optimization_method}")
    logger.info(f"Iteraciones: {max_iterations}")
    logger.info("=" * 80)
    
    # Crear optimizador
    optimizer = HyperparameterOptimizer(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        optimization_metric=optimization_metric,
        optimization_method=optimization_method
    )
    
    # Ejecutar optimización
    results = optimizer.optimize(
        max_iterations=max_iterations,
        random_seed=42  # Para reproducibilidad
    )
    
    # Mostrar resultados
    logger.info("\n" + "=" * 80)
    logger.info("📊 RESULTADOS DE OPTIMIZACIÓN")
    logger.info("=" * 80)
    logger.info(f"Mejor Score: {results['best_score']:.4f}")
    logger.info(f"Total Iteraciones: {results['total_iterations']}")
    logger.info("\nMejor Configuración:")
    
    for key, value in results['best_config'].items():
        logger.info(f"  {key}: {value}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ Optimización completada")
    logger.info(f"Resultados guardados en: docs/OPTIMIZATION_RESULTS/")
    logger.info("=" * 80)
    
    return results


if __name__ == "__main__":
    try:
        results = main()
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Optimización interrumpida por el usuario")
        sys.exit(1)
    except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
        logger.error(f"❌ Error en optimización: {e}", exc_info=True)
        sys.exit(1)

