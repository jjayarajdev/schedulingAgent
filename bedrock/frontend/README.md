# Bedrock Agent Chat UI

Beautiful React + Flask application to interact with AWS Bedrock multi-agent system.

## 🎯 Features

- **Sample User Login:** Pre-configured with CUST001 (John Doe)
- **3 Mock Projects:** Flooring, Windows, Deck Repair (from mock data)
- **Chat Interface:** Natural language interaction with Bedrock agents
- **Project Dashboard:** View all your projects at a glance
- **Quick Actions:** Pre-built queries for common tasks
- **Real-time Responses:** Stream responses from Bedrock agents

## 🚀 Quick Start

### 1. Start Backend (Flask)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run server
python app.py
```

Backend runs on: `http://localhost:5001`

### 2. Start Frontend (React)

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Frontend runs on: `http://localhost:3000`

### 3. Open Browser

Navigate to: `http://localhost:3000`

You'll be logged in as **John Doe (CUST001)** with 3 projects.

## 📋 Sample Queries

Try these queries in the chat:

1. **"Show me all my projects"**
   - Lists all 3 projects (12345, 12347, 12350)

2. **"What dates are available for project 12347?"**
   - Returns next 10 weekdays

3. **"Tell me about project 12345"**
   - Shows detailed info about Flooring Installation

4. **"What are your business hours?"**
   - Returns Mon-Fri 8AM-6PM schedule

5. **"Add a note to project 12345: Customer prefers morning appointments"**
   - Adds note to project

6. **"Book project 12347 for [date] at 10:00 AM"**
   - Schedules appointment

## 🏗️ Architecture

```
Browser (http://localhost:3000)
    ↓
React Frontend (Vite + TypeScript)
    ↓ /api/* requests
Flask Backend (http://localhost:5001)
    ↓ boto3
AWS Bedrock Multi-Agent System
    ↓
Lambda Functions (Mock Data)
    ↓
Returns Real Mock Data
```

## 📁 Project Structure

```
frontend/
├── backend/
│   ├── app.py              # Flask API server
│   └── requirements.txt    # Python dependencies
└── frontend/
    ├── src/
    │   ├── App.tsx         # Main UI component
    │   ├── main.tsx        # Entry point
    │   └── index.css       # Global styles
    ├── package.json        # Node dependencies
    ├── vite.config.ts      # Vite configuration
    └── tailwind.config.js  # Tailwind CSS config
```

## 🔑 Key Features

### Sample User (CUST001)

The app is pre-configured with a sample user:

```json
{
  "customer_id": "CUST001",
  "customer_type": "B2C",
  "name": "John Doe",
  "email": "john.doe@example.com"
}
```

### Mock Projects

Three projects from the mock data:

| ID | Type | Category | Status |
|----|------|----------|--------|
| 12345 | Installation | Flooring | Scheduled |
| 12347 | Installation | Windows | Pending |
| 12350 | Repair | Deck Repair | Pending |

### Chat Interface

- **Natural Language:** Ask questions in plain English
- **Context Aware:** Automatically includes customer_id
- **Multi-Agent:** Routes to appropriate specialist
- **Real Data:** Returns actual mock data (no hallucinations)

## 🛠️ Technology Stack

### Backend
- **Flask:** Python web framework
- **Flask-CORS:** Cross-origin resource sharing
- **boto3:** AWS SDK for Python
- **AWS Bedrock:** Multi-agent system

### Frontend
- **React 18:** UI framework
- **TypeScript:** Type safety
- **Vite:** Build tool
- **Tailwind CSS:** Styling
- **Axios:** HTTP client

## 🔧 Configuration

### Backend Configuration

The backend automatically loads agent configuration from:
`../agent_config.json`

Fallback values if file not found:
```python
SUPERVISOR_ID = 'V3BW0KFBMX'
SUPERVISOR_ALIAS = 'K6BWBY1RNY'
REGION = 'us-east-1'
```

### Frontend Configuration

Vite proxy configuration (auto-forwards /api to backend):
```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:5001',
      changeOrigin: true
    }
  }
}
```

## 🧪 Testing

### Test Backend Only

```bash
cd backend
python app.py

# In another terminal
curl http://localhost:5001/api/health
curl http://localhost:5001/api/user
```

### Test Full Stack

1. Start both backend and frontend
2. Open `http://localhost:3000`
3. Try sample queries
4. Check browser console for API calls
5. Check backend terminal for Bedrock logs

## 📊 API Endpoints

### GET /api/health
Health check endpoint

### GET /api/user
Returns current user (CUST001) and their projects

### POST /api/chat/simple
Send message to Bedrock agent (non-streaming)

**Request:**
```json
{
  "message": "Show me all my projects"
}
```

**Response:**
```json
{
  "response": "Here are all your projects: ...",
  "customer_id": "CUST001",
  "timestamp": 1697123456.789
}
```

### GET /api/config
Returns Bedrock configuration

## 🎨 UI Components

### Project Dashboard
- **Project Cards:** Show status, address, technician
- **Color Coding:** Green (Scheduled), Yellow (Pending)
- **Click to Select:** Highlight selected project

### Chat Interface
- **Message History:** Scrollable conversation
- **User Messages:** Blue bubbles (right side)
- **Agent Messages:** Gray bubbles (left side)
- **Loading State:** Animated dots while processing

### Quick Actions
- **Pre-built Queries:** Common questions
- **One-Click:** Send query instantly
- **Example Driven:** Learn by using

## 🚀 Deployment

### Production Build

```bash
cd frontend
npm run build
```

Outputs to: `frontend/dist/`

Serve static files with nginx or deploy to:
- Vercel
- Netlify
- AWS S3 + CloudFront
- AWS Amplify

### Backend Deployment

Deploy Flask backend to:
- AWS Lambda + API Gateway
- AWS Elastic Beanstalk
- Docker container
- Heroku

## 📝 Notes

### Mock Data Mode

The app uses mock data by default (`USE_MOCK_API=true` in Lambda).

To switch to real API:
```bash
aws lambda update-function-configuration \
  --function-name scheduling-agent-scheduling-actions \
  --environment Variables={USE_MOCK_API=false} \
  --region us-east-1
```

### Session Context

The backend automatically injects customer context:

```python
augmented_prompt = f"""Session Context:
- Customer ID: {customer_id}
- Customer Type: {customer_type}

User Request: {message}

Please help the customer with their request using their customer ID for any actions."""
```

This makes the multi-agent collaboration work correctly!

## 🔍 Troubleshooting

### Backend Issues

**Port already in use:**
```bash
# Find process
lsof -i :5001
# Kill process
kill -9 <PID>
```

**Bedrock errors:**
- Check agent_config.json exists
- Verify AWS credentials configured
- Check CloudWatch logs

### Frontend Issues

**Dependencies not installed:**
```bash
rm -rf node_modules package-lock.json
npm install
```

**Port 3000 in use:**
Update `vite.config.ts` to use different port

**API calls failing:**
- Check backend is running on port 5001
- Check browser console for CORS errors
- Verify proxy configuration in vite.config.ts

## 💡 Tips

1. **Use Quick Actions:** Click sample queries to learn
2. **Check Project IDs:** Use 12345, 12347, 12350
3. **Natural Language:** Ask in plain English
4. **Be Specific:** Include project IDs when asking about projects
5. **Multi-Step:** Book appointments step by step

## 📖 Related Documentation

- **`/bedrock/README.md`** - Main documentation
- **`/bedrock/PRODUCTION_IMPLEMENTATION.md`** - Integration guide
- **`/bedrock/docs/MOCK_DATA_REFERENCE.md`** - Mock data reference

---

**Status:** ✅ Ready to use
**Sample User:** John Doe (CUST001)
**Projects:** 3 mock projects
**Architecture:** React + Flask + AWS Bedrock
