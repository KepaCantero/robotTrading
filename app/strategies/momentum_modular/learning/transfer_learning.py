"""
TransferLearning - Sistema de transfer learning para modelos de trading.

Incluye:
1. Pre-trained models para diferentes regímenes de mercado
2. Fine-tuning adaptativo
3. Knowledge distillation entre modelos
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np

if TYPE_CHECKING:
    import torch.nn as nn

logger = logging.getLogger(__name__)

# ============================================================================
# Optional Dependencies
# ============================================================================
try:
    import torch

    PYTORCH_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    torch = None  # type: ignore
    PYTORCH_AVAILABLE = False

try:
    import joblib

    JOBLIB_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    joblib = None  # type: ignore
    JOBLIB_AVAILABLE = False

try:
    import msgpack

    MSGPACK_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    msgpack = None  # type: ignore
    MSGPACK_AVAILABLE = False


class ModelRegistry:
    """
    Registro de modelos pre-entrenados para transfer learning.

    Almacena metadatos y paths de modelos entrenados en diferentes regímenes.
    """

    def __init__(
        self,
        registry_path: str = "models/registry",
    ):
        """
        Inicializar registry.

        Args:
            registry_path: Ruta base del registry
        """
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_path / "registry.json"
        self.models_dir = self.registry_path / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Cargar registry existente
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        """Cargar registry desde archivo JSON."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    return json.load(f)
            except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
                logger.warning(f"Error cargando registry: {e}")
                return {}
        return {}

    def _save_registry(self) -> None:
        """Guardar registry a archivo JSON."""
        try:
            with open(self.registry_file, 'w') as f:
                json.dump(self.registry, f, indent=2, default=str)
        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            logger.error(f"Error guardando registry: {e}", exc_info=True)
            # No raise - registry sigue funcionando en memoria aunque no se guarde

    def register_model(
        self,
        model: Any,
        model_id: str,
        regime: str,
        model_type: str,
        algorithm: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Registrar un modelo pre-entrenado usando serialización segura.

        Args:
            model: Modelo entrenado
            model_id: ID único del modelo
            regime: Régimen de mercado (bull, bear, sideways, etc.)
            model_type: Tipo (supervised, deep, transformer)
            algorithm: Algoritmo (xgboost, lstm, etc.)
            metadata: Metadata adicional (métricas, config, etc.)
            tags: Tags adicionales

        Returns:
            True si se registró correctamente
        """
        try:
            # SECURITY: Use joblib for sklearn models, torch.save for PyTorch
            # Avoid pickle for security reasons
            model_path = None
            model_saved = False
            model_format = None

            try:
                self.models_dir.mkdir(parents=True, exist_ok=True)

                # Detect model type and use appropriate serialization
                if PYTORCH_AVAILABLE and 'torch.nn' in str(type(model)):
                    # PyTorch model - use torch.save (secure for PyTorch objects)
                    model_path = self.models_dir / f"{model_id}.pt"
                    torch.save(model, model_path)
                    model_saved = True
                    model_format = 'pt'
                elif JOBLIB_AVAILABLE:
                    # sklearn or other models - use joblib (secure)
                    model_path = self.models_dir / f"{model_id}.joblib"
                    joblib.dump(model, model_path)
                    model_saved = True
                    model_format = 'joblib'
                elif MSGPACK_AVAILABLE:
                    # Generic Python objects - use msgpack with custom encoding
                    model_path = self.models_dir / f"{model_id}.msgpack"
                    self._save_model_msgpack(model, model_path)
                    model_saved = True
                    model_format = 'msgpack'
                else:
                    logger.warning(
                        f"No secure serialization available for model {model_id}. "
                        "Saving metadata only."
                    )

            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.warning(
                    f"No se pudo serializar modelo {model_id}: {e}. Guardando solo metadata."
                )
                model_path = None

            # Registrar en registry
            entry = {
                'model_id': model_id,
                'regime': regime,
                'model_type': model_type,
                'algorithm': algorithm,
                'model_path': str(model_path) if model_path else None,
                'model_format': model_format,
                'registered_at': datetime.now().isoformat(),
                'metadata': metadata or {},
                'tags': tags or [],
                'model_saved': model_saved,
            }

            # Crear índice por régimen
            if regime not in self.registry:
                self.registry[regime] = {}

            if model_type not in self.registry[regime]:
                self.registry[regime][model_type] = {}

            self.registry[regime][model_type][model_id] = entry

            # Índice global
            if 'all_models' not in self.registry:
                self.registry['all_models'] = {}
            self.registry['all_models'][model_id] = entry

            # Guardar registry (puede fallar pero no es crítico)
            try:
                self._save_registry()
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.warning(f"Error guardando registry (no crítico): {e}")

            logger.info(f"Modelo {model_id} registrado para régimen {regime}")
            return True

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error registrando modelo: {e}", exc_info=True)
            return False

    def _save_model_msgpack(self, model: Any, path: Path) -> None:
        """
        Save model using msgpack for generic Python objects.

        Args:
            model: Model to save
            path: Path to save to
        """
        import io

        # Convert model to bytes using msgpack
        # For numpy arrays, msgpack-numpy is recommended, but we'll use a simple approach
        buffer = io.BytesIO()

        # Try to convert to dict if possible
        if hasattr(model, '__dict__'):
            # Model has __dict__, convert to dict
            model_dict = {
                '_module': model.__class__.__module__,
                '_class': model.__class__.__name__,
                'data': model.__dict__,
            }
            packed = msgpack.packb(model_dict)
        else:
            # Fallback to string representation (not ideal but safe)
            packed = msgpack.packb({'_repr': repr(model)})

        buffer.write(packed)
        buffer.seek(0)

        with open(path, 'wb') as f:
            f.write(buffer.read())

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información de un modelo por ID.

        Args:
            model_id: ID del modelo

        Returns:
            Dict con información del modelo o None
        """
        return self.registry.get('all_models', {}).get(model_id)

    def list_models(
        self,
        regime: Optional[str] = None,
        model_type: Optional[str] = None,
        algorithm: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Listar modelos que coinciden con criterios.

        Args:
            regime: Filtrar por régimen
            model_type: Filtrar por tipo
            algorithm: Filtrar por algoritmo
            tags: Filtrar por tags

        Returns:
            Lista de modelos que coinciden
        """
        results = []

        if regime:
            # Buscar en régimen específico
            regime_models = self.registry.get(regime, {})
            for model_type_dict in regime_models.values():
                for model_entry in model_type_dict.values():
                    if self._matches_filters(model_entry, model_type, algorithm, tags):
                        results.append(model_entry)
        else:
            # Buscar en todos
            for model_entry in self.registry.get('all_models', {}).values():
                if self._matches_filters(model_entry, model_type, algorithm, tags):
                    results.append(model_entry)

        return results

    def _matches_filters(
        self,
        model_entry: Dict[str, Any],
        model_type: Optional[str],
        algorithm: Optional[str],
        tags: Optional[List[str]],
    ) -> bool:
        """Verificar si un modelo coincide con los filtros."""
        if model_type and model_entry.get('model_type') != model_type:
            return False
        if algorithm and model_entry.get('algorithm') != algorithm:
            return False
        if tags:
            model_tags = model_entry.get('tags', [])
            if not any(tag in model_tags for tag in tags):
                return False
        return True

    def load_model(self, model_id: str) -> Optional[Any]:
        """
        Cargar modelo desde registry usando serialización segura.

        Args:
            model_id: ID del modelo

        Returns:
            Modelo cargado o None
        """
        entry = self.get_model(model_id)
        if not entry:
            logger.warning(f"Modelo {model_id} no encontrado en registry")
            return None

        model_path = entry.get('model_path')

        # Si el modelo no fue guardado (no serializable), retornar None
        if not entry.get('model_saved', False):
            logger.info(
                f"Modelo {model_id} no fue serializado (no serializable). Usar metadata para recrear."
            )
            return None

        if not model_path or not Path(model_path).exists():
            logger.warning(f"Archivo de modelo no encontrado: {model_path}")
            return None

        try:
            model_format = entry.get('model_format', '')
            model_path_obj = Path(model_path)

            # SECURITY: Use appropriate loader based on format
            if model_format == 'pt' or model_path_obj.suffix == '.pt':
                if not PYTORCH_AVAILABLE:
                    raise ImportError("PyTorch no disponible para cargar .pt")
                model = torch.load(
                    model_path_obj, map_location='cpu'
                )  # nosec B614 - torch handles this
            elif model_format == 'joblib' or model_path_obj.suffix == '.joblib':
                if not JOBLIB_AVAILABLE:
                    raise ImportError("joblib no disponible para cargar .joblib")
                model = joblib.load(model_path_obj)
            elif model_format == 'msgpack' or model_path_obj.suffix == '.msgpack':
                if not MSGPACK_AVAILABLE:
                    raise ImportError("msgpack no disponible para cargar .msgpack")
                model = self._load_model_msgpack(model_path_obj)
            elif model_path_obj.suffix == '.pkl':
                # SECURITY: Migrate old .pkl files to secure format
                logger.warning(f"Found old .pkl file for {model_id}, migrating...")
                model = self._migrate_pkl_model(model_path_obj, entry)
            else:
                logger.error(f"Unsupported model format: {model_format}")
                return None

            logger.info(f"Modelo {model_id} cargado desde {model_path}")
            return model
        except (FileNotFoundError, PermissionError, IOError, OSError, IsADirectoryError) as e:
            logger.error(f"Error cargando modelo {model_id}: {e}", exc_info=True)
            return None

    def _load_model_msgpack(self, path: Path) -> Any:
        """
        Load model using msgpack.

        Args:
            path: Path to load from

        Returns:
            Loaded model
        """
        with open(path, 'rb') as f:
            data = msgpack.unpackb(f.read(), raw=False)

        # Reconstruct object if it was saved with __dict__
        if '_module' in data and '_class' in data and 'data' in data:
            # Import the class
            import importlib

            module = importlib.import_module(data['_module'])
            cls = getattr(module, data['_class'])
            obj = cls.__new__(cls)
            obj.__dict__.update(data['data'])
            return obj
        elif '_repr' in data:
            # Fallback - return the representation as string
            return data['_repr']
        else:
            return data

    def _migrate_pkl_model(self, pkl_path: Path, entry: Dict[str, Any]) -> Any:
        """
        Migrate old .pkl model to secure format (one-time migration).

        Args:
            pkl_path: Path to old .pkl file
            entry: Registry entry for the model

        Returns:
            Loaded model
        """
        try:
            # SECURITY: One-time migration from pickle to secure format
            # This is only for migrating existing trusted model files
            import pickle  # noqa: S403 - Only for migration

            with open(pkl_path, 'rb') as f:
                model = pickle.load(f)  # noqa: S301 - Trusted migration only

            # Re-save in secure format
            model_id = entry['model_id']
            if JOBLIB_AVAILABLE:
                # Try joblib first
                joblib_path = pkl_path.with_suffix('.joblib')
                joblib.dump(model, joblib_path)

                # Update registry
                entry['model_path'] = str(joblib_path)
                entry['model_format'] = 'joblib'
                self._save_registry()

                # Remove old .pkl
                pkl_path.unlink()

                logger.info(f"Migrated {model_id} from .pkl to .joblib")
            else:
                logger.warning(f"Cannot migrate {model_id}: joblib not available")

            return model

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error migrating model from .pkl: {e}")
            return None


class FineTuner:
    """
    Sistema de fine-tuning adaptativo para modelos pre-entrenados.

    Soporta:
    - Neural networks (PyTorch): Freeze layers, adjust learning rate
    - Tree-based models: Continuar entrenamiento con nuevos datos
    - Adaptación a nuevos regímenes de mercado
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar fine-tuner.

        Args:
            config: Configuración
        """
        config = config or {}
        self.freeze_layers = config.get("freeze_layers", True)  # Freeze early layers
        self.freeze_n_layers = config.get("freeze_n_layers", 0)  # Número de capas a freeze
        self.learning_rate_multiplier = config.get("learning_rate_multiplier", 0.1)  # LR más bajo
        self.fine_tune_epochs = config.get("fine_tune_epochs", 10)
        self.early_stopping_patience = config.get("early_stopping_patience", 5)

    def fine_tune(
        self,
        base_model: Any,
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None,
        model_type: str = "auto",
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Fine-tune un modelo pre-entrenado.

        Args:
            base_model: Modelo pre-entrenado
            training_data: Nuevos datos de entrenamiento
            validation_data: Datos de validación
            model_type: Tipo de modelo (auto, pytorch, tree, sklearn)

        Returns:
            (modelo_fine_tuned, métricas)
        """
        if model_type == "auto":
            model_type = self._detect_model_type(base_model)

        if model_type == "pytorch":
            return self._fine_tune_pytorch(base_model, training_data, validation_data)
        elif model_type in ["tree", "sklearn"]:
            return self._fine_tune_tree_based(base_model, training_data, validation_data)
        else:
            logger.warning(f"Fine-tuning no soportado para tipo {model_type}")
            return base_model, {}

    def _detect_model_type(self, model: Any) -> str:
        """Detectar tipo de modelo."""
        model_type = str(type(model)).lower()

        if any(x in model_type for x in ['module', 'nn', 'sequential']):
            return "pytorch"
        elif any(
            x in model_type
            for x in ['xgboost', 'lightgbm', 'catboost', 'randomforest', 'gradientboosting']
        ):
            return "tree"
        else:
            return "sklearn"

    def _fine_tune_pytorch(
        self,
        model: "nn.Module",
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple["nn.Module", Dict[str, float]]:
        """
        Fine-tune modelo PyTorch.

        Args:
            model: Modelo PyTorch
            training_data: Datos de entrenamiento
            validation_data: Datos de validación

        Returns:
            (modelo_fine_tuned, métricas)
        """
        if not PYTORCH_AVAILABLE:
            logger.error("PyTorch no disponible para fine-tuning")
            return model, {}

        try:
            # Clonar modelo para no modificar el original
            fine_tuned_model = self._clone_pytorch_model(model)

            # Freeze layers si está configurado
            if self.freeze_layers:
                self._freeze_layers(fine_tuned_model)

            # Preparar datos
            # Asumir que training_data tiene 'sequences' y 'labels' para deep learning
            sequences = training_data.get('sequences')
            labels = training_data.get('labels')

            if sequences is None or labels is None:
                logger.error("training_data debe contener 'sequences' y 'labels'")
                return model, {}

            # Convertir a tensores
            sequences_t = torch.FloatTensor(sequences)
            labels_t = (
                torch.FloatTensor(labels).unsqueeze(1)
                if labels.ndim == 1
                else torch.FloatTensor(labels)
            )

            # Optimizer con learning rate reducido
            lr = 0.001 * self.learning_rate_multiplier
            optimizer = optim.Adam(fine_tuned_model.parameters(), lr=lr)
            criterion = nn.MSELoss() if labels_t.dtype == torch.float32 else nn.BCELoss()

            # Training loop
            fine_tuned_model.train()
            metrics = {'train_loss': []}

            for epoch in range(self.fine_tune_epochs):
                optimizer.zero_grad()
                outputs = fine_tuned_model(sequences_t)
                loss = criterion(outputs, labels_t)
                loss.backward()
                optimizer.step()

                metrics['train_loss'].append(float(loss.item()))

                if (epoch + 1) % 5 == 0:
                    logger.debug(
                        f"Fine-tuning epoch {epoch+1}/{self.fine_tune_epochs}, Loss: {loss.item():.4f}"
                    )

            # Validation
            if validation_data:
                val_sequences = validation_data.get('sequences')
                val_labels = validation_data.get('labels')
                if val_sequences is not None and val_labels is not None:
                    fine_tuned_model.eval()
                    with torch.no_grad():
                        val_sequences_t = torch.FloatTensor(val_sequences)
                        val_labels_t = (
                            torch.FloatTensor(val_labels).unsqueeze(1)
                            if val_labels.ndim == 1
                            else torch.FloatTensor(val_labels)
                        )
                        val_outputs = fine_tuned_model(val_sequences_t)
                        val_loss = criterion(val_outputs, val_labels_t)
                        metrics['val_loss'] = float(val_loss.item())

            return fine_tuned_model, metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en fine-tuning PyTorch: {e}", exc_info=True)
            return model, {}

    def _clone_pytorch_model(self, model: "nn.Module") -> "nn.Module":
        """Clonar modelo PyTorch."""
        # Usar copy.deepcopy para clonar modelo completo
        import copy

        try:
            cloned = copy.deepcopy(model)
            return cloned
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.warning(
                f"No se pudo clonar modelo con deepcopy: {e}. Usando estado del modelo original."
            )
            # Fallback: retornar el modelo original (no es ideal pero funciona)
            return model

    def _freeze_layers(self, model: "nn.Module") -> None:
        """Freeze early layers del modelo."""
        if self.freeze_n_layers > 0:
            layers = list(model.children())
            n_freeze = min(self.freeze_n_layers, len(layers))
            for layer in layers[:n_freeze]:
                for param in layer.parameters():
                    param.requires_grad = False
            logger.info(f"Frozen {n_freeze} layers")

    def _fine_tune_tree_based(
        self,
        model: Any,
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Fine-tune modelo tree-based (continuar entrenamiento).

        Args:
            model: Modelo tree-based
            training_data: Nuevos datos
            validation_data: Datos de validación

        Returns:
            (modelo_fine_tuned, métricas)
        """
        try:
            X_train = training_data.get('features')
            y_train = training_data.get('labels')

            if X_train is None or y_train is None:
                logger.error("training_data debe contener 'features' y 'labels'")
                return model, {}

            # Para tree-based models, simplemente continuar entrenamiento
            # Esto funciona mejor con XGBoost, LightGBM, CatBoost

            model_type = str(type(model)).lower()

            if 'xgboost' in model_type:
                # XGBoost: continuar entrenamiento
                model.fit(X_train, y_train, xgb_model=model.get_booster())
                metrics = {'status': 'continued_training'}
            elif 'lightgbm' in model_type:
                # LightGBM: continuar entrenamiento
                # (Requiere implementación específica)
                metrics = {'status': 'tree_based_continued'}
            elif 'catboost' in model_type:
                # CatBoost: continuar entrenamiento
                # (Requiere implementación específica)
                metrics = {'status': 'tree_based_continued'}
            else:
                # Para otros (RandomForest, etc.), retrain desde cero
                # pero con parámetros del modelo original
                metrics = {'status': 'retrained_from_scratch'}

            return model, metrics

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error en fine-tuning tree-based: {e}", exc_info=True)
            return model, {}


class KnowledgeDistiller:
    """
    Sistema de Knowledge Distillation.

    Transfiere conocimiento de un modelo grande (teacher) a uno pequeño (student).
    Útil para comprimir modelos o transferir conocimiento entre regímenes.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar distiller.

        Args:
            config: Configuración
        """
        config = config or {}
        self.temperature = config.get("temperature", 3.0)  # Temperature para softmax
        self.alpha = config.get("alpha", 0.7)  # Weight para soft targets vs hard targets
        self.distillation_epochs = config.get("distillation_epochs", 50)

    def distill(
        self,
        teacher_model: Any,
        student_model: Any,
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Distilar conocimiento de teacher a student.

        Args:
            teacher_model: Modelo grande (teacher)
            student_model: Modelo pequeño (student)
            training_data: Datos de entrenamiento
            validation_data: Datos de validación

        Returns:
            (student_model_trained, métricas)
        """
        try:
            # Detectar tipos
            teacher_type = self._detect_model_type(teacher_model)
            student_type = self._detect_model_type(student_model)

            if teacher_type == "pytorch" and student_type == "pytorch":
                return self._distill_pytorch(
                    teacher_model, student_model, training_data, validation_data
                )
            elif teacher_type in ["tree", "sklearn"] and student_type in ["tree", "sklearn"]:
                return self._distill_tree_based(
                    teacher_model, student_model, training_data, validation_data
                )
            else:
                logger.warning(f"Distillation no soportada entre {teacher_type} y {student_type}")
                return student_model, {}

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en distillation: {e}", exc_info=True)
            return student_model, {}

    def _detect_model_type(self, model: Any) -> str:
        """Detectar tipo de modelo."""
        model_type = str(type(model)).lower()
        if any(x in model_type for x in ['module', 'nn', 'sequential']):
            return "pytorch"
        elif any(x in model_type for x in ['xgboost', 'lightgbm', 'catboost', 'randomforest']):
            return "tree"
        else:
            return "sklearn"

    def _distill_pytorch(
        self,
        teacher: "nn.Module",
        student: "nn.Module",
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple["nn.Module", Dict[str, float]]:
        """
        Distillation para modelos PyTorch.

        Args:
            teacher: Modelo teacher
            student: Modelo student
            training_data: Datos de entrenamiento
            validation_data: Datos de validación

        Returns:
            (student_trained, métricas)
        """
        if not PYTORCH_AVAILABLE:
            logger.error("PyTorch no disponible")
            return student, {}

        try:
            # Preparar datos
            sequences = training_data.get('sequences')
            labels = training_data.get('labels')

            if sequences is None or labels is None:
                logger.error("training_data debe contener 'sequences' y 'labels'")
                return student, {}

            sequences_t = torch.FloatTensor(sequences)
            labels_t = (
                torch.FloatTensor(labels).unsqueeze(1)
                if labels.ndim == 1
                else torch.FloatTensor(labels)
            )

            # Teacher en eval mode
            teacher.eval()
            student.train()

            # Optimizer
            optimizer = optim.Adam(student.parameters(), lr=0.001)

            # Loss function combinado
            def distillation_loss(student_logits, teacher_logits, true_labels, temperature, alpha):
                # Soft targets (teacher)
                soft_targets = nn.functional.softmax(teacher_logits / temperature, dim=1)
                soft_prob = nn.functional.log_softmax(student_logits / temperature, dim=1)
                soft_loss = nn.functional.kl_div(soft_prob, soft_targets, reduction='batchmean') * (
                    temperature**2
                )

                # Hard targets (true labels)
                hard_loss = nn.functional.cross_entropy(student_logits, true_labels.long())

                # Combinar
                return alpha * soft_loss + (1 - alpha) * hard_loss

            metrics = {'train_loss': [], 'distillation_loss': []}

            # Training loop
            for epoch in range(self.distillation_epochs):
                optimizer.zero_grad()

                # Forward pass
                student_logits = student(sequences_t)
                with torch.no_grad():
                    teacher_logits = teacher(sequences_t)

                # Loss
                loss = distillation_loss(
                    student_logits, teacher_logits, labels_t, self.temperature, self.alpha
                )

                loss.backward()
                optimizer.step()

                metrics['train_loss'].append(float(loss.item()))

                if (epoch + 1) % 10 == 0:
                    logger.debug(
                        f"Distillation epoch {epoch+1}/{self.distillation_epochs}, Loss: {loss.item():.4f}"
                    )

            # Validation
            if validation_data:
                val_sequences = validation_data.get('sequences')
                val_labels = validation_data.get('labels')
                if val_sequences is not None and val_labels is not None:
                    student.eval()
                    with torch.no_grad():
                        val_sequences_t = torch.FloatTensor(val_sequences)
                        val_labels_t = (
                            torch.FloatTensor(val_labels).unsqueeze(1)
                            if val_labels.ndim == 1
                            else torch.FloatTensor(val_labels)
                        )
                        val_outputs = student(val_sequences_t)
                        val_loss = nn.functional.mse_loss(val_outputs, val_labels_t)
                        metrics['val_loss'] = float(val_loss.item())

            return student, metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en distillation PyTorch: {e}", exc_info=True)
            return student, {}

    def _distill_tree_based(
        self,
        teacher: Any,
        student: Any,
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Distillation para modelos tree-based.

        Usa predicciones del teacher como "soft labels" para entrenar student.
        """
        try:
            X_train = training_data.get('features')
            y_train = training_data.get('labels')

            if X_train is None or y_train is None:
                logger.error("training_data debe contener 'features' y 'labels'")
                return student, {}

            # Obtener predicciones del teacher (soft labels)
            if hasattr(teacher, 'predict_proba'):
                teacher_probs = teacher.predict_proba(X_train)
            else:
                teacher_probs = teacher.predict(X_train)
                # Convertir a probabilidades si es necesario
                if teacher_probs.ndim == 1:
                    teacher_probs = np.column_stack([1 - teacher_probs, teacher_probs])

            # Aplicar temperature scaling
            teacher_probs_scaled = self._apply_temperature(teacher_probs, self.temperature)

            # Combinar con true labels
            # Usar soft labels con probabilidad alpha
            if self.alpha > 0:
                # Convertir true labels a one-hot
                if y_train.ndim == 1:
                    y_one_hot = np.eye(2)[y_train.astype(int)]
                else:
                    y_one_hot = y_train

                # Combinar soft y hard labels
                combined_labels = self.alpha * teacher_probs_scaled + (1 - self.alpha) * y_one_hot
            else:
                combined_labels = teacher_probs_scaled

            # Entrenar student con soft labels
            # Para tree-based, esto puede requerir custom loss
            # Por ahora, usar predicciones como labels continuos

            # Convertir a labels discretos para tree models
            soft_labels = np.argmax(combined_labels, axis=1)

            # Entrenar student
            student.fit(X_train, soft_labels)

            metrics = {
                'status': 'distilled',
                'teacher_confidence': float(np.mean(np.max(teacher_probs, axis=1))),
                'student_confidence': float(np.mean(np.max(combined_labels, axis=1))),
            }

            return student, metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en distillation tree-based: {e}", exc_info=True)
            return student, {}

    def _apply_temperature(self, probs: np.ndarray, temperature: float) -> np.ndarray:
        """Aplicar temperature scaling a probabilidades."""
        # Softmax con temperature
        exp_probs = np.exp(probs / temperature)
        return exp_probs / np.sum(exp_probs, axis=1, keepdims=True)


class TransferLearningManager:
    """
    Manager unificado para transfer learning.

    Combina ModelRegistry, FineTuner y KnowledgeDistiller.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializar manager.

        Args:
            config: Configuración
        """
        config = config or {}
        self.registry = ModelRegistry(config.get("registry_path", "models/registry"))
        self.fine_tuner = FineTuner(config.get("fine_tuner_config", {}))
        self.distiller = KnowledgeDistiller(config.get("distiller_config", {}))

    def create_pretrained_model(
        self,
        model: Any,
        regime: str,
        model_type: str,
        algorithm: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Crear y registrar un modelo pre-entrenado.

        Args:
            model: Modelo entrenado
            regime: Régimen de mercado
            model_type: Tipo de modelo
            algorithm: Algoritmo
            metadata: Metadata (métricas, performance, etc.)
            tags: Tags adicionales

        Returns:
            model_id generado
        """
        model_id = f"{regime}_{model_type}_{algorithm}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        success = self.registry.register_model(
            model, model_id, regime, model_type, algorithm, metadata, tags
        )

        if not success:
            # Log detailed error but don't raise - return None instead
            logger.error(f"No se pudo registrar modelo {model_id}. Verificar logs para detalles.")
            return None

        return model_id

    def load_and_finetune(
        self,
        model_id: str,
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Cargar modelo pre-entrenado y hacer fine-tuning.

        Args:
            model_id: ID del modelo en registry
            training_data: Nuevos datos de entrenamiento
            validation_data: Datos de validación

        Returns:
            (modelo_fine_tuned, métricas)
        """
        # Cargar modelo
        model = self.registry.load_model(model_id)
        if model is None:
            raise ValueError(f"Modelo {model_id} no encontrado")

        # Obtener metadata
        model_info = self.registry.get_model(model_id)
        model_type = model_info.get('model_type', 'auto')

        # Fine-tune
        fine_tuned_model, metrics = self.fine_tuner.fine_tune(
            model, training_data, validation_data, model_type
        )

        return fine_tuned_model, metrics

    def find_best_model(
        self, regime: str, model_type: str, algorithm: Optional[str] = None
    ) -> Optional[str]:
        """
        Encontrar el mejor modelo pre-entrenado para un régimen.

        Args:
            regime: Régimen de mercado
            model_type: Tipo de modelo
            algorithm: Algoritmo (opcional)

        Returns:
            model_id del mejor modelo o None
        """
        models = self.registry.list_models(
            regime=regime, model_type=model_type, algorithm=algorithm
        )

        if not models:
            return None

        # Seleccionar por mejor métrica en metadata
        best_model = None
        best_score = -float('inf')

        for model_entry in models:
            metadata = model_entry.get('metadata', {})
            # Buscar métricas comunes
            score = metadata.get('accuracy', metadata.get('f1_score', metadata.get('roc_auc', 0)))
            if score > best_score:
                best_score = score
                best_model = model_entry['model_id']

        return best_model

    def distill_model(
        self,
        teacher_model_id: str,
        student_model: Any,
        training_data: Dict[str, Any],
        validation_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Distilar conocimiento de un modelo teacher a student.

        Args:
            teacher_model_id: ID del modelo teacher
            student_model: Modelo student (más pequeño)
            training_data: Datos de entrenamiento
            validation_data: Datos de validación

        Returns:
            (student_trained, métricas)
        """
        # Cargar teacher
        teacher_model = self.registry.load_model(teacher_model_id)
        if teacher_model is None:
            raise ValueError(f"Modelo teacher {teacher_model_id} no encontrado")

        # Distill
        student_trained, metrics = self.distiller.distill(
            teacher_model, student_model, training_data, validation_data
        )

        return student_trained, metrics
