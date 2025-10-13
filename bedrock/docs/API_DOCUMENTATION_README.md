# Bulk Operations API Documentation

**Version:** 1.0.0
**Last Updated:** October 13, 2025
**Status:** ✅ Production Ready

---

## 📚 Documentation Overview

This directory contains comprehensive API documentation for the **Bulk Scheduling Operations** system.

### Available Documentation Formats

| Format | File | Description |
|--------|------|-------------|
| **Swagger/OpenAPI YAML** | [`BULK_OPS_API_SWAGGER.yaml`](./BULK_OPS_API_SWAGGER.yaml) | Complete OpenAPI 3.0 specification |
| **Interactive HTML** | [`BULK_OPS_API_DOCS.html`](./BULK_OPS_API_DOCS.html) | Swagger UI interactive documentation |
| **Design Document** | [`BULK_SCHEDULING_DESIGN.md`](./BULK_SCHEDULING_DESIGN.md) | Architecture and design details |
| **Deployment Guide** | [`BULK_OPS_DEPLOYMENT.md`](./BULK_OPS_DEPLOYMENT.md) | Step-by-step deployment instructions |
| **Implementation Summary** | [`BULK_SCHEDULING_SUMMARY.md`](./BULK_SCHEDULING_SUMMARY.md) | Feature summary and benchmarks |

---

## 🚀 Quick Start

### View Documentation

**Option 1: Interactive Swagger UI (Recommended)**

```bash
cd docs
open BULK_OPS_API_DOCS.html
```

This opens a beautiful, interactive API documentation in your browser with:
- Try-it-out functionality
- Request/response examples
- Schema validation
- Filtering and search

**Option 2: Import into Swagger Editor**

1. Visit https://editor.swagger.io/
2. File → Import URL
3. Paste the YAML file path or content

**Option 3: View Raw YAML**

```bash
cat BULK_OPS_API_SWAGGER.yaml | less
```

---

## 📖 API Overview

### Base Information

- **Lambda ARN:** `arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-bulk-ops-dev`
- **Runtime:** Python 3.11
- **Timeout:** 60 seconds
- **Memory:** 1024 MB
- **Region:** us-east-1

### Endpoints

| Endpoint | Method | Description | Max Projects |
|----------|--------|-------------|--------------|
| `/optimize_route` | POST | Optimize route using TSP | 2-50 |
| `/bulk_assign` | POST | Bulk team assignments | 1-100 |
| `/validate_projects` | POST | Project validation | 1-100 |
| `/detect_conflicts` | POST | Conflict detection | Unlimited |

---

## 🔑 Authentication

This API is invoked by **AWS Bedrock Agents** internally. External access requires:

1. **AWS IAM Credentials**
   - Access Key ID
   - Secret Access Key
   - Session Token (if using STS)

2. **Lambda Invoke Permission**
   ```json
   {
     "Effect": "Allow",
     "Action": "lambda:InvokeFunction",
     "Resource": "arn:aws:lambda:us-east-1:618048437522:function:scheduling-agent-bulk-ops-dev"
   }
   ```

3. **Bedrock Agent Permission** (Already configured ✅)
   - Bedrock service can invoke the Lambda

---

## 📝 Example Requests

### 1. Route Optimization

**Request:**
```bash
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{
    "body": "{\"operation\": \"optimize_route\", \"project_ids\": [\"12345\", \"12347\", \"12350\"], \"date\": \"2025-10-15\", \"optimize_for\": \"time\"}"
  }' \
  response.json

cat response.json
```

**Response:**
```json
{
  "statusCode": 200,
  "body": {
    "operation": "route_optimize",
    "project_count": 3,
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
      "total_drive_time_minutes": 45,
      "time_saved_minutes": 77,
      "savings_percentage": 30.0
    }
  }
}
```

### 2. Bulk Assignment

**Request:**
```bash
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{
    "body": "{\"operation\": \"bulk_assign_teams\", \"project_ids\": [\"15001\", \"15002\", \"15003\"], \"team\": \"Team A\", \"date_range\": [\"2025-10-15\", \"2025-10-20\"]}"
  }' \
  response.json
```

**Response:**
```json
{
  "statusCode": 200,
  "body": {
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
        "suggested_resolution": "Assign to Team B"
      }
    ]
  }
}
```

### 3. Project Validation

**Request:**
```bash
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{
    "body": "{\"operation\": \"validate_projects\", \"project_ids\": [\"10001\", \"10002\"], \"validation_checks\": [\"permit\", \"measurement\", \"access\"]}"
  }' \
  response.json
```

**Response:**
```json
{
  "statusCode": 200,
  "body": {
    "operation": "validate",
    "total_projects": 2,
    "valid_count": 2,
    "issues_count": 0,
    "projects": [
      {
        "project_id": "10001",
        "is_valid": true,
        "checks": {
          "permit_valid": true,
          "measurements_complete": true,
          "access_approved": true
        },
        "issues": []
      }
    ],
    "summary": {
      "ready_to_schedule": ["10001", "10002"],
      "blocked": []
    }
  }
}
```

### 4. Conflict Detection

**Request:**
```bash
aws lambda invoke \
  --function-name scheduling-agent-bulk-ops-dev \
  --region us-east-1 \
  --payload '{
    "body": "{\"operation\": \"detect_conflicts\", \"project_ids\": [\"12345\"], \"team\": \"Team A\", \"date_range\": [\"2025-10-15\", \"2025-10-20\"]}"
  }' \
  response.json
```

**Response:**
```json
{
  "statusCode": 200,
  "body": {
    "conflicts_found": 0,
    "conflicts": []
  }
}
```

---

## 📊 Performance Benchmarks

| Operation | 10 Projects | 50 Projects | 100 Projects |
|-----------|-------------|-------------|--------------|
| **Route Optimization** | 2s | 10s | N/A (max 50) |
| **Bulk Assignment** | 2s | 7s | 15s |
| **Validation** | 3s | 5s | 10s |
| **Conflict Detection** | 2s | 3s | 5s |

---

## ⚠️ Error Handling

### HTTP Status Codes

| Code | Description | Example |
|------|-------------|---------|
| `200` | Success | Operation completed |
| `400` | Bad Request | Invalid parameters |
| `422` | Validation Error | Too many projects |
| `500` | Internal Error | Lambda timeout or crash |

### Error Response Format

```json
{
  "statusCode": 400,
  "body": {
    "error": "Invalid request parameters",
    "code": "BAD_REQUEST",
    "details": {
      "field": "project_ids",
      "message": "Must provide at least 2 project IDs"
    }
  }
}
```

---

## 🧪 Testing

### Manual Testing with AWS CLI

```bash
# Test route optimization
./test-route-optimization.sh

# Test bulk assignment
./test-bulk-assignment.sh

# Test validation
./test-validation.sh

# Test conflict detection
./test-conflict-detection.sh
```

### CloudWatch Logs

Monitor real-time logs:

```bash
aws logs tail /aws/lambda/scheduling-agent-bulk-ops-dev --follow
```

Filter errors:

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/scheduling-agent-bulk-ops-dev \
  --filter-pattern "ERROR"
```

---

## 📈 Monitoring

### Key Metrics to Track

1. **Invocation Count**
   - Metric: `Invocations`
   - Namespace: `AWS/Lambda`

2. **Error Rate**
   - Metric: `Errors`
   - Alert if > 5%

3. **Duration**
   - Metric: `Duration`
   - Alert if > 50s (near timeout)

4. **Throttles**
   - Metric: `Throttles`
   - Alert if > 0

### CloudWatch Dashboard

Create a dashboard with:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name bulk-ops-monitoring \
  --dashboard-body file://cloudwatch-dashboard.json
```

---

## 🔧 Troubleshooting

### Common Issues

**Issue 1: Lambda Timeout**

```
Error: Task timed out after 60.00 seconds
```

**Solution:**
- Reduce number of projects
- Increase Lambda timeout (if needed)
- Check PF360 API response times

**Issue 2: Invalid Project IDs**

```
Error: Project not found: 12345
```

**Solution:**
- Verify project IDs exist in PF360
- Check project status (must be active)

**Issue 3: DynamoDB Access Denied**

```
Error: An error occurred (AccessDeniedException) when calling PutItem
```

**Solution:**
- Check Lambda IAM role has DynamoDB permissions
- Verify table name matches: `scheduling-agent-bulk-ops-tracking-dev`

---

## 🔐 Security Best Practices

1. **Never expose Lambda ARN publicly**
2. **Use IAM roles with least privilege**
3. **Enable CloudWatch Logs encryption**
4. **Rotate API credentials regularly**
5. **Monitor for unusual invocation patterns**

---

## 📚 Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [OpenAPI 3.0 Specification](https://swagger.io/specification/)
- [Swagger UI Documentation](https://swagger.io/tools/swagger-ui/)

---

## 🆘 Support

### Internal Support

- **Slack Channel:** #scheduling-agent-support
- **Email:** dev-team@projectsforce.com
- **On-Call:** PagerDuty rotation

### External Support

- **Documentation Issues:** File an issue on GitHub
- **Feature Requests:** Submit via Jira
- **Security Issues:** security@projectsforce.com

---

## 📝 Changelog

### Version 1.0.0 (October 13, 2025)

- ✅ Initial release
- ✅ 4 operations implemented
- ✅ Complete Swagger documentation
- ✅ Lambda deployed to production
- ✅ Integration with Bedrock Agents

---

## 📄 License

Proprietary - ProjectsForce 360
© 2025 All Rights Reserved

---

**Last Updated:** October 13, 2025
**Maintained by:** Development Team
**Version:** 1.0.0
