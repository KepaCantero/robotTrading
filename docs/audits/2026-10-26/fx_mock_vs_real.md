# FX: mock vs real (Bloque 3 — T3.4)

26-10-2026 · commit 457dbb85. Fuentes: ECB Data Portal (cierres diarios de
referencia, derivación exacta por cruces EUR) + FRED (tipos de política /
interbancario 3M). Antes: constantes hardcodeadas en `forex_data_service.py`.

## Precios: constante inventada vs fix real

| Par | Mock (constante) | Real 2024-06-28 | Real 2026-10-20 | Última vs mock |
|---|---|---|---|---|
| EUR/USD | 1.08 | 1.0717 | 1.0821 | +0.2% |
| USD/JPY | 150.0 | 160.62 | 158.13 | **+5.4%** |
| GBP/USD | 1.25 | 1.2648 | 1.3347 | **+6.8%** |
| AUD/USD | 0.65 | 0.6658 | 0.6985 | **+7.5%** |
| USD/CAD | 1.35 | 1.3704 | 1.4051 | **+4.1%** |
| NZD/USD | 0.60 | 0.6082 | 0.5679 | **−5.4%** |
| USD/CHF | 0.88 | 0.9000 | 0.8236 | **−6.4%** |

Una cartera FX "hedged" con estas constantes cargaba desvíos de ±7% por
par antes de abrir posición. El carry además era una foto congelada de
2023-24 (Fed 5.25%) que ya no existe.

## Diferenciales de tipos (lo que el carry COBRA de verdad)

| Par | Mock (pp) | Real jun-2024 (pp) |
|---|---|---|
| USD/JPY | +5.25 | +5.35 |
| AUD/USD | −1.00 | −1.11 |
| NZD/USD | +0.25 | +0.12 |

El signo coincide (el mock estaba calibrado a ojo sobre la misma época);
la magnitud y, sobre todo, la EVOLUCIÓN temporal (cortes de la Fed 2024-25,
subidas del BoJ) solo existen con datos reales y fecha de observación PIT.

## Qué cambió en el código

- `ForexDataService` lee el corpus local (sin red); las constantes
  sobreviven SOLO como fallback paper/live con warning ruidoso.
- Backtests: `FxHistory` estricto — par/fecha sin cobertura → `None`
  (D04), nunca número inventado. Hueco >7d (FX) / >120d (tipos mensuales)
  = hueco declarado.
- Dukascopy (freeserv) bloquea acceso programático: anotado como upgrade
  intradía futuro, no como fuente de hoy.

Regenerar corpus: `python scripts/download_fx.py` (ECB+FRED, ~10s).
