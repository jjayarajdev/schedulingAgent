# 🎬 Demo Guide - Bedrock Agent Chat UI

## 🎯 What You'll See

Beautiful, modern chat interface to interact with AWS Bedrock multi-agent system using sample user from mock data.

### Landing Page

```
┌─────────────────────────────────────────────────────────────────┐
│  Property Management Portal              John Doe (CUST001/B2C) │
│  Powered by AWS Bedrock Multi-Agent System                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌─────────────────────────────────────────┐ │
│  │ My Projects  │  │ AI Assistant Chat                       │ │
│  ├──────────────┤  │ Multi-agent system: Scheduling •        │ │
│  │              │  │ Information • Notes • Chitchat          │ │
│  │ 🏠 Flooring  │  ├─────────────────────────────────────────┤ │
│  │ ORD-2025-001 │  │ 🤖 Hello! I'm your property            │ │
│  │ [Scheduled]  │  │    management assistant. How can I      │ │
│  │              │  │    help you today?                      │ │
│  │ 🪟 Windows   │  │                                         │ │
│  │ ORD-2025-002 │  │ 👤 Show me all my projects             │ │
│  │ [Pending]    │  │                                         │ │
│  │              │  │ 🤖 Here are all your projects:         │ │
│  │ 🏗️ Deck Repair│  │    1. Project 12345 - Flooring...     │ │
│  │ ORD-2025-003 │  │    2. Project 12347 - Windows...       │ │
│  │ [Pending]    │  │    3. Project 12350 - Deck Repair...   │ │
│  │              │  │                                         │ │
│  ├──────────────┤  ├─────────────────────────────────────────┤ │
│  │ Quick Actions│  │ [Type your message here...]    [Send]  │ │
│  ├──────────────┤  └─────────────────────────────────────────┘ │
│  │ Sample       │                                             │ │
│  │ Queries      │                                             │ │
│  └──────────────┘                                             │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Demo Workflow

### Step 1: View Your Projects (Left Panel)

**What you see:**
- **Project 12345** - Flooring Installation (Scheduled)
  - ✅ Green badge
  - 📅 Scheduled for 2025-10-15, 08:00 AM - 12:00 PM
  - 📍 123 Main St, Tampa, FL
  - 👤 Technician: John Smith

- **Project 12347** - Windows Installation (Pending)
  - 🟡 Yellow badge
  - 📍 456 Oak Ave, Tampa, FL
  - 👤 Technician: Jane Doe

- **Project 12350** - Deck Repair (Pending)
  - 🟡 Yellow badge
  - 📍 789 Pine Dr, Clearwater, FL
  - 👤 Technician: Mike Johnson

### Step 2: Try Quick Actions

Click any of these pre-built queries:

1. **"Show me all my projects"**
   ```
   You → Show me all my projects
   
   AI → Here are all your projects:
   
   Project 1:
   - Project ID: 12345
   - Type: Installation - Flooring
   - Status: Scheduled
   - Address: 123 Main St, Tampa, FL 33601
   - Scheduled Date: 2025-10-15, 08:00 AM - 12:00 PM
   
   [... shows all 3 projects ...]
   
   You have 3 total projects - 1 scheduled and 2 pending.
   ```

2. **"What dates are available for project 12347?"**
   ```
   You → What dates are available for project 12347?
   
   AI → Here are the available dates for project 12347:
   - October 20, 2025
   - October 21, 2025
   - October 22, 2025
   [... next 10 weekdays ...]
   
   Would you like to check available time slots for any of these dates?
   ```

3. **"Tell me about project 12345"**
   ```
   You → Tell me about project 12345
   
   AI → Here are the details for project 12345:
   
   Project Information:
   - Project ID: 12345
   - Order Number: ORD-2025-001
   - Type: Installation - Flooring
   - Status: Scheduled
   
   Schedule:
   - Date: October 15, 2025
   - Time: 8:00 AM - 12:00 PM (4 hours)
   
   Location:
   - Address: 123 Main St, Tampa, FL 33601
   - Store: ST-101
   
   Team:
   - Technician: John Smith
   ```

4. **"What are your business hours?"**
   ```
   You → What are your business hours?
   
   AI → Here are our business hours:
   
   Monday - Friday: 8:00 AM - 6:00 PM
   Saturday: 9:00 AM - 4:00 PM
   Sunday: Closed
   
   All times are in Eastern Time (America/New_York).
   ```

5. **"Add a note to project 12345: Customer prefers morning appointments"**
   ```
   You → Add a note to project 12345: Customer prefers morning appointments
   
   AI → I've successfully added the note to project 12345:
   
   Note: "Customer prefers morning appointments"
   Added by: System
   Timestamp: [current time]
   
   Would you like to add any other notes or need help with anything else?
   ```

### Step 3: Natural Conversation

**Multi-step workflow:**

```
You → I need to schedule my windows project

AI → I can help you schedule project 12347 (Windows Installation).
     Let me check available dates. One moment...
     
     Here are the available dates for project 12347:
     - October 20, 2025
     - October 21, 2025
     - October 22, 2025
     [...]
     
     Which date would you prefer?

You → October 21st works for me

AI → Great! Let me check available time slots for October 21, 2025...
     
     Available time slots:
     - 08:00 AM
     - 09:00 AM
     - 10:00 AM
     - 11:00 AM
     - 01:00 PM
     - 02:00 PM
     - 03:00 PM
     - 04:00 PM
     
     What time would you prefer?

You → 10:00 AM please

AI → Perfect! I need a few more details to confirm your appointment:
     - Your name (for confirmation)
     - Contact phone number
     
     Please provide these details.

You → John Doe, 555-1234

AI → ✅ Appointment confirmed!
     
     Project: 12347 (Windows Installation)
     Date: October 21, 2025
     Time: 10:00 AM
     Duration: 3 hours
     Technician: Jane Doe
     Customer: John Doe (555-1234)
     
     You'll receive a confirmation email shortly.
```

## 🎨 UI Features

### Real-time Chat
- **User messages:** Blue bubbles (right-aligned)
- **AI messages:** Gray bubbles (left-aligned)
- **Timestamps:** On every message
- **Loading indicator:** Animated dots while AI thinks

### Project Cards
- **Click to select:** Card highlights in blue
- **Status badges:** Color-coded (Green/Yellow)
- **Icons:** 📅 Date, 🕐 Time, 👤 Technician, 📍 Location
- **Hover effects:** Smooth transitions

### Quick Actions
- **One-click queries:** No typing needed
- **Learn by example:** See how to phrase questions
- **Disabled during loading:** Prevents duplicate requests

### Responsive Design
- **Mobile friendly:** Works on all screen sizes
- **Scrollable chat:** Auto-scrolls to latest message
- **Fixed input:** Always visible at bottom

## 📊 Behind the Scenes

### What Happens When You Send a Message:

```
1. User types: "Show me all my projects"
   ↓
2. Frontend sends to: POST /api/chat/simple
   Body: { "message": "Show me all my projects" }
   ↓
3. Flask backend receives request
   ↓
4. Backend augments prompt with customer context:
   "Session Context:
    - Customer ID: CUST001
    - Customer Type: B2C
    
    User Request: Show me all my projects
    
    Please help the customer..."
   ↓
5. Backend invokes Bedrock Supervisor Agent
   ↓
6. Supervisor routes to Scheduling Agent
   ↓
7. Scheduling Agent calls list_projects Lambda
   ↓
8. Lambda returns mock data (3 projects)
   ↓
9. Agent formats response
   ↓
10. Backend streams response to frontend
    ↓
11. Frontend displays in chat
```

### Why It Works:

✅ **Customer context injected** into prompt
✅ **Supervisor routes** to correct specialist
✅ **Specialist calls Lambda** with customer_id
✅ **Lambda returns real mock data** (not hallucinations)
✅ **Response formatted** nicely for user

## 🎯 Key Highlights

### For Users:
- **Natural language:** Ask in plain English
- **No training needed:** Intuitive interface
- **Quick actions:** Common tasks pre-built
- **Visual feedback:** See projects and status

### For Developers:
- **Production pattern:** Uses working customer context injection
- **Type-safe:** TypeScript frontend
- **Clean architecture:** Separation of concerns
- **Easy to extend:** Add more features easily

### For Testing:
- **Sample user:** Pre-configured CUST001
- **Mock data:** 3 projects ready to use
- **All actions:** Scheduling, information, notes, chitchat
- **CloudWatch:** Can verify Lambda invocations

## 🚀 Running the Demo

### Quick Start (One Command):

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock/frontend
./start.sh
```

**Opens:**
- Backend: http://localhost:5001
- Frontend: http://localhost:3000

**Sample User:** John Doe (CUST001)
**Projects:** 12345, 12347, 12350

### Manual Start:

**Terminal 1 - Backend:**
```bash
cd backend
pip install -r requirements.txt
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 💡 Tips for Demo

1. **Start with Quick Actions:** Click pre-built queries
2. **Show project cards:** Explain the 3 mock projects
3. **Try multi-step workflow:** Schedule an appointment
4. **Check CloudWatch:** Show Lambda invocations
5. **Explain architecture:** Supervisor → Specialist → Lambda

## 🎥 Demo Script (5 minutes)

**Minute 1:** Show landing page, explain sample user
**Minute 2:** Click "Show me all my projects" - show response
**Minute 3:** Click project card, ask about specific project
**Minute 4:** Schedule appointment (multi-step)
**Minute 5:** Show CloudWatch logs (Lambda invocations)

## 📸 Screenshots

### Main Interface
- Left: Project dashboard (3 cards)
- Right: Chat interface
- Top: User info (John Doe)
- Bottom: Sample queries

### Chat in Action
- User message bubbles (blue)
- AI response bubbles (gray)
- Timestamps
- Loading indicator

### Project Details
- Selected project highlighted
- Status badge (color-coded)
- All details visible
- Click to select

---

**Status:** ✅ Ready for demo
**User:** John Doe (CUST001)
**Projects:** 3 mock projects
**Backend:** Flask + AWS Bedrock
**Frontend:** React + TypeScript + Tailwind
