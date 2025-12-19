"""
Página Streamlit para Meta Dashboard - Control de Misión Quant
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import streamlit as st

    from app.dashboard.meta_dashboard import MetaDashboard

    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    logging.warning("Streamlit no disponible")

logger = logging.getLogger(__name__)

if STREAMLIT_AVAILABLE:
    st.set_page_config(
        page_title="Control de Misión Quant",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🎯 Control de Misión Quant")
    st.markdown("**Análisis metacognitivo y diagnóstico automático de estrategias**")
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuración")

        results_dir = st.text_input(
            "Directorio de Resultados",
            value="reports/comprehensive_backtest",
            help="Ruta al directorio con resultados de backtests",
        )

        config_path = st.text_input(
            "Archivo de Configuración (opcional)",
            value="config/backtesting/comprehensive_backtest.yaml",
            help="Ruta al YAML de configuración para cargar umbrales",
        )

        if st.button("🔄 Cargar y Analizar", type="primary"):
            with st.spinner("Cargando resultados y ejecutando análisis..."):
                try:
                    dashboard = MetaDashboard(
                        results_dir=results_dir, config_path=config_path if config_path else None
                    )

                    # Ejecutar análisis asíncrono
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Si ya hay loop, crear tarea
                            import nest_asyncio

                            nest_asyncio.apply()
                            results = loop.run_until_complete(dashboard.load_and_analyze())
                        else:
                            results = loop.run_until_complete(dashboard.load_and_analyze())
                    except RuntimeError:
                        results = asyncio.run(dashboard.load_and_analyze())

                    st.session_state['meta_dashboard'] = dashboard
                    st.success("✅ Análisis completado")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    logger.error(f"Error en análisis: {e}", exc_info=True)

    # Renderizar dashboard si está cargado
    if 'meta_dashboard' in st.session_state:
        dashboard = st.session_state['meta_dashboard']
        dashboard.render_dashboard()
    else:
        st.info("👈 Usa el sidebar para cargar y analizar resultados")
        st.markdown(
            """
        ### 📋 Instrucciones
        
        1. **Configura el directorio** con los resultados de backtests
        2. **Opcionalmente**, especifica la ruta al archivo de configuración YAML (para umbrales)
        3. **Haz clic en "Cargar y Analizar"** para ejecutar el análisis completo
        
        ### 🎯 Características
        
        - **Alert Engine**: Detecta problemas críticos automáticamente
        - **Performance Matrix**: Visualiza rendimiento por estrategia/engine
        - **Meta-Analyzer View**: Correlaciones y clusters
        - **Indicadores Avanzados**: Stability Index, Profit Consistency, etc.
        - **Volatility Context**: Overlay de volatilidad vs drawdown
        - **Drilldown Panel**: Detalles por test individual
        """
        )
