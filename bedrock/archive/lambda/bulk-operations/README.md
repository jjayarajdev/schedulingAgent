# Bulk Operations Lambda Function

Handles bulk scheduling operations for coordinators:
- **Route optimization** - Optimize routes for 2-50 projects
- **Bulk team assignments** - Assign up to 100 projects with conflict detection
- **Project validation** - Validate permits, measurements, access for up to 100 projects
- **Conflict detection** - Detect scheduling conflicts across projects and teams

## Features

### 1. Route Optimization

Optimizes travel routes for field technicians using TSP (Traveling Salesman Problem) algorithms.

**Input:**
```json
{
  "operation": "optimize_route",
  "project_ids": ["12345", "12347", "12350", "12352"],
  "date": "2025-10-15",
  "optimize_for": "time"
}
```

**Output:**
```json
{
  "operation": "route_optimize",
  "project_count": 4,
  "optimized_route": [
    {
      "sequence": 1,
      "project_id": "12345",
      "address": "123 Main St, Tampa, FL",
      "arrival_time": "2025-10-15T08:00:00",
      "duration_minutes": 120,
      "drive_time_to_next_minutes": 15,
      "coordinates": [27.9506, -82.4572]
    }
  ],
  "metrics": {
    "total_distance_miles": 45.2,
    "total_drive_time_minutes": 180,
    "time_saved_minutes": 77,
    "savings_percentage": 30.0
  }
}
```

### 2. Bulk Team Assignment

Assigns multiple projects to a team with automatic conflict detection.

**Input:**
```json
{
  "operation": "bulk_assign_teams",
  "project_ids": ["15001", "15002", "15003"],
  "team": "Team A",
  "date_range": ["2025-10-15", "2025-10-20"],
  "ignore_conflicts": false
}
```

**Output:**
```json
{
  "operation": "bulk_assign",
  "requested_count": 3,
  "successful": 2,
  "failed": 1,
  "assignments": [
    {
      "project_id": "15001",
      "team": "Team A",
      "scheduled_date": "2025-10-15",
      "estimated_hours": 2,
      "status": "assigned"
    }
  ],
  "conflicts": [
    {
      "project_id": "15003",
      "reason": "Team A on vacation Oct 20",
      "severity": "error",
      "suggested_resolution": "Assign to Team B or reschedule"
    }
  ]
}
```

### 3. Project Validation

Validates projects for scheduling readiness (permits, measurements, access).

**Input:**
```json
{
  "operation": "validate_projects",
  "project_ids": ["10001", "10002", "10003"],
  "validation_checks": ["permit", "measurement", "access", "conflicts"]
}
```

**Output:**
```json
{
  "operation": "validate",
  "total_projects": 3,
  "valid_count": 2,
  "issues_count": 1,
  "projects": [
    {
      "project_id": "10001",
      "is_valid": true,
      "checks": {
        "permit_valid": true,
        "measurements_complete": true,
        "access_approved": true,
        "no_conflicts": true
      },
      "issues": []
    },
    {
      "project_id": "10003",
      "is_valid": false,
      "checks": {
        "permit_valid": false
      },
      "issues": [
        {
          "type": "permit",
          "severity": "blocking",
          "message": "Permit not approved",
          "resolution_steps": ["Contact permitting dept"]
        }
      ]
    }
  ],
  "summary": {
    "ready_to_schedule": ["10001", "10002"],
    "requires_action": [],
    "blocked": ["10003"]
  }
}
```

### 4. Conflict Detection

Detects scheduling conflicts for projects.

**Input:**
```json
{
  "operation": "detect_conflicts",
  "project_ids": ["12345", "12347"],
  "team": "Team A",
  "date_range": ["2025-10-15", "2025-10-20"]
}
```

**Output:**
```json
{
  "conflicts_found": 1,
  "conflicts": [
    {
      "project_id": "12347",
      "reason": "Overlaps with existing appointment",
      "severity": "error",
      "suggested_resolution": "Reschedule to Oct 21"
    }
  ]
}
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name | `dev` |
| `PF360_API_URL` | PF360 API base URL | `https://api.pf360.com` |
| `DYNAMODB_TABLE` | DynamoDB table for tracking | `bulk-operations-tracking-dev` |
| `MAX_PROJECTS` | Max projects per operation | `50` |
| `GOOGLE_MAPS_API_KEY` | Google Maps API key (optional) | `AIza...` |

## IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/bulk-operations-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:pf360-api-*"
    }
  ]
}
```

## Deployment

### Build Package

```bash
cd lambda/bulk-operations

# Create deployment package
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --target package/
cd package && zip -r ../lambda.zip . && cd ..
zip -g lambda.zip handler.py

# Clean up
rm -rf package venv
```

### Deploy with Terraform

```hcl
resource "aws_lambda_function" "bulk_operations" {
  filename      = "lambda/bulk-operations/lambda.zip"
  function_name = "scheduling-agent-bulk-ops-${var.environment}"
  role          = aws_iam_role.lambda_bulk_ops.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 1024

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      PF360_API_URL    = var.pf360_api_url
      DYNAMODB_TABLE   = aws_dynamodb_table.bulk_ops_tracking.name
      MAX_PROJECTS     = 50
    }
  }
}
```

## Testing

### Local Testing

```python
import json
from handler import lambda_handler

# Test route optimization
event = {
    'body': json.dumps({
        'operation': 'optimize_route',
        'project_ids': ['12345', '12347', '12350', '12352'],
        'date': '2025-10-15',
        'optimize_for': 'time'
    })
}

response = lambda_handler(event, None)
print(json.loads(response['body']))
```

### API Gateway Testing

```bash
# Test via API Gateway
curl -X POST https://API_ID.execute-api.us-east-1.amazonaws.com/prod/bulk-operations \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "optimize_route",
    "project_ids": ["12345", "12347", "12350"],
    "optimize_for": "time"
  }'
```

## Performance

### Route Optimization
- **10 projects:** ~2 seconds
- **25 projects:** ~5 seconds
- **50 projects:** ~10 seconds

### Bulk Assignment
- **20 projects:** ~3 seconds
- **50 projects:** ~7 seconds
- **100 projects:** ~15 seconds

### Validation
- **50 projects:** ~5 seconds (parallel checks)
- **100 projects:** ~10 seconds

## Algorithms

### Route Optimization

Currently uses **Nearest Neighbor** algorithm (greedy heuristic):
- Fast: O(n²)
- Good enough for small datasets (< 50 projects)
- ~70-80% optimal

**Future improvement:** Use OR-Tools for exact TSP solving:
```python
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
```

### Conflict Detection

Checks:
- **Team availability** - vacation, capacity
- **Time overlaps** - existing appointments
- **Skill requirements** - certifications
- **Resource conflicts** - equipment, tools

## Monitoring

### CloudWatch Metrics

Custom metrics to publish:
- `BulkOperationsCount` - Total operations
- `RouteOptimizationTime` - P50, P95, P99
- `ProjectsProcessed` - Count by operation
- `ConflictsDetected` - Count

### CloudWatch Logs

```bash
# Tail logs
aws logs tail /aws/lambda/scheduling-agent-bulk-ops-dev --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-bulk-ops-dev \
  --filter-pattern "ERROR"
```

## Cost Estimate

### Lambda Costs (1000 operations/month)
- Memory: 1024 MB
- Duration: 10s average
- Invocations: 1000/month
- **Cost:** ~$0.40/month

### API Costs
- PF360 API calls: ~$0 (existing service)
- Google Maps API: ~$5/month (if using)

**Total: ~$5/month**

## Version History

- **v1.0.0** (2025-10-13): Initial implementation with 4 operations

## Related Documentation

- [BULK_SCHEDULING_DESIGN.md](../../docs/BULK_SCHEDULING_DESIGN.md)
- [Coordinator Action Group Schema](../../infrastructure/openapi_schemas/coordinator_actions.json)
