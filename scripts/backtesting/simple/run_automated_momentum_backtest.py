#!/usr/bin/env python3
"""
Script ejecutable para backtest automatizado de estrategia Momentum Modular.
"""

import sys
from pathlib import Path

# Agregar raíz del proyecto al path
# scripts/backtesting/simple/ -> scripts/backtesting/ -> scripts/ -> project_root
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
from decimal import Decimal
from app.domain.strategies.momentum_modular.automated_backtest import run_automated_backtest

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('logs/automated_backtest.log'), logging.StreamHandler()],
)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("BACKTEST AUTOMATIZADO - ESTRATEGIA MOMENTUM MODULAR")
    logger.info("=" * 80)

    try:
        # Ejecutar backtest automatizado
        results = run_automated_backtest(
            symbol=None,  # Auto-seleccionar mejor stock
            criteria="momentum_signal",  # Criterio de selección
            initial_capital=Decimal("100000"),
        )

        logger.info("\n✅ Backtest automatizado completado exitosamente!")
        logger.info(f"Stock analizado: {results['symbol']}")
        logger.info(f"\nResultados guardados en: docs/BACKTEST_RESULTS/")

        # Mostrar resumen
        if 'summary' in results and len(results['summary']) > 0:
            summary = results['summary']
            logger.info(f"\n📊 Total de configuraciones probadas: {len(summary)}")

            if len(summary) > 0:
                best = summary.iloc[0]
                logger.info(f"\n🏆 MEJOR CONFIGURACIÓN:")
                logger.info(f"   Nombre: {best['name']}")
                logger.info(f"   Sharpe Ratio: {best['sharpe_ratio']:.3f}")
                logger.info(f"   Return: {best['return_pct']:.2f}%")
                logger.info(f"   Win Rate: {best['win_rate']:.2f}%")

    except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
        logger.error(f"❌ Error ejecutando backtest: {e}", exc_info=True)
        sys.exit(1)
