# Bedrock Agent Tests

This directory contains test scripts for validating the Bedrock multi-agent system.

## Test Scripts

### 1. `test_api_access.py`
**Purpose**: Comprehensive API access validation

Tests three scenarios:
- ✅ Direct model invocation (bedrock-runtime API)
- ⚠️ Individual agent invocation (bedrock-agent-runtime API)
- ⚠️ Supervisor agent invocation with collaborators

**Usage:**
```bash
python3 tests/test_api_access.py
```

**Expected Output:**
- PASS: Direct Model invocation
- FAIL: Agent invocations (until on-demand access enabled)

**When to use:**
- After enabling API access in AWS Console
- Troubleshooting 403 Access Denied errors
- Validating agent deployment

---

### 2. `test_agents_interactive.py`
**Purpose**: Interactive agent testing with multiple modes

Features:
- Pre-flight checks (credentials, agent status, collaborators)
- 4 predefined test scenarios
- Interactive chat mode
- Console testing instructions
- Colored terminal output

**Usage:**
```bash
python3 tests/test_agents_interactive.py
```

**Modes:**
1. **Predefined tests** - Runs 4 test scenarios automatically
2. **Interactive mode** - Chat with the agent
3. **Console instructions** - Shows how to test in AWS Console
4. **Exit**

**Sample commands in interactive mode:**
```
You: Hello! How are you?
You: I want to schedule an appointment
You: What are your working hours?
You: Add a note that I prefer mornings
```

---

### 3. `test_agent.py`
**Purpose**: Basic agent testing (legacy)

Simple test script for quick validation.

**Usage:**
```bash
python3 tests/test_agent.py
```

**Note**: This is the original test script. Use `test_agents_interactive.py` for better experience.

---

## Agent Configuration

All test scripts use these agent IDs:

### Supervisor Agent
- **Agent ID**: `5VTIWONUMO`
- **Latest Alias**: `HH2U7EZXMW` (version 6 with v4 collaborators)
- **Test Alias**: `TSTALIASID` (points to DRAFT)
- **Model**: Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)

### Collaborator Agents
| Agent | ID | v4 Alias | Version |
|-------|-----|----------|---------|
| Chitchat | `BIUW1ARHGL` | `THIPMPJCPI` | 5 |
| Scheduling | `IX24FSMTQH` | `TYJRF3CJ7F` | 4 |
| Information | `C9ANXRIO8Y` | `YVNFXEKPWO` | 4 |
| Notes | `G5BVBYEPUM` | `F9QQNLZUW8` | 4 |

---

## Troubleshooting

### Error: AccessDeniedException (403)

**Symptoms:**
```
An error occurred (accessDeniedException) when calling the InvokeAgent operation:
Access denied when calling Bedrock
```

**Causes:**
1. On-demand API access not enabled for Claude Sonnet 4.5
2. IAM role missing permissions
3. Agent not prepared
4. Model not available in region

**Solutions:**
1. Enable on-demand access in AWS Console (see `docs/ENABLE_API_ACCESS.md`)
2. Verify IAM permissions in agent roles
3. Run `python3 utils/prepare_all_agents.py`
4. Check model availability: `aws bedrock list-foundation-models --region us-east-1`

### Error: ValidationException (Model not supported)

**Symptoms:**
```
Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0 with on-demand throughput isn't supported
```

**Cause:** Agent alias pointing to old version with Claude Sonnet 4 (instead of 4.5)

**Solution:** Use latest aliases that point to correct model versions (see table above)

---

## Testing Workflow

### 1. Initial Deployment Testing
```bash
# Check agent status
python3 tests/test_agents_interactive.py
# Select option 1 (Predefined tests)
```

### 2. API Access Validation
```bash
# Test API access status
python3 tests/test_api_access.py
```

### 3. Interactive Development
```bash
# Chat with agents
python3 tests/test_agents_interactive.py
# Select option 2 (Interactive mode)
```

### 4. Console Testing (Fallback)
```bash
# Show console instructions
python3 tests/test_agents_interactive.py
# Select option 3 (Console instructions)
```

---

## Requirements

```bash
pip install boto3
```

**AWS Credentials:**
- Configured via `aws configure`
- Or environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- Or IAM role (if running on EC2/Lambda)

**Permissions Required:**
- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `bedrock-agent:InvokeAgent`
- `bedrock-agent:GetAgent`
- `bedrock-agent:ListAgentCollaborators`

---

## Related Documentation

- **API Access Setup**: `docs/ENABLE_API_ACCESS.md`
- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md`
- **AWS Support Ticket**: `docs/AWS_SUPPORT_TICKET.md` (if API access issues)

---

**Last Updated**: October 13, 2025
