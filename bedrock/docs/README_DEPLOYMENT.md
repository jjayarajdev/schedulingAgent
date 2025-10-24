# Bedrock Multi-Agent System - Deployment

## 🚀 One-Command Deployment

```bash
./DEPLOY.sh dev us-east-1
```

That's it! The script handles everything automatically.

## What Gets Deployed

✅ **IAM Roles** - Lambda execution roles with proper policies
✅ **DynamoDB** - Session storage with TTL
✅ **S3 Buckets** - OpenAPI schemas storage
✅ **Lambda Functions** - 3 functions with automatic retries
✅ **Bedrock Agents** - 5 agents (1 supervisor + 4 specialists)
✅ **Agent Aliases** - v1 aliases for all agents
✅ **Collaborators** - Multi-agent routing configured
✅ **Action Groups** - Lambda integration complete

## Prerequisites

```bash
# 1. Install AWS CLI
brew install awscli  # macOS
# or: pip install awscli

# 2. Configure AWS credentials
aws configure

# 3. Install Terraform
brew install terraform  # macOS

# 4. Verify Python 3.11+
python3 --version
```

## Production Deployment

```bash
# 1. Deploy infrastructure
./DEPLOY.sh prod us-east-1

# 2. Run tests
cd tests && ./run_tests.sh

# 3. Monitor logs
tail -f deployment_prod_*.log
```

## Troubleshooting

### Lambda Stuck in Pending?

This is an AWS service issue. Solutions:

1. **Wait**: AWS usually resolves in 10-15 minutes
2. **Retry**: Run `./DEPLOY.sh` again (it's safe, idempotent)
3. **Different region**: `./DEPLOY.sh dev us-west-2`

### Need to Start Over?

```bash
# Remove deployment state
rm .deployment_state_dev.json

# Rollback everything
./ROLLBACK.sh dev us-east-1

# Deploy again
./DEPLOY.sh dev us-east-1
```

## Features

| Feature | Description |
|---------|-------------|
| **Idempotent** | Run multiple times safely |
| **Resumable** | Continues from failures |
| **Validated** | Checks each step |
| **Logged** | Complete audit trail |
| **Retries** | Handles AWS service issues |
| **Multi-env** | Dev, staging, prod |

## What If It Fails?

The script has built-in intelligence:

1. **Saves progress** - Won't repeat completed steps
2. **Auto-retries** - Up to 10 attempts for AWS API calls
3. **Detailed logs** - Check `deployment_*.log` for errors
4. **State tracking** - Resume from exactly where it failed

Just run it again: `./DEPLOY.sh dev us-east-1`

## Directory Structure

```
bedrock/
├── DEPLOY.sh              # 👈 Main deployment script
├── ROLLBACK.sh            # Cleanup script
├── DEPLOYMENT_GUIDE.md    # Detailed guide
├── infrastructure/
│   └── terraform/         # Infrastructure as code
├── lambda/                # Lambda function code
│   ├── scheduling-actions/
│   ├── information-actions/
│   └── notes-actions/
├── frontend/              # UI application
└── tests/                 # Test suites
```

## After Deployment

```bash
# 1. Get your supervisor agent ID
cat agent_config.json

# 2. Test it
aws bedrock-agent-runtime invoke-agent \
  --agent-id $(jq -r .supervisor_id agent_config.json) \
  --agent-alias-id $(jq -r .supervisor_alias agent_config.json) \
  --session-id test-$(date +%s) \
  --input-text "Show me my projects" \
  --region us-east-1 \
  output.txt

# 3. Start UI
cd frontend && ./start.sh

# 4. Open browser
open http://localhost:3000
```

## Cost Estimate

| Environment | Monthly Cost |
|-------------|-------------|
| Development | $10-20 |
| Staging | $30-50 |
| Production | $100-300 |

*Based on moderate usage*

## Support

- 📖 **Full Guide**: See `DEPLOYMENT_GUIDE.md`
- 🐛 **Issues**: Check deployment logs first
- 💬 **Questions**: Review troubleshooting section

## Quick Commands

```bash
# Deploy
./DEPLOY.sh dev us-east-1

# Rollback
./ROLLBACK.sh dev us-east-1

# Check status
cat .deployment_state_dev.json

# View logs
tail -f deployment_*.log

# Test
cd tests && ./run_tests.sh
```

## Success Criteria

After deployment, you should see:

✅ All Lambda functions in "Active" state
✅ All Bedrock agents "PREPARED"
✅ Collaborators associated with supervisor
✅ Action groups "ENABLED"
✅ `agent_config.json` created

## Next Steps

1. **Read** `DEPLOYMENT_GUIDE.md` for detailed documentation
2. **Test** your deployment with the test suite
3. **Monitor** AWS CloudWatch for logs
4. **Scale** to production when ready
