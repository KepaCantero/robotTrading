# Resumen de Ejecuciones - Profile-Driven Trading

Fecha: 2026-01-24

## Combinaciones Ejecutadas

| # | Archivo | Capital | Objetivo | Riesgo | Horizonte | Target Mensual | Estado |
|---|---------|---------|----------|--------|-----------|-----------------|--------|
| 1 | `conservador_50k_bajo.json` | €50,000 | Preservar Capital | Bajo | 12 meses | €500 | ✅ SUCCESS |
| 2 | `agresivo_100k_alto.json` | €100,000 | Maximizar Capital | Alto | 12 meses | €5,000 | ✅ SUCCESS |
| 3 | `balanceado_75k_medio_24m.json` | €75,000 | Crecimiento Equilibrado | Medio | 24 meses | €1,500 | ✅ SUCCESS |
| 4 | `dividendos_150k_medio_36m.json` | €150,000 | Maximizar Dividendos | Medio | 36 meses | €2,500 | ✅ SUCCESS |
| 5 | `growth_250k_bajo_48m.json` | €250,000 | Maximizar Capital | Bajo | 48 meses | €4,000 | ✅ SUCCESS |
| 6 | `income_200k_bajo_60m.json` | €200,000 | Maximizar Dividendos | Bajo | 60 meses | €3,000 | ✅ SUCCESS |

## Configuración Común

Todas las ejecuciones utilizaron:
- **Broker**: Mock/Paper (no IBKR)
- **RL Signals**: Enabled
- **Tax Optimization**: Enabled
- **Backtest Validation**: Enabled
- **Risk Gates**: Enabled
- **Auto-Execute**: Disabled (dry-run mode)

## Comandos Ejecutados

```bash
# 1. Perfil Conservador
python run_profile_driven_trading.py run \
  --capital 50000 \
  --objective preservar_capital \
  --risk bajo \
  --horizon 12 \
  --target-monthly 500 \
  --no-ibkr \
  --report-path results/profile_driven_trading/conservador_50k_bajo.json

# 2. Perfil Agresivo
python run_profile_driven_trading.py run \
  --capital 100000 \
  --objective maximizar_capital \
  --risk alto \
  --horizon 12 \
  --target-monthly 5000 \
  --no-ibkr \
  --report-path results/profile_driven_trading/agresivo_100k_alto.json

# 3. Perfil Balanceado
python run_profile_driven_trading.py run \
  --capital 75000 \
  --objective crecimiento_equilibrado \
  --risk medio \
  --horizon 24 \
  --target-monthly 1500 \
  --no-ibkr \
  --report-path results/profile_driven_trading/balanceado_75k_medio_24m.json

# 4. Perfil Dividendos
python run_profile_driven_trading.py run \
  --capital 150000 \
  --objective maximizar_dividendos \
  --risk medio \
  --horizon 36 \
  --target-monthly 2500 \
  --no-ibkr \
  --report-path results/profile_driven_trading/dividendos_150k_medio_36m.json

# 5. Perfil Growth Alto Capital
python run_profile_driven_trading.py run \
  --capital 250000 \
  --objective maximizar_capital \
  --risk bajo \
  --horizon 48 \
  --target-monthly 4000 \
  --no-ibkr \
  --report-path results/profile_driven_trading/growth_250k_bajo_48m.json

# 6. Perfil Income Generation
python run_profile_driven_trading.py run \
  --capital 200000 \
  --objective maximizar_dividendos \
  --risk bajo \
  --horizon 60 \
  --target-monthly 3000 \
  --no-ibkr \
  --report-path results/profile_driven_trading/income_200k_bajo_60m.json
```

## Estructura del Reporte JSON

Cada reporte contiene:

```json
{
  "timestamp": "ISO timestamp",
  "input": {
    "capital": float,
    "objective": string,
    "risk": string,
    "horizon_months": int,
    "target_monthly": float
  },
  "config": {
    "enable_rl_signals": bool,
    "enable_tax_optimization": bool,
    "enable_backtest_validation": bool,
    "enable_risk_gates": bool,
    "auto_execute_trades": bool,
    "use_ibkr": bool
  },
  "profile": {
    "profile_id": "PROF-XXXXXXXX"
  },
  "allocation": {
    "total_positions": int,
    "residual_capital": float,
    "positions": []
  },
  "signals": {
    "total_signals": int,
    "buy_signals": int,
    "sell_signals": int,
    "hold_signals": int
  },
  "stages": {
    "profile_generation": {...},
    "universe_selection": {...},
    "capital_allocation": {...},
    "signal_generation": {...},
    "tax_optimization": {...},
    "risk_validation": {...},
    "backtest_validation": {...},
    "trade_execution": {...}
  },
  "execution": {
    "dry_run": bool,
    "orders_submitted": int,
    "orders_filled": int
  },
  "risk": {
    "passed": bool,
    "risk_level": "LOW|MEDIUM|HIGH"
  },
  "summary": {
    "success": bool,
    "execution_time_seconds": float,
    "successful_stages": int
  }
}
```

## Observaciones

- ✅ **Todas las ejecuciones fueron exitosas** (8/8 stages completados)
- ✅ **Todas pasaron la validación de riesgo** (risk_level: LOW)
- ⚠️ **No se generaron posiciones** debido a datos de prueba mock (yfinance no disponible en Python 3.9)
- ✅ **Tiempo de ejecución promedio**: ~0.8-1.0 segundos

## Próximos Pasos

1. **Conectar yfinance o datos reales**: Para obtener datos de mercado reales
2. **Habilitar IBKR**: Usar `--use-ibkr` para conectar con Interactive Brokers real
3. **Activar auto-execute**: Usar `--auto-execute` para ejecutar trades reales (CUIDADO)
4. **Ajustar parámetros**: Optimizar según resultados del backtest
