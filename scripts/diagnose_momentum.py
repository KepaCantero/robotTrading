#!/usr/bin/env python3
"""
Script de diagnóstico completo para Momentum Strategy.

Ejecuta todos los tests y genera un reporte detallado de problemas.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# Agregar proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.strategies.momentum import MomentumStrategy
from app.models.market_data import Quote
from app.models.portfolio import Portfolio, Position
from app.models.signal import Signal, SignalType, SignalStrength, SignalSource
from app.models.portfolio import AssetClass


def test_signal_generation():
    """Test 1: Verificar generación de señales."""
    print("\n" + "="*80)
    print("TEST 1: Generación de Señales")
    print("="*80)
    
    config = {
        "rsi_threshold": 40,
        "momentum_threshold": 0.02,
        "volume_threshold": 1.0,
        "max_position_size": 0.1,
        "stop_loss": 0.05,
        "take_profit": 0.10,
    }
    strategy = MomentumStrategy(config)
    
    signals_generated = 0
    signals_by_type = {"BUY": 0, "SELL": 0}
    
    # Generar 50 días de datos
    for i in range(50):
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            open=Decimal("200") + Decimal(str(i * 0.1)),
            high=Decimal("202") + Decimal(str(i * 0.1)),
            low=Decimal("198") + Decimal(str(i * 0.1)),
            close=Decimal("200") + Decimal(str(i * 0.1)),
            last=Decimal("200") + Decimal(str(i * 0.1)),
            volume=Decimal("1000000") + Decimal(str(i * 10000)),
        )
        signals = strategy.generate_signals(quote)
        
        if signals:
            signals_generated += len(signals)
            for sig in signals:
                sig_type = sig.signal_type.value if hasattr(sig.signal_type, 'value') else str(sig.signal_type)
                signals_by_type[sig_type.upper()] += 1
    
    print(f"✅ Señales generadas: {signals_generated}")
    print(f"   - BUY: {signals_by_type['BUY']}")
    print(f"   - SELL: {signals_by_type['SELL']}")
    
    return signals_generated > 0, signals_generated, signals_by_type


def test_position_size_calculation():
    """Test 2: Verificar cálculo de tamaño de posición."""
    print("\n" + "="*80)
    print("TEST 2: Cálculo de Tamaño de Posición")
    print("="*80)
    
    config = {"max_position_size": Decimal("0.1")}
    strategy = MomentumStrategy(config)
    
    test_cases = [
        {
            "name": "Cash suficiente ($50k)",
            "cash": Decimal("50000"),
            "price": Decimal("200"),
            "expected_min": Decimal("20"),  # Al menos 20 acciones
        },
        {
            "name": "Cash bajo ($1k)",
            "cash": Decimal("1000"),
            "price": Decimal("200"),
            "expected_min": Decimal("1"),  # Mínimo 1 acción
        },
        {
            "name": "Cash muy alto ($100k)",
            "cash": Decimal("100000"),
            "price": Decimal("200"),
            "expected_min": Decimal("40"),  # Al menos 40 acciones
        },
    ]
    
    all_passed = True
    for case in test_cases:
        portfolio = Portfolio(
            portfolio_id="test",
            cash=case["cash"],
            positions=[],
            timestamp=datetime.utcnow(),
        )
        
        signal = Signal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=case["price"],
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )
        
        position_size = strategy.get_position_size(signal, portfolio)
        passed = position_size >= case["expected_min"]
        
        print(f"  {'✅' if passed else '❌'} {case['name']}: {position_size:.6f} acciones (esperado >= {case['expected_min']})")
        
        if not passed:
            all_passed = False
            print(f"     ERROR: Position size {position_size} < expected {case['expected_min']}")
    
    return all_passed


def test_risk_check_scenarios():
    """Test 3: Verificar risk_check en diferentes escenarios."""
    print("\n" + "="*80)
    print("TEST 3: Risk Check - Escenarios")
    print("="*80)
    
    config = {"max_position_size": Decimal("0.1")}
    strategy = MomentumStrategy(config)
    
    scenarios = [
        {
            "name": "BUY con cash suficiente",
            "cash": Decimal("50000"),
            "positions": [],
            "signal_type": SignalType.BUY,
            "price": Decimal("200"),
            "expected": True,
        },
        {
            "name": "BUY sin cash suficiente",
            "cash": Decimal("10"),
            "positions": [],
            "signal_type": SignalType.BUY,
            "price": Decimal("200"),
            "expected": False,
        },
        {
            "name": "BUY con exposición alta (85%)",
            "cash": Decimal("10000"),
            "positions": [
                Position(
                    symbol="MSFT",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("300"),  # $60k
                    avg_price=Decimal("200"),
                    market_price=Decimal("200"),
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker="test",
                )
            ],
            "signal_type": SignalType.BUY,
            "price": Decimal("200"),
            "expected": False,  # 85.7% > 80%
        },
        {
            "name": "BUY con exposición media (50%)",
            "cash": Decimal("50000"),
            "positions": [
                Position(
                    symbol="MSFT",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("100"),  # $20k
                    avg_price=Decimal("200"),
                    market_price=Decimal("200"),
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker="test",
                )
            ],
            "signal_type": SignalType.BUY,
            "price": Decimal("200"),
            "expected": True,  # 28.6% < 80%
        },
        {
            "name": "SELL con posición",
            "cash": Decimal("50000"),
            "positions": [
                Position(
                    symbol="AAPL",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("10"),
                    avg_price=Decimal("200"),
                    market_price=Decimal("200"),
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker="test",
                )
            ],
            "signal_type": SignalType.SELL,
            "price": Decimal("200"),
            "expected": True,
        },
        {
            "name": "SELL sin posición",
            "cash": Decimal("50000"),
            "positions": [],
            "signal_type": SignalType.SELL,
            "price": Decimal("200"),
            "expected": False,
        },
    ]
    
    all_passed = True
    for scenario in scenarios:
        portfolio = Portfolio(
            portfolio_id="test",
            cash=scenario["cash"],
            positions=scenario["positions"],
            timestamp=datetime.utcnow(),
        )
        
        signal = Signal(
            symbol="AAPL",
            signal_type=scenario["signal_type"],
            strength=SignalStrength.MODERATE,
            confidence=70.0,
            liquidity_score=80.0,
            priority_score=85.0,
            source=SignalSource.MOMENTUM,
            price=scenario["price"],
            volume=Decimal("1"),
            timestamp=datetime.utcnow(),
            metadata={"strategy": "momentum"},
        )
        
        result = strategy.risk_check(signal, portfolio)
        passed = result == scenario["expected"]
        
        status = "✅" if passed else "❌"
        print(f"  {status} {scenario['name']}: {result} (esperado: {scenario['expected']})")
        
        if not passed:
            all_passed = False
            # Calcular exposición para diagnóstico
            if portfolio.positions:
                total_value = portfolio.cash + sum(p.market_value for p in portfolio.positions)
                invested = sum(p.market_value for p in portfolio.positions)
                exposure = (invested / total_value) if total_value > 0 else Decimal("0")
                print(f"     Exposición actual: {exposure:.2%}")
            
            # Calcular position_size para diagnóstico
            position_size = strategy.get_position_size(signal, portfolio)
            if scenario["signal_type"] == SignalType.BUY:
                required_cash = scenario["price"] * position_size
                print(f"     Position size: {position_size:.6f}, Required cash: ${required_cash:.2f}, Available: ${portfolio.cash:.2f}")
    
    return all_passed


def test_exposure_calculation():
    """Test 4: Verificar cálculo de exposición."""
    print("\n" + "="*80)
    print("TEST 4: Cálculo de Exposición")
    print("="*80)
    
    config = {}
    strategy = MomentumStrategy(config)
    
    test_cases = [
        {
            "name": "Sin posiciones",
            "cash": Decimal("50000"),
            "positions": [],
            "expected": Decimal("0"),
        },
        {
            "name": "50% exposición",
            "cash": Decimal("50000"),
            "positions": [
                Position(
                    symbol="AAPL",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("250"),  # $50k
                    avg_price=Decimal("200"),
                    market_price=Decimal("200"),
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker="test",
                )
            ],
            "expected": Decimal("0.5"),  # 50%
        },
        {
            "name": "80% exposición",
            "cash": Decimal("25000"),
            "positions": [
                Position(
                    symbol="AAPL",
                    asset_class=AssetClass.EQUITY,
                    quantity=Decimal("500"),  # $100k
                    avg_price=Decimal("200"),
                    market_price=Decimal("200"),
                    unrealized_pnl=Decimal("0"),
                    realized_pnl=Decimal("0"),
                    currency="USD",
                    broker="test",
                )
            ],
            "expected": Decimal("0.8"),  # 80%
        },
    ]
    
    all_passed = True
    for case in test_cases:
        portfolio = Portfolio(
            portfolio_id="test",
            cash=case["cash"],
            positions=case["positions"],
            timestamp=datetime.utcnow(),
        )
        
        exposure = strategy._calculate_total_exposure(portfolio)
        diff = abs(exposure - case["expected"])
        passed = diff < Decimal("0.01")
        
        print(f"  {'✅' if passed else '❌'} {case['name']}: {exposure:.2%} (esperado: {case['expected']:.2%})")
        
        if not passed:
            all_passed = False
            print(f"     ERROR: Diferencia de {diff:.2%}")
    
    return all_passed


def generate_report(results):
    """Generar reporte final."""
    print("\n" + "="*80)
    print("REPORTE FINAL")
    print("="*80)
    
    all_passed = all(r["passed"] for r in results)
    
    print(f"\nEstado general: {'✅ TODOS LOS TESTS PASARON' if all_passed else '❌ ALGUNOS TESTS FALLARON'}\n")
    
    for result in results:
        status = "✅" if result["passed"] else "❌"
        print(f"{status} {result['name']}")
        if not result["passed"]:
            print(f"   Detalles: {result.get('details', 'N/A')}")
    
    # Guardar reporte
    report_file = Path("docs/BACKTEST_RESULTS/momentum_diagnostic_report.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    report_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "PASSED" if all_passed else "FAILED",
        "results": results,
    }
    
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\n📄 Reporte guardado en: {report_file}")
    
    return all_passed


def main():
    """Ejecutar todos los tests."""
    print("="*80)
    print("DIAGNÓSTICO COMPLETO DE MOMENTUM STRATEGY")
    print("="*80)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    
    results = []
    
    # Test 1: Generación de señales
    try:
        passed, signals_count, signals_by_type = test_signal_generation()
        results.append({
            "name": "Test 1: Generación de Señales",
            "passed": passed,
            "details": {
                "signals_generated": signals_count,
                "by_type": signals_by_type,
            },
        })
    except Exception as e:
        results.append({
            "name": "Test 1: Generación de Señales",
            "passed": False,
            "details": f"ERROR: {str(e)}",
        })
        print(f"❌ ERROR en Test 1: {e}")
    
    # Test 2: Cálculo de tamaño de posición
    try:
        passed = test_position_size_calculation()
        results.append({
            "name": "Test 2: Cálculo de Tamaño de Posición",
            "passed": passed,
        })
    except Exception as e:
        results.append({
            "name": "Test 2: Cálculo de Tamaño de Posición",
            "passed": False,
            "details": f"ERROR: {str(e)}",
        })
        print(f"❌ ERROR en Test 2: {e}")
    
    # Test 3: Risk check
    try:
        passed = test_risk_check_scenarios()
        results.append({
            "name": "Test 3: Risk Check - Escenarios",
            "passed": passed,
        })
    except Exception as e:
        results.append({
            "name": "Test 3: Risk Check - Escenarios",
            "passed": False,
            "details": f"ERROR: {str(e)}",
        })
        print(f"❌ ERROR en Test 3: {e}")
    
    # Test 4: Cálculo de exposición
    try:
        passed = test_exposure_calculation()
        results.append({
            "name": "Test 4: Cálculo de Exposición",
            "passed": passed,
        })
    except Exception as e:
        results.append({
            "name": "Test 4: Cálculo de Exposición",
            "passed": False,
            "details": f"ERROR: {str(e)}",
        })
        print(f"❌ ERROR en Test 4: {e}")
    
    # Generar reporte
    all_passed = generate_report(results)
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

