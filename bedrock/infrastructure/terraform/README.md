# Bedrock Agents Terraform Configuration

This directory contains Terraform configurations for creating AWS Bedrock Agents with multi-agent collaboration.

## Architecture

```
Supervisor Agent (Router)
├── Scheduling Agent (with action groups for PF360 API)
├── Information Agent (with action groups for project/appointment info)
├── Notes Agent (with action groups for note management)
└── Chitchat Agent (conversational, no action groups)
```

## Prerequisites

1. **Terraform** >= 1.5.0
2. **AWS CLI** configured with appropriate credentials
3. **AWS Bedrock Model Access** - You must have access to Claude 3.5 Sonnet v2
   - Go to AWS Console → Bedrock → Model access
   - Request access to `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - Wait for approval (24-48 hours)

## Files

- `bedrock_agents.tf` - Main configuration for all 5 agents
- `variables.tf` - Input variables (to be created)
- `outputs.tf` - Output values (included in bedrock_agents.tf)
- `terraform.tfvars` - Variable values (to be created, not in git)

## Setup

### 1. Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

### 2. Create `terraform.tfvars`

Create a file with your environment-specific values:

```hcl
# terraform.tfvars
environment      = "dev"
aws_region       = "us-east-1"
project_name     = "scheduling-agent"
foundation_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

### 3. Validate Configuration

```bash
terraform validate
```

### 4. Plan Deployment

```bash
terraform plan
```

This will show you all resources that will be created:
- 5 Bedrock Agents (1 supervisor + 4 collaborators)
- 5 IAM roles with policies
- 1 S3 bucket for OpenAPI schemas
- 3 OpenAPI schema uploads
- 5 Agent aliases
- 4 Agent collaboration associations

### 5. Deploy Agents

```bash
terraform apply
```

Type `yes` when prompted.

**Note:** This will create the agents WITHOUT action groups. Action groups will be added after Lambda functions are deployed.

## What Gets Created

### S3 Bucket
- **Name:** `scheduling-agent-schemas-{env}-{account-id}`
- **Purpose:** Stores OpenAPI schemas for action groups
- **Contents:**
  - `scheduling_actions.json`
  - `information_actions.json`
  - `notes_actions.json`

### IAM Roles

1. **Supervisor Agent Role**
   - Permissions: Invoke Claude model, invoke collaborator agents

2. **Collaborator Agent Roles** (4 roles)
   - Scheduling Agent Role
   - Information Agent Role
   - Notes Agent Role
   - Chitchat Agent Role
   - Permissions: Invoke Claude model, read S3 schemas

### Bedrock Agents

1. **Supervisor Agent**
   - Name: `scheduling-agent-supervisor`
   - Role: Routes requests to collaborators
   - Instructions: From `agent_instructions/supervisor.txt`

2. **Scheduling Agent**
   - Name: `scheduling-agent-scheduling`
   - Role: Handles appointment scheduling
   - Instructions: From `agent_instructions/scheduling_collaborator.txt`

3. **Information Agent**
   - Name: `scheduling-agent-information`
   - Role: Provides information
   - Instructions: From `agent_instructions/information_collaborator.txt`

4. **Notes Agent**
   - Name: `scheduling-agent-notes`
   - Role: Manages appointment notes
   - Instructions: From `agent_instructions/notes_collaborator.txt`

5. **Chitchat Agent**
   - Name: `scheduling-agent-chitchat`
   - Role: Handles conversational interactions
   - Instructions: From `agent_instructions/chitchat_collaborator.txt`

### Agent Aliases

Each agent gets a `v1` alias for stable invocation.

### Collaborator Associations

The supervisor agent is associated with all 4 collaborators, enabling multi-agent collaboration.

## Outputs

After successful deployment, Terraform will output:

```
supervisor_agent_id     = "XXXXXXXXXX"
supervisor_agent_arn    = "arn:aws:bedrock:us-east-1:123456789012:agent/XXXXXXXXXX"
supervisor_alias_id     = "YYYYYYYYYY"
supervisor_alias_arn    = "arn:aws:bedrock:us-east-1:123456789012:agent-alias/XXXXXXXXXX/YYYYYYYYYY"
scheduling_agent_id     = "XXXXXXXXXX"
information_agent_id    = "XXXXXXXXXX"
notes_agent_id          = "XXXXXXXXXX"
chitchat_agent_id       = "XXXXXXXXXX"
agent_schemas_bucket    = "scheduling-agent-schemas-dev-123456789012"
```

**Save these values!** You'll need them for:
- FastAPI configuration (supervisor agent ID and alias ID)
- Adding action groups (agent IDs)

## Next Steps

After agents are created:

1. **Create Lambda Functions** for action groups
   - `scheduling_actions` Lambda
   - `information_actions` Lambda
   - `notes_actions` Lambda

2. **Add Action Groups** to agents (uncomment in `bedrock_agents.tf`)

3. **Prepare and Deploy** agents:
   ```bash
   # In AWS Console or via API
   # Prepare agents (required before first use)
   aws bedrock-agent prepare-agent --agent-id <agent-id>
   ```

4. **Test Agents** via AWS Console or API

## Testing Agents

### Via AWS Console

1. Go to AWS Console → Bedrock → Agents
2. Select `scheduling-agent-supervisor`
3. Click "Test" tab
4. Try test messages:
   - "Hello" (should route to chitchat)
   - "I want to schedule an appointment" (should route to scheduling)
   - "What's the weather?" (should route to information)

### Via AWS CLI

```bash
# Test supervisor agent
aws bedrock-agent-runtime invoke-agent \
  --agent-id <supervisor-agent-id> \
  --agent-alias-id <supervisor-alias-id> \
  --session-id test-session-123 \
  --input-text "Hello, I want to schedule an appointment"
```

## Updating Agents

### Update Agent Instructions

1. Edit instruction files in `agent_instructions/`
2. Run:
   ```bash
   terraform apply
   ```

Terraform will detect changes and update the agents.

### Update OpenAPI Schemas

1. Edit schema files in `openapi_schemas/`
2. Run:
   ```bash
   terraform apply
   ```

Terraform will upload new schemas and update references.

### Add Action Groups

Once Lambda functions are deployed:

1. Uncomment action group resources in `bedrock_agents.tf`
2. Add Lambda ARN variables
3. Run:
   ```bash
   terraform apply
   ```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning:** This will delete:
- All 5 agents
- All IAM roles
- S3 bucket and schemas
- Cannot be undone

## Troubleshooting

### Error: "Agent not found"

Wait 30-60 seconds after creation before testing. Agents need time to initialize.

### Error: "Model access denied"

You need to request Bedrock model access:
1. AWS Console → Bedrock → Model access
2. Request access to Claude 3.5 Sonnet v2
3. Wait for approval

### Error: "Invalid agent instruction"

Check that instruction files exist in `agent_instructions/` directory.

### Error: "S3 bucket already exists"

The bucket name must be globally unique. Change `project_name` in `terraform.tfvars`.

## Cost Estimate

**Free Tier / Low Usage:**
- Agent creation: Free
- S3 storage: ~$0.01/month (minimal)
- Agent invocations: Pay per use

**10,000 messages/month:**
- Model invocations: ~$135/month (Claude 3.5 Sonnet)
- AgentCore (starting Sept 2025): ~$13/month
- S3: ~$0.01/month
- **Total: ~$148/month**

## References

- [AWS Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Multi-Agent Collaboration](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html)
- [Terraform AWS Provider - Bedrock Agent](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagent_agent)
