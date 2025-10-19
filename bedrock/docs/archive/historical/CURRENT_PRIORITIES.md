# Current Priorities - What to Work On Now

**Date:** October 17, 2025
**Context:** Phase 3 (Voice) is blocked by AISPL account limitation
**Status:** Multiple high-priority tasks ready to start immediately

---

## 🎯 Top Priority: Complete Phase 1.5 (Deploy Lambda Functions)

### Why This is Critical

Your **Lambda functions are built and tested** (100% pass rate), but they're **NOT deployed to AWS yet**. This is the most important missing piece.

**Current Status:**
- ✅ 3 Lambda functions coded (`scheduling-actions`, `information-actions`, `notes-actions`)
- ✅ 12 actions fully implemented
- ✅ Mock data working
- ✅ Tests passing (6/6 flows, 22 invocations)
- ❌ **NOT deployed to AWS Lambda**
- ❌ **NOT connected to Bedrock Agent action groups**

**Impact:** Your Bedrock Agents cannot actually DO anything yet (they're just configured but have no action groups)

---

## 📋 Immediate Action Plan (Next 2-3 Days)

### Priority 1: Deploy Lambda Functions to AWS ⭐⭐⭐

**Time Required:** 2-4 hours
**Complexity:** Low (straightforward deployment)
**Impact:** HIGH - Makes your Bedrock Agents fully functional

#### Step 1: Package Lambda Functions

**For each Lambda function:**

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/lambda

# Package scheduling-actions
cd scheduling-actions
mkdir -p package
pip install -r requirements.txt -t package/
cp handler.py config.py mock_data.py package/
cd package && zip -r ../scheduling-actions.zip . && cd ..

# Package information-actions
cd ../information-actions
mkdir -p package
pip install -r requirements.txt -t package/
cp handler.py config.py mock_data.py package/
cd package && zip -r ../information-actions.zip . && cd ..

# Package notes-actions
cd ../notes-actions
mkdir -p package
pip install -r requirements.txt -t package/
cp handler.py config.py mock_data.py package/
cd package && zip -r ../notes-actions.zip . && cd ..
```

#### Step 2: Create Lambda Functions in AWS

```bash
# Set variables
REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create IAM role for Lambda
aws iam create-role \
  --role-name scheduling-agent-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' \
  --region $REGION

# Attach policies
aws iam attach-role-policy \
  --role-name scheduling-agent-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Wait 10 seconds for role propagation
sleep 10

# Deploy scheduling-actions
aws lambda create-function \
  --function-name scheduling-agent-scheduling-actions \
  --runtime python3.11 \
  --role arn:aws:iam::${ACCOUNT_ID}:role/scheduling-agent-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://scheduling-actions/scheduling-actions.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables={USE_MOCK_API=true} \
  --region $REGION

# Deploy information-actions
aws lambda create-function \
  --function-name scheduling-agent-information-actions \
  --runtime python3.11 \
  --role arn:aws:iam::${ACCOUNT_ID}:role/scheduling-agent-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://information-actions/information-actions.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables={USE_MOCK_API=true} \
  --region $REGION

# Deploy notes-actions
aws lambda create-function \
  --function-name scheduling-agent-notes-actions \
  --runtime python3.11 \
  --role arn:aws:iam::${ACCOUNT_ID}:role/scheduling-agent-lambda-role \
  --handler handler.lambda_handler \
  --zip-file fileb://notes-actions/notes-actions.zip \
  --timeout 30 \
  --memory-size 512 \
  --environment Variables={USE_MOCK_API=true} \
  --region $REGION
```

#### Step 3: Test Lambda Functions in AWS

```bash
# Test scheduling-actions
aws lambda invoke \
  --function-name scheduling-agent-scheduling-actions \
  --payload '{"action": "list_projects", "parameters": {}}' \
  --region $REGION \
  output.json

cat output.json
# Should see projects list

# Test information-actions
aws lambda invoke \
  --function-name scheduling-agent-information-actions \
  --payload '{"action": "get_working_hours", "parameters": {}}' \
  --region $REGION \
  output.json

cat output.json
# Should see working hours

# Test notes-actions
aws lambda invoke \
  --function-name scheduling-agent-notes-actions \
  --payload '{"action": "list_notes", "parameters": {"project_id": "12345"}}' \
  --region $REGION \
  output.json

cat output.json
# Should see notes
```

**Expected Time:** 2 hours

---

### Priority 2: Connect Lambda to Bedrock Agent Action Groups ⭐⭐⭐

**Time Required:** 1-2 hours
**Complexity:** Medium
**Impact:** HIGH - Completes the full integration

#### Step 1: Update Bedrock Agents with Lambda ARNs

You need to update each collaborator agent to point to the Lambda functions.

**For Scheduling Collaborator:**

```bash
SCHEDULING_AGENT_ID="IX24FSMTQH"
SCHEDULING_LAMBDA_ARN="arn:aws:lambda:ap-south-1:${ACCOUNT_ID}:function:scheduling-agent-scheduling-actions"

# Update action group (you'll need to do this via console or API)
# The action group already exists, just needs Lambda ARN added
```

**Via AWS Console (Easier):**

1. Go to: https://console.aws.amazon.com/bedrock/
2. Navigate to **Agents** → **scheduling-agent-scheduling-collab**
3. Click **Edit** → **Action groups**
4. Find your action group
5. **Lambda function**: Select `scheduling-agent-scheduling-actions`
6. **Save**
7. Click **Prepare** (wait 30-60 seconds)

Repeat for:
- Information Collaborator → `scheduling-agent-information-actions`
- Notes Collaborator → `scheduling-agent-notes-actions`

#### Step 2: Grant Bedrock Permission to Invoke Lambda

```bash
# For each Lambda function
aws lambda add-permission \
  --function-name scheduling-agent-scheduling-actions \
  --statement-id bedrock-invoke-scheduling \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:ap-south-1:${ACCOUNT_ID}:agent/${SCHEDULING_AGENT_ID}" \
  --region $REGION

# Repeat for other functions
aws lambda add-permission \
  --function-name scheduling-agent-information-actions \
  --statement-id bedrock-invoke-information \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:ap-south-1:${ACCOUNT_ID}:agent/C9ANXRIO8Y" \
  --region $REGION

aws lambda add-permission \
  --function-name scheduling-agent-notes-actions \
  --statement-id bedrock-invoke-notes \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:ap-south-1:${ACCOUNT_ID}:agent/G5BVBYEPUM" \
  --region $REGION
```

#### Step 3: Test End-to-End via Bedrock Console

1. Go to: https://console.aws.amazon.com/bedrock/home?region=ap-south-1#/agents
2. Click **scheduling-agent-supervisor**
3. Click **Test** button
4. Try conversation:
   ```
   User: "I want to schedule an appointment"

   Expected: Agent should route to scheduling collaborator,
             invoke Lambda, get real response from list_projects
   ```

**Expected Time:** 1-2 hours

---

### Priority 3: Create Database Models (Missing Piece) ⭐⭐

**Time Required:** 3-4 hours
**Complexity:** Medium
**Impact:** MEDIUM - Enables real data storage

**Current Status:**
- ✅ Aurora PostgreSQL infrastructure ready
- ✅ Database connection code ready (`backend/app/core/database.py`)
- ❌ **No SQLAlchemy models created**
- ❌ **No Alembic migrations**

#### Models Needed

**File: `bedrock/backend/app/models/session.py`**

```python
from datetime import datetime
from sqlalchemy import String, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Session(Base):
    """Customer conversation session."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(20))  # sms, voice, chat
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, completed, expired
    context: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
```

**File: `bedrock/backend/app/models/conversation.py`**

```python
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Message(Base):
    """Individual message in conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    agent_id: Mapped[str] = mapped_column(String(100), nullable=True)
    action_invoked: Mapped[str] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**File: `bedrock/backend/app/models/appointment.py`**

```python
from datetime import datetime, date, time
from sqlalchemy import String, DateTime, Date, Time, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Appointment(Base):
    """Customer appointments."""

    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(100), index=True)
    project_id: Mapped[str] = mapped_column(String(100), index=True)
    project_type: Mapped[str] = mapped_column(String(50))

    appointment_date: Mapped[date] = mapped_column(Date, index=True)
    appointment_time: Mapped[time] = mapped_column(Time)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)

    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled, confirmed, completed, cancelled
    confirmation_code: Mapped[str] = mapped_column(String(50), unique=True)

    notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**File: `bedrock/backend/app/models/customer.py`**

```python
from datetime import datetime
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Customer(Base):
    """Customer information."""

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=True)

    preferences: Mapped[str] = mapped_column(Text, nullable=True)  # JSON string

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**File: `bedrock/backend/app/models/__init__.py`**

```python
from app.models.session import Session
from app.models.conversation import Message
from app.models.appointment import Appointment
from app.models.customer import Customer

__all__ = ["Session", "Message", "Appointment", "Customer"]
```

#### Create Alembic Migration

```bash
cd bedrock/backend

# Initialize Alembic (if not already done)
alembic init alembic

# Edit alembic.ini to point to your database
# Then create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

**Expected Time:** 3-4 hours

---

### Priority 4: Build Simple Web Chat Interface ⭐⭐

**Time Required:** 4-6 hours
**Complexity:** Medium
**Impact:** MEDIUM - Provides a working demo channel

Create a simple HTML/JavaScript chat interface that calls your Bedrock Agent.

**File: `bedrock/frontend/chat.html`**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Scheduling Agent Chat</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
        }
        #chat-container {
            border: 1px solid #ccc;
            height: 400px;
            overflow-y: scroll;
            padding: 10px;
            margin-bottom: 10px;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }
        .user-message {
            background: #007bff;
            color: white;
            text-align: right;
        }
        .agent-message {
            background: #f0f0f0;
        }
        #input-container {
            display: flex;
            gap: 10px;
        }
        #user-input {
            flex: 1;
            padding: 10px;
            font-size: 16px;
        }
        #send-button {
            padding: 10px 20px;
            background: #007bff;
            color: white;
            border: none;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>Scheduling Agent Chat</h1>
    <div id="chat-container"></div>
    <div id="input-container">
        <input type="text" id="user-input" placeholder="Type your message...">
        <button id="send-button">Send</button>
    </div>

    <script>
        const chatContainer = document.getElementById('chat-container');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');

        let sessionId = 'web-' + Date.now();

        function addMessage(text, isUser) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user-message' : 'agent-message');
            div.textContent = text;
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message) return;

            addMessage(message, true);
            userInput.value = '';

            try {
                const response = await fetch('YOUR_API_GATEWAY_URL/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        session_id: sessionId
                    })
                });

                const data = await response.json();
                addMessage(data.response, false);
            } catch (error) {
                addMessage('Error: ' + error.message, false);
            }
        }

        sendButton.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        addMessage('Hello! How can I help you schedule an appointment today?', false);
    </script>
</body>
</html>
```

**Backend API Handler:**

```python
# bedrock/backend/app/api/routes.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import boto3

router = APIRouter()

bedrock = boto3.client('bedrock-agent-runtime', region_name='ap-south-1')

class ChatRequest(BaseModel):
    message: str
    session_id: str

@router.post("/chat")
async def chat(request: ChatRequest):
    response = bedrock.invoke_agent(
        agentId='5VTIWONUMO',
        agentAliasId='HH2U7EZXMW',
        sessionId=request.session_id,
        inputText=request.message
    )

    # Extract response from Bedrock
    agent_response = ""
    for event in response['completion']:
        if 'chunk' in event:
            agent_response += event['chunk']['bytes'].decode()

    return {"response": agent_response}
```

**Expected Time:** 4-6 hours

---

### Priority 5: Set Up Monitoring & Observability ⭐

**Time Required:** 2-3 hours
**Complexity:** Low
**Impact:** MEDIUM - Essential for production

#### CloudWatch Dashboard

Create a dashboard to monitor your Bedrock Agents and Lambda functions.

```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name scheduling-agent-dashboard \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "properties": {
          "metrics": [
            ["AWS/Bedrock", "InvokeAgent", {"stat": "Sum"}]
          ],
          "period": 300,
          "stat": "Sum",
          "region": "ap-south-1",
          "title": "Bedrock Agent Invocations"
        }
      },
      {
        "type": "metric",
        "properties": {
          "metrics": [
            ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
            [".", "Errors", {"stat": "Sum"}],
            [".", "Duration", {"stat": "Average"}]
          ],
          "period": 300,
          "stat": "Average",
          "region": "ap-south-1",
          "title": "Lambda Metrics"
        }
      }
    ]
  }'
```

#### Set Up Alarms

```bash
# Lambda errors alarm
aws cloudwatch put-metric-alarm \
  --alarm-name scheduling-lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1

# Bedrock throttling alarm
aws cloudwatch put-metric-alarm \
  --alarm-name bedrock-throttles \
  --alarm-description "Alert on Bedrock throttling" \
  --metric-name ThrottledRequests \
  --namespace AWS/Bedrock \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

**Expected Time:** 2-3 hours

---

## 📊 Priority Summary (What to Do in Order)

| Priority | Task | Time | Impact | Blocking? |
|----------|------|------|--------|-----------|
| **1** | Deploy Lambda to AWS | 2 hrs | HIGH | Yes (for 2) |
| **2** | Connect Lambda to Bedrock | 1-2 hrs | HIGH | No |
| **3** | Create database models | 3-4 hrs | MEDIUM | No |
| **4** | Build web chat UI | 4-6 hrs | MEDIUM | No |
| **5** | Set up monitoring | 2-3 hrs | MEDIUM | No |

**Total Time:** 12-17 hours (1.5-2 working days)

---

## 🚀 Quick Wins (Can Do Today)

### Option A: Deploy Lambda Functions (2 hours)

**This unblocks everything else** and makes your Bedrock Agents actually functional.

**Steps:**
1. Package Lambda ZIP files (30 min)
2. Create IAM role (10 min)
3. Deploy 3 Lambda functions (30 min)
4. Test each function (30 min)
5. Update Bedrock action groups (20 min)

**Result:** Your Bedrock Agents can now take real actions!

---

### Option B: Create Database Models (3-4 hours)

**Enables real data persistence** instead of just mock data.

**Steps:**
1. Create 4 model files (2 hrs)
2. Set up Alembic (30 min)
3. Create migration (30 min)
4. Apply to database (30 min)

**Result:** You can store real customer sessions, appointments, messages!

---

### Option C: Build Web Chat (4-6 hours)

**Provides a working demo** before voice is ready.

**Steps:**
1. Create HTML chat UI (2 hrs)
2. Build FastAPI backend (2 hrs)
3. Deploy to API Gateway (1 hr)
4. Test end-to-end (1 hr)

**Result:** Working web chat interface to demo the system!

---

## 💡 My Recommendation

**Do Priority 1 TODAY (2 hours):**

Deploy Lambda functions to AWS and connect to Bedrock. This is the **biggest missing piece** and makes everything else more valuable.

**Then tomorrow:**
- Build web chat UI (gives you a working demo channel)
- OR create database models (enables real data storage)

**Result in 2 days:**
- ✅ Fully functional Bedrock Agents with Lambda
- ✅ Working demo (web chat OR real database)
- ✅ Ready for voice integration when Twilio is set up

---

## 📝 Step-by-Step Guide for Priority 1 (Deploy Lambda)

I can create a detailed deployment script that you can run right now to get your Lambda functions deployed in 1-2 hours.

**Want me to:**
1. Create a deployment automation script?
2. Walk you through manual deployment?
3. Create Terraform for Lambda deployment?

Let me know and I'll create the detailed guide!

---

**Document Version:** 1.0
**Last Updated:** October 17, 2025
**Next Action:** Deploy Lambda functions (Priority 1)
