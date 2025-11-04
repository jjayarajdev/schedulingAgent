#!/bin/bash

##############################################################################
# VALIDATE.sh - Validate 4-Agent Deployment
#
# Purpose: Comprehensive validation of all deployed resources
# Usage: ./VALIDATE.sh
##############################################################################

set -e

REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ENV="dev"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Unicode symbols
CHECK_MARK="✅"
CROSS_MARK="❌"
WARNING="⚠️"

echo ""
echo "=========================================="
echo "ProjectForce 4-Agent Deployment Validation"
echo "=========================================="
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Environment: $ENV"
echo ""

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

##############################################################################
# 1. Bedrock Agents
##############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. BEDROCK AGENTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
printf "%-25s %-20s %-15s %-10s\n" "AGENT NAME" "AGENT ID" "STATUS" "RESULT"
printf "%-25s %-20s %-15s %-10s\n" "-------------------------" "--------------------" "---------------" "----------"

for agent_name in "SchedulingAgent" "pf-information" "pf-chitchat" "Supervisor"; do
    AGENT_DATA=$(aws bedrock-agent list-agents \
        --region "$REGION" \
        --query "agentSummaries[?agentName=='$agent_name'].[agentId,agentStatus]" \
        --output text 2>/dev/null | head -1)

    if [[ -n "$AGENT_DATA" ]]; then
        AGENT_ID=$(echo "$AGENT_DATA" | awk '{print $1}')
        AGENT_STATUS=$(echo "$AGENT_DATA" | awk '{print $2}')

        if [[ "$AGENT_STATUS" == "PREPARED" ]]; then
            printf "%-25s %-20s ${GREEN}%-15s${NC} ${GREEN}%-10s${NC}\n" "$agent_name" "$AGENT_ID" "$AGENT_STATUS" "$CHECK_MARK PASS"
            ((PASS_COUNT++))
        else
            printf "%-25s %-20s ${YELLOW}%-15s${NC} ${YELLOW}%-10s${NC}\n" "$agent_name" "$AGENT_ID" "$AGENT_STATUS" "$WARNING WARN"
            ((WARN_COUNT++))
        fi
    else
        printf "%-25s %-20s ${RED}%-15s${NC} ${RED}%-10s${NC}\n" "$agent_name" "NOT FOUND" "N/A" "$CROSS_MARK FAIL"
        ((FAIL_COUNT++))
    fi
done

##############################################################################
# 2. Lambda Functions
##############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. LAMBDA FUNCTIONS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
printf "%-30s %-15s %-15s %-15s %-10s\n" "FUNCTION NAME" "STATE" "BEARER TOKEN" "USE_MOCK_API" "RESULT"
printf "%-30s %-15s %-15s %-15s %-10s\n" "------------------------------" "---------------" "---------------" "---------------" "----------"

for func_name in "pf-scheduling-actions" "pf-information-actions" "pf-query-router"; do
    FUNC_STATE=$(aws lambda get-function \
        --function-name "$func_name" \
        --region "$REGION" \
        --query 'Configuration.State' \
        --output text 2>/dev/null || echo "NOT_FOUND")

    if [[ "$FUNC_STATE" != "NOT_FOUND" ]]; then
        ENV_VARS=$(aws lambda get-function-configuration \
            --function-name "$func_name" \
            --region "$REGION" \
            --query 'Environment.Variables' \
            --output json 2>/dev/null)

        BEARER_TOKEN=$(echo "$ENV_VARS" | python3 -c "import sys, json; env=json.load(sys.stdin); print('SET' if env.get('BEARER_TOKEN') else 'NOT SET')" 2>/dev/null || echo "NOT SET")
        USE_MOCK=$(echo "$ENV_VARS" | python3 -c "import sys, json; env=json.load(sys.stdin); print(env.get('USE_MOCK_API', 'NOT SET'))" 2>/dev/null || echo "NOT SET")

        if [[ "$FUNC_STATE" == "Active" ]] && [[ "$BEARER_TOKEN" == "SET" ]]; then
            printf "%-30s ${GREEN}%-15s${NC} ${GREEN}%-15s${NC} %-15s ${GREEN}%-10s${NC}\n" "$func_name" "$FUNC_STATE" "$BEARER_TOKEN" "$USE_MOCK" "$CHECK_MARK PASS"
            ((PASS_COUNT++))
        elif [[ "$FUNC_STATE" == "Active" ]]; then
            printf "%-30s ${GREEN}%-15s${NC} ${RED}%-15s${NC} %-15s ${YELLOW}%-10s${NC}\n" "$func_name" "$FUNC_STATE" "$BEARER_TOKEN" "$USE_MOCK" "$WARNING WARN"
            ((WARN_COUNT++))
        else
            printf "%-30s ${RED}%-15s${NC} ${RED}%-15s${NC} %-15s ${RED}%-10s${NC}\n" "$func_name" "$FUNC_STATE" "$BEARER_TOKEN" "$USE_MOCK" "$CROSS_MARK FAIL"
            ((FAIL_COUNT++))
        fi
    else
        printf "%-30s ${RED}%-15s${NC} ${RED}%-15s${NC} %-15s ${RED}%-10s${NC}\n" "$func_name" "NOT FOUND" "N/A" "N/A" "$CROSS_MARK FAIL"
        ((FAIL_COUNT++))
    fi
done

##############################################################################
# 3. Action Groups
##############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. ACTION GROUPS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
printf "%-25s %-30s %-15s %-10s\n" "AGENT" "ACTION GROUP NAME" "STATE" "RESULT"
printf "%-25s %-30s %-15s %-10s\n" "-------------------------" "------------------------------" "---------------" "----------"

for agent_name in "SchedulingAgent" "pf-information"; do
    AGENT_ID=$(aws bedrock-agent list-agents \
        --region "$REGION" \
        --query "agentSummaries[?agentName=='$agent_name'].agentId" \
        --output text 2>/dev/null | head -1)

    if [[ -n "$AGENT_ID" ]]; then
        ACTION_GROUPS=$(aws bedrock-agent list-agent-action-groups \
            --agent-id "$AGENT_ID" \
            --agent-version "DRAFT" \
            --region "$REGION" \
            --query 'actionGroupSummaries[*].[actionGroupName,actionGroupState]' \
            --output text 2>/dev/null)

        if [[ -n "$ACTION_GROUPS" ]]; then
            while IFS=$'\t' read -r ag_name ag_state; do
                if [[ "$ag_state" == "ENABLED" ]]; then
                    printf "%-25s %-30s ${GREEN}%-15s${NC} ${GREEN}%-10s${NC}\n" "$agent_name" "$ag_name" "$ag_state" "$CHECK_MARK PASS"
                    ((PASS_COUNT++))
                else
                    printf "%-25s %-30s ${YELLOW}%-15s${NC} ${YELLOW}%-10s${NC}\n" "$agent_name" "$ag_name" "$ag_state" "$WARNING WARN"
                    ((WARN_COUNT++))
                fi
            done <<< "$ACTION_GROUPS"
        else
            printf "%-25s %-30s ${RED}%-15s${NC} ${RED}%-10s${NC}\n" "$agent_name" "NO ACTION GROUPS" "N/A" "$CROSS_MARK FAIL"
            ((FAIL_COUNT++))
        fi
    else
        printf "%-25s %-30s ${RED}%-15s${NC} ${RED}%-10s${NC}\n" "$agent_name" "AGENT NOT FOUND" "N/A" "$CROSS_MARK FAIL"
        ((FAIL_COUNT++))
    fi
done

##############################################################################
# 4. DynamoDB Table
##############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. DYNAMODB TABLE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
printf "%-30s %-15s %-10s\n" "TABLE NAME" "STATUS" "RESULT"
printf "%-30s %-15s %-10s\n" "------------------------------" "---------------" "----------"

TABLE_NAME="pf-sessions-dev"
TABLE_STATUS=$(aws dynamodb describe-table \
    --table-name "$TABLE_NAME" \
    --region "$REGION" \
    --query 'Table.TableStatus' \
    --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$TABLE_STATUS" == "ACTIVE" ]]; then
    printf "%-30s ${GREEN}%-15s${NC} ${GREEN}%-10s${NC}\n" "$TABLE_NAME" "$TABLE_STATUS" "$CHECK_MARK PASS"
    ((PASS_COUNT++))
elif [[ "$TABLE_STATUS" == "NOT_FOUND" ]]; then
    printf "%-30s ${RED}%-15s${NC} ${RED}%-10s${NC}\n" "$TABLE_NAME" "NOT FOUND" "$CROSS_MARK FAIL"
    ((FAIL_COUNT++))
else
    printf "%-30s ${YELLOW}%-15s${NC} ${YELLOW}%-10s${NC}\n" "$TABLE_NAME" "$TABLE_STATUS" "$WARNING WARN"
    ((WARN_COUNT++))
fi

##############################################################################
# 5. IAM Roles
##############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. IAM ROLES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
printf "%-50s %-10s\n" "ROLE NAME" "RESULT"
printf "%-50s %-10s\n" "--------------------------------------------------" "----------"

for role_name in "pf-scheduling-actions-role-dev" "pf-information-actions-role-dev" "pf-query-router-role-dev" "AmazonBedrockExecutionRoleForAgents_SchedulingAgent" "AmazonBedrockExecutionRoleForAgents_pf-information" "AmazonBedrockExecutionRoleForAgents_pf-chitchat" "AmazonBedrockExecutionRoleForAgents_Supervisor"; do
    if aws iam get-role --role-name "$role_name" &>/dev/null; then
        printf "%-50s ${GREEN}%-10s${NC}\n" "$role_name" "$CHECK_MARK PASS"
        ((PASS_COUNT++))
    else
        printf "%-50s ${RED}%-10s${NC}\n" "$role_name" "$CROSS_MARK FAIL"
        ((FAIL_COUNT++))
    fi
done

##############################################################################
# Summary
##############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "VALIDATION SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TOTAL_TESTS=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT))

printf "${GREEN}%-15s${NC} %d\n" "✅ PASSED:" "$PASS_COUNT"
printf "${YELLOW}%-15s${NC} %d\n" "⚠️  WARNINGS:" "$WARN_COUNT"
printf "${RED}%-15s${NC} %d\n" "❌ FAILED:" "$FAIL_COUNT"
printf "%-15s %d\n" "TOTAL TESTS:" "$TOTAL_TESTS"

echo ""

if [[ $FAIL_COUNT -eq 0 ]] && [[ $WARN_COUNT -eq 0 ]]; then
    echo -e "${GREEN}${CHECK_MARK} All validations passed! Deployment is healthy.${NC}"
    exit 0
elif [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "${YELLOW}${WARNING} Deployment has warnings. Review above for details.${NC}"
    exit 0
else
    echo -e "${RED}${CROSS_MARK} Deployment has failures. Review above for details.${NC}"
    exit 1
fi
