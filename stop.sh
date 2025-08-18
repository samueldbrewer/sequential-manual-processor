#!/bin/bash

# Sequential AI Manual Processor - Stop Script
# This script stops all running services

echo "🛑 Sequential AI Manual Processor - Stopping Services"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Kill backend server
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${YELLOW}Stopping backend server (PID: $BACKEND_PID)...${NC}"
        kill -9 $BACKEND_PID
        echo -e "${GREEN}✅ Backend server stopped${NC}"
    fi
    rm .backend.pid
fi

# Kill frontend server
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${YELLOW}Stopping frontend server (PID: $FRONTEND_PID)...${NC}"
        kill -9 $FRONTEND_PID
        echo -e "${GREEN}✅ Frontend server stopped${NC}"
    fi
    rm .frontend.pid
fi

# Kill any remaining processes on ports
if lsof -Pi :8888 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}Cleaning up port 8888...${NC}"
    kill -9 $(lsof -Pi :8888 -sTCP:LISTEN -t)
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}Cleaning up port 3000...${NC}"
    kill -9 $(lsof -Pi :3000 -sTCP:LISTEN -t)
fi

# Kill any Python processes running server.py
pkill -f "python.*server.py" 2>/dev/null
pkill -f "python3.*server.py" 2>/dev/null

echo ""
echo "=================================================="
echo -e "${GREEN}✨ All services stopped successfully!${NC}"
echo "=================================================="