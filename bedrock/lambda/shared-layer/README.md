# Shared Lambda Layer for Bedrock Agents

This Lambda layer provides common utilities for all Bedrock Agent Lambda functions.

## Contents

### `python/lib/api_client.py`
- `PF360APIClient`: API client for PF360 Customer Scheduler API
- Features:
  - Automatic retry with exponential backoff
  - Mock mode support (USE_MOCK_API flag)
  - Session management for request_id tracking
  - Error handling and logging
  - Timeout configuration

### `python/lib/session_manager.py`
- `SessionManager`: DynamoDB session storage manager
- Features:
  - CRUD operations for sessions
  - TTL support (30-minute expiration)
  - Request ID tracking
  - Customer session queries

### `python/lib/error_handler.py`
- Error handling utilities:
  - `handle_errors`: Decorator for Lambda handlers
  - `format_error_response`: Format error responses
  - `format_success_response`: Format success responses
  - `format_bedrock_response`: Format Bedrock Agent responses
  - `classify_error`: Classify exceptions
  - `log_request`, `log_response`: Logging helpers

### `python/lib/validators.py`
- Input validation utilities:
  - `validate_customer_id`, `validate_project_id`, etc.
  - `validate_date`, `validate_time`: Date/time validation
  - `validate_bedrock_event`: Bedrock event structure validation
  - `extract_bedrock_parameters`: Extract parameters from event
  - Action-specific validators

## Building the Layer

```bash
cd lambda/shared-layer
./build.sh
```

This will:
1. Install dependencies from requirements.txt
2. Copy library code
3. Create `shared-layer.zip`

## Deploying the Layer

```bash
aws lambda publish-layer-version \
  --layer-name bedrock-agent-shared \
  --description 'Shared utilities for Bedrock Agents' \
  --zip-file fileb://shared-layer.zip \
  --compatible-runtimes python3.11 python3.12 \
  --region us-east-1
```

Save the Layer ARN from the output.

## Using the Layer in Lambda Functions

1. **Add layer to Lambda function:**
   ```bash
   aws lambda update-function-configuration \
     --function-name scheduling-actions \
     --layers arn:aws:lambda:us-east-1:123456789012:layer:bedrock-agent-shared:1
   ```

2. **Import in Lambda handler:**
   ```python
   from lib.api_client import PF360APIClient
   from lib.session_manager import SessionManager
   from lib.error_handler import handle_errors, format_bedrock_response
   from lib.validators import extract_bedrock_parameters, validate_customer_id
   ```

## Environment Variables

Lambda functions using this layer should set:

- `USE_MOCK_API` - "true" for mock mode, "false" for real API (default: "true")
- `API_ENVIRONMENT` - "dev", "staging", or "prod" (default: "dev")
- `API_TIMEOUT` - API request timeout in seconds (default: "30")
- `ENABLE_REAL_CONFIRM` - "true" to enable real confirm API (default: "false")
- `ENABLE_REAL_CANCEL` - "true" to enable real cancel API (default: "false")
- `DYNAMODB_TABLE_NAME` - DynamoDB table name (default: "scheduling-agent-sessions-dev")

## Testing Locally

```python
# Mock mode (no AWS credentials needed)
import os
os.environ["USE_MOCK_API"] = "true"

from lib.api_client import PF360APIClient

session_data = {
    "customer_id": "CUST001",
    "client_id": "CLIENT123",
    "client_name": "testclient"
}

client = PF360APIClient(session_data)
projects = client.get_projects()
print(projects)
```

## Dependencies

- `requests>=2.31.0` - HTTP requests with retry
- `boto3>=1.28.0` - AWS SDK
- `pytz>=2024.1` - Timezone handling

## Size Optimization

Current layer size: ~5-10 MB

To reduce size:
- Dependencies are already minimal
- boto3 is included in Lambda runtime (but specified for local testing)
- No heavy ML libraries

## Updates

To update the layer:
1. Modify code in `python/lib/`
2. Run `./build.sh`
3. Publish new layer version
4. Update Lambda functions to use new version
