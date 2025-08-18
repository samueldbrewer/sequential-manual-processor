#!/bin/bash

echo "🛑 Sequential AI Manual Processor - Stopping Services"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to kill process on port
kill_port() {
    local PORT=$1
    local NAME=$2
    local PID=$(lsof -ti :$PORT)
    if [ ! -z "$PID" ]; then
        echo -e "${YELLOW}Stopping $NAME (PID: $PID)...${NC}"
        kill -9 $PID 2>/dev/null
        sleep 0.5
        echo -e "${GREEN}✅ $NAME stopped${NC}"
    else
        echo -e "${YELLOW}No $NAME running on port $PORT${NC}"
    fi
}

# Stop backend server
kill_port 8888 "backend server"

# Stop frontend server  
kill_port 3000 "frontend server"

# Clean up any remaining Node processes
echo -e "${YELLOW}Cleaning up port 3000...${NC}"
lsof -ti :3000 | xargs kill -9 2>/dev/null

echo ""
echo "=================================================="
echo -e "${GREEN}✨ All services stopped successfully!${NC}"
echo "=================================================="