#!/bin/bash
# Verification script for AWS Bedrock Multi-Agent Deployment

echo "=========================================="
echo "AWS Bedrock Multi-Agent Deployment Check"
echo "=========================================="
echo ""

echo "✓ Checking Supervisor Agent..."
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1 | jq -r '"Agent: \(.agent.agentName) | Status: \(.agent.agentStatus) | Model: \(.agent.foundationModel)"'
echo ""

echo "✓ Checking Collaborator Associations..."
aws bedrock-agent list-agent-collaborators --agent-id 5VTIWONUMO --agent-version DRAFT --region us-east-1 | jq -r '.agentCollaboratorSummaries | length as $count | "Found \($count) collaborators associated with supervisor"'
aws bedrock-agent list-agent-collaborators --agent-id 5VTIWONUMO --agent-version DRAFT --region us-east-1 | jq -r '.agentCollaboratorSummaries[] | "  - \(.collaboratorName)"'
echo ""

echo "✓ Checking All Agent Statuses..."
for agent_id in 5VTIWONUMO IX24FSMTQH C9ANXRIO8Y G5BVBYEPUM BIUW1ARHGL; do
  aws bedrock-agent get-agent --agent-id $agent_id --region us-east-1 | jq -r '"  \(.agent.agentName): \(.agent.agentStatus)"'
done
echo ""

echo "✓ Checking S3 Bucket..."
aws s3 ls s3://scheduling-agent-schemas-dev-618048437522/ --region us-east-1 | wc -l | xargs -I {} echo "  Found {} OpenAPI schema files"
echo ""

echo "✓ Checking Model Access..."
aws bedrock get-inference-profile --inference-profile-identifier us.anthropic.claude-sonnet-4-5-20250929-v1:0 --region us-east-1 | jq -r '"  Profile: \(.inferenceProfileName) | Status: \(.status)"'
echo ""

echo "=========================================="
echo "✅ Deployment Verification Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Test the agents in AWS Console: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents"
echo "2. Navigate to 'scheduling-agent-supervisor' and click the 'Test' button"
echo "3. Try: 'Hello!' (should route to chitchat agent)"
echo "4. Try: 'I want to schedule an appointment' (should route to scheduling agent)"
echo ""
