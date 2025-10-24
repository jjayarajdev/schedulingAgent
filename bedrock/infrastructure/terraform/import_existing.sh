#!/bin/bash
################################################################################
# Import Existing Resources into Terraform State
################################################################################

set -e

echo "Importing existing resources into Terraform state..."
echo ""

# Import S3 bucket
echo "Importing S3 bucket..."
terraform import aws_s3_bucket.agent_schemas scheduling-agent-schemas-dev-618048437522 || echo "Already imported or doesn't exist"

# Import DynamoDB table
echo "Importing DynamoDB table..."
terraform import aws_dynamodb_table.bedrock_sessions scheduling-agent-sessions-dev || echo "Already imported or doesn't exist"

echo ""
echo "✓ Import complete"
echo ""
echo "Now comment out all agent aliases and collaborators in bedrock_agents.tf"
echo "Then run: ./prepare_agents.sh"
echo "Then uncomment aliases and run: terraform apply"
