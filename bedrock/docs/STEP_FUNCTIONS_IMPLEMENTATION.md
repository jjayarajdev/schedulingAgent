# AWS Step Functions Implementation

## Overview

This document describes the AWS Step Functions implementation for orchestrating complex multi-agent workflows in the scheduling system.

## Architecture

### Dual-Path Query Routing

```
User Query
    ↓
Query Router Lambda (pf-query-router)
    ↓
    ├─→ SIMPLE Query → Direct Bedrock Agent Invocation
    │   (single agent, no orchestration needed)
    │
    └─→ COMPLEX Query → AWS Step Functions
        (multi-step, conditional logic, orchestration)
```

### Components Deployed

#### 1. Query Router Lambda (`pf-query-router`)
**Purpose**: Classify incoming queries as SIMPLE or COMPLEX

**Location**: `lambda/query-router/handler.py`

**Function**: Uses Claude 3.5 Sonnet V2 to analyze query complexity
- **SIMPLE**: Single agent action, no conditional logic
  - Examples: "Show me my projects", "What are your hours?"
- **COMPLEX**: Multi-step workflow, conditional logic, orchestration
  - Examples: "Schedule my most urgent project", "If weather is good, schedule outdoor project"

**Test Results**: 100% accuracy on 10 test queries (5 simple, 5 complex)

**ARN**: `arn:aws:lambda:us-east-1:618048437522:function:pf-query-router`

#### 2. Filter Projects Lambda (`pf-filter-projects`)
**Purpose**: Filter and prioritize project lists based on criteria

**Location**: `lambda/filter-projects/handler.py`

**Capabilities**:
- Find most urgent project (by status/priority)
- Filter by priority level (HIGH, MEDIUM, LOW)
- Filter by status (Scheduled, Pending, etc.)
- Filter by type (outdoor, indoor, installation, etc.)

**Priority Logic**:
1. Status = "Urgent" (highest priority)
2. Priority = "HIGH"
3. Status = "Scheduled" (has date, needs attention)
4. First project in list (fallback)

**ARN**: `arn:aws:lambda:us-east-1:618048437522:function:pf-filter-projects`

#### 3. State Machine: Schedule Urgent Project
**Purpose**: Orchestrate workflow to find and schedule urgent projects

**Location**: `infrastructure/step-functions/state-machines/schedule-urgent-project.json`

**ARN**: `arn:aws:states:us-east-1:618048437522:stateMachine:pf-schedule-urgent-project`

**Workflow**:
```
GetAllProjects (Lambda: pf-information-actions)
    ↓
ParseProjectsResponse (Extract projects array)
    ↓
ParseProjectsJSON (Parse JSON string)
    ↓
FilterUrgentProject (Lambda: pf-filter-projects)
    ↓
ParseFilterResult (Parse filter response)
    ↓
CheckIfUrgentFound (Choice State)
    ├─→ Found = true → PrepareSchedulingRequest → FormatSuccessResponse
    └─→ Found = false → NoUrgentProjects
```

**Error Handling**:
- Retry policy: 2 attempts with exponential backoff (2x)
- Catch block: Routes to HandleGetProjectsError state
- Timeout: 30 seconds per Lambda invocation

#### 4. IAM Role
**Name**: `pf-step-functions-role`

**ARN**: `arn:aws:iam::618048437522:role/pf-step-functions-role`

**Permissions**:
- `lambda:InvokeFunction` (invoke Lambda functions)
- `bedrock:InvokeAgent` (future: invoke agents directly)
- `logs:*` (CloudWatch Logs)

## Deployment

### Automated Deployment Script
**Location**: `scripts/deploy_step_functions.sh`

**What it deploys**:
1. Query Router Lambda
2. Filter Projects Lambda
3. IAM Role for Step Functions
4. State Machine definition
5. Environment variables

**Usage**:
```bash
cd /path/to/schedulingAgent-bb/bedrock
chmod +x scripts/deploy_step_functions.sh
./scripts/deploy_step_functions.sh
```

**Output**:
- All resources created/updated
- ARNs for all deployed resources
- Verification of successful deployment

### Manual Update (State Machine Only)
```bash
REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
STATE_MACHINE_NAME="pf-schedule-urgent-project"
STATE_MACHINE_FILE="infrastructure/step-functions/state-machines/schedule-urgent-project.json"

aws stepfunctions update-state-machine \
  --state-machine-arn "arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:${STATE_MACHINE_NAME}" \
  --definition file://$STATE_MACHINE_FILE \
  --region $REGION
```

## Testing

### Test Script
**Location**: `tests/test_step_functions.py`

**Usage**:
```bash
python3 tests/test_step_functions.py
```

**Test Cases**:
1. "Schedule my most urgent project for the earliest time"
2. "Show me my urgent projects"

**Test Results** (as of 2025-10-27):
```
✅ Test 1: SUCCEEDED
   Found project: PRJ-78945 (Flooring)
   Status: Scheduled
   Address: 123 Main St, Tampa, FL 33601

✅ Test 2: SUCCEEDED
   Found project: PRJ-78945 (Flooring)
   Correctly identified urgent project
```

### Query Router Classification Test
**Location**: `lambda/query-router/test_router.py`

**Usage**:
```bash
cd lambda/query-router
python3 test_router.py
```

**Results**: 10/10 queries classified correctly

## AWS Console Access

### View Executions
https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines

### View Lambda Functions
- Query Router: https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/pf-query-router
- Filter Projects: https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/pf-filter-projects

### View CloudWatch Logs
```bash
# Query Router logs
aws logs tail /aws/lambda/pf-query-router --follow

# Filter Projects logs
aws logs tail /aws/lambda/pf-filter-projects --follow

# State Machine logs
aws logs tail /aws/states/pf-schedule-urgent-project --follow
```

## Data Flow Example

### Input to State Machine:
```json
{
  "query": "Schedule my most urgent project for the earliest time",
  "customer_id": "CUST001",
  "client_id": "CLIENT001",
  "sessionId": "test-session-CUST001"
}
```

### State Machine Output:
```json
{
  "success": true,
  "message": "Found urgent project: PRJ-78945 (Flooring). Ready to schedule for earliest available time.",
  "project": {
    "id": "PRJ-78945",
    "category": "Flooring",
    "status": "Scheduled",
    "address": "123 Main St, Tampa, FL 33601"
  },
  "nextStep": "Please confirm to proceed with scheduling, or I can show you available times first."
}
```

## Integration with Flask Backend

### Current Status
- ⏸️ **Not Yet Integrated** - Flask backend still uses direct Bedrock invocation
- Backend code: `backend/app.py`

### Integration Plan
1. Update Flask `/invoke-agent` endpoint to call Query Router first
2. Route SIMPLE queries to existing Bedrock Agent flow
3. Route COMPLEX queries to Step Functions
4. Parse Step Functions response and format for frontend
5. Handle session management across both paths

### Pseudo-code
```python
@app.route('/invoke-agent', methods=['POST'])
def invoke_agent():
    query = request.json.get('prompt')
    customer_id = SAMPLE_USER['customer_id']

    # Step 1: Classify query
    router_response = lambda_client.invoke(
        FunctionName='pf-query-router',
        Payload=json.dumps({'query': query})
    )

    complexity = router_response['complexity']

    if complexity == 'SIMPLE':
        # Existing Bedrock Agent flow
        response = bedrock_agent.invoke_agent(...)
    else:
        # Step Functions flow
        state_machine_arn = router_response['state_machine_arn']
        response = sfn_client.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps({
                'query': query,
                'customer_id': customer_id,
                ...
            })
        )

    return format_response(response)
```

## Future State Machines

### Planned Implementations

#### 1. Weather-Based Scheduling
**Name**: `pf-schedule-weather-dependent`

**Use Case**: "If weather is good next week, schedule my outdoor project"

**Workflow**:
- Get all outdoor projects
- Get weather forecast
- Check weather conditions
- Schedule if conditions are favorable
- Notify user with recommendation

#### 2. Batch Scheduling
**Name**: `pf-schedule-batch-projects`

**Use Case**: "Schedule all my pending installation projects"

**Workflow**:
- Get all projects matching criteria
- Get available time slots (Map state for parallel processing)
- Optimize scheduling (minimize travel time)
- Create multiple appointments
- Return batch confirmation

#### 3. Conditional Routing with Fallback
**Name**: `pf-schedule-with-fallback`

**Use Case**: "Schedule project PRJ-123 for Monday, or Tuesday if not available"

**Workflow**:
- Check Monday availability
- If available → Schedule for Monday
- If not → Check Tuesday
- If not → Get all available slots
- Return recommendation

## Cost Considerations

### Step Functions Pricing (as of 2025)
- State transitions: $0.025 per 1,000 transitions
- Estimated: ~10 transitions per execution
- Cost per execution: ~$0.00025
- 1,000 complex queries/month = ~$0.25

### Lambda Pricing
- Query Router: 512MB, ~500ms → $0.000001 per invocation
- Filter Projects: 256MB, ~100ms → $0.0000002 per invocation
- 1,000 complex queries/month = ~$0.0012

**Total estimated cost**: ~$0.25/month for 1,000 complex queries

## Monitoring and Debugging

### CloudWatch Metrics
- Execution duration
- Success/failure rate
- State transition counts
- Lambda invocation counts

### X-Ray Tracing
Enable X-Ray in state machine for end-to-end tracing:
```bash
aws stepfunctions update-state-machine \
  --state-machine-arn $STATE_MACHINE_ARN \
  --tracing-configuration enabled=true
```

### Debug Tips
1. Check Step Functions execution history in console
2. Review Lambda CloudWatch logs
3. Use Step Functions simulator for testing changes
4. Enable detailed logging in state machine definition

## Troubleshooting

### Common Issues

#### 1. Lambda Parameter Extraction Error
**Error**: "Missing required parameter: customer_id"

**Cause**: Incorrect payload format for information-actions Lambda

**Solution**: Use `parameters` array format:
```json
{
  "parameters": [
    {"name": "customer_id", "value": "CUST001"}
  ]
}
```

#### 2. JSONPath Not Found
**Error**: "The JSONPath '$.path' could not be found"

**Cause**: Response structure doesn't match expected path

**Solution**: Add Parse state to extract/transform data:
```json
{
  "Type": "Pass",
  "Parameters": {
    "data.$": "States.StringToJson($.response.body)"
  }
}
```

#### 3. Choice State Invalid Value
**Error**: "The choice state's condition path references an invalid value"

**Cause**: Referenced field doesn't exist or is null

**Solution**: Add validation or use default value:
```json
{
  "Variable": "$.found",
  "BooleanEquals": true,
  "IsPresent": true
}
```

## References

- [AWS Step Functions Developer Guide](https://docs.aws.amazon.com/step-functions/)
- [State Machine Language Spec](https://states-language.net/spec.html)
- [Lambda Integration Patterns](https://docs.aws.amazon.com/step-functions/latest/dg/connect-lambda.html)
- [JSONPath in Step Functions](https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-paths.html)

## Changelog

### 2025-10-27 - Initial Implementation
- Created Query Router Lambda with Claude-based classification
- Created Filter Projects Lambda with intelligent prioritization
- Built schedule-urgent-project state machine
- Deployed all resources to AWS us-east-1
- Successfully tested end-to-end execution
- Achieved 100% test pass rate (2/2 test cases)
