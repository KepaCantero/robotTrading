"""
Parallel Executor - Sistema de ejecución paralela para backtests.

Permite paralelizar:
- Monte Carlo simulations
- Grid Search combinations
- Learning Engines tests
- Ablation tests
"""

import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Determinar número óptimo de workers
DEFAULT_MAX_WORKERS = min(multiprocessing.cpu_count(), 8)


class ParallelExecutor:
    """
    Ejecutor paralelo para backtests que pueden ejecutarse independientemente.

    Usa ProcessPoolExecutor para CPU-bound tasks (simulaciones Monte Carlo, etc.)
    y ThreadPoolExecutor para I/O-bound tasks.
    """

    def __init__(self, max_workers: Optional[int] = None, use_processes: bool = True):
        """
        Inicializar ejecutor paralelo.

        Args:
            max_workers: Número máximo de workers (default: CPU count)
            use_processes: Si True, usa ProcessPoolExecutor (CPU-bound),
                          si False, usa ThreadPoolExecutor (I/O-bound)
        """
        self.max_workers = max_workers or DEFAULT_MAX_WORKERS
        self.use_processes = use_processes

        logger.info(
            f"ParallelExecutor inicializado: max_workers={self.max_workers}, use_processes={use_processes}"
        )

    def run_parallel(
        self, tasks: List[Dict[str, Any]], task_function: Callable, task_name: str = "task"
    ) -> List[Dict[str, Any]]:
        """
        Ejecutar múltiples tareas en paralelo.

        Args:
            tasks: Lista de dicts con parámetros para cada tarea
            task_function: Función que ejecuta una tarea (debe aceptar un dict)
            task_name: Nombre descriptivo para logging

        Returns:
            Lista de resultados de cada tarea
        """
        if not tasks:
            return []

        logger.info(
            f"🚀 Ejecutando {len(tasks)} {task_name}(s) en paralelo (workers={self.max_workers})..."
        )

        # Elegir executor apropiado
        ExecutorClass = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor

        results = []
        failed_count = 0

        with ExecutorClass(max_workers=self.max_workers) as executor:
            # Submit todas las tareas
            future_to_task = {executor.submit(task_function, task): task for task in tasks}

            # Recoger resultados conforme completan
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                    else:
                        failed_count += 1
                        logger.warning(
                            f"⚠️ {task_name} falló (retornó None): {task.get('name', 'unknown')}"
                        )
                except Exception as e:
                    failed_count += 1
                    task_name_str = task.get('name', 'unknown')
                    logger.error(f"❌ Error en {task_name} '{task_name_str}': {e}", exc_info=True)

        logger.info(f"✅ {task_name} completado: {len(results)} exitosos, {failed_count} fallidos")

        return results

    def run_monte_carlo_parallel(
        self, num_simulations: int, simulation_function: Callable, **simulation_kwargs
    ) -> List[Dict[str, Any]]:
        """
        Ejecutar simulaciones Monte Carlo en paralelo.

        Args:
            num_simulations: Número de simulaciones
            simulation_function: Función que ejecuta una simulación
            **simulation_kwargs: Argumentos adicionales para cada simulación

        Returns:
            Lista de resultados de simulaciones
        """
        # Crear tareas para cada simulación
        tasks = [
            {
                'simulation_num': i + 1,
                'name': f'Monte Carlo Simulation {i + 1}',
                **simulation_kwargs,
            }
            for i in range(num_simulations)
        ]

        return self.run_parallel(
            tasks=tasks, task_function=simulation_function, task_name="Monte Carlo Simulation"
        )

    def run_grid_search_parallel(
        self, parameter_combinations: List[Dict[str, Any]], combination_function: Callable
    ) -> List[Dict[str, Any]]:
        """
        Ejecutar combinaciones de Grid Search en paralelo.

        Args:
            parameter_combinations: Lista de dicts con combinaciones de parámetros
            combination_function: Función que ejecuta una combinación

        Returns:
            Lista de resultados de combinaciones
        """
        tasks = [
            {
                'combination_num': i + 1,
                'name': f'Grid Search Combination {i + 1}',
                'parameters': combo,
                **combo,
            }
            for i, combo in enumerate(parameter_combinations)
        ]

        return self.run_parallel(
            tasks=tasks, task_function=combination_function, task_name="Grid Search Combination"
        )

    def run_learning_engines_parallel(
        self, engines: List[str], engine_function: Callable, **engine_kwargs
    ) -> List[Dict[str, Any]]:
        """
        Ejecutar tests de learning engines en paralelo.

        Args:
            engines: Lista de nombres de engines a probar
            engine_function: Función que ejecuta un test de engine
            **engine_kwargs: Argumentos adicionales para cada test

        Returns:
            Lista de resultados de engines
        """
        tasks = [
            {'engine_name': engine, 'name': f'Learning Engine - {engine}', **engine_kwargs}
            for engine in engines
        ]

        return self.run_parallel(
            tasks=tasks, task_function=engine_function, task_name="Learning Engine Test"
        )


def create_parallel_executor(
    max_workers: Optional[int] = None, use_processes: bool = True
) -> ParallelExecutor:
    """
    Factory function para crear ParallelExecutor.

    Args:
        max_workers: Número máximo de workers
        use_processes: Si usar procesos (CPU-bound) o threads (I/O-bound)

    Returns:
        ParallelExecutor instance
    """
    return ParallelExecutor(max_workers=max_workers, use_processes=use_processes)
