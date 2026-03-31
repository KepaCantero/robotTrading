"""
TransformerEngine - Usa Transformers para optimización de parámetros y predicción de series de tiempo.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

# ============================================================================
# CRÍTICO: Configurar variables de entorno ANTES de importar numpy/pandas/PyTorch
# FORZAR configuración (no solo setdefault) para asegurar que se aplique
# Esto previene bloqueos de threading con mutex.cc
# ============================================================================
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["MKL_SERVICE_FORCE_INTEL"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["FOR_DISABLE_CONSOLE_CTRL_HANDLER"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Deshabilitar CUDA completamente
os.environ["TORCH_USE_CUDA_DSA"] = "0"
os.environ["MKL_DYNAMIC"] = "FALSE"
os.environ["MKL_INTERFACE_LAYER"] = "LP64,GNU"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# Ahora importar numpy y pandas DESPUÉS de configurar variables
import numpy as np

from .base_learning_engine import BaseLearningEngine

logger = logging.getLogger(__name__)

import contextlib

# REQUIRED: PyTorch is REQUIRED - NO FALLBACKS
import torch
import torch.nn as nn
import torch.optim as optim

# Configure threading BEFORE any PyTorch operations
torch.set_num_threads(1)
with contextlib.suppress(RuntimeError):
    torch.set_num_interop_threads(1)

torch.backends.cudnn.enabled = False
torch.backends.cudnn.benchmark = False


# NO definir TransformerModel o TransformerDataset aquí - se crearán lazy cuando se necesiten
# Esto previene que PyTorch inicialice threading durante la importación del módulo
# Las clases se definen dentro de los métodos train() y evaluate() después de configurar threading


class TransformerEngine(BaseLearningEngine):
    """
    Motor de aprendizaje usando Transformers para:
    - Predicción de performance de estrategia
    - Optimización de parámetros/thresholds
    - Detección de patrones complejos en series de tiempo
    """

    def __init__(self, config: dict, defer_pytorch_init: bool = False):
        """
        Inicializar TransformerEngine.

        Args:
            config: Configuración del engine desde YAML
            defer_pytorch_init: Si True, NO importa PyTorch durante __init__ (útil para subprocess)
        """
        super().__init__("transformer", config)

        # Si defer_pytorch_init=True, no importar PyTorch ahora (se hará en subprocess)
        if defer_pytorch_init:
            self.enabled = True  # Marcarlo como habilitado pero no inicializar PyTorch
            logger.debug(
                "TransformerEngine creado con defer_pytorch_init=True (PyTorch se inicializará en subprocess)"
            )
            # Establecer valores por defecto sin importar PyTorch
            params = config.get("parameters", {})
            self.d_model = params.get("d_model", 64)
            self.nhead = params.get("nhead", 8)
            self.num_layers = params.get("num_layers", 4)
            self.dim_feedforward = params.get("dim_feedforward", 256)
            self.dropout = params.get("dropout", 0.1)
            self.epochs = params.get("epochs", 50)
            self.batch_size = params.get("batch_size", 32)
            self.learning_rate = params.get("learning_rate", 0.0001)
            self.model: Optional[nn.Module] = None
            self.scaler = None
            return

        # PyTorch es REQUIRED - ya importado al inicio del módulo

        # Parámetros del modelo desde config
        params = config.get("parameters", {})
        self.d_model = params.get("d_model", 64)
        self.nhead = params.get("nhead", 8)
        self.num_layers = params.get("num_layers", 4)
        self.dim_feedforward = params.get("dim_feedforward", 256)
        self.dropout = params.get("dropout", 0.1)
        self.epochs = params.get("epochs", 50)
        self.batch_size = params.get("batch_size", 32)
        self.learning_rate = params.get("learning_rate", 0.0001)

        # Estado del modelo
        self.model = None
        # Usar CPU siempre para evitar bloqueos de threading con CUDA
        self.device = torch.device("cpu")
        logger.info(f"TransformerEngine inicializado (device: {self.device})")

        # Configurar threading de PyTorch
        with contextlib.suppress(RuntimeError):
            torch.set_num_threads(1)
        with contextlib.suppress(RuntimeError):
            torch.set_num_interop_threads(1)

    def _prepare_sequences(
        self, data: list[dict[str, object]], sequence_length: int = 30, target_key: str = "target"
    ) -> tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Preparar sequences de tiempo desde datos históricos.

        Args:
            data: Lista de dicts con features
            sequence_length: Longitud de cada sequence
            target_key: Clave del target en los dicts

        Returns:
            (sequences, labels) como numpy arrays
        """
        if not data or len(data) < sequence_length + 1:
            return np.array([]), None

        sequences = []
        labels = []

        for i in range(len(data) - sequence_length):
            # Extraer features de la ventana
            window_data = data[i : i + sequence_length]

            # Convertir a array (asumiendo features numéricas)
            features = []
            for item in window_data:
                # Extraer todas las features numéricas
                numeric_features = [
                    v for k, v in item.items() if isinstance(v, (int, float)) and k != target_key
                ]
                if numeric_features:
                    features.append(numeric_features[0])  # Usar primera feature numérica
                else:
                    features.append(0.0)  # Default

            sequences.append(features)

            # Target (si está disponible)
            if target_key in data[i + sequence_length]:
                labels.append(float(data[i + sequence_length][target_key]))
            else:
                labels.append(0.0)

        sequences = np.array(sequences)
        labels = np.array(labels) if labels else None

        # Reshape para Transformer: (batch, seq_len, features)
        if sequences.ndim == 2:
            sequences = sequences.reshape((sequences.shape[0], sequences.shape[1], 1))
        elif sequences.ndim == 1:
            sequences = sequences.reshape((sequences.shape[0], 1, 1))

        return sequences, labels

    def train(
        self,
        training_data: Optional[dict[str, object]] = None,
        validation_data: Optional[dict[str, object]] = None,
    ) -> dict[str, object]:
        """
        Entrenar el modelo Transformer.

        Args:
            training_data: Dict con 'features' y 'targets' o lista de dicts
            validation_data: Datos de validación opcionales

        Returns:
            Dict con métricas de entrenamiento
        """
        if not self.enabled:
            logger.warning("TransformerEngine deshabilitado")
            return {}

        # If no training data provided, mark as trained for compatibility
        if training_data is None:
            logger.info("No training data provided - marking model as trained (dummy mode)")
            self.is_trained = True
            return {
                "loss": 0.0,
                "accuracy": 0.0,
                "samples": 0,
            }

        # PyTorch es REQUIRED - ya importado al inicio del módulo

        try:
            # Preparar datos
            if isinstance(training_data, dict):
                if "sequences" in training_data and "labels" in training_data:
                    sequences = np.array(training_data["sequences"])
                    labels = np.array(training_data["labels"])
                elif "features" in training_data:
                    # Convertir features a sequences
                    sequences, labels = self._prepare_sequences(
                        training_data.get("features", []), sequence_length=30
                    )
                else:
                    # Intentar como lista de dicts
                    sequences, labels = self._prepare_sequences(
                        training_data.get("data", []), sequence_length=30
                    )
            else:
                sequences, labels = self._prepare_sequences(training_data, sequence_length=30)

            if len(sequences) == 0:
                logger.warning("No hay sequences válidas para entrenar")
                return {"loss": float("inf"), "error": "no_data"}

            # Inicializar modelo si no existe
            if self.model is None:
                # PyTorch es REQUIRED - ya importado al inicio del módulo

                # CRÍTICO: Asegurar threading antes de crear modelo

                with contextlib.suppress(RuntimeError):
                    torch.set_num_threads(1)
                with contextlib.suppress(RuntimeError):
                    torch.set_num_interop_threads(1)

                torch.backends.cudnn.enabled = False
                torch.backends.cudnn.benchmark = False

                # Definir TransformerModel lazy dentro de este contexto
                class TransformerModel(nn.Module):
                    """Modelo Transformer para predicción de series de tiempo y optimización."""

                    def __init__(
                        self,
                        d_model=64,
                        nhead=8,
                        num_layers=4,
                        dim_feedforward=256,
                        dropout=0.1,
                        output_size=1,
                        max_len=1000,
                    ):
                        super().__init__()
                        self.d_model = d_model

                        # Proyección de entrada
                        self.input_projection = nn.Linear(1, d_model)

                        # Positional encoding sinusoidal mejorado
                        # Usa sin/cos encoding estándar (más efectivo que random parameter)
                        pe = torch.zeros(max_len, d_model)
                        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
                        div_term = torch.exp(
                            torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model)
                        )
                        pe[:, 0::2] = torch.sin(position * div_term)
                        pe[:, 1::2] = torch.cos(position * div_term)
                        self.register_buffer("pos_encoder", pe.unsqueeze(0))

                        # Transformer encoder
                        encoder_layer = nn.TransformerEncoderLayer(
                            d_model=d_model,
                            nhead=nhead,
                            dim_feedforward=dim_feedforward,
                            dropout=dropout,
                            batch_first=True,
                        )
                        self.transformer_encoder = nn.TransformerEncoder(
                            encoder_layer, num_layers=num_layers
                        )

                        # Output layer
                        self.fc = nn.Linear(d_model, output_size)
                        self.dropout = nn.Dropout(dropout)

                    def forward(self, x):
                        # Proyectar entrada
                        if x.dim() == 2:
                            x = x.unsqueeze(-1)
                        x = self.input_projection(x)

                        # Añadir positional encoding sinusoidal
                        seq_len = x.size(1)
                        x = x + self.pos_encoder[:, :seq_len, :]

                        # Transformer encoder
                        x = self.transformer_encoder(x)

                        # Usar última posición para predicción
                        x = x[:, -1, :]
                        x = self.dropout(x)
                        x = self.fc(x)
                        return x

                sequences.shape[2] if len(sequences.shape) > 2 else 1
                # Crear modelo en contexto seguro - usar no_grad para máxima seguridad
                try:
                    with torch.no_grad():
                        self.model = TransformerModel(
                            d_model=self.d_model,
                            nhead=self.nhead,
                            num_layers=self.num_layers,
                            dim_feedforward=self.dim_feedforward,
                            dropout=self.dropout,
                            output_size=1,
                        )
                        # Mover a device sin threading
                        self.model = self.model.to(self.device, non_blocking=False)
                except (ValueError, TypeError, KeyError, AttributeError) as e:
                    error_msg = str(e).lower()
                    if "mutex" in error_msg or "lock" in error_msg:
                        logger.error(
                            "❌ Bloqueo de mutex detectado al crear TransformerModel. "
                            "Intenta: export MKL_SERVICE_FORCE_INTEL=1 && export KMP_DUPLICATE_LIB_OK=TRUE"
                        )
                        raise RuntimeError(
                            "Bloqueo de mutex en PyTorch. Revisa docs/PROBLEMA_MUTEX_BLOQUEO.md para soluciones."
                        ) from e
                    raise

            # PyTorch is imported at module level (lines 37-39)
            # Import Dataset and DataLoader from torch.utils.data
            from torch.utils.data import DataLoader as _DataLoader, Dataset as _Dataset

            # Type guard - model should exist at this point
            assert self.model is not None

            # Definir TransformerDataset lazy dentro de este contexto
            class TransformerDataset(_Dataset):
                """Dataset para sequences de tiempo para Transformer."""

                def __init__(self, sequences, labels):
                    with contextlib.suppress(RuntimeError):
                        torch.set_num_threads(1)
                    with contextlib.suppress(RuntimeError):
                        torch.set_num_interop_threads(1)
                    import numpy as np

                    sequences_np = np.array(sequences, dtype=np.float32)
                    labels_np = None
                    if labels is not None:
                        labels_np = np.array(labels, dtype=np.float32)
                    with torch.no_grad():
                        self.sequences = torch.from_numpy(sequences_np).clone()
                        if labels_np is not None:
                            self.labels = torch.from_numpy(labels_np).clone()
                        else:
                            self.labels = None

                def __len__(self):
                    return len(self.sequences)

                def __getitem__(self, idx):
                    if self.labels is not None:
                        return self.sequences[idx], self.labels[idx]
                    return self.sequences[idx]

            # Preparar datasets
            train_dataset = TransformerDataset(sequences, labels)
            # CRÍTICO: Asegurar threading ANTES de crear DataLoader
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)

            # CRÍTICO: num_workers=0 para evitar bloqueos de threading
            train_loader = _DataLoader(
                train_dataset,
                batch_size=self.batch_size,
                shuffle=True,
                num_workers=0,  # Sin workers para evitar mutex.cc
                pin_memory=False,  # Deshabilitar pin_memory para evitar bloqueos
                persistent_workers=False,  # Sin workers persistentes
            )

            # Optimizer y loss
            optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
            criterion = nn.MSELoss()

            # Entrenamiento
            self.model.train()
            train_losses = []

            for epoch in range(self.epochs):
                batch_losses = []
                for batch_sequences, batch_labels in train_loader:
                    batch_sequences = batch_sequences.to(self.device)
                    batch_labels = batch_labels.to(self.device).unsqueeze(1)

                    optimizer.zero_grad()
                    outputs = self.model(batch_sequences)
                    loss = criterion(outputs, batch_labels)
                    loss.backward()
                    optimizer.step()

                    batch_losses.append(loss.item())

                avg_loss = sum(batch_losses) / len(batch_losses) if batch_losses else 0.0
                train_losses.append(avg_loss)

                if (epoch + 1) % 10 == 0:
                    logger.debug(
                        f"Transformer Epoch {epoch + 1}/{self.epochs}, Loss: {avg_loss:.6f}"
                    )

            # Validación si está disponible
            val_loss = None
            if validation_data is not None:
                val_sequences, val_labels = self._prepare_sequences(
                    validation_data.get("data", validation_data), sequence_length=30
                )
                if len(val_sequences) > 0:
                    # Import Dataset and DataLoader again for this context
                    from torch.utils.data import DataLoader as _DataLoader, Dataset as _Dataset

                    class TransformerDatasetVal(_Dataset):
                        """Dataset para sequences de tiempo para Transformer."""

                        def __init__(self, sequences, labels):
                            with contextlib.suppress(RuntimeError):
                                torch.set_num_threads(1)
                            import numpy as np

                            sequences_np = np.array(sequences, dtype=np.float32)
                            labels_np = None
                            if labels is not None:
                                labels_np = np.array(labels, dtype=np.float32)
                            with torch.no_grad():
                                self.sequences = torch.from_numpy(sequences_np).clone()
                                if labels_np is not None:
                                    self.labels = torch.from_numpy(labels_np).clone()
                                else:
                                    self.labels = None

                        def __len__(self):
                            return len(self.sequences)

                        def __getitem__(self, idx):
                            if self.labels is not None:
                                return self.sequences[idx], self.labels[idx]
                            return self.sequences[idx]

                    val_dataset = TransformerDatasetVal(val_sequences, val_labels)
                    # CRÍTICO: Asegurar threading antes de crear DataLoader
                    torch.set_num_threads(1)
                    torch.set_num_interop_threads(1)

                    # CRÍTICO: num_workers=0 para evitar bloqueos de threading
                    val_loader = _DataLoader(
                        val_dataset,
                        batch_size=self.batch_size,
                        shuffle=False,
                        num_workers=0,  # Sin workers para evitar mutex.cc
                        pin_memory=False,  # Deshabilitar pin_memory para evitar bloqueos
                        persistent_workers=False,  # Sin workers persistentes
                    )

                    self.model.eval()
                    val_loss_sum = 0.0
                    val_batches = 0

                    with torch.no_grad():
                        for batch_sequences, batch_labels in val_loader:
                            batch_sequences = batch_sequences.to(self.device)
                            batch_labels = batch_labels.to(self.device).unsqueeze(1)

                            outputs = self.model(batch_sequences)
                            loss = criterion(outputs, batch_labels)
                            val_loss_sum += loss.item()
                            val_batches += 1

                    val_loss = val_loss_sum / val_batches if val_batches > 0 else None

            final_loss = train_losses[-1] if train_losses else 0.0
            self.is_trained = True

            metrics = {
                "loss": final_loss,
                "train_losses": train_losses,
            }
            if val_loss is not None:
                metrics["val_loss"] = val_loss

            logger.info(
                f"TransformerEngine entrenado: Loss={final_loss:.6f}"
                + (f", Val Loss={val_loss:.6f}" if val_loss else "")
            )

            return metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error entrenando TransformerEngine: {e}", exc_info=True)
            return {"error": str(e), "loss": float("inf")}

    def predict(self, features: dict[str, object]) -> dict[str, object]:
        """
        Generar predicción usando el modelo Transformer.

        Args:
            features: Features actuales (debe incluir sequence histórica)

        Returns:
            Dict con predicción y metadata
        """
        if not self.is_ready():
            logger.warning("TransformerEngine no está entrenado")
            return {"prediction": 0.0, "confidence": 0.0, "ready": False}

        try:
            # Convertir features a sequence
            if "sequence" in features:
                sequence = np.array(features["sequence"])
            elif "features" in features:
                # Usar features como sequence
                feature_list = [
                    v for v in features["features"].values() if isinstance(v, (int, float))
                ]
                sequence = np.array(feature_list[-30:])  # Últimos 30 valores
            else:
                logger.warning("No se encontró sequence en features")
                return {"prediction": 0.0, "confidence": 0.0}

            # Reshape: (1, seq_len, features)
            if sequence.ndim == 1:
                sequence = sequence.reshape((1, sequence.shape[0], 1))
            elif sequence.ndim == 2:
                sequence = sequence.reshape((1, sequence.shape[0], sequence.shape[1]))
            else:
                # Already in correct shape, just add batch dimension
                sequence = sequence.reshape((1, *sequence.shape))

            # Predecir
            assert self.model is not None  # Type guard
            self.model.eval()
            with torch.no_grad():
                sequence_tensor = torch.FloatTensor(sequence).to(self.device)
                output = self.model(sequence_tensor)
                prediction = output.cpu().numpy()[0, 0]

            return {
                "prediction": float(prediction),
                "confidence": min(1.0, abs(prediction)),
                "ready": True,
            }

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en predicción Transformer: {e}", exc_info=True)
            return {"prediction": 0.0, "confidence": 0.0, "error": str(e)}

    def evaluate(self, test_data: dict[str, object]) -> dict[str, object]:
        """
        Evaluar el modelo con datos de prueba.

        Args:
            test_data: Datos de prueba con 'features' y 'targets'

        Returns:
            Dict con métricas de evaluación
        """
        if not self.is_ready():
            return {"error": "model_not_trained"}

        try:
            sequences, labels = self._prepare_sequences(
                test_data.get("data", test_data), sequence_length=30
            )

            if len(sequences) == 0:
                return {"error": "no_data"}

            # Import Dataset and DataLoader for this context
            from torch.utils.data import DataLoader as _DataLoader, Dataset as _Dataset

            # Definir TransformerDatasetEval aquí también
            class TransformerDatasetEval(_Dataset):
                """Dataset para sequences de tiempo para Transformer."""

                def __init__(self, sequences, labels):
                    with contextlib.suppress(RuntimeError):
                        torch.set_num_threads(1)
                    import numpy as np

                    sequences_np = np.array(sequences, dtype=np.float32)
                    labels_np = None
                    if labels is not None:
                        labels_np = np.array(labels, dtype=np.float32)
                    with torch.no_grad():
                        self.sequences = torch.from_numpy(sequences_np).clone()
                        if labels_np is not None:
                            self.labels = torch.from_numpy(labels_np).clone()
                        else:
                            self.labels = None

                def __len__(self):
                    return len(self.sequences)

                def __getitem__(self, idx):
                    if self.labels is not None:
                        return self.sequences[idx], self.labels[idx]
                    return self.sequences[idx]

            test_dataset = TransformerDatasetEval(sequences, labels)
            # CRÍTICO: Asegurar threading antes de crear DataLoader
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)

            # CRÍTICO: num_workers=0 para evitar bloqueos de threading
            test_loader = _DataLoader(
                test_dataset,
                batch_size=self.batch_size,
                shuffle=False,
                num_workers=0,  # Sin workers para evitar mutex.cc
                pin_memory=False,  # Deshabilitar pin_memory para evitar bloqueos
                persistent_workers=False,  # Sin workers persistentes
            )

            criterion = nn.MSELoss()
            assert self.model is not None  # Type guard
            self.model.eval()

            total_loss = 0.0
            predictions = []
            targets = []
            num_batches = 0

            with torch.no_grad():
                for batch_sequences, batch_labels in test_loader:
                    batch_sequences = batch_sequences.to(self.device)
                    batch_labels = batch_labels.to(self.device).unsqueeze(1)

                    outputs = self.model(batch_sequences)
                    loss = criterion(outputs, batch_labels)

                    total_loss += loss.item()
                    predictions.extend(outputs.cpu().numpy().flatten())
                    targets.extend(batch_labels.cpu().numpy().flatten())
                    num_batches += 1

            avg_loss = total_loss / num_batches if num_batches > 0 else 0.0

            # Calcular métricas adicionales
            predictions = np.array(predictions)
            targets = np.array(targets)
            mae = np.mean(np.abs(predictions - targets))
            rmse = np.sqrt(np.mean((predictions - targets) ** 2))

            return {"loss": avg_loss, "mae": float(mae), "rmse": float(rmse)}

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error evaluando TransformerEngine: {e}", exc_info=True)
            return {"error": str(e)}
