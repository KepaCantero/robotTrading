"""
Servicio de validación de rentabilidad para estrategias de trading.

Este servicio valida que las estrategias generen rentabilidad neta positiva
después de todos los costos operativos, incluyendo comisiones, slippage,
market impact e infraestructura.
"""

import logging
import statistics
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.domain.models.profitability_validation import (
    CostBreakdown,
    HistoricalValidation,
    ProfitabilityMetrics,
    ProfitabilityValidation,
    StrategyComparison,
    ValidationCriteria,
    ValidationReport,
    ValidationRequest,
    ValidationResponse,
    ValidationStatus,
)
from app.services.cost_analysis_service import CostAnalysisService
from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


class ProfitabilityCalculator:
    """Calculadora de métricas de rentabilidad."""

    def __init__(self):
        self.cost_service = CostAnalysisService()

    def calculate_metrics(
        self,
        trades_data: List[Dict[str, Any]],
        initial_capital: Decimal,
        final_capital: Decimal,
    ) -> Tuple[ProfitabilityMetrics, CostBreakdown]:
        """Calcular métricas de rentabilidad y desglose de costos."""

        # Calcular ganancia bruta
        gross_profit = final_capital - initial_capital

        # Calcular costos estimados basados en trades_data
        cost_breakdown = self._estimate_costs_from_trades(trades_data)

        # Calcular ganancia neta
        net_profit = gross_profit - cost_breakdown.total_costs

        # Calcular métricas adicionales
        profit_margin = (
            (net_profit / initial_capital) * 100 if initial_capital > 0 else Decimal("0")
        )
        roi = profit_margin  # ROI es igual al profit margin en este contexto

        # Calcular métricas de trading
        win_rate, profit_factor, max_drawdown = self._calculate_trading_metrics(
            trades_data, initial_capital
        )

        # Calcular Sharpe ratio (simplificado)
        sharpe_ratio = self._calculate_sharpe_ratio(trades_data)

        # Calcular Cost Impact Ratio
        cost_impact_ratio = (
            (cost_breakdown.total_costs / gross_profit) if gross_profit > 0 else Decimal("0")
        )

        metrics = ProfitabilityMetrics(
            gross_profit=gross_profit,
            net_profit=net_profit,
            total_costs=cost_breakdown.total_costs,
            profit_margin=profit_margin,
            return_on_investment=roi,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            cost_impact_ratio=cost_impact_ratio,
        )

        return metrics, cost_breakdown

    def _estimate_costs_from_trades(self, trades_data: List[Dict[str, Any]]) -> CostBreakdown:
        """Estimar costos basados en datos de trades."""

        config = get_config()
        cost_config = config.trading_costs

        total_commissions = Decimal("0")
        total_slippage = Decimal("0")
        total_market_impact = Decimal("0")
        total_infrastructure = Decimal("0")
        total_data_fees = Decimal("0")
        total_financing = Decimal("0")
        total_other = Decimal("0")

        for trade in trades_data:
            # Estimar comisiones (0.1% del valor del trade)
            pnl = trade.get("pnl", Decimal("0"))
            if isinstance(pnl, (int, float)):
                pnl = Decimal(str(pnl))

            # Estimar valor del trade basado en PnL (simplificado)
            # Estimación conservadora - usa config
            estimated_trade_value = abs(pnl) * cost_config.trade_value_multiplier

            commission = estimated_trade_value * cost_config.commission_rate
            total_commissions += commission

            # Estimar slippage (0.05% del valor del trade)
            slippage = estimated_trade_value * cost_config.slippage_rate
            total_slippage += slippage

            # Estimar market impact (0.02% del valor del trade)
            market_impact = estimated_trade_value * cost_config.market_impact_rate
            total_market_impact += market_impact

            # Costos fijos por trade - usa config
            total_infrastructure += cost_config.infrastructure_cost_per_trade
            total_data_fees += cost_config.data_fee_per_trade

        return CostBreakdown(
            commissions=total_commissions,
            slippage=total_slippage,
            market_impact=total_market_impact,
            infrastructure=total_infrastructure,
            data_fees=total_data_fees,
            financing=total_financing,
            other=total_other,
        )

    def _calculate_trading_metrics(
        self, trades_data: List[Dict[str, Any]], initial_capital: Decimal
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """Calcular métricas específicas de trading."""

        if not trades_data:
            return Decimal("0"), Decimal("0"), Decimal("0")

        # Separar trades ganadores y perdedores
        winning_trades = []
        losing_trades = []

        for trade in trades_data:
            pnl = trade.get("pnl", Decimal("0"))
            if isinstance(pnl, (int, float)):
                pnl = Decimal(str(pnl))

            if pnl > 0:
                winning_trades.append(pnl)
            elif pnl < 0:
                losing_trades.append(abs(pnl))

        # Calcular win rate
        total_trades = len(trades_data)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else Decimal("0")

        # Calcular profit factor
        total_wins = sum(winning_trades) if winning_trades else Decimal("0")
        total_losses = sum(losing_trades) if losing_trades else Decimal("0")
        profit_factor = (total_wins / total_losses) if total_losses > 0 else Decimal("0")

        # Calcular max drawdown
        max_drawdown = self._calculate_max_drawdown(trades_data, initial_capital)

        return win_rate, profit_factor, max_drawdown

    def _calculate_max_drawdown(
        self, trades_data: List[Dict[str, Any]], initial_capital: Decimal
    ) -> Decimal:
        """Calcular el drawdown máximo."""

        if not trades_data:
            return Decimal("0")

        # Ordenar trades por fecha
        sorted_trades = sorted(trades_data, key=lambda x: x.get("timestamp", ""))

        peak = initial_capital
        max_dd = Decimal("0")
        current_capital = initial_capital

        for trade in sorted_trades:
            pnl = trade.get("pnl", Decimal("0"))
            if isinstance(pnl, (int, float)):
                pnl = Decimal(str(pnl))

            current_capital += pnl

            if current_capital > peak:
                peak = current_capital

            drawdown = ((peak - current_capital) / peak * 100) if peak > 0 else Decimal("0")
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    def _calculate_sharpe_ratio(self, trades_data: List[Dict[str, Any]]) -> Optional[Decimal]:
        """Calcular Sharpe ratio simplificado."""

        if len(trades_data) < 2:
            return None

        config = get_config()
        base_capital = config.trading_costs.assumed_base_capital

        # Extraer retornos
        returns = []
        for trade in trades_data:
            pnl = trade.get("pnl", Decimal("0"))
            if isinstance(pnl, (int, float)):
                pnl = Decimal(str(pnl))

            # Convertir a retorno porcentual (simplificado)
            # Usa capital base configurado
            return_pct = (pnl / base_capital) * 100
            returns.append(float(return_pct))

        if len(returns) < 2:
            return None

        # Calcular Sharpe ratio
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0

        if std_return == 0:
            return None

        # Asumiendo risk-free rate de 0% para simplificar
        sharpe_ratio = mean_return / std_return

        return Decimal(str(round(sharpe_ratio, 2)))


class ProfitabilityValidator:
    """Validador de criterios de rentabilidad."""

    def __init__(self):
        self.config = get_config()

    def validate_profitability(
        self, metrics: ProfitabilityMetrics, criteria: ValidationCriteria
    ) -> Tuple[ValidationStatus, List[str], List[str], List[str]]:
        """Validar rentabilidad contra criterios específicos."""

        passed_tests = []
        failed_tests = []
        warnings = []

        # Test 1: Ganancia neta mínima
        if metrics.net_profit >= criteria.min_net_profit:
            passed_tests.append("min_net_profit")
        else:
            failed_tests.append(f"min_net_profit: {metrics.net_profit} < {criteria.min_net_profit}")

        # Test 2: Margen de ganancia mínimo
        if metrics.profit_margin >= criteria.min_profit_margin:
            passed_tests.append("min_profit_margin")
        else:
            failed_tests.append(
                f"min_profit_margin: {metrics.profit_margin}% < {criteria.min_profit_margin}%"
            )

        # Test 3: ROI mínimo
        if metrics.return_on_investment >= criteria.min_roi:
            passed_tests.append("min_roi")
        else:
            failed_tests.append(f"min_roi: {metrics.return_on_investment}% < {criteria.min_roi}%")

        # Test 4: Sharpe ratio mínimo
        if metrics.sharpe_ratio and metrics.sharpe_ratio >= criteria.min_sharpe_ratio:
            passed_tests.append("min_sharpe_ratio")
        elif metrics.sharpe_ratio is None:
            warnings.append("sharpe_ratio: Insufficient data for calculation")
        else:
            failed_tests.append(
                f"min_sharpe_ratio: {metrics.sharpe_ratio} < {criteria.min_sharpe_ratio}"
            )

        # Test 5: Drawdown máximo
        if metrics.max_drawdown <= criteria.max_drawdown_limit:
            passed_tests.append("max_drawdown_limit")
        else:
            failed_tests.append(
                f"max_drawdown_limit: {metrics.max_drawdown}% > {criteria.max_drawdown_limit}%"
            )

        # Test 6: Tasa de ganancia mínima
        if metrics.win_rate >= criteria.min_win_rate:
            passed_tests.append("min_win_rate")
        else:
            failed_tests.append(f"min_win_rate: {metrics.win_rate}% < {criteria.min_win_rate}%")

        # Test 7: Factor de ganancia mínimo
        if metrics.profit_factor >= criteria.min_profit_factor:
            passed_tests.append("min_profit_factor")
        else:
            failed_tests.append(
                f"min_profit_factor: {metrics.profit_factor} < {criteria.min_profit_factor}"
            )

        # Test 8: Ratio de impacto de costos máximo
        if metrics.cost_impact_ratio <= criteria.max_cost_impact_ratio:
            passed_tests.append("max_cost_impact_ratio")
        else:
            failed_tests.append(
                f"max_cost_impact_ratio: {metrics.cost_impact_ratio} > {criteria.max_cost_impact_ratio}"
            )

        # Determinar estado general
        if not failed_tests:
            if not warnings:
                status = ValidationStatus.PASSED
            else:
                status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAILED

        return status, passed_tests, failed_tests, warnings

    def generate_recommendation(
        self,
        metrics: ProfitabilityMetrics,
        status: ValidationStatus,
        failed_tests: List[str],
    ) -> Tuple[str, str]:
        """Generar recomendación y nivel de riesgo."""

        if status == ValidationStatus.PASSED:
            recommendation = "Estrategia rentable y robusta. Considerar escalado gradual."
            risk_level = "low"
        elif status == ValidationStatus.WARNING:
            recommendation = (
                "Estrategia rentable con algunas áreas de mejora. Monitorear métricas críticas."
            )
            risk_level = "medium"
        else:
            recommendation = "Estrategia no rentable. Revisar parámetros y considerar optimización."
            risk_level = "high"

        # Recomendaciones específicas basadas en métricas
        if metrics.cost_impact_ratio > Decimal("0.5"):
            recommendation += " Costos operativos altos - optimizar ejecución."

        if metrics.max_drawdown > Decimal("20"):
            recommendation += " Drawdown alto - implementar stop-loss más agresivo."

        if metrics.win_rate < Decimal("40"):
            recommendation += " Tasa de ganancia baja - revisar criterios de entrada."

        return recommendation, risk_level


class ProfitabilityValidationService:
    """Servicio principal de validación de rentabilidad."""

    def __init__(self):
        self.calculator = ProfitabilityCalculator()
        self.validator = ProfitabilityValidator()
        self.config = get_config()

    def validate_strategy_profitability(self, request: ValidationRequest) -> ValidationResponse:
        """Validar rentabilidad de una estrategia específica."""

        logger.info(f"Validating profitability for strategy: {request.strategy_name}")

        # Usar criterios personalizados o por defecto
        criteria = request.criteria or ValidationCriteria()

        # Calcular capital final basado en trades
        final_capital = self._calculate_final_capital(request.initial_capital, request.trades_data)

        # Calcular métricas de rentabilidad
        metrics, cost_breakdown = self.calculator.calculate_metrics(
            request.trades_data, request.initial_capital, final_capital
        )

        # Validar contra criterios
        status, passed_tests, failed_tests, warnings = self.validator.validate_profitability(
            metrics, criteria
        )

        # Generar recomendación
        recommendation, risk_level = self.validator.generate_recommendation(
            metrics, status, failed_tests
        )

        # Crear validación
        validation = ProfitabilityValidation(
            strategy_name=request.strategy_name,
            period_start=request.period_start,
            period_end=request.period_end,
            initial_capital=request.initial_capital,
            final_capital=final_capital,
            metrics=metrics,
            cost_breakdown=cost_breakdown,
            criteria=criteria,
            status=status,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            warnings=warnings,
            is_profitable=metrics.net_profit > 0,
            recommendation=recommendation,
            risk_level=risk_level,
        )

        # Crear resumen
        summary = {
            "strategy": request.strategy_name,
            "period": f"{request.period_start} to {request.period_end}",
            "initial_capital": float(request.initial_capital),
            "final_capital": float(final_capital),
            "net_profit": float(metrics.net_profit),
            "profit_margin": float(metrics.profit_margin),
            "roi": float(metrics.return_on_investment),
            "win_rate": float(metrics.win_rate),
            "max_drawdown": float(metrics.max_drawdown),
            "status": status.value,
            "risk_level": risk_level,
        }

        # Generar recomendaciones y próximos pasos
        recommendations = self._generate_recommendations(validation)
        next_steps = self._generate_next_steps(validation)

        return ValidationResponse(
            validation=validation,
            summary=summary,
            recommendations=recommendations,
            next_steps=next_steps,
        )

    def compare_strategies(self, validations: List[ProfitabilityValidation]) -> StrategyComparison:
        """Comparar múltiples estrategias."""

        if not validations:
            raise ValueError("At least one validation is required for comparison")

        # Encontrar mejor y peor estrategia
        best_strategy = max(validations, key=lambda v: v.metrics.net_profit)
        worst_strategy = min(validations, key=lambda v: v.metrics.net_profit)

        # Calcular métricas promedio
        avg_metrics = self._calculate_average_metrics(validations)

        # Crear ranking
        ranking = self._create_strategy_ranking(validations)

        return StrategyComparison(
            strategies=validations,
            best_strategy=best_strategy.strategy_name,
            worst_strategy=worst_strategy.strategy_name,
            average_metrics=avg_metrics,
            ranking=ranking,
        )

    def analyze_historical_performance(
        self, strategy_name: str, validations: List[ProfitabilityValidation]
    ) -> HistoricalValidation:
        """Analizar rendimiento histórico de una estrategia."""

        if not validations:
            raise ValueError("At least one validation is required for historical analysis")

        # Análisis de tendencias
        trend_analysis = self._analyze_trends(validations)

        # Calcular score de estabilidad
        stability_score = self._calculate_stability_score(validations)

        # Determinar rating de consistencia
        consistency_rating = self._determine_consistency_rating(stability_score)

        return HistoricalValidation(
            strategy_name=strategy_name,
            validations=validations,
            trend_analysis=trend_analysis,
            stability_score=stability_score,
            consistency_rating=consistency_rating,
        )

    def generate_validation_report(
        self,
        validations: List[ProfitabilityValidation],
        include_comparison: bool = True,
        include_historical: bool = True,
    ) -> ValidationReport:
        """Generar reporte completo de validación."""

        # Comparación de estrategias
        strategy_comparison = None
        if include_comparison and len(validations) > 1:
            strategy_comparison = self.compare_strategies(validations)

        # Análisis histórico por estrategia
        historical_analysis = None
        if include_historical:
            strategy_groups = {}
            for validation in validations:
                if validation.strategy_name not in strategy_groups:
                    strategy_groups[validation.strategy_name] = []
                strategy_groups[validation.strategy_name].append(validation)

            # Crear análisis histórico para cada estrategia
            historical_analyses = []
            for strategy_name, strategy_validations in strategy_groups.items():
                if len(strategy_validations) > 1:
                    historical_analyses.append(
                        self.analyze_historical_performance(strategy_name, strategy_validations)
                    )

        # Evaluación general
        overall_assessment = self._generate_overall_assessment(validations)
        risk_assessment = self._generate_risk_assessment(validations)
        recommendations = self._generate_general_recommendations(validations)

        return ValidationReport(
            strategy_validations=validations,
            strategy_comparison=strategy_comparison,
            historical_analysis=historical_analysis,
            overall_assessment=overall_assessment,
            risk_assessment=risk_assessment,
            recommendations=recommendations,
        )

    def _calculate_final_capital(
        self, initial_capital: Decimal, trades_data: List[Dict[str, Any]]
    ) -> Decimal:
        """Calcular capital final basado en trades."""

        final_capital = initial_capital

        for trade in trades_data:
            pnl = trade.get("pnl", Decimal("0"))
            if isinstance(pnl, (int, float)):
                pnl = Decimal(str(pnl))
            final_capital += pnl

        return final_capital

    def _calculate_average_metrics(
        self, validations: List[ProfitabilityValidation]
    ) -> ProfitabilityMetrics:
        """Calcular métricas promedio de múltiples validaciones."""

        if not validations:
            raise ValueError("Cannot calculate average metrics for empty list")

        # Sumar todas las métricas
        total_gross_profit = sum(v.metrics.gross_profit for v in validations)
        total_net_profit = sum(v.metrics.net_profit for v in validations)
        total_costs = sum(v.metrics.total_costs for v in validations)
        total_profit_margin = sum(v.metrics.profit_margin for v in validations)
        total_roi = sum(v.metrics.return_on_investment for v in validations)
        total_max_drawdown = sum(v.metrics.max_drawdown for v in validations)
        total_win_rate = sum(v.metrics.win_rate for v in validations)
        total_profit_factor = sum(v.metrics.profit_factor for v in validations)
        total_cost_impact_ratio = sum(v.metrics.cost_impact_ratio for v in validations)

        # Calcular promedios
        count = len(validations)

        # Calcular Sharpe ratio promedio (solo si todos tienen valor)
        sharpe_ratios = [
            v.metrics.sharpe_ratio for v in validations if v.metrics.sharpe_ratio is not None
        ]
        avg_sharpe_ratio = (
            Decimal(str(statistics.mean([float(sr) for sr in sharpe_ratios])))
            if sharpe_ratios
            else None
        )

        return ProfitabilityMetrics(
            gross_profit=total_gross_profit / count,
            net_profit=total_net_profit / count,
            total_costs=total_costs / count,
            profit_margin=total_profit_margin / count,
            return_on_investment=total_roi / count,
            sharpe_ratio=avg_sharpe_ratio,
            max_drawdown=total_max_drawdown / count,
            win_rate=total_win_rate / count,
            profit_factor=total_profit_factor / count,
            cost_impact_ratio=total_cost_impact_ratio / count,
        )

    def _create_strategy_ranking(
        self, validations: List[ProfitabilityValidation]
    ) -> List[Dict[str, Any]]:
        """Crear ranking de estrategias."""

        # Ordenar por ganancia neta
        sorted_validations = sorted(validations, key=lambda v: v.metrics.net_profit, reverse=True)

        ranking = []
        for i, validation in enumerate(sorted_validations):
            ranking.append(
                {
                    "rank": i + 1,
                    "strategy_name": validation.strategy_name,
                    "net_profit": float(validation.metrics.net_profit),
                    "profit_margin": float(validation.metrics.profit_margin),
                    "roi": float(validation.metrics.return_on_investment),
                    "win_rate": float(validation.metrics.win_rate),
                    "max_drawdown": float(validation.metrics.max_drawdown),
                    "status": validation.status.value,
                    "risk_level": validation.risk_level,
                }
            )

        return ranking

    def _analyze_trends(self, validations: List[ProfitabilityValidation]) -> Dict[str, Any]:
        """Analizar tendencias en el rendimiento histórico."""

        if len(validations) < 2:
            return {"insufficient_data": True}

        # Ordenar por fecha
        sorted_validations = sorted(validations, key=lambda v: v.validation_date)

        # Analizar tendencia de ganancia neta
        net_profits = [float(v.metrics.net_profit) for v in sorted_validations]
        profit_margins = [float(v.metrics.profit_margin) for v in sorted_validations]
        win_rates = [float(v.metrics.win_rate) for v in sorted_validations]

        # Calcular tendencias (simplificado)
        net_profit_trend = "improving" if net_profits[-1] > net_profits[0] else "declining"
        margin_trend = "improving" if profit_margins[-1] > profit_margins[0] else "declining"
        win_rate_trend = "improving" if win_rates[-1] > win_rates[0] else "declining"

        return {
            "net_profit_trend": net_profit_trend,
            "margin_trend": margin_trend,
            "win_rate_trend": win_rate_trend,
            "volatility": statistics.stdev(net_profits) if len(net_profits) > 1 else 0,
            "consistency": "high" if statistics.stdev(net_profits) < 100 else "low",
        }

    def _calculate_stability_score(self, validations: List[ProfitabilityValidation]) -> Decimal:
        """Calcular score de estabilidad (0-100)."""

        if len(validations) < 2:
            return Decimal("50")  # Score neutral para datos insuficientes

        # Calcular variabilidad en métricas clave
        net_profits = [float(v.metrics.net_profit) for v in validations]
        profit_margins = [float(v.metrics.profit_margin) for v in validations]

        # Score basado en consistencia (menor variabilidad = mayor score)
        net_profit_cv = (
            statistics.stdev(net_profits) / abs(statistics.mean(net_profits))
            if statistics.mean(net_profits) != 0
            else 1
        )
        margin_cv = (
            statistics.stdev(profit_margins) / abs(statistics.mean(profit_margins))
            if statistics.mean(profit_margins) != 0
            else 1
        )

        # Convertir a score (0-100)
        stability_score = max(0, min(100, 100 - (net_profit_cv + margin_cv) * 25))

        return Decimal(str(round(stability_score, 1)))

    def _determine_consistency_rating(self, stability_score: Decimal) -> str:
        """Determinar rating de consistencia basado en stability score."""

        if stability_score >= 80:
            return "excellent"
        elif stability_score >= 60:
            return "good"
        elif stability_score >= 40:
            return "fair"
        else:
            return "poor"

    def _generate_recommendations(self, validation: ProfitabilityValidation) -> List[str]:
        """Generar recomendaciones específicas para una validación."""

        recommendations = []

        if validation.metrics.cost_impact_ratio > Decimal("0.4"):
            recommendations.append(
                "Optimizar costos operativos - considerar ejecución más eficiente"
            )

        if validation.metrics.max_drawdown > Decimal("15"):
            recommendations.append("Implementar stop-loss más agresivo para reducir drawdown")

        if validation.metrics.win_rate < Decimal("45"):
            recommendations.append("Mejorar criterios de entrada para aumentar tasa de ganancia")

        if validation.metrics.profit_factor < Decimal("1.3"):
            recommendations.append("Revisar gestión de pérdidas para mejorar profit factor")

        if validation.status == ValidationStatus.PASSED:
            recommendations.append("Estrategia rentable - considerar escalado gradual")

        return recommendations

    def _generate_next_steps(self, validation: ProfitabilityValidation) -> List[str]:
        """Generar próximos pasos basados en la validación."""

        next_steps = []

        if validation.status == ValidationStatus.PASSED:
            next_steps.extend(
                [
                    "Proceder con paper trading extendido",
                    "Implementar monitoreo continuo de métricas",
                    "Considerar optimización de parámetros",
                    "Preparar para live trading con capital limitado",
                ]
            )
        elif validation.status == ValidationStatus.WARNING:
            next_steps.extend(
                [
                    "Revisar métricas con advertencias",
                    "Implementar mejoras específicas",
                    "Extender período de prueba",
                    "Monitorear métricas críticas",
                ]
            )
        else:
            next_steps.extend(
                [
                    "Revisar completamente la estrategia",
                    "Optimizar parámetros críticos",
                    "Considerar estrategias alternativas",
                    "No proceder con live trading",
                ]
            )

        return next_steps

    def _generate_overall_assessment(self, validations: List[ProfitabilityValidation]) -> str:
        """Generar evaluación general de todas las validaciones."""

        if not validations:
            return "No validations available for assessment"

        passed_count = sum(1 for v in validations if v.status == ValidationStatus.PASSED)
        total_count = len(validations)

        if passed_count == total_count:
            return "All strategies are profitable and meet validation criteria"
        elif passed_count > total_count // 2:
            return "Most strategies are profitable with some areas for improvement"
        else:
            return "Multiple strategies require optimization before proceeding"

    def _generate_risk_assessment(self, validations: List[ProfitabilityValidation]) -> str:
        """Generar evaluación de riesgo general."""

        if not validations:
            return "No validations available for risk assessment"

        high_risk_count = sum(1 for v in validations if v.risk_level == "high")
        total_count = len(validations)

        if high_risk_count == 0:
            return "Low overall risk - strategies are well-validated"
        elif high_risk_count < total_count // 2:
            return "Moderate risk - some strategies require attention"
        else:
            return "High risk - multiple strategies need significant optimization"

    def _generate_general_recommendations(
        self, validations: List[ProfitabilityValidation]
    ) -> List[str]:
        """Generar recomendaciones generales."""

        recommendations = []

        # Análisis de patrones comunes
        high_cost_strategies = [
            v for v in validations if v.metrics.cost_impact_ratio > Decimal("0.4")
        ]
        high_drawdown_strategies = [
            v for v in validations if v.metrics.max_drawdown > Decimal("15")
        ]
        low_win_rate_strategies = [v for v in validations if v.metrics.win_rate < Decimal("45")]

        if high_cost_strategies:
            recommendations.append("Optimizar costos operativos en múltiples estrategias")

        if high_drawdown_strategies:
            recommendations.append("Implementar gestión de riesgo más agresiva")

        if low_win_rate_strategies:
            recommendations.append(
                "Mejorar criterios de entrada en estrategias con baja tasa de ganancia"
            )

        # Recomendación general
        passed_count = sum(1 for v in validations if v.status == ValidationStatus.PASSED)
        if passed_count == len(validations):
            recommendations.append("Todas las estrategias están validadas - proceder con confianza")
        else:
            recommendations.append("Implementar mejoras antes de proceder con live trading")

        return recommendations
