"""
Market Microstructure Models Module

This module implements the foundational market microstructure models from
Maureen O'Hara's "Market Microstructure Theory" and related literature.

Key Models Implemented:
1. Glosten-Milgrom (1985): Sequential trade model with adverse selection
2. Kyle (1985): Strategic trading and market depth
3. Madhavan-Richardson-Rooms (1997): Order flow and price dynamics
4. Roll (1984): Bid-ask spread and serial covariance
5. Stoll (2000): Spread decomposition

These models form the theoretical foundation for understanding how
information is incorporated into market prices through trading.

References:
- O'Hara, M. (1995) "Market Microstructure Theory"
- Glosten, L.R., & Milgrom, P.R. (1985) "Bid, Ask and Transaction Prices"
- Kyle, A.S. (1985) "Continuous Auctions and Insider Trading"
- Madhavan, A., Richardson, M., & Roomans, M. (1997) "Why Do Stock Prices Move?"
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

import numpy as np
import pandas as pd


class ModelType(Enum):
    """Types of microstructure models"""

    GLOSTEN_MILGROM = "GLOSTEN_MILGROM"  # Sequential trade
    KYLE = "KYLE"  # Strategic informed trading
    MADHAVAN_RICHARDSON = "MADHAVAN_RICHARDSON"  # Order flow dynamics
    ROLL = "ROLL"  # Spread estimation
    STOLL = "STOLL"  # Spread decomposition


class InformationEvent(Enum):
    """Types of information events in models"""

    NONE = "NONE"  # No new information
    GOOD = "GOOD"  # Positive information
    BAD = "BAD"  # Negative information


@dataclass
class ModelParameters:
    """
    Generic model parameters

    Attributes:
        alpha: Probability of information event
        delta: Probability of bad news given event
        mu: Informed trader arrival rate
        epsilon: Uninformed trader arrival rate (buy = sell)
        sigma: Informed trader order size
    """

    alpha: float  # Information event probability
    delta: float  # Bad news probability
    mu: float  # Informed trader intensity
    epsilon: float  # Uninformed trader intensity
    sigma: float  # Informed trader size

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'alpha': self.alpha,
            'delta': self.delta,
            'mu': self.mu,
            'epsilon': self.epsilon,
            'sigma': self.sigma,
        }


@dataclass
class GlostenMilgromResult:
    """
    Results from Glosten-Milgrom model

    The GM model shows how dealers set quotes to compensate for
    adverse selection from informed traders

    Attributes:
        timestamp: Calculation time
        bid_price: Equilibrium bid price
        ask_price: Equilibrium ask price
        spread_bps: Spread in basis points
        adverse_selection_component: Portion of spread due to adverse selection
        informed_trading_probability: Probability current trade is informed
    """

    timestamp: datetime
    bid_price: Decimal
    ask_price: Decimal
    spread_bps: float
    adverse_selection_component: float
    informed_trading_probability: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'bid_price': str(self.bid_price),
            'ask_price': str(self.ask_price),
            'spread_bps': self.spread_bps,
            'adverse_selection_component_pct': self.adverse_selection_component * 100,
            'informed_trading_probability_pct': self.informed_trading_probability * 100,
        }


@dataclass
class KyleModelResult:
    """
    Results from Kyle (1985) model

    Kyle model analyzes strategic trading by informed traders who
    optimize their trading to maximize profits while concealing information

    Attributes:
        timestamp: Calculation time
        market_depth_lambda: Market depth parameter (impact per unit)
        expected_informed_profit: Expected profit of informed trader
        optimal_order_size: Optimal order size for informed trader
        price_impact: Expected price impact
        information_revelation: How much information is revealed
    """

    timestamp: datetime
    market_depth_lambda: float
    expected_informed_profit: float
    optimal_order_size: float
    price_impact: float
    information_revelation: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'market_depth_lambda': self.market_depth_lambda,
            'expected_informed_profit': self.expected_informed_profit,
            'optimal_order_size': self.optimal_order_size,
            'price_impact': self.price_impact,
            'information_revelation_pct': self.information_revelation * 100,
        }


@dataclass
class OrderFlowImpactResult:
    """
    Results from Madhavan-Richardson-Rooms model

    Analyzes how order flow impacts prices and how this impact
    decays over time

    Attributes:
        timestamp: Calculation time
        immediate_impact: Immediate price impact
        permanent_impact: Long-run price impact
        impact_decay: Decay rate of temporary impact
        information_content: Information content of order flow
        adjustment_speed: Speed of price adjustment
    """

    timestamp: datetime
    immediate_impact: float
    permanent_impact: float
    impact_decay: float
    information_content: float
    adjustment_speed: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'immediate_impact_bps': self.immediate_impact,
            'permanent_impact_bps': self.permanent_impact,
            'impact_decay_rate': self.impact_decay,
            'information_content': self.information_content,
            'adjustment_speed': self.adjustment_speed,
        }


@dataclass
class RollSpreadResult:
    """
    Results from Roll (1984) spread estimation model

    Estimates effective spread from first-order serial covariance
    of price changes

    Attributes:
        timestamp: Calculation time
        estimated_spread_bps: Estimated effective spread
        covariance: First-order serial covariance
        spread_std_error: Standard error of spread estimate
        is_significant: Whether spread is statistically significant
    """

    timestamp: datetime
    estimated_spread_bps: float
    covariance: float
    spread_std_error: float
    is_significant: bool

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'estimated_spread_bps': self.estimated_spread_bps,
            'covariance': self.covariance,
            'spread_std_error': self.spread_std_error,
            'is_significant': self.is_significant,
        }


@dataclass
class StollDecompositionResult:
    """
    Results from Stoll (2000) spread decomposition model

    Decomposes spread into order processing, inventory holding,
    and adverse selection components

    Attributes:
        timestamp: Calculation time
        total_spread_bps: Total observed spread
        order_processing_bps: Fixed cost component
        inventory_holding_bps: Inventory risk component
        adverse_selection_bps: Information asymmetry component
        component_weights: Weight of each component
    """

    timestamp: datetime
    total_spread_bps: float
    order_processing_bps: float
    inventory_holding_bps: float
    adverse_selection_bps: float
    component_weights: dict[str, float]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_spread_bps': self.total_spread_bps,
            'order_processing_bps': self.order_processing_bps,
            'inventory_holding_bps': self.inventory_holding_bps,
            'adverse_selection_bps': self.adverse_selection_bps,
            'component_weights': self.component_weights,
        }


class GlostenMilgromModel:
    """
    Implements the Glosten-Milgrom (1985) sequential trade model

    Key insights:
    1. Bid-ask spread arises from adverse selection risk
    2. Spreads are wider when informed trading is more likely
    3. Quote adjustments depend on trade direction

    Model structure:
    - With probability α: information event occurs
      - With probability δ: Bad news (value goes to 0)
      - With probability 1-δ: Good news (value goes to 1)
    - With probability 1-α: No information event (value stays at V₀)
    """

    def __init__(
        self,
        initial_value: float = 100.0,
        alpha: float = 0.2,  # Information event probability
        delta: float = 0.5,  # Bad news probability
        mu: float = 0.1,  # Informed trader arrival rate
        epsilon: float = 0.5,  # Uninformed arrival rate
    ):
        """
        Initialize Glosten-Milgrom model

        Args:
            initial_value: Initial fundamental value
            alpha: Probability of information event
            delta: Probability of bad news given event
            mu: Informed trader arrival rate
            epsilon: Uninformed trader arrival rate (buy = sell)
        """
        self.initial_value = initial_value
        self.alpha = alpha
        self.delta = delta
        self.mu = mu
        self.epsilon = epsilon
        self.current_value = initial_value

    def calculate_equilibrium_spread(self) -> Tuple[float, float]:
        """
        Calculate equilibrium bid and ask prices

        In GM model, quotes are set to expected value conditional on
        buying or selling

        Bid = E[V | sell]
        Ask = E[V | buy]

        Returns:
            Tuple of (bid_price, ask_price)
        """
        V0 = self.initial_value
        V_low = 0  # Value with bad news
        V_high = 2 * V0  # Value with good news (assumes symmetric)

        # Calculate unconditional value
        # E[V] = (1-α)*V₀ + α*δ*V_low + α*(1-δ)*V_high
        #      = (1-α)*V₀ + α*(1-δ)*2*V₀
        (1 - self.alpha) * V0 + self.alpha * (1 - self.delta) * 2 * V0

        # Probability sell is informed
        # P(informed | sell) = P(sell | informed)*P(informed) / P(sell)
        informed_sell_rate = self.alpha * self.delta * self.mu
        uninformed_sell_rate = (1 - self.alpha) * self.epsilon
        total_sell_rate = informed_sell_rate + uninformed_sell_rate

        if total_sell_rate > 0:
            prob_informed_given_sell = informed_sell_rate / total_sell_rate
        else:
            prob_informed_given_sell = 0

        # Probability buy is informed
        informed_buy_rate = self.alpha * (1 - self.delta) * self.mu
        uninformed_buy_rate = (1 - self.alpha) * self.epsilon
        total_buy_rate = informed_buy_rate + uninformed_buy_rate

        if total_buy_rate > 0:
            prob_informed_given_buy = informed_buy_rate / total_buy_rate
        else:
            prob_informed_given_buy = 0

        # Expected value conditional on trade
        # E[V | sell] = prob_informed_given_sell * V_low + (1 - prob_informed_given_sell) * V₀
        bid = prob_informed_given_sell * V_low + (1 - prob_informed_given_sell) * V0

        # E[V | buy] = prob_informed_given_buy * V_high + (1 - prob_informed_given_buy) * V₀
        ask = prob_informed_given_buy * V_high + (1 - prob_informed_given_buy) * V0

        return bid, ask

    def simulate_trade_sequence(
        self,
        num_trades: int,
        information_event: InformationEvent | None = None,
    ) -> pd.DataFrame:
        """
        Simulate a sequence of trades

        Args:
            num_trades: Number of trades to simulate
            information_event: Type of information event (None = random)

        Returns:
            DataFrame with trade sequence
        """
        # Determine information event
        if information_event is None:
            if np.random.random() < self.alpha:
                information_event = (
                    InformationEvent.BAD
                    if np.random.random() < self.delta
                    else InformationEvent.GOOD
                )
            else:
                information_event = InformationEvent.NONE

        # Set true value
        if information_event == InformationEvent.BAD:
            true_value = 0
        elif information_event == InformationEvent.GOOD:
            true_value = 2 * self.initial_value
        else:
            true_value = self.initial_value

        # Simulate trades
        trades = []
        current_bid = self.initial_value
        current_ask = self.initial_value

        for i in range(num_trades):
            # Determine trader type and direction
            rand = np.random.random()

            # Calculate arrival probabilities
            total_rate = self.mu + 2 * self.epsilon
            prob_informed = self.mu / total_rate
            prob_uninformed_buy = self.epsilon / total_rate
            self.epsilon / total_rate

            if rand < prob_informed:
                # Informed trader
                if true_value > current_bid:
                    side = 'BUY'
                elif true_value < current_ask:
                    side = 'SELL'
                else:
                    side = np.random.choice(['BUY', 'SELL'])
                trader_type = 'INFORMED'
            elif rand < prob_informed + prob_uninformed_buy:
                side = 'BUY'
                trader_type = 'UNINFORMED'
            else:
                side = 'SELL'
                trader_type = 'UNINFORMED'

            # Execute trade at mid
            execution_price = (current_bid + current_ask) / 2

            trades.append(
                {
                    'trade_num': i + 1,
                    'side': side,
                    'trader_type': trader_type,
                    'price': execution_price,
                    'bid': current_bid,
                    'ask': current_ask,
                    'spread': current_ask - current_bid,
                    'true_value': true_value,
                    'information_event': information_event.value,
                }
            )

            # Update quotes
            if side == 'BUY':
                # Buy signal: increase quotes
                current_bid = min(current_bid * 1.01, true_value)
                current_ask = min(current_ask * 1.01, true_value)
            else:
                # Sell signal: decrease quotes
                current_bid = max(current_bid * 0.99, true_value)
                current_ask = max(current_ask * 0.99, true_value)

        return pd.DataFrame(trades)

    def calculate_spread_components(self) -> dict[str, float]:
        """
        Decompose spread into components

        In GM model, spread is entirely due to adverse selection
        (no inventory costs or order processing costs in basic model)

        Returns:
            Dictionary with component breakdown
        """
        bid, ask = self.calculate_equilibrium_spread()
        total_spread = ask - bid

        # In basic GM model, entire spread is adverse selection

        # Calculate percentages
        if total_spread > 0:
            return {
                'total_spread': total_spread,
                'adverse_selection_pct': 100.0,
                'order_processing_pct': 0.0,
                'inventory_holding_pct': 0.0,
            }
        else:
            return {
                'total_spread': 0.0,
                'adverse_selection_pct': 0.0,
                'order_processing_pct': 0.0,
                'inventory_holding_pct': 0.0,
            }


class KyleModel:
    """
    Implements the Kyle (1985) strategic informed trading model

    Key insights:
    1. Informed traders trade strategically to conceal information
    2. Market depth determines how much they can trade before moving price
    3. Ultimately all information is revealed in price

    Model structure:
    - Informed trader observes true value v ~ N(V₀, Σ₀)
    - Submits order x = X(v)
    - Noise traders submit random order u ~ N(0, σᵤ²)
    - Market maker observes total flow y = x + u
    - Sets price p = E[v | y] = V₀ + λy
    """

    def __init__(
        self,
        V0: float = 100.0,  # Prior expected value
        Sigma0: float = 25.0,  # Prior variance
        Sigma_u: float = 100.0,  # Noise trader variance
    ):
        """
        Initialize Kyle model

        Args:
            V0: Prior expected value
            Sigma0: Prior variance of value
            Sigma_u: Variance of noise trader demand
        """
        self.V0 = V0
        self.Sigma0 = Sigma0
        self.Sigma_u = Sigma_u

        # Calculate equilibrium lambda (market depth parameter)
        # λ = σᵥ / σᵤ where σᵥ² = Σ₀
        self.lambda_kyle = np.sqrt(Sigma0) / np.sqrt(Sigma_u)

    def calculate_market_depth(self) -> float:
        """
        Calculate market depth (lambda)

        Lambda is the price impact per unit of order flow
        Higher lambda = less depth = more impact

        Returns:
            Market depth parameter
        """
        return self.lambda_kyle

    def calculate_optimal_informed_trading(
        self,
        true_value: float,
    ) -> KyleModelResult:
        """
        Calculate optimal informed trading strategy

        Informed trader maximizes: E[(v - p)x]
        Optimal strategy: x = (v - V₀) / (2λ)

        Args:
            true_value: Actual fundamental value known to informed trader

        Returns:
            KyleModelResult with analysis
        """
        # Optimal order size
        information_signal = true_value - self.V0
        optimal_order = information_signal / (2 * self.lambda_kyle)

        # Expected profit
        expected_profit = (information_signal**2) / (4 * self.lambda_kyle)

        # Price impact
        price_impact = self.lambda_kyle * optimal_order

        # Information revelation (how much of signal gets into price)
        # In equilibrium, λ = σᵥ/(2σᵤ) for partial revelation
        # All information revealed in final price
        information_revelation = 1.0  # Complete revelation in Kyle model

        return KyleModelResult(
            timestamp=datetime.now(),
            market_depth_lambda=self.lambda_kyle,
            expected_informed_profit=expected_profit,
            optimal_order_size=optimal_order,
            price_impact=price_impact,
            information_revelation=information_revelation,
        )

    def simulate_kyle_equilibrium(
        self,
        num_periods: int = 10,
    ) -> pd.DataFrame:
        """
        Simulate Kyle model over multiple periods

        Args:
            num_periods: Number of trading periods

        Returns:
            DataFrame with simulation results
        """
        results = []

        # Simulate sequence of information events
        for t in range(num_periods):
            # Draw true value
            true_value = np.random.normal(self.V0, np.sqrt(self.Sigma0))

            # Informed trader's optimal order
            signal = true_value - self.V0
            informed_order = signal / (2 * self.lambda_kyle)

            # Noise trader demand
            noise_order = np.random.normal(0, np.sqrt(self.Sigma_u))

            # Total order flow
            total_flow = informed_order + noise_order

            # Market maker sets price
            transaction_price = self.V0 + self.lambda_kyle * total_flow

            # Calculate profit
            informed_profit = (true_value - transaction_price) * informed_order

            results.append(
                {
                    'period': t + 1,
                    'true_value': true_value,
                    'informed_order': informed_order,
                    'noise_order': noise_order,
                    'total_flow': total_flow,
                    'transaction_price': transaction_price,
                    'price_error': transaction_price - true_value,
                    'informed_profit': informed_profit,
                }
            )

        return pd.DataFrame(results)


class MadhavanRichardsonModel:
    """
    Implements the Madhavan-Richardson-Rooms (1997) order flow model

    Analyzes how order flow impacts prices in both short and long run
    """

    def __init__(
        self,
        price_impact: float = 0.001,
        decay_rate: float = 0.5,
    ):
        """
        Initialize MRR model

        Args:
            price_impact: Immediate price impact per unit flow
            decay_rate: Rate at which temporary impact decays
        """
        self.price_impact = price_impact
        self.decay_rate = decay_rate

    def estimate_order_flow_impact(
        self,
        order_flow: pd.Series,
        price_changes: pd.Series,
    ) -> OrderFlowImpactResult:
        """
        Estimate order flow impact on prices

        Uses regression to decompose impact into permanent and temporary

        Args:
            order_flow: Signed order flow series
            price_changes: Price change series

        Returns:
            OrderFlowImpactResult
        """
        # Align series
        min_len = min(len(order_flow), len(price_changes))
        flow = order_flow.tail(min_len).values
        changes = price_changes.tail(min_len).values

        if min_len < 10:
            return OrderFlowImpactResult(
                timestamp=datetime.now(),
                immediate_impact=0.0,
                permanent_impact=0.0,
                impact_decay=0.0,
                information_content=0.0,
                adjustment_speed=0.0,
            )

        # Regress price changes on order flow
        # Δp = γ * flow + ε
        try:
            flow = flow.reshape(-1, 1)
            gamma, _, _, _ = np.linalg.lstsq(flow, changes, rcond=None)

            permanent_impact = float(gamma[0])
            immediate_impact = permanent_impact * 1.5  # Temporary impact adds to immediate

        except Exception:
            permanent_impact = 0.0
            immediate_impact = 0.0

        # Information content
        information_content = abs(np.corrcoef(flow.flatten(), changes)[0, 1])

        return OrderFlowImpactResult(
            timestamp=datetime.now(),
            immediate_impact=immediate_impact * 10000,  # Convert to bps
            permanent_impact=permanent_impact * 10000,
            impact_decay=self.decay_rate,
            information_content=information_content,
            adjustment_speed=1 - self.decay_rate,
        )


class RollSpreadEstimator:
    """
    Implements Roll (1984) spread estimator

    Estimates effective spread from serial covariance of returns
    based on bid-ask bounce

    Key insight:
    Cov(Δp, Δp-1) = -s²/4
    where s is the effective spread
    """

    def __init__(self):
        """Initialize Roll estimator"""
        pass

    def estimate_spread(
        self,
        price_series: pd.Series,
    ) -> RollSpreadResult:
        """
        Estimate effective spread from price series

        Args:
            price_series: Series of transaction prices

        Returns:
            RollSpreadResult with estimate
        """
        if len(price_series) < 10:
            return RollSpreadResult(
                timestamp=datetime.now(),
                estimated_spread_bps=0.0,
                covariance=0.0,
                spread_std_error=0.0,
                is_significant=False,
            )

        # Calculate returns
        returns = price_series.pct_change().dropna()

        # Calculate first-order serial covariance
        if len(returns) >= 2:
            covariance = returns.iloc[1:].cov(returns.iloc[:-1])
        else:
            covariance = 0.0

        # Estimate spread: s = 2*sqrt(-cov)
        if covariance < 0:
            estimated_spread = 2 * np.sqrt(-covariance)
        else:
            estimated_spread = 0.0

        # Standard error (simplified)
        std_error = abs(covariance) / np.sqrt(len(returns))

        # Significance test
        is_significant = covariance < -std_error * 1.96

        return RollSpreadResult(
            timestamp=datetime.now(),
            estimated_spread_bps=estimated_spread * 10000,  # Convert to bps
            covariance=covariance,
            spread_std_error=std_error,
            is_significant=is_significant,
        )


class StollSpreadDecomposer:
    """
    Implements Stoll (2000) spread decomposition

    Decomposes observed spread into:
    1. Order processing costs
    2. Inventory holding costs
    3. Adverse selection costs
    """

    def __init__(self):
        """Initialize Stoll decomposer"""
        pass

    def decompose_spread(
        self,
        observed_spread_bps: float,
        price_variance: float,
        order_flow_imbalance: float,
        volume: float,
        volatility: float,
    ) -> StollDecompositionResult:
        """
        Decompose spread into components

        Args:
            observed_spread_bps: Observed bid-ask spread
            price_variance: Variance of returns
            order_flow_imbalance: Order flow imbalance
            volume: Trading volume
            volatility: Price volatility

        Returns:
            StollDecompositionResult
        """
        # Order processing component (fixed)
        # Typically 25-35% of spread
        order_processing = observed_spread_bps * 0.30

        # Inventory holding component
        # Proportional to volatility
        inventory_holding = min(
            observed_spread_bps * 0.40, volatility * 100 * np.sqrt(price_variance)
        )

        # Adverse selection component
        # Proportional to order flow imbalance
        adverse_selection = observed_spread_bps * abs(order_flow_imbalance) * 0.5

        # Ensure components sum to total
        total_components = order_processing + inventory_holding + adverse_selection
        if total_components > 0:
            scaling = observed_spread_bps / total_components
            order_processing *= scaling
            inventory_holding *= scaling
            adverse_selection *= scaling
        else:
            # Default equal split
            third = observed_spread_bps / 3
            order_processing = third
            inventory_holding = third
            adverse_selection = third

        # Calculate weights
        if observed_spread_bps > 0:
            weights: dict[str, float] = {
                'order_processing': order_processing / observed_spread_bps,
                'inventory_holding': inventory_holding / observed_spread_bps,
                'adverse_selection': adverse_selection / observed_spread_bps,
            }
        else:
            weights: dict[str, float] = {
                'order_processing': 0.0,
                'inventory_holding': 0.0,
                'adverse_selection': 0.0,
            }

        return StollDecompositionResult(
            timestamp=datetime.now(),
            total_spread_bps=observed_spread_bps,
            order_processing_bps=order_processing,
            inventory_holding_bps=inventory_holding,
            adverse_selection_bps=adverse_selection,
            component_weights=weights,
        )


class MicrostructureModelComparator:
    """
    Compares results across different microstructure models
    """

    def __init__(self):
        """Initialize comparator"""
        self.gm_model = GlostenMilgromModel()
        self.kyle_model = KyleModel()
        self.roll_estimator = RollSpreadEstimator()
        self.stoll_decomposer = StollSpreadDecomposer()

    def analyze_market(
        self,
        price_history: pd.DataFrame,
        order_flow: pd.Series | None = None,
    ) -> dict:
        """
        Run comprehensive microstructure model analysis

        Args:
            price_history: Price history with 'close' column
            order_flow: Optional order flow series

        Returns:
            Dictionary with results from all models
        """
        results = {}

        # Roll spread estimate
        roll_result = self.roll_estimator.estimate_spread(price_history['close'])
        results['roll'] = roll_result.to_dict()

        # Glosten-Milgrom equilibrium spread
        bid, ask = self.gm_model.calculate_equilibrium_spread()
        spread_bps = (ask - bid) / ((bid + ask) / 2) * 10000
        results['glosten_milgrom'] = {
            'bid': bid,
            'ask': ask,
            'spread_bps': spread_bps,
            'spread_components': self.gm_model.calculate_spread_components(),
        }

        # Kyle market depth
        lambda_kyle = self.kyle_model.calculate_market_depth()
        results['kyle'] = {
            'market_depth_lambda': lambda_kyle,
            'interpretation': 'Higher values = less depth = more impact',
        }

        # Stoll decomposition
        if len(price_history) >= 20:
            returns = price_history['close'].pct_change().dropna()
            volatility = returns.tail(20).std()
            variance = returns.tail(20).var()
            volume = (
                price_history['volume'].tail(20).mean()
                if 'volume' in price_history.columns
                else 1000000
            )

            # Estimate order imbalance from price direction
            price_direction = np.sign(returns.tail(20).sum())
            order_imbalance = abs(price_direction) * 0.3

            stoll_result = self.stoll_decomposer.decompose_spread(
                observed_spread_bps=roll_result.estimated_spread_bps,
                price_variance=variance,
                order_flow_imbalance=order_imbalance,
                volume=volume,
                volatility=volatility,
            )
            results['stoll'] = stoll_result.to_dict()

        return results


# Singleton instances
_gm_model: GlostenMilgromModel | None = None
_kyle_model: KyleModel | None = None
_mrr_model: MadhavanRichardsonModel | None = None
_roll_estimator: RollSpreadEstimator | None = None
_stoll_decomposer: StollSpreadDecomposer | None = None
_model_comparator: MicrostructureModelComparator | None = None


def get_glosten_milgrom_model(
    initial_value: float = 100.0,
    alpha: float = 0.2,
    delta: float = 0.5,
    mu: float = 0.1,
    epsilon: float = 0.5,
) -> GlostenMilgromModel:
    """Get or create Glosten-Milgrom model instance"""
    global _gm_model
    if _gm_model is None:
        _gm_model = GlostenMilgromModel(
            initial_value=initial_value,
            alpha=alpha,
            delta=delta,
            mu=mu,
            epsilon=epsilon,
        )
    return _gm_model


def get_kyle_model(
    V0: float = 100.0,
    Sigma0: float = 25.0,
    Sigma_u: float = 100.0,
) -> KyleModel:
    """Get or create Kyle model instance"""
    global _kyle_model
    if _kyle_model is None:
        _kyle_model = KyleModel(V0=V0, Sigma0=Sigma0, Sigma_u=Sigma_u)
    return _kyle_model


def get_madhavanh_richardson_model(
    price_impact: float = 0.001,
    decay_rate: float = 0.5,
) -> MadhavanRichardsonModel:
    """Get or create MRR model instance"""
    global _mrr_model
    if _mrr_model is None:
        _mrr_model = MadhavanRichardsonModel(
            price_impact=price_impact,
            decay_rate=decay_rate,
        )
    return _mrr_model


def get_roll_estimator() -> RollSpreadEstimator:
    """Get or create Roll estimator instance"""
    global _roll_estimator
    if _roll_estimator is None:
        _roll_estimator = RollSpreadEstimator()
    return _roll_estimator


def get_stoll_decomposer() -> StollSpreadDecomposer:
    """Get or create Stoll decomposer instance"""
    global _stoll_decomposer
    if _stoll_decomposer is None:
        _stoll_decomposer = StollSpreadDecomposer()
    return _stoll_decomposer


def get_model_comparator() -> MicrostructureModelComparator:
    """Get or create model comparator instance"""
    global _model_comparator
    if _model_comparator is None:
        _model_comparator = MicrostructureModelComparator()
    return _model_comparator


__all__ = [
    "ModelType",
    "InformationEvent",
    "ModelParameters",
    "GlostenMilgromResult",
    "KyleModelResult",
    "OrderFlowImpactResult",
    "RollSpreadResult",
    "StollDecompositionResult",
    "GlostenMilgromModel",
    "KyleModel",
    "MadhavanRichardsonModel",
    "RollSpreadEstimator",
    "StollSpreadDecomposer",
    "MicrostructureModelComparator",
    "get_glosten_milgrom_model",
    "get_kyle_model",
    "get_madhavanh_richardson_model",
    "get_roll_estimator",
    "get_stoll_decomposer",
    "get_model_comparator",
]
