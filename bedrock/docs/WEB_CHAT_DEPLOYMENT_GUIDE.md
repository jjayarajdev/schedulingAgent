# Web Chat Deployment Guide

Complete guide for deploying the web chat interface with FastAPI backend.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

The web chat interface provides a beautiful, modern UI for interacting with the Bedrock scheduling agent. It consists of:

1. **Frontend**: Self-contained HTML/CSS/JS chat interface (`frontend/index.html`)
2. **Backend**: FastAPI application with Bedrock Agent integration (`backend/app/`)
3. **Database**: PostgreSQL for session and message storage
4. **Cache**: Redis for session state management

**Key Features:**
- ✅ Modern, responsive UI with gradient design
- ✅ Real-time typing indicators
- ✅ Session persistence across page reloads
- ✅ Full conversation history
- ✅ Quick action buttons for common tasks
- ✅ Error handling and status indicators
- ✅ Direct integration with Bedrock Supervisor Agent

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Web Browser (index.html)                    │  │
│  │  - Session Management (localStorage)                  │  │
│  │  - Message Display & Formatting                       │  │
│  │  - User Input Handling                                │  │
│  │  - API Communication                                  │  │
│  └───────────────────┬──────────────────────────────────┘  │
│                      │ HTTP POST /api/chat                 │
└──────────────────────┼─────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────┐
│                     API Gateway Layer                        │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         FastAPI Backend (app/main.py)                 │  │
│  │                                                        │  │
│  │  Routes:                                              │  │
│  │  • POST /api/chat      - Process message             │  │
│  │  • GET  /api/health    - Health check                │  │
│  │  • GET  /api/sessions  - Session info                │  │
│  │                                                        │  │
│  │  Middleware:                                          │  │
│  │  • CORS handling                                      │  │
│  │  • Error handling                                     │  │
│  │  • Request validation                                 │  │
│  └───────────────────┬──────────────────────────────────┘  │
└──────────────────────┼─────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────┐
│                   Business Logic Layer                       │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │     Bedrock Agent Client (core/bedrock_agent.py)    │   │
│  │                                                       │   │
│  │  • Agent invocation with session management         │   │
│  │  • Response parsing                                  │   │
│  │  • Error handling & retries                          │   │
│  └───────────────────┬─────────────────────────────────┘   │
└──────────────────────┼─────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────┐
│                    Data Access Layer                         │
│                                                               │
│  ┌──────────────────┐         ┌───────────────────────┐    │
│  │   PostgreSQL     │         │      Redis Cache       │    │
│  │                  │         │                        │    │
│  │  Tables:         │         │  • Session state       │    │
│  │  • sessions      │         │  • Rate limiting       │    │
│  │  • messages      │         │  • Temporary data      │    │
│  │  • customers     │         └────────────────────────┘    │
│  │  • appointments  │                                        │
│  └──────────────────┘                                        │
└──────────────────────┼─────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────┐
│                    AWS Bedrock Layer                         │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │    Supervisor Agent (5VTIWONUMO)                      │  │
│  │    Alias: HH2U7EZXMW                                  │  │
│  │                                                        │  │
│  │    Collaborators:                                     │  │
│  │    ├── Scheduling Agent (IX24FSMTQH)                 │  │
│  │    ├── Information Agent (C9ANXRIO8Y)                │  │
│  │    ├── Notes Agent (G5BVBYEPUM)                      │  │
│  │    └── Chitchat Agent (UQQQ3OXYB0)                   │  │
│  │                                                        │  │
│  │    Lambda Actions (12 total):                        │  │
│  │    • list_projects, get_time_slots, etc.             │  │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

- **Python 3.11+**
- **PostgreSQL 14+** (or Aurora Serverless v2)
- **Redis 6+** (or ElastiCache)
- **AWS CLI** configured with credentials
- **Modern web browser** (Chrome 90+, Firefox 88+, Safari 14+)

### AWS Resources

- ✅ Bedrock Agent deployed (Supervisor: `5VTIWONUMO`)
- ✅ Lambda functions deployed (12 actions)
- ✅ IAM role with permissions:
  - `bedrock-agent-runtime:InvokeAgent`
  - `secretsmanager:GetSecretValue`
  - `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### Environment Variables

Create `backend/.env` file:

```bash
# Application
APP_NAME=scheduling-agent-bedrock
ENVIRONMENT=dev
DEBUG=false
PORT=8000
HOST=0.0.0.0

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scheduling
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_SESSION_TTL=1800

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Bedrock Agent
BEDROCK_AGENT_ID=5VTIWONUMO
BEDROCK_AGENT_ALIAS_ID=HH2U7EZXMW
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0

# PF360 API
CUSTOMER_SCHEDULER_API_URL=https://api.projectsforce.com
PF360_API_TIMEOUT=30
PF360_MAX_RETRIES=3

# Security
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
SECRET_KEY=your-secret-key-change-in-production

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## Local Development

### Step 1: Initialize Database

Run the database initialization script:

```bash
cd bedrock

# Ensure DATABASE_URL is set
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/scheduling"

# Run initialization
./scripts/init_database.sh
```

**Expected output:**
```
================================================
Database Initialization Complete!
================================================

Database Tables:
  1. sessions - Conversation sessions
  2. messages - Chat messages
  3. conversation_summaries - Conversation analytics
  4. appointments - Scheduled appointments
  5. customers - Customer profiles

All done! 🎉
```

### Step 2: Start Backend

```bash
cd bedrock/backend

# Install dependencies
pip install -r requirements.txt

# OR use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run backend
python3 -m app.main
```

**Backend starts at:** `http://localhost:8000`

**Verify it's running:**
```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "timestamp": "2025-10-17T12:00:00Z",
  "checks": {
    "database": "healthy"
  }
}
```

### Step 3: Open Chat Interface

**Option 1: Direct file open (simplest)**
```bash
open bedrock/frontend/index.html
```

**Option 2: Local HTTP server**
```bash
cd bedrock/frontend
python3 -m http.server 3000
```

Then visit: `http://localhost:3000`

### Step 4: Test Chat

1. Click "Schedule Appointment" quick action
2. Or type: "I want to schedule an appointment"
3. Follow the conversation flow
4. Agent will guide you through scheduling

---

## Production Deployment

### Option 1: AWS Elastic Beanstalk + S3

**Best for:** Quick deployment with minimal configuration

#### Backend Deployment

```bash
cd bedrock/backend

# Install EB CLI
pip install awsebcli

# Initialize Elastic Beanstalk
eb init -p python-3.11 scheduling-agent-backend --region us-east-1

# Create environment
eb create scheduling-agent-prod \
  --instance-type t3.medium \
  --envvars \
    BEDROCK_AGENT_ID=5VTIWONUMO,\
    BEDROCK_AGENT_ALIAS_ID=HH2U7EZXMW,\
    DATABASE_URL=$DATABASE_URL,\
    REDIS_URL=$REDIS_URL

# Deploy
eb deploy
```

#### Frontend Deployment

```bash
cd bedrock/frontend

# Update API_BASE_URL in index.html
# Change: const API_BASE_URL = 'http://localhost:8000/api';
# To: const API_BASE_URL = 'https://your-backend.elasticbeanstalk.com/api';

# Create S3 bucket
aws s3 mb s3://scheduling-agent-frontend

# Enable static website hosting
aws s3 website s3://scheduling-agent-frontend \
  --index-document index.html

# Upload files
aws s3 cp index.html s3://scheduling-agent-frontend/ --acl public-read

# Create CloudFront distribution (optional, for HTTPS + CDN)
aws cloudfront create-distribution \
  --origin-domain-name scheduling-agent-frontend.s3.amazonaws.com
```

**Access:** `https://your-cloudfront-url`

---

### Option 2: AWS Lambda + API Gateway + S3

**Best for:** Serverless, cost-effective, auto-scaling

#### Backend Deployment (Lambda)

Create `backend/lambda_handler.py`:

```python
from mangum import Mangum
from app.main import app

handler = Mangum(app)
```

Deploy with AWS SAM:

```bash
cd bedrock/backend

# Create SAM template
cat > template.yaml << 'EOF'
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  SchedulingAgentAPI:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: scheduling-agent-api
      Runtime: python3.11
      Handler: lambda_handler.handler
      CodeUri: .
      MemorySize: 1024
      Timeout: 30
      Environment:
        Variables:
          BEDROCK_AGENT_ID: 5VTIWONUMO
          BEDROCK_AGENT_ALIAS_ID: HH2U7EZXMW
          DATABASE_URL: !Ref DatabaseURL
          REDIS_URL: !Ref RedisURL
      Policies:
        - AWSLambdaVPCAccessExecutionRole
        - Statement:
          - Effect: Allow
            Action:
              - bedrock-agent-runtime:InvokeAgent
            Resource: '*'
      Events:
        ApiEvent:
          Type: Api
          Properties:
            Path: /{proxy+}
            Method: ANY

Outputs:
  ApiUrl:
    Description: "API Gateway endpoint URL"
    Value: !Sub "https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/"
EOF

# Build and deploy
sam build
sam deploy --guided
```

**Get API URL:**
```bash
aws cloudformation describe-stacks \
  --stack-name scheduling-agent-api \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text
```

#### Frontend Deployment (same as Option 1)

---

### Option 3: Docker + ECS Fargate

**Best for:** Full control, containerized deployment

#### Create Dockerfile

`backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ app/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Build and Push

```bash
cd bedrock/backend

# Build image
docker build -t scheduling-agent-backend .

# Tag for ECR
docker tag scheduling-agent-backend:latest \
  123456789012.dkr.ecr.us-east-1.amazonaws.com/scheduling-agent:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789012.dkr.ecr.us-east-1.amazonaws.com

docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/scheduling-agent:latest
```

#### Deploy to ECS Fargate

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name scheduling-agent-cluster

# Create task definition (see ECS docs)
# Create service
aws ecs create-service \
  --cluster scheduling-agent-cluster \
  --service-name scheduling-agent-service \
  --task-definition scheduling-agent-task \
  --desired-count 2 \
  --launch-type FARGATE \
  --load-balancers targetGroupArn=$TARGET_GROUP_ARN,containerName=backend,containerPort=8000
```

---

## Configuration

### Backend Configuration

#### CORS Settings

Edit `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend-domain.com",  # Production frontend
        "http://localhost:3000",             # Local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

#### Database Connection Pooling

For production, increase pool size in `backend/.env`:

```bash
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20
```

#### Logging

Configure structured JSON logging for CloudWatch:

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_TRACING=true
```

### Frontend Configuration

#### API Endpoint

Edit `frontend/index.html`:

```javascript
// Development
const API_BASE_URL = 'http://localhost:8000/api';

// Production
const API_BASE_URL = 'https://api.your-domain.com/api';
```

#### Branding

Customize colors:

```css
/* Change gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

---

## Testing

### 1. Health Check

```bash
curl http://localhost:8000/api/health
```

Expected:
```json
{
  "status": "ok",
  "timestamp": "2025-10-17T12:00:00Z",
  "checks": {
    "database": "healthy"
  }
}
```

### 2. Chat API Test

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "session_id": "test-session-123",
    "customer_id": "1645975",
    "client_name": "test"
  }'
```

Expected:
```json
{
  "response": "Hello! I'm your scheduling assistant...",
  "session_id": "test-session-123",
  "metadata": {
    "processing_time_ms": 850
  }
}
```

### 3. End-to-End Test

Open browser console and run:

```javascript
// Test message sending
fetch('http://localhost:8000/api/chat', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    message: 'I want to schedule an appointment',
    session_id: 'e2e-test-' + Date.now(),
    customer_id: '1645975',
    client_name: 'web-chat'
  })
})
.then(r => r.json())
.then(console.log);
```

---

## Troubleshooting

### Issue: "Failed to send message"

**Symptoms:**
- Red error banner in chat
- Browser console shows network error

**Solutions:**

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **Check CORS configuration:**
   - Open browser DevTools > Network tab
   - Look for CORS errors
   - Verify `allow_origins` in `main.py`

3. **Check firewall:**
   ```bash
   # Test from command line
   curl -v http://localhost:8000/api/chat
   ```

### Issue: Database connection failed

**Symptoms:**
- Backend logs: "database_connection_failed"
- Health check shows database unhealthy

**Solutions:**

1. **Verify DATABASE_URL:**
   ```bash
   echo $DATABASE_URL
   # Should be: postgresql+asyncpg://...
   ```

2. **Test PostgreSQL connection:**
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

3. **Check database migrations:**
   ```bash
   cd backend
   alembic current
   ```

### Issue: Agent not responding

**Symptoms:**
- Messages sent but no response
- Backend logs: "bedrock_agent_invocation_failed"

**Solutions:**

1. **Verify agent IDs:**
   ```bash
   echo $BEDROCK_AGENT_ID
   echo $BEDROCK_AGENT_ALIAS_ID
   ```

2. **Test agent directly:**
   ```bash
   aws bedrock-agent-runtime invoke-agent \
     --agent-id 5VTIWONUMO \
     --agent-alias-id HH2U7EZXMW \
     --session-id test-123 \
     --input-text "Hello" \
     --region us-east-1
   ```

3. **Check IAM permissions:**
   ```bash
   aws iam get-role-policy \
     --role-name your-lambda-role \
     --policy-name BedrockAgentPolicy
   ```

### Issue: Session not persisting

**Symptoms:**
- Conversation resets on page reload
- Session ID changes

**Solutions:**

1. **Check localStorage:**
   ```javascript
   // In browser console
   localStorage.getItem('chat_session_id')
   ```

2. **Clear and regenerate:**
   ```javascript
   localStorage.clear();
   location.reload();
   ```

---

## Performance Optimization

### 1. Database Query Optimization

Add indexes for common queries:

```sql
CREATE INDEX CONCURRENTLY idx_messages_session_created
ON messages(session_id, created_at DESC);
```

### 2. Redis Caching

Cache session data:

```python
# In app/api/chat.py
session_cache_key = f"session:{session_id}"
cached_session = await redis.get(session_cache_key)
```

### 3. Connection Pooling

Increase pool size for high traffic:

```bash
DATABASE_POOL_SIZE=100
DATABASE_MAX_OVERFLOW=50
```

### 4. CDN for Frontend

Use CloudFront for global distribution:

```bash
aws cloudfront create-distribution \
  --origin-domain-name your-s3-bucket.s3.amazonaws.com \
  --default-cache-behavior MinTTL=86400
```

---

## Security Checklist

- [ ] HTTPS enabled for all endpoints
- [ ] CORS restricted to specific origins
- [ ] Environment variables not in code
- [ ] Database credentials in Secrets Manager
- [ ] IAM roles follow least privilege
- [ ] Input validation on all endpoints
- [ ] Rate limiting configured
- [ ] SQL injection prevention (using SQLAlchemy)
- [ ] XSS prevention (using CSP headers)
- [ ] Session timeout configured (30 minutes)

---

## Monitoring

See [MONITORING_SETUP_GUIDE.md](./MONITORING_SETUP_GUIDE.md) for complete monitoring setup.

**Quick setup:**

```bash
# CloudWatch Log Groups
aws logs create-log-group --log-group-name /aws/scheduling-agent/backend

# CloudWatch Alarms
aws cloudwatch put-metric-alarm \
  --alarm-name high-error-rate \
  --metric-name Errors \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

---

## Next Steps

1. ✅ Deploy backend to AWS Lambda/ECS
2. ✅ Deploy frontend to S3 + CloudFront
3. ✅ Set up monitoring and alarms
4. ⏳ Add WebSocket support for streaming
5. ⏳ Add authentication (Cognito/Auth0)
6. ⏳ Add file upload capability
7. ⏳ Implement voice input/output

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [AWS Bedrock Agents Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Uvicorn Deployment](https://www.uvicorn.org/deployment/)
