# AWS Services & Permissions Requirements

**Project**: Scheduling Agent Multi-Agent System
**Last Updated**: October 22, 2025
**Environment**: Development (us-east-1)
**Account ID**: 618048437522

---

## Table of Contents

1. [Phase 1: Current Production (Deployed)](#phase-1-current-production-deployed)
2. [Phase 2: Scaling & Observability (Next 3-6 Months)](#phase-2-scaling--observability-next-3-6-months)
3. [Phase 3: Enterprise & Multi-Region (6-12 Months)](#phase-3-enterprise--multi-region-6-12-months)
4. [Cost Estimates](#cost-estimates)
5. [IAM Permissions Summary](#iam-permissions-summary)

---

## Phase 1: Current Production (Deployed)

**Status**: ✅ Fully Deployed and Operational
**Deployment Date**: October 2025

### AWS Services Currently in Use

| Service | Resource Count | Purpose | Monthly Cost Estimate |
|---------|---------------|---------|----------------------|
| **AWS Bedrock** | 5 agents | Multi-agent AI system with Claude Sonnet 4.5 | $135 (10k msgs) |
| **AWS Lambda** | 3 functions | Action group backends for agents | $0.20 (included in free tier) |
| **Amazon S3** | 1 bucket, 3 objects | OpenAPI schema storage | $0.01 |
| **AWS IAM** | 5 roles, 10 policies | Agent execution permissions | Free |
| **Amazon CloudWatch Logs** | Log groups for Lambdas | Lambda execution logs | $0.50 |
| **Terraform State** | Not stored in AWS | Local state files | $0 |
| **Total Phase 1** | - | - | **~$136/month** |

### Detailed Service Breakdown

#### 0. Current Data Storage Approach

**⚠️ IMPORTANT**: Currently using **in-memory mock data** - NO database!

**Data Sources**:
- Lambda functions use Python dictionaries in `mock_data.py`
- Mock data hardcoded in Lambda function code
- No persistent storage (data resets on Lambda cold start)
- Mock data includes:
  - 3 mock projects (Flooring, Windows, Deck Repair)
  - Mock available dates (next 30 days)
  - Mock time slots (8 AM - 5 PM)
  - Mock appointment confirmations

**Why Mock Data?**:
- ✅ Quick prototyping and testing
- ✅ No external API dependencies during development
- ✅ Predictable test data
- ❌ Not suitable for production
- ❌ Data not persistent
- ❌ Cannot handle real customer data

**Migration Path**: Phase 2 will introduce DynamoDB for persistent storage.

#### 1. AWS Bedrock (Agents)

**Resources Created**:
- 1 Supervisor Agent (WF1S95L7X1)
- 4 Specialist Agents:
  - Scheduling Agent (TIGRBGSXCS)
  - Information Agent (JEK4SDJOOU)
  - Notes Agent (CF0IPHCFFY)
  - Chitchat Agent (GXVZEOBQ64)

**Foundation Model**:
- `us.anthropic.claude-sonnet-4-5-20250929-v1:0`
- Cross-region inference: us-east-1, us-east-2, us-west-2

**Features Used**:
- ✅ Multi-agent collaboration (SUPERVISOR_ROUTER)
- ✅ Action groups (Lambda-backed)
- ✅ Session attributes
- ✅ Conversation relay (TO_COLLABORATOR)
- ✅ Agent aliases (v1)

**Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `bedrock:InvokeModel` | Foundation models | Invoke Claude Sonnet 4.5 |
| `bedrock:InvokeModelWithResponseStream` | Foundation models | Streaming responses |
| `bedrock:GetAgentAlias` | Agent aliases | Retrieve alias information |
| `bedrock:InvokeAgent` | Collaborator agents | Supervisor delegates to specialists |
| `bedrock:CreateAgent` | - | Terraform creates agents |
| `bedrock:UpdateAgent` | - | Update agent configurations |
| `bedrock:PrepareAgent` | - | Create DRAFT versions |
| `bedrock:CreateAgentAlias` | - | Create v1 aliases |
| `bedrock:AssociateAgentCollaborator` | - | Link specialists to supervisor |
| `bedrock:CreateAgentActionGroup` | - | Link Lambda functions |
| `bedrock:ListAgents` | - | Management operations |
| `bedrock:GetAgent` | - | Status checks |

#### 2. AWS Lambda

**Functions Deployed**:

| Function Name | Runtime | Handler | Memory | Timeout | Purpose | Data Source |
|--------------|---------|---------|--------|---------|---------|-------------|
| `pf-scheduling-actions` | Python 3.11 | handler.lambda_handler | 256 MB | 30s | Scheduling operations | **Mock data** (mock_data.py) |
| `pf-information-actions` | Python 3.11 | handler.lambda_handler | 256 MB | 30s | Information retrieval | **Mock data** (mock_data.py) |
| `pf-notes-actions` | Python 3.11 | handler.lambda_handler | 256 MB | 30s | Note management | **Mock data** (mock_data.py) |

**Current Implementation Details**:
- ⚠️ All functions currently use **in-memory mock data**
- Mock data stored in `mock_data.py` within each Lambda function
- `USE_MOCK_API=true` environment variable controls mock mode
- No database connections or external API calls in current version
- Functions return hardcoded responses based on mock data
- **Not production-ready** - mock data resets on cold starts

**Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `lambda:InvokeFunction` | All pf-* functions | Agents invoke Lambda functions |
| `lambda:CreateFunction` | - | Deploy new functions |
| `lambda:UpdateFunctionCode` | - | Update function code |
| `lambda:UpdateFunctionConfiguration` | - | Update function settings |
| `lambda:GetFunction` | - | Retrieve function details |
| `lambda:ListFunctions` | - | List all functions |

**Lambda Execution Role Permissions** (Not listed in agent IAM):
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents
- VPC (if needed): CreateNetworkInterface, DeleteNetworkInterface, DescribeNetworkInterfaces

#### 3. Amazon S3

**Buckets**:

| Bucket Name | Purpose | Versioning | Encryption | Objects |
|-------------|---------|------------|------------|---------|
| `pf-schemas-dev-618048437522` | OpenAPI schema storage | ✅ Enabled | ✅ SSE-S3 | 3 schemas |

**Objects Stored**:
1. `scheduling_actions.json` - Scheduling agent OpenAPI schema
2. `information_actions.json` - Information agent OpenAPI schema
3. `notes_actions.json` - Notes agent OpenAPI schema

**Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `s3:CreateBucket` | Schema bucket | Terraform creates bucket |
| `s3:PutObject` | Schema objects | Upload OpenAPI schemas |
| `s3:GetObject` | Schema objects | Agents read schemas during preparation |
| `s3:PutBucketVersioning` | Schema bucket | Enable versioning |
| `s3:GetBucketVersioning` | Schema bucket | Check versioning status |
| `s3:ListBucket` | Schema bucket | List objects |
| `s3:DeleteObject` | Schema objects | Cleanup old schemas |

#### 4. AWS IAM

**Roles Created**:

| Role Name | Type | Used By | Policies Attached |
|-----------|------|---------|-------------------|
| `pf-supervisor-agent-role-dev` | Service Role | Supervisor Agent | Inline: bedrock, invoke agents |
| `pf-scheduling-agent-role-dev` | Service Role | Scheduling Agent | Inline: bedrock, s3, lambda |
| `pf-information-agent-role-dev` | Service Role | Information Agent | Inline: bedrock, s3, lambda |
| `pf-notes-agent-role-dev` | Service Role | Notes Agent | Inline: bedrock, s3, lambda |
| `pf-chitchat-agent-role-dev` | Service Role | Chitchat Agent | Inline: bedrock |

**Trust Policies**:
- Principal: `bedrock.amazonaws.com`
- Conditions:
  - `aws:SourceAccount`: 618048437522
  - `aws:SourceArn`: Agent ARNs

**Inline Policies**:
- Supervisor: `pf-supervisor-agent-policy`
- Collaborators: `pf-{agent}-agent-policy` (4 policies)

**Permissions Required** (for Terraform to manage IAM):

| Permission | Resource | Purpose |
|------------|----------|---------|
| `iam:CreateRole` | Agent roles | Create service roles |
| `iam:DeleteRole` | Agent roles | Cleanup |
| `iam:GetRole` | Agent roles | Check role status |
| `iam:PassRole` | Agent roles | Bedrock assumes roles |
| `iam:PutRolePolicy` | Agent roles | Attach inline policies |
| `iam:DeleteRolePolicy` | Agent roles | Remove policies |
| `iam:ListRoles` | - | List all roles |
| `iam:ListRolePolicies` | Agent roles | List attached policies |

#### 5. Amazon CloudWatch Logs

**Log Groups** (Auto-created by Lambda):

| Log Group | Retention | Size | Purpose |
|-----------|-----------|------|---------|
| `/aws/lambda/pf-scheduling-actions` | Indefinite | ~10 MB | Scheduling Lambda logs |
| `/aws/lambda/pf-information-actions` | Indefinite | ~5 MB | Information Lambda logs |
| `/aws/lambda/pf-notes-actions` | Indefinite | ~3 MB | Notes Lambda logs |

**Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `logs:CreateLogGroup` | Log groups | Lambda creates log groups |
| `logs:CreateLogStream` | Log streams | Lambda creates streams |
| `logs:PutLogEvents` | Log streams | Lambda writes logs |
| `logs:DescribeLogGroups` | - | List log groups |
| `logs:DescribeLogStreams` | Log streams | List streams |
| `logs:GetLogEvents` | Log streams | Read logs |
| `logs:FilterLogEvents` | Log streams | Search logs |

---

## Phase 1.5: Real API Integration (Immediate Next Step)

**Status**: 🟡 Ready to Implement
**Estimated Duration**: 1-2 weeks
**Prerequisites**: PF360 API access credentials

### Overview

**Goal**: Replace mock data with real PF360 API calls while maintaining current AWS infrastructure.

**Changes Required**:
- ✅ No new AWS services needed
- ✅ Lambda code changes only
- ✅ Environment variable updates
- ✅ Credentials stored in environment variables (temporary) or Secrets Manager

### Implementation Steps

| Step | Action | Estimated Time |
|------|--------|----------------|
| 1 | Store PF360 API credentials | 15 min |
| 2 | Update Lambda environment variables (`USE_MOCK_API=false`) | 10 min |
| 3 | Test with real PF360 API | 2-4 hours |
| 4 | Update error handling for real API failures | 2-4 hours |
| 5 | Monitor CloudWatch logs for errors | Ongoing |

### Configuration Changes

**Lambda Environment Variables**:

| Variable | Current Value | New Value | Purpose |
|----------|--------------|-----------|---------|
| `USE_MOCK_API` | `true` | `false` | Enable real API calls |
| `PF360_API_BASE_URL` | Not set | `https://api.pf360.com` | API endpoint |
| `PF360_CLIENT_ID` | Not set | `09PF05VD` | Client identifier |
| `PF360_USERNAME` | Not set | (from credentials) | API username |
| `PF360_PASSWORD` | Not set | (from credentials) | API password |

### Cost Impact

**Additional Costs**: $0/month (using existing Lambda, no new services)

**Considerations**:
- Lambda execution time may increase (real API calls slower than mock data)
- Potential increase in Lambda duration charges (~$0.10-0.50/month)
- External PF360 API may have usage fees (check with PF360)

### Recommended: Add Secrets Manager (Optional for Phase 1.5)

If you want secure credential storage:

| Service | Purpose | Monthly Cost |
|---------|---------|--------------|
| **AWS Secrets Manager** | Store PF360 credentials securely | $0.40/secret = $0.40/month |

**Without Secrets Manager**: Use Lambda environment variables (encrypted at rest by default)
**With Secrets Manager**: More secure, supports automatic rotation

---

## Phase 2: Scaling & Observability (Next 3-6 Months)

**Status**: 🔵 Planned
**Estimated Start**: Q1 2026

### New Services Required

| Service | Purpose | Estimated Monthly Cost |
|---------|---------|----------------------|
| **Amazon DynamoDB** | Customer conversation history, session state persistence | $5-10 |
| **Amazon API Gateway** | REST API for frontend, rate limiting, API keys | $3.50 |
| **AWS Secrets Manager** | Store PF360 API credentials, database passwords | $2 |
| **Amazon CloudWatch** (Enhanced) | Custom metrics, dashboards, alarms | $10 |
| **AWS X-Ray** | Distributed tracing for Lambda and agents | $5 |
| **Amazon SNS** | Alerts and notifications | $0.50 |
| **Amazon EventBridge** | Event-driven workflows, scheduled tasks | $0 (free tier) |
| **AWS Systems Manager Parameter Store** | Application configuration | $0 (standard params) |
| **Total Phase 2 Addition** | - | **~$26-31/month** |

### Detailed Phase 2 Requirements

#### 1. Amazon DynamoDB

**Tables to Create**:

| Table Name | Partition Key | Sort Key | Purpose | Read/Write Units |
|------------|--------------|----------|---------|------------------|
| `pf-conversation-history-dev` | `session_id` (S) | `timestamp` (N) | Store conversation turns | 5 RCU / 5 WCU |
| `pf-session-state-dev` | `session_id` (S) | - | Persistent session attributes | 5 RCU / 5 WCU |
| `pf-appointment-cache-dev` | `customer_id` (S) | `project_id` (S) | Cache PF360 API responses | 5 RCU / 5 WCU |
| `pf-agent-metrics-dev` | `agent_id` (S) | `timestamp` (N) | Agent performance metrics | 3 RCU / 3 WCU |

**Features**:
- ✅ Point-in-time recovery (PITR)
- ✅ Auto-scaling (scale to zero for dev)
- ✅ TTL for conversation history (30 days)
- ✅ Global secondary indexes for queries

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `dynamodb:CreateTable` | All tables | Terraform creates tables |
| `dynamodb:DescribeTable` | All tables | Check table status |
| `dynamodb:PutItem` | All tables | Write data |
| `dynamodb:GetItem` | All tables | Read data |
| `dynamodb:Query` | All tables | Query with partition key |
| `dynamodb:Scan` | All tables | Full table scans (admin only) |
| `dynamodb:UpdateItem` | All tables | Update existing items |
| `dynamodb:DeleteItem` | All tables | Delete items |
| `dynamodb:BatchWriteItem` | All tables | Batch writes |
| `dynamodb:UpdateTimeToLive` | All tables | Configure TTL |

#### 2. Amazon API Gateway

**APIs to Create**:

| API Name | Type | Purpose | Endpoints |
|----------|------|---------|-----------|
| `pf-scheduling-api-dev` | REST API | Frontend integration | /chat, /sessions, /health |

**Features**:
- ✅ Lambda proxy integration
- ✅ API keys for authentication
- ✅ Usage plans (rate limiting: 1000 req/min)
- ✅ CORS enabled
- ✅ CloudWatch logging
- ✅ Request/response validation

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `apigateway:POST` | /restapis | Create REST API |
| `apigateway:GET` | /restapis | Describe API |
| `apigateway:PATCH` | /restapis | Update API |
| `apigateway:DELETE` | /restapis | Delete API |
| `apigateway:CreateDeployment` | API stages | Deploy API to stage |
| `apigateway:CreateStage` | API stages | Create dev/prod stages |
| `apigateway:UpdateStage` | API stages | Update stage configuration |
| `lambda:AddPermission` | Lambda functions | Allow API Gateway to invoke Lambda |

#### 3. AWS Secrets Manager

**Secrets to Store**:

| Secret Name | Type | Purpose | Rotation |
|-------------|------|---------|----------|
| `pf/pf360/api-credentials` | Key-Value | PF360 API username/password | 90 days |
| `pf/database/connection` | Key-Value | Future RDS credentials | 30 days |
| `pf/bedrock/api-keys` | Key-Value | Frontend API keys | Manual |

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `secretsmanager:CreateSecret` | All secrets | Create new secrets |
| `secretsmanager:GetSecretValue` | All secrets | Lambda reads secrets |
| `secretsmanager:PutSecretValue` | All secrets | Update secret values |
| `secretsmanager:DescribeSecret` | All secrets | Get metadata |
| `secretsmanager:RotateSecret` | All secrets | Trigger rotation |
| `secretsmanager:DeleteSecret` | All secrets | Remove secrets |

#### 4. Amazon CloudWatch (Enhanced)

**Custom Metrics**:

| Metric Name | Namespace | Purpose | Alarm Threshold |
|-------------|-----------|---------|-----------------|
| `AgentInvocationCount` | `PF/Bedrock` | Track agent usage | >10,000/day |
| `LambdaErrorRate` | `PF/Lambda` | Track Lambda errors | >5% |
| `AgentResponseTime` | `PF/Bedrock` | Monitor latency | >5 seconds |
| `SessionAttributeFailures` | `PF/Bedrock` | Track session issues | >10/hour |

**Dashboards**:
- Agent Performance Dashboard
- Lambda Execution Dashboard
- Cost Optimization Dashboard

**Alarms**:
- High error rate (SNS notification)
- Lambda throttling (SNS notification)
- DynamoDB capacity warnings

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `cloudwatch:PutMetricData` | Custom metrics | Lambda publishes metrics |
| `cloudwatch:GetMetricData` | All metrics | Read metric data |
| `cloudwatch:PutDashboard` | Dashboards | Create dashboards |
| `cloudwatch:PutMetricAlarm` | Alarms | Create alarms |
| `cloudwatch:DescribeAlarms` | Alarms | Check alarm status |

#### 5. AWS X-Ray

**Tracing**:
- Lambda function execution traces
- Bedrock agent invocation traces
- DynamoDB query performance
- External API calls (PF360)

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `xray:PutTraceSegments` | - | Lambda sends traces |
| `xray:PutTelemetryRecords` | - | Send telemetry data |
| `xray:GetSamplingRules` | - | Retrieve sampling config |

#### 6. Amazon SNS

**Topics**:

| Topic Name | Purpose | Subscribers |
|------------|---------|-------------|
| `pf-alerts-dev` | System alerts | Email, Slack webhook |
| `pf-errors-dev` | Error notifications | Email, PagerDuty |

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `sns:CreateTopic` | Topics | Create notification topics |
| `sns:Subscribe` | Topics | Add subscribers |
| `sns:Publish` | Topics | Send notifications |
| `sns:SetTopicAttributes` | Topics | Configure topic |

#### 7. Amazon EventBridge

**Rules**:

| Rule Name | Schedule | Target | Purpose |
|-----------|----------|--------|---------|
| `pf-cleanup-old-sessions` | rate(1 day) | Lambda | Delete old DynamoDB sessions |
| `pf-refresh-cache` | rate(1 hour) | Lambda | Refresh appointment cache |
| `pf-daily-metrics` | cron(0 9 * * ? *) | Lambda | Daily metrics aggregation |

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `events:PutRule` | Rules | Create scheduled rules |
| `events:PutTargets` | Rules | Attach Lambda targets |
| `events:EnableRule` | Rules | Enable rules |
| `lambda:AddPermission` | Lambda | Allow EventBridge to invoke |

---

## Phase 3: Enterprise & Multi-Region (6-12 Months)

**Status**: 🟣 Future Planning
**Estimated Start**: Q3 2026

### New Services Required

| Service | Purpose | Estimated Monthly Cost |
|---------|---------|----------------------|
| **Amazon RDS (Aurora Serverless v2)** | Persistent data storage, analytics | $50-100 |
| **Amazon ElastiCache (Redis)** | Session caching, rate limiting | $20 |
| **AWS WAF** | API protection, DDoS mitigation | $10 |
| **Amazon Route 53** | Multi-region routing, health checks | $1 |
| **AWS CloudFront** | CDN for frontend, caching | $5 |
| **Amazon Cognito** | User authentication, SSO | $0-5 (free tier + usage) |
| **AWS KMS** | Encryption key management | $1 |
| **Amazon SQS** | Message queue for async processing | $0.40 |
| **AWS Step Functions** | Complex workflow orchestration | $5 |
| **Amazon Kinesis Data Streams** | Real-time analytics, event streaming | $15 |
| **AWS Glue** | ETL for data warehouse | $10 |
| **Amazon Athena** | SQL queries on S3 data | $5 |
| **Total Phase 3 Addition** | - | **~$122-172/month** |

### Detailed Phase 3 Requirements

#### 1. Amazon RDS (Aurora Serverless v2)

**Database Cluster**:

| Cluster Name | Engine | Purpose | Capacity Units |
|--------------|--------|---------|----------------|
| `pf-analytics-db-dev` | PostgreSQL 15 | Analytics, reporting, audit logs | 0.5 - 4 ACU |

**Tables** (Sample):
- `customer_interactions` - Full conversation logs
- `appointment_history` - Appointment tracking
- `agent_performance` - Historical metrics
- `user_feedback` - Customer ratings

**Features**:
- ✅ Multi-AZ for high availability
- ✅ Automated backups (7 days)
- ✅ Encryption at rest (KMS)
- ✅ Performance Insights

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `rds:CreateDBCluster` | DB cluster | Create Aurora cluster |
| `rds:CreateDBInstance` | DB instances | Create instances |
| `rds:DescribeDBClusters` | All clusters | Check status |
| `rds:ModifyDBCluster` | DB cluster | Update configuration |
| `rds:DeleteDBCluster` | DB cluster | Cleanup |
| `rds:CreateDBSnapshot` | Snapshots | Manual backups |

#### 2. Amazon ElastiCache (Redis)

**Cluster**:

| Cluster Name | Engine | Node Type | Nodes | Purpose |
|--------------|--------|-----------|-------|---------|
| `pf-session-cache-dev` | Redis 7.0 | cache.t4g.micro | 2 (primary + replica) | Session state, rate limiting |

**Use Cases**:
- Session state caching (faster than DynamoDB)
- Rate limiting (API throttling)
- Temporary data storage
- Pub/sub for real-time updates

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `elasticache:CreateCacheCluster` | Clusters | Create Redis cluster |
| `elasticache:DescribeCacheClusters` | Clusters | Check status |
| `elasticache:ModifyCacheCluster` | Clusters | Update configuration |
| `elasticache:DeleteCacheCluster` | Clusters | Cleanup |

#### 3. AWS WAF

**Web ACL**:

| ACL Name | Protected Resource | Rules |
|----------|-------------------|-------|
| `pf-api-protection` | API Gateway | Rate limiting, geo-blocking, SQL injection, XSS |

**Rules**:
- Rate limit: 100 requests per 5 minutes per IP
- Geo-blocking: Allow US only
- AWS Managed Rules: Core rule set, Known bad inputs

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `wafv2:CreateWebACL` | Web ACLs | Create WAF rules |
| `wafv2:AssociateWebACL` | API Gateway | Attach WAF to API |
| `wafv2:UpdateWebACL` | Web ACLs | Update rules |
| `wafv2:GetWebACL` | Web ACLs | Check status |

#### 4. Amazon Route 53

**Hosted Zone**:

| Domain | Record Type | Routing Policy | Purpose |
|--------|------------|----------------|---------|
| `api.scheduling-agent.com` | A | Latency-based | Multi-region API routing |
| `health.scheduling-agent.com` | A | Failover | Health check endpoint |

**Health Checks**:
- API Gateway health endpoint
- Multi-region failover

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `route53:CreateHostedZone` | Hosted zones | Create DNS zone |
| `route53:ChangeResourceRecordSets` | Record sets | Update DNS records |
| `route53:GetHealthCheck` | Health checks | Monitor endpoints |
| `route53:CreateHealthCheck` | Health checks | Create checks |

#### 5. AWS CloudFront

**Distribution**:

| Distribution | Origin | Purpose | Cache Behavior |
|--------------|--------|---------|----------------|
| `pf-frontend-cdn` | S3 (frontend assets) | Frontend hosting, global CDN | Cache static assets |
| `pf-api-cdn` | API Gateway | API caching, reduced latency | Cache GET requests |

**Features**:
- ✅ HTTPS only (ACM certificate)
- ✅ Origin Shield (reduce origin load)
- ✅ Custom error pages
- ✅ Geo-restriction (optional)

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `cloudfront:CreateDistribution` | Distributions | Create CDN |
| `cloudfront:UpdateDistribution` | Distributions | Update config |
| `cloudfront:GetDistribution` | Distributions | Check status |
| `cloudfront:CreateInvalidation` | Distributions | Clear cache |

#### 6. Amazon Cognito

**User Pool**:

| Pool Name | Purpose | MFA | Social Identity Providers |
|-----------|---------|-----|--------------------------|
| `pf-users-dev` | Customer authentication | Optional (SMS) | Google, Facebook (future) |

**Features**:
- ✅ Email verification
- ✅ Password policies
- ✅ Custom attributes (customer_id, client_id)
- ✅ Lambda triggers (pre-signup, post-confirmation)

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `cognito-idp:CreateUserPool` | User pools | Create authentication |
| `cognito-idp:CreateUserPoolClient` | App clients | Create app integrations |
| `cognito-idp:AdminCreateUser` | Users | Create users |
| `cognito-idp:AdminSetUserPassword` | Users | Reset passwords |

#### 7. AWS KMS

**Keys**:

| Key Alias | Purpose | Key Type |
|-----------|---------|----------|
| `alias/pf-rds-encryption` | RDS encryption | Symmetric |
| `alias/pf-s3-encryption` | S3 encryption | Symmetric |
| `alias/pf-secrets-encryption` | Secrets Manager | Symmetric |

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `kms:CreateKey` | Keys | Create encryption keys |
| `kms:CreateAlias` | Aliases | Create key aliases |
| `kms:Encrypt` | Keys | Encrypt data |
| `kms:Decrypt` | Keys | Decrypt data |
| `kms:DescribeKey` | Keys | Get key info |

#### 8. Amazon SQS

**Queues**:

| Queue Name | Type | Purpose | DLQ |
|------------|------|---------|-----|
| `pf-async-tasks-dev` | Standard | Async processing (reports, emails) | ✅ Yes |
| `pf-appointment-notifications-dev` | Standard | Send appointment reminders | ✅ Yes |
| `pf-dlq-dev` | Standard | Dead letter queue | - |

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `sqs:CreateQueue` | Queues | Create queues |
| `sqs:SendMessage` | Queues | Send messages |
| `sqs:ReceiveMessage` | Queues | Lambda polls messages |
| `sqs:DeleteMessage` | Queues | Remove processed messages |
| `sqs:GetQueueAttributes` | Queues | Check queue status |

#### 9. AWS Step Functions

**State Machines**:

| State Machine Name | Purpose | Steps | Timeout |
|-------------------|---------|-------|---------|
| `pf-appointment-workflow` | Multi-step appointment booking | 5 steps | 5 minutes |
| `pf-customer-onboarding` | New customer setup | 7 steps | 10 minutes |

**Integration**:
- Lambda function invocations
- DynamoDB updates
- SNS notifications
- Wait states

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `states:CreateStateMachine` | State machines | Create workflows |
| `states:StartExecution` | Executions | Start workflow |
| `states:DescribeExecution` | Executions | Check status |
| `lambda:InvokeFunction` | Lambda | Step Functions invokes Lambda |

#### 10. Amazon Kinesis Data Streams

**Streams**:

| Stream Name | Shards | Purpose | Retention |
|-------------|--------|---------|-----------|
| `pf-events-stream-dev` | 2 | Real-time event streaming | 24 hours |
| `pf-metrics-stream-dev` | 1 | Real-time metrics | 7 days |

**Consumers**:
- Lambda (real-time processing)
- Kinesis Data Firehose → S3 (archival)
- Kinesis Data Analytics (real-time analytics)

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `kinesis:CreateStream` | Streams | Create stream |
| `kinesis:PutRecord` | Streams | Write events |
| `kinesis:PutRecords` | Streams | Batch writes |
| `kinesis:GetRecords` | Streams | Read events |
| `kinesis:DescribeStream` | Streams | Check status |

#### 11. AWS Glue

**ETL Jobs**:

| Job Name | Source | Target | Schedule |
|----------|--------|--------|----------|
| `pf-conversations-to-s3` | DynamoDB | S3 Parquet | Daily |
| `pf-metrics-aggregation` | CloudWatch Logs | S3 Parquet | Hourly |

**Data Catalog**:
- Crawlers for S3 data
- Tables for Athena queries

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `glue:CreateJob` | Jobs | Create ETL jobs |
| `glue:StartJobRun` | Jobs | Run jobs |
| `glue:CreateCrawler` | Crawlers | Catalog S3 data |
| `glue:StartCrawler` | Crawlers | Run crawlers |

#### 12. Amazon Athena

**Workgroup**:

| Workgroup Name | Output Location | Purpose |
|----------------|----------------|---------|
| `pf-analytics-dev` | s3://pf-query-results-dev/ | Ad-hoc SQL queries on conversation data |

**Sample Queries**:
- Customer engagement metrics
- Agent performance analysis
- Appointment booking trends

**New Permissions Required**:

| Permission | Resource | Purpose |
|------------|----------|---------|
| `athena:StartQueryExecution` | Workgroups | Run queries |
| `athena:GetQueryExecution` | Queries | Check status |
| `athena:GetQueryResults` | Queries | Retrieve results |
| `s3:PutObject` | Query results bucket | Store results |

---

## Cost Estimates

### Summary by Phase

| Phase | Services Count | Monthly Cost (Low) | Monthly Cost (High) | Annual Cost (High) | Data Source |
|-------|---------------|-------------------|--------------------|--------------------|-------------|
| **Phase 1 (Current)** | 5 services | $136 | $136 | $1,632 | Mock data (Python dicts) |
| **Phase 1.5 (Real API)** | 5 services (+0 new) | $136 | $137 | $1,644 | PF360 API (real-time) |
| **Phase 2 (Scaling)** | +8 services | $162 | $167 | $2,004 | PF360 API + DynamoDB cache |
| **Phase 3 (Enterprise)** | +12 services | $284 | $339 | $4,068 | Multi-tier (API + DB + Analytics) |

### Detailed Cost Breakdown

#### Phase 1: Current Production

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| Bedrock (Claude 4.5) | 10,000 messages | $0.003/1K input tokens, $0.015/1K output | $135 |
| Lambda | 10,000 invocations, 256MB, 5s avg | $0.20/million requests + $0.0000166667/GB-sec | $0.20 |
| S3 | 1 GB storage, 1,000 requests | $0.023/GB + $0.0004/1K PUT | $0.01 |
| CloudWatch Logs | 1 GB ingestion, 1 GB storage | $0.50/GB ingestion | $0.50 |
| **Total** | - | - | **$135.71** |

#### Phase 2: Scaling & Observability

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| DynamoDB | 4 tables, 5 RCU/WCU each, 1 GB storage | $0.25/GB + $0.00013/RCU-hour | $5 |
| API Gateway | 100,000 requests | $3.50/million requests | $0.35 |
| Secrets Manager | 3 secrets | $0.40/secret/month | $1.20 |
| CloudWatch (metrics) | 10 custom metrics, 3 dashboards, 5 alarms | $0.30/metric, $3/dashboard, $0.10/alarm | $12.50 |
| X-Ray | 100,000 traces | $5/million traces | $0.50 |
| SNS | 1,000 notifications | $0.50/million | $0.001 |
| EventBridge | 10,000 events | Free tier | $0 |
| **Total** | - | - | **$19.55** |

#### Phase 3: Enterprise & Multi-Region

| Service | Usage | Unit Cost | Monthly Cost |
|---------|-------|-----------|--------------|
| Aurora Serverless v2 | 2 ACU avg, 10 GB storage | $0.12/ACU-hour, $0.10/GB | $172.80 + $1 = $173.80 |
| ElastiCache (Redis) | 2x cache.t4g.micro | $0.034/hour | $48.96 |
| WAF | 1 Web ACL, 5 rules | $5/ACL + $1/rule | $10 |
| Route 53 | 1 hosted zone, 2 health checks | $0.50/zone, $0.50/health check | $1.50 |
| CloudFront | 100 GB data transfer, 1M requests | $0.085/GB + $0.0075/10K | $9.25 |
| Cognito | 5,000 MAUs | Free tier (first 50K) | $0 |
| KMS | 3 keys, 10,000 requests | $1/key, $0.03/10K | $3.03 |
| SQS | 1M requests | $0.40/million | $0.40 |
| Step Functions | 10,000 state transitions | $0.025/1K transitions | $0.25 |
| Kinesis | 2 shards, 1M PUT records | $0.015/shard-hour + $0.014/1M | $21.60 + $0.014 = $21.61 |
| Glue | 10 DPU-hours | $0.44/DPU-hour | $4.40 |
| Athena | 100 GB scanned | $5/TB | $0.50 |
| **Total** | - | - | **$273.70** |

### Cost Optimization Strategies

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| **Reserved Capacity** | 30-50% | Purchase 1-year RDS/ElastiCache reserved instances |
| **Auto-scaling** | 20-40% | Scale down DynamoDB/Aurora during off-peak hours |
| **S3 Lifecycle Policies** | 50-70% | Move old logs to Glacier after 90 days |
| **Lambda Memory Optimization** | 10-20% | Right-size Lambda memory based on profiling |
| **CloudFront Caching** | 30-50% | Increase cache TTL for API responses |
| **Data Transfer Optimization** | 20-30% | Use VPC endpoints, avoid cross-region transfers |

---

## IAM Permissions Summary

### Permissions by Service Category

#### Compute & AI

| Service | Read Permissions | Write Permissions | Admin Permissions |
|---------|-----------------|-------------------|-------------------|
| **Bedrock** | GetAgent, GetAgentAlias, ListAgents | InvokeModel, InvokeAgent, PrepareAgent | CreateAgent, UpdateAgent, DeleteAgent |
| **Lambda** | GetFunction, ListFunctions | InvokeFunction | CreateFunction, UpdateFunctionCode |

#### Storage

| Service | Read Permissions | Write Permissions | Admin Permissions |
|---------|-----------------|-------------------|-------------------|
| **S3** | GetObject, ListBucket | PutObject | CreateBucket, DeleteBucket |
| **DynamoDB** | GetItem, Query, Scan | PutItem, UpdateItem, DeleteItem | CreateTable, DeleteTable |
| **RDS** | DescribeDBClusters | - | CreateDBCluster, ModifyDBCluster |

#### Networking & Security

| Service | Read Permissions | Write Permissions | Admin Permissions |
|---------|-----------------|-------------------|-------------------|
| **IAM** | GetRole, ListRoles | PassRole, PutRolePolicy | CreateRole, DeleteRole |
| **Secrets Manager** | GetSecretValue, DescribeSecret | PutSecretValue | CreateSecret, DeleteSecret |
| **KMS** | DescribeKey | Encrypt, Decrypt | CreateKey, CreateAlias |
| **API Gateway** | GetRestApis | - | POST /restapis, CreateDeployment |

#### Monitoring & Logging

| Service | Read Permissions | Write Permissions | Admin Permissions |
|---------|-----------------|-------------------|-------------------|
| **CloudWatch Logs** | GetLogEvents, DescribeLogGroups | PutLogEvents | CreateLogGroup |
| **CloudWatch Metrics** | GetMetricData | PutMetricData | PutMetricAlarm, PutDashboard |
| **X-Ray** | GetTraceSummaries | PutTraceSegments | - |

#### Messaging & Events

| Service | Read Permissions | Write Permissions | Admin Permissions |
|---------|-----------------|-------------------|-------------------|
| **SNS** | GetTopicAttributes | Publish | CreateTopic, Subscribe |
| **SQS** | ReceiveMessage, GetQueueAttributes | SendMessage, DeleteMessage | CreateQueue, DeleteQueue |
| **EventBridge** | DescribeRule | PutTargets | PutRule, EnableRule |

---

## Next Steps

### Phase 1 (Current) - Maintenance

✅ **Completed**: All services deployed and operational with mock data
- ✅ 5 AWS services deployed
- ✅ 5 Bedrock agents configured
- ✅ 3 Lambda functions with mock data
- ⚠️ **Currently using mock data - NOT production-ready**

**Ongoing Tasks**:
- Monthly review of CloudWatch Logs
- Optimize Lambda memory configurations
- Monitor Bedrock agent costs

### Phase 1.5 (Immediate Priority) - Real API Integration

**Timeline**: Next 1-2 weeks
**Status**: 🟡 Ready to implement

**Prerequisites**:
1. Obtain PF360 API credentials
2. Test PF360 API endpoints manually
3. Verify API rate limits and quotas

**Implementation Steps**:
1. **Week 1**: Configure Lambda environment variables with PF360 credentials
2. **Week 1**: Update `USE_MOCK_API=false` in Lambda configuration
3. **Week 1**: Test with real API, monitor CloudWatch logs
4. **Week 2**: Update error handling for API failures
5. **Week 2**: Load testing with real API

**Deliverables**:
- ✅ Lambda functions calling real PF360 API
- ✅ Error handling for API failures
- ✅ CloudWatch alarms for API errors
- ✅ Documentation of API integration

### Phase 2 (Next 3-6 Months) - Scaling & Observability

**Timeline**: Q1-Q2 2026
**Prerequisites**: Phase 1.5 completed (real API working)

**Priorities**:
1. **Q1 2026**: Implement DynamoDB for conversation history and caching
2. **Q1 2026**: Add Secrets Manager for credential management
3. **Q2 2026**: Add API Gateway with rate limiting and authentication
4. **Q2 2026**: Set up CloudWatch dashboards, custom metrics, and alarms
5. **Q2 2026**: Implement X-Ray for distributed tracing

### Phase 3 (6-12 Months) - Enterprise & Multi-Region

**Timeline**: Q3-Q4 2026
**Prerequisites**: Phase 2 completed (DynamoDB, observability in place)

**Roadmap**:
1. **Q3 2026**: Deploy Aurora Serverless for analytics and reporting
2. **Q3 2026**: Set up ElastiCache (Redis) for session caching
3. **Q3 2026**: Implement AWS WAF for API protection
4. **Q4 2026**: Implement multi-region with Route 53 and CloudFront
5. **Q4 2026**: Add Cognito for user authentication and SSO

---

## Appendix: IAM Policy Examples

### Example: Bedrock Agent Execution Role (Phase 1)

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
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-5-20250929-v1:0",
        "arn:aws:bedrock:*:618048437522:inference-profile/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::pf-schemas-dev-618048437522/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:618048437522:function:pf-*-actions"
      ]
    }
  ]
}
```

### Example: Lambda Execution Role (All Phases)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:618048437522:log-group:/aws/lambda/pf-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:618048437522:table/pf-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:618048437522:secret:pf/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

---

**Document Version**: 1.0
**Last Updated**: October 22, 2025
**Maintained By**: Infrastructure Team
**Review Frequency**: Quarterly

**Note**: Estimated costs are based on current AWS pricing as of October 2025 and low-to-moderate usage patterns. Actual costs may vary based on usage, region, and pricing changes.
