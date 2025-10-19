# 🚀 START HERE - Bedrock Multi-Agent System

## Quick Start (3 Steps)

### 1️⃣ Setup (~3 minutes)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/scripts
python3 complete_setup.py
```

**Creates:**
- 5 agents (1 supervisor + 4 specialists)
- 12 Lambda action groups
- All collaborator relationships
- Saves agent IDs to `agent_config.json`

### 2️⃣ Test (~1 minute)

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/tests
python3 test_production.py
```

**Expected:** ✅ 5/5 tests pass

### 3️⃣ Integrate

**See:** `PRODUCTION_IMPLEMENTATION.md` for Flask/FastAPI/React/Lambda examples

## 🔑 The Key Pattern

When a user logs into your app, you have their `customer_id`. Use this pattern:

```python
import boto3

def chat_with_agent(user_message, customer_id):
    """Your application's chat function"""
    
    # CRITICAL: Inject customer context into prompt
    augmented_prompt = f"""Session Context:
- Customer ID: {customer_id}
- Customer Type: B2C

User Request: {user_message}

Please help the customer with their request using their customer ID for any actions."""
    
    client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    
    response = client.invoke_agent(
        agentId='V3BW0KFBMX',  # From agent_config.json
        agentAliasId='K6BWBY1RNY',  # From agent_config.json
        sessionId=f"session-{customer_id}-{int(time.time())}",
        inputText=augmented_prompt,
        sessionState={
            'sessionAttributes': {
                'customer_id': customer_id,
                'customer_type': 'B2C'
            }
        }
    )
    
    # Return response to user
    full_response = ""
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                full_response += chunk['bytes'].decode('utf-8')
    
    return full_response
```

**That's it!** The agents will:
1. Extract customer_id from the prompt
2. Route to the right specialist
3. Call Lambda functions with customer_id
4. Return real data (no hallucinations)

## 📖 Documentation

| File | What It Is |
|------|-----------|
| **README.md** | Architecture, quick start, troubleshooting |
| **PRODUCTION_IMPLEMENTATION.md** | Complete integration examples (Flask/FastAPI/React/Lambda) |
| **SETUP_COMPLETE_SUMMARY.md** | Technical details, limitations, decisions |
| **CLEANUP_SUMMARY.md** | File organization, what's active vs archived |

## ✅ Success Checklist

Your system works when:

- [x] Setup completes without errors
- [x] `agent_config.json` created with 5 agent IDs
- [x] Tests pass (5/5)
- [x] CloudWatch shows Lambda invocations
- [x] Agents return real project IDs (12345, 12347, 12350)
- [x] No hallucinated data (Kitchen, Bathroom, etc.)

## 🆘 Troubleshooting

**Tests failing?**
1. Check agent IDs in `agent_config.json`
2. Run `./scripts/test_lambdas.sh` to verify Lambda functions
3. Check CloudWatch logs for errors
4. Re-run `python3 scripts/complete_setup.py`

**Agents not calling Lambda?**
- Make sure you're using the pattern above (prompt injection)
- Check action groups: `aws bedrock-agent list-agent-action-groups --agent-id <ID> --agent-version DRAFT --region us-east-1`

**Need help?**
- See `README.md` for detailed troubleshooting
- Check `PRODUCTION_IMPLEMENTATION.md` for integration patterns

## 🎯 What You Have

✅ **5 AWS Bedrock Agents:**
- Supervisor (routes requests)
- Scheduling (6 actions: list projects, availability, bookings, etc.)
- Information (4 actions: project details, status, hours, weather)
- Notes (2 actions: add, list)
- Chitchat (greetings, farewells)

✅ **12 Lambda Functions Actions:**
- All connected via OpenAPI 3.0 schemas
- Mock data mode for testing
- Real API ready when you are

✅ **Production-Ready Code:**
- ONE setup script
- ONE test script
- Complete integration examples
- Working session context pattern

## 🚀 Next Steps

1. ✅ Run setup (done if you followed step 1)
2. ✅ Run tests (done if you followed step 2)
3. 👉 **Integrate** into your Flask/FastAPI/Lambda app
4. 👉 **Deploy** to production
5. 👉 **Monitor** with CloudWatch

---

**Ready?** Start with step 1 above! 🎉
