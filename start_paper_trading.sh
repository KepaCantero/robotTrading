#!/bin/bash
# ============================================================================
# AlgoTrading - Paper Trading Startup Script
# ============================================================================
# This script starts the complete paper trading system:
# 1. Virtual environment activation
# 2. Background API server
# 3. Dashboard (foreground)
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Print banner
echo -e "${BLUE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║                  🚀 ALGOTRADING - PAPER TRADING 🚀                    ║
║                                                                        ║
║                    Professional Trading System                          ║
╚══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${GREEN}✅ .env created${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env and add your API keys before continuing${NC}"
    echo ""
    read -p "Press Enter to open .env in your editor, or Ctrl+C to cancel..."
    ${EDITOR:-nano} .env
fi

# Activate virtual environment
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Please run: python3 -m venv .venv"
    exit 1
fi

# Create logs directory
mkdir -p logs
mkdir -p data

# Check if API is already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  API server already running on port 8000${NC}"
else
    # Start API server in background
    echo -e "${BLUE}🚀 Starting API server in background...${NC}"
    nohup uvicorn app.api.paper_trading:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        > logs/api_server.log 2>&1 &
    API_PID=$!
    echo $API_PID > .api_server.pid
    echo -e "${GREEN}✅ API server started (PID: $API_PID)${NC}"
    echo -e "${GREEN}   Logs: logs/api_server.log${NC}"
    sleep 2
fi

# Check if dashboard is already running
if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Dashboard already running on port 8501${NC}"
else
    # Start dashboard
    echo -e "${BLUE}📊 Starting Dashboard...${NC}"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  PAPER TRADING SYSTEM READY${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  🌐 API Server:      ${BLUE}http://localhost:8000${NC}"
    echo -e "  📚 API Docs:       ${BLUE}http://localhost:8000/docs${NC}"
    echo -e "  📊 Dashboard:      ${BLUE}http://localhost:8501${NC}"
    echo ""
    echo -e "${YELLOW}  Press Ctrl+C to stop the dashboard${NC}"
    echo -e "${YELLOW}  API server continues running in background${NC}"
    echo -e "${YELLOW}  To stop API server: ./stop_paper_trading.sh${NC}"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""

    streamlit run app/dashboard/advanced_dashboard.py
fi
