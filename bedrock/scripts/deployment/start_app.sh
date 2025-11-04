#!/bin/bash

# ==============================================================================
# Start Full Application (Backend + React Frontend)
# ==============================================================================
# This script starts both the Flask backend and React frontend for testing
# ==============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  AWS Bedrock Multi-Agent System - Full Stack Startup        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."

    if [ ! -z "$BACKEND_PID" ]; then
        echo "   Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
    fi

    if [ ! -z "$FRONTEND_PID" ]; then
        echo "   Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    echo "✅ Services stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo "🚀 Starting Flask Backend..."
echo "   Directory: $BACKEND_DIR"
cd "$BACKEND_DIR"

# Kill any existing backend processes
pkill -f "python3 app.py" 2>/dev/null || true
sleep 1

# Start backend in background
python3 app.py > /tmp/bedrock_backend.log 2>&1 &
BACKEND_PID=$!

echo "   Backend PID: $BACKEND_PID"
echo "   Logs: /tmp/bedrock_backend.log"

# Wait for backend to start
echo "   Waiting for backend to be ready..."
for i in {1..20}; do
    sleep 0.5
    if curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
        echo "   ✅ Backend is ready!"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "   ❌ Backend failed to start. Check logs at /tmp/bedrock_backend.log"
        exit 1
    fi
done

echo ""

# Start frontend
echo "🎨 Starting React Frontend..."
echo "   Directory: $FRONTEND_DIR"
cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "   📦 Installing dependencies..."
    npm install
fi

# Start frontend in background
npm run dev > /tmp/bedrock_frontend.log 2>&1 &
FRONTEND_PID=$!

echo "   Frontend PID: $FRONTEND_PID"
echo "   Logs: /tmp/bedrock_frontend.log"

# Wait for frontend to start
echo "   Waiting for frontend to be ready..."
for i in {1..30}; do
    sleep 0.5
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo "   ✅ Frontend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ⚠️  Frontend may still be starting..."
    fi
done

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✅ Application Running                                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📍 Backend:  http://localhost:5001"
echo "📍 Frontend: http://localhost:5173"
echo ""
echo "Model Configuration:"
echo "  • Classification: Claude 3.5 Sonnet V2"
echo "  • Agents:        Claude 3.5 Sonnet V2 (supports supervisor)"
echo ""
echo "📊 Logs:"
echo "  • Backend:  tail -f /tmp/bedrock_backend.log"
echo "  • Frontend: tail -f /tmp/bedrock_frontend.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep script running and monitor processes
while true; do
    # Check if backend is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "❌ Backend process died. Check logs at /tmp/bedrock_backend.log"
        exit 1
    fi

    # Check if frontend is still running
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "❌ Frontend process died. Check logs at /tmp/bedrock_frontend.log"
        exit 1
    fi

    sleep 2
done
