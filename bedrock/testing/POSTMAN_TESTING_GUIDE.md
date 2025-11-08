# ProjectForce Scheduling Agent API - Postman Testing Guide

Complete guide for testing the ProjectForce Scheduling Agent API using Postman.

## 📦 Files Included

1. **ProjectForce_Agent_API.postman_collection.json** - Main API collection with all endpoints
2. **ProjectForce_Agent_Environment.postman_environment.json** - Environment variables for local testing

## 🚀 Quick Start

### Step 1: Import into Postman

1. Open Postman
2. Click **Import** button (top left)
3. Drag and drop both JSON files:
   - `ProjectForce_Agent_API.postman_collection.json`
   - `ProjectForce_Agent_Environment.postman_environment.json`

### Step 2: Select Environment

1. In the top-right corner, select **"ProjectForce Agent - Local"** from the environment dropdown
2. Verify the environment variables:
   - `proxy_url`: http://localhost:5003
   - `user_id`: 1646085
   - `client_id`: 09PF05VD

### Step 3: Start the Proxy Server

Before testing, make sure the proxy server is running:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/testing/ui
python3 pf_proxy.py
```

You should see:
```
🚀 ProjectForce API Proxy Server
Server running on: http://localhost:5003
```

## 📋 API Collection Structure

### 1. Authentication
- **Login** - Get access token (automatically saves to environment)
- **Validate Token** - Verify token is valid

### 2. ProjectForce Dashboard API
- **Get Dashboard/Projects** - Retrieve all projects for the user

### 3. Bedrock Agent - Non-Streaming
- **Show Projects** - Get list of all projects via agent
- **Greeting** - Test chitchat agent
- **Project Details** - Get detailed information about a specific project
- **Schedule Appointment** - Schedule an appointment for a project
- **Information Query** - Test the information agent

### 4. Bedrock Agent - Streaming
- **Show Projects (Streaming)** - Real-time streaming response
- **Greeting (Streaming)** - Streaming chitchat response

### 5. Health Checks
- **Proxy Health Check** - Verify proxy server is running

## 🔑 Authentication Flow

### Automatic Token Management

The collection is set up to automatically manage your access token:

1. **Run "Login" request first**
   - The test script automatically extracts and saves the `access_token`
   - Also saves `user_id` to the environment

2. **All subsequent requests use the token**
   - Look for `{{access_token}}` in request headers
   - No need to manually copy/paste tokens

### Manual Login (if needed)

If you need to login manually or use different credentials:

```json
POST {{proxy_url}}/api/login
Content-Type: application/json

{
    "email": "jay@mailinator.com",
    "password": "Password@123"
}
```

## 🧪 Testing Workflow

### Basic Testing Flow

1. **Health Check**
   - Run "Proxy Health Check" to verify server is up

2. **Authentication**
   - Run "Login" to get access token
   - (Optional) Run "Validate Token" to verify

3. **Test Dashboard**
   - Run "Get Dashboard/Projects" to see raw project data

4. **Test Agents**
   - Run any of the "Bedrock Agent" requests
   - Try both streaming and non-streaming versions

### Example Test Scenarios

#### Scenario 1: View All Projects
```
1. Login
2. Invoke Agent - Show Projects
3. Expected: JSON response with project list
```

#### Scenario 2: Get Project Details
```
1. Login
2. Invoke Agent - Show Projects (get project IDs)
3. Invoke Agent - Project Details (use specific ID)
4. Expected: Detailed project information
```

#### Scenario 3: Schedule Appointment
```
1. Login
2. Invoke Agent - Show Projects
3. Invoke Agent - Schedule Appointment
4. Expected: Confirmation of scheduled appointment
```

#### Scenario 4: Test Streaming
```
1. Login
2. Invoke Agent - Show Projects (Streaming)
3. Expected: Server-Sent Events (SSE) stream
```

## 🔧 Environment Variables

### Collection Variables

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `proxy_url` | Proxy server URL | http://localhost:5003 |
| `access_token` | Auth token (auto-populated) | _(empty)_ |
| `user_id` | ProjectForce user ID | 1646085 |
| `client_id` | ProjectForce client ID | 09PF05VD |

### Customizing Variables

To use different values:

1. Click the environment dropdown (top-right)
2. Click the eye icon next to "ProjectForce Agent - Local"
3. Edit the values
4. Save

## 📊 Understanding Responses

### Non-Streaming Response Format

```json
{
  "response": "Agent response text here",
  "agent_name": "Supervisor Agent",
  "session_id": "test-session-123456"
}
```

### Streaming Response Format (SSE)

Streaming responses come as Server-Sent Events:

```
data: {"chunk": "Hello"}
data: {"chunk": " there!"}
data: {"done": true}
```

**Note:** Postman shows SSE responses as plain text. For better visualization, use the web UI or a tool like `curl`.

### JSON Project Response Format

When requesting projects, the agent returns:

```json
{
  "message": "You have 8 projects",
  "projects": [
    {
      "id": "7751743",
      "projectNumber": "21083_09PF05VD_1762166550719_1_1",
      "status": "Scheduled",
      "category": "Decking",
      "projectType": "Call Back",
      "address": {...},
      "scheduledDate": "11-12-2025 01:00 PM"
    }
  ]
}
```

## 🐛 Troubleshooting

### Common Issues

#### 1. "Connection Refused" Error
**Problem:** Proxy server is not running

**Solution:**
```bash
cd bedrock/testing/ui
python3 pf_proxy.py
```

#### 2. "401 Unauthorized" Error
**Problem:** Access token is expired or invalid

**Solution:**
1. Run the "Login" request again
2. The new token will be automatically saved

#### 3. "Streaming not supported" Error
**Problem:** Postman doesn't fully support SSE visualization

**Solution:**
- The request still works, but Postman shows raw SSE text
- For better visualization, use the web UI or `curl`

#### 4. No Response / Timeout
**Problem:** Bedrock agent is taking too long

**Solution:**
- Check proxy logs: `tail -f /tmp/pf_proxy.log`
- Verify AWS credentials are configured
- Check agent IDs in environment config

## 📝 Example cURL Commands

If you prefer using cURL instead of Postman:

### Login
```bash
curl -X POST http://localhost:5003/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jay@mailinator.com",
    "password": "Password@123"
  }'
```

### Invoke Agent (Non-Streaming)
```bash
curl -X POST http://localhost:5003/api/invoke-agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show my projects",
    "session_id": "test-123",
    "pf_token": "YOUR_ACCESS_TOKEN",
    "pf_client_id": "09PF05VD",
    "pf_user_id": "1646085",
    "stream": false
  }'
```

### Invoke Agent (Streaming)
```bash
curl -X POST http://localhost:5003/api/invoke-agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "show my projects",
    "session_id": "test-123",
    "pf_token": "YOUR_ACCESS_TOKEN",
    "pf_client_id": "09PF05VD",
    "pf_user_id": "1646085",
    "stream": true
  }' \
  --no-buffer
```

## 🔍 Monitoring & Debugging

### View Proxy Logs
```bash
tail -f /tmp/pf_proxy.log
```

### View Bedrock Agent Logs
```bash
aws logs tail /aws/lambda/pf-scheduling-actions \
  --since 5m \
  --format short \
  --follow
```

### Check Running Processes
```bash
# Check if proxy is running
lsof -ti:5003

# Check proxy process details
ps aux | grep pf_proxy
```

## 📚 Additional Resources

- **Web UI:** http://localhost:8000/index.html
- **Proxy Server:** http://localhost:5003
- **API Documentation:** See `bedrock/DASHBOARD_API_DEPLOYMENT_STATUS.md`
- **Agent Configuration:** `bedrock/config/agent_config.dev.json`

## 💡 Tips & Best Practices

1. **Always run "Login" first** to get a fresh access token
2. **Use unique session IDs** for testing different conversation flows
3. **Check proxy logs** if responses seem incorrect
4. **Test non-streaming first** before trying streaming
5. **Use the web UI** for better streaming visualization

## 🎯 Test Checklist

- [ ] Proxy server is running (port 5003)
- [ ] Postman collection and environment imported
- [ ] Environment selected ("ProjectForce Agent - Local")
- [ ] Login request successful (token saved)
- [ ] Dashboard API working
- [ ] Non-streaming agent requests working
- [ ] Streaming agent requests working (SSE)
- [ ] All three agents responding (Supervisor, Scheduling, Chitchat, Information)

---

**Last Updated:** 2025-11-08
**Version:** 1.0
