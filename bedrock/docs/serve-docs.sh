#!/bin/bash

# Simple HTTP server to view Swagger UI documentation
# This avoids CORS issues when loading the YAML file locally

echo "================================================"
echo "📚 Starting Documentation Server"
echo "================================================"
echo ""
echo "Opening Swagger UI in browser..."
echo "URL: http://localhost:8080/BULK_OPS_API_DOCS.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================================"
echo ""

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    # Open browser after 2 seconds
    (sleep 2 && open "http://localhost:8080/BULK_OPS_API_DOCS.html") &

    # Start Python HTTP server
    python3 -m http.server 8080
elif command -v python &> /dev/null; then
    # Fallback to Python 2
    (sleep 2 && open "http://localhost:8080/BULK_OPS_API_DOCS.html") &
    python -m SimpleHTTPServer 8080
else
    echo "❌ Error: Python not found"
    echo "Please install Python to run the documentation server"
    exit 1
fi
