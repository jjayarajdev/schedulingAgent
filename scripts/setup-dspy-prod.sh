#!/bin/bash
#
# Setup DSPy Resources for Production (us-east-2)
#
# This script creates:
# 1. S3 buckets for DSPy models and training logs
# 2. DynamoDB table for training logs
# 3. Updates IAM permissions for orchestrator
# 4. Copies DSPy models from dev to prod
# 5. Updates Lambda environment variables
#
# Usage: ./setup-dspy-prod.sh [--dry-run]
#
# Created: January 5, 2026

set -e

PROFILE="pf-aws"
REGION="us-east-2"
ACCOUNT_ID="772634497954"

# Resource names
DSPY_BUCKET="pf-syn-dspy-models-prod"
TRAINING_BUCKET="pf-syn-training-logs-prod"
TRAINING_TABLE="pf-syn-training-logs-prod"
ORCHESTRATOR_ROLE="pf-syn-orchestrator-role-prod"
ORCHESTRATOR_LAMBDA="pf-syn-orchestrator-prod"

# Source bucket (DEV)
DEV_DSPY_BUCKET="pf-syn-dspy-models-dev"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}=== DRY RUN MODE - No changes will be made ===${NC}"
    echo ""
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  DSPy Production Setup (us-east-2)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# -----------------------------------------------------------------------------
# Step 1: Create S3 Buckets
# -----------------------------------------------------------------------------
echo -e "${GREEN}Step 1: Creating S3 Buckets${NC}"
echo "----------------------------------------"

# Create DSPy models bucket
echo -n "  Creating $DSPY_BUCKET... "
if aws --profile $PROFILE s3api head-bucket --bucket $DSPY_BUCKET 2>/dev/null; then
    echo -e "${YELLOW}EXISTS${NC}"
else
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}WOULD CREATE${NC}"
    else
        aws --profile $PROFILE s3api create-bucket \
            --bucket $DSPY_BUCKET \
            --region $REGION \
            --create-bucket-configuration LocationConstraint=$REGION
        echo -e "${GREEN}CREATED${NC}"
    fi
fi

# Create training logs bucket
echo -n "  Creating $TRAINING_BUCKET... "
if aws --profile $PROFILE s3api head-bucket --bucket $TRAINING_BUCKET 2>/dev/null; then
    echo -e "${YELLOW}EXISTS${NC}"
else
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}WOULD CREATE${NC}"
    else
        aws --profile $PROFILE s3api create-bucket \
            --bucket $TRAINING_BUCKET \
            --region $REGION \
            --create-bucket-configuration LocationConstraint=$REGION
        echo -e "${GREEN}CREATED${NC}"
    fi
fi

echo ""

# -----------------------------------------------------------------------------
# Step 2: Create DynamoDB Table
# -----------------------------------------------------------------------------
echo -e "${GREEN}Step 2: Creating DynamoDB Table${NC}"
echo "----------------------------------------"

echo -n "  Creating $TRAINING_TABLE... "
if aws --profile $PROFILE dynamodb describe-table --table-name $TRAINING_TABLE --region $REGION 2>/dev/null >/dev/null; then
    echo -e "${YELLOW}EXISTS${NC}"
else
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}WOULD CREATE${NC}"
    else
        aws --profile $PROFILE dynamodb create-table \
            --table-name $TRAINING_TABLE \
            --attribute-definitions \
                AttributeName=log_id,AttributeType=S \
            --key-schema \
                AttributeName=log_id,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region $REGION
        echo -e "${GREEN}CREATED${NC}"

        # Wait for table to be active
        echo -n "  Waiting for table to be active... "
        aws --profile $PROFILE dynamodb wait table-exists --table-name $TRAINING_TABLE --region $REGION
        echo -e "${GREEN}READY${NC}"
    fi
fi

echo ""

# -----------------------------------------------------------------------------
# Step 3: Update IAM Permissions
# -----------------------------------------------------------------------------
echo -e "${GREEN}Step 3: Updating IAM Permissions${NC}"
echo "----------------------------------------"

# Create updated policy document
POLICY_DOC=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*"
        },
        {
            "Sid": "LambdaInvoke",
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": "arn:aws:lambda:us-east-2:${ACCOUNT_ID}:function:pf-syn-*-prod"
        },
        {
            "Sid": "SecretsAccess",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:us-east-2:${ACCOUNT_ID}:secret:projectforce/*"
        },
        {
            "Sid": "S3ConfigAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::pf-syn-config-prod",
                "arn:aws:s3:::pf-syn-config-prod/*"
            ]
        },
        {
            "Sid": "S3DspyModelsAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${DSPY_BUCKET}",
                "arn:aws:s3:::${DSPY_BUCKET}/*"
            ]
        },
        {
            "Sid": "S3TrainingLogsAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${TRAINING_BUCKET}",
                "arn:aws:s3:::${TRAINING_BUCKET}/*"
            ]
        }
    ]
}
EOF
)

echo -n "  Updating OrchestratorPermissions policy... "
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}WOULD UPDATE${NC}"
    echo "  Policy additions:"
    echo "    - S3DspyModelsAccess: s3:GetObject, s3:ListBucket on $DSPY_BUCKET"
    echo "    - S3TrainingLogsAccess: s3:GetObject, s3:PutObject, s3:ListBucket on $TRAINING_BUCKET"
else
    aws --profile $PROFILE iam put-role-policy \
        --role-name $ORCHESTRATOR_ROLE \
        --policy-name OrchestratorPermissions \
        --policy-document "$POLICY_DOC"
    echo -e "${GREEN}UPDATED${NC}"
fi

echo ""

# -----------------------------------------------------------------------------
# Step 4: Copy DSPy Models from DEV to PROD
# -----------------------------------------------------------------------------
echo -e "${GREEN}Step 4: Copying DSPy Models${NC}"
echo "----------------------------------------"

echo "  Source: s3://$DEV_DSPY_BUCKET/optimized/"
echo "  Target: s3://$DSPY_BUCKET/optimized/"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "  Models to copy:"
    aws --profile $PROFILE s3 ls s3://$DEV_DSPY_BUCKET/optimized/ 2>/dev/null | while read -r line; do
        echo "    - $(echo $line | awk '{print $4}')"
    done
    echo -e "  ${YELLOW}WOULD COPY${NC}"
else
    aws --profile $PROFILE s3 sync \
        s3://$DEV_DSPY_BUCKET/optimized/ \
        s3://$DSPY_BUCKET/optimized/ \
        --region $REGION
    echo -e "  ${GREEN}COPIED${NC}"
fi

echo ""

# -----------------------------------------------------------------------------
# Step 5: Update Lambda Environment Variables
# -----------------------------------------------------------------------------
echo -e "${GREEN}Step 5: Updating Lambda Environment Variables${NC}"
echo "----------------------------------------"

# Get current environment variables
echo -n "  Fetching current config... "
CURRENT_ENV=$(aws --profile $PROFILE lambda get-function-configuration \
    --function-name $ORCHESTRATOR_LAMBDA \
    --region $REGION \
    --query 'Environment.Variables' \
    --output json)
echo -e "${GREEN}OK${NC}"

# Add new variables using jq
NEW_ENV=$(echo $CURRENT_ENV | python3 -c "
import sys, json
env = json.load(sys.stdin)
env['DSPY_MODEL_BUCKET'] = '$DSPY_BUCKET'
env['DSPY_MODEL_PREFIX'] = 'optimized/'
env['TRAINING_LOG_BUCKET'] = '$TRAINING_BUCKET'
env['TRAINING_LOG_TABLE'] = '$TRAINING_TABLE'
env['TRAINING_LOG_ENABLED'] = 'true'
print(json.dumps({'Variables': env}))
")

echo "  New environment variables:"
echo "    - DSPY_MODEL_BUCKET: $DSPY_BUCKET"
echo "    - DSPY_MODEL_PREFIX: optimized/"
echo "    - TRAINING_LOG_BUCKET: $TRAINING_BUCKET"
echo "    - TRAINING_LOG_TABLE: $TRAINING_TABLE"
echo "    - TRAINING_LOG_ENABLED: true"
echo ""

echo -n "  Updating $ORCHESTRATOR_LAMBDA... "
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}WOULD UPDATE${NC}"
else
    aws --profile $PROFILE lambda update-function-configuration \
        --function-name $ORCHESTRATOR_LAMBDA \
        --region $REGION \
        --environment "$NEW_ENV" \
        --query 'LastModified' \
        --output text
    echo -e "${GREEN}UPDATED${NC}"
fi

echo ""

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Resources created/updated in us-east-2:"
echo ""
echo "  S3 Buckets:"
echo "    - $DSPY_BUCKET"
echo "    - $TRAINING_BUCKET"
echo ""
echo "  DynamoDB Tables:"
echo "    - $TRAINING_TABLE"
echo ""
echo "  IAM Policies:"
echo "    - $ORCHESTRATOR_ROLE (OrchestratorPermissions)"
echo ""
echo "  Lambda Functions:"
echo "    - $ORCHESTRATOR_LAMBDA (environment updated)"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}This was a DRY RUN. No changes were made.${NC}"
    echo -e "${YELLOW}Run without --dry-run to apply changes.${NC}"
fi
