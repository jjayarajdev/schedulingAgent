#!/bin/bash

##############################################################################
# AWS Resource Inventory Script
# Generates a comprehensive inventory of all AWS resources in the account
##############################################################################

set -e

PROFILE="${1:-pf-aws}"
REGION="${2:-us-east-1}"
OUTPUT_FILE="aws_resource_inventory_$(date +%Y%m%d_%H%M%S).txt"

echo "================================================================================"
echo "AWS Resource Inventory Generator"
echo "================================================================================"
echo "Profile: $PROFILE"
echo "Region: $REGION"
echo "Output: $OUTPUT_FILE"
echo "================================================================================"
echo ""

# Start the output file
cat > "$OUTPUT_FILE" <<EOF
================================================================================
AWS RESOURCE INVENTORY
================================================================================
Generated: $(date)
AWS Profile: $PROFILE
Region: $REGION
================================================================================

EOF

echo "Gathering account information..."

# Account Information
cat >> "$OUTPUT_FILE" <<EOF
================================================================================
1. ACCOUNT INFORMATION
================================================================================

EOF

AWS_PROFILE=$PROFILE aws sts get-caller-identity --region $REGION >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF

Account Contact Information:
EOF
AWS_PROFILE=$PROFILE aws account get-contact-information --region $REGION >> "$OUTPUT_FILE" 2>&1 || echo "  (Unable to retrieve contact info)" >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
2. IAM ROLES AND POLICIES
================================================================================

EOF

echo "Gathering IAM roles..."

# List all roles
cat >> "$OUTPUT_FILE" <<EOF
All IAM Roles:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws iam list-roles --query 'Roles[].RoleName' --output table >> "$OUTPUT_FILE" 2>&1

# Get detailed info for key roles
cat >> "$OUTPUT_FILE" <<EOF

Detailed Role Information:
--------------------------------------------------------------------------------

EOF

# Lambda Orchestrator Role
echo "  - pf-orchestrator-role-dev"
cat >> "$OUTPUT_FILE" <<EOF
--- Role: pf-orchestrator-role-dev ---

Trust Policy:
EOF
AWS_PROFILE=$PROFILE aws iam get-role --role-name pf-orchestrator-role-dev --query 'Role.AssumeRolePolicyDocument' >> "$OUTPUT_FILE" 2>&1 || echo "  Role not found" >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" <<EOF

Inline Policies:
EOF
AWS_PROFILE=$PROFILE aws iam list-role-policies --role-name pf-orchestrator-role-dev >> "$OUTPUT_FILE" 2>&1 || echo "  Role not found" >> "$OUTPUT_FILE"

for policy in $(AWS_PROFILE=$PROFILE aws iam list-role-policies --role-name pf-orchestrator-role-dev --query 'PolicyNames[]' --output text 2>/dev/null); do
  cat >> "$OUTPUT_FILE" <<EOF

  Policy: $policy
EOF
  AWS_PROFILE=$PROFILE aws iam get-role-policy --role-name pf-orchestrator-role-dev --policy-name "$policy" --query 'PolicyDocument' >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF

Attached Managed Policies:
EOF
AWS_PROFILE=$PROFILE aws iam list-attached-role-policies --role-name pf-orchestrator-role-dev >> "$OUTPUT_FILE" 2>&1 || echo "  Role not found" >> "$OUTPUT_FILE"

# Bedrock Agent Execution Roles
for role in "AmazonBedrockExecutionRoleForAgents_Supervisor" \
            "AmazonBedrockExecutionRoleForAgents_pf-chitchat" \
            "AmazonBedrockExecutionRoleForAgents_SchedulingAgent" \
            "AmazonBedrockExecutionRoleForAgents_pf-information"; do

  echo "  - $role"
  cat >> "$OUTPUT_FILE" <<EOF

--- Role: $role ---

Trust Policy:
EOF
  AWS_PROFILE=$PROFILE aws iam get-role --role-name "$role" --query 'Role.AssumeRolePolicyDocument' >> "$OUTPUT_FILE" 2>&1 || echo "  Role not found" >> "$OUTPUT_FILE"

  cat >> "$OUTPUT_FILE" <<EOF

Inline Policies:
EOF
  AWS_PROFILE=$PROFILE aws iam list-role-policies --role-name "$role" >> "$OUTPUT_FILE" 2>&1 || echo "  Role not found" >> "$OUTPUT_FILE"

  for policy in $(AWS_PROFILE=$PROFILE aws iam list-role-policies --role-name "$role" --query 'PolicyNames[]' --output text 2>/dev/null); do
    cat >> "$OUTPUT_FILE" <<EOF

  Policy: $policy
EOF
    AWS_PROFILE=$PROFILE aws iam get-role-policy --role-name "$role" --policy-name "$policy" --query 'PolicyDocument' >> "$OUTPUT_FILE" 2>&1
  done

  cat >> "$OUTPUT_FILE" <<EOF

Attached Managed Policies:
EOF
  AWS_PROFILE=$PROFILE aws iam list-attached-role-policies --role-name "$role" >> "$OUTPUT_FILE" 2>&1 || echo "  Role not found" >> "$OUTPUT_FILE"
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
3. AWS BEDROCK AGENTS
================================================================================

EOF

echo "Gathering Bedrock agents..."

cat >> "$OUTPUT_FILE" <<EOF
All Bedrock Agents:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws bedrock-agent list-agents --region $REGION >> "$OUTPUT_FILE" 2>&1

# Get detailed info for each agent
AGENT_IDS=$(AWS_PROFILE=$PROFILE aws bedrock-agent list-agents --region $REGION --query 'agentSummaries[].agentId' --output text 2>/dev/null)

for agent_id in $AGENT_IDS; do
  echo "  - Agent: $agent_id"
  cat >> "$OUTPUT_FILE" <<EOF

--- Agent Details: $agent_id ---
EOF
  AWS_PROFILE=$PROFILE aws bedrock-agent get-agent --agent-id "$agent_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Agent Aliases:
EOF
  AWS_PROFILE=$PROFILE aws bedrock-agent list-agent-aliases --agent-id "$agent_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Agent Action Groups:
EOF
  AWS_PROFILE=$PROFILE aws bedrock-agent list-agent-action-groups --agent-id "$agent_id" --agent-version DRAFT --region $REGION >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
4. LAMBDA FUNCTIONS
================================================================================

EOF

echo "Gathering Lambda functions..."

cat >> "$OUTPUT_FILE" <<EOF
All Lambda Functions:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws lambda list-functions --region $REGION --query 'Functions[].[FunctionName, Runtime, Handler, MemorySize, Timeout]' --output table >> "$OUTPUT_FILE" 2>&1

# Get detailed info for key Lambda functions
LAMBDA_FUNCTIONS=$(AWS_PROFILE=$PROFILE aws lambda list-functions --region $REGION --query 'Functions[?starts_with(FunctionName, `pf-`)].FunctionName' --output text 2>/dev/null)

for func in $LAMBDA_FUNCTIONS; do
  echo "  - Lambda: $func"
  cat >> "$OUTPUT_FILE" <<EOF

--- Function: $func ---

Configuration:
EOF
  AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name "$func" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Environment Variables:
EOF
  AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name "$func" --region $REGION --query 'Environment.Variables' >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

VPC Configuration:
EOF
  AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name "$func" --region $REGION --query 'VpcConfig' >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Tags:
EOF
  AWS_PROFILE=$PROFILE aws lambda list-tags --resource "arn:aws:lambda:$REGION:$(AWS_PROFILE=$PROFILE aws sts get-caller-identity --query Account --output text):function:$func" >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
5. API GATEWAY
================================================================================

EOF

echo "Gathering API Gateway resources..."

cat >> "$OUTPUT_FILE" <<EOF
REST APIs:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws apigateway get-rest-apis --region $REGION >> "$OUTPUT_FILE" 2>&1

# Get detailed info for each REST API
API_IDS=$(AWS_PROFILE=$PROFILE aws apigateway get-rest-apis --region $REGION --query 'items[].id' --output text 2>/dev/null)

for api_id in $API_IDS; do
  echo "  - API: $api_id"
  cat >> "$OUTPUT_FILE" <<EOF

--- API: $api_id ---

Resources:
EOF
  AWS_PROFILE=$PROFILE aws apigateway get-resources --rest-api-id "$api_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Deployments:
EOF
  AWS_PROFILE=$PROFILE aws apigateway get-deployments --rest-api-id "$api_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Stages:
EOF
  AWS_PROFILE=$PROFILE aws apigateway get-stages --rest-api-id "$api_id" --region $REGION >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
6. AWS CONNECT
================================================================================

EOF

echo "Gathering AWS Connect resources..."

cat >> "$OUTPUT_FILE" <<EOF
Connect Instances:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws connect list-instances --region $REGION >> "$OUTPUT_FILE" 2>&1

# Get detailed info for each instance
INSTANCE_IDS=$(AWS_PROFILE=$PROFILE aws connect list-instances --region $REGION --query 'InstanceSummaryList[].Id' --output text 2>/dev/null)

for instance_id in $INSTANCE_IDS; do
  echo "  - Connect Instance: $instance_id"
  cat >> "$OUTPUT_FILE" <<EOF

--- Instance: $instance_id ---

Phone Numbers:
EOF
  AWS_PROFILE=$PROFILE aws connect list-phone-numbers-v2 --target-arn "arn:aws:connect:$REGION:$(AWS_PROFILE=$PROFILE aws sts get-caller-identity --query Account --output text):instance/$instance_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Contact Flows:
EOF
  AWS_PROFILE=$PROFILE aws connect list-contact-flows --instance-id "$instance_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Hours of Operation:
EOF
  AWS_PROFILE=$PROFILE aws connect list-hours-of-operations --instance-id "$instance_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Queues:
EOF
  AWS_PROFILE=$PROFILE aws connect list-queues --instance-id "$instance_id" --region $REGION >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
7. LEX BOTS
================================================================================

EOF

echo "Gathering Lex bots..."

cat >> "$OUTPUT_FILE" <<EOF
Lex Bots:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws lexv2-models list-bots --region $REGION >> "$OUTPUT_FILE" 2>&1

# Get detailed info for each bot
BOT_IDS=$(AWS_PROFILE=$PROFILE aws lexv2-models list-bots --region $REGION --query 'botSummaries[].botId' --output text 2>/dev/null)

for bot_id in $BOT_IDS; do
  echo "  - Lex Bot: $bot_id"
  cat >> "$OUTPUT_FILE" <<EOF

--- Bot: $bot_id ---

Bot Details:
EOF
  AWS_PROFILE=$PROFILE aws lexv2-models describe-bot --bot-id "$bot_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Bot Locales:
EOF
  AWS_PROFILE=$PROFILE aws lexv2-models list-bot-locales --bot-id "$bot_id" --bot-version DRAFT --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Bot Aliases:
EOF
  AWS_PROFILE=$PROFILE aws lexv2-models list-bot-aliases --bot-id "$bot_id" --region $REGION >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
8. DYNAMODB TABLES
================================================================================

EOF

echo "Gathering DynamoDB tables..."

cat >> "$OUTPUT_FILE" <<EOF
DynamoDB Tables:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws dynamodb list-tables --region $REGION >> "$OUTPUT_FILE" 2>&1

# Get detailed info for each table
TABLE_NAMES=$(AWS_PROFILE=$PROFILE aws dynamodb list-tables --region $REGION --query 'TableNames[]' --output text 2>/dev/null)

for table in $TABLE_NAMES; do
  echo "  - DynamoDB Table: $table"
  cat >> "$OUTPUT_FILE" <<EOF

--- Table: $table ---

Table Description:
EOF
  AWS_PROFILE=$PROFILE aws dynamodb describe-table --table-name "$table" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Table Tags:
EOF
  TABLE_ARN=$(AWS_PROFILE=$PROFILE aws dynamodb describe-table --table-name "$table" --region $REGION --query 'Table.TableArn' --output text 2>/dev/null)
  AWS_PROFILE=$PROFILE aws dynamodb list-tags-of-resource --resource-arn "$TABLE_ARN" --region $REGION >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
9. ELASTICACHE (REDIS)
================================================================================

EOF

echo "Gathering ElastiCache resources..."

cat >> "$OUTPUT_FILE" <<EOF
ElastiCache Serverless Caches:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws elasticache describe-serverless-caches --region $REGION >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF

ElastiCache Replication Groups:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws elasticache describe-replication-groups --region $REGION >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF

ElastiCache Cache Clusters:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws elasticache describe-cache-clusters --region $REGION >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
10. SECRETS MANAGER
================================================================================

EOF

echo "Gathering Secrets Manager secrets..."

cat >> "$OUTPUT_FILE" <<EOF
Secrets:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws secretsmanager list-secrets --region $REGION >> "$OUTPUT_FILE" 2>&1

# Get detailed info for each secret (without values)
SECRET_NAMES=$(AWS_PROFILE=$PROFILE aws secretsmanager list-secrets --region $REGION --query 'SecretList[].Name' --output text 2>/dev/null)

for secret in $SECRET_NAMES; do
  echo "  - Secret: $secret"
  cat >> "$OUTPUT_FILE" <<EOF

--- Secret: $secret ---

Metadata:
EOF
  AWS_PROFILE=$PROFILE aws secretsmanager describe-secret --secret-id "$secret" --region $REGION >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
11. VPC AND NETWORKING
================================================================================

EOF

echo "Gathering VPC resources..."

cat >> "$OUTPUT_FILE" <<EOF
VPCs:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws ec2 describe-vpcs --region $REGION >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF

Subnets:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws ec2 describe-subnets --region $REGION >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF

Security Groups:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws ec2 describe-security-groups --region $REGION >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF

VPC Endpoints:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws ec2 describe-vpc-endpoints --region $REGION >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
12. BEDROCK MODEL ACCESS
================================================================================

EOF

echo "Gathering Bedrock model access..."

cat >> "$OUTPUT_FILE" <<EOF
Foundation Models with Access:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws bedrock list-foundation-models --region $REGION --query 'modelSummaries[?modelLifecycle.status==`ACTIVE`].[modelId, modelName, providerName]' --output table >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF

Inference Profiles:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws bedrock list-inference-profiles --region $REGION >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
END OF INVENTORY
================================================================================
Generated: $(date)
================================================================================
EOF

echo ""
echo "================================================================================"
echo "✅ Inventory Complete!"
echo "================================================================================"
echo "Output file: $OUTPUT_FILE"
echo ""
echo "Summary:"
wc -l "$OUTPUT_FILE"
du -h "$OUTPUT_FILE"
echo "================================================================================"
