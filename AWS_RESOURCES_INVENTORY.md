# AWS Resources Inventory - Scheduling Agent

> Complete inventory of AWS resources required to set up the Scheduling Agent in a new environment.

## AWS Account Details

| Item | Value |
|------|-------|
| **Account ID** | `772634497954` |
| **Region** | `us-east-1` |

---

## 1. Lambda Functions (Core)

| Function Name | Runtime | Timeout | Memory | Role |
|---------------|---------|---------|--------|------|
| `pf-orchestrator` | Python 3.11 | 120s | 512 MB | `pf-orchestrator-role` |
| `pf-scheduling-actions` | Python 3.11 | 60s | 1769 MB | `pf-scheduling-actions-role` |
| `pf-information-actions` | Python 3.11 | 60s | 1769 MB | `pf-information-actions-role` |
| `pf-chitchat-actions` | Python 3.11 | 60s | 1769 MB | `pf-chitchat-actions-role` |
| `pf-customer-lookup-dev` | Python 3.11 | 30s | 256 MB | `pf-customer-lookup-role-dev` |
| `pf-lex-fulfillment-dev` | Python 3.11 | 90s | 256 MB | `pf-lex-fulfillment-role-dev` |
| `pf-voice-bedrock-bridge-dev` | Python 3.11 | 30s | 256 MB | `pf-voice-bedrock-bridge-role-dev` |
| `scheduling-agent-sms-inbound-dev` | Python 3.11 | 30s | 512 MB | `scheduling-agent-lambda-sms-dev` |

### Lambda Environment Variables

#### pf-orchestrator
```bash
ORCHESTRATOR_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0
SCHEDULING_LAMBDA=pf-scheduling-actions
INFORMATION_LAMBDA=pf-information-actions
CHITCHAT_LAMBDA=pf-chitchat-actions
DYNAMODB_TABLE=pf-sessions-dev
WORKFLOW_STATE_TABLE=pf-workflow-states-dev
REGION=us-east-1
ALLOW_DIRECT_LAMBDA=true
USE_SUPERVISOR=false
ENABLE_MULTI_AGENT_ORCHESTRATION=false
```

#### pf-scheduling-actions
```bash
ENVIRONMENT=dev
USE_MOCK_API=false
DEFAULT_CLIENT_ID=09PF05VD
```

#### scheduling-agent-sms-inbound-dev
```bash
ORCHESTRATOR_LAMBDA=pf-orchestrator
SESSIONS_TABLE=scheduling-agent-sms-sessions-dev
MESSAGES_TABLE=scheduling-agent-sms-messages-dev
CONSENT_TABLE=scheduling-agent-sms-consent-dev
OPT_OUT_TRACKING_TABLE=scheduling-agent-opt-out-tracking-dev
SMS_CONFIGURATION_SET=scheduling-agent-sms-config-dev
ORIGINATION_NUMBER=+18786789053
PF_SECRET_NAME=projectforce/api/credentials
AWS_REGION_NAME=us-east-1
ENVIRONMENT=dev
```

#### pf-lex-fulfillment-dev
```bash
ENVIRONMENT=dev
```

---

## 2. IAM Roles

| Role Name | ARN |
|-----------|-----|
| `pf-orchestrator-role` | `arn:aws:iam::772634497954:role/pf-orchestrator-role` |
| `pf-scheduling-actions-role` | `arn:aws:iam::772634497954:role/pf-scheduling-actions-role` |
| `pf-information-actions-role` | `arn:aws:iam::772634497954:role/pf-information-actions-role` |
| `pf-chitchat-actions-role` | `arn:aws:iam::772634497954:role/pf-chitchat-actions-role` |
| `pf-customer-lookup-role-dev` | `arn:aws:iam::772634497954:role/pf-customer-lookup-role-dev` |
| `pf-lex-fulfillment-role-dev` | `arn:aws:iam::772634497954:role/pf-lex-fulfillment-role-dev` |
| `pf-voice-bedrock-bridge-role-dev` | `arn:aws:iam::772634497954:role/pf-voice-bedrock-bridge-role-dev` |
| `scheduling-agent-lambda-sms-dev` | `arn:aws:iam::772634497954:role/scheduling-agent-lambda-sms-dev` |
| `AmazonBedrockExecutionRoleForAgents_pf-chitchat` | `arn:aws:iam::772634497954:role/AmazonBedrockExecutionRoleForAgents_pf-chitchat` |
| `AmazonBedrockExecutionRoleForAgents_pf-information` | `arn:aws:iam::772634497954:role/AmazonBedrockExecutionRoleForAgents_pf-information` |

### Required IAM Permissions (per Lambda role)

```json
{
  "Bedrock": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Lambda": [
    "lambda:InvokeFunction"
  ],
  "DynamoDB": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:DeleteItem"
  ],
  "SecretsManager": [
    "secretsmanager:GetSecretValue"
  ],
  "CloudWatchLogs": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "SNS": [
    "sns:Publish"
  ],
  "SMSVoice": [
    "sms-voice:SendTextMessage"
  ]
}
```

---

## 3. DynamoDB Tables

| Table Name | Purpose |
|------------|---------|
| `pf-sessions-dev` | User session state storage |
| `pf-customers-dev` | Customer data lookup |
| `pf-notes-dev` | Notes/conversation history |
| `pf-workflow-states-dev` | Workflow state machine |
| `scheduling-agent-sms-sessions-dev` | SMS session tracking |
| `scheduling-agent-sms-messages-dev` | SMS message storage |
| `scheduling-agent-sms-consent-dev` | SMS consent tracking |
| `scheduling-agent-opt-out-tracking-dev` | SMS opt-out tracking |

---

## 4. Secrets Manager

| Secret Name | Purpose |
|-------------|---------|
| `projectforce/api/credentials` | ProjectForce API credentials |
| `scheduling-agent/pf360/api-credentials` | PF360 API credentials |
| `pf-api-bearer-token` | API bearer token |
| `pf/client/config/09PF05VD` | Client config for 09PF05VD |
| `dev/pf/tenant/database-credentials/09PF05VD` | DB credentials for tenant |

---

## 5. API Gateway

| API Name | API ID | Endpoint |
|----------|--------|----------|
| `pf-orchestrator-api-dev` | `fpheaag7c7` | `https://fpheaag7c7.execute-api.us-east-1.amazonaws.com/dev` |

---

## 6. Amazon Lex V2

| Item | Value |
|------|-------|
| **Bot Name** | `pf-scheduling-assistant-dev` |
| **Bot ID** | `MCMSOW2OXJ` |
| **Alias ID** | `TSTALIASID` |
| **Alias Name** | `TestBotAlias` |

---

## 7. Amazon Connect (Voice)

| Item | Value |
|------|-------|
| **Instance ID** | `3edd99db-14e2-4628-836e-478b574e4b90` |
| **Instance Alias** | `pf-schedule-voice-dev` |
| **Instance ARN** | `arn:aws:connect:us-east-1:772634497954:instance/3edd99db-14e2-4628-836e-478b574e4b90` |
| **Phone Number** | `+14702832382` (DID) |

### Contact Flows

| Flow Name | Flow ID | ARN |
|-----------|---------|-----|
| `pf-main-inbound-voice` | `6b9d1980-82df-4ca8-a448-398050cc2b57` | `arn:aws:connect:us-east-1:772634497954:instance/3edd99db-14e2-4628-836e-478b574e4b90/contact-flow/6b9d1980-82df-4ca8-a448-398050cc2b57` |
| `pf-scheduling-voice-dev` | `b830c12f-988b-4c62-8a06-3abc6b6c28c9` | `arn:aws:connect:us-east-1:772634497954:instance/3edd99db-14e2-4628-836e-478b574e4b90/contact-flow/b830c12f-988b-4c62-8a06-3abc6b6c28c9` |

### Connect Lambda Association
```
arn:aws:lambda:us-east-1:772634497954:function:pf-lex-fulfillment-dev
```

---

## 8. SMS (End User Messaging)

| Item | Value |
|------|-------|
| **SMS Phone Number** | `+18786789053` |
| **Phone ARN** | `arn:aws:sms-voice:us-east-1:772634497954:phone-number/phone-a35b5011d15b4d938b008ca1102e9658` |
| **Two-Way Enabled** | `true` |
| **SNS Topic (Inbound)** | `arn:aws:sns:us-east-1:772634497954:scheduling-agent-sms-inbound-dev` |
| **Configuration Set** | `scheduling-agent-sms-config-dev` |

---

## 9. SNS Topics

| Topic ARN | Purpose |
|-----------|---------|
| `arn:aws:sns:us-east-1:772634497954:scheduling-agent-sms-inbound-dev` | SMS inbound trigger for Lambda |

---

## 10. S3 Buckets

| Bucket Name | Purpose |
|-------------|---------|
| `pf-call-recordings-dev-772634497954` | Connect call recordings |
| `pf-schemas-dev-772634497954` | Schema storage |

---

## 11. KMS Keys

| Alias | Key ID | Purpose |
|-------|--------|---------|
| `alias/pf-connect-recordings-dev` | `335a2949-0b69-4a7c-b33d-099e81eaa592` | Encrypt call recordings |

---

## 12. Amazon Bedrock

### Model Access Required

| Model ID | Model Name | Usage |
|----------|------------|-------|
| `us.anthropic.claude-3-5-sonnet-20241022-v2:0` | Claude 3.5 Sonnet v2 | Orchestrator classification & decision |

> **Note:** Enable model access in AWS Bedrock console before use.

---

## 13. Setup Order

1. **Create IAM Roles** with required policies
2. **Create DynamoDB Tables** (8 tables)
3. **Create Secrets** in Secrets Manager (API credentials)
4. **Enable Bedrock Model Access** for Claude 3.5 Sonnet
5. **Create SNS Topic** for SMS inbound
6. **Deploy Lambda Functions** (8 functions)
7. **Create API Gateway** and link to pf-orchestrator
8. **Create Lex V2 Bot** with intents and aliases
9. **Create Connect Instance** with contact flows
10. **Request SMS Phone Number** and configure two-way messaging
11. **Configure Contact Flow** to use Lex bot and Lambda

---

## 14. Architecture Flow

```
                                    ┌─────────────────────┐
                                    │   Amazon Connect    │
                                    │  +14702832382 (DID) │
                                    └──────────┬──────────┘
                                               │
                                               ▼
┌─────────────────┐                 ┌─────────────────────┐
│   SMS Inbound   │                 │   Lex V2 Bot        │
│  +18786789053   │                 │ pf-scheduling-      │
│                 │                 │ assistant-dev       │
└────────┬────────┘                 └──────────┬──────────┘
         │                                     │
         ▼                                     ▼
┌─────────────────────┐            ┌─────────────────────┐
│  SNS Topic          │            │ pf-lex-fulfillment  │
│  sms-inbound-dev    │            │       -dev          │
└────────┬────────────┘            └──────────┬──────────┘
         │                                     │
         ▼                                     │
┌─────────────────────┐                        │
│ scheduling-agent-   │                        │
│ sms-inbound-dev     │                        │
└────────┬────────────┘                        │
         │                                     │
         └──────────────┬──────────────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │   pf-orchestrator   │
              │   (Bedrock Claude)  │
              └──────────┬──────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ pf-scheduling│  │pf-information│  │ pf-chitchat │
│   -actions   │  │   -actions   │  │  -actions   │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  ProjectForce API   │
              │   (External)        │
              └─────────────────────┘
```

---

## 15. Quick Reference Commands

### Deploy Lambda
```bash
AWS_PROFILE=pf-aws ./scripts/DEPLOY_LAMBDA_ONLY_ADVANCED.sh
```

### Tail Orchestrator Logs
```bash
AWS_PROFILE=pf-aws aws logs tail /aws/lambda/pf-orchestrator --since 5m --follow
```

### Tail SMS Inbound Logs
```bash
AWS_PROFILE=pf-aws aws logs tail /aws/lambda/scheduling-agent-sms-inbound-dev --since 5m --follow
```

### Test Orchestrator Directly
```bash
aws lambda invoke \
  --function-name pf-orchestrator \
  --payload '{"body": "{\"message\": \"hello\", \"session_id\": \"test\", \"pf_client_id\": \"09PF05VD\", \"pf_user_id\": \"1646085\", \"channel\": \"chat\"}"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/response.json
```

---

*Last Updated: December 7, 2025*
