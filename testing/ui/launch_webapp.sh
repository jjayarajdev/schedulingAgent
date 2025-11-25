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

echo "════════════════════════════════════════════════════════════════════════════"
echo "🚀 ProjectForce Web Application Launcher"
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

# Get fresh token from ProjectForce (after proxy starts)
# This will be called later after pf_proxy.py is running

# Check if flask and flask-cors are installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask not installed. Installing..."
    pip3 install flask flask-cors requests
fi

if ! python3 -c "import flask_cors" 2>/dev/null; then
    echo "⚠️  Flask-CORS not installed. Installing..."
    pip3 install flask-cors
fi

# Check if port 5003 is already in use
if lsof -Pi :5003 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 5003 is already in use. Killing existing process..."
    kill $(lsof -t -i:5003) 2>/dev/null || true
    sleep 1
fi

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8000 is already in use. Killing existing process..."
    kill $(lsof -t -i:8000) 2>/dev/null || true
    sleep 1
fi

# Start the CORS proxy server
echo "🔌 Starting CORS proxy server on port 5003..."
python3 pf_proxy.py > /tmp/pf_proxy.log 2>&1 &
PROXY_PID=$!

# Wait for proxy to start
sleep 3

# Sync token from source secret to target secret
echo "🔐 Syncing ProjectForce token to AWS Secrets Manager..."
python3 << 'EOF'
import json
import boto3
import time

try:
    secrets_client = boto3.client('secretsmanager', region_name='us-east-1')

    # Get token from source secret
    source_response = secrets_client.get_secret_value(SecretId='projectforce/api/credentials')
    source_secret = json.loads(source_response['SecretString'])

    access_token = source_secret.get('bearer_token', '')
    client_id = source_secret.get('client_id', '09PF05VD')
    customer_id = source_secret.get('user_id', '1646085')
    api_url = source_secret.get('api_base_url', 'https://api-cx-portal.dev.projectsforce.com')

    if access_token and len(access_token) > 100:
        print(f"  ✅ Found token in source secret (length: {len(access_token)})")

        # Update target secret
        secret_value = {
            "pf_token": access_token,
            "client_id": client_id,
            "customer_id": customer_id,
            "api_url": api_url,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "updated_by": "launch_webapp.sh",
            "notes": "Synced from projectforce/api/credentials on startup"
        }

        secrets_client.put_secret_value(
            SecretId='scheduling-agent/pf360/api-credentials',
            SecretString=json.dumps(secret_value)
        )

        print(f"  ✅ Token synced to scheduling-agent/pf360/api-credentials")
    else:
        print(f"  ⚠️  No valid token found (length: {len(access_token)})")
        print(f"  💡 Login via UI first, then restart to sync token")

except Exception as e:
    print(f"  ⚠️  Token sync failed: {e}")
EOF

# Start the HTTP server on port 8000
echo "🌐 Starting HTTP server on port 8000..."
python3 -m http.server 8000 > /tmp/http_server.log 2>&1 &
HTTP_PID=$!

# Wait for HTTP server to start
sleep 2

# Open the browser
echo "🌐 Opening UI in browser..."
open "http://localhost:8000/index.local.html"

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
echo "  • Proxy:      /tmp/pf_proxy.log"
echo "  • HTTP:       /tmp/http_server.log"
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
