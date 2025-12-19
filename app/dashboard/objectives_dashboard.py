"""
🎯 Dashboard de Objetivos de Backtesting
Enfocado en validación de métricas y cumplimiento de límites
"""

# CRÍTICO: Importar streamlit PRIMERO
import streamlit as st

# CRÍTICO: set_page_config DEBE ser la primera llamada a Streamlit
st.set_page_config(
    page_title="🎯 Backtesting Objectives Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# CRÍTICO: Configurar variables de entorno ANTES de imports pesados
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
os.environ.setdefault('NUMEXPR_MAX_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
if 'CUDA_VISIBLE_DEVICES' not in os.environ:
    os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Imports
try:
    from app.dashboard.comprehensive_data_loader import ComprehensiveBacktestLoader

    loader_available = True
except Exception as e:
    loader_available = False
    st.error(f"❌ Error cargando ComprehensiveBacktestLoader: {e}")

try:
    import pandas as pd
except Exception:
    pd = None
    st.error("❌ pandas no disponible")

try:
    import plotly.express as px
    import plotly.graph_objects as go

    plotly_available = True
except Exception:
    plotly_available = False

import logging

logger = logging.getLogger(__name__)

# ============================================================================
# OBJETIVOS DE MÉTRICAS
# ============================================================================

OBJECTIVES = {
    'max_drawdown': {
        'target': 20.0,
        'operator': '<',
        'description': 'Protección del capital ante rachas negativas',
        'unit': '%',
        'better_direction': 'lower',
    },
    'sharpe_ratio': {
        'target': 1.2,
        'operator': '>',
        'description': 'Buena relación retorno/riesgo',
        'unit': '',
        'better_direction': 'higher',
    },
    'sortino_ratio': {
        'target': 1.5,
        'operator': '>',
        'description': 'Minimiza penalización por pérdidas',
        'unit': '',
        'better_direction': 'higher',
    },
    'volatility': {
        'target_min': 10.0,
        'target_max': 15.0,
        'operator': 'range',
        'description': 'Control de fluctuaciones de cartera',
        'unit': '%',
        'better_direction': 'mid',
    },
    'profit_factor': {
        'target': 1.4,
        'operator': '>',
        'description': 'Ganancias por cada unidad de pérdida',
        'unit': '',
        'better_direction': 'higher',
    },
    'win_rate': {
        'target_min': 45.0,
        'target_max': 60.0,
        'operator': 'range',
        'description': 'Ideal si las ganancias promedio > pérdidas promedio',
        'unit': '%',
        'better_direction': 'mid',
    },
}


def evaluate_objective(metric_name: str, value: float) -> Tuple[bool, str]:
    """Evalúa si una métrica cumple con el objetivo."""
    if metric_name not in OBJECTIVES:
        return False, "❓ Objetivo no definido"

    obj = OBJECTIVES[metric_name]
    operator = obj.get('operator', '>')

    if operator == '>':
        passes = value > obj['target']
        target_str = f">{obj['target']}{obj['unit']}"
    elif operator == '<':
        passes = value < abs(obj['target'])  # Max drawdown es negativo
        target_str = f"<{obj['target']}{obj['unit']}"
    elif operator == 'range':
        passes = obj['target_min'] <= value <= obj['target_max']
        target_str = f"{obj['target_min']}-{obj['target_max']}{obj['unit']}"
    else:
        return False, "❓ Operador desconocido"

    status = "✅ CUMPLE" if passes else "❌ NO CUMPLE"
    return passes, f"{status} (Objetivo: {target_str})"


# ============================================================================
# HELPERS DE VISUALIZACIÓN
# ============================================================================


def render_objective_card(metric_name: str, value: float, test_name: str = ""):
    """Renderiza una tarjeta de objetivo con color verde/rojo."""
    passes, status = evaluate_objective(metric_name, value)
    obj = OBJECTIVES[metric_name]

    # Color según cumplimiento
    if passes:
        bg_color = "#10b981"  # Verde
        border_color = "#059669"
    else:
        bg_color = "#ef4444"  # Rojo
        border_color = "#dc2626"

    # Formatear valor
    unit = obj.get('unit', '')
    if unit == '%':
        display_value = f"{abs(value):.2f}%"
    else:
        display_value = f"{value:.2f}"

    metric_label = metric_name.replace('_', ' ').title()

    st.markdown(
        f"""
    <div style="
        background-color: {bg_color};
        color: white;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid {border_color};
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        <div style="font-size: 0.9rem; opacity: 0.9;">{metric_label}</div>
        <div style="font-size: 2rem; font-weight: bold; margin: 0.5rem 0;">{display_value}</div>
        <div style="font-size: 0.85rem;">{status}</div>
        <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 0.5rem;">{obj['description']}</div>
        {f'<div style="font-size: 0.7rem; opacity: 0.7; margin-top: 0.25rem;">{test_name}</div>' if test_name else ''}
    </div>
    """,
        unsafe_allow_html=True,
    )


def get_metric_value(row: pd.Series, metric_name: str) -> Optional[float]:
    """Obtiene el valor de una métrica desde una fila del DataFrame."""
    metric_map = {
        'max_drawdown': 'max_drawdown',
        'sharpe_ratio': 'sharpe_ratio',
        'sortino_ratio': 'sortino_ratio',
        'volatility': 'volatility',
        'annualized_volatility': 'volatility',  # Alias
        'profit_factor': 'profit_factor',
        'win_rate': 'win_rate',
    }

    col_name = metric_map.get(metric_name, metric_name)

    if col_name in row.index:
        value = row[col_name]
        if pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return None


# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================


def load_results() -> Optional[pd.DataFrame]:
    """Carga resultados usando el loader existente."""
    if not loader_available:
        return None

    try:
        loader = ComprehensiveBacktestLoader()
        df = loader.load_as_dataframe()

        if df is None or df.empty:
            return None

        # Normalizar nombres de columnas si es necesario
        return df
    except Exception as e:
        st.error(f"❌ Error cargando resultados: {e}")
        return None


def show_objectives_summary(df: pd.DataFrame):
    """Muestra resumen de cumplimiento de objetivos para todos los tests."""
    st.header("📊 Resumen de Cumplimiento de Objetivos")

    if df.empty:
        st.warning("⚠️ No hay resultados para mostrar")
        return

    # Evaluar cada test contra objetivos
    results_summary = []

    for idx, row in df.iterrows():
        test_name = row.get('test_name', f'Test {idx}')
        test_type = row.get('test_type', 'unknown')

        metrics_status = {}
        total_passed = 0
        total_metrics = 0

        for metric_name in OBJECTIVES.keys():
            value = get_metric_value(row, metric_name)
            if value is not None:
                passes, _ = evaluate_objective(metric_name, value)
                metrics_status[metric_name] = {'value': value, 'passes': passes}
                total_metrics += 1
                if passes:
                    total_passed += 1

        if total_metrics > 0:
            pass_rate = (total_passed / total_metrics) * 100
            results_summary.append(
                {
                    'test_name': test_name,
                    'test_type': test_type,
                    'pass_rate': pass_rate,
                    'passed': total_passed,
                    'total': total_metrics,
                    'metrics': metrics_status,
                    'row': row,
                }
            )

    # Ordenar por tasa de cumplimiento
    results_summary.sort(key=lambda x: x['pass_rate'], reverse=True)

    # Mostrar resumen
    if not results_summary:
        st.warning("⚠️ No se pudieron evaluar métricas")
        return

    # Tabs por tipo de test
    test_types = list(set([r['test_type'] for r in results_summary]))

    if len(test_types) > 1:
        tabs = st.tabs([f"📋 {t.replace('_', ' ').title()}" for t in test_types])

        for tab_idx, test_type in enumerate(test_types):
            with tabs[tab_idx]:
                show_test_type_results([r for r in results_summary if r['test_type'] == test_type])
    else:
        show_test_type_results(results_summary)


def show_test_type_results(results: List[Dict]):
    """Muestra resultados de un tipo de test específico."""
    for result in results:
        with st.expander(
            f"{'✅' if result['pass_rate'] == 100 else '⚠️' if result['pass_rate'] >= 50 else '❌'} "
            f"{result['test_name']} - {result['passed']}/{result['total']} objetivos cumplidos ({result['pass_rate']:.0f}%)",
            expanded=False,
        ):
            # Mostrar métricas en grid
            cols = st.columns(3)

            metric_idx = 0
            for metric_name, metric_data in result['metrics'].items():
                col = cols[metric_idx % 3]
                with col:
                    render_objective_card(metric_name, metric_data['value'], result['test_name'])
                metric_idx += 1


def show_best_strategies(df: pd.DataFrame):
    """Muestra las mejores estrategias que cumplen todos los objetivos."""
    st.header("🏆 Estrategias que Cumplen TODOS los Objetivos")

    if df.empty:
        st.warning("⚠️ No hay resultados")
        return

    perfect_strategies = []

    for idx, row in df.iterrows():
        all_pass = True
        metrics_values = {}

        for metric_name in OBJECTIVES.keys():
            value = get_metric_value(row, metric_name)
            if value is not None:
                passes, _ = evaluate_objective(metric_name, value)
                metrics_values[metric_name] = value
                if not passes:
                    all_pass = False
            else:
                all_pass = False  # Si falta una métrica, no cuenta como perfecto

        if all_pass:
            perfect_strategies.append(
                {
                    'test_name': row.get('test_name', f'Test {idx}'),
                    'test_type': row.get('test_type', 'unknown'),
                    'metrics': metrics_values,
                    'row': row,
                }
            )

    if not perfect_strategies:
        st.info("ℹ️ Ninguna estrategia cumple todos los objetivos actualmente")
        st.markdown("💡 Revisa las estrategias con mejor tasa de cumplimiento en el resumen")
    else:
        st.success(f"✅ {len(perfect_strategies)} estrategia(s) cumple(n) todos los objetivos")

        for strategy in perfect_strategies:
            with st.expander(f"✅ {strategy['test_name']}", expanded=False):
                cols = st.columns(3)
                metric_idx = 0
                for metric_name, value in strategy['metrics'].items():
                    col = cols[metric_idx % 3]
                    with col:
                        render_objective_card(metric_name, value, strategy['test_name'])
                    metric_idx += 1


def show_objective_comparison(df: pd.DataFrame):
    """Muestra comparación de todos los tests para cada objetivo."""
    st.header("📈 Comparación por Objetivo")

    if df.empty:
        return

    # Crear un tab por objetivo
    tabs = st.tabs([f"🎯 {m.replace('_', ' ').title()}" for m in OBJECTIVES.keys()])

    for tab_idx, metric_name in enumerate(OBJECTIVES.keys()):
        with tabs[tab_idx]:
            obj = OBJECTIVES[metric_name]

            # Obtener valores para este objetivo
            data = []
            for idx, row in df.iterrows():
                value = get_metric_value(row, metric_name)
                if value is not None:
                    passes, status = evaluate_objective(metric_name, value)
                    data.append(
                        {
                            'Test': row.get('test_name', f'Test {idx}'),
                            'Tipo': row.get('test_type', 'unknown'),
                            'Valor': value,
                            'Cumple': '✅' if passes else '❌',
                            'Status': passes,
                        }
                    )

            if not data:
                st.warning(f"⚠️ No hay datos para {metric_name}")
                continue

            # Crear DataFrame y mostrar
            comp_df = pd.DataFrame(data)

            # Ordenar por valor (mejor primero)
            if obj['better_direction'] == 'higher':
                comp_df = comp_df.sort_values('Valor', ascending=False)
            elif obj['better_direction'] == 'lower':
                comp_df = comp_df.sort_values('Valor', ascending=True)
            else:  # mid
                # Para rangos, los más cercanos al centro primero
                target_mid = (obj['target_min'] + obj['target_max']) / 2
                comp_df['distance_from_target'] = abs(comp_df['Valor'] - target_mid)
                comp_df = comp_df.sort_values('distance_from_target')

            # Mostrar gráfico
            if plotly_available:
                fig = px.bar(
                    comp_df,
                    x='Test',
                    y='Valor',
                    color='Status',
                    color_discrete_map={True: '#10b981', False: '#ef4444'},
                    title=f"{metric_name.replace('_', ' ').title()} - Comparación de Tests",
                    labels={'Valor': f"Valor ({obj.get('unit', '')})"},
                )

                # Añadir línea de objetivo
                if obj['operator'] == '>':
                    fig.add_hline(
                        y=obj['target'],
                        line_dash="dash",
                        line_color="blue",
                        annotation_text=f"Objetivo: >{obj['target']}",
                    )
                elif obj['operator'] == '<':
                    fig.add_hline(
                        y=obj['target'],
                        line_dash="dash",
                        line_color="blue",
                        annotation_text=f"Objetivo: <{obj['target']}",
                    )
                elif obj['operator'] == 'range':
                    fig.add_hline(
                        y=obj['target_min'],
                        line_dash="dash",
                        line_color="blue",
                        annotation_text=f"Min: {obj['target_min']}",
                    )
                    fig.add_hline(
                        y=obj['target_max'],
                        line_dash="dash",
                        line_color="blue",
                        annotation_text=f"Max: {obj['target_max']}",
                    )

                st.plotly_chart(fig, use_container_width=True)

            # Mostrar tabla
            st.dataframe(
                comp_df[['Test', 'Tipo', 'Valor', 'Cumple']],
                use_container_width=True,
                hide_index=True,
            )


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Función principal del dashboard."""
    try:
        # Header
        st.markdown(
            """
        <div style="text-align: center; padding: 2rem 0;">
            <h1 style="font-size: 3rem; margin-bottom: 0.5rem;">🎯 Backtesting Objectives Dashboard</h1>
            <p style="font-size: 1.2rem; color: #666;">Validación de Métricas y Cumplimiento de Límites</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Sidebar
        with st.sidebar:
            st.header("⚙️ Configuración")
            st.markdown("---")
            st.info(
                """
            **Objetivos de Métricas:**
            - Max Drawdown: < 20%
            - Sharpe Ratio: > 1.2
            - Sortino Ratio: > 1.5
            - Volatilidad: 10-15%
            - Profit Factor: > 1.4
            - Win Rate: 45-60%
            """
            )

            if st.button("🔄 Recargar Resultados", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        # Cargar resultados
        with st.spinner("📊 Cargando resultados..."):
            df = load_results()

        if df is None or df.empty:
            st.warning(
                """
            ⚠️ No se encontraron resultados de backtesting.
            
            Ejecuta algunos backtests primero:
            ```bash
            python scripts/run_comprehensive_backtest.py baseline grid_search
            ```
            """
            )
            return

        st.success(f"✅ {len(df)} resultado(s) cargado(s)")

        # Tabs principales
        tab1, tab2, tab3 = st.tabs(
            ["📊 Resumen de Objetivos", "🏆 Estrategias Perfectas", "📈 Comparación por Objetivo"]
        )

        with tab1:
            show_objectives_summary(df)

        with tab2:
            show_best_strategies(df)

        with tab3:
            show_objective_comparison(df)

    except Exception as e:
        st.error(f"❌ Error en dashboard: {e}")
        logger.exception("Error en dashboard")


if __name__ == "__main__":
    main()
