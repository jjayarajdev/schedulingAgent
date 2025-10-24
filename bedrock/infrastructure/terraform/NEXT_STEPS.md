# Next Steps - Action Items

## Current Status ✅
- ✅ Bedrock multi-agent infrastructure deployed
- ✅ 5 agents created and PREPARED
- ✅ 5 agent aliases active
- ✅ 4 collaborator associations configured
- ✅ DynamoDB session table ready
- ✅ S3 bucket with OpenAPI schemas ready
- ✅ Lambda IAM roles created
- ✅ Lambda functions exist (not deployed yet)

## Your Next Action Items

### 🔴 Priority 1: Connect Lambda Functions (Required for Full Functionality)

#### Step 1: Deploy Lambda Functions
```bash
cd ../../scripts
./deploy_lambda_functions.sh
```

**What this does:**
- Packages 3 Lambda functions (scheduling, information, notes)
- Creates Lambda shared layer with common dependencies
- Deploys to AWS Lambda
- Outputs Lambda ARNs

**Duration:** ~5-10 minutes

#### Step 2: Add Lambda ARNs to Terraform
After Lambda deployment, you'll get ARNs like:
```
scheduling_lambda_arn: arn:aws:lambda:us-east-1:xxxxx:function:scheduling-actions
information_lambda_arn: arn:aws:lambda:us-east-1:xxxxx:function:information-actions
notes_lambda_arn: arn:aws:lambda:us-east-1:xxxxx:function:notes-actions
```

Create `terraform.tfvars` in the terraform directory:
```bash
cd ../infrastructure/terraform

cat > terraform.tfvars <<EOF
scheduling_lambda_arn  = "arn:aws:lambda:us-east-1:xxxxx:function:scheduling-actions"
information_lambda_arn = "arn:aws:lambda:us-east-1:xxxxx:function:information-actions"
notes_lambda_arn       = "arn:aws:lambda:us-east-1:xxxxx:function:notes-actions"
EOF
```

#### Step 3: Add Lambda Variables to variables.tf
Edit `variables.tf` and add:
```hcl
variable "scheduling_lambda_arn" {
  description = "ARN of scheduling Lambda function"
  type        = string
  default     = ""
}

variable "information_lambda_arn" {
  description = "ARN of information Lambda function"
  type        = string
  default     = ""
}

variable "notes_lambda_arn" {
  description = "ARN of notes Lambda function"
  type        = string
  default     = ""
}
```

#### Step 4: Uncomment Action Groups in bedrock_agents.tf
Find lines ~548-561 in `bedrock_agents.tf` and uncomment:
```hcl
resource "aws_bedrockagent_agent_action_group" "scheduling_actions" {
  agent_id              = aws_bedrockagent_agent.scheduling.agent_id
  agent_version         = "DRAFT"
  action_group_name     = "scheduling-actions"

  action_group_executor {
    lambda = var.scheduling_lambda_arn
  }

  api_schema {
    s3 {
      s3_bucket_name = aws_s3_bucket.agent_schemas.id
      s3_object_key  = aws_s3_object.scheduling_actions_schema.key
    }
  }
}
```

Repeat for information and notes action groups.

#### Step 5: Deploy Action Groups
```bash
terraform apply
./prepare_agents.sh  # Re-prepare agents after adding action groups
terraform apply
```

#### Step 6: Test Lambda Integration
```bash
cd ../../scripts
./test_lambdas.sh
```

---

### 🟡 Priority 2: Initialize Database (Optional but Recommended)

If you want realistic test data:

```bash
cd ../../scripts
./init_database.sh
```

**What this does:**
- Creates DynamoDB tables for:
  - Projects
  - Appointments
  - Availability
  - Notes
- Populates with sample data
- Configures indexes

**Duration:** ~2-3 minutes

---

### 🟡 Priority 3: Set Up Monitoring (Production Readiness)

```bash
cd ../../scripts
./setup_monitoring.sh
```

**What this creates:**
- CloudWatch Log Groups for all agents
- CloudWatch Alarms for errors
- SNS topic for alerts
- CloudWatch Dashboard for metrics

**Duration:** ~3-5 minutes

---

### 🟢 Priority 4: Run Comprehensive Tests

```bash
cd ../../tests
python3 comprehensive_test.py
```

**What this tests:**
- All 4 agent types (18 test cases)
- Multi-step workflows
- Error handling
- Session management
- Generates test report

**Expected:** 18/18 passed ✅

---

### 🟢 Priority 5: Production Hardening (Before Go-Live)

#### A. Add Guardrails
```hcl
# In bedrock_agents.tf, add to each agent:
guardrail_configuration {
  guardrail_identifier = "your-guardrail-id"
  guardrail_version    = "1"
}
```

#### B. Enable CloudWatch Logging
Already configured in IAM roles, verify logs are appearing:
```bash
aws logs describe-log-groups --log-group-name-prefix "/aws/bedrock/agents"
```

#### C. Configure Rate Limiting
Add API Gateway or Application Load Balancer with rate limiting rules.

#### D. Set Up CloudTrail
Enable for audit logging:
```bash
aws cloudtrail create-trail \
  --name bedrock-agent-audit \
  --s3-bucket-name your-audit-bucket
```

#### E. Enable Backup Automation
```bash
# DynamoDB point-in-time recovery
aws dynamodb update-continuous-backups \
  --table-name scheduling-agent-sessions-dev \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

---

### 🟢 Priority 6: Documentation Review

Review and update documentation:
- [ ] Update `README.md` with your agent IDs
- [ ] Review `DEPLOYMENT_SUMMARY.md`
- [ ] Read `PRODUCTION_IMPLEMENTATION.md` for integration examples
- [ ] Check `API_DOCUMENTATION_README.md` for API specs

---

### 🔵 Priority 7: Integration Planning

Choose your integration approach:

#### Option A: Direct Lambda Integration
```python
import boto3

client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = client.invoke_agent(
    agentId='YZOPVMTYWY',  # Your supervisor agent
    agentAliasId='NUPCJSZ1FA',  # Your supervisor alias
    sessionId=f"session-{user_id}",
    inputText="Schedule an appointment for tomorrow"
)
```

#### Option B: API Gateway + Lambda
Create REST API fronting the Bedrock agent.

#### Option C: WebSocket for Real-Time
Use AWS API Gateway WebSocket for streaming responses.

---

## Quick Command Reference

### Deploy Everything
```bash
# From bedrock/infrastructure/terraform
cd ../../scripts
./deploy_lambda_functions.sh  # Get Lambda ARNs

# Add ARNs to terraform.tfvars
cd ../infrastructure/terraform
nano terraform.tfvars  # Add Lambda ARNs

# Add variables to variables.tf
nano variables.tf  # Add Lambda variable definitions

# Uncomment action groups
nano bedrock_agents.tf  # Uncomment lines ~548-600

# Deploy action groups
terraform apply
cd ../../scripts
./prepare_agents.sh  # Re-prepare
cd ../infrastructure/terraform
terraform apply
```

### Test Everything
```bash
cd ../../tests
python3 comprehensive_test.py
```

### Monitor
```bash
# View agent logs
aws logs tail /aws/bedrock/agents/YZOPVMTYWY --follow

# View Lambda logs
aws logs tail /aws/lambda/scheduling-actions --follow

# Check DynamoDB
aws dynamodb scan --table-name scheduling-agent-sessions-dev --max-items 5
```

---

## Timeline Estimate

| Task | Duration | When |
|------|----------|------|
| Deploy Lambda functions | 5-10 min | Do now |
| Configure action groups | 10-15 min | Do now |
| Initialize database | 2-3 min | Optional |
| Set up monitoring | 3-5 min | Before prod |
| Run tests | 2-3 min | After Lambda |
| Production hardening | 30-60 min | Before go-live |

**Total Time to Full Functionality:** ~30-45 minutes

---

## Decision Points

### Do You Need Action Groups?
- ✅ **YES** if you want agents to call Lambda functions and return real data
- ❌ **NO** if you only want conversational responses (Chitchat agent works without Lambda)

### Do You Need Sample Data?
- ✅ **YES** if testing/demo
- ❌ **NO** if you have your own data source

### Are You Going to Production?
- ✅ **YES** → Complete Priority 5 (hardening)
- ❌ **NO** → Skip Priority 5

---

## Blockers/Dependencies

### Before Deploying Lambda Functions:
- [x] AWS credentials configured
- [x] Lambda IAM roles created (done by Terraform)
- [x] DynamoDB table exists (done by Terraform)

### Before Adding Action Groups:
- [ ] Lambda functions deployed
- [ ] Lambda ARNs obtained
- [ ] Variables added to terraform.tfvars

### Before Production:
- [ ] Monitoring configured
- [ ] Guardrails set up
- [ ] Rate limiting configured
- [ ] Load testing completed
- [ ] Security review done

---

## Help & Support

### If Lambda Deployment Fails:
```bash
# Check IAM permissions
aws iam get-role --role-name scheduling-agent-scheduling-lambda-role-dev

# Check Lambda function
aws lambda get-function --function-name scheduling-actions

# View logs
aws logs tail /aws/lambda/scheduling-actions --follow
```

### If Action Groups Fail:
```bash
# Verify agent is PREPARED
aws bedrock-agent get-agent --agent-id VIPX4UDKMV --query 'agent.agentStatus'

# Re-prepare agent
aws bedrock-agent prepare-agent --agent-id VIPX4UDKMV

# Check action group
aws bedrock-agent list-agent-action-groups \
  --agent-id VIPX4UDKMV \
  --agent-version DRAFT
```

### If Tests Fail:
```bash
# Enable debug mode
export DEBUG=true
python3 comprehensive_test.py

# Check agent logs
aws logs tail /aws/bedrock/agents/YZOPVMTYWY --follow

# Verify Lambda response
aws lambda invoke \
  --function-name scheduling-actions \
  --payload '{"action":"get_available_projects"}' \
  output.json
```

---

## Success Criteria

You're done when:
- [ ] All Lambda functions deployed successfully
- [ ] All action groups configured and showing in AWS Console
- [ ] All agents re-prepared after adding action groups
- [ ] All 18 tests passing
- [ ] Agents returning real data (not just conversational responses)
- [ ] Monitoring dashboard shows metrics
- [ ] Documentation updated with your agent/Lambda ARNs

---

## Next Document to Read

After completing Priority 1 & 2, read:
- `../../docs/PRODUCTION_IMPLEMENTATION.md` - Integration patterns
- `../../docs/API_DOCUMENTATION_README.md` - API specifications

---

**Current Status:** Infrastructure deployed, Lambda integration pending
**Next Action:** Deploy Lambda functions and configure action groups
**Estimated Time to Complete:** ~30-45 minutes
