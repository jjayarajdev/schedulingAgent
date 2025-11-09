# AWS SMS Integration Plan for ProjectForce Bedrock Agents

**Date:** November 9, 2025
**Status:** Planning Phase
**Integration Type:** Two-Way SMS using AWS End User Messaging

---

## Executive Summary

Add SMS messaging capability to ProjectForce Bedrock agents, allowing customers to interact with the scheduling system via text messages. This complements the existing voice integration and provides an asynchronous communication channel.

**Key Benefits:**
- ✅ Asynchronous communication (no need for real-time availability)
- ✅ Lower cost than voice calls (~$0.00645/message vs $0.018/min)
- ✅ Message history automatically preserved
- ✅ Easier for quick confirmations and updates
- ✅ No phone time required

---

## Architecture Overview

```
Customer SMS
    ↓
AWS End User Messaging (Phone Number)
    ↓
Amazon SNS Topic (sms-inbound)
    ↓
Lambda Function (sms-bedrock-bridge)
    ↓
Bedrock Supervisor Agent
    ↓
Specialist Agents (Scheduling, Information, ChitChat)
    ↓
Lambda Function (sms-bedrock-bridge)
    ↓
AWS End User Messaging (Send SMS)
    ↓
Customer SMS
```

---

## AWS Services Required

### 1. AWS End User Messaging SMS (formerly Pinpoint SMS)

**Purpose:** Send and receive SMS messages

**Configuration:**
- Request phone number (Toll-Free Number recommended for US)
- Enable two-way SMS
- Configure SNS topic for incoming messages

**Pricing:**
- Outbound SMS: $0.00645/message (US)
- Inbound SMS: $0.0075/message (US)
- Phone number: $2.00/month (US Toll-Free)

**Note:** Amazon Pinpoint is being deprecated on October 30, 2026, but SMS APIs remain supported under AWS End User Messaging.

### 2. Amazon SNS (Simple Notification Service)

**Purpose:** Route incoming SMS messages to Lambda

**Configuration:**
- Create topic: `pf-sms-inbound`
- Subscribe Lambda function
- Set delivery policy for retries

**Pricing:**
- $0.50 per 1 million requests
- Effectively free for SMS volume

### 3. AWS Lambda

**Purpose:** Bridge SMS messages to Bedrock Supervisor

**Functions:**
- `pf-sms-bedrock-bridge` - Handle incoming/outgoing SMS
- Reuse existing `pf-voice-bedrock-bridge` logic

**Configuration:**
- Runtime: Python 3.11
- Timeout: 60 seconds
- Memory: 512 MB
- Environment variables:
  - SUPERVISOR_AGENT_ID
  - SUPERVISOR_AGENT_ALIAS_ID
  - DYNAMODB_TABLE (for session management)
  - SMS_PHONE_NUMBER

### 4. Amazon DynamoDB

**Purpose:** Track SMS conversation sessions

**Table:** Reuse existing `pf-session-data-dev`

**Schema:**
```json
{
  "session_id": "sms_+1234567890_20250109",
  "channel": "sms",
  "phone_number": "+1234567890",
  "customer_id": "CUST001",
  "conversation_history": [...],
  "created_at": "2025-01-09T10:30:00Z",
  "last_activity": "2025-01-09T10:35:00Z",
  "expires_at": 1736428800
}
```

---

## Implementation Plan

### Phase 1: Infrastructure Setup (Week 1)

#### Step 1.1: Request Phone Number
- Sign up for AWS End User Messaging SMS
- Request US Toll-Free Number (TFN)
- Wait for approval (1-2 weeks for TFN)
- Alternative: Use long code (10DLC) - faster but requires registration

#### Step 1.2: Configure SNS Topic
```bash
# Create SNS topic for incoming SMS
aws sns create-topic --name pf-sms-inbound --region us-east-1

# Set delivery policy
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:pf-sms-inbound \
  --attribute-name DeliveryPolicy \
  --attribute-value '{"http":{"defaultHealthyRetryPolicy":{"numRetries":3}}}'
```

#### Step 1.3: Enable Two-Way SMS
- Configure phone number to publish to SNS topic
- Test message delivery to SNS

### Phase 2: Lambda Development (Week 1)

#### Step 2.1: Create SMS Bridge Lambda

**File:** `lambda/sms-bedrock-bridge/handler.py`

```python
import json
import boto3
import os
from datetime import datetime, timedelta

bedrock_runtime = boto3.client('bedrock-agent-runtime')
dynamodb = boto3.resource('dynamodb')
pinpoint_sms = boto3.client('pinpoint-sms-voice-v2')

SUPERVISOR_AGENT_ID = os.environ['SUPERVISOR_AGENT_ID']
SUPERVISOR_ALIAS_ID = os.environ['SUPERVISOR_AGENT_ALIAS_ID']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']
SMS_PHONE_NUMBER = os.environ['SMS_PHONE_NUMBER']

def lambda_handler(event, context):
    """
    Handle incoming SMS messages from SNS

    Event format from AWS End User Messaging:
    {
        "Records": [{
            "Sns": {
                "Message": "{
                    \"originationNumber\": \"+1234567890\",
                    \"destinationNumber\": \"+1987654321\",
                    \"messageKeyword\": \"KEYWORD\",
                    \"messageBody\": \"Hello, I need to schedule\",
                    \"inboundMessageId\": \"...\",
                    \"previousPublishedMessageId\": \"...\"
                }"
            }
        }]
    }
    """

    # Parse SNS message
    sns_message = json.loads(event['Records'][0]['Sns']['Message'])

    phone_number = sns_message['originationNumber']
    message_text = sns_message['messageBody']

    # Get or create session
    session_id = f"sms_{phone_number}_{datetime.now().strftime('%Y%m%d')}"
    session_data = get_session(session_id, phone_number)

    # Invoke Bedrock Supervisor
    response = invoke_bedrock_supervisor(
        session_id=session_id,
        input_text=message_text,
        session_attributes=session_data.get('attributes', {})
    )

    # Format response for SMS (max 160 chars for single message)
    sms_response = format_for_sms(response['response'])

    # Send SMS response
    send_sms(phone_number, sms_response)

    # Update session
    update_session(session_id, phone_number, message_text, sms_response)

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'SMS processed successfully'})
    }

def invoke_bedrock_supervisor(session_id, input_text, session_attributes):
    """Invoke Bedrock Supervisor agent"""
    try:
        response = bedrock_runtime.invoke_agent(
            agentId=SUPERVISOR_AGENT_ID,
            agentAliasId=SUPERVISOR_ALIAS_ID,
            sessionId=session_id,
            inputText=input_text,
            sessionState={
                'sessionAttributes': session_attributes
            }
        )

        # Collect streaming response
        full_response = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    full_response += chunk['bytes'].decode('utf-8')

        return {'response': full_response}

    except Exception as e:
        print(f"Bedrock error: {str(e)}")
        return {
            'response': "I'm having trouble processing your request. Please try again or call us."
        }

def format_for_sms(text):
    """
    Format Bedrock response for SMS
    - Remove markdown formatting
    - Limit to 160 characters for single message
    - Or split into multiple messages
    """
    # Remove markdown
    text = text.replace('**', '').replace('*', '').replace('`', '')
    text = text.replace('\n\n', '\n')

    # Truncate to 160 chars (or implement multi-part SMS)
    if len(text) > 160:
        # Option 1: Truncate
        text = text[:157] + "..."

        # Option 2: Split into multiple messages (implement later)
        # messages = [text[i:i+160] for i in range(0, len(text), 160)]

    return text.strip()

def send_sms(destination_number, message):
    """Send SMS using AWS End User Messaging"""
    try:
        response = pinpoint_sms.send_text_message(
            DestinationPhoneNumber=destination_number,
            OriginationIdentity=SMS_PHONE_NUMBER,
            MessageBody=message,
            MessageType='TRANSACTIONAL'
        )
        print(f"SMS sent: {response['MessageId']}")
        return response

    except Exception as e:
        print(f"Error sending SMS: {str(e)}")
        raise

def get_session(session_id, phone_number):
    """Get or create session from DynamoDB"""
    table = dynamodb.Table(DYNAMODB_TABLE)

    try:
        response = table.get_item(Key={'session_id': session_id})
        if 'Item' in response:
            return response['Item']
    except Exception as e:
        print(f"DynamoDB get error: {str(e)}")

    # Create new session
    return {
        'session_id': session_id,
        'channel': 'sms',
        'phone_number': phone_number,
        'created_at': datetime.now().isoformat(),
        'attributes': {}
    }

def update_session(session_id, phone_number, user_message, bot_response):
    """Update session in DynamoDB"""
    table = dynamodb.Table(DYNAMODB_TABLE)

    try:
        table.put_item(
            Item={
                'session_id': session_id,
                'channel': 'sms',
                'phone_number': phone_number,
                'last_message_user': user_message,
                'last_message_bot': bot_response,
                'last_activity': datetime.now().isoformat(),
                'expires_at': int((datetime.now() + timedelta(hours=24)).timestamp())
            }
        )
    except Exception as e:
        print(f"DynamoDB update error: {str(e)}")
```

#### Step 2.2: Create Deployment Package

**File:** `lambda/sms-bedrock-bridge/requirements.txt`
```
boto3>=1.34.0
```

### Phase 3: Terraform Configuration (Week 1)

#### Step 3.1: Create Terraform Module

**File:** `infrastructure/terraform/sms/main.tf`

```hcl
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "ProjectForce"
      ManagedBy   = "Terraform"
      Phase       = "SMS"
      Environment = var.environment
    }
  }
}

data "aws_caller_identity" "current" {}

# SNS Topic for incoming SMS
resource "aws_sns_topic" "sms_inbound" {
  name = "${var.prefix}-sms-inbound-${var.environment}"

  tags = {
    Name = "${var.prefix}-sms-inbound-${var.environment}"
  }
}

# Lambda function for SMS-Bedrock bridge
resource "aws_lambda_function" "sms_bedrock_bridge" {
  filename         = "${path.module}/../../../lambda/sms-bedrock-bridge/deployment.zip"
  function_name    = "${var.prefix}-sms-bedrock-bridge-${var.environment}"
  role             = aws_iam_role.sms_bedrock_bridge.arn
  handler          = "handler.lambda_handler"
  source_code_hash = filebase64sha256("${path.module}/../../../lambda/sms-bedrock-bridge/deployment.zip")
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 512

  environment {
    variables = {
      SUPERVISOR_AGENT_ID       = var.supervisor_agent_id
      SUPERVISOR_AGENT_ALIAS_ID = var.supervisor_agent_alias_id
      DYNAMODB_TABLE            = var.dynamodb_table_name
      SMS_PHONE_NUMBER          = var.sms_phone_number
    }
  }

  tags = {
    Name = "${var.prefix}-sms-bedrock-bridge-${var.environment}"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "sms_bedrock_bridge" {
  name              = "/aws/lambda/${aws_lambda_function.sms_bedrock_bridge.function_name}"
  retention_in_days = 14

  tags = {
    Name = "${var.prefix}-sms-bridge-logs-${var.environment}"
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "sms_bedrock_bridge" {
  name = "${var.prefix}-sms-bedrock-bridge-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.prefix}-sms-bedrock-bridge-role-${var.environment}"
  }
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "sms_bedrock_bridge" {
  name = "${var.prefix}-sms-bedrock-bridge-policy-${var.environment}"
  role = aws_iam_role.sms_bedrock_bridge.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.prefix}-sms-bedrock-bridge-${var.environment}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = "arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.dynamodb_table_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgent"
        ]
        Resource = [
          "arn:aws:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:agent/${var.supervisor_agent_id}",
          "arn:aws:bedrock:${var.region}:${data.aws_caller_identity.current.account_id}:agent-alias/${var.supervisor_agent_id}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sms-voice:SendTextMessage"
        ]
        Resource = "*"
      }
    ]
  })
}

# SNS Topic Subscription
resource "aws_sns_topic_subscription" "sms_lambda" {
  topic_arn = aws_sns_topic.sms_inbound.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.sms_bedrock_bridge.arn
}

# Lambda permission for SNS
resource "aws_lambda_permission" "sns_invoke" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sms_bedrock_bridge.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.sms_inbound.arn
}

# Outputs
output "sms_bedrock_bridge_function_name" {
  description = "SMS-Bedrock Bridge Lambda Function Name"
  value       = aws_lambda_function.sms_bedrock_bridge.function_name
}

output "sms_bedrock_bridge_function_arn" {
  description = "SMS-Bedrock Bridge Lambda Function ARN"
  value       = aws_lambda_function.sms_bedrock_bridge.arn
}

output "sns_topic_arn" {
  description = "SNS Topic ARN for incoming SMS"
  value       = aws_sns_topic.sms_inbound.arn
}
```

**File:** `infrastructure/terraform/sms/variables.tf`

```hcl
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "prefix" {
  description = "Project prefix"
  type        = string
  default     = "pf"
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "dev"
}

variable "supervisor_agent_id" {
  description = "Bedrock Supervisor Agent ID"
  type        = string
}

variable "supervisor_agent_alias_id" {
  description = "Bedrock Supervisor Agent Alias ID"
  type        = string
  default     = "TSTALIASID"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table for sessions"
  type        = string
  default     = "pf-session-data-dev"
}

variable "sms_phone_number" {
  description = "SMS phone number (Toll-Free or 10DLC)"
  type        = string
}
```

### Phase 4: Deployment Script (Week 1)

**File:** `scripts/DEPLOY_SMS.sh`

```bash
#!/bin/bash

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform/sms"
LAMBDA_DIR="$PROJECT_ROOT/lambda"
CONFIG_FILE="$PROJECT_ROOT/config/agent_ids.json"
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  SMS Integration Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Load agent IDs
SUPERVISOR_AGENT_ID=$(jq -r '.agents.Supervisor.id' "$CONFIG_FILE")
SUPERVISOR_ALIAS_ID=$(aws bedrock-agent list-agent-aliases \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --region "$REGION" \
  --query 'agentAliasSummaries[?agentAliasName==`v1`].agentAliasId' \
  --output text || echo "TSTALIASID")

echo ""
echo "Enter SMS phone number (e.g., +18001234567):"
read -p "> " SMS_PHONE_NUMBER

# Package Lambda
echo -e "${YELLOW}Packaging Lambda function...${NC}"
cd "$LAMBDA_DIR/sms-bedrock-bridge"
rm -f deployment.zip
pip3 install -r requirements.txt -t package/ -q
cd package && zip -r ../deployment.zip . -q && cd ..
zip -g deployment.zip handler.py -q
echo -e "${GREEN}✅ Lambda packaged${NC}"

# Deploy Terraform
cd "$TERRAFORM_DIR"
cat > terraform.tfvars <<EOF
supervisor_agent_id       = "$SUPERVISOR_AGENT_ID"
supervisor_agent_alias_id = "$SUPERVISOR_ALIAS_ID"
sms_phone_number          = "$SMS_PHONE_NUMBER"
EOF

terraform init -upgrade
terraform apply -auto-approve

echo -e "${GREEN}✅ SMS integration deployed${NC}"
```

---

## Conversation Flow Examples

### Example 1: Schedule Appointment

```
Customer: Hi, I need to schedule my project
Bot: Hello! I can help you schedule. What's your project ID?

Customer: 12345
Bot: Found project at 123 Main St. When would you like to schedule?

Customer: Next Tuesday
Bot: Available times for Jan 14:
1. 9:00 AM
2. 1:00 PM
3. 3:00 PM
Reply with number

Customer: 2
Bot: Confirmed! Jan 14 at 1:00 PM for project 12345. You'll receive a reminder.
```

### Example 2: Weather Check

```
Customer: What's the weather like?
Bot: I can check the weather. What's the address?

Customer: 123 Main St Tampa FL
Bot: Tampa weather: Sunny, 75°F. Perfect day for your appointment!
```

### Example 3: Quick Status

```
Customer: STATUS 12345
Bot: Project 12345: Scheduled for Jan 14, 1:00 PM. Crew assigned. All set!
```

---

## Features & Capabilities

### Phase 1 Features (MVP)
- ✅ Two-way SMS messaging
- ✅ Session management (24-hour context)
- ✅ Bedrock Supervisor integration
- ✅ Basic conversation flow
- ✅ Error handling and fallback responses

### Phase 2 Features (Enhanced)
- ⏳ Multi-part SMS messages (>160 chars)
- ⏳ Rich formatting (links, emojis)
- ⏳ Image/attachment support (MMS)
- ⏳ Automated reminders
- ⏳ Broadcast messaging
- ⏳ Opt-in/opt-out management

### Phase 3 Features (Advanced)
- ⏳ Natural language understanding
- ⏳ Sentiment analysis
- ⏳ Multi-language support
- ⏳ Analytics dashboard
- ⏳ A/B testing
- ⏳ Integration with CRM

---

## Message Templates

### Welcome Message
```
Welcome to ProjectForce! Text HELP for commands or ask a question. Reply STOP to opt out.
```

### Help Message
```
Commands:
• SCHEDULE - Book appointment
• STATUS <ID> - Check project
• WEATHER - Get forecast
• HELP - This message

Or just ask a question!
```

### Error Message
```
Sorry, I didn't understand. Text HELP for commands or try rephrasing your question.
```

### Appointment Confirmation
```
✅ Appointment confirmed!
📅 {date} at {time}
📍 {address}
📞 Questions? Reply here.
```

---

## Cost Estimate

### SMS Pricing (US)
- Outbound SMS: $0.00645/message
- Inbound SMS: $0.0075/message
- Phone number: $2.00/month (TFN)

### Monthly Cost (100 conversations, 5 messages avg)
```
Inbound:  100 × 2.5 × $0.0075  = $1.88
Outbound: 100 × 2.5 × $0.00645 = $1.61
Phone:    1 × $2.00             = $2.00
Lambda:   500 invocations       = ~$0.10
DynamoDB: Minimal               = ~$0.25
Bedrock:  ~500 requests         = ~$5.00
--------------------------------
Total:                            ~$10.84/month
```

### Monthly Cost (1,000 conversations)
```
Total: ~$93/month
```

**Compare to Voice:**
- Voice: 1,000 calls × 5 min × $0.018/min = $90/month (calls only)
- SMS: $93/month (includes infrastructure)

---

## Compliance & Best Practices

### Regulatory Compliance

**TCPA (Telephone Consumer Protection Act)**
- ✅ Obtain explicit consent before messaging
- ✅ Provide clear opt-out mechanism (STOP)
- ✅ Honor opt-out requests immediately
- ✅ Include business identification

**10DLC Registration (for non-TFN)**
- Register business with carrier
- Verify use case
- Wait for approval (1-2 weeks)

**CTIA Messaging Principles**
- Obtain consent
- Be transparent
- Respect privacy
- Enable choice

### Message Best Practices

1. **Keep it short:** SMS is 160 characters
2. **Be clear:** Avoid jargon
3. **Be personal:** Use customer name when possible
4. **Be timely:** Respond within 5 minutes
5. **Be helpful:** Provide value in every message

### Security Considerations

- ✅ Don't send sensitive data (SSN, credit cards)
- ✅ Use secure channels for payment
- ✅ Implement rate limiting
- ✅ Monitor for abuse/spam
- ✅ Encrypt data at rest and in transit

---

## Testing Plan

### Unit Tests
```python
# Test Lambda handler
def test_sms_handler_valid_message():
    event = create_sns_event("+1234567890", "Hello")
    response = lambda_handler(event, None)
    assert response['statusCode'] == 200

def test_format_for_sms():
    long_text = "This is a very long message..." * 10
    formatted = format_for_sms(long_text)
    assert len(formatted) <= 160
```

### Integration Tests
```bash
# Test end-to-end SMS flow
python3 test_sms_integration.py --phone "+1234567890"
```

### Manual Testing Scenarios
1. Send "HELP" → Receive help message
2. Send "STATUS 12345" → Receive project status
3. Send "SCHEDULE" → Start appointment booking flow
4. Send "WEATHER" → Get weather info
5. Send "STOP" → Opt out

---

## Monitoring & Analytics

### CloudWatch Metrics
- SMS received count
- SMS sent count
- Lambda invocation count
- Lambda error rate
- Response time (p50, p95, p99)
- Bedrock invocation count

### CloudWatch Alarms
```hcl
resource "aws_cloudwatch_metric_alarm" "sms_errors" {
  alarm_name          = "pf-sms-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "SMS Lambda error rate too high"

  dimensions = {
    FunctionName = aws_lambda_function.sms_bedrock_bridge.function_name
  }
}
```

### Dashboard
- Message volume (hourly, daily)
- Response times
- Error rates
- Top conversation topics
- Customer satisfaction (based on feedback)

---

## Roadmap

### Week 1-2: Foundation
- [ ] Request phone number
- [ ] Create Lambda function
- [ ] Deploy Terraform infrastructure
- [ ] Test basic two-way messaging

### Week 3-4: Integration
- [ ] Integrate with Bedrock Supervisor
- [ ] Implement session management
- [ ] Add error handling
- [ ] Test conversation flows

### Week 5-6: Enhancement
- [ ] Add multi-part message support
- [ ] Implement message templates
- [ ] Add analytics tracking
- [ ] Create monitoring dashboard

### Week 7-8: Production
- [ ] Load testing
- [ ] Security audit
- [ ] Documentation
- [ ] Go live

---

## Comparison: Voice vs SMS

| Feature | Voice | SMS |
|---------|-------|-----|
| **Cost** | $0.018/min | $0.00645/msg |
| **Speed** | Real-time | Asynchronous |
| **Complexity** | High (Lex, Connect) | Medium (SNS, Lambda) |
| **User Preference** | 40% | 60% |
| **Automation** | Complex (TTS/STT) | Simple (text) |
| **Message History** | No | Yes |
| **Multitasking** | No | Yes |
| **Accessibility** | Requires speaking | Text-based |
| **Infrastructure** | 5 services | 3 services |

**Recommendation:** Deploy both! Voice for urgent/complex, SMS for quick/async.

---

## Next Steps

1. **Decision Point:** Proceed with SMS integration?
2. **Phone Number:** Request Toll-Free Number (2 weeks) or 10DLC (1 week)?
3. **Development:** Create Lambda function (1 day)
4. **Deployment:** Deploy infrastructure (1 day)
5. **Testing:** Test end-to-end flow (2 days)
6. **Documentation:** Update guides (1 day)

**Total Time:** 3-4 weeks to production

---

## Related Documentation

- [Voice Integration Plan](./AWS_CONSOLE_SETUP_GUIDE.md)
- [Bedrock Architecture](./FINAL_AGENT_ARCHITECTURE.md)
- [Deployment Scripts Reference](./DEPLOYMENT_SCRIPTS_REFERENCE.md)

---

## References

- [AWS End User Messaging SMS Documentation](https://docs.aws.amazon.com/pinpoint/latest/userguide/channels-sms-two-way.html)
- [Two-Way SMS Tutorial](https://docs.aws.amazon.com/pinpoint/latest/userguide/tutorials-two-way-sms.html)
- [AWS SMS Pricing](https://aws.amazon.com/sns/sms-pricing/)
- [TCPA Compliance](https://www.fcc.gov/tcpa)
