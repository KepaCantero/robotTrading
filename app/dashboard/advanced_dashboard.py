"""
Advanced Visual Dashboard for AlgoTrading Backtesting
Dashboard mejorado con diseño atractivo, indicadores colorizados y configuración visual
"""

# CRÍTICO: Importar streamlit PRIMERO
import streamlit as st

# CRÍTICO: set_page_config DEBE ser la primera llamada a Streamlit
st.set_page_config(
    page_title="🎯 AlgoTrading Control Center",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

import os

# Ahora importar el resto
import sys
from pathlib import Path

# ============================================================================
# SOLUCIÓN DEFINITIVA: Configurar variables de entorno ANTES de cualquier import
# Esto previene bloqueos de threading con mutex.cc
# Debe ir ANTES de importar numpy, pandas, torch, o cualquier otra librería
# ============================================================================
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['MKL_SERVICE_FORCE_INTEL'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TORCH_USE_CUDA_DSA'] = '0'

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Importar el resto de módulos con manejo de errores
try:
    from app.dashboard.comprehensive_data_loader import ComprehensiveBacktestLoader
except Exception:
    ComprehensiveBacktestLoader = None

# No cargar aquí para evitar bloqueos - se cargará dentro de main() cuando se necesite
ComprehensiveBacktestRunner = None

# Importar librerías básicas
try:
    import yaml
except Exception:
    yaml = None

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except Exception:
    make_subplots = None
    go = None
    px = None

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from app.core.logging_config import setup_file_logging
except Exception:
    setup_file_logging = None

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# CSS custom styles
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card-bad {
        background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
    }
    .metric-card-warn {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    .metric-card-good {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    .metric-card-excellent {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
</style>
""",
    unsafe_allow_html=True,
)


def load_thresholds(config_path: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    """Cargar thresholds desde configuración."""
    default = {
        'sharpe': {'bad': 0.0, 'warn': 0.8, 'good': 1.5},
        'drawdown': {'bad': 15.0, 'warn': 10.0, 'good': 5.0},
        'winrate': {'bad': 0.4, 'warn': 0.55, 'good': 0.65},
        'return_pct': {'bad': 0.0, 'warn': 10.0, 'good': 25.0},
    }

    if not config_path:
        return default

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if 'thresholds' in config:
            return config['thresholds']
    except Exception as e:
        logger.warning(f"No se pudieron cargar thresholds: {e}")

    return default


def get_metric_color(value: float, metric: str, thresholds: Dict) -> Tuple[str, str]:
    """
    Obtener color y emoji para métrica.
    Returns: (color_class, emoji)
    """
    if metric not in thresholds:
        return "metric-card", "📊"

    t = thresholds[metric]
    if value >= t['good']:
        return "metric-card-excellent", "🟢"
    elif value >= t['warn']:
        return "metric-card-good", "🟡"
    elif value >= t['bad']:
        return "metric-card-warn", "🟠"
    else:
        return "metric-card-bad", "🔴"


def render_metric_card(
    label: str, value: Any, metric: str, thresholds: Dict, format_str: str = "{:.2f}"
):
    """Renderizar card de métrica con color dinámico."""
    try:
        value_float = float(value)
    except (ValueError, TypeError):
        value_float = 0.0

    color_class, emoji = get_metric_color(value_float, metric, thresholds)

    if isinstance(value, (int, float)):
        if metric == 'return_pct' or metric == 'drawdown':
            display_value = f"{value_float:.2f}%"
        elif metric == 'winrate':
            display_value = f"{value_float:.1f}%"
        else:
            display_value = format_str.format(value_float)
    else:
        display_value = str(value)

    st.markdown(
        """
    <div class="metric-card {color_class}">
        <div style="font-size: 0.9rem; opacity: 0.9; margin-bottom: 0.5rem;">{label}</div>
        <div style="font-size: 2rem; font-weight: bold;">{emoji} {display_value}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ============================================================================
# INTEGRATION TEST OBJECTIVES - Objetivos de Métricas para Integration Tests
# ============================================================================


def get_integration_test_objectives() -> Dict[str, Dict[str, Any]]:
    """
    Define los objetivos de métricas para integration tests.
    Returns: Dict con objetivos por métrica
    """
    return {
        'max_drawdown': {
            'target': 20.0,  # < 20%
            'operator': '<',
            'description': 'Protección del capital ante rachas negativas',
            'unit': '%',
        },
        'sharpe_ratio': {
            'target': 1.2,  # > 1.2
            'operator': '>',
            'description': 'Buena relación retorno/riesgo',
            'unit': '',
        },
        'sortino_ratio': {
            'target': 1.5,  # > 1.5
            'operator': '>',
            'description': 'Minimiza penalización por pérdidas',
            'unit': '',
        },
        'annualized_volatility': {
            'target_min': 10.0,  # 10-15%
            'target_max': 15.0,
            'operator': 'range',
            'description': 'Control de fluctuaciones de cartera',
            'unit': '%',
        },
        'profit_factor': {
            'target': 1.4,  # > 1.4
            'operator': '>',
            'description': 'Ganancias por cada unidad de pérdida',
            'unit': '',
        },
        'win_rate': {
            'target_min': 45.0,  # 45-60%
            'target_max': 60.0,
            'operator': 'range',
            'description': 'Ideal si las ganancias promedio > pérdidas promedio',
            'unit': '%',
        },
    }


def evaluate_objective(metric_name: str, value: float, objectives: Dict) -> Tuple[bool, str]:
    """
    Evalúa si una métrica cumple con el objetivo.
    Returns: (passes, status_message)
    """
    if metric_name not in objectives:
        return False, "Objetivo no definido"

    obj = objectives[metric_name]
    operator = obj.get('operator', '>')

    if operator == '>':
        passes = value > obj['target']
        status = "✅ CUMPLE" if passes else "❌ NO CUMPLE"
    elif operator == '<':
        passes = value < obj['target']
        status = "✅ CUMPLE" if passes else "❌ NO CUMPLE"
    elif operator == 'range':
        passes = obj['target_min'] <= value <= obj['target_max']
        status = "✅ CUMPLE" if passes else "❌ NO CUMPLE"
    else:
        return False, "Operador desconocido"

    return passes, status


def evaluate_all_objectives(
    metrics: Dict[str, float], objectives: Dict
) -> Dict[str, Tuple[bool, str, Dict]]:
    """
    Evalúa todas las métricas contra sus objetivos.
    Returns: Dict[metric_name] = (passes, status_message, objective_config)
    """
    results = {}

    for metric_name, objective_config in objectives.items():
        # Map metric names to actual column names
        metric_map = {
            'max_drawdown': 'max_drawdown',
            'sharpe_ratio': 'sharpe_ratio',
            'sortino_ratio': 'sortino_ratio',
            'annualized_volatility': 'volatility',  # Might need adjustment
            'profit_factor': 'profit_factor',
            'win_rate': 'win_rate',
        }

        actual_metric = metric_map.get(metric_name, metric_name)

        if actual_metric in metrics:
            value = float(metrics[actual_metric])
            # Handle abs for max_drawdown (it's negative)
            if metric_name == 'max_drawdown':
                value = abs(value)
            # Handle percentage for win_rate
            if metric_name == 'win_rate' and value <= 1.0:
                value = value * 100

            passes, status = evaluate_objective(metric_name, value, objectives)
            results[metric_name] = (passes, status, objective_config)
        else:
            results[metric_name] = (False, "⚠️ Métrica no disponible", objective_config)

    return results


def extract_strategy_config(result_row: pd.Series) -> Dict[str, Any]:
    """
    Extrae la configuración de estrategia y parámetros de un resultado.
    Returns: Dict con información de estrategia, parámetros, módulos, etc.
    """
    config = {
        'test_name': result_row.get('test_name', 'Unknown'),
        'test_type': result_row.get('test_type', 'Unknown'),
        'strategy': result_row.get('strategy', 'Unknown'),
        'learning_engine': result_row.get('learning_engine', None),
        'modules_active': result_row.get('modules_active', []),
        'parameters': {},
    }

    # Try to extract parameters from different sources
    if 'parameters' in result_row and isinstance(result_row['parameters'], dict):
        config['parameters'] = result_row['parameters']
    elif 'parameters' in result_row and isinstance(result_row['parameters'], str):
        try:
            import ast

            config['parameters'] = ast.literal_eval(result_row['parameters'])
        except BaseException:
            pass

    # Extract threshold information if available
    if 'thresholds' in result_row:
        if isinstance(result_row['thresholds'], dict):
            config['thresholds'] = result_row['thresholds']
        elif isinstance(result_row['thresholds'], str):
            try:
                import ast

                config['thresholds'] = ast.literal_eval(result_row['thresholds'])
            except BaseException:
                pass

    return config


def main():
    """Dashboard principal."""
    try:
        logger.debug("🚀 Dashboard main() iniciado")

        # Header
        st.markdown(
            '<div class="main-header">🎯 AlgoTrading Control Center</div>', unsafe_allow_html=True
        )
        st.markdown(
            "### <div style='text-align: center; color: #666;'>Mission Control for Quantitative Trading</div>",
            unsafe_allow_html=True,
        )

        # EXECUTE BUTTON AT THE TOP
        st.markdown("---")
        col_exec1, col_exec2, col_exec3 = st.columns([1, 2, 1])
        with col_exec2:
            execute_button_top = st.button(
                "🚀 EXECUTE SELECTED TESTS", type="primary", key="execute_button_top"
            )
        st.markdown("---")

        # Quick status indicator (con try-catch más robusto)
        try:
            loader = ComprehensiveBacktestLoader()
            # Mostrar información de depuración
            with st.expander("🔍 Debug: Información de carga de resultados", expanded=False):
                st.write(f"📁 Buscando en: `{loader.results_dir}`")
                st.write(f"📁 Directorio existe: {loader.results_dir.exists()}")

                # Verificar si hay archivos JSON en el directorio
                if loader.results_dir.exists():
                    json_files = list(loader.results_dir.rglob("*.json"))
                    st.write(f"📁 Archivos JSON encontrados: {len(json_files)}")
                    if json_files:
                        st.write("📁 Archivos:")
                        for f in json_files[:10]:
                            st.write(f"  - {f.relative_to(loader.results_dir)}")
                else:
                    st.write("📁 El directorio no existe aún (se creará cuando ejecutes tests)")

                # Intentar cargar resultados
                all_results = loader.load_all_results()
                st.write(f"📊 Resultados cargados: {len(all_results)}")

                # Mostrar estadísticas
                stats = loader.get_summary_stats()
                if stats['total_tests'] > 0:
                    st.success(f"✅ {stats['total_tests']} backtest results disponibles")
                    st.json(stats)
                else:
                    st.info("ℹ️ No hay resultados aún. Esto es normal si no has ejecutado tests.")
                    st.write("💡 Para generar resultados:")
                    st.write("1. Selecciona tests en el sidebar")
                    st.write("2. Selecciona learning engines (opcional)")
                    st.write("3. Haz clic en '🚀 EXECUTE SELECTED TESTS'")

            stats = loader.get_summary_stats()
            if stats['total_tests'] > 0:
                st.success(f"📊 {stats['total_tests']} backtest results available")
            else:
                st.info(
                    "ℹ️ No backtest results yet. Configure tests in the sidebar and click EXECUTE."
                )
        except Exception as e:
            logger.debug(f"Could not load initial stats: {e}")
            # Don't show error to user, just continue
            st.info("ℹ️ Ready to execute tests. Configure in the sidebar.")

        # Load configuration
        config_path = project_root / "config" / "backtesting" / "comprehensive_backtest.yaml"
        thresholds = load_thresholds(str(config_path) if config_path.exists() else None)

        # Initialize session state
        if "backtest_config" not in st.session_state:
            st.session_state.backtest_config = {}
        if "results_loaded" not in st.session_state:
            st.session_state.results_loaded = False
        if "df_results" not in st.session_state:
            st.session_state.df_results = pd.DataFrame()
        if "execute_tests" not in st.session_state:
            st.session_state.execute_tests = False

        # Sidebar - Configuration
        with st.sidebar:
            st.header("⚙️ Configuration Center")

            # Strategy Mode Selector
            st.subheader("🎯 Strategy Mode")

            strategy_mode = st.radio(
                "Select Strategy Execution Mode",
                options=["Simple Strategy", "Multi-Strategy"],
                index=0,
                key="strategy_mode",
                help="Simple Strategy: Test individual strategies. Multi-Strategy: Test multiple strategies simultaneously with capital allocation.",
            )

            use_multi_strategy = strategy_mode == "Multi-Strategy"

            if use_multi_strategy:
                st.info(
                    "🔄 Multi-Strategy mode: Testing multiple strategies with dynamic capital allocation"
                )
            else:
                st.info("📊 Simple Strategy mode: Testing individual strategies")

            st.divider()

            # Learning Engines Configuration (ALWAYS VISIBLE, NOT IN EXPANDER)
            st.subheader("🧠 Learning Engines")

            col_le1, col_le2 = st.columns(2)

            with col_le1:
                enable_supervised = st.checkbox(
                    "Supervised Learning",
                    value=True,
                    key="enable_supervised",
                    help="Random Forest, XGBoost (scikit-learn)",
                )

                enable_deep = st.checkbox(
                    "Deep Learning",
                    value=False,
                    key="enable_deep",
                    help="Neural Networks (PyTorch/TensorFlow)",
                )

            with col_le2:
                enable_reinforcement = st.checkbox(
                    "Reinforcement Learning",
                    value=False,
                    key="enable_reinforcement",
                    help="PPO, A2C (stable-baselines3)",
                )

                enable_transformer = st.checkbox(
                    "Transformer",
                    value=False,
                    key="enable_transformer",
                    help="Attention-based (PyTorch)",
                )

            # Show selection summary
            selected_learning_engines = []
            if enable_supervised:
                selected_learning_engines.append("supervised")
            if enable_deep:
                selected_learning_engines.append("deep")
            if enable_reinforcement:
                selected_learning_engines.append("reinforcement")
            if enable_transformer:
                selected_learning_engines.append("transformer")

            if selected_learning_engines:
                st.caption(f"✅ Selected: {', '.join(selected_learning_engines)}")
            else:
                st.caption("ℹ️ No learning engines selected (Baseline only)")

            st.divider()

            # Define available tests based on strategy mode (fuera del expander para acceso global)
            if use_multi_strategy:
                available_tests = {
                    "Multi-Strategy Baseline": "multi_strategy",
                    "Monte Carlo": "monte_carlo",
                    "Grid Search": "grid_search",
                    "Walk Forward": "walk_forward",
                    "Out of Sample": "out_of_sample",
                    "Regime Test": "regime_test",
                }
            else:
                available_tests = {
                    "Baseline": "baseline",
                    "Learning Engines": "learning_engines",
                    "Monte Carlo": "monte_carlo",
                    "Grid Search": "grid_search",
                    "Ablation Study": "ablation",
                    "Walk Forward": "walk_forward",
                    "Out of Sample": "out_of_sample",
                    "Regime Test": "regime_test",
                    "Transformer Optimization": "transformer_optimization",
                }

            # Guardar en session_state para acceso posterior
            st.session_state['available_tests'] = available_tests

            # Test Selector (COLLAPSIBLE)
            with st.expander("📋 Select Tests to Execute", expanded=True):
                selected_tests = []

                # Organize in columns for better layout
                num_tests = len(available_tests)
                cols_per_row = 2

                test_items = list(available_tests.items())
                for i in range(0, num_tests, cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, (display_name, test_name) in enumerate(test_items[i: i + cols_per_row]):
                        with cols[j]:
                            checkbox_key = f"test_{test_name}_{use_multi_strategy}"
                            checkbox_value = st.checkbox(
                                display_name,
                                value=st.session_state.get(checkbox_key, False),
                                key=checkbox_key,
                            )
                            # El valor ya está en session_state automáticamente gracias al key
                            if checkbox_value:
                                selected_tests.append(test_name)

                # Auto-seleccionar test "learning_engines" si hay learning engines seleccionados
                if selected_learning_engines and "learning_engines" not in selected_tests:
                    selected_tests.append("learning_engines")
                    st.success(
                        "✅ Test 'Learning Engines' agregado automáticamente (hay learning engines seleccionados)"
                    )
                    st.info(
                        "💡 El test 'Learning Engines' se ejecutará automáticamente cuando hay learning engines seleccionados"
                    )

                # Guardar selected_tests en session_state para acceso fuera del expander
                st.session_state['selected_tests_sidebar'] = selected_tests

                # If multi-strategy mode, ensure multi_strategy test is
                # available
                if use_multi_strategy:
                    if selected_tests and "multi_strategy" not in selected_tests:
                        st.info("💡 Tip: 'Multi-Strategy Baseline' recommended")

            st.divider()

            # Execution Parameters (COLLAPSIBLE)
            with st.expander("🚀 Execution Parameters", expanded=True):
                symbol = st.text_input("Symbol", value="SNOW", key="symbol")

                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "Start Date", value=datetime.now() - timedelta(days=365), key="start_date"
                    )
                with col2:
                    end_date = st.date_input(
                        "End Date", value=datetime.now() - timedelta(days=1), key="end_date"
                    )

                initial_capital = st.number_input(
                    "Initial Capital ($)",
                    min_value=1000,
                    value=100000,
                    step=10000,
                    key="initial_capital",
                )

            # Multi-Strategy Configuration (only if multi-strategy mode is
            # selected, COLLAPSIBLE)
            if use_multi_strategy:
                st.divider()
                with st.expander("🔄 Multi-Strategy Settings", expanded=False):
                    strategies_to_use = st.multiselect(
                        "Select Strategies",
                        options=["momentum", "mean_reversion", "pairs_trading"],
                        default=["momentum", "mean_reversion", "pairs_trading"],
                        key="multi_strategy_selection",
                    )

                    enable_dynamic_reallocation = st.checkbox(
                        "Dynamic Capital Reallocation",
                        value=True,
                        key="enable_dynamic_reallocation",
                        help="Automatically reallocate capital based on performance",
                    )

                    if enable_dynamic_reallocation:
                        reallocation_frequency = st.number_input(
                            "Reallocation Frequency (days)",
                            min_value=1,
                            max_value=90,
                            value=30,
                            key="reallocation_frequency",
                        )

                    if strategies_to_use:
                        st.success(f"✅ Strategies: {', '.join(strategies_to_use)}")

            st.divider()

            # Advanced Settings (COLLAPSIBLE)
            with st.expander("⚙️ Advanced Settings", expanded=False):
                enable_parallel = st.checkbox(
                    "Enable Parallelization", value=True, key="enable_parallel"
                )
                max_workers = st.number_input(
                    "Max Workers",
                    min_value=1,
                    max_value=16,
                    value=4,
                    disabled=not enable_parallel,
                    key="max_workers",
                )
                enable_meta_analysis = st.checkbox(
                    "Enable Meta Analysis", value=True, key="enable_meta_analysis"
                )
                enable_incremental_learning = st.checkbox(
                    "Enable Incremental Learning", value=True, key="enable_incremental_learning"
                )

            st.divider()

            # Threshold Configuration (COLLAPSIBLE)
            with st.expander("🎨 Color Thresholds", expanded=False):
                st.write("**Sharpe Ratio**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    sharpe_bad = st.number_input(
                        "Bad", value=thresholds['sharpe']['bad'], key="sharpe_bad", format="%.2"
                    )
                with col2:
                    sharpe_warn = st.number_input(
                        "Warn", value=thresholds['sharpe']['warn'], key="sharpe_warn", format="%.2"
                    )
                with col3:
                    sharpe_good = st.number_input(
                        "Good", value=thresholds['sharpe']['good'], key="sharpe_good", format="%.2"
                    )

                st.write("**Max Drawdown (%)**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    dd_bad = st.number_input(
                        "Bad", value=thresholds['drawdown']['bad'], key="dd_bad", format="%.2"
                    )
                with col2:
                    dd_warn = st.number_input(
                        "Warn", value=thresholds['drawdown']['warn'], key="dd_warn", format="%.2"
                    )
                with col3:
                    dd_good = st.number_input(
                        "Good", value=thresholds['drawdown']['good'], key="dd_good", format="%.2"
                    )

                st.write("**Win Rate (%)**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    wr_bad = st.number_input(
                        "Bad", value=thresholds['winrate']['bad'] * 100, key="wr_bad", format="%.1"
                    )
                with col2:
                    wr_warn = st.number_input(
                        "Warn",
                        value=thresholds['winrate']['warn'] * 100,
                        key="wr_warn",
                        format="%.1",
                    )
                with col3:
                    wr_good = st.number_input(
                        "Good",
                        value=thresholds['winrate']['good'] * 100,
                        key="wr_good",
                        format="%.1",
                    )

                st.write("**Return (%)**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    ret_bad = st.number_input(
                        "Bad", value=thresholds['return_pct']['bad'], key="ret_bad", format="%.2"
                    )
                with col2:
                    ret_warn = st.number_input(
                        "Warn",
                        value=thresholds['return_pct']['warn'],
                        key="ret_warn",
                        format="%.2",
                    )
                with col3:
                    ret_good = st.number_input(
                        "Good",
                        value=thresholds['return_pct']['good'],
                        key="ret_good",
                        format="%.2",
                    )

            # Update thresholds (inside sidebar, using sidebar variables)
            thresholds = {
                'sharpe': {'bad': sharpe_bad, 'warn': sharpe_warn, 'good': sharpe_good},
                'drawdown': {'bad': dd_bad, 'warn': dd_warn, 'good': dd_good},
                'winrate': {'bad': wr_bad / 100, 'warn': wr_warn / 100, 'good': wr_good / 100},
                'return_pct': {'bad': ret_bad, 'warn': ret_warn, 'good': ret_good},
            }

            st.divider()

            # Execute Button (also check top button)
            execute_button_sidebar = st.button(
                "🚀 EXECUTE",
                type="secondary",
                use_container_width=True,
                key="execute_button_sidebar",
            )

            if execute_button_sidebar:
                st.session_state.execute_button_sidebar_clicked = True

            # Check if execute button was clicked
            button_clicked = execute_button_top or st.session_state.get(
                'execute_button_sidebar_clicked', False
            )
            logger.debug(
                f"🔍 Botón ejecutar: top={execute_button_top}, sidebar={st.session_state.get('execute_button_sidebar_clicked', False)}"
            )

            if button_clicked:
                logger.info("🔘 Botón EXECUTE presionado")
                # Reset flag
                if st.session_state.get('execute_button_sidebar_clicked'):
                    st.session_state.execute_button_sidebar_clicked = False

                # Obtener selected_tests desde session_state si no está disponible localmente
                if not selected_tests:
                    selected_tests = st.session_state.get('selected_tests_sidebar', [])

                # Reconstruir selected_tests desde checkboxes en session_state si aún está vacío
                if not selected_tests:
                    selected_tests = []
                    # Usar available_tests desde session_state como respaldo
                    tests_to_check = (
                        available_tests
                        if 'available_tests' not in st.session_state
                        else st.session_state.get('available_tests', available_tests)
                    )
                    for display_name, test_name in tests_to_check.items():
                        checkbox_key = f"test_{test_name}_{use_multi_strategy}"
                        if st.session_state.get(checkbox_key, False):
                            selected_tests.append(test_name)

                logger.info(f"📋 Tests seleccionados: {selected_tests}")
                logger.info(f"📋 Learning engines seleccionados: {selected_learning_engines}")

                # Debug: Mostrar qué se está capturando
                with st.expander("🔍 Debug: Información de ejecución", expanded=False):
                    st.write(f"**Tests seleccionados:** {selected_tests}")
                    st.write(f"**Learning engines:** {selected_learning_engines}")

                if not selected_tests:
                    st.error(
                        "❌ No hay tests seleccionados. Por favor, selecciona al menos un test antes de ejecutar."
                    )
                    st.info(
                        "💡 Tip: Ve a '📋 Select Tests to Execute' en el sidebar y marca los tests que deseas ejecutar."
                    )
                    logger.warning("⚠️ No hay tests seleccionados para ejecutar")
                else:
                    st.session_state.execute_tests = True
                    st.session_state.selected_tests = selected_tests
                    st.info(
                        f"✅ {len(selected_tests)} test(s) seleccionados. Preparando ejecución..."
                    )
                    logger.info(f"✅ {len(selected_tests)} test(s) preparados para ejecutar")

                    # Build execution params
                    execution_params = {
                        'symbol': symbol,
                        'start_date': start_date,
                        'end_date': end_date,
                        'initial_capital': initial_capital,
                        'parallel': enable_parallel,
                        'max_workers': max_workers if enable_parallel else None,
                        'meta_analysis': enable_meta_analysis,
                        'incremental_learning': enable_incremental_learning,
                        'use_multi_strategy': use_multi_strategy,
                    }

                    # Add multi-strategy specific params if in multi-strategy
                    # mode
                    if use_multi_strategy:
                        execution_params['strategies'] = st.session_state.get(
                            'multi_strategy_selection',
                            ["momentum", "mean_reversion", "pairs_trading"],
                        )
                        execution_params['enable_dynamic_reallocation'] = st.session_state.get(
                            'enable_dynamic_reallocation', True
                        )
                        if execution_params['enable_dynamic_reallocation']:
                            execution_params['reallocation_frequency'] = st.session_state.get(
                                'reallocation_frequency', 30
                            )

                    # Add learning engines configuration
                    learning_engines = []
                    if st.session_state.get('enable_supervised', False):
                        learning_engines.append('supervised')
                    if st.session_state.get('enable_deep', False):
                        learning_engines.append('deep')
                    if st.session_state.get('enable_reinforcement', False):
                        learning_engines.append('reinforcement')
                    if st.session_state.get('enable_transformer', False):
                        learning_engines.append('transformer')

                    execution_params['learning_engines'] = learning_engines

                    st.session_state.execution_params = execution_params

        # Main Content Area (outside sidebar)
        tabs = st.tabs(
            [
                "📊 Dashboard",
                "📈 Individual Results",
                "🎓 Training Analysis",
                "💾 Saved Configs",
                "🎯 Integration Objectives",
                "🔍 Comparison",
                "📁 Load Results",
            ]
        )

        # Tab 1: Dashboard Overview
        with tabs[0]:
            st.header("📊 Mission Control Dashboard")

            # Load existing results
            try:
                # Use cached results if available
                if 'df_results' in st.session_state and not st.session_state.df_results.empty:
                    df_results = st.session_state.df_results
                    stats = {'total_tests': len(df_results)}
                else:
                    # Load fresh if not in session state
                    loader = ComprehensiveBacktestLoader()
                    stats = loader.get_summary_stats()
                    df_results = loader.load_as_dataframe()

                    # Verificar y loggear datos de learning engines
                    if not df_results.empty:
                        learning_engine_results = df_results[
                            df_results['test_type'] == 'learning_engine'
                        ]
                        if not learning_engine_results.empty:
                            # Contar cuántos tienen datos de training
                            has_before = learning_engine_results.apply(
                                lambda row: bool(row.get('before_training_metrics')), axis=1
                            ).sum()
                            has_after = learning_engine_results.apply(
                                lambda row: bool(row.get('after_training_metrics')), axis=1
                            ).sum()
                            has_improvement = learning_engine_results.apply(
                                lambda row: bool(row.get('improvement_pct')), axis=1
                            ).sum()

                            logger.info(
                                f"📊 Learning Engines cargados: {len(learning_engine_results)} resultados - "
                                f"Antes: {has_before}, Después: {has_after}, Mejora: {has_improvement}"
                            )

                    # Store in session state
                    if not df_results.empty:
                        st.session_state.df_results = df_results
                        st.session_state.results_loaded = True

                if not df_results.empty:
                    st.session_state.results_loaded = True
                    st.session_state.df_results = df_results

                    # KPI Cards
                    st.subheader("🎯 Key Performance Indicators")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        best_sharpe = (
                            df_results['sharpe_ratio'].max()
                            if 'sharpe_ratio' in df_results.columns
                            else 0
                        )
                        render_metric_card("Best Sharpe Ratio", best_sharpe, "sharpe", thresholds)

                    with col2:
                        best_return = (
                            df_results['return_pct'].max()
                            if 'return_pct' in df_results.columns
                            else 0
                        )
                        render_metric_card("Best Return", best_return, "return_pct", thresholds)

                    with col3:
                        avg_winrate = (
                            df_results['win_rate'].mean() if 'win_rate' in df_results.columns else 0
                        )
                        render_metric_card("Avg Win Rate", avg_winrate, "winrate", thresholds)

                    with col4:
                        min_drawdown = (
                            abs(df_results['max_drawdown'].min())
                            if 'max_drawdown' in df_results.columns
                            else 0
                        )
                        render_metric_card("Worst Drawdown", min_drawdown, "drawdown", thresholds)

                    st.divider()

                    # Learning Engines Status Indicator
                    learning_engine_results = (
                        df_results[df_results['test_type'] == 'learning_engine']
                        if 'test_type' in df_results.columns
                        else pd.DataFrame()
                    )
                    if not learning_engine_results.empty:
                        # Contar cuántos tienen datos completos
                        complete_count = 0
                        for idx, row in learning_engine_results.iterrows():
                            before = row.get('before_training_metrics')
                            after = row.get('after_training_metrics')
                            if (isinstance(before, dict) and len(before) > 0) or (
                                isinstance(before, str) and before not in ['nan', '', 'None', '{}']
                            ):
                                if (isinstance(after, dict) and len(after) > 0) or (
                                    isinstance(after, str)
                                    and after not in ['nan', '', 'None', '{}']
                                ):
                                    complete_count += 1

                        if complete_count > 0:
                            st.success(
                                "🎓 **Learning Engines Analysis Available:** "
                                f"{complete_count} de {len(learning_engine_results)} tienen datos completos "
                                "(antes/después del entrenamiento). "
                                "Ve a la tab '🎓 Training Analysis' para ver detalles."
                            )
                        else:
                            st.info(
                                f"ℹ️ **Learning Engines:** {len(learning_engine_results)} resultados encontrados, "
                                "pero sin datos de comparación. Ejecuta nuevos tests para ver análisis de entrenamiento."
                            )

                    # Top Performers
                    st.subheader("🏆 Top Performers")

                    if 'sharpe_ratio' in df_results.columns:
                        top_5 = df_results.nlargest(5, 'sharpe_ratio')

                        for idx, row in top_5.iterrows():
                            test_name_safe = (
                                str(row.get('test_name', f'Test_{idx}'))
                                .replace(' ', '_')
                                .replace('/', '_')[:50]
                            )
                            with st.container(key=f"top_performer_{test_name_safe}_{idx}"):
                                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

                                with col1:
                                    st.write(f"**{row.get('test_name', 'Unknown')}**")
                                    st.caption(f"Type: {row.get('test_type', 'N/A')}")

                                with col2:
                                    render_metric_card(
                                        "Sharpe", row.get('sharpe_ratio', 0), "sharpe", thresholds
                                    )

                                with col3:
                                    render_metric_card(
                                        "Return", row.get('return_pct', 0), "return_pct", thresholds
                                    )

                                with col4:
                                    render_metric_card(
                                        "Win Rate", row.get('win_rate', 0), "winrate", thresholds
                                    )

                                with col5:
                                    render_metric_card(
                                        "DD",
                                        abs(row.get('max_drawdown', 0)),
                                        "drawdown",
                                        thresholds,
                                    )

                                st.divider()

                    # Performance Distribution Charts
                    st.subheader("📊 Performance Distribution")

                    col1, col2 = st.columns(2)

                    with col1:
                        if 'sharpe_ratio' in df_results.columns:
                            fig_sharpe = px.histogram(
                                df_results,
                                x='sharpe_ratio',
                                nbins=20,
                                title='Sharpe Ratio Distribution',
                                labels={'sharpe_ratio': 'Sharpe Ratio', 'count': 'Frequency'},
                                color_discrete_sequence=['#667eea'],
                            )
                            fig_sharpe.update_layout(showlegend=False)
                            st.plotly_chart(
                                fig_sharpe, width='stretch', key="dashboard_sharpe_dist"
                            )

                    with col2:
                        if 'return_pct' in df_results.columns:
                            fig_return = px.histogram(
                                df_results,
                                x='return_pct',
                                nbins=20,
                                title='Return % Distribution',
                                labels={'return_pct': 'Return (%)', 'count': 'Frequency'},
                                color_discrete_sequence=['#764ba2'],
                            )
                            fig_return.update_layout(showlegend=False)
                            st.plotly_chart(
                                fig_return, width='stretch', key="dashboard_return_dist"
                            )
                else:
                    st.info(
                        "📋 No hay resultados cargados. Ejecuta tests o carga resultados existentes."
                    )
                    st.markdown(
                        """
                    **💡 Para empezar:**
                    1. Ve al sidebar y selecciona tests (Baseline, Learning Engines, etc.)
                    2. Activa los learning engines que quieras probar
                    3. Haz clic en "🚀 EXECUTE SELECTED TESTS" (arriba o en el sidebar)
                    4. O carga resultados existentes desde la tab "📁 Load Results"
                    """
                    )
            except Exception as e:
                st.error(f"❌ Error cargando resultados: {e}")
                st.exception(e)
                logger.error(f"Error en dashboard: {e}", exc_info=True)

            # Show helpful message even on error
            st.markdown(
                """
            **🔧 Solución:**
            1. Verifica que el directorio `reports/comprehensive_backtest` existe
            2. Ejecuta algunos backtests primero desde el sidebar
            3. O carga resultados desde la tab "📁 Load Results"
            """
            )

        # Tab 2: Individual Results
        with tabs[1]:
            st.header("📈 Individual Results")

            if st.session_state.get('results_loaded') and 'df_results' in st.session_state:
                df = st.session_state.df_results

                # Filter options
                col1, col2, col3 = st.columns(3)
                with col1:
                    test_type_filter = st.selectbox(
                        "Filter by Test Type",
                        options=(
                            ['All'] + list(df['test_type'].unique())
                            if 'test_type' in df.columns
                            else ['All']
                        ),
                        key="test_type_filter",
                    )

                with col2:
                    sort_by = st.selectbox(
                        "Sort by",
                        options=[
                            'sharpe_ratio',
                            'return_pct',
                            'win_rate',
                            'max_drawdown',
                            'total_pnl',
                        ],
                        key="sort_by",
                    )

                with col3:
                    limit_results = st.number_input(
                        "Show Top N", min_value=5, max_value=100, value=20
                    )

                # Filter and sort
                df_filtered = df.copy()
                if test_type_filter != 'All' and 'test_type' in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered['test_type'] == test_type_filter]

                if sort_by in df_filtered.columns:
                    df_filtered = df_filtered.nlargest(limit_results, sort_by)

                # Display results
                for idx, row in df_filtered.iterrows():
                    test_name_safe = (
                        str(row.get('test_name', f'Test_{idx}'))
                        .replace(' ', '_')
                        .replace('/', '_')[:50]
                    )
                    expander_key = f"individual_result_{test_name_safe}_{idx}"

                    with st.expander(f"📊 {row.get('test_name', f'Test {idx}')}", expanded=False):
                        col1, col2 = st.columns([2, 3])

                        with col1:
                            st.subheader("Key Metrics")
                            col_m1, col_m2 = st.columns(2)

                            with col_m1:
                                render_metric_card(
                                    "Sharpe", row.get('sharpe_ratio', 0), "sharpe", thresholds
                                )
                                render_metric_card(
                                    "Return", row.get('return_pct', 0), "return_pct", thresholds
                                )

                            with col_m2:
                                render_metric_card(
                                    "Win Rate", row.get('win_rate', 0), "winrate", thresholds
                                )
                                render_metric_card(
                                    "Max DD",
                                    abs(row.get('max_drawdown', 0)),
                                    "drawdown",
                                    thresholds,
                                )

                            # Additional metrics
                            st.markdown("**Additional Metrics:**")
                            st.write(f"- Total PnL: ${row.get('total_pnl', 0):,.2f}")
                            st.write(f"- Total Trades: {row.get('total_trades', 0)}")
                            st.write(f"- Avg Trade PnL: ${row.get('avg_trade_pnl', 0):,.2f}")

                        with col2:
                            # Performance chart placeholder
                            st.subheader("Performance Metrics")
                            metrics_df = pd.DataFrame(
                                {
                                    'Metric': ['Sharpe', 'Return %', 'Win Rate %', 'Max DD %'],
                                    'Value': [
                                        row.get('sharpe_ratio', 0),
                                        row.get('return_pct', 0),
                                        row.get('win_rate', 0),
                                        abs(row.get('max_drawdown', 0)),
                                    ],
                                }
                            )

                            fig = px.bar(
                                metrics_df,
                                x='Metric',
                                y='Value',
                                title='Metrics Comparison',
                                color='Value',
                                color_continuous_scale='RdYlGn',
                            )
                            st.plotly_chart(
                                fig, width='stretch', key=f"individual_chart_{test_name_safe}_{idx}"
                            )
            else:
                st.info(
                    "📋 No hay resultados cargados. Ve a la pestaña 'Dashboard' o 'Load Results'."
                )

        # Tab 3: Training Analysis (Before/After)
        with tabs[2]:
            st.header("🎓 Training Analysis - Before vs After")

            if st.session_state.get('results_loaded') and 'df_results' in st.session_state:
                df = st.session_state.df_results

                # Filter for learning engine results with before/after metrics
                # Convert dict columns to strings for comparison
                learning_engine_results = df[(df['test_type'] == 'learning_engine')].copy()

                # Initialize variables
                has_comparison = False
                comparison_count = 0

                if not learning_engine_results.empty:
                    logger.info(
                        f"🔍 Encontrados {len(learning_engine_results)} resultados de learning engines"
                    )

                    # Check if we have before/after data by checking if columns
                    # exist
                    for idx, row in learning_engine_results.iterrows():
                        before = row.get('before_training_metrics')
                        after = row.get('after_training_metrics')

                        # Verificar que ambos existan y sean válidos
                        before_valid = (isinstance(before, dict) and len(before) > 0) or (
                            isinstance(before, str) and before not in ['nan', '', 'None', '{}']
                        )
                        after_valid = (isinstance(after, dict) and len(after) > 0) or (
                            isinstance(after, str) and after not in ['nan', '', 'None', '{}']
                        )

                        if before_valid and after_valid:
                            has_comparison = True
                            comparison_count += 1
                            logger.debug(
                                f"✅ Learning engine {row.get('learning_engine', 'unknown')} "
                                "tiene datos de comparación (antes y después)"
                            )

                    logger.info(
                        f"📊 {comparison_count} de {len(learning_engine_results)} tienen datos completos de comparación"
                    )

                if has_comparison and comparison_count > 0:
                    st.success(
                        f"✅ Found {len(learning_engine_results)} learning engine results with training comparison"
                    )

                    for idx, row in learning_engine_results.iterrows():
                        test_name = row.get('test_name', f'Learning Engine {idx}')
                        learning_engine = row.get('learning_engine', 'unknown')

                        # Extract before/after metrics (handle both dict and
                        # string representations)
                        before = row.get('before_training_metrics', {})
                        after = row.get('after_training_metrics', {})
                        improvement = row.get('improvement_pct', {})

                        # Parse if string
                        if isinstance(before, str) and before != 'nan' and before:
                            try:
                                import ast

                                before = ast.literal_eval(before) if before.startswith('{') else {}
                            except BaseException:
                                before = {}
                        if isinstance(after, str) and after != 'nan' and after:
                            try:
                                import ast

                                after = ast.literal_eval(after) if after.startswith('{') else {}
                            except BaseException:
                                after = {}
                        if isinstance(improvement, str) and improvement != 'nan' and improvement:
                            try:
                                import ast

                                improvement = (
                                    ast.literal_eval(improvement)
                                    if improvement.startswith('{')
                                    else {}
                                )
                            except BaseException:
                                improvement = {}

                        if (
                            not before
                            or not after
                            or not isinstance(before, dict)
                            or not isinstance(after, dict)
                        ):
                            continue

                        with st.expander(f"🎓 {test_name} - Training Impact", expanded=False):
                            st.markdown(f"**Learning Engine:** `{learning_engine}`")

                            # Comparison metrics in columns
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.subheader("📉 Before Training")
                                st.metric("Sharpe Ratio", f"{before.get('sharpe_ratio', 0):.2f}")
                                st.metric("Return %", f"{before.get('return_pct', 0):.2f}%")
                                st.metric("Win Rate", f"{before.get('win_rate', 0)*100:.1f}%")
                                st.metric(
                                    "Max Drawdown", f"{abs(before.get('max_drawdown', 0)):.2f}%"
                                )
                                st.metric("Total PnL", f"${before.get('total_pnl', 0):,.2f}")

                            with col2:
                                st.subheader("📈 After Training")
                                st.metric("Sharpe Ratio", f"{after.get('sharpe_ratio', 0):.2f}")
                                st.metric("Return %", f"{after.get('return_pct', 0):.2f}%")
                                st.metric("Win Rate", f"{after.get('win_rate', 0)*100:.1f}%")
                                st.metric(
                                    "Max Drawdown", f"{abs(after.get('max_drawdown', 0)):.2f}%"
                                )
                                st.metric("Total PnL", f"${after.get('total_pnl', 0):,.2f}")

                            with col3:
                                st.subheader("📊 Improvement")
                                sharpe_imp = (
                                    improvement.get('sharpe_ratio', 0)
                                    if isinstance(improvement, dict)
                                    else 0
                                )
                                return_imp = (
                                    improvement.get('return_pct', 0)
                                    if isinstance(improvement, dict)
                                    else 0
                                )
                                winrate_imp = (
                                    improvement.get('win_rate', 0)
                                    if isinstance(improvement, dict)
                                    else 0
                                )
                                dd_imp = (
                                    improvement.get('max_drawdown', 0)
                                    if isinstance(improvement, dict)
                                    else 0
                                )
                                pnl_imp = (
                                    improvement.get('total_pnl', 0)
                                    if isinstance(improvement, dict)
                                    else 0
                                )

                                # Color code improvements
                                def improvement_color(val):
                                    if val > 0:
                                        return "🟢"
                                    elif val < 0:
                                        return "🔴"
                                    return "⚪"

                                st.metric(
                                    "Sharpe Ratio",
                                    f"{improvement_color(sharpe_imp)} {sharpe_imp:+.2f}%",
                                )
                                st.metric(
                                    "Return %",
                                    f"{improvement_color(return_imp)} {return_imp:+.2f}%",
                                )
                                st.metric(
                                    "Win Rate",
                                    f"{improvement_color(winrate_imp)} {winrate_imp:+.2f}%",
                                )
                                st.metric(
                                    "Max Drawdown", f"{improvement_color(-dd_imp)} {dd_imp:+.2f}%"
                                )
                                st.metric(
                                    "Total PnL", f"{improvement_color(pnl_imp)} {pnl_imp:+.2f}%"
                                )

                            # Visual comparison chart
                            st.markdown("---")
                            st.subheader("📊 Metrics Comparison Chart")

                            metrics_to_compare = [
                                'sharpe_ratio',
                                'return_pct',
                                'win_rate',
                                'max_drawdown',
                            ]
                            comparison_data = {
                                'Metric': [],
                                'Before': [],
                                'After': [],
                                'Improvement %': [],
                            }

                            for metric in metrics_to_compare:
                                if metric == 'max_drawdown':
                                    comparison_data['Metric'].append('Max Drawdown (abs)')
                                    comparison_data['Before'].append(abs(before.get(metric, 0)))
                                    comparison_data['After'].append(abs(after.get(metric, 0)))
                                else:
                                    comparison_data['Metric'].append(
                                        metric.replace('_', ' ').title()
                                    )
                                    comparison_data['Before'].append(before.get(metric, 0))
                                    comparison_data['After'].append(after.get(metric, 0))
                                comparison_data['Improvement %'].append(
                                    sharpe_imp
                                    if metric == 'sharpe_ratio'
                                    else (
                                        return_imp
                                        if metric == 'return_pct'
                                        else winrate_imp
                                        if metric == 'win_rate'
                                        else dd_imp
                                    )
                                )

                            comparison_df = pd.DataFrame(comparison_data)

                            fig = px.bar(
                                comparison_df,
                                x='Metric',
                                y=['Before', 'After'],
                                barmode='group',
                                title=f'Before vs After Training - {learning_engine}',
                                labels={'value': 'Value', 'variable': 'Period'},
                                color_discrete_map={'Before': '#e74c3c', 'After': '#2ecc71'},
                            )
                            st.plotly_chart(
                                fig,
                                width='stretch',
                                key=f"training_comparison_{learning_engine}_{idx}",
                            )
                    else:
                        # Mostrar qué learning engines fueron encontrados pero sin datos
                        learning_engines_found = (
                            learning_engine_results['learning_engine'].unique().tolist()
                            if 'learning_engine' in learning_engine_results.columns
                            else []
                        )
                        st.warning(
                            f"⚠️ Se encontraron {len(learning_engine_results)} resultados de learning engines "
                            f"({', '.join([str(le) for le in learning_engines_found[:5]]) if learning_engines_found else 'unknown'}), "
                            "pero sin datos de comparación (before/after training).\n\n"
                            "**Posibles causas:**\n"
                            "1. Los resultados fueron guardados antes de implementar la funcionalidad de comparación\n"
                            "2. Los learning engines fallaron durante el entrenamiento\n"
                            "3. Los datos no se guardaron correctamente en el JSON\n\n"
                            "**Solución:** Ejecuta nuevos tests con 'Learning Engines' habilitado para ver la comparación antes/después."
                        )
                        logger.warning(
                            f"⚠️ {len(learning_engine_results)} learning engine results encontrados "
                            f"pero {comparison_count} tienen datos de comparación completos"
                        )
                else:
                    st.info(
                        "📋 No se encontraron resultados de learning engines.\n\n"
                        "**Para ver análisis de entrenamiento:**\n"
                        "1. Activa al menos un Learning Engine en el sidebar (Supervised, Deep, Reinforcement, Transformer)\n"
                        "2. Selecciona 'Learning Engines' en los tests a ejecutar\n"
                        "3. Haz clic en '🚀 EXECUTE SELECTED TESTS'\n"
                        "4. Los resultados mostrarán métricas ANTES y DESPUÉS del entrenamiento"
                    )
                    logger.info(
                        "ℹ️ No se encontraron resultados de learning engines para análisis de training"
                    )
            else:
                st.info("📋 No results loaded. Execute tests or load results first.")

        # Tab 4: Saved Configurations
        with tabs[3]:
            st.header("💾 Saved Successful Configurations")

            from app.backtesting.successful_configs import SuccessfulConfigManager

            config_manager = SuccessfulConfigManager()

            # Save configuration section
            with st.expander("💾 Save Current Configuration", expanded=False):
                if st.session_state.get('results_loaded') and 'df_results' in st.session_state:
                    df = st.session_state.df_results

                    # Select result to save
                    result_names = df['test_name'].tolist() if 'test_name' in df.columns else []
                    if result_names:
                        selected_result_name = st.selectbox(
                            "Select Result to Save", options=result_names, key="save_config_select"
                        )

                        selected_result = df[df['test_name'] == selected_result_name].iloc[0]

                        col1, col2 = st.columns(2)
                        with col1:
                            config_name = st.text_input(
                                "Configuration Name",
                                value=f"config_{selected_result.get('test_type', 'test')}_{datetime.now().strftime('%Y%m%d')}",
                                key="config_name_input",
                            )
                        with col2:
                            config_tags = st.text_input(
                                "Tags (comma-separated)",
                                value=",".join(
                                    [
                                        str(selected_result.get('test_type', '')),
                                        str(selected_result.get('learning_engine', '')),
                                    ]
                                ),
                                key="config_tags_input",
                                help="e.g., momentum,supervised,high_sharpe",
                            )

                        config_description = st.text_area(
                            "Description (optional)",
                            value=f"Saved from {selected_result_name}",
                            key="config_description_input",
                        )

                        if st.button(
                            "💾 Save Configuration", type="primary", key="save_config_button"
                        ):
                            try:
                                # Extract full config
                                config_to_save = {
                                    'test_type': selected_result.get('test_type'),
                                    'learning_engine': selected_result.get('learning_engine'),
                                    'modules_active': selected_result.get('modules_active', []),
                                    'thresholds': selected_result.get('thresholds', {}),
                                }

                                metrics_to_save = {
                                    'sharpe_ratio': selected_result.get('sharpe_ratio'),
                                    'return_pct': selected_result.get('return_pct'),
                                    'win_rate': selected_result.get('win_rate'),
                                    'max_drawdown': selected_result.get('max_drawdown'),
                                    'total_pnl': selected_result.get('total_pnl'),
                                    'sortino_ratio': selected_result.get('sortino_ratio'),
                                    'total_trades': selected_result.get('total_trades'),
                                }

                                before_training = selected_result.get('before_training_metrics')
                                after_training = selected_result.get('after_training_metrics')
                                improvement = selected_result.get('improvement_pct')

                                # Parse if string
                                if isinstance(before_training, str):
                                    try:
                                        import ast

                                        before_training = (
                                            ast.literal_eval(before_training)
                                            if before_training.startswith('{')
                                            else None
                                        )
                                    except BaseException:
                                        before_training = None
                                if isinstance(after_training, str):
                                    try:
                                        import ast

                                        after_training = (
                                            ast.literal_eval(after_training)
                                            if after_training.startswith('{')
                                            else None
                                        )
                                    except BaseException:
                                        after_training = None
                                if isinstance(improvement, str):
                                    try:
                                        import ast

                                        improvement = (
                                            ast.literal_eval(improvement)
                                            if improvement.startswith('{')
                                            else None
                                        )
                                    except BaseException:
                                        improvement = None

                                tags_list = [t.strip() for t in config_tags.split(',') if t.strip()]

                                config_id = config_manager.save_config(
                                    name=config_name,
                                    config=config_to_save,
                                    metrics=metrics_to_save,
                                    description=config_description,
                                    tags=tags_list,
                                    before_training_metrics=(
                                        before_training
                                        if isinstance(before_training, dict)
                                        else None
                                    ),
                                    after_training_metrics=(
                                        after_training if isinstance(after_training, dict) else None
                                    ),
                                    improvement_pct=(
                                        improvement if isinstance(improvement, dict) else None
                                    ),
                                )

                                st.success(
                                    f"✅ Configuration '{config_name}' saved successfully! (ID: {config_id})"
                                )
                                st.balloons()
                            except Exception as e:
                                st.error(f"❌ Error saving configuration: {e}")
                                logger.error(f"Error saving configuration: {e}", exc_info=True)
                    else:
                        st.warning("No results available to save.")
                else:
                    st.info("📋 Load results first before saving configurations.")

        st.markdown("---")

        # List saved configurations
        st.subheader("📋 Saved Configurations")

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            min_sharpe_filter = st.number_input(
                "Min Sharpe", value=0.0, step=0.1, key="min_sharpe_filter"
            )
        with col2:
            min_return_filter = st.number_input(
                "Min Return %", value=0.0, step=1.0, key="min_return_filter"
            )
        with col3:
            sort_by_config = st.selectbox(
                "Sort By", ['sharpe_ratio', 'return_pct', 'timestamp'], key="sort_by_config"
            )

        saved_configs = config_manager.list_configs(
            min_sharpe=min_sharpe_filter if min_sharpe_filter > 0 else None,
            min_return=min_return_filter if min_return_filter > 0 else None,
            sort_by=sort_by_config,
        )

        if saved_configs:
            st.success(f"Found {len(saved_configs)} saved configurations")

            for config in saved_configs:
                config_id = config.get('id')
                config_name = config.get('name')
                metrics = config.get('metrics', {})
                tags = config.get('tags', [])
                timestamp = config.get('timestamp', '')
                improvement = config.get('improvement_pct', {})

                with st.expander(
                    f"💾 {config_name} - Sharpe: {metrics.get('sharpe_ratio', 0):.2f}, Return: {metrics.get('return_pct', 0):.2f}%",
                    expanded=False,
                ):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.write(f"**ID:** `{config_id}`")
                        st.write(f"**Timestamp:** {timestamp}")
                        if config.get('description'):
                            st.write(f"**Description:** {config.get('description')}")

                        st.markdown("**Metrics:**")
                        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                        with col_m1:
                            st.metric("Sharpe", f"{metrics.get('sharpe_ratio', 0):.2f}")
                        with col_m2:
                            st.metric("Return %", f"{metrics.get('return_pct', 0):.2f}%")
                        with col_m3:
                            st.metric("Win Rate", f"{metrics.get('win_rate', 0)*100:.1f}%")
                        with col_m4:
                            st.metric("Max DD", f"{abs(metrics.get('max_drawdown', 0)):.2f}%")

                        if improvement:
                            st.markdown("**Training Improvement:**")
                            st.write(f"- Sharpe: {improvement.get('sharpe_ratio', 0):+.2f}%")
                            st.write(f"- Return: {improvement.get('return_pct', 0):+.2f}%")

                        if tags:
                            st.markdown("**Tags:** " + ", ".join([f"`{t}`" for t in tags]))

                    with col2:
                        if st.button("📥 Load", key=f"load_config_{config_id}"):
                            st.session_state['selected_config_to_load'] = config_id
                            st.info(
                                f"Configuration '{config_name}' selected. Use it when executing tests."
                            )

                        if st.button("🗑️ Delete", key=f"delete_config_{config_id}"):
                            if config_manager.delete_config(config_id=config_id):
                                st.success(f"✅ Configuration '{config_name}' deleted")
                                st.rerun()
                            else:
                                st.error("Failed to delete configuration")
        else:
            st.info(
                "📋 No saved configurations found. Save successful configurations from test results."
            )

        # Tab 5: Integration Test Objectives
        with tabs[4]:
            st.header("🎯 Integration Test Objectives")
            st.markdown(
                """
            ### Objetivos de Métricas para Integration Tests

            Esta sección muestra qué estrategias con qué parámetros cumplen los objetivos establecidos para los integration tests.
            """
            )

            # Load and display Meta Analysis results if available
            loader = ComprehensiveBacktestLoader()
            meta_summary = loader.get_meta_analysis_summary()

            if meta_summary:
                st.success(
                    "✅ **Meta Análisis Disponible** - Se ejecutó análisis agregado de todos los backtests"
                )

                with st.expander("🔍 Ver Resultados del Meta Análisis", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Total Backtests Analizados",
                            meta_summary.get('total_backtests_analyzed', 0),
                        )
                    with col2:
                        st.metric("Clusters Encontrados", meta_summary.get('clusters_found', 0))
                    with col3:
                        st.metric(
                            "Combinaciones Óptimas", meta_summary.get('optimal_combinations', 0)
                        )

                    st.markdown(f"**Archivo:** `{meta_summary.get('file_name', 'Unknown')}`")
                    st.markdown(f"**Timestamp:** {meta_summary.get('timestamp', 'Unknown')}")

                    # Show aggregate metrics if available
                    if meta_summary.get('avg_sharpe') or meta_summary.get('avg_return'):
                        st.subheader("📊 Métricas Agregadas")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(
                                "Sharpe Ratio Promedio", f"{meta_summary.get('avg_sharpe', 0):.2f}"
                            )
                        with col2:
                            st.metric(
                                "Return Promedio", f"{meta_summary.get('avg_return', 0):.2f}%"
                            )

                    # Show optimal combinations if available
                    optimal_combs = meta_summary.get('optimal_combinations', [])
                    if optimal_combs:
                        st.subheader("🏆 Top Combinaciones Óptimas")
                        for idx, combo in enumerate(optimal_combs[:5], 1):  # Show top 5
                            if isinstance(combo, dict):
                                st.write(
                                    f"**{idx}.** {combo.get('description', 'Combinación óptima')}"
                                )
                                st.json(combo)

                    # Show correlations if available
                    correlations = meta_summary.get('correlations', {})
                    if correlations:
                        st.subheader("📈 Correlaciones entre Métricas")
                        st.json(correlations)

                    st.info(
                        "💡 Estos resultados provienen del análisis meta ejecutado automáticamente después de los backtests."
                    )

                st.divider()

            # Display objectives table
            objectives = get_integration_test_objectives()

            st.subheader("📋 Objetivos Definidos")
            objectives_data = []
            for metric_name, obj_config in objectives.items():
                if obj_config['operator'] == 'range':
                    target_str = f"{obj_config['target_min']}{obj_config['unit']} - {obj_config['target_max']}{obj_config['unit']}"
                else:
                    target_str = (
                        f"{obj_config['operator']} {obj_config['target']}{obj_config['unit']}"
                    )

                objectives_data.append(
                    {
                        'Métrica': metric_name.replace('_', ' ').title(),
                        'Objetivo': target_str,
                        'Descripción': obj_config['description'],
                    }
                )

            objectives_df = pd.DataFrame(objectives_data)
            st.dataframe(objectives_df, use_container_width=True, hide_index=True)

            st.divider()

            # Evaluate all results against objectives
            if st.session_state.get('results_loaded') and 'df_results' in st.session_state:
                df = st.session_state.df_results

                if not df.empty:
                    st.subheader("🔍 Evaluación de Estrategias")

                    # Filter options
                    col1, col2 = st.columns(2)
                    with col1:
                        show_only_passing = st.checkbox(
                            "Mostrar solo estrategias que cumplen TODOS los objetivos", value=False
                        )
                    with col2:
                        min_objectives_passed = st.slider(
                            "Mínimo de objetivos cumplidos",
                            min_value=0,
                            max_value=len(objectives),
                            value=0,
                        )

                    # Evaluate each result
                    evaluation_results = []

                    for idx, row in df.iterrows():
                        # Extract metrics
                        metrics = {
                            'max_drawdown': row.get('max_drawdown', 0),
                            'sharpe_ratio': row.get('sharpe_ratio', 0),
                            'sortino_ratio': row.get('sortino_ratio', 0),
                            'profit_factor': row.get('profit_factor', 0),
                            'win_rate': row.get('win_rate', 0),
                        }

                    # Evaluate objectives
                    eval_results = evaluate_all_objectives(metrics, objectives)

                    # Count passed objectives
                    passed_count = sum(1 for passes, _, _ in eval_results.values() if passes)
                    # Only count if metric available
                    total_count = len([r for r in eval_results.values() if r[2]])

                    all_passed = passed_count == total_count and total_count > 0

                    # Extract strategy config
                    strategy_config = extract_strategy_config(row)

                    # Build evaluation result
                    eval_result = {
                        'test_name': row.get('test_name', f'Test {idx}'),
                        'test_type': row.get('test_type', 'Unknown'),
                        'strategy': strategy_config.get('strategy', 'Unknown'),
                        'learning_engine': strategy_config.get('learning_engine', 'None'),
                        'modules': (
                            ', '.join(strategy_config.get('modules_active', []))
                            if strategy_config.get('modules_active')
                            else 'None'
                        ),
                        'parameters': strategy_config.get('parameters', {}),
                        'passed_count': passed_count,
                        'total_count': total_count,
                        'all_passed': all_passed,
                        'evaluations': eval_results,
                        'metrics': metrics,
                        'row_index': idx,
                    }

                    evaluation_results.append(eval_result)

                    # Filter results
                    if show_only_passing:
                        evaluation_results = [r for r in evaluation_results if r['all_passed']]

                    evaluation_results = [
                        r for r in evaluation_results if r['passed_count'] >= min_objectives_passed
                    ]

                    # Sort by passed count (descending)
                    evaluation_results.sort(
                        key=lambda x: (x['passed_count'], x['all_passed']), reverse=True
                    )

                    if evaluation_results:
                        st.success(
                            f"✅ Encontradas {len(evaluation_results)} estrategia(s) que cumplen los criterios"
                        )

                        # Display results
                        for eval_result in evaluation_results:
                            # Determine color based on performance
                            if eval_result['all_passed']:
                                status_color = "🟢"
                                status_text = "✅ CUMPLE TODOS LOS OBJETIVOS"
                            elif eval_result['passed_count'] >= len(objectives) * 0.8:
                                status_color = "🟡"
                                status_text = f"⚠️ CUMPLE {eval_result['passed_count']}/{eval_result['total_count']} OBJETIVOS"
                            elif eval_result['passed_count'] >= len(objectives) * 0.5:
                                status_color = "🟠"
                                status_text = f"⚠️ CUMPLE {eval_result['passed_count']}/{eval_result['total_count']} OBJETIVOS"
                            else:
                                status_color = "🔴"
                                status_text = f"❌ CUMPLE {eval_result['passed_count']}/{eval_result['total_count']} OBJETIVOS"

                            with st.expander(
                                f"{status_color} **{eval_result['test_name']}** - {status_text}",
                                # Auto-expand if all passed
                                expanded=eval_result['all_passed'],
                            ):
                                # Strategy info
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.markdown(f"**Tipo de Test:** {eval_result['test_type']}")
                                    st.markdown(f"**Estrategia:** `{eval_result['strategy']}`")
                                with col2:
                                    st.markdown(
                                        f"**Learning Engine:** `{eval_result['learning_engine']}`"
                                    )
                                    st.markdown(f"**Módulos Activos:** {eval_result['modules']}")
                                with col3:
                                    st.markdown(
                                        f"**Objetivos Cumplidos:** {eval_result['passed_count']}/{eval_result['total_count']}"
                                    )
                                    if eval_result['all_passed']:
                                        st.success("🎯 ESTRATEGIA ÓPTIMA")

                                st.divider()

                                # Parameters
                                if eval_result['parameters']:
                                    st.subheader("⚙️ Parámetros de la Estrategia")
                                    st.json(eval_result['parameters'])

                                st.divider()

                                # Detailed metric evaluation
                                st.subheader("📊 Evaluación Detallada de Métricas")

                                metric_cols = st.columns(3)
                                metric_idx = 0

                                for metric_name, (passes, status, obj_config) in eval_result[
                                    'evaluations'
                                ].items():
                                    with metric_cols[metric_idx % 3]:
                                        # Get actual value
                                        metric_key = metric_name
                                        if metric_name == 'max_drawdown':
                                            actual_value = abs(
                                                eval_result['metrics'].get('max_drawdown', 0)
                                            )
                                        elif metric_name == 'win_rate':
                                            actual_value = eval_result['metrics'].get('win_rate', 0)
                                            if actual_value <= 1.0:
                                                actual_value = actual_value * 100
                                        else:
                                            actual_value = eval_result['metrics'].get(metric_key, 0)

                                        # Format target
                                        if obj_config['operator'] == 'range':
                                            target_str = f"{obj_config['target_min']}{obj_config['unit']} - {obj_config['target_max']}{obj_config['unit']}"
                                        else:
                                            target_str = f"{obj_config['operator']} {obj_config['target']}{obj_config['unit']}"

                                        # Display
                                        st.markdown(f"**{metric_name.replace('_', ' ').title()}**")
                                        st.write(
                                            f"**Valor:** {actual_value:.2f}{obj_config['unit']}"
                                        )
                                        st.write(f"**Objetivo:** {target_str}")
                                        st.write(f"**Estado:** {status}")
                                        st.write(f"*{obj_config['description']}*")

                                    metric_idx += 1

                                # Metrics summary table
                                st.divider()
                                st.subheader("📈 Resumen de Métricas")
                                summary_data = []
                                for metric_name, (passes, status, obj_config) in eval_result[
                                    'evaluations'
                                ].items():
                                    metric_key = metric_name
                                    if metric_name == 'max_drawdown':
                                        actual_value = abs(
                                            eval_result['metrics'].get('max_drawdown', 0)
                                        )
                                    elif metric_name == 'win_rate':
                                        actual_value = eval_result['metrics'].get('win_rate', 0)
                                        if actual_value <= 1.0:
                                            actual_value = actual_value * 100
                                    else:
                                        actual_value = eval_result['metrics'].get(metric_key, 0)

                                    if obj_config['operator'] == 'range':
                                        target_str = f"{obj_config['target_min']}{obj_config['unit']} - {obj_config['target_max']}{obj_config['unit']}"
                                    else:
                                        target_str = f"{obj_config['operator']} {obj_config['target']}{obj_config['unit']}"

                                    summary_data.append(
                                        {
                                            'Métrica': metric_name.replace('_', ' ').title(),
                                            'Valor Actual': f"{actual_value:.2f}{obj_config['unit']}",
                                            'Objetivo': target_str,
                                            'Estado': status,
                                            'Descripción': obj_config['description'],
                                        }
                                    )

                                summary_df = pd.DataFrame(summary_data)
                                st.dataframe(summary_df, use_container_width=True, hide_index=True)
                        else:
                            st.warning(
                                "⚠️ No se encontraron estrategias que cumplan los criterios seleccionados. Ajusta los filtros o ejecuta más tests."
                            )
                else:
                    st.info(
                        "📋 No hay resultados cargados. Ejecuta tests o carga resultados existentes."
                    )
            else:
                st.info(
                    "📋 No hay resultados cargados. Ejecuta tests o carga resultados existentes."
                )

        # Tab 6: Comparison
        with tabs[5]:
            st.header("🔍 Comparison View")

            if st.session_state.get('results_loaded') and 'df_results' in st.session_state:
                df = st.session_state.df_results

                # Multi-select for comparison
                test_names = df['test_name'].tolist() if 'test_name' in df.columns else []
                selected_for_comparison = st.multiselect(
                    "Select tests to compare",
                    options=test_names,
                    default=test_names[:5] if len(test_names) >= 5 else test_names,
                )

                if selected_for_comparison:
                    df_compare = df[df['test_name'].isin(selected_for_comparison)]

                    # Comparison Chart
                    st.subheader("📊 Metrics Comparison")

                    metrics_to_compare = ['sharpe_ratio', 'return_pct', 'win_rate', 'max_drawdown']
                    available_metrics = [m for m in metrics_to_compare if m in df_compare.columns]

                    if available_metrics:
                        fig = go.Figure()

                        for metric in available_metrics:
                            fig.add_trace(
                                go.Scatter(
                                    x=df_compare['test_name'],
                                    y=df_compare[metric],
                                    mode='lines+markers',
                                    name=metric.replace('_', ' ').title(),
                                    marker=dict(size=10),
                                )
                            )

                        fig.update_layout(
                            title='Metrics Comparison Across Tests',
                            xaxis_title='Test Name',
                            yaxis_title='Metric Value',
                            hovermode='x unified',
                            height=500,
                        )
                        st.plotly_chart(fig, width='stretch', key="comparison_chart")

                    # Comparison Table
                    st.subheader("📋 Detailed Comparison Table")
                    comparison_cols = (
                        ['test_name'] + available_metrics + ['total_pnl', 'total_trades']
                    )
                    display_cols = [c for c in comparison_cols if c in df_compare.columns]
                    st.dataframe(df_compare[display_cols], width='stretch')
                else:
                    st.warning("Select at least one test to compare.")
            else:
                st.info(
                    "📋 No hay resultados cargados. Ve a la pestaña 'Dashboard' o 'Load Results'."
                )

        # Tab 7: Load Results
        with tabs[6]:
            st.header("📁 Load Results")

            st.write("Load existing backtest results from files.")

            results_dir = st.text_input(
                "Results Directory", value="reports/comprehensive_backtest", key="results_dir"
            )

            if st.button("📂 Load Results", type="primary"):
                try:
                    loader = ComprehensiveBacktestLoader()
                    if Path(results_dir).exists():
                        loader.results_dir = Path(results_dir)

                    # Use load_as_dataframe() instead of load_all_results()
                    df_results = loader.load_as_dataframe()

                    if not df_results.empty:
                        st.session_state.results_loaded = True
                        st.session_state.df_results = df_results
                        st.success(f"✅ Loaded {len(df_results)} results!")
                        st.dataframe(df_results.head(10))
                    else:
                        st.warning("No results found in the specified directory.")
                except Exception as e:
                    st.error(f"Error loading results: {e}")
                    logger.error(f"Error loading results: {e}", exc_info=True)

            # Show file browser
            st.subheader("📂 Available Result Files")
            if Path(results_dir).exists():
                result_files = list(Path(results_dir).glob("*.csv")) + list(
                    Path(results_dir).glob("*.json")
                )
                if result_files:
                    for file in result_files[:10]:  # Show first 10
                        st.write(f"- {file.name}")
                else:
                    st.info("No result files found.")
            else:
                st.warning(f"Directory {results_dir} does not exist.")

        # Execute tests if button was clicked
        execute_tests_flag = st.session_state.get('execute_tests', False)
        logger.debug(f"🔍 execute_tests flag: {execute_tests_flag}")

        if execute_tests_flag:
            logger.info("🚀 Iniciando ejecución de tests...")
            try:
                params = st.session_state.get('execution_params', {})
                selected_tests = st.session_state.get('selected_tests', [])
                use_multi_strategy = params.get('use_multi_strategy', False)

                logger.info(f"📋 Params: {list(params.keys())}")
                logger.info(f"📋 Selected tests: {selected_tests}")

                if not params:
                    st.error(
                        "❌ No hay parámetros de ejecución. Por favor, haz clic en el botón EXECUTE de nuevo."
                    )
                    st.session_state.execute_tests = False
                    raise ValueError("No execution params")

                if not selected_tests:
                    st.error(
                        "❌ No hay tests seleccionados. Por favor, selecciona tests y haz clic en EXECUTE de nuevo."
                    )
                    st.session_state.execute_tests = False
                    raise ValueError("No selected tests")

                # Create a temporary config file or modify existing one
                config_path = (
                    project_root / "config" / "backtesting" / "comprehensive_backtest.yaml"
                )

                # Load existing config
                import yaml

                try:
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)

                    if config is None:
                        st.error(f"❌ Error: Config file is empty or invalid: {config_path}")
                        raise ValueError("Config file is empty")

                    logger.info(f"✅ Config cargado desde: {config_path}")
                    logger.debug(
                        f"📋 Learning engines antes de actualizar: {config.get('learning_engines', {})}"
                    )
                except Exception as e:
                    st.error(f"❌ Error cargando config: {e}")
                    logger.error(f"Error cargando config: {e}", exc_info=True)
                    raise

                # Update config with user selections
                # Update input parameters
                config['input']['symbol'] = params.get('symbol', 'SNOW')
                config['input']['start_date'] = params.get(
                    'start_date', datetime.now() - timedelta(days=365)
                ).strftime("%Y-%m-%d")
                config['input']['end_date'] = params.get(
                    'end_date', datetime.now() - timedelta(days=1)
                ).strftime("%Y-%m-%d")
                config['input']['initial_capital'] = float(params.get('initial_capital', 100000))

                # Update learning engines
                if 'learning_engines' not in config:
                    config['learning_engines'] = {}

                learning_engines_selected = params.get('learning_engines', [])

                # Ensure all learning engine sections exist before updating
                for engine_name in ['supervised', 'deep', 'reinforcement', 'transformer']:
                    if engine_name not in config['learning_engines']:
                        config['learning_engines'][engine_name] = {
                            'enabled': False,
                            'parameters': {},
                        }

                # Update enabled flags
                config['learning_engines']['supervised']['enabled'] = (
                    'supervised' in learning_engines_selected
                )
                config['learning_engines']['deep']['enabled'] = 'deep' in learning_engines_selected
                config['learning_engines']['reinforcement']['enabled'] = (
                    'reinforcement' in learning_engines_selected
                )
                config['learning_engines']['transformer']['enabled'] = (
                    'transformer' in learning_engines_selected
                )

                # Validation: if learning_engines test is selected, warn if no engines are enabled
                if 'learning_engines' in selected_tests and not learning_engines_selected:
                    st.warning(
                        "⚠️ Learning Engines test selected but no learning engines enabled. Please select at least one learning engine."
                    )

                # Log learning engines configuration
                enabled_engines = [
                    eng
                    for eng in ['supervised', 'deep', 'reinforcement', 'transformer']
                    if config['learning_engines'].get(eng, {}).get('enabled', False)
                ]
                logger.info(
                    f"📋 Learning engines configurados: {enabled_engines} (seleccionados: {learning_engines_selected})"
                )
                logger.debug(
                    f"📋 Learning engines después de actualizar: {config.get('learning_engines', {})}"
                )

                # Update multi-strategy config
                if 'backtests' not in config:
                    config['backtests'] = {}
                if 'multi_strategy' not in config['backtests']:
                    config['backtests']['multi_strategy'] = {}

                config['backtests']['multi_strategy']['enabled'] = use_multi_strategy
                if use_multi_strategy:
                    config['backtests']['multi_strategy']['strategies'] = params.get(
                        'strategies', ["momentum", "mean_reversion", "pairs_trading"]
                    )
                    config['backtests']['multi_strategy'][
                        'enable_dynamic_reallocation'
                    ] = params.get('enable_dynamic_reallocation', True)
                    if params.get('enable_dynamic_reallocation', True):
                        config['backtests']['multi_strategy'][
                            'reallocation_frequency_days'
                        ] = params.get('reallocation_frequency', 30)

                # Enable/disable specific backtests
                for test_name in [
                    'baseline',
                    'learning_engines',
                    'monte_carlo',
                    'grid_search',
                    'ablation',
                    'walk_forward',
                    'out_of_sample',
                    'regime_test',
                    'transformer_optimization',
                ]:
                    if 'backtests' not in config:
                        config['backtests'] = {}
                    if test_name not in config['backtests']:
                        config['backtests'][test_name] = {}
                    config['backtests'][test_name]['enabled'] = test_name in selected_tests

                    # Para learning_engines test, asegurar que use simple strategy si estamos en modo simple
                    if test_name == 'learning_engines' and test_name in selected_tests:
                        config['backtests'][test_name]['use_multi_strategy'] = use_multi_strategy
                        logger.info(
                            f"📋 Learning engines test configurado con use_multi_strategy={use_multi_strategy}"
                        )

                # Ensure multi_strategy test is enabled if selected
                if 'multi_strategy' in selected_tests:
                    config['backtests']['multi_strategy']['enabled'] = True

                # Update parallelization
                if 'parallelization' not in config:
                    config['parallelization'] = {}
                config['parallelization']['enabled'] = params.get('parallel', True)
                if params.get('max_workers'):
                    config['parallelization']['max_workers'] = params.get('max_workers')

                # Update meta analysis
                if 'meta_analysis' not in config:
                    config['meta_analysis'] = {}
                config['meta_analysis']['enabled'] = params.get('meta_analysis', True)
                config['meta_analysis']['enable_incremental_learning'] = params.get(
                    'incremental_learning', True
                )

                # Create temporary config file
                temp_config_path = (
                    project_root
                    / "config"
                    / "backtesting"
                    / "comprehensive_backtest_dashboard_temp.yaml"
                )
                with open(temp_config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

                # Show execution summary
                st.markdown("### 📋 Execution Summary")
                st.write(
                    f"**Strategy Mode:** {'🔄 Multi-Strategy' if use_multi_strategy else '📊 Simple Strategy'}"
                )

                if use_multi_strategy:
                    strategies = params.get('strategies', [])
                    st.write(f"**Strategies:** {', '.join(strategies) if strategies else 'None'}")
                    st.write(
                        f"**Dynamic Reallocation:** {'✅ Enabled' if params.get('enable_dynamic_reallocation', False) else '❌ Disabled'}"
                    )
                    if params.get('enable_dynamic_reallocation', False):
                        st.write(
                            f"**Reallocation Frequency:** {params.get('reallocation_frequency', 30)} days"
                        )

                learning_engines = params.get('learning_engines', [])
                if learning_engines:
                    st.write(f"**Learning Engines:** {', '.join(learning_engines)}")
                else:
                    st.write("**Learning Engines:** ❌ None (Baseline only)")

                st.write(f"**Selected Tests:** {', '.join(selected_tests)}")
                st.write(f"**Symbol:** {params.get('symbol', 'N/A')}")
                st.write(
                    f"**Date Range:** {params.get('start_date', 'N/A')} to {params.get('end_date', 'N/A')}"
                )
                st.write(f"**Initial Capital:** ${params.get('initial_capital', 0):,.2f}")

                st.markdown("---")

                # Execute tests
                progress_bar = st.progress(0)
                status_text = st.empty()

                try:
                    status_text.text("🔄 Initializing backtest runner...")
                    progress_bar.progress(10)

                    # Importar solo cuando se necesita (lazy loading)
                    global ComprehensiveBacktestRunner
                    if ComprehensiveBacktestRunner is None:
                        logger.info("📦 Iniciando import de ComprehensiveBacktestRunner...")
                        with st.spinner(
                            "📦 Cargando ComprehensiveBacktestRunner (esto puede tardar 10-30 segundos)..."
                        ):
                            try:
                                logger.debug("Importando módulo...")
                                from app.backtesting.comprehensive_backtest_runner import (
                                    ComprehensiveBacktestRunner,
                                )

                                logger.info("✅ ComprehensiveBacktestRunner importado correctamente")
                            except Exception as import_error:
                                logger.error(f"Error durante import: {import_error}", exc_info=True)
                                raise
                        st.success("✅ ComprehensiveBacktestRunner cargado correctamente")

                    logger.info("🔧 Instanciando ComprehensiveBacktestRunner...")
                    status_text.text("🔧 Creando runner...")
                    progress_bar.progress(15)

                    runner = ComprehensiveBacktestRunner(str(temp_config_path))
                    logger.info(
                        f"✅ ComprehensiveBacktestRunner instanciado con config: {temp_config_path}"
                    )

                    status_text.text(f"🚀 Executing {len(selected_tests)} test(s)...")
                    progress_bar.progress(30)

                    # Execute selected tests
                    results_df = runner.run_specific_backtests(selected_tests)

                    progress_bar.progress(90)
                    status_text.text("✅ Tests completed! Loading results...")

                    # Validate that output directory exists and has results
                    logger.info(f"📁 Output directory: {runner.output_dir}")
                    if not runner.output_dir.exists():
                        st.error(f"❌ Output directory does not exist: {runner.output_dir}")
                        logger.error(f"Output directory does not exist: {runner.output_dir}")
                    else:
                        # List JSON files in output directory
                        json_files = list(runner.output_dir.glob("*.json"))
                        logger.info(f"📁 Found {len(json_files)} JSON files in {runner.output_dir}")
                        if json_files:
                            logger.debug(f"📁 JSON files: {[f.name for f in json_files[:5]]}")

                    # Reload results from correct directory
                    loader = ComprehensiveBacktestLoader()
                    loader.results_dir = runner.output_dir
                    logger.info(f"🔄 Cargando resultados desde: {loader.results_dir}")

                    # Force reload by calling load_all_results first
                    all_results = loader.load_all_results()
                    logger.info(f"📊 Resultados cargados (raw): {len(all_results)}")

                    # Then convert to dataframe
                    df_results = loader.load_as_dataframe()
                    logger.info(f"📊 Resultados en DataFrame: {len(df_results)} filas")

                    if not df_results.empty:
                        st.session_state.results_loaded = True
                        # Actualizar o inicializar df_results en session_state
                        if (
                            'df_results' in st.session_state
                            and not st.session_state.df_results.empty
                        ):
                            st.session_state.df_results = pd.concat(
                                [st.session_state.df_results, df_results]
                            ).drop_duplicates(subset=['test_name'], keep='last')
                        else:
                            st.session_state.df_results = df_results

                        # Contar learning engines con datos de training
                        learning_engine_results = (
                            df_results[df_results['test_type'] == 'learning_engine']
                            if 'test_type' in df_results.columns
                            else pd.DataFrame()
                        )
                        if not learning_engine_results.empty:
                            has_training_data = learning_engine_results.apply(
                                lambda row: bool(row.get('before_training_metrics'))
                                and bool(row.get('after_training_metrics')),
                                axis=1,
                            ).sum()
                            st.info(
                                f"📊 {len(learning_engine_results)} resultado(s) de learning engines, {has_training_data} con datos de comparación (antes/después)"
                            )
                    else:
                        st.warning("⚠️ No se encontraron resultados después de la ejecución.")
                        st.write(f"📁 Directorio buscado: `{loader.results_dir}`")
                        st.write(f"📁 Directorio existe: {loader.results_dir.exists()}")
                        if loader.results_dir.exists():
                            json_files_found = list(loader.results_dir.glob("*.json"))
                            st.write(f"📁 Archivos JSON encontrados: {len(json_files_found)}")
                            if json_files_found:
                                st.write("📁 Archivos encontrados:")
                                for f in json_files_found[:5]:
                                    st.write(f"  - {f.name}")
                        logger.warning(f"No se encontraron resultados en {loader.results_dir}")
                        logger.debug(f"Runner output_dir: {runner.output_dir}")
                        logger.debug(f"Loader results_dir: {loader.results_dir}")

                    progress_bar.progress(100)
                    status_text.text("✅ Execution completed successfully!")

                    st.success(
                        f"🎉 Successfully executed {len(selected_tests)} test(s)! Results loaded."
                    )

                    # Forzar recarga de la página para mostrar nuevos resultados
                    st.info(
                        "🔄 Los resultados están disponibles en las pestañas del dashboard. Recarga la página si no los ves."
                    )

                    # Show quick results preview
                    if not df_results.empty:
                        st.markdown("### 📊 Quick Results Preview")
                        st.dataframe(
                            df_results[
                                [
                                    'test_name',
                                    'test_type',
                                    'sharpe_ratio',
                                    'return_pct',
                                    'win_rate',
                                    'max_drawdown',
                                ]
                            ].head(10),
                            width='stretch',
                        )

                        st.info(f"📁 Full results saved to: `{runner.output_dir}`")

                    # Clean up temp config
                    try:
                        temp_config_path.unlink()
                    except BaseException:
                        pass

                    # Reset execute flag after successful execution
                    st.session_state.execute_tests = False
                    logger.info("✅ Ejecución completada, flag reseteado")

                except Exception as e:
                    progress_bar.progress(100)
                    status_text.text("❌ Error during execution")
                    st.error(f"❌ Error executing tests: {e}")
                    logger.error(f"Error executing tests: {e}", exc_info=True)
                    st.exception(e)

                    # Show command as fallback
                    st.markdown("---")
                    st.markdown("### 🚀 Alternative: Run Command Manually")
                    # Obtener selected_tests desde session_state como respaldo
                    tests_for_cmd = st.session_state.get(
                        'selected_tests', selected_tests if 'selected_tests' in locals() else []
                    )
                    if use_multi_strategy:
                        if "multi_strategy" in tests_for_cmd:
                            tests_to_run = ["multi_strategy"] + [
                                t for t in tests_for_cmd if t != "multi_strategy"
                            ]
                        else:
                            tests_to_run = tests_for_cmd
                        cmd = (
                            f"python scripts/run_comprehensive_backtest.py {' '.join(tests_to_run)}"
                        )
                    else:
                        cmd = f"python scripts/run_comprehensive_backtest.py {' '.join(tests_for_cmd)}"
                    st.code(cmd, language="bash")

                    st.session_state.execute_tests = False

            except Exception as e:
                st.error(f"❌ Error preparing execution: {e}")
                logger.error(f"Error preparing execution: {e}", exc_info=True)
                st.exception(e)
                st.session_state.execute_tests = False

    except Exception as e:
        # Catch-all para errores que bloqueen toda la renderización
        st.error("❌ Error crítico en el dashboard")
        st.exception(e)
        logger.error(f"Error crítico en dashboard main(): {e}", exc_info=True)

        # Show minimal working interface
        st.markdown(
            """
        ## 🔧 Dashboard en modo recuperación

        El dashboard encontró un error. Por favor:
        1. Recarga la página (F5 o Cmd+R)
        2. Si persiste, revisa los logs en `logs/errors.log`
        3. Intenta ejecutar el dashboard básico: `python run_dashboard.py`
        """
        )


# Streamlit ejecuta el script directamente, así que siempre llamamos main()
# tanto si se ejecuta como script como si Streamlit lo importa
try:
    main()
except Exception as e:
    # Capturar cualquier error que pueda ocurrir durante la ejecución
    st.error(f"❌ Error crítico al ejecutar el dashboard: {e}")
    st.exception(e)
    import traceback

    st.code(traceback.format_exc(), language="python")
    logger.error(f"Error crítico en dashboard: {e}", exc_info=True)
