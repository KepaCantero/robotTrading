"""
HyperparameterOptimizer - Sistema de optimización automatizada para ModularMomentumStrategy.
"""

import json
import logging
import random
from datetime import datetime
from decimal import Decimal
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.backtesting.engine import SimpleBacktester
from app.backtesting.models import BacktestConfig
from app.models.market_data import Quote
from app.strategies.momentum_modular.strategy import ModularMomentumStrategy

logger = logging.getLogger(__name__)


class HyperparameterOptimizer:
    """
    Sistema de optimización automatizada de hiperparámetros.

    Ejecuta múltiples backtests variando parámetros del strategy y learning engine
    para encontrar la combinación óptima que maximice métricas de performance.
    """

    def __init__(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: Decimal = Decimal("100000"),
        optimization_metric: str = "sharpe_ratio",  # "sharpe_ratio", "total_pnl", "win_rate"
        optimization_method: str = "grid_search",  # "grid_search", "random_search", "bayesian"
    ):
        """
        Inicializar optimizador.

        Args:
            symbol: Símbolo del stock a optimizar
            start_date: Fecha de inicio (1 año de datos)
            end_date: Fecha de fin
            initial_capital: Capital inicial
            optimization_metric: Métrica a optimizar ("sharpe_ratio", "total_pnl", "win_rate")
            optimization_method: Método de optimización ("grid_search", "random_search", "bayesian")
        """
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.optimization_metric = optimization_metric
        self.optimization_method = optimization_method

        self.results: List[Dict[str, Any]] = []
        self.best_config: Optional[Dict[str, Any]] = None
        self.best_score: float = float('-in')

        # Espacio de búsqueda de parámetros
        self.parameter_space = self._define_parameter_space()

    def _define_parameter_space(self) -> Dict[str, List[Any]]:
        """Definir espacio de búsqueda de parámetros."""
        return {
            # Presets de estrategia
            "preset": ["conservative", "balanced", "aggressive"],
            # Learning engine
            "enable_learning": [True, False],
            "learning_engine_type": ["supervised", "deep", "reinforcement"],
            "learning_algorithm": {
                "supervised": ["random_forest", "xgboost", "neural_network"],
                "deep": ["lstm", "gru", "transformer"],
                "reinforcement": ["ppo", "a2c", "ddpg"],
            },
            # Parámetros de filtros
            "ema_fast_period": [10, 12, 14, 16],
            "ema_slow_period": [24, 26, 28, 30],
            "rsi_period": [12, 14, 16],
            # FIXED: Now using single buy_threshold and sell_threshold (standard RSI)
            "rsi_buy_threshold": [25, 30, 35, 40],  # BUY when RSI <= threshold (oversold)
            "rsi_sell_threshold": [65, 70, 75, 80],  # SELL when RSI >= threshold (overbought)
            "stoch_rsi_oversold": [15, 20, 25],  # StochRSI oversold threshold
            "stoch_rsi_overbought": [75, 80, 85],  # StochRSI overbought threshold
            "momentum_threshold": [0.01, 0.015, 0.02, 0.025],
            "volume_threshold": [1.05, 1.1, 1.15, 1.2],
            "atr_percentile_threshold": [55, 60, 65, 70],
            # Parámetros de riesgo
            "max_position_size": [0.05, 0.10, 0.15, 0.20],
            "stop_loss_pct": [0.02, 0.025, 0.03],
            "take_profit_pct": [0.06, 0.08, 0.10],
            # Learning engine parameters
            "min_success_probability": [0.5, 0.55, 0.6, 0.65],
            "rebalance_frequency_days": [5, 7, 10, 14],
        }

    def optimize(
        self, max_iterations: int = 1000, random_seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ejecutar optimización.

        Args:
            max_iterations: Número máximo de iteraciones/configuraciones a probar
            random_seed: Seed para reproducibilidad

        Returns:
            Dict con mejor configuración y resultados
        """
        if random_seed:
            random.seed(random_seed)
            np.random.seed(random_seed)

        logger.info("🚀 Iniciando optimización de hiperparámetros")
        logger.info(f"   Símbolo: {self.symbol}")
        logger.info(f"   Período: {self.start_date.date()} - {self.end_date.date()}")
        logger.info(f"   Métrica objetivo: {self.optimization_metric}")
        logger.info(f"   Método: {self.optimization_method}")
        logger.info(f"   Máximo de iteraciones: {max_iterations}")

        if self.optimization_method == "grid_search":
            configs = self._generate_grid_search_configs(max_iterations)
        elif self.optimization_method == "random_search":
            configs = self._generate_random_search_configs(max_iterations)
        else:
            raise ValueError(f"Método de optimización no soportado: {self.optimization_method}")

        logger.info(f"📊 Generadas {len(configs)} configuraciones a probar")

        # Ejecutar backtests
        for i, config in enumerate(configs):
            try:
                logger.info(f"\n{'='*80}")
                logger.info(f"🔄 Iteración {i+1}/{len(configs)}")
                logger.info(f"   Config: {self._config_summary(config)}")

                result = self._run_backtest(config)

                if result:
                    score = self._calculate_score(result)
                    self.results.append(
                        {'iteration': i + 1, 'config': config, 'result': result, 'score': score}
                    )

                    # Actualizar mejor resultado
                    if score > self.best_score:
                        self.best_score = score
                        self.best_config = config.copy()
                        logger.info(f"✅ ¡Nuevo mejor resultado! Score: {score:.4f}")

                    logger.info(
                        f"   Score: {score:.4f} | PnL: ${result.get('total_pnl', 0):.2f} | "
                        f"Sharpe: {result.get('sharpe_ratio', 0):.2f} | "
                        f"Win Rate: {result.get('win_rate', 0):.1f}%"
                    )

            except Exception as e:
                logger.error(f"❌ Error en iteración {i+1}: {e}", exc_info=True)
                continue

        # Generar reporte
        report = self._generate_report()

        # Guardar resultados
        self._save_results()

        return {
            'best_config': self.best_config,
            'best_score': self.best_score,
            'total_iterations': len(self.results),
            'report': report,
        }

    def _generate_grid_search_configs(self, max_iterations: int) -> List[Dict[str, Any]]:
        """Generar configuraciones usando grid search."""
        configs = []

        # Parámetros principales (prioridad alta)
        main_params = {
            'preset': self.parameter_space['preset'],
            'enable_learning': self.parameter_space['enable_learning'],
            'learning_engine_type': self.parameter_space['learning_engine_type'],
            'rsi_buy_threshold': self.parameter_space['rsi_buy_threshold'],
            'momentum_threshold': self.parameter_space['momentum_threshold'],
            'volume_threshold': self.parameter_space['volume_threshold'],
        }

        # Generar combinaciones principales
        main_combinations = list(product(*main_params.values()))

        for main_combo in main_combinations[:max_iterations]:
            config = dict(zip(main_params.keys(), main_combo))

            # Añadir parámetros secundarios (valores fijos o aleatorios)
            config['ema_fast_period'] = random.choice(self.parameter_space['ema_fast_period'])
            config['ema_slow_period'] = random.choice(self.parameter_space['ema_slow_period'])
            config['rsi_period'] = random.choice(self.parameter_space['rsi_period'])
            config['rsi_sell_threshold'] = random.choice(self.parameter_space['rsi_sell_threshold'])
            config['atr_percentile_threshold'] = random.choice(
                self.parameter_space['atr_percentile_threshold']
            )
            config['max_position_size'] = random.choice(self.parameter_space['max_position_size'])

            # Learning algorithm
            if config['enable_learning'] and config['learning_engine_type']:
                algorithms = self.parameter_space['learning_algorithm'].get(
                    config['learning_engine_type'], []
                )
                if algorithms:
                    config['learning_algorithm'] = random.choice(algorithms)
                    config['min_success_probability'] = random.choice(
                        self.parameter_space['min_success_probability']
                    )
                    config['rebalance_frequency_days'] = random.choice(
                        self.parameter_space['rebalance_frequency_days']
                    )

            configs.append(config)

        return configs[:max_iterations]

    def _generate_random_search_configs(self, max_iterations: int) -> List[Dict[str, Any]]:
        """Generar configuraciones usando random search."""
        configs = []

        for _ in range(max_iterations):
            config = {
                'preset': random.choice(self.parameter_space['preset']),
                'enable_learning': random.choice(self.parameter_space['enable_learning']),
                'ema_fast_period': random.choice(self.parameter_space['ema_fast_period']),
                'ema_slow_period': random.choice(self.parameter_space['ema_slow_period']),
                'rsi_period': random.choice(self.parameter_space['rsi_period']),
                'rsi_buy_threshold': random.choice(self.parameter_space['rsi_buy_threshold']),
                'rsi_sell_threshold': random.choice(self.parameter_space['rsi_sell_threshold']),
                'stoch_rsi_oversold': random.choice(self.parameter_space.get('stoch_rsi_oversold', [20])),
                'stoch_rsi_overbought': random.choice(self.parameter_space.get('stoch_rsi_overbought', [80])),
                'momentum_threshold': random.choice(self.parameter_space['momentum_threshold']),
                'volume_threshold': random.choice(self.parameter_space['volume_threshold']),
                'atr_percentile_threshold': random.choice(
                    self.parameter_space['atr_percentile_threshold']
                ),
                'max_position_size': random.choice(self.parameter_space['max_position_size']),
                'stop_loss_pct': random.choice(self.parameter_space['stop_loss_pct']),
                'take_profit_pct': random.choice(self.parameter_space['take_profit_pct']),
            }

            # Learning engine (si está habilitado)
            if config['enable_learning']:
                config['learning_engine_type'] = random.choice(
                    self.parameter_space['learning_engine_type']
                )
                algorithms = self.parameter_space['learning_algorithm'].get(
                    config['learning_engine_type'], []
                )
                if algorithms:
                    config['learning_algorithm'] = random.choice(algorithms)
                    config['min_success_probability'] = random.choice(
                        self.parameter_space['min_success_probability']
                    )
                    config['rebalance_frequency_days'] = random.choice(
                        self.parameter_space['rebalance_frequency_days']
                    )
            else:
                config['learning_engine_type'] = None
                config['learning_algorithm'] = None

            configs.append(config)

        return configs

    def _run_backtest(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ejecutar backtest con configuración específica."""
        try:
            # Crear configuración de estrategia
            strategy_config = self._build_strategy_config(config)

            # Crear estrategia
            strategy = ModularMomentumStrategy(strategy_config)

            # Cargar datos históricos
            from app.data.feeds import YahooFinanceFeed
            from app.models.market_data import DataFeedConfig, DataFeedType

            config = DataFeedConfig(
                feed_type=DataFeedType.YAHOO_FINANCE,
                api_key="",
                rate_limit=5,
                timeout_seconds=30,
            )
            provider = YahooFinanceFeed(config)
            # Run async method in sync context
            import asyncio

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            historical_data = loop.run_until_complete(
                provider.get_historical_data(
                    symbol=self.symbol,
                    start_date=self.start_date,
                    end_date=self.end_date,
                )
            )

            # Convert HistoricalData objects to DataFrame
            import pandas as pd

            df_data = []
            for hist in historical_data:
                df_data.append(
                    {
                        'open': float(hist.open),
                        'high': float(hist.high),
                        'low': float(hist.low),
                        'close': float(hist.close),
                        'volume': float(hist.volume),
                    }
                )
            df = pd.DataFrame(df_data)
            df.index = [hist.timestamp for hist in historical_data]

            if df is None or len(df) == 0:
                logger.warning(f"No se pudieron cargar datos para {self.symbol}")
                return None

            # Convertir a Quotes
            quotes = []
            for idx, row in df.iterrows():
                quote = Quote(
                    symbol=self.symbol,
                    timestamp=idx if isinstance(idx, datetime) else pd.to_datetime(idx),
                    bid=Decimal(str(row['close'])),
                    ask=Decimal(str(row['close'])),
                    volume=int(row.get('volume', 0)),
                    close=Decimal(str(row['close'])),
                    high=Decimal(str(row.get('high', row['close']))),
                    low=Decimal(str(row.get('low', row['close']))),
                )
                quotes.append(quote)

            # Generar señales
            signals = []
            for quote in quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)

            if not signals:
                logger.warning(f"No se generaron señales para {self.symbol}")
                return None

            # Ejecutar backtest
            backtest_config = BacktestConfig(
                initial_capital=self.initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001"),
            )

            backtester = SimpleBacktester(config=backtest_config, strategy=strategy)

            result = backtester.run_backtest(quotes, signals)

            # Extraer métricas
            return {
                'total_pnl': float(result.performance.total_pnl),
                'total_return': float(result.total_return),
                'sharpe_ratio': (
                    float(result.performance.sharpe_ratio)
                    if result.performance.sharpe_ratio
                    else 0.0
                ),
                'win_rate': float(result.performance.win_rate),
                'max_drawdown': float(result.performance.max_drawdown_percentage),
                'total_trades': result.performance.total_trades,
                'final_capital': float(result.final_capital),
                'annualized_return': (
                    float(result.annualized_return) if hasattr(result, 'annualized_return') else 0.0
                ),
            }

        except Exception as e:
            logger.error(f"Error ejecutando backtest: {e}", exc_info=True)
            return None

    def _build_strategy_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Construir configuración completa de estrategia desde parámetros."""
        # Cargar configuración base desde YAML
        from pathlib import Path

        import yaml

        config_path = (
            Path(__file__).parent.parent.parent.parent
            / "config"
            / "strategies"
            / "momentum_modular.yaml"
        )
        base_config = {}
        if config_path.exists():
            with open(config_path, 'r') as f:
                base_config = yaml.safe_load(f) or {}

        # Aplicar parámetros de optimización
        strategy_config = base_config.copy()
        strategy_config['preset'] = config.get('preset', 'balanced')

        # Ajustar parámetros de módulos
        if 'modules' not in strategy_config:
            strategy_config['modules'] = {}

        # EMA Filter
        if 'ema_filter' in strategy_config['modules']:
            ema_params = strategy_config['modules']['ema_filter'].get('parameters', {})
            ema_params['fast_period'] = config.get('ema_fast_period', 12)
            ema_params['slow_period'] = config.get('ema_slow_period', 26)

        # RSI Filter - FIXED: Now using buy_threshold and sell_threshold
        if 'rsi_filter' in strategy_config['modules']:
            rsi_params = strategy_config['modules']['rsi_filter'].get('parameters', {})
            rsi_params['period'] = config.get('rsi_period', 14)
            # Update adaptive thresholds with new single-value format
            thresholds = strategy_config['modules']['rsi_filter'].get('adaptive_thresholds', {})
            for context in thresholds:
                thresholds[context]['buy_threshold'] = config.get('rsi_buy_threshold', 30)
                thresholds[context]['sell_threshold'] = config.get('rsi_sell_threshold', 70)

        # StochRSI Filter - FIXED: Now using oversold_threshold and overbought_threshold
        if 'stoch_rsi_filter' in strategy_config['modules']:
            thresholds = strategy_config['modules']['stoch_rsi_filter'].get('thresholds', {})
            for preset in ['conservative', 'balanced', 'aggressive']:
                if preset in thresholds:
                    thresholds[preset]['oversold_threshold'] = config.get('stoch_rsi_oversold', 20)
                    thresholds[preset]['overbought_threshold'] = config.get('stoch_rsi_overbought', 80)

        # Momentum Filter
        if 'momentum_filter' in strategy_config['modules']:
            mom_params = strategy_config['modules']['momentum_filter'].get(
                'thresholds', {}
            )
            for preset in ['conservative', 'balanced', 'aggressive']:
                if preset in mom_params:
                    mom_params[preset]['min_positive_momentum'] = config.get(
                        'momentum_threshold', 0.015
                    )

        # Volume Filter
        if 'volume_filter' in strategy_config['modules']:
            vol_params = strategy_config['modules']['volume_filter'].get('parameters', {})
            vol_params['min_volume_ratio'] = config.get('volume_threshold', 1.1)

        # ATR Filter
        if 'atr_filter' in strategy_config['modules']:
            atr_params = strategy_config['modules']['atr_filter'].get('parameters', {})
            atr_params['percentile_threshold'] = config.get('atr_percentile_threshold', 60)

        # Risk parameters
        strategy_config['max_position_size'] = config.get('max_position_size', 0.10)
        strategy_config['stop_loss_pct'] = config.get('stop_loss_pct', 0.025)
        strategy_config['take_profit_pct'] = config.get('take_profit_pct', 0.08)

        # Learning engine
        if config.get('enable_learning', False):
            if 'adaptive_learning' not in strategy_config:
                strategy_config['adaptive_learning'] = {}
            strategy_config['adaptive_learning']['enabled'] = True
            strategy_config['adaptive_learning']['engine_type'] = config.get(
                'learning_engine_type', 'supervised'
            )
            strategy_config['adaptive_learning']['algorithm'] = config.get(
                'learning_algorithm', 'random_forest'
            )
            strategy_config['adaptive_learning']['min_success_probability'] = config.get(
                'min_success_probability', 0.6
            )
            strategy_config['adaptive_learning']['rebalance_frequency_days'] = config.get(
                'rebalance_frequency_days', 7
            )

        return strategy_config

    def _calculate_score(self, result: Dict[str, Any]) -> float:
        """Calcular score basado en métrica objetivo."""
        if self.optimization_metric == "sharpe_ratio":
            return result.get('sharpe_ratio', 0.0)
        elif self.optimization_metric == "total_pnl":
            return result.get('total_pnl', 0.0)
        elif self.optimization_metric == "win_rate":
            return result.get('win_rate', 0.0)
        elif self.optimization_metric == "combined":
            # Score combinado: Sharpe * 0.4 + PnL_norm * 0.3 + WinRate_norm * 0.3
            sharpe = max(0, result.get('sharpe_ratio', 0.0))
            pnl_norm = result.get('total_pnl', 0.0) / 10000.0  # Normalizar
            win_rate_norm = result.get('win_rate', 0.0) / 100.0
            return sharpe * 0.4 + pnl_norm * 0.3 + win_rate_norm * 0.3
        else:
            return result.get('sharpe_ratio', 0.0)

    def _config_summary(self, config: Dict[str, Any]) -> str:
        """Resumen de configuración para logging."""
        parts = [
            f"preset={config.get('preset')}",
            f"learning={config.get('enable_learning')}",
        ]
        if config.get('enable_learning'):
            parts.append(f"engine={config.get('learning_engine_type')}")
        parts.extend(
            [
                f"rsi_buy={config.get('rsi_buy_threshold')}",
                f"rsi_sell={config.get('rsi_sell_threshold')}",
                f"momentum={config.get('momentum_threshold')}",
                f"volume={config.get('volume_threshold')}",
            ]
        )
        return ", ".join(parts)

    def _generate_report(self) -> pd.DataFrame:
        """Generar reporte de resultados."""
        if not self.results:
            return pd.DataFrame()

        # Crear DataFrame con resultados
        report_data = []
        for res in self.results:
            row = {
                'iteration': res['iteration'],
                'score': res['score'],
                'total_pnl': res['result'].get('total_pnl', 0),
                'sharpe_ratio': res['result'].get('sharpe_ratio', 0),
                'win_rate': res['result'].get('win_rate', 0),
                'total_trades': res['result'].get('total_trades', 0),
                'max_drawdown': res['result'].get('max_drawdown', 0),
                **res['config'],
            }
            report_data.append(row)

        df = pd.DataFrame(report_data)
        df = df.sort_values('score', ascending=False)

        return df

    def _save_results(self) -> None:
        """Guardar resultados a archivo."""
        results_dir = Path(__file__).parent.parent.parent.parent / "docs" / "OPTIMIZATION_RESULTS"
        results_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Guardar mejor configuración
        if self.best_config:
            best_config_file = results_dir / f"best_config_{self.symbol}_{timestamp}.json"
            with open(best_config_file, 'w') as f:
                json.dump(
                    {
                        'symbol': self.symbol,
                        'start_date': self.start_date.isoformat(),
                        'end_date': self.end_date.isoformat(),
                        'optimization_metric': self.optimization_metric,
                        'best_score': self.best_score,
                        'best_config': self.best_config,
                        'total_iterations': len(self.results),
                    },
                    f,
                    indent=2,
                )
            logger.info(f"💾 Mejor configuración guardada: {best_config_file}")

        # Guardar reporte completo
        if self.results:
            report = self._generate_report()
            report_file = results_dir / f"optimization_report_{self.symbol}_{timestamp}.csv"
            report.to_csv(report_file, index=False)
            logger.info(f"💾 Reporte completo guardado: {report_file}")

            # Guardar resumen
            summary_file = results_dir / f"summary_{self.symbol}_{timestamp}.txt"
            with open(summary_file, 'w') as f:
                f.write("Optimización de Hiperparámetros\n")
                f.write(f"{'='*80}\n\n")
                f.write(f"Símbolo: {self.symbol}\n")
                f.write(f"Período: {self.start_date.date()} - {self.end_date.date()}\n")
                f.write(f"Métrica objetivo: {self.optimization_metric}\n")
                f.write(f"Método: {self.optimization_method}\n")
                f.write(f"Total iteraciones: {len(self.results)}\n\n")
                f.write(f"Mejor Score: {self.best_score:.4f}\n\n")
                f.write("Mejor Configuración:\n")
                f.write(json.dumps(self.best_config, indent=2))
                f.write("\n\nTop 10 Resultados:\n")
                f.write(report.head(10).to_string())
            logger.info(f"💾 Resumen guardado: {summary_file}")
