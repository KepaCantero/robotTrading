"""
Automated Backtest System - Backtest automatizado con ablation y learning engines.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from app.backtesting.data_loader import DataLoader
from app.backtesting.engine import SimpleBacktester
from app.domain.models.market_data import Quote

# Los módulos y learning engines se importan internamente por ModularMomentumStrategy
# No necesitamos importarlos aquí directamente

logger = logging.getLogger(__name__)


class PortfolioAnalyzer:
    """Analiza portfolio para seleccionar el mejor stock para backtesting."""

    def __init__(self, portfolio_config_manager):
        self.portfolio_config = portfolio_config_manager
        # Late import to avoid domain layer depending on services layer
        from app.services.portfolio_builder import PortfolioBuilder

        self.portfolio_builder = PortfolioBuilder(portfolio_config=portfolio_config_manager)

    def select_best_stock(
        self,
        criteria: str = "momentum_signal",  # "momentum_signal", "performance", "volatility"
        lookback_days: int = 365,
    ) -> tuple[str, dict]:
        """
        Seleccionar el mejor stock según criterio.

        Args:
            criteria: Criterio de selección
            lookback_days: Días hacia atrás para analizar

        Returns:
            (symbol, metrics_dict)
        """
        # Obtener símbolos disponibles
        strategy_mapping = self.portfolio_builder.get_strategy_symbols_mapping()
        all_symbols = []
        for symbols in strategy_mapping.values():
            all_symbols.extend(symbols)

        all_symbols = list(set(all_symbols))[:20]  # Limitar a 20 para velocidad

        logger.info(f"Analizando {len(all_symbols)} símbolos para seleccionar el mejor...")

        loader = DataLoader()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        best_symbol = None
        best_score = -np.inf
        best_metrics = {}

        for symbol in all_symbols:
            try:
                # Descargar datos históricos usando DataLoader
                quotes = loader.load_market_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe="1d",
                    source="csv",  # Intentar CSV primero
                )

                if not quotes or len(quotes) < 60:
                    continue

                # Convertir quotes a DataFrame
                df = pd.DataFrame(
                    [
                        {
                            "date": q.timestamp,
                            "close": float(q.close if q.close else q.last),
                            "open": float(q.open if q.open else q.last),
                            "high": float(q.high if q.high else q.last),
                            "low": float(q.low if q.low else q.last),
                            "volume": float(q.volume),
                        }
                        for q in quotes
                    ]
                )
                df.set_index("date", inplace=True)

                # Calcular métricas según criterio
                if criteria == "momentum_signal":
                    score, metrics = self._calculate_momentum_score(df)
                elif criteria == "performance":
                    score, metrics = self._calculate_performance_score(df)
                elif criteria == "volatility":
                    score, metrics = self._calculate_volatility_score(df)
                else:
                    score, metrics = self._calculate_momentum_score(df)

                if score > best_score:
                    best_score = score
                    best_symbol = symbol
                    best_metrics = metrics
                    best_metrics["symbol"] = symbol
                    best_metrics["score"] = score

            except (ValueError, KeyError, AttributeError, IndexError, TypeError) as e:
                logger.warning(f"Error analizando {symbol}: {e}")
                continue

        if best_symbol:
            logger.info(f"Mejor stock seleccionado: {best_symbol} (score: {best_score:.4f})")
            return best_symbol, best_metrics
        else:
            # Fallback a símbolo por defecto
            return "AAPL", {"symbol": "AAPL", "score": 0.0}

    def _calculate_momentum_score(self, df: pd.DataFrame) -> tuple[float, dict]:
        """Calcular score de momentum."""
        if len(df) < 20:
            return 0.0, {}

        # Calcular RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-8)
        rsi = 100 - (100 / (1 + rs))

        # Calcular momentum (ROC)
        roc = ((df["close"] - df["close"].shift(20)) / df["close"].shift(20)) * 100

        # Calcular EMA cross
        ema_fast = df["close"].ewm(span=12, adjust=False).mean()
        ema_slow = df["close"].ewm(span=26, adjust=False).mean()

        # Score basado en condiciones de momentum
        current_rsi = rsi.iloc[-1]
        current_roc = roc.iloc[-1]
        ema_bullish = ema_fast.iloc[-1] > ema_slow.iloc[-1]
        price_above_ema = df["close"].iloc[-1] > ema_fast.iloc[-1]

        score = 0.0
        score += 0.3 if (40 < current_rsi < 70) else 0  # RSI en zona de momentum
        score += 0.3 if current_roc > 2.0 else 0  # Momentum positivo fuerte
        score += 0.2 if ema_bullish else 0  # EMA cruzado alcista
        score += 0.2 if price_above_ema else 0  # Precio sobre EMA

        metrics = {
            "rsi": float(current_rsi),
            "roc": float(current_roc),
            "ema_bullish": ema_bullish,
            "return_1y": float((df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100),
        }

        return score, metrics

    def _calculate_performance_score(self, df: pd.DataFrame) -> tuple[float, dict]:
        """Calcular score basado en performance."""
        if len(df) < 2:
            return 0.0, {}

        return_pct = (df["close"].iloc[-1] / df["close"].iloc[0] - 1) * 100
        volatility = df["close"].pct_change().std() * np.sqrt(252) * 100

        sharpe = return_pct / volatility if volatility > 0 else 0

        metrics = {
            "return_1y": float(return_pct),
            "volatility": float(volatility),
            "sharpe": float(sharpe),
        }

        return sharpe, metrics

    def _calculate_volatility_score(self, df: pd.DataFrame) -> tuple[float, dict]:
        """Calcular score basado en volatilidad (menor es mejor para algunos casos)."""
        volatility = df["close"].pct_change().std() * np.sqrt(252) * 100

        # Score inverso: menor volatilidad = mayor score (hasta cierto punto)
        score = 1.0 / (1.0 + volatility / 50.0)

        metrics = {"volatility": float(volatility)}
        return score, metrics


class AutomatedBacktestRunner:
    """Ejecuta backtests automatizados con ablation y learning engines."""

    def __init__(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: Optional[Decimal] = None,
        config_path: Optional[str] = None,
    ):
        """Inicializar runner de backtest."""
        if initial_capital is None:
            initial_capital = Decimal("100000")
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital

        # Cargar configuración
        if config_path:
            import yaml

            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self._load_default_config()

        # Preparar datos
        self.quotes = self._load_historical_data()

        # Resultados
        self.results: list[dict[str, Any]] = []

    def _load_default_config(self) -> dict:
        """Cargar configuración por defecto."""
        config_path = (
            Path(__file__).parent.parent.parent.parent
            / "config"
            / "strategies"
            / "momentum_modular.yaml"
        )
        if config_path.exists():
            import yaml

            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}

    def _load_historical_data(self) -> list[Quote]:
        """Cargar datos históricos para el símbolo."""
        loader = DataLoader()
        quotes = loader.load_market_data(
            symbol=self.symbol,
            start_date=self.start_date,
            end_date=self.end_date,
            timeframe="1d",
            source="csv",  # Intentar CSV primero, luego yfinance
        )

        if not quotes or len(quotes) == 0:
            raise ValueError(f"No se pudieron cargar datos para {self.symbol}")

        logger.info(f"Cargados {len(quotes)} quotes para {self.symbol}")
        return quotes

    def run_baseline_backtest(self) -> dict[str, Any]:
        """Ejecutar backtest con todos los módulos activos (baseline)."""
        logger.info("=" * 80)
        logger.info("EJECUTANDO BACKTEST BASELINE (Todos los módulos activos)")
        logger.info("=" * 80)

        # Crear estrategia con todos los módulos
        strategy = self._create_strategy_with_modules(disable_modules=[], enable_learning=False)

        # Ejecutar backtest
        from app.backtesting.models import BacktestConfig

        config = BacktestConfig(
            initial_capital=self.initial_capital,
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.001"),
        )
        backtester = SimpleBacktester(config=config, strategy=strategy)

        # Generar señales desde la estrategia para cada quote
        signals = []
        for quote in self.quotes:
            quote_signals = strategy.generate_signals(quote)
            signals.extend(quote_signals)

        result = backtester.run_backtest(self.quotes, signals=signals)

        metrics = self._extract_metrics(result, "BASELINE - All Modules")
        self.results.append(metrics)

        return metrics

    def run_ablation_study(self) -> list[dict[str, Any]]:
        """Ejecutar estudio de ablation desactivando módulos uno por uno."""
        logger.info("=" * 80)
        logger.info("EJECUTANDO ESTUDIO DE ABLATION")
        logger.info("=" * 80)

        modules_to_test = [
            "ema_filter",
            "rsi_filter",
            "stoch_rsi_filter",
            "momentum_filter",
            "volume_filter",
            "atr_filter",
        ]

        ablation_results = []

        for module_name in modules_to_test:
            logger.info(f"\n--- Desactivando {module_name} ---")

            strategy = self._create_strategy_with_modules(
                disable_modules=[module_name], enable_learning=False
            )

            from app.backtesting.models import BacktestConfig

            config = BacktestConfig(
                initial_capital=self.initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001"),
            )
            backtester = SimpleBacktester(config=config, strategy=strategy)

            # Generar señales desde la estrategia para cada quote
            signals = []
            for quote in self.quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)

            result = backtester.run_backtest(self.quotes, signals=signals)
            metrics = self._extract_metrics(result, f"ABLATION - Without {module_name}")
            metrics["disabled_module"] = module_name
            ablation_results.append(metrics)
            self.results.append(metrics)

        return ablation_results

    def run_learning_engines_backtest(self) -> list[dict[str, Any]]:
        """Ejecutar backtests con cada learning engine."""
        logger.info("=" * 80)
        logger.info("EJECUTANDO BACKTESTS CON LEARNING ENGINES")
        logger.info("=" * 80)

        learning_results = []

        # 1. Supervised Learning
        logger.info("\n--- Supervised Learning (RandomForest) ---")
        supervised_metrics = self._run_with_learning_engine("supervised", "random_forest")
        learning_results.append(supervised_metrics)

        # 2. Deep Learning
        logger.info("\n--- Deep Learning (LSTM) ---")
        deep_metrics = self._run_with_learning_engine("deep", "lstm")
        learning_results.append(deep_metrics)

        # 3. Reinforcement Learning
        logger.info("\n--- Reinforcement Learning (PPO) ---")
        rl_metrics = self._run_with_learning_engine("reinforcement", "ppo")
        learning_results.append(rl_metrics)

        return learning_results

    def _run_with_learning_engine(self, engine_type: str, algorithm: str) -> dict[str, Any]:
        """Ejecutar backtest con un learning engine específico."""
        try:
            # Crear estrategia con learning engine
            strategy = self._create_strategy_with_modules(
                disable_modules=[],
                enable_learning=True,
                learning_engine_type=engine_type,
                learning_algorithm=algorithm,
            )

            # Entrenar modelo con datos históricos (primeros 70%)
            # CRITICAL: Add temporal gap to prevent data leakage
            split_idx = int(len(self.quotes) * 0.7)
            gap_size = min(20, int(len(self.quotes) * 0.02))  # 2% or 20 periods gap

            training_quotes = self.quotes[:split_idx]
            # Skip 'gap_size' periods between train and test to prevent leakage
            test_start_idx = split_idx + gap_size
            test_quotes = self.quotes[test_start_idx:] if test_start_idx < len(self.quotes) else []

            if len(test_quotes) < 10:
                logger.warning("⚠️ Insufficient test data after temporal gap, reducing gap")
                test_quotes = self.quotes[split_idx:]

            logger.info(
                f"Train/Test split: {len(training_quotes)} train, {gap_size} gap, {len(test_quotes)} test"
            )

            # Entrenar learning engine
            if hasattr(strategy, "learning_engine") and strategy.learning_engine:
                training_data = self._prepare_training_data(training_quotes, engine_type)
                strategy.learning_engine.train(training_data)

            # Ejecutar backtest en datos de test
            from app.backtesting.models import BacktestConfig

            config = BacktestConfig(
                initial_capital=self.initial_capital,
                commission_per_trade=Decimal("1.0"),
                slippage_percentage=Decimal("0.001"),
            )
            backtester = SimpleBacktester(config=config, strategy=strategy)

            # Generar señales desde la estrategia para cada quote
            signals = []
            for quote in test_quotes:
                quote_signals = strategy.generate_signals(quote)
                signals.extend(quote_signals)

            result = backtester.run_backtest(test_quotes, signals=signals)
            metrics = self._extract_metrics(result, f"{engine_type.upper()} - {algorithm.upper()}")
            metrics["learning_engine"] = engine_type
            metrics["algorithm"] = algorithm

            return metrics

        except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
            logger.error(f"Error ejecutando {engine_type}: {e}", exc_info=True)
            return {
                "name": f"{engine_type.upper()} - {algorithm.upper()}",
                "error": str(e),
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "return_pct": 0.0,
            }

    def _create_strategy_with_modules(
        self,
        disable_modules: list[str],
        enable_learning: bool = False,
        learning_engine_type: Optional[str] = None,
        learning_algorithm: Optional[str] = None,
    ):
        """Crear estrategia con módulos específicos activados/desactivados."""
        from app.domain.strategies.momentum_modular.strategy import ModularMomentumStrategy

        # Crear configuración para ModularMomentumStrategy
        strategy_config = {
            "name": "momentum_modular",
            "enabled": True,
            **self.config,  # Incluir toda la configuración del YAML
        }

        # Desactivar módulos solicitados
        if disable_modules:
            modules_config = strategy_config.get("modules", {})
            for module_name in disable_modules:
                if module_name in modules_config:
                    modules_config[module_name]["enabled"] = False

        # Configurar learning engine si está habilitado
        if enable_learning and learning_engine_type:
            if "adaptive_learning" not in strategy_config:
                strategy_config["adaptive_learning"] = {}
            strategy_config["adaptive_learning"]["enabled"] = True
            strategy_config["adaptive_learning"]["engine_type"] = learning_engine_type
            if learning_algorithm:
                strategy_config["adaptive_learning"]["algorithm"] = learning_algorithm

        strategy = ModularMomentumStrategy(strategy_config)

        return strategy

    def _prepare_training_data(self, quotes: list[Quote], engine_type: str) -> dict:
        """Preparar datos de entrenamiento según tipo de engine."""
        from app.backtesting.engine import SimpleBacktester
        from app.backtesting.models import BacktestConfig
        from app.domain.strategies.learning.training_data_preparator import TrainingDataPreparator

        preparator = TrainingDataPreparator()

        # Ejecutar backtest preliminar usando ModularMomentumStrategy sin learning para obtener trades históricos
        from app.domain.strategies.momentum_modular.strategy import ModularMomentumStrategy

        temp_strategy_config = {
            "name": "momentum_modular",
            "enabled": True,
            **self.config,  # Usar la misma configuración base
        }
        temp_strategy = ModularMomentumStrategy(temp_strategy_config)
        temp_config = BacktestConfig(
            initial_capital=self.initial_capital,
            commission_per_trade=Decimal("1.0"),
            slippage_percentage=Decimal("0.001"),
        )
        temp_backtester = SimpleBacktester(config=temp_config, strategy=temp_strategy)

        signals = []
        for quote in quotes:
            quote_signals = temp_strategy.generate_signals(quote)
            signals.extend(quote_signals)

        temp_result = temp_backtester.run_backtest(quotes, signals)
        historical_trades = temp_result.trades if temp_result else []

        # Preparar datos según tipo de engine
        if engine_type == "supervised":
            return preparator.prepare_supervised_training_data(
                quotes=quotes, trades=historical_trades, min_sequence_length=60
            )
        elif engine_type == "deep":
            return preparator.prepare_deep_learning_training_data(
                quotes=quotes, trades=historical_trades, sequence_length=60, min_sequence_length=120
            )
        elif engine_type == "reinforcement":
            return preparator.prepare_reinforcement_learning_data(
                quotes=quotes, initial_capital=self.initial_capital
            )

        return {}

    def _extract_metrics(self, result, name: str) -> dict[str, Any]:
        """Extraer métricas del resultado del backtest."""
        if result is None:
            return {
                "name": name,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "return_pct": 0.0,
            }

        performance = result.performance

        return {
            "name": name,
            "total_pnl": float(performance.total_pnl),
            "win_rate": float(performance.win_rate) * 100,
            "sharpe_ratio": float(performance.sharpe_ratio) if performance.sharpe_ratio else 0.0,
            "max_drawdown": float(performance.max_drawdown_percentage),
            "total_trades": performance.total_trades,
            "return_pct": float(result.total_return),
            "final_capital": float(result.final_capital),
        }

    def generate_summary_report(self) -> pd.DataFrame:
        """Generar reporte resumen de todos los backtests."""
        if not self.results:
            logger.warning("No hay resultados para generar reporte")
            return pd.DataFrame()

        df = pd.DataFrame(self.results)

        # Ordenar por Sharpe ratio (descendente)
        df = df.sort_values("sharpe_ratio", ascending=False)

        logger.info("\n" + "=" * 80)
        logger.info("RESUMEN COMPARATIVO DE BACKTESTS")
        logger.info("=" * 80)
        logger.info(f"\n{df.to_string(index=False)}")

        # Guardar a archivo
        report_dir = Path(__file__).parent.parent.parent.parent / "docs" / "BACKTEST_RESULTS"
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"automated_backtest_{self.symbol}_{timestamp}.csv"
        df.to_csv(report_file, index=False)

        logger.info(f"\nReporte guardado en: {report_file}")

        return df


def run_automated_backtest(
    symbol: Optional[str] = None,
    criteria: str = "momentum_signal",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    initial_capital: Optional[Decimal] = None,
):
    """
    Ejecutar backtest automatizado completo.

    Args:
        symbol: Símbolo específico (si None, se selecciona automáticamente)
        criteria: Criterio para seleccionar stock
        start_date: Fecha inicio (si None, usa hace 1 año)
        end_date: Fecha fin (si None, usa hoy)
        initial_capital: Capital inicial
    """
    if initial_capital is None:
        initial_capital = Decimal("100000")
    # Seleccionar stock si no se proporciona
    if symbol is None:
        # Late import to avoid domain layer depending on services layer
        from app.services.portfolio_config_manager import get_portfolio_config_manager

        portfolio_config = get_portfolio_config_manager()
        analyzer = PortfolioAnalyzer(portfolio_config)
        symbol, metrics = analyzer.select_best_stock(criteria=criteria)
        logger.info(f"Stock seleccionado: {symbol}")
        logger.info(f"Métricas: {metrics}")

    # Definir fechas
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=365)

    # Crear runner
    runner = AutomatedBacktestRunner(
        symbol=symbol, start_date=start_date, end_date=end_date, initial_capital=initial_capital
    )

    # Ejecutar backtests
    logger.info(f"\n{'=' * 80}")
    logger.info(f"INICIANDO BACKTEST AUTOMATIZADO PARA {symbol}")
    logger.info(f"Período: {start_date.date()} a {end_date.date()}")
    logger.info(f"Capital inicial: ${initial_capital:,.2f}")
    logger.info(f"{'=' * 80}\n")

    # 1. Baseline
    baseline = runner.run_baseline_backtest()

    # 2. Ablation study
    ablation_results = runner.run_ablation_study()

    # 3. Learning engines
    learning_results = runner.run_learning_engines_backtest()

    # 4. Generar reporte
    summary = runner.generate_summary_report()

    # 5. Análisis final
    logger.info("\n" + "=" * 80)
    logger.info("ANÁLISIS FINAL")
    logger.info("=" * 80)

    if len(summary) > 0:
        best = summary.iloc[0]
        logger.info(f"\n🏆 MEJOR ESTRATEGIA: {best['name']}")
        logger.info(f"   Sharpe Ratio: {best['sharpe_ratio']:.3f}")
        logger.info(f"   Return %: {best['return_pct']:.2f}%")
        logger.info(f"   Win Rate: {best['win_rate']:.2f}%")
        logger.info(f"   Max Drawdown: {best['max_drawdown']:.2f}%")
        logger.info(f"   Total Trades: {int(best['total_trades'])}")

    return {
        "symbol": symbol,
        "baseline": baseline,
        "ablation_results": ablation_results,
        "learning_results": learning_results,
        "summary": summary,
    }


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Ejecutar backtest automatizado
    results = run_automated_backtest(
        symbol=None,  # Auto-seleccionar
        criteria="momentum_signal",
        initial_capital=Decimal("100000"),
    )

    logger.debug("\n✅ Backtest automatizado completado!")
    logger.debug("Resultados guardados en: docs/BACKTEST_RESULTS/")
