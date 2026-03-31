"""
Regularization Techniques for Statistical Learning.

This module implements comprehensive regularization methods following
Hastie, Tibshirani, and Friedman's "The Elements of Statistical Learning"
(ESL) Chapter 3: Linear Methods for Regression and Chapter 11: Regularization.

Key Techniques:
1. L1 Regularization (Lasso) - Sparse solutions, feature selection
2. L2 Regularization (Ridge) - Shrinkage, multicollinearity handling
3. Elastic Net - Combination of L1 and L2
4. Adaptive Lasso - Weighted L1 penalty
5. Group Lasso - Structured sparsity
6. Regularization path tracking

Reference:
    "The Elements of Statistical Learning" by Hastie, Tibshirani, Friedman
    Chapter 3: Linear Methods for Regression
    Chapter 11: Regularization and Reproducing Kernel Hilbert Spaces
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import ElasticNet, Lasso, LassoCV, Ridge, RidgeCV
from sklearn.utils.validation import check_array, check_is_fitted

logger = logging.getLogger(__name__)


class RegularizationType(Enum):
    """Types of regularization."""

    L1 = "l1"  # Lasso
    L2 = "l2"  # Ridge
    ELASTIC_NET = "elastic_net"  # L1 + L2
    ADAPTIVE_LASSO = "adaptive_lasso"
    GROUP_LASSO = "group_lasso"
    NONE = "none"


@dataclass
class RegularizationResult:
    """Results from regularization analysis."""

    timestamp: datetime
    regularization_type: RegularizationType
    alpha: float
    l1_ratio: float  # For Elastic Net (0 = Ridge, 1 = Lasso)
    n_features: int
    n_nonzero_features: int
    sparsity_ratio: float

    # Model coefficients
    coefficients: np.ndarray
    intercept: float

    # Performance metrics
    train_score: float
    test_score: float
    explained_variance: float

    # Feature importance
    feature_importance: dict[str, float] = field(default_factory=dict)

    # Convergence info
    n_iterations: int = 0
    converged: bool = True

    # Additional info
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "regularization_type": self.regularization_type.value,
            "alpha": self.alpha,
            "l1_ratio": self.l1_ratio,
            "n_features": self.n_features,
            "n_nonzero_features": self.n_nonzero_features,
            "sparsity_ratio": self.sparsity_ratio,
            "coefficients": self.coefficients.tolist(),
            "intercept": float(self.intercept),
            "train_score": self.train_score,
            "test_score": self.test_score,
            "explained_variance": self.explained_variance,
            "feature_importance": self.feature_importance,
            "n_iterations": self.n_iterations,
            "converged": self.converged,
            "details": self.details,
        }


@dataclass
class RegularizationPathPoint:
    """Single point on regularization path."""

    alpha: float
    coefficients: np.ndarray
    n_nonzero: int
    score: float


@dataclass
class RegularizationPath:
    """Regularization path analysis."""

    timestamp: datetime
    regularization_type: RegularizationType
    path_points: list[RegularizationPathPoint]
    feature_names: list[str]

    # Optimal point
    optimal_alpha: float
    optimal_score: float
    optimal_n_nonzero: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "regularization_type": self.regularization_type.value,
            "path_points": [
                {
                    "alpha": p.alpha,
                    "coefficients": p.coefficients.tolist(),
                    "n_nonzero": p.n_nonzero,
                    "score": p.score,
                }
                for p in self.path_points
            ],
            "feature_names": self.feature_names,
            "optimal_alpha": self.optimal_alpha,
            "optimal_score": self.optimal_score,
            "optimal_n_nonzero": self.optimal_n_nonzero,
        }


class L1Regularization:
    """
    L1 Regularization (Lasso).

    Implements Lasso regression as described in ESL Section 3.4.2.
    L1 penalty encourages sparse solutions, effectively performing
    feature selection.

    Optimization: min ||y - Xbeta||^2 + lambda||beta||₁

    Properties:
    - Sparse solutions (many coefficients = 0)
    - Feature selection capability
    - Convex optimization problem
    - Unique solution for orthogonal predictors

    Advantages:
    - Automatic feature selection
    - Interpretable models
    - Handles multicollinearity by selecting one feature

    Disadvantages:
    - Selects at most n features (n = sample size)
    - Can be unstable with correlated features
    - No closed-form solution
    """

    def __init__(
        self,
        alpha: float = 1.0,
        fit_intercept: bool = True,
        max_iter: int = 1000,
        tol: float = 1e-4,
        random_state: int | None = None,
    ):
        """
        Initialize L1 Regularization.

        Args:
            alpha: Regularization strength (lambda)
            fit_intercept: Whether to fit intercept
            max_iter: Maximum iterations
            tol: Tolerance for convergence
            random_state: Random seed
        """
        self.alpha = alpha
        self.fit_intercept = fit_intercept
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state

    def fit(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        sample_weight: np.ndarray | None = None,
    ) -> L1Regularization:
        """
        Fit Lasso regression.

        Args:
            X: Feature matrix
            y: Target vector
            sample_weight: Sample weights

        Returns:
            Self (fitted estimator)
        """
        # Convert to arrays
        X_array = check_array(X, accept_sparse=True)
        y_array = check_array(y, ensure_2d=False)

        # Initialize Lasso
        self.lasso_ = Lasso(
            alpha=self.alpha,
            fit_intercept=self.fit_intercept,
            max_iter=self.max_iter,
            tol=self.tol,
            random_state=self.random_state,
        )

        # Fit model
        self.lasso_.fit(X_array, y_array, sample_weight=sample_weight)

        return self

    def predict(self, X: np.ndarray | pd.DataFrame) -> np.ndarray:
        """
        Predict using fitted model.

        Args:
            X: Feature matrix

        Returns:
            Predictions
        """
        check_is_fitted(self, ["lasso_"])
        X_array = check_array(X, accept_sparse=True)
        return np.asarray(self.lasso_.predict(X_array))

    def score(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
    ) -> float:
        """
        Return R^2 score.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            R^2 score
        """
        check_is_fitted(self, ["lasso_"])
        return float(self.lasso_.score(X, y))

    def get_coefficients(self) -> np.ndarray:
        """Get model coefficients."""
        check_is_fitted(self, ["lasso_"])
        return np.asarray(self.lasso_.coef_)

    def get_intercept(self) -> float:
        """Get intercept."""
        check_is_fitted(self, ["lasso_"])
        return float(self.lasso_.intercept_)

    def get_sparsity_mask(self) -> np.ndarray:
        """Get boolean mask of non-zero coefficients."""
        return self.get_coefficients() != 0

    def get_selected_features(self) -> np.ndarray:
        """Get indices of selected features."""
        return np.where(self.get_sparsity_mask())[0]


class L2Regularization:
    """
    L2 Regularization (Ridge).

    Implements Ridge regression as described in ESL Section 3.4.1.
    L2 penalty shrinks coefficients towards zero but doesn't set them
    to exactly zero.

    Optimization: min ||y - Xbeta||^2 + lambda||beta||₂^2

    Properties:
    - Closed-form solution: beta = (X'X + lambdaI)⁻¹X'y
    - Shrinks coefficients proportionally
    - Handles multicollinearity well
    - Stable solution

    Advantages:
    - Closed-form solution
    - Numerically stable
    - Handles multicollinearity
    - All features retained

    Disadvantages:
    - No feature selection
    - Less interpretable than Lasso
    - All features contribute to prediction
    """

    def __init__(
        self,
        alpha: float = 1.0,
        fit_intercept: bool = True,
        solver: str = "auto",
        max_iter: int | None = None,
        tol: float = 1e-4,
    ):
        """
        Initialize L2 Regularization.

        Args:
            alpha: Regularization strength (lambda)
            fit_intercept: Whether to fit intercept
            solver: Solver to use ('auto', 'svd', 'cholesky', 'lsqr', etc.)
            max_iter: Maximum iterations (for iterative solvers)
            tol: Tolerance for convergence
        """
        self.alpha = alpha
        self.fit_intercept = fit_intercept
        self.solver = solver
        self.max_iter = max_iter
        self.tol = tol

    def fit(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        sample_weight: np.ndarray | None = None,
    ) -> L2Regularization:
        """
        Fit Ridge regression.

        Args:
            X: Feature matrix
            y: Target vector
            sample_weight: Sample weights

        Returns:
            Self (fitted estimator)
        """
        # Convert to arrays
        X_array = check_array(X, accept_sparse=True)
        y_array = check_array(y, ensure_2d=False)

        # Initialize Ridge
        self.ridge_ = Ridge(
            alpha=self.alpha,
            fit_intercept=self.fit_intercept,
            solver=self.solver,
            max_iter=self.max_iter,
            tol=self.tol,
        )

        # Fit model
        self.ridge_.fit(X_array, y_array, sample_weight=sample_weight)

        return self

    def predict(self, X: np.ndarray | pd.DataFrame) -> np.ndarray:
        """
        Predict using fitted model.

        Args:
            X: Feature matrix

        Returns:
            Predictions
        """
        check_is_fitted(self, ["ridge_"])
        X_array = check_array(X, accept_sparse=True)
        return np.asarray(self.ridge_.predict(X_array))

    def score(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
    ) -> float:
        """
        Return R^2 score.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            R^2 score
        """
        check_is_fitted(self, ["ridge_"])
        return float(self.ridge_.score(X, y))

    def get_coefficients(self) -> np.ndarray:
        """Get model coefficients."""
        check_is_fitted(self, ["ridge_"])
        return np.asarray(self.ridge_.coef_)

    def get_intercept(self) -> float:
        """Get intercept."""
        check_is_fitted(self, ["ridge_"])
        return float(self.ridge_.intercept_)


class ElasticNetRegularization:
    """
    Elastic Net Regularization.

    Implements Elastic Net as described in ESL Section 3.4.3.
    Combines L1 and L2 penalties to get benefits of both:
    - L1: Sparsity and feature selection
    - L2: Stability with correlated features

    Optimization: min ||y - Xbeta||^2 + lambda₁||beta||₁ + lambda₂||beta||₂^2

    Equivalent to: min ||y - Xbeta||^2 + lambda(alpha||beta||₁ + (1-alpha)||beta||₂^2)

    Properties:
    - Sparse solutions (like Lasso)
    - Groups correlated features (like Ridge)
    - More stable than Lasso alone

    Advantages:
    - Feature selection + grouping
    - Handles correlated features better than Lasso
    - Can select more than n features

    Disadvantages:
    - Two hyperparameters to tune (lambda, alpha)
    - No closed-form solution
    """

    def __init__(
        self,
        alpha: float = 1.0,
        l1_ratio: float = 0.5,
        fit_intercept: bool = True,
        max_iter: int = 1000,
        tol: float = 1e-4,
        random_state: int | None = None,
    ):
        """
        Initialize Elastic Net Regularization.

        Args:
            alpha: Overall regularization strength (lambda)
            l1_ratio: L1 mixing parameter (alpha in formula)
                     0 = Ridge, 1 = Lasso, 0.5 = equal mix
            fit_intercept: Whether to fit intercept
            max_iter: Maximum iterations
            tol: Tolerance for convergence
            random_state: Random seed
        """
        self.alpha = alpha
        self.l1_ratio = l1_ratio
        self.fit_intercept = fit_intercept
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state

    def fit(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        sample_weight: np.ndarray | None = None,
    ) -> ElasticNetRegularization:
        """
        Fit Elastic Net regression.

        Args:
            X: Feature matrix
            y: Target vector
            sample_weight: Sample weights

        Returns:
            Self (fitted estimator)
        """
        # Convert to arrays
        X_array = check_array(X, accept_sparse=True)
        y_array = check_array(y, ensure_2d=False)

        # Initialize Elastic Net
        self.enet_ = ElasticNet(
            alpha=self.alpha,
            l1_ratio=self.l1_ratio,
            fit_intercept=self.fit_intercept,
            max_iter=self.max_iter,
            tol=self.tol,
            random_state=self.random_state,
        )

        # Fit model
        self.enet_.fit(X_array, y_array, sample_weight=sample_weight)

        return self

    def predict(self, X: np.ndarray | pd.DataFrame) -> np.ndarray:
        """
        Predict using fitted model.

        Args:
            X: Feature matrix

        Returns:
            Predictions
        """
        check_is_fitted(self, ["enet_"])
        X_array = check_array(X, accept_sparse=True)
        return np.asarray(self.enet_.predict(X_array))

    def score(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
    ) -> float:
        """
        Return R^2 score.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            R^2 score
        """
        check_is_fitted(self, ["enet_"])
        return float(self.enet_.score(X, y))

    def get_coefficients(self) -> np.ndarray:
        """Get model coefficients."""
        check_is_fitted(self, ["enet_"])
        return np.asarray(self.enet_.coef_)

    def get_intercept(self) -> float:
        """Get intercept."""
        check_is_fitted(self, ["enet_"])
        return float(self.enet_.intercept_)

    def get_sparsity_mask(self) -> np.ndarray:
        """Get boolean mask of non-zero coefficients."""
        return self.get_coefficients() != 0


class AdaptiveLasso:
    """
    Adaptive Lasso.

    Implements Adaptive Lasso as described in ESL.
    Uses weights to penalize coefficients adaptively based on
    initial OLS estimates.

    Weighted penalty: lambda Sigma wⱼ|betaⱼ|

    Where weights wⱼ = 1/|betâⱼ|^gamma (betâ from OLS or Ridge)

    Properties:
    - Oracle properties (consistent and asymptotically normal)
    - Variable selection consistency
    - Weights based on initial estimates

    Advantages:
    - Better variable selection than standard Lasso
    - Oracle properties
    - Adaptively penalizes coefficients

    Disadvantages:
    - Two-stage procedure
    - Requires initial estimate
    """

    def __init__(
        self,
        alpha: float = 1.0,
        gamma: float = 1.0,
        max_iter: int = 1000,
        tol: float = 1e-4,
        random_state: int | None = None,
    ):
        """
        Initialize Adaptive Lasso.

        Args:
            alpha: Regularization strength
            gamma: Weighting exponent (typically 1 or 2)
            max_iter: Maximum iterations
            tol: Tolerance for convergence
            random_state: Random seed
        """
        self.alpha = alpha
        self.gamma = gamma
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state

    def fit(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
    ) -> AdaptiveLasso:
        """
        Fit Adaptive Lasso.

        Args:
            X: Feature matrix
            y: Target vector

        Returns:
            Self (fitted estimator)
        """
        # Convert to arrays
        X_array = check_array(X, accept_sparse=True)
        y_array = check_array(y, ensure_2d=False)

        # Stage 1: Get initial estimate (Ridge for stability)
        ridge_init = Ridge(alpha=0.1, fit_intercept=True)
        ridge_init.fit(X_array, y_array)
        initial_coef = ridge_init.coef_

        # Stage 2: Calculate weights
        weights = 1.0 / (np.abs(initial_coef) ** self.gamma + 1e-6)

        # Stage 3: Weighted Lasso
        # Use coordinate descent with weights
        self.lasso_ = Lasso(
            alpha=self.alpha,
            fit_intercept=True,
            max_iter=self.max_iter,
            tol=self.tol,
            random_state=self.random_state,
        )

        # Weighted features
        X_weighted = X_array / weights

        self.lasso_.fit(X_weighted, y_array)

        # Transform coefficients back
        self.coef_ = self.lasso_.coef_ / weights
        self.intercept_ = self.lasso_.intercept_
        self.weights_ = weights

        return self

    def predict(self, X: np.ndarray | pd.DataFrame) -> np.ndarray:
        """
        Predict using fitted model.

        Args:
            X: Feature matrix

        Returns:
            Predictions
        """
        check_is_fitted(self, ["coef_", "intercept_"])
        X_array = check_array(X, accept_sparse=True)
        return np.asarray(X_array @ self.coef_ + self.intercept_)

    def get_coefficients(self) -> np.ndarray:
        """Get model coefficients."""
        check_is_fitted(self, ["coef_"])
        return np.asarray(self.coef_)


class RegularizationAnalyzer:
    """
    Comprehensive regularization analysis.

    This class provides tools for analyzing and comparing different
    regularization methods following ESL best practices.
    """

    def __init__(
        self,
        cv_folds: int = 5,
        test_size: float = 0.2,
        random_state: int = 42,
    ):
        """
        Initialize analyzer.

        Args:
            cv_folds: Number of CV folds
            test_size: Test set size
            random_state: Random seed
        """
        self.cv_folds = cv_folds
        self.test_size = test_size
        self.random_state = random_state

    def analyze_l1_regularization(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        alpha: float = 1.0,
        feature_names: list[str] | None = None,
    ) -> RegularizationResult:
        """
        Analyze L1 regularization (Lasso).

        Args:
            X: Feature matrix
            y: Target vector
            alpha: Regularization strength
            feature_names: Feature names

        Returns:
            RegularizationResult with analysis
        """
        from sklearn.model_selection import train_test_split

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state
        )

        # Fit Lasso
        lasso = L1Regularization(alpha=alpha, random_state=self.random_state)
        lasso.fit(X_train, y_train)

        # Get coefficients
        coef = lasso.get_coefficients()
        intercept = lasso.get_intercept()

        # Scores
        train_score = lasso.score(X_train, y_train)
        test_score = lasso.score(X_test, y_test)

        # Sparsity
        n_nonzero: int = int(np.sum(coef != 0))
        n_features = len(coef)
        sparsity_ratio = 1.0 - (n_nonzero / n_features)

        # Feature importance
        feature_importance = {}
        if feature_names is not None:
            for name, imp in zip(feature_names, np.abs(coef)):
                if imp > 0:
                    feature_importance[name] = float(imp)

        # Explained variance
        y_pred = lasso.predict(X_test)
        explained_var = float(1 - np.var(y_test - y_pred) / np.var(y_test))

        result = RegularizationResult(
            timestamp=datetime.now(),
            regularization_type=RegularizationType.L1,
            alpha=alpha,
            l1_ratio=1.0,
            n_features=n_features,
            n_nonzero_features=n_nonzero,
            sparsity_ratio=sparsity_ratio,
            coefficients=coef,
            intercept=intercept,
            train_score=train_score,
            test_score=test_score,
            explained_variance=explained_var,
            feature_importance=feature_importance,
            details={"n_selected": int(n_nonzero)},
        )

        logger.info(
            f"L1 (alpha={alpha}): {n_nonzero}/{n_features} features, test_score={test_score:.4f}"
        )

        return result

    def analyze_l2_regularization(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        alpha: float = 1.0,
        feature_names: list[str] | None = None,
    ) -> RegularizationResult:
        """
        Analyze L2 regularization (Ridge).

        Args:
            X: Feature matrix
            y: Target vector
            alpha: Regularization strength
            feature_names: Feature names

        Returns:
            RegularizationResult with analysis
        """
        from sklearn.model_selection import train_test_split

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state
        )

        # Fit Ridge
        ridge = L2Regularization(alpha=alpha)
        ridge.fit(X_train, y_train)

        # Get coefficients
        coef = ridge.get_coefficients()
        intercept = ridge.get_intercept()

        # Scores
        train_score = ridge.score(X_train, y_train)
        test_score = ridge.score(X_test, y_test)

        # All features retained
        n_features = len(coef)
        n_nonzero: int = n_features
        sparsity_ratio = 0.0

        # Feature importance
        feature_importance = {}
        if feature_names is not None:
            for name, imp in zip(feature_names, np.abs(coef)):
                feature_importance[name] = float(imp)

        # Explained variance
        y_pred = ridge.predict(X_test)
        explained_var = float(1 - np.var(y_test - y_pred) / np.var(y_test))

        result = RegularizationResult(
            timestamp=datetime.now(),
            regularization_type=RegularizationType.L2,
            alpha=alpha,
            l1_ratio=0.0,
            n_features=n_features,
            n_nonzero_features=n_nonzero,
            sparsity_ratio=sparsity_ratio,
            coefficients=coef,
            intercept=intercept,
            train_score=train_score,
            test_score=test_score,
            explained_variance=explained_var,
            feature_importance=feature_importance,
            details={},
        )

        logger.info(f"L2 (alpha={alpha}): test_score={test_score:.4f}")

        return result

    def analyze_elastic_net(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        alpha: float = 1.0,
        l1_ratio: float = 0.5,
        feature_names: list[str] | None = None,
    ) -> RegularizationResult:
        """
        Analyze Elastic Net regularization.

        Args:
            X: Feature matrix
            y: Target vector
            alpha: Overall regularization strength
            l1_ratio: L1 mixing parameter
            feature_names: Feature names

        Returns:
            RegularizationResult with analysis
        """
        from sklearn.model_selection import train_test_split

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state
        )

        # Fit Elastic Net
        enet = ElasticNetRegularization(
            alpha=alpha, l1_ratio=l1_ratio, random_state=self.random_state
        )
        enet.fit(X_train, y_train)

        # Get coefficients
        coef = enet.get_coefficients()
        intercept = enet.get_intercept()

        # Scores
        train_score = enet.score(X_train, y_train)
        test_score = enet.score(X_test, y_test)

        # Sparsity
        n_nonzero: int = int(np.sum(coef != 0))
        n_features = len(coef)
        sparsity_ratio = 1.0 - (n_nonzero / n_features)

        # Feature importance
        feature_importance = {}
        if feature_names is not None:
            for name, imp in zip(feature_names, np.abs(coef)):
                if imp > 0:
                    feature_importance[name] = float(imp)

        # Explained variance
        y_pred = enet.predict(X_test)
        explained_var = float(1 - np.var(y_test - y_pred) / np.var(y_test))

        result = RegularizationResult(
            timestamp=datetime.now(),
            regularization_type=RegularizationType.ELASTIC_NET,
            alpha=alpha,
            l1_ratio=l1_ratio,
            n_features=n_features,
            n_nonzero_features=n_nonzero,
            sparsity_ratio=sparsity_ratio,
            coefficients=coef,
            intercept=intercept,
            train_score=train_score,
            test_score=test_score,
            explained_variance=explained_var,
            feature_importance=feature_importance,
            details={"l1_ratio": l1_ratio},
        )

        logger.info(
            f"ElasticNet (alpha={alpha}, l1_ratio={l1_ratio}): "
            f"{n_nonzero}/{n_features} features, test_score={test_score:.4f}"
        )

        return result

    def compute_regularization_path(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        regularization_type: RegularizationType = RegularizationType.L1,
        n_alphas: int = 50,
        alpha_range: tuple[float, float] = (1e-4, 10.0),
        l1_ratio: float = 0.5,
        feature_names: list[str] | None = None,
    ) -> RegularizationPath:
        """
        Compute regularization path.

        Args:
            X: Feature matrix
            y: Target vector
            regularization_type: Type of regularization
            n_alphas: Number of alpha values
            alpha_range: Range of alpha values (log scale)
            l1_ratio: L1 ratio for Elastic Net
            feature_names: Feature names

        Returns:
            RegularizationPath with path analysis
        """
        from sklearn.model_selection import train_test_split

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=self.random_state
        )

        # Generate alpha values (log scale)
        alphas = np.logspace(
            np.log10(alpha_range[0]),
            np.log10(alpha_range[1]),
            n_alphas,
        )

        path_points = []
        best_score = -np.inf
        best_alpha = alphas[0]

        for alpha in alphas:
            try:
                # Fit model with this alpha
                if regularization_type == RegularizationType.L1:
                    model: L1Regularization | L2Regularization | ElasticNetRegularization = (
                        L1Regularization(alpha=alpha, random_state=self.random_state)
                    )
                elif regularization_type == RegularizationType.L2:
                    model = L2Regularization(alpha=alpha)
                else:  # ELASTIC_NET
                    model = ElasticNetRegularization(
                        alpha=alpha, l1_ratio=l1_ratio, random_state=self.random_state
                    )

                model.fit(X_train, y_train)

                # Get coefficients
                coef = model.get_coefficients()
                n_nonzero: int = int(np.sum(coef != 0))

                # Score
                score = model.score(X_test, y_test)

                path_points.append(
                    RegularizationPathPoint(
                        alpha=alpha,
                        coefficients=coef,
                        n_nonzero=int(n_nonzero),
                        score=float(score),
                    )
                )

                # Track best
                if score > best_score:
                    best_score = score
                    best_alpha = alpha

            except Exception as e:
                logger.warning(f"Failed for alpha={alpha}: {e}")
                continue

        if not path_points:
            raise ValueError("No valid points computed on regularization path")

        # Get feature names
        if feature_names is None:
            if isinstance(X, pd.DataFrame):
                feature_names = X.columns.tolist()
            else:
                feature_names = [f"feature_{i}" for i in range(X.shape[1])]

        result = RegularizationPath(
            timestamp=datetime.now(),
            regularization_type=regularization_type,
            path_points=path_points,
            feature_names=feature_names,
            optimal_alpha=best_alpha,
            optimal_score=float(best_score),
            optimal_n_nonzero=path_points[np.argmax([p.score for p in path_points])].n_nonzero,
        )

        logger.info(
            f"Regularization path: optimal_alpha={best_alpha:.4f}, optimal_score={best_score:.4f}"
        )

        return result

    def compare_regularization_methods(
        self,
        X: np.ndarray | pd.DataFrame,
        y: np.ndarray | pd.Series,
        alphas: list[float] | None = None,
        l1_ratios: list[float] | None = None,
        feature_names: list[str] | None = None,
    ) -> dict[str, list[RegularizationResult]]:
        """
        Compare different regularization methods.

        Args:
            X: Feature matrix
            y: Target vector
            alphas: Alpha values to test
            l1_ratios: L1 ratios for Elastic Net
            feature_names: Feature names

        Returns:
            Dict mapping method name to list of results
        """
        if alphas is None:
            alphas = [0.001, 0.01, 0.1, 1.0, 10.0]

        if l1_ratios is None:
            l1_ratios = [0.2, 0.5, 0.8]

        results: dict[str, list[RegularizationResult]] = {
            "l1": [],
            "l2": [],
            "elastic_net": [],
        }

        # L1 regularization
        for alpha in alphas:
            try:
                result = self.analyze_l1_regularization(
                    X, y, alpha=alpha, feature_names=feature_names
                )
                results["l1"].append(result)
            except Exception as e:
                logger.warning(f"L1 with alpha={alpha} failed: {e}")

        # L2 regularization
        for alpha in alphas:
            try:
                result = self.analyze_l2_regularization(
                    X, y, alpha=alpha, feature_names=feature_names
                )
                results["l2"].append(result)
            except Exception as e:
                logger.warning(f"L2 with alpha={alpha} failed: {e}")

        # Elastic Net
        for alpha in alphas:
            for l1_ratio in l1_ratios:
                try:
                    result = self.analyze_elastic_net(
                        X, y, alpha=alpha, l1_ratio=l1_ratio, feature_names=feature_names
                    )
                    results["elastic_net"].append(result)
                except Exception as e:
                    logger.warning(
                        f"ElasticNet with alpha={alpha}, l1_ratio={l1_ratio} failed: {e}"
                    )

        return results


def optimize_regularization(
    X: np.ndarray | pd.DataFrame,
    y: np.ndarray | pd.Series,
    method: str = "lasso",
    cv_folds: int = 5,
    feature_names: list[str] | None = None,
) -> RegularizationResult:
    """
    Convenience function for automatic regularization optimization.

    Uses cross-validation to find optimal regularization parameters.

    Args:
        X: Feature matrix
        y: Target vector
        method: Regularization method ('lasso', 'ridge', 'elastic_net')
        cv_folds: Number of CV folds
        feature_names: Feature names

    Returns:
        RegularizationResult with best parameters

    Example:
        >>> result = optimize_regularization(X, y, method='lasso')
        >>> print(f"Optimal alpha: {result.alpha}")
        >>> print(f"Selected features: {result.n_nonzero_features}")
    """
    from sklearn.model_selection import train_test_split

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Use sklearn's CV for hyperparameter tuning
    if method == "lasso":
        model_cv = LassoCV(cv=cv_folds, random_state=42)
        model_cv.fit(X_train, y_train)

        # Refit on full training set
        lasso = Lasso(alpha=model_cv.alpha_, random_state=42)
        lasso.fit(X_train, y_train)

        coef = lasso.coef_
        intercept = lasso.intercept_
        alpha = model_cv.alpha_
        reg_type = RegularizationType.L1
        l1_ratio = 1.0

    elif method == "ridge":
        model_cv = RidgeCV(cv=cv_folds)
        model_cv.fit(X_train, y_train)

        ridge = Ridge(alpha=model_cv.alpha_)
        ridge.fit(X_train, y_train)

        coef = ridge.coef_
        intercept = ridge.intercept_
        alpha = model_cv.alpha_
        reg_type = RegularizationType.L2
        l1_ratio = 0.0

    else:
        raise ValueError(f"Unknown method: {method}")

    # Compute metrics
    train_score = (
        lasso.score(X_train, y_train) if method == "lasso" else ridge.score(X_train, y_train)
    )
    test_score = lasso.score(X_test, y_test) if method == "lasso" else ridge.score(X_test, y_test)

    n_features = len(coef)
    n_nonzero: int = int(np.sum(coef != 0))
    sparsity_ratio = 1.0 - (n_nonzero / n_features)

    # Feature importance
    feature_importance = {}
    if feature_names is not None:
        for name, imp in zip(feature_names, np.abs(coef)):
            if imp > 0:
                feature_importance[name] = float(imp)

    result = RegularizationResult(
        timestamp=datetime.now(),
        regularization_type=reg_type,
        alpha=alpha,
        l1_ratio=l1_ratio,
        n_features=n_features,
        n_nonzero_features=n_nonzero,
        sparsity_ratio=sparsity_ratio,
        coefficients=coef,
        intercept=intercept,
        train_score=train_score,
        test_score=test_score,
        explained_variance=0.0,  # Would need to compute
        feature_importance=feature_importance,
    )

    logger.info(f"Optimized {method}: alpha={alpha}, test_score={test_score:.4f}")

    return result
