#!/bin/bash
set -e

###############################################################################
# AWS RESOURCE CLEANUP SCRIPT
# Removes ALL scheduling-agent resources from AWS
# Use with caution - this will DELETE all data!
###############################################################################

REGION="us-east-1"
ACCOUNT_ID="618048437522"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 AWS RESOURCE CLEANUP SCRIPT                  ║"
echo "║                                                              ║"
echo "║  This will DELETE ALL scheduling-agent resources:           ║"
echo "║  • 5 Bedrock Agents                                          ║"
echo "║  • 3 Lambda Functions                                        ║"
echo "║  • 2 S3 Buckets (with all contents)                          ║"
echo "║  • 6 DynamoDB Tables (with all data)                         ║"
echo "║  • 10 IAM Roles (with policies)                              ║"
echo "║                                                              ║"
echo "║  THIS ACTION CANNOT BE UNDONE!                               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

read -p "Type 'DELETE ALL' to confirm: " confirmation

if [ "$confirmation" != "DELETE ALL" ]; then
    echo -e "${YELLOW}Cleanup cancelled.${NC}"
    exit 0
fi

echo -e "${GREEN}Starting cleanup...${NC}\n"

###############################################################################
# 1. DELETE BEDROCK AGENTS
###############################################################################
echo -e "${YELLOW}[1/6] Deleting Bedrock Agents...${NC}"

AGENTS=(
    "YDCJTJBSLO"  # scheduling
    "I4UC076CNX"  # information
    "H2GHYHEDS7"  # notes
    "0HRRAJHJOA"  # chitchat
    "GUA4WQTCID"  # supervisor
)

for AGENT_ID in "${AGENTS[@]}"; do
    echo "  Deleting agent: $AGENT_ID"

    # Delete all aliases first
    ALIASES=$(aws bedrock-agent list-agent-aliases \
        --agent-id "$AGENT_ID" \
        --region "$REGION" \
        --query 'agentAliasSummaries[].agentAliasId' \
        --output text 2>/dev/null || echo "")

    for ALIAS_ID in $ALIASES; do
        if [ "$ALIAS_ID" != "TSTALIASID" ]; then
            echo "    Deleting alias: $ALIAS_ID"
            aws bedrock-agent delete-agent-alias \
                --agent-id "$AGENT_ID" \
                --agent-alias-id "$ALIAS_ID" \
                --region "$REGION" 2>/dev/null || true
        fi
    done

    # Wait a bit for aliases to delete
    sleep 2

    # Delete the agent
    aws bedrock-agent delete-agent \
        --agent-id "$AGENT_ID" \
        --region "$REGION" \
        --skip-resource-in-use-check 2>/dev/null || true

    echo "    ✓ Deleted agent $AGENT_ID"
done

echo -e "${GREEN}✓ Bedrock agents deleted${NC}\n"

###############################################################################
# 2. DELETE LAMBDA FUNCTIONS
###############################################################################
echo -e "${YELLOW}[2/6] Deleting Lambda Functions...${NC}"

LAMBDAS=(
    "scheduling-agent-scheduling-actions"
    "scheduling-agent-information-actions"
    "scheduling-agent-notes-actions"
)

for LAMBDA in "${LAMBDAS[@]}"; do
    echo "  Deleting Lambda: $LAMBDA"
    aws lambda delete-function \
        --function-name "$LAMBDA" \
        --region "$REGION" 2>/dev/null || true
    echo "    ✓ Deleted"
done

echo -e "${GREEN}✓ Lambda functions deleted${NC}\n"

###############################################################################
# 3. DELETE S3 BUCKETS
###############################################################################
echo -e "${YELLOW}[3/6] Deleting S3 Buckets...${NC}"

BUCKETS=(
    "scheduling-agent-schemas-dev-618048437522"
    "scheduling-agent-artifacts-dev"
)

for BUCKET in "${BUCKETS[@]}"; do
    echo "  Emptying bucket: $BUCKET"

    # Empty the bucket first
    aws s3 rm "s3://$BUCKET" --recursive 2>/dev/null || true

    echo "  Deleting bucket: $BUCKET"
    aws s3 rb "s3://$BUCKET" --force 2>/dev/null || true

    echo "    ✓ Deleted"
done

echo -e "${GREEN}✓ S3 buckets deleted${NC}\n"

###############################################################################
# 4. DELETE DYNAMODB TABLES
###############################################################################
echo -e "${YELLOW}[4/6] Deleting DynamoDB Tables...${NC}"

TABLES=(
    "scheduling-agent-projects-dev"
    "scheduling-agent-appointments-dev"
    "scheduling-agent-availability-dev"
    "scheduling-agent-sessions-dev"
    "scheduling-agent-notes-dev"
    "scheduling-agent-bulk-ops-tracking-dev"
)

for TABLE in "${TABLES[@]}"; do
    echo "  Deleting table: $TABLE"
    aws dynamodb delete-table \
        --table-name "$TABLE" \
        --region "$REGION" 2>/dev/null || true
    echo "    ✓ Deleted"
done

echo -e "${GREEN}✓ DynamoDB tables deleted${NC}\n"

###############################################################################
# 5. DELETE IAM ROLES
###############################################################################
echo -e "${YELLOW}[5/6] Deleting IAM Roles and Policies...${NC}"

ROLES=(
    "scheduling-agent-scheduling-agent-role-dev"
    "scheduling-agent-information-agent-role-dev"
    "scheduling-agent-notes-agent-role-dev"
    "scheduling-agent-chitchat-agent-role-dev"
    "scheduling-agent-supervisor-agent-role-dev"
    "scheduling-agent-scheduling-lambda-role-dev"
    "scheduling-agent-information-lambda-role-dev"
    "scheduling-agent-notes-lambda-role-dev"
    "scheduling-agent-lambda-role"
    "scheduling-agent-bulk-ops-lambda-role"
)

for ROLE in "${ROLES[@]}"; do
    echo "  Deleting role: $ROLE"

    # Detach all managed policies
    POLICIES=$(aws iam list-attached-role-policies \
        --role-name "$ROLE" \
        --query 'AttachedPolicies[].PolicyArn' \
        --output text 2>/dev/null || echo "")

    for POLICY_ARN in $POLICIES; do
        echo "    Detaching policy: $POLICY_ARN"
        aws iam detach-role-policy \
            --role-name "$ROLE" \
            --policy-arn "$POLICY_ARN" 2>/dev/null || true
    done

    # Delete inline policies
    INLINE_POLICIES=$(aws iam list-role-policies \
        --role-name "$ROLE" \
        --query 'PolicyNames[]' \
        --output text 2>/dev/null || echo "")

    for POLICY_NAME in $INLINE_POLICIES; do
        echo "    Deleting inline policy: $POLICY_NAME"
        aws iam delete-role-policy \
            --role-name "$ROLE" \
            --policy-name "$POLICY_NAME" 2>/dev/null || true
    done

    # Delete the role
    aws iam delete-role --role-name "$ROLE" 2>/dev/null || true
    echo "    ✓ Deleted role"
done

echo -e "${GREEN}✓ IAM roles deleted${NC}\n"

###############################################################################
# 6. CLEANUP LOCAL STATE
###############################################################################
echo -e "${YELLOW}[6/6] Cleaning up local state files...${NC}"

cd "$(dirname "$0")"

# Remove Terraform state
rm -f terraform.tfstate*
rm -f .terraform.lock.hcl
rm -rf .terraform/

# Remove deployment states
rm -f .deployment_state_*.json
rm -f deployment_*.log

# Remove Lambda packages
rm -f lambda_*.zip

echo -e "${GREEN}✓ Local state cleaned${NC}\n"

###############################################################################
# SUMMARY
###############################################################################
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   CLEANUP COMPLETED!                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "All resources have been deleted. AWS is now clean."
echo ""
echo "Next steps:"
echo "  1. Update Terraform configs with 'pf' prefix"
echo "  2. Run: terraform init"
echo "  3. Run: terraform apply"
echo ""
