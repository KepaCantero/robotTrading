"""
BacktestMetaAnalyzer - Análisis metacognitivo de resultados de backtests.

Permite:
- Análisis de patrones de rendimiento
- Detección de correlaciones y comportamientos
- Clusterización de resultados
- Sugerencias de combinaciones óptimas
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from sklearn.cluster import KMeans

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn no disponible. Clustering deshabilitado.")

try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib no disponible. Visualizaciones deshabilitadas.")

logger = logging.getLogger(__name__)


class BacktestMetaAnalyzer:
    """
    Analizador meta de resultados de backtests.

    Permite analizar múltiples resultados, detectar patrones,
    clusterizar resultados y sugerir combinaciones óptimas.
    """

    def __init__(
        self, data_dir: str, output_dir: Optional[str] = None, enable_visualizations: bool = True
    ):
        """
        Inicializar analizador meta.

        Args:
            data_dir: Directorio con resultados de backtests (.json o .csv)
            output_dir: Directorio para reportes (default: reports/meta/)
            enable_visualizations: Habilitar generación de gráficos
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir) if output_dir else Path("reports/meta")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.enable_visualizations = enable_visualizations and MATPLOTLIB_AVAILABLE

        self.results: List[Dict[str, Any]] = []
        self.df_results: Optional[pd.DataFrame] = None
        self.analysis_results: Dict[str, Any] = {}

        logger.info(
            f"BacktestMetaAnalyzer inicializado: data_dir={data_dir}, output_dir={self.output_dir}"
        )

    async def load_results(self, path: Optional[str] = None) -> int:
        """
        Cargar resultados automáticamente desde directorio.

        Args:
            path: Ruta opcional (usa self.data_dir si None)

        Returns:
            Número de archivos cargados
        """
        data_path = Path(path) if path else self.data_dir

        if not data_path.exists():
            logger.error(f"Directorio no existe: {data_path}")
            return 0

        logger.info(f"🔄 Cargando resultados desde {data_path}...")

        # Cargar archivos JSON y CSV en paralelo
        json_files = list(data_path.glob("**/*.json"))
        csv_files = list(data_path.glob("**/*.csv"))

        total_files = len(json_files) + len(csv_files)
        logger.info(
            f"Encontrados {total_files} archivos ({len(json_files)} JSON, {len(csv_files)} CSV)"
        )

        # Cargar JSONs
        json_results = await self._load_json_files_async(json_files)

        # Cargar CSVs
        csv_results = await self._load_csv_files_async(csv_files)

        self.results = json_results + csv_results

        # Crear DataFrame para análisis
        if self.results:
            self.df_results = pd.DataFrame(self.results)
            logger.info(f"✅ Cargados {len(self.results)} resultados")
            logger.info(f"   Columnas: {list(self.df_results.columns)}")
        else:
            logger.warning("⚠️ No se encontraron resultados válidos")

        return len(self.results)

    async def _load_json_files_async(self, files: List[Path]) -> List[Dict[str, Any]]:
        """Cargar archivos JSON en paralelo."""

        async def load_file(file_path: Path) -> Optional[Dict[str, Any]]:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Normalizar estructura
                    if isinstance(data, dict):
                        data['source_file'] = str(file_path)
                        data['file_type'] = 'json'
                        return data
            except Exception as e:
                logger.debug(f"Error cargando {file_path}: {e}")
            return None

        tasks = [load_file(f) for f in files]
        results = await asyncio.gather(*tasks)

        # Filtrar None
        return [r for r in results if r is not None]

    async def _load_csv_files_async(self, files: List[Path]) -> List[Dict[str, Any]]:
        """Cargar archivos CSV en paralelo."""

        async def load_file(file_path: Path) -> Optional[List[Dict[str, Any]]]:
            try:
                df = pd.read_csv(file_path)
                # Convertir a lista de dicts
                records = df.to_dict('records')
                # Agregar metadata
                for record in records:
                    record['source_file'] = str(file_path)
                    record['file_type'] = 'csv'
                return records
            except Exception as e:
                logger.debug(f"Error cargando {file_path}: {e}")
            return None

        tasks = [load_file(f) for f in files]
        results = await asyncio.gather(*tasks)

        # Flatten lista de listas
        flattened = []
        for r in results:
            if r:
                flattened.extend(r)

        return flattened

    def analyze_performance(self) -> Dict[str, Any]:
        """
        Analizar rendimiento agregado de todos los resultados.

        Returns:
            Dict con métricas agregadas y análisis
        """
        if self.df_results is None or self.df_results.empty:
            logger.warning("No hay resultados cargados para analizar")
            return {}

        logger.info("📊 Analizando rendimiento...")

        # Métricas numéricas clave
        metrics = [
            'total_pnl',
            'return_pct',
            'sharpe_ratio',
            'sortino_ratio',
            'max_drawdown',
            'win_rate',
            'total_trades',
            'avg_trade_pnl',
            'profit_factor',
            'calmar_ratio',
        ]

        # Filtrar métricas disponibles
        available_metrics = [m for m in metrics if m in self.df_results.columns]

        analysis = {
            'summary_stats': {},
            'performance_by_category': {},
            'correlations': {},
            'best_performers': {},
            'worst_performers': {},
            'timestamp': datetime.now().isoformat(),
        }

        # Estadísticas resumidas
        for metric in available_metrics:
            col = self.df_results[metric]
            analysis['summary_stats'][metric] = {
                'mean': float(col.mean()) if pd.notna(col.mean()) else None,
                'median': float(col.median()) if pd.notna(col.median()) else None,
                'std': float(col.std()) if pd.notna(col.std()) else None,
                'min': float(col.min()) if pd.notna(col.min()) else None,
                'max': float(col.max()) if pd.notna(col.max()) else None,
                'q25': float(col.quantile(0.25)) if pd.notna(col.quantile(0.25)) else None,
                'q75': float(col.quantile(0.75)) if pd.notna(col.quantile(0.75)) else None,
            }

        # Análisis por categoría
        category_columns = ['test_type', 'strategy_name', 'learning_engine']
        for cat_col in category_columns:
            if cat_col in self.df_results.columns:
                analysis['performance_by_category'][cat_col] = self._analyze_by_category(
                    cat_col, available_metrics
                )

        # Correlaciones
        if len(available_metrics) > 1:
            numeric_df = self.df_results[available_metrics].select_dtypes(include=[np.number])
            if not numeric_df.empty:
                analysis['correlations'] = numeric_df.corr().to_dict()

        # Mejores y peores
        if 'sharpe_ratio' in self.df_results.columns:
            best_sharpe = self.df_results.nlargest(10, 'sharpe_ratio')
            worst_sharpe = self.df_results.nsmallest(10, 'sharpe_ratio')
            analysis['best_performers']['by_sharpe'] = best_sharpe.to_dict('records')
            analysis['worst_performers']['by_sharpe'] = worst_sharpe.to_dict('records')

        if 'total_pnl' in self.df_results.columns:
            best_pnl = self.df_results.nlargest(10, 'total_pnl')
            worst_pnl = self.df_results.nsmallest(10, 'total_pnl')
            analysis['best_performers']['by_pnl'] = best_pnl.to_dict('records')
            analysis['worst_performers']['by_pnl'] = worst_pnl.to_dict('records')

        self.analysis_results = analysis
        logger.info("✅ Análisis de rendimiento completado")

        return analysis

    def _analyze_by_category(self, category_col: str, metrics: List[str]) -> Dict[str, Any]:
        """Analizar métricas por categoría."""
        category_analysis = {}

        for category in self.df_results[category_col].dropna().unique():
            category_data = self.df_results[self.df_results[category_col] == category]
            category_analysis[category] = {}

            for metric in metrics:
                if metric in category_data.columns:
                    col = category_data[metric].dropna()
                    if len(col) > 0:
                        category_analysis[category][metric] = {
                            'mean': float(col.mean()),
                            'count': int(len(col)),
                        }

        return category_analysis

    def detect_clusters(
        self, n_clusters: int = 3, features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detectar clusters de resultados similares usando KMeans.

        Args:
            n_clusters: Número de clusters
            features: Lista de features para clustering (default: métricas principales)

        Returns:
            Dict con clusters y sus características
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn no disponible. Clustering deshabilitado.")
            return {}

        if self.df_results is None or self.df_results.empty:
            logger.warning("No hay resultados para clusterizar")
            return {}

        logger.info(f"🔍 Detectando {n_clusters} clusters...")

        # Features por defecto
        if features is None:
            features = [
                'sharpe_ratio',
                'total_pnl',
                'max_drawdown',
                'win_rate',
                'return_pct',
                'total_trades',
            ]

        # Filtrar features disponibles
        available_features = [f for f in features if f in self.df_results.columns]

        if len(available_features) < 2:
            logger.warning(f"No hay suficientes features para clustering: {available_features}")
            return {}

        # Preparar datos
        X = self.df_results[available_features].select_dtypes(include=[np.number])
        X = X.dropna()

        if len(X) < n_clusters:
            logger.warning(f"No hay suficientes datos ({len(X)}) para {n_clusters} clusters")
            return {}

        # Normalizar
        X_normalized = (X - X.mean()) / X.std()

        # KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_normalized)

        # Agregar clusters al DataFrame
        cluster_df = X.copy()
        cluster_df['cluster'] = clusters

        # Analizar cada cluster
        cluster_analysis = {}
        for i in range(n_clusters):
            cluster_data = cluster_df[cluster_df['cluster'] == i]
            cluster_analysis[f'cluster_{i}'] = {
                'size': int(len(cluster_data)),
                'characteristics': {
                    feature: {
                        'mean': float(cluster_data[feature].mean()),
                        'std': float(cluster_data[feature].std()),
                    }
                    for feature in available_features
                    if feature in cluster_data.columns
                },
                'indices': cluster_data.index.tolist(),
            }

        # Agregar información al DataFrame principal
        self.df_results['cluster'] = pd.Series(clusters, index=X.index)

        result = {
            'n_clusters': n_clusters,
            'features_used': available_features,
            'clusters': cluster_analysis,
            'inertia': float(kmeans.inertia_),
        }

        logger.info(f"✅ Clusters detectados: {n_clusters}")

        return result

    def suggest_optimal_combinations(
        self, top_n: int = 10, criteria: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Sugerir combinaciones óptimas de parámetros o estrategias.

        Args:
            top_n: Número de sugerencias
            criteria: Dict con pesos para métricas (default: sharpe y pnl)
                     Ej: {'sharpe_ratio': 0.6, 'total_pnl': 0.4}

        Returns:
            Lista de combinaciones ordenadas por score
        """
        if self.df_results is None or self.df_results.empty:
            logger.warning("No hay resultados para sugerir combinaciones")
            return []

        logger.info(f"💡 Sugiriendo {top_n} combinaciones óptimas...")

        # Criterios por defecto
        if criteria is None:
            criteria = {
                'sharpe_ratio': 0.4,
                'total_pnl': 0.3,
                'win_rate': 0.2,
                'max_drawdown': -0.1,  # Negativo porque queremos minimizar drawdown
            }

        # Calcular score compuesto
        scores = []
        available_criteria = {k: v for k, v in criteria.items() if k in self.df_results.columns}

        for idx, row in self.df_results.iterrows():
            score = 0.0
            for metric, weight in available_criteria.items():
                value = row[metric]
                if pd.notna(value):
                    # Normalizar por max si weight > 0, por min si weight < 0
                    if weight > 0:
                        max_val = self.df_results[metric].max()
                        if max_val > 0:
                            normalized = float(value) / float(max_val)
                        else:
                            normalized = 0.0
                    else:
                        min_val = self.df_results[metric].min()
                        if min_val < 0:
                            normalized = float(value) / abs(float(min_val))
                        else:
                            normalized = 0.0
                    score += normalized * abs(weight)

            scores.append({'index': idx, 'score': score, 'row': row.to_dict()})

        # Ordenar por score
        scores.sort(key=lambda x: x['score'], reverse=True)

        # Top N
        suggestions = scores[:top_n]

        logger.info(f"✅ {top_n} sugerencias generadas")
        logger.info(f"   Mejor score: {suggestions[0]['score']:.4f}")

        return [s['row'] for s in suggestions]

    def export_report(self, output_path: Optional[str] = None, format: str = "json") -> str:
        """
        Exportar reporte completo de análisis.

        Args:
            output_path: Ruta de salida (default: output_dir/meta_analysis_YYYYMMDD_HHMMSS.json)
            format: Formato ('json' o 'csv')

        Returns:
            Ruta del archivo generado
        """
        if not self.analysis_results:
            logger.warning("No hay análisis para exportar. Ejecuta analyze_performance() primero.")
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if output_path is None:
            filename = f"meta_analysis_{timestamp}.{format}"
            output_path = self.output_dir / filename
        else:
            output_path = Path(output_path)

        if format == "json":
            with open(output_path, 'w') as f:
                json.dump(self.analysis_results, f, indent=2, default=str)
        elif format == "csv" and self.df_results is not None:
            self.df_results.to_csv(output_path, index=False)
        else:
            logger.error(f"Formato no soportado: {format}")
            return ""

        logger.info(f"✅ Reporte exportado: {output_path}")

        # Generar visualizaciones si está habilitado
        if self.enable_visualizations:
            self._generate_visualizations()

        return str(output_path)

    def _generate_visualizations(self) -> None:
        """Generar visualizaciones de análisis."""
        if not MATPLOTLIB_AVAILABLE or self.df_results is None:
            return

        logger.info("📊 Generando visualizaciones...")

        try:
            # Configurar estilo
            plt.style.use('seaborn-v0_8-darkgrid')
            sns.set_palette("husl")

            # 1. Distribución de Sharpe Ratio
            if 'sharpe_ratio' in self.df_results.columns:
                fig, ax = plt.subplots(figsize=(10, 6))
                self.df_results['sharpe_ratio'].hist(bins=30, ax=ax)
                ax.set_title('Distribución de Sharpe Ratio')
                ax.set_xlabel('Sharpe Ratio')
                ax.set_ylabel('Frecuencia')
                plt.savefig(
                    self.output_dir / 'sharpe_distribution.png', dpi=150, bbox_inches='tight'
                )
                plt.close()

            # 2. Scatter: Sharpe vs PnL
            if 'sharpe_ratio' in self.df_results.columns and 'total_pnl' in self.df_results.columns:
                fig, ax = plt.subplots(figsize=(10, 6))
                scatter = ax.scatter(
                    self.df_results['total_pnl'],
                    self.df_results['sharpe_ratio'],
                    alpha=0.6,
                    c=self.df_results.get('cluster', 0),
                    cmap='viridis',
                )
                ax.set_xlabel('Total PnL')
                ax.set_ylabel('Sharpe Ratio')
                ax.set_title('Sharpe Ratio vs Total PnL')
                plt.colorbar(scatter, ax=ax, label='Cluster')
                plt.savefig(self.output_dir / 'sharpe_vs_pnl.png', dpi=150, bbox_inches='tight')
                plt.close()

            # 3. Heatmap de correlaciones
            if len(self.df_results.select_dtypes(include=[np.number]).columns) > 1:
                numeric_cols = self.df_results.select_dtypes(include=[np.number]).columns[
                    :10
                ]  # Top 10
                corr = self.df_results[numeric_cols].corr()
                fig, ax = plt.subplots(figsize=(10, 8))
                sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0, ax=ax)
                ax.set_title('Matriz de Correlaciones')
                plt.savefig(
                    self.output_dir / 'correlation_heatmap.png', dpi=150, bbox_inches='tight'
                )
                plt.close()

            logger.info(f"✅ Visualizaciones guardadas en {self.output_dir}")

        except Exception as e:
            logger.error(f"Error generando visualizaciones: {e}", exc_info=True)

    async def run_parallel_analysis(
        self, max_workers: int = 4, include_clustering: bool = True, n_clusters: int = 3
    ) -> Dict[str, Any]:
        """
        Ejecutar análisis completo en paralelo.

        Args:
            max_workers: Número máximo de workers para tareas CPU-bound
            include_clustering: Incluir detección de clusters
            n_clusters: Número de clusters si clustering está habilitado

        Returns:
            Dict con todos los resultados del análisis
        """
        logger.info(f"🚀 Iniciando análisis paralelo (max_workers={max_workers})...")

        # Tareas I/O-bound (asyncio)
        async def load_data():
            await self.load_results()

        # Tareas CPU-bound (ThreadPoolExecutor)
        def analyze_cpu():
            return self.analyze_performance()

        def cluster_cpu():
            if include_clustering and SKLEARN_AVAILABLE:
                return self.detect_clusters(n_clusters=n_clusters)
            return {}

        # Ejecutar carga de datos
        await load_data()

        # Ejecutar análisis CPU-bound en paralelo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(analyze_cpu): 'performance',
                executor.submit(cluster_cpu): 'clustering',
            }

            results = {}
            for future in as_completed(futures):
                task_name = futures[future]
                try:
                    results[task_name] = future.result()
                except Exception as e:
                    logger.error(f"Error en tarea {task_name}: {e}")
                    results[task_name] = {}

        # Sugerencias (usando resultados ya calculados)
        if 'performance' in results:
            suggestions = self.suggest_optimal_combinations(top_n=10)
            results['suggestions'] = suggestions

        logger.info("✅ Análisis paralelo completado")

        return results
