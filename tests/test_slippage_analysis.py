"""
Tests for Dynamic Slippage Analysis
TASK-11: Análisis Dinámico de Slippage

Tests comprehensivos para el sistema de análisis de slippage dinámico.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from typing import List

from app.models.slippage_analysis import (
    DynamicSlippageAnalysis,
    SlippageComponent,
    SlippageType,
    MarketCondition,
    VolatilityMetrics,
    LiquidityMetrics,
    OrderSizeImpact,
    SlippageCalculationParams,
    SlippageHistory
)
from app.services.slippage_analysis_service import (
    DynamicSlippageService,
    VolatilityCalculator,
    LiquidityCalculator,
    OrderSizeCalculator
)
from app.models.market_data import Quote


class TestSlippageModels:
    """Tests para los modelos de slippage."""
    
    def test_slippage_component_creation(self):
        """Test creación de componente de slippage."""
        component = SlippageComponent(
            slippage_type=SlippageType.MARKET_IMPACT,
            value=Decimal('0.5'),
            confidence=0.8,
            market_condition=MarketCondition.NORMAL,
            calculation_method="test_method"
        )
        
        assert component.slippage_type == SlippageType.MARKET_IMPACT
        assert component.value == Decimal('0.5')
        assert component.confidence == 0.8
        assert component.market_condition == MarketCondition.NORMAL
    
    def test_slippage_component_validation(self):
        """Test validación de componente de slippage."""
        # Test valor máximo
        with pytest.raises(ValueError, match="Slippage value cannot exceed 10%"):
            SlippageComponent(
                slippage_type=SlippageType.MARKET_IMPACT,
                value=Decimal('15.0'),  # Excede 10%
                confidence=0.8,
                market_condition=MarketCondition.NORMAL,
                calculation_method="test_method"
            )
    
    def test_volatility_metrics_creation(self):
        """Test creación de métricas de volatilidad."""
        metrics = VolatilityMetrics(
            current_volatility=Decimal('25.0'),
            historical_volatility=Decimal('20.0'),
            volatility_percentile=75.0,
            volatility_trend="increasing",
            volatility_regime=MarketCondition.HIGH_VOLATILITY
        )
        
        assert metrics.current_volatility == Decimal('25.0')
        assert metrics.historical_volatility == Decimal('20.0')
        assert metrics.volatility_percentile == 75.0
        assert metrics.volatility_trend == "increasing"
        assert metrics.volatility_regime == MarketCondition.HIGH_VOLATILITY
    
    def test_liquidity_metrics_creation(self):
        """Test creación de métricas de liquidez."""
        metrics = LiquidityMetrics(
            bid_ask_spread=Decimal('0.5'),
            volume_24h=Decimal('1000000'),
            order_book_depth=Decimal('500000'),
            liquidity_score=0.8,
            liquidity_regime=MarketCondition.NORMAL
        )
        
        assert metrics.bid_ask_spread == Decimal('0.5')
        assert metrics.volume_24h == Decimal('1000000')
        assert metrics.liquidity_score == 0.8
    
    def test_order_size_impact_creation(self):
        """Test creación de impacto de tamaño de orden."""
        impact = OrderSizeImpact(
            order_size=Decimal('10000'),
            market_cap_ratio=Decimal('0.001'),
            impact_multiplier=1.2
        )
        
        assert impact.order_size == Decimal('10000')
        assert impact.market_cap_ratio == Decimal('0.001')
        assert impact.impact_multiplier == 1.2
    
    def test_dynamic_slippage_analysis_creation(self):
        """Test creación de análisis de slippage dinámico."""
        volatility_metrics = VolatilityMetrics(
            current_volatility=Decimal('25.0'),
            historical_volatility=Decimal('20.0'),
            volatility_percentile=75.0,
            volatility_trend="increasing",
            volatility_regime=MarketCondition.HIGH_VOLATILITY
        )
        
        liquidity_metrics = LiquidityMetrics(
            bid_ask_spread=Decimal('0.5'),
            volume_24h=Decimal('1000000'),
            order_book_depth=Decimal('500000'),
            liquidity_score=0.8,
            liquidity_regime=MarketCondition.NORMAL
        )
        
        order_size_impact = OrderSizeImpact(
            order_size=Decimal('10000'),
            market_cap_ratio=Decimal('0.001'),
            impact_multiplier=1.2
        )
        
        analysis = DynamicSlippageAnalysis(
            asset_symbol="AAPL",
            base_price=Decimal('150.0'),
            order_side="buy",
            order_size=Decimal('10000'),
            volatility_metrics=volatility_metrics,
            liquidity_metrics=liquidity_metrics,
            order_size_impact=order_size_impact,
            slippage_components=[],
            total_slippage=Decimal('1.5'),
            slippage_confidence=0.8,
            market_condition=MarketCondition.HIGH_VOLATILITY
        )
        
        assert analysis.asset_symbol == "AAPL"
        assert analysis.base_price == Decimal('150.0')
        assert analysis.total_slippage == Decimal('1.5')
        assert analysis.slippage_confidence == 0.8
    
    def test_slippage_analysis_methods(self):
        """Test métodos del análisis de slippage."""
        analysis = DynamicSlippageAnalysis(
            asset_symbol="AAPL",
            base_price=Decimal('150.0'),
            order_side="buy",
            order_size=Decimal('10000'),
            volatility_metrics=VolatilityMetrics(
                current_volatility=Decimal('25.0'),
                historical_volatility=Decimal('20.0'),
                volatility_percentile=75.0,
                volatility_trend="increasing",
                volatility_regime=MarketCondition.HIGH_VOLATILITY
            ),
            liquidity_metrics=LiquidityMetrics(
                bid_ask_spread=Decimal('0.5'),
                volume_24h=Decimal('1000000'),
                order_book_depth=Decimal('500000'),
                liquidity_score=0.8,
                liquidity_regime=MarketCondition.NORMAL
            ),
            order_size_impact=OrderSizeImpact(
                order_size=Decimal('10000'),
                market_cap_ratio=Decimal('0.001'),
                impact_multiplier=1.2
            ),
            slippage_components=[],
            total_slippage=Decimal('1.5'),
            slippage_confidence=0.8,
            market_condition=MarketCondition.HIGH_VOLATILITY
        )
        
        # Test precio ajustado
        adjusted_price = analysis.get_adjusted_price()
        expected_price = Decimal('150.0') * (1 + Decimal('1.5') / Decimal('100'))
        assert adjusted_price == expected_price
        
        # Test costo de slippage
        slippage_cost = analysis.get_slippage_cost()
        expected_cost = Decimal('150.0') * Decimal('10000') * Decimal('1.5') / Decimal('100')
        assert slippage_cost == expected_cost


class TestVolatilityCalculator:
    """Tests para el calculador de volatilidad."""
    
    def test_volatility_calculation(self):
        """Test cálculo de volatilidad."""
        calculator = VolatilityCalculator(lookback_days=30)
        
        # Crear historial de precios con volatilidad conocida
        prices = [Decimal('100.0')]
        for i in range(29):
            # Simular volatilidad del 20% anual
            variation = Decimal('0.02') if i % 2 == 0 else Decimal('-0.02')
            new_price = prices[-1] * (1 + variation)
            prices.append(new_price)
        
        metrics = calculator.calculate_volatility(prices)
        
        assert isinstance(metrics, VolatilityMetrics)
        assert metrics.current_volatility > Decimal('0')
        assert metrics.historical_volatility > Decimal('0')
        assert 0 <= metrics.volatility_percentile <= 100
        assert metrics.volatility_trend in ["increasing", "decreasing", "stable", "insufficient_data"]
        assert metrics.volatility_regime in MarketCondition
    
    def test_volatility_calculation_insufficient_data(self):
        """Test cálculo con datos insuficientes."""
        calculator = VolatilityCalculator(lookback_days=30)
        
        with pytest.raises(ValueError, match="Insufficient price history"):
            calculator.calculate_volatility([Decimal('100.0')])
    
    def test_volatility_regime_determination(self):
        """Test determinación de régimen de volatilidad."""
        calculator = VolatilityCalculator()
        
        # Test volatilidad normal
        regime = calculator._determine_volatility_regime(Decimal('20.0'))
        assert regime == MarketCondition.NORMAL
        
        # Test volatilidad alta
        regime = calculator._determine_volatility_regime(Decimal('35.0'))
        assert regime == MarketCondition.HIGH_VOLATILITY
        
        # Test volatilidad extrema
        regime = calculator._determine_volatility_regime(Decimal('55.0'))
        assert regime == MarketCondition.EXTREME_EVENTS


class TestLiquidityCalculator:
    """Tests para el calculador de liquidez."""
    
    def test_liquidity_calculation(self):
        """Test cálculo de liquidez."""
        calculator = LiquidityCalculator()
        
        quote = Quote(
            symbol="AAPL",
            last=Decimal('150.0'),
            bid=Decimal('149.9'),
            ask=Decimal('150.1'),
            volume=Decimal('1000000'),
            timestamp=datetime.now()
        )
        
        metrics = calculator.calculate_liquidity(
            quote=quote,
            volume_24h=Decimal('1000000'),
            order_book_depth=Decimal('500000')
        )
        
        assert isinstance(metrics, LiquidityMetrics)
        assert metrics.bid_ask_spread > Decimal('0')
        assert metrics.volume_24h == Decimal('1000000')
        assert metrics.order_book_depth == Decimal('500000')
        assert 0 <= metrics.liquidity_score <= 1
        assert metrics.liquidity_regime in MarketCondition
    
    def test_liquidity_score_calculation(self):
        """Test cálculo de score de liquidez."""
        calculator = LiquidityCalculator()
        
        # Test con spread bajo y volumen alto
        score = calculator._calculate_liquidity_score(
            spread=Decimal('0.1'),
            volume=Decimal('2000000'),
            depth=Decimal('1000000')
        )
        assert score > 0.8
        
        # Test con spread alto y volumen bajo
        score = calculator._calculate_liquidity_score(
            spread=Decimal('5.0'),
            volume=Decimal('100000'),
            depth=Decimal('50000')
        )
        assert score < 0.5


class TestOrderSizeCalculator:
    """Tests para el calculador de impacto de tamaño de orden."""
    
    def test_order_impact_calculation(self):
        """Test cálculo de impacto de orden."""
        calculator = OrderSizeCalculator()
        
        impact = calculator.calculate_order_impact(
            order_size=Decimal('10000'),
            market_cap=Decimal('1000000000'),
            current_price=Decimal('100.0')
        )
        
        assert isinstance(impact, OrderSizeImpact)
        assert impact.order_size == Decimal('10000')
        assert impact.market_cap_ratio == Decimal('0.00001')
        assert impact.impact_multiplier >= 1.0
    
    def test_impact_multiplier_calculation(self):
        """Test cálculo de multiplicador de impacto."""
        calculator = OrderSizeCalculator()
        
        # Test orden pequeña
        multiplier = calculator._calculate_impact_multiplier(Decimal('0.0005'))
        assert multiplier == 1.0
        
        # Test orden grande
        multiplier = calculator._calculate_impact_multiplier(Decimal('0.02'))
        assert multiplier > 1.0


class TestDynamicSlippageService:
    """Tests para el servicio de slippage dinámico."""
    
    def test_service_initialization(self):
        """Test inicialización del servicio."""
        service = DynamicSlippageService()
        
        assert isinstance(service.params, SlippageCalculationParams)
        assert isinstance(service.volatility_calculator, VolatilityCalculator)
        assert isinstance(service.liquidity_calculator, LiquidityCalculator)
        assert isinstance(service.order_size_calculator, OrderSizeCalculator)
        assert isinstance(service.slippage_history, dict)
    
    def test_dynamic_slippage_calculation(self):
        """Test cálculo de slippage dinámico completo."""
        service = DynamicSlippageService()
        
        # Crear datos de prueba
        quote = Quote(
            symbol="AAPL",
            last=Decimal('150.0'),
            bid=Decimal('149.9'),
            ask=Decimal('150.1'),
            volume=Decimal('1000000'),
            timestamp=datetime.now()
        )
        
        price_history = [Decimal('150.0')] * 30  # Precio estable
        
        analysis = service.calculate_dynamic_slippage(
            asset_symbol="AAPL",
            base_price=Decimal('150.0'),
            order_side="buy",
            order_size=Decimal('10000'),
            quote=quote,
            price_history=price_history,
            volume_24h=Decimal('1000000'),
            order_book_depth=Decimal('500000'),
            market_cap=Decimal('1000000000')
        )
        
        assert isinstance(analysis, DynamicSlippageAnalysis)
        assert analysis.asset_symbol == "AAPL"
        assert analysis.base_price == Decimal('150.0')
        assert analysis.total_slippage >= Decimal('0')
        assert analysis.slippage_confidence > 0
        assert len(analysis.slippage_components) > 0
    
    def test_slippage_history_management(self):
        """Test gestión del historial de slippage."""
        service = DynamicSlippageService()
        
        # Crear análisis de prueba
        analysis = DynamicSlippageAnalysis(
            asset_symbol="AAPL",
            base_price=Decimal('150.0'),
            order_side="buy",
            order_size=Decimal('10000'),
            volatility_metrics=VolatilityMetrics(
                current_volatility=Decimal('25.0'),
                historical_volatility=Decimal('20.0'),
                volatility_percentile=75.0,
                volatility_trend="increasing",
                volatility_regime=MarketCondition.HIGH_VOLATILITY
            ),
            liquidity_metrics=LiquidityMetrics(
                bid_ask_spread=Decimal('0.5'),
                volume_24h=Decimal('1000000'),
                order_book_depth=Decimal('500000'),
                liquidity_score=0.8,
                liquidity_regime=MarketCondition.NORMAL
            ),
            order_size_impact=OrderSizeImpact(
                order_size=Decimal('10000'),
                market_cap_ratio=Decimal('0.001'),
                impact_multiplier=1.2
            ),
            slippage_components=[],
            total_slippage=Decimal('1.5'),
            slippage_confidence=0.8,
            market_condition=MarketCondition.HIGH_VOLATILITY
        )
        
        # Test agregar al historial
        service._add_to_history(analysis)
        
        history = service.get_slippage_history("AAPL")
        assert history is not None
        assert history.asset_symbol == "AAPL"
        assert len(history.analyses) == 1
        
        # Test obtener análisis más reciente
        latest = history.get_latest_analysis()
        assert latest is not None
        assert latest.asset_symbol == "AAPL"
    
    def test_average_slippage_calculation(self):
        """Test cálculo de slippage promedio."""
        service = DynamicSlippageService()
        
        # Crear múltiples análisis
        for i in range(5):
            analysis = DynamicSlippageAnalysis(
                asset_symbol="AAPL",
                base_price=Decimal('150.0'),
                order_side="buy",
                order_size=Decimal('10000'),
                volatility_metrics=VolatilityMetrics(
                    current_volatility=Decimal('25.0'),
                    historical_volatility=Decimal('20.0'),
                    volatility_percentile=75.0,
                    volatility_trend="increasing",
                    volatility_regime=MarketCondition.HIGH_VOLATILITY
                ),
                liquidity_metrics=LiquidityMetrics(
                    bid_ask_spread=Decimal('0.5'),
                    volume_24h=Decimal('1000000'),
                    order_book_depth=Decimal('500000'),
                    liquidity_score=0.8,
                    liquidity_regime=MarketCondition.NORMAL
                ),
                order_size_impact=OrderSizeImpact(
                    order_size=Decimal('10000'),
                    market_cap_ratio=Decimal('0.001'),
                    impact_multiplier=1.2
                ),
                slippage_components=[],
                total_slippage=Decimal('1.5'),
                slippage_confidence=0.8,
                market_condition=MarketCondition.HIGH_VOLATILITY,
                calculation_timestamp=datetime.now() - timedelta(days=i)
            )
            service._add_to_history(analysis)
        
        # Test promedio de últimos 7 días
        avg_slippage = service.get_average_slippage("AAPL", days=7)
        assert avg_slippage is not None
        assert avg_slippage == Decimal('1.5')


class TestSlippageCalculationParams:
    """Tests para parámetros de cálculo de slippage."""
    
    def test_params_creation(self):
        """Test creación de parámetros."""
        params = SlippageCalculationParams()
        
        assert params.volatility_lookback_days == 30
        assert params.volatility_threshold_high == Decimal('30.0')
        assert params.volatility_threshold_extreme == Decimal('50.0')
        assert params.min_liquidity_score == 0.3
        assert params.max_spread_threshold == Decimal('2.0')
        assert params.max_order_size_ratio == Decimal('0.05')
        assert params.base_slippage == Decimal('0.1')
    
    def test_params_validation(self):
        """Test validación de parámetros."""
        with pytest.raises(ValueError, match="Extreme threshold must be greater than high threshold"):
            SlippageCalculationParams(
                volatility_threshold_high=Decimal('50.0'),
                volatility_threshold_extreme=Decimal('30.0')  # Menor que high
            )


class TestSlippageHistory:
    """Tests para historial de slippage."""
    
    def test_history_creation(self):
        """Test creación de historial."""
        history = SlippageHistory(asset_symbol="AAPL")
        
        assert history.asset_symbol == "AAPL"
        assert len(history.analyses) == 0
        assert isinstance(history.created_at, datetime)
        assert isinstance(history.updated_at, datetime)
    
    def test_add_analysis(self):
        """Test agregar análisis al historial."""
        history = SlippageHistory(asset_symbol="AAPL")
        
        analysis = DynamicSlippageAnalysis(
            asset_symbol="AAPL",
            base_price=Decimal('150.0'),
            order_side="buy",
            order_size=Decimal('10000'),
            volatility_metrics=VolatilityMetrics(
                current_volatility=Decimal('25.0'),
                historical_volatility=Decimal('20.0'),
                volatility_percentile=75.0,
                volatility_trend="increasing",
                volatility_regime=MarketCondition.HIGH_VOLATILITY
            ),
            liquidity_metrics=LiquidityMetrics(
                bid_ask_spread=Decimal('0.5'),
                volume_24h=Decimal('1000000'),
                order_book_depth=Decimal('500000'),
                liquidity_score=0.8,
                liquidity_regime=MarketCondition.NORMAL
            ),
            order_size_impact=OrderSizeImpact(
                order_size=Decimal('10000'),
                market_cap_ratio=Decimal('0.001'),
                impact_multiplier=1.2
            ),
            slippage_components=[],
            total_slippage=Decimal('1.5'),
            slippage_confidence=0.8,
            market_condition=MarketCondition.HIGH_VOLATILITY
        )
        
        history.add_analysis(analysis)
        
        assert len(history.analyses) == 1
        assert history.analyses[0] == analysis
    
    def test_get_latest_analysis(self):
        """Test obtener análisis más reciente."""
        history = SlippageHistory(asset_symbol="AAPL")
        
        # Agregar análisis con timestamps diferentes
        analysis1 = DynamicSlippageAnalysis(
            asset_symbol="AAPL",
            base_price=Decimal('150.0'),
            order_side="buy",
            order_size=Decimal('10000'),
            volatility_metrics=VolatilityMetrics(
                current_volatility=Decimal('25.0'),
                historical_volatility=Decimal('20.0'),
                volatility_percentile=75.0,
                volatility_trend="increasing",
                volatility_regime=MarketCondition.HIGH_VOLATILITY
            ),
            liquidity_metrics=LiquidityMetrics(
                bid_ask_spread=Decimal('0.5'),
                volume_24h=Decimal('1000000'),
                order_book_depth=Decimal('500000'),
                liquidity_score=0.8,
                liquidity_regime=MarketCondition.NORMAL
            ),
            order_size_impact=OrderSizeImpact(
                order_size=Decimal('10000'),
                market_cap_ratio=Decimal('0.001'),
                impact_multiplier=1.2
            ),
            slippage_components=[],
            total_slippage=Decimal('1.5'),
            slippage_confidence=0.8,
            market_condition=MarketCondition.HIGH_VOLATILITY,
            calculation_timestamp=datetime.now() - timedelta(hours=1)
        )
        
        analysis2 = DynamicSlippageAnalysis(
            asset_symbol="AAPL",
            base_price=Decimal('150.0'),
            order_side="buy",
            order_size=Decimal('10000'),
            volatility_metrics=VolatilityMetrics(
                current_volatility=Decimal('25.0'),
                historical_volatility=Decimal('20.0'),
                volatility_percentile=75.0,
                volatility_trend="increasing",
                volatility_regime=MarketCondition.HIGH_VOLATILITY
            ),
            liquidity_metrics=LiquidityMetrics(
                bid_ask_spread=Decimal('0.5'),
                volume_24h=Decimal('1000000'),
                order_book_depth=Decimal('500000'),
                liquidity_score=0.8,
                liquidity_regime=MarketCondition.NORMAL
            ),
            order_size_impact=OrderSizeImpact(
                order_size=Decimal('10000'),
                market_cap_ratio=Decimal('0.001'),
                impact_multiplier=1.2
            ),
            slippage_components=[],
            total_slippage=Decimal('2.0'),
            slippage_confidence=0.8,
            market_condition=MarketCondition.HIGH_VOLATILITY,
            calculation_timestamp=datetime.now()
        )
        
        history.add_analysis(analysis1)
        history.add_analysis(analysis2)
        
        latest = history.get_latest_analysis()
        assert latest is not None
        assert latest.total_slippage == Decimal('2.0')  # El más reciente
    
    def test_get_average_slippage(self):
        """Test obtener slippage promedio."""
        history = SlippageHistory(asset_symbol="AAPL")
        
        # Agregar análisis con diferentes slippages
        slippages = [Decimal('1.0'), Decimal('1.5'), Decimal('2.0')]
        
        for i, slippage in enumerate(slippages):
            analysis = DynamicSlippageAnalysis(
                asset_symbol="AAPL",
                base_price=Decimal('150.0'),
                order_side="buy",
                order_size=Decimal('10000'),
                volatility_metrics=VolatilityMetrics(
                    current_volatility=Decimal('25.0'),
                    historical_volatility=Decimal('20.0'),
                    volatility_percentile=75.0,
                    volatility_trend="increasing",
                    volatility_regime=MarketCondition.HIGH_VOLATILITY
                ),
                liquidity_metrics=LiquidityMetrics(
                    bid_ask_spread=Decimal('0.5'),
                    volume_24h=Decimal('1000000'),
                    order_book_depth=Decimal('500000'),
                    liquidity_score=0.8,
                    liquidity_regime=MarketCondition.NORMAL
                ),
                order_size_impact=OrderSizeImpact(
                    order_size=Decimal('10000'),
                    market_cap_ratio=Decimal('0.001'),
                    impact_multiplier=1.2
                ),
                slippage_components=[],
                total_slippage=slippage,
                slippage_confidence=0.8,
                market_condition=MarketCondition.HIGH_VOLATILITY,
                calculation_timestamp=datetime.now() - timedelta(days=i)
            )
            history.add_analysis(analysis)
        
        avg_slippage = history.get_average_slippage(days=7)
        assert avg_slippage is not None
        assert avg_slippage == Decimal('1.5')  # Promedio de 1.0, 1.5, 2.0
    
    def test_get_slippage_trend(self):
        """Test obtener tendencia de slippage."""
        history = SlippageHistory(asset_symbol="AAPL")
        
        # Agregar análisis con tendencia creciente
        analysis1 = DynamicSlippageAnalysis(
            asset_symbol="AAPL",
            base_price=Decimal('150.0'),
            order_side="buy",
            order_size=Decimal('10000'),
            volatility_metrics=VolatilityMetrics(
                current_volatility=Decimal('25.0'),
                historical_volatility=Decimal('20.0'),
                volatility_percentile=75.0,
                volatility_trend="increasing",
                volatility_regime=MarketCondition.HIGH_VOLATILITY
            ),
            liquidity_metrics=LiquidityMetrics(
                bid_ask_spread=Decimal('0.5'),
                volume_24h=Decimal('1000000'),
                order_book_depth=Decimal('500000'),
                liquidity_score=0.8,
                liquidity_regime=MarketCondition.NORMAL
            ),
            order_size_impact=OrderSizeImpact(
                order_size=Decimal('10000'),
                market_cap_ratio=Decimal('0.001'),
                impact_multiplier=1.2
            ),
            slippage_components=[],
            total_slippage=Decimal('1.0'),
            slippage_confidence=0.8,
            market_condition=MarketCondition.HIGH_VOLATILITY,
            calculation_timestamp=datetime.now() - timedelta(hours=1)
        )
        
        analysis2 = DynamicSlippageAnalysis(
            asset_symbol="AAPL",
            base_price=Decimal('150.0'),
            order_side="buy",
            order_size=Decimal('10000'),
            volatility_metrics=VolatilityMetrics(
                current_volatility=Decimal('25.0'),
                historical_volatility=Decimal('20.0'),
                volatility_percentile=75.0,
                volatility_trend="increasing",
                volatility_regime=MarketCondition.HIGH_VOLATILITY
            ),
            liquidity_metrics=LiquidityMetrics(
                bid_ask_spread=Decimal('0.5'),
                volume_24h=Decimal('1000000'),
                order_book_depth=Decimal('500000'),
                liquidity_score=0.8,
                liquidity_regime=MarketCondition.NORMAL
            ),
            order_size_impact=OrderSizeImpact(
                order_size=Decimal('10000'),
                market_cap_ratio=Decimal('0.001'),
                impact_multiplier=1.2
            ),
            slippage_components=[],
            total_slippage=Decimal('1.5'),
            slippage_confidence=0.8,
            market_condition=MarketCondition.HIGH_VOLATILITY,
            calculation_timestamp=datetime.now()
        )
        
        history.add_analysis(analysis1)
        history.add_analysis(analysis2)
        
        trend = history.get_slippage_trend()
        assert trend == "increasing"
        
        # Test con datos insuficientes
        history_empty = SlippageHistory(asset_symbol="AAPL")
        trend_empty = history_empty.get_slippage_trend()
        assert trend_empty == "insufficient_data"
