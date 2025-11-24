#!/bin/bash
# ProjectForce Bedrock Agent Test Configuration
# Source this file before running tests: source test_config.sh

# API Gateway Endpoint (pf-orchestrator-api-dev)
#export API_ENDPOINT="https://fpheaag7c7.execute-api.us-east-1.amazonaws.com/dev/invoke-agent"
export API_ENDPOINT="https://r38h2sy06l.execute-api.us-east-1.amazonaws.com/dev/invoke-agent"

# Authentication Credentials
# IMPORTANT: Update these with your actual credentials
export PF_TOKEN="TaDWx6r5O0WE2tb5/Lb77XuI29UR7j2NlMHbUdXd+YrYPR7ZdTrczgYigcaRHxvF4PUl7KCfKcSa/5LTVI9GZGD2xjCQuIIGifYzjbeIG4F9hljoQfRSa4yHgXV4iKYuqyrGhSMR2SSZtZYnMIprKV7PeLzJznVIv7SR82P7CkClzbV8eg8vHl3V6yZnKsclkIMM0H0UevfHj/hqKwxuLElM6oSr6YDueYPPFKRX8CYhXCQvhr3C3zvXYF29fC37sQ0YrLtGoAmDIy9Ep1lsnOxrwA67+nUT4XY7RRF/7gGQ7CvQkAReOMSzYrf8dsN1mZZ7k4aMDYHcCf8BVsEEnrC0RJQfB9HBc8h92fKL9VoD1i+yzOxOmZplxYkl4eoo/G1ls7CcuHiRkVC67efaFupXySzhFtOYi0/tmkgSDB1dtpegpzYzEKYbQd/K6+7fwBBAzmD72/aMuOg/mbo5XObEfnv9mNJzZQ6Tud3M5wLbwlc7iDM6k1ML669PDOwDInLNBY473ndj43ZCJmC8uoT7/d1WzbQ7Z8lJrYSv3mv2Bnb9heTec/DokO8uNwymiKc14c6RAuRfb3XUoNZilfhBogYTshiQ8U98009VTFZgmPozt6+387QEImkm4jGNI+hq5lTD74Vk6joyKYpXOTkXqPPXBqLcK7A5A4MKDPX61iteGeHa28lupucDnx85epUR2p0mODznPs+uISLCT6t93TvoOxx6XjbQ8sy7vsI="
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
