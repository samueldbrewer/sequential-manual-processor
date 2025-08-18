#!/bin/bash

echo "🚀 Starting Sequential Manual Processor (Cached Version)..."

# Kill any existing processes on the ports
echo "🔍 Checking for existing processes..."
lsof -ti:8888 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Give ports time to free up
sleep 1

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies if needed
echo "📚 Checking Python dependencies..."
pip install Flask flask-cors requests PyPDF2 PyMuPDF pdf2image pillow playwright 2>/dev/null

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
fi

# Create necessary directories
mkdir -p public/temp-pdfs
mkdir -p logs

# Start the cached backend server
echo "🎯 Starting cached backend server on port 8888..."
python -u server_cached.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Check if backend is running
if ! lsof -i:8888 > /dev/null 2>&1; then
    echo "❌ Backend failed to start. Check backend.log for errors."
    cat backend.log
    exit 1
fi

# Start the frontend
echo "🎨 Starting frontend on port 3000..."
npm start &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "✅ Application started successfully!"
echo "   🌐 Frontend: http://localhost:3000"
echo "   🔧 Backend:  http://localhost:8888"
echo "   📊 Using cached data for instant responses!"
echo ""
echo "📝 Monitoring logs (press Ctrl+C to stop)..."
echo ""

# Monitor the backend log
tail -f backend.log