#!/bin/bash

# Launch ProjectForce Agent Demo
# This script starts all necessary services

echo "================================================"
echo "  ProjectForce Agent Demo Launcher"
echo "================================================"
echo ""

# Kill any existing instances
echo "🧹 Cleaning up old processes..."
pkill -f "pf_proxy.py" 2>/dev/null
pkill -f "python.*app.py" 2>/dev/null
pkill -f "http.server" 2>/dev/null
sleep 2

# Change to testing/ui directory
cd "$(dirname "$0")"

echo ""
echo "📂 Working directory: $(pwd)"
echo ""

# Start Flask backend (port 5001)
echo "1️⃣  Starting Flask backend on port 5001..."
cd ../../backend
python3 app.py > /tmp/flask_backend.log 2>&1 &
FLASK_PID=$!
echo "   ✅ Flask backend started (PID: $FLASK_PID)"
sleep 3

# Check if Flask is running
if ! curl -s http://localhost:5001/api/health > /dev/null 2>&1; then
    echo "   ❌ Flask backend failed to start"
    echo "   Check logs: tail -f /tmp/flask_backend.log"
    exit 1
fi

# Start CORS Proxy (port 5003)
echo ""
echo "2️⃣  Starting CORS Proxy on port 5003..."
cd ../testing/ui
python3 pf_proxy.py > /tmp/pf_proxy.log 2>&1 &
PROXY_PID=$!
echo "   ✅ CORS Proxy started (PID: $PROXY_PID)"
sleep 2

# Start simple HTTP server for UI (port 8000)
echo ""
echo "3️⃣  Starting UI server on port 8000..."
python3 -m http.server 8000 > /tmp/ui_server.log 2>&1 &
UI_PID=$!
echo "   ✅ UI server started (PID: $UI_PID)"
sleep 2

echo ""
echo "================================================"
echo "  🎉 All services started successfully!"
echo "================================================"
echo ""
echo "📊 Service Status:"
echo "   • Flask Backend:  http://localhost:5001  (PID: $FLASK_PID)"
echo "   • CORS Proxy:     http://localhost:5003  (PID: $PROXY_PID)"
echo "   • UI Server:      http://localhost:8000  (PID: $UI_PID)"
echo ""
echo "🌐 Open your browser to:"
echo ""
echo "   Option 1 (New Clean UI):"
echo "   → http://localhost:8000/index.html"
echo ""
echo "   Option 2 (Original Demo):"
echo "   → http://localhost:8000/pf_auth_demo.html"
echo ""
echo "================================================"
echo ""
echo "💡 Tips:"
echo "   • The new UI at /index.html has the card layout"
echo "   • It will auto-login and load projects"
echo "   • Switch between 'Current Orders' and 'Agent Chat' tabs"
echo ""
echo "📝 Logs:"
echo "   • Flask:  tail -f /tmp/flask_backend.log"
echo "   • Proxy:  tail -f /tmp/pf_proxy.log"
echo "   • UI:     tail -f /tmp/ui_server.log"
echo ""
echo "🛑 To stop all services:"
echo "   pkill -f pf_proxy.py"
echo "   pkill -f 'python.*app.py'"
echo "   pkill -f http.server"
echo ""
echo "Press Ctrl+C to view logs (services will keep running)"
echo "================================================"

# Wait for user interrupt
trap 'echo ""; echo "Services are still running in background"; exit 0' INT

# Show Flask logs
echo ""
echo "📋 Showing Flask backend logs (Ctrl+C to exit):"
echo ""
tail -f /tmp/flask_backend.log
