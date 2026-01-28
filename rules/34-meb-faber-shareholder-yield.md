# 🟠 34. "Shareholder Yield" - Meb Faber

## REGLAS DE INVERSIÓN EN DIVIDENDOS Y SHAREHOLDER YIELD

**Regla 34.1 — Métrica Total Yield**

Claude DEBE usar Total Yield, NO solo Dividend Yield.

**Total Yield = Dividend Yield + Buyback Yield + Net Debt Paydown Yield.**

```python
def calculate_total_shareholder_yield(
    self,
    dividend_yield: float,
    buyback_yield: float,
    net_debt_paydown_yield: float
) -> dict:
    """
    Calcular Total Shareholder Yield.

    Faber: Dividend Yield solo cuenta 1/3 del retorno al accionista.
    """
    total_yield = (
        dividend_yield +
        buyback_yield +
        net_debt_paydown_yield
    )

    logger.info(
        f"Total Shareholder Yield: {total_yield:.2%} "
        f"(Div={dividend_yield:.2%}, Buyback={buyback_yield:.2%}, "
        f"Debt={net_debt_paydown_yield:.2%})"
    )

    # Breakdown
    dividend_pct = dividend_yield / total_yield if total_yield > 0 else 0
    buyback_pct = buyback_yield / total_yield if total_yield > 0 else 0
    debt_pct = net_debt_paydown_yield / total_yield if total_yield > 0 else 0

    return {
        'total_yield': total_yield,
        'dividend_yield': dividend_yield,
        'buyback_yield': buyback_yield,
        'net_debt_paydown_yield': net_debt_paydown_yield,
        'dividend_pct': dividend_pct,
        'buyback_pct': buyback_pct,
        'debt_pct': debt_pct
    }
```

**Regla 34.2 — Filtro de Recompras Activas**

```python
def buyback_preference_filter(
    self,
    dividend_yield: float,
    buyback_yield: float,
    tax_profile: str  # 'TAXABLE', 'RETIREMENT', 'FOUNDATIONS'
) -> float:
    """
    Priorizar recompras activas (más eficientes fiscalmente).

    Faber: Buybacks > Dividendos para perfiles sujetos a impuestos.
    """
    # En perfiles sujetos a impuestos, recompras son más eficientes
    if tax_profile == 'TAXABLE':
        # Penalización fiscal: dividendos gravados inmediatamente
        tax_penalty = 0.15  # 15% penalty

        # Ajustar yield neto
        dividend_net = dividend_yield * (1 - tax_penalty)
        buyback_net = buyback_yield  # No taxed until sale

        if buyback_yield > dividend_yield:
            logger.info(
                f"Buyback preference: {buyback_yield:.2%} > "
                f"{dividend_yield:.2%} (tax-efficient)"
            )
            return buyback_net + dividend_net

    return dividend_yield + buyback_yield
```

**Regla 34.3 — Filtro de Deuda (Trampa de Liquidez)**

```python
def debt_trap_filter(
    self,
    dividend_yield: float,
    net_debt_change: float,  # Cambio en deuda neta (% de market cap)
    free_cash_flow: float
) -> bool:
    """
    Si deuda aumenta mientras pagan dividendos → DESCALIFICAR.

    Faber: Trampa de liquidez = endeudarse para pagar dividendos.
    """
    # Si deuda neta aumenta
    if net_debt_change > 0:
        # Y pagan dividendos
        if dividend_yield > 0.02:  # > 2%
            logger.warning(
                f"❌ DEBT TRAP: Net debt +{net_debt_change:.1%} "
                f"while paying {dividend_yield:.1%} dividends. "
                f"Unsustainable."
            )
            return False

        # Chequear si FCF cubre dividendos
        fcf_coverage = free_cash_flow / dividend_yield if dividend_yield > 0 else float('inf')

        if fcf_coverage < 1.0:
            logger.error(
                f"❌ FCF ({free_cash_flow:.2%}) doesn't cover "
                f"dividends ({dividend_yield:.2%})"
            )
            return False

    return True
```

**Regla 34.4 — Evitar "Yield Traps"**

```python
def yield_trap_filter(
    self,
    dividend_yield: float,
    all_yields: pd.Series,
    exclude_decile: bool = True
) -> bool:
    """
    Excluir decil con yield más alto (suelen ser empresas en distress).

    Faber: Yield extremo → distress financiero, no oportunidad.
    """
    if not exclude_decile:
        return True

    # Calcular percentil del yield
    yield_percentile = (all_yields < dividend_yield).sum() / len(all_yields)

    # Top decil (10% más alto)
    if yield_percentile >= 0.90:
        logger.warning(
            f"⚠️ YIELD TRAP: Dividend yield {dividend_yield:.1%} "
            f"in top decile ({yield_percentile:.1%}). "
            f"Potential distress."
        )
        return False

    return True
```

**Regla 34.5 — Valoración Relativa**

```python
def valuation_yield_filter(
    self,
    dividend_yield: float,
    pe_ratio: float,
    ps_ratio: float,
    max_pe: float = 25.0,
    max_ps: float = 5.0
) -> bool:
    """
    Yield debe venir de activos con valoración razonable.

    Faber: P/E y P/S excesivos → sobrevalorado.
    """
    if pe_ratio > max_pe:
        logger.warning(
            f"⚠️ High valuation: P/E {pe_ratio:.1f} > {max_pe:.0f}. "
            f"Yield may not compensate."
        )
        return False

    if ps_ratio > max_ps:
        logger.warning(
            f"⚠️ High valuation: P/S {ps_ratio:.1f} > {max_ps:.0f}"
        )
        return False

    logger.info(
        f"✅ Reasonable valuation: P/E={pe_ratio:.1f}, P/S={ps_ratio:.1f}"
    )

    return True
```

**Regla 34.6 — Consistencia de Flujo de Caja**

```python
def fcf_coverage_requirement(
    self,
    free_cash_flow: float,
    total_shareholder_yield: float,
    min_coverage: float = 1.2
) -> bool:
    """
    FCF positivo debe cubrir 1.2x el total yield.

    Faber: Flujo de caja libre = sustainablity.
    """
    if free_cash_flow <= 0:
        logger.error("❌ Negative FCF. Dividends unsustainable.")
        return False

    coverage_ratio = free_cash_flow / total_shareholder_yield

    if coverage_ratio < min_coverage:
        logger.warning(
            f"⚠️ Low FCF coverage: {coverage_ratio:.2f}x "
            f"< {min_coverage:.1f}x required"
        )
        return False

    logger.info(
        f"✅ FCF coverage: {coverage_ratio:.2f}x "
        f"(FCC={free_cash_flow:.2%}, Yield={total_shareholder_yield:.2%})"
    )

    return True
```

**Regla 34.7 — Net Issuance**

```python
def net_issuance_adjustment(
    self,
    total_yield: float,
    net_share_issuance: float  # Positive = issuing, Negative = buying back
) -> float:
    """
    Si empresa emite acciones, restar del yield.

    Faber: Net Issuance = dilución del accionista.
    """
    if net_share_issuance > 0:
        adjusted_yield = total_yield - net_share_issuance

        logger.info(
            f"Net issuance adjustment: {total_yield:.2%} → "
            f"{adjusted_yield:.2%} (-{net_share_issuance:.2%})"
        )

        return adjusted_yield

    return total_yield
```

**Regla 34.8 — Efecto Impuestos en Backtest**

```python
def tax_adjusted_yield(
    self,
    dividend_yield: float,
    buyback_yield: float,
    dividend_tax_rate: float = 0.20,  # 20% qualified dividends
    capital_gains_rate: float = 0.15  # 15% long-term
) -> dict:
    """
    Aplicar penalización 15-20% extra a dividendos vs recompras.

    Faber: Backtest debe reflejar realidad fiscal.
    """
    # Dividendos: gravados inmediatamente
    dividend_after_tax = dividend_yield * (1 - dividend_tax_rate)

    # Recompras: gravados al realizar ganancia (diferido)
    # Penalización menor por diferimiento
    buyback_after_tax = buyback_yield * (1 - capital_gains_rate * 0.5)

    tax_disadvantage = dividend_after_tax - buyback_after_tax

    logger.info(
        f"Tax-adjusted: Div={dividend_after_tax:.2%}, "
        f"Buyback={buyback_after_tax:.2%}, "
        f"Disadvantage={tax_disadvantage:.2%}"
    )

    return {
        'dividend_after_tax': dividend_after_tax,
        'buyback_after_tax': buyback_after_tax,
        'tax_disadvantage': tax_disadvantage
    }
```

**Regla 34.9 — Métrica de Cash**

```python
def cash_potential_yield(
    self,
    net_cash_position: float,  # % de market cap
    profile_type: str  # 'GROWTH', 'VALUE', 'INCOME'
) -> float:
    """
    Caja neta = potencial de yield futuro.

    Faber: En perfiles crecimiento, cash es opción estratégica.
    """
    if profile_type != 'GROWTH':
        return 0.0

    # Cash como potencial yield (opcionalidad)
    # Solo si cash > 10% de market cap
    if net_cash_position > 0.10:
        potential_yield = net_cash_position * 0.05  # 5% potencial

        logger.info(
            f"Net cash {net_cash_position:.1%} = "
            f"potential future yield {potential_yield:.2%}"
        )

        return potential_yield

    return 0.0
```

**Regla 34.10 — Rebalanceo Trimestral**

```python
def quarterly_rebalance_signal(
    self,
    last_rebalance_date: datetime,
    current_date: datetime,
    max_days: int = 90
) -> bool:
    """
    Shareholder Yield degrada si no se refresca cada 90 días.

    Faber: Rebalanceo trimestral obligatorio.
    """
    days_since_rebalance = (current_date - last_rebalance_date).days

    if days_since_rebalance > max_days:
        logger.info(
            f"Rebalance due: {days_since_rebalance} days since last"
        )
        return True

    return False
```

**Regla 34.11 — Filtro de Sector**

```python
def sector_concentration_yield_filter(
    self,
    portfolio: pd.DataFrame,  # columns: symbol, sector, weight, yield
    max_sector_exposure: float = 0.30  # 30%
) -> dict:
    """
    No permitir que Financials/REITs dominen solo por yield.

    Faber: Diversificación sectorial > yield nominal.
    """
    # Exposición por sector
    sector_exposure = portfolio.groupby('sector')['weight'].sum()

    # Chequear sectores de alto yield
    high_yield_sectors = ['Financials', 'REITs', 'Utilities']

    for sector in high_yield_sectors:
        if sector in sector_exposure.index:
            exposure = sector_exposure[sector]

            if exposure > max_sector_exposure:
                logger.warning(
                    f"⚠️ Sector concentration: {sector} = {exposure:.1%} "
                    f"> {max_sector_exposure:.0%} (yield bias)"
                )

                return {
                    'balanced': False,
                    'overconcentrated_sector': sector,
                    'exposure': exposure
                }

    return {'balanced': True}
```

**Regla 34.12 — Dividend Growth vs. Yield**

```python
def dividend_growth_preference(
    self,
    dividend_yield: float,
    dividend_growth_rate: float,
    min_growth: float = 0.05  # 5%
) -> float:
    """
    Priorizar crecimiento del dividendo sobre yield absoluto.

    Faber: Dividend Growth > Yield para largo plazo.
    """
    if dividend_growth_rate < min_growth:
        # Dividendo estancado o decreciente
        logger.warning(
            f"⚠️ Low dividend growth: {dividend_growth_rate:.1%} "
            f"< {min_growth:.0%}. Yield may be 'value trap'."
        )
        return dividend_yield * 0.5  # Penalizar

    # Crecimiento fuerte → preferir
    if dividend_growth_rate > 0.10:  # > 10%
        adjusted_score = dividend_yield * 1.5  # Bonus

        logger.info(
            f"✅ Strong dividend growth: {dividend_growth_rate:.1%}. "
            f"Premium yield."
        )

        return adjusted_score

    return dividend_yield
```

**Regla 34.13 — Correlación con Tipos de Interés**

```python
def rate_correlation_adjustment(
    self,
    dividend_yield: float,
    interest_rate_change: float,  # Cambio en tasas (ej: +0.25%)
    duration: float  # Duración del activo
) -> float:
    """
    Si tipos suben, reducir exposición a dividendos altos.

    Faber: Dividendos actúan como bonos (sensibles a tipos).
    """
    # Si tipos suben
    if interest_rate_change > 0:
        # Alta duración + alto yield = sensibilidad a tipos
        duration_adjustment = -duration * interest_rate_change * 2

        adjusted_yield = dividend_yield + duration_adjustment

        logger.info(
            f"Rate correlation: Rates +{interest_rate_change:.2%}, "
            f"Yield {dividend_yield:.2%} → {adjusted_yield:.2%}"
        )

        return max(0, adjusted_yield)

    return dividend_yield
```

**Regla 34.14 — Small Caps Advantage**

```python
def small_cap_yield_boost(
    self,
    market_cap: float,
    dividend_yield: float,
    small_cap_threshold: float = 2e9  # 2B USD
) -> float:
    """
    Shareholder yield más potente en Small/Mid caps.

    Faber: Small caps tienen más room para revaloración.
    """
    if market_cap < small_cap_threshold:
        # Boost factor para small caps
        boost = 1.2  # +20%

        adjusted_yield = dividend_yield * boost

        logger.info(
            f"Small cap yield boost: ${market_cap/1e9:.1f}B, "
            f"Yield {dividend_yield:.2%} → {adjusted_yield:.2%}"
        )

        return adjusted_yield

    return dividend_yield
```

**Regla 34.15 — Integración con Momentum**

```python
def dividend_momentum_filter(
    self,
    dividend_yield: float,
    momentum_6m: float
) -> bool:
    """
    Solo entrar en alto yield si momentum 6M > 0.

    Faber: Evitar "falling knife" con alto yield.
    """
    min_yield = 0.03  # 3%

    if dividend_yield > min_yield:
        # Alto yield: chequear momentum
        if momentum_6m < 0:
            logger.warning(
                f"⚠️ HIGH YIELD FALLING KNIFE: "
                f"Yield={dividend_yield:.1%}, "
                f"Momentum={momentum_6m:.1%}. Avoid."
            )
            return False

        logger.info(
            f"✅ High yield with momentum: "
            f"Yield={dividend_yield:.1%}, Mom={momentum_6m:.1%}"
        )

    return True
```
