# Simple Dashboard Implementation Prompt

## Task Overview
Create a terminal-based dashboard for monitoring trading performance, positions, and system status.

## Requirements
1. **Dashboard Data Models** (`app/dashboard/dashboard_data.py`)
   - PositionSummary: Individual position data
   - PerformanceMetrics: Trading performance metrics
   - SystemStatus: System health status
   - DashboardSnapshot: Complete dashboard snapshot

2. **Dashboard Service** (`app/dashboard/dashboard_service.py`)
   - Fetch data from ComplianceEngine
   - Aggregate positions, performance, and system status
   - Handle errors gracefully

3. **Terminal CLI** (`scripts/simple_dashboard.py`)
   - Auto-refresh mode (default 5s interval)
   - One-shot mode (--once)
   - JSON output mode (--json)
   - Color-coded display (green for profit, red for loss)

4. **Tests** (`tests/unit/dashboard/test_dashboard_service.py`)
   - Test data fetching
   - Test error handling
   - Test display formatting

## Validation
- All files compile successfully
- Tests pass
- Dashboard displays correctly in terminal
- JSON output is valid

## Dependencies
- Task 09 (Compliance Engine) - COMPLETED
