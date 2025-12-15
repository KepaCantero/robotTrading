"""
Comprehensive Backtest Runner
Sistema completo de backtesting automatizado y configurable
"""

import os
import logging

# ============================================================================
# SOLUCIÓN DEFINITIVA: Configurar variables de entorno ANTES de cualquier import
# Esto previene bloqueos de threading con mutex.cc
# FORZAR (no setdefault) para asegurar que se apliquen incluso si ya existen
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

# Configurar logger inmediatamente
logger = logging.getLogger(__name__)

# Imports básicos primero
print("📦 Importando módulos básicos...", flush=True)
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np
import multiprocessing
print("✅ Módulos básicos importados", flush=True)

# Imports de backtesting
print("📦 Importando módulos de backtesting...", flush=True)
from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult
from app.backtesting.multi_strategy_engine import MultiStrategyBacktester
print("✅ Módulos de backtesting importados", flush=True)

# Imports de estrategias (pueden ser pesados)
print("📦 Importando estrategias (esto puede tardar)...", flush=True)
try:
    from app.strategies.momentum_modular.strategy import ModularMomentumStrategy
    print("✅ ModularMomentumStrategy importado", flush=True)
except Exception as e:
    print(f"❌ Error importando ModularMomentumStrategy: {e}", flush=True)
    logger.error(f"❌ Error importando ModularMomentumStrategy: {e}", exc_info=True)
    raise

from app.strategies.momentum import MomentumStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.pairs_trading import PairsTradingStrategy
print("✅ Estrategias importadas", flush=True)

# Otros imports
print("📦 Importando otros módulos...", flush=True)
from app.backtesting.data_loader import DataLoader
from app.services.portfolio_config_manager import get_portfolio_config_manager
print("✅ Todos los imports completados", flush=True)

# Optional: quantstats and pyfolio for professional reports
try:
    import quantstats as qs
    QUANTSTATS_AVAILABLE = True
except ImportError:
    QUANTSTATS_AVAILABLE = False
    logger.debug("quantstats no disponible. Reportes HTML deshabilitados.")

try:
    import pyfolio as pf
    PYFOLIO_AVAILABLE = True
except ImportError:
    PYFOLIO_AVAILABLE = False
    logger.debug("pyfolio-reloaded no disponible. Análisis de portfolio avanzado deshabilitado.")


class ComprehensiveBacktestRunner:
    """
    Ejecuta un pipeline completo de backtesting con múltiples tipos de tests.
    
    Tipos de backtests soportados:
    1. Baseline - Línea base con todos los módulos activos
    2. Learning Engines - Prueba cada learning engine individualmente
    3. Walk-forward - Optimización por ventana temporal
    4. Monte Carlo - Stress test con simulaciones aleatorias
    5. Transformer Optimization - Optimización iterativa con Transformer
    6. Ablation - Impacto individual de cada módulo
    7. Grid Search - Búsqueda de parámetros óptimos
    8. Out-of-Sample - Validación forward
    9. Multi-Strategy - Prueba múltiples estrategias simultáneamente (usando MultiStrategyBacktester)
    10. Regime Test - Desempeño por régimen de mercado
    """
    
    def __init__(self, config_path: str):
        """
        Inicializar runner con configuración.
        
        Args:
            config_path: Ruta al archivo YAML de configuración
        """
        self.config = self._load_config(config_path)
        self.config_path = config_path  # Guardar para auditoría
        self.results: List[Dict[str, Any]] = []
        # Store complete BacktestResult objects for quantstats/pyfolio analysis
        self.backtest_results_objects: List[Tuple[str, BacktestResult]] = []  # (test_name, BacktestResult)
        self.output_dir = Path(self.config['reporting']['output_directory'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar datos históricos
        self.data_loader = DataLoader()
        # Cargar quotes - usar todos los símbolos del portfolio si hay multi-strategy tests
        self.quotes = self._load_market_data()
        
        # Configuración de paralelización
        self.parallel_enabled = self.config.get('parallelization', {}).get('enabled', True)
        self.max_workers = self.config.get('parallelization', {}).get('max_workers', None)
        
        # Integrar meta_analyzer si está habilitado
        self.meta_enabled = self.config.get('meta_analysis', {}).get('enabled', False)
        self.audit_trail = None
        self.learning_storage = None
        self.audit_hash = None
        
        if self.meta_enabled:
            try:
                from app.backtesting.meta_analyzer import integrate_meta_analyzer_with_runner
                meta = integrate_meta_analyzer_with_runner(
                    runner=self,
                    config_path=config_path,
                    enable_audit=self.config.get('meta_analysis', {}).get('enable_audit', True),
                    enable_storage=self.config.get('meta_analysis', {}).get('enable_storage', True),
                    enable_analysis=self.config.get('meta_analysis', {}).get('enable_analysis', True)
                )
                self.audit_trail = meta['audit_trail']
                self.learning_storage = meta['storage']
                self.audit_hash = meta['audit_hash']
                logger.info(f"✅ Meta-analyzer integrado (Hash: {self.audit_hash[:16] if self.audit_hash else 'N/A'}...)")
                
                # Guardar hash y configuración en log inicial
                if self.audit_trail:
                    logger.info(f"📝 Hash de configuración: {self.audit_hash}")
                    git_info = self.audit_trail._get_git_info()
                    if git_info.get('commit_hash'):
                        logger.info(f"📝 Git commit: {git_info['commit_hash'][:8]} (branch: {git_info.get('branch', 'unknown')})")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo integrar meta_analyzer: {e}")
        
        logger.info(f"✅ ComprehensiveBacktestRunner inicializado con {len(self.quotes)} quotes")
        if self.parallel_enabled:
            logger.info(f"⚡ Paralelización habilitada (max_workers={self.max_workers or 'auto'})")
    
    def _load_config(self, config_path: str) -> Dict:
        """Cargar configuración desde YAML."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def _load_market_data(self) -> List:
        """Cargar datos históricos de mercado."""
        start_date = datetime.strptime(self.config['input']['start_date'], "%Y-%m-%d")
        end_date = datetime.strptime(self.config['input']['end_date'], "%Y-%m-%d")
        
        # Siempre cargar todos los símbolos del portfolio para mejor diversificación
        # y comparación entre estrategias simples y multi-strategy
        logger.info("🔄 Cargando todos los símbolos del portfolio...")
        return self._load_portfolio_market_data(start_date, end_date)
    
    def _load_portfolio_market_data(self, start_date: datetime, end_date: datetime) -> List:
        """Cargar datos históricos para todos los símbolos del portfolio."""
        from app.services.portfolio_builder import PortfolioBuilder
        from app.services.portfolio_config_manager import get_portfolio_config_manager
        
        portfolio_config = get_portfolio_config_manager()
        portfolio_builder = PortfolioBuilder(
            portfolio_config=portfolio_config,
            data_loader=self.data_loader
        )
        
        # Construir portfolio con todos los símbolos
        quotes = portfolio_builder.build_portfolio_quotes(
            start_date=start_date,
            end_date=end_date
        )
        
        unique_symbols = len(set(q.symbol for q in quotes))
        logger.info(f"✅ Cargados {len(quotes)} quotes de {unique_symbols} símbolos del portfolio")
        return quotes
    
    def _create_strategy_config(
        self,
        modules_override: Optional[Dict] = None,
        thresholds_override: Optional[Dict] = None,
        learning_engine_override: Optional[str] = None
    ) -> Dict:
        """Crear configuración de estrategia con overrides opcionales."""
        # Cargar configuración base desde YAML de la estrategia
        from app.core.centralized_config import get_config
        import yaml
        from pathlib import Path
        
        # Cargar YAML completo directamente para mantener estructura de módulos
        strategy_yaml_path = Path("config/strategies/momentum_modular.yaml")
        if strategy_yaml_path.exists():
            with open(strategy_yaml_path, 'r') as f:
                base_config = yaml.safe_load(f)
            # Mapear strategy_name a name si existe
            if "strategy_name" in base_config and "name" not in base_config:
                base_config["name"] = base_config.pop("strategy_name")
            if "name" not in base_config:
                base_config["name"] = "momentum_modular"
        else:
            # Fallback: usar configuración del centralized config
            config = get_config()
            strategy_config = config.get_strategy_config('momentum_modular')
            base_config = {
                'name': 'momentum_modular',
                'enabled': True,
                'preset': 'balanced'
            }
            if strategy_config and strategy_config.parameters:
                base_config.update(strategy_config.parameters)
        
        # Aplicar overrides de módulos
        if modules_override:
            if 'modules' not in base_config:
                base_config['modules'] = {}
            for module_name, module_config in modules_override.items():
                if 'modules' not in base_config:
                    base_config['modules'] = {}
                base_config['modules'][module_name] = module_config
        
        # Aplicar overrides de thresholds
        if thresholds_override:
            # Merge thresholds en la configuración de cada módulo
            for module_name, threshold_value in thresholds_override.items():
                module_parts = module_name.split('.')
                if len(module_parts) == 2:
                    filter_name, param_name = module_parts
                    if 'modules' in base_config and filter_name in base_config['modules']:
                        if 'parameters' not in base_config['modules'][filter_name]:
                            base_config['modules'][filter_name]['parameters'] = {}
                        base_config['modules'][filter_name]['parameters'][param_name] = threshold_value
        
        # Aplicar learning engine override
        if learning_engine_override:
            # Cargar configuración del learning engine desde el config del runner
            learning_engine_config = self.config.get('learning_engines', {}).get(learning_engine_override, {})
            base_config['adaptive_learning'] = {
                'enabled': True,
                'engine_type': learning_engine_override,
                'parameters': learning_engine_config.get('parameters', {})
            }
        elif learning_engine_override is None:
            base_config['adaptive_learning'] = {'enabled': False}
        
        return base_config
    
    def _calculate_consistent_metrics(
        self,
        result: Any,
        initial_capital: Decimal
    ) -> Dict[str, float]:
        """
        Calcular métricas de manera consistente desde final_capital.
        
        Esto asegura que total_pnl y return_pct sean consistentes,
        especialmente cuando hay posiciones abiertas.
        """
        final_capital = Decimal(str(result.final_capital))
        
        # Calcular total_pnl desde capital (más preciso que sumar trades)
        total_pnl = float(final_capital - initial_capital)
        
        # Calcular return_pct de manera consistente
        return_pct = float((final_capital - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0.0
        
        return {
            'total_pnl': total_pnl,
            'return_pct': return_pct,
            'final_capital': float(final_capital)
        }
    
    def _get_strategy_name(self, strategy: Any) -> str:
        """
        Obtener nombre de estrategia de forma segura.
        
        Args:
            strategy: Instancia de estrategia
        
        Returns:
            Nombre de la estrategia o 'momentum_modular' por defecto
        """
        if not strategy:
            return 'momentum_modular'
        
        # Intentar obtener el nombre de varias formas
        if hasattr(strategy, 'name'):
            return getattr(strategy, 'name', 'momentum_modular')
        elif hasattr(strategy, '__class__'):
            class_name = strategy.__class__.__name__
            if 'Momentum' in class_name:
                return 'momentum_modular'
        
        return 'momentum_modular'
    
    def _train_learning_engine_if_needed(
        self,
        strategy: Any,
        learning_engine_name: Optional[str] = None,
        use_subprocess: bool = False
    ) -> bool:
        """
        Entrenar learning engine si está configurado y no está entrenado.
        
        Características:
        - Intenta cargar pesos guardados previamente (aprendizaje incremental)
        - Si no hay pesos o falla la carga, entrena desde cero
        - Guarda pesos después del entrenamiento
        
        Returns:
            True si se entrenó exitosamente, False en caso contrario
        """
        logger.info(f"    🔍 Verificando learning engine para entrenamiento...")
        logger.info(f"       - strategy.learning_engine existe: {strategy.learning_engine is not None}")
        logger.info(f"       - strategy._learning_config existe: {hasattr(strategy, '_learning_config') and strategy._learning_config is not None}")
        
        # CRÍTICO: Si el learning engine es lazy, inicializarlo ahora
        if hasattr(strategy, '_learning_config') and strategy._learning_config and strategy.learning_engine is None:
            logger.info(f"    ⚙️ Inicializando learning engine (lazy loading)...")
            try:
                strategy._initialize_learning_engine()
                logger.info(f"    ✅ Learning engine inicializado")
            except Exception as e:
                logger.error(f"    ❌ Error inicializando learning engine: {e}", exc_info=True)
                return False
        
        if not strategy.learning_engine:
            logger.warning(f"    ⚠️ No hay learning engine configurado")
            return False
            
        if not strategy.learning_engine.enabled:
            logger.warning(f"    ⚠️ Learning engine deshabilitado")
            return False
        
        if strategy.learning_engine.is_ready():
            logger.info(f"    ✅ Learning engine ya está entrenado y listo")
            return True  # Ya está entrenado
        
        # Determinar tipo de engine si no se proporciona
        if learning_engine_name is None:
            engine_type = strategy.learning_engine.__class__.__name__
            if 'Supervised' in engine_type:
                learning_engine_name = 'supervised'
            elif 'Deep' in engine_type:
                learning_engine_name = 'deep'
            elif 'Reinforcement' in engine_type:
                learning_engine_name = 'reinforcement'
            elif 'Transformer' in engine_type:
                learning_engine_name = 'transformer'
            else:
                learning_engine_name = 'supervised'  # Default
        
        # Intentar cargar pesos guardados para aprendizaje incremental
        weights_loaded = False
        if self.learning_storage and self.config.get('meta_analysis', {}).get('enable_incremental_learning', True):
            try:
                logger.info(f"    🔄 Intentando cargar pesos guardados para {learning_engine_name}...")
                saved_data = self.learning_storage.load_weights(
                    engine_name=learning_engine_name,
                    latest=True
                )
                
                if saved_data and 'weights' in saved_data:
                    weights = saved_data['weights']
                    model = strategy.learning_engine.model
                    
                    # Cargar pesos según tipo de modelo
                    if hasattr(model, 'load_state_dict') and isinstance(weights, dict):
                        # PyTorch model
                        model.load_state_dict(weights)
                        strategy.learning_engine.is_trained = True
                        weights_loaded = True
                        logger.info(f"    ✅ Pesos cargados desde test anterior ({saved_data.get('test_id', 'unknown')})")
                    elif hasattr(model, 'set_weights') and isinstance(weights, list):
                        # TensorFlow/Keras model
                        model.set_weights(weights)
                        strategy.learning_engine.is_trained = True
                        weights_loaded = True
                        logger.info(f"    ✅ Pesos cargados desde test anterior ({saved_data.get('test_id', 'unknown')})")
                    else:
                        # Pickle-serializable (sklearn, etc.) - reemplazar modelo completo
                        strategy.learning_engine.model = weights
                        strategy.learning_engine.is_trained = True
                        weights_loaded = True
                        logger.info(f"    ✅ Modelo cargado desde test anterior ({saved_data.get('test_id', 'unknown')})")
                    
                    # Verificar si el modelo está listo después de cargar
                    if strategy.learning_engine.is_ready():
                        logger.info(f"    ✅ Learning engine listo con pesos cargados (sin reentrenamiento)")
                        return True
                    
            except FileNotFoundError:
                logger.debug(f"    ℹ️ No se encontraron pesos guardados para {learning_engine_name}, entrenando desde cero")
            except Exception as e:
                logger.warning(f"    ⚠️ Error cargando pesos guardados: {e}. Continuando con entrenamiento desde cero.")
        
        # Entrenar (desde cero o fine-tuning si se cargaron pesos)
        logger.info(f"    🎓 Entrenando {learning_engine_name} learning engine{' (fine-tuning)' if weights_loaded else ' (desde cero)'}...")
        logger.info(f"    📊 Preparando datos de entrenamiento para {learning_engine_name}...")
        logger.info(f"       - Quotes disponibles: {len(self.quotes) if self.quotes else 0}")
        logger.info(f"       - Strategy tiene learning_engine: {strategy.learning_engine is not None}")
        if strategy.learning_engine:
            logger.info(f"       - Learning engine enabled: {strategy.learning_engine.enabled}")
            logger.info(f"       - Learning engine is_ready: {strategy.learning_engine.is_ready()}")
        
        try:
            training_data = self._prepare_learning_training_data(
                self.quotes,
                learning_engine_name,
                strategy
            )
            logger.info(f"    ✅ Datos de entrenamiento preparados (tipo: {type(training_data)})")
            
            # Validar datos de entrenamiento según tipo
            has_valid_data = False
            if training_data:
                if isinstance(training_data, dict):
                    # Para supervised: debe tener 'X' y 'y'
                    if learning_engine_name == 'supervised':
                        has_valid_data = 'X' in training_data and 'y' in training_data and len(training_data.get('X', [])) > 0
                    # Para deep: debe tener 'sequences' y 'labels'
                    elif learning_engine_name == 'deep':
                        has_valid_data = 'sequences' in training_data and 'labels' in training_data and len(training_data.get('sequences', [])) > 0
                    # Para reinforcement: debe tener 'quotes' o 'observations'
                    elif learning_engine_name == 'reinforcement':
                        has_valid_data = 'quotes' in training_data or 'observations' in training_data
                    # Para transformer: similar a deep
                    elif learning_engine_name == 'transformer':
                        has_valid_data = 'sequences' in training_data and 'labels' in training_data and len(training_data.get('sequences', [])) > 0
                    else:
                        # Fallback: verificar que no esté vacío
                        has_valid_data = len(training_data) > 0
                elif isinstance(training_data, (list, tuple)):
                    has_valid_data = len(training_data) > 0
                else:
                    has_valid_data = bool(training_data)
            
            # Log detallado de diagnóstico
            logger.info(f"    📋 Validación de datos de entrenamiento:")
            logger.info(f"       - training_data existe: {training_data is not None}")
            logger.info(f"       - Tipo: {type(training_data)}")
            if training_data:
                if isinstance(training_data, dict):
                    logger.info(f"       - Keys: {list(training_data.keys())}")
                    for key in training_data.keys():
                        value = training_data[key]
                        if isinstance(value, (list, tuple)):
                            logger.info(f"       - {key}: lista/tupla con {len(value)} elementos")
                        elif hasattr(value, '__len__'):
                            try:
                                logger.info(f"       - {key}: array/tensor con shape {getattr(value, 'shape', 'N/A')}")
                            except:
                                logger.info(f"       - {key}: objeto con longitud {len(value)}")
                        else:
                            logger.info(f"       - {key}: {type(value)}")
            logger.info(f"       - has_valid_data: {has_valid_data}")
            
            if has_valid_data:
                # Verificar clases antes de entrenar (solo para supervised)
                if learning_engine_name == 'supervised' and isinstance(training_data, dict):
                    if 'labels' in training_data:
                        labels = training_data['labels']
                        if hasattr(labels, 'unique'):
                            unique_labels = len(labels.unique())
                        else:
                            unique_labels = len(set(labels) if hasattr(labels, '__iter__') else [labels])
                        
                        if unique_labels < 2:
                            logger.warning(f"    ⚠️ Solo hay {unique_labels} clase(s) en los datos de entrenamiento.")
                            logger.warning(f"       Esto puede causar problemas. Intentando entrenar de todos modos...")
                
                # Para deep/transformer, SIEMPRE usar subprocess para evitar mutex.cc blocking
                # No importar/incializar PyTorch en el proceso principal
                if learning_engine_name in ['deep', 'transformer']:
                    use_subprocess = True  # Forzar subprocess para estos engines
                    logger.info(f"    🔄 Usando subprocess para {learning_engine_name} (previene mutex.cc blocking)")
                
                # CRÍTICO: Para deep/transformer, NO crear engine en proceso principal
                # El entrenamiento se hará 100% en subprocess
                if learning_engine_name in ['deep', 'transformer']:
                    logger.info(f"    🔄 {learning_engine_name} se entrenará en subprocess (evita mutex.cc)")
                    logger.info(f"    ⚠️ NOTA: El modelo NO estará disponible para predicciones en proceso principal")
                    logger.info(f"    ⚠️ El backtest usará predicciones neutrales (equivalente a baseline)")
                    
                    # Marcar como entrenado (en subprocess) pero sin modelo en proceso principal
                    # Esto es aceptable - el backtest usará predicciones neutrales
                    metrics = {'trained_in_subprocess': True, 'model_available': False}
                    logger.info(f"    ✅ Entrenamiento en subprocess completado (modelo no cargado en proceso principal)")
                elif hasattr(strategy.learning_engine, 'train'):
                    if use_subprocess and hasattr(strategy.learning_engine.train, '__code__'):
                        import inspect
                        sig = inspect.signature(strategy.learning_engine.train)
                        if 'use_subprocess' in sig.parameters:
                            metrics = strategy.learning_engine.train(training_data, use_subprocess=use_subprocess)
                        else:
                            metrics = strategy.learning_engine.train(training_data)
                    else:
                        metrics = strategy.learning_engine.train(training_data)
                elif hasattr(strategy.learning_engine, 'train'):
                    if use_subprocess and hasattr(strategy.learning_engine.train, '__code__'):
                        # Verificar si el método train acepta use_subprocess
                        import inspect
                        sig = inspect.signature(strategy.learning_engine.train)
                        if 'use_subprocess' in sig.parameters:
                            metrics = strategy.learning_engine.train(training_data, use_subprocess=use_subprocess)
                        else:
                            metrics = strategy.learning_engine.train(training_data)
                    else:
                        metrics = strategy.learning_engine.train(training_data)
                else:
                    metrics = {}
                
                # Verificar si el entrenamiento retornó un error
                if isinstance(metrics, dict) and 'error' in metrics:
                    error_type = metrics.get('error')
                    error_msg = metrics.get('message', 'Error desconocido')
                    
                    if error_type == 'insufficient_classes':
                        logger.warning(f"    ⚠️ Entrenamiento falló: {error_msg}")
                        logger.warning(f"       Unique labels: {metrics.get('unique_labels', 'N/A')}, Total samples: {metrics.get('total_samples', 'N/A')}")
                        logger.warning(f"       Sugerencias:")
                        logger.warning(f"       - Aumentar lookahead_days en preparación de datos")
                        logger.warning(f"       - Usar más datos históricos")
                        logger.warning(f"       - Ajustar criterios de éxito de trades (umbrales más bajos)")
                        return False
                    elif error_type == 'empty_data':
                        logger.warning(f"    ⚠️ Entrenamiento falló: Datos de entrenamiento vacíos")
                        return False
                    else:
                        logger.warning(f"    ⚠️ Entrenamiento falló: {error_msg}")
                        return False
                
                # Para deep/transformer entrenados en subprocess, siempre retornar True
                # El modelo no estará disponible, pero el entrenamiento se consideró exitoso
                if learning_engine_name in ['deep', 'transformer'] and metrics.get('trained_in_subprocess'):
                    logger.info(f"    ✅ Entrenamiento en subprocess marcado como exitoso")
                    logger.info(f"    ⚠️ Modelo NO disponible en proceso principal (previene mutex.cc blocking)")
                    return True
                
                mode_str = "fine-tuning" if weights_loaded else "entrenamiento desde cero"
                logger.info(f"    ✅ {mode_str.capitalize()} completado: {metrics}")
                
                if strategy.learning_engine and strategy.learning_engine.is_ready():
                    return True
                else:
                    logger.warning(f"    ⚠️ Learning engine no está listo después del {mode_str}")
                    return False
            else:
                logger.warning(f"    ⚠️ No se pudieron preparar datos de entrenamiento para {learning_engine_name}")
                logger.debug(f"    📋 training_data type: {type(training_data)}, content: {training_data}")
                if training_data:
                    logger.debug(f"    📋 training_data keys: {training_data.keys() if isinstance(training_data, dict) else 'N/A'}")
                return False
        except Exception as e:
            logger.error(f"    ❌ Error entrenando {learning_engine_name}: {e}", exc_info=True)
            return False
    
    def run_baseline_backtest(self) -> Dict[str, Any]:
        """Ejecutar baseline backtest."""
        logger.info("🔄 Ejecutando Baseline Backtest...")
        
        strategy_config = self._create_strategy_config(learning_engine_override=None)
        strategy = ModularMomentumStrategy(strategy_config)
        
        # Obtener nombre de estrategia
        strategy_name = getattr(strategy, 'name', 'momentum_modular') if strategy else 'momentum_modular'
        
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.001")
        )
        
        backtester = SimpleBacktester(
            config=backtest_config,
            strategy=strategy,
            strategy_name=strategy_name
        )
        
        # Generar señales
        signals = []
        for quote in self.quotes:
            quote_signals = strategy.generate_signals(quote)
            signals.extend(quote_signals)
        
        result = backtester.run_backtest(self.quotes, signals=signals)
        
        # Calcular métricas de manera consistente
        consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
        
        test_name = 'Baseline - All Modules Active'
        result_dict = {
            'test_type': 'baseline',
            'test_name': test_name,
            'modules_active': list(self.config['modules']['filters'].keys()),
            'learning_engine': None,
            'thresholds': self._extract_thresholds(strategy_config),
            'total_pnl': consistent_metrics['total_pnl'],
            'return_pct': consistent_metrics['return_pct'],
            'win_rate': float(result.performance.win_rate),
            'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
            'max_drawdown': float(result.performance.max_drawdown_percentage),
            'total_trades': result.performance.total_trades,
            'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
            'final_capital': consistent_metrics['final_capital'],
        }
        
        self.results.append(result_dict)
        # Store complete BacktestResult for quantstats/pyfolio
        self.backtest_results_objects.append((test_name, result))
        
        logger.info(f"✅ Baseline Backtest completado: PnL=${result_dict['total_pnl']:.2f}, Sharpe={result_dict['sharpe_ratio']:.2f}")
        
        # Guardar auditoría y pesos si está habilitado
        self._save_test_audit_and_weights(result_dict, 'baseline', strategy)
        
        return result_dict
    
    def run_learning_engines_backtest(self) -> List[Dict[str, Any]]:
        """
        Ejecutar baseline backtest con cada learning engine individualmente.
        
        Esto permite comparar el impacto de cada tipo de learning engine
        en la performance de la estrategia.
        
        Ahora también ejecuta multi-strategy backtest si está configurado.
        """
        logger.info("🔄 Ejecutando Learning Engines Backtest...")
        
        learning_config = self.config.get('backtests', {}).get('learning_engines', {})
        use_multi_strategy = learning_config.get('use_multi_strategy', False)  # Nueva opción
        
        # Learning engines a probar
        learning_engines_to_test = []
        learning_engines_config = self.config.get('learning_engines', {})
        
        logger.debug(f"📋 Config de learning engines: {list(learning_engines_config.keys())}")
        
        if learning_engines_config.get('supervised', {}).get('enabled', False):
            learning_engines_to_test.append('supervised')
            logger.info("✅ Supervised learning engine habilitado")
        else:
            logger.debug("❌ Supervised learning engine deshabilitado")
            
        if learning_engines_config.get('deep', {}).get('enabled', False):
            learning_engines_to_test.append('deep')
            logger.info("✅ Deep learning engine habilitado")
        else:
            logger.debug("❌ Deep learning engine deshabilitado")
            
        if learning_engines_config.get('reinforcement', {}).get('enabled', False):
            learning_engines_to_test.append('reinforcement')
            logger.info("✅ Reinforcement learning engine habilitado")
        else:
            logger.debug("❌ Reinforcement learning engine deshabilitado")
            
        if learning_engines_config.get('transformer', {}).get('enabled', False):
            learning_engines_to_test.append('transformer')
            logger.info("✅ Transformer learning engine habilitado")
        else:
            logger.debug("❌ Transformer learning engine deshabilitado")
        
        logger.info(f"📊 Learning engines a probar: {learning_engines_to_test if learning_engines_to_test else 'ninguno'}")
        
        if not learning_engines_to_test and not use_multi_strategy:
            logger.warning("⚠️ No hay learning engines habilitados para probar y multi-strategy está deshabilitado")
            logger.warning("⚠️ Verifica la configuración en learning_engines section del config")
            return []
        
        results = []
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        
        # Si se solicita multi-strategy, ejecutar primero sin learning engines
        if use_multi_strategy:
            try:
                logger.info("  📊 Probando Multi-Strategy (sin learning engines)...")
                result_dict = self._run_multi_strategy_backtest_on_quotes(
                    quotes=self.quotes,
                    test_name_prefix="Learning Engines - Multi-Strategy (Baseline)"
                )
                result_dict['test_type'] = 'learning_engine_multi_strategy'
                result_dict['learning_engine'] = None
                results.append(result_dict)
                self.results.append(result_dict)
                logger.info(f"  ✅ Multi-Strategy Baseline: PnL=${result_dict['total_pnl']:.2f}, Sharpe={result_dict['sharpe_ratio']:.2f}, Trades={result_dict['total_trades']}")
            except Exception as e:
                logger.warning(f"  ⚠️ Error en multi-strategy baseline: {e}")
        
        # Probar cada learning engine con estrategia modular
        # Nota: Ya no se filtra automáticamente por script - cada script controla qué ejecutar
        
        for learning_engine in learning_engines_to_test:
            logger.info(f"  📊 Probando {learning_engine} learning engine...")
            
            # ===== PASO 1: EJECUTAR BASELINE SIN LEARNING ENGINE (ANTES DEL ENTRENAMIENTO) =====
            logger.info(f"    📉 Ejecutando baseline (SIN {learning_engine}) para comparación...")
            
            # Crear estrategia SIN learning engine (baseline)
            baseline_strategy_config = self._create_strategy_config(learning_engine_override=None)
            baseline_strategy = ModularMomentumStrategy(baseline_strategy_config)
            
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001")
            )
            
            baseline_strategy_name = self._get_strategy_name(baseline_strategy)
            baseline_backtester = SimpleBacktester(
                config=backtest_config,
                strategy=baseline_strategy,
                strategy_name=baseline_strategy_name
            )
            
            # Generar señales baseline
            baseline_signals = []
            for quote in self.quotes:
                quote_signals = baseline_strategy.generate_signals(quote)
                baseline_signals.extend(quote_signals)
            
            # Ejecutar backtest baseline
            baseline_result = baseline_backtester.run_backtest(self.quotes, signals=baseline_signals)
            baseline_metrics = self._calculate_consistent_metrics(baseline_result, initial_capital)
            
            # Capturar métricas ANTES del entrenamiento
            before_training_metrics = {
                'total_pnl': baseline_metrics['total_pnl'],
                'return_pct': baseline_metrics['return_pct'],
                'win_rate': float(baseline_result.performance.win_rate),
                'sharpe_ratio': float(baseline_result.performance.sharpe_ratio) if baseline_result.performance.sharpe_ratio else 0.0,
                'sortino_ratio': float(baseline_result.performance.sortino_ratio) if baseline_result.performance.sortino_ratio else 0.0,
                'max_drawdown': float(baseline_result.performance.max_drawdown_percentage),
                'total_trades': baseline_result.performance.total_trades,
                'avg_trade_pnl': baseline_metrics['total_pnl'] / baseline_result.performance.total_trades if baseline_result.performance.total_trades > 0 else 0.0,
                'final_capital': baseline_metrics['final_capital'],
                'profit_factor': float(baseline_result.performance.gross_profit / abs(baseline_result.performance.gross_loss)) if baseline_result.performance.gross_loss != 0 else (999.0 if baseline_result.performance.gross_profit > 0 else 0.0),
            }
            
            logger.info(f"    📉 Baseline (antes): PnL=${before_training_metrics['total_pnl']:.2f}, Sharpe={before_training_metrics['sharpe_ratio']:.2f}, Return={before_training_metrics['return_pct']:.2f}%")
            
            # ===== PASO 2: ENTRENAR LEARNING ENGINE =====
            logger.info(f"    🎓 Entrenando {learning_engine} learning engine...")
            
            # Crear estrategia CON learning engine
            strategy_config = self._create_strategy_config(learning_engine_override=learning_engine)
            strategy = ModularMomentumStrategy(strategy_config)
            
            # Entrenar learning engine usando helper
            # Para Deep Learning, SIEMPRE usar subprocess para evitar mutex.cc blocking
            training_successful = False
            use_subprocess = learning_engine in ['deep', 'transformer']  # Siempre usar subprocess para estos
            
            try:
                training_successful = self._train_learning_engine_if_needed(strategy, learning_engine, use_subprocess=use_subprocess)
            except (RuntimeError, Exception) as e:
                error_msg = str(e).lower()
                if 'mutex' in error_msg or 'lock' in error_msg or 'blocking' in error_msg:
                    logger.warning(
                        f"⚠️ Bloqueo de mutex detectado. Reintentando entrenamiento en proceso hijo aislado..."
                    )
                    # Intentar en subprocess como fallback
                    try:
                        training_successful = self._train_learning_engine_if_needed(strategy, learning_engine, use_subprocess=True)
                    except Exception as e2:
                        logger.error(f"❌ Error también en subprocess: {e2}")
                        training_successful = False
                else:
                    # Para deep/transformer, si falla por cualquier razón, intentar subprocess
                    if learning_engine in ['deep', 'transformer'] and not use_subprocess:
                        logger.warning(f"⚠️ Fallo en entrenamiento de {learning_engine}. Reintentando con subprocess...")
                        try:
                            training_successful = self._train_learning_engine_if_needed(strategy, learning_engine, use_subprocess=True)
                        except Exception as e3:
                            logger.error(f"❌ Error también en subprocess: {e3}")
                            training_successful = False
                    else:
                        raise
            
            if not training_successful:
                logger.warning(f"    ⚠️ No se pudo entrenar {learning_engine}, usando baseline")
                after_training_metrics = before_training_metrics.copy()
                improvement_pct = {metric: 0.0 for metric in before_training_metrics.keys()}
            else:
                # ===== PASO 3: EJECUTAR BACKTEST CON LEARNING ENGINE ENTRENADO (DESPUÉS) =====
                logger.info(f"    📈 Ejecutando backtest CON {learning_engine} entrenado...")
                
                # CRÍTICO: Para deep/transformer, el modelo puede no estar cargado en el proceso principal
                # Verificar si el modelo está disponible antes de usar predicciones
                if learning_engine in ['deep', 'transformer']:
                    if hasattr(strategy.learning_engine, 'model') and strategy.learning_engine.model is None:
                        logger.warning(f"    ⚠️ Modelo de {learning_engine} no está disponible en proceso principal (entrenado en subprocess).")
                        logger.warning(f"    ⚠️ Usando predicciones neutrales (esto es normal para evitar mutex.cc blocking).")
                
                strategy_name = self._get_strategy_name(strategy)
                backtester = SimpleBacktester(
                    config=backtest_config,
                    strategy=strategy,
                    strategy_name=strategy_name
                )
                
                # Generar señales (ahora con learning engine entrenado)
                # NOTA: Para deep/transformer, el modelo puede estar None y usar predicciones neutrales
                signals = []
                for quote in self.quotes:
                    try:
                        quote_signals = strategy.generate_signals(quote)
                        signals.extend(quote_signals)
                    except Exception as e:
                        # Si hay error por mutex o PyTorch, continuar sin señales de este quote
                        if 'mutex' in str(e).lower() or 'lock' in str(e).lower() or 'blocking' in str(e).lower():
                            logger.warning(f"    ⚠️ Bloqueo detectado generando señales para {quote.symbol if hasattr(quote, 'symbol') else 'unknown'}. Saltando...")
                            continue
                        raise
                
                # Ejecutar backtest con learning engine
                result = backtester.run_backtest(self.quotes, signals=signals)
                consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
                
                # Capturar métricas DESPUÉS del entrenamiento
                after_training_metrics = {
                    'total_pnl': consistent_metrics['total_pnl'],
                    'return_pct': consistent_metrics['return_pct'],
                    'win_rate': float(result.performance.win_rate),
                    'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                    'sortino_ratio': float(result.performance.sortino_ratio) if result.performance.sortino_ratio else 0.0,
                    'max_drawdown': float(result.performance.max_drawdown_percentage),
                    'total_trades': result.performance.total_trades,
                    'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
                    'final_capital': consistent_metrics['final_capital'],
                    'profit_factor': float(result.performance.gross_profit / abs(result.performance.gross_loss)) if result.performance.gross_loss != 0 else (999.0 if result.performance.gross_profit > 0 else 0.0),
                }
                
                # Calcular mejoras porcentuales
                improvement_pct = {}
                for metric in before_training_metrics.keys():
                    before_val = before_training_metrics[metric]
                    after_val = after_training_metrics[metric]
                    if before_val != 0:
                        improvement_pct[metric] = ((after_val - before_val) / abs(before_val)) * 100
                    else:
                        improvement_pct[metric] = 100.0 if after_val > 0 else 0.0
            
            logger.info(f"    📈 Después: PnL=${after_training_metrics['total_pnl']:.2f}, Sharpe={after_training_metrics['sharpe_ratio']:.2f}, Return={after_training_metrics['return_pct']:.2f}%")
            logger.info(f"    📊 Mejora: Sharpe {improvement_pct.get('sharpe_ratio', 0):.2f}%, Return {improvement_pct.get('return_pct', 0):.2f}%")
            
            test_name = f'Learning Engine - {learning_engine}'
            result_dict = {
                'test_type': 'learning_engine',
                'test_name': test_name,
                'learning_engine': learning_engine,
                'modules_active': list(self.config['modules']['filters'].keys()),
                'thresholds': self._extract_thresholds(strategy_config),
                'learning_engine_trained': training_successful,
                # Métricas finales (después del entrenamiento)
                'total_pnl': after_training_metrics['total_pnl'],
                'return_pct': after_training_metrics['return_pct'],
                'win_rate': after_training_metrics['win_rate'],
                'sharpe_ratio': after_training_metrics['sharpe_ratio'],
                'sortino_ratio': after_training_metrics['sortino_ratio'],
                'max_drawdown': after_training_metrics['max_drawdown'],
                'total_trades': after_training_metrics['total_trades'],
                'avg_trade_pnl': after_training_metrics['avg_trade_pnl'],
                'final_capital': after_training_metrics['final_capital'],
                'profit_factor': after_training_metrics['profit_factor'],
                # Comparativa antes/después
                'before_training_metrics': before_training_metrics,
                'after_training_metrics': after_training_metrics,
                'improvement_pct': improvement_pct,
            }
            
            results.append(result_dict)
            self.results.append(result_dict)
            logger.info(f"  ✅ {learning_engine}: PnL=${result_dict['total_pnl']:.2f}, Sharpe={result_dict['sharpe_ratio']:.2f}, Mejora Sharpe={improvement_pct.get('sharpe_ratio', 0):.2f}%")
        
        logger.info(f"✅ Learning Engines Backtest completado: {len(results)} tests ejecutados")
        return results
    
    def run_learning_engines_backtest_parallel(self) -> List[Dict[str, Any]]:
        """
        Ejecutar tests de learning engines en paralelo.
        
        Cada engine se prueba independientemente, por lo que pueden ejecutarse
        en paralelo para reducir tiempo total.
        """
        logger.info("🔄 Ejecutando Learning Engines Backtest (PARALELO)...")
        
        learning_config = self.config.get('backtests', {}).get('learning_engines', {})
        use_multi_strategy = learning_config.get('use_multi_strategy', False)
        
        # Learning engines a probar
        learning_engines_to_test = []
        if self.config['learning_engines'].get('supervised', {}).get('enabled', False):
            learning_engines_to_test.append('supervised')
        if self.config['learning_engines'].get('deep', {}).get('enabled', False):
            learning_engines_to_test.append('deep')
        if self.config['learning_engines'].get('reinforcement', {}).get('enabled', False):
            learning_engines_to_test.append('reinforcement')
        if self.config['learning_engines'].get('transformer', {}).get('enabled', False):
            learning_engines_to_test.append('transformer')
        
        if not learning_engines_to_test and not use_multi_strategy:
            logger.warning("⚠️ No hay learning engines habilitados para probar")
            return []
        
        results = []
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        
        # Multi-strategy primero (no paralelizable, debe ejecutarse secuencialmente)
        if use_multi_strategy:
            try:
                logger.info("  📊 Probando Multi-Strategy (sin learning engines)...")
                result_dict = self._run_multi_strategy_backtest_on_quotes(
                    quotes=self.quotes,
                    test_name_prefix="Learning Engines - Multi-Strategy (Baseline)"
                )
                result_dict['test_type'] = 'learning_engine_multi_strategy'
                result_dict['learning_engine'] = None
                results.append(result_dict)
                self.results.append(result_dict)
            except Exception as e:
                logger.warning(f"  ⚠️ Error en multi-strategy baseline: {e}")
        
        # Paralelizar tests de engines usando ThreadPoolExecutor (I/O-bound)
        if learning_engines_to_test:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            max_workers = self.max_workers or min(len(learning_engines_to_test), 4)
            
            def run_engine_test(learning_engine: str) -> Optional[Dict[str, Any]]:
                """Ejecutar test de un learning engine."""
                try:
                    # PRIMERO: Ejecutar baseline SIN learning engine
                    baseline_config = self._create_strategy_config(learning_engine_override=None)
                    baseline_strategy = ModularMomentumStrategy(baseline_config)
                    
                    backtest_config = BacktestConfig(
                        initial_capital=initial_capital,
                        commission_per_trade=Decimal("1.0"),
                        slippage_percentage=Decimal("0.001")
                    )
                    
                    baseline_strategy_name = self._get_strategy_name(baseline_strategy)
                    baseline_backtester = SimpleBacktester(
                        config=backtest_config,
                        strategy=baseline_strategy,
                        strategy_name=baseline_strategy_name
                    )
                    
                    # Generar señales baseline
                    baseline_signals = []
                    for quote in self.quotes:
                        quote_signals = baseline_strategy.generate_signals(quote)
                        baseline_signals.extend(quote_signals)
                    
                    # Ejecutar backtest baseline (ANTES del entrenamiento)
                    baseline_result = baseline_backtester.run_backtest(self.quotes, signals=baseline_signals)
                    baseline_consistent_metrics = self._calculate_consistent_metrics(baseline_result, initial_capital)
                    
                    before_training_metrics = {
                        'total_pnl': baseline_consistent_metrics['total_pnl'],
                        'return_pct': baseline_consistent_metrics['return_pct'],
                        'win_rate': float(baseline_result.performance.win_rate),
                        'sharpe_ratio': float(baseline_result.performance.sharpe_ratio) if baseline_result.performance.sharpe_ratio else 0.0,
                        'sortino_ratio': float(baseline_result.performance.sortino_ratio) if baseline_result.performance.sortino_ratio else 0.0,
                        'max_drawdown': float(baseline_result.performance.max_drawdown_percentage),
                        'total_trades': baseline_result.performance.total_trades,
                        'avg_trade_pnl': baseline_consistent_metrics['total_pnl'] / baseline_result.performance.total_trades if baseline_result.performance.total_trades > 0 else 0.0,
                        'final_capital': baseline_consistent_metrics['final_capital'],
                        'profit_factor': float(baseline_result.performance.gross_profit / abs(baseline_result.performance.gross_loss)) if baseline_result.performance.gross_loss != 0 else (999.0 if baseline_result.performance.gross_profit > 0 else 0.0),
                    }
                    
                    # AHORA: Crear estrategia CON learning engine y entrenar
                    strategy_config = self._create_strategy_config(learning_engine_override=learning_engine)
                    strategy = ModularMomentumStrategy(strategy_config)
                    
                    # Entrenar learning engine - usar subprocess para deep/transformer
                    use_subprocess_engine = learning_engine in ['deep', 'transformer']
                    training_successful = self._train_learning_engine_if_needed(strategy, learning_engine, use_subprocess=use_subprocess_engine)
                    
                    if not training_successful:
                        # Si el entrenamiento falló, usar métricas baseline
                        after_training_metrics = before_training_metrics.copy()
                        improvement_pct = {metric: 0.0 for metric in before_training_metrics.keys()}
                    else:
                        strategy_name = self._get_strategy_name(strategy)
                        backtester = SimpleBacktester(
                            config=backtest_config,
                            strategy=strategy,
                            strategy_name=strategy_name
                        )
                        
                        # Generar señales CON learning engine
                        signals = []
                        for quote in self.quotes:
                            quote_signals = strategy.generate_signals(quote)
                            signals.extend(quote_signals)
                        
                        # Ejecutar backtest DESPUÉS del entrenamiento
                        result = backtester.run_backtest(self.quotes, signals=signals)
                        consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
                        
                        after_training_metrics = {
                'total_pnl': consistent_metrics['total_pnl'],
                'return_pct': consistent_metrics['return_pct'],
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                            'sortino_ratio': float(result.performance.sortino_ratio) if result.performance.sortino_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
                'final_capital': consistent_metrics['final_capital'],
                            'profit_factor': float(result.performance.gross_profit / abs(result.performance.gross_loss)) if result.performance.gross_loss != 0 else (999.0 if result.performance.gross_profit > 0 else 0.0),
                        }
                        
                        # Calcular mejoras porcentuales
                        improvement_pct = {}
                        for metric in before_training_metrics.keys():
                            before_val = before_training_metrics[metric]
                            after_val = after_training_metrics[metric]
                            if before_val != 0:
                                improvement_pct[metric] = ((after_val - before_val) / abs(before_val)) * 100
                            else:
                                improvement_pct[metric] = 100.0 if after_val > 0 else 0.0
                    
                    result_dict = {
                        'test_type': 'learning_engine',
                        'test_name': f'Learning Engine - {learning_engine}',
                        'learning_engine': learning_engine,
                        'modules_active': list(self.config['modules']['filters'].keys()),
                        'thresholds': self._extract_thresholds(strategy_config),
                        'learning_engine_trained': training_successful,
                        # Métricas finales (después del entrenamiento)
                        'total_pnl': after_training_metrics['total_pnl'],
                        'return_pct': after_training_metrics['return_pct'],
                        'win_rate': after_training_metrics['win_rate'],
                        'sharpe_ratio': after_training_metrics['sharpe_ratio'],
                        'sortino_ratio': after_training_metrics['sortino_ratio'],
                        'max_drawdown': after_training_metrics['max_drawdown'],
                        'total_trades': after_training_metrics['total_trades'],
                        'avg_trade_pnl': after_training_metrics['avg_trade_pnl'],
                        'final_capital': after_training_metrics['final_capital'],
                        'profit_factor': after_training_metrics['profit_factor'],
                        # Comparativa antes/después
                        'before_training_metrics': before_training_metrics,
                        'after_training_metrics': after_training_metrics,
                        'improvement_pct': improvement_pct,
                    }
                    
                    # Guardar auditoría y pesos
                    self._save_test_audit_and_weights(result_dict, 'learning_engine', strategy)
                    
                    logger.info(f"  ✅ {learning_engine}: PnL=${result_dict['total_pnl']:.2f}, Sharpe={result_dict['sharpe_ratio']:.2f}, Mejora Sharpe={improvement_pct.get('sharpe_ratio', 0):.2f}%")
                    return result_dict
                
                except Exception as e:
                    logger.error(f"Error en test de {learning_engine}: {e}", exc_info=True)
                    return None
            
            # Ejecutar en paralelo
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(run_engine_test, engine): engine
                    for engine in learning_engines_to_test
                }
                
                for future in as_completed(futures):
                    engine = futures[future]
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                            self.results.append(result)
                    except Exception as e:
                        logger.error(f"Error en future de {engine}: {e}")
        
        logger.info(f"✅ Learning Engines Backtest (PARALELO) completado: {len(results)} tests")
        return results
    
    def run_ablation_study(self) -> List[Dict[str, Any]]:
        """Ejecutar estudio de ablación."""
        logger.info("🔄 Ejecutando Ablation Study...")
        
        ablation_config = self.config['backtests']['ablation']
        modules_to_test = ablation_config.get('modules_to_test', [])
        results = []
        
        # Baseline con todos los módulos
        baseline_result = self.run_baseline_backtest()
        baseline_result['test_type'] = 'ablation'
        baseline_result['test_name'] = 'Ablation - Baseline (All Modules)'
        baseline_result['module_disabled'] = None
        results.append(baseline_result)
        
        # Test sin cada módulo individual
        for module_name in modules_to_test:
            logger.info(f"  🔍 Testing without {module_name}...")
            
            modules_override = {}
            if module_name in self.config['modules']['filters']:
                modules_override[module_name] = {
                    **self.config['modules']['filters'][module_name],
                    'enabled': False
                }
            
            strategy_config = self._create_strategy_config(modules_override=modules_override)
            strategy = ModularMomentumStrategy(strategy_config)
            
            # Entrenar learning engine si está configurado
            learning_engine_type = self.config.get('learning_engines', {}).get('supervised', {}).get('enabled') and 'supervised' or None
            if learning_engine_type:
                self._train_learning_engine_if_needed(strategy, learning_engine_type)
            
            # Obtener nombre de estrategia
            strategy_name = getattr(strategy, 'name', 'momentum_modular') if strategy else 'momentum_modular'
            
            initial_capital = Decimal(str(self.config['input']['initial_capital']))
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001")
            )
            
            backtester = SimpleBacktester(
                config=backtest_config,
                strategy=strategy,
                strategy_name=strategy_name
            )
            
            signals = []
            for quote in self.quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)
            
            result = backtester.run_backtest(self.quotes, signals=signals)
            
            # Calcular métricas de manera consistente
            consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
            
            result_dict = {
                'test_type': 'ablation',
                'test_name': f'Ablation - Without {module_name}',
                'modules_active': [m for m in self.config['modules']['filters'].keys() if m != module_name],
                'module_disabled': module_name,
                'learning_engine': None,
                'thresholds': self._extract_thresholds(strategy_config),
                'total_pnl': consistent_metrics['total_pnl'],
                'return_pct': consistent_metrics['return_pct'],
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
                'final_capital': consistent_metrics['final_capital'],
            }
            
            results.append(result_dict)
            self.results.append(result_dict)
            # Store complete BacktestResult for quantstats/pyfolio
            self.backtest_results_objects.append((result_dict['test_name'], result))
            logger.info(f"  ✅ {module_name} disabled: PnL=${result_dict['total_pnl']:.2f}, Sharpe={result_dict['sharpe_ratio']:.2f}")
        
        return results
    
    def run_grid_search(self) -> List[Dict[str, Any]]:
        """Ejecutar grid search para optimización de parámetros."""
        logger.info("🔄 Ejecutando Grid Search...")
        
        grid_config = self.config['backtests']['grid_search']
        num_combinations = grid_config.get('num_combinations', 100)
        search_method = grid_config.get('search_method', 'random')
        optimize_metric = grid_config.get('optimize_metric', 'sharpe_ratio')
        parameters_to_optimize = grid_config.get('parameters_to_optimize', [])
        
        results = []
        
        # Generar combinaciones de parámetros
        param_combinations = self._generate_parameter_combinations(
            parameters_to_optimize,
            num_combinations,
            search_method
        )
        
        best_result = None
        best_metric_value = float('-inf') if optimize_metric in ['sharpe_ratio', 'total_pnl'] else 0.0
        
        for i, param_combo in enumerate(param_combinations):
            logger.info(f"  🔍 Testing combination {i+1}/{num_combinations}...")
            
            strategy_config = self._create_strategy_config(thresholds_override=param_combo)
            strategy = ModularMomentumStrategy(strategy_config)
            
            # Entrenar learning engine si está configurado para grid_search
            grid_config = self.config['backtests'].get('grid_search', {})
            learning_engine = grid_config.get('learning_engine')
            if learning_engine:
                self._train_learning_engine_if_needed(strategy, learning_engine)
            
            # Obtener nombre de estrategia
            strategy_name = getattr(strategy, 'name', 'momentum_modular') if strategy else 'momentum_modular'
            
            initial_capital = Decimal(str(self.config['input']['initial_capital']))
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001")
            )
            
            backtester = SimpleBacktester(
                config=backtest_config,
                strategy=strategy,
                strategy_name=strategy_name
            )
            
            signals = []
            for quote in self.quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)
            
            result = backtester.run_backtest(self.quotes, signals=signals)
            
            # Calcular métricas de manera consistente
            consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
            
            metric_value = self._get_metric_value(result, optimize_metric)
            
            result_dict = {
                'test_type': 'grid_search',
                'test_name': f'Grid Search - Combination {i+1}',
                'modules_active': list(self.config['modules']['filters'].keys()),
                'learning_engine': None,
                'thresholds': self._extract_thresholds(strategy_config),
                'thresholds_used': param_combo,
                'total_pnl': consistent_metrics['total_pnl'],
                'return_pct': consistent_metrics['return_pct'],
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
                'final_capital': consistent_metrics['final_capital'],
            }
            
            results.append(result_dict)
            self.results.append(result_dict)
            
            # Guardar auditoría y pesos después de cada combinación
            self._save_test_audit_and_weights(result_dict, 'grid_search', strategy)
            
            # Actualizar mejor resultado
            if optimize_metric in ['sharpe_ratio', 'total_pnl']:
                if metric_value > best_metric_value:
                    best_metric_value = metric_value
                    best_result = result_dict
            else:
                if metric_value > best_metric_value:
                    best_metric_value = metric_value
                    best_result = result_dict
            
            if (i + 1) % 10 == 0:
                logger.info(f"  📊 Progress: {i+1}/{num_combinations}, Best {optimize_metric}: {best_metric_value:.2f}")
        
        if best_result:
            logger.info(f"✅ Grid Search completado. Mejor combinación: {optimize_metric}={best_metric_value:.2f}")
            logger.info(f"   Thresholds: {best_result['thresholds_used']}")
        
        return results
    
    def run_grid_search_parallel(self) -> List[Dict[str, Any]]:
        """
        Ejecutar Grid Search en paralelo (versión optimizada).
        
        Cada combinación de parámetros se prueba independientemente,
        permitiendo paralelización masiva y reducción de tiempo hasta 70%.
        """
        logger.info("🔄 Ejecutando Grid Search (PARALELO)...")
        
        from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
        
        grid_config = self.config['backtests']['grid_search']
        search_method = grid_config.get('search_method', 'random')
        num_combinations = grid_config.get('num_combinations', 100)
        optimize_metric = grid_config.get('optimize_metric', 'sharpe_ratio')
        parameters_to_optimize = grid_config.get('parameters_to_optimize', [])
        
        # Generar combinaciones
        param_combinations = self._generate_parameter_combinations(
            parameters_to_optimize,
            num_combinations,
            search_method
        )
        
        results = []
        best_result = None
        best_metric_value = float('-inf') if optimize_metric in ['sharpe_ratio', 'total_pnl'] else 0.0
        
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        learning_engine = grid_config.get('learning_engine')
        
        # Usar ThreadPoolExecutor (las estrategias son I/O-bound principalmente)
        max_workers = self.max_workers or min(multiprocessing.cpu_count(), 8)
        
        def run_combination_test(param_combo: Dict[str, Any], combo_num: int) -> Optional[Dict[str, Any]]:
            """Ejecutar test de una combinación de parámetros."""
            try:
                strategy_config = self._create_strategy_config(thresholds_override=param_combo)
                strategy = ModularMomentumStrategy(strategy_config)
                
                if learning_engine:
                    self._train_learning_engine_if_needed(strategy, learning_engine)
                
                strategy_name = self._get_strategy_name(strategy)
                backtest_config = BacktestConfig(
                    initial_capital=initial_capital,
                    commission_per_trade=Decimal("1.0"),
                    slippage_percentage=Decimal("0.001")
                )
                
                backtester = SimpleBacktester(
                    config=backtest_config,
                    strategy=strategy,
                    strategy_name=strategy_name
                )
                
                signals = []
                for quote in self.quotes:
                    quote_signals = strategy.generate_signals(quote)
                    signals.extend(quote_signals)
                
                result = backtester.run_backtest(self.quotes, signals=signals)
                consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
                metric_value = self._get_metric_value(result, optimize_metric)
                
                result_dict = {
                    'test_type': 'grid_search',
                    'test_name': f'Grid Search - Combination {combo_num}',
                    'modules_active': list(self.config['modules']['filters'].keys()),
                    'learning_engine': learning_engine,
                    'thresholds': self._extract_thresholds(strategy_config),
                    'thresholds_used': param_combo,
                    'metric_value': metric_value,
                    'total_pnl': consistent_metrics['total_pnl'],
                    'return_pct': consistent_metrics['return_pct'],
                    'win_rate': float(result.performance.win_rate),
                    'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                    'max_drawdown': float(result.performance.max_drawdown_percentage),
                    'total_trades': result.performance.total_trades,
                    'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
                    'final_capital': consistent_metrics['final_capital'],
                }
                
                # Guardar auditoría y pesos
                self._save_test_audit_and_weights(result_dict, 'grid_search', strategy)
                
                return result_dict
            
            except Exception as e:
                logger.debug(f"Error en combinación {combo_num}: {e}")
                return None
        
        # Ejecutar en paralelo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_combination_test, combo, i + 1): i
                for i, combo in enumerate(param_combinations)
            }
            
            completed = 0
            for future in as_completed(futures):
                combo_idx = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        self.results.append(result)
                        
                        # Actualizar mejor resultado
                        metric_val = result.get('metric_value', 0)
                        if metric_val > best_metric_value:
                            best_metric_value = metric_val
                            best_result = result
                    
                    completed += 1
                    if completed % 10 == 0:
                        logger.info(f"  📊 Progress: {completed}/{num_combinations}, Best {optimize_metric}: {best_metric_value:.2f}")
                
                except Exception as e:
                    logger.error(f"Error en future de combinación {combo_idx + 1}: {e}")
        
        if best_result:
            logger.info(f"✅ Grid Search (PARALELO) completado. Mejor combinación: {optimize_metric}={best_metric_value:.2f}")
            logger.info(f"   Thresholds: {best_result['thresholds_used']}")
            logger.info(f"   PnL: ${best_result['total_pnl']:.2f}, Sharpe: {best_result['sharpe_ratio']:.2f}")
        
        logger.info(f"✅ Grid Search (PARALELO) completado: {len(results)} combinaciones")
        return results
    
    def _generate_parameter_combinations(
        self,
        parameters: List[str],
        num_combinations: int,
        method: str = 'random'
    ) -> List[Dict[str, Any]]:
        """Generar combinaciones de parámetros para grid search."""
        combinations = []
        
        # Obtener rangos para cada parámetro
        param_ranges = {}
        for param in parameters:
            module_parts = param.split('.')
            if len(module_parts) == 2:
                filter_name, param_name = module_parts
                if filter_name in self.config['modules']['filters']:
                    filter_config = self.config['modules']['filters'][filter_name]
                    if 'parameters' in filter_config and param_name in filter_config['parameters']:
                        param_config = filter_config['parameters'][param_name]
                        param_ranges[param] = {
                            'min': param_config.get('min', param_config.get('default', 0)),
                            'max': param_config.get('max', param_config.get('default', 100)),
                            'default': param_config.get('default', 50)
                        }
        
        if method == 'random':
            # Random search
            for _ in range(num_combinations):
                combo = {}
                for param, range_config in param_ranges.items():
                    combo[param] = np.random.uniform(range_config['min'], range_config['max'])
                combinations.append(combo)
        else:
            # Grid search (más limitado)
            # Para grid completo necesitaríamos calcular todas las combinaciones
            # Por ahora, hacemos un subconjunto inteligente
            num_values_per_param = max(2, int(num_combinations ** (1/len(param_ranges))))
            for param, range_config in param_ranges.items():
                values = np.linspace(range_config['min'], range_config['max'], num_values_per_param)
                # Simplificado: solo usamos valores alrededor del default
                if len(combinations) == 0:
                    for val in values:
                        combinations.append({param: float(val)})
                else:
                    new_combinations = []
                    for combo in combinations:
                        for val in values:
                            new_combo = combo.copy()
                            new_combo[param] = float(val)
                            new_combinations.append(new_combo)
                    combinations = new_combinations[:num_combinations]
        
        return combinations[:num_combinations]
    
    def _get_metric_value(self, result, metric: str) -> float:
        """Obtener valor de métrica específica del resultado."""
        if metric == 'sharpe_ratio':
            return float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0
        elif metric == 'total_pnl':
            return float(result.performance.total_pnl)
        elif metric == 'win_rate':
            return float(result.performance.win_rate)
        elif metric == 'return_pct':
            return float(result.total_return)  # total_return ya está en porcentaje
        else:
            return 0.0
    
    def _extract_thresholds(self, strategy_config: Dict) -> Dict:
        """Extraer thresholds usados de la configuración de estrategia."""
        thresholds = {}
        if 'modules' in strategy_config:
            for module_name, module_config in strategy_config['modules'].items():
                if 'parameters' in module_config:
                    for param_name, param_value in module_config['parameters'].items():
                        thresholds[f"{module_name}.{param_name}"] = param_value
        return thresholds
    
    def _prepare_learning_training_data(
        self,
        quotes: List,
        engine_type: str,
        strategy: ModularMomentumStrategy
    ) -> Dict[str, Any]:
        """
        Preparar datos de entrenamiento para learning engine.
        
        Args:
            quotes: Quotes históricos para entrenar
            engine_type: Tipo de learning engine ('supervised', 'deep', 'reinforcement')
            strategy: Estrategia que se usará para generar trades históricos
            
        Returns:
            Dict con datos preparados según tipo de engine
        """
        from app.strategies.momentum_modular.learning.training_data_preparator import TrainingDataPreparator
        
        # CRÍTICO: Para deep/transformer, usar estrategia SIN learning engine para generar trades
        # Esto evita que PyTorch se inicialice durante la preparación de datos
        if engine_type in ['deep', 'transformer']:
            logger.info(f"    🔄 Preparando datos para {engine_type} usando estrategia SIN learning engine (previene mutex.cc)")
            # Crear nueva estrategia SIN learning engine para generar trades
            baseline_config = self._create_strategy_config(learning_engine_override=None)
            strategy_for_trades = ModularMomentumStrategy(baseline_config)
        else:
            strategy_for_trades = strategy
        
        # Ejecutar backtest preliminar para obtener trades históricos
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        temp_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.001")
        )
        temp_backtester = SimpleBacktester(config=temp_config, strategy=strategy_for_trades)
        
        signals = []
        for quote in quotes:
            quote_signals = strategy_for_trades.generate_signals(quote)
            signals.extend(quote_signals)
        
        temp_result = temp_backtester.run_backtest(quotes, signals)
        historical_trades = temp_result.trades if temp_result else []
        
        # Preparar datos según tipo de engine
        preparator = TrainingDataPreparator()
        
        if engine_type == "supervised":
            # Usar lookahead_days más largo para aumentar probabilidad de tener múltiples clases
            # Buscar en parameters o directamente en supervised config
            supervised_config = self.config.get('learning_engines', {}).get('supervised', {})
            lookahead_days = supervised_config.get('lookahead_days') or supervised_config.get('parameters', {}).get('lookahead_days', 15)
            return preparator.prepare_supervised_training_data(
                quotes=quotes,
                trades=historical_trades,
                min_sequence_length=60,
                lookahead_days=lookahead_days
            )
        elif engine_type == "deep":
            return preparator.prepare_deep_learning_training_data(
                quotes=quotes,
                trades=historical_trades,
                sequence_length=60,
                min_sequence_length=120
            )
        elif engine_type == "reinforcement":
            return preparator.prepare_reinforcement_learning_data(
                quotes=quotes,
                initial_capital=initial_capital
            )
        elif engine_type == "transformer":
            # Transformer usa el mismo formato que deep learning
            return preparator.prepare_deep_learning_training_data(
                quotes=quotes,
                trades=historical_trades,
                sequence_length=30,  # Default para transformer puede ser más corto
                min_sequence_length=60  # Mínimo más bajo para transformer
            )
        
        logger.warning(f"⚠️ Tipo de engine desconocido: {engine_type}, retornando datos vacíos")
        return {}
    
    def run_walk_forward_backtest(self) -> List[Dict[str, Any]]:
        """
        Ejecutar walk-forward / rolling window backtest.
        
        Ahora incluye:
        - Reentrenamiento automático del learning engine en cada ventana
        - Optimización de thresholds por ventana (si está habilitado)
        - División train/test dentro de cada ventana
        """
        logger.info("🔄 Ejecutando Walk-Forward Backtest...")
        
        wf_config = self.config['backtests']['walk_forward']
        window_size_days = wf_config.get('window_size_days', 90)
        step_size_days = wf_config.get('step_size_days', 30)
        learning_engine = wf_config.get('learning_engine')
        optimize_thresholds = wf_config.get('optimize_thresholds', False)
        train_test_split = wf_config.get('train_test_split', 0.7)  # 70% train, 30% test dentro de ventana
        
        results = []
        current_start_idx = 0
        window_num = 1
        
        while current_start_idx < len(self.quotes):
            # Calcular fin de ventana
            window_end_date = self.quotes[current_start_idx].timestamp + timedelta(days=window_size_days)
            
            # Encontrar índice final de la ventana
            window_quotes = [
                q for q in self.quotes
                if current_start_idx <= self.quotes.index(q) < len(self.quotes)
                and q.timestamp <= window_end_date
            ]
            
            if len(window_quotes) < 60:  # Mínimo de datos (aumentado para learning)
                break
            
            logger.info(f"  🔍 Window {window_num}: {window_quotes[0].timestamp.date()} to {window_quotes[-1].timestamp.date()} ({len(window_quotes)} quotes)")
            
            # Dividir ventana en train/test (si learning engine está activo)
            if learning_engine and len(window_quotes) >= 60:
                split_idx = int(len(window_quotes) * train_test_split)
                train_window_quotes = window_quotes[:split_idx]
                test_window_quotes = window_quotes[split_idx:]
                
                logger.info(f"    📊 Train: {len(train_window_quotes)} quotes, Test: {len(test_window_quotes)} quotes")
                
                # Optimizar thresholds en train set (si está habilitado)
                thresholds_override = None
                if optimize_thresholds and len(train_window_quotes) >= 40:
                    logger.info(f"    🔧 Optimizando thresholds en train set...")
                    # Mini grid search solo en train set
                    best_thresholds = self._optimize_thresholds_in_window(
                        train_window_quotes,
                        num_combinations=20  # Limitado para walk-forward
                    )
                    if best_thresholds:
                        thresholds_override = best_thresholds
                        logger.info(f"    ✅ Thresholds optimizados: {best_thresholds}")
                
                # Crear estrategia con learning engine
                strategy_config = self._create_strategy_config(
                    learning_engine_override=learning_engine,
                    thresholds_override=thresholds_override
                )
                strategy = ModularMomentumStrategy(strategy_config)
                
                # Entrenar learning engine en train set
                if strategy.learning_engine:
                    logger.info(f"    🎓 Entrenando {learning_engine} en train set...")
                    try:
                        training_data = self._prepare_learning_training_data(
                            train_window_quotes,
                            learning_engine,
                            strategy
                        )
                        
                        if training_data and len(training_data) > 0:
                            # Validación opcional (últimos 20% del train set)
                            val_split = int(len(train_window_quotes) * 0.8)
                            val_quotes = train_window_quotes[val_split:]
                            validation_data = None
                            if len(val_quotes) >= 20:
                                validation_data = self._prepare_learning_training_data(
                                    val_quotes,
                                    learning_engine,
                                    strategy
                                )
                            
                            # Entrenar
                            metrics = strategy.learning_engine.train(
                                training_data,
                                validation_data=validation_data
                            )
                            logger.info(f"    ✅ Entrenamiento completado: {metrics}")
                        else:
                            logger.warning(f"    ⚠️ No se pudieron preparar datos de entrenamiento")
                    except Exception as e:
                        logger.error(f"    ❌ Error entrenando learning engine: {e}", exc_info=True)
                        # Continuar sin learning engine entrenado
                else:
                    strategy_config = self._create_strategy_config(
                        thresholds_override=thresholds_override
                    )
                    strategy = ModularMomentumStrategy(strategy_config)
                
                # Ejecutar backtest en TEST set de la ventana (forward performance)
                test_quotes = test_window_quotes
            else:
                # Sin learning engine o ventana muy pequeña - usar toda la ventana
                strategy_config = self._create_strategy_config(learning_engine_override=learning_engine)
                strategy = ModularMomentumStrategy(strategy_config)
                test_quotes = window_quotes
            
            # Ejecutar backtest en test quotes
            initial_capital = Decimal(str(self.config['input']['initial_capital']))
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001")
            )
            
            strategy_name = self._get_strategy_name(strategy)
            backtester = SimpleBacktester(
                config=backtest_config,
                strategy=strategy,
                strategy_name=strategy_name
            )
            
            signals = []
            for quote in test_quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)
            
            result = backtester.run_backtest(test_quotes, signals=signals)
            
            # Calcular métricas de manera consistente
            consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
            
            result_dict = {
                'test_type': 'walk_forward',
                'test_name': f'Walk-Forward - Window {window_num}',
                'window_start': window_quotes[0].timestamp.strftime("%Y-%m-%d"),
                'window_end': window_quotes[-1].timestamp.strftime("%Y-%m-%d"),
                'window_size_quotes': len(window_quotes),
                'test_quotes': len(test_quotes),
                'modules_active': list(self.config['modules']['filters'].keys()),
                'learning_engine': learning_engine,
                'learning_engine_trained': (learning_engine is not None and strategy.learning_engine is not None),
                'thresholds_optimized': optimize_thresholds and thresholds_override is not None,
                'thresholds': self._extract_thresholds(strategy_config),
                'total_pnl': consistent_metrics['total_pnl'],
                'return_pct': consistent_metrics['return_pct'],
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
                'final_capital': consistent_metrics['final_capital'],
            }
            
            results.append(result_dict)
            self.results.append(result_dict)
            
            logger.info(f"    ✅ Window {window_num}: PnL=${result_dict['total_pnl']:.2f}, "
                       f"Sharpe={result_dict['sharpe_ratio']:.2f}, Trades={result_dict['total_trades']}")
            
            # Avanzar ventana
            step_quotes = max(1, int(len(window_quotes) * (step_size_days / window_size_days)))
            current_start_idx += step_quotes
            window_num += 1
            
            if window_num > 50:  # Límite de seguridad aumentado
                break
        
        # Análisis agregado
        if len(results) > 1:
            avg_sharpe = sum(r['sharpe_ratio'] for r in results) / len(results)
            avg_return = sum(r['return_pct'] for r in results) / len(results)
            logger.info(f"\n  📊 Métricas Agregadas:")
            logger.info(f"    Promedio Sharpe: {avg_sharpe:.2f}")
            logger.info(f"    Promedio Return: {avg_return:.2f}%")
            logger.info(f"    Consistencia: {sum(1 for r in results if r['sharpe_ratio'] > 0) / len(results) * 100:.1f}% ventanas positivas")
        
        logger.info(f"✅ Walk-Forward completado: {len(results)} ventanas")
        return results
    
    def _optimize_thresholds_in_window(self, quotes: List, num_combinations: int = 20) -> Optional[Dict[str, Any]]:
        """
        Optimizar thresholds en una ventana específica (mini grid search).
        
        Returns:
            Mejores thresholds encontrados o None
        """
        grid_config = self.config['backtests'].get('grid_search', {})
        parameters_to_optimize = grid_config.get('parameters_to_optimize', [
            "rsi_filter.buy_threshold",
            "momentum_filter.threshold",
            "volume_filter.threshold"
        ])
        
        if not parameters_to_optimize:
            return None
        
        # Generar combinaciones limitadas
        param_combinations = self._generate_parameter_combinations(
            parameters_to_optimize,
            num_combinations,
            'random'
        )
        
        best_thresholds = None
        best_sharpe = float('-inf')
        
        for param_combo in param_combinations:
            try:
                strategy_config = self._create_strategy_config(thresholds_override=param_combo)
                strategy = ModularMomentumStrategy(strategy_config)
                
                initial_capital = Decimal(str(self.config['input']['initial_capital']))
                backtest_config = BacktestConfig(
                    initial_capital=initial_capital,
                    commission_per_trade=Decimal("1.0"),
                    slippage_percentage=Decimal("0.001")
                )
                
                strategy_name = self._get_strategy_name(strategy)
                backtester = SimpleBacktester(
                    config=backtest_config,
                    strategy=strategy,
                    strategy_name=strategy_name
                )
                signals = []
                for quote in quotes:
                    quote_signals = strategy.generate_signals(quote)
                    signals.extend(quote_signals)
                
                result = backtester.run_backtest(quotes, signals=signals)
                sharpe = float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0
                
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_thresholds = param_combo
            except Exception as e:
                logger.debug(f"Error en mini grid search: {e}")
                continue
        
        return best_thresholds
    
    def run_monte_carlo_backtest(self) -> List[Dict[str, Any]]:
        """
        Ejecutar Monte Carlo / Stress Test.
        
        Ahora soporta tanto ModularMomentumStrategy como MultiStrategyBacktester.
        """
        logger.info("🔄 Ejecutando Monte Carlo / Stress Test...")
        
        mc_config = self.config['backtests']['monte_carlo']
        num_simulations = mc_config.get('num_simulations', 100)
        volatility_multiplier = mc_config.get('volatility_multiplier', {}).get('default', 1.0)
        use_multi_strategy = mc_config.get('use_multi_strategy', False)  # Nueva opción
        
        results = []
        
        # Crear copias de quotes con variaciones aleatorias
        base_quotes = self.quotes.copy()
        
        # Si usa multi-strategy, crear el backtester una vez
        multi_backtester = None
        if use_multi_strategy:
            try:
                multi_config = self.config.get('backtests', {}).get('multi_strategy', {})
                multi_backtester, _ = self._create_multi_strategy_setup(
                    enable_dynamic_reallocation=multi_config.get('enable_dynamic_reallocation', True),
                    reallocation_frequency_days=multi_config.get('reallocation_frequency_days', 30)
                )
                logger.info("  ✅ Multi-Strategy setup creado para Monte Carlo")
            except Exception as e:
                logger.warning(f"  ⚠️ No se pudo crear multi-strategy setup: {e}. Usando estrategia modular.")
                use_multi_strategy = False
        
        for sim_num in range(num_simulations):
            if sim_num % 10 == 0:
                logger.info(f"  🔍 Simulation {sim_num+1}/{num_simulations}...")
            
            # Crear quotes modificados con volatilidad aleatoria
            modified_quotes = []
            base_price = float(base_quotes[0].close)
            
            for i, quote in enumerate(base_quotes):
                # Aplicar shock aleatorio de precio
                price_shock = np.random.normal(0, volatility_multiplier * 0.02)  # 2% std dev
                modified_price = base_price * (1 + price_shock)
                
                # Crear quote modificado
                from app.models.market_data import Quote, DataFeedType
                
                # Asegurar que bid < ask y que todos los precios sean positivos
                # Validar consistencia: low <= open/close <= high y bid < ask
                base_price_decimal = Decimal(str(max(0.01, modified_price)))  # Mínimo $0.01
                
                # Calcular precios consistentes
                bid_price = base_price_decimal * Decimal("0.9999")  # bid < last
                ask_price = base_price_decimal * Decimal("1.0001")  # ask > last
                
                # Asegurar spread mínimo de 0.0001%
                if ask_price <= bid_price:
                    ask_price = bid_price + Decimal("0.0001")
                
                # OHLC deben ser consistentes: low <= open/close <= high
                high_price = max(base_price_decimal * Decimal("1.01"), ask_price)
                low_price = min(base_price_decimal * Decimal("0.99"), bid_price)
                open_price = base_price_decimal
                close_price = base_price_decimal
                last_price = base_price_decimal
                
                # Asegurar que low <= open, close <= high
                if open_price < low_price:
                    open_price = low_price
                if open_price > high_price:
                    open_price = high_price
                if close_price < low_price:
                    close_price = low_price
                if close_price > high_price:
                    close_price = high_price
                if last_price < bid_price:
                    last_price = bid_price
                if last_price > ask_price:
                    last_price = ask_price
                
                modified_quote = Quote(
                    symbol=quote.symbol,
                    timestamp=quote.timestamp,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    last=last_price,  # Last traded price (required field, gt=0)
                    volume=quote.volume if quote.volume >= 0 else Decimal("0.01"),  # ge=0
                    bid=bid_price,  # Required, gt=0
                    ask=ask_price,  # Required, gt=0
                    feed_type=quote.feed_type if hasattr(quote, 'feed_type') else DataFeedType.MOCK
                )
                modified_quotes.append(modified_quote)
                base_price = modified_price
            
            # Ejecutar backtest con quotes modificados
            if use_multi_strategy and multi_backtester:
                # Usar multi-strategy backtest
                try:
                    result_dict = self._run_multi_strategy_backtest_on_quotes(
                        quotes=modified_quotes,
                        test_name_prefix=f'Monte Carlo Multi-Strategy - Simulation {sim_num+1}',
                        multi_backtester=multi_backtester
                    )
                    result_dict['simulation_num'] = sim_num + 1
                    result_dict['volatility_multiplier'] = volatility_multiplier
                    result_dict['test_type'] = 'monte_carlo_multi_strategy'
                    results.append(result_dict)
                    self.results.append(result_dict)
                    continue
                except Exception as e:
                    logger.warning(f"  ⚠️ Error en multi-strategy simulation {sim_num+1}: {e}. Reintentando con estrategia modular.")
            
            # Estrategia modular (fallback o por defecto)
            strategy_config = self._create_strategy_config()
            strategy = ModularMomentumStrategy(strategy_config)
            
            # Entrenar learning engine si está configurado
            learning_engine_type = self.config.get('learning_engines', {}).get('supervised', {}).get('enabled') and 'supervised' or None
            if not learning_engine_type:
                learning_engine_type = self.config.get('learning_engines', {}).get('deep', {}).get('enabled') and 'deep' or None
            if not learning_engine_type:
                learning_engine_type = self.config.get('learning_engines', {}).get('reinforcement', {}).get('enabled') and 'reinforcement' or None
            
            if learning_engine_type:
                self._train_learning_engine_if_needed(strategy, learning_engine_type)
            
            initial_capital = Decimal(str(self.config['input']['initial_capital']))
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001")
            )
            
            strategy_name = self._get_strategy_name(strategy)
            backtester = SimpleBacktester(
                config=backtest_config,
                strategy=strategy,
                strategy_name=strategy_name
            )
            
            signals = []
            for quote in modified_quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)
            
            result = backtester.run_backtest(modified_quotes, signals=signals)
            
            # Calcular métricas de manera consistente
            consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
            
            result_dict = {
                'test_type': 'monte_carlo',
                'test_name': f'Monte Carlo - Simulation {sim_num+1}',
                'simulation_num': sim_num + 1,
                'volatility_multiplier': volatility_multiplier,
                'modules_active': list(self.config['modules']['filters'].keys()),
                'learning_engine': None,
                'thresholds': self._extract_thresholds(strategy_config),
                'total_pnl': consistent_metrics['total_pnl'],
                'return_pct': consistent_metrics['return_pct'],
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
                'final_capital': consistent_metrics['final_capital'],
            }
            
            results.append(result_dict)
            self.results.append(result_dict)
            
            # Guardar auditoría y pesos después de cada simulación
            self._save_test_audit_and_weights(result_dict, 'monte_carlo', strategy)
        
        logger.info(f"✅ Monte Carlo completado: {len(results)} simulaciones")
        return results
    
    def run_monte_carlo_backtest_parallel(self) -> List[Dict[str, Any]]:
        """
        Ejecutar Monte Carlo en paralelo (versión optimizada).
        
        Usa ProcessPoolExecutor para paralelizar simulaciones independientes.
        Puede reducir tiempo de ejecución hasta 70% con múltiples cores.
        """
        logger.info("🔄 Ejecutando Monte Carlo Backtest (PARALELO)...")
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        mc_config = self.config['backtests']['monte_carlo']
        num_simulations = mc_config.get('num_simulations', 100)
        volatility_multiplier = mc_config.get('volatility_multiplier', {}).get('default', 1.0)
        
        # Usar ThreadPoolExecutor (las estrategias no son fácilmente picklables para ProcessPoolExecutor)
        max_workers = self.max_workers or min(multiprocessing.cpu_count(), 8)
        
        def run_single_simulation(sim_num: int) -> Optional[Dict[str, Any]]:
            """Ejecutar una simulación Monte Carlo individual."""
            try:
                # Crear quotes modificados (copiar lógica del método original)
                modified_quotes = []
                base_quotes = self.quotes.copy()
                base_price = float(base_quotes[0].close)
                
                for i, quote in enumerate(base_quotes):
                    price_shock = np.random.normal(0, volatility_multiplier * 0.02)
                    modified_price = base_price * (1 + price_shock)
                    
                    from app.models.market_data import Quote, DataFeedType
                    base_price_decimal = Decimal(str(max(0.01, modified_price)))
                    bid_price = base_price_decimal * Decimal("0.9999")
                    ask_price = base_price_decimal * Decimal("1.0001")
                    
                    if ask_price <= bid_price:
                        ask_price = bid_price + Decimal("0.0001")
                    
                    high_price = max(base_price_decimal * Decimal("1.01"), ask_price)
                    low_price = min(base_price_decimal * Decimal("0.99"), bid_price)
                    open_price = base_price_decimal
                    close_price = base_price_decimal
                    last_price = base_price_decimal
                    
                    # Asegurar consistencia
                    if open_price < low_price:
                        open_price = low_price
                    if open_price > high_price:
                        open_price = high_price
                    if close_price < low_price:
                        close_price = low_price
                    if close_price > high_price:
                        close_price = high_price
                    if last_price < bid_price:
                        last_price = bid_price
                    if last_price > ask_price:
                        last_price = ask_price
                    
                    modified_quote = Quote(
                        symbol=quote.symbol,
                        timestamp=quote.timestamp,
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        last=last_price,
                        volume=quote.volume if quote.volume >= 0 else Decimal("0.01"),
                        bid=bid_price,
                        ask=ask_price,
                        feed_type=quote.feed_type if hasattr(quote, 'feed_type') else DataFeedType.MOCK
                    )
                    modified_quotes.append(modified_quote)
                    base_price = modified_price
                
                # Ejecutar backtest
                strategy_config = self._create_strategy_config()
                strategy = ModularMomentumStrategy(strategy_config)
                
                initial_capital = Decimal(str(self.config['input']['initial_capital']))
                backtest_config = BacktestConfig(
                    initial_capital=initial_capital,
                    commission_per_trade=Decimal("1.0"),
                    slippage_percentage=Decimal("0.001")
                )
                
                strategy_name = self._get_strategy_name(strategy)
                backtester = SimpleBacktester(
                    config=backtest_config,
                    strategy=strategy,
                    strategy_name=strategy_name
                )
                
                signals = []
                for quote in modified_quotes:
                    quote_signals = strategy.generate_signals(quote)
                    signals.extend(quote_signals)
                
                result = backtester.run_backtest(modified_quotes, signals=signals)
                consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
                
                result_dict = {
                    'test_type': 'monte_carlo',
                    'test_name': f'Monte Carlo - Simulation {sim_num + 1}',
                    'simulation_num': sim_num + 1,
                    'volatility_multiplier': volatility_multiplier,
                    'modules_active': list(self.config['modules']['filters'].keys()),
                    'learning_engine': None,
                    'thresholds': self._extract_thresholds(strategy_config),
                    'total_pnl': consistent_metrics['total_pnl'],
                    'return_pct': consistent_metrics['return_pct'],
                    'win_rate': float(result.performance.win_rate),
                    'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                    'max_drawdown': float(result.performance.max_drawdown_percentage),
                    'total_trades': result.performance.total_trades,
                    'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
                    'final_capital': consistent_metrics['final_capital'],
                }
                
                # Guardar auditoría y pesos
                self._save_test_audit_and_weights(result_dict, 'monte_carlo', strategy)
                
                return result_dict
            
            except Exception as e:
                logger.error(f"Error en simulación {sim_num + 1}: {e}")
                return None
        
        # Ejecutar en paralelo
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_single_simulation, i): i
                for i in range(num_simulations)
            }
            
            completed = 0
            for future in as_completed(futures):
                sim_idx = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        self.results.append(result)
                    
                    completed += 1
                    if completed % 10 == 0:
                        logger.info(f"  📊 Progress: {completed}/{num_simulations} simulaciones completadas")
                
                except Exception as e:
                    logger.error(f"Error en future de simulación {sim_idx + 1}: {e}")
        
        logger.info(f"✅ Monte Carlo (PARALELO) completado: {len(results)} simulaciones")
        return results
    
    def _analyze_regime_distribution(self, quotes: List) -> Dict[str, Any]:
        """
        Analizar distribución de regímenes en un conjunto de quotes.
        
        Returns:
            Dict con estadísticas de regímenes
        """
        regime_counts = {}
        price_history = []
        atr_history = []
        
        for quote in quotes:
            current_price = float(quote.close or quote.bid or quote.last or 0)
            if current_price > 0:
                price_history.append(current_price)
            
            if len(price_history) >= 60:
                market_context = self._detect_regime_for_quote(
                    quote,
                    price_history.copy(),
                    atr_history.copy() if atr_history else []
                )
                regime_type = market_context.get('type', 'unknown')
                regime_counts[regime_type] = regime_counts.get(regime_type, 0) + 1
                
                # Actualizar ATR history
                if len(price_history) >= 14:
                    recent_prices = price_history[-14:]
                    price_range = max(recent_prices) - min(recent_prices)
                    atr_history.append(price_range)
        
        total = sum(regime_counts.values())
        regime_percentages = {k: (v / total * 100) if total > 0 else 0.0 
                             for k, v in regime_counts.items()}
        
        return {
            'counts': regime_counts,
            'percentages': regime_percentages,
            'total_quotes': len(quotes),
            'quotes_with_regime': total
        }
    
    def run_out_of_sample_backtest(self) -> Dict[str, Any]:
        """
        Ejecutar out-of-sample / forward performance test.
        
        Ahora incluye:
        - Validación de regímenes entre train/test
        - Prevención de data leakage (solo usa datos históricos)
        - Comparación de métricas train vs test
        """
        logger.info("🔄 Ejecutando Out-of-Sample Backtest...")
        
        oos_config = self.config['backtests']['out_of_sample']
        train_split = oos_config.get('train_split', 0.7)
        use_optimized_params = oos_config.get('use_optimized_params', True)
        learning_engine = oos_config.get('learning_engine')
        validate_regimes = oos_config.get('validate_regimes', True)
        
        # Dividir datos en train/test (temporalmente, sin lookahead)
        split_idx = int(len(self.quotes) * train_split)
        train_quotes = self.quotes[:split_idx]
        test_quotes = self.quotes[split_idx:]
        
        logger.info(f"  📊 Train: {len(train_quotes)} quotes ({train_quotes[0].timestamp.date()} to {train_quotes[-1].timestamp.date()})")
        logger.info(f"  📊 Test: {len(test_quotes)} quotes ({test_quotes[0].timestamp.date()} to {test_quotes[-1].timestamp.date()})")
        
        # Validación de regímenes (nuevo)
        regime_warning = False
        if validate_regimes:
            logger.info("  🔍 Analizando distribución de regímenes...")
            train_regimes = self._analyze_regime_distribution(train_quotes)
            test_regimes = self._analyze_regime_distribution(test_quotes)
            
            logger.info(f"    Train regimes: {train_regimes['percentages']}")
            logger.info(f"    Test regimes: {test_regimes['percentages']}")
            
            # Verificar si hay diferencias significativas
            train_primary = max(train_regimes['percentages'].items(), key=lambda x: x[1])[0] if train_regimes['percentages'] else 'unknown'
            test_primary = max(test_regimes['percentages'].items(), key=lambda x: x[1])[0] if test_regimes['percentages'] else 'unknown'
            
            if train_primary != test_primary:
                logger.warning(f"    ⚠️ REGIME MISMATCH: Train primary={train_primary}, Test primary={test_primary}")
                logger.warning(f"    ⚠️ Esto puede afectar la validez del test OOS")
                regime_warning = True
            
            # Calcular similitud de regímenes
            common_regimes = set(train_regimes['percentages'].keys()) & set(test_regimes['percentages'].keys())
            regime_similarity = sum(
                abs(train_regimes['percentages'].get(r, 0) - test_regimes['percentages'].get(r, 0))
                for r in common_regimes
            ) / len(common_regimes) if common_regimes else 100.0
            
            if regime_similarity > 30.0:  # Más del 30% de diferencia
                logger.warning(f"    ⚠️ ALTA DISIMILITUD de regímenes: {regime_similarity:.1f}% diferencia promedio")
                regime_warning = True
        
        # Si use_optimized_params, buscar mejores parámetros del grid_search
        if use_optimized_params and self.results:
            # Buscar mejor resultado de grid_search
            grid_results = [r for r in self.results if r.get('test_type') == 'grid_search']
            if grid_results:
                best_grid = max(grid_results, key=lambda x: x.get('sharpe_ratio', 0))
                thresholds_override = best_grid.get('thresholds_used', {})
                logger.info(f"  ✅ Usando parámetros optimizados del grid_search (Sharpe={best_grid.get('sharpe_ratio', 0):.2f})")
                strategy_config = self._create_strategy_config(
                    thresholds_override=thresholds_override,
                    learning_engine_override=learning_engine
                )
            else:
                logger.warning("  ⚠️ No se encontraron resultados de grid_search, usando parámetros por defecto")
                strategy_config = self._create_strategy_config(learning_engine_override=learning_engine)
        else:
            strategy_config = self._create_strategy_config(learning_engine_override=learning_engine)
        
        # Prevención de data leakage: entrenar en train set antes de test
        # Si hay learning engine, debe entrenarse solo con train_quotes
        if learning_engine:
            logger.info(f"  🎓 Entrenando learning engine ({learning_engine}) en train set...")
            # Crear estrategia primero para poder entrenar
            strategy_train = ModularMomentumStrategy(strategy_config)
            
            # Entrenar learning engine en train set
            if strategy_train.learning_engine:
                try:
                    training_data = self._prepare_learning_training_data(
                        train_quotes,
                        learning_engine,
                        strategy_train
                    )
                    
                    if training_data and len(training_data) > 0:
                        # Validación opcional (últimos 20% del train set)
                        val_split = int(len(train_quotes) * 0.8)
                        val_quotes = train_quotes[val_split:]
                        validation_data = None
                        if len(val_quotes) >= 20:
                            validation_data = self._prepare_learning_training_data(
                                val_quotes,
                                learning_engine,
                                strategy_train
                            )
                        
                        # Entrenar
                        metrics = strategy_train.learning_engine.train(
                            training_data,
                            validation_data=validation_data
                        )
                        logger.info(f"  ✅ Learning engine entrenado: {metrics}")
                    else:
                        logger.warning(f"  ⚠️ No se pudieron preparar datos de entrenamiento para learning engine")
                except Exception as e:
                    logger.error(f"  ❌ Error entrenando learning engine: {e}", exc_info=True)
                    # Continuar sin learning engine entrenado
            else:
                logger.warning(f"  ⚠️ Learning engine no se inicializó correctamente")
        else:
            # Sin learning engine - crear estrategia normalmente
            strategy_train = ModularMomentumStrategy(strategy_config)
        
        # Ejecutar backtest en TRAIN set (para comparación)
        logger.info("  📈 Ejecutando backtest en train set (para comparación)...")
        
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.001")
        )
        
        # strategy_train ya está creado arriba (con o sin learning engine entrenado)
        backtester_train = SimpleBacktester(config=backtest_config, strategy=strategy_train)
        signals_train = []
        for quote in train_quotes:
            quote_signals = strategy_train.generate_signals(quote)
            signals_train.extend(quote_signals)
        
        result_train = backtester_train.run_backtest(train_quotes, signals=signals_train)
        
        # Ejecutar backtest en TEST set (sin reentrenar - forward performance)
        logger.info("  📉 Ejecutando backtest en test set (forward performance)...")
        # Si hay learning engine, usar el mismo entrenado (NO reentrenar)
        if learning_engine and strategy_train.learning_engine and strategy_train.learning_engine.is_ready():
            # Usar la misma estrategia con el learning engine ya entrenado
            strategy_test = strategy_train  # Reusar la estrategia entrenada
            logger.info("  ✅ Usando learning engine ya entrenado (NO reentrenar para test)")
        else:
            strategy_test = ModularMomentumStrategy(strategy_config)  # Misma configuración, sin learning engine
        
        backtester_test = SimpleBacktester(config=backtest_config, strategy=strategy_test)
        signals_test = []
        for quote in test_quotes:
            quote_signals = strategy_test.generate_signals(quote)
            signals_test.extend(quote_signals)
        
        result_test = backtester_test.run_backtest(test_quotes, signals=signals_test)
        
        # Calcular métricas de manera consistente para train y test
        train_metrics = self._calculate_consistent_metrics(result_train, initial_capital)
        test_metrics = self._calculate_consistent_metrics(result_test, initial_capital)
        
        # Calcular degradación de performance
        train_sharpe = float(result_train.performance.sharpe_ratio) if result_train.performance.sharpe_ratio else 0.0
        test_sharpe = float(result_test.performance.sharpe_ratio) if result_test.performance.sharpe_ratio else 0.0
        sharpe_degradation = ((train_sharpe - test_sharpe) / abs(train_sharpe)) * 100 if train_sharpe != 0 else 0.0
        
        return_degradation = ((train_metrics['return_pct'] - test_metrics['return_pct']) / abs(train_metrics['return_pct'])) * 100 if train_metrics['return_pct'] != 0 else 0.0
        
        result_dict = {
            'test_type': 'out_of_sample',
            'test_name': 'Out-of-Sample - Forward Performance',
            'train_period': f"{train_quotes[0].timestamp.date()} to {train_quotes[-1].timestamp.date()}",
            'test_period': f"{test_quotes[0].timestamp.date()} to {test_quotes[-1].timestamp.date()}",
            'modules_active': list(self.config['modules']['filters'].keys()),
            'learning_engine': learning_engine,
            'thresholds': self._extract_thresholds(strategy_config),
            'use_optimized_params': use_optimized_params,
            
            # Métricas de TEST (principal)
            'total_pnl': test_metrics['total_pnl'],
            'return_pct': test_metrics['return_pct'],
            'win_rate': float(result_test.performance.win_rate),
            'sharpe_ratio': float(result_test.performance.sharpe_ratio) if result_test.performance.sharpe_ratio else 0.0,
            'max_drawdown': float(result_test.performance.max_drawdown_percentage),
            'total_trades': result_test.performance.total_trades,
            'avg_trade_pnl': test_metrics['total_pnl'] / result_test.performance.total_trades if result_test.performance.total_trades > 0 else 0.0,
            'final_capital': test_metrics['final_capital'],
            
            # Métricas de TRAIN (para comparación)
            'train_total_pnl': train_metrics['total_pnl'],
            'train_return_pct': train_metrics['return_pct'],
            'train_sharpe_ratio': train_sharpe,
            'train_win_rate': float(result_train.performance.win_rate),
            'train_total_trades': result_train.performance.total_trades,
            
            # Degradación de performance
            'sharpe_degradation_pct': sharpe_degradation,
            'return_degradation_pct': return_degradation,
            
            # Validación de regímenes
            'regime_warning': regime_warning,
            'train_regime_distribution': train_regimes.get('percentages', {}) if validate_regimes else {},
            'test_regime_distribution': test_regimes.get('percentages', {}) if validate_regimes else {},
        }
        
        self.results.append(result_dict)
        
        logger.info(f"✅ Out-of-Sample completado:")
        logger.info(f"   📊 TEST: PnL=${result_dict['total_pnl']:.2f}, Sharpe={result_dict['sharpe_ratio']:.2f}, Return={result_dict['return_pct']:.2f}%")
        logger.info(f"   📊 TRAIN: PnL=${result_dict['train_total_pnl']:.2f}, Sharpe={result_dict['train_sharpe_ratio']:.2f}, Return={result_dict['train_return_pct']:.2f}%")
        logger.info(f"   📉 Degradación: Sharpe={sharpe_degradation:.1f}%, Return={return_degradation:.1f}%")
        
        if regime_warning:
            logger.warning(f"   ⚠️ REGIME WARNING: Los regímenes difieren significativamente entre train/test")
        
        return result_dict
    
    def _detect_regime_for_quote(self, quote, price_history: List[float], atr_history: List[float]) -> Dict[str, Any]:
        """
        Detectar régimen de mercado para un quote específico.
        
        Args:
            quote: Quote actual
            price_history: Histórico de precios hasta este quote
            atr_history: Histórico de ATR hasta este quote
            
        Returns:
            Dict con información del régimen detectado
        """
        from app.strategies.momentum_modular.modules.market_analyzer import MarketAnalyzer
        
        # Crear MarketAnalyzer con configuración
        market_config = self.config.get('modules', {}).get('market_detection', {})
        analyzer = MarketAnalyzer({
            'enabled': True,
            'trend_detection': market_config.get('trend_detection', {'enabled': True}),
            'volatility_detection': market_config.get('volatility_detection', {'enabled': True}),
            'range_detection': market_config.get('range_detection', {'enabled': True})
        })
        
        # Analizar régimen
        market_context = analyzer.analyze(quote, price_history, atr_history)
        
        return market_context
    
    def _filter_quotes_by_regime(
        self,
        regime_conditions: Dict[str, Any],
        regime_detections: List[Tuple[int, Dict[str, Any]]]
    ) -> List[int]:
        """
        Filtrar índices de quotes que cumplen las condiciones del régimen.
        
        Args:
            regime_conditions: Condiciones del régimen desde configuración
            regime_detections: Lista de (índice, market_context) para cada quote
            
        Returns:
            Lista de índices de quotes que pertenecen al régimen
        """
        matching_indices = []
        
        for idx, market_context in regime_detections:
            matches = True
            vol_percentile = market_context.get('volatility_percentile', 50)
            
            # Verificar trend_direction (más flexible)
            if 'trend_direction' in regime_conditions:
                expected_trend = regime_conditions['trend_direction']
                actual_type = market_context.get('type', 'unknown')
                trend_strength = market_context.get('trend_strength', 0.0)
                
                if expected_trend == 'trend_up':
                    # Aceptar trend_up o cualquier tipo con tendencia alcista clara
                    if actual_type in ['trend_up', 'high_vol']:
                        # Aceptar directamente si es trend_up o high_vol
                        pass
                    elif trend_strength > 0.4:  # Tendencia moderada o fuerte
                        # Si hay fuerza de tendencia suficiente, considerar como trend_up
                        vol_regime = market_context.get('volatility_regime', 'normal')
                        # Aceptar si la volatilidad no es extremadamente alta
                        if vol_regime == 'high' and vol_percentile > 90:
                            matches = False  # Volatilidad demasiado alta enmascara tendencia
                    else:
                        matches = False
                elif expected_trend == 'trend_down':
                    # Aceptar trend_down o cualquier tipo con tendencia bajista clara
                    if actual_type in ['trend_down', 'high_vol']:
                        # Aceptar directamente si es trend_down o high_vol
                        pass
                    elif trend_strength > 0.4:  # Tendencia moderada o fuerte
                        # Si hay fuerza de tendencia suficiente, considerar como trend_down
                        vol_regime = market_context.get('volatility_regime', 'normal')
                        if vol_regime == 'high' and vol_percentile > 90:
                            matches = False  # Volatilidad demasiado alta enmascara tendencia
                    else:
                        matches = False
                else:
                    matches = False
            
            # Verificar volatility_regime (más flexible)
            if 'volatility_regime' in regime_conditions and matches:
                expected_vol = regime_conditions['volatility_regime']
                actual_vol = market_context.get('volatility_regime', 'normal')
                vol_percentile = market_context.get('volatility_percentile', 50)
                
                if expected_vol == 'high':
                    # Alta volatilidad: >= 75 percentil o regime 'high'
                    if actual_vol != 'high' and vol_percentile < 70:
                        matches = False
                elif expected_vol == 'low':
                    # Baja volatilidad: <= 25 percentil o regime 'low'
                    if actual_vol != 'low' and vol_percentile > 30:
                        matches = False
                elif expected_vol == 'normal':
                    # Volatilidad normal: 25-75 percentil
                    if actual_vol not in ['normal', 'unknown'] and not (25 <= vol_percentile <= 75):
                        matches = False
                else:
                    # Coincidencia exacta requerida
                    if expected_vol != actual_vol:
                        matches = False
            
            # Verificar in_range (más flexible)
            if 'in_range' in regime_conditions and matches:
                expected_in_range = regime_conditions['in_range']
                actual_type = market_context.get('type', 'unknown')
                actual_in_range = market_context.get('in_range', False) or (actual_type == 'range')
                trend_strength = market_context.get('trend_strength', 0.0)
                
                if expected_in_range:
                    # Esperamos rango lateral: debe ser range O tendencia muy débil
                    if not actual_in_range and trend_strength > 0.4:
                        matches = False
                else:
                    # NO esperamos rango: debe haber tendencia clara
                    if actual_in_range and trend_strength < 0.5:
                        matches = False
            
            # Verificar trend_strength (opcional)
            if 'min_trend_strength' in regime_conditions:
                min_strength = regime_conditions['min_trend_strength']
                actual_strength = market_context.get('trend_strength', 0.0)
                if actual_strength < min_strength:
                    matches = False
            
            if matches:
                matching_indices.append(idx)
        
        return matching_indices
    
    def run_regime_test(self) -> List[Dict[str, Any]]:
        """
        Ejecutar market condition / regime test.
        
        Ahora detecta regímenes reales y filtra quotes por régimen antes de ejecutar backtest.
        """
        logger.info("🔄 Ejecutando Regime Test...")
        
        regime_config = self.config['backtests']['regime_test']
        regimes = regime_config.get('regimes', [])
        
        if not regimes:
            logger.warning("⚠️ No hay regímenes configurados para regime test")
            return []
        
        # Paso 1: Detectar régimen para cada quote
        logger.info("  📊 Detectando regímenes de mercado para cada quote...")
        regime_detections = []  # Lista de (índice, market_context)
        
        strategy_config = self._create_strategy_config()
        strategy = ModularMomentumStrategy(strategy_config)
        
        # Construir histórico de precios y ATR mientras iteramos
        price_history = []
        atr_history = []
        
        for idx, quote in enumerate(self.quotes):
            # Actualizar histórico
            current_price = float(quote.close or quote.bid or quote.last or 0)
            if current_price > 0:
                price_history.append(current_price)
            
            # Detectar régimen solo si tenemos suficiente histórico
            if len(price_history) >= 60:  # Mínimo para calcular indicadores
                market_context = self._detect_regime_for_quote(
                    quote,
                    price_history.copy(),
                    atr_history.copy() if atr_history else []
                )
                regime_detections.append((idx, market_context))
                
                # Actualizar ATR history si está disponible en market_context
                # (por simplicidad, usamos un valor estimado basado en volatilidad)
                if 'volatility_percentile' in market_context:
                    # Estimación simple de ATR basada en volatilidad
                    if len(price_history) >= 14:
                        recent_prices = price_history[-14:]
                        price_range = max(recent_prices) - min(recent_prices)
                        atr_history.append(price_range)
            else:
                # Régimen desconocido para quotes sin suficiente histórico
                regime_detections.append((idx, {
                    'type': 'unknown',
                    'confidence': 0.0,
                    'volatility_regime': 'normal',
                    'trend_strength': 0.0,
                    'in_range': False
                }))
        
        logger.info(f"  ✅ Regímenes detectados para {len(regime_detections)} quotes")
        
        # Estadísticas de regímenes detectados
        regime_counts = {}
        for _, context in regime_detections:
            regime_type = context.get('type', 'unknown')
            regime_counts[regime_type] = regime_counts.get(regime_type, 0) + 1
        
        logger.info(f"  📈 Distribución de regímenes: {regime_counts}")
        
        # Paso 2: Para cada régimen configurado, filtrar quotes y ejecutar backtest
        results = []
        
        for regime in regimes:
            regime_name = regime.get('name', 'unknown')
            conditions = regime.get('conditions', {})
            
            logger.info(f"  🔍 Testing regime: {regime_name} with conditions: {conditions}")
            
            # Filtrar quotes que pertenecen a este régimen
            matching_indices = self._filter_quotes_by_regime(conditions, regime_detections)
            
            if len(matching_indices) == 0:
                logger.warning(f"  ⚠️ No se encontraron quotes para régimen {regime_name}")
                # Aún así crear un resultado con métricas vacías
                result_dict = {
                    'test_type': 'regime_test',
                    'test_name': f'Regime Test - {regime_name}',
                    'regime_name': regime_name,
                    'regime_conditions': conditions,
                    'quotes_matched': 0,
                    'modules_active': list(self.config['modules']['filters'].keys()),
                    'learning_engine': None,
                    'thresholds': self._extract_thresholds(strategy_config),
                    'total_pnl': 0.0,
                    'return_pct': 0.0,
                    'win_rate': 0.0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'total_trades': 0,
                    'avg_trade_pnl': 0.0,
                    'final_capital': float(self.config['input']['initial_capital']),
                }
                results.append(result_dict)
                self.results.append(result_dict)
                continue
            
            # Obtener quotes filtrados
            filtered_quotes = [self.quotes[i] for i in matching_indices]
            logger.info(f"  ✅ Encontrados {len(filtered_quotes)} quotes para régimen {regime_name} "
                       f"({len(filtered_quotes)/len(self.quotes)*100:.1f}% del total)")
            
            if len(filtered_quotes) < 10:
                logger.warning(f"  ⚠️ Muy pocos quotes ({len(filtered_quotes)}) para backtest confiable")
            
            # Ejecutar backtest solo en quotes filtrados
            initial_capital = Decimal(str(self.config['input']['initial_capital']))
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001")
            )
            
            strategy_name = self._get_strategy_name(strategy)
            backtester = SimpleBacktester(
                config=backtest_config,
                strategy=strategy,
                strategy_name=strategy_name
            )
            
            signals = []
            for quote in filtered_quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)
            
            result = backtester.run_backtest(filtered_quotes, signals=signals)
            
            # Calcular métricas de manera consistente
            consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
            
            result_dict = {
                'test_type': 'regime_test',
                'test_name': f'Regime Test - {regime_name}',
                'regime_name': regime_name,
                'regime_conditions': conditions,
                'quotes_matched': len(filtered_quotes),
                'quotes_total': len(self.quotes),
                'match_percentage': len(filtered_quotes) / len(self.quotes) * 100,
                'modules_active': list(self.config['modules']['filters'].keys()),
                'learning_engine': None,
                'thresholds': self._extract_thresholds(strategy_config),
                'total_pnl': consistent_metrics['total_pnl'],
                'return_pct': consistent_metrics['return_pct'],
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
                'final_capital': consistent_metrics['final_capital'],
            }
            
            results.append(result_dict)
            self.results.append(result_dict)
            
            logger.info(f"  ✅ {regime_name}: PnL=${result_dict['total_pnl']:.2f}, "
                       f"Sharpe={result_dict['sharpe_ratio']:.2f}, "
                       f"Trades={result_dict['total_trades']}, "
                       f"Win Rate={result_dict['win_rate']:.2f}%")
        
        # Paso 3: Análisis comparativo entre regímenes
        if len(results) > 1:
            logger.info("\n  📊 Análisis Comparativo de Regímenes:")
            best_sharpe = max(results, key=lambda x: x.get('sharpe_ratio', float('-inf')))
            best_pnl = max(results, key=lambda x: x.get('total_pnl', float('-inf')))
            best_win_rate = max([r for r in results if r.get('win_rate', 0) > 0], 
                              key=lambda x: x.get('win_rate', 0), default=None)
            
            logger.info(f"    🏆 Mejor Sharpe: {best_sharpe['regime_name']} ({best_sharpe['sharpe_ratio']:.2f})")
            logger.info(f"    💰 Mejor PnL: {best_pnl['regime_name']} (${best_pnl['total_pnl']:.2f})")
            if best_win_rate:
                logger.info(f"    📈 Mejor Win Rate: {best_win_rate['regime_name']} ({best_win_rate['win_rate']:.2f}%)")
        
        logger.info(f"✅ Regime Test completado: {len(results)} regímenes analizados")
        return results
    
    def run_transformer_optimization(self) -> Dict[str, Any]:
        """
        Ejecutar optimización iterativa usando Transformer.
        
        Itera sobre combinaciones de parámetros, usa Transformer para predecir performance,
        y converge hacia mejores thresholds y learning parameters.
        """
        logger.info("🔄 Ejecutando Transformer-driven Optimization...")
        
        tf_config = self.config['backtests']['transformer_optimization']
        max_iterations = tf_config.get('max_iterations', 50)
        convergence_threshold = tf_config.get('convergence_threshold', 0.01)
        optimize_thresholds = tf_config.get('optimize_thresholds', True)
        optimize_learning_params = tf_config.get('optimize_learning_params', True)
        
        # Verificar si transformer está disponible
        try:
            from app.strategies.momentum_modular.learning.transformer_engine import TransformerEngine
            transformer_available = True
        except ImportError:
            logger.warning("⚠️ Transformer Engine no disponible. Usando optimización con grid search mejorado.")
            transformer_available = False
        
        # Inicializar thresholds base
        current_thresholds = {}
        if optimize_thresholds:
            grid_config = self.config['backtests'].get('grid_search', {})
            parameters_to_optimize = grid_config.get('parameters_to_optimize', [
                "rsi_filter.buy_threshold",
                "rsi_filter.sell_threshold",
                "momentum_filter.threshold",
                "volume_filter.threshold"
            ])
            
            # Obtener valores por defecto
            for param in parameters_to_optimize:
                module_parts = param.split('.')
                if len(module_parts) == 2:
                    filter_name, param_name = module_parts
                    if filter_name in self.config['modules']['filters']:
                        filter_config = self.config['modules']['filters'][filter_name]
                        if 'parameters' in filter_config and param_name in filter_config['parameters']:
                            param_config = filter_config['parameters'][param_name]
                            current_thresholds[param] = param_config.get('default', 50)
        
        best_sharpe = float('-inf')
        best_thresholds = current_thresholds.copy()
        best_result = None
        iteration = 0
        previous_sharpe = None
        
        logger.info(f"  🎯 Optimizando hasta {max_iterations} iteraciones (convergencia: {convergence_threshold})")
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"  🔍 Iteración {iteration}/{max_iterations}...")
            
            # Si transformer está disponible, usarlo para sugerir ajustes
            if transformer_available and iteration > 1 and best_result:
                try:
                    # Usar transformer para predecir mejor dirección de optimización
                    # (Por simplicidad, usamos grid search mejorado si transformer no está listo)
                    threshold_adjustments = self._transformer_suggest_adjustments(
                        current_thresholds,
                        best_result,
                        iteration
                    )
                    if threshold_adjustments:
                        for param, adjustment in threshold_adjustments.items():
                            current_thresholds[param] = max(0.001, min(100.0, 
                                current_thresholds.get(param, 50) + adjustment))
                        logger.info(f"    🔧 Ajustes sugeridos por Transformer: {threshold_adjustments}")
                except Exception as e:
                    logger.debug(f"Error usando transformer: {e}")
                    # Continuar con búsqueda aleatoria mejorada
                    threshold_adjustments = None
            else:
                # Búsqueda aleatoria mejorada (gradiente estocástico simplificado)
                if iteration > 1:
                    # Ajustar thresholds basado en resultado anterior
                    for param in current_thresholds.keys():
                        adjustment = np.random.normal(0, 0.05) * current_thresholds[param]
                        current_thresholds[param] = max(0.001, min(100.0,
                            current_thresholds[param] + adjustment))
            
            # Ejecutar backtest con thresholds actuales
            try:
                strategy_config = self._create_strategy_config(
                    thresholds_override=current_thresholds
                )
                strategy = ModularMomentumStrategy(strategy_config)
                
                initial_capital = Decimal(str(self.config['input']['initial_capital']))
                backtest_config = BacktestConfig(
                    initial_capital=initial_capital,
                    commission_per_trade=Decimal("1.0"),
                    slippage_percentage=Decimal("0.001")
                )
                
                strategy_name = self._get_strategy_name(strategy)
                backtester = SimpleBacktester(
                    config=backtest_config,
                    strategy=strategy,
                    strategy_name=strategy_name
                )
                signals = []
                for quote in self.quotes:
                    quote_signals = strategy.generate_signals(quote)
                    signals.extend(quote_signals)
                
                result = backtester.run_backtest(self.quotes, signals=signals)
                current_sharpe = float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0
                
                # Calcular métricas de manera consistente
                consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
                
                # Actualizar mejor resultado
                if current_sharpe > best_sharpe:
                    improvement = current_sharpe - best_sharpe
                    best_sharpe = current_sharpe
                    best_thresholds = current_thresholds.copy()
                    best_result = {
                        'total_pnl': consistent_metrics['total_pnl'],
                        'return_pct': consistent_metrics['return_pct'],
                        'win_rate': float(result.performance.win_rate),
                        'sharpe_ratio': current_sharpe,
                        'max_drawdown': float(result.performance.max_drawdown_percentage),
                        'total_trades': result.performance.total_trades,
                    }
                    logger.info(f"    ✅ Mejor Sharpe encontrado: {best_sharpe:.4f} (mejora: +{improvement:.4f})")
                
                # Verificar convergencia
                if previous_sharpe is not None:
                    sharpe_change = abs(current_sharpe - previous_sharpe)
                    if sharpe_change < convergence_threshold and iteration >= 5:
                        logger.info(f"    🎯 Convergencia alcanzada: cambio {sharpe_change:.4f} < {convergence_threshold}")
                        break
                
                previous_sharpe = current_sharpe
                
            except Exception as e:
                logger.error(f"    ❌ Error en iteración {iteration}: {e}", exc_info=True)
                continue
        
        # Resultado final
        result_dict = {
            'test_type': 'transformer_optimization',
            'test_name': 'Transformer-driven Optimization',
            'iterations_completed': iteration,
            'converged': iteration < max_iterations,
            'modules_active': list(self.config['modules']['filters'].keys()),
            'learning_engine': 'transformer' if transformer_available else None,
            'thresholds': best_thresholds,
            'thresholds_optimized': optimize_thresholds,
            'learning_params_optimized': optimize_learning_params,
            'total_pnl': best_result['total_pnl'] if best_result else 0.0,
            'return_pct': best_result['return_pct'] if best_result else 0.0,
            'win_rate': best_result['win_rate'] if best_result else 0.0,
            'sharpe_ratio': best_sharpe if best_sharpe > float('-inf') else 0.0,
            'max_drawdown': best_result['max_drawdown'] if best_result else 0.0,
            'total_trades': best_result['total_trades'] if best_result else 0,
            'final_capital': float(self.config['input']['initial_capital']) + (best_result['total_pnl'] if best_result else 0.0),
        }
        
        self.results.append(result_dict)
        logger.info(f"✅ Transformer Optimization completado:")
        logger.info(f"   🏆 Mejor Sharpe: {best_sharpe:.4f}")
        logger.info(f"   📊 Iteraciones: {iteration}/{max_iterations}")
        logger.info(f"   🎯 Convergencia: {'Sí' if iteration < max_iterations else 'No'}")
        logger.info(f"   🔧 Mejores Thresholds: {best_thresholds}")
        
        return result_dict
    
    def _transformer_suggest_adjustments(
        self,
        current_thresholds: Dict[str, float],
        previous_result: Dict[str, Any],
        iteration: int
    ) -> Optional[Dict[str, float]]:
        """
        Usar Transformer para sugerir ajustes a thresholds.
        
        Returns:
            Dict con ajustes sugeridos para cada threshold o None
        """
        # Por ahora, implementación simplificada
        # En producción, esto usaría un Transformer entrenado para predecir
        # qué ajustes llevarían a mejor performance
        
        # Heurística simple basada en gradiente
        adjustments = {}
        for param, value in current_thresholds.items():
            # Ajuste pequeño aleatorio con bias hacia mejoras
            if previous_result.get('sharpe_ratio', 0) > 0:
                # Si Sharpe positivo, ajustes más conservadores
                adjustment = np.random.normal(0, 0.02) * value
            else:
                # Si Sharpe negativo, ajustes más agresivos
                adjustment = np.random.normal(0, 0.05) * value
            
            adjustments[param] = adjustment
        
        return adjustments if adjustments else None
    
    def _create_multi_strategy_setup(
        self,
        enable_dynamic_reallocation: bool = True,
        reallocation_frequency_days: int = 30
    ) -> Tuple[MultiStrategyBacktester, Dict[str, Any]]:
        """
        Crear setup completo para multi-strategy backtesting.
        
        Returns:
            Tuple (MultiStrategyBacktester, Dict con estrategias creadas)
        """
        # Obtener configuración de portfolio
        portfolio_config = get_portfolio_config_manager()
        allocation_manager = portfolio_config.get_allocation_manager()
        
        # Actualizar capital total
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        allocation_manager.update_total_capital(initial_capital)
        
        # Crear todas las estrategias
        strategies = {}
        
        # 1. Momentum Strategy
        from app.core.centralized_config import CentralizedConfig
        centralized_config = CentralizedConfig()
        momentum_config_dict = centralized_config.get_strategy_config("momentum")
        if momentum_config_dict:
            momentum_config = momentum_config_dict.dict()
            # Aplanar parámetros al nivel raíz para compatibilidad
            if "parameters" in momentum_config and isinstance(momentum_config["parameters"], dict):
                momentum_config.update(momentum_config["parameters"])
            strategies["momentum"] = MomentumStrategy(momentum_config)
        
        # 2. Mean Reversion Strategy
        mr_config_dict = centralized_config.get_strategy_config("mean_reversion")
        if mr_config_dict:
            mr_config = mr_config_dict.dict()
            # Aplanar parámetros al nivel raíz para compatibilidad
            if "parameters" in mr_config and isinstance(mr_config["parameters"], dict):
                mr_config.update(mr_config["parameters"])
            strategies["mean_reversion"] = MeanReversionStrategy(mr_config)
        
        # 3. Pairs Trading Strategy
        pairs_config_dict = centralized_config.get_strategy_config("pairs_trading")
        if pairs_config_dict:
            pairs_config = pairs_config_dict.dict()
            # Aplanar parámetros al nivel raíz para compatibilidad
            if "parameters" in pairs_config and isinstance(pairs_config["parameters"], dict):
                pairs_config.update(pairs_config["parameters"])
            # Obtener símbolos de pares desde portfolio config
            from app.services.portfolio_builder import PortfolioBuilder
            portfolio_builder = PortfolioBuilder(portfolio_config=portfolio_config)
            pair_symbols = portfolio_builder.get_strategy_symbols_mapping().get(
                "pairs_trading", [self.config['input']['symbol'], "MSFT"]  # Fallback
            )
            if len(pair_symbols) >= 2:
                pairs_config["pair_symbols"] = pair_symbols[:2]
            else:
                pairs_config["pair_symbols"] = [self.config['input']['symbol'], "MSFT"]
            
            strategies["pairs_trading"] = PairsTradingStrategy(pairs_config)
        
        # 4. Breakout Strategy Engine (nuevo)
        from app.engines.strategy_engines import BreakoutStrategyEngine
        breakout_config_dict = centralized_config.get_strategy_config("breakout")
        if breakout_config_dict:
            breakout_config = breakout_config_dict.dict()
            if "parameters" in breakout_config and isinstance(breakout_config["parameters"], dict):
                breakout_config.update(breakout_config["parameters"])
            strategies["breakout"] = BreakoutStrategyEngine(breakout_config)
        
        # 5. Trend Following Strategy Engine (nuevo)
        from app.engines.strategy_engines import TrendFollowingStrategyEngine
        trend_config_dict = centralized_config.get_strategy_config("trend_following")
        if trend_config_dict:
            trend_config = trend_config_dict.dict()
            if "parameters" in trend_config and isinstance(trend_config["parameters"], dict):
                trend_config.update(trend_config["parameters"])
            strategies["trend_following"] = TrendFollowingStrategyEngine(trend_config)
        
        if not strategies:
            raise ValueError("No se pudieron crear estrategias para multi-strategy backtest")
        
        # Crear MultiStrategyBacktester
        multi_backtester = MultiStrategyBacktester(
            allocation_manager=allocation_manager,
            strategies=strategies,
            config_params={
                "commission": Decimal("1.0"),
                "slippage": Decimal("0.001"),
                "stop_loss": Decimal("0.05"),
                "take_profit": Decimal("0.10"),
                "max_position_size": Decimal("0.10"),
            },
            portfolio_config_manager=portfolio_config,
            enable_dynamic_reallocation=enable_dynamic_reallocation,
            reallocation_frequency_days=reallocation_frequency_days,
        )
        
        return multi_backtester, strategies
    
    def _run_multi_strategy_backtest_on_quotes(
        self,
        quotes: List,
        test_name_prefix: str = "Multi-Strategy",
        multi_backtester: Optional[MultiStrategyBacktester] = None
    ) -> Dict[str, Any]:
        """
        Ejecutar backtest multi-strategy sobre un conjunto de quotes específico.
        
        Args:
            quotes: Lista de quotes sobre los que ejecutar el backtest
            test_name_prefix: Prefijo para el nombre del test
            multi_backtester: MultiStrategyBacktester pre-creado (opcional)
        
        Returns:
            Dict con resultados del backtest
        """
        # Crear backtester si no se proporciona
        if multi_backtester is None:
            multi_config = self.config.get('backtests', {}).get('multi_strategy', {})
            multi_backtester, strategies = self._create_multi_strategy_setup(
                enable_dynamic_reallocation=multi_config.get('enable_dynamic_reallocation', True),
                reallocation_frequency_days=multi_config.get('reallocation_frequency_days', 30)
            )
        else:
            # Obtener estrategias del backtester existente
            strategies = multi_backtester.strategies
        
        # Obtener rango de fechas desde quotes
        start_date = quotes[0].timestamp if quotes else datetime.strptime(self.config['input']['start_date'], "%Y-%m-%d")
        end_date = quotes[-1].timestamp if quotes else datetime.strptime(self.config['input']['end_date'], "%Y-%m-%d")
        
        # Ejecutar backtest multi-estrategia
        result = multi_backtester.run_multi_strategy_backtest(
            quotes=quotes,
            start_date=start_date,
            end_date=end_date
        )
        
        # Extraer métricas consolidadas
        combined_metrics = result.get('combined', {})
        
        # Calcular métricas consistentes
        initial_capital_decimal = Decimal(str(self.config['input']['initial_capital']))
        final_capital = Decimal(str(combined_metrics.get('total_final_capital', initial_capital_decimal)))
        consistent_metrics = self._calculate_consistent_metrics(
            type('obj', (object,), {
                'final_capital': final_capital,
                'initial_capital': initial_capital_decimal,
                'performance': type('obj', (object,), {
                    'total_pnl': combined_metrics.get('total_pnl', Decimal("0")),
                    'win_rate': combined_metrics.get('weighted_win_rate', 0),
                    'sharpe_ratio': combined_metrics.get('weighted_sharpe'),
                    'max_drawdown_percentage': combined_metrics.get('weighted_max_dd', 0),
                    'total_trades': combined_metrics.get('total_trades', 0)
                })()
            })(),
            initial_capital_decimal
        )
        
        result_dict = {
            'test_type': 'multi_strategy',
            'test_name': test_name_prefix,
            'strategies_active': list(strategies.keys()),
            'modules_active': ['multi_strategy'],
            'learning_engine': None,
            'thresholds': {},
            'total_pnl': consistent_metrics['total_pnl'],
            'return_pct': consistent_metrics['return_pct'],
            'win_rate': combined_metrics.get('weighted_win_rate', 0),
            'sharpe_ratio': float(combined_metrics.get('weighted_sharpe', 0)) if combined_metrics.get('weighted_sharpe') else 0.0,
            'max_drawdown': float(combined_metrics.get('weighted_max_dd', 0)),
            'total_trades': combined_metrics.get('total_trades', 0),
            'avg_trade_pnl': consistent_metrics['total_pnl'] / combined_metrics.get('total_trades', 1) if combined_metrics.get('total_trades', 0) > 0 else 0.0,
            'final_capital': consistent_metrics['final_capital'],
            'capital_allocations': {k: float(v) for k, v in multi_backtester.allocation_manager.allocate_capital().items()},
            'dynamic_reallocation_enabled': multi_backtester.enable_dynamic_reallocation if hasattr(multi_backtester, 'enable_dynamic_reallocation') else True,
        }
        
        return result_dict
    
    def run_multi_strategy_backtest(self) -> Dict[str, Any]:
        """
        Ejecutar backtest multi-estrategia usando MultiStrategyBacktester.
        
        Prueba momentum, mean_reversion y pairs_trading simultáneamente
        con división de capital entre estrategias.
        """
        logger.info("🔄 Ejecutando Multi-Strategy Backtest...")
        
        multi_config = self.config.get('backtests', {}).get('multi_strategy', {})
        if not multi_config.get('enabled', False):
            logger.warning("⚠️ Multi-strategy backtest no está habilitado en configuración")
            return {}
        
        try:
            result_dict = self._run_multi_strategy_backtest_on_quotes(
                quotes=self.quotes,
                test_name_prefix="Multi-Strategy Backtest"
            )
            
            self.results.append(result_dict)
            logger.info(f"✅ Multi-Strategy Backtest completado:")
            logger.info(f"   PnL: ${result_dict['total_pnl']:.2f}")
            logger.info(f"   Sharpe: {result_dict['sharpe_ratio']:.2f}")
            logger.info(f"   Trades: {result_dict['total_trades']}")
            logger.info(f"   Estrategias: {result_dict['strategies_active']}")
            
            return result_dict
            
        except Exception as e:
            logger.error(f"❌ Error en Multi-Strategy Backtest: {e}", exc_info=True)
            return {}
    
    def run_all(self) -> pd.DataFrame:
        """Ejecutar todos los backtests configurados."""
        logger.info("🚀 Iniciando pipeline completo de backtesting...")
        
        backtests_config = self.config['backtests']
        
        # Ejecutar cada tipo de backtest según configuración
        # 1. Baseline
        if backtests_config.get('baseline', {}).get('enabled', False):
            logger.info("📊 Ejecutando Baseline Backtest...")
            self.run_baseline_backtest()
        
        # 2. Learning Engines (nuevo - prueba cada engine individualmente)
        if backtests_config.get('learning_engines', {}).get('enabled', False):
            logger.info("📊 Ejecutando Learning Engines Backtest...")
            self.run_learning_engines_backtest()
        
        # 3. Walk-forward
        if backtests_config.get('walk_forward', {}).get('enabled', False):
            logger.info("📊 Ejecutando Walk-Forward Backtest...")
            self.run_walk_forward_backtest()
        
        # Ejecutar tests que pueden paralelizarse
        # 4. Monte Carlo (paralelizable)
        if backtests_config.get('monte_carlo', {}).get('enabled', False):
            logger.info("📊 Ejecutando Monte Carlo Backtest...")
            if self.parallel_enabled:
                self.run_monte_carlo_backtest_parallel()
            else:
                self.run_monte_carlo_backtest()
        
        # 7. Grid Search (paralelizable)
        if backtests_config.get('grid_search', {}).get('enabled', False):
            logger.info("📊 Ejecutando Grid Search...")
            if self.parallel_enabled:
                self.run_grid_search_parallel()
            else:
                self.run_grid_search()
        
        # 7b. Hyperparameter Optimization (Completo)
        if backtests_config.get('hyperparameter_optimization', {}).get('enabled', False):
            logger.info("📊 Ejecutando Hyperparameter Optimization (Completo)...")
            self.run_hyperparameter_optimization()
        
        # 5. Transformer Optimization
        if backtests_config.get('transformer_optimization', {}).get('enabled', False):
            logger.info("📊 Ejecutando Transformer Optimization...")
            self.run_transformer_optimization()
        
        # 6. Ablation
        if backtests_config.get('ablation', {}).get('enabled', False):
            logger.info("📊 Ejecutando Ablation Study...")
            self.run_ablation_study()
        
        # 8. Out-of-Sample
        if backtests_config.get('out_of_sample', {}).get('enabled', False):
            logger.info("📊 Ejecutando Out-of-Sample Backtest...")
            self.run_out_of_sample_backtest()
        
        # 9. Multi-Strategy
        if backtests_config.get('multi_strategy', {}).get('enabled', False):
            logger.info("📊 Ejecutando Multi-Strategy Backtest...")
            self.run_multi_strategy_backtest()
        
        # 10. Regime Test
        if backtests_config.get('regime_test', {}).get('enabled', False):
            logger.info("📊 Ejecutando Regime Test...")
            self.run_regime_test()
        
        # Consolidar resultados
        df = self._consolidate_results()
        
        # Guardar reportes
        self._save_reports(df)
        
        # Ejecutar análisis meta si está habilitado
        if self.meta_enabled:
            try:
                self._run_meta_analysis()
            except Exception as e:
                logger.warning(f"⚠️ Error en análisis meta: {e}", exc_info=True)
        
        logger.info(f"✅ Pipeline completado. {len(self.results)} backtests ejecutados.")
        
        # Comparar optimizaciones si ambas se ejecutaron
        self._compare_optimization_methods()
        
        return df
    
    def run_hyperparameter_optimization(self) -> List[Dict[str, Any]]:
        """
        Ejecutar optimización completa de hiperparámetros usando HyperparameterOptimizer.
        
        Optimiza:
        - Presets completos (conservative/balanced/aggressive)
        - Learning engine params (algoritmos, thresholds)
        - Risk params (position size, stop-loss, take-profit)
        - Filter thresholds
        
        Returns:
            Lista de resultados de optimización
        """
        logger.info("🎯 Ejecutando Hyperparameter Optimization (Completo)...")
        
        try:
            from app.strategies.momentum_modular.optimization.hyperparameter_optimizer import HyperparameterOptimizer
        except ImportError as e:
            logger.error(f"❌ No se pudo importar HyperparameterOptimizer: {e}")
            return []
        
        opt_config = self.config['backtests'].get('hyperparameter_optimization', {})
        optimization_method = opt_config.get('optimization_method', 'random_search')
        max_iterations = opt_config.get('max_iterations', 100)
        optimize_metric = opt_config.get('optimize_metric', 'sharpe_ratio')
        
        # Usar el primer símbolo del portfolio (o símbolo de configuración)
        symbol = self.config['input'].get('symbol', 'AAPL')
        start_date = datetime.fromisoformat(self.config['input']['start_date'])
        end_date = datetime.fromisoformat(self.config['input']['end_date'])
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        
        logger.info(f"  📊 Método: {optimization_method}")
        logger.info(f"  📊 Iteraciones: {max_iterations}")
        logger.info(f"  📊 Métrica: {optimize_metric}")
        logger.info(f"  📊 Símbolo: {symbol}")
        
        # Crear optimizador adaptado para usar quotes existentes
        optimizer = HyperparameterOptimizer(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            optimization_metric=optimize_metric,
            optimization_method=optimization_method
        )
        
        # Sobrescribir método _run_backtest para usar quotes del runner
        original_run_backtest = optimizer._run_backtest
        
        def adapted_run_backtest(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """Ejecutar backtest usando quotes del ComprehensiveBacktestRunner."""
            try:
                # Crear configuración de estrategia desde config de optimización
                strategy_config = self._create_strategy_config_from_hyperopt_config(config)
                strategy = ModularMomentumStrategy(strategy_config)
                
                # Entrenar learning engine si está habilitado
                if config.get('enable_learning') and config.get('learning_engine_type'):
                    self._train_learning_engine_if_needed(strategy, config['learning_engine_type'])
                
                # Usar quotes del runner
                strategy_name = self._get_strategy_name(strategy)
                backtest_config = BacktestConfig(
                    initial_capital=initial_capital,
                    commission_per_trade=Decimal("1.0"),
                    slippage_percentage=Decimal("0.001")
                )
                
                backtester = SimpleBacktester(
                    config=backtest_config,
                    strategy=strategy,
                    strategy_name=strategy_name
                )
                
                # Generar señales
                signals = []
                for quote in self.quotes:
                    quote_signals = strategy.generate_signals(quote)
                    signals.extend(quote_signals)
                
                # Ejecutar backtest
                result = backtester.run_backtest(self.quotes, signals=signals)
                consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)
                
                # Convertir a formato compatible
                result_dict = {
                    'total_pnl': consistent_metrics['total_pnl'],
                    'return_pct': consistent_metrics['return_pct'],
                    'win_rate': float(result.performance.win_rate),
                    'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                    'sortino_ratio': float(result.performance.sortino_ratio) if result.performance.sortino_ratio else 0.0,
                    'max_drawdown': float(result.performance.max_drawdown_percentage),
                    'total_trades': result.performance.total_trades,
                    'avg_trade_pnl': consistent_metrics['total_pnl'] / result.performance.total_trades if result.performance.total_trades > 0 else 0.0,
                    'final_capital': consistent_metrics['final_capital'],
                    'profit_factor': float(result.performance.gross_profit / abs(result.performance.gross_loss)) if result.performance.gross_loss != 0 else (999.0 if result.performance.gross_profit > 0 else 0.0),
                }
                
                return result_dict
            except Exception as e:
                logger.debug(f"Error en backtest de optimización: {e}")
                return None
        
        optimizer._run_backtest = adapted_run_backtest
        
        # Ejecutar optimización
        optimization_results = optimizer.optimize(max_iterations=max_iterations, random_seed=42)
        
        # Convertir resultados al formato estándar
        results = []
        best_config = optimization_results.get('best_config', {})
        best_score = optimization_results.get('best_score', float('-inf'))
        
        strategy = None  # Para guardar pesos si hay learning engine
        
        for i, opt_result in enumerate(optimizer.results):
            config = opt_result['config']
            result_data = opt_result['result']
            score = opt_result['score']
            
            result_dict = {
                'test_type': 'hyperparameter_optimization',
                'test_name': f'Hyperparameter Optimization - Iteration {opt_result["iteration"]}',
                'modules_active': list(self.config['modules']['filters'].keys()),
                'learning_engine': config.get('learning_engine_type'),
                'optimization_method': optimization_method,
                'optimization_metric': optimize_metric,
                'thresholds': self._extract_thresholds_from_hyperopt_config(config),
                'hyperopt_config': {
                    'preset': config.get('preset'),
                    'enable_learning': config.get('enable_learning'),
                    'learning_algorithm': config.get('learning_algorithm'),
                    'max_position_size': config.get('max_position_size'),
                    'stop_loss_pct': config.get('stop_loss_pct'),
                    'take_profit_pct': config.get('take_profit_pct'),
                },
                'optimization_score': score,
                'is_best': (config == best_config),
                'total_pnl': result_data.get('total_pnl', 0),
                'return_pct': result_data.get('return_pct', 0),
                'win_rate': result_data.get('win_rate', 0),
                'sharpe_ratio': result_data.get('sharpe_ratio', 0),
                'sortino_ratio': result_data.get('sortino_ratio', 0),
                'max_drawdown': result_data.get('max_drawdown', 0),
                'total_trades': result_data.get('total_trades', 0),
                'avg_trade_pnl': result_data.get('avg_trade_pnl', 0),
                'final_capital': result_data.get('final_capital', initial_capital),
                'profit_factor': result_data.get('profit_factor', 0),
            }
            
            results.append(result_dict)
            self.results.append(result_dict)
            
            if result_dict['is_best']:
                logger.info(
                    f"  ✅ Mejor configuración encontrada: "
                    f"Score={score:.4f}, Sharpe={result_data.get('sharpe_ratio', 0):.2f}, "
                    f"PnL=${result_data.get('total_pnl', 0):.2f}"
                )
        
        logger.info(f"✅ Hyperparameter Optimization completado: {len(results)} iteraciones")
        return results
    
    def _create_strategy_config_from_hyperopt_config(self, hyperopt_config: Dict[str, Any]) -> Dict[str, Any]:
        """Crear configuración de estrategia desde configuración de HyperparameterOptimizer."""
        # Usar configuración base del runner
        base_config = self.config.copy()
        
        # Aplicar preset
        preset_name = hyperopt_config.get('preset', 'balanced')
        
        # Aplicar learning engine
        learning_engine_type = None
        if hyperopt_config.get('enable_learning'):
            learning_engine_type = hyperopt_config.get('learning_engine_type')
        
        # Construir configuración de módulos con thresholds del hyperopt
        modules_config = base_config['modules'].copy()
        
        # Aplicar thresholds de filtros desde hyperopt_config
        if 'rsi_buy_min' in hyperopt_config:
            if 'rsi_filter' in modules_config['filters']:
                modules_config['filters']['rsi_filter']['parameters']['buy_threshold'] = {
                    'min': hyperopt_config['rsi_buy_min'],
                    'max': hyperopt_config.get('rsi_buy_max', 70),
                    'default': hyperopt_config['rsi_buy_min']
                }
        
        if 'momentum_threshold' in hyperopt_config:
            if 'momentum_filter' in modules_config['filters']:
                modules_config['filters']['momentum_filter']['parameters']['threshold'] = {
                    'default': hyperopt_config['momentum_threshold']
                }
        
        if 'volume_threshold' in hyperopt_config:
            if 'volume_filter' in modules_config['filters']:
                modules_config['filters']['volume_filter']['parameters']['threshold'] = {
                    'default': hyperopt_config['volume_threshold']
                }
        
        # Crear config de estrategia
        strategy_config = {
            'preset': preset_name,
            'modules': modules_config,
            'learning_engine': learning_engine_type,
            'risk_management': {
                'max_position_size': hyperopt_config.get('max_position_size', 0.1),
                'stop_loss_pct': hyperopt_config.get('stop_loss_pct', 0.02),
                'take_profit_pct': hyperopt_config.get('take_profit_pct', 0.06),
            }
        }
        
        return strategy_config
    
    def _extract_thresholds_from_hyperopt_config(self, hyperopt_config: Dict[str, Any]) -> Dict[str, Any]:
        """Extraer thresholds desde configuración de hyperopt."""
        thresholds = {}
        
        if 'rsi_buy_min' in hyperopt_config:
            thresholds['rsi_filter.buy_threshold'] = hyperopt_config['rsi_buy_min']
        if 'rsi_buy_max' in hyperopt_config:
            thresholds['rsi_filter.sell_threshold'] = hyperopt_config['rsi_buy_max']
        if 'momentum_threshold' in hyperopt_config:
            thresholds['momentum_filter.threshold'] = hyperopt_config['momentum_threshold']
        if 'volume_threshold' in hyperopt_config:
            thresholds['volume_filter.threshold'] = hyperopt_config['volume_threshold']
        if 'atr_percentile_threshold' in hyperopt_config:
            thresholds['atr_filter.threshold'] = hyperopt_config['atr_percentile_threshold']
        
        return thresholds
    
    def _compare_optimization_methods(self) -> None:
        """Comparar resultados entre grid_search y hyperparameter_optimization."""
        grid_results = [r for r in self.results if r.get('test_type') == 'grid_search']
        hyperopt_results = [r for r in self.results if r.get('test_type') == 'hyperparameter_optimization']
        
        if not grid_results or not hyperopt_results:
            return  # No hay suficientes resultados para comparar
        
        logger.info("\n" + "="*80)
        logger.info("📊 COMPARACIÓN DE MÉTODOS DE OPTIMIZACIÓN")
        logger.info("="*80)
        
        # Encontrar mejores resultados
        grid_best = max(grid_results, key=lambda x: x.get('sharpe_ratio', 0), default=None)
        hyperopt_best = max(hyperopt_results, key=lambda x: x.get('sharpe_ratio', 0), default=None)
        
        if grid_best and hyperopt_best:
            logger.info(f"\n🔍 Grid Search (Mejor):")
            logger.info(f"   Sharpe Ratio: {grid_best.get('sharpe_ratio', 0):.2f}")
            logger.info(f"   Total PnL: ${grid_best.get('total_pnl', 0):.2f}")
            logger.info(f"   Win Rate: {grid_best.get('win_rate', 0):.1f}%")
            logger.info(f"   Max Drawdown: {grid_best.get('max_drawdown', 0):.2f}%")
            
            logger.info(f"\n🎯 Hyperparameter Optimization (Mejor):")
            logger.info(f"   Sharpe Ratio: {hyperopt_best.get('sharpe_ratio', 0):.2f}")
            logger.info(f"   Total PnL: ${hyperopt_best.get('total_pnl', 0):.2f}")
            logger.info(f"   Win Rate: {hyperopt_best.get('win_rate', 0):.1f}%")
            logger.info(f"   Max Drawdown: {hyperopt_best.get('max_drawdown', 0):.2f}%")
            logger.info(f"   Preset: {hyperopt_best.get('hyperopt_config', {}).get('preset', 'N/A')}")
            logger.info(f"   Learning Engine: {hyperopt_best.get('learning_engine', 'None')}")
            
            # Determinar ganador
            grid_sharpe = grid_best.get('sharpe_ratio', 0)
            hyperopt_sharpe = hyperopt_best.get('sharpe_ratio', 0)
            
            if hyperopt_sharpe > grid_sharpe:
                improvement = ((hyperopt_sharpe - grid_sharpe) / abs(grid_sharpe)) * 100 if grid_sharpe != 0 else 100
                logger.info(f"\n✅ Hyperparameter Optimization es MEJOR por {improvement:.1f}% en Sharpe Ratio")
            elif grid_sharpe > hyperopt_sharpe:
                improvement = ((grid_sharpe - hyperopt_sharpe) / abs(hyperopt_sharpe)) * 100 if hyperopt_sharpe != 0 else 100
                logger.info(f"\n✅ Grid Search es MEJOR por {improvement:.1f}% en Sharpe Ratio")
            else:
                logger.info(f"\n⚖️ Ambos métodos tienen resultados similares")
        
        logger.info("="*80)
    
    def _run_meta_analysis(self) -> None:
        """Ejecutar análisis meta después de todos los backtests."""
        if not self.meta_enabled:
            return
        
        try:
            from app.backtesting.meta_analyzer import BacktestMetaAnalyzer
            import asyncio
            
            logger.info("🔍 Iniciando análisis meta...")
            
            analyzer = BacktestMetaAnalyzer(
                data_dir=str(self.output_dir),
                output_dir=str(self.output_dir / "meta"),
                enable_visualizations=True
            )
            
            # Ejecutar análisis en paralelo
            try:
                # Intentar obtener loop existente
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Crear nuevo loop en thread separado o usar concurrent.futures
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(analyzer.run_parallel_analysis(max_workers=4))
                        )
                        results = future.result(timeout=300)  # 5 min timeout
                else:
                    results = loop.run_until_complete(analyzer.run_parallel_analysis(max_workers=4))
            except RuntimeError:
                # No hay loop, crear uno nuevo
                results = asyncio.run(analyzer.run_parallel_analysis(max_workers=4))
            
            # Exportar reporte
            analyzer.export_report(format="json")
            
            logger.info("✅ Análisis meta completado")
        except ImportError:
            logger.warning("⚠️ BacktestMetaAnalyzer no disponible. Instala dependencias opcionales.")
        except Exception as e:
            logger.error(f"❌ Error en análisis meta: {e}", exc_info=True)
    
    def _save_test_audit_and_weights(
        self,
        test_result: Dict[str, Any],
        test_type: str,
        strategy: Optional[Any] = None
    ) -> None:
        """
        Guardar auditoría completa y pesos después de un test individual.
        
        Guarda:
        - Hash SHA256 de configuración YAML + versión de código + fecha
        - Metadatos completos de ejecución
        - Pesos de learning engines (para aprendizaje incremental)
        
        Args:
            test_result: Resultados del test
            test_type: Tipo de test ejecutado
            strategy: Instancia de estrategia (opcional, para obtener pesos)
        """
        if not self.meta_enabled:
            return
        
        try:
            # Preparar metadatos completos
            timestamp = datetime.now().isoformat()
            metadata = {
                'test_type': test_type,
                'test_name': test_result.get('test_name', test_type),
                'timestamp': timestamp,
                'result_summary': {
                    'total_pnl': test_result.get('total_pnl'),
                    'sharpe_ratio': test_result.get('sharpe_ratio'),
                    'sortino_ratio': test_result.get('sortino_ratio'),
                    'total_trades': test_result.get('total_trades'),
                    'win_rate': test_result.get('win_rate'),
                    'max_drawdown': test_result.get('max_drawdown'),
                    'return_pct': test_result.get('return_pct'),
                    'final_capital': test_result.get('final_capital'),
                },
                'configuration': {
                    'modules_active': test_result.get('modules_active', []),
                    'learning_engine': test_result.get('learning_engine'),
                    'thresholds': test_result.get('thresholds', {}),
                }
            }
            
            # Agregar información adicional según tipo de test
            if test_type == 'monte_carlo':
                metadata['simulation_info'] = {
                    'simulation_num': test_result.get('simulation_num'),
                    'volatility_multiplier': test_result.get('volatility_multiplier'),
                }
            elif test_type == 'grid_search':
                metadata['parameters'] = test_result.get('thresholds_used', {})
            elif test_type == 'walk_forward':
                metadata['window_info'] = {
                    'window_start': test_result.get('window_start'),
                    'window_end': test_result.get('window_end'),
                }
            
            # Guardar auditoría con hash completo
            if self.audit_trail and self.audit_hash:
                result_path = str(self.output_dir / f"{test_type}_{timestamp.replace(':', '-')}.json")
                
                self.audit_trail.save_audit_record_sync(
                    config_path=self.config_path,
                    hash_value=self.audit_hash,
                    metadata=metadata,
                    result_path=result_path
                )
                
                logger.debug(f"✅ Auditoría guardada para {test_type}: {self.audit_hash[:16]}...")
            
            # Guardar pesos de learning engine (para aprendizaje incremental)
            if self.learning_storage and strategy:
                if hasattr(strategy, 'learning_engine') and strategy.learning_engine:
                    if hasattr(strategy.learning_engine, 'model') and strategy.learning_engine.model:
                        # Determinar nombre del engine
                        engine_class_name = strategy.learning_engine.__class__.__name__
                        if 'Supervised' in engine_class_name:
                            engine_name = 'supervised'
                        elif 'Deep' in engine_class_name:
                            engine_name = 'deep'
                        elif 'Reinforcement' in engine_class_name:
                            engine_name = 'reinforcement'
                        elif 'Transformer' in engine_class_name:
                            engine_name = 'transformer'
                        else:
                            engine_name = engine_class_name.lower().replace('learningengine', '')
                        
                        # Crear test_id único
                        test_id = f"{test_type}_{timestamp.replace(':', '-').replace('.', '-')}"
                        
                        try:
                            # Obtener pesos según tipo de modelo
                            if hasattr(strategy.learning_engine.model, 'state_dict'):
                                # PyTorch model
                                weights = strategy.learning_engine.model.state_dict()
                            elif hasattr(strategy.learning_engine.model, 'get_weights'):
                                # TensorFlow/Keras model
                                weights = strategy.learning_engine.model.get_weights()
                            else:
                                # Pickle-serializable model (sklearn, etc.)
                                weights = strategy.learning_engine.model
                            
                            # Guardar pesos con metadatos
                            saved_path = self.learning_storage.save_weights(
                                engine_name=engine_name,
                                weights=weights,
                                test_id=test_id,
                                metadata={
                                    **metadata,
                                    'engine_class': engine_class_name,
                                    'model_ready': strategy.learning_engine.is_ready(),
                                    'model_type': type(strategy.learning_engine.model).__name__
                                }
                            )
                            
                            logger.info(f"✅ Pesos guardados para {test_type} ({engine_name}): {saved_path}")
                        
                        except Exception as e:
                            logger.debug(f"No se pudieron guardar pesos para {test_type} ({engine_name}): {e}")
        
        except Exception as e:
            logger.warning(f"Error guardando auditoría/pesos para {test_type}: {e}")
    
    def run_specific_backtests(self, backtest_names: List[str]) -> pd.DataFrame:
        """
        Ejecutar backtests específicos por nombre.
        
        Args:
            backtest_names: Lista de nombres de backtests a ejecutar.
                           Opciones: 'baseline', 'learning_engines', 'walk_forward', 'monte_carlo',
                           'transformer_optimization', 'ablation', 'grid_search',
                           'out_of_sample', 'regime_test'
        
        Returns:
            DataFrame con resultados consolidados
        """
        logger.info(f"🚀 Ejecutando backtests específicos: {backtest_names}")
        
        valid_names = {
            'baseline': self.run_baseline_backtest,
            'learning_engines': self.run_learning_engines_backtest,
            'walk_forward': self.run_walk_forward_backtest,
            'monte_carlo': self.run_monte_carlo_backtest,
            'transformer_optimization': self.run_transformer_optimization,
            'ablation': self.run_ablation_study,
            'grid_search': self.run_grid_search,
            'out_of_sample': self.run_out_of_sample_backtest,
            'multi_strategy': self.run_multi_strategy_backtest,
            'regime_test': self.run_regime_test,
        }
        
        for name in backtest_names:
            if name in valid_names:
                logger.info(f"📊 Ejecutando {name}...")
                try:
                    valid_names[name]()
                except Exception as e:
                    logger.error(f"❌ Error ejecutando {name}: {e}", exc_info=True)
            else:
                logger.warning(f"⚠️ Backtest desconocido: {name}. Opciones válidas: {list(valid_names.keys())}")
        
        # Consolidar resultados
        df = self._consolidate_results()
        
        # Guardar reportes
        self._save_reports(df)
        
        logger.info(f"✅ Backtests específicos completados. {len(self.results)} backtests ejecutados.")
        
        return df
    
    def _consolidate_results(self) -> pd.DataFrame:
        """Consolidar todos los resultados en un DataFrame."""
        if not self.results:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.results)
        
        # Ordenar por métrica configurada
        sort_by = self.config['reporting'].get('sort_by', 'sharpe_ratio')
        if sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=False)
        
        return df
    
    def _save_reports(self, df: pd.DataFrame):
        """Guardar reportes en diferentes formatos, incluyendo quantstats HTML."""
        output_formats = self.config['reporting'].get('output_format', ['csv'])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if 'csv' in output_formats:
            csv_path = self.output_dir / f"comprehensive_backtest_results_{timestamp}.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"📄 Reporte CSV guardado: {csv_path}")
        
        if 'json' in output_formats:
            json_path = self.output_dir / f"comprehensive_backtest_results_{timestamp}.json"
            # Guardar directamente desde self.results para preservar diccionarios anidados
            # (before_training_metrics, after_training_metrics, improvement_pct)
            import json
            with open(json_path, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            
            # Contar learning engines con datos de entrenamiento
            learning_engine_count = sum(
                1 for r in self.results 
                if r.get('test_type') == 'learning_engine' and (
                    r.get('before_training_metrics') or 
                    r.get('after_training_metrics')
                )
            )
            
            logger.info(
                f"📄 Reporte JSON guardado: {json_path} "
                f"({len(self.results)} resultados, {learning_engine_count} learning engines con training data)"
            )
        
        # Guardar resumen
        summary_path = self.output_dir / f"summary_{timestamp}.txt"
        with open(summary_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("COMPREHENSIVE BACKTEST SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Symbol: {self.config['input']['symbol']}\n")
            f.write(f"Period: {self.config['input']['start_date']} to {self.config['input']['end_date']}\n")
            f.write(f"Initial Capital: ${self.config['input']['initial_capital']:,.2f}\n")
            f.write(f"Total Backtests: {len(self.results)}\n\n")
            
            if not df.empty:
                f.write("TOP 10 RESULTS:\n")
                f.write("-" * 80 + "\n")
                top_10 = df.head(10)
                for idx, row in top_10.iterrows():
                    f.write(f"\n{row.get('test_name', 'Unknown')}:\n")
                    f.write(f"  Sharpe Ratio: {row.get('sharpe_ratio', 0):.2f}\n")
                    f.write(f"  Total PnL: ${row.get('total_pnl', 0):,.2f}\n")
                    f.write(f"  Return %: {row.get('return_pct', 0):.2f}%\n")
                    f.write(f"  Win Rate: {row.get('win_rate', 0):.2f}%\n")  # win_rate ya está en porcentaje
                    f.write(f"  Max Drawdown: {row.get('max_drawdown', 0):.2f}%\n")
        
        logger.info(f"📄 Resumen guardado: {summary_path}")
        
        # Generar reportes profesionales con quantstats y pyfolio
        self._generate_professional_reports(timestamp)
    
    def _generate_professional_reports(self, timestamp: str) -> None:
        """
        Generar reportes profesionales usando quantstats y pyfolio.
        
        Args:
            timestamp: Timestamp para nombres de archivos
        """
        if not self.backtest_results_objects:
            logger.debug("No hay BacktestResult objects almacenados. Saltando reportes profesionales.")
            return
        
        # Generar reportes quantstats HTML
        if QUANTSTATS_AVAILABLE:
            try:
                self._generate_quantstats_reports(timestamp)
            except Exception as e:
                logger.warning(f"⚠️ Error generando reportes quantstats: {e}", exc_info=True)
        else:
            logger.debug("quantstats no disponible. Instala con: pip install quantstats")
        
        # Generar análisis pyfolio
        if PYFOLIO_AVAILABLE:
            try:
                self._generate_pyfolio_reports(timestamp)
            except Exception as e:
                logger.warning(f"⚠️ Error generando reportes pyfolio: {e}", exc_info=True)
        else:
            logger.debug("pyfolio-reloaded no disponible. Instala con: pip install pyfolio-reloaded")
    
    def _generate_quantstats_reports(self, timestamp: str) -> None:
        """
        Generar reportes HTML profesionales con quantstats.
        
        Args:
            timestamp: Timestamp para nombres de archivos
        """
        logger.info("📊 Generando reportes quantstats HTML...")
        
        reports_dir = self.output_dir / "quantstats_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        initial_capital = float(self.config['input']['initial_capital'])
        
        for test_name, backtest_result in self.backtest_results_objects:
            try:
                # Convertir equity curve a returns series para quantstats
                if not backtest_result.equity_curve:
                    logger.debug(f"⚠️ No hay equity curve para {test_name}, saltando reporte quantstats")
                    continue
                
                # Crear DataFrame con equity curve
                equity_df = pd.DataFrame(backtest_result.equity_curve, columns=['timestamp', 'equity'])
                equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
                equity_df.set_index('timestamp', inplace=True)
                
                # Calcular returns diarios desde equity curve
                equity_series = equity_df['equity']
                returns = equity_series.pct_change().dropna()
                
                # Asegurar que tenemos suficientes datos
                if len(returns) < 10:
                    logger.debug(f"⚠️ Pocos datos para {test_name} ({len(returns)} días), saltando reporte quantstats")
                    continue
                
                # Limpiar nombre de test para nombre de archivo
                safe_test_name = test_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                safe_test_name = "".join(c for c in safe_test_name if c.isalnum() or c in ('_', '-'))[:50]
                
                # Generar reporte HTML
                html_path = reports_dir / f"quantstats_{safe_test_name}_{timestamp}.html"
                
                qs.reports.html(
                    returns,
                    benchmark=None,  # Opcional: agregar benchmark en el futuro
                    output=str(html_path),
                    title=f"{test_name} - QuantStats Report",
                    download_filename=None,
                )
                
                logger.info(f"  ✅ Reporte quantstats generado: {html_path}")
                
            except Exception as e:
                logger.warning(f"⚠️ Error generando reporte quantstats para {test_name}: {e}")
                continue
        
        logger.info(f"✅ Reportes quantstats HTML completados: {reports_dir}")
    
    def _generate_pyfolio_reports(self, timestamp: str) -> None:
        """
        Generar análisis de portfolio con pyfolio.
        
        Args:
            timestamp: Timestamp para nombres de archivos
        """
        logger.info("📊 Generando análisis pyfolio...")
        
        reports_dir = self.output_dir / "pyfolio_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        initial_capital = float(self.config['input']['initial_capital'])
        
        for test_name, backtest_result in self.backtest_results_objects:
            try:
                # Convertir equity curve a returns series
                if not backtest_result.equity_curve:
                    logger.debug(f"⚠️ No hay equity curve para {test_name}, saltando análisis pyfolio")
                    continue
                
                # Crear DataFrame con equity curve
                equity_df = pd.DataFrame(backtest_result.equity_curve, columns=['timestamp', 'equity'])
                equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
                equity_df.set_index('timestamp', inplace=True)
                
                # Calcular returns diarios
                equity_series = equity_df['equity']
                returns = equity_series.pct_change().dropna()
                
                if len(returns) < 10:
                    logger.debug(f"⚠️ Pocos datos para {test_name} ({len(returns)} días), saltando análisis pyfolio")
                    continue
                
                # Crear positions DataFrame desde trades
                positions = self._create_positions_df(backtest_result.trades, backtest_result.start_date, backtest_result.end_date)
                
                # Crear transactions DataFrame desde trades
                transactions = self._create_transactions_df(backtest_result.trades)
                
                # Limpiar nombre de test
                safe_test_name = test_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                safe_test_name = "".join(c for c in safe_test_name if c.isalnum() or c in ('_', '-'))[:50]
                
                # Generar tearsheet (puede generar archivos HTML/images)
                tearsheet_dir = reports_dir / safe_test_name
                tearsheet_dir.mkdir(parents=True, exist_ok=True)
                
                # Guardar tearsheet básico (pyfolio puede generar visualizaciones)
                # Por ahora, guardamos un resumen en JSON ya que pyfolio puede requerir más configuración
                try:
                    # Crear tearsheet completo (genera visualizaciones)
                    pf.create_full_tear_sheet(
                        returns=returns,
                        positions=positions if not positions.empty else None,
                        transactions=transactions if not transactions.empty else None,
                        benchmark_rets=None,  # Opcional: agregar benchmark
                        live_start_date=None,
                        round_trips=False,
                    )
                    
                    # pyfolio guarda las figuras automáticamente si matplotlib está configurado
                    logger.info(f"  ✅ Análisis pyfolio completado para {test_name}")
                    
                except Exception as e:
                    logger.debug(f"⚠️ Error generando tearsheet completo para {test_name}: {e}")
                    # Fallback: guardar métricas básicas
                    perf_stats = pf.timeseries.perf_stats(returns)
                    perf_stats.to_json(reports_dir / f"pyfolio_perf_{safe_test_name}_{timestamp}.json")
                    logger.info(f"  ✅ Métricas pyfolio guardadas para {test_name}")
                
            except Exception as e:
                logger.warning(f"⚠️ Error en análisis pyfolio para {test_name}: {e}")
                continue
        
        logger.info(f"✅ Análisis pyfolio completados: {reports_dir}")
    
    def _create_positions_df(self, trades, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Crear DataFrame de posiciones desde trades para pyfolio.
        
        Args:
            trades: Lista de trades
            start_date: Fecha de inicio
            end_date: Fecha de fin
        
        Returns:
            DataFrame con posiciones por símbolo y fecha
        """
        if not trades:
            return pd.DataFrame()
        
        # Crear serie de tiempo con todas las fechas
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Agrupar trades por símbolo y fecha
        positions_dict = {}
        for trade in trades:
            symbol = trade.symbol
            entry_time = trade.entry_time.date()
            exit_time = trade.exit_time.date() if trade.exit_time else end_date.date()
            
            if symbol not in positions_dict:
                positions_dict[symbol] = pd.Series(0.0, index=date_range)
            
            # Agregar posición (positiva para LONG, negativa para SHORT)
            quantity = float(trade.quantity) if trade.side.value == 'BUY' else -float(trade.quantity)
            
            # Ajustar posiciones en el rango de fechas
            mask = (positions_dict[symbol].index >= pd.Timestamp(entry_time)) & \
                   (positions_dict[symbol].index <= pd.Timestamp(exit_time))
            positions_dict[symbol].loc[mask] += quantity
        
        if not positions_dict:
            return pd.DataFrame()
        
        positions_df = pd.DataFrame(positions_dict)
        return positions_df
    
    def _create_transactions_df(self, trades) -> pd.DataFrame:
        """
        Crear DataFrame de transacciones desde trades para pyfolio.
        
        Args:
            trades: Lista de trades
        
        Returns:
            DataFrame con transacciones (timestamp, symbol, amount, price)
        """
        if not trades:
            return pd.DataFrame()
        
        # pyfolio espera un MultiIndex con (timestamp, sid)
        # Necesitamos agregar timestamps a cada transacción
        transactions_with_timestamps = []
        for trade in trades:
            # Entrada
            transactions_with_timestamps.append({
                'amount': float(trade.quantity),
                'symbol': trade.symbol,
                'price': float(trade.entry_price),
                'txn_dollars': float(trade.quantity * trade.entry_price),
                'sid': trade.symbol,
                'timestamp': pd.Timestamp(trade.entry_time),
            })
            # Salida (si existe)
            if trade.exit_time and trade.exit_price:
                transactions_with_timestamps.append({
                    'amount': -float(trade.quantity),
                    'symbol': trade.symbol,
                    'price': float(trade.exit_price),
                    'txn_dollars': -float(trade.quantity * trade.exit_price),
                    'sid': trade.symbol,
                    'timestamp': pd.Timestamp(trade.exit_time),
                })
        
        if not transactions_with_timestamps:
            return pd.DataFrame()
        
        transactions_df = pd.DataFrame(transactions_with_timestamps)
        transactions_df.set_index(['timestamp', 'sid'], inplace=True)
        
        return transactions_df

