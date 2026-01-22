#!/bin/bash
# =============================================================================
# Lambda Version & Deploy Script
# Creates a version snapshot before deploying, enabling easy rollback
# =============================================================================

set -e

# Configuration
AWS_PROFILE="${AWS_PROFILE:-pf-aws}"
REGION="${AWS_REGION:-us-east-1}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 <action> <function-name> [zip-file]"
    echo ""
    echo "Actions:"
    echo "  snapshot    - Publish current code as a new version (backup before deploy)"
    echo "  deploy      - Deploy new code and publish as version"
    echo "  rollback    - Rollback to a previous version"
    echo "  list        - List all versions of a function"
    echo "  backup-db   - Create DynamoDB backup"
    echo ""
    echo "Examples:"
    echo "  $0 snapshot pf-syn-orchestrator-prod"
    echo "  $0 deploy pf-syn-orchestrator-prod /tmp/orchestrator.zip"
    echo "  $0 rollback pf-syn-orchestrator-prod 3"
    echo "  $0 list pf-syn-orchestrator-prod"
    echo "  $0 backup-db pf-syn-workflow-states-dev"
    exit 1
}

# Publish current function as a version
snapshot() {
    local FUNC_NAME=$1
    local DESCRIPTION="${2:-Pre-deploy snapshot $TIMESTAMP}"

    echo -e "${YELLOW}Creating version snapshot for: $FUNC_NAME${NC}"

    VERSION=$(AWS_PROFILE=$AWS_PROFILE aws lambda publish-version \
        --function-name "$FUNC_NAME" \
        --description "$DESCRIPTION" \
        --region "$REGION" \
        --query 'Version' --output text)

    echo -e "${GREEN}✓ Published version $VERSION for $FUNC_NAME${NC}"
    echo "  Rollback command: $0 rollback $FUNC_NAME $VERSION"
}

# Deploy new code and publish as version
deploy() {
    local FUNC_NAME=$1
    local ZIP_FILE=$2
    local DESCRIPTION="${3:-Deploy $TIMESTAMP}"

    if [ -z "$ZIP_FILE" ]; then
        echo -e "${RED}Error: ZIP file required for deploy${NC}"
        usage
    fi

    if [ ! -f "$ZIP_FILE" ]; then
        echo -e "${RED}Error: ZIP file not found: $ZIP_FILE${NC}"
        exit 1
    fi

    # Step 1: Snapshot current version first (for rollback)
    echo -e "${YELLOW}Step 1: Creating backup snapshot...${NC}"
    snapshot "$FUNC_NAME" "Pre-deploy backup $TIMESTAMP"
    BACKUP_VERSION=$VERSION

    # Step 2: Deploy new code
    echo -e "${YELLOW}Step 2: Deploying new code...${NC}"
    AWS_PROFILE=$AWS_PROFILE aws lambda update-function-code \
        --function-name "$FUNC_NAME" \
        --zip-file "fileb://$ZIP_FILE" \
        --region "$REGION" \
        --query 'LastModified' --output text

    # Wait for update to complete
    echo "Waiting for function to be ready..."
    AWS_PROFILE=$AWS_PROFILE aws lambda wait function-updated \
        --function-name "$FUNC_NAME" \
        --region "$REGION" 2>/dev/null || sleep 5

    # Step 3: Publish new version
    echo -e "${YELLOW}Step 3: Publishing new version...${NC}"
    NEW_VERSION=$(AWS_PROFILE=$AWS_PROFILE aws lambda publish-version \
        --function-name "$FUNC_NAME" \
        --description "$DESCRIPTION" \
        --region "$REGION" \
        --query 'Version' --output text)

    echo -e "${GREEN}✓ Deployed and published version $NEW_VERSION${NC}"
    echo ""
    echo -e "${YELLOW}Rollback command if issues:${NC}"
    echo "  $0 rollback $FUNC_NAME $BACKUP_VERSION"
}

# Rollback to a specific version
rollback() {
    local FUNC_NAME=$1
    local TARGET_VERSION=$2

    if [ -z "$TARGET_VERSION" ]; then
        echo -e "${RED}Error: Version number required${NC}"
        echo "Use '$0 list $FUNC_NAME' to see available versions"
        exit 1
    fi

    echo -e "${YELLOW}Rolling back $FUNC_NAME to version $TARGET_VERSION...${NC}"

    # Get the code location for the target version
    CODE_URL=$(AWS_PROFILE=$AWS_PROFILE aws lambda get-function \
        --function-name "$FUNC_NAME" \
        --qualifier "$TARGET_VERSION" \
        --region "$REGION" \
        --query 'Code.Location' --output text)

    # Download the version's code
    TEMP_ZIP="/tmp/${FUNC_NAME}-v${TARGET_VERSION}.zip"
    curl -s -o "$TEMP_ZIP" "$CODE_URL"

    # Update function with the old code
    AWS_PROFILE=$AWS_PROFILE aws lambda update-function-code \
        --function-name "$FUNC_NAME" \
        --zip-file "fileb://$TEMP_ZIP" \
        --region "$REGION" \
        --query 'LastModified' --output text

    rm -f "$TEMP_ZIP"

    echo -e "${GREEN}✓ Rolled back $FUNC_NAME to version $TARGET_VERSION${NC}"
}

# List all versions
list_versions() {
    local FUNC_NAME=$1

    echo -e "${YELLOW}Versions for $FUNC_NAME:${NC}"
    echo ""
    AWS_PROFILE=$AWS_PROFILE aws lambda list-versions-by-function \
        --function-name "$FUNC_NAME" \
        --region "$REGION" \
        --query 'Versions[*].[Version,Description,LastModified]' \
        --output table
}

# Create DynamoDB backup
backup_db() {
    local TABLE_NAME=$1
    local BACKUP_NAME="${TABLE_NAME}-backup-${TIMESTAMP}"

    echo -e "${YELLOW}Creating backup for DynamoDB table: $TABLE_NAME${NC}"

    BACKUP_ARN=$(AWS_PROFILE=$AWS_PROFILE aws dynamodb create-backup \
        --table-name "$TABLE_NAME" \
        --backup-name "$BACKUP_NAME" \
        --region "$REGION" \
        --query 'BackupDetails.BackupArn' --output text)

    echo -e "${GREEN}✓ Backup created: $BACKUP_NAME${NC}"
    echo "  Backup ARN: $BACKUP_ARN"
    echo ""
    echo "To restore (creates new table):"
    echo "  AWS_PROFILE=$AWS_PROFILE aws dynamodb restore-table-from-backup \\"
    echo "    --target-table-name ${TABLE_NAME}-restored \\"
    echo "    --backup-arn $BACKUP_ARN \\"
    echo "    --region $REGION"
}

# Main
ACTION=$1
FUNC_NAME=$2

case $ACTION in
    snapshot)
        [ -z "$FUNC_NAME" ] && usage
        snapshot "$FUNC_NAME" "$3"
        ;;
    deploy)
        [ -z "$FUNC_NAME" ] && usage
        deploy "$FUNC_NAME" "$3" "$4"
        ;;
    rollback)
        [ -z "$FUNC_NAME" ] && usage
        rollback "$FUNC_NAME" "$3"
        ;;
    list)
        [ -z "$FUNC_NAME" ] && usage
        list_versions "$FUNC_NAME"
        ;;
    backup-db)
        [ -z "$FUNC_NAME" ] && usage
        backup_db "$FUNC_NAME"
        ;;
    *)
        usage
        ;;
esac
