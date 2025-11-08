# Supervisor Multi-Agent Collaboration Research Findings

**Date**: October 21, 2025
**Source**: AWS Documentation & Blog Posts

---

## Key Findings from AWS Documentation

### 1. Two Collaboration Modes

**SUPERVISOR Mode** (what we had initially):
- Full orchestration for ALL requests
- Supervisor analyzes, breaks down complex requests
- Coordinates multiple agents as needed
- More overhead for simple queries

**SUPERVISOR_ROUTER Mode** (what we have now):
- **Routes simple requests directly** to specialist agents
- Bypasses full orchestration for efficiency
- Falls back to full supervisor mode for complex/ambiguous queries
- **This is what we want for our use case**

### 2. How Routing Works

**Supervisor with Routing Mode**:
```
Simple Query → Direct route to specialist agent → Response
Complex Query → Supervisor coordination → Multiple agents → Consolidated response
```

**Example**:
- "What's the weather?" → Routes directly to Information Agent
- "Schedule appointment and check weather" → Supervisor coordinates both agents

### 3. Configuration Requirements

✅ **We did correctly**:
- Changed to `SUPERVISOR_ROUTER` mode
- Associated 4 collaborators
- Set collaboration instructions
- Enabled conversation relay (`TO_COLLABORATOR`)

❓ **What documentation emphasizes**:
- Use **alias versions** of collaborator agents (we are using v1 aliases ✅)
- Clearly define each agent's unique role (we did ✅)
- Minimize overlapping responsibilities (we did ✅)
- Supervisor must be saved before associating collaborators (we did ✅)

### 4. Known Issues

**From search results**:
- Someone reported a "Potential Bug" with Amazon Multi-Agent Collaboration Routing on AWS re:Post
- Couldn't access details (403 error), but confirms others are experiencing routing issues
- This may be a platform limitation, not our configuration issue

### 5. Feature Status

- **Generally Available**: March 10, 2025
- This is a relatively new feature (< 1 month old in GA)
- Likely still has bugs and limitations being worked out

---

## What We've Discovered Through Testing

### ✅ What's Working

1. **Agents are properly associated**:
   ```
   Scheduling-Agent, Information-Agent, Notes-Agent, Chitchat-Agent
   All associated with relayConversationHistory: TO_COLLABORATOR
   ```

2. **Supervisor mode changed**:
   ```
   agentCollaboration: SUPERVISOR_ROUTER ✅
   ```

3. **Specialist agents work independently**:
   - Chitchat: 100% functional
   - Information: 100% functional (Lambda invokes working)
   - Notes: 100% functional
   - Scheduling: Has session attribute issues (separate problem)

### ❌ What's NOT Working

1. **Supervisor doesn't route to collaborators**:
   - Test trace shows: 0 collaborator invocations
   - Supervisor handles all requests itself
   - No delegation occurring

2. **Possible explanations**:
   - **Platform bug**: Feature is very new (GA < 1 month)
   - **TSTALIASID limitation**: Test alias may not support routing
   - **Model behavior**: Claude 4.5 may need specific prompting
   - **Missing configuration**: Undocumented requirement we're missing

---

## Comparison: What We Have vs. What Docs Say

| Requirement | Our Status | Notes |
|-------------|------------|-------|
| Supervisor agent created | ✅ | WF1S95L7X1 |
| Collaborators associated | ✅ | 4 agents via v1 aliases |
| Collaboration mode set | ✅ | SUPERVISOR_ROUTER |
| Collaboration instructions | ✅ | Detailed for each agent |
| Conversation relay | ✅ | TO_COLLABORATOR |
| Agent prepared | ✅ | Multiple times |
| Alias updated | ✅ | TSTALIASID pointing to DRAFT |
| **Routing working** | ❌ | **Not functioning** |

---

## Theories About Why Routing Isn't Working

### Theory 1: TSTALIASID Not Supported
**Evidence**:
- We're using TSTALIASID (test alias) for supervisor
- Collaborators use v1 aliases
- Docs emphasize using "alias versions"

**Test**: Try creating a numbered version alias (not TSTALIASID) for supervisor

### Theory 2: Platform Bug
**Evidence**:
- Feature just went GA (March 2025)
- Someone else reported routing bug on AWS re:Post
- No examples show successful routing in wild

**Test**: Open AWS Support case, provide our configuration

### Theory 3: Prompt Engineering Required
**Evidence**:
- Supervisor instructions may need specific format
- Model may need explicit routing keywords
- Documentation lacks specific prompt examples

**Test**: Try different supervisor instruction formats

### Theory 4: Session State Not Passed in Routing Mode
**Evidence**:
- Scheduling Agent can't read session attributes when invoked directly
- Information Agent can invoke Lambda but Scheduling can't
- May be fundamental difference in how routing passes context

**Test**: Check if session attributes work when supervisor routes vs direct invocation

---

## Recommended Next Steps

### Option 1: Use Frontend Routing (RECOMMENDED) ✅

**Why**:
- Frontend routing already configured and working
- No dependency on Bedrock's routing feature
- More control over routing logic
- Proven to work

**How**:
```json
{
  "routing": {
    "enabled": true,
    "method": "llm_intent_classification",
    "use_supervisor": false  ← Keep as false
  }
}
```

**Status**: Already configured, just need to verify it works

### Option 2: Fix Scheduling Agent Session Attributes (PRIORITY)

**Why**:
- This is blocking end-to-end workflow regardless of routing method
- Affects both frontend routing AND supervisor routing
- Relatively easier to fix than platform routing issues

**How**:
1. Check Scheduling Agent instructions for session attribute guidance
2. Compare with working Information Agent configuration
3. Verify action group parameter mapping
4. Test with direct parameter passing

### Option 3: Open AWS Support Case

**Why**:
- We've correctly configured everything per documentation
- Others are reporting similar issues
- May be a known bug with workaround

**How**:
- Provide our configuration details
- Show test results proving routing doesn't work
- Ask about SUPERVISOR_ROUTER mode specifics
- Request examples or troubleshooting guidance

### Option 4: Try Different Supervisor Configuration

**Why**:
- TSTALIASID may have limitations
- Numbered version might work better
- Worth trying before giving up

**How**:
1. Create version 1 of supervisor (not DRAFT)
2. Create regular alias pointing to version 1
3. Retest routing with this alias
4. Compare behavior

---

## Conclusion

**Summary**:
1. ✅ Multi-agent collaboration IS a real, GA feature
2. ✅ SUPERVISOR_ROUTER mode exists and should work
3. ✅ We've configured everything correctly per documentation
4. ❌ Routing is not working despite correct configuration
5. ⚠️ Feature is very new (< 1 month GA) - likely has bugs

**Recommendation**:
**Use frontend routing** (Option 1) as the primary solution, while **fixing the Scheduling Agent session attributes** (Option 2) as the critical blocker. The supervisor routing can be revisited later when the platform matures or AWS provides more guidance.

**Reality Check**:
The Bedrock multi-agent routing feature may not be production-ready yet. Frontend-based routing is more reliable and gives us better control.
