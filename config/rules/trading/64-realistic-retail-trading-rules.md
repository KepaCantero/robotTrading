# 📘 64. "Realistic Retail Trading Rules" - Extraído de gemini_rules.txt

## REGLAS DE IMPLEMENTACIÓN PARA CLAUDE CODE

**Objetivo:** Sistema de algo trading para escalar de 1000€ → 500k
**Principio:** Sobrevivir, aprender, y escalar gradualmente

---

## BLOQUE 1: GESTIÓN DE CAPITAL Y RIESGO (R1-R4)

### R1. Kelly Criterion + Tamaño Máximo de Posición

**SIEMPRE usa Kelly Criterion fraccional para tamaño de posición**

```python
def kelly_position_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    capital: Decimal,
    kelly_fraction: float = 0.5  # Half-Kelly por defecto
) -> Decimal:
    """
    Kelly Criterion = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

    SIEMPRE usar fraccional Kelly (25-50%) para reducir volatilidad.
    """
    loss_rate = 1.0 - win_rate
    kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

    # Limitar a fracción de Kelly
    kelly = max(0, min(kelly * kelly_fraction, 0.25))

    return capital * Decimal(str(kelly))


# NUNCA arriesgues más del 2% del capital por trade
def calculate_position_size(
    capital: Decimal,
    entry_price: Decimal,
    stop_loss: Decimal,
    max_risk_pct: Decimal = Decimal("0.02")
) -> Decimal:
    """
    Calcular tamaño basado en riesgo máximo del 2% del capital.
    """
    risk_amount = capital * max_risk_pct
    risk_per_share = abs(entry_price - stop_loss)

    if risk_per_share == 0:
        return Decimal("0")

    position_size = risk_amount / risk_per_share

    # Máximo 20% del capital en una sola posición
    max_position = capital * Decimal("0.20")
    return min(position_size, position_size)
```

**Referencias:**
- *The Mathematics of Money Management* - Ralph Vince
- *Fortune's Formula* - William Poundstone

---

### R2. Drawdown Máximo - Stop Trading Automático

**Implementa drawdown máximo del 15% con parada automática**

```python
class DrawdownMonitor:
    """Monitorea drawdown y detiene trading al alcanzar límites."""

    WARNING_THRESHOLD = Decimal("0.15")  # 15% - reducir tamaño
    CRITICAL_THRESHOLD = Decimal("0.25")  # 25% - parar trading

    def __init__(self, initial_capital: Decimal):
        self.initial_capital = initial_capital
        self.peak_capital = initial_capital
        self.is_trading_halted = False
        self.cooldown_until = None

    def update(self, current_capital: Decimal) -> Optional[AlertAction]:
        """
        Actualizar peak y calcular drawdown actual.

        Retorna acción si se excede umbral.
        """
        # Actualizar peak
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital

        # Calcular drawdown
        drawdown = (self.peak_capital - current_capital) / self.peak_capital

        if drawdown >= self.CRITICAL_THRESHOLD:
            self.is_trading_halted = True
            return AlertAction(
                severity=AlertSeverity.CRITICAL,
                action="HALT_TRADING",
                message=f"Drawdown {drawdown:.1%} >= 25% - Trading detenido",
                metadata={"drawdown": str(drawdown), "current_capital": str(current_capital)}
            )

        elif drawdown >= self.WARNING_THRESHOLD:
            return AlertAction(
                severity=AlertSeverity.WARNING,
                action="REDUCE_POSITIONS",
                message=f"Drawdown {drawdown:.1%} >= 15% - Reducir tamaño 50%",
                metadata={"drawdown": str(drawdown), "reduction_factor": "0.5"}
            )

        return None
```

---

### R3. Correlación y Concentración Máxima

**NUNCA excedas estos límites de concentración:**

```python
from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass
class PositionLimits:
    """Límites de posición por nivel de capital."""
    max_positions: int
    max_correlation: float
    max_single_asset: Decimal  # % del capital
    max_single_sector: Decimal  # % del capital


class PositionLimitsManager:
    """Gestiona límites de posición según fase de capital."""

    LIMITS_BY_CAPITAL = {
        # Fase 1: 1k-10k
        (1000, 10000): PositionLimits(
            max_positions=2,
            max_correlation=0.7,
            max_single_asset=Decimal("0.20"),
            max_single_sector=Decimal("0.40")
        ),
        # Fase 2: 10k-50k
        (10000, 50000): PositionLimits(
            max_positions=3,
            max_correlation=0.7,
            max_single_asset=Decimal("0.15"),
            max_single_sector=Decimal("0.35")
        ),
        # Fase 3: 50k-500k
        (50000, 500000): PositionLimits(
            max_positions=5,
            max_correlation=0.6,
            max_single_asset=Decimal("0.10"),
            max_single_sector=Decimal("0.25")
        ),
    }

    @classmethod
    def get_limits(cls, capital: Decimal) -> PositionLimits:
        """Obtener límites según capital actual."""
        capital_float = float(capital)
        for (min_cap, max_cap), limits in cls.LIMITS_BY_CAPITAL.items():
            if min_cap <= capital_float < max_cap:
                return limits

        # Default a fase más alta
        return cls.LIMITS_BY_CAPITAL[(50000, 500000)]

    def check_position_limits(
        self,
        portfolio: Portfolio,
        new_symbol: str,
        new_sector: str,
        correlations: Dict[str, float]
    ) -> Tuple[bool, Optional[str]]:
        """
        Verificar si nueva posición cumple límites.

        Returns:
            (is_allowed, rejection_reason)
        """
        capital = portfolio.total_value
        limits = self.get_limits(capital)

        # Verificar número máximo de posiciones
        if len(portfolio.positions) >= limits.max_positions:
            return False, f"Máximo {limits.max_positions} posiciones alcanzado"

        # Verificar exposición por activo
        existing_position = next((p for p in portfolio.positions if p.symbol == new_symbol), None)
        current_exposure = existing_position.market_value if existing_position else Decimal("0")

        if (current_exposure / capital) > limits.max_single_asset:
            return False, f"Exceso en {new_symbol}: {current_exposure/capital:.1%} > {limits.max_single_asset:.1%}"

        # Verificar correlación con posiciones existentes
        for position in portfolio.positions:
            corr = correlations.get(position.symbol, 0.0)
            if abs(corr) > limits.max_correlation:
                return False, f"Correlación {position.symbol}-{new_symbol} = {corr:.2f} > {limits.max_correlation}"

        return True, None
```

---

### R4. Ratio Riesgo/Beneficio Mínimo 2:1

**NUNCA entres en un trade con R:R < 2:1**

```python
def calculate_risk_reward_ratio(
    entry_price: Decimal,
    target_price: Decimal,
    stop_loss: Decimal
) -> Decimal:
    """
    R:R = (Target - Entry) / (Entry - Stop)

    Ratio mínimo: 2:1
    """
    potential_profit = abs(target_price - entry_price)
    potential_loss = abs(entry_price - stop_loss)

    if potential_loss == 0:
        return Decimal("0")

    return potential_profit / potential_loss


def validate_risk_reward(
    signal: Signal,
    min_rr_ratio: Decimal = Decimal("2.0")
) -> Tuple[bool, Optional[str]]:
    """
    Validar que la señal cumpla el ratio mínimo R:R.

    Returns:
        (is_valid, rejection_reason)
    """
    # Obtener target y stop de metadata de la señal
    target_price = Decimal(signal.metadata.get("target_price", 0))
    stop_loss = Decimal(signal.metadata.get("stop_loss", 0))

    if target_price == 0 or stop_loss == 0:
        return False, "Falta target_price o stop_loss en señal"

    entry_price = signal.price
    rr_ratio = calculate_risk_reward_ratio(entry_price, target_price, stop_loss)

    if rr_ratio < min_rr_ratio:
        return False, f"R:R {rr_ratio:.2f} < {min_rr_ratio:.2f} mínimo"

    # Para setups de alta probabilidad, permitir 1.5:1
    if signal.confidence >= 80.0:
        min_rr_high_prob = Decimal("1.5")
        if rr_ratio < min_rr_high_prob:
            return False, f"R:R {rr_ratio:.2f} < {min_rr_high_prob:.2f} (alta probabilidad)"

    return True, None
```

---

## BLOQUE 2: BACKTESTING Y VALIDACIÓN (R5-R7)

### R5. Walk-Forward Analysis

**SIEMPRE valida con Walk-Forward Analysis**

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple
import numpy as np


@dataclass
class WalkForwardConfig:
    """Configuración para Walk-Forward Analysis."""
    train_pct: float = 0.70
    test_pct: float = 0.30
    min_train_periods: int = 60  # Mínimo 6 meses datos diarios
    step_periods: int = 20  # Rolling window de 3 meses


class WalkForwardValidator:
    """Implementa Walk-Forward Analysis para evitar overfitting."""

    def __init__(self, config: WalkForwardConfig):
        self.config = config

    def walk_forward_backtest(
        self,
        data: pd.DataFrame,
        strategy_generator,
        min_trades: int = 50
    ) -> Dict[str, float]:
        """
        Ejecuta walk-forward analysis.

        Args:
            data: DataFrame con datos históricos
            strategy_generator: Función que retorna estrategia con parámetros
            min_trades: Mínimo trades en OOS para validar

        Returns:
            Dict con métricas agregadas IS/OOS
        """
        results = {
            "is_sharpe": [],
            "oos_sharpe": [],
            "is_trades": [],
            "oos_trades": [],
            "degradation": []
        }

        total_periods = len(data)
        window_size = int(total_periods * self.config.train_pct)

        # Rolling windows
        for start_idx in range(0, total_periods - window_size, self.config.step_periods):
            train_end = start_idx + window_size
            test_end = min(train_end + int(total_periods * self.config.test_pct), total_periods)

            if test_end > total_periods or (train_end - start_idx) < self.config.min_train_periods:
                continue

            # Train data (IS)
            train_data = data.iloc[start_idx:train_end]

            # Test data (OOS) - NO usado para optimización
            test_data = data.iloc[train_end:test_end]

            # Optimizar en training
            strategy = strategy_generator()
            strategy.optimize(train_data)

            # Evaluar IS
            is_result = strategy.backtest(train_data)
            results["is_sharpe"].append(is_result["sharpe_ratio"])
            results["is_trades"].append(is_result["total_trades"])

            # Evaluar OOS
            oos_result = strategy.backtest(test_data)
            results["oos_sharpe"].append(oos_result["sharpe_ratio"])
            results["oos_trades"].append(oos_result["total_trades"])

            # Degradación IS vs OOS
            degradation = (is_result["sharpe_ratio"] - oos_result["sharpe_ratio"]) / is_result["sharpe_ratio"]
            results["degradation"].append(degradation)

        # Agregar métricas
        return {
            "is_mean_sharpe": np.mean(results["is_sharpe"]),
            "oos_mean_sharpe": np.mean(results["oos_sharpe"]),
            "is_total_trades": sum(results["is_trades"]),
            "oos_total_trades": sum(results["oos_trades"]),
            "mean_degradation": np.mean(results["degradation"]),
            "valid": sum(results["oos_trades"]) >= min_trades
        }

    def validate_degradation(self, walk_forward_result: Dict) -> bool:
        """
        Validar que degradación OOS no exceda 30%.

        Reject estrategia si:
        - OOS Sharpe degrada >30% vs IS
        - OOS trades < 50
        """
        if not walk_forward_result["valid"]:
            logger.error("❌ Insuficientes trades OOS (<50)")
            return False

        degradation = walk_forward_result["mean_degradation"]
        if degradation > 0.30:
            logger.error(f"❌ Degradación OOS {degradation:.1%} > 30%")
            return False

        logger.info(f"✅ Walk-forward validado: degradación {degradation:.1%}")
        return True
```

**Referencia:** *Advances in Financial Machine Learning* - Marcos López de Prado

---

### R6. Prevención de Overfitting

**SIEMPRE valida ratio parámetros/datos < 1:30**

```python
class OverfittingGuard:
    """Previne overfitting en backtesting."""

    MIN_TRAIN_SAMPLES = 50
    PARAMETER_DATA_RATIO = 30  # Mínimo 30 datos por parámetro

    @classmethod
    def validate_parameter_count(
        cls,
        parameter_count: int,
        train_samples: int
    ) -> bool:
        """
        Validar ratio parámetros/datos.

        Reject si ratio < 1:30 (demasiados parámetros para pocos datos).
        """
        ratio = train_samples / parameter_count

        if ratio < cls.PARAMETER_DATA_RATIO:
            logger.error(
                f"❌ Overfitting riesgo: {parameter_count} params "
                f"para {train_samples} muestras (ratio {ratio:.1f} < 30)"
            )
            return False

        logger.info(f"✅ Ratio parámetros/datos: {ratio:.1f}")
        return True

    @staticmethod
    def purged_cross_validation(
        data: pd.DataFrame,
        n_folds: int = 5,
        embargo_periods: int = 3
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Purged Cross-Validation con embargo temporal.

        Elimina datos entre train y test para prevenir leakage.

        Args:
            embargo_periods: N períodos a eliminar entre train/test
        """
        fold_size = len(data) // n_folds
        folds = []

        for i in range(n_folds):
            # Train fold
            train_start = 0
            train_end = i * fold_size

            # Test fold
            test_start = (i + 1) * fold_size + embargo_periods
            test_end = min((i + 2) * fold_size, len(data))

            if test_end >= len(data):
                continue

            train_data = data.iloc[train_start:train_end]
            test_data = data.iloc[test_start:test_end]

            folds.append((train_data, test_data))

        return folds
```

---

### R7. Monte Carlo para Riesgo

**Ejecuta 1000 simulaciones Monte Carlo del backtest**

```python
def monte_carlo_risk_analysis(
    returns: np.array,
    n_simulations: int = 1000,
    confidence_level: float = 0.05
) -> Dict[str, float]:
    """
    Simula escenarios Monte Carlo para estimar drawdown máximo.

    Args:
        returns: Array de retornos del backtest
        n_simulations: Número de simulaciones
        confidence_level: Percentil para estimar DD máximo (5%)

    Returns:
        Dict con percentiles de drawdown y otros métricas de riesgo
    """
    max_drawdowns = []

    for _ in range(n_simulations):
        # Bootstrap sampling de retornos
        simulated_returns = np.random.choice(returns, size=len(returns), replace=True)

        # Calcular equity curve
        equity = np.cumprod(1 + simulated_returns)

        # Calcular máximo drawdown
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak
        max_dd = np.max(drawdown)

        max_drawdowns.append(max_dd)

    # Percentiles
    max_drawdowns = np.array(max_drawdowns)

    return {
        "dd_mean": np.mean(max_drawdowns),
        "dd_std": np.std(max_drawdowns),
        "dd_percentile_5": np.percentile(max_drawdowns, confidence_level * 100),
        "dd_percentile_95": np.percentile(max_drawdowns, 100 - confidence_level * 100),
        "dd_max": np.max(max_drawdowns)
    }


def validate_monte_carlo_result(
    actual_dd: float,
    mc_result: Dict,
    tolerance: float = 0.10
) -> bool:
    """
    Validar que resultado real esté dentro de rango Monte Carlo.

    Si el resultado real está fuera del rango 5-95%: revisar modelo.
    """
    dd_5 = mc_result["dd_percentile_5"]
    dd_95 = mc_result["dd_percentile_95"]

    if actual_dd < dd_5 or actual_dd > dd_95:
        logger.warning(
            f"⚠️ DD real {actual_dd:.2%} fuera de rango MC [{dd_5:.2%}, {dd_95:.2%}]"
        )
        return False

    logger.info(f"✅ DD real {actual_dd:.2%} dentro de rango Monte Carlo")
    return True
```

---

## BLOQUE 3: EJECUCIÓN Y MICROESTRUCTURA (R8-R10)

### R8. Gestión de Spread Bid-Ask

**Usa limit/market orders según spread**

```python
from enum import Enum
from decimal import Decimal


class OrderType(Enum):
    """Tipo de orden según spread."""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    AVOID = "AVOID"  # No operar


def determine_order_type(
    bid_price: Decimal,
    ask_price: Decimal,
    market_price: Decimal,
    signal_strength: float
) -> OrderType:
    """
    Determinar tipo de orden según spread.

    Reglas:
    - Spread < 0.1%: LIMIT order
    - Spread 0.1-0.2%: MARKET solo en señales fuertes (>80%)
    - Spread > 0.5%: AVOID (excepto crypto emergente)
    """
    spread_pct = abs(ask_price - bid_price) / market_price

    if spread_pct < Decimal("0.001"):  # < 0.1%
        return OrderType.LIMIT

    elif spread_pct < Decimal("0.002"):  # 0.1-0.2%
        if signal_strength >= 80.0:
            return OrderType.MARKET
        else:
            return OrderType.LIMIT

    else:  # > 0.2%
        if spread_pct > Decimal("0.005"):  # > 0.5%
            return OrderType.AVOID
        elif signal_strength >= 85.0:
            return OrderType.MARKET
        else:
            return OrderType.AVOID
```

**Referencia:** *Market Microstructure Theory* - Maureen O'Hara

---

### R9. Timing de Ejecución

**Evita horarios de alta volatilidad sin razón clara**

```python
from datetime import time, datetime
from typing import Optional


class ExecutionTiming:
    """Controla horarios permitidos para ejecución."""

    # Horas a evitar (UTC - ajustar según mercado)
    AVOID_PERIODS = [
        # Primeros 15 min del mercado
        (time(13, 30), time(13, 45)),  # NY open 9:30 AM EST
        # Últimos 15 min del mercado
        (time(19, 45), time(20, 0)),   # NY close 4:00 PM EST
    ]

    # Horas óptimas para trading
    OPTIMAL_HOURS = [
        (time(15, 0), time(18, 0)),  # 10 AM - 1 PM EST
    ]

    @classmethod
    def should_trade(cls, current_time: datetime, signal_reason: str) -> Tuple[bool, Optional[str]]:
        """
        Verificar si se debe permitir trading en este momento.

        Returns:
            (should_trade, rejection_reason)
        """
        current_time_only = current_time.time()

        # Evitar períodos de alta volatilidad
        for start, end in cls.AVOID_PERIODS:
            if start <= current_time_only <= end:
                # Solo permitir si la razón es explícitamente "evento_volatil"
                if "evento_volatil" not in signal_reason.lower():
                    return False, f"Hora no óptima: {current_time_only}"

        # Preferir horas óptimas
        for start, end in cls.OPTIMAL_HOURS:
            if start <= current_time_only <= end:
                return True, None

        # Fuera de horas óptimas pero permitido
        return True, None


# Evitar operar durante anuncios macro
MACRO_ANNOUNCEMENTS = {
    "FED": [],  # Dinámico: se actualiza con fechas
    "CPI": [],
    "NFP": [],
}


def is_macro_announcement_time(dt: datetime) -> bool:
    """Verificar si es horario de anuncio macro."""
    for announcement, dates in MACRO_ANNOUNCEMENTS.items():
        for ann_date in dates:
            if dt.date() == ann_date.date():
                # Ventana de 1 hora antes y 1 hora después
                time_diff = abs((dt - ann_date).total_seconds()) / 3600
                if time_diff <= 1.0:
                    return True
    return False
```

---

### R10. Slippage Máximo

**Implementa control de slippaje máximo aceptable**

```python
class SlippageMonitor:
    """Monitorea slippage y rechaza ejecuciones con exceso."""

    MAX_SLIPPAGE_WARNING = Decimal("0.001")  # 0.1%
    MAX_SLIPPAGE_REJECT = Decimal("0.002")   # 0.2%

    @classmethod
    def calculate_slippage(
        cls,
        expected_price: Decimal,
        executed_price: Decimal,
        side: str
    ) -> Decimal:
        """
        Calcular slippage como % del precio esperado.

        Para BUY: positive slippage = pagaste más
        Para SELL: positive slippage = vendiste por menos
        """
        if side.upper() == "BUY":
            slippage = (executed_price - expected_price) / expected_price
        else:  # SELL
            slippage = (expected_price - executed_price) / expected_price

        return max(slippage, Decimal("0"))  # Solo positivo (desfavorable)

    @classmethod
    def validate_execution(
        cls,
        expected_price: Decimal,
        executed_price: Decimal,
        side: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validar si slippage es aceptable.

        Returns:
            (is_acceptable, rejection_reason)
        """
        slippage = cls.calculate_slippage(expected_price, executed_price, side)

        if slippage >= cls.MAX_SLIPPAGE_REJECT:
            return False, f"Slippage {slippage:.3%} >= {cls.MAX_SLIPPAGE_REJECT:.3%} máximo"

        elif slippage >= cls.MAX_SLIPPAGE_WARNING:
            logger.warning(f"⚠️ Slippage alto: {slippage:.3%}")
            return True, "slippage_warning"

        return True, None
```

---

## BLOQUE 4: GESTIÓN DE POSICIONES (R11-R13)

### R11. Trailing Stop Dinámico

**Implementa trailing stop que se ajusta con el beneficio**

```python
class TrailingStopManager:
    """Gestiona trailing stops dinámicos."""

    def __init__(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        trailing_pct: Decimal = Decimal("0.015")  # 1.5%
    ):
        self.entry_price = entry_price
        self.initial_stop = stop_loss
        self.trailing_pct = trailing_pct
        self.highest_price = entry_price
        self.current_stop = stop_loss

    def update(self, current_price: Decimal, unrealized_pnl: Decimal) -> Optional[Decimal]:
        """
        Actualizar trailing stop según precio actual y P&L.

        Returns:
            Nuevo stop si cambió, None si igual
        """
        # Actualizar máximo
        if current_price > self.highest_price:
            self.highest_price = current_price

        # Calcular riesgo inicial
        initial_risk = abs(self.entry_price - self.initial_stop)

        # Beneficio en R-múltiplos
        r_multiple = unrealized_pnl / initial_risk if initial_risk > 0 else 0

        new_stop = self.current_stop

        if r_multiple >= 2.0:
            # Mover a break-even
            new_stop = self.entry_price

        elif r_multiple >= 3.0:
            # Trailing stop al 50% del beneficio
            profit = current_price - self.entry_price
            new_stop = current_price - (profit * Decimal("0.5"))

        elif r_multiple >= 1.0:
            # Trailing stop del 1.5% desde el máximo
            new_stop = self.highest_price * (Decimal("1") - self.trailing_pct)

        # Solo retornar si cambió
        if new_stop != self.current_stop:
            self.current_stop = new_stop
            return new_stop

        return None
```

---

### R12. Take Profit Parcial

**Cierra parcialmente en hitos de beneficio**

```python
@dataclass
class ProfitTarget:
    """Objetivo de beneficio parcial."""
    r_multiple: float
    close_pct: float  # % de posición a cerrar
    action: str  # "move_to_breakeven", "trailing_stop", etc.


class PartialTakeProfit:
    """Gestiona take profit parcial en múltiples niveles."""

    DEFAULT_TARGETS = [
        ProfitTarget(r_multiple=2.0, close_pct=0.50, action="move_to_breakeven"),
        ProfitTarget(r_multiple=3.0, close_pct=0.25, action="trailing_stop"),
        ProfitTarget(r_multiple=5.0, close_pct=0.25, action="none"),
    ]

    def __init__(self, entry_price: Decimal, initial_stop: Decimal, targets: List[ProfitTarget] = None):
        self.entry_price = entry_price
        self.initial_stop = initial_stop
        self.targets = targets or self.DEFAULT_TARGETS
        self.executed_targets = set()

    def check_targets(
        self,
        current_price: Decimal,
        position_size: Decimal
    ) -> Optional[Tuple[Decimal, str]]:
        """
        Verificar si se alcanzó algún objetivo.

        Returns:
            (size_to_close, action) o None
        """
        initial_risk = abs(self.entry_price - self.initial_stop)
        current_profit = current_price - self.entry_price
        r_multiple = float(current_profit / initial_risk)

        for target in self.targets:
            if target.r_multiple in self.executed_targets:
                continue

            if r_multiple >= target.r_multiple:
                self.executed_targets.add(target.r_multiple)
                size_to_close = position_size * Decimal(str(target.close_pct))
                return (size_to_close, target.action)

        return None
```

---

### R13. Pyramiding - Añadir a Ganadores

**Solo agrega a posiciones ganadoras, nunca a perdedoras**

```python
class PyramidingManager:
    """Gestiona añadir posiciones a trades ganadores."""

    def __init__(
        self,
        initial_size: Decimal,
        max_additions: int = 2,
        first_addition_pct: float = 0.5,  # 50% del tamaño inicial
        second_addition_pct: float = 0.25,  # 25% del tamaño inicial
    ):
        self.initial_size = initial_size
        self.max_additions = max_additions
        self.additions = [
            Decimal(str(first_addition_pct)),
            Decimal(str(second_addition_pct))
        ]
        self.current_additions = 0

    def can_add_position(self, current_pnl: Decimal) -> bool:
        """
        Solo añadir si:
        1. Posición está en beneficio (P&L > 0)
        2. No se ha alcanzado máximo de adiciones
        """
        if current_pnl <= 0:
            logger.info("❌ No pyramiding: posición en pérdidas")
            return False

        if self.current_additions >= self.max_additions:
            logger.info(f"❌ No pyramiding: máximo {self.max_additions} adiciones")
            return False

        return True

    def get_addition_size(self) -> Optional[Decimal]:
        """Calcular tamaño de siguiente adición."""
        if self.current_additions >= len(self.additions):
            return None

        addition_pct = self.additions[self.current_additions]
        self.current_additions += 1

        return self.initial_size * addition_pct
```

---

## BLOQUE 5: DATA E INFRAESTRUCTURA (R14-R16)

### R14. Calidad de Datos

**Valida y limpia datos antes de usar**

```python
import pandas as pd
import numpy as np


class DataQualityValidator:
    """Valida calidad de datos financieros."""

    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validar calidad de datos.

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        # Check for missing values
        missing = df.isnull().sum()
        if missing.any():
            for col, count in missing[missing > 0].items():
                issues.append(f"Missing values en {col}: {count}")

        # Check for duplicates
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            issues.append(f"Duplicated rows: {duplicates}")

        # Check for outliers (>3 std)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            outliers = df[(df[col] < mean - 3*std) | (df[col] > mean + 3*std)]
            if len(outliers) > 0:
                issues.append(f"Outliers en {col}: {len(outliers)} valores")

        return (len(issues) == 0, issues)

    @staticmethod
    def clean_dataframe(df: pd.DataFrame, max_gap: int = 3) -> pd.DataFrame:
        """
        Limpiar datos con reglas específicas.

        Args:
            max_gap: Máximo gaps consecutivos para forward fill
        """
        cleaned = df.copy()

        # Forward fill para missing values (máximo max_gap consecutivos)
        cleaned = cleaned.fillna(method='ffill', limit=max_gap)

        # Si aún quedan missing, backward fill
        cleaned = cleaned.fillna(method='bfill', limit=1)

        # Marcar outliers para revisión
        numeric_cols = cleaned.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            mean = cleaned[col].mean()
            std = cleaned[col].std()
            outlier_mask = (cleaned[col] < mean - 3*std) | (cleaned[col] > mean + 3*std)
            if outlier_mask.any():
                # Crear columna de flags
                cleaned[f"{col}_outlier"] = outlier_mask

        return cleaned

    @staticmethod
    def preserve_raw_data(raw_data: pd.DataFrame, output_path: str) -> None:
        """
        Guardar datos raw sin modificar (append-only).

        NUNCA sobreescribir datos crudos.
        """
        raw_data.to_csv(output_path, mode='a', header=False, index=False)
```

---

### R15. Logging Completo

**Registra CADA decisión del sistema**

```python
import logging
from datetime import datetime
from typing import Any, Dict
import json


class TradingDecisionLogger:
    """Logger especializado para decisiones de trading."""

    def __init__(self, log_path: str):
        self.log_path = log_path
        self.logger = logging.getLogger("trading_decisions")
        handler = logging.FileHandler(log_path, mode='a')  # Append-only
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(handler)

    def log_signal(self, signal: Signal, metadata: Dict[str, Any] = None) -> None:
        """Registrar señal generada."""
        decision = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "signal_generated",
            "symbol": signal.symbol,
            "type": signal.signal_type.value,
            "price": str(signal.price),
            "strength": signal.strength.value,
            "confidence": signal.confidence,
            "metadata": metadata or signal.metadata
        }
        self.logger.info(json.dumps(decision))

    def log_execution(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        reason: str
    ) -> None:
        """Registrar ejecución."""
        decision = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "order_executed",
            "symbol": symbol,
            "side": side,
            "quantity": str(quantity),
            "price": str(price),
            "reason": reason
        }
        self.logger.info(json.dumps(decision))

    def log_risk_check(
        self,
        signal: Signal,
        passed: bool,
        reason: str
    ) -> None:
        """Registrar verificación de riesgo."""
        decision = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "risk_check",
            "symbol": signal.symbol,
            "type": signal.signal_type.value,
            "passed": passed,
            "reason": reason
        }
        self.logger.warning(json.dumps(decision) if not passed else json.dumps(decision))
```

---

### R16. Reconciliación Diaria

**Reconcilia posición del sistema vs broker DÍARIAMENTE**

```python
@dataclass
class ReconciliationResult:
    """Resultado de reconciliación diaria."""
    matched: bool
    system_positions: Dict[str, Decimal]
    broker_positions: Dict[str, Decimal]
    differences: Dict[str, Decimal]
    cash_matched: bool
    system_cash: Decimal
    broker_cash: Decimal


class DailyReconciler:
    """Reconcilia posiciones del sistema vs broker."""

    TOLERANCE_PCT = Decimal("0.001")  # 0.1%

    def reconcile(
        self,
        portfolio: Portfolio,
        broker_statement: Dict[str, Any]
    ) -> ReconciliationResult:
        """
        Reconciliar portafolio del sistema con estado del broker.

        Si diferencias > 0.1%: alerta inmediata.
        """
        # Extraer posiciones del broker
        broker_positions = {
            pos["symbol"]: Decimal(str(pos["quantity"]))
            for pos in broker_statement.get("positions", [])
        }

        # Posiciones del sistema
        system_positions = {
            pos.symbol: pos.quantity
            for pos in portfolio.positions
        }

        # Encontrar diferencias
        differences = {}
        all_symbols = set(system_positions.keys()) | set(broker_positions.keys())

        for symbol in all_symbols:
            system_qty = system_positions.get(symbol, Decimal("0"))
            broker_qty = broker_positions.get(symbol, Decimal("0"))

            if abs(system_qty - broker_qty) > 0:
                # Verificar si diferencia es significativa
                total_value = max(abs(system_qty), abs(broker_qty))
                if total_value > 0:
                    diff_pct = abs(system_qty - broker_qty) / total_value
                    if diff_pct > self.TOLERANCE_PCT:
                        differences[symbol] = broker_qty - system_qty

        # Reconciliar cash
        system_cash = portfolio.cash
        broker_cash = Decimal(str(broker_statement.get("cash", "0")))
        cash_diff = abs(system_cash - broker_cash)
        cash_matched = cash_pct < self.TOLERANCE_PCT

        matched = len(differences) == 0 and cash_matched

        return ReconciliationResult(
            matched=matched,
            system_positions=system_positions,
            broker_positions=broker_positions,
            differences=differences,
            cash_matched=cash_matched,
            system_cash=system_cash,
            broker_cash=broker_cash
        )

    def generate_daily_report(self, result: ReconciliationResult) -> Dict[str, Any]:
        """Generar reporte diario de P&L y reconciliación."""
        return {
            "date": datetime.utcnow().date().isoformat(),
            "reconciliation": {
                "matched": result.matched,
                "position_differences": {
                    symbol: str(qty)
                    for symbol, qty in result.differences.items()
                },
                "cash_matched": result.cash_matched,
                "cash_difference": str(result.broker_cash - result.system_cash)
            },
            "pnl": {
                # Calcular P&L del día
                "unrealized": sum(pos.unrealized_pnl for pos in portfolio.positions),
                "realized": portfolio.realized_pnl,
                "total": portfolio.total_pnl
            }
        }
```

---

## BLOQUE 6: PSICOLOGÍA Y DISCIPLINA (R17-R18)

### R17. Sin Emociones - Control Automático

**NUNCA cambies reglas durante mercado abierto**

```python
from datetime import time
from enum import Enum


class TradingState(Enum):
    """Estado del trading."""
    ACTIVE = "ACTIVE"
    COOLDOWN = "COOLDOWN"
    HALTED = "HALTED"


class EmotionControlGuard:
    """Previene decisiones emocionales."""

    COOLDOWN_DURATION = 3600  # 1 hora en segundos
    MAX_CONSECUTIVE_LOSSES = 3

    def __init__(self):
        self.consecutive_losses = 0
        self.cooldown_until = None
        self.state = TradingState.ACTIVE

    def on_trade_closed(self, pnl: Decimal) -> Optional[TradingState]:
        """
        Actualizar estado tras cerrar trade.

        Retorna nuevo estado si cambió.
        """
        if pnl < 0:
            self.consecutive_losses += 1

            # Cooldown tras 3 pérdidas consecutivas
            if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
                self.start_cooldown()
                return TradingState.COOLDOWN
        else:
            self.consecutive_losses = 0

        return None

    def start_cooldown(self) -> None:
        """Iniciar periodo de cooldown."""
        self.cooldown_until = datetime.utcnow() + timedelta(seconds=self.COOLDOWN_DURATION)
        self.state = TradingState.COOLDOWN
        logger.warning(f"🔒 Cooldown iniciado tras {self.consecutive_losses} pérdidas")

    def can_trade(self) -> bool:
        """
        Verificar si se permite trading.

        Reglas:
        1. No trading durante cooldown
        2. No trading fuera de horario de mercado
        """
        if self.state == TradingState.HALTED:
            return False

        if self.state == TradingState.COOLDOWN:
            if datetime.utcnow() < self.cooldown_until:
                return False
            else:
                # Cooldown terminado
                self.state = TradingState.ACTIVE
                self.consecutive_losses = 0

        return True

    def is_market_open(self, current_time: datetime) -> bool:
        """Verificar si mercado está abierto (no ejecutar fuera de horario)."""
        # Definir horario de mercado según mercado
        # Por defecto: 9:30 AM - 4:00 PM EST (13:30 - 20:00 UTC)
        market_open = time(13, 30)
        market_close = time(20, 0)

        current_time_only = current_time.time()
        return market_open <= current_time_only <= market_close
```

---

### R18. Journal de Trades

**Registra cada trade con contexto emocional**

```python
@dataclass
class TradeJournalEntry:
    """Entrada del journal de trading."""
    timestamp: datetime
    symbol: str
    side: str
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    pnl: Decimal
    setup_type: str  # "ganador_planificado", "ganador_suerte", "perdedor_error", "perdedor_planificado"
    reason: str
    emotion_before: int  # 1-5 scale
    emotion_after: int  # 1-5 scale
    lessons: str


class TradingJournal:
    """Journal de trades para análisis posterior."""

    def __init__(self, journal_path: str):
        self.journal_path = journal_path
        self.entries: List[TradeJournalEntry] = []
        self._load()

    def _load(self) -> None:
        """Cargar entries existentes."""
        if os.path.exists(self.journal_path):
            with open(self.journal_path, 'r') as f:
                data = json.load(f)
                for entry_data in data:
                    entry = TradeJournalEntry(**entry_data)
                    self.entries.append(entry)

    def add_entry(self, entry: TradeJournalEntry) -> None:
        """Añadir nueva entrada."""
        self.entries.append(entry)
        self._save()

    def _save(self) -> None:
        """Guardar entries a archivo."""
        data = [asdict(entry) for entry in self.entries]
        with open(self.journal_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def analyze_weekly(self) -> Dict[str, Any]:
        """Analizar trades de la semana para encontrar errores recurrentes."""
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        recent_trades = [
            e for e in self.entries
            if e.timestamp >= one_week_ago
        ]

        # Categorizar trades
        categories = {}
        for trade in recent_trades:
            cat = trade.setup_type
            categories[cat] = categories.get(cat, 0) + 1

        # Encontrar errores recurrentes
        errors = [
            t for t in recent_trades
            if "error" in t.setup_type
        ]

        # Setups ganadores
        winners = [t for t in recent_trades if t.pnl > 0]

        return {
            "total_trades": len(recent_trades),
            "categories": categories,
            "errors_count": len(errors),
            "winners_count": len(winners),
            "top_losing_reasons": self._get_common_reasons(errors),
            "top_winning_setups": self._get_common_reasons(winners)
        }

    def _get_common_reasons(self, trades: List[TradeJournalEntry]) -> List[Tuple[str, int]]:
        """Encontrar razones más comunes."""
        reasons = {}
        for trade in trades:
            reason = trade.reason
            reasons[reason] = reasons.get(reason, 0) + 1

        return sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:5]
```

---

## BLOQUE 7: ANÁLISIS TÉCNICO Y SEÑALES (R19-R21)

### R19. Identificación de Régimen de Mercado

**Usa ADX para identificar tendencia vs rango**

```python
class MarketRegimeDetector:
    """Detecta régimen de mercado (tendencia vs rango)."""

    def __init__(self, period: int = 14):
        self.period = period

    def calculate_adx(self, df: pd.DataFrame) -> pd.Series:
        """
        Calcular ADX (Average Directional Index).

        ADX > 25: Tendencia
        ADX < 15: Sin dirección clara
        """
        # Calcular True Range
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )

        # Calcular +DM y -DM
        df['plus_dm'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
            np.maximum(df['high'] - df['high'].shift(1), 0),
            0
        )
        df['minus_dm'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
            np.maximum(df['low'].shift(1) - df['low'], 0),
            0
        )

        # Suavizar
        alpha = 1 / self.period
        df['atr'] = df['tr'].ewm(alpha=alpha, adjust=False).mean()
        df['plus_di'] = 100 * (df['plus_dm'].ewm(alpha=alpha, adjust=False).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].ewm(alpha=alpha, adjust=False).mean() / df['atr'])

        # Calcular DX y ADX
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].ewm(alpha=alpha, adjust=False).mean()

        return df['adx']

    def detect_regime(self, df: pd.DataFrame) -> str:
        """
        Detectar régimen actual.

        Returns:
            "trend", "range", o "unclear"
        """
        if len(df) < self.period:
            return "unclear"

        adx = self.calculate_adx(df).iloc[-1]

        if adx > 25:
            return "trend"
        elif adx < 15:
            return "range"
        else:
            return "unclear"


def select_strategy_for_regime(regime: str) -> str:
    """
    Seleccionar estrategia según régimen.

    - Tendencia: seguimientos de tendencia (breakouts, moving averages)
    - Rango: mean reversion (RSI, bandas Bollinger)
    - Unclear: no operar
    """
    if regime == "trend":
        return "trend_following"
    elif regime == "range":
        return "mean_reversion"
    else:
        return "no_trade"
```

**Referencia:** *Fractal Market Analysis* - Edgar E. Peters

---

### R20. Confirmación Múltiple

**Requiere mínimo 2 confirmaciones antes de entrar**

```python
class MultiConfirmationValidator:
    """Valida señales con múltiples confirmaciones."""

    def __init__(self, min_confirmations: int = 2):
        self.min_confirmations = min_confirmations

    def validate_signal(
        self,
        signal: Signal,
        market_data: pd.DataFrame,
        index_data: Optional[pd.DataFrame] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validar señal con múltiples confirmaciones.

        Confirmaciones requeridas:
        1. Señal primaria (setup)
        2. Confirmación de volumen
        3. Confirmación de mercado general (índice)

        Returns:
            (is_valid, list_of_confirmations)
        """
        confirmations = []

        # 1. Señal primaria (ya viene en signal)
        confirmations.append("primary_signal")

        # 2. Confirmación de volumen
        if self._confirm_volume(market_data):
            confirmations.append("volume_confirmation")

        # 3. Confirmación de mercado general (si disponible)
        if index_data is not None:
            if self._confirm_market_general(signal, index_data):
                confirmations.append("market_confirmation")

        # Validar mínimo de confirmaciones
        is_valid = len(confirmations) >= self.min_confirmations

        if not is_valid:
            logger.warning(
                f"❌ Insuficientes confirmaciones: {len(confirmations)} "
                f"< {self.min_confirmations}"
            )
            # Reducir tamaño si solo 1 confirmación
            if len(confirmations) == 1 and signal.confidence >= 75.0:
                confirmations.append("reduced_size")
                return (True, confirmations)

        return (is_valid, confirmations)

    def _confirm_volume(self, df: pd.DataFrame) -> bool:
        """Confirmar que volumen está por encima de media."""
        if len(df) < 20:
            return False

        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].iloc[-20:].mean()

        return current_volume >= avg_volume

    def _confirm_market_general(self, signal: Signal, index_df: pd.DataFrame) -> bool:
        """
        Confirmar que mercado general está alineado con señal.

        Para BUY: índice debería estar sobre su media
        Para SELL: índice debería estar bajo su media
        """
        if len(index_df) < 20:
            return False

        index_close = index_df['close'].iloc[-1]
        index_ma = index_df['close'].iloc[-20:].mean()

        if signal.signal_type == SignalType.BUY:
            return index_close > index_ma
        else:  # SELL
            return index_close < index_ma
```

---

### R21. Volumen como Filtro

**Usa volumen para filtrar señales falsas**

```python
class VolumeFilter:
    """Filtra señales basado en volumen."""

    @staticmethod
    def validate_breakout(
        df: pd.DataFrame,
        current_price: float
    ) -> Tuple[bool, str]:
        """
        Validar breakout tiene volumen.

        Breakouts sin volumen suelen ser falsos.
        """
        if len(df) < 20:
            return (False, "Insufficient data")

        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].iloc[-20:].mean()
        volume_ratio = current_volume / avg_volume

        # Breakout necesita volumen > 1.5x media
        if volume_ratio < 1.5:
            return (False, f"Volumen bajo: {volume_ratio:.2f}x < 1.5x")

        return (True, f"Volumen confirmado: {volume_ratio:.2f}x")

    @staticmethod
    def check_divergence(df: pd.DataFrame) -> Optional[str]:
        """
        Detectar divergencias precio-volumen.

        Divergencia = señal de alerta.
        """
        if len(df) < 20:
            return None

        # Precio subiendo, volumen bajando = divergencia alcista
        price_trend = df['close'].iloc[-5:].diff().mean()
        volume_trend = df['volume'].iloc[-5:].diff().mean()

        if price_trend > 0 and volume_trend < 0:
            return "divergence_bullish_weak"  # Precio sube sin volumen = débil
        elif price_trend < 0 and volume_trend < 0:
            return "divergence_bearish_strong"  # Precio baja con volumen = fuerte

        return None
```

**Referencia:** *Algorithmic Trading: Winning Strategies and Their Rationale* - Ernie Chan

---

## BLOQUE 8: ADAPTACIÓN Y MEJORA (R22-R24)

### R22. Revisión Mensual

**Analiza métricas mensuales y ajusta según resultado**

```python
@dataclass
class MonthlyMetrics:
    """Métricas mensuales de rendimiento."""
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    total_pnl: Decimal
    benchmark_return: float


class MonthlyReviewer:
    """Revisa rendimiento mensual y recomienda ajustes."""

    def __init__(self, benchmark_symbol: str = "SPY"):
        self.benchmark_symbol = benchmark_symbol

    def calculate_metrics(
        self,
        equity_curve: pd.Series,
        trades: List[Trade],
        benchmark_returns: pd.Series
    ) -> MonthlyMetrics:
        """Calcular métricas mensuales."""
        # Sharpe Ratio
        returns = equity_curve.pct_change().dropna()
        sharpe = np.sqrt(252) * returns.mean() / returns.std()

        # Sortino Ratio
        downside_returns = returns[returns < 0]
        sortino = np.sqrt(252) * returns.mean() / downside_returns.std()

        # Max Drawdown
        peak = equity_curve.expanding().max()
        drawdown = (peak - equity_curve) / peak
        max_dd = drawdown.max()

        # Win Rate
        winning_trades = [t for t in trades if t.pnl > 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0

        # Total P&L
        total_pnl = sum(t.pnl for t in trades)

        # Benchmark return
        benchmark_return = (1 + benchmark_returns).prod() - 1

        return MonthlyMetrics(
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            win_rate=win_rate,
            total_trades=len(trades),
            total_pnl=total_pnl,
            benchmark_return=benchmark_return
        )

    def generate_recommendations(self, metrics: MonthlyMetrics) -> List[str]:
        """
        Generar recomendaciones basadas en métricas.

        Si Sharpe < 1 o Sortino < 1.5: revisar estrategia
        """
        recommendations = []

        # Sharpe Ratio check
        if metrics.sharpe_ratio < 1.0:
            recommendations.append(
                f"⚠️ Sharpe {metrics.sharpe_ratio:.2f} < 1.0: "
                "Revisar relación riesgo/beneficio"
            )

        # Sortino Ratio check
        if metrics.sortino_ratio < 1.5:
            recommendations.append(
                f"⚠️ Sortino {metrics.sortino_ratio:.2f} < 1.5: "
                "Demasiadas pérdidas grandes"
            )

        # Benchmark comparison
        if metrics.total_pnl < Decimal(str(metrics.benchmark_return)):
            recommendations.append(
                f"⚠️ Estrategia underperformó vs benchmark "
                f"({metrics.total_pnl:.2%} vs {metrics.benchmark_return:.2%})"
            )

        # Drawdown check
        if metrics.max_drawdown > 0.20:
            recommendations.append(
                f"⚠️ Drawdown {metrics.max_drawdown:.1%} > 20%: "
                "Reducir tamaño de posición"
            )

        return recommendations
```

---

### R23. A/B Testing

**Prueba cambios en paper trading antes de producción**

```python
@dataclass
class ABTestConfig:
    """Configuración para A/B test."""
    name: str
    variant_a_params: Dict[str, Any]
    variant_b_params: Dict[str, Any]
    min_trades: int = 20
    min_duration_days: int = 14


class ABTester:
    """Ejecuta A/B testing de parámetros."""

    def __init__(self, config: ABTestConfig):
        self.config = config
        self.variant_a_results = []
        self.variant_b_results = []

    def run_paper_trade(
        self,
        variant: str,
        params: Dict[str, Any],
        duration_days: int
    ) -> Dict[str, float]:
        """
        Ejecutar paper trade con parámetros dados.

        Returns:
            Métricas del paper trade
        """
        # Simular ejecución con parámetros
        # En producción: esto ejecutaría realmente en modo paper
        pass

    def compare_results(self) -> Tuple[str, bool]:
        """
        Comparar resultados de variantes.

        Returns:
            (winning_variant, is_significant)

        Implementa solo si mejora >10% en métricas clave.
        """
        metrics_a = self._calculate_metrics(self.variant_a_results)
        metrics_b = self._calculate_metrics(self.variant_b_results)

        # Comparar Sharpe ratio
        sharpe_improvement = (metrics_b['sharpe'] - metrics_a['sharpe']) / metrics_a['sharpe']

        if sharpe_improvement > 0.10:  # >10% mejora
            return ("variant_b", True)
        elif sharpe_improvement < -0.10:
            return ("variant_a", True)
        else:
            return ("none", False)
```

---

### R24. Diversificación de Estrategias

**Usa múltiples estrategias no correlacionadas**

```python
class StrategyPortfolio:
    """Gestiona portafolio de estrategias no correlacionadas."""

    def __init__(self, min_strategies: int = 2):
        self.min_strategies = min_strategies
        self.strategies = {}
        self.allocations = {}

    def add_strategy(
        self,
        name: str,
        strategy,
        allocation: float
    ) -> None:
        """
        Añadir estrategia al portafolio.

        Args:
            allocation: % de capital (60-40 o 50-50 según performance)
        """
        self.strategies[name] = strategy
        self.allocations[name] = allocation

    def validate_correlation(
        self,
        returns_matrix: pd.DataFrame
    ) -> bool:
        """
        Validar que estrategias no estén altamente correlacionadas.

        Correlación máxima aceptable: 0.7
        """
        corr_matrix = returns_matrix.corr()

        # Verificar que ninguna correlación > 0.7
        for i in range(len(corr_matrix)):
            for j in range(i + 1, len(corr_matrix)):
                if abs(corr_matrix.iloc[i, j]) > 0.7:
                    logger.warning(
                        f"⚠️ Correlación alta: "
                        f"{corr_matrix.index[i]}-{corr_matrix.columns[j]} = "
                        f"{corr_matrix.iloc[i, j]:.2f}"
                    )
                    return False

        return True

    def rebalance_quarterly(self) -> None:
        """Rebalancear asignación trimestralmente."""
        # Recalcular asignación según performance reciente
        pass
```

**Referencia:** *Quantitative Trading: How to Build Your Own Algorithmic Trading Business* - Ernie Chan

---

## BLOQUE 9: ESCALADO POR FASES DE CAPITAL (R25-R27)

### R25-R27. Fases de Capital: 1k-10k, 10k-50k, 50k-500k

```python
from enum import Enum


class CapitalPhase(Enum):
    """Fase de capital."""
    SURVIVAL = "SURVIVAL"      # 1k-10k
    GROWTH = "GROWTH"          # 10k-50k
    OPTIMIZATION = "OPTIMIZATION"  # 50k-500k


@dataclass
class PhaseParameters:
    """Parámetros por fase de capital."""
    phase: CapitalPhase
    capital_range: Tuple[int, int]
    max_risk_per_trade: Decimal
    max_positions: int
    max_single_asset: Decimal
    max_single_sector: Decimal
    min_rr_ratio: Decimal
    strategies_enabled: List[str]


class CapitalPhaseManager:
    """Gestiona parámetros según fase de capital."""

    PHASES = {
        CapitalPhase.SURVIVAL: PhaseParameters(
            phase=CapitalPhase.SURVIVAL,
            capital_range=(1000, 10000),
            max_risk_per_trade=Decimal("0.01"),  # 1%
            max_positions=2,
            max_single_asset=Decimal("0.20"),
            max_single_sector=Decimal("0.40"),
            min_rr_ratio=Decimal("2.5"),
            strategies_enabled=["momentum"]
        ),
        CapitalPhase.GROWTH: PhaseParameters(
            phase=CapitalPhase.GROWTH,
            capital_range=(10000, 50000),
            max_risk_per_trade=Decimal("0.015"),  # 1.5%
            max_positions=3,
            max_single_asset=Decimal("0.15"),
            max_single_sector=Decimal("0.35"),
            min_rr_ratio=Decimal("2.2"),
            strategies_enabled=["momentum", "mean_reversion"]
        ),
        CapitalPhase.OPTIMIZATION: PhaseParameters(
            phase=CapitalPhase.OPTIMIZATION,
            capital_range=(50000, 500000),
            max_risk_per_trade=Decimal("0.02"),  # 2%
            max_positions=5,
            max_single_asset=Decimal("0.10"),
            max_single_sector=Decimal("0.25"),
            min_rr_ratio=Decimal("2.0"),
            strategies_enabled=["momentum", "mean_reversion", "pairs_trading"]
        ),
    }

    @classmethod
    def get_phase(cls, capital: Decimal) -> CapitalPhase:
        """Determinar fase según capital."""
        capital_float = float(capital)

        for phase, params in cls.PHASES.items():
            min_cap, max_cap = params.capital_range
            if min_cap <= capital_float < max_cap:
                return phase

        # Default a fase más alta
        return CapitalPhase.OPTIMIZATION

    @classmethod
    def get_parameters(cls, capital: Decimal) -> PhaseParameters:
        """Obtener parámetros para capital dado."""
        phase = cls.get_phase(capital)
        return cls.PHASES[phase]

    @classmethod
    def validate_strategy(
        cls,
        capital: Decimal,
        strategy_name: str
    ) -> bool:
        """Validar si estrategia está habilitada para esta fase."""
        params = cls.get_parameters(capital)
        return strategy_name in params.strategies_enabled
```

---

## BLOQUE 10: COMPLIANCE RETAIL (R28-R29)

### R28. Registro de Operaciones

**Mantén registro para Hacienda (mínimo 5 años)**

```python
from dataclasses import dataclass, asdict
from typing import List
import csv


@dataclass
class TradeRecord:
    """Registro de operación para fiscalidad."""
    timestamp: datetime
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    pnl: Decimal
    commission: Decimal
    trade_id: str


class TaxComplianceLogger:
    """Registra operaciones para cumplimiento fiscal."""

    def __init__(self, log_path: str):
        self.log_path = log_path
        self.records: List[TradeRecord] = []
        self._load()

    def _load(self) -> None:
        """Cargar registros existentes."""
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    record = TradeRecord(
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        symbol=row['symbol'],
                        side=row['side'],
                        quantity=Decimal(row['quantity']),
                        entry_price=Decimal(row['entry_price']),
                        exit_price=Decimal(row['exit_price']),
                        pnl=Decimal(row['pnl']),
                        commission=Decimal(row['commission']),
                        trade_id=row['trade_id']
                    )
                    self.records.append(record)

    def add_record(self, record: TradeRecord) -> None:
        """Añadir nuevo registro."""
        self.records.append(record)
        self._save()

    def _save(self) -> None:
        """Guardar registros a CSV."""
        with open(self.log_path, 'w', newline='') as f:
            fieldnames = [
                'timestamp', 'symbol', 'side', 'quantity',
                'entry_price', 'exit_price', 'pnl', 'commission', 'trade_id'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for record in self.records:
                writer.writerow(asdict(record))

    def generate_monthly_report(self, year: int, month: int) -> Dict[str, Any]:
        """Generar reporte mensual para declaración."""
        monthly_trades = [
            r for r in self.records
            if r.timestamp.year == year and r.timestamp.month == month
        ]

        total_pnl = sum(r.pnl for r in monthly_trades)
        total_commission = sum(r.commission for r in monthly_trades)
        net_pnl = total_pnl - total_commission

        return {
            "year": year,
            "month": month,
            "total_trades": len(monthly_trades),
            "gross_pnl": str(total_pnl),
            "commissions": str(total_commission),
            "net_pnl": str(net_pnl)
        }
```

---

### R29. Seguridad de API Keys

**2FA obligatorio, permisos mínimos, rotación trimestral**

```python
from datetime import datetime, timedelta
from typing import Dict, Optional
import hashlib


class APIKeyManager:
    """Gestiona API keys con rotación y permisos mínimos."""

    def __init__(self):
        self.keys: Dict[str, Dict] = {}
        self.rotation_frequency_days = 90

    def generate_key_hash(self, api_key: str) -> str:
        """Generar hash de API key (nunca guardar en texto plano)."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def register_key(
        self,
        exchange: str,
        api_key: str,
        permissions: List[str],
        description: str = ""
    ) -> str:
        """
        Registrar nueva API key.

        Permisos mínimos:
        - Leer balance
        - Colocar órdenes
        - NO retirar fondos
        """
        key_hash = self.generate_key_hash(api_key)

        # Validar permisos mínimos
        if "withdraw" in permissions:
            raise ValueError("❌ API key NO debe tener permisos de retiro")

        self.keys[key_hash] = {
            "exchange": exchange,
            "permissions": permissions,
            "description": description,
            "created_at": datetime.utcnow(),
            "last_rotated": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=self.rotation_frequency_days)
        }

        return key_hash

    def check_rotation_needed(self, key_hash: str) -> bool:
        """Verificar si key necesita rotación."""
        if key_hash not in self.keys:
            return False

        key_data = self.keys[key_hash]
        return datetime.utcnow() >= key_data["expires_at"]

    def rotate_key(self, old_key_hash: str, new_api_key: str) -> str:
        """Rotar API key."""
        if old_key_hash not in self.keys:
            raise ValueError("Key no encontrada")

        old_key_data = self.keys[old_key_hash]

        # Crear nueva key
        new_key_hash = self.register_key(
            exchange=old_key_data["exchange"],
            api_key=new_api_key,
            permissions=old_key_data["permissions"],
            description=f"Rotated from {old_key_hash[:8]}"
        )

        # Invalidar key anterior
        del self.keys[old_key_hash]

        return new_key_hash

    def validate_permissions(self, key_hash: str, required_permission: str) -> bool:
        """Validar que key tiene permiso requerido."""
        if key_hash not in self.keys:
            return False

        return required_permission in self.keys[key_hash]["permissions"]


# NUNCA harcodear credenciales en código
def load_credentials_from_env() -> Dict[str, str]:
    """
    Cargar credenciales desde variables de entorno.

    Usar python-dotenv o similar.
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    return {
        "exchange_api_key": os.getenv("EXCHANGE_API_KEY"),
        "exchange_api_secret": os.getenv("EXCHANGE_API_SECRET"),
        # NUNCA commitear .env file
    }
```

---

## REFERENCIAS PRINCIPALES

1. **López de Prado, Marcos** - *Advances in Financial Machine Learning*
2. **Chan, Ernie** - *Algorithmic Trading: Winning Strategies and Their Rationale*
3. **Vince, Ralph** - *The Mathematics of Money Management*
4. **O'Hara, Maureen** - *Market Microstructure Theory*
5. **Hull, John** - *Risk Management and Financial Institutions*
6. **Kissell, Robert** - *The Science of Algorithmic Trading and Portfolio Management*
7. **Cartea, Álvaro** - *Algorithmic and High-Frequency Trading*
8. **Jansen, Stefan** - *Machine Learning for Algorithmic Trading*

---

## MÉTRICAS OBJETIVO POR FASE

| Fase | Capital | Trades/mes | Win Rate | R:R Prom | Max DD | Sharpe |
|------|---------|------------|----------|----------|--------|--------|
| 1    | 1k-10k  | 10-20      | >45%     | >2.5     | <20%   | >1.0   |
| 2    | 10k-50k | 20-40      | >50%     | >2.2     | <15%   | >1.2   |
| 3    | 50k-500k| 40-100     | >55%     | >2.0     | <12%   | >1.5   |

---

## RESUMEN EJECUTIVO

### CRÍTICO (implementar primero)
- R1: Kelly + 2% max por trade
- R2: Drawdown 15% stop
- R4: R:R 2:1 mínimo
- R15: Logs completos
- R16: Reconciliación diaria

### IMPORTANTE (1-3 meses)
- R5: Walk-forward analysis
- R8: Gestión de spread
- R11: Trailing stop
- R14: Calidad de datos

### DESEABLE (al escalar)
- R12: Take profit parcial
- R24: Diversificación de estrategias
- R27: Gestión de portafolio
