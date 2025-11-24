#!/bin/bash
# ProjectForce Bedrock Agent Test Configuration
# Source this file before running tests: source test_config.sh

# API Gateway Endpoint (pf-orchestrator-api-dev)
#export API_ENDPOINT="https://fpheaag7c7.execute-api.us-east-1.amazonaws.com/dev/invoke-agent"
export API_ENDPOINT="https://r38h2sy06l.execute-api.us-east-1.amazonaws.com/dev/invoke-agent"

# Authentication Credentials
# IMPORTANT: Update these with your actual credentials
export PF_TOKEN="TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4PUl7KCfKcSa/5LTVI9GZGD2xjCQuIIGifYzjbeIG4F9hljoQfRSa4yHgXV4iKYuqyrGhSMR2SSZtZYnMIprKV5KeLzJznUoYrSR/3v7C6rMzUEPeiijmTA6d9p98iOLmU0m4XudO1rLCFkuKQw1PZVIolgwUO/CCoNNBcBjsYVcpDZVO70ew7ISYRTTa2JA8Q2WzBpMBYDoP0q4YlVDTC5H63tTIeWY4BXGbQd/vj6FhL8vtzm1ltwYRuj5srU09uPxW6aqhtDODS2Y05Rf7GxmWjKhAjHACyR4jYGLdGiA+UfivzsFUuskmnM+q39WSLahe1V9t5cLFnfSAkbS1vDJLBeAhHrUWI9m9BrOu04TisB1DcG783yuIRPS5LcM+8280s9GijarZOfVgbl4TYGWPm9+nDAMYR2/fIcWVWTm3VV98iCvmrLvW+JhxqiE7FN9wcRO3TstXOJIpWJh1Qv75H5lUEfmWhg0q9wBkJNurXewd9KUJ/Goepfp5HeOJiLJSydBNrQGrtSDgYtLHYMBEflnuaXFW7XkcLpaIA32Hmaz8VWDerJQy5CYOOmcrq8GtQu3VrQW7VvJSwLV4LSUNDIHp5hXJoDH4byO0H4deM11so1s2vCwWnW0vYl+khHXnBfhva9lQuFeeMmcb+h+lPnPP7gfk4rqLfMhoWo="
export PF_CLIENT_ID="09PF05VD"
export PF_USER_ID=1646085

# Optional: Override for different environments
# export API_ENDPOINT="https://your-dev-endpoint.com/dev/invoke-agent"
# export PF_TOKEN="your-dev-token"

echo "✅ Test configuration loaded:"
echo "   API_ENDPOINT: $API_ENDPOINT"
echo "   PF_CLIENT_ID: $PF_CLIENT_ID"
echo "   PF_USER_ID: $PF_USER_ID"
echo "   PF_TOKEN: ${PF_TOKEN:0:20}..."
echo ""
echo "You can now run tests from TEST_CASES.md"
