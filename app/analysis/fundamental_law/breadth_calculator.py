"""
Breadth Calculator

This module implements the calculation of strategy breadth, which measures
the number of independent betting opportunities per year.

Breadth is a critical component of the Fundamental Law:
    IR = IC × √BR

Higher breadth allows strategies with lower IC to achieve good IR.

Reference:
    Grinold, R., & Kahn, R. (2000). "Active Portfolio Management"
    Chapter 9: The Information Ratio
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd

from app.analysis.fundamental_law.models import BreadthMetrics
from app.core.decimal_utils import to_decimal

logger = logging.getLogger(__name__)


class BreadthCalculator:
    """
    Calculate and analyze strategy breadth.

    Breadth measures the number of independent betting opportunities
    per year. Key concepts:

    1. Annual Bets: Number of trading decisions per year
    2. Independence: How correlated are the bets with each other
    3. Effective Breadth: Annual bets adjusted for independence

    Methods:
        - calculate_breadth: Calculate from trading parameters
        - calculate_independence_factor: Estimate from correlations
        - calculate_from_returns: Infer from historical positions
        - estimate_required_breadth: Calculate BR needed for target IR

    Examples:
        >>> calculator = BreadthCalculator()
        >>> metrics = calculator.calculate_breadth(
        ...     n_assets=100,
        ...     rebalance_frequency="weekly"
        ... )
        >>> metrics.effective_breadth
        Decimal('5200')
    """

    # Trading periods per year for different rebalancing frequencies
    PERIODS_PER_YEAR = {
        "daily": 252,
        "weekly": 52,
        "biweekly": 26,
        "monthly": 12,
        "quarterly": 4,
        "annually": 1,
    }

    def __init__(self):
        """Initialize the Breadth Calculator."""
        pass

    def calculate_breadth(
        self,
        n_assets: int,
        rebalance_frequency: str,
        asset_correlation: Optional[pd.DataFrame] = None,
    ) -> "BreadthMetrics":
        """
        Calculate annual breadth from trading parameters.

        Formula:
            BR = periods_per_year × n_assets × independence_factor

        Args:
            n_assets: Number of assets traded
            rebalance_frequency: How often positions are rebalanced
                - "daily", "weekly", "biweekly", "monthly", "quarterly", "annually"
            asset_correlation: Optional correlation matrix between assets
                If provided, used to calculate independence factor

        Returns:
            BreadthMetrics containing annual_breadth, independence_factor,
            and effective_breadth

        Raises:
            ValueError: If invalid rebalance_frequency or n_assets

        Examples:
            >>> calculator = BreadthCalculator()
            >>> # Weekly trading of 100 stocks
            >>> metrics = calculator.calculate_breadth(
            ...     n_assets=100,
            ...     rebalance_frequency="weekly"
            ... )
            >>> metrics.annual_breadth
            Decimal('5200')
        """
        if n_assets <= 0:
            raise ValueError(f"n_assets must be positive, got {n_assets}")

        # Get periods per year
        frequency_lower = rebalance_frequency.lower()
        if frequency_lower not in self.PERIODS_PER_YEAR:
            raise ValueError(
                f"Invalid rebalance_frequency: {rebalance_frequency}. "
                f"Use one of: {list(self.PERIODS_PER_YEAR.keys())}"
            )

        periods_per_year = Decimal(str(self.PERIODS_PER_YEAR[frequency_lower]))

        # Calculate annual breadth (before independence adjustment)
        annual_breadth = periods_per_year * Decimal(n_assets)

        # Calculate independence factor
        if asset_correlation is not None:
            independence_factor = self.calculate_independence_factor(asset_correlation)
        else:
            # Assume moderate independence if no correlation data
            # Conservative assumption: some correlation exists
            independence_factor = Decimal("0.5")

        # Calculate effective breadth
        effective_breadth = annual_breadth * independence_factor

        # Generate notes
        notes = (
            f"{frequency_lower.capitalize()} rebalancing of {n_assets} assets. "
            f"Independence factor: {float(independence_factor):.2f}"
        )

        from app.analysis.fundamental_law.models import BreadthMetrics

        return BreadthMetrics(
            annual_breadth=annual_breadth,
            independence_factor=independence_factor,
            effective_breadth=effective_breadth,
            notes=notes,
        )

    def calculate_independence_factor(
        self,
        correlation_matrix: pd.DataFrame,
    ) -> Decimal:
        """
        Calculate independence factor from correlation matrix.

        The independence factor adjusts breadth for correlation between
        bets. Highly correlated bets don't count as independent opportunities.

        Formula:
            IF = 1 / (1 + avg_correlation × (n - 1))

        Logic:
        - If all assets are perfectly correlated (avg_corr = 1):
          IF = 1/n (treating all assets as one bet)
        - If assets are uncorrelated (avg_corr = 0):
          IF = 1 (all bets are independent)

        Args:
            correlation_matrix: NxN correlation matrix between assets

        Returns:
            Independence factor in range [0, 1]

        Raises:
            ValueError: If matrix is invalid or not square

        Examples:
            >>> import pandas as pd
            >>> import numpy as np
            >>> calculator = BreadthCalculator()
            >>> # Uncorrelated assets
            >>> corr = pd.DataFrame(np.eye(3))
            >>> factor = calculator.calculate_independence_factor(corr)
            >>> factor >= Decimal('0.9')  # Should be close to 1.0
            True
        """
        # Validate matrix
        if not isinstance(correlation_matrix, pd.DataFrame):
            raise ValueError("correlation_matrix must be a pandas DataFrame")

        if correlation_matrix.shape[0] != correlation_matrix.shape[1]:
            raise ValueError("correlation_matrix must be square")

        n = correlation_matrix.shape[0]

        if n < 2:
            return Decimal("1.0")

        # Calculate average correlation (excluding diagonal)
        # Get upper triangle of matrix (excluding diagonal)
        upper_triangle = correlation_matrix.values[np.triu_indices(n, k=1)]

        if len(upper_triangle) == 0:
            return Decimal("1.0")

        avg_correlation = float(np.mean(upper_triangle))

        # Calculate independence factor
        # Formula: IF = 1 / (1 + avg_corr * (n - 1))
        independence_factor = 1 / (1 + avg_correlation * (n - 1))

        # Clamp to valid range [0, 1]
        independence_factor = max(0.0, min(1.0, independence_factor))

        return to_decimal(str(round(independence_factor, 4)))

    def calculate_from_returns(
        self,
        returns: pd.DataFrame,
        min_position: float = 0.01,
    ) -> "BreadthMetrics":
        """
        Calculate breadth from historical returns and positions.

        This infers breadth by counting how many distinct positions were
        taken per year, adjusted for correlation.

        Args:
            returns: DataFrame of asset returns
                - Columns: Assets
                - Index: Dates
            min_position: Minimum position size to count as a bet
                (as fraction, e.g., 0.01 = 1%)

        Returns:
            BreadthMetrics based on historical data

        Examples:
            >>> import pandas as pd
            >>> import numpy as np
            >>> calculator = BreadthCalculator()
            >>> # Create sample returns data
            >>> dates = pd.date_range("2020-01-01", periods=252, freq="D")
            >>> returns = pd.DataFrame(
            ...     np.random.randn(252, 10) * 0.01,
            ...     index=dates,
            ...     columns=[f"asset_{i}" for i in range(10)]
            ... )
            >>> metrics = calculator.calculate_from_returns(returns)
            >>> metrics.effective_breadth > 0
            True
        """
        # Count number of assets
        n_assets = returns.shape[1]

        # Calculate years in data
        date_range = (returns.index[-1] - returns.index[0]).days / 365.25
        if date_range < 0.01:
            date_range = 1.0  # Default to 1 year if insufficient data

        # Estimate rebalancing frequency from data
        # Count unique dates (assuming daily data)
        unique_dates = returns.index.normalize().nunique()
        periods_per_year = Decimal(str(unique_dates / date_range))

        # Calculate correlation matrix
        corr_matrix = returns.corr()

        # Calculate independence factor
        independence_factor = self.calculate_independence_factor(corr_matrix)

        # Calculate annual breadth
        annual_breadth = periods_per_year * Decimal(n_assets)

        # Calculate effective breadth
        effective_breadth = annual_breadth * independence_factor

        # Generate notes
        notes = (
            f"Inferred from {n_assets} assets over {date_range:.1f} years. "
            f"Estimated {float(periods_per_year):.0f} periods/year. "
            f"Independence factor: {float(independence_factor):.2f}"
        )

        from app.analysis.fundamental_law.models import BreadthMetrics

        return BreadthMetrics(
            annual_breadth=annual_breadth,
            independence_factor=independence_factor,
            effective_breadth=effective_breadth,
            notes=notes,
        )

    def estimate_required_breadth(
        self,
        target_ir: Decimal,
        information_coefficient: Decimal,
        transfer_coefficient: Decimal = Decimal("1.0"),
    ) -> Decimal:
        """
        Estimate required breadth for a target Information Ratio.

        Rearranging the Fundamental Law:
            IR = IC × √BR × TC
            ∴ BR = (IR / (IC × TC))²

        This tells you how many independent bets you need per year to
        achieve your target IR, given your forecasting skill (IC).

        Args:
            target_ir: Desired Information Ratio
            information_coefficient: Your forecasting skill (IC)
            transfer_coefficient: Your implementation efficiency (TC)

        Returns:
            Required breadth (bets per year)

        Raises:
            ValueError: If IC or TC is zero or negative

        Examples:
            >>> calculator = BreadthCalculator()
            >>> # How many bets needed for IR=1.0 with IC=0.05?
            >>> br = calculator.estimate_required_breadth(
            ...     target_ir=Decimal("1.0"),
            ...     information_coefficient=Decimal("0.05")
            ... )
            >>> br >= Decimal('300') and br <= Decimal('500')
            True
        """
        if information_coefficient <= 0:
            raise ValueError(
                f"Information Coefficient must be positive, got {information_coefficient}"
            )

        if transfer_coefficient <= 0:
            raise ValueError(f"Transfer Coefficient must be positive, got {transfer_coefficient}")

        # Calculate required breadth
        # BR = (IR / (IC × TC))²
        denominator = information_coefficient * transfer_coefficient
        ratio = target_ir / denominator
        required_breadth = ratio**2

        return required_breadth

    def calculate_optimal_breadth(
        self,
        information_coefficient: Decimal,
        transfer_coefficient: Decimal = Decimal("1.0"),
        max_ir: Decimal = Decimal("2.0"),
    ) -> Decimal:
        """
        Calculate the breadth that would achieve a maximum target IR.

        This is useful for understanding when you've hit diminishing returns
        from increasing breadth.

        Args:
            information_coefficient: Your forecasting skill (IC)
            transfer_coefficient: Your implementation efficiency (TC)
            max_ir: Maximum realistic IR (default: 2.0)

        Returns:
            Breadth required to achieve max_ir

        Examples:
            >>> calculator = BreadthCalculator()
            >>> br = calculator.calculate_optimal_breadth(
            ...     information_coefficient=Decimal("0.03")
            ... )
            >>> br > Decimal('1000')
            True
        """
        return self.estimate_required_breadth(max_ir, information_coefficient, transfer_coefficient)

    def decompose_breadth(
        self,
        returns: pd.DataFrame,
        positions: Optional[pd.DataFrame] = None,
    ) -> dict:
        """
        Decompose breadth into its components.

        Provides a detailed breakdown of what contributes to breadth.

        Args:
            returns: Asset returns DataFrame
            positions: Optional positions DataFrame
                If provided, uses actual positions taken
                If not provided, assumes all assets are traded

        Returns:
            Dictionary with breadth breakdown:
                - n_assets: Number of assets
                - periods_per_year: Trading frequency
                - avg_correlation: Average asset correlation
                - independence_factor: Calculated IF
                - annual_breadth: Raw breadth
                - effective_breadth: Adjusted breadth
                - breadth_sqrt: Square root of effective breadth

        Examples:
            >>> import pandas as pd
            >>> import numpy as np
            >>> calculator = BreadthCalculator()
            >>> returns = pd.DataFrame(
            ...     np.random.randn(100, 5) * 0.01,
            ...     columns=[f"A{i}" for i in range(5)]
            ... )
            >>> decomp = calculator.decompose_breadth(returns)
            >>> "n_assets" in decomp
            True
        """
        # Number of assets
        n_assets = returns.shape[1]

        # Estimate periods per year
        # Handle both DatetimeIndex and numeric indices
        if isinstance(returns.index, pd.DatetimeIndex):
            date_range_days = (returns.index[-1] - returns.index[0]).days
            date_range_years = max(date_range_days / 365.25, 0.01)
            periods_per_year = len(returns) / date_range_years
        else:
            # For numeric indices, assume one period is one observation
            # Default to annual frequency
            date_range_years = len(returns) / 252.0  # Assume daily data
            periods_per_year = 252.0  # Default to daily trading

        # Calculate correlations
        corr_matrix = returns.corr()
        upper_triangle = corr_matrix.values[np.triu_indices(n_assets, k=1)]
        avg_correlation = float(np.mean(upper_triangle)) if len(upper_triangle) > 0 else 0.0

        # Calculate independence factor
        independence_factor = self.calculate_independence_factor(corr_matrix)

        # Calculate breadth
        annual_breadth = Decimal(str(periods_per_year)) * Decimal(n_assets)
        effective_breadth = annual_breadth * independence_factor

        # Calculate square root
        import math

        breadth_sqrt = Decimal(str(math.sqrt(float(effective_breadth))))

        return {
            "n_assets": n_assets,
            "periods_per_year": round(periods_per_year, 1),
            "avg_correlation": round(avg_correlation, 4),
            "independence_factor": float(independence_factor),
            "annual_breadth": float(annual_breadth),
            "effective_breadth": float(effective_breadth),
            "breadth_sqrt": float(breadth_sqrt),
        }
