#!/bin/bash

##############################################################################
# CLEANUP.sh - Complete Infrastructure Cleanup
#
# Purpose: Delete all ProjectForce Bedrock infrastructure including VPC changes
# WARNING: This will delete ALL resources. Use with caution!
#
# Usage:
#   ./CLEANUP.sh --dry-run                   # Show what would be deleted (safe)
#   ./CLEANUP.sh --confirm                   # Actually delete resources
#   ./CLEANUP.sh --dry-run --profile pf-aws  # Use specific AWS profile
#   ./CLEANUP.sh --confirm --profile pf-aws  # Delete with specific profile
##############################################################################

set -e

# AWS Profile Support
AWS_PROFILE="${AWS_PROFILE:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DRY_RUN=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --confirm)
            DRY_RUN=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run            Show what would be deleted (safe)"
            echo "  --confirm            Actually delete resources"
            echo "  --profile PROFILE    AWS profile to use (default: none, uses default profile)"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --dry-run                    # Preview deletion with default profile"
            echo "  $0 --confirm --profile pf-aws   # Delete using pf-aws profile"
            echo "  AWS_PROFILE=pf-aws $0 --confirm # Delete using environment variable"
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check that either --dry-run or --confirm was specified
if [[ "$DRY_RUN" == "true" ]]; then
    : # dry-run is default, no action needed
else
    : # confirm was specified, proceed
fi

# AWS CLI wrapper function
aws_cmd() {
    if [[ -n "$AWS_PROFILE" ]]; then
        aws --profile "$AWS_PROFILE" "$@"
    else
        aws "$@"
    fi
}

REGION="us-east-1"
ACCOUNT_ID=$(aws_cmd sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
ENV="dev"

echo "=========================================="
echo "ProjectForce Infrastructure Cleanup"
echo "=========================================="
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
if [[ -n "$AWS_PROFILE" ]]; then
    echo "Profile: $AWS_PROFILE"
fi
echo "Environment: $ENV"
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}DRY RUN MODE: No resources will be deleted${NC}"
else
    echo -e "${RED}⚠️  DANGER: This will DELETE all resources!${NC}"
    echo ""
    echo "Resources to be deleted:"
    echo "  • VPC Endpoint for Bedrock"
    echo "  • Lambda VPC configuration"
    echo "  • Lambda functions (3)"
    echo "  • Bedrock agents (4)"
    echo "  • IAM roles and policies (7+)"
    echo "  • Security group HTTPS rule"
    echo "  • DynamoDB tables"
    echo "  • Secrets Manager secrets"
    echo ""
    read -p "Type 'DELETE EVERYTHING' to confirm: " CONFIRM
    if [[ "$CONFIRM" != "DELETE EVERYTHING" ]]; then
        echo "Cleanup cancelled."
        exit 0
    fi
fi
echo ""

delete_resource() {
    local TYPE=$1
    local ID=$2
    local CMD=$3

    if [[ "$DRY_RUN" == "true" ]]; then
        echo -e "${YELLOW}[DRY RUN]${NC} Would delete $TYPE: $ID"
    else
        echo -e "${BLUE}→${NC} Deleting $TYPE: $ID"
        if eval "$CMD" &>/dev/null; then
            echo -e "${GREEN}✅${NC} Deleted: $ID"
        else
            echo -e "${RED}❌${NC} Failed: $ID"
        fi
    fi
}

##############################################################################
# Step 1: Delete VPC Endpoint
##############################################################################

echo ""
echo "Step 1: VPC Endpoint"
echo "===================="

VPC_ENDPOINT=$(aws_cmd ec2 describe-vpc-endpoints \
    --region "$REGION" \
    --filters "Name=service-name,Values=com.amazonaws.${REGION}.bedrock-agent-runtime" \
    --query 'VpcEndpoints[0].VpcEndpointId' \
    --output text 2>/dev/null || echo "")

if [[ -n "$VPC_ENDPOINT" ]] && [[ "$VPC_ENDPOINT" != "None" ]]; then
    delete_resource "VPC Endpoint" "$VPC_ENDPOINT" \
        "aws_cmd ec2 delete-vpc-endpoints --vpc-endpoint-ids $VPC_ENDPOINT --region $REGION"
else
    echo "  ℹ️  No VPC endpoint found"
fi

##############################################################################
# Step 2: Remove Lambda from VPC
##############################################################################

echo ""
echo "Step 2: Lambda VPC Configuration"
echo "================================="

if aws_cmd lambda get-function --function-name pf-orchestrator --region "$REGION" &>/dev/null; then
    VPC=$(aws_cmd lambda get-function-configuration \
        --function-name pf-orchestrator \
        --region "$REGION" \
        --query 'VpcConfig.VpcId' \
        --output text 2>/dev/null || echo "")

    if [[ -n "$VPC" ]] && [[ "$VPC" != "None" ]]; then
        delete_resource "Lambda VPC" "pf-orchestrator" \
            "aws_cmd lambda update-function-configuration --function-name pf-orchestrator --vpc-config SubnetIds=[],SecurityGroupIds=[] --region $REGION"
        
        if [[ "$DRY_RUN" == "false" ]]; then
            echo "  ⏳ Waiting 30s for VPC detachment..."
            sleep 30
        fi
    else
        echo "  ℹ️  Lambda not in VPC"
    fi
fi

##############################################################################
# Step 3: Delete Bedrock Agents
##############################################################################

echo ""
echo "Step 3: Bedrock Agents"
echo "======================"

for NAME in "SchedulingAgent" "pf-information" "pf-chitchat" "Supervisor"; do
    ID=$(aws_cmd bedrock-agent list-agents --region "$REGION" \
        --query "agentSummaries[?agentName=='$NAME'].agentId" \
        --output text 2>/dev/null || echo "")

    if [[ -n "$ID" ]]; then
        delete_resource "Agent" "$NAME" \
            "aws_cmd bedrock-agent delete-agent --agent-id $ID --skip-resource-in-use-check --region $REGION"
    else
        echo "  ℹ️  Not found: $NAME"
    fi
done

[[ "$DRY_RUN" == "false" ]] && sleep 10

##############################################################################
# Step 4: Delete Lambda Functions
##############################################################################

echo ""
echo "Step 4: Lambda Functions"
echo "========================"

for FUNC in "pf-orchestrator" "pf-scheduling-actions" "pf-information-actions"; do
    if aws_cmd lambda get-function --function-name "$FUNC" --region "$REGION" &>/dev/null; then
        delete_resource "Lambda" "$FUNC" \
            "aws_cmd lambda delete-function --function-name $FUNC --region $REGION"
    else
        echo "  ℹ️  Not found: $FUNC"
    fi
done

##############################################################################
# Step 5: Delete IAM Roles
##############################################################################

echo ""
echo "Step 5: IAM Roles"
echo "================="

ROLES=(
    "pf-orchestrator-role-dev"
    "pf-scheduling-actions-role-dev"
    "pf-information-actions-role-dev"
    "AmazonBedrockExecutionRoleForAgents_SchedulingAgent"
    "AmazonBedrockExecutionRoleForAgents_pf-information"
    "AmazonBedrockExecutionRoleForAgents_pf-chitchat"
    "AmazonBedrockExecutionRoleForAgents_Supervisor"
)

for ROLE in "${ROLES[@]}"; do
    if aws_cmd iam get-role --role-name "$ROLE" &>/dev/null; then
        
        # Detach policies
        if [[ "$DRY_RUN" == "false" ]]; then
            aws_cmd iam list-attached-role-policies --role-name "$ROLE" \
                --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null | \
                xargs -n1 aws_cmd iam detach-role-policy --role-name "$ROLE" --policy-arn 2>/dev/null || true
            
            aws_cmd iam list-role-policies --role-name "$ROLE" \
                --query 'PolicyNames[]' --output text 2>/dev/null | \
                xargs -n1 aws_cmd iam delete-role-policy --role-name "$ROLE" --policy-name 2>/dev/null || true
        fi

        delete_resource "IAM Role" "$ROLE" \
            "aws_cmd iam delete-role --role-name $ROLE"
    else
        echo "  ℹ️  Not found: $ROLE"
    fi
done

##############################################################################
# Step 6: Remove Security Group Rule
##############################################################################

echo ""
echo "Step 6: Security Group Rules"
echo "============================="

# Check for legacy Redis cluster security group (DynamoDB doesn't use security groups)
REDIS_CLUSTER_ID="pf-sessions-${ENV}"
if aws_cmd elasticache describe-cache-clusters --cache-cluster-id "$REDIS_CLUSTER_ID" --region "$REGION" &>/dev/null 2>&1; then
    SG=$(aws_cmd elasticache describe-cache-clusters \
        --cache-cluster-id "$REDIS_CLUSTER_ID" \
        --region "$REGION" \
        --query 'CacheClusters[0].SecurityGroups[0].SecurityGroupId' \
        --output text 2>/dev/null)

    if [[ -n "$SG" ]] && [[ "$SG" != "None" ]]; then
        if aws_cmd ec2 describe-security-groups --group-ids "$SG" --region "$REGION" &>/dev/null 2>&1; then
            HAS_443=$(aws_cmd ec2 describe-security-groups --group-ids "$SG" --region "$REGION" \
                --query "SecurityGroups[0].IpPermissions[?FromPort==\`443\`]" \
                --output text 2>/dev/null)

            if [[ -n "$HAS_443" ]]; then
                # Get VPC CIDR for this security group
                VPC_ID=$(aws_cmd ec2 describe-security-groups --group-ids "$SG" --region "$REGION" \
                    --query 'SecurityGroups[0].VpcId' --output text 2>/dev/null)
                VPC_CIDR=$(aws_cmd ec2 describe-vpcs --vpc-ids "$VPC_ID" --region "$REGION" \
                    --query 'Vpcs[0].CidrBlock' --output text 2>/dev/null)

                delete_resource "SG Rule" "TCP/443 on $SG" \
                    "aws_cmd ec2 revoke-security-group-ingress --group-id $SG --protocol tcp --port 443 --cidr $VPC_CIDR --region $REGION"
            else
                echo "  ℹ️  No HTTPS rule found"
            fi
        else
            echo "  ℹ️  Security group not found: $SG"
        fi
    else
        echo "  ℹ️  No security group associated with Redis cluster"
    fi
else
    echo "  ℹ️  Redis cluster not found, skipping security group cleanup"
fi

##############################################################################
# Step 7: Delete DynamoDB Tables
##############################################################################

echo ""
echo "Step 7: DynamoDB Tables"
echo "======================="

if aws_cmd dynamodb describe-table --table-name pf-sessions-dev --region "$REGION" &>/dev/null; then
    delete_resource "DynamoDB" "pf-sessions-dev" \
        "aws_cmd dynamodb delete-table --table-name pf-sessions-dev --region $REGION"
else
    echo "  ℹ️  Table not found: pf-sessions-dev"
fi

echo ""
if aws_cmd dynamodb describe-table --table-name pf-notes-dev --region "$REGION" &>/dev/null; then
    delete_resource "DynamoDB" "pf-notes-dev" \
        "aws_cmd dynamodb delete-table --table-name pf-notes-dev --region $REGION"
else
    echo "  ℹ️  Table not found: pf-notes-dev"
fi

##############################################################################
# Step 8: Delete Secrets
##############################################################################

echo ""
echo "Step 8: Secrets Manager"
echo "======================="

if aws_cmd secretsmanager describe-secret --secret-id projectforce/api/credentials --region "$REGION" &>/dev/null; then
    delete_resource "Secret" "projectforce/api/credentials" \
        "aws_cmd secretsmanager delete-secret --secret-id projectforce/api/credentials --force-delete-without-recovery --region $REGION"
else
    echo "  ℹ️  Secret not found"
fi

##############################################################################
# Step 9: Delete DynamoDB Session Table
##############################################################################

echo ""
echo "Step 9: DynamoDB Session Table"
echo "==============================="

DYNAMODB_TABLE="pf-sessions-${ENV}"
if aws_cmd dynamodb describe-table --table-name "$DYNAMODB_TABLE" --region "$REGION" &>/dev/null 2>&1; then
    delete_resource "DynamoDB Table" "$DYNAMODB_TABLE" \
        "aws_cmd dynamodb delete-table --table-name $DYNAMODB_TABLE --region $REGION"
else
    echo "  ℹ️  DynamoDB table not found"
fi

##############################################################################
# Summary
##############################################################################

echo ""
echo "=========================================="
if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${GREEN}Dry Run Complete${NC}"
    echo "=========================================="
    echo ""
    echo "No resources deleted. To actually delete:"
    echo "  $0 --confirm"
else
    echo -e "${GREEN}Cleanup Complete${NC}"
    echo "=========================================="
    echo ""
    echo "✅ All resources deleted"
    echo ""
    echo -e "${YELLOW}Optional manual cleanup:${NC}"
    echo "  • Config files: rm -rf config/agent_ids.json config/agent_config.*.json"
    echo "  • CloudWatch logs: Check /aws/lambda/* log groups"
    echo ""
    echo -e "${BLUE}Note:${NC} DynamoDB table deletion is immediate"
    echo ""
    echo -e "${BLUE}To verify DynamoDB table deletion:${NC}"
    if [[ -n "$AWS_PROFILE" ]]; then
        echo "  AWS_PROFILE=$AWS_PROFILE aws dynamodb describe-table \\"
    else
        echo "  aws dynamodb describe-table \\"
    fi
    echo "    --table-name pf-sessions-$ENV \\"
    echo "    --region $REGION"
    echo "    --output text 2>&1"
    echo ""
    echo "  Expected output:"
    echo "    • 'deleting' = Still in progress"
    echo "    • 'CacheClusterNotFound' = ✅ Deletion complete"
fi
echo ""
