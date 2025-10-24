# Testing Guide - AWS Bedrock Multi-Agent System

**Complete guide for testing your deployed agents**

---

## 🎯 Quick Start

**Best method:** AWS Console (works 100% of the time)

1. Open: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
2. Click **scheduling-agent-supervisor**
3. Click **Test** button
4. Enter: `Hello! How are you?`

---

## 📋 Testing Methods

### Method 1: AWS Console (⭐ Recommended)

**Pros:**
- ✅ Always works (no API permission issues)
- ✅ Visual interface
- ✅ Shows routing decisions
- ✅ Displays full conversation history
- ✅ Can see which collaborator was invoked

**How to use:**

1. **Navigate to Bedrock Agents**
   - URL: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents
   - Or: AWS Console → Services → Bedrock → Agents

2. **Select Your Agent**
   - Find: `scheduling-agent-supervisor`
   - Click on it

3. **Open Test Interface**
   - Click the **"Test"** button in the top right corner
   - A chat panel will appear on the right side

4. **Test Messages**
   - Type your message in the input box
   - Press Enter or click Send
   - Watch the agent route and respond

**Sample Messages:**
```
Hello! How are you today?
```
```
I want to schedule an appointment
```
```
What are your working hours?
```
```
Can you add a note that I prefer morning appointments?
```

---

### Method 2: Interactive Python Script (New!)

**Pros:**
- 🎨 Colored terminal output
- 💬 Interactive chat mode
- ✅ Pre-flight checks
- 📊 Test result summaries
- 🔄 Session management

**Location:** `tests/test_agents_interactive.py`

**How to run:**

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/test_agents_interactive.py
```

**Features:**

**Option 1: Predefined Test Scenarios**
- Runs 4 automated tests
- Tests all collaborator routing
- Shows results summary

**Option 2: Interactive Mode**
- Chat directly with the agent
- Maintains conversation context
- Type 'examples' for sample messages
- Type 'new' to start fresh session
- Type 'quit' to exit

**Option 3: Console Instructions**
- Shows how to test in AWS Console
- Direct links and step-by-step guide

**Pre-flight Checks:**
- ✓ AWS credentials configured
- ✓ Agent exists and is PREPARED
- ✓ Collaborators are associated
- ✓ Model access is enabled

**Note:** If API invocation fails, the script provides instructions for console testing.

---

### Method 3: Basic Python Script

**Location:** `tests/test_agent.py`

**How to run:**

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
python3 tests/test_agent.py
```

**What it does:**
- Runs 4 predefined test scenarios
- Tests routing to all 4 collaborators
- Simple output format

**Known Issue:** Currently fails with API permission errors. Use Method 1 (Console) or Method 2 (Interactive) instead.

---

### Method 4: Verification Script

**Location:** `scripts/verify_deployment.sh`

**How to run:**

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock
./scripts/verify_deployment.sh
```

**What it checks:**
- ✓ Supervisor agent status
- ✓ All 5 agent statuses
- ✓ Collaborator associations (4)
- ✓ S3 bucket and schemas (3)
- ✓ Model access (Claude Sonnet 4.5)

**Output:**
```
==========================================
AWS Bedrock Multi-Agent Deployment Check
==========================================

✓ Checking Supervisor Agent...
Agent: scheduling-agent-supervisor | Status: PREPARED | Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0

✓ Checking Collaborator Associations...
Found 4 collaborators associated with supervisor
  - information_collaborator
  - notes_collaborator
  - chitchat_collaborator
  - scheduling_collaborator

✓ Checking All Agent Statuses...
  scheduling-agent-supervisor: PREPARED
  scheduling-agent-scheduling: PREPARED
  ...

✓ Checking S3 Bucket...
  Found 3 OpenAPI schema files

✓ Checking Model Access...
  Profile: US Anthropic Claude Sonnet 4.5 | Status: ACTIVE

==========================================
✅ Deployment Verification Complete!
==========================================
```

**Note:** This doesn't test agent responses, only infrastructure health.

---

## 🧪 Test Scenarios

### Scenario 1: Chitchat (Greeting)

**Test Messages:**
```
Hello!
Hi there!
How are you doing?
Good morning!
```

**Expected Behavior:**
- Routes to: `chitchat_collaborator`
- Response: Warm greeting
- No action groups invoked
- Friendly, conversational tone

**Example Response:**
```
Hello! I'm doing great, thank you for asking! I'm here to help you
with scheduling appointments and any questions you might have.
How can I assist you today?
```

---

### Scenario 2: Scheduling Request

**Test Messages:**
```
I want to schedule an appointment
I need to book a meeting
Can I schedule something?
I'd like to make an appointment
```

**Expected Behavior:**
- Routes to: `scheduling_collaborator`
- Response: Asks about project selection
- Would invoke: `list_projects` (when Lambda connected)
- Guides through 4-step scheduling workflow

**Example Response:**
```
I'd be happy to help you schedule an appointment! Let me show you
your available projects so you can choose which one you'd like to
schedule for.

[Note: Currently action groups are not connected, so actual project
list won't appear. This will work once Lambda functions are deployed
in Phase 2]
```

---

### Scenario 3: Information Query

**Test Messages:**
```
What are your working hours?
When are you open?
What time do you close?
Tell me about business hours
```

**Expected Behavior:**
- Routes to: `information_collaborator`
- Response: Provides information
- Would invoke: `get_working_hours` (when Lambda connected)

**Example Response:**
```
Let me get that information for you!

[Note: Currently action groups are not connected. Once Lambda
functions are deployed, this will return actual working hours
from the PF360 system]
```

---

### Scenario 4: Notes Request

**Test Messages:**
```
Add a note that I prefer morning appointments
Can you add a note?
I want to leave a note
Please note that I need parking
```

**Expected Behavior:**
- Routes to: `notes_collaborator`
- Response: Confirms note addition
- Would invoke: `add_note` (when Lambda connected)

**Example Response:**
```
I'd be happy to add a note for you!

[Note: Currently action groups are not connected. Once Lambda
functions are deployed, this will save the note to your profile
in the PF360 system]
```

---

### Scenario 5: Multi-Turn Conversation

**Test this in Console or Interactive mode:**

```
User: Hello!
Agent: [Greeting from chitchat_collaborator]

User: I want to schedule an appointment
Agent: [Routes to scheduling_collaborator, asks for project]

User: What are your hours?
Agent: [Routes to information_collaborator, provides hours]

User: Thanks!
Agent: [Routes to chitchat_collaborator, says you're welcome]
```

**Expected Behavior:**
- Supervisor correctly routes each message
- Context is maintained across turns
- Smooth transitions between collaborators

---

## 🎯 What to Look For

### Successful Routing

When testing in AWS Console, you should see:

1. **User Input** - Your message
2. **Agent Thinking** - "Analyzing request..."
3. **Routing Decision** - Which collaborator was selected
4. **Collaborator Response** - The actual response

**Example Console Output:**
```
User: Hello!

Agent Thinking...
Routing to: chitchat_collaborator

chitchat_collaborator: Hello! I'm doing great, thank you for asking!
How can I assist you today?
```

### Incorrect Routing

If routing is wrong:
- Scheduling message goes to chitchat ❌
- Information query goes to notes ❌
- Generic greeting goes to scheduling ❌

**This usually means:**
- Agent instructions need tuning
- Collaborator descriptions unclear
- Re-prepare agent needed

---

## 🔧 Troubleshooting

### Issue 1: API Permission Denied

**Error:**
```
Access denied when calling Bedrock. Check your request permissions
```

**Solution:**
- Use AWS Console testing (Method 1)
- Or use the new interactive script (Method 2) which provides console instructions
- API permissions may need additional setup

---

### Issue 2: Agent Not Responding

**Symptoms:**
- No response in console
- Error messages
- Blank output

**Checks:**
```bash
# Check agent status
aws bedrock-agent get-agent --agent-id 5VTIWONUMO --region us-east-1 | grep agentStatus

# Should show: "agentStatus": "PREPARED"
```

**Solution:**
```bash
# Re-prepare agent
aws bedrock-agent prepare-agent --agent-id 5VTIWONUMO --region us-east-1

# Wait 20 seconds
sleep 20

# Test again
```

---

### Issue 3: Wrong Collaborator Selected

**Symptoms:**
- Greeting goes to scheduling agent
- Scheduling request goes to chitchat
- Routing seems random

**Possible Causes:**
1. Agent instructions not clear enough
2. Collaborator descriptions overlap
3. Agent not prepared after changes

**Solution:**
1. Review agent instructions in `infrastructure/agent_instructions/supervisor.txt`
2. Ensure routing guidelines are clear
3. Re-prepare agent after any changes

---

### Issue 4: Action Groups Not Working

**Symptoms:**
- Agent says "I'll check that" but no data returned
- Placeholder responses
- "Action groups not connected" messages

**This is EXPECTED for Phase 1:**
- Lambda functions not deployed yet (Phase 2)
- Action groups defined but not connected
- Agents can route correctly but can't execute actions yet

**Next Steps:**
- Phase 2: Build Lambda functions
- Connect Lambda to action groups
- Test end-to-end workflows

---

## 📊 Testing Checklist

Before considering testing complete:

- [ ] **Chitchat routing works**
  - Greetings route correctly
  - Thanks/goodbye handled
  - General conversation flows

- [ ] **Scheduling routing works**
  - Appointment requests identified
  - Reschedule requests handled
  - Cancellation requests recognized

- [ ] **Information routing works**
  - Hours questions route correctly
  - Status checks identified
  - General info queries handled

- [ ] **Notes routing works**
  - Add note requests recognized
  - List notes requests handled

- [ ] **Multi-turn works**
  - Context maintained
  - Smooth collaborator transitions
  - No routing confusion

- [ ] **Edge cases handled**
  - Unclear requests
  - Multiple intents in one message
  - Spelling errors/typos

---

## 📝 Test Results Template

Use this template to document your testing:

```markdown
## Test Session: [Date/Time]

### Environment
- Agent ID: 5VTIWONUMO
- Model: Claude Sonnet 4.5
- Method: [Console/Python/Interactive]

### Test Results

#### Test 1: Chitchat
- Input: "Hello!"
- Expected: chitchat_collaborator
- Actual: [collaborator name]
- Result: ✅ PASS / ❌ FAIL
- Notes: [any observations]

#### Test 2: Scheduling
- Input: "I want to schedule an appointment"
- Expected: scheduling_collaborator
- Actual: [collaborator name]
- Result: ✅ PASS / ❌ FAIL
- Notes: [any observations]

#### Test 3: Information
- Input: "What are your working hours?"
- Expected: information_collaborator
- Actual: [collaborator name]
- Result: ✅ PASS / ❌ FAIL
- Notes: [any observations]

#### Test 4: Notes
- Input: "Add a note that I prefer mornings"
- Expected: notes_collaborator
- Actual: [collaborator name]
- Result: ✅ PASS / ❌ FAIL
- Notes: [any observations]

### Summary
- Pass Rate: X/4 (XX%)
- Issues Found: [list]
- Next Steps: [actions]
```

---

## 🚀 Advanced Testing

### Load Testing (Future)

Once Lambda functions are deployed:

```python
# Example load test script
import concurrent.futures
import boto3

def invoke_agent_concurrent(message):
    # Invoke agent logic
    pass

messages = ["Hello!"] * 100
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(invoke_agent_concurrent, messages)
```

### Integration Testing (Future)

Test full workflows:
1. Schedule appointment
2. Confirm booking
3. Add note
4. Check status
5. Reschedule
6. Cancel

---

## 📚 Related Documents

- **[README.md](docs/README.md)** - Project overview
- **[DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md)** - Current status
- **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Deployment steps

---

## 🎯 Summary

**Best for Quick Testing:** AWS Console (Method 1)
**Best for Development:** Interactive Python Script (Method 2)
**Best for CI/CD:** Verification Script (Method 4)

**Current Limitation:** Action groups not connected (Phase 2 needed)
**Current Working:** Agent routing, collaborator selection, conversational responses

**Next Phase:** Build Lambda functions to enable actual data retrieval and appointment booking.

---

**Last Updated:** October 13, 2025
**Status:** ✅ Phase 1 Testing Complete
