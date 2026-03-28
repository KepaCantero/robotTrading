"""
Data Loader para Comprehensive Backtest Results

Carga resultados de comprehensive_backtest para el dashboard principal.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ComprehensiveBacktestLoader:
    """Cargador de resultados de comprehensive backtests."""

    def __init__(self, results_dir: Optional[str] = None):
        """
        Inicializar cargador.

        Args:
            results_dir: Directorio con resultados de comprehensive backtests.
                        Si es None, busca en múltiples ubicaciones posibles.
        """
        if results_dir:
            self.results_dir = Path(results_dir)
        else:
            # Buscar en múltiples ubicaciones posibles
            possible_dirs = [
                Path("reports/comprehensive_backtest"),
                Path("reports"),
                Path("docs/BACKTEST_RESULTS"),
            ]

            # Usar el primer directorio que exista o crear el primero
            self.results_dir = None
            for dir_path in possible_dirs:
                if dir_path.exists():
                    self.results_dir = dir_path
                    break

            if self.results_dir is None:
                # Si ninguno existe, usar el primero y crearlo
                self.results_dir = possible_dirs[0]

        self.results_dir.mkdir(parents=True, exist_ok=True)

    def load_all_results(self) -> List[Dict[str, Any]]:
        """
        Cargar todos los resultados de comprehensive backtests.

        Returns:
            Lista de dicts con resultados de cada backtest
        """
        results = []

        # Buscar archivos JSON de resultados
        # Primero buscar en el directorio principal
        json_files = []

        # Buscar archivos con el patrón estándar (recursivo)
        json_files.extend(list(self.results_dir.rglob("comprehensive_backtest_results_*.json")))

        # También buscar archivos individuales de tests (grid_search, monte_carlo, etc.)
        test_patterns = [
            "grid_search_*.json",
            "monte_carlo_*.json",
            "baseline_*.json",
            "learning_engine_*.json",
            "ablation_*.json",
            "walk_forward_*.json",
            "out_of_sample_*.json",
            "regime_test_*.json",
            "multi_strategy_*.json",
        ]

        for pattern in test_patterns:
            json_files.extend(list(self.results_dir.rglob(pattern)))

        # Si no encontramos nada, buscar en toda la estructura de reports
        if not json_files:
            logger.debug(
                f"🔍 No se encontraron archivos JSON en {self.results_dir}. Buscando en estructura completa..."
            )
            # Buscar también en el directorio padre (reports/)
            parent_dir = (
                self.results_dir.parent
                if self.results_dir.name == "comprehensive_backtest"
                else self.results_dir.parent
            )
            if parent_dir.exists() and parent_dir != self.results_dir:
                logger.debug(f"🔍 Buscando en directorio padre: {parent_dir}")
                json_files.extend(list(parent_dir.rglob("*backtest*.json")))
                json_files.extend(list(parent_dir.rglob("*comprehensive*.json")))
                json_files.extend(list(parent_dir.rglob("comprehensive_backtest_results_*.json")))

        # También buscar en el directorio de trabajo actual si no encontramos nada
        if not json_files:
            from pathlib import Path

            cwd = Path.cwd()
            reports_dir = cwd / "reports"
            if reports_dir.exists():
                logger.debug(f"🔍 Buscando en reports/ del proyecto: {reports_dir}")
                json_files.extend(list(reports_dir.rglob("comprehensive_backtest_results_*.json")))
                json_files.extend(list(reports_dir.rglob("grid_search_*.json")))
                json_files.extend(list(reports_dir.rglob("monte_carlo_*.json")))
                json_files.extend(list(reports_dir.rglob("baseline_*.json")))
                json_files.extend(list(reports_dir.rglob("learning_engine_*.json")))

        # Eliminar duplicados y filtrar solo archivos que existen
        json_files = list({f for f in json_files if f.exists() and f.is_file()})

        # Ordenar por fecha de modificación (más recientes primero)
        json_files = sorted(
            json_files, key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True
        )

        if json_files:
            logger.info(f"📁 Encontrados {len(json_files)} archivos JSON")
            logger.debug(f"📁 Primeros archivos: {[f.name for f in json_files[:5]]}")
        else:
            # Solo log debug cuando no hay archivos (es normal si no se han ejecutado tests)
            logger.debug(
                f"ℹ️ No hay archivos JSON aún en {self.results_dir} (normal si no se han ejecutado tests)"
            )

        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                    # Si es una lista, agregar cada elemento
                    file_results = []
                    if isinstance(data, list):
                        file_results = data
                    elif isinstance(data, dict):
                        # Si tiene 'results', usar eso
                        file_results = data.get('results', [data])

                    # Parsear campos de learning engines si vienen como strings
                    for result in file_results:
                        # Parsear before_training_metrics si es string
                        if 'before_training_metrics' in result:
                            before_metrics = result['before_training_metrics']
                            if isinstance(before_metrics, str) and before_metrics.strip():
                                try:
                                    import ast

                                    result['before_training_metrics'] = (
                                        ast.literal_eval(before_metrics)
                                        if before_metrics.startswith('{')
                                        else {}
                                    )
                                except (ValueError, SyntaxError):
                                    try:
                                        result['before_training_metrics'] = json.loads(
                                            before_metrics
                                        )
                                    except (ValueError, json.JSONDecodeError) as e2:
                                        logger.debug(
                                            f"No se pudo parsear before_training_metrics: {before_metrics[:50]} - {e2}"
                                        )
                                        result['before_training_metrics'] = {}

                        # Parsear after_training_metrics si es string
                        if 'after_training_metrics' in result:
                            after_metrics = result['after_training_metrics']
                            if isinstance(after_metrics, str) and after_metrics.strip():
                                try:
                                    import ast

                                    result['after_training_metrics'] = (
                                        ast.literal_eval(after_metrics)
                                        if after_metrics.startswith('{')
                                        else {}
                                    )
                                except (ValueError, SyntaxError):
                                    try:
                                        result['after_training_metrics'] = json.loads(after_metrics)
                                    except (ValueError, json.JSONDecodeError) as e2:
                                        logger.debug(
                                            f"No se pudo parsear after_training_metrics: {after_metrics[:50]} - {e2}"
                                        )
                                        result['after_training_metrics'] = {}

                        # Parsear improvement_pct si es string
                        if 'improvement_pct' in result:
                            improvement = result['improvement_pct']
                            if isinstance(improvement, str) and improvement.strip():
                                try:
                                    import ast

                                    result['improvement_pct'] = (
                                        ast.literal_eval(improvement)
                                        if improvement.startswith('{')
                                        else {}
                                    )
                                except (ValueError, SyntaxError):
                                    try:
                                        result['improvement_pct'] = json.loads(improvement)
                                    except (ValueError, json.JSONDecodeError) as e2:
                                        logger.debug(
                                            f"No se pudo parsear improvement_pct: {improvement[:50]} - {e2}"
                                        )
                                        result['improvement_pct'] = {}

                        # Contar learning engines con datos de entrenamiento
                        if result.get('test_type') == 'learning_engine' and (
                            result.get('before_training_metrics')
                            or result.get('after_training_metrics')
                            or result.get('improvement_pct')
                        ):
                            logger.debug(
                                f"✅ Learning engine result encontrado: {result.get('learning_engine', 'unknown')} "
                                f"- Antes: {bool(result.get('before_training_metrics'))} "
                                f"- Después: {bool(result.get('after_training_metrics'))} "
                                f"- Mejora: {bool(result.get('improvement_pct'))}"
                            )

                    results.extend(file_results)
                    logger.debug(
                        f"Cargado: {json_file.name} ({len(file_results)} resultados, {len(results)} total)"
                    )
            except OSError as e:
                logger.warning(f"Error cargando {json_file.name}: {e}", exc_info=True)

        # Contar learning engines con datos de entrenamiento
        learning_engine_count = sum(
            1
            for r in results
            if r.get('test_type') == 'learning_engine'
            and (r.get('before_training_metrics') or r.get('after_training_metrics'))
        )

        logger.info(
            f"✅ Cargados {len(results)} resultados de comprehensive backtests "
            f"({learning_engine_count} con datos de training)"
        )
        return results

    def load_latest_results(self) -> Optional[Dict[str, Any]]:
        """
        Cargar los resultados más recientes.

        Returns:
            Dict con resultados más recientes o None
        """
        all_results = self.load_all_results()
        if all_results:
            # Retornar el primero (más reciente)
            return all_results[0]
        return None

    def load_as_dataframe(self) -> pd.DataFrame:
        """
        Cargar todos los resultados como DataFrame.

        Returns:
            DataFrame con todos los resultados
        """
        results = self.load_all_results()

        if not results:
            return pd.DataFrame()

        # Convertir a DataFrame
        df = pd.DataFrame(results)

        # Asegurar que las columnas clave existen
        required_cols = ['test_type', 'total_pnl', 'sharpe_ratio', 'win_rate', 'max_drawdown']
        for col in required_cols:
            if col not in df.columns:
                df[col] = None

        return df

    def get_results_by_type(self, test_type: str) -> List[Dict[str, Any]]:
        """
        Obtener resultados filtrados por tipo de test.

        Args:
            test_type: Tipo de test (baseline, monte_carlo, grid_search, etc.)

        Returns:
            Lista de resultados del tipo especificado
        """
        all_results = self.load_all_results()
        return [r for r in all_results if r.get('test_type') == test_type]

    def get_best_result(self, metric: str = 'sharpe_ratio') -> Optional[Dict[str, Any]]:
        """
        Obtener el mejor resultado según una métrica.

        Args:
            metric: Métrica para comparar (sharpe_ratio, total_pnl, etc.)

        Returns:
            Dict con el mejor resultado o None
        """
        all_results = self.load_all_results()

        if not all_results:
            return None

        # Filtrar resultados con la métrica
        valid_results = [r for r in all_results if r.get(metric) is not None]

        if not valid_results:
            return None

        # Retornar el mejor
        return max(valid_results, key=lambda x: x.get(metric, float('-in')))

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas resumidas de todos los resultados.

        Returns:
            Dict con estadísticas agregadas
        """
        df = self.load_as_dataframe()

        if df.empty:
            return {
                'total_tests': 0,
                'test_types': [],
                'avg_sharpe': 0.0,
                'avg_pnl': 0.0,
                'best_sharpe': 0.0,
                'best_pnl': 0.0,
            }

        stats = {
            'total_tests': len(df),
            'test_types': df['test_type'].unique().tolist() if 'test_type' in df.columns else [],
            'avg_sharpe': float(df['sharpe_ratio'].mean()) if 'sharpe_ratio' in df.columns else 0.0,
            'avg_pnl': float(df['total_pnl'].mean()) if 'total_pnl' in df.columns else 0.0,
            'avg_win_rate': float(df['win_rate'].mean()) if 'win_rate' in df.columns else 0.0,
            'best_sharpe': float(df['sharpe_ratio'].max()) if 'sharpe_ratio' in df.columns else 0.0,
            'best_pnl': float(df['total_pnl'].max()) if 'total_pnl' in df.columns else 0.0,
            'worst_drawdown': (
                float(df['max_drawdown'].min()) if 'max_drawdown' in df.columns else 0.0
            ),
        }

        return stats

    def load_meta_analysis_results(self) -> Optional[Dict[str, Any]]:
        """
        Cargar resultados del meta análisis (si existen).

        Returns:
            Dict con resultados del meta análisis o None
        """
        meta_dir = self.results_dir / "meta"

        if not meta_dir.exists():
            logger.debug("No existe directorio meta/ para análisis meta")
            return None

        # Buscar el archivo más reciente de meta análisis
        meta_files = sorted(
            meta_dir.glob("meta_analysis_*.json"), key=lambda x: x.stat().st_mtime, reverse=True
        )

        if not meta_files:
            logger.debug("No se encontraron archivos de meta análisis")
            return None

        # Cargar el más reciente
        latest_file = meta_files[0]
        try:
            with open(latest_file, 'r') as f:
                meta_results = json.load(f)

            logger.info(f"✅ Cargados resultados de meta análisis: {latest_file.name}")
            return {
                'file_path': str(latest_file),
                'file_name': latest_file.name,
                'timestamp': datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat(),
                'data': meta_results,
            }
        except OSError as e:
            logger.warning(f"Error cargando meta análisis {latest_file.name}: {e}")
            return None

    def get_meta_analysis_summary(self) -> Optional[Dict[str, Any]]:
        """
        Obtener resumen del meta análisis.

        Returns:
            Dict con resumen o None
        """
        meta_data = self.load_meta_analysis_results()

        if not meta_data or 'data' not in meta_data:
            return None

        analysis_data = meta_data['data']

        summary = {
            'file_name': meta_data.get('file_name', 'Unknown'),
            'timestamp': meta_data.get('timestamp', 'Unknown'),
            'total_backtests_analyzed': analysis_data.get('total_backtests', 0),
            'clusters_found': (
                len(analysis_data.get('clusters', {}))
                if isinstance(analysis_data.get('clusters'), dict)
                else 0
            ),
            'optimal_combinations_count': len(analysis_data.get('optimal_combinations', [])),
            'avg_sharpe': analysis_data.get('aggregate_metrics', {}).get('avg_sharpe_ratio', 0),
            'avg_return': analysis_data.get('aggregate_metrics', {}).get('avg_return_pct', 0),
            'correlations': analysis_data.get('correlations', {}),
            'clusters': analysis_data.get('clusters', {}),
            'optimal_combinations': analysis_data.get('optimal_combinations', []),
        }

        return summary
