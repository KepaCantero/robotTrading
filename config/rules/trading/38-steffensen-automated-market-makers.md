# 🪙 38. "Automated Market Makers" - Steffensen et al.

## REGLAS DE AMM EN DEX (Uniswap, Curve, etc.)

**Regla 38.1 — Constant Product Formula**

Claude DEBE calcular slippage teórico ANTES de lanzar órdenes en DEX.

**x · y = k es la base de Uniswap.**

```python
def calculate_dex_slippage(
    self,
    reserve_x: float,
    reserve_y: float,
    trade_amount_x: float,
    fee_rate: float = 0.003  # 0.3%
) -> dict:
    """
    Calcular slippage usando x · y = k.

    Steffensen: AMM math para trades DEX.
    """
    # Constant product
    k = reserve_x * reserve_y

    # Con fee
    input_with_fee = trade_amount_x * (1 - fee_rate)

    # Nuevo x despues del trade
    new_x = reserve_x + input_with_fee

    # Nuevo y (manteniendo k)
    new_y = k / new_x

    # Output recibido
    output_y = reserve_y - new_y

    # Slippage
    expected_price = reserve_y / reserve_x
    actual_price = output_y / trade_amount_x

    slippage = (expected_price - actual_price) / expected_price

    logger.info(
        f"DEX trade: In={trade_amount_x:.4f}, Out={output_y:.4f}, "
        f"Slippage={slippage:.2%}"
    )

    return {
        'output_amount': output_y,
        'slippage_pct': slippage,
        'new_reserve_x': new_x,
        'new_reserve_y': new_y
    }
```

**Regla 38.2 — Impermanent Loss (IL) Buffer**

```python
def impermanent_loss_check(
    self,
    initial_price: float,
    current_price: float,
    volatility_forecast: float,
    fee_apr: float
) -> bool:
    """
    NO proveer liquidez si volatilidad esperada > 2x fees.

    Steffensen: IL > fees = pérdida neta.
    """
    # IL estimado
    price_ratio = current_price / initial_price
    il = 1 - (2 * np.sqrt(price_ratio)) / (1 + price_ratio)

    # Fee income esperado (anualizado)
    daily_fee = fee_apr / 365
    expected_fee_daily = daily_fee * 0.5  # Asumiendo 50% del volumen diario

    # Comparar IL vs fees (periodo de 30 días)
    il_30d = il
    fee_30d = expected_fee_daily * 30

    if vol_forecast > 0.5 and il > fee_30d * 2:
        logger.warning(
            f"❌ IL > Fees: IL={il:.2%}, Fee(30d)={fee_30d:.2%}. "
            f"Dont provide liquidity."
        )
        return False

    return True
```

**Regla 38.3 — Concentrated Liquidity (V3)**

```python
def v3_tick_range_calculation(
    self,
    current_price: float,
    volatility_24h: float,
    std_dev_multiplier: float = 2.0
) -> dict:
    """
    Colocar rango en ±2 SD basadas en volatilidad 24h.

    Steffensen: Concentrated liquidity = más fees, más riesgo.
    """
    # Calcular ticks
    price_std = current_price * volatility_24h

    lower_price = current_price * np.exp(-std_dev_multiplier * price_std / current_price)
    upper_price = current_price * np.exp(std_dev_multiplier * price_std / current_price)

    logger.info(
        f"V3 Range: [{lower_price:.2f}, {upper_price:.2f}] "
        f"(±{std_dev_multiplier}σ, current={current_price:.2f})"
    )

    return {
        'tick_lower': self.price_to_tick(lower_price),
        'tick_upper': self.price_to_tick(upper_price),
        'lower_price': lower_price,
        'upper_price': upper_price
    }
```

**Regla 38.4 — Arbitrage Monitoring (CEX vs DEX)**

```python
def cex_dex_arbitrage(
    self,
    cex_price: float,
    dex_price: float,
    threshold: float = 0.005  # 0.5%
) -> dict:
    """
    Monitorear diferencia CEX/DEX. Si > 0.5% → arbitrar o pausar LP.

    Steffensen: Arbitrage mantiene paridad.
    """
    diff = abs(cex_price - dex_price) / cex_price

    if diff > threshold:
        logger.info(
            f"Arbitrage opportunity: CEX=${cex_price:.2f}, "
            f"DEX=${dex_price:.2f}, Diff={diff:.2%}"
        )

        direction = 'BUY_DEX_SELL_CEX' if dex_price < cex_price else 'BUY_CEX_SELL_DEX'

        return {
            'arbitrage': True,
            'diff_pct': diff,
            'direction': direction,
            'action': 'EXECUTE_ARBITRAGE'
        }

    return {'arbitrage': False}
```

**Regla 38.5 — Gas Optimization**

```python
def gas_cost_check(
    self,
    gas_price_gwei: float,
    gas_limit: int,
    expected_profit_usd: float,
    eth_price_usd: float
) -> bool:
    """
    Solo operar si gas < 2% del beneficio.

    Steffensen: Gas eat profits en Ethereum.
    """
    # Gas cost en USD
    gas_cost_eth = (gas_price_gwei * 1e-9) * gas_limit
    gas_cost_usd = gas_cost_eth * eth_price_usd

    # Gas como % del profit
    gas_ratio = gas_cost_usd / expected_profit_usd

    if gas_ratio > 0.02:  # > 2%
        logger.warning(
            f"Gas too expensive: ${gas_cost_usd:.2f} "
            f"({gas_ratio:.1%} of profit). Skip trade."
        )
        return False

    logger.info(
        f"Gas acceptable: ${gas_cost_usd:.2f} "
        f"({gas_ratio:.1%} of ${expected_profit_usd:.2f} profit)"
    )

    return True
```

**Regla 38.6 — JIT (Just-In-Time) Liquidity**

```python
def jit_liquidity_strategy(
    self,
    mempool_large_orders: List[dict],
    current_tick: int
) -> dict:
    """
    Detectar órdenes grandes en mempool y proveer liquidez ahí.

    Steffensen: JIT = capturar fee de whale.
    """
    if not mempool_large_orders:
        return {'opportunity': False}

    for order in mempool_large_orders:
        # Orden grande cerca de nuestro tick
        if abs(order['tick'] - current_tick) < 10:
            logger.info(
                f"JIT opportunity: Large order at tick {order['tick']}, "
                f"current={current_tick}"
            )

            return {
                'opportunity': True,
                'target_tick': order['tick'],
                'liquidity_amount': order['amount'] * 0.1,
                'action': 'PROVIDE_JIT_LIQUIDITY'
            }

    return {'opportunity': False}
```

**Regla 38.7 — Sandwich Attack Guard**

```python
def sandwich_protection(
    self,
    trade_amount: float,
    slippage_setting: float,
    max_slippage: float = 0.001  # 0.1%
) -> bool:
    """
    NO usar market orders en DEX. Slippage estricto < 0.1%.

    Steffensen: MEV bots atacan órdenes con slippage amplio.
    """
    if slippage_setting > max_slippage:
        logger.error(
            f"❌ SLIPPAGE TOO HIGH: {slippage_setting:.2%} "
            f"> {max_slippage:.2%}. Vulnerable to sandwich."
        )
        return False

    # Usar límite de slippage estricto
    logger.info(f"Safe trade: Slippage {slippage_setting:.2%}")

    return True
```

**Regla 38.8 — Pool Balancing**

```python
def pool_imbalance_check(
    self,
    reserve_x: float,
    reserve_y: float,
    initial_ratio: float = 1.0,
    max_deviation: float = 0.10  # 10%
) -> dict:
    """
    Si ratio se desvía > 10% → rebalanceo forzoso.

    Steffensen: Pools desbalanceadas pierden fees.
    """
    current_ratio = reserve_x / reserve_y
    deviation = abs(current_ratio - initial_ratio) / initial_ratio

    if deviation > max_deviation:
        logger.warning(
            f"Pool imbalanced: Ratio {current_ratio:.2f} "
            f"(deviation={deviation:.1%}). Rebalance needed."
        )

        return {
            'imbalanced': True,
            'deviation': deviation,
            'action': 'FORCE_REBALANCE'
        }

    return {'imbalanced': False}
```

**Regla 38.9 — Flashloan Awareness**

```python
def flashloan_detection(
    self,
    pool_volume_current: float,
    pool_volume_ma: float
) -> bool:
    """
    Volumen 100x en un bloque = flashloan attack.

    Steffensen: Desconectar contrato si detectado.
    """
    volume_ratio = pool_volume_current / pool_volume_ma

    if volume_ratio > 100:
        logger.critical(
            f"🚨 FLASHLOAN ATTACK: Volume {volume_ratio:.0f}x normal. "
            f"Disconnect contract."
        )

        return True

    return False
```

**Regla 38.10 — Oracle Latency**

```python
def oracle_manipulation_guard(
    self,
    chainlink_price: float,
    uniswap_twap_price: float,
    spot_price: float,
    max_deviation: float = 0.02  # 2%
) -> dict:
    """
    Usar Chainlink + TWAP para evitar manipulación de oráculo corto plazo.

    Steffensen: Multi-oracle = seguridad.
    """
    # Comparar oráculos
    chainlink_deviation = abs(chainlink_price - spot_price) / spot_price
    twap_deviation = abs(uniswap_twap_price - spot_price) / spot_price

    if chainlink_deviation > max_deviation and twap_deviation > max_deviation:
        logger.warning(
            f"Oracle manipulation: CL={chainlink_deviation:.2%}, "
            f"TWAP={twap_deviation:.2%}. Pause trading."
        )

        return {
            'manipulation_detected': True,
            'safe_price': chainlink_price,
            'action': 'PAUSE_TRADING'
        }

    # Precio seguro = promedio ponderado
    safe_price = (chainlink_price * 0.7 + uniswap_twap_price * 0.3)

    return {
        'manipulation_detected': False,
        'safe_price': safe_price
    }
```

**Regla 38.11 — Fee Compounding**

```python
def auto_compound_fees(
    self,
    accumulated_fees: float,
    gas_cost: float,
    min_compound_amount: float = 100  # USD
) -> bool:
    """
    Reinvertir fees automáticamente cuando gas lo haga rentable.

    Steffensen: Compound = crecimiento exponencial.
    """
    if accumulated_fees < min_compound_amount:
        return False

    # Profit despues de gas
    net_profit = accumulated_fees - gas_cost

    if net_profit > 0:
        logger.info(
            f"Compounding ${accumulated_fees:.2f} fees "
            f"(net=${net_profit:.2f})"
        )
        return True

    return False
```

**Regla 38.12 — LVR (Loss Versus Rebalancing)**

```python
def calculate_lvr(
    self,
    lp_returns: pd.Series,
    rebalance_returns: pd.Series
) -> float:
    """
    Medir rendimiento contra rebalanceo activo, no HODL.

    Steffensen: LVR = true cost of being LP.
    """
    # LP vs Active Rebalance
    lvr = (rebalance_returns - lp_returns).sum()

    logger.info(f"LVR: {lvr:.2%} (cost of passive LP)")

    return lvr
```

**Regla 38.13 — MEV Protection (Flashbots)**

```python
def use_flashbots(
    self,
    transaction: dict,
    min_profit_threshold: float
) -> str:
    """
    Usar Flashbots para enviar directo a mineros/validadores.

    Steffensen: Evitar mempool público = evitar MEV.
    """
    # Solo si profit significativo
    if transaction['expected_profit'] > min_profit_threshold:
        logger.info("Using Flashbots for MEV protection")

        # Enviar via Flashbots
        return 'FLASHBOTS'

    # Transacción normal
    return 'PUBLIC_MEMPOOL'
```

**Regla 38.14 — Multi-hop Routing**

```python
def optimal_routing(
    self,
    amount_in: float,
    token_a: str,
    token_b: str,
    stable_token: str
) -> dict:
    """
    Calcular si es mejor A→B o A→Stable→B.

    Steffensen: Multi-hop puede ser más barato.
    """
    # Route directo
    direct_quote = self.get_v2_quote(token_a, token_b, amount_in)

    # Route via stable
    stable_quote = self.get_v2_quote(token_a, stable_token, amount_in)
    final_quote = self.get_v2_quote(stable_token, token_b, stable_quote['output'])

    if final_quote['output'] > direct_quote['output']:
        logger.info(
            f"Multi-hop better: "
            f"Direct={direct_quote['output']:.4f}, "
            f"Multi={final_quote['output']:.4f}"
        )

        return {
            'route': f'{token_a}->{stable_token}->{token_b}',
            'output': final_quote['output']
        }

    return {'route': f'{token_a}->{token_b}', 'output': direct_quote['output']}
```

**Regla 38.15 — Liquidity Fragmentation**

```python
def liquidity_migration(
    self,
    uniswap_liquidity: float,
    curve_liquidity: float,
    threshold: float = 0.20  # 20%
) -> dict:
    """
    Si liquidez se mueve de Uniswap a Curve → migrar fondos.

    Steffensen: Seguir la liquidez.
    """
    total = uniswap_liquidity + curve_liquidity
    curve_pct = curve_liquidity / total

    if curve_pct > threshold and uniswap_liquidity < curve_liquidity:
        logger.info(
            f"Liquidity migrated to Curve: {curve_pct:.1%}. "
            f"Move funds next block."
        )

        return {
            'migration_needed': True,
            'target': 'CURVE',
            'action': 'WITHDRAW_UNISWAP_DEPOSIT_CURVE'
        }

    return {'migration_needed': False}
```
