"""
Comprehensive Backtest Runner - Modernized Architecture
Sistema completo de backtesting automatizado y configurable

Integración Fase 3: Migración a nueva arquitectura modular
- Eliminadas variables de entorno (reemplazado por ProcessPoolBacktestExecutor)
- Logging minimal (sin emojis)
- AggressiveMemoryManager para manejo de memoria
- train_with_retry para manejo robusto de errores
- BacktestDefaults para valores centralizados
- Monte Carlo unificado con BacktestOrchestrator
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

# Core backtesting modules (Fase 1 + Fase 2)
from app.backtesting.core import (
    BacktestConfigLoader,
    BacktestDefaults,
    BacktestOrchestrator,
    BacktestRunnerFacade,
    BoundedResults,
    create_backtest_runner,
)
from app.backtesting.core.executor import (
    BacktestExecutorFactory,
    ProcessPoolBacktestExecutor,
    SimpleBacktestExecutor,
)
from app.backtesting.core.error_handling import (
    MutexError,
    TrainingError,
    is_mutex_error,
    safe_execute,
    train_with_retry,
)
from app.backtesting.core.memory_manager import AggressiveMemoryManager

# Backtesting engine and models
from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig, BacktestResult
from app.backtesting.multi_strategy_engine import MultiStrategyBacktester

# Data loading
from app.backtesting.data_loader import DataLoader

# Data splitting and multiple testing correction
from app.backtesting.data_split import (
    MultipleTestingCorrector,
    TrainValTestSplitter,
    validate_out_of_sample_performance,
)

# Survivorship bias adjustment
from app.backtesting.universe_manager import UniverseManager

# Portfolio management
from app.services.portfolio_config_manager import get_portfolio_config_manager

# Strategy factory (Phase 5: extracted from God Object)
from app.backtesting.factories import StrategyFactory

# Strategy implementations
from app.strategies.momentum_modular.strategy import ModularMomentumStrategy

# Optional: quantstats and pyfolio for professional reports
try:
    import quantstats as qs

    QUANTSTATS_AVAILABLE = True
except ImportError:
    QUANTSTATS_AVAILABLE = False

try:
    import pyfolio as pf

    PYFOLIO_AVAILABLE = True
except ImportError:
    PYFOLIO_AVAILABLE = False

logger = logging.getLogger(__name__)


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
    9. Multi-Strategy - Prueba múltiples estrategias simultáneamente
    10. Regime Test - Desempeño por régimen de mercado

    Fase 3: Integración con nueva arquitectura modular
    """

    def __init__(self, config_path: str):
        """
        Inicializar runner con configuración.

        Args:
            config_path: Ruta al archivo YAML de configuración
        """
        logger.info("Initializing comprehensive backtest runner")

        # Usar BacktestConfigLoader (Fase 3)
        self.config_loader = BacktestConfigLoader(config_path)
        self.raw_config = self.config_loader.raw_config
        self.backtest_config = self.config_loader.get_backtest_config()
        self.config_path = config_path

        # Usar AggressiveMemoryManager (Fase 3)
        self.memory_manager = AggressiveMemoryManager(
            max_results=500,
            max_backtest_objects=100,
            memory_threshold_mb=4096
        )

        self.output_dir = Path(self.raw_config['reporting']['output_directory'])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cargar datos históricos
        self.data_loader = DataLoader()
        self.quotes = self._load_market_data()

        # Configuración de paralelización
        self.parallel_enabled = self.raw_config.get('parallelization', {}).get('enabled', True)
        self.max_workers = self.raw_config.get('parallelization', {}).get('max_workers', None)

        # Integrar meta_analyzer si está habilitado
        self.meta_enabled = self.raw_config.get('meta_analysis', {}).get('enabled', False)
        self.audit_trail = None
        self.learning_storage = None
        self.audit_hash: Optional[str] = None

        if self.meta_enabled:
            self._integrate_meta_analyzer()

        logger.info(f"ComprehensiveBacktestRunner initialized with {len(self.quotes)} quotes")
        if self.parallel_enabled:
            logger.info(f"Parallelization enabled (max_workers={self.max_workers or 'auto'})")

    def _integrate_meta_analyzer(self) -> None:
        """Integrate meta-analyzer if enabled."""
        try:
            from app.backtesting.meta_analyzer import integrate_meta_analyzer_with_runner

            meta = integrate_meta_analyzer_with_runner(
                runner=self,
                config_path=self.config_path,
                enable_audit=self.raw_config.get('meta_analysis', {}).get('enable_audit', True),
                enable_storage=self.raw_config.get('meta_analysis', {}).get('enable_storage', True),
                enable_analysis=self.raw_config.get('meta_analysis', {}).get('enable_analysis', True),
            )
            self.audit_trail = meta['audit_trail']
            self.learning_storage = meta['storage']
            self.audit_hash = meta['audit_hash']

            if self.audit_hash:
                hash_display = self.audit_hash[:16]
                logger.info(f"Meta-analyzer integrated (Hash: {hash_display}...)")

                if self.audit_trail:
                    logger.info(f"Configuration hash: {self.audit_hash}")
                    git_info = self.audit_trail._get_git_info()
                    if git_info.get('commit_hash'):
                        logger.info(
                            f"Git commit: {git_info['commit_hash'][:8]} "
                            f"(branch: {git_info.get('branch', 'unknown')})"
                        )
        except Exception as e:
            logger.warning(f"Could not integrate meta_analyzer: {e}")

    def _load_market_data(self) -> List:
        """Cargar datos históricos de mercado."""
        start_date = datetime.strptime(self.raw_config['input']['start_date'], "%Y-%m-%d")
        end_date = datetime.strptime(self.raw_config['input']['end_date'], "%Y-%m-%d")

        all_symbols = self.raw_config['input']['symbols']

        logger.info(f"Loading market data from {start_date.date()} to {end_date.date()}")
        logger.info(f"Symbols: {all_symbols}")

        quotes = []
        for symbol in all_symbols:
            symbol_quotes = self.data_loader.load_market_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )
            quotes.extend(symbol_quotes)
            logger.info(f"  Loaded {len(symbol_quotes)} quotes for {symbol}")

        return quotes

    def run_all_backtests(self) -> List[Dict[str, Any]]:
        """
        Ejecutar todos los backtests configurados.

        Returns:
            Lista de resultados de todos los backtests
        """
        logger.info("=" * 80)
        logger.info("STARTING COMPREHENSIVE BACKTEST SUITE")
        logger.info("=" * 80)

        start_time = datetime.now()
        results = []

        # Backtests configurados
        backtests_config = self.raw_config.get('backtests', {})

        # 1. Baseline
        if backtests_config.get('baseline', {}).get('enabled', True):
            logger.info("\n" + "=" * 80)
            logger.info("BASELINE BACKTEST")
            logger.info("=" * 80)
            baseline_results = self.run_baseline_backtest()
            results.extend(baseline_results)

        # 2. Learning Engines
        if backtests_config.get('learning_engines', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("LEARNING ENGINES BACKTEST")
            logger.info("=" * 80)
            learning_results = self.run_learning_engines_backtest()
            results.extend(learning_results)

        # 3. Walk-forward
        if backtests_config.get('walk_forward', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("WALK-FORWARD BACKTEST")
            logger.info("=" * 80)
            walk_forward_results = self.run_walk_forward_backtest()
            results.extend(walk_forward_results)

        # 4. Monte Carlo (unificado con Fase 3)
        if backtests_config.get('monte_carlo', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("MONTE CARLO BACKTEST")
            logger.info("=" * 80)
            monte_carlo_results = self.run_monte_carlo_backtest(
                parallel=self.parallel_enabled
            )
            results.extend(monte_carlo_results)

        # 5. Transformer Optimization
        if backtests_config.get('transformer_optimization', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("TRANSFORMER OPTIMIZATION BACKTEST")
            logger.info("=" * 80)
            transformer_results = self.run_transformer_optimization_backtest()
            results.extend(transformer_results)

        # 6. Ablation
        if backtests_config.get('ablation', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("ABLATION BACKTEST")
            logger.info("=" * 80)
            ablation_results = self.run_ablation_backtest()
            results.extend(ablation_results)

        # 7. Grid Search
        if backtests_config.get('grid_search', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("GRID SEARCH BACKTEST")
            logger.info("=" * 80)
            grid_results = self.run_grid_search_backtest()
            results.extend(grid_results)

        # 8. Out-of-Sample
        if backtests_config.get('out_of_sample', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("OUT-OF-SAMPLE BACKTEST")
            logger.info("=" * 80)
            oos_results = self.run_out_of_sample_backtest()
            results.extend(oos_results)

        # 9. Multi-Strategy
        if backtests_config.get('multi_strategy', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("MULTI-STRATEGY BACKTEST")
            logger.info("=" * 80)
            multi_results = self.run_multi_strategy_backtest()
            results.extend(multi_results)

        # 10. Regime Test
        if backtests_config.get('regime_test', {}).get('enabled', False):
            logger.info("\n" + "=" * 80)
            logger.info("REGIME TEST BACKTEST")
            logger.info("=" * 80)
            regime_results = self.run_regime_test_backtest()
            results.extend(regime_results)

        # Guardar resultados
        self._save_results(results)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 80)
        logger.info(f"COMPREHENSIVE BACKTEST SUITE COMPLETED")
        logger.info(f"Total backtests: {len(results)}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 80)

        return results

    def run_specific_backtests(self, backtest_names: List[str]) -> List[Dict[str, Any]]:
        """
        Ejecutar backtests específicos por nombre.

        Args:
            backtest_names: Lista de nombres de backtests a ejecutar
                           (baseline, learning_engines, walk_forward, monte_carlo,
                            transformer_optimization, ablation, grid_search, out_of_sample,
                            multi_strategy, regime_test)

        Returns:
            Lista de resultados de los backtests ejecutados
        """
        logger.info("=" * 80)
        logger.info(f"RUNNING SPECIFIC BACKTESTS: {backtest_names}")
        logger.info("=" * 80)

        start_time = datetime.now()
        results = []

        # Mapa de nombres a métodos
        backtest_methods = {
            'baseline': self.run_baseline_backtest,
            'learning_engines': self.run_learning_engines_backtest,
            'walk_forward': self.run_walk_forward_backtest,
            'monte_carlo': lambda: self.run_monte_carlo_backtest(parallel=self.parallel_enabled),
            'transformer_optimization': self.run_transformer_optimization_backtest,
            'ablation': self.run_ablation_backtest,
            'grid_search': self.run_grid_search_backtest,
            'out_of_sample': self.run_out_of_sample_backtest,
            'multi_strategy': self.run_multi_strategy_backtest,
            'regime_test': self.run_regime_test_backtest,
        }

        for name in backtest_names:
            if name not in backtest_methods:
                logger.warning(f"⚠️ Unknown backtest type: {name}")
                continue

            logger.info(f"\n{'=' * 80}")
            logger.info(f"EXECUTING: {name.upper()}")
            logger.info(f"{'=' * 80}")

            try:
                method = backtest_methods[name]
                test_results = method()
                results.extend(test_results)
            except Exception as e:
                logger.error(f"❌ Error executing {name}: {e}", exc_info=True)

        # Guardar resultados
        if results:
            self._save_results(results)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 80)
        logger.info(f"SPECIFIC BACKTESTS COMPLETED")
        logger.info(f"Total backtests: {len(results)}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 80)

        return results

    def run_baseline_backtest(self) -> List[Dict[str, Any]]:
        """
        Ejecutar backtest baseline con todos los módulos activos.

        Returns:
            Lista con resultado del baseline
        """
        logger.info("Running baseline backtest...")

        strategy_config = self._create_strategy_config()
        strategy = ModularMomentumStrategy(strategy_config)

        # Use loaded YAML config (not hardcoded defaults)
        initial_capital = Decimal(str(self.raw_config['input']['initial_capital']))
        backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=self.backtest_config.commission_per_trade,
            slippage_percentage=self.backtest_config.slippage_percentage,
            max_position_size=self.backtest_config.max_position_size,
            stop_loss_percentage=self.backtest_config.stop_loss_percentage,
            take_profit_percentage=self.backtest_config.take_profit_percentage,
            risk_free_rate=self.backtest_config.risk_free_rate,
        )

        strategy_name = self._get_strategy_name(strategy)

        # Usar SimpleBacktestExecutor (Fase 3)
        executor = SimpleBacktestExecutor(backtest_config)
        result = executor.execute(
            self.quotes,
            strategy,
            strategy_name=strategy_name
        )

        consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)

        result_dict = {
            'test_type': 'baseline',
            'test_name': 'Baseline - All Modules Active',
            'modules_active': list(self.raw_config['modules']['filters'].keys()),
            'learning_engine': None,
            'thresholds': self._extract_thresholds(strategy_config),
            'total_pnl': consistent_metrics['total_pnl'],
            'return_pct': consistent_metrics['return_pct'],
            'win_rate': float(result.performance.win_rate),
            'sharpe_ratio': (
                float(result.performance.sharpe_ratio)
                if result.performance.sharpe_ratio
                else 0.0
            ),
            'max_drawdown': float(result.performance.max_drawdown_percentage),
            'total_trades': result.performance.total_trades,
            'avg_trade_pnl': (
                consistent_metrics['total_pnl'] / result.performance.total_trades
                if result.performance.total_trades > 0
                else 0.0
            ),
            'final_capital': consistent_metrics['final_capital'],
        }

        # Usar AggressiveMemoryManager (Fase 3)
        self.memory_manager.add_result(result_dict)
        self.memory_manager.add_backtest_object('baseline', result)

        self._save_test_audit_and_weights(result_dict, 'baseline', strategy)

        logger.info(f"Baseline complete: PnL=${result_dict['total_pnl']:.2f}, Sharpe={result_dict['sharpe_ratio']:.2f}")

        return [result_dict]

    def run_learning_engines_backtest(self) -> List[Dict[str, Any]]:
        """
        Ejecutar backtests para cada learning engine individualmente.

        Returns:
            Lista de resultados para cada learning engine
        """
        logger.info("Running learning engines backtest...")

        results = []
        learning_engines_config = self.raw_config.get('learning_engines', {})

        # Learning engines a probar
        engine_types = ['supervised', 'deep', 'reinforcement', 'transformer']

        for engine_type in engine_types:
            if not learning_engines_config.get(engine_type, {}).get('enabled', False):
                logger.info(f"Skipping {engine_type} learning engine (disabled)")
                continue

            logger.info(f"Testing {engine_type} learning engine...")

            result_dict = self._test_learning_engine(engine_type)
            if result_dict:
                results.append(result_dict)

        logger.info(f"Learning engines backtest completed: {len(results)} engines tested")

        return results

    def _test_learning_engine(self, engine_type: str) -> Optional[Dict[str, Any]]:
        """
        Probar un learning engine específico.

        Args:
            engine_type: Tipo de learning engine ('supervised', 'deep', etc.)

        Returns:
            Resultado del backtest o None si falló
        """
        try:
            strategy_config = self._create_strategy_config()
            strategy = ModularMomentumStrategy(strategy_config)

            # Usar train_with_retry (Fase 3)
            training_successful = train_with_retry(
                strategy=strategy,
                engine_type=engine_type,
                use_subprocess=True  # Usar multiprocessing como fallback
            )

            if not training_successful:
                logger.warning(f"{engine_type} learning engine training failed")
                return None

            # Ejecutar backtest
            initial_capital = Decimal(str(self.raw_config['input']['initial_capital']))
            backtest_config = BacktestConfig(
                initial_capital=initial_capital,
                commission_per_trade=self.backtest_config.commission_per_trade,
                slippage_percentage=self.backtest_config.slippage_percentage,
                max_position_size=self.backtest_config.max_position_size,
                stop_loss_percentage=self.backtest_config.stop_loss_percentage,
                take_profit_percentage=self.backtest_config.take_profit_percentage,
                risk_free_rate=self.backtest_config.risk_free_rate,
            )

            strategy_name = self._get_strategy_name(strategy)
            executor = SimpleBacktestExecutor(backtest_config)
            result = executor.execute(
                self.quotes,
                strategy,
                strategy_name=strategy_name
            )

            consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)

            result_dict = {
                'test_type': f'learning_engine_{engine_type}',
                'test_name': f'Learning Engine - {engine_type.capitalize()}',
                'modules_active': list(self.raw_config['modules']['filters'].keys()),
                'learning_engine': engine_type,
                'thresholds': self._extract_thresholds(strategy_config),
                'total_pnl': consistent_metrics['total_pnl'],
                'return_pct': consistent_metrics['return_pct'],
                'win_rate': float(result.performance.win_rate),
                'sharpe_ratio': (
                    float(result.performance.sharpe_ratio)
                    if result.performance.sharpe_ratio
                    else 0.0
                ),
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'avg_trade_pnl': (
                    consistent_metrics['total_pnl'] / result.performance.total_trades
                    if result.performance.total_trades > 0
                    else 0.0
                ),
                'final_capital': consistent_metrics['final_capital'],
            }

            self.memory_manager.add_result(result_dict)
            self.memory_manager.add_backtest_object(f'learning_engine_{engine_type}', result)

            self._save_test_audit_and_weights(result_dict, f'learning_engine_{engine_type}', strategy)

            logger.info(
                f"{engine_type.capitalize()} learning engine complete: "
                f"PnL=${result_dict['total_pnl']:.2f}, "
                f"Sharpe={result_dict['sharpe_ratio']:.2f}"
            )

            return result_dict

        except MutexError as e:
            logger.warning(f"Mutex error in {engine_type} learning engine: {e}")
            return None
        except TrainingError as e:
            logger.error(f"Training error in {engine_type} learning engine: {e}")
            return None
        except Exception as e:
            logger.error(f"Error testing {engine_type} learning engine: {e}", exc_info=True)
            return None

    def run_monte_carlo_backtest(self, parallel: bool = False) -> List[Dict[str, Any]]:
        """
        Ejecutar Monte Carlo / Stress Test (Fase 3: Unificado).

        Soporta ejecución secuencial y paralela usando ProcessPoolBacktestExecutor.

        Args:
            parallel: Si True, usa ProcessPoolBacktestExecutor para paralelización

        Returns:
            Lista de resultados de simulaciones Monte Carlo
        """
        logger.info(f"Running Monte Carlo Backtest ({'parallel' if parallel else 'sequential'})...")

        mc_config = self.raw_config['backtests']['monte_carlo']
        num_simulations = mc_config.get('num_simulations', 100)
        volatility_multiplier = mc_config.get('volatility_multiplier', {}).get('default', 1.0)

        results = []

        # Crear executor según configuración
        if parallel:
            executor = ProcessPoolBacktestExecutor(
                self.backtest_config,
                max_processes=self.max_workers or 4
            )
        else:
            executor = SimpleBacktestExecutor(self.backtest_config)

        # Usar BacktestOrchestrator (Fase 3)
        orchestrator = BacktestOrchestrator(self.backtest_config, executor)

        # Crear estrategia base
        strategy_config = self._create_strategy_config()
        base_strategy = ModularMomentumStrategy(strategy_config)

        # Ejecutar simulaciones
        for sim_num in range(num_simulations):
            if sim_num % 10 == 0:
                logger.info(f"  Simulation {sim_num+1}/{num_simulations}...")

            # Crear quotes modificados con volatilidad aleatoria
            modified_quotes = self._create_monte_carlo_quotes(volatility_multiplier)

            # Ejecutar backtest
            result = executor.execute(
                modified_quotes,
                base_strategy,
                strategy_name=f'Monte Carlo Simulation {sim_num+1}'
            )

            # Convertir a diccionario
            initial_capital = float(self.backtest_config.initial_capital)
            final_capital = float(result.final_capital)

            result_dict = {
                'test_type': 'monte_carlo',
                'test_name': f'Monte Carlo - Simulation {sim_num+1}',
                'simulation_num': sim_num + 1,
                'volatility_multiplier': volatility_multiplier,
                'modules_active': list(self.raw_config['modules']['filters'].keys()),
                'learning_engine': None,
                'thresholds': self._extract_thresholds(strategy_config),
                'total_pnl': final_capital - initial_capital,
                'return_pct': ((final_capital - initial_capital) / initial_capital * 100)
                if initial_capital > 0 else 0.0,
                'win_rate': float(result.performance.win_rate) if result.performance else 0.0,
                'sharpe_ratio': (
                    float(result.performance.sharpe_ratio)
                    if result.performance and result.performance.sharpe_ratio else 0.0
                ),
                'max_drawdown': (
                    float(result.performance.max_drawdown_percentage)
                    if result.performance else 0.0
                ),
                'total_trades': result.performance.total_trades if result.performance else 0,
                'avg_trade_pnl': (
                    (final_capital - initial_capital) / result.performance.total_trades
                    if result.performance and result.performance.total_trades > 0 else 0.0
                ),
                'final_capital': final_capital,
            }

            results.append(result_dict)
            self.memory_manager.add_result(result_dict)

        logger.info(f"Monte Carlo completed: {len(results)} simulations")

        return results

    def _create_monte_carlo_quotes(self, volatility_multiplier: float) -> List:
        """
        Crear quotes modificados con volatilidad realista para Monte Carlo.

        ANTES: Usaba shock aleatorio simple np.random.normal(0, volatility_multiplier * 0.02)
        AHORA: Usa RealisticDataGenerator con GARCH y regime switching

        Args:
            volatility_multiplier: Multiplicador de volatilidad

        Returns:
            Lista de quotes modificados con datos realistas
        """
        from app.models.market_data import DataFeedType, Quote
        from app.backtesting.realistic_data_generator import RealisticDataGenerator

        # Si no hay quotes base, crear datos nuevos
        if not self.quotes:
            logger.warning("No base quotes available, generating new realistic data")
            gen = RealisticDataGenerator(
                seed=self.config.get('random_state', 42),
                base_price=100.0,
                base_volume=50_000_000,
            )
            from datetime import datetime
            start_date = datetime.now()
            return gen.generate_realistic_quotes(
                symbol='SYNTH',
                n_days=252,
                start_date=start_date,
                use_regime_switching=True,
            )

        # Usar generador realista para crear simulaciones Monte Carlo realistas
        gen = RealisticDataGenerator(
            seed=self.config.get('random_state', 42),
            base_price=float(self.quotes[0].close),
            base_volume=int(self.quotes[0].volume) if self.quotes[0].volume else 50_000_000,
        )

        # Generar escenario Monte Carlo con volatilidad ajustada
        # Usamos regime VOLATILE para simulaciones Monte Carlo
        from datetime import datetime
        start_date = self.quotes[0].timestamp if self.quotes else datetime.now()

        modified_quotes = gen.generate_realistic_quotes(
            symbol=self.quotes[0].symbol if self.quotes else 'SYNTH',
            n_days=len(self.quotes),
            start_date=start_date,
            use_regime_switching=True,
            initial_regime='volatile',  # Usa régimen volátil para Monte Carlo
        )

        logger.info(
            f"Generated {len(modified_quotes)} realistic Monte Carlo quotes "
            f"(replacing simplistic random shocks)"
        )

        return modified_quotes

    # Métodos placeholder para otros backtests (se implementarán en próximas fases)
    def run_walk_forward_backtest(self) -> List[Dict[str, Any]]:
        """Ejecutar backtest walk-forward (placeholder)."""
        logger.info("Walk-forward backtest not yet implemented in Phase 3")
        return []

    def run_transformer_optimization_backtest(self) -> List[Dict[str, Any]]:
        """Ejecutar backtest de optimización con Transformer (placeholder)."""
        logger.info("Transformer optimization backtest not yet implemented in Phase 3")
        return []

    def run_ablation_backtest(self) -> List[Dict[str, Any]]:
        """Ejecutar backtest de ablation (placeholder)."""
        logger.info("Ablation backtest not yet implemented in Phase 3")
        return []

    def run_grid_search_backtest(self) -> List[Dict[str, Any]]:
        """Ejecutar backtest de grid search (placeholder)."""
        logger.info("Grid search backtest not yet implemented in Phase 3")
        return []

    def run_out_of_sample_backtest(self) -> List[Dict[str, Any]]:
        """Ejecutar backtest out-of-sample (placeholder)."""
        logger.info("Out-of-sample backtest not yet implemented in Phase 3")
        return []

    def run_multi_strategy_backtest(self) -> List[Dict[str, Any]]:
        """
        Ejecutar backtest multi-strategy con asignación de capital.

        Integración con:
        - ProfileStrategyMapper para mapeo de perfil a estrategias
        - MultiStrategyBacktester para ejecución concurrente
        - MultiStrategyAllocationManager para distribución de capital

        Returns:
            Lista de resultados con métricas por estrategia y combinadas
        """
        logger.info("Running multi-strategy backtest...")

        try:
            # Paso 1: Crear InputProfile desde la configuración
            profile = self._create_input_profile_from_config()

            # Paso 2: Crear ProfileStrategyMapper
            from app.services.profile_driven_trading.profile_strategy_mapper import (
                ProfileStrategyMapper,
            )

            mapper = ProfileStrategyMapper()

            # Paso 3: Obtener mapeo de estrategia
            strategy_mapping = mapper.create_strategy_mapping(profile)

            logger.info(
                f"Profile mapped to {len(strategy_mapping.enabled_strategies)} strategies: "
                f"{', '.join(strategy_mapping.enabled_strategies)}"
            )

            # Paso 4: Obtener asignación de capital
            allocation_manager = mapper.get_capital_allocation(profile)
            capital_allocations = allocation_manager.allocate_capital()

            logger.info("Capital allocation:")
            for strategy_name, capital in capital_allocations.items():
                weight = float(capital / profile.capital_initial)
                logger.info(f"  {strategy_name}: ${capital:,.2f} ({weight:.1%})")

            # Paso 5: Crear instancias de estrategia
            strategies = {}
            for strategy_name in strategy_mapping.enabled_strategies:
                try:
                    strategy_config = self._create_strategy_config_for_type(
                        strategy_name, strategy_mapping
                    )
                    strategy = StrategyFactory.create_strategy(strategy_config)
                    strategies[strategy_name] = strategy
                    logger.info(f"Created strategy instance: {strategy_name}")
                except Exception as e:
                    logger.error(f"Failed to create strategy {strategy_name}: {e}")
                    continue

            if not strategies:
                logger.error("No strategies could be created")
                return []

            # Paso 6: Crear MultiStrategyBacktester
            config_params = {
                "commission": self.backtest_config.commission_per_trade,
                "slippage": self.backtest_config.slippage_percentage,
                "stop_loss": self.backtest_config.stop_loss_percentage,
                "take_profit": self.backtest_config.take_profit_percentage,
                "max_position_size": self.backtest_config.max_position_size,
            }

            multi_strategy_backtester = MultiStrategyBacktester(
                allocation_manager=allocation_manager,
                strategies=strategies,
                config_params=config_params,
                enable_diagnostics=self.raw_config.get("diagnostics", {}).get(
                    "enabled", False
                ),
                enable_dynamic_reallocation=self.raw_config.get(
                    "dynamic_reallocation", {}
                ).get("enabled", True),
            )

            # Paso 7: Ejecutar backtest multi-strategy
            start_date = datetime.strptime(
                self.raw_config["input"]["start_date"], "%Y-%m-%d"
            )
            end_date = datetime.strptime(self.raw_config["input"]["end_date"], "%Y-%m-%d")

            logger.info(
                f"Running multi-strategy backtest from {start_date.date()} to {end_date.date()}"
            )

            consolidated_results = multi_strategy_backtester.run_multi_strategy_backtest(
                quotes=self.quotes, start_date=start_date, end_date=end_date
            )

            # Paso 8: Convertir resultados al formato esperado
            results = self._format_multi_strategy_results(
                consolidated_results=consolidated_results,
                strategy_mapping=strategy_mapping,
                profile=profile,
            )

            # Paso 9: Guardar resultados
            for result in results:
                self.memory_manager.add_result(result)

            logger.info(
                f"Multi-strategy backtest completed: {len(results)} results generated"
            )

            return results

        except Exception as e:
            logger.error(f"Error in multi-strategy backtest: {e}", exc_info=True)
            return []

    def _create_input_profile_from_config(self):
        """
        Crear InputProfile desde la configuración de backtest.

        Returns:
            InputProfile con parámetros del config
        """
        from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance

        # Extraer parámetros del config
        initial_capital = Decimal(str(self.raw_config["input"]["initial_capital"]))

        # Obtener objetivo y riesgo del config o usar defaults
        objective_str = self.raw_config.get("profile", {}).get(
            "objective", "balanced_growth"
        )
        risk_str = self.raw_config.get("profile", {}).get("risk_tolerance", "medio")

        # Mapear a enums
        objective = ObjectivoInversion(objective_str)
        risk = RiskTolerance(risk_str)

        # Obtener horizonte de inversión (default 24 meses)
        investment_horizon = self.raw_config.get("profile", {}).get(
            "investment_horizon", 24
        )

        profile = InputProfile(
            capital_initial=initial_capital,
            objetivo_inversion=objective,
            risk_tolerance=risk,
            investment_horizon=investment_horizon,
        )

        logger.info(
            f"Created InputProfile: capital={initial_capital}, "
            f"objective={objective.value}, risk={risk.value}"
        )

        return profile

    def _create_strategy_config_for_type(
        self, strategy_name: str, strategy_mapping
    ) -> Dict[str, Any]:
        """
        Crear configuración para un tipo de estrategia específico.

        Args:
            strategy_name: Nombre de la estrategia
            strategy_mapping: Mapeo de estrategia desde ProfileStrategyMapper

        Returns:
            Configuración de estrategia
        """
        # Configuración base
        base_config = {
            "type": strategy_name,
            "symbols": self.raw_config["input"]["symbols"],
            "parameters": {
                "risk_profile": strategy_mapping.risk_profile,
                "leverage": strategy_mapping.leverage,
                "max_position_size": strategy_mapping.max_position_size,
                "max_sector_allocation": strategy_mapping.max_sector_allocation,
            },
            "thresholds": {
                "buy_threshold": 0.7,
                "sell_threshold": 0.3,
                "stop_loss": -0.05,
                "take_profit": 0.10,
            },
        }

        # Ajustar según tipo de estrategia
        if strategy_name == "momentum_modular":
            # Configuración específica para momentum modular
            base_config.update(
                {
                    "preset": "custom",
                    "modules": self._get_filter_config(),
                    "presets": {
                        "custom": {
                            "combination_mode": "MAJORITY",
                            "min_confidence": 0.7,
                        }
                    },
                }
            )
        elif strategy_name == "mean_reversion_modular":
            # Configuración para mean reversion
            base_config["parameters"].update(
                {
                    "lookback_period": 20,
                    "entry_threshold": 2.0,
                    "exit_threshold": 0.5,
                }
            )
        elif strategy_name == "dividend_screener":
            # Configuración para dividendos
            base_config["parameters"].update(
                {
                    "min_dividend_yield": 0.03,
                    "max_payout_ratio": 0.8,
                    "min_growth_rate": 0.05,
                }
            )

        return base_config

    def _get_filter_config(self) -> Dict[str, Any]:
        """
        Obtener configuración de filtros desde el config YAML.

        Returns:
            Diccionario con configuración de filtros
        """
        filters_config = {}

        if "modules" in self.raw_config and "filters" in self.raw_config["modules"]:
            filters = self.raw_config["modules"]["filters"]

            for filter_name, filter_config in filters.items():
                if filter_config.get("enabled", False):
                    filter_params = {}
                    for param_name, param_config in filter_config.get(
                        "parameters", {}
                    ).items():
                        if "default" in param_config:
                            filter_params[param_name] = param_config["default"]

                    filters_config[filter_name] = {
                        "enabled": True,
                        **filter_params
                    }

        return filters_config

    def _format_multi_strategy_results(
        self,
        consolidated_results: Dict,
        strategy_mapping,
        profile,
    ) -> List[Dict[str, Any]]:
        """
        Formatear resultados del multi-strategy backtest.

        Args:
            consolidated_results: Resultados consolidados desde MultiStrategyBacktester
            strategy_mapping: Mapeo de estrategia desde ProfileStrategyMapper
            profile: InputProfile utilizado

        Returns:
            Lista de diccionarios con resultados formateados
        """
        results = []

        # Extraer resultados por estrategia
        per_strategy = consolidated_results.get("per_strategy", {})
        combined = consolidated_results.get("combined", {})
        allocation_info = consolidated_results.get("allocation", {})

        # Crear resultado individual por cada estrategia
        for strategy_name, strategy_metrics in per_strategy.items():
            result_dict = {
                "test_type": f"multi_strategy_{strategy_name}",
                "test_name": f"Multi-Strategy - {strategy_name}",
                "strategy_name": strategy_name,
                "modules_active": [strategy_name],
                "learning_engine": None,
                "thresholds": self._extract_thresholds({}),
                # Métricas de la estrategia
                "total_pnl": (
                    strategy_metrics["final_capital"] - strategy_metrics["initial_capital"]
                ),
                "return_pct": strategy_metrics["total_return"],
                "win_rate": strategy_metrics.get("win_rate", 0.0),
                "sharpe_ratio": strategy_metrics.get("sharpe_ratio", 0.0),
                "max_drawdown": strategy_metrics.get("max_drawdown", 0.0),
                "total_trades": strategy_metrics.get("total_trades", 0),
                "avg_trade_pnl": (
                    (
                        strategy_metrics["final_capital"]
                        - strategy_metrics["initial_capital"]
                    )
                    / strategy_metrics.get("total_trades", 1)
                ),
                "final_capital": strategy_metrics["final_capital"],
                # Información de asignación
                "allocated_capital": strategy_metrics["initial_capital"],
                "capital_weight": allocation_info.get(strategy_name, {}).get(
                    "weight", 0.0
                ),
                # Perfil
                "profile_objective": profile.objetivo_inversion.value,
                "profile_risk": profile.risk_tolerance.value,
                "profile_capital_tier": strategy_mapping.capital_tier,
            }

            results.append(result_dict)

        # Crear resultado combinado
        if combined:
            combined_result = {
                "test_type": "multi_strategy_combined",
                "test_name": "Multi-Strategy - Combined Portfolio",
                "strategy_name": "combined",
                "modules_active": strategy_mapping.enabled_strategies,
                "learning_engine": None,
                "thresholds": self._extract_thresholds({}),
                # Métricas combinadas
                "total_pnl": (
                    combined["total_final_capital"] - combined["total_initial_capital"]
                ),
                "return_pct": combined["total_return"],
                "win_rate": 0.0,  # No aplicable a portafolio combinado
                "sharpe_ratio": combined.get("weighted_sharpe", 0.0),
                "max_drawdown": combined.get("weighted_max_dd", 0.0),
                "total_trades": combined.get("total_trades", 0),
                "avg_trade_pnl": (
                    (
                        combined["total_final_capital"]
                        - combined["total_initial_capital"]
                    )
                    / combined.get("total_trades", 1)
                ),
                "final_capital": combined["total_final_capital"],
                # Información de portafolio
                "total_initial_capital": combined["total_initial_capital"],
                "num_strategies": len(per_strategy),
                # Ensemble config
                "ensemble_mode": strategy_mapping.ensemble_mode,
                "ensemble_min_strategies": strategy_mapping.ensemble_min_strategies,
                "ensemble_confidence": strategy_mapping.ensemble_confidence_threshold,
                # Perfil
                "profile_objective": profile.objetivo_inversion.value,
                "profile_risk": profile.risk_tolerance.value,
                "profile_capital_tier": strategy_mapping.capital_tier,
            }

            results.append(combined_result)

        return results

    def run_regime_test_backtest(self) -> List[Dict[str, Any]]:
        """Ejecutar backtest de régimen de mercado (placeholder)."""
        logger.info("Regime test backtest not yet implemented in Phase 3")
        return []

    def optimize_with_validation(
        self,
        param_grid: List[Dict[str, Any]],
        strategy_class: Any = ModularMomentumStrategy,
    ) -> Dict[str, Any]:
        """
        Optimize strategy parameters with proper train/val/test split and multiple testing correction.

        This method implements robust parameter optimization to prevent overfitting:
        1. Split data into train/validation/test sets
        2. Optimize parameters on training data
        3. Select best parameters based on validation performance
        4. Apply Bonferroni correction for multiple testing
        5. Validate final performance on held-out test set

        Args:
            param_grid: List of parameter combinations to test
            strategy_class: Strategy class to optimize (default: ModularMomentumStrategy)

        Returns:
            Dictionary with optimization results including:
            - best_params: Best parameter combination
            - train_sharpe: Sharpe ratio on training set
            - val_sharpe: Sharpe ratio on validation set
            - test_sharpe: Sharpe ratio on test set
            - adjusted_confidence: Confidence level after Bonferroni correction
            - oos_valid: Whether out-of-sample validation passed
            - all_results: All parameter combinations tested
        """
        logger.info(f"Starting parameter optimization with validation ({len(param_grid)} parameter sets)")

        # Initialize data splitter
        splitter = TrainValTestSplitter(
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
        )

        # Split data
        train_quotes, val_quotes, test_quotes = splitter.split_data(
            quotes=self.quotes,
            start_date=datetime.strptime(self.raw_config['input']['start_date'], "%Y-%m-%d"),
            end_date=datetime.strptime(self.raw_config['input']['end_date'], "%Y-%m-%d"),
        )

        logger.info(
            f"Data split complete: train={len(train_quotes)}, "
            f"val={len(val_quotes)}, test={len(test_quotes)}"
        )

        # Initialize multiple testing corrector
        corrector = MultipleTestingCorrector(num_tests=len(param_grid), base_confidence=0.95)
        adjusted_confidence = corrector.bonferroni_correction()

        logger.info(
            f"Multiple testing correction applied: {0.95:.4f} -> {adjusted_confidence:.4f} "
            f"({len(param_grid)} tests)"
        )

        # Test each parameter combination
        results = []
        for i, params in enumerate(param_grid):
            if i % 10 == 0:
                logger.info(f"Testing parameter set {i+1}/{len(param_grid)}...")

            # Create strategy with parameters
            try:
                strategy_config = self._create_strategy_config()
                strategy_config.update(params)
                strategy = strategy_class(strategy_config)

                # Backtest on training data
                train_result = self._backtest_with_quotes(
                    quotes=train_quotes,
                    strategy=strategy,
                )

                # Backtest on validation data
                val_result = self._backtest_with_quotes(
                    quotes=val_quotes,
                    strategy=strategy,
                )

                # Store results
                results.append({
                    'params': params,
                    'train_sharpe': train_result.get('sharpe_ratio', 0.0),
                    'val_sharpe': val_result.get('sharpe_ratio', 0.0),
                    'train_result': train_result,
                    'val_result': val_result,
                })

            except Exception as e:
                logger.warning(f"Parameter set {i+1} failed: {e}")
                continue

        # Select best params based on validation performance
        if not results:
            logger.error("No parameter combinations completed successfully")
            return {
                'success': False,
                'error': 'All parameter combinations failed'
            }

        best_result = max(results, key=lambda x: x['val_sharpe'])

        logger.info(
            f"Best parameters selected: train_sharpe={best_result['train_sharpe']:.3f}, "
            f"val_sharpe={best_result['val_sharpe']:.3f}"
        )

        # Test on held-out test set
        strategy_config = self._create_strategy_config()
        strategy_config.update(best_result['params'])
        strategy = strategy_class(strategy_config)

        test_result = self._backtest_with_quotes(
            quotes=test_quotes,
            strategy=strategy,
        )

        test_sharpe = test_result.get('sharpe_ratio', 0.0)

        # Validate OOS performance
        oos_ok = validate_out_of_sample_performance(
            train_sharpe=best_result['train_sharpe'],
            val_sharpe=best_result['val_sharpe'],
            test_sharpe=test_sharpe,
            degradation_tolerance=0.5,
        )

        optimization_result = {
            'success': True,
            'best_params': best_result['params'],
            'train_sharpe': best_result['train_sharpe'],
            'val_sharpe': best_result['val_sharpe'],
            'test_sharpe': test_sharpe,
            'adjusted_confidence': adjusted_confidence,
            'oos_valid': oos_ok,
            'num_tests': len(param_grid),
            'all_results': results,
        }

        # Log summary
        logger.info("=" * 80)
        logger.info("OPTIMIZATION WITH VALIDATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Best parameters: {best_result['params']}")
        logger.info(f"Performance:")
        logger.info(f"  Train Sharpe: {best_result['train_sharpe']:.3f}")
        logger.info(f"  Val Sharpe:   {best_result['val_sharpe']:.3f}")
        logger.info(f"  Test Sharpe:  {test_sharpe:.3f}")
        logger.info(f"Adjusted confidence (Bonferroni): {adjusted_confidence:.4f}")
        logger.info(f"OOS validation: {'PASSED' if oos_ok else 'FAILED'}")
        logger.info("=" * 80)

        return optimization_result

    def _backtest_with_quotes(
        self,
        quotes: List,
        strategy: Any,
    ) -> Dict[str, Any]:
        """
        Execute backtest with specific quotes and strategy.

        Args:
            quotes: Market data to backtest
            strategy: Strategy instance

        Returns:
            Dictionary with backtest results
        """
        initial_capital = Decimal(str(self.raw_config['input']['initial_capital']))
        backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=self.backtest_config.commission_per_trade,
            slippage_percentage=self.backtest_config.slippage_percentage,
            max_position_size=self.backtest_config.max_position_size,
            stop_loss_percentage=self.backtest_config.stop_loss_percentage,
            take_profit_percentage=self.backtest_config.take_profit_percentage,
            risk_free_rate=self.backtest_config.risk_free_rate,
        )

        strategy_name = self._get_strategy_name(strategy)
        executor = SimpleBacktestExecutor(backtest_config)
        result = executor.execute(
            quotes,
            strategy,
            strategy_name=strategy_name
        )

        consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)

        return {
            'total_pnl': consistent_metrics['total_pnl'],
            'return_pct': consistent_metrics['return_pct'],
            'win_rate': float(result.performance.win_rate) if result.performance else 0.0,
            'sharpe_ratio': (
                float(result.performance.sharpe_ratio)
                if result.performance and result.performance.sharpe_ratio
                else 0.0
            ),
            'max_drawdown': (
                float(result.performance.max_drawdown_percentage)
                if result.performance
                else 0.0
            ),
            'total_trades': result.performance.total_trades if result.performance else 0,
            'final_capital': consistent_metrics['final_capital'],
            'expectancy': (
                float(result.performance.expectancy)
                if result.performance and result.performance.expectancy
                else None
            ),
        }

    # Métodos helper
    def _create_strategy_config(self) -> Dict[str, Any]:
        """
        Crear configuración de estrategia desde config YAML.

        Phase 5: Now delegates to StrategyFactory to reduce God Object.
        """
        # Si la config tiene modules.filters, crear config adaptada
        if 'modules' in self.raw_config and 'filters' in self.raw_config['modules']:
            # Crear configuración de filtros desde YAML
            filters_config = {}
            filters = self.raw_config['modules']['filters']

            for filter_name, filter_config in filters.items():
                if filter_config.get('enabled', False):
                    # Extraer parámetros default
                    filter_params = {}
                    for param_name, param_config in filter_config.get('parameters', {}).items():
                        if 'default' in param_config:
                            filter_params[param_name] = param_config['default']

                    filters_config[filter_name] = {
                        'enabled': True,
                        **filter_params
                    }

            # ModularMomentumStrategy lee filtros desde config['modules'][nombre_filtro]
            # NO desde presets.custom.filters
            # BALANCED APPROACH: MAJORITY mode (5/6+ filters) instead of ALL (6/6)
            # This prevents 0 signals while maintaining higher quality than original 4/6
            return {
                'type': 'modular_momentum',
                'preset': 'custom',  # Preset personalizado
                'modules': filters_config,  # Filtros al nivel que la estrategia espera
                'presets': {
                    'custom': {
                        'combination_mode': 'MAJORITY',  # 5/6+ filters must agree (balanced)
                        'min_confidence': 0.7,  # 70% confidence threshold
                        'learning_mode': 'supervised'
                    }
                }
            }

        return StrategyFactory.create_baseline_config(self.raw_config)

    def _extract_filter_thresholds(self) -> Dict[str, Any]:
        """
        Extraer thresholds de la configuración de filtros.

        Returns:
            Diccionario con thresholds de cada filtro activo
        """
        thresholds = {}
        filters_config = self.raw_config.get('modules', {}).get('filters', {})

        # Extraer thresholds de cada filtro
        for filter_name, filter_config in filters_config.items():
            if filter_config.get('enabled', False):
                params = filter_config.get('parameters', {})
                # Usar valores default de los parámetros
                for param_name, param_config in params.items():
                    if 'default' in param_config:
                        threshold_key = f"{filter_name}.{param_name}"
                        thresholds[threshold_key] = param_config['default']

        return thresholds

    def _get_strategy_name(self, strategy: Any) -> str:
        """
        Obtener nombre de estrategia.

        Phase 5: Now delegates to StrategyFactory.
        """
        return StrategyFactory.get_strategy_name(strategy)

    def _extract_thresholds(self, strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extraer thresholds de configuración de estrategia.

        Phase 5: Now delegates to StrategyFactory.
        """
        return StrategyFactory.extract_thresholds(strategy_config)

    def _calculate_consistent_metrics(
        self, result: BacktestResult, initial_capital: Decimal
    ) -> Dict[str, float]:
        """
        Calcular métricas consistentes desde BacktestResult.

        Args:
            result: Resultado del backtest
            initial_capital: Capital inicial

        Returns:
            Diccionario con métricas calculadas
        """
        initial_capital_float = float(initial_capital)
        final_capital_float = float(result.final_capital)

        total_pnl = final_capital_float - initial_capital_float
        return_pct = (
            (total_pnl / initial_capital_float * 100)
            if initial_capital_float > 0
            else 0.0
        )

        return {
            'total_pnl': total_pnl,
            'return_pct': return_pct,
            'final_capital': final_capital_float,
        }

    def _save_test_audit_and_weights(
        self, result_dict: Dict[str, Any], test_type: str, strategy: Any
    ) -> None:
        """
        Guardar auditoría y pesos del test.

        Args:
            result_dict: Resultado del backtest
            test_type: Tipo de test
            strategy: Estrategia utilizada
        """
        if not self.meta_enabled:
            return

        try:
            # Guardar auditoría
            if self.audit_trail:
                self.audit_trail.log_test_result(result_dict)

            # Guardar pesos si hay learning engine
            if self.learning_storage and result_dict.get('learning_engine'):
                engine_type = result_dict['learning_engine']
                if hasattr(strategy, 'learning_engine') and strategy.learning_engine:
                    try:
                        self.learning_storage.save_weights(
                            engine_name=engine_type,
                            weights=strategy.learning_engine.model,
                            test_id=result_dict['test_name'],
                            metrics=result_dict
                        )
                    except Exception as e:
                        logger.warning(f"Could not save weights: {e}")

        except Exception as e:
            logger.warning(f"Error saving audit/weights: {e}")

    def _save_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Guardar resultados a archivos.

        Args:
            results: Lista de resultados
        """
        if not results:
            logger.warning("No results to save")
            return

        reporting_config = self.raw_config.get('reporting', {})
        output_formats = reporting_config.get('output_format', ['csv', 'json'])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Guardar CSV
        if 'csv' in output_formats:
            csv_path = self.output_dir / f"backtest_results_{timestamp}.csv"
            df = pd.DataFrame(results)
            df.to_csv(csv_path, index=False)
            logger.info(f"Results saved to CSV: {csv_path}")

        # Guardar JSON
        if 'json' in output_formats:
            json_path = self.output_dir / f"backtest_results_{timestamp}.json"
            import json
            with open(json_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to JSON: {json_path}")

    def get_results(self) -> List[Dict[str, Any]]:
        """
        Obtener todos los resultados almacenados.

        Returns:
            Lista de resultados
        """
        return self.memory_manager.get_results()

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de memoria.

        Returns:
            Diccionario con estadísticas
        """
        return self.memory_manager.get_stats()
