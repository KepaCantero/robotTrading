# TASK-53: Dashboard de Métricas Ajustadas por Riesgo

## 📋 **DESCRIPCIÓN**

Implementar dashboard de métricas ajustadas por riesgo (Sharpe, Max Drawdown, Calmar, Profit Factor, Sortino) para análisis avanzado de performance.

## 🎯 **OBJETIVOS**

- **Dashboard de métricas ajustadas por riesgo** en tiempo real
- **Cálculo de métricas avanzadas** (Sharpe, Calmar, Sortino, Profit Factor)
- **Visualización interactiva** de performance
- **Comparación de estrategias** por métricas de riesgo
- **Alertas automáticas** por métricas críticas

## 🏗️ **COMPONENTES A IMPLEMENTAR**

### **1. Risk-Adjusted Metrics Calculator**

```python
class RiskAdjustedMetricsCalculator:
    def __init__(self, config: MetricsConfig):
        self.config = config
        self.metrics_cache: Dict[str, RiskAdjustedMetrics] = {}

    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float) -> SharpeRatio:
        """Calcular ratio de Sharpe"""
        pass

    def calculate_calmar_ratio(self, returns: List[float], max_drawdown: float) -> CalmarRatio:
        """Calcular ratio de Calmar"""
        pass

    def calculate_sortino_ratio(self, returns: List[float], target_return: float) -> SortinoRatio:
        """Calcular ratio de Sortino"""
        pass

    def calculate_profit_factor(self, trades: List[Trade]) -> ProfitFactor:
        """Calcular profit factor"""
        pass
```

### **2. Performance Dashboard**

```python
class PerformanceDashboard:
    def __init__(self, config: DashboardConfig):
        self.config = config
        self.dashboard_widgets: List[DashboardWidget] = []

    def create_metrics_dashboard(self, strategies: List[BaseStrategy]) -> MetricsDashboard:
        """Crear dashboard de métricas"""
        pass

    def create_comparison_dashboard(self, strategies: List[BaseStrategy]) -> ComparisonDashboard:
        """Crear dashboard de comparación"""
        pass

    def create_risk_dashboard(self, portfolio: Portfolio) -> RiskDashboard:
        """Crear dashboard de riesgo"""
        pass
```

### **3. Metrics Alert System**

```python
class MetricsAlertSystem:
    def __init__(self, config: AlertConfig):
        self.config = config
        self.alert_thresholds: Dict[str, float] = {}
        self.active_alerts: List[MetricsAlert] = []

    def check_sharpe_threshold(self, sharpe_ratio: float) -> Optional[MetricsAlert]:
        """Verificar threshold de Sharpe"""
        pass

    def check_drawdown_threshold(self, max_drawdown: float) -> Optional[MetricsAlert]:
        """Verificar threshold de drawdown"""
        pass

    def check_profit_factor_threshold(self, profit_factor: float) -> Optional[MetricsAlert]:
        """Verificar threshold de profit factor"""
        pass
```

## 📊 **ARCHIVOS A CREAR**

- `app/services/risk_adjusted_metrics_calculator.py` - Calculador de métricas ajustadas por riesgo
- `app/services/performance_dashboard.py` - Dashboard de performance
- `app/services/metrics_alert_system.py` - Sistema de alertas de métricas
- `app/models/risk_metrics.py` - Modelos para métricas de riesgo
- `app/api/risk_metrics.py` - API endpoints para métricas
- `tests/test_risk_adjusted_metrics_calculator.py` - Tests del calculador
- `tests/test_performance_dashboard.py` - Tests del dashboard
- `tests/test_metrics_alert_system.py` - Tests del sistema de alertas

## 🧪 **TESTS REQUERIDOS**

### **Risk-Adjusted Metrics Calculation Tests**

- Test de cálculo de ratio de Sharpe
- Test de cálculo de ratio de Calmar
- Test de cálculo de ratio de Sortino
- Test de cálculo de profit factor

### **Performance Dashboard Tests**

- Test de creación de dashboard de métricas
- Test de creación de dashboard de comparación
- Test de creación de dashboard de riesgo
- Test de visualización interactiva

### **Metrics Alert System Tests**

- Test de verificación de threshold de Sharpe
- Test de verificación de threshold de drawdown
- Test de verificación de threshold de profit factor
- Test de alertas automáticas

## ✅ **CRITERIOS DE ÉXITO**

- [ ] Dashboard de métricas ajustadas por riesgo implementado
- [ ] Cálculo de métricas avanzadas funcional
- [ ] Visualización interactiva de performance implementada
- [ ] Comparación de estrategias por métricas funcional
- [ ] Alertas automáticas por métricas críticas implementadas
- [ ] API endpoints para métricas de riesgo
- [ ] > 90% test coverage
- [ ] Integración con TASK 20 (Monitoring y Observabilidad)

## 🔗 **DEPENDENCIAS**

- ✅ TASK 20 (Monitoring y Observabilidad) - Ready
- ✅ TASK-R7 (Monitoreo y Alertas de Riesgo) - Ready
- ✅ TASK-31 (Sistema de Estrategias Múltiples) - Ready

## 📈 **PRIORIDAD**

**🔵 FASE AVANZADA** - Para análisis avanzado de performance

## 🎯 **FASE**

**FASE AVANZADA** - Implementar después de validación completa
