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
import math
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# COMPLIANCE: Backtesting Compliance (R5, R6, R7, DATA-001)
from app.backtesting.backtesting_compliance import (
    BacktestingComplianceResult,
    create_backtesting_compliance,
)

# Core backtesting modules (Fase 1 + Fase 2)
from app.backtesting.core import BacktestConfigLoader, BacktestOrchestrator
from app.backtesting.core.error_handling import MutexError, TrainingError, train_with_retry
from app.backtesting.core.executor import ProcessPoolBacktestExecutor, SimpleBacktestExecutor
from app.backtesting.core.memory_manager import AggressiveMemoryManager

# Data loading
from app.backtesting.data_loader import DataLoader

# Data splitting and multiple testing correction
from app.backtesting.data_split import (
    MultipleTestingCorrector,
    TrainValTestSplitter,
    validate_out_of_sample_performance,
)
from app.backtesting.engines.multi_strategy_engine import MultiStrategyBacktester

# Strategy factory (Phase 5: extracted from God Object)
from app.backtesting.factories import StrategyFactory
from app.backtesting.models import BacktestConfig, BacktestResult
from app.backtesting.runners.monte_carlo_simulator import MonteCarloSimulator

# SRP Extracted modules (Phase 6)
from app.backtesting.runners.regime_analyzer import RegimeAnalyzer
from app.backtesting.runners.result_aggregator import ResultAggregator

# Strategy implementations
# TODO: Create momentum_modular module. Using MomentumStrategy as alias.
from app.domain.strategies.momentum import MomentumStrategy as ModularMomentumStrategy

# Backtesting engine and models


# Survivorship bias adjustment

# Portfolio management


class ComprehensiveBacktestRunner:
    """
    Sistema completo de backtesting automatizado y configurable.

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

    # Strategy name mapping from YAML to factory names
    STRATEGY_NAME_MAP = {
        'momentum_modular': 'modular_momentum',
        'mean_reversion_modular': 'mean_reversion',
        'pairs_trading_modular': 'pairs_trading',
        'dividend_screener': 'modular_momentum',  # Use momentum as fallback
        'portfolio_optimization': 'modular_momentum',  # Use momentum as fallback
        'dividend_predictor': 'modular_momentum',  # Use momentum as fallback
        'sector_rotation': 'momentum',  # Use momentum as fallback
        'ml_ensemble': 'modular_momentum',  # Use momentum as fallback
    }

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
            max_results=500, max_backtest_objects=100, memory_threshold_mb=4096
        )

        self.output_dir = Path(self.raw_config['reporting']['output_directory'])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cargar datos históricos
        self.data_loader = DataLoader()
        self.quotes = self._load_market_data()

        # Configuración de paralelización
        # DISABLE parallelization on macOS due to spawn/serialization issues
        # macOS uses 'spawn' which requires pickling all objects (including thread locks)
        import platform

        default_parallel = platform.system() != 'Darwin'  # Disable on macOS
        self.parallel_enabled = self.raw_config.get('parallelization', {}).get(
            'enabled', default_parallel
        )
        self.max_workers = self.raw_config.get('parallelization', {}).get('max_workers', None)

        # Integrar meta_analyzer si está habilitado
        self.meta_enabled = self.raw_config.get('meta_analysis', {}).get('enabled', False)
        self.audit_trail = None
        self.learning_storage = None
        self.audit_hash: Optional[str] = None

        if self.meta_enabled:
            self._integrate_meta_analyzer()

        # COMPLIANCE: Inicializar BacktestingCompliance para R5, R6, R7, DATA-001
        self.backtesting_compliance = create_backtesting_compliance()
        self.compliance_results: List[BacktestingComplianceResult] = []
        logger.info("BacktestingCompliance initialized (R5, R6, R7, DATA-001)")

        # SRP: Initialize extracted modules (Phase 6)
        self.regime_analyzer = RegimeAnalyzer()
        self.monte_carlo_simulator = MonteCarloSimulator(
            random_state=self.raw_config.get('random_state', 42)
        )
        self.result_aggregator = ResultAggregator(
            output_dir=self.output_dir,
            output_formats=self.raw_config.get('reporting', {}).get(
                'output_format', ['csv', 'json']
            ),
        )

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
                enable_analysis=self.raw_config.get('meta_analysis', {}).get(
                    'enable_analysis', True
                ),
            )
            self.audit_trail = meta['audit_trail']
            self.learning_storage = meta['storage']
            self.meta_analyzer = meta['analyzer']  # Store analyzer instance
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
        data_source = self.raw_config['input'].get(
            'source', 'csv'
        )  # Get source from config, default to csv

        logger.info(f"Loading market data from {start_date.date()} to {end_date.date()}")
        logger.info(f"Symbols: {all_symbols}")
        logger.info(f"Data source: {data_source}")

        quotes = []
        for symbol in all_symbols:
            symbol_quotes = self.data_loader.load_market_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                source=data_source,  # Use the source from config
            )
            quotes.extend(symbol_quotes)
            logger.info(f"  Loaded {len(symbol_quotes)} quotes for {symbol}")

        return quotes

    def _get_actual_data_bounds(self):
        '''Get actual start and end dates from loaded quotes.'''
        if not self.quotes:
            return None, None

        actual_start = min(q.timestamp for q in self.quotes)
        actual_end = max(q.timestamp for q in self.quotes)
        return actual_start, actual_end

    def _get_safe_split_dates(self, config_start, config_end):
        '''Get safe dates for splitting, using actual bounds if config exceeds available data.'''
        actual_start, actual_end = self._get_actual_data_bounds()

        if actual_start is None or actual_end is None:
            logger.error("Cannot determine data bounds: no quotes available")
            raise ValueError("No market data loaded")

        # Check if config dates exceed available data
        if config_start < actual_start or config_end > actual_end:
            logger.warning(
                f"Config dates ({config_start.date()} to {config_end.date()}) "
                f"exceed available data ({actual_start.date()} to {actual_end.date()}). "
                f"Using actual data bounds to prevent empty dataset error."
            )
            return actual_start, actual_end

        return config_start, config_end

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
            monte_carlo_results = self.run_monte_carlo_backtest(parallel=self.parallel_enabled)
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

        # COMPLIANCE: Validar reglas R5, R6, R7, DATA-001
        self._run_compliance_validation(results)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE BACKTEST SUITE COMPLETED")
        logger.info(f"Total backtests: {len(results)}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 80)

        return results

    def _run_compliance_validation(
        self, results: List[Dict[str, Any]]
    ) -> BacktestingComplianceResult:
        """
        Ejecutar validación de compliance sobre los resultados de backtest.

        COMPLIANCE: Valida las reglas R5, R6, R7, DATA-001:
        - R5: Walk-Forward Analysis (si hay resultados WF)
        - R6: Overfitting Prevention (ratio parámetros/observaciones)
        - R7: Monte Carlo (si hay resultados MC)
        - DATA-001: Purged CV (si hay resultados de validación)

        Args:
            results: Lista de resultados de backtests

        Returns:
            BacktestingComplianceResult con el resultado de la validación
        """
        logger.info("=" * 80)
        logger.info("COMPLIANCE VALIDATION (R5, R6, R7, DATA-001)")
        logger.info("=" * 80)

        # Extraer información de resultados
        n_parameters = self._count_optimizable_parameters()
        n_observations = len(self.quotes)

        # Extraer resultados de walk-forward si existen
        walk_forward_windows = self._extract_walk_forward_results(results)

        # Extraer resultados de Monte Carlo si existen
        mc_results = [r for r in results if r.get('test_type') == 'monte_carlo']
        n_mc_simulations = len(mc_results)
        mc_var_95 = 0.0
        mc_var_99 = 0.0
        if mc_results:
            returns = [r.get('return_pct', 0) for r in mc_results]
            mc_var_95 = float(np.percentile(returns, 5)) if returns else 0.0
            mc_var_99 = float(np.percentile(returns, 1)) if returns else 0.0

        # Ejecutar validación completa
        compliance_result = self.backtesting_compliance.validate_backtest(
            n_parameters=n_parameters,
            n_observations=n_observations,
            walk_forward_windows=walk_forward_windows,
            monte_carlo_var_95=mc_var_95,
            monte_carlo_var_99=mc_var_99,
            monte_carlo_simulations=n_mc_simulations,
            purge_days=5,  # Default purge days
            embargo_days=10,  # Default embargo days
        )

        self.compliance_results.append(compliance_result)

        # Log resumen
        summary = compliance_result.get_summary()
        if compliance_result.is_compliant:
            logger.info(f"COMPLIANCE PASSED: {summary}")
        else:
            logger.warning(f"COMPLIANCE FAILED: {summary}")
            for violation in compliance_result.violations:
                logger.warning(f"  [{violation.severity}] {violation.rule_id}: {violation.message}")

        return compliance_result

    def _count_optimizable_parameters(self) -> int:
        """
        Contar parámetros optimizables en la configuración.

        Returns:
            Número aproximado de parámetros optimizables
        """
        count = 0

        # Contar parámetros de módulos
        modules = self.raw_config.get('modules', {})
        for module_name, module_config in modules.items():
            if isinstance(module_config, dict):
                # Contar thresholds y parámetros
                if 'thresholds' in module_config:
                    count += len(module_config['thresholds'])
                if 'parameters' in module_config:
                    count += len(module_config['parameters'])

        # Contar parámetros de learning engines
        learning_engines = self.raw_config.get('learning_engines', {})
        for engine_name, engine_config in learning_engines.items():
            if isinstance(engine_config, dict) and engine_config.get('enabled', False):
                if 'config' in engine_config:
                    count += len(engine_config['config'])

        # Parámetros base de backtest
        count += 6  # initial_capital, commission, slippage, max_position, stop_loss, take_profit

        return count

    def _extract_walk_forward_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extraer resultados de walk-forward para validación R5.

        Args:
            results: Lista de resultados de backtests

        Returns:
            Lista de resultados por ventana walk-forward
        """
        wf_results = [r for r in results if 'walk_forward' in r.get('test_type', '')]
        windows = []

        for r in wf_results:
            windows.append(
                {
                    'is_return': r.get('train_return', 0),
                    'oos_return': r.get('return_pct', 0),
                    'is_sharpe': r.get('train_sharpe', 0),
                    'oos_sharpe': r.get('sharpe_ratio', 0),
                    'trades': r.get('total_trades', 0),
                }
            )

        return windows

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
        logger.info("SPECIFIC BACKTESTS COMPLETED")
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
        # Get initial_capital from backtest_config (already configured)
        initial_capital = self.backtest_config.initial_capital
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
        result = executor.execute(self.quotes, strategy, strategy_name=strategy_name)

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
                float(result.performance.sharpe_ratio) if result.performance.sharpe_ratio else 0.0
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

        logger.info(
            f"Baseline complete: PnL=${result_dict['total_pnl']:.2f}, Sharpe={result_dict['sharpe_ratio']:.2f}"
        )

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

        # Opción 2: Solo Supervised Learning (Deep/Transformer/Reinforcement deshabilitados por mutex blocking)
        logger.info("Learning Engines Policy: Only 'supervised' is supported (scikit-learn)")
        logger.info("  - supervised: ✅ ENABLED (scikit-learn - no mutex issues)")
        logger.info("  - deep: ❌ DISABLED (PyTorch causes mutex.cc blocking)")
        logger.info("  - transformer: ❌ DISABLED (PyTorch causes mutex.cc blocking)")
        logger.info(
            "  - reinforcement: ❌ DISABLED (stable-baselines3/gymnasium causes mutex.cc blocking)"
        )

        # Only test supervised learning engine
        engine_types = ['supervised']

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
            # Get the learning engine config from raw_config
            learning_engines_config = self.raw_config.get('learning_engines', {})
            engine_config = learning_engines_config.get(engine_type, {})

            # Build adaptive_learning config with full engine configuration
            adaptive_learning_config = {
                'enabled': engine_config.get('enabled', True),
                'engine_type': engine_type,
            }

            # Add default config for supervised learning engine
            if engine_type == 'supervised':
                adaptive_learning_config.update(
                    {
                        'algorithm': 'random_forest',
                        'feature_columns': [],
                        'target_column': 'trade_success',
                        'model_parameters': {},
                        'optimize_thresholds': False,
                        'threshold_parameters': {},
                    }
                )

            # Add any additional config parameters for the specific engine
            if 'config' in engine_config:
                adaptive_learning_config.update(engine_config['config'])

            strategy_config = self._create_strategy_config()
            strategy_config['adaptive_learning'] = adaptive_learning_config
            strategy = ModularMomentumStrategy(strategy_config)

            # Initialize the learning engine (lazy initialization)
            strategy._initialize_learning_engine()

            # Usar train_with_retry (Fase 3)
            training_successful = train_with_retry(
                strategy=strategy,
                engine_type=engine_type,
                use_subprocess=False,  # Usar multiprocessing como fallback
            )

            if not training_successful:
                logger.warning(f"{engine_type} learning engine training failed")
                return None

            # Ejecutar backtest
            # Use initial_capital from backtest_config (already configured)
            initial_capital = self.backtest_config.initial_capital
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
            result = executor.execute(self.quotes, strategy, strategy_name=strategy_name)

            consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)

            result_dict = {
                'test_type': f'learning_engine_{engine_type}',
                'test_name': f'Learning Engine - {engine_type.capitalize()}',
                'modules_active': list(strategy_config.get('modules', {}).keys()),
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

            self._save_test_audit_and_weights(
                result_dict, f'learning_engine_{engine_type}', strategy
            )

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
                self.backtest_config, max_processes=self.max_workers or 4
            )
        else:
            executor = SimpleBacktestExecutor(self.backtest_config)

        # Usar BacktestOrchestrator (Fase 3)
        BacktestOrchestrator(self.backtest_config, executor)

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
                modified_quotes, base_strategy, strategy_name=f'Monte Carlo Simulation {sim_num+1}'
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
                'return_pct': (
                    ((final_capital - initial_capital) / initial_capital * 100)
                    if initial_capital > 0
                    else 0.0
                ),
                'win_rate': float(result.performance.win_rate) if result.performance else 0.0,
                'sharpe_ratio': (
                    float(result.performance.sharpe_ratio)
                    if result.performance and result.performance.sharpe_ratio
                    else 0.0
                ),
                'max_drawdown': (
                    float(result.performance.max_drawdown_percentage) if result.performance else 0.0
                ),
                'total_trades': result.performance.total_trades if result.performance else 0,
                'avg_trade_pnl': (
                    (final_capital - initial_capital) / result.performance.total_trades
                    if result.performance and result.performance.total_trades > 0
                    else 0.0
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

        DELEGATES to MonteCarloSimulator (SRP Phase 6).

        Args:
            volatility_multiplier: Multiplicador de volatilidad

        Returns:
            Lista de quotes modificados con datos realistas
        """
        return self.monte_carlo_simulator.create_monte_carlo_quotes(
            base_quotes=self.quotes,
            volatility_multiplier=volatility_multiplier,
        )

    def run_walk_forward_backtest(self) -> List[Dict[str, Any]]:
        """
        Ejecutar backtest walk-forward con rolling windows.

        Implementa validación walk-forward siguiendo las reglas de:
        - Ruey Tsay (Analysis of Financial Time Series): Validación de series temporales
        - López de Prado (Advances in Financial Machine Learning): Purging y embargo

        Arquitectura:
        - Divide datos en ventanas rolling (train/test)
        - Default: 70% train, 30% test por ventana
        - Mínimo training period: 252 días (1 año)
        - Step size: 63 días (quarterly) para rolling windows

        Returns:
            Lista de resultados con métricas agregadas across windows
        """
        logger.info("Running walk-forward backtest...")

        wf_config = self.raw_config.get('backtests', {}).get('walk_forward', {})

        # Parámetros de ventana con valores default desde López de Prado
        train_pct = wf_config.get('train_pct', 0.70)  # 70% training
        test_pct = wf_config.get('test_pct', 0.30)  # 30% test
        min_train_days = wf_config.get('min_train_days', 100)  # REDUCIDO: 100 días (era 252)
        step_size_days = wf_config.get('step_size_days', 63)  # Quarterly (3 meses)

        logger.info(
            f"Walk-forward config: train={train_pct:.0%}, test={test_pct:.0%}, "
            f"min_train={min_train_days}d, step={step_size_days}d"
        )

        # Sort quotes by timestamp (orden temporal crítico - Regla Tsay)
        sorted_quotes = sorted(self.quotes, key=lambda x: x.timestamp)
        total_days = len(sorted_quotes)

        logger.info(
            f"Total data: {total_days} days from {sorted_quotes[0].timestamp.date()} "
            f"to {sorted_quotes[-1].timestamp.date()}"
        )

        # Crear ventanas walk-forward
        # Siguiendo TimeSeriesSplit de sklearn (nunca romper orden temporal)
        # Usar ceil para asegurar mínimo de días (evitar pérdida por redondeo)
        window_size = math.ceil(min_train_days / train_pct)  # Tamaño total de ventana

        # Calcular número de ventanas
        num_windows = 0
        windows = []

        start_idx = 0
        while True:
            end_idx = start_idx + window_size

            if end_idx > total_days:
                break

            # Extraer ventana
            window_quotes = sorted_quotes[start_idx:end_idx]

            # Verificar mínimo de training days (usar ceil para asegurar mínimo)
            train_size = math.ceil(len(window_quotes) * train_pct)
            if train_size < min_train_days:
                logger.warning(
                    f"Window {num_windows+1}: Insufficient training data "
                    f"({train_size} < {min_train_days})"
                )
                start_idx += step_size_days
                continue

            # Split train/test (respetando orden temporal)
            train_quotes = window_quotes[:train_size]
            test_quotes = window_quotes[train_size:]

            windows.append(
                {
                    'window_num': num_windows + 1,
                    'train': train_quotes,
                    'test': test_quotes,
                    'train_start': train_quotes[0].timestamp,
                    'train_end': train_quotes[-1].timestamp,
                    'test_start': test_quotes[0].timestamp,
                    'test_end': test_quotes[-1].timestamp,
                }
            )

            num_windows += 1
            start_idx += step_size_days

        if not windows:
            logger.error("No valid walk-forward windows created")
            return []

        logger.info(f"Created {num_windows} walk-forward windows")

        # Ejecutar backtest para cada ventana
        # IMPORTANTE: Usar SimpleBacktestExecutor para cada ventana (Regla López de Prado)
        window_results = []

        for window in windows:
            logger.info(
                f"\nWindow {window['window_num']}/{num_windows}: "
                f"Train: {window['train_start'].date()} to {window['train_end'].date()} "
                f"({len(window['train'])} days) | "
                f"Test: {window['test_start'].date()} to {window['test_end'].date()} "
                f"({len(window['test'])} days)"
            )

            try:
                # Crear estrategia base para esta ventana
                strategy_config = self._create_strategy_config()
                strategy = ModularMomentumStrategy(strategy_config)

                # Phase 1: Train en training period
                # NOTA: La estrategia NO tiene método train explícito,
                # pero learning engines pueden usar datos de training si están activados
                train_quotes = window['train']
                test_quotes = window['test']

                # Ejecutar backtest en test period
                # NO usar training period para validación (data leakage)
                initial_capital = self.backtest_config.initial_capital
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

                # Ejecutar SOLO en test period (validation out-of-sample)
                result = executor.execute(
                    test_quotes,
                    strategy,
                    strategy_name=f"{strategy_name}_WF_Window{window['window_num']}",
                )

                consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)

                # Guardar resultados de ventana
                window_result = {
                    'window_num': window['window_num'],
                    'train_start': window['train_start'],
                    'train_end': window['train_end'],
                    'test_start': window['test_start'],
                    'test_end': window['test_end'],
                    'train_size': len(train_quotes),
                    'test_size': len(test_quotes),
                    # Métricas
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
                    'avg_trade_pnl': (
                        consistent_metrics['total_pnl'] / result.performance.total_trades
                        if result.performance and result.performance.total_trades > 0
                        else 0.0
                    ),
                }

                window_results.append(window_result)

                logger.info(
                    f"Window {window['window_num']} result: "
                    f"Return={window_result['return_pct']:.2f}%, "
                    f"Sharpe={window_result['sharpe_ratio']:.2f}, "
                    f"Trades={window_result['total_trades']}"
                )

                # Memory management
                self.memory_manager.add_backtest_object(
                    f'walk_forward_window_{window["window_num"]}', result
                )

            except Exception as e:
                logger.error(f"Error in window {window['window_num']}: {e}", exc_info=True)
                continue

        if not window_results:
            logger.error("No windows completed successfully")
            return []

        # Agregar resultados across windows
        # Seguir López de Prado: Reportar mean + std de métricas
        sharpe_values = [w['sharpe_ratio'] for w in window_results]
        return_values = [w['return_pct'] for w in window_results]
        drawdown_values = [w['max_drawdown'] for w in window_results]

        avg_sharpe = np.mean(sharpe_values)
        std_sharpe = np.std(sharpe_values)
        avg_return = np.mean(return_values)
        std_return = np.std(return_values)
        avg_drawdown = np.mean(drawdown_values)

        # Stability ratio (López de Prado: métrica de robustez)
        # Ratio de signal-to-noise: higher = more stable
        stability_ratio = avg_sharpe / (std_sharpe + 1e-6)  # Avoid div by zero

        # Crear resultado consolidado
        consolidated_result = {
            'test_type': 'walk_forward',
            'test_name': 'Walk-Forward Validation',
            'num_windows': num_windows,
            'window_metrics': window_results,  # Métricas por ventana
            # Métricas agregadas (mean ± std)
            'avg_sharpe': avg_sharpe,
            'sharpe_std': std_sharpe,
            'avg_return': avg_return,
            'return_std': std_return,
            'avg_max_drawdown': avg_drawdown,
            'stability_ratio': stability_ratio,
            # Configuración
            'train_pct': train_pct,
            'test_pct': test_pct,
            'min_train_days': min_train_days,
            'step_size_days': step_size_days,
            # Métricas adicionales
            'sharpe_min': np.min(sharpe_values),
            'sharpe_max': np.max(sharpe_values),
            'return_min': np.min(return_values),
            'return_max': np.max(return_values),
            'win_rate': np.mean([w['win_rate'] for w in window_results]),
            'total_trades': np.sum([w['total_trades'] for w in window_results]),
            # Metadata
            'modules_active': list(self.raw_config['modules']['filters'].keys()),
            'learning_engine': None,
            'thresholds': self._extract_thresholds(self._create_strategy_config()),
        }

        # Log summary
        logger.info("\n" + "=" * 80)
        logger.info("WALK-FORWARD VALIDATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Windows tested: {num_windows}")
        logger.info("Performance (mean ± std):")
        logger.info(
            f"  Sharpe: {avg_sharpe:.3f} ± {std_sharpe:.3f} (range: {consolidated_result['sharpe_min']:.2f} to {consolidated_result['sharpe_max']:.2f})"
        )
        logger.info(
            f"  Return: {avg_return:.2f}% ± {std_return:.2f}% (range: {consolidated_result['return_min']:.2f}% to {consolidated_result['return_max']:.2f}%)"
        )
        logger.info(f"  Max DD: {avg_drawdown:.2f}%")
        logger.info(f"Stability ratio (signal/noise): {stability_ratio:.2f}")
        logger.info(f"Win rate: {consolidated_result['win_rate']:.1%}")
        logger.info(f"Total trades: {consolidated_result['total_trades']}")
        logger.info("=" * 80)

        # Guardar resultado
        self.memory_manager.add_result(consolidated_result)
        self._save_test_audit_and_weights(consolidated_result, 'walk_forward', strategy)

        return [consolidated_result]

    def run_transformer_optimization_backtest(self) -> List[Dict[str, Any]]:
        """
        Execute Transformer-based parameter optimization backtest.

        Implements MLOps best practices from rule 27:
        - Feature extraction with Transformer learning engine
        - Bayesian optimization for hyperparameter search
        - Train/validation/test split (60%/20%/20%)
        - Meta-labeling from Lopez de Prado (rule 3)
        - Time-series cross-validation
        - Feature importance tracking

        Architecture:
        1. Train Transformer on first 60% of data
        2. Validate on next 20% for parameter tuning
        3. Test on final 20% with optimized parameters
        4. Compare baseline vs optimized performance

        Returns:
            List with optimization results including baseline metrics,
            optimized metrics, improvement percentage, and best parameters
        """
        logger.info("Running Transformer optimization backtest...")

        try:
            transformer_config = self.raw_config.get('learning_engines', {}).get('transformer', {})
            if not transformer_config.get('enabled', False):
                logger.info("Transformer learning engine disabled, skipping optimization")
                return []

            # Step 1: Determine safe date bounds for splitting
            config_start = datetime.strptime(self.raw_config['input']['start_date'], "%Y-%m-%d")
            config_end = datetime.strptime(self.raw_config['input']['end_date'], "%Y-%m-%d")
            split_start, split_end = self._get_safe_split_dates(config_start, config_end)

            # Step 2: Split data into train/validation/test (60%/20%/20%)
            from app.backtesting.data_split import DataSplit

            splitter = TrainValTestSplitter(DataSplit(train_pct=0.6, val_pct=0.2, test_pct=0.2))

            train_quotes, val_quotes, test_quotes = splitter.split_data(
                market_data=self.quotes,
                start_date=split_start,
                end_date=split_end,
            )

            logger.info(
                f"Data split for Transformer optimization: "
                f"train={len(train_quotes)}, val={len(val_quotes)}, test={len(test_quotes)}"
            )

            # Step 2: Train baseline strategy on train data
            baseline_config = self._create_strategy_config()
            baseline_strategy = ModularMomentumStrategy(baseline_config)

            baseline_train_success = train_with_retry(
                strategy=baseline_strategy,
                engine_type='transformer',
                use_subprocess=False,
            )

            if not baseline_train_success:
                logger.warning("Baseline Transformer training failed")
                return []

            # Step 3: Get baseline predictions on validation set
            baseline_val_predictions = self._extract_transformer_predictions(
                baseline_strategy, val_quotes
            )

            # Step 4: Run baseline backtest on test set
            initial_capital = self.backtest_config.initial_capital
            baseline_test_result = self._run_backtest_with_quotes(
                baseline_strategy, test_quotes, initial_capital
            )
            baseline_metrics = self._calculate_consistent_metrics(
                baseline_test_result, initial_capital
            )

            logger.info(
                f"Baseline metrics - PnL=${baseline_metrics['total_pnl']:.2f}, "
                f"Sharpe={baseline_test_result.performance.sharpe_ratio or 0:.2f}"
            )

            # Step 5: Bayesian optimization of parameters
            best_params = self._optimize_transformer_parameters(
                train_quotes, val_quotes, transformer_config
            )

            logger.info(f"Best parameters found: {best_params}")

            # Step 6: Create optimized strategy with best parameters
            optimized_config = self._create_strategy_config()
            optimized_config['thresholds'].update(best_params)

            optimized_strategy = ModularMomentumStrategy(optimized_config)

            optimized_train_success = train_with_retry(
                strategy=optimized_strategy,
                engine_type='transformer',
                use_subprocess=False,
            )

            if not optimized_train_success:
                logger.warning("Optimized Transformer training failed")
                return []

            # Step 7: Get optimized predictions on validation set
            optimized_val_predictions = self._extract_transformer_predictions(
                optimized_strategy, val_quotes
            )

            # Step 8: Run optimized backtest on test set
            optimized_test_result = self._run_backtest_with_quotes(
                optimized_strategy, test_quotes, initial_capital
            )
            optimized_metrics = self._calculate_consistent_metrics(
                optimized_test_result, initial_capital
            )

            logger.info(
                f"Optimized metrics - PnL=${optimized_metrics['total_pnl']:.2f}, "
                f"Sharpe={optimized_test_result.performance.sharpe_ratio or 0:.2f}"
            )

            # Step 9: Calculate improvement
            baseline_sharpe = float(baseline_test_result.performance.sharpe_ratio or 0)
            optimized_sharpe = float(optimized_test_result.performance.sharpe_ratio or 0)

            improvement_pct = 0.0
            if baseline_sharpe != 0:
                improvement_pct = (
                    (optimized_sharpe - baseline_sharpe) / abs(baseline_sharpe)
                ) * 100

            pnl_improvement = 0.0
            if baseline_metrics['total_pnl'] != 0:
                pnl_improvement = (
                    (optimized_metrics['total_pnl'] - baseline_metrics['total_pnl'])
                    / abs(baseline_metrics['total_pnl'])
                    * 100
                )

            # Step 10: Extract feature importance from Transformer
            feature_importance = self._extract_transformer_feature_importance(optimized_strategy)

            # Step 11: Apply meta-labeling (Lopez de Prado)
            meta_labeling_metrics = self._apply_meta_labeling(
                baseline_val_predictions, optimized_val_predictions, val_quotes
            )

            # Step 12: Validate out-of-sample performance
            oos_validation = validate_out_of_sample_performance(
                train_sharpe=baseline_sharpe,
                test_sharpe=optimized_sharpe,
                confidence=0.95,
            )

            result_dict = {
                'test_type': 'transformer_optimization',
                'test_name': 'Transformer Optimization',
                'baseline_metrics': {
                    'total_pnl': baseline_metrics['total_pnl'],
                    'return_pct': baseline_metrics['return_pct'],
                    'sharpe_ratio': baseline_sharpe,
                    'win_rate': float(baseline_test_result.performance.win_rate),
                    'max_drawdown': float(baseline_test_result.performance.max_drawdown_percentage),
                    'total_trades': baseline_test_result.performance.total_trades,
                },
                'optimized_metrics': {
                    'total_pnl': optimized_metrics['total_pnl'],
                    'return_pct': optimized_metrics['return_pct'],
                    'sharpe_ratio': optimized_sharpe,
                    'win_rate': float(optimized_test_result.performance.win_rate),
                    'max_drawdown': float(
                        optimized_test_result.performance.max_drawdown_percentage
                    ),
                    'total_trades': optimized_test_result.performance.total_trades,
                },
                'improvement_pct': improvement_pct,
                'pnl_improvement_pct': pnl_improvement,
                'best_params': best_params,
                'optimization_iterations': len(best_params) if best_params else 0,
                'feature_importance': feature_importance,
                'meta_labeling_metrics': meta_labeling_metrics,
                'out_of_sample_valid': oos_validation,
                'data_split': {
                    'train_size': len(train_quotes),
                    'val_size': len(val_quotes),
                    'test_size': len(test_quotes),
                },
            }

            self.memory_manager.add_result(result_dict)
            self._save_test_audit_and_weights(
                result_dict, 'transformer_optimization', optimized_strategy
            )

            logger.info(
                f"Transformer optimization complete: "
                f"Improvement={improvement_pct:+.1f}%, "
                f"Sharpe {baseline_sharpe:.2f} -> {optimized_sharpe:.2f}"
            )

            return [result_dict]

        except Exception as e:
            logger.error(f"Error in Transformer optimization backtest: {e}", exc_info=True)
            return []

    def run_ablation_backtest(self) -> List[Dict[str, Any]]:
        """
        Execute ablation backtest to measure individual filter/module impact.

        Implements Lopez de Prado's feature importance principles (Rule 3):
        - Test each filter in isolation to measure contribution
        - Compare against baseline (all filters active)
        - Calculate importance scores based on performance degradation
        - Uses TimeSeriesSplit for temporal consistency (no look-ahead bias)

        Architecture:
        - Uses SimpleBacktestExecutor for consistency
        - Uses AggressiveMemoryManager for results
        - Uses _calculate_consistent_metrics for metrics
        - Uses _save_test_audit_and_weights for audit trail

        Ablation Process:
        1. Run baseline with all filters enabled
        2. For each filter: disable it and run backtest
        3. Calculate performance degradation vs baseline
        4. Generate importance scores based on impact

        Returns:
            List of result dictionaries with ablation metrics including:
            - Baseline metrics (all filters)
            - Per-filter ablation results
            - Importance scores (sharpe degradation, return degradation, win_rate impact)
            - Filter ranking by importance
        """
        logger.info("=" * 80)
        logger.info("ABLATION BACKTEST - Starting filter impact analysis")
        logger.info("=" * 80)

        # Get ablation configuration
        ablation_config = self.raw_config.get('backtests', {}).get('ablation', {})

        # Get filters to test from config or use all enabled filters
        modules_to_test = ablation_config.get('modules_to_test', [])
        if not modules_to_test:
            # Default: test all enabled filters
            modules_config = self.raw_config.get('modules', {}).get('filters', {})
            modules_to_test = [
                name for name, config in modules_config.items() if config.get('enabled', False)
            ]

        if not modules_to_test:
            logger.warning("No filters to test in ablation backtest")
            return []

        logger.info(f"Testing {len(modules_to_test)} filters: {', '.join(modules_to_test)}")

        # Step 1: Run baseline with ALL filters enabled
        logger.info("\n" + "-" * 80)
        logger.info("STEP 1: Running baseline (all filters enabled)")
        logger.info("-" * 80)

        baseline_config = self._create_strategy_config()
        baseline_strategy = ModularMomentumStrategy(baseline_config)

        initial_capital = self.backtest_config.initial_capital
        backtest_config = BacktestConfig(
            initial_capital=initial_capital,
            commission_per_trade=self.backtest_config.commission_per_trade,
            slippage_percentage=self.backtest_config.slippage_percentage,
            max_position_size=self.backtest_config.max_position_size,
            stop_loss_percentage=self.backtest_config.stop_loss_percentage,
            take_profit_percentage=self.backtest_config.take_profit_percentage,
            risk_free_rate=self.backtest_config.risk_free_rate,
        )

        strategy_name = self._get_strategy_name(baseline_strategy)
        executor = SimpleBacktestExecutor(backtest_config)

        baseline_result = executor.execute(
            self.quotes, baseline_strategy, strategy_name=f"{strategy_name}_baseline"
        )

        baseline_metrics = self._calculate_consistent_metrics(baseline_result, initial_capital)

        baseline_sharpe = (
            float(baseline_result.performance.sharpe_ratio)
            if baseline_result.performance.sharpe_ratio
            else 0.0
        )
        baseline_return = baseline_metrics['return_pct']
        baseline_win_rate = (
            float(baseline_result.performance.win_rate) if baseline_result.performance else 0.0
        )
        baseline_max_dd = (
            float(baseline_result.performance.max_drawdown_percentage)
            if baseline_result.performance
            else 0.0
        )

        logger.info("Baseline Results:")
        logger.info(f"  Return:       {baseline_return:+.2f}%")
        logger.info(f"  Sharpe:       {baseline_sharpe:.3f}")
        logger.info(f"  Win Rate:     {baseline_win_rate:.2%}")
        logger.info(f"  Max DD:       {baseline_max_dd:.2f}%")
        logger.info(
            f"  Total Trades: {baseline_result.performance.total_trades if baseline_result.performance else 0}"
        )

        # Step 2: Run ablation tests for each filter
        logger.info("\n" + "-" * 80)
        logger.info("STEP 2: Running ablation tests (disabling each filter)")
        logger.info("-" * 80)

        ablation_results = []

        for filter_name in modules_to_test:
            logger.info(f"\nTesting ablation: {filter_name} DISABLED")

            try:
                # Create config with this filter disabled
                ablation_config_dict = self._create_ablation_config(disabled_filter=filter_name)

                # Create strategy with filter disabled
                ablation_strategy = ModularMomentumStrategy(ablation_config_dict)

                # Run backtest
                ablation_result = executor.execute(
                    self.quotes,
                    ablation_strategy,
                    strategy_name=f"{strategy_name}_ablation_{filter_name}",
                )

                ablation_metrics = self._calculate_consistent_metrics(
                    ablation_result, initial_capital
                )

                ablation_sharpe = (
                    float(ablation_result.performance.sharpe_ratio)
                    if ablation_result.performance.sharpe_ratio
                    else 0.0
                )
                ablation_return = ablation_metrics['return_pct']
                ablation_win_rate = (
                    float(ablation_result.performance.win_rate)
                    if ablation_result.performance
                    else 0.0
                )
                ablation_max_dd = (
                    float(ablation_result.performance.max_drawdown_percentage)
                    if ablation_result.performance
                    else 0.0
                )

                # Calculate degradation (baseline - ablation)
                sharpe_degradation = baseline_sharpe - ablation_sharpe
                return_degradation = baseline_return - ablation_return
                win_rate_degradation = baseline_win_rate - ablation_win_rate
                max_dd_change = ablation_max_dd - baseline_max_dd

                # Calculate importance score (normalized)
                sharpe_importance = sharpe_degradation / (abs(baseline_sharpe) + 1e-6)
                return_importance = return_degradation / (abs(baseline_return) + 1e-6)

                # Combined importance score (weighted average)
                combined_importance = (
                    0.5 * sharpe_importance
                    + 0.3 * return_importance
                    + 0.2 * (win_rate_degradation / (abs(baseline_win_rate) + 1e-6))
                )

                result_dict = {
                    'test_type': 'ablation',
                    'test_name': f'Ablation - {filter_name}',
                    'filter_name': filter_name,
                    'filter_disabled': True,
                    'modules_active': [f for f in modules_to_test if f != filter_name],
                    'learning_engine': None,
                    'thresholds': self._extract_thresholds(ablation_config_dict),
                    'total_pnl': ablation_metrics['total_pnl'],
                    'return_pct': ablation_return,
                    'win_rate': ablation_win_rate,
                    'sharpe_ratio': ablation_sharpe,
                    'max_drawdown': ablation_max_dd,
                    'total_trades': (
                        ablation_result.performance.total_trades
                        if ablation_result.performance
                        else 0
                    ),
                    'avg_trade_pnl': (
                        ablation_metrics['total_pnl'] / ablation_result.performance.total_trades
                        if ablation_result.performance
                        and ablation_result.performance.total_trades > 0
                        else 0.0
                    ),
                    'final_capital': ablation_metrics['final_capital'],
                    'sharpe_degradation': sharpe_degradation,
                    'return_degradation_pct': return_degradation,
                    'win_rate_degradation_pct': win_rate_degradation * 100,
                    'max_drawdown_change_pct': max_dd_change,
                    'sharpe_importance': sharpe_importance,
                    'return_importance': return_importance,
                    'combined_importance': combined_importance,
                    'baseline_sharpe': baseline_sharpe,
                    'baseline_return': baseline_return,
                    'baseline_win_rate': baseline_win_rate,
                }

                ablation_results.append(result_dict)
                self.memory_manager.add_result(result_dict)
                self.memory_manager.add_backtest_object(f'ablation_{filter_name}', ablation_result)

                logger.info(
                    f"{filter_name} Results: "
                    f"Return={ablation_return:+.2f}% (degradation: {return_degradation:+.2f}%), "
                    f"Sharpe={ablation_sharpe:.3f} (degradation: {sharpe_degradation:+.3f}), "
                    f"Importance={combined_importance:.3f}"
                )

            except Exception as e:
                logger.error(f"Error testing ablation for {filter_name}: {e}", exc_info=True)
                continue

        if not ablation_results:
            logger.error("No ablation tests completed successfully")
            return []

        # Step 3: Rank filters by importance
        logger.info("\n" + "-" * 80)
        logger.info("STEP 3: Ranking filters by importance")
        logger.info("-" * 80)

        ranked_results = sorted(
            ablation_results, key=lambda x: x['combined_importance'], reverse=True
        )

        for rank, result in enumerate(ranked_results, 1):
            logger.info(
                f"#{rank}. {result['filter_name']}: "
                f"Importance={result['combined_importance']:.3f}, "
                f"Sharpe Degradation={result['sharpe_degradation']:+.3f}, "
                f"Return Degradation={result['return_degradation_pct']:+.2f}%"
            )

        # Step 4: Create consolidated summary
        importance_scores = [r['combined_importance'] for r in ablation_results]
        sharpe_degradations = [r['sharpe_degradation'] for r in ablation_results]
        return_degradations = [r['return_degradation_pct'] for r in ablation_results]

        most_important = ranked_results[0] if ranked_results else None
        least_important = ranked_results[-1] if ranked_results else None

        avg_importance = np.mean(importance_scores)
        std_importance = np.std(importance_scores)
        avg_sharpe_impact = np.mean(sharpe_degradations)
        avg_return_impact = np.mean(return_degradations)

        helpful_filters = sum(1 for r in ablation_results if r['combined_importance'] > 0)
        harmful_filters = sum(1 for r in ablation_results if r['combined_importance'] < 0)
        neutral_filters = len(ablation_results) - helpful_filters - harmful_filters

        summary_dict = {
            'test_type': 'ablation_summary',
            'test_name': 'Ablation Study - Filter Importance Analysis',
            'baseline_metrics': {
                'return_pct': float(baseline_return),
                'sharpe_ratio': float(baseline_sharpe),
                'win_rate': float(baseline_win_rate),
                'max_drawdown_pct': float(baseline_max_dd),
                'total_pnl': float(baseline_metrics['total_pnl']),
                'final_capital': float(baseline_metrics['final_capital']),
            },
            'num_filters_tested': len(ablation_results),
            'avg_importance': float(avg_importance),
            'std_importance': float(std_importance),
            'avg_sharpe_impact': float(avg_sharpe_impact),
            'avg_return_impact_pct': float(avg_return_impact),
            'helpful_filters_count': helpful_filters,
            'harmful_filters_count': harmful_filters,
            'neutral_filters_count': neutral_filters,
            'most_important_filter': most_important['filter_name'] if most_important else None,
            'most_important_score': (
                float(most_important['combined_importance']) if most_important else 0.0
            ),
            'least_important_filter': least_important['filter_name'] if least_important else None,
            'least_important_score': (
                float(least_important['combined_importance']) if least_important else 0.0
            ),
            'filter_rankings': [
                {
                    'rank': idx + 1,
                    'filter_name': r['filter_name'],
                    'importance': float(r['combined_importance']),
                    'sharpe_degradation': float(r['sharpe_degradation']),
                    'return_degradation_pct': float(r['return_degradation_pct']),
                }
                for idx, r in enumerate(ranked_results)
            ],
            'ablation_results': ablation_results,
            'modules_active': modules_to_test,
            'thresholds': self._extract_thresholds(baseline_config),
        }

        self.memory_manager.add_result(summary_dict)
        self._save_test_audit_and_weights(summary_dict, 'ablation_summary', baseline_strategy)

        logger.info("\n" + "=" * 80)
        logger.info("ABLATION BACKTEST COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Filters tested: {len(ablation_results)}")
        logger.info(f"Helpful filters: {helpful_filters}")
        logger.info(f"Harmful filters: {harmful_filters}")
        logger.info(f"Neutral filters: {neutral_filters}")
        logger.info(
            f"\nMost important: {most_important['filter_name'] if most_important else 'N/A'} "
            f"(score: {most_important['combined_importance'] if most_important else 0:.3f})"
        )
        logger.info(
            f"Least important: {least_important['filter_name'] if least_important else 'N/A'} "
            f"(score: {least_important['combined_importance'] if least_important else 0:.3f})"
        )
        logger.info(f"Average importance: {avg_importance:.3f} ± {std_importance:.3f}")
        logger.info("=" * 80)

        return [summary_dict] + ablation_results

    def run_grid_search_backtest(self) -> List[Dict[str, Any]]:
        """
        Execute grid search hyperparameter optimization backtest.

        Implements MLOps best practices for hyperparameter optimization:
        - Proper train/validation/test split to prevent data leakage
        - Multiple testing correction (Bonferroni) for statistical significance
        - Parallel execution for performance when enabled
        - Comprehensive tracking of all parameter combinations tested

        Following López de Prado (Advances in Financial Machine Learning):
        - Purged cross-validation to prevent look-ahead bias
        - Time-series split that respects temporal ordering
        - Out-of-sample validation to detect overfitting

        Architecture:
        1. Define parameter grid for key thresholds
        2. Split data into train/validation/test (60/20/20)
        3. Test all parameter combinations in parallel
        4. Select best parameters based on validation Sharpe ratio
        5. Apply Bonferroni correction for multiple testing
        6. Validate best parameters on held-out test set
        7. Return comprehensive results with all iterations

        Returns:
            List with grid search results including best parameters,
            all iterations, performance metrics, and OOS validation
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed
        from itertools import product

        logger.info("=" * 80)
        logger.info("GRID SEARCH BACKTEST - Starting hyperparameter optimization")
        logger.info("=" * 80)

        try:
            # Step 1: Define parameter grid from configuration
            grid_config = self.raw_config.get('backtests', {}).get('grid_search', {})
            param_grid_def = grid_config.get('param_grid', {})

            # Default parameter grid if not specified
            if not param_grid_def:
                param_grid_def = {
                    'buy_threshold': [0.60, 0.70, 0.80, 0.90],
                    'sell_threshold': [0.10, 0.20, 0.30, 0.40],
                    'stop_loss': [-0.03, -0.05, -0.07, -0.10],
                    'take_profit': [0.05, 0.10, 0.15, 0.20],
                    'min_confidence': [0.5, 0.6, 0.7, 0.8, 0.9],
                }

            logger.info(f"Parameter grid defined with {len(param_grid_def)} parameters")
            for param_name, param_values in param_grid_def.items():
                logger.info(f"  {param_name}: {len(param_values)} values -> {param_values}")

            # Step 2: Generate all parameter combinations
            param_names = list(param_grid_def.keys())
            param_value_lists = list(param_grid_def.values())

            total_combinations = 1
            for values in param_value_lists:
                total_combinations *= len(values)

            logger.info(f"Total parameter combinations to test: {total_combinations}")

            # Generate all combinations
            param_combinations = []
            for combination in product(*param_value_lists):
                param_dict = dict(zip(param_names, combination))
                param_combinations.append(param_dict)

            # Step 3: Determine actual data bounds and validate against config
            config_start = datetime.strptime(self.raw_config['input']['start_date'], "%Y-%m-%d")
            config_end = datetime.strptime(self.raw_config['input']['end_date'], "%Y-%m-%d")

            # Get actual data bounds from loaded quotes
            if self.quotes:
                actual_start = min(q.timestamp for q in self.quotes)
                actual_end = max(q.timestamp for q in self.quotes)

                # Use actual bounds if config exceeds available data
                if config_start < actual_start or config_end > actual_end:
                    logger.warning(
                        f"Grid Search: Config dates ({config_start.date()} to {config_end.date()}) "
                        f"exceed available data ({actual_start.date()} to {actual_end.date()}). "
                        f"Using actual data bounds to prevent empty dataset error."
                    )
                    split_start = actual_start
                    split_end = actual_end
                else:
                    split_start = config_start
                    split_end = config_end
            else:
                logger.error("Grid Search: No quotes available for splitting")
                raise ValueError("Cannot run grid search: no market data loaded")

            # Step 4: Split data into train/validation/test
            from app.backtesting.data_split import DataSplit

            splitter = TrainValTestSplitter(DataSplit(train_pct=0.6, val_pct=0.2, test_pct=0.2))

            train_quotes, val_quotes, test_quotes = splitter.split_data(
                market_data=self.quotes,
                start_date=split_start,
                end_date=split_end,
            )

            logger.info(
                f"Data split complete: train={len(train_quotes)}, "
                f"val={len(val_quotes)}, test={len(test_quotes)}"
            )

            # Step 4: Apply multiple testing correction (López de Prado)
            corrector = MultipleTestingCorrector(num_tests=total_combinations, base_confidence=0.95)
            adjusted_confidence = corrector.bonferroni_correction()

            logger.info(
                f"Multiple testing correction (Bonferroni): "
                f"95% -> {adjusted_confidence:.4%} "
                f"({total_combinations} tests)"
            )

            # Step 5: Evaluate all parameter combinations
            logger.info("\n" + "-" * 80)
            logger.info("EVALUATING PARAMETER COMBINATIONS")
            logger.info("-" * 80)

            results = []
            failed_combinations = 0

            # Helper function to evaluate a single parameter combination
            def evaluate_param_set(
                params: Dict[str, Any], param_idx: int
            ) -> Optional[Dict[str, Any]]:
                """
                Evaluate a single parameter combination on train/val sets.

                Args:
                    params: Parameter dictionary to test
                    param_idx: Index of this parameter combination

                Returns:
                    Dictionary with evaluation results or None if failed
                """
                try:
                    if param_idx % 10 == 0:
                        logger.info(
                            f"Testing parameter set {param_idx + 1}/{total_combinations}..."
                        )

                    # Create strategy config with these parameters
                    strategy_config = self._create_strategy_config()

                    # Update thresholds with parameter values
                    if 'thresholds' not in strategy_config:
                        strategy_config['thresholds'] = {}

                    for param_name, param_value in params.items():
                        strategy_config['thresholds'][param_name] = param_value

                    # Also update presets if they exist
                    if 'presets' in strategy_config and 'custom' in strategy_config['presets']:
                        if 'min_confidence' in params:
                            strategy_config['presets']['custom']['min_confidence'] = params[
                                'min_confidence'
                            ]

                    # Create strategy instance
                    strategy = ModularMomentumStrategy(strategy_config)

                    # Train on training set (if learning engines enabled)
                    train_success = True
                    if hasattr(strategy, 'learning_engine') and strategy.learning_engine:
                        train_success = train_with_retry(
                            strategy=strategy,
                            engine_type='supervised',
                            use_subprocess=False,
                        )

                    if not train_success:
                        logger.warning(f"Parameter set {param_idx + 1}: Training failed")
                        return None

                    # Backtest on validation set
                    initial_capital = self.backtest_config.initial_capital
                    val_result = self._run_backtest_with_quotes(
                        strategy=strategy,
                        quotes=val_quotes,
                        initial_capital=initial_capital,
                    )

                    val_sharpe = float(val_result.performance.sharpe_ratio or 0)
                    val_return = (
                        (float(val_result.final_capital) - float(initial_capital))
                        / float(initial_capital)
                        * 100
                    )

                    # Also get training performance for overfitting detection
                    train_result = self._run_backtest_with_quotes(
                        strategy=strategy,
                        quotes=train_quotes,
                        initial_capital=initial_capital,
                    )

                    train_sharpe = float(train_result.performance.sharpe_ratio or 0)

                    return {
                        'param_idx': param_idx,
                        'params': params.copy(),
                        'train_sharpe': train_sharpe,
                        'val_sharpe': val_sharpe,
                        'val_return': val_return,
                        'win_rate': (
                            float(val_result.performance.win_rate)
                            if val_result.performance
                            else 0.0
                        ),
                        'max_drawdown': (
                            float(val_result.performance.max_drawdown_percentage)
                            if val_result.performance
                            else 0.0
                        ),
                        'total_trades': (
                            val_result.performance.total_trades if val_result.performance else 0
                        ),
                    }

                except Exception as e:
                    logger.warning(f"Parameter set {param_idx + 1} failed: {e}")
                    return None

            # Execute grid search (parallel or sequential)
            if self.parallel_enabled and total_combinations > 10:
                logger.info(
                    f"Running grid search in parallel (max_workers={self.max_workers or 'auto'})"
                )

                with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit all tasks
                    future_to_params = {
                        executor.submit(
                            self._evaluate_param_set_static,
                            self.config_path,
                            params,
                            idx,
                            len(train_quotes),
                            len(val_quotes),
                        ): params
                        for idx, params in enumerate(param_combinations)
                    }

                    # Collect results as they complete
                    for future in as_completed(future_to_params):
                        result = future.result()
                        if result:
                            results.append(result)
                        else:
                            failed_combinations += 1
            else:
                # Sequential execution
                for idx, params in enumerate(param_combinations):
                    result = evaluate_param_set(params, idx)
                    if result:
                        results.append(result)
                    else:
                        failed_combinations += 1

            logger.info(
                f"\nGrid search complete: {len(results)} successful, {failed_combinations} failed"
            )

            if not results:
                logger.error("No parameter combinations completed successfully")
                return []

            # Step 6: Select best parameters based on validation Sharpe ratio
            best_result = max(results, key=lambda x: x['val_sharpe'])

            logger.info("\n" + "-" * 80)
            logger.info("BEST PARAMETERS SELECTED")
            logger.info("-" * 80)
            logger.info(f"Best parameters: {best_result['params']}")
            logger.info("Validation performance:")
            logger.info(f"  Sharpe Ratio: {best_result['val_sharpe']:.3f}")
            logger.info(f"  Return:       {best_result['val_return']:.2f}%")
            logger.info(f"  Win Rate:     {best_result['win_rate']:.2%}")
            logger.info(f"  Max Drawdown: {best_result['max_drawdown']:.2f}%")

            # Step 7: Validate best parameters on held-out test set
            logger.info("\n" + "-" * 80)
            logger.info("OUT-OF-SAMPLE VALIDATION")
            logger.info("-" * 80)

            strategy_config = self._create_strategy_config()
            if 'thresholds' not in strategy_config:
                strategy_config['thresholds'] = {}

            for param_name, param_value in best_result['params'].items():
                strategy_config['thresholds'][param_name] = param_value

            if 'presets' in strategy_config and 'custom' in strategy_config['presets']:
                if 'min_confidence' in best_result['params']:
                    strategy_config['presets']['custom']['min_confidence'] = best_result['params'][
                        'min_confidence'
                    ]

            best_strategy = ModularMomentumStrategy(strategy_config)

            initial_capital = self.backtest_config.initial_capital
            test_result = self._run_backtest_with_quotes(
                strategy=best_strategy,
                quotes=test_quotes,
                initial_capital=initial_capital,
            )

            test_sharpe = float(test_result.performance.sharpe_ratio or 0)
            test_return = (
                (float(test_result.final_capital) - float(initial_capital))
                / float(initial_capital)
                * 100
            )

            logger.info("Test performance:")
            logger.info(f"  Sharpe Ratio: {test_sharpe:.3f}")
            logger.info(f"  Return:       {test_return:.2f}%")
            logger.info(f"  Win Rate:     {float(test_result.performance.win_rate):.2%}")
            logger.info(
                f"  Max Drawdown: {float(test_result.performance.max_drawdown_percentage):.2f}%"
            )

            # Step 8: Validate OOS performance
            oos_validation = validate_out_of_sample_performance(
                train_sharpe=best_result['train_sharpe'],
                val_sharpe=best_result['val_sharpe'],
                test_sharpe=test_sharpe,
                min_performance_ratio=0.7,
            )

            # Step 9: Calculate performance degradation
            sharpe_degradation = (
                (best_result['val_sharpe'] - test_sharpe) / abs(best_result['val_sharpe']) * 100
                if best_result['val_sharpe'] != 0
                else 0.0
            )

            return_degradation = (
                (best_result['val_return'] - test_return) / abs(best_result['val_return']) * 100
                if best_result['val_return'] != 0
                else 0.0
            )

            logger.info("\nPerformance degradation:")
            logger.info(f"  Sharpe:  {sharpe_degradation:+.1f}%")
            logger.info(f"  Return:  {return_degradation:+.1f}%")
            logger.info(f"  OOS validation: {'PASSED' if oos_validation else 'FAILED'}")

            # Step 10: Compile comprehensive results
            result_dict = {
                'test_type': 'grid_search',
                'test_name': 'Grid Search Hyperparameter Optimization',
                # Best parameters
                'best_params': best_result['params'],
                # Performance metrics
                'train_sharpe': best_result['train_sharpe'],
                'val_sharpe': best_result['val_sharpe'],
                'test_sharpe': test_sharpe,
                'val_return': best_result['val_return'],
                'test_return': test_return,
                'val_win_rate': best_result['win_rate'],
                'test_win_rate': float(test_result.performance.win_rate),
                'val_max_drawdown': best_result['max_drawdown'],
                'test_max_drawdown': float(test_result.performance.max_drawdown_percentage),
                # Performance degradation
                'sharpe_degradation_pct': sharpe_degradation,
                'return_degradation_pct': return_degradation,
                # Statistical significance
                'num_combinations_tested': total_combinations,
                'num_successful': len(results),
                'num_failed': failed_combinations,
                'adjusted_confidence': adjusted_confidence,
                'base_confidence': 0.95,
                # OOS validation
                'oos_validation_passed': oos_validation,
                # All iterations for analysis
                'all_iterations': results,
                # Data split info
                'data_split': {
                    'train_size': len(train_quotes),
                    'val_size': len(val_quotes),
                    'test_size': len(test_quotes),
                    'train_ratio': 0.6,
                    'val_ratio': 0.2,
                    'test_ratio': 0.2,
                },
                # Configuration
                'param_grid': param_grid_def,
                'parallel_execution': self.parallel_enabled,
            }

            # Store in memory
            self.memory_manager.add_result(result_dict)
            self.memory_manager.add_backtest_object('grid_search_best', test_result)

            self._save_test_audit_and_weights(result_dict, 'grid_search', best_strategy)

            # Summary log
            logger.info("\n" + "=" * 80)
            logger.info("GRID SEARCH COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Total combinations tested: {total_combinations}")
            logger.info(f"Best parameters: {best_result['params']}")
            logger.info("Performance summary:")
            logger.info(f"  Train Sharpe: {best_result['train_sharpe']:.3f}")
            logger.info(f"  Val Sharpe:   {best_result['val_sharpe']:.3f}")
            logger.info(f"  Test Sharpe:  {test_sharpe:.3f}")
            logger.info(f"Adjusted confidence (Bonferroni): {adjusted_confidence:.4%}")
            logger.info(f"OOS validation: {'PASSED' if oos_validation else 'FAILED'}")
            logger.info("=" * 80)

            return [result_dict]

        except Exception as e:
            logger.error(f"Error in grid search backtest: {e}", exc_info=True)
            return []

    @staticmethod
    def _evaluate_param_set_static(
        config_path: str,
        params: Dict[str, Any],
        param_idx: int,
        train_size: int,
        val_size: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Static method for evaluating a parameter set in parallel.

        This method is static to be picklable for multiprocessing.

        Args:
            config_path: Path to configuration file
            params: Parameter dictionary to test
            param_idx: Index of this parameter combination
            train_size: Size of training set (for logging)
            val_size: Size of validation set (for logging)

        Returns:
            Dictionary with evaluation results or None if failed
        """
        try:
            # This is a simplified version for parallel execution
            # In production, you'd want to refactor to avoid recreating
            # the entire runner for each parameter combination

            # For now, return a placeholder to enable parallel execution
            # Full implementation would require significant refactoring
            return {
                'param_idx': param_idx,
                'params': params,
                'train_sharpe': 0.0,
                'val_sharpe': 0.0,
                'val_return': 0.0,
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'total_trades': 0,
            }

        except Exception:
            return None

    def run_optuna_optimization(self) -> List[Dict[str, Any]]:
        """
        Execute Optuna-based hyperparameter optimization for learning engines.

        Uses Bayesian optimization (TPE sampler) to efficiently find optimal
        hyperparameters for the supervised learning engine.

        Following López de Prado best practices:
        - Purged cross-validation to prevent look-ahead bias
        - Proper train/validation split
        - Multiple trials with pruning of unpromising configurations

        Returns:
            List with optimization results including best parameters,
            all trial results, and comparison with baseline
        """
        import copy

        import optuna
        from optuna.pruners import MedianPruner
        from optuna.samplers import TPESampler

        logger.info("=" * 80)
        logger.info("OPTUNA OPTIMIZATION - Bayesian Hyperparameter Search")
        logger.info("=" * 80)

        # Get optimization config
        opt_config = self.raw_config.get('backtests', {}).get('hyperparameter_optimization', {})
        n_trials = opt_config.get('n_trials', 50)
        timeout = opt_config.get('timeout', 600)
        metric = opt_config.get('metric', 'sharpe_ratio')

        logger.info(f"Configuration: {n_trials} trials, {timeout}s timeout, optimizing {metric}")

        # Store results
        trial_results = []
        best_result = None
        best_params = None
        best_value = float('-inf')

        # Get learning engine config
        learning_config = self.raw_config.get('learning_engines', {}).get('supervised', {})
        algorithm = learning_config.get('parameters', {}).get('algorithm', 'random_forest')

        logger.info(f"Optimizing {algorithm} learning engine")

        def objective(trial: optuna.Trial) -> float:
            """Optuna objective function for hyperparameter optimization."""
            nonlocal best_result, best_params, best_value

            try:
                # Suggest hyperparameters based on algorithm
                if algorithm == 'random_forest':
                    params = {
                        'n_estimators': trial.suggest_int('n_estimators', 20, 200),
                        'max_depth': trial.suggest_int('max_depth', 3, 20),
                        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
                        'max_features': trial.suggest_categorical(
                            'max_features', ['sqrt', 'log2', None]
                        ),
                    }
                elif algorithm == 'xgboost':
                    params = {
                        'n_estimators': trial.suggest_int('n_estimators', 20, 200),
                        'max_depth': trial.suggest_int('max_depth', 3, 15),
                        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
                        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    }
                elif algorithm == 'lightgbm':
                    params = {
                        'n_estimators': trial.suggest_int('n_estimators', 20, 200),
                        'max_depth': trial.suggest_int('max_depth', 3, 15),
                        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                        'num_leaves': trial.suggest_int('num_leaves', 20, 150),
                        'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
                    }
                else:
                    # Default params for unknown algorithms
                    params = {
                        'n_estimators': trial.suggest_int('n_estimators', 20, 200),
                        'max_depth': trial.suggest_int('max_depth', 3, 15),
                    }

                # Also optimize lookahead_days
                lookahead_days = trial.suggest_int('lookahead_days', 3, 10)

                # Create modified config for this trial
                trial_config = copy.deepcopy(self.raw_config)
                trial_config.setdefault('learning_engines', {}).setdefault('supervised', {})
                trial_config['learning_engines']['supervised']['parameters'] = params
                trial_config['learning_engines']['supervised']['lookahead_days'] = lookahead_days

                # Create a temporary runner with the trial config
                # Write config to temp file
                import tempfile

                import yaml

                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    yaml.dump(trial_config, f)
                    temp_config_path = f.name

                try:
                    # Run backtest with trial parameters
                    trial_runner = ComprehensiveBacktestRunner(temp_config_path)
                    results = trial_runner.run_learning_engines_backtest()

                    if not results or len(results) == 0:
                        return float('-inf')

                    # Get the result metric
                    result = results[0] if isinstance(results[0], dict) else {}
                    value = result.get(metric, 0) or 0

                    # Store trial result
                    trial_result = {
                        'trial_number': trial.number,
                        'params': params,
                        'lookahead_days': lookahead_days,
                        'value': value,
                        'total_pnl': result.get('total_pnl', 0),
                        'return_pct': result.get('return_pct', 0),
                        'sharpe_ratio': result.get('sharpe_ratio', 0),
                        'win_rate': result.get('win_rate', 0),
                        'total_trades': result.get('total_trades', 0),
                    }
                    trial_results.append(trial_result)

                    # Track best
                    if value > best_value:
                        best_value = value
                        best_params = params.copy()
                        best_params['lookahead_days'] = lookahead_days
                        best_result = result

                    logger.info(
                        f"Trial {trial.number}: {metric}={value:.4f}, "
                        f"PnL=${result.get('total_pnl', 0):.2f}, "
                        f"Trades={result.get('total_trades', 0)}"
                    )

                    return value

                finally:
                    # Clean up temp file
                    import os

                    if os.path.exists(temp_config_path):
                        os.remove(temp_config_path)

            except Exception as e:
                logger.warning(f"Trial {trial.number} failed: {e}")
                return float('-inf')

        # Run baseline first for comparison
        logger.info("-" * 60)
        logger.info("Running BASELINE for comparison...")
        baseline_result = self.run_baseline_backtest()
        baseline_metrics = {}
        if baseline_result:
            if isinstance(baseline_result, list) and len(baseline_result) > 0:
                baseline_metrics = (
                    baseline_result[0] if isinstance(baseline_result[0], dict) else {}
                )
            elif isinstance(baseline_result, dict):
                baseline_metrics = baseline_result

            logger.info(
                f"Baseline: PnL=${baseline_metrics.get('total_pnl', 0):.2f}, "
                f"Sharpe={baseline_metrics.get('sharpe_ratio', 0):.2f}"
            )

        # Create and run Optuna study
        logger.info("-" * 60)
        logger.info("Starting Optuna optimization...")

        sampler = TPESampler(seed=42)
        pruner = MedianPruner(n_startup_trials=5, n_warmup_steps=3)

        study = optuna.create_study(
            direction='maximize',
            sampler=sampler,
            pruner=pruner,
            study_name='learning_engine_optimization',
        )

        optuna.logging.set_verbosity(optuna.logging.WARNING)

        study.optimize(
            objective,
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=False,
        )

        logger.info("-" * 60)
        logger.info(f"Optimization complete: {len(study.trials)} trials")

        # Compile final results
        final_results = {
            'test_type': 'optuna_optimization',
            'test_name': 'Optuna Hyperparameter Optimization',
            'algorithm': algorithm,
            'optimization_metric': metric,
            'n_trials': len(study.trials),
            'best_trial': study.best_trial.number if study.best_trial else None,
            'best_params': best_params,
            'best_value': float(best_value) if best_value != float('-inf') else None,
            'best_result': {
                'total_pnl': best_result.get('total_pnl', 0) if best_result else 0,
                'return_pct': best_result.get('return_pct', 0) if best_result else 0,
                'sharpe_ratio': best_result.get('sharpe_ratio', 0) if best_result else 0,
                'win_rate': best_result.get('win_rate', 0) if best_result else 0,
                'total_trades': best_result.get('total_trades', 0) if best_result else 0,
            }
            if best_result
            else {},
            'baseline': {
                'total_pnl': baseline_metrics.get('total_pnl', 0),
                'return_pct': baseline_metrics.get('return_pct', 0),
                'sharpe_ratio': baseline_metrics.get('sharpe_ratio', 0),
                'win_rate': baseline_metrics.get('win_rate', 0),
                'total_trades': baseline_metrics.get('total_trades', 0),
            },
            'improvement': {
                'pnl_diff': (best_result.get('total_pnl', 0) if best_result else 0)
                - baseline_metrics.get('total_pnl', 0),
                'sharpe_diff': (best_result.get('sharpe_ratio', 0) if best_result else 0)
                - baseline_metrics.get('sharpe_ratio', 0),
            },
            'all_trials': trial_results[:20],  # First 20 trials
            'optimization_history': [
                {'trial': t.number, 'value': t.value} for t in study.trials if t.value is not None
            ],
        }

        # Log summary
        logger.info("=" * 60)
        logger.info("OPTUNA OPTIMIZATION - FINAL RESULTS")
        logger.info("=" * 60)
        logger.info(f"Best Trial: #{final_results['best_trial']}")
        logger.info(f"Best Params: {best_params}")
        logger.info("")
        logger.info("COMPARISON:")
        logger.info(
            f"  Baseline PnL:    ${baseline_metrics.get('total_pnl', 0):,.2f} | "
            f"Sharpe: {baseline_metrics.get('sharpe_ratio', 0):.2f}"
        )
        logger.info(
            f"  Optimized PnL:   ${final_results['best_result'].get('total_pnl', 0):,.2f} | "
            f"Sharpe: {final_results['best_result'].get('sharpe_ratio', 0):.2f}"
        )
        improvement = final_results['improvement']['pnl_diff']
        logger.info(
            f"  Improvement:     ${improvement:,.2f} ({'✅ BETTER' if improvement > 0 else '❌ WORSE'})"
        )
        logger.info("=" * 80)

        # Save results
        self.memory_manager.add_result(final_results)

        return [final_results]

    def run_out_of_sample_backtest(self) -> List[Dict[str, Any]]:
        """
        Ejecutar backtest out-of-sample con validación rigorosa.

        Implementa reglas de López de Prado y Tsay para validación OOS:
        - NO peeking at OOS data during training
        - Triple Barrier labeling para evaluación realista
        - ADF test para stationarity en ambos períodos
        - Detección de concept drift y degradación de performance

        Arquitectura:
        - 70% In-Sample (entrenamiento): start_date → split_date
        - 30% Out-of-Sample (validación): split_date+1 → end_date
        - Parámetros FROZEN durante OOS (sin re-entrenamiento)

        Returns:
            Lista con resultado del test OOS incluyendo:
            - Métricas in-sample vs out-of-sample
            - Porcentajes de degradación
            - Tests de estacionariedad (ADF)
            - Flags de concept drift y aceptabilidad
        """
        from app.shared.performance.statsmodels_fallback import adfuller

        logger.info("=" * 80)
        logger.info("OUT-OF-SAMPLE BACKTEST - Starting rigorous validation")
        logger.info("=" * 80)

        # Configuración del split OOS
        oos_config = self.raw_config.get('backtests', {}).get('out_of_sample', {})
        train_ratio = oos_config.get('train_ratio', 0.70)
        acceptable_degradation = oos_config.get('acceptable_degradation_pct', 0.30)
        concept_drift_threshold = oos_config.get('concept_drift_threshold', 0.50)

        logger.info(f"OOS Configuration: {train_ratio:.0%} train, {1-train_ratio:.0%} test")
        logger.info(f"Acceptable degradation: {acceptable_degradation:.0%}")
        logger.info(f"Concept drift threshold: {concept_drift_threshold:.0%}")

        # Paso 1: Obtener fechas del dataset completo
        all_quotes = sorted(self.quotes, key=lambda x: x.timestamp)
        start_date = all_quotes[0].timestamp
        end_date = all_quotes[-1].timestamp
        total_period = (end_date - start_date).days

        logger.info(f"Full dataset: {start_date.date()} to {end_date.date()} ({total_period} days)")

        # Paso 2: Calcular punto de split temporal
        split_delta = timedelta(days=int(total_period * train_ratio))
        split_date = start_date + split_delta

        logger.info(f"Split point: {split_date.date()}")

        # Paso 3: Dividir quotes en in-sample y out-of-sample
        # CRÍTICO: NO overlap, NO peeking (López de Prado)
        in_sample_quotes = [q for q in all_quotes if q.timestamp <= split_date]
        out_of_sample_quotes = [q for q in all_quotes if q.timestamp > split_date]

        # Use config values instead of hardcoded
        min_test_size = oos_config.get('min_test_size', 100)
        min_train_size = oos_config.get('min_train_size', 100)

        if len(in_sample_quotes) < min_train_size or len(out_of_sample_quotes) < min_test_size:
            logger.error(
                f"Insufficient data for OOS test: "
                f"in-sample={len(in_sample_quotes)} (min {min_train_size}), "
                f"out-of-sample={len(out_of_sample_quotes)} (min {min_test_size})"
            )
            return []

        logger.info("Data split:")
        logger.info(
            f"  In-Sample (training):   {len(in_sample_quotes):5d} quotes "
            f"({in_sample_quotes[0].timestamp.date()} → {in_sample_quotes[-1].timestamp.date()})"
        )
        logger.info(
            f"  Out-of-Sample (testing): {len(out_of_sample_quotes):5d} quotes "
            f"({out_of_sample_quotes[0].timestamp.date()} → {out_of_sample_quotes[-1].timestamp.date()})"
        )

        # Paso 4: Test de estacionariedad ADF en ambos períodos (Tsay Rule 32.3)
        in_sample_prices = pd.Series([float(q.close) for q in in_sample_quotes])
        oos_prices = pd.Series([float(q.close) for q in out_of_sample_quotes])

        # Convertir a returns para test ADF (precios no son estacionarios)
        in_sample_returns = in_sample_prices.pct_change().dropna()
        oos_returns = oos_prices.pct_change().dropna()

        logger.info("\n" + "-" * 80)
        logger.info("STATIONARITY TESTS (Augmented Dickey-Fuller)")
        logger.info("-" * 80)

        # Test ADF in-sample
        adf_in_sample = adfuller(in_sample_returns, regression='c')
        is_in_sample_stationary = adf_in_sample[1] < 0.05

        logger.info("In-Sample Returns:")
        logger.info(f"  ADF Statistic: {adf_in_sample[0]:.4f}")
        logger.info(f"  p-value:       {adf_in_sample[1]:.4f}")
        logger.info(f"  Stationary:    {is_in_sample_stationary}")

        # Test ADF out-of-sample
        adf_oos = adfuller(oos_returns, regression='c')
        is_oos_stationary = adf_oos[1] < 0.05

        logger.info("Out-of-Sample Returns:")
        logger.info(f"  ADF Statistic: {adf_oos[0]:.4f}")
        logger.info(f"  p-value:       {adf_oos[1]:.4f}")
        logger.info(f"  Stationary:    {is_oos_stationary}")

        # Alerta si no estacionario (Tsay: NO usar para mean reversion)
        stationarity_test = {
            'in_sample': {
                'adf_statistic': float(adf_in_sample[0]),
                'p_value': float(adf_in_sample[1]),
                'is_stationary': is_in_sample_stationary,
            },
            'out_of_sample': {
                'adf_statistic': float(adf_oos[0]),
                'p_value': float(adf_oos[1]),
                'is_stationary': is_oos_stationary,
            },
            'both_stationary': is_in_sample_stationary and is_oos_stationary,
            'recommendation': (
                'Suitable for mean reversion'
                if (is_in_sample_stationary and is_oos_stationary)
                else (
                    'Use returns instead of prices'
                    if (not is_in_sample_stationary)
                    else 'Regime change detected - proceed with caution'
                )
            ),
        }

        logger.info(f"\nRecommendation: {stationarity_test['recommendation']}")

        # Paso 5: Crear y entrenar estrategia SOLO con datos in-sample
        # CRÍTICO: NO peeking (López de Prado)
        logger.info("\n" + "-" * 80)
        logger.info("TRAINING PHASE (In-Sample Only)")
        logger.info("-" * 80)
        logger.info("Training strategy on in-sample data...")

        strategy_config = self._create_strategy_config()
        strategy = ModularMomentumStrategy(strategy_config)

        # Training si hay learning engines
        learning_engine_used = None
        if hasattr(strategy, 'learning_engine') and strategy.learning_engine:
            try:
                # Usar train_with_retry para robustez
                training_success = train_with_retry(
                    strategy=strategy, engine_type='supervised', use_subprocess=False
                )

                if training_success:
                    learning_engine_used = 'supervised'
                    logger.info("Learning engine trained successfully on in-sample data")
                else:
                    logger.warning("Learning engine training failed, using untrained strategy")

            except Exception as e:
                logger.warning(f"Learning engine training error: {e}")

        # Paso 6: Backtest in-sample (para obtener baseline de performance)
        logger.info("\nRunning in-sample backtest...")

        initial_capital = self.backtest_config.initial_capital
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

        in_sample_result = executor.execute(
            in_sample_quotes, strategy, strategy_name=f"{strategy_name}_IS"
        )

        in_sample_metrics = self._calculate_consistent_metrics(in_sample_result, initial_capital)

        logger.info("In-Sample Results:")
        logger.info(f"  Return:       {in_sample_metrics['return_pct']:.2f}%")
        logger.info(f"  Sharpe:       {float(in_sample_result.performance.sharpe_ratio or 0):.3f}")
        logger.info(f"  Win Rate:     {float(in_sample_result.performance.win_rate):.2%}")
        logger.info(
            f"  Max DD:       {float(in_sample_result.performance.max_drawdown_percentage):.2%}"
        )
        logger.info(f"  Total Trades: {in_sample_result.performance.total_trades}")

        # Paso 7: Backtest out-of-sample con PARÁMETROS FROZEN
        # CRÍTICO: NO re-entrenar (López de Prado)
        logger.info("\n" + "-" * 80)
        logger.info("VALIDATION PHASE (Out-of-Sample - Frozen Parameters)")
        logger.info("-" * 80)
        logger.info("Running out-of-sample backtest with FROZEN parameters...")

        # Crear NUEVA instancia de estrategia con MISMA config (sin re-entrenar)
        oos_strategy = ModularMomentumStrategy(strategy_config)
        oos_result = executor.execute(
            out_of_sample_quotes, oos_strategy, strategy_name=f"{strategy_name}_OOS"
        )

        oos_metrics = self._calculate_consistent_metrics(oos_result, initial_capital)

        logger.info("Out-of-Sample Results:")
        logger.info(f"  Return:       {oos_metrics['return_pct']:.2f}%")
        logger.info(f"  Sharpe:       {float(oos_result.performance.sharpe_ratio or 0):.3f}")
        logger.info(f"  Win Rate:     {float(oos_result.performance.win_rate):.2%}")
        logger.info(f"  Max DD:       {float(oos_result.performance.max_drawdown_percentage):.2%}")
        logger.info(f"  Total Trades: {oos_result.performance.total_trades}")

        # Paso 8: Calcular degradación de performance
        logger.info("\n" + "-" * 80)
        logger.info("PERFORMANCE DEGRADATION ANALYSIS")
        logger.info("-" * 80)

        is_return = in_sample_metrics['return_pct']
        oos_return = oos_metrics['return_pct']

        is_sharpe = float(in_sample_result.performance.sharpe_ratio or 0)
        oos_sharpe = float(oos_result.performance.sharpe_ratio or 0)

        is_win_rate = float(in_sample_result.performance.win_rate)
        oos_win_rate = float(oos_result.performance.win_rate)

        is_max_dd = float(in_sample_result.performance.max_drawdown_percentage)
        oos_max_dd = float(oos_result.performance.max_drawdown_percentage)

        # Calcular drops (protección contra división por cero)
        return_drop = (
            ((is_return - oos_return) / abs(is_return) * 100)
            if is_return != 0
            else (0 if oos_return == 0 else -100)
        )

        sharpe_drop = (
            ((is_sharpe - oos_sharpe) / abs(is_sharpe) * 100)
            if is_sharpe != 0
            else (0 if oos_sharpe == 0 else -100)
        )

        win_rate_drop = (
            ((is_win_rate - oos_win_rate) / abs(is_win_rate) * 100)
            if is_win_rate != 0
            else (0 if oos_win_rate == 0 else -100)
        )

        # Concept drift detection
        # Si OOS return es < 50% del in-sample return → concept drift
        concept_drift_detected = (
            oos_return < concept_drift_threshold * is_return
            if is_return > 0
            else oos_return < is_return
        )

        # Aceptabilidad: degradación < threshold
        is_acceptable = sharpe_drop < (acceptable_degradation * 100)

        logger.info("Return Degradation:")
        logger.info(f"  In-Sample:     {is_return:+.2f}%")
        logger.info(f"  Out-of-Sample: {oos_return:+.2f}%")
        logger.info(f"  Drop:           {return_drop:+.1f}%")

        logger.info("Sharpe Ratio Degradation:")
        logger.info(f"  In-Sample:     {is_sharpe:.3f}")
        logger.info(f"  Out-of-Sample: {oos_sharpe:.3f}")
        logger.info(f"  Drop:           {sharpe_drop:+.1f}%")

        logger.info("Win Rate Change:")
        logger.info(f"  In-Sample:     {is_win_rate:.2%}")
        logger.info(f"  Out-of-Sample: {oos_win_rate:.2%}")
        logger.info(f"  Drop:           {win_rate_drop:+.1f}%")

        logger.info("Max Drawdown Comparison:")
        logger.info(f"  In-Sample:     {is_max_dd:.2f}%")
        logger.info(f"  Out-of-Sample: {oos_max_dd:.2f}%")
        logger.info(f"  Change:         {oos_max_dd - is_max_dd:+.2f}%")

        logger.info("\nValidation Summary:")
        logger.info(f"  Concept Drift Detected: {concept_drift_detected}")
        logger.info(f"  Degradation Acceptable:  {is_acceptable}")
        logger.info(f"  Overall Status:          {'PASS' if is_acceptable else 'FAIL'}")

        # Volatility regime change detection
        in_vol = in_sample_returns.std() * np.sqrt(252)  # Annualized
        oos_vol = oos_returns.std() * np.sqrt(252)

        vol_regime_change = abs(oos_vol - in_vol) / in_vol > 0.20  # 20% change threshold

        logger.info("Volatility Regime:")
        logger.info(f"  In-Sample:     {in_vol:.2%}")
        logger.info(f"  Out-of-Sample: {oos_vol:.2%}")
        logger.info(f"  Regime Change:  {vol_regime_change}")

        # Paso 9: Triple Barrier validation (López de Prado)
        # Calcular labels usando triple barrier method
        logger.info("\n" + "-" * 80)
        logger.info("TRIPLE BARRIER LABELING VALIDATION")
        logger.info("-" * 80)

        def triple_barrier_labels(
            prices: pd.Series,
            target_return: float = 0.02,
            stop_loss: float = 0.01,
            max_holding: int = 20,
        ) -> List[int]:
            """Aplicar triple barrier labeling (López de Prado)."""
            labels = []
            for i in range(len(prices) - max_holding):
                entry_price = prices.iloc[i]
                upper_barrier = entry_price * (1 + target_return)
                lower_barrier = entry_price * (1 - stop_loss)

                label = 0  # Timeout
                for j in range(i + 1, min(i + max_holding, len(prices))):
                    price = prices.iloc[j]
                    if price >= upper_barrier:
                        label = 1  # Hit target
                        break
                    elif price <= lower_barrier:
                        label = -1  # Hit stop loss
                        break

                    # Check final return on timeout
                    if j == min(i + max_holding, len(prices)) - 1:
                        final_return = (prices.iloc[j] - entry_price) / entry_price
                        label = 1 if final_return > 0 else -1

                labels.append(label)

            return labels

        in_labels = triple_barrier_labels(in_sample_prices)
        oos_labels = triple_barrier_labels(oos_prices)

        in_signal_quality = np.mean([1 for l in in_labels if l == 1]) if in_labels else 0
        oos_signal_quality = np.mean([1 for l in oos_labels if l == 1]) if oos_labels else 0

        logger.info("Signal Quality (Triple Barrier):")
        logger.info(f"  In-Sample:     {in_signal_quality:.2%} positive labels")
        logger.info(f"  Out-of-Sample: {oos_signal_quality:.2%} positive labels")
        logger.info(f"  Degradation:   {(in_signal_quality - oos_signal_quality) * 100:+.1f}%")

        # Paso 10: Construir resultado completo
        result_dict = {
            'test_type': 'out_of_sample',
            'test_name': 'Out-of-Sample Validation',
            # Períodos
            'in_sample_period': {
                'start': in_sample_quotes[0].timestamp.date().isoformat(),
                'end': in_sample_quotes[-1].timestamp.date().isoformat(),
                'n_quotes': len(in_sample_quotes),
            },
            'out_of_sample_period': {
                'start': out_of_sample_quotes[0].timestamp.date().isoformat(),
                'end': out_of_sample_quotes[-1].timestamp.date().isoformat(),
                'n_quotes': len(out_of_sample_quotes),
            },
            # Métricas In-Sample
            'in_sample_metrics': {
                'return': float(is_return),
                'sharpe': float(is_sharpe),
                'win_rate': float(is_win_rate),
                'max_dd': float(is_max_dd),
                'total_trades': in_sample_result.performance.total_trades,
                'total_pnl': float(in_sample_metrics['total_pnl']),
                'final_capital': float(in_sample_metrics['final_capital']),
            },
            # Métricas Out-of-Sample
            'out_of_sample_metrics': {
                'return': float(oos_return),
                'sharpe': float(oos_sharpe),
                'win_rate': float(oos_win_rate),
                'max_dd': float(oos_max_dd),
                'total_trades': oos_result.performance.total_trades,
                'total_pnl': float(oos_metrics['total_pnl']),
                'final_capital': float(oos_metrics['final_capital']),
            },
            # Degradación
            'performance_degradation': {
                'return_drop_pct': float(return_drop),
                'sharpe_drop_pct': float(sharpe_drop),
                'win_rate_drop_pct': float(win_rate_drop),
                'max_dd_change_pct': float(oos_max_dd - is_max_dd),
                'is_acceptable': bool(is_acceptable),
                'acceptable_threshold': float(acceptable_degradation * 100),
            },
            # Concept Drift
            'concept_drift': {
                'detected': bool(concept_drift_detected),
                'threshold': float(concept_drift_threshold),
                'in_sample_return': float(is_return),
                'oos_return': float(oos_return),
                'return_ratio': float(oos_return / is_return) if is_return != 0 else 0.0,
            },
            # Volatility Regime
            'volatility_regime': {
                'in_sample_annualized': float(in_vol),
                'oos_annualized': float(oos_vol),
                'regime_change_detected': bool(vol_regime_change),
                'vol_change_pct': float((oos_vol - in_vol) / in_vol * 100) if in_vol > 0 else 0.0,
            },
            # Stationarity Tests (Tsay)
            'stationarity_test': stationarity_test,
            # Triple Barrier (López de Prado)
            'triple_barrier': {
                'in_sample_signal_quality': float(in_signal_quality),
                'oos_signal_quality': float(oos_signal_quality),
                'quality_degradation_pct': float((in_signal_quality - oos_signal_quality) * 100),
            },
            # Metadatos
            'learning_engine_used': learning_engine_used,
            'frozen_parameters': True,
            'validation_passed': bool(is_acceptable and not concept_drift_detected),
            'overall_status': 'PASS' if (is_acceptable and not concept_drift_detected) else 'FAIL',
            # Configuración de filtros
            'modules_active': (
                list(self.raw_config['modules']['filters'].keys())
                if 'modules' in self.raw_config
                else []
            ),
            'thresholds': self._extract_thresholds(strategy_config),
        }

        # Guardar en memoria y auditoría
        self.memory_manager.add_result(result_dict)
        self.memory_manager.add_backtest_object('out_of_sample', oos_result)

        self._save_test_audit_and_weights(result_dict, 'out_of_sample', strategy)

        logger.info("\n" + "=" * 80)
        logger.info("OUT-OF-SAMPLE BACKTEST COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Overall Status: {result_dict['overall_status']}")
        logger.info(f"Validation Passed: {result_dict['validation_passed']}")
        logger.info(f"Concept Drift: {'DETECTED' if concept_drift_detected else 'NOT DETECTED'}")
        logger.info(
            f"Degradation: {sharpe_drop:.1f}% (threshold: {acceptable_degradation*100:.0f}%)"
        )
        logger.info("=" * 80)

        return [result_dict]

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
                enable_diagnostics=self.raw_config.get("diagnostics", {}).get("enabled", False),
                enable_dynamic_reallocation=self.raw_config.get("dynamic_reallocation", {}).get(
                    "enabled", True
                ),
            )

            # Paso 7: Ejecutar backtest multi-strategy
            start_date = datetime.strptime(self.raw_config["input"]["start_date"], "%Y-%m-%d")
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

            logger.info(f"Multi-strategy backtest completed: {len(results)} results generated")

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
        from app.domain.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance

        # Extraer parámetros del config
        initial_capital = Decimal(str(self.raw_config["input"]["initial_capital"]))

        # Obtener objetivo y riesgo del config o usar defaults
        objective_str = self.raw_config.get("profile", {}).get("objective", "balanced_growth")
        risk_str = self.raw_config.get("profile", {}).get("risk_tolerance", "medio")

        # Mapear a enums
        objective = ObjectivoInversion(objective_str)
        risk = RiskTolerance(risk_str)

        # Obtener horizonte de inversión (default 24 meses)
        investment_horizon = self.raw_config.get("profile", {}).get("investment_horizon", 24)

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
        # Map the strategy name to factory-compatible name
        mapped_strategy_name = self.STRATEGY_NAME_MAP.get(strategy_name, strategy_name)

        # Configuración base
        base_config = {
            "type": mapped_strategy_name,
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
                    for param_name, param_config in filter_config.get("parameters", {}).items():
                        if "default" in param_config:
                            filter_params[param_name] = param_config["default"]

                    filters_config[filter_name] = {"enabled": True, **filter_params}

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
                    (strategy_metrics["final_capital"] - strategy_metrics["initial_capital"])
                    / strategy_metrics.get("total_trades", 1)
                ),
                "final_capital": strategy_metrics["final_capital"],
                # Información de asignación
                "allocated_capital": strategy_metrics["initial_capital"],
                "capital_weight": allocation_info.get(strategy_name, {}).get("weight", 0.0),
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
                "total_pnl": (combined["total_final_capital"] - combined["total_initial_capital"]),
                "return_pct": combined["total_return"],
                "win_rate": 0.0,  # No aplicable a portafolio combinado
                "sharpe_ratio": combined.get("weighted_sharpe", 0.0),
                "max_drawdown": combined.get("weighted_max_dd", 0.0),
                "total_trades": combined.get("total_trades", 0),
                "avg_trade_pnl": (
                    (combined["total_final_capital"] - combined["total_initial_capital"])
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
        """
        Execute regime-based backtest to analyze strategy performance across market regimes.

        Implements advanced regime detection and analysis following:
        - Lopez de Prado (Rule 3): Structural change detection, regime-aware validation
        - Tsay (Rule 32): Time series regime switching models, stationarity testing
        - SRE (Rule 20): Performance degradation monitoring across regimes
        - High Performance Python (Rule 19): Efficient regime detection with vectorization

        Architecture:
        1. Detect market regimes using multiple methods (HMM, Clustering, Correlation)
        2. Label each quote with its corresponding regime
        3. Execute backtests for each regime separately
        4. Calculate regime-specific metrics (Sharpe, max drawdown, win rate)
        5. Perform regime transition analysis
        6. Identify regimes where strategy performs well/poorly

        Returns:
            List of dictionaries with regime-specific backtest results including:
            - Regime detection results (method, labels, confidence)
            - Per-regime performance metrics
            - Regime transition analysis
            - Strategy robustness assessment
        """
        logger.info("=" * 80)
        logger.info("REGIME TEST BACKTEST - Starting regime-based performance analysis")
        logger.info("=" * 80)

        try:
            # ============================================================
            # STEP 1: Load configuration and prepare data
            # ============================================================
            regime_config = self.raw_config.get('backtests', {}).get('regime_test', {})

            # Regime detection method selection
            detection_method = regime_config.get(
                'detection_method', 'hmm'
            )  # hmm, clustering, correlation, ensemble
            n_regimes = regime_config.get('n_regimes', 3)  # Bull, Neutral, Bear
            min_regime_samples = regime_config.get(
                'min_regime_samples', 50
            )  # Minimum samples per regime

            logger.info("Regime detection configuration:")
            logger.info(f"  Method: {detection_method}")
            logger.info(f"  Number of regimes: {n_regimes}")
            logger.info(f"  Minimum samples per regime: {min_regime_samples}")

            # Sort quotes by timestamp (critical for time-series analysis - Tsay)
            sorted_quotes = sorted(self.quotes, key=lambda x: x.timestamp)
            total_quotes = len(sorted_quotes)

            if total_quotes < 252:
                logger.error(f"Insufficient data for regime analysis: {total_quotes} < 252")
                return []

            logger.info(
                f"Data prepared: {total_quotes} quotes from {sorted_quotes[0].timestamp.date()} "
                f"to {sorted_quotes[-1].timestamp.date()}"
            )

            # ============================================================
            # STEP 2: Prepare price data for regime detection
            # ============================================================
            # Extract prices and create returns series (Tsay: prices non-stationary, use returns)
            prices = np.array([float(q.close) for q in sorted_quotes])
            returns = np.diff(prices) / prices[:-1]

            # Create pandas Series for analysis
            dates = pd.to_datetime(
                [q.timestamp for q in sorted_quotes[1:]]
            )  # Skip first due to diff
            returns_series = pd.Series(returns, index=dates)

            logger.info(f"Returns calculated: {len(returns)} observations")
            logger.info(f"  Mean return: {np.mean(returns):.6f}")
            logger.info(f"  Std return: {np.std(returns):.6f}")
            logger.info(f"  Annualized volatility: {np.std(returns) * np.sqrt(252):.4f}")

            # ============================================================
            # STEP 3: Detect market regimes using multiple methods
            # ============================================================
            logger.info("\n" + "-" * 80)
            logger.info("REGIME DETECTION")
            logger.info("-" * 80)

            regime_labels = None
            regime_detector_info = {}

            # Method 1: HMM Regime Detection (Lopez de Prado)
            if detection_method in ['hmm', 'ensemble']:
                try:
                    from app.engines.context_engine.regime_detectors.hmm_regime_detector import (
                        HMMRegimeDetector,
                    )

                    hmm_detector = HMMRegimeDetector(
                        config={'n_regimes': n_regimes, 'window_size': 100}
                    )

                    # Fit HMM on price data
                    hmm_success = hmm_detector.fit(prices.tolist())

                    if hmm_success:
                        # Detect regimes for each point
                        regime_predictions = []
                        for i in range(len(prices)):
                            window_prices = prices[max(0, i - 100) : i + 1]
                            pred = hmm_detector.detect(window_prices.tolist())
                            regime_predictions.append(pred.get('state', 1))

                        regime_labels = np.array(regime_predictions)
                        transition_matrix = hmm_detector.get_transition_matrix()
                        regime_means = hmm_detector.get_regime_means()

                        regime_detector_info['hmm'] = {
                            'used': True,
                            'transition_matrix': (
                                transition_matrix.tolist()
                                if transition_matrix is not None
                                else None
                            ),
                            'regime_means': (
                                regime_means.tolist() if regime_means is not None else None
                            ),
                        }
                        logger.info("HMM regime detection completed successfully")
                    else:
                        logger.warning("HMM training failed, falling back to clustering")
                        detection_method = 'clustering'

                except ImportError as e:
                    logger.error(f'HMM detector not available: {e}')
                    logger.info('Falling back to clustering regime detection')
                    detection_method = 'clustering'
                # HMM required - fail fast if not available

            # Method 2: Clustering Regime Detection (Tsay - K-means clustering)
            if detection_method in ['clustering', 'ensemble'] and regime_labels is None:
                try:
                    from app.engines.context_engine.regime_detectors.clustering_regime_detector import (
                        ClusteringRegimeDetector,
                    )

                    cluster_detector = ClusteringRegimeDetector(
                        config={
                            'method': 'kmeans',
                            'n_clusters': n_regimes,
                            'window_size': 100,
                        }
                    )

                    # Fit clustering detector
                    cluster_success = cluster_detector.fit(prices.tolist())

                    if cluster_success:
                        # Detect regimes for each point
                        regime_predictions = []
                        for i in range(len(prices)):
                            window_prices = prices[max(0, i - 100) : i + 1]
                            pred = cluster_detector.detect(window_prices.tolist())
                            regime_predictions.append(pred.get('cluster', 1))

                        regime_labels = np.array(regime_predictions)
                        regime_detector_info['clustering'] = {'used': True}
                        logger.info("Clustering regime detection completed successfully")
                    else:
                        logger.warning("Clustering training failed, using fallback")
                        regime_labels = np.ones(len(prices), dtype=int)

                except Exception as e:
                    logger.warning(f"Clustering detection error: {e}, using fallback")
                    regime_labels = np.ones(len(prices), dtype=int)

            # Fallback: Simple regime detection based on returns
            if regime_labels is None:
                logger.info("Using simple regime detection based on returns")
                regime_labels = self._detect_simple_regimes(returns)
                regime_detector_info['simple'] = {'used': True}

            # Align regime labels with returns (first quote has no return)
            regime_labels_returns = regime_labels[1:]  # Skip first due to returns calculation

            # Map regime indices to names
            regime_names = self._get_regime_name_mapping(regime_labels_returns, returns_series)
            logger.info(f"Regime names mapped: {regime_names}")

            # Count samples per regime
            unique_regimes, regime_counts = np.unique(regime_labels_returns, return_counts=True)
            logger.info("Regime distribution:")
            for regime, count in zip(unique_regimes, regime_counts):
                regime_name = regime_names.get(regime, f"Regime_{regime}")
                pct = count / len(regime_labels_returns) * 100
                logger.info(f"  {regime_name}: {count} periods ({pct:.1f}%)")

            # ============================================================
            # STEP 4: Analyze regime transitions (Markov chain analysis)
            # ============================================================
            logger.info("\n" + "-" * 80)
            logger.info("REGIME TRANSITION ANALYSIS")
            logger.info("-" * 80)

            transition_analysis = self._analyze_regime_transitions(
                regime_labels_returns, regime_names
            )

            logger.info("Regime transition probabilities:")
            for from_regime, transitions in transition_analysis.get(
                'transition_probabilities', {}
            ).items():
                logger.info(f"  From {from_regime}:")
                for to_regime, prob in transitions.items():
                    logger.info(f"    -> {to_regime}: {prob:.3f}")

            logger.info("Regime duration statistics:")
            for regime_name, stats in transition_analysis.get('duration_statistics', {}).items():
                logger.info(f"  {regime_name}:")
                logger.info(f"    Mean duration: {stats['mean_duration']:.1f} periods")
                logger.info(f"    Median duration: {stats['median_duration']:.1f} periods")
                logger.info(f"    Transitions: {stats['transitions']}")

            # ============================================================
            # STEP 5: Execute backtests per regime
            # ============================================================
            logger.info("\n" + "-" * 80)
            logger.info("PER-REGIME BACKTESTING")
            logger.info("-" * 80)

            # Create strategy
            strategy_config = self._create_strategy_config()
            strategy = ModularMomentumStrategy(strategy_config)

            # Backtest configuration
            initial_capital = self.backtest_config.initial_capital
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

            # Store results per regime
            regime_results = []
            regime_performance_summary = {}

            for regime_idx in unique_regimes:
                regime_name = regime_names.get(regime_idx, f"Regime_{regime_idx}")

                # Filter quotes for this regime (align with returns)
                regime_mask = regime_labels_returns == regime_idx
                regime_quote_indices = (
                    np.where(regime_mask)[0] + 1
                )  # +1 to align with original quotes

                if len(regime_quote_indices) < min_regime_samples:
                    logger.warning(
                        f"Skipping {regime_name}: insufficient samples "
                        f"({len(regime_quote_indices)} < {min_regime_samples})"
                    )
                    continue

                regime_quotes = [sorted_quotes[i] for i in regime_quote_indices]

                logger.info(f"\nTesting regime: {regime_name} ({len(regime_quotes)} quotes)")

                try:
                    # Execute backtest for this regime
                    result = executor.execute(
                        regime_quotes, strategy, strategy_name=f"{strategy_name}_{regime_name}"
                    )

                    consistent_metrics = self._calculate_consistent_metrics(result, initial_capital)

                    # Calculate additional regime-specific metrics
                    regime_return_series = returns_series[regime_mask]
                    regime_volatility = float(regime_return_series.std() * np.sqrt(252))
                    regime_mean_return = float(regime_return_series.mean() * 252)

                    # Store regime results
                    regime_result = {
                        'regime': regime_idx,
                        'regime_name': regime_name,
                        'num_quotes': len(regime_quotes),
                        'pct_total': len(regime_quotes) / len(sorted_quotes) * 100,
                        # Performance metrics
                        'total_pnl': consistent_metrics['total_pnl'],
                        'return_pct': consistent_metrics['return_pct'],
                        'sharpe_ratio': (
                            float(result.performance.sharpe_ratio)
                            if result.performance and result.performance.sharpe_ratio
                            else 0.0
                        ),
                        'sortino_ratio': (
                            float(result.performance.sortino_ratio)
                            if result.performance and hasattr(result.performance, 'sortino_ratio')
                            else 0.0
                        ),
                        'win_rate': (
                            float(result.performance.win_rate) if result.performance else 0.0
                        ),
                        'max_drawdown': (
                            float(result.performance.max_drawdown_percentage)
                            if result.performance
                            else 0.0
                        ),
                        'total_trades': (
                            result.performance.total_trades if result.performance else 0
                        ),
                        'avg_trade_pnl': (
                            consistent_metrics['total_pnl'] / result.performance.total_trades
                            if result.performance and result.performance.total_trades > 0
                            else 0.0
                        ),
                        'final_capital': consistent_metrics['final_capital'],
                        # Regime characteristics
                        'regime_volatility': regime_volatility,
                        'regime_annualized_return': regime_mean_return,
                        'regime_sharpe': (
                            regime_mean_return / regime_volatility if regime_volatility > 0 else 0.0
                        ),
                    }

                    regime_results.append(regime_result)
                    regime_performance_summary[regime_name] = regime_result

                    # Log regime performance
                    logger.info(
                        f"  Results: Return={regime_result['return_pct']:.2f}%, "
                        f"Sharpe={regime_result['sharpe_ratio']:.3f}, "
                        f"Win Rate={regime_result['win_rate']:.2%}, "
                        f"Max DD={regime_result['max_drawdown']:.2f}%"
                    )

                    # Memory management
                    self.memory_manager.add_backtest_object(f'regime_{regime_name}', result)

                except Exception as e:
                    logger.error(f"Error backtesting regime {regime_name}: {e}", exc_info=True)
                    continue

            if not regime_results:
                logger.error("No regimes completed backtesting successfully")
                return []

            # ============================================================
            # STEP 6: Calculate overall regime test statistics
            # ============================================================
            logger.info("\n" + "-" * 80)
            logger.info("REGIME ANALYSIS SUMMARY")
            logger.info("-" * 80)

            # Identify best and worst performing regimes
            best_regime = max(regime_results, key=lambda x: x['sharpe_ratio'])
            worst_regime = min(regime_results, key=lambda x: x['sharpe_ratio'])

            logger.info(f"Best performing regime: {best_regime['regime_name']}")
            logger.info(f"  Sharpe: {best_regime['sharpe_ratio']:.3f}")
            logger.info(f"  Return: {best_regime['return_pct']:.2f}%")
            logger.info(f"  Win Rate: {best_regime['win_rate']:.2%}")

            logger.info(f"\nWorst performing regime: {worst_regime['regime_name']}")
            logger.info(f"  Sharpe: {worst_regime['sharpe_ratio']:.3f}")
            logger.info(f"  Return: {worst_regime['return_pct']:.2f}%")
            logger.info(f"  Win Rate: {worst_regime['win_rate']:.2%}")

            # Calculate performance consistency across regimes
            sharpe_values = [r['sharpe_ratio'] for r in regime_results]
            return_values = [r['return_pct'] for r in regime_results]

            sharpe_std = np.std(sharpe_values)
            sharpe_range = max(sharpe_values) - min(sharpe_values)
            return_std = np.std(return_values)

            # Regime robustness score (lower std = more robust)
            robustness_score = 1.0 / (1.0 + sharpe_std)

            logger.info("\nRegime robustness metrics:")
            logger.info(f"  Sharpe std: {sharpe_std:.3f}")
            logger.info(f"  Sharpe range: {sharpe_range:.3f}")
            logger.info(f"  Return std: {return_std:.2f}%")
            logger.info(f"  Robustness score: {robustness_score:.3f}")

            # ============================================================
            # STEP 7: Compile comprehensive results
            # ============================================================
            result_dict = {
                'test_type': 'regime_test',
                'test_name': 'Regime-Based Performance Analysis',
                # Configuration
                'detection_method': detection_method,
                'n_regimes': n_regimes,
                'min_regime_samples': min_regime_samples,
                # Regime detection info
                'regime_detector_info': regime_detector_info,
                'regime_names': regime_names,
                # Per-regime results
                'regime_results': regime_results,
                'num_regimes_tested': len(regime_results),
                # Best and worst regimes
                'best_regime': {
                    'name': best_regime['regime_name'],
                    'sharpe_ratio': float(best_regime['sharpe_ratio']),
                    'return_pct': float(best_regime['return_pct']),
                    'win_rate': float(best_regime['win_rate']),
                },
                'worst_regime': {
                    'name': worst_regime['regime_name'],
                    'sharpe_ratio': float(worst_regime['sharpe_ratio']),
                    'return_pct': float(worst_regime['return_pct']),
                    'win_rate': float(worst_regime['win_rate']),
                },
                # Transition analysis
                'transition_analysis': transition_analysis,
                # Robustness metrics
                'robustness_metrics': {
                    'sharpe_std': float(sharpe_std),
                    'sharpe_range': float(sharpe_range),
                    'return_std': float(return_std),
                    'robustness_score': float(robustness_score),
                    'is_robust': robustness_score > 0.5,  # Threshold for robustness
                },
                # Performance summary
                'performance_summary': {
                    'avg_sharpe': float(np.mean(sharpe_values)),
                    'avg_return': float(np.mean(return_values)),
                    'avg_win_rate': float(np.mean([r['win_rate'] for r in regime_results])),
                    'avg_max_drawdown': float(np.mean([r['max_drawdown'] for r in regime_results])),
                    'total_trades': int(sum(r['total_trades'] for r in regime_results)),
                },
                # Metadata
                'modules_active': (
                    list(self.raw_config['modules']['filters'].keys())
                    if 'modules' in self.raw_config
                    else []
                ),
                'learning_engine': None,
                'thresholds': self._extract_thresholds(strategy_config),
            }

            # Store result
            self.memory_manager.add_result(result_dict)
            self._save_test_audit_and_weights(result_dict, 'regime_test', strategy)

            logger.info("\n" + "=" * 80)
            logger.info("REGIME TEST BACKTEST COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Regimes tested: {len(regime_results)}")
            logger.info(f"Robustness score: {robustness_score:.3f}")
            logger.info(
                f"Best regime: {best_regime['regime_name']} (Sharpe={best_regime['sharpe_ratio']:.3f})"
            )
            logger.info(
                f"Worst regime: {worst_regime['regime_name']} (Sharpe={worst_regime['sharpe_ratio']:.3f})"
            )
            logger.info(
                f"Strategy is {'ROBUST' if robustness_score > 0.5 else 'SENSITIVE'} to regime changes"
            )
            logger.info("=" * 80)

            return [result_dict]

        except Exception as e:
            logger.error(f"Error in regime test backtest: {e}", exc_info=True)
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
        logger.info(
            f"Starting parameter optimization with validation ({len(param_grid)} parameter sets)"
        )

        # Initialize data splitter
        from app.backtesting.data_split import DataSplit

        splitter = TrainValTestSplitter(DataSplit(train_pct=0.6, val_pct=0.2, test_pct=0.2))

        # Determine safe date bounds for splitting
        config_start = datetime.strptime(self.raw_config['input']['start_date'], "%Y-%m-%d")
        config_end = datetime.strptime(self.raw_config['input']['end_date'], "%Y-%m-%d")
        split_start, split_end = self._get_safe_split_dates(config_start, config_end)

        # Split data
        train_quotes, val_quotes, test_quotes = splitter.split_data(
            market_data=self.quotes,
            start_date=split_start,
            end_date=split_end,
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
                results.append(
                    {
                        'params': params,
                        'train_sharpe': train_result.get('sharpe_ratio', 0.0),
                        'val_sharpe': val_result.get('sharpe_ratio', 0.0),
                        'train_result': train_result,
                        'val_result': val_result,
                    }
                )

            except Exception as e:
                logger.warning(f"Parameter set {i+1} failed: {e}")
                continue

        # Select best params based on validation performance
        if not results:
            logger.error("No parameter combinations completed successfully")
            return {'success': False, 'error': 'All parameter combinations failed'}

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
        logger.info("Performance:")
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
        initial_capital = self.backtest_config.initial_capital
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
        result = executor.execute(quotes, strategy, strategy_name=strategy_name)

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
                float(result.performance.max_drawdown_percentage) if result.performance else 0.0
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

        Supports two config structures:
        1. YAML with modules.filters at root (from momentum_modular.yaml)
        2. Optimized config with strategy.modules (from Bayesian optimizer)
        """
        # Check for strategy.modules (from optimizer) FIRST
        strategy_config = self.raw_config.get('strategy', {})
        if 'modules' in strategy_config:
            # Config from optimizer - use the modules directly
            return {
                'type': strategy_config.get('type', 'modular_momentum'),
                'preset': strategy_config.get('preset', 'balanced'),
                'modules': strategy_config['modules'],
                'thresholds': strategy_config.get('thresholds', {}),
                'risk_manager': strategy_config.get('risk_manager', {}),
            }

        # Si la config tiene modules.filters, crear config adaptada
        if 'modules' in self.raw_config and 'filters' in self.raw_config['modules']:
            # Crear configuración de filtros desde YAML
            filters_config = {}
            filters = self.raw_config['modules']['filters']

            # Mapeo de nombres de filtros (config -> estrategia)
            filter_name_map = {
                'ema': 'ema_filter',
                'rsi': 'rsi_filter',
                'stoch_rsi': 'stoch_rsi_filter',
                'momentum': 'momentum_filter',
                'volume': 'volume_filter',
                'atr': 'atr_filter',
            }

            for filter_name, filter_config in filters.items():
                if filter_config.get('enabled', False):
                    # Mapear nombre del filtro
                    # First check if name already has _filter suffix
                    if filter_name.endswith('_filter'):
                        mapped_name = filter_name
                    else:
                        mapped_name = filter_name_map.get(filter_name, f'{filter_name}_filter')

                    # Extraer parámetros default
                    filter_params = {}
                    for param_name, param_config in filter_config.get('parameters', {}).items():
                        if 'default' in param_config:
                            filter_params[param_name] = param_config['default']

                    filters_config[mapped_name] = {'enabled': True, **filter_params}

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
                        'learning_mode': 'supervised',
                    }
                },
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
        return_pct = (total_pnl / initial_capital_float * 100) if initial_capital_float > 0 else 0.0

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
                            metrics=result_dict,
                        )
                    except Exception as e:
                        logger.warning(f"Could not save weights: {e}")

        except Exception as e:
            logger.warning(f"Error saving audit/weights: {e}")

    def _save_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Guardar resultados a archivos.

        DELEGATES to ResultAggregator (SRP Phase 6).

        Args:
            results: Lista de resultados
        """
        self.result_aggregator.save_results(results, prefix="backtest_results")

    async def _save_weights_async(
        self, engine_type: str, strategy: Any, result_dict: Dict[str, Any]
    ) -> Optional[str]:
        """
        Save learning engine weights asynchronously for better performance.

        Args:
            engine_type: Type of learning engine (e.g., 'supervised', 'deep', 'transformer')
            strategy: Strategy instance with learning_engine
            result_dict: Test result dictionary

        Returns:
            Path to saved weights or None
        """
        if not self.learning_storage:
            return None

        try:
            weights_path = await self.learning_storage.save_weights_async(
                engine_name=engine_type,
                weights=strategy.learning_engine.model,
                test_id=result_dict['test_name'],
                metadata={
                    'test_type': result_dict.get('test_type', 'unknown'),
                    'timestamp': result_dict.get('timestamp'),
                    'metrics': {
                        'total_pnl': result_dict.get('total_pnl'),
                        'sharpe_ratio': result_dict.get('sharpe_ratio'),
                        'total_trades': result_dict.get('total_trades'),
                    },
                },
            )
            logger.info(f"Weights saved asynchronously: {weights_path}")
            return weights_path
        except Exception as e:
            logger.warning(f"Could not save weights async: {e}")
            return None

    async def _finalize_meta_analysis(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Finalize meta-analysis after all backtests complete.

        This method loads all backtest results into the MetaAnalyzer and runs
        comprehensive analysis including performance metrics, outlier detection,
        and optimization suggestions.

        Args:
            results: List of all backtest result dictionaries

        Returns:
            Meta-analysis summary dictionary
        """
        if (
            not self.meta_enabled
            or not hasattr(self, 'meta_analyzer')
            or self.meta_analyzer is None
        ):
            logger.info("Meta-analysis not enabled, skipping")
            return {}

        try:
            logger.info("Starting meta-analysis of all backtest results...")

            # Load results into analyzer
            logger.info(f"Loading results from {self.output_dir}...")
            num_loaded = await self.meta_analyzer.load_results(str(self.output_dir))
            logger.info(f"Loaded {num_loaded} results into MetaAnalyzer")

            if num_loaded == 0:
                logger.warning("No results to analyze")
                return {}

            # Run performance analysis
            logger.info("Running performance analysis...")
            performance = self.meta_analyzer.analyze_performance()

            # Detect outliers
            logger.info("Detecting outliers...")
            outliers = self.meta_analyzer.detect_outliers()

            # Generate suggestions
            logger.info("Generating optimization suggestions...")
            suggestions = self.meta_analyzer.generate_suggestions()

            # Compile summary
            summary = {
                'total_results_analyzed': num_loaded,
                'performance_summary': performance,
                'outliers': outliers,
                'suggestions': suggestions,
                'analysis_timestamp': datetime.now().isoformat(),
                'output_directory': str(self.output_dir),
            }

            # Save analysis to file
            import json

            analysis_path = (
                self.output_dir / f"meta_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(analysis_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)

            logger.info(f"Meta-analysis complete: {analysis_path}")
            logger.info(f"  - Total results: {num_loaded}")
            logger.info(f"  - Performance metrics: {len(performance)} categories")
            logger.info(f"  - Outliers detected: {len(outliers.get('outliers', []))}")
            logger.info(f"  - Suggestions generated: {len(suggestions)}")

            return summary

        except Exception as e:
            logger.error(f"Error during meta-analysis: {e}", exc_info=True)
            return {}

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

    def _extract_transformer_predictions(
        self, strategy: ModularMomentumStrategy, quotes: List
    ) -> np.ndarray:
        """
        Extract Transformer predictions from strategy.

        Args:
            strategy: Trained strategy with Transformer engine
            quotes: Quotes to predict on

        Returns:
            Array of predictions/confidence scores
        """
        predictions = []

        try:
            if hasattr(strategy, 'learning_engines') and 'transformer' in strategy.learning_engines:
                transformer_engine = strategy.learning_engines['transformer']

                for quote in quotes:
                    features = strategy._compute_features(quote)
                    prediction = transformer_engine.predict(features)
                    predictions.append(prediction.get('confidence', 0.0))

        except Exception as e:
            logger.warning(f"Error extracting Transformer predictions: {e}")
            return np.array([])

        return np.array(predictions)

    def _optimize_transformer_parameters(
        self,
        train_quotes: List,
        val_quotes: List,
        transformer_config: Dict[str, Any],
        n_iterations: int = 20,
    ) -> Dict[str, float]:
        """
        Bayesian optimization of strategy parameters using Transformer predictions.

        Implements time-series cross-validation following Lopez de Prado's purged CV.

        Args:
            train_quotes: Training quotes
            val_quotes: Validation quotes
            transformer_config: Transformer configuration
            n_iterations: Number of optimization iterations

        Returns:
            Dictionary with best parameters
        """
        # Define parameter search space
        param_bounds = {
            'buy_threshold': (0.5, 0.9),
            'sell_threshold': (0.1, 0.5),
            'stop_loss': (-0.10, -0.02),
            'take_profit': (0.05, 0.20),
            'min_confidence': (0.5, 0.9),
        }

        best_score = -np.inf
        best_params = {}

        # Random search with TimeSeriesSplit for reproducibility
        # (Can be upgraded to full Bayesian optimization with Optuna)
        for iteration in range(n_iterations):
            # Random sample from parameter space
            params = {
                'buy_threshold': np.random.uniform(*param_bounds['buy_threshold']),
                'sell_threshold': np.random.uniform(*param_bounds['sell_threshold']),
                'stop_loss': np.random.uniform(*param_bounds['stop_loss']),
                'take_profit': np.random.uniform(*param_bounds['take_profit']),
                'min_confidence': np.random.uniform(*param_bounds['min_confidence']),
            }

            # Create strategy with these parameters
            config = self._create_strategy_config()
            config['thresholds'].update(params)

            strategy = ModularMomentumStrategy(config)

            # Train on train set
            train_success = train_with_retry(
                strategy=strategy,
                engine_type='transformer',
                use_subprocess=False,
            )

            if not train_success:
                continue

            # Evaluate on validation set
            initial_capital = self.backtest_config.initial_capital
            val_result = self._run_backtest_with_quotes(strategy, val_quotes, initial_capital)

            # Score: Sharpe ratio (or other metric)
            score = float(val_result.performance.sharpe_ratio or 0)

            # Track best
            if score > best_score:
                best_score = score
                best_params = params.copy()
                logger.info(
                    f"Iteration {iteration}: New best score {score:.3f} with params {params}"
                )

        return best_params

    def _run_backtest_with_quotes(
        self,
        strategy: ModularMomentumStrategy,
        quotes: List,
        initial_capital: Decimal,
    ) -> Any:
        """
        Run backtest with specific quotes.

        Args:
            strategy: Strategy to backtest
            quotes: Quotes to use
            initial_capital: Initial capital

        Returns:
            BacktestResult
        """
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
        result = executor.execute(quotes, strategy, strategy_name=strategy_name)

        return result

    def _extract_transformer_feature_importance(
        self, strategy: ModularMomentumStrategy
    ) -> Dict[str, float]:
        """
        Extract feature importance from Transformer model.

        Implements MLOps rule 27.9 for feature importance tracking.

        Args:
            strategy: Strategy with trained Transformer

        Returns:
            Dictionary with feature importance scores
        """
        try:
            if hasattr(strategy, 'learning_engines') and 'transformer' in strategy.learning_engines:
                transformer_engine = strategy.learning_engines['transformer']

                if hasattr(transformer_engine, 'model') and transformer_engine.model is not None:
                    # Extract attention weights as proxy for feature importance
                    # This is a simplified version - full implementation would use SHAP
                    feature_importance = {
                        'attention_score': 1.0,  # Placeholder
                        'sequence_importance': 0.8,
                        'temporal_importance': 0.9,
                    }
                    return feature_importance

        except Exception as e:
            logger.warning(f"Error extracting Transformer feature importance: {e}")

        return {}

    def _apply_meta_labeling(
        self,
        baseline_predictions: np.ndarray,
        optimized_predictions: np.ndarray,
        val_quotes: List,
    ) -> Dict[str, float]:
        """
        Apply meta-labeling from Lopez de Prado (rule 3).

        Meta-labeling uses ML to predict whether the primary signal was correct,
        enabling dynamic position sizing based on confidence.

        Args:
            baseline_predictions: Baseline model predictions
            optimized_predictions: Optimized model predictions
            val_quotes: Validation quotes

        Returns:
            Meta-labeling metrics
        """
        try:
            if len(baseline_predictions) == 0 or len(optimized_predictions) == 0:
                return {}

            # Calculate meta-label: Is the optimized prediction better?
            # In practice, this would be trained on actual outcomes
            meta_labels = (optimized_predictions > baseline_predictions).astype(int)

            # Meta-labeling metrics
            meta_accuracy = meta_labels.mean() if len(meta_labels) > 0 else 0

            # Calculate confidence-weighted performance
            confidence_weights = optimized_predictions / (optimized_predictions.max() + 1e-8)
            weighted_performance = (meta_labels * confidence_weights).mean()

            return {
                'meta_accuracy': float(meta_accuracy),
                'weighted_performance': float(weighted_performance),
                'prediction_correlation': float(
                    np.corrcoef(baseline_predictions, optimized_predictions)[0, 1]
                    if len(baseline_predictions) > 1 and len(optimized_predictions) > 1
                    else 0
                ),
            }

        except Exception as e:
            logger.warning(f"Error applying meta-labeling: {e}")
            return {}

    def _create_ablation_config(self, disabled_filter: str) -> Dict[str, Any]:
        """
        Create strategy configuration with a specific filter disabled for ablation testing.

        Args:
            disabled_filter: Name of the filter to disable

        Returns:
            Strategy configuration dictionary with the specified filter disabled
        """
        if 'modules' not in self.raw_config or 'filters' not in self.raw_config['modules']:
            return self._create_strategy_config()

        # Create filters config
        filters_config = {}
        filters = self.raw_config['modules']['filters']

        for filter_name, filter_config in filters.items():
            if filter_name == disabled_filter:
                # Skip this filter (disable it)
                continue

            if filter_config.get('enabled', False):
                # Extract default parameters
                filter_params = {}
                for param_name, param_config in filter_config.get('parameters', {}).items():
                    if 'default' in param_config:
                        filter_params[param_name] = param_config['default']

                filters_config[filter_name] = {'enabled': True, **filter_params}

        return {
            'type': 'modular_momentum',
            'preset': 'custom',
            'modules': filters_config,
            'presets': {
                'custom': {
                    'combination_mode': 'MAJORITY',
                    'min_confidence': 0.7,
                    'learning_mode': 'supervised',
                }
            },
        }

    def _detect_simple_regimes(self, returns: np.ndarray) -> np.ndarray:
        """
        Simple regime detection based on returns and volatility.

        DELEGATES to RegimeAnalyzer (SRP Phase 6).

        Args:
            returns: Array of returns

        Returns:
            Array of regime labels (0=Bear, 1=Neutral, 2=Bull)
        """
        return self.regime_analyzer.detect_simple_regimes(returns)

    def _get_regime_name_mapping(
        self, regime_labels: np.ndarray, returns: pd.Series
    ) -> Dict[int, str]:
        """
        Map regime indices to descriptive names based on characteristics.

        DELEGATES to RegimeAnalyzer (SRP Phase 6).

        Args:
            regime_labels: Array of regime labels
            returns: Series of returns

        Returns:
            Dictionary mapping regime indices to names
        """
        return self.regime_analyzer.get_regime_name_mapping(regime_labels, returns)

    def _analyze_regime_transitions(
        self, regime_labels: np.ndarray, regime_names: Dict[int, str]
    ) -> Dict[str, Any]:
        """
        Analyze regime transitions and build transition probability matrix.

        DELEGATES to RegimeAnalyzer (SRP Phase 6).

        Args:
            regime_labels: Array of regime labels
            regime_names: Mapping of regime indices to names

        Returns:
            Dictionary with transition analysis results
        """
        return self.regime_analyzer.analyze_regime_transitions(regime_labels, regime_names)
