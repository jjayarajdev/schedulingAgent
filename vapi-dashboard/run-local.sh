#!/bin/bash
# Run VAPI Dashboard locally (frontend + backend)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting VAPI Dashboard (Local Development)${NC}"
echo "================================================"

# Check for required commands
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is required${NC}"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is required${NC}"
    exit 1
fi

# Check for requests module
if ! python3 -c "import requests" 2>/dev/null; then
    echo -e "${YELLOW}Installing Python requests module...${NC}"
    pip3 install requests
fi

# Kill any existing processes on our ports
echo -e "${YELLOW}Cleaning up any existing processes...${NC}"
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Start backend server
echo -e "${GREEN}Starting backend server on http://localhost:8080${NC}"
cd "$SCRIPT_DIR/backend"
python3 local-server.py &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Backend failed to start${NC}"
    exit 1
fi

# Start frontend server
echo -e "${GREEN}Starting frontend server on http://localhost:5173${NC}"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Trap to clean up on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}VAPI Dashboard is running!${NC}"
echo ""
echo -e "  Frontend: ${YELLOW}http://localhost:5173${NC}"
echo -e "  Backend:  ${YELLOW}http://localhost:8080${NC}"
echo ""
echo -e "  Login:    ${YELLOW}admin / admin123${NC}"
echo ""
echo -e "${GREEN}Press Ctrl+C to stop${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Wait for both processes
wait
