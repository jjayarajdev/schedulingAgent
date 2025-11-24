#!/bin/bash

##############################################################################
# Bedrock Multi-Agent Project Inventory Script
# Generates inventory of resources specific to this Bedrock project
##############################################################################

set -e

PROFILE="${1:-pf-aws}"
REGION="${2:-us-east-1}"
OUTPUT_FILE="bedrock_project_inventory_$(date +%Y%m%d_%H%M%S).txt"

echo "================================================================================"
echo "Bedrock Multi-Agent Project Inventory"
echo "================================================================================"
echo "Profile: $PROFILE"
echo "Region: $REGION"
echo "Output: $OUTPUT_FILE"
echo "================================================================================"
echo ""

# Start the output file
cat > "$OUTPUT_FILE" <<EOF
================================================================================
BEDROCK MULTI-AGENT PROJECT INVENTORY
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

ACCOUNT_ID=$(AWS_PROFILE=$PROFILE aws sts get-caller-identity --query Account --output text)

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
2. BEDROCK AGENTS (All 4 Agents)
================================================================================

EOF

echo "Gathering Bedrock agents..."

# Get all agents
AGENT_IDS=$(AWS_PROFILE=$PROFILE aws bedrock-agent list-agents --region $REGION --query 'agentSummaries[].agentId' --output text 2>/dev/null)

for agent_id in $AGENT_IDS; do
  echo "  - Agent: $agent_id"

  AGENT_NAME=$(AWS_PROFILE=$PROFILE aws bedrock-agent get-agent --agent-id "$agent_id" --region $REGION --query 'agent.agentName' --output text 2>/dev/null)

  cat >> "$OUTPUT_FILE" <<EOF

################################################################################
AGENT: $AGENT_NAME ($agent_id)
################################################################################

Agent Configuration:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws bedrock-agent get-agent --agent-id "$agent_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Agent Aliases:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws bedrock-agent list-agent-aliases --agent-id "$agent_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Agent Action Groups:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws bedrock-agent list-agent-action-groups --agent-id "$agent_id" --agent-version DRAFT --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Agent Collaborators (if Supervisor):
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws bedrock-agent list-agent-collaborators --agent-id "$agent_id" --agent-version DRAFT --region $REGION >> "$OUTPUT_FILE" 2>&1 || echo "  Not a supervisor agent or no collaborators" >> "$OUTPUT_FILE"
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
3. IAM ROLES (Bedrock Project Specific)
================================================================================

EOF

echo "Gathering IAM roles..."

# Lambda Orchestrator Role
echo "  - pf-orchestrator-role-dev"
cat >> "$OUTPUT_FILE" <<EOF
################################################################################
ROLE: pf-orchestrator-role-dev (Lambda Orchestrator)
################################################################################

Trust Policy:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws iam get-role --role-name pf-orchestrator-role-dev --query 'Role.AssumeRolePolicyDocument' >> "$OUTPUT_FILE" 2>&1 || echo "  Role not found" >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" <<EOF

Inline Policies:
--------------------------------------------------------------------------------
EOF
for policy in $(AWS_PROFILE=$PROFILE aws iam list-role-policies --role-name pf-orchestrator-role-dev --query 'PolicyNames[]' --output text 2>/dev/null); do
  cat >> "$OUTPUT_FILE" <<EOF

Policy: $policy
EOF
  AWS_PROFILE=$PROFILE aws iam get-role-policy --role-name pf-orchestrator-role-dev --policy-name "$policy" --query 'PolicyDocument' >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF

Attached Managed Policies:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws iam list-attached-role-policies --role-name pf-orchestrator-role-dev >> "$OUTPUT_FILE" 2>&1 || echo "  Role not found" >> "$OUTPUT_FILE"

# Bedrock Agent Execution Roles
for role in "AmazonBedrockExecutionRoleForAgents_Supervisor" \
            "AmazonBedrockExecutionRoleForAgents_pf-chitchat" \
            "AmazonBedrockExecutionRoleForAgents_SchedulingAgent" \
            "AmazonBedrockExecutionRoleForAgents_pf-information"; do

  echo "  - $role"
  cat >> "$OUTPUT_FILE" <<EOF

################################################################################
ROLE: $role (Bedrock Agent Execution)
################################################################################

Trust Policy:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws iam get-role --role-name "$role" --query 'Role.AssumeRolePolicyDocument' >> "$OUTPUT_FILE" 2>&1 || echo "  Role not found" >> "$OUTPUT_FILE"

  cat >> "$OUTPUT_FILE" <<EOF

Inline Policies:
--------------------------------------------------------------------------------
EOF
  for policy in $(AWS_PROFILE=$PROFILE aws iam list-role-policies --role-name "$role" --query 'PolicyNames[]' --output text 2>/dev/null); do
    cat >> "$OUTPUT_FILE" <<EOF

Policy: $policy
EOF
    AWS_PROFILE=$PROFILE aws iam get-role-policy --role-name "$role" --policy-name "$policy" --query 'PolicyDocument' >> "$OUTPUT_FILE" 2>&1
  done

  cat >> "$OUTPUT_FILE" <<EOF

Attached Managed Policies:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws iam list-attached-role-policies --role-name "$role" >> "$OUTPUT_FILE" 2>&1 || echo "  Role not found" >> "$OUTPUT_FILE"
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
4. LAMBDA FUNCTIONS (Bedrock Project)
================================================================================

EOF

echo "Gathering Lambda functions..."

# Orchestrator Lambda
echo "  - pf-orchestrator"
cat >> "$OUTPUT_FILE" <<EOF
################################################################################
LAMBDA: pf-orchestrator (Main Orchestrator)
################################################################################

Configuration:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name pf-orchestrator --region $REGION >> "$OUTPUT_FILE" 2>&1 || echo "  Function not found" >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" <<EOF

Environment Variables:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name pf-orchestrator --region $REGION --query 'Environment.Variables' >> "$OUTPUT_FILE" 2>&1 || echo "  Function not found" >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" <<EOF

VPC Configuration:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name pf-orchestrator --region $REGION --query 'VpcConfig' >> "$OUTPUT_FILE" 2>&1 || echo "  Function not found" >> "$OUTPUT_FILE"

# Action Group Lambdas
for func in "pf-scheduling-actions" "pf-information-actions"; do
  echo "  - $func"
  cat >> "$OUTPUT_FILE" <<EOF

################################################################################
LAMBDA: $func (Agent Action Group)
################################################################################

Configuration:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name "$func" --region $REGION >> "$OUTPUT_FILE" 2>&1 || echo "  Function not found" >> "$OUTPUT_FILE"

  cat >> "$OUTPUT_FILE" <<EOF

Environment Variables:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name "$func" --region $REGION --query 'Environment.Variables' >> "$OUTPUT_FILE" 2>&1 || echo "  Function not found" >> "$OUTPUT_FILE"

  cat >> "$OUTPUT_FILE" <<EOF

VPC Configuration:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name "$func" --region $REGION --query 'VpcConfig' >> "$OUTPUT_FILE" 2>&1 || echo "  Function not found" >> "$OUTPUT_FILE"
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
5. API GATEWAY (Bedrock Orchestrator)
================================================================================

EOF

echo "Gathering API Gateway..."

cat >> "$OUTPUT_FILE" <<EOF
All REST APIs:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws apigateway get-rest-apis --region $REGION --query 'items[?name==`pf-orchestrator-api`]' >> "$OUTPUT_FILE" 2>&1

API_ID=$(AWS_PROFILE=$PROFILE aws apigateway get-rest-apis --region $REGION --query 'items[?name==`pf-orchestrator-api`].id' --output text 2>/dev/null)

if [ -n "$API_ID" ]; then
  echo "  - API: $API_ID"
  cat >> "$OUTPUT_FILE" <<EOF

Resources:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws apigateway get-resources --rest-api-id "$API_ID" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Stages:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws apigateway get-stages --rest-api-id "$API_ID" --region $REGION >> "$OUTPUT_FILE" 2>&1
fi

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
6. SECRETS MANAGER (ProjectForce API Credentials)
================================================================================

EOF

echo "Gathering Secrets Manager..."

cat >> "$OUTPUT_FILE" <<EOF
Secret: projectforce/api/credentials
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws secretsmanager describe-secret --secret-id "projectforce/api/credentials" --region $REGION >> "$OUTPUT_FILE" 2>&1 || echo "  Secret not found" >> "$OUTPUT_FILE"

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
7. DYNAMODB TABLES (Session Storage)
================================================================================

EOF

echo "Gathering DynamoDB tables..."

cat >> "$OUTPUT_FILE" <<EOF
Tables (Session-related):
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws dynamodb list-tables --region $REGION --query 'TableNames[?contains(@, `session`) || contains(@, `Session`)]' >> "$OUTPUT_FILE" 2>&1

SESSION_TABLES=$(AWS_PROFILE=$PROFILE aws dynamodb list-tables --region $REGION --query 'TableNames[?contains(@, `session`) || contains(@, `Session`)]' --output text 2>/dev/null)

for table in $SESSION_TABLES; do
  echo "  - Table: $table"
  cat >> "$OUTPUT_FILE" <<EOF

Table: $table
EOF
  AWS_PROFILE=$PROFILE aws dynamodb describe-table --table-name "$table" --region $REGION >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
8. ELASTICACHE (Redis - Session Storage)
================================================================================

EOF

echo "Gathering ElastiCache..."

cat >> "$OUTPUT_FILE" <<EOF
ElastiCache Serverless Caches:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws elasticache describe-serverless-caches --region $REGION --query 'ServerlessCaches[?contains(ServerlessCacheName, `pf`) || contains(ServerlessCacheName, `session`)]' >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
9. VPC AND NETWORKING (Project VPC)
================================================================================

EOF

echo "Gathering VPC resources..."

# Get VPC used by Lambda
VPC_ID=$(AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name pf-orchestrator --region $REGION --query 'VpcConfig.VpcId' --output text 2>/dev/null)

if [ -n "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
  cat >> "$OUTPUT_FILE" <<EOF
VPC: $VPC_ID
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Subnets in VPC:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Security Groups for Lambda:
--------------------------------------------------------------------------------
EOF
  SG_IDS=$(AWS_PROFILE=$PROFILE aws lambda get-function-configuration --function-name pf-orchestrator --region $REGION --query 'VpcConfig.SecurityGroupIds' --output text 2>/dev/null)
  for sg in $SG_IDS; do
    AWS_PROFILE=$PROFILE aws ec2 describe-security-groups --group-ids "$sg" --region $REGION >> "$OUTPUT_FILE" 2>&1
  done

  cat >> "$OUTPUT_FILE" <<EOF

VPC Endpoints in VPC:
--------------------------------------------------------------------------------
EOF
  AWS_PROFILE=$PROFILE aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$VPC_ID" --region $REGION >> "$OUTPUT_FILE" 2>&1
else
  cat >> "$OUTPUT_FILE" <<EOF
VPC: None (Lambda not in VPC)
EOF
fi

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
10. AWS CONNECT (Voice Integration)
================================================================================

EOF

echo "Gathering AWS Connect..."

cat >> "$OUTPUT_FILE" <<EOF
Connect Instances:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws connect list-instances --region $REGION --query 'InstanceSummaryList[?contains(InstanceAlias, `pf`) || contains(InstanceAlias, `schedule`)]' >> "$OUTPUT_FILE" 2>&1

INSTANCE_IDS=$(AWS_PROFILE=$PROFILE aws connect list-instances --region $REGION --query 'InstanceSummaryList[?contains(InstanceAlias, `pf`) || contains(InstanceAlias, `schedule`)].Id' --output text 2>/dev/null)

for instance_id in $INSTANCE_IDS; do
  echo "  - Connect Instance: $instance_id"
  cat >> "$OUTPUT_FILE" <<EOF

Instance: $instance_id
EOF

  cat >> "$OUTPUT_FILE" <<EOF

Phone Numbers:
EOF
  AWS_PROFILE=$PROFILE aws connect list-phone-numbers-v2 --target-arn "arn:aws:connect:$REGION:$ACCOUNT_ID:instance/$instance_id" --region $REGION >> "$OUTPUT_FILE" 2>&1

  cat >> "$OUTPUT_FILE" <<EOF

Contact Flows:
EOF
  AWS_PROFILE=$PROFILE aws connect list-contact-flows --instance-id "$instance_id" --region $REGION >> "$OUTPUT_FILE" 2>&1
done

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
11. BEDROCK MODEL ACCESS
================================================================================

EOF

echo "Gathering Bedrock model access..."

cat >> "$OUTPUT_FILE" <<EOF
Claude Models with Access:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws bedrock list-foundation-models --region $REGION --query 'modelSummaries[?contains(modelId, `claude`) && modelLifecycle.status==`ACTIVE`].[modelId, modelName]' --output table >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF

Inference Profiles:
--------------------------------------------------------------------------------
EOF
AWS_PROFILE=$PROFILE aws bedrock list-inference-profiles --region $REGION --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `claude`)]' >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
12. CONFIGURATION FILES
================================================================================

EOF

echo "Reading local configuration files..."

cat >> "$OUTPUT_FILE" <<EOF
Agent IDs Configuration:
--------------------------------------------------------------------------------
EOF
cat config/agent_ids.json >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF

Agent Configuration (Dev):
--------------------------------------------------------------------------------
EOF
cat config/agent_config.dev.json >> "$OUTPUT_FILE" 2>&1

cat >> "$OUTPUT_FILE" <<EOF


================================================================================
END OF INVENTORY
================================================================================
Generated: $(date)
================================================================================
EOF

echo ""
echo "================================================================================"
echo "✅ Bedrock Project Inventory Complete!"
echo "================================================================================"
echo "Output file: $OUTPUT_FILE"
echo ""
echo "Summary:"
wc -l "$OUTPUT_FILE"
du -h "$OUTPUT_FILE"
echo "================================================================================"
