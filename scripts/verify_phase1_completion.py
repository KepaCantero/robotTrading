#!/usr/bin/env python3
"""
Phase 1 Completion Verification Script

This script verifies that Phase 1 of the Clean Architecture refactoring
has been completed successfully.
"""
import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_domain_entities_exist():
    """Test that all domain entity files exist."""
    print("Testing domain entity files exist...")

    entities = [
        "app/domain/entities/pre_trade_analysis.py",
        "app/domain/entities/post_trade_analysis.py",
        "app/domain/entities/portfolio_optimization.py",
    ]

    for entity in entities:
        path = project_root / entity
        if not path.exists():
            print(f"  ❌ {entity} does not exist")
            return False
        print(f"  ✅ {entity} exists")

    return True


def test_domain_entities_importable():
    """Test that all domain entities can be imported."""
    print("\nTesting domain entity imports...")

    try:
        from app.domain.entities.pre_trade_analysis import PreTradeAnalysis
        print("  ✅ PreTradeAnalysis imported")
    except ImportError as e:
        print(f"  ❌ PreTradeAnalysis import failed: {e}")
        return False

    try:
        from app.domain.entities.post_trade_analysis import PostTradeAnalysis
        print("  ✅ PostTradeAnalysis imported")
    except ImportError as e:
        print(f"  ❌ PostTradeAnalysis import failed: {e}")
        return False

    try:
        from app.domain.entities.portfolio_optimization import PortfolioOptimization
        print("  ✅ PortfolioOptimization imported")
    except ImportError as e:
        print(f"  ❌ PortfolioOptimization import failed: {e}")
        return False

    return True


def test_domain_entities_functional():
    """Test that domain entities work correctly."""
    print("\nTesting domain entity functionality...")

    from app.domain.entities.pre_trade_analysis import PreTradeAnalysis
    from app.domain.entities.post_trade_analysis import PostTradeAnalysis
    from app.domain.entities.portfolio_optimization import PortfolioOptimization

    # Test PreTradeAnalysis
    try:
        pre_trade = PreTradeAnalysis(
            can_execute=True,
            confidence=0.85,
            reasons=["Test"],
        )
        summary = pre_trade.get_execution_summary()
        assert isinstance(summary, str)
        print("  ✅ PreTradeAnalysis functional")
    except Exception as e:
        print(f"  ❌ PreTradeAnalysis failed: {e}")
        return False

    # Test PostTradeAnalysis
    try:
        post_trade = PostTradeAnalysis(
            order_id="TEST123",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            execution_price=Decimal("150.25"),
        )
        cost_summary = post_trade.get_cost_summary()
        assert isinstance(cost_summary, dict)
        print("  ✅ PostTradeAnalysis functional")
    except Exception as e:
        print(f"  ❌ PostTradeAnalysis failed: {e}")
        return False

    # Test PortfolioOptimization
    try:
        portfolio = PortfolioOptimization(
            weights={"AAPL": Decimal("0.5")},
            expected_return=0.1,
            expected_risk=0.15,
            sharpe_ratio=0.67,
        )
        top_positions = portfolio.get_top_positions()
        assert isinstance(top_positions, list)
        print("  ✅ PortfolioOptimization functional")
    except Exception as e:
        print(f"  ❌ PortfolioOptimization failed: {e}")
        return False

    return True


def test_compliance_engine_updated():
    """Test that compliance_engine.py has been updated."""
    print("\nTesting compliance_engine.py updates...")

    compliance_engine_path = project_root / "app/core/compliance_engine.py"

    if not compliance_engine_path.exists():
        print("  ❌ compliance_engine.py does not exist")
        return False

    content = compliance_engine_path.read_text()

    # Check that imports are present
    if "from app.domain.entities.pre_trade_analysis import PreTradeAnalysis" not in content:
        print("  ❌ PreTradeAnalysis import not found in compliance_engine.py")
        return False
    print("  ✅ PreTradeAnalysis import found")

    if "from app.domain.entities.post_trade_analysis import PostTradeAnalysis" not in content:
        print("  ❌ PostTradeAnalysis import not found in compliance_engine.py")
        return False
    print("  ✅ PostTradeAnalysis import found")

    if "from app.domain.entities.portfolio_optimization import PortfolioOptimization" not in content:
        print("  ❌ PortfolioOptimization import not found in compliance_engine.py")
        return False
    print("  ✅ PortfolioOptimization import found")

    # Check that old dataclass definitions are removed
    if "@dataclass\nclass PreTradeAnalysis:" in content:
        print("  ❌ Old PreTradeAnalysis dataclass still exists in compliance_engine.py")
        return False
    print("  ✅ Old PreTradeAnalysis dataclass removed")

    if "@dataclass\nclass PostTradeAnalysis:" in content:
        print("  ❌ Old PostTradeAnalysis dataclass still exists in compliance_engine.py")
        return False
    print("  ✅ Old PostTradeAnalysis dataclass removed")

    if "@dataclass\nclass PortfolioOptimization:" in content:
        print("  ❌ Old PortfolioOptimization dataclass still exists in compliance_engine.py")
        return False
    print("  ✅ Old PortfolioOptimization dataclass removed")

    return True


def test_domain_entities_init():
    """Test that domain/entities/__init__.py has been updated."""
    print("\nTesting domain/entities/__init__.py updates...")

    init_path = project_root / "app/domain/entities/__init__.py"

    if not init_path.exists():
        print("  ❌ app/domain/entities/__init__.py does not exist")
        return False

    content = init_path.read_text()

    if "PreTradeAnalysis" not in content:
        print("  ❌ PreTradeAnalysis not exported from __init__.py")
        return False
    print("  ✅ PreTradeAnalysis exported")

    if "PostTradeAnalysis" not in content:
        print("  ❌ PostTradeAnalysis not exported from __init__.py")
        return False
    print("  ✅ PostTradeAnalysis exported")

    if "PortfolioOptimization" not in content:
        print("  ❌ PortfolioOptimization not exported from __init__.py")
        return False
    print("  ✅ PortfolioOptimization exported")

    return True


def main():
    """Run all verification tests."""
    print("=" * 80)
    print("PHASE 1 CLEAN ARCHITECTURE REFACTORING VERIFICATION")
    print("=" * 80)

    tests = [
        test_domain_entities_exist,
        test_domain_entities_importable,
        test_domain_entities_functional,
        test_compliance_engine_updated,
        test_domain_entities_init,
    ]

    all_passed = True
    for test in tests:
        if not test():
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED - PHASE 1 COMPLETE")
        print("=" * 80)
        print("\nSummary:")
        print("  - 3 domain entity files created")
        print("  - All entities importable from domain layer")
        print("  - All entities functional with business logic")
        print("  - compliance_engine.py updated with proper imports")
        print("  - Old dataclass definitions removed from compliance_engine.py")
        print("  - Domain exports updated in __init__.py")
        print("\n✅ Ready for Phase 2: Extract Use Cases")
        return 0
    else:
        print("❌ SOME TESTS FAILED - PLEASE REVIEW")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
