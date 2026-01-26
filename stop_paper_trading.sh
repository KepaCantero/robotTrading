#!/bin/bash
# ============================================================================
# AlgoTrading - Paper Trading Stop Script
# ============================================================================
# This script stops the paper trading system gracefully.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${YELLOW}🛑 Stopping AlgoTrading Paper Trading System...${NC}"
echo ""

# Stop API server
if [ -f ".api_server.pid" ]; then
    API_PID=$(cat .api_server.pid)
    if ps -p $API_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}  Stopping API server (PID: $API_PID)...${NC}"
        kill $API_PID
        rm .api_server.pid
        echo -e "${GREEN}  ✅ API server stopped${NC}"
    else
        echo -e "${YELLOW}  ⚠️  API server not running${NC}"
        rm .api_server.pid
    fi
else
    # Try to find uvicorn process
    UVICORN_PID=$(pgrep -f "uvicorn app.api.paper_trading:app" || true)
    if [ -n "$UVICORN_PID" ]; then
        echo -e "${YELLOW}  Stopping API server (PID: $UVICORN_PID)...${NC}"
        kill $UVICORN_PID
        echo -e "${GREEN}  ✅ API server stopped${NC}"
    else
        echo -e "${YELLOW}  ⚠️  API server not running${NC}"
    fi
fi

# Stop dashboard
DASHBOARD_PID=$(pgrep -f "streamlit run app/dashboard/advanced_dashboard.py" || true)
if [ -n "$DASHBOARD_PID" ]; then
    echo -e "${YELLOW}  Stopping Dashboard (PID: $DASHBOARD_PID)...${NC}"
    kill $DASHBOARD_PID
    echo -e "${GREEN}  ✅ Dashboard stopped${NC}"
else
    echo -e "${YELLOW}  ⚠️  Dashboard not running${NC}"
fi

echo ""
echo -e "${GREEN}✅ All services stopped${NC}"
