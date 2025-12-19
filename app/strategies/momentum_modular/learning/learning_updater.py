"""
LearningEngineUpdater - Sistema de reentrenamiento automático para learning engines.

Integra:
- Detección de drift [TASK-4.2-DRIFT] para reentrenamiento inteligente
- Análisis de Feature Importance [TASK-4.2-FEATURE-IMPORTANCE]
- Transfer Learning [TASK-4.2-TRANSFER-LEARNING] para fine-tuning de modelos pre-entrenados

Características:
- Detección de concept drift (PSI, KS test, ADWIN)
- Detección de feature drift a nivel individual
- Detección de overfitting (train/val gap)
- Triggers automáticos de reentrenamiento basados en drift
- Feature importance analysis con 6 métodos (SHAP, Permutation, Built-in, Correlation, Attention, Stability)
- Recomendaciones automáticas de feature engineering
- Transfer Learning: Fine-tuning de modelos pre-entrenados por régimen de mercado
- Registro automático de modelos entrenados para transferencia futura
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

from .base_learning_engine import BaseLearningEngine
from .drift_detector import (
    AutoRetrainingTrigger,
    ComprehensiveDriftDetector,
    ComprehensiveDriftReport,
    OverfittingDetector,
    load_drift_config,
)
from .feature_importance import ComprehensiveFeatureAnalyzer, load_feature_importance_config
from .training_data_preparator import TrainingDataPreparator
from .transfer_learning import TransferLearningManager

logger = logging.getLogger(__name__)


def load_transfer_learning_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load Transfer Learning configuration from YAML file.

    Args:
        config_path: Path to YAML config file (optional)

    Returns:
        Dictionary with Transfer Learning configuration
    """
    if config_path is None:
        # Try multiple default locations
        from pathlib import Path
        possible_paths = [
            Path("config/transfer_learning.yaml"),
            Path(__file__).parent.parent.parent.parent.parent / "config/transfer_learning.yaml",
        ]
        for path in possible_paths:
            if path.exists():
                config_path = str(path)
                break

    if config_path:
        try:
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.debug(f"Loaded transfer learning config from {config_path}")
                return config or {}
        except Exception as e:
            logger.warning(f"Error loading transfer learning config from {config_path}: {e}")

    # Return default configuration if file not found or error loading
    return {
        "enabled": True,
        "registry_path": "models/registry",
        "fine_tuner": {
            "freeze_layers": True,
            "freeze_n_layers": 2,
            "learning_rate_multiplier": 0.1,
            "fine_tune_epochs": 10,
            "early_stopping_patience": 5,
        },
        "distiller": {
            "temperature": 3.0,
            "alpha": 0.7,
            "distillation_epochs": 50,
        },
        "market_regime": {
            "detection_window_days": 20,
            "volatility_thresholds": {"low": 0.01, "normal": 0.03, "high": 1.0},
            "trend_thresholds": {"bearish": -0.001, "bullish": 0.001},
        },
    }


class LearningEngineUpdater:
    """
    Gestiona reentrenamiento automático periódico de learning engines.

    Características:
    - Reentrenamiento periódico (cada N días)
    - Validación de lookahead bias
    - Gestión de historial de trades
    - Preparación de datos desde historial
    - Detección de drift para reentrenamiento inteligente [TASK-4.2-DRIFT]
    - Análisis de Feature Importance con 6 métodos [TASK-4.2-FEATURE-IMPORTANCE]
    """

    def __init__(
        self,
        learning_engine: BaseLearningEngine,
        rebalance_frequency_days: int = 7,
        min_trades_for_retrain: int = 20,
        lookahead_window_days: int = 10,
        drift_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Inicializar updater.

        Args:
            learning_engine: Learning engine a reentrenar
            rebalance_frequency_days: Frecuencia de reentrenamiento (días)
            min_trades_for_retrain: Número mínimo de trades para reentrenar
            lookahead_window_days: Ventana de lookahead para labels (días)
            drift_config: Configuración de drift detection (opcional, se carga de YAML si no se proporciona)
        """
        self.learning_engine = learning_engine
        self.rebalance_frequency_days = rebalance_frequency_days
        self.min_trades_for_retrain = min_trades_for_retrain
        self.lookahead_window_days = lookahead_window_days

        self.last_retrain_date: Optional[datetime] = None
        self.trade_history: List[Dict[str, Any]] = []
        self.market_history: List[Dict[str, Any]] = []

        self.training_data_preparator = TrainingDataPreparator()

        # Drift detection integration [TASK-4.2-DRIFT]
        self._drift_config = drift_config or load_drift_config()
        self._drift_enabled = self._drift_config.get("enabled", True)

        if self._drift_enabled:
            self._drift_detector = ComprehensiveDriftDetector(self._drift_config)
            self._overfitting_detector = OverfittingDetector(
                self._drift_config.get("overfitting", {})
            )
            self._retrain_trigger = AutoRetrainingTrigger(
                self._drift_config.get("auto_retrain", {})
            )
            self._reference_features: Optional[np.ndarray] = None
            self._drift_history: List[ComprehensiveDriftReport] = []
            logger.info("Drift detection enabled for LearningEngineUpdater")
        else:
            self._drift_detector = None
            self._overfitting_detector = None
            self._retrain_trigger = None
            self._reference_features = None
            self._drift_history = []

        # Feature Importance integration [TASK-4.2-FEATURE-IMPORTANCE]
        self._feature_importance_config = load_feature_importance_config()
        self._feature_importance_enabled = self._feature_importance_config.get("enabled", True)

        if self._feature_importance_enabled:
            self._feature_analyzer = ComprehensiveFeatureAnalyzer(self._feature_importance_config)
            self._feature_importance_history: List[Dict[str, Any]] = []
            self._last_feature_analysis: Optional[Dict[str, Any]] = None
            logger.info("Feature importance analysis enabled for LearningEngineUpdater")
        else:
            self._feature_analyzer = None
            self._feature_importance_history = []
            self._last_feature_analysis = None

        # Transfer Learning integration [TASK-4.2-TRANSFER-LEARNING]
        self._transfer_learning_config = load_transfer_learning_config()
        self._transfer_learning_enabled = self._transfer_learning_config.get("enabled", True)

        if self._transfer_learning_enabled:
            try:
                self._transfer_manager = TransferLearningManager(
                    registry_path=self._transfer_learning_config.get("registry_path", "models/registry")
                )
                self._transfer_history: List[Dict[str, Any]] = []
                self._last_transfer_operation: Optional[Dict[str, Any]] = None
                logger.info("Transfer Learning enabled for LearningEngineUpdater")
            except Exception as e:
                logger.warning(f"Failed to initialize Transfer Learning: {e}, disabling TL")
                self._transfer_learning_enabled = False
                self._transfer_manager = None
                self._transfer_history = []
                self._last_transfer_operation = None
        else:
            self._transfer_manager = None
            self._transfer_history = []
            self._last_transfer_operation = None

    def should_retrain(self, current_date: datetime) -> bool:
        """
        Verificar si se debe reentrenar basado en tiempo o drift.

        Args:
            current_date: Fecha actual del backtest

        Returns:
            True si se debe reentrenar, False en caso contrario
        """
        if self.last_retrain_date is None:
            # Primera vez - reentrenar si hay suficientes trades
            return len(self.trade_history) >= self.min_trades_for_retrain

        days_since_retrain = (current_date - self.last_retrain_date).days
        has_enough_trades = len(self.trade_history) >= self.min_trades_for_retrain

        # Time-based check
        time_based = days_since_retrain >= self.rebalance_frequency_days and has_enough_trades

        if time_based:
            return True

        # Drift-based check [TASK-4.2-DRIFT]
        if self._drift_enabled and self._retrain_trigger and has_enough_trades:
            trigger_result = self._retrain_trigger.should_retrain()
            if trigger_result.get("should_retrain", False):
                reasons = trigger_result.get("reasons", [])
                logger.info(f"Drift-based retraining triggered: {', '.join(reasons)}")
                return True

        return False

    def check_drift(self, current_features: np.ndarray) -> Optional[ComprehensiveDriftReport]:
        """
        Check for drift in current features against reference.

        Args:
            current_features: Current feature data (2D array: samples x features)

        Returns:
            ComprehensiveDriftReport if drift detection is enabled, None otherwise
        """
        if not self._drift_enabled or self._drift_detector is None:
            return None

        if self._reference_features is None:
            logger.debug("No reference features set, skipping drift check")
            return None

        try:
            # Ensure 2D array
            if current_features.ndim == 1:
                current_features = current_features.reshape(1, -1)

            report = self._drift_detector.detect(current_features)
            self._drift_history.append(report)

            # Log if drift detected
            if report.overall_drift_detected:
                logger.warning(
                    f"Drift detected! Severity: {report.overall_severity.value}, "
                    f"Recommendation: {report.recommendation}"
                )

                # Update retrain trigger with drift info
                if self._retrain_trigger:
                    self._retrain_trigger.record_drift(
                        drift_detected=True,
                        severity=report.overall_severity,
                        detectors_triggered=[
                            name
                            for name, result in report.detector_results.items()
                            if result.drift_detected
                        ],
                    )

            return report

        except Exception as e:
            logger.warning(f"Error checking drift: {e}")
            return None

    def set_reference_data(self, reference_features: np.ndarray) -> None:
        """
        Set reference data for drift detection.

        Should be called after initial training with the training data.

        Args:
            reference_features: Reference feature data (2D array: samples x features)
        """
        if not self._drift_enabled or self._drift_detector is None:
            return

        try:
            if reference_features.ndim == 1:
                reference_features = reference_features.reshape(1, -1)

            self._reference_features = reference_features
            self._drift_detector.set_reference(reference_features)
            logger.info(
                f"Reference data set for drift detection: {reference_features.shape[0]} samples, "
                f"{reference_features.shape[1]} features"
            )

        except Exception as e:
            logger.warning(f"Error setting reference data: {e}")

    def record_training_metrics(
        self,
        epoch: int,
        train_loss: float,
        val_loss: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Record training metrics for overfitting detection.

        Args:
            epoch: Current training epoch
            train_loss: Training loss
            val_loss: Validation loss

        Returns:
            Overfitting detection result if enabled, None otherwise
        """
        if not self._drift_enabled or self._overfitting_detector is None:
            return None

        try:
            self._overfitting_detector.update_metrics(epoch, train_loss, val_loss)
            result = self._overfitting_detector.detect_overfitting()

            if result.get("overfitting_detected", False):
                logger.warning(
                    f"Overfitting detected at epoch {epoch}! "
                    f"Gap ratio: {result.get('gap_ratio', 0):.4f}"
                )

                # Update retrain trigger
                if self._retrain_trigger:
                    self._retrain_trigger.record_overfitting(
                        overfitting_detected=True,
                        train_val_gap=result.get("gap_ratio", 0),
                    )

            return result

        except Exception as e:
            logger.warning(f"Error recording training metrics: {e}")
            return None

    def get_drift_history(self) -> List[ComprehensiveDriftReport]:
        """Get drift detection history."""
        return self._drift_history.copy()

    def get_drift_summary(self) -> Dict[str, Any]:
        """Get summary of drift detection status."""
        if not self._drift_enabled:
            return {"enabled": False}

        total_checks = len(self._drift_history)
        drift_detected_count = sum(1 for r in self._drift_history if r.overall_drift_detected)
        severity_counts = {}
        for report in self._drift_history:
            sev = report.overall_severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "enabled": True,
            "total_checks": total_checks,
            "drift_detected_count": drift_detected_count,
            "drift_rate": drift_detected_count / total_checks if total_checks > 0 else 0,
            "severity_distribution": severity_counts,
            "reference_set": self._reference_features is not None,
        }

    def add_trade_result(self, trade: Dict[str, Any], timestamp: datetime) -> None:
        """
        Agregar resultado de trade al historial.

        Args:
            trade: Dict con información del trade (pnl, entry_time, exit_time, etc.)
            timestamp: Timestamp del trade
        """
        trade_record = {**trade, 'recorded_at': timestamp}
        self.trade_history.append(trade_record)

    def add_market_data(self, market_data: Dict[str, Any], timestamp: datetime) -> None:
        """
        Agregar datos de mercado al historial.

        Args:
            market_data: Dict con datos de mercado (price, volume, indicators, etc.)
            timestamp: Timestamp de los datos
        """
        market_record = {**market_data, 'timestamp': timestamp}
        self.market_history.append(market_record)

    def _detect_market_regime(self, training_data: Dict[str, Any]) -> str:
        """
        Detect current market regime (bull, bear, sideways, etc.).

        Args:
            training_data: Dict with training data containing targets/returns

        Returns:
            Market regime string (bull, bear, sideways, high_volatility, low_volatility)
        """
        try:
            targets = training_data.get("targets")
            if targets is None:
                logger.debug("No targets available for regime detection, defaulting to 'normal'")
                return "normal"

            # Convert to numpy if needed
            if hasattr(targets, "values"):
                targets = targets.values

            targets = np.asarray(targets).flatten()

            if len(targets) < 2:
                return "normal"

            # Calculate volatility (std dev of returns)
            volatility = float(np.std(targets))

            # Calculate trend (mean return)
            trend = float(np.mean(targets))

            # Get thresholds from config
            config = self._transfer_learning_config.get("market_regime", {})
            vol_thresholds = config.get("volatility_thresholds", {"low": 0.01, "normal": 0.03, "high": 1.0})
            trend_thresholds = config.get("trend_thresholds", {"bearish": -0.001, "bullish": 0.001})

            # Determine volatility classification
            if volatility < vol_thresholds.get("low", 0.01):
                vol_class = "low_volatility"
            elif volatility < vol_thresholds.get("normal", 0.03):
                vol_class = "normal_volatility"
            else:
                vol_class = "high_volatility"

            # Determine trend classification
            if trend < trend_thresholds.get("bearish", -0.001):
                trend_class = "bear"
            elif trend > trend_thresholds.get("bullish", 0.001):
                trend_class = "bull"
            else:
                trend_class = "sideways"

            # Combine into regime
            regime = f"{trend_class}_{vol_class}"

            logger.debug(f"Detected market regime: {regime} (vol={volatility:.4f}, trend={trend:.4f})")
            return regime

        except Exception as e:
            logger.debug(f"Error detecting market regime: {e}, defaulting to 'normal'")
            return "normal"

    def _execute_transfer_learning_step(
        self, training_data: Dict[str, Any], current_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Execute transfer learning step before training.

        Tries to find and fine-tune a pre-trained model instead of training from scratch.
        Falls back to normal training if no suitable model found.

        Args:
            training_data: Dict with training data
            current_date: Current date

        Returns:
            Metrics dict if TL was applied and successful, None if should use normal training
        """
        if not self._transfer_learning_enabled or not self._transfer_manager:
            return None

        try:
            # Detect market regime
            regime = self._detect_market_regime(training_data)

            # Get engine type
            engine_type = self._get_engine_type()

            # Find best pre-trained model for this regime
            best_model_id = self._transfer_manager.find_best_model(
                regime=regime,
                model_type=engine_type,
                metric="f1_score"
            )

            if not best_model_id:
                logger.debug(f"No pre-trained model found for regime={regime}, type={engine_type}, will train normally")
                return None

            logger.info(f"Using pre-trained model {best_model_id} for {regime} market")

            # Extract training arrays
            features = training_data.get("features")
            targets = training_data.get("targets")

            if features is None or targets is None:
                logger.debug("Features or targets not available for fine-tuning, training normally")
                return None

            # Convert to numpy
            if hasattr(features, "values"):
                features = features.values
            if hasattr(targets, "values"):
                targets = targets.values

            features = np.asarray(features)
            targets = np.asarray(targets)

            if len(features) == 0:
                return None

            # Fine-tune the pre-trained model
            fine_tuned_model, tl_metrics = self._transfer_manager.load_and_finetune(
                base_model_id=best_model_id,
                X_train=features,
                y_train=targets,
            )

            # Replace learning engine model with fine-tuned version
            self.learning_engine.model = fine_tuned_model
            self.learning_engine.is_trained = True

            # Store TL operation info
            self._last_transfer_operation = {
                "timestamp": current_date,
                "type": "fine_tune",
                "model_id": best_model_id,
                "regime": regime,
                "metrics": tl_metrics,
            }

            logger.info(f"✅ Transfer Learning fine-tuning completed with metrics: {tl_metrics}")
            return tl_metrics

        except Exception as e:
            logger.debug(f"Transfer learning failed (non-critical): {type(e).__name__}: {e}, falling back to normal training")
            return None

    def retrain_if_needed(self, current_date: datetime, quotes: Optional[List] = None) -> bool:
        """
        Reentrenar learning engine si es necesario.

        El reentrenamiento nunca debe fallar - si hay errores, se registran
        pero el backtest continúa normalmente.

        Args:
            current_date: Fecha actual del backtest
            quotes: Lista de quotes históricos (opcional, se usan si están disponibles)

        Returns:
            True si se reentrenó, False en caso contrario (nunca lanza excepciones)
        """
        # Verificar si se debe reentrenar
        if not self.should_retrain(current_date):
            return False

        # Verificar que el engine esté habilitado
        if not self.learning_engine or not self.learning_engine.enabled:
            logger.debug("Learning engine no habilitado, saltando reentrenamiento")
            return False

        logger.info(
            f"🔄 Iniciando reentrenamiento de {self.learning_engine.__class__.__name__} "
            f"({len(self.trade_history)} trades, "
            f"último reentrenamiento: {self.last_retrain_date})"
        )

        try:
            # Preparar datos de entrenamiento desde historial
            training_data = self._prepare_training_data_from_history(quotes)

            if not training_data or self._is_training_data_empty(training_data):
                logger.debug("⚠️ Datos de entrenamiento vacíos, saltando reentrenamiento")
                return False

            # Verificar dependencias antes de intentar entrenar
            if not self._can_train():
                logger.debug(
                    "⚠️ Learning engine no puede entrenar (dependencias faltantes), saltando reentrenamiento"
                )
                return False

            # Transfer Learning [TASK-4.2-TRANSFER-LEARNING] - Try to use pre-trained model
            tl_metrics = self._execute_transfer_learning_step(training_data, current_date)
            if tl_metrics is not None:
                # Transfer Learning was successful, use those metrics
                metrics = tl_metrics
            else:
                # No TL model available or TL failed, train normally
                metrics = self.learning_engine.train(training_data)

            logger.info(f"✅ Reentrenamiento completado: {metrics}")

            self.last_retrain_date = current_date

            # Set reference data for drift detection [TASK-4.2-DRIFT]
            if self._drift_enabled and "features" in training_data:
                features = training_data["features"]
                if hasattr(features, "values"):
                    features = features.values
                if isinstance(features, np.ndarray) and features.size > 0:
                    self.set_reference_data(features)
                    logger.debug(
                        f"Reference data updated after retraining with {features.shape[0]} samples"
                    )

            # Record retrain event in trigger
            if self._retrain_trigger:
                self._retrain_trigger.record_retrain()
                # Reset overfitting detector after retrain
                if self._overfitting_detector:
                    self._overfitting_detector.reset()

            # Limpiar historial antiguo (mantener solo último 30 días)
            self._clean_old_history(current_date)

            # Analyze feature importance [TASK-4.2-FEATURE-IMPORTANCE]
            if self._feature_importance_enabled and "features" in training_data:
                self._analyze_and_log_feature_importance(training_data, current_date)

            # Register newly trained model for Transfer Learning [TASK-4.2-TRANSFER-LEARNING]
            if self._transfer_learning_enabled and metrics and self.learning_engine.is_trained:
                self._register_trained_model_for_transfer_learning(training_data, metrics, current_date)

            return True

        except ImportError as e:
            # Dependencias faltantes - no es crítico, solo registramos y continuamos
            logger.debug(
                f"⚠️ Reentrenamiento omitido: dependencias faltantes ({e}). "
                f"El backtest continúa sin reentrenamiento."
            )
            return False
        except Exception as e:
            # Cualquier otro error - no es crítico, registramos y continuamos
            logger.warning(
                f"⚠️ Error en reentrenamiento (no crítico): {type(e).__name__}: {e}. "
                f"El backtest continúa sin reentrenamiento."
            )
            # No loguear el stack trace completo para errores no críticos
            return False

    def _prepare_training_data_from_history(
        self, quotes: Optional[List] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Preparar datos de entrenamiento desde historial de trades y market data.

        Args:
            quotes: Lista de quotes históricos (si están disponibles)

        Returns:
            Dict con datos de entrenamiento o None si no hay suficientes datos
        """
        if not self.trade_history or len(self.trade_history) < self.min_trades_for_retrain:
            logger.warning(f"No hay suficientes trades ({len(self.trade_history)}) para reentrenar")
            return None

        engine_type = self._get_engine_type()

        if quotes is None:
            # Si no hay quotes, intentar reconstruir desde market_history
            if not self.market_history:
                logger.warning("No hay quotes ni market_history disponible")
                return None

            # Convertir market_history a formato Quote (simplificado)
            # Esto es una aproximación - en producción se requerirían los quotes completos
            quotes = self._convert_market_history_to_quotes()

        if not quotes or len(quotes) < 60:
            logger.warning(
                f"No hay suficientes quotes ({len(quotes) if quotes else 0}) para entrenar"
            )
            return None

        # Convertir trade_history a formato Trade
        trades = self._convert_trade_history_to_trades()

        # Preparar datos según tipo de engine
        if engine_type == "supervised":
            return self.training_data_preparator.prepare_supervised_training_data(
                quotes=quotes, trades=trades, min_sequence_length=60
            )
        elif engine_type == "deep":
            return self.training_data_preparator.prepare_deep_learning_training_data(
                quotes=quotes, trades=trades, sequence_length=60, min_sequence_length=120
            )
        elif engine_type == "reinforcement":
            return self.training_data_preparator.prepare_reinforcement_learning_data(
                quotes=quotes, initial_capital=Decimal("100000")  # Default
            )

        return None

    def _get_engine_type(self) -> str:
        """Obtener tipo de learning engine."""
        class_name = self.learning_engine.__class__.__name__
        if "Supervised" in class_name:
            return "supervised"
        elif "Deep" in class_name:
            return "deep"
        elif "Reinforcement" in class_name:
            return "reinforcement"
        return "supervised"  # Default

    def _can_train(self) -> bool:
        """
        Verificar si el learning engine puede entrenar (dependencias disponibles).

        Returns:
            True si puede entrenar, False en caso contrario (nunca lanza excepciones)
        """
        if not self.learning_engine:
            return False

        engine_type = self._get_engine_type()

        try:
            if engine_type == "supervised":
                # Verificar scikit-learn
                import sklearn  # noqa: F401
                from sklearn.ensemble import RandomForestClassifier  # noqa: F401

                return True
            elif engine_type == "deep":
                # Verificar PyTorch o TensorFlow
                try:
                    import torch  # noqa: F401

                    return True
                except ImportError:
                    try:
                        import tensorflow as tf  # noqa: F401

                        return True
                    except ImportError:
                        return False
            elif engine_type == "reinforcement":
                # Verificar stable-baselines3 y gym
                try:
                    import gym  # noqa: F401
                    from stable_baselines3 import PPO  # noqa: F401

                    return True
                except ImportError:
                    return False
            return True  # Si no sabemos, intentamos
        except Exception:
            # Cualquier error al verificar significa que no puede entrenar
            return False

    def _is_training_data_empty(self, training_data: Dict[str, Any]) -> bool:
        """Verificar si los datos de entrenamiento están vacíos."""
        if "features" in training_data:
            df = training_data["features"]
            return df is None or (hasattr(df, 'empty') and df.empty) or len(df) == 0
        elif "sequences" in training_data:
            arr = training_data["sequences"]
            return arr is None or len(arr) == 0
        elif "market_sequences" in training_data:
            lst = training_data["market_sequences"]
            return lst is None or len(lst) == 0

        return True

    def _convert_trade_history_to_trades(self) -> List:
        """
        Convertir trade_history a formato Trade (simplificado para backtest).

        Retorna diccionarios con la estructura compatible con objetos Trade
        para que puedan ser usados tanto por código que espera objetos como diccionarios.
        """
        trades = []
        for trade_record in self.trade_history:
            entry_time = trade_record.get('entry_time')
            exit_time = trade_record.get('exit_time')
            pnl = trade_record.get('pnl', 0)

            # Convertir pnl a Decimal si es necesario
            if pnl is not None and not isinstance(pnl, (int, float, Decimal)):
                try:
                    pnl = Decimal(str(pnl))
                except:
                    pnl = Decimal("0")
            elif pnl is None:
                pnl = Decimal("0")

            # Determinar status
            status_str = 'CLOSED' if exit_time else 'OPEN'

            trade_dict = {
                'pnl': pnl,
                'entry_time': entry_time,
                'exit_time': exit_time,
                'status': status_str,
                'symbol': trade_record.get('symbol', 'UNKNOWN'),
                'side': trade_record.get('side', 'BUY'),
                'quantity': trade_record.get('quantity', 0),
                'entry_price': trade_record.get('entry_price', 0),
                'exit_price': trade_record.get('exit_price', trade_record.get('entry_price', 0)),
            }
            trades.append(trade_dict)
        return trades

    def _convert_market_history_to_quotes(self) -> List:
        """Convertir market_history a formato Quote (simplificado)."""
        # En producción, esto requeriría reconstruir objetos Quote completos
        # Por ahora, retornar formato simplificado
        from app.models.market_data import Quote

        quotes = []
        for market_record in self.market_history:
            quote = Quote(
                symbol=market_record.get('symbol', 'UNKNOWN'),
                timestamp=market_record.get('timestamp', datetime.now()),
                bid=Decimal(str(market_record.get('price', 0))),
                ask=Decimal(str(market_record.get('price', 0))),
                volume=int(market_record.get('volume', 0)),
            )
            quotes.append(quote)

        return quotes

    def _clean_old_history(self, current_date: datetime) -> None:
        """Limpiar historial antiguo (mantener solo último 30 días)."""
        cutoff_date = current_date - timedelta(days=30)

        self.trade_history = [
            t for t in self.trade_history if t.get('recorded_at', current_date) >= cutoff_date
        ]

        self.market_history = [
            m for m in self.market_history if m.get('timestamp', current_date) >= cutoff_date
        ]

        logger.debug(
            f"🧹 Historial limpiado: {len(self.trade_history)} trades, "
            f"{len(self.market_history)} market data points"
        )

    def _analyze_and_log_feature_importance(
        self, training_data: Dict[str, Any], current_date: datetime
    ) -> None:
        """
        Analizar importancia de features después del reentrenamiento [TASK-4.2-FEATURE-IMPORTANCE].

        Args:
            training_data: Datos de entrenamiento usados
            current_date: Fecha del análisis
        """
        try:
            if not self._feature_analyzer or not self.learning_engine.is_ready():
                return

            features = training_data.get("features")
            targets = training_data.get("targets")

            if features is None or targets is None:
                logger.debug("⚠️ Features o targets no disponibles para análisis de importancia")
                return

            # Convert to numpy arrays if needed
            if hasattr(features, "values"):
                features = features.values
            if hasattr(targets, "values"):
                targets = targets.values

            # Run comprehensive feature analysis
            logger.debug("📊 Analizando importancia de features (6 métodos)...")
            analysis_result = self._feature_analyzer.analyze(
                model=self.learning_engine.model
                if hasattr(self.learning_engine, "model")
                else None,
                features=features,
                targets=targets,
                feature_names=training_data.get("feature_names"),
                model_type=self._get_engine_type(),
            )

            if analysis_result and "error" not in analysis_result:
                # Store analysis result
                self._last_feature_analysis = {
                    "timestamp": current_date,
                    "analysis": analysis_result,
                    "n_features": len(features[0]) if len(features) > 0 else 0,
                    "n_samples": len(features),
                }
                self._feature_importance_history.append(self._last_feature_analysis)

                # Log top/low importance features
                if "top_features" in analysis_result:
                    top_features = analysis_result.get("top_features", {})
                    if top_features:
                        logger.info(
                            f"🌟 Top 5 features por importancia: "
                            f"{', '.join(list(top_features.keys())[:5])}"
                        )

                # Check for critical warnings
                if "warnings" in analysis_result:
                    warnings = analysis_result.get("warnings", [])
                    if warnings:
                        for warning in warnings:
                            logger.warning(f"⚠️ Feature Importance Warning: {warning}")

                # Recommendations
                if "recommendations" in analysis_result:
                    recommendations = analysis_result.get("recommendations", [])
                    if recommendations:
                        logger.info(
                            f"💡 Feature Engineering Recommendations: "
                            f"{'; '.join(recommendations[:3])}"
                        )

                logger.info(
                    f"✅ Feature importance analysis completado "
                    f"({len(analysis_result.get('top_features', {}))} features analizados)"
                )
            else:
                logger.debug(
                    f"⚠️ Feature importance analysis no disponible: "
                    f"{analysis_result.get('error', 'Unknown error') if analysis_result else 'No result'}"
                )

        except Exception as e:
            logger.debug(
                f"⚠️ Error en feature importance analysis (no crítico): {type(e).__name__}: {e}"
            )
            # Feature importance is non-critical, continue regardless

    def _register_trained_model_for_transfer_learning(
        self, training_data: Dict[str, Any], metrics: Dict[str, Any], current_date: datetime
    ) -> None:
        """
        Register newly trained model for future transfer learning.

        Args:
            training_data: Dict with training data
            metrics: Metrics from training
            current_date: Current date
        """
        try:
            if not self._transfer_manager:
                return

            # Detect market regime
            regime = self._detect_market_regime(training_data)
            engine_type = self._get_engine_type()

            # Get feature importance if available
            feature_importance = self.get_last_feature_importance_analysis() or {}

            # Get feature info
            features = training_data.get("features")
            n_features = 0
            n_samples = 0
            if features is not None:
                if hasattr(features, "values"):
                    features = features.values
                features_array = np.asarray(features)
                if len(features_array.shape) > 0:
                    n_samples = features_array.shape[0]
                if len(features_array.shape) > 1:
                    n_features = features_array.shape[1]

            # Register the newly trained model
            model_id = self._transfer_manager.create_pretrained_model(
                model=self.learning_engine.model,
                regime=regime,
                model_type=engine_type,
                algorithm=self.learning_engine.algorithm if hasattr(self.learning_engine, 'algorithm') else 'unknown',
                metadata={
                    'training_date': current_date.isoformat(),
                    'metrics': metrics,
                    'n_features': n_features,
                    'n_samples': n_samples,
                    'feature_importance': feature_importance,
                }
            )

            # Store in transfer learning history
            self._transfer_history.append({
                'timestamp': current_date,
                'model_id': model_id,
                'regime': regime,
                'type': 'new_model_registration',
                'metrics': metrics,
            })

            logger.info(f"Registered new model {model_id} for {regime} market")

        except Exception as e:
            logger.debug(f"Failed to register model (non-critical): {type(e).__name__}: {e}")
            # Model registration is non-critical, continue regardless

    def get_last_feature_importance_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Obtener último análisis de importancia de features.

        Returns:
            Dictionary con análisis o None si no disponible
        """
        return self._last_feature_analysis

    def get_feature_importance_history(self) -> List[Dict[str, Any]]:
        """
        Obtener historial completo de análisis de importancia.

        Returns:
            List de análisis históricos
        """
        return self._feature_importance_history.copy()

    def get_feature_importance_summary(self) -> Dict[str, Any]:
        """
        Obtener resumen de feature importance (últimas 5 análisis).

        Returns:
            Resumen con estadísticas de importancia
        """
        if not self._feature_importance_history:
            return {"status": "no_analyses_yet", "count": 0}

        # Get last 5 analyses
        recent_analyses = self._feature_importance_history[-5:]

        # Collect all top features from recent analyses
        all_top_features = {}
        for analysis_record in recent_analyses:
            analysis = analysis_record.get("analysis", {})
            top_features = analysis.get("top_features", {})
            for feature, importance in top_features.items():
                if feature not in all_top_features:
                    all_top_features[feature] = []
                all_top_features[feature].append(importance)

        # Average importance across analyses
        feature_importance_avg = {
            feature: float(np.mean(importances))
            for feature, importances in all_top_features.items()
        }

        # Sort by average importance
        sorted_features = sorted(feature_importance_avg.items(), key=lambda x: x[1], reverse=True)

        return {
            "status": "ok",
            "count": len(self._feature_importance_history),
            "recent_analyses": len(recent_analyses),
            "top_features": dict(sorted_features[:10]),
            "last_analysis_date": (
                recent_analyses[-1].get("timestamp") if recent_analyses else None
            ),
        }

    def get_last_transfer_operation(self) -> Optional[Dict[str, Any]]:
        """
        Get details of last transfer learning operation (fine-tune or registration).

        Returns:
            Dict with last operation details or None if no operations yet
        """
        return self._last_transfer_operation

    def get_transfer_history(self) -> List[Dict[str, Any]]:
        """
        Get complete history of transfer learning operations.

        Returns:
            List of transfer learning operations (fine-tunes, registrations)
        """
        return self._transfer_history.copy()

    def get_available_pretrained_models(self, regime: Optional[str] = None) -> Dict[str, Any]:
        """
        Get available pre-trained models, optionally filtered by market regime.

        Args:
            regime: Optional market regime to filter by (bull, bear, sideways, etc.)

        Returns:
            Dict with available models organized by regime and type
        """
        if not self._transfer_manager:
            return {"status": "transfer_learning_disabled", "models": {}}

        try:
            models = self._transfer_manager.list_models(regime=regime)
            return {
                "status": "ok",
                "models": models,
                "filter_regime": regime,
                "total_models": sum(len(v) for v in models.values()) if models else 0,
            }
        except Exception as e:
            logger.debug(f"Error listing pre-trained models: {e}")
            return {"status": "error", "error": str(e), "models": {}}

    def get_transfer_learning_status(self) -> Dict[str, Any]:
        """
        Get current transfer learning configuration and status.

        Returns:
            Dict with TL status, enabled flag, operations count, etc.
        """
        return {
            "enabled": self._transfer_learning_enabled,
            "manager_initialized": self._transfer_manager is not None,
            "last_operation": self._last_transfer_operation,
            "total_operations": len(self._transfer_history),
            "registrations": len([op for op in self._transfer_history if op.get("type") == "new_model_registration"]),
            "fine_tunes": len([op for op in self._transfer_history if op.get("type") == "fine_tune"]),
        }
