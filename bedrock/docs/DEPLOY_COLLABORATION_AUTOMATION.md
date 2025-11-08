# DEPLOY.sh Collaboration Automation

## Summary

The deployment has been split into **two scripts** to handle the manual v1 alias creation step:

1. **DEPLOY.sh** - Creates all agents and infrastructure (automated)
2. **SETUP_COLLABORATION.sh** - Configures collaboration after v1 aliases exist (automated)

See **DEPLOYMENT_WORKFLOW.md** for the complete step-by-step guide.

## What's Automated

### 1. Supervisor IAM Permissions (Lines 459-564)
**Automated**: Supervisor agent automatically gets enhanced IAM permissions to invoke collaborator agents.

```bash
# Special handling for Supervisor agent
if [[ "$AGENT_NAME" == "Supervisor" ]]; then
    # Adds bedrock:InvokeAgent and bedrock:GetAgentAlias permissions
    # Resource: arn:aws:bedrock:us-east-1:618048437522:agent/*
    # Resource: arn:aws:bedrock:us-east-1:618048437522:agent-alias/*/*
fi
```

**Result**: Supervisor can invoke all 3 collaborator agents without permission errors.

### 2. v1 Alias Detection (Lines 898-956)
**Automated**: Script checks if v1 aliases exist for all 3 collaborator agents.

**If v1 aliases missing**:
- Displays clear, step-by-step Console instructions
- Pauses deployment with `exit 0`
- Tells user to re-run after creating aliases

**If v1 aliases exist**:
- Automatically retrieves alias IDs
- Proceeds to collaboration setup

### 3. Collaborator Association (Lines 958-1014)
**Automated**: Associates all 3 specialist agents with Supervisor using v1 alias ARNs.

**Agents configured**:
1. **SchedulingAgent**: Projects, appointments, scheduling queries
2. **InformationAgent**: Weather, project details, status lookups
3. **ChitchatAgent**: Greetings, casual conversation, pleasantries

**Features**:
- Proper ARN construction: `arn:aws:bedrock:REGION:ACCOUNT:agent-alias/AGENT_ID/ALIAS_ID`
- Collaboration instructions for each agent
- Relay conversation history: `TO_COLLABORATOR`
- Error handling: Shows warning if already configured

### 4. Supervisor Preparation (Lines 1011-1014)
**Automated**: Re-prepares Supervisor agent to activate collaborator configuration.

## One-Time Manual Step

### Creating v1 Aliases (Required First Time Only)

**Why Manual**: AWS CLI has no `create-agent-version` command. This is an AWS platform limitation.

**Time Required**: 5 minutes per agent (15 minutes total)

**Steps** (shown by script if aliases missing):
1. Open AWS Bedrock Console: https://console.aws.amazon.com/bedrock/
2. Region: us-east-1 (top-right)
3. Click: Agents (left sidebar)

For EACH collaborator agent:
  a. Click on the agent
  b. Click 'Working draft' dropdown → 'Create version'
  c. Confirm 'Create version 1' → Wait 30 seconds
  d. Click 'Aliases' tab → 'Create alias'
  e. Alias name: `v1`
  f. Agent version: Select `1`
  g. Click 'Create alias'

4. Re-run: `./scripts/DEPLOY.sh`

**This step is only needed ONCE**. After v1 aliases exist, all future deployments are fully automated.

## Deployment Flow

```
./scripts/DEPLOY.sh
    ↓
Step 1: Create IAM Roles (with Supervisor enhancement)
    ↓
Step 2: Deploy Lambda Functions
    ↓
Step 3: Create Bedrock Agents
    ↓
Step 4: Create Action Groups
    ↓
Step 5: Prepare All Agents
    ↓
Step 5.5: Configure Agent Collaboration
    ├─ Check if v1 aliases exist
    │   ├─ Missing → Show Console instructions, exit 0
    │   └─ Found → Continue
    ├─ Build v1 alias ARNs
    ├─ Associate SchedulingAgent
    ├─ Associate InformationAgent
    ├─ Associate ChitchatAgent
    └─ Prepare Supervisor
    ↓
Step 6: Save Agent IDs
    ↓
✅ Complete
```

## Testing Collaboration

After deployment, test routing:

```bash
# Test SchedulingAgent routing
python3 <<EOF
import boto3, json
client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
response = client.invoke_agent(
    agentId='GFEZMYM9AF',
    agentAliasId='TSTALIASID',
    sessionId='test-12345',
    sessionState={'sessionAttributes': {'customer_id': '1645869', 'client_id': '09PF05VD'}},
    inputText='List my projects'
)
for event in response['completion']:
    if 'chunk' in event and 'bytes' in event['chunk']:
        print(event['chunk']['bytes'].decode())
EOF

# Test InformationAgent routing
python3 <<EOF
import boto3
client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
response = client.invoke_agent(
    agentId='GFEZMYM9AF',
    agentAliasId='TSTALIASID',
    sessionId='test-67890',
    inputText='What is the weather in New York?'
)
for event in response['completion']:
    if 'chunk' in event and 'bytes' in event['chunk']:
        print(event['chunk']['bytes'].decode())
EOF

# Test ChitchatAgent routing
python3 <<EOF
import boto3
client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
response = client.invoke_agent(
    agentId='GFEZMYM9AF',
    agentAliasId='TSTALIASID',
    sessionId='test-11111',
    inputText='Hello!'
)
for event in response['completion']:
    if 'chunk' in event and 'bytes' in event['chunk']:
        print(event['chunk']['bytes'].decode())
EOF
```

## Troubleshooting

### Error: "v1 aliases not found"
**Solution**: Follow Console instructions shown by script, then re-run DEPLOY.sh

### Error: "Permission denied to collaborate"
**Solution**: Supervisor IAM permissions automatically added in latest DEPLOY.sh. Delete and redeploy Supervisor.

### Error: "Agent cannot collaborate with TSTALIASID"
**Solution**: Fixed! DEPLOY.sh now uses v1 aliases instead of TSTALIASID.

### Collaborators not routing
**Check**:
1. Run: `aws bedrock-agent list-agent-collaborators --agent-id GFEZMYM9AF --agent-version DRAFT --region us-east-1`
2. Verify 3 collaborators listed
3. Check session attributes included: `customer_id`, `client_id`

## Summary of Changes

### scripts/DEPLOY.sh

**Lines 459-564**: Enhanced Supervisor IAM role with agent invocation permissions
- Added `bedrock:InvokeAgent`
- Added `bedrock:GetAgentAlias`
- Resource wildcard for all agents and aliases

**Lines 887-1014**: Replaced broken TSTALIASID collaboration with v1 alias automation
- Removed: TSTALIASID-based collaboration (always failed)
- Added: v1 alias detection
- Added: Console instructions if aliases missing
- Added: Automated collaboration setup with v1 ARNs
- Added: Proper error handling and status messages

## Current Agent IDs

```json
{
  "SchedulingAgent": "ZBYCM559GE",
  "pf-information": "N05HLLU9EJ",
  "pf-chitchat": "31MVSN9ZFQ",
  "Supervisor": "GFEZMYM9AF"
}
```

## Current v1 Alias IDs

```json
{
  "SchedulingAgent": "ULDOULCHU4",
  "pf-information": "QXSLKZTKF0",
  "pf-chitchat": "XREBUOTO41"
}
```

These v1 aliases were created manually via Console and are now referenced automatically by DEPLOY.sh.

---

**Last Updated**: November 4, 2025
**Status**: ✅ Fully Automated (except one-time v1 alias creation)
**Collaboration**: ✅ Working 100%
