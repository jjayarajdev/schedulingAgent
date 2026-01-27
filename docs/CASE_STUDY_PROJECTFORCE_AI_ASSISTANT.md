# Case Study: ProjectForce AI Scheduling Assistant

**Multi-Channel Conversational AI Platform for Home Services**

**Version:** 1.2.9
**Date:** January 2026

---

# Slide 1: The Challenge

## Business Problem

Home service companies face significant operational challenges in managing customer appointments:

### Customer Pain Points
| Challenge | Impact |
|-----------|--------|
| **Phone Hold Times** | Customers wait 10-15 minutes to speak with an agent |
| **Limited Hours** | Call centers operate 8am-6pm, missing working professionals |
| **Manual Scheduling** | Prone to double-booking and miscommunication |
| **No Self-Service** | Customers cannot check project status independently |
| **Weather Surprises** | Outdoor projects scheduled on bad weather days |

### Business Pain Points
| Challenge | Impact |
|-----------|--------|
| **High Call Volume** | 500+ calls/day for scheduling alone |
| **Agent Burnout** | Repetitive scheduling tasks reduce job satisfaction |
| **Missed Appointments** | 15-20% no-show rate due to poor communication |
| **Scaling Costs** | Adding agents costs $40K+/year per headcount |

## The Opportunity

**Goal:** Build an AI-powered assistant that allows customers to manage their home improvement projects through natural conversation - anytime, anywhere, on any channel.

### Target Channels
```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   WEB/MOBILE    │   │     VOICE       │   │      SMS        │
│     CHAT        │   │   PHONE CALL    │   │   TEXT MESSAGE  │
│                 │   │                 │   │                 │
│  Tech-savvy     │   │  Traditional    │   │  On-the-go      │
│  customers      │   │  customers      │   │  quick queries  │
│  24/7 access    │   │  Hands-free     │   │  Asynchronous   │
└─────────────────┘   └─────────────────┘   └─────────────────┘
```

---

# Slide 2: The Solution

## System Architecture

```
                          ┌──────────────────────────────────────┐
                          │       PROJECTFORCE CX PORTAL         │
                          │           (PF360 API)                │
                          │   Projects | Scheduling | Weather    │
                          └──────────────────┬───────────────────┘
                                             │
         ┌───────────────────────────────────┼───────────────────────────────────┐
         │                                   │                                   │
         ▼                                   ▼                                   ▼
┌─────────────────┐               ┌─────────────────┐               ┌─────────────────┐
│   WEB CLIENT    │               │  VAPI PLATFORM  │               │   AWS PINPOINT  │
│   React Chat    │               │   Voice + STT   │               │   SMS Gateway   │
│   Widget        │               │   + TTS         │               │                 │
└────────┬────────┘               └────────┬────────┘               └────────┬────────┘
         │ HTTPS                           │ Webhook                         │ SNS
         │                                 │                                 │
         └─────────────────────────────────┼─────────────────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │           ORCHESTRATOR LAMBDA                 │
                    │         (Central Intelligence)                │
                    │                                              │
                    │  ┌────────────────────────────────────────┐  │
                    │  │         NLU Intent Classifier           │  │
                    │  │    Claude Sonnet 3.5 + DSPy Optimized   │  │
                    │  └────────────────────────────────────────┘  │
                    │                      │                       │
                    │  ┌────────────────────────────────────────┐  │
                    │  │       Intelligent Router                │  │
                    │  │    Context Resolution | Workflow State  │  │
                    │  └────────────────────────────────────────┘  │
                    │                      │                       │
                    │  ┌────────────────────────────────────────┐  │
                    │  │      Channel-Specific Formatters        │  │
                    │  │    Voice | Chat | SMS (320 char limit)  │  │
                    │  └────────────────────────────────────────┘  │
                    └──────────────────────┬───────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
    │   SCHEDULING    │          │   INFORMATION   │          │    CHITCHAT     │
    │    ACTIONS      │          │     ACTIONS     │          │    ACTIONS      │
    │                 │          │                 │          │                 │
    │ • list_projects │          │ • get_weather   │          │ • greet         │
    │ • get_dates     │          │ • calendar_info │          │ • help          │
    │ • get_slots     │          │                 │          │ • farewell      │
    │ • schedule      │          │                 │          │                 │
    │ • reschedule    │          │                 │          │                 │
    │ • cancel        │          │                 │          │                 │
    └─────────────────┘          └─────────────────┘          └─────────────────┘
```

## Key Components

### 1. Multi-Channel Entry Points

| Channel | Technology | Authentication | Response Format |
|---------|------------|----------------|-----------------|
| **Web Chat** | API Gateway + Lambda | Bearer Token | Rich JSON + Markdown |
| **Voice** | VAPI + Twilio | Phone Number Lookup | Conversational Speech |
| **SMS** | AWS Pinpoint + SNS | Phone Number | 320-char plain text |

### 2. Intelligent Orchestrator

The brain of the system - processes all requests regardless of channel:

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Intent Classifier** | Claude Sonnet 3.5 | 17 intents with 95%+ accuracy |
| **Entity Extractor** | DSPy Optimized | Dates, times, project IDs, categories |
| **Context Resolver** | Custom NLU | "the first one", "this project", "reschedule it" |
| **Workflow State** | DynamoDB | Multi-turn conversation tracking |
| **Weather Integration** | WeatherAPI | Proactive weather warnings for outdoor projects |

### 3. Action Handlers

| Action | Description | Example Utterance |
|--------|-------------|-------------------|
| `list_projects` | Show customer's projects | "Show my projects" |
| `get_project_details` | Details for specific project | "Tell me about my deck project" |
| `get_available_dates` | Available scheduling dates | "When can I schedule?" |
| `get_time_slots` | Time slots for a date | "What times on Friday?" |
| `confirm_appointment` | Book the appointment | "Yes, 9 AM works" |
| `reschedule_appointment` | Change existing appointment | "Move to next week" |
| `cancel_appointment` | Cancel appointment | "Cancel my appointment" |
| `get_weather` | Weather forecast | "What's the weather Friday?" |
| `add_note` | Add note to project | "Add a note about the gate code" |

---

# Slide 3: Key Features & Innovations

## 1. Natural Language Understanding

### Multi-Intent Support
```
User: "Show me my kitchen projects that are ready to schedule"
       └──────┬──────┘ └────┬────┘ └──────────┬──────────┘
           action     category           status filter

Extracted:
  Intent: Project_List_Request
  Parameters:
    - category: "kitchen" (bucket: dishwasher, sink, oven, cooktop...)
    - status: "schedulable" (Ready To Schedule, New)
```

### Context Resolution
```
User: "Show my projects"
AI: "You have 5 projects: Deck, Storm Door, Dishwasher..."

User: "Schedule the second one"    ← Ordinal reference
AI: "Great, the Storm Door project. Here are available dates..."

User: "What about the dishwasher?" ← Category switch
AI: "Your Dishwasher project is Ready To Schedule..."
```

### Date Reference Resolution
```
User: "What day is February 18th?"
AI: "February 18, 2026 is a Wednesday."

User: "Schedule it for this date"  ← Contextual reference
AI: "Here are the time slots for February 18th..."
```

## 2. Weather-Aware Scheduling

For outdoor projects (Decking, Roofing, Fencing, etc.):

```
┌────────────────────────────────────────────────────────────┐
│           WEATHER-AWARE DATE SELECTION                      │
├──────────────┬──────────────┬──────────────┬───────────────┤
│  Sat 01/24   │  Sun 01/25   │  Mon 01/26   │  Tue 01/27    │
│  66°F Foggy  │  79°F Rain   │  70°F Rain   │  52°F Clear   │
│   [GOOD]     │   [WARN]     │   [WARN]     │   [GOOD]      │
│  Suitable    │  May impact  │  May impact  │  Suitable     │
└──────────────┴──────────────┴──────────────┴───────────────┘

"Saturday and Tuesday look best for your deck installation.
 Sunday and Monday have rain in the forecast."
```

## 3. Voice-Optimized Responses

| Feature | Chat Response | Voice Response |
|---------|---------------|----------------|
| **Project List** | Full table with IDs | "You have 3 projects: Deck, Storm Door, and Dishwasher" |
| **Dates** | Calendar picker | "I've got Friday, Saturday, or Monday open" |
| **Confirmation** | JSON + checkmark | "Got it! Your deck install is set for Friday at 9 AM" |

### Smart System Prompt (GPT-4o)
```
Voice channel embeds project state in GPT-4o's system prompt:
- Project category, status, scheduled date
- Pre-generated response guidance
- 70%+ of queries answered without tool calls
```

## 4. SMS Optimization

320-character limit with intelligent summarization:
```
SMS Response:
"You have 3 projects: Decking (Ready), Storm Door (Scheduled 1/25),
Dishwasher (Ready). Reply with project name or number to see details."
```

## 5. Mandatory Confirmation Flow

**Before:** Appointments booked instantly (accidental bookings)
**After:** Two-step confirmation required

```
User: "Schedule for Friday at 9"
AI: "I'll book your Deck Installation for Friday, January 24th at 9:00 AM.
     Does that work for you?"

User: "Yes"
AI: "Your appointment is confirmed!"
```

---

# Slide 4: Technical Excellence

## AWS Serverless Architecture

| Service | Purpose | Region |
|---------|---------|--------|
| **Lambda** | Compute (7 functions) | us-east-1, us-east-2 |
| **API Gateway** | REST API endpoint | us-east-1 |
| **DynamoDB** | Session & workflow state | us-east-1 |
| **Secrets Manager** | API credentials | us-east-1 |
| **S3** | DSPy models, training logs | us-east-1 |
| **CloudWatch** | Logging & monitoring | Both regions |
| **Pinpoint** | SMS gateway | us-east-1 |

## Lambda Functions

| Function | Purpose | Cold Start | Memory |
|----------|---------|------------|--------|
| `pf-syn-orchestrator` | Central brain | ~700ms | 512MB |
| `pf-syn-scheduling-actions` | Project/appointment APIs | ~300ms | 256MB |
| `pf-syn-information-actions` | Weather API | ~200ms | 256MB |
| `pf-syn-chitchat-actions` | Conversational responses | ~200ms | 256MB |
| `pf-syn-notes-actions` | Project notes | ~200ms | 256MB |
| `pf-syn-vapi-webhook` | Voice webhook | ~400ms | 256MB |
| `pf-syn-sms-inbound` | SMS processor | ~300ms | 256MB |

## AI/ML Stack

| Component | Model/Service | Purpose |
|-----------|---------------|---------|
| **Intent Classification** | Claude Sonnet 3.5 v2 | Primary NLU |
| **Entity Enrichment** | Claude Sonnet 3.5 | Context-aware extraction |
| **Voice Routing** | GPT-4o Mini | Real-time voice conversation |
| **Speech-to-Text** | Deepgram Nova-3 | Voice transcription |
| **Text-to-Speech** | OpenAI Alloy | Natural voice synthesis |
| **Optimization** | DSPy | Few-shot prompt optimization |

## Performance Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| **Response Time (Chat)** | <5s | 2-4s |
| **Response Time (Voice)** | <3s | 1.5-2.5s |
| **Intent Accuracy** | >90% | 95%+ |
| **Uptime** | 99.9% | 99.95% |
| **Concurrent Users** | 100+ | Tested 150 |

---

# Slide 5: Business Impact & KPIs

## Operational Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Avg Call Duration** | 8 min | 3 min | **62% reduction** |
| **After-Hours Requests** | 0% served | 100% served | **24/7 availability** |
| **Scheduling Accuracy** | 85% | 99% | **14% improvement** |
| **Weather-Related Reschedules** | 12% | 3% | **75% reduction** |
| **Customer Wait Time** | 10-15 min | 0 min | **Eliminated** |

## Cost Savings

| Category | Monthly Savings |
|----------|-----------------|
| **Reduced Call Center Load** | 40% fewer human-handled calls |
| **Avoided Hires** | 2-3 FTEs worth of capacity |
| **Reduced No-Shows** | Proactive reminders + weather alerts |
| **Infrastructure** | Serverless = pay-per-use |

## Customer Satisfaction

| Metric | Score |
|--------|-------|
| **CSAT (Chat)** | 4.5/5 |
| **CSAT (Voice)** | 4.3/5 |
| **First Contact Resolution** | 85% |
| **Self-Service Completion** | 78% |

## Channel Distribution (Production)

```
┌─────────────────────────────────────────────────────────┐
│                  CHANNEL USAGE                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   VOICE  ████████████████████████████████████  55%     │
│                                                         │
│   CHAT   ████████████████████████              35%     │
│                                                         │
│   SMS    ████████                              10%     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

# Slide 6: Innovation Highlights

## 1. DSPy-Optimized Prompts
- Continuous learning from production interactions
- Few-shot examples auto-generated from successful classifications
- 15% improvement in edge case handling

## 2. Vague Prompt Handler
```
User: "Schedule a project"  (no specific project mentioned)
AI: "I found 3 projects ready to schedule: Deck, Storm Door, Dishwasher.
     Which one would you like to schedule?"
```

## 3. Project Status Validation
```
User: "Schedule my deck project"

IF status = "Ready for Quote":
  AI: "This project can't be scheduled yet. The status is 'Ready for Quote'.
       Please contact our office for assistance."

IF status = "Scheduled":
  AI: "This project is already scheduled for January 25th.
       Would you like to reschedule it?"
```

## 4. Multi-Project Batch Scheduling
```
User: "Schedule all my kitchen projects"
AI: "I'll help you schedule 3 kitchen projects:
     1. Dishwasher - scheduling now...
     2. Sink Installation - next...
     3. Cooktop - finally..."
```

## 5. Intelligent Date Interpretation
```
"next Tuesday"        → 2026-01-28
"end of February"     → 2026-02-24 to 2026-02-28
"2nd week of March"   → 2026-03-09 to 2026-03-13
"this Friday"         → 2026-01-24
```

---

# Appendix: Technology Stack

## Languages & Frameworks
- **Backend:** Python 3.11
- **Frontend:** React 18 (Chat Widget)
- **Infrastructure:** AWS CDK / Terraform

## External Integrations
- **VAPI:** Voice AI platform
- **Twilio:** Phone number provisioning
- **Deepgram:** Speech-to-text
- **OpenAI:** GPT-4o (voice), TTS
- **Anthropic:** Claude Sonnet 3.5 (NLU)
- **WeatherAPI:** Weather forecasts

## Deployment
- **Dev:** us-east-1 (Lambda, DynamoDB, API Gateway)
- **Prod:** us-east-2 (Voice), us-east-1 (Chat, SMS)
- **CI/CD:** GitHub Actions + AWS CodePipeline

---

*ProjectForce AI Scheduling Assistant - Transforming Home Services Customer Experience*

**Contact:** engineering@projectforce.com
