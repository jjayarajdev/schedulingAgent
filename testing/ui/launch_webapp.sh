#!/bin/bash
 
##############################################################################
# Launch ProjectForce UI on localhost:8000
#
# This script:
#   1. Starts the CORS proxy server on port 5003
#   2. Starts a Python HTTP server on port 8000
#   3. Opens the browser to http://localhost:8000/pf_auth_demo.html
##############################################################################
 
set -e

cd "$(dirname "$0")"

# Detect OS for cross-platform compatibility
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS="linux";;
        Darwin*)    OS="mac";;
        CYGWIN*|MINGW*|MSYS*) OS="windows";;
        *)          OS="unknown";;
    esac
    echo "$OS"
}

OS=$(detect_os)

# Detect Python command (python3 on Mac/Linux, python on Windows)
if command -v python3 &>/dev/null; then
    PYTHON="python3"
    PIP="pip3"
elif command -v python &>/dev/null; then
    PYTHON="python"
    PIP="pip"
else
    echo "❌ Python not found. Please install Python 3."
    exit 1
fi

echo "════════════════════════════════════════════════════════════════════════════"
echo "🚀 ProjectForce Web Application Launcher (OS: $OS, Python: $PYTHON)"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
 
# Display AWS Account Information
echo "☁️  AWS Account Information:"
echo "────────────────────────────────────────────────────────────────────────────"
if command -v aws &> /dev/null; then
    # Get AWS caller identity
    AWS_IDENTITY=$(aws sts get-caller-identity 2>/dev/null)
    if [ $? -eq 0 ]; then
        AWS_ACCOUNT=$(echo "$AWS_IDENTITY" | grep -o '"Account": "[^"]*"' | cut -d'"' -f4)
        AWS_USER=$(echo "$AWS_IDENTITY" | grep -o '"Arn": "[^"]*"' | cut -d'"' -f4 | awk -F'/' '{print $NF}')
        AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
        AWS_PROFILE_NAME="${AWS_PROFILE:-default}"
 
        echo "  • Account ID: $AWS_ACCOUNT"
        echo "  • User/Role:  $AWS_USER"
        echo "  • Region:     $AWS_REGION"
        echo "  • Profile:    $AWS_PROFILE_NAME"
    else
        echo "  ⚠️  Unable to get AWS credentials. Please configure AWS CLI."
        echo "  Run: aws configure"
    fi
else
    echo "  ⚠️  AWS CLI not installed. Cannot verify AWS account."
fi
echo "────────────────────────────────────────────────────────────────────────────"
echo ""
 
# Check if flask and flask-cors are installed
if ! $PYTHON -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not installed. Installing..."
    $PIP install flask flask-cors requests
fi

if ! $PYTHON -c "import flask_cors" 2>/dev/null; then
    echo "⚠️  Flask-CORS not installed. Installing..."
    $PIP install flask-cors
fi
 
# Cross-platform function to check and kill process on port
kill_port() {
    local port=$1
    if [ "$OS" = "windows" ]; then
        # Windows: use netstat and taskkill
        local pid=$(netstat -ano 2>/dev/null | grep ":$port " | grep LISTENING | awk '{print $5}' | head -1)
        if [ -n "$pid" ] && [ "$pid" != "0" ]; then
            echo "⚠️  Port $port is in use (PID: $pid). Killing..."
            taskkill //F //PID "$pid" 2>/dev/null || true
            sleep 1
        fi
    elif [ "$OS" = "mac" ]; then
        # Mac: use lsof
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "⚠️  Port $port is already in use. Killing existing process..."
            kill $(lsof -t -i:$port) 2>/dev/null || true
            sleep 1
        fi
    else
        # Linux: use lsof or ss
        if command -v lsof &>/dev/null; then
            if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                echo "⚠️  Port $port is already in use. Killing existing process..."
                kill $(lsof -t -i:$port) 2>/dev/null || true
                sleep 1
            fi
        elif command -v ss &>/dev/null; then
            local pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | head -1)
            if [ -n "$pid" ]; then
                echo "⚠️  Port $port is in use (PID: $pid). Killing..."
                kill "$pid" 2>/dev/null || true
                sleep 1
            fi
        fi
    fi
}

# Check and kill processes on ports 5003 and 8000
kill_port 5003
kill_port 8000

# Set up cross-platform temp directory for logs
if [ "$OS" = "windows" ]; then
    # Windows: use TEMP or current directory
    LOG_DIR="${TEMP:-$(pwd)}"
else
    # Mac/Linux: use /tmp
    LOG_DIR="/tmp"
fi

# Start the CORS proxy server
echo "🔌 Starting CORS proxy server on port 5003..."
# Set UTF-8 encoding for Windows to handle emojis in Python output
export PYTHONIOENCODING=utf-8
# Set AWS profile for pf-aws account (772634497954) - required for Lambda/Bedrock/Secrets Manager
export AWS_PROFILE="${AWS_PROFILE:-pf-aws}"
echo "  • Using AWS Profile: $AWS_PROFILE"
$PYTHON pf_proxy.py > "$LOG_DIR/pf_proxy.log" 2>&1 &
PROXY_PID=$!

# Wait for proxy to start
sleep 2

# Start the HTTP server on port 8000
echo "🌐 Starting HTTP server on port 8000..."
$PYTHON -m http.server 8000 > "$LOG_DIR/http_server.log" 2>&1 &
HTTP_PID=$!
 
# Wait for HTTP server to start
sleep 2
 
# Cross-platform browser opening
open_browser() {
    local url=$1
    if [ "$OS" = "windows" ]; then
        # Windows Git Bash: use explorer.exe or start with proper escaping
        explorer.exe "$url" 2>/dev/null || start "$url" 2>/dev/null || echo "⚠️  Could not open browser. Please open: $url"
    elif [ "$OS" = "mac" ]; then
        # Mac: use open command
        open "$url" 2>/dev/null || echo "⚠️  Could not open browser. Please open: $url"
    else
        # Linux: use xdg-open
        xdg-open "$url" 2>/dev/null || echo "⚠️  Could not open browser. Please open: $url"
    fi
}

echo "🌐 Opening UI in browser..."
open_browser "http://localhost:8000/index.local.html"
 
echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "✅ Web Application is running!"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "📡 Services:"
echo "  • CORS Proxy: http://localhost:5003 (PID: $PROXY_PID)"
echo "  • Web Server: http://localhost:8000 (PID: $HTTP_PID)"
echo ""
echo "🌐 Access Points:"
echo "  • LOCAL (Proxy):  http://localhost:8000/index.local.html"
echo "  • AWS (Gateway):  http://localhost:8000/index.aws.html"
echo "  • Auth Demo:      http://localhost:8000/pf_auth_demo.html"
echo "  • Test UI:        http://localhost:8000/test_ui.html"
echo ""
echo "📋 Logs:"
echo "  • Proxy:      $LOG_DIR/pf_proxy.log"
echo "  • HTTP:       $LOG_DIR/http_server.log"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""
 
# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $PROXY_PID 2>/dev/null || true
    kill $HTTP_PID 2>/dev/null || true
    sleep 1
    echo "✅ All servers stopped"
    exit 0
}
 
# Trap Ctrl+C
trap cleanup INT
 
# Wait for both processes
wait $PROXY_PID $HTTP_PID