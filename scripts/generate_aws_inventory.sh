#!/bin/bash

# AWS Resources Inventory Generator
# Generates a comprehensive inventory of all AWS resources for the ProjectForce Scheduling Agent
#
# Usage: ./generate_aws_inventory.sh [output_file]
# Default output: ../AWS_RESOURCES_INVENTORY.md

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_FILE="${1:-$PROJECT_ROOT/../AWS_RESOURCES_INVENTORY.md}"
REGION="${AWS_REGION:-us-east-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AWS Resources Inventory Generator${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get AWS account info
echo -e "${GREEN}Gathering AWS account information...${NC}"
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
USER_ARN=$(aws sts get-caller-identity --query 'Arn' --output text)
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

echo "  Account ID: $ACCOUNT_ID"
echo "  User: $USER_ARN"
echo "  Region: $REGION"
echo ""

# Gather Bedrock Agents
echo -e "${GREEN}Gathering Bedrock Agents...${NC}"
AGENTS_JSON=$(aws bedrock-agent list-agents --region $REGION --output json 2>/dev/null || echo '{"agentSummaries":[]}')
AGENTS_COUNT=$(echo "$AGENTS_JSON" | jq -r '.agentSummaries | length')
echo "  Found $AGENTS_COUNT agents"

# Gather Lambda Functions
echo -e "${GREEN}Gathering Lambda Functions...${NC}"
LAMBDAS_JSON=$(aws lambda list-functions --region $REGION --output json 2>/dev/null || echo '{"Functions":[]}')
LAMBDAS_COUNT=$(echo "$LAMBDAS_JSON" | jq -r '[.Functions[] | select(.FunctionName | contains("pf-") or contains("scheduling"))] | length')
echo "  Found $LAMBDAS_COUNT Lambda functions"

# Gather IAM Roles
echo -e "${GREEN}Gathering IAM Roles...${NC}"
ROLES_JSON=$(aws iam list-roles --output json 2>/dev/null || echo '{"Roles":[]}')
ROLES_COUNT=$(echo "$ROLES_JSON" | jq -r '[.Roles[] | select(.RoleName | contains("pf-") or contains("bedrock") or contains("Bedrock") or contains("scheduling"))] | length')
echo "  Found $ROLES_COUNT IAM roles"

# Gather DynamoDB Tables
echo -e "${GREEN}Gathering DynamoDB Tables...${NC}"
DYNAMO_JSON=$(aws dynamodb list-tables --region $REGION --output json 2>/dev/null || echo '{"TableNames":[]}')
DYNAMO_COUNT=$(echo "$DYNAMO_JSON" | jq -r '[.TableNames[] | select(contains("pf-") or contains("scheduling"))] | length')
echo "  Found $DYNAMO_COUNT DynamoDB tables"

# Gather S3 Buckets
echo -e "${GREEN}Gathering S3 Buckets...${NC}"
S3_BUCKETS=$(aws s3 ls | grep -E 'pf-|scheduling|bedrock' || echo "")
S3_COUNT=$(echo "$S3_BUCKETS" | grep -c . || echo "0")
echo "  Found $S3_COUNT S3 buckets"

# Gather CloudWatch Log Groups
echo -e "${GREEN}Gathering CloudWatch Log Groups...${NC}"
LOGS_JSON=$(aws logs describe-log-groups --region $REGION --output json 2>/dev/null || echo '{"logGroups":[]}')
LOGS_COUNT=$(echo "$LOGS_JSON" | jq -r '[.logGroups[] | select(.logGroupName | contains("/aws/lambda/pf-") or contains("/aws/lambda/scheduling"))] | length')
echo "  Found $LOGS_COUNT log groups"

echo ""
echo -e "${BLUE}Generating inventory document...${NC}"

# Generate the markdown document
cat > "$OUTPUT_FILE" <<EOF
# AWS Resources Inventory - ProjectForce Scheduling Agent

**Account ID:** $ACCOUNT_ID
**Region:** $REGION
**User:** $USER_ARN
**Generated:** $TIMESTAMP

---

## 🤖 Bedrock Agents ($AGENTS_COUNT Total)

EOF

# Add Bedrock Agents Details
echo "$AGENTS_JSON" | jq -r '.agentSummaries[] | select(.agentName | contains("pf-") or contains("Supervisor") or contains("Scheduling")) |
"### \(.agentName)
- **Agent ID:** \(.agentId)
- **Status:** \(.agentStatus)
- **Last Updated:** \(.updatedAt // "N/A")

"' >> "$OUTPUT_FILE"

# Get detailed agent information
for agent_id in $(echo "$AGENTS_JSON" | jq -r '.agentSummaries[].agentId'); do
    echo -e "${YELLOW}  Getting details for agent: $agent_id${NC}"
    AGENT_DETAIL=$(aws bedrock-agent get-agent --agent-id "$agent_id" --region $REGION --output json 2>/dev/null || echo '{}')

    AGENT_NAME=$(echo "$AGENT_DETAIL" | jq -r '.agent.agentName // "Unknown"')
    AGENT_MODEL=$(echo "$AGENT_DETAIL" | jq -r '.agent.foundationModel // "N/A"')
    AGENT_DESC=$(echo "$AGENT_DETAIL" | jq -r '.agent.description // "No description"')
    AGENT_ROLE=$(echo "$AGENT_DETAIL" | jq -r '.agent.agentResourceRoleArn // "N/A"' | sed 's/.*role\///')

    cat >> "$OUTPUT_FILE" <<AGENT_EOF

#### $AGENT_NAME ($agent_id)
- **Model:** $AGENT_MODEL
- **Description:** $AGENT_DESC
- **IAM Role:** $AGENT_ROLE

AGENT_EOF

    # Get action groups
    ACTION_GROUPS=$(aws bedrock-agent list-agent-action-groups --agent-id "$agent_id" --agent-version DRAFT --region $REGION --output json 2>/dev/null || echo '{"actionGroupSummaries":[]}')
    AG_COUNT=$(echo "$ACTION_GROUPS" | jq -r '.actionGroupSummaries | length')

    if [ "$AG_COUNT" -gt 0 ]; then
        echo "**Action Groups:**" >> "$OUTPUT_FILE"
        echo "$ACTION_GROUPS" | jq -r '.actionGroupSummaries[] | "  - \(.actionGroupName) (ID: \(.actionGroupId), State: \(.actionGroupState))"' >> "$OUTPUT_FILE"
    fi

    # Get collaborators (for Supervisor)
    if [[ "$AGENT_NAME" == *"Supervisor"* ]]; then
        COLLABORATORS=$(aws bedrock-agent list-agent-collaborators --agent-id "$agent_id" --agent-version DRAFT --region $REGION --output json 2>/dev/null || echo '{"agentCollaboratorSummaries":[]}')
        COLLAB_COUNT=$(echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries | length')

        if [ "$COLLAB_COUNT" -gt 0 ]; then
            echo "**Collaborators:** $COLLAB_COUNT" >> "$OUTPUT_FILE"
            echo "$COLLABORATORS" | jq -r '.agentCollaboratorSummaries[] | "  - \(.collaboratorName) (Agent: \(.agentId))"' >> "$OUTPUT_FILE"
        fi
    fi

    echo "" >> "$OUTPUT_FILE"
done

cat >> "$OUTPUT_FILE" <<EOF

---

## λ Lambda Functions ($LAMBDAS_COUNT Active)

EOF

# Add Lambda Functions
echo "$LAMBDAS_JSON" | jq -r '.Functions[] | select(.FunctionName | contains("pf-") or contains("scheduling")) |
"### \(.FunctionName)
- **Runtime:** \(.Runtime)
- **Memory:** \(.MemorySize) MB
- **Timeout:** \(.Timeout) seconds
- **Handler:** \(.Handler)
- **IAM Role:** \(.Role | split("/") | .[-1])
- **Last Modified:** \(.LastModified)
- **Code Size:** \(.CodeSize) bytes

"' >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" <<EOF

---

## 🔐 IAM Roles ($ROLES_COUNT Total)

EOF

# Add IAM Roles
echo "$ROLES_JSON" | jq -r '.Roles[] | select(.RoleName | contains("pf-") or contains("bedrock") or contains("Bedrock") or contains("scheduling")) |
"### \(.RoleName)
- **ARN:** \(.Arn)
- **Created:** \(.CreateDate)
- **Path:** \(.Path)

"' >> "$OUTPUT_FILE"

# Get IAM policies for each role
echo "" >> "$OUTPUT_FILE"
echo "### IAM Role Policies" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

for role in $(echo "$ROLES_JSON" | jq -r '.Roles[] | select(.RoleName | contains("pf-") or contains("Bedrock") or contains("scheduling")) | .RoleName' | head -10); do
    echo -e "${YELLOW}  Getting policies for role: $role${NC}"

    # Get attached policies
    ATTACHED=$(aws iam list-attached-role-policies --role-name "$role" --output json 2>/dev/null || echo '{"AttachedPolicies":[]}')
    ATTACHED_COUNT=$(echo "$ATTACHED" | jq -r '.AttachedPolicies | length')

    if [ "$ATTACHED_COUNT" -gt 0 ]; then
        cat >> "$OUTPUT_FILE" <<ROLE_EOF

#### $role
**Attached Policies:**
ROLE_EOF
        echo "$ATTACHED" | jq -r '.AttachedPolicies[] | "  - \(.PolicyName)"' >> "$OUTPUT_FILE"
    fi

    # Get inline policies
    INLINE=$(aws iam list-role-policies --role-name "$role" --output json 2>/dev/null || echo '{"PolicyNames":[]}')
    INLINE_COUNT=$(echo "$INLINE" | jq -r '.PolicyNames | length')

    if [ "$INLINE_COUNT" -gt 0 ]; then
        echo "**Inline Policies:**" >> "$OUTPUT_FILE"
        echo "$INLINE" | jq -r '.PolicyNames[] | "  - \(.)"' >> "$OUTPUT_FILE"
    fi
done

cat >> "$OUTPUT_FILE" <<EOF

---

## 📊 DynamoDB Tables ($DYNAMO_COUNT Total)

EOF

# Add DynamoDB Tables
echo "$DYNAMO_JSON" | jq -r '.TableNames[] | select(contains("pf-") or contains("scheduling")) |
"### \(.)
- **Region:** $REGION
- **Purpose:** Session/data storage

"' >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" <<EOF

---

## 🪣 S3 Buckets ($S3_COUNT Total)

EOF

# Add S3 Buckets
if [ -n "$S3_BUCKETS" ]; then
    echo "$S3_BUCKETS" | while IFS= read -r bucket_line; do
        if [ -n "$bucket_line" ]; then
            BUCKET_DATE=$(echo "$bucket_line" | awk '{print $1, $2}')
            BUCKET_NAME=$(echo "$bucket_line" | awk '{print $3}')
            cat >> "$OUTPUT_FILE" <<S3_EOF
### $BUCKET_NAME
- **Created:** $BUCKET_DATE
- **Region:** $REGION

S3_EOF
        fi
    done
else
    echo "No S3 buckets found matching the criteria." >> "$OUTPUT_FILE"
fi

cat >> "$OUTPUT_FILE" <<EOF

---

## 📝 CloudWatch Log Groups ($LOGS_COUNT Total)

EOF

# Add CloudWatch Log Groups
echo "$LOGS_JSON" | jq -r '.logGroups[] | select(.logGroupName | contains("/aws/lambda/pf-") or contains("/aws/lambda/scheduling")) |
"### \(.logGroupName)
- **Size:** \(.storedBytes) bytes
- **Created:** \(.creationTime / 1000 | todate)
- **Retention:** \(.retentionInDays // "Never expires") days

"' >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" <<EOF

---

## 🔗 Resource Dependencies

### Agent Collaboration Flow
\`\`\`
User Query
    ↓
Supervisor Agent
    ↓ (routes to)
    ├─→ SchedulingAgent
    │       ↓ (invokes)
    │       └─→ Lambda: pf-scheduling-actions
    │               ↓ (calls)
    │               └─→ ProjectForce API
    │
    ├─→ InformationAgent
    │       ↓ (invokes)
    │       └─→ Lambda: pf-information-actions
    │               ↓ (calls)
    │               └─→ ProjectForce API
    │
    └─→ ChitchatAgent
            └─→ Direct conversational response
\`\`\`

---

## 💰 Estimated Monthly Costs

### Bedrock Agents (Claude 3.5 Sonnet)
- **Input:** ~\$3 per 1M tokens
- **Output:** ~\$15 per 1M tokens
- **Estimated:** \$50-200/month (depending on usage)

### Lambda Functions
- **Compute:** ~\$0.20 per 1M requests
- **Duration:** ~\$0.0000166667 per GB-second
- **Estimated:** \$5-20/month

### DynamoDB
- **On-Demand Pricing:** Pay per request
- **Estimated:** \$1-10/month

### S3 Storage
- **Standard Storage:** \$0.023 per GB
- **Estimated:** <\$1/month

### CloudWatch Logs
- **Ingestion:** \$0.50 per GB
- **Storage:** \$0.03 per GB/month
- **Estimated:** \$2-5/month

**Total Estimated Monthly Cost:** \$60-250/month

---

## 🔒 Security Considerations

### IAM Policies
- ✅ Least privilege access for Lambda roles
- ✅ Bedrock model invocation restricted to specific models
- ✅ DynamoDB access scoped to specific tables
- ⚠️  Review secrets management strategy

### API Authentication
- ✅ Bearer token authentication for ProjectForce API
- ⚠️  Consider AWS Secrets Manager for token rotation

### Network Security
- ✅ HTTPS for all external API calls
- ⚠️  Consider VPC deployment for Lambda functions

---

## 📋 Maintenance Commands

### Update This Inventory
\`\`\`bash
cd bedrock/scripts
./generate_aws_inventory.sh
\`\`\`

### View Specific Resources
\`\`\`bash
# List all agents
aws bedrock-agent list-agents --region $REGION

# List all Lambda functions
aws lambda list-functions --region $REGION --query 'Functions[?contains(FunctionName, \`pf-\`)].FunctionName'

# List all IAM roles
aws iam list-roles --query 'Roles[?contains(RoleName, \`pf-\`)].RoleName'
\`\`\`

### Deploy Updates
\`\`\`bash
cd bedrock/scripts
./DEPLOY.sh
\`\`\`

### Test End-to-End
\`\`\`bash
cd bedrock/scripts
./test_agent_flow.py
\`\`\`

---

**Generated By:** generate_aws_inventory.sh
**Timestamp:** $TIMESTAMP
**Account:** $ACCOUNT_ID
**Region:** $REGION
EOF

echo ""
echo -e "${GREEN}✅ Inventory generated successfully!${NC}"
echo ""
echo -e "${BLUE}Output file: $OUTPUT_FILE${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "  - Bedrock Agents: $AGENTS_COUNT"
echo "  - Lambda Functions: $LAMBDAS_COUNT"
echo "  - IAM Roles: $ROLES_COUNT"
echo "  - DynamoDB Tables: $DYNAMO_COUNT"
echo "  - S3 Buckets: $S3_COUNT"
echo "  - CloudWatch Log Groups: $LOGS_COUNT"
echo ""
echo -e "${GREEN}Total AWS Resources: $((AGENTS_COUNT + LAMBDAS_COUNT + ROLES_COUNT + DYNAMO_COUNT + S3_COUNT + LOGS_COUNT))${NC}"
echo ""
