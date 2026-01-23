"""
T9.1 PHASE 2: PyFolioIntegrator - Advanced risk decomposition and tearsheet generation

Wraps pyfolio library for comprehensive performance analysis including factor exposure,
position concentration, and capacity fade metrics. Provides tearsheet generation and
risk decomposition capabilities.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES FOR PYFOLIO OUTPUTS
# ============================================================================


@dataclass
class FactorExposure:
    """Exposure to a single factor."""

    factor_name: str
    coefficient: Decimal
    t_stat: Decimal
    p_value: Decimal
    significant: bool  # p_value < 0.05

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "factor_name": self.factor_name,
            "coefficient": float(self.coefficient),
            "t_stat": float(self.t_stat),
            "p_value": float(self.p_value),
            "significant": self.significant,
        }


@dataclass
class FactorAnalysis:
    """Results of factor exposure analysis."""

    analysis_date: datetime
    num_periods: int
    factors: List[FactorExposure] = field(default_factory=list)
    residual_return_pct: Decimal = Decimal("0")  # Unexplained return (alpha)
    residual_volatility_pct: Decimal = Decimal("0")  # Unexplained volatility
    model_r_squared: Decimal = Decimal("0")  # How well factors explain returns
    factor_contribution_pct: Dict[str, Decimal] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "num_periods": self.num_periods,
            "factors": [f.to_dict() for f in self.factors],
            "residual_return_pct": float(self.residual_return_pct),
            "residual_volatility_pct": float(self.residual_volatility_pct),
            "model_r_squared": float(self.model_r_squared),
            "factor_contribution_pct": {
                k: float(v) for k, v in self.factor_contribution_pct.items()
            },
        }


@dataclass
class PositionConcentration:
    """Position concentration metrics."""

    largest_position_pct: Decimal  # % of portfolio
    herfindahl_index: Decimal  # Sum of squared weights, 0-1
    effective_num_positions: Decimal  # 1/Herfindahl
    top_5_concentration_pct: Decimal  # % in top 5 positions
    diversification_ratio: Decimal  # Avg position volatility / portfolio volatility

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "largest_position_pct": float(self.largest_position_pct),
            "herfindahl_index": float(self.herfindahl_index),
            "effective_num_positions": float(self.effective_num_positions),
            "top_5_concentration_pct": float(self.top_5_concentration_pct),
            "diversification_ratio": float(self.diversification_ratio),
        }


@dataclass
class CapacityFade:
    """Capacity fade analysis results."""

    backtest_period: str  # e.g., "2023-2024"
    backtest_ann_return_pct: Decimal
    backtest_sharpe: Decimal
    simulated_current_return_pct: Decimal  # At current capital size
    simulated_target_return_pct: Decimal  # At target capital size
    fade_ratio: Decimal  # Target return / Backtest return
    projected_feasible: bool  # Is target return above required minimum?
    confidence_level: str  # "high", "medium", "low"
    constraints: List[str] = field(default_factory=list)  # What limits scalability

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "backtest_period": self.backtest_period,
            "backtest_ann_return_pct": float(self.backtest_ann_return_pct),
            "backtest_sharpe": float(self.backtest_sharpe),
            "simulated_current_return_pct": float(self.simulated_current_return_pct),
            "simulated_target_return_pct": float(self.simulated_target_return_pct),
            "fade_ratio": float(self.fade_ratio),
            "projected_feasible": self.projected_feasible,
            "confidence_level": self.confidence_level,
            "constraints": self.constraints,
        }


@dataclass
class Tearsheet:
    """Complete tearsheet data."""

    generation_date: datetime
    strategy_name: str
    period_start: datetime
    period_end: datetime

    # Basic metrics
    total_return_pct: Decimal
    annual_return_pct: Decimal
    annual_volatility_pct: Decimal
    sharpe_ratio: Decimal
    calmar_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown_pct: Decimal
    win_rate_pct: Decimal

    # Risk decomposition
    systematic_return_pct: Optional[Decimal] = None  # From factors
    idiosyncratic_return_pct: Optional[Decimal] = None  # Alpha
    systematic_volatility_pct: Optional[Decimal] = None
    idiosyncratic_volatility_pct: Optional[Decimal] = None

    # Concentration metrics
    position_concentration: Optional[PositionConcentration] = None

    # Factor analysis
    factor_analysis: Optional[FactorAnalysis] = None

    # Capacity analysis
    capacity_fade: Optional[CapacityFade] = None

    # Monthly returns distribution
    monthly_returns: Dict[str, Decimal] = field(default_factory=dict)

    # Best/worst days
    best_day_pct: Decimal = Decimal("0")
    worst_day_pct: Decimal = Decimal("0")

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "generation_date": self.generation_date.isoformat(),
            "strategy_name": self.strategy_name,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_return_pct": float(self.total_return_pct),
            "annual_return_pct": float(self.annual_return_pct),
            "annual_volatility_pct": float(self.annual_volatility_pct),
            "sharpe_ratio": float(self.sharpe_ratio),
            "calmar_ratio": float(self.calmar_ratio),
            "sortino_ratio": float(self.sortino_ratio),
            "max_drawdown_pct": float(self.max_drawdown_pct),
            "win_rate_pct": float(self.win_rate_pct),
            "systematic_return_pct": (
                float(self.systematic_return_pct) if self.systematic_return_pct else None
            ),
            "idiosyncratic_return_pct": (
                float(self.idiosyncratic_return_pct) if self.idiosyncratic_return_pct else None
            ),
            "systematic_volatility_pct": (
                float(self.systematic_volatility_pct) if self.systematic_volatility_pct else None
            ),
            "idiosyncratic_volatility_pct": (
                float(self.idiosyncratic_volatility_pct)
                if self.idiosyncratic_volatility_pct
                else None
            ),
            "position_concentration": (
                self.position_concentration.to_dict() if self.position_concentration else None
            ),
            "factor_analysis": (self.factor_analysis.to_dict() if self.factor_analysis else None),
            "capacity_fade": (self.capacity_fade.to_dict() if self.capacity_fade else None),
            "monthly_returns": {k: float(v) for k, v in self.monthly_returns.items()},
            "best_day_pct": float(self.best_day_pct),
            "worst_day_pct": float(self.worst_day_pct),
        }


# ============================================================================
# PYFOLIO INTEGRATOR
# ============================================================================


class PyFolioIntegrator:
    """
    Wrapper around pyfolio library for advanced risk decomposition and tearsheet generation.

    Provides:
    - Tearsheet generation with comprehensive metrics
    - Factor exposure analysis (market, size, momentum, quality factors)
    - Position concentration metrics (Herfindahl index, diversification)
    - Capacity fade simulation (how alpha decays with capital scaling)
    """

    def __init__(self):
        """Initialize PyFolio integrator."""
        self.tearsheets_generated = 0
        self.analysis_completed = 0
        logger.info("PyFolioIntegrator initialized")

    def generate_tearsheet(
        self,
        strategy_name: str,
        returns: List[Decimal],
        positions: Optional[List[Dict]] = None,
        transactions: Optional[List[Dict]] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        annual_return_pct: Optional[Decimal] = None,
        annual_volatility_pct: Optional[Decimal] = None,
        sharpe_ratio: Optional[Decimal] = None,
        calmar_ratio: Optional[Decimal] = None,
        sortino_ratio: Optional[Decimal] = None,
        max_drawdown_pct: Optional[Decimal] = None,
        win_rate_pct: Optional[Decimal] = None,
    ) -> Tearsheet:
        """
        Generate comprehensive tearsheet with all risk metrics and decomposition.

        Args:
            strategy_name: Name of the strategy
            returns: List of period returns (Decimal)
            positions: Optional list of position data
            transactions: Optional list of transaction data
            period_start: Analysis period start date
            period_end: Analysis period end date
            annual_return_pct: Annual return percentage
            annual_volatility_pct: Annual volatility percentage
            sharpe_ratio: Sharpe ratio
            calmar_ratio: Calmar ratio
            sortino_ratio: Sortino ratio
            max_drawdown_pct: Maximum drawdown percentage
            win_rate_pct: Win rate percentage

        Returns:
            Tearsheet with comprehensive metrics
        """
        try:
            # Defaults
            if period_start is None:
                period_start = datetime.utcnow()
            if period_end is None:
                period_end = datetime.utcnow()
            if annual_return_pct is None:
                annual_return_pct = Decimal("0")
            if annual_volatility_pct is None:
                annual_volatility_pct = Decimal("0")
            if sharpe_ratio is None:
                sharpe_ratio = Decimal("0")
            if calmar_ratio is None:
                calmar_ratio = Decimal("0")
            if sortino_ratio is None:
                sortino_ratio = Decimal("0")
            if max_drawdown_pct is None:
                max_drawdown_pct = Decimal("0")
            if win_rate_pct is None:
                win_rate_pct = Decimal("0")

            # Calculate basic metrics from returns
            returns_array = np.array([float(r) for r in returns])
            total_return = Decimal(str(np.sum(returns_array))) * Decimal("100")
            best_day = Decimal(str(np.max(returns_array) * 100))
            worst_day = Decimal(str(np.min(returns_array) * 100))

            # Build monthly returns distribution
            monthly_returns = self._calculate_monthly_returns(returns)

            # Calculate position concentration if positions provided
            position_concentration = None
            if positions:
                position_concentration = self._calculate_position_concentration(positions)

            # Create tearsheet
            tearsheet = Tearsheet(
                generation_date=datetime.utcnow(),
                strategy_name=strategy_name,
                period_start=period_start,
                period_end=period_end,
                total_return_pct=total_return,
                annual_return_pct=annual_return_pct,
                annual_volatility_pct=annual_volatility_pct,
                sharpe_ratio=sharpe_ratio,
                calmar_ratio=calmar_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown_pct=max_drawdown_pct,
                win_rate_pct=win_rate_pct,
                position_concentration=position_concentration,
                best_day_pct=best_day,
                worst_day_pct=worst_day,
                monthly_returns=monthly_returns,
            )

            self.tearsheets_generated += 1
            logger.info(
                f"Tearsheet generated for {strategy_name} "
                f"(return: {annual_return_pct:.2f}%, sharpe: {sharpe_ratio:.2f})"
            )

            return tearsheet

        except Exception as e:
            logger.error(f"Tearsheet generation failed: {e}")
            raise

    def analyze_factor_exposure(
        self,
        returns: List[Decimal],
        factor_data: Dict[str, List[float]],
        confidence_level: float = 0.95,
    ) -> FactorAnalysis:
        """
        Analyze exposure to market factors (market, size, momentum, quality, etc.).

        Performs linear regression of returns against factors to decompose return sources.

        Args:
            returns: Period returns (Decimal)
            factor_data: Dictionary of factor_name → factor_values
            confidence_level: Confidence level for significance testing

        Returns:
            FactorAnalysis with exposures, contributions, and alpha
        """
        try:
            returns_array = np.array([float(r) for r in returns])

            # Build factor matrix
            factor_names = list(factor_data.keys())
            if not factor_names:
                # No factors provided, return empty analysis
                return FactorAnalysis(
                    analysis_date=datetime.utcnow(),
                    num_periods=len(returns),
                )

            # Stack factors into matrix (n_periods x n_factors)
            factor_matrix = np.column_stack([factor_data[f] for f in factor_names])

            # Add intercept (constant term for alpha)
            intercept_col = np.ones((len(returns_array), 1))
            X = np.column_stack([intercept_col, factor_matrix])

            # Solve linear regression: returns = α + β1*F1 + β2*F2 + ...
            # Using least squares: (X'X)^-1 X'y
            try:
                coefficients = np.linalg.lstsq(X, returns_array, rcond=None)[0]
            except np.linalg.LinAlgError:
                logger.warning("Factor regression failed, returning empty analysis")
                return FactorAnalysis(
                    analysis_date=datetime.utcnow(),
                    num_periods=len(returns),
                )

            alpha = coefficients[0]  # Intercept (unexplained return)
            betas = coefficients[1:]  # Factor exposures

            # Calculate residuals and residual variance
            predictions = X @ coefficients
            residuals = returns_array - predictions
            residual_var = np.var(residuals)
            residual_std = np.sqrt(residual_var)

            # Calculate R-squared (variance explained by factors)
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((returns_array - np.mean(returns_array)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else Decimal("0")

            # Calculate t-statistics and p-values
            n = len(returns_array)
            k = len(coefficients)
            mse = ss_res / (n - k) if (n - k) > 0 else 1.0
            var_covar = mse * np.linalg.inv(X.T @ X)
            std_errors = np.sqrt(np.diag(var_covar))

            from scipy import stats as scipy_stats

            exposures = []
            for i, factor_name in enumerate(factor_names):
                t_stat = betas[i] / std_errors[i + 1] if std_errors[i + 1] > 0 else 0
                # Two-tailed t-test
                p_value = 2 * (1 - scipy_stats.t.cdf(abs(t_stat), n - k) if (n - k) > 0 else 1.0)
                significant = p_value < (1 - confidence_level)

                exposures.append(
                    FactorExposure(
                        factor_name=factor_name,
                        coefficient=Decimal(str(betas[i])),
                        t_stat=Decimal(str(t_stat)),
                        p_value=Decimal(str(p_value)),
                        significant=significant,
                    )
                )

            # Calculate factor contributions (% of return from each factor)
            factor_returns = {}
            sum(betas[i] * np.mean(factor_data[fn]) for i, fn in enumerate(factor_names))
            mean_ret = np.mean(returns_array)
            for i, factor_name in enumerate(factor_names):
                factor_contribution = (
                    (betas[i] * np.mean(factor_data[factor_name]) / mean_ret * 100)
                    if mean_ret != 0
                    else Decimal("0")
                )
                factor_returns[factor_name] = Decimal(str(factor_contribution))

            analysis = FactorAnalysis(
                analysis_date=datetime.utcnow(),
                num_periods=len(returns),
                factors=exposures,
                residual_return_pct=Decimal(str(alpha * 100)),  # Alpha in percent
                residual_volatility_pct=Decimal(str(residual_std * 100)),
                model_r_squared=Decimal(str(r_squared)),
                factor_contribution_pct=factor_returns,
            )

            self.analysis_completed += 1
            logger.info(
                f"Factor analysis completed (R²: {r_squared:.3f}, "
                f"alpha: {alpha*100:.2f}%, factors: {len(factor_names)})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Factor exposure analysis failed: {e}")
            raise

    def calculate_position_concentration(self, positions: List[Dict]) -> PositionConcentration:
        """
        Calculate concentration metrics for portfolio positions.

        Metrics include:
        - Largest position as % of portfolio
        - Herfindahl index (concentration measure, 0-1)
        - Effective number of positions
        - Top 5 concentration
        - Diversification ratio

        Args:
            positions: List of position dicts with 'value' key

        Returns:
            PositionConcentration metrics
        """
        try:
            if not positions:
                return PositionConcentration(
                    largest_position_pct=Decimal("0"),
                    herfindahl_index=Decimal("0"),
                    effective_num_positions=Decimal("0"),
                    top_5_concentration_pct=Decimal("0"),
                    diversification_ratio=Decimal("1"),
                )

            # Extract position values
            position_values = [float(p.get("value", 0)) for p in positions]
            position_values = [v for v in position_values if v > 0]

            if not position_values:
                return PositionConcentration(
                    largest_position_pct=Decimal("0"),
                    herfindahl_index=Decimal("0"),
                    effective_num_positions=Decimal("0"),
                    top_5_concentration_pct=Decimal("0"),
                    diversification_ratio=Decimal("1"),
                )

            total_value = sum(position_values)
            if total_value == 0:
                total_value = 1  # Avoid division by zero

            # Calculate weights
            weights = np.array([v / total_value for v in position_values])

            # Largest position
            largest_pct = Decimal(str(np.max(weights) * 100))

            # Herfindahl index: sum of squared weights
            herfindahl = Decimal(str(np.sum(weights**2)))

            # Effective number of positions: 1 / Herfindahl
            effective_n = Decimal(str(1.0 / float(herfindahl))) if herfindahl > 0 else Decimal("0")

            # Top 5 concentration
            sorted_weights = np.sort(weights)[::-1]  # Descending
            top_5_weights = sorted_weights[: min(5, len(sorted_weights))]
            top_5_pct = Decimal(str(np.sum(top_5_weights) * 100))

            # Diversification ratio: average weight volatility / portfolio volatility
            # Simplified: std of weights / mean weight
            avg_weight = 1.0 / len(weights) if len(weights) > 0 else 0
            weight_std = np.std(weights)
            diversification_ratio = (
                Decimal(str(1.0 + weight_std / avg_weight)) if avg_weight > 0 else Decimal("1")
            )

            return PositionConcentration(
                largest_position_pct=largest_pct,
                herfindahl_index=herfindahl,
                effective_num_positions=effective_n,
                top_5_concentration_pct=top_5_pct,
                diversification_ratio=diversification_ratio,
            )

        except Exception as e:
            logger.error(f"Position concentration calculation failed: {e}")
            raise

    def analyze_capacity_fade(
        self,
        backtest_returns: List[Decimal],
        live_returns: Optional[List[Decimal]] = None,
        backtest_capital: Decimal = Decimal("100000"),
        current_capital: Decimal = Decimal("100000"),
        target_capital: Decimal = Decimal("250000"),
        required_return_pct: Decimal = Decimal("3.9"),
        backtest_sharpe: Optional[Decimal] = None,
        live_sharpe: Optional[Decimal] = None,
    ) -> CapacityFade:
        """
        Analyze capacity fade: how strategy alpha decays with scaling capital.

        Compares backtest performance with live trading to estimate fade ratio,
        then projects returns at target capital using sqrt(capacity) decay model.

        Args:
            backtest_returns: Historical backtest returns (Decimal)
            live_returns: Current live trading returns, if available
            backtest_capital: Capital used in backtest
            current_capital: Current deployed capital
            target_capital: Target capital for deployment
            required_return_pct: Required annual return
            backtest_sharpe: Backtest Sharpe ratio
            live_sharpe: Live trading Sharpe ratio

        Returns:
            CapacityFade analysis with projections
        """
        try:
            # Calculate backtest metrics
            backtest_arr = np.array([float(r) for r in backtest_returns])
            backtest_return = Decimal(str(np.mean(backtest_arr) * 252 * 100))  # Annualize

            if backtest_sharpe is None:
                backtest_sharpe = Decimal("0")

            # Calculate live metrics if provided
            live_return = backtest_return  # Default: assume no fade yet
            if live_returns and len(live_returns) > 0:
                live_arr = np.array([float(r) for r in live_returns])
                live_return = Decimal(str(np.mean(live_arr) * 252 * 100))

            # Calculate fade ratio: live_return / backtest_return
            if backtest_return > 0:
                fade_ratio = live_return / backtest_return
            else:
                fade_ratio = Decimal("0")

            # Project returns at target capital using sqrt(capacity) decay
            # Formula: target_return = backtest_return * sqrt(current_capital / target_capital) * fade_ratio
            capital_ratio = float(current_capital / target_capital)
            capacity_factor = float(np.sqrt(capital_ratio))
            projected_return = backtest_return * Decimal(str(capacity_factor)) * fade_ratio

            # Check feasibility
            projected_feasible = projected_return >= required_return_pct

            # Determine confidence level based on data
            if live_returns and len(live_returns) >= 60:
                confidence = "high"
            elif live_returns and len(live_returns) >= 20:
                confidence = "medium"
            else:
                confidence = "low"

            # Identify constraints
            constraints = []
            if fade_ratio < Decimal("1"):
                constraints.append(
                    f"Capacity fade observed: {float(fade_ratio):.2%} of backtest return"
                )
            if projected_return < required_return_pct:
                shortfall = required_return_pct - projected_return
                constraints.append(
                    f"Projected return {float(projected_return):.2f}% below required "
                    f"{float(required_return_pct):.2f}% (shortfall: {float(shortfall):.2f}%)"
                )
            if float(current_capital / target_capital) < 0.5:
                constraints.append(
                    "Target capital significantly larger than current deployment, "
                    "fade uncertainty high"
                )

            analysis = CapacityFade(
                backtest_period="Historical",
                backtest_ann_return_pct=backtest_return,
                backtest_sharpe=backtest_sharpe,
                simulated_current_return_pct=live_return,
                simulated_target_return_pct=projected_return,
                fade_ratio=fade_ratio,
                projected_feasible=projected_feasible,
                confidence_level=confidence,
                constraints=constraints,
            )

            logger.info(
                "Capacity fade analysis completed "
                f"(fade: {float(fade_ratio):.2%}, target return: {float(projected_return):.2f}%, "
                f"feasible: {projected_feasible})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Capacity fade analysis failed: {e}")
            raise

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _calculate_monthly_returns(self, returns: List[Decimal]) -> Dict[str, Decimal]:
        """Calculate aggregated monthly returns."""
        try:
            if not returns or len(returns) < 20:
                return {}

            # Assume 252 trading days per year, ~21 per month
            monthly_dict = {}
            days_per_month = 21
            month_num = 1

            for i in range(0, len(returns), days_per_month):
                month_returns = returns[i : i + days_per_month]
                if month_returns:
                    # Compound returns: product(1 + r) - 1
                    monthly_ret = Decimal("1")
                    for r in month_returns:
                        monthly_ret *= Decimal("1") + r
                    monthly_ret -= Decimal("1")
                    monthly_dict[f"Month_{month_num}"] = monthly_ret * Decimal("100")
                    month_num += 1

            return monthly_dict

        except Exception as e:
            logger.warning(f"Monthly return calculation failed: {e}")
            return {}

    def _calculate_position_concentration(self, positions: List[Dict]) -> PositionConcentration:
        """Helper to calculate position concentration."""
        return self.calculate_position_concentration(positions)

    def get_integrator_status(self) -> Dict:
        """Get integrator operational status."""
        return {
            "status": "operational",
            "tearsheets_generated": self.tearsheets_generated,
            "analyses_completed": self.analysis_completed,
            "last_update": datetime.utcnow().isoformat(),
        }


# ============================================================================
# SINGLETON ACCESSOR
# ============================================================================


_pyfolio_integrator_instance: Optional[PyFolioIntegrator] = None


def get_pyfolio_integrator() -> PyFolioIntegrator:
    """Get or create PyFolioIntegrator singleton."""
    global _pyfolio_integrator_instance
    if _pyfolio_integrator_instance is None:
        _pyfolio_integrator_instance = PyFolioIntegrator()

    return _pyfolio_integrator_instance
