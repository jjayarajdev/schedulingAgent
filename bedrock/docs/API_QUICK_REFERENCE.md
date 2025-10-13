# Bulk Operations API - Quick Reference

**Version:** 1.0.0 | **Last Updated:** October 13, 2025

---

## 🔗 Quick Links

- **Interactive Docs:** Open `BULK_OPS_API_DOCS.html` in browser
- **OpenAPI Spec:** `BULK_OPS_API_SWAGGER.yaml`
- **Postman Collection:** `BULK_OPS_POSTMAN_COLLECTION.json`
- **Full Documentation:** `API_DOCUMENTATION_README.md`

---

## 📍 Endpoints

| Operation | Endpoint | Max Projects |
|-----------|----------|--------------|
| **Route Optimization** | `/optimize_route` | 2-50 |
| **Bulk Assignment** | `/bulk_assign` | 1-100 |
| **Validation** | `/validate_projects` | 1-100 |
| **Conflict Detection** | `/detect_conflicts` | Unlimited |

---

## 🚀 Quick Start

### AWS CLI

```bash
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{"body": "{\"operation\": \"optimize_route\", \"project_ids\": [\"12345\", \"12347\"], \"date\": \"2025-10-15\"}"}' \
  response.json
```

### Python

```python
import boto3
import json

lambda_client = boto3.client('lambda', region_name='us-east-1')

response = lambda_client.invoke(
    FunctionName='scheduling-agent-bulk-ops-dev',
    InvocationType='RequestResponse',
    Payload=json.dumps({
        'body': json.dumps({
            'operation': 'optimize_route',
            'project_ids': ['12345', '12347', '12350'],
            'date': '2025-10-15',
            'optimize_for': 'time'
        })
    })
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))
```

### Node.js

```javascript
const AWS = require('aws-sdk');
const lambda = new AWS.Lambda({ region: 'us-east-1' });

const params = {
  FunctionName: 'scheduling-agent-bulk-ops-dev',
  InvocationType: 'RequestResponse',
  Payload: JSON.stringify({
    body: JSON.stringify({
      operation: 'optimize_route',
      project_ids: ['12345', '12347', '12350'],
      date: '2025-10-15',
      optimize_for: 'time'
    })
  })
};

lambda.invoke(params, (err, data) => {
  if (err) console.error(err);
  else console.log(JSON.parse(data.Payload));
});
```

---

## 📝 Request/Response Examples

### 1️⃣ Route Optimization

**Request:**
```json
{
  "operation": "optimize_route",
  "project_ids": ["12345", "12347", "12350"],
  "date": "2025-10-15",
  "optimize_for": "time"
}
```

**Response:**
```json
{
  "operation": "route_optimize",
  "project_count": 3,
  "optimized_route": [...],
  "metrics": {
    "total_distance_miles": 45.2,
    "time_saved_minutes": 77,
    "savings_percentage": 30.0
  }
}
```

### 2️⃣ Bulk Assignment

**Request:**
```json
{
  "operation": "bulk_assign_teams",
  "project_ids": ["15001", "15002", "15003"],
  "team": "Team A",
  "date_range": ["2025-10-15", "2025-10-20"]
}
```

**Response:**
```json
{
  "operation": "bulk_assign",
  "successful": 2,
  "failed": 1,
  "assignments": [...],
  "conflicts": [...]
}
```

### 3️⃣ Project Validation

**Request:**
```json
{
  "operation": "validate_projects",
  "project_ids": ["10001", "10002", "10003"],
  "validation_checks": ["permit", "measurement", "access"]
}
```

**Response:**
```json
{
  "operation": "validate",
  "valid_count": 2,
  "issues_count": 1,
  "projects": [...],
  "summary": {
    "ready_to_schedule": ["10001", "10002"],
    "blocked": ["10003"]
  }
}
```

### 4️⃣ Conflict Detection

**Request:**
```json
{
  "operation": "detect_conflicts",
  "project_ids": ["12345", "12347"],
  "team": "Team A",
  "date_range": ["2025-10-15", "2025-10-20"]
}
```

**Response:**
```json
{
  "conflicts_found": 1,
  "conflicts": [
    {
      "project_id": "12347",
      "reason": "Team A at capacity",
      "severity": "warning",
      "suggested_resolution": "Consider Team C"
    }
  ]
}
```

---

## ⚡ Performance

| Projects | Route Opt | Bulk Assign | Validation |
|----------|-----------|-------------|------------|
| 10 | 2s | 2s | 3s |
| 25 | 5s | 4s | 3s |
| 50 | 10s | 7s | 5s |
| 100 | N/A | 15s | 10s |

---

## ⚠️ Error Codes

| Code | Description | Action |
|------|-------------|--------|
| 400 | Bad Request | Check parameters |
| 422 | Validation Error | Reduce project count |
| 500 | Internal Error | Check CloudWatch logs |

---

## 🔐 Authentication

**Required:** AWS IAM credentials with Lambda invoke permission

```json
{
  "Effect": "Allow",
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-bulk-ops-dev"
}
```

---

## 📊 Monitoring

**CloudWatch Logs:**
```bash
aws logs tail /aws/lambda/scheduling-agent-bulk-ops-dev --follow
```

**DynamoDB Tracking:**
```bash
aws dynamodb scan --table-name scheduling-agent-bulk-ops-tracking-dev
```

**Lambda Metrics:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=scheduling-agent-bulk-ops-dev \
  --start-time 2025-10-13T00:00:00Z \
  --end-time 2025-10-14T00:00:00Z \
  --period 3600 \
  --statistics Average,Maximum
```

---

## 🛠️ Troubleshooting

### Lambda Timeout
```
Error: Task timed out after 60.00 seconds
```
**Fix:** Reduce project count or increase timeout

### Invalid Project ID
```
Error: Project not found: 12345
```
**Fix:** Verify project exists in PF360

### DynamoDB Access Denied
```
Error: AccessDeniedException
```
**Fix:** Check Lambda IAM role permissions

---

## 📚 Documentation

| Doc | Purpose |
|-----|---------|
| `BULK_OPS_API_SWAGGER.yaml` | OpenAPI 3.0 specification |
| `BULK_OPS_API_DOCS.html` | Interactive Swagger UI |
| `BULK_OPS_POSTMAN_COLLECTION.json` | Postman collection |
| `API_DOCUMENTATION_README.md` | Complete documentation |
| `BULK_SCHEDULING_DESIGN.md` | Architecture design |
| `BULK_OPS_DEPLOYMENT.md` | Deployment guide |

---

## 🆘 Support

- **Slack:** #scheduling-agent-support
- **Email:** dev-team@projectsforce.com
- **Logs:** CloudWatch `/aws/lambda/scheduling-agent-bulk-ops-dev`

---

## 💡 Tips

✅ **DO:**
- Batch projects by region for route optimization
- Check conflicts before bulk assignment
- Validate projects before scheduling
- Monitor CloudWatch metrics

❌ **DON'T:**
- Exceed 50 projects for route optimization
- Ignore conflict warnings
- Skip validation checks
- Forget to handle errors

---

**Lambda ARN:** `arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-bulk-ops-dev`

**Region:** us-east-1

**Timeout:** 60 seconds

**Memory:** 1024 MB
