#!/bin/bash

# Launch Script for Intent Classification Testing UI
# Version: 2.0
# Purpose: Start backend server and open testing UI

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Intent Classification Testing UI - v2.0                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/../../backend"
UI_FILE="$SCRIPT_DIR/test_ui.html"

# Check if backend exists
if [ ! -f "$BACKEND_DIR/app.py" ]; then
    echo "❌ Error: Backend not found at $BACKEND_DIR/app.py"
    exit 1
fi

# Check if UI exists
if [ ! -f "$UI_FILE" ]; then
    echo "❌ Error: UI not found at $UI_FILE"
    exit 1
fi

echo "✅ Files found"
echo ""

# Function to check if backend is running
check_backend() {
    curl -s http://localhost:5001/api/health > /dev/null 2>&1
    return $?
}

# Check if backend is already running
if check_backend; then
    echo "ℹ️  Backend is already running on http://localhost:5001"
    echo ""
else
    echo "🚀 Starting Flask backend server..."
    echo "   Location: $BACKEND_DIR"
    echo "   Port: 5001"
    echo ""

    # Start backend in background
    cd "$BACKEND_DIR"
    python3 app.py > /tmp/bedrock_backend.log 2>&1 &
    BACKEND_PID=$!

    echo "   Backend PID: $BACKEND_PID"
    echo "   Logs: /tmp/bedrock_backend.log"
    echo ""

    # Wait for backend to start (max 10 seconds)
    echo "⏳ Waiting for backend to start..."
    for i in {1..20}; do
        sleep 0.5
        if check_backend; then
            echo "✅ Backend started successfully!"
            echo ""
            break
        fi
        if [ $i -eq 20 ]; then
            echo "❌ Backend failed to start. Check logs at /tmp/bedrock_backend.log"
            exit 1
        fi
    done
fi

# Check backend health
echo "🔍 Checking backend health..."
HEALTH_RESPONSE=$(curl -s http://localhost:5001/api/health)
if [ $? -eq 0 ]; then
    echo "✅ Backend is healthy"
    echo ""
else
    echo "❌ Backend health check failed"
    exit 1
fi

# Open UI in default browser
echo "🌐 Opening Testing UI in your browser..."
echo "   File: $UI_FILE"
echo ""

# Detect OS and open browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open "$UI_FILE"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open "$UI_FILE" 2>/dev/null || firefox "$UI_FILE" 2>/dev/null || google-chrome "$UI_FILE" 2>/dev/null
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    start "$UI_FILE"
else
    echo "⚠️  Could not detect OS. Please open manually: $UI_FILE"
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Testing UI is ready!                                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "📍 Backend URL: http://localhost:5001"
echo "📍 UI File: file://$UI_FILE"
echo ""
echo "📊 You can now:"
echo "   • Test individual queries by clicking on them"
echo "   • Test all 27 queries with the 'Test All Queries' button"
echo "   • Test custom queries using the input field"
echo "   • View real-time accuracy metrics in the header"
echo ""
echo "💡 Tip: Keep this terminal open to see backend logs"
echo "📝 Backend logs: tail -f /tmp/bedrock_backend.log"
echo ""
echo "🛑 To stop the backend: kill $BACKEND_PID"
echo ""
echo "Press Ctrl+C to exit and stop the backend server"
echo ""

# Keep script running and tail logs
if [ ! -z "$BACKEND_PID" ]; then
    echo "═══════════════════════════════════════════════════════════════"
    echo "Backend Logs (live):"
    echo "═══════════════════════════════════════════════════════════════"
    tail -f /tmp/bedrock_backend.log &
    TAIL_PID=$!

    # Cleanup on exit
    trap "kill $BACKEND_PID $TAIL_PID 2>/dev/null; echo ''; echo '🛑 Backend stopped'; exit 0" INT TERM

    # Wait for backend process
    wait $BACKEND_PID
else
    echo "Backend was already running. Press Ctrl+C to exit."
    # Just wait for interrupt
    trap "echo ''; echo '👋 Exiting...'; exit 0" INT TERM
    while true; do sleep 1; done
fi
