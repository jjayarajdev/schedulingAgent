# Production Web Application Deployment Guide
**For Bedrock Multi-Agent System**
**Date**: November 5, 2025

---

## 📋 Table of Contents
1. [Current State Analysis](#current-state-analysis)
2. [Architecture Options](#architecture-options)
3. [Recommended Architecture](#recommended-architecture)
4. [Testing Current Setup](#testing-current-setup)
5. [Production Deployment Steps](#production-deployment-steps)
6. [Security & Authentication](#security--authentication)
7. [Scaling & Performance](#scaling--performance)

---

## 🔍 Current State Analysis

### What You Have

#### 1. **Backend** (`backend/app.py`)
- **Type**: Flask Python server
- **Features**:
  - Bedrock agent invocation
  - Intent-based routing to specialist agents
  - Session management
  - CORS enabled
  - Environment-based configuration (dev/staging/prod)
- **API Endpoints**:
  - `/api/user` - Get user data
  - `/api/chat/simple` - Simple chat (non-streaming)
  - `/api/chat/stream` - Streaming chat responses
  - `/api/session` - Session management
- **Status**: ✅ **Production-ready** with minor enhancements needed

#### 2. **Frontend** (`frontend/`)
- **Type**: React + TypeScript + Vite
- **Features**:
  - Chat interface
  - Project display
  - User context
  - Sample queries
- **Status**: ✅ **Production-ready** but needs ProjectForce API integration

#### 3. **Testing UI** (`testing/ui/`)
- **`pf_auth_demo.html`**: Simple HTML demo with ProjectForce API integration
- **`auth_proxy.py`**: Flask proxy for CORS during testing
- **Status**: ✅ **Works** for testing, not for production

---

## 🏗️ Architecture Options

### Option 1: Simple Deployment (Current Stack)
```
[User Browser]
    ↓
[React Frontend (Static Files on S3/CloudFront)]
    ↓ API calls
[Flask Backend (EC2/ECS/Lambda)]
    ↓
[AWS Bedrock Agents]
    ↓
[Lambda Functions → ProjectForce API]
```

**Pros**:
- Uses your existing code
- Simple to deploy
- Low cost

**Cons**:
- Flask not as scalable as AWS native services
- Requires server maintenance

### Option 2: AWS Native (Recommended for Production)
```
[User Browser]
    ↓
[React Frontend (S3 + CloudFront)]
    ↓
[API Gateway]
    ↓
[Lambda Backend (Python)]
    ↓
[AWS Bedrock Agents]
    ↓
[Lambda Functions → ProjectForce API]
```

**Pros**:
- Serverless = auto-scaling
- No server maintenance
- Pay-per-use
- Built-in SSL/security

**Cons**:
- More AWS services to manage
- Slightly more complex initial setup

### Option 3: Containerized (Best for Complex Apps)
```
[User Browser]
    ↓
[React Frontend (S3 + CloudFront)]
    ↓
[Application Load Balancer]
    ↓
[ECS/Fargate (Flask Backend Container)]
    ↓
[AWS Bedrock Agents]
    ↓
[Lambda Functions → ProjectForce API]
```

**Pros**:
- Easy to scale
- Can run anywhere (AWS, on-prem, other clouds)
- Good for microservices

**Cons**:
- More complex
- Higher cost than serverless

---

## ✅ Recommended Architecture

**For your use case, I recommend Option 2 (AWS Native) with these components**:

```
┌─────────────────────────────────────────────────────────────┐
│                        User Browser                          │
│              (Web App or Mobile App)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTPS
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  CloudFront + S3                            │
│           (React Frontend - Static Hosting)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ REST API
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway                              │
│  - Authentication (Cognito/IAM)                            │
│  - Rate limiting                                            │
│  - Request validation                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Lambda Invoke
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              Backend Lambda Function                        │
│  - Chat endpoint handler                                    │
│  - Session management (DynamoDB)                           │
│  - Intent routing logic                                     │
│  - User context injection                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ InvokeAgent API
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                AWS Bedrock Agents                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│  │ Supervisor │  │ Scheduling │  │Information │          │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘          │
│         │ Collaborate   │                │                 │
│         └───────────────┴────────────────┘                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Action Group → Lambda
                       ↓
┌─────────────────────────────────────────────────────────────┐
│          Agent Action Lambda Functions                      │
│  - pf-scheduling-actions                                    │
│  - pf-information-actions                                   │
│  - pf-chitchat-actions                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTPS
                       ↓
┌─────────────────────────────────────────────────────────────┐
│             ProjectForce API                                │
│  (https://api-cx-portal.dev.projectsforce.com)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing Current Setup

### Step 1: Test the Simple HTML Demo

**This works RIGHT NOW!**

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/testing/ui
./launch_auth_demo.sh
```

**What it does**:
1. Starts Flask proxy on port 5003
2. Opens `pf_auth_demo.html` in browser
3. Uses ProjectForce API credentials from LocalStorage

**Test queries**:
- "show me my projects"
- "what is the weather in New York?"
- "tell me a joke"

### Step 2: Test the Flask Backend + React Frontend

**2a. Start the Flask backend**:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend

# Install dependencies
pip3 install -r requirements.txt

# Set environment (dev, staging, or prod)
export ENVIRONMENT=dev

# Run the backend
python3 app.py
```

Backend will run on: `http://localhost:5000`

**2b. Start the React frontend**:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Frontend will run on: `http://localhost:5173`

**Test it**:
1. Open `http://localhost:5173` in browser
2. Try sample queries
3. Check browser console for errors
4. Check Flask logs in terminal

### Step 3: Test with Real ProjectForce API

**Update backend to use real ProjectForce API**:

Edit `backend/agent_config.dev.json`:
```json
{
  "supervisor_id": "YOUR_SUPERVISOR_AGENT_ID",
  "supervisor_alias": "YOUR_SUPERVISOR_ALIAS_ID",
  "region": "us-east-1",
  "agents": {
    "scheduling": {
      "agent_id": "YOUR_SCHEDULING_AGENT_ID",
      "alias_id": "YOUR_SCHEDULING_ALIAS_ID"
    },
    "information": {
      "agent_id": "YOUR_INFORMATION_AGENT_ID",
      "alias_id": "YOUR_INFORMATION_ALIAS_ID"
    },
    "chitchat": {
      "agent_id": "YOUR_CHITCHAT_AGENT_ID",
      "alias_id": "YOUR_CHITCHAT_ALIAS_ID"
    }
  },
  "routing": {
    "enabled": true,
    "use_supervisor": false
  }
}
```

Get agent IDs from:
```bash
cat /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/config/agent_ids.json
```

---

## 🚀 Production Deployment Steps

### Phase 1: Prepare Backend for Lambda

**Create a Lambda-compatible version of app.py**:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/backend
```

**Create `lambda_handler.py`**:
```python
#!/usr/bin/env python3
"""
AWS Lambda handler for Bedrock Agent Chat API
Converts Flask app.py to Lambda handler
"""

import json
import os
import boto3
from typing import Dict, Any

# Import your existing logic from app.py
# (You'll need to refactor app.py to extract the core logic)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for API Gateway proxy integration
    """
    # Parse API Gateway event
    http_method = event.get('httpMethod')
    path = event.get('path')
    body = json.loads(event.get('body', '{}'))

    # Route based on path
    if path == '/api/chat/simple':
        return handle_chat_simple(body)
    elif path == '/api/chat/stream':
        return handle_chat_stream(body)
    elif path == '/api/user':
        return handle_get_user()
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Not found'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

def handle_chat_simple(body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle simple chat request"""
    message = body.get('message', '')
    session_id = body.get('session_id', f"session-{int(time.time())}")

    # Your Bedrock invocation logic here
    # ...

    return {
        'statusCode': 200,
        'body': json.dumps({
            'response': response_text,
            'session_id': session_id
        }),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    }

# ... other handler functions
```

### Phase 2: Deploy Backend to Lambda

**Create deployment package**:

```bash
#!/bin/bash
# deploy_backend_lambda.sh

cd backend/

# Create deployment package
mkdir -p lambda_package
cp lambda_handler.py lambda_package/
cp agent_config.json lambda_package/
pip3 install -r requirements.txt -t lambda_package/

# Create zip
cd lambda_package/
zip -r ../backend_lambda.zip .
cd ..

# Deploy to Lambda
aws lambda create-function \
    --function-name pf-chat-backend \
    --runtime python3.11 \
    --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-bedrock-role \
    --handler lambda_handler.lambda_handler \
    --zip-file fileb://backend_lambda.zip \
    --timeout 30 \
    --memory-size 512 \
    --environment Variables="{ENVIRONMENT=prod}"
```

### Phase 3: Setup API Gateway

**Create REST API**:

```bash
# Create API
aws apigateway create-rest-api \
    --name "ProjectForce-Chat-API" \
    --description "Bedrock Agent Chat API"

# Create resources and methods
# /api/chat/simple (POST)
# /api/chat/stream (POST)
# /api/user (GET)

# Integrate with Lambda
# Enable CORS
# Deploy to stage (dev, staging, prod)
```

**Or use AWS Console**:
1. Go to API Gateway
2. Create REST API
3. Create resources: `/api/chat/simple`, `/api/chat/stream`, `/api/user`
4. For each resource, add POST/GET method
5. Integration type: Lambda Function
6. Select `pf-chat-backend`
7. Enable CORS
8. Deploy API to stage

### Phase 4: Deploy Frontend to S3 + CloudFront

**Build React app**:

```bash
cd frontend/

# Update API endpoint in vite.config.ts
# Point to your API Gateway URL

# Build for production
npm run build

# Deploy to S3
aws s3 sync dist/ s3://projectforce-chat-frontend/

# Create CloudFront distribution (one-time)
aws cloudfront create-distribution \
    --origin-domain-name projectforce-chat-frontend.s3.amazonaws.com \
    --default-root-object index.html
```

### Phase 5: Setup Authentication (Cognito)

**Create User Pool**:

```bash
aws cognito-idp create-user-pool \
    --pool-name ProjectForceUsers \
    --policies "PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true}"

# Create app client
aws cognito-idp create-user-pool-client \
    --user-pool-id YOUR_POOL_ID \
    --client-name ProjectForceChatApp
```

**Integrate with API Gateway**:
1. Create Cognito authorizer in API Gateway
2. Attach to API methods
3. Update frontend to use Cognito SDK for auth

---

## 🔒 Security & Authentication

### Current Issues to Fix

1. **No Authentication**: Anyone can call your API
2. **Hardcoded Credentials**: ProjectForce API tokens in code
3. **No Rate Limiting**: Can be abused

### Production Security Checklist

- [ ] Use AWS Cognito for user authentication
- [ ] Store ProjectForce API credentials in AWS Secrets Manager
- [ ] Enable API Gateway rate limiting (1000 requests/minute)
- [ ] Use IAM roles instead of access keys
- [ ] Enable CloudFront WAF for DDoS protection
- [ ] Implement request signing
- [ ] Add input validation
- [ ] Enable CloudWatch logging
- [ ] Set up AWS GuardDuty
- [ ] Use HTTPS only (enforce TLS 1.2+)

### Quick Security Fix (Before Production)

**Move API credentials to Secrets Manager** (already done for Lambda!):

```bash
# Your Lambda functions already use Secrets Manager!
# Secret: projectforce/api/credentials

# Update backend to use same approach:
import boto3
import json

def get_projectforce_credentials():
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name='us-east-1'
    )
    secret = client.get_secret_value(SecretId='projectforce/api/credentials')
    return json.loads(secret['SecretString'])
```

---

## 📊 Scaling & Performance

### Current Capacity

With your setup:
- **Lambda Functions**: Auto-scale to 1000 concurrent executions
- **Bedrock Agents**: Auto-scale (managed by AWS)
- **API Gateway**: 10,000 requests/second default
- **DynamoDB**: 40,000 read/write units (auto-scaling)

### Optimization Tips

1. **Enable API Gateway Caching**: Cache GET requests (user data, etc.)
2. **Use CloudFront**: CDN for frontend + API caching
3. **Implement Connection Pooling**: Reuse Bedrock/Lambda connections
4. **Add ElastiCache**: Cache frequent queries (projects, user data)
5. **Enable Lambda Provisioned Concurrency**: Pre-warm functions for faster response
6. **Use WebSocket API**: For real-time streaming chat (instead of HTTP polling)

### Cost Estimates (Monthly)

**For 10,000 users, 100,000 chat messages/month**:

- Lambda (Backend): $50
- Bedrock Agents: $100-200 (depends on tokens)
- API Gateway: $35
- S3 + CloudFront: $20
- DynamoDB: $25
- Secrets Manager: $1
- **Total**: ~$230-330/month

---

## 🎯 Quick Start Production Checklist

### Week 1: Testing & Preparation
- [ ] Test Flask backend locally with Bedrock agents
- [ ] Test React frontend with Flask backend
- [ ] Verify ProjectForce API integration works
- [ ] Review security requirements
- [ ] Get AWS account/permissions ready

### Week 2: Lambda Migration
- [ ] Convert app.py to lambda_handler.py
- [ ] Test Lambda function locally (sam local)
- [ ] Deploy Lambda function
- [ ] Test Lambda with API Gateway locally

### Week 3: Infrastructure Setup
- [ ] Create API Gateway
- [ ] Setup Cognito (if needed)
- [ ] Configure S3 bucket for frontend
- [ ] Create CloudFront distribution
- [ ] Setup custom domain (optional)

### Week 4: Deployment & Testing
- [ ] Deploy frontend to S3
- [ ] Configure API Gateway endpoints
- [ ] Test end-to-end in staging
- [ ] Load testing
- [ ] Security review
- [ ] Deploy to production
- [ ] Monitor for 1 week

---

## 📞 Next Steps

**Choose your deployment approach**:

1. **Quick Test** (Today):
   ```bash
   cd testing/ui && ./launch_auth_demo.sh
   ```

2. **Local Development** (This Week):
   ```bash
   # Terminal 1: Backend
   cd backend && python3 app.py

   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

3. **Production Deployment** (Next 2-4 Weeks):
   - Follow the Phase 1-5 deployment steps
   - Use provided scripts and AWS CLI commands
   - Test thoroughly in staging first

**Need Help?** See:
- `/scripts/deployment/DEPLOYMENT_GUIDE.md` - Infrastructure deployment
- `/testing/ui/TEST_UI_README.md` - Testing guide
- `/backend/PROJECT_API_REFERENCE.md` - API documentation

---

## 🔗 Useful Links

- **AWS Bedrock Documentation**: https://docs.aws.amazon.com/bedrock/
- **API Gateway Setup**: https://docs.aws.amazon.com/apigateway/
- **React + Vite Deployment**: https://vitejs.dev/guide/static-deploy.html
- **Flask on Lambda**: https://github.com/aws/serverless-application-model

---

**Last Updated**: November 5, 2025
**Version**: 1.0
**Status**: Ready for production deployment planning
