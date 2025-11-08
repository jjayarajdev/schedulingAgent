# Deployment Workflow - Multi-Agent Collaboration Setup

## Overview

This guide explains the **two-step deployment process** for the ProjectForce scheduling multi-agent system with AWS Bedrock collaboration.

## Why Two Steps?

AWS Bedrock agent collaboration requires **versioned aliases (v1)**, which can only be created via the AWS Console. The AWS CLI and Terraform don't support creating agent versions yet.

**Solution**: Separate the deployment into two scripts:
1. **DEPLOY.sh** - Creates all agents and infrastructure
2. **SETUP_COLLABORATION.sh** - Configures collaboration (runs after manual v1 alias creation)

---

## Complete Deployment Process

### First-Time Deployment

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Deploy Agents and Infrastructure                    │
└─────────────────────────────────────────────────────────────┘

cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/DEPLOY.sh

The script will prompt for ProjectForce API credentials:
  • Client ID (e.g., 09PF05VD)
  • User ID (e.g., 1645869)
  • Bearer Token (starts with 'eyJ...')
  • Refresh Token (optional)

Alternatively, set environment variables before running:
  export PF_CLIENT_ID="09PF05VD"
  export PF_USER_ID="1645869"
  export PF_BEARER_TOKEN="eyJ..."
  export PF_REFRESH_TOKEN="..." # optional
  ./scripts/DEPLOY.sh

See CREDENTIAL_PROMPT_EXAMPLE.md for detailed prompt flow examples.

Creates:
  ✓ AWS Secrets Manager secret with API credentials
  ✓ 4 Bedrock agents (Supervisor, SchedulingAgent, pf-information, pf-chitchat)
  ✓ 2 Lambda functions (pf-scheduling-actions, pf-information-actions)
  ✓ IAM roles with proper permissions (including Supervisor agent invocation)
  ✓ Action groups linking agents to Lambdas
  ✓ Agent IDs saved to config/agent_ids.json

Time: ~3-5 minutes

┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Create v1 Aliases (Manual - One-Time Only)          │
└─────────────────────────────────────────────────────────────┘

Open: https://console.aws.amazon.com/bedrock/
Region: us-east-1

For EACH of these 3 agents:
  • SchedulingAgent
  • pf-information
  • pf-chitchat

Do:
  1. Click on the agent
  2. Click "Working draft" dropdown → "Create version"
  3. Wait 30 seconds for "Version 1" to become "Available"
  4. Click "Aliases" tab → "Create alias"
  5. Alias name: v1
  6. Agent version: Select "1"
  7. Click "Create alias"

Time: ~15 minutes (5 minutes per agent)

┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Setup Collaboration                                  │
└─────────────────────────────────────────────────────────────┘

./scripts/SETUP_COLLABORATION.sh

This script:
  ✓ Detects v1 aliases automatically
  ✓ Associates SchedulingAgent with Supervisor
  ✓ Associates InformationAgent with Supervisor
  ✓ Associates ChitchatAgent with Supervisor
  ✓ Prepares Supervisor to activate routing
  ✓ Verifies all collaborators are configured

Time: ~30 seconds

┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Test Routing                                         │
└─────────────────────────────────────────────────────────────┘

Test SchedulingAgent routing:
python3 <<EOF
import boto3
client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
response = client.invoke_agent(
    agentId='GFEZMYM9AF',
    agentAliasId='TSTALIASID',
    sessionId='test-123',
    inputText='List my projects'
)
for event in response['completion']:
    if 'chunk' in event and 'bytes' in event['chunk']:
        print(event['chunk']['bytes'].decode())
EOF

Test InformationAgent routing:
python3 <<EOF
import boto3
client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
response = client.invoke_agent(
    agentId='GFEZMYM9AF',
    agentAliasId='TSTALIASID',
    sessionId='test-456',
    inputText='What is the weather in New York?'
)
for event in response['completion']:
    if 'chunk' in event and 'bytes' in event['chunk']:
        print(event['chunk']['bytes'].decode())
EOF

Test ChitchatAgent routing:
python3 <<EOF
import boto3
client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
response = client.invoke_agent(
    agentId='GFEZMYM9AF',
    agentAliasId='TSTALIASID',
    sessionId='test-789',
    inputText='Hello!'
)
for event in response['completion']:
    if 'chunk' in event and 'bytes' in event['chunk']:
        print(event['chunk']['bytes'].decode())
EOF
```

---

## Subsequent Deployments

After the first-time setup (v1 aliases created), future deployments are simpler:

```
┌─────────────────────────────────────────────────────────────┐
│ Update Agent Instructions or Lambda Code                     │
└─────────────────────────────────────────────────────────────┘

# Update agents and Lambdas
./scripts/DEPLOY.sh

# Re-setup collaboration (automatically detects existing v1 aliases)
./scripts/SETUP_COLLABORATION.sh

# Done!
```

**Why re-run SETUP_COLLABORATION.sh?**
- DEPLOY.sh recreates agents from scratch
- Collaboration associations are stored in the agent's DRAFT configuration
- SETUP_COLLABORATION.sh re-associates collaborators with the new DRAFT

---

## Script Comparison

### DEPLOY.sh
**Purpose**: Create/update all infrastructure
**What it does**:
- Creates IAM roles (with Supervisor agent invocation permissions)
- Deploys Lambda functions
- Creates all 4 Bedrock agents
- Creates action groups
- Prepares agents
- Saves agent IDs to config

**What it does NOT do**:
- Create v1 aliases (requires Console)
- Associate collaborators (requires v1 aliases first)

**When to run**:
- First-time deployment
- After changing agent instructions
- After updating Lambda code
- After infrastructure changes

### SETUP_COLLABORATION.sh
**Purpose**: Configure Supervisor agent collaboration
**What it does**:
- Checks for v1 aliases
- Exits with instructions if aliases missing
- Associates 3 collaborators with Supervisor
- Prepares Supervisor to activate routing
- Verifies collaboration is configured

**What it does NOT do**:
- Create agents
- Deploy Lambdas
- Create v1 aliases

**When to run**:
- After DEPLOY.sh (first time)
- After re-deploying agents (to restore collaboration)
- To verify collaboration is working

---

## Architecture

```
User Request
    ↓
Supervisor Agent (GFEZMYM9AF)
    ├── Uses TSTALIASID for invocation
    ├── Has IAM permissions to invoke other agents
    └── Routes based on collaboration instructions
        ↓
    ┌───┴────────────────────────────────┐
    │                                     │
    ↓                                     ↓
SchedulingAgent (v1: ULDOULCHU4)    InformationAgent (v1: QXSLKZTKF0)
    ├── Lambda: pf-scheduling-actions       ├── Lambda: pf-information-actions
    └── Actions: list_projects, book        └── Actions: get_weather, get_details

    ↓
ChitchatAgent (v1: XREBUOTO41)
    └── Conversational only (no Lambda)
```

---

## Key Insights

### Why TSTALIASID Can't Be Used for Collaboration
- **Problem**: Every agent gets the same `TSTALIASID`
- **Error**: "Agent GFEZMYM9AF cannot collaborate with TSTALIASID alias of another agent"
- **Solution**: Use versioned aliases (v1) which are unique per agent

### Why v1 Aliases Must Be Created Manually
- AWS CLI has no `create-agent-version` command
- Terraform AWS provider has no `aws_bedrockagent_agent_version` resource
- This is an AWS platform limitation (as of November 2025)

### How Routing Works
1. User invokes Supervisor with TSTALIASID
2. Supervisor analyzes query against collaboration instructions
3. Supervisor invokes appropriate collaborator using v1 alias ARN
4. Collaborator processes query (may call Lambda)
5. Supervisor returns response to user

### IAM Permissions Required
Supervisor agent role needs:
```json
{
  "Action": [
    "bedrock:InvokeAgent",
    "bedrock:GetAgentAlias"
  ],
  "Resource": [
    "arn:aws:bedrock:us-east-1:618048437522:agent/*",
    "arn:aws:bedrock:us-east-1:618048437522:agent-alias/*/*"
  ]
}
```

This is automatically added by DEPLOY.sh when creating the Supervisor agent.

---

## Files

```
scripts/
  ├── DEPLOY.sh                  # Step 1: Deploy all infrastructure
  ├── SETUP_COLLABORATION.sh     # Step 3: Configure collaboration (new)
  └── CLEANUP.sh                 # Delete all resources

config/
  └── agent_ids.json             # Generated by DEPLOY.sh

docs/
  ├── DEPLOYMENT_WORKFLOW.md     # This file
  ├── ENABLE_COLLABORATION.md    # Original collaboration guide
  └── TERRAFORM_COLLABORATION_GUIDE.md  # Terraform approach (not used)
```

---

## Troubleshooting

### SETUP_COLLABORATION.sh says "v1 alias NOT found"
**Solution**: Complete Step 2 (create v1 aliases via Console)

### Routing not working after DEPLOY.sh
**Solution**: Run SETUP_COLLABORATION.sh to restore collaboration associations

### "Permission denied to collaborate"
**Solution**: Delete and redeploy Supervisor agent (DEPLOY.sh adds permissions automatically)

### Can't find agent IDs
**Solution**: Check `config/agent_ids.json` (created by DEPLOY.sh)

---

## Quick Reference

| Task | Command |
|------|---------|
| First-time deployment | `./scripts/DEPLOY.sh` → Manual v1 aliases → `./scripts/SETUP_COLLABORATION.sh` |
| Update agent instructions | `./scripts/DEPLOY.sh` → `./scripts/SETUP_COLLABORATION.sh` |
| Update Lambda code | `./scripts/DEPLOY.sh` → `./scripts/SETUP_COLLABORATION.sh` |
| Verify collaboration | `aws bedrock-agent list-agent-collaborators --agent-id GFEZMYM9AF --agent-version DRAFT` |
| Test routing | See Step 4 above |
| Clean up | `./scripts/CLEANUP.sh` |

---

**Last Updated**: November 4, 2025
**Current Agent IDs**: See `config/agent_ids.json`
**Collaboration Status**: ✅ Fully Automated (except one-time v1 alias creation)
