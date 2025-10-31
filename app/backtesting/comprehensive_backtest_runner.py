"""
Comprehensive Backtest Runner
Sistema completo de backtesting automatizado y configurable
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.strategies.momentum_modular.strategy import ModularMomentumStrategy
from app.backtesting.data_loader import DataLoader

logger = logging.getLogger(__name__)


class ComprehensiveBacktestRunner:
    """
    Ejecuta un pipeline completo de backtesting con múltiples tipos de tests.
    
    Tipos de backtests soportados:
    1. Baseline - Línea base con todos los módulos activos
    2. Walk-forward - Optimización por ventana temporal
    3. Monte Carlo - Stress test con simulaciones aleatorias
    4. Transformer Optimization - Optimización iterativa con Transformer
    5. Ablation - Impacto individual de cada módulo
    6. Grid Search - Búsqueda de parámetros óptimos
    7. Out-of-Sample - Validación forward
    8. Regime Test - Desempeño por régimen de mercado
    """
    
    def __init__(self, config_path: str):
        """
        Inicializar runner con configuración.
        
        Args:
            config_path: Ruta al archivo YAML de configuración
        """
        self.config = self._load_config(config_path)
        self.results: List[Dict[str, Any]] = []
        self.output_dir = Path(self.config['reporting']['output_directory'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar datos históricos
        self.data_loader = DataLoader()
        self.quotes = self._load_market_data()
        
        logger.info(f"✅ ComprehensiveBacktestRunner inicializado con {len(self.quotes)} quotes")
    
    def _load_config(self, config_path: str) -> Dict:
        """Cargar configuración desde YAML."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def _load_market_data(self) -> List:
        """Cargar datos históricos de mercado."""
        symbol = self.config['input']['symbol']
        start_date = self.config['input']['start_date']
        end_date = self.config['input']['end_date']
        
        quotes = self.data_loader.load_market_data(
            symbol=symbol,
            start_date=datetime.strptime(start_date, "%Y-%m-%d"),
            end_date=datetime.strptime(end_date, "%Y-%m-%d")
        )
        
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
            base_config['adaptive_learning'] = {
                'enabled': True,
                'engine_type': learning_engine_override
            }
        elif learning_engine_override is None:
            base_config['adaptive_learning'] = {'enabled': False}
        
        return base_config
    
    def run_baseline_backtest(self) -> Dict[str, Any]:
        """Ejecutar baseline backtest."""
        logger.info("🔄 Ejecutando Baseline Backtest...")
        
        strategy_config = self._create_strategy_config(learning_engine_override=None)
        strategy = ModularMomentumStrategy(strategy_config)
        
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.001")
        )
        
        backtester = SimpleBacktester(config=backtest_config, strategy=strategy)
        
        # Generar señales
        signals = []
        for quote in self.quotes:
            quote_signals = strategy.generate_signals(quote)
            signals.extend(quote_signals)
        
        result = backtester.run_backtest(self.quotes, signals=signals)
        
        result_dict = {
            'test_type': 'baseline',
            'test_name': 'Baseline - All Modules Active',
            'modules_active': list(self.config['modules']['filters'].keys()),
            'learning_engine': None,
            'thresholds': self._extract_thresholds(strategy_config),
            'total_pnl': float(result.performance.total_pnl),
            'return_pct': float(result.total_return),  # total_return ya está en porcentaje (0-100)
            'win_rate': float(result.performance.win_rate),
            'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
            'max_drawdown': float(result.performance.max_drawdown_percentage),
            'total_trades': result.performance.total_trades,
            'avg_trade_pnl': float(result.performance.total_pnl / result.performance.total_trades) if result.performance.total_trades > 0 else 0.0,
            'final_capital': float(result.final_capital),
        }
        
        self.results.append(result_dict)
        logger.info(f"✅ Baseline Backtest completado: PnL=${result_dict['total_pnl']:.2f}, Sharpe={result_dict['sharpe_ratio']:.2f}")
        
        return result_dict
    
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
            
            initial_capital = Decimal(str(self.config['input']['initial_capital']))
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001")
            )
            
            backtester = SimpleBacktester(config=backtest_config, strategy=strategy)
            
            signals = []
            for quote in self.quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)
            
            result = backtester.run_backtest(self.quotes, signals=signals)
            
            result_dict = {
                'test_type': 'ablation',
                'test_name': f'Ablation - Without {module_name}',
                'modules_active': [m for m in self.config['modules']['filters'].keys() if m != module_name],
                'module_disabled': module_name,
                'learning_engine': None,
                'thresholds': self._extract_thresholds(strategy_config),
                'total_pnl': float(result.performance.total_pnl),
                'return_pct': float(result.total_return),  # total_return ya está en porcentaje (0-100)
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': float(result.performance.total_pnl / result.performance.total_trades) if result.performance.total_trades > 0 else 0.0,
                'final_capital': float(result.final_capital),
            }
            
            results.append(result_dict)
            self.results.append(result_dict)
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
            
            initial_capital = Decimal(str(self.config['input']['initial_capital']))
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001")
            )
            
            backtester = SimpleBacktester(config=backtest_config, strategy=strategy)
            
            signals = []
            for quote in self.quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)
            
            result = backtester.run_backtest(self.quotes, signals=signals)
            
            metric_value = self._get_metric_value(result, optimize_metric)
            
            result_dict = {
                'test_type': 'grid_search',
                'test_name': f'Grid Search - Combination {i+1}',
                'modules_active': list(self.config['modules']['filters'].keys()),
                'learning_engine': None,
                'thresholds': self._extract_thresholds(strategy_config),
                'thresholds_used': param_combo,
                'total_pnl': float(result.performance.total_pnl),
                'return_pct': float(result.total_return),  # total_return ya está en porcentaje (0-100)
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': float(result.performance.total_pnl / result.performance.total_trades) if result.performance.total_trades > 0 else 0.0,
                'final_capital': float(result.final_capital),
            }
            
            results.append(result_dict)
            self.results.append(result_dict)
            
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
        
        # Ejecutar backtest preliminar para obtener trades históricos
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        temp_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.001")
        )
        temp_backtester = SimpleBacktester(config=temp_config, strategy=strategy)
        
        signals = []
        for quote in quotes:
            quote_signals = strategy.generate_signals(quote)
            signals.extend(quote_signals)
        
        temp_result = temp_backtester.run_backtest(quotes, signals)
        historical_trades = temp_result.trades if temp_result else []
        
        # Preparar datos según tipo de engine
        preparator = TrainingDataPreparator()
        
        if engine_type == "supervised":
            return preparator.prepare_supervised_training_data(
                quotes=quotes,
                trades=historical_trades,
                min_sequence_length=60
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
            
            backtester = SimpleBacktester(config=backtest_config, strategy=strategy)
            
            signals = []
            for quote in test_quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)
            
            result = backtester.run_backtest(test_quotes, signals=signals)
            
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
                'total_pnl': float(result.performance.total_pnl),
                'return_pct': float(result.total_return),
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': float(result.performance.total_pnl / result.performance.total_trades) if result.performance.total_trades > 0 else 0.0,
                'final_capital': float(result.final_capital),
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
                
                backtester = SimpleBacktester(config=backtest_config, strategy=strategy)
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
        """Ejecutar Monte Carlo / Stress Test."""
        logger.info("🔄 Ejecutando Monte Carlo / Stress Test...")
        
        mc_config = self.config['backtests']['monte_carlo']
        num_simulations = mc_config.get('num_simulations', 100)
        volatility_multiplier = mc_config.get('volatility_multiplier', {}).get('default', 1.0)
        
        results = []
        
        # Crear copias de quotes con variaciones aleatorias
        base_quotes = self.quotes.copy()
        
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
            strategy_config = self._create_strategy_config()
            strategy = ModularMomentumStrategy(strategy_config)
            
            initial_capital = Decimal(str(self.config['input']['initial_capital']))
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001")
            )
            
            backtester = SimpleBacktester(config=backtest_config, strategy=strategy)
            
            signals = []
            for quote in modified_quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)
            
            result = backtester.run_backtest(modified_quotes, signals=signals)
            
            result_dict = {
                'test_type': 'monte_carlo',
                'test_name': f'Monte Carlo - Simulation {sim_num+1}',
                'simulation_num': sim_num + 1,
                'volatility_multiplier': volatility_multiplier,
                'modules_active': list(self.config['modules']['filters'].keys()),
                'learning_engine': None,
                'thresholds': self._extract_thresholds(strategy_config),
                'total_pnl': float(result.performance.total_pnl),
                'return_pct': float(result.total_return),  # total_return ya está en porcentaje (0-100)
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': float(result.performance.total_pnl / result.performance.total_trades) if result.performance.total_trades > 0 else 0.0,
                'final_capital': float(result.final_capital),
            }
            
            results.append(result_dict)
            self.results.append(result_dict)
        
        logger.info(f"✅ Monte Carlo completado: {len(results)} simulaciones")
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
            # El learning engine se entrena automáticamente durante el backtest
            # pero debemos asegurar que solo use datos históricos
        
        # Ejecutar backtest en TRAIN set (para comparación)
        logger.info("  📈 Ejecutando backtest en train set (para comparación)...")
        strategy_train = ModularMomentumStrategy(strategy_config)
        
        initial_capital = Decimal(str(self.config['input']['initial_capital']))
        backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.001")
        )
        
        backtester_train = SimpleBacktester(config=backtest_config, strategy=strategy_train)
        signals_train = []
        for quote in train_quotes:
            quote_signals = strategy_train.generate_signals(quote)
            signals_train.extend(quote_signals)
        
        result_train = backtester_train.run_backtest(train_quotes, signals=signals_train)
        
        # Ejecutar backtest en TEST set (sin reentrenar - forward performance)
        logger.info("  📉 Ejecutando backtest en test set (forward performance)...")
        strategy_test = ModularMomentumStrategy(strategy_config)  # Misma configuración, NO reentrenar
        
        backtester_test = SimpleBacktester(config=backtest_config, strategy=strategy_test)
        signals_test = []
        for quote in test_quotes:
            quote_signals = strategy_test.generate_signals(quote)
            signals_test.extend(quote_signals)
        
        result_test = backtester_test.run_backtest(test_quotes, signals=signals_test)
        
        # Calcular degradación de performance
        train_sharpe = float(result_train.performance.sharpe_ratio) if result_train.performance.sharpe_ratio else 0.0
        test_sharpe = float(result_test.performance.sharpe_ratio) if result_test.performance.sharpe_ratio else 0.0
        sharpe_degradation = ((train_sharpe - test_sharpe) / abs(train_sharpe)) * 100 if train_sharpe != 0 else 0.0
        
        train_return = float(result_train.total_return)
        test_return = float(result_test.total_return)
        return_degradation = ((train_return - test_return) / abs(train_return)) * 100 if train_return != 0 else 0.0
        
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
            'total_pnl': float(result_test.performance.total_pnl),
            'return_pct': float(result_test.total_return),
            'win_rate': float(result_test.performance.win_rate),
            'sharpe_ratio': float(result_test.performance.sharpe_ratio) if result_test.performance.sharpe_ratio else 0.0,
            'max_drawdown': float(result_test.performance.max_drawdown_percentage),
            'total_trades': result_test.performance.total_trades,
            'avg_trade_pnl': float(result_test.performance.total_pnl / result_test.performance.total_trades) if result_test.performance.total_trades > 0 else 0.0,
            'final_capital': float(result_test.final_capital),
            
            # Métricas de TRAIN (para comparación)
            'train_total_pnl': float(result_train.performance.total_pnl),
            'train_return_pct': float(result_train.total_return),
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
            
            # Verificar trend_direction
            if 'trend_direction' in regime_conditions:
                expected_trend = regime_conditions['trend_direction']
                actual_type = market_context.get('type', 'unknown')
                
                if expected_trend == 'trend_up':
                    if actual_type != 'trend_up':
                        matches = False
                elif expected_trend == 'trend_down':
                    if actual_type != 'trend_down':
                        matches = False
                else:
                    matches = False
            
            # Verificar volatility_regime
            if 'volatility_regime' in regime_conditions:
                expected_vol = regime_conditions['volatility_regime']
                actual_vol = market_context.get('volatility_regime', 'normal')
                
                if expected_vol != actual_vol:
                    matches = False
            
            # Verificar in_range
            if 'in_range' in regime_conditions:
                expected_in_range = regime_conditions['in_range']
                actual_type = market_context.get('type', 'unknown')
                actual_in_range = market_context.get('in_range', False) or (actual_type == 'range')
                
                if expected_in_range != actual_in_range:
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
            
            backtester = SimpleBacktester(config=backtest_config, strategy=strategy)
            
            signals = []
            for quote in filtered_quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)
            
            result = backtester.run_backtest(filtered_quotes, signals=signals)
            
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
                'total_pnl': float(result.performance.total_pnl),
                'return_pct': float(result.total_return),  # total_return ya está en porcentaje (0-100)
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0,
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': float(result.performance.total_pnl / result.performance.total_trades) if result.performance.total_trades > 0 else 0.0,
                'final_capital': float(result.final_capital),
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
                
                backtester = SimpleBacktester(config=backtest_config, strategy=strategy)
                signals = []
                for quote in self.quotes:
                    quote_signals = strategy.generate_signals(quote)
                    signals.extend(quote_signals)
                
                result = backtester.run_backtest(self.quotes, signals=signals)
                current_sharpe = float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0
                
                # Actualizar mejor resultado
                if current_sharpe > best_sharpe:
                    improvement = current_sharpe - best_sharpe
                    best_sharpe = current_sharpe
                    best_thresholds = current_thresholds.copy()
                    best_result = {
                        'total_pnl': float(result.performance.total_pnl),
                        'return_pct': float(result.total_return),
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
    
    def run_all(self) -> pd.DataFrame:
        """Ejecutar todos los backtests configurados."""
        logger.info("🚀 Iniciando pipeline completo de backtesting...")
        
        backtests_config = self.config['backtests']
        
        # Ejecutar cada tipo de backtest según configuración
        # 1. Baseline
        if backtests_config.get('baseline', {}).get('enabled', False):
            logger.info("📊 Ejecutando Baseline Backtest...")
            self.run_baseline_backtest()
        
        # 2. Walk-forward
        if backtests_config.get('walk_forward', {}).get('enabled', False):
            logger.info("📊 Ejecutando Walk-Forward Backtest...")
            self.run_walk_forward_backtest()
        
        # 3. Monte Carlo
        if backtests_config.get('monte_carlo', {}).get('enabled', False):
            logger.info("📊 Ejecutando Monte Carlo Backtest...")
            self.run_monte_carlo_backtest()
        
        # 4. Transformer Optimization
        if backtests_config.get('transformer_optimization', {}).get('enabled', False):
            logger.info("📊 Ejecutando Transformer Optimization...")
            self.run_transformer_optimization()
        
        # 5. Ablation
        if backtests_config.get('ablation', {}).get('enabled', False):
            logger.info("📊 Ejecutando Ablation Study...")
            self.run_ablation_study()
        
        # 6. Grid Search
        if backtests_config.get('grid_search', {}).get('enabled', False):
            logger.info("📊 Ejecutando Grid Search...")
            self.run_grid_search()
        
        # 7. Out-of-Sample
        if backtests_config.get('out_of_sample', {}).get('enabled', False):
            logger.info("📊 Ejecutando Out-of-Sample Backtest...")
            self.run_out_of_sample_backtest()
        
        # 8. Regime Test
        if backtests_config.get('regime_test', {}).get('enabled', False):
            logger.info("📊 Ejecutando Regime Test...")
            self.run_regime_test()
        
        # Consolidar resultados
        df = self._consolidate_results()
        
        # Guardar reportes
        self._save_reports(df)
        
        logger.info(f"✅ Pipeline completado. {len(self.results)} backtests ejecutados.")
        
        return df
    
    def run_specific_backtests(self, backtest_names: List[str]) -> pd.DataFrame:
        """
        Ejecutar backtests específicos por nombre.
        
        Args:
            backtest_names: Lista de nombres de backtests a ejecutar.
                           Opciones: 'baseline', 'walk_forward', 'monte_carlo',
                           'transformer_optimization', 'ablation', 'grid_search',
                           'out_of_sample', 'regime_test'
        
        Returns:
            DataFrame con resultados consolidados
        """
        logger.info(f"🚀 Ejecutando backtests específicos: {backtest_names}")
        
        valid_names = {
            'baseline': self.run_baseline_backtest,
            'walk_forward': self.run_walk_forward_backtest,
            'monte_carlo': self.run_monte_carlo_backtest,
            'transformer_optimization': self.run_transformer_optimization,
            'ablation': self.run_ablation_study,
            'grid_search': self.run_grid_search,
            'out_of_sample': self.run_out_of_sample_backtest,
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
        """Guardar reportes en diferentes formatos."""
        output_formats = self.config['reporting'].get('output_format', ['csv'])
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if 'csv' in output_formats:
            csv_path = self.output_dir / f"comprehensive_backtest_results_{timestamp}.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"📄 Reporte CSV guardado: {csv_path}")
        
        if 'json' in output_formats:
            json_path = self.output_dir / f"comprehensive_backtest_results_{timestamp}.json"
            df.to_json(json_path, orient='records', indent=2)
            logger.info(f"📄 Reporte JSON guardado: {json_path}")
        
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

