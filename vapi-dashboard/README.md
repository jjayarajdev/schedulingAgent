# PF-SYN VAPI Dashboard

Multi-tenant dashboard for VAPI call analytics and cost tracking.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    React Frontend (S3)                          │
│                    Login → Dashboard → Reports                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API Gateway                               │
│     /auth/login  /api/calls  /api/stats  /api/costs             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
┌───────────────────────┐   ┌───────────────────────────────────┐
│   Auth Lambda         │   │        API Lambda                 │
│   - Login             │   │   - Fetch VAPI calls              │
│   - JWT verify        │   │   - Stats & costs                 │
└───────────┬───────────┘   └───────────┬───────────────────────┘
            │                           │
            ▼                           ▼
┌───────────────────────┐   ┌───────────────────────────────────┐
│      DynamoDB         │   │          VAPI API                 │
│   - Users             │   │   - GET /call                     │
│   - Tenants           │   │   - Filtered by phoneNumberId     │
└───────────────────────┘   └───────────────────────────────────┘
```

## Environments

| Environment | Region | Resources Prefix |
|-------------|--------|------------------|
| DEV | us-east-1 | `pf-syn-vapi-dashboard-*-dev` |
| PROD | us-east-2 | `pf-syn-vapi-dashboard-*-prod` |

## Quick Start

### 1. Setup Infrastructure (First Time Only)

```bash
cd infrastructure

# DEV (us-east-1)
chmod +x *.sh
./setup-dev.sh

# PROD (us-east-2)
./setup-prod.sh
```

This creates:
- IAM Role for Lambda
- DynamoDB tables (users, tenants)
- S3 bucket for frontend
- API Gateway

### 2. Deploy Backend

```bash
# DEV
export VAPI_API_KEY="your-vapi-api-key"
./deploy-backend-dev.sh

# PROD
export VAPI_API_KEY="your-vapi-api-key"
./deploy-backend-prod.sh
```

### 3. Deploy Frontend

```bash
# Build React app first
cd ../frontend
npm install
npm run build

# Deploy to S3
cd ../infrastructure
./deploy-frontend-dev.sh   # or deploy-frontend-prod.sh
```

## API Endpoints

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Login with username/password |
| GET | `/auth/verify` | Verify JWT token |
| POST | `/auth/logout` | Logout |

### API (Requires JWT)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/calls` | List calls for tenant |
| GET | `/api/call/{id}` | Get call details + transcript |
| GET | `/api/stats` | Get statistics |
| GET | `/api/costs` | Get cost breakdown |
| GET | `/api/tenants` | List tenants (admin only) |

## Login Credentials

### Default Admin (DEV only)
- Username: `admin`
- Password: `admin123`
- Tenant: `pf` (ProjectsForce)

**IMPORTANT:** Change password in production!

## Adding Tenants & Users

### Add Tenant
```bash
AWS_PROFILE=pf-aws aws dynamodb put-item \
  --table-name pf-syn-vapi-dashboard-tenants-dev \
  --item '{
    "tenant_id": {"S": "new-tenant"},
    "name": {"S": "New Tenant Name"},
    "vapi_phone_number_id": {"S": "vapi-phone-id"},
    "vapi_phone_number": {"S": "+1234567890"}
  }' \
  --region us-east-1
```

### Add User
```bash
# Generate password hash
HASH=$(python3 -c "import hashlib; print(hashlib.sha256('secure-password'.encode()).hexdigest())")

AWS_PROFILE=pf-aws aws dynamodb put-item \
  --table-name pf-syn-vapi-dashboard-users-dev \
  --item '{
    "username": {"S": "newuser"},
    "password_hash": {"S": "'$HASH'"},
    "tenant_id": {"S": "tenant-id"},
    "role": {"S": "user"},
    "name": {"S": "User Name"}
  }' \
  --region us-east-1
```

## Reports

1. **Executive Overview** - KPIs, success rate, call volume
2. **Cost Analytics** - Spend by tenant, cost breakdown
3. **Call Outcomes** - Success/fail, end reasons
4. **Call Log** - Searchable call list with transcripts
5. **Issues** - Error patterns, improvement opportunities

## Security Notes

- JWT tokens expire after 24 hours
- Passwords are SHA-256 hashed
- Tenants can only see their own calls
- Admin role can view all tenants
- VAPI API key stored in Lambda environment variables

## Troubleshooting

### "Tenant not found"
- Verify tenant exists in DynamoDB
- Check tenant_id matches user's tenant_id

### "VAPI API error"
- Check VAPI_API_KEY is set in Lambda
- Verify phone number ID exists in VAPI

### CORS errors
- API Gateway CORS is configured for `*`
- If custom domain, update CORS settings
