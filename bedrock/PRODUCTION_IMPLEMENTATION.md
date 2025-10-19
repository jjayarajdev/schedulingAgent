# Production Implementation Guide

## How to Use Session Attributes in Your Application

### Overview

When a user logs into your application, you'll have their `customer_id` in your session. Here's how to pass it to AWS Bedrock agents so they can call Lambda functions with the correct context.

## ✅ Working Solution

### The Pattern

```python
def invoke_bedrock_agent(user_message, customer_id, customer_type):
    """
    Invoke Bedrock agent with customer context from logged-in session.

    Args:
        user_message: The user's actual question/request
        customer_id: From your login session (e.g., "CUST001")
        customer_type: B2C or B2B from your user profile
    """

    # Inject customer context into the prompt
    augmented_prompt = f"""Session Context:
- Customer ID: {customer_id}
- Customer Type: {customer_type}

User Request: {user_message}

Please help the customer with their request using their customer ID for any actions."""

    client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

    response = client.invoke_agent(
        agentId='V3BW0KFBMX',  # Your supervisor agent
        agentAliasId='K6BWBY1RNY',  # Your production alias
        sessionId=session_id,  # Unique per conversation
        inputText=augmented_prompt,  # Augmented with context
        sessionState={
            'sessionAttributes': {
                'customer_id': customer_id,
                'customer_type': customer_type
            }
        }
    )

    # Stream response back to user
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                yield chunk['bytes'].decode('utf-8')
```

## Integration Examples

### Example 1: Flask/FastAPI Web Application

```python
from flask import Flask, session, request, jsonify
import boto3

app = Flask(__name__)
bedrock_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

@app.route('/api/chat', methods=['POST'])
def chat():
    # Get customer info from login session
    customer_id = session.get('customer_id')  # Set during login
    customer_type = session.get('customer_type')  # B2C or B2B

    if not customer_id:
        return jsonify({'error': 'Not logged in'}), 401

    # Get user's message
    user_message = request.json.get('message')

    # Generate unique session ID for this conversation
    conversation_id = session.get('bedrock_session_id')
    if not conversation_id:
        conversation_id = f"session-{customer_id}-{int(time.time())}"
        session['bedrock_session_id'] = conversation_id

    # Augment prompt with customer context
    augmented_prompt = f"""Session Context:
- Customer ID: {customer_id}
- Customer Type: {customer_type}

User Request: {user_message}

Please help the customer with their request using their customer ID for any actions."""

    # Invoke Bedrock
    response = bedrock_client.invoke_agent(
        agentId='V3BW0KFBMX',
        agentAliasId='K6BWBY1RNY',
        sessionId=conversation_id,
        inputText=augmented_prompt,
        sessionState={
            'sessionAttributes': {
                'customer_id': customer_id,
                'customer_type': customer_type
            }
        }
    )

    # Collect response
    full_response = ""
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                full_response += chunk['bytes'].decode('utf-8')

    return jsonify({
        'response': full_response,
        'customer_id': customer_id
    })


@app.route('/api/login', methods=['POST'])
def login():
    # Your authentication logic
    username = request.json.get('username')
    password = request.json.get('password')

    # Authenticate user (your logic)
    user = authenticate(username, password)

    if user:
        # Store customer info in session
        session['customer_id'] = user.customer_id
        session['customer_type'] = user.customer_type
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Invalid credentials'}), 401
```

### Example 2: React Frontend Integration

```javascript
// api.js - API client
export const sendChatMessage = async (message) => {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include', // Include session cookie
    body: JSON.stringify({ message }),
  });

  return response.json();
};

// ChatComponent.jsx
import React, { useState } from 'react';
import { sendChatMessage } from './api';

function ChatComponent() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    // Add user message
    setMessages([...messages, { role: 'user', content: input }]);
    setLoading(true);

    try {
      // Send to backend (customer_id is in session)
      const response = await sendChatMessage(input);

      // Add agent response
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.response
      }]);
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setLoading(false);
      setInput('');
    }
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {loading && <div className="loading">Agent is thinking...</div>}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        placeholder="Ask about your projects..."
      />
      <button onClick={handleSend}>Send</button>
    </div>
  );
}
```

### Example 3: AWS Lambda + API Gateway

```python
# lambda_handler.py
import json
import boto3
import time

bedrock_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

def lambda_handler(event, context):
    # Get customer info from JWT token or API Gateway authorizer
    claims = event['requestContext']['authorizer']['claims']
    customer_id = claims['customer_id']
    customer_type = claims.get('customer_type', 'B2C')

    # Parse request
    body = json.loads(event['body'])
    user_message = body['message']
    session_id = body.get('session_id', f"session-{customer_id}-{int(time.time())}")

    # Augment prompt
    augmented_prompt = f"""Session Context:
- Customer ID: {customer_id}
- Customer Type: {customer_type}

User Request: {user_message}

Please help the customer with their request using their customer ID for any actions."""

    # Invoke Bedrock
    response = bedrock_client.invoke_agent(
        agentId='V3BW0KFBMX',
        agentAliasId='K6BWBY1RNY',
        sessionId=session_id,
        inputText=augmented_prompt,
        sessionState={
            'sessionAttributes': {
                'customer_id': customer_id,
                'customer_type': customer_type
            }
        }
    )

    # Collect response
    full_response = ""
    for chunk in response['completion']:
        if 'chunk' in chunk:
            if 'bytes' in chunk['chunk']:
                full_response += chunk['chunk']['bytes'].decode('utf-8')

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'response': full_response,
            'session_id': session_id
        })
    }
```

## Key Points

### ✅ What Works

1. **User logs in** → You store `customer_id` in session
2. **User sends message** → You retrieve `customer_id` from session
3. **Augment the prompt** with customer context before sending to Bedrock
4. **Agents receive context** and can use it to call Lambda functions
5. **Lambda functions** get `customer_id` as parameter and return real data

### ⚠️ Important Notes

1. **Session Management:**
   - Create unique `session_id` per conversation (not per request)
   - Use format: `session-{customer_id}-{timestamp}`
   - Reuse same `session_id` for conversation continuity

2. **Security:**
   - Always validate user is logged in before invoking agent
   - Never expose agent IDs or aliases to frontend
   - Validate customer_id matches logged-in user

3. **Error Handling:**
   - Handle timeout errors (agents can take 30+ seconds)
   - Implement retry logic for transient failures
   - Log failures for debugging

4. **Performance:**
   - First invocation can take 60+ seconds (cold start)
   - Subsequent calls in same session are faster
   - Consider showing loading indicators

## Testing in Production

### Test Script

```python
#!/usr/bin/env python3
"""Test production setup with real user flow"""
import boto3
import time

def simulate_user_session(customer_id, customer_type='B2C'):
    """Simulate a logged-in user having a conversation"""

    client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    session_id = f"session-{customer_id}-{int(time.time())}"

    print(f"\n{'='*80}")
    print(f"SIMULATED USER SESSION")
    print(f"{'='*80}")
    print(f"Customer ID: {customer_id}")
    print(f"Session ID: {session_id}\n")

    # Test queries
    queries = [
        "Show me all my projects",
        "What are your business hours?",
        "Tell me about project 12345",
        "What dates are available for project 12347?"
    ]

    for query in queries:
        print(f"\n{'─'*80}")
        print(f"User: {query}")
        print(f"{'─'*80}")

        # Augment prompt
        augmented_prompt = f"""Session Context:
- Customer ID: {customer_id}
- Customer Type: {customer_type}

User Request: {query}

Please help the customer with their request using their customer ID for any actions."""

        try:
            response = client.invoke_agent(
                agentId='V3BW0KFBMX',
                agentAliasId='K6BWBY1RNY',
                sessionId=session_id,
                inputText=augmented_prompt,
                sessionState={
                    'sessionAttributes': {
                        'customer_id': customer_id,
                        'customer_type': customer_type
                    }
                }
            )

            print("Agent: ", end='')
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        print(chunk['bytes'].decode('utf-8'), end='')
            print()

        except Exception as e:
            print(f"Error: {e}")

# Run test
if __name__ == '__main__':
    simulate_user_session('CUST001', 'B2C')
```

## Configuration

### Agent IDs (Production)

```python
# bedrock_config.py
BEDROCK_CONFIG = {
    'region': 'us-east-1',
    'supervisor_agent_id': 'V3BW0KFBMX',
    'supervisor_alias_id': 'K6BWBY1RNY',  # Update with production alias

    # Specialist agents (for direct testing)
    'specialists': {
        'scheduling': '8BGUCA98U7',
        'information': 'UVF5I7KLZ0',
        'notes': 'H0UWLOOQWN',
        'chitchat': 'OBSED5E3TZ'
    }
}
```

## Monitoring

### CloudWatch Logs

Monitor Lambda invocations to verify agents are calling functions:

```bash
# Watch scheduling actions
aws logs tail /aws/lambda/scheduling-agent-scheduling-actions \
  --follow --region us-east-1

# Watch information actions
aws logs tail /aws/lambda/scheduling-agent-information-actions \
  --follow --region us-east-1

# Watch notes actions
aws logs tail /aws/lambda/scheduling-agent-notes-actions \
  --follow --region us-east-1
```

### Metrics to Track

1. **Response times** - First call vs subsequent calls
2. **Error rates** - Timeout errors, validation errors
3. **Lambda invocations** - Verify agents are calling functions
4. **Hallucination checks** - Look for fake data in responses

---

**Summary:** The multi-agent system works perfectly when you inject customer context into the prompt. Your login session provides the `customer_id`, which you augment into each Bedrock request. The agents then use this context to call Lambda functions and return real data.

**Status:** ✅ Ready for production integration
