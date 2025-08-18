#!/bin/bash

echo "🚀 Sequential AI Manual Processor - Starting Services"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if port is in use
check_port() {
    lsof -i :$1 >/dev/null 2>&1
    return $?
}

# Function to kill process on port
kill_port() {
    local PORT=$1
    local PID=$(lsof -ti :$PORT)
    if [ ! -z "$PID" ]; then
        echo -e "${YELLOW}Stopping process on port $PORT (PID: $PID)...${NC}"
        kill -9 $PID 2>/dev/null
        sleep 1
    fi
}

# Check and clean ports if needed
echo -e "${YELLOW}🔍 Checking for existing processes...${NC}"
if check_port 8888; then
    kill_port 8888
fi
if check_port 3000; then
    kill_port 3000
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}🐍 Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}🐍 Activating Python virtual environment...${NC}"
source venv/bin/activate

# Install Python dependencies if needed
echo -e "${YELLOW}📚 Checking Python dependencies...${NC}"
pip install -q Flask flask-cors PyPDF2 PyMuPDF pdf2image playwright 2>/dev/null

# Check if Playwright browsers are installed
if [ ! -d "$HOME/Library/Caches/ms-playwright" ]; then
    echo -e "${YELLOW}🌐 Installing Playwright browsers...${NC}"
    playwright install chromium
else
    echo -e "${GREEN}✅ Playwright browsers already installed${NC}"
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing Node dependencies...${NC}"
    npm install
else
    echo -e "${GREEN}✅ Node modules already installed${NC}"
fi

# Start backend server
echo -e "${YELLOW}🚀 Starting backend server on port 8888...${NC}"
python3 -u server_new.py > backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend server started (PID: $BACKEND_PID)${NC}"

# Wait for backend to be ready
echo -e "${YELLOW}⏳ Waiting for backend server to initialize...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:8888/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend server is ready!${NC}"
        break
    fi
    sleep 1
done

# Start frontend
echo -e "${YELLOW}🚀 Starting frontend server on port 3000...${NC}"
npm start > frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✅ Frontend server starting (PID: $FRONTEND_PID)${NC}"

echo ""
echo "=================================================="
echo -e "${GREEN}✨ All services started successfully!${NC}"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8888"
echo "📖 API Docs: http://localhost:8888/"
echo ""
echo -e "${YELLOW}To stop all services, run: ./stop_new.sh${NC}"
echo -e "${YELLOW}Or press Ctrl+C in this terminal${NC}"
echo ""
echo "Backend logs: tail -f backend.log"
echo "Frontend logs: tail -f frontend.log"
echo "=================================================="

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    kill_port 8888
    kill_port 3000
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Set up trap to cleanup on Ctrl+C
trap cleanup INT

# Keep script running and show logs
echo ""
echo -e "${YELLOW}📋 Showing backend logs (backend.log):${NC}"
echo -e "${YELLOW}(Frontend logs in frontend.log)${NC}"
echo "=================================================="
tail -f backend.log