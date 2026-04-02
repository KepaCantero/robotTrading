"""
SubprocessLearningEngineWrapper - Wrapper to run learning engines in subprocess.

This solves the macOS mutex.cc blocking issue where PyTorch and stable-baselines3
cause deadlocks when used with multiprocessing's default 'spawn' start method.

The wrapper:
1. Detects if running on macOS
2. If macOS, runs heavy operations (train, predict) in a subprocess
3. Communicates results via multiprocessing.Queue

This allows Deep Learning, Transformer, and Reinforcement Learning engines
to work on macOS without blocking.

FIX: Added proper initialization handshake, config sanitization, and better
timeout handling to prevent hangs.
"""

from __future__ import annotations

import contextlib
import logging
import multiprocessing as mp
import platform
import traceback
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Engines that require subprocess mode (PyTorch-based)
PYTORCH_ENGINES = {"deep", "transformer", "reinforcement"}

# Engines that can run directly (scikit-learn based)
DIRECT_ENGINES = {"supervised"}


class EngineOperation(Enum):
    """Operations that can be performed on a learning engine."""

    TRAIN = "train"
    PREDICT = "predict"
    EVALUATE = "evaluate"
    LOAD_MODEL = "load_model"
    SAVE_MODEL = "save_model"


@dataclass
class SubprocessRequest:
    """Request to be sent to the subprocess."""

    operation: EngineOperation
    engine_type: str
    config: dict[str, Any]
    data: dict[str, Any] | None = None
    features: dict[str, Any] | None = None
    model_path: str | None = None


@dataclass
class SubprocessResponse:
    """Response from the subprocess."""

    success: bool
    result: Any | None = None
    error: str | None = None


def _worker_process(
    request_queue: mp.Queue,
    response_queue: mp.Queue,
    engine_type: str,
    config: dict[str, Any],
):
    """
    Worker process that handles learning engine operations.

    This process imports and uses PyTorch/stable-baselines3 safely,
    isolated from the main process.

    Args:
        request_queue: Queue to receive requests from main process
        response_queue: Queue to send responses to main process
        engine_type: Type of learning engine to create
        config: Configuration for the engine
    """
    engine = None

    try:
        # Set environment variables for single-threaded operation
        import os

        os.environ["MKL_NUM_THREADS"] = "1"
        os.environ["NUMEXPR_NUM_THREADS"] = "1"
        os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
        os.environ["OMP_NUM_THREADS"] = "1"
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

        # Import and create the appropriate engine
        if engine_type == "deep":
            from .deep_learning_engine import DeepLearningEngine

            engine = DeepLearningEngine(config)
        elif engine_type == "transformer":
            from .transformer_engine import TransformerEngine

            engine = TransformerEngine(config)
        elif engine_type == "reinforcement":
            from .reinforcement_learning_engine import ReinforcementLearningEngine

            engine = ReinforcementLearningEngine(config)
        else:
            response_queue.put(
                SubprocessResponse(
                    success=False,
                    error=f"Unknown engine type: {engine_type}",
                )
            )
            return

        # Send initialization success signal
        # Use None to indicate successful initialization
        response_queue.put(None)

        # Process requests
        while True:
            try:
                request = request_queue.get(timeout=300)  # 5 minute timeout

                if request is None:
                    # Shutdown signal
                    break

                if request.operation == EngineOperation.TRAIN:
                    result = engine.train(
                        training_data=request.data,
                        validation_data=(
                            request.data.get("validation_data") if request.data else None
                        ),
                    )
                    response_queue.put(SubprocessResponse(success=True, result=result))

                elif request.operation == EngineOperation.PREDICT:
                    result = engine.predict(request.features or {})
                    response_queue.put(SubprocessResponse(success=True, result=result))

                elif request.operation == EngineOperation.EVALUATE:
                    result = engine.evaluate(request.data or {})
                    response_queue.put(SubprocessResponse(success=True, result=result))

                elif request.operation == EngineOperation.LOAD_MODEL:
                    result = engine.load_model(request.model_path)
                    response_queue.put(SubprocessResponse(success=result, result=result))

                elif request.operation == EngineOperation.SAVE_MODEL:
                    result = engine.save_model(request.model_path)
                    response_queue.put(SubprocessResponse(success=result, result=result))

            except Exception as e:
                response_queue.put(SubprocessResponse(success=False, error=str(e)))

    except Exception as e:
        response_queue.put(
            SubprocessResponse(success=False, error=f"Worker initialization failed: {e}")
        )


class SubprocessLearningEngineWrapper:
    """
    Wrapper that runs a learning engine in a subprocess.

    This wrapper provides the same interface as BaseLearningEngine but
    executes operations in a separate process to avoid mutex blocking
    on macOS.
    """

    def __init__(
        self,
        engine_type: str,
        config: dict[str, Any],
    ):
        """
        Initialize the subprocess wrapper.

        Args:
            engine_type: Type of engine ('deep', 'transformer', 'reinforcement')
            config: Configuration for the engine
        """
        self.engine_type = engine_type
        self.config = config
        self.enabled = config.get("enabled", True)
        self.name = engine_type

        # Model path for load/save
        self.model_path = config.get("model_path", f"models/{engine_type}_model.pkl")
        self.is_trained = False

        # Subprocess management
        self._process: mp.process.BaseProcess | None = None
        self._request_queue: mp.Queue | None = None
        self._response_queue: mp.Queue | None = None

        # Check if we need subprocess mode
        self._use_subprocess = self._should_use_subprocess()

        if self._use_subprocess:
            logger.info(f"🚀 {engine_type}: Using subprocess mode for macOS compatibility")
        else:
            # Direct mode for non-macOS systems
            self._engine = self._create_engine_direct()
            if self._engine:
                logger.info(f"✅ {engine_type}: Using direct mode")

    def _should_use_subprocess(self) -> bool:
        """Determine if we should use subprocess mode."""
        # Only PyTorch-based engines need subprocess mode on macOS
        # Scikit-learn based engines (supervised) can run directly
        if self.engine_type in DIRECT_ENGINES:
            logger.debug(f"{self.engine_type}: Can run directly (scikit-learn based)")
            return False

        # Only use subprocess on macOS for PyTorch engines
        return bool(platform.system() == "Darwin" and self.engine_type in PYTORCH_ENGINES)

    def _sanitize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize config for subprocess serialization.

        Removes unpicklable objects like file handles, database connections, etc.
        """

        def _is_picklable(obj: object) -> bool:
            """Check if an object can be pickled."""
            try:
                import pickle

                pickle.dumps(
                    obj
                )  # nosemgrep: python.lang.security.deserialization.pickle.avoid-pickle - only used for picklability check, not deserialization of untrusted data
                return True
            except (TypeError, pickle.PicklingError, AttributeError):
                return False

        sanitized: dict[str, Any] = {}
        for key, value in config.items():
            # Skip keys that typically contain unpicklable objects
            if key in ("connection", "session", "db", "database", "engine", "pool"):
                continue

            # Check if value is picklable
            if isinstance(value, dict):
                sanitized[key] = self._sanitize_config(value)
            elif isinstance(value, (str, int, float, bool, type(None))):
                sanitized[key] = value
            elif isinstance(value, (list, tuple, set)):
                try:
                    # Try to pickle the value
                    import pickle

                    pickle.dumps(
                        value
                    )  # nosemgrep: python.lang.security.deserialization.pickle.avoid-pickle - only used for picklability check, not deserialization of untrusted data
                    sanitized[key] = value
                except (TypeError, pickle.PicklingError):
                    # Convert to string representation
                    sanitized[key] = str(value)
            elif _is_picklable(value):
                sanitized[key] = value
            else:
                # Skip unpicklable values
                logger.debug(f"Skipping unpicklable config key: {key}")
                continue

        return sanitized

    def _create_engine_direct(self) -> Any | None:
        """Create engine directly (for non-macOS systems)."""
        try:
            if self.engine_type == "deep":
                from .deep_learning_engine import DeepLearningEngine

                return DeepLearningEngine(self.config)
            elif self.engine_type == "transformer":
                from .transformer_engine import TransformerEngine

                return TransformerEngine(self.config)
            elif self.engine_type == "reinforcement":
                from .reinforcement_learning_engine import ReinforcementLearningEngine

                return ReinforcementLearningEngine(self.config)
            return None
        except ImportError as e:
            logger.warning(f"Could not create {self.engine_type} engine directly: {e}")
            return None

    def _start_subprocess(self) -> bool:
        """Start the worker subprocess."""
        if self._process is not None and self._process.is_alive():
            return True

        try:
            # Create queues
            self._request_queue = mp.Queue()
            self._response_queue = mp.Queue()

            # Sanitize config for subprocess serialization
            sanitized_config = self._sanitize_config(self.config)

            # Start process with 'spawn' method (required for macOS)
            ctx = mp.get_context("spawn")
            self._process = ctx.Process(
                target=_worker_process,
                args=(
                    self._request_queue,
                    self._response_queue,
                    self.engine_type,
                    sanitized_config,
                ),
                daemon=True,
            )
            self._process.start()

            # Wait for initialization with proper handshake
            # Worker sends INIT_SUCCESS on successful initialization
            try:
                response = self._response_queue.get(timeout=60)  # Increased timeout
                if response is None:
                    # None means successful initialization (worker sent None as success signal)
                    logger.info(f"✅ {self.engine_type}: Subprocess started successfully")
                    return True
                elif isinstance(response, SubprocessResponse):
                    if not response.success:
                        logger.error(f"Subprocess initialization failed: {response.error}")
                        self._cleanup_subprocess()
                        return False
                    else:
                        logger.info(f"✅ {self.engine_type}: Subprocess started successfully")
                        return True
                else:
                    # Unexpected response type - assume success
                    logger.info(f"✅ {self.engine_type}: Subprocess started (unconfirmed)")
                    return True

            except Exception as e:
                logger.warning(f"Subprocess initialization timeout or error: {e}")
                # Check if process is still alive - if so, it might be working
                if self._process.is_alive():
                    logger.info(f"✅ {self.engine_type}: Subprocess running (unconfirmed init)")
                    return True
                self._cleanup_subprocess()
                return False

        except Exception as e:
            logger.error(f"Failed to start subprocess: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def _cleanup_subprocess(self):
        """Clean up subprocess resources."""
        try:
            if self._process is not None:
                if self._process.is_alive():
                    self._process.terminate()
                    self._process.join(timeout=2)
                    if self._process.is_alive():
                        self._process.kill()
                self._process = None
        except Exception as e:
            logger.debug(f"Error cleaning up subprocess: {e}")

        with contextlib.suppress(Exception):
            if self._request_queue is not None:
                self._request_queue.close()
                self._request_queue = None

        with contextlib.suppress(Exception):
            if self._response_queue is not None:
                self._response_queue.close()
                self._response_queue = None

    def _send_request(self, request: SubprocessRequest) -> SubprocessResponse:
        """Send a request to the subprocess and wait for response."""
        if not self._use_subprocess:
            # Direct mode
            return self._handle_direct(request)

        if not self._start_subprocess():
            return SubprocessResponse(
                success=False,
                error="Failed to start subprocess",
            )

        try:
            self._request_queue.put(request)
            response = self._response_queue.get(timeout=120)  # 2 minute timeout
            return response
        except Exception as e:
            return SubprocessResponse(
                success=False,
                error=f"Communication error: {e}",
            )

    def _handle_direct(self, request: SubprocessRequest) -> SubprocessResponse:
        """Handle request directly without subprocess."""
        if self._engine is None:
            return SubprocessResponse(
                success=False,
                error="Engine not initialized",
            )

        try:
            if request.operation == EngineOperation.TRAIN:
                result = self._engine.train(
                    training_data=request.data,
                    validation_data=request.data.get("validation_data") if request.data else None,
                )
                if result:
                    self.is_trained = True
                return SubprocessResponse(success=True, result=result)

            elif request.operation == EngineOperation.PREDICT:
                result = self._engine.predict(request.features or {})
                return SubprocessResponse(success=True, result=result)

            elif request.operation == EngineOperation.EVALUATE:
                result = self._engine.evaluate(request.data or {})
                return SubprocessResponse(success=True, result=result)

            elif request.operation == EngineOperation.LOAD_MODEL:
                result = self._engine.load_model(request.model_path)
                if result:
                    self.is_trained = True
                return SubprocessResponse(success=result, result=result)

            elif request.operation == EngineOperation.SAVE_MODEL:
                result = self._engine.save_model(request.model_path)
                return SubprocessResponse(success=result, result=result)

            return SubprocessResponse(
                success=False,
                error=f"Unknown operation: {request.operation}",
            )

        except Exception as e:
            return SubprocessResponse(
                success=False,
                error=str(e),
            )

    def train(
        self,
        training_data: dict[str, Any] | None = None,
        validation_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Train the model.

        Args:
            training_data: Training data
            validation_data: Validation data

        Returns:
            Training metrics
        """
        data = training_data or {}
        if validation_data:
            data["validation_data"] = validation_data

        request = SubprocessRequest(
            operation=EngineOperation.TRAIN,
            engine_type=self.engine_type,
            config=self.config,
            data=data,
        )

        response = self._send_request(request)

        if response.success and response.result:
            self.is_trained = True
            return response.result

        logger.error(f"Training failed: {response.error}")
        return {"error": response.error or "Unknown error"}

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Generate predictions.

        Args:
            features: Input features

        Returns:
            Prediction result
        """
        request = SubprocessRequest(
            operation=EngineOperation.PREDICT,
            engine_type=self.engine_type,
            config=self.config,
            features=features,
        )

        response = self._send_request(request)

        if response.success:
            return response.result or {
                "success_probability": 0.5,
                "confidence": 0.0,
                "recommended_action": "HOLD",
            }

        logger.warning(f"Prediction failed: {response.error}")
        return {
            "success_probability": 0.5,
            "confidence": 0.0,
            "recommended_action": "HOLD",
            "error": response.error,
        }

    def evaluate(self, test_data: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate the model.

        Args:
            test_data: Test data

        Returns:
            Evaluation metrics
        """
        request = SubprocessRequest(
            operation=EngineOperation.EVALUATE,
            engine_type=self.engine_type,
            config=self.config,
            data=test_data,
        )

        response = self._send_request(request)

        if response.success:
            return response.result or {}

        return {"error": response.error or "Unknown error"}

    def load_model(self, path: str | None = None) -> bool:
        """
        Load a trained model.

        Args:
            path: Model path

        Returns:
            True if successful
        """
        request = SubprocessRequest(
            operation=EngineOperation.LOAD_MODEL,
            engine_type=self.engine_type,
            config=self.config,
            model_path=path or self.model_path,
        )

        response = self._send_request(request)

        if response.success:
            self.is_trained = True
            return True

        return False

    def save_model(self, path: str | None = None) -> bool:
        """
        Save the trained model.

        Args:
            path: Model path

        Returns:
            True if successful
        """
        request = SubprocessRequest(
            operation=EngineOperation.SAVE_MODEL,
            engine_type=self.engine_type,
            config=self.config,
            model_path=path or self.model_path,
        )

        response = self._send_request(request)
        return response.success

    def is_ready(self) -> bool:
        """Check if the engine is ready to use."""
        return self.enabled and self.is_trained

    def explain(self, features: dict[str, Any], prediction: dict[str, Any] | None = None) -> str:
        """Generate explanation for prediction."""
        if prediction is None:
            prediction = self.predict(features)

        action = prediction.get("recommended_action", "HOLD")
        confidence = prediction.get("confidence", 0.0)
        prob = prediction.get("success_probability", 0.0)

        return (
            f"Action: {action}. "
            f"Success probability: {prob:.2%}, "
            f"Confidence: {confidence:.2%}. "
            f"(Engine: {self.engine_type}, Mode: {'subprocess' if self._use_subprocess else 'direct'})"
        )

    def shutdown(self):
        """Shutdown the subprocess."""
        try:
            if (
                self._process is not None
                and self._process.is_alive()
                and self._request_queue is not None
            ):
                self._request_queue.put(None)
                self._process.join(timeout=5)
            self._cleanup_subprocess()
        except Exception as e:
            logger.debug(f"Error during shutdown: {e}")

    def __del__(self):
        """Cleanup on destruction."""
        with contextlib.suppress(Exception):
            self.shutdown()
