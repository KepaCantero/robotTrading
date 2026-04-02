"""
Factor Calculator - Compute Fama-French Factor Scores

This module implements the calculation of individual factor scores for stocks
based on the Fama-French 5-factor model plus Momentum.

Factors:
1. Value (HML): High book-to-market ratio
2. Size (SMB): Small market cap
3. Profitability (RMW): High operating profitability
4. Investment (CMA): Conservative investment (low asset growth)
5. Momentum (WML): Past winners continue to win

Reference:
- Fama, E. F., & French, K. R. (2015). "A five-factor asset pricing model"
- Carhart, M. M. (1997). "On persistence in mutual fund performance"

SOLID Principles:
- Single Responsibility: Only factor calculations, no portfolio construction
- Open/Closed: Extensible with new factors
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

import numpy as np
from scipy import stats

from .models import FactorProfile, FactorScores

logger = logging.getLogger(__name__)


class FactorCalculator:
    """
    Calculator for Fama-French factor scores.

    Computes standardized factor scores for a universe of stocks.
    Scores are z-score normalized (mean=0, std=1) for cross-sectional comparison.
    """

    def __init__(self, min_samples: int = 10):
        """
        Initialize factor calculator.

        Args:
            min_samples: Minimum number of samples required for calculation
        """
        self.min_samples = min_samples
        self.factor_statistics: dict[str, dict[str, float]] = {}

    def calculate_factor_scores(
        self,
        profiles: list[FactorProfile],
    ) -> dict[str, FactorScores]:
        """
        Calculate factor scores for all profiles.

        Args:
            profiles: List of factor profiles

        Returns:
            Dictionary mapping symbol to factor scores
        """
        if len(profiles) < self.min_samples:
            logger.warning(
                f"Insufficient samples for factor calculation: {len(profiles)} < {self.min_samples}"
            )
            return {}

        logger.info(f"Calculating factor scores for {len(profiles)} stocks")

        # Calculate individual factor scores
        value_scores = self._calculate_value_scores(profiles)
        size_scores = self._calculate_size_scores(profiles)
        profitability_scores = self._calculate_profitability_scores(profiles)
        investment_scores = self._calculate_investment_scores(profiles)
        momentum_scores = self._calculate_momentum_scores(profiles)

        # Combine into factor scores
        factor_scores_dict = {}

        for profile in profiles:
            symbol = profile.symbol

            factor_scores = FactorScores(
                symbol=symbol,
                book_to_market=profile.book_to_market,
                market_cap=profile.market_cap,
                log_market_cap=self._log_cap(profile.market_cap),
                operating_profitability=profile.roa,
                roe=profile.roe,
                roa=profile.roa,
                asset_growth=profile.asset_growth,
                momentum_12m=profile.momentum_excluding_last_month,
                momentum_6m=profile.momentum_6m,
                value_score=value_scores.get(symbol),
                size_score=size_scores.get(symbol),
                profitability_score=profitability_scores.get(symbol),
                investment_score=investment_scores.get(symbol),
                momentum_score=momentum_scores.get(symbol),
                calculated_at=datetime.utcnow(),
            )

            # Calculate composite scores
            factor_scores.composite_quality_score = self._calculate_composite_quality(
                factor_scores, profile
            )
            factor_scores.factor_momentum_score = self._calculate_factor_momentum(factor_scores)

            factor_scores_dict[symbol] = factor_scores

        # Store statistics
        self._store_statistics(factor_scores_dict)

        logger.info(f"Calculated factor scores for {len(factor_scores_dict)} stocks")

        return factor_scores_dict

    def _calculate_value_scores(self, profiles: list[FactorProfile]) -> dict[str, Decimal]:
        """
        Calculate value factor scores based on book-to-market ratio.

        Value factor (HML): High B/M stocks outperform low B/M stocks.
        High positive score = value stock (high B/M).

        Args:
            profiles: List of factor profiles

        Returns:
            Dictionary mapping symbol to value score (z-score)
        """
        # Extract valid B/M ratios
        valid_bm = [
            (p.symbol, float(p.book_to_market))
            for p in profiles
            if p.book_to_market is not None and p.book_to_market > 0
        ]

        if len(valid_bm) < self.min_samples:
            logger.warning("Insufficient valid book-to-market ratios")
            return {}

        symbols, bm_values = zip(*valid_bm)

        # Calculate z-scores
        bm_array = np.array(bm_values)
        z_scores = stats.zscore(bm_array)

        # High B/M = value stock = positive score
        # Standard z-score already gives this property

        return {symbol: Decimal(str(z_score)) for symbol, z_score in zip(symbols, z_scores)}

    def _calculate_size_scores(self, profiles: list[FactorProfile]) -> dict[str, Decimal]:
        """
        Calculate size factor scores based on market cap.

        Size factor (SMB): Small cap stocks outperform large cap stocks.
        High negative score on log market cap = small cap = positive size score.

        Args:
            profiles: List of factor profiles

        Returns:
            Dictionary mapping symbol to size score (z-score)
        """
        # Extract valid market caps
        valid_mc = [
            (p.symbol, float(p.market_cap))
            for p in profiles
            if p.market_cap is not None and p.market_cap > 0
        ]

        if len(valid_mc) < self.min_samples:
            logger.warning("Insufficient valid market caps")
            return {}

        symbols, mc_values = zip(*valid_mc)

        # Use log of market cap (standard in FF model)
        log_mc = np.log(np.array(mc_values))

        # Calculate z-scores
        z_scores = stats.zscore(log_mc)

        # Small cap = negative z-score on log MC = we want positive for small caps
        # So flip the sign
        size_scores = -z_scores

        return {
            symbol: Decimal(str(size_score)) for symbol, size_score in zip(symbols, size_scores)
        }

    def _calculate_profitability_scores(self, profiles: list[FactorProfile]) -> dict[str, Decimal]:
        """
        Calculate profitability factor scores.

        Profitability factor (RMW): High profitability stocks outperform low profitability.
        Uses operating profitability (Revenue - COGS - SGA - Interest) / Assets.
        We use ROA as proxy.

        Args:
            profiles: List of factor profiles

        Returns:
            Dictionary mapping symbol to profitability score (z-score)
        """
        # Extract valid ROA values
        valid_roa = [(p.symbol, float(p.roa)) for p in profiles if p.roa is not None]

        if len(valid_roa) < self.min_samples:
            logger.warning("Insufficient valid ROA values")
            return {}

        symbols, roa_values = zip(*valid_roa)

        # Calculate z-scores
        roa_array = np.array(roa_values)
        z_scores = stats.zscore(roa_array)

        # High ROA = profitable = positive score
        # Standard z-score already gives this

        return {symbol: Decimal(str(z_score)) for symbol, z_score in zip(symbols, z_scores)}

    def _calculate_investment_scores(self, profiles: list[FactorProfile]) -> dict[str, Decimal]:
        """
        Calculate investment factor scores.

        Investment factor (CMA): Conservative investors (low asset growth) outperform
        aggressive investors (high asset growth).

        Low asset growth = conservative = positive investment score.

        Args:
            profiles: List of factor profiles

        Returns:
            Dictionary mapping symbol to investment score (z-score)
        """
        # Extract valid asset growth values
        valid_ag = [
            (p.symbol, float(p.asset_growth)) for p in profiles if p.asset_growth is not None
        ]

        if len(valid_ag) < self.min_samples:
            logger.warning("Insufficient valid asset growth values")
            return {}

        symbols, ag_values = zip(*valid_ag)

        # Calculate z-scores
        ag_array = np.array(ag_values)
        z_scores = stats.zscore(ag_array)

        # Low asset growth = conservative = positive score
        # So flip the sign
        investment_scores = -z_scores

        return {
            symbol: Decimal(str(inv_score)) for symbol, inv_score in zip(symbols, investment_scores)
        }

    def _calculate_momentum_scores(self, profiles: list[FactorProfile]) -> dict[str, Decimal]:
        """
        Calculate momentum factor scores.

        Momentum factor (WML): Past winners (high past returns) continue to outperform.
        Uses 12-month momentum excluding last month.

        Args:
            profiles: List of factor profiles

        Returns:
            Dictionary mapping symbol to momentum score (z-score)
        """
        # Extract valid momentum values
        valid_mom = [
            (p.symbol, float(p.momentum_excluding_last_month))
            for p in profiles
            if p.momentum_excluding_last_month is not None
        ]

        if len(valid_mom) < self.min_samples:
            logger.warning("Insufficient valid momentum values")
            return {}

        symbols, mom_values = zip(*valid_mom)

        # Calculate z-scores
        mom_array = np.array(mom_values)
        z_scores = stats.zscore(mom_array)

        # High momentum = winner = positive score
        # Standard z-score already gives this

        return {symbol: Decimal(str(z_score)) for symbol, z_score in zip(symbols, z_scores)}

    def _calculate_composite_quality(
        self, factor_scores: FactorScores, profile: FactorProfile
    ) -> Decimal:
        """
        Calculate composite quality score (0-100).

        Quality combines:
        - High profitability
        - Conservative investment
        - Low volatility
        - Good earnings quality

        Args:
            factor_scores: Calculated factor scores
            profile: Factor profile

        Returns:
            Composite quality score
        """
        quality_components = []

        # Profitability score (converted to 0-100)
        if factor_scores.profitability_score is not None:
            # Z-score to 0-100: mean=50, each SD=15
            prof_score = 50 + float(factor_scores.profitability_score) * 15
            quality_components.append(prof_score)

        # Investment score (conservative = good)
        if factor_scores.investment_score is not None:
            # Positive investment score = conservative = good
            inv_score = 50 + float(factor_scores.investment_score) * 15
            quality_components.append(inv_score)

        # Earnings quality (net margin)
        if profile.net_margin is not None:
            # Net margin to score: 20% = 100, 0% = 50, negative = 0
            margin_score = 50 + float(profile.net_margin) * 2.5
            margin_score = max(0, min(100, margin_score))
            quality_components.append(margin_score)

        # ROE
        if profile.roe is not None:
            # ROE to score: 20% = 100, 0% = 50, negative = 0
            roe_score = 50 + float(profile.roe) * 2.5
            roe_score = max(0, min(100, roe_score))
            quality_components.append(roe_score)

        if not quality_components:
            return Decimal("50")

        # Average quality score
        avg_quality = np.mean(quality_components)
        return Decimal(str(max(0, min(100, avg_quality))))

    def _calculate_factor_momentum(self, factor_scores: FactorScores) -> Decimal:
        """
        Calculate factor momentum score.

        Measures how fast factor scores are improving.

        Args:
            factor_scores: Calculated factor scores

        Returns:
            Factor momentum score (0-100)
        """
        momentum_components = []

        # Actual momentum factor
        if factor_scores.momentum_score is not None:
            # Z-score to 0-100
            mom_score = 50 + float(factor_scores.momentum_score) * 15
            momentum_components.append(mom_score)

        # Momentum from 6-month return
        if factor_scores.momentum_6m is not None:
            # Convert to score: 50% return = 100, 0% = 50, -50% = 0
            mom_6m_score = 50 + float(factor_scores.momentum_6m)
            mom_6m_score = max(0, min(100, mom_6m_score))
            momentum_components.append(mom_6m_score)

        if not momentum_components:
            return Decimal("50")

        avg_momentum = np.mean(momentum_components)
        return Decimal(str(max(0, min(100, avg_momentum))))

    def _log_cap(self, market_cap: Decimal | None) -> Decimal | None:
        """Calculate log of market cap."""
        if market_cap is None or market_cap <= 0:
            return None
        try:
            import math

            return Decimal(str(math.log(float(market_cap))))
        except (ValueError, OverflowError):
            return None

    def _store_statistics(self, factor_scores_dict: dict[str, FactorScores]) -> None:
        """Store factor score statistics for analysis."""
        if not factor_scores_dict:
            return

        factors = ["value", "size", "profitability", "investment", "momentum"]
        factor_fields = {
            "value": "value_score",
            "size": "size_score",
            "profitability": "profitability_score",
            "investment": "investment_score",
            "momentum": "momentum_score",
        }

        for factor in factors:
            field = factor_fields[factor]
            values = [
                float(getattr(scores, field))
                for scores in factor_scores_dict.values()
                if getattr(scores, field) is not None
            ]

            if values:
                self.factor_statistics[factor] = {
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values)),
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "count": len(values),
                }

    def get_factor_statistics(self) -> dict[str, dict[str, float]]:
        """Get stored factor statistics."""
        return self.factor_statistics.copy()

    def calculate_predicted_returns(
        self,
        factor_scores_dict: dict[str, FactorScores],
        factor_premiums: dict[str, float],
        risk_free_rate: float = 0.02,
    ) -> dict[str, Decimal]:
        """
        Calculate predicted returns using factor model.

        R_i - R_f = β_MKT * MKT + β_SMB * SMB + β_HML * HML + β_RMW * RMW + β_CMA * CMA + β_WML * WML

        Args:
            factor_scores_dict: Factor scores for all stocks
            factor_premiums: Historical factor premiums (annual returns)
            risk_free_rate: Risk-free rate

        Returns:
            Dictionary mapping symbol to predicted annual return
        """
        predicted_returns = {}

        for symbol, scores in factor_scores_dict.items():
            # Factor loadings (using z-scores as proxy for betas)
            loadings = {
                "value": float(scores.value_score or 0),
                "size": float(scores.size_score or 0),
                "profitability": float(scores.profitability_score or 0),
                "investment": float(scores.investment_score or 0),
                "momentum": float(scores.momentum_score or 0),
            }

            # Calculate expected return from factors
            expected_return = risk_free_rate
            for factor, loading in loadings.items():
                premium = factor_premiums.get(factor, 0.05)  # Default 5% premium
                expected_return += loading * premium

            predicted_returns[symbol] = Decimal(str(expected_return * 100))  # As percentage

        return predicted_returns


def get_default_factor_premiums() -> dict[str, float]:
    """
    Get default factor premiums based on historical research.

    Values are approximate long-term annual premiums from US market data.
    Source: Fama-French research, Kenneth French data library.

    Returns:
        Dictionary mapping factor name to annual premium (decimal)
    """
    return {
        "market": 0.06,  # Market risk premium (~6%)
        "value": 0.04,  # HML premium (~4%)
        "size": 0.03,  # SMB premium (~3%)
        "profitability": 0.04,  # RMW premium (~4%)
        "investment": 0.03,  # CMA premium (~3%)
        "momentum": 0.05,  # WML premium (~5%)
    }
