# pylint: disable=non-ascii-name
"""Black-Litterman Portfolio Optimization Implementation.

This module implements the Black-Litterman model for portfolio optimization,
which combines market equilibrium returns with investor views to produce
more stable and intuitive portfolio allocations.

Key Features:
- Equilibrium returns from market capitalization weights (Rule 66)
- Combine equilibrium with investor views (P and Q matrices)
- Confidence parameter (tau) for view uncertainty
- Formula: E[R] = [(τΣ)^(-1) + P'Ω^(-1)P]^(-1) * [(τΣ)^(-1)Π + P'Ω^(-1)Q]
- Ledoit-Wolf shrinkage for covariance stability (Rule 74)
- Support for absolute and relative views
- Proper type hints using modern Python 3.10+ syntax

Reference:
    Black, F. and Litterman, R. (1992). "Global Portfolio Optimization".
    Financial Analysts Journal, 48(5), pp. 28-43.
    https://doi.org/10.2469/faj.v48.n5.28

Implementation based on:
    - The original Black-Litterman paper (1992)
    - Idzorek's method for view confidence
    - Walters' "The Black-Litterman Model in Detail" (2014)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


class ViewType(str, Enum):
    """Type of investor view."""

    ABSOLUTE = "absolute"  # "Asset A will return X%"
    RELATIVE = "relative"  # "Asset A will outperform Asset B by X%"


@dataclass(frozen=True)
class InvestorView:
    """Represents a single investor view on expected returns.

    An investor view expresses a belief about future returns, either:
    - Absolute: "Asset i will return μ%"
    - Relative: "Asset i will outperform Asset j by μ%"

    Attributes:
        view_type: Type of view (ABSOLUTE or RELATIVE)
        assets: Indices of assets involved in the view
        pick_vector: Picking vector P that maps view to assets
            - For absolute: [0, ..., 1, ..., 0] (1 at view asset index)
            - For relative: [0, ..., 1, ..., -1, ..., 0] (1 and -1 at asset indices)
        expected_return: Expected return Q for the view (annualized)
        confidence: Confidence level for the view (0.0 to 1.0)
            - 1.0 = 100% confident (view dominates equilibrium)
            - 0.0 = 0% confident (equilibrium dominates)
        id: Optional identifier for the view

    Example:
        >>> # Absolute view: Asset 0 will return 8%
        >>> absolute_view = InvestorView(
        ...     view_type=ViewType.ABSOLUTE,
        ...     assets=[0],
        ...     pick_vector=np.array([1, 0, 0, 0]),
        ...     expected_return=0.08,
        ...     confidence=0.75,
        ... )
        >>> # Relative view: Asset 0 will outperform Asset 1 by 3%
        >>> relative_view = InvestorView(
        ...     view_type=ViewType.RELATIVE,
        ...     assets=[0, 1],
        ...     pick_vector=np.array([1, -1, 0, 0]),
        ...     expected_return=0.03,
        ...     confidence=0.60,
        ... )
    """

    view_type: ViewType
    assets: list[int]
    pick_vector: NDArray[np.float64]
    expected_return: float
    confidence: float
    id: str | None = None

    def __post_init__(self) -> None:
        """Validate investor view parameters."""
        # Validate confidence range (0, 1) exclusive - representing partial certainty
        # 0 = no confidence, 1 = absolute certainty (both edge cases are problematic)
        if not 0.0 < self.confidence < 1.0:
            raise ValueError(
                f"Confidence must be in (0, 1), got {self.confidence}. "
                "View confidence represents the certainty in the expressed view. "
                "Use values strictly between 0 and 1 for partial confidence."
            )

        # Validate pick vector matches assets
        if len(self.pick_vector) != len(self.assets) and self.pick_vector.sum() not in [
            1.0,
            -1.0,
            0.0,
        ]:
            # For absolute views: pick_vector should sum to 1
            # For relative views: pick_vector should sum to 0
            if self.view_type == ViewType.ABSOLUTE:
                if not np.isclose(self.pick_vector.sum(), 1.0):
                    logger.warning(
                        f"Absolute view pick vector should sum to 1, got {self.pick_vector.sum()}"
                    )
            elif self.view_type == ViewType.RELATIVE:
                if not np.isclose(self.pick_vector.sum(), 0.0):
                    logger.warning(
                        f"Relative view pick vector should sum to 0, got {self.pick_vector.sum()}"
                    )


@dataclass
class BlackLittermanConfig:
    """Configuration for Black-Litterman optimization.

    Attributes:
        tau: Uncertainty parameter for equilibrium returns (default: 0.05)
            - Smaller tau = more confidence in equilibrium
            - Typical range: 0.01 to 0.10
            - Represents the ratio of uncertainty in the CAPM prior
        risk_aversion: Risk aversion coefficient (default: 3.0)
            - Higher = more conservative investor
            - Typical range: 2.0 to 4.0
        use_shrinkage: Whether to apply Ledoit-Wolf shrinkage (default: True)
        lookback_days: Days for covariance calculation (default: 252 per Rule 66)
        risk_free_rate: Risk-free rate for Sharpe calculation (default: 0.02)
        max_position: Maximum weight per asset for diversification (default: 0.20)
        omega_method: Method for calculating uncertainty matrix Ω
            - 'idzorek': Use confidence levels (Idzorek's method)
            - 'proportional': Ω proportional to P Σ P'
            - 'diagonal': Diagonal Ω based on asset variances
    """

    tau: float = 0.05
    risk_aversion: float = 3.0
    use_shrinkage: bool = True
    lookback_days: int = 252
    risk_free_rate: float = 0.02
    max_position: float = 0.20
    omega_method: str = "idzorek"

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.tau <= 0:
            raise ValueError(f"tau must be positive, got {self.tau}")

        if self.risk_aversion <= 0:
            raise ValueError(f"risk_aversion must be positive, got {self.risk_aversion}")

        if self.lookback_days < 252:
            raise ValueError(f"lookback_days must be >= 252 (Rule 66), got {self.lookback_days}")

        if not 0.0 < self.max_position <= 1.0:
            raise ValueError(
                f"max_position must be in (0, 1], got {self.max_position}. "
                "Rule 70: Max position constraint for diversification."
            )

        if self.omega_method not in ["idzorek", "proportional", "diagonal"]:
            raise ValueError(
                f"omega_method must be one of ['idzorek', 'proportional', 'diagonal'], "
                f"got {self.omega_method}"
            )


@dataclass(frozen=True)
class BlackLittermanResult:
    """Result of Black-Litterman portfolio optimization.

    Attributes:
        weights: Optimal portfolio weights (N,)
        equilibrium_returns: Market equilibrium returns Π (N,)
        bl_returns: Black-Litterman combined expected returns E[R] (N,)
        views: Investor views used in optimization
        posterior_covariance: Posterior covariance matrix (N, N)
        expected_return: Portfolio expected return (annualized)
        expected_risk: Portfolio expected risk (annualized)
        sharpe_ratio: Portfolio Sharpe ratio
        view_impact: Impact of each view on returns (optional)
        success: Whether optimization succeeded
        message: Status message
    """

    weights: NDArray[np.float64]
    equilibrium_returns: NDArray[np.float64]
    bl_returns: NDArray[np.float64]
    views: list[InvestorView]
    posterior_covariance: NDArray[np.float64]
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    view_impact: NDArray[np.float64] | None = None
    success: bool = True
    message: str = "Optimization successful"

    @property
    def weights_dict(self) -> dict[str, float]:
        """Convert weights array to dictionary format."""
        return {f"asset_{i}": float(w) for i, w in enumerate(self.weights)}

    def get_view_summary(self) -> list[dict[str, float | str | list[int]]]:
        """Get summary of views and their impacts."""
        summary = []
        for i, view in enumerate(self.views):
            view_dict: dict[str, float | str | list[int]] = {
                "view_id": view.id or f"view_{i}",
                "type": view.view_type.value,
                "expected_return": float(view.expected_return),
                "confidence": float(view.confidence),
                "assets": view.assets,
            }
            if self.view_impact is not None:
                view_dict["impact_on_returns"] = float(self.view_impact[i])
            summary.append(view_dict)
        return summary


class EquilibriumReturns:
    """Calculate market equilibrium returns (Implied Equilibrium Returns).

    The equilibrium returns Π represent the market's consensus expectation
    under CAPM assumptions. They are calculated from market capitalization
    weights and the covariance matrix.

    Formula:
        Π = λ * Σ * w_market

    Where:
        λ = risk_aversion coefficient
        Σ = covariance matrix
        w_market = market capitalization weights

    Reference:
        The equilibrium returns represent the returns that would make the
        market portfolio optimal under mean-variance optimization.
    """

    @staticmethod
    def from_market_caps(
        cov_matrix: NDArray[np.float64],
        market_caps: NDArray[np.float64],
        risk_aversion: float,
    ) -> NDArray[np.float64]:
        """Calculate equilibrium returns from market capitalizations.

        Args:
            cov_matrix: Covariance matrix (N, N), annualized
            market_caps: Market capitalizations for each asset (N,)
            risk_aversion: Risk aversion coefficient λ

        Returns:
            Equilibrium returns Π (N,), annualized

        Example:
            >>> cov = np.array([[0.01, 0.005], [0.005, 0.02]])
            >>> caps = np.array([1e12, 5e11])  # Asset 1 is 2x larger
            >>> pi = EquilibriumReturns.from_market_caps(cov, caps, risk_aversion=3.0)
        """
        # Normalize market caps to get market weights
        total_market_cap = market_caps.sum()
        market_weights = market_caps / total_market_cap

        # Calculate equilibrium returns: Π = λ * Σ * w_market
        equilibrium_returns = risk_aversion * (cov_matrix @ market_weights)

        logger.info(
            f"Equilibrium returns calculated: "
            f"mean={equilibrium_returns.mean():.4f}, "
            f"std={equilibrium_returns.std():.4f}"
        )

        return equilibrium_returns

    @staticmethod
    def from_weights(
        cov_matrix: NDArray[np.float64],
        market_weights: NDArray[np.float64],
        risk_aversion: float,
    ) -> NDArray[np.float64]:
        """Calculate equilibrium returns from market weights.

        This is an alternative method when market capitalizations are
        not directly available, but market weights are known.

        Args:
            cov_matrix: Covariance matrix (N, N), annualized
            market_weights: Market capitalization weights (N,), must sum to 1
            risk_aversion: Risk aversion coefficient λ

        Returns:
            Equilibrium returns Π (N,), annualized

        Raises:
            ValueError: If weights don't sum to 1 (within tolerance)
        """
        # Validate weights sum to 1
        if not np.isclose(market_weights.sum(), 1.0, atol=1e-6):
            raise ValueError(
                f"Market weights must sum to 1, got {market_weights.sum()}. "
                "Equilibrium calculation requires properly normalized weights."
            )

        # Calculate equilibrium returns: Π = λ * Σ * w_market
        equilibrium_returns = risk_aversion * (cov_matrix @ market_weights)

        logger.info(
            f"Equilibrium returns from weights: "
            f"mean={equilibrium_returns.mean():.4f}, "
            f"std={equilibrium_returns.std():.4f}"
        )

        return equilibrium_returns


class ViewMatrix:
    """Build P and Q matrices for investor views.

    The Black-Litterman model uses:
    - P matrix (Pick matrix): Maps views to assets (K x N)
    - Q vector: Expected returns for each view (K,)

    Where K is the number of views.
    """

    @staticmethod
    def build_pick_matrix(views: list[InvestorView], n_assets: int) -> NDArray[np.float64]:
        """Build the P (Pick) matrix from investor views.

        Each row of P represents one view's exposure to assets.

        Args:
            views: List of investor views
            n_assets: Total number of assets in the universe

        Returns:
            Pick matrix P of shape (K, N) where K = len(views)

        Example:
            >>> views = [
            ...     InvestorView(ViewType.ABSOLUTE, [0], np.array([1]), 0.08, 0.7),
            ...     InvestorView(ViewType.RELATIVE, [0, 1], np.array([1, -1]), 0.03, 0.6),
            ... ]
            >>> P = ViewMatrix.build_pick_matrix(views, n_assets=4)
            >>> # P will be shape (2, 4):
            >>> # [[1, 0, 0, 0],      # Absolute view on asset 0
            >>> #  [1, -1, 0, 0]]     # Relative view: asset 0 - asset 1
        """
        if not views:
            raise ValueError("Cannot build P matrix from empty views list")

        n_views = len(views)
        P = np.zeros((n_views, n_assets), dtype=np.float64)

        for i, view in enumerate(views):
            # Validate pick vector length matches n_assets
            if len(view.pick_vector) != n_assets:
                raise ValueError(
                    f"View {i} pick_vector length {len(view.pick_vector)} "
                    f"does not match n_assets {n_assets}"
                )
            P[i, :] = view.pick_vector

        logger.info(f"Built P matrix: shape={P.shape}, {n_views} views, {n_assets} assets")

        return P

    @staticmethod
    def build_q_vector(views: list[InvestorView]) -> NDArray[np.float64]:
        """Build the Q vector from investor views.

        Q contains the expected returns for each view.

        Args:
            views: List of investor views

        Returns:
            Q vector of shape (K,) where K = len(views)
        """
        if not views:
            raise ValueError("Cannot build Q vector from empty views list")

        Q = np.array([view.expected_return for view in views], dtype=np.float64)

        logger.info(
            f"Built Q vector: shape={Q.shape}, "
            f"mean={Q.mean():.4f}, range=[{Q.min():.4f}, {Q.max():.4f}]"
        )

        return Q

    @staticmethod
    def build_omega_matrix(
        P: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
        views: list[InvestorView],
        tau: float,
        method: str = "idzorek",
    ) -> NDArray[np.float64]:
        """Build the Ω (uncertainty) matrix for investor views.

        Ω represents the uncertainty in investor views. Different methods:

        1. 'idzorek' (default): Use confidence levels from views
           Ω_ii = (1/confidence - 1) * P_i Σ P_i'

        2. 'proportional': Ω proportional to P Σ P'
           Ω = tau * P Σ P'

        3. 'diagonal': Diagonal matrix based on asset variances

        Args:
            P: Pick matrix (K, N)
            cov_matrix: Covariance matrix (N, N)
            views: List of investor views (for confidence levels)
            tau: Uncertainty parameter
            method: Method for calculating Ω

        Returns:
            Uncertainty matrix Ω (K, K), diagonal
        """
        n_views = P.shape[0]

        if method == "idzorek":
            # Idzorek's method: Use confidence levels
            Ω = np.zeros((n_views, n_views), dtype=np.float64)

            for i, view in enumerate(views):
                # Formula: Ω_ii = (1/c - 1) * P_i Σ P_i'
                P_i = P[i, :].reshape(1, -1)
                variance = float((P_i @ cov_matrix @ P_i.T).item())
                omega_ii = (1.0 / view.confidence - 1.0) * variance

                Ω[i, i] = omega_ii

        elif method == "proportional":
            # Ω proportional to P Σ P'
            Ω = tau * (P @ cov_matrix @ P.T)

        elif method == "diagonal":
            # Diagonal based on asset variances
            Ω = np.zeros((n_views, n_views), dtype=np.float64)
            for i in range(n_views):
                # Variance of the view portfolio
                P_i = P[i, :].reshape(1, -1)
                variance = float((P_i @ cov_matrix @ P_i.T).item())
                Ω[i, i] = variance

        else:
            raise ValueError(f"Unknown omega_method: {method}")

        logger.info(
            f"Built Ω matrix: method={method}, shape={Ω.shape}, "
            f"diag_mean={Ω.diagonal().mean():.6f}"
        )

        return Ω


class BlackLittermanOptimizer:
    """Black-Litterman Portfolio Optimizer.

    The Black-Litterman model combines market equilibrium returns with
    investor views to produce more stable and intuitive portfolio allocations.

    Core Formula:
        E[R] = [(τΣ)^(-1) + P'Ω^(-1)P]^(-1) * [(τΣ)^(-1)Π + P'Ω^(-1)Q]

    Where:
        E[R] = Combined expected returns
        τ = Uncertainty parameter (tau)
        Σ = Covariance matrix
        Π = Equilibrium returns
        P = Pick matrix (maps views to assets)
        Q = View returns
        Ω = View uncertainty matrix

    Example:
        >>> optimizer = BlackLittermanOptimizer()
        >>> returns = np.random.randn(252, 5) * 0.01  # 252 days, 5 assets
        >>> market_caps = np.array([1e12, 8e11, 6e11, 4e11, 2e11])
        >>>
        >>> # Define views
        >>> views = [
        ...     InvestorView(ViewType.ABSOLUTE, [0], np.array([1,0,0,0,0]), 0.08, 0.7),
        ...     InvestorView(ViewType.RELATIVE, [0,1], np.array([1,-1,0,0,0]), 0.03, 0.6),
        ... ]
        >>>
        >>> result = optimizer.optimize(returns, market_caps, views)
        >>> print(f"Weights: {result.weights}")
        >>> print(f"BL Returns: {result.bl_returns}")
    """

    def __init__(self, config: BlackLittermanConfig | None = None) -> None:
        """Initialize Black-Litterman optimizer.

        Args:
            config: Configuration. If None, uses defaults.
        """
        self.config = config or BlackLittermanConfig()

        logger.info(
            f"Initialized BlackLittermanOptimizer: "
            f"tau={self.config.tau}, "
            f"risk_aversion={self.config.risk_aversion}, "
            f"lookback={self.config.lookback_days}"
        )

    def calculate_covariance_matrix(
        self,
        returns: NDArray[np.float64],
        use_shrinkage: bool | None = None,
    ) -> NDArray[np.float64]:
        """Calculate covariance matrix with 252-day lookback (Rule 66).

        Args:
            returns: Historical returns (T, N) where T >= lookback_days
            use_shrinkage: Whether to apply shrinkage (default: from config)

        Returns:
            Covariance matrix (N, N), annualized

        Raises:
            ValueError: If insufficient data
        """
        if use_shrinkage is None:
            use_shrinkage = self.config.use_shrinkage

        n_periods, n_assets = returns.shape

        if n_periods < self.config.lookback_days:
            raise ValueError(
                f"Insufficient data: {n_periods} periods < {self.config.lookback_days} "
                f"required (Rule 66)"
            )

        # Use most recent lookback_days
        recent_returns = returns[-self.config.lookback_days :, :]

        if use_shrinkage:
            cov_matrix = self._shrink_covariance(recent_returns)
        else:
            # Sample covariance
            cov_matrix = np.asarray(
                np.cov(recent_returns, rowvar=False) * 252, dtype=np.float64
            )  # Annualize

        # Ensure positive semi-definite
        cov_matrix = self._ensure_psd(cov_matrix)

        logger.info(
            f"Covariance matrix: {n_assets} assets, "
            f"{self.config.lookback_days} days, shrinkage={use_shrinkage}"
        )

        return cov_matrix

    def _shrink_covariance(self, returns: NDArray[np.float64]) -> NDArray[np.float64]:
        """Apply Ledoit-Wolf shrinkage to covariance matrix (Rule 74)."""
        try:
            from sklearn.covariance import LedoitWolf

            lw = LedoitWolf()
            shrunk_cov = lw.fit(returns).covariance_ * 252  # Annualize
            shrinkage = lw.shrinkage_

            logger.info(f"Rule 74: Ledoit-Wolf shrinkage applied: {shrinkage:.2%}")

            return shrunk_cov

        except ImportError as e:
            logger.warning(
                f"scikit-learn not available, using sample covariance: {e}",
                exc_info=True,
            )
            return np.cov(returns, rowvar=False) * 252

    @staticmethod
    def _ensure_psd(cov_matrix: NDArray[np.float64]) -> NDArray[np.float64]:
        """Ensure covariance matrix is positive semi-definite."""
        # Symmetrize
        cov_matrix = (cov_matrix + cov_matrix.T) / 2

        # Eigen decomposition
        eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)

        # Clip negative eigenvalues
        eigenvalues = np.maximum(eigenvalues, 0)

        # Reconstruct
        return eigenvectors @ np.diag(eigenvalues) @ eigenvectors.T

    def calculate_equilibrium_returns(
        self,
        cov_matrix: NDArray[np.float64],
        market_caps: NDArray[np.float64] | None = None,
        market_weights: NDArray[np.float64] | None = None,
    ) -> NDArray[np.float64]:
        """Calculate equilibrium returns Π from market weights.

        Args:
            cov_matrix: Covariance matrix (N, N)
            market_caps: Market capitalizations (N,) [alternative to market_weights]
            market_weights: Market weights (N,) [alternative to market_caps]

        Returns:
            Equilibrium returns Π (N,)

        Raises:
            ValueError: If neither market_caps nor market_weights provided
        """
        if market_caps is not None:
            return EquilibriumReturns.from_market_caps(
                cov_matrix, market_caps, self.config.risk_aversion
            )
        elif market_weights is not None:
            return EquilibriumReturns.from_weights(
                cov_matrix, market_weights, self.config.risk_aversion
            )
        else:
            raise ValueError(
                "Either market_caps or market_weights must be provided "
                "to calculate equilibrium returns"
            )

    def calculate_bl_returns(
        self,
        equilibrium_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
        views: list[InvestorView],
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Calculate Black-Litterman combined expected returns.

        Implements the core BL formula:
            E[R] = M^(-1) * [(τΣ)^(-1)Π + P'Ω^(-1)Q]

        Where:
            M = (τΣ)^(-1) + P'Ω^(-1)P

        Args:
            equilibrium_returns: Market equilibrium returns Π (N,)
            cov_matrix: Covariance matrix Σ (N, N)
            views: List of investor views

        Returns:
            Tuple of (bl_returns, posterior_covariance):
                - bl_returns: Combined expected returns E[R] (N,)
                - posterior_covariance: Posterior covariance (N, N)
        """
        n_assets = len(equilibrium_returns)

        if not views:
            # No views: return equilibrium
            logger.info("No views provided, returning equilibrium returns")
            return equilibrium_returns, cov_matrix

        # Build matrices
        P = ViewMatrix.build_pick_matrix(views, n_assets)
        Q = ViewMatrix.build_q_vector(views)
        Ω = ViewMatrix.build_omega_matrix(
            P, cov_matrix, views, self.config.tau, self.config.omega_method
        )

        # Core BL calculation
        tau_Sigma = self.config.tau * cov_matrix
        tau_Sigma_inv = np.linalg.inv(tau_Sigma)

        # M = (τΣ)^(-1) + P'Ω^(-1)P
        Ω_inv = np.linalg.inv(Ω)
        M = tau_Sigma_inv + P.T @ Ω_inv @ P
        M_inv = np.linalg.inv(M)

        # E[R] = M^(-1) * [(τΣ)^(-1)Π + P'Ω^(-1)Q]
        prior_term = tau_Sigma_inv @ equilibrium_returns
        view_term = P.T @ Ω_inv @ Q
        bl_returns: NDArray[np.float64] = np.asarray(
            M_inv @ (prior_term + view_term), dtype=np.float64
        )

        # Posterior covariance
        posterior_covariance: NDArray[np.float64] = np.asarray(M_inv, dtype=np.float64)

        logger.info(
            f"BL returns calculated: mean={bl_returns.mean():.4f}, "
            f"std={bl_returns.std():.4f}, "
            f"equilibrium_mean={equilibrium_returns.mean():.4f}"
        )

        return bl_returns, posterior_covariance

    def optimize(
        self,
        returns: NDArray[np.float64],
        market_caps: NDArray[np.float64] | None = None,
        market_weights: NDArray[np.float64] | None = None,
        views: list[InvestorView] | None = None,
    ) -> BlackLittermanResult:
        """Run complete Black-Litterman optimization.

        This is the main entry point that performs:
        1. Covariance estimation with shrinkage
        2. Equilibrium return calculation
        3. View matrix construction
        4. BL return combination
        5. Mean-varariance optimization with BL returns

        Args:
            returns: Historical returns (T, N)
            market_caps: Market capitalizations (N,) [alternative to market_weights]
            market_weights: Market weights (N,) [alternative to market_caps]
            views: List of investor views (optional, can be empty)

        Returns:
            BlackLittermanResult with optimal weights and metrics

        Raises:
            ValueError: If inputs are invalid
        """
        try:
            # Step 1: Calculate covariance
            cov_matrix = self.calculate_covariance_matrix(returns)
            n_assets = cov_matrix.shape[0]

            # Step 2: Calculate equilibrium returns
            equilibrium_returns = self.calculate_equilibrium_returns(
                cov_matrix, market_caps, market_weights
            )

            # Step 3: Handle views
            views = views or []
            bl_returns, posterior_cov = self.calculate_bl_returns(
                equilibrium_returns, cov_matrix, views
            )

            # Step 4: Optimize with BL returns (max Sharpe)
            weights = self._max_sharpe_weights(bl_returns, posterior_cov)

            # Step 5: Calculate metrics
            portfolio_return = float(weights @ bl_returns)
            portfolio_risk = float(np.sqrt(weights @ posterior_cov @ weights))
            sharpe_ratio = (
                (portfolio_return - self.config.risk_free_rate) / portfolio_risk
                if portfolio_risk > 0
                else -np.inf
            )

            # Calculate view impact
            view_impact = (
                self._calculate_view_impact(equilibrium_returns, bl_returns, views, n_assets)
                if views
                else None
            )

            logger.info(
                f"BL Optimization complete: "
                f"return={portfolio_return:.4f}, "
                f"risk={portfolio_risk:.4f}, "
                f"sharpe={sharpe_ratio:.2f}"
            )

            return BlackLittermanResult(
                weights=weights,
                equilibrium_returns=equilibrium_returns,
                bl_returns=bl_returns,
                views=views,
                posterior_covariance=posterior_cov,
                expected_return=portfolio_return,
                expected_risk=portfolio_risk,
                sharpe_ratio=sharpe_ratio,
                view_impact=view_impact,
                success=True,
                message="Black-Litterman optimization successful",
            )

        except Exception as e:
            logger.error(
                f"Black-Litterman optimization failed: {e}",
                exc_info=True,
                extra={
                    "returns_shape": returns.shape if hasattr(returns, "shape") else None,
                    "n_views": len(views) if views else 0,
                },
            )
            # Return equal weights as fallback
            n_assets = returns.shape[1]
            equal_weights = np.ones(n_assets) / n_assets

            return BlackLittermanResult(
                weights=equal_weights,
                equilibrium_returns=np.zeros(n_assets),
                bl_returns=np.zeros(n_assets),
                views=views or [],
                posterior_covariance=np.eye(n_assets),
                expected_return=0.0,
                expected_risk=0.0,
                sharpe_ratio=0.0,
                success=False,
                message=f"Optimization failed: {str(e)}",
            )

    def _max_sharpe_weights(
        self,
        expected_returns: NDArray[np.float64],
        cov_matrix: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Calculate maximum Sharpe ratio weights (Rule 72)."""

        def negative_sharpe(weights: NDArray[np.float64]) -> float:
            """Negative Sharpe for minimization."""
            portfolio_return = float(weights @ expected_returns)
            portfolio_risk = float(np.sqrt(weights @ cov_matrix @ weights))

            if portfolio_risk < 1e-10:
                return -np.inf

            return -((portfolio_return - self.config.risk_free_rate) / portfolio_risk)

        n_assets = len(expected_returns)
        constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        bounds = [(0.0, self.config.max_position) for _ in range(n_assets)]
        x0 = np.ones(n_assets) / n_assets

        result = minimize(
            negative_sharpe,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 1000},
        )

        if result.success:
            return result.x
        else:
            logger.warning(f"Max Sharpe optimization failed: {result.message}")
            return x0

    def _calculate_view_impact(
        self,
        equilibrium_returns: NDArray[np.float64],
        bl_returns: NDArray[np.float64],
        views: list[InvestorView],
        n_assets: int,
    ) -> NDArray[np.float64]:
        """Calculate the impact of each view on returns.

        Measures how much each view shifts returns from equilibrium.
        """
        # Difference between BL and equilibrium
        diff = bl_returns - equilibrium_returns

        # For each view, calculate its contribution
        # Use the pick vectors to weight the impact
        impact = np.zeros(len(views))

        for i, view in enumerate(views):
            # Weight the return difference by the view's pick vector
            P_i = view.pick_vector
            impact[i] = float(np.abs(P_i @ diff))

        return impact


def compute_black_litterman_weights(
    returns: NDArray[np.float64],
    market_caps: NDArray[np.float64],
    views: list[InvestorView],
    tau: float = 0.05,
    risk_aversion: float = 3.0,
    max_position: float = 0.20,
) -> NDArray[np.float64]:
    """Convenience function for Black-Litterman optimization.

    Args:
        returns: Historical returns (T, N)
        market_caps: Market capitalizations (N,)
        views: List of investor views
        tau: Uncertainty parameter (default: 0.05)
        risk_aversion: Risk aversion coefficient (default: 3.0)
        max_position: Maximum weight per asset (default: 0.20)

    Returns:
        Optimal weights (N,)

    Example:
        >>> weights = compute_black_litterman_weights(
        ...     returns=returns_data,
        ...     market_caps=caps_data,
        ...     views=[view1, view2],
        ... )
    """
    config = BlackLittermanConfig(tau=tau, risk_aversion=risk_aversion, max_position=max_position)
    optimizer = BlackLittermanOptimizer(config)
    result = optimizer.optimize(returns, market_caps=market_caps, views=views)

    return result.weights
