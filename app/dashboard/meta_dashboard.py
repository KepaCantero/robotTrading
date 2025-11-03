"""
Meta Dashboard - Control de Misión Quant

Dashboard avanzado con:
- Análisis metacognitivo de estrategias
- Colores dinámicos según salud del sistema
- Análisis de patrones y recomendaciones automáticas
- Visualización de regímenes de mercado
- Indicadores avanzados (Stability Index, Learning Retention, etc.)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from app.backtesting.meta_analyzer import BacktestMetaAnalyzer
from app.backtesting.meta_analyzer import AuditTrail

logger = logging.getLogger(__name__)


class MetaDashboard:
    """
    Dashboard avanzado para análisis meta de backtests.
    
    Características:
    - Meta-Analyzer View con correlaciones
    - Performance Matrix con heatmap
    - Alert Engine con colores dinámicos
    - Drilldown Panel para detalles
    - Volatility Context overlay
    - Indicadores avanzados
    """
    
    def __init__(
        self,
        results_dir: str = "reports/comprehensive_backtest",
        config_path: Optional[str] = None
    ):
        """
        Inicializar dashboard meta.
        
        Args:
            results_dir: Directorio con resultados de backtests
            config_path: Ruta a configuración YAML (para umbrales)
        """
        self.results_dir = Path(results_dir)
        self.config_path = config_path
        
        # Cargar umbrales desde configuración
        self.thresholds = self._load_thresholds()
        
        # Meta analyzer
        self.analyzer = None
        self.analysis_results = {}
        self.df_results = None
        
        logger.info(f"MetaDashboard inicializado: results_dir={results_dir}")
    
    def _load_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Cargar umbrales desde configuración YAML."""
        default_thresholds = {
            'sharpe': {'bad': 0.0, 'warn': 0.8, 'good': 1.5},
            'drawdown': {'bad': 15.0, 'warn': 10.0, 'good': 5.0},
            'winrate': {'bad': 0.4, 'warn': 0.55, 'good': 0.65},
            'return_pct': {'bad': 0.0, 'warn': 10.0, 'good': 25.0}
        }
        
        if not self.config_path:
            return default_thresholds
        
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if 'thresholds' in config:
                return config['thresholds']
        except Exception as e:
            logger.warning(f"No se pudieron cargar umbrales desde config: {e}")
        
        return default_thresholds
    
    def color_for_metric(self, value: float, metric: str) -> str:
        """
        Obtener color según valor de métrica y umbrales.
        
        Args:
            value: Valor de la métrica
            metric: Nombre de la métrica ('sharpe', 'drawdown', 'winrate', 'return_pct')
        
        Returns:
            Color: 'red', 'orange', 'yellow', 'green'
        """
        if metric not in self.thresholds:
            return 'gray'
        
        t = self.thresholds[metric]
        
        # Para drawdown, valores negativos son peores (mayor drawdown absoluto)
        if metric == 'drawdown':
            value = abs(value)  # Drawdown es negativo, convertir a absoluto
        
        if value < t['bad']:
            return 'red'
        elif value < t['warn']:
            return 'orange'
        elif value < t['good']:
            return 'yellow'
        else:
            return 'green'
    
    def emoji_for_metric(self, value: float, metric: str) -> str:
        """Obtener emoji según color."""
        color = self.color_for_metric(value, metric)
        emoji_map = {'red': '🔴', 'orange': '🟠', 'yellow': '🟡', 'green': '🟢'}
        return emoji_map.get(color, '⚪')
    
    async def load_and_analyze(self) -> Dict[str, Any]:
        """Cargar resultados y ejecutar análisis completo."""
        self.analyzer = BacktestMetaAnalyzer(
            data_dir=str(self.results_dir),
            output_dir=str(self.results_dir / "meta"),
            enable_visualizations=True
        )
        
        await self.analyzer.load_results()
        self.df_results = self.analyzer.df_results
        
        # Análisis completo
        self.analysis_results = await self.analyzer.run_parallel_analysis(
            max_workers=4,
            include_clustering=True,
            n_clusters=4
        )
        
        return self.analysis_results
    
    def render_dashboard(self) -> None:
        """Renderizar dashboard completo (para Streamlit)."""
        if not STREAMLIT_AVAILABLE:
            logger.error("Streamlit no disponible")
            return
        
        if self.df_results is None or self.df_results.empty:
            st.warning("⚠️ No hay resultados para mostrar. Ejecuta análisis primero.")
            return
        
        # Header
        st.title("🎯 Control de Misión Quant")
        st.markdown("**Análisis metacognitivo y diagnóstico automático de estrategias**")
        st.markdown("---")
        
        # 1. Alert Engine - Alertas críticas
        self._render_alert_engine()
        
        # 2. Performance Matrix
        self._render_performance_matrix()
        
        # 3. Meta-Analyzer View
        self._render_meta_analyzer_view()
        
        # 4. Indicadores Avanzados
        self._render_advanced_indicators()
        
        # 5. Volatility Context
        self._render_volatility_context()
        
        # 6. Drilldown Panel (selector)
        self._render_drilldown_panel()
    
    def _render_alert_engine(self) -> None:
        """Renderizar sistema de alertas."""
        st.subheader("🚨 Alert Engine")
        
        alerts = []
        
        for idx, row in self.df_results.iterrows():
            test_name = row.get('test_type', 'unknown')
            
            # Verificar métricas críticas
            sharpe = row.get('sharpe_ratio', 0)
            drawdown = row.get('max_drawdown', 0)
            winrate = row.get('win_rate', 0)
            
            if sharpe < self.thresholds['sharpe']['bad']:
                alerts.append({
                    'type': 'critical',
                    'test': test_name,
                    'metric': 'Sharpe Ratio',
                    'value': sharpe,
                    'message': f'Sharpe negativo: {sharpe:.2f}'
                })
            
            if abs(drawdown) > self.thresholds['drawdown']['bad']:
                alerts.append({
                    'type': 'critical',
                    'test': test_name,
                    'metric': 'Max Drawdown',
                    'value': abs(drawdown),
                    'message': f'Drawdown crítico: {abs(drawdown):.1f}%'
                })
            
            if winrate < self.thresholds['winrate']['bad']:
                alerts.append({
                    'type': 'warning',
                    'test': test_name,
                    'metric': 'Win Rate',
                    'value': winrate,
                    'message': f'Win rate bajo: {winrate:.1%}'
                })
        
        if alerts:
            for alert in alerts[:10]:  # Top 10 alertas
                emoji = '🔴' if alert['type'] == 'critical' else '🟠'
                st.markdown(
                    f"{emoji} **{alert['test']}**: {alert['message']}"
                )
        else:
            st.success("✅ No hay alertas críticas")
    
    def _render_performance_matrix(self) -> None:
        """Renderizar matriz de rendimiento (heatmap)."""
        st.subheader("📊 Performance Matrix")
        
        if 'test_type' not in self.df_results.columns:
            st.warning("No hay información de test_type para matriz")
            return
        
        # Preparar datos para matriz
        matrix_data = []
        strategies = self.df_results['test_type'].unique() if 'test_type' in self.df_results.columns else ['all']
        
        # Obtener engines únicos
        engines = []
        if 'learning_engine' in self.df_results.columns:
            engines = self.df_results['learning_engine'].dropna().unique().tolist()
        engines = engines if engines else ['baseline']
        
        for strategy in strategies:
            for engine in engines:
                subset = self.df_results[
                    (self.df_results['test_type'] == strategy) if 'test_type' in self.df_results.columns else True
                ]
                if 'learning_engine' in self.df_results.columns:
                    subset = subset[subset['learning_engine'] == engine]
                
                if not subset.empty:
                    avg_sharpe = subset['sharpe_ratio'].mean() if 'sharpe_ratio' in subset.columns else 0
                    avg_return = subset['return_pct'].mean() if 'return_pct' in subset.columns else 0
                    avg_dd = subset['max_drawdown'].mean() if 'max_drawdown' in subset.columns else 0
                    
                    matrix_data.append({
                        'Strategy': strategy,
                        'Engine': engine if engine else 'baseline',
                        'Sharpe': avg_sharpe,
                        'Return %': avg_return,
                        'Drawdown %': abs(avg_dd)
                    })
        
        if matrix_data:
            df_matrix = pd.DataFrame(matrix_data)
            
            # Pivot para heatmap
            if PLOTLY_AVAILABLE:
                # Heatmap de Sharpe
                fig = px.imshow(
                    df_matrix.pivot(index='Strategy', columns='Engine', values='Sharpe'),
                    labels=dict(x="Engine", y="Strategy", color="Sharpe Ratio"),
                    title="Performance Matrix - Sharpe Ratio",
                    color_continuous_scale='RdYlGn',
                    aspect="auto"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Tabla con colores
            st.markdown("**Matriz de Rendimiento (con indicadores de color)**")
            self._render_colored_table(df_matrix)
    
    def _render_colored_table(self, df: pd.DataFrame) -> None:
        """Renderizar tabla con colores dinámicos."""
        if not STREAMLIT_AVAILABLE:
            return
        
        # Crear HTML con colores
        html = "<table style='width:100%; border-collapse: collapse;'>"
        
        # Header
        html += "<tr>"
        for col in df.columns:
            html += f"<th style='border: 1px solid #ddd; padding: 8px;'>{col}</th>"
        html += "</tr>"
        
        # Rows
        for _, row in df.iterrows():
            html += "<tr>"
            for col in df.columns:
                value = row[col]
                
                # Determinar color según métrica
                if col in ['Sharpe', 'Return %']:
                    color = self.color_for_metric(value, 'sharpe' if col == 'Sharpe' else 'return_pct')
                elif col == 'Drawdown %':
                    color = self.color_for_metric(value, 'drawdown')
                else:
                    color = None
                
                bg_color_map = {
                    'red': '#ffcccc',
                    'orange': '#ffdd99',
                    'yellow': '#ffff99',
                    'green': '#ccffcc'
                }
                bg_color = bg_color_map.get(color, 'white')
                emoji = self.emoji_for_metric(value, col.lower().replace(' %', '').replace(' ', ''))
                
                html += f"<td style='border: 1px solid #ddd; padding: 8px; background-color: {bg_color};'>"
                html += f"{emoji} {value:.2f}" if isinstance(value, (int, float)) else f"{emoji} {value}"
                html += "</td>"
            
            html += "</tr>"
        
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)
    
    def _render_meta_analyzer_view(self) -> None:
        """Renderizar vista de meta-analyzer con correlaciones."""
        st.subheader("🔍 Meta-Analyzer View")
        
        if 'performance' not in self.analysis_results:
            st.info("Ejecuta análisis completo para ver correlaciones")
            return
        
        # Correlaciones
        if 'correlations' in self.analysis_results['performance']:
            st.markdown("**Correlaciones entre Métricas**")
            if PLOTLY_AVAILABLE and self.analyzer:
                try:
                    # Cargar heatmap de correlación generado
                    corr_path = self.results_dir / "meta" / "correlation_heatmap.png"
                    if corr_path.exists():
                        st.image(str(corr_path))
                    else:
                        st.info("Generando heatmap de correlaciones...")
                except Exception as e:
                    logger.warning(f"Error mostrando heatmap: {e}")
        
        # Clusters
        if 'clustering' in self.analysis_results and 'clusters' in self.analysis_results['clustering']:
            st.markdown("**Clusters Detectados**")
            clusters = self.analysis_results['clustering']['clusters']
            
            for cluster_name, cluster_info in clusters.items():
                with st.expander(f"{cluster_name} (Size: {cluster_info['size']})"):
                    st.json(cluster_info['characteristics'])
        
        # Sugerencias
        if 'suggestions' in self.analysis_results:
            st.markdown("**Top 10 Combinaciones Óptimas**")
            suggestions = self.analysis_results['suggestions'][:10]
            
            for i, suggestion in enumerate(suggestions, 1):
                test_type = suggestion.get('test_type', 'unknown')
                sharpe = suggestion.get('sharpe_ratio', 0)
                pnl = suggestion.get('total_pnl', 0)
                emoji = self.emoji_for_metric(sharpe, 'sharpe')
                
                st.markdown(f"{i}. {emoji} **{test_type}**: Sharpe={sharpe:.2f}, PnL=${pnl:,.2f}")
    
    def _render_advanced_indicators(self) -> None:
        """Renderizar indicadores avanzados."""
        st.subheader("🧠 Indicadores Avanzados")
        
        if self.df_results is None or self.df_results.empty:
            return
        
        # Calcular indicadores avanzados
        indicators = {}
        
        # Stability Index (correlación entre resultados consecutivos)
        if len(self.df_results) > 1 and 'sharpe_ratio' in self.df_results.columns:
            stability = self._calculate_stability_index()
            indicators['Stability Index'] = stability
        
        # Meta-Cluster Quality (silueta media)
        if 'clustering' in self.analysis_results and SKLEARN_AVAILABLE:
            cluster_quality = self._calculate_cluster_quality()
            indicators['Meta-Cluster Quality'] = cluster_quality
        
        # Profit Consistency (% días con beneficio)
        profit_consistency = self._calculate_profit_consistency()
        indicators['Profit Consistency %'] = profit_consistency
        
        # Mostrar indicadores
        cols = st.columns(len(indicators))
        for i, (name, value) in enumerate(indicators.items()):
            with cols[i]:
                st.metric(name, f"{value:.2f}" if isinstance(value, float) else value)
    
    def _calculate_stability_index(self) -> float:
        """Calcular Stability Index (correlación entre resultados consecutivos)."""
        if 'sharpe_ratio' not in self.df_results.columns:
            return 0.0
        
        sharpe_values = self.df_results['sharpe_ratio'].dropna().values
        
        if len(sharpe_values) < 2:
            return 0.0
        
        # Correlación entre valores consecutivos
        if len(sharpe_values) >= 2:
            correlation = np.corrcoef(sharpe_values[:-1], sharpe_values[1:])[0, 1]
            return float(correlation) if not np.isnan(correlation) else 0.0
        
        return 0.0
    
    def _calculate_cluster_quality(self) -> float:
        """Calcular calidad de clusters (silueta media)."""
        if not SKLEARN_AVAILABLE or 'cluster' not in self.df_results.columns:
            return 0.0
        
        features = ['sharpe_ratio', 'total_pnl', 'max_drawdown']
        available_features = [f for f in features if f in self.df_results.columns]
        
        if len(available_features) < 2:
            return 0.0
        
        X = self.df_results[available_features].select_dtypes(include=[np.number]).dropna()
        clusters = self.df_results.loc[X.index, 'cluster']
        
        if len(X) < 2 or len(set(clusters)) < 2:
            return 0.0
        
        try:
            score = silhouette_score(X, clusters)
            return float(score)
        except Exception:
            return 0.0
    
    def _calculate_profit_consistency(self) -> float:
        """Calcular % de tests con beneficio positivo."""
        if 'total_pnl' not in self.df_results.columns:
            return 0.0
        
        profitable = (self.df_results['total_pnl'] > 0).sum()
        total = len(self.df_results)
        
        return (profitable / total * 100) if total > 0 else 0.0
    
    def _render_volatility_context(self) -> None:
        """Renderizar contexto de volatilidad."""
        st.subheader("📈 Volatility Context")
        
        if self.df_results is None or self.df_results.empty:
            return
        
        if PLOTLY_AVAILABLE:
            # Gráfico overlay: Drawdown vs Volatility (si está disponible)
            if 'max_drawdown' in self.df_results.columns:
                fig = go.Figure()
                
                # Drawdown timeline (si hay timestamps)
                if 'timestamp' in self.df_results.columns:
                    # Agrupar por fecha para ver evolución
                    pass  # Implementar si hay datos temporales
                
                # Scatter: Drawdown vs Sharpe (proxy de volatilidad)
                if 'sharpe_ratio' in self.df_results.columns:
                    fig.add_trace(go.Scatter(
                        x=self.df_results['sharpe_ratio'],
                        y=abs(self.df_results['max_drawdown']),
                        mode='markers',
                        text=self.df_results.get('test_type', 'unknown'),
                        marker=dict(
                            size=10,
                            color=abs(self.df_results['max_drawdown']),
                            colorscale='RdYlGn',
                            showscale=True,
                            colorbar=dict(title="Drawdown")
                        ),
                        name="Drawdown vs Sharpe"
                    ))
                    
                    fig.update_layout(
                        title="Volatility Context: Drawdown vs Sharpe Ratio",
                        xaxis_title="Sharpe Ratio",
                        yaxis_title="Max Drawdown (%)",
                        height=400
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
    
    def _render_drilldown_panel(self) -> None:
        """Renderizar panel de drilldown (selector)."""
        st.subheader("🔎 Drilldown Panel")
        
        if self.df_results is None or self.df_results.empty:
            return
        
        # Selector de test
        test_types = self.df_results['test_type'].unique() if 'test_type' in self.df_results.columns else ['all']
        selected_test = st.selectbox("Selecciona test para ver detalles:", test_types)
        
        if selected_test:
            subset = self.df_results[
                self.df_results['test_type'] == selected_test
            ] if 'test_type' in self.df_results.columns else self.df_results
            
            if not subset.empty:
                # Mostrar detalles
                st.markdown(f"**Detalles para: {selected_test}**")
                
                # Métricas clave
                cols = st.columns(4)
                with cols[0]:
                    sharpe = subset['sharpe_ratio'].mean() if 'sharpe_ratio' in subset.columns else 0
                    emoji = self.emoji_for_metric(sharpe, 'sharpe')
                    st.metric("Sharpe Ratio", f"{emoji} {sharpe:.2f}")
                
                with cols[1]:
                    pnl = subset['total_pnl'].mean() if 'total_pnl' in subset.columns else 0
                    st.metric("Total PnL", f"${pnl:,.2f}")
                
                with cols[2]:
                    dd = subset['max_drawdown'].mean() if 'max_drawdown' in subset.columns else 0
                    emoji = self.emoji_for_metric(abs(dd), 'drawdown')
                    st.metric("Max Drawdown", f"{emoji} {abs(dd):.1f}%")
                
                with cols[3]:
                    wr = subset['win_rate'].mean() if 'win_rate' in subset.columns else 0
                    emoji = self.emoji_for_metric(wr, 'winrate')
                    st.metric("Win Rate", f"{emoji} {wr:.1%}")
                
                # Tabla completa
                st.dataframe(subset, use_container_width=True)

