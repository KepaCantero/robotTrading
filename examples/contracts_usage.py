"""
Code Contracts Usage Examples for AlgoTrading MVP

This module demonstrates how to use the Design by Contract system
in real trading operations.

Author: AlgoTrading MVP Team
Version: 1.0.0
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from app.core.contracts import (
    ContractViolationError,
    MarketDataContract,
    PositionContract,
    SignalContract,
    TechnicalIndicatorContract,
    contract,
    risk_calculation,
    signal_analysis,
    trading_operation,
    validate_batch_trading_data,
    validate_trading_data,
)


class TradingOperationsWithContracts:
    """Example trading operations using code contracts."""

    @trading_operation(MarketDataContract)
    def execute_trade(
        self, market_data: Dict, quantity: Decimal, price: Decimal
    ) -> Dict:
        """
        Execute a trade with contract validation.

        Preconditions:
        - Market data must be valid (validated by MarketDataContract)
        - Quantity must be positive
        - Price must be reasonable

        Postconditions:
        - Trade value must be within limits
        """
        trade_value = quantity * price

        return {
            "symbol": market_data["symbol"],
            "quantity": quantity,
            "price": price,
            "trade_value": trade_value,
            "timestamp": datetime.now(),
            "status": "executed",
        }

    @signal_analysis(SignalContract)
    def analyze_signal(self, signal_data: Dict) -> Dict:
        """
        Analyze a trading signal with contract validation.

        Preconditions:
        - Signal data must be valid (validated by SignalContract)
        - Confidence must be between 0.0 and 1.0

        Postconditions:
        - Analysis result must be consistent with signal strength
        """
        confidence = signal_data["confidence"]
        strength = signal_data["strength"]

        # Calculate analysis score based on confidence and strength
        strength_multiplier = {"WEAK": 0.5, "MEDIUM": 0.75, "STRONG": 1.0}
        analysis_score = confidence * strength_multiplier.get(strength, 0.5)

        return {
            "signal_id": signal_data.get("id", "unknown"),
            "symbol": signal_data["symbol"],
            "analysis_score": analysis_score,
            "recommendation": (
                "BUY"
                if analysis_score > 0.7
                else "HOLD" if analysis_score > 0.4 else "SELL"
            ),
            "confidence_level": (
                "HIGH" if confidence > 0.8 else "MEDIUM" if confidence > 0.5 else "LOW"
            ),
        }

    @risk_calculation()
    def calculate_position_risk(
        self, quantity: Decimal, price: Decimal, volatility: float
    ) -> Dict:
        """
        Calculate position risk with contract validation.

        Preconditions:
        - Quantity must be non-zero
        - Price must be positive
        - Volatility must be between 0.0 and 1.0

        Postconditions:
        - Risk metrics must be reasonable
        """
        position_value = abs(quantity * price)
        risk_amount = position_value * Decimal(str(volatility))

        return {
            "position_value": position_value,
            "risk_amount": risk_amount,
            "risk_percentage": volatility * 100,
            "risk_level": (
                "HIGH" if volatility > 0.3 else "MEDIUM" if volatility > 0.15 else "LOW"
            ),
        }

    @contract(
        preconditions=[lambda data: isinstance(data, dict)],
        postconditions=[lambda result: isinstance(result, list)],
    )
    def process_market_data_batch(self, market_data_list: List[Dict]) -> List[Dict]:
        """
        Process a batch of market data with contract validation.

        Preconditions:
        - Input must be a list of dictionaries

        Postconditions:
        - Output must be a list of processed data
        """
        processed_data = []

        for data in market_data_list:
            try:
                # Validate each market data item
                validate_trading_data(data, MarketDataContract)

                # Process the data
                processed_item = {
                    "symbol": data["symbol"],
                    "price": data["price"],
                    "volume": data["volume"],
                    "processed_at": datetime.now(),
                    "status": "valid",
                }
                processed_data.append(processed_item)

            except ContractViolationError as e:
                # Log invalid data but continue processing
                processed_item = {
                    "symbol": data.get("symbol", "unknown"),
                    "error": str(e),
                    "processed_at": datetime.now(),
                    "status": "invalid",
                }
                processed_data.append(processed_item)

        return processed_data

    def calculate_technical_indicators(
        self, price_data: List[Decimal], indicator_type: str
    ) -> Dict:
        """
        Calculate technical indicators with contract validation.

        This method demonstrates how to use contracts for complex calculations.
        """
        if not price_data:
            raise ContractViolationError(
                "Price data cannot be empty",
                "PRECONDITION",
                "calculate_technical_indicators",
            )

        # Validate indicator type
        valid_indicators = ["RSI", "EMA", "MACD", "ATR", "VOLUME_SMA"]
        if indicator_type not in valid_indicators:
            raise ContractViolationError(
                f"Invalid indicator type: {indicator_type}",
                "PRECONDITION",
                "calculate_technical_indicators",
            )

        # Calculate indicator value (simplified)
        if indicator_type == "RSI":
            # Simplified RSI calculation
            value = 50.0  # Placeholder
        elif indicator_type == "EMA":
            value = float(sum(price_data) / len(price_data))
        else:
            value = 0.0

        # Create contract instance for validation
        indicator_data = {
            "indicator_type": indicator_type,
            "value": value,
            "symbol": "AAPL",  # Would be passed as parameter in real implementation
            "timestamp": datetime.now(),
        }

        # Validate the result
        validate_trading_data(indicator_data, TechnicalIndicatorContract)

        return {
            "indicator_type": indicator_type,
            "value": value,
            "calculated_at": datetime.now(),
            "data_points": len(price_data),
        }


# Example usage and testing functions


def example_trading_workflow():
    """Example of how to use contracts in a trading workflow."""

    trading_ops = TradingOperationsWithContracts()

    # Example 1: Execute a trade
    market_data = {
        "symbol": "AAPL",
        "price": Decimal("150.0"),
        "volume": Decimal("1000000"),
        "timestamp": datetime.now(),
    }

    try:
        trade_result = trading_ops.execute_trade(
            market_data, Decimal("100"), Decimal("150.0")
        )
        print(f"Trade executed: {trade_result}")
    except ContractViolationError as e:
        print(f"Trade failed due to contract violation: {e}")

    # Example 2: Analyze a signal
    signal_data = {
        "signal_type": "BUY",
        "confidence": 0.85,
        "strength": "STRONG",
        "symbol": "AAPL",
    }

    try:
        analysis_result = trading_ops.analyze_signal(signal_data)
        print(f"Signal analysis: {analysis_result}")
    except ContractViolationError as e:
        print(f"Signal analysis failed due to contract violation: {e}")

    # Example 3: Calculate risk
    try:
        risk_result = trading_ops.calculate_position_risk(
            Decimal("1000"), Decimal("150.0"), 0.2
        )
        print(f"Risk calculation: {risk_result}")
    except ContractViolationError as e:
        print(f"Risk calculation failed due to contract violation: {e}")

    # Example 4: Process batch data
    batch_data = [
        {
            "symbol": "AAPL",
            "price": Decimal("150.0"),
            "volume": Decimal("1000000"),
            "timestamp": datetime.now(),
        },
        {
            "symbol": "MSFT",
            "price": Decimal("200.0"),
            "volume": Decimal("500000"),
            "timestamp": datetime.now(),
        },
    ]

    try:
        processed_batch = trading_ops.process_market_data_batch(batch_data)
        print(f"Batch processing result: {processed_batch}")
    except ContractViolationError as e:
        print(f"Batch processing failed due to contract violation: {e}")


def example_contract_violations():
    """Example of contract violations and how they are handled."""

    trading_ops = TradingOperationsWithContracts()

    print("\n=== Contract Violation Examples ===")

    # Example 1: Invalid market data (lowercase symbol)
    invalid_market_data = {
        "symbol": "aapl",  # Invalid: should be uppercase
        "price": Decimal("150.0"),
        "volume": Decimal("1000000"),
        "timestamp": datetime.now(),
    }

    try:
        trading_ops.execute_trade(invalid_market_data, Decimal("100"), Decimal("150.0"))
    except ContractViolationError as e:
        print(f"Contract violation caught: {e}")

    # Example 2: Invalid signal (confidence > 1.0)
    invalid_signal = {
        "signal_type": "BUY",
        "confidence": 1.5,  # Invalid: should be <= 1.0
        "strength": "STRONG",
        "symbol": "AAPL",
    }

    try:
        trading_ops.analyze_signal(invalid_signal)
    except ContractViolationError as e:
        print(f"Contract violation caught: {e}")

    # Example 3: Invalid risk calculation (zero quantity)
    try:
        trading_ops.calculate_position_risk(Decimal("0"), Decimal("150.0"), 0.2)
    except ContractViolationError as e:
        print(f"Contract violation caught: {e}")


if __name__ == "__main__":
    print("=== Code Contracts Usage Examples ===")
    example_trading_workflow()
    example_contract_violations()
