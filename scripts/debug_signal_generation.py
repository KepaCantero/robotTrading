#!/usr/bin/env python3
"""
Script de debug para investigar generación de señales
"""

import sys
import logging
from pathlib import Path

# Agregar raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.strategies.momentum_modular.strategy import ModularMomentumStrategy
from app.backtesting.data_loader import DataLoader
from app.core.centralized_config import get_config
import yaml

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Debug signal generation."""
    logger.info("🔍 Iniciando debug de generación de señales...")
    
    # 1. Cargar configuración
    strategy_yaml_path = Path("config/strategies/momentum_modular.yaml")
    if strategy_yaml_path.exists():
        with open(strategy_yaml_path, 'r') as f:
            strategy_config = yaml.safe_load(f)
        # Mapear strategy_name a name
        if "strategy_name" in strategy_config and "name" not in strategy_config:
            strategy_config["name"] = strategy_config.pop("strategy_name")
        if "name" not in strategy_config:
            strategy_config["name"] = "momentum_modular"
    else:
        logger.error("No se encontró el archivo de configuración")
        return
    
    # 2. Verificar módulos en configuración
    logger.info("\n📋 Módulos en configuración:")
    modules_config = strategy_config.get("modules", {})
    for module_name, module_config in modules_config.items():
        enabled = module_config.get("enabled", True)
        logger.info(f"  - {module_name}: enabled={enabled}")
    
    # 3. Crear estrategia
    logger.info("\n🚀 Creando estrategia...")
    strategy = ModularMomentumStrategy(strategy_config)
    logger.info(f"  - Filtros activos: {len(strategy.filters)}")
    for filter_obj in strategy.filters:
        logger.info(f"    ✅ {filter_obj.name}")
    
    if len(strategy.filters) == 0:
        logger.error("❌ NO HAY FILTROS ACTIVOS! Esto explica por qué no se generan señales.")
        logger.info("\n🔍 Revisando configuración de módulos...")
        logger.info(f"  modules_config keys: {list(modules_config.keys())}")
        logger.info(f"  modules_config content: {modules_config}")
        return
    
    # 4. Cargar datos de mercado
    logger.info("\n📊 Cargando datos de mercado...")
    data_loader = DataLoader()
    quotes = data_loader.load_market_data(
        symbol="SNOW",
        start_date=None,  # Cargar desde archivo CSV
        end_date=None
    )
    logger.info(f"  - Quotes cargados: {len(quotes)}")
    
    if len(quotes) < 60:
        logger.warning(f"⚠️ Solo {len(quotes)} quotes disponibles. Se necesitan mínimo 60 para calcular indicadores.")
        return
    
    # 5. Probar generación de señales
    logger.info("\n🎯 Probando generación de señales...")
    signals_generated = 0
    signals_by_reason = {}
    
    # Probar con los últimos 100 quotes (después de tener suficiente histórico)
    for i, quote in enumerate(quotes):
        if i < 60:
            continue  # Saltar primeros 60 para tener histórico
        
        quote_signals = strategy.generate_signals(quote)
        if quote_signals:
            signals_generated += len(quote_signals)
            for signal in quote_signals:
                reason = signal.metadata.get('filter_results', {}).get('combination_result', 'unknown')
                signals_by_reason[reason] = signals_by_reason.get(reason, 0) + 1
        
        if i % 50 == 0 and i > 60:
            logger.info(f"  Procesados {i} quotes, señales generadas hasta ahora: {signals_generated}")
        
        if i >= 160:  # Limitar a 100 quotes de prueba
            break
    
    logger.info(f"\n📈 Resultados:")
    logger.info(f"  - Señales generadas: {signals_generated}")
    logger.info(f"  - Desglose por razón: {signals_by_reason}")
    
    # 6. Si no hay señales, investigar por qué
    if signals_generated == 0:
        logger.warning("\n⚠️ NO SE GENERARON SEÑALES")
        logger.info("🔍 Investigando causas...")
        
        # Probar con un quote específico
        test_quote = quotes[100] if len(quotes) > 100 else quotes[-1]
        logger.info(f"\n  Probando con quote del {test_quote.timestamp}:")
        
        # Verificar histórico
        logger.info(f"    - Price history length: {len(strategy.price_history)}")
        logger.info(f"    - Volume history length: {len(strategy.volume_history)}")
        
        if len(strategy.price_history) >= 60:
            # Calcular indicadores manualmente
            indicators = strategy._calculate_indicators()
            logger.info(f"    - Indicadores calculados: {list(indicators.keys())}")
            logger.info(f"    - RSI: {indicators.get('rsi')}")
            logger.info(f"    - EMA Fast: {indicators.get('ema_fast')}")
            logger.info(f"    - EMA Slow: {indicators.get('ema_slow')}")
            logger.info(f"    - Momentum: {indicators.get('momentum_roc')}")
            logger.info(f"    - Volume Ratio: {indicators.get('volume_ratio')}")
            
            # Analizar contexto
            price_list = list(strategy.price_history)
            atr_list = list(strategy.atr_history) if strategy.atr_history else []
            market_context = strategy.market_analyzer.analyze(test_quote, price_list, atr_list)
            logger.info(f"    - Market Context: {market_context}")
            
            # Evaluar filtros
            filter_results = strategy._evaluate_filters(indicators, market_context)
            logger.info(f"\n    - Resultados de filtros:")
            for filter_name, result in filter_results.items():
                passed = result.get('passed', False)
                confidence = result.get('confidence', 0.0)
                reason = result.get('reason', 'unknown')
                logger.info(f"      {filter_name}: passed={passed}, confidence={confidence:.2f}, reason={reason[:50]}")
            
            # Determinar tipo de señal
            signal_type = strategy._determine_signal_type(filter_results, market_context)
            logger.info(f"\n    - Signal Type determinado: {signal_type}")
            
            if signal_type is None:
                logger.warning("    ❌ No se determinó tipo de señal")
                logger.info("    🔍 Revisando lógica de determinación...")
                
                # Verificar combinación de filtros
                combination_mode = strategy.current_preset.get("combination_mode", "MAJORITY")
                logger.info(f"    - Combination mode: {combination_mode}")
                
                # Contar filtros que pasaron
                passed_filters = [name for name, result in filter_results.items() if result.get('passed', False)]
                logger.info(f"    - Filtros que pasaron: {len(passed_filters)}/{len(filter_results)}")
                logger.info(f"    - Nombres: {passed_filters}")
        else:
            logger.warning(f"    ⚠️ No hay suficiente histórico: {len(strategy.price_history)} < 60")
    
    logger.info("\n✅ Debug completado")


if __name__ == "__main__":
    main()

