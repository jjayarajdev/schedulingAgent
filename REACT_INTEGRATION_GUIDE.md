# React.js Integration Guide - Scheduling Agent Chat API

> Complete guide for the React.js development team to integrate the Scheduling Agent chat functionality.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [API Endpoint](#2-api-endpoint)
3. [Authentication](#3-authentication)
4. [Request/Response Format](#4-requestresponse-format)
5. [Session Management](#5-session-management)
6. [Welcome Flow](#6-welcome-flow)
7. [Sample React Implementation](#7-sample-react-implementation)
8. [Response Handling](#8-response-handling)
9. [Error Handling](#9-error-handling)
10. [Sample Conversations](#10-sample-conversations)
11. [Testing](#11-testing)
12. [Deployment](#12-deployment)
13. [Local Development (Optional)](#13-local-development-optional)

---

## 1. Architecture Overview

### Production Architecture (Serverless)

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   React App     │────────▶│   API Gateway   │────────▶│  pf-orchestrator│
│  (Browser)      │  HTTPS  │   (CORS enabled)│  Lambda │    Lambda       │
└─────────────────┘         └─────────────────┘         └────────┬────────┘
                                                                 │
                            ┌────────────────────────────────────┼────────────────────┐
                            │                                    │                    │
                            ▼                                    ▼                    ▼
                   ┌─────────────────┐               ┌─────────────────┐   ┌─────────────────┐
                   │ pf-scheduling   │               │ pf-information  │   │ pf-chitchat     │
                   │ -actions        │               │ -actions        │   │ -actions        │
                   └────────┬────────┘               └─────────────────┘   └─────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ ProjectForce    │
                   │ API (External)  │
                   └─────────────────┘
```

### Key Points

- **No proxy server needed** - React calls API Gateway directly
- **CORS enabled** - API Gateway configured to accept browser requests
- **Fully serverless** - Everything runs in AWS (Lambda, API Gateway)
- **Pass credentials per request** - No Secrets Manager needed for chat channel

---

## 2. API Endpoint

### Base URL

```
https://fpheaag7c7.execute-api.us-east-1.amazonaws.com/dev
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/invoke-agent` | POST | Main chat endpoint |
| `/health` | GET | Health check |

### CORS Configuration

API Gateway is pre-configured with CORS headers:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization, X-Api-Key
```

---

## 3. Authentication

### Required Parameters

All parameters are passed in the request body (not headers):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pf_client_id` | string | **Yes** | ProjectForce client ID (e.g., `09PF05VD`) |
| `pf_user_id` | string | **Yes** | ProjectForce user ID (e.g., `1646085`) |
| `pf_token` | string | **Yes** | Bearer token from ProjectForce authentication |
| `pf_user_name` | string | **Yes** | User's display name for personalized greetings |

### Getting Credentials

Credentials come from the user's ProjectForce session after login:

```javascript
// After user logs into ProjectForce
const credentials = {
  clientId: pfAuthResponse.client_id,     // "09PF05VD"
  userId: pfAuthResponse.user_id,         // "1646085"
  userName: pfAuthResponse.display_name,  // "John Smith"
  token: pfAuthResponse.access_token      // Bearer token
};
```

---

## 4. Request/Response Format

### Request Body

```typescript
interface ChatRequest {
  message: string;        // User's message (required)
  session_id: string;     // Unique session identifier (required)
  pf_client_id: string;   // Client ID (required)
  pf_user_id: string;     // User ID (required)
  pf_token: string;       // Bearer token (required)
  pf_user_name: string;   // User's display name (required)
  channel: 'chat';        // Always 'chat' for React integration
}
```

### Response Body

```typescript
interface ChatResponse {
  response: string;       // Bot's response message
  agent_name: string;     // Which agent handled the request
  intent: string;         // Detected intent (scheduling, information, chitchat)
  action?: string;        // Specific action performed
  session_id: string;     // Echo of session ID
  direct_call: boolean;   // Whether Lambda was called directly
  performance: {
    classification: number;  // Time for intent classification (seconds)
    decision?: number;       // Time for decision making (seconds)
    lambda_call?: number;    // Time for Lambda invocation (seconds)
    total: number;           // Total response time (seconds)
  };
}
```

### Example Request

```javascript
const API_URL = 'https://fpheaag7c7.execute-api.us-east-1.amazonaws.com/dev';

const response = await fetch(`${API_URL}/invoke-agent`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    message: "What are my projects?",
    session_id: "user-1646085-1733590000000",
    pf_client_id: "09PF05VD",
    pf_user_id: "1646085",
    pf_token: "eyJhbGciOiJIUzI1NiIs...",
    pf_user_name: "John Smith",
    channel: "chat"
  })
});

const data = await response.json();
console.log(data.response);  // "You have 3 projects: ..."
```

---

## 5. Session Management

### Session ID Requirements

- Must be unique per user conversation
- Should persist across page refreshes (use localStorage)
- Recommended format: `{userId}-{timestamp}` or UUID

### Session ID Best Practices

```javascript
function getOrCreateSessionId(userId) {
  const storageKey = `pf_session_${userId}`;
  let sessionId = localStorage.getItem(storageKey);

  if (!sessionId) {
    sessionId = `${userId}-${Date.now()}`;
    localStorage.setItem(storageKey, sessionId);
  }

  return sessionId;
}

function clearSession(userId) {
  localStorage.removeItem(`pf_session_${userId}`);
}
```

### Conversation History

The backend automatically maintains conversation history per session_id:
- Context awareness ("details for the first project")
- Pronoun resolution ("schedule it", "cancel that")
- Multi-turn workflows (scheduling flow with multiple steps)

---

## 6. Welcome Flow

### Triggering Welcome Message

Send a special `__WELCOME__` message to get a personalized greeting:

```javascript
async function initializeChat(credentials, sessionId) {
  const response = await fetch(`${API_URL}/invoke-agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: '__WELCOME__',
      session_id: sessionId,
      pf_client_id: credentials.clientId,
      pf_user_id: credentials.userId,
      pf_token: credentials.token,
      pf_user_name: credentials.userName,
      channel: 'chat'
    })
  });

  const data = await response.json();
  // data.response: "Hi John! You have 3 projects..."
  return data;
}
```

### Welcome Response Example

```json
{
  "response": "Hi John! You have 3 projects:\n\n1. **Flooring** - Scheduled for Dec 15\n2. **Plumbing** - Needs scheduling\n3. **HVAC** - In progress\n\nWhat would you like to do?",
  "agent_name": "Welcome",
  "intent": "welcome",
  "action": "welcome_with_projects",
  "session_id": "1646085-1733590000000",
  "direct_call": true,
  "performance": { "total": 1.2 }
}
```

---

## 7. Sample React Implementation

### ChatService.ts

```typescript
// services/ChatService.ts

const API_URL = 'https://fpheaag7c7.execute-api.us-east-1.amazonaws.com/dev';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: {
    agent_name?: string;
    intent?: string;
    action?: string;
    performance?: { total: number };
  };
}

export interface ChatConfig {
  clientId: string;
  userId: string;
  userName: string;
  token: string;
}

class ChatService {
  private sessionId: string;
  private config: ChatConfig;

  constructor(config: ChatConfig) {
    this.config = config;
    this.sessionId = this.getOrCreateSessionId();
  }

  private getOrCreateSessionId(): string {
    const key = `pf_chat_session_${this.config.userId}`;
    let sessionId = localStorage.getItem(key);

    if (!sessionId) {
      sessionId = `${this.config.userId}-${Date.now()}`;
      localStorage.setItem(key, sessionId);
    }

    return sessionId;
  }

  async sendMessage(message: string): Promise<ChatMessage> {
    const response = await fetch(`${API_URL}/invoke-agent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: this.sessionId,
        pf_client_id: this.config.clientId,
        pf_user_id: this.config.userId,
        pf_token: this.config.token,
        pf_user_name: this.config.userName,
        channel: 'chat'
      })
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();

    return {
      role: 'assistant',
      content: data.response,
      timestamp: new Date(),
      metadata: {
        agent_name: data.agent_name,
        intent: data.intent,
        action: data.action,
        performance: data.performance
      }
    };
  }

  async initializeWelcome(): Promise<ChatMessage> {
    return this.sendMessage('__WELCOME__');
  }

  resetSession(): void {
    const key = `pf_chat_session_${this.config.userId}`;
    localStorage.removeItem(key);
    this.sessionId = this.getOrCreateSessionId();
  }
}

export default ChatService;
```

### ChatComponent.tsx

```tsx
// components/Chat/ChatComponent.tsx

import React, { useState, useEffect, useRef } from 'react';
import ChatService, { ChatMessage, ChatConfig } from '../../services/ChatService';

interface ChatProps {
  credentials: ChatConfig;
}

const ChatComponent: React.FC<ChatProps> = ({ credentials }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatService] = useState(() => new ChatService(credentials));
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize with welcome message
  useEffect(() => {
    const initChat = async () => {
      setIsLoading(true);
      try {
        const welcomeMessage = await chatService.initializeWelcome();
        setMessages([welcomeMessage]);
      } catch (error) {
        console.error('Failed to initialize chat:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initChat();
  }, [chatService]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await chatService.sendMessage(input);
      setMessages(prev => [...prev, response]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
        timestamp: new Date()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">{msg.content}</div>
            {msg.metadata?.performance && (
              <div className="message-meta">
                {msg.metadata.agent_name} | {msg.metadata.performance.total.toFixed(2)}s
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="message assistant loading">
            <div className="typing-indicator">...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          disabled={isLoading}
        />
        <button onClick={handleSend} disabled={isLoading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatComponent;
```

### useChat Hook

```typescript
// hooks/useChat.ts

import { useState, useCallback } from 'react';

const API_URL = 'https://fpheaag7c7.execute-api.us-east-1.amazonaws.com/dev';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface UseChatOptions {
  clientId: string;
  userId: string;
  userName: string;
  token: string;
  sessionId?: string;
}

export function useChat({ clientId, userId, userName, token, sessionId }: UseChatOptions) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const effectiveSessionId = sessionId || `${userId}-${Date.now()}`;

  const sendMessage = useCallback(async (message: string) => {
    setIsLoading(true);
    setError(null);

    setMessages(prev => [...prev, { role: 'user', content: message }]);

    try {
      const response = await fetch(`${API_URL}/invoke-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          session_id: effectiveSessionId,
          pf_client_id: clientId,
          pf_user_id: userId,
          pf_token: token,
          pf_user_name: userName,
          channel: 'chat'
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }]);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [clientId, userId, userName, token, effectiveSessionId]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, isLoading, error, sendMessage, clearMessages };
}
```

---

## 8. Response Handling

### Markdown in Responses

Responses may contain markdown:
- **Bold text** for emphasis
- Lists for projects/dates
- Code blocks with JSON data

Use `react-markdown` to render:

```tsx
import ReactMarkdown from 'react-markdown';

<div className="message-content">
  <ReactMarkdown>{message.content}</ReactMarkdown>
</div>
```

### Parsing Embedded JSON

Some responses include structured JSON:

```javascript
function parseResponse(response) {
  const jsonMatch = response.match(/```json\n([\s\S]*?)\n```/);

  if (jsonMatch) {
    return {
      text: response.split('```json')[0].trim(),
      data: JSON.parse(jsonMatch[1])
    };
  }

  return { text: response, data: null };
}
```

---

## 9. Error Handling

### HTTP Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad Request | Check required parameters |
| 401 | Unauthorized | Token expired, re-authenticate |
| 500 | Server Error | Retry with backoff |
| 503 | Service Unavailable | Retry later |

### Retry Logic

```typescript
async function sendWithRetry(chatService: ChatService, message: string, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await chatService.sendMessage(message);
    } catch (error) {
      if (attempt < maxRetries) {
        await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt - 1)));
      } else {
        throw error;
      }
    }
  }
}
```

---

## 10. Sample Conversations

> These are actual responses from the scheduling agent captured during testing.

### Greeting

```
User: "Hello!"

Bot: "Hi there! Welcome back! I'm your ProjectForce scheduling assistant.
I can help you view your projects, find available dates, and get
appointments scheduled. Feel free to ask me anything!"
```

### Help Request

```
User: "What can you help me with?"

Bot: "I can help you with:
- View your projects (list my projects)
- Get project details (details for project 7751744)
- Check available dates (what dates are available for project 7751744)
- View time slots (show me time slots for Nov 25)
- Schedule appointments (schedule project 7751744)

Just ask me what you'd like to do!"
```

### List Projects

```
User: "Show my projects"

Bot: "I see you have several decking projects with us at your Chicago Avenue
address in Minneapolis. You currently have 8 projects, with 4 scheduled
appointments:

• December 22, 2025 at 1:00 PM - 2:00 PM
• December 16, 2025 at 8:00 AM - 9:00 AM
• November 26, 2025 at 8:00 AM - 8:10 AM
• November 25, 2025 at 8:00 AM - 8:10 AM

The remaining 4 projects are ready to be scheduled at your convenience.
One of your projects includes some documents you might want to review."
```

### Project Details

```
User: "Give me details for project 7751741"

Bot: "I found your decking project details! This is project #7751741, which
is currently ready to be scheduled. It's a callback project for your
property at 401 Chicago Avenue in Minneapolis. The project was purchased
through Lowe's on November 3rd, 2025, and we'll be able to get it on the
calendar for you as soon as a date is selected."
```

### Schedule Appointment Flow

```
User: "I want to schedule an appointment for project 7751741"

Bot: "I'd be happy to help you schedule project #7751741. We have several
dates available in December 2025, but I should mention that the first week
(Dec 6-11) has some weather concerns - including snow and cold temperatures
around 16-37°F. However, starting December 12th through the end of the
month, we have many good weather days available for your project, including
weekday and weekend options."
```

```
User: "I'll take the first available date"

Bot: "I see several dates available in December 2025. Please specify which
date you'd prefer (between December 6-31, except Sundays), and I'll show
you the available time slots for that day."
```

```
User: "The morning slot works for me"

Bot: "Perfect! The morning slot at 8:00 AM is available for your service
appointment. I should mention that the weather forecast shows some cold
temperatures and light snow expected, with temperatures ranging from 8 to
16 degrees. While our crews are prepared to work in various conditions,
you might want to know that warmer temperatures are expected later in the
week around December 9-10, with highs in the upper 30s."
```

### Weather Queries

```
User: "What's the weather in Tampa?"

Bot: "Right now in Tampa it's a clear night at 62°F with light winds. The
next few days will be quite wet - we're looking at drizzle and rain from
Friday through Monday, with temperatures reaching the mid to high 70s.
Things should dry up by Tuesday, with overcast skies and slightly cooler
temperatures in the high 60s to low 70s for the rest of the week."
```

```
User: "Will it rain in Miami tomorrow?"

Bot: "Looking at tomorrow's forecast for Miami, there's only a small 4%
chance of rain. It'll be mostly overcast with temperatures ranging from
67°F to 79°F - quite pleasant overall. If you're planning any outdoor
activities, the weather should cooperate nicely, though you might see
some clouds overhead."
```

---

## 11. Testing

### Test Credentials

```javascript
const TEST_CREDENTIALS = {
  clientId: '09PF05VD',
  userId: '1646085',
  userName: 'Test User',
  token: 'YOUR_VALID_TOKEN'  // Get from ProjectForce login
};
```

### cURL Test

```bash
curl -X POST https://fpheaag7c7.execute-api.us-east-1.amazonaws.com/dev/invoke-agent \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are my projects?",
    "session_id": "test-123",
    "pf_client_id": "09PF05VD",
    "pf_user_id": "1646085",
    "pf_token": "YOUR_TOKEN",
    "pf_user_name": "Test User",
    "channel": "chat"
  }'
```

### Health Check

```bash
curl https://fpheaag7c7.execute-api.us-east-1.amazonaws.com/dev/health
```

---

## 12. Deployment

### Deploy API Gateway (New Environment)

If setting up a new environment, run:

```bash
cd scripts
./deploy_api_gateway.sh [environment]

# Example:
./deploy_api_gateway.sh dev
```

This script:
1. Creates REST API with CORS enabled
2. Creates `/invoke-agent` POST endpoint
3. Creates `/health` GET endpoint
4. Configures Lambda integration
5. Deploys to specified stage

### Deploy Lambda Functions

```bash
cd scripts
./DEPLOY_LAMBDA_ONLY_ADVANCED.sh
```

---

## 13. Local Development (Optional)

For local development without AWS credentials, use the Flask proxy:

### Start Local Proxy

```bash
cd testing/ui
./launch_webapp.sh
```

This starts:
- **pf_proxy.py** on `localhost:5003` - handles CORS and token management
- **HTTP server** on `localhost:8000` - serves static files

### Local API URL

```javascript
// For local development only
const API_URL = 'http://localhost:5003/api';

// Use /api/invoke-agent instead of /invoke-agent
```

### Proxy Features

The proxy provides additional functionality for development:
- Auto-loads tokens from AWS Secrets Manager
- Handles CORS without API Gateway
- Provides login endpoint for testing

---

## Quick Reference

### Minimum Request

```javascript
{
  "message": "Hello",
  "session_id": "user-123-session-456",
  "pf_client_id": "09PF05VD",
  "pf_user_id": "1646085",
  "pf_token": "eyJhbGciOiJIUzI1NiIs...",
  "pf_user_name": "John Smith",
  "channel": "chat"
}
```

### Response Fields

| Field | Description |
|-------|-------------|
| `response` | Bot's text response |
| `agent_name` | Which agent handled request |
| `intent` | scheduling, information, or chitchat |
| `action` | Specific action performed |
| `session_id` | Echo of session ID |
| `performance` | Timing metrics |

---

## Support

- **CloudWatch Logs**: `/aws/lambda/pf-orchestrator`
- **API Gateway Console**: [AWS Console](https://console.aws.amazon.com/apigateway)
- **Deploy Script**: `./scripts/deploy_api_gateway.sh`

---

*Last Updated: December 7, 2025*
