# Guía de Implementación - Estrategia Momentum Modular

## Estado Actual

✅ **Completado:**

- Arquitectura base (`BaseFilter`, `MarketAnalyzer`)
- Configuración YAML completa
- Filtro EMA (`EMAFilter`)
- Documentación de diseño técnico

🔄 **En Progreso:**

- Filtros modulares restantes (RSI, StochRSI, Momentum, Volume, ATR)
- Clase principal `ModularMomentumStrategy`
- Risk Manager integrado

## Próximos Pasos de Implementación

### 1. Completar Filtros Modulares

Cada filtro sigue el mismo patrón que `EMAFilter`. Implementar:

#### `rsi_filter.py`

```python
class RSIFilter(BaseFilter):
    def _apply_filter_logic(self, indicators, market_context, signal_type):
        rsi = indicators.get("rsi")
        market_type = market_context.get("type")

        # Obtener thresholds adaptativos según contexto
        adaptive = self.config.get("adaptive_thresholds", {})
        thresholds = adaptive.get(market_type, adaptive.get("balanced", {}))

        if signal_type == "BUY":
            buy_min = thresholds.get("buy_min", 30)
            buy_max = thresholds.get("buy_max", 70)
            passed = buy_min <= rsi <= buy_max
            ...
```

#### `stoch_rsi_filter.py`, `momentum_filter.py`, `volume_filter.py`, `atr_filter.py`

- Similar estructura a `EMAFilter`
- Cada uno evalúa su indicador específico
- Adapta thresholds según preset y contexto de mercado

### 2. Implementar `ModularMomentumStrategy`

```python
class ModularMomentumStrategy(BaseStrategy):
    def __init__(self, config):
        # 1. Cargar configuración YAML
        # 2. Inicializar MarketAnalyzer
        # 3. Inicializar todos los filtros modulares
        # 4. Inicializar RiskManager

    def generate_signal(self, market_data):
        # 1. Analizar contexto de mercado
        market_context = self.market_analyzer.analyze(...)

        # 2. Calcular todos los indicadores
        indicators = self._calculate_indicators(market_data)

        # 3. Evaluar todos los filtros activos
        filter_results = []
        for filter in self.active_filters:
            result = filter.evaluate(indicators, market_context, "BUY")
            filter_results.append(result)

        # 4. Combinar resultados según combination_mode
        combined = self._combine_filter_results(filter_results)

        # 5. Validar con RiskManager
        if combined['passed']:
            risk_check = self.risk_manager.validate(...)
            if risk_check['allowed']:
                return self._create_signal(...)
```

### 3. Risk Manager

Implementar en `modules/risk_manager.py`:

- Validación de exposición máxima
- Cálculo de stop-loss (fijo o dinámico ATR)
- Cálculo de take-profit
- Position sizing

## Estructura de Archivos Final

```
app/strategies/momentum_modular/
├── __init__.py
├── strategy.py              # ModularMomentumStrategy (PRINCIPAL)
├── modules/
│   ├── __init__.py
│   ├── base_filter.py       ✅
│   ├── market_analyzer.py   ✅
│   ├── risk_manager.py      ⏳
│   └── filters/
│       ├── __init__.py      ✅
│       ├── ema_filter.py    ✅
│       ├── rsi_filter.py    ⏳
│       ├── stoch_rsi_filter.py  ⏳
│       ├── momentum_filter.py   ⏳
│       ├── volume_filter.py     ⏳
│       └── atr_filter.py        ⏳
└── config/
    └── momentum_modular.yaml  ✅
```

## Testing

Crear tests unitarios:

1. Por filtro individual
2. Por combinación de filtros
3. Por contexto de mercado
4. Integración completa con backtester

## Migración desde MomentumStrategy Actual

La estrategia actual (`app/strategies/momentum.py`) puede coexistir con la modular.
Para migrar:

1. Mantener `momentum.yaml` para compatibilidad reduzca
2. Usar `momentum_modular.yaml` para nueva estrategia
3. Ambos pueden ejecutarse en paralelo para comparación
