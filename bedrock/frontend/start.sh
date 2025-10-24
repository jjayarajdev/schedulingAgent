#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Bedrock Agent Chat UI - Startup Script                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if agent_config.json exists and copy it
if [ -f "../agent_config.json" ]; then
    cp ../agent_config.json ./agent_config.json
    echo "✅ Loaded agent configuration"
else
    echo "⚠️  Warning: agent_config.json not found"
    echo "   Run: cd ../scripts && python3 complete_setup.py"
    echo ""
fi

# Start backend
echo "🚀 Starting Flask backend..."
cd backend
pip install -r requirements.txt > /dev/null 2>&1

# Start backend in background
python3 app.py &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID) on http://localhost:5001"
echo ""

# Wait for backend to start
sleep 3

# Start frontend
echo "🚀 Starting React frontend..."
cd ../frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo "✅ Frontend starting on http://localhost:3000"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Open your browser: http://localhost:3000"
echo "  Sample User: John Doe (CUST001)"
echo "  Press Ctrl+C to stop both servers"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Start frontend (this blocks)
npm run dev

# Cleanup on exit
kill $BACKEND_PID 2>/dev/null
