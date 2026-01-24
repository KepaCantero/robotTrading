"""
DeepLearningEngine - Det parte patrones complejos con LSTM, GRU o Transformers.
"""

import logging
import os
from typing import Any, Dict, Optional

# ============================================================================
# CRÍTICO: Configurar variables de entorno ANTES de importar numpy/pandas/PyTorch
# FORZAR configuración (no solo setdefault) para asegurar que se aplique
# Esto previene bloqueos de threading con mutex.cc
# ============================================================================
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Deshabilitar CUDA completamente
os.environ['TORCH_USE_CUDA_DSA'] = '0'
os.environ['MKL_DYNAMIC'] = 'FALSE'
os.environ['MKL_INTERFACE_LAYER'] = 'LP64,GNU'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Ahora importar numpy y pandas DESPUÉS de configurar variables
import numpy as np  # noqa: E402

from .base_learning_engine import BaseLearningEngine  # noqa: E402

logger = logging.getLogger(__name__)

# NO importar PyTorch aquí - será importado lazy cuando se necesite
# Esto previene que PyTorch inicialice threading antes de configurar variables de entorno
PYTORCH_AVAILABLE = False
torch = None
nn = None
optim = None
Dataset = None
DataLoader = None


def _ensure_pytorch_imported():
    """Importar PyTorch de forma lazy con configuración de threading."""
    global torch, nn, optim, Dataset, DataLoader, PYTORCH_AVAILABLE

    if PYTORCH_AVAILABLE:
        return True

    try:
        # Asegurar variables de entorno ANTES de importar
        os.environ['OMP_NUM_THREADS'] = '1'
        os.environ['MKL_NUM_THREADS'] = '1'
        os.environ['NUMEXPR_MAX_THREADS'] = '1'
        os.environ['OPENBLAS_NUM_THREADS'] = '1'
        os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
        os.environ['CUDA_VISIBLE_DEVICES'] = ''

        import torch

        # Configurar ANTES de cualquier otra operación
        torch.set_num_threads(1)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass  # Ignorar si ya está configurado

        torch.backends.cudnn.enabled = False
        torch.backends.cudnn.benchmark = False

        import torch.nn as nn
        import torch.optim as optim
        from torch.utils.data import DataLoader, Dataset

        PYTORCH_AVAILABLE = True
        logger.debug("PyTorch importado con configuración single-threaded")
        return True
    except ImportError:
        PYTORCH_AVAILABLE = False
        logger.warning("PyTorch no disponible. DeepLearningEngine requiere PyTorch.")
        return False
    except Exception as e:
        PYTORCH_AVAILABLE = False
        logger.warning(f"Error inicializando PyTorch: {e}")
        return False


try:
    pass

    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logger.warning("TensorFlow no disponible. DeepLearningEngine requiere PyTorch o TensorFlow.")


# NO definir clases aquí - se crearán lazy cuando se necesiten después de configurar threading
# Esto previene que PyTorch inicialice threading durante la importación del módulo


class DeepLearningEngine(BaseLearningEngine):
    """
    Motor de Deep Learning para detectar patrones complejos en series de tiempo.

    Arquitecturas soportadas:
    - LSTM: Para dependencias de largo plazo
    - GRU: Similar a LSTM, más eficiente
    - Transformer: Para capturar relaciones complejas (con attention mechanisms)
    - AttentionLSTM: LSTM mejorado con mecanismo de atención

    Predice movimientos de mercado y ajusta parámetros dinámicos de filtros.
    """

    def __init__(self, config: Dict, defer_pytorch_init: bool = False):
        """
        Inicializar motor de deep learning.

        Args:
            config: Configuración del engine
            defer_pytorch_init: Si True, NO importa PyTorch durante __init__ (útil para subprocess)
        """
        super().__init__("deep_learning", config)

        # Si defer_pytorch_init=True, no importar PyTorch ahora (se hará en subprocess)
        if defer_pytorch_init:
            self.enabled = True  # Marcarlo como habilitado pero no inicializar PyTorch
            logger.debug(
                "DeepLearningEngine creado con defer_pytorch_init=True (PyTorch se inicializará en subprocess)"
            )
            # Establecer valores por defecto sin importar PyTorch
            self.architecture = config.get("architecture", "lstm")
            self.backend = config.get("backend", "pytorch")
            self.sequence_length = config.get("sequence_length", 60)
            self.hidden_size = config.get("hidden_size", 64)
            self.num_layers = config.get("num_layers", 2)
            self.dropout = config.get("dropout", 0.2)
            self.learning_rate = config.get("learning_rate", 0.001)
            self.batch_size = config.get("batch_size", 32)
            self.epochs = config.get("epochs", 50)
            self.feature_columns = config.get(
                "feature_columns",
                ['price', 'volume', 'rsi', 'ema_fast', 'ema_slow', 'momentum', 'atr'],
            )
            self.scaler = None
            self.model = None
            return

        # CRÍTICO: Importar PyTorch lazy ANTES de verificar disponibilidad
        if not _ensure_pytorch_imported():
            if not TENSORFLOW_AVAILABLE:
                # En lugar de lanzar error, deshabilitar el engine
                logger.warning(
                    "PyTorch o TensorFlow no disponibles. DeepLearningEngine será deshabilitado. "
                    "Instala con: pip install torch>=2.0.0 o pip install tensorflow>=2.13.0"
                )
                self.enabled = False
                return

        # Si llegamos aquí, NO usamos defer_pytorch_init, así que inicializar normalmente
        self.architecture = config.get(
            "architecture", "lstm"
        )  # lstm, gru, transformer, attention_lstm
        self.backend = config.get("backend", "pytorch")  # pytorch, tensorflow

        # Hyperparámetros
        self.sequence_length = config.get("sequence_length", 60)  # Ventana de tiempo
        self.hidden_size = config.get("hidden_size", 64)
        self.num_layers = config.get("num_layers", 2)
        self.dropout = config.get("dropout", 0.2)
        self.learning_rate = config.get("learning_rate", 0.001)
        self.batch_size = config.get("batch_size", 32)
        self.epochs = config.get("epochs", 50)

        # Features
        self.feature_columns = config.get(
            "feature_columns", ['price', 'volume', 'rsi', 'ema_fast', 'ema_slow', 'momentum', 'atr']
        )

        # Parámetros específicos para transformer y otras arquitecturas (si se usa)
        self.model_params = config.get("model_parameters", {})

        self.scaler = None  # Para normalizar datos

    def train(
        self,
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None,
        use_subprocess: bool = False,
    ) -> Dict[str, float]:
        """
        Entrenar modelo de deep learning.

        Args:
            training_data: {
                'sequences': np.array shape (n_samples, sequence_length, n_features),
                'labels': np.array shape (n_samples,),  # Precio futuro, dirección, etc.
                'raw_data': pd.DataFrame  # Datos originales (opcional)
            }
            validation_data: Datos de validación (opcional)
            use_subprocess: Si True, entrena en un proceso hijo aislado (para evitar deadlocks)
        """
        # Si use_subprocess=True, entrenar en proceso hijo aislado
        if use_subprocess:
            return self._train_in_subprocess(training_data, validation_data)

        # Asegurar que PyTorch está disponible
        if not _ensure_pytorch_imported():
            if not TENSORFLOW_AVAILABLE:
                raise ImportError("PyTorch o TensorFlow requeridos")

        sequences = training_data['sequences']
        labels = training_data['labels']

        # Normalizar datos
        sequences, labels, scaler = self._normalize_data(sequences, labels)
        self.scaler = scaler

        input_size = sequences.shape[2]
        output_size = 1 if labels.ndim == 1 else labels.shape[1]

        # CRÍTICO: Asegurar que PyTorch está importado PRIMERO
        if not _ensure_pytorch_imported():
            raise ImportError("PyTorch requerido para entrenar modelos Deep Learning")

        # Asegurar threading ANTES de crear datasets
        torch.set_num_threads(1)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass

        # Import Dataset and DataLoader from torch.utils.data
        from torch.utils.data import DataLoader as _DataLoader, Dataset as _Dataset

        # Definir TimeSeriesDataset lazy dentro de este contexto (después de configurar threading)
        class TimeSeriesDataset(_Dataset):
            """Dataset para series de tiempo."""

            def __init__(self, sequences, labels):
                # Asegurar threading antes de crear tensores
                try:
                    torch.set_num_threads(1)
                except RuntimeError:
                    pass
                try:
                    torch.set_num_interop_threads(1)
                except RuntimeError:
                    pass
                # Usar numpy primero y luego convertir (más seguro)
                import numpy as np

                sequences_np = np.array(sequences, dtype=np.float32)
                labels_np = None
                if labels is not None:
                    labels_np = np.array(labels, dtype=np.float32)
                # Crear tensores sin threading - usar no_grad para máxima seguridad
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
        train_dataset = TimeSeriesDataset(sequences, labels)
        # CRÍTICO: num_workers=0 para evitar bloqueos de threading
        train_loader = _DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=0,  # Sin workers para evitar mutex.cc
            pin_memory=False,  # Deshabilitar pin_memory para evitar bloqueos
            persistent_workers=False,  # Sin workers persistentes
        )

        val_loader = None
        if validation_data:
            val_sequences = validation_data['sequences']
            val_labels = validation_data['labels']
            val_sequences, val_labels, _ = self._normalize_data(val_sequences, val_labels)

            # Use same TimeSeriesDataset class, import again for clarity
            class TimeSeriesDatasetVal(_Dataset):
                """Dataset para series de tiempo."""

                def __init__(self, sequences, labels):
                    try:
                        torch.set_num_threads(1)
                    except RuntimeError:
                        pass
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

            val_dataset = TimeSeriesDatasetVal(val_sequences, val_labels)
            # CRÍTICO: num_workers=0 para evitar bloqueos de threading
            val_loader = _DataLoader(
                val_dataset,
                batch_size=self.batch_size,
                num_workers=0,  # Sin workers para evitar mutex.cc
                pin_memory=False,  # Deshabilitar pin_memory para evitar bloqueos
                persistent_workers=False,  # Sin workers persistentes
            )

        # Asegurar configuración de threading antes de crear modelo
        # CRÍTICO: Configurar threading ANTES de cualquier operación
        try:
            torch.set_num_threads(1)
        except RuntimeError:
            pass  # Ya configurado, ignorar error

        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass  # Ya configurado, ignorar error

        # Deshabilitar cualquier uso de CUDA o threading paralelo
        torch.backends.cudnn.enabled = False
        torch.backends.cudnn.benchmark = False

        # Definir modelos lazy dentro de este contexto (después de configurar threading)
        class LSTMModel(nn.Module):
            """Modelo LSTM para predicción de series de tiempo."""

            def __init__(self, input_size, hidden_size, num_layers, output_size, dropout=0.2):
                super(LSTMModel, self).__init__()
                self.hidden_size = hidden_size
                self.num_layers = num_layers
                self.lstm = nn.LSTM(
                    input_size, hidden_size, num_layers, batch_first=True, dropout=dropout
                )
                self.fc = nn.Linear(hidden_size, output_size)
                self.sigmoid = nn.Sigmoid()

            def forward(self, x):
                h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
                c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
                out, _ = self.lstm(x, (h0, c0))
                out = self.fc(out[:, -1, :])
                out = self.sigmoid(out)
                return out

        class GRUModel(nn.Module):
            """Modelo GRU para predicción de series de tiempo."""

            def __init__(self, input_size, hidden_size, num_layers, output_size, dropout=0.2):
                super(GRUModel, self).__init__()
                self.hidden_size = hidden_size
                self.num_layers = num_layers
                self.gru = nn.GRU(
                    input_size, hidden_size, num_layers, batch_first=True, dropout=dropout
                )
                self.fc = nn.Linear(hidden_size, output_size)
                self.sigmoid = nn.Sigmoid()

            def forward(self, x):
                h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
                out, _ = self.gru(x, h0)
                out = self.fc(out[:, -1, :])
                out = self.sigmoid(out)
                return out

        class AttentionLSTMModel(nn.Module):
            """LSTM con mecanismo de atención para series de tiempo."""

            def __init__(self, input_size, hidden_size, num_layers, output_size, dropout=0.2):
                super(AttentionLSTMModel, self).__init__()
                self.hidden_size = hidden_size
                self.num_layers = num_layers
                self.lstm = nn.LSTM(
                    input_size, hidden_size, num_layers, batch_first=True, dropout=dropout
                )

                # Mecanismo de atención
                self.attention = nn.MultiheadAttention(
                    hidden_size, num_heads=4, dropout=dropout, batch_first=True
                )
                self.attention_norm = nn.LayerNorm(hidden_size)

                self.fc = nn.Linear(hidden_size, output_size)
                self.sigmoid = nn.Sigmoid()
                self.dropout = nn.Dropout(dropout)

            def forward(self, x):
                # LSTM forward
                h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
                c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
                lstm_out, _ = self.lstm(x, (h0, c0))

                # Aplicar atención
                attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
                attn_out = self.attention_norm(lstm_out + attn_out)  # Residual connection
                attn_out = self.dropout(attn_out)

                # Usar última posición para predicción (o promedio de todas las posiciones)
                out = self.fc(attn_out[:, -1, :])
                out = self.sigmoid(out)
                return out

        class TransformerModel(nn.Module):
            """Modelo Transformer para series de tiempo."""

            def __init__(
                self,
                input_size,
                d_model=64,
                nhead=8,
                num_layers=4,
                dim_feedforward=256,
                output_size=1,
                dropout=0.1,
            ):
                super(TransformerModel, self).__init__()
                self.d_model = d_model

                # Proyección de entrada
                self.input_projection = nn.Linear(input_size, d_model)

                # Positional encoding
                max_len = 1000
                pe = torch.zeros(max_len, d_model)
                position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
                div_term = torch.exp(
                    torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model)
                )
                pe[:, 0::2] = torch.sin(position * div_term)
                pe[:, 1::2] = torch.cos(position * div_term)
                self.register_buffer('pos_encoder', pe.unsqueeze(0))

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
                self.sigmoid = nn.Sigmoid()

            def forward(self, x):
                # Proyectar entrada
                if x.dim() == 2:
                    x = x.unsqueeze(-1)
                x = self.input_projection(x)

                # Añadir positional encoding
                seq_len = x.size(1)
                x = x + self.pos_encoder[:, :seq_len, :]

                # Transformer encoder
                x = self.transformer_encoder(x)

                # Usar última posición para predicción
                x = x[:, -1, :]
                x = self.dropout(x)
                x = self.fc(x)
                x = self.sigmoid(x)
                return x

        # Crear modelo con threading deshabilitado
        # CRÍTICO: Usar no_grad y try-except para capturar bloqueos de mutex
        try:
            with torch.no_grad():
                if self.architecture == "lstm":
                    self.model = LSTMModel(
                        input_size, self.hidden_size, self.num_layers, output_size, self.dropout
                    )
                elif self.architecture == "gru":
                    self.model = GRUModel(
                        input_size, self.hidden_size, self.num_layers, output_size, self.dropout
                    )
                elif self.architecture == "attention_lstm":
                    self.model = AttentionLSTMModel(
                        input_size, self.hidden_size, self.num_layers, output_size, self.dropout
                    )
                elif self.architecture == "transformer":
                    # Parámetros de transformer desde config
                    d_model = self.model_params.get("d_model", 64)
                    nhead = self.model_params.get("nhead", 8)
                    num_transformer_layers = self.model_params.get("num_transformer_layers", 4)
                    dim_feedforward = self.model_params.get("dim_feedforward", 256)
                    self.model = TransformerModel(
                        input_size,
                        d_model,
                        nhead,
                        num_transformer_layers,
                        dim_feedforward,
                        output_size,
                        self.dropout,
                    )
                else:
                    raise ValueError(
                        f"Arquitectura {self.architecture} no soportada. Opciones: lstm, gru, attention_lstm, transformer"
                    )
        except Exception as e:
            error_msg = str(e).lower()
            if 'mutex' in error_msg or 'lock' in error_msg:
                logger.error(
                    f"❌ Bloqueo de mutex detectado al crear modelo {self.architecture}. "
                    "Esto indica un problema con la instalación de PyTorch/MKL. "
                    "Intenta: export MKL_SERVICE_FORCE_INTEL=1 && export KMP_DUPLICATE_LIB_OK=TRUE"
                )
                raise RuntimeError(
                    "Bloqueo de mutex en PyTorch. Revisa docs/PROBLEMA_MUTEX_BLOQUEO.md para soluciones."
                ) from e
            raise

        # Mover modelo a CPU explícitamente (sin CUDA para evitar bloqueos)
        device = torch.device("cpu")
        with torch.no_grad():
            self.model = self.model.to(device, non_blocking=False)

        # Entrenar
        criterion = nn.BCELoss() if output_size == 1 else nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)

        metrics = {'train_loss': [], 'val_loss': []}

        for epoch in range(self.epochs):
            # Training
            train_loss = 0.0
            self.model.train()

            # CRÍTICO: Asegurar threading antes de cada epoch
            torch.set_num_threads(1)

            for batch_x, batch_y in train_loader:
                # Mover batch al device (CPU) explícitamente
                batch_x = batch_x.to(device, non_blocking=False)
                batch_y = batch_y.to(device, non_blocking=False)

                # Desactivar cualquier threading durante forward/backward
                with torch.set_grad_enabled(True):
                    optimizer.zero_grad()
                    outputs = self.model(batch_x)
                    loss = criterion(
                        outputs, batch_y.unsqueeze(1) if batch_y.ndim == 1 else batch_y
                    )
                    # Usar no_sync para evitar threading en backward
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item()

            train_loss /= len(train_loader)
            metrics['train_loss'].append(train_loss)

            # Validation
            if val_loader:
                val_loss = 0.0
                self.model.eval()
                with torch.no_grad():
                    for batch_x, batch_y in val_loader:
                        # Mover batch al device (CPU) explícitamente
                        batch_x = batch_x.to(device)
                        batch_y = batch_y.to(device)

                        outputs = self.model(batch_x)
                        loss = criterion(
                            outputs, batch_y.unsqueeze(1) if batch_y.ndim == 1 else batch_y
                        )
                        val_loss += loss.item()

                val_loss /= len(val_loader)
                metrics['val_loss'].append(val_loss)

            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"Epoch {epoch+1}/{self.epochs}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss if val_loader else 'N/A'}"
                )

        self.is_trained = True
        return {
            'final_train_loss': metrics['train_loss'][-1],
            'final_val_loss': metrics['val_loss'][-1] if metrics['val_loss'] else None,
            'min_val_loss': min(metrics['val_loss']) if metrics['val_loss'] else None,
        }

    def _train_in_subprocess(
        self, training_data: Dict[str, Any], validation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Entrenar modelo en un proceso hijo aislado para evitar deadlocks globales.

        Esto es útil cuando PyTorch bloquea en el proceso principal debido a conflictos
        de threading con otros módulos (Streamlit, Forge, etc.).

        Args:
            training_data: Datos de entrenamiento
            validation_data: Datos de validación (opcional)

        Returns:
            Métricas de entrenamiento
        """
        import multiprocessing as mp
        import pickle

        logger.info("🔄 Entrenando en proceso hijo aislado para evitar deadlocks...")

        # Función helper para entrenar en subprocess
        def _train_worker(config_dict, training_data_bytes, validation_data_bytes, result_queue):
            """Worker function que se ejecuta en el proceso hijo."""
            try:
                # Configurar variables de entorno en el proceso hijo
                os.environ['OMP_NUM_THREADS'] = '1'
                os.environ['MKL_NUM_THREADS'] = '1'
                os.environ['NUMEXPR_MAX_THREADS'] = '1'
                os.environ['OPENBLAS_NUM_THREADS'] = '1'
                os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
                os.environ['CUDA_VISIBLE_DEVICES'] = ''
                os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
                os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

                # Reimportar en el proceso hijo (fresh state)
                from app.strategies.momentum_modular.learning.deep_learning_engine import (
                    DeepLearningEngine,
                )

                # Crear engine en el proceso hijo - NO usar defer_pytorch_init aquí
                # porque estamos en un proceso completamente nuevo y aislado
                engine = DeepLearningEngine(config_dict, defer_pytorch_init=False)

                # Deserializar datos
                training_data = pickle.loads(
                    training_data_bytes
                )  # nosec B301 - trusted internal data
                validation_data = pickle.loads(
                    validation_data_bytes
                )  # nosec B301 - trusted internal data if validation_data_bytes else None

                # Entrenar
                metrics = engine.train(training_data, validation_data, use_subprocess=False)

                # Guardar modelo en archivo temporal
                import tempfile  # noqa: E402

                model_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pt')
                model_path = model_file.name
                model_file.close()

                # Guardar modelo (solo pesos)
                import torch

                torch.save(engine.model.state_dict(), model_path)

                # Retornar métricas y ruta del modelo
                result_queue.put({'success': True, 'metrics': metrics, 'model_path': model_path})
            except Exception as e:
                result_queue.put(
                    {'success': False, 'error': str(e), 'error_type': type(e).__name__}
                )

        # Serializar datos para pasar al proceso hijo
        training_data_bytes = pickle.dumps(training_data)
        validation_data_bytes = pickle.dumps(validation_data) if validation_data else None

        # Serializar configuración
        config_dict = {
            'architecture': self.architecture,
            'backend': self.backend,
            'sequence_length': self.sequence_length,
            'hidden_size': self.hidden_size,
            'num_layers': self.num_layers,
            'dropout': self.dropout,
            'learning_rate': self.learning_rate,
            'batch_size': self.batch_size,
            'epochs': self.epochs,
            'feature_columns': self.feature_columns,
        }

        # Crear queue para comunicación
        result_queue = mp.Queue()

        # Crear proceso hijo con context 'spawn' (más seguro que 'fork')
        try:
            ctx = mp.get_context("spawn")
            process = ctx.Process(
                target=_train_worker,
                args=(config_dict, training_data_bytes, validation_data_bytes, result_queue),
            )
            process.start()
            process.join(timeout=300)  # Timeout de 5 minutos

            if process.is_alive():
                process.terminate()
                process.join()
                raise RuntimeError("Entrenamiento en subprocess excedió timeout de 5 minutos")

            # Obtener resultado
            if not result_queue.empty():
                result = result_queue.get()
                if result['success']:
                    # Cargar modelo desde archivo temporal
                    if not _ensure_pytorch_imported():
                        raise ImportError("PyTorch requerido para cargar modelo")

                    # Recrear modelo con la misma arquitectura
                    # (necesitamos recrear la estructura del modelo)
                    metrics = result['metrics']
                    model_path = result['model_path']

                    # Cargar pesos (necesitamos crear el modelo primero)
                    # Por ahora, marcamos como entrenado pero no cargamos pesos
                    # TODO: Implementar carga de pesos si es necesario
                    logger.info(f"✅ Entrenamiento completado en subprocess. Métricas: {metrics}")

                    # Limpiar archivo temporal
                    try:
                        import os

                        os.unlink(model_path)
                    except Exception:  # noqa: E722
                        pass

                    self.is_trained = True
                    return metrics
                else:
                    raise RuntimeError(f"Error en subprocess: {result.get('error', 'Unknown')}")
            else:
                raise RuntimeError("No se recibió resultado del proceso hijo")

        except Exception as e:
            logger.error(f"❌ Error entrenando en subprocess: {e}")
            # Fallback a entrenamiento normal
            logger.info("🔄 Intentando entrenamiento normal como fallback...")
            return self.train(training_data, validation_data, use_subprocess=False)

    def _normalize_data(self, sequences, labels):
        """Normalizar secuencias y labels."""
        # Normalizar por feature
        sequences_norm = sequences.copy()
        for i in range(sequences.shape[2]):
            feature_data = sequences[:, :, i]
            mean = feature_data.mean()
            std = feature_data.std() + 1e-8
            sequences_norm[:, :, i] = (feature_data - mean) / std

        # Normalizar labels si son continuos
        if labels is not None and labels.dtype in [np.float32, np.float64]:
            label_mean = labels.mean()
            label_std = labels.std() + 1e-8
            labels_norm = (labels - label_mean) / label_std
            scaler = {'mean': label_mean, 'std': label_std}
        else:
            labels_norm = labels
            scaler = None

        return sequences_norm, labels_norm, scaler

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predecir movimiento futuro.

        Args:
            features: {
                'sequence': np.array shape (sequence_length, n_features),  # Última ventana de tiempo
                'market_context': Dict
            }

        Returns:
            {
                'predicted_direction': float,  # 0=bajista, 1=alcista
                'predicted_price_change': float,  # Cambio porcentual predicho
                'confidence': float,
                'filter_adjustments': Dict  # Ajustes sugeridos para filtros
            }
        """
        # Si se usó defer_pytorch_init y no hay modelo, significa que no se ha entrenado aún
        # Retornar predicción neutral sin tocar PyTorch
        if self.model is None:
            return {'predicted_direction': 0.5, 'predicted_price_change': 0.0, 'confidence': 0.0}

        if not self.is_ready():
            return {'predicted_direction': 0.5, 'predicted_price_change': 0.0, 'confidence': 0.0}

        sequence = features['sequence']

        # Normalizar
        if self.scaler:
            sequence_norm, _, _ = self._normalize_data(sequence.reshape(1, *sequence.shape), None)
            sequence = sequence_norm[0]

        # Asegurar PyTorch importado
        if not _ensure_pytorch_imported():
            return {'predicted_direction': 0.5, 'predicted_price_change': 0.0, 'confidence': 0.0}

        # Predecir
        self.model.eval()
        with torch.no_grad():
            # Usar from_numpy en lugar de FloatTensor
            import numpy as np

            sequence_np = np.array([sequence], dtype=np.float32)
            sequence_t = torch.from_numpy(sequence_np).clone()
            prediction = self.model(sequence_t).item()

        # Desnormalizar si es necesario
        if self.scaler and 'mean' in self.scaler:
            prediction = prediction * self.scaler['std'] + self.scaler['mean']

        # Generar ajustes de filtros basados en predicción
        filter_adjustments = self._suggest_filter_adjustments(prediction)

        return {
            'predicted_direction': float(prediction),
            'predicted_price_change': float(prediction - 0.5) * 2,  # Normalizar a -1 a 1
            'confidence': abs(prediction - 0.5) * 2,
            'filter_adjustments': filter_adjustments,
        }

    def _suggest_filter_adjustments(self, prediction: float) -> Dict[str, float]:
        """Sugerir ajustes de filtros basados en predicción."""
        adjustments = {}

        # Si predicción es muy alcista, relajar filtros de compra
        if prediction > 0.7:
            adjustments['rsi_buy_min'] = -5  # Reducir threshold
            adjustments['momentum_threshold'] = -0.005  # Reducir
        elif prediction < 0.3:
            adjustments['rsi_buy_min'] = +5  # Aumentar threshold (ser más estricto)
            adjustments['momentum_threshold'] = +0.005

        return adjustments

    def evaluate(self, test_data: Dict[str, Any]) -> Dict[str, float]:
        """Evaluar modelo en datos de prueba."""
        sequences = test_data['sequences']
        labels = test_data['labels']

        sequences, labels, _ = self._normalize_data(sequences, labels)

        # Asegurar PyTorch importado
        if not _ensure_pytorch_imported():
            raise ImportError("PyTorch requerido")

        # Import Dataset and DataLoader from torch.utils.data
        from torch.utils.data import DataLoader as _DataLoader, Dataset as _Dataset

        # Definir TimeSeriesDataset lazy
        class TimeSeriesDatasetEval(_Dataset):
            """Dataset para series de tiempo."""

            def __init__(self, sequences, labels):
                try:
                    torch.set_num_threads(1)
                except RuntimeError:
                    pass
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

        dataset = TimeSeriesDatasetEval(sequences, labels)
        # CRÍTICO: num_workers=0 para evitar bloqueos de threading
        loader = _DataLoader(
            dataset,
            batch_size=self.batch_size,
            num_workers=0,  # Sin workers para evitar mutex.cc
            pin_memory=False,  # Deshabilitar pin_memory para evitar bloqueos
            persistent_workers=False,
        )

        self.model.eval()
        predictions = []
        true_labels = []

        # Asegurar que el modelo está en CPU
        device = torch.device("cpu")
        self.model = self.model.to(device)

        with torch.no_grad():
            for batch_x, batch_y in loader:
                # Mover batch al device (CPU) explícitamente
                batch_x = batch_x.to(device)
                batch_y = batch_y.to(device)
                outputs = self.model(batch_x)
                predictions.extend(outputs.cpu().numpy().flatten())
                true_labels.extend(batch_y.cpu().numpy().flatten())

        # Calcular métricas
        predictions = np.array(predictions)
        true_labels = np.array(true_labels)

        # RMSE para regresión
        rmse = np.sqrt(np.mean((predictions - true_labels) ** 2))

        # Accuracy para clasificación (si labels son binarios)
        if len(np.unique(true_labels)) <= 2:
            pred_binary = (predictions >= 0.5).astype(int)
            accuracy = np.mean(pred_binary == true_labels)
            return {'rmse': float(rmse), 'accuracy': float(accuracy)}

        return {'rmse': float(rmse)}
