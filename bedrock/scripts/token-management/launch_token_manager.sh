#!/bin/bash
# Launch Token Manager UI
# Simple HTTP server to serve the token manager interface

PORT=8080
HTML_FILE="token_manager.html"

echo "========================================"
echo "ProjectForce Token Manager"
echo "========================================"
echo ""
echo "Starting HTTP server on port $PORT..."
echo ""
echo "🌐 Open in your browser:"
echo "   http://localhost:$PORT/$HTML_FILE"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

# Start Python HTTP server
python3 -m http.server $PORT
