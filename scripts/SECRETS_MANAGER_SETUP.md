# AWS Secrets Manager Setup for PF360 Token

## ✅ Completed Setup

The ProjectForce API credentials have been successfully stored in AWS Secrets Manager for AWS Connect and Lambda integration.

### Secret Details

- **Secret Name**: `scheduling-agent/pf360/api-credentials`
- **Secret ARN**: `arn:aws:secretsmanager:us-east-1:618048437522:secret:scheduling-agent/pf360/api-credentials-tao3IX`
- **Region**: `us-east-1`
- **Account**: `618048437522`

### Secret Contents

```json
{
  "pf_token": "[ENCRYPTED_BEARER_TOKEN]",
  "client_id": "09PF05VD",
  "customer_id": "1646085",
  "api_url": "https://api-cx-portal.dev.projectsforce.com",
  "updated_at": "2025-11-25T...",
  "updated_by": "jjayaraj",
  "notes": "Copied from projectforce/api/credentials secret"
}
```

## 📚 How to Use This Secret

### 1️⃣ AWS Lambda (Python)

```python
import boto3
import json

def get_pf_credentials():
    """Retrieve PF credentials from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='scheduling-agent/pf360/api-credentials')
    secret = json.loads(response['SecretString'])
    return {
        'pf_token': secret['pf_token'],
        'client_id': secret['client_id'],
        'customer_id': secret['customer_id'],
        'api_url': secret['api_url']
    }

# Usage in Lambda:
creds = get_pf_credentials()
headers = {
    'projectforcetoken': creds['pf_token'],
    'Content-Type': 'application/json'
}
```

### 2️⃣ AWS Connect Contact Flow

Add a "Get customer input" or "Store customer input" block with:

```json
{
  "Type": "GetExternalData",
  "Parameters": {
    "SecretsManager": {
      "SecretArn": "arn:aws:secretsmanager:us-east-1:618048437522:secret:scheduling-agent/pf360/api-credentials-tao3IX"
    }
  },
  "Transitions": {
    "NextAction": "InvokeLambda",
    "Conditions": [],
    "Errors": []
  }
}
```

Then reference the secret in subsequent blocks:
- `$.Secrets.pf_token`
- `$.Secrets.client_id`
- `$.Secrets.customer_id`

### 3️⃣ AWS CLI (Test/Verify)

```bash
# Retrieve full secret
aws secretsmanager get-secret-value \
  --secret-id scheduling-agent/pf360/api-credentials \
  --query 'SecretString' --output text | jq .

# Extract just the token
aws secretsmanager get-secret-value \
  --secret-id scheduling-agent/pf360/api-credentials \
  --query 'SecretString' --output text | jq -r '.pf_token'
```

### 4️⃣ Lambda Environment Variable (Reference Only)

Instead of hardcoding tokens, reference the secret ARN in environment variables:

```bash
SECRET_ARN=arn:aws:secretsmanager:us-east-1:618048437522:secret:scheduling-agent/pf360/api-credentials-tao3IX
```

Then retrieve it at runtime using boto3.

## 🔒 IAM Permissions Required

### For AWS Lambda

The Lambda execution role needs:

```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:us-east-1:618048437522:secret:scheduling-agent/pf360/*"
}
```

### For AWS Connect

The AWS Connect service role needs:

```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:us-east-1:618048437522:secret:scheduling-agent/pf360/*"
}
```

## 🔄 Updating the Token

If you need to refresh the token in the future, you can either:

### Option 1: Manual Update (Recommended)

```bash
aws secretsmanager put-secret-value \
  --secret-id scheduling-agent/pf360/api-credentials \
  --secret-string '{"pf_token":"NEW_TOKEN_HERE","client_id":"09PF05VD","customer_id":"1646085","api_url":"https://api-cx-portal.dev.projectsforce.com"}'
```

### Option 2: Copy from Source Secret

```bash
# Get token from source secret
SOURCE_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id projectforce/api/credentials \
  --query 'SecretString' --output text | jq -r '.bearer_token')

# Update target secret
aws secretsmanager put-secret-value \
  --secret-id scheduling-agent/pf360/api-credentials \
  --secret-string "{\"pf_token\":\"$SOURCE_TOKEN\",\"client_id\":\"09PF05VD\",\"customer_id\":\"1646085\",\"api_url\":\"https://api-cx-portal.dev.projectsforce.com\"}"
```

## 📌 Next Steps

1. ✅ Secret created and populated with working token
2. ⬜ Grant AWS Connect IAM role permission to read this secret
3. ⬜ Update AWS Connect contact flow to retrieve secret
4. ⬜ Update Lambda functions to read from Secrets Manager (if not already doing so)
5. ⬜ Remove any hardcoded tokens from code/environment variables
6. ⬜ Set up CloudWatch alarm for secret access failures (optional)
7. ⬜ Document secret rotation policy (if needed)

## 🔍 Verification

To verify the secret is accessible:

```bash
# Test retrieval
aws secretsmanager get-secret-value \
  --secret-id scheduling-agent/pf360/api-credentials \
  --query 'SecretString' --output text | jq '.client_id, .customer_id'

# Expected output:
# "09PF05VD"
# "1646085"
```

## 📝 Notes

- The token stored is the same one currently in use by `projectforce/api/credentials`
- The token format is an encrypted bearer token (not a plain JWT)
- PF360 tokens appear to be long-lived and don't require frequent rotation
- The secret was last updated: 2025-11-25
