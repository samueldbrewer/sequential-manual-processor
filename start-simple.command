#!/bin/bash

# Sequential AI Manual Processor - Quick Start (Double-click to run)
# This script can be double-clicked from Finder on macOS

# Change to script directory
cd "$(dirname "$0")"

# Clear terminal
clear

echo "🚀 Sequential AI Manual Processor"
echo "=================================="
echo ""

# Kill any existing processes silently
lsof -Pi :8888 -sTCP:LISTEN -t >/dev/null && kill -9 $(lsof -Pi :8888 -sTCP:LISTEN -t) 2>/dev/null
lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null && kill -9 $(lsof -Pi :3000 -sTCP:LISTEN -t) 2>/dev/null
pkill -f "python.*server.py" 2>/dev/null

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    echo "Visit: https://www.python.org/downloads/"
    read -p "Press Enter to exit..."
    exit 1
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16 or higher."
    echo "Visit: https://nodejs.org/"
    read -p "Press Enter to exit..."
    exit 1
fi

# Install Python dependencies if needed
echo "📦 Checking Python dependencies..."
pip3 install -q flask flask-cors playwright 2>/dev/null || {
    echo "Installing Python dependencies..."
    pip3 install flask flask-cors playwright
}

# Install Playwright browsers if needed
if [ ! -d "$HOME/Library/Caches/ms-playwright" ]; then
    echo "🌐 Installing browser for web scraping..."
    playwright install chromium
fi

# Install Node dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

# Start backend
echo ""
echo "🔧 Starting backend server..."
python3 server.py > backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend
sleep 3

# Start frontend
echo "🎨 Starting frontend application..."
echo ""
echo "=================================="
echo "✨ Opening in your browser..."
echo "=================================="
echo ""

# Open browser after a short delay
(sleep 5 && open http://localhost:3000) &

# Start React app
npm start

# When npm start is terminated, kill backend
kill $BACKEND_PID 2>/dev/null