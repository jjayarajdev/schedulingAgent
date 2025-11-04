#!/usr/bin/env bash
###############################################################################
# List All AWS Resources Related to ProjectForce
#
# Searches for resources with common naming patterns:
# - pf-*, projectforce*, *bedrock*, *scheduling*, *information*, *chitchat*
###############################################################################

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo ""
echo "================================================================================"
echo "AWS Resources Inventory - ProjectForce Deployment"
echo "================================================================================"
echo ""
echo "Account: $ACCOUNT_ID"
echo "Region:  $REGION"
echo ""
echo "Searching for resources with patterns:"
echo "  • pf-*"
echo "  • projectforce*"
echo "  • *bedrock*"
echo "  • *scheduling*"
echo "  • *information*"
echo "  • *chitchat*"
echo "  • *supervisor*"
echo ""
echo "================================================================================"
echo ""

###############################################################################
# 1. IAM Roles
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}1. IAM Roles${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

ROLES=$(aws iam list-roles --query 'Roles[?contains(RoleName, `pf-`) || contains(RoleName, `projectforce`) || contains(RoleName, `bedrock`) || contains(RoleName, `scheduling`) || contains(RoleName, `information`) || contains(RoleName, `chitchat`) || contains(RoleName, `supervisor`)].RoleName' --output text 2>/dev/null || echo "")

if [[ -n "$ROLES" ]]; then
    for role in $ROLES; do
        CREATED=$(aws iam get-role --role-name "$role" --query 'Role.CreateDate' --output text 2>/dev/null || echo "Unknown")
        echo -e "  ${GREEN}✓${NC} $role"
        echo -e "    ${GRAY}Created: $CREATED${NC}"

        # Show attached policies
        POLICIES=$(aws iam list-attached-role-policies --role-name "$role" --query 'AttachedPolicies[*].PolicyName' --output text 2>/dev/null || echo "")
        if [[ -n "$POLICIES" ]]; then
            echo -e "    ${GRAY}Policies: $POLICIES${NC}"
        fi
        echo ""
    done
else
    echo -e "  ${YELLOW}No IAM roles found${NC}"
    echo ""
fi

###############################################################################
# 2. Lambda Functions
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}2. Lambda Functions${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

FUNCTIONS=$(aws lambda list-functions --region "$REGION" --query 'Functions[?contains(FunctionName, `pf-`) || contains(FunctionName, `projectforce`) || contains(FunctionName, `scheduling`) || contains(FunctionName, `information`) || contains(FunctionName, `chitchat`)].FunctionName' --output text 2>/dev/null || echo "")

if [[ -n "$FUNCTIONS" ]]; then
    for func in $FUNCTIONS; do
        DETAILS=$(aws lambda get-function --function-name "$func" --region "$REGION" 2>/dev/null || echo "{}")
        RUNTIME=$(echo "$DETAILS" | jq -r '.Configuration.Runtime // "Unknown"' 2>/dev/null || echo "Unknown")
        SIZE=$(echo "$DETAILS" | jq -r '.Configuration.CodeSize // 0' 2>/dev/null || echo "0")
        MODIFIED=$(echo "$DETAILS" | jq -r '.Configuration.LastModified // "Unknown"' 2>/dev/null || echo "Unknown")

        echo -e "  ${GREEN}✓${NC} $func"
        echo -e "    ${GRAY}Runtime: $RUNTIME | Size: $SIZE bytes | Modified: $MODIFIED${NC}"
        echo -e "    ${GRAY}ARN: arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${func}${NC}"
        echo ""
    done
else
    echo -e "  ${YELLOW}No Lambda functions found${NC}"
    echo ""
fi

###############################################################################
# 3. Bedrock Agents
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}3. Bedrock Agents${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

AGENTS=$(aws bedrock-agent list-agents --region "$REGION" --query 'agentSummaries[?contains(agentName, `pf-`) || contains(agentName, `Scheduling`) || contains(agentName, `Information`) || contains(agentName, `Chitchat`) || contains(agentName, `Supervisor`)].{Name:agentName,Id:agentId,Status:agentStatus,Updated:updatedAt}' --output json 2>/dev/null || echo "[]")

AGENT_COUNT=$(echo "$AGENTS" | jq 'length' 2>/dev/null || echo "0")

if [[ "$AGENT_COUNT" -gt 0 ]]; then
    echo "$AGENTS" | jq -r '.[] | "  ✓ \(.Name) (ID: \(.Id))\n    Status: \(.Status) | Updated: \(.Updated)\n    ARN: arn:aws:bedrock:'$REGION':'$ACCOUNT_ID':agent/\(.Id)\n"' 2>/dev/null | sed "s/^  ✓/  ${GREEN}✓${NC}/" | sed "s/^    /${GRAY}    /;s/$/${NC}/"
else
    echo -e "  ${YELLOW}No Bedrock agents found${NC}"
    echo ""
fi

###############################################################################
# 4. Secrets Manager Secrets
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}4. Secrets Manager Secrets${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

SECRETS=$(aws secretsmanager list-secrets --region "$REGION" --query 'SecretList[?contains(Name, `projectforce`) || contains(Name, `pf-`)].Name' --output text 2>/dev/null || echo "")

if [[ -n "$SECRETS" ]]; then
    for secret in $SECRETS; do
        DETAILS=$(aws secretsmanager describe-secret --secret-id "$secret" --region "$REGION" 2>/dev/null || echo "{}")
        MODIFIED=$(echo "$DETAILS" | jq -r '.LastChangedDate // "Unknown"' 2>/dev/null || echo "Unknown")

        echo -e "  ${GREEN}✓${NC} $secret"
        echo -e "    ${GRAY}Last Modified: $MODIFIED${NC}"
        echo -e "    ${GRAY}ARN: arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:${secret}${NC}"

        # Show secret keys (not values)
        SECRET_VALUE=$(aws secretsmanager get-secret-value --secret-id "$secret" --region "$REGION" --query 'SecretString' --output text 2>/dev/null || echo "{}")
        KEYS=$(echo "$SECRET_VALUE" | jq -r 'keys | join(", ")' 2>/dev/null || echo "")
        if [[ -n "$KEYS" ]]; then
            echo -e "    ${GRAY}Keys: $KEYS${NC}"
        fi
        echo ""
    done
else
    echo -e "  ${YELLOW}No Secrets Manager secrets found${NC}"
    echo ""
fi

###############################################################################
# 5. DynamoDB Tables
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}5. DynamoDB Tables${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

TABLES=$(aws dynamodb list-tables --region "$REGION" --query 'TableNames[?contains(@, `pf-`) || contains(@, `projectforce`) || contains(@, `scheduling`) || contains(@, `bedrock`)]' --output text 2>/dev/null || echo "")

if [[ -n "$TABLES" ]]; then
    for table in $TABLES; do
        DETAILS=$(aws dynamodb describe-table --table-name "$table" --region "$REGION" 2>/dev/null || echo "{}")
        STATUS=$(echo "$DETAILS" | jq -r '.Table.TableStatus // "Unknown"' 2>/dev/null || echo "Unknown")
        CREATED=$(echo "$DETAILS" | jq -r '.Table.CreationDateTime // "Unknown"' 2>/dev/null || echo "Unknown")
        ITEM_COUNT=$(echo "$DETAILS" | jq -r '.Table.ItemCount // 0' 2>/dev/null || echo "0")

        echo -e "  ${GREEN}✓${NC} $table"
        echo -e "    ${GRAY}Status: $STATUS | Items: $ITEM_COUNT | Created: $CREATED${NC}"
        echo -e "    ${GRAY}ARN: arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${table}${NC}"
        echo ""
    done
else
    echo -e "  ${YELLOW}No DynamoDB tables found${NC}"
    echo ""
fi

###############################################################################
# 6. S3 Buckets
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}6. S3 Buckets${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

ALL_BUCKETS=$(aws s3api list-buckets --query 'Buckets[*].Name' --output text 2>/dev/null || echo "")
FILTERED_BUCKETS=""

for bucket in $ALL_BUCKETS; do
    if [[ "$bucket" == *"pf-"* ]] || [[ "$bucket" == *"projectforce"* ]] || [[ "$bucket" == *"bedrock"* ]] || [[ "$bucket" == *"scheduling"* ]]; then
        FILTERED_BUCKETS="$FILTERED_BUCKETS $bucket"
    fi
done

if [[ -n "$FILTERED_BUCKETS" ]]; then
    for bucket in $FILTERED_BUCKETS; do
        CREATION=$(aws s3api list-buckets --query "Buckets[?Name=='$bucket'].CreationDate" --output text 2>/dev/null || echo "Unknown")
        REGION_BUCKET=$(aws s3api get-bucket-location --bucket "$bucket" --query 'LocationConstraint' --output text 2>/dev/null || echo "us-east-1")

        echo -e "  ${GREEN}✓${NC} $bucket"
        echo -e "    ${GRAY}Region: ${REGION_BUCKET:-us-east-1} | Created: $CREATION${NC}"
        echo ""
    done
else
    echo -e "  ${YELLOW}No S3 buckets found${NC}"
    echo ""
fi

###############################################################################
# 7. CloudWatch Log Groups
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}7. CloudWatch Log Groups${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

LOG_GROUPS=$(aws logs describe-log-groups --region "$REGION" --query 'logGroups[?contains(logGroupName, `/aws/lambda/pf-`) || contains(logGroupName, `projectforce`) || contains(logGroupName, `scheduling`) || contains(logGroupName, `information`) || contains(logGroupName, `chitchat`)].logGroupName' --output text 2>/dev/null || echo "")

if [[ -n "$LOG_GROUPS" ]]; then
    for log_group in $LOG_GROUPS; do
        DETAILS=$(aws logs describe-log-groups --region "$REGION" --log-group-name-prefix "$log_group" --query 'logGroups[0]' --output json 2>/dev/null || echo "{}")
        CREATED=$(echo "$DETAILS" | jq -r '.creationTime // 0' 2>/dev/null || echo "0")
        SIZE=$(echo "$DETAILS" | jq -r '.storedBytes // 0' 2>/dev/null || echo "0")

        if [[ "$CREATED" != "0" ]]; then
            CREATED_DATE=$(date -r $((CREATED / 1000)) 2>/dev/null || echo "Unknown")
        else
            CREATED_DATE="Unknown"
        fi

        echo -e "  ${GREEN}✓${NC} $log_group"
        echo -e "    ${GRAY}Size: $SIZE bytes | Created: $CREATED_DATE${NC}"
        echo ""
    done
else
    echo -e "  ${YELLOW}No CloudWatch log groups found${NC}"
    echo ""
fi

###############################################################################
# 8. IAM Policies (Customer Managed)
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}8. IAM Policies (Customer Managed)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

POLICIES=$(aws iam list-policies --scope Local --query 'Policies[?contains(PolicyName, `pf-`) || contains(PolicyName, `projectforce`) || contains(PolicyName, `bedrock`) || contains(PolicyName, `scheduling`)].{Name:PolicyName,Arn:Arn}' --output json 2>/dev/null || echo "[]")

POLICY_COUNT=$(echo "$POLICIES" | jq 'length' 2>/dev/null || echo "0")

if [[ "$POLICY_COUNT" -gt 0 ]]; then
    echo "$POLICIES" | jq -r '.[] | "  ✓ \(.Name)\n    ARN: \(.Arn)\n"' 2>/dev/null | sed "s/^  ✓/  ${GREEN}✓${NC}/" | sed "s/^    ARN:/${GRAY}    ARN:/;s/$/${NC}/"
else
    echo -e "  ${YELLOW}No customer-managed IAM policies found${NC}"
    echo ""
fi

###############################################################################
# 9. EventBridge Rules
###############################################################################

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}9. EventBridge Rules${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

RULES=$(aws events list-rules --region "$REGION" --query 'Rules[?contains(Name, `pf-`) || contains(Name, `projectforce`) || contains(Name, `scheduling`)].Name' --output text 2>/dev/null || echo "")

if [[ -n "$RULES" ]]; then
    for rule in $RULES; do
        DETAILS=$(aws events describe-rule --name "$rule" --region "$REGION" 2>/dev/null || echo "{}")
        STATE=$(echo "$DETAILS" | jq -r '.State // "Unknown"' 2>/dev/null || echo "Unknown")

        echo -e "  ${GREEN}✓${NC} $rule"
        echo -e "    ${GRAY}State: $STATE${NC}"
        echo ""
    done
else
    echo -e "  ${YELLOW}No EventBridge rules found${NC}"
    echo ""
fi

###############################################################################
# Summary
###############################################################################

echo ""
echo "================================================================================"
echo -e "${CYAN}Summary${NC}"
echo "================================================================================"
echo ""
echo "To delete specific resources, use:"
echo ""
echo "  IAM Roles:        aws iam delete-role --role-name <ROLE_NAME>"
echo "  Lambda:           aws lambda delete-function --function-name <FUNCTION_NAME>"
echo "  Bedrock Agents:   aws bedrock-agent delete-agent --agent-id <AGENT_ID>"
echo "  Secrets:          aws secretsmanager delete-secret --secret-id <SECRET_NAME>"
echo "  DynamoDB:         aws dynamodb delete-table --table-name <TABLE_NAME>"
echo "  S3 Buckets:       aws s3 rb s3://<BUCKET_NAME> --force"
echo "  Log Groups:       aws logs delete-log-group --log-group-name <LOG_GROUP_NAME>"
echo ""
echo "Or use the cleanup script:"
echo "  ./scripts/CLEANUP.sh"
echo ""
echo "================================================================================"
echo ""
