# DSPy Integration Deployment Guide

## Overview

This guide covers deploying the DSPy integration for continuous learning and prompt optimization.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRODUCTION FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Query ──► classifier.py ──► enhance_nlu_prompt() ──► Bedrock LLM     │
│                      │                    │                                  │
│                      │                    └── Loads few-shots from S3       │
│                      │                                                       │
│                      └──► log_classification() ──► S3 Training Logs         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           RETRAINING FLOW (Weekly)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  S3 Training Logs ──► retrain.py ──► DSPy Optimize ──► S3 Models            │
│         │                                                      │             │
│         └── Human Review ──► Corrections                       │             │
│                                                                 ▼             │
│                                              Lambda loads new models         │
│                                              (no redeployment needed)        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Files Added

| File | Location | Purpose |
|------|----------|---------|
| `dspy_integration.py` | `lambda/orchestrator/` | S3 model loading, prompt enhancement |
| `training_logger.py` | `lambda/orchestrator/` | Log classifications for training |
| `retrain.py` | `dspy-poc/` | Retraining script |
| `training_data.py` | `dspy-poc/` | 223 training examples |

## AWS Resources Required

### S3 Buckets

```bash
# Create S3 buckets
aws s3 mb s3://projectforce-dspy-models --region us-east-1
aws s3 mb s3://projectforce-training-logs --region us-east-1
```

### DynamoDB Table (Optional - for fast queries)

```bash
aws dynamodb create-table \
    --table-name projectforce-training-logs \
    --attribute-definitions \
        AttributeName=log_id,AttributeType=S \
    --key-schema \
        AttributeName=log_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

### Lambda Environment Variables

Add these to the orchestrator Lambda:

```bash
# DSPy Integration
DSPY_ENABLED=false                          # Set true for full DSPy mode
DSPY_MODEL_BUCKET=projectforce-dspy-models
DSPY_MODEL_PREFIX=optimized/

# Training Logger
TRAINING_LOG_ENABLED=true
TRAINING_LOG_BUCKET=projectforce-training-logs
TRAINING_LOG_TABLE=projectforce-training-logs
TRAINING_LOG_SAMPLE_RATE=1                  # Log every request (set higher to sample)
```

### IAM Permissions

Add to Lambda execution role:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::projectforce-dspy-models/*",
                "arn:aws:s3:::projectforce-training-logs/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:GetItem",
                "dynamodb:Scan"
            ],
            "Resource": "arn:aws:dynamodb:us-east-1:*:table/projectforce-training-logs"
        }
    ]
}
```

## Deployment Steps

### Step 1: Upload Initial Optimized Models

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/dspy-poc

# Upload optimized models to S3
aws s3 cp optimized_classifier.json s3://projectforce-dspy-models/optimized/
aws s3 cp optimized_extractor.json s3://projectforce-dspy-models/optimized/
aws s3 cp optimized_weather.json s3://projectforce-dspy-models/optimized/
```

### Step 2: Deploy Lambda

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/dev-22Dec/lambda/orchestrator

# Package and deploy
zip -r orchestrator.zip *.py
aws lambda update-function-code \
    --function-name projectforce-orchestrator \
    --zip-file fileb://orchestrator.zip \
    --region us-east-1
```

### Step 3: Set Environment Variables

```bash
aws lambda update-function-configuration \
    --function-name projectforce-orchestrator \
    --environment Variables="{
        TRAINING_LOG_ENABLED=true,
        TRAINING_LOG_BUCKET=projectforce-training-logs,
        DSPY_MODEL_BUCKET=projectforce-dspy-models
    }" \
    --region us-east-1
```

## Continuous Learning Workflow

### Daily: Automatic Logging

Classifications are automatically logged to S3:
```
s3://projectforce-training-logs/classification-logs/
    year=2026/
        month=01/
            day=03/
                <log_id>.json
```

### Weekly: Review & Retrain

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/dspy-poc

# 1. Fetch new examples from production logs
python retrain.py --fetch-from-s3 --days 7

# 2. Review and add corrections (optional)
# Edit training_data.py to add/fix examples

# 3. Re-optimize with new data
python retrain.py --local-only --upload

# 4. Verify new models are loaded
aws s3 ls s3://projectforce-dspy-models/optimized/
```

### Manual Corrections

When a misclassification is identified:

```python
from training_logger import log_feedback

# Correct a previous classification
log_feedback(
    log_id="abc-123-def",
    correct_intent="information",
    correct_action="get_project_details",
    feedback_type="correction",
    feedback_source="reviewer",
    notes="User asked for details, not scheduling"
)
```

## Integration Levels

### Level 1: Prompt Enhancement Only (Current)

- DSPy few-shot examples added to existing prompt
- No Lambda layer changes needed
- Fallback to regular prompt if models unavailable

```python
# In classifier.py
prompt = enhance_nlu_prompt(prompt)  # Adds DSPy few-shots
```

### Level 2: Full DSPy Mode (Future)

- DSPy runs classification directly
- Requires DSPy Lambda layer
- Set `DSPY_ENABLED=true`

```bash
# Create DSPy Lambda layer
pip install dspy-ai -t python/
zip -r dspy-layer.zip python/
aws lambda publish-layer-version \
    --layer-name dspy-layer \
    --zip-file fileb://dspy-layer.zip
```

## Monitoring

### Check Model Status

```python
from dspy_integration import get_model_status
print(get_model_status())
```

### Check Training Log Stats

```python
from training_logger import get_logging_stats
print(get_logging_stats(days=7))
```

### CloudWatch Queries

```sql
-- Classification latency
fields @timestamp, @message
| filter @message like /response_time_ms/
| stats avg(response_time_ms) by bin(1h)

-- DSPy model loads
fields @timestamp, @message
| filter @message like /Loaded DSPy model/
| stats count() by bin(1h)
```

## Troubleshooting

### Models Not Loading

1. Check S3 bucket permissions
2. Verify model files exist: `aws s3 ls s3://projectforce-dspy-models/optimized/`
3. Check Lambda logs for errors

### Training Logs Not Appearing

1. Verify `TRAINING_LOG_ENABLED=true`
2. Check S3 bucket permissions
3. Check `TRAINING_LOG_SAMPLE_RATE` (1 = all, 10 = 1 in 10)

### Retraining Fails

1. Ensure `ANTHROPIC_API_KEY` is set in `.env`
2. Check sufficient training examples (min 10)
3. Verify DSPy version: `pip show dspy-ai`

## Cost Estimates

| Component | Estimate |
|-----------|----------|
| S3 Storage (logs) | ~$0.023/GB/month |
| S3 Requests | ~$0.005/1000 requests |
| DynamoDB | Pay-per-request (~$0.25/million writes) |
| Retraining (Claude API) | ~$1-5 per run |

## Next Steps

1. **Enable logging**: Set `TRAINING_LOG_ENABLED=true`
2. **Monitor for 1 week**: Collect real user queries
3. **Review misclassifications**: Add corrections
4. **Run first retraining**: `python retrain.py --fetch-from-s3 --upload`
5. **Compare performance**: Check accuracy improvement
