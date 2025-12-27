"""
Seasonality Analyzer - PHASE 4 MODULE 7 PHASE 2

Analyzes seasonal patterns in strategy returns:
- Monthly return patterns and performance
- Quarterly return analysis
- Seasonal decomposition (additive/multiplicative)
- Best/worst month identification
- Seasonality strength index
- Markdown report generation
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SeasonalityAnalyzer:
    """Analyzer for seasonal patterns in returns."""

    def __init__(self, min_data_points: int = 60):
        """
        Initialize seasonality analyzer.

        Args:
            min_data_points: Minimum data points required for reliable analysis (default: 60 months = 5 years)
        """
        self.min_data_points = min_data_points
        self.analysis_performed = False

    def analyze_monthly_returns(
        self, equity_curve: List[Tuple[datetime, Decimal]]
    ) -> Optional[Dict]:
        """
        Analyze monthly return patterns.

        Args:
            equity_curve: List of (datetime, equity) tuples

        Returns:
            Dictionary with monthly statistics or None if insufficient data
        """
        try:
            if not equity_curve or len(equity_curve) < 12:
                logger.warning("Insufficient data for monthly analysis (need ≥12 months)")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(equity_curve, columns=['date', 'equity'])
            df['date'] = pd.to_datetime(df['date'])
            df['equity'] = df['equity'].astype(float)
            df = df.sort_values('date').set_index('date')

            # Calculate daily returns
            df['daily_return'] = df['equity'].pct_change()

            # Group by month and year
            df['year_month'] = df.index.to_period('M')
            monthly_returns = df.groupby('year_month')['daily_return'].apply(
                lambda x: (1 + x).prod() - 1
            )

            # Calculate statistics by month of year
            df['month'] = df.index.month
            df['month_name'] = df.index.strftime('%B')

            month_stats = []
            for month in range(1, 13):
                month_data = df[df['month'] == month]['daily_return'].dropna()

                if len(month_data) > 0:
                    # Monthly return (cumulative for month)
                    monthly_ret = (1 + month_data).prod() - 1

                    month_stats.append(
                        {
                            'month': month,
                            'month_name': self._month_name(month),
                            'avg_return': float(np.mean(month_data)),
                            'median_return': float(np.median(month_data)),
                            'std_dev': float(np.std(month_data)),
                            'cumulative_return': float(monthly_ret),
                            'positive_count': int((month_data > 0).sum()),
                            'negative_count': int((month_data <= 0).sum()),
                            'total_count': len(month_data),
                        }
                    )

            return {
                'total_months_analyzed': len(monthly_returns),
                'month_stats': month_stats,
                'best_month': max(month_stats, key=lambda x: x['cumulative_return'], default=None),
                'worst_month': min(month_stats, key=lambda x: x['cumulative_return'], default=None),
                'overall_avg_return': float(np.mean(monthly_returns)),
            }

        except Exception as e:
            logger.error(f"Error analyzing monthly returns: {e}")
            return None

    def analyze_quarterly_returns(
        self, equity_curve: List[Tuple[datetime, Decimal]]
    ) -> Optional[Dict]:
        """
        Analyze quarterly return patterns.

        Args:
            equity_curve: List of (datetime, equity) tuples

        Returns:
            Dictionary with quarterly statistics or None if insufficient data
        """
        try:
            if not equity_curve or len(equity_curve) < 63:  # ~5 years of quarterly data
                logger.warning("Insufficient data for quarterly analysis (need ≥5 years)")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(equity_curve, columns=['date', 'equity'])
            df['date'] = pd.to_datetime(df['date'])
            df['equity'] = df['equity'].astype(float)
            df = df.sort_values('date').set_index('date')

            # Calculate daily returns
            df['daily_return'] = df['equity'].pct_change()

            # Group by quarter
            df['quarter'] = df.index.quarter
            df['year_quarter'] = df.index.to_period('Q')

            quarterly_returns = df.groupby('year_quarter')['daily_return'].apply(
                lambda x: (1 + x).prod() - 1
            )

            # Calculate statistics by quarter
            quarter_stats = []
            for q in range(1, 5):
                q_data = df[df['quarter'] == q]['daily_return'].dropna()

                if len(q_data) > 0:
                    q_return = (1 + q_data).prod() - 1

                    quarter_stats.append(
                        {
                            'quarter': q,
                            'quarter_name': f'Q{q}',
                            'avg_return': float(np.mean(q_data)),
                            'median_return': float(np.median(q_data)),
                            'std_dev': float(np.std(q_data)),
                            'cumulative_return': float(q_return),
                            'positive_count': int((q_data > 0).sum()),
                            'negative_count': int((q_data <= 0).sum()),
                            'total_count': len(q_data),
                        }
                    )

            return {
                'total_quarters_analyzed': len(quarterly_returns),
                'quarter_stats': quarter_stats,
                'best_quarter': max(
                    quarter_stats, key=lambda x: x['cumulative_return'], default=None
                ),
                'worst_quarter': min(
                    quarter_stats, key=lambda x: x['cumulative_return'], default=None
                ),
                'overall_avg_return': float(np.mean(quarterly_returns)),
            }

        except Exception as e:
            logger.error(f"Error analyzing quarterly returns: {e}")
            return None

    def get_best_worst_months(
        self, equity_curve: List[Tuple[datetime, Decimal]]
    ) -> Optional[Dict[str, List]]:
        """
        Get ranking of best and worst months for the strategy.

        Args:
            equity_curve: List of (datetime, equity) tuples

        Returns:
            Dictionary with ranked months or None
        """
        try:
            monthly_analysis = self.analyze_monthly_returns(equity_curve)

            if not monthly_analysis or not monthly_analysis.get('month_stats'):
                return None

            month_stats = monthly_analysis['month_stats']

            # Sort by cumulative return
            sorted_months = sorted(month_stats, key=lambda x: x['cumulative_return'], reverse=True)

            # Get worst months and sort them in ascending order (lowest first)
            worst_months = sorted(sorted_months[-3:], key=lambda x: x['cumulative_return'])

            return {
                'best_months': sorted_months[:3],  # Top 3
                'worst_months': worst_months,  # Bottom 3, sorted ascending
                'all_months_ranked': sorted_months,
            }

        except Exception as e:
            logger.error(f"Error getting best/worst months: {e}")
            return None

    def get_seasonality_strength(
        self, equity_curve: List[Tuple[datetime, Decimal]]
    ) -> Optional[Decimal]:
        """
        Calculate seasonality strength index (0-1).

        Formula:
        - Measures how much variance is explained by seasonal component
        - 0 = no seasonality, 1 = perfect seasonality
        - Uses ratio of seasonal variance to total variance

        Args:
            equity_curve: List of (datetime, equity) tuples

        Returns:
            Seasonality strength (0-1) or None if calculation not possible
        """
        try:
            monthly_analysis = self.analyze_monthly_returns(equity_curve)

            if not monthly_analysis or not monthly_analysis.get('month_stats'):
                return None

            month_stats = monthly_analysis['month_stats']

            # Get cumulative returns by month
            returns_by_month = [m['cumulative_return'] for m in month_stats]

            # Calculate variance
            total_variance = np.var(returns_by_month)

            if total_variance == 0:
                return Decimal("0")

            # Seasonal strength = 1 - (residual var / total var)
            # For simplicity, use coefficient of variation
            mean_return = np.mean(returns_by_month)
            std_return = np.std(returns_by_month)

            if mean_return == 0:
                # Use normalized measure
                strength = std_return / 0.1  # Normalize to 0.1 baseline
            else:
                strength = std_return / abs(mean_return)

            # Normalize to 0-1 range
            strength = min(1.0, strength)

            return Decimal(str(round(strength, 4)))

        except Exception as e:
            logger.error(f"Error calculating seasonality strength: {e}")
            return None

    def decompose_returns(
        self, equity_curve: List[Tuple[datetime, Decimal]], method: str = 'additive'
    ) -> Optional[Dict]:
        """
        Decompose returns into trend, seasonal, and residual components.

        Args:
            equity_curve: List of (datetime, equity) tuples
            method: 'additive' or 'multiplicative' (default: 'additive')

        Returns:
            Dictionary with decomposition components or None
        """
        try:
            if not equity_curve or len(equity_curve) < 24:
                logger.warning("Insufficient data for decomposition (need ≥24 months)")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(equity_curve, columns=['date', 'equity'])
            df['date'] = pd.to_datetime(df['date'])
            df['equity'] = df['equity'].astype(float)
            df = df.sort_values('date').set_index('date')

            # Resample to monthly frequency
            monthly = df['equity'].resample('M').last()

            if len(monthly) < 12:
                logger.warning("Insufficient monthly data for decomposition")
                return None

            # Try statsmodels decomposition
            try:
                from statsmodels.tsa.seasonal import seasonal_decompose

                decomposition = seasonal_decompose(monthly, model=method, period=12)

                return {
                    'method': method,
                    'trend': [float(x) for x in decomposition.trend.dropna()],
                    'seasonal': [float(x) for x in decomposition.seasonal.dropna()],
                    'residual': [float(x) for x in decomposition.resid.dropna()],
                    'periods_analyzed': len(monthly),
                }
            except ImportError:
                logger.warning("statsmodels not available, skipping decomposition")
                return None

        except Exception as e:
            logger.error(f"Error decomposing returns: {e}")
            return None

    def generate_seasonality_report(
        self, equity_curve: List[Tuple[datetime, Decimal]], strategy_name: str = "Strategy"
    ) -> str:
        """
        Generate a markdown report of seasonality analysis.

        Args:
            equity_curve: List of (datetime, equity) tuples
            strategy_name: Name of the strategy

        Returns:
            Markdown formatted report
        """
        try:
            report = []
            report.append(f"# Seasonality Analysis Report: {strategy_name}\n")
            report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            # Monthly Analysis
            monthly = self.analyze_monthly_returns(equity_curve)
            if monthly:
                report.append("## Monthly Return Analysis\n")
                report.append(f"**Total Months Analyzed**: {monthly['total_months_analyzed']}\n")
                report.append(
                    f"**Average Monthly Return**: {monthly['overall_avg_return']:.4f}\n\n"
                )

                if monthly['best_month']:
                    report.append(
                        f"**Best Month**: {monthly['best_month']['month_name']} "
                        f"({monthly['best_month']['cumulative_return']:.4f})\n"
                    )
                if monthly['worst_month']:
                    report.append(
                        f"**Worst Month**: {monthly['worst_month']['month_name']} "
                        f"({monthly['worst_month']['cumulative_return']:.4f})\n\n"
                    )

                # Month table
                report.append("### Monthly Performance Table\n\n")
                report.append(
                    "| Month | Avg Return | Median Return | Std Dev | Win Rate | Count |\n"
                )
                report.append(
                    "|-------|-----------|---------------|---------|----------|-------|\n"
                )

                for m in monthly['month_stats']:
                    win_rate = (
                        m['positive_count'] / m['total_count'] * 100 if m['total_count'] > 0 else 0
                    )
                    report.append(
                        f"| {m['month_name']:>10} | {m['avg_return']:>9.4f} | {m['median_return']:>13.4f} | "
                        f"{m['std_dev']:>7.4f} | {win_rate:>7.1f}% | {m['total_count']:>5} |\n"
                    )
                report.append("")

            # Quarterly Analysis
            quarterly = self.analyze_quarterly_returns(equity_curve)
            if quarterly:
                report.append("\n## Quarterly Return Analysis\n")
                report.append(
                    f"**Total Quarters Analyzed**: {quarterly['total_quarters_analyzed']}\n"
                )
                report.append(
                    f"**Average Quarterly Return**: {quarterly['overall_avg_return']:.4f}\n\n"
                )

                if quarterly['best_quarter']:
                    report.append(
                        f"**Best Quarter**: {quarterly['best_quarter']['quarter_name']} "
                        f"({quarterly['best_quarter']['cumulative_return']:.4f})\n"
                    )
                if quarterly['worst_quarter']:
                    report.append(
                        f"**Worst Quarter**: {quarterly['worst_quarter']['quarter_name']} "
                        f"({quarterly['worst_quarter']['cumulative_return']:.4f})\n\n"
                    )

                # Quarter table
                report.append("### Quarterly Performance Table\n\n")
                report.append(
                    "| Quarter | Avg Return | Median Return | Std Dev | Win Rate | Count |\n"
                )
                report.append(
                    "|---------|-----------|---------------|---------|----------|-------|\n"
                )

                for q in quarterly['quarter_stats']:
                    win_rate = (
                        q['positive_count'] / q['total_count'] * 100 if q['total_count'] > 0 else 0
                    )
                    report.append(
                        f"| {q['quarter_name']:>7} | {q['avg_return']:>9.4f} | {q['median_return']:>13.4f} | "
                        f"{q['std_dev']:>7.4f} | {win_rate:>7.1f}% | {q['total_count']:>5} |\n"
                    )
                report.append("")

            # Seasonality Strength
            strength = self.get_seasonality_strength(equity_curve)
            if strength is not None:
                report.append("\n## Seasonality Strength\n")
                report.append(f"**Seasonality Index**: {strength} (0=none, 1=perfect)\n")

                strength_val = float(strength)
                if strength_val < 0.1:
                    interpretation = "Very weak seasonal patterns"
                elif strength_val < 0.3:
                    interpretation = "Weak seasonal patterns"
                elif strength_val < 0.6:
                    interpretation = "Moderate seasonal patterns"
                else:
                    interpretation = "Strong seasonal patterns"

                report.append(f"**Interpretation**: {interpretation}\n")

            # Insights
            report.append("\n## Key Insights\n")

            if monthly:
                best_months_names = [m['month_name'] for m in monthly['month_stats'][:3]]
                report.append(
                    f"- Historically strongest months: {', '.join(best_months_names[:2])}\n"
                )

            if quarterly:
                best_quarters = [q['quarter_name'] for q in quarterly['quarter_stats'][:2]]
                report.append(f"- Historically strongest quarters: {', '.join(best_quarters)}\n")

            if strength is not None and float(strength) > 0.3:
                report.append(
                    "- Significant seasonal patterns detected - consider seasonal adjustments\n"
                )
            else:
                report.append(
                    "- Weak seasonal patterns - strategy performance not highly seasonal\n"
                )

            return "".join(report)

        except Exception as e:
            logger.error(f"Error generating seasonality report: {e}")
            return f"Error generating report: {str(e)}"

    @staticmethod
    def _month_name(month: int) -> str:
        """Get month name from number."""
        months = [
            'January',
            'February',
            'March',
            'April',
            'May',
            'June',
            'July',
            'August',
            'September',
            'October',
            'November',
            'December',
        ]
        return months[month - 1] if 1 <= month <= 12 else f"Month {month}"
