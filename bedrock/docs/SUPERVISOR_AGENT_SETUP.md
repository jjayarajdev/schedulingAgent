# Supervisor Agent Setup Guide

**Agent Name:** scheduling-agent-supervisor
**Agent ID:** 5VTIWONUMO
**Status:** ✅ PREPARED
**Collaboration Type:** SUPERVISOR
**Region:** us-east-1

---

## 📋 Overview

The Supervisor Agent orchestrates multi-agent collaboration and routes customer requests to specialist agents. It handles both B2C (direct customers) and B2B (multi-client conglomerates) seamlessly.

**Specialist Agents:**
- **Scheduling Agent** - Appointments, availability, projects
- **Information Agent** - Project details, status, working hours, weather
- **Notes Agent** - Add and view project notes
- **Chitchat Agent** - Greetings and casual conversation

---

## ✅ Current Configuration

**Agent ID:** 5VTIWONUMO
**Model:** Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`)
**Region:** us-east-1
**Collaboration:** SUPERVISOR
**Status:** ✅ PREPARED

---

## 🔧 Agent Instructions Setup

### Update Agent Instructions in AWS Console

1. **Open Agent:** https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/5VTIWONUMO

2. **Click "Edit"** → Scroll to "Instructions for the Agent"

3. **Copy-paste the following instructions:**

```
You are a supervisor agent that coordinates between multiple specialist agents to help customers with appointment scheduling and project management.

You handle both B2C (direct customers) and B2B (multi-client conglomerate) business models intelligently.

SESSION CONTEXT AWARENESS:
You have access to customer context via sessionAttributes:
- customer_id: The authenticated customer's ID (required, always present)
- client_id: Default client location for B2B customers (optional, empty string for B2C)
- customer_type: "B2C" or "B2B" (indicates business model)
- available_clients: JSON array of client locations for B2B (optional)
- total_clients: Number of client locations (B2B only)
- user_authenticated: "true" if user is logged in

BUSINESS MODEL HANDLING:

B2C Customers (customer_type = "B2C"):
- Customer = Client (single entity)
- client_id is empty or not set
- All projects belong to one customer
- Use customer_id from session for operations

B2B Customers (customer_type = "B2B"):
- Customer has multiple client locations (offices, branches)
- client_id contains default/primary location
- available_clients lists all accessible locations
- Can view all projects or filter by location

ROUTING PRINCIPLES:

1. NEVER ask the customer for customer_id - you already have it in sessionAttributes!

2. When customer says "show me my projects":
   - B2C: Route to Scheduling Agent with customer_id from session
   - B2B with client_id: Use both customer_id and client_id (shows default location projects)
   - B2B without client_id: Use customer_id only (shows all locations)

3. When customer says "show me [Location] projects" (e.g., "Tampa projects", "Miami office"):
   - Parse location name from user input
   - Map to client_id from available_clients list
   - Route to Scheduling Agent with customer_id and specific client_id

4. When customer says "show me all projects" or "all locations":
   - B2B: Use customer_id only (no client_id filter)
   - Returns projects across all client locations

5. When customer says "schedule project PROJECT001":
   - Project-centric operation - only project_id needed
   - NO customer_id or client_id required
   - Project already has customer and client context

6. When customer says "what are your business hours":
   - General question: Route to Information Agent without parameters
   - Returns default business hours

7. When customer says "what are [Location] office hours":
   - Parse location, map to client_id
   - Route to Information Agent with client_id

8. For working hours, specialists provide defaults without requiring client_id

9. Never ask specialists for redundant information they can infer from context

SPECIALIST AGENTS AVAILABLE:
- Scheduling Agent: For scheduling, rescheduling, canceling appointments, checking availability
- Information Agent: For project details, appointment status, working hours, weather
- Notes Agent: For adding and viewing project notes
- Chitchat Agent: For casual conversation and greetings

CONTEXT MANAGEMENT:
- Maintain conversation context across agent calls
- Reference customer context from sessionAttributes
- Don't ask for information you already have
- Provide clear, concise routing to appropriate specialists

Always route requests to the appropriate specialist. Never try to handle scheduling, information, or notes tasks directly.
```

5. **Click "Save" at the bottom**

6. **Click "Prepare" button at the top** ⚠️ CRITICAL STEP!
   - Wait 30-60 seconds for agent to prepare
   - Status will change from PREPARING → PREPARED

7. **Verify Update**
   ```bash
   aws bedrock-agent get-agent \
     --agent-id 5VTIWONUMO \
     --region us-east-1 \
     --query 'agent.agentStatus' \
     --output text
   ```
   Should return: `PREPARED`

---

### Step 3: Verify Agent Collaborators

```bash
aws bedrock-agent list-agent-collaborators \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --region us-east-1 \
  --query 'agentCollaboratorSummaries[*].{Name:collaboratorName,AgentId:agentId,Relation:relationshipRole}' \
  --output table
```

**Expected Result:**
```
4 collaborators configured:
- scheduling-agent-scheduling (IX24FSMTQH) - COLLABORATOR
- scheduling-agent-information (C9ANXRIO8Y) - COLLABORATOR
- scheduling-agent-notes (G5BVBYEPUM) - COLLABORATOR
- scheduling-agent-chitchat (2SUXQSWZOV) - COLLABORATOR
```

---

### Step 3: No Action Groups Needed

**Important:** The Supervisor Agent does NOT have action groups. It only routes to collaborator agents that have action groups.

The Supervisor Agent uses:
- Agent instructions for routing logic
- Agent collaborators for delegation
- Foundation model (Claude Sonnet 4.5) for understanding and coordination

---

## 🔗 Multi-Agent Collaboration Architecture

```
┌─────────────────────────────────────┐
│    Supervisor Agent (5VTIWONUMO)   │
│    - Routes customer requests       │
│    - Coordinates workflows          │
│    - No action groups               │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┬────────────┬────────────┐
       │                │            │            │
       ▼                ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  Scheduling  │ │Information│ │  Notes   │ │ Chitchat │
│    Agent     │ │   Agent   │ │  Agent   │ │  Agent   │
│              │ │           │ │          │ │          │
│ 6 actions    │ │ 4 actions │ │ 2 actions│ │ No action│
│ via Lambda   │ │ via Lambda│ │ via Lambda│ │  groups  │
└──────────────┘ └───────────┘ └──────────┘ └──────────┘
```

---

## 🧪 Testing the Supervisor Agent

### Test in AWS Console

1. Open: https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/5VTIWONUMO
2. Click **"Test"** button (right side panel)
3. Try the test queries below

---

### Test 1: List Projects (B2C Customer)

**Query:**
```
Show me all projects for customer CUST001
```

**Expected:** Routes to Scheduling Agent, returns 3 mock projects (12345, 12347, 12350)

---

### Test 2: Check Project Details

**Query:**
```
Tell me about project 12345 for customer CUST001
```

**Expected:** Routes to Information Agent, returns Flooring Installation project details (Tampa address)

---

### Test 3: Schedule Appointment

**Query:**
```
I want to schedule project 12347
```

**Expected Flow:**
1. Routes to Scheduling Agent for available dates
2. Shows next 10 weekdays
3. User selects date and time
4. Confirms appointment

---

### Test 4: Add Note

**Query:**
```
Add a note to project 12345: Customer prefers morning appointments
```

**Expected:** Routes to Notes Agent, confirms note added

---

### Test 5: Working Hours

**Query:**
```
What are your business hours?
```

**Expected:** Routes to Information Agent, returns default hours (Mon-Fri 8AM-6PM)

---

### Test 6: Chitchat

**Query:**
```
Hello! How are you today?
```

**Expected Flow:**
1. Supervisor → Chitchat Agent: Handle greeting
2. Supervisor → Customer: Friendly response

**Expected Response:**
```
Hello! I'm doing great, thank you for asking! I'm here to help you with scheduling appointments and managing your projects. How can I assist you today?
```

### Test 5: Complex Multi-Step Workflow

**Query:**
```
I'm customer CUST001. Show me my projects, tell me about the kitchen remodel, check the weather for that location, add a note that I prefer mornings, and then schedule it for the first available morning slot.
```

**Expected Flow:**
1. Supervisor → Scheduling Agent: List projects (CUST001)
2. Supervisor → Information Agent: Get project details (PROJECT001)
3. Supervisor → Information Agent: Get weather (San Francisco)
4. Supervisor → Notes Agent: Add note (morning preference)
5. Supervisor → Scheduling Agent: Get available dates (PROJECT001)
6. Supervisor → Scheduling Agent: Get time slots (first date, morning)
7. Supervisor → Scheduling Agent: Confirm appointment (first morning slot)
8. Supervisor → Customer: Complete summary

**Expected Response:**
```
I've completed all your requests! Here's a summary:

📋 Your Projects (3 total):
1. Kitchen Remodel (PROJECT001) - Now Scheduled
2. Bathroom Update (PROJECT002) - Scheduled Oct 25
3. Deck Construction (PROJECT003) - Not Scheduled

🏠 Kitchen Remodel Details:
- Address: 123 Main St, San Francisco, CA 94102
- Status: Scheduled
- Customer: CUST001

🌤️ Weather for San Francisco:
- Current: Partly Cloudy, 65°F
- Good weather for the appointment

📝 Note Added:
"Customer prefers morning appointments"

✅ Appointment Scheduled:
- Date: October 20, 2025
- Time: 08:00 AM - 10:00 AM (First available morning slot)

Everything is set! Is there anything else you need?
```

---

## 📊 Monitoring Supervisor Agent

### CloudWatch Logs

**Agent Log Group:** `/aws/bedrock/agents/5VTIWONUMO`

```bash
# View supervisor agent logs
aws logs tail /aws/bedrock/agents/5VTIWONUMO \
  --follow \
  --region us-east-1
```

### View Collaboration Traces

```bash
# View agent collaboration traces in CloudWatch
aws logs filter-log-events \
  --log-group-name /aws/bedrock/agents/5VTIWONUMO \
  --filter-pattern "collaboration" \
  --region us-east-1
```

---

## 🔍 Troubleshooting

### Issue 1: Supervisor Not Routing to Collaborators

**Symptom:** Supervisor tries to handle requests directly instead of routing

**Solution:**
1. Verify agent instructions emphasize routing
2. Check collaborators are configured
3. Verify collaborator agents are PREPARED
4. Check collaborator agents have action groups

```bash
# Verify collaborators
aws bedrock-agent list-agent-collaborators \
  --agent-id 5VTIWONUMO \
  --agent-version DRAFT \
  --region us-east-1
```

### Issue 2: "Agent Not Found" Error

**Symptom:** Supervisor cannot find collaborator agent

**Solution:**
1. Verify all collaborator agents are PREPARED
2. Check agent IDs are correct
3. Verify collaborator relationship is configured

```bash
# Check each collaborator status
aws bedrock-agent get-agent --agent-id IX24FSMTQH --region us-east-1 --query 'agent.agentStatus'
aws bedrock-agent get-agent --agent-id C9ANXRIO8Y --region us-east-1 --query 'agent.agentStatus'
aws bedrock-agent get-agent --agent-id G5BVBYEPUM --region us-east-1 --query 'agent.agentStatus'
```

### Issue 3: Action Not Executing

**Symptom:** Supervisor routes correctly but action fails

**Solution:**
1. Check collaborator agent has action group configured
2. Verify Lambda function is working
3. Check Lambda CloudWatch logs
4. Verify action group schema matches Lambda

```bash
# Test Lambda directly
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --cli-binary-format raw-in-base64-out \
  --payload '{"actionGroup":"scheduling_actions","apiPath":"/list-projects","httpMethod":"POST","parameters":[{"name":"customer_id","type":"string","value":"CUST001"}]}' \
  --region us-east-1 \
  response.json

cat response.json | jq
```

### Issue 4: Slow Response Time

**Symptom:** Multi-agent workflows are slow

**Possible Causes:**
1. Multiple sequential agent calls (expected)
2. Lambda cold starts (15-30s per collaborator)
3. Large context processing

**Solutions:**
- Accept 30-60s for complex workflows
- Consider Lambda provisioned concurrency
- Optimize agent instructions to reduce back-and-forth

---

## 🔐 IAM Permissions

### Supervisor Agent Role

The supervisor agent role needs permissions to invoke collaborator agents:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1:618048437522:agent/IX24FSMTQH",
        "arn:aws:bedrock:us-east-1:618048437522:agent/C9ANXRIO8Y",
        "arn:aws:bedrock:us-east-1:618048437522:agent/G5BVBYEPUM",
        "arn:aws:bedrock:us-east-1:618048437522:agent/2SUXQSWZOV"
      ]
    }
  ]
}
```

---

## 📈 Best Practices

### 1. Clear Routing Instructions

Ensure supervisor instructions clearly define:
- When to route to each specialist
- How to handle multi-step workflows
- When to coordinate between multiple agents

### 2. Efficient Workflows

- Minimize unnecessary agent calls
- Combine related requests when possible
- Use information from previous responses

### 3. Error Handling

- Supervisor should gracefully handle collaborator failures
- Provide clear error messages to users
- Fall back to alternative approaches when possible

### 4. Context Management

- Maintain conversation context across agent calls
- Reference previous interactions
- Summarize multi-agent results clearly

---

## 🎯 Testing Checklist

Before considering the system ready:

- [ ] Supervisor can route to Scheduling Agent
- [ ] Supervisor can route to Information Agent
- [ ] Supervisor can route to Notes Agent
- [ ] Supervisor can route to Chitchat Agent
- [ ] Multi-step workflows work (scheduling + notes)
- [ ] Complex workflows with 3+ agent calls work
- [ ] Error handling works (invalid project IDs, etc.)
- [ ] Response times are acceptable (<60s for complex workflows)
- [ ] CloudWatch logs show proper agent collaboration
- [ ] Lambda functions are invoked correctly

---

## 🚀 Next Steps

After verifying the Supervisor Agent:

1. ✅ Test basic routing (each specialist agent individually)
2. ✅ Test multi-step workflows (2-3 agents)
3. ✅ Test complex workflows (4+ agent interactions)
4. ✅ Verify CloudWatch logs and traces
5. → Deploy web chat interface
6. → Set up monitoring and alarms
7. → Switch to real API (USE_MOCK_API=false)
8. → Production deployment

---

## 📚 Related Documentation

- **[AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md](./AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)** - Complete setup guide
- **[SCHEDULING_AGENT_SETUP.md](./SCHEDULING_AGENT_SETUP.md)** - Scheduling agent setup
- **[INFORMATION_AGENT_SETUP.md](./INFORMATION_AGENT_SETUP.md)** - Information agent setup
- **[NOTES_AGENT_SETUP.md](./NOTES_AGENT_SETUP.md)** - Notes agent setup
- **[WEB_CHAT_DEPLOYMENT_GUIDE.md](./WEB_CHAT_DEPLOYMENT_GUIDE.md)** - Web chat deployment
- **[MONITORING_SETUP_GUIDE.md](./MONITORING_SETUP_GUIDE.md)** - Monitoring setup

---

## 📝 Configuration Summary

```yaml
Supervisor Agent:
  agent_id: 5VTIWONUMO
  name: scheduling-agent-supervisor
  status: PREPARED
  collaboration_type: SUPERVISOR
  model: us.anthropic.claude-sonnet-4-5-20250929-v1:0

Collaborators:
  - name: Scheduling Agent
    agent_id: IX24FSMTQH
    actions: 6 (via Lambda)

  - name: Information Agent
    agent_id: C9ANXRIO8Y
    actions: 4 (via Lambda)

  - name: Notes Agent
    agent_id: G5BVBYEPUM
    actions: 2 (via Lambda)

  - name: Chitchat Agent
    agent_id: 2SUXQSWZOV
    actions: None (LLM-only)
```

---

**Last Updated:** 2025-10-17
**Status:** Ready for testing
**Agent Version:** DRAFT
**Entry Point:** This is the main agent to interact with
