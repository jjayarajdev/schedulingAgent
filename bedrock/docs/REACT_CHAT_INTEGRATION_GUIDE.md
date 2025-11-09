# React Chat App → Bedrock Agents Integration Guide
**Integrating Your Existing React Chat with Bedrock Multi-Agent System**

---

## 🎯 Goal
Connect your **existing React chat application** to call your **new Bedrock agents** instead of the old backend.

---

## 📋 What You Need

### 1. Your Old React Chat App
- Location: Where is your current production React chat?
- Current API: What backend does it currently call?
- Authentication: How do users authenticate?

### 2. Your New Bedrock Agents (Already Deployed!)
- ✅ Supervisor Agent
- ✅ SchedulingAgent
- ✅ pf-information
- ✅ pf-chitchat
- ✅ Lambda functions with ProjectForce API integration

---

## 🏗️ Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Your Existing React Chat App                    │
│  (Running in Production - Don't Touch Yet!)            │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Change API endpoint
                       │ (Only change this line!)
                       ↓
┌─────────────────────────────────────────────────────────┐
│              NEW Backend API                            │
│  Option A: Flask (backend/app.py) - Quick             │
│  Option B: Lambda + API Gateway - Production          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ InvokeAgent
                       ↓
┌─────────────────────────────────────────────────────────┐
│           AWS Bedrock Agents (Already Working!)        │
│  - Supervisor, Scheduling, Information, Chitchat       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│           Lambda → ProjectForce API                     │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Integration (Option A) - Use Flask Backend

**This gets you working in 1 hour!**

### Step 1: Deploy Flask Backend

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend

# Install dependencies
pip3 install flask flask-cors boto3

# Configure agents
# Edit agent_config.json with your agent IDs
cat > agent_config.json <<EOF
{
  "supervisor_id": "2ISTTH2SMI",
  "supervisor_alias": "TSTALIASID",
  "region": "us-east-1",
  "agents": {
    "scheduling": {
      "agent_id": "INJAT6DHEJ",
      "alias_id": "TSTALIASID"
    },
    "information": {
      "agent_id": "BGPHWLGRC8",
      "alias_id": "TSTALIASID"
    },
    "chitchat": {
      "agent_id": "CP9PMY5EF8",
      "alias_id": "TSTALIASID"
    }
  },
  "routing": {
    "enabled": true,
    "use_supervisor": false
  }
}
EOF

# Run the backend
python3 app.py
```

Backend will run on: **http://localhost:5000**

### Step 2: Update Your React App API Endpoint

**In your existing React chat app, find the API call**. It probably looks like:

```typescript
// OLD CODE (current)
const response = await fetch('https://your-old-backend.com/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    message: userMessage
  })
});
```

**Change to**:

```typescript
// NEW CODE (Bedrock agents)
const response = await fetch('http://localhost:5000/api/chat/simple', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: userMessage,
    session_id: sessionId,
    user_context: {
      customer_id: userId,
      // Add any user data from ProjectForce
    }
  })
});

const data = await response.json();
const botMessage = data.response;
```

### Step 3: Test Locally

1. **Terminal 1**: Run Flask backend
   ```bash
   cd backend && python3 app.py
   ```

2. **Terminal 2**: Run your React app
   ```bash
   cd your-react-app && npm start
   ```

3. **Test**: Open browser, send messages
   - "show me my projects"
   - "what is the weather?"
   - "tell me a joke"

---

## 🏢 Production Integration (Option B) - Lambda + API Gateway

**Better for production, takes 1-2 days**

### Architecture

```
Your React App → API Gateway → Lambda → Bedrock Agents
```

### Step 1: Create Backend Lambda

**Create `lambda/backend/handler.py`**:

```python
#!/usr/bin/env python3
"""
Lambda handler for React chat → Bedrock agents
"""

import json
import boto3
import os
from typing import Dict, Any

# Initialize Bedrock client
bedrock_agent_runtime = boto3.client(
    'bedrock-agent-runtime',
    region_name=os.environ.get('AWS_REGION', 'us-east-1')
)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle chat requests from React app
    """
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        message = body.get('message', '')
        session_id = body.get('session_id', f"session-{context.request_id}")
        user_context = body.get('user_context', {})

        # Route to appropriate agent based on intent
        agent_id = route_to_agent(message)
        agent_alias = os.environ.get('AGENT_ALIAS_ID')

        # Invoke Bedrock agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias,
            sessionId=session_id,
            inputText=message,
            sessionState={
                'sessionAttributes': user_context
            }
        )

        # Parse response
        completion_text = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    completion_text += chunk['bytes'].decode('utf-8')

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'response': completion_text,
                'session_id': session_id,
                'agent_used': agent_id
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }

def route_to_agent(message: str) -> str:
    """
    Simple intent routing
    """
    message_lower = message.lower()

    # Scheduling keywords
    if any(word in message_lower for word in ['schedule', 'appointment', 'calendar', 'book', 'reschedule']):
        return os.environ.get('SCHEDULING_AGENT_ID')

    # Information keywords
    elif any(word in message_lower for word in ['weather', 'time', 'date', 'information']):
        return os.environ.get('INFORMATION_AGENT_ID')

    # Default to supervisor
    else:
        return os.environ.get('SUPERVISOR_AGENT_ID')
```

### Step 2: Deploy Lambda

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Create deployment package
mkdir -p lambda/backend
cp backend/app.py lambda/backend/handler.py  # Adapt the code above
cd lambda/backend

# Package
zip -r backend.zip handler.py

# Deploy
aws lambda create-function \
    --function-name pf-chat-backend \
    --runtime python3.11 \
    --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-bedrock-role \
    --handler handler.lambda_handler \
    --zip-file fileb://backend.zip \
    --timeout 30 \
    --memory-size 512 \
    --environment Variables="{
        SUPERVISOR_AGENT_ID=2ISTTH2SMI,
        SCHEDULING_AGENT_ID=INJAT6DHEJ,
        INFORMATION_AGENT_ID=BGPHWLGRC8,
        CHITCHAT_AGENT_ID=CP9PMY5EF8,
        AGENT_ALIAS_ID=TSTALIASID,
        AWS_REGION=us-east-1
    }"
```

### Step 3: Create API Gateway

**Option 3a: AWS Console** (Easier)

1. Go to **API Gateway** console
2. Click **Create API** → **REST API**
3. API name: `ProjectForce-Chat-API`
4. Create resource: `/chat`
5. Create method: **POST**
6. Integration type: **Lambda Function**
7. Select: `pf-chat-backend`
8. Enable **CORS**
9. Deploy to stage: `prod`
10. Get API URL: `https://abc123.execute-api.us-east-1.amazonaws.com/prod`

**Option 3b: AWS CLI** (Faster if you know what you're doing)

```bash
# Create API
API_ID=$(aws apigateway create-rest-api \
    --name "ProjectForce-Chat-API" \
    --query 'id' --output text)

# Get root resource
ROOT_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --query 'items[0].id' --output text)

# Create /chat resource
RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_ID \
    --path-part chat \
    --query 'id' --output text)

# Create POST method
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method POST \
    --authorization-type NONE

# Integrate with Lambda
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:pf-chat-backend/invocations"

# Enable CORS
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method OPTIONS \
    --authorization-type NONE

# Deploy
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod
```

### Step 4: Update React App

```typescript
// Update API endpoint in your React app
const API_ENDPOINT = 'https://abc123.execute-api.us-east-1.amazonaws.com/prod/chat';

async function sendMessage(message: string) {
  const response = await fetch(API_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionStorage.getItem('chat_session_id'),
      user_context: {
        customer_id: getCurrentUserId(),
        // Add ProjectForce user data
      }
    })
  });

  const data = await response.json();
  return data.response;
}
```

---

## 🔧 Minimal Code Changes Needed

### If Your React App Has:

**1. Simple chat interface with `sendMessage()` function**:
```typescript
// ONLY CHANGE THIS:
const API_URL = 'YOUR_NEW_BACKEND_URL';  // Flask or API Gateway

// Rest stays the same
async function sendMessage(text: string) {
  const response = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message: text })
  });
  return response.json();
}
```

**2. Chat component with state management**:
```typescript
// NO CHANGES needed to your UI components
// Only change the API service layer

// Before:
import { sendMessage } from './services/oldChatApi';

// After:
import { sendMessage } from './services/bedrockChatApi';  // New file
```

**3. Redux/Context for chat state**:
```typescript
// NO CHANGES to your state management
// Only change the API action/thunk

// actions/chatActions.ts
export const sendChatMessage = (message) => async (dispatch) => {
  // Change this URL only ↓
  const response = await fetch('NEW_BACKEND_URL', {...});
  // Rest stays the same
};
```

---

## 📝 Implementation Checklist

### Phase 1: Local Testing (Day 1)
- [ ] Start Flask backend (`backend/app.py`)
- [ ] Update React app API endpoint to `http://localhost:5000`
- [ ] Test with sample queries
- [ ] Verify agent responses work
- [ ] Check session management

### Phase 2: Staging Deploy (Day 2-3)
- [ ] Create Lambda function from handler.py
- [ ] Create API Gateway
- [ ] Update React app to use API Gateway URL
- [ ] Deploy React app to staging S3
- [ ] Test end-to-end in staging

### Phase 3: Production Deploy (Day 4-5)
- [ ] Add Cognito authentication (if needed)
- [ ] Enable API Gateway caching
- [ ] Setup CloudWatch monitoring
- [ ] Load test with 100 concurrent users
- [ ] Update DNS to point to new API
- [ ] Deploy React app to production
- [ ] Monitor for 24 hours

---

## 🎨 Sample React Integration Code

**Create `src/services/bedrockChatApi.ts`**:

```typescript
// bedrockChatApi.ts
// Drop-in replacement for your old chat API

interface ChatMessage {
  message: string;
  session_id?: string;
  user_context?: Record<string, any>;
}

interface ChatResponse {
  response: string;
  session_id: string;
  agent_used?: string;
}

class BedrockChatAPI {
  private apiUrl: string;
  private sessionId: string;

  constructor() {
    // Use environment variable for API URL
    this.apiUrl = process.env.REACT_APP_CHAT_API_URL || 'http://localhost:5000/api/chat/simple';
    this.sessionId = this.getOrCreateSessionId();
  }

  private getOrCreateSessionId(): string {
    let sessionId = sessionStorage.getItem('chat_session_id');
    if (!sessionId) {
      sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('chat_session_id', sessionId);
    }
    return sessionId;
  }

  async sendMessage(message: string, userContext?: Record<string, any>): Promise<string> {
    try {
      const response = await fetch(this.apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          session_id: this.sessionId,
          user_context: userContext
        } as ChatMessage)
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data: ChatResponse = await response.json();
      return data.response;

    } catch (error) {
      console.error('Chat API error:', error);
      throw error;
    }
  }

  resetSession() {
    this.sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    sessionStorage.setItem('chat_session_id', this.sessionId);
  }
}

export const chatAPI = new BedrockChatAPI();
```

**Use in your existing React component**:

```typescript
// YourExistingChatComponent.tsx
import { chatAPI } from './services/bedrockChatApi';  // NEW

function ChatComponent() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const handleSend = async () => {
    // Add user message
    setMessages([...messages, { role: 'user', content: input }]);

    try {
      // Call Bedrock agents (NEW)
      const response = await chatAPI.sendMessage(input, {
        customer_id: userId,  // Your user data
        // Add any ProjectForce context
      });

      // Add bot response
      setMessages(prev => [...prev, { role: 'assistant', content: response }]);

    } catch (error) {
      console.error('Error:', error);
    }

    setInput('');
  };

  // Rest of your component stays the same
  return (
    <div className="chat">
      {/* Your existing UI */}
    </div>
  );
}
```

---

## 🚦 Testing Strategy

### 1. Unit Test the Integration

```typescript
// bedrockChatApi.test.ts
describe('BedrockChatAPI', () => {
  it('should send message and get response', async () => {
    const response = await chatAPI.sendMessage('Hello');
    expect(response).toBeTruthy();
    expect(typeof response).toBe('string');
  });

  it('should maintain session across messages', async () => {
    const sessionId1 = chatAPI.sessionId;
    await chatAPI.sendMessage('First message');
    const sessionId2 = chatAPI.sessionId;
    expect(sessionId1).toBe(sessionId2);
  });
});
```

### 2. Integration Test with Real Agents

```bash
# Test queries
curl -X POST http://localhost:5000/api/chat/simple \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show me my projects",
    "session_id": "test-session"
  }'
```

### 3. Load Test

```bash
# Install k6
brew install k6

# Create load-test.js
k6 run load-test.js
```

---

## 💡 Pro Tips

1. **Start Simple**: Use Flask backend first, then migrate to Lambda
2. **Keep Old Backend**: Run both in parallel during migration
3. **Feature Flag**: Add toggle to switch between old/new backend
4. **Monitor Everything**: CloudWatch logs, API Gateway metrics
5. **Gradual Rollout**: 10% → 50% → 100% of users

---

## 🆘 Troubleshooting

### CORS Errors
```typescript
// Backend must return these headers:
'Access-Control-Allow-Origin': '*'
'Access-Control-Allow-Headers': 'Content-Type'
'Access-Control-Allow-Methods': 'POST, OPTIONS'
```

### Session Not Working
```typescript
// Check session ID persistence
console.log('Session ID:', sessionStorage.getItem('chat_session_id'));
```

### Agent Not Responding
```bash
# Check Lambda logs
aws logs tail /aws/lambda/pf-chat-backend --follow
```

---

## 📚 Next Steps

1. **Today**: Test Flask backend locally with your React app
2. **This Week**: Deploy Lambda + API Gateway to staging
3. **Next Week**: Production deployment with monitoring
4. **Ongoing**: Monitor, optimize, scale

---

**Questions? Check**:
- `backend/app.py` - Flask backend reference
- `testing/ui/pf_auth_demo.html` - Working example
- `PRODUCTION_WEB_APP_GUIDE.md` - Full production guide
