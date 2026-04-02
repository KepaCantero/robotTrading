"""
BacktestMetaAnalyzer - Análisis metacognitivo de resultados de backtests.

Permite:
- Análisis de patrones de rendimiento
- Detección de correlaciones y comportamientos
- Clusterización de resultados
- Sugerencias de combinaciones óptimas
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Optional dependencies with graceful fallbacks
try:
    from sklearn.cluster import KMeans

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    KMeans = None

try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    HAS_MATPLOTLIB = True
except Exception:
    # Matplotlib may fail due to numpy version incompatibility
    HAS_MATPLOTLIB = False
    plt = None
    sns = None

logger = logging.getLogger(__name__)


class BacktestMetaAnalyzer:
    """
    Analizador meta de resultados de backtests.

    Permite analizar múltiples resultados, detectar patrones,
    clusterizar resultados y sugerir combinaciones óptimas.
    """

    def __init__(
        self, data_dir: str, output_dir: str | None = None, enable_visualizations: bool = True
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
        self.enable_visualizations = enable_visualizations

        # Thread-safe state management with RLock
        self._lock = threading.RLock()
        self.results: list[dict[str, Any]] = []
        self.df_results: pd.DataFrame | None = None
        self.analysis_results: dict[str, Any] = {}

        logger.info(
            f"BacktestMetaAnalyzer inicializado: data_dir={data_dir}, output_dir={self.output_dir}"
        )

    async def load_results(self, path: str | None = None) -> int:
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

        # Thread-safe update of shared state
        with self._lock:
            self.results = json_results + csv_results

            # Crear DataFrame para análisis
            if self.results:
                self.df_results = pd.DataFrame(self.results)
                logger.info(f"✅ Cargados {len(self.results)} resultados")
                logger.info(f"   Columnas: {list(self.df_results.columns)}")
            else:
                self.df_results = None
                logger.warning("⚠️ No se encontraron resultados válidos")

        return len(self.results)

    async def _load_json_files_async(self, files: list[Path]) -> list[dict[str, Any]]:
        """Cargar archivos JSON en paralelo."""

        async def load_file(file_path: Path) -> dict[str, Any] | None:
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    # Normalizar estructura
                    if isinstance(data, dict):
                        data["source_file"] = str(file_path)
                        data["file_type"] = "json"
                        return data
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.debug(f"Error cargando {file_path}: {e}", exc_info=True)
            return None

        tasks = [load_file(f) for f in files]
        results = await asyncio.gather(*tasks)

        # Filtrar None
        return [r for r in results if r is not None]

    async def _load_csv_files_async(self, files: list[Path]) -> list[dict[str, Any]]:
        """Cargar archivos CSV en paralelo."""

        async def load_file(file_path: Path) -> list[dict[str, Any]] | None:
            try:
                df = pd.read_csv(file_path)
                # Convertir a lista de dicts
                records = df.to_dict("records")
                # Agregar metadata
                for record in records:
                    record["source_file"] = str(file_path)
                    record["file_type"] = "csv"
                return records
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                logger.debug(f"Error cargando {file_path}: {e}", exc_info=True)
            return None

        tasks = [load_file(f) for f in files]
        results = await asyncio.gather(*tasks)

        # Flatten lista de listas
        flattened = []
        for r in results:
            if r:
                flattened.extend(r)

        return flattened

    def analyze_performance(self) -> dict[str, Any]:
        """
        Analizar rendimiento agregado de todos los resultados.

        Returns:
            Dict con métricas agregadas y análisis
        """
        # Thread-safe read of shared state
        with self._lock:
            if self.df_results is None or self.df_results.empty:
                logger.warning("No hay resultados cargados para analizar")
                return {}

            # Make a copy to avoid holding lock during computation
            df_copy = self.df_results.copy()

        logger.info("📊 Analizando rendimiento...")

        # Métricas numéricas clave
        metrics = [
            "total_pnl",
            "return_pct",
            "sharpe_ratio",
            "sortino_ratio",
            "max_drawdown",
            "win_rate",
            "total_trades",
            "avg_trade_pnl",
            "profit_factor",
            "calmar_ratio",
        ]

        # Filtrar métricas disponibles
        available_metrics = [m for m in metrics if m in df_copy.columns]

        analysis = {
            "summary_stats": {},
            "performance_by_category": {},
            "correlations": {},
            "best_performers": {},
            "worst_performers": {},
            "timestamp": datetime.now().isoformat(),
        }

        # Estadísticas resumidas
        for metric in available_metrics:
            col = df_copy[metric]
            analysis["summary_stats"][metric] = {
                "mean": float(col.mean()) if pd.notna(col.mean()) else None,
                "median": float(col.median()) if pd.notna(col.median()) else None,
                "std": float(col.std()) if pd.notna(col.std()) else None,
                "min": float(col.min()) if pd.notna(col.min()) else None,
                "max": float(col.max()) if pd.notna(col.max()) else None,
                "q25": float(col.quantile(0.25)) if pd.notna(col.quantile(0.25)) else None,
                "q75": float(col.quantile(0.75)) if pd.notna(col.quantile(0.75)) else None,
            }

        # Análisis por categoría
        category_columns = ["test_type", "strategy_name", "learning_engine"]
        for cat_col in category_columns:
            if cat_col in df_copy.columns:
                analysis["performance_by_category"][cat_col] = self._analyze_by_category(
                    df_copy, cat_col, available_metrics
                )

        # Correlaciones
        if len(available_metrics) > 1:
            numeric_df = df_copy[available_metrics].select_dtypes(include=[np.number])
            if not numeric_df.empty:
                analysis["correlations"] = numeric_df.corr().to_dict()

        # Mejores y peores
        if "sharpe_ratio" in df_copy.columns:
            best_sharpe = df_copy.nlargest(10, "sharpe_ratio")
            worst_sharpe = df_copy.nsmallest(10, "sharpe_ratio")
            analysis["best_performers"]["by_sharpe"] = best_sharpe.to_dict("records")
            analysis["worst_performers"]["by_sharpe"] = worst_sharpe.to_dict("records")

        if "total_pnl" in df_copy.columns:
            best_pnl = df_copy.nlargest(10, "total_pnl")
            worst_pnl = df_copy.nsmallest(10, "total_pnl")
            analysis["best_performers"]["by_pnl"] = best_pnl.to_dict("records")
            analysis["worst_performers"]["by_pnl"] = worst_pnl.to_dict("records")

        # Thread-safe update of shared state
        with self._lock:
            self.analysis_results = analysis

        logger.info("✅ Análisis de rendimiento completado")

        return analysis

    def _analyze_by_category(
        self, df: pd.DataFrame, category_col: str, metrics: list[str]
    ) -> dict[str, Any]:
        """Analizar métricas por categoría (thread-safe with df copy)."""
        category_analysis = {}

        for category in df[category_col].dropna().unique():
            category_data = df[df[category_col] == category]
            category_analysis[category] = {}

            for metric in metrics:
                if metric in category_data.columns:
                    col = category_data[metric].dropna()
                    if len(col) > 0:
                        category_analysis[category][metric] = {
                            "mean": float(col.mean()),
                            "count": len(col),
                        }

        return category_analysis

    def detect_clusters(
        self, n_clusters: int = 3, features: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Detectar clusters de resultados similares usando KMeans.

        Args:
            n_clusters: Número de clusters
            features: Lista de features para clustering (default: métricas principales)

        Returns:
            Dict con clusters y sus características
        """
        # Check if required dependencies are available
        if not HAS_SKLEARN or KMeans is None:
            logger.warning("sklearn not available, skipping cluster detection")
            return {}

        # Thread-safe read of shared state
        with self._lock:
            if self.df_results is None or self.df_results.empty:
                logger.warning("No hay resultados para clusterizar")
                return {}

            # Make a copy to avoid holding lock during computation
            df_copy = self.df_results.copy()

        logger.info(f"🔍 Detectando {n_clusters} clusters...")

        # Features por defecto
        if features is None:
            features = [
                "sharpe_ratio",
                "total_pnl",
                "max_drawdown",
                "win_rate",
                "return_pct",
                "total_trades",
            ]

        # Filtrar features disponibles
        available_features = [f for f in features if f in df_copy.columns]

        if len(available_features) < 2:
            logger.warning(f"No hay suficientes features para clustering: {available_features}")
            return {}

        # Preparar datos
        X = df_copy[available_features].select_dtypes(include=[np.number])
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
        cluster_df["cluster"] = clusters

        # Analizar cada cluster
        cluster_analysis = {}
        for i in range(n_clusters):
            cluster_data = cluster_df[cluster_df["cluster"] == i]
            cluster_analysis[f"cluster_{i}"] = {
                "size": len(cluster_data),
                "characteristics": {
                    feature: {
                        "mean": float(cluster_data[feature].mean()),
                        "std": float(cluster_data[feature].std()),
                    }
                    for feature in available_features
                    if feature in cluster_data.columns
                },
                "indices": cluster_data.index.tolist(),
            }

        # Thread-safe update of shared state
        with self._lock:
            self.df_results["cluster"] = pd.Series(clusters, index=X.index)

        result = {
            "n_clusters": n_clusters,
            "features_used": available_features,
            "clusters": cluster_analysis,
            "inertia": float(kmeans.inertia_),
        }

        logger.info(f"✅ Clusters detectados: {n_clusters}")

        return result

    def suggest_optimal_combinations(
        self, top_n: int = 10, criteria: dict[str, float] | None = None
    ) -> list[dict[str, Any]]:
        """
        Sugerir combinaciones óptimas de parámetros o estrategias.

        Args:
            top_n: Número de sugerencias
            criteria: Dict con pesos para métricas (default: sharpe y pnl)
                     Ej: {'sharpe_ratio': 0.6, 'total_pnl': 0.4}

        Returns:
            Lista de combinaciones ordenadas por score
        """
        # Thread-safe read of shared state
        with self._lock:
            if self.df_results is None or self.df_results.empty:
                logger.warning("No hay resultados para sugerir combinaciones")
                return []

            # Make a copy to avoid holding lock during computation
            df_copy = self.df_results.copy()

        logger.info(f"💡 Sugiriendo {top_n} combinaciones óptimas...")

        # Criterios por defecto
        if criteria is None:
            criteria = {
                "sharpe_ratio": 0.4,
                "total_pnl": 0.3,
                "win_rate": 0.2,
                "max_drawdown": -0.1,  # Negativo porque queremos minimizar drawdown
            }

        # Calcular score compuesto usando operaciones vectorizadas (100-1000x más rápido)
        # VECTORIZED: Reemplazar iterrows con operaciones vectorizadas
        available_criteria = {k: v for k, v in criteria.items() if k in df_copy.columns}

        # Calcular normalizaciones vectorizadas para cada métrica
        normalized_dfs = {}
        for metric, weight in available_criteria.items():
            if weight > 0:
                max_val = df_copy[metric].max()
                normalized_dfs[metric] = df_copy[metric] / max_val if max_val > 0 else 0.0
            else:
                min_val = df_copy[metric].min()
                normalized_dfs[metric] = df_copy[metric] / abs(min_val) if min_val < 0 else 0.0

        # Calcular scores vectorizados
        scores = pd.DataFrame(index=df_copy.index)
        scores["score"] = 0.0
        for metric, weight in available_criteria.items():
            scores["score"] += normalized_dfs[metric] * abs(weight)

        # Ordenar por score y convertir a lista de dicts
        scores_sorted = scores.sort_values("score", ascending=False)
        suggestions = [
            {
                "index": idx,
                "score": scores_sorted.loc[idx, "score"],
                "row": df_copy.loc[idx].to_dict(),
            }
            for idx in scores_sorted.head(top_n).index
        ]

        logger.info(f"✅ {top_n} sugerencias generadas")
        logger.info(f"   Mejor score: {suggestions[0]['score']:.4f}")

        return [s["row"] for s in suggestions]

    def export_report(self, output_path: str | None = None, output_format: str = "json") -> str:
        """
        Exportar reporte completo de análisis.

        Args:
            output_path: Ruta de salida (default: output_dir/meta_analysis_YYYYMMDD_HHMMSS.json)
            output_format: Formato ('json' o 'csv')

        Returns:
            Ruta del archivo generado
        """
        # Thread-safe read of shared state
        with self._lock:
            if not self.analysis_results:
                logger.warning(
                    "No hay análisis para exportar. Ejecuta analyze_performance() primero."
                )
                return ""

            analysis_copy = self.analysis_results.copy()
            df_copy = self.df_results.copy() if self.df_results is not None else None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if output_path is None:
            filename = f"meta_analysis_{timestamp}.{output_format}"
            output_path = self.output_dir / filename
        else:
            output_path = Path(output_path)

        if output_format == "json":
            with open(output_path, "w") as f:
                json.dump(analysis_copy, f, indent=2, default=str)
        elif output_format == "csv" and df_copy is not None:
            df_copy.to_csv(output_path, index=False)
        else:
            logger.error(f"Formato no soportado: {output_format}")
            return ""

        logger.info(f"✅ Reporte exportado: {output_path}")

        # Generar visualizaciones si está habilitado
        if self.enable_visualizations:
            self._generate_visualizations()

        return str(output_path)

    def _generate_visualizations(self) -> None:
        """Generar visualizaciones de análisis (thread-safe)."""
        # Check if required dependencies are available
        if not HAS_MATPLOTLIB or plt is None:
            logger.warning("matplotlib not available, skipping visualizations")
            return

        # Thread-safe read of shared state
        with self._lock:
            if self.df_results is None:
                return

            # Make a copy to avoid holding lock during plotting
            df_copy = self.df_results.copy()

        logger.info("📊 Generando visualizaciones...")

        try:
            # Configurar estilo
            plt.style.use("seaborn-v0_8-darkgrid")
            if sns is not None:
                sns.set_palette("husl")

            # 1. Distribución de Sharpe Ratio
            if "sharpe_ratio" in df_copy.columns:
                _fig, ax = plt.subplots(figsize=(10, 6))
                df_copy["sharpe_ratio"].hist(bins=30, ax=ax)
                ax.set_title("Distribución de Sharpe Ratio")
                ax.set_xlabel("Sharpe Ratio")
                ax.set_ylabel("Frecuencia")
                plt.savefig(
                    self.output_dir / "sharpe_distribution.png", dpi=150, bbox_inches="tight"
                )
                plt.close()

            # 2. Scatter: Sharpe vs PnL
            if "sharpe_ratio" in df_copy.columns and "total_pnl" in df_copy.columns:
                _fig, ax = plt.subplots(figsize=(10, 6))
                scatter = ax.scatter(
                    df_copy["total_pnl"],
                    df_copy["sharpe_ratio"],
                    alpha=0.6,
                    c=df_copy.get("cluster", 0),
                    cmap="viridis",
                )
                ax.set_xlabel("Total PnL")
                ax.set_ylabel("Sharpe Ratio")
                ax.set_title("Sharpe Ratio vs Total PnL")
                plt.colorbar(scatter, ax=ax, label="Cluster")
                plt.savefig(self.output_dir / "sharpe_vs_pnl.png", dpi=150, bbox_inches="tight")
                plt.close()

            # 3. Heatmap de correlaciones
            if len(df_copy.select_dtypes(include=[np.number]).columns) > 1:
                numeric_cols = df_copy.select_dtypes(include=[np.number]).columns[:10]  # Top 10
                corr = df_copy[numeric_cols].corr()
                _fig, ax = plt.subplots(figsize=(10, 8))
                if sns is not None:
                    sns.heatmap(corr, annot=True, fmt=".2", cmap="coolwarm", center=0, ax=ax)
                else:
                    # Fallback if seaborn is not available
                    ax.imshow(corr, cmap="coolwarm", aspect="auto", vmin=-1, vmax=1)
                    ax.set_xticks(range(len(corr.columns)))
                    ax.set_yticks(range(len(corr.columns)))
                    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
                    ax.set_yticklabels(corr.columns)
                ax.set_title("Matriz de Correlaciones")
                plt.savefig(
                    self.output_dir / "correlation_heatmap.png", dpi=150, bbox_inches="tight"
                )
                plt.close()

            logger.info(f"✅ Visualizaciones guardadas en {self.output_dir}")

        except (asyncio.TimeoutError, OSError) as e:
            logger.error(f"Error generando visualizaciones: {e}", exc_info=True)

    async def run_parallel_analysis(
        self, max_workers: int = 4, include_clustering: bool = True, n_clusters: int = 3
    ) -> dict[str, Any]:
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
        async def load_data() -> None:
            await self.load_results()

        # Tareas CPU-bound (ThreadPoolExecutor)
        def analyze_cpu() -> dict[str, Any]:
            return self.analyze_performance()

        def cluster_cpu() -> dict[str, Any]:
            if include_clustering:
                return self.detect_clusters(n_clusters=n_clusters)
            return {}

        # Ejecutar carga de datos
        await load_data()

        # Ejecutar análisis CPU-bound en paralelo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(analyze_cpu): "performance",
                executor.submit(cluster_cpu): "clustering",
            }

            results = {}
            for future in as_completed(futures):
                task_name = futures[future]
                try:
                    results[task_name] = future.result()
                except (asyncio.TimeoutError, OSError) as e:
                    logger.error(f"Error en tarea {task_name}: {e}")
                    results[task_name] = {}

        # Sugerencias (usando resultados ya calculados)
        if "performance" in results:
            suggestions = self.suggest_optimal_combinations(top_n=10)
            results["suggestions"] = suggestions

        logger.info("✅ Análisis paralelo completado")

        return results
