# Test Credentials

## ProjectForce API Test Account

**Always use these credentials for testing:**

```json
{
  "email": "jay@mailinator.com",
  "password": "U2FsdGVkX1/ZiR9CNgR3SeEgf5MHKaC1npGOA+P5PTY=",
  "device_type": 1
}
```

### Details:

- **Email:** `jay@mailinator.com`
- **Password (encrypted):** `U2FsdGVkX1/ZiR9CNgR3SeEgf5MHKaC1npGOA+P5PTY=`
- **Password (plaintext):** `All0wj@y5677`
- **Device Type:** `1`

### Associated IDs:

- **Client ID:** `09PF05VD`
- **User ID / Customer ID:** `6f72bffa-c323-4058-a01c-9d495d696364`
- **Customer Type:** `B2C`

### API Endpoints:

- **Auth URL:** `https://auth.dev.projectsforce.com`
- **API Base URL:** `https://api-cx-portal.dev.projectsforce.com`

### OAuth2 Credentials:

- **Client ID:** `web-client`
- **Client Secret:** `77mq6MbaNyU0Gzz7SV1zXx`

### Usage in Tests:

All test scripts should use these credentials:
- `test_api_real.sh`
- `scripts/test_agents.sh`
- `test_lambda_direct.py`

### Session Attributes Format:

```json
{
  "customer_id": "6f72bffa-c323-4058-a01c-9d495d696364",
  "client_id": "09PF05VD",
  "user_name": "jay@mailinator.com",
  "customer_type": "B2C",
  "pf_api_base": "https://api.dev.projectsforce.com",
  "device_type": "1"
}
```
