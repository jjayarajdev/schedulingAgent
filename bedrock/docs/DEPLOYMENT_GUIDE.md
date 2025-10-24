# Production Deployment Guide

## Quick Start

```bash
# Deploy to development
./DEPLOY.sh dev us-east-1

# Deploy to production
./DEPLOY.sh prod us-east-1
```

## Prerequisites

Before running the deployment script, ensure you have:

1. **AWS CLI** configured with appropriate credentials
   ```bash
   aws configure
   # Verify: aws sts get-caller-identity
   ```

2. **Terraform** installed (v1.0+)
   ```bash
   terraform version
   ```

3. **Python 3.11+** installed
   ```bash
   python3 --version
   ```

4. **Required IAM Permissions:**
   - IAM: Create roles, attach policies
   - Lambda: Create functions, manage permissions
   - Bedrock: Create agents, manage aliases
   - DynamoDB: Create tables
   - S3: Create buckets
   - CloudWatch Logs: Create log groups

## Deployment Script

The master deployment script (`DEPLOY.sh`) is **idempotent** - you can run it multiple times safely.

### Features

- ✅ **Automatic Retries** - Handles AWS service issues
- ✅ **State Management** - Resumes from failures
- ✅ **Validation** - Checks each step
- ✅ **Detailed Logging** - Complete audit trail
- ✅ **Rollback Support** - Can undo changes
- ✅ **Multi-Environment** - Dev, staging, prod

### Usage

```bash
./DEPLOY.sh [environment] [region] [--skip-terraform]
```

**Parameters:**
- `environment`: `dev`, `staging`, or `prod` (default: `dev`)
- `region`: AWS region (default: `us-east-1`)
- `--skip-terraform`: Skip Terraform steps (optional)

**Examples:**

```bash
# Development deployment
./DEPLOY.sh dev us-east-1

# Production deployment
./DEPLOY.sh prod us-east-1

# Skip Terraform (if already deployed)
./DEPLOY.sh dev us-east-1 --skip-terraform

# Different region
./DEPLOY.sh dev us-west-2
```

### Deployment Steps

The script performs these steps in order:

1. **Prerequisites Check**
   - Validates AWS CLI, Terraform, Python
   - Checks AWS credentials
   - Verifies required tools

2. **IAM Roles & Policies**
   - Creates Lambda execution roles
   - Attaches required policies
   - Waits for IAM propagation

3. **Terraform Infrastructure**
   - Initializes Terraform
   - Imports existing resources
   - Creates DynamoDB, S3, IAM resources

4. **Lambda Functions**
   - Packages Lambda code
   - Creates/updates functions
   - Adds Bedrock permissions
   - Validates function state

5. **Bedrock Agents**
   - Creates 5 agents (Supervisor + 4 specialists)
   - Prepares agents
   - Validates status

6. **Aliases & Collaborators**
   - Creates agent aliases
   - Associates collaborators
   - Configures routing

7. **Action Groups**
   - Connects Lambda to agents
   - Configures OpenAPI schemas
   - Validates connections

8. **Validation & Output**
   - Tests all components
   - Generates configuration
   - Displays summary

### Monitoring Deployment

The script creates a detailed log file:

```bash
# View real-time logs
tail -f deployment_dev_*.log

# Search for errors
grep "ERROR\|FAILED" deployment_dev_*.log

# Check deployment state
cat .deployment_state_dev.json
```

### Resume from Failure

The deployment script tracks completed steps in `.deployment_state_*.json`.

If deployment fails, simply run the script again - it will skip completed steps and resume from the failure point.

**To start fresh:**

```bash
# Remove state file
rm .deployment_state_dev.json

# Run deployment again
./DEPLOY.sh dev us-east-1
```

## Rollback

To rollback a deployment:

```bash
./ROLLBACK.sh dev us-east-1
```

This will:
- Delete all Lambda functions
- Remove Bedrock agents
- Clean up IAM roles
- Remove DynamoDB tables
- Delete S3 buckets

**WARNING:** This is destructive. Make sure you have backups!

## Troubleshooting

### Lambda Functions Stuck in "Pending"

**Symptom:** Lambda stays in Pending state for >5 minutes

**Cause:** AWS Lambda service issue (common in us-east-1 during high load)

**Solution:**

1. Check AWS Service Health: https://health.aws.amazon.com
2. Wait 10-15 minutes and rerun script
3. Or deploy to different region temporarily:
   ```bash
   ./DEPLOY.sh dev us-west-2
   ```

### IAM Role Permission Errors

**Symptom:** "Access Denied" or "Unauthorized" errors

**Solution:**

1. Verify AWS credentials:
   ```bash
   aws sts get-caller-identity
   ```

2. Check IAM permissions:
   ```bash
   aws iam get-user
   ```

3. Ensure you have required permissions (see Prerequisites)

### Terraform State Lock

**Symptom:** "Error acquiring the state lock"

**Solution:**

```bash
cd infrastructure/terraform
terraform force-unlock <LOCK_ID>
```

### Bedrock Agent Not Preparing

**Symptom:** Agent stuck in "NOT_PREPARED" state

**Solution:**

1. Check agent has all required components:
   - IAM role
   - Foundation model access
   - For collaborators: parent agent must be prepared first

2. Manually prepare:
   ```bash
   aws bedrock-agent prepare-agent \
     --agent-id <AGENT_ID> \
     --region us-east-1
   ```

## Multi-Environment Setup

### Development

```bash
./DEPLOY.sh dev us-east-1
```

- Uses mock data
- Lower costs
- Faster iteration

### Staging

```bash
./DEPLOY.sh staging us-east-1
```

- Uses real API (test environment)
- Production-like setup
- Testing before prod

### Production

```bash
./DEPLOY.sh prod us-east-1
```

- Uses real API (production)
- Full monitoring
- High availability setup

## Cost Optimization

### Development Environment

- On-demand Lambda
- On-demand DynamoDB
- No reserved capacity
- **Estimated cost:** $10-20/month

### Production Environment

- Provisioned concurrency for Lambda
- DynamoDB auto-scaling
- CloudWatch detailed monitoring
- **Estimated cost:** $100-300/month

## CI/CD Integration

### GitHub Actions

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Deploy
        run: |
          cd bedrock
          ./DEPLOY.sh prod us-east-1
```

## Post-Deployment

After deployment completes:

1. **Test the system:**
   ```bash
   cd tests
   ./run_tests.sh
   ```

2. **Start the UI:**
   ```bash
   cd frontend
   ./start.sh
   ```

3. **Test via CLI:**
   ```bash
   aws bedrock-agent-runtime invoke-agent \
     --agent-id <SUPERVISOR_ID> \
     --agent-alias-id <ALIAS_ID> \
     --session-id test-$(date +%s) \
     --input-text "Show me my projects" \
     --region us-east-1 \
     output.txt

   cat output.txt
   ```

4. **Monitor:**
   - CloudWatch Logs: Lambda execution logs
   - CloudWatch Metrics: Invocation counts, errors
   - AWS Cost Explorer: Daily costs

## Support

For issues or questions:

1. Check deployment log file
2. Review troubleshooting section
3. Check AWS Service Health
4. Open GitHub issue with logs

## Security Best Practices

1. **Credentials:** Never commit AWS credentials
2. **IAM Roles:** Use least-privilege principle
3. **Secrets:** Store API keys in Secrets Manager
4. **Encryption:** Enable at rest and in transit
5. **Audit:** Enable CloudTrail logging
6. **MFA:** Require for production deployments
