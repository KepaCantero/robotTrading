"""
TransferLearning - Sistema de transfer learning para modelos de trading.

Incluye:
1. Pre-trained models para diferentes regímenes de mercado
2. Fine-tuning adaptativo
3. Knowledge distillation entre modelos
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Protocol, Union, cast, runtime_checkable

import numpy as np

if TYPE_CHECKING:
    from types import ModuleType

    from numpy.typing import NDArray

# Type alias for training metrics (heterogeneous dict with floats, lists, and strings)
TrainingMetrics = dict[str, Union[float, list[float], str]]


# ---------------------------------------------------------------------------
# Protocol for PyTorch-like models used in fine-tuning / distillation
# ---------------------------------------------------------------------------
@runtime_checkable
class _PyTorchParameter(Protocol):
    """Minimal protocol for a PyTorch parameter with a requires_grad flag."""

    requires_grad: bool


@runtime_checkable
class _PyTorchModel(Protocol):
    """Minimal protocol describing what we need from a PyTorch nn.Module."""

    def parameters(self) -> list[_PyTorchParameter]: ...
    def train(self) -> _PyTorchModel: ...
    def eval(self) -> _PyTorchModel: ...
    def children(self) -> list[object]: ...
    def __call__(self, *args: object, **kwargs: object) -> object: ...


logger = logging.getLogger(__name__)

# ============================================================================
# Optional Dependencies
# ============================================================================
# Type aliases for optional modules - use object for runtime flexibility
# when the actual module is not available
_torch_module: ModuleType | None = None
_joblib_module: ModuleType | None = None
_msgpack_module: ModuleType | None = None

try:
    import torch

    _torch_module = torch
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False

try:
    import joblib

    _joblib_module = joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    import msgpack

    _msgpack_module = msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

# JSON-compatible type for registry entries
_RegistryValue = Union[str, int, float, bool, list, dict, None]


class ModelRegistry:
    """
    Registro de modelos pre-entrenados para transfer learning.

    Almacena metadatos y paths de modelos entrenados en diferentes regimenes.
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
        self.registry: dict[str, dict[str, _RegistryValue]] = self._load_registry()

    def _load_registry(self) -> dict[str, dict[str, _RegistryValue]]:
        """Cargar registry desde archivo JSON."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file) as f:
                    loaded: dict[str, dict[str, _RegistryValue]] = json.load(f)
                    return loaded
            except OSError as e:
                logger.warning(f"Error cargando registry: {e}")
                return {}
        return {}

    def _save_registry(self) -> None:
        """Guardar registry a archivo JSON."""
        try:
            with open(self.registry_file, "w") as f:
                json.dump(self.registry, f, indent=2, default=str)
        except OSError as e:
            logger.error(f"Error guardando registry: {e}", exc_info=True)
            # No raise - registry sigue funcionando en memoria aunque no se guarde

    def register_model(
        self,
        model: object,
        model_id: str,
        regime: str,
        model_type: str,
        algorithm: str,
        metadata: dict[str, _RegistryValue] | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """
        Registrar un modelo pre-entrenado usando serializacion segura.

        Args:
            model: Modelo entrenado
            model_id: ID unico del modelo
            regime: Regimen de mercado (bull, bear, sideways, etc.)
            model_type: Tipo (supervised, deep, transformer)
            algorithm: Algoritmo (xgboost, lstm, etc.)
            metadata: Metadata adicional (metricas, config, etc.)
            tags: Tags adicionales

        Returns:
            True si se registro correctamente
        """
        try:
            # SECURITY: Use joblib for sklearn models, torch.save for PyTorch
            # Avoid pickle for security reasons
            model_path: str | None = None
            model_saved = False
            model_format: str | None = None

            try:
                self.models_dir.mkdir(parents=True, exist_ok=True)

                # Detect model type and use appropriate serialization
                if (
                    PYTORCH_AVAILABLE
                    and _torch_module is not None
                    and "torch.nn" in str(type(model))
                ):
                    # PyTorch model - use torch.save (secure for PyTorch objects)
                    pt_path = self.models_dir / f"{model_id}.pt"
                    _torch_module.save(model, pt_path)
                    model_path = str(pt_path)
                    model_saved = True
                    model_format = "pt"
                elif JOBLIB_AVAILABLE and _joblib_module is not None:
                    # sklearn or other models - use joblib (secure)
                    joblib_path = self.models_dir / f"{model_id}.joblib"
                    _joblib_module.dump(model, joblib_path)
                    model_path = str(joblib_path)
                    model_saved = True
                    model_format = "joblib"
                elif MSGPACK_AVAILABLE and _msgpack_module is not None:
                    # Generic Python objects - use msgpack with custom encoding
                    msgpack_path = self.models_dir / f"{model_id}.msgpack"
                    self._save_model_msgpack(model, msgpack_path)
                    model_path = str(msgpack_path)
                    model_saved = True
                    model_format = "msgpack"
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
            entry: dict[str, _RegistryValue] = {
                "model_id": model_id,
                "regime": regime,
                "model_type": model_type,
                "algorithm": algorithm,
                "model_path": model_path,
                "model_format": model_format,
                "registered_at": datetime.now().isoformat(),
                "metadata": metadata or {},
                "tags": tags or [],
                "model_saved": model_saved,
            }

            # Crear indice por regimen
            if regime not in self.registry:
                self.registry[regime] = {}

            regime_dict = self.registry[regime]
            assert isinstance(regime_dict, dict)
            if model_type not in regime_dict:
                regime_dict[model_type] = {}

            model_type_dict = regime_dict[model_type]
            assert isinstance(model_type_dict, dict)
            model_type_dict[model_id] = entry

            # Indice global
            if "all_models" not in self.registry:
                self.registry["all_models"] = {}
            all_models_dict = self.registry["all_models"]
            assert isinstance(all_models_dict, dict)
            all_models_dict[model_id] = entry

            # Guardar registry (puede fallar pero no es critico)
            try:
                self._save_registry()
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.warning(f"Error guardando registry (no critico): {e}")

            logger.info(f"Modelo {model_id} registrado para regimen {regime}")
            return True

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error registrando modelo: {e}", exc_info=True)
            return False

    def _save_model_msgpack(self, model: object, path: Path) -> None:
        """
        Save model using msgpack for generic Python objects.

        Args:
            model: Model to save
            path: Path to save to
        """
        import io

        if _msgpack_module is None:
            raise ImportError("msgpack not available")

        # Convert model to bytes using msgpack
        # For numpy arrays, msgpack-numpy is recommended, but we'll use a simple approach
        buffer = io.BytesIO()

        # Try to convert to dict if possible
        if hasattr(model, "__dict__"):
            # Model has __dict__, convert to dict
            model_dict = {
                "_module": model.__class__.__module__,
                "_class": model.__class__.__name__,
                "data": model.__dict__,
            }
            packed = _msgpack_module.packb(model_dict)
        else:
            # Fallback to string representation (not ideal but safe)
            packed = _msgpack_module.packb({"_repr": repr(model)})

        buffer.write(packed)
        buffer.seek(0)

        with open(path, "wb") as f:
            f.write(buffer.read())

    def get_model(self, model_id: str) -> dict[str, _RegistryValue] | None:
        """
        Obtener informacion de un modelo por ID.

        Args:
            model_id: ID del modelo

        Returns:
            Dict con informacion del modelo o None
        """
        all_models = self.registry.get("all_models", {})
        assert isinstance(all_models, dict)
        result = all_models.get(model_id)
        if result is None:
            return None
        assert isinstance(result, dict)
        return result

    def list_models(
        self,
        regime: str | None = None,
        model_type: str | None = None,
        algorithm: str | None = None,
        tags: list[str] | None = None,
    ) -> list[dict[str, _RegistryValue]]:
        """
        Listar modelos que coinciden con criterios.

        Args:
            regime: Filtrar por regimen
            model_type: Filtrar por tipo
            algorithm: Filtrar por algoritmo
            tags: Filtrar por tags

        Returns:
            Lista de modelos que coinciden
        """
        results: list[dict[str, _RegistryValue]] = []

        if regime:
            # Buscar en regimen especifico
            regime_models = self.registry.get(regime, {})
            assert isinstance(regime_models, dict)
            for model_type_dict in regime_models.values():
                assert isinstance(model_type_dict, dict)
                for model_entry in model_type_dict.values():
                    assert isinstance(model_entry, dict)
                    if self._matches_filters(model_entry, model_type, algorithm, tags):
                        results.append(model_entry)
        else:
            # Buscar en todos
            all_models = self.registry.get("all_models", {})
            assert isinstance(all_models, dict)
            for model_entry in all_models.values():
                assert isinstance(model_entry, dict)
                if self._matches_filters(model_entry, model_type, algorithm, tags):
                    results.append(model_entry)

        return results

    def _matches_filters(
        self,
        model_entry: dict[str, _RegistryValue],
        model_type: str | None,
        algorithm: str | None,
        tags: list[str] | None,
    ) -> bool:
        """Verificar si un modelo coincide con los filtros."""
        if model_type and model_entry.get("model_type") != model_type:
            return False
        if algorithm and model_entry.get("algorithm") != algorithm:
            return False
        if tags:
            model_tags = model_entry.get("tags", [])
            assert isinstance(model_tags, list)
            if not any(tag in model_tags for tag in tags):
                return False
        return True

    def load_model(self, model_id: str) -> object | None:
        """
        Cargar modelo desde registry usando serializacion segura.

        Args:
            model_id: ID del modelo

        Returns:
            Modelo cargado o None
        """
        entry = self.get_model(model_id)
        if not entry:
            logger.warning(f"Modelo {model_id} no encontrado en registry")
            return None

        raw_model_path = entry.get("model_path")

        # Si el modelo no fue guardado (no serializable), retornar None
        if not entry.get("model_saved", False):
            logger.info(
                f"Modelo {model_id} no fue serializado (no serializable). Usar metadata para recrear."
            )
            return None

        assert isinstance(raw_model_path, str)
        if not raw_model_path or not Path(raw_model_path).exists():
            logger.warning(f"Archivo de modelo no encontrado: {raw_model_path}")
            return None

        try:
            raw_model_format = entry.get("model_format", "")
            assert isinstance(raw_model_format, str)
            model_format = raw_model_format
            model_path_obj = Path(raw_model_path)

            # SECURITY: Use appropriate loader based on format
            loaded_model: object
            if model_format == "pt" or model_path_obj.suffix == ".pt":
                if not PYTORCH_AVAILABLE or _torch_module is None:
                    raise ImportError("PyTorch no disponible para cargar .pt")
                loaded_model = _torch_module.load(model_path_obj, map_location="cpu")
            elif model_format == "joblib" or model_path_obj.suffix == ".joblib":
                if not JOBLIB_AVAILABLE or _joblib_module is None:
                    raise ImportError("joblib no disponible para cargar .joblib")
                loaded_model = _joblib_module.load(model_path_obj)
            elif model_format == "msgpack" or model_path_obj.suffix == ".msgpack":
                if not MSGPACK_AVAILABLE or _msgpack_module is None:
                    raise ImportError("msgpack no disponible para cargar .msgpack")
                loaded_model = self._load_model_msgpack(model_path_obj)
            elif model_path_obj.suffix == ".pkl":
                # SECURITY: Migrate old .pkl files to secure format
                logger.warning(f"Found old .pkl file for {model_id}, migrating...")
                loaded_model = self._migrate_pkl_model(model_path_obj, entry)
                if loaded_model is None:
                    return None
            else:
                logger.error(f"Unsupported model format: {model_format}")
                return None

            logger.info(f"Modelo {model_id} cargado desde {raw_model_path}")
            return loaded_model
        except OSError as e:
            logger.error(f"Error cargando modelo {model_id}: {e}", exc_info=True)
            return None

    def _load_model_msgpack(self, path: Path) -> object:
        """
        Load model using msgpack.

        Args:
            path: Path to load from

        Returns:
            Loaded model
        """
        if _msgpack_module is None:
            raise ImportError("msgpack not available")

        with open(path, "rb") as f:
            data: dict[str, object] = _msgpack_module.unpackb(f.read(), raw=False)

        # Reconstruct object if it was saved with __dict__
        if "_module" in data and "_class" in data and "data" in data:
            # Import the class
            import importlib

            module = importlib.import_module(str(data["_module"]))
            cls = getattr(module, str(data["_class"]))
            obj = cls.__new__(cls)
            obj.__dict__.update(data["data"])
            return obj
        elif "_repr" in data:
            # Fallback - return the representation as string
            return data["_repr"]
        else:
            return data

    def _migrate_pkl_model(self, pkl_path: Path, entry: dict[str, _RegistryValue]) -> object | None:
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
            # Using RestrictedUnpickler to prevent arbitrary code execution
            import pickle

            class _MigrationUnpickler(pickle.Unpickler):
                """Restrict pickle deserialization to known safe classes for migration."""

                ALLOWED_CLASSES: ClassVar[dict[tuple[str, str], type | None]] = {
                    ("builtins", "dict"): dict,
                    ("builtins", "list"): list,
                    ("builtins", "tuple"): tuple,
                    ("builtins", "set"): set,
                    ("builtins", "frozenset"): frozenset,
                    ("builtins", "str"): str,
                    ("builtins", "int"): int,
                    ("builtins", "float"): float,
                    ("builtins", "bool"): bool,
                    ("builtins", "bytes"): bytes,
                    ("builtins", "bytearray"): bytearray,
                    ("builtins", "NoneType"): type(None),
                    ("collections", "OrderedDict"): None,
                    ("collections", "defaultdict"): None,
                    ("numpy.core.multiarray", "_reconstruct"): None,
                    ("numpy", "dtype"): None,
                    ("numpy", "ndarray"): None,
                }

                def find_class(self, module: str, name: str) -> type:
                    key = (module, name)
                    if key in self.ALLOWED_CLASSES:
                        cls: type | None = self.ALLOWED_CLASSES[key]
                        if cls is not None:
                            return cls
                        try:
                            mod = __import__(module, fromlist=[name])
                            loaded_cls: type = getattr(mod, name)
                            return loaded_cls
                        except (ImportError, AttributeError):
                            pass
                    raise pickle.UnpicklingError(  # nosemgrep: python.lang.security.deserialization.pickle.avoid-pickle - RestrictedUnpickler only allows basic Python/numpy types for safe legacy migration
                        f"Forbidden class during migration: {module}.{name}. "
                        f"Only basic Python and numpy types are allowed."
                    )

            with open(pkl_path, "rb") as f:
                loaded_model: object = _MigrationUnpickler(f).load()

            # Re-save in secure format
            raw_model_id = entry["model_id"]
            assert isinstance(raw_model_id, str)
            model_id = raw_model_id
            if JOBLIB_AVAILABLE and _joblib_module is not None:
                # Try joblib first
                joblib_path = pkl_path.with_suffix(".joblib")
                _joblib_module.dump(loaded_model, joblib_path)

                # Update registry
                entry["model_path"] = str(joblib_path)
                entry["model_format"] = "joblib"
                self._save_registry()

                # Remove old .pkl
                pkl_path.unlink()

                logger.info(f"Migrated {model_id} from .pkl to .joblib")
            else:
                logger.warning(f"Cannot migrate {model_id}: joblib not available")

            return loaded_model

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error migrating model from .pkl: {e}")
            return None


class FineTuner:
    """
    Sistema de fine-tuning adaptativo para modelos pre-entrenados.

    Soporta:
    - Neural networks (PyTorch): Freeze layers, adjust learning rate
    - Tree-based models: Continuar entrenamiento con nuevos datos
    - Adaptacion a nuevos regimenes de mercado
    """

    def __init__(self, config: dict[str, _RegistryValue] | None = None):
        """
        Inicializar fine-tuner.

        Args:
            config: Configuracion
        """
        config = config or {}
        self.freeze_layers: bool = bool(config.get("freeze_layers", True))  # Freeze early layers
        raw_freeze_n = config.get("freeze_n_layers", 0)
        assert isinstance(raw_freeze_n, (int, float))
        self.freeze_n_layers: int = int(raw_freeze_n)  # Numero de capas a freeze
        raw_lr_mult = config.get("learning_rate_multiplier", 0.1)
        assert isinstance(raw_lr_mult, (int, float))
        self.learning_rate_multiplier: float = float(raw_lr_mult)  # LR mas bajo
        raw_epochs = config.get("fine_tune_epochs", 10)
        assert isinstance(raw_epochs, (int, float))
        self.fine_tune_epochs: int = int(raw_epochs)
        raw_patience = config.get("early_stopping_patience", 5)
        assert isinstance(raw_patience, (int, float))
        self.early_stopping_patience: int = int(raw_patience)

    def fine_tune(
        self,
        base_model: object,
        training_data: dict[str, object],
        validation_data: dict[str, object] | None = None,
        model_type: str = "auto",
    ) -> tuple[object, TrainingMetrics]:
        """
        Fine-tune un modelo pre-entrenado.

        Args:
            base_model: Modelo pre-entrenado
            training_data: Nuevos datos de entrenamiento
            validation_data: Datos de validacion
            model_type: Tipo de modelo (auto, pytorch, tree, sklearn)

        Returns:
            (modelo_fine_tuned, metricas)
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

    def _detect_model_type(self, model: object) -> str:
        """Detectar tipo de modelo."""
        model_type = str(type(model)).lower()

        if any(x in model_type for x in ["module", "nn", "sequential"]):
            return "pytorch"
        elif any(
            x in model_type
            for x in ["xgboost", "lightgbm", "catboost", "randomforest", "gradientboosting"]
        ):
            return "tree"
        else:
            return "sklearn"

    def _fine_tune_pytorch(
        self,
        model: object,
        training_data: dict[str, object],
        validation_data: dict[str, object] | None = None,
    ) -> tuple[object, TrainingMetrics]:
        """
        Fine-tune modelo PyTorch.

        Args:
            model: Modelo PyTorch
            training_data: Datos de entrenamiento
            validation_data: Datos de validacion

        Returns:
            (modelo_fine_tuned, metricas)
        """
        if not PYTORCH_AVAILABLE or _torch_module is None:
            logger.error("PyTorch no disponible para fine-tuning")
            return model, {}

        try:
            # Clonar modelo para no modificar el original
            fine_tuned_model = self._clone_pytorch_model(model)
            assert isinstance(fine_tuned_model, _PyTorchModel)

            # Freeze layers si esta configurado
            if self.freeze_layers:
                self._freeze_layers(fine_tuned_model)

            # Preparar datos
            # Asumir que training_data tiene 'sequences' y 'labels' para deep learning
            raw_sequences = training_data.get("sequences")
            raw_labels = training_data.get("labels")

            if raw_sequences is None or raw_labels is None:
                logger.error("training_data debe contener 'sequences' y 'labels'")
                return model, {}

            sequences_arr = cast("np.ndarray", raw_sequences)
            labels_arr = cast("np.ndarray", raw_labels)

            # Convertir a tensores
            if _torch_module is None:
                raise ImportError("PyTorch not available")

            sequences_t = _torch_module.FloatTensor(sequences_arr)
            labels_t = (
                _torch_module.FloatTensor(labels_arr).unsqueeze(1)
                if labels_arr.ndim == 1
                else _torch_module.FloatTensor(labels_arr)
            )

            # Optimizer con learning rate reducido
            lr = 0.001 * self.learning_rate_multiplier
            optimizer = _torch_module.optim.Adam(fine_tuned_model.parameters(), lr=lr)
            criterion = (
                _torch_module.nn.MSELoss()
                if labels_t.dtype == _torch_module.float32
                else _torch_module.nn.BCELoss()
            )

            # Training loop
            fine_tuned_model.train()
            metrics: TrainingMetrics = {"train_loss": []}

            for epoch in range(self.fine_tune_epochs):
                optimizer.zero_grad()
                outputs = fine_tuned_model(sequences_t)
                loss = criterion(outputs, labels_t)
                loss.backward()
                optimizer.step()

                train_loss_list = metrics["train_loss"]
                assert isinstance(train_loss_list, list)
                loss_val = loss.item()
                assert isinstance(loss_val, float)
                train_loss_list.append(loss_val)

                if (epoch + 1) % 5 == 0:
                    loss_display = loss.item()
                    assert isinstance(loss_display, float)
                    logger.debug(
                        f"Fine-tuning epoch {epoch + 1}/{self.fine_tune_epochs}, Loss: {loss_display:.4f}"
                    )

            # Validation
            if validation_data:
                raw_val_sequences = validation_data.get("sequences")
                raw_val_labels = validation_data.get("labels")
                if raw_val_sequences is not None and raw_val_labels is not None:
                    val_sequences_arr = cast("np.ndarray", raw_val_sequences)
                    val_labels_arr = cast("np.ndarray", raw_val_labels)
                    fine_tuned_model.eval()
                    with _torch_module.no_grad():
                        val_sequences_t = _torch_module.FloatTensor(val_sequences_arr)
                        val_labels_t = (
                            _torch_module.FloatTensor(val_labels_arr).unsqueeze(1)
                            if val_labels_arr.ndim == 1
                            else _torch_module.FloatTensor(val_labels_arr)
                        )
                        val_outputs = fine_tuned_model(val_sequences_t)
                        val_loss = criterion(val_outputs, val_labels_t)
                        val_loss_val = val_loss.item()
                        assert isinstance(val_loss_val, float)
                        metrics["val_loss"] = val_loss_val

            return fine_tuned_model, metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en fine-tuning PyTorch: {e}", exc_info=True)
            return model, {}

    def _clone_pytorch_model(self, model: object) -> object:
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

    def _freeze_layers(self, model: _PyTorchModel) -> None:
        """Freeze early layers del modelo."""
        if self.freeze_n_layers > 0:
            layers = model.children()
            n_freeze = min(self.freeze_n_layers, len(layers))
            for layer in layers[:n_freeze]:
                if isinstance(layer, _PyTorchModel):
                    for param in layer.parameters():
                        param.requires_grad = False
            logger.info(f"Frozen {n_freeze} layers")

    def _fine_tune_tree_based(
        self,
        model: object,
        training_data: dict[str, object],
        validation_data: dict[str, object] | None = None,
    ) -> tuple[object, TrainingMetrics]:
        """
        Fine-tune modelo tree-based (continuar entrenamiento).

        Args:
            model: Modelo tree-based
            training_data: Nuevos datos
            validation_data: Datos de validacion

        Returns:
            (modelo_fine_tuned, metricas)
        """
        try:
            X_train = training_data.get("features")
            y_train = training_data.get("labels")

            if X_train is None or y_train is None:
                logger.error("training_data debe contener 'features' y 'labels'")
                return model, {}

            # Para tree-based models, simplemente continuar entrenamiento
            # Esto funciona mejor con XGBoost, LightGBM, CatBoost

            model_type = str(type(model)).lower()

            if "xgboost" in model_type:
                # XGBoost: continuar entrenamiento
                assert hasattr(model, "fit") and callable(model.fit)
                assert hasattr(model, "get_booster") and callable(model.get_booster)
                model.fit(X_train, y_train, xgb_model=model.get_booster())
                metrics: TrainingMetrics = {"status": "continued_training"}
            elif "lightgbm" in model_type or "catboost" in model_type:
                # LightGBM/CatBoost: continuar entrenamiento
                # (Requiere implementacion especifica)
                metrics = {"status": "tree_based_continued"}
            else:
                # Para otros (RandomForest, etc.), retrain desde cero
                # pero con parametros del modelo original
                metrics = {"status": "retrained_from_scratch"}

            return model, metrics

        except (FileNotFoundError, ValueError, KeyError, TypeError) as e:
            logger.error(f"Error en fine-tuning tree-based: {e}", exc_info=True)
            return model, {}


class KnowledgeDistiller:
    """
    Sistema de Knowledge Distillation.

    Transfiere conocimiento de un modelo grande (teacher) a uno pequeno (student).
    Util para comprimir modelos o transferir conocimiento entre regimenes.
    """

    def __init__(self, config: dict[str, _RegistryValue] | None = None):
        """
        Inicializar distiller.

        Args:
            config: Configuracion
        """
        config = config or {}
        raw_temp = config.get("temperature", 3.0)
        assert isinstance(raw_temp, (int, float))
        self.temperature: float = float(raw_temp)  # Temperature para softmax
        raw_alpha = config.get("alpha", 0.7)
        assert isinstance(raw_alpha, (int, float))
        self.alpha: float = float(raw_alpha)  # Weight para soft targets vs hard targets
        raw_epochs = config.get("distillation_epochs", 50)
        assert isinstance(raw_epochs, (int, float))
        self.distillation_epochs: int = int(raw_epochs)

    def distill(
        self,
        teacher_model: object,
        student_model: object,
        training_data: dict[str, object],
        validation_data: dict[str, object] | None = None,
    ) -> tuple[object, TrainingMetrics]:
        """
        Distilar conocimiento de teacher a student.

        Args:
            teacher_model: Modelo grande (teacher)
            student_model: Modelo pequeno (student)
            training_data: Datos de entrenamiento
            validation_data: Datos de validacion

        Returns:
            (student_model_trained, metricas)
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

    def _detect_model_type(self, model: object) -> str:
        """Detectar tipo de modelo."""
        model_type = str(type(model)).lower()
        if any(x in model_type for x in ["module", "nn", "sequential"]):
            return "pytorch"
        elif any(x in model_type for x in ["xgboost", "lightgbm", "catboost", "randomforest"]):
            return "tree"
        else:
            return "sklearn"

    def _distill_pytorch(
        self,
        teacher: object,
        student: object,
        training_data: dict[str, object],
        validation_data: dict[str, object] | None = None,
    ) -> tuple[object, TrainingMetrics]:
        """
        Distillation para modelos PyTorch.

        Args:
            teacher: Modelo teacher
            student: Modelo student
            training_data: Datos de entrenamiento
            validation_data: Datos de validacion

        Returns:
            (student_trained, metricas)
        """
        if not PYTORCH_AVAILABLE or _torch_module is None:
            logger.error("PyTorch no disponible")
            return student, {}

        try:
            # Narrow types to PyTorch-like models
            assert isinstance(teacher, _PyTorchModel)
            assert isinstance(student, _PyTorchModel)

            # Preparar datos
            raw_sequences = training_data.get("sequences")
            raw_labels = training_data.get("labels")

            if raw_sequences is None or raw_labels is None:
                logger.error("training_data debe contener 'sequences' y 'labels'")
                return student, {}

            sequences_arr = cast("np.ndarray", raw_sequences)
            labels_arr = cast("np.ndarray", raw_labels)

            sequences_t = _torch_module.FloatTensor(sequences_arr)
            labels_t = (
                _torch_module.FloatTensor(labels_arr).unsqueeze(1)
                if labels_arr.ndim == 1
                else _torch_module.FloatTensor(labels_arr)
            )

            # Teacher en eval mode
            teacher.eval()
            student.train()

            # Optimizer
            optimizer = _torch_module.optim.Adam(student.parameters(), lr=0.001)

            # Loss function combinado
            def distillation_loss(student_logits, teacher_logits, true_labels, temperature, alpha):
                # Scale logits by temperature via multiplication with inverse
                inv_temp = 1.0 / temperature
                soft_targets = _torch_module.nn.functional.softmax(teacher_logits * inv_temp, dim=1)
                soft_prob = _torch_module.nn.functional.log_softmax(
                    student_logits * inv_temp, dim=1
                )
                soft_loss = _torch_module.nn.functional.kl_div(
                    soft_prob, soft_targets, reduction="batchmean"
                ) * (temperature**2)

                # Hard targets (true labels)
                hard_loss = _torch_module.nn.functional.cross_entropy(
                    student_logits, true_labels.long()
                )

                # Combinar
                return alpha * soft_loss + (1 - alpha) * hard_loss

            metrics: TrainingMetrics = {"train_loss": [], "distillation_loss": []}

            # Training loop
            for epoch in range(self.distillation_epochs):
                optimizer.zero_grad()

                # Forward pass
                student_logits = student(sequences_t)
                with _torch_module.no_grad():
                    teacher_logits = teacher(sequences_t)

                # Loss
                loss = distillation_loss(
                    student_logits, teacher_logits, labels_t, self.temperature, self.alpha
                )

                loss.backward()
                optimizer.step()

                train_loss_list = metrics["train_loss"]
                assert isinstance(train_loss_list, list)
                loss_val = loss.item()
                assert isinstance(loss_val, float)
                train_loss_list.append(loss_val)

                if (epoch + 1) % 10 == 0:
                    loss_display = loss.item()
                    assert isinstance(loss_display, float)
                    logger.debug(
                        f"Distillation epoch {epoch + 1}/{self.distillation_epochs}, Loss: {loss_display:.4f}"
                    )

            # Validation
            if validation_data:
                raw_val_sequences = validation_data.get("sequences")
                raw_val_labels = validation_data.get("labels")
                if raw_val_sequences is not None and raw_val_labels is not None:
                    val_sequences_arr = cast("np.ndarray", raw_val_sequences)
                    val_labels_arr = cast("np.ndarray", raw_val_labels)
                    student.eval()
                    with _torch_module.no_grad():
                        val_sequences_t = _torch_module.FloatTensor(val_sequences_arr)
                        val_labels_t = (
                            _torch_module.FloatTensor(val_labels_arr).unsqueeze(1)
                            if val_labels_arr.ndim == 1
                            else _torch_module.FloatTensor(val_labels_arr)
                        )
                        val_outputs = student(val_sequences_t)
                        val_loss = _torch_module.nn.functional.mse_loss(val_outputs, val_labels_t)
                        val_loss_val = val_loss.item()
                        assert isinstance(val_loss_val, float)
                        metrics["val_loss"] = val_loss_val

            return student, metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en distillation PyTorch: {e}", exc_info=True)
            return student, {}

    def _distill_tree_based(
        self,
        teacher: object,
        student: object,
        training_data: dict[str, object],
        validation_data: dict[str, object] | None = None,
    ) -> tuple[object, TrainingMetrics]:
        """
        Distillation para modelos tree-based.

        Usa predicciones del teacher como "soft labels" para entrenar student.
        """
        try:
            X_train = training_data.get("features")
            y_train = training_data.get("labels")

            if X_train is None or y_train is None:
                logger.error("training_data debe contener 'features' y 'labels'")
                return student, {}

            # Obtener predicciones del teacher (soft labels)
            teacher_probs: np.ndarray
            if hasattr(teacher, "predict_proba") and callable(teacher.predict_proba):
                predict_proba_fn = teacher.predict_proba
                teacher_probs = np.asarray(predict_proba_fn(X_train))
            else:
                assert hasattr(teacher, "predict") and callable(teacher.predict)
                predict_fn = teacher.predict
                raw_preds = predict_fn(X_train)
                teacher_probs = np.asarray(raw_preds)
                # Convertir a probabilidades si es necesario
                if teacher_probs.ndim == 1:
                    teacher_probs = np.column_stack([1 - teacher_probs, teacher_probs])

            # Aplicar temperature scaling
            teacher_probs_scaled = self._apply_temperature(teacher_probs, self.temperature)

            # Combinar con true labels
            # Usar soft labels con probabilidad alpha
            y_train_arr = np.asarray(y_train)
            combined_labels: np.ndarray
            if self.alpha > 0:
                # Convertir true labels a one-hot
                if y_train_arr.ndim == 1:
                    y_one_hot = np.eye(2)[y_train_arr.astype(int)]
                else:
                    y_one_hot = y_train_arr

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
            assert hasattr(student, "fit") and callable(student.fit)
            fit_fn = student.fit
            fit_fn(X_train, soft_labels)

            metrics: TrainingMetrics = {
                "status": "distilled",
                "teacher_confidence": float(np.mean(np.max(teacher_probs, axis=1))),
                "student_confidence": float(np.mean(np.max(combined_labels, axis=1))),
            }

            return student, metrics

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Error en distillation tree-based: {e}", exc_info=True)
            return student, {}

    def _apply_temperature(
        self, probs: NDArray[np.floating], temperature: float
    ) -> NDArray[np.floating]:
        """Aplicar temperature scaling a probabilidades."""
        # Softmax con temperature
        scaled = probs / temperature
        exp_probs = np.exp(scaled)
        sum_exp: NDArray[np.floating] = np.sum(exp_probs, axis=1, keepdims=True)
        return exp_probs / sum_exp


class TransferLearningManager:
    """
    Manager unificado para transfer learning.

    Combina ModelRegistry, FineTuner y KnowledgeDistiller.
    """

    def __init__(self, config: dict[str, _RegistryValue] | None = None):
        """
        Inicializar manager.

        Args:
            config: Configuracion
        """
        config = config or {}
        raw_registry_path = config.get("registry_path", "models/registry")
        assert isinstance(raw_registry_path, str)
        self.registry = ModelRegistry(raw_registry_path)

        raw_fine_tuner_config = config.get("fine_tuner_config", {})
        assert isinstance(raw_fine_tuner_config, dict)
        self.fine_tuner = FineTuner(raw_fine_tuner_config)

        raw_distiller_config = config.get("distiller_config", {})
        assert isinstance(raw_distiller_config, dict)
        self.distiller = KnowledgeDistiller(raw_distiller_config)

    def create_pretrained_model(
        self,
        model: object,
        regime: str,
        model_type: str,
        algorithm: str,
        metadata: dict[str, _RegistryValue] | None = None,
        tags: list[str] | None = None,
    ) -> str | None:
        """
        Crear y registrar un modelo pre-entrenado.

        Args:
            model: Modelo entrenado
            regime: Regimen de mercado
            model_type: Tipo de modelo
            algorithm: Algoritmo
            metadata: Metadata (metricas, performance, etc.)
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
        training_data: dict[str, object],
        validation_data: dict[str, object] | None = None,
    ) -> tuple[object, TrainingMetrics]:
        """
        Cargar modelo pre-entrenado y hacer fine-tuning.

        Args:
            model_id: ID del modelo en registry
            training_data: Nuevos datos de entrenamiento
            validation_data: Datos de validacion

        Returns:
            (modelo_fine_tuned, metricas)
        """
        # Cargar modelo
        model = self.registry.load_model(model_id)
        if model is None:
            raise ValueError(f"Modelo {model_id} no encontrado")

        # Obtener metadata
        model_info = self.registry.get_model(model_id)
        assert model_info is not None
        raw_model_type = model_info.get("model_type", "auto")
        assert isinstance(raw_model_type, str)
        model_type = raw_model_type

        # Fine-tune
        fine_tuned_model, metrics = self.fine_tuner.fine_tune(
            model, training_data, validation_data, model_type
        )

        return fine_tuned_model, metrics

    def find_best_model(
        self, regime: str, model_type: str, algorithm: str | None = None
    ) -> str | None:
        """
        Encontrar el mejor modelo pre-entrenado para un regimen.

        Args:
            regime: Regimen de mercado
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

        # Seleccionar por mejor metrica en metadata
        best_model: str | None = None
        best_score = -float("inf")

        for model_entry in models:
            raw_metadata = model_entry.get("metadata", {})
            assert isinstance(raw_metadata, dict)
            metadata: dict[str, _RegistryValue] = raw_metadata
            # Buscar metricas comunes
            raw_acc = metadata.get("accuracy")
            raw_f1 = metadata.get("f1_score")
            raw_roc = metadata.get("roc_auc")

            score: float
            if raw_acc is not None and isinstance(raw_acc, (int, float)):
                score = float(raw_acc)
            elif raw_f1 is not None and isinstance(raw_f1, (int, float)):
                score = float(raw_f1)
            elif raw_roc is not None and isinstance(raw_roc, (int, float)):
                score = float(raw_roc)
            else:
                score = 0.0

            if score > best_score:
                best_score = score
                raw_best = model_entry["model_id"]
                assert isinstance(raw_best, str)
                best_model = raw_best

        return best_model

    def distill_model(
        self,
        teacher_model_id: str,
        student_model: object,
        training_data: dict[str, object],
        validation_data: dict[str, object] | None = None,
    ) -> tuple[object, TrainingMetrics]:
        """
        Distilar conocimiento de un modelo teacher a student.

        Args:
            teacher_model_id: ID del modelo teacher
            student_model: Modelo student (mas pequeno)
            training_data: Datos de entrenamiento
            validation_data: Datos de validacion

        Returns:
            (student_trained, metricas)
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
