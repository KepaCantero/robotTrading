# Central Config Consolidation - Prompt

**Tarea ID:** 26_central_config_consolidation
**Propósito:** Centralizar todos los parámetros del proyecto
**Tiempo estimado:** 8 horas
**Prioridad:** P0 (Crítica para producción)

---

## OBJETIVO

Consolidar TODOS los parámetros del proyecto en un sistema de configuración centralizado.

## ESTRUCTURA

```
app/shared/config/
├── __init__.py
├── central_config.py      # Config principal con dataclasses
├── trading_thresholds.py  # R1-R4, position sizes
├── timing_config.py       # R9, execution windows
├── api_endpoints.py       # URLs, timeouts
├── risk_parameters.py     # R2, R10, stop losses
└── environment.py         # Carga desde .env
```

## PARÁMETROS A CENTRALIZAR

### Trading (trading_thresholds.py)
- KELLY_FRACTION = 0.02
- MAX_POSITION_SIZE = 0.02
- MAX_DRAWDOWN_PCT = 0.15
- MIN_RR_RATIO = 2.0
- TRAILING_STOP_PCT = 0.10
- PARTIAL_TP_PCT = 0.05

### Timing (timing_config.py)
- MARKET_OPEN_HOUR = 9.5
- MARKET_CLOSE_HOUR = 16.0
- AVOID_FIRST_MINUTES = 30
- AVOID_LAST_MINUTES = 30
- LUNCH_START_HOUR = 12
- LUNCH_END_HOUR = 13

### API (api_endpoints.py)
- ALPACA_BASE_URL
- ALPACA_DATA_URL
- REQUEST_TIMEOUT_SECONDS
- MAX_RETRIES

## SUCCESS CRITERIA

- [ ] Todos los magic numbers extraídos
- [ ] CentralConfig creado con dataclasses
- [ ] Tests de validación de config
- [ ] Documentación actualizada
