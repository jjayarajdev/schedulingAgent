# AWS Services & Permissions - Multi-Agent Scheduling System

**Project**: Scheduling Agent with Bedrock AI
**Last Updated**: October 22, 2025
**Account**: 618048437522
**Region**: us-east-1

---

## 📋 Table of Contents

1. [Phase 1: Current Deployment (AI Chat)](#phase-1-current-deployment-ai-chat)
2. [Phase 2: Telephony Integration (Voice Calls)](#phase-2-telephony-integration-voice-calls)
3. [Phase 3: SMS Integration](#phase-3-sms-integration)
4. [Cost Summary](#cost-summary)
5. [Permissions Matrix](#permissions-matrix)

---

## Phase 1: Current Deployment (AI Chat)

**Status**: ✅ Deployed and Operational
**Data Source**: ⚠️ Mock data (Python dictionaries) - NOT production-ready
**Deployment Date**: October 2025

### Services Overview

| # | Service | Resources | Purpose | Monthly Cost | Status |
|---|---------|-----------|---------|--------------|--------|
| 1 | **AWS Bedrock** | 5 agents | Multi-agent AI with Claude Sonnet 4.5 | $135.00 | ✅ Active |
| 2 | **AWS Lambda** | 3 functions | Action group backends (scheduling, info, notes) | $0.20 | ✅ Active |
| 3 | **Amazon S3** | 1 bucket, 3 objects | OpenAPI schema storage | $0.01 | ✅ Active |
| 4 | **AWS IAM** | 5 roles, 10 policies | Agent execution permissions | Free | ✅ Active |
| 5 | **CloudWatch Logs** | 3 log groups | Lambda execution logs | $0.50 | ✅ Active |
| | **TOTAL** | | | **$135.71/mo** | |

### Detailed Resources

#### 1. AWS Bedrock Agents

| Agent Name | Agent ID | Alias | Lambda Integration | Purpose |
|------------|----------|-------|-------------------|---------|
| **Supervisor** | WF1S95L7X1 | TSTALIASID | ❌ None | Routes requests to specialist agents |
| **Scheduling** | TIGRBGSXCS | PNDF9AQVHW | ✅ pf-scheduling-actions | Appointment scheduling |
| **Information** | JEK4SDJOOU | LF61ZU9X2T | ✅ pf-information-actions | Project/order information |
| **Notes** | CF0IPHCFFY | YOBOR0JJM7 | ✅ pf-notes-actions | Note management |
| **Chitchat** | GXVZEOBQ64 | RSSE65OYGM | ❌ None | Casual conversation |

**Foundation Model**: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

#### 2. Lambda Functions

| Function Name | Runtime | Memory | Timeout | Data Source | Invocations/mo |
|--------------|---------|--------|---------|-------------|----------------|
| `pf-scheduling-actions` | Python 3.11 | 256 MB | 30s | **Mock data** | ~3,000 |
| `pf-information-actions` | Python 3.11 | 256 MB | 30s | **Mock data** | ~2,000 |
| `pf-notes-actions` | Python 3.11 | 256 MB | 30s | **Mock data** | ~1,000 |

⚠️ **Mock Data Contents**:
- 3 sample projects (Flooring, Windows, Deck Repair)
- Hardcoded dates and time slots
- No persistent storage

#### 3. Storage & Configuration

| Resource | Type | Size | Purpose |
|----------|------|------|---------|
| `pf-schemas-dev-618048437522` | S3 Bucket | 1 MB | OpenAPI schemas |
| `scheduling_actions.json` | S3 Object | 15 KB | Scheduling agent schema |
| `information_actions.json` | S3 Object | 8 KB | Information agent schema |
| `notes_actions.json` | S3 Object | 6 KB | Notes agent schema |

#### 4. IAM Roles & Policies

| Role Name | Used By | Key Permissions |
|-----------|---------|-----------------|
| `pf-supervisor-agent-role-dev` | Supervisor Agent | InvokeModel, InvokeAgent |
| `pf-scheduling-agent-role-dev` | Scheduling Agent | InvokeModel, S3:GetObject, Lambda:InvokeFunction |
| `pf-information-agent-role-dev` | Information Agent | InvokeModel, S3:GetObject, Lambda:InvokeFunction |
| `pf-notes-agent-role-dev` | Notes Agent | InvokeModel, S3:GetObject, Lambda:InvokeFunction |
| `pf-chitchat-agent-role-dev` | Chitchat Agent | InvokeModel |

### Phase 1 Permissions Summary

| Service | Read | Write | Admin |
|---------|------|-------|-------|
| **Bedrock** | GetAgent, GetAgentAlias | InvokeModel, InvokeAgent | CreateAgent, PrepareAgent |
| **Lambda** | GetFunction | InvokeFunction | CreateFunction, UpdateFunctionCode |
| **S3** | GetObject, ListBucket | PutObject | CreateBucket |
| **IAM** | GetRole, ListRoles | PassRole | CreateRole, PutRolePolicy |
| **CloudWatch Logs** | GetLogEvents | PutLogEvents | CreateLogGroup |

---

## Phase 2: Telephony Integration (Voice Calls)

**Status**: 🔵 Planned
**Timeline**: Q1-Q2 2026 (3-6 months)
**Goal**: Enable inbound customer calls (AWS Connect) and outbound appointment reminders (Pinpoint Voice)

### New Services Required

| # | Service | Resources | Purpose | Monthly Cost | Setup Time |
|---|---------|-----------|---------|--------------|------------|
| 1 | **Amazon Connect** | 1 instance | **INBOUND** contact center (customers call in) | $30-50 | 2 weeks |
| 2 | **Amazon Pinpoint Voice** | Voice campaigns | **OUTBOUND** automated appointment reminders | $50-100 | 1 week |
| 3 | **Amazon Lex** | 1 bot | Voice conversational AI (for inbound calls) | $15-30 | 1 week |
| 4 | **Amazon Polly** | Voice synthesis | Text-to-speech for both inbound/outbound | $4-8 | 1 day |
| 5 | **Amazon Transcribe** | Speech-to-text | Convert voice to text (inbound calls) | $3-6 | 1 day |
| 6 | **DynamoDB** | 3 tables | Call history, campaigns, customer preferences | $8-15 | 3 days |
| 7 | **Lambda** | +4 functions | Call handlers, campaign triggers | $0.80 | 1 week |
| 8 | **EventBridge** | 5 rules | Scheduled outbound reminder campaigns | Free | 2 days |
| 9 | **API Gateway** | 1 REST API | Frontend integration | $3.50 | 3 days |
| 10 | **Secrets Manager** | 2 secrets | Store PF360 & Pinpoint credentials | $0.80 | 1 hour |
| 11 | **CloudWatch** | Enhanced monitoring | Call metrics, dashboards, alarms | $10-15 | 2 days |
| | **TOTAL** | | | **$125-228/mo** | **4-5 weeks** |

### Detailed Phase 2 Services

#### Amazon Connect Configuration (INBOUND Calls)

| Component | Configuration | Purpose | Cost Driver |
|-----------|--------------|---------|-------------|
| **Instance** | Connect instance in us-east-1 | **Inbound** contact center platform | $0/hour + usage |
| **Phone Number** | 1 toll-free number | Customers call in for support | $0.03/min inbound |
| **Contact Flows** | 4 flows (IVR, appointment info, reschedule, cancel) | Call routing logic | Included |
| **Agent Seats** | 0 seats (AI-only, no human agents) | Automated AI responses only | $0 |
| **Lex Integration** | Voice bot for inbound calls | AI handles customer inquiries | Included |
| **Estimated Usage** | 200 inbound calls/mo, 3 min avg | Customer-initiated calls | $18/month |

**Inbound Use Cases**:
- ✅ Customer calls to check appointment status
- ✅ Customer calls to reschedule appointment
- ✅ Customer calls to cancel appointment
- ✅ Customer calls for project information
- ✅ Customer calls for general inquiries
- ✅ IVR menu with voice recognition
- ✅ Integration with Bedrock agents for complex queries

#### Amazon Pinpoint Voice Configuration (OUTBOUND Calls)

| Component | Configuration | Purpose | Cost Driver |
|-----------|--------------|---------|-------------|
| **Voice Campaigns** | Automated voice campaigns | **Outbound** appointment reminders | Per campaign |
| **Phone Number** | Dedicated origination number | Outbound calling | $2/month + usage |
| **Voice Templates** | 5 templates (reminder, confirm, reschedule, cancel) | Pre-recorded/TTS messages | Free |
| **Call Duration** | 1-2 min avg per call | Reminder messages | $0.02/min |
| **Estimated Usage** | 500 outbound calls/mo, 1.5 min avg | Automated reminders | $15 + $15 = $30/month |
| **Retry Logic** | 3 attempts if no answer | Ensure delivery | Included |
| **Scheduling** | EventBridge triggers | Time-based campaigns | Free |

**Outbound Use Cases**:
- ✅ Automated appointment reminders (24 hours before)
- ✅ Automated appointment reminders (2 hours before)
- ✅ Appointment confirmation calls (after booking)
- ✅ Rescheduling notifications (when system reschedules)
- ✅ Emergency cancellation notifications
- ✅ Press-1-to-confirm functionality
- ✅ Voicemail detection and drop

#### Amazon Lex Bot Configuration (Inbound Calls Only)

| Bot Feature | Configuration | Purpose |
|-------------|--------------|---------|
| **Bot Name** | `pf-scheduling-voice-bot` | Voice conversational AI for **inbound calls** |
| **Language** | English (US) | Primary language |
| **Intents** | 6 intents (check-status, reschedule, cancel, book, get-info, speak-to-bedrock) | User intent recognition |
| **Slots** | Date, time, project_id, customer_id | Extract data from speech |
| **Integration** | Amazon Connect (inbound only) | Voice channel |
| **Fallback** | Route to Bedrock agent | Complex queries |
| **Channel** | Voice only (Amazon Connect) | No text/chat |

**Estimated Usage**:
- 200 inbound calls/month
- 8 turns per call avg
- 1,600 requests/month = $15/month

#### DynamoDB Tables (Phase 2)

| Table Name | Partition Key | Sort Key | Purpose | Use Case | RCU/WCU |
|------------|--------------|----------|---------|----------|---------|
| `pf-inbound-call-history-dev` | `customer_id` | `call_timestamp` | Inbound call logs (Connect) | Customer-initiated calls | 3/3 |
| `pf-outbound-campaign-history-dev` | `campaign_id` | `call_timestamp` | Outbound call logs (Pinpoint) | System-initiated reminders | 5/5 |
| `pf-voice-preferences-dev` | `customer_id` | - | Customer voice call preferences | Opt-in/out for voice calls | 2/2 |

**Estimated Cost**: $8-15/month (on-demand pricing)

#### Lambda Functions (Phase 2)

| Function Name | Trigger | Purpose | Type | Integrations |
|--------------|---------|---------|------|--------------|
| `pf-connect-inbound-handler` | Connect contact flow | Handle inbound call routing | Inbound | Connect, Lex, DynamoDB |
| `pf-connect-lex-fulfillment` | Lex bot intent | Process customer voice requests | Inbound | Bedrock, PF360 API, DynamoDB |
| `pf-pinpoint-outbound-handler` | EventBridge schedule | Trigger outbound reminder campaigns | Outbound | Pinpoint Voice, DynamoDB |
| `pf-pinpoint-campaign-tracker` | Pinpoint events | Track call delivery status | Outbound | DynamoDB, CloudWatch |

#### EventBridge Rules (Phase 2)

| Rule Name | Schedule | Target | Purpose | Type |
|-----------|----------|--------|---------|------|
| `pf-outbound-reminder-24h` | Every hour | Pinpoint Voice Lambda | Trigger 24h reminder campaigns | Outbound |
| `pf-outbound-reminder-2h` | Every 15 min | Pinpoint Voice Lambda | Trigger 2h reminder campaigns | Outbound |
| `pf-outbound-confirmation` | On appointment booking | Pinpoint Voice Lambda | Send booking confirmation calls | Outbound |
| `pf-daily-voice-report` | Daily at 9 AM | Lambda | Generate inbound/outbound call reports | Monitoring |
| `pf-emergency-cancellation` | Manual/API trigger | Pinpoint Voice Lambda | Emergency cancellation calls | Outbound |

### Phase 2 Permissions

| Service | Permissions Needed | Resource ARN Pattern | Use Case |
|---------|-------------------|---------------------|----------|
| **Amazon Connect** | `connect:DescribeInstance`<br>`connect:GetContactAttributes`<br>`connect:UpdateContactAttributes` | `arn:aws:connect:us-east-1:*:instance/*` | Inbound calls only |
| **Amazon Pinpoint Voice** | `mobiletargeting:SendMessages`<br>`mobiletargeting:GetCampaign`<br>`mobiletargeting:CreateCampaign`<br>`mobiletargeting:SendVoiceMessage` | `arn:aws:mobiletargeting:us-east-1:*:apps/*` | Outbound calls only |
| **Amazon Lex** | `lex:PostContent`<br>`lex:PostText`<br>`lex:RecognizeText` | `arn:aws:lex:us-east-1:*:bot-alias/*` | Inbound call processing |
| **Amazon Polly** | `polly:SynthesizeSpeech` | `*` | Text-to-speech (both) |
| **Amazon Transcribe** | `transcribe:StartStreamTranscription` | `*` | Speech-to-text (inbound) |
| **DynamoDB** | `dynamodb:PutItem`<br>`dynamodb:GetItem`<br>`dynamodb:Query`<br>`dynamodb:UpdateItem` | `arn:aws:dynamodb:us-east-1:*:table/pf-*` | Call history tracking |
| **EventBridge** | `events:PutRule`<br>`events:PutTargets` | `arn:aws:events:us-east-1:*:rule/pf-*` | Scheduled campaigns |

### Phase 2 Implementation Steps

| Week | Task | Type | Deliverables |
|------|------|------|--------------|
| **Week 1** | Setup Amazon Connect for inbound calls, claim toll-free number | Inbound | Working Connect instance |
| **Week 1-2** | Create Lex bot, design contact flows (IVR) | Inbound | Voice bot handling customer calls |
| **Week 2** | Setup Amazon Pinpoint Voice, configure outbound campaigns | Outbound | Reminder campaign infrastructure |
| **Week 3** | Develop Lambda functions (inbound + outbound handlers) | Both | Call handlers functional |
| **Week 3-4** | Create DynamoDB tables, integrate call tracking | Both | Call history tracking |
| **Week 4-5** | Testing (inbound + outbound), monitoring, documentation | Both | Production-ready voice system |

---

## Phase 3: SMS Integration

**Status**: 🟣 Planned
**Timeline**: Q2-Q3 2026 (6-9 months)
**Goal**: SMS appointment reminders, confirmations, and two-way messaging

### New Services Required

| # | Service | Resources | Purpose | Monthly Cost | Setup Time |
|---|---------|-----------|---------|--------------|------------|
| 1 | **Amazon Pinpoint** | 1 project | SMS messaging platform | $25-50 | 1 week |
| 2 | **Amazon SNS** | 2 topics | SMS delivery, notifications | $0.50 | 1 day |
| 3 | **Amazon SQS** | 2 queues | Async message processing | $0.40 | 1 day |
| 4 | **DynamoDB** | +2 tables | SMS history, opt-outs | $3-5 | 2 days |
| 5 | **Lambda** | +4 functions | SMS handlers, webhooks | $0.30 | 1 week |
| 6 | **EventBridge** | +3 rules | Scheduled SMS campaigns | Free | 1 day |
| 7 | **API Gateway** | +1 endpoint | Webhook for inbound SMS | $0.50 | 1 day |
| 8 | **Step Functions** | 2 state machines | Multi-step SMS workflows | $5 | 3 days |
| | **TOTAL** | | | **$35-61/mo** | **2-3 weeks** |

### Detailed Phase 3 Services

#### Amazon Pinpoint Configuration

| Component | Configuration | Purpose | Cost |
|-----------|--------------|---------|------|
| **Project** | `pf-scheduling-sms` | SMS messaging platform | $1.00/month |
| **Phone Number** | 10DLC registration | Dedicated SMS number | $2.00/month |
| **Message Template** | 5 templates | Pre-defined SMS messages | Free |
| **Segments** | Customer groups | Targeted messaging | Free |
| **Campaigns** | Scheduled campaigns | Automated reminders | Free |
| **Message Sending** | ~2,000 SMS/month | Transactional + marketing | $0.00645/SMS = $12.90/month |

**10DLC Registration Requirements**:
- Business information
- Use case description (appointment reminders)
- Sample message templates
- Registration fee: $15 one-time
- Monthly fee: $2/month per number

**Throughput Limits**:
- Standard: 3 SMS/second
- High volume: 100 SMS/second (requires approval)

#### SMS Use Cases

| Use Case | Trigger | Message Type | Frequency |
|----------|---------|--------------|-----------|
| **Appointment Reminder** | 24h before | Transactional | ~500/month |
| **Appointment Confirmation** | After booking | Transactional | ~300/month |
| **Rescheduling Notification** | Customer request | Transactional | ~100/month |
| **Cancellation Notice** | Customer/system | Transactional | ~50/month |
| **Two-way Messaging** | Customer reply | Interactive | ~200/month |
| **Promotional** | Weekly/monthly | Marketing | ~500/month |

**Total**: ~1,650 SMS/month

#### DynamoDB Tables (Phase 3)

| Table Name | Partition Key | Sort Key | Purpose | RCU/WCU |
|------------|--------------|----------|---------|---------|
| `pf-sms-history-dev` | `customer_id` | `timestamp` | SMS delivery logs | 3/3 |
| `pf-sms-opt-outs-dev` | `phone_number` | - | Opt-out management | 1/1 |

**Compliance Features**:
- ✅ STOP keyword handling (auto opt-out)
- ✅ START keyword handling (re-subscribe)
- ✅ HELP keyword (information)
- ✅ Opt-out list persistence
- ✅ TCPA compliance

#### Lambda Functions (Phase 3)

| Function Name | Trigger | Purpose | Integrations |
|--------------|---------|---------|--------------|
| `pf-sms-outbound-handler` | EventBridge | Send scheduled SMS | Pinpoint, DynamoDB |
| `pf-sms-inbound-handler` | API Gateway webhook | Process incoming SMS | Bedrock, DynamoDB |
| `pf-sms-opt-out-handler` | SNS topic | Handle opt-outs | DynamoDB |
| `pf-sms-delivery-handler` | SNS topic | Track delivery status | DynamoDB, CloudWatch |

#### Step Functions Workflows

| Workflow Name | Steps | Purpose | Timeout |
|--------------|-------|---------|---------|
| `pf-sms-reminder-workflow` | 1. Check opt-out<br>2. Load template<br>3. Send SMS<br>4. Log delivery<br>5. Handle retry | Multi-step SMS delivery | 5 min |
| `pf-sms-conversation-workflow` | 1. Receive SMS<br>2. Check intent<br>3. Route to Bedrock<br>4. Get response<br>5. Send reply | Two-way SMS conversation | 30 sec |

#### Amazon Pinpoint Event Streams

| Event Type | Destination | Purpose |
|------------|-------------|---------|
| SMS Delivery | SNS → Lambda → DynamoDB | Track successful deliveries |
| SMS Failure | SNS → Lambda → CloudWatch | Alert on failures |
| Customer Opt-out | SNS → Lambda → DynamoDB | Update opt-out list |
| Message Click | Kinesis Data Stream | Analytics (future) |

### Phase 3 Permissions

| Service | Permissions Needed | Resource ARN Pattern |
|---------|-------------------|---------------------|
| **Amazon Pinpoint** | `mobiletargeting:SendMessages`<br>`mobiletargeting:GetEndpoint`<br>`mobiletargeting:UpdateEndpoint` | `arn:aws:mobiletargeting:us-east-1:*:apps/*` |
| **Amazon SNS** | `sns:Publish`<br>`sns:Subscribe` | `arn:aws:sns:us-east-1:*:pf-sms-*` |
| **Amazon SQS** | `sqs:SendMessage`<br>`sqs:ReceiveMessage`<br>`sqs:DeleteMessage` | `arn:aws:sqs:us-east-1:*:pf-sms-*` |
| **DynamoDB** | `dynamodb:PutItem`<br>`dynamodb:GetItem`<br>`dynamodb:Query`<br>`dynamodb:UpdateItem` | `arn:aws:dynamodb:us-east-1:*:table/pf-sms-*` |
| **Step Functions** | `states:StartExecution`<br>`states:DescribeExecution` | `arn:aws:states:us-east-1:*:stateMachine:pf-sms-*` |

### Phase 3 Compliance & Best Practices

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| **TCPA Compliance** | Opt-in consent before sending SMS | ✅ Built-in |
| **Opt-out Management** | STOP keyword auto-processing | ✅ Built-in |
| **Message Frequency** | Max 1 SMS per customer per day | ✅ Configurable |
| **Quiet Hours** | No SMS 9 PM - 8 AM local time | ✅ Configurable |
| **Two-way Messaging** | Support for customer replies | ✅ Planned |
| **Delivery Reports** | Track sent/delivered/failed | ✅ Built-in |
| **Cost Monitoring** | Budget alerts at $50/month | ✅ CloudWatch |

### Phase 3 Implementation Steps

| Week | Task | Deliverables |
|------|------|--------------|
| **Week 1** | Register 10DLC, setup Pinpoint project | SMS number ready |
| **Week 1-2** | Create message templates, test delivery | Templates approved |
| **Week 2** | Build Lambda handlers, DynamoDB tables | SMS handlers working |
| **Week 3** | Implement two-way messaging, Bedrock integration | Interactive SMS working |
| **Week 3** | Testing, compliance review, monitoring | Production-ready SMS |

---

## Cost Summary

### Monthly Cost by Phase

| Phase | Description | Services | Monthly Cost | Annual Cost | Cumulative Monthly |
|-------|-------------|----------|--------------|-------------|-------------------|
| **Phase 1** | Current (AI Chat with mock data) | 5 services | $136 | $1,632 | $136 |
| **Phase 2** | + Voice (Connect inbound + Pinpoint outbound) | +11 services | $125-228 | $1,500-2,736 | $261-364 |
| **Phase 3** | + SMS (Pinpoint SMS) | +8 services | $35-61 | $420-732 | $296-425 |
| | **TOTAL (All Phases)** | **24 services** | **$296-425** | **$3,552-5,100** | |

### Cost Breakdown by Service Category

| Category | Phase 1 | Phase 2 | Phase 3 | Total |
|----------|---------|---------|---------|-------|
| **AI/ML** (Bedrock, Lex) | $135 | $15-30 | $0 | $150-165 |
| **Compute** (Lambda) | $0.20 | $0.80 | $0.30 | $1.30 |
| **Storage** (S3, DynamoDB) | $0.01 | $8-15 | $3-5 | $11-20 |
| **Inbound Voice** (Connect, Transcribe) | $0 | $18-25 | $0 | $18-25 |
| **Outbound Voice** (Pinpoint Voice) | $0 | $50-100 | $0 | $50-100 |
| **SMS** (Pinpoint SMS, SNS) | $0 | $0 | $25-50 | $25-50 |
| **Text-to-Speech** (Polly) | $0 | $4-8 | $0 | $4-8 |
| **Monitoring** (CloudWatch) | $0.50 | $10-15 | $0 | $10-15 |
| **Security** (Secrets, KMS) | $0 | $0.80 | $0 | $0.80 |
| **API** (API Gateway) | $0 | $3.50 | $0.50 | $4.00 |
| **Orchestration** (Step Functions, EventBridge) | $0 | $0 | $5 | $5 |
| **Other** (SNS, SQS) | $0 | $0.50 | $1 | $1.50 |
| **TOTAL** | **$136** | **$125-228** | **$35-61** | **$296-425** |

### Cost Optimization Strategies

| Strategy | Savings | Phase | Implementation |
|----------|---------|-------|----------------|
| **Lambda Memory Right-sizing** | 10-20% | All | Profile and optimize memory allocation |
| **DynamoDB On-Demand Pricing** | 20-40% | 2, 3 | Use on-demand for variable workloads |
| **Reserved Capacity (Connect)** | 30-40% | 2 | 1-year commit for predictable usage |
| **S3 Lifecycle Policies** | 50-70% | All | Move old logs to Glacier after 90 days |
| **CloudWatch Log Retention** | 30-50% | All | Reduce retention to 30 days |
| **Pinpoint Message Batching** | 10-15% | 3 | Batch multiple SMS in campaigns |
| **Budget Alerts** | Alert only | All | Notify at 80% of budget |
| **Auto-scaling** | 20-30% | 2, 3 | Scale down during off-peak hours |

**Estimated Total Savings**: 20-35% = **$58-147/month**

---

## Permissions Matrix

### Complete IAM Permissions by Service

| Service | Phase | Read Permissions | Write Permissions | Admin Permissions |
|---------|-------|-----------------|-------------------|-------------------|
| **AWS Bedrock** | 1 | `GetAgent`<br>`GetAgentAlias`<br>`ListAgents` | `InvokeModel`<br>`InvokeAgent`<br>`PrepareAgent` | `CreateAgent`<br>`UpdateAgent`<br>`DeleteAgent` |
| **AWS Lambda** | 1, 2, 3 | `GetFunction`<br>`ListFunctions` | `InvokeFunction` | `CreateFunction`<br>`UpdateFunctionCode` |
| **Amazon S3** | 1 | `GetObject`<br>`ListBucket` | `PutObject` | `CreateBucket`<br>`PutBucketVersioning` |
| **AWS IAM** | 1, 2, 3 | `GetRole`<br>`ListRoles` | `PassRole`<br>`PutRolePolicy` | `CreateRole`<br>`DeleteRole` |
| **CloudWatch Logs** | 1, 2, 3 | `GetLogEvents`<br>`DescribeLogGroups` | `PutLogEvents` | `CreateLogGroup`<br>`CreateLogStream` |
| **Amazon Connect** | 2 | `connect:DescribeInstance`<br>`connect:GetContactAttributes` | `connect:UpdateContactAttributes` | `connect:CreateInstance`<br>`connect:UpdateInstanceAttribute` |
| **Amazon Pinpoint Voice** | 2 | `mobiletargeting:GetCampaign`<br>`mobiletargeting:GetEndpoint` | `mobiletargeting:SendMessages`<br>`mobiletargeting:SendVoiceMessage` | `mobiletargeting:CreateCampaign`<br>`mobiletargeting:CreateApp` |
| **Amazon Lex** | 2 | `lex:GetBot`<br>`lex:GetIntent` | `lex:PostContent`<br>`lex:PostText`<br>`lex:RecognizeText` | `lex:PutBot`<br>`lex:PutIntent` |
| **Amazon Polly** | 2 | `polly:DescribeVoices` | `polly:SynthesizeSpeech` | N/A |
| **Amazon Transcribe** | 2 | `transcribe:GetTranscriptionJob` | `transcribe:StartStreamTranscription`<br>`transcribe:StartTranscriptionJob` | N/A |
| **DynamoDB** | 2, 3 | `dynamodb:GetItem`<br>`dynamodb:Query`<br>`dynamodb:Scan` | `dynamodb:PutItem`<br>`dynamodb:UpdateItem`<br>`dynamodb:DeleteItem` | `dynamodb:CreateTable`<br>`dynamodb:UpdateTable` |
| **Amazon Pinpoint** | 3 | `mobiletargeting:GetEndpoint`<br>`mobiletargeting:GetCampaign` | `mobiletargeting:SendMessages`<br>`mobiletargeting:UpdateEndpoint` | `mobiletargeting:CreateCampaign`<br>`mobiletargeting:CreateApp` |
| **Amazon SNS** | 2, 3 | `sns:GetTopicAttributes`<br>`sns:ListTopics` | `sns:Publish` | `sns:CreateTopic`<br>`sns:Subscribe` |
| **Amazon SQS** | 3 | `sqs:GetQueueAttributes`<br>`sqs:ReceiveMessage` | `sqs:SendMessage`<br>`sqs:DeleteMessage` | `sqs:CreateQueue`<br>`sqs:DeleteQueue` |
| **EventBridge** | 2, 3 | `events:DescribeRule`<br>`events:ListRules` | `events:PutTargets` | `events:PutRule`<br>`events:EnableRule` |
| **API Gateway** | 2, 3 | `apigateway:GET` | N/A | `apigateway:POST`<br>`apigateway:PATCH` |
| **Step Functions** | 3 | `states:DescribeExecution`<br>`states:GetExecutionHistory` | `states:StartExecution` | `states:CreateStateMachine`<br>`states:UpdateStateMachine` |
| **Secrets Manager** | 2 | `secretsmanager:GetSecretValue`<br>`secretsmanager:DescribeSecret` | `secretsmanager:PutSecretValue` | `secretsmanager:CreateSecret`<br>`secretsmanager:RotateSecret` |

### Service Quotas & Limits

| Service | Quota Type | Default Limit | Phase | Notes |
|---------|-----------|---------------|-------|-------|
| **Bedrock** | Agent invocations | 10,000/min | 1 | Per region |
| **Lambda** | Concurrent executions | 1,000 | 1, 2, 3 | Account-wide |
| **Lambda** | Function timeout | 15 min | 1, 2, 3 | Configurable |
| **Connect** | Concurrent calls | 10 | 2 | Soft limit, can increase |
| **Connect** | Outbound calls/sec | 10 | 2 | API rate limit |
| **Lex** | Requests/sec | 1,000 | 2 | Per bot |
| **Pinpoint** | SMS/sec | 20 | 3 | Standard throughput |
| **Pinpoint** | SMS/day | 100,000 | 3 | Soft limit |
| **DynamoDB** | On-demand throughput | Unlimited | 2, 3 | Pay per request |
| **DynamoDB** | Table size | Unlimited | 2, 3 | No limit |
| **API Gateway** | Requests/sec | 10,000 | 2, 3 | Burst limit |
| **Step Functions** | Executions/sec | 2,000 | 3 | Per account |

---

## Appendix: Sample IAM Policies

### Phase 1: Bedrock Agent Execution Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-5-*",
        "arn:aws:bedrock:*:618048437522:inference-profile/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": ["arn:aws:s3:::pf-schemas-dev-618048437522/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": ["arn:aws:lambda:us-east-1:618048437522:function:pf-*-actions"]
    }
  ]
}
```

### Phase 2: Connect Lambda Execution Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "connect:StartOutboundVoiceContact",
        "connect:GetContactAttributes",
        "connect:UpdateContactAttributes"
      ],
      "Resource": ["arn:aws:connect:us-east-1:618048437522:instance/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["lex:PostContent", "lex:PostText"],
      "Resource": ["arn:aws:lex:us-east-1:618048437522:bot-alias/*/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query"],
      "Resource": ["arn:aws:dynamodb:us-east-1:618048437522:table/pf-call-*"]
    }
  ]
}
```

### Phase 3: Pinpoint SMS Handler Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mobiletargeting:SendMessages",
        "mobiletargeting:GetEndpoint",
        "mobiletargeting:UpdateEndpoint"
      ],
      "Resource": ["arn:aws:mobiletargeting:us-east-1:618048437522:apps/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query"],
      "Resource": ["arn:aws:dynamodb:us-east-1:618048437522:table/pf-sms-*"]
    },
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": ["arn:aws:sns:us-east-1:618048437522:pf-sms-*"]
    }
  ]
}
```

---

**Document Version**: 2.0
**Last Updated**: October 22, 2025
**Maintained By**: Infrastructure Team
**Review Schedule**: Quarterly
