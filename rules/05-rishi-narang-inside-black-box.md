# 📕 5. "Inside the Black Box" - Rishi K. Narang

## REGLAS DE ARQUITECTURA DE QUANT FUNDS

**SIEMPRE separa Alpha Model de Risk Model**

```python
class AlphaModel:
    """Genera señales de trading (dirección y confianza)."""
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        # Retorna: symbol, direction (+1/-1), confidence (0-1)
        pass

class RiskModel:
    """Gestiona exposiciones y constraints."""
    def apply_constraints(self, signals: pd.DataFrame) -> pd.DataFrame:
        # Retorna: señales filtradas por risk limits
        pass

class PortfolioConstructor:
    """Combina alpha y risk para generar portfolio."""
    def __init__(self, alpha_model: AlphaModel, risk_model: RiskModel):
        self.alpha = alpha_model
        self.risk = risk_model

    def construct_portfolio(self, data: pd.DataFrame) -> pd.Series:
        signals = self.alpha.generate_signals(data)
        filtered_signals = self.risk.apply_constraints(signals)
        weights = self._optimize_weights(filtered_signals)
        return weights
```

**Risk Model: Limita factor exposures (sector, country, etc.)**

```python
def apply_factor_constraints(
    self,
    weights: pd.Series,
    factor_loadings: pd.DataFrame,
    max_factor_exposure: float = 0.15
) -> pd.Series:
    """
    Limitar exposure a cada factor (e.g., sector, country).

    Example: Max 15% exposure to Tech sector.
    """
    constrained_weights = weights.copy()

    for factor in factor_loadings.columns:
        # Calcular exposure a este factor
        factor_exposure = (weights * factor_loadings[factor]).sum()

        if abs(factor_exposure) > max_factor_exposure:
            # Reducir weights proporcionalmente
            scale_factor = max_factor_exposure / abs(factor_exposure)

            # Aplicar solo a assets que contribuyen a excess exposure
            if factor_exposure > 0:
                mask = factor_loadings[factor] > 0
            else:
                mask = factor_loadings[factor] < 0

            constrained_weights[mask] *= scale_factor

    # Renormalize
    constrained_weights /= constrained_weights.sum()

    return constrained_weights
```

**Transaction Cost Model: Divide en componentes**

```python
def calculate_transaction_costs(
    self,
    symbol: str,
    order_size: Decimal,
    market_data: Quote
) -> Decimal:
    """
    Total transaction cost = commission + spread + market impact + timing cost.
    """
    # 1. Commission (fijo)
    commission = Decimal("5.0")  # €5 per trade

    # 2. Spread cost
    spread = market_data.ask - market_data.bid
    spread_cost = spread * order_size / 2  # Pagar la mitad del spread

    # 3. Market impact (permanent)
    adv = self.get_average_daily_volume(symbol)
    participation_rate = order_size / adv

    # Square-root model (Almgren-Chriss)
    volatility = self.get_volatility(symbol)
    market_impact = Decimal(str(
        0.1 * volatility * np.sqrt(float(participation_rate))
    )) * market_data.last * order_size

    # 4. Timing cost (temporary)
    # Si orden tarda T horas, precio puede moverse
    expected_duration_hours = max(1, float(order_size / adv) * 6.5)  # 6.5h trading day
    timing_risk = Decimal(str(
        volatility * np.sqrt(expected_duration_hours / 252 / 6.5)
    )) * market_data.last * order_size

    total_cost = commission + spread_cost + market_impact + timing_risk

    return total_cost
```

**Execution Algorithm: VWAP para órdenes grandes**

```python
def vwap_execution(
    self,
    symbol: str,
    total_quantity: Decimal,
    start_time: datetime,
    end_time: datetime
) -> List[Order]:
    """
    VWAP (Volume-Weighted Average Price) execution.

    Dividir orden en child orders proporcionales a volumen histórico.
    """
    # 1. Obtener historical volume profile
    historical_volume = self.get_intraday_volume_profile(symbol)

    # 2. Dividir tiempo en slices (e.g., cada 5 minutos)
    time_slices = pd.date_range(start_time, end_time, freq='5T')

    # 3. Distribuir quantity proporcional a expected volume
    orders = []

    for i, slice_time in enumerate(time_slices[:-1]):
        # Expected volume en este slice
        expected_vol_pct = historical_volume.loc[slice_time.time()]['volume_pct']

        # Quantity para este slice
        slice_quantity = total_quantity * Decimal(str(expected_vol_pct))

        orders.append(Order(
            symbol=symbol,
            quantity=slice_quantity,
            execution_time=slice_time,
            order_type="LIMIT",  # VWAP usa limit orders
            limit_price=None  # Set dinámicamente
        ))

    return orders
```

**NUNCA uses Market Orders para órdenes > 1% ADV**

```python
def validate_order_type(
    self,
    order_size: Decimal,
    adv: Decimal,
    order_type: str
) -> bool:
    """
    Market orders solo para órdenes pequeñas.

    Órdenes grandes DEBEN usar execution algorithms.
    """
    participation_rate = float(order_size / adv)

    if order_type == "MARKET" and participation_rate > 0.01:
        logger.error(
            f"❌ Market order for {participation_rate:.1%} of ADV - "
            "Use execution algorithm (VWAP/TWAP/IS)"
        )
        return False

    return True
```

**Data Quality Checks: SIEMPRE valida antes de usar**

```python
def validate_market_data(self, quote: Quote) -> bool:
    """
    Validar data quality antes de generar señales.

    Bad data = bad signals = losses.
    """
    # 1. Check for stale data
    if (datetime.now() - quote.timestamp).seconds > 300:  # 5 minutos
        logger.warning(f"⚠️ Stale data: {quote.symbol} - {quote.timestamp}")
        return False

    # 2. Check bid <= last <= ask
    if not (quote.bid <= quote.last <= quote.ask):
        logger.error(f"❌ Invalid prices: bid={quote.bid}, last={quote.last}, ask={quote.ask}")
        return False

    # 3. Check for zero volume
    if quote.volume == 0:
        logger.warning(f"⚠️ Zero volume: {quote.symbol}")
        return False

    # 4. Check for suspicious jumps (>10% intraday)
    if hasattr(self, 'last_price'):
        price_change = abs(quote.last - self.last_price[quote.symbol]) / self.last_price[quote.symbol]

        if price_change > 0.10:
            logger.warning(f"⚠️ Large price jump: {quote.symbol} - {price_change:.1%}")
            # Podría ser halt, corporate action, o bad data
            return False

    return True
```
