# Bedrock Agent Utilities

Utility scripts for managing and maintaining Bedrock agents.

## Scripts

### `prepare_all_agents.py`
**Purpose**: Prepare all agents and test invocation

This script:
1. Prepares all 5 agents (supervisor + 4 collaborators)
2. Waits for preparation to complete
3. Tests supervisor agent invocation
4. Shows streaming response

**Usage:**
```bash
python3 utils/prepare_all_agents.py
```

**Output:**
```
Preparing all agents...
============================================================
✓ Supervisor    (5VTIWONUMO): PREPARING
✓ Scheduling    (IX24FSMTQH): PREPARING
✓ Information   (C9ANXRIO8Y): PREPARING
✓ Notes         (G5BVBYEPUM): PREPARING
✓ Chitchat      (BIUW1ARHGL): PREPARING

Waiting 30 seconds for preparation...

Testing agent invocation...
============================================================
✅ Agent invoked!

Response:
------------------------------------------------------------
[Agent's response appears here]
------------------------------------------------------------

🎉 SUCCESS!
```

**Agent IDs:**
```python
agents = {
    'Supervisor': '5VTIWONUMO',
    'Scheduling': 'IX24FSMTQH',
    'Information': 'C9ANXRIO8Y',
    'Notes': 'G5BVBYEPUM',
    'Chitchat': 'BIUW1ARHGL'
}
```

**When to use:**
- After Terraform deployment
- After updating agent configurations
- After changing agent models
- Before running tests
- When agents show NOT_PREPARED status

**Notes:**
- Collaborator agents (SUPERVISOR_ROUTER type) cannot be prepared individually
- They are automatically prepared when the supervisor is prepared
- Preparation typically takes 20-40 seconds
- Script uses supervisor alias `PEXPJRXIML` (may need updating to use latest alias)

---

## Common Tasks

### Prepare Agents After Deployment
```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 utils/prepare_all_agents.py
```

### Check Agent Status
```bash
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1 --query 'agent.agentStatus'
```

### List All Agent Versions
```bash
aws bedrock-agent list-agent-versions --agent-id 5VTIWONUMO --region us-east-1
```

### Create New Agent Version
```python
import boto3

client = boto3.client('bedrock-agent', region_name='us-east-1')

# Prepare DRAFT first
client.prepare_agent(agentId='5VTIWONUMO')

# Wait for preparation, then create alias (automatically creates version)
response = client.create_agent_alias(
    agentId='5VTIWONUMO',
    agentAliasName='v5',
    description='Version 5 with updated configuration'
)

print(f"Created alias: {response['agentAlias']['agentAliasId']}")
```

---

## Troubleshooting

### Issue: Collaborator agents fail to prepare

**Error:**
```
ValidationException: This agent cannot be prepared. The AgentCollaboration attribute
is set to SUPERVISOR_ROUTER but no agent collaborators are added.
```

**Explanation:** This is expected behavior. Collaborator agents with `agentCollaboration: SUPERVISOR_ROUTER` cannot be prepared individually.

**Solution:** Only prepare the supervisor agent. Collaborators are prepared automatically.

### Issue: Agent preparation takes too long

**Symptoms:** Script waits 30 seconds but agent still shows PREPARING status

**Causes:**
- Large agent configuration
- Many collaborators
- AWS backend load

**Solution:**
```bash
# Check status manually
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1 --query 'agent.agentStatus'

# Wait and retry
sleep 30
python3 utils/prepare_all_agents.py
```

### Issue: Test invocation fails with 403

**Symptoms:**
```
❌ FAILED: AccessDeniedException
```

**Cause:** On-demand API access not enabled for Claude Sonnet 4.5

**Solution:** See `docs/ENABLE_API_ACCESS.md` or `docs/AWS_SUPPORT_TICKET.md`

---

## Future Utilities (To Be Added)

- `update_agent_model.py` - Update all agents to new model version
- `create_agent_versions.py` - Create new versions for all agents
- `update_aliases.py` - Update alias routing configurations
- `sync_collaborators.py` - Sync collaborator associations across versions
- `export_agent_config.py` - Export agent configurations as JSON
- `import_agent_config.py` - Import and apply agent configurations

---

## Requirements

```bash
pip install boto3
```

**AWS Credentials:** Must be configured with permissions:
- `bedrock-agent:PrepareAgent`
- `bedrock-agent:GetAgent`
- `bedrock-agent:InvokeAgent`
- `bedrock-agent:ListAgentVersions`
- `bedrock-agent:CreateAgentAlias`

---

## Related Documentation

- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md`
- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **Architecture**: `docs/ARCHITECTURE.md`

---

**Last Updated**: October 13, 2025
