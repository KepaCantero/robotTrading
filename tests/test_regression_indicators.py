"""
Tests de Regresión para Indicadores Técnicos

Generado automáticamente por StrategyAuditor.
Valida que los indicadores coinciden con pandas_ta.
"""

import unittest
from decimal import Decimal

import numpy as np

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
