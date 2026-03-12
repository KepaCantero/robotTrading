"""
Unit tests for Daily Reconciliation Service (R16)

Tests for the daily position reconciliation between broker and internal records.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.reconciliation import (
    DailyReconciler,
    DiscrepancyDetector,
    Position,
    ReconciliationResult,
)


class TestPosition:
    """Tests for Position dataclass"""

    def test_position_creation(self):
        """Test Position creation with valid data"""
        pos = Position(
            symbol="SAN.MC",
            quantity=Decimal("100"),
            avg_price=Decimal("10.50"),
            current_price=Decimal("11.00"),
            market_value=Decimal("1100.00"),
            currency="EUR",
        )
        assert pos.symbol == "SAN.MC"
        assert pos.quantity == Decimal("100")
        assert pos.currency == "EUR"

    def test_position_default_currency(self):
        """Test Position defaults to EUR currency"""
        pos = Position(
            symbol="REE.MC",
            quantity=Decimal("50"),
            avg_price=Decimal("20.00"),
            current_price=Decimal("21.00"),
            market_value=Decimal("1050.00"),
        )
        assert pos.currency == "EUR"

    def test_position_frozen(self):
        """Test Position is frozen (immutable)"""
        pos = Position(
            symbol="SAN.MC",
            quantity=Decimal("100"),
            avg_price=Decimal("10.50"),
            current_price=Decimal("11.00"),
            market_value=Decimal("1100.00"),
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            pos.quantity = Decimal("200")

    def test_position_to_dict(self):
        """Test Position serialization to dict"""
        pos = Position(
            symbol="SAN.MC",
            quantity=Decimal("100"),
            avg_price=Decimal("10.50"),
            current_price=Decimal("11.00"),
            market_value=Decimal("1100.00"),
        )
        result = pos.to_dict()
        assert result["symbol"] == "SAN.MC"
        assert result["quantity"] == "100"
        assert isinstance(result["quantity"], str)


class TestDiscrepancyDetector:
    """Tests for DiscrepancyDetector"""

    def test_quantity_tolerance_within(self):
        """Test quantity within tolerance (1 share) passes"""
        detector = DiscrepancyDetector()
        result = detector.detect_position_mismatch(
            broker_qty=Decimal("100"), internal_qty=Decimal("100")
        )
        assert result is None

    def test_quantity_tolerance_boundary(self):
        """Test quantity at tolerance boundary (1 share) passes"""
        detector = DiscrepancyDetector()
        result = detector.detect_position_mismatch(
            broker_qty=Decimal("100"), internal_qty=Decimal("101")
        )
        assert result is None  # Exactly at tolerance

    def test_quantity_mismatch_detected(self):
        """Test quantity mismatch detected (2 shares > 1 tolerance)"""
        detector = DiscrepancyDetector()
        result = detector.detect_position_mismatch(
            broker_qty=Decimal("100"), internal_qty=Decimal("98")
        )
        assert result is not None
        assert result["type"] == "QUANTITY_MISMATCH"
        assert result["difference"] == "2"
        assert result["severity"] == "MEDIUM"

    def test_quantity_mismatch_critical_severity(self):
        """Test CRITICAL severity for large quantity mismatch (>10 shares)"""
        detector = DiscrepancyDetector()
        result = detector.detect_position_mismatch(
            broker_qty=Decimal("100"), internal_qty=Decimal("85")
        )
        assert result is not None
        assert result["severity"] == "CRITICAL"  # 15 shares difference > 10

    def test_price_tolerance_within(self):
        """Test price within 0.1% tolerance passes"""
        detector = DiscrepancyDetector()
        result = detector.detect_price_mismatch(
            broker_price=Decimal("100.05"), internal_price=Decimal("100.00")
        )
        assert result is None  # 0.05% < 0.1%

    def test_price_mismatch_detected(self):
        """Test price mismatch detected (0.5% > 0.1% tolerance)"""
        detector = DiscrepancyDetector()
        result = detector.detect_price_mismatch(
            broker_price=Decimal("100.50"), internal_price=Decimal("100.00")
        )
        assert result is not None
        assert result["type"] == "PRICE_MISMATCH"
        assert result["difference_pct"] == "0.500%"

    def test_price_zero_internal(self):
        """Test price mismatch when internal price is zero"""
        detector = DiscrepancyDetector()
        result = detector.detect_price_mismatch(
            broker_price=Decimal("100.00"), internal_price=Decimal("0")
        )
        assert result is not None
        assert result["severity"] == "HIGH"

    def test_value_mismatch_within(self):
        """Test value within 0.5% tolerance passes"""
        detector = DiscrepancyDetector()
        result = detector.detect_value_mismatch(
            broker_value=Decimal("10000.00"), internal_value=Decimal("10030.00")
        )
        assert result is None  # 0.3% < 0.5%

    def test_value_mismatch_detected(self):
        """Test value mismatch detected"""
        detector = DiscrepancyDetector()
        result = detector.detect_value_mismatch(
            broker_value=Decimal("10100.00"), internal_value=Decimal("10000.00")
        )
        assert result is not None
        assert result["type"] == "VALUE_MISMATCH"

    def test_missing_positions_both_sides(self):
        """Test detection of missing positions in both systems"""
        detector = DiscrepancyDetector()
        broker_syms = {"SAN.MC", "REE.MC"}
        internal_syms = {"SAN.MC", "AAPL"}

        missing = detector.detect_missing_positions(broker_syms, internal_syms)

        assert len(missing) == 2
        assert any(d["symbol"] == "REE.MC" and d["type"] == "MISSING_IN_INTERNAL" for d in missing)
        assert any(d["symbol"] == "AAPL" and d["type"] == "MISSING_IN_BROKER" for d in missing)

    def test_missing_positions_critical_severity(self):
        """Test CRITICAL severity for phantom positions (missing in broker)"""
        detector = DiscrepancyDetector()
        broker_syms = {"SAN.MC"}
        internal_syms = {"SAN.MC", "AAPL"}

        missing = detector.detect_missing_positions(broker_syms, internal_syms)

        aapl_entry = next(d for d in missing if d["symbol"] == "AAPL")
        assert aapl_entry["severity"] == "CRITICAL"

    def test_comprehensive_discrepancy_detection(self):
        """Test comprehensive detection of all discrepancy types"""
        detector = DiscrepancyDetector()

        broker_positions = {
            "SAN.MC": {
                "quantity": Decimal("100"),
                "price": Decimal("10.00"),
                "value": Decimal("1000.00"),
            }
        }
        internal_positions = {
            "SAN.MC": {
                "quantity": Decimal("98"),  # Mismatch
                "price": Decimal("10.05"),  # Within tolerance
                "value": Decimal("985.00"),  # Will be checked too
            }
        }

        result = detector.detect_all_discrepancies(broker_positions, internal_positions)

        # At least quantity mismatch should be detected
        assert len(result["quantity_mismatches"]) >= 1
        assert result["quantity_mismatches"][0]["symbol"] == "SAN.MC"


class TestDailyReconciler:
    """Tests for DailyReconciler"""

    @pytest.mark.asyncio
    async def test_reconcile_all_matched(self):
        """Test reconciliation when all positions match"""
        reconciler = DailyReconciler()

        broker_positions = [
            Position(
                symbol="SAN.MC",
                quantity=Decimal("100"),
                avg_price=Decimal("10.00"),
                current_price=Decimal("10.50"),
                market_value=Decimal("1050.00"),
            )
        ]
        internal_positions = [
            Position(
                symbol="SAN.MC",
                quantity=Decimal("100"),
                avg_price=Decimal("10.00"),
                current_price=Decimal("10.50"),
                market_value=Decimal("1050.00"),
            )
        ]

        result = await reconciler.reconcile_positions(broker_positions, internal_positions)

        assert result.is_balanced is True
        assert result.total_positions == 1
        assert result.matched_positions == 1
        assert result.mismatched_positions == 0
        assert result.missing_positions == 0

    @pytest.mark.asyncio
    async def test_reconcile_quantity_mismatch(self):
        """Test reconciliation detects quantity mismatch"""
        reconciler = DailyReconciler()

        broker_positions = [
            Position(
                symbol="SAN.MC",
                quantity=Decimal("100"),
                avg_price=Decimal("10.00"),
                current_price=Decimal("10.50"),
                market_value=Decimal("1050.00"),
            )
        ]
        internal_positions = [
            Position(
                symbol="SAN.MC",
                quantity=Decimal("98"),  # Mismatch
                avg_price=Decimal("10.00"),
                current_price=Decimal("10.50"),
                market_value=Decimal("1029.00"),
            )
        ]

        result = await reconciler.reconcile_positions(broker_positions, internal_positions)

        assert result.is_balanced is False
        assert result.mismatched_positions == 1
        assert len(result.discrepancies) == 1
        assert result.discrepancies[0]["symbol"] == "SAN.MC"

    @pytest.mark.asyncio
    async def test_reconcile_missing_in_internal(self):
        """Test reconciliation detects position missing in internal"""
        reconciler = DailyReconciler()

        broker_positions = [
            Position(
                symbol="SAN.MC",
                quantity=Decimal("100"),
                avg_price=Decimal("10.00"),
                current_price=Decimal("10.50"),
                market_value=Decimal("1050.00"),
            )
        ]
        internal_positions = []  # Empty

        result = await reconciler.reconcile_positions(broker_positions, internal_positions)

        assert result.is_balanced is False
        assert result.missing_positions == 1
        assert result.discrepancies[0]["type"] == "INTERNAL_ONLY"
        assert result.discrepancies[0]["severity"] == "HIGH"

    @pytest.mark.asyncio
    async def test_reconcile_phantom_position(self):
        """Test reconciliation detects phantom position (missing in broker)"""
        reconciler = DailyReconciler()

        broker_positions = []  # Empty
        internal_positions = [
            Position(
                symbol="SAN.MC",
                quantity=Decimal("100"),
                avg_price=Decimal("10.00"),
                current_price=Decimal("10.50"),
                market_value=Decimal("1050.00"),
            )
        ]

        result = await reconciler.reconcile_positions(broker_positions, internal_positions)

        assert result.is_balanced is False
        assert result.missing_positions == 1
        assert result.discrepancies[0]["type"] == "BROKER_ONLY"
        assert result.discrepancies[0]["severity"] == "CRITICAL"

    def test_generate_report_balanced(self):
        """Test report generation for balanced reconciliation"""
        reconciler = DailyReconciler()

        result = ReconciliationResult(
            date=date.today(),
            total_positions=5,
            matched_positions=5,
            mismatched_positions=0,
            missing_positions=0,
            discrepancies=[],
            is_balanced=True,
        )

        report = reconciler.generate_reconciliation_report(result)

        assert "BALANCED" in report
        assert "- **Matched:** 5" in report
        assert "- **Mismatched:** 0" in report

    def test_generate_report_with_discrepancies(self):
        """Test report generation with discrepancies"""
        reconciler = DailyReconciler()

        result = ReconciliationResult(
            date=date.today(),
            total_positions=3,
            matched_positions=1,
            mismatched_positions=1,
            missing_positions=1,
            discrepancies=[
                {"symbol": "SAN.MC", "status": "MISMATCH", "severity": "HIGH"},
                {
                    "symbol": "REE.MC",
                    "status": "MISSING",
                    "type": "BROKER_ONLY",
                    "severity": "CRITICAL",
                },
            ],
            is_balanced=False,
        )

        report = reconciler.generate_reconciliation_report(result)

        assert "DISCREPANCIES" in report
        assert "SAN.MC" in report
        assert "REE.MC" in report
        assert "CRITICAL" in report

    def test_get_position_delta(self):
        """Test position delta calculation"""
        reconciler = DailyReconciler()

        broker_pos = Position(
            symbol="SAN.MC",
            quantity=Decimal("100"),
            avg_price=Decimal("10.00"),
            current_price=Decimal("10.50"),
            market_value=Decimal("1050.00"),
        )
        internal_pos = Position(
            symbol="SAN.MC",
            quantity=Decimal("98"),
            avg_price=Decimal("10.00"),
            current_price=Decimal("10.50"),
            market_value=Decimal("1029.00"),
        )

        delta = reconciler.get_position_delta("SAN.MC", broker_pos, internal_pos)

        assert delta["symbol"] == "SAN.MC"
        assert delta["delta_quantity"] == Decimal("2")
        assert delta["delta_value"] == Decimal("21.00")

    def test_tolerances_constants(self):
        """Test tolerance constants match R16 requirements"""
        assert DailyReconciler.QUANTITY_TOLERANCE == Decimal("1")
        assert DailyReconciler.PRICE_TOLERANCE_PCT == Decimal("0.001")
        assert DiscrepancyDetector.QUANTITY_TOLERANCE == Decimal("1")
        assert DiscrepancyDetector.PRICE_TOLERANCE_PCT == Decimal("0.001")


class TestReconciliationResult:
    """Tests for ReconciliationResult dataclass"""

    def test_result_creation(self):
        """Test ReconciliationResult creation"""
        result = ReconciliationResult(
            date=date.today(),
            total_positions=10,
            matched_positions=8,
            mismatched_positions=1,
            missing_positions=1,
            discrepancies=[],
            is_balanced=False,
        )
        assert result.total_positions == 10
        assert result.matched_positions == 8

    def test_result_to_dict(self):
        """Test ReconciliationResult serialization"""
        result = ReconciliationResult(
            date=date(2026, 2, 8),
            total_positions=5,
            matched_positions=5,
            mismatched_positions=0,
            missing_positions=0,
            is_balanced=True,
        )
        dict_result = result.to_dict()
        assert dict_result["date"] == "2026-02-08"
        assert dict_result["is_balanced"] is True


# Test imports work correctly
def test_imports():
    """Test that all main classes can be imported"""
    from app.services.reconciliation import (
        DailyReconciler,
        DiscrepancyDetector,
    )

    assert DailyReconciler is not None
    assert DiscrepancyDetector is not None
