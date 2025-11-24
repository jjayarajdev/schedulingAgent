#!/bin/bash
# Gather diagnostic information for AWS Support ticket

OUTPUT_DIR="/tmp/bedrock_diagnostics_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "Gathering diagnostic information..."
echo "Output directory: $OUTPUT_DIR"
echo ""

# 1. Test API access
echo "[1/8] Running API access tests..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BEDROCK_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
python3 "$BEDROCK_DIR/tests/test_api_access.py" > "$OUTPUT_DIR/1_api_test_results.txt" 2>&1

# 2. Get supervisor agent configuration
echo "[2/8] Getting supervisor agent config..."
aws bedrock-agent get-agent \
  --agent-id 5VTIWONUMO \
  --region us-east-1 \
  --output json > "$OUTPUT_DIR/2_supervisor_agent_config.json" 2>&1

# 3. Get supervisor agent version details
echo "[3/8] Getting supervisor version 6 details..."
aws bedrock-agent get-agent-version \
  --agent-id 5VTIWONUMO \
  --agent-version 6 \
  --region us-east-1 \
  --output json > "$OUTPUT_DIR/3_supervisor_version6_config.json" 2>&1

# 4. Get supervisor IAM policy
echo "[4/8] Getting supervisor IAM role policy..."
aws iam get-role-policy \
  --role-name scheduling-agent-supervisor-agent-role-dev \
  --policy-name scheduling-agent-supervisor-agent-policy \
  --output json > "$OUTPUT_DIR/4_supervisor_iam_policy.json" 2>&1

# 5. Get collaborator agents summary
echo "[5/8] Getting collaborator agents info..."
cat > "$OUTPUT_DIR/5_collaborator_agents.txt" << 'EOF'
Collaborator Agents:

1. Chitchat Agent
   - Agent ID: BIUW1ARHGL
   - Latest Alias: TSTALIASID (points to DRAFT)
   - V4 Alias: THIPMPJCPI (points to version 5)
   - Foundation Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0

2. Scheduling Agent
   - Agent ID: IX24FSMTQH
   - Latest Alias: TSTALIASID (points to DRAFT)
   - V4 Alias: TYJRF3CJ7F (points to version 4)
   - Foundation Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0

3. Information Agent
   - Agent ID: C9ANXRIO8Y
   - Latest Alias: TSTALIASID (points to DRAFT)
   - V4 Alias: YVNFXEKPWO (points to version 4)
   - Foundation Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0

4. Notes Agent
   - Agent ID: G5BVBYEPUM
   - Latest Alias: TSTALIASID (points to DRAFT)
   - V4 Alias: F9QQNLZUW8 (points to version 4)
   - Foundation Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0
EOF

# 6. Test direct model invocation
echo "[6/8] Testing direct model invocation..."
cat > /tmp/test_model_invoke.py << 'PYEOF'
import boto3
import json

client = boto3.client('bedrock-runtime', region_name='us-east-1')

try:
    response = client.invoke_model(
        modelId='us.anthropic.claude-sonnet-4-5-20250929-v1:0',
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 30,
            'messages': [{'role': 'user', 'content': 'Say hello'}]
        })
    )
    result = json.loads(response['body'].read())
    print("✅ SUCCESS - Direct model invocation works")
    print(f"Response: {result['content'][0]['text']}")
except Exception as e:
    print(f"❌ FAILED - Direct model invocation failed: {e}")
PYEOF

python3 /tmp/test_model_invoke.py > "$OUTPUT_DIR/6_direct_model_test.txt" 2>&1

# 7. Get available inference profiles
echo "[7/8] Listing available inference profiles..."
aws bedrock list-inference-profiles \
  --region us-east-1 \
  --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `sonnet-4-5`)]' \
  --output json > "$OUTPUT_DIR/7_inference_profiles.json" 2>&1

# 8. Get AWS account info
echo "[8/8] Getting account information..."
aws sts get-caller-identity > "$OUTPUT_DIR/8_account_info.json" 2>&1

# Create summary
cat > "$OUTPUT_DIR/0_SUMMARY.txt" << EOF
BEDROCK AGENT API ACCESS ISSUE - DIAGNOSTIC SUMMARY
====================================================

Date: $(date)
Account: $(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null || echo "Unknown")
Region: us-east-1
User: $(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null || echo "Unknown")

ISSUE:
Agent API invocation fails with 403 Access Denied despite:
- Cross-region inference access enabled for Claude Sonnet 4.5
- Correct IAM permissions configured
- Console testing works fine
- Direct model invocation works fine

MODEL:
- Name: Claude Sonnet 4.5
- ID: anthropic.claude-sonnet-4-5-20250929-v1:0
- Inference Profile: us.anthropic.claude-sonnet-4-5-20250929-v1:0
- Access Status: Cross-region inference enabled, On-demand status unknown

AGENTS:
- Supervisor: 5VTIWONUMO (latest alias: HH2U7EZXMW -> version 6)
- 4 Collaborator agents (see file 5_collaborator_agents.txt)

FILES INCLUDED:
1. api_test_results.txt - Test output showing 403 errors
2. supervisor_agent_config.json - Agent configuration
3. supervisor_version6_config.json - Version 6 details
4. supervisor_iam_policy.json - IAM role policy
5. collaborator_agents.txt - Collaborator agent details
6. direct_model_test.txt - Direct model invocation test
7. inference_profiles.json - Available inference profiles
8. account_info.json - AWS account information

WHAT WORKS:
✅ Direct model invocation (bedrock-runtime API)
✅ Console agent testing (AWS Console UI)
✅ IAM permissions configured correctly

WHAT FAILS:
❌ Agent invocation via bedrock-agent-runtime API
❌ Error: accessDeniedException (403)
❌ All aliases and versions affected

REQUEST:
Enable on-demand/base model API access for Claude Sonnet 4.5
to allow bedrock-agent-runtime API invocation.

EOF

echo ""
echo "✅ Diagnostics gathered successfully!"
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "Files created:"
ls -lh "$OUTPUT_DIR"
echo ""
echo "To attach to support ticket:"
echo "1. Zip the directory:"
echo "   cd /tmp && zip -r bedrock_diagnostics.zip $(basename $OUTPUT_DIR)"
echo ""
echo "2. Or attach individual files from: $OUTPUT_DIR"
echo ""
echo "Most important files to attach:"
echo "  - 0_SUMMARY.txt (overview)"
echo "  - 1_api_test_results.txt (error output)"
echo "  - 4_supervisor_iam_policy.json (IAM permissions)"
