#!/bin/bash

##############################################################################
# Launch ProjectForce Auth Demo
#
# Starts the proxy server and opens the HTML page in the browser
##############################################################################

set -e

cd "$(dirname "$0")"

echo "════════════════════════════════════════════════════════════════════════════"
echo "🔐 ProjectForce API Authentication Demo"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Check if flask and flask-cors are installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not installed. Installing..."
    pip3 install flask flask-cors requests
fi

if ! python3 -c "import flask_cors" 2>/dev/null; then
    echo "⚠️  Flask-CORS not installed. Installing..."
    pip3 install flask-cors
fi

# Start the proxy server
echo "🚀 Starting CORS proxy server on port 5003..."
echo ""

python3 pf_proxy.py &
PROXY_PID=$!

# Wait for server to start
sleep 2

# Open the HTML page
echo ""
echo "🌐 Opening demo page in browser..."
open pf_auth_demo.html

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "✅ Demo is running!"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Proxy server: http://localhost:5003 (PID: $PROXY_PID)"
echo ""
echo "Press Ctrl+C to stop the proxy server"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping proxy server...'; kill $PROXY_PID 2>/dev/null; echo '✅ Demo stopped'; exit 0" INT

wait $PROXY_PID
