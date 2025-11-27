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

# ============================================================================
# AWS ACCOUNT SELECTION - Smart account detection and configuration
# ============================================================================

echo -e "${CYAN}🔐 AWS ACCOUNT SELECTION${NC}"
echo ""

# Get current/default profile
CURRENT_PROFILE="${AWS_PROFILE:-default}"
CURRENT_ACCOUNT=$(aws sts get-caller-identity --profile "$CURRENT_PROFILE" --query Account --output text 2>/dev/null || echo "N/A")

echo -e "Current Profile: ${YELLOW}${CURRENT_PROFILE}${NC}"
echo -e "Current Account: ${YELLOW}${CURRENT_ACCOUNT}${NC}"
echo ""

# Ask if this is correct
echo -e "${YELLOW}Is this the correct AWS account?${NC}"
echo ""
echo "  [1] Yes, proceed with account ${CURRENT_ACCOUNT}"
echo "  [2] No, I want to use a different account"
echo ""
read -p "Enter choice (1 or 2): " ACCOUNT_CHOICE

if [[ "$ACCOUNT_CHOICE" == "1" ]]; then
    AWS_PROFILE="$CURRENT_PROFILE"
    AWS_ACCOUNT="$CURRENT_ACCOUNT"
    echo ""
    echo -e "${GREEN}✓ Using account: ${AWS_ACCOUNT}${NC}"
else
    echo ""
    echo -e "${YELLOW}Enter the AWS Account ID you want to use:${NC}"
    read -p "Account ID (12 digits): " TARGET_ACCOUNT_ID

    if ! [[ "$TARGET_ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
        echo -e "${RED}Invalid account ID format. Must be 12 digits.${NC}"
        exit 1
    fi

    echo ""
    echo "Searching existing profiles for account ${TARGET_ACCOUNT_ID}..."

    FOUND_PROFILE=""
    while IFS= read -r profile; do
        if [[ -n "$profile" ]]; then
            PROFILE_ACCOUNT=$(aws sts get-caller-identity --profile "$profile" --query Account --output text 2>/dev/null || echo "")
            if [[ "$PROFILE_ACCOUNT" == "$TARGET_ACCOUNT_ID" ]]; then
                FOUND_PROFILE="$profile"
                break
            fi
        fi
    done < <(aws configure list-profiles 2>/dev/null)

    if [[ -n "$FOUND_PROFILE" ]]; then
        echo -e "${GREEN}✓ Found existing profile '${FOUND_PROFILE}' with account ${TARGET_ACCOUNT_ID}${NC}"
        AWS_PROFILE="$FOUND_PROFILE"
        AWS_ACCOUNT="$TARGET_ACCOUNT_ID"
    else
        echo -e "${YELLOW}No existing profile found for account ${TARGET_ACCOUNT_ID}${NC}"
        echo ""
        echo -e "${CYAN}Let's configure AWS credentials for this account:${NC}"
        echo ""

        read -p "Profile name (e.g., pf-${TARGET_ACCOUNT_ID}): " NEW_PROFILE_NAME
        if [[ -z "$NEW_PROFILE_NAME" ]]; then
            NEW_PROFILE_NAME="pf-${TARGET_ACCOUNT_ID}"
        fi

        echo ""
        echo -e "${YELLOW}Enter AWS credentials for account ${TARGET_ACCOUNT_ID}:${NC}"
        echo ""

        read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
        if [[ -z "$AWS_ACCESS_KEY_ID" ]]; then
            echo -e "${RED}Access Key ID is required. Aborting.${NC}"
            exit 1
        fi

        echo -e "${YELLOW}AWS Secret Access Key (will be visible - clear screen after):${NC}"
        read -p "> " AWS_SECRET_ACCESS_KEY
        if [[ -z "$AWS_SECRET_ACCESS_KEY" ]]; then
            echo -e "${RED}Secret Access Key is required. Aborting.${NC}"
            exit 1
        fi
        echo -e "\033[1A\033[2K> ********** (hidden)"

        echo ""
        echo "Configuring profile '${NEW_PROFILE_NAME}'..."

        aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID" --profile "$NEW_PROFILE_NAME"
        aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY" --profile "$NEW_PROFILE_NAME"
        aws configure set region "us-east-1" --profile "$NEW_PROFILE_NAME"
        aws configure set output "json" --profile "$NEW_PROFILE_NAME"

        echo "Verifying credentials..."
        VERIFY_ACCOUNT=$(aws sts get-caller-identity --profile "$NEW_PROFILE_NAME" --query Account --output text 2>/dev/null || echo "ERROR")

        if [[ "$VERIFY_ACCOUNT" == "$TARGET_ACCOUNT_ID" ]]; then
            echo -e "${GREEN}✓ Profile '${NEW_PROFILE_NAME}' configured successfully!${NC}"
            echo -e "${GREEN}✓ Verified account: ${VERIFY_ACCOUNT}${NC}"
            AWS_PROFILE="$NEW_PROFILE_NAME"
            AWS_ACCOUNT="$TARGET_ACCOUNT_ID"
        else
            echo -e "${RED}❌ Credentials verification failed!${NC}"
            echo "   Expected account: $TARGET_ACCOUNT_ID"
            echo "   Got account: $VERIFY_ACCOUNT"
            exit 1
        fi
    fi
fi

echo ""

# Export AWS_PROFILE for use by pf_proxy.py
export AWS_PROFILE

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

# Display AWS Account Information (using selected profile)
echo -e "${CYAN}☁️  AWS Account Information:${NC}"
echo "────────────────────────────────────────────────────────────────────────────"
AWS_IDENTITY=$(aws sts get-caller-identity --profile "$AWS_PROFILE" 2>/dev/null)
if [ $? -eq 0 ]; then
    AWS_USER=$(echo "$AWS_IDENTITY" | grep -o '"Arn": "[^"]*"' | cut -d'"' -f4 | awk -F'/' '{print $NF}')
    AWS_REGION=$(aws configure get region --profile "$AWS_PROFILE" 2>/dev/null || echo "us-east-1")

    echo "  • Account ID:     $AWS_ACCOUNT"
    echo "  • User/Role:      $AWS_USER"
    echo "  • Region:         $AWS_REGION"
    echo "  • Profile:        $AWS_PROFILE"
else
    echo -e "  ${YELLOW}⚠️  Unable to get AWS credentials${NC}"
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
