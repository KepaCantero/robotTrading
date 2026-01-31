"""
Error Handling and Retry Logic for Backtesting Operations.

This module provides robust error handling with automatic retries for
transient failures, especially those related to threading/locking issues
in machine learning libraries.
"""

from __future__ import annotations

import logging
import multiprocessing
from multiprocessing import Queue
from typing import Any, Callable

# SQLAlchemy exception types for database error handling
try:
    from sqlalchemy.exc import (
        DatabaseError,
        DataError,
        IntegrityError,
        OperationalError,
        ProgrammingError,
    )
except ImportError:
    # Fallback if SQLAlchemy is not available
    DatabaseError = Exception
    DataError = Exception
    IntegrityError = Exception
    OperationalError = Exception
    ProgrammingError = Exception

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class MutexError(Exception):
    """
    Error raised when a mutex/locking issue is detected.

    This typically occurs with:
    - PyTorch/torchvision threading issues
    - TensorFlow session locking
    - OpenBLAS/MKL threading conflicts
    """

    pass


class TrainingError(Exception):
    """
    Error raised when training fails.

    This is a wrapper for various training failures including:
    - Insufficient data
    - Model convergence issues
    - Resource exhaustion
    """

    pass


class SubprocessTimeoutError(TrainingError):
    """
    Error raised when subprocess training times out.
    """

    pass


def is_mutex_error(exception: Exception) -> bool:
    """
    Detect if an exception is related to mutex/locking issues.

    Args:
        exception: The exception to check

    Returns:
        True if the exception appears to be mutex-related

    Example:
        >>> try:
        ...     model.train()
        ... except (ValueError, TypeError, KeyError, AttributeError) as e:
        ...     if is_mutex_error(e):
        ...         logger.error("Mutex issue detected")
    """
    if not isinstance(exception, Exception):
        return False

    error_str = str(exception).lower()
    error_type = type(exception).__name__.lower()

    # Keywords that indicate mutex/locking issues
    mutex_keywords = [
        'mutex',
        'lock',
        'blocking',
        'thread',
        'concurrent',
        'omp',  # OpenMP
        'mkl',  # Intel MKL
        'openblas',
        'blas',
        'torch',
    ]

    # Check error message
    for keyword in mutex_keywords:
        if keyword in error_str or keyword in error_type:
            return True

    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(MutexError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def train_with_retry(
    strategy: Any,
    engine_type: str,
    use_subprocess: bool = False,
    timeout: int = 300,
) -> bool:
    """
    Train strategy with automatic retries for transient failures.

    This function will automatically retry training if a MutexError is detected,
    using exponential backoff between attempts.

    Args:
        strategy: Strategy instance with learning_engine
        engine_type: Type of learning engine ('deep', 'transformer', etc.)
        use_subprocess: If True, use multiprocessing as fallback
        timeout: Timeout in seconds for subprocess training

    Returns:
        True if training was successful, False otherwise

    Raises:
        MutexError: If mutex errors persist after retries
        TrainingError: If training fails for non-mutex reasons

    Example:
        >>> success = train_with_retry(
        ...     strategy=my_strategy,
        ...     engine_type='deep',
        ...     use_subprocess=True
        ... )
    """
    if use_subprocess:
        return _train_in_subprocess(strategy, engine_type, timeout)

    try:
        if not strategy.learning_engine:
            logger.warning(f"Learning engine not initialized for {engine_type}")
            return False

        # Attempt training in-process
        logger.info(f"Training {engine_type} learning engine (in-process)")
        strategy.learning_engine.train()
        return True

    except (ValueError, TypeError, KeyError, AttributeError, IndexError) as e:
        if is_mutex_error(e):
            # Convert to MutexError for tenacity retry
            raise MutexError(f"Mutex detected: {e}") from e
        raise TrainingError(f"Training failed: {e}") from e


def _train_in_subprocess(
    strategy: Any,
    engine_type: str,
    timeout: int = 300,
) -> bool:
    """
    Fallback: Train in isolated subprocess to avoid threading issues.

    This function spawns a new process to perform training, completely
    isolating it from the parent process's threading context.

    Args:
        strategy: Strategy instance to train
        engine_type: Type of learning engine
        timeout: Maximum time to wait for training (seconds)

    Returns:
        True if training succeeded, False otherwise

    Example:
        >>> success = _train_in_subprocess(
        ...     strategy=my_strategy,
        ...     engine_type='deep',
        ...     timeout=600  # 10 minutes
        ... )
    """
    logger.info(f"🔄 Training {engine_type} in isolated subprocess " f"(timeout: {timeout}s)")

    # Use multiprocessing for safe subprocess spawning
    # 'spawn' context creates fresh Python process
    ctx = multiprocessing.get_context('spawn')
    result_queue = ctx.Queue()

    def train_process(queue: Queue) -> None:
        """
        Training function to run in subprocess.
        Imports are done inside the subprocess to avoid import-time threading issues.
        """
        try:
            # Import in subprocess to avoid threading issues in parent
            import importlib

            # Re-import the strategy module in the subprocess
            importlib.import_module(strategy.__module__)

            # Create new strategy instance in subprocess
            # (pickled config would need to be passed if needed)
            logger.info(f"Training {engine_type} in subprocess")

            # Get learning engine and train
            # Note: This assumes learning_engine is already initialized
            # or can be initialized in the subprocess
            if hasattr(strategy, 'learning_engine') and strategy.learning_engine:
                strategy.learning_engine.train()
                queue.put((True, 'Training completed successfully'))
            else:
                queue.put((False, 'Learning engine not available in subprocess'))

        except (ValueError, TypeError, KeyError, AttributeError) as e:
            logger.error(f"Subprocess training error: {e}", exc_info=True)
            queue.put((False, str(e)))

    # Start training process
    p = ctx.Process(target=train_process, args=(result_queue,))

    try:
        p.start()
        p.join(timeout=timeout)

        if p.is_alive():
            # Process timed out
            logger.error(f"❌ Training timeout after {timeout}s - terminating process")
            p.terminate()
            p.join(timeout=5)
            if p.is_alive():
                p.kill()
                p.join()
            raise SubprocessTimeoutError(f"Training timeout after {timeout}s")

        # Get result from queue
        if not result_queue.empty():
            success, message = result_queue.get()
            if success:
                logger.info(f"✅ Subprocess training succeeded: {message}")
                return True
            else:
                logger.error(f"❌ Subprocess training failed: {message}")
                return False
        else:
            logger.error("❌ Subprocess training failed: no result in queue")
            return False

    except SubprocessTimeoutError:
        # Re-raise timeout errors
        raise
    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        logger.error(f"❌ Subprocess training exception: {e}")
        if p.is_alive():
            p.terminate()
            p.join()
        return False


def safe_execute(
    func: Callable[..., Any],
    *args: Any,
    default_return: Any = None,
    log_errors: bool = True,
    **kwargs: Any,
) -> Any:
    """
    Safely execute a function with error handling.

    This is a generic wrapper that catches and logs exceptions,
    returning a default value on failure.

    Args:
        func: Function to execute
        *args: Positional arguments for func
        default_return: Value to return on error
        log_errors: Whether to log errors
        **kwargs: Keyword arguments for func

    Returns:
        Return value of func or default_return on error

    Example:
        >>> result = safe_execute(
        ...     risky_calculation,
        ...     data,
        ...     default_return=0.0
        ... )
    """
    try:
        return func(*args, **kwargs)
    except (IntegrityError, OperationalError, DatabaseError, DataError, ProgrammingError) as e:
        if log_errors:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
        return default_return


def log_and_suppress(
    exception_types: tuple[type[Exception], ...] = (Exception,),
    message: str = "Error suppressed",
    default_return: Any = None,
) -> Callable[..., Any]:
    """
    Decorator to log and suppress exceptions.

    Args:
        exception_types: Tuple of exception types to catch
        message: Message to log when exception occurs
        default_return: Value to return on exception

    Example:
        >>> @log_and_suppress((ValueError, TypeError), "Calculation failed")
        ... def calculate_risk(data):
        ...     return complex_risk_calculation(data)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                logger.warning(f"{message}: {e}")
                return default_return

        return wrapper

    return decorator
