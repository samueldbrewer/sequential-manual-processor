#!/bin/bash

# Sequential AI Manual Processor - Startup Script
# This script kills any existing instances and starts both backend and frontend servers

echo "🚀 Sequential AI Manual Processor - Starting Services"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Kill existing processes
echo -e "${YELLOW}🔍 Checking for existing processes...${NC}"

# Kill Python server on port 8888
if lsof -Pi :8888 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${RED}⚠️  Found existing backend server on port 8888${NC}"
    kill -9 $(lsof -Pi :8888 -sTCP:LISTEN -t)
    echo -e "${GREEN}✅ Killed existing backend server${NC}"
fi

# Kill React dev server on port 3000
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${RED}⚠️  Found existing frontend server on port 3000${NC}"
    kill -9 $(lsof -Pi :3000 -sTCP:LISTEN -t)
    echo -e "${GREEN}✅ Killed existing frontend server${NC}"
fi

# Kill any Python processes running server.py
pkill -f "python.*server.py" 2>/dev/null
pkill -f "python3.*server.py" 2>/dev/null

# Wait a moment for ports to be released
sleep 2

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}🐍 Activating Python virtual environment...${NC}"
source venv/bin/activate 2>/dev/null || . venv/bin/activate

# Install/update Python dependencies
echo -e "${YELLOW}📚 Installing Python dependencies...${NC}"
pip install -q --upgrade pip

# Check if requirements.txt exists and install from it
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
else
    # Fallback to manual installation
    pip install -q flask flask-cors playwright PyPDF2 PyMuPDF pdf2image pillow requests
fi

# Install Playwright browsers if not already installed
if [ ! -d "$HOME/Library/Caches/ms-playwright" ]; then
    echo -e "${YELLOW}🌐 Installing Playwright browsers...${NC}"
    playwright install chromium
else
    echo -e "${GREEN}✅ Playwright browsers already installed${NC}"
fi

# Check if node_modules exists, if not install
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing Node.js dependencies...${NC}"
    npm install
else
    echo -e "${GREEN}✅ Node modules already installed${NC}"
fi

# Start backend server in background with unbuffered output
echo -e "${YELLOW}🚀 Starting backend server on port 8888...${NC}"
python -u server.py > backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend server started (PID: $BACKEND_PID)${NC}"

# Wait for backend to be ready
echo -e "${YELLOW}⏳ Waiting for backend server to initialize...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8888/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend server is ready!${NC}"
        break
    fi
    sleep 1
done

# Start frontend server
echo -e "${YELLOW}🚀 Starting frontend server on port 3000...${NC}"
npm start &
FRONTEND_PID=$!
echo -e "${GREEN}✅ Frontend server starting (PID: $FRONTEND_PID)${NC}"

# Save PIDs to file for easy shutdown later
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

echo ""
echo "=================================================="
echo -e "${GREEN}✨ All services started successfully!${NC}"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8888"
echo "📖 API Docs: http://localhost:8888/docs"
echo ""
echo -e "${YELLOW}To stop all services, run: ./stop.sh${NC}"
echo -e "${YELLOW}Or press Ctrl+C in this terminal${NC}"
echo ""
echo "Backend logs: tail -f backend.log"
echo "=================================================="
echo ""
echo -e "${YELLOW}📋 Showing backend logs (backend.log):${NC}"
echo -e "${YELLOW}(Frontend logs shown above)${NC}"
echo "=================================================="

# Show backend logs in background
tail -f backend.log &
TAIL_PID=$!

# Wait for user interrupt
wait $FRONTEND_PID

# Clean up tail process
kill $TAIL_PID 2>/dev/null