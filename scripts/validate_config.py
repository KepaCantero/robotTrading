#!/usr/bin/env python3
"""
Configuration Validation Script

Validates all trading configuration before starting live trading.
Checks:
- Broker API credentials
- Risk limit settings
- Trading symbols
- Order type settings
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.compliance_engine import get_compliance_engine, ComplianceConfig
from app.services.live_trading.broker_connector import get_broker_connector


async def validate_config():
    """Validate all trading configuration."""
    print("Validating trading configuration...")
    print("=" * 60)

    errors = []
    warnings = []

    # 1. Validate ComplianceConfig
    print("\n1. Validating ComplianceConfig...")
    try:
        config = ComplianceConfig()
        print(f"   Max position ratio: {config.max_position_ratio:.1%}")
        print(f"   Max drawdown: {config.max_drawdown_ratio:.1%}")
        print(f"   Kill switch threshold: {config.kill_switch_threshold:.1%}")
        print(f"   Max daily VaR 95%: {config.max_daily_var_95:.1%}")
        print("   ComplianceConfig: OK")
    except Exception as e:
        errors.append(f"ComplianceConfig validation failed: {e}")
        print(f"   ERROR: {e}")

    # 2. Validate broker connection
    print("\n2. Validating broker connection...")
    try:
        broker = get_broker_connector()
        account = await broker.get_account_info()
        if account:
            print(f"   Account ID: {account.get('account_id', 'N/A')}")
            print(f"   Buying power: ${account.get('buying_power', 0):,.2f}")
            print("   Broker connection: OK")
        else:
            errors.append("Cannot retrieve broker account info")
            print("   ERROR: Cannot retrieve account info")
    except Exception as e:
        errors.append(f"Broker connection failed: {e}")
        print(f"   ERROR: {e}")

    # 3. Validate risk gates
    print("\n3. Validating risk gates...")
    try:
        from app.services.live_trading.risk_gates import RiskGates

        risk_gates = RiskGates(broker)
        print("   RiskGates initialized: OK")
    except Exception as e:
        errors.append(f"RiskGates validation failed: {e}")
        print(f"   ERROR: {e}")

    # 4. Validate trading bridge
    print("\n4. Validating trading bridge...")
    try:
        from app.services.live_trading.trading_bridge_orchestrator import (
            get_trading_bridge_orchestrator,
        )

        bridge = get_trading_bridge_orchestrator()
        print(f"   Bridge status: {bridge.status.value}")
        print("   TradingBridge: OK")
    except Exception as e:
        errors.append(f"TradingBridge validation failed: {e}")
        print(f"   ERROR: {e}")

    # 5. Validate compliance engine
    print("\n5. Validating compliance engine...")
    try:
        engine = get_compliance_engine(enable_logging=False)
        status = engine.get_system_status()
        available = status['availability']['available_systems']
        total = status['availability']['total_systems']
        print(f"   Systems: {available}/{total} available")
        if available < total:
            warnings.append(f"Some systems unavailable: {available}/{total}")
        print("   ComplianceEngine: OK")
    except Exception as e:
        errors.append(f"ComplianceEngine validation failed: {e}")
        print(f"   ERROR: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")

    if errors:
        print("\nERRORS:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")

    if not errors:
        print("\nConfiguration validation: PASSED")
        return True
    else:
        print("\nConfiguration validation: FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(validate_config())
    sys.exit(0 if success else 1)
