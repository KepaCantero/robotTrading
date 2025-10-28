"""
Cost Analysis API endpoints.

This module provides FastAPI endpoints for cost analysis functionality
including cost breakdown, profitability validation, and Cost Impact Ratio (CIR) analysis.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from app.backtesting.models import Trade, TradeStatus
from app.services.cost_analysis_service import CostAnalysisResult, CostAnalysisService

router = APIRouter(prefix="/cost-analysis", tags=["cost-analysis"])


def get_cost_analysis_service() -> CostAnalysisService:
    """Get cost analysis service instance."""
    return CostAnalysisService()


@router.post("/analyze-trade")
async def analyze_trade_costs(
    trade_data: Dict[str, Any],
    service: CostAnalysisService = Depends(get_cost_analysis_service),
):
    """Analyze costs for a single trade."""
    try:
        # Convert trade data to Trade object
        trade = Trade(
            trade_id=trade_data["id"],  # Map 'id' to 'trade_id'
            symbol=trade_data["symbol"],
            side=trade_data["side"],  # Use string directly
            quantity=Decimal(str(trade_data["quantity"])),
            entry_price=Decimal(str(trade_data["entry_price"])),
            exit_price=Decimal(str(trade_data.get("exit_price", trade_data["entry_price"]))),
            entry_time=datetime.fromisoformat(trade_data["entry_time"]),
            exit_time=datetime.fromisoformat(trade_data.get("exit_time", trade_data["entry_time"])),
            pnl=Decimal(str(trade_data.get("pnl", 0))),
            status=TradeStatus(trade_data.get("status", "closed")),
            commission=Decimal(str(trade_data.get("commission", 0))),
            slippage=Decimal(str(trade_data.get("slippage", 0))),
        )

        market_data = trade_data.get("market_data", {})

        breakdown = service.analyze_trade_costs(trade, market_data)

        return {
            "trade_id": breakdown.trade_id,
            "symbol": breakdown.symbol,
            "order_type": breakdown.order_type.value,
            "quantity": float(breakdown.quantity),
            "execution_price": float(breakdown.execution_price),
            "costs": {
                "commission": float(breakdown.commission),
                "slippage": float(breakdown.slippage),
                "market_impact": float(breakdown.market_impact),
                "infrastructure": float(breakdown.infrastructure_cost),
                "borrowing": float(breakdown.borrowing_cost),
                "total": float(breakdown.total_cost),
            },
            "metrics": {
                "cost_percentage": float(breakdown.cost_percentage),
                "cost_impact_ratio": float(breakdown.cost_impact_ratio),
            },
            "timestamp": breakdown.timestamp.isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error analyzing trade costs: {str(e)}")


@router.post("/analyze-strategy")
async def analyze_strategy_costs(
    strategy_data: Dict[str, Any],
    service: CostAnalysisService = Depends(get_cost_analysis_service),
):
    """Analyze costs for an entire trading strategy."""
    try:
        strategy_name = strategy_data["strategy_name"]
        trades_data = strategy_data["trades"]
        market_data = strategy_data.get("market_data", {})

        # Convert trades data to Trade objects
        trades = []
        for trade_data in trades_data:
            trade = Trade(
                trade_id=trade_data["id"],  # Map 'id' to 'trade_id'
                symbol=trade_data["symbol"],
                side=trade_data["side"],  # Use string directly
                quantity=Decimal(str(trade_data["quantity"])),
                entry_price=Decimal(str(trade_data["entry_price"])),
                exit_price=Decimal(str(trade_data.get("exit_price", trade_data["entry_price"]))),
                entry_time=datetime.fromisoformat(trade_data["entry_time"]),
                exit_time=datetime.fromisoformat(
                    trade_data.get("exit_time", trade_data["entry_time"])
                ),
                pnl=Decimal(str(trade_data.get("pnl", 0))),
                status=TradeStatus(trade_data.get("status", "closed")),
                commission=Decimal(str(trade_data.get("commission", 0))),
                slippage=Decimal(str(trade_data.get("slippage", 0))),
            )
            trades.append(trade)

        result = service.analyze_strategy_costs(trades, strategy_name, market_data)

        return {
            "strategy_name": result.strategy_name,
            "analysis_period": {
                "start": result.analysis_period[0].isoformat(),
                "end": result.analysis_period[1].isoformat(),
            },
            "summary": {
                "total_trades": result.total_trades,
                "total_costs": float(result.total_costs),
                "gross_profit": float(result.gross_profit),
                "net_profit": float(result.net_profit),
                "cost_impact_ratio": float(result.cost_impact_ratio),
                "profitability_threshold": float(result.profitability_threshold),
            },
            "cost_breakdown": {
                "commission": float(result.total_commission),
                "slippage": float(result.total_slippage),
                "market_impact": float(result.total_market_impact),
                "infrastructure": float(result.total_infrastructure),
                "borrowing": float(result.total_borrowing),
            },
            "validation": {
                "is_profitable": result.is_profitable,
                "exceeds_cost_threshold": result.exceeds_cost_threshold,
                "is_valid": service.validate_profitability(result),
            },
            "recommendations": result.recommendations,
            "trade_breakdowns": [
                {
                    "trade_id": bd.trade_id,
                    "symbol": bd.symbol,
                    "total_cost": float(bd.total_cost),
                    "cost_percentage": float(bd.cost_percentage),
                    "cost_impact_ratio": float(bd.cost_impact_ratio),
                }
                for bd in result.cost_breakdowns
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error analyzing strategy costs: {str(e)}")


@router.post("/validate-profitability")
async def validate_profitability(
    analysis_data: Dict[str, Any],
    service: CostAnalysisService = Depends(get_cost_analysis_service),
):
    """Validate profitability of a trading strategy."""
    try:
        # Create CostAnalysisResult from input data
        result = CostAnalysisResult(
            strategy_name=analysis_data["strategy_name"],
            analysis_period=(
                datetime.fromisoformat(analysis_data["analysis_period"]["start"]),
                datetime.fromisoformat(analysis_data["analysis_period"]["end"]),
            ),
            total_trades=analysis_data["total_trades"],
            total_commission=Decimal(str(analysis_data.get("total_commission", 0))),
            total_slippage=Decimal(str(analysis_data.get("total_slippage", 0))),
            total_market_impact=Decimal(str(analysis_data.get("total_market_impact", 0))),
            total_infrastructure=Decimal(str(analysis_data.get("total_infrastructure", 0))),
            total_borrowing=Decimal(str(analysis_data.get("total_borrowing", 0))),
            total_costs=Decimal(str(analysis_data["total_costs"])),
            gross_profit=Decimal(str(analysis_data["gross_profit"])),
            net_profit=Decimal(str(analysis_data["net_profit"])),
            cost_impact_ratio=Decimal(str(analysis_data["cost_impact_ratio"])),
            profitability_threshold=Decimal("0.02"),  # Default threshold
            cost_breakdowns=[],
            is_profitable=analysis_data["is_profitable"],
            exceeds_cost_threshold=analysis_data["exceeds_cost_threshold"],
            recommendations=analysis_data.get("recommendations", []),
        )

        is_valid = service.validate_profitability(result)

        return {
            "strategy_name": result.strategy_name,
            "is_profitable": result.is_profitable,
            "exceeds_cost_threshold": result.exceeds_cost_threshold,
            "is_valid": is_valid,
            "cost_impact_ratio": float(result.cost_impact_ratio),
            "max_allowed_cir": float(service.max_cost_impact_ratio),
            "recommendations": result.recommendations,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error validating profitability: {str(e)}")


@router.get("/cost-parameters")
async def get_cost_parameters(
    service: CostAnalysisService = Depends(get_cost_analysis_service),
):
    """Get current cost parameters configuration."""
    return {
        "commission_rates": {
            asset_class: float(rate) for asset_class, rate in service.commission_rates.items()
        },
        "slippage_rates": {
            asset_class: float(rate) for asset_class, rate in service.slippage_rates.items()
        },
        "infrastructure_cost_per_trade": float(service.infrastructure_cost_per_trade),
        "borrowing_cost_rate": float(service.borrowing_cost_rate),
        "profitability_thresholds": {
            "min_profitability_threshold": float(service.min_profitability_threshold),
            "max_cost_impact_ratio": float(service.max_cost_impact_ratio),
        },
    }


@router.post("/cost-parameters")
async def update_cost_parameters(
    parameters: Dict[str, Any],
    service: CostAnalysisService = Depends(get_cost_analysis_service),
):
    """Update cost parameters configuration."""
    try:
        if "commission_rates" in parameters:
            for asset_class, rate in parameters["commission_rates"].items():
                if rate > 0.1:  # Max 10% commission
                    raise ValueError(
                        f"Commission rate for {asset_class} ({rate}) exceeds maximum allowed (0.1)"
                    )
            service.commission_rates = {
                asset_class: Decimal(str(rate))
                for asset_class, rate in parameters["commission_rates"].items()
            }

        if "slippage_rates" in parameters:
            for asset_class, rate in parameters["slippage_rates"].items():
                if rate > 0.05:  # Max 5% slippage
                    raise ValueError(
                        f"Slippage rate for {asset_class} ({rate}) exceeds maximum allowed (0.05)"
                    )
            service.slippage_rates = {
                asset_class: Decimal(str(rate))
                for asset_class, rate in parameters["slippage_rates"].items()
            }

        if "infrastructure_cost_per_trade" in parameters:
            service.infrastructure_cost_per_trade = Decimal(
                str(parameters["infrastructure_cost_per_trade"])
            )

        if "borrowing_cost_rate" in parameters:
            service.borrowing_cost_rate = Decimal(str(parameters["borrowing_cost_rate"]))

        if "profitability_thresholds" in parameters:
            thresholds = parameters["profitability_thresholds"]
            if "min_profitability_threshold" in thresholds:
                service.min_profitability_threshold = Decimal(
                    str(thresholds["min_profitability_threshold"])
                )
            if "max_cost_impact_ratio" in thresholds:
                service.max_cost_impact_ratio = Decimal(str(thresholds["max_cost_impact_ratio"]))

        return {
            "message": "Cost parameters updated successfully",
            "updated_parameters": parameters,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating cost parameters: {str(e)}")


@router.get("/cost-breakdown/{trade_id}")
async def get_cost_breakdown(
    trade_id: str, service: CostAnalysisService = Depends(get_cost_analysis_service)
):
    """Get detailed cost breakdown for a specific trade."""
    # This would typically fetch from database
    # For now, return a placeholder response
    return {
        "trade_id": trade_id,
        "message": "Cost breakdown retrieval not yet implemented",
        "note": "This endpoint would fetch cost breakdown from database",
    }


@router.get("/strategy-costs/{strategy_name}")
async def get_strategy_costs(
    strategy_name: str,
    service: CostAnalysisService = Depends(get_cost_analysis_service),
):
    """Get cost analysis results for a specific strategy."""
    # This would typically fetch from database
    # For now, return a placeholder response
    return {
        "strategy_name": strategy_name,
        "message": "Strategy cost analysis retrieval not yet implemented",
        "note": "This endpoint would fetch cost analysis from database",
    }
