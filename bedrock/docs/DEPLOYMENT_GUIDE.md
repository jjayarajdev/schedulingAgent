# AWS Deployment Guide for ProjectForce Bedrock Agent UI

## Architecture Overview

```
┌─────────────┐      HTTPS      ┌──────────────┐
│   Browser   │ ───────────────> │  CloudFront  │
│             │                  │     (CDN)    │
└─────────────┘                  └──────┬───────┘
                                        │
                                        v
                                 ┌──────────────┐
                                 │   S3 Bucket  │
                                 │  (HTML/CSS)  │
                                 └──────────────┘
                                        │
                                        │ API Calls
                                        v
                                 ┌──────────────┐
                                 │ API Gateway  │
                                 │  (HTTP API)  │
                                 └──────┬───────┘
                                        │
                                        v
                                 ┌──────────────┐
                                 │    Lambda    │
                                 │ (Flask App)  │
                                 └──────┬───────┘
                                        │
                                        v
                                 ┌──────────────┐
                                 │   Bedrock    │
                                 │    Agents    │
                                 └──────────────┘
```

## Deployment Steps

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. IAM permissions for:
   - S3 (CreateBucket, PutObject, PutBucketPolicy)
   - Lambda (CreateFunction, UpdateFunctionCode)
   - API Gateway (CreateApi, CreateStage)
   - IAM (CreateRole, AttachRolePolicy)
   - CloudFront (optional, for HTTPS)

### Step 1: Deploy Updated Lambda Functions

First, fix the scheduling API bug by deploying the updated Lambda code:

```bash
cd /Users/jjayaraj/workspaces/studios/projectsforce/schedulingAgent-bb/bedrock

# Deploy information-actions Lambda (contains the scheduling bug fix)
cd lambda/information-actions
zip -r function.zip handler.py requirements.txt
aws lambda update-function-code \
    --function-name pf-bedrock-information-actions \
    --zip-file fileb://function.zip \
    --region us-east-1

# Deploy scheduling-actions Lambda (contains endpoint fixes)
cd ../scheduling-actions
zip -r function.zip handler.py requirements.txt
aws lambda update-function-code \
    --function-name pf-bedrock-scheduling-actions \
    --zip-file fileb://function.zip \
    --region us-east-1

cd ../..
```

### Step 2: Deploy API Gateway

This creates an HTTP API that proxies requests from the UI to your Bedrock agents:

```bash
cd scripts
chmod +x deploy_api_gateway.sh
./deploy_api_gateway.sh dev
```

**What this does:**
- Creates a Lambda function from your Flask backend (`backend/app.py`)
- Wraps it in an API Gateway-compatible handler
- Creates HTTP API with CORS enabled
- Configures Lambda integration
- Deploys to production stage
- Outputs API endpoint URL

**Expected output:**
```
================================================
  ✅ API Gateway Deployment Complete!
================================================

API Endpoint:
  https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod

Test the API:
  curl https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/api/health
```

### Step 3: Deploy UI to S3

Deploy the HTML/CSS/JS files to S3 for static hosting:

```bash
# Update API endpoint in deploy_ui.sh first
API_GATEWAY_URL="https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod"
sed -i.bak "s|API_GATEWAY_URL=\"\"|API_GATEWAY_URL=\"$API_GATEWAY_URL\"|g" deploy_ui.sh

# Deploy UI
chmod +x deploy_ui.sh
./deploy_ui.sh dev
```

**What this does:**
- Creates S3 bucket for static website hosting
- Configures bucket for public read access
- Updates `index.html` with API Gateway endpoint
- Uploads all UI files to S3
- Outputs website URL

**Expected output:**
```
================================================
  ✅ Deployment Complete!
================================================

S3 Website URL:
  http://pf-agent-ui-dev.s3-website-us-east-1.amazonaws.com

Next Steps:
  1. Test the UI at the URL above
  2. (Optional) Set up CloudFront for HTTPS
```

### Step 4: (Optional) Add CloudFront CDN

For production, add CloudFront for HTTPS and global distribution:

```bash
# Create CloudFront distribution
aws cloudfront create-distribution \
    --origin-domain-name pf-agent-ui-dev.s3-website-us-east-1.amazonaws.com \
    --default-root-object index.html \
    --query 'Distribution.DomainName' \
    --output text
```

This takes 15-20 minutes to deploy globally. You'll get a URL like:
```
https://d111111abcdef8.cloudfront.net
```

### Step 5: (Optional) Custom Domain

If you have a custom domain in Route 53:

```bash
# 1. Request ACM certificate (must be in us-east-1 for CloudFront)
aws acm request-certificate \
    --domain-name chat.projectsforce.com \
    --validation-method DNS \
    --region us-east-1

# 2. Validate certificate via DNS (follow email/console instructions)

# 3. Update CloudFront distribution with custom domain and certificate

# 4. Create Route 53 alias record pointing to CloudFront
```

## Architecture Options

### Option A: S3 + CloudFront (Current)
**Pros:**
- Full control over infrastructure
- Cost-effective for static sites
- Easy to integrate with existing AWS services
- CloudFront provides global CDN

**Cons:**
- Manual configuration required
- Separate API Gateway setup
- More moving parts to manage

**Cost:** ~$1-5/month for low traffic

### Option B: AWS Amplify
**Pros:**
- Simplified deployment (one command)
- Built-in CI/CD from Git
- Automatic HTTPS
- Integrated backend (AppSync/Lambda)

**Cons:**
- Less control over infrastructure
- Higher cost for advanced features
- Locked into Amplify ecosystem

**Cost:** ~$0.01/build + $0.15/GB served

## Environment Variables

The deployment scripts use these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `dev` | Deployment environment (dev/staging/prod) |
| `AWS_REGION` | `us-east-1` | AWS region for resources |
| `API_NAME` | `pf-agent-api-${ENVIRONMENT}` | API Gateway name |
| `S3_BUCKET` | `pf-agent-ui-${ENVIRONMENT}` | S3 bucket name |

## Testing the Deployment

### Test API Gateway
```bash
# Health check
curl https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/api/health

# Chat endpoint
curl -X POST https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me my projects", "sessionId": "test-123"}'
```

### Test UI
1. Open S3 website URL in browser
2. Type "Show me my projects"
3. Verify projects load with formatted cards
4. Select project and test date/time selection
5. Verify appointment scheduling works

## Monitoring and Logs

### CloudWatch Logs
```bash
# View Lambda logs
aws logs tail /aws/lambda/pf-bedrock-agent-proxy-dev --follow

# View API Gateway logs (if enabled)
aws logs tail /aws/apigateway/pf-agent-api-dev --follow
```

### Metrics
- Lambda invocations: CloudWatch → Lambda → Metrics
- API Gateway requests: CloudWatch → API Gateway → Metrics
- S3 bandwidth: CloudWatch → S3 → Metrics

## Cleanup

To remove all deployed resources:

```bash
# Delete CloudFront distribution (if created)
aws cloudfront delete-distribution --id YOUR-DISTRIBUTION-ID

# Delete API Gateway
aws apigatewayv2 delete-api --api-id YOUR-API-ID

# Delete Lambda function
aws lambda delete-function --function-name pf-bedrock-agent-proxy-dev

# Delete S3 bucket
aws s3 rb s3://pf-agent-ui-dev --force

# Delete IAM roles
aws iam delete-role --role-name pf-api-lambda-role-dev
```

## Troubleshooting

### Issue: API Gateway returns 403 Forbidden
**Fix:** Check Lambda permissions allow API Gateway to invoke:
```bash
aws lambda get-policy --function-name pf-bedrock-agent-proxy-dev
```

### Issue: S3 website returns 404
**Fix:** Verify bucket policy allows public read:
```bash
aws s3api get-bucket-policy --bucket pf-agent-ui-dev
```

### Issue: CORS errors in browser
**Fix:** Update API Gateway CORS configuration:
```bash
aws apigatewayv2 update-api \
    --api-id YOUR-API-ID \
    --cors-configuration AllowOrigins='*',AllowMethods='GET,POST,OPTIONS',AllowHeaders='Content-Type'
```

### Issue: Lambda timeout errors
**Fix:** Increase timeout (current: 30s, max: 900s):
```bash
aws lambda update-function-configuration \
    --function-name pf-bedrock-agent-proxy-dev \
    --timeout 60
```

## Security Considerations

1. **API Authentication**: Add API Gateway authorizer for production
2. **S3 Bucket**: Consider CloudFront-only access (disable direct S3 access)
3. **HTTPS**: Always use CloudFront with ACM certificate for production
4. **Secrets**: Never commit AWS credentials or API keys to Git
5. **IAM Roles**: Follow least-privilege principle for Lambda execution role
6. **CORS**: Restrict allowed origins to your domain in production

## Production Checklist

- [ ] Lambda functions deployed with latest code
- [ ] API Gateway deployed with correct endpoints
- [ ] S3 bucket created and configured
- [ ] CloudFront distribution created (for HTTPS)
- [ ] Custom domain configured (optional)
- [ ] API Gateway authorizer added (for auth)
- [ ] CloudWatch alarms configured
- [ ] Backup/disaster recovery plan
- [ ] Cost alerts configured
- [ ] Security review completed
