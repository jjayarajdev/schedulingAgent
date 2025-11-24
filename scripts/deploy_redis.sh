#!/bin/bash

###############################################################################
# deploy_redis.sh - Deploy ElastiCache Redis for Orchestrator Lambda
###############################################################################
#
# Purpose: Create and configure ElastiCache Redis cluster for session management
#
# Prerequisites:
#   - AWS CLI configured
#   - VPC with private subnets
#   - Security groups configured
#
# Usage: ./deploy_redis.sh [environment]
#
###############################################################################

set -e

# AWS Profile Support
AWS_PROFILE="${AWS_PROFILE:-}"

# Parse parameters
ENV="dev"
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [environment]"
            echo ""
            echo "Options:"
            echo "  --profile PROFILE    AWS profile to use (default: none, uses default profile)"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Arguments:"
            echo "  environment          Environment name (default: dev)"
            echo ""
            echo "Examples:"
            echo "  $0                           # Deploy to dev with default profile"
            echo "  $0 --profile pf-aws          # Deploy to dev with pf-aws profile"
            echo "  $0 --profile pf-aws staging  # Deploy to staging with pf-aws profile"
            exit 0
            ;;
        *)
            ENV="$1"
            shift
            ;;
    esac
done

# AWS CLI wrapper function
aws_cmd() {
    if [[ -n "$AWS_PROFILE" ]]; then
        aws --profile "$AWS_PROFILE" "$@"
    else
        aws "$@"
    fi
}

# Configuration
REGION="${AWS_REGION:-us-east-1}"
CLUSTER_ID="pf-sessions-${ENV}"
NODE_TYPE="cache.t3.micro"  # Smallest/cheapest for dev, use cache.r6g.large for prod
ENGINE="redis"
ENGINE_VERSION="7.0"
NUM_NODES=1
PORT=6379

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "================================================================================"
echo -e "${BLUE}ElastiCache Redis Deployment${NC}"
echo "================================================================================"
echo ""
echo "Environment: $ENV"
echo "Region:      $REGION"
echo "Cluster ID:  $CLUSTER_ID"
echo "Node Type:   $NODE_TYPE"
echo ""

###############################################################################
# Step 1: Check for existing cluster
###############################################################################

echo -e "${YELLOW}Step 1: Checking for existing Redis cluster${NC}"
echo ""

if aws_cmd elasticache describe-cache-clusters \
    --cache-cluster-id "$CLUSTER_ID" \
    --region "$REGION" \
    &>/dev/null; then

    echo -e "${GREEN}✓ Redis cluster already exists: $CLUSTER_ID${NC}"

    # Get cluster details
    CLUSTER_STATUS=$(aws_cmd elasticache describe-cache-clusters \
        --cache-cluster-id "$CLUSTER_ID" \
        --region "$REGION" \
        --query 'CacheClusters[0].CacheClusterStatus' \
        --output text)

    echo "  Status: $CLUSTER_STATUS"

    if [[ "$CLUSTER_STATUS" == "available" ]]; then
        REDIS_ENDPOINT=$(aws_cmd elasticache describe-cache-clusters \
            --cache-cluster-id "$CLUSTER_ID" \
            --region "$REGION" \
            --show-cache-node-info \
            --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
            --output text)

        REDIS_PORT=$(aws_cmd elasticache describe-cache-clusters \
            --cache-cluster-id "$CLUSTER_ID" \
            --region "$REGION" \
            --show-cache-node-info \
            --query 'CacheClusters[0].CacheNodes[0].Endpoint.Port' \
            --output text)

        echo "  Endpoint: $REDIS_ENDPOINT:$REDIS_PORT"
        echo ""
        echo -e "${GREEN}✓ Redis cluster is ready to use${NC}"
        echo ""

        # Display next steps
        echo "================================================================================"
        echo -e "${GREEN}Next Steps:${NC}"
        echo "================================================================================"
        echo ""
        echo "1. Update Orchestrator Lambda environment variables:"
        echo ""
        echo -e "${YELLOW}aws lambda update-function-configuration \\${NC}"
        echo -e "${YELLOW}  --function-name pf-orchestrator \\${NC}"
        echo -e "${YELLOW}  --environment Variables='{\"REDIS_ENDPOINT\":\"$REDIS_ENDPOINT\",\"REDIS_PORT\":\"$REDIS_PORT\",\"SUPERVISOR_AGENT_ID\":\"your-supervisor-id\"}'${NC}"
        echo ""
        echo "2. Or update via AWS Console:"
        echo "   • Go to Lambda > pf-orchestrator > Configuration > Environment variables"
        echo "   • Add: REDIS_ENDPOINT = $REDIS_ENDPOINT"
        echo "   • Add: REDIS_PORT = $REDIS_PORT"
        echo ""
        exit 0
    else
        echo -e "${YELLOW}⚠ Cluster exists but not available yet (status: $CLUSTER_STATUS)${NC}"
        echo "  Waiting for cluster to become available..."
    fi
else
    echo "  ℹ️  No existing cluster found, will create new one"
fi

echo ""

###############################################################################
# Step 2: Get VPC and Subnet Information
###############################################################################

echo -e "${YELLOW}Step 2: Getting VPC and Subnet Information${NC}"
echo ""

# Try to get default VPC
DEFAULT_VPC=$(aws_cmd ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --region "$REGION" \
    --query 'Vpcs[0].VpcId' \
    --output text 2>/dev/null || echo "")

if [[ -z "$DEFAULT_VPC" || "$DEFAULT_VPC" == "None" ]]; then
    # Get any VPC
    DEFAULT_VPC=$(aws_cmd ec2 describe-vpcs \
        --region "$REGION" \
        --query 'Vpcs[0].VpcId' \
        --output text 2>/dev/null || echo "")
fi

if [[ -z "$DEFAULT_VPC" || "$DEFAULT_VPC" == "None" ]]; then
    echo -e "${RED}✗ No VPC found in region $REGION${NC}"
    echo ""
    echo "Please create a VPC first or specify VPC_ID environment variable"
    exit 1
fi

echo "  VPC ID: $DEFAULT_VPC"

# Get subnets
SUBNETS=$(aws_cmd ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$DEFAULT_VPC" \
    --region "$REGION" \
    --query 'Subnets[*].SubnetId' \
    --output text)

if [[ -z "$SUBNETS" ]]; then
    echo -e "${RED}✗ No subnets found in VPC $DEFAULT_VPC${NC}"
    exit 1
fi

SUBNET_ARRAY=($SUBNETS)
echo "  Subnets: ${SUBNET_ARRAY[@]}"
echo ""

###############################################################################
# Step 3: Create Cache Subnet Group
###############################################################################

echo -e "${YELLOW}Step 3: Creating Cache Subnet Group${NC}"
echo ""

SUBNET_GROUP_NAME="pf-redis-subnet-group-${ENV}"

# Check if subnet group exists
if aws_cmd elasticache describe-cache-subnet-groups \
    --cache-subnet-group-name "$SUBNET_GROUP_NAME" \
    --region "$REGION" \
    &>/dev/null; then
    echo -e "${GREEN}✓ Cache subnet group already exists: $SUBNET_GROUP_NAME${NC}"
else
    echo "  → Creating subnet group: $SUBNET_GROUP_NAME"

    aws_cmd elasticache create-cache-subnet-group \
        --cache-subnet-group-name "$SUBNET_GROUP_NAME" \
        --cache-subnet-group-description "Subnet group for ProjectForce Redis cluster ($ENV)" \
        --subnet-ids ${SUBNET_ARRAY[@]} \
        --region "$REGION" \
        &>/dev/null

    echo -e "${GREEN}✓ Cache subnet group created${NC}"
fi

echo ""

###############################################################################
# Step 4: Create Security Group
###############################################################################

echo -e "${YELLOW}Step 4: Creating Security Group${NC}"
echo ""

SECURITY_GROUP_NAME="pf-redis-sg-${ENV}"

# Check if security group exists
EXISTING_SG=$(aws_cmd ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" "Name=vpc-id,Values=$DEFAULT_VPC" \
    --region "$REGION" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "")

if [[ -n "$EXISTING_SG" && "$EXISTING_SG" != "None" ]]; then
    SECURITY_GROUP_ID="$EXISTING_SG"
    echo -e "${GREEN}✓ Security group already exists: $SECURITY_GROUP_ID${NC}"
else
    echo "  → Creating security group: $SECURITY_GROUP_NAME"

    SECURITY_GROUP_ID=$(aws_cmd ec2 create-security-group \
        --group-name "$SECURITY_GROUP_NAME" \
        --description "Security group for ProjectForce Redis cluster ($ENV)" \
        --vpc-id "$DEFAULT_VPC" \
        --region "$REGION" \
        --query 'GroupId' \
        --output text)

    echo -e "${GREEN}✓ Security group created: $SECURITY_GROUP_ID${NC}"

    # Add inbound rule for Redis port from VPC CIDR
    VPC_CIDR=$(aws_cmd ec2 describe-vpcs \
        --vpc-ids "$DEFAULT_VPC" \
        --region "$REGION" \
        --query 'Vpcs[0].CidrBlock' \
        --output text)

    echo "  → Adding inbound rule for Redis port $PORT from VPC ($VPC_CIDR)"

    aws_cmd ec2 authorize-security-group-ingress \
        --group-id "$SECURITY_GROUP_ID" \
        --protocol tcp \
        --port "$PORT" \
        --cidr "$VPC_CIDR" \
        --region "$REGION" \
        &>/dev/null

    echo -e "${GREEN}✓ Inbound rule added${NC}"
fi

echo ""

###############################################################################
# Step 5: Create Redis Cluster
###############################################################################

echo -e "${YELLOW}Step 5: Creating Redis Cluster${NC}"
echo ""

if aws_cmd elasticache describe-cache-clusters \
    --cache-cluster-id "$CLUSTER_ID" \
    --region "$REGION" \
    &>/dev/null; then
    echo -e "${GREEN}✓ Cluster already exists (verified)${NC}"
else
    echo "  → Creating Redis cluster: $CLUSTER_ID"
    echo "  → Node type: $NODE_TYPE"
    echo "  → Engine: $ENGINE $ENGINE_VERSION"
    echo ""
    echo "  ℹ️  This will take 5-10 minutes..."
    echo ""

    aws_cmd elasticache create-cache-cluster \
        --cache-cluster-id "$CLUSTER_ID" \
        --cache-node-type "$NODE_TYPE" \
        --engine "$ENGINE" \
        --engine-version "$ENGINE_VERSION" \
        --num-cache-nodes "$NUM_NODES" \
        --cache-subnet-group-name "$SUBNET_GROUP_NAME" \
        --security-group-ids "$SECURITY_GROUP_ID" \
        --region "$REGION" \
        &>/dev/null

    echo -e "${GREEN}✓ Redis cluster creation initiated${NC}"
fi

echo ""

###############################################################################
# Step 6: Wait for Cluster to be Available
###############################################################################

echo -e "${YELLOW}Step 6: Waiting for cluster to be available${NC}"
echo ""

echo "  → Waiting for cluster to reach 'available' status..."
echo "  → This typically takes 5-10 minutes"
echo ""

MAX_WAIT=600  # 10 minutes
WAIT_TIME=0
SLEEP_INTERVAL=15

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    CLUSTER_STATUS=$(aws_cmd elasticache describe-cache-clusters \
        --cache-cluster-id "$CLUSTER_ID" \
        --region "$REGION" \
        --query 'CacheClusters[0].CacheClusterStatus' \
        --output text 2>/dev/null || echo "creating")

    if [[ "$CLUSTER_STATUS" == "available" ]]; then
        echo ""
        echo -e "${GREEN}✓ Cluster is available!${NC}"
        break
    fi

    echo -n "."
    sleep $SLEEP_INTERVAL
    WAIT_TIME=$((WAIT_TIME + SLEEP_INTERVAL))
done

echo ""

if [[ "$CLUSTER_STATUS" != "available" ]]; then
    echo -e "${YELLOW}⚠ Cluster is still not available after $MAX_WAIT seconds${NC}"
    echo "  Current status: $CLUSTER_STATUS"
    echo ""
    echo "  → Check cluster status with:"
    echo "    aws_cmd elasticache describe-cache-clusters --cache-cluster-id $CLUSTER_ID --region $REGION"
    echo ""
    exit 1
fi

###############################################################################
# Step 7: Get Cluster Endpoint
###############################################################################

echo ""
echo -e "${YELLOW}Step 7: Getting cluster endpoint${NC}"
echo ""

REDIS_ENDPOINT=$(aws_cmd elasticache describe-cache-clusters \
    --cache-cluster-id "$CLUSTER_ID" \
    --region "$REGION" \
    --show-cache-node-info \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
    --output text)

REDIS_PORT=$(aws_cmd elasticache describe-cache-clusters \
    --cache-cluster-id "$CLUSTER_ID" \
    --region "$REGION" \
    --show-cache-node-info \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Port' \
    --output text)

echo -e "${GREEN}✓ Cluster endpoint: $REDIS_ENDPOINT:$REDIS_PORT${NC}"
echo ""

###############################################################################
# Summary
###############################################################################

echo "================================================================================"
echo -e "${GREEN}✓ Redis Deployment Complete!${NC}"
echo "================================================================================"
echo ""
echo "Cluster Details:"
echo "  • Cluster ID:    $CLUSTER_ID"
echo "  • Endpoint:      $REDIS_ENDPOINT"
echo "  • Port:          $REDIS_PORT"
echo "  • Node Type:     $NODE_TYPE"
echo "  • Engine:        $ENGINE $ENGINE_VERSION"
echo "  • VPC:           $DEFAULT_VPC"
echo "  • Security Group: $SECURITY_GROUP_ID"
echo ""
echo "================================================================================"
echo -e "${GREEN}Next Steps:${NC}"
echo "================================================================================"
echo ""
echo "1. Update Orchestrator Lambda environment variables:"
echo ""
echo -e "${YELLOW}aws lambda update-function-configuration \\${NC}"
echo -e "${YELLOW}  --function-name pf-orchestrator \\${NC}"
echo -e "${YELLOW}  --environment Variables='{${NC}"
echo -e "${YELLOW}    \"REDIS_ENDPOINT\":\"$REDIS_ENDPOINT\",${NC}"
echo -e "${YELLOW}    \"REDIS_PORT\":\"$REDIS_PORT\",${NC}"
echo -e "${YELLOW}    \"REDIS_SSL\":\"true\",${NC}"
echo -e "${YELLOW}    \"SUPERVISOR_AGENT_ID\":\"your-supervisor-id\",${NC}"
echo -e "${YELLOW}    \"AWS_REGION\":\"$REGION\"${NC}"
echo -e "${YELLOW}  }'${NC}"
echo ""
echo "2. Update Lambda VPC configuration to access Redis:"
echo ""
echo -e "${YELLOW}aws lambda update-function-configuration \\${NC}"
echo -e "${YELLOW}  --function-name pf-orchestrator \\${NC}"
echo -e "${YELLOW}  --vpc-config SubnetIds=${SUBNET_ARRAY[0]},${SUBNET_ARRAY[1]:-},SecurityGroupIds=$SECURITY_GROUP_ID${NC}"
echo ""
echo "3. Test Redis connection (if you have redis-cli installed):"
echo ""
echo -e "${YELLOW}redis-cli -h $REDIS_ENDPOINT -p $REDIS_PORT ping${NC}"
echo ""
echo "4. Monitor cluster:"
echo ""
echo -e "${YELLOW}aws elasticache describe-cache-clusters \\${NC}"
echo -e "${YELLOW}  --cache-cluster-id $CLUSTER_ID \\${NC}"
echo -e "${YELLOW}  --show-cache-node-info${NC}"
echo ""
echo "================================================================================"
echo ""
