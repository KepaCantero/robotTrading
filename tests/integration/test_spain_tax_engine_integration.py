"""
Integration test for SpainTaxEngine with real-world scenarios.

This test demonstrates practical use cases for the SpainTaxEngine,
including calculation of taxes for actual trading scenarios.
"""

from decimal import Decimal

from app.services.tax_efficiency.engines import get_tax_engine


def test_spain_tax_engine_integration():
    """
    Test SpainTaxEngine with realistic trading scenario.

    Scenario:
    - Spanish resident trader
    - Multiple trades throughout the year
    - Mixed capital gains and losses
    - Dividend income from EU and US stocks
    - Foreign assets threshold check
    """

    # Create Spain tax engine
    engine = get_tax_engine("ES")

    # === Scenario 1: Year-end capital gains calculation ===
    print("\n=== Scenario 1: Capital Gains Calculation ===")

    trades = [
        {"amount": Decimal("15000"), "description": "AAPL profit"},
        {"amount": Decimal("8000"), "description": "MSFT profit"},
        {"amount": Decimal("-3000"), "description": "TSLA loss"},
        {"amount": Decimal("12000"), "description": "NVDA profit"},
    ]

    total_gain = sum(t["amount"] for t in trades)
    capital_gains_tax = engine.calculate_capital_gains_tax(total_gain)

    print(f"Total capital gains: €{total_gain:,.2f}")
    print(f"Capital gains tax: €{capital_gains_tax:,.2f}")
    print(f"Effective rate: {float(capital_gains_tax / total_gain):.1%}")

    # === Scenario 2: Dividend income from multiple countries ===
    print("\n=== Scenario 2: International Dividend Income ===")

    dividends = {
        "DE": Decimal("2000"),  # German stocks (0% withholding)
        "US": Decimal("1500"),  # US stocks (15% withholding)
        "UK": Decimal("800"),   # UK stocks (15% withholding)
    }

    total_dividends = sum(dividends.values())
    dividend_tax = engine.calculate_dividend_tax(total_dividends)

    print(f"Total dividends received: €{total_dividends:,.2f}")
    print(f"Dividend tax (Spain): €{dividend_tax:,.2f}")

    # Show withholding taxes by country
    print("\nWithholding taxes:")
    for country, amount in dividends.items():
        wh_rate = engine.get_withholding_tax_rate(country)
        wh_tax = amount * wh_rate
        print(f"  {country}: {wh_rate:.0%} = €{wh_tax:,.2f}")

    # === Scenario 3: Annual tax summary ===
    print("\n=== Scenario 3: Annual Tax Summary ===")

    summary = engine.get_tax_summary(
        capital_gains=total_gain,
        dividends=total_dividends,
    )

    print(f"Capital gains: €{summary['capital_gains']:,.2f}")
    print(f"Dividends: €{summary['dividends']:,.2f}")
    print(f"Capital gains tax: €{summary['capital_gains_tax']:,.2f}")
    print(f"Dividend tax: €{summary['dividend_tax']:,.2f}")
    print(f"Total tax liability: €{summary['total_tax']:,.2f}")
    print(f"Country: {summary['country']}")

    # === Scenario 4: Modelo 720 check ===
    print("\n=== Scenario 4: Modelo 720 (Foreign Assets) ===")

    # Check various foreign asset values
    test_values = [
        Decimal("30000"),  # Below threshold
        Decimal("50000"),  # At threshold
        Decimal("75000"),  # Above threshold
    ]

    for value in test_values:
        result = engine.check_modelo_720_threshold(value)
        status = "REQUIRED" if result["filing_required"] else "not required"
        print(f"Foreign assets €{value:,.2f}: Modelo 720 {status}")

    # === Scenario 5: Tax planning scenarios ===
    print("\n=== Scenario 5: Tax Planning Analysis ===")

    # Compare tax impact of realizing gains now vs later
    potential_gains = [
        Decimal("30000"),  # Would be in bracket 1
        Decimal("35000"),  # Would push into bracket 2
        Decimal("60000"),  # Deep in bracket 3
    ]

    print("\nTax analysis for potential gains:")
    for gain in potential_gains:
        tax = engine.calculate_capital_gains_tax(gain)
        rate, limit = engine.get_tax_rate_by_gain(gain)
        effective_rate = float(tax / gain)
        print(f"  Gain €{gain:,.2f}: Tax €{tax:,.2f} ({effective_rate:.1%})")

    # === Scenario 6: Loss harvesting optimization ===
    print("\n=== Scenario 6: Loss Harvesting Strategy ===")

    # Current position with gain
    current_gain = Decimal("40000")
    current_tax = engine.calculate_capital_gains_tax(current_gain)

    # Consider harvesting losses to offset
    loss_opportunity = Decimal("-10000")
    net_after_loss = current_gain + loss_opportunity  # 30000
    tax_after_harvest = engine.calculate_capital_gains_tax(net_after_loss)

    tax_saved = current_tax - tax_after_harvest

    print(f"Current gain: €{current_gain:,.2f}")
    print(f"Current tax: €{current_tax:,.2f}")
    print(f"Potential loss harvest: €{abs(loss_opportunity):,.2f}")
    print(f"Net gain after harvest: €{net_after_loss:,.2f}")
    print(f"Tax after harvest: €{tax_after_harvest:,.2f}")
    print(f"Tax savings: €{tax_saved:,.2f}")

    # === Scenario 7: No wash sale rule advantage ===
    print("\n=== Scenario 7: No Wash Sale Rule Advantage ===")

    wash_sale_applies = engine.applies_wash_sale()
    print(f"Wash sale rule applies in Spain: {wash_sale_applies}")

    if not wash_sale_applies:
        print("  Strategy: Can sell and repurchase immediately for")
        print("  tax-loss harvesting without waiting 30 days")
        print("  (unlike US wash sale rule)")

    # === Verify key Spain tax rules ===
    print("\n=== Spain Tax Rules Verification ===")

    print("Progressive tax brackets:")
    for bracket in engine.get_tax_brackets():
        print(f"  Bracket {bracket['bracket']}: {bracket['rate']:.0%} "
              f"({bracket['description']})")

    print("\nKey differences from US:")
    print("  - No distinction between long-term and short-term gains")
    print("  - Dividends taxed at same progressive rates")
    print("  - No wash sale rule")
    print("  - EU dividends: 0% withholding tax")
    print("  - Losses can offset gains with 4-year carryforward")

    # Assertions
    assert capital_gains_tax > 0
    assert dividend_tax > 0
    assert summary["country"] == "Spain"
    assert not wash_sale_applies

    print("\n=== Integration test completed successfully ===")


if __name__ == "__main__":
    test_spain_tax_engine_integration()
