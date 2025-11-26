#!/bin/bash

##############################################################################
# ProjectForce Advanced Web Application Launcher
##############################################################################
# Purpose: Cross-platform launcher for ProjectForce web UI
# Features: Platform detection, cross-platform port management, browser launch
# Compatible: Windows (Git Bash), macOS, Linux
##############################################################################

set -e

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============================================================================
# Platform Detection
# ============================================================================

PLATFORM="Unknown"
PYTHON_CMD="python3"
PIP_CMD="pip3"

if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    PLATFORM="Windows (Git Bash)"
    PYTHON_CMD="python"
    PIP_CMD="pip"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
else
    PLATFORM="Linux"
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
fi

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Create logs directory if it doesn't exist
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

PROXY_LOG="$LOG_DIR/pf_proxy.log"
HTTP_LOG="$LOG_DIR/http_server.log"

PROXY_PORT=5003
HTTP_PORT=8000

# ============================================================================
# Helper Functions
# ============================================================================

# Check if a port is in use (cross-platform)
is_port_in_use() {
    local PORT=$1

    if [[ "$PLATFORM" == "Windows (Git Bash)" ]]; then
        # Windows: Use netstat
        netstat -ano | grep ":$PORT " | grep "LISTENING" >/dev/null 2>&1
        return $?
    else
        # Unix/Mac: Try lsof first, fallback to netstat
        if command -v lsof &> /dev/null; then
            lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1
            return $?
        else
            netstat -an | grep ":$PORT " | grep "LISTEN" >/dev/null 2>&1
            return $?
        fi
    fi
}

# Kill process on port (cross-platform)
kill_port() {
    local PORT=$1

    echo -e "  ${YELLOW}⚠️  Port $PORT is in use. Attempting to free it...${NC}"

    if [[ "$PLATFORM" == "Windows (Git Bash)" ]]; then
        # Windows: Use netstat + taskkill
        local PID=$(netstat -ano | grep ":$PORT " | grep "LISTENING" | awk '{print $5}' | head -1)
        if [ -n "$PID" ]; then
            echo "  → Killing process $PID on port $PORT..."
            taskkill //F //PID $PID >/dev/null 2>&1 || true
            sleep 1
            echo -e "  ${GREEN}✓${NC} Port $PORT freed"
        fi
    else
        # Unix/Mac: Use lsof or fuser
        if command -v lsof &> /dev/null; then
            local PID=$(lsof -t -i:$PORT 2>/dev/null)
            if [ -n "$PID" ]; then
                echo "  → Killing process $PID on port $PORT..."
                kill $PID 2>/dev/null || true
                sleep 1
                echo -e "  ${GREEN}✓${NC} Port $PORT freed"
            fi
        elif command -v fuser &> /dev/null; then
            echo "  → Killing process on port $PORT..."
            fuser -k ${PORT}/tcp 2>/dev/null || true
            sleep 1
            echo -e "  ${GREEN}✓${NC} Port $PORT freed"
        else
            echo -e "  ${RED}⚠️  Cannot kill process - lsof/fuser not available${NC}"
        fi
    fi
}

# Open URL in browser (cross-platform)
open_browser() {
    local URL=$1

    if [[ "$PLATFORM" == "Windows (Git Bash)" ]]; then
        # Windows: Use start
        start "$URL" 2>/dev/null || true
    elif [[ "$PLATFORM" == "macOS" ]]; then
        # macOS: Use open
        open "$URL" 2>/dev/null || true
    else
        # Linux: Try xdg-open, then gnome-open, then firefox
        if command -v xdg-open &> /dev/null; then
            xdg-open "$URL" 2>/dev/null || true
        elif command -v gnome-open &> /dev/null; then
            gnome-open "$URL" 2>/dev/null || true
        elif command -v firefox &> /dev/null; then
            firefox "$URL" 2>/dev/null || true
        else
            echo -e "  ${YELLOW}⚠️  Could not auto-open browser. Please visit: $URL${NC}"
        fi
    fi
}

# Check and install Python dependencies
check_dependencies() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Checking Python Dependencies${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Check Flask
    if ! $PYTHON_CMD -c "import flask" 2>/dev/null; then
        echo -e "  ${YELLOW}⚠️  Flask not installed. Installing...${NC}"
        $PIP_CMD install flask flask-cors requests >/dev/null 2>&1
        echo -e "  ${GREEN}✓${NC} Flask installed"
    else
        echo -e "  ${GREEN}✓${NC} Flask installed"
    fi

    # Check Flask-CORS
    if ! $PYTHON_CMD -c "import flask_cors" 2>/dev/null; then
        echo -e "  ${YELLOW}⚠️  Flask-CORS not installed. Installing...${NC}"
        $PIP_CMD install flask-cors >/dev/null 2>&1
        echo -e "  ${GREEN}✓${NC} Flask-CORS installed"
    else
        echo -e "  ${GREEN}✓${NC} Flask-CORS installed"
    fi

    # Check Requests
    if ! $PYTHON_CMD -c "import requests" 2>/dev/null; then
        echo -e "  ${YELLOW}⚠️  Requests not installed. Installing...${NC}"
        $PIP_CMD install requests >/dev/null 2>&1
        echo -e "  ${GREEN}✓${NC} Requests installed"
    else
        echo -e "  ${GREEN}✓${NC} Requests installed"
    fi
}

# ============================================================================
# Main Script
# ============================================================================

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🚀 ProjectForce Advanced Web Application Launcher${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Display platform info
echo -e "${CYAN}📋 Platform Information:${NC}"
echo "────────────────────────────────────────────────────────────────────────────"
echo "  • Platform:       $PLATFORM"
echo "  • Python Command: $PYTHON_CMD"
echo "  • Pip Command:    $PIP_CMD"
echo "  • Working Dir:    $SCRIPT_DIR"
echo "  • Log Directory:  $LOG_DIR"
echo "────────────────────────────────────────────────────────────────────────────"
echo ""

# Display AWS Account Information
echo -e "${CYAN}☁️  AWS Account Information:${NC}"
echo "────────────────────────────────────────────────────────────────────────────"
if command -v aws &> /dev/null; then
    # Get AWS caller identity
    AWS_IDENTITY=$(aws sts get-caller-identity 2>/dev/null)
    if [ $? -eq 0 ]; then
        AWS_ACCOUNT=$(echo "$AWS_IDENTITY" | grep -o '"Account": "[^"]*"' | cut -d'"' -f4)
        AWS_USER=$(echo "$AWS_IDENTITY" | grep -o '"Arn": "[^"]*"' | cut -d'"' -f4 | awk -F'/' '{print $NF}')
        AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
        AWS_PROFILE_NAME="${AWS_PROFILE:-default}"

        echo "  • Account ID:     $AWS_ACCOUNT"
        echo "  • User/Role:      $AWS_USER"
        echo "  • Region:         $AWS_REGION"
        echo "  • Profile:        $AWS_PROFILE_NAME"
    else
        echo -e "  ${YELLOW}⚠️  Unable to get AWS credentials${NC}"
        echo "  Run: aws configure"
    fi
else
    echo -e "  ${YELLOW}⚠️  AWS CLI not installed${NC}"
fi
echo "────────────────────────────────────────────────────────────────────────────"

# Check dependencies
check_dependencies

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Preparing Ports${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check and free ports
if is_port_in_use $PROXY_PORT; then
    kill_port $PROXY_PORT
else
    echo -e "  ${GREEN}✓${NC} Port $PROXY_PORT is available"
fi

if is_port_in_use $HTTP_PORT; then
    kill_port $HTTP_PORT
else
    echo -e "  ${GREEN}✓${NC} Port $HTTP_PORT is available"
fi

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Starting Services${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Start the CORS proxy server
echo "  → Starting CORS proxy server on port $PROXY_PORT..."
# Set UTF-8 encoding for Windows to handle emoji characters
if [[ "$PLATFORM" == "Windows (Git Bash)" ]]; then
    PYTHONIOENCODING=utf-8 $PYTHON_CMD pf_proxy.py > "$PROXY_LOG" 2>&1 &
else
    $PYTHON_CMD pf_proxy.py > "$PROXY_LOG" 2>&1 &
fi
PROXY_PID=$!

# Wait for proxy to start
sleep 2

# Verify proxy started
if ps -p $PROXY_PID > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} CORS proxy running (PID: $PROXY_PID)"
else
    echo -e "  ${RED}✗${NC} CORS proxy failed to start"
    echo "  Check logs: $PROXY_LOG"
    exit 1
fi

# Start the HTTP server
echo "  → Starting HTTP server on port $HTTP_PORT..."
$PYTHON_CMD -m http.server $HTTP_PORT > "$HTTP_LOG" 2>&1 &
HTTP_PID=$!

# Wait for HTTP server to start
sleep 2

# Verify HTTP server started
if ps -p $HTTP_PID > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} HTTP server running (PID: $HTTP_PID)"
else
    echo -e "  ${RED}✗${NC} HTTP server failed to start"
    echo "  Check logs: $HTTP_LOG"
    kill $PROXY_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Opening Browser${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Open the browser
URL="http://localhost:$HTTP_PORT/index.local.html"
echo "  → Opening $URL..."
open_browser "$URL"
echo -e "  ${GREEN}✓${NC} Browser launched"

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Web Application is running!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}📡 Services:${NC}"
echo "  • CORS Proxy:     http://localhost:$PROXY_PORT (PID: $PROXY_PID)"
echo "  • Web Server:     http://localhost:$HTTP_PORT (PID: $HTTP_PID)"
echo ""

echo -e "${CYAN}🌐 Access Points:${NC}"
echo "  • LOCAL (Proxy):  http://localhost:$HTTP_PORT/index.local.html"
echo "  • AWS (Gateway):  http://localhost:$HTTP_PORT/index.aws.html"
echo "  • Auth Demo:      http://localhost:$HTTP_PORT/pf_auth_demo.html"
echo "  • Test UI:        http://localhost:$HTTP_PORT/test_ui.html"
echo ""

echo -e "${CYAN}📋 Logs:${NC}"
echo "  • Proxy:          $PROXY_LOG"
echo "  • HTTP:           $HTTP_LOG"
echo ""

echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# ============================================================================
# Cleanup and Signal Handling
# ============================================================================

cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping servers...${NC}"

    # Kill processes
    if ps -p $PROXY_PID > /dev/null 2>&1; then
        kill $PROXY_PID 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} CORS proxy stopped"
    fi

    if ps -p $HTTP_PID > /dev/null 2>&1; then
        kill $HTTP_PID 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} HTTP server stopped"
    fi

    sleep 1

    echo ""
    echo -e "${GREEN}✅ All servers stopped successfully${NC}"
    echo ""
    exit 0
}

# Trap Ctrl+C and other termination signals
trap cleanup INT TERM

# Wait for both processes to finish (or until interrupted)
wait $PROXY_PID $HTTP_PID
