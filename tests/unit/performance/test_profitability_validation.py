"""
Tests comprehensivos para el sistema de validación de rentabilidad.

Este módulo contiene tests para validar que las estrategias generen
rentabilidad neta positiva después de todos los costos operativos.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.presentation.api.profitability_validation import router
from app.models.profitability_validation import (
    CostBreakdown,
    HistoricalValidation,
    ProfitabilityMetrics,
    ProfitabilityValidation,
    StrategyComparison,
    ValidationCriteria,
    ValidationRequest,
    ValidationResponse,
    ValidationStatus,
)
from app.services.profitability_validation_service import (
    ProfitabilityCalculator,
    ProfitabilityValidationService,
    ProfitabilityValidator,
)


class TestCostBreakdown:
    """Tests para el modelo CostBreakdown."""

    def test_cost_breakdown_creation(self):
        """Test creación de desglose de costos."""
        breakdown = CostBreakdown(
            commissions=Decimal("50.0"),
            slippage=Decimal("25.0"),
            market_impact=Decimal("15.0"),
            infrastructure=Decimal("10.0"),
            data_fees=Decimal("5.0"),
            financing=Decimal("2.0"),
            other=Decimal("3.0"),
        )
        assert breakdown.commissions == Decimal("50.0")
        assert breakdown.slippage == Decimal("25.0")
        assert breakdown.total_costs == Decimal("110.0")

    def test_cost_breakdown_validation(self):
        """Test validación de costos negativos."""
        with pytest.raises(ValueError, match="Cost amounts must be non-negative"):
            CostBreakdown(
                commissions=Decimal("-10.0"),
                slippage=Decimal("25.0"),
                market_impact=Decimal("15.0"),
                infrastructure=Decimal("10.0"),
            )

    def test_cost_breakdown_defaults(self):
        """Test valores por defecto."""
        breakdown = CostBreakdown(
            commissions=Decimal("50.0"),
            slippage=Decimal("25.0"),
            market_impact=Decimal("15.0"),
            infrastructure=Decimal("10.0"),
        )
        assert breakdown.data_fees == Decimal("0")
        assert breakdown.financing == Decimal("0")
        assert breakdown.other == Decimal("0")


class TestProfitabilityMetrics:
    """Tests para el modelo ProfitabilityMetrics."""

    def test_profitability_metrics_creation(self):
        """Test creación de métricas de rentabilidad."""
        metrics = ProfitabilityMetrics(
            gross_profit=Decimal("1000.0"),
            net_profit=Decimal("800.0"),
            total_costs=Decimal("200.0"),
            profit_margin=Decimal("8.0"),
            return_on_investment=Decimal("8.0"),
            sharpe_ratio=Decimal("1.5"),
            max_drawdown=Decimal("5.0"),
            win_rate=Decimal("60.0"),
            profit_factor=Decimal("2.0"),
            cost_impact_ratio=Decimal("0.2"),
        )
        assert metrics.gross_profit == Decimal("1000.0")
        assert metrics.net_profit == Decimal("800.0")
        assert metrics.profit_margin == Decimal("8.0")

    def test_profitability_metrics_validation(self):
        """Test validación de porcentajes."""
        with pytest.raises(ValueError, match="Percentage values must be between -100 and 1000"):
            ProfitabilityMetrics(
                gross_profit=Decimal("1000.0"),
                net_profit=Decimal("800.0"),
                total_costs=Decimal("200.0"),
                profit_margin=Decimal("1500.0"),  # Invalid percentage
                return_on_investment=Decimal("8.0"),
                max_drawdown=Decimal("5.0"),
                win_rate=Decimal("60.0"),
                profit_factor=Decimal("2.0"),
                cost_impact_ratio=Decimal("0.2"),
            )


class TestValidationCriteria:
    """Tests para el modelo ValidationCriteria."""

    def test_validation_criteria_creation(self):
        """Test creación de criterios de validación."""
        criteria = ValidationCriteria(
            min_net_profit=Decimal("100.0"),
            min_profit_margin=Decimal("5.0"),
            min_roi=Decimal("10.0"),
            min_sharpe_ratio=Decimal("1.0"),
            max_drawdown_limit=Decimal("15.0"),
            min_win_rate=Decimal("50.0"),
            min_profit_factor=Decimal("1.5"),
            max_cost_impact_ratio=Decimal("0.3"),
        )
        assert criteria.min_net_profit == Decimal("100.0")
        assert criteria.min_profit_margin == Decimal("5.0")
        assert criteria.max_drawdown_limit == Decimal("15.0")

    def test_validation_criteria_defaults(self):
        """Test valores por defecto."""
        criteria = ValidationCriteria()

        assert criteria.min_net_profit == Decimal("100")
        assert criteria.min_profit_margin == Decimal("5")
        assert criteria.min_roi == Decimal("10")
        assert criteria.min_sharpe_ratio == Decimal("1.0")


class TestProfitabilityCalculator:
    """Tests para ProfitabilityCalculator."""

    def setup_method(self):
        """Setup para cada test."""
        self.calculator = ProfitabilityCalculator()

    def test_calculate_metrics_basic(self):
        """Test cálculo básico de métricas."""
        trades_data = [
            {"pnl": Decimal("100.0"), "timestamp": "2025-01-01"},
            {"pnl": Decimal("-50.0"), "timestamp": "2025-01-02"},
            {"pnl": Decimal("200.0"), "timestamp": "2025-01-03"},
        ]

        initial_capital = Decimal("10000.0")
        final_capital = Decimal("10250.0")

        metrics, cost_breakdown = self.calculator.calculate_metrics(
            trades_data, initial_capital, final_capital
        )
        assert metrics.gross_profit == Decimal("250.0")
        assert metrics.net_profit < Decimal("250.0")  # Debe ser menor debido a costos
        assert cost_breakdown.total_costs > Decimal("0")

    def test_calculate_trading_metrics(self):
        """Test cálculo de métricas de trading."""
        trades_data = [
            {"pnl": Decimal("100.0")},
            {"pnl": Decimal("-50.0")},
            {"pnl": Decimal("200.0")},
            {"pnl": Decimal("-25.0")},
        ]

        win_rate, profit_factor, max_drawdown = self.calculator._calculate_trading_metrics(
            trades_data, Decimal("10000.0")
        )
        assert win_rate == Decimal("50.0")  # 2 wins out of 4 trades
        assert profit_factor == Decimal("4.0")  # 300 / 75 (corregido)

    def test_calculate_max_drawdown(self):
        """Test cálculo de drawdown máximo."""
        trades_data = [
            {"pnl": Decimal("100.0"), "timestamp": "2025-01-01"},
            {"pnl": Decimal("-200.0"), "timestamp": "2025-01-02"},
            {"pnl": Decimal("50.0"), "timestamp": "2025-01-03"},
            {"pnl": Decimal("-150.0"), "timestamp": "2025-01-04"},
        ]

        max_drawdown = self.calculator._calculate_max_drawdown(trades_data, Decimal("10000.0"))
        # El drawdown máximo debería ser cuando el capital baja de 10100 a 9900
        assert max_drawdown > Decimal("0")

    def test_calculate_sharpe_ratio(self):
        """Test cálculo de Sharpe ratio."""
        trades_data = [
            {"pnl": Decimal("100.0")},
            {"pnl": Decimal("-50.0")},
            {"pnl": Decimal("200.0")},
            {"pnl": Decimal("-25.0")},
        ]

        sharpe_ratio = self.calculator._calculate_sharpe_ratio(trades_data)

        assert sharpe_ratio is not None
        assert isinstance(sharpe_ratio, Decimal)

    def test_calculate_sharpe_ratio_insufficient_data(self):
        """Test Sharpe ratio con datos insuficientes."""
        trades_data = [{"pnl": Decimal("100.0")}]

        sharpe_ratio = self.calculator._calculate_sharpe_ratio(trades_data)

        assert sharpe_ratio is None


class TestProfitabilityValidator:
    """Tests para ProfitabilityValidator."""

    def setup_method(self):
        """Setup para cada test."""
        self.validator = ProfitabilityValidator()

    def test_validate_profitability_passed(self):
        """Test validación exitosa."""
        metrics = ProfitabilityMetrics(
            gross_profit=Decimal("1000.0"),
            net_profit=Decimal("200.0"),
            total_costs=Decimal("800.0"),
            profit_margin=Decimal("10.0"),
            return_on_investment=Decimal("10.0"),
            sharpe_ratio=Decimal("1.5"),
            max_drawdown=Decimal("5.0"),
            win_rate=Decimal("60.0"),
            profit_factor=Decimal("2.0"),
            cost_impact_ratio=Decimal("0.2"),
        )
        criteria = ValidationCriteria()

        status, passed_tests, failed_tests, warnings = self.validator.validate_profitability(
            metrics, criteria
        )
        assert status == ValidationStatus.PASSED
        assert len(failed_tests) == 0
        assert len(passed_tests) > 0

    def test_validate_profitability_failed(self):
        """Test validación fallida."""
        metrics = ProfitabilityMetrics(
            gross_profit=Decimal("100.0"),
            net_profit=Decimal("50.0"),
            total_costs=Decimal("50.0"),
            profit_margin=Decimal("2.0"),  # Below minimum
            return_on_investment=Decimal("2.0"),  # Below minimum
            sharpe_ratio=Decimal("0.5"),  # Below minimum
            max_drawdown=Decimal("20.0"),  # Above maximum
            win_rate=Decimal("30.0"),  # Below minimum
            profit_factor=Decimal("1.0"),  # Below minimum
            cost_impact_ratio=Decimal("0.5"),  # Above maximum
        )
        criteria = ValidationCriteria()

        status, passed_tests, failed_tests, warnings = self.validator.validate_profitability(
            metrics, criteria
        )
        assert status == ValidationStatus.FAILED
        assert len(failed_tests) > 0

    def test_generate_recommendation_passed(self):
        """Test generación de recomendación para estrategia exitosa."""
        metrics = ProfitabilityMetrics(
            gross_profit=Decimal("1000.0"),
            net_profit=Decimal("200.0"),
            total_costs=Decimal("800.0"),
            profit_margin=Decimal("10.0"),
            return_on_investment=Decimal("10.0"),
            sharpe_ratio=Decimal("1.5"),
            max_drawdown=Decimal("5.0"),
            win_rate=Decimal("60.0"),
            profit_factor=Decimal("2.0"),
            cost_impact_ratio=Decimal("0.2"),
        )
        recommendation, risk_level = self.validator.generate_recommendation(
            metrics, ValidationStatus.PASSED, []
        )
        assert "rentable" in recommendation.lower()
        assert risk_level == "low"

    def test_generate_recommendation_failed(self):
        """Test generación de recomendación para estrategia fallida."""
        metrics = ProfitabilityMetrics(
            gross_profit=Decimal("100.0"),
            net_profit=Decimal("-50.0"),
            total_costs=Decimal("150.0"),
            profit_margin=Decimal("-5.0"),
            return_on_investment=Decimal("-5.0"),
            sharpe_ratio=Decimal("0.5"),
            max_drawdown=Decimal("25.0"),
            win_rate=Decimal("30.0"),
            profit_factor=Decimal("0.8"),
            cost_impact_ratio=Decimal("1.5"),
        )
        recommendation, risk_level = self.validator.generate_recommendation(
            metrics, ValidationStatus.FAILED, ["min_profit_margin", "min_roi"]
        )
        assert "no rentable" in recommendation.lower()
        assert risk_level == "high"


class TestProfitabilityValidationService:
    """Tests para ProfitabilityValidationService."""

    def setup_method(self):
        """Setup para cada test."""
        self.service = ProfitabilityValidationService()

    def test_validate_strategy_profitability(self):
        """Test validación completa de estrategia."""
        request = ValidationRequest(
            strategy_name="Test Strategy",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            initial_capital=Decimal("10000.0"),
            trades_data=[
                {"pnl": Decimal("100.0"), "timestamp": "2025-01-01"},
                {"pnl": Decimal("-50.0"), "timestamp": "2025-01-02"},
                {"pnl": Decimal("200.0"), "timestamp": "2025-01-03"},
            ],
        )
        result = self.service.validate_strategy_profitability(request)

        assert isinstance(result, ValidationResponse)
        assert result.validation.strategy_name == "Test Strategy"
        assert result.validation.initial_capital == Decimal("10000.0")
        assert result.validation.final_capital == Decimal("10250.0")
        assert result.validation.is_profitable is True

    def test_compare_strategies(self):
        """Test comparación de estrategias."""
        validation1 = ProfitabilityValidation(
            strategy_name="Strategy A",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            initial_capital=Decimal("10000.0"),
            final_capital=Decimal("11000.0"),
            metrics=ProfitabilityMetrics(
                gross_profit=Decimal("1000.0"),
                net_profit=Decimal("800.0"),
                total_costs=Decimal("200.0"),
                profit_margin=Decimal("8.0"),
                return_on_investment=Decimal("8.0"),
                sharpe_ratio=Decimal("1.5"),
                max_drawdown=Decimal("5.0"),
                win_rate=Decimal("60.0"),
                profit_factor=Decimal("2.0"),
                cost_impact_ratio=Decimal("0.2"),
            ),
            cost_breakdown=CostBreakdown(
                commissions=Decimal("100.0"),
                slippage=Decimal("50.0"),
                market_impact=Decimal("30.0"),
                infrastructure=Decimal("20.0"),
            ),
            criteria=ValidationCriteria(),
            status=ValidationStatus.PASSED,
            passed_tests=["min_net_profit", "min_profit_margin"],
            failed_tests=[],
            warnings=[],
            is_profitable=True,
            recommendation="Strategy is profitable",
            risk_level="low",
        )
        validation2 = ProfitabilityValidation(
            strategy_name="Strategy B",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            initial_capital=Decimal("10000.0"),
            final_capital=Decimal("10500.0"),
            metrics=ProfitabilityMetrics(
                gross_profit=Decimal("500.0"),
                net_profit=Decimal("300.0"),
                total_costs=Decimal("200.0"),
                profit_margin=Decimal("3.0"),
                return_on_investment=Decimal("3.0"),
                sharpe_ratio=Decimal("0.8"),
                max_drawdown=Decimal("8.0"),
                win_rate=Decimal("45.0"),
                profit_factor=Decimal("1.2"),
                cost_impact_ratio=Decimal("0.4"),
            ),
            cost_breakdown=CostBreakdown(
                commissions=Decimal("100.0"),
                slippage=Decimal("50.0"),
                market_impact=Decimal("30.0"),
                infrastructure=Decimal("20.0"),
            ),
            criteria=ValidationCriteria(),
            status=ValidationStatus.WARNING,
            passed_tests=["min_net_profit"],
            failed_tests=["min_profit_margin"],
            warnings=[],
            is_profitable=True,
            recommendation="Strategy needs improvement",
            risk_level="medium",
        )
        comparison = self.service.compare_strategies([validation1, validation2])

        assert isinstance(comparison, StrategyComparison)
        assert comparison.best_strategy == "Strategy A"
        assert comparison.worst_strategy == "Strategy B"
        assert len(comparison.ranking) == 2
        assert comparison.ranking[0]["strategy_name"] == "Strategy A"

    def test_analyze_historical_performance(self):
        """Test análisis de rendimiento histórico."""
        validations = [
            ProfitabilityValidation(
                strategy_name="Test Strategy",
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
                initial_capital=Decimal("10000.0"),
                final_capital=Decimal("10500.0"),
                metrics=ProfitabilityMetrics(
                    gross_profit=Decimal("500.0"),
                    net_profit=Decimal("400.0"),
                    total_costs=Decimal("100.0"),
                    profit_margin=Decimal("4.0"),
                    return_on_investment=Decimal("4.0"),
                    sharpe_ratio=Decimal("1.0"),
                    max_drawdown=Decimal("3.0"),
                    win_rate=Decimal("55.0"),
                    profit_factor=Decimal("1.5"),
                    cost_impact_ratio=Decimal("0.2"),
                ),
                cost_breakdown=CostBreakdown(
                    commissions=Decimal("50.0"),
                    slippage=Decimal("25.0"),
                    market_impact=Decimal("15.0"),
                    infrastructure=Decimal("10.0"),
                ),
                criteria=ValidationCriteria(),
                status=ValidationStatus.PASSED,
                passed_tests=["min_net_profit"],
                failed_tests=[],
                warnings=[],
                is_profitable=True,
                recommendation="Strategy is profitable",
                risk_level="low",
            ),
            ProfitabilityValidation(
                strategy_name="Test Strategy",
                period_start=date(2025, 2, 1),
                period_end=date(2025, 2, 28),
                initial_capital=Decimal("10500.0"),
                final_capital=Decimal("11000.0"),
                metrics=ProfitabilityMetrics(
                    gross_profit=Decimal("500.0"),
                    net_profit=Decimal("450.0"),
                    total_costs=Decimal("50.0"),
                    profit_margin=Decimal("4.3"),
                    return_on_investment=Decimal("4.3"),
                    sharpe_ratio=Decimal("1.2"),
                    max_drawdown=Decimal("2.5"),
                    win_rate=Decimal("60.0"),
                    profit_factor=Decimal("1.8"),
                    cost_impact_ratio=Decimal("0.1"),
                ),
                cost_breakdown=CostBreakdown(
                    commissions=Decimal("30.0"),
                    slippage=Decimal("15.0"),
                    market_impact=Decimal("5.0"),
                    infrastructure=Decimal("0.0"),
                ),
                criteria=ValidationCriteria(),
                status=ValidationStatus.PASSED,
                passed_tests=["min_net_profit"],
                failed_tests=[],
                warnings=[],
                is_profitable=True,
                recommendation="Strategy is profitable",
                risk_level="low",
            ),
        ]

        historical_analysis = self.service.analyze_historical_performance(
            "Test Strategy", validations
        )
        assert isinstance(historical_analysis, HistoricalValidation)
        assert historical_analysis.strategy_name == "Test Strategy"
        assert len(historical_analysis.validations) == 2
        assert historical_analysis.stability_score > Decimal("0")
        assert historical_analysis.consistency_rating in [
            "excellent",
            "good",
            "fair",
            "poor",
        ]


class TestProfitabilityValidationAPI:
    """Tests para la API de validación de rentabilidad."""

    def setup_method(self):
        """Setup para cada test."""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_validate_strategy_endpoint(self):
        """Test endpoint de validación de estrategia."""
        request_data = {
            "strategy_name": "Test Strategy",
            "period_start": "2025-01-01",
            "period_end": "2025-01-31",
            "initial_capital": 10000.0,
            "trades_data": [
                {"pnl": 100.0, "timestamp": "2025-01-01"},
                {"pnl": -50.0, "timestamp": "2025-01-02"},
                {"pnl": 200.0, "timestamp": "2025-01-03"},
            ],
        }

        with patch("app.api.profitability_validation.profitability_service") as mock_service:
            mock_response = ValidationResponse(
                validation=ProfitabilityValidation(
                    strategy_name="Test Strategy",
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 1, 31),
                    initial_capital=Decimal("10000.0"),
                    final_capital=Decimal("10250.0"),
                    metrics=ProfitabilityMetrics(
                        gross_profit=Decimal("250.0"),
                        net_profit=Decimal("190.0"),
                        total_costs=Decimal("60.0"),
                        profit_margin=Decimal("1.9"),
                        return_on_investment=Decimal("1.9"),
                        sharpe_ratio=Decimal("1.0"),
                        max_drawdown=Decimal("2.0"),
                        win_rate=Decimal("66.7"),
                        profit_factor=Decimal("2.0"),
                        cost_impact_ratio=Decimal("0.24"),
                    ),
                    cost_breakdown=CostBreakdown(
                        commissions=Decimal("25.0"),
                        slippage=Decimal("15.0"),
                        market_impact=Decimal("10.0"),
                        infrastructure=Decimal("5.0"),
                        data_fees=Decimal("2.0"),
                        financing=Decimal("1.0"),
                        other=Decimal("2.0"),
                    ),
                    criteria=ValidationCriteria(),
                    status=ValidationStatus.PASSED,
                    passed_tests=["min_net_profit"],
                    failed_tests=[],
                    warnings=[],
                    is_profitable=True,
                    recommendation="Strategy is profitable",
                    risk_level="low",
                ),
                summary={},
                recommendations=[],
                next_steps=[],
            )
            mock_service.validate_strategy_profitability.return_value = mock_response

            response = self.client.post("/api/v1/profitability/validate", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["validation"]["strategy_name"] == "Test Strategy"
            assert data["validation"]["is_profitable"] is True

    def test_validate_strategy_endpoint_invalid_data(self):
        """Test endpoint con datos inválidos."""
        request_data = {
            "strategy_name": "Test Strategy",
            "period_start": "2025-01-01",
            "period_end": "2025-01-31",
            "initial_capital": -1000.0,  # Invalid negative capital
            "trades_data": [],
        }

        response = self.client.post("/api/v1/profitability/validate", json=request_data)

        # FastAPI devuelve 422 para errores de validación
        assert response.status_code == 422

    def test_compare_strategies_endpoint(self):
        """Test endpoint de comparación de estrategias."""
        validations_data = [
            {
                "strategy_name": "Strategy A",
                "period_start": "2025-01-01",
                "period_end": "2025-01-31",
                "initial_capital": 10000.0,
                "final_capital": 11000.0,
                "metrics": {
                    "gross_profit": 1000.0,
                    "net_profit": 800.0,
                    "total_costs": 200.0,
                    "profit_margin": 8.0,
                    "return_on_investment": 8.0,
                    "sharpe_ratio": 1.5,
                    "max_drawdown": 5.0,
                    "win_rate": 60.0,
                    "profit_factor": 2.0,
                    "cost_impact_ratio": 0.2,
                },
                "cost_breakdown": {
                    "commissions": 100.0,
                    "slippage": 50.0,
                    "market_impact": 30.0,
                    "infrastructure": 20.0,
                    "data_fees": 0.0,
                    "financing": 0.0,
                    "other": 0.0,
                },
                "criteria": {},
                "status": "passed",
                "passed_tests": ["min_net_profit"],
                "failed_tests": [],
                "warnings": [],
                "is_profitable": True,
                "recommendation": "Strategy is profitable",
                "risk_level": "low",
            },
            {
                "strategy_name": "Strategy B",
                "period_start": "2025-01-01",
                "period_end": "2025-01-31",
                "initial_capital": 10000.0,
                "final_capital": 10500.0,
                "metrics": {
                    "gross_profit": 500.0,
                    "net_profit": 300.0,
                    "total_costs": 200.0,
                    "profit_margin": 3.0,
                    "return_on_investment": 3.0,
                    "sharpe_ratio": 0.8,
                    "max_drawdown": 8.0,
                    "win_rate": 45.0,
                    "profit_factor": 1.2,
                    "cost_impact_ratio": 0.4,
                },
                "cost_breakdown": {
                    "commissions": 100.0,
                    "slippage": 50.0,
                    "market_impact": 30.0,
                    "infrastructure": 20.0,
                    "data_fees": 0.0,
                    "financing": 0.0,
                    "other": 0.0,
                },
                "criteria": {},
                "status": "warning",
                "passed_tests": ["min_net_profit"],
                "failed_tests": ["min_profit_margin"],
                "warnings": [],
                "is_profitable": True,
                "recommendation": "Strategy needs improvement",
                "risk_level": "medium",
            },
        ]

        with patch("app.api.profitability_validation.profitability_service") as mock_service:
            mock_comparison = StrategyComparison(
                comparison_date=datetime.utcnow(),
                strategies=[],
                best_strategy="Strategy A",
                worst_strategy="Strategy A",
                average_metrics=ProfitabilityMetrics(
                    gross_profit=Decimal("1000.0"),
                    net_profit=Decimal("800.0"),
                    total_costs=Decimal("200.0"),
                    profit_margin=Decimal("8.0"),
                    return_on_investment=Decimal("8.0"),
                    sharpe_ratio=Decimal("1.5"),
                    max_drawdown=Decimal("5.0"),
                    win_rate=Decimal("60.0"),
                    profit_factor=Decimal("2.0"),
                    cost_impact_ratio=Decimal("0.2"),
                ),
                ranking=[],
            )
            mock_service.compare_strategies.return_value = mock_comparison

            response = self.client.post("/api/v1/profitability/compare", json=validations_data)

            assert response.status_code == 200
            data = response.json()
            assert data["best_strategy"] == "Strategy A"

    def test_health_check_endpoint(self):
        """Test endpoint de health check."""
        response = self.client.get("/api/v1/profitability/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "profitability-validation"

    def test_metrics_summary_endpoint(self):
        """Test endpoint de resumen de métricas."""
        response = self.client.get("/api/v1/profitability/metrics/summary")

        assert response.status_code == 200
        data = response.json()
        assert "profitability_metrics" in data
        assert "validation_criteria" in data
        assert "validation_statuses" in data
        assert "risk_levels" in data

    def test_default_criteria_endpoint(self):
        """Test endpoint de criterios por defecto."""
        response = self.client.get("/api/v1/profitability/criteria/default")

        assert response.status_code == 200
        data = response.json()
        assert "min_net_profit" in data
        assert "min_profit_margin" in data
        assert "min_roi" in data
        assert "max_drawdown_limit" in data


class TestIntegrationTests:
    """Tests de integración para el sistema completo."""

    def setup_method(self):
        """Setup para cada test."""
        self.service = ProfitabilityValidationService()

    def test_end_to_end_validation(self):
        """Test de validación completa de extremo a extremo."""
        # Datos de trades realistas
        trades_data = [
            {
                "pnl": Decimal("150.0"),
                "timestamp": "2025-01-01",
                "symbol": "AAPL",
                "quantity": 10,
            },
            {
                "pnl": Decimal("-75.0"),
                "timestamp": "2025-01-02",
                "symbol": "GOOGL",
                "quantity": 5,
            },
            {
                "pnl": Decimal("200.0"),
                "timestamp": "2025-01-03",
                "symbol": "MSFT",
                "quantity": 8,
            },
            {
                "pnl": Decimal("-50.0"),
                "timestamp": "2025-01-04",
                "symbol": "TSLA",
                "quantity": 3,
            },
            {
                "pnl": Decimal("100.0"),
                "timestamp": "2025-01-05",
                "symbol": "AMZN",
                "quantity": 2,
            },
        ]

        request = ValidationRequest(
            strategy_name="Momentum Strategy",
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            initial_capital=Decimal("50000.0"),
            trades_data=trades_data,
        )
        result = self.service.validate_strategy_profitability(request)

        # Verificar que la validación es completa
        assert result.validation.strategy_name == "Momentum Strategy"
        assert result.validation.initial_capital == Decimal("50000.0")
        assert result.validation.final_capital == Decimal("50325.0")  # 50000 + 325

        # Verificar métricas calculadas
        assert result.validation.metrics.gross_profit == Decimal("325.0")
        assert result.validation.metrics.net_profit < Decimal(
            "325.0"
        )  # Debe ser menor debido a costos

        # Verificar desglose de costos
        assert result.validation.cost_breakdown.total_costs > Decimal("0")

        # Verificar que se generaron recomendaciones
        assert len(result.next_steps) > 0  # next_steps sí se generan

    def test_multiple_strategies_comparison(self):
        """Test de comparación de múltiples estrategias."""
        # Crear validaciones para múltiples estrategias
        strategies = [
            {
                "name": "Momentum Strategy",
                "trades": [
                    {"pnl": Decimal("100.0"), "timestamp": "2025-01-01"},
                    {"pnl": Decimal("-50.0"), "timestamp": "2025-01-02"},
                    {"pnl": Decimal("200.0"), "timestamp": "2025-01-03"},
                ],
            },
            {
                "name": "Mean Reversion Strategy",
                "trades": [
                    {"pnl": Decimal("75.0"), "timestamp": "2025-01-01"},
                    {"pnl": Decimal("-25.0"), "timestamp": "2025-01-02"},
                    {"pnl": Decimal("150.0"), "timestamp": "2025-01-03"},
                ],
            },
            {
                "name": "Pairs Trading Strategy",
                "trades": [
                    {"pnl": Decimal("50.0"), "timestamp": "2025-01-01"},
                    {"pnl": Decimal("-30.0"), "timestamp": "2025-01-02"},
                    {"pnl": Decimal("100.0"), "timestamp": "2025-01-03"},
                ],
            },
        ]

        validations = []
        for strategy in strategies:
            request = ValidationRequest(
                strategy_name=strategy["name"],
                period_start=date(2025, 1, 1),
                period_end=date(2025, 1, 31),
                initial_capital=Decimal("10000.0"),
                trades_data=strategy["trades"],
            )
            result = self.service.validate_strategy_profitability(request)
            validations.append(result.validation)

        # Comparar estrategias
        comparison = self.service.compare_strategies(validations)

        # Verificar que la comparación es correcta
        assert len(comparison.strategies) == 3
        assert comparison.best_strategy in [
            "Momentum Strategy",
            "Mean Reversion Strategy",
            "Pairs Trading Strategy",
        ]
        assert len(comparison.ranking) == 3

        # Verificar que el ranking está ordenado correctamente
        for i in range(len(comparison.ranking) - 1):
            assert comparison.ranking[i]["net_profit"] >= comparison.ranking[i + 1]["net_profit"]

    def test_historical_analysis(self):
        """Test de análisis histórico de una estrategia."""
        # Crear validaciones históricas para la misma estrategia
        historical_validations = []

        for month in range(1, 4):  # 3 meses de datos
            trades_data = [
                {
                    "pnl": Decimal(f"{100 + month * 10}"),
                    "timestamp": f"2025-{month:02d}-01",
                },
                {
                    "pnl": Decimal(f"{-50 - month * 5}"),
                    "timestamp": f"2025-{month:02d}-15",
                },
                {
                    "pnl": Decimal(f"{200 + month * 20}"),
                    "timestamp": f"2025-{month:02d}-28",
                },
            ]

            request = ValidationRequest(
                strategy_name="Momentum Strategy",
                period_start=date(2025, month, 1),
                period_end=date(2025, month, 28),
                initial_capital=Decimal("10000.0"),
                trades_data=trades_data,
            )
            result = self.service.validate_strategy_profitability(request)
            historical_validations.append(result.validation)

        # Analizar rendimiento histórico
        historical_analysis = self.service.analyze_historical_performance(
            "Momentum Strategy", historical_validations
        )
        # Verificar que el análisis histórico es correcto
        assert historical_analysis.strategy_name == "Momentum Strategy"
        assert len(historical_analysis.validations) == 3
        assert historical_analysis.stability_score >= Decimal("0")
        assert historical_analysis.stability_score <= Decimal("100")
        assert historical_analysis.consistency_rating in [
            "excellent",
            "good",
            "fair",
            "poor",
        ]

        # Verificar que se analizaron las tendencias
        assert "net_profit_trend" in historical_analysis.trend_analysis
        assert "margin_trend" in historical_analysis.trend_analysis
        assert "win_rate_trend" in historical_analysis.trend_analysis
