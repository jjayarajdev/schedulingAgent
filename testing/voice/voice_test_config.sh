#!/bin/bash
# ProjectForce Voice Integration Test Configuration
# Source this file before running voice tests: source voice_test_config.sh

# AWS Configuration
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="772634497954"

# API Gateway Endpoint (ProjectsForce Production)
export API_ENDPOINT="https://fpheaag7c7.execute-api.us-east-1.amazonaws.com/dev/invoke-agent"

# Lambda Function Names
export LEX_FULFILLMENT_LAMBDA="pf-lex-fulfillment-dev"
export VOICE_BRIDGE_LAMBDA="pf-voice-bedrock-bridge-dev"
export CUSTOMER_LOOKUP_LAMBDA="pf-customer-lookup-dev"

# Authentication Credentials (same as chat testing)
# IMPORTANT: Update these with your actual credentials from ProjectForce
export PF_TOKEN="TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4PUl7KCfKcSa/5LTVI9GZGD2xjCQuIIGifYzjbeIG4F9hljoQfRSa4yHgXV4iKYuqyrGhSMR2SSZtZYnMIprKV5KJUUvD3WK07SR+Wr7XZ1/gyWGOVXUymLVo4pYa8fdhKI1FO1kYIZZx6M9/YrNuc7Y4VcLCu5Mx8Y4hx/O15KwoCEtQMRzBA0iFNc4KiKMxn5T6Qc8OCz1TbNMLB4BC0LLmFgalsvGeUB3WXytW7L12cCOqq17dXJhnjKaDMgB3o5cbi1ngUgnkl0YS84s/CTxgNv/2TsSLAhx/qSY3zFFzcmFwras9EN5HyaYpyyswEGEuHm30rBreOwTkUEikvSLRp5ZnJJzI/F4mfg2MrZtPvpIAY2P6b71R8XEN8HhdXqtIgT0Ttdwz8LB4C+UyJxWQmA7VFxDnG5UkDLlzJnmY8ORSqXmAbRIFclNbzaw4J685q/w9YbpMfQgNHbk4BmIDDreexc6ka8feHce20OE1tg21R46+XCxUjzDrvOE5st9JSTm7kCyLcIyXQydf4h+DMyD++ZQQljw9SNE6oMfGcipDzwMCvJZtoCz2Eky9bOXboP+P6ZeuAxQtVsJmFb080gcuwLr5XFwPo5w/+Jrwa1c/D9sFWS3RG1UF7GdEjsBHGS1vwHDUiLtpORKwOURNrQVeylNYJgCGjoAdOk="
export PF_CLIENT_ID="09PF05VD"
export PF_USER_ID=1646085

# Test Phone Number (AWS Connect assigned number)
export VOICE_PHONE_NUMBER="+14702832382"
export TEST_PHONE_NUMBER="+18005551234"
export TEST_CUSTOMER_ID="CUST0001"

# Optional: Color output
export GREEN='\033[0;32m'
export BLUE='\033[0;34m'
export YELLOW='\033[1;33m'
export RED='\033[0;31m'
export NC='\033[0m' # No Color

echo -e "${GREEN}✅ Voice test configuration loaded:${NC}"
echo "   AWS_REGION: $AWS_REGION"
echo "   LEX_FULFILLMENT_LAMBDA: $LEX_FULFILLMENT_LAMBDA"
echo "   VOICE_BRIDGE_LAMBDA: $VOICE_BRIDGE_LAMBDA"
echo "   CUSTOMER_LOOKUP_LAMBDA: $CUSTOMER_LOOKUP_LAMBDA"
echo "   PF_CLIENT_ID: $PF_CLIENT_ID"
echo "   PF_USER_ID: $PF_USER_ID"
echo "   PF_TOKEN: ${PF_TOKEN:0:20}..."
echo ""
echo "You can now run voice test suites from testing/voice/"
