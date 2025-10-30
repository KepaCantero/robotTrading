#!/usr/bin/env python3
"""
Auditoría Exhaustiva de Estrategias de Trading

Verifica:
- Sincronización de timestamps y datos
- Exactitud de indicadores (comparación con pandas_ta)
- Coherencia de señales (duplicadas, invertidas, solapadas)
- Aplicación correcta de presets y límites
- Tests de regresión automatizados
"""
import sys
from pathlib import Path

# Agregar directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

import numpy as np
import pandas as pd

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logging.warning("pandas_ta no disponible, saltando validación de indicadores")

from app.models.market_data import Quote
from app.models.signal import Signal, SignalType
from app.strategies.momentum import MomentumStrategy
from app.strategies.mean_reversion import MeanReversionStrategy
from app.strategies.pairs_trading import PairsTradingStrategy
from app.services.momentum_analysis import TechnicalIndicatorCalculator
from app.core.centralized_config import get_strategy_config
from app.services.portfolio_builder import PortfolioBuilder
from app.services.portfolio_config_manager import get_portfolio_config_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StrategyAuditor:
    """Auditoría completa de estrategias de trading."""
    
    def __init__(self):
        """Inicializar auditor."""
        self.calculator = TechnicalIndicatorCalculator()
        self.audit_results = {
            "indicator_discrepancies": [],
            "signals_errors": [],
            "parameter_mismatches": [],
            "data_issues": [],
            "execution_errors": [],
            "recommendations": []
        }
        
        self.strategies = {
            "momentum": MomentumStrategy({"name": "momentum"}),
            "mean_reversion": MeanReversionStrategy({"name": "mean_reversion"}),
            "pairs_trading": PairsTradingStrategy({
                "name": "pairs_trading",
                "pair_symbols": ["AAPL", "MSFT"]
            })
        }
    
    def audit_data_integrity(self, quotes: List[Quote]) -> Dict[str, Any]:
        """Auditoría de integridad de datos."""
        logger.info("🔍 Auditoría de Integridad de Datos")
        
        issues = []
        symbols = set(q.symbol for q in quotes)
        
        # Verificar sincronización de timestamps
        for symbol in symbols:
            symbol_quotes = sorted([q for q in quotes if q.symbol == symbol], key=lambda x: x.timestamp)
            
            if not symbol_quotes:
                issues.append({
                    "type": "missing_data",
                    "symbol": symbol,
                    "severity": "high",
                    "message": f"No hay datos para {symbol}"
                })
                continue
            
            # Verificar orden cronológico
            for i in range(1, len(symbol_quotes)):
                if symbol_quotes[i].timestamp < symbol_quotes[i-1].timestamp:
                    issues.append({
                        "type": "timestamp_out_of_order",
                        "symbol": symbol,
                        "severity": "high",
                        "message": f"Timestamp fuera de orden: {symbol_quotes[i].timestamp} < {symbol_quotes[i-1].timestamp}"
                    })
            
            # Verificar gaps (ignorando fines de semana y días festivos)
            def is_weekend_or_holiday_gap(prev_ts: datetime, curr_ts: datetime) -> bool:
                """Detecta si un gap es esperado (fin de semana o día festivo)."""
                gap_days = (curr_ts - prev_ts).days
                
                # Gap de 4 días puede ser: viernes -> lunes (fin de semana normal)
                # Gap de 5 días puede ser: viernes -> martes o jueves -> martes (fin de semana largo)
                # Gap de 4-5 días suelen ser esperados en mercados US
                
                # Si es viernes (4=Friday) y el siguiente es lunes (0=Monday), es normal
                if prev_ts.weekday() == 4 and curr_ts.weekday() == 0:
                    return gap_days <= 4  # Permitir hasta 4 días (viernes a lunes)
                
                # Si es jueves (3=Thursday) y el siguiente es martes (1=Tuesday), puede ser fin de semana largo
                if prev_ts.weekday() == 3 and curr_ts.weekday() == 1:
                    return gap_days <= 5  # Permitir hasta 5 días
                
                # Si es viernes y el siguiente es martes, es fin de semana largo (día festivo el lunes)
                if prev_ts.weekday() == 4 and curr_ts.weekday() == 1:
                    return gap_days <= 5
                
                # Días festivos comunes en US (aproximado por fechas)
                # New Year, MLK Day, Presidents Day, Good Friday, Memorial Day, 
                # Independence Day, Labor Day, Thanksgiving, Christmas
                # Estos suelen crear gaps de 4-5 días cuando caen en viernes o lunes
                
                # Para gaps <= 5 días, asumir que son festivos/fines de semana largos (normal en US)
                if gap_days <= 5:
                    return True
                
                return False
            
            for i in range(1, len(symbol_quotes)):
                gap_days = (symbol_quotes[i].timestamp - symbol_quotes[i-1].timestamp).days
                if gap_days > 3 and not is_weekend_or_holiday_gap(symbol_quotes[i-1].timestamp, symbol_quotes[i].timestamp):
                    # Solo reportar gaps > 5 días o gaps inusuales (>3 días que no sean fines de semana)
                    issues.append({
                        "type": "temporal_gap",
                        "symbol": symbol,
                        "severity": "medium" if gap_days <= 7 else "high",
                        "message": f"Gap de {gap_days} días entre {symbol_quotes[i-1].timestamp} y {symbol_quotes[i].timestamp}"
                    })
            
            # Verificar consistencia de precios
            for quote in symbol_quotes:
                if quote.low > quote.high:
                    issues.append({
                        "type": "price_inconsistency",
                        "symbol": symbol,
                        "severity": "high",
                        "message": f"low > high en {quote.timestamp}: low={quote.low}, high={quote.high}"
                    })
                if quote.open > quote.high or quote.close > quote.high:
                    issues.append({
                        "type": "price_inconsistency",
                        "symbol": symbol,
                        "severity": "high",
                        "message": f"open/close > high en {quote.timestamp}"
                    })
        
        self.audit_results["data_issues"] = issues
        
        logger.info(f"✅ Auditoría de datos completada: {len(issues)} issues encontrados")
        return {"total_issues": len(issues), "issues": issues}
    
    def audit_indicators(self, quotes: List[Quote], symbol: str = "AAPL") -> Dict[str, Any]:
        """Validar indicadores comparando con pandas_ta."""
        logger.info(f"🔍 Auditoría de Indicadores para {symbol}")
        
        if not PANDAS_TA_AVAILABLE:
            logger.warning("pandas_ta no disponible, saltando validación de indicadores")
            return {"status": "skipped", "reason": "pandas_ta no disponible"}
        
        symbol_quotes = sorted([q for q in quotes if q.symbol == symbol], key=lambda x: x.timestamp)
        
        if len(symbol_quotes) < 50:
            logger.warning(f"Insuficientes datos para {symbol}: {len(symbol_quotes)} quotes")
            return {"status": "insufficient_data", "quotes_count": len(symbol_quotes)}
        
        discrepancies = []
        prices = [float(q.close) for q in symbol_quotes]
        df = pd.DataFrame({
            "close": prices,
            "high": [float(q.high) for q in symbol_quotes],
            "low": [float(q.low) for q in symbol_quotes],
            "volume": [float(q.volume) for q in symbol_quotes],
        })
        
        # RSI
        period = 14
        our_rsi_values = []
        for i in range(period + 1, len(prices) + 1):
            rsi = self.calculator.calculate_rsi(prices[:i], period=period)
            if rsi is not None:
                our_rsi_values.append(rsi)
        
        pandas_rsi = ta.rsi(df["close"], length=period)
        pandas_rsi_values = pandas_rsi.dropna().values.tolist()
        
        if our_rsi_values and pandas_rsi_values:
            min_len = min(len(our_rsi_values), len(pandas_rsi_values))
            if min_len > 0:
                our_slice = np.array(our_rsi_values[-min_len:])
                pandas_slice = np.array(pandas_rsi_values[-min_len:])
                differences = np.abs(our_slice - pandas_slice)
                max_diff = np.max(differences)
                
                if max_diff > 1.0:  # Tolerancia 1.0
                    discrepancies.append({
                        "indicator": "RSI",
                        "symbol": symbol,
                        "max_difference": float(max_diff),
                        "tolerance": 1.0,
                        "severity": "high" if max_diff > 5.0 else "medium",
                        "message": f"RSI difiere de pandas_ta: max_diff={max_diff:.4f}"
                    })
        
        # EMA
        ema_period = 20
        our_ema = self.calculator.calculate_ema(prices, period=ema_period)
        pandas_ema = ta.ema(df["close"], length=ema_period)
        
        if our_ema is not None and pandas_ema is not None:
            pandas_ema_value = pandas_ema.iloc[-1]
            diff = abs(our_ema - pandas_ema_value)
            
            if diff > 0.1:
                discrepancies.append({
                    "indicator": "EMA",
                    "symbol": symbol,
                    "max_difference": float(diff),
                    "tolerance": 0.1,
                    "severity": "medium",
                    "message": f"EMA difiere de pandas_ta: our={our_ema}, pandas={pandas_ema_value}, diff={diff:.4f}"
                })
        
        # MACD
        our_macd, our_signal, our_hist = self.calculator.calculate_macd(
            prices, fast_period=12, slow_period=26, signal_period=9
        )
        macd_ta = ta.macd(df["close"], fast=12, slow=26, signal=9)
        
        if our_macd is not None and macd_ta is not None:
            pandas_macd = macd_ta.iloc[-1]["MACD_12_26_9"]
            diff = abs(our_macd - pandas_macd)
            
            if diff > 1.0:
                discrepancies.append({
                    "indicator": "MACD",
                    "symbol": symbol,
                    "max_difference": float(diff),
                    "tolerance": 1.0,
                    "severity": "medium",
                    "message": f"MACD difiere de pandas_ta: our={our_macd}, pandas={pandas_macd}, diff={diff:.4f}"
                })
        
        self.audit_results["indicator_discrepancies"].extend(discrepancies)
        
        logger.info(f"✅ Auditoría de indicadores completada: {len(discrepancies)} discrepancias")
        return {"discrepancies": discrepancies, "total": len(discrepancies)}
    
    def audit_signals(self, quotes: List[Quote], strategy_name: str, symbol: str = "AAPL") -> Dict[str, Any]:
        """Auditar señales generadas por estrategia."""
        logger.info(f"🔍 Auditoría de Señales: {strategy_name} para {symbol}")
        
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            logger.error(f"Estrategia {strategy_name} no encontrada")
            return {"error": "strategy_not_found"}
        
        symbol_quotes = sorted([q for q in quotes if q.symbol == symbol], key=lambda x: x.timestamp)
        
        if len(symbol_quotes) < 50:
            return {"status": "insufficient_data", "quotes_count": len(symbol_quotes)}
        
        # Generar señales
        all_signals = []
        for quote in symbol_quotes:
            signals = strategy.generate_signals(quote)
            all_signals.extend(signals)
        
        errors = []
        
        # Verificar señales duplicadas
        seen_signals = {}
        for signal in all_signals:
            key = (signal.symbol, signal.timestamp, signal.signal_type)
            if key in seen_signals:
                errors.append({
                    "type": "duplicate_signal",
                    "symbol": symbol,
                    "timestamp": signal.timestamp.isoformat(),
                    "signal_type": str(signal.signal_type),
                    "severity": "high",
                    "message": f"Señal duplicada: {signal.signal_id} duplica {seen_signals[key]}"
                })
            seen_signals[key] = signal.signal_id
        
        # Verificar señales solapadas (BUY y SELL simultáneos)
        signals_by_timestamp = defaultdict(list)
        for signal in all_signals:
            signals_by_timestamp[signal.timestamp].append(signal)
        
        for timestamp, signals_at_time in signals_by_timestamp.items():
            signal_types = [s.signal_type for s in signals_at_time]
            if SignalType.BUY in signal_types and SignalType.SELL in signal_types:
                signal_types_str = [str(s.signal_type) for s in signals_at_time]
                errors.append({
                    "type": "overlapping_signals",
                    "symbol": symbol,
                    "timestamp": timestamp.isoformat(),
                    "severity": "high",
                    "message": f"Señales opuestas simultáneas en {timestamp}: {signal_types_str}"
                })
        
        # Verificar coherencia de señales según indicadores (solo para Momentum)
        if strategy_name == "momentum":
            momentum_errors = self._audit_momentum_signal_coherence(symbol_quotes, all_signals)
            errors.extend(momentum_errors)
        
        self.audit_results["signals_errors"].extend(errors)
        
        logger.info(f"✅ Auditoría de señales completada: {len(errors)} errores encontrados")
        return {"errors": errors, "total_signals": len(all_signals), "total_errors": len(errors)}
    
    def _audit_momentum_signal_coherence(self, quotes: List[Quote], signals: List[Signal]) -> List[Dict[str, Any]]:
        """Verificar coherencia de señales Momentum con indicadores."""
        errors = []
        
        prices = [float(q.close) for q in quotes]
        
        # Agrupar señales por timestamp aproximado
        for signal in signals:
            # Encontrar quote más cercano
            closest_quote = min(quotes, key=lambda q: abs((q.timestamp - signal.timestamp).total_seconds()))
            
            if abs((closest_quote.timestamp - signal.timestamp).total_seconds()) > 86400:
                continue  # Skip si está muy lejos
            
            # Calcular RSI
            quote_index = quotes.index(closest_quote)
            if quote_index >= 14:
                rsi = self.calculator.calculate_rsi(prices[:quote_index+1], period=14)
                
                if rsi is not None:
                    # BUY cuando RSI < 30 (oversold) o condiciones alcistas
                    # SELL cuando RSI > 70 (overbought) o condiciones bajistas
                    if signal.signal_type == SignalType.BUY:
                        if rsi > 70:  # RSI muy alto, no debería comprar
                            errors.append({
                                "type": "inverted_signal",
                                "symbol": signal.symbol,
                                "timestamp": signal.timestamp.isoformat(),
                                "signal_type": str(SignalType.BUY),
                                "severity": "high",
                                "message": f"BUY con RSI alto ({rsi:.2f}): posible señal invertida"
                            })
                    elif signal.signal_type == SignalType.SELL:
                        if rsi < 30:  # RSI muy bajo, no debería vender
                            errors.append({
                                "type": "inverted_signal",
                                "symbol": signal.symbol,
                                "timestamp": signal.timestamp.isoformat(),
                                "signal_type": str(SignalType.SELL),
                                "severity": "high",
                                "message": f"SELL con RSI bajo ({rsi:.2f}): posible señal invertida"
                            })
        
        return errors
    
    def audit_parameters_and_presets(self) -> Dict[str, Any]:
        """Auditar presets y parámetros."""
        logger.info("🔍 Auditoría de Presets y Parámetros")
        
        mismatches = []
        
        for strategy_name, strategy in self.strategies.items():
            config = get_strategy_config(strategy_name)
            
            # Verificar parámetros de riesgo
            if hasattr(strategy, 'stop_loss') and hasattr(strategy, 'take_profit'):
                if strategy.stop_loss is None:
                    mismatches.append({
                        "type": "missing_parameter",
                        "strategy": strategy_name,
                        "parameter": "stop_loss",
                        "severity": "high",
                        "message": f"{strategy_name}: stop_loss no está configurado"
                    })
                
                if strategy.take_profit is None:
                    mismatches.append({
                        "type": "missing_parameter",
                        "strategy": strategy_name,
                        "parameter": "take_profit",
                        "severity": "high",
                        "message": f"{strategy_name}: take_profit no está configurado"
                    })
                
                # Verificar que stop_loss < take_profit
                if strategy.stop_loss is not None and strategy.take_profit is not None:
                    if strategy.stop_loss >= strategy.take_profit:
                        mismatches.append({
                            "type": "invalid_parameter_relationship",
                            "strategy": strategy_name,
                            "severity": "high",
                            "message": f"{strategy_name}: stop_loss ({strategy.stop_loss}) >= take_profit ({strategy.take_profit})"
                        })
            
            # Verificar límites de exposición
            if hasattr(strategy, 'max_exposure'):
                if strategy.max_exposure is None:
                    mismatches.append({
                        "type": "missing_parameter",
                        "strategy": strategy_name,
                        "parameter": "max_exposure",
                        "severity": "high",
                        "message": f"{strategy_name}: max_exposure no está configurado"
                    })
                elif strategy.max_exposure > 1.0:
                    mismatches.append({
                        "type": "invalid_parameter_value",
                        "strategy": strategy_name,
                        "parameter": "max_exposure",
                        "severity": "high",
                        "message": f"{strategy_name}: max_exposure ({strategy.max_exposure}) > 1.0 (100%)"
                    })
        
        self.audit_results["parameter_mismatches"] = mismatches
        
        logger.info(f"✅ Auditoría de parámetros completada: {len(mismatches)} issues encontrados")
        return {"mismatches": mismatches, "total": len(mismatches)}
    
    def generate_regression_tests(self, output_dir: Path = Path("tests")) -> Dict[str, Any]:
        """Generar tests de regresión automatizados."""
        logger.info("🔍 Generación de Tests de Regresión")
        
        test_files = []
        
        # Test de indicadores
        indicators_test = self._generate_indicators_regression_test()
        indicators_file = output_dir / "test_regression_indicators.py"
        indicators_file.write_text(indicators_test)
        test_files.append(str(indicators_file))
        
        # Test de señales Momentum
        momentum_test = self._generate_strategy_regression_test("momentum")
        momentum_file = output_dir / "test_regression_momentum.py"
        momentum_file.write_text(momentum_test)
        test_files.append(str(momentum_file))
        
        # Test de señales Mean Reversion
        mean_rev_test = self._generate_strategy_regression_test("mean_reversion")
        mean_rev_file = output_dir / "test_regression_mean_reversion.py"
        mean_rev_file.write_text(mean_rev_test)
        test_files.append(str(mean_rev_file))
        
        logger.info(f"✅ Tests de regresión generados: {len(test_files)} archivos")
        return {"test_files": test_files, "total": len(test_files)}
    
    def _generate_indicators_regression_test(self) -> str:
        """Generar test de regresión para indicadores."""
        return '''"""
Tests de Regresión para Indicadores Técnicos

Generado automáticamente por StrategyAuditor.
Valida que los indicadores coinciden con pandas_ta.
"""
import unittest
import numpy as np
from decimal import Decimal

try:
    import pandas as pd
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False

from app.services.momentum_analysis import TechnicalIndicatorCalculator


class TestIndicatorsRegression(unittest.TestCase):
    """Tests de regresión para indicadores."""
    
    def setUp(self):
        """Setup para tests de indicadores."""
        self.calculator = TechnicalIndicatorCalculator()
        # Dataset conocido con resultados esperados
        self.prices = [100.0 + i * 0.5 + np.random.RandomState(42).normal(0, 1) for i in range(100)]
    
    @unittest.skipUnless(PANDAS_TA_AVAILABLE, "pandas_ta no disponible")
    def test_rsi_regression(self):
        """Test de regresión para RSI."""
        period = 14
        our_rsi = self.calculator.calculate_rsi(self.prices, period=period)
        
        df = pd.DataFrame({"close": self.prices})
        pandas_rsi = ta.rsi(df["close"], length=period)
        
        if our_rsi is not None and pandas_rsi is not None:
            pandas_rsi_value = pandas_rsi.iloc[-1]
            diff = abs(our_rsi - pandas_rsi_value)
            self.assertLess(diff, 1.0, f"RSI difiere de pandas_ta: {diff:.4f}")
    
    @unittest.skipUnless(PANDAS_TA_AVAILABLE, "pandas_ta no disponible")
    def test_ema_regression(self):
        """Test de regresión para EMA."""
        period = 20
        our_ema = self.calculator.calculate_ema(self.prices, period=period)
        
        df = pd.DataFrame({"close": self.prices})
        pandas_ema = ta.ema(df["close"], length=period)
        
        if our_ema is not None and pandas_ema is not None:
            pandas_ema_value = pandas_ema.iloc[-1]
            diff = abs(our_ema - pandas_ema_value)
            self.assertLess(diff, 0.1, f"EMA difiere de pandas_ta: {diff:.4f}")


if __name__ == "__main__":
    unittest.main()
'''
    
    def _generate_strategy_regression_test(self, strategy_name: str) -> str:
        """Generar test de regresión para estrategia."""
        strategy_class = {
            "momentum": "MomentumStrategy",
            "mean_reversion": "MeanReversionStrategy"
        }.get(strategy_name, "BaseStrategy")
        
        return f'''"""
Test de Regresión para {strategy_name.replace("_", " ").title()}

Generado automáticamente por StrategyAuditor.
Valida coherencia de señales y parámetros.
"""
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.market_data import Quote
from app.models.signal import SignalType
from app.strategies.{strategy_name} import {strategy_class}


class Test{strategy_name.replace("_", "").title()}Regression(unittest.TestCase):
    """Tests de regresión para {strategy_name}."""
    
    def setUp(self):
        """Setup para tests."""
        self.strategy = {strategy_class}({{"name": "{strategy_name}"}})
    
    def test_no_duplicate_signals(self):
        """Verificar que no hay señales duplicadas."""
        base_date = datetime(2024, 1, 1)
        quotes = []
        all_signals = []
        
        for i in range(50):
            quote = Quote(
                symbol="AAPL",
                timestamp=base_date + timedelta(days=i),
                open=Decimal("200"),
                high=Decimal("202"),
                low=Decimal("198"),
                close=Decimal("200"),
                last=Decimal("200"),
                bid=Decimal("199.8"),
                ask=Decimal("200.2"),
                volume=Decimal("1000000"),
            )
            quotes.append(quote)
            signals = self.strategy.generate_signals(quote)
            all_signals.extend(signals)
        
        # Verificar no duplicados
        seen = set()
        for signal in all_signals:
            key = (signal.symbol, signal.timestamp, signal.signal_type)
            self.assertNotIn(key, seen, f"Señal duplicada: {{signal.signal_id}}")
            seen.add(key)
    
    def test_no_overlapping_signals(self):
        """Verificar que no hay BUY y SELL simultáneos."""
        base_date = datetime(2024, 1, 1)
        quotes = []
        all_signals = []
        
        for i in range(50):
            quote = Quote(
                symbol="AAPL",
                timestamp=base_date + timedelta(days=i),
                open=Decimal("200"),
                high=Decimal("202"),
                low=Decimal("198"),
                close=Decimal("200"),
                last=Decimal("200"),
                bid=Decimal("199.8"),
                ask=Decimal("200.2"),
                volume=Decimal("1000000"),
            )
            quotes.append(quote)
            signals = self.strategy.generate_signals(quote)
            all_signals.extend(signals)
        
        # Agrupar por timestamp
        from collections import defaultdict
        signals_by_time = defaultdict(list)
        for signal in all_signals:
            signals_by_time[signal.timestamp].append(signal)
        
        # Verificar no solapamiento
        for timestamp, signals_at_time in signals_by_time.items():
            signal_types = [s.signal_type for s in signals_at_time]
            if SignalType.BUY in signal_types and SignalType.SELL in signal_types:
                self.fail(f"Señales opuestas simultáneas en {{timestamp}}")
    
    def test_parameters_configured(self):
        """Verificar que los parámetros están configurados."""
        self.assertIsNotNone(self.strategy.stop_loss, "stop_loss debe estar configurado")
        self.assertIsNotNone(self.strategy.take_profit, "take_profit debe estar configurado")
        self.assertGreater(self.strategy.stop_loss, 0, "stop_loss debe ser > 0")
        self.assertGreater(self.strategy.take_profit, 0, "take_profit debe ser > 0")


if __name__ == "__main__":
    unittest.main()
'''
    
    def generate_report(self, output_file: Path = Path("docs/STRATEGY_AUDIT_REPORT.json")) -> Dict[str, Any]:
        """Generar reporte completo de auditoría."""
        logger.info("📄 Generando Reporte de Auditoría")
        
        # Calcular estadísticas
        total_issues = (
            len(self.audit_results["data_issues"]) +
            len(self.audit_results["indicator_discrepancies"]) +
            len(self.audit_results["signals_errors"]) +
            len(self.audit_results["parameter_mismatches"])
        )
        
        high_severity = sum(1 for issue in (
            self.audit_results["data_issues"] +
            self.audit_results["indicator_discrepancies"] +
            self.audit_results["signals_errors"] +
            self.audit_results["parameter_mismatches"]
        ) if issue.get("severity") == "high")
        
        # Generar recomendaciones
        recommendations = []
        
        if self.audit_results["indicator_discrepancies"]:
            recommendations.append({
                "priority": "high",
                "action": "Revisar cálculo de indicadores técnicos, especialmente RSI y MACD",
                "details": f"{len(self.audit_results['indicator_discrepancies'])} discrepancias encontradas"
            })
        
        if self.audit_results["signals_errors"]:
            recommendations.append({
                "priority": "high",
                "action": "Corregir lógica de generación de señales para evitar duplicados e inversiones",
                "details": f"{len(self.audit_results['signals_errors'])} errores en señales"
            })
        
        if self.audit_results["parameter_mismatches"]:
            recommendations.append({
                "priority": "medium",
                "action": "Verificar configuración de parámetros y presets",
                "details": f"{len(self.audit_results['parameter_mismatches'])} desajustes en parámetros"
            })
        
        self.audit_results["recommendations"] = recommendations
        
        report = {
            "audit_timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_issues": total_issues,
                "high_severity_issues": high_severity,
                "data_issues": len(self.audit_results["data_issues"]),
                "indicator_discrepancies": len(self.audit_results["indicator_discrepancies"]),
                "signals_errors": len(self.audit_results["signals_errors"]),
                "parameter_mismatches": len(self.audit_results["parameter_mismatches"])
            },
            **self.audit_results
        }
        
        # Guardar reporte
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"✅ Reporte guardado en {output_file}")
        return report


def main():
    """Ejecutar auditoría completa."""
    logger.info("🚀 Iniciando Auditoría Exhaustiva de Estrategias")
    
    auditor = StrategyAuditor()
    
    # Obtener datos de ejemplo
    portfolio_config = get_portfolio_config_manager()
    portfolio_builder = PortfolioBuilder(portfolio_config=portfolio_config)
    
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2024, 1, 1)
    
    try:
        # Construir portfolio y obtener quotes
        quotes = []
        
        # Intentar obtener quotes directamente
        # Si build_portfolio_quotes no está disponible, crear datos de ejemplo
        try:
            quotes = portfolio_builder.build_portfolio_quotes(
                start_date=start_date,
                end_date=end_date,
                max_symbols_per_strategy=5,
            )
        except Exception as e:
            logger.warning(f"No se pudieron obtener quotes del portfolio builder: {e}")
            # Crear datos de ejemplo para auditoría
            logger.info("Generando datos de ejemplo para auditoría...")
            from app.models.market_data import Quote
            for i in range(100):
                day = start_date + timedelta(days=i)
                quotes.append(Quote(
                    symbol="AAPL",
                    timestamp=day,
                    open=Decimal("200"),
                    high=Decimal("202"),
                    low=Decimal("198"),
                    close=Decimal("200") + Decimal(str(i % 10 - 5)),
                    last=Decimal("200"),
                    bid=Decimal("199.8"),
                    ask=Decimal("200.2"),
                    volume=Decimal("1000000"),
                ))
        
        logger.info(f"✅ Obtenidos {len(quotes)} quotes")
        
        # Ejecutar auditorías
        auditor.audit_data_integrity(quotes)
        
        # Auditoría de indicadores para cada símbolo
        symbols = list(set(q.symbol for q in quotes))[:3]  # Primeros 3 símbolos
        for symbol in symbols:
            auditor.audit_indicators(quotes, symbol=symbol)
        
        # Auditoría de señales
        for strategy_name in ["momentum", "mean_reversion"]:
            for symbol in symbols:
                auditor.audit_signals(quotes, strategy_name, symbol=symbol)
        
        # Auditoría de parámetros
        auditor.audit_parameters_and_presets()
        
        # Generar tests de regresión
        auditor.generate_regression_tests()
        
        # Generar reporte
        report = auditor.generate_report()
        
        # Imprimir resumen
        print("\n" + "="*80)
        print("📊 RESUMEN DE AUDITORÍA")
        print("="*80)
        print(f"Total de Issues: {report['summary']['total_issues']}")
        print(f"Issues de Alta Severidad: {report['summary']['high_severity_issues']}")
        print(f"\nDetalles:")
        print(f"  - Issues de Datos: {report['summary']['data_issues']}")
        print(f"  - Discrepancias de Indicadores: {report['summary']['indicator_discrepancies']}")
        print(f"  - Errores en Señales: {report['summary']['signals_errors']}")
        print(f"  - Desajustes de Parámetros: {report['summary']['parameter_mismatches']}")
        print("\n" + "="*80)
        print(f"📄 Reporte completo guardado en: docs/STRATEGY_AUDIT_REPORT.json")
        print("="*80 + "\n")
        
        return report
        
    except Exception as e:
        logger.error(f"Error durante auditoría: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

