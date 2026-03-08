# Specialized Libraries - Prompt

**Tarea ID:** 27_specialized_libraries
**Propósito:** Migrar cálculos a librerías especializadas
**Tiempo estimado:** 6 horas
**Prioridad:** P1 (Importante)

---

## OBJETIVO

Usar numpy, pandas, scipy para todos los cálculos numéricos y estadísticos.

## LIBRERÍAS

### numpy
- Operaciones vectorizadas
- Cálculos de arrays
- Funciones matemáticas

### pandas
- Time series operations
- Rolling calculations
- Data manipulation

### scipy
- Estadística (stats)
- Optimización (optimize)
- Señales (signal)

### scikit-learn
- TimeSeriesSplit para validación
- Preprocessing
- Metrics

## MIGRACIONES

| Cálculo Actual | Librería |
|----------------|----------|
| for loops para sumas | numpy.sum() |
| manual moving average | pandas.rolling().mean() |
| manual std dev | numpy.std() / pandas.std() |
| VaR calculation | scipy.stats.norm.ppf() |
| Correlation matrix | numpy.corrcoef() |
| Time series split | sklearn TimeSeriesSplit |

## SUCCESS CRITERIA

- [ ] No hay for loops para cálculos numéricos
- [ ] scipy usado para estadística
- [ ] pandas usado para time series
- [ ] numpy usado para operaciones vectorizadas
