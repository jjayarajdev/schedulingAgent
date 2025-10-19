# Chitchat Agent Setup Guide

**Agent Name:** scheduling-agent-chitchat
**Agent ID:** 2SUXQSWZOV
**Status:** ✅ PREPARED
**Collaboration Type:** DISABLED
**Region:** us-east-1

---

## 📋 Overview

The Chitchat Agent is a specialist agent responsible for handling casual conversation, greetings, small talk, and general customer service interactions that don't require specific actions or data access.

---

## ✅ Current Configuration

### Agent Details

```json
{
  "agentId": "2SUXQSWZOV",
  "agentName": "scheduling-agent-chitchat",
  "agentStatus": "PREPARED",
  "agentCollaboration": "DISABLED",
  "foundationModel": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
  "agentResourceRoleArn": "arn:aws:iam::618048437522:role/scheduling-agent-chitchat-agent-role-dev"
}
```

### Agent Instructions

```
You are a friendly chitchat agent that handles casual conversation and customer service.

Your responsibilities:
1) Respond to greetings and goodbyes
2) Handle small talk and casual questions
3) Provide general company information
4) Be friendly and professional

For specific tasks like scheduling, information queries, or notes, tell customers that the specialist agents will help them.

Always be warm, helpful, and maintain a positive tone.
```

---

## 🔧 Setup Steps

### Step 1: Verify Agent Status

```bash
aws bedrock-agent get-agent \
  --agent-id 2SUXQSWZOV \
  --region us-east-1 \
  --query 'agent.{Name:agentName,Status:agentStatus,Collab:agentCollaboration}' \
  --output table
```

**Expected Result:**
```
Status: PREPARED
Collab: DISABLED
```

---

### Step 2: Agent Instructions (No B2B Updates Needed)

**Note:** The Chitchat Agent handles casual conversation only and doesn't access customer data, projects, or business logic. Therefore, B2C/B2B awareness is not required for this agent.

**Current Instructions (No Changes):**
```
You are a friendly chitchat agent that handles casual conversation and customer service.

Your responsibilities:
1) Respond to greetings and goodbyes
2) Handle small talk and casual questions
3) Provide general company information
4) Be friendly and professional

For specific tasks like scheduling, information queries, or notes, tell customers that the specialist agents will help them.

Always be warm, helpful, and maintain a positive tone.
```

**Why no B2B updates?**
- Chitchat doesn't handle customer IDs, client IDs, or projects
- No data operations or business logic
- Pure conversational responses using LLM only
- Same behavior for B2C and B2B customers

---

### Step 3: No Action Groups Needed

**Important:** The Chitchat Agent does NOT have action groups or Lambda functions. It uses only the foundation model (Claude Sonnet 4.5) to generate conversational responses.

**Why no action groups?**
- Chitchat doesn't need to access external systems
- No database queries or API calls required
- Pure conversational AI using the LLM
- Faster response times (no Lambda cold starts)

---

## 🧪 Testing the Chitchat Agent

### Test in AWS Console

1. **Navigate to Agent**
   - Go to: https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
   - Click on agent: `scheduling-agent-chitchat` (2SUXQSWZOV)
   - Click **"Test"** button (right side panel)

2. **Test Queries**

**Test 1: Greeting**
```
Hello! How are you?
```
**Expected:** Friendly greeting response, offers to help

**Test 2: Small Talk**
```
How's the weather today?
```
**Expected:** Polite response redirecting to Information Agent for weather

**Test 3: Company Information**
```
What services do you offer?
```
**Expected:** Describes scheduling services (appointments, projects, notes)

**Test 4: Goodbye**
```
Thanks! Goodbye
```
**Expected:** Warm farewell message

**Test 5: Redirect to Specialist**
```
Can you schedule an appointment?
```
**Expected:** Redirects to Scheduling specialist agent

---

## 🎯 Chitchat Agent Responsibilities

### What It Handles

✅ **Greetings and Pleasantries**
- Hello, hi, how are you
- Good morning/afternoon/evening
- Nice to meet you

✅ **Small Talk**
- How's your day going?
- Thank you, you're welcome
- General conversation

✅ **Company/Service Information**
- What do you do?
- How can you help me?
- What services are available?

✅ **Farewells**
- Goodbye, bye, see you later
- Thanks for the help
- Have a nice day

✅ **General Customer Service**
- I need help
- Who should I talk to?
- How does this work?

### What It Redirects

❌ **Scheduling Tasks** → Scheduling Agent
- Schedule appointment
- Check availability
- Cancel/reschedule

❌ **Information Queries** → Information Agent
- Project details
- Appointment status
- Working hours
- Weather

❌ **Notes Management** → Notes Agent
- Add notes
- View notes
- Update preferences

---

## 📊 Monitoring

### CloudWatch Logs

**Agent Log Group:** `/aws/bedrock/agents/2SUXQSWZOV`

```bash
# View chitchat agent logs
aws logs tail /aws/bedrock/agents/2SUXQSWZOV \
  --follow \
  --region us-east-1
```

### Metrics to Monitor

```bash
# Check agent invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name AgentInvocations \
  --dimensions Name=AgentId,Value=2SUXQSWZOV \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

---

## 🔍 Troubleshooting

### Issue 1: Agent Cannot Be Prepared

**Error:** `This agent cannot be prepared. The AgentCollaboration attribute is set to SUPERVISOR_ROUTER`

**Solution:** Update agent collaboration to `DISABLED`:
```bash
aws bedrock-agent update-agent \
  --agent-id 2SUXQSWZOV \
  --agent-name scheduling-agent-chitchat \
  --foundation-model us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --agent-resource-role-arn arn:aws:iam::618048437522:role/scheduling-agent-chitchat-agent-role-dev \
  --agent-collaboration DISABLED \
  --instruction "You are a friendly chitchat agent..." \
  --region us-east-1

aws bedrock-agent prepare-agent --agent-id 2SUXQSWZOV --region us-east-1
```

### Issue 2: Agent Tries to Handle Scheduling

**Symptom:** Chitchat agent attempts to schedule appointments directly

**Solution:** Update agent instructions to emphasize redirection:
```
For scheduling tasks, always tell customers that our Scheduling specialist will help them.
Never attempt to schedule, check availability, or confirm appointments yourself.
```

### Issue 3: Responses Too Long

**Symptom:** Chitchat agent gives overly detailed responses

**Solution:** Update instructions to be more concise:
```
Keep responses brief and friendly. For detailed information, redirect to specialist agents.
```

### Issue 4: Not Routing to Supervisor

**Symptom:** When accessed through supervisor, chitchat doesn't integrate well

**Solution:**
1. Verify supervisor has chitchat agent as collaborator
2. Check supervisor instructions mention chitchat for casual conversation
3. Test routing from supervisor agent

---

## 🔐 IAM Permissions

### Agent Role Permissions

The chitchat agent role (`scheduling-agent-chitchat-agent-role-dev`) needs minimal permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
      ]
    }
  ]
}
```

**Note:** No Lambda permissions needed since this agent has no action groups.

---

## 📝 Configuration Files

### Agent Configuration
- **Location:** Managed by AWS Bedrock (no local file)
- **View:** AWS Console or CLI (`aws bedrock-agent get-agent`)

### No Lambda Code
- **Reason:** This agent uses only the LLM, no external actions
- **Benefit:** Faster responses, simpler architecture

### No OpenAPI Schema
- **Reason:** No action groups configured
- **Benefit:** Less complexity, easier maintenance

---

## 🎭 Conversation Examples

### Example 1: Simple Greeting Flow

**User:** Hi there!

**Chitchat Agent:** Hello! Welcome! I'm here to help make your scheduling experience great. How can I assist you today?

**User:** I'm good, thanks! Just looking around.

**Chitchat Agent:** That's wonderful! Feel free to ask me anything. If you need help with scheduling an appointment, checking project details, or anything else, just let me know!

---

### Example 2: Redirect to Scheduling

**User:** Hello! Can you help me book an appointment?

**Chitchat Agent:** Hello! Absolutely, I'd be happy to help you with that! Let me connect you with our Scheduling specialist who can check availability and book your appointment for you.

**[Supervisor routes to Scheduling Agent]**

**Scheduling Agent:** Hi! I'd be happy to help you schedule an appointment. Can you provide me with your customer ID so I can look up your projects?

---

### Example 3: Mixed Conversation

**User:** Hi! How's your day going?

**Chitchat Agent:** Hello! My day is going great, thank you for asking! I'm here and ready to help you with anything you need. How's your day going?

**User:** Pretty good! I need to schedule an appointment.

**Chitchat Agent:** I'm glad to hear your day is going well! For scheduling, let me connect you with our Scheduling specialist who can help you find the perfect time slot.

---

## 🚀 Next Steps

The Chitchat Agent is complete and ready to use:

1. ✅ Agent is PREPARED
2. ✅ Instructions configured for casual conversation
3. ✅ No action groups needed (LLM-only)
4. ✅ Integrated with Supervisor Agent
5. → Test routing from Supervisor
6. → Verify smooth transitions to specialist agents

---

## 📚 Related Documentation

- **[AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md](./AWS_BEDROCK_COMPLETE_SETUP_GUIDE.md)** - Complete setup guide
- **[SUPERVISOR_AGENT_SETUP.md](./SUPERVISOR_AGENT_SETUP.md)** - Supervisor agent setup
- **[SCHEDULING_AGENT_SETUP.md](./SCHEDULING_AGENT_SETUP.md)** - Scheduling agent setup
- **[INFORMATION_AGENT_SETUP.md](./INFORMATION_AGENT_SETUP.md)** - Information agent setup
- **[NOTES_AGENT_SETUP.md](./NOTES_AGENT_SETUP.md)** - Notes agent setup

---

## 💡 Design Philosophy

### Why Have a Separate Chitchat Agent?

**1. Separation of Concerns**
- Keeps conversational logic separate from business logic
- Specialist agents focus on their specific tasks
- Easier to tune each agent's behavior

**2. Better Customer Experience**
- Warm, friendly first interaction
- Smooth transitions to specialist agents
- Natural conversation flow

**3. Reduced Token Usage**
- Chitchat doesn't need context from Lambda functions
- Faster responses (no Lambda cold starts)
- Lower costs for casual conversation

**4. Easier Maintenance**
- Update chitchat personality without affecting business logic
- Test conversational improvements independently
- Simple to add new greetings or responses

---

## 📊 Cost Optimization

### Chitchat Agent Costs

**Model Usage Only:**
- No Lambda invocations
- No API calls
- Just Claude Sonnet 4.5 model tokens

**Estimated Cost per Conversation:**
- Input tokens: ~100 (user greeting + context)
- Output tokens: ~50-100 (friendly response)
- Cost: ~$0.0015 - $0.003 per interaction

**Comparison:**
- Chitchat: $0.003 per interaction
- Scheduling with Lambda: $0.005 - $0.010 per interaction
- Information with Lambda: $0.005 - $0.010 per interaction

**Monthly Costs (1000 chitchat interactions):**
- Model: ~$3
- No Lambda costs
- Total: ~$3/month

---

**Last Updated:** 2025-10-17
**Status:** Complete and ready to use
**Agent Version:** DRAFT
**Special Note:** No action groups needed - LLM-only agent
