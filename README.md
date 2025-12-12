# ProjectForce AI Scheduling Agent

**Version**: 6.0 (Consolidated pf-syn-* Stack)
**Status**: Production - Voice, SMS, and Chat Channels Live
**Architecture**: Direct Lambda with Claude 3.5 Sonnet Classification
**Resource Prefix**: `pf-syn-`
**Last Updated**: 2025-12-12

---

## Overview

Production multi-channel AI scheduling assistant for ProjectForce customers. Supports natural language conversations for project scheduling, rescheduling, cancellation, and general inquiries.

### Live Channels

| Channel | Status | Entry Point |
|---------|--------|-------------|
| **Voice** | Live | +1 (470) 283-2382 (Amazon Connect) |
| **SMS** | Live | +1 (878) 678-9053 (AWS End User Messaging) |
| **Chat** | Live | API Gateway (`pf-syn-orchestrator-api-dev`) |

### Key Features

- **Natural Language Understanding** - Claude 3.5 Sonnet for intent classification
- **Multi-Turn Conversations** - Context-aware session management
- **Weather Integration** - Open-Meteo API for weather forecasts + Nominatim for geocoding
- **Channel-Specific Formatting** - Optimized responses for voice, SMS, and chat
- **TCPA 2025 Compliance** - Opt-out handling for SMS
- **Unified Deployment** - Single `pf-manage.sh` script for all operations

---

## Architecture

See [docs/AWS_RESOURCES_INVENTORY.md](./docs/AWS_RESOURCES_INVENTORY.md) for detailed Mermaid diagrams.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SCHEDULING AGENT SYSTEM (pf-syn-*)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐              │
│    │    VOICE     │     │     SMS      │     │    CHAT      │              │
│    │  (Connect)   │     │ (End User    │     │   (React)    │              │
│    │ +14702832382 │     │  Messaging)  │     │  API Gateway │              │
│    │              │     │ +18786789053 │     │              │              │
│    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘              │
│           │                    │                    │                       │
│           ▼                    ▼                    │                       │
│    ┌──────────────┐     ┌──────────────┐           │                       │
│    │   Lex V2     │     │  SNS Topic   │           │                       │
│    │ pf-syn-      │     │ pf-syn-sms-  │           │                       │
│    │ scheduling-  │     │ inbound-dev  │           │                       │
│    │ assistant    │     └──────┬───────┘           │                       │
│    └──────┬───────┘            │                   │                       │
│           │                    ▼                   ▼                       │
│           ▼             ┌──────────────┐    ┌──────────────┐               │
│    ┌──────────────┐     │ pf-syn-sms-  │    │ API Gateway  │               │
│    │ pf-syn-lex-  │     │ inbound-dev  │    │ /chat        │               │
│    │ fulfillment  │     └──────┬───────┘    └──────┬───────┘               │
│    └──────┬───────┘            │                   │                       │
│           │                    │                   │                       │
│           └────────────────────┼───────────────────┘                       │
│                                │                                            │
│                                ▼                                            │
│                    ┌───────────────────────┐                                │
│                    │ pf-syn-orchestrator   │                                │
│                    │       -dev            │                                │
│                    │   (Claude 3.5 Sonnet) │                                │
│                    │  Intent Classification │                                │
│                    │   + Smart Routing      │                                │
│                    └───────────┬───────────┘                                │
│                                │                                            │
│         ┌──────────────────────┼──────────────────────┐                    │
│         │                      │                      │                    │
│         ▼                      ▼                      ▼                    │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────┐              │
│  │ pf-syn-        │   │ pf-syn-        │   │ pf-syn-        │              │
│  │ scheduling-    │   │ information-   │   │ chitchat-      │              │
│  │ actions-dev    │   │ actions-dev    │   │ actions-dev    │              │
│  │                │   │                │   │                │              │
│  │ • list_projects│   │ • get_weather  │   │ • greet        │              │
│  │ • get_details  │   │                │   │ • help         │              │
│  │ • get_dates    │   │                │   │ • goodbye      │              │
│  │ • get_timeslots│   │                │   │                │              │
│  │ • schedule     │   │                │   │                │              │
│  │ • reschedule   │   │                │   │                │              │
│  │ • cancel       │   │                │   │                │              │
│  └───────┬────────┘   └───────┬────────┘   └────────────────┘              │
│          │                    │                                             │
│          ▼                    ▼                                             │
│  ┌────────────────┐   ┌────────────────┐                                   │
│  │ ProjectForce   │   │ Weather APIs   │                                   │
│  │ External API   │   │ (Open-Meteo +  │                                   │
│  │                │   │  Nominatim)    │                                   │
│  └────────────────┘   └────────────────┘                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## AWS Resources

| Resource | Name/ID | Purpose |
|----------|---------|---------|
| **Lambda** | `pf-syn-orchestrator-dev` | Main classifier + router |
| **Lambda** | `pf-syn-scheduling-actions-dev` | Scheduling operations |
| **Lambda** | `pf-syn-information-actions-dev` | Weather queries |
| **Lambda** | `pf-syn-chitchat-actions-dev` | Greetings, help |
| **Lambda** | `pf-syn-notes-actions-dev` | Notes management |
| **Lambda** | `pf-syn-lex-fulfillment-dev` | Voice/Lex fulfillment |
| **Lambda** | `pf-syn-sms-inbound-dev` | SMS processing |
| **Lambda** | `pf-syn-customer-lookup-dev` | Customer lookup |
| **API Gateway** | `pf-syn-orchestrator-api-dev` (`4e4680oc2h`) | REST API for chat |
| **Lex V2 Bot** | `pf-syn-scheduling-assistant-dev` (`RUSMRZJNYG`) | Voice NLU |
| **Connect** | `pf-schedule-voice-dev` (`3edd99db-...`) | Voice contact center |
| **DynamoDB** | `pf-syn-sessions-dev` | Session storage |
| **DynamoDB** | `pf-syn-workflow-states-dev` | Workflow state |
| **DynamoDB** | `pf-syn-sms-sessions-dev` | SMS session tracking |
| **Secrets Manager** | `projectforce/api/credentials` | API credentials |

See [docs/AWS_RESOURCES_INVENTORY.md](./docs/AWS_RESOURCES_INVENTORY.md) for complete details.

---

## Channel-Specific Response Formatting

| Channel | Formatter | Max Length | Features |
|---------|-----------|------------|----------|
| `chat` | None (raw) | Unlimited | Full markdown, emojis, JSON blocks |
| `voice` | `voice_formatter.py` | ~300 chars | Natural speech, contractions, follow-ups |
| `sms` | `sms_formatter.py` | 1500 chars | ASCII-only, no emojis, truncation |

### Voice Formatter
- Direct responses (no filler phrases)
- Contractions for natural speech
- Date summarization for long lists
- Follow-up questions ("Anything else?")

### SMS Formatter
- Emoji to text conversion (sunny, cloudy)
- Strips remaining emojis
- Removes markdown formatting
- Unicode to ASCII normalization
- Smart truncation at sentence boundaries

---

## Quick Start

### Prerequisites

- AWS CLI configured with `pf-aws` profile
- Python 3.11
- Access to AWS account `772634497954`

### Deploy All Resources

```bash
cd scripts
AWS_PROFILE=pf-aws ./pf-manage.sh deploy --all
```

### Deploy Lambda Functions Only

```bash
cd scripts
AWS_PROFILE=pf-aws ./pf-manage.sh deploy --lambda
```

### Deploy Voice Resources

```bash
cd scripts
AWS_PROFILE=pf-aws ./pf-manage.sh deploy --voice
```

### Deploy SMS Resources

```bash
cd scripts
AWS_PROFILE=pf-aws ./pf-manage.sh deploy --sms
```

### Validate Deployment

```bash
cd scripts
AWS_PROFILE=pf-aws ./pf-manage.sh validate --all
```

### Test Chat Channel

```bash
curl -X POST https://4e4680oc2h.execute-api.us-east-1.amazonaws.com/dev/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "list my projects",
    "session_id": "test-123",
    "pf_client_id": "09PF05VD",
    "pf_user_id": "1646085",
    "channel": "chat"
  }'
```

### Test Voice Channel

Call +1 (470) 283-2382 and say "I need help with my projects"

### Test SMS Channel

Text "Hello" to +1 (878) 678-9053

---

## Local Development

### Start Test UI with Proxy

```bash
cd testing/ui
./launch_webapp.sh
```

This starts:
- **pf_proxy.py** on `localhost:5003` - CORS proxy + auth
- **HTTP server** on `localhost:8000` - Test UI

### Run Postman Tests

```bash
cd testing
newman run ProjectForce_Happy_Path.postman_collection.json \
  --reporters cli \
  --timeout-request 60000
```

---

## Project Structure

```
schedulingAgent/
├── lambda/
│   ├── orchestrator/           # Main orchestrator Lambda
│   │   ├── handler.py          # API Gateway handler
│   │   ├── router.py           # Intent classification + routing
│   │   ├── conversation.py     # Conversation management
│   │   ├── sms_formatter.py    # SMS response formatting
│   │   └── voice_formatter.py  # Voice response formatting
│   ├── scheduling-actions/     # Scheduling operations
│   ├── information-actions/    # Weather queries
│   ├── chitchat-actions/       # Greetings, help
│   ├── notes-actions/          # Notes management
│   ├── lex-fulfillment/        # Voice/Lex integration
│   ├── sms-inbound-processor/  # SMS processing
│   ├── customer-lookup/        # Customer lookup
│   └── voice-bedrock-bridge/   # Voice-to-Bedrock bridge
├── scripts/
│   ├── pf-manage.sh            # Unified deployment script
│   ├── lib/                    # Deployment library modules
│   │   ├── common.sh           # Common functions
│   │   ├── lambda.sh           # Lambda deployment
│   │   ├── voice.sh            # Voice resources
│   │   ├── sms.sh              # SMS resources
│   │   ├── iam.sh              # IAM roles
│   │   ├── dynamodb.sh         # DynamoDB tables
│   │   ├── api.sh              # API Gateway
│   │   ├── secrets.sh          # Secrets Manager
│   │   ├── cloudwatch.sh       # CloudWatch logs
│   │   └── validate.sh         # Validation
│   └── config/                 # Deployment configuration
│       ├── resources.env       # Resource naming
│       ├── connect/            # Connect flow templates
│       └── lex/                # Lex bot configuration
├── testing/
│   ├── ui/                     # Test UI + proxy
│   │   ├── index.html          # Chat test interface
│   │   ├── pf_proxy.py         # Flask CORS proxy
│   │   └── launch_webapp.sh    # Start script
│   └── ProjectForce_Happy_Path.postman_collection.json
├── docs/
│   └── AWS_RESOURCES_INVENTORY.md  # Complete AWS resource list
└── README.md                   # This file
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/AWS_RESOURCES_INVENTORY.md](./docs/AWS_RESOURCES_INVENTORY.md) | Complete AWS resource inventory with Mermaid diagrams |
| [REACT_INTEGRATION_GUIDE.md](./REACT_INTEGRATION_GUIDE.md) | React.js integration guide |
| [lambda/sms-inbound-processor/README.md](./lambda/sms-inbound-processor/README.md) | SMS Lambda documentation |
| [lambda/orchestrator/sms_formatter.py](./lambda/orchestrator/sms_formatter.py) | SMS formatting code |
| [lambda/orchestrator/voice_formatter.py](./lambda/orchestrator/voice_formatter.py) | Voice formatting code |
| [scripts/pf-manage.sh](./scripts/pf-manage.sh) | Unified deployment script |

---

## Monitoring

### CloudWatch Log Groups

```bash
# Orchestrator
AWS_PROFILE=pf-aws aws logs tail /aws/lambda/pf-syn-orchestrator-dev --since 5m --follow

# SMS Inbound
AWS_PROFILE=pf-aws aws logs tail /aws/lambda/pf-syn-sms-inbound-dev --since 5m --follow

# Lex Fulfillment
AWS_PROFILE=pf-aws aws logs tail /aws/lambda/pf-syn-lex-fulfillment-dev --since 5m --follow

# Scheduling Actions
AWS_PROFILE=pf-aws aws logs tail /aws/lambda/pf-syn-scheduling-actions-dev --since 5m --follow
```

### Key Log Searches

| Search Term | What It Shows |
|-------------|---------------|
| `"Intent classified"` | Classification results |
| `"[SMS] Formatted"` | SMS formatting applied |
| `"[VOICE]"` | Voice formatting applied |
| `"ERROR"` | Any errors |

---

## Sample Conversations

### Greeting
```
User: "Hello!"
Bot: "Hi there! Welcome back! I'm your ProjectForce scheduling assistant.
     I can help you view your projects, find available dates, and get
     appointments scheduled."
```

### List Projects
```
User: "Show my projects"
Bot: "I see you have several decking projects with us at your Chicago Avenue
     address in Minneapolis. You currently have 8 projects, with 4 scheduled
     appointments..."
```

### Weather Query
```
User: "What's the weather in Tampa?"
Bot: "Right now in Tampa it's a clear night at 62°F with light winds.
     The next few days will be quite wet - we're looking at drizzle
     and rain from Friday through Monday..."
```

See [REACT_INTEGRATION_GUIDE.md](./REACT_INTEGRATION_GUIDE.md#10-sample-conversations) for more examples.

---

## Troubleshooting

### SMS Not Sending
1. Check phone number is provisioned: `+18786789053`
2. Verify IAM permissions for `sms-voice:SendTextMessage`
3. Check CloudWatch logs for errors

### Voice Calls Not Working
1. Verify Connect instance is active
2. Check Lex bot is associated with contact flow
3. Review `/aws/lambda/pf-syn-lex-fulfillment-dev` logs

### Chat API Errors
1. Verify API Gateway endpoint: `4e4680oc2h`
2. Check CORS headers (should be `*`)
3. Verify required parameters in request body

### Response Contains Emojis (SMS)
1. Verify `channel: 'sms'` is passed
2. Check `sms_formatter.py` is imported in `router.py`
3. Look for `[SMS] Formatted` in logs

---

## Cost Estimate

**Monthly costs (estimated for 1,000 interactions):**

| Service | Cost |
|---------|------|
| Lambda (8 functions) | $10 |
| Bedrock (Claude 3.5 Sonnet) | $50 |
| DynamoDB | $5 |
| API Gateway | $5 |
| Connect (voice calls) | $90 |
| SMS (End User Messaging) | $20 |
| CloudWatch | $5 |
| **Total** | **~$185/month** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 6.0 | 2025-12-12 | Consolidated `pf-syn-*` stack, unified `pf-manage.sh` deployment |
| 5.0 | 2025-12-07 | Multi-channel production (Voice + SMS + Chat) |
| 4.0 | 2025-11-15 | Direct Lambda architecture (removed Bedrock Agents) |
| 3.0 | 2025-10-01 | Bedrock Agents with Supervisor |
| 2.0 | 2025-09-01 | Initial SMS integration |
| 1.0 | 2025-08-01 | Initial release |

---

*Last Updated: December 12, 2025*
