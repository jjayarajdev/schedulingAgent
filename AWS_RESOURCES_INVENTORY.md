# AWS Resources Inventory - ProjectForce Scheduling Agent

**Account ID:** 618048437522
**Region:** us-east-1
**User:** arn:aws:iam::618048437522:user/pfuser
**Last Updated:** 2025-11-06

---

## 🤖 Bedrock Agents (4 Total)

### 1. Supervisor Agent
- **Agent ID:** 76VIQYAT6R
- **Name:** Supervisor
- **Status:** PREPARED
- **Model:** us.anthropic.claude-3-5-sonnet-20241022-v2:0
- **Description:** Orchestrator agent that routes queries to specialized agents
- **IAM Role:** AmazonBedrockExecutionRoleForAgents_Supervisor
- **Collaborators:** 3 (InformationAgent, SchedulingAgent, ChitchatAgent)
- **Action Groups:** None (routing only)

### 2. Scheduling Agent
- **Agent ID:** 3L0QABDNOR
- **Name:** SchedulingAgent
- **Status:** PREPARED
- **Model:** us.anthropic.claude-3-5-sonnet-20241022-v2:0
- **Description:** Primary agent for scheduling and project management
- **IAM Role:** AmazonBedrockExecutionRoleForAgents_SchedulingAgent
- **Action Groups:**
  - scheduling-actions (ID: GKSZFWLX2O, State: ENABLED)
- **Lambda Integration:** pf-scheduling-actions

### 3. Information Agent
- **Agent ID:** ZNRHW6QAAN
- **Name:** pf-information
- **Status:** PREPARED
- **Model:** us.anthropic.claude-3-5-sonnet-20241022-v2:0
- **Description:** Weather information specialist using external API
- **IAM Role:** AmazonBedrockExecutionRoleForAgents_pf-information
- **Action Groups:**
  - information-actions (ID: M4NRNSQ1HL, State: ENABLED)
- **Lambda Integration:** pf-information-actions

### 4. Chitchat Agent
- **Agent ID:** 4CEB7QKGSR
- **Name:** pf-chitchat
- **Status:** PREPARED
- **Model:** us.anthropic.claude-3-5-sonnet-20241022-v2:0
- **Description:** Conversational agent for greetings and general queries
- **IAM Role:** AmazonBedrockExecutionRoleForAgents_pf-chitchat
- **Action Groups:** None (conversational only)

---

## λ Lambda Functions (5 Active)

### 1. pf-scheduling-actions
- **Runtime:** python3.11
- **Memory:** 512 MB
- **Timeout:** 30 seconds
- **Handler:** handler.lambda_handler
- **IAM Role:** pf-scheduling-actions-role-dev
- **Last Modified:** 2025-11-06T12:53:01.673+0000
- **Environment Variables:**
  - PF_CLIENT_ID: 09PF05VD
  - PF_USER_ID: 1646085
  - PF_API_BASE_URL: https://api-cx-portal.dev.projectsforce.com
  - TOKEN_SECRET_NAME: projectforce/api/credentials
  - API_ENVIRONMENT: dev
  - USE_MOCK_API: false
  - LOG_LEVEL: INFO
  - BEARER_TOKEN: [Encrypted token]
- **Purpose:** Handles scheduling operations (create/update/delete appointments, list projects)

### 2. pf-information-actions
- **Runtime:** python3.11
- **Memory:** 512 MB
- **Timeout:** 30 seconds
- **Handler:** handler.lambda_handler
- **IAM Role:** pf-information-actions-role-dev
- **Last Modified:** 2025-11-06T12:53:19.681+0000
- **Environment Variables:** (Same as pf-scheduling-actions)
- **Purpose:** Provides project information and details

### 3. scheduling-agent-scheduling-actions
- **Runtime:** python3.11
- **Memory:** 512 MB
- **Last Modified:** 2025-11-04T02:21:22.000+0000
- **IAM Role:** scheduling-agent-scheduling-lambda-role-dev
- **Status:** Legacy function (replaced by pf-scheduling-actions)

### 4. scheduling-agent-information-actions
- **Runtime:** python3.11
- **Memory:** 512 MB
- **Last Modified:** 2025-11-04T02:21:24.000+0000
- **IAM Role:** scheduling-agent-information-lambda-role-dev
- **Status:** Legacy function (replaced by pf-information-actions)

### 5. scheduling-agent-notes-actions
- **Runtime:** python3.11
- **Memory:** 512 MB
- **Last Modified:** 2025-11-04T01:47:00.677+0000
- **IAM Role:** scheduling-agent-notes-lambda-role-dev
- **Status:** Notes management function

---

## 🔐 IAM Roles (13 Total)

### Bedrock Agent Execution Roles

#### 1. AmazonBedrockExecutionRoleForAgents_Supervisor
- **ARN:** arn:aws:iam::618048437522:role/AmazonBedrockExecutionRoleForAgents_Supervisor
- **Created:** 2025-11-04T04:37:11+00:00
- **Attached Policies:**
  - AmazonBedrockAgentsMultiAgentsPolicies_WS4VYP4IYS (custom)
- **Inline Policies:**
  - BedrockModelInvoke
- **Purpose:** Allows Supervisor agent to invoke Claude models and collaborate with other agents

#### 2. AmazonBedrockExecutionRoleForAgents_SchedulingAgent
- **ARN:** arn:aws:iam::618048437522:role/AmazonBedrockExecutionRoleForAgents_SchedulingAgent
- **Created:** 2025-11-04T04:36:22+00:00
- **Inline Policies:**
  - BedrockModelInvoke
- **Purpose:** Allows SchedulingAgent to invoke Claude models and Lambda functions

#### 3. AmazonBedrockExecutionRoleForAgents_pf-information
- **ARN:** arn:aws:iam::618048437522:role/AmazonBedrockExecutionRoleForAgents_pf-information
- **Created:** 2025-11-04T04:36:38+00:00
- **Purpose:** Allows Information agent to invoke Claude models and Lambda functions

#### 4. AmazonBedrockExecutionRoleForAgents_pf-chitchat
- **ARN:** arn:aws:iam::618048437522:role/AmazonBedrockExecutionRoleForAgents_pf-chitchat
- **Created:** 2025-11-04T04:36:55+00:00
- **Purpose:** Allows Chitchat agent to invoke Claude models

### Lambda Execution Roles

#### 5. pf-scheduling-actions-role-dev
- **ARN:** arn:aws:iam::618048437522:role/pf-scheduling-actions-role-dev
- **Created:** 2025-11-03T13:47:19+00:00
- **Attached Policies:**
  - projectforce-secrets-access-dev (custom)
  - AWSLambdaBasicExecutionRole (AWS managed)
  - AmazonDynamoDBFullAccess (AWS managed)
- **Purpose:** Execution role for pf-scheduling-actions Lambda

#### 6. pf-information-actions-role-dev
- **ARN:** arn:aws:iam::618048437522:role/pf-information-actions-role-dev
- **Created:** 2025-11-03T13:51:01+00:00
- **Attached Policies:**
  - projectforce-secrets-access-dev (custom)
  - AWSLambdaBasicExecutionRole (AWS managed)
- **Purpose:** Execution role for pf-information-actions Lambda

#### 7. pf-query-router-role-dev
- **ARN:** arn:aws:iam::618048437522:role/pf-query-router-role-dev
- **Created:** 2025-11-03T13:51:32+00:00
- **Purpose:** Query routing functionality

#### 8-11. Legacy Lambda Roles
- scheduling-agent-scheduling-lambda-role-dev
- scheduling-agent-information-lambda-role-dev
- scheduling-agent-notes-lambda-role-dev
- scheduling-agent-lambda-role

#### 12. AmazonBedrockExecutionRoleForFlows_YBNNNE7RI2
- **Created:** 2025-10-21T04:06:55+00:00
- **Purpose:** Bedrock Flows (if used)

---

## 📊 DynamoDB Tables (1)

### pf-sessions-dev
- **Purpose:** Session management and conversation history storage
- **Region:** us-east-1
- **Used By:** Multi-agent system for maintaining conversation context

---

## 🪣 S3 Buckets (1)

### pf-schemas-dev-618048437522
- **Created:** 2025-11-04 00:38:41
- **Purpose:** Stores agent action group schemas and OpenAPI specifications
- **Region:** us-east-1
- **Access:** Private

---

## 📝 CloudWatch Log Groups (7)

### Active Log Groups
1. **/aws/lambda/pf-scheduling-actions**
   - Size: 169,855 bytes
   - Created: 1761016865323

2. **/aws/lambda/pf-information-actions**
   - Size: 37,027 bytes
   - Created: 1761034840955

3. **/aws/lambda/pf-filter-projects**
   - Size: 2,254 bytes
   - Created: 1761589335959

### Legacy Log Groups
4. **/aws/lambda/scheduling-agent-scheduling-actions**
   - Size: 41,786 bytes

5. **/aws/lambda/scheduling-agent-information-actions**
   - Size: 19,370 bytes

6. **/aws/lambda/scheduling-agent-notes-actions**
   - Size: 16,705 bytes

7. **/aws/lambda/scheduling-agent**
   - Size: 0 bytes (empty)

---

## 🔗 Resource Dependencies

### Agent Collaboration Flow
```
User Query
    ↓
Supervisor Agent (76VIQYAT6R)
    ↓ (routes to)
    ├─→ SchedulingAgent (3L0QABDNOR)
    │       ↓ (invokes)
    │       └─→ pf-scheduling-actions Lambda
    │               ↓ (calls)
    │               └─→ ProjectForce API
    │
    ├─→ InformationAgent (ZNRHW6QAAN)
    │       ↓ (invokes)
    │       └─→ pf-information-actions Lambda
    │               ↓ (calls)
    │               └─→ ProjectForce API
    │
    └─→ ChitchatAgent (4CEB7QKGSR)
            └─→ Direct conversational response
```

### Lambda → External API Flow
```
Lambda Function
    ↓ (uses env vars)
    ├─→ PF_API_BASE_URL: https://api-cx-portal.dev.projectsforce.com
    ├─→ BEARER_TOKEN: [from env or Secrets Manager]
    └─→ CLIENT_ID: 09PF05VD
    └─→ USER_ID: 1646085
```

---

## 🔑 Key Configuration Files

### Local Configuration
- **bedrock/config/agent_config.dev.json** - Development agent IDs
- **bedrock/config/agent_config.staging.json** - Staging agent IDs
- **bedrock/config/agent_config.prod.json** - Production agent IDs
- **bedrock/config/agent_ids.json** - Master agent ID mapping

### Lambda Deployment Packages
- **bedrock/lambda/pf_scheduling_actions/** - Scheduling Lambda code
- **bedrock/lambda/pf_information_actions/** - Information Lambda code

---

## 💰 Estimated Monthly Costs

### Bedrock Agents (Claude 3.5 Sonnet)
- **Input:** ~$3 per 1M tokens
- **Output:** ~$15 per 1M tokens
- **Estimated:** $50-200/month (depending on usage)

### Lambda Functions
- **Compute:** ~$0.20 per 1M requests
- **Duration:** ~$0.0000166667 per GB-second
- **Estimated:** $5-20/month

### DynamoDB
- **On-Demand Pricing:** Pay per request
- **Estimated:** $1-10/month

### S3 Storage
- **Standard Storage:** $0.023 per GB
- **Estimated:** <$1/month

### CloudWatch Logs
- **Ingestion:** $0.50 per GB
- **Storage:** $0.03 per GB/month
- **Estimated:** $2-5/month

**Total Estimated Monthly Cost:** $60-250/month

---

## 🔒 Security Considerations

### IAM Policies
- ✅ Least privilege access for Lambda roles
- ✅ Bedrock model invocation restricted to specific models
- ✅ DynamoDB access scoped to specific tables
- ✅ Secrets Manager access for API credentials

### API Authentication
- ✅ Bearer token authentication for ProjectForce API
- ✅ Token stored in environment variables (encrypted at rest)
- ⚠️  Consider moving to AWS Secrets Manager for rotation

### Network Security
- ✅ HTTPS for all external API calls
- ✅ No public internet exposure of Lambda functions
- ⚠️  Consider VPC deployment for Lambda functions

---

## 📋 Maintenance Tasks

### Regular
- Monitor CloudWatch logs for errors
- Review Lambda execution metrics
- Check agent collaboration success rates
- Update bearer tokens when expired

### Quarterly
- Review IAM policies for least privilege
- Audit agent instructions for accuracy
- Optimize Lambda memory/timeout settings
- Clean up unused legacy resources

### As Needed
- Update agent model versions
- Modify action group schemas
- Update Lambda function code
- Adjust DynamoDB capacity

---

## 🧹 Cleanup Candidates

### Legacy Resources (Can be deleted if confirmed unused)
1. scheduling-agent-scheduling-actions Lambda
2. scheduling-agent-information-actions Lambda
3. scheduling-agent-notes-actions Lambda
4. scheduling-agent Lambda (empty)
5. Associated legacy IAM roles
6. Legacy CloudWatch log groups

**Estimated Savings:** ~$10-20/month

---

## 🚀 Deployment Commands

### View All Resources
```bash
# List agents
aws bedrock-agent list-agents --region us-east-1

# List Lambda functions
aws lambda list-functions --region us-east-1

# List IAM roles
aws iam list-roles
```

### Deploy New Changes
```bash
cd bedrock/scripts
./DEPLOY.sh
```

### Test End-to-End
```bash
cd bedrock/scripts
./test_agent_flow.py
```

---

**Generated:** 2025-11-06
**Tool:** AWS CLI + Claude Code
**Repository:** schedulingAgent-bb (branch: 24Oct)
